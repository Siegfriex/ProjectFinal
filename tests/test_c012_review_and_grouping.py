"""C012 — review queue 해소 / web_target 구조 정합 / 구조적 debt 3건.

이 파일이 지키는 것도 스키마의 모양이 아니라 **다시 저지르면 안 되는 실수**들이다.

C011 이 세운 원칙을 그대로 따른다:
    파생물끼리의 일치는 검증이 아니다. 대조의 한쪽 끝은 반드시 원본이어야 한다.

그래서 W1 판정 인용은 산문으로 읽고 끝내지 않고, layer 별로 A1 원문에 다시 대본다.
BODY_TEXT 는 sources/wiseapp/raw/wiseapp933_text.txt 의 부분문자열인지,
PUBLISHER_TAGS 는 발행처 태그 목록의 원소인지, FIGURE_ROW 는 원자료 261행의 해당
panel_id/rank 에 실제로 그 표기가 있는지, ABSENCE 는 지정 파일에서 정말 0회인지.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
STATE = RESEARCH / "state"
WISEAPP = RESEARCH / "sources" / "wiseapp"
BODY_TEXT = WISEAPP / "raw" / "wiseapp933_text.txt"
AUTHORITY = WISEAPP / "authority_manifest.json"

sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility import authority_manifest as am  # noqa: E402
from landing_accessibility import evidence_manifest as em  # noqa: E402
from landing_accessibility import review_queue as rq  # noqa: E402

ALLOWED_REVIEW = {"MERGE", "KEEP_SEPARATE", "UNRESOLVED"}
ALLOWED_RELATIONSHIP = {"SAME_LANDING_EXPECTED", "DIFFERENT_LANDING_EXPECTED", "UNKNOWN"}
EXPECTED_QUEUE_SIZE = 7
EXPECTED_GROUPS = 68

pytestmark = pytest.mark.skipif(
    not (STATE / "service_master.parquet").exists(),
    reason="landing_accessibility state 산출물이 없다",
)


@pytest.fixture(scope="module")
def service_master() -> pd.DataFrame:
    return pd.read_parquet(STATE / "service_master.parquet")


@pytest.fixture(scope="module")
def web_target_group() -> pd.DataFrame:
    return pd.read_parquet(STATE / "web_target_group.parquet")


@pytest.fixture(scope="module")
def rows() -> pd.DataFrame:
    return pd.read_parquet(STATE / "source_ranking_rows.parquet")


@pytest.fixture(scope="module")
def ledger() -> dict:
    return json.loads((STATE / "entity_review_decisions.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def authority() -> dict:
    return json.loads(AUTHORITY.read_text(encoding="utf-8"))


# ── W1: review queue 해소 ────────────────────────────────────────────────────


def test_needs_human_review_is_derived_not_hand_set(service_master: pd.DataFrame) -> None:
    """미결 플래그를 손으로 켜고 끄면 '판정 없이 해소' 가 가능해진다.

    C011 판본은 needs_human_review 가 ENTITY_SPEC 의 손입력 bool 이었다. 판정 없이
    False 로 바꾸는 것만으로 큐가 비워질 수 있었다. 이제 파생값이다.
    """
    decided = service_master["review_decision"].notna()
    assert set(service_master.loc[decided, "review_decision"]) <= ALLOWED_REVIEW

    expected = service_master["review_decision"].eq("UNRESOLVED")
    assert service_master["needs_human_review"].equals(expected)

    # 판정이 없는 entity 는 애초에 큐에 오르지 않은 entity 다 — 미결이 아니다.
    assert not service_master.loc[~decided, "needs_human_review"].any()


def test_review_queue_of_seven_is_fully_accounted_for(
    service_master: pd.DataFrame, ledger: dict
) -> None:
    """큐는 7건이다. 오케스트레이터 state.json 은 5건으로 기록돼 있었다.

    5건은 review_queue 표에 적힌 '쟁점 3줄' 을 센 것이고, 실제 needs_human_review=True 인
    measurement_entity 는 coupang_app / coupang_retail 을 포함해 7건이었다.
    """
    decided = service_master[service_master["review_decision"].notna()]
    assert len(decided) == EXPECTED_QUEUE_SIZE
    assert set(decided["canonical_service_key"]) == {
        "hyundai_homeshopping_hmall",
        "naver_app",
        "naver_naverpay",
        "gmarket_app",
        "gmarket_auction",
        "coupang_app",
        "coupang_retail",
    }
    assert len(ledger["decisions"]) == EXPECTED_QUEUE_SIZE
    assert ledger["queue_size_before"] == EXPECTED_QUEUE_SIZE
    assert sum(ledger["distribution"].values()) == EXPECTED_QUEUE_SIZE
    assert ledger["unresolved_remaining"] == ledger["distribution"]["UNRESOLVED"]

    # 원장과 표가 같은 말을 해야 한다.
    by_key = {d["canonical_service_key"]: d for d in ledger["decisions"]}
    for row in decided.itertuples():
        assert by_key[row.canonical_service_key]["review_decision"] == row.review_decision
        assert by_key[row.canonical_service_key]["needs_human_review"] == bool(
            row.needs_human_review
        )


# ── V2-C008: review queue **멤버십**을 구조 규칙으로 고정한다 ───────────────────
#
# v1 승계부채 `queue-membership-still-hand-set-in-entity-spec`.
# C012 가 고친 것은 needs_human_review 한 칸이고, 누가 큐에 오르는가는 여전히
# ENTITY_SPEC 손입력이었다. 그것을 잡던 유일한 장치가 위의 EXPECTED_QUEUE_SIZE = 7 이라는
# **하드코딩 리터럴**인데, 리터럴은 크기만 본다 — 한 건을 빼고 다른 한 건을 넣으면 통과한다.
#
# 아래 테스트들은 리터럴을 쓰지 않는다. `state/source_ranking_rows.parquet` 원자료에서
# 큐를 다시 유도해 산출물과 대조하고, 규칙이 실제로 반례를 잡는지 **반례를 주입해** 확인한다.


def _entity_rows_from_state(rows: pd.DataFrame, service_master: pd.DataFrame) -> list[tuple]:
    """원자료 261행을 유도 입력 삼중항으로 바꾼다 — 산출물의 canonical 매핑만 빌린다."""
    alias = pd.read_parquet(STATE / "entity_alias_map.parquet")
    id2key = dict(
        zip(service_master["service_id"], service_master["canonical_service_key"], strict=True)
    )
    pair2key = {
        (r.entity_name_raw, r.domain): id2key[r.service_id]
        for r in alias.itertuples()
        if r.service_id in id2key
    }
    return rq.rows_from_frame(rows, pair2key)


def test_review_queue_membership_is_derived_from_the_source_rows(
    rows: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """큐 멤버십은 손입력이 아니라 원자료에서 유도된다 — 크기가 아니라 집합을 본다."""
    derived = rq.derive_review_queue(_entity_rows_from_state(rows, service_master))
    decided = set(
        service_master.loc[service_master["review_decision"].notna(), "canonical_service_key"]
    )
    assert set(derived) == decided, (
        "산출물의 review queue 와 원자료에서 유도한 큐가 다르다\n"
        f"  유도에만: {sorted(set(derived) - decided)}\n"
        f"  산출물에만: {sorted(decided - set(derived))}"
    )
    # 각 항목이 어떤 규칙으로 올라왔는지도 확정한다 — 우연히 크기만 맞는 경로를 막는다.
    assert derived == {
        "coupang_app": (rq.QR_CROSS_DOMAIN_IDENTICAL_LABEL,),
        "coupang_retail": (rq.QR_CROSS_DOMAIN_IDENTICAL_LABEL,),
        "gmarket_app": (rq.QR_CROSS_DOMAIN_COMPONENT_LABEL,),
        "gmarket_auction": (rq.QR_CROSS_DOMAIN_COMPONENT_LABEL,),
        "hyundai_homeshopping_hmall": (rq.QR_ALIAS_ABSORPTION,),
        "naver_app": (rq.QR_CROSS_DOMAIN_COMPONENT_LABEL,),
        "naver_naverpay": (rq.QR_CROSS_DOMAIN_COMPONENT_LABEL,),
    }


def test_queue_rule_catches_a_silently_dropped_member(
    rows: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """반례 ① — 큐에 올라야 할 entity 를 조용히 빼면 잡힌다.

    C012 이전 구조에서는 ENTITY_SPEC 플래그를 False 로 두는 것만으로 빌드가 exit 0 이었다.
    """
    entity_rows = _entity_rows_from_state(rows, service_master)
    declared = set(rq.derive_review_queue(entity_rows))
    with pytest.raises(rq.ReviewQueueMismatchError) as err:
        rq.assert_queue_matches_declaration(entity_rows, declared - {"coupang_retail"})
    assert "coupang_retail" in str(err.value)


def test_queue_rule_catches_a_member_added_without_source_basis(
    rows: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """반례 ② — 원자료 근거 없이 큐에 올린 entity 도 잡힌다. 크기 검사로는 못 잡는 방향이다."""
    entity_rows = _entity_rows_from_state(rows, service_master)
    declared = set(rq.derive_review_queue(entity_rows))
    with pytest.raises(rq.ReviewQueueMismatchError) as err:
        rq.assert_queue_matches_declaration(entity_rows, declared | {"kakaotalk"})
    assert "kakaotalk" in str(err.value)


def test_queue_size_stays_seven_while_membership_is_wrong(
    rows: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """반례 ③ — 한 건을 빼고 한 건을 넣으면 **크기는 7 그대로**다.

    이 반례가 EXPECTED_QUEUE_SIZE 리터럴이 왜 검사가 아닌지를 보여준다.
    리터럴은 통과시키고 구조 규칙은 차단한다.
    """
    entity_rows = _entity_rows_from_state(rows, service_master)
    tampered = (set(rq.derive_review_queue(entity_rows)) - {"naver_naverpay"}) | {"toss"}
    assert len(tampered) == EXPECTED_QUEUE_SIZE  # 리터럴 검사는 여기서 침묵한다
    with pytest.raises(rq.ReviewQueueMismatchError) as err:
        rq.assert_queue_matches_declaration(entity_rows, tampered)
    message = str(err.value)
    assert "naver_naverpay" in message and "toss" in message


def test_queue_rule_reacts_to_new_source_ambiguity() -> None:
    """반례 ④ — 원자료가 늘어 새 모호성이 생기면 큐도 자동으로 늘어난다.

    리터럴 7 은 이 경우 **틀린 숫자**가 되고, 규칙은 새 쌍을 스스로 찾아낸다.
    """
    base = [
        ("toss", "APP", "토스"),
        ("kakaotalk", "APP", "카카오톡"),
    ]
    assert rq.derive_review_queue(base) == {}
    grown = [*base, ("toss_pay_retail", "RETAIL", "토스/토스페이")]
    assert rq.derive_review_queue(grown) == {
        "toss": (rq.QR_CROSS_DOMAIN_COMPONENT_LABEL,),
        "toss_pay_retail": (rq.QR_CROSS_DOMAIN_COMPONENT_LABEL,),
    }


def test_queue_rule_uses_no_threshold_and_no_fuzzy_matching() -> None:
    """규칙은 결정적 술어만 쓴다 — 유사도·임계값을 새로 만들지 않았음을 고정한다.

    '토스' 와 '토스뱅크' 는 부분문자열 관계지만 슬래시 구성요소가 아니므로 큐에 오르지 않는다.
    느슨한 부분문자열 술어를 도입하면 이 테스트가 깨진다.
    """
    rows = [
        ("toss", "APP", "토스"),
        ("tossbank_retail", "RETAIL", "토스뱅크"),
    ]
    assert rq.derive_review_queue(rows) == {}
    assert rq.label_components("네이버/네이버페이") == ("네이버", "네이버페이")
    assert rq.label_components("쿠팡") == ("쿠팡",)


def test_queue_rule_rejects_a_domain_straddling_entity() -> None:
    """한 canonical key 가 두 도메인에 걸치면 유도 자체가 성립하지 않는다 — 조용히 넘어가지 않는다."""
    with pytest.raises(rq.ReviewQueueError):
        rq.derive_review_queue([("x", "APP", "가"), ("x", "RETAIL", "가")])


# ── V2-C008: MERGE 판정은 실제로 무언가를 흡수해야 한다 ────────────────────────
#
# v1 승계부채 `merge-decision-merges-nothing-no-alias-assert`.


def _alias_pairs(service_master: pd.DataFrame) -> list[tuple[str, str]]:
    alias = pd.read_parquet(STATE / "entity_alias_map.parquet")
    id2key = dict(
        zip(service_master["service_id"], service_master["canonical_service_key"], strict=True)
    )
    return [(id2key[r.service_id], r.entity_name_raw) for r in alias.itertuples()]


def test_the_single_merge_decision_actually_absorbs_an_alias(
    rows: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """MERGE 1건이 흡수한 것을 이름으로 확정한다 — '아무것도 병합하지 않는' MERGE 가 아니다."""
    entity_rows = _entity_rows_from_state(rows, service_master)
    decisions = dict(
        zip(
            service_master["canonical_service_key"],
            service_master["review_decision"],
            strict=True,
        )
    )
    absorbed = rq.assert_merge_decisions_absorb_aliases(
        entity_rows, decisions, _alias_pairs(service_master)
    )
    assert absorbed == {
        "hyundai_homeshopping_hmall": ("현대홈쇼핑/현대Hmall", "현대홈쇼핑/현대Hmallord")
    }
    # 흡수된 표기가 원자료에 실재해야 한다 — 대조의 한쪽 끝은 원본이다.
    raw_labels = set(rows["entity_name_raw"])
    for label in absorbed["hyundai_homeshopping_hmall"]:
        assert label in raw_labels


def test_merge_that_absorbs_nothing_is_rejected(
    rows: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """반례 ① — 표기가 1종뿐인 entity 에 MERGE 를 찍으면 잡힌다.

    이것이 결함 이름이 말하는 '아무것도 병합하지 않는 MERGE' 다. 옛 구조에서는 통과했다.
    """
    entity_rows = _entity_rows_from_state(rows, service_master)
    decisions = dict.fromkeys(service_master["canonical_service_key"], None)
    decisions["kakaotalk"] = rq.MERGE_DECISION  # 표기 1종
    with pytest.raises(rq.MergeDecisionError) as err:
        rq.assert_merge_decisions_absorb_aliases(
            entity_rows, decisions, _alias_pairs(service_master)
        )
    assert "kakaotalk" in str(err.value) and "흡수한 것이 없다" in str(err.value)


def test_merge_whose_absorbed_label_is_missing_from_the_alias_ledger_is_rejected(
    rows: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """반례 ② — 흡수했다면서 별칭 원장에 등재하지 않으면 잡힌다. 그것은 흡수가 아니라 유실이다."""
    entity_rows = _entity_rows_from_state(rows, service_master)
    decisions = dict(
        zip(
            service_master["canonical_service_key"],
            service_master["review_decision"],
            strict=True,
        )
    )
    pruned = [pair for pair in _alias_pairs(service_master) if pair[1] != "현대홈쇼핑/현대Hmallord"]
    with pytest.raises(rq.MergeDecisionError) as err:
        rq.assert_merge_decisions_absorb_aliases(entity_rows, decisions, pruned)
    assert "현대홈쇼핑/현대Hmallord" in str(err.value)


def test_merge_that_double_maps_a_label_is_rejected() -> None:
    """반례 ③ — 흡수한 표기가 다른 entity 로도 매핑되면 잡힌다. 흡수가 아니라 중복이다."""
    entity_rows = [
        ("a", "RETAIL", "가"),
        ("a", "RETAIL", "가b"),
        ("b", "APP", "가b"),
    ]
    with pytest.raises(rq.MergeDecisionError) as err:
        rq.assert_merge_decisions_absorb_aliases(
            entity_rows,
            {"a": rq.MERGE_DECISION, "b": None},
            [("a", "가"), ("a", "가b"), ("b", "가b")],
        )
    assert "중복" in str(err.value)


def test_zero_merge_decisions_is_a_valid_state_not_an_error() -> None:
    """MERGE 가 0건인 판정 집합은 정상이다 — 적용대상 없음(moot)을 오류로 만들지 않는다.

    web_target 그룹 가설 검정이 바로 이 경우다 (§ LANE B: MERGE 0 / SPLIT 2 / NOT_TESTABLE 1).
    """
    assert (
        rq.assert_merge_decisions_absorb_aliases(
            [("a", "APP", "가")], {"a": "KEEP_SEPARATE"}, [("a", "가")]
        )
        == {}
    )


def test_every_decision_carries_basis_evidence_and_signature(
    service_master: pd.DataFrame,
) -> None:
    decided = service_master[service_master["review_decision"].notna()]
    for row in decided.itertuples():
        assert row.decision_rule, f"{row.canonical_service_key}: decision_rule 이 없다"
        assert len(row.decision_basis) > 40, f"{row.canonical_service_key}: 근거가 너무 짧다"
        assert row.decision_confidence in {"HIGH", "MEDIUM", "LOW"}
        assert row.decided_at and row.decided_by
        evidence = json.loads(row.decision_evidence)
        assert evidence, f"{row.canonical_service_key}: 인용이 비었다"
        for item in evidence:
            assert item["layer"] in {"BODY_TEXT", "PUBLISHER_TAGS", "FIGURE_ROW", "ABSENCE"}
            assert item["quote"] and item["source"]


def test_decision_evidence_is_verified_against_the_source_itself(
    service_master: pd.DataFrame, rows: pd.DataFrame, authority: dict
) -> None:
    """**대조의 한쪽 끝이 A1 원문이다.** 인용이 원문에 없으면 판정은 무효다.

    산문 근거는 아무도 다시 확인하지 않는다. layer 별로 기계가 확인한다.
    """
    body = BODY_TEXT.read_text(encoding="utf-8")
    tags = set(authority["source"]["tags"])
    decided = service_master[service_master["review_decision"].notna()]

    checked = {"BODY_TEXT": 0, "PUBLISHER_TAGS": 0, "FIGURE_ROW": 0, "ABSENCE": 0}
    for row in decided.itertuples():
        for item in json.loads(row.decision_evidence):
            layer, quote, source = item["layer"], item["quote"], item["source"]
            where = f"{row.canonical_service_key}/{layer}"

            if layer == "BODY_TEXT":
                assert quote in body, f"{where}: 인용이 A1 본문에 없다 — {quote[:60]!r}"
            elif layer == "PUBLISHER_TAGS":
                assert quote in tags, f"{where}: 발행처 태그 목록에 없다 — {quote!r}"
            elif layer == "FIGURE_ROW":
                spec = dict(part.split("=", 1) for part in source.split(";"))
                sub = rows[
                    (rows["panel_id"] == spec["panel_id"]) & (rows["rank"] == int(spec["rank"]))
                ]
                assert not sub.empty, f"{where}: {source} 에 해당하는 원자료 행이 없다"
                assert set(sub["entity_name_raw"]) == {quote}, (
                    f"{where}: {source} 의 표기는 {set(sub['entity_name_raw'])} 인데 "
                    f"인용은 {quote!r} 다"
                )
            elif layer == "ABSENCE":
                for relpath in source.split(";"):
                    text = (RESEARCH / relpath).read_text(encoding="utf-8", errors="replace")
                    assert text.count(quote) == 0, (
                        f"{where}: {relpath} 에 {quote!r} 가 {text.count(quote)}회 있다 — "
                        "부재 주장이 거짓이다"
                    )
            checked[layer] += 1

    # 네 layer 가 전부 실제로 사용됐는지 확인한다 — 검사하지 않은 layer 를 통과로 세지 않는다.
    assert all(n > 0 for n in checked.values()), f"사용되지 않은 검증 layer 가 있다: {checked}"


def test_absence_claims_are_scoped_to_the_933_body_not_the_raw_payload(ledger: dict) -> None:
    """부재 검사의 범위 착오는 조용히 틀린다.

    서버 응답 원본(detail.json / api.json)에는 933 본문 외에 '관련 인사이트' 등 다른 기사
    본문이 함께 실려 있다. 실제로 'G마켓/옥션' 은 그 2파일에 4회 등장하지만 전부 다른 기사의
    문장이다. 범위를 파일 4개로 넓히면 gmarket 의 부재 주장이 거짓이 된다.
    """
    payload_files = ledger["absence_scope"]["raw_payload_layer"]
    assert payload_files
    for relpath in payload_files:
        text = (RESEARCH / relpath).read_text(encoding="utf-8", errors="replace")
        assert text.count("G마켓/옥션") > 0, (
            "전제가 바뀌었다 — raw payload 에 다른 기사 본문이 더는 실려 있지 않다면 "
            "absence_scope 경고문을 갱신해야 한다"
        )


def test_hyundai_merge_is_grounded_in_the_source_brand_count(
    service_master: pd.DataFrame, rows: pd.DataFrame
) -> None:
    """MERGE 는 큐에서 유일하게 entity 를 없애는 판정이다. 근거를 한 번 더 못 박는다."""
    merged = service_master[service_master["review_decision"] == "MERGE"]
    assert set(merged["canonical_service_key"]) == {"hyundai_homeshopping_hmall"}

    t1 = set(rows.loc[rows["panel_id"] == "fig10_t1", "entity_name_raw"])
    t2 = set(rows.loc[rows["panel_id"] == "fig10_t2", "entity_name_raw"])
    # 같은 그림의 두 패널이 5개씩이고, 한 라벨만 다르다.
    assert len(t1) == len(t2) == 5
    assert len(t1 & t2) == 4
    assert t1 - t2 == {"현대홈쇼핑/현대Hmall"}
    assert t2 - t1 == {"현대홈쇼핑/현대Hmallord"}
    # 별개 브랜드라면 fig10 의 브랜드는 6개가 되는데 원문은 5개라고 적었다.
    assert len(t1 | t2) == 6
    assert "주요 홈쇼핑 리테일 브랜드 5개는" in BODY_TEXT.read_text(encoding="utf-8"), (
        "원문의 '5개' 진술이 사라졌다면 MERGE 근거를 다시 세워야 한다"
    )

    # 원자료는 병합하지 않는다 — 두 표기가 261행에 그대로 남아 있어야 한다.
    assert (rows["entity_name_raw"] == "현대홈쇼핑/현대Hmallord").sum() == 1


def test_keep_separate_did_not_change_the_entity_count(service_master: pd.DataFrame) -> None:
    """판정은 기술이지 조작이 아니다. 판정 후에도 entity 수가 그대로여야 한다."""
    assert len(service_master) == 81
    keep = service_master[service_master["review_decision"] == "KEEP_SEPARATE"]
    assert len(keep) == 6
    # 여섯 건은 세 쌍이다 — 한쪽만 분리하고 다른 쪽을 잊는 일이 없어야 한다.
    pairs = [
        ("naver_app", "naver_naverpay"),
        ("gmarket_app", "gmarket_auction"),
        ("coupang_app", "coupang_retail"),
    ]
    keys = set(keep["canonical_service_key"])
    for a, b in pairs:
        assert a in keys and b in keys, f"{a}/{b} 중 한쪽만 판정됐다"


# ── W2: web_target_group 구조 정합 ──────────────────────────────────────────


def test_grouping_basis_is_machine_readable(web_target_group: pd.DataFrame) -> None:
    """산문 근거는 사후 조정을 눈치채기 어렵다. 구조를 고정한다."""
    assert len(web_target_group) == EXPECTED_GROUPS
    required = {"rule", "signal_kind", "shared_signal", "evidence_layer", "url_evidence", "note"}
    for row in web_target_group.itertuples():
        basis = json.loads(row.grouping_basis)
        assert required <= basis.keys(), f"{row.web_target_key}: grouping_basis 필드 누락"
        assert basis["url_evidence"] is None, "URL 증거가 없는데 채워졌다"
        assert basis["evidence_layer"] == "A1_SOURCE_LABEL"
        if row.grouping_status == "CANDIDATE_PENDING_URL_REVIEW":
            assert basis["rule"] == "SHARED_SOURCE_LABEL_SIGNAL"
            assert basis["shared_signal"], "후보인데 공유 신호가 비었다"
        else:
            assert basis["rule"] == "NO_SHARED_SOURCE_LABEL_SIGNAL"
            assert basis["shared_signal"] is None


def test_expected_url_relationship_is_declared_as_a_hypothesis(
    web_target_group: pd.DataFrame,
) -> None:
    """URL 을 보기 전에 기대를 적되, 그것이 확정이 아님을 필드로 드러낸다."""
    assert set(web_target_group["expected_url_relationship"]) <= ALLOWED_RELATIONSHIP
    assert not web_target_group["expected_url_relationship_confirmed_by_url"].any()
    assert web_target_group["web_target_url"].isna().all()
    assert web_target_group["url_evidence"].isna().all()

    cand = web_target_group[web_target_group["grouping_status"] == "CANDIDATE_PENDING_URL_REVIEW"]
    assert set(cand["web_target_key"]) == {"coupang", "naver", "gmarket"}
    assert (cand["expected_url_relationship"] == "SAME_LANDING_EXPECTED").all()
    assert cand["expected_url_relationship_is_hypothesis"].all()
    for row in cand.itertuples():
        assert len(row.expected_url_relationship_basis) > 40
        assert row.expected_url_relationship_falsifier, "반증 조건이 없는 가설은 가설이 아니다"
        assert row.expected_url_relationship_risk
        # 06 §3-2: 추측 URL 생성 금지. 반증 조건에 URL 을 적지 않는다.
        text = row.expected_url_relationship_falsifier + row.expected_url_relationship_basis
        for token in ("http://", "https://", "www.", ".com", ".co.kr", ".kr/"):
            assert token not in text, f"{row.web_target_key}: 추측 URL 이 섞였다 ({token})"

    single = web_target_group[web_target_group["grouping_status"] == "SINGLETON_PENDING_URL_REVIEW"]
    assert len(single) == 65
    assert (single["expected_url_relationship"] == "UNKNOWN").all()
    assert not single["expected_url_relationship_is_hypothesis"].any()


def test_every_brand_entity_belongs_to_exactly_one_group(
    web_target_group: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """W2-4: service_master ↔ web_target_group 정합 불변식."""
    brands = service_master[service_master["axis_type"] == "SERVICE_BRAND"]
    industry = service_master[service_master["axis_type"] == "INDUSTRY_CATEGORY"]
    assert len(industry) == 10

    membership: dict[str, list[str]] = {}
    for row in web_target_group.itertuples():
        for sid_ in row.member_service_ids.split(","):
            membership.setdefault(sid_, []).append(row.web_target_group_id)

    assert all(len(v) == 1 for v in membership.values()), "두 그룹에 동시에 속한 service_id 가 있다"
    assert set(membership) == set(brands["service_id"])
    assert int(web_target_group["member_count"].sum()) == len(brands) == 71

    # 업종 축은 그룹 층에 존재하지 않는다 — 컬럼도 비어 있고 member 로도 등장하지 않는다.
    assert industry["web_target_group_id"].isna().all()
    assert industry["web_target_key"].isna().all()
    assert industry["web_target_grouping_status"].isna().all()
    assert not (set(industry["service_id"]) & set(membership))

    # service_master 쪽 그룹 id 와 그룹 표의 id 집합이 일치해야 한다.
    assert set(brands["web_target_group_id"]) == set(web_target_group["web_target_group_id"])


def test_member_review_decisions_are_positionally_aligned(
    web_target_group: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """C011 이 member_domains 에서 겪은 위치 어긋남을 새 배열에서 반복하지 않는다."""
    decision_of = dict(
        zip(service_master["service_id"], service_master["review_decision"], strict=True)
    )
    checked = 0
    for row in web_target_group.itertuples():
        ids = row.member_service_ids.split(",")
        decs = row.member_review_decisions.split(",")
        assert len(ids) == len(decs) == row.member_count
        for i, sid_ in enumerate(ids):
            expected = decision_of[sid_]
            expected = "NOT_IN_REVIEW_QUEUE" if pd.isna(expected) else expected
            assert decs[i] == expected, f"{row.web_target_group_id}[{i}]: 위치 어긋남"
            checked += 1
    assert checked == int(web_target_group["member_count"].sum())


def test_measurement_decision_does_not_propagate_to_the_web_target_axis(
    web_target_group: pd.DataFrame,
) -> None:
    """두 축은 독립이다.

    naver / gmarket 을 measurement 층에서 KEEP_SEPARATE 로 확정했다고 해서 web_target 층에서
    그룹이 해체되는 것이 아니다. '무엇을 쟀는가' 와 '어느 URL 을 여는가' 는 다른 질문이고,
    후자는 URL 증거가 나올 때까지 미확정이다. 여기서 그룹을 깨면 URL 없이 결론을 내린 것이다.
    """
    cand = web_target_group[web_target_group["grouping_status"] == "CANDIDATE_PENDING_URL_REVIEW"]
    assert len(cand) == 3
    for row in cand.itertuples():
        assert set(row.member_review_decisions.split(",")) == {"KEEP_SEPARATE"}
        assert row.member_count == 2
        assert row.expected_url_relationship == "SAME_LANDING_EXPECTED"


# ── D1: evidence manifest 계약 ──────────────────────────────────────────────


def test_run_without_a_manifest_is_invalid(tmp_path: Path) -> None:
    """manifest 없는 Run 은 유효하지 않다 — 문서가 아니라 코드가 막는다."""
    run_dir = tmp_path / "e001_run"
    (run_dir / "dom").mkdir(parents=True)
    (run_dir / "dom" / "a.html").write_text("<html></html>", encoding="utf-8")

    with pytest.raises(em.MissingRunManifestError):
        em.load_run_manifest(run_dir)
    with pytest.raises(em.MissingRunManifestError):
        em.verify_run(run_dir)


def test_manifest_detects_tampering_and_missing_files(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "dom").mkdir(parents=True)
    payload = b"<html>evidence</html>"
    (run_dir / "dom" / "a.html").write_bytes(payload)
    entry = em.ManifestEntry(
        observation_id="obs_0001",
        relpath="dom/a.html",
        sha256=hashlib.sha256(payload).hexdigest(),
        bytes=len(payload),
    )
    em.write_run_manifest(run_dir, [entry])

    ok = em.verify_run(run_dir)
    assert ok["status"] == "VERIFIED"
    assert ok["entries"] == 1 and ok["observations"] == 1
    assert ok["files_checked"] == 1
    assert ok["mode"] == em.MODE_FULL

    # V2-C008: raw 가 **있는** 상태에서 require_files=False 로 불러도 실제로는 전건을
    # 해시했다. 옛 구현은 여기서 STRUCTURE_ONLY_RAW_ABSENT 를 찍었고 이 테스트가 그 오라벨을
    # 사실로 고정하고 있었다 (v1 승계부채 verify-run-mislabels-mode-...).
    # mode 는 요청이 아니라 측정에서 유도된다.
    lenient = em.verify_run(run_dir, require_files=False)
    assert lenient["files_checked"] == 1
    assert lenient["mode"] == em.MODE_FULL
    assert lenient["status"] == "VERIFIED"
    assert lenient["require_files"] is False

    # 내용을 바꾸면 잡힌다.
    (run_dir / "dom" / "a.html").write_bytes(b"<html>tampered!!!!!!!</html>")
    bad = em.verify_run(run_dir)
    assert bad["status"] == "FAILED"
    assert bad["hash_mismatch"]

    # 파일을 지우면 잡힌다.
    (run_dir / "dom" / "a.html").unlink()
    gone = em.verify_run(run_dir)
    assert gone["status"] == "FAILED"
    assert gone["missing_files"] == ["dom/a.html"]

    # raw 가 정말로 없는 clone 이라야 STRUCTURE_ONLY 다 — 검사하지 않은 것을 통과로 세지 않는다.
    absent = em.verify_run(run_dir, require_files=False)
    assert absent["files_checked"] == 0
    assert absent["mode"] == em.MODE_STRUCTURE_ONLY
    assert absent["status"] == "MANIFEST_WELL_FORMED_FILES_NOT_CHECKED"


def _one_entry(payload: bytes, relpath: str, observation_id: str = "obs_1") -> em.ManifestEntry:
    return em.ManifestEntry(
        observation_id=observation_id,
        relpath=relpath,
        sha256=hashlib.sha256(payload).hexdigest(),
        bytes=len(payload),
    )


def test_partial_verification_is_labelled_partial_not_full(tmp_path: Path) -> None:
    """반쯤 검사한 Run 을 '전건 검증' 으로도 '아무것도 안 봤음' 으로도 라벨하지 않는다."""
    run_dir = tmp_path / "run"
    (run_dir / "dom").mkdir(parents=True)
    a, b = b"<html>a</html>", b"<html>b</html>"
    (run_dir / "dom" / "a.html").write_bytes(a)
    em.write_run_manifest(
        run_dir, [_one_entry(a, "dom/a.html", "o1"), _one_entry(b, "dom/b.html", "o2")]
    )

    report = em.verify_run(run_dir, require_files=False)
    assert report["files_checked"] == 1 and report["entries"] == 2
    assert report["mode"] == em.MODE_PARTIAL
    assert report["status"] == "MANIFEST_WELL_FORMED_FILES_NOT_CHECKED", (
        "하나라도 안 본 것이 있으면 VERIFIED 가 아니다"
    )


def test_symlinked_directory_component_cannot_smuggle_bytes_from_outside(
    tmp_path: Path,
) -> None:
    """반례 — relpath 문자열 규칙을 **한 글자도 위반하지 않고** Run 밖 바이트를 검증시킨다.

    v1 승계부채 `verify-run-mislabels-mode-and-symlink-bypasses-relpath-guard` 의 후반부.
    `dom` 을 Run 밖 디렉터리로 링크하면 `dom/a.html` 은 절대경로도 `..` 도 아니므로
    `load_run_manifest` 를 그대로 통과하고, 옛 `verify_run` 은 그 바깥 바이트를 해시해
    **VERIFIED** 를 돌려줬다.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    payload = b"<html>not-in-this-run</html>"
    (outside / "a.html").write_bytes(payload)

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "dom").symlink_to(outside, target_is_directory=True)
    em.write_run_manifest(run_dir, [_one_entry(payload, "dom/a.html")])

    # 문자열 계약은 통과한다 — 그래서 여기까지는 정상이다.
    assert em.load_run_manifest(run_dir)[0].relpath == "dom/a.html"

    report = em.verify_run(run_dir)
    assert report["status"] == "FAILED"
    assert report["symlink_escape"] and report["symlink_escape"][0]["relpath"] == "dom/a.html"
    # 해시하지 않았음을 확인한다 — 탈출 경로를 해시하면 그 바이트가 증거가 된다.
    assert report["files_checked"] == 0
    assert report["hash_mismatch"] == []


