# Korean Pledges Actor-Attribution Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `korean-pledges-demo/`, a runnable real-data example showing what the RFC-0003 actor layer adds: a complete cluster slice of the Korean forest-policy OOS pledge corpus, a filter that recomputes the study's real retention numbers live, an attributed two-decision ASTRA analysis, and a live-demo chat script.

**Architecture:** A one-time extraction tool produces two committed data files (real sentences + derived reference statistics). A pure-function filter module recomputes retention per universe, reading its configuration *from the ASTRA universe files themselves*. The attributed `analysis/astra.yaml` quotes only numbers the pipeline computes; a test enforces that invariant permanently.

**Tech Stack:** Python 3.12 (the repo venv built by `install_and_validate.sh`), numpy, pandas, scipy, pydantic v2, pytest, the `astra` CLI from the sibling submodules.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-30-korean-pledges-demo-design.md`. Read it first.
- No changes to the `astra-spec` / `astra-tools` submodules, the iris example, or `install_and_validate.sh`.
- Branch: `feature/korean-pledges-demo`. Never push to `main`.
- Commit messages: self-contained, no AI-attribution footers, `type(scope): summary` shape.
- Published subset columns are exactly `sentence_id`, `text_sentence`, `president`, `cluster`, `D1..D18`. No district/party/code/similarity columns may be committed.
- The honesty invariant: every percentage in `analysis/astra.yaml` must be a value the pipeline computes from `data/`. Never hand-adjust a number to match the YAML or the study; on mismatch, stop and reconcile the implementation.
- Actor registry values (fixed by the approved design): `oliver` (human); `claude_code` (agent, `model: claude-opus-4-8`, `harness: claude-code`, `version: "2026-05"`).
- Ground truth for verification (from the study's May 2026 five-variant comparison, manuscript supplementary "OOS Conformal Filter — Design Decisions"): cluster 6 (1-indexed, "Forest Bioenergy and Industrial Growth"), n = 218 OOS sentences; Mahalanobis + pooled correction keeps 68 (31.2%); Euclidean + pooled correction keeps 161 (73.9%).
- The demo venv is `.venv/` at repo root (created by `./install_and_validate.sh`). Demo Python deps are added to it idempotently by `run_demo.sh` (Task 4); until then use `uv pip install -q -p .venv numpy pandas scipy pydantic openpyxl pytest` manually.
- Private source corpus (never committed): `--source-dir` pointing at the researcher's local `hye_in` working tree, which contains `data_may7_2026/projections/{Lee,Park,Moon}_projection.xlsx`, `for_hyein/projection/deliverable/reference_consensus_embeddings.npz`, and `for_hyein/park_moon_results_2026-05-07_v2/all_five_variants_filtered.xlsx`.

---

### Task 1: Extraction tool + committed data (`tools/make_subset.py`)

**Files:**
- Create: `korean-pledges-demo/tools/make_subset.py`
- Create (generated, committed): `korean-pledges-demo/data/pledges_subset.csv`
- Create (generated, committed): `korean-pledges-demo/data/reference_stats.npz`
- Create (generated, committed): `korean-pledges-demo/tests/fixtures/expected_cluster6.csv`

**Interfaces:**
- Produces `data/pledges_subset.csv` with columns `sentence_id` (e.g. `Lee_0007`, president + zero-padded source row), `text_sentence`, `president`, `cluster` (1-indexed, always 6), `D1`..`D18`.
- Produces `data/reference_stats.npz` with keys: `mu_ref` (18,), `cov_ref` (18,18), `loo_mahal_d2` (n_ref,) sorted ascending, `loo_eucl_d` (n_ref,) sorted ascending, `n_ref` (scalar int), `cluster_1idx` (scalar int, 6). All float64 except the ints.
- Produces `tests/fixtures/expected_cluster6.csv` with columns `sentence_id`, `keep_mahalanobis_pooled` (bool), `keep_euclidean_pooled` (bool) — extracted from the study's per-point results, no text.

- [ ] **Step 1: Scaffold the directory and write the extraction tool**

`korean-pledges-demo/tools/make_subset.py`:

```python
"""One-time extraction of the demo subset from the private source corpus.

Reads the three presidential projection files, the reference consensus
embeddings, and the study's per-point five-variant results; writes the
committed demo data files. The source corpus is NOT distributed with this
repo — this tool exists so the published files are reproducible for anyone
with access to the private working tree.

Inputs (via --source-dir, the private working tree):
  data_may7_2026/projections/{Lee,Park,Moon}_projection.xlsx
  for_hyein/projection/deliverable/reference_consensus_embeddings.npz
  for_hyein/park_moon_results_2026-05-07_v2/all_five_variants_filtered.xlsx

Outputs (side effects — writes into the repo):
  data/pledges_subset.csv            real sentences, complete cluster-6 slice
  data/reference_stats.npz           derived reference statistics, no text
  tests/fixtures/expected_cluster6.csv  per-point expected keep decisions

Every output is deterministic. Fails loudly on any schema surprise.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PRESIDENTS = ("Lee", "Park", "Moon")
DIM_COLS = [f"D{i}" for i in range(1, 19)]
TARGET_CLUSTER_1IDX = 6
EXPECTED_N = 218  # study ground truth for cluster 6
KEEP_COLS = ["sentence_id", "text_sentence", "president", "cluster", *DIM_COLS]


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
        missing = [c for c in ("text_sentence", "cluster_k", *DIM_COLS) if c not in df.columns]
        if missing:
            raise ValueError(f"{path.name}: missing expected columns {missing}")
        df = df.reset_index(drop=True)
        df["sentence_id"] = [f"{president}_{i:04d}" for i in df.index]
        df["president"] = president
        frames.append(df)
    oos = pd.concat(frames, ignore_index=True)
    cluster_min = int(oos["cluster_k"].min())
    if cluster_min == 0:
        oos["cluster"] = oos["cluster_k"].astype(int) + 1
    elif cluster_min == 1:
        oos["cluster"] = oos["cluster_k"].astype(int)
    else:
        raise ValueError(f"cannot infer cluster indexing: min cluster_k = {cluster_min}")
    return oos


def get_reference_stats(npz_path: Path, cluster_1idx: int) -> dict[str, np.ndarray]:
    """Derive per-cluster reference statistics from the consensus embeddings.

    Returns mu_ref, cov_ref, and the sorted leave-one-out Mahalanobis-D^2 and
    Euclidean distance distributions for the target cluster. LOO means: for
    each reference point j in the cluster, distance of x_j to the centroid and
    covariance estimated WITHOUT x_j.
    """
    z = np.load(npz_path)
    for key in ("consensus_18d", "cluster_labels"):
        if key not in z.files:
            raise KeyError(f"{npz_path.name}: missing key {key}")
    coords = z["consensus_18d"].astype(np.float64)
    labels = np.asarray(z["cluster_labels"]).astype(int)
    labels_1idx = labels + 1 if labels.min() == 0 else labels
    points = coords[labels_1idx == cluster_1idx]
    n_ref = points.shape[0]
    if n_ref <= coords.shape[1] + 1:
        raise ValueError(
            f"cluster {cluster_1idx}: n_ref={n_ref} too small for a "
            f"non-singular {coords.shape[1]}-d covariance"
        )
    loo_mahal_d2 = np.empty(n_ref)
    loo_eucl_d = np.empty(n_ref)
    for j in range(n_ref):
        rest = np.delete(points, j, axis=0)
        mu_j = rest.mean(axis=0)
        cov_j = np.cov(rest, rowvar=False)
        diff = points[j] - mu_j
        loo_mahal_d2[j] = float(diff @ np.linalg.inv(cov_j) @ diff)
        loo_eucl_d[j] = float(np.linalg.norm(diff))
    return {
        "mu_ref": points.mean(axis=0),
        "cov_ref": np.cov(points, rowvar=False),
        "loo_mahal_d2": np.sort(loo_mahal_d2),
        "loo_eucl_d": np.sort(loo_eucl_d),
        "n_ref": np.asarray(n_ref),
        "cluster_1idx": np.asarray(cluster_1idx),
    }


def get_expected_decisions(xlsx_path: Path, subset: pd.DataFrame) -> pd.DataFrame:
    """Extract per-point expected keep flags for the two headline variants.

    Matches the study's per-point results to the subset by (president,
    text_sentence, cluster). Raises if any subset sentence cannot be matched
    exactly once — silent fuzziness here would poison the regression fixture.
    Returns a frame with sentence_id + two boolean columns, no text.
    """
    ref = pd.read_excel(xlsx_path)
    needed = ["text_sentence", "president", "Mahalanobis + pooled correction",
              "Euclidean + pooled correction"]
    missing = [c for c in needed if c not in ref.columns]
    if missing:
        raise ValueError(
            f"{xlsx_path.name}: missing expected columns {missing}; "
            f"inspect actual columns and update this tool deliberately: {list(ref.columns)}"
        )
    merged = subset.merge(
        ref[needed].drop_duplicates(subset=["president", "text_sentence"]),
        on=["president", "text_sentence"],
        how="left",
        validate="many_to_one",
    )
    unmatched = merged["Mahalanobis + pooled correction"].isna()
    if unmatched.any():
        raise ValueError(
            f"{int(unmatched.sum())} subset sentences not found in {xlsx_path.name}; "
            "refusing to write a partial fixture"
        )
    out = pd.DataFrame({
        "sentence_id": merged["sentence_id"],
        "keep_mahalanobis_pooled": merged["Mahalanobis + pooled correction"].astype(bool),
        "keep_euclidean_pooled": merged["Euclidean + pooled correction"].astype(bool),
    })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True,
                        help="private source working tree (not distributed)")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]

    oos = get_oos_frame(args.source_dir)
    subset = oos[oos["cluster"] == TARGET_CLUSTER_1IDX][KEEP_COLS].reset_index(drop=True)
    if len(subset) != EXPECTED_N:
        raise ValueError(
            f"cluster {TARGET_CLUSTER_1IDX} slice has {len(subset)} rows, "
            f"expected {EXPECTED_N} (study ground truth) — reconcile before writing"
        )

    stats = get_reference_stats(
        args.source_dir / "for_hyein" / "projection" / "deliverable"
        / "reference_consensus_embeddings.npz",
        TARGET_CLUSTER_1IDX,
    )
    expected = get_expected_decisions(
        args.source_dir / "for_hyein" / "park_moon_results_2026-05-07_v2"
        / "all_five_variants_filtered.xlsx",
        subset,
    )

    (repo / "data").mkdir(exist_ok=True)
    (repo / "tests" / "fixtures").mkdir(parents=True, exist_ok=True)
    subset.to_csv(repo / "data" / "pledges_subset.csv", index=False)
    np.savez(repo / "data" / "reference_stats.npz", **stats)
    expected.to_csv(repo / "tests" / "fixtures" / "expected_cluster6.csv", index=False)
    kept_m = int(expected["keep_mahalanobis_pooled"].sum())
    kept_e = int(expected["keep_euclidean_pooled"].sum())
    print(f"subset: {len(subset)} rows -> data/pledges_subset.csv")
    print(f"expected keeps: mahalanobis {kept_m}/{len(subset)}, euclidean {kept_e}/{len(subset)}")


if __name__ == "__main__":
    main()
```

Note the two verification gates built in: the row count must be exactly 218, and every subset sentence must match the study's per-point results exactly once. If `all_five_variants_filtered.xlsx` uses different column names than assumed here, the tool prints the actual columns — update `needed` deliberately, never fuzzily.

- [ ] **Step 2: Run the tool against the private corpus**

```bash
cd korean-pledges-demo  # create it first: mkdir -p korean-pledges-demo/{tools,data,tests/fixtures}
uv pip install -q -p ../.venv numpy pandas scipy pydantic openpyxl pytest
env -u PYTHONPATH ../.venv/bin/python tools/make_subset.py \
  --source-dir "$HOME/Documents/Berkeley/Research/green-narrative/hye_in"
```

Expected: `subset: 218 rows`, `expected keeps: mahalanobis 68/218, euclidean 161/218`. Those two counts are the study's ground truth; if either differs, STOP — inspect the xlsx column semantics (keep flags may be stored as KEEP/REMOVE strings rather than booleans; if so, map explicitly and re-run) before any data file is committed.

- [ ] **Step 3: Sanity-check the committed files**

```bash
env -u PYTHONPATH ../.venv/bin/python - <<'PY'
import numpy as np, pandas as pd
df = pd.read_csv("data/pledges_subset.csv")
assert list(df.columns) == ["sentence_id", "text_sentence", "president", "cluster"] + [f"D{i}" for i in range(1, 19)], df.columns
assert len(df) == 218 and set(df["cluster"]) == {6}
z = np.load("data/reference_stats.npz")
assert set(z.files) == {"mu_ref", "cov_ref", "loo_mahal_d2", "loo_eucl_d", "n_ref", "cluster_1idx"}
print("n_ref =", int(z["n_ref"]), "| subset OK")
PY
```

- [ ] **Step 4: Commit**

```bash
git add korean-pledges-demo/tools korean-pledges-demo/data korean-pledges-demo/tests/fixtures
git commit -m "feat(korean-pledges-demo): add real cluster-6 pledge subset and extraction tool

Complete slice of the 218 out-of-sample Forest Bioenergy pledge sentences
(text, president, 18-d coordinates only; district/party metadata deliberately
excluded) plus derived reference statistics and the study's per-point keep
decisions as a regression fixture. The extraction tool requires the private
source corpus and exists for reproducibility; the corpus is not distributed."
```

---

### Task 2: Filter module (`src/filter_pledges.py`), TDD against the study's per-point results

**Files:**
- Create: `korean-pledges-demo/src/filter_pledges.py`
- Create: `korean-pledges-demo/tests/test_filter_pledges.py`

**Interfaces:**
- Consumes: `data/pledges_subset.csv`, `data/reference_stats.npz`, `tests/fixtures/expected_cluster6.csv` (Task 1 shapes).
- Produces for later tasks:
  - `FilterConfig(BaseModel)` with `metric: Literal["mahalanobis", "euclidean"]`, `threshold: Literal["loo_alpha_01", "chisq_shrinkage"]`, `alpha: float = 0.01`, `shrinkage_beta: float = 0.75`.
  - `get_keep_mask(coords: np.ndarray, stats: ReferenceStats, config: FilterConfig) -> np.ndarray` (bool, per row).
  - `get_retention(csv_path: Path, npz_path: Path, config: FilterConfig) -> RetentionResult` where `RetentionResult(BaseModel)` has `kept: int`, `n: int`, `pct: float` (one decimal, `round(100 * kept / n, 1)`).
  - `get_universe_config(universes_dir: Path, universe_id: str) -> FilterConfig` — reads the ASTRA universe YAML and maps option ids to config values.
  - CLI: `python src/filter_pledges.py --universe <id> [--show-diff]` (run from `korean-pledges-demo/`).

- [ ] **Step 1: Write the failing tests**

`korean-pledges-demo/tests/test_filter_pledges.py`:

```python
"""E2E tests for the demo filter against the study's real per-point results.

