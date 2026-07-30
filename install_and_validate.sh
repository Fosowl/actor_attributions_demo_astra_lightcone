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

echo "==> Installing astra-spec + astra-tools (editable) into $VENV"
[ -d "$VENV" ] || uv venv --quiet "$VENV"
# One resolution with both local editables: the local astra-spec satisfies
# astra-tools' astra-spec pin, so nothing is pulled from PyPI for it.
uv pip install --quiet -p "$VENV" -e "$SPEC" -e "$TOOLS[dev]"

ASTRA="$VENV/bin/astra"
echo "==> $("$ASTRA" --version) | astra-spec $("$VENV/bin/python" -c 'from importlib.metadata import version; print(version("astra-spec"))')"

# Smoke check: the actor layer is present iff the schema serves the concept.
if "$ASTRA" spec actor >/dev/null 2>&1; then
  echo "==> Actor layer (RFC-0003) present: astra spec actor OK"
else
  echo "==> NOTE: this astra-spec checkout has no Actor concept —"
  echo "    update the submodules (git submodule update --remote) for the actor layer."
fi

[ -f "$TARGET" ] || fail "no such analysis file: $TARGET"

echo
echo "==> Validating $TARGET"
"$ASTRA" validate "$TARGET"

# Validate sibling universes, if the conventional directory exists.
UNIVERSES="$(dirname "$TARGET")/universes"
if [ -d "$UNIVERSES" ]; then
  for u in "$UNIVERSES"/*.yaml; do
    [ -e "$u" ] || continue
    echo
    echo "==> Validating universe $u"
    "$ASTRA" validate "$u" -a "$TARGET"
  done
fi

if [ "$RUN_SUITE" = 1 ]; then
  echo
  echo "==> Running astra-tools test suite"
  (cd "$TOOLS" && "$VENV/bin/python" -m pytest -q)
  echo "    (astra-spec's own suite needs the linkml toolchain: cd astra-spec && uv run pytest)"
fi

echo
echo "All checks passed."