def test_symlink_pointing_inside_the_run_is_also_refused(tmp_path: Path) -> None:
    """지금 Run 안을 가리키는 링크도 거부한다 — realpath 검사만으로는 못 막는 경로다.

    `resolve()` 결과만 보면 이 링크는 합법이다. 그러나 그 링크가 다음 검증 전에 바깥을
    가리키도록 바뀌어도 검사는 계속 통과한다. 링크 자체를 evidence 층에 두지 않는다.
    """
    run_dir = tmp_path / "run"
    (run_dir / "real").mkdir(parents=True)
    payload = b"<html>inside</html>"
    (run_dir / "real" / "a.html").write_bytes(payload)
    (run_dir / "dom").symlink_to(run_dir / "real", target_is_directory=True)
    em.write_run_manifest(run_dir, [_one_entry(payload, "dom/a.html")])

    with pytest.raises(em.SymlinkEscapeError):
        em.resolve_entry_path(run_dir, "dom/a.html")
    assert em.verify_run(run_dir)["status"] == "FAILED"


def test_symlinked_leaf_file_is_refused(tmp_path: Path) -> None:
    """디렉터리 성분만이 아니라 마지막 성분(파일 자신)이 링크여도 거부한다."""
    outside = tmp_path / "outside"
    outside.mkdir()
    payload = b"<html>leaf</html>"
    (outside / "a.html").write_bytes(payload)

    run_dir = tmp_path / "run"
    (run_dir / "dom").mkdir(parents=True)
    (run_dir / "dom" / "a.html").symlink_to(outside / "a.html")
    em.write_run_manifest(run_dir, [_one_entry(payload, "dom/a.html")])

    report = em.verify_run(run_dir)
    assert report["status"] == "FAILED"
    assert report["symlink_escape"]