Real data only: the committed subset IS the test data. No mocks.
Run from korean-pledges-demo/: env -u PYTHONPATH ../.venv/bin/python -m pytest tests/ -v
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from filter_pledges import (  # noqa: E402
    FilterConfig,
    get_reference_stats,
    get_retention,
    get_universe_config,
)

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "pledges_subset.csv"
NPZ = ROOT / "data" / "reference_stats.npz"
EXPECTED = ROOT / "tests" / "fixtures" / "expected_cluster6.csv"

MAHAL = FilterConfig(metric="mahalanobis", threshold="loo_alpha_01")
EUCL = FilterConfig(metric="euclidean", threshold="loo_alpha_01")


def test_counts_match_study_ground_truth():
    assert get_retention(CSV, NPZ, MAHAL).kept == 68
    assert get_retention(CSV, NPZ, EUCL).kept == 161


def test_pct_rounding():
    r = get_retention(CSV, NPZ, MAHAL)
    assert (r.n, r.pct) == (218, 31.2)
    assert get_retention(CSV, NPZ, EUCL).pct == 73.9


@pytest.mark.parametrize(
    "config,column",
    [(MAHAL, "keep_mahalanobis_pooled"), (EUCL, "keep_euclidean_pooled")],
)
def test_point_level_agreement_with_study(config, column):
    """Every single sentence must get the same keep/remove as the study."""
    from filter_pledges import get_keep_mask, load_subset

    df = load_subset(CSV)
    stats = get_reference_stats(NPZ)
    mask = get_keep_mask(df[[f"D{i}" for i in range(1, 19)]].to_numpy(float), stats, config)
    expected = pd.read_csv(EXPECTED)
    merged = df[["sentence_id"]].assign(got=mask).merge(expected, on="sentence_id", validate="one_to_one")
    disagree = merged[merged["got"] != merged[column]]
    assert disagree.empty, f"{len(disagree)} disagreements: {disagree['sentence_id'].tolist()[:10]}"


