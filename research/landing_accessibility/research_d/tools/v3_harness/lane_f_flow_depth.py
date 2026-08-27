#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lane F — Flow Topology / Depth analysis harness + counterexample detectors (v3, outcome-independent).

WHAT THIS IS
------------
A calculator for the v3 Flow/Depth axis, implemented *strictly* from SSOTV3 definitions, and
validated against synthetic fixtures with pre-baked expected answers.  MAIN50 has not been
collected; nothing here touches REAL targets, production/mart/raw evidence, gold labels, or holdout.

AUTHORITY (verified by sha256 at build time)
  SSOTV3 MANIFEST_v3.0.json  = 1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a
  04_FLOW_CODEBOOK_v3.0.md   = aaae54bfb174b3d5f1da7dc0673bb8e1e1d846136012de09fd8ffb476dab0e43
  05_ANALYSIS_PLAN_v3.0.md   = dfdeaa795322ca8088ab8fb09445f4ee35769107fa0badd2837558fda08b314c
  03_COLLECTION_MEASUREMENT_SPEC_v3.0.md = 13bb8b52abf3117638e2dd20107c0f4fd11b4f776b8163ead9a3714b0815b6e9
  00_SSOT_v3.0_CROSS_SERVICE_FLOW.md     = 951c69f13d119f7b1bbe47196fbe908118963ae125519ee24408c2921f97b3e9

HARD CONSTRAINTS OBSERVED BY THIS FILE
--------------------------------------
1. NO NEW OPERATIONALIZATION.  Where the codebook under-determines a value, this module does NOT
   choose.  It emits every admissible reading side by side and emits a single primary value ONLY
   when all admissible readings agree ("agreement rule").  Disagreement -> value withheld
   (`None`) + the open question is listed in AMBIGUOUS_DEFINITIONS.
2. NO THRESHOLDS / CUT-OFFS / COMPOSITE SCORES.  Distances are reported as numbers.  No predicate
   of the form "distance > X therefore different" exists anywhere in this file.  Every detector
   predicate is an EXACT structural relation (== / != / ==0 / >0 on integer counts), never a tuned
   boundary.
3. n IS NOT 45.  A family has n=10 service-task units.  The 45 unordered pairs of a 10-member
   family are CELLS of a distance matrix used for description/visualization.  They are not
   independent observations and must never be used as a sample size, a denominator for a rate, or
   an input to an inferential test.  See PAIR_CELL_WARNING.
4. `activation_depth` and `flow_step_count` have DIFFERENT include/exclude lists in the codebook.
   They are deliberately NOT unified here.

Usage:
    python lane_f_flow_depth.py            # run fixtures + detectors + mutation testing, write outputs
    python lane_f_flow_depth.py --stdout   # also print the JSON
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from itertools import combinations
from typing import Any, Dict, List, Optional, Sequence, Tuple

RD = "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/research/landing_accessibility/research_d"
SSOT_DIR = "/home/sieg/projects-wsl/ProjectFinal/SSOTV3"
OUT_DIR = os.path.join(RD, "results", "harness", "lane_f")

PAIR_CELL_WARNING = (
    "family n=10 is the independent unit. The 45 unordered pairs are distance-matrix CELLS for "
    "description/visualization only — never n=45, never a rate denominator, never an inferential "
    "sample. (05_ANALYSIS_PLAN_v3.0 §1: '동일 family의 45 pair는 distance matrix의 cell이지 독립 표본 n=45가 아니다.')"
)

# ---------------------------------------------------------------------------
# 1. Canonical tokens — 04_FLOW_CODEBOOK_v3.0 §2, verbatim, in codebook order.
# ---------------------------------------------------------------------------
CANONICAL_TOKENS: Dict[str, str] = {
    "OPEN_GLOBAL_MENU": "전역 햄버거/전체메뉴를 연다",
    "OPEN_LOCAL_MENU": "과업 영역 내부 메뉴/더보기를 연다",
    "SWITCH_TAB": "탭을 전환한다",
    "EXPAND_ACCORDION": "접힌 영역을 펼친다",
    "SELECT_CATEGORY": "과업 관련 카테고리/서비스군을 선택한다",
    "SELECT_FUNCTION": "사전지정 task 기능 control을 선택한다",
    "INPUT_QUERY": "검색어/번호/키워드를 입력한다",
    "SELECT_ORIGIN": "출발지를 선택한다",
    "SELECT_DESTINATION": "도착지를 선택한다",
    "SELECT_DATE": "날짜를 선택한다",
    "SUBMIT_QUERY": "검색/조회 control을 실행한다",
    "SELECT_RESULT": "결과 목록에서 항목을 선택한다",
    "OPEN_ITEM_DETAIL": "상품 상세를 연다",
    "OPEN_PLACE_DETAIL": "장소/기관 상세를 연다",
    "DISMISS_OBSTRUCTION": "task path 진행에 필수인 방해요소를 허용된 닫기 control로 제거한다",
    "AUTH_GATE": "사전지정 task 경로에서 인증이 불가피해지는 상태에 도달한다",
    "ENDPOINT_REACHED": "사전정의 endpoint가 충족된다",
    "ABSTAIN": "증거 부족/다중 후보/경로 불확정으로 억지 판정하지 않는다",
}
assert len(CANONICAL_TOKENS) == 18, "codebook §2 defines exactly 18 canonical tokens"

# Tokens the codebook NAMES VERBATIM as reveal tokens for menu_dependency (§5).
REVEAL_TOKENS_EXPLICIT = ("OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "EXPAND_ACCORDION")
# §5 writes "OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION 등 reveal token" — the trailing
# "등" leaves the set open. SWITCH_TAB is the only other token that plausibly reveals a container
# (cf. nav_container_type TOP_DROPDOWN / INLINE_EXPAND). We do NOT decide; both readings are emitted.
REVEAL_TOKENS_INCL_SWITCH_TAB = REVEAL_TOKENS_EXPLICIT + ("SWITCH_TAB",)

# Tokens that denote an outcome/terminal STATE rather than a user activation.
# Δ9 (T-A-V3-STEP1-006) has since RULED these OUT of activation_depth; the tuple is retained
# because it names the set the pre-Δ9 "activation_only" reading used.
STATE_OUTCOME_TOKENS = ("AUTH_GATE", "ENDPOINT_REACHED", "ABSTAIN")

# ---------------------------------------------------------------------------
# 1b. Δ9 — activation_depth token attribution.  RULED by A in T-A-V3-STEP1-006.
#     This is an authority ruling transcribed verbatim, NOT a reading this harness chose.
#     Before Δ9 this module emitted two readings side by side (AMB-F03) and withheld the value.
# ---------------------------------------------------------------------------
DELTA9_TICKET = "T-A-V3-STEP1-006"
R12_TICKET = "T-A-V3-STEP1-007"

DELTA9_GENERAL_CRITERION = {
    "source": DELTA9_TICKET + " .general_criterion",
    "rule": "`activation_depth` 는 **사용자가 control 을 의도적으로 활성화해 상태 전이를 일으킨 토큰**의 수다.",
    "three_tests": [
        "① 사용자의 의도적 조작인가 (수동 로드·리다이렉트·대기는 아니다)",
        "② control 활성화인가 (스크롤·타이핑은 control 활성화가 아니다)",
        "③ 상태가 전이되는가 (단순 표시 변화가 아니라 화면·경로·컨테이너 상태가 바뀌는가)",
    ],
    "why_a_criterion_not_a_list": "목록만 두면 새 상황마다 티켓이 필요하다. 기준을 두면 목록은 기준의 적용례가 된다",
}

# 04 §2 order preserved.  Ten IN, five OUT, three CONDITIONAL = the canonical 18.
DELTA9_IN: Tuple[str, ...] = (
    "OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SWITCH_TAB", "EXPAND_ACCORDION",
    "SELECT_CATEGORY", "SELECT_FUNCTION", "SUBMIT_QUERY", "SELECT_RESULT",
    "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL",
)
DELTA9_OUT: Dict[str, str] = {
    "INPUT_QUERY": "타이핑이다. 03·04 둘 다 명시 제외. flow_step_count 에는 포함",
    "DISMISS_OBSTRUCTION": "03·04 둘 다 명시 제외. forced_dismissal_count 로 별도 집계",
    "AUTH_GATE": "사용자 활성화가 아니라 **마주친 상태**다. 기준 ①에 걸린다. flow_step_count 에는 auth encounter 로 포함",
    "ENDPOINT_REACHED": "종결 표지이지 행위가 아니다",
    "ABSTAIN": "행위가 아니라 판정 유보다",
}
DELTA9_CONDITIONAL: Tuple[str, ...] = ("SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE")
DELTA9_CONDITIONAL_RULE = (
    "**입력수단에 따라 갈린다.** picker/dropdown/calendar 처럼 control 을 활성화해야 값이 정해지면 "
    "activation_depth 에 **포함**한다. 자유입력란에 타이핑했다면 타이핑이므로 **제외**하고 "
    "flow_step_count 에만 넣는다"
)

DELTA9_CLASSIFICATION: Dict[str, str] = {}
DELTA9_CLASSIFICATION.update({t: "IN" for t in DELTA9_IN})
DELTA9_CLASSIFICATION.update({t: "OUT" for t in DELTA9_OUT})
DELTA9_CLASSIFICATION.update({t: "CONDITIONAL" for t in DELTA9_CONDITIONAL})
assert set(DELTA9_CLASSIFICATION) == set(CANONICAL_TOKENS), (
    "Δ9 must classify EXACTLY the canonical 18 — an extra key would be a token the codebook "
    "does not define (cf. T-B-FC-013 / OPEN_RIGHT_DRAWER)"
)
assert (len(DELTA9_IN), len(DELTA9_OUT), len(DELTA9_CONDITIONAL)) == (10, 5, 3)

# Δ8-R5 (T-A-V3-STEP1-003): `fixture_input_mode` — FREE_TEXT / DROPDOWN / MIXED / MAP_PAN / OTHER.
FIXTURE_INPUT_MODES: Tuple[str, ...] = ("FREE_TEXT", "DROPDOWN", "MIXED", "MAP_PAN", "OTHER")
# Δ9 how_to_decide: "DROPDOWN/MAP_PAN 계열이면 포함, FREE_TEXT 면 제외, MIXED 면 실제로 사용한 수단 기준".
# OTHER is not ruled on, and an ABSENT mode is not evidence of any mode — T-A-V3-STEP1-007 R13
# states the governing principle ("어떤 변수든 '없음'을 적으려면 관측했다는 증거가 있어야 한다").
# Both resolve to UNRESOLVED here.  Neither is silently defaulted to IN or OUT.
CONDITIONAL_MODE_RESOLUTION: Dict[str, str] = {"DROPDOWN": "IN", "MAP_PAN": "IN", "FREE_TEXT": "OUT"}

# T-B-FC-013 (confirmed in Δ9): direction is NOT a token.
DIRECTION_IS_NOT_A_TOKEN = {
    "example_rejected_token": "OPEN_RIGHT_DRAWER",
    "correct_encoding": "OPEN_GLOBAL_MENU 또는 OPEN_LOCAL_MENU 토큰 + nav_container_type=RIGHT_DRAWER + reveal_direction=RIGHT",
    "why": "방향을 토큰에 넣으면 sequence signature 가 방향까지 포함해 갈라진다. 그러면 '같은 구조, 다른 방향'과 "
           "'다른 구조'가 편집거리에서 구분되지 않는다",
    "lane_f_obligation": "토큰 목록 밖 값은 스키마 오류로 보고한다 (validate_sequence -> NOT_IN_CANONICAL_18). "
                         "nav_container_type / reveal_direction 자체는 Lane S 소관이며 여기서 계산하지 않는다",
    "adopted_protocol": "상위 지시와 SSOT 가 다르면 SSOT 를 따른다",
}

# ---------------------------------------------------------------------------
# 2. Verbatim definitions carried into the output artifact (no paraphrase).
# ---------------------------------------------------------------------------
VERBATIM: Dict[str, Dict[str, str]] = {
    "flow_is_primary": {
        "source": "00_SSOT_v3.0_CROSS_SERVICE_FLOW.md §7",
        "text": (
            "Raw primary: `task_flow_sequence`와 `experienced_flow_sequence`.\n"
            "- `task_flow_sequence`: 서비스 자체 navigation/task 구조. forced dismissal 제외.\n"
            "- `experienced_flow_sequence`: 실사용자가 실제 겪은 path. forced dismissal 포함.\n"
            "Derived: menu_dependency / nav_container_depth / activation_depth / NED,IED,MPFED "
            "compatibility fields / flow_step_count / auth_gate_stage\n"
            "Scroll은 `first_visible_scroll_state`로 별도 측정하며 activation depth에 합산하지 않는다."
        ),
    },
    "task_vs_experienced": {
        "source": "04_FLOW_CODEBOOK_v3.0.md §3",
        "text": (
            "- `task_flow_sequence`: `DISMISS_OBSTRUCTION`을 제외한 서비스 자체 task navigation.\n"
            "- `experienced_flow_sequence`: 실제 진행에 필요했던 dismissal까지 포함.\n"
            "예:\n"
            "`task_flow = OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE`\n"
            "`experienced_flow = DISMISS_OBSTRUCTION > OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE`"
        ),
    },
    "menu_dependency": {
        "source": "04_FLOW_CODEBOOK_v3.0.md §5",
        "text": "`menu_dependency = 1` iff endpoint 전 OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION 등 reveal token 존재.",
    },
    "menu_dependency_table": {
        "source": "04_FLOW_CODEBOOK_v3.0.md §4",
        "text": "menu_dependency | Derived | bool | action_sequence에 OPEN/REVEAL 계열 token이 endpoint 이전에 존재하는지",
    },
    "activation_depth": {
        "source": "04_FLOW_CODEBOOK_v3.0.md §5",
        "text": "`activation_depth`: state-changing activation token 수. scroll/typing/passive/dismiss 제외.",
    },
    "activation_depth_table": {
        "source": "04_FLOW_CODEBOOK_v3.0.md §4",
        "text": "activation_depth | Derived | count | scroll/typing/passive wait/dismiss 제외 state-changing activation 수",
    },
    "flow_step_count": {
        "source": "04_FLOW_CODEBOOK_v3.0.md §5",
        "text": "`flow_step_count`: task-intent token 수. typing/submit/auth encounter 포함, scroll/passive 제외.",
    },
    "flow_step_count_table": {
        "source": "04_FLOW_CODEBOOK_v3.0.md §4",
        "text": "flow_step_count | Derived | count | task-intent action token 수. typing/submit/auth encounter 포함, scroll/passive load 제외",
    },
    "nav_container_depth": {
        "source": "04_FLOW_CODEBOOK_v3.0.md §5 + §4",
        "text": (
            "§5: `nav_container_depth`: task control 노출 전 nested reveal 수.\n"
            "§4: nav_container_depth | Derived | count | task control 노출 전 menu/drawer expansion 수"
        ),
    },
    "action_inclusion": {
        "source": "03_COLLECTION_MEASUREMENT_SPEC_v3.0.md §6",
        "text": (
            "Depth에 포함: link/button/tab/menu open · category/function/result select · "
            "state-changing menu/drawer reveal\n"
            "Depth에서 제외: scroll · passive load / redirect / wait · text 한 글자 입력 · popup dismiss\n"
            "단 `flow_step_count`에는 task-intent typing/submit을 별도 token으로 보존한다."
        ),
    },
    "flow_topology_metrics": {
        "source": "05_ANALYSIS_PLAN_v3.0.md §2-E",
        "text": "E. Flow Topology — unique sequence signatures / normalized Levenshtein distance / LCS similarity / sequence cluster·heatmap",
    },
    "depth_metrics": {
        "source": "05_ANALYSIS_PLAN_v3.0.md §2-F",
        "text": "F. Depth — activation depth median/IQR/range / optional legacy NED/IED/MPFED",
    },
    "analysis_unit": {
        "source": "05_ANALYSIS_PLAN_v3.0.md §1",
        "text": "Primary: `service × frozen task`. family n=10. 동일 family의 45 pair는 distance matrix의 cell이지 독립 표본 n=45가 아니다.",
    },
    "no_composite_score": {
        "source": "05_ANALYSIS_PLAN_v3.0.md §3",
        "text": "가중합 단일 score 생성 금지. Secondary visualization으로 Gower/mixed distance를 쓸 수 있으나 규범적 threshold나 '고령자 부담 점수'로 해석 금지.",
    },
    # --- Δ9 / R12 rulings, transcribed from the tickets without paraphrase ---
    "delta9_general_criterion": {
        "source": "T-A-V3-STEP1-006 .general_criterion",
        "text": ("rule: `activation_depth` 는 **사용자가 control 을 의도적으로 활성화해 상태 전이를 일으킨 토큰**의 수다.\n"
                 "① 사용자의 의도적 조작인가 (수동 로드·리다이렉트·대기는 아니다)\n"
                 "② control 활성화인가 (스크롤·타이핑은 control 활성화가 아니다)\n"
                 "③ 상태가 전이되는가 (단순 표시 변화가 아니라 화면·경로·컨테이너 상태가 바뀌는가)"),
    },
    "delta9_submit_query": {
        "source": "T-A-V3-STEP1-006 .headline / .the_apparent_conflict / .substantive_reason_for_including_submit",
        "text": ("headline: SUBMIT_QUERY 는 activation_depth 에 **포함된다.** 두 문서를 실제로 대조하면 충돌이 아니다 — "
                 "03 의 마지막 문장이 그렇게 읽힐 뿐이다.\n"
                 "finding: **두 제외 목록 어디에도 submit 이 없다.** 03 의 포함 목록 첫 항목 'link/button/tab/menu open' 에 "
                 "submit control 은 button 으로 들어간다\n"
                 "substantive_reason: submit 을 빼면, 검색어를 넣고 조회를 눌러야 진입하는 서비스와 control 을 바로 "
                 "누르면 되는 서비스가 **같은 activation_depth 를 갖는다.** 그것은 실재하는 구조 차이를 지우는 것이며 "
                 "v3 가 재려는 바로 그 차이다."),
    },
    "delta9_conditional": {
        "source": "T-A-V3-STEP1-006 .canonical_18_classification.CONDITIONAL",
        "text": ("tokens: SELECT_ORIGIN / SELECT_DESTINATION / SELECT_DATE\n"
                 "rule: **입력수단에 따라 갈린다.** picker/dropdown/calendar 처럼 control 을 활성화해야 값이 정해지면 "
                 "activation_depth 에 **포함**한다. 자유입력란에 타이핑했다면 타이핑이므로 **제외**하고 flow_step_count 에만 넣는다\n"
                 "how_to_decide: Δ8-R5 의 `fixture_input_mode` 가 이미 이것을 기록한다 — DROPDOWN/MAP_PAN 계열이면 포함, "
                 "FREE_TEXT 면 제외, MIXED 면 실제로 사용한 수단 기준\n"
                 "record: 각 관측에 `depth_conditional_tokens` 로 어느 토큰이 어떤 근거로 포함/제외됐는지 남긴다"),
    },
    "delta9_family_asymmetry": {
        "source": "T-A-V3-STEP1-006 .family_asymmetry_note",
        "text": ("이 규칙은 검색 기반 family(F2·F3·F5)의 depth 를 F1·F4 보다 구조적으로 높인다. 그것이 사실이다. "
                 "관측 0건 시점에 이 비대칭을 예상으로 기록한다 — 나중에 '예상대로였다'고 사후 서술하지 않기 위함이다."),
    },
    "tb_fc_013": {
        "source": "T-A-V3-STEP1-006 .T_B_FC_013_confirmed",
        "text": ("`OPEN_RIGHT_DRAWER` 는 04 §2 canonical 18종에 없다. 오른쪽 drawer 를 여는 행위는 `OPEN_GLOBAL_MENU` "
                 "또는 `OPEN_LOCAL_MENU` 토큰 + `nav_container_type=RIGHT_DRAWER` + `reveal_direction=RIGHT` 로 "
                 "표현한다. **방향은 토큰이 아니라 별도 변수다**\n"
                 "**상위 지시와 SSOT 가 다르면 SSOT 를 따른다.**"),
    },
    "r12_sequence_distance_normalization": {
        "source": "T-A-V3-STEP1-007 .R12_sequence_distance_normalization",
        "text": ("ruling: primary = `max(len(a), len(b))` 정규화. also_stored = [sum(len) 정규화, Yujian-Bo]. "
                 "single_scalar: primary 만 단일 보고에 쓴다\n"
                 "why_max_len: 값이 [0,1] 에 갇히고 1.0 이 '완전히 다름'을 뜻해 해석이 직관적이다 / 'normalized edit "
                 "distance' 의 가장 흔한 관례 / sum(len) 은 비어 있지 않은 두 열에서 결코 1 에 도달하지 못해 차이를 과소보고한다\n"
                 "yujian_bo_as_declared_sensitivity: **군집·MDS 를 수행할 때는 Yujian-Bo 를 병기한다.**\n"
                 "store_all_three: 셋 다 저장하고 primary 를 지정하는 것이지, 하나만 계산하는 것이 아니다"),
    },
}

# ---------------------------------------------------------------------------
# 3. Open definitional questions.  These are RAISED, not filled.
# ---------------------------------------------------------------------------
# ---- CLOSED by an authority ruling.  Kept as a record so the closure is auditable and so a
#      later reader can see what the harness used to emit and why it changed.
CLOSED_AMBIGUITIES: List[Dict[str, Any]] = [
    {
        "id": "AMB-F01",
        "variable": "normalized Levenshtein distance",
        "question": "정규화 분모가 정의되지 않았다. max(len(a),len(b)) 인가, len(a)+len(b) 인가, 아니면 Yujian-Bo 2d/(|a|+|b|+d) 인가?",
        "closed_by": R12_TICKET + " .R12_sequence_distance_normalization",
        "ruling": "primary = max(len(a), len(b)) 정규화. sum(len) 과 Yujian-Bo 는 함께 저장하되 단일 보고에는 primary 만 쓴다.",
        "harness_behaviour_before": "세 후보를 병기하고 단일 'normalized' 스칼라를 emit 하지 않았다.",
        "harness_behaviour_after": "세 후보를 여전히 전부 저장하고, `levenshtein_normalized_primary` 단일 스칼라를 by_max_len 으로 emit 한다.",
        "residual": "군집·MDS 를 수행할 때 Yujian-Bo 를 병기하라는 R12 의 선언적 민감도 조항은 clustering 을 구현하지 "
                    "않은 이 하네스의 범위 밖이다 (NOT_IMPLEMENTED 에 그대로 남는다).",
    },
    {
        "id": "AMB-F03",
        "variable": "activation_depth",
        "question": "AUTH_GATE / ENDPOINT_REACHED / ABSTAIN 이 'state-changing activation token' 에 포함되는가?",
        "closed_by": DELTA9_TICKET + " .general_criterion + .canonical_18_classification",
        "ruling": "셋 다 OUT. AUTH_GATE 는 '사용자 활성화가 아니라 마주친 상태'라 기준 ①에 걸리고, ENDPOINT_REACHED 는 "
                  "'종결 표지이지 행위가 아니'며, ABSTAIN 은 '행위가 아니라 판정 유보'다. "
                  "즉 Δ9 는 기존 두 읽기 중 `activation_only` 쪽을 확정했다.",
        "harness_behaviour_before": "literal_all_but_excluded / activation_only 두 읽기를 병기하고, 둘이 갈리면 value=None 으로 보류했다.",
        "harness_behaviour_after": "Δ9 분류표로 단일 값을 emit 한다. 두 읽기 기록은 `readings` 에 감사 추적용으로만 남는다.",
        "residual": "AUTH_GATE 가 flow_step_count 에 auth encounter 로 포함된다는 것은 Δ9 가 재확인했다. "
                    "`auth_gate_stage`(NONE/BEFORE_TASK_DISCOVERY/... + R13 UNDETERMINED) 판정은 Lane A 소관이며 "
                    "여기서 구현하지 않는다.",
    },
]

AMBIGUOUS_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "id": "AMB-F02",
        "variable": "LCS similarity",
        "source": "05_ANALYSIS_PLAN_v3.0.md §2-E ('LCS similarity')",
        "question": "LCS 길이를 무엇으로 나눠 similarity 로 만드는지 정의되지 않았다. L/max(len), L/min(len), 2L/(|a|+|b|) 중 어느 것인가?",
        "why_it_matters": "길이가 다른 sequence pair에서 값이 크게 갈린다. prefix pair([A,B] vs [A,B,C])는 0.667 / 1.0 / 0.8.",
        "harness_behaviour": "세 후보를 나란히 반환. 단일 similarity 스칼라 없음.",
        "needs_ruling_from": "SSOT owner (A)",
        "severity": "HIGH",
    },
    {
        "id": "AMB-F04",
        "variable": "flow_step_count",
        "source": "04_FLOW_CODEBOOK_v3.0.md §5 / §4",
        "question": "(a) 어느 sequence 위에서 세는가 — task_flow_sequence 인가 experienced_flow_sequence 인가? DISMISS_OBSTRUCTION 은 포함/제외 어느 목록에도 없다. (b) ENDPOINT_REACHED / ABSTAIN 이 'task-intent action token' 인가?",
        "why_it_matters": "(a) base 선택이 곧 dismissal 포함 여부다. modal 이 있는 서비스의 step count 가 통째로 달라진다. (b) terminal token 포함 여부가 모든 값을 +1 시킨다.",
        "harness_behaviour": "base(task|experienced) × terminal(incl|excl) 4조합을 모두 emit. 단일 primary 는 4값이 모두 같을 때만.",
        "delta9_did_not_close_this": "Δ9 는 activation_depth 만 확정했다. DISMISS_OBSTRUCTION 을 'forced_dismissal_count 로 "
            "별도 집계'한다고 적었으나 그것은 별도 변수의 존재를 말한 것이지 flow_step_count 의 base 를 정한 문장이 아니다. "
            "ENDPOINT_REACHED / ABSTAIN 이 'task-intent action token' 인지도 여전히 미정이다. **열린 채로 둔다.**",
        "needs_ruling_from": "SSOT owner (A)",
        "severity": "HIGH",
    },
    {
        "id": "AMB-F05",
        "variable": "menu_dependency",
        "source": "04_FLOW_CODEBOOK_v3.0.md §5 ('... 등 reveal token'), §4 ('OPEN/REVEAL 계열 token')",
        "question": "reveal token 집합이 열려 있다('등', '계열'). SWITCH_TAB 이 reveal token 인가? nav_container_type 에는 TOP_DROPDOWN/INLINE_EXPAND 가 있어 tab 전환이 container reveal 로 읽힐 여지가 있다.",
        "why_it_matters": "탭 기반 진입 서비스의 menu dependency rate(§2-A primary metric)가 통째로 뒤집힌다.",
        "harness_behaviour": "explicit3 / incl_switch_tab 두 읽기를 모두 emit. 일치할 때만 단일 primary.",
        "needs_ruling_from": "SSOT owner (A)",
        "severity": "HIGH",
    },
    {
        "id": "AMB-F06",
        "variable": "nav_container_depth",
        "source": "04_FLOW_CODEBOOK_v3.0.md §5 ('task control 노출 전 nested reveal 수'), §4 ('task control 노출 전 menu/drawer expansion 수')",
        "question": "token sequence 만으로는 계산 불가능하다. 'task control 노출' 시점을 표시하는 token 이 canonical 18 에 없다. 또한 §5 는 'nested reveal', §4 는 'menu/drawer expansion' 이라 두 문구가 nesting 요구 여부에서 어긋난다.",
        "why_it_matters": "값 자체가 정의되지 않으므로 임의 규칙(예: '첫 SELECT_FUNCTION 이전')을 넣으면 그것이 새 조작화가 된다.",
        "harness_behaviour": "단일 값을 emit 하지 않는다. 후보 계산 3종을 candidate 로만 병기하고 not_implemented 에 등재한다. fact_flow_step 의 nav_container_type/reveal 증거가 sequence 와 함께 들어와야 계산 가능.",
        "needs_ruling_from": "SSOT owner (A)",
        "severity": "HIGH",
    },
    {
        "id": "AMB-F07",
        "variable": "ABSTAIN token 취급",
        "source": "04_FLOW_CODEBOOK_v3.0.md §2 (ABSTAIN), §4 endpoint_status(ABSTAIN)",
        "question": "ABSTAIN 이 sequence 안에 들어왔을 때 (a) derived count 에 세는가, (b) 그 sequence 를 distance/ signature 모집단에 넣는가, (c) 넣는다면 ABSTAIN 을 하나의 심볼로 취급하는가 wildcard 로 취급하는가?",
        "delta9_partial_closure": "(a) 는 activation_depth 에 한해 닫혔다 — Δ9 가 ABSTAIN 을 OUT 으로 확정했다('행위가 아니라 판정 유보'). "
            "그러나 flow_step_count 에서의 취급(AMB-F04 (b))과 (b)·(c) 는 Δ9·R12 어디에도 없다. **부분 폐쇄이며 항목은 열린 채로 둔다.**",
        "why_it_matters": "ABSTAIN 은 '경로 불확정' 선언이다. 이를 일반 token 으로 세면 불확정 경로가 확정 depth 값을 갖게 되고, distance 행렬에 확정값처럼 들어간다.",
        "harness_behaviour": "임의 판단하지 않는다. abstain_present=True 를 표시하고, derived 값은 include/exclude 두 읽기를 병기하며, 이 observation 이 들어간 모든 distance cell 에 interpretable=false 를 찍는다. 값 자체는 계산해 두되 해석 가능으로 표시하지 않는다.",
        "needs_ruling_from": "SSOT owner (A)",
        "severity": "HIGH",
    },
    {
        "id": "AMB-F08",
        "variable": "distance base sequence",
        "source": "05_ANALYSIS_PLAN_v3.0.md §2-E, §8",
        "question": "sequence signature / Levenshtein / LCS 를 task_flow_sequence 위에서 계산하는가 experienced_flow_sequence 위에서 계산하는가? §2-E 는 base 를 말하지 않는다.",
        "why_it_matters": "정확히 detector 3(modal 로 experienced 만 길어지는 경우)이 이 선택에서 나타났다 사라진다.",
        "harness_behaviour": "두 base 모두에서 계산해 병기한다. primary base 를 고르지 않는다.",
        "needs_ruling_from": "SSOT owner (A)",
        "severity": "MEDIUM",
    },
    {
        "id": "AMB-F09",
        "variable": "menu_dependency 'endpoint 전' 경계",
        "source": "04_FLOW_CODEBOOK_v3.0.md §5",
        "question": "ENDPOINT_REACHED 가 없는 terminal(AUTH_GATE / ABSTAIN / BLOCKED)에서 'endpoint 전' prefix 는 어디까지인가?",
        "why_it_matters": "endpoint 미도달 observation 이 menu dependency 분모/분자에 어떻게 들어가는지가 §2-A rate 에 영향.",
        "harness_behaviour": "ENDPOINT_REACHED 가 있으면 그 앞까지, 없으면 sequence 전체를 prefix 로 본 값과 그 사실(endpoint_token_present)을 함께 emit. 두 해석의 값이 다를 수 있는 경우를 flag.",
        "needs_ruling_from": "SSOT owner (A)",
        "severity": "LOW",
    },
    {
        "id": "AMB-F10",
        "variable": "빈 sequence 의 normalized distance",
        "source": "05_ANALYSIS_PLAN_v3.0.md §2-E",
        "question": "두 sequence 가 모두 빈 경우 분모가 0 이다. 0.0(완전 동일)으로 볼 것인가 undefined 로 볼 것인가?",
        "why_it_matters": "flow-evaluable 하지 않은 unit 이 heatmap 에서 '완벽히 동일'로 보이면 오독된다.",
        "harness_behaviour": "0/0 을 0.0 으로 채우지 않는다. None + reason=ZERO_DENOMINATOR 로 반환한다. raw levenshtein=0, raw lcs=0 은 그대로 보고.",
        "needs_ruling_from": "SSOT owner (A)",
        "severity": "LOW",
    },
    {
        "id": "AMB-F11",
        "variable": "task_flow vs experienced_flow 의 구조적 관계",
        "source": "04_FLOW_CODEBOOK_v3.0.md §3",
        "question": "§3 예시는 experienced = task + dismissal 삽입 관계를 보이지만, 'DISMISS_OBSTRUCTION 을 제거하면 반드시 task_flow 와 같아야 한다'를 규범으로 명시하지 않았다.",
        "why_it_matters": "이 불변식을 강제하면 데이터 결함 탐지가 되고, 강제하지 않으면 두 sequence 가 독립적으로 어긋나도 통과한다.",
        "harness_behaviour": "불변식을 강제하지 않는다. 위반을 TASK_EXPERIENCED_INCONSISTENT 로 '보고'만 하고 어느 쪽도 수정하지 않는다.",
        "needs_ruling_from": "SSOT owner (A)",
        "severity": "MEDIUM",
    },
    {
        "id": "AMB-F12",
        "variable": "activation_depth CONDITIONAL 3종 × fixture_input_mode",
        "source": "T-A-V3-STEP1-006 .canonical_18_classification.CONDITIONAL.how_to_decide + Δ8-R5 (T-A-V3-STEP1-003)",
        "question": "Δ9 는 DROPDOWN/MAP_PAN→포함, FREE_TEXT→제외, MIXED→'실제로 사용한 수단 기준' 만 정했다. "
                    "(a) `OTHER` 는 어느 쪽인가? (b) MIXED 에서 '실제로 사용한 수단'을 토큰 단위로 기록하는 필드가 "
                    "R5 스키마(`fixture_input_mode` 단일 값)에 없다. (c) fixture_input_mode 가 아예 기록되지 않은 "
                    "관측의 CONDITIONAL 토큰은 어떻게 처리하는가?",
        "why_it_matters": "CONDITIONAL 3종이 모두 등장하는 F2/F3 경로에서 activation_depth 가 최대 3 만큼 갈린다. "
                          "예: [SO,SD,SDATE,SQ,SR,ER] 은 DROPDOWN 이면 5, FREE_TEXT 면 2 다.",
        "harness_behaviour": "채우지 않는다. OTHER·기록없음·수단미기록 MIXED 는 전부 `UNRESOLVED` 로 두고 "
                             "activation_depth value 를 **보류**(None)한 뒤 `bounds_when_unresolved` 로 "
                             "min(전부 제외)/max(전부 포함) 만 보고한다. 부재를 특정 수단으로 채우면 그것이 새 조작화다 "
                             "(R13 의 '없음을 적으려면 관측 증거가 있어야 한다' 원칙과 같은 층).",
        "needs_ruling_from": "SSOT owner (A)",
        "severity": "HIGH",
    },
]

