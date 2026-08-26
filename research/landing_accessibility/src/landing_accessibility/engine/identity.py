"""Evidence identity — `02 §11` · `A1 §6.2` · `§6.3` · `07_EVIDENCE_MANIFEST_CONTRACT`.

`02 §11`: *display name 을 file id 로 사용하지 않는다. hash-based observation id 사용.*
`A1 §6.3` 은 해시 **입력 집합**만 확정하고 함수·정규화·자릿수는 P-C 에 미뤘다.
이 파일이 그 미뤄진 부분을 동결한다.

    observation_id = hash( web_target_id, evidence_run_id, requested_url,
                           protocol_version, collection_started_at )

`collection_started_at` 이 입력에 들어가는 이유는 `A1 §6.3` 그대로다 —
`audit_date` 만으로는 **같은 날 재수집한 두 run 이 구분되지 않는다.**

## P-C 동결 결정

| 항목 | 값 | 왜 |
|---|---|---|
| 해시 함수 | `sha256` | manifest 의 `sha256` 규약과 같은 함수를 쓴다 |
| 정규화 | 각 필드 `NFC` → `strip()` | 한글 표기의 조합/완성형 차이가 다른 id 를 만들지 않게 |
| 시각 정규화 | UTC ISO-8601 마이크로초 + `Z` | 같은 날 재수집 구분 (`A1 §6.3`) |
| 구분자 | `\\x1f` (unit separator) | URL·id 에 나타날 수 없는 바이트라 필드 경계가 모호해지지 않는다 |
| 자릿수 | hex 32자 (128bit) | 파일명으로 쓰기에 충분히 짧고 충돌 여지가 없다 |
| 접두사 | 없음 | manifest 의 `sha256` 규약(접두사 없는 소문자 hex)과 같은 모양 |

`02 §14` 가 요구한 `같은 길이의 한글 이름 등 ID collision 위험` 은
display name 이 입력에 **들어가지 않으므로** 구조적으로 발생하지 않는다.
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass

_FIELD_SEPARATOR = "\x1f"
OBSERVATION_ID_HEX_LEN = 32
OBSERVATION_ID_HASH = "sha256"


class IdentityError(ValueError):
    """observation identity 계약 위반."""


def _normalize(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IdentityError(f"{field} 는 비어 있을 수 없다 (A1 §6.3 해시 입력 집합)")
    text = unicodedata.normalize("NFC", value).strip()
    if _FIELD_SEPARATOR in text:
        raise IdentityError(f"{field} 에 구분자 바이트가 들어 있다: {value!r}")
    return text


@dataclass(frozen=True)
class ObservationIdentity:
    """`A1 §6.3` 이 확정한 해시 입력 5종. 이 밖의 값은 id 에 영향을 주지 않는다."""

    web_target_id: str
    evidence_run_id: str
    requested_url: str
    protocol_version: str
    collection_started_at: str

    def canonical_input(self) -> str:
        return _FIELD_SEPARATOR.join(
            (
                _normalize(self.web_target_id, field="web_target_id"),
                _normalize(self.evidence_run_id, field="evidence_run_id"),
                _normalize(self.requested_url, field="requested_url"),
                _normalize(self.protocol_version, field="protocol_version"),
                _normalize(self.collection_started_at, field="collection_started_at"),
            )
        )

    def observation_id(self) -> str:
        digest = hashlib.sha256(self.canonical_input().encode("utf-8")).hexdigest()
        return digest[:OBSERVATION_ID_HEX_LEN]


def observation_id(
    *,
    web_target_id: str,
    evidence_run_id: str,
    requested_url: str,
    protocol_version: str,
    collection_started_at: str,
) -> str:
    """`A1 §6.3` 입력 집합으로 observation id 를 만든다."""
    return ObservationIdentity(
        web_target_id=web_target_id,
        evidence_run_id=evidence_run_id,
        requested_url=requested_url,
        protocol_version=protocol_version,
        collection_started_at=collection_started_at,
    ).observation_id()


#: `A1 §6.2` — `02 §11` identity 집합을 7종으로 읽는다.
#: 이 7종이 §4.1 evidence completeness 분자의 근거다.
EVIDENCE_SLOTS: tuple[str, ...] = (
    "dom",
    "ax",
    "screenshot_initial",
    "screenshot_fullpage",
    "computed_css",
    "probe",
    "manifest",
)

#: `A2 §1.2` — `measurement_status = MEASURED` 를 주기 위해 `02 §11` 이 요구하는 5종.
#: 7종 중 두 screenshot 을 하나로 세고 computed CSS 를 빼면 `02 §11` 원문의 5종이 된다.
EVIDENCE_SLOTS_REQUIRED_FOR_MEASURED: tuple[str, ...] = (
    "dom",
    "ax",
    "screenshot_initial",
    "probe",
    "manifest",
)


def missing_slots(present: dict[str, str | None]) -> list[str]:
    """`MEASURED` 판정에 필요한 evidence 슬롯 중 비어 있는 것을 돌려준다."""
    return [s for s in EVIDENCE_SLOTS_REQUIRED_FOR_MEASURED if not present.get(s)]
