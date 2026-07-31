#!/usr/bin/env bash
# Reset this workspace so the walkthrough can be run again from scratch,
# then check that it is ready.
#
# What it does:
#   - deletes /tmp/astra-demo/, where a demo run writes everything
#   - deletes __pycache__ left by running the filter
#   - restores any tracked file in this directory that was modified
#   - reports (but never deletes) untracked files someone added here
#   - runs the filter once to prove the workspace still works
#
# Usage:
#   ./reset.sh              reset, then verify
#   ./reset.sh --dry-run    show what would be removed, change nothing

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/../.venv"
SCRATCH="/tmp/astra-demo"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1
[ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] && { sed -n '2,16p' "$0"; exit 0; }

say() { printf '%s\n' "$*"; }

# 1. the scratch directory a run writes into
if [ -d "$SCRATCH" ]; then
  say "scratch files in $SCRATCH:"
  find "$SCRATCH" -type f -exec printf '    %s\n' {} \;
  if [ "$DRY" = 0 ]; then
    rm -rf "$SCRATCH"
    say "  removed."
  fi
else
  say "no scratch directory at $SCRATCH — nothing to clear."
fi

# 2. python bytecode caches
if [ "$DRY" = 0 ]; then
  find "$HERE" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
fi

# 3. restore tracked files, report untracked ones
if git -C "$HERE" rev-parse --git-dir >/dev/null 2>&1; then
  changed="$(git -C "$HERE" status --porcelain -- "$HERE")"
  if [ -n "$changed" ]; then
    say ""
    say "changes inside live-demo/:"
    printf '%s\n' "$changed" | sed 's/^/    /'
    if [ "$DRY" = 0 ]; then
      git -C "$HERE" checkout -q -- "$HERE"
      say "  tracked files restored."
      still="$(git -C "$HERE" status --porcelain --untracked-files=all -- "$HERE")"
      if [ -n "$still" ]; then
        say "  these are untracked and were LEFT ALONE — delete them yourself if they are demo leftovers:"
        printf '%s\n' "$still" | sed 's/^/    /'
      fi
    fi
  fi
fi

[ "$DRY" = 1 ] && { say ""; say "dry run — nothing changed."; exit 0; }

# 4. prove the workspace still runs
say ""
say "verifying..."
[ -x "$VENV/bin/python" ] || {
  say "error: $VENV is missing — run ../install_and_validate.sh from the repo root first" >&2
  exit 1; }
out="$(env -u PYTHONPATH "$VENV/bin/python" "$HERE/src/filter.py" --compare)"
printf '%s\n' "$out" | sed 's/^/    /'
case "$out" in
  *218*) ;;
  *) say "error: the filter did not load the expected data" >&2; exit 1 ;;
esac

say ""
say "Ready. Open a fresh assistant session in this directory and start at prompt 1."