@pytest.mark.parametrize(
    "line",
    [
        '{"observation_id": "o1", "relpath": "dom/a.html", "bytes": 3}',  # sha256 누락
        '{"observation_id": "o1", "relpath": "/etc/passwd", "sha256": "'
        + "a" * 64
        + '", "bytes": 3}',
        '{"observation_id": "o1", "relpath": "dom/a.html", "sha256": "sha256:zz", "bytes": 3}',
        '{"observation_id": "o1", "relpath": "../x", "sha256": "' + "a" * 64 + '", "bytes": 3}',
    ],
)
def test_malformed_manifest_lines_are_rejected(tmp_path: Path, line: str) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    em.manifest_path(run_dir).write_text(line + "\n", encoding="utf-8")
    with pytest.raises(em.MalformedRunManifestError):
        em.load_run_manifest(run_dir)


def test_gitignore_excludes_raw_evidence_but_tracks_the_manifest() -> None:
    """제외는 유지하되 manifest 는 반드시 추적된다 — git 에게 직접 물어본다."""

    def ignored(relpath: str) -> bool:
        proc = subprocess.run(
            ["git", "-C", str(REPO), "check-ignore", "-q", "--no-index", relpath],
            capture_output=True,
        )
        assert proc.returncode in (0, 1), proc.stderr.decode()
        return proc.returncode == 0

    base = "research/landing_accessibility/evidence/e001_run"
    for excluded in ("dom/page.html", "ax/tree.json", "screen/shot.png", "probe/result.json"):
        assert ignored(f"{base}/{excluded}"), f"{excluded} 가 추적 대상이 됐다"
    assert not ignored(f"{base}/manifest.jsonl"), (
        "manifest 가 gitignore 에 걸린다 — 제외를 감당 가능하게 만드는 유일한 장치가 사라졌다"
    )


