"""Retention filter for the Korean pledges demo.

Recomputes, live, the study's out-of-sample filter on the committed
cluster-6 slice. Pure functions; the only side effect is CLI printing.

The manuscript's accepted filter is EUCLIDEAN + pooled location correction
at alpha = 0.01. Mahalanobis was the theoretically assumed choice (shape
adaptation) and was excluded after inspection; it survives here as a
diagnostic replay so the demo can show what it would have discarded.

Conventions (verified point-level against the study's per-sentence keep
decisions; enforced by tests/test_filter_pledges.py):
- Distances are measured from the pledge slice's own pooled centroid; the
  reference cluster supplies shape and threshold.
- Thresholds are the 99th percentile (NumPy linear quantile) of the
  reference leave-one-out distance distribution for the matching metric.
- The reference covariance for the Mahalanobis replay is ridged
  (np.cov + 1e-6*I, the study's stabilizer — carried inside
  data/reference_stats.npz).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict

DIM_COLS = [f"D{i}" for i in range(1, 19)]

# ASTRA option id -> config value, per analysis/astra.yaml
METRIC_OPTIONS = {"euclidean": "euclidean", "mahalanobis": "mahalanobis"}

# Counterfactual presets. These are deliberately NOT committed as ASTRA
# universe files: the toolchain refuses a universe that selects an excluded
# option (EXCLUDED_OPTION_SELECTED), which is exactly the enforcement this
# demo showcases. The counterfactuals therefore run through ASTRA's other
# form — explicit decision values, as in the analysis recipe commands.
WHAT_IF_PRESETS: dict[str, dict[str, str]] = {
    "what-if-mahalanobis": {"metric": "mahalanobis"},
}


class FilterConfig(BaseModel):
    """One point in the demo's decision space (a universe or replay)."""

    model_config = ConfigDict(frozen=True)
    metric: Literal["euclidean", "mahalanobis"]
    alpha: float = 0.01


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
        mu_ref=z["mu_ref"],
        cov_ref=z["cov_ref"],
        loo_mahal_d2=z["loo_mahal_d2"],
        loo_eucl_d=z["loo_eucl_d"],
        n_ref=int(z["n_ref"]),
        cluster_1idx=int(z["cluster_1idx"]),
    )


def get_keep_mask(
    coords: np.ndarray, stats: ReferenceStats, config: FilterConfig
) -> np.ndarray:
    """Apply one configuration's filter to the slice; True = sentence retained.

    Pooled location correction: distances are measured from the pooled OOS
    centroid of the slice (complete per cluster, so identical to the study's
    per-cluster pooled centroid).
    """
    mu_oos = coords.mean(axis=0)
    diff = coords - mu_oos
    if config.metric == "euclidean":
        d = np.linalg.norm(diff, axis=1)
        cutoff = float(np.quantile(stats.loo_eucl_d, 1.0 - config.alpha))
        return d <= cutoff
    d2 = np.einsum("ij,jk,ik->i", diff, np.linalg.inv(stats.cov_ref), diff)
    cutoff = float(np.quantile(stats.loo_mahal_d2, 1.0 - config.alpha))
    return d2 <= cutoff


def get_retention(csv_path: Path, npz_path: Path, config: FilterConfig) -> RetentionResult:
    """Run one configuration end-to-end on the committed files."""
    df = load_subset(csv_path)
    stats = get_reference_stats(npz_path)
    mask = get_keep_mask(df[DIM_COLS].to_numpy(dtype=np.float64), stats, config)
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
    decisions = doc.get("decisions") if isinstance(doc, dict) else None
    if not isinstance(decisions, dict):
        raise ValueError(f"{path.name}: no decisions mapping")

    sel = decisions.get("distance_metric")
    if isinstance(sel, dict):
        sel = sel.get("option_id")
    if not isinstance(sel, str):
        raise ValueError(f"{path.name}: cannot read option for decision 'distance_metric'")
    return FilterConfig(metric=METRIC_OPTIONS[sel])  # type: ignore[arg-type]


def get_config(universes_dir: Path, name: str) -> FilterConfig:
    """Resolve a run name: an ASTRA universe file first, then a counterfactual preset."""
    if (universes_dir / f"{name}.yaml").exists():
        return get_universe_config(universes_dir, name)
    if name in WHAT_IF_PRESETS:
        return FilterConfig(**WHAT_IF_PRESETS[name])  # type: ignore[arg-type]
    raise FileNotFoundError(
        f"unknown run {name!r}: no universe file in {universes_dir} and no "
        f"counterfactual preset (have: {sorted(WHAT_IF_PRESETS)})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one universe of the pledge filter demo.")
    parser.add_argument(
        "--universe",
        default=None,
        help="run name: a universe id under analysis/universes/, or a "
        "counterfactual preset (diagnostic replay of an excluded option)",
    )
    parser.add_argument("--metric", default=None, choices=sorted(METRIC_OPTIONS))
    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="list sentences the baseline retains that this replay removes",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "data" / "pledges_subset.csv"
    npz_path = root / "data" / "reference_stats.npz"
    universes = root / "analysis" / "universes"

    # Two entry forms: --universe <id> (reads the ASTRA universe file or a
    # preset), or the ASTRA recipe form --metric X.
    if args.metric is not None:
        if args.universe is not None:
            parser.error("give either --universe or --metric, not both")
        label = "(from decision flags)"
        config = FilterConfig(metric=args.metric)
    else:
        label = args.universe or "baseline"
        config = get_config(universes, label)
    result = get_retention(csv_path, npz_path, config)
    stats = get_reference_stats(npz_path)
    print(f"universe: {label}   (metric={config.metric}, alpha={config.alpha})")
    print(
        f"cluster {stats.cluster_1idx} (Forest Bioenergy): "
        f"retained {result.kept}/{result.n} ({result.pct}%)"
    )

    if args.show_diff and label != "baseline":
        df = load_subset(csv_path)
        coords = df[DIM_COLS].to_numpy(dtype=np.float64)
        here = get_keep_mask(coords, stats, config)
        base = get_keep_mask(coords, stats, get_config(universes, "baseline"))
        dropped = df[base & ~here]
        print(
            f"\nretained by the accepted baseline but REMOVED here: "
            f"{len(dropped)} sentences; first 5:"
        )
        for _, row in dropped.head(5).iterrows():
            print(f"  [{row.sentence_id}] {row.text_sentence[:80]}")


if __name__ == "__main__":
    main()
