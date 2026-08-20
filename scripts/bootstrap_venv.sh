#!/usr/bin/env bash
# ProjectFinal 통합 파이썬 환경 부트스트랩 (uv 기반, CUDA 13.0 / sm_120)
set -uo pipefail
cd "$(dirname "$0")/.."
export VIRTUAL_ENV="$PWD/.venv"
export UV_LINK_MODE=hardlink
LOG=artifacts/bootstrap_venv.log
mkdir -p artifacts
: > "$LOG"

TORCH_IDX="https://download.pytorch.org/whl/cu130"

step() { echo -e "\n===== $* =====" | tee -a "$LOG"; }

step "1/4 torch stack (cu130)"
uv pip install --python .venv/bin/python \
  --index-url "$TORCH_IDX" --extra-index-url https://pypi.org/simple \
  --index-strategy unsafe-best-match \
  torch==2.13.0+cu130 torchvision==0.28.0+cu130 torchaudio==2.11.0+cu130 \
  >>"$LOG" 2>&1 && echo "OK torch" | tee -a "$LOG" || echo "FAIL torch" | tee -a "$LOG"

step "2/4 base (KOEN freeze 재현)"
grep -vE '^(torch|torchvision|torchaudio)==' requirements/base-koen.freeze.txt > /tmp/base_notorch.txt
uv pip install --python .venv/bin/python \
  --extra-index-url "$TORCH_IDX" --index-strategy unsafe-best-match \
  -r /tmp/base_notorch.txt >>"$LOG" 2>&1 && echo "OK base" | tee -a "$LOG" || {
  echo "BULK FAIL base -> 개별 재시도" | tee -a "$LOG"
  while read -r p; do
    [ -z "$p" ] && continue
    uv pip install --python .venv/bin/python --extra-index-url "$TORCH_IDX" \
      --index-strategy unsafe-best-match "$p" >>"$LOG" 2>&1 || echo "SKIP $p" | tee -a "$LOG"
  done < /tmp/base_notorch.txt
}

step "3/4 extras"
uv pip install --python .venv/bin/python \
  --extra-index-url "$TORCH_IDX" --index-strategy unsafe-best-match \
  -r requirements/extras.txt >>"$LOG" 2>&1 && echo "OK extras" | tee -a "$LOG" || {
  echo "BULK FAIL extras -> 개별 재시도" | tee -a "$LOG"
  grep -vE '^\s*#|^\s*$' requirements/extras.txt | while read -r p; do
    uv pip install --python .venv/bin/python --extra-index-url "$TORCH_IDX" \
      --index-strategy unsafe-best-match "$p" >>"$LOG" 2>&1 || echo "SKIP $p" | tee -a "$LOG"
  done
}

step "4/4 검증"
.venv/bin/python - <<'PY' 2>&1 | tee -a "$LOG"
import importlib.metadata as m
print("installed:", len(list(m.distributions())))
try:
    import torch
    print("torch", torch.__version__, "cuda", torch.cuda.is_available(), torch.version.cuda)
    if torch.cuda.is_available(): print("gpu", torch.cuda.get_device_name(0))
except Exception as e: print("torch ERR", e)
for mod in ["numpy","pandas","cv2","sklearn","matplotlib","transformers","polars","duckdb","fastapi","streamlit"]:
    try:
        mm=__import__(mod); print(f"  {mod} {getattr(mm,'__version__','?')}")
    except Exception as e: print(f"  {mod} ERR {type(e).__name__}")
PY
echo "DONE" | tee -a "$LOG"
