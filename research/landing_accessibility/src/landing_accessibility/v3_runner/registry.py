"""TaskRegistryLoader — 동결된 MAIN50 manifest 에서 ``TaskContract`` 50건을 fail-closed 로 적재한다.

정본 / 대조군
-------------

**정본 (authority).** ``research/landing_accessibility/control/v3/FINAL_MAIN50_MANIFEST.json``
— A 가 ``T-A-V3-STEP1-FREEZE`` 로 동결한 MAIN50 manifest. 표본 정의의 유일한 권위다.
``stratum`` · ``is_pilot_5`` · ``collection_order`` · ``forbidden_actions`` 는 여기에만 있다.

**대조군 (control).** ``SSOTV3/CROSS_SERVICE_TASK_REGISTRY_50_v3.0.csv`` +
``SSOTV3/CROSS_SERVICE_TARGET_FRAME_50_v3.0_candidate.json``. manifest 와 겹치는 모든 필드를
byte-exact 로 대조한다. **한 건이라도 다르면 하나를 조용히 고르지 않고**
:class:`RegistryConflictError` 를 던진다 — 이것이 "관측 후 조용한 변경" 을 잡는 대조군이다.
대조군이 없거나 부실하면 그 자체가 실패다 (``require_control=True`` 가 기본).

**manifest 가 없으면 SSOTV3 로 fallback 하지 않는다.** 그것이 가장 위험한 실패 양식이다 —
candidate frame 을 동결본으로 오인해 수집이 진행된다. 부재는 무조건
:class:`RegistrySourceMissingError` 다.


필드명 매핑 (정본 → 대조군 → TaskContract)
------------------------------------------

동결 manifest 와 SSOTV3 CSV 는 **같은 것을 다른 이름으로 부른다.** 로더가 매핑하며, C 가 두
소스를 대조할 때 이 표가 근거다. 매핑 상수는 :data:`_MANIFEST_VS_CSV` /
:data:`_MANIFEST_VS_JSON_TARGET` 이다.

====================== ============================ ==========================
동결 manifest (정본)   SSOTV3 CSV/JSON (대조군)     TaskContract 필드
====================== ============================ ==========================
``target_id``          ``target_id``                ``target_id``
``family_id``          ``family_id``                ``family_id``
``service_name``       ``service_name``             ``service``
``starting_url``       ``official_entry_url``       ``starting_url``
``frozen_task``        ``matched_task``             ``frozen_task``
``task_instruction``   ``task_instruction``         ``task_instruction``
``fixed_fixture``      ``fixed_fixture``            ``fixed_fixture``
``fixture_override``   ``fixture_override``         ``fixture_override`` (빈 문자열 → ``None``)
``endpoint_contract``  ``endpoint_contract``        ``endpoint_contract``
``task_family``        ``task_family``              (대조 전용. 계약에 넣지 않는다)
``provider_type``      ``provider_type``            (대조 전용)
``mobile_web_eligibility`` ``mobile_web_eligibility`` ``mobile_web_eligibility``
``forbidden_actions``  *(대조군에 없음)*            ``forbidden_actions``
``collection_order``   *(대조군에 없음)*            ``collection_order``
``stratum``            *(대조군에 없음)*            ``stratum`` (``"_"`` 도 원문 보존)
``is_pilot_5``         *(대조군에 없음)*            ``is_pilot_5``
``task_role`` (선택)   *(대조군에 없음)*            ``task_role`` (없으면 ``PRIMARY``, R3)
*(없음 — 관측값)*      *(없음)*                     ``fixture_input_mode`` (R5, 적재 시 ``None``)
*(family 단위)* ``legacy_archetype`` ``legacy_archetype``  ``legacy_archetype`` (metadata 전용)
====================== ============================ ==========================

대조군에 대응이 없는 4개 필드는 :data:`CONTROL_UNCOVERED_FIELDS` 로 명시해 둔다 —
교차대조가 이 필드들을 **검증하지 못한다** 는 사실 자체가 기록되어야 한다.


fail-closed 규칙 (전부 예외. 조용한 부분 로드 없음)
--------------------------------------------------

1. manifest/대조군 파일·디렉터리 부재 → :class:`RegistrySourceMissingError`
2. JSON/CSV 파싱 실패, 필수 키·컬럼 누락, 타입 불일치 → :class:`RegistryParseError`
3. target 수 ≠ 50 (또는 선언된 ``target_count`` 와 불일치) → :class:`RegistryIntegrityError`
4. family 수 ≠ 5, family 별 target 수 ≠ 10 → :class:`RegistryIntegrityError`
5. ``target_id`` 중복 → :class:`RegistryIntegrityError`
6. manifest ``status`` ≠ ``FROZEN`` → :class:`RegistryIntegrityError`
7. 선언된 ``manifest_sha256`` 과 재계산 body 해시 불일치 → :class:`RegistryIntegrityError`
8. ``collection_order`` 가 배열 순서대로 1..50 이 아님 → :class:`RegistryIntegrityError`
9. ``is_pilot_5`` 집합이 ``pilot_5.targets`` 와 불일치 → :class:`RegistryIntegrityError`
10. ``forbidden_actions`` 가 비어 있음/문자열 아님 → :class:`RegistryParseError`
    (빈 목록은 "금지가 없다" 로 오독되어 guard 를 fail-open 시킨다)
11. manifest 와 대조군의 값 불일치 → :class:`RegistryConflictError`
12. ``task_role`` 이 허용값 밖 → :class:`RegistryParseError` (R3)
13. 동결 manifest 에 관측 필드 ``fixture_input_mode`` 가 들어 있음 → :class:`RegistryParseError`
    (R5. 계약과 관측이 섞이면 안 된다)
14. 예비(``replacement_reserve``)의 ``starting_url`` 이 같은 family 의 primary 와 동일,
    또는 ``reserve_rank`` 가 ``(family, stratum)`` 안에서 1..n 연속·유일이 아님
    → :class:`RegistryIntegrityError`


R3 / R4 / R5 (A ``T-A-V3-STEP1-003``)
--------------------------------------

* **R3 ``task_role``** — family-level 집계와 본표본 n 은 :data:`PRIMARY_SAMPLE_FILTER`
  (``"task_role == 'PRIMARY'"``) 로만 필터한다. 각 집계 산출물은 "적용했다" 는 주장이 아니라
  **이 조건 문자열 자체**를 함께 기록한다. :meth:`TaskRegistry.primary` /
  :meth:`TaskRegistry.primary_sample_filter`.
* **R4 분모 사슬** — ``candidate → [replaced k, 사유별 내역] → eligible/frozen → attempted n
  → evidence-bearing n → flow-evaluable n``. 이 로더는 앞 두 단계를
  :meth:`TaskRegistry.replacement_log` 로 산출한다. **``k=0`` 이어도 0 을 명시**하며,
  ``applied_replacements`` 키의 부재는 ``replacements_source="ABSENT_TREATED_AS_ZERO"`` 로
  구분해 남긴다 — "기록이 없다" 와 "0건이다" 를 같아 보이게 두지 않는다.
  ``attempted n`` 이후 단계는 수집 산출물의 소관이며 여기서 채우지 않는다.
* **R5 ``fixture_input_mode``** — 계약이 아니라 **관측값**이다. 적재 결과는 언제나 ``None``
  이고 runner 가 수집 시 채운다. ``task_contract_hash`` payload 에서 제외된다.
  기록용 메타데이터가 아니라 ``activation_depth`` **파생 계산의 입력**이며
  (A ``T-A-V3-STEP1-006`` Δ9: ``SELECT_ORIGIN`` · ``SELECT_DESTINATION`` · ``SELECT_DATE``
  가 CONDITIONAL), 결측으로 흘리면 depth 가 조용히 틀린다. 관측 단위 요약값이고 **step 단위
  실제 수단은 ``FlowStep.input_mode``(W5B 소유)** 가 갖는다 — 두 값이 갈릴 수 있고 정상이다.
  상세 정의는 :mod:`.contracts` docstring 의 R5 절.

**수집 순서를 재정렬하지 않는다.** manifest ``targets`` 배열 순서(= ``collection_order``)를
그대로 보존한다. 정렬은 그 자체로 자유도이고, 원본 순서를 쓰면 그 자유도가 0 이다.

**대표기능(archetype)을 추론하지 않는다.** ``legacy_archetype`` 은 소스 값을 그대로 보존만 하며
이 모듈의 어떤 분기·조건·필터에도 쓰이지 않는다
(``SSOTV3/02_DATA_SCHEMA_v3.0.md`` §1 "대표기능 classifier는 v3 main lineage에 없다").


해시 정규화 규약 (C 가 독립 재계산한다 — 아래 정의가 유일한 권위)
------------------------------------------------------------------

세 종류의 해시가 있고 **서로 값이 다른 것이 정상이다.** 어느 것인지 항상 명시한다.

``manifest_file_sha256``
    manifest **파일 전체 바이트** 의 sha256. :func:`compute_manifest_file_sha256`.

``manifest_body_sha256``
    manifest 문서에서 ``manifest_sha256`` 필드 **하나만 제거한 본문** 을
    ``json.dumps(body, ensure_ascii=False, indent=1)`` 로 직렬화한 문자열의 UTF-8 바이트 sha256.
    manifest 안에 선언된 ``manifest_sha256`` 값이 바로 이것이며, 적재 시 재계산해 대조한다.
    :func:`compute_manifest_body_sha256`.

``endpoint_contract_hash``
    ``sha256(endpoint_contract.encode("utf-8")).hexdigest()``. 소스 원문 문자열을 어떤
    trim/normalize 도 없이 그대로 UTF-8 인코딩한 바이트의 sha256.

``task_contract_hash``
    계약의 *정규화 직렬화* 의 sha256. 절차는 정확히 다음과 같다.

    1. payload = :data:`CONTRACT_HASH_PAYLOAD_FIELDS` 의 필드만 담은 dict. 이는
       :class:`~landing_accessibility.v3_runner.contracts.TaskContract` 의 전체 필드에서
       :data:`CONTRACT_HASH_EXCLUDED_FIELDS` 를 뺀 것이다 —
       ``task_contract_hash`` (self-reference 불가) 와 ``fixture_input_mode`` (**관측값**;
       관측이 계약의 신원을 바꾸면 안 된다) 두 개다.
       ``endpoint_contract_hash`` 와 ``task_role`` 은 **포함** 된다.
    2. ``forbidden_actions`` 는 tuple → ``list`` 로 변환한다. 다른 필드는 소스 값 그대로이며
       ``None`` 은 JSON ``null``, ``bool`` 은 JSON ``true/false`` 로 남는다.
    3. ``json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))``
       — 키 사전순 정렬, 비-ASCII 이스케이프 금지, 구분자에 공백 없음.
    4. 그 문자열을 ``UTF-8`` 로 인코딩한 바이트의 ``sha256().hexdigest()``.

    :func:`recompute_task_contract_hash` 가 이 절차의 실행 가능한 정의다.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from .contracts import FIXTURE_INPUT_MODES, TASK_ROLE_PRIMARY, TASK_ROLES, TaskContract

__all__ = [
    "CONTRACT_HASH_EXCLUDED_FIELDS",
    "CONTRACT_HASH_PAYLOAD_FIELDS",
    "CONTROL_UNCOVERED_FIELDS",
    "DEFAULT_MANIFEST_PATH",
    "EXPECTED_FAMILY_COUNT",
    "EXPECTED_PILOT_COUNT",
    "EXPECTED_TARGETS_PER_FAMILY",
    "EXPECTED_TARGET_COUNT",
    "MANIFEST_HASH_FIELD",
    "MANIFEST_RELPATH",
    "PRIMARY_SAMPLE_FILTER",
    "REQUIRED_CSV_COLUMNS",
    "SSOT_DIR_NAME",
    "TARGET_FRAME_JSON_NAME",
    "TASK_REGISTRY_CSV_NAME",
    "FamilyDenominatorChain",
    "RegistryConflictError",
    "RegistryError",
    "RegistryIntegrityError",
    "RegistryLookupError",
    "RegistryParseError",
    "RegistrySourceMissingError",
    "ReplacementLog",
    "ReplacementReserveEntry",
    "TaskRegistry",
    "canonical_contract_payload",
    "canonical_json",
    "compute_manifest_body_sha256",
    "compute_manifest_file_sha256",
    "load_task_registry",
    "recompute_task_contract_hash",
    "resolve_manifest_path",
    "resolve_ssot_dir",
]


# --------------------------------------------------------------------------------------
# 상수
# --------------------------------------------------------------------------------------

#: ``research/landing_accessibility`` — 이 모듈은 그 아래 src/landing_accessibility/v3_runner 다.
_RESEARCH_ROOT = Path(__file__).resolve().parents[3]

MANIFEST_RELPATH = "control/v3/FINAL_MAIN50_MANIFEST.json"
DEFAULT_MANIFEST_PATH = _RESEARCH_ROOT / MANIFEST_RELPATH

SSOT_DIR_NAME = "SSOTV3"
TASK_REGISTRY_CSV_NAME = "CROSS_SERVICE_TASK_REGISTRY_50_v3.0.csv"
TARGET_FRAME_JSON_NAME = "CROSS_SERVICE_TARGET_FRAME_50_v3.0_candidate.json"

#: manifest body 해시 계산에서 제외하는 유일한 필드.
MANIFEST_HASH_FIELD = "manifest_sha256"

EXPECTED_TARGET_COUNT = 50
EXPECTED_FAMILY_COUNT = 5
EXPECTED_TARGETS_PER_FAMILY = 10
EXPECTED_PILOT_COUNT = 5

REQUIRED_MANIFEST_KEYS: tuple[str, ...] = (
    "frame_id",
    "version",
    "status",
    "target_count",
    "task_family_count",
    "task_families",
    "targets",
    "pilot_5",
    MANIFEST_HASH_FIELD,
)

REQUIRED_MANIFEST_TARGET_KEYS: tuple[str, ...] = (
    "target_id",
    "collection_order",
    "family_id",
    "task_family",
    "service_name",
    "provider_type",
    "stratum",
    "starting_url",
    "frozen_task",
    "task_instruction",
    "fixed_fixture",
    "fixture_override",
    "endpoint_contract",
    "forbidden_actions",
    "mobile_web_eligibility",
    "is_pilot_5",
)

REQUIRED_MANIFEST_FAMILY_KEYS: tuple[str, ...] = (
    "family_id",
    "task_family",
    "domain",
    "legacy_archetype",
    "matched_task",
    "task_instruction",
    "fixed_fixture",
    "endpoint_contract",
)

#: 대조군 CSV 에 반드시 존재해야 하는 컬럼.
REQUIRED_CSV_COLUMNS: tuple[str, ...] = (
    "target_id",
    "family_id",
    "task_family",
    "domain",
    "legacy_archetype",
    "service_name",
    "provider_type",
    "official_entry_url",
    "mobile_web_eligibility",
    "matched_task",
    "task_instruction",
    "fixed_fixture",
    "fixture_override",
    "endpoint_contract",
)

_REQUIRED_JSON_TARGET_KEYS: tuple[str, ...] = (
    "target_id",
    "family_id",
    "service_name",
    "provider_type",
    "official_entry_url",
    "matched_task",
    "fixed_fixture",
    "fixture_override",
    "endpoint_contract",
    "mobile_web_eligibility",
)

_REQUIRED_JSON_FAMILY_KEYS: tuple[str, ...] = REQUIRED_MANIFEST_FAMILY_KEYS

#: manifest target 키 → 대조군 CSV 컬럼.
_MANIFEST_VS_CSV: tuple[tuple[str, str], ...] = (
    ("family_id", "family_id"),
    ("task_family", "task_family"),
    ("service_name", "service_name"),
    ("provider_type", "provider_type"),
    ("starting_url", "official_entry_url"),
    ("frozen_task", "matched_task"),
    ("task_instruction", "task_instruction"),
    ("fixed_fixture", "fixed_fixture"),
    ("fixture_override", "fixture_override"),
    ("endpoint_contract", "endpoint_contract"),
    ("mobile_web_eligibility", "mobile_web_eligibility"),
)

#: manifest target 키 → 대조군 JSON ``targets[]`` 키.
_MANIFEST_VS_JSON_TARGET: tuple[tuple[str, str], ...] = (
    ("family_id", "family_id"),
    ("service_name", "service_name"),
    ("provider_type", "provider_type"),
    ("starting_url", "official_entry_url"),
    ("frozen_task", "matched_task"),
    ("fixed_fixture", "fixed_fixture"),
    ("fixture_override", "fixture_override"),
    ("endpoint_contract", "endpoint_contract"),
    ("mobile_web_eligibility", "mobile_web_eligibility"),
)

#: manifest task_family 키 → 대조군 JSON ``task_families[]`` 키 (동명).
_MANIFEST_VS_JSON_FAMILY: tuple[str, ...] = REQUIRED_MANIFEST_FAMILY_KEYS

#: 대조군 소스에 대응 필드가 **없어서** 교차대조로 검증되지 않는 manifest 전용 필드.
#: A 가 동결 시점에 새로 등록한 값들이라 대조군이 존재하지 않는다 — C 는 이 목록을 알고 있어야 한다.
CONTROL_UNCOVERED_FIELDS: tuple[str, ...] = (
    "collection_order",
    "stratum",
    "is_pilot_5",
    "forbidden_actions",
)

#: task_contract_hash payload 에서 **제외** 하는 필드.
#:
#: * ``task_contract_hash`` — self-reference 불가.
#: * ``fixture_input_mode`` — **관측값**이다. 수집 시 runner 가 채우므로 동결 시점에는 항상
#:   ``None`` 이다. 관측이 계약의 신원(hash)을 바꾸면 동결의 의미가 사라진다.
CONTRACT_HASH_EXCLUDED_FIELDS: tuple[str, ...] = ("task_contract_hash", "fixture_input_mode")

#: task_contract_hash payload 필드 (= TaskContract 전체 − 위 제외 필드).
CONTRACT_HASH_PAYLOAD_FIELDS: tuple[str, ...] = tuple(
    f.name for f in fields(TaskContract) if f.name not in CONTRACT_HASH_EXCLUDED_FIELDS
)

#: R3. family-level 집계와 본표본 n 에 반드시 적용해야 하는 필터 **조건 문자열**.
#: 각 집계 산출물은 "적용했다" 는 주장이 아니라 이 문자열 자체를 함께 기록한다.
PRIMARY_SAMPLE_FILTER = "task_role == 'PRIMARY'"

#: replacement_reserve 항목의 필수 키.
REQUIRED_RESERVE_KEYS: tuple[str, ...] = (
    "family_id",
    "stratum",
    "reserve_rank",
    "service_name",
    "starting_url",
    "mobile_web_eligibility",
    "inherits",
)

#: 실제 적용된 교체 기록이 담기는 (선택적) manifest 키. 없으면 **명시적 0** 으로 읽는다.
APPLIED_REPLACEMENTS_KEY = "applied_replacements"


# --------------------------------------------------------------------------------------
# 예외
# --------------------------------------------------------------------------------------


class RegistryError(Exception):
    """TaskRegistry 적재 실패의 공통 상위 예외."""


class RegistrySourceMissingError(RegistryError):
    """manifest 또는 대조군 소스가 없다. **SSOTV3 로의 조용한 fallback 은 하지 않는다.**"""


class RegistryParseError(RegistryError):
    """JSON/CSV 를 읽거나 해석할 수 없다 (인코딩·문법·필수 필드·타입 포함)."""


class RegistryIntegrityError(RegistryError):
    """행 수·family 균형·중복 id·해시 대조·순서 등 구조 불변조건 위반."""


class RegistryConflictError(RegistryError):
    """동결 manifest 와 SSOTV3 대조군이 같은 target 의 같은 필드에 다른 값을 준다."""


class RegistryLookupError(RegistryError, KeyError):
    """레지스트리에 없는 target_id / family_id 를 조회했다."""


# --------------------------------------------------------------------------------------
# 해시 (모듈 docstring 의 규약이 여기 구현되어 있다)
# --------------------------------------------------------------------------------------


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json(payload: Mapping[str, Any]) -> str:
    """계약 정규화 직렬화: 키 사전순, ``ensure_ascii=False``, 공백 없는 구분자."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_manifest_file_sha256(raw: bytes) -> str:
    """manifest **파일 전체 바이트** 의 sha256."""
    return _sha256_bytes(raw)


