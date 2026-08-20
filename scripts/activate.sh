#!/usr/bin/env bash
# ProjectFinal 통합 개발 환경 — `source scripts/activate.sh`
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Python (통합 .venv, CUDA 13.0 / sm_120) ──
export VIRTUAL_ENV="$ROOT/.venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export UV_LINK_MODE=hardlink

# ── Java (SDKMAN: JDK 21 / Maven / Gradle / Spring Boot) ──
export SDKMAN_DIR="/home/sieg/.sdkman"
[ -s "$SDKMAN_DIR/bin/sdkman-init.sh" ] && source "$SDKMAN_DIR/bin/sdkman-init.sh"
export JAVA_HOME="$SDKMAN_DIR/candidates/java/current"

# ── Node (전역 도구: mermaid-cli, tsx, pnpm …) ──
export PATH="/home/sieg/.local/bin:$ROOT/node_modules/.bin:$PATH"

# ── 브라우저 (mermaid-cli / playwright / selenium 공용) ──
export PUPPETEER_EXECUTABLE_PATH="/usr/bin/google-chrome"
export PLAYWRIGHT_BROWSERS_PATH="/home/sieg/.cache/ms-playwright"

# ── 프로젝트 루트 고정 ──
export PROJECT_FINAL_ROOT="$ROOT"

echo "ProjectFinal 환경 활성화 → $ROOT"
python -c "import torch;print(f'  torch {torch.__version__} | CUDA {torch.cuda.is_available()} | {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')" 2>/dev/null
