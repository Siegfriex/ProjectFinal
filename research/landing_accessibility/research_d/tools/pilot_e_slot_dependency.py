"""D-PILOT-E — Evidence Slot Dependency Matrix.

RQ: Axis A(KWCAG) / Axis B(depth) / Axis C(obstruction) 이 공유하는 raw evidence slot 은
무엇이며, 그 공유가 planned association 에서 correlated measurement error 를 만들 수 있는
pair 는 어디인가.

SSOT 00 v2.1 §3 은 세 축을 **독립 측정축**으로 규정하고 §15/§16 은 단일 composite 합산을
금지한다. 이 스크립트는 그 전제가 **측정 공정(evidence slot) 수준에서** 성립하는지를
exact-SHA 코드 독해 + frozen evidence 재계산으로 본다.

authority: NON_CANONICAL. construct 결정(어느 축을 고칠지)은 A 의 권한이며 여기서 하지 않는다.
causal claim 을 하지 않는다 — "이 slot 을 공유하므로 상관될 수 있다" 까지만 말한다.

firewall: holdout label · LABEL_SPLIT_FROZEN* · HOLDOUT_FOR_C* · RAW_L1~L4* · PACKET_L* ·
  *_OVERLAP* · PRECEDENCE_CONTESTED* · CALIBRATION_FOR_B* · **/control/** 은
  not_opened = 전부 열지 않았다. 입력은 INPUTS 에 적힌 것이 전부다.
"""

from __future__ import annotations

import glob
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

KST = timezone(timedelta(hours=9))
SEED = 20260827
CODE_SHA = "2281c853950d0c475c5d2c1678680b971c2804f4"

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
WT = REPO / ".agent_worktrees"
RD = WT / "claude_d_research/research/landing_accessibility/research_d"
MART = WT / "claude_b_analysis_current/artifacts/e001_real_marts"
OBS_TABLE = RD / "results/D_OBSERVATION_TABLE_v2.csv"
SSOT = REPO / "SSOTV2/00_SSOT_v2.1_POST_PILOT_RECOVERY.md"
EVIDENCE_GLOB = "claude_b_e001_worker_0*/artifacts/e001_w0*/evidence"

OUT_JSON = RD / "results/PILOT_E_slot_dependency.json"
FIG_DIR = RD / "figures"

# probe(l0_probe.js:379-381) 의 dismiss 어휘를 그대로 옮긴다 — 재판정이 아니라 귀속 분석용이다.
CLOSE_WORDS = re.compile(
    r"(닫기|닫음|확인|취소|동의|건너뛰기|나중에|오늘\s*하루\s*보지\s*않기|다시\s*보지\s*않기|"
    r"close|dismiss|skip|no\s*thanks|got\s*it|accept)",
    re.IGNORECASE,
)