def test_evidence_exclusion_survives_deeper_and_relocated_run_layouts() -> None:
    """V2-C008 — 한 겹만 보던 검사를 깊이·위치 두 축으로 넓힌다.

    v1 승계부채 `gitignore-evidence-pattern-single-level-only`.
    옛 패턴 `evidence/*/dom/` 의 `*` 는 경로 구분자를 넘지 않아 `evidence/<run>/dom/` 딱
    한 겹만 걸렸다. 위 테스트가 정확히 그 한 겹만 확인했기 때문에 결함이 잡히지 않았다.
    00_SSOT §7 의 L0/L1 2계층 수집은 Run 안에 층을 하나 더 만들므로, 이것은 가정이 아니라
    곧 실현될 레이아웃에서 수백 MB 를 그대로 커밋시키는 결함이다.
    """
    research = "research/landing_accessibility"

    def ignored(relpath: str) -> bool:
        proc = subprocess.run(
            ["git", "-C", str(REPO), "check-ignore", "-q", "--no-index", relpath],
            capture_output=True,
        )
        assert proc.returncode in (0, 1), proc.stderr.decode()
        return proc.returncode == 0

    # ① 깊이 — Run 안이 한 겹 더 나뉘어도 제외된다.
    for deep in (
        f"{research}/evidence/e001_run/L0/dom/page.html",
        f"{research}/evidence/e001_run/pages/p1/screen/shot.png",
        f"{research}/evidence/e001_run/L1/task_a/probe/result.json",
    ):
        assert ignored(deep), f"깊은 중첩이 추적 대상이 됐다: {deep}"

    # ② 위치 — evidence 디렉터리가 .gitignore 바로 밑이 아니어도 제외된다.
    for moved in (
        f"{research}/runs/e001_run/evidence/dom/page.html",
        f"{research}/analysis/evidence/e001_run/ax/tree.json",
        f"{research}/engine/out/evidence/e001_run/probe/result.json",
    ):
        assert ignored(moved), f"위치가 옮겨진 evidence 가 추적 대상이 됐다: {moved}"

    # ③ manifest 는 어느 깊이·어느 위치에서도 추적된다 — 제외를 감당 가능하게 만드는 장치다.
    for manifest in (
        f"{research}/evidence/e001_run/manifest.jsonl",
        f"{research}/evidence/e001_run/L0/manifest.jsonl",
        f"{research}/analysis/evidence/e001_run/run_manifest.json",
    ):
        assert not ignored(manifest), f"manifest 가 제외됐다: {manifest}"

    # ④ 과잉 제외가 아님 — evidence 아래라도 네 디렉터리 밖은 추적된다.
    for kept in (
        f"{research}/evidence/e001_run/report.json",
        f"{research}/state/service_master.parquet",
    ):
        assert not ignored(kept), f"제외 범위가 넓어졌다: {kept}"


