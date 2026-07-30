"""E2E tests for the demo filter against the study's real per-point results.

Real data only: the committed subset IS the test data. No mocks.
Run from korean-pledges-demo/: env -u PYTHONPATH ../.venv/bin/python -m pytest tests/ -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from filter_pledges import (  # noqa: E402
    FilterConfig,
    get_keep_mask,
    get_reference_stats,
    get_retention,
    get_universe_config,
    load_subset,
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
def test_point_level_agreement_with_study(config: FilterConfig, column: str):
    """Every single sentence must get the same keep/remove as the study."""
    df = load_subset(CSV)
    stats = get_reference_stats(NPZ)
    coords = df[[f"D{i}" for i in range(1, 19)]].to_numpy(dtype=np.float64)
    mask = get_keep_mask(coords, stats, config)
    expected = pd.read_csv(EXPECTED)
    merged = df[["sentence_id"]].assign(got=mask).merge(
        expected, on="sentence_id", validate="one_to_one"
    )
    disagree = merged[merged["got"] != merged[column]]
    assert disagree.empty, (
        f"{len(disagree)} disagreements: {disagree['sentence_id'].tolist()[:10]}"
    )


def test_chisq_universe_runs_and_is_between_extremes():
    cfg = FilterConfig(metric="mahalanobis", threshold="chisq_shrinkage")
    r = get_retention(CSV, NPZ, cfg)
    assert r.n == 218 and 0 < r.kept < 218


def test_chisq_requires_mahalanobis():
    cfg = FilterConfig(metric="euclidean", threshold="chisq_shrinkage")
    with pytest.raises(ValueError, match="mahalanobis"):
        get_retention(CSV, NPZ, cfg)


def test_universe_files_drive_the_filter():
    universes = ROOT / "analysis" / "universes"
    if not any(universes.glob("*.yaml")):
        pytest.skip("analysis/ not built yet (Task 3)")
    assert get_universe_config(universes, "baseline") == MAHAL
    assert get_universe_config(universes, "what-if-euclidean") == EUCL


def test_unknown_universe_raises():
    with pytest.raises(FileNotFoundError):
        get_universe_config(ROOT / "analysis" / "universes", "nonexistent")
