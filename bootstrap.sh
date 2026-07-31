#!/usr/bin/env bash
# One-command setup for this repo, for people who would rather not run the
# steps by hand. Entirely optional — `./install_and_validate.sh` on its own
# still works exactly as before.
#
# It checks for git and uv (offering to install uv), fetches the submodules,
# builds the shared virtualenv, validates the toy example, runs the demo
# filter once to prove the workspace works, and then tells you where to go.
# Nothing here is destructive: it creates and installs, never deletes.
#
# Usage:
#   ./bootstrap.sh          set up, asking before installing anything
#   ./bootstrap.sh --yes    same, but answer yes to prompts (for scripts/CI)
#   ./bootstrap.sh --help   this text

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSUME_YES=0

for arg in "$@"; do
  case "$arg" in
    -y|--yes) ASSUME_YES=1 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "error: unknown argument '$arg' (try --help)" >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }
fail() { printf 'error: %s\n' "$*" >&2; exit 1; }

# --- 1. we must be inside the repo -------------------------------------
[ -f "$ROOT/.gitmodules" ] && [ -f "$ROOT/install_and_validate.sh" ] \
  || fail "run this from inside a clone of the demo repo"

# --- 2. git -------------------------------------------------------------
command -v git >/dev/null 2>&1 || fail "git is required but was not found"

# --- 3. uv --------------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  say "uv is required and was not found."
  say "  install command: curl -LsSf https://astral.sh/uv/install.sh | sh"
  reply="n"
  if [ "$ASSUME_YES" = 1 ]; then
    reply="y"
  else
    printf 'Run that now? [y/N] '
    read -r reply || reply="n"
  fi
  case "$reply" in
    y|Y|yes|Yes|YES)
      curl -LsSf https://astral.sh/uv/install.sh | sh
      # uv lands in one of these depending on platform and installer version
      PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
      export PATH
      ;;
    *) fail "uv not installed. Install it, then re-run this script." ;;
  esac
  command -v uv >/dev/null 2>&1 \
    || fail "uv was installed but is not on PATH — open a new shell and re-run"
fi
say "==> uv $(uv --version 2>/dev/null | awk '{print $2}')"

# --- 4. submodules ------------------------------------------------------
# A plain `git clone` without --recurse-submodules leaves these empty, which
# is the most common way this repo fails to build for someone new.
if [ ! -f "$ROOT/astra-spec/pyproject.toml" ] || [ ! -f "$ROOT/astra-tools/pyproject.toml" ]; then
  say "==> Fetching submodules"
  git -C "$ROOT" submodule update --init --recursive
else
  say "==> Submodules present"
fi

# --- 5. environment + toy example --------------------------------------
say "==> Building the environment (the first run downloads packages)"
"$ROOT/install_and_validate.sh"

# --- 6. prove the demo workspace itself runs ---------------------------
say ""
# install_and_validate.sh installs astra only; the demo scripts also need the
# scientific stack. Idempotent, so re-running costs nothing.
say "==> Installing the demo's Python dependencies"
uv pip install --quiet -p "$ROOT/.venv" numpy pandas scipy pydantic pyyaml pytest

say "==> Checking the demo workspace"
env -u PYTHONPATH "$ROOT/.venv/bin/python" "$ROOT/live-demo/src/filter.py" --compare \
  | sed 's/^/    /'

# --- 7. the one thing this script cannot install for you ---------------
say ""
if command -v claude >/dev/null 2>&1; then
  say "==> Found an agentic assistant on PATH (claude)."
else
  say "==> No 'claude' on PATH."
  say "    The walkthrough is driven by an agentic coding assistant that can"
  say "    run commands and edit files. Install Claude Code"
  say "    (https://claude.com/claude-code), or point the assistant you use at"
  say "    live-demo/CLAUDE.md — it carries the rules and commands."
fi

say ""
say "Ready. Next:"
say "    cd live-demo && ./reset.sh      # confirms a clean starting point"
say "    open your assistant in that directory"
say "    follow docs/live-demo-walkthrough.md"
