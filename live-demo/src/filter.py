"""Out-of-sample pledge filter — decides which sentences belong to the topic.

Each pledge sentence is a point in an 18-dimensional space. A sentence is
kept if its distance to the topic's centre is within the cut-off measured
on the reference corpus. Two distance measures are available:

  euclidean     straight-line distance; treats every direction alike
  mahalanobis   accounts for the topic's stretched shape, using the shape
                (covariance) measured on the reference corpus

The cut-off is the 99th percentile of the reference corpus's own
leave-one-out distances for the matching measure, so both measures are
judged against the same kind of yardstick.

Usage (from live-demo/):
  python src/filter.py --metric <measure>
  python src/filter.py --metric <measure> --show-dropped
  python src/filter.py --compare
  python src/filter.py --compare --show-disagreement

Reads data/pledges_subset.csv and data/reference_stats.npz.
Side effects: prints to stdout. Writes nothing.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DIM_COLS = [f"D{i}" for i in range(1, 19)]
ALPHA = 0.01
ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "pledges_subset.csv"
NPZ = ROOT / "data" / "reference_stats.npz"


def get_keep_mask(coords: np.ndarray, stats, metric: str) -> np.ndarray:
    """Return a boolean per sentence: True = kept by this distance measure.

    Distances are measured from the pledge set's own centre; the reference
    corpus supplies the shape and the cut-off.
    """
    diff = coords - coords.mean(axis=0)
    if metric == "euclidean":
        distance = np.linalg.norm(diff, axis=1)
        cutoff = float(np.quantile(stats["loo_eucl_d"], 1.0 - ALPHA))
    elif metric == "mahalanobis":
        distance = np.einsum("ij,jk,ik->i", diff, np.linalg.inv(stats["cov_ref"]), diff)
        cutoff = float(np.quantile(stats["loo_mahal_d2"], 1.0 - ALPHA))
    else:
        raise ValueError(f"unknown metric {metric!r}: use euclidean or mahalanobis")
    return distance <= cutoff


def get_kept(df: pd.DataFrame, stats, metric: str) -> np.ndarray:
    """Apply one measure to the loaded sentences."""
    return get_keep_mask(df[DIM_COLS].to_numpy(dtype=np.float64), stats, metric)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metric", choices=["euclidean", "mahalanobis"])
    parser.add_argument(
        "--show-dropped", action="store_true", help="print sentences this measure removes"
    )
    parser.add_argument(
        "--compare", action="store_true", help="run both measures side by side"
    )
    parser.add_argument(
        "--show-disagreement",
        action="store_true",
        help="with --compare: print sentences the two measures disagree on",
    )
    args = parser.parse_args()

    df = pd.read_csv(CSV)
    stats = np.load(NPZ)
    n = len(df)
    print(f"Loaded {n} pledge sentences (topic: Forest Bioenergy).\n")

    if args.compare:
        masks = {m: get_kept(df, stats, m) for m in ("euclidean", "mahalanobis")}
        print(f"{'measure':<14}{'kept':>10}{'share':>10}")
        print("-" * 34)
        for metric, mask in masks.items():
            kept = int(mask.sum())
            print(f"{metric:<14}{f'{kept}/{n}':>10}{f'{100 * kept / n:.1f}%':>10}")
        if args.show_disagreement:
            gap = df[masks["euclidean"] & ~masks["mahalanobis"]]
            print(f"\nkept by euclidean, removed by mahalanobis: {len(gap)}; first 5:")
            for _, row in gap.head(5).iterrows():
                print(f"  [{row.sentence_id}] {row.text_sentence[:70]}")
            rev = df[masks["mahalanobis"] & ~masks["euclidean"]]
            print(f"\nkept by mahalanobis, removed by euclidean: {len(rev)}; all of them:")
            for _, row in rev.iterrows():
                print(f"  [{row.sentence_id}] {row.text_sentence[:70]}")
        return

    if not args.metric:
        parser.error("give --metric euclidean|mahalanobis, or --compare")

    mask = get_kept(df, stats, args.metric)
    kept = int(mask.sum())
    print(f"measure: {args.metric}")
    print(f"kept {kept}/{n}  ({100 * kept / n:.1f}%)")

    if args.show_dropped:
        dropped = df[~mask]
        print(f"\nremoved by {args.metric}: {len(dropped)} sentences; first 5:")
        for _, row in dropped.head(5).iterrows():
            print(f"  [{row.sentence_id}] {row.text_sentence[:70]}")


if __name__ == "__main__":
    main()
