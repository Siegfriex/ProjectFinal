#!/usr/bin/env bash
# C helper: mirror bus → commit → push using absolute paths (avoids cwd-reset failures).
# Usage: c_commit.sh "<message>" [extra paths relative to worktree root...]
set -euo pipefail
W=/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21
A=$W/research/landing_accessibility/assurance
# R51 ③: mirror failures are never swallowed — exit 2 (did not run) or exit 1 (residual mismatch) aborts the commit
python3 $A/mirror_sync.py || { rc=$?; echo "c_commit: mirror_sync exit $rc — commit aborted (R51: unsynced mirror is not committed)"; exit $rc; }
git -C "$W" add research/landing_accessibility/assurance/bus_mirror_c "${@:2}"
git -C "$W" -c user.name="Claude C" -c user.email="c@assurance" commit -q -m "$1" || { echo "nothing to commit"; exit 0; }
git -C "$W" push -q origin claude-c/assurance-v21
git -C "$W" rev-parse --short HEAD