def compute_manifest_body_sha256(document: Mapping[str, Any]) -> str:
    """manifest **본문**(``manifest_sha256`` 필드 제외) 의 sha256.

    직렬화는 ``json.dumps(body, ensure_ascii=False, indent=1)`` — A 가 동결에 쓴 그 방식이다.
    파일 전체 해시와 값이 다른 것이 정상이다.
    """
    body = {k: v for k, v in document.items() if k != MANIFEST_HASH_FIELD}
    return _sha256_text(json.dumps(body, ensure_ascii=False, indent=1))


def canonical_contract_payload(contract_fields: Mapping[str, Any]) -> dict[str, Any]:
    """``task_contract_hash`` 를 뺀 계약 payload. ``forbidden_actions`` 만 tuple → list."""
    payload: dict[str, Any] = {}
    for name in CONTRACT_HASH_PAYLOAD_FIELDS:
        if name not in contract_fields:
            raise RegistryParseError(
                f"계약 payload 에 필수 필드가 없다: {name!r} "
                f"(필요: {list(CONTRACT_HASH_PAYLOAD_FIELDS)})"
            )
        value = contract_fields[name]
        payload[name] = list(value) if name == "forbidden_actions" else value
    return payload


def recompute_task_contract_hash(contract: TaskContract | Mapping[str, Any]) -> str:
    """모듈 docstring 의 정규화 절차를 그대로 실행한 ``task_contract_hash``."""
    if isinstance(contract, TaskContract):
        source: Mapping[str, Any] = {
            name: getattr(contract, name) for name in CONTRACT_HASH_PAYLOAD_FIELDS
        }
    else:
        source = contract
    return _sha256_text(canonical_json(canonical_contract_payload(source)))


