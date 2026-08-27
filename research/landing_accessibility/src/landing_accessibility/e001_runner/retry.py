"""자동 복구 정책 — transient 실패에 **정확히 1회**만 재시도한다.

## 왜 상수를 하드코드하고 파라미터로 노출하지 않는가

"결과를 보고 재시도 횟수를 늘린다"(optional stopping)는 이 연구 전체가 금지하는
패턴이다 — `landing_accessibility.engine.evidence.select_canonical_run`이
`verdict_state`를 인자로 받을 수 없게 만들어 같은 사고를 막은 것과 정확히 같은
이유다. 재시도 상한을 함수 인자로 노출하면 언젠가 "이 target만 3번 봐주자"는
호출이 생기고, 그 순간부터 실패율이 재시도 정책이 아니라 운영자의 재량이 된다.
그래서 `MAX_RETRIES_PER_TARGET`은 모듈 상수이고, `run_with_retry`의 시그니처에는
그것을 넓힐 수 있는 자리가 **존재하지 않는다.**

## 정책

    attempt 1 실패 → 원인을 분류한다 → attempt 2(재시도) 시도
    attempt 2 도 실패 → 원인이 같든 다르든 **더 이상 시도하지 않는다**
                        → `SKIPPED_RETRY_EXHAUSTED` 로 기록하고 다음 target으로

가드 위반(`AccountActionBlockedError`)과 firewall 위반은 transient 실패가
아니므로 재시도 대상에서 제외한다 — 그대로 위로 전파한다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .guard import AccountActionBlockedError
from .outcomes import TargetOutcome, classify_exception

#: **이 값을 넓히는 파라미터는 이 모듈 어디에도 없다.** 정책을 바꾸려면 이 상수
#: 자체를 고치는 커밋이 있어야 하고, 그 커밋은 감사 대상이 된다
#: (`landing_accessibility.engine.firewall`이 P0 게이트를 여는 방법을 코드 수정
#:  하나로 제한한 것과 같은 설계).
MAX_RETRIES_PER_TARGET: int = 1

#: 재시도하지 않고 즉시 전파해야 하는 예외 — transient 실패가 아니라 범위/설정 위반.
_NON_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (AccountActionBlockedError,)


@dataclass
class RetryOutcome:
    """`run_with_retry`의 결과. `attempts`는 항상 `1 <= attempts <= 1 + MAX_RETRIES_PER_TARGET`."""

    succeeded: bool
    attempts: int
    value: object | None = None
    final_outcome: TargetOutcome | None = None
    attempt_outcomes: list[TargetOutcome] = field(default_factory=list)
    same_cause_on_retry: bool | None = None
    last_error: str | None = None


def run_with_retry[T](fn: Callable[[], T]) -> RetryOutcome:
    """`fn`을 최대 `1 + MAX_RETRIES_PER_TARGET`번 호출한다. 그 이상은 절대 없다.

    `fn`은 인자를 받지 않는 thunk다 — 호출부가 매 시도마다 무엇을 다시 시도할지
    스스로 클로저로 캡슐화한다.
    """
    attempt_outcomes: list[TargetOutcome] = []
    last_error: str | None = None

    attempt = 0
    while True:
        attempt += 1
        try:
            value = fn()
            return RetryOutcome(
                succeeded=True,
                attempts=attempt,
                value=value,
                final_outcome=TargetOutcome.MEASURED,
                attempt_outcomes=attempt_outcomes,
            )
        except _NON_RETRYABLE_EXCEPTIONS:
            raise
        except Exception as exc:
            outcome = classify_exception(exc)
            attempt_outcomes.append(outcome)
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt > MAX_RETRIES_PER_TARGET:
                same_cause = (
                    len(attempt_outcomes) >= 2 and attempt_outcomes[-1] == attempt_outcomes[-2]
                )
                return RetryOutcome(
                    succeeded=False,
                    attempts=attempt,
                    final_outcome=TargetOutcome.SKIPPED_RETRY_EXHAUSTED,
                    attempt_outcomes=attempt_outcomes,
                    same_cause_on_retry=same_cause,
                    last_error=last_error,
                )
            # 정확히 MAX_RETRIES_PER_TARGET 번만 더 시도하고 루프 상단에서 다시 시도한다.
            continue


__all__ = ["MAX_RETRIES_PER_TARGET", "RetryOutcome", "run_with_retry"]