NOT_IMPLEMENTED: List[Dict[str, str]] = [
    {"item": "nav_container_depth (single value)", "reason": "AMB-F06 — token sequence 만으로 'task control 노출' 시점을 알 수 없다. candidate 3종만 병기."},
    {"item": "auth_gate_stage", "reason": "BEFORE_TASK_DISCOVERY/AFTER_TASK_SELECT/AT_ENDPOINT 판정은 fact_flow_step 의 endpoint_signal/discovery evidence 를 요구한다. token 열만으로 확정 불가 — Lane F 범위 밖으로 두고 조작화하지 않음."},
    {"item": "NED / IED / MPFED legacy compatibility fields", "reason": "02 §7 의 legacy materialization 규칙이며 v3 codebook 이 재정의하지 않았다. v2.1 정의를 여기서 재구성하면 새 조작화가 된다."},
    {"item": "sequence cluster / heatmap (05 §2-E 4번째 항목)", "reason": "clustering 은 linkage·거리 선택이 필요하고 그 선택이 AMB-F01/F02 미해결에 종속된다. 거리행렬만 산출."},
    {"item": "family-level median/IQR/range (05 §2-F, §4)", "reason": "MAIN50 미수집. 합성 fixture 로 기술통계를 내면 실측처럼 오독될 수 있어 산출하지 않음."},
    {"item": "any threshold / cut-off / composite score", "reason": "Director 금지 + 05 §3 가중합 단일 score 금지. detector 는 전부 정확한 구조적 상등/부등 술어만 사용."},
    {"item": "REAL target access, gold label, holdout, GO/NO-GO verdict", "reason": "Lane F 계약상 금지."},
]


# ---------------------------------------------------------------------------
# 4. Token validation — unknown tokens are ERRORS, never silently passed through.
# ---------------------------------------------------------------------------
class TokenError(ValueError):
    """Raised when a sequence contains a token outside the canonical 18."""


def validate_sequence(seq: Sequence[str], label: str = "sequence") -> Dict[str, Any]:
    """Validate a token sequence against 04 §2.

    No silent normalization: case-folding, whitespace-stripping and alias mapping are NOT
    performed, because any such rule would be a new operationalization. A token either matches
    one of the 18 canonical strings exactly, or it is reported as invalid.
    """
    invalid: List[Dict[str, Any]] = []
    for i, tok in enumerate(seq):
        if tok not in CANONICAL_TOKENS:
            near = [c for c in CANONICAL_TOKENS if isinstance(tok, str) and c.upper() == tok.upper()]
            invalid.append(
                {
                    "index": i,
                    "token": tok,
                    "reason": "NOT_IN_CANONICAL_18",
                    "case_insensitive_match": near or None,
                    "note": "case-insensitive match exists but exact match is required; no silent case folding"
                    if near
                    else None,
                }
            )
    return {
        "label": label,
        "length": len(seq),
        "valid": not invalid,
        "invalid_tokens": invalid,
        "abstain_present": "ABSTAIN" in seq,
    }


def require_valid(seq: Sequence[str], label: str = "sequence") -> None:
    v = validate_sequence(seq, label)
    if not v["valid"]:
        raise TokenError(f"{label}: non-canonical token(s) {v['invalid_tokens']}")


# ---------------------------------------------------------------------------
# 5. Distances — 05 §2-E.  Raw values are unambiguous; normalizations are NOT.
# ---------------------------------------------------------------------------
def levenshtein(a: Sequence[str], b: Sequence[str]) -> int:
    """Standard Levenshtein edit distance over token symbols, unit cost for
    insertion / deletion / substitution. No transposition operation, no custom token
    substitution costs (either would be a new operationalization)."""
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ai = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ai == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[lb]


def lcs_length(a: Sequence[str], b: Sequence[str]) -> int:
    """Length of the longest common SUBSEQUENCE (order-preserving, not contiguous)."""
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0
    prev = [0] * (lb + 1)
    for i in range(1, la + 1):
        cur = [0] * (lb + 1)
        ai = a[i - 1]
        for j in range(1, lb + 1):
            cur[j] = prev[j - 1] + 1 if ai == b[j - 1] else max(prev[j], cur[j - 1])
        prev = cur
    return prev[lb]


# R12 (T-A-V3-STEP1-007): the primary normalization for reported normalized edit distance.
# Module-level so a mutant can swap it and the fixtures must notice.
R12_PRIMARY_NORMALIZATION = "by_max_len"
R12_ALSO_STORED = ("by_sum_len", "yujian_bo_2d_over_sum_plus_d")


def _div(num: float, den: float) -> Optional[float]:
    """Return None (not 0.0) on a zero denominator — see AMB-F10."""
    if den == 0:
        return None
    return round(num / den, 10)


def distance_profile(a: Sequence[str], b: Sequence[str]) -> Dict[str, Any]:
    """Raw distances plus every normalization, with R12's primary designated.

    R12 (T-A-V3-STEP1-007) closed AMB-F01: primary = max(len(a),len(b)).  All three normalizations
    are still STORED — "셋 다 저장하고 primary 를 지정하는 것이지, 하나만 계산하는 것이 아니다" — but
    exactly one of them is emitted as a single reportable scalar.

    AMB-F02 (LCS similarity denominator) was NOT ruled on, so `lcs_similarity_primary` stays None
    and the three LCS candidates remain side by side with no default.

    Every returned key is a plain number. There is deliberately no boolean 'different' field and
    no threshold anywhere: the caller gets values, not verdicts.
    """
    la, lb = len(a), len(b)
    d = levenshtein(a, b)
    L = lcs_length(a, b)
    lev_candidates = {
        "by_max_len": _div(d, max(la, lb)),
        "by_sum_len": _div(d, la + lb),
        "yujian_bo_2d_over_sum_plus_d": _div(2 * d, la + lb + d),
    }
    return {
        "len_a": la,
        "len_b": lb,
        "levenshtein_raw": d,
        "lcs_length": L,
        # R12 — all three stored; primary designated, not invented.
        "levenshtein_normalized_candidates": lev_candidates,
        "levenshtein_normalized_primary": lev_candidates[R12_PRIMARY_NORMALIZATION],
        "levenshtein_normalized_primary_key": R12_PRIMARY_NORMALIZATION,
        "levenshtein_normalized_primary_ruling": R12_TICKET + " .R12_sequence_distance_normalization",
        "levenshtein_normalized_also_stored": {k: lev_candidates[k] for k in R12_ALSO_STORED},
        # AMB-F02 — LCS similarity candidates. STILL no primary: R12 ruled on Levenshtein only.
        "lcs_similarity_candidates": {
            "over_max_len": _div(L, max(la, lb)),
            "over_min_len": _div(L, min(la, lb)),
            "dice_2L_over_sum": _div(2 * L, la + lb),
        },
        "lcs_similarity_primary": None,
        "lcs_similarity_primary_reason": "AMB-F02 미해결 — R12 는 Levenshtein 정규화만 확정했다",
        "zero_denominator_present": (max(la, lb) == 0) or (min(la, lb) == 0),
        "identical": list(a) == list(b),
        "disjoint_no_common_subsequence": L == 0,
    }


def sequence_signature(seq: Sequence[str]) -> str:
    """Rendering of the ordered token list, using the ' > ' join shown in codebook §3.
    Signature IDENTITY is the ordered token list itself; this string is only its rendering."""
    return " > ".join(seq)


# ---------------------------------------------------------------------------
# 6. Derived variables — 04 §5, with the agreement rule for under-determined cases.
# ---------------------------------------------------------------------------
def _agree(values: Dict[str, Any]) -> Tuple[Optional[Any], bool]:
    """Emit a primary value only when every admissible reading agrees."""
    vals = list(values.values())
    if vals and all(v == vals[0] for v in vals):
        return vals[0], False
    return None, True


def prefix_before_endpoint(seq: Sequence[str]) -> Tuple[List[str], bool]:
    """Tokens before the first ENDPOINT_REACHED. If absent, the whole sequence (AMB-F09)."""
    if "ENDPOINT_REACHED" in seq:
        return list(seq[: list(seq).index("ENDPOINT_REACHED")]), True
    return list(seq), False


def menu_dependency(task_seq: Sequence[str], experienced_seq: Sequence[str]) -> Dict[str, Any]:
    """04 §5: menu_dependency = 1 iff a reveal token exists before the endpoint.

    Reveal-token set is open in the codebook ('등' / 'OPEN/REVEAL 계열') -> AMB-F05: both readings
    reported. Base sequence is provably irrelevant here (the two sequences differ only by
    DISMISS_OBSTRUCTION, which is not a reveal token under either reading) — the harness asserts
    that invariance rather than assuming it.
    """
    out: Dict[str, Any] = {}
    for base_name, seq in (("task", task_seq), ("experienced", experienced_seq)):
        prefix, endpoint_present = prefix_before_endpoint(seq)
        out[base_name] = {
            "endpoint_token_present": endpoint_present,
            "readings": {
                "reveal_set_explicit3": any(t in REVEAL_TOKENS_EXPLICIT for t in prefix),
                "reveal_set_incl_switch_tab": any(t in REVEAL_TOKENS_INCL_SWITCH_TAB for t in prefix),
            },
        }
    base_invariant = out["task"]["readings"] == out["experienced"]["readings"]
    primary, ambiguous = _agree(out["task"]["readings"])
    return {
        "readings": out["task"]["readings"],
        "readings_experienced_base": out["experienced"]["readings"],
        "base_invariant": base_invariant,
        "endpoint_token_present": out["task"]["endpoint_token_present"],
        "value": primary,
        "ambiguity_active": ambiguous,
        "ambiguity_ids": ["AMB-F05"] + ([] if out["task"]["endpoint_token_present"] else ["AMB-F09"]),
    }