def test_chisq_universe_runs_and_is_between_extremes():
    cfg = FilterConfig(metric="mahalanobis", threshold="chisq_shrinkage")
    r = get_retention(CSV, NPZ, cfg)
    assert r.n == 218 and 0 < r.kept < 218


def test_universe_files_drive_the_filter():
    universes = ROOT / "analysis" / "universes"
    if not universes.is_dir():
        pytest.skip("analysis/ not built yet (Task 3)")
    assert get_universe_config(universes, "baseline") == MAHAL
    assert get_universe_config(universes, "what-if-euclidean") == EUCL


def test_unknown_universe_raises():
    with pytest.raises(FileNotFoundError):
        get_universe_config(ROOT / "analysis" / "universes", "nonexistent")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd korean-pledges-demo && env -u PYTHONPATH ../.venv/bin/python -m pytest tests/test_filter_pledges.py -v
```

Expected: collection error / ImportError — `filter_pledges` does not exist yet.

- [ ] **Step 3: Implement the filter**

`korean-pledges-demo/src/filter_pledges.py`:

```python
"""Retention filter for the Korean pledges demo.

Recomputes, live, the study's out-of-sample filter on the committed
cluster-6 slice. Pure functions; the only side effect is CLI printing.

The location-correction decision from the full study is hard-coded to its
accepted value: distances are measured from the pooled OOS centroid (the
mean of the committed cluster-6 coordinates) using the REFERENCE cluster's
covariance. Thresholds come from the reference leave-one-out distance
distribution (empirical, alpha=0.01) or the chi-squared theoretical
quantile with shrinkage covariance (beta=0.75), matching the study.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict
from scipy.stats import chi2

DIM_COLS = [f"D{i}" for i in range(1, 19)]

# ASTRA option id -> config value, per analysis/astra.yaml
METRIC_OPTIONS = {"mahalanobis": "mahalanobis", "euclidean": "euclidean"}
THRESHOLD_OPTIONS = {"loo_alpha_01": "loo_alpha_01", "chisq_shrinkage": "chisq_shrinkage"}


class FilterConfig(BaseModel):
    """One point in the demo's decision space (a universe)."""

    model_config = ConfigDict(frozen=True)
    metric: Literal["mahalanobis", "euclidean"]
    threshold: Literal["loo_alpha_01", "chisq_shrinkage"]
    alpha: float = 0.01
    shrinkage_beta: float = 0.75


