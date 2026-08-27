"""W2 — Representative Function / Endpoint detector (real-site). `T-A-W2-001`.

**이 파일의 PASS/FAIL 은 synthetic fixture 와 hand-built raw dict 에 대한 engine test
결과다. 실제 서비스에 대한 research finding 이 아니다** (`PHASE_GATES §4.1`·`§4.3`·`§4.6`,
`D-R0-17`). 픽스처가 심는 마커가 곧 지금 detector 가 읽는 것이라는 뜻이 **아니다** — 이 파일의
핵심 취지가 바로 그 반대(marker 없이 성립하는 실신호 경로)를 증명하는 것이지만, 그렇다고 해도
"이 fixture 셋 위에서 통과했다"가 "임의의 실사이트에서 이 정확도로 동작한다"를 뜻하지 않는다.
정밀도/재현율은 holdout 에서 C 가 독립 검증한다 — B(이 lane)는 holdout 을 찾거나 읽지 않는다.

대응 티켓: `T-A-W2-001` (P1). 관련 계약: RF-DT v2.1 §5·§6, R0 계약 §3(D-R0-10~13)·§4
(D-R0-14~20), Director 조정 D-R0-41(UTILITY_ENTRY Branch U)·D-R0-42(marker 게이팅).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.depth import (  # noqa: E402
    DepthResult,
    assign_depth_segments,
)
from landing_accessibility.engine.firewall import ExecutionMode  # noqa: E402
from landing_accessibility.engine.gate_classifier import (  # noqa: E402
    GateSignals,
    classify_gate_kind,
)
from landing_accessibility.engine.l0_collector import PROBE_JS  # noqa: E402
from landing_accessibility.engine.l1_engine import (  # noqa: E402
    NLP_FALLBACK_MARGIN_THRESHOLD,
    MappingOutcome,
    Scout,
    ScoutBudget,
    TaskDefinition,
    _gate_basis_is_vocabulary_only,
    _nlp_fallback_resolve,
    detect_area_signal,
    detect_endpoint_signal,
    gate_observed,
    observation_truncation_caveats,
    resolve_representative_function,
)
from landing_accessibility.engine.vocabulary import (  # noqa: E402
    AreaSignalStatus,
    DepthSegment,
    EndpointStatus,
    GateKind,
)
from landing_accessibility.engine.vocabulary import InteractionArchetype as A  # noqa: E402
from landing_accessibility.engine.vocabulary import RegionSignalType as R  # noqa: E402

pytest.importorskip("playwright.sync_api")

FIXTURES = RESEARCH / "fixtures"

pytestmark = pytest.mark.slow


def _scout(
    budget: ScoutBudget | None = None, execution_mode: ExecutionMode = ExecutionMode.FIXTURE
) -> Scout:
    return Scout(
        fixture_root=FIXTURES,
        budget=budget or ScoutBudget(max_activations_per_task=5, branching_limit=3),
        execution_mode=execution_mode,
    )


# ══════════════════════════════════════════════════════════════════════════
# 1) synthetic marker 없이 region/endpoint 가 실신호로 성립한다 (D-R0-14 · D-R0-16)
# ══════════════════════════════════════════════════════════════════════════
def test_content_open_region_and_endpoint_succeed_without_any_marker() -> None:
    """`w2_real_content_list.html`/`w2_real_content_article.html` 은 `data-region`/
    `data-endpoint` 를 전혀 쓰지 않는다. Region 은 `repeated_structure`(list-container 소속
    링크), Endpoint 는 `endpoint_signals.article_present`(실 `<article>` 태그) 만으로 성립해야
    한다."""
    task = TaskDefinition("T2", A.CONTENT_OPEN, None, None)  # 기본 signal_type = DOM_AX_ROLE
    entry, manifest = _scout().scout(
        web_target_id="wt-w2-content", entry_fixture="w2_real_content_list.html", task=task
    )
    assert entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert (entry.ned, entry.ied, entry.mpfed) == (0, 1, 1)
    assert [s.depth_segment for s in entry.steps] == ["IED"]
    assert manifest is not None


def test_utility_entry_region_and_endpoint_succeed_without_any_marker() -> None:
    """`w2_real_utility.html` — Branch U(D-R0-41): landing 이 이미 button+input 을 갖고 있으므로
    k=m=0. `<a>` 링크가 아니라 실제 조작 가능한 위젯(button)만 candidate 로 인정한 결과다."""
    task = TaskDefinition("TU2", A.UTILITY_ENTRY, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    entry, _ = _scout().scout(
        web_target_id="wt-w2-utility", entry_fixture="w2_real_utility.html", task=task
    )
    assert entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert (entry.ned, entry.ied, entry.mpfed) == (0, 0, 0)
    assert len(entry.steps) == 0


def test_utility_entry_bare_navigation_link_does_not_count_as_primary_control() -> None:
    """`unresolved_route.html` 은 `<a>` 링크만 있다(button/input 없음) — Branch U 의
    "primary control" 이 plain navigation link 로 오판되면 안 된다는 회귀다. 실측: 이
    좁힘이 없으면 이 fixture 가 랜딩에서 즉시 area=True 가 되어 기존 예산-소진 계약
    (`test_budget_fires_and_depth_stays_null`, `tests/test_pc_fixture_engine.py`)이 깨진다."""
    task = TaskDefinition("TU3", A.UTILITY_ENTRY, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    entry, _ = _scout(budget=ScoutBudget(max_activations_per_task=5, branching_limit=3)).scout(
        web_target_id="wt-w2-bare-link", entry_fixture="unresolved_route.html", task=task
    )
    assert entry.endpoint_status == "UNRESOLVED"
    assert (entry.ned, entry.ied, entry.mpfed) == (None, None, None)


def test_query_endpoint_succeeds_via_real_url_pattern_without_marker() -> None:
    """`w2_query_real.html` 은 진짜 `<form method=get>` 제출을 쓴다 — `data-endpoint`/
    `body[data-endpoint-reached]` 없이, Scout 가 채운 `task.query_text` 가 실제로 URL 의
    query string 에 반영됐는지(URL_PATTERN)만으로 endpoint 가 성립해야 한다."""
    task = TaskDefinition(
        "TQR", A.QUERY, None, None, R.FORM_STRUCTURE, R.URL_PATTERN, query_text="고령자 접근성"
    )
    entry, _ = _scout().scout(
        web_target_id="wt-w2-query", entry_fixture="w2_query_real.html", task=task
    )
    assert entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert (entry.ned, entry.ied, entry.mpfed) == (0, 1, 1)
    assert entry.text_input_episode_count == 1


# ══════════════════════════════════════════════════════════════════════════
# 2) REAL_TARGET 모드에서 marker 3종 읽기 시도 자체가 없다 (D-R0-42 · Director 지시)
# ══════════════════════════════════════════════════════════════════════════
def test_real_target_mode_never_calls_the_three_forbidden_marker_reads() -> None:
    """`data-region` / `data-endpoint` / `data-endpoint-reached` — 결과값이 비어 있는 것으로는
    부족하다(Director 지시). `document.querySelectorAll`/`Element.getAttribute` 를 spy 로
    감싸 **호출 자체**가 없음을 증명한다. `depth_path_0.html` 은 세 marker 를 전부 갖고 있어
    양성 대조(FIXTURE 모드에서는 실제로 호출됨)와 음성 대조(REAL_TARGET 모드에서는 호출 안 됨)
    양쪽을 한 fixture 로 검증할 수 있다.
    """
    from playwright.sync_api import sync_playwright

    spy_install_js = """
    () => {
      window.__w2SpyCalls = [];
      if (!window.__w2SpyInstalled) {
        window.__w2SpyInstalled = true;
        const origQSA = Document.prototype.querySelectorAll;
        Document.prototype.querySelectorAll = function (sel) {
          if (sel === '[data-region]' || sel === '[data-endpoint]') {
            window.__w2SpyCalls.push('querySelectorAll(' + sel + ')');
          }
          return origQSA.call(this, sel);
        };
        const origGetAttr = Element.prototype.getAttribute;
        Element.prototype.getAttribute = function (name) {
          if (name === 'data-endpoint-reached' && this === document.body) {
            window.__w2SpyCalls.push('body.getAttribute(data-endpoint-reached)');
          }
          return origGetAttr.call(this, name);
        };
      }
    }
    """
    fixture = FIXTURES / "depth_path_0.html"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        try:
            page.goto(f"file://{fixture.resolve()}", wait_until="load")
            page.evaluate(spy_install_js)

            # 양성 대조 — FIXTURE 모드(인자 없음 → undefined)에서는 세 신호 모두 실제로 읽힌다.
            fixture_probe = page.evaluate(PROBE_JS)
            fixture_calls = page.evaluate("window.__w2SpyCalls")
            assert "querySelectorAll([data-region])" in fixture_calls
            assert "querySelectorAll([data-endpoint])" in fixture_calls
            assert "body.getAttribute(data-endpoint-reached)" in fixture_calls
            # spy 가 실제로 작동한다는 증거로, 이 모드에서는 marker 값도 채워져 있어야 한다.
            assert fixture_probe["raw_features"]["region_signals"]["declared_regions"]
            assert fixture_probe["raw_features"]["endpoint_signals"]["declared_endpoints"]
            assert fixture_probe["raw_features"]["endpoint_signals"]["body_endpoint_reached"]

            # 음성 대조 — REAL_TARGET 모드에서는 호출 자체가 없다.
            page.evaluate("window.__w2SpyCalls = []")
            real_target_probe = page.evaluate(PROBE_JS, "REAL_TARGET")
            real_target_calls = page.evaluate("window.__w2SpyCalls")
            assert real_target_calls == [], (
                f"REAL_TARGET 모드에서 marker 읽기 시도가 있었다: {real_target_calls}"
            )
            assert real_target_probe["raw_features"]["region_signals"]["declared_regions"] == []
            assert real_target_probe["raw_features"]["endpoint_signals"]["declared_endpoints"] == []
            assert (
                real_target_probe["raw_features"]["endpoint_signals"]["body_endpoint_reached"]
                is None
            )
            assert (
                real_target_probe["raw_features"]["region_signals"]["marker_path_disabled"] is True
            )
            assert (
                real_target_probe["raw_features"]["endpoint_signals"]["marker_path_disabled"]
                is True
            )
        finally:
            browser.close()


def test_detect_functions_never_use_marker_fields_in_real_target_mode_even_if_populated() -> None:
    """방어적 이중화 — `l0_probe.js` 의 게이팅이 어떤 이유로든 깨져 `raw` 에 marker 값이
    실려 왔다고 **가정해도**, Python 판정 함수는 `execution_mode is REAL_TARGET` 이면 그
    필드를 절대 소비하지 않는다."""
    raw = {
        "region_signals": {
            "declared_regions": [{"region": "MATCHES_TASK", "present": True, "visible": True}],
            "search_inputs": [],
        },
        "endpoint_signals": {
            "declared_endpoints": [{"endpoint": "MATCHES_TASK_EP", "visible": True}],
            "body_endpoint_reached": "MATCHES_TASK_EP",
            "article_present": 0,
            "video_playing": False,
        },
    }
    task = TaskDefinition("TDEF", A.CONTENT_OPEN, "MATCHES_TASK", "MATCHES_TASK_EP")
    assert (
        detect_area_signal(raw, task, ExecutionMode.FIXTURE) is True
    )  # FIXTURE 는 여전히 marker 를 쓴다
    assert detect_area_signal(raw, task, ExecutionMode.REAL_TARGET) is False
    assert detect_endpoint_signal(raw, task, ExecutionMode.FIXTURE) is True
    assert detect_endpoint_signal(raw, task, ExecutionMode.REAL_TARGET) is False


# ══════════════════════════════════════════════════════════════════════════
# 3) endpoint false-positive adversarial — 우연 일치 marker (T-B-FC-001 실측 재현)
# ══════════════════════════════════════════════════════════════════════════
def test_endpoint_false_positive_adversarial_fixture_from_real_measurement() -> None:
    """B 의 n=58 전수 재집계에서 실제로 관측된 형태를 그대로 재현한다: tiktok.com 은
    분석/설정용 `<script>` 에 우연히 `data-region="sg"` 를 갖고 있었다(region 신호와 무관한
    속성이 우연히 marker 셀렉터에 걸린 사례). 이 테스트는 그보다 더 나쁜 경우 —
    **task 의 region_definition/endpoint_definition 이 그 우연한 값과 정확히 일치하는
    최악의 경우**를 구성해, REAL_TARGET 모드에서는 그래도 위양성이 나지 않음을 증명한다.
    (실제 `body_endpoint_reached`/`declared_endpoints` 는 58/58 에서 신호가 없었다 — 여기서는
    "만약 있었다면"을 가정해 더 엄격하게 시험한다.)
    """
    raw = {
        "region_signals": {
            "declared_regions": [
                {
                    "selector": "html>head>script:nth-of-type(2)",
                    "region": "sg",  # 실측(tiktok.com)값 그대로
                    "present": True,
                    "visible": False,  # 실측대로 — script 태그는 visible 하지 않다
                    "hittable": False,
                }
            ],
            "search_inputs": [],
        },
        "endpoint_signals": {
            "declared_endpoints": [{"selector": "body", "endpoint": "sg", "visible": True}],
            "body_endpoint_reached": "sg",
            "article_present": 0,
            "video_playing": False,
        },
        "repeated_structure": {
            "list_container_count": 0,
            "list_item_link_count": 0,
            "hittable_list_item_link_count": 0,
        },
        "primary_action_candidates": [],
    }
    # task 의 정의가 우연히 그 marker 값과 정확히 같다고 최악으로 가정한다.
    task = TaskDefinition("TADV", A.CONTENT_OPEN, "sg", "sg")
    assert detect_area_signal(raw, task, ExecutionMode.REAL_TARGET) is False
    assert detect_endpoint_signal(raw, task, ExecutionMode.REAL_TARGET) is False
    # area 는 실측대로 `visible=False`(script 태그)라 marker 경로조차 원래 이 필드를
    # 위양성으로 못 낸다(구현이 `visible` 을 이미 요구한다) — 이 실측 예시가 area 축에서는
    # 애초에 최악이 아니었다는 뜻이다. 반대로 endpoint 는 `body_endpoint_reached` 가
    # visible 여부와 무관하게 무조건 일치로 처리되므로(구현), **FIXTURE 모드에서는 실제로
    # 위양성이 났을 것**이다 — 그 차이 자체가 D-R0-17("픽스처 PASS 는 실사이트 성립을
    # 증명하지 못한다")의 근거다. picture: marker 경로를 유지하는 한 endpoint 축이
    # area 축보다 구조적으로 더 취약하다.
    assert detect_area_signal(raw, task, ExecutionMode.FIXTURE) is False
    assert detect_endpoint_signal(raw, task, ExecutionMode.FIXTURE) is True


# ══════════════════════════════════════════════════════════════════════════
# 4) Stage 4 resolver — unique 후보만 MAPPED, 나머지는 force-map 없이 AMBIGUOUS_UNRESOLVED
# ══════════════════════════════════════════════════════════════════════════
def test_resolver_maps_the_unique_evidenced_candidate() -> None:
    raw = {
        "region_signals": {
            "search_inputs": [{"visible": True, "in_form": True, "has_submit": True}]
        },
        "repeated_structure": {"hittable_list_item_link_count": 0},
        "primary_action_candidates": [],
    }
    result = resolve_representative_function(raw, [A.QUERY, A.ITEM_DETAIL], target_id="wt-x")
    assert result.outcome == MappingOutcome.MAPPED
    assert result.archetype is A.QUERY
    assert result.region_signal_type is R.FORM_STRUCTURE
    assert result.evidence_slots_used == ("probe.json:raw_features",)
    assert result.candidate_archetypes == (A.QUERY,)


def test_resolver_does_not_force_map_when_two_candidates_both_have_evidence() -> None:
    """검색창(QUERY 증거) 과 list-container 카드(CONTENT_OPEN 증거) 가 한 페이지에 동시에
    있는 흔한 실제 상황 — 첫 매칭을 무조건 고르지 않는다(`01 §6`)."""
    raw = {
        "region_signals": {
            "search_inputs": [{"visible": True, "in_form": True, "has_submit": True}]
        },
        "repeated_structure": {"hittable_list_item_link_count": 3},
        "primary_action_candidates": [],
    }
    result = resolve_representative_function(raw, [A.QUERY, A.CONTENT_OPEN])
    assert result.outcome == MappingOutcome.AMBIGUOUS_UNRESOLVED
    assert result.archetype is None
    assert set(result.candidate_archetypes) == {A.QUERY, A.CONTENT_OPEN}
    assert result.unresolved_reason is not None and "force-map" in result.unresolved_reason


def test_resolver_abstains_when_no_evidence_exists_for_any_candidate() -> None:
    raw = {
        "region_signals": {"search_inputs": []},
        "repeated_structure": {"hittable_list_item_link_count": 0},
        "primary_action_candidates": [],
    }
    result = resolve_representative_function(raw, [A.ITEM_DETAIL, A.FINANCIAL_ACTION_ENTRY])
    assert result.outcome == MappingOutcome.AMBIGUOUS_UNRESOLVED
    assert result.archetype is None
    assert "evidence 없음" in (result.unresolved_reason or "")


def test_resolver_tier2_breaks_search_vs_list_tie_using_primary_surface() -> None:
    """`D-R0-61`(PRECEDENCE_CONTESTED) 경합 유형의 **일반 재현** — 특정 holdout 타깃의
    구체적 candidate 쌍을 쓰지 않는다(제너릭 raw dict 로 구성). 검색창(QUERY 증거)과
    list-container 카드(CONTENT_OPEN 증거)가 한 페이지에 동시에 있을 때, MIN-4 로 정한
    1위 candidate(tier2 "public page primary interaction surface")가 list 소속이면
    CONTENT_OPEN 이 이기고, 진 QUERY 는 `runner_up` 으로 **조용히 삼켜지지 않고 기록**된다."""
    raw = {
        "region_signals": {
            "search_inputs": [{"visible": True, "in_form": True, "has_submit": True}]
        },
        "repeated_structure": {"hittable_list_item_link_count": 2},
        "primary_action_candidates": [
            {
                "selector": "a#card-1",
                "hittable": True,
                "marked_primary": False,
                "dom_order": 0,
                "in_list_container": True,
            },
            {
                "selector": "button#search-submit",
                "hittable": True,
                "marked_primary": False,
                "dom_order": 5,
                "in_list_container": False,
            },
        ],
    }
    result = resolve_representative_function(raw, [A.QUERY, A.CONTENT_OPEN])
    assert result.outcome == MappingOutcome.MAPPED
    assert result.archetype is A.CONTENT_OPEN
    assert result.runner_up is A.QUERY
    assert result.why_not_runner_up is not None and "tier2" in result.why_not_runner_up
    assert any("tier2" in t for t in result.precedence_trace)


def test_resolver_tier2_favors_query_when_search_control_is_the_top_ranked_surface() -> None:
    """위와 반대 방향 — MIN-4 1위가 검색 제출 버튼이면 QUERY 가 이긴다."""
    raw = {
        "region_signals": {
            "search_inputs": [{"visible": True, "in_form": True, "has_submit": True}]
        },
        "repeated_structure": {"hittable_list_item_link_count": 2},
        "primary_action_candidates": [
            {
                "selector": "button#search-submit",
                "hittable": True,
                "marked_primary": False,
                "dom_order": 0,
                "in_list_container": False,
            },
            {
                "selector": "a#card-1",
                "hittable": True,
                "marked_primary": False,
                "dom_order": 5,
                "in_list_container": True,
            },
        ],
    }
    result = resolve_representative_function(raw, [A.QUERY, A.CONTENT_OPEN])
    assert result.outcome == MappingOutcome.MAPPED
    assert result.archetype is A.QUERY
    assert result.runner_up is A.CONTENT_OPEN


def test_resolver_stays_ambiguous_when_tier2_cannot_break_a_tie_between_two_list_archetypes() -> (
    None
):
    """`D-R0-67-2` 시정 이후 — 공유 list 신호 하나만으로는 더 이상 여러 archetype 이
    동시에 evidenced 되지 않는다(그게 이 rework 의 목적이다: CONTENT_OPEN 만 bare list 를
    받는 residual 자리이므로, 아래처럼 순수 list 하나뿐이면 이제 **유일하게** CONTENT_OPEN
    으로 MAPPED 된다 — 더 이상 ambiguous 가 아니다. 별도 assertion 으로 이 개선을 직접
    확인한다).

    이 테스트가 원래 검증하려던 것 — "두 candidate 가 각자의 **전용** family 신호로 진짜
    evidenced 됐는데 tier2 로도 못 가르면 force-map 하지 않는다" — 은 ITEM_DETAIL(price
    pattern)과 COMMUNICATION_ENTRY(compose textarea)를 각자의 신호로 evidence 시켜
    재현한다. 둘 다 tier2 의 "list 계열" 집합에 속해 top surface 가 list 여도 가르지
    못한다(candidate 쌍이 구체적으로 무엇이었는지는 특정 holdout 타깃 값을 쓰지 않는다 —
    `D-R0-61` 경합 4건 중 3건이 사후에 holdout 으로 확인됐다)."""
    bare_list_raw = {
        "region_signals": {"search_inputs": []},
        "repeated_structure": {"hittable_list_item_link_count": 3},
        "primary_action_candidates": [
            {
                "selector": "a#card-1",
                "hittable": True,
                "marked_primary": False,
                "dom_order": 0,
                "in_list_container": True,
            },
        ],
    }
    bare_list_result = resolve_representative_function(
        bare_list_raw, [A.CONTENT_OPEN, A.ITEM_DETAIL]
    )
    assert bare_list_result.outcome == MappingOutcome.MAPPED
    assert bare_list_result.archetype is A.CONTENT_OPEN, (
        "D-R0-67-2 회귀 — bare list 만으로 ITEM_DETAIL 이 다시 co-evidence 되면 안 된다"
    )

    genuinely_contested_raw = {
        "region_signals": {"search_inputs": []},
        "repeated_structure": {"hittable_list_item_link_count": 3},
        "family_signals": {
            "structured_data_types": [],
            "price_pattern_present": True,
            "compose_textarea_present": True,
        },
        "primary_action_candidates": [
            {
                "selector": "a#card-1",
                "hittable": True,
                "marked_primary": False,
                "dom_order": 0,
                "in_list_container": True,
            },
        ],
    }
    result = resolve_representative_function(
        genuinely_contested_raw, [A.ITEM_DETAIL, A.COMMUNICATION_ENTRY]
    )
    assert result.outcome == MappingOutcome.AMBIGUOUS_UNRESOLVED
    assert result.archetype is None
    assert set(result.candidate_archetypes) == {A.ITEM_DETAIL, A.COMMUNICATION_ENTRY}


def test_utility_entry_custom_uri_scheme_control_is_not_counted_as_a_primary_control() -> None:
    """`mplweb.ahnlab.com` 유형(비-holdout, Director 가 명시적으로 다뤄도 된다고 확인함) —
    도구의 유일한 "control"이 `v3mobileplus://` 같은 커스텀 URI 스킴 링크뿐이면 Branch U
    (`D-R0-41`)의 endpoint("primary control이 present/actionable")가 **웹에서는 성립하지
    않는다.** `<a>` 태그는 애초에 `_utility_primary_control_present` 의 candidate 가 아니므로
    (button/input/select/textarea 또는 role=button 만 인정) 이 상황을 **억지로 UTILITY_ENTRY
    로 매핑하지 않는다** — 대신 실제로 존재하는 다른 표면(예: 뉴스 카드 목록)이 있으면 그쪽이
    evidenced 된다."""
    raw_scheme_only = {
        "primary_action_candidates": [
            {
                "selector": "a#open-app",
                "tag": "a",
                "role": None,
                "hittable": True,
                "href": "v3mobileplus://open",
                "marked_primary": False,
                "dom_order": 0,
                "in_list_container": False,
            }
        ],
    }
    task = TaskDefinition("TSCHEME", A.UTILITY_ENTRY, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    assert detect_area_signal(raw_scheme_only, task, ExecutionMode.REAL_TARGET) is False
    assert detect_endpoint_signal(raw_scheme_only, task, ExecutionMode.REAL_TARGET) is False

    # 같은 페이지에 실제로 열리는 뉴스카드(list-container 소속 링크)가 있으면 CONTENT_OPEN
    # 후보는 evidenced 된다 — "성립 불가"를 침묵으로 남기지 않고 다른 candidate 로 드러낸다.
    raw_with_news_cards = {
        **raw_scheme_only,
        "region_signals": {"search_inputs": []},
        "repeated_structure": {"hittable_list_item_link_count": 4},
    }
    result = resolve_representative_function(raw_with_news_cards, [A.UTILITY_ENTRY, A.CONTENT_OPEN])
    assert result.outcome == MappingOutcome.MAPPED
    assert result.archetype is A.CONTENT_OPEN


def test_resolver_never_returns_an_archetype_outside_the_seven() -> None:
    """`D-R0-11` — 신규 archetype 을 만들지 않는다. resolver 산출은 항상 닫힌 7종 안에 있다."""
    raw = {
        "region_signals": {
            "search_inputs": [{"visible": True, "in_form": True, "has_submit": True}]
        },
        "repeated_structure": {"hittable_list_item_link_count": 0},
        "primary_action_candidates": [],
    }
    result = resolve_representative_function(raw, list(A))
    if result.archetype is not None:
        assert result.archetype in set(A)


# ══════════════════════════════════════════════════════════════════════════
# 5) partial depth 보존 + assign_depth_segments NULL 결함 시정 (D-R0-20 · depth.py:212-215)
# ══════════════════════════════════════════════════════════════════════════
def test_partial_depth_is_preserved_when_region_observed_but_endpoint_never_found() -> None:
    """`w2_partial_depth_a/b.html` — 실 DOM list 구조로 region 은 관측되지만(k=0) 두 페이지
    어디에도 endpoint 신호(article/video)가 없어 순환하다 MAX_STATE_REVISITS 로 종료된다.
    NED 는 보존돼야 하고(D-R0-20), IED/MPFED 는 NULL, 그리고 region 관측 이후 step 들은
    `IED` 가 아니라 `UNASSIGNED` 여야 한다(이전 구현은 MPFED=NULL 을 step_count 로 대체해
    `IED` 로 잘못 라벨링했다)."""
    task = TaskDefinition("TPD", A.CONTENT_OPEN, None, None)
    entry, manifest = _scout(
        budget=ScoutBudget(max_activations_per_task=5, max_state_revisits=1, branching_limit=2)
    ).scout(web_target_id="wt-w2-partial", entry_fixture="w2_partial_depth_a.html", task=task)

    assert entry.endpoint_status == "UNRESOLVED"
    assert entry.endpoint_status_detail == "UNRESOLVED_DEPTH_BUDGET_EXCEEDED"
    assert entry.ned == 0  # region 은 살아 있다 — NULL 로 지워지지 않는다
    assert entry.ied is None
    assert entry.mpfed is None
    assert entry.area_signal_status == "OBSERVED"
    assert len(entry.steps) >= 1, (
        "이 fixture 설계는 region 확정 이후에도 탐색이 계속돼야 결함이 드러난다"
    )
    assert all(s.depth_segment == "UNASSIGNED" for s in entry.steps), (
        f"MPFED=NULL 인데 IED 로 라벨링된 step 이 있다(결함 재발): "
        f"{[s.depth_segment for s in entry.steps]}"
    )
    assert manifest is None  # endpoint 미도달 — Freeze 산출물을 만들지 않는다
    assert any("partial depth 보존" in n for n in entry.notes)


def test_assign_depth_segments_does_not_substitute_step_count_for_null_mpfed() -> None:
    """depth.py 단위 시험 — `assign_depth_segments`가 직접 결함을 재현하는 최소 사례.
    구 구현: `m = depth.mpfed if ... else step_count` → step_count 를 상한으로 대체해
    NED 이후 전부 `IED` 로 라벨링했다. 시정 후: `MPFED is None` 이면 NED 이후는 `UNASSIGNED`."""
    depth = DepthResult(
        ned=1,
        ied=None,
        mpfed=None,
        area_signal_status=AreaSignalStatus.OBSERVED,
        endpoint_status=EndpointStatus.UNRESOLVED,
        endpoint_status_detail=None,
        endpoint_reached=0,
    )
    segments = assign_depth_segments(3, depth)
    assert segments == [DepthSegment.NED, DepthSegment.UNASSIGNED, DepthSegment.UNASSIGNED]
    # 구 구현이었다면 [NED, IED, IED] 가 나왔을 것이다 — 그 값과 다름을 명시적으로 대조한다.
    assert segments != [DepthSegment.NED, DepthSegment.IED, DepthSegment.IED]


def test_assign_depth_segments_with_known_mpfed_is_unaffected_by_the_fix() -> None:
    """회귀 방지 — MPFED 가 실제로 확정된 정상 경로는 이 시정으로 바뀌지 않는다."""
    depth = DepthResult(
        ned=2,
        ied=1,
        mpfed=3,
        area_signal_status=AreaSignalStatus.OBSERVED,
        endpoint_status=EndpointStatus.FUNCTION_ENDPOINT_REACHED,
        endpoint_status_detail=None,
        endpoint_reached=1,
    )
    assert assign_depth_segments(3, depth) == [
        DepthSegment.NED,
        DepthSegment.NED,
        DepthSegment.IED,
    ]


# ══════════════════════════════════════════════════════════════════════════
# 6b) T-B-BLK-003(P1, A 결정 대기) — gate_observed 는 고치지 않되, gate→endpoint 승격의
#     근거가 어휘뿐인지 구조 신호를 포함하는지는 구분해 기록한다
# ══════════════════════════════════════════════════════════════════════════
def test_gate_endpoint_promotion_is_flagged_when_basis_is_vocabulary_only() -> None:
    """FINANCIAL_ACTION_ENTRY 는 IDENTITY_VERIFICATION gate 도 endpoint 로 승격한다
    (`ENDPOINT_GATE_KINDS`). "통신사/본인인증" 어휘만 있고 실제 캐리어 선택지·OTP 입력
    필드는 하나도 없는 최악의 경우를 구성해, 그 경로가 vocabulary-only 로 정확히
    식별되는지 확인한다. `classify_gate_kind` 자체의 판정 로직은 바꾸지 않는다
    (`T-B-BLK-003` 은 A 결정 대기 — 이 lane 은 근거를 기록만 한다)."""
    vocab_only = GateSignals(
        text="휴대폰 본인확인은 SKT KT LG U+ 알뜰폰 중 하나를 선택하고 인증번호를 받아 진행합니다",
        # 구조 신호(carrier_option_count/otp_input_count/identity_number_input_count/
        # tel_autocomplete_count/password_input_count/username_autocomplete_count)는 전부 0.
    )
    decision = classify_gate_kind(vocab_only)
    assert decision.resolved and decision.gate_kind is not None
    assert decision.gate_kind.value == "IDENTITY_VERIFICATION"
    assert _gate_basis_is_vocabulary_only(decision) is True


def test_gate_endpoint_promotion_is_not_flagged_when_structural_signal_present() -> None:
    """실제 OTP 입력 필드 등 구조 신호가 있으면 vocabulary-only 가 아니다 — 과탐 방지."""
    structural = GateSignals(text="본인 확인", identity_number_input_count=1, otp_input_count=1)
    decision = classify_gate_kind(structural)
    assert decision.resolved and decision.gate_kind is not None
    assert _gate_basis_is_vocabulary_only(decision) is False


def test_gate_endpoint_promotion_note_appears_on_the_real_fixture_path() -> None:
    """`auth_identity_gate.html`(P-C 기존 회귀 fixture)은 캐리어/OTP 구조 신호를 실제로
    갖고 있으므로 vocabulary-only 로 flag 되면 안 된다 — 과탐 방지의 end-to-end 확인."""
    entry, _ = _scout().scout(
        web_target_id="wt-gate-note",
        entry_fixture="auth_identity_gate.html",
        task=TaskDefinition(
            "TF", A.FINANCIAL_ACTION_ENTRY, None, "FIN", R.GATE_SIGNAL, R.GATE_SIGNAL
        ),
    )
    assert entry.endpoint_status_detail == "ENDPOINT_VIA_AUTH_GATE"
    assert not any("GATE_BASIS_VOCABULARY_ONLY" in n for n in entry.notes)


# ══════════════════════════════════════════════════════════════════════════
# 6) observation truncation caveats — T-B-FINDING-002 강건성
# ══════════════════════════════════════════════════════════════════════════
def test_truncation_caveat_is_recorded_for_item_detail_when_relevant_cap_hit() -> None:
    raw = {
        "probe_truncation": {
            "primary_action_candidates": {"cap": 200, "matched": 214, "truncated": True},
            "accessible_name_sources": {"cap": 300, "matched": 120, "truncated": False},
        }
    }
    task = TaskDefinition("TT1", A.ITEM_DETAIL, None, None)
    caveats = observation_truncation_caveats(raw, task)
    assert len(caveats) == 1
    assert "OBSERVATION_TRUNCATED" in caveats[0]
    assert "primary_action_candidates" in caveats[0]
    assert "accessible_name_sources" not in caveats[0]  # 이건 절단되지 않았다


def test_truncation_caveat_is_silent_when_nothing_relevant_was_truncated() -> None:
    raw = {
        "probe_truncation": {
            "primary_action_candidates": {"cap": 200, "matched": 40, "truncated": False}
        }
    }
    task = TaskDefinition("TT2", A.ITEM_DETAIL, None, None)
    assert observation_truncation_caveats(raw, task) == []


def test_truncation_caveat_ignores_irrelevant_cap_for_query_archetype() -> None:
    """QUERY 는 `search_inputs`(cap 없음)만 쓴다 — `primary_action_candidates` 절단은
    QUERY 판정과 무관하므로 caveat 을 달지 않는다."""
    raw = {
        "probe_truncation": {
            "primary_action_candidates": {"cap": 200, "matched": 250, "truncated": True}
        }
    }
    task = TaskDefinition("TT3", A.QUERY, None, None, R.FORM_STRUCTURE, R.FORM_STRUCTURE)
    assert observation_truncation_caveats(raw, task) == []


# ══════════════════════════════════════════════════════════════════════════
# 7) FIXTURE 회귀 — 기존 marker 경로가 이번 변경으로 죽지 않았다 (D-R0-42)
# ══════════════════════════════════════════════════════════════════════════
def test_marker_path_still_works_in_fixture_mode_for_existing_regression_fixtures() -> None:
    """`depth_path_0.html` 은 실 `<article>` 도 갖고 있어 real detector 로도 통과할 수 있다
    (redundant). marker 전용 경로가 여전히 살아있는지는 `depth_path_1.html`(list 구조는
    real 로도 통과하지만 endpoint 는 marker 전용)로 다시 확인한다 — 이건 기존 `test_pc_*`
    스위트가 이미 전수 검증하므로 여기서는 대표 1건만 재확인한다."""
    task = TaskDefinition("T", A.CONTENT_OPEN, "ARTICLE_LIST_REGION", "ARTICLE_BODY_OPEN")
    entry, manifest = _scout().scout(
        web_target_id="wt-marker-regress", entry_fixture="depth_path_3.html", task=task
    )
    assert entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert (entry.ned, entry.ied, entry.mpfed) == (2, 1, 3)
    assert manifest is not None


# ══════════════════════════════════════════════════════════════════════════
# 8) CAPTCHA presence≠blocking (C-BLOCKER-221347, D-R0-05, D-R0-65 확정) — G1-c
# ══════════════════════════════════════════════════════════════════════════
def _probe_raw(fixture_name: str) -> dict[str, Any]:
    """PROBE_JS 를 fixture 에 직접 실행해 `raw_features` 를 얻는다(FIXTURE 모드, mode 인자 없음)."""
    from playwright.sync_api import sync_playwright

    fixture = FIXTURES / fixture_name
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        try:
            page.goto(f"file://{fixture.resolve()}", wait_until="load")
            page.wait_for_timeout(200)
            probe = page.evaluate(PROBE_JS)
            return probe["raw_features"]
        finally:
            browser.close()


def test_hidden_captcha_iframe_alone_is_not_resolved_as_captcha_gate() -> None:
    """양성 대조군 — `captcha_hidden_iframe_only.html`. iframe 은 raw feature 로는 잡히지만
    (`captcha_iframe_count>0`), `captcha_challenge_active` 는 False 여야 하고 판별기는
    RESOLVED CAPTCHA 를 내면 안 된다(`D-R0-05`: 존재만으로 terminal 아님). `gate_observed()`
    도 이 iframe 만으로는 True 가 되지 않는다 — 이게 빠지면 Scout 가 이 state 를 gate 로
    취급해 탐색이 여기서 멈춘다(정확히 C 가 실측한 결함)."""
    raw = _probe_raw("captcha_hidden_iframe_only.html")
    signals = GateSignals.from_raw(raw)
    assert signals.captcha_iframe_count > 0, "iframe 존재 자체는 raw feature 로 관측돼야 한다"
    assert signals.captcha_challenge_active is False
    decision = classify_gate_kind(signals)
    assert decision.gate_kind is not GateKind.CAPTCHA
    assert gate_observed(raw) is False


def test_visible_active_challenge_without_iframe_is_resolved_as_captcha_gate() -> None:
    """음성 대조군 — `captcha_visible_active_challenge.html`. iframe 이 전혀 없어도
    dialog/aria-modal + captcha 입력/이미지 + viewport 가시성이 전부 있으면 CAPTCHA 로
    RESOLVED 돼야 한다. 이 대조군이 없으면 "iframe 만 안 믿는다"는 구현이 통과해 버리고,
    실제로 막고 있는 challenge 를 놓친다(A 가 지적한 "한 방향만 보면 통과하는" 함정)."""
    raw = _probe_raw("captcha_visible_active_challenge.html")
    signals = GateSignals.from_raw(raw)
    assert signals.captcha_iframe_count == 0, "이 픽스처는 iframe 이 전혀 없다"
    assert signals.captcha_challenge_active is True
    decision = classify_gate_kind(signals)
    assert decision.resolved and decision.gate_kind is GateKind.CAPTCHA
    assert gate_observed(raw) is True


def test_scout_does_not_terminate_on_a_hidden_captcha_iframe() -> None:
    """Scout 통합 — 숨김 iframe 이 있는 랜딩에서 실제로 탐색이 멈추지 않고 실 `<article>`
    endpoint(`w2_real_content_article.html`, marker 없음)까지 도달해야 한다."""
    task = TaskDefinition("TCH1", A.CONTENT_OPEN, None, None)
    entry, _ = _scout().scout(
        web_target_id="wt-captcha-hidden",
        entry_fixture="captcha_hidden_iframe_only.html",
        task=task,
    )
    assert entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert entry.endpoint_status_detail is None
    assert (entry.ned, entry.ied, entry.mpfed) == (0, 1, 1)


def test_scout_terminates_zero_step_on_a_visible_active_captcha_challenge() -> None:
    """Scout 통합 — visible active challenge 는 landing 에서 즉시 CAPTCHA terminal(0-step)
    이어야 한다. 입력 필드를 채우거나 제출하지 않는다(해결·우회 금지, 그대로 유지)."""
    task = TaskDefinition("TCH2", A.ITEM_DETAIL, None, None)
    entry, manifest = _scout().scout(
        web_target_id="wt-captcha-visible",
        entry_fixture="captcha_visible_active_challenge.html",
        task=task,
    )
    assert entry.endpoint_status == "CAPTCHA"
    assert len(entry.steps) == 0
    assert (entry.ned, entry.ied, entry.mpfed) == (None, None, None)
    assert manifest is None


def test_gate_structural_signal_no_longer_keys_on_bare_iframe_presence() -> None:
    """`_gate_structural_signal_present` 가 여전히 `captcha_iframe_count` 를 쓰면 이
    테스트가 실패한다 — 회귀 방지용 화이트박스 확인."""
    from landing_accessibility.engine.l1_engine import _gate_structural_signal_present

    only_iframe = GateSignals(captcha_iframe_count=3, captcha_challenge_active=False)
    assert _gate_structural_signal_present(only_iframe) is False
    active_challenge = GateSignals(captcha_iframe_count=0, captcha_challenge_active=True)
    assert _gate_structural_signal_present(active_challenge) is True


# ══════════════════════════════════════════════════════════════════════════
# 9) D-R0-67-1 — UTILITY catch-all 시정 (single-purpose tool surface 요구)
# ══════════════════════════════════════════════════════════════════════════
def test_utility_entry_requires_a_real_input_widget_not_a_bare_button() -> None:
    """`w2_real_utility_button_only.html` — 버튼 하나뿐이고 입력 위젯이 없다. UTILITY_ENTRY
    로 force-map 되면 안 된다(region/endpoint 둘 다 성립 안 함)."""
    task = TaskDefinition("TUB", A.UTILITY_ENTRY, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    entry, _ = _scout().scout(
        web_target_id="wt-utility-button-only",
        entry_fixture="w2_real_utility_button_only.html",
        task=task,
    )
    assert entry.endpoint_status == "UNRESOLVED"
    assert (entry.ned, entry.ied, entry.mpfed) == (None, None, None)


def test_utility_entry_with_a_real_input_widget_still_succeeds() -> None:
    """`w2_real_utility.html` — 양성 대조(회귀 재확인). 실제 `<input>` 이 있으면 여전히
    성립해야 한다(`utility_input_widgets` 신규 신호 경유)."""
    task = TaskDefinition("TU2B", A.UTILITY_ENTRY, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    entry, _ = _scout().scout(
        web_target_id="wt-utility-input-widget", entry_fixture="w2_real_utility.html", task=task
    )
    assert entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert (entry.ned, entry.ied, entry.mpfed) == (0, 0, 0)


# ══════════════════════════════════════════════════════════════════════════
# 10) D-R0-67-2 — family-specific 판별 신호 (공유 카드 신호 대체 아님)
# ══════════════════════════════════════════════════════════════════════════
def test_item_detail_evidenced_by_product_structured_data_without_marker() -> None:
    """`w2_item_structured_data.html` — Product JSON-LD 만으로 ITEM_DETAIL evidence."""
    task = TaskDefinition("TID", A.ITEM_DETAIL, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    entry, _ = _scout().scout(
        web_target_id="wt-item-structured", entry_fixture="w2_item_structured_data.html", task=task
    )
    assert entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert (entry.ned, entry.ied, entry.mpfed) == (0, 0, 0)


def test_place_lookup_evidenced_by_map_control_without_marker() -> None:
    """`w2_place_map_control.html` — "지도에서 매장 찾기" control 만으로 PLACE_LOOKUP region."""
    raw = _probe_raw("w2_place_map_control.html")
    task = TaskDefinition("TPL", A.PLACE_LOOKUP, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    assert detect_area_signal(raw, task, ExecutionMode.REAL_TARGET) is True


def test_communication_entry_evidenced_by_compose_textarea_without_marker() -> None:
    """`w2_communication_compose.html` — 실 `<textarea>` 만으로 COMMUNICATION_ENTRY 성립."""
    task = TaskDefinition("TCE", A.COMMUNICATION_ENTRY, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    entry, _ = _scout().scout(
        web_target_id="wt-comm-compose", entry_fixture="w2_communication_compose.html", task=task
    )
    assert entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert (entry.ned, entry.ied, entry.mpfed) == (0, 0, 0)


def test_family_signals_do_not_cross_contaminate_other_archetypes() -> None:
    """음성 대조 — Product structured data 만 있는 페이지는 PLACE_LOOKUP/COMMUNICATION_ENTRY
    의 evidence 가 아니다(family 신호가 서로 새지 않는다)."""
    raw = _probe_raw("w2_item_structured_data.html")
    place_task = TaskDefinition("TX1", A.PLACE_LOOKUP, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    comm_task = TaskDefinition(
        "TX2", A.COMMUNICATION_ENTRY, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE
    )
    assert detect_area_signal(raw, place_task, ExecutionMode.REAL_TARGET) is False
    assert detect_area_signal(raw, comm_task, ExecutionMode.REAL_TARGET) is False


def test_bare_list_alone_no_longer_evidences_item_place_or_communication() -> None:
    """`D-R0-67-2` 회귀 방지 — `w2_real_content_list.html`(순수 `<ul><li><a>` 목록, 상품/
    장소/커뮤니티 신호 전혀 없음)은 이제 CONTENT_OPEN 만 evidence 를 받는다."""
    raw = _probe_raw("w2_real_content_list.html")
    for archetype in (A.ITEM_DETAIL, A.PLACE_LOOKUP, A.COMMUNICATION_ENTRY):
        task = TaskDefinition("TX3", archetype, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
        assert detect_area_signal(raw, task, ExecutionMode.REAL_TARGET) is False, archetype
    content_task = TaskDefinition("TX4", A.CONTENT_OPEN, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    assert detect_area_signal(raw, content_task, ExecutionMode.REAL_TARGET) is True


# ══════════════════════════════════════════════════════════════════════════
# 11) D-R0-70 — HITTABLE ≠ ENABLED (presence≠operative, 다섯 번째 사례)
# ══════════════════════════════════════════════════════════════════════════
def test_disabled_search_input_does_not_count_as_area_observed() -> None:
    """`w2_disabled_search_not_area.html` — coordinator 가 명시한 신규 관측의 직접 재현.
    disabled 검색 input + button 만 있는 랜딩은 area OBSERVED 로 계수되면 안 된다."""
    raw = _probe_raw("w2_disabled_search_not_area.html")
    task = TaskDefinition("TDS", A.QUERY, None, None, R.FORM_STRUCTURE, R.FORM_STRUCTURE)
    assert detect_area_signal(raw, task, ExecutionMode.REAL_TARGET) is False


def test_enabled_search_input_still_counts_as_area_observed() -> None:
    """양성 대조 — 동일 구조에서 `disabled` 만 뺀 픽스처는 여전히 area 성립해야 한다.
    한 방향만 보면 '아무것도 성립시키지 않는' 구현도 통과한다(D-R0-65-3) — 이 쌍이 그걸 막는다."""
    raw = _probe_raw("w2_enabled_search_is_area.html")
    task = TaskDefinition("TES", A.QUERY, None, None, R.FORM_STRUCTURE, R.FORM_STRUCTURE)
    assert detect_area_signal(raw, task, ExecutionMode.REAL_TARGET) is True


def test_is_enabled_helper_defaults_true_for_legacy_raw_without_enabled_field() -> None:
    """`enabled` 필드가 없는 구 raw 스냅샷은 결측을 '비활성'으로 단정하지 않는다(하위호환)."""
    from landing_accessibility.engine.l1_engine import _is_enabled

    assert _is_enabled({"hittable": True}) is True
    assert _is_enabled({"hittable": True, "enabled": False}) is False
    assert _is_enabled({"hittable": True, "enabled": True}) is True


# ══════════════════════════════════════════════════════════════════════════
# 12) D-R0-74 — NLP fallback (deterministic ambiguity 이후에만, force-map 금지 유지)
# ══════════════════════════════════════════════════════════════════════════
pytestmark_embedding = pytest.mark.slow


def _skip_if_no_embedding_model() -> None:
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        pytest.skip(
            "sentence-transformers 미설치 환경 — fallback 은 abstain 으로 안전하게 후퇴한다"
        )


def test_nlp_fallback_resolves_a_clearly_distinguishable_query_vs_content_tie() -> None:
    """`D-R0-74-2`(1) 시도 확인 — 명확히 구분되는 두 문맥에서 embedding margin 이 threshold
    를 넘어 정확한 archetype 을 고르는지 sanity check 한다(calibration 에 fallback 발화
    사례가 0건이라 이게 유일한 직접 검증 경로다 — 최종보고에 이 confound 을 명시한다)."""
    _skip_if_no_embedding_model()
    raw_query_like = {
        "viewport": {
            "title": "검색 - 무엇이든 검색해보세요",
            "final_url": "https://example.com/search",
        },
        "primary_action_candidates": [],
        "accessible_name_sources": [{"aria_label": "검색어 입력", "visible_text": None}],
        "region_signals": {"search_inputs": [{"role": "searchbox"}]},
    }
    result = _nlp_fallback_resolve(raw_query_like, (A.QUERY, A.CONTENT_OPEN))
    assert result.resolved is True
    assert result.archetype is A.QUERY
    assert result.margin >= NLP_FALLBACK_MARGIN_THRESHOLD


def test_nlp_fallback_excludes_communication_and_utility_regardless_of_margin() -> None:
    """`D-R0-74-2`(5) — calibration 공백(COMMUNICATION 0건·UTILITY 1건) archetype 은
    margin 과 무관하게 즉시 abstain 한다."""
    raw = {
        "viewport": {"title": "글쓰기 게시판", "final_url": "https://example.com/write"},
        "primary_action_candidates": [],
        "accessible_name_sources": [],
        "region_signals": {"search_inputs": []},
    }
    result = _nlp_fallback_resolve(raw, (A.COMMUNICATION_ENTRY, A.CONTENT_OPEN))
    assert result.resolved is False
    assert "calibration" in result.reason or "COMMUNICATION" in result.reason


def test_nlp_fallback_abstains_below_margin_threshold() -> None:
    """모호한(둘 다 비슷하게 점수가 나오는) 텍스트는 margin 미달로 abstain 해야 한다."""
    _skip_if_no_embedding_model()
    raw_ambiguous = {
        "viewport": {"title": "서비스", "final_url": "https://example.com/"},
        "primary_action_candidates": [],
        "accessible_name_sources": [],
        "region_signals": {"search_inputs": []},
    }
    result = _nlp_fallback_resolve(raw_ambiguous, (A.QUERY, A.CONTENT_OPEN), margin_threshold=0.99)
    assert result.resolved is False
    assert "threshold" in result.reason or "비어있다" in result.reason


def test_resolver_fallback_never_fires_on_the_no_evidence_path() -> None:
    """`evidence 없음`(0건 evidenced) 경로는 fallback 을 절대 타지 않는다 — margin 계산
    조차 시도하지 않는다(precedence_trace 에 `nlp_fallback` 흔적이 없어야 한다)."""
    raw = {
        "region_signals": {"search_inputs": []},
        "repeated_structure": {"hittable_list_item_link_count": 0},
        "primary_action_candidates": [],
    }
    result = resolve_representative_function(
        raw, [A.ITEM_DETAIL, A.FINANCIAL_ACTION_ENTRY], enable_nlp_fallback=True
    )
    assert result.outcome == MappingOutcome.AMBIGUOUS_UNRESOLVED
    assert not any("nlp_fallback" in t for t in result.precedence_trace)


def test_resolver_end_to_end_uses_fallback_when_tier2_cannot_break_a_genuine_tie() -> None:
    """`D-R0-74-2`(3) — rule 이 두 candidate 를 진짜 evidenced 했고 tier2(top surface 없음)
    로도 못 가른 경우에만 fallback 이 개입해 MAPPED 를 낸다. runner_up/why_not_runner_up/
    evidence_slots_used 에 fallback 근거가 남아야 한다."""
    _skip_if_no_embedding_model()
    raw = {
        "viewport": {
            "title": "검색 - 무엇이든 검색해보세요",
            "final_url": "https://example.com/search",
        },
        "region_signals": {
            "search_inputs": [{"visible": True, "in_form": True, "has_submit": True}]
        },
        "repeated_structure": {"hittable_list_item_link_count": 1},
        "primary_action_candidates": [],  # top surface 없음 — tier2 가 못 가른다
        "accessible_name_sources": [{"aria_label": "검색어 입력", "visible_text": None}],
    }
    result = resolve_representative_function(raw, [A.QUERY, A.CONTENT_OPEN])
    assert result.outcome == MappingOutcome.MAPPED
    assert result.archetype is A.QUERY
    assert result.runner_up is A.CONTENT_OPEN
    assert "NLP fallback" in (result.mapping_basis or "")
    assert any("nlp_fallback" in s for s in result.evidence_slots_used)
    assert any("nlp_fallback" in t for t in result.precedence_trace)


def test_resolver_disabling_fallback_restores_pure_rule_dt_behavior() -> None:
    """되돌릴 수 있는 구현 — `enable_nlp_fallback=False` 면 이전(rule-only) 동작 그대로
    AMBIGUOUS_UNRESOLVED 로 남는다."""
    raw = {
        "viewport": {"title": "검색", "final_url": "https://example.com/search"},
        "region_signals": {
            "search_inputs": [{"visible": True, "in_form": True, "has_submit": True}]
        },
        "repeated_structure": {"hittable_list_item_link_count": 1},
        "primary_action_candidates": [],
        "accessible_name_sources": [],
    }
    result = resolve_representative_function(
        raw, [A.QUERY, A.CONTENT_OPEN], enable_nlp_fallback=False
    )
    assert result.outcome == MappingOutcome.AMBIGUOUS_UNRESOLVED
    assert result.archetype is None


def test_place_lookup_no_longer_shares_generic_search_control_with_query() -> None:
    """`D-R0-74` 진단 중 발견한 rule 결함의 회귀 방지 — 일반 검색창(장소 어휘/지도 control
    없음)만으로는 더 이상 PLACE_LOOKUP 이 evidenced 되지 않는다(daangn.com/daum.net/
    google.com/lottemart 4건이 가짜로 tier3-tied 됐던 원인)."""
    raw = {
        "region_signals": {
            "search_inputs": [{"visible": True, "in_form": True, "has_submit": True}]
        },
        "family_signals": {},
        "repeated_structure": {"hittable_list_item_link_count": 0},
        "primary_action_candidates": [],
    }
    task = TaskDefinition("TPLQ", A.PLACE_LOOKUP, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    assert detect_area_signal(raw, task, ExecutionMode.REAL_TARGET) is False
    query_task = TaskDefinition("TPLQ2", A.QUERY, None, None, R.DOM_AX_ROLE, R.DOM_AX_ROLE)
    assert detect_area_signal(raw, query_task, ExecutionMode.REAL_TARGET) is True
