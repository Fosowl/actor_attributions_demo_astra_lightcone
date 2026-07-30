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
    get_config,
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

EUCL = FilterConfig(metric="euclidean")
MAHAL = FilterConfig(metric="mahalanobis")


def test_counts_match_study_ground_truth():
    assert get_retention(CSV, NPZ, EUCL).kept == 161
    assert get_retention(CSV, NPZ, MAHAL).kept == 68


def test_pct_rounding():
    r = get_retention(CSV, NPZ, EUCL)
    assert (r.n, r.pct) == (218, 73.9)
    assert get_retention(CSV, NPZ, MAHAL).pct == 31.2


@pytest.mark.parametrize(
    "config,column",
    [(EUCL, "keep_euclidean_pooled"), (MAHAL, "keep_mahalanobis_pooled")],
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


def test_universe_file_and_presets_drive_the_filter():
    """baseline (the accepted euclidean filter) resolves from the ASTRA
    universe file; the mahalanobis counterfactual from a preset (the
    toolchain refuses a universe selecting an excluded option, so the
    what-if is deliberately not a universe file)."""
    universes = ROOT / "analysis" / "universes"
    if not any(universes.glob("*.yaml")):
        pytest.skip("analysis/ not built yet")
    assert get_universe_config(universes, "baseline") == EUCL
    assert get_config(universes, "baseline") == EUCL
    assert get_config(universes, "what-if-mahalanobis") == MAHAL


def test_unknown_universe_raises():
    with pytest.raises(FileNotFoundError):
        get_config(ROOT / "analysis" / "universes", "nonexistent")
