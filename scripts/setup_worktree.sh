#!/usr/bin/env bash
# 새 git 워크트리에 메인 코드베이스의 환경을 연결한다.
# 사용법: scripts/setup_worktree.sh /path/to/worktree
set -euo pipefail
MAIN="/home/sieg/projects-wsl/ProjectFinal"
WT="${1:?워크트리 경로를 인자로 넘겨라}"
[ -d "$WT" ] || { echo "워크트리가 없다: $WT" >&2; exit 1; }

for item in .venv env node_modules; do
  if [ -e "$MAIN/$item" ]; then
    ln -sfn "$MAIN/$item" "$WT/$item"
    echo "링크 $item"
  fi
done
mkdir -p "$WT/artifacts" "$WT/data"
[ -f "$MAIN/.env" ] && ln -sfn "$MAIN/.env" "$WT/.env" && echo "링크 .env"

echo "워크트리 환경 연결 완료 → $WT"
"$WT/.venv/bin/python" -c "import torch;print(f'  torch {torch.__version__} | CUDA {torch.cuda.is_available()}')" 2>/dev/null || true