class ReferenceStats(BaseModel):
    """Derived reference statistics for the demo cluster (no text)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    mu_ref: np.ndarray
    cov_ref: np.ndarray
    loo_mahal_d2: np.ndarray
    loo_eucl_d: np.ndarray
    n_ref: int
    cluster_1idx: int


class RetentionResult(BaseModel):
    """Retention summary for one universe on the committed slice."""

    kept: int
    n: int
    pct: float


def load_subset(csv_path: Path) -> pd.DataFrame:
    """Load the committed subset, failing loudly on schema drift."""
    df = pd.read_csv(csv_path)
    expected = ["sentence_id", "text_sentence", "president", "cluster", *DIM_COLS]
    if list(df.columns) != expected:
        raise ValueError(f"{csv_path.name}: columns {list(df.columns)} != expected {expected}")
    return df


def get_reference_stats(npz_path: Path) -> ReferenceStats:
    """Load the committed reference statistics, failing loudly on missing keys."""
    z = np.load(npz_path)
    needed = {"mu_ref", "cov_ref", "loo_mahal_d2", "loo_eucl_d", "n_ref", "cluster_1idx"}
    if set(z.files) != needed:
        raise KeyError(f"{npz_path.name}: keys {sorted(z.files)} != expected {sorted(needed)}")
    return ReferenceStats(
        mu_ref=z["mu_ref"], cov_ref=z["cov_ref"],
        loo_mahal_d2=z["loo_mahal_d2"], loo_eucl_d=z["loo_eucl_d"],
        n_ref=int(z["n_ref"]), cluster_1idx=int(z["cluster_1idx"]),
    )


def get_keep_mask(coords: np.ndarray, stats: ReferenceStats, config: FilterConfig) -> np.ndarray:
    """Apply one universe's filter to the slice; True = sentence retained.

    Pooled location correction: distances are measured from the pooled OOS
    centroid of the slice (complete per cluster, so identical to the study's
    per-cluster pooled centroid).
    """
    mu_oos = coords.mean(axis=0)
    diff = coords - mu_oos
    if config.threshold == "loo_alpha_01":
        if config.metric == "mahalanobis":
            d2 = np.einsum("ij,jk,ik->i", diff, np.linalg.inv(stats.cov_ref), diff)
            cutoff = float(np.quantile(stats.loo_mahal_d2, 1.0 - config.alpha))
            return d2 <= cutoff
        d = np.linalg.norm(diff, axis=1)
        cutoff = float(np.quantile(stats.loo_eucl_d, 1.0 - config.alpha))
        return d <= cutoff
    # chisq_shrinkage (defined for mahalanobis only; astra.yaml encodes this
    # with a `requires: [distance_metric.mahalanobis]` constraint)
    if config.metric != "mahalanobis":
        raise ValueError("chisq_shrinkage is only defined for the mahalanobis metric")
    cov_oos = np.cov(coords, rowvar=False)
    cov_eff = config.shrinkage_beta * stats.cov_ref + (1.0 - config.shrinkage_beta) * cov_oos
    d2 = np.einsum("ij,jk,ik->i", diff, np.linalg.inv(cov_eff), diff)
    return d2 <= float(chi2.ppf(1.0 - config.alpha, df=coords.shape[1]))


def get_retention(csv_path: Path, npz_path: Path, config: FilterConfig) -> RetentionResult:
    """Run one universe end-to-end on the committed files."""
    df = load_subset(csv_path)
    stats = get_reference_stats(npz_path)
    mask = get_keep_mask(df[DIM_COLS].to_numpy(float), stats, config)
    kept = int(mask.sum())
    return RetentionResult(kept=kept, n=len(df), pct=round(100.0 * kept / len(df), 1))


def get_universe_config(universes_dir: Path, universe_id: str) -> FilterConfig:
    """Build a FilterConfig from an ASTRA universe file — the YAML is the config.

    Accepts both selection forms the schema allows: scalar option id and
    attribution object ({option_id: ..., selected_by: ...}).
    """
    path = universes_dir / f"{universe_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no such universe: {path}")
    doc = yaml.safe_load(path.read_text())
    decisions = doc.get("decisions")
    if not isinstance(decisions, dict):
        raise ValueError(f"{path.name}: no decisions mapping")

    def get_option(decision_id: str) -> str:
        sel = decisions.get(decision_id)
        if isinstance(sel, dict):
            sel = sel.get("option_id")
        if not isinstance(sel, str):
            raise ValueError(f"{path.name}: cannot read option for decision {decision_id!r}")
        return sel

    return FilterConfig(
        metric=METRIC_OPTIONS[get_option("distance_metric")],
        threshold=THRESHOLD_OPTIONS[get_option("threshold_rule")],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one universe of the pledge filter demo.")
    parser.add_argument("--universe", default="baseline")
    parser.add_argument("--show-diff", action="store_true",
                        help="list sentences this universe retains that baseline removes")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    csv_path, npz_path = root / "data" / "pledges_subset.csv", root / "data" / "reference_stats.npz"
    universes = root / "analysis" / "universes"

    config = get_universe_config(universes, args.universe)
    result = get_retention(csv_path, npz_path, config)
    stats = get_reference_stats(npz_path)
    print(f"universe: {args.universe}   (metric={config.metric}, threshold={config.threshold})")
    print(f"cluster {stats.cluster_1idx} (Forest Bioenergy): "
          f"retained {result.kept}/{result.n} ({result.pct}%)")

    if args.show_diff and args.universe != "baseline":
        df = load_subset(csv_path)
        coords = df[DIM_COLS].to_numpy(float)
        here = get_keep_mask(coords, stats, config)
        base = get_keep_mask(coords, stats, get_universe_config(universes, "baseline"))
        extra = df[here & ~base]
        print(f"\nretained here but removed by baseline: {len(extra)} sentences; first 5:")
        for _, row in extra.head(5).iterrows():
            print(f"  [{row.sentence_id}] {row.text_sentence[:80]}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests**

```bash
cd korean-pledges-demo && env -u PYTHONPATH ../.venv/bin/python -m pytest tests/test_filter_pledges.py -v
```

Expected: all pass except `test_universe_files_drive_the_filter` (skipped — analysis/ arrives in Task 3). If `test_point_level_agreement_with_study` fails: the LOO/quantile conventions differ from the study's. Reconcile in THIS bounded order, re-running the point-level test after each change, and never touching the expected fixture: (1) quantile method — try `np.quantile(..., method="higher")` then `method="lower"`; (2) covariance normalization — `np.cov(..., ddof=0)` in both the tool and the module; (3) strict vs non-strict cutoff (`<` vs `<=`); (4) pooled centroid over the full corpus rather than the slice — if this is the culprit the slice-completeness premise still holds only if counts match; investigate with the source corpus via the extraction tool, and record whatever convention finally matches as comments in both files. If none of these reconcile point-level, STOP and surface the disagreement rather than shipping approximate numbers.

- [ ] **Step 5: pyright + commit**

```bash
cd korean-pledges-demo && uvx pyright src/ tools/ tests/   # basic mode, expect 0 errors
git add korean-pledges-demo/src korean-pledges-demo/tests
git commit -m "feat(korean-pledges-demo): filter module reproducing the study's per-point decisions

Mahalanobis/Euclidean metrics with pooled location correction and empirical
LOO (alpha=0.01) or chi-squared shrinkage (beta=0.75) thresholds. Tests pin
point-level agreement with the study's five-variant results (68/218 and
161/218 on the Forest Bioenergy cluster), so any drift in conventions
(quantile method, covariance ddof, cutoff strictness) fails loudly."
```

---

### Task 3: The attributed analysis (`analysis/astra.yaml` + three universes)

**Files:**
- Create: `korean-pledges-demo/analysis/astra.yaml`
- Create: `korean-pledges-demo/analysis/universes/baseline.yaml`
- Create: `korean-pledges-demo/analysis/universes/what-if-euclidean.yaml`
- Create: `korean-pledges-demo/analysis/universes/what-if-chisq.yaml`

**Interfaces:**
- Consumes: option ids `distance_metric.{mahalanobis,euclidean}`, `threshold_rule.{loo_alpha_01,chisq_shrinkage}` — must match `METRIC_OPTIONS` / `THRESHOLD_OPTIONS` in Task 2 exactly.
- Produces: the three universe ids consumed by `run_demo.sh` and `get_universe_config`: `baseline`, `what-if-euclidean`, `what-if-chisq`.

- [ ] **Step 1: Get the chi-squared shrinkage number from the pipeline**

```bash
cd korean-pledges-demo && env -u PYTHONPATH ../.venv/bin/python - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, "src")
from filter_pledges import FilterConfig, get_retention
r = get_retention(Path("data/pledges_subset.csv"), Path("data/reference_stats.npz"),
                  FilterConfig(metric="mahalanobis", threshold="chisq_shrinkage"))
print(f"chisq_shrinkage on cluster 6: {r.kept}/{r.n} ({r.pct}%)")
PY
```

Record the printed `kept/n (pct%)`. In Step 2 below, replace every `«CHISQ»` marker with these actual values. Judgment call defined in the spec: if the chisq number is undramatic (between 31.2% and 40%, i.e. barely above baseline), flag it to the user with the option of adding a second cluster — do not silently proceed.

- [ ] **Step 2: Write `analysis/astra.yaml`**

The `«CHISQ»` markers below MUST be replaced with the values printed in Step 1 before this file is written; grep the final file for `«` and fail the task if any remain.

```yaml
# ASTRA Analysis Specification — Korean pledges actor-attribution demo
#
# A simplified, runnable slice of a real study: filtering out-of-sample
# Korean forest-policy pledge sentences against a reference corpus. Every
# number quoted below is recomputed live by src/filter_pledges.py from the
# committed data (tests/test_demo_numbers.py enforces this).
#
# Provenance: the exclusions encoded here were logged in TRACE session
# trace_20260509_305aaf (2026-05-09). The full study also varied a third
# decision (out-of-sample centroid correction); this demo hard-codes its
# accepted value (pooled) — see README.
version: "0.0.13"
name: "korean_pledges_actor_demo"
container: python:3.12-slim
description: |
  Decides which of the 218 out-of-sample Forest Bioenergy pledge sentences
  are retained as genuinely belonging to the reference cluster. Retention
  is the contested quantity: both excluded options below produce a HIGHER
  retention than the accepted configuration, so every exclusion was a
  decision to keep the less tempting number.

# Who was on this analysis's decisions (RFC-0003 actor layer).
actors:
  oliver:
    type: human
  claude_code:
    type: agent
    # Model id supplied by the researcher; the original working sessions
    # predate model-id capture in the provenance record.
    model: claude-opus-4-8
    harness: claude-code
    version: "2026-05"

inputs:
  - id: pledges_subset
    type: data
    source: "data/pledges_subset.csv"
    description: >-
      Complete slice of the 218 out-of-sample pledge sentences assigned to
      the Forest Bioenergy reference cluster (three presidencies; Korean
      text plus 18-d projected coordinates).

  - id: reference_stats
    type: data
    source: "data/reference_stats.npz"
    description: >-
      Derived statistics of the 905-sentence reference planning corpus for
      this cluster: centroid, covariance, and leave-one-out distance
      distributions. No reference text is distributed.

outputs:
  - id: retained_sentences
    type: data
    description: Pledge sentences admitted to the reference cluster.
    decisions: [distance_metric, threshold_rule]
    recipe:
      command: >-
        python src/filter_pledges.py --universe {universe}

  - id: retention_rate
    type: metric
    description: >-
      Share of the 218 sentences retained. Accepted configuration: 68/218
      (31.2%). Both excluded options land far higher — that is the point.
    inputs: [retained_sentences]
    recipe:
      command: >-
        python src/filter_pledges.py --universe {universe}

decisions:
  distance_metric:
    label: "Distance metric for cluster membership"
    rationale: >-
      Decides whether the cluster's anisotropic shape counts when judging
      whether a pledge belongs. Shape adaptation is load-bearing here, not
      cosmetic: it is what keeps off-topic industrial-policy pledges out.
    default: mahalanobis
    options:
      mahalanobis:
        label: "Mahalanobis distance"
        description: >-
          Uses the reference cluster's covariance; retains 68/218 (31.2%).
          The harder-to-defend number, kept because it is the honest one.
      euclidean:
        label: "Euclidean distance"
        description: >-
          Ignores cluster shape; retains 161/218 (73.9%) on the same
          sentences with the same threshold rule.
        excluded: true
        proposed_by: claude_code
        excluded_by: {actor: oliver, role: validation}
        excluded_at: "2026-05-09"
        exclusion_rationale: >-
          The tempting number: more than twice the retention, from the
          simplest metric. Rejected because qualitative reading showed the
          extra sentences are off-topic (general industrial policy, not
          forest bioenergy) — they survive only because Euclidean ignores
          the cluster's elongated shape.
        excluded_reason: >-
          Retains 161/218 (73.9%) vs 68/218 (31.2%) for Mahalanobis.
          Qualitative review of the additionally admitted sentences found
          general industrial-policy content (defense industry, electronics,
          urban industrial complexes) that lands near the centroid only
          along the cluster's dominant axis. A 42.7-point retention jump
          from ignoring shape is the filter failing at its one job.

  threshold_rule:
    label: "Distance threshold"
    rationale: >-
      Sets the cut point, and therefore governs retention most directly —
      the decision a reviewer will read as tuned if it is not principled.
    default: loo_alpha_01
    options:
      loo_alpha_01:
        label: "Empirical leave-one-out quantile, alpha = 0.01"
        description: >-
          99th percentile of the reference leave-one-out distance
          distribution — the threshold carries the reference corpus's own
          estimation noise.
      chisq_shrinkage:
        label: "Chi-squared theoretical threshold, shrinkage covariance beta = 0.75"
        description: >-
          Blends reference and out-of-sample covariance (beta = 0.75) and
          cuts at the theoretical chi-squared quantile; retains «CHISQ».
        requires: [distance_metric.mahalanobis]
        excluded: true
        proposed_by: claude_code
        excluded_by: {actor: oliver, role: validation}
        excluded_at: "2026-05-09"
        exclusion_rationale: >-
          Also a higher number, rejected anyway: beta = 0.75 has no
          principled basis, and the variant changes the threshold source
          and the covariance source at once, so nothing can be attributed.
        excluded_reason: >-
          Retains «CHISQ» on this cluster. Rejected on three grounds: no
          principled basis for beta = 0.75 over 0.6 or 0.85; threshold
          source and covariance source change simultaneously, so the
          retention shift cannot be attributed to either; and the conformal
          coverage guarantee does not extend to a covariance estimated on
          the test corpus.
```

- [ ] **Step 3: Write the three universe files**

`analysis/universes/baseline.yaml` (attribution-object form):

```yaml
id: baseline
description: "The study's accepted configuration: shape-aware and conservative."

decisions:
  distance_metric:
    option_id: mahalanobis
    selected_by: {actor: oliver, role: methodology}
    reviewed_by: {actor: claude_code, role: validation}
  threshold_rule:
    option_id: loo_alpha_01
    selected_by: {actor: oliver, role: methodology}
```

Role-legality note: `role: validation` on an agent is unverified against the
schema's `AgentRole` enum. Check with `env -u PYTHONPATH ../.venv/bin/astra
spec actor` before validating; if validation is human-only, use a legal agent
role from that output, or drop the `reviewed_by` line (it is optional).

`analysis/universes/what-if-euclidean.yaml` (scalar shorthand):

```yaml
id: what_if_euclidean
description: "The tempting number: ignore cluster shape, watch retention jump."

decisions:
  distance_metric: euclidean
  threshold_rule: loo_alpha_01
```

`analysis/universes/what-if-chisq.yaml` (scalar shorthand):

```yaml
id: what_if_chisq
description: "The other tempting number: blended covariance, theoretical cutoff."

decisions:
  distance_metric: mahalanobis
  threshold_rule: chisq_shrinkage
```

Note: universe FILE names use hyphens (`what-if-euclidean.yaml`) because `run_demo.sh --universe what-if-euclidean` resolves by filename; the `id:` fields inside use underscores to satisfy the schema's `^[a-z][a-z0-9_]*$` id pattern. Verify `astra validate` accepts this; if it requires id == filename, rename the files to underscores and update `run_demo.sh` and `DEMO_SCRIPT.md` accordingly.

- [ ] **Step 4: Validate everything through the fork toolchain**

```bash
./install_and_validate.sh korean-pledges-demo/analysis/astra.yaml
```

Expected: analysis validates, then each universe in `analysis/universes/` validates against it automatically. Any actor-layer error (unknown actor ref, illegal role for actor type, `excluded_by` without `excluded: true`) means the YAML above drifted from the schema — fix the YAML, not the toolchain.

- [ ] **Step 5: Run the previously-skipped test and commit**

```bash
cd korean-pledges-demo && env -u PYTHONPATH ../.venv/bin/python -m pytest tests/test_filter_pledges.py -v
```

Expected: `test_universe_files_drive_the_filter` now runs and passes (no skips).

```bash
git add korean-pledges-demo/analysis
git commit -m "feat(korean-pledges-demo): attributed two-decision ASTRA analysis and universes

Two decisions (distance metric, threshold rule), both excluded options
attributed: agent proposed, human excluded, dated, with rationale. The
baseline universe uses attribution-object selections; the what-if universes
use scalar shorthand. All quoted retention numbers are pipeline-computed."
```

---

### Task 4: `run_demo.sh`

**Files:**
- Create: `korean-pledges-demo/run_demo.sh` (chmod +x)

**Interfaces:**
- Consumes: repo venv `.venv/` (from `install_and_validate.sh`), `src/filter_pledges.py` CLI, universe ids from Task 3.
- Produces: the single command surface the README and DEMO_SCRIPT reference.

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# Run the Korean pledges demo: filter + ASTRA validation + actor display.
#
# Usage (from korean-pledges-demo/):
#   ./run_demo.sh                        # baseline universe
#   ./run_demo.sh -u what-if-euclidean   # a what-if universe, with diff
#   ./run_demo.sh --validate             # astra validate + info only
#
# Requires ../.venv from ../install_and_validate.sh; installs the demo's
# Python deps into it idempotently.

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/../.venv"
[ -x "$VENV/bin/python" ] || {
  echo "error: $VENV missing — run ../install_and_validate.sh first" >&2; exit 1; }

uv pip install --quiet -p "$VENV" numpy pandas scipy pydantic pyyaml openpyxl pytest

UNIVERSE="baseline"; VALIDATE_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    -u|--universe) UNIVERSE="$2"; shift 2 ;;
    --validate) VALIDATE_ONLY=1; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "error: unknown argument $1" >&2; exit 1 ;;
  esac
done

run() { env -u PYTHONPATH "$VENV/bin/$1" "${@:2}"; }

if [ "$VALIDATE_ONLY" = 1 ]; then
  run astra validate "$HERE/analysis/astra.yaml"
  for u in "$HERE"/analysis/universes/*.yaml; do
    run astra validate "$u" -a "$HERE/analysis/astra.yaml"
  done
  run astra info "$HERE/analysis/astra.yaml"
  exit 0
fi

if [ "$UNIVERSE" = "baseline" ]; then
  run python "$HERE/src/filter_pledges.py" --universe "$UNIVERSE"
else
  run python "$HERE/src/filter_pledges.py" --universe "$UNIVERSE" --show-diff
fi
```

- [ ] **Step 2: Exercise all paths**

```bash
cd korean-pledges-demo && chmod +x run_demo.sh
./run_demo.sh                        # expect: retained 68/218 (31.2%)
./run_demo.sh -u what-if-euclidean   # expect: 161/218 (73.9%) + 5 Korean sentences
./run_demo.sh -u what-if-chisq       # expect: the Task 3 chisq number
./run_demo.sh --validate             # expect: green validations + actor rendering in info
./run_demo.sh -u nonexistent && echo "BUG: should have failed" || echo "fails loudly: OK"
```

- [ ] **Step 3: Commit**

```bash
git add korean-pledges-demo/run_demo.sh
git commit -m "feat(korean-pledges-demo): single-command demo runner"
```

---

### Task 5: The invariant guard (`tests/test_demo_numbers.py`)

**Files:**
- Create: `korean-pledges-demo/tests/test_demo_numbers.py`

**Interfaces:**
- Consumes: `analysis/astra.yaml` text, Task 2's `get_retention`/`get_universe_config`, the repo venv's `astra` CLI.

- [ ] **Step 1: Write the tests (they should pass immediately — the guard exists for the future)**

```python
"""The honesty invariant: every number quoted in analysis/astra.yaml is a
number the pipeline computes from the committed data, and the analysis
always validates through the fork toolchain.