def test_evidence_directory_is_still_absent() -> None:
    """E001 본수집은 금지 상태다. 증거 디렉터리가 생겼다면 게이트를 건너뛴 것이다."""
    assert not (RESEARCH / "evidence").exists()


def test_evidence_manifest_contract_memo_exists() -> None:
    memo = RESEARCH / "docs" / "07_EVIDENCE_MANIFEST_CONTRACT.md"
    assert memo.exists(), "왜 raw 는 제외하고 manifest 는 추적하는지 적어 둔 근거가 없다"
    text = memo.read_text(encoding="utf-8")
    assert "manifest 없는 Run 은 유효하지 않다" in text


# ── D2: authority_manifest 판본 선언 ────────────────────────────────────────


def test_authority_manifest_declares_its_own_revision(authority: dict) -> None:
    report = am.verify(AUTHORITY)
    assert report["manifest_revision"] >= 4
    assert report["revisions_recorded"] == report["manifest_revision"]
    assert authority["revised_at"]

    # 판본별로 무엇이 왜 바뀌었는지 적혀 있어야 한다.
    for entry in authority["revision_log"]:
        assert entry["changes"], f"revision {entry['revision']}: 변경 내역이 비었다"
        assert entry["cycle"]


def test_manifest_self_hash_is_recomputable(authority: dict) -> None:
    """자기 해시가 자기 자신을 포함하면 고정점이 된다. 그 한 필드만 빼고 계산한다."""
    declared = authority[am.SELF_HASH_FIELD]
    assert declared.startswith("sha256:")
    assert am.compute_self_sha256(authority) == declared

    # 한 글자만 바꿔도 값이 달라져야 한다 — 해시가 실제로 내용을 덮고 있는지 확인.
    tampered = dict(authority)
    tampered["authority_id"] = authority["authority_id"] + "_x"
    assert am.compute_self_sha256(tampered) != declared


