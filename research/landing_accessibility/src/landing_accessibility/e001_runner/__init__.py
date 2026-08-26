"""E001 배치 러너 — P-C fixture 엔진 위의 **배치 오케스트레이션 층**.

이 패키지는 L0/L1 측정 엔진(`landing_accessibility.engine`)을 재구현하지 않는다.
`landing_accessibility.engine`이 이미 구현한 execution_mode firewall, evidence
무결성, NED/IED/MPFED, endpoint state machine을 그대로 호출하고, 그 위에
아래 네 가지만 얹는다.

1. **배치 오케스트레이션** — `E001_PLAN`(targets)을 작은 append-only batch로
   나눠 순회하고, batch마다 manifest+hash를 남기고 봉인한다 (`ledger.py`).
2. **사이트 실패 격리** — target 하나의 실패를 `TRANSPORT_FAILURE` 등
   닫힌 상태값으로 분류해 기록하고, 다음 target으로 넘어간다 (`outcomes.py`).
3. **계정 행동 금지 가드** — login/signup/purchase/payment/message send/
   booking confirm/OTP/개인정보 입력/CAPTCHA 우회로 이어질 수 있는 activation
   후보를 클릭 **이전에** 걸러내 그 코드 경로 자체를 막는다 (`guard.py`).
4. **자동 복구 정책** — transient 실패에 정확히 1회만 재시도하고, 그 이상은
   절대 재시도하지 않는다. 재시도 횟수는 어떤 파라미터로도 넓힐 수 없다
   (`retry.py`).

이 패키지가 만드는 모든 산출물은 `landing_accessibility.engine.provenance`의
SHADOW provenance 계약(`PHASE_GATES.md §4.3`)을 그대로 따르며
`shadow_lane = "E001_RUNNER"` 로 표시한다.

**REAL_TARGET firewall은 이 층에서도 독립적으로 재검증한다** — P-C 엔진의
`engine.firewall` 가드에만 기대지 않는다 (`layer_firewall.py`). 두 계층 중
하나가 실수로 뚫려도 다른 하나가 막는다.
"""

from __future__ import annotations

__all__: list[str] = []