Run from korean-pledges-demo/: env -u PYTHONPATH ../.venv/bin/python -m pytest tests/ -v
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from filter_pledges import get_retention, get_universe_config  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "pledges_subset.csv"
NPZ = ROOT / "data" / "reference_stats.npz"
YAML_TEXT = (ROOT / "analysis" / "astra.yaml").read_text()
UNIVERSE_IDS = ["baseline", "what-if-euclidean", "what-if-chisq"]


def get_computed_values() -> tuple[set[str], set[str]]:
    """Return (percentages, kept/n fractions) the pipeline computes."""
    pcts, fracs = set(), set()
    for uid in UNIVERSE_IDS:
        r = get_retention(CSV, NPZ, get_universe_config(ROOT / "analysis" / "universes", uid))
        pcts.add(f"{r.pct}%")
        fracs.add(f"{r.kept}/{r.n}")
    return pcts, fracs


def test_every_quoted_percentage_is_pipeline_computed():
    pcts, _ = get_computed_values()
    quoted = set(re.findall(r"\d+\.\d+%", YAML_TEXT))
    stray = quoted - pcts
    assert not stray, f"astra.yaml quotes percentages the pipeline does not compute: {sorted(stray)}"


def test_every_quoted_fraction_is_pipeline_computed():
    _, fracs = get_computed_values()
    quoted = set(re.findall(r"\b\d+/218\b", YAML_TEXT))
    stray = quoted - fracs
    assert not stray, f"astra.yaml quotes fractions the pipeline does not compute: {sorted(stray)}"


