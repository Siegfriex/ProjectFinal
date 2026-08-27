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

from collections.abc import Sequence
from typing import Any

import pandas as pd

from .batch_results import derive_collection_markers

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


def depth_axis_report(
    marts: dict[str, pd.DataFrame],
    *,
    batches_dir: str | Sequence[str] | None = None,
    allow_cross_cohort: bool = False,
) -> dict[str, Any]:
    """`mpfed_available_n` / 사유별 계수 / E-6b 발화 횟수를 낸다 (개정 1 §2 표).

    사유별 계수는 `endpoint_status`·`endpoint_status_detail`에서 유도한다.

    가드 차단·E-6b 발화는 **배치 결과 JSON에서 파생**한다(`batches_dir`) — 수집기를
    바꾸지 않는다. 배치를 못 찾으면 `None`(확인 불가)이고, 찾았는데 0이면 0건이다.
    이 둘을 구분하지 않으면 "수집이 안 됐다"와 "가드가 안 걸렸다"가 같아 보인다.
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

    # 1순위 — 배치 결과 JSON에서 파생(수집기 무변경). 2순위 — mart 컬럼(있으면).
    markers = (
        derive_collection_markers(batches_dir, allow_cross_cohort=allow_cross_cohort)
        if batches_dir
        else None
    )
    if markers and markers.get("batches_found"):
        guard_n = int(markers["guard_blocked_n"])
        e6b_n = int(markers["e6b_fired_n"])
        guard_present = e6b_present = True
        marker_source = "BATCH_RESULTS"
    else:
        guard_n, guard_present = _count_flag(task, ("l1_guard_blocked", "guard_blocked_pre_scout"))
        e6b_n, e6b_present = _count_flag(task, _E6B_COLUMNS)
        marker_source = "MART_COLUMNS" if (guard_present or e6b_present) else "UNAVAILABLE"

    by_reason = {
        # 계정행동 가드가 Scout 이전에 차단 — **우리 도구의 제약**.
        # 확인 불가면 0이 아니라 None이다.
        "guard_blocked_pre_scout": guard_n if guard_present else None,
        # gate 종류 판별 실패 → E-6b fail-closed.
        "gate_kind_undetermined": e6b_n if e6b_present else None,
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
        "e6b_fired_count": e6b_n if e6b_present else None,
        "e6b_marker_present": e6b_present,
        "guard_marker_present": guard_present,
        "marker_source": marker_source,
        # UNRESOLVED를 budget_reason으로 분해한 결과 — endpoint_status_detail만 보면
        # SCOUT_ERROR가 '깊이 예산 초과'로 잘못 기술된다.
        "unresolved_decomposition": (
            {
                "by_budget_reason": markers.get("unresolved_by_budget_reason"),
                "by_category": markers.get("unresolved_by_category"),
                "reason_unrecorded_n": markers.get("unresolved_reason_unrecorded_n"),
                "note": markers.get("unresolved_note"),
            }
            if markers and markers.get("batches_found")
            else None
        ),
        "skipped_retry_exhausted_n": (
            markers.get("skipped_retry_exhausted_n")
            if markers and markers.get("batches_found")
            else None
        ),
        "snapshot_at": (markers or {}).get("snapshot_at"),
        "batch_markers": markers,
        "marker_note": (
            (
                "가드·E-6b 계수를 배치 결과 JSON에서 파생했다(수집기 무변경) — "
                f"소스 {markers.get('n_sources_with_files')}개 · 코호트 {markers.get('cohorts')} · "
                f"guard_blocked_by_category={markers.get('guard_blocked_by_category')}, "
                f"e6b 값-보강 확인={markers.get('e6b_value_corroborated_n')}건. "
                f"체인은 소스별 독립 검증(all_ok={markers.get('chain_verified_all_sources')})."
            )
            if marker_source == "BATCH_RESULTS"
            else (
                "가드·E-6b 마커를 **확인하지 못했다**(배치 미발견 또는 mart 컬럼 부재). "
                "이 경우 계수는 0건이 아니라 **확인 불가(None)**다 — "
                f"guard_marker_present={guard_present}, e6b_marker_present={e6b_present}."
            )
        ),
        "narrative_constraint": DEPTH_NARRATIVE_CONSTRAINT,
    }
