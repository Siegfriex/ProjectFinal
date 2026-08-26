"""P-C L0/L1 측정 엔진 — **fixture 전용 SHADOW 산출물**.

    status                          = SHADOW_PREPARATORY
    shadow_lane                     = LANE_C
    base_sha                        = d5f1da5652953542d5c8be377026cc3293f2075a
    created_before_p0_close         = true
    authoritative                   = false
    real_target_outcome_used        = false
    fixture_only                    = true
    real_target_measurement         = false
    requires_post_p0_reconciliation = true

이 패키지가 내는 PASS/FAIL 은 **synthetic fixture 에 대한 engine test 결과**다.
실제 서비스에 대한 research finding 이 아니며 그렇게 인용할 수 없다
(`PHASE_GATES §4.1` · `§4.3` · `§4.6`).

권위 근거: `docs/v2/PHASE_GATES.md` · `02_COLLECTION_MEASUREMENT_SPEC_v2.0.md` ·
`A1_MEASUREMENT_OPERATIONALIZATION.md` · `A2_VOCABULARY_AND_SCHEMA_BINDING.md` ·
`docs/07_EVIDENCE_MANIFEST_CONTRACT.md`.
"""

from __future__ import annotations

from .firewall import (
    ExecutionMode,
    FirewallError,
    NavigationBlockedError,
    RealTargetBlockedError,
    UnknownExecutionModeError,
    assert_mode_allowed,
    assert_navigation_allowed,
    firewall_state,
    real_target_permitted,
)
from .provenance import PROTOCOL_VERSION, ShadowProvenance, validate_provenance

__all__ = [
    "PROTOCOL_VERSION",
    "ExecutionMode",
    "FirewallError",
    "NavigationBlockedError",
    "RealTargetBlockedError",
    "ShadowProvenance",
    "UnknownExecutionModeError",
    "assert_mode_allowed",
    "assert_navigation_allowed",
    "firewall_state",
    "real_target_permitted",
    "validate_provenance",
]
