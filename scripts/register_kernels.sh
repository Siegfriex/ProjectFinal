#!/usr/bin/env bash
# 통합 .venv + 상위 프로젝트 venv들을 Jupyter 커널로 등록
set -uo pipefail
cd "$(dirname "$0")/.."
reg() {
  local py="$1" name="$2" disp="$3"
  [ -x "$py" ] || { echo "SKIP $name (python 없음)"; return; }
  "$py" -c "import ipykernel" 2>/dev/null || { echo "SKIP $name (ipykernel 없음)"; return; }
  "$py" -m ipykernel install --user --name "$name" --display-name "$disp" >/dev/null 2>&1 \
    && echo "OK   $name" || echo "FAIL $name"
}
reg ".venv/bin/python"       "projectfinal"  "ProjectFinal (통합, cu130)"
reg "env/koen/bin/python"    "koen"          "KOEN (torch cu130)"
reg "env/sbs-ds/bin/python"  "sbs-ds"        "SBS DataScience (opencv/tf)"
reg "env/hongik/bin/python"  "hongik"        "Hongik 26-1"
reg "env/mbn/bin/python"     "mbn"           "mbN GUIDE"
reg "env/ai-env/bin/python"  "ai-env"        "ai-env (경량)"
reg "env/dsja/bin/python"    "dsja"          "DSJA P4 recruit"
reg "env/miriart/bin/python" "miriart"       "MiriArt AI"
echo "--- 등록된 커널 ---"
.venv/bin/python -m jupyter kernelspec list 2>/dev/null || jupyter kernelspec list 2>/dev/null
