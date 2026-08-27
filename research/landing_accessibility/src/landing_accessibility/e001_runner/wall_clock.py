"""target 하나 전체(재시도 포함)에 대한 방어적 wall-clock 상한.

## 왜 필요한가 (2026-08-27, Claude A 지적)

L0(`NAV_TIMEOUT_MS=15s`)와 Scout 자신의 예산(`ScoutBudget.max_scout_wall_clock_s
=180s`)은 각자 **자기 범위 안**에서만 시간을 잰다. 그런데 target 하나를 실제로
끝내려면 L0 → (가드 통과 시) L1 Scout → Freeze/Replay 순으로 여러 단계를 거치고,
`retry.run_with_retry`가 그 전체를 최대 `1 + MAX_RETRIES_PER_TARGET`번 되풀이한다.
그 **전체를 감싸는** 상한이 어디에도 없었다 — fixture 자체의 결함(무한루프
스크립트 등)이나 예상 밖의 상호작용으로 어느 한 target이 무한정 매달리면,
그 target 하나가 배치 전체를 막아버릴 수 있었다.

## 설계

`run_with_retry`의 시그니처는 건드리지 않는다 — 그 함수에 시간 인자를 추가하는
것도 optional stopping이 열리는 자리이기 때문이다(`retry.py`의 "이 값을 넓히는
파라미터는 이 모듈 어디에도 없다" 원칙과 같은 이유). 대신 `run_with_retry(attempt)`
호출 **전체**(재시도까지 포함)를 별도 스레드에서 실행하고, 바깥에서
`threading.Thread.join(timeout=...)`으로 시간을 잰다 — "재시도 1회 × cap"이
아니라 "이 target에 쓸 수 있는 전체 시간"이라는 뜻이다.

## 이 장치가 하지 않는 것

상한을 넘기면 **더 기다리지 않고 실패로 기록**하지만, 배경 스레드 자체를 강제로
죽이지는 않는다 — Playwright 동기 API로 진행 중인 브라우저 호출을 외부에서
안전하게 취소할 방법이 없기 때문이다(프로세스를 통째로 죽이는 것 외에는). 그래서
스레드는 `daemon=True`로 띄운다 — 드물게 백그라운드에서 계속 돌다가 스스로
끝나더라도 프로세스 종료를 막지 않는다. 이 lane은 FIXTURE/SHADOW_DRY_RUN
전용이라 실제 네트워크 hang은 없다 — 이 장치가 막는 것은 fixture 결함이나
예기치 못한 상호작용이다.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

#: Claude A 확정값(2026-08-27) — target 하나(L0 + L1 Scout/Freeze/Replay,
#: 재시도 포함) 전체에 허용하는 wall-clock 상한. **정확히 6분**으로 고정한다
#: (5~8분 범위로 논의됐던 것을 이 값 하나로 확정).
DEFAULT_TARGET_WALL_CLOCK_CAP_S: float = 360.0


class TargetWallClockExceededError(RuntimeError):
    """target 하나(재시도 포함)의 전체 실행이 wall-clock 상한을 넘었다.

    Claude A 지시: 이 실패는 **transport failure**이지 measurement outcome이
    아니다 — 절대 `UNDETERMINED`(콘텐츠 판정 축의 abstain 값)로 흡수하지 않는다.
    `batch.py`가 이 예외를 `TargetOutcome.TRANSPORT_FAILURE`로 기록한다.
    """


def run_with_wall_clock_cap[T](fn: Callable[[], T], *, cap_s: float) -> T:
    """`fn()`을 daemon 스레드에서 실행한다. `cap_s`초 안에 끝나지 않으면
    `TargetWallClockExceededError`를 던진다 — 스레드 자체는 유기한다(위 모듈
    docstring 참고).

    `fn()`이 예외를 던지면 그 예외 객체를 **그대로**(타입 보존) 호출자 스레드에서
    다시 던진다 — `AccountActionBlockedError`/`BatchRealTargetBlockedError` 등
    상위 계층이 `isinstance`로 구분하는 예외 타입이 스레드 경계를 넘으며 뭉개지지
    않아야 하기 때문이다.
    """
    if cap_s <= 0:
        raise ValueError(f"cap_s 는 양수여야 한다: {cap_s}")

    box: dict[str, object] = {}

    def _runner() -> None:
        try:
            box["value"] = fn()
        except BaseException as exc:  # 스레드 경계에서 예외를 타입 그대로 옮겨 담는다
            box["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout=cap_s)

    if thread.is_alive():
        raise TargetWallClockExceededError(
            f"target 실행이 wall-clock 상한 {cap_s}s 를 넘었다 — "
            "더 기다리지 않고 TRANSPORT_FAILURE 로 기록한다 (백그라운드 스레드는 유기)"
        )
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    return box["value"]  # type: ignore[return-value]


__all__ = [
    "DEFAULT_TARGET_WALL_CLOCK_CAP_S",
    "TargetWallClockExceededError",
    "run_with_wall_clock_cap",
]
