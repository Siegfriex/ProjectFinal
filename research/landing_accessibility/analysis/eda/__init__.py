"""목표 2 — EDA-03~08 스크립트 (P-H, `03_CRISP_DM_EXECUTION_PLAN_v2.0.md`).

각 스크립트는 CSV/Parquet + summary JSON + PNG + Markdown note를 낸다.
전부 synthetic 데이터로만 end-to-end 검증됐다 (`PHASE_GATES.md §4.2`).
"""

from .eda03_landing_accessibility import run_eda03
from .eda04_popup_obstruction import run_eda04
from .eda05_entry_depth import run_eda05
from .eda06_joint_profile import run_eda06
from .eda07_certification_descriptive import run_eda07
from .eda08_robustness import run_eda08

RUNNERS = {
    "eda03": run_eda03,
    "eda04": run_eda04,
    "eda05": run_eda05,
    "eda06": run_eda06,
    "eda07": run_eda07,
    "eda08": run_eda08,
}

__all__ = [
    "RUNNERS",
    "run_eda03",
    "run_eda04",
    "run_eda05",
    "run_eda06",
    "run_eda07",
    "run_eda08",
]
