"""The honesty invariant: every number quoted in analysis/astra.yaml is a
number the pipeline computes from the committed data, and the analysis
always validates through the fork toolchain.

Run from korean-pledges-demo/: env -u PYTHONPATH ../.venv/bin/python -m pytest tests/ -v
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from filter_pledges import get_config, get_retention  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "pledges_subset.csv"
NPZ = ROOT / "data" / "reference_stats.npz"
YAML_TEXT = (ROOT / "analysis" / "astra.yaml").read_text()
RUN_NAMES = ["baseline", "what-if-euclidean", "what-if-chisq"]


def get_computed_values() -> tuple[set[str], set[str]]:
    """Return (percentages, kept/n fractions) the pipeline computes."""
    pcts: set[str] = set()
    fracs: set[str] = set()
    for name in RUN_NAMES:
        r = get_retention(CSV, NPZ, get_config(ROOT / "analysis" / "universes", name))
        pcts.add(f"{r.pct}%")
        fracs.add(f"{r.kept}/{r.n}")
    return pcts, fracs


def test_every_quoted_percentage_is_pipeline_computed():
    pcts, _ = get_computed_values()
    quoted = set(re.findall(r"\d+\.\d+%", YAML_TEXT))
    stray = quoted - pcts
    assert not stray, (
        f"astra.yaml quotes percentages the pipeline does not compute: {sorted(stray)}"
    )


def test_every_quoted_fraction_is_pipeline_computed():
    _, fracs = get_computed_values()
    quoted = set(re.findall(r"\b\d+/218\b", YAML_TEXT))
    stray = quoted - fracs
    assert not stray, (
        f"astra.yaml quotes fractions the pipeline does not compute: {sorted(stray)}"
    )


def test_headline_numbers_are_present():
    """The demo-critical numbers must actually appear in the YAML."""
    assert "31.2%" in YAML_TEXT and "73.9%" in YAML_TEXT
    assert "68/218" in YAML_TEXT and "161/218" in YAML_TEXT


@pytest.mark.parametrize(
    "target",
    ["analysis/astra.yaml", "analysis/universes/baseline.yaml"],
)
def test_astra_validate_green(target: str):
    astra = ROOT.parent / ".venv" / "bin" / "astra"
    assert astra.exists(), "repo venv missing — run ../install_and_validate.sh first"
    cmd = [str(astra), "validate", str(ROOT / target)]
    if "universes" in target:
        cmd += ["-a", str(ROOT / "analysis" / "astra.yaml")]
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, f"{target}: {proc.stdout}\n{proc.stderr}"
