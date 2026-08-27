"""depth 축을 **결과로** 보고한다 — `LA-AC-AMD1-20260827` §2.

E000 6/6에서 `MPFED`가 전건 NULL이었다. 원인 두 가지 모두 시정하지 않기로
판정됐으므로(가드 입도 · E-6b fail-closed), depth 축은 **산출 실패 자체가
결과**다. 서술에서 지우지 않는다.

## 서술 제약 (개정 1 §2 재확인)

> ○ 대표기능은 **본 연구의 자동 관측 프로토콜 범위에서** 초기 화면으로부터
>   도달 가능한 경로로 관측되지 않았다.
> ✗ 고령자가 대표기능에 도달할 수 없다
> ✗ 대표기능이 로그인 뒤에 있다

**우리가 관측한 것은 우리 도구의 도달 한계이지 사용자의 도달 한계가 아니다.**
"""

from __future__ import annotations

from typing import Any

import pandas as pd

#: 개정 1 §2가 요구한 서술 제약. 산출물에 그대로 실어 나른다.
DEPTH_NARRATIVE_CONSTRAINT = (
    "대표기능은 **본 연구의 자동 관측 프로토콜 범위에서** 초기 화면으로부터 도달 가능한 "
    "경로로 관측되지 않았다. '고령자가 대표기능에 도달할 수 없다'거나 '대표기능이 로그인 "
    "뒤에 있다'로 쓰지 않는다 — **우리가 관측한 것은 우리 도구의 도달 한계이지 사용자의 "
    "도달 한계가 아니다.**"
)

#: E-6b(gate 종류 판별 실패 → fail-closed) 발화가 표시되는 후보 컬럼.
_E6B_COLUMNS: tuple[str, ...] = ("e6b_fired", "gate_kind_undetermined", "e6b_fail_closed")


def _count_flag(frame: pd.DataFrame, columns: tuple[str, ...]) -> tuple[int, bool]:
    """후보 컬럼 중 존재하는 것으로 1/True 건수를 센다. (건수, 컬럼존재여부)."""
    for col in columns:
        if col in frame.columns:
            values = frame[col].astype(str).str.strip().str.upper()
            return int(values.isin({"1", "TRUE"}).sum()), True
    return 0, False


def depth_axis_report(marts: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """`mpfed_available_n` / 사유별 계수 / E-6b 발화 횟수를 낸다 (개정 1 §2 표).

    사유별 계수는 `endpoint_status`·`endpoint_status_detail`에서 유도한다.
    엔진이 아직 내보내지 않는 표시(가드·E-6b)는 **컬럼 존재 여부를 함께 보고**해서
    0건이 "일어나지 않았다"로 오독되지 않게 한다.
    """
    landing = marts.get("fact_landing_observation", pd.DataFrame())
    task = marts.get("fact_task_entry", pd.DataFrame())
    attempted_n = len(landing)

    if task.empty:
        return {
            "attempted_n": attempted_n,
            "mpfed_available_n": 0,
            "mpfed_available_rate": None,
            "by_reason": {},
            "e6b_fired_count": 0,
            "e6b_marker_present": False,
            "narrative_constraint": DEPTH_NARRATIVE_CONSTRAINT,
            "note": "fact_task_entry가 비어 있어 depth 축 사유를 분해할 수 없다.",
        }

    mpfed = pd.to_numeric(task.get("MPFED"), errors="coerce")
    available_n = int(mpfed.notna().sum())
    endpoint_status = task.get("endpoint_status", pd.Series(dtype=object)).astype(str)
    detail = task.get("endpoint_status_detail", pd.Series(dtype=object)).astype(str)
    unresolved = mpfed.isna()

    guard_n, guard_present = _count_flag(task, ("l1_guard_blocked", "guard_blocked_pre_scout"))
    e6b_n, e6b_present = _count_flag(task, _E6B_COLUMNS)

    by_reason = {
        # 계정행동 가드가 Scout 이전에 차단 — **우리 도구의 제약**.
        "guard_blocked_pre_scout": guard_n,
        # gate 종류 판별 실패 → E-6b fail-closed.
        "gate_kind_undetermined": e6b_n,
        # Scout 예산 소진.
        "scout_no_signal": int((unresolved & (detail == "UNRESOLVED_NO_SIGNAL")).sum()),
        # 그 외 endpoint 미도달.
        "endpoint_not_reached": int(
            (unresolved & (endpoint_status != "FUNCTION_ENDPOINT_REACHED")).sum()
        ),
    }

    return {
        "attempted_n": attempted_n,
        "n_task_rows": len(task),
        "mpfed_available_n": available_n,
        "mpfed_available_rate": (round(available_n / len(task), 4) if len(task) else None),
        "by_reason": by_reason,
        "e6b_fired_count": e6b_n,
        "e6b_marker_present": e6b_present,
        "guard_marker_present": guard_present,
        "marker_note": (
            "가드·E-6b 표시 컬럼이 mart에 없으면 그 계수 0은 '일어나지 않았다'가 아니라 "
            "'표시가 산출되지 않았다'는 뜻이다 — "
            f"guard_marker_present={guard_present}, e6b_marker_present={e6b_present}."
        ),
        "narrative_constraint": DEPTH_NARRATIVE_CONSTRAINT,
    }
