"""Depth 산출 — `A1 §1` · `§2` / `A2 §1.5`.

`02 §9` 가 activation 으로 인정하지 않는 행위(문자 단위 입력·passive loading·redirect·
server wait·scroll·popup dismiss)는 **step row 자체를 만들지 않는다** (`A2` 규칙 D-2).
그러므로 이 모듈은 "activation 목록"만 받고, 제외 규칙은 그 목록을 만드는 쪽(scout)이 지킨다.

`NULL` 을 `0` 이나 예산 상한값으로 대체하지 않는다 — 금지 전이 **X-5**.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .vocabulary import (
    AreaSignalStatus,
    DepthSegment,
    EndpointStatus,
    EndpointStatusDetail,
    GateKind,
    InteractionArchetype,
)

if TYPE_CHECKING:  # pragma: no cover - 순환 임포트를 피한다
    from .gate_classifier import GateKindDecision


class DepthRuleError(ValueError):
    """`A1 §1` / `A2 §1.5` 규칙 위반."""


#: `A2 §1.5.1a` 규칙 E-6a — `00 §3` L1 표가 **그 행에 명시한 종류의 gate** 만 endpoint 다.
#: 금융 행: `또는 로그인/인증 gate`. 커뮤니티 행: `또는 로그인 gate` (인증은 없다).
#: 나머지 5 archetype 은 `00 §3` 에 gate 문구가 없으므로 공집합이다 (규칙 E-6 확대 금지).
ENDPOINT_GATE_KINDS: dict[InteractionArchetype, frozenset[GateKind]] = {
    InteractionArchetype.FINANCIAL_ACTION_ENTRY: frozenset(
        {GateKind.LOGIN, GateKind.IDENTITY_VERIFICATION}
    ),
    InteractionArchetype.COMMUNICATION_ENTRY: frozenset({GateKind.LOGIN}),
    InteractionArchetype.QUERY: frozenset(),
    InteractionArchetype.CONTENT_OPEN: frozenset(),
    InteractionArchetype.ITEM_DETAIL: frozenset(),
    InteractionArchetype.PLACE_LOOKUP: frozenset(),
    InteractionArchetype.UTILITY_ENTRY: frozenset(),
}


def gate_outcome(
    archetype: InteractionArchetype,
    gate_kind: GateKind,
    *,
    personal_data_required: bool = False,
) -> tuple[EndpointStatus, EndpointStatusDetail | None]:
    """관측된 gate 를 `02 §7` 의 7값 중 하나로 보낸다.

    `A2 §1.5.1a` 규칙 E-5 / E-6 / E-6a 의 표 그대로다. **미매핑을 남기지 않는다** —
    `COMMUNICATION_ENTRY` 의 본인인증 gate처럼 endpoint 가 아닌 gate 도 갈 자리가 있다.
    """
    if gate_kind is GateKind.PAYMENT:
        return EndpointStatus.PAYMENT_GATE_REACHED, None
    if gate_kind is GateKind.CAPTCHA:
        return EndpointStatus.CAPTCHA, None
    if gate_kind is GateKind.PERSONAL_DATA:
        return EndpointStatus.PERSONAL_DATA_REQUIRED, None

    if gate_kind in ENDPOINT_GATE_KINDS[archetype]:
        # 규칙 E-5 — `00 §3` 이 그 행의 endpoint 정의 안에 넣은 종류의 gate 다.
        return (
            EndpointStatus.FUNCTION_ENDPOINT_REACHED,
            EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE,
        )
    if personal_data_required:
        return EndpointStatus.PERSONAL_DATA_REQUIRED, None
    return EndpointStatus.AUTH_GATE_REACHED, None


def assert_detail_rollup(
    status: EndpointStatus,
    detail: EndpointStatusDetail | None,
    archetype: InteractionArchetype,
) -> None:
    """`A2 §1.5.2` roll-up 규칙 + 규칙 E-6 / E-6a 를 강제한다.

    주입 I-1 · I-2 · I-3 이 여기서 막힌다.
    """
    from .vocabulary import DETAIL_ROLLUP

    if detail is None:
        if status is EndpointStatus.FUNCTION_ENDPOINT_REACHED:
            return
        return
    expected = DETAIL_ROLLUP[detail]
    if expected is not status:
        raise DepthRuleError(
            f"roll-up 위반: {detail.value} 의 상위 값은 {expected.value} 인데 "
            f"{status.value} 로 기록됐다 (A2 §1.5.2 · 규칙 S-3)"
        )
    if detail is EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE and not ENDPOINT_GATE_KINDS[archetype]:
        raise DepthRuleError(
            f"{archetype.value} 는 `00 §3` 에 gate 문구가 없다 — "
            "ENDPOINT_VIA_AUTH_GATE 를 붙이는 것은 규칙 E-6 확대 금지 위반이다 (주입 I-2)"
        )


def assert_gate_endpoint_allowed(archetype: InteractionArchetype, gate_kind: GateKind) -> None:
    """규칙 E-6a — 그 archetype 이 그 **종류의** gate 를 endpoint 로 인정하는가 (주입 I-3)."""
    if gate_kind not in ENDPOINT_GATE_KINDS[archetype]:
        allowed = sorted(g.value for g in ENDPOINT_GATE_KINDS[archetype])
        raise DepthRuleError(
            f"{archetype.value} 에서 {gate_kind.value} gate 는 endpoint 가 아니다. "
            f"`00 §3` 이 그 행에 준 gate 종류: {allowed or '없음'} (규칙 E-6a · 주입 I-3)"
        )


@dataclass(frozen=True)
class DepthResult:
    """`A1 §1.3` ~ `§1.5` 의 산출. `NULL` 은 파이썬 `None` 이다 (`0` 이 아니다)."""

    ned: int | None
    ied: int | None
    mpfed: int | None
    area_signal_status: AreaSignalStatus
    endpoint_status: EndpointStatus
    endpoint_status_detail: EndpointStatusDetail | None
    endpoint_reached: int

    def as_dict(self) -> dict[str, object]:
        return {
            "NED": self.ned,
            "IED": self.ied,
            "MPFED": self.mpfed,
            "area_signal_status": self.area_signal_status.value,
            "endpoint_status": self.endpoint_status.value,
            "endpoint_status_detail": (
                self.endpoint_status_detail.value if self.endpoint_status_detail else None
            ),
            "endpoint_reached": self.endpoint_reached,
        }


def compute_depth(
    *,
    archetype: InteractionArchetype,
    area_step_index: int | None,
    endpoint_step_index: int | None,
    endpoint_status: EndpointStatus,
    endpoint_status_detail: EndpointStatusDetail | None = None,
) -> DepthResult:
    """`A1 §1.3` 산출식 + `§1.4` 동시성립·역전 규칙 + `§1.5` 미관측 표.

        k = min{ i : s_i 에서 FUNCTION_AREA_REACHED 성립 }
        m = min{ i : s_i 에서 FUNCTION_ENDPOINT_REACHED 성립 }
        NED = k,  IED = m - k,  MPFED = m

    `endpoint_status` 는 scout 가 이미 `02 §7` 의 7값 중 하나로 확정한 값을 받는다.
    이 함수는 그 값과 정합하지 않는 depth 를 만들지 않는다.
    """
    assert_detail_rollup(endpoint_status, endpoint_status_detail, archetype)
    reached = endpoint_status is EndpointStatus.FUNCTION_ENDPOINT_REACHED

    if reached and endpoint_step_index is None:
        raise DepthRuleError(
            "FUNCTION_ENDPOINT_REACHED 인데 endpoint step 이 없다 — "
            "이 조합에서 MPFED 가 NULL 인 경우는 없다 (A2 §1.5.1)"
        )
    if not reached:
        # `A1 §1.5` — endpoint 전 종료. 영역만 관측됐으면 NED 는 남고 IED/MPFED 는 NULL.
        if area_step_index is None:
            return DepthResult(
                None,
                None,
                None,
                AreaSignalStatus.NOT_OBSERVED,
                endpoint_status,
                endpoint_status_detail,
                0,
            )
        return DepthResult(
            area_step_index,
            None,
            None,
            AreaSignalStatus.OBSERVED,
            endpoint_status,
            endpoint_status_detail,
            0,
        )

    m = int(endpoint_step_index or 0)
    if area_step_index is None or area_step_index > m:
        # `A1 §1.4` 역전 — k := m 으로 소급 확정. 추정이 아니라 논리적 강제다.
        return DepthResult(
            m,
            0,
            m,
            AreaSignalStatus.INFERRED_FROM_ENDPOINT,
            endpoint_status,
            endpoint_status_detail,
            1,
        )
    k = int(area_step_index)
    return DepthResult(
        k, m - k, m, AreaSignalStatus.OBSERVED, endpoint_status, endpoint_status_detail, 1
    )


def assign_depth_segments(step_count: int, depth: DepthResult) -> list[DepthSegment]:
    """`A1 §1.7` step 단위 귀속. scout 종료 시점에 **일괄** 확정한다.

    저장된 step 신호(`area_signal_detected` · `endpoint_signal_detected`)만으로
    제3자가 재계산 가능해야 한다 (`A2` 규칙 D-1) — 그래서 이 함수는 저장값만 입력으로 받는다.

    `W2` 결함 시정 — `MPFED = NULL`(endpoint 미도달, `D-R0-20` partial depth)인데도
    이전 구현은 `m = depth.mpfed if ... else step_count`로 **NULL을 상한값으로 대체**해서
    region 관측 이후의 step 을 `IED`로 잘못 라벨링했다. `IED`는 `m`(MPFED)이 확정된
    경우에만 정의된다 — `m`이 없으면 `k` 이후 step은 `UNASSIGNED`다 (금지 전이 X-5의
    step-라벨 버전: NULL을 다른 값으로 채우지 않는다).
    """
    if depth.area_signal_status is AreaSignalStatus.NOT_OBSERVED:
        return [DepthSegment.UNASSIGNED] * step_count
    k = depth.ned if depth.ned is not None else 0
    if depth.mpfed is None:
        # endpoint 가 확정되지 않았다 — k 이후를 IED 로 채울 근거(m)가 없다.
        return [DepthSegment.NED if i <= k else DepthSegment.UNASSIGNED for i in range(1, step_count + 1)]
    m = depth.mpfed
    out: list[DepthSegment] = []
    for i in range(1, step_count + 1):
        if i <= k:
            out.append(DepthSegment.NED)
        elif i <= m:
            out.append(DepthSegment.IED)
        else:  # `A1 §1.7` — endpoint 이후 activation 은 발생하지 않는다 (02 §7 즉시종료)
            raise DepthRuleError(
                f"endpoint(m={m}) 이후에 activation step {i} 이 있다 — "
                "규칙 E-7 gate 통과 금지 / `02 §7` 즉시종료 위반이다 (주입 I-5)"
            )
    return out


def auth_gate_before_endpoint(
    *,
    auth_gate_detected_per_step: list[int],
    endpoint_status_detail: EndpointStatusDetail | None,
) -> int:
    """`A2 §1.5.1a` 규칙 E-9.

        auth_gate_before_endpoint =
          1  if EXISTS step: auth_gate_detected = 1 AND 그 step 이 endpoint 를 실현한 gate step 이 아니다

    "endpoint 를 실현한 gate step" 은 정확히 하나 — `ENDPOINT_VIA_AUTH_GATE` 인 task 의
    **마지막 step** 이다. 허용값은 `0`/`1` 이며 `NULL` 을 쓰지 않는다 (주입 I-8).
    """
    steps = list(auth_gate_detected_per_step)
    if endpoint_status_detail is EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE and steps:
        steps = steps[:-1]  # endpoint 자체인 gate 는 `before` 로 세지 않는다 (주입 I-7)
    return int(any(bool(s) for s in steps))


def auth_gate_observed(
    *,
    auth_gate_before_endpoint_value: int,
    endpoint_status_detail: EndpointStatusDetail | None,
) -> int:
    """`A2 §1.5.1a` 규칙 E-8 — 2항 합집합.

        auth_gate_observed = (auth_gate_before_endpoint = 1)
                          OR (endpoint_status_detail = 'ENDPOINT_VIA_AUTH_GATE')

    `endpoint_status = 'AUTH_GATE_REACHED'` 단독 집계는 두 archetype 에서
    **0 으로 과소집계**된다 (주입 I-6).
    """
    return int(
        bool(auth_gate_before_endpoint_value)
        or endpoint_status_detail is EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE
    )


def gate_outcome_from_decision(
    archetype: InteractionArchetype,
    decision: GateKindDecision,
    *,
    personal_data_required: bool = False,
) -> tuple[EndpointStatus, EndpointStatusDetail | None]:
    """판별 결과를 `02 §7` 의 7값으로 보낸다 — Q-9 의 abstain 경로 포함.

    **판별이 확정되지 않으면 archetype 을 가리지 않고 `AUTH_GATE_REACHED` 다.**
    `A2 §1.5.1a`: *codebook 이 가르지 못한 gate 는 `endpoint_definition` 미충족으로 보아
    endpoint 로 승격시키지 않는다 — 모호할 때 endpoint 로 올리는 방향의 기본값을 두지 않는다.*

    `FINANCIAL_ACTION_ENTRY` 에서는 로그인·본인인증이 **둘 다** endpoint 이므로
    "둘 중 하나면 어차피 endpoint" 라는 반론이 가능하지만, `UNDETERMINED` 는
    *둘 중 하나임이 확실하다* 가 아니라 *무엇인지 모른다* 이므로 그 반론은 성립하지 않는다.
    """
    if decision.resolved and decision.gate_kind is not None:
        return gate_outcome(
            archetype, decision.gate_kind, personal_data_required=personal_data_required
        )
    if personal_data_required:
        return EndpointStatus.PERSONAL_DATA_REQUIRED, None
    return EndpointStatus.AUTH_GATE_REACHED, None
