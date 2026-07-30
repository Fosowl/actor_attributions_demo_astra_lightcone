"""One-time extraction of the demo subset from the private source corpus.

Reads the three presidential projection files, the reference consensus
embeddings, and the study's per-point five-variant results; writes the
committed demo data files. The source corpus is NOT distributed with this
repo — this tool exists so the published files are reproducible for anyone
with access to the private working tree.

Inputs (via --source-dir, the private working tree):
  data_may7_2026/projections/{Lee,Park,Moon}_projection.xlsx
  for_hyein/embeddings6_projected.csv
  for_hyein/park_moon_results_2026-05-07_v2/all_five_variants_filtered.xlsx

Reference-statistics conventions (verified point-level against the study's
per-sentence keep decisions; every choice below is load-bearing):
  - reference coordinates AND cluster labels come from
    embeddings6_projected.csv (the deliverable npz holds a different
    projection version and does NOT reproduce the study's distances)
  - covariance: np.cov(cluster points) + 1e-6 * I (ridge)
  - Mahalanobis LOO distribution: leave each reference point out, recompute
    centroid AND ridged covariance, squared distance
  - Euclidean LOO distribution: leave-one-out centroid only, non-squared

Outputs (side effects — writes into the repo):
  data/pledges_subset.csv               real sentences, complete cluster-6 slice
  data/reference_stats.npz              derived reference statistics, no text
  tests/fixtures/expected_cluster6.csv  per-point expected keep decisions

Every output is deterministic. Fails loudly on any schema surprise.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

PRESIDENTS = ("Lee", "Park", "Moon")
DIM_COLS = [f"D{i}" for i in range(1, 19)]
TARGET_CLUSTER_1IDX = 6
EXPECTED_N = 218  # study ground truth for cluster 6
KEEP_COLS = ["sentence_id", "text_sentence", "president", "cluster", *DIM_COLS]

# Study convention: per-cluster covariance is ridged (see module docstring).
RIDGE_EPS = 1e-6

# Column names in the study's per-point five-variant results file.
STUDY_KEEP_MAHAL = "keep_M_pooled_p99"
STUDY_KEEP_EUCL = "keep_E_pooled_p99"

# Known source-data quirk (documented in the study as an OCR artifact):
# Park_projection.xlsx names its sentence-text column with a stray jamo
# instead of "text_sentence". Renamed explicitly, never by position.
SOURCE_TEXT_COL_FIXES = {"Park": {"ㅎ": "text_sentence"}}


def get_oos_frame(source_dir: Path) -> pd.DataFrame:
    """Load and concatenate the three projection files, 1-indexing clusters.

    Returns all OOS rows (all clusters) with a stable sentence_id assigned
    from the president and the source-file row position BEFORE any filtering,
    so ids remain stable regardless of the target cluster.
    """
    frames: list[pd.DataFrame] = []
    for president in PRESIDENTS:
        path = source_dir / "data_may7_2026" / "projections" / f"{president}_projection.xlsx"
        if not path.exists():
            raise FileNotFoundError(f"missing projection file: {path}")
        df = pd.read_excel(path)
        fixes = SOURCE_TEXT_COL_FIXES.get(president, {})
        if fixes and not set(fixes).issubset(df.columns):
            raise ValueError(f"{path.name}: expected quirk column(s) {sorted(fixes)} absent")
        df = df.rename(columns=fixes)
        missing = [c for c in ("text_sentence", "cluster_k", *DIM_COLS) if c not in df.columns]
        if missing:
            raise ValueError(f"{path.name}: missing expected columns {missing}")
        df = df.reset_index(drop=True)
        df["sentence_id"] = [f"{president}_{i:04d}" for i in df.index]
        df["president"] = president
        frames.append(df)
    oos = pd.concat(frames, ignore_index=True)
    cluster_min = int(cast(Any, oos["cluster_k"].min()))
    if cluster_min == 0:
        oos["cluster"] = oos["cluster_k"].astype(int) + 1
    elif cluster_min == 1:
        oos["cluster"] = oos["cluster_k"].astype(int)
    else:
        raise ValueError(f"cannot infer cluster indexing: min cluster_k = {cluster_min}")
    return oos


def get_reference_stats(ref_csv_path: Path, cluster_1idx: int) -> dict[str, np.ndarray]:
    """Derive per-cluster reference statistics from the projected reference corpus.

    Returns mu_ref, the ridged cov_ref, and the sorted leave-one-out distance
    distributions for the target cluster, using the study's exact conventions
    (see module docstring): Mahalanobis LOO recomputes centroid and ridged
    covariance per held-out point (squared distances); Euclidean LOO recomputes
    the centroid only (non-squared distances).
    """
    ref = pd.read_csv(ref_csv_path)
    missing = [c for c in ("cluster_k", *DIM_COLS) if c not in ref.columns]
    if missing:
        raise ValueError(f"{ref_csv_path.name}: missing expected columns {missing}")
    coords = ref[DIM_COLS].to_numpy(dtype=np.float64)
    labels = ref["cluster_k"].to_numpy()
    labels_1idx = labels + 1 if int(cast(Any, labels.min())) == 0 else labels
    points = coords[labels_1idx == cluster_1idx]
    n_ref = points.shape[0]
    if n_ref <= coords.shape[1] + 1:
        raise ValueError(
            f"cluster {cluster_1idx}: n_ref={n_ref} too small for a "
            f"non-singular {coords.shape[1]}-d covariance"
        )
    dim = coords.shape[1]
    loo_mahal_d2 = np.empty(n_ref)
    loo_eucl_d = np.empty(n_ref)
    for j in range(n_ref):
        rest = np.delete(points, j, axis=0)
        mu_j = rest.mean(axis=0)
        cov_j = np.cov(rest, rowvar=False) + RIDGE_EPS * np.eye(dim)
        diff = points[j] - mu_j
        loo_mahal_d2[j] = float(diff @ np.linalg.inv(cov_j) @ diff)
        loo_eucl_d[j] = float(np.linalg.norm(diff))
    return {
        "mu_ref": points.mean(axis=0),
        "cov_ref": np.cov(points, rowvar=False) + RIDGE_EPS * np.eye(dim),
        "loo_mahal_d2": np.sort(loo_mahal_d2),
        "loo_eucl_d": np.sort(loo_eucl_d),
        "n_ref": np.asarray(n_ref),
        "cluster_1idx": np.asarray(cluster_1idx),
    }


def get_expected_decisions(xlsx_path: Path, subset: pd.DataFrame) -> pd.DataFrame:
    """Extract per-point expected keep flags for the two headline variants.

    Matches the study's per-point results to the subset by (president,
    text_sentence). Raises if any subset sentence cannot be matched —
    silent fuzziness here would poison the regression fixture.
    Returns a frame with sentence_id + two boolean columns, no text.
    """
    ref = pd.read_excel(xlsx_path)
    needed = ["text_sentence", "president", STUDY_KEEP_MAHAL, STUDY_KEEP_EUCL]
    missing = [c for c in needed if c not in ref.columns]
    if missing:
        raise ValueError(
            f"{xlsx_path.name}: missing expected columns {missing}; "
            f"actual columns: {list(ref.columns)}"
        )
    study = cast(pd.DataFrame, ref[needed]).drop_duplicates(
        subset=("president", "text_sentence")
    )
    merged = subset.merge(
        study,
        on=["president", "text_sentence"],
        how="left",
        validate="many_to_one",
    )
    unmatched = merged[STUDY_KEEP_MAHAL].isna()
    if bool(unmatched.any()):
        raise ValueError(
            f"{int(cast(Any, unmatched.sum()))} subset sentences not found in {xlsx_path.name}; "
            "refusing to write a partial fixture"
        )
    return pd.DataFrame(
        {
            "sentence_id": merged["sentence_id"],
            "keep_mahalanobis_pooled": merged[STUDY_KEEP_MAHAL].astype(bool),
            "keep_euclidean_pooled": merged[STUDY_KEEP_EUCL].astype(bool),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="private source working tree (not distributed)",
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]

    oos = get_oos_frame(args.source_dir)
    subset = oos.loc[oos["cluster"] == TARGET_CLUSTER_1IDX, KEEP_COLS].reset_index(drop=True)
    if len(subset) != EXPECTED_N:
        raise ValueError(
            f"cluster {TARGET_CLUSTER_1IDX} slice has {len(subset)} rows, "
            f"expected {EXPECTED_N} (study ground truth) — reconcile before writing"
        )

    stats = get_reference_stats(
        args.source_dir / "for_hyein" / "embeddings6_projected.csv",
        TARGET_CLUSTER_1IDX,
    )
    expected = get_expected_decisions(
        args.source_dir
        / "for_hyein"
        / "park_moon_results_2026-05-07_v2"
        / "all_five_variants_filtered.xlsx",
        subset,
    )

    (repo / "data").mkdir(exist_ok=True)
    (repo / "tests" / "fixtures").mkdir(parents=True, exist_ok=True)
    subset.to_csv(repo / "data" / "pledges_subset.csv", index=False)
    np.savez(repo / "data" / "reference_stats.npz", **cast("dict[str, Any]", stats))
    expected.to_csv(repo / "tests" / "fixtures" / "expected_cluster6.csv", index=False)
    kept_m = int(cast(Any, expected["keep_mahalanobis_pooled"].sum()))
    kept_e = int(cast(Any, expected["keep_euclidean_pooled"].sum()))
    print(f"subset: {len(subset)} rows -> data/pledges_subset.csv")
    print(f"expected keeps: mahalanobis {kept_m}/{len(subset)}, euclidean {kept_e}/{len(subset)}")


if __name__ == "__main__":
    main()
