"""``probe.js`` 를 페이지에서 평가하는 공용 헬퍼.

probe 는 **판정하지 않고 raw feature 만** 반환한다 (SSOT 02 §4, PHASE_GATES
``L0_L1_ENGINE_READY`` 의 "probe 분리" 조건). 이 파일이 그 분리 경계다 —
여기서 반환되는 dict 에는 PASS/FAIL 같은 verdict 필드가 없다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Page

PROBE_JS = (Path(__file__).parent / "probe.js").read_text(encoding="utf-8")


def extract_probe(page: Page) -> dict[str, Any]:
    result = page.evaluate(PROBE_JS)
    if not isinstance(result, dict):
        raise RuntimeError(f"probe.js 가 dict 를 반환하지 않았다: {result!r}")
    return result