def test_headline_numbers_are_present():
    """The two demo-critical numbers must actually appear in the YAML."""
    assert "31.2%" in YAML_TEXT and "73.9%" in YAML_TEXT
    assert "68/218" in YAML_TEXT and "161/218" in YAML_TEXT


@pytest.mark.parametrize("target", ["analysis/astra.yaml"] +
                         [f"analysis/universes/{u}.yaml" for u in UNIVERSE_IDS])
def test_astra_validate_green(target):
    astra = ROOT.parent / ".venv" / "bin" / "astra"
    assert astra.exists(), "repo venv missing — run ../install_and_validate.sh first"
    cmd = [str(astra), "validate", str(ROOT / target)]
    if "universes" in target:
        cmd += ["-a", str(ROOT / "analysis" / "astra.yaml")]
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, f"{target}: {proc.stdout}\n{proc.stderr}"
```

- [ ] **Step 2: Run the full suite**

```bash
cd korean-pledges-demo && env -u PYTHONPATH ../.venv/bin/python -m pytest tests/ -v
```

Expected: everything passes, zero skips. If a stray number surfaces: fix `astra.yaml` to quote only computed values (or fix the pipeline bug) — never widen the regex to let it through.

- [ ] **Step 3: Deliberately break it, watch it fail, restore**

Edit `analysis/astra.yaml`: change `73.9%` to `74.0%`. Run the suite — `test_every_quoted_percentage_is_pipeline_computed` must FAIL naming `74.0%`. Revert with `git checkout korean-pledges-demo/analysis/astra.yaml`. This proves the guard guards.

- [ ] **Step 4: Commit**

```bash
git add korean-pledges-demo/tests/test_demo_numbers.py
git commit -m "test(korean-pledges-demo): enforce that quoted numbers are pipeline-computed

