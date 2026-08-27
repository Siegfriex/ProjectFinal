"""`E001_PLAN` 로더 — Worker E가 만든 `E000_PLAN.json` 형식과 호환된다.

`shadow/e000_plan/E000_PLAN.json`의 `targets[]` 각 행은 이 로더가 요구하는
최소 필드(`target_id`, `canonical_service_key`, `official_url`,
`interaction_archetype`)를 전부 갖는다. `plan_kind`가 `"E000_PLAN"`이든
`"E001_PLAN"`이든 구조가 같으면 그대로 읽는다 — E001이 E000의 target frame을
그대로 이어받는 관계이기 때문이다 (`PHASE_GATES.md` E000→E001 순서).

**이 모듈은 `official_url`을 어디에도 navigate하지 않는다.** 여기서 하는 일은
JSON을 파싱해 `TargetSpec` 목록을 만드는 것뿐이다. FIXTURE 모드 실행에서
실제로 여는 파일은 `TargetSpec.fixture_override`이며, 그 필드가 없는 target은
FIXTURE 실행기가 애초에 열 수 있는 URL이 없다 (`executor.py` 참고).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PlanValidationError(ValueError):
    """`E001_PLAN`/`E000_PLAN` 형식 계약 위반."""


_REQUIRED_TARGET_FIELDS: tuple[str, ...] = (
    "target_id",
    "canonical_service_key",
    "official_url",
    "interaction_archetype",
)


@dataclass(frozen=True)
class TargetSpec:
    """`E001_PLAN.targets[]` 한 행의 이 러너용 최소 투영.

    `fixture_override`는 **이 러너가 추가한 테스트 전용 필드**다 — 원본
    `E000_PLAN.json` 스키마에는 없다. FIXTURE 모드 실행기는 이 필드가 있는
    target만 열 수 있고, `official_url`은 절대 읽지 않는다 (`executor.py`).
    """

    target_id: str
    canonical_service_key: str
    official_url: str
    interaction_archetype: str
    e000_id: str | None = None
    endpoint_definition: str | None = None
    service_name_canonical: str | None = None
    fixture_override: str | None = None

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> TargetSpec:
        missing = [f for f in _REQUIRED_TARGET_FIELDS if not row.get(f)]
        if missing:
            raise PlanValidationError(
                f"target 행에 필수 필드가 없다: {missing} (행: {row.get('target_id', '?')!r})"
            )
        return cls(
            target_id=str(row["target_id"]),
            canonical_service_key=str(row["canonical_service_key"]),
            official_url=str(row["official_url"]),
            interaction_archetype=str(row["interaction_archetype"]),
            e000_id=row.get("e000_id"),
            endpoint_definition=row.get("endpoint_definition"),
            service_name_canonical=row.get("service_name_canonical"),
            fixture_override=row.get("fixture_override"),
        )

    def with_fixture_override(self, fixture_name: str) -> TargetSpec:
        """FIXTURE 모드 테스트용 — target을 로컬 fixture 파일에 묶는다.

        원본 dataclass는 frozen이므로 새 인스턴스를 돌려준다. `official_url`은
        건드리지 않는다 — 그대로 남지만 FIXTURE 실행기는 이 필드를 읽지 않는다.
        """
        from dataclasses import replace

        return replace(self, fixture_override=fixture_name)


def load_plan(path: str | Path) -> list[TargetSpec]:
    """`E001_PLAN`/`E000_PLAN` JSON 파일을 읽어 `TargetSpec` 목록으로 돌려준다."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return load_plan_dict(data)


def load_plan_dict(data: dict[str, Any]) -> list[TargetSpec]:
    plan_kind = data.get("plan_kind")
    if plan_kind not in (None, "E000_PLAN", "E000_FAST_PLAN", "E001_PLAN"):
        raise PlanValidationError(
            f"plan_kind 는 E000_PLAN/E000_FAST_PLAN/E001_PLAN 만 이 러너와 호환된다: {plan_kind!r}"
        )
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise PlanValidationError("targets 배열이 비어 있거나 없다")

    specs = [TargetSpec.from_dict(row) for row in targets]

    ids = [s.target_id for s in specs]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise PlanValidationError(f"target_id 중복: {dupes}")

    return specs


def validate_no_real_navigation_fields_required(specs: list[TargetSpec]) -> None:
    """FIXTURE 실행 전 호출 — `fixture_override` 없는 target이 하나라도 있으면 실패한다.

    FIXTURE 모드 배치를 돌리기 전 명시적으로 이걸 부르면, "fixture_override를
    깜빡해서 official_url로 새 나갈 뻔했다"는 사고가 개별 target 실행 중이
    아니라 **배치 시작 전에** 드러난다.
    """
    missing = [s.target_id for s in specs if not s.fixture_override]
    if missing:
        raise PlanValidationError(
            f"FIXTURE 실행에는 모든 target에 fixture_override 가 있어야 한다. "
            f"없는 target: {missing} — official_url 은 FIXTURE 모드에서 열리지 않는다."
        )


def validate_real_target_scope_allowlist(
    specs: list[TargetSpec], *, scope: object = None, allowlist: object = None
) -> object:
    """실제 수집 배치 시작 **전에** 모든 target 이 scope allowlist 안인지 확인한다.

    개별 target 실행 중이 아니라 배치 시작 전에 실패하게 만드는 것이 목적이다 —
    "6개 중 4번째에서야 목록 밖 target 이 드러나 3개는 이미 열려 버렸다" 는 상황을
    만들지 않는다.
    """
    from landing_accessibility.engine.firewall import (
        ExecutionScope,
        assert_target_allowlisted,
        load_scope_allowlist,
    )

    resolved_scope = scope if scope is not None else ExecutionScope.E000_FAST
    resolved_list = allowlist or load_scope_allowlist(resolved_scope)
    for spec in specs:
        assert_target_allowlisted(
            resolved_scope,
            target_id=spec.target_id,
            url=spec.official_url,
            canonical_service_key=spec.canonical_service_key,
            allowlist=resolved_list,  # type: ignore[arg-type]
        )
    return resolved_list


__all__ = [
    "PlanValidationError",
    "TargetSpec",
    "load_plan",
    "load_plan_dict",
    "validate_no_real_navigation_fields_required",
    "validate_real_target_scope_allowlist",
]