# ─────────────────────────────────────────────────────────────────────────────
# 1. slot × 축 행렬 — 모든 cell 은 exact SHA 코드 라인 또는 SSOT 절을 근거로 갖는다.
#    status 어휘:
#      CONSUMED       그 축의 산출값이 이 slot 을 실제로 읽는다 (코드 라인 있음)
#      CONSUMED_PARTIAL 일부 하위신호만 읽는다
#      CONSUMED_INDIRECT 다른 축의 산출을 경유해서만 영향을 받는다
#      PLANNED_ONLY   SSOT 가 그 축에 요구하지만 @SHA 에 소비 코드가 없다
#      NOT_CONSUMED   @SHA 에 소비 코드가 없고 SSOT 도 요구하지 않는다
#      UNKNOWN        판단 근거가 없다 (이유를 적는다)
# ─────────────────────────────────────────────────────────────────────────────
SLOT_MATRIX: list[dict] = [
    {
        "slot": "aria-label (DOM attribute)",
        "captured_at": "l0_probe.js:173 accessible_name_sources.aria_label; :206 overlay aria_modal 인접 :216 overlay aria_label; :288 primary_action_candidates.aria_label; :350/:360/:364 gate_signals 가 aria-label 을 읽음; :394 dismiss control accessible_name_source",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "KWCAG accessible-name 계열 criterion (레이블 제공 / 대체 텍스트 / 명확한 지시사항)",
            "evidence": "SSOT 00 §9 '각 criterion 은 raw evidence 와 exact evaluator version 을 연결한다' + §9 자동화 우선순위 1 browser-native/AX. @2281c85 engine/ 에 KWCAG evaluator 모듈이 **없다** (engine/ 파일목록에 kwcag/criterion evaluator 부재; fact_criterion_result.json = 0행).",
        },
        "axis_b": {
            "status": "CONSUMED",
            "consumer": "TaskStep.accessible_name; endpoint_status(gate 경유); activation 후보 제외(dismiss 경유)",
            "evidence": "l0_collector.py:353 accessible_name=aria_label or visible_text; l1_engine.py:505-506 동일식; l0_probe.js:360/:364 identity/otp count 가 aria-label 매칭 → gate_classifier.py:89 _IDENTITY_STRUCTURAL → depth.gate_outcome → endpoint_status; l1_engine.py:346-357 dismiss selector 집합에 든 후보를 activation 후보에서 제외",
        },
        "axis_c": {
            "status": "CONSUMED",
            "consumer": "interrupt 의미분류(final_label); dismiss_control_exists/visible/accessible_name",
            "evidence": "l0_collector.py:267-272 classify_interrupt 가 accessible_text+aria_label 을 _LABEL_RULES 에 넣음; l0_probe.js:394 name=aria-label||title||textContent → :400 matches_close_vocabulary, :402 icon_only → :409 filter; l0_collector.py:669-671 dismiss_control_accessible_name",
        },
    },
    {
        "slot": "accessible name (AX tree, CDP computed)",
        "captured_at": "l0_collector.py:404-434 _ax_tree (Accessibility.getFullAXTree); :505 l0a/ax.json 저장; :424-426 name / name_computed 로 NAME_ABSENT 와 NULL 구분 보존",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "SSOT §9 자동화 우선순위 1(browser-native/AX) 이 지정한 Axis A 1차 증거",
            "evidence": "SSOT 00 §5 L0 evidence 목록 'Accessibility Tree via browser/CDP'; §9. 소비 코드 부재(위와 동일).",
        },
        "axis_b": {
            "status": "NOT_CONSUMED",
            "consumer": None,
            "evidence": "l1_engine.py:317-331 _observe 는 PROBE_JS 재평가 + page.content() 만 쓴다. ax.json 을 읽는 경로가 없다. SSOT §8.1 은 DOM_AX_ROLE region signal 을 요구하므로 이는 SSOT 대비 **미구현 gap** 이다.",
        },
        "axis_c": {
            "status": "NOT_CONSUMED",
            "consumer": None,
            "evidence": "l0_collector.py:258-282 classify_interrupt 는 probe raw feature 만 본다.",
        },
    },
    {
        "slot": "visible text (textContent / innerText)",
        "captured_at": "l0_probe.js:117 contrast 텍스트노드; :179 accessible_name_sources.visible_text; :214 overlay accessible_text; :289 primary_action_candidates.visible_text; :332 body.innerText(4000자 상한) → :353 gate_signals.visible_text; :394 dismiss name fallback",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "명도대비 대상 텍스트, 레이블/대체텍스트 criterion",
            "evidence": "l0_probe.js:111 '임계값 비교 없음' — verdict 층이 분리되어 있고 @SHA 에 존재하지 않는다.",
        },
        "axis_b": {
            "status": "CONSUMED",
            "consumer": "TaskStep.accessible_name fallback; gate 종류 판별 → endpoint_status",
            "evidence": "l0_collector.py:353-354; l1_engine.py:505-506; gate_classifier.py:70-88 _LOGIN_TEXT/_IDENTITY_TEXT/_CARRIER_TEXT 정규식이 :111 GateSignals.text(=probe gate_signals.visible_text) 에 걸림 → depth.py:48-75 gate_outcome → endpoint_status",
        },
        "axis_c": {
            "status": "CONSUMED",
            "consumer": "interrupt final_label; dismiss control 어휘매칭",
            "evidence": "l0_collector.py:114-121 _LABEL_RULES + :267-272; l0_probe.js:394/:400",
        },
    },
    {
        "slot": "title attribute",
        "captured_at": "l0_probe.js:175 accessible_name_sources.title; :394 dismiss name 2순위; :107 document.title(viewport 메타)",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "accessible name 계산 소스",
            "evidence": "SSOT §9. 소비 코드 부재.",
        },
        "axis_b": {
            "status": "CONSUMED_INDIRECT",
            "consumer": "activation 후보 제외 (title 로 이름이 생긴 control 이 dismiss 로 잡히면 Axis B 후보에서 빠진다)",
            "evidence": "l0_probe.js:394 name 에 title 포함 → :400/:409 dismiss 후보 확정 → l1_engine.py:346-357 제외. primary_action_candidates 자체에는 title 필드가 없다(l0_probe.js:286-302).",
        },
        "axis_c": {
            "status": "CONSUMED",
            "consumer": "dismiss_control accessible_name_source",
            "evidence": "l0_probe.js:394",
        },
    },
    {
        "slot": "AX role (CDP)",
        "captured_at": "l0_collector.py:414-418 role 추출, :416 role in (None,'none','InlineTextBox') 제외; :505 ax.json",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "role/name/state 기반 criterion",
            "evidence": "SSOT §5 · §9. 소비 코드 부재.",
        },
        "axis_b": {
            "status": "NOT_CONSUMED",
            "consumer": None,
            "evidence": "SSOT §8.1 이 DOM_AX_ROLE 를 region signal type 으로 명시했으나 l1_engine.py:201-218 detect_area_signal 은 region_signals(declared_regions / search_inputs) 만 읽는다. AX role 경로 미구현.",
        },
        "axis_c": {"status": "NOT_CONSUMED", "consumer": None, "evidence": "소비 코드 부재."},
    },
    {
        "slot": "DOM role attribute / tagName",
        "captured_at": "l0_probe.js:143-144 target_size 질의; :158 role; :169-172 accessible_name_sources 질의; :225 [role=dialog],[role=alertdialog]; :277-278 primary action 질의; :287 role; :393 dismiss 질의",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "target size / name 대상 집합 정의",
            "evidence": "l0_probe.js:143-144 는 Axis A 의 target_size raw feature 대상 집합을 role 로 고른다. 판정층 부재.",
        },
        "axis_b": {
            "status": "CONSUMED",
            "consumer": "activation 후보 집합; TaskStep.control_role",
            "evidence": "l0_probe.js:277-278 [role=button],[role=link],[role=tab] 포함; l0_collector.py:352 control_role=role or tag; l1_engine.py:504",
        },
        "axis_c": {
            "status": "CONSUMED",
            "consumer": "modal 후보 sources; dismiss control 집합",
            "evidence": "l0_probe.js:224-226 dialog_element/role_dialog/aria_modal; l0_collector.py:275-279 modal_like; l0_probe.js:393",
        },
    },
    {
        "slot": "URL / final_url",
        "captured_at": "l0_probe.js:94 · :108 final_url; l0_collector.py:498 final_url=page.url; :557",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "관측 provenance (criterion 판정의 대상 식별)",
            "evidence": "SSOT §5 manifest/hash provenance. 판정 소비 없음.",
        },
        "axis_b": {
            "status": "CONSUMED",
            "consumer": "state_key(상태전이 식별); TaskStep.url; replay 검증",
            "evidence": "l1_engine.py:194-197 state_key(url,dom); :502 step url; :522 expected_url_tail; :790 replay 대조. SSOT §8.1 URL_PATTERN.",
        },
        "axis_c": {"status": "NOT_CONSUMED", "consumer": None, "evidence": "소비 코드 부재."},
    },
    {
        "slot": "form structure (form / submit / autocomplete / label[for])",
        "captured_at": "l0_probe.js:180 labelled_by_for; :316-326 search_inputs(in_form, has_submit); :344-345 autocompleteCount; :354-372 gate 구조신호; :413 form[method=dialog]",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "레이블 제공 criterion (label[for] / autocomplete)",
            "evidence": "l0_probe.js:180 이 그 자리를 만들어 두었으나 판정층 부재.",
        },
        "axis_b": {
            "status": "CONSUMED",
            "consumer": "QUERY archetype 의 area_signal; gate 구조신호 → endpoint_status",
            "evidence": "l1_engine.py:208-212 (visible ∧ in_form ∧ has_submit); gate_classifier.py:69 _LOGIN_STRUCTURAL · :89 _IDENTITY_STRUCTURAL ← l0_probe.js:354-372",
        },
        "axis_c": {
            "status": "CONSUMED_PARTIAL",
            "consumer": "dismiss method DIALOG_CLOSE 경로",
            "evidence": "l0_probe.js:393 form[method=dialog] button · :413 has_form_method_dialog → l0_collector.py:707-712 DIALOG_CLOSE",
        },
    },
    {
        "slot": "geometry (getBoundingClientRect box / viewport coverage)",
        "captured_at": "l0_probe.js:31-36 box(); :46-52 intersectArea/viewportBox; :147-164 target_size; :218-219 viewport_overlap/coverage; l0_collector.py:88-95 computed_css box",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "target size(2.5.x 계열) criterion, 명도대비 대상의 위치",
            "evidence": "l0_probe.js:141 'target size raw feature — CSS px, DPR 곱하지 않음'; :7 '가져오지 않은 것: KWCAG 임계값 비교(required)'. SSOT §9 자동화 우선순위 2(deterministic geometry/CSS).",
        },
        "axis_b": {
            "status": "NOT_CONSUMED",
            "consumer": None,
            "evidence": "l0_collector.py:304-316 min4_sort_key 가 area_css_px2 를 tie-break 키에서 **의도적으로 제외** ([V2-C010b 시정]: '관측 잡음이 있는 면적을 정렬 키로 쓰면 순서가 잡음을 따라간다'). l1_engine.py 전체에 box/coverage/area 참조 없음(grep 확인).",
        },
        "axis_c": {
            "status": "CONSUMED",
            "consumer": "OverlayCoverage, PrimaryActionOcclusion, blocks_primary_action, max_overlay_coverage",
            "evidence": "l0_collector.py:250-255 _overlap; :627-637 occlusion/blocking; :575-577 max_overlay_coverage; :582 max_primary_action_occlusion. SSOT §10.",
        },
    },
    {
        "slot": "hittability (document.elementFromPoint)",
        "captured_at": "l0_probe.js:54-62 hittable(); :220 overlay hittable; :301 primary action hittable; :313/:324 region hittable; :406 dismiss control hittable; l0_collector.py:98-111 _DISMISS_STATE_JS",
        "axis_a": {
            "status": "UNKNOWN",
            "consumer": None,
            "evidence": "SSOT §9 는 criterion 별 required evidence slot 을 evaluator 가 선언하라고만 하고 목록을 고정하지 않았다. evaluator 가 없으므로 Axis A 가 hittability 를 요구하는지 알 수 없다 — 추측으로 채우지 않는다.",
        },
        "axis_b": {
            "status": "CONSUMED",
            "consumer": "activation 후보 필터, area_signal(HITTABLE), forced_dismissal 실행 가능성",
            "evidence": "l1_engine.py:354 c.get('hittable') 필터; :202 'PRESENT ∧ HITTABLE ∧ NO_FURTHER_ACTIVATION'; :726 dismiss blocker 도 hittable 만 클릭. SSOT §8.1.",
        },
        "axis_c": {
            "status": "CONSUMED",
            "consumer": "dismiss_control_visible, best control 선택, dismiss_succeeded",
            "evidence": "l0_collector.py:641-643 best=첫 hittable; :652 visible_flag 에 hittable 포함; :701 control 선택; :723-726 dismiss 성공판정",
        },
    },
    {
        "slot": "z-index / position (fixed·sticky)",
        "captured_at": "l0_probe.js:195-199 z/fixed/backdrop 후보조건; :209-211; :227-231 body * 스캔; :386-390 dismiss 컨테이너 스캔",
        "axis_a": {"status": "NOT_CONSUMED", "consumer": None, "evidence": "SSOT §9 에 해당 요구 없음."},
        "axis_b": {
            "status": "CONSUMED_INDIRECT",
            "consumer": "activation 후보 제외 집합의 **경계**를 정한다",
            "evidence": "l0_probe.js:386-390 이 fixed/sticky/z>=100 컨테이너 전부를 dismiss 스캔 대상으로 삼고, 그 안에서 나온 selector 가 l1_engine.py:346-357 에서 Axis B 후보를 깎는다.",
        },
        "axis_c": {
            "status": "CONSUMED",
            "consumer": "modal/overlay 후보 자격, BANNER 라벨",
            "evidence": "l0_probe.js:199 '!sources.length && !fixed && !(z>=100) → return'; l0_collector.py:280-281 position_sticky/fixed → BANNER",
        },
    },
    {
        "slot": "body scroll lock",
        "captured_at": "l0_probe.js:235-244 body_scroll_lock{body_overflow, body_position, html_overflow, locked}",
        "axis_a": {"status": "NOT_CONSUMED", "consumer": None, "evidence": "SSOT §9 에 해당 요구 없음."},
        "axis_b": {
            "status": "NOT_CONSUMED",
            "consumer": None,
            "evidence": "SSOT §3 · §8.2 가 scroll 을 depth 합산에서 제외한다. l1_engine.py 는 body_scroll_lock 을 읽지 않는다(grep 확인).",
        },
        "axis_c": {
            "status": "CONSUMED",
            "consumer": "blocks_primary_action, SSOT §3 Axis C 핵심 5요소 중 하나",
            "evidence": "l0_collector.py:620 scroll_locked; :636 (scroll_locked ∧ coverage>=0.5) → blocking. SSOT §3 Axis C 'body scroll lock'.",
        },
    },
    {
        "slot": "dismiss control (Axis C 파생이면서 Axis B 입력)",
        "captured_at": "l0_probe.js:377-418 dismiss_control_candidates (컨테이너별 목록)",
        "axis_a": {"status": "NOT_CONSUMED", "consumer": None, "evidence": "SSOT §9 에 해당 요구 없음."},
        "axis_b": {
            "status": "CONSUMED",
            "consumer": "activation 후보 집합에서의 **제외**; forced_dismissal_count",
            "evidence": "l1_engine.py:346-357 dismiss_selectors 에 든 selector 를 후보에서 뺀다(주석 :337-339 'popup 의 닫기 control 은 후보가 아니다'); :717-735 _dismiss_blockers → forced_dismissal_count. SSOT §3 'popup dismissal 은 depth 에 합산하지 않음'.",
        },
        "axis_c": {
            "status": "CONSUMED",
            "consumer": "dismiss_control_exists/visible/accessible_name/width/height, dismiss_persistence_hint, dismiss_succeeded, dismiss_failure_mode",
            "evidence": "l0_collector.py:639-674; :679-748. SSOT §3 Axis C 'dismiss control presence/visibility/actionability'.",
        },
    },
    {
        "slot": "computed CSS (color / background / contrast / font)",
        "captured_at": "l0_probe.js:64-89 lum/effectiveBg/contrastRatio; :111-139 contrast raw feature; l0_collector.py:69-96 _COMPUTED_CSS_PROPERTIES + _COMPUTED_CSS_JS → :508-510 computed_css.json",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "명도대비 criterion",
            "evidence": "l0_probe.js:5-8 '가져온 것: 상대휘도/명도대비 산식 … 가져오지 않은 것: KWCAG 임계값 비교(required), large_text 분류, 판정 문자열'; :111 '임계값 비교 없음'. 판정층 @SHA 부재.",
        },
        "axis_b": {"status": "NOT_CONSUMED", "consumer": None, "evidence": "l1_engine.py 에 color/contrast/font 참조 없음(grep 확인)."},
        "axis_c": {
            "status": "CONSUMED_PARTIAL",
            "consumer": "가시성(display/visibility/opacity) 판정만. 색/대비는 쓰지 않는다.",
            "evidence": "l0_probe.js:38-44 visible(); l0_collector.py:624 'if not cand.get(\"visible\"): continue'; :648-651 dismiss_control_visible",
        },
    },
    {
        "slot": "screenshot (viewport / full-page / dismiss before-after)",
        "captured_at": "l0_collector.py:512-517 screen_initial/screen_fullpage; :692-695 · :739-743 l0c before/after",
        "axis_a": {
            "status": "PLANNED_ONLY",
            "consumer": "SSOT §9 자동화 우선순위 4 (VLM) 및 5 (Human Final)",
            "evidence": "SSOT §5 'viewport screenshot / full-page screenshot'; §9. 소비 코드 부재.",
        },
        "axis_b": {
            "status": "NOT_CONSUMED",
            "consumer": None,
            "evidence": "l1_engine.py:124 TaskStep.screenshot_path 는 provenance 필드이며 어떤 판정에도 들어가지 않는다.",
        },
        "axis_c": {
            "status": "PROVENANCE_ONLY",
            "consumer": None,
            "consumer_note": "dismiss before/after 증거로 저장되지만 dismiss_succeeded 는 화면이 아니라 _DISMISS_STATE_JS 로 판정한다",
            "evidence": "l0_collector.py:723-726 판정은 DOM 상태로; 스크린샷은 :693 · :739 저장만",
        },
    },
]

