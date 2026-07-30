"""Retention filter for the Korean pledges demo.

Recomputes, live, the study's out-of-sample filter on the committed
cluster-6 slice. Pure functions; the only side effect is CLI printing.

The location-correction decision from the full study is hard-coded to its
accepted value: distances are measured from the pooled OOS centroid (the
mean of the committed cluster-6 coordinates) using the REFERENCE cluster's
ridged covariance (np.cov + 1e-6*I, the study's stabilizer — carried inside
data/reference_stats.npz). Thresholds come from the reference leave-one-out
distance distribution (empirical, alpha=0.01) or the chi-squared theoretical
quantile with shrinkage covariance (beta=0.75), matching the study. The
loo_alpha_01 paths reproduce the study's per-sentence keep decisions exactly
(enforced by tests/test_filter_pledges.py).
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

# Study convention: covariances are stabilized with a small ridge. The
# reference covariance in reference_stats.npz is already ridged; the OOS
# covariance (shrinkage variant only) gets the same treatment here.
RIDGE_EPS = 1e-6

# ASTRA option id -> config value, per analysis/astra.yaml
METRIC_OPTIONS = {"mahalanobis": "mahalanobis", "euclidean": "euclidean"}
THRESHOLD_OPTIONS = {"loo_alpha_01": "loo_alpha_01", "chisq_shrinkage": "chisq_shrinkage"}

# Counterfactual presets. These are deliberately NOT committed as ASTRA
# universe files: the toolchain refuses a universe that selects an excluded
# option (EXCLUDED_OPTION_SELECTED), which is exactly the enforcement this
# demo showcases. The counterfactuals therefore run through ASTRA's other
# form — explicit decision values, as in the analysis recipe commands.
WHAT_IF_PRESETS: dict[str, dict[str, str]] = {
    "what-if-euclidean": {"metric": "euclidean", "threshold": "loo_alpha_01"},
    "what-if-chisq": {"metric": "mahalanobis", "threshold": "chisq_shrinkage"},
}


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
    cov_oos = np.cov(coords, rowvar=False) + RIDGE_EPS * np.eye(coords.shape[1])
    cov_eff = config.shrinkage_beta * stats.cov_ref + (1.0 - config.shrinkage_beta) * cov_oos
    d2 = np.einsum("ij,jk,ik->i", diff, np.linalg.inv(cov_eff), diff)
    return d2 <= float(chi2.ppf(1.0 - config.alpha, df=coords.shape[1]))


def get_retention(csv_path: Path, npz_path: Path, config: FilterConfig) -> RetentionResult:
    """Run one universe end-to-end on the committed files."""
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

    def get_option(decision_id: str) -> str:
        sel = decisions.get(decision_id)
        if isinstance(sel, dict):
            sel = sel.get("option_id")
        if not isinstance(sel, str):
            raise ValueError(f"{path.name}: cannot read option for decision {decision_id!r}")
        return sel

    return FilterConfig(
        metric=METRIC_OPTIONS[get_option("distance_metric")],  # type: ignore[arg-type]
        threshold=THRESHOLD_OPTIONS[get_option("threshold_rule")],  # type: ignore[arg-type]
    )


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
    parser.add_argument("--threshold", default=None, choices=sorted(THRESHOLD_OPTIONS))
    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="list sentences this universe retains that baseline removes",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "data" / "pledges_subset.csv"
    npz_path = root / "data" / "reference_stats.npz"
    universes = root / "analysis" / "universes"

    # Two entry forms: --universe <id> (reads the ASTRA universe file), or the
    # ASTRA recipe form --metric X --threshold Y (both flags required together).
    if (args.metric is None) != (args.threshold is None):
        parser.error("--metric and --threshold must be given together")
    if args.metric is not None:
        if args.universe is not None:
            parser.error("give either --universe or --metric/--threshold, not both")
        label = "(from decision flags)"
        config = FilterConfig(metric=args.metric, threshold=args.threshold)
    else:
        label = args.universe or "baseline"
        config = get_config(universes, label)
    result = get_retention(csv_path, npz_path, config)
    stats = get_reference_stats(npz_path)
    print(f"universe: {label}   (metric={config.metric}, threshold={config.threshold})")
    print(
        f"cluster {stats.cluster_1idx} (Forest Bioenergy): "
        f"retained {result.kept}/{result.n} ({result.pct}%)"
    )

    if args.show_diff and label != "baseline":
        df = load_subset(csv_path)
        coords = df[DIM_COLS].to_numpy(dtype=np.float64)
        here = get_keep_mask(coords, stats, config)
        base = get_keep_mask(coords, stats, get_universe_config(universes, "baseline"))
        extra = df[here & ~base]
        print(f"\nretained here but removed by baseline: {len(extra)} sentences; first 5:")
        for _, row in extra.head(5).iterrows():
            print(f"  [{row.sentence_id}] {row.text_sentence[:80]}")


if __name__ == "__main__":
    main()
