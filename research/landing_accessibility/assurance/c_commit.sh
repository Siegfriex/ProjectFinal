#!/usr/bin/env bash
# C helper: mirror bus → commit → push using absolute paths (avoids cwd-reset failures).
# Usage: c_commit.sh "<message>" [extra paths relative to worktree root...]
set -euo pipefail
W=/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21
A=$W/research/landing_accessibility/assurance
python3 $A/mirror_sync.py >/dev/null 2>&1 || true
git -C "$W" add research/landing_accessibility/assurance/bus_mirror_c "${@:2}"
git -C "$W" -c user.name="Claude C" -c user.email="c@assurance" commit -q -m "$1" || { echo "nothing to commit"; exit 0; }
git -C "$W" push -q origin claude-c/assurance-v21
git -C "$W" rev-parse --short HEAD
