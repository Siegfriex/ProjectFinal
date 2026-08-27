"""D 도구의 exit 코드 규약 — **미실행과 실패를 다른 값으로 낸다.**

A 가 STEP1-034 에서 자기 검사기에 있던 것을 찾았다: 잘못된 입력에 traceback
+ exit 1 을 냈는데 **exit 1 은 '검사가 돌아서 실패했다' 와 같은 코드**였다.
미실행과 실패가 같은 출력이다 — 이 세션의 중심 결함이 검사기 안에 있었다.

D 도구를 실측하니 다섯 개 전부 크래시가 exit 1 이고, 그중 셋이 1 을 의미
있는 값으로 쓰고 있었다(DRIFT · NOT_READY · demo FAIL). 같은 충돌이다.

    0  통과
    1  검사가 돌았고 결과가 부정이다 (FAIL · DRIFT · NOT_READY)
    3  **대조군 실패** — 결과를 내지 않는다
    4  **검사가 돌지 않았다** — 통과로도 실패로도 읽지 마라

A 는 '돌지 않았다' 에 2 를 썼다. D 는 4 를 쓴다 — D 방화벽이 2 를 이미
FAIL 로 쓰고 있었고, 그것을 바꾸면 이미 나간 산출의 의미가 소급해 달라진다.
**값이 다른 것보다 의미가 섞이는 것이 나쁘다.** 이 차이는 티켓에 적는다.
"""
from __future__ import annotations

import sys
import traceback
from typing import Callable

EXIT_OK = 0
EXIT_NEGATIVE = 1
EXIT_CONTROL_FAIL = 3
EXIT_DID_NOT_RUN = 4

MEANING = {0: "통과", 1: "검사가 돌았고 결과가 부정", 3: "대조군 실패 — 결과 없음",
           4: "검사가 돌지 않았다 — 통과로도 실패로도 읽지 마라"}


def run(main: Callable[[], int]) -> int:
    """main 을 감싸 미처리 예외를 exit 4 로 내린다."""
    try:
        return main()
    except SystemExit:
        raise
    except BaseException:                                   # noqa: BLE001
        traceback.print_exc()
        print("\n!! 검사가 돌지 않았다 (exit 4) — 이 실행의 결과를 "
              "통과로도 실패로도 읽지 마라. 산출 파일이 있다면 이전 실행의 것이다.",
              file=sys.stderr)
        return EXIT_DID_NOT_RUN
