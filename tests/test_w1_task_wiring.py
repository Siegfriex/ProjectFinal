"""E001 배치 러너 — task definition wiring 59/59 (`T-A-W1-001` §2, D-R0-07~09).

수용 기준은 "측정 가능해진 개수"가 아니라 **lineage 보존율 59/59** 다(`D-R0-08`).
이 파일의 핵심 테스트(`test_load_e001_full_targets_preserves_five_field_lineage_for_59_of_59`)
는 몇 건이 측정 가능해졌는지를 세지 않는다 — 상류 CSV의 다섯 필드가 조인·`TargetSpec`·
`TaskDefinition`까지 **정확히 같은 값으로** 도달했는지만 센다. `CODEBOOK_PENDING`인
행이 있어도(실제로 6행 있다 — `D-R0-41`의 UTILITY_ENTRY) 그 자체는 실패가 아니다:
그건 상류가 실제로 그 값을 실어 온 것이고, 이 파이프라인이 그 부재를 있는 그대로
옮겼다는 뜻이다(D-R0-09: 부재는 거부가 아니다).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.executor import default_task_definition  # noqa: E402
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402
from landing_accessibility.engine.firewall import load_e001_full_targets  # noqa: E402
from landing_accessibility.engine.vocabulary import RegionSignalType  # noqa: E402


def _spec_from_row(row) -> TargetSpec:
    """`scripts/run_e001_real.py` `_worker_plan`과 정확히 같은 필드 매핑."""
    return TargetSpec(
        target_id=row.target_id,
        canonical_service_key=row.canonical_service_key,
        official_url=row.official_url,
        interaction_archetype=row.interaction_archetype,
        endpoint_definition=row.endpoint_definition,
        service_name_canonical=row.service_name_canonical,
        task_id=row.task_id,
        region_definition=row.region_definition,
        region_signal_type=row.region_signal_type,
        endpoint_signal_type=row.endpoint_signal_type,
    )


# ══════════════════════════════════════════════════════════════════════════
# 1. 실제 동결 계획 — loader 단계에서 다섯 필드가 조인되는가 (firewall.py:542-730)
# ══════════════════════════════════════════════════════════════════════════
def test_load_e001_full_targets_preserves_five_field_lineage_for_59_of_59():
    """실제 `E001_MASTER_PLAN.json` + P-B CSV 조인 결과 — 상류 CSV의 다섯 필드
    (`task_id`·`region_definition`·`region_signal_type`·`endpoint_definition`·
    `endpoint_signal_type`)가 **59행 전건**에서 `E001TargetRow`까지 도달한다.

    이전에는 이 로더(`load_e001_full_targets`)가 `endpoint_definition`·`task_id`만
    옮기고 나머지 셋을 CSV에서 읽고도 버렸다 — 그게 이 lineage 단절의 실제 지점
    이었다(CSV 자체는 71행 전건에 다섯 필드가 다 있었다).
    """
    rows = load_e001_full_targets()
    assert len(rows) == 59, f"동결 순서 n=59 가 아니다: {len(rows)}"

    missing: dict[str, list[str]] = {
        "task_id": [],
        "region_definition": [],
        "region_signal_type": [],
        "endpoint_signal_type": [],
    }
    for row in rows:
        if row.task_id is None:
            missing["task_id"].append(row.target_id)
        if row.region_definition is None:
            missing["region_definition"].append(row.target_id)
        if row.region_signal_type is None:
            missing["region_signal_type"].append(row.target_id)
        if row.endpoint_signal_type is None:
            missing["endpoint_signal_type"].append(row.target_id)

    # `endpoint_definition`은 이미 이전부터 옮겨지고 있었다 — 회귀만 확인한다.
    missing_endpoint_definition = [r.target_id for r in rows if r.endpoint_definition is None]

    assert missing["task_id"] == [], f"task_id 누락: {missing['task_id']}"
    assert missing["region_definition"] == [], f"region_definition 누락: {missing['region_definition']}"
    assert missing["region_signal_type"] == [], (
        f"region_signal_type 누락: {missing['region_signal_type']}"
    )
    assert missing["endpoint_signal_type"] == [], (
        f"endpoint_signal_type 누락: {missing['endpoint_signal_type']}"
    )
    assert missing_endpoint_definition == [], f"endpoint_definition 누락: {missing_endpoint_definition}"


def test_task_wiring_lineage_survives_targetspec_and_taskdefinition_for_59_of_59():
    """`E001TargetRow` → `TargetSpec`(`run_e001_real._worker_plan`과 같은 매핑) →
    `TaskDefinition`(`executor.default_task_definition`)까지 **값이 그대로**
    도달하는가. `CODEBOOK_PENDING`인 행이 섞여 있어도(D-R0-41의 UTILITY_ENTRY 6행)
    그 자체는 lineage 실패가 아니다 — 상류가 실제로 그 값을 실었다.
    """
    rows = load_e001_full_targets()
    codebook_pending_count = 0
    for row in rows:
        spec = _spec_from_row(row)
        task = default_task_definition(spec)

        assert task.task_id == row.task_id, row.target_id
        assert task.region_definition == row.region_definition, row.target_id
        assert task.endpoint_definition == row.endpoint_definition, row.target_id

        if not task.mapping_frozen_allowed():
            codebook_pending_count += 1
            # `D-R0-09` — CODEBOOK_PENDING 은 부재이지 거부가 아니다. 그 행이 CSV에서
            # 실제로 CODEBOOK_PENDING을 실어 왔을 때만 이 상태여야 한다(이 함수가
            # 임의로 골라 채운 게 아니라는 것).
            assert (
                row.region_signal_type == RegionSignalType.CODEBOOK_PENDING.value
                or row.endpoint_signal_type == RegionSignalType.CODEBOOK_PENDING.value
            ), (
                f"{row.target_id}: mapping_frozen_allowed=False 인데 CSV 원본에는 "
                f"CODEBOOK_PENDING 이 없다 — 이 함수가 값을 지어냈다는 뜻이다"
            )

    # D-R0-41 — Branch U(UTILITY_ENTRY) 6행이 frozen operational definition 상 여전히
    # CODEBOOK_PENDING이다. 이 숫자가 달라지면(0이 되거나 6이 아니면) CSV 자체가
    # 바뀌었거나 이 파이프라인이 값을 흡수/왜곡하고 있다는 신호다.
    assert codebook_pending_count == 6, (
        f"CODEBOOK_PENDING 행 수가 예상(6, D-R0-41 UTILITY_ENTRY)과 다르다: "
        f"{codebook_pending_count}"
    )


# ══════════════════════════════════════════════════════════════════════════
# 2. `default_task_definition` — 인자 무관 상수 하드코딩이 사라졌는가
# ══════════════════════════════════════════════════════════════════════════
def test_default_task_definition_is_no_longer_a_constant_regardless_of_input():
    """옛 결함: `default_task_definition`이 `target`을 받으면서도 `region_definition=
    None`·`endpoint_definition=None`·양쪽 signal_type=`CODEBOOK_PENDING`을 **인자와
    무관한 상수**로 반환했다. 이제는 `target`이 실어 온 값이 그대로 나온다 —
    서로 다른 두 `target`이 서로 다른 `TaskDefinition`을 낸다는 것으로 확인한다.
    """
    wired = TargetSpec(
        target_id="wt-wired",
        canonical_service_key="wired",
        official_url="https://example.com/never-opened",
        interaction_archetype="ITEM_DETAIL",
        task_id="task_wired",
        region_definition="상품 목록 카드가 노출",
        region_signal_type="DOM_AX_ROLE",
        endpoint_definition="상품 상세 화면 진입",
        endpoint_signal_type="URL_PATTERN",
    )
    unwired = TargetSpec(
        target_id="wt-unwired",
        canonical_service_key="unwired",
        official_url="https://example.com/never-opened",
        interaction_archetype="ITEM_DETAIL",
    )

    wired_task = default_task_definition(wired)
    unwired_task = default_task_definition(unwired)

    assert wired_task.task_id == "task_wired"
    assert wired_task.region_definition == "상품 목록 카드가 노출"
    assert wired_task.endpoint_definition == "상품 상세 화면 진입"
    assert wired_task.region_signal_type is RegionSignalType.DOM_AX_ROLE
    assert wired_task.endpoint_signal_type is RegionSignalType.URL_PATTERN
    assert wired_task.mapping_frozen_allowed() is True

    # `target`에 실려 온 게 없으면(P-A codebook 미동결) 그 부재를 정직하게 옮긴다 —
    # 이 함수가 지어내지 않는다.
    assert unwired_task.region_definition is None
    assert unwired_task.endpoint_definition is None
    assert unwired_task.region_signal_type is RegionSignalType.CODEBOOK_PENDING
    assert unwired_task.mapping_frozen_allowed() is False

    assert wired_task != unwired_task, "두 target 이 서로 다른데 같은 TaskDefinition 이 나왔다"


def test_resolve_signal_type_does_not_fabricate_unknown_values():
    """CSV의 signal type 문자열이 비어 있거나 이 엔진이 모르는 값이면
    `CODEBOOK_PENDING` — 값을 지어내지 않는다."""
    from landing_accessibility.e001_runner.executor import _resolve_signal_type

    assert _resolve_signal_type(None) is RegionSignalType.CODEBOOK_PENDING
    assert _resolve_signal_type("") is RegionSignalType.CODEBOOK_PENDING
    assert _resolve_signal_type("NOT_A_REAL_SIGNAL_TYPE") is RegionSignalType.CODEBOOK_PENDING
    assert _resolve_signal_type("DOM_AX_ROLE") is RegionSignalType.DOM_AX_ROLE
    assert _resolve_signal_type("URL_PATTERN") is RegionSignalType.URL_PATTERN