# --------------------------------------------------------------------------------------
# 레지스트리
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplacementReserveEntry:
    """precheck 단계에서만 쓰이는 예비 target 1건. manifest ``replacement_reserve`` 원문."""

    family_id: str
    stratum: str | None
    reserve_rank: int
    service_name: str
    starting_url: str
    mobile_web_eligibility: str
    inherits: str


@dataclass(frozen=True)
class FamilyDenominatorChain:
    """R4 분모 사슬의 앞 두 단계. ``candidate → [replaced k] → eligible/frozen``.

    ``replaced_count`` 가 0 이어도 **0 을 명시**한다 — 필드 부재와 0 이 같아 보이면 안 된다.
    ``attempted_n`` 이후 단계는 수집 산출물에서 채워지며 이 로더의 소관이 아니다.
    """

    family_id: str
    candidate_count: int
    replaced_count: int
    replaced_reasons: tuple[str, ...]
    frozen_count: int
    reserve_count: int
    reserve_remaining: int


@dataclass(frozen=True)
class ReplacementLog:
    """교체 이력 + family 별 분모 사슬 앞단.

    ``replacements_source`` 가 ``"ABSENT_TREATED_AS_ZERO"`` 이면 manifest 에
    ``applied_replacements`` 키 자체가 없다는 뜻이다 — 동결은 precheck **이전** 상태를
    고정하므로 교체가 아직 0건인 것이 정상이다. "기록이 없다" 와 "0건이다" 를 구분해 남긴다.
    """

    total_replaced: int
    replacements_source: str
    rule: Mapping[str, Any]
    reserve: tuple[ReplacementReserveEntry, ...]
    per_family: tuple[FamilyDenominatorChain, ...]

    def by_family(self, family_id: str) -> FamilyDenominatorChain:
        for chain in self.per_family:
            if chain.family_id == family_id:
                return chain
        raise RegistryLookupError(f"알 수 없는 family_id: {family_id!r}")

    def reserve_for(self, family_id: str) -> tuple[ReplacementReserveEntry, ...]:
        """``reserve_rank`` 오름차순. 교체는 이 순서로만 진행한다."""
        return tuple(
            sorted(
                (e for e in self.reserve if e.family_id == family_id),
                key=lambda e: (e.stratum or "", e.reserve_rank),
            )
        )


