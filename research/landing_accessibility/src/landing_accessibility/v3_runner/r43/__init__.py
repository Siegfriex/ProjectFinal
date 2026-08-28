"""W5R — `R43` 검증 함수 실패 실증 (`Δ48`).

**하위 패키지로 두는 이유**: `r32_check.sweep_candidates` 는
`v3_runner/*.py` 를 **비재귀**로 훑고 `W5P_TOOLING` 밖의 파일을 전부 R32 후보로
쓸어 담는다. 이 lane 의 도구를 `v3_runner/` 바로 아래에 두면 W5P 의 검사기가
**내 도구의 매개변수를 R32 미등재 후보로 잡아** 실패한다. `r32_check.py` 를
고치는 것은 이 lane 의 금지사항이므로(다른 워커가 쓰는 중), 대신 이쪽이 비켰다.
"""

from __future__ import annotations

__all__ = ["check", "control_failure_demo"]
