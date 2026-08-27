"""배치 오케스트레이션 층의 **독립적인** REAL_TARGET firewall.

`landing_accessibility.engine.firewall`이 이미 `REAL_TARGET`을 hard block한다
(`assert_mode_allowed`). 이 모듈은 그것을 대체하지 않는다 — `batch.py`는 엔진의
가드와 이 모듈의 가드를 **둘 다** 호출한다.

## 왜 같은 것을 두 번 검사하는가

지시사항 원문: "REAL_TARGET을 요청하면 하드 fail 하는지 이 배치 러너 레벨에서도
다시 확인해라 (P-C 엔진의 가드에만 의존하지 말고 이 층에서도 방어)."

엔진의 `firewall.py`를 이 모듈이 단순히 다시 import해서 호출하기만 하면,
그 파일 하나가 고쳐지거나(버그) import가 실패하면(설정 오류) 두 계층이 동시에
뚫린다 — 결국 하나의 가드다. 그래서 이 모듈은 **엔진 코드를 참조하지 않는**
자체 어휘·자체 예외·자체 상수를 갖는다. 두 계층이 우연히 동시에 실패할
확률은 각 계층이 독립적으로 유지될 때만 낮아진다.

이 모듈이 막는 것은 오직 "이 배치 러너가 REAL_TARGET으로 무언가를 시도하는가"
뿐이다 — fixture 경로 자체의 안전(예: fixture_root 밖 파일 접근)은 여전히
엔진의 `firewall.assert_navigation_allowed`가 유일한 정본이다 (중복 구현하지
않는다 — 그것까지 재구현하면 "재구현 금지" 원칙을 이 모듈 스스로 어기게 된다).
"""

from __future__ import annotations

#: 이 레이어가 배치 실행을 허용하는 모드. 엔진의 `ExecutionMode` enum과 **값은
#: 같지만 별도로 선언한다** — 이 상수가 엔진 열거형을 import하지 않는 것 자체가
#: 독립성의 증거다.
BATCH_LAYER_ALLOWED_MODES: frozenset[str] = frozenset({"FIXTURE", "SHADOW_DRY_RUN"})

BATCH_LAYER_BLOCKED_MODE: str = "REAL_TARGET"


class BatchRealTargetBlockedError(RuntimeError):
    """E001 배치 러너 층에서 독립적으로 발화한 REAL_TARGET 차단.

    `landing_accessibility.engine.firewall.RealTargetBlockedError`와 다른
    예외 클래스다 — 둘 중 어느 쪽이 발화했는지가 "어느 계층이 막았는지"의
    증거가 된다.
    """


def assert_batch_execution_mode_safe(mode: object) -> str:
    """배치 실행 진입점에서 호출한다. 통과하면 정규화된 모드 문자열을 돌려준다.

    `mode`가 `ExecutionMode` enum이든 문자열이든, `.value`가 있으면 그것을,
    없으면 `str(mode)`를 본다 — 엔진의 `ExecutionMode` 타입에 구조적으로만
    의존하고 그 모듈을 import하지 않는다.
    """
    value = getattr(mode, "value", None)
    if value is None:
        value = str(mode)
    if value == BATCH_LAYER_BLOCKED_MODE:
        raise BatchRealTargetBlockedError(
            "E001 배치 러너 층 firewall: REAL_TARGET 은 이 레이어에서 독립적으로 "
            "hard block 된다. P0(V2_SSOT_FROZEN) 종료 전 실제 서비스 measurement는 "
            "금지다. 이 검사는 landing_accessibility.engine.firewall 과 별개다."
        )
    if value not in BATCH_LAYER_ALLOWED_MODES:
        raise BatchRealTargetBlockedError(
            f"E001 배치 러너 층 firewall: 알 수 없는 execution_mode {value!r} — "
            f"허용 집합은 {sorted(BATCH_LAYER_ALLOWED_MODES)} 뿐이다. "
            "닫힌 집합 밖의 값은 UNKNOWN 으로 흡수하지 않고 차단한다."
        )
    return value


__all__ = [
    "BATCH_LAYER_ALLOWED_MODES",
    "BATCH_LAYER_BLOCKED_MODE",
    "BatchRealTargetBlockedError",
    "assert_batch_execution_mode_safe",
]
