"""`older_relevance` 정본 표 — **동결됨** (`LA-ORS-20260827`).

Claude A(Analysis Governor)가 2026-08-27 12:25 KST에, **REAL TARGET evidence 0건
상태**(outcome-blind)에서 33개 전수 배정을 동결했다. 이 모듈은 그 정본 문서를
**커밋 SHA로 고정해 읽고, 선언된 sha256과 대조한 뒤** 파싱한다.

```
경로      research/landing_accessibility/control/OLDER_RELEVANT_KWCAG_SUBSET.md
control   333119e6821166cbba7c950203098f199f0fdc13
blob SHA  85f506c248b577c5067d10802b894b65eecb74be
sha256    da4b5208c91dd7634fc9e50d7a883674ad7666fc3828f359e4f428b3be863f8e
```

**이것은 외부 표준이 아니라 본 연구진의 판정이다** — KWCAG에는 공식 "고령자
관련" 지정이 없다(정본 문서 §0). 산출물이 이를 외부 권위처럼 인용하지 않도록
`LIMITATIONS_REQUIRED_ITEMS`(문서 §5)를 그대로 실어 나른다.

## 분모에 대한 정합 (문서 §3 · `ANALYSIS_CONTRACT §2`)

**태깅 소계 22는 분모가 아니다.** 분모는 서비스마다 다르며
`EligibleOlderRelevant_i` = older-relevant(≠`OTHER`) 중 그 관측에서
`final_status ∈ {PASS, FAIL}`로 **판정된 것**의 수다. 22는 태깅된 criterion
수이고, Pilot r4(n=257)에서 실제 적용기회가 확인된 것은 12개 — 분모의 실질
크기는 12 근방이다. `EligibleOlderRelevant_i = 0`이면 `FailRate = NULL`이며
0으로 대체하지 않는다.

## 기계 판독 규약 (문서 §4)

- mart의 `older_relevance`가 이 표와 다르면 **C1 `OLDER_TAG_DRIFT`**.
- 이 표에 없는 criterion id가 mart에 나타나면 **C1 `SUSPECT_CRITERION_ID`**.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── 정본 문서의 좌표 — 전부 고정값이다 ──────────────────────────────────────
CANONICAL_DOC_ID = "LA-ORS-20260827"
CANONICAL_DOC_PATH = "research/landing_accessibility/control/OLDER_RELEVANT_KWCAG_SUBSET.md"
CANONICAL_CONTROL_COMMIT = "333119e6821166cbba7c950203098f199f0fdc13"
CANONICAL_BLOB_SHA = "85f506c248b577c5067d10802b894b65eecb74be"
CANONICAL_DOC_SHA256 = "da4b5208c91dd7634fc9e50d7a883674ad7666fc3828f359e4f428b3be863f8e"
CANONICAL_FROZEN_AT = "2026-08-27T12:25:00+09:00"
CANONICAL_FROZEN_BEFORE_ANY_REAL_EVIDENCE = True

#: 문서 §3 집계 — 파싱 결과가 이와 다르면 파싱이 어긋난 것이므로 실패시킨다.
EXPECTED_DOMAIN_COUNTS: dict[str, int] = {
    "VISION": 3,
    "MOTOR": 4,
    "COGNITIVE_NAVIGATION": 15,
    "OTHER": 11,
}
EXPECTED_TOTAL = 33
EXPECTED_OLDER_RELEVANT_SUBTOTAL = 22
EXPECTED_OLDER_RELEVANT_PILOT_APPLIED = 12

#: 문서 §5 — `LIMITATIONS.md` 필수 기재 5항목. **원문 그대로** 옮긴다.
LIMITATIONS_REQUIRED_ITEMS: tuple[str, ...] = (
    "이 태깅은 외부 표준이 아니라 본 연구진의 판정이다. KWCAG에 공식 '고령자 관련' 지정은 없다. "
    "배정 근거는 정본 문서 §2에 criterion 단위로 공개돼 있으며, 다른 배정이 가능하다.",
    "데이터 관측 이전에 동결됐다 (2026-08-27 12:25 KST, REAL TARGET evidence 0건 상태).",
    "청각 도메인이 어휘에 없다. 노인성 난청은 실재하는 노화 변화지만 본 프로토콜이 청각 접근을 "
    "측정하지 않아 `1.2.1`이 `OTHER`로 분류됐다. 청각 장벽의 부재를 뜻하지 않는다.",
    "`NOT_AUTOMATABLE`로 인해 태깅된 22개 중 실제로 판정되는 것은 그보다 훨씬 적다. "
    "`EligibleOlderRelevant`·`undetermined_n`·`undetermined_rate`를 반드시 병기한다.",
    "서비스별 `EligibleOlderRelevant_i = 0`인 경우 `FailRate = NULL`이며 그 건수를 보고한다.",
)

#: 문서 §0 — 이 표가 **무엇이 아닌지**. 산출물에 항상 동반한다.
NOT_AN_EXTERNAL_STANDARD_NOTICE = (
    "KWCAG에는 '고령자 관련'이라는 공식 지정이 없다. 이 표는 외부 표준이 아니라 "
    "본 연구진(Claude A, Analysis Governor)의 판정이며, 다른 연구가 다르게 배정할 수 있다. "
    "KWCAG threshold 자체는 건드리지 않았다 — 이 표는 '어느 criterion을 분모에 넣는가'만 정한다."
)

#: `source_kind`가 이 집합에 있으면 정본 표 없이도 FailRate 계산을 허용한다.
NON_AUTHORITATIVE_SOURCE_KINDS: frozenset[str] = frozenset({"SYNTHETIC", "EMPTY", "FIXTURE"})

_VALID_DOMAINS = frozenset({"VISION", "MOTOR", "COGNITIVE_NAVIGATION", "OTHER"})
_ROW_RE = re.compile(
    r"^\|\s*(?P<id>\d+\.\d+\.\d+)\s*\|(?P<name>[^|]*)\|\s*`(?P<rel>[A-Z_]+)`\s*\|"
    r"(?P<auto>[^|]*)\|(?P<pilot>[^|]*)\|(?P<rationale>[^|]*)\|\s*$"
)


class OlderRelevanceNotFrozenError(RuntimeError):
    """정본 표가 동결/주입되지 않은 상태에서 실제 데이터로 FailRate를 계산하려 했다."""


class OlderRelevanceShaMismatch(ValueError):
    """정본 문서의 실제 해시가 선언된 SHA와 다르다 — 문서가 바뀌었거나 잘못 읽었다."""


class OlderRelevanceParseError(ValueError):
    """정본 문서 §2 배정표 파싱이 문서 §3 집계와 어긋난다."""


class OlderRelevanceDrift(ValueError):
    """C1 — mart의 `older_relevance`가 정본과 다르거나 표에 없는 criterion id가 나타났다."""


@dataclass(frozen=True)
class CriterionTag:
    """정본 배정표 한 행."""

    criterion_id: str
    name: str
    older_relevance: str
    automation: str
    pilot_applied: bool
    rationale: str

    @property
    def is_older_relevant(self) -> bool:
        return self.older_relevance != "OTHER"


@dataclass(frozen=True)
class CanonicalOlderRelevance:
    """동결된 정본 표."""

    doc_id: str
    tags: dict[str, CriterionTag]
    #: 정본 **문서 파일**의 sha256 — A가 동결하고 coordinator가 실측 대조한 값.
    source_sha256: str
    #: 파싱된 매핑에서 유도한 해시 — 파싱이 조용히 달라지면 여기서 드러난다.
    mapping_sha256: str
    control_commit: str
    blob_sha: str
    source_path: str
    frozen_at: str
    frozen_before_any_real_evidence: bool
    limitations_required_items: tuple[str, ...] = field(default=LIMITATIONS_REQUIRED_ITEMS)

    @property
    def mapping(self) -> dict[str, str]:
        """`criterion_id → older_relevance`."""
        return {cid: tag.older_relevance for cid, tag in self.tags.items()}

    def relevance_of(self, criterion_id: str) -> str | None:
        tag = self.tags.get(criterion_id)
        return tag.older_relevance if tag else None

    def older_relevant_ids(self) -> tuple[str, ...]:
        return tuple(sorted(cid for cid, t in self.tags.items() if t.is_older_relevant))

    def pilot_applied_older_relevant_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(cid for cid, t in self.tags.items() if t.is_older_relevant and t.pilot_applied)
        )


_CANONICAL: CanonicalOlderRelevance | None = None


# ── 문서 읽기 · 검증 · 파싱 ────────────────────────────────────────────────


def _repo_root() -> Path:
    # .../research/landing_accessibility/analysis/older_relevance_registry.py
    return Path(__file__).resolve().parents[3]


def read_canonical_document(*, repo_root: Path | None = None, verify: bool = True) -> str:
    """정본 문서를 **고정 커밋에서** 읽는다 (워킹트리 조작 방지).

    작업 트리에 파일이 있으면 그것도 허용하되, 어느 경로로 읽든 sha256이
    `CANONICAL_DOC_SHA256`과 일치해야 한다 — 일치하지 않으면 실패한다.
    """
    root = repo_root or _repo_root()
    text: str | None = None

    # 1순위: 고정 커밋의 blob (워킹트리 상태와 무관하다).
    try:
        raw = subprocess.run(
            ["git", "-C", str(root), "show", f"{CANONICAL_CONTROL_COMMIT}:{CANONICAL_DOC_PATH}"],
            capture_output=True,
            check=True,
        ).stdout
        text = raw.decode("utf-8")
    except (subprocess.CalledProcessError, FileNotFoundError, UnicodeDecodeError):
        text = None

    # 2순위: 워킹트리 파일 (그래도 sha256 대조를 통과해야 한다).
    if text is None:
        path = root / CANONICAL_DOC_PATH
        if not path.exists():
            raise OlderRelevanceNotFrozenError(
                f"정본 문서를 읽을 수 없다 — commit {CANONICAL_CONTROL_COMMIT[:12]}에도, "
                f"워킹트리 {path}에도 없다."
            )
        text = path.read_text(encoding="utf-8")

    if verify:
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual != CANONICAL_DOC_SHA256:
            raise OlderRelevanceShaMismatch(
                f"정본 문서 sha256 불일치. 선언={CANONICAL_DOC_SHA256} 실제={actual} — "
                "문서가 바뀌었으면 이 모듈의 상수와 변경이력을 함께 갱신해야 한다."
            )
    return text


def parse_older_relevance_table(text: str) -> dict[str, CriterionTag]:
    """정본 문서 §2 배정표를 파싱하고 §3 집계와 대조한다.

    집계가 어긋나면 `OlderRelevanceParseError` — 파싱이 조용히 몇 행을 놓치면
    분모가 조용히 달라지므로, 문서 자신이 적어 둔 집계를 검산으로 쓴다.
    """
    tags: dict[str, CriterionTag] = {}
    for line in text.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        rel = m.group("rel")
        if rel not in _VALID_DOMAINS:
            raise OlderRelevanceParseError(
                f"허용되지 않은 도메인 값: {rel!r} (00_SSOT §4의 4값만 쓴다)"
            )
        cid = m.group("id")
        pilot_cell = m.group("pilot").strip()
        tags[cid] = CriterionTag(
            criterion_id=cid,
            name=m.group("name").strip(),
            older_relevance=rel,
            automation=m.group("auto").strip(),
            pilot_applied="✓" in pilot_cell,
            rationale=m.group("rationale").strip(),
        )

    if len(tags) != EXPECTED_TOTAL:
        raise OlderRelevanceParseError(
            f"배정표 행 수가 {len(tags)}개다 — 문서 §3 집계는 {EXPECTED_TOTAL}개다."
        )
    counts: dict[str, int] = {}
    for tag in tags.values():
        counts[tag.older_relevance] = counts.get(tag.older_relevance, 0) + 1
    if counts != EXPECTED_DOMAIN_COUNTS:
        raise OlderRelevanceParseError(
            f"도메인별 집계 불일치. 파싱={counts} 문서 §3={EXPECTED_DOMAIN_COUNTS}"
        )
    older = [t for t in tags.values() if t.is_older_relevant]
    if len(older) != EXPECTED_OLDER_RELEVANT_SUBTOTAL:
        raise OlderRelevanceParseError(
            f"older-relevant 소계 불일치. 파싱={len(older)} 문서 §3={EXPECTED_OLDER_RELEVANT_SUBTOTAL}"
        )
    applied = [t for t in older if t.pilot_applied]
    if len(applied) != EXPECTED_OLDER_RELEVANT_PILOT_APPLIED:
        raise OlderRelevanceParseError(
            f"pilot_applied older-relevant 불일치. 파싱={len(applied)} "
            f"문서 §3={EXPECTED_OLDER_RELEVANT_PILOT_APPLIED}"
        )
    return tags


def canonical_mapping_sha256(mapping: dict[str, str]) -> str:
    """매핑 자체의 정규화 해시 — 키 정렬 + 공백 없는 JSON 직렬화 기준."""
    payload = json.dumps(mapping, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_frozen_canonical(*, repo_root: Path | None = None) -> CanonicalOlderRelevance:
    """정본 문서를 읽고(sha256 대조) 파싱해(집계 대조) 레지스트리에 주입한다."""
    global _CANONICAL
    text = read_canonical_document(repo_root=repo_root, verify=True)
    tags = parse_older_relevance_table(text)
    mapping = {cid: t.older_relevance for cid, t in tags.items()}
    _CANONICAL = CanonicalOlderRelevance(
        doc_id=CANONICAL_DOC_ID,
        tags=tags,
        source_sha256=CANONICAL_DOC_SHA256,
        mapping_sha256=canonical_mapping_sha256(mapping),
        control_commit=CANONICAL_CONTROL_COMMIT,
        blob_sha=CANONICAL_BLOB_SHA,
        source_path=CANONICAL_DOC_PATH,
        frozen_at=CANONICAL_FROZEN_AT,
        frozen_before_any_real_evidence=CANONICAL_FROZEN_BEFORE_ANY_REAL_EVIDENCE,
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


def ensure_frozen(*, repo_root: Path | None = None) -> CanonicalOlderRelevance:
    """아직 주입되지 않았으면 정본 문서에서 지연 로드한다."""
    if _CANONICAL is None:
        return load_frozen_canonical(repo_root=repo_root)
    return _CANONICAL


def assert_older_relevance_frozen(source_kind: str) -> None:
    """**fail-closed 가드** — 실제 데이터로 FailRate를 계산하려는데 정본 표가
    없으면 실패시킨다. synthetic/empty/fixture는 그대로 통과한다.

    정본이 동결된 지금은, 실제 데이터 경로에서 문서를 지연 로드해 자동으로
    열린다 — 다만 **sha256·집계 대조를 통과할 때만** 열린다.
    """
    if source_kind in NON_AUTHORITATIVE_SOURCE_KINDS:
        return
    if _CANONICAL is None:
        try:
            load_frozen_canonical()
        except (
            OlderRelevanceShaMismatch,
            OlderRelevanceParseError,
            OlderRelevanceNotFrozenError,
        ) as exc:
            raise OlderRelevanceNotFrozenError(
                f"source_kind={source_kind!r}(실제 데이터)로 OlderRelevantKWCAGFailRate를 "
                f"계산하려 했으나 정본 표를 확보하지 못했다: {exc}"
            ) from exc


# ── C1 드리프트 검사 (문서 §4 기계 판독 규약) ──────────────────────────────


def check_mart_older_relevance_drift(
    criterion_ids: list[str], older_relevance_values: list[str]
) -> list[dict[str, Any]]:
    """mart의 `(criterion_id, older_relevance)` 쌍을 정본과 대조한다.

    - 값이 다르면 `OLDER_TAG_DRIFT`
    - 표에 없는 id면 `SUSPECT_CRITERION_ID`

    정본이 주입돼 있지 않으면 빈 목록(검사 불가)을 돌려준다 — 이 함수 자체는
    fail-closed 가드가 아니다(그 역할은 `assert_older_relevance_frozen`).
    """
    canonical = _CANONICAL
    if canonical is None:
        return []
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for cid, rel in zip(criterion_ids, older_relevance_values, strict=True):
        key = (str(cid), str(rel))
        if key in seen:
            continue
        seen.add(key)
        expected = canonical.relevance_of(str(cid))
        if expected is None:
            findings.append(
                {
                    "code": "SUSPECT_CRITERION_ID",
                    "severity": "C1",
                    "criterion_id": str(cid),
                    "detail": f"정본 배정표({CANONICAL_DOC_ID})에 없는 criterion id다.",
                }
            )
        elif expected != str(rel):
            findings.append(
                {
                    "code": "OLDER_TAG_DRIFT",
                    "severity": "C1",
                    "criterion_id": str(cid),
                    "expected": expected,
                    "actual": str(rel),
                    "detail": "mart의 older_relevance가 정본 배정과 다르다.",
                }
            )
    return findings


def assert_no_mart_drift(criterion_ids: list[str], older_relevance_values: list[str]) -> None:
    findings = check_mart_older_relevance_drift(criterion_ids, older_relevance_values)
    if findings:
        raise OlderRelevanceDrift(f"C1 — 정본 배정표와 어긋난다({len(findings)}건): {findings[:5]}")


# ── 산출물용 상태 블록 ─────────────────────────────────────────────────────


def registry_status() -> dict[str, Any]:
    """산출물에 그대로 실을 수 있는 동결 상태 블록."""
    if _CANONICAL is None:
        return {
            "frozen": False,
            "doc_id": CANONICAL_DOC_ID,
            "source_sha256": None,
            "note": (
                "정본 older_relevance 표가 이 프로세스에 주입되지 않았다 — 실제 데이터 "
                "FailRate 계산은 fail-closed로 차단된다(synthetic 경로만 허용)."
            ),
        }
    c = _CANONICAL
    return {
        "frozen": True,
        "doc_id": c.doc_id,
        "source_path": c.source_path,
        "control_commit": c.control_commit,
        "blob_sha": c.blob_sha,
        "source_sha256": f"sha256:{c.source_sha256}",
        "mapping_sha256": f"sha256:{c.mapping_sha256}",
        "frozen_at": c.frozen_at,
        "frozen_before_any_real_evidence": c.frozen_before_any_real_evidence,
        "criterion_count": len(c.tags),
        "domain_counts": dict(EXPECTED_DOMAIN_COUNTS),
        # 태깅 소계와 분모를 명확히 구분한다 — 22는 분모가 아니다.
        "older_relevant_tagged_subtotal": EXPECTED_OLDER_RELEVANT_SUBTOTAL,
        "older_relevant_pilot_applied": EXPECTED_OLDER_RELEVANT_PILOT_APPLIED,
        "denominator_note": (
            "태깅 소계 22는 **분모가 아니다.** 분모는 서비스마다 다르며 "
            "EligibleOlderRelevant_i = older-relevant(≠OTHER) 중 그 관측에서 "
            "final_status ∈ {PASS, FAIL}로 판정된 것의 수다(ANALYSIS_CONTRACT §2). "
            "Pilot r4에서 실제 적용기회가 확인된 것은 12개로, 분모의 실질 크기는 12 근방이다. "
            "EligibleOlderRelevant_i = 0이면 FailRate = NULL이며 0으로 대체하지 않는다."
        ),
        "not_an_external_standard": NOT_AN_EXTERNAL_STANDARD_NOTICE,
        "limitations_required_items": list(LIMITATIONS_REQUIRED_ITEMS),
    }
