"""P-B — `shadow_provenance.py` REAL-TARGET FIREWALL (`PHASE_GATES.md` §4.5) + §4.3 provenance."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.shadow_provenance import (  # noqa: E402
    ALLOWED_BEFORE_P0_CLOSE,
    RealTargetFirewallError,
    require_execution_mode,
    shadow_provenance,
)


def test_fixture_and_shadow_dry_run_allowed() -> None:
    assert require_execution_mode("FIXTURE") == "FIXTURE"
    assert require_execution_mode("SHADOW_DRY_RUN") == "SHADOW_DRY_RUN"


def test_real_target_hard_fails() -> None:
    with pytest.raises(RealTargetFirewallError):
        require_execution_mode("REAL_TARGET")


def test_unknown_mode_hard_fails() -> None:
    with pytest.raises(RealTargetFirewallError):
        require_execution_mode("SOMETHING_ELSE")


def test_allowed_set_matches_phase_gates_4_5() -> None:
    assert {"FIXTURE", "SHADOW_DRY_RUN"} == ALLOWED_BEFORE_P0_CLOSE


def test_shadow_provenance_block_has_required_fields() -> None:
    block = shadow_provenance(shadow_lane="P-B", execution_mode="SHADOW_DRY_RUN")
    for field in (
        "base_sha",
        "created_at",
        "created_before_p0_close",
        "authoritative",
        "real_target_outcome_used",
        "requires_post_p0_reconciliation",
        "shadow_lane",
    ):
        assert field in block, f"§4.3 필수 필드 {field} 누락"
    assert block["created_before_p0_close"] is True
    assert block["authoritative"] is False
    assert block["real_target_outcome_used"] is False
    assert block["requires_post_p0_reconciliation"] is True
    assert block["shadow_lane"] == "P-B"
    assert block["base_sha"] == "d5f1da5"


def test_shadow_provenance_rejects_real_target() -> None:
    with pytest.raises(RealTargetFirewallError):
        shadow_provenance(shadow_lane="P-B", execution_mode="REAL_TARGET")
