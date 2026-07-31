#!/usr/bin/env bash
# Run the Korean pledges demo: filter + ASTRA validation + actor display.
#
# Usage (from korean-pledges-demo/):
#   ./run_demo.sh                          # accepted baseline (euclidean)
#   ./run_demo.sh -u what-if-mahalanobis   # excluded-option replay, with diff
#   ./run_demo.sh --validate               # astra validate + actor-attributed info
#
# Requires ../.venv from ../install_and_validate.sh; installs the demo's
# Python deps into it idempotently.

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/../.venv"
[ -x "$VENV/bin/python" ] || {
  echo "error: $VENV missing — run ../install_and_validate.sh first" >&2; exit 1; }

command -v uv >/dev/null 2>&1 \
  || { echo "error: uv is required (https://docs.astral.sh/uv/)" >&2; exit 1; }
echo "==> Checking demo dependencies (first run installs them; later runs are instant)..."
uv pip install --quiet -p "$VENV" numpy pandas scipy pydantic pyyaml pytest

UNIVERSE="baseline"; VALIDATE_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    -u|--universe) UNIVERSE="$2"; shift 2 ;;
    --validate) VALIDATE_ONLY=1; shift ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "error: unknown argument $1" >&2; exit 1 ;;
  esac
done

run() { env -u PYTHONPATH "$VENV/bin/$1" "${@:2}"; }

if [ "$VALIDATE_ONLY" = 1 ]; then
  echo "==> Validating analysis + universes with the astra CLI..."
  run astra validate "$HERE/analysis/astra.yaml"
  for u in "$HERE"/analysis/universes/*.yaml; do
    run astra validate "$u" -a "$HERE/analysis/astra.yaml"
  done
  echo "==> Rendering the actor-attributed analysis (astra info)..."
  run astra info -f "$HERE/analysis/astra.yaml" -d
  exit 0
fi

echo "==> Running the '$UNIVERSE' filter on the 218 committed sentences..."
if [ "$UNIVERSE" = "baseline" ]; then
  run python "$HERE/src/filter_pledges.py" --universe "$UNIVERSE"
else
  run python "$HERE/src/filter_pledges.py" --universe "$UNIVERSE" --show-diff
fi