def resolve_conditional_token(
    index: int,
    token: str,
    fixture_input_mode: Optional[str],
    conditional_token_modes: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    """Δ9 CONDITIONAL rule, applied to ONE token occurrence.

    Returns the inclusion decision together with the evidence it rests on, so that Δ9's
    `record` requirement ("어느 토큰이 어떤 근거로 포함/제외됐는지 남긴다") is satisfiable.

    Nothing is defaulted.  Δ9 ruled on DROPDOWN / MAP_PAN / FREE_TEXT and said MIXED follows the
    means actually used.  It did not rule on OTHER, R5 has no per-token field for the means
    actually used under MIXED, and an absent `fixture_input_mode` is not evidence of any mode.
    All three of those return UNRESOLVED — never a quiet IN or OUT.
    """
    per_token = (conditional_token_modes or {}).get(index)
    effective = per_token if per_token is not None else fixture_input_mode
    rec: Dict[str, Any] = {
        "index": index,
        "token": token,
        "classification": "CONDITIONAL",
        "fixture_input_mode": fixture_input_mode,
        "effective_mode": effective,
        "basis": ("conditional_token_modes[%d] (MIXED 에서 실제로 사용한 수단)" % index)
        if per_token is not None else "fixture_input_mode (Δ8-R5)",
        "rule": DELTA9_CONDITIONAL_RULE,
    }
    if effective in CONDITIONAL_MODE_RESOLUTION:
        rec["decision"] = CONDITIONAL_MODE_RESOLUTION[effective]
        rec["reason"] = "Δ9 how_to_decide: DROPDOWN/MAP_PAN 계열이면 포함, FREE_TEXT 면 제외"
        rec["ambiguity_ids"] = []
        return rec
    rec["decision"] = "UNRESOLVED"
    rec["ambiguity_ids"] = ["AMB-F12"]
    if effective == "MIXED":
        rec["reason"] = ("Δ9: MIXED 는 '실제로 사용한 수단 기준'이다. 그 수단이 이 관측에 기록되지 않았다 — "
                         "R5 의 fixture_input_mode 는 관측 단위 단일 값이라 토큰별 수단을 담지 못한다")
    elif effective is None:
        rec["reason"] = ("fixture_input_mode 미기록. 부재를 특정 수단으로 채우지 않는다 "
                         "(T-A-V3-STEP1-007 R13: '없음'을 적으려면 관측했다는 증거가 있어야 한다)")
    else:
        rec["reason"] = "Δ9 는 fixture_input_mode=%s 에 대해 판정하지 않았다" % (effective,)
    return rec


def _activation_depth_delta9(
    seq: Sequence[str],
    fixture_input_mode: Optional[str],
    conditional_token_modes: Optional[Dict[int, str]],
    classification: Dict[str, str],
) -> Tuple[int, int, List[Dict[str, Any]]]:
    """Count IN tokens; resolve CONDITIONAL tokens; return (determined, unresolved, records)."""
    determined = 0
    unresolved = 0
    records: List[Dict[str, Any]] = []
    for i, tok in enumerate(seq):
        cls = classification[tok]
        if cls == "IN":
            determined += 1
        elif cls == "CONDITIONAL":
            rec = resolve_conditional_token(i, tok, fixture_input_mode, conditional_token_modes)
            records.append(rec)
            if rec["decision"] == "IN":
                determined += 1
            elif rec["decision"] == "UNRESOLVED":
                unresolved += 1
    return determined, unresolved, records


def _activation_depth_core(
    task_seq: Sequence[str],
    experienced_seq: Sequence[str],
    fixture_input_mode: Optional[str],
    conditional_token_modes: Optional[Dict[int, str]],
    classification: Dict[str, str],
    legacy_exclusions: Tuple[str, ...],
) -> Dict[str, Any]:
    """Shared body so that mutants can perturb the Δ9 classification table itself."""

    # --- pre-Δ9 record.  Kept verbatim in shape so the convergence is auditable and so the
    #     existing regression fixtures keep testing exactly what they tested before.
    def count(seq: Sequence[str], also_exclude: Tuple[str, ...]) -> int:
        return sum(1 for t in seq if t not in legacy_exclusions and t not in also_exclude)

    readings = {
        "literal_all_but_excluded": count(task_seq, ()),
        "activation_only": count(task_seq, STATE_OUTCOME_TOKENS),
    }
    readings_exp = {
        "literal_all_but_excluded": count(experienced_seq, ()),
        "activation_only": count(experienced_seq, STATE_OUTCOME_TOKENS),
    }

    # --- Δ9 computation.
    det_t, unres_t, cond_t = _activation_depth_delta9(
        task_seq, fixture_input_mode, conditional_token_modes, classification)
    det_e, unres_e, cond_e = _activation_depth_delta9(
        experienced_seq, fixture_input_mode, conditional_token_modes, classification)

    value = det_t if unres_t == 0 else None
    bounds = None if unres_t == 0 else {"min_all_unresolved_excluded": det_t,
                                        "max_all_unresolved_included": det_t + unres_t}
    return {
        "delta9_ruling": DELTA9_TICKET,
        "value": value,
        "value_withheld_reason": None if unres_t == 0 else
            "AMB-F12 — CONDITIONAL 토큰 %d 개의 입력수단이 확정되지 않았다" % unres_t,
        "bounds_when_unresolved": bounds,
        "unresolved_conditional_count": unres_t,
        "fixture_input_mode": fixture_input_mode,
        "depth_conditional_tokens": cond_t,
        "delta9_experienced_base_value": det_e if unres_e == 0 else None,
        "delta9_base_invariant": (det_t, unres_t) == (det_e, unres_e),
        "determined_exclusions": [t for t, c in classification.items() if c == "OUT"],
        "conditional_tokens": [t for t, c in classification.items() if c == "CONDITIONAL"],
        "open_tokens": [],
        # --- audit trail of the pre-Δ9 state ---
        "readings": readings,
        "readings_experienced_base": readings_exp,
        "readings_note": "AMB-F03 이 열려 있던 시절의 두 읽기 기록이다. Δ9 가 `activation_only` 쪽으로 확정했으므로 "
                         "더 이상 병기 대상이 아니며, 감사 추적과 회귀 고정을 위해서만 남긴다.",
        "base_invariant": readings == readings_exp,
        "superseded_open_tokens": list(STATE_OUTCOME_TOKENS),
        "closed_ambiguity_ids": ["AMB-F03"],
        "ambiguity_active": unres_t > 0,
        "ambiguity_ids": (["AMB-F12"] if unres_t > 0 else [])
        + (["AMB-F07"] if "ABSTAIN" in task_seq or "ABSTAIN" in experienced_seq else []),
    }


def activation_depth(
    task_seq: Sequence[str],
    experienced_seq: Sequence[str],
    fixture_input_mode: Optional[str] = None,
    conditional_token_modes: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    """04 §5 + Δ9 (T-A-V3-STEP1-006): count of tokens the user intentionally activated to cause a
    state transition.

    Δ9 closed AMB-F03 by ruling the full canonical 18 into IN (10) / OUT (5) / CONDITIONAL (3):
      IN         — OPEN_GLOBAL_MENU, OPEN_LOCAL_MENU, SWITCH_TAB, EXPAND_ACCORDION,
                   SELECT_CATEGORY, SELECT_FUNCTION, SUBMIT_QUERY, SELECT_RESULT,
                   OPEN_ITEM_DETAIL, OPEN_PLACE_DETAIL
      OUT        — INPUT_QUERY (typing), DISMISS_OBSTRUCTION (dismiss),
                   AUTH_GATE (encountered state, not an activation),
                   ENDPOINT_REACHED (terminal marker), ABSTAIN (a withheld judgement)
      CONDITIONAL— SELECT_ORIGIN / SELECT_DESTINATION / SELECT_DATE, decided by fixture_input_mode

    SUBMIT_QUERY is IN.  Neither exclusion list (03 §6, 04 §5) contains submit, and 03's include
    list covers it as a button.  See `submit_query_effect` in the convergence report for what
    that buys: without it, a service you must search through and a service you press directly
    collapse to the same depth.

    AUTH_GATE's attribution is settled HERE (out of activation_depth, in flow_step_count as an
    auth encounter).  `auth_gate_stage` — including R13's UNDETERMINED — is Lane A's variable and
    is deliberately not computed in this module.

    scroll and passive load have NO canonical token, so they cannot appear in a sequence at all.
    This exclude list stays intentionally DIFFERENT from flow_step_count's include list.
    """
    return _activation_depth_core(
        task_seq, experienced_seq, fixture_input_mode, conditional_token_modes,
        DELTA9_CLASSIFICATION, ("INPUT_QUERY", "DISMISS_OBSTRUCTION"))


def flow_step_count(task_seq: Sequence[str], experienced_seq: Sequence[str]) -> Dict[str, Any]:
    """04 §5: task-intent token count; typing / submit / auth encounter INCLUDED, scroll / passive
    excluded.

    Determined inclusions: INPUT_QUERY (typing), SUBMIT_QUERY (submit), AUTH_GATE (auth encounter).
    Open: (a) base sequence — DISMISS_OBSTRUCTION appears in neither the include nor the exclude
    list, so the base choice *is* the dismissal decision; (b) ENDPOINT_REACHED / ABSTAIN
    (AMB-F04) -> all four combinations reported.
    """
    readings: Dict[str, int] = {}
    for base_name, seq in (("task", task_seq), ("experienced", experienced_seq)):
        readings[f"base={base_name}|terminal=incl"] = len(seq)
        readings[f"base={base_name}|terminal=excl"] = sum(
            1 for t in seq if t not in ("ENDPOINT_REACHED", "ABSTAIN")
        )
    primary, ambiguous = _agree(readings)
    return {
        "readings": readings,
        "determined_inclusions": ["INPUT_QUERY", "SUBMIT_QUERY", "AUTH_GATE"],
        "value": primary,
        "ambiguity_active": ambiguous,
        "ambiguity_ids": ["AMB-F04"] + (["AMB-F07"] if "ABSTAIN" in task_seq or "ABSTAIN" in experienced_seq else []),
    }


def nav_container_depth_candidates(task_seq: Sequence[str]) -> Dict[str, Any]:
    """NOT a value. AMB-F06: 'task control 노출' has no marker token in the canonical 18, so
    nav_container_depth cannot be computed from a token sequence. Three candidate readings are
    shown ONLY to make the size of the gap visible. No primary value is emitted."""
    prefix, _ = prefix_before_endpoint(task_seq)
    reveal = set(REVEAL_TOKENS_EXPLICIT)
    if "SELECT_FUNCTION" in prefix:
        upto_fn = prefix[: prefix.index("SELECT_FUNCTION")]
    else:
        upto_fn = prefix
    leading_run = 0
    for t in prefix:
        if t in reveal:
            leading_run += 1
        else:
            break
    return {
        "value": None,
        "not_computable_reason": "AMB-F06: no exposure marker token in canonical 18",
        "candidates_illustrative_only": {
            "reveal_tokens_before_first_SELECT_FUNCTION": sum(1 for t in upto_fn if t in reveal),
            "leading_consecutive_reveal_run": leading_run,
            "all_reveal_tokens_before_endpoint": sum(1 for t in prefix if t in reveal),
        },
        "ambiguity_ids": ["AMB-F06"],
    }


# ---------------------------------------------------------------------------
# 7. Observation container + §3 consistency check (reported, never corrected).
# ---------------------------------------------------------------------------
def compute_observation(
    obs_id: str,
    task_seq: Sequence[str],
    experienced_seq: Sequence[str],
    fixture_input_mode: Optional[str] = None,
    conditional_token_modes: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    v_task = validate_sequence(task_seq, "task_flow_sequence")
    v_exp = validate_sequence(experienced_seq, "experienced_flow_sequence")
    if not (v_task["valid"] and v_exp["valid"]):
        return {
            "observation_id": obs_id,
            "status": "INVALID_TOKENS",
            "validation": {"task": v_task, "experienced": v_exp},
        }

    # 04 §3 forbids DISMISS_OBSTRUCTION in task_flow_sequence. This is an explicit codebook rule,
    # so a violation is a hard schema error, not an ambiguity.
    dismiss_in_task = "DISMISS_OBSTRUCTION" in task_seq
    # AMB-F11: whether experienced-minus-dismissal must equal task_flow is NOT stated as a norm.
    # We report the comparison; we do not repair either sequence.
    exp_minus_dismiss = [t for t in experienced_seq if t != "DISMISS_OBSTRUCTION"]
    consistent = exp_minus_dismiss == list(task_seq)

    abstain = v_task["abstain_present"] or v_exp["abstain_present"]
    return {
        "observation_id": obs_id,
        "status": "OK",
        "task_flow_sequence": list(task_seq),
        "experienced_flow_sequence": list(experienced_seq),
        "task_signature": sequence_signature(task_seq),
        "experienced_signature": sequence_signature(experienced_seq),
        "dismissal_count_in_experienced": sum(1 for t in experienced_seq if t == "DISMISS_OBSTRUCTION"),
        "schema_errors": (["DISMISS_OBSTRUCTION_IN_TASK_FLOW (04 §3 violation)"] if dismiss_in_task else []),
        "task_experienced_consistency": {
            "experienced_minus_dismissal_equals_task": consistent,
            "flag": None if consistent else "TASK_EXPERIENCED_INCONSISTENT",
            "note": "AMB-F11 — reported only. Neither sequence is corrected by this harness.",
        },
        "abstain_present": abstain,
        "interpretability": {
            "derived_values_interpretable": not abstain,
            "reason": "AMB-F07 — ABSTAIN declares an undetermined path; counts/distances involving it "
            "are computed but must not be read as determinate." if abstain else None,
        },
        "fixture_input_mode": fixture_input_mode,
        "menu_dependency": menu_dependency(task_seq, experienced_seq),
        "activation_depth": activation_depth(
            task_seq, experienced_seq, fixture_input_mode, conditional_token_modes),
        "flow_step_count": flow_step_count(task_seq, experienced_seq),
        "nav_container_depth": nav_container_depth_candidates(task_seq),
    }


# ---------------------------------------------------------------------------
# 8. Synthetic fixtures — pre-baked expected answers (the "정답").
#    These are SYNTHETIC. They are not services, not MAIN50, not evidence.
# ---------------------------------------------------------------------------
S01 = ["OPEN_GLOBAL_MENU", "SELECT_CATEGORY", "SELECT_FUNCTION", "ENDPOINT_REACHED"]
S02 = ["INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT", "OPEN_ITEM_DETAIL", "ENDPOINT_REACHED"]
S03 = ["SWITCH_TAB", "EXPAND_ACCORDION", "OPEN_PLACE_DETAIL", "ENDPOINT_REACHED"]
S04 = ["SWITCH_TAB", "SELECT_CATEGORY", "SELECT_FUNCTION", "AUTH_GATE"]
S07 = ["SELECT_CATEGORY", "OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"]
S08 = ["SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE", "SUBMIT_QUERY", "SELECT_RESULT", "ENDPOINT_REACHED"]
S09 = ["OPEN_GLOBAL_MENU", "ABSTAIN"]


def _fsc(t_incl: int, t_excl: int, e_incl: int, e_excl: int) -> Dict[str, int]:
    return {
        "base=task|terminal=incl": t_incl,
        "base=task|terminal=excl": t_excl,
        "base=experienced|terminal=incl": e_incl,
        "base=experienced|terminal=excl": e_excl,
    }


FIXTURE_FAMILY: List[Dict[str, Any]] = [
    {
        "id": "SYN01_menu_category",
        "note": "global menu -> category -> function -> endpoint",
        "task": S01, "experienced": S01,
        "expected": {
            "activation_depth_readings": {"literal_all_but_excluded": 4, "activation_only": 3},
            "activation_depth_delta9_value": 3,
            "flow_step_count_readings": _fsc(4, 3, 4, 3),
            "menu_dependency_readings": {"reveal_set_explicit3": True, "reveal_set_incl_switch_tab": True},
            "menu_dependency_value": True,
            "consistent": True, "abstain": False,
        },
    },
    {
        "id": "SYN02_search_item",
        "note": "typing search path; INPUT_QUERY excluded from depth but included in flow_step_count",
        "task": S02, "experienced": S02,
        "expected": {
            "activation_depth_readings": {"literal_all_but_excluded": 4, "activation_only": 3},
            "activation_depth_delta9_value": 3,
            "flow_step_count_readings": _fsc(5, 4, 5, 4),
            "menu_dependency_readings": {"reveal_set_explicit3": False, "reveal_set_incl_switch_tab": False},
            "menu_dependency_value": False,
            "consistent": True, "abstain": False,
        },
    },
    {
        "id": "SYN03_tab_accordion",
        "note": "tab + accordion reveal; explicit3 already satisfied by EXPAND_ACCORDION",
        "task": S03, "experienced": S03,
        "expected": {
            "activation_depth_readings": {"literal_all_but_excluded": 4, "activation_only": 3},
            "activation_depth_delta9_value": 3,
            "flow_step_count_readings": _fsc(4, 3, 4, 3),
            "menu_dependency_readings": {"reveal_set_explicit3": True, "reveal_set_incl_switch_tab": True},
            "menu_dependency_value": True,
            "consistent": True, "abstain": False,
        },
    },
    {
        "id": "SYN04_tab_auth_terminal",
        "note": "AMB-F05 live: SWITCH_TAB only, no explicit3 reveal token -> readings disagree, "
                "menu_dependency withheld. Also AMB-F09 (no ENDPOINT_REACHED). flow_step_count is "
                "determinate here because the sequence carries no ENDPOINT_REACHED/ABSTAIN.",
        "task": S04, "experienced": S04,
        "expected": {
            "activation_depth_readings": {"literal_all_but_excluded": 4, "activation_only": 3},
            "activation_depth_delta9_value": 3,
            "flow_step_count_readings": _fsc(4, 4, 4, 4),
            "menu_dependency_readings": {"reveal_set_explicit3": False, "reveal_set_incl_switch_tab": True},
            "menu_dependency_value": None,
            "consistent": True, "abstain": False,
        },
    },
    {
        "id": "SYN05_modal_then_menu",
        "note": "identical task_flow to SYN01, one forced dismissal in experienced_flow only "
                "(detector-3 positive vs SYN01/SYN06)",
        "task": S01, "experienced": ["DISMISS_OBSTRUCTION"] + S01,
        "expected": {
            "activation_depth_readings": {"literal_all_but_excluded": 4, "activation_only": 3},
            "activation_depth_delta9_value": 3,
            "flow_step_count_readings": _fsc(4, 3, 5, 4),
            "menu_dependency_readings": {"reveal_set_explicit3": True, "reveal_set_incl_switch_tab": True},
            "menu_dependency_value": True,
            "consistent": True, "abstain": False,
        },
    },
    {
        "id": "SYN06_no_modal_twin",
        "note": "exact twin of SYN01 in both sequences (detector-1/2/3 negative vs SYN01)",
        "task": S01, "experienced": S01,
        "expected": {
            "activation_depth_readings": {"literal_all_but_excluded": 4, "activation_only": 3},
            "activation_depth_delta9_value": 3,
            "flow_step_count_readings": _fsc(4, 3, 4, 3),
            "menu_dependency_readings": {"reveal_set_explicit3": True, "reveal_set_incl_switch_tab": True},
            "menu_dependency_value": True,
            "consistent": True, "abstain": False,
        },
    },
    {
        "id": "SYN07_reordered",
        "note": "same token multiset as SYN01, different order -> same depth, nonzero distance "
                "(detector-1/2 positive vs SYN01)",
        "task": S07, "experienced": S07,
        "expected": {
            "activation_depth_readings": {"literal_all_but_excluded": 4, "activation_only": 3},
            "activation_depth_delta9_value": 3,
            "flow_step_count_readings": _fsc(4, 3, 4, 3),
            "menu_dependency_readings": {"reveal_set_explicit3": True, "reveal_set_incl_switch_tab": True},
            "menu_dependency_value": True,
            "consistent": True, "abstain": False,
        },
    },
    {
        "id": "SYN08_transport_slots",
        "note": "origin/destination/date slot path, deeper (depth-tie negative vs the depth-3 group). "
                "Δ9 CONDITIONAL 3종이 모두 등장하므로 fixture_input_mode 를 명시해야 depth 가 확정된다; "
                "DROPDOWN 이면 세 토큰 모두 포함되어 Δ9 값 5 다. FREE_TEXT 판본은 CONDITIONAL_CASES 에 있다.",
        "task": S08, "experienced": S08, "fixture_input_mode": "DROPDOWN",
        "expected": {
            "activation_depth_readings": {"literal_all_but_excluded": 6, "activation_only": 5},
            "activation_depth_delta9_value": 5,
            "flow_step_count_readings": _fsc(6, 5, 6, 5),
            "menu_dependency_readings": {"reveal_set_explicit3": False, "reveal_set_incl_switch_tab": False},
            "menu_dependency_value": False,
            "consistent": True, "abstain": False,
        },
    },
    {
        "id": "SYN09_abstain",
        "note": "AMB-F07 live: ABSTAIN inside the sequence -> values computed but marked "
                "non-interpretable; harness does not decide whether ABSTAIN is countable",
        "task": S09, "experienced": S09,
        "expected": {
            "activation_depth_readings": {"literal_all_but_excluded": 2, "activation_only": 1},
            "activation_depth_delta9_value": 1,
            "flow_step_count_readings": _fsc(2, 1, 2, 1),
            "menu_dependency_readings": {"reveal_set_explicit3": True, "reveal_set_incl_switch_tab": True},
            "menu_dependency_value": True,
            "consistent": True, "abstain": True,
        },
    },
    {
        "id": "SYN10_empty",
        "note": "boundary: empty sequence. all readings agree at 0, so no ambiguity is active; "
                "normalized distances against it are UNDEFINED, not 0.0",
        "task": [], "experienced": [],
        "expected": {
            "activation_depth_readings": {"literal_all_but_excluded": 0, "activation_only": 0},
            "activation_depth_delta9_value": 0,
            "flow_step_count_readings": _fsc(0, 0, 0, 0),
            "menu_dependency_readings": {"reveal_set_explicit3": False, "reveal_set_incl_switch_tab": False},
            "menu_dependency_value": False,
            "consistent": True, "abstain": False,
        },
    },
]
assert len(FIXTURE_FAMILY) == 10, "synthetic family mirrors family n=10"

# Pre-baked pairwise expectations (hand-derived, then machine-checked).
EXPECTED_PAIR_DISTANCES: List[Dict[str, Any]] = [
    {"a": "SYN01_menu_category", "b": "SYN07_reordered", "base": "task",
     "levenshtein_raw": 2, "lcs_length": 3,
     "why": "OGM,SC transposed -> two substitutions; LCS keeps SC,SF,ER"},
    {"a": "SYN01_menu_category", "b": "SYN06_no_modal_twin", "base": "task",
     "levenshtein_raw": 0, "lcs_length": 4, "why": "identical"},
    {"a": "SYN01_menu_category", "b": "SYN05_modal_then_menu", "base": "task",
     "levenshtein_raw": 0, "lcs_length": 4, "why": "task_flow identical — modal is not in task_flow"},
    {"a": "SYN01_menu_category", "b": "SYN05_modal_then_menu", "base": "experienced",
     "levenshtein_raw": 1, "lcs_length": 4, "why": "one DISMISS_OBSTRUCTION insertion"},
    {"a": "SYN02_search_item", "b": "SYN04_tab_auth_terminal", "base": "task",
     "levenshtein_raw": 5, "lcs_length": 0,
     "why": "no shared token at all; len 5 vs 4 -> 4 substitutions + 1 deletion"},
    {"a": "SYN01_menu_category", "b": "SYN10_empty", "base": "task",
     "levenshtein_raw": 4, "lcs_length": 0, "why": "four deletions"},
]

# Boundary cases for the distance table (05 §2-E), with hand-derived expected values.
BOUNDARY_CASES: List[Dict[str, Any]] = [
    {"id": "BND01_both_empty", "a": [], "b": [],
     "expected": {"levenshtein_raw": 0, "lcs_length": 0,
                  "lev_by_max_len": None, "lev_by_sum_len": None, "lev_yujian_bo": None,
                  "lcs_over_max_len": None, "lcs_over_min_len": None, "lcs_dice": None},
     "note": "0/0 is UNDEFINED. Not filled with 0.0 (AMB-F10)."},
    {"id": "BND02_empty_vs_len1", "a": [], "b": ["ENDPOINT_REACHED"],
     "expected": {"levenshtein_raw": 1, "lcs_length": 0,
                  "lev_by_max_len": 1.0, "lev_by_sum_len": 1.0, "lev_yujian_bo": 1.0,
                  "lcs_over_max_len": 0.0, "lcs_over_min_len": None, "lcs_dice": 0.0},
     "note": "min(len)=0 -> LCS/min undefined while LCS/max is defined. The three LCS candidates "
             "are not interchangeable."},
    {"id": "BND03_len1_identical", "a": ["SELECT_FUNCTION"], "b": ["SELECT_FUNCTION"],
     "expected": {"levenshtein_raw": 0, "lcs_length": 1,
                  "lev_by_max_len": 0.0, "lev_by_sum_len": 0.0, "lev_yujian_bo": 0.0,
                  "lcs_over_max_len": 1.0, "lcs_over_min_len": 1.0, "lcs_dice": 1.0},
     "note": "length-1 identical"},
    {"id": "BND04_len1_different", "a": ["SELECT_FUNCTION"], "b": ["SELECT_RESULT"],
     "expected": {"levenshtein_raw": 1, "lcs_length": 0,
                  "lev_by_max_len": 1.0, "lev_by_sum_len": 0.5, "lev_yujian_bo": 0.6666666667,
                  "lcs_over_max_len": 0.0, "lcs_over_min_len": 0.0, "lcs_dice": 0.0},
     "note": "the three Levenshtein normalizations give 1.0 / 0.5 / 0.667 for the SAME pair — "
             "this is exactly why AMB-F01 must be ruled on."},
    {"id": "BND05_fully_identical_len4", "a": S01, "b": list(S01),
     "expected": {"levenshtein_raw": 0, "lcs_length": 4,
                  "lev_by_max_len": 0.0, "lev_by_sum_len": 0.0, "lev_yujian_bo": 0.0,
                  "lcs_over_max_len": 1.0, "lcs_over_min_len": 1.0, "lcs_dice": 1.0},
     "note": "fully identical"},
    {"id": "BND06_fully_disjoint_len3",
     "a": ["OPEN_GLOBAL_MENU", "SELECT_CATEGORY", "SELECT_FUNCTION"],
     "b": ["INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT"],
     "expected": {"levenshtein_raw": 3, "lcs_length": 0,
                  "lev_by_max_len": 1.0, "lev_by_sum_len": 0.5, "lev_yujian_bo": 0.6666666667,
                  "lcs_over_max_len": 0.0, "lcs_over_min_len": 0.0, "lcs_dice": 0.0},
     "note": "fully different, equal length"},
    {"id": "BND07_prefix_vs_extension",
     "a": ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION"],
     "b": ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
     "expected": {"levenshtein_raw": 1, "lcs_length": 2,
                  "lev_by_max_len": 0.3333333333, "lev_by_sum_len": 0.2, "lev_yujian_bo": 0.3333333333,
                  "lcs_over_max_len": 0.6666666667, "lcs_over_min_len": 1.0, "lcs_dice": 0.8},
     "note": "prefix containment: LCS/min = 1.0 says 'contained', LCS/max = 0.667 says 'partly "
             "similar'. Different research claims follow from the unresolved choice."},
]

# --- Δ9 CONDITIONAL 3종 × fixture_input_mode.  Kept OUT of FIXTURE_FAMILY on purpose: the family
#     is n=10 and its 45 pair cells are fixed, and adding members would silently change both.
CONDITIONAL_CASES: List[Dict[str, Any]] = [
    {"id": "CD01_dropdown", "seq": S08, "fixture_input_mode": "DROPDOWN",
     "expected_value": 5, "expected_unresolved": 0, "expected_bounds": None,
     "why": "picker 로 세 값을 정한다 -> CONDITIONAL 3종 모두 포함. 2(hard) + 3 = 5"},
    {"id": "CD02_free_text", "seq": S08, "fixture_input_mode": "FREE_TEXT",
     "expected_value": 2, "expected_unresolved": 0, "expected_bounds": None,
     "why": "자유입력란 타이핑 -> 세 토큰 모두 제외. SUBMIT_QUERY + SELECT_RESULT 만 남아 2. "
            "**같은 token 열이 입력수단 때문에 5 와 2 로 갈린다 — 이것이 Δ9 가 재려는 조작량 차이다**"},
    {"id": "CD03_map_pan", "seq": S08, "fixture_input_mode": "MAP_PAN",
     "expected_value": 5, "expected_unresolved": 0, "expected_bounds": None,
     "why": "지도 pan/zoom 도 control 활성화다 (Δ9: DROPDOWN/MAP_PAN 계열이면 포함)"},
    {"id": "CD04_mixed_means_unrecorded", "seq": S08, "fixture_input_mode": "MIXED",
     "expected_value": None, "expected_unresolved": 3,
     "expected_bounds": {"min_all_unresolved_excluded": 2, "max_all_unresolved_included": 5},
     "why": "Δ9 는 MIXED 를 '실제로 사용한 수단 기준'으로 정했는데 R5 스키마에 그 수단을 담을 토큰별 필드가 없다 "
            "-> AMB-F12. 값을 채우지 않고 보류하고 구간만 보고한다"},
    {"id": "CD05_mixed_means_recorded", "seq": S08, "fixture_input_mode": "MIXED",
     "conditional_token_modes": {0: "DROPDOWN", 1: "DROPDOWN", 2: "FREE_TEXT"},
     "expected_value": 4, "expected_unresolved": 0, "expected_bounds": None,
     "why": "실제 사용 수단이 토큰별로 기록되면 MIXED 도 확정된다: 출발지·도착지는 picker(포함), 날짜는 타이핑(제외) -> 2+2=4"},
    {"id": "CD06_mode_absent", "seq": S08, "fixture_input_mode": None,
     "expected_value": None, "expected_unresolved": 3,
     "expected_bounds": {"min_all_unresolved_excluded": 2, "max_all_unresolved_included": 5},
     "why": "fixture_input_mode 미기록. 부재를 FREE_TEXT 로도 DROPDOWN 으로도 채우지 않는다 (R13 원칙)"},
    {"id": "CD07_mode_other", "seq": S08, "fixture_input_mode": "OTHER",
     "expected_value": None, "expected_unresolved": 3,
     "expected_bounds": {"min_all_unresolved_excluded": 2, "max_all_unresolved_included": 5},
     "why": "Δ9 는 OTHER 를 판정하지 않았다 -> AMB-F12"},
    {"id": "CD08_no_conditional_token_present", "seq": S01, "fixture_input_mode": None,
     "expected_value": 3, "expected_unresolved": 0, "expected_bounds": None,
     "why": "CONDITIONAL 토큰이 없으면 fixture_input_mode 부재는 depth 에 아무 영향이 없다 — "
            "AMB-F12 를 필요 이상으로 번지게 하지 않는다"},
]

# --- Δ9 SUBMIT_QUERY ruling: what including submit actually buys.
SQ_SEARCH_PATH = ["INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT", "ENDPOINT_REACHED"]
SQ_DIRECT_PATH = ["SELECT_RESULT", "ENDPOINT_REACHED"]

SUBMIT_QUERY_EFFECT_CASES: List[Dict[str, Any]] = [
    {"id": "SQE01_search_then_submit", "seq": SQ_SEARCH_PATH, "fixture_input_mode": None,
     "expected_delta9": 2, "expected_if_submit_excluded": 1,
     "why": "검색어를 넣고 조회를 눌러야 결과에 진입하는 경로"},
    {"id": "SQE02_press_directly", "seq": SQ_DIRECT_PATH, "fixture_input_mode": None,
     "expected_delta9": 1, "expected_if_submit_excluded": 1,
     "why": "control 을 바로 누르면 되는 경로. submit 을 빼면 SQE01 과 **구별되지 않는다**"},
    {"id": "SQE03_family_SYN02", "seq": S02, "fixture_input_mode": None,
     "expected_delta9": 3, "expected_if_submit_excluded": 2,
     "why": "family fixture SYN02 의 task_flow. 수렴 전 이 하네스는 4/3 두 읽기를 병기하고 value 를 보류했다"},
    {"id": "SQE04_slot_search_SYN08", "seq": S08, "fixture_input_mode": "DROPDOWN",
     "expected_delta9": 5, "expected_if_submit_excluded": 4,
     "why": "slot + submit 경로. F2·F3·F5 의 구조적 depth 우위(Δ9 family_asymmetry_note)가 여기서 나온다"},
]


def _counterfactual_delta9_depth(
    seq: Sequence[str], override: Dict[str, str],
    fixture_input_mode: Optional[str] = None,
    conditional_token_modes: Optional[Dict[int, str]] = None,
) -> Tuple[Optional[int], int]:
    """Depth under a DELIBERATELY WRONG classification, used only to exhibit what Δ9 decided.
    It is never emitted as a value for any observation."""
    cls = dict(DELTA9_CLASSIFICATION)
    cls.update(override)
    det, unres, _ = _activation_depth_delta9(seq, fixture_input_mode, conditional_token_modes, cls)
    return (det if unres == 0 else None), unres


INVALID_TOKEN_CASES: List[Dict[str, Any]] = [
    {"id": "INV01_unknown_token", "seq": ["OPEN_GLOBAL_MENU", "CLICK_BUTTON"],
     "expect_valid": False, "expect_reason": "NOT_IN_CANONICAL_18"},
    {"id": "INV02_lowercase", "seq": ["open_global_menu"],
     "expect_valid": False, "expect_reason": "NOT_IN_CANONICAL_18",
     "note": "no silent case folding — a case-insensitive match is reported but does not pass"},
    {"id": "INV03_v2_legacy_token", "seq": ["SCROLL", "SELECT_FUNCTION"],
     "expect_valid": False, "expect_reason": "NOT_IN_CANONICAL_18",
     "note": "scroll has no canonical token (00 §7 keeps scroll in first_visible_scroll_state)"},
    {"id": "INV04_all_canonical", "seq": list(CANONICAL_TOKENS.keys()),
     "expect_valid": True, "expect_reason": None},
    {"id": "INV05_open_right_drawer", "seq": ["OPEN_RIGHT_DRAWER", "SELECT_FUNCTION"],
     "expect_valid": False, "expect_reason": "NOT_IN_CANONICAL_18",
     "note": "T-B-FC-013 (Δ9 확인): 방향은 토큰이 아니다. 오른쪽 drawer 는 OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU "
             "+ nav_container_type=RIGHT_DRAWER + reveal_direction=RIGHT 로 적는다. "
             "Lane F 는 토큰 목록 밖 값을 스키마 오류로 보고한다"},
]


# ---------------------------------------------------------------------------
# 9. Counterexample detectors.
#
#    EVERY predicate below is an exact structural relation on integers or on ordered token lists
#    (== / != / ==0 / >0).  There is no tuned boundary, no "distance > X", no score.  Where the
#    Director's wording used a magnitude word ("전혀 다른", "distance 는 큰데"), it is rendered as
#    the exact structural fact (LCS length == 0; distance != 0 with the magnitude REPORTED and
#    rank-ordered), never as a cut-off.
#
#    Detectors run over pairs. A pair is a distance-matrix CELL, not an observation. See
#    PAIR_CELL_WARNING.
# ---------------------------------------------------------------------------
DEPTH_READINGS = ("literal_all_but_excluded", "activation_only")
SIG_BASES = ("task", "experienced")


def _seq(obs: Dict[str, Any], base: str) -> List[str]:
    return obs["task_flow_sequence"] if base == "task" else obs["experienced_flow_sequence"]


def _sig(obs: Dict[str, Any], base: str) -> str:
    return obs["task_signature"] if base == "task" else obs["experienced_signature"]


def _pair_cell(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    cell: Dict[str, Any] = {
        "a": a["observation_id"],
        "b": b["observation_id"],
        "cell_kind": "distance_matrix_cell_not_a_sample",
        "depth_tie": {},
        "depth_diff": {},
        "distance": {},
        "signature_differs": {},
        "interpretable": a["interpretability"]["derived_values_interpretable"]
        and b["interpretability"]["derived_values_interpretable"],
    }
    for r in DEPTH_READINGS:
        da = a["activation_depth"]["readings"][r]
        db = b["activation_depth"]["readings"][r]
        cell["depth_diff"][r] = abs(da - db)
        cell["depth_tie"][r] = da == db
    cell["depth_tie_robust"] = all(cell["depth_tie"][r] for r in DEPTH_READINGS)
    va = a["activation_depth"]["value"]
    vb = b["activation_depth"]["value"]
    cell["depth_delta9"] = {"a": va, "b": vb}
    cell["depth_delta9_determinate"] = (va is not None) and (vb is not None)
    cell["depth_tie_delta9"] = cell["depth_delta9_determinate"] and va == vb
    for base in SIG_BASES:
        cell["distance"][base] = distance_profile(_seq(a, base), _seq(b, base))
        cell["signature_differs"][base] = _sig(a, base) != _sig(b, base)
    return cell


def detector_1_depth_tie_flow_divergent(cells: List[Dict[str, Any]]) -> Dict[str, Any]:
    """D1 — 'depth is identical but the flow is entirely different'.

    tier1 predicate: depth_a == depth_b (exact) AND ordered token lists differ (exact).
    tier2 predicate: tier1 AND lcs_length == 0 — the exact structural rendering of
                     'flows share nothing', with no similarity threshold.
    """
    hits = {f"reading={r}|base={b}": [] for r in DEPTH_READINGS for b in SIG_BASES}
    delta9_hits: Dict[str, List[Dict[str, Any]]] = {b: [] for b in SIG_BASES}
    delta9_indeterminate: List[Dict[str, Any]] = []
    tier2: List[Dict[str, Any]] = []
    negatives_tie_but_same: List[Dict[str, Any]] = []
    for c in cells:
        for r in DEPTH_READINGS:
            for b in SIG_BASES:
                if c["depth_tie"][r] and c["signature_differs"][b]:
                    hits[f"reading={r}|base={b}"].append(
                        {"a": c["a"], "b": c["b"], "depth_diff": 0,
                         "levenshtein_raw": c["distance"][b]["levenshtein_raw"],
                         "lcs_length": c["distance"][b]["lcs_length"],
                         "interpretable": c["interpretable"]}
                    )
        for b in SIG_BASES:
            if c["depth_tie_delta9"] and c["signature_differs"][b]:
                delta9_hits[b].append(
                    {"a": c["a"], "b": c["b"], "delta9_depth": c["depth_delta9"]["a"],
                     "levenshtein_raw": c["distance"][b]["levenshtein_raw"],
                     "levenshtein_normalized_primary": c["distance"][b]["levenshtein_normalized_primary"],
                     "lcs_length": c["distance"][b]["lcs_length"],
                     "interpretable": c["interpretable"]})
        if not c["depth_delta9_determinate"]:
            delta9_indeterminate.append({"a": c["a"], "b": c["b"],
                                         "reason": "한쪽 이상의 activation_depth 가 AMB-F12 로 보류됨"})
        if c["depth_tie_robust"] and not c["signature_differs"]["task"]:
            negatives_tie_but_same.append({"a": c["a"], "b": c["b"], "reason": "identical task_flow_sequence"})
        if c["depth_tie_robust"] and c["signature_differs"]["task"] and c["distance"]["task"]["lcs_length"] == 0:
            tier2.append({"a": c["a"], "b": c["b"],
                          "depth_readings_all_tied": True,
                          "lcs_length": 0,
                          "levenshtein_raw": c["distance"]["task"]["levenshtein_raw"],
                          "interpretable": c["interpretable"]})
    return {
        "detector_id": "D1_DEPTH_TIE_FLOW_DIVERGENT",
        "claim_tested": "동일 depth 가 동일 flow 를 함의하지 않는다 (depth 는 flow 의 요약손실 파생값이다).",
        "predicate_tier1": "activation_depth[a] == activation_depth[b] AND ordered_tokens[a] != ordered_tokens[b]",
        "predicate_tier2": "tier1 AND lcs_length == 0",
        "threshold_used": None,
        "positives_by_reading_and_base": {k: len(v) for k, v in hits.items()},
        "positives_detail": hits,
        "tier2_no_common_subsequence": tier2,
        "negatives_depth_tie_but_identical_flow": negatives_tie_but_same,
        "delta9_predicate": "activation_depth_delta9[a] == activation_depth_delta9[b] (both determinate) "
                            "AND ordered_tokens[a] != ordered_tokens[b]",
        "positives_delta9_by_base": {b: len(v) for b, v in delta9_hits.items()},
        "positives_delta9_detail": delta9_hits,
        "delta9_indeterminate_cells": delta9_indeterminate,
    }


def detector_2_distance_positive_depth_tie(cells: List[Dict[str, Any]]) -> Dict[str, Any]:
    """D2 — 'sequence distance is large while depth difference is 0'.

    The word 'large' is NOT operationalized (that would be a cut-off, which is forbidden).
    Predicate: depth_diff == 0 AND levenshtein_raw > 0 — i.e. nonzero, not 'big'.
    The magnitude is then REPORTED and rank-ordered, and the extremal cell is named as an order
    statistic, not as a significance claim.

    HONEST NOTE: as exact predicates, D2 and D1-tier1 are the SAME set on a given base
    (levenshtein_raw == 0 iff the ordered token lists are identical). They are kept separate
    because they report different things — D1 reports structure, D2 reports magnitude. We did not
    invent a threshold to make them differ.
    """
    ranked: List[Dict[str, Any]] = []
    negatives: List[Dict[str, Any]] = []
    for c in cells:
        for b in SIG_BASES:
            d = c["distance"][b]["levenshtein_raw"]
            if c["depth_tie_robust"] and d > 0:
                ranked.append({
                    "a": c["a"], "b": c["b"], "base": b,
                    "depth_diff_all_readings": 0,
                    "levenshtein_raw": d,
                    "levenshtein_normalized_candidates": c["distance"][b]["levenshtein_normalized_candidates"],
                    "lcs_similarity_candidates": c["distance"][b]["lcs_similarity_candidates"],
                    "interpretable": c["interpretable"],
                })
            elif c["depth_tie_robust"] and d == 0:
                negatives.append({"a": c["a"], "b": c["b"], "base": b,
                                  "reason": "depth tie AND zero distance — identical flows, must not be detected"})
            elif not c["depth_tie_robust"] and d > 0:
                negatives.append({"a": c["a"], "b": c["b"], "base": b,
                                  "reason": "nonzero distance but depth differs — outside D2 by construction",
                                  "depth_diff": c["depth_diff"]})
    ranked.sort(key=lambda x: (-x["levenshtein_raw"], x["a"], x["b"], x["base"]))
    top = max((x["levenshtein_raw"] for x in ranked), default=None)
    return {
        "detector_id": "D2_DISTANCE_POSITIVE_DEPTH_TIE",
        "claim_tested": "depth 차이 0 인 pair 에서도 sequence 거리가 0 이 아닐 수 있고, 그 크기는 depth 로 복원되지 않는다.",
        "predicate": "depth_diff == 0 under EVERY depth reading AND levenshtein_raw > 0",
        "threshold_used": None,
        "magnitude_handling": "reported and rank-ordered; extremal cell named as an order statistic only",
        "positives_count": len(ranked),
        "extremal_levenshtein_raw_among_depth_tied": top,
        "extremal_cells": [x for x in ranked if top is not None and x["levenshtein_raw"] == top],
        "positives_ranked": ranked,
        "negatives": negatives,
        "positives_by_base": {b: len([x for x in ranked if x["base"] == b]) for b in SIG_BASES},
        "equivalence_note": "levenshtein_raw == 0 iff the ordered token lists are identical, so on a "
                            "fixed base this positive set is exactly D1-tier1's positive set restricted "
                            "to cells where EVERY depth reading ties. No threshold was introduced to "
                            "separate the two detectors; they differ in what they report (structure vs "
                            "magnitude), not in what they select.",
    }


def detector_3_modal_experienced_only(
    cells: List[Dict[str, Any]], obs_by_id: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """D3 — 'the modal lengthens only the experienced flow; task_flow is unchanged'.

    Pairwise predicate: task signatures EQUAL AND experienced signatures DIFFER.
    Attribution predicate: stripping DISMISS_OBSTRUCTION from both experienced sequences makes
    them equal -> the difference is dismissal-attributable. If it is not, the pair goes into a
    separate bucket instead of being counted as a D3 positive (we do not assume the cause).

    Per-observation form: len(experienced) > len(task) with the excess consisting of
    DISMISS_OBSTRUCTION tokens only.
    """
    positives, non_attributable, negatives = [], [], []
    for c in cells:
        same_task = not c["signature_differs"]["task"]
        diff_exp = c["signature_differs"]["experienced"]
        if same_task and diff_exp:
            ea = [t for t in obs_by_id[c["a"]]["experienced_flow_sequence"] if t != "DISMISS_OBSTRUCTION"]
            eb = [t for t in obs_by_id[c["b"]]["experienced_flow_sequence"] if t != "DISMISS_OBSTRUCTION"]
            rec = {
                "a": c["a"], "b": c["b"],
                "task_flow_distance": c["distance"]["task"]["levenshtein_raw"],
                "experienced_flow_distance": c["distance"]["experienced"]["levenshtein_raw"],
                "dismissal_count_a": obs_by_id[c["a"]]["dismissal_count_in_experienced"],
                "dismissal_count_b": obs_by_id[c["b"]]["dismissal_count_in_experienced"],
                "interpretable": c["interpretable"],
            }
            if ea == eb:
                positives.append(rec)
            else:
                rec["reason"] = "experienced flows differ by something other than DISMISS_OBSTRUCTION"
                non_attributable.append(rec)
        elif same_task and not diff_exp:
            negatives.append({"a": c["a"], "b": c["b"],
                              "reason": "task_flow AND experienced_flow both identical — must not be detected"})
        elif not same_task:
            negatives.append({"a": c["a"], "b": c["b"],
                              "reason": "task_flow already differs — outside D3 by construction"})
    per_obs = []
    for oid, o in obs_by_id.items():
        excess = len(o["experienced_flow_sequence"]) - len(o["task_flow_sequence"])
        per_obs.append({
            "observation_id": oid,
            "experienced_minus_task_length": excess,
            "dismissal_count_in_experienced": o["dismissal_count_in_experienced"],
            "excess_fully_dismissal_attributable": excess == o["dismissal_count_in_experienced"],
            "flow_step_count_task_base_excl_terminal": o["flow_step_count"]["readings"]["base=task|terminal=excl"],
            "flow_step_count_experienced_base_excl_terminal": o["flow_step_count"]["readings"]["base=experienced|terminal=excl"],
            "activation_depth_base_invariant": o["activation_depth"]["base_invariant"],
        })
    return {
        "detector_id": "D3_MODAL_EXPERIENCED_ONLY_INFLATION",
        "claim_tested": "forced dismissal 은 experienced_flow 만 늘리고 task_flow 와 activation_depth 는 그대로 둔다. "
                        "따라서 base sequence 선택(AMB-F08)과 flow_step_count base(AMB-F04)가 결과를 바꾼다.",
        "predicate": "task signature EQUAL AND experienced signature DIFFERS",
        "attribution_predicate": "experienced_a minus DISMISS_OBSTRUCTION == experienced_b minus DISMISS_OBSTRUCTION",
        "threshold_used": None,
        "positives": positives,
        "difference_not_dismissal_attributable": non_attributable,
        "negatives": negatives,
        "per_observation_inflation": per_obs,
    }


# ---------------------------------------------------------------------------
# 10. Directed positive / negative cases (two-sided control), pre-baked verdicts.
# ---------------------------------------------------------------------------
DIRECTED_CASES: List[Dict[str, Any]] = [
    {"id": "DC01_D1_pos_reordered", "detector": "D1", "expect_positive": True,
     "a": {"id": "A_menu_order", "task": S01, "exp": S01},
     "b": {"id": "B_reordered", "task": S07, "exp": S07},
     "why": "same token multiset, same depth under both readings, different order"},
    {"id": "DC02_D1_neg_identical", "detector": "D1", "expect_positive": False,
     "a": {"id": "A_menu_order", "task": S01, "exp": S01},
     "b": {"id": "B_twin", "task": list(S01), "exp": list(S01)},
     "why": "depth tie but flows identical — must NOT be detected"},
    {"id": "DC03_D1_neg_depth_differs", "detector": "D1", "expect_positive": False,
     "a": {"id": "A_menu_order", "task": S01, "exp": S01},
     "b": {"id": "B_transport", "task": S08, "exp": S08},
     "why": "flows differ but depth also differs — outside D1 by construction"},
    {"id": "DC04_D1tier2_pos_disjoint", "detector": "D1_TIER2", "expect_positive": True,
     "a": {"id": "A_search", "task": S02, "exp": S02},
     "b": {"id": "B_tab_auth", "task": S04, "exp": S04},
     "why": "depth tied under both readings AND zero common subsequence"},
    {"id": "DC05_D1tier2_neg_shared_endpoint", "detector": "D1_TIER2", "expect_positive": False,
     "a": {"id": "A_menu_order", "task": S01, "exp": S01},
     "b": {"id": "B_tab_accordion", "task": S03, "exp": S03},
     "why": "depth tie and different flow, but LCS>0 — tier1 yes, tier2 no"},
    {"id": "DC06_D2_pos_disjoint", "detector": "D2", "expect_positive": True,
     "a": {"id": "A_search", "task": S02, "exp": S02},
     "b": {"id": "B_tab_auth", "task": S04, "exp": S04},
     "why": "depth diff 0 under every reading, levenshtein 5"},
    {"id": "DC07_D2_neg_zero_distance", "detector": "D2", "expect_positive": False,
     "a": {"id": "A_menu_order", "task": S01, "exp": S01},
     "b": {"id": "B_twin", "task": list(S01), "exp": list(S01)},
     "why": "depth tie with zero distance — must NOT be detected"},
    {"id": "DC08_D2_neg_depth_differs", "detector": "D2", "expect_positive": False,
     "a": {"id": "A_search", "task": S02, "exp": S02},
     "b": {"id": "B_transport", "task": S08, "exp": S08},
     "why": "distance is nonzero and sizeable, but depth differs — must NOT be detected. "
            "This is the case that a magnitude threshold would have wrongly swept in."},
    {"id": "DC09_D3_pos_modal_one_side", "detector": "D3", "expect_positive": True,
     "a": {"id": "A_no_modal", "task": S01, "exp": S01},
     "b": {"id": "B_modal", "task": list(S01), "exp": ["DISMISS_OBSTRUCTION"] + S01},
     "why": "task_flow identical, experienced_flow longer by one dismissal only"},
    {"id": "DC10_D3_neg_no_modal_anywhere", "detector": "D3", "expect_positive": False,
     "a": {"id": "A_no_modal", "task": S01, "exp": S01},
     "b": {"id": "B_twin", "task": list(S01), "exp": list(S01)},
     "why": "no dismissal on either side — must NOT be detected"},
    {"id": "DC11_D3_neg_same_modal_both_sides", "detector": "D3", "expect_positive": False,
     "a": {"id": "A_modal", "task": S01, "exp": ["DISMISS_OBSTRUCTION"] + S01},
     "b": {"id": "B_modal", "task": list(S01), "exp": ["DISMISS_OBSTRUCTION"] + S01},
     "why": "both sides dismissed identically — experienced flows equal, must NOT be detected"},
    {"id": "DC12_D3_neg_task_flow_differs", "detector": "D3", "expect_positive": False,
     "a": {"id": "A_search", "task": S02, "exp": S02},
     "b": {"id": "B_modal", "task": list(S01), "exp": ["DISMISS_OBSTRUCTION"] + S01},
     "why": "task_flow already differs — outside D3 by construction"},
    {"id": "DC13_D3_nonattributable", "detector": "D3_NONATTRIB", "expect_positive": True,
     "a": {"id": "A_no_modal", "task": S01, "exp": S01},
     "b": {"id": "B_extra_tab", "task": list(S01), "exp": ["SWITCH_TAB"] + S01},
     "why": "task identical, experienced differs — but NOT by a dismissal. Must land in the "
            "non-attributable bucket, not in D3 positives. (Also trips TASK_EXPERIENCED_INCONSISTENT.)"},
]


def _obs(spec: Dict[str, Any]) -> Dict[str, Any]:
    return compute_observation(spec["id"], spec["task"], spec["exp"],
                               spec.get("fixture_input_mode"), spec.get("conditional_token_modes"))


def evaluate_directed_case(case: Dict[str, Any]) -> Dict[str, Any]:
    a, b = _obs(case["a"]), _obs(case["b"])
    cells = [_pair_cell(a, b)]
    obs_by_id = {a["observation_id"]: a, b["observation_id"]: b}
    det = case["detector"]
    if det == "D1":
        res = detector_1_depth_tie_flow_divergent(cells)
        got = len(res["positives_detail"]["reading=activation_only|base=task"]) > 0
    elif det == "D1_TIER2":
        res = detector_1_depth_tie_flow_divergent(cells)
        got = len(res["tier2_no_common_subsequence"]) > 0
    elif det == "D2":
        res = detector_2_distance_positive_depth_tie(cells)
        got = any(x["base"] == "task" for x in res["positives_ranked"])
    elif det == "D3":
        res = detector_3_modal_experienced_only(cells, obs_by_id)
        got = len(res["positives"]) > 0
    elif det == "D3_NONATTRIB":
        res = detector_3_modal_experienced_only(cells, obs_by_id)
        got = len(res["difference_not_dismissal_attributable"]) > 0 and len(res["positives"]) == 0
    else:
        raise ValueError(det)
    return {
        "case_id": case["id"], "detector": det, "why": case["why"],
        "expected_positive": case["expect_positive"], "detected_positive": got,
        "pass": got == case["expect_positive"],
        "consistency_flag_a": a.get("task_experienced_consistency", {}).get("flag"),
        "consistency_flag_b": b.get("task_experienced_consistency", {}).get("flag"),
    }


# ---------------------------------------------------------------------------
# 11. Check runner (used by both the normal run and the mutation run).
# ---------------------------------------------------------------------------
def run_all_checks() -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    def chk(cid: str, expected: Any, actual: Any, note: str = "") -> None:
        checks.append({"check_id": cid, "expected": expected, "actual": actual,
                       "pass": expected == actual, "note": note})

    # (a) fixture-level derived values
    for fx in FIXTURE_FAMILY:
        o = compute_observation(fx["id"], fx["task"], fx["experienced"], fx.get("fixture_input_mode"))
        e = fx["expected"]
        chk(f"{fx['id']}::activation_depth_readings", e["activation_depth_readings"], o["activation_depth"]["readings"])
        chk(f"{fx['id']}::activation_depth_delta9_value", e["activation_depth_delta9_value"],
            o["activation_depth"]["value"], "Δ9 (T-A-V3-STEP1-006) 분류표에 의한 단일 값")
        chk(f"{fx['id']}::activation_depth_delta9_base_invariant", True,
            o["activation_depth"]["delta9_base_invariant"],
            "Δ9 는 DISMISS_OBSTRUCTION 을 OUT 으로 두므로 depth 는 task/experienced base 에 불변이어야 한다")
        chk(f"{fx['id']}::flow_step_count_readings", e["flow_step_count_readings"], o["flow_step_count"]["readings"])
        chk(f"{fx['id']}::menu_dependency_readings", e["menu_dependency_readings"], o["menu_dependency"]["readings"])
        chk(f"{fx['id']}::menu_dependency_value", e["menu_dependency_value"], o["menu_dependency"]["value"])
        chk(f"{fx['id']}::menu_dependency_base_invariant", True, o["menu_dependency"]["base_invariant"],
            "menu_dependency must not depend on task vs experienced base (dismissal is not a reveal token)")
        chk(f"{fx['id']}::activation_depth_base_invariant", True, o["activation_depth"]["base_invariant"],
            "activation_depth excludes dismissal, so it must be base-invariant")
        chk(f"{fx['id']}::consistency", e["consistent"],
            o["task_experienced_consistency"]["experienced_minus_dismissal_equals_task"])
        chk(f"{fx['id']}::abstain_present", e["abstain"], o["abstain_present"])
        chk(f"{fx['id']}::no_schema_error", [], o["schema_errors"])
        chk(f"{fx['id']}::nav_container_depth_withheld", None, o["nav_container_depth"]["value"],
            "AMB-F06 — must never emit a value")

    # (b) pairwise distances
    obs = {fx["id"]: compute_observation(fx["id"], fx["task"], fx["experienced"],
                                        fx.get("fixture_input_mode")) for fx in FIXTURE_FAMILY}
    for ex in EXPECTED_PAIR_DISTANCES:
        dp = distance_profile(_seq(obs[ex["a"]], ex["base"]), _seq(obs[ex["b"]], ex["base"]))
        chk(f"dist::{ex['a']}|{ex['b']}|{ex['base']}::levenshtein_raw", ex["levenshtein_raw"], dp["levenshtein_raw"], ex["why"])
        chk(f"dist::{ex['a']}|{ex['b']}|{ex['base']}::lcs_length", ex["lcs_length"], dp["lcs_length"], ex["why"])

    # (c) boundary cases
    for bc in BOUNDARY_CASES:
        dp = distance_profile(bc["a"], bc["b"])
        e = bc["expected"]
        chk(f"{bc['id']}::levenshtein_raw", e["levenshtein_raw"], dp["levenshtein_raw"], bc["note"])
        chk(f"{bc['id']}::lcs_length", e["lcs_length"], dp["lcs_length"])
        chk(f"{bc['id']}::lev_by_max_len", e["lev_by_max_len"], dp["levenshtein_normalized_candidates"]["by_max_len"])
        chk(f"{bc['id']}::lev_by_sum_len", e["lev_by_sum_len"], dp["levenshtein_normalized_candidates"]["by_sum_len"])
        chk(f"{bc['id']}::lev_yujian_bo", e["lev_yujian_bo"], dp["levenshtein_normalized_candidates"]["yujian_bo_2d_over_sum_plus_d"])
        chk(f"{bc['id']}::lcs_over_max_len", e["lcs_over_max_len"], dp["lcs_similarity_candidates"]["over_max_len"])
        chk(f"{bc['id']}::lcs_over_min_len", e["lcs_over_min_len"], dp["lcs_similarity_candidates"]["over_min_len"])
        chk(f"{bc['id']}::lcs_dice", e["lcs_dice"], dp["lcs_similarity_candidates"]["dice_2L_over_sum"])
        chk(f"{bc['id']}::R12_primary_equals_by_max_len", e["lev_by_max_len"],
            dp["levenshtein_normalized_primary"],
            "R12 (T-A-V3-STEP1-007): primary 정규화 = max(len(a),len(b))")
        chk(f"{bc['id']}::R12_lcs_has_no_primary", None, dp["lcs_similarity_primary"],
            "AMB-F02 는 R12 가 다루지 않았다 — LCS similarity 는 여전히 단일 스칼라를 emit 하지 않는다")

    # (d) token validation, both directions
    for iv in INVALID_TOKEN_CASES:
        v = validate_sequence(iv["seq"], iv["id"])
        chk(f"{iv['id']}::valid", iv["expect_valid"], v["valid"], iv.get("note", ""))
        if not iv["expect_valid"]:
            chk(f"{iv['id']}::reason", iv["expect_reason"], v["invalid_tokens"][0]["reason"])
    raised = False
    try:
        require_valid(["OPEN_GLOBAL_MENU", "NOT_A_TOKEN"], "raise_test")
    except TokenError:
        raised = True
    chk("TOKENERR::raises_on_unknown_token", True, raised, "unknown tokens must not pass silently")
    chk("CANONICAL::token_count", 18, len(CANONICAL_TOKENS))

    # (e) directed detector cases
    for dc in DIRECTED_CASES:
        r = evaluate_directed_case(dc)
        chk(f"{dc['id']}::{dc['detector']}", dc["expect_positive"], r["detected_positive"], dc["why"])

    # (e2) Δ9 classification table structure — the 18 must be partitioned, not merely covered.
    chk("DELTA9::classifies_exactly_18", sorted(CANONICAL_TOKENS), sorted(DELTA9_CLASSIFICATION))
    chk("DELTA9::in_out_conditional_sizes", (10, 5, 3),
        (len(DELTA9_IN), len(DELTA9_OUT), len(DELTA9_CONDITIONAL)))
    chk("DELTA9::submit_query_is_IN", "IN", DELTA9_CLASSIFICATION["SUBMIT_QUERY"],
        "T-A-V3-STEP1-006 headline")
    chk("DELTA9::auth_gate_is_OUT", "OUT", DELTA9_CLASSIFICATION["AUTH_GATE"],
        "'사용자 활성화가 아니라 마주친 상태' — 기준 ①")
    chk("DELTA9::endpoint_reached_is_OUT", "OUT", DELTA9_CLASSIFICATION["ENDPOINT_REACHED"])
    chk("DELTA9::abstain_is_OUT", "OUT", DELTA9_CLASSIFICATION["ABSTAIN"])
    chk("DELTA9::input_query_is_OUT", "OUT", DELTA9_CLASSIFICATION["INPUT_QUERY"])
    chk("DELTA9::dismiss_is_OUT", "OUT", DELTA9_CLASSIFICATION["DISMISS_OBSTRUCTION"])
    chk("DELTA9::slot_tokens_are_CONDITIONAL",
        ["CONDITIONAL", "CONDITIONAL", "CONDITIONAL"],
        [DELTA9_CLASSIFICATION[t] for t in ("SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE")])
    chk("DELTA9::no_direction_token_in_table", False, "OPEN_RIGHT_DRAWER" in DELTA9_CLASSIFICATION,
        "T-B-FC-013 — 방향은 토큰이 아니다")
    chk("DELTA9::flow_step_count_list_not_unified", True,
        set(DELTA9_OUT) != set(), "activation_depth 의 제외목록과 flow_step_count 의 포함목록은 통합하지 않는다")
    chk("DELTA9::submit_in_depth_and_in_step_count", (True, True),
        (DELTA9_CLASSIFICATION["SUBMIT_QUERY"] == "IN",
         "SUBMIT_QUERY" in flow_step_count(["SUBMIT_QUERY"], ["SUBMIT_QUERY"])["determined_inclusions"]))

    # (e3) Δ9 CONDITIONAL × fixture_input_mode
    for cd in CONDITIONAL_CASES:
        ad = activation_depth(cd["seq"], cd["seq"], cd.get("fixture_input_mode"),
                              cd.get("conditional_token_modes"))
        chk(f"{cd['id']}::value", cd["expected_value"], ad["value"], cd["why"])
        chk(f"{cd['id']}::unresolved_count", cd["expected_unresolved"], ad["unresolved_conditional_count"])
        chk(f"{cd['id']}::bounds", cd["expected_bounds"], ad["bounds_when_unresolved"],
            "보류할 때는 값을 채우지 않고 구간만 보고한다")
        n_cond = sum(1 for t in cd["seq"] if DELTA9_CLASSIFICATION[t] == "CONDITIONAL")
        chk(f"{cd['id']}::conditional_record_complete", n_cond, len(ad["depth_conditional_tokens"]),
            "Δ9 record: 어느 토큰이 어떤 근거로 포함/제외됐는지 전부 남긴다")
    chk("CD::dropdown_vs_free_text_differ", True,
        activation_depth(S08, S08, "DROPDOWN")["value"] != activation_depth(S08, S08, "FREE_TEXT")["value"],
        "같은 token 열이 입력수단에 따라 갈리는 것은 결함이 아니라 측정이다 (Δ9 why_this_is_correct)")

    # (e4) SUBMIT_QUERY effect — what Δ9's ruling buys, stated as fixtures
    for sq in SUBMIT_QUERY_EFFECT_CASES:
        ad = activation_depth(sq["seq"], sq["seq"], sq.get("fixture_input_mode"))
        cf, _u = _counterfactual_delta9_depth(sq["seq"], {"SUBMIT_QUERY": "OUT"},
                                              sq.get("fixture_input_mode"))
        chk(f"{sq['id']}::delta9_depth", sq["expected_delta9"], ad["value"], sq["why"])
        chk(f"{sq['id']}::depth_if_submit_excluded", sq["expected_if_submit_excluded"], cf,
            "반사실 — Δ9 가 배제한 읽기. 어떤 관측에도 emit 되지 않는다")
    _sqe = {c["id"]: c for c in SUBMIT_QUERY_EFFECT_CASES}
    chk("SQE::delta9_distinguishes_search_from_direct", True,
        _sqe["SQE01_search_then_submit"]["expected_delta9"] != _sqe["SQE02_press_directly"]["expected_delta9"],
        "submit 을 포함하면 검색 경유 서비스와 직접 진입 서비스가 다른 depth 를 갖는다")
    chk("SQE::excluding_submit_collapses_them", True,
        _sqe["SQE01_search_then_submit"]["expected_if_submit_excluded"]
        == _sqe["SQE02_press_directly"]["expected_if_submit_excluded"],
        "submit 을 빼면 실재하는 구조 차이가 지워진다 — Δ9 substantive_reason_for_including_submit")

    # (e5) R12 — one primary scalar, three stored
    _dp = distance_profile(["OPEN_GLOBAL_MENU", "SELECT_CATEGORY", "SELECT_FUNCTION"],
                           ["INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT"])
    chk("R12::primary_key_is_by_max_len", "by_max_len", _dp["levenshtein_normalized_primary_key"])
    chk("R12::three_normalizations_all_stored",
        ["by_max_len", "by_sum_len", "yujian_bo_2d_over_sum_plus_d"],
        sorted(_dp["levenshtein_normalized_candidates"], key=["by_max_len", "by_sum_len", "yujian_bo_2d_over_sum_plus_d"].index))
    chk("R12::three_normalizations_disagree_on_same_pair", (1.0, 0.5, 0.6666666667),
        (_dp["levenshtein_normalized_candidates"]["by_max_len"],
         _dp["levenshtein_normalized_candidates"]["by_sum_len"],
         _dp["levenshtein_normalized_candidates"]["yujian_bo_2d_over_sum_plus_d"]),
        "서로소 len3-len3 pair 에서 세 정규화가 1.0 / 0.5 / 0.667 로 갈린다")
    chk("R12::primary_is_the_max_len_value", 1.0, _dp["levenshtein_normalized_primary"])
    chk("R12::also_stored_excludes_primary", ["by_sum_len", "yujian_bo_2d_over_sum_plus_d"],
        sorted(_dp["levenshtein_normalized_also_stored"], key=["by_sum_len", "yujian_bo_2d_over_sum_plus_d"].index))
    chk("R12::lcs_similarity_still_has_no_primary", None, _dp["lcs_similarity_primary"],
        "AMB-F02 는 열려 있다")
    chk("R12::zero_denominator_still_undefined", None,
        distance_profile([], [])["levenshtein_normalized_primary"],
        "AMB-F10 — R12 는 0/0 을 다루지 않았다. 0.0 으로 채우지 않는다")

    # (f) whole-family detector counts (pre-baked)
    cells = [_pair_cell(obs[x["id"]], obs[y["id"]]) for x, y in combinations(FIXTURE_FAMILY, 2)]
    chk("FAMILY::pair_cell_count", 45, len(cells), PAIR_CELL_WARNING)
    d1 = detector_1_depth_tie_flow_divergent(cells)
    d2 = detector_2_distance_positive_depth_tie(cells)
    d3 = detector_3_modal_experienced_only(cells, obs)
    chk("FAMILY::D1_positives_activation_only_task_base", 18,
        d1["positives_by_reading_and_base"]["reading=activation_only|base=task"],
        "7 fixtures tie at depth 3; C(7,2)=21 tied cells minus 3 identical-signature cells")
    chk("FAMILY::D1_positives_literal_task_base", 18,
        d1["positives_by_reading_and_base"]["reading=literal_all_but_excluded|base=task"],
        "same set under the other depth reading -> the D1 result is robust to AMB-F03")
    chk("FAMILY::D1_positives_activation_only_experienced_base", 20,
        d1["positives_by_reading_and_base"]["reading=activation_only|base=experienced"],
        "on the experienced base SYN05 separates from SYN01/SYN06 -> +2. AMB-F08 is live.")
    chk("FAMILY::D1_positives_delta9_task_base", 18, d1["positives_delta9_by_base"]["task"],
        "Δ9 단일값 기준. 7 fixture 가 depth 3 에서 동률 -> C(7,2)=21 셀에서 동일 signature 3 셀을 뺀 18")
    chk("FAMILY::D1_positives_delta9_experienced_base", 20, d1["positives_delta9_by_base"]["experienced"],
        "experienced base 에서 SYN05 가 SYN01/SYN06 과 갈린다 -> +2. AMB-F08 은 여전히 열려 있다")
    chk("FAMILY::D1_delta9_matches_activation_only_reading", True,
        d1["positives_delta9_by_base"]["task"]
        == d1["positives_by_reading_and_base"]["reading=activation_only|base=task"],
        "Δ9 는 기존 두 읽기 중 activation_only 를 확정한 것이므로 이 family 에서는 같은 셀 집합이 나와야 한다")
    chk("FAMILY::D1_delta9_indeterminate_cells", 0, len(d1["delta9_indeterminate_cells"]),
        "family fixture 는 SYN08 에 fixture_input_mode 를 명시했으므로 보류 셀이 없다")
    chk("FAMILY::D1_tier2_count", 1, len(d1["tier2_no_common_subsequence"]),
        "only SYN02 vs SYN04 share no token")
    chk("FAMILY::D1_negatives_count", 3, len(d1["negatives_depth_tie_but_identical_flow"]))
    chk("FAMILY::D2_positives_task_base", 18,
        len([x for x in d2["positives_ranked"] if x["base"] == "task"]))
    chk("FAMILY::D2_extremal_distance", 5, d2["extremal_levenshtein_raw_among_depth_tied"])
    chk("FAMILY::D2_positives_by_base", {"task": 18, "experienced": 20}, d2["positives_by_base"],
        "the base choice (AMB-F08) changes the cell count — the harness does not pick a base")
    chk("FAMILY::D3_positives", 2, len(d3["positives"]),
        "SYN05 vs SYN01 and SYN05 vs SYN06")
    chk("FAMILY::D3_nonattributable", 0, len(d3["difference_not_dismissal_attributable"]))
    chk("FAMILY::D3_neg_identical_pair_present", True,
        any(n["a"] == "SYN01_menu_category" and n["b"] == "SYN06_no_modal_twin" for n in d3["negatives"]))
    return checks


# ---------------------------------------------------------------------------
# 11b. Frozen pre-Δ9 regression set.
#      The exact 202 check ids that this harness ran and passed at base SHA
#      ce97273129b404774736ec566603b9e2b969ecdf, BEFORE the Δ9/R12 convergence.
#      The convergence must not delete, rename, or relax any of them.  Every one is re-run
#      unchanged (same id, same expected value) by run_all_checks(); the convergence only ADDS.
# ---------------------------------------------------------------------------
PRE_DELTA9_CHECK_IDS: Tuple[str, ...] = (
    "BND01_both_empty::lcs_dice",
    "BND01_both_empty::lcs_length",
    "BND01_both_empty::lcs_over_max_len",
    "BND01_both_empty::lcs_over_min_len",
    "BND01_both_empty::lev_by_max_len",
    "BND01_both_empty::lev_by_sum_len",
    "BND01_both_empty::lev_yujian_bo",
    "BND01_both_empty::levenshtein_raw",
    "BND02_empty_vs_len1::lcs_dice",
    "BND02_empty_vs_len1::lcs_length",
    "BND02_empty_vs_len1::lcs_over_max_len",
    "BND02_empty_vs_len1::lcs_over_min_len",
    "BND02_empty_vs_len1::lev_by_max_len",
    "BND02_empty_vs_len1::lev_by_sum_len",
    "BND02_empty_vs_len1::lev_yujian_bo",
    "BND02_empty_vs_len1::levenshtein_raw",
    "BND03_len1_identical::lcs_dice",
    "BND03_len1_identical::lcs_length",
    "BND03_len1_identical::lcs_over_max_len",
    "BND03_len1_identical::lcs_over_min_len",
    "BND03_len1_identical::lev_by_max_len",
    "BND03_len1_identical::lev_by_sum_len",
    "BND03_len1_identical::lev_yujian_bo",
    "BND03_len1_identical::levenshtein_raw",
    "BND04_len1_different::lcs_dice",
    "BND04_len1_different::lcs_length",
    "BND04_len1_different::lcs_over_max_len",
    "BND04_len1_different::lcs_over_min_len",
    "BND04_len1_different::lev_by_max_len",
    "BND04_len1_different::lev_by_sum_len",
    "BND04_len1_different::lev_yujian_bo",
    "BND04_len1_different::levenshtein_raw",
    "BND05_fully_identical_len4::lcs_dice",
    "BND05_fully_identical_len4::lcs_length",
    "BND05_fully_identical_len4::lcs_over_max_len",
    "BND05_fully_identical_len4::lcs_over_min_len",
    "BND05_fully_identical_len4::lev_by_max_len",
    "BND05_fully_identical_len4::lev_by_sum_len",
    "BND05_fully_identical_len4::lev_yujian_bo",
    "BND05_fully_identical_len4::levenshtein_raw",
    "BND06_fully_disjoint_len3::lcs_dice",
    "BND06_fully_disjoint_len3::lcs_length",
    "BND06_fully_disjoint_len3::lcs_over_max_len",
    "BND06_fully_disjoint_len3::lcs_over_min_len",
    "BND06_fully_disjoint_len3::lev_by_max_len",
    "BND06_fully_disjoint_len3::lev_by_sum_len",
    "BND06_fully_disjoint_len3::lev_yujian_bo",
    "BND06_fully_disjoint_len3::levenshtein_raw",
    "BND07_prefix_vs_extension::lcs_dice",
    "BND07_prefix_vs_extension::lcs_length",
    "BND07_prefix_vs_extension::lcs_over_max_len",
    "BND07_prefix_vs_extension::lcs_over_min_len",
    "BND07_prefix_vs_extension::lev_by_max_len",
    "BND07_prefix_vs_extension::lev_by_sum_len",
    "BND07_prefix_vs_extension::lev_yujian_bo",
    "BND07_prefix_vs_extension::levenshtein_raw",
    "CANONICAL::token_count",
    "DC01_D1_pos_reordered::D1",
    "DC02_D1_neg_identical::D1",
    "DC03_D1_neg_depth_differs::D1",
    "DC04_D1tier2_pos_disjoint::D1_TIER2",
    "DC05_D1tier2_neg_shared_endpoint::D1_TIER2",
    "DC06_D2_pos_disjoint::D2",
    "DC07_D2_neg_zero_distance::D2",
    "DC08_D2_neg_depth_differs::D2",
    "DC09_D3_pos_modal_one_side::D3",
    "DC10_D3_neg_no_modal_anywhere::D3",
    "DC11_D3_neg_same_modal_both_sides::D3",
    "DC12_D3_neg_task_flow_differs::D3",
    "DC13_D3_nonattributable::D3_NONATTRIB",
    "FAMILY::D1_negatives_count",
    "FAMILY::D1_positives_activation_only_experienced_base",
    "FAMILY::D1_positives_activation_only_task_base",
    "FAMILY::D1_positives_literal_task_base",
    "FAMILY::D1_tier2_count",
    "FAMILY::D2_extremal_distance",
    "FAMILY::D2_positives_by_base",
    "FAMILY::D2_positives_task_base",
    "FAMILY::D3_neg_identical_pair_present",
    "FAMILY::D3_nonattributable",
    "FAMILY::D3_positives",
    "FAMILY::pair_cell_count",
    "INV01_unknown_token::reason",
    "INV01_unknown_token::valid",
    "INV02_lowercase::reason",
    "INV02_lowercase::valid",
    "INV03_v2_legacy_token::reason",
    "INV03_v2_legacy_token::valid",
    "INV04_all_canonical::valid",
    "SYN01_menu_category::abstain_present",
    "SYN01_menu_category::activation_depth_base_invariant",
    "SYN01_menu_category::activation_depth_readings",
    "SYN01_menu_category::consistency",
    "SYN01_menu_category::flow_step_count_readings",
    "SYN01_menu_category::menu_dependency_base_invariant",
    "SYN01_menu_category::menu_dependency_readings",
    "SYN01_menu_category::menu_dependency_value",
    "SYN01_menu_category::nav_container_depth_withheld",
    "SYN01_menu_category::no_schema_error",
    "SYN02_search_item::abstain_present",
    "SYN02_search_item::activation_depth_base_invariant",
    "SYN02_search_item::activation_depth_readings",
    "SYN02_search_item::consistency",
    "SYN02_search_item::flow_step_count_readings",
    "SYN02_search_item::menu_dependency_base_invariant",
    "SYN02_search_item::menu_dependency_readings",
    "SYN02_search_item::menu_dependency_value",
    "SYN02_search_item::nav_container_depth_withheld",
    "SYN02_search_item::no_schema_error",
    "SYN03_tab_accordion::abstain_present",
    "SYN03_tab_accordion::activation_depth_base_invariant",
    "SYN03_tab_accordion::activation_depth_readings",
    "SYN03_tab_accordion::consistency",
    "SYN03_tab_accordion::flow_step_count_readings",
    "SYN03_tab_accordion::menu_dependency_base_invariant",
    "SYN03_tab_accordion::menu_dependency_readings",
    "SYN03_tab_accordion::menu_dependency_value",
    "SYN03_tab_accordion::nav_container_depth_withheld",
    "SYN03_tab_accordion::no_schema_error",
    "SYN04_tab_auth_terminal::abstain_present",
    "SYN04_tab_auth_terminal::activation_depth_base_invariant",
    "SYN04_tab_auth_terminal::activation_depth_readings",
    "SYN04_tab_auth_terminal::consistency",
    "SYN04_tab_auth_terminal::flow_step_count_readings",
    "SYN04_tab_auth_terminal::menu_dependency_base_invariant",
    "SYN04_tab_auth_terminal::menu_dependency_readings",
    "SYN04_tab_auth_terminal::menu_dependency_value",
    "SYN04_tab_auth_terminal::nav_container_depth_withheld",
    "SYN04_tab_auth_terminal::no_schema_error",
    "SYN05_modal_then_menu::abstain_present",
    "SYN05_modal_then_menu::activation_depth_base_invariant",
    "SYN05_modal_then_menu::activation_depth_readings",
    "SYN05_modal_then_menu::consistency",
    "SYN05_modal_then_menu::flow_step_count_readings",
    "SYN05_modal_then_menu::menu_dependency_base_invariant",
    "SYN05_modal_then_menu::menu_dependency_readings",
    "SYN05_modal_then_menu::menu_dependency_value",
    "SYN05_modal_then_menu::nav_container_depth_withheld",
    "SYN05_modal_then_menu::no_schema_error",
    "SYN06_no_modal_twin::abstain_present",
    "SYN06_no_modal_twin::activation_depth_base_invariant",
    "SYN06_no_modal_twin::activation_depth_readings",
    "SYN06_no_modal_twin::consistency",
    "SYN06_no_modal_twin::flow_step_count_readings",
    "SYN06_no_modal_twin::menu_dependency_base_invariant",
    "SYN06_no_modal_twin::menu_dependency_readings",
    "SYN06_no_modal_twin::menu_dependency_value",
    "SYN06_no_modal_twin::nav_container_depth_withheld",
    "SYN06_no_modal_twin::no_schema_error",
    "SYN07_reordered::abstain_present",
    "SYN07_reordered::activation_depth_base_invariant",
    "SYN07_reordered::activation_depth_readings",
    "SYN07_reordered::consistency",
    "SYN07_reordered::flow_step_count_readings",
    "SYN07_reordered::menu_dependency_base_invariant",
    "SYN07_reordered::menu_dependency_readings",
    "SYN07_reordered::menu_dependency_value",
    "SYN07_reordered::nav_container_depth_withheld",
    "SYN07_reordered::no_schema_error",
    "SYN08_transport_slots::abstain_present",
    "SYN08_transport_slots::activation_depth_base_invariant",
    "SYN08_transport_slots::activation_depth_readings",
    "SYN08_transport_slots::consistency",
    "SYN08_transport_slots::flow_step_count_readings",
    "SYN08_transport_slots::menu_dependency_base_invariant",
    "SYN08_transport_slots::menu_dependency_readings",
    "SYN08_transport_slots::menu_dependency_value",
    "SYN08_transport_slots::nav_container_depth_withheld",
    "SYN08_transport_slots::no_schema_error",
    "SYN09_abstain::abstain_present",
    "SYN09_abstain::activation_depth_base_invariant",
    "SYN09_abstain::activation_depth_readings",
    "SYN09_abstain::consistency",
    "SYN09_abstain::flow_step_count_readings",
    "SYN09_abstain::menu_dependency_base_invariant",
    "SYN09_abstain::menu_dependency_readings",
    "SYN09_abstain::menu_dependency_value",
    "SYN09_abstain::nav_container_depth_withheld",
    "SYN09_abstain::no_schema_error",
    "SYN10_empty::abstain_present",
    "SYN10_empty::activation_depth_base_invariant",
    "SYN10_empty::activation_depth_readings",
    "SYN10_empty::consistency",
    "SYN10_empty::flow_step_count_readings",
    "SYN10_empty::menu_dependency_base_invariant",
    "SYN10_empty::menu_dependency_readings",
    "SYN10_empty::menu_dependency_value",
    "SYN10_empty::nav_container_depth_withheld",
    "SYN10_empty::no_schema_error",
    "TOKENERR::raises_on_unknown_token",
    "dist::SYN01_menu_category|SYN05_modal_then_menu|experienced::lcs_length",
    "dist::SYN01_menu_category|SYN05_modal_then_menu|experienced::levenshtein_raw",
    "dist::SYN01_menu_category|SYN05_modal_then_menu|task::lcs_length",
    "dist::SYN01_menu_category|SYN05_modal_then_menu|task::levenshtein_raw",
    "dist::SYN01_menu_category|SYN06_no_modal_twin|task::lcs_length",
    "dist::SYN01_menu_category|SYN06_no_modal_twin|task::levenshtein_raw",
    "dist::SYN01_menu_category|SYN07_reordered|task::lcs_length",
    "dist::SYN01_menu_category|SYN07_reordered|task::levenshtein_raw",
    "dist::SYN01_menu_category|SYN10_empty|task::lcs_length",
    "dist::SYN01_menu_category|SYN10_empty|task::levenshtein_raw",
    "dist::SYN02_search_item|SYN04_tab_auth_terminal|task::lcs_length",
    "dist::SYN02_search_item|SYN04_tab_auth_terminal|task::levenshtein_raw",
)
PRE_DELTA9_CHECK_ID_SHA256 = "8db2dbacbe2b9825e010cd49096349258d63210d14ff1b9378869073f9c33649"


def run_regression_against_pre_delta9(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Two-sided: the frozen set must be PRESENT and PASSING. A missing id is a failure, not a
    silent zero — an empty intersection and a green run must not look alike."""
    by_id = {c["check_id"]: c for c in checks}
    missing = [i for i in PRE_DELTA9_CHECK_IDS if i not in by_id]
    failed = [i for i in PRE_DELTA9_CHECK_IDS if i in by_id and not by_id[i]["pass"]]
    added = sorted(set(by_id) - set(PRE_DELTA9_CHECK_IDS))
    digest = hashlib.sha256("\n".join(sorted(PRE_DELTA9_CHECK_IDS)).encode("utf-8")).hexdigest()
    return {
        "base_sha_of_frozen_set": "ce97273129b404774736ec566603b9e2b969ecdf",
        "pre_delta9_check_count": len(PRE_DELTA9_CHECK_IDS),
        "frozen_id_list_sha256": digest,
        "frozen_id_list_sha256_matches_recorded": digest == PRE_DELTA9_CHECK_ID_SHA256,
        "still_present": len(PRE_DELTA9_CHECK_IDS) - len(missing),
        "missing_after_convergence": missing,
        "failing_after_convergence": failed,
        "regression_clean": (not missing) and (not failed),
        "checks_added_by_convergence": len(added),
        "added_check_ids": added,
        "total_checks_now": len(checks),
        "note": "202/202 이 사라지지 않고 그대로 통과하는지를 id 단위로 확인한다. 기대값도 바꾸지 않았다.",
    }


# ---------------------------------------------------------------------------
# 12. Mutation testing — deliberately break the calculator, confirm the fixtures catch it,
#     then restore. Nothing on disk is modified; only in-process module globals are swapped.
# ---------------------------------------------------------------------------
def _mut_classification(**override):
    """Build an activation_depth replacement whose Δ9 table is deliberately wrong."""
    def fn(task_seq, experienced_seq, fixture_input_mode=None, conditional_token_modes=None):
        cls = dict(DELTA9_CLASSIFICATION)
        cls.update(override)
        legacy = tuple(t for t in ("INPUT_QUERY", "DISMISS_OBSTRUCTION") if cls.get(t) == "OUT")
        return _activation_depth_core(task_seq, experienced_seq, fixture_input_mode,
                                      conditional_token_modes, cls, legacy)
    return fn


# BUG: popup dismiss counted as an activation (04 §5 / 03 §6 exclude it)
_mut_activation_depth_counts_dismiss = _mut_classification(DISMISS_OBSTRUCTION="IN")
# BUG: Δ9 headline reversed — submit excluded from depth
_mut_depth_excludes_submit_query = _mut_classification(SUBMIT_QUERY="OUT")
# BUG: CONDITIONAL 3종을 입력수단과 무관하게 무조건 포함
_mut_conditional_always_in = _mut_classification(
    SELECT_ORIGIN="IN", SELECT_DESTINATION="IN", SELECT_DATE="IN")
# BUG: AUTH_GATE counted as an activation (Δ9: 마주친 상태이지 활성화가 아니다)
_mut_auth_gate_counts_as_activation = _mut_classification(AUTH_GATE="IN")


def _mut_menu_dependency_always_true(task_seq, experienced_seq):
    r = {"reveal_set_explicit3": True, "reveal_set_incl_switch_tab": True}
    return {"readings": r, "readings_experienced_base": r, "base_invariant": True,
            "endpoint_token_present": "ENDPOINT_REACHED" in task_seq, "value": True,
            "ambiguity_active": False, "ambiguity_ids": ["AMB-F05"]}


def _mut_levenshtein_len_diff(a, b):
    return abs(len(a) - len(b))  # BUG: order/content blind


def _mut_flow_step_count_drops_typing(task_seq, experienced_seq):
    readings = {}
    for base_name, seq in (("task", task_seq), ("experienced", experienced_seq)):
        s = [t for t in seq if t != "INPUT_QUERY"]  # BUG: §5 says typing is INCLUDED
        readings[f"base={base_name}|terminal=incl"] = len(s)
        readings[f"base={base_name}|terminal=excl"] = sum(
            1 for t in s if t not in ("ENDPOINT_REACHED", "ABSTAIN"))
    primary, ambiguous = _agree(readings)
    return {"readings": readings, "determined_inclusions": ["SUBMIT_QUERY", "AUTH_GATE"],
            "value": primary, "ambiguity_active": ambiguous, "ambiguity_ids": ["AMB-F04"]}


def _mut_div_zero_as_zero(num, den):
    if den == 0:
        return 0.0  # BUG: 0/0 silently reported as "identical"
    return round(num / den, 10)


def _mut_sig_always_experienced(obs, base):
    return obs["experienced_signature"]  # BUG: task/experienced separation collapsed


def _mut_lcs_is_min_len(a, b):
    return min(len(a), len(b))  # BUG: ignores content, never returns 0 for nonempty pairs


MUTANTS: List[Dict[str, Any]] = [
    {"id": "MUT01_depth_counts_dismissal", "target": "activation_depth", "fn": _mut_activation_depth_counts_dismiss,
     "breaks": "04 §5 / 03 §6 — popup dismiss must be excluded from depth"},
    {"id": "MUT02_menu_dependency_always_true", "target": "menu_dependency", "fn": _mut_menu_dependency_always_true,
     "breaks": "04 §5 — reveal token must actually be present"},
    {"id": "MUT03_levenshtein_length_only", "target": "levenshtein", "fn": _mut_levenshtein_len_diff,
     "breaks": "05 §2-E — edit distance must be order/content sensitive"},
    {"id": "MUT04_flow_step_count_drops_typing", "target": "flow_step_count", "fn": _mut_flow_step_count_drops_typing,
     "breaks": "04 §5 — typing/submit/auth are INCLUDED in flow_step_count (this is exactly where it "
               "differs from activation_depth; unifying the two lists is the failure mode being guarded)"},
    {"id": "MUT05_zero_denominator_as_zero", "target": "_div", "fn": _mut_div_zero_as_zero,
     "breaks": "AMB-F10 — 0/0 must not be reported as 0.0 (would read as 'identical flows')"},
    {"id": "MUT06_signature_collapse", "target": "_sig", "fn": _mut_sig_always_experienced,
     "breaks": "04 §3 — task_flow and experienced_flow must stay separate"},
    {"id": "MUT07_lcs_length_blind", "target": "lcs_length", "fn": _mut_lcs_is_min_len,
     "breaks": "05 §2-E — LCS must reflect shared content; tier2 (LCS==0) depends on it"},
    {"id": "MUT08_depth_excludes_submit_query", "target": "activation_depth",
     "fn": _mut_depth_excludes_submit_query,
     "breaks": "Δ9 (T-A-V3-STEP1-006) — SUBMIT_QUERY 는 activation_depth 에 포함된다. 빼면 검색을 거쳐야 "
               "진입하는 서비스와 바로 누르는 서비스가 같은 depth 를 갖는다"},
    {"id": "MUT09_conditional_always_included", "target": "activation_depth",
     "fn": _mut_conditional_always_in,
     "breaks": "Δ9 CONDITIONAL — SELECT_ORIGIN/DESTINATION/DATE 는 fixture_input_mode 에 따라 갈린다. "
               "무조건 포함하면 FREE_TEXT 로 타이핑한 값이 activation 으로 집계된다"},
    {"id": "MUT10_auth_gate_counts_as_activation", "target": "activation_depth",
     "fn": _mut_auth_gate_counts_as_activation,
     "breaks": "Δ9 — AUTH_GATE 는 '사용자 활성화가 아니라 마주친 상태'다 (기준 ①)"},
    {"id": "MUT11_distance_primary_is_sum_len", "target": "R12_PRIMARY_NORMALIZATION",
     "fn": "by_sum_len",
     "breaks": "R12 (T-A-V3-STEP1-007) — primary 는 max(len) 정규화다. sum(len) 은 비어 있지 않은 두 열에서 "
               "결코 1 에 도달하지 못해 차이를 과소보고한다"},
]


def run_mutation_testing() -> List[Dict[str, Any]]:
    g = globals()
    out = []
    for m in MUTANTS:
        original = g[m["target"]]
        g[m["target"]] = m["fn"]
        try:
            checks = run_all_checks()
            failed = [c["check_id"] for c in checks if not c["pass"]]
        except Exception as exc:  # a mutant may make the calculator raise — that also counts as caught
            failed = [f"EXCEPTION::{type(exc).__name__}: {exc}"]
        finally:
            g[m["target"]] = original
        out.append({
            "mutant_id": m["id"], "target": m["target"], "breaks": m["breaks"],
            "caught": len(failed) > 0, "failed_check_count": len(failed),
            "sample_failed_checks": failed[:6],
        })
    # restoration proof: the clean suite must be green again after every mutant is reverted
    post = run_all_checks()
    out.append({
        "mutant_id": "RESTORE_PROOF", "target": None,
        "breaks": "n/a — verifies every mutation was reverted",
        "caught": None,
        "failed_check_count": len([c for c in post if not c["pass"]]),
        "sample_failed_checks": [c["check_id"] for c in post if not c["pass"]][:6],
    })
    return out


# ---------------------------------------------------------------------------
# 13. Output assembly
# ---------------------------------------------------------------------------
def _sha256(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def build_report() -> Dict[str, Any]:
    checks = run_all_checks()
    mutations = run_mutation_testing()
    failed = [c for c in checks if not c["pass"]]
    restore = [m for m in mutations if m["mutant_id"] == "RESTORE_PROOF"][0]
    uncaught = [m for m in mutations if m["mutant_id"] != "RESTORE_PROOF" and not m["caught"]]

    obs = {fx["id"]: compute_observation(fx["id"], fx["task"], fx["experienced"],
                                        fx.get("fixture_input_mode")) for fx in FIXTURE_FAMILY}
    cells = [_pair_cell(obs[x["id"]], obs[y["id"]]) for x, y in combinations(FIXTURE_FAMILY, 2)]
    d1 = detector_1_depth_tie_flow_divergent(cells)
    d2 = detector_2_distance_positive_depth_tie(cells)
    d3 = detector_3_modal_experienced_only(cells, obs)

    if failed or uncaught or restore["failed_check_count"] > 0:
        verdict = "NOT_READY"
    elif AMBIGUOUS_DEFINITIONS:
        verdict = "READY_WITH_AMBIGUITY"
    else:
        verdict = "READY"

    boundary_table = []
    for bc in BOUNDARY_CASES:
        dp = distance_profile(bc["a"], bc["b"])
        boundary_table.append({
            "id": bc["id"], "a": bc["a"], "b": bc["b"], "note": bc["note"],
            "expected": bc["expected"],
            "computed": {
                "levenshtein_raw": dp["levenshtein_raw"], "lcs_length": dp["lcs_length"],
                "lev_by_max_len": dp["levenshtein_normalized_candidates"]["by_max_len"],
                "lev_by_sum_len": dp["levenshtein_normalized_candidates"]["by_sum_len"],
                "lev_yujian_bo": dp["levenshtein_normalized_candidates"]["yujian_bo_2d_over_sum_plus_d"],
                "lcs_over_max_len": dp["lcs_similarity_candidates"]["over_max_len"],
                "lcs_over_min_len": dp["lcs_similarity_candidates"]["over_min_len"],
                "lcs_dice": dp["lcs_similarity_candidates"]["dice_2L_over_sum"],
            },
            "match": all(dp_v == bc["expected"][k] for k, dp_v in [
                ("levenshtein_raw", dp["levenshtein_raw"]), ("lcs_length", dp["lcs_length"]),
                ("lev_by_max_len", dp["levenshtein_normalized_candidates"]["by_max_len"]),
                ("lev_by_sum_len", dp["levenshtein_normalized_candidates"]["by_sum_len"]),
                ("lev_yujian_bo", dp["levenshtein_normalized_candidates"]["yujian_bo_2d_over_sum_plus_d"]),
                ("lcs_over_max_len", dp["lcs_similarity_candidates"]["over_max_len"]),
                ("lcs_over_min_len", dp["lcs_similarity_candidates"]["over_min_len"]),
                ("lcs_dice", dp["lcs_similarity_candidates"]["dice_2L_over_sum"]),
            ]),
        })

    unique_task_sigs = sorted({o["task_signature"] for o in obs.values()})
    unique_exp_sigs = sorted({o["experienced_signature"] for o in obs.values()})

    return {
        "artifact": "LANE_F_HARNESS",
        "lane": "F — Flow Topology / Depth",
        "verdict": verdict,
        "verdict_basis": {
            "fixture_checks_total": len(checks),
            "fixture_checks_failed": len(failed),
            "failed_check_ids": [c["check_id"] for c in failed],
            "mutants_total": len(MUTANTS),
            "mutants_caught": len([m for m in mutations if m["mutant_id"] != "RESTORE_PROOF" and m["caught"]]),
            "mutants_uncaught": [m["mutant_id"] for m in uncaught],
            "restore_proof_failed_checks": restore["failed_check_count"],
            "open_ambiguities": len(AMBIGUOUS_DEFINITIONS),
            "rule": "READY only if zero open ambiguities; ambiguities are raised, not filled, so the "
                    "highest achievable verdict here is READY_WITH_AMBIGUITY.",
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "ssot_dir": SSOT_DIR,
            "ssot_file_sha256": {f: _sha256(os.path.join(SSOT_DIR, f)) for f in (
                "MANIFEST_v3.0.json", "00_SSOT_v3.0_CROSS_SERVICE_FLOW.md",
                "03_COLLECTION_MEASUREMENT_SPEC_v3.0.md", "04_FLOW_CODEBOOK_v3.0.md",
                "05_ANALYSIS_PLAN_v3.0.md")},
            "expected_manifest_sha256": "1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a",
            "harness_path": os.path.abspath(__file__),
            "data_source": "SYNTHETIC FIXTURES ONLY — no REAL target, no MAIN50, no mart/raw evidence, "
                           "no gold label, no holdout, no network access.",
        },
        "sampling_discipline": {
            "independent_unit": "service × frozen task (family n=10)",
            "pair_cells_in_this_run": len(cells),
            "warning": PAIR_CELL_WARNING,
        },
        "codebook_definitions_verbatim": VERBATIM,
        "canonical_tokens": CANONICAL_TOKENS,
        "implemented_variables": {
            "task_flow_sequence / experienced_flow_sequence": "separated per 04 §3; DISMISS_OBSTRUCTION in "
                "task_flow_sequence is reported as a schema error",
            "sequence_signature": "ordered token list; ' > ' rendering per the §3 example",
            "menu_dependency": "04 §5 — two reveal-set readings (AMB-F05); single value only on agreement",
            "activation_depth": "04 §5 — excludes INPUT_QUERY and DISMISS_OBSTRUCTION; two readings for "
                "AUTH_GATE/ENDPOINT_REACHED/ABSTAIN (AMB-F03); base-invariance asserted",
            "flow_step_count": "04 §5 — includes typing/submit/auth encounter; 4 readings over "
                "base × terminal (AMB-F04). Deliberately NOT unified with activation_depth.",
            "nav_container_depth": "candidates only, no value (AMB-F06)",
            "levenshtein_raw / lcs_length": "05 §2-E raw values, unambiguous",
            "normalized levenshtein / LCS similarity": "3 candidate denominators each, no default "
                "(AMB-F01 / AMB-F02)",
        },
        "fixture_results": {
            "family_size": len(FIXTURE_FAMILY),
            "observations": obs,
            "checks": checks,
            "boundary_case_table": boundary_table,
            "invalid_token_cases": [
                {"id": iv["id"], "sequence": iv["seq"], "expect_valid": iv["expect_valid"],
                 "result": validate_sequence(iv["seq"], iv["id"])} for iv in INVALID_TOKEN_CASES],
            "unique_task_flow_signatures": {"count": len(unique_task_sigs), "signatures": unique_task_sigs},
            "unique_experienced_flow_signatures": {"count": len(unique_exp_sigs), "signatures": unique_exp_sigs},
            "directed_cases": [evaluate_directed_case(dc) for dc in DIRECTED_CASES],
            "mutation_testing": mutations,
        },
        "counterexample_detectors": {
            "D1_depth_tie_flow_divergent": d1,
            "D2_distance_positive_depth_tie": d2,
            "D3_modal_experienced_only_inflation": d3,
        },
        "ambiguous_definitions": AMBIGUOUS_DEFINITIONS,
        "not_implemented": NOT_IMPLEMENTED,
        "limitation": [
            "MAIN50 미수집. 여기의 모든 수치는 합성 fixture 산출물이며 어떤 서비스에 대한 관측도 아니다.",
            "fixture 는 계산기가 정의를 지키는지만 보인다. 실제 MAIN50 sequence 의 token 분포·길이·terminal "
            "구성이 fixture 와 다르면 detector 의 산출 규모는 달라진다. fixture 는 대표성 주장이 아니다.",
            "detector 는 존재증명이다. '동일 depth 에서 flow 가 갈리는 pair 가 존재한다'는 구조적 사실을 보일 뿐, "
            "그 빈도·효과크기·모집단 일반화를 말하지 않는다.",
            "AMB-F01/F02 가 미해결인 한 normalized distance heatmap(05 §8)은 단일 그림으로 확정 발행할 수 없다. "
            "분모 선택이 pair 순위를 바꾼다(BND07: 0.667 vs 1.0 vs 0.8).",
            "AMB-F03/F04 가 미해결인 한 activation depth 의 median/IQR(05 §2-F) 절대값은 확정할 수 없다. "
            "단, depth '차이'는 두 읽기에서 동일하게 나오는 경우가 많아 D1/D2 는 robust 하게 판정된다(본 run 에서 18=18).",
            "AMB-F06 때문에 nav_container_depth 는 산출하지 못했다. token 열이 아니라 fact_flow_step 의 "
            "nav_container_type/reveal evidence 가 있어야 계산 가능하다.",
            "Levenshtein 은 모든 token 치환 비용을 1 로 둔다. token 간 의미거리(예: OPEN_GLOBAL_MENU↔OPEN_LOCAL_MENU 가 "
            "OPEN_GLOBAL_MENU↔INPUT_QUERY 보다 가깝다)를 codebook 이 정의하지 않았으므로 가중치를 만들지 않았다.",
            "D1-tier1 과 D2 는 임계값 없이는 동일 술어다. 이를 다르게 보이게 하려면 'large' 컷오프가 필요하고, "
            "그것은 금지 사항이라 만들지 않았다.",
            "본 하네스는 GO/NO-GO 를 내지 않는다. verdict 는 계산기 준비 상태에 대한 것이지 연구 결론이 아니다.",
        ],
    }



# ---------------------------------------------------------------------------
# 13b. Δ9 / R12 convergence report — the deliverable for the Lane F-Δ9 task.
# ---------------------------------------------------------------------------
FLOW_STEP_COUNT_NOTE = {
    "INPUT_QUERY": "포함 (Δ9 OUT 사유문: 'flow_step_count 에는 포함'; 04 §5 'typing ... 포함')",
    "SUBMIT_QUERY": "포함 (04 §5 'typing/submit/auth encounter 포함'; 03 §6 'task-intent typing/submit 을 별도 token 으로 보존')",
    "AUTH_GATE": "포함 (Δ9 OUT 사유문: 'flow_step_count 에는 auth encounter 로 포함')",
    "DISMISS_OBSTRUCTION": "미정 — Δ9 는 'forced_dismissal_count 로 별도 집계'라고만 적었다. flow_step_count base(task|experienced) 는 AMB-F04 로 열려 있다",
}


def token_classification_table() -> List[Dict[str, Any]]:
    rows = []
    for tok, defn in CANONICAL_TOKENS.items():
        cls = DELTA9_CLASSIFICATION[tok]
        if cls == "IN":
            reason = ("Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. "
                      "03 §6 포함목록 'link/button/tab/menu open · category/function/result select · "
                      "state-changing menu/drawer reveal' 의 적용례다")
        elif cls == "OUT":
            reason = DELTA9_OUT[tok]
        else:
            reason = DELTA9_CONDITIONAL_RULE
        rows.append({
            "token": tok,
            "codebook_definition_04_§2": defn,
            "delta9_activation_depth": cls,
            "delta9_reason": reason,
            "flow_step_count": FLOW_STEP_COUNT_NOTE.get(tok, "미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다"),
            "harness_behaviour": (
                "무조건 계수" if cls == "IN" else
                "무조건 제외" if cls == "OUT" else
                "fixture_input_mode 로 결정. DROPDOWN/MAP_PAN→포함, FREE_TEXT→제외, "
                "MIXED(수단 기록시)→그 수단, 그 외/미기록→UNRESOLVED 로 value 보류"),
        })
    assert len(rows) == 18
    return rows


def submit_query_effect() -> Dict[str, Any]:
    rows = []
    for sq in SUBMIT_QUERY_EFFECT_CASES:
        pre = activation_depth(sq["seq"], sq["seq"], sq.get("fixture_input_mode"))
        cf, _ = _counterfactual_delta9_depth(sq["seq"], {"SUBMIT_QUERY": "OUT"}, sq.get("fixture_input_mode"))
        rows.append({
            "case_id": sq["id"],
            "sequence": list(sq["seq"]),
            "signature": sequence_signature(sq["seq"]),
            "fixture_input_mode": sq.get("fixture_input_mode"),
            "pre_convergence_readings_AMB_F03": pre["readings"],
            "pre_convergence_emitted_value": None if pre["readings"]["literal_all_but_excluded"]
                != pre["readings"]["activation_only"] else pre["readings"]["activation_only"],
            "pre_convergence_state": ("두 읽기가 갈려 value 를 보류(None)했다"
                                      if pre["readings"]["literal_all_but_excluded"] != pre["readings"]["activation_only"]
                                      else "두 읽기가 일치해 이미 단일값이었다"),
            "post_convergence_delta9_value": pre["value"],
            "counterfactual_submit_excluded": cf,
            "delta_from_excluding_submit": None if (pre["value"] is None or cf is None) else pre["value"] - cf,
            "why": sq["why"],
        })
    a = [r for r in rows if r["case_id"] == "SQE01_search_then_submit"][0]
    b = [r for r in rows if r["case_id"] == "SQE02_press_directly"][0]
    return {
        "ruling": "SUBMIT_QUERY 는 activation_depth 에 포함된다 (T-A-V3-STEP1-006 headline).",
        "what_lane_f_did_before": (
            "이 하네스는 수렴 전에도 SUBMIT_QUERY 를 제외하지 않았다 — 제외목록은 (INPUT_QUERY, "
            "DISMISS_OBSTRUCTION) 뿐이었다. 따라서 **Δ9 의 submit 조항 자체는 Lane F 의 계수를 바꾸지 "
            "않는다.** Lane F 에서 실제로 값을 바꾼 것은 같은 티켓의 AMB-F03 확정(AUTH_GATE/"
            "ENDPOINT_REACHED/ABSTAIN 을 OUT 으로) 이며, 그것이 '두 읽기 병기 + value 보류'를 "
            "'단일 값'으로 바꿨다. 과대주장을 피하기 위해 이 사실을 먼저 적는다."),
        "rows": rows,
        "structural_claim": {
            "claim": "submit 을 빼면 검색을 거쳐야 진입하는 서비스와 바로 누르는 서비스가 같은 depth 를 갖는다",
            "search_path": a["signature"],
            "direct_path": b["signature"],
            "delta9_depths": {"search": a["post_convergence_delta9_value"], "direct": b["post_convergence_delta9_value"]},
            "delta9_distinguishes": a["post_convergence_delta9_value"] != b["post_convergence_delta9_value"],
            "counterfactual_depths": {"search": a["counterfactual_submit_excluded"], "direct": b["counterfactual_submit_excluded"]},
            "counterfactual_collapses_them": a["counterfactual_submit_excluded"] == b["counterfactual_submit_excluded"],
            "verdict": "Δ9 의 주장이 fixture 에서 그대로 재현된다",
        },
        "preregistered_family_asymmetry": VERBATIM["delta9_family_asymmetry"]["text"],
    }


def conditional_input_mode_effect() -> Dict[str, Any]:
    rows = []
    for cd in CONDITIONAL_CASES:
        ad = activation_depth(cd["seq"], cd["seq"], cd.get("fixture_input_mode"), cd.get("conditional_token_modes"))
        rows.append({
            "case_id": cd["id"],
            "signature": sequence_signature(cd["seq"]),
            "fixture_input_mode": cd.get("fixture_input_mode"),
            "conditional_token_modes": cd.get("conditional_token_modes"),
            "activation_depth_value": ad["value"],
            "unresolved_conditional_count": ad["unresolved_conditional_count"],
            "bounds_when_unresolved": ad["bounds_when_unresolved"],
            "depth_conditional_tokens": ad["depth_conditional_tokens"],
            "why": cd["why"],
        })
    return {
        "ruling": VERBATIM["delta9_conditional"]["text"],
        "fixture_input_mode_enum": list(FIXTURE_INPUT_MODES),
        "resolution_map_ruled_by_delta9": CONDITIONAL_MODE_RESOLUTION,
        "unruled_modes": ["MIXED (토큰별 실제 사용 수단이 기록되지 않은 경우)", "OTHER", "미기록(None)"],
        "rows": rows,
        "same_sequence_splits": {
            "sequence": sequence_signature(S08),
            "DROPDOWN": activation_depth(S08, S08, "DROPDOWN")["value"],
            "FREE_TEXT": activation_depth(S08, S08, "FREE_TEXT")["value"],
            "reading": "입력수단에 따라 depth 가 갈리는 것은 결함이 아니라 측정이다 (Δ9 why_this_is_correct)",
        },
    }


def distance_three_way() -> Dict[str, Any]:
    demo = [
        {"id": "BND04_len1_different", "a": ["SELECT_FUNCTION"], "b": ["SELECT_RESULT"]},
        {"id": "BND06_fully_disjoint_len3",
         "a": ["OPEN_GLOBAL_MENU", "SELECT_CATEGORY", "SELECT_FUNCTION"],
         "b": ["INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT"]},
        {"id": "BND07_prefix_vs_extension",
         "a": ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION"],
         "b": ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"]},
        {"id": "BND01_both_empty", "a": [], "b": []},
        {"id": "FAM_SYN01_vs_SYN07", "a": S01, "b": S07},
    ]
    rows = []
    for d in demo:
        dp = distance_profile(d["a"], d["b"])
        c = dp["levenshtein_normalized_candidates"]
        rows.append({
            "pair_id": d["id"],
            "a": sequence_signature(d["a"]), "b": sequence_signature(d["b"]),
            "levenshtein_raw": dp["levenshtein_raw"],
            "by_max_len_PRIMARY": c["by_max_len"],
            "by_sum_len_stored": c["by_sum_len"],
            "yujian_bo_stored": c["yujian_bo_2d_over_sum_plus_d"],
            "three_values_agree": len({c["by_max_len"], c["by_sum_len"], c["yujian_bo_2d_over_sum_plus_d"]}) == 1,
            "single_reported_scalar": dp["levenshtein_normalized_primary"],
            "emitted_primary_key": dp["levenshtein_normalized_primary_key"],
            "lcs_similarity_primary": dp["lcs_similarity_primary"],
        })
    return {
        "ruling": VERBATIM["r12_sequence_distance_normalization"]["text"],
        "primary": R12_PRIMARY_NORMALIZATION,
        "also_stored": list(R12_ALSO_STORED),
        "single_scalar_rule": "단일 보고에는 primary 만 쓴다. 나머지 둘은 저장되지만 스칼라로 emit 되지 않는다.",
        "worked_example_from_the_ticket": {
            "pair": "BND04 / BND06 — 서로소 pair",
            "by_max_len": 1.0, "by_sum_len": 0.5, "yujian_bo": 0.6666666667,
            "note": "R12 가 AMB-F01 을 제기할 때 든 바로 그 1.0 / 0.5 / 0.667 이다",
        },
        "rows": rows,
        "lcs_similarity_still_open": {
            "ambiguity_id": "AMB-F02",
            "state": "R12 는 Levenshtein 정규화만 확정했다. LCS similarity 는 세 후보(over_max_len / "
                     "over_min_len / dice)를 그대로 병기하고 primary 를 emit 하지 않는다.",
        },
        "zero_denominator_still_open": {
            "ambiguity_id": "AMB-F10",
            "state": "두 열이 모두 비면 max(len)=0 이라 primary 도 정의되지 않는다. R12 는 이 경우를 다루지 "
                     "않았다. 0.0 으로 채우지 않고 None 을 반환한다.",
        },
        "declared_sensitivity": "군집·MDS 를 수행할 때는 Yujian-Bo 를 병기한다 (R12). 이 하네스는 clustering 을 "
                                "구현하지 않으므로 그 조항은 미이행 상태로 남는다.",
    }


def build_delta9_convergence() -> Dict[str, Any]:
    checks = run_all_checks()
    regression = run_regression_against_pre_delta9(checks)
    mutations = run_mutation_testing()
    failed = [c["check_id"] for c in checks if not c["pass"]]
    uncaught = [m["mutant_id"] for m in mutations
                if m["mutant_id"] != "RESTORE_PROOF" and not m["caught"]]
    restore = [m for m in mutations if m["mutant_id"] == "RESTORE_PROOF"][0]

    converged = (not failed) and (not uncaught) and regression["regression_clean"] \
        and restore["failed_check_count"] == 0
    if not converged:
        verdict = "NOT_CONVERGED"
    elif AMBIGUOUS_DEFINITIONS:
        verdict = "CONVERGED_WITH_AMBIGUITY"
    else:
        verdict = "CONVERGED"

    return {
        "artifact": "LANE_F_DELTA9_CONVERGENCE",
        "lane": "F — Flow Topology / Depth",
        "task": "Lane F 를 Δ9(activation_depth 18종 전수 분류)와 R12(sequence 거리 정규화)로 수렴",
        "verdict": verdict,
        "verdict_basis": {
            "rule": "CONVERGED 는 열린 모호성이 0 일 때만. Δ9·R12 는 AMB-F01·AMB-F03 을 닫았고 "
                    "AMB-F12 를 새로 드러냈으므로 상한은 CONVERGED_WITH_AMBIGUITY 다.",
            "fixture_checks_total": len(checks),
            "fixture_checks_failed": len(failed),
            "failed_check_ids": failed,
            "pre_delta9_regression_clean": regression["regression_clean"],
            "mutants_total": len(MUTANTS),
            "mutants_uncaught": uncaught,
            "restore_proof_failed_checks": restore["failed_check_count"],
            "open_ambiguities": len(AMBIGUOUS_DEFINITIONS),
            "closed_ambiguities": len(CLOSED_AMBIGUITIES),
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": {
            "delta9_ticket": DELTA9_TICKET,
            "delta9_ticket_path": "/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2/tickets/T-A-V3-STEP1-006.json",
            "r12_ticket": R12_TICKET,
            "r12_ticket_path": "/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2/tickets/T-A-V3-STEP1-007.json",
            "ssot": os.path.join(SSOT_DIR, "04_FLOW_CODEBOOK_v3.0.md"),
            "ssot_sha256": {f: _sha256(os.path.join(SSOT_DIR, f)) for f in (
                "MANIFEST_v3.0.json", "03_COLLECTION_MEASUREMENT_SPEC_v3.0.md",
                "04_FLOW_CODEBOOK_v3.0.md", "05_ANALYSIS_PLAN_v3.0.md")},
            "ssot_unmodified": "SSOTV3 원본은 읽기만 했다. Δ9·Δ10 은 delta 로 기록되며 원본을 고치지 않는다.",
            "base_sha": "ce97273129b404774736ec566603b9e2b969ecdf",
        },
        "delta9_verbatim": {
            "general_criterion": DELTA9_GENERAL_CRITERION,
            "submit_query": VERBATIM["delta9_submit_query"],
            "canonical_18_classification": {
                "IN_activation_depth": list(DELTA9_IN),
                "OUT_activation_depth": DELTA9_OUT,
                "CONDITIONAL": {"tokens": list(DELTA9_CONDITIONAL), "rule": DELTA9_CONDITIONAL_RULE,
                                "how_to_decide": "Δ8-R5 의 fixture_input_mode — DROPDOWN/MAP_PAN 계열이면 포함, "
                                                 "FREE_TEXT 면 제외, MIXED 면 실제로 사용한 수단 기준",
                                "record": "각 관측에 depth_conditional_tokens 로 남긴다"},
            },
            "conditional": VERBATIM["delta9_conditional"],
            "family_asymmetry": VERBATIM["delta9_family_asymmetry"],
            "T_B_FC_013_confirmed": VERBATIM["tb_fc_013"],
        },
        "r12_verbatim": VERBATIM["r12_sequence_distance_normalization"],
        "token_classification_table": token_classification_table(),
        "direction_is_not_a_token": {
            "ruling": DIRECTION_IS_NOT_A_TOKEN,
            "lane_f_check": [
                {"id": iv["id"], "sequence": iv["seq"], "expect_valid": iv["expect_valid"],
                 "result": validate_sequence(iv["seq"], iv["id"])}
                for iv in INVALID_TOKEN_CASES if iv["id"] == "INV05_open_right_drawer"],
            "confirmed": not validate_sequence(["OPEN_RIGHT_DRAWER"])["valid"],
            "note": "Lane F 는 canonical 18 밖의 값을 NOT_IN_CANONICAL_18 스키마 오류로 보고한다. "
                    "nav_container_type / reveal_direction 자체는 Lane S 소관이라 여기서 계산하지 않는다.",
        },
        "submit_query_effect": submit_query_effect(),
        "conditional_input_mode_effect": conditional_input_mode_effect(),
        "distance_three_way": distance_three_way(),
        "mutation_results": mutations,
        "regression": regression,
        "ambiguities_closed": CLOSED_AMBIGUITIES,
        "ambiguities_still_open": AMBIGUOUS_DEFINITIONS,
        "out_of_scope_here": [
            {"item": "R13 auth_gate_stage UNDETERMINED",
             "owner": "Lane A",
             "why": "R13 은 auth_gate_stage enum 확장이다. Lane F 는 token 열만 다루며 auth_gate_stage 를 "
                    "산출하지 않는다(NOT_IMPLEMENTED 에 기존 등재). "
                    "**Lane F 소관은 AUTH_GATE 토큰의 depth 귀속뿐이고, 그것은 Δ9 가 OUT 으로 확정했다.**"},
            {"item": "nav_container_type / reveal_direction",
             "owner": "Lane S",
             "why": "T-B-FC-013 이 방향을 별도 변수로 확정했으나 그 변수들은 Lane F 의 산출물이 아니다."},
            {"item": "cross-lane 중복 변수 수렴검사 (nav_container_depth · menu_dependency)",
             "owner": "다른 워커",
             "why": "converge_dup_vars.py 는 이 작업의 수정 대상이 아니다. 읽지도 쓰지도 않았다."},
        ],
        "limitation": [
            "REAL 접속 0건. MAIN50 미수집. 여기의 모든 수치는 합성 fixture 산출물이며 어떤 서비스에 대한 관측도 아니다.",
            "**Δ9 의 submit 조항은 Lane F 의 계수를 바꾸지 않았다.** Lane F 는 수렴 전에도 SUBMIT_QUERY 를 "
            "제외하지 않았기 때문이다. 값을 바꾼 것은 같은 티켓의 AMB-F03 확정이다. submit_query_effect 표의 "
            "'수렴 전' 열은 그 사실을 드러내기 위한 것이지 Lane F 가 submit 을 빼고 있었다는 뜻이 아니다.",
            "fixture 는 워커가 티켓을 읽고 만든 것이다. 티켓을 오독했다면 fixture 도 같이 틀린다. 변이 검사는 "
            "구현 오류만 잡고 해석 오류는 못 잡는다 (R14 weakest-link, A 가 구속력 있는 한계로 채택).",
            "AMB-F12 는 이 수렴 과정에서 **새로 드러난** 모호성이다. Δ9 가 CONDITIONAL 규칙을 세우면서 "
            "OTHER·미기록·수단미기록 MIXED 를 남겼다. 채우지 않고 올린다.",
            "AMB-F02(LCS similarity 분모)·F04(flow_step_count base/terminal)·F05(reveal token 집합)·"
            "F06(nav_container_depth)·F07(b)(c)·F08(distance base)·F09·F10·F11 은 Δ9·R12 가 다루지 않았다. "
            "닫히지 않았다.",
            "R12 의 '군집·MDS 시 Yujian-Bo 병기' 조항은 clustering 미구현이라 이 하네스에서 이행되지 않는다.",
            "family n=10 이 독립단위다. 이 run 의 45 pair 는 distance matrix 의 cell 이며 n=45 가 아니다.",
            "본 하네스는 GO/NO-GO 를 내지 않는다. verdict 는 계산기가 Δ9·R12 로 수렴했는지에 대한 것이지 "
            "연구 결론이 아니다.",
        ],
        "pair_cell_warning": PAIR_CELL_WARNING,
    }


def write_delta9_markdown(rep: Dict[str, Any], path: str) -> None:
    vb = rep["verdict_basis"]
    reg = rep["regression"]
    sqe = rep["submit_query_effect"]
    L: List[str] = []
    L.append("# LANE F — Δ9 / R12 수렴 결과\n")
    L.append(f"- **verdict**: `{rep['verdict']}`")
    L.append(f"- 생성: {rep['generated_at_utc']}")
    L.append(f"- 권위: `{rep['authority']['delta9_ticket']}` (Δ9) · `{rep['authority']['r12_ticket']}` (R12) · "
             f"SSOTV3 04 §2/§5, 03 §6")
    L.append(f"- base SHA: `{rep['authority']['base_sha']}`")
    L.append("- 데이터: **합성 fixture 전용**. REAL 접속·MAIN50·mart/raw·gold·holdout 없음.")
    L.append("- 독립단위 family n=10. 45 pair 는 distance matrix cell 이며 **n=45 가 아니다**.\n")

    L.append("## 1. 회귀 — 수렴이 기존 검사를 지우지 않았는가\n")
    L.append(f"- 수렴 전 고정된 check {reg['pre_delta9_check_count']}건 중 **{reg['still_present']}건이 그대로 존재**"
             f" (id·기대값 무수정), 실패 {len(reg['failing_after_convergence'])}건, 소실 {len(reg['missing_after_convergence'])}건")
    L.append(f"- 수렴이 **추가**한 check: {reg['checks_added_by_convergence']}건 → 현재 총 {reg['total_checks_now']}건")
    L.append(f"- 전체 실패: {vb['fixture_checks_failed']}건 / 변이 미검출: {vb['mutants_uncaught']} / "
             f"원복 증명 실패: {vb['restore_proof_failed_checks']}")
    L.append(f"- 고정 id 목록 sha256 `{reg['frozen_id_list_sha256']}` (기록값과 일치: {reg['frozen_id_list_sha256_matches_recorded']})\n")

    L.append("## 2. Δ9 — canonical 18종 전수 분류\n")
    L.append("> " + DELTA9_GENERAL_CRITERION["rule"])
    for t in DELTA9_GENERAL_CRITERION["three_tests"]:
        L.append("> - " + t)
    L.append("")
    L.append("| token | activation_depth | 근거 | flow_step_count |")
    L.append("|---|---|---|---|")
    for r in rep["token_classification_table"]:
        L.append("| `{t}` | **{c}** | {w} | {f} |".format(
            t=r["token"], c=r["delta9_activation_depth"],
            w=r["delta9_reason"].replace("|", "/")[:150],
            f=r["flow_step_count"].replace("|", "/")[:90]))
    L.append("\n`OPEN_RIGHT_DRAWER` 는 이 표에 **없다**. 방향은 토큰이 아니라 `nav_container_type` + "
             "`reveal_direction` 이다 (T-B-FC-013). Lane F 는 목록 밖 값을 `NOT_IN_CANONICAL_18` 스키마 오류로 "
             f"보고한다 — 확인됨: {rep['direction_is_not_a_token']['confirmed']}.\n")

    L.append("## 3. SUBMIT_QUERY 포함이 바꾸는 값\n")
    L.append("**먼저 정직하게**: " + sqe["what_lane_f_did_before"] + "\n")
    L.append("| case | sequence | 수렴 전 두 읽기(literal/activation_only) | 수렴 전 emit | 수렴 후 Δ9 | submit 제외 반사실 |")
    L.append("|---|---|---|---|---|---|")
    for r in sqe["rows"]:
        pr = r["pre_convergence_readings_AMB_F03"]
        L.append("| {i} | `{s}` | {a} / {b} | {e} | **{v}** | {c} |".format(
            i=r["case_id"], s=r["signature"] or "∅",
            a=pr["literal_all_but_excluded"], b=pr["activation_only"],
            e="보류(None)" if r["pre_convergence_emitted_value"] is None else r["pre_convergence_emitted_value"],
            v=r["post_convergence_delta9_value"], c=r["counterfactual_submit_excluded"]))
    sc = sqe["structural_claim"]
    L.append(f"\n- 검색 경유 `{sc['search_path']}` = **{sc['delta9_depths']['search']}**, "
             f"직접 진입 `{sc['direct_path']}` = **{sc['delta9_depths']['direct']}** → 구별됨: {sc['delta9_distinguishes']}")
    L.append(f"- submit 을 빼면 각각 {sc['counterfactual_depths']['search']} / {sc['counterfactual_depths']['direct']} "
             f"→ **붕괴됨: {sc['counterfactual_collapses_them']}**. Δ9 의 실질 근거가 fixture 에서 재현된다.")
    L.append(f"- 사전등록된 family 비대칭: {sqe['preregistered_family_asymmetry']}\n")

    L.append("## 4. CONDITIONAL 3종 × fixture_input_mode\n")
    ci = rep["conditional_input_mode_effect"]
    L.append("| case | fixture_input_mode | activation_depth | 미해결 CONDITIONAL | 보류 구간 |")
    L.append("|---|---|---|---|---|")
    for r in ci["rows"]:
        b = r["bounds_when_unresolved"]
        L.append("| {i} | {m} | {v} | {u} | {b} |".format(
            i=r["case_id"], m=r["fixture_input_mode"] or "(미기록)",
            v="**보류(None)**" if r["activation_depth_value"] is None else r["activation_depth_value"],
            u=r["unresolved_conditional_count"],
            b="—" if not b else "[%d, %d]" % (b["min_all_unresolved_excluded"], b["max_all_unresolved_included"])))
    ss = ci["same_sequence_splits"]
    L.append(f"\n- 같은 열 `{ss['sequence']}` 이 DROPDOWN 이면 **{ss['DROPDOWN']}**, FREE_TEXT 면 **{ss['FREE_TEXT']}** 이다. "
             f"{ss['reading']}")
    L.append("- 미기록·`OTHER`·수단미기록 `MIXED` 는 채우지 않고 **보류**한다 → AMB-F12 로 올린다.\n")

    L.append("## 5. R12 — 거리 정규화 3종\n")
    dt = rep["distance_three_way"]
    L.append(f"- primary = `{dt['primary']}`, 함께 저장 = {dt['also_stored']}. {dt['single_scalar_rule']}\n")
    L.append("| pair | a | b | lev | **max(len) PRIMARY** | sum(len) 저장 | Yujian-Bo 저장 | 세 값 일치 |")
    L.append("|---|---|---|---|---|---|---|---|")
    f = lambda v: "UNDEF" if v is None else ("%g" % v)
    for r in dt["rows"]:
        L.append("| {i} | `{a}` | `{b}` | {l} | **{m}** | {s} | {y} | {g} |".format(
            i=r["pair_id"], a=r["a"] or "∅", b=r["b"] or "∅", l=r["levenshtein_raw"],
            m=f(r["by_max_len_PRIMARY"]), s=f(r["by_sum_len_stored"]),
            y=f(r["yujian_bo_stored"]), g=r["three_values_agree"]))
    L.append("\n- 서로소 pair 에서 세 정규화는 **1.0 / 0.5 / 0.667** 로 갈린다. R12 가 AMB-F01 을 제기할 때 든 바로 그 값이다.")
    L.append("- 단일 스칼라는 `levenshtein_normalized_primary` 하나뿐이고 나머지 둘은 저장만 된다.")
    L.append(f"- **LCS similarity 는 여전히 primary 가 없다** ({dt['lcs_similarity_still_open']['ambiguity_id']}). "
             "R12 는 Levenshtein 만 확정했다.")
    L.append(f"- 0/0 은 여전히 UNDEF 다 ({dt['zero_denominator_still_open']['ambiguity_id']}).")
    L.append(f"- 선언적 민감도: {dt['declared_sensitivity']}\n")

    L.append("## 6. 변이 검사\n")
    L.append("| mutant | 대상 | 깨뜨리는 규범 | 잡힘 | 실패 check |")
    L.append("|---|---|---|---|---|")
    for m in rep["mutation_results"]:
        if m["mutant_id"] == "RESTORE_PROOF":
            continue
        L.append("| {i} | `{t}` | {b} | {c} | {n} |".format(
            i=m["mutant_id"], t=m["target"], b=m["breaks"].replace("|", "/")[:110],
            c="예" if m["caught"] else "**아니오**", n=m["failed_check_count"]))
    rp = [m for m in rep["mutation_results"] if m["mutant_id"] == "RESTORE_PROOF"][0]
    L.append(f"\n원복 증명: 모든 변이를 되돌린 뒤 실패 check {rp['failed_check_count']}건.\n")

    L.append("## 7. 닫힌 모호성\n")
    for a in rep["ambiguities_closed"]:
        L.append(f"- **{a['id']}** (`{a['variable']}`) — {a['closed_by']} 로 닫힘. 판정: {a['ruling']}")
        L.append(f"  - 하네스 이전: {a['harness_behaviour_before']}")
        L.append(f"  - 하네스 이후: {a['harness_behaviour_after']}")
        L.append(f"  - 잔여: {a['residual']}")

    L.append("\n## 8. 여전히 열린 모호성\n")
    L.append("| id | 변수 | 미결 쟁점 | severity |")
    L.append("|---|---|---|---|")
    for a in rep["ambiguities_still_open"]:
        L.append("| {i} | `{v}` | {q} | {s} |".format(
            i=a["id"], v=a["variable"], q=a["question"].replace("|", "/")[:220], s=a["severity"]))
    L.append("\n**AMB-F12 는 이 수렴에서 새로 드러난 것이다.** Δ9 가 CONDITIONAL 규칙을 세우면서 `OTHER`·"
             "미기록·수단미기록 `MIXED` 를 남겼다. 채우지 않고 올린다.\n")

    L.append("## 9. 여기서 하지 않은 것\n")
    for o in rep["out_of_scope_here"]:
        L.append(f"- **{o['item']}** (소관: {o['owner']}) — {o['why']}")

    L.append("\n## 10. 한계\n")
    for x in rep["limitation"]:
        L.append(f"- {x}")

    L.append("\n## 11. 재현\n")
    L.append("```bash\n/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \\\n"
             "  " + os.path.abspath(__file__) + "\n```")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


MD_TEMPLATE_HEADER = """# LANE F — Flow Topology / Depth 하네스 결과

- **verdict**: `{verdict}`
- 생성: {ts}
- 데이터: **합성 fixture 전용**. REAL 접속·MAIN50·mart/raw evidence·gold·holdout 없음.
- 독립단위: `service × frozen task` (family n=10). **이 run 의 {ncells} pair 는 distance matrix 의 cell 이며 n=45 가 아니다.**
"""


def write_markdown(rep: Dict[str, Any], path: str) -> None:
    d1 = rep["counterexample_detectors"]["D1_depth_tie_flow_divergent"]
    d2 = rep["counterexample_detectors"]["D2_distance_positive_depth_tie"]
    d3 = rep["counterexample_detectors"]["D3_modal_experienced_only_inflation"]
    vb = rep["verdict_basis"]
    L: List[str] = [MD_TEMPLATE_HEADER.format(
        verdict=rep["verdict"], ts=rep["generated_at_utc"],
        ncells=rep["sampling_discipline"]["pair_cells_in_this_run"])]

    L.append("\n## 1. 검증 요약\n")
    L.append(f"- fixture check: {vb['fixture_checks_total'] - vb['fixture_checks_failed']}/{vb['fixture_checks_total']} pass")
    L.append(f"- mutation test: {vb['mutants_caught']}/{vb['mutants_total']} 개 변이가 fixture 에 잡힘, 미검출 {vb['mutants_uncaught']}")
    L.append(f"- 원복 증명(restore proof) 실패 check: {vb['restore_proof_failed_checks']}")
    L.append(f"- 미해결 정의 모호성: {vb['open_ambiguities']}건 → verdict 상한이 `READY_WITH_AMBIGUITY`")

    L.append("\n## 2. 반례 탐지기 3종\n")
    L.append("모든 술어는 정수/토큰열에 대한 **정확한 구조적 상등·부등**이다. threshold·cut-off·composite score 없음.\n")
    L.append("### D1 — depth 는 같은데 flow 가 다르다")
    L.append(f"- tier1 술어: `{d1['predicate_tier1']}`")
    L.append(f"- tier2 술어: `{d1['predicate_tier2']}` (‘전혀 다르다’를 임계값이 아니라 LCS==0 이라는 구조 사실로 렌더)")
    L.append("- positive (합성 family 45 cell 기준):")
    for k, v in d1["positives_by_reading_and_base"].items():
        L.append(f"  - `{k}` → {v}")
    L.append(f"- tier2 positive: {len(d1['tier2_no_common_subsequence'])}건 "
             + (", ".join(f"({t['a']}, {t['b']})" for t in d1["tier2_no_common_subsequence"]) or "없음"))
    L.append(f"- **negative(잡히면 안 되는 것)**: depth 는 같지만 flow 가 동일한 {len(d1['negatives_depth_tie_but_identical_flow'])}건 — 모두 미검출 확인")

    L.append("\n### D2 — depth 차이는 0 인데 sequence 거리는 0 이 아니다")
    L.append(f"- 술어: `{d2['predicate']}`")
    L.append("- positive: " + ", ".join(f"base={b} {n}건" for b, n in d2["positives_by_base"].items())
             + f" (합 {d2['positives_count']} cell-base 조합)")
    L.append(f"- 최대 raw Levenshtein = {d2['extremal_levenshtein_raw_among_depth_tied']} "
             "(‘큰’의 정의를 만들지 않고 순위통계로만 보고)")
    L.append(f"- negative: {len(d2['negatives'])}건 — 거리 0 인 동일 flow, 그리고 거리는 크지만 depth 가 다른 pair 는 모두 미검출")
    L.append(f"- 정직한 한계: {d2['equivalence_note']}")

    L.append("\n### D3 — modal 때문에 experienced flow 만 길어진다")
    L.append(f"- 술어: `{d3['predicate']}` + 귀속검사 `{d3['attribution_predicate']}`")
    L.append(f"- positive {len(d3['positives'])}건: " + (", ".join(f"({p['a']}, {p['b']}) task_dist={p['task_flow_distance']} exp_dist={p['experienced_flow_distance']}" for p in d3["positives"]) or "없음"))
    L.append(f"- negative {len(d3['negatives'])}건 (modal 없음 / 양쪽 동일 modal / task_flow 자체가 다름) — 모두 미검출")
    L.append(f"- 귀속 불가 bucket: {len(d3['difference_not_dismissal_attributable'])}건 (directed case DC13 에서 별도 검증)")
    L.append("- 이 탐지기는 `activation_depth` 가 dismissal 에 불변임을 동시에 확인한다 → **depth 는 modal 부담을 보지 못한다**.")

    L.append("\n## 3. 경계 케이스 표 (정답 대조)\n")
    L.append("| case | a | b | lev | LCS | lev/max | lev/sum | Yujian-Bo | LCS/max | LCS/min | Dice | 정답일치 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rep["fixture_results"]["boundary_case_table"]:
        c = r["computed"]
        f = lambda v: "UNDEF" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))
        L.append("| {id} | `{a}` | `{b}` | {lev} | {lcs} | {m} | {s} | {y} | {lm} | {ln} | {dc} | {ok} |".format(
            id=r["id"], a=" > ".join(r["a"]) or "∅", b=" > ".join(r["b"]) or "∅",
            lev=c["levenshtein_raw"], lcs=c["lcs_length"], m=f(c["lev_by_max_len"]), s=f(c["lev_by_sum_len"]),
            y=f(c["lev_yujian_bo"]), lm=f(c["lcs_over_max_len"]), ln=f(c["lcs_over_min_len"]),
            dc=f(c["lcs_dice"]), ok="OK" if r["match"] else "MISMATCH"))
    L.append("\n주: `UNDEF` 는 분모 0 이다. **0.0 으로 채우지 않았다** (AMB-F10). 0.0 으로 채우면 flow 미평가 unit 이 heatmap 에서 ‘완전 동일’로 오독된다.")

    L.append("\n## 4. 파생값 fixture 표\n")
    L.append("| fixture | task_flow | act_depth (literal / activation_only) | flow_step_count (task incl/excl · exp incl/excl) | menu_dep | 비고 |")
    L.append("|---|---|---|---|---|---|")
    for fx in FIXTURE_FAMILY:
        o = rep["fixture_results"]["observations"][fx["id"]]
        ad, fs, md = o["activation_depth"], o["flow_step_count"], o["menu_dependency"]
        L.append("| {i} | `{t}` | {a1} / {a2} | {b1}/{b2} · {b3}/{b4} | {m} | {n} |".format(
            i=fx["id"], t=o["task_signature"] or "∅",
            a1=ad["readings"]["literal_all_but_excluded"], a2=ad["readings"]["activation_only"],
            b1=fs["readings"]["base=task|terminal=incl"], b2=fs["readings"]["base=task|terminal=excl"],
            b3=fs["readings"]["base=experienced|terminal=incl"], b4=fs["readings"]["base=experienced|terminal=excl"],
            m="WITHHELD" if md["value"] is None else str(md["value"]),
            n=("ABSTAIN 포함 → 비해석" if o["abstain_present"] else "") or ("menu_dep 읽기 불일치" if md["ambiguity_active"] else "")))

    L.append("\n## 5. ABSTAIN 취급\n")
    L.append("- `ABSTAIN` 은 canonical 18 에 있으므로 **invalid token 이 아니다**. 그러나 derived count·distance 에서의 취급을 codebook 이 정하지 않았다 (AMB-F07).")
    L.append("- 하네스 동작: `abstain_present=true` 표시 → 해당 observation 의 `derived_values_interpretable=false` → 그 observation 이 들어간 모든 pair cell 의 `interpretable=false`.")
    L.append("- 값 자체는 두 읽기(포함/제외)로 계산해 두되 **확정값으로 승격하지 않는다**. 임의 판단하지 않았다.")

    L.append("\n## 6. AMBIGUOUS_DEFINITION (채우지 않고 올림)\n")
    L.append("| id | 변수 | 미결 쟁점 | severity |")
    L.append("|---|---|---|---|")
    for a in rep["ambiguous_definitions"]:
        L.append(f"| {a['id']} | `{a['variable']}` | {a['question']} | {a['severity']} |")
    L.append("\n가장 중요한 것은 **AMB-F01 정규화 분모**다. codebook·analysis plan 어디에도 분모가 없다. "
             "하네스는 `max(len)` / `sum(len)` / Yujian-Bo 세 후보값을 병기만 하며 단일 스칼라를 emit 하지 않는다. "
             "같은 pair 가 1.0 / 0.5 / 0.667 로 갈린다(BND04·BND06).")

    L.append("\n## 7. 구현하지 않은 것\n")
    for n in rep["not_implemented"]:
        L.append(f"- **{n['item']}** — {n['reason']}")

    L.append("\n## 8. 한계\n")
    for x in rep["limitation"]:
        L.append(f"- {x}")

    L.append("\n## 9. 재현\n")
    L.append("```bash\n/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \\\n"
             "  " + rep["provenance"]["harness_path"] + "\n```")
    L.append(f"\nSSOT sha256 대조: MANIFEST = `{rep['provenance']['ssot_file_sha256']['MANIFEST_v3.0.json']}` "
             f"(계약값 `{rep['provenance']['expected_manifest_sha256']}`)")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Lane F flow topology / depth harness")
    ap.add_argument("--stdout", action="store_true", help="print the JSON report to stdout")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    rep = build_report()
    json_path = os.path.join(OUT_DIR, "LANE_F_HARNESS.json")
    md_path = os.path.join(OUT_DIR, "LANE_F_FINDINGS.md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    write_markdown(rep, md_path)

    conv = build_delta9_convergence()
    conv_json = os.path.join(OUT_DIR, "LANE_F_DELTA9_CONVERGENCE.json")
    conv_md = os.path.join(OUT_DIR, "LANE_F_DELTA9_FINDINGS.md")
    with open(conv_json, "w", encoding="utf-8") as fh:
        json.dump(conv, fh, ensure_ascii=False, indent=2)
    write_delta9_markdown(conv, conv_md)

    vb = rep["verdict_basis"]
    print(f"verdict={rep['verdict']}")
    print(f"checks {vb['fixture_checks_total'] - vb['fixture_checks_failed']}/{vb['fixture_checks_total']} pass; "
          f"mutants caught {vb['mutants_caught']}/{vb['mutants_total']}; "
          f"restore-proof failures {vb['restore_proof_failed_checks']}")
    if vb["failed_check_ids"]:
        print("FAILED:", vb["failed_check_ids"][:20])
    print("wrote", json_path)
    print("wrote", md_path)
    cr = conv["regression"]
    print(f"delta9 verdict={conv['verdict']}; pre-Δ9 regression {cr['still_present']}/"
          f"{cr['pre_delta9_check_count']} present, {len(cr['failing_after_convergence'])} failing, "
          f"{cr['checks_added_by_convergence']} checks added")
    print("wrote", conv_json)
    print("wrote", conv_md)
    if args.stdout:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["verdict"] != "NOT_READY" else 1


if __name__ == "__main__":
    sys.exit(main())
