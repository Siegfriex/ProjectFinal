"""`older_relevance` 정본 표 — **아직 동결되지 않았다.**

Claude A(governor) 지적: `OlderRelevantKWCAGFailRate`의 **분모가 되는 criterion
집합**이 이 저장소 어디에도 동결돼 있지 않다. `marts/synthetic.py`의 하드코딩
6개 목록이 사실상 유일한 목록인데 그것은 **픽스처용이며 정본이 아니다**
(그래서 그 상수 이름 자체가 `SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE`다).

A가 원천을 찾아 `(criterion_id → older_relevance)` 표를 SHA로 동결해 주입할
예정이다. **그 전까지 실제 데이터로 FailRate를 계산하면 안 된다.** 이 모듈이
그 금지를 코드로 강제한다 — 문서로 부탁하지 않는다.

## 주입 방법 (A의 정본 표가 도착하면)

```python
freeze_canonical_older_relevance(
    mapping={"1.1.1": "VISION", ...},
    sha256="<정본 표 파일의 sha256>",
    source="<원천 문서/커밋 경로>",
)
```

`verify_sha`로 주입 시점에 해시를 대조하므로, 표가 바뀌었는데 SHA를 갱신하지
않으면 주입 자체가 실패한다.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

#: `source_kind`가 이 집합에 있으면 정본 표 없이도 FailRate 계산을 허용한다 —
#: synthetic/빈 입력은 실제 서비스에 대한 주장을 만들지 않기 때문이다.
#: 그 외(=실제 데이터)는 정본 표가 동결돼 있어야만 통과한다.
NON_AUTHORITATIVE_SOURCE_KINDS: frozenset[str] = frozenset({"SYNTHETIC", "EMPTY", "FIXTURE"})


class OlderRelevanceNotFrozenError(RuntimeError):
    """정본 `older_relevance` 표가 동결되지 않은 상태에서 실제 데이터로 FailRate를
    계산하려 했다 — fail-closed로 막는다 (governor 지시)."""


class OlderRelevanceShaMismatch(ValueError):
    """주입된 표의 실제 해시가 선언된 SHA와 다르다."""


@dataclass(frozen=True)
class CanonicalOlderRelevance:
    """동결된 정본 표. `mapping`은 `criterion_id → older_relevance`."""

    mapping: dict[str, str]
    sha256: str
    source: str
    frozen_at: str

    def relevance_of(self, criterion_id: str) -> str | None:
        return self.mapping.get(criterion_id)


#: **현재 상태: 미동결(None).** A의 정본 표가 도착하면
#: `freeze_canonical_older_relevance()`로 주입된다.
_CANONICAL: CanonicalOlderRelevance | None = None


def canonical_mapping_sha256(mapping: dict[str, str]) -> str:
    """표 자체의 정규화 해시 — 키 정렬 + 공백 없는 JSON 직렬화 기준."""
    payload = json.dumps(mapping, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def freeze_canonical_older_relevance(
    *,
    mapping: dict[str, str],
    sha256: str,
    source: str,
    frozen_at: str,
    verify_sha: bool = True,
) -> CanonicalOlderRelevance:
    """정본 표를 주입한다. `verify_sha=True`면 실제 해시와 선언 SHA를 대조한다."""
    global _CANONICAL
    if verify_sha:
        actual = canonical_mapping_sha256(mapping)
        if actual != sha256:
            raise OlderRelevanceShaMismatch(
                f"정본 older_relevance 표의 해시가 다르다. 선언={sha256} 실제={actual} "
                "— 표가 바뀌었으면 SHA도 함께 갱신해야 한다."
            )
    _CANONICAL = CanonicalOlderRelevance(
        mapping=dict(mapping), sha256=sha256, source=source, frozen_at=frozen_at
    )
    return _CANONICAL


def clear_canonical_older_relevance() -> None:
    """테스트 전용 — 주입을 되돌린다."""
    global _CANONICAL
    _CANONICAL = None


def canonical_older_relevance() -> CanonicalOlderRelevance | None:
    return _CANONICAL


def is_frozen() -> bool:
    return _CANONICAL is not None


def assert_older_relevance_frozen(source_kind: str) -> None:
    """**fail-closed 가드** — 실제 데이터로 FailRate를 계산하려는데 정본 표가
    동결돼 있지 않으면 실패시킨다.

    `source_kind`가 `NON_AUTHORITATIVE_SOURCE_KINDS`(synthetic/empty/fixture)면
    그대로 통과한다 — synthetic 경로는 계속 돌아야 한다는 지시 그대로다.
    """
    if source_kind in NON_AUTHORITATIVE_SOURCE_KINDS:
        return
    if _CANONICAL is None:
        raise OlderRelevanceNotFrozenError(
            f"source_kind={source_kind!r}(실제 데이터)로 OlderRelevantKWCAGFailRate를 "
            "계산하려 했으나 정본 (criterion_id → older_relevance) 표가 동결되지 않았다. "
            "marts/synthetic.py의 SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE는 픽스처용이며 "
            "정본이 아니다 — Claude A(governor)가 SHA로 동결한 표를 "
            "freeze_canonical_older_relevance()로 주입한 뒤에만 계산할 수 있다."
        )


def registry_status() -> dict[str, Any]:
    """산출물에 그대로 실을 수 있는 동결 상태 블록."""
    if _CANONICAL is None:
        return {
            "frozen": False,
            "sha256": None,
            "source": None,
            "criterion_count": None,
            "note": (
                "정본 older_relevance 표 미동결 — 실제 데이터 FailRate 계산은 fail-closed로 "
                "차단된다. synthetic 경로만 허용된다."
            ),
        }
    return {
        "frozen": True,
        "sha256": _CANONICAL.sha256,
        "source": _CANONICAL.source,
        "frozen_at": _CANONICAL.frozen_at,
        "criterion_count": len(_CANONICAL.mapping),
        "note": "정본 표가 동결됐다 — 실제 데이터 FailRate 계산이 허용된다.",
    }
