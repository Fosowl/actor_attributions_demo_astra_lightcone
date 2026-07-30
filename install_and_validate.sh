#!/usr/bin/env bash
# Local install of the astra-spec + astra-tools forks (the two submodules)
# into a shared venv, then validate an ASTRA analysis file with the result.
#
# Usage:
#   ./install_and_validate.sh                      # validate the iris example
#   ./install_and_validate.sh path/to/astra.yaml   # validate a specific file
#   ./install_and_validate.sh --suite              # also run the astra-tools test suite
#
# The venv lives at .venv/ in this repo (gitignored). Re-running is
# idempotent: the editable installs pick up submodule changes without
# reinstalling; re-run after `git submodule update` to re-resolve.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
SPEC="$ROOT/astra-spec"
TOOLS="$ROOT/astra-tools"

RUN_SUITE=0
TARGET=""
for arg in "$@"; do
  case "$arg" in
    --suite) RUN_SUITE=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) TARGET="$arg" ;;
  esac
done
TARGET="${TARGET:-$TOOLS/examples/iris/astra.yaml}"

fail() { echo "error: $*" >&2; exit 1; }

command -v uv >/dev/null 2>&1 \
  || fail "uv is required (https://docs.astral.sh/uv/). Install it and re-run."

[ -f "$SPEC/pyproject.toml" ] && [ -f "$TOOLS/pyproject.toml" ] \
  || fail "submodules missing — run: git submodule update --init"

# astra-spec derives its package version from git tags (uv-dynamic-versioning);
# make sure the submodule has them, or the built version won't satisfy the
# astra-tools pin. Best-effort: offline is fine if tags are already present.
git -C "$SPEC" fetch --tags --quiet origin 2>/dev/null || true

echo "==> Installing astra-spec + astra-tools into $VENV"
[ -d "$VENV" ] || uv venv --quiet "$VENV"
# Installed as real packages, not editable. Editable installs write .pth files,
# macOS flags them UF_HIDDEN, and CPython >= 3.11 skips hidden .pth files without
# warning, which silently turns the install into a no-op after it has already
# reported success. --no-sources is required: astra-tools' [tool.uv.sources]
# pins astra-spec to the sibling path as editable, which would reintroduce the
# .pth indirection even here. Both paths are passed explicitly, so the local
# astra-spec still satisfies astra-tools' pin and nothing comes from PyPI.
uv pip install --quiet --no-sources -p "$VENV" "$SPEC" "$TOOLS[dev]"

# Prove the venv itself imports, with no PYTHONPATH rescue and no source tree on
# the path. A demo harness that only works via ambient environment is not proof.
env -u PYTHONPATH "$VENV/bin/python" - <<'PY' || fail "venv cannot import astra; the install did not take"
import importlib.util
import sys

spec = importlib.util.find_spec("astra")
if spec is None or not spec.submodule_search_locations:
    sys.exit("astra is not importable")
if not any("site-packages" in p for p in spec.submodule_search_locations):
    sys.exit(f"astra resolves outside site-packages: {list(spec.submodule_search_locations)}")
import astra.cli  # noqa: F401
import astra.datamodel.analysis  # noqa: F401
PY

ASTRA="$VENV/bin/astra"
astra_run() { env -u PYTHONPATH "$ASTRA" "$@"; }
echo "==> $(astra_run --version) | astra-spec $(env -u PYTHONPATH "$VENV/bin/python" -c 'from importlib.metadata import version; print(version("astra-spec"))')"

# Smoke check: the actor layer is present iff the schema serves the concept.
if astra_run spec actor >/dev/null 2>&1; then
  echo "==> Actor layer (RFC-0003) present: astra spec actor OK"
else
  echo "==> NOTE: this astra-spec checkout has no Actor concept —"
  echo "    update the submodules (git submodule update --remote) for the actor layer."
fi

[ -f "$TARGET" ] || fail "no such analysis file: $TARGET"

echo
echo "==> Validating $TARGET"
astra_run validate "$TARGET"

# Validate sibling universes, if the conventional directory exists.
UNIVERSES="$(dirname "$TARGET")/universes"
if [ -d "$UNIVERSES" ]; then
  for u in "$UNIVERSES"/*.yaml; do
    [ -e "$u" ] || continue
    echo
    echo "==> Validating universe $u"
    astra_run validate "$u" -a "$TARGET"
  done
fi

if [ "$RUN_SUITE" = 1 ]; then
  echo
  echo "==> Running astra-tools test suite"
  (cd "$TOOLS" && env -u PYTHONPATH "$VENV/bin/python" -m pytest -q)
  echo "    (astra-spec's own suite needs the linkml toolchain: cd astra-spec && uv run pytest)"
fi

echo
echo "All checks passed."