@dataclass(frozen=True)
class TaskRegistry:
    """동결된 ``TaskContract`` 50건 + 출처 digest.

    ``contracts`` 는 manifest ``targets`` 배열 순서(= ``collection_order`` 오름차순)를
    그대로 보존한다. 재정렬하지 않는다.
    """

    manifest_path: Path
    manifest_version: str
    manifest_status: str
    declared_manifest_sha256: str
    manifest_body_sha256: str
    manifest_file_sha256: str
    real_target_allowed: bool
    contracts: tuple[TaskContract, ...]
    replacement_rule: Mapping[str, Any]
    replacement_reserve: tuple[ReplacementReserveEntry, ...]
    applied_replacements: tuple[Mapping[str, Any], ...]
    applied_replacements_source: str
    control_source_dir: Path | None = None
    control_csv_sha256: str | None = None
    control_json_sha256: str | None = None

    def all(self) -> tuple[TaskContract, ...]:
        """manifest 순서를 보존한 전체 계약 50건."""
        return self.contracts

    def by_target_id(self, target_id: str) -> TaskContract:
        for contract in self.contracts:
            if contract.target_id == target_id:
                return contract
        raise RegistryLookupError(
            f"알 수 없는 target_id: {target_id!r} (등록된 {len(self.contracts)}건 중 없음)"
        )

    def by_family(self, family_id: str) -> tuple[TaskContract, ...]:
        found = tuple(c for c in self.contracts if c.family_id == family_id)
        if not found:
            raise RegistryLookupError(
                f"알 수 없는 family_id: {family_id!r} (등록된 family: {list(self.family_ids())})"
            )
        return found

    def family_ids(self) -> tuple[str, ...]:
        """최초 등장 순서를 보존한 family_id 목록."""
        seen: dict[str, None] = {}
        for contract in self.contracts:
            seen.setdefault(contract.family_id, None)
        return tuple(seen)

    def pilot_5(self) -> tuple[TaskContract, ...]:
        """``is_pilot_5`` 로 표시된 pilot 대상. manifest 순서 보존."""
        return tuple(c for c in self.contracts if c.is_pilot_5)

    def primary(self) -> tuple[TaskContract, ...]:
        """본표본. ``task_role == 'PRIMARY'`` 인 계약만. :data:`PRIMARY_SAMPLE_FILTER` 참조."""
        return tuple(c for c in self.contracts if c.task_role == TASK_ROLE_PRIMARY)

    def primary_sample_filter(self) -> str:
        """집계 산출물에 함께 기록해야 하는 **필터 조건 문자열** 자체."""
        return PRIMARY_SAMPLE_FILTER

    def replacement_log(self) -> ReplacementLog:
        """R4 분모 사슬 앞단 + 예비 명부. ``replaced k`` 가 0 이어도 0 을 명시한다."""
        per_family: list[FamilyDenominatorChain] = []
        for family_id in self.family_ids():
            frozen = len(self.by_family(family_id))
            replaced = sum(
                1 for entry in self.applied_replacements if str(entry.get("family_id")) == family_id
            )
            reserve_count = sum(1 for e in self.replacement_reserve if e.family_id == family_id)
            per_family.append(
                FamilyDenominatorChain(
                    family_id=family_id,
                    candidate_count=frozen,
                    replaced_count=replaced,
                    replaced_reasons=tuple(
                        str(entry.get("reason", ""))
                        for entry in self.applied_replacements
                        if str(entry.get("family_id")) == family_id
                    ),
                    frozen_count=frozen,
                    reserve_count=reserve_count,
                    reserve_remaining=reserve_count - replaced,
                )
            )
        return ReplacementLog(
            total_replaced=len(self.applied_replacements),
            replacements_source=self.applied_replacements_source,
            rule=self.replacement_rule,
            reserve=self.replacement_reserve,
            per_family=tuple(per_family),
        )

    def control_verified(self) -> bool:
        """SSOTV3 대조군과 교차대조를 실제로 수행했는지."""
        return self.control_source_dir is not None

    def __len__(self) -> int:
        return len(self.contracts)

    def __iter__(self) -> Iterator[TaskContract]:
        return iter(self.contracts)


