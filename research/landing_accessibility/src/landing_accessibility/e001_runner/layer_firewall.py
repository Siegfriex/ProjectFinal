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

import json
import subprocess
from pathlib import Path

#: 이 레이어가 **scope 없이** 배치 실행을 허용하는 모드. 엔진의 `ExecutionMode` enum과
#: **값은 같지만 별도로 선언한다** — 이 상수가 엔진 열거형을 import하지 않는 것 자체가
#: 독립성의 증거다.
BATCH_LAYER_ALLOWED_MODES: frozenset[str] = frozenset({"FIXTURE", "SHADOW_DRY_RUN"})

BATCH_LAYER_BLOCKED_MODE: str = "REAL_TARGET"

#: scope 가 주어졌을 때만 `REAL_TARGET` 을 통과시킬 수 있는 유일한 값.
BATCH_LAYER_REAL_SCOPE: str = "E000_FAST"

#: 이 층이 **자기 힘으로** 확인하는 릴리스 문서. 엔진 모듈의 상수를 재사용하지 않는다 —
#: 두 층이 같은 파일을 각자 읽어야 한 층의 버그가 두 층을 동시에 뚫지 않는다.
BATCH_LAYER_RELEASE_REF = "origin/control/landing-orchestrator"
BATCH_LAYER_RELEASE_PATH = "research/landing_accessibility/control/P0_RELEASE.json"

_REPO_ROOT = Path(__file__).resolve().parents[5]


class BatchRealTargetBlockedError(RuntimeError):
    """E001 배치 러너 층에서 독립적으로 발화한 REAL_TARGET 차단.

    `landing_accessibility.engine.firewall.RealTargetBlockedError`와 다른
    예외 클래스다 — 둘 중 어느 쪽이 발화했는지가 "어느 계층이 막았는지"의
    증거가 된다.
    """


def _release_document(repo_dir: Path | None = None) -> dict[str, object] | None:
    """`git show` 로 릴리스 문서를 직접 읽는다. 실패는 `None` — 그리고 `None` 은 차단이다."""
    cwd = Path(repo_dir) if repo_dir is not None else _REPO_ROOT
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(cwd),
                "show",
                f"{BATCH_LAYER_RELEASE_REF}:{BATCH_LAYER_RELEASE_PATH}",
            ],
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def batch_layer_real_target_released(repo_dir: Path | None = None) -> bool:
    """이 층이 독립적으로 판정하는 "실제 수집이 승인됐는가"."""
    data = _release_document(repo_dir)
    if data is None:
        return False
    promoted = data.get("promoted_main_sha")
    return bool(
        data.get("status") == "RELEASED"
        and isinstance(promoted, str)
        and len(promoted) >= 7
        and data.get("e000_allowed") is True
    )


def assert_batch_execution_mode_safe(mode: object, scope: object | None = None) -> str:
    """배치 실행 진입점에서 호출한다. 통과하면 정규화된 모드 문자열을 돌려준다.

    `mode`가 `ExecutionMode` enum이든 문자열이든, `.value`가 있으면 그것을,
    없으면 `str(mode)`를 본다 — 엔진의 `ExecutionMode` 타입에 구조적으로만
    의존하고 그 모듈을 import하지 않는다.

    `REAL_TARGET` 은 scope 없이는 여전히 무조건 차단이다. scope 가 주어져도 이 층이
    **자기 힘으로** 릴리스 문서를 읽어 승인 여부를 다시 확인한다 — 엔진 층이
    통과시켰다는 사실은 이 층의 판정 근거가 아니다.
    """
    value = getattr(mode, "value", None)
    if value is None:
        value = str(mode)
    scope_value = None
    if scope is not None:
        scope_value = getattr(scope, "value", None) or str(scope)

    if value == BATCH_LAYER_BLOCKED_MODE:
        if scope_value is None:
            raise BatchRealTargetBlockedError(
                "E001 배치 러너 층 firewall: scope 없는 REAL_TARGET 은 이 레이어에서 "
                "독립적으로 hard block 된다. 무제한 실제 수집 경로는 열리지 않는다. "
                "이 검사는 landing_accessibility.engine.firewall 과 별개다."
            )
        if scope_value != BATCH_LAYER_REAL_SCOPE:
            raise BatchRealTargetBlockedError(
                f"E001 배치 러너 층 firewall: 이 레이어가 아는 실제 수집 scope 는 "
                f"{BATCH_LAYER_REAL_SCOPE!r} 뿐이다 — 받은 값: {scope_value!r}."
            )
        if not batch_layer_real_target_released():
            raise BatchRealTargetBlockedError(
                "E001 배치 러너 층 firewall: 릴리스 문서를 이 레이어가 직접 확인했으나 "
                f"승인 조건(status=RELEASED · promoted_main_sha · e000_allowed=true)이 "
                f"충족되지 않았다 ({BATCH_LAYER_RELEASE_REF}:{BATCH_LAYER_RELEASE_PATH})."
            )
        return value

    if scope_value is not None:
        raise BatchRealTargetBlockedError(
            f"E001 배치 러너 층 firewall: execution_scope 는 REAL_TARGET 에서만 쓴다 — "
            f"mode={value!r} scope={scope_value!r}."
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
    "BATCH_LAYER_REAL_SCOPE",
    "BatchRealTargetBlockedError",
    "assert_batch_execution_mode_safe",
    "batch_layer_real_target_released",
]
