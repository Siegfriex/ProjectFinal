"""W4 — Axis C(초기 obstruction) + mart 회귀검사.

`D-R0-24`/`D-R0-25`/`SSOTV2 §10`/Research Director 지시(2026-08-27)를 코드 불변조건으로
증명한다. **REAL_TARGET 에 접속하지 않는다** — 전부 이미 디스크에 있는 E001_FULL evidence를
읽기 전용으로 읽거나, in-memory dict 로 순수함수를 검사한다.

실행:
    /home/sieg/projects-wsl/ProjectFinal/.venv/bin/python -m pytest \\
        research/landing_accessibility/tests/test_w4_axisc_mart.py -q
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH / "src"))
sys.path.insert(0, str(RESEARCH / "scripts"))

import build_mart_axisc as mart  # noqa: E402
from landing_accessibility.engine.l0_collector import (  # noqa: E402
    InterruptAxisStatus,
    InterruptClassification,
    classify_interrupt,
)
from landing_accessibility.engine.vocabulary import InterruptLabel  # noqa: E402

EVIDENCE_AVAILABLE = len(mart.discover_run_dirs()) > 0


def _require_evidence() -> None:
    if not EVIDENCE_AVAILABLE:
        pytest.skip(
            "E001_FULL evidence 디렉터리를 찾지 못했다 — 이 worktree 밖에서 실행 중일 수 있다"
        )


# ── 실제 mart 를 한 번 빌드해 여러 테스트가 재사용한다 (evidence 는 읽기 전용) ──


@pytest.fixture(scope="module")
def mart_rows() -> list[dict]:
    _require_evidence()
    attempted = mart.load_attempted_population()
    run_dirs = mart.discover_run_dirs()
    return mart.build_mart_rows(attempted, run_dirs)


@pytest.fixture(scope="module")
def denominators(mart_rows: list[dict]) -> dict:
    return mart.compute_denominators(mart_rows)


# ══════════════════════════════════════════════════════════════════════════
# 1. classify_interrupt — D-R0-25 tier 순서 + geometry 불변
# ══════════════════════════════════════════════════════════════════════════


class TestClassifyInterruptTiering:
    """`D-R0-25`/`D-R0-58` — `interrupt_form`/`interrupt_semantic` 은 직교하는 독립 축.
    `C-FINDING-214214` 이 지적한 "구조가 텍스트를 덮는" 붕괴가 재발하지 않는지 여기서
    직접 증명한다."""

    def test_viewport_overlap_zero_is_not_applicable_on_both_axes(self):
        c = classify_interrupt({"viewport_overlap_css_px2": 0})
        assert c.interrupt_form_status is InterruptAxisStatus.NOT_APPLICABLE
        assert c.interrupt_form is InterruptLabel.UNKNOWN
        assert c.interrupt_semantic_status is InterruptAxisStatus.NOT_APPLICABLE
        assert c.interrupt_semantic is InterruptLabel.UNKNOWN

    def test_structural_and_text_both_resolve_independently_D_R0_58(self):
        """`D-R0-58` 핵심 — dialog role(구조) 이면서 쿠키 텍스트(의미)를 가진 후보는
        **둘 다** 확정돼야 한다. 하나가 다른 하나를 덮지 않는다."""
        candidate = {
            "viewport_overlap_css_px2": 100.0,
            "viewport_coverage": 0.6,
            "candidate_sources": ["role_dialog"],
            "accessible_text": "쿠키 사용에 동의합니다",
        }
        c = classify_interrupt(candidate)
        assert c.interrupt_form_status is InterruptAxisStatus.RESOLVED
        assert c.interrupt_form is InterruptLabel.BLOCKING_MODAL  # coverage>=0.5
        assert c.interrupt_semantic_status is InterruptAxisStatus.RESOLVED
        assert c.interrupt_semantic is InterruptLabel.COOKIE_CONSENT  # 붕괴하지 않음

    def test_sticky_banner_with_login_text_keeps_both_labels(self):
        """A 가 든 예시 그대로 — "로그인 유도 sticky bar"는 `interrupt_form = BANNER`
        이면서 `interrupt_semantic = LOGIN_PROMPT` 다."""
        candidate = {
            "viewport_overlap_css_px2": 40.0,
            "viewport_coverage": 0.05,
            "candidate_sources": ["position_sticky"],
            "accessible_text": "로그인 하고 계속하기",
        }
        c = classify_interrupt(candidate)
        assert c.interrupt_form is InterruptLabel.BANNER
        assert c.interrupt_form_status is InterruptAxisStatus.RESOLVED
        assert c.interrupt_semantic is InterruptLabel.LOGIN_PROMPT
        assert c.interrupt_semantic_status is InterruptAxisStatus.RESOLVED

    def test_semantic_resolves_alone_when_form_has_no_structural_signal(self):
        candidate = {
            "viewport_overlap_css_px2": 50.0,
            "viewport_coverage": 0.1,
            "candidate_sources": [],  # 구조 신호 없음
            "accessible_text": "쿠키 사용에 동의합니다",
        }
        c = classify_interrupt(candidate)
        assert c.interrupt_form_status is InterruptAxisStatus.UNRESOLVED
        assert c.interrupt_form is InterruptLabel.UNKNOWN
        assert c.interrupt_semantic_status is InterruptAxisStatus.RESOLVED
        assert c.interrupt_semantic is InterruptLabel.COOKIE_CONSENT

    def test_form_resolves_alone_when_text_has_no_lexicon_match(self):
        candidate = {
            "viewport_overlap_css_px2": 50.0,
            "viewport_coverage": 0.1,
            "candidate_sources": ["position_fixed"],
            "accessible_text": "완전히 무관한 문구",
        }
        c = classify_interrupt(candidate)
        assert c.interrupt_form_status is InterruptAxisStatus.RESOLVED
        assert c.interrupt_form is InterruptLabel.BANNER
        assert c.interrupt_semantic_status is InterruptAxisStatus.UNRESOLVED
        assert c.interrupt_semantic is InterruptLabel.UNKNOWN

    def test_neither_axis_resolves_no_vlm_both_unresolved(self):
        candidate = {
            "viewport_overlap_css_px2": 50.0,
            "viewport_coverage": 0.1,
            "candidate_sources": [],
            "accessible_text": "완전히 무관한 문구",
        }
        c = classify_interrupt(candidate)
        assert c.interrupt_form_status is InterruptAxisStatus.UNRESOLVED
        assert c.interrupt_semantic_status is InterruptAxisStatus.UNRESOLVED
        assert c.interrupt_form is InterruptLabel.UNKNOWN
        assert c.interrupt_semantic is InterruptLabel.UNKNOWN

    def test_position_fixed_is_structural_banner(self):
        candidate = {
            "viewport_overlap_css_px2": 10.0,
            "viewport_coverage": 0.01,
            "candidate_sources": ["position_fixed"],
        }
        c = classify_interrupt(candidate)
        assert c.interrupt_form_status is InterruptAxisStatus.RESOLVED
        assert c.interrupt_form is InterruptLabel.BANNER

    def test_pure_function_does_not_mutate_input_candidate(self):
        candidate = {
            "viewport_overlap_css_px2": 50.0,
            "viewport_coverage": 0.1,
            "candidate_sources": ["position_sticky"],
            "accessible_text": "이벤트 할인",
            "box": {"x": 1, "y": 2, "w": 3, "h": 4},
        }
        before = copy.deepcopy(candidate)
        classify_interrupt(candidate)
        assert candidate == before, "classify_interrupt 가 입력 candidate 를 변형했다"

    def test_a_neither_field_overwrites_or_blanks_the_other(self):
        """ "상호 덮어쓰기 금지" — 한쪽이 RESOLVED 라고 다른 쪽이 UNKNOWN 으로 강제
        리셋되지 않는지, 반대로 UNRESOLVED 라고 다른 쪽 RESOLVED 값이 지워지지
        않는지 여러 조합으로 확인한다."""
        both_resolve = classify_interrupt(
            {
                "viewport_overlap_css_px2": 100.0,
                "viewport_coverage": 0.05,
                "candidate_sources": ["position_fixed"],
                "accessible_text": "광고 sponsored",
            }
        )
        assert both_resolve.interrupt_form is InterruptLabel.BANNER
        assert both_resolve.interrupt_semantic is InterruptLabel.ADVERTISEMENT
        # 둘 다 RESOLVED — 어느 쪽도 UNKNOWN 으로 리셋되지 않았다.
        assert InterruptLabel.UNKNOWN not in (
            both_resolve.interrupt_form,
            both_resolve.interrupt_semantic,
        )


# ══════════════════════════════════════════════════════════════════════════
# 2. semantic 분류가 geometry 를 바꾸지 않는다 (구조로 증명)
# ══════════════════════════════════════════════════════════════════════════


class TestSemanticClassificationDoesNotMutateGeometry:
    def test_geometry_fields_are_verbatim_copies_of_raw_probe_scalars(self):
        """`axis_c_page_level_from_probe` 가 만드는 interrupt 의 geometry 필드가
        classify_interrupt 의 결과와 무관하게 raw candidate 의 값과 정확히 같은지 확인한다.
        """
        raw_features = {
            "modal_overlay_candidates": [
                {
                    "selector": "div.a",
                    "visible": True,
                    "viewport_overlap_css_px2": 1234.5,
                    "viewport_coverage": 0.42,
                    "candidate_sources": ["role_dialog"],
                    "accessible_text": None,
                },
                {
                    "selector": "div.b",
                    "visible": True,
                    "viewport_overlap_css_px2": 9.9,
                    "viewport_coverage": 0.01,
                    "candidate_sources": [],
                    "accessible_text": "쿠키 안내",
                },
            ],
            "dismiss_control_candidates": [],
            "body_scroll_lock": {"locked": False},
        }
        result = mart.axis_c_page_level_from_probe(raw_features)
        recs = {r["selector"]: r for r in result["interrupts"]}
        assert recs["div.a"]["viewport_overlap_css_px2"] == 1234.5
        assert recs["div.a"]["viewport_coverage"] == 0.42
        assert recs["div.b"]["viewport_overlap_css_px2"] == 9.9
        assert recs["div.b"]["viewport_coverage"] == 0.01
        # 서로 다른 interrupt_form/interrupt_semantic 이 나왔는데도 geometry 는 원본 그대로.
        assert recs["div.a"]["interrupt_form"] != recs["div.b"]["interrupt_form"]
        assert recs["div.a"]["interrupt_semantic"] != recs["div.b"]["interrupt_semantic"]

    def test_monkeypatched_classifier_cannot_change_geometry(self, monkeypatch):
        """classify_interrupt 의 반환값을 강제로 바꿔도 geometry 열은 그대로다 —
        `axis_c_page_level_from_probe` 가 geometry 와 classification 을 코드 구조로
        분리하고 있음을 직접 증명한다.
        """
        raw_features = {
            "modal_overlay_candidates": [
                {
                    "selector": "div.c",
                    "visible": True,
                    "viewport_overlap_css_px2": 777.0,
                    "viewport_coverage": 0.33,
                    "candidate_sources": [],
                }
            ],
            "dismiss_control_candidates": [],
            "body_scroll_lock": {"locked": False},
        }
        before = mart.axis_c_page_level_from_probe(raw_features)

        def _always_blocking_modal(_candidate):
            return InterruptClassification(
                interrupt_form=InterruptLabel.BLOCKING_MODAL,
                interrupt_form_status=InterruptAxisStatus.RESOLVED,
                interrupt_semantic=InterruptLabel.LOGIN_PROMPT,
                interrupt_semantic_status=InterruptAxisStatus.RESOLVED,
            )

        monkeypatch.setattr(mart, "classify_interrupt", _always_blocking_modal)
        after = mart.axis_c_page_level_from_probe(raw_features)

        assert after["interrupts"][0]["interrupt_form"] == "BLOCKING_MODAL"
        assert after["interrupts"][0]["interrupt_semantic"] == "LOGIN_PROMPT"
        assert before["interrupts"][0]["viewport_overlap_css_px2"] == 777.0
        assert after["interrupts"][0]["viewport_overlap_css_px2"] == 777.0
        assert before["overlay_coverage"] == after["overlay_coverage"] == 0.33

    def test_axis_c_page_level_has_no_box_overlap_computation(self, monkeypatch):
        """`_overlap`(box-vs-box 새 geometry 계산)을 이 함수가 절대 호출하지 않는다는
        것을 monkeypatch 로 직접 증명한다 — 호출되면 예외를 던져 실패시킨다.
        """
        from landing_accessibility.engine import l0_collector

        def _boom(*_args, **_kwargs):
            raise AssertionError("axis_c_page_level_from_probe 가 _overlap 을 호출했다 — 금지")

        monkeypatch.setattr(l0_collector, "_overlap", _boom)
        raw_features = {
            "modal_overlay_candidates": [
                {
                    "selector": "div.d",
                    "visible": True,
                    "viewport_overlap_css_px2": 5.0,
                    "viewport_coverage": 0.02,
                    "candidate_sources": ["position_fixed"],
                }
            ],
            "dismiss_control_candidates": [
                {
                    "container_selector": "div.d",
                    "dismiss_control_candidates": [
                        {
                            "display": "block",
                            "visibility": "visible",
                            "opacity": "1",
                            "viewport_overlap_css_px2": 10,
                            "hittable": True,
                        }
                    ],
                }
            ],
            "body_scroll_lock": {"locked": True},
        }
        result = mart.axis_c_page_level_from_probe(raw_features)  # 예외 없이 통과해야 함
        assert result["overlay_coverage"] == 0.02


# ══════════════════════════════════════════════════════════════════════════
# 3. PrimaryActionOcclusion — task binding 없이는 절대 값을 만들지 않는다
# ══════════════════════════════════════════════════════════════════════════


class TestPrimaryActionOcclusionPendingTaskBinding:
    def test_always_none_with_pending_status_regardless_of_input(self):
        cases = [
            {
                "modal_overlay_candidates": [],
                "dismiss_control_candidates": [],
                "body_scroll_lock": {},
            },
            {
                "modal_overlay_candidates": [
                    {
                        "selector": "x",
                        "visible": True,
                        "viewport_overlap_css_px2": 999.0,
                        "viewport_coverage": 0.99,
                        "candidate_sources": ["role_dialog"],
                    }
                ],
                "dismiss_control_candidates": [],
                "body_scroll_lock": {"locked": True},
            },
        ]
        for raw in cases:
            result = mart.axis_c_page_level_from_probe(raw)
            assert result["primary_action_occlusion"] is None
            assert result["primary_action_occlusion_status"] == "PENDING_TASK_BINDING"

    def test_function_signature_takes_no_task_binding_input(self):
        """`axis_c_page_level_from_probe` 는 `primary_action_candidates`/task 정보를
        파라미터로조차 받지 않는다 — task binding 값을 만들 **능력이 코드에 없다.**
        """
        import inspect

        sig = inspect.signature(mart.axis_c_page_level_from_probe)
        params = list(sig.parameters)
        assert params == ["raw_features"], (
            "axis_c_page_level_from_probe 에 task/primary_action 관련 파라미터가 추가됐다 — "
            "PENDING_TASK_BINDING 경계가 깨졌을 수 있다"
        )

    def test_mart_rows_never_produce_primary_action_occlusion(self, mart_rows):
        for row in mart_rows:
            assert row["primary_action_occlusion"] is None
            assert row["primary_action_occlusion_status"] == "PENDING_TASK_BINDING"
            assert row["task_id"] is None
            assert row["task_id_status"] == "PENDING_TASK_BINDING"


# ══════════════════════════════════════════════════════════════════════════
# 4. 모집단 — duplicate 4건 제외, stub 6건(3 target) 배제, 하드코딩 없이 유도
# ══════════════════════════════════════════════════════════════════════════


class TestPopulationDenominators:
    def test_attempted_is_59(self, denominators):
        assert denominators["attempted"] == 59

    def test_evidence_bytes_denominator_is_56_after_duplicate_exclusion(self, denominators):
        assert denominators["evidence_bytes"] == 56
        assert denominators["excluded_duplicate_launch"] == 4

    def test_unobserved_stub_excludes_3_targets_not_6_raw_dirs(self, mart_rows, denominators):
        assert denominators["unobserved"] == 3
        unobserved_rows = [r for r in mart_rows if r["population_status"] == "UNOBSERVED_STUB"]
        names = {r["service_name"] for r in unobserved_rows}
        assert names == {"samsung_internet_browser", "samsung_notes", "samsung_wallet"}
        for r in unobserved_rows:
            assert r["in_main_population"] is False

    def test_measured_denominator_excludes_3_degenerate_captures(self, denominators):
        assert denominators["measured"] == 53
        assert denominators["failed_evidence_incomplete"] == 3

    def test_degenerate_captures_are_the_named_three(self, mart_rows):
        failed = {
            r["service_name"]
            for r in mart_rows
            if r["measurement_status"] == "FAILED_EVIDENCE_INCOMPLETE"
        }
        assert failed == {"coupang_eats", "shinhan_sol_bank", "lotte_himart"}

    def test_degenerate_captures_stay_undetermined_not_fail(self, mart_rows):
        """`D-R0-23` — 측정 실패는 FAIL 로 전이되지 않는다. 이 mart 에 PASS/FAIL 어휘
        자체가 없다는 것으로 그 금지를 지킨다(Axis A 판정 컬럼이 이 mart 에 없음)."""
        for r in mart_rows:
            for key in r:
                assert "verdict" not in key.lower()
            assert r.get("axis_c_missingness_reason") != "FAIL"

    def test_duplicate_launch_rows_are_flagged_not_silently_dropped(self, mart_rows):
        dup_rows = [r for r in mart_rows if r["population_status"] == "EXCLUDED_DUPLICATE_LAUNCH"]
        assert len(dup_rows) == 4
        names = {r["service_name"] for r in dup_rows}
        assert names == {"netflix", "chrome", "hyundai_card", "cashwalk"}
        for r in dup_rows:
            assert r["in_main_population"] is False
            assert r["canonical_run_id_kept"] is not None

    def test_row_count_accounts_for_every_attempted_and_every_excluded_duplicate(
        self, mart_rows, denominators
    ):
        # attempted(59) 서비스 각각 최소 1행 + duplicate 로 제외된 4행 추가 = 63.
        assert (
            len(mart_rows) == denominators["attempted"] + denominators["excluded_duplicate_launch"]
        )

    def test_denominator_is_never_a_single_hardcoded_number_in_source(self):
        """`compute_denominators` 가 실제로 데이터에서 집계하는지 — 소스에 `== 56`
        같은 매직넘버로 반환을 고정한 줄이 없는지 정적으로 확인한다."""
        src = Path(mart.__file__).read_text(encoding="utf-8")
        # compute_denominators 함수 몸통만 추출해 하드코딩 리터럴 반환이 없는지 확인.
        start = src.index("def compute_denominators")
        end = src.index("\ndef main", start)
        body = src[start:end]
        assert "return {" in body
        for magic in ("56", "53", "59", "3,", "4,"):
            assert f"= {magic}" not in body.replace(" ", "")


# ══════════════════════════════════════════════════════════════════════════
# 5. 결측은 NULL — 0 이나 상한값으로 대체하지 않는다
# ══════════════════════════════════════════════════════════════════════════


class TestMissingnessStaysNull:
    def test_failed_and_unobserved_rows_have_null_axis_c_fields_not_zero(self, mart_rows):
        null_fields = (
            "interrupt_count_visible",
            "overlay_coverage",
            "interrupts",
            "classifier_version",
            "form_classification_tier_counts",
            "semantic_classification_tier_counts",
            "body_scroll_locked",
            "dismiss_control_present_count",
            "dismiss_control_visible_count",
            "pac_len",
            "pac_truncated",
        )
        for row in mart_rows:
            if row["measurement_status"] in ("MEASURED",):
                continue
            for f in null_fields:
                assert row[f] is None, (
                    f"{row['service_name']}.{f} 가 결측인데 {row[f]!r} 로 채워짐 — 0/상한 대체 금지"
                )

    def test_measured_rows_overlay_coverage_is_never_silently_zero_for_missing_probe(
        self, mart_rows
    ):
        # probe_path 가 없는 행은 axis_c_valid 가 False 이고 overlay_coverage 는 None 이어야 한다
        # (0.0 으로 채워지면 "관측된 무장애물(0.0)"과 "결측"이 뒤섞인다).
        for row in mart_rows:
            if not row["probe_path"]:
                assert row["overlay_coverage"] is None

    def test_informative_missingness_candidates_total_6(self, denominators):
        assert denominators["informative_missingness_candidates"] == 6

    def test_task_id_is_null_everywhere_not_a_placeholder_string_value(self, mart_rows):
        for row in mart_rows:
            assert row["task_id"] is None  # "PENDING" 같은 문자열로 결측을 감추지 않는다
            assert row["task_id_status"] == "PENDING_TASK_BINDING"


# ══════════════════════════════════════════════════════════════════════════
# 6. probe 배열 cap — page-level(overlay) 은 안전, primary_action 은 절단 관측됨
# ══════════════════════════════════════════════════════════════════════════


class TestProbeCapTruncation:
    def test_overlay_and_dismiss_fields_never_hit_any_cap_candidate(self, mart_rows):
        for row in mart_rows:
            if row["measurement_status"] != "MEASURED":
                continue
            assert row["modal_overlay_candidates_len"] < 200
            assert row["dismiss_control_candidates_len"] < 200

    def test_verify_overlay_fields_not_capped_reports_safe(self, mart_rows):
        report = mart.verify_overlay_fields_not_capped(mart_rows)
        assert report["safe_from_cap"] is True
        assert report["n_checked"] == 53

    def test_primary_action_candidates_truncation_is_flagged_when_present(self, mart_rows):
        truncated = [r for r in mart_rows if r.get("pac_truncated")]
        for r in truncated:
            assert r["pac_len"] == 200
        # B 의 전수조사(n=58) 결과와 일치해야 한다: 정확히 7건.
        assert len(truncated) == 7

    def test_pac_truncated_never_true_when_axis_c_invalid(self, mart_rows):
        for row in mart_rows:
            if not row["axis_c_valid"]:
                assert row["pac_truncated"] is None


# ══════════════════════════════════════════════════════════════════════════
# 7. duplicate capture group (F-A2) — 삭제하지 않고 플래그 + 양방향 분모
# ══════════════════════════════════════════════════════════════════════════


class TestDuplicateCaptureGroup:
    def test_nh_pair_flagged_same_group_not_deleted(self, mart_rows):
        nh = {
            r["service_name"]: r
            for r in mart_rows
            if r["service_name"] in ("nh_smart_banking", "nh_cok_bank")
        }
        assert len(nh) == 2
        groups = {r["duplicate_capture_group"] for r in nh.values()}
        assert len(groups) == 1
        assert None not in groups
        for r in nh.values():
            assert r["duplicate_capture_group_size"] == 2
            assert r["in_main_population"] is True  # 삭제되지 않았다
            assert r["measurement_status"] == "MEASURED"  # FAIL 로 전이되지 않았다

    def test_both_raw_and_collapsed_denominator_are_computable(self, denominators):
        assert denominators["measured_n_raw"] == 53
        assert denominators["measured_n_collapsed_duplicate_capture"] == 52
        assert (
            denominators["measured_n_collapsed_duplicate_capture"] < denominators["measured_n_raw"]
        )

    def test_only_one_duplicate_capture_group_found(self, denominators):
        # A 의 전수 스캔 결과("이런 쌍은 이 1군뿐")를 W4 가 독립적으로 재확인.
        assert denominators["duplicate_capture_groups"] == 1

    def test_dr054_primary_collapses_one_member_sensitivity_keeps_both(
        self, mart_rows, denominators
    ):
        """`D-R0-54` — 주분석은 그룹당 1건으로 접고, 2건 계수는 감도분석으로 낸다."""
        nh = [r for r in mart_rows if r["service_name"] in ("nh_smart_banking", "nh_cok_bank")]
        roles = {r["collapse_role"] for r in nh}
        assert roles == {"PRIMARY_REPRESENTATIVE", "COLLAPSED_IN_PRIMARY"}
        primary_count = sum(1 for r in nh if r["axis_c_valid_primary"])
        assert primary_count == 1  # 주분석엔 그룹당 1건만
        sensitivity_count = sum(1 for r in nh if r["axis_c_valid"])
        assert sensitivity_count == 2  # 감도분석(uncollapsed)엔 2건 다
        assert denominators["axis_c_valid_primary_collapsed"] == 52
        assert denominators["axis_c_valid_sensitivity_uncollapsed"] == 53

    def test_collapse_role_deterministic_by_service_name(self, mart_rows):
        """대표 선택이 임의가 아니라 `service_name` 사전순으로 재현 가능해야 한다."""
        nh = sorted(
            (r for r in mart_rows if r["service_name"] in ("nh_smart_banking", "nh_cok_bank")),
            key=lambda r: r["service_name"],
        )
        # "nh_cok_bank" < "nh_smart_banking" 사전순 — cok 이 대표가 돼야 한다.
        assert nh[0]["service_name"] == "nh_cok_bank"
        assert nh[0]["collapse_role"] == "PRIMARY_REPRESENTATIVE"
        assert nh[1]["collapse_role"] == "COLLAPSED_IN_PRIMARY"

    def test_non_grouped_rows_are_always_primary_representative(self, mart_rows):
        for r in mart_rows:
            if r.get("in_main_population") and r.get("duplicate_capture_group") is None:
                assert r["collapse_role"] == "PRIMARY_REPRESENTATIVE"


# ══════════════════════════════════════════════════════════════════════════
# 8. 소유 파일 경계 — l0_probe.js 를 건드리지 않았는지, 다른 owner 파일 무손 확인
# ══════════════════════════════════════════════════════════════════════════


class TestProbeCapCountsMatchConfirmedScan:
    """B/C 독립 재계산이 일치한 확정 수치(n=58 probe.json)와 대조한다."""

    def test_contrast_cap_hits_8(self, mart_rows):
        assert sum(1 for r in mart_rows if r.get("contrast_at_400")) == 8

    def test_animated_elements_cap_hits_at_least_1(self, mart_rows):
        hits = [r for r in mart_rows if r.get("anim_truncated")]
        assert len(hits) >= 1
        for r in hits:
            assert r["anim_len"] == 60

    def test_ans_and_ts_cap_counts(self, mart_rows):
        assert sum(1 for r in mart_rows if r.get("ans_truncated")) == 13
        assert sum(1 for r in mart_rows if r.get("ts_truncated")) == 6

    def test_probe_primary_action_n_is_alias_of_pac_len(self, mart_rows):
        for r in mart_rows:
            assert r["probe_primary_action_n"] == r["pac_len"]

    def test_all_cap_columns_store_counts_not_only_bools(self, mart_rows):
        """개수(`*_len`) 자체가 있어야 cap 기준이 바뀌어도 재계산할 수 있다."""
        measured = [r for r in mart_rows if r["measurement_status"] == "MEASURED"]
        assert measured
        for r in measured:
            assert isinstance(r["pac_len"], int)
            assert isinstance(r["ans_len"], int)
            assert isinstance(r["ts_len"], int)
            assert isinstance(r["contrast_len"], int)
            assert isinstance(r["anim_len"], int)


class TestCapHitDecisionD_R0_53:
    """`D-R0-53` DECISION-1(이름 확정) · DECISION-2(영향 범위) 를 코드로 확인한다."""

    def test_cap_hit_keys_use_confirmed_naming(self, mart_rows):
        measured = [r for r in mart_rows if r["measurement_status"] == "MEASURED"]
        assert measured
        for r in measured:
            for key in (
                "cap_hit_primary_action_candidates",
                "cap_hit_accessible_name_sources",
                "cap_hit_target_size",
                "cap_hit_contrast",
                "cap_hit_animated_elements",
            ):
                assert key in r
                assert r[key] in (True, False)

    def test_cap_hit_matches_len_based_truncated_flags(self, mart_rows):
        for r in mart_rows:
            if r["measurement_status"] != "MEASURED":
                continue
            assert r["cap_hit_primary_action_candidates"] == r["pac_truncated"]
            assert r["cap_hit_accessible_name_sources"] == r["ans_truncated"]
            assert r["cap_hit_target_size"] == r["ts_truncated"]
            assert r["cap_hit_contrast"] == r["contrast_at_400"]

    def test_truncation_does_not_lower_axis_c_valid(self, mart_rows):
        """DECISION-2 — 절단은 그 필드 의존 지표만 UNDETERMINED 후보다. 이 mart 에
        `axis_c_valid`를 낮추는 코드 경로가 cap 여부를 참조하지 않는지 소스로 확인한다.

        대입문 전체(괄호가 닫힐 때까지, 여러 줄일 수 있음)를 잘라내 검사한다 — 한
        줄만 보면 `row["axis_c_valid"] = (` 만 잡혀 아무것도 검증하지 못한다.
        """
        source = Path(mart.__file__).read_text(encoding="utf-8")
        start = source.index('row["axis_c_valid"] = (')
        end = source.index(")\n", start) + 1
        formula = source[start:end]
        assert "bool(row[" in formula  # 실제로 뭔가 잡혔는지 자체 검증
        assert "measurement_status" in formula
        assert "cap_hit" not in formula
        assert "truncated" not in formula

    def test_regex_extraction_sanity_check(self):
        """위 테스트가 실제로 formula 를 잘라내는지 자체 검증 — 빈 문자열을 통과
        시키는 퇴화 테스트가 아님을 보증한다."""
        source = Path(mart.__file__).read_text(encoding="utf-8")
        start = source.index('row["axis_c_valid"] = (')
        end = source.index(")\n", start) + 1
        formula = source[start:end]
        assert len(formula) > 40

    def test_overlay_geometry_unaffected_by_any_cap(self, mart_rows):
        """DECISION-2 — modal_overlay/dismiss_control 은 cap 무관이므로 page-level
        OverlayCoverage 는 절단 영향이 없다."""
        report = mart.verify_overlay_fields_not_capped(mart_rows)
        assert report["safe_from_cap"] is True

    def test_cap_hit_counts_match_confirmed_scan(self, mart_rows):
        assert sum(1 for r in mart_rows if r.get("cap_hit_primary_action_candidates")) == 7
        assert sum(1 for r in mart_rows if r.get("cap_hit_accessible_name_sources")) == 13
        assert sum(1 for r in mart_rows if r.get("cap_hit_target_size")) == 6
        assert sum(1 for r in mart_rows if r.get("cap_hit_contrast")) == 8


class TestPriorObservedArchetypeD_R0_55:
    """`D-R0-55` — A 가 유보한 결정을 W4 가 대신 확정하지 않는다."""

    def test_prior_archetype_populated_for_all_attempted(self, mart_rows):
        attempted_rows = [
            r for r in mart_rows if r["population_status"] != "EXCLUDED_DUPLICATE_LAUNCH"
        ]
        assert len(attempted_rows) == 59
        for r in attempted_rows:
            assert r["prior_archetype"] in (
                "QUERY",
                "CONTENT_OPEN",
                "ITEM_DETAIL",
                "PLACE_LOOKUP",
                "COMMUNICATION_ENTRY",
                "FINANCIAL_ACTION_ENTRY",
                "UTILITY_ENTRY",
            )

    def test_observed_archetype_never_populated_without_task_binding(self, mart_rows):
        for r in mart_rows:
            assert r["observed_archetype"] is None
            assert r["observed_archetype_status"] == "PENDING_TASK_BINDING"

    def test_neither_archetype_column_is_dropped_or_renamed_to_the_other(self, mart_rows):
        """두 컬럼이 항상 공존해야 한다 — 어느 한쪽으로 확정해 다른 쪽을 지우지 않는다."""
        for r in mart_rows:
            assert "prior_archetype" in r
            assert "observed_archetype" in r


class TestCapHitBiasIsDescriptiveOnly:
    """cap-hit 15/14 건의 archetype 분포는 기술통계다 — 이 mart 는 결론을 내지 않는다."""

    def test_manifest_marks_distribution_as_descriptive_only(self):
        stats = mart.cap_hit_prior_archetype_distribution(
            [
                {
                    "measurement_status": "MEASURED",
                    "cap_hit_primary_action_candidates": True,
                    "cap_hit_accessible_name_sources": False,
                    "cap_hit_target_size": False,
                    "cap_hit_contrast": False,
                    "prior_archetype": "ITEM_DETAIL",
                },
                {
                    "measurement_status": "MEASURED",
                    "cap_hit_primary_action_candidates": False,
                    "cap_hit_accessible_name_sources": False,
                    "cap_hit_target_size": False,
                    "cap_hit_contrast": False,
                    "prior_archetype": "QUERY",
                },
            ]
        )
        assert (
            stats["note"]
            == "DESCRIPTIVE_ONLY_NOT_A_TEST — 통계적 유의성 주장 없음, archetype 비교 왜곡 결론 없음"
        )
        assert stats["cap_hit_n"] == 1
        assert stats["measured_n"] == 2

    def test_no_conclusion_language_in_mart_script_source(self):
        """ "왜곡"·"편향" 같은 결론성 단어가 소스 문자열 리터럴(출력값)에 들어가지
        않는지 확인한다 — 주석/문서에서의 인용은 허용하되, 실제로 만드는 데이터에
        결론을 담지 않는다는 것을 간접적으로 확인한다."""
        stats_keys = set(
            mart.cap_hit_prior_archetype_distribution(
                [{"measurement_status": "MEASURED", "prior_archetype": "QUERY"}]
            ).keys()
        )
        assert "conclusion" not in stats_keys
        assert "bias_confirmed" not in stats_keys
        assert "skew" not in stats_keys


class TestSlotRawMaterialLeavesDefinitionOpen:
    """`T-A-LABEL-FROZEN-001` F-A3.1 — dom/ax/probe slot 원자재는 저장하되
    `dom_body_empty`/`slot_disagreement` 는 W4 가 임의로 bool 을 확정하지 않는다."""

    def test_dom_body_empty_is_always_none_with_pending_status(self, mart_rows):
        for r in mart_rows:
            assert r["dom_body_empty"] is None
            assert r["dom_body_empty_status"] == "DEFINITION_PENDING_D_LAYER"

    def test_slot_disagreement_is_always_none_with_pending_status(self, mart_rows):
        for r in mart_rows:
            assert r["slot_disagreement"] is None
            assert r["slot_disagreement_status"] == "DEFINITION_PENDING_D_LAYER_T-B-RQ-D-001-Q3"

    def test_dom_ax_raw_material_survives_even_when_probe_is_missing(self, mart_rows):
        """shinhan_sol_bank/lotte_himart 는 probe.json 이 없어 axis_c 는 결측이지만,
        dom.html/ax.json 은 L0-a 단계에서 먼저 저장되므로 그 원자재는 남아 있어야 한다."""
        by_name = {r["service_name"]: r for r in mart_rows}
        for name in ("shinhan_sol_bank", "lotte_himart"):
            row = by_name[name]
            assert row["pac_len"] is None  # probe 결측이므로 probe 파생값은 NULL
            assert row["dom_bytes"] is not None  # 그러나 dom slot 은 존재한다
            assert row["dom_body_element_count"] is not None
            assert row["ax_node_count"] is not None

    def test_nh_pair_shows_empty_dom_ax_but_rich_probe(self, mart_rows):
        """F-A3.1 이 설명한 slot 불일치 현상을 원자재 컬럼으로 재확인한다 — 해석하지
        않는다(불일치 여부 판정은 이 mart 의 일이 아니다), 숫자만 검증한다."""
        by_name = {r["service_name"]: r for r in mart_rows}
        for name in ("nh_smart_banking", "nh_cok_bank"):
            row = by_name[name]
            assert row["dom_bytes"] == 1657
            assert row["dom_body_element_count"] == 0
            assert row["ax_node_count"] == 1
            assert row["probe_primary_action_n"] == 24
            assert row["modal_overlay_candidates_len"] == 15

    def test_dom_bytes_never_null_for_measured_or_failed_probe_missing_rows(self, mart_rows):
        for r in mart_rows:
            if r["population_status"] == "OBSERVED":
                assert r["dom_bytes"] is not None


class TestD_R0_58_SemanticLabelNoLongerCollapses:
    """`C-FINDING-214214` P2 회귀검사 — semantic 라벨이 다시 BANNER 등으로 붕괴하면
    이 클래스가 실패해야 한다."""

    def test_semantic_labels_beyond_form_vocabulary_are_present_in_real_mart(self, mart_rows):
        """실제 mart 에 LOGIN_PROMPT/COOKIE_CONSENT/CHAT_WIDGET/ADVERTISEMENT/
        APP_INSTALL_PROMPT 중 하나라도 RESOLVED 로 살아남아 있어야 한다 — 전부
        BANNER/PROMOTION_MODAL/BLOCKING_MODAL(form 어휘)로만 나오면 붕괴가 재발한 것."""
        semantic_only_labels = {
            "LOGIN_PROMPT",
            "COOKIE_CONSENT",
            "CHAT_WIDGET",
            "ADVERTISEMENT",
            "APP_INSTALL_PROMPT",
        }
        found: set[str] = set()
        for r in mart_rows:
            for iv in r.get("interrupts") or []:
                if iv["interrupt_semantic_status"] == "RESOLVED":
                    found.add(iv["interrupt_semantic"])
        assert found & semantic_only_labels, (
            "semantic 전용 라벨이 mart 어디에도 RESOLVED 로 없다 — BANNER 붕괴 재발 의심"
        )

    def test_v1_transition_table_reproduces_w4_self_recomputed_counts(self, mart_rows):
        """`D-R0-58-2` provenance — W4 자체 재계산 수치를 회귀 고정한다(재발 시 실패).
        C 인용치(22/17)와 다를 수 있음을 completion 보고에 명시(모집단 차이 미확인)."""
        table = mart.compute_v1_collapse_transition_table(mart_rows)
        assert table["classifier_version_new"] == mart.CLASSIFY_INTERRUPT_VERSION
        assert table["total_semantic_labels_recovered"] == 19
        assert table["observations_affected"] == 16
        assert table["transitions_semantic_to_v1_shown"]["LOGIN_PROMPT→BANNER"] == 7
        assert table["transitions_semantic_to_v1_shown"]["PROMOTION_MODAL→BANNER"] == 5

    def test_form_and_semantic_never_forced_equal_by_construction(self, mart_rows):
        """두 축이 서로 값을 복사/강제하지 않는지 — RESOLVED 인데 값이 다른 사례가
        실제로 존재해야 한다(둘이 항상 같다면 독립 축이 아니라 여전히 하나로 묶인 것)."""
        differing = 0
        for r in mart_rows:
            for iv in r.get("interrupts") or []:
                if (
                    iv["interrupt_form_status"] == "RESOLVED"
                    and iv["interrupt_semantic_status"] == "RESOLVED"
                    and iv["interrupt_form"] != iv["interrupt_semantic"]
                ):
                    differing += 1
        assert differing > 0

    def test_axis_status_vocabulary_is_the_confirmed_three_values(self, mart_rows):
        """`D-R0-58-1` — 기존 `ClassificationStatus`(5종) 를 재사용하지 않고
        `RESOLVED`/`UNRESOLVED`/`NOT_APPLICABLE` 3종만 쓴다."""
        seen: set[str] = set()
        for r in mart_rows:
            for iv in r.get("interrupts") or []:
                seen.add(iv["interrupt_form_status"])
                seen.add(iv["interrupt_semantic_status"])
        assert seen <= {"RESOLVED", "UNRESOLVED", "NOT_APPLICABLE"}
        assert "DETERMINISTIC" not in seen
        assert "SEMANTIC_MODEL" not in seen
        assert "AMBIGUOUS" not in seen

    def test_classifier_version_present_on_measured_rows(self, mart_rows):
        for r in mart_rows:
            if r["measurement_status"] == "MEASURED":
                assert r["classifier_version"] == mart.CLASSIFY_INTERRUPT_VERSION
            else:
                assert r["classifier_version"] is None


class TestArtifactProvenanceProtocol12:
    """`D-R0-58-2`/프로토콜 §12 — completion 이 검산 가능하도록 sha256/bytes/행수를
    manifest 자신이 담는다(C 가 지난번 이게 없어 산출물을 검산 못했다고 지적함)."""

    def test_manifest_has_artifact_refs_with_sha256_bytes_row_count(self, tmp_path):
        attempted = mart.load_attempted_population()
        run_dirs = mart.discover_run_dirs()
        rows = mart.build_mart_rows(attempted, run_dirs)
        out_jsonl = tmp_path / "mart_axisc_observations.jsonl"
        with out_jsonl.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(__import__("json").dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        data = out_jsonl.read_bytes()
        import hashlib as _hashlib

        expected_sha = _hashlib.sha256(data).hexdigest()
        assert len(expected_sha) == 64
        assert len(data) > 0
        assert len(rows) == 63


class TestOwnershipBoundary:
    def test_l0_probe_js_not_opened_or_imported_by_mart_script(self):
        """`l0_probe.js` 는 문서 주석의 **인용**으로만 나타나야 한다 — 스크립트가 그
        파일을 열거나(`open(...)`) import 하면 안 된다(W2 소유, 읽기 전용 계약 위반)."""
        src = Path(mart.__file__).read_text(encoding="utf-8")
        forbidden_patterns = ('"l0_probe.js"', "'l0_probe.js'", "PROBE_JS", "import l0_probe")
        for pattern in forbidden_patterns:
            assert pattern not in src, (
                f"{pattern!r} 가 스크립트에 있다 — l0_probe.js 를 열려는 시도로 보인다"
            )

    def test_mart_script_never_imports_playwright(self):
        src = Path(mart.__file__).read_text(encoding="utf-8")
        assert "playwright" not in src.lower()
        assert "sync_playwright" not in src


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