def test_source_revision_is_separate_from_manifest_revision(authority: dict) -> None:
    """**A1 원문 sha256 은 불변이다.** 매니페스트 판본이 올라가도 바뀌지 않는다.

    대조의 한쪽 끝은 raw 파일 자체다 — 매니페스트끼리 비교하지 않는다.
    """
    frozen = {
        "detail_json": "wiseapp933_detail.json",
        "rendered_html": "wiseapp933_rendered.html",
        "body_text": "wiseapp933_text.txt",
        "full_page_screenshot": "wiseapp933_full.png",
    }
    for key, filename in frozen.items():
        path = WISEAPP / "raw" / filename
        assert path.exists(), f"A1 동결본이 없다: {filename}"
        data = path.read_bytes()
        declared = authority["raw_assets"][key]
        assert declared["bytes"] == len(data)
        assert declared["sha256"] == "sha256:" + hashlib.sha256(data).hexdigest()

    assert all(e["raw_assets_unchanged"] for e in authority["revision_log"]), (
        "원문 판본이 바뀌었다면 그것은 revision 이 아니라 새 authority_id 다"
    )


# ── D3: 산출물에 절대경로를 적지 않는다 ─────────────────────────────────────


def test_journal_provenance_records_no_absolute_path() -> None:
    """C011 의 'diff -r 바이트 동일' 주장은 같은 워크트리에서만 참이었다."""
    provenance = json.loads((STATE / "journal_provenance.json").read_text(encoding="utf-8"))
    assert provenance["schema"] == "journal_provenance/v3"
    assert "journal_path" not in provenance, "절대경로 필드가 되살아났다"
    assert provenance["journal_path_in_repo"].startswith("research/landing_accessibility/")

    policy = provenance["path_policy"]
    assert policy["absolute_paths_recorded"] is False
    assert "journal_path" in policy["resolved_at_runtime"]


def test_no_state_artifact_embeds_a_machine_specific_path() -> None:
    """journal_provenance 만의 문제가 아니다. 산출물 전체를 훑는다.

    경로 의존은 C011 P2-3 에서 한 번 제거됐다가 형태만 바꿔 되살아났다. 필드 하나가 아니라
    '절대경로가 산출물에 들어가는 것' 자체를 막는다.
    """
    offenders: list[str] = []
    for path in sorted(STATE.rglob("*.json")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if '": "/' in stripped or "/home/" in stripped or "\\\\Users\\\\" in stripped:
                offenders.append(f"{path.relative_to(STATE)}:{line_no} {stripped[:90]}")
    assert not offenders, "산출물에 머신 의존 절대경로가 있다:\n" + "\n".join(offenders)
