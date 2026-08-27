"""W3 — KWCAG Stage 1 evaluator 검증.

`D-R0-51`(A ACCEPT)로 착수가 허가된 Stage 1(Applicability → Required evidence
slots → Expectation → Outcome)을 검증한다. Stage 0(manifest freeze) 검증은
`test_w3_manifest_freeze.py` 가 맡는다 — 여기서는 판정 로직만 본다.

REAL_TARGET 접속 없음 · gold label 생성/열람 없음. 아래 fixture 는 전부 이 파일
안에서 만든 **합성(synthetic) probe dict**다 — 실제 evidence 파일을 그대로 베낀
게 아니라, `probe.json`(`raw_features`) 이 실제로 갖는 필드 이름/자료형만 그대로
쓴 최소 재현이다. (별도로 `test_stage1_smoke_against_real_evidence_if_available`
하나만, 이 worktree 밖 다른 agent worktree 에 실제 evidence 가 있으면 읽어 스모크
테스트하고 없으면 스스로 skip 한다 — 이식성 때문에 필수 조건으로 걸지 않았다.)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.kwcag import stage1_evidence as sev  # noqa: E402
from landing_accessibility.engine.kwcag import stage1_pipeline as sp  # noqa: E402
from landing_accessibility.engine.kwcag.stage1_types import (  # noqa: E402
    EVALUATOR_VERSION,
    PHYSICAL_EVIDENCE_SLOT,
    ApplicabilityResult,
    ApplicabilityStatus,
    EvidenceRequiredError,
    EvidenceSlotResult,
    EvidenceSlotStatus,
    ExpectationResult,
    MeasurementFailureAsFailError,
    SubsetScopeError,
    UndeterminedLaunderingError,
)
from landing_accessibility.engine.vocabulary import VerdictState  # noqa: E402

OLDER_RELEVANT_IDS = sp.OLDER_RELEVANT_IDS
CODEBOOK_AUTOMATION_GRADE = sp.CODEBOOK_AUTOMATION_GRADE

DEC_IDS = {cid for cid, g in CODEBOOK_AUTOMATION_GRADE.items() if g == "AUTO_DECIDABLE"}
FLAG_IDS = {cid for cid, g in CODEBOOK_AUTOMATION_GRADE.items() if g == "AUTO_FLAG_ONLY"}
NOT_AUTO_IDS = {cid for cid, g in CODEBOOK_AUTOMATION_GRADE.items() if g == "NOT_AUTOMATABLE"}

IMPLEMENTED_EXPECTATION_IDS = {"1.4.2", "1.4.3", "2.1.3", "2.4.2", "3.3.2"}


def _empty_probe() -> dict:
    """모든 raw_features 키가 존재하되 전부 빈 값 — "관측했지만 아무것도 없었다"."""
    return {
        "collected_at": "2026-08-27T00:00:00Z",
        "probe_version": "test-fixture@0",
        "url": "https://example.invalid/",
        "raw_features": {
            "accessible_name_sources": [],
            "body_scroll_lock": {"locked": False},
            "contrast": [],
            "dismiss_control_candidates": [],
            "endpoint_signals": {},
            "gate_signals": {},
            "modal_overlay_candidates": [],
            "motion": {
                "animated_elements": [],
                "infinite_animation_count": 0,
                "marquee_count": 0,
                "autoplay_media": [],
                "prefers_reduced_motion_supported": True,
            },
            "primary_action_candidates": [],
            "region_signals": {"declared_regions": [], "search_inputs": []},
            "target_size": [],
            "viewport": {"title": "빈 페이지"},
        },
    }


def _probe_missing_schema_keys() -> dict:
    """`raw_features` 에 극히 일부 키만 있는, 구식/부분 probe — schema gap 재현."""
    return {
        "collected_at": "2026-08-27T00:00:00Z",
        "probe_version": "test-fixture@0",
        "url": "https://example.invalid/",
        "raw_features": {"viewport": {"title": "부분 probe"}},
    }


# ── 1) evidence slot 결측 → UNDETERMINED, 절대 FAIL 아님 ────────────────────────
class TestEvidenceMissingNeverBecomesFail:
    def test_schema_gap_criterion_is_undetermined(self):
        # 2.2.1(응답시간 조절)은 Stage1 registry에 evidence slot 매핑이 아예 없다.
        outcome = sp.evaluate_criterion("2.2.1", _empty_probe())
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert outcome.needs_semantic is True
        assert outcome.outcome != VerdictState.FAIL

    @pytest.mark.parametrize("criterion_id", sorted(OLDER_RELEVANT_IDS))
    def test_partial_probe_never_yields_fail_for_any_of_22(self, criterion_id):
        """raw_features 대부분이 빠진 probe 에서 22개 전부를 평가해도 FAIL 이 하나도
        나오면 안 된다 — 결측이 FAIL 로 둔갑하는 경로가 없다는 전수 검사."""
        outcome = sp.evaluate_criterion(criterion_id, _probe_missing_schema_keys())
        assert outcome.outcome != VerdictState.FAIL, (
            f"{criterion_id}: 결측투성이 probe 에서 FAIL 이 나왔다 — measurement failure "
            "가 FAIL 로 전이됐다는 신호"
        )

    def test_measurement_failure_as_fail_error_direct(self):
        """`_finalize` 를 직접 호출해 '결측인데 FAIL' 조합을 강제로 만들면 거부돼야
        한다 — 정상 경로에서는 도달하지 않는 상태를 방어선이 실제로 잡는지 본다."""
        appl = ApplicabilityResult(ApplicabilityStatus.APPLICABLE, "테스트로 강제")
        slot = EvidenceSlotResult(
            slot_names=("contrast",),
            physical_evidence_slot=PHYSICAL_EVIDENCE_SLOT,
            status=EvidenceSlotStatus.EMPTY,
            cap_hit=False,
            item_count=0,
            reason="테스트로 강제한 결측",
        )
        expect = ExpectationResult(VerdictState.FAIL, ({"forced": True},), "강제 FAIL")
        with pytest.raises(MeasurementFailureAsFailError):
            sp._finalize(
                "1.4.3", appl, slot, expect, codebook_grade="AUTO_DECIDABLE", evidence_ref_base={}
            )


# ── 2) UNDETERMINED 세탁 금지 ────────────────────────────────────────────────────
class TestUndeterminedLaunderingBlocked:
    def test_not_automatable_cannot_be_forced_to_pass(self):
        appl = ApplicabilityResult(ApplicabilityStatus.APPLICABLE, "강제")
        slot = EvidenceSlotResult(
            slot_names=(),
            physical_evidence_slot=PHYSICAL_EVIDENCE_SLOT,
            status=EvidenceSlotStatus.PRESENT,
            cap_hit=False,
            item_count=3,
            reason="강제",
        )
        expect = ExpectationResult(VerdictState.PASS, ({"x": 1},), "세탁 시도")
        with pytest.raises(UndeterminedLaunderingError):
            sp._finalize(
                "1.4.1", appl, slot, expect, codebook_grade="NOT_AUTOMATABLE", evidence_ref_base={}
            )

    def test_applicability_undetermined_cannot_be_forced_to_fail(self):
        appl = ApplicabilityResult(ApplicabilityStatus.UNDETERMINED, "schema gap 강제")
        slot = EvidenceSlotResult(
            slot_names=(),
            physical_evidence_slot=PHYSICAL_EVIDENCE_SLOT,
            status=EvidenceSlotStatus.ABSENT_FROM_PROBE_SCHEMA,
            cap_hit=False,
            item_count=None,
            reason="강제",
        )
        expect = ExpectationResult(VerdictState.FAIL, ({"x": 1},), "세탁 시도")
        with pytest.raises(UndeterminedLaunderingError):
            sp._finalize(
                "2.2.1", appl, slot, expect, codebook_grade="AUTO_DECIDABLE", evidence_ref_base={}
            )

    def test_flag_only_cannot_be_forced_to_a_verdict(self):
        appl = ApplicabilityResult(ApplicabilityStatus.APPLICABLE, "강제")
        slot = EvidenceSlotResult(
            slot_names=("motion",),
            physical_evidence_slot=PHYSICAL_EVIDENCE_SLOT,
            status=EvidenceSlotStatus.PRESENT,
            cap_hit=False,
            item_count=1,
            reason="강제",
        )
        expect = ExpectationResult(VerdictState.FAIL, ({"x": 1},), "세탁 시도")
        with pytest.raises(UndeterminedLaunderingError):
            sp._finalize(
                "2.2.2", appl, slot, expect, codebook_grade="AUTO_FLAG_ONLY", evidence_ref_base={}
            )

    def test_not_applicable_cannot_carry_a_candidate_verdict(self):
        appl = ApplicabilityResult(ApplicabilityStatus.NOT_APPLICABLE, "강제")
        slot = EvidenceSlotResult(
            slot_names=("contrast",),
            physical_evidence_slot=PHYSICAL_EVIDENCE_SLOT,
            status=EvidenceSlotStatus.EMPTY,
            cap_hit=False,
            item_count=0,
            reason="강제",
        )
        expect = ExpectationResult(VerdictState.PASS, ({"x": 1},), "세탁 시도")
        with pytest.raises(UndeterminedLaunderingError):
            sp._finalize(
                "1.4.3", appl, slot, expect, codebook_grade="AUTO_DECIDABLE", evidence_ref_base={}
            )


# ── 3) applicability=False → NA, 절대 PASS 아님 ──────────────────────────────────
class TestNotApplicableIsNaNeverPass:
    def test_empty_candidates_yield_na_not_pass(self):
        probe = _empty_probe()  # motion.autoplay_media == [] → 1.4.2 적용기회 없음
        outcome = sp.evaluate_criterion("1.4.2", probe)
        assert outcome.outcome == VerdictState.NA
        assert outcome.outcome != VerdictState.PASS

    @pytest.mark.parametrize("criterion_id", sorted(IMPLEMENTED_EXPECTATION_IDS - {"2.4.2"}))
    def test_all_implemented_dec_criteria_go_na_on_empty_probe(self, criterion_id):
        # 2.4.2(제목 제공)는 페이지 단위 보편 기준이라 후보가 항상 1개 — 제외.
        outcome = sp.evaluate_criterion(criterion_id, _empty_probe())
        assert outcome.outcome == VerdictState.NA
        assert outcome.outcome not in (VerdictState.PASS, VerdictState.FAIL)


# ── 4) 모든 PASS/FAIL 결과에 evidence_ref·evaluator_version 이 붙어 있다 ─────────────
class TestPassFailCarryEvidenceAndVersion:
    def test_real_shaped_probe_produces_pass_and_fail_with_evidence(self):
        probe = _empty_probe()
        # 1.4.3: 기준 미달 항목 하나 추가 → FAIL 기대. bg_resolved=True·fg_alpha=1·
        # font_px=14(작은 폰트지만 TINY_GLYPH_MAX_PX=2 보다 크다)로 "측정 불가" 배제
        # 조건에 안 걸리게 만든다 — 진짜 FAIL 로 판정돼야 하는 항목이다.
        probe["raw_features"]["contrast"] = [
            {
                "text": "회색 위 회색",
                "selector": "div.low",
                "bg_resolved": True,
                "behind_image": False,
                "fg_alpha": 1,
                "contrast_ratio": 1.2,
                "font_px": 14,
                "font_weight": 400,
            }
        ]
        # 2.1.3: 대각선 6mm(≈22.68px) 이상인 타깃 → PASS 기대.
        probe["raw_features"]["target_size"] = [
            {
                "selector": "a.big",
                "tag": "a",
                "role": None,
                "width_css_px": 40.0,
                "height_css_px": 40.0,
                "min_side_css_px": 40.0,
                "nearest_neighbor_gap_css_px": 10.0,
            }
        ]

        fail_outcome = sp.evaluate_criterion("1.4.3", probe, evidence_ref={"probe_path": "x"})
        assert fail_outcome.outcome == VerdictState.FAIL
        assert fail_outcome.evidence_ref, "FAIL 인데 evidence_ref 가 비었다"
        assert fail_outcome.evidence_ref["physical_evidence_slot"] == "probe"
        assert fail_outcome.evaluator_version == EVALUATOR_VERSION

        pass_outcome = sp.evaluate_criterion("2.1.3", probe, evidence_ref={"probe_path": "x"})
        assert pass_outcome.outcome == VerdictState.PASS
        assert pass_outcome.evidence_ref
        assert pass_outcome.evaluator_version == EVALUATOR_VERSION

    def test_evidence_required_error_direct(self):
        """candidate_verdict 는 있는데 matched_items 가 비어있으면(있을 수 없는 조합을
        강제로 만들면) 거부돼야 한다."""
        appl = ApplicabilityResult(ApplicabilityStatus.APPLICABLE, "강제")
        slot = EvidenceSlotResult(
            slot_names=("contrast",),
            physical_evidence_slot=PHYSICAL_EVIDENCE_SLOT,
            status=EvidenceSlotStatus.PRESENT,
            cap_hit=False,
            item_count=1,
            reason="강제",
        )
        expect = ExpectationResult(VerdictState.FAIL, (), "matched_items 없이 FAIL 강제")
        with pytest.raises(EvidenceRequiredError):
            sp._finalize(
                "1.4.3", appl, slot, expect, codebook_grade="AUTO_DECIDABLE", evidence_ref_base={}
            )


# ── D-R0-13/52 — subset 경계 ─────────────────────────────────────────────────────
class TestSubsetScopeEnforced:
    def test_other_domain_criterion_rejected(self):
        # 1.1.1 은 manifest 상 applicability == OTHER — Stage1 대상 밖.
        assert sev._MANIFEST_BY_ID["1.1.1"]["applicability"] == "OTHER"
        with pytest.raises(SubsetScopeError):
            sp.evaluate_criterion("1.1.1", _empty_probe())

    def test_unknown_criterion_id_rejected(self):
        with pytest.raises(SubsetScopeError):
            sp.evaluate_criterion("9.9.9", _empty_probe())

    def test_older_relevant_ids_match_manifest_exactly(self):
        manifest_older_relevant = {
            row["criterion_id"]
            for row in sev._MANIFEST["criteria"]
            if row["applicability"] != "OTHER"
        }
        assert manifest_older_relevant == OLDER_RELEVANT_IDS
        assert len(OLDER_RELEVANT_IDS) == 22


# ── D-R0-52 DecisionCoverage 사전등록 — 구조적 상한/하한 ─────────────────────────────
class TestDecisionCoverageStructuralBounds:
    def test_automation_grade_partition_matches_directors_numbers(self):
        assert len(DEC_IDS) == 9
        assert len(FLAG_IDS) == 6
        assert len(NOT_AUTO_IDS) == 7
        assert DEC_IDS | FLAG_IDS | NOT_AUTO_IDS == OLDER_RELEVANT_IDS

    @pytest.mark.parametrize("criterion_id", sorted(FLAG_IDS))
    def test_flag_only_never_decides_pass_fail_across_probe_shapes(self, criterion_id):
        """DECISION-1 — FLAG 는 분자에 포함하지 않는다. 후보 신호가 있어도(evidence
        가 풍부해도) 최종 outcome 은 PASS/FAIL 이 될 수 없다."""
        rich_probe = _empty_probe()
        rich_probe["raw_features"]["motion"]["infinite_animation_count"] = 3
        rich_probe["raw_features"]["motion"]["marquee_count"] = 1
        rich_probe["raw_features"]["accessible_name_sources"] = [
            {
                "tag": "a",
                "aria_label": None,
                "aria_labelledby": None,
                "title": None,
                "labelled_by_for": False,
                "visible_text": None,
            }
        ]
        rich_probe["raw_features"]["gate_signals"]["password_input_count"] = 2
        outcome = sp.evaluate_criterion(criterion_id, rich_probe)
        assert outcome.outcome not in (VerdictState.PASS, VerdictState.FAIL)
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert outcome.needs_semantic is True

    @pytest.mark.parametrize("criterion_id", sorted(NOT_AUTO_IDS))
    def test_not_automatable_never_decides_regardless_of_probe(self, criterion_id):
        for probe in (_empty_probe(), _probe_missing_schema_keys()):
            outcome = sp.evaluate_criterion(criterion_id, probe)
            assert outcome.outcome == VerdictState.UNDETERMINED
            assert outcome.needs_semantic is True

    def test_max_possible_decision_coverage_numerator_is_9_of_22(self):
        """AUTO_DECIDABLE 9개가 DecisionCoverage 분자의 구조적 상한이다
        (`9/22 ≈ 0.409`). Stage 1 이 실제로 Expectation 을 구현한 건 5개뿐이라
        **실측 상한은 이보다 더 낮다** — 그 격차 자체가 이 커밋의 한계이지 버그가 아니다."""
        assert len(DEC_IDS) == 9
        assert IMPLEMENTED_EXPECTATION_IDS <= DEC_IDS
        assert len(IMPLEMENTED_EXPECTATION_IDS) == 5


# ── cap_hit(D-R0-53) — PASS 만 하향, FAIL 은 그대로 ───────────────────────────────
class TestCapHitAsymmetricDowngrade:
    def _capped_target_size_probe(self, *, make_one_fail: bool) -> dict:
        probe = _empty_probe()
        items = []
        for i in range(300):  # PROBE_SLOT_CAPS["target_size"] == 300
            items.append(
                {
                    "selector": f"a:nth-of-type({i})",
                    "tag": "a",
                    "role": None,
                    "width_css_px": 40.0,
                    "height_css_px": 40.0,
                    "min_side_css_px": 40.0,
                    "nearest_neighbor_gap_css_px": 10.0,
                }
            )
        if make_one_fail:
            items[0] = {
                **items[0],
                "width_css_px": 5.0,
                "height_css_px": 5.0,
                "min_side_css_px": 5.0,
            }
        probe["raw_features"]["target_size"] = items
        return probe

    def test_cap_hit_pass_is_downgraded_to_undetermined(self):
        probe = self._capped_target_size_probe(make_one_fail=False)
        outcome = sp.evaluate_criterion("2.1.3", probe)
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert "cap_hit" in outcome.reason.lower() or "cap" in outcome.reason
        assert outcome.outcome != VerdictState.PASS

    def test_cap_hit_fail_stays_fail(self):
        probe = self._capped_target_size_probe(make_one_fail=True)
        outcome = sp.evaluate_criterion("2.1.3", probe)
        assert outcome.outcome == VerdictState.FAIL
        assert outcome.evidence_ref.get("cap_hit") is True

    def test_below_cap_pass_is_not_downgraded(self):
        probe = _empty_probe()
        probe["raw_features"]["target_size"] = [
            {
                "selector": "a:nth-of-type(1)",
                "tag": "a",
                "role": None,
                "width_css_px": 40.0,
                "height_css_px": 40.0,
                "min_side_css_px": 40.0,
                "nearest_neighbor_gap_css_px": 10.0,
            }
        ]
        outcome = sp.evaluate_criterion("2.1.3", probe)
        assert outcome.outcome == VerdictState.PASS


# ── service-level 결과를 criterion row 로 복제하지 않는다(D-R0-23) ──────────────────
class TestNoServiceLevelDuplication:
    def test_evaluate_all_returns_22_distinct_criteria(self):
        probe = _empty_probe()
        outcomes = sp.evaluate_older_relevant_subset(probe, evidence_ref={"probe_path": "x"})
        assert len(outcomes) == 22
        assert {o.criterion_id for o in outcomes.values()} == OLDER_RELEVANT_IDS
        # 서로 다른 criterion 이 통째로 같은 outcome 객체(같은 reason)를 복제해 들고
        # 있으면 안 된다 — 최소한 reason 문자열 집합이 22개보다 훨씬 적게 뭉치지 않는지 본다.
        reasons = {o.reason for o in outcomes.values()}
        assert len(reasons) >= 4, "22개 criterion 의 reason 이 지나치게 적은 값으로 뭉쳐 있다"

    def test_each_outcome_stamped_with_its_own_criterion_id(self):
        probe = _empty_probe()
        outcomes = sp.evaluate_older_relevant_subset(probe)
        for cid, outcome in outcomes.items():
            assert outcome.criterion_id == cid


# ── evaluator_version / physical_evidence_slot 이 전 outcome 에 일관되게 붙는다 ──────
class TestEvaluatorVersionAndPhysicalSlotAlwaysPresent:
    @pytest.mark.parametrize("criterion_id", sorted(OLDER_RELEVANT_IDS))
    def test_every_outcome_has_version_and_slot(self, criterion_id):
        outcome = sp.evaluate_criterion(criterion_id, _empty_probe())
        assert outcome.evaluator_version == EVALUATOR_VERSION
        assert outcome.evidence_ref.get("physical_evidence_slot") == "probe"


# ── T-A-W3-SCHEMA-001 요구#3 — 2.4.2 존재≠적절성(D-R0-70) ───────────────────────────
class TestTitleExistenceDoesNotEqualPass:
    def test_title_present_is_undetermined_needs_semantic_not_pass(self):
        """존재만으로 PASS 를 주지 않는다 — `D-R0-70`, 이 세션의 4번째 '존재≠작동' 사례."""
        probe = _empty_probe()
        probe["raw_features"]["viewport"]["title"] = "정상적으로 보이는 제목"
        outcome = sp.evaluate_criterion("2.4.2", probe)
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert outcome.outcome != VerdictState.PASS
        assert outcome.needs_semantic is True

    def test_title_missing_is_still_deterministic_fail(self):
        """부재는 모호하지 않다 — 결정적으로 FAIL 이다(존재≠작동의 반대쪽은 그대로 결정적)."""
        probe = _empty_probe()
        probe["raw_features"]["viewport"]["title"] = ""
        outcome = sp.evaluate_criterion("2.4.2", probe)
        assert outcome.outcome == VerdictState.FAIL
        assert outcome.needs_semantic is False
        assert outcome.evidence_ref

    def test_title_whitespace_only_is_also_fail(self):
        probe = _empty_probe()
        probe["raw_features"]["viewport"]["title"] = "   "
        outcome = sp.evaluate_criterion("2.4.2", probe)
        assert outcome.outcome == VerdictState.FAIL


# ── T-A-W3-SCHEMA-001 요구#2 — 1.4.3 측정불가(alpha0/1px/bg미해결) vs 실제 실패 구분 ──────
class TestContrastMeasurementInconclusiveNeverCountsAsRealVerdict:
    def _contrast_item(self, **overrides) -> dict:
        base = {
            "text": "표본",
            "selector": "div.x",
            "bg_resolved": True,
            "behind_image": False,
            "fg_alpha": 1,
            "contrast_ratio": 1.2,
            "font_px": 14,
            "font_weight": 400,
        }
        return {**base, **overrides}

    def test_alpha0_item_alone_is_undetermined_not_fail(self):
        """alpha0(전경 투명) 단독 항목 — ratio=1.2(기준 미달처럼 보이는 값)라도 FAIL 로
        세면 안 된다. 색 자체를 신뢰 못하기 때문이다."""
        probe = _empty_probe()
        probe["raw_features"]["contrast"] = [self._contrast_item(fg_alpha=0)]
        outcome = sp.evaluate_criterion("1.4.3", probe)
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert outcome.outcome != VerdictState.FAIL
        assert outcome.needs_semantic is True

    def test_tiny_font_item_alone_is_undetermined_not_fail(self):
        """1px 짜리 '텍스트'(아이콘 글리프/장식 배지 추정) — FAIL 로 세면 안 된다."""
        probe = _empty_probe()
        probe["raw_features"]["contrast"] = [self._contrast_item(font_px=1)]
        outcome = sp.evaluate_criterion("1.4.3", probe)
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert outcome.outcome != VerdictState.FAIL

    def test_near_identical_ratio_item_alone_is_undetermined_not_fail(self):
        """전경·배경 동색 산출(ratio<=1.05) — 계산 신뢰 불가, FAIL 로 세면 안 된다."""
        probe = _empty_probe()
        probe["raw_features"]["contrast"] = [self._contrast_item(contrast_ratio=1.0)]
        outcome = sp.evaluate_criterion("1.4.3", probe)
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert outcome.outcome != VerdictState.FAIL

    def test_real_fail_still_stands_alongside_inconclusive_items(self):
        """측정불가 항목과 진짜 결함 항목이 섞여 있으면, 측정불가는 세지 않되 진짜
        결함은 그대로 FAIL 로 반영돼야 한다 — 측정불가가 실제 실패를 가리면 안 된다."""
        probe = _empty_probe()
        probe["raw_features"]["contrast"] = [
            self._contrast_item(fg_alpha=0, selector="div.inconclusive"),
            self._contrast_item(contrast_ratio=1.2, selector="div.real-fail"),
        ]
        outcome = sp.evaluate_criterion("1.4.3", probe)
        assert outcome.outcome == VerdictState.FAIL
        item_verdicts = {
            it.get("selector"): it.get("item_verdict")
            for it in outcome.stage_trace["expectation"].matched_items
        }
        assert item_verdicts["div.inconclusive"] == "MEASUREMENT_INCONCLUSIVE"
        assert item_verdicts["div.real-fail"] == "FAIL"

    def test_all_inconclusive_probe_is_undetermined_with_evidence_preserved(self):
        probe = _empty_probe()
        probe["raw_features"]["contrast"] = [
            self._contrast_item(fg_alpha=0),
            self._contrast_item(font_px=1),
        ]
        outcome = sp.evaluate_criterion("1.4.3", probe)
        assert outcome.outcome == VerdictState.UNDETERMINED
        # stage_trace 에 두 항목 모두 MEASUREMENT_INCONCLUSIVE 로 보존돼 있어야 한다(기록 요구).
        matched = outcome.stage_trace["expectation"].matched_items
        assert len(matched) == 2
        assert all(m["item_verdict"] == "MEASUREMENT_INCONCLUSIVE" for m in matched)


# ── T-A-W3-SCHEMA-001 요구#1 — schema gap 4건 개별 재심사 결과 회귀 방지 ─────────────────
class TestSchemaGapReassessment:
    @pytest.mark.parametrize("criterion_id", ["2.2.1", "2.5.4"])
    def test_truly_absent_signals_stay_absent_even_with_rich_probe(self, criterion_id):
        """2.2.1/2.5.4 는 probe 스키마 자체에 대응 신호가 없다 — 아무리 다른 필드를
        채워도 UNDETERMINED(schema gap)여야 한다."""
        probe = _empty_probe()
        probe["raw_features"]["motion"]["infinite_animation_count"] = 5
        probe["raw_features"]["gate_signals"]["password_input_count"] = 3
        outcome = sp.evaluate_criterion(criterion_id, probe)
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert outcome.needs_semantic is True

    def test_2_4_1_does_not_use_declared_regions_even_when_present(self):
        """`region_signals.declared_regions` 가 실제로 채워져 있어도(합성 fixture 마커
        신호) 2.4.1 은 그것을 쓰지 않는다 — 의도적 미배선(근거는 stage1_evidence.py
        모듈 docstring)."""
        probe = _empty_probe()
        probe["raw_features"]["region_signals"]["declared_regions"] = [
            {"selector": "nav#skip", "region": "main", "present": True}
        ]
        outcome = sp.evaluate_criterion("2.4.1", probe)
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert outcome.stage_trace["evidence_slot"].status.value == "ABSENT_FROM_PROBE_SCHEMA"

    def test_3_3_4_evidence_slot_now_shows_real_signal_but_outcome_stays_undetermined(self):
        """3.3.4 매핑 누락을 고쳤으므로 evidence_slot 은 이제 실제 신호를 보여줘야
        한다 — 그러나 Applicability/Outcome 은 여전히 UNDETERMINED 다(구조적 비대칭)."""
        probe = _empty_probe()
        probe["raw_features"]["gate_signals"]["username_autocomplete_count"] = 2

        outcome = sp.evaluate_criterion("3.3.4", probe)
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert outcome.outcome not in (VerdictState.PASS, VerdictState.FAIL, VerdictState.NA)
        assert outcome.needs_semantic is True
        # Applicability 이유에 "판정에는 쓰지 않았다"는 문구가 남아 투명성은 있되 결정에는
        # 반영 안 됐음을 보여줘야 한다.
        assert "판정에는 쓰지 않았다" in outcome.stage_trace["applicability"].reason

        evidence_slot = sev.required_evidence_slots("3.3.4", probe)
        assert evidence_slot.status.value != "ABSENT_FROM_PROBE_SCHEMA", (
            "매핑을 고쳤는데도 evidence_slot 이 여전히 ABSENT 로 나온다 — 배선 실패"
        )
        assert evidence_slot.item_count == 1

    def test_3_3_4_zero_signal_also_stays_undetermined_not_na(self):
        """count==0 이 '적용기회 없음'(NA)으로 조용히 바뀌면 안 된다 — 그것도 이 신호가
        구분 못하는 경우다."""
        outcome = sp.evaluate_criterion("3.3.4", _empty_probe())
        assert outcome.outcome == VerdictState.UNDETERMINED
        assert outcome.outcome != VerdictState.NA


# ── (선택) 실제 evidence 스모크 — 다른 agent worktree 에 있으면만 돈다 ───────────────
def _find_one_real_probe() -> Path | None:
    candidates = REPO.parent.glob("claude_b_e001_worker_*/artifacts/*/evidence/*/*/l0a/probe.json")
    return next(candidates, None)


def test_stage1_smoke_against_real_evidence_if_available():
    probe_path = _find_one_real_probe()
    if probe_path is None:
        pytest.skip("이 worktree 밖 real L0 evidence 를 찾지 못했다 — 이식성 위해 skip")
    import json

    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    outcomes = sp.evaluate_older_relevant_subset(
        probe, evidence_ref={"probe_path": str(probe_path)}
    )
    assert len(outcomes) == 22
    for cid, outcome in outcomes.items():
        if CODEBOOK_AUTOMATION_GRADE[cid] in ("AUTO_FLAG_ONLY", "NOT_AUTOMATABLE"):
            assert outcome.outcome not in (VerdictState.PASS, VerdictState.FAIL)
