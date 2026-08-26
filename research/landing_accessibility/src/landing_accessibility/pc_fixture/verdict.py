"""KWCAG criterion verdict 의미론 — 구성 시점(construction time)에 불변식을
강제한다. 후처리 guard 규칙에 의존하지 않는다.

닫는 결함:

    guard-blind-to-na-undetermined-laundering (CRITICAL, Pilot 감사)
        ``research/refcohort/src/refcohort/guard.py`` 의 ``na_not_pass``/
        ``undetermined_not_true`` 규칙은 ``applicable_count``/
        ``undetermined_count``/``fail_count`` 조합을 충분히 보지 않았다.
        위조 레코드 4종(모두 직접 실행해 재현됨)이 전부 무통과였다:
        UNDETERMINED 12건을 NA 로 라벨링, applicable_count=0 인데 PASS
        선언, NA 인데 fail_count=9 유지 등.

    undetermined-absorbed-into-pass (HIGH, Pilot 감사)
        ``research/refcohort/src/refcohort/criteria.py:76`` 의
        ``strict = FAIL if f>0 else (UNDET if u==total else PASS)`` 는
        6개 중 5개가 UNDETERMINED 여도 1개만 PASS 면 전체를 PASS 로
        보고했다(``observed_strict_pass='TRUE'``), metric=0.167 과 모순.

    두 결함의 공통 근본원인은 "위반 가능한 상태를 만들고 나서 나중에
    검사"하는 순서다. 여기서는 ``CriterionObservation`` 이 그 상태 자체를
    표현할 수 없게 한다 — ``__post_init__`` 이 실패하면 인스턴스가 아예
    존재하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

VERDICT_STATES = frozenset({"PASS", "FAIL", "UNDETERMINED", "NA"})


class VerdictSemanticError(ValueError):
    """CriterionObservation 이 표현하려는 상태가 판정 의미론을 위반한다."""


@dataclass(frozen=True)
class CriterionObservation:
    criterion_id: str
    applicable_count: int
    pass_count: int
    fail_count: int
    undetermined_count: int
    verdict_state: str
    # UNDETERMINED 인데 일부는 PASS 였던 항목 수. 보존은 하되 PASS 로
    # 승격하는 근거로 쓰지 않는다 (undetermined-absorbed-into-pass 재발 방지).
    partial_pass_count: int = 0
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.verdict_state not in VERDICT_STATES:
            raise VerdictSemanticError(
                f"{self.criterion_id}: 알 수 없는 verdict_state={self.verdict_state!r}"
            )
        for name, v in (
            ("applicable_count", self.applicable_count),
            ("pass_count", self.pass_count),
            ("fail_count", self.fail_count),
            ("undetermined_count", self.undetermined_count),
        ):
            if v < 0:
                raise VerdictSemanticError(f"{self.criterion_id}: {name}={v} 는 음수일 수 없다")

        counted = self.pass_count + self.fail_count + self.undetermined_count
        if counted != self.applicable_count:
            raise VerdictSemanticError(
                f"{self.criterion_id}: applicable_count={self.applicable_count} != "
                f"pass+fail+undetermined={counted} (항등식 위반)"
            )
        if self.applicable_count == 0 and self.verdict_state != "NA":
            raise VerdictSemanticError(
                f"{self.criterion_id}: applicable_count=0 인데 "
                f"verdict_state={self.verdict_state} (NA 여야 한다 — NA 세탁 차단)"
            )
        if self.applicable_count > 0 and self.verdict_state == "NA":
            raise VerdictSemanticError(
                f"{self.criterion_id}: applicable_count={self.applicable_count}>0 인데 "
                "verdict_state=NA (적용기회가 있는데 NA 로 세탁 차단)"
            )
        if self.fail_count > 0 and self.verdict_state != "FAIL":
            raise VerdictSemanticError(
                f"{self.criterion_id}: fail_count={self.fail_count}>0 인데 "
                f"verdict_state={self.verdict_state} (FAIL 이어야 한다)"
            )
        if (
            self.fail_count == 0
            and self.undetermined_count > 0
            and self.verdict_state != "UNDETERMINED"
        ):
            raise VerdictSemanticError(
                f"{self.criterion_id}: undetermined_count={self.undetermined_count}>0 인데 "
                f"verdict_state={self.verdict_state} — 부분 확인은 UNDETERMINED 로 남아야 하고 "
                "PASS 로 승격 금지 (undetermined-absorbed-into-pass 재발 차단)"
            )
        if (
            self.fail_count == 0
            and self.undetermined_count == 0
            and self.applicable_count > 0
            and self.verdict_state != "PASS"
        ):
            raise VerdictSemanticError(
                f"{self.criterion_id}: 전부 PASS 조건인데 verdict_state={self.verdict_state}"
            )
        if self.partial_pass_count > self.undetermined_count:
            raise VerdictSemanticError(
                f"{self.criterion_id}: partial_pass_count={self.partial_pass_count} > "
                f"undetermined_count={self.undetermined_count}"
            )


def derive_verdict_state(
    applicable_count: int, pass_count: int, fail_count: int, undetermined_count: int
) -> str:
    """올바른 순서: NA -> FAIL -> UNDETERMINED -> PASS. FAIL 이 UNDETERMINED 보다
    우선한다(하나라도 확정 FAIL 이면 부분 UNDETERMINED 여부와 무관하게 FAIL)."""
    if applicable_count == 0:
        return "NA"
    if fail_count > 0:
        return "FAIL"
    if undetermined_count > 0:
        return "UNDETERMINED"
    return "PASS"


def make_criterion_observation(
    criterion_id: str,
    pass_count: int,
    fail_count: int,
    undetermined_count: int,
    notes: list[str] | None = None,
) -> CriterionObservation:
    """개별 카운트로부터 항상 의미론적으로 일관된 관측을 만든다.

    호출자가 verdict_state 를 직접 고를 수 없다 — 상태는 카운트에서
    파생된다. 이것이 "UNDETERMINED->PASS 세탁"을 구조적으로 막는다.
    """
    applicable = pass_count + fail_count + undetermined_count
    state = derive_verdict_state(applicable, pass_count, fail_count, undetermined_count)
    partial = pass_count if (undetermined_count > 0 and fail_count == 0) else 0
    return CriterionObservation(
        criterion_id=criterion_id,
        applicable_count=applicable,
        pass_count=pass_count,
        fail_count=fail_count,
        undetermined_count=undetermined_count,
        verdict_state=state,
        partial_pass_count=partial,
        notes=notes or [],
    )