Any percentage or kept/218 fraction in the analysis file that the pipeline
does not itself produce fails the suite, as does any validation regression
in the analysis or universe files."
```

---

### Task 6: `README.md` + `DEMO_SCRIPT.md`

**Files:**
- Create: `korean-pledges-demo/README.md`
- Create: `korean-pledges-demo/DEMO_SCRIPT.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# Korean pledges: a real actor-attribution example

The iris example next door is a toy. This one is a slice of a real study,
with the real failure mode the actor layer exists for.

## The 90-second story

A dissertation pipeline filters Korean presidential/district election
pledge sentences, deciding which ones genuinely belong to a forest-policy
topic cluster. This demo ships the complete slice for one cluster
(Forest Bioenergy): 218 real sentences with their 18-d embedding
coordinates.

The accepted filter retains **68/218 (31.2%)**. Every alternative that was
considered retains MORE — the simplest one more than twice as much — and
qualitative reading showed the extra sentences are off-topic (defense
industry, electronics, urban industrial complexes). Each alternative was
proposed by the AI assistant during analysis and excluded by the human
researcher. A plain ASTRA file records *that* they were excluded and why.
The actor layer records *who* proposed them, *who* excluded them, and
*when* — which is exactly what a methods reviewer, a committee, or a
future collaborator needs when the tempting number resurfaces.

