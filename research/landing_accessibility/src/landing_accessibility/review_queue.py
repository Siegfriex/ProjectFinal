"""measurement_entity review queue 의 **멤버십 유도 규칙** — 손입력을 구조 규칙으로 바꾼다.

## 무엇이 남아 있던 결함인가 (v1 승계부채 `queue-membership-still-hand-set-in-entity-spec`)

C012(W1) 이 고친 것은 `needs_human_review` **한 칸**이다. 그 칸은 이제
`review_decision == 'UNRESOLVED'` 에서 유도되는 파생값이다. 그러나 **누가 큐에 오르는가**,
즉 큐 멤버십 자체는 여전히 `build_canonical_entities.ENTITY_SPEC` 세 번째 원소의 손입력
`bool` 이었다. 그래서 다음 두 경로가 열려 있었다.

* 큐에 올라야 할 entity 의 플래그를 `False` 로 두면 **아무 검사도 걸리지 않고** 빌드가
  `exit 0` 으로 끝난다. 판정이 없으므로 `review_decision` 도 비고, 원장에도 남지 않는다.
  "판정되지 않은 채 조용히 사라진 모호성" 이 무증상으로 통과한다.
* 그것을 잡던 유일한 장치는 `tests/test_c012_review_and_grouping.py` 의
  `EXPECTED_QUEUE_SIZE = 7` 이라는 **하드코딩 리터럴**이었다. 리터럴은 크기만 본다.
  한 건을 빼고 다른 한 건을 넣으면 크기는 7 그대로라 통과한다. 그리고 원자료가 늘어나
  큐가 정당하게 커져야 할 때도 리터럴은 그저 틀린 숫자가 된다.

## 이 모듈이 하는 일

큐 멤버십을 **원자료에서 유도**한다. 입력은 `state/source_ranking_rows.parquet` 이 가진
`(entity_name_raw, domain)` 과 그것을 canonical key 로 접는 매핑뿐이다. 연구자의 의견도,
회사 관계 상식도, 이름 목록도 들어가지 않는다.

유도 규칙 세 가지 — 전부 "원문 표기가 만든 모호성" 이다:

| 규칙 | 조건 | 왜 사람이 봐야 하는가 |
|---|---|---|
| `QR1_ALIAS_ABSORPTION` | 한 canonical entity 가 서로 다른 `entity_name_raw` 를 2종 이상 흡수했다 | 흡수가 정당한지(오타 vs 별개 브랜드)는 원문 대조 없이 결정할 수 없다 |
| `QR2_CROSS_DOMAIN_IDENTICAL_LABEL` | 두 도메인에 **문자 단위로 같은** 표기가 있는데 canonical key 는 다르다 | 표기가 같은데 나눴다면 나눈 근거가 원문에 있어야 한다 |
| `QR3_CROSS_DOMAIN_COMPONENT_LABEL` | 한쪽 표기가 다른 도메인 표기의 **슬래시 구성요소**다 (`네이버` ⊂ `네이버/네이버페이`) | 부분·전체 관계는 같은 대상일 수도 다른 대상일 수도 있다 |

규칙은 **대칭**이다. 관계에 걸린 두 entity 가 함께 큐에 오른다 — 한쪽만 판정하고 반대편을
방치하는 경로를 막는다.

## 이 규칙이 임계값을 새로 만들지 않는다는 것

세 규칙 어디에도 유사도 점수·임계값·컷오프가 없다. 전부 문자열 동일성과 슬래시 분해라는
**결정적 술어**다. 편집거리나 부분문자열 포함 같은 느슨한 술어를 쓰지 않은 이유가 이것이다 —
그런 술어는 임계값을 요구하고, 임계값은 새 연구기준이 된다.

## 실측 (2026-08-27, exec V2-C008)

C012 가 손으로 세운 큐 7건과 이 규칙이 원자료에서 유도한 7건이 **정확히 일치한다.**

    QR1 hyundai_homeshopping_hmall
    QR2 coupang_app, coupang_retail
    QR3 gmarket_app, gmarket_auction, naver_app, naver_naverpay

과탐 0 · 누락 0. 그래서 이 규칙은 기존 판정을 바꾸지 않고, 손입력만 대체한다.
`tests/test_c012_review_and_grouping.py` 의 반례 주입 테스트가 이 성질을 고정한다.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from itertools import combinations

#: 한 canonical entity 가 2종 이상의 원문 표기를 흡수했다.
QR_ALIAS_ABSORPTION = "QR1_ALIAS_ABSORPTION"

#: 서로 다른 도메인에 문자 단위로 동일한 원문 표기가 있는데 canonical key 가 다르다.
QR_CROSS_DOMAIN_IDENTICAL_LABEL = "QR2_CROSS_DOMAIN_IDENTICAL_LABEL"

#: 한쪽 원문 표기가 다른 도메인 표기의 슬래시 구성요소다.
QR_CROSS_DOMAIN_COMPONENT_LABEL = "QR3_CROSS_DOMAIN_COMPONENT_LABEL"

ALL_QUEUE_RULES: frozenset[str] = frozenset(
    {QR_ALIAS_ABSORPTION, QR_CROSS_DOMAIN_IDENTICAL_LABEL, QR_CROSS_DOMAIN_COMPONENT_LABEL}
)


class ReviewQueueError(Exception):
    """review queue 멤버십 계약 위반."""


class ReviewQueueMismatchError(ReviewQueueError):
    """선언된 큐와 원자료에서 유도한 큐가 다르다."""


def label_components(raw: str) -> tuple[str, ...]:
    """원문 표기를 슬래시로 분해한다. 분해 자체가 판정은 아니다.

    `'네이버/네이버페이'` -> `('네이버', '네이버페이')`
    `'쿠팡'` -> `('쿠팡',)`
    """
    return tuple(part.strip() for part in raw.split("/") if part.strip())


def derive_review_queue(
    entity_rows: Iterable[tuple[str, str, str]],
) -> dict[str, tuple[str, ...]]:
    """원자료에서 review queue 멤버십을 유도한다.

    Args:
        entity_rows: `(canonical_service_key, domain, entity_name_raw)` 삼중항.
            중복은 무시된다. 축이 `INDUSTRY_CATEGORY` 인 행은 호출자가 걸러 넣는다 —
            업종 축은 브랜드가 아니라 애초에 measurement_entity 모호성의 대상이 아니다.

    Returns:
        `canonical_service_key -> 발동한 규칙 id 튜플(정렬됨)`.
        큐에 오르지 않는 entity 는 키 자체가 없다.
    """
    raws_of: dict[str, set[str]] = defaultdict(set)
    domain_of: dict[str, str] = {}
    for ckey, domain, raw in entity_rows:
        raws_of[ckey].add(raw)
        prior = domain_of.setdefault(ckey, domain)
        if prior != domain:
            raise ReviewQueueError(
                f"{ckey}: measurement_entity 가 도메인을 넘나든다 ({prior} / {domain})"
            )

    triggered: dict[str, set[str]] = defaultdict(set)

    # QR1 — 흡수는 그 자체로 원문 대조를 요구한다.
    for ckey, raws in raws_of.items():
        if len(raws) > 1:
            triggered[ckey].add(QR_ALIAS_ABSORPTION)

    # QR2 / QR3 — 도메인을 가로지르는 표기 관계. 관계에 걸린 양쪽을 함께 올린다.
    for left, right in combinations(sorted(raws_of), 2):
        if domain_of[left] == domain_of[right]:
            continue
        for a in raws_of[left]:
            for b in raws_of[right]:
                if a == b:
                    triggered[left].add(QR_CROSS_DOMAIN_IDENTICAL_LABEL)
                    triggered[right].add(QR_CROSS_DOMAIN_IDENTICAL_LABEL)
                elif a in label_components(b) or b in label_components(a):
                    triggered[left].add(QR_CROSS_DOMAIN_COMPONENT_LABEL)
                    triggered[right].add(QR_CROSS_DOMAIN_COMPONENT_LABEL)

    return {ckey: tuple(sorted(rules)) for ckey, rules in sorted(triggered.items())}


def assert_queue_matches_declaration(
    entity_rows: Iterable[tuple[str, str, str]],
    declared: Iterable[str],
) -> dict[str, tuple[str, ...]]:
    """유도한 큐와 선언된 큐가 정확히 같은지 단언한다.

    크기가 아니라 **집합**을 본다. 한 건을 빼고 다른 한 건을 넣어도 걸린다.
    """
    derived = derive_review_queue(entity_rows)
    declared_set = set(declared)
    missing = sorted(set(derived) - declared_set)
    extra = sorted(declared_set - set(derived))
    if missing or extra:
        lines = ["review queue 멤버십이 원자료에서 유도한 것과 다르다."]
        if missing:
            lines.append(
                "  원자료가 요구하는데 큐에 없다: "
                + ", ".join(f"{k}({'+'.join(derived[k])})" for k in missing)
            )
        if extra:
            lines.append("  큐에 있는데 원자료 근거가 없다: " + ", ".join(extra))
        raise ReviewQueueMismatchError("\n".join(lines))
    return derived


def rows_from_frame(
    frame: object,
    key_by_pair: Mapping[tuple[str, str], str],
    *,
    excluded_axis_types: Iterable[str] = ("INDUSTRY_CATEGORY",),
) -> list[tuple[str, str, str]]:
    """`source_ranking_rows` 프레임에서 유도 입력 삼중항을 뽑는다.

    pandas 를 이 모듈의 의존성으로 만들지 않으려고 duck typing 으로 받는다 —
    필요한 것은 `entity_name_raw` · `domain` · `axis_type` 세 컬럼뿐이다.
    """
    excluded = set(excluded_axis_types)
    rows: list[tuple[str, str, str]] = []
    for raw, domain, axis in zip(
        frame["entity_name_raw"],  # type: ignore[index]
        frame["domain"],  # type: ignore[index]
        frame["axis_type"],  # type: ignore[index]
        strict=True,
    ):
        if axis in excluded:
            continue
        ckey = key_by_pair.get((raw, domain))
        if ckey is None:
            raise ReviewQueueError(f"ENTITY_SPEC 에 없는 원문 표기: {(raw, domain)}")
        rows.append((ckey, domain, raw))
    return rows


# --------------------------------------------------------------------------
# MERGE 판정의 alias assert
#
# v1 승계부채 `merge-decision-merges-nothing-no-alias-assert`.
#
# `MERGE` 는 "두 원문 표기를 하나의 measurement_entity 로 흡수한다" 는 뜻이다. 그런데
# 그 흡수가 **실제로 일어났는지** 확인하는 코드가 어디에도 없었다. 판정 원장에
# `review_decision: "MERGE"` 라고 적어 두기만 하면, 별칭이 하나도 흡수되지 않은
# entity 도 MERGE 로 통과했다. 판정이 데이터에 아무 흔적을 남기지 않으면 그것은 판정이
# 아니라 주석이다.
#
# 아래 세 조건이 MERGE 의 **데이터 상의 의미**다.
#   M1  MERGE 로 판정된 canonical entity 는 서로 다른 `entity_name_raw` 를 2종 이상 갖는다
#       (= QR1 이 발동한다). 하나뿐이면 흡수한 것이 없다.
#   M2  흡수된 표기는 별칭 원장(entity_alias_map)에 그 entity 의 service_id 로 등재돼 있다.
#       원자료에만 있고 별칭 원장에 없으면 흡수가 아니라 유실이다.
#   M3  흡수된 표기가 다른 canonical entity 로도 매핑되지 않는다. 매핑되면 흡수가 아니라
#       중복이며, 그 표기의 행이 두 entity 에 동시에 귀속된다.
# --------------------------------------------------------------------------

MERGE_DECISION = "MERGE"


class MergeDecisionError(ReviewQueueError):
    """MERGE 판정이 데이터 상의 흡수와 대응하지 않는다."""


def assert_merge_decisions_absorb_aliases(
    entity_rows: Iterable[tuple[str, str, str]],
    decisions: Mapping[str, str | None],
    alias_pairs: Iterable[tuple[str, str]],
) -> dict[str, tuple[str, ...]]:
    """`MERGE` 판정이 실제 별칭 흡수와 1:1 로 대응하는지 단언한다.

    Args:
        entity_rows: `(canonical_service_key, domain, entity_name_raw)` 삼중항 (원자료).
        decisions: `canonical_service_key -> review_decision` (판정이 없으면 `None`).
        alias_pairs: 별칭 원장의 `(canonical_service_key, entity_name_raw)` 쌍.

    Returns:
        `canonical_service_key -> 흡수된 표기 튜플(정렬됨)`. MERGE 가 0건이면 빈 dict.
    """
    raws_of: dict[str, set[str]] = defaultdict(set)
    for ckey, _domain, raw in entity_rows:
        raws_of[ckey].add(raw)

    alias_of: dict[str, set[str]] = defaultdict(set)
    for ckey, raw in alias_pairs:
        alias_of[ckey].add(raw)

    absorbed: dict[str, tuple[str, ...]] = {}
    for ckey, decision in sorted(decisions.items()):
        if decision != MERGE_DECISION:
            continue
        raws = raws_of.get(ckey, set())
        # M1 — 흡수할 것이 있어야 MERGE 다.
        if len(raws) < 2:
            raise MergeDecisionError(
                f"{ckey}: MERGE 판정인데 원문 표기가 {sorted(raws)} 뿐이다 — 흡수한 것이 없다. "
                "판정이 데이터에 흔적을 남기지 않으면 그것은 판정이 아니다."
            )
        # M2 — 흡수된 표기가 별칭 원장에 있어야 한다.
        missing = sorted(raws - alias_of.get(ckey, set()))
        if missing:
            raise MergeDecisionError(
                f"{ckey}: MERGE 로 흡수했다는 표기가 별칭 원장에 없다: {missing}"
            )
        # M3 — 흡수된 표기가 다른 entity 로도 가면 안 된다.
        for other, other_raws in raws_of.items():
            if other == ckey:
                continue
            shared = sorted(raws & other_raws)
            if shared:
                raise MergeDecisionError(
                    f"{ckey}: 흡수한 표기 {shared} 가 {other} 로도 매핑된다 — 흡수가 아니라 중복이다"
                )
        absorbed[ckey] = tuple(sorted(raws))
    return absorbed
