"""dom.html 을 선언된 charset 에 맞게 디코드한다.

D 결함 시정: 기존 두 빌더는 `lxml.html.fromstring(path.read_bytes())` 로 **바이트를 직접**
넘겼고, lxml 이 선언 charset 을 무시하고 Latin-1 로 해석해 한글 title 이 mojibake 가 됐다.
(6/56 관측. 전부 `charset=UTF-8` 을 선언한 정상 UTF-8 바이트였다.)

수집기 결함이 아니라 D 의 파싱 결함이다. D-VRC-001-A 는 이 사실로 정정된다.
"""
from __future__ import annotations

import re
from pathlib import Path

from lxml import html as lxml_html

META_CHARSET = re.compile(rb'charset=["\']?\s*([\w\-]+)', re.I)
FALLBACKS = ("utf-8", "cp949", "euc-kr", "latin-1")


def decode_html(raw: bytes) -> tuple[str, str]:
    """(디코드된 문자열, 사용된 인코딩)"""
    m = META_CHARSET.search(raw[:8192])
    declared = m.group(1).decode("ascii", "ignore").lower() if m else None
    order = ([declared] if declared else []) + [e for e in FALLBACKS if e != declared]
    for enc in order:
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "replace"), "utf-8-replace"


def parse_html(path: Path):
    """lxml element tree + 사용 인코딩. 바이트를 직접 넘기지 않는다."""
    text, enc = decode_html(path.read_bytes())
    # XML 선언이 있으면 str 파싱이 거부되므로 제거
    text = re.sub(r'^\s*<\?xml[^>]*\?>', '', text, count=1)
    return lxml_html.fromstring(text), enc
