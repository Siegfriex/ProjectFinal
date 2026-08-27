"""Joint-valid 분류 — Claude A(governor) 확정 정의 (LA-TB-1630-20260827, 결과를
보기 전에 고정, 사후 변경 금지).

관측 1건이 **joint-valid**이려면 4개 조건을 **전부** 충족해야 한다:

1. **L0 수집 완료** — `measurement_status=MEASURED` (DOM·AX·CSS/geometry·
   screenshot 존재, manifest 검증 통과가 이 상태값의 전제조건이다).
2. **L1이 종결상태 도달** — `endpoint_reached=1` **또는** archetype별 정당한
   auth-gate endpoint(`endpoint_status_detail=ENDPOINT_VIA_AUTH_GATE`, A2 규칙
   E-5~E-10) **또는** 명시적 도달불가 판정(`endpoint_status` ∈
   `{AUTH_GATE_REACHED, PAYMENT_GATE_REACHED, PERSONAL_DATA_REQUIRED, CAPTCHA,
   BLOCKED}`). `UNRESOLVED`(depth budget 소진·replay 깨짐·신호 없음)는 종결이
   아니다 — 이건 **수집 사정**이지 관측 결과가 아니다.
3. **MPFED 산출 가능** — `NED`·`IED`가 둘 다 정의됨(→ `MPFED` not null).
4. **older-relevant KWCAG 기준 중 최소 1개가 UNDETERMINED가 아닌 판정** —
   `older_relevance != OTHER`인 `fact_criterion_result` 행 중 `final_status`가
   `UNDETERMINED`가 아닌 것이 하나라도 있어야 한다.

**중요한 비대칭(의도된 것)**: obstruction 변수(`OverlayCoverage` 등)는 joint-valid
요건에 넣지 않는다 — secondary라서, 요건에 넣으면 primary 표본이 불필요하게
깎인다. 그 대신 obstruction 변수의 결측률은 별도로 항상 보고한다
(`eda09_association_and_quadrant.py`의 secondary association `missing_n`).

**"명시적 도달불가"(예: 로그인 벽에 막힘)는 joint-valid에 포함된다** — 그건
관측 결과지 실패가 아니다. **타임아웃(수집 사정)은 제외된다.** 이 둘을 섞지 않는다
— 그래서 이 모듈의 exclusion reason 분류가 `L1_NOT_ATTEMPTED_OR_UNRESOLVED`
(수집이 끝을 못 봄)와 `endpoint_status`의 명시적 값들(수집은 끝났고 결과가
"막힘"으로 확정됨)을 서로 다른 경로로 나눈다.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

#: 조건 1 위반 — L0 수집 자체가 transport/브라우저 사정으로 끝나지 못함.
#: `NOT_ELIGIBLE_AT_COLLECTION`은 `FAILED_%` 계열이 아니지만(규칙 N-6) 애초에
#: `MEASURED`가 아니므로 여기서도 조건 1을 통과하지 못한다 — TRANSPORT 계열로 묶는다
#: (수집 자체가 없었다는 점에서 성격이 같다. 타임아웃과는 명확히 분리해 둔다).
_TRANSPORT_FAILURE_STATUSES = frozenset(
    {
        "FAILED_ACCESS_BLOCKED",
        "FAILED_ROBOTS_OR_TRANSPORT",
        "FAILED_BROWSER_CRASH",
        "FAILED_EVIDENCE_INCOMPLETE",
        "NOT_ELIGIBLE_AT_COLLECTION",
    }
)
#: 조건 1 위반 — 6분 cap 초과(타임아웃). transport failure와 섞지 않는다(governor 지시).
_TIMEOUT_STATUSES = frozenset({"FAILED_PAGE_TIMEOUT"})

#: 조건 2 통과로 보는 명시적 종결 `endpoint_status` 값 — `FUNCTION_ENDPOINT_REACHED`는
#: `endpoint_reached=1`로 이미 잡히므로 여기 목록은 "명시적 도달불가" 값들이다.
_EXPLICIT_UNREACHABLE_ENDPOINT_STATUSES = frozenset(
    {"AUTH_GATE_REACHED", "PAYMENT_GATE_REACHED", "PERSONAL_DATA_REQUIRED", "CAPTCHA", "BLOCKED"}
)

#: **Claude A(governor) 확정** — gate에 도달해서 MPFED가 NULL이 된 경우는
#: `MPFED_NULL`과 **섞지 않는다**. 전자는 **대상의 성질**(대표기능이 인증/결제/
#: 본인확인 벽 뒤에 있다)이고, 후자·transport·timeout은 **우리 쪽 사정**(수집이
#: 끝을 못 봤다)이다. A2 §1.5.1상 endpoint 미도달이면 MPFED=NULL이라 J3에서
#: 탈락하는 것은 같지만, **왜 탈락했는가**가 전혀 다르므로 사유를 분리한다.
#:
#: `BLOCKED`는 여기 넣지 않는다(Claude A 승인) — 접근 차단은 gate(진입 조건)가
#: 아니라 **우리 도구에 대한 거절**이고, gate 집계를 부풀리면 "인증 벽 뒤 N건"
#: 보고가 과대해진다. 다만 **지우지 않고** `ACCESS_REFUSED_MPFED_NULL`로 따로
#: 세서 보고한다 — WAF·403은 대상의 진입 설계가 아니라 우리 도구에 대한
#: 반응이므로, "진입 설계를 관측하지 못했다"로 기록해야 할 별개의 사실이다.
GATE_ENDPOINT_STATUSES = frozenset(
    {"AUTH_GATE_REACHED", "PAYMENT_GATE_REACHED", "PERSONAL_DATA_REQUIRED", "CAPTCHA"}
)

EXCLUSION_REASONS: tuple[str, ...] = (
    "TRANSPORT_FAILURE",
    "TIMEOUT",
    "L1_NOT_ATTEMPTED_OR_UNRESOLVED",
    "GATE_REACHED_MPFED_NULL",
    "ACCESS_REFUSED_MPFED_NULL",
    "MPFED_NULL",
    "KWCAG_ALL_UNDETERMINED",
)

#: 위 사유가 **대상의 성질**인가(True) **우리 쪽 수집 사정**인가(False).
#: 보고에서 이 둘을 합산하지 않기 위한 표다.
EXCLUSION_REASON_IS_TARGET_PROPERTY: dict[str, bool] = {
    "TRANSPORT_FAILURE": False,
    "TIMEOUT": False,
    "L1_NOT_ATTEMPTED_OR_UNRESOLVED": False,
    "GATE_REACHED_MPFED_NULL": True,
    # WAF·403은 우리 도구에 대한 반응이지 대상의 진입 설계가 아니다 → 대상의 성질이 아니다.
    "ACCESS_REFUSED_MPFED_NULL": False,
    "MPFED_NULL": False,
    "KWCAG_ALL_UNDETERMINED": False,
}

_JOINT_VALIDITY_COLUMNS = [
    "observation_id",
    "web_target_id",
    "archetype",
    "is_joint_valid",
    "exclusion_reason",
    # gate 종류를 남긴다 — "인증 벽 뒤 N건"을 endpoint_status별로 분해해 보고하기 위해서다.
    "endpoint_status",
    # L0 단계 접근 거절(FAILED_ACCESS_BLOCKED)을 L1 BLOCKED와 함께 세기 위해 남긴다.
    "measurement_status",
]


def classify_joint_validity(marts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """관측(`fact_landing_observation` 1행)마다 joint-valid 여부 + exclusion_reason.

    조건 1→2→3→4 순서로 검사하고, **처음 위반한 조건**을 exclusion_reason으로
    기록한다(관측 하나가 여러 조건을 동시에 어겨도 사유는 하나만 남긴다 — 우선
    순위가 있는 깔때기 구조이기 때문이다). 빈 입력이면 빈 표를 돌려준다.
    """
    landing = marts.get("fact_landing_observation", pd.DataFrame())
    if landing.empty:
        return pd.DataFrame(columns=_JOINT_VALIDITY_COLUMNS)

    task = marts.get("fact_task_entry", pd.DataFrame())
    criterion = marts.get("fact_criterion_result", pd.DataFrame())

    task_by_target = task.set_index("web_target_id") if not task.empty else pd.DataFrame()

    older_undetermined_all: pd.Series = pd.Series(dtype=bool)
    older_n: pd.Series = pd.Series(dtype=int)
    if not criterion.empty:
        older = criterion[criterion["older_relevance"].astype(str) != "OTHER"]
        if not older.empty:
            older_n = older.groupby("observation_id").size()
            older_undetermined_all = older.groupby("observation_id")["final_status"].apply(
                lambda s: bool((s.astype(str) == "UNDETERMINED").all())
            )

    rows: list[dict[str, Any]] = []
    for _, obs in landing.iterrows():
        obs_id = obs["observation_id"]
        wt_id = obs["web_target_id"]
        status = str(obs.get("measurement_status"))

        task_row = None
        archetype = None
        if wt_id in task_by_target.index:
            candidate = task_by_target.loc[wt_id]
            # 동일 web_target_id에 task 행이 둘 이상이면(1:다) 첫 행만 대표로 쓴다 —
            # 이 연구는 L1 대표기능 진입 1건을 본다(00 §Hard Scope).
            task_row = candidate.iloc[0] if isinstance(candidate, pd.DataFrame) else candidate
            archetype = task_row.get("interaction_archetype")

        # 조건 1.
        if status in _TRANSPORT_FAILURE_STATUSES:
            rows.append(
                _row(
                    obs_id, wt_id, archetype, False, "TRANSPORT_FAILURE", measurement_status=status
                )
            )
            continue
        if status in _TIMEOUT_STATUSES:
            rows.append(_row(obs_id, wt_id, archetype, False, "TIMEOUT", measurement_status=status))
            continue
        if status != "MEASURED":
            # 스키마상 나머지 값은 없어야 하나, 방어적으로 TRANSPORT_FAILURE로 묶는다.
            rows.append(
                _row(
                    obs_id, wt_id, archetype, False, "TRANSPORT_FAILURE", measurement_status=status
                )
            )
            continue

        # 조건 2 — L1 종결상태 도달.
        if task_row is None:
            # task 행 자체가 없다 — endpoint_status도 없다(L1 미시도).
            rows.append(
                _row(
                    obs_id,
                    wt_id,
                    archetype,
                    False,
                    "L1_NOT_ATTEMPTED_OR_UNRESOLVED",
                    None,
                    measurement_status=status,
                )
            )
            continue
        endpoint_status = str(task_row.get("endpoint_status"))
        endpoint_reached = str(task_row.get("endpoint_reached")) == "1"
        explicit_terminal = (
            endpoint_reached or endpoint_status in _EXPLICIT_UNREACHABLE_ENDPOINT_STATUSES
        )
        if not explicit_terminal:
            # endpoint_status == UNRESOLVED (또는 알 수 없는 값) — 종결이 아니다.
            rows.append(
                _row(
                    obs_id,
                    wt_id,
                    archetype,
                    False,
                    "L1_NOT_ATTEMPTED_OR_UNRESOLVED",
                    endpoint_status,
                    measurement_status=status,
                )
            )
            continue

        # 조건 3 — MPFED 산출 가능(NED·IED 둘 다 정의).
        # **판정 동작은 바꾸지 않는다**(governor 확인: 현 동작이 맞다) — 탈락 여부는
        # 그대로고, gate 도달로 인한 탈락만 사유 라벨을 분리한다.
        ned = task_row.get("NED")
        ied = task_row.get("IED")
        mpfed = task_row.get("MPFED")
        if pd.isna(ned) or pd.isna(ied) or pd.isna(mpfed):
            if endpoint_status in GATE_ENDPOINT_STATUSES:
                reason = "GATE_REACHED_MPFED_NULL"
            elif endpoint_status == "BLOCKED":
                reason = "ACCESS_REFUSED_MPFED_NULL"
            else:
                reason = "MPFED_NULL"
            rows.append(
                _row(
                    obs_id,
                    wt_id,
                    archetype,
                    False,
                    reason,
                    endpoint_status,
                    measurement_status=status,
                )
            )
            continue

        # 조건 4 — older-relevant KWCAG 기준 중 최소 1개가 UNDETERMINED 아님.
        n_older = int(older_n.get(obs_id, 0))
        all_undetermined = bool(older_undetermined_all.get(obs_id, True))
        if n_older == 0 or all_undetermined:
            rows.append(
                _row(
                    obs_id,
                    wt_id,
                    archetype,
                    False,
                    "KWCAG_ALL_UNDETERMINED",
                    measurement_status=status,
                )
            )
            continue

        rows.append(_row(obs_id, wt_id, archetype, True, None, measurement_status=status))

    return pd.DataFrame(rows, columns=_JOINT_VALIDITY_COLUMNS)


def _row(
    obs_id: Any,
    wt_id: Any,
    archetype: Any,
    is_valid: bool,
    reason: str | None,
    endpoint_status: Any = None,
    measurement_status: Any = None,
) -> dict[str, Any]:
    return {
        "observation_id": obs_id,
        "web_target_id": wt_id,
        "archetype": archetype,
        "is_joint_valid": is_valid,
        "exclusion_reason": reason,
        "endpoint_status": endpoint_status,
        "measurement_status": measurement_status,
    }


def joint_validity_summary(validity: pd.DataFrame) -> dict[str, Any]:
    """시도 N · joint-valid N · 제외 N을 **제외 사유별로 분해**해서 낸다 — 총계만
    주지 않는다(governor 지시). archetype별 분해도 함께 낸다 — 이 archetype별
    joint-valid N이 `EXCESS_DEPTH_INCLUDE_MIN_N`(n>=5) 가드가 세는 바로 그 n이다.
    """
    if validity.empty:
        return {
            "n_attempted": 0,
            "n_joint_valid": 0,
            "n_excluded": 0,
            "excluded_by_reason": dict.fromkeys(EXCLUSION_REASONS, 0),
            "behind_gate": {"n_services": 0, "by_endpoint_status": {}},
            "access_refusal": {"n_total": 0, "n_l1_blocked": 0, "n_l0_access_blocked": 0},
            "by_archetype": {},
        }

    n_attempted = len(validity)
    n_valid = int(validity["is_joint_valid"].sum())
    excluded = validity[~validity["is_joint_valid"]]
    excluded_by_reason = {
        reason: int((excluded["exclusion_reason"] == reason).sum()) for reason in EXCLUSION_REASONS
    }

    by_archetype: dict[str, Any] = {}
    for archetype, group in validity.dropna(subset=["archetype"]).groupby("archetype"):
        g_excluded = group[~group["is_joint_valid"]]
        by_archetype[str(archetype)] = {
            "n_attempted": len(group),
            "n_joint_valid": int(group["is_joint_valid"].sum()),
            "excluded_by_reason": {
                reason: int((g_excluded["exclusion_reason"] == reason).sum())
                for reason in EXCLUSION_REASONS
            },
        }

    # **대표기능이 인증/결제/본인확인 벽 뒤에 있는 서비스** — joint-valid에서
    # 빠졌다는 이유로 서술에서 사라지면 은폐다(governor 지시). entry friction에
    # 관한 실질 관측이므로 gate 종류별로 분해해 항상 보고한다.
    behind_gate = excluded[excluded["exclusion_reason"] == "GATE_REACHED_MPFED_NULL"]
    behind_gate_by_status = (
        behind_gate["endpoint_status"].astype(str).value_counts().to_dict()
        if not behind_gate.empty
        else {}
    )

    # **자동 접근이 거절된 건수** — WAF·403 같은 반응은 **우리 도구에 대한 반응**이지
    # 대상의 진입 설계가 아니다(Claude A 판정). gate(대상의 성질)와 합산하지 않고,
    # "N건은 자동 접근이 거절되어 진입 설계를 관측하지 못했다"로 따로 보고한다.
    n_l1_blocked = int((excluded["exclusion_reason"] == "ACCESS_REFUSED_MPFED_NULL").sum())
    n_l0_access_blocked = int(
        (excluded["measurement_status"].astype(str) == "FAILED_ACCESS_BLOCKED").sum()
    )

    return {
        "n_attempted": n_attempted,
        "n_joint_valid": n_valid,
        "n_excluded": n_attempted - n_valid,
        "excluded_by_reason": excluded_by_reason,
        "excluded_reason_is_target_property": dict(EXCLUSION_REASON_IS_TARGET_PROPERTY),
        "behind_gate": {
            "n_services": len(behind_gate),
            "by_endpoint_status": {str(k): int(v) for k, v in behind_gate_by_status.items()},
            "note": (
                "대표기능이 인증/결제/본인확인 벽 뒤에 있어 MPFED를 잴 수 없었던 서비스다. "
                "joint-valid 표본에서는 빠지지만 이것은 **대상의 성질**이며 entry friction에 "
                "관한 실질 관측이므로 별도로 보고한다 — transport/timeout(우리 쪽 사정)과 합산하지 않는다."
            ),
        },
        "access_refusal": {
            "n_total": n_l1_blocked + n_l0_access_blocked,
            "n_l1_blocked": n_l1_blocked,
            "n_l0_access_blocked": n_l0_access_blocked,
            "note": (
                "자동 접근이 거절되어 진입 설계를 관측하지 못한 건수다. L1 endpoint_status="
                "BLOCKED와 L0 measurement_status=FAILED_ACCESS_BLOCKED를 함께 센다. "
                "WAF·403은 **우리 도구에 대한 반응**이지 대상의 진입 설계가 아니므로 "
                "gate(대상의 성질)와 합산하지 않는다 — 접근 거절을 진입 장벽으로 세면 "
                "대상이 하지 않은 설계를 대상 탓으로 돌리게 된다."
            ),
        },
        "by_archetype": by_archetype,
    }