# --------------------------------------------------------------------------------------
# 소스 위치 해석
# --------------------------------------------------------------------------------------


def resolve_manifest_path(manifest_path: Path | str | None = None) -> Path:
    """동결 manifest 파일 경로. ``None`` 이면 :data:`DEFAULT_MANIFEST_PATH`.

    부재하면 :class:`RegistrySourceMissingError`. **SSOTV3 로 fallback 하지 않는다.**
    """
    candidate = Path(manifest_path) if manifest_path is not None else DEFAULT_MANIFEST_PATH
    if not candidate.is_file():
        raise RegistrySourceMissingError(
            f"동결 MAIN50 manifest 가 없다: {candidate} — "
            "SSOTV3 candidate frame 으로 대체하지 않는다 (동결 전 수집 금지)"
        )
    return candidate


def resolve_ssot_dir(registry_path: Path | str | None = None) -> Path:
    """대조군 SSOTV3 디렉터리. ``None`` 이면 이 모듈에서 위로 올라가며 찾는다."""
    if registry_path is not None:
        candidate = Path(registry_path)
        if not candidate.is_dir():
            raise RegistrySourceMissingError(f"대조군 디렉터리가 없다: {candidate}")
        return candidate

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / SSOT_DIR_NAME
        if (candidate / TASK_REGISTRY_CSV_NAME).is_file() and (
            candidate / TARGET_FRAME_JSON_NAME
        ).is_file():
            return candidate
    raise RegistrySourceMissingError(
        f"{here} 의 상위 어디에서도 {SSOT_DIR_NAME}/{TASK_REGISTRY_CSV_NAME} + "
        f"{TARGET_FRAME_JSON_NAME} 를 찾지 못했다"
    )


def _require_file(directory: Path, name: str) -> Path:
    target = directory / name
    if not target.is_file():
        raise RegistrySourceMissingError(f"소스 파일이 없다: {target}")
    return target


# --------------------------------------------------------------------------------------
# manifest 읽기 · 검증
# --------------------------------------------------------------------------------------