SHARED_MECHANISMS: list[dict] = [
    {
        "pair_id": "E-P1",
        "pair": "Axis C → Axis B (dismiss control 이 activation 후보를 깎는다)",
        "shared_slots": ["dismiss control", "aria-label", "title", "visible text", "hittability", "z-index/position"],
        "mechanism": (
            "l0_probe.js:391-409 는 fixed/sticky/z>=100 컨테이너 안의 button/link 중 "
            "matches_close_vocabulary(:400) 또는 icon_only(:402) 인 것을 dismiss control 후보로 남긴다. "
            "l1_engine.py:346-357 은 그 selector 집합을 Axis B 의 activation 후보에서 뺀다. "
            "따라서 Axis C 의 dismiss detector 가 false positive 를 내면 Axis B 의 탐색공간이 그만큼 줄고, "
            "false negative 를 내면 Axis B 가 닫기버튼을 activation 으로 밟는다."
        ),
        "direction": "same",
        "direction_note": (
            "이름 slot(aria-label/title/visible text)이 빈약해지면 icon_only(:402) 가 더 자주 참이 되어 "
            "dismiss 후보가 **늘고**(Axis C 과탐), 같은 증가분이 Axis B 후보에서 **빠진다**. "
            "즉 두 축의 오차가 같은 원인에서 같은 부호로 생긴다 — Axis C 는 장애물을 과대, Axis B 는 깊이를 과대."
        ),
        "measurable_now": "yes",
        "measurable_note": "probe raw feature 로 제외 수를 그대로 재계산할 수 있다. Axis A 는 실측이 없어 proxy 로만.",
        "risk_level": "HIGH",
        "what_would_falsify_it": (
            "제외된 후보가 전부 실제 닫기 control 로 확인되면(즉 href 없는 순수 close control), "
            "그리고 제외 후에도 activation pool 이 비지 않으면 이 pair 의 실효 위험은 사라진다."
        ),
    },
    {
        "pair_id": "E-P2",
        "pair": "Axis A ↔ Axis C (accessible name slot 공유)",
        "shared_slots": ["aria-label", "visible text", "title", "DOM role"],
        "mechanism": (
            "Axis A 의 name 계열 criterion(SSOT §9)과 Axis C 의 두 산출 — interrupt final_label "
            "(l0_collector.py:267-272) 및 dismiss_control_* (l0_probe.js:394-402) — 이 **같은 세 문자열 소스**를 읽는다. "
            "페이지가 접근가능한 이름을 제공하지 않으면 Axis A 는 FAIL 방향, Axis C 는 "
            "'분류불가/닫기control 없음' 방향으로 동시에 움직인다."
        ),
        "direction": "same",
        "direction_note": (
            "같은 방향으로 '나쁨' 이 커진다. 다만 Axis C 쪽 결과는 두 갈래다: "
            "(a) 이름이 없어 어휘매칭 실패 → dismiss_control_exists=0 (장애물이 더 나빠 보임), "
            "(b) 이름이 없고 아이콘만 있어 icon_only 발동 → dismiss 후보 과탐 (장애물이 덜 나빠 보임). "
            "두 갈래가 같은 slot 결핍에서 갈라지므로 Axis C 오차의 부호가 페이지마다 뒤집힐 수 있다 — "
            "이것이 이 pair 를 단순한 same 이 아니라 'same-in-cause, mixed-in-sign' 로 만든다."
        ),
        "measurable_now": "proxy_only",
        "measurable_note": "fact_criterion_result 0행 → Axis A 실측 없음. dom_aria_label_n==0 을 proxy 로만 쓴다.",
        "risk_level": "HIGH",
        "what_would_falsify_it": (
            "Axis A evaluator 가 생산된 뒤, aria-label 빈약 층과 충분 층에서 Axis C 의 "
            "분류확정률·dismiss_control_exists 가 차이 없음이 확인되면 반박된다."
        ),
    },
    {
        "pair_id": "E-P3",
        "pair": "Axis A ↔ Axis B (accessible name + form structure + gate 텍스트)",
        "shared_slots": ["aria-label", "visible text", "form structure", "DOM role"],
        "mechanism": (
            "Axis B 의 endpoint_status 는 gate 종류 판별에 의존하고(depth.py:48-75), 그 판별 입력은 "
            "gate_classifier.py:70-88 의 텍스트 정규식 + :69/:89 의 구조신호다. 구조신호 중 "
            "identity_number_input_count 와 otp_input_count 는 l0_probe.js:357-364 에서 **aria-label 을 직접 읽는다**. "
            "즉 로그인/본인인증 화면이 접근가능한 이름을 주지 않으면 Axis A 는 FAIL 방향, "
            "Axis B 는 gate UNDETERMINED → endpoint 미승격 방향으로 함께 움직인다."
        ),
        "direction": "same",
        "direction_note": (
            "gate_classifier 는 모호하면 UNDETERMINED 로 abstain 하고(:22-23, :29-36) endpoint 로 올리지 않는다. "
            "따라서 이름 slot 결핍 → Axis A FAIL↑ 와 Axis B '깊이 미확정/미도달'↑ 가 같은 방향이다."
        ),
        "measurable_now": "no",
        "measurable_note": (
            "Axis A 0행이고 Axis B 도 NED/IED/MPFED 가 59/59 전부 None(RQ-D6)이라 **양쪽 다 변량이 없다**. "
            "endpoint_status 만 31행 있으나 endpoint_reached 는 31/31 이 0 이다."
        ),
        "risk_level": "MEDIUM_UNMEASURED",
        "what_would_falsify_it": (
            "gate 판별이 aria-label 없이 password/tel autocomplete 같은 브라우저-네이티브 구조신호만으로 "
            "동일한 판별을 낸다면(예: aria-label 필드를 ablation 해도 gate_kind 분포가 불변) 반박된다."
        ),
    },
    {
        "pair_id": "E-P4",
        "pair": "Axis B ↔ Axis C (hittability 공유)",
        "shared_slots": ["hittability", "z-index/position"],
        "mechanism": (
            "hittable() 은 요소 중심점의 elementFromPoint 결과가 그 요소(또는 그 후손/조상)인지로 정의된다"
            "(l0_probe.js:54-62). 오버레이가 떠 있으면 그 아래의 모든 control 이 hittable=false 가 된다. "
            "Axis B 는 hittable 인 후보만 activation 대상으로 삼고(l1_engine.py:354), "
            "Axis C 는 hittable 로 dismiss_control_visible 과 dismiss_succeeded 를 정한다(l0_collector.py:641-643, :652, :723-726). "
            "같은 오버레이가 두 축의 값을 동시에 결정한다."
        ),
        "direction": "same",
        "direction_note": (
            "오버레이가 hit-test 를 가로채면 Axis C 는 '장애물 있음' 을, Axis B 는 '후보 없음/경로 못 감' 을 "
            "동시에 기록한다. 이 상관은 **실체적 상관(진짜 장애물이 진짜로 경로를 막는다)과 "
            "측정오차 상관(중심점 한 점 hit-test 의 실패)이 같은 자리에서 겹친다** — 둘을 이 자료로는 못 가른다."
        ),
        "measurable_now": "partial",
        "measurable_note": "hittable 분포는 잴 수 있으나 Axis B 산출(NED/MPFED)이 전부 None 이라 결과쪽 변량이 없다.",
        "risk_level": "MEDIUM",
        "what_would_falsify_it": (
            "중심점 hit-test 대신 다점 hit-test(예: 요소 내 5점)로 바꿨을 때 Axis B 후보수와 "
            "Axis C dismiss_control_visible 이 서로 다른 방향으로 움직이면, 공유는 있어도 "
            "오차상관은 측정방식의 산물이 아니라는 뜻이 된다."
        ),
    },
    {
        "pair_id": "E-P5",
        "pair": "Axis A ↔ Axis C (geometry 공유)",
        "shared_slots": ["geometry (box/coverage)"],
        "mechanism": (
            "Axis A 의 target size raw feature(l0_probe.js:147-164)와 Axis C 의 OverlayCoverage/"
            "PrimaryActionOcclusion(l0_collector.py:250-255, :627-637)이 같은 getBoundingClientRect 산출을 쓴다. "
            "레이아웃이 아직 안정되지 않은 상태에서 캡처되면(SETTLE_MS=400, l0_collector.py:63) "
            "두 축의 기하값이 같은 시점 오차를 공유한다."
        ),
        "direction": "unknown",
        "direction_note": (
            "레이아웃 미안정의 부호가 정해져 있지 않다 — 늦게 뜨는 배너는 coverage 를 과소, "
            "collapse 전 컨테이너는 과대로 만든다. 방향을 정하려면 시점별 재캡처가 필요한데 "
            "frozen evidence 는 단일 시점뿐이다."
        ),
        "measurable_now": "no",
        "measurable_note": "단일 시점 캡처라 시점 오차의 부호를 식별할 수 없다. Axis A 는 0행.",
        "risk_level": "LOW_UNMEASURED",
        "what_would_falsify_it": "동일 target 을 여러 SETTLE_MS 로 재수집해 두 축의 기하값이 서로 다른 시점민감도를 보이면 반박.",
    },
]