## Run it

    ../install_and_validate.sh          # once: build the shared venv
    ./run_demo.sh                       # baseline: 68/218 (31.2%)
    ./run_demo.sh -u what-if-euclidean  # 161/218 (73.9%) + the sentences it lets in
    ./run_demo.sh -u what-if-chisq      # the other tempting number
    ./run_demo.sh --validate            # astra validate + actor-attributed info

Tests (`env -u PYTHONPATH ../.venv/bin/python -m pytest tests/ -v`) enforce
two things: point-level agreement with the study's recorded per-sentence
decisions, and that every number quoted in `analysis/astra.yaml` is one
this pipeline computes from `data/`.

## What was simplified

- The full study varies a third decision (out-of-sample centroid
  correction); this demo hard-codes its accepted value (pooled).
- The full study covers 8 clusters and 1,662 sentences; this demo ships
  the one cluster where the metric choice matters most. The committed
  slice is COMPLETE for that cluster, so the numbers here are the study's
  real per-cluster values, not approximations.

## Data

`data/pledges_subset.csv`: sentence text (Korean), president, cluster,
D1..D18 — district/party metadata deliberately not included.
`data/reference_stats.npz`: derived reference-corpus statistics (centroid,
covariance, leave-one-out distance distributions); no reference text.
The source corpus is private to the originating research group;
`tools/make_subset.py` regenerates these files for anyone with access.
Decision provenance: TRACE session trace_20260509_305aaf (2026-05-09).
```

- [ ] **Step 2: Write `DEMO_SCRIPT.md`**

```markdown
# Live-demo script

Prompts to type into an agentic coding assistant (e.g. Claude Code opened
at the repo root), in order. Prereq: `./install_and_validate.sh` has been
run once. The committed `analysis/astra.yaml` is the reference output for
prompt 4 — if the generated file differs, diff them on screen; that
comparison is itself a good demo beat.

**1 — Run the real pipeline**

> Read korean-pledges-demo/README.md, then run ./run_demo.sh in
> korean-pledges-demo. Report what was filtered and why that number.

Expected: 68/218 (31.2%) retained, shape-aware metric, conservative threshold.

**2 — Show the real problem**

> Now run ./run_demo.sh -u what-if-euclidean. Translate the first three
> Korean sentences it retains that the baseline removes, and say whether
> they belong in a "Forest Bioenergy" topic cluster.

Expected: retention jumps to 161/218 (73.9%); the translated sentences are
about defense industry / electronics / industrial complexes — off-topic.
The tempting number admits junk.

**3 — Generate the decision record**

> Write an ASTRA analysis spec (schema version 0.0.13) for this filter in
> a scratch file: decisions distance_metric (mahalanobis, euclidean) and
> threshold_rule (loo_alpha_01, chisq_shrinkage), with the options we just
> compared, the rejected ones marked excluded with excluded_reason quoting
> the numbers you just computed.

Expected: a valid plain ASTRA file — decision space captured, but no
record of WHO ruled anything out.

**4 — Attribute it**

> Add the RFC-0003 actor layer: register actors oliver (human) and
> claude_code (agent, model claude-opus-4-8, harness claude-code). The
> assistant proposed euclidean and chisq_shrinkage during the original
> analysis; the researcher excluded both on 2026-05-09. Attribute each
> exclusion (proposed_by, excluded_by, excluded_at) and add a one-sentence
> exclusion_rationale to each.

Expected: the same file, now answering who/when/why — compare with the
committed korean-pledges-demo/analysis/astra.yaml.

**5 — Prove it**

> Validate the file with the astra CLI from .venv, then run astra info on
> it and show me who excluded what.

Expected: validation green (the actor layer is enforced, not decorative);
`astra info` renders the actor registry and the attributed exclusions.
```

- [ ] **Step 3: Commit**

```bash
git add korean-pledges-demo/README.md korean-pledges-demo/DEMO_SCRIPT.md
git commit -m "docs(korean-pledges-demo): demo story and live chat script"
```

---

### Task 7: Final gates, spec acceptance, PR

- [ ] **Step 1: Full acceptance run (spec's acceptance criteria, verbatim)**

```bash
./install_and_validate.sh korean-pledges-demo/analysis/astra.yaml   # + universes
cd korean-pledges-demo
env -u PYTHONPATH ../.venv/bin/python -m pytest tests/ -v            # all green, no skips
./run_demo.sh && ./run_demo.sh -u what-if-euclidean && ./run_demo.sh -u what-if-chisq
uvx pyright src/ tools/ tests/                                       # 0 errors (basic mode)
```

Cross-check the three printed retention lines against `analysis/astra.yaml` by eye — the tests already enforce it, the eyeball is for the demo dry-run.

- [ ] **Step 2: Push branch and open the PR**

```bash
git push -u origin feature/korean-pledges-demo
gh pr create --repo Fosowl/actor_attributions_demo_astra_lightcone \
  --title "feat: Korean pledges real-data actor-attribution demo" \
  --body "$(cat <<'EOF'
## Summary

Adds `korean-pledges-demo/`: a runnable real-data companion to the iris
example. A complete 218-sentence slice of a real Korean forest-policy
filtering study, a filter that recomputes the study's retention numbers
live from the committed data, an attributed two-decision ASTRA analysis
(RFC-0003 actor layer), and a live-demo chat script.

## Why

The iris example shows the actor layer's syntax; this shows its purpose.
Every excluded option in the analysis retains MORE sentences than the
accepted one — the record of who proposed each tempting number and who
excluded it is the difference between a defensible methods section and an
unattributable tuning history.

## Verification

- Point-level regression: the filter reproduces the study's recorded
  per-sentence keep/remove decisions exactly (68/218 and 161/218).
- Invariant test: every percentage and fraction quoted in
  `analysis/astra.yaml` is recomputed by the pipeline from `data/`.
- `astra validate` green on the analysis and all three universes via
  `install_and_validate.sh`; pyright basic clean.
EOF
)"
```

Before submitting, re-read the PR body against the self-containment rules (no session narrative, no AI-attribution footers, no internal labels).

---

## Execution notes

- Tasks run in order; Tasks 3-6 each depend on their predecessors' interfaces.
- TRACE: log one decision/contribution per milestone commit (max 1-2 trace calls per turn), in the active session.
- After Task 7, run the requested ~3 adversarial verification passes (openai-adversarial-review skill) over the finished demo before reporting completion.