def _load_json_document(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryParseError(f"JSON 파싱 실패: {path} ({exc})") from exc
    if not isinstance(document, dict):
        raise RegistryParseError(f"JSON 최상위가 object 가 아니다: {path}")
    return document


def _require_str_list(value: Any, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise RegistryParseError(f"{where} 는 문자열 list 여야 한다: {value!r}")
    return tuple(value)


def _validate_manifest_shape(document: Mapping[str, Any], path: Path) -> None:
    missing = [k for k in REQUIRED_MANIFEST_KEYS if k not in document]
    if missing:
        raise RegistryParseError(f"manifest 필수 키 누락: {missing} — {path}")
    for key in ("task_families", "targets"):
        if not isinstance(document[key], list):
            raise RegistryParseError(f"manifest {key!r} 가 list 가 아니다: {path}")
    if not isinstance(document["pilot_5"], dict) or "targets" not in document["pilot_5"]:
        raise RegistryParseError(f"manifest pilot_5.targets 가 없다: {path}")

    status = document["status"]
    if status != "FROZEN":
        raise RegistryIntegrityError(
            f"manifest status 가 FROZEN 이 아니다: {status!r} — 동결 전 manifest 로 수집하지 않는다"
        )

    declared = document[MANIFEST_HASH_FIELD]
    recomputed = compute_manifest_body_sha256(document)
    if declared != recomputed:
        raise RegistryIntegrityError(
            "manifest body 해시 불일치 — "
            f"선언 {MANIFEST_HASH_FIELD}={declared!r}, 재계산(body, indent=1)={recomputed!r} "
            f"({path}). 참고: 파일 전체 해시는 body 해시와 다른 값이 정상이다."
        )


def _parse_manifest_families(document: Mapping[str, Any], path: Path) -> dict[str, dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(document["task_families"]):
        if not isinstance(entry, dict):
            raise RegistryParseError(f"manifest task_families[{index}] 가 object 가 아니다: {path}")
        missing = [k for k in REQUIRED_MANIFEST_FAMILY_KEYS if k not in entry]
        if missing:
            raise RegistryParseError(
                f"manifest task_families[{index}] 필수 키 누락: {missing} — {path}"
            )
        family_id = str(entry["family_id"])
        if family_id in families:
            raise RegistryIntegrityError(f"manifest 에 중복 family_id: {family_id!r}")
        families[family_id] = entry

    declared = document["task_family_count"]
    if len(families) != declared:
        raise RegistryIntegrityError(
            f"manifest task_family_count={declared} 인데 실제 {len(families)}건이다"
        )
    if len(families) != EXPECTED_FAMILY_COUNT:
        raise RegistryIntegrityError(
            f"family 수가 {EXPECTED_FAMILY_COUNT} 가 아니다: {sorted(families)}"
        )
    return families


def _parse_manifest_targets(
    document: Mapping[str, Any], families: Mapping[str, Any], path: Path
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for index, entry in enumerate(document["targets"]):
        if not isinstance(entry, dict):
            raise RegistryParseError(f"manifest targets[{index}] 가 object 가 아니다: {path}")
        missing = [k for k in REQUIRED_MANIFEST_TARGET_KEYS if k not in entry]
        if missing:
            raise RegistryParseError(f"manifest targets[{index}] 필수 키 누락: {missing} — {path}")
        targets.append(entry)

    declared = document["target_count"]
    if len(targets) != declared:
        raise RegistryIntegrityError(
            f"manifest target_count={declared} 인데 실제 {len(targets)}건이다 — 부분 로드 금지"
        )
    if len(targets) != EXPECTED_TARGET_COUNT:
        raise RegistryIntegrityError(
            f"target 수가 {EXPECTED_TARGET_COUNT} 이 아니다: {len(targets)}건 — 부분 로드 금지"
        )

    counts = Counter(str(t["target_id"]) for t in targets)
    duplicates = sorted(tid for tid, n in counts.items() if n > 1)
    if duplicates:
        raise RegistryIntegrityError(f"manifest 에 중복 target_id: {duplicates}")

    per_family = Counter(str(t["family_id"]) for t in targets)
    unknown = sorted(set(per_family) - set(families))
    if unknown:
        raise RegistryIntegrityError(f"task_families 에 없는 family_id 를 쓰는 target: {unknown}")
    unbalanced = {f: n for f, n in sorted(per_family.items()) if n != EXPECTED_TARGETS_PER_FAMILY}
    if unbalanced:
        raise RegistryIntegrityError(
            f"family 별 target 수가 {EXPECTED_TARGETS_PER_FAMILY} 이 아니다: {unbalanced} "
            f"(전체: {dict(sorted(per_family.items()))})"
        )

    orders = [t["collection_order"] for t in targets]
    if any(not isinstance(o, int) or isinstance(o, bool) for o in orders):
        raise RegistryParseError(f"collection_order 에 정수가 아닌 값이 있다: {orders}")
    if orders != list(range(1, EXPECTED_TARGET_COUNT + 1)):
        raise RegistryIntegrityError(
            f"collection_order 가 배열 순서대로 1..{EXPECTED_TARGET_COUNT} 가 아니다 "
            f"(재정렬 금지): {orders!r}"
        )

    declared_pilot = _require_str_list(document["pilot_5"]["targets"], "manifest pilot_5.targets")
    flagged = tuple(str(t["target_id"]) for t in targets if t["is_pilot_5"] is True)
    if set(flagged) != set(declared_pilot) or len(flagged) != EXPECTED_PILOT_COUNT:
        raise RegistryIntegrityError(
            f"is_pilot_5 플래그 집합 {list(flagged)} 이 pilot_5.targets {list(declared_pilot)} 와 "
            f"다르거나 {EXPECTED_PILOT_COUNT}건이 아니다"
        )

    for entry in targets:
        actions = _require_str_list(
            entry["forbidden_actions"], f"targets[{entry['target_id']}].forbidden_actions"
        )
        if not actions:
            raise RegistryParseError(
                f"{entry['target_id']}: forbidden_actions 가 비어 있다 — "
                "빈 목록은 guard 를 fail-open 시키므로 허용하지 않는다"
            )
        role = entry.get("task_role", TASK_ROLE_PRIMARY)
        if role not in TASK_ROLES:
            raise RegistryParseError(
                f"{entry['target_id']}: task_role 이 허용값이 아니다 — {role!r} "
                f"(허용: {list(TASK_ROLES)})"
            )
        mode = entry.get("fixture_input_mode")
        if mode is not None:
            raise RegistryParseError(
                f"{entry['target_id']}: fixture_input_mode 는 관측값이라 동결 manifest 에 "
                f"들어 있으면 안 된다 — {mode!r} (허용 관측값: {list(FIXTURE_INPUT_MODES)})"
            )
    return targets


def _parse_replacement_reserve(
    document: Mapping[str, Any],
    families: Mapping[str, Any],
    manifest_targets: Sequence[Mapping[str, Any]],
    path: Path,
) -> tuple[ReplacementReserveEntry, ...]:
    """예비 명부를 읽고 검증한다.

    길이가 family 마다 다른 것은 정상이다 (manifest ``replacement_reserve_note``) — 균등화를
    위해 후보를 만들어 넣지 않았다. 대신 다음을 fail-closed 로 본다.

    * ``reserve_rank`` 는 ``(family_id, stratum)`` 안에서 유일하고 1부터 연속이어야 한다.
    * 예비의 ``starting_url`` 이 primary target 의 ``starting_url`` 과 같으면 안 된다 —
      교체해도 같은 것을 다시 수집하게 되므로 예비로서 성립하지 않는다
      (A 가 v3.0.1 → v3.0.2 에서 시정한 바로 그 결함).
    """
    raw = document.get("replacement_reserve", [])
    if not isinstance(raw, list):
        raise RegistryParseError(f"replacement_reserve 가 list 가 아니다: {path}")

    entries: list[ReplacementReserveEntry] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise RegistryParseError(f"replacement_reserve[{index}] 가 object 가 아니다: {path}")
        missing = [k for k in REQUIRED_RESERVE_KEYS if k not in item]
        if missing:
            raise RegistryParseError(
                f"replacement_reserve[{index}] 필수 키 누락: {missing} — {path}"
            )
        rank = item["reserve_rank"]
        if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
            raise RegistryParseError(
                f"replacement_reserve[{index}].reserve_rank 가 1 이상의 정수가 아니다: {rank!r}"
            )
        entries.append(
            ReplacementReserveEntry(
                family_id=str(item["family_id"]),
                stratum=_blank_to_none(item["stratum"]),
                reserve_rank=rank,
                service_name=str(item["service_name"]),
                starting_url=str(item["starting_url"]),
                mobile_web_eligibility=str(item["mobile_web_eligibility"]),
                inherits=str(item["inherits"]),
            )
        )

    unknown = sorted({e.family_id for e in entries} - set(families))
    if unknown:
        raise RegistryIntegrityError(f"예비 명부가 알 수 없는 family 를 참조한다: {unknown}")

    grouped: dict[tuple[str, str | None], list[int]] = {}
    for entry in entries:
        grouped.setdefault((entry.family_id, entry.stratum), []).append(entry.reserve_rank)
    for key, ranks in sorted(grouped.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        if sorted(ranks) != list(range(1, len(ranks) + 1)):
            raise RegistryIntegrityError(
                f"예비 명부 reserve_rank 가 {key} 안에서 1..{len(ranks)} 연속·유일이 아니다: "
                f"{sorted(ranks)}"
            )

    primary_urls = {
        (str(t["family_id"]), str(t["starting_url"])): str(t["target_id"]) for t in manifest_targets
    }
    collisions = [
        f"{e.family_id} rank {e.reserve_rank} {e.service_name!r} {e.starting_url} "
        f"== primary {primary_urls[(e.family_id, e.starting_url)]}"
        for e in entries
        if (e.family_id, e.starting_url) in primary_urls
    ]
    if collisions:
        raise RegistryIntegrityError(
            "예비가 같은 family 의 primary target 과 starting_url 이 같다 — 예비로 성립하지 "
            "않는다:\n  " + "\n  ".join(collisions)
        )
    return tuple(entries)


def _parse_applied_replacements(
    document: Mapping[str, Any], path: Path
) -> tuple[tuple[Mapping[str, Any], ...], str]:
    """실제 적용된 교체 기록. 키가 없으면 **명시적 0** 으로 읽되 그 사실을 출처로 남긴다."""
    if APPLIED_REPLACEMENTS_KEY not in document:
        return (), "ABSENT_TREATED_AS_ZERO"
    raw = document[APPLIED_REPLACEMENTS_KEY]
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise RegistryParseError(f"{APPLIED_REPLACEMENTS_KEY} 가 object list 가 아니다: {path}")
    return tuple(raw), "MANIFEST_KEY"


# --------------------------------------------------------------------------------------
# 대조군 읽기
# --------------------------------------------------------------------------------------


def _read_control_csv(csv_path: Path) -> dict[str, dict[str, str]]:
    raw = csv_path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RegistryParseError(f"CSV 를 UTF-8 로 디코드할 수 없다: {csv_path} ({exc})") from exc

    try:
        reader = csv.DictReader(text.splitlines())
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise RegistryParseError(f"CSV 헤더가 비어 있다: {csv_path}")
        # 첫 컬럼명에 UTF-8 BOM(``﻿``)이 붙어 있다. utf-8-sig 로 이미 제거되지만
        # 다른 경로로 들어온 BOM 도 여기서 한 번 더 정규화한다.
        normalized = [name.lstrip("﻿").strip() for name in fieldnames]
        rows = [
            {normalized[i]: (row.get(name) or "") for i, name in enumerate(fieldnames)}
            for row in reader
        ]
    except csv.Error as exc:
        raise RegistryParseError(f"CSV 파싱 실패: {csv_path} ({exc})") from exc

    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in normalized]
    if missing:
        raise RegistryParseError(f"CSV 필수 컬럼 누락: {missing} (헤더: {normalized}) — {csv_path}")

    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        tid = row["target_id"]
        if not tid.strip():
            raise RegistryParseError(f"대조군 CSV 에 target_id 가 빈 행이 있다: {csv_path}")
        if tid in indexed:
            raise RegistryIntegrityError(f"대조군 CSV 에 중복 target_id: {tid!r}")
        indexed[tid] = row
    return indexed


def _read_control_json(json_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    document = _load_json_document(json_path)
    for key in ("task_families", "targets"):
        if not isinstance(document.get(key), list):
            raise RegistryParseError(f"대조군 JSON 에 list 형 {key!r} 가 없다: {json_path}")

    families: dict[str, Any] = {}
    for index, entry in enumerate(document["task_families"]):
        if not isinstance(entry, dict):
            raise RegistryParseError(f"대조군 task_families[{index}] 가 object 가 아니다")
        missing = [k for k in _REQUIRED_JSON_FAMILY_KEYS if k not in entry]
        if missing:
            raise RegistryParseError(f"대조군 task_families[{index}] 필수 키 누락: {missing}")
        fid = str(entry["family_id"])
        if fid in families:
            raise RegistryIntegrityError(f"대조군 JSON 에 중복 family_id: {fid!r}")
        families[fid] = entry

    targets: dict[str, Any] = {}
    for index, entry in enumerate(document["targets"]):
        if not isinstance(entry, dict):
            raise RegistryParseError(f"대조군 targets[{index}] 가 object 가 아니다")
        missing = [k for k in _REQUIRED_JSON_TARGET_KEYS if k not in entry]
        if missing:
            raise RegistryParseError(f"대조군 targets[{index}] 필수 키 누락: {missing}")
        tid = str(entry["target_id"])
        if tid in targets:
            raise RegistryIntegrityError(f"대조군 JSON 에 중복 target_id: {tid!r}")
        targets[tid] = entry
    return families, targets


def _crosscheck_against_control(
    manifest_targets: Sequence[Mapping[str, Any]],
    manifest_families: Mapping[str, Mapping[str, Any]],
    csv_rows: Mapping[str, Mapping[str, str]],
    control_families: Mapping[str, Mapping[str, Any]],
    control_targets: Mapping[str, Mapping[str, Any]],
) -> None:
    """동결 manifest 와 SSOTV3 대조군을 byte-exact 로 대조. 불일치는 전량 실패."""
    manifest_ids = {str(t["target_id"]) for t in manifest_targets}
    for label, control_ids in (("CSV", set(csv_rows)), ("JSON", set(control_targets))):
        if manifest_ids != control_ids:
            raise RegistryIntegrityError(
                f"manifest 와 대조군 {label} 의 target 집합이 다르다 — "
                f"manifest 에만: {sorted(manifest_ids - control_ids)}, "
                f"{label} 에만: {sorted(control_ids - manifest_ids)}"
            )
    if set(manifest_families) != set(control_families):
        raise RegistryIntegrityError(
            "manifest 와 대조군의 family 집합이 다르다 — "
            f"manifest 에만: {sorted(set(manifest_families) - set(control_families))}, "
            f"대조군에만: {sorted(set(control_families) - set(manifest_families))}"
        )

    conflicts: list[str] = []
    for target in manifest_targets:
        tid = str(target["target_id"])
        row = csv_rows[tid]
        for mk, ck in _MANIFEST_VS_CSV:
            if target[mk] != row[ck]:
                conflicts.append(
                    f"{tid}.{mk}: manifest={target[mk]!r} != SSOTV3 csv[{ck}]={row[ck]!r}"
                )
        control_target = control_targets[tid]
        for mk, jk in _MANIFEST_VS_JSON_TARGET:
            if target[mk] != control_target[jk]:
                conflicts.append(
                    f"{tid}.{mk}: manifest={target[mk]!r} != "
                    f"SSOTV3 json targets[{jk}]={control_target[jk]!r}"
                )

    for fid, family in manifest_families.items():
        control_family = control_families[fid]
        for key in _MANIFEST_VS_JSON_FAMILY:
            if family[key] != control_family[key]:
                conflicts.append(
                    f"family {fid}.{key}: manifest={family[key]!r} != "
                    f"SSOTV3 json task_families[{key}]={control_family[key]!r}"
                )

    if conflicts:
        raise RegistryConflictError(
            f"동결 manifest 와 SSOTV3 대조군이 {len(conflicts)}개 필드에서 불일치한다 "
            "(하나를 임의로 고르지 않는다):\n  " + "\n  ".join(conflicts)
        )


# --------------------------------------------------------------------------------------
# 계약 조립
# --------------------------------------------------------------------------------------


def _blank_to_none(value: Any) -> str | None:
    """빈 문자열을 "값 없음"(``None``)으로 정규화한다. 필드 이름에 의존하지 않는다."""
    text = str(value)
    if text:
        return text
    return None


def _build_contract(target: Mapping[str, Any], family: Mapping[str, Any]) -> TaskContract:
    endpoint_contract = str(target["endpoint_contract"])
    contract_fields: dict[str, Any] = {
        "target_id": str(target["target_id"]),
        "family_id": str(target["family_id"]),
        "service": str(target["service_name"]),
        "starting_url": str(target["starting_url"]),
        "frozen_task": str(target["frozen_task"]),
        "task_instruction": str(target["task_instruction"]),
        # "없음" 을 포함해 소스 문자열을 그대로 보존한다. 의미 해석은 하지 않는다.
        "fixed_fixture": str(target["fixed_fixture"]),
        # 빈 문자열은 "override 없음" 이므로 None. 그 외에는 원문 보존.
        "fixture_override": _blank_to_none(target["fixture_override"]),
        "endpoint_contract": endpoint_contract,
        "forbidden_actions": tuple(target["forbidden_actions"]),
        "endpoint_contract_hash": _sha256_text(endpoint_contract),
        # metadata 전용. 아래 어떤 분기·조건에도 쓰이지 않는다.
        "legacy_archetype": _blank_to_none(family["legacy_archetype"]),
        "mobile_web_eligibility": str(target["mobile_web_eligibility"]),
        # 사전등록된 층. manifest 원문 보존 ("_" 도 그대로 둔다).
        "stratum": _blank_to_none(target["stratum"]),
        "is_pilot_5": bool(target["is_pilot_5"]),
        "collection_order": int(target["collection_order"]),
        # R3. manifest 가 명시하지 않으면 PRIMARY 로 동결한다 (본표본 정의).
        "task_role": str(target.get("task_role", TASK_ROLE_PRIMARY)),
    }
    return TaskContract(
        **contract_fields,
        task_contract_hash=recompute_task_contract_hash(contract_fields),
        # R5. 관측값이므로 동결 시점에는 언제나 None. runner 가 수집 시 채운다.
        fixture_input_mode=None,
    )


# --------------------------------------------------------------------------------------
# 공개 진입점
# --------------------------------------------------------------------------------------


def load_task_registry(
    manifest_path: Path | str | None = None,
    *,
    registry_path: Path | str | None = None,
    require_control: bool = True,
) -> TaskRegistry:
    """동결 MAIN50 manifest 에서 ``TaskContract`` 50건을 적재한다.

    :param manifest_path: 동결 manifest 파일. ``None`` 이면 :data:`DEFAULT_MANIFEST_PATH`.
    :param registry_path: 대조군 SSOTV3 디렉터리. ``None`` 이면 상위 탐색.
    :param require_control: ``True`` (기본) 면 대조군 대조를 반드시 수행한다.
        ``False`` 는 대조 없이 정본만 적재한다 — 대조군을 실제로 확보할 수 없는
        환경에서만 **명시적으로** 쓴다. 조용한 우회 경로가 아니다.
    :raises RegistrySourceMissingError: manifest/대조군 부재.
    :raises RegistryParseError: 인코딩·문법·필수 필드·타입 문제.
    :raises RegistryIntegrityError: 수량·균형·중복·해시·순서 불변조건 위반.
    :raises RegistryConflictError: manifest 와 대조군 값 불일치.
    """
    resolved_manifest = resolve_manifest_path(manifest_path)
    raw = resolved_manifest.read_bytes()
    document = _load_json_document(resolved_manifest)

    _validate_manifest_shape(document, resolved_manifest)
    manifest_families = _parse_manifest_families(document, resolved_manifest)
    manifest_targets = _parse_manifest_targets(document, manifest_families, resolved_manifest)
    reserve = _parse_replacement_reserve(
        document, manifest_families, manifest_targets, resolved_manifest
    )
    applied, applied_source = _parse_applied_replacements(document, resolved_manifest)

    control_dir: Path | None = None
    control_csv_sha: str | None = None
    control_json_sha: str | None = None
    if require_control:
        control_dir = resolve_ssot_dir(registry_path)
        csv_path = _require_file(control_dir, TASK_REGISTRY_CSV_NAME)
        json_path = _require_file(control_dir, TARGET_FRAME_JSON_NAME)
        csv_rows = _read_control_csv(csv_path)
        control_families, control_targets = _read_control_json(json_path)
        _crosscheck_against_control(
            manifest_targets, manifest_families, csv_rows, control_families, control_targets
        )
        control_csv_sha = _sha256_bytes(csv_path.read_bytes())
        control_json_sha = _sha256_bytes(json_path.read_bytes())

    contracts = tuple(
        _build_contract(target, manifest_families[str(target["family_id"])])
        for target in manifest_targets
    )
    # 조립 후 사후검증: 조용한 부분 로드가 없었음을 한 번 더 확인한다.
    if len(contracts) != EXPECTED_TARGET_COUNT:
        raise RegistryIntegrityError(f"계약 조립 결과가 {len(contracts)}건이다")

    return TaskRegistry(
        manifest_path=resolved_manifest,
        manifest_version=str(document["version"]),
        manifest_status=str(document["status"]),
        declared_manifest_sha256=str(document[MANIFEST_HASH_FIELD]),
        manifest_body_sha256=compute_manifest_body_sha256(document),
        manifest_file_sha256=compute_manifest_file_sha256(raw),
        real_target_allowed=bool(document.get("real_target_allowed", False)),
        contracts=contracts,
        replacement_rule=document.get("replacement_rule", {}),
        replacement_reserve=reserve,
        applied_replacements=applied,
        applied_replacements_source=applied_source,
        control_source_dir=control_dir,
        control_csv_sha256=control_csv_sha,
        control_json_sha256=control_json_sha,
    )