COUNTEREXAMPLE_CANDIDATES: list[dict] = [
    {
        "slot": "geometry (box / area_css_px2)",
        "claim": "Axis C 가 강하게 소비하는 slot 인데 Axis B 는 **의도적으로** 소비하지 않는다",
        "evidence": (
            "l0_collector.py:304-316 min4_sort_key 독스트링: '`area_css_px2`는 tie-break 키에서 제외한다 "
            "[V2-C010b 시정] — 관측 잡음이 있는 면적을 정렬 키로 쓰면 어떤 양자화를 거쳐도 순서가 잡음을 따라간다'. "
            "l1_engine.py 전체에 box/coverage/area 참조 없음."
        ),
        "why_it_counts": (
            "공유 slot 이 있어도 소비 지점을 끊으면 축이 독립적으로 움직인다는 **존재증명**이다. "
            "이 프로젝트는 이미 한 번 그 결정을 내렸고 코드에 근거가 남아 있다."
        ),
        "caveat": "'독립적으로 움직인다' 를 실측으로 보인 것이 아니라 소비경로 부재로 보인 것이다. Axis B 산출이 전부 None 이라 실측 대조가 불가능하다.",
    },
    {
        "slot": "body scroll lock",
        "claim": "Axis C 의 핵심 5요소 중 하나인데 Axis B 는 SSOT 수준에서 배제되어 있다",
        "evidence": "SSOT 00 §3 Axis B 'scroll, text typing, redirect, passive wait, popup dismissal 은 depth 에 합산하지 않음'; l1_engine.py 에 body_scroll_lock 참조 없음; l0_collector.py:620/:636 은 Axis C 만.",
        "why_it_counts": "SSOT 정의 자체가 공유를 끊은 사례. 코드가 그 정의를 지키고 있다.",
        "caveat": "단 forced_dismissal_count(l1_engine.py:717-735)는 여전히 Axis C 산출을 경유하므로 Axis B 가 obstruction 과 완전히 무관하지는 않다.",
    },
    {
        "slot": "URL / final_url",
        "claim": "Axis B 가 강하게 소비하는데 Axis C 는 전혀 읽지 않는다",
        "evidence": "l1_engine.py:194-197 · :502 · :522 · :790 vs l0_collector.py 의 Axis C 경로(:602-677)에 URL 참조 없음.",
        "why_it_counts": "한 축 전용 slot 이 존재한다는 것 — 모든 slot 이 공유되는 것은 아니다.",
        "caveat": "공유가 없으므로 '공유가 있는데 독립' 이라는 요구된 형태의 반례는 아니다. 부분적 반례로만 센다.",
    },
]

NOT_ANSWERED: list[str] = [
    "Axis A 의 실제 측정오차와 Axis B/C 오차의 상관은 **추정 불가**다. fact_criterion_result 가 0행이고 "
    "@2281c85 engine/ 에 KWCAG evaluator 모듈 자체가 없다. 이 RQ 는 '어디서 생길 수 있는가' 까지만 답한다.",
    "Axis B 의 핵심 산출(NED/IED/MPFED)이 59/59 전부 None 이므로(RQ-D6) Axis B 를 결과변수로 하는 "
    "어떤 상관도 이 자료에서 계산되지 않는다. E-P1 의 위험은 **탐색공간 축소량**으로만 잰다.",
    "공유 slot 이 실제로 오차를 상관시키는지 vs 실체적 연관(진짜 나쁜 페이지가 세 축 모두 나쁘다)인지 "
    "이 자료로는 가르지 못한다. 가르려면 slot 을 ablation 한 재수집이 필요하다.",
    "어느 축을 어떻게 고쳐야 하는지는 정하지 않는다 — construct 는 A 의 권한이다 (NON_CANONICAL).",
    "인과 주장 없음. 모든 문장은 '공유하므로 상관될 수 있다' 형태다.",
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (round((c - h) / d, 4), round((c + h) / d, 4))


def phi_perm(a, b, rng, n_perm: int = 20000) -> dict:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    m = ~(np.isnan(a) | np.isnan(b))
    a, b = a[m], b[m]
    if len(a) < 3 or len(set(a.tolist())) < 2 or len(set(b.tolist())) < 2:
        return {"phi": None, "perm_p": None, "n": int(len(a)), "note": "상수열 또는 n<3 — 계산 불가"}
    r = float(stats.pearsonr(a, b)[0])
    null = np.array([abs(float(stats.pearsonr(rng.permutation(a), b)[0])) for _ in range(n_perm)])
    return {
        "phi": round(r, 4),
        "perm_p": round(float((np.sum(null >= abs(r)) + 1) / (n_perm + 1)), 4),
        "n": int(len(a)),
        "n_perm": n_perm,
    }


def probe_path_for(run_dir: str) -> str | None:
    hits = glob.glob(str(WT / EVIDENCE_GLOB / run_dir / "*/l0a/probe.json"))
    return hits[0] if hits else None


def main() -> dict:
    rng = np.random.default_rng(SEED)
    obs = pd.read_csv(OBS_TABLE)
    tgt = obs[obs.in_mart == 1].copy()
    n_target = len(tgt)

    lo = pd.DataFrame(json.loads((MART / "fact_landing_observation.json").read_text()))
    te = pd.DataFrame(json.loads((MART / "fact_task_entry.json").read_text()))
    ie = pd.DataFrame(json.loads((MART / "fact_interrupt_element.json").read_text()))
    cr = json.loads((MART / "fact_criterion_result.json").read_text())

    # ── A. 코드-수준 결합의 직접 재계산 (E-P1) ───────────────────────────────
    per_target, excluded_rows, overlay_rows = [], [], []
    for _, r in tgt.iterrows():
        pp = probe_path_for(str(r.run_dir))
        if pp is None:
            per_target.append({"wtg": r.wtg, "probe": False})
            continue
        raw = json.loads(Path(pp).read_text())["raw_features"]
        pac = raw.get("primary_action_candidates", [])
        dmap: dict[str, dict] = {}
        for cont in raw.get("dismiss_control_candidates", []):
            for c in cont.get("dismiss_control_candidates") or []:
                dmap.setdefault(str(c.get("selector")), c)
        hit = [c for c in pac if c.get("hittable") and c.get("selector")]
        excl = [c for c in hit if str(c["selector"]) in dmap]
        for c in excl:
            dc = dmap[str(c["selector"])]
            basis = (
                "close_vocabulary"
                if dc.get("matches_close_vocabulary")
                else ("icon_only" if dc.get("icon_only") else "other")
            )
            name_slot = (
                "aria_label"
                if c.get("aria_label")
                else ("visible_text" if c.get("visible_text") else "none_title_or_glyph")
            )
            excluded_rows.append(
                {
                    "wtg": r.wtg,
                    "selector": str(c["selector"]),
                    "dismiss_basis": basis,
                    "pac_name_slot": name_slot,
                    "dismiss_name": dc.get("accessible_name_source"),
                    "has_href": bool(c.get("href")),
                }
            )
        ans = raw.get("accessible_name_sources", [])
        mo = [c for c in raw.get("modal_overlay_candidates", []) if c.get("visible")]
        for c in mo:
            txt = " ".join(str(x) for x in (c.get("accessible_text"), c.get("aria_label")) if x)
            overlay_rows.append(
                {
                    "wtg": r.wtg,
                    "selector": str(c.get("selector")),
                    "name_slot_empty": int(not txt.strip()),
                    "viewport_overlap": float(c.get("viewport_overlap_css_px2") or 0.0),
                }
            )
        dc_all = [c for cont in raw.get("dismiss_control_candidates", []) for c in (cont.get("dismiss_control_candidates") or [])]
        per_target.append(
            {
                "wtg": r.wtg,
                "probe": True,
                "n_pac": len(pac),
                "n_pac_hittable": len(hit),
                "n_excluded_by_dismiss": len(excl),
                "n_activation_pool": len(hit) - len(excl),
                "pool_emptied_by_exclusion": int(len(hit) > 0 and len(hit) - len(excl) == 0),
                "exclusion_rate": (len(excl) / len(hit)) if hit else None,
                "n_accessible_name_sources": len(ans),
                "n_with_aria_label": sum(1 for e in ans if e.get("aria_label")),
                "n_dismiss_controls": len(dc_all),
                "n_dismiss_controls_unnamed": sum(1 for c in dc_all if not c.get("accessible_name_source")),
            }
        )
    pt = pd.DataFrame(per_target)
    ptp = pt[pt.probe]
    ex = pd.DataFrame(excluded_rows)
    ov = pd.DataFrame(overlay_rows)

    n_hit_tot = int(ptp.n_pac_hittable.sum())
    n_excl_tot = int(ptp.n_excluded_by_dismiss.sum())
    ep1 = {
        "grain": "target (in_mart==1, probe 보유) 및 그 안의 hittable primary_action_candidate",
        "n_targets_with_probe": int(len(ptp)),
        "n_targets_expected": n_target,
        "n_hittable_candidates": n_hit_tot,
        "n_removed_from_axis_b_pool": n_excl_tot,
        "removal_rate": round(n_excl_tot / n_hit_tot, 4) if n_hit_tot else None,
        "removal_rate_wilson95": wilson(n_excl_tot, n_hit_tot),
        "n_targets_affected": int((ptp.n_excluded_by_dismiss > 0).sum()),
        "n_targets_pool_emptied_by_exclusion": int(ptp.pool_emptied_by_exclusion.sum()),
        "pool_emptied_wilson95": wilson(int(ptp.pool_emptied_by_exclusion.sum()), int(len(ptp))),
        "removal_basis": ex.dismiss_basis.value_counts().to_dict() if len(ex) else {},
        "removed_candidate_name_slot": ex.pac_name_slot.value_counts().to_dict() if len(ex) else {},
        "n_removed_with_href": int(ex.has_href.sum()) if len(ex) else 0,
        "href_share_wilson95": wilson(int(ex.has_href.sum()), len(ex)) if len(ex) else None,
        "interpretation": (
            "Axis C 의 dismiss detector 산출이 Axis B 의 탐색공간을 직접 깎는다. "
            "이것은 통계적 상관이 아니라 l1_engine.py:346-357 의 결정적 코드경로다. "
            "제외분 중 href 를 가진(=실제 네비게이션) 후보가 있다는 것이 과탐 위험의 신호다 — "
            "다만 href 보유가 곧 오분류라는 뜻은 아니다(닫기 역할의 앵커도 존재한다)."
        ),
    }

    # ── B. Axis A proxy 정량 (interrupt grain) ───────────────────────────────
    j = ov.merge(
        ie[["selector", "classification_status", "final_label", "dismiss_control_exists"]],
        on="selector",
        how="left",
    ).drop_duplicates(subset=["wtg", "selector"])
    j["dce"] = pd.to_numeric(j.dismiss_control_exists, errors="coerce")
    reached = j[(j.viewport_overlap > 0) & j.classification_status.notna()].copy()

    def _strkeys(d: dict) -> dict:
        return {str(int(k) if isinstance(k, float) and k == int(k) else k):
                {str(int(kk) if isinstance(kk, float) and kk == int(kk) else kk): int(vv) for kk, vv in v.items()}
                for k, v in d.items()}

    ct_amb = _strkeys(pd.crosstab(reached.name_slot_empty, reached.classification_status).to_dict())
    ct_dce = _strkeys(pd.crosstab(reached.name_slot_empty, reached.dce).to_dict())
    interrupt_grain = {
        "grain": "visible modal/overlay candidate that reached the text-rule branch (viewport_overlap>0)",
        "n": int(len(reached)),
        "n_all_visible_overlays": int(len(ov)),
        "mart_interrupt_rows": int(len(ie)),
        "proxy_definition": (
            "name_slot_empty = overlay 의 accessible_text 와 aria_label 이 **둘 다** 비어 있음. "
            "l0_collector.py:267-269 가 두 필드를 이어붙여 _LABEL_RULES 에 넣으므로, 이 조건은 "
            "'Axis C 의 의미분류가 읽을 이름 slot 이 없다' 와 정확히 같다. "
            "**Axis A 의 proxy 이지 Axis A 측정치가 아니다.**"
        ),
        "crosstab_classification_status": ct_amb,
        "crosstab_dismiss_control_exists": ct_dce,
        "phi_name_empty_vs_AMBIGUOUS": phi_perm(
            reached.name_slot_empty.values,
            (reached.classification_status == "AMBIGUOUS").astype(int).values,
            rng,
        ),
        "phi_name_empty_vs_label_UNKNOWN": phi_perm(
            reached.name_slot_empty.values,
            (reached.final_label == "UNKNOWN").astype(int).values,
            rng,
        ),
        "phi_name_empty_vs_no_dismiss_control": phi_perm(
            reached.name_slot_empty.values, (reached.dce == 0).astype(int).values, rng
        ),
    }

    # ── C. Axis A proxy 정량 (target grain) ──────────────────────────────────
    t = tgt.merge(
        lo[
            [
                "observation_id",
                "web_target_id",
                "max_overlay_coverage",
                "blocking_modal_count",
                "max_primary_action_occlusion",
                "primary_action_visible_initial",
            ]
        ],
        on="observation_id",
        how="left",
    )
    ie["dce_n"] = pd.to_numeric(ie.dismiss_control_exists, errors="coerce")
    agg = (
        ie.groupby("observation_id")
        .agg(
            n_interrupts=("interrupt_id", "size"),
            deterministic_rate=("classification_status", lambda s: float((s == "DETERMINISTIC").mean())),
            dismiss_exists_rate=("dce_n", "mean"),
        )
        .reset_index()
    )
    t = t.merge(agg, on="observation_id", how="left")
    t = t.merge(
        te[["web_target_id", "endpoint_status", "auth_gate_before_endpoint", "forced_dismissal_count"]],
        on="web_target_id",
        how="left",
    )
    t["proxyA_poor"] = (t.dom_aria_label_n == 0).astype(int)
    t["has_task_entry"] = t.endpoint_status.notna().astype(int)

    k_poor = int(t.proxyA_poor.sum())
    binary_tests = {}
    for name, series in [
        ("axisB_has_task_entry", t.has_task_entry),
        ("axisB_auth_gate_before_endpoint", pd.to_numeric(t.auth_gate_before_endpoint, errors="coerce")),
        ("axisB_forced_dismissal_gt0", (pd.to_numeric(t.forced_dismissal_count, errors="coerce") > 0).astype(float)),
        ("axisC_blocking_modal_gt0", (pd.to_numeric(t.blocking_modal_count, errors="coerce") > 0).astype(float)),
        ("axisC_primary_action_visible_initial", pd.to_numeric(t.primary_action_visible_initial, errors="coerce")),
        ("axisC_body_scroll_locked", pd.to_numeric(t.body_scroll_locked, errors="coerce")),
    ]:
        binary_tests[name] = phi_perm(t.proxyA_poor.values, series.values, rng)

    rank_tests = {}
    for name, series in [
        ("axisC_max_overlay_coverage", t.max_overlay_coverage),
        ("axisC_deterministic_rate", t.deterministic_rate),
        ("axisC_dismiss_exists_rate", t.dismiss_exists_rate),
        ("axisC_n_interrupts", t.n_interrupts),
        ("axisC_max_primary_action_occlusion", t.max_primary_action_occlusion),
        ("axisB_activation_pool_size", t.wtg.map(ptp.set_index("wtg").n_activation_pool)),
        ("axisB_n_excluded_by_dismiss", t.wtg.map(ptp.set_index("wtg").n_excluded_by_dismiss)),
        ("axisB_exclusion_rate_of_hittable", t.wtg.map(ptp.set_index("wtg").exclusion_rate)),
        ("axisB_n_pac_hittable", t.wtg.map(ptp.set_index("wtg").n_pac_hittable)),
    ]:
        y = pd.to_numeric(series, errors="coerce")
        m = y.notna()
        g1 = y[m & (t.proxyA_poor == 1)]
        g0 = y[m & (t.proxyA_poor == 0)]
        if len(g1) < 3 or len(g0) < 3:
            rank_tests[name] = {"note": f"층 n 부족 (poor={len(g1)}, ok={len(g0)})"}
            continue
        u = stats.mannwhitneyu(g1, g0, alternative="two-sided")
        rho = stats.spearmanr(t.proxyA_poor[m], y[m])
        rank_tests[name] = {
            "n_poor": int(len(g1)),
            "n_ok": int(len(g0)),
            "median_poor": round(float(g1.median()), 4),
            "median_ok": round(float(g0.median()), 4),
            "mannwhitney_u_p": round(float(u.pvalue), 4),
            "spearman_rho": round(float(rho.statistic), 4),
            "spearman_p": round(float(rho.pvalue), 4),
            "low_n_flag": bool(len(g1) <= 5 or len(g0) <= 5),
        }

    target_grain = {
        "grain": "target (in_mart==1)",
        "n": n_target,
        "proxy_definition": (
            "proxyA_poor = (dom_aria_label_n == 0). '접근성 표면 빈약' 의 **proxy 이며 Axis A 측정치가 아니다.** "
            "Axis A 는 fact_criterion_result 0행이므로 실측이 존재하지 않는다."
        ),
        "n_proxyA_poor": k_poor,
        "proxyA_poor_rate": round(k_poor / n_target, 4),
        "proxyA_poor_wilson95": wilson(k_poor, n_target),
        "phi_tests": binary_tests,
        "rank_tests": rank_tests,
    }

    # ── D. 반례 탐색 (실측 쪽) ────────────────────────────────────────────────
    # 공유 slot 이 빈약한데 두 축이 함께 나빠지지 '않은' target 을 센다.
    poor = t[t.proxyA_poor == 1]
    ok_axisc = poor[
        (pd.to_numeric(poor.deterministic_rate, errors="coerce") >= 0.6667)
    ]
    counter_empirical = {
        "question": "Axis A proxy 가 빈약(dom_aria_label_n==0)한데 Axis C 의 분류확정률이 중앙값 이상인 target 이 있는가",
        "n_proxyA_poor_with_interrupts": int(poor.deterministic_rate.notna().sum()),
        "n_high_deterministic_rate_ge_0.6667": int(len(ok_axisc)),
        "wilson95": wilson(int(len(ok_axisc)), int(poor.deterministic_rate.notna().sum())),
        "reading": (
            "빈약해도 Axis C 가 잘 확정되는 target 이 존재한다 — 공유가 곧 결정론적 동반붕괴는 아니다. "
            "다만 이것은 '두 축이 독립' 의 증거가 아니라 '상관이 완전하지 않다' 의 증거다. "
            "Axis A 실측이 없어 진짜 독립성 검정은 불가능하다."
        ),
    }

    matrix_stats = {"CONSUMED": 0, "CONSUMED_PARTIAL": 0, "CONSUMED_INDIRECT": 0, "PLANNED_ONLY": 0, "NOT_CONSUMED": 0, "UNKNOWN": 0, "PROVENANCE_ONLY": 0}
    shared_realized, shared_planned, single_axis = [], [], []
    for row in SLOT_MATRIX:
        sts = [row["axis_a"]["status"], row["axis_b"]["status"], row["axis_c"]["status"]]
        for s in sts:
            matrix_stats[s] = matrix_stats.get(s, 0) + 1
        real = sum(1 for s in sts if s.startswith("CONSUMED"))
        planned = sum(1 for s in sts if s.startswith("CONSUMED") or s == "PLANNED_ONLY")
        if real >= 2:
            shared_realized.append(row["slot"])
        if planned >= 2:
            shared_planned.append(row["slot"])
        if planned <= 1:
            single_axis.append(row["slot"])

    verdict = "SUPPORTED"
    doc = {
        "schema": "PILOT_E_slot_dependency/1",
        "verdict": verdict,
        "child_id": "D-PILOT-E",
        "rq_id": "RQ-D-PILOT-001",
        "hypothesis_id": "H-PILOT-E-SLOT-DEPENDENCY",
        "model_or_rule_version": "PILOT_E_v1",
        "seed": SEED,
        "generated_at_kst": datetime.now(KST).isoformat(),
        "plane": "D",
        "authority": "NON_CANONICAL",
        "claim_kind": "ANALYSIS",
        "split": "none",
        "go_nogo_decision": "NOT_IN_SCOPE — D 는 GO/NO-GO 와 threshold 를 내지 않는다",
        "construct_authority_note": "어느 축을 어떻게 고칠지는 A 의 권한이다. 이 문서는 위치와 메커니즘만 보고한다.",
        "causal_claim": "none — 모든 문장은 '공유하므로 상관될 수 있다' 형태다",
        "research_question": (
            "Axis A(KWCAG) · Axis B(depth) · Axis C(obstruction) 이 공유하는 raw evidence slot 은 "
            "무엇이며, 그 공유가 planned association 에서 correlated measurement error 를 만들 수 있는 pair 는 어디인가"
        ),
        "ssot_premise": {
            "source": str(SSOT),
            "sha256": sha256_file(SSOT),
            "sections_read": ["§3", "§4", "§5", "§8", "§9", "§10", "§11", "§12", "§15", "§16"],
            "premise": "§3 세 축을 독립 측정축으로 규정. §3 말미 · §16 단일 composite 합산 금지.",
            "finding": "정의 수준의 독립은 유지되나, **측정 공정 수준에서는 다수의 slot 이 공유된다.**",
        },
        "code_sha": CODE_SHA,
        "code_read": [
            "engine/l0_probe.js",
            "engine/l0_collector.py",
            "engine/l1_engine.py (Axis B 소비지점 확인용)",
            "engine/depth.py (endpoint_status 매핑 확인용)",
            "engine/gate_classifier.py (gate 신호 소비 확인용)",
        ],
        "code_read_method": "git show <sha>:<path> — 읽기 전용. 실행하지 않았다.",
        "axis_a_status": {
            "state": "0_rows_proxy_only",
            "fact_criterion_result_rows": len(cr),
            "evaluator_module_at_sha": "ABSENT — engine/ 파일목록에 KWCAG/criterion evaluator 모듈이 없다",
            "consequence": "Axis A 는 이 문서 전체에서 **proxy 로만** 다룬다. 모든 Axis A 수치에 proxy 표기가 붙는다.",
        },
        "axis_b_status": {
            "state": "depth_all_null",
            "note": "RQ-D6: NED/IED/MPFED 가 59/59 전부 None. endpoint_reached 31/31 = 0.",
            "consequence": "Axis B 를 결과변수로 하는 상관은 계산되지 않는다. E-P1 은 탐색공간 축소량으로만 잰다.",
        },
        "inputs": [
            {"path": str(OBS_TABLE), "sha256": sha256_file(OBS_TABLE)},
            {"path": str(MART / "fact_landing_observation.json"), "sha256": sha256_file(MART / "fact_landing_observation.json")},
            {"path": str(MART / "fact_interrupt_element.json"), "sha256": sha256_file(MART / "fact_interrupt_element.json")},
            {"path": str(MART / "fact_task_entry.json"), "sha256": sha256_file(MART / "fact_task_entry.json")},
            {"path": str(MART / "fact_criterion_result.json"), "sha256": sha256_file(MART / "fact_criterion_result.json")},
            {"path": str(SSOT), "sha256": sha256_file(SSOT)},
            {"path": "raw L0 probe.json (E001 evidence, read-only)", "n_files": int(len(ptp))},
        ],
        "input_snapshot_sha_NEW": "NOT_APPLICABLE_frozen_only",
        "firewall": {
            "not_opened": [
                "holdout label",
                "LABEL_SPLIT_FROZEN*",
                "HOLDOUT_FOR_C*",
                "RAW_L1~L4*",
                "PACKET_L*",
                "*_OVERLAP*",
                "PRECEDENCE_CONTESTED*",
                "CALIBRATION_FOR_B*",
                "**/control/**",
            ],
            "note": "위 목록의 어떤 파일도 열지 않았다. 네트워크 없음. gold label 생성 없음. A~E 기존 산출물 수정 없음. production/engine/mart 수정 없음.",
        },
        "slot_axis_matrix": SLOT_MATRIX,
        "matrix_summary": {
            "n_slots": len(SLOT_MATRIX),
            "status_counts": matrix_stats,
            "shared_realized_ge2_axes": shared_realized,
            "n_shared_realized": len(shared_realized),
            "shared_including_planned_axis_a_ge2": shared_planned,
            "n_shared_including_planned": len(shared_planned),
            "single_axis_or_none": single_axis,
        },
        "shared_slot_mechanisms": SHARED_MECHANISMS,
        "risk_pair_table": [
            {
                "pair_id": m["pair_id"],
                "pair": m["pair"],
                "shared_slots": m["shared_slots"],
                "direction": m["direction"],
                "measurable_now": m["measurable_now"],
                "risk_level": m["risk_level"],
                "what_would_falsify_it": m["what_would_falsify_it"],
            }
            for m in SHARED_MECHANISMS
        ],
        "quantification": {
            "EP1_axisC_to_axisB_searchspace": ep1,
            "axis_a_proxy_interrupt_grain": interrupt_grain,
            "axis_a_proxy_target_grain": target_grain,
        },
        "counterexamples": {
            "code_level": COUNTEREXAMPLE_CANDIDATES,
            "empirical": counter_empirical,
            "verdict": (
                "코드 수준 반례는 **찾았다** (geometry, body scroll lock). 실측 수준의 완전한 반례는 "
                "**찾지 못했다** — Axis A 0행 · Axis B 전부 None 이라 '두 축이 독립적으로 움직이는지' 를 "
                "관측할 결과변량 자체가 없기 때문이다."
            ),
        },
        "not_answered_by_this_rq": NOT_ANSWERED,
        "limitation": (
            "Axis A 는 실측 0행이므로 모든 Axis A 수치가 proxy 다(dom_aria_label_n==0, overlay name slot 공백). "
            "Axis B 는 NED/IED/MPFED 가 전부 None 이라 결과변수로 쓸 수 없다. 따라서 이 RQ 는 실제 오차상관을 "
            "추정하지 못하고 '공유 지점과 메커니즘' 까지만 확정한다. 공유가 실체적 연관인지 측정오차 상관인지도 "
            "가르지 못한다 — 그것은 slot ablation 재수집을 요구한다."
        ),
        "further_research_questions": [
            "RQ-E-1: dismiss detector 의 icon_only(l0_probe.js:402) 조건을 끄면 Axis B activation pool 이 얼마나 회복되는가 (ablation, 재수집 없이 probe 재계산으로 가능).",
            "RQ-E-2: Axis A evaluator 가 생산된 뒤 dom_aria_label_n 층별로 Axis C 분류확정률 차이가 유지되는가 (E-P2 확증/반증).",
            "RQ-E-3: hittable() 을 중심점 1점에서 다점으로 바꾸면 Axis B 후보수와 Axis C dismiss_control_visible 이 같은 방향으로 움직이는가 (E-P4 식별).",
            "RQ-E-4: SSOT §8.1 이 요구한 DOM_AX_ROLE region signal 이 미구현인 것이 Axis B 의 declared_regions 의존(실사이트 2/54)을 만든 원인인가.",
            "RQ-E-5: AX tree 가 수집되지만 어느 축도 소비하지 않는다 — Axis A evaluator 를 AX 우선(SSOT §9 우선순위 1)으로 두면 Axis B/C 와의 slot 공유가 줄어드는가.",
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc



def make_figures(doc: dict) -> list[str]:
    """PILOT_E 그림 3종. 판정을 그리지 않는다 — 분포와 소비관계만 그린다."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out: list[str] = []

    # (1) slot x axis 소비 히트맵
    order = {"CONSUMED": 3, "CONSUMED_PARTIAL": 2, "CONSUMED_INDIRECT": 2,
             "PLANNED_ONLY": 1, "PROVENANCE_ONLY": 0, "NOT_CONSUMED": 0, "UNKNOWN": -1}
    slots = [r["slot"].split(" (")[0] for r in SLOT_MATRIX]
    mat = np.array([[order[r[k]["status"]] for k in ("axis_a", "axis_b", "axis_c")] for r in SLOT_MATRIX], float)
    fig, ax = plt.subplots(figsize=(7.5, 8.5))
    im = ax.imshow(mat, cmap="YlOrRd", vmin=-1, vmax=3, aspect="auto")
    ax.set_xticks([0, 1, 2], ["Axis A\n(KWCAG,\n0 rows)", "Axis B\n(depth)", "Axis C\n(obstruction)"])
    ax.set_yticks(range(len(slots)), slots, fontsize=8)
    for i, r in enumerate(SLOT_MATRIX):
        for j, k in enumerate(("axis_a", "axis_b", "axis_c")):
            st = r[k]["status"]
            ax.text(j, i, {"CONSUMED": "C", "CONSUMED_PARTIAL": "c", "CONSUMED_INDIRECT": "i",
                           "PLANNED_ONLY": "P", "NOT_CONSUMED": "-", "UNKNOWN": "?",
                           "PROVENANCE_ONLY": "p"}[st], ha="center", va="center", fontsize=9)
    ax.set_title("Evidence slot x axis consumption @ %s\nC=consumed c=partial i=indirect P=planned-only -=not p=provenance ?=unknown"
                 % CODE_SHA[:8], fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.5, label="consumption strength")
    fig.tight_layout()
    f1 = FIG_DIR / "PILOT_E_slot_axis_matrix.png"
    fig.savefig(f1, dpi=150); plt.close(fig); out.append(str(f1))

    # (2) E-P1 — Axis C dismiss detector 가 깎아낸 Axis B 후보
    ep1 = doc["quantification"]["EP1_axisC_to_axisB_searchspace"]
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    axs[0].bar(["hittable\ncandidates", "removed by\ndismiss set", "remaining\npool"],
               [ep1["n_hittable_candidates"], ep1["n_removed_from_axis_b_pool"],
                ep1["n_hittable_candidates"] - ep1["n_removed_from_axis_b_pool"]],
               color=["#4C72B0", "#C44E52", "#55A868"])
    axs[0].set_ylabel("candidate count (n targets = %d)" % ep1["n_targets_with_probe"])
    axs[0].set_title("E-P1: Axis C output shrinks Axis B search space\n%d/%d = %.1f%% (l1_engine.py:346-357)"
                     % (ep1["n_removed_from_axis_b_pool"], ep1["n_hittable_candidates"],
                        100 * ep1["removal_rate"]), fontsize=9)
    b = ep1["removal_basis"]
    axs[1].bar(list(b.keys()), list(b.values()), color="#8172B2")
    axs[1].set_title("why they were removed\n(icon_only = l0_probe.js:402, needs no close word)", fontsize=9)
    axs[1].set_ylabel("removed candidates")
    fig.tight_layout()
    f2 = FIG_DIR / "PILOT_E_ep1_searchspace.png"
    fig.savefig(f2, dpi=150); plt.close(fig); out.append(str(f2))

    # (3) Axis A proxy x Axis C 산출 (proxy 임을 제목에 명시)
    ig = doc["quantification"]["axis_a_proxy_interrupt_grain"]
    tg = doc["quantification"]["axis_a_proxy_target_grain"]
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    ct = ig["crosstab_dismiss_control_exists"]
    n0 = [ct["0"]["0"], ct["1"]["0"]]  # name present: no-dismiss, has-dismiss
    n1 = [ct["0"]["1"], ct["1"]["1"]]
    x = np.arange(2)
    axs[0].bar(x - 0.18, [n0[0], n1[0]], 0.36, label="name slot present")
    axs[0].bar(x + 0.18, [n0[1], n1[1]], 0.36, label="name slot EMPTY (proxy)")
    axs[0].set_xticks(x, ["dismiss_control\nexists = 0", "dismiss_control\nexists = 1"])
    axs[0].legend(fontsize=8)
    axs[0].set_ylabel("overlay candidates (n=%d)" % ig["n"])
    pv = ig["phi_name_empty_vs_no_dismiss_control"]
    axs[0].set_title("PROXY only (Axis A has 0 rows)\nphi=%.3f perm p=%.4f" % (pv["phi"], pv["perm_p"]), fontsize=9)
    rt = tg["rank_tests"]["axisC_deterministic_rate"]
    axs[1].bar(["aria-label n>0\n(n=%d)" % rt["n_ok"], "aria-label n==0\n(n=%d, PROXY)" % rt["n_poor"]],
               [rt["median_ok"], rt["median_poor"]], color=["#55A868", "#C44E52"])
    axs[1].set_ylabel("median Axis C deterministic classification rate")
    axs[1].set_title("target grain, PROXY only\nspearman rho=%.3f p=%.4f  MWU p=%.4f"
                     % (rt["spearman_rho"], rt["spearman_p"], rt["mannwhitney_u_p"]), fontsize=9)
    fig.tight_layout()
    f3 = FIG_DIR / "PILOT_E_axisA_proxy_vs_axisC.png"
    fig.savefig(f3, dpi=150); plt.close(fig); out.append(str(f3))
    return out


def matrix_text() -> str:
    lines = [
        f"slot x axis dependency matrix — code SHA {CODE_SHA}",
        "status: CONSUMED / CONSUMED_PARTIAL / CONSUMED_INDIRECT / PLANNED_ONLY / NOT_CONSUMED / UNKNOWN / PROVENANCE_ONLY",
        "Axis A = 0 rows (fact_criterion_result), so every Axis A cell is definition-level, not observed.",
        "",
    ]
    for row in SLOT_MATRIX:
        lines.append(f"### {row['slot']}")
        lines.append(f"  captured_at: {row['captured_at']}")
        for ax, key in (("A", "axis_a"), ("B", "axis_b"), ("C", "axis_c")):
            c = row[key]
            lines.append(f"  Axis {ax}: {c['status']}")
            if c.get("consumer"):
                lines.append(f"    consumer: {c['consumer']}")
            lines.append(f"    evidence: {c['evidence']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    d = main()
    figs = make_figures(d)
    d["figures"] = figs
    OUT_JSON.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("figures:", figs)
    print(json.dumps(d["matrix_summary"], ensure_ascii=False, indent=2))
    print(json.dumps(d["quantification"]["EP1_axisC_to_axisB_searchspace"], ensure_ascii=False, indent=2))
