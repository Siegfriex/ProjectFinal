"""Stage 1 — Expectation(공식 기준 조건).

`T-A-W3-SCHEMA-001`(A ACCEPTED_WITH_ONE_DIVERGENCE 이후 발행) 반영: schema gap
4건을 "채울 수 있는가"로 개별 재심사했다 — 결과는 `stage1_evidence.py` 모듈
docstring에 criterion 별로 적어뒀다. 결론만 요약하면:

- `2.2.1`(응답시간 조절) · `2.5.4`(동작기반 작동): probe 어디에도 대응 신호가 없다
  (meta refresh/session timeout, devicemotion/deviceorientation 전부 미수집) —
  **진짜로 못 채운다.**
- `2.4.1`(반복영역 건너뛰기): `region_signals.declared_regions` 가 존재하긴 하나
  `[data-region]` **fixture 전용 마커**만 감지한다(ARIA landmark/skip-link 아님).
  실 pilot 증거에서 55/58 이 항상 빈 배열이었다 — 이 신호로 Applicability 를
  내리면 "적용기회 없음"을 대량으로 오판한다. **의도적으로 안 채운다.**
- `3.3.4`(반복 입력 정보): `gate_signals.username_autocomplete_count` /
  `tel_autocomplete_count` 는 **실재하는 비-fixture 신호**였다(매핑 누락이었음 —
  이제 고쳤다). 다만 "있음"만 셀 수 있고 "있어야 하는데 없음"은 셀 수 없는
  구조적 비대칭 신호라 Applicability/Outcome 어느 쪽도 여전히 안전하게 못
  내린다 — evidence_slot 투명성만 개선하고 **판정은 그대로 UNDETERMINED 로 둔다**
  (coverage 를 올리는 것 자체가 목표가 아니다 — W2 force-map 교훈과 같은 원칙).

**AUTO_DECIDABLE 5개**가 candidate_verdict PASS/FAIL 산출 로직을 갖는다:
`1.4.2` `1.4.3` `2.1.3` `2.4.2` `3.3.2`. 다만 **C 확인 기준 실효(effective) 결정
criterion 은 4/22 다**(`1.4.2`·`1.4.3`·`2.1.3`·`3.3.2` — `2.4.2` 는 §요구#3 분리
이후 real evidence 에서 항상 UNDETERMINED 로 귀결돼 실질 기여가 0). **decision
coverage 사전등록값 = 0.114**(C 확인, `T-B-FC-008`) — 결과를 본 뒤 바뀌면 조작이니
이 값을 고정한다. `AUTO_FLAG_ONLY` 6개는 최종 Outcome 이 항상 `UNDETERMINED` 로
cap 되므로(`DECISION-1`) 여기서 candidate_verdict 를 만들지 않는다.

`C-BLOCKER-234221`(P1) 시정: `1.4.3` 의 "측정불가 제외 후 나머지가 전부 통과하면
PASS" 구조가 `D-R0-23` 의 거울상 위반이었다(제외가 많을수록 PASS 가 쉬워짐) — 아래
`expect_1_4_3` 참조. **`D-R0-78` 로 확정됐다**: FAIL 은 존재 주장이라 제외에도
유효하고, PASS 는 전칭 주장이라 제외가 하나라도 있으면 성립하지 않는다(A 의 표현).
`PASS_MEASURABLE_ONLY` 같은 새 상태는 만들지 않는다(`D-R0-78-2`, A 기각 — "PASS"
토큰이 이름에 있으면 하류에서 결국 PASS 로 집계된다) — 제외 비율은 `UNDETERMINED`
의 reason 부기로만 남긴다. `D-R0-70-2` 훑기로 같은 패턴을 `expect_2_1_3` 에서도
찾아 같은 규칙을 적용했다(아래).

각 함수는 **하나의 criterion 만** 다루는 독립 함수다 — `D-R0-21` "각 단계가
독립 함수/데이터로 드러나야 한다"를 Expectation 단계에서 지키는 지점이 여기다.

임계값 출처를 전부 주석에 남긴다. 추정치는 하나도 없다 — KWCAG 2.2 해설서 원문
수치이거나, 이미 그 원문 기준으로 시정된 `research/refcohort` 값을 재사용했다
(원문이 반복해서 정의될 필요가 없게).
"""

from __future__ import annotations

import math

from ..vocabulary import VerdictState
from .stage1_types import ExpectationResult


# ── 1.4.2 자동 재생 금지 ──────────────────────────────────────────────────────
# KWCAG 2.2 1.4.2: 자동 재생 콘텐츠는 (a) 3초 이내로 짧거나 (b) 정지/일시정지 수단을
# 제공해야 한다. probe 는 `duration` 을 수집하지 않으므로(수집기 한계) (a) 분기는
# 판정하지 못하고 (b) "정지 제어 존재" 또는 "음소거(청각 방해 없음)+비반복"만 본다.
def expect_1_4_2(items: list[dict]) -> ExpectationResult:
    if not items:
        return ExpectationResult(None, (), "자동재생 매체 후보 없음")
    matched = []
    verdict = VerdictState.PASS
    for it in items:
        muted, loop, controls = (
            bool(it.get("muted")),
            bool(it.get("loop")),
            bool(it.get("controls")),
        )
        ok = (muted and not loop) or controls
        matched.append({**it, "item_verdict": "PASS" if ok else "FAIL"})
        if not ok:
            verdict = VerdictState.FAIL
    n_fail = sum(1 for m in matched if m["item_verdict"] == "FAIL")
    reason = (
        f"자동재생 {len(matched)}건 중 제어없음 {n_fail}건 "
        "(duration 필드 미수집 — '3초 이하' 분기는 검사하지 않음)"
    )
    return ExpectationResult(verdict, tuple(matched), reason)


# ── 1.4.3 텍스트 콘텐츠의 명도 대비 ────────────────────────────────────────────
# KWCAG 2.2 1.4.3(WCAG 1.4.3과 동일 수치): 일반 텍스트 4.5:1, 큰 텍스트(18pt≥24px
# 또는 굵게 14pt≥18.67px) 3:1. 96dpi CSS 표준 환산(1pt = 4/3px)은 통용 수치이며
# `research/refcohort` 의 2.1.3 수정(`32460b8`)과 같은 CSS-표준-환산 원칙을 따른다.
CONTRAST_NORMAL_THRESHOLD = 4.5
CONTRAST_LARGE_THRESHOLD = 3.0
LARGE_TEXT_MIN_PX = 24.0  # 18pt @ 96dpi
LARGE_TEXT_BOLD_MIN_PX = 18.6667  # 14pt @ 96dpi
BOLD_WEIGHT_MIN = 700

# `T-A-W3-SCHEMA-001` 요구#2(1차) — A 지적: "현재 alpha0/1px/bg 미해결이 '진짜 대비
# 실패'와 구분되지 않는다." 58건 실 evidence 를 스캔해 세 패턴을 확인했었다:
#   - `fg_alpha == 0`: 예) "Global Standard" 텍스트가 fg_rgb=[0,0,0], fg_alpha=0,
#     bg_rgb=[0,0,0](동일 검정)인데 ratio=1 로 계산된 사례 — 그라디언트 텍스트
#     (background-clip:text 등)나 실제로 렌더되지 않는 색이라 fg_rgb 자체가 신뢰
#     불가능하다. **유지한다.**
#   - `font_px` 가 극히 작음(≤2px): 아이콘 폰트 글리프나 장식 배지가 "텍스트"로
#     잡힌 경우 — 사람이 읽는 본문/UI 텍스트가 아닐 가능성이 높다. **유지한다.**
#   - `ratio <= 1.05`: **`C-BLOCKER-234221`(2차, `T-B-FC-008`)로 제거했다.**
#     `research/refcohort/codebook/` 에 이 조건의 근거가 없었다(그 파일 하단 주석
#     참조) — `fg_alpha==1`·`bg_resolved==True` 인데 `ratio==1.0` 인 항목은 측정
#     실패가 아니라 **진짜 동색 렌더링(예: 흰 배경 위 흰 텍스트)일 수 있는 측정
#     결과**다. 이 조건으로 FAIL→PASS 로 잘못 정정됐던 2건(`464c1fb5`·`12158b64`)
#     이 이 수정으로 다시 FAIL 로 돌아간다.
# 남은 두 조건(alpha0/극소폰트) + 기존 bg_resolved/behind_image 를 **"측정 불가"**
# 로 묶어 candidate 산출에서 제외한다 — PASS 로도 FAIL 로도 세지 않는다(D-R0-23).
# 측정 불가 항목도 `matched_items` 에 `item_verdict="MEASUREMENT_INCONCLUSIVE"` 로
# 남겨 근거를 보존한다. **그리고 제외 항목이 하나라도 있으면 남은 항목이 전부 통과
# 해도 그냥 PASS 를 내지 않는다** — `expect_1_4_3` 아래쪽 분기 참조
# (`D-R0-23` 거울상 · `D-R0-76` · `D-R0-78-1` 확정).
TINY_GLYPH_MAX_PX = 2.0

# `C-BLOCKER-234221`(P1, `T-B-FC-008`) — 이전 버전은 `ratio <= 1.05`(전경·배경 동색
# 산출)도 "측정 불가"로 묶어 분모에서 뺐다. C 가 `research/refcohort/codebook/` 를
# 근거로 요구해 다시 찾아봤다 — `kwcag22_criteria.json`(이 디렉터리의 유일한 파일)
# 의 1.4.3 항목에는 `{id, principle, guideline, name, automation, detector}` 뿐이고
# ratio 기반 측정실패 규정이 전혀 없다. 그 reasoning 은 `research/refcohort/src/
# refcohort/criteria.py` 의 `c_1_4_3` **구현 코드 안의 주석**에만 있었다 — 그건
# codebook(정본 기준)이 아니라 구현체의 휴리스틱이다. **근거를 찾지 못했으므로
# 이 조건을 뺀다.** `fg_alpha==1`·`bg_resolved==True`·`ratio==1.0` 인 항목은 이제
# "계산 신뢰 불가"가 아니라 **측정 결과**(진짜 동색 렌더링, 예: 흰 배경 위 흰 텍스트)
# 로 취급해 정상적으로 PASS/FAIL 판정에 넣는다 — `ratio < threshold` 이면 FAIL 이다.
#
# `fg_alpha==0`(전경 투명)과 `font_px<=TINY_GLYPH_MAX_PX`(극소 글리프)는 그대로
# 남긴다 — 이 둘은 "대비가 나쁘다"가 아니라 "측정 대상 자체가 사람이 읽는 텍스트가
# 아니다(투명이라 안 보이거나 아이콘 폰트 글리프)"라는, 성격이 다른 근거다.


def _is_large_text(font_px: float | None, font_weight: int | None) -> bool:
    if font_px is None:
        return False
    if font_px >= LARGE_TEXT_MIN_PX:
        return True
    return bool(
        font_weight and font_weight >= BOLD_WEIGHT_MIN and font_px >= LARGE_TEXT_BOLD_MIN_PX
    )


def _contrast_measurement_inconclusive_reason(item: dict) -> str | None:
    """None 이 아니면 이 항목의 대비 계산을 신뢰할 수 없다는 뜻 — PASS/FAIL 후보에서 뺀다.

    `ratio<=1.05`(동색 산출)는 **여기 없다** — codebook 에 근거가 없어 뺐다(위 주석).
    """
    if not item.get("bg_resolved") or item.get("behind_image"):
        return "배경 미확정(투명 조상) 또는 배경 이미지 위 텍스트 — 배경색 자체를 모른다"
    if item.get("fg_alpha") == 0:
        return (
            "전경 alpha=0 — 텍스트가 실제로 화면에 렌더링되는 색을 모른다"
            "(그라디언트 클립/투명 텍스트 트릭 포함)"
        )
    font_px = item.get("font_px")
    if font_px is not None and font_px <= TINY_GLYPH_MAX_PX:
        return f"font_px={font_px} — 아이콘 글리프/장식 요소로 추정, 실제 본문 텍스트가 아닐 가능성이 높다"
    return None


def expect_1_4_3(items: list[dict]) -> ExpectationResult:
    resolvable = []
    inconclusive_tagged = []
    for it in items:
        why = _contrast_measurement_inconclusive_reason(it)
        if why is not None:
            inconclusive_tagged.append(
                {**it, "item_verdict": "MEASUREMENT_INCONCLUSIVE", "inconclusive_reason": why}
            )
        else:
            resolvable.append(it)

    if not resolvable:
        return ExpectationResult(
            None,
            tuple(inconclusive_tagged),
            f"전 {len(items)}건이 측정 불가(배경 미확정/alpha0/극소폰트) — 대비 계산 불가",
            escalate_semantic=True,  # DOM 색상 계산이 아니라 screenshot 을 보는 VLM 이면 풀 수 있다.
        )

    matched = list(inconclusive_tagged)
    verdict = VerdictState.PASS
    n_checked = 0
    for it in resolvable:
        ratio = it.get("contrast_ratio")
        if ratio is None:
            continue
        n_checked += 1
        required = (
            CONTRAST_LARGE_THRESHOLD
            if _is_large_text(it.get("font_px"), it.get("font_weight"))
            else CONTRAST_NORMAL_THRESHOLD
        )
        ok = ratio >= required
        matched.append({**it, "required": required, "item_verdict": "PASS" if ok else "FAIL"})
        if not ok:
            verdict = VerdictState.FAIL

    if n_checked == 0:
        return ExpectationResult(
            None,
            tuple(inconclusive_tagged),
            "측정 가능 항목 중 유효 contrast_ratio 없음",
            escalate_semantic=True,
        )

    n_fail = sum(1 for m in matched if m.get("item_verdict") == "FAIL")

    # `D-R0-23` 의 거울상(C 지적, `C-BLOCKER-234221`) — "측정 실패를 PASS 의 근거
    # 부재로 처리해야지 PASS 로 전이하면 안 된다"(`D-R0-76`, 분모를 지워 비율을
    # 올리지 않는다). `D-R0-78-1` 로 확정: FAIL 은 존재 주장이라 제외에도 유효하고,
    # PASS 는 전칭 주장이라 제외가 있으면 표본 누락에 취약해 성립하지 않는다.
    # `PASS_MEASURABLE_ONLY` 는 만들지 않는다(`D-R0-78-2`) — 제외 비율은 아래처럼
    # UNDETERMINED 의 reason 에 개수/비율로만 남긴다.
    if verdict == VerdictState.PASS and inconclusive_tagged:
        return ExpectationResult(
            None,
            tuple(matched),
            f"측정 가능 {n_checked}건은 전부 기준 충족했으나 측정불가 {len(inconclusive_tagged)}건이 "
            f"함께 있어 PASS 를 내지 않는다(제외비율 {len(inconclusive_tagged)}/"
            f"{n_checked + len(inconclusive_tagged)}, D-R0-78-1)",
            escalate_semantic=True,
        )

    reason = (
        f"대비 검사 {n_checked}건(측정불가 제외 {len(inconclusive_tagged)}건), 기준 미달 {n_fail}건"
    )
    return ExpectationResult(verdict, tuple(matched), reason)


# ── 2.1.3 조작 가능 ────────────────────────────────────────────────────────────
# KWCAG 2.2 해설서: "CSS 픽셀 기준 대각선 길이 6mm 이상". 96dpi 환산 1px≈0.2646mm.
# 값 출처: `research/refcohort/src/refcohort/criteria.py` `c_2_1_3`
# (commit `32460b8` — "2.1.3 조작 가능 임계값을 KWCAG 2.2 해설서 원문 기준으로 시정").
# 이 worktree 는 그 값을 재계산해 재사용한다(같은 상수를 두 번 발명하지 않는다).
CSS_PX_TO_MM = 25.4 / 96.0
TARGET_DIAGONAL_MIN_MM = 6.0


def expect_2_1_3(items: list[dict]) -> ExpectationResult:
    # `D-R0-70-2` 훑기(`C-BLOCKER-234221` 후속)에서 발견 — width/height 가 없거나
    # 0인 항목을 그냥 `continue` 로 조용히 빼고 있었다. `1.4.3` 과 같은 결함 계열이다
    # (측정 안 된 항목을 지운 뒤 남은 게 전부 PASS 면 PASS 를 냈다). `D-R0-78-1` 비대칭을
    # 그대로 적용한다: 제외 항목이 있어도 FAIL 은 유효하고(존재 주장), 제외 항목이
    # 있으면 PASS 는 성립하지 않는다(전칭 주장이 표본 누락에 취약하므로).
    matched = []
    unmeasurable = []
    verdict = VerdictState.PASS
    n_checked = 0
    for it in items:
        w, h = it.get("width_css_px"), it.get("height_css_px")
        if not w or not h:
            unmeasurable.append(
                {
                    **it,
                    "item_verdict": "MEASUREMENT_INCONCLUSIVE",
                    "inconclusive_reason": "width/height 없음 또는 0 — 크기 측정 불가",
                }
            )
            continue
        n_checked += 1
        diag_px = math.hypot(w, h)
        diag_mm = diag_px * CSS_PX_TO_MM
        ok = diag_mm >= TARGET_DIAGONAL_MIN_MM
        matched.append(
            {
                **it,
                "diagonal_css_px": round(diag_px, 2),
                "diagonal_mm_css_standard": round(diag_mm, 2),
                "item_verdict": "PASS" if ok else "FAIL",
            }
        )
        if not ok:
            verdict = VerdictState.FAIL

    if n_checked == 0:
        return ExpectationResult(
            None, tuple(unmeasurable), "유효 width/height 없음", escalate_semantic=True
        )

    n_fail = sum(1 for m in matched if m["item_verdict"] == "FAIL")

    # `D-R0-78-1`/`D-R0-78-2` — 제외 항목이 있는데 verdict 가 PASS 면 그냥 PASS 를 내지
    # 않는다. `PASS_MEASURABLE_ONLY` 같은 새 상태를 만들지 않는다(A 가 기각) — 제외
    # 비율은 UNDETERMINED 의 reason 부기로만 남긴다.
    if verdict == VerdictState.PASS and unmeasurable:
        return ExpectationResult(
            None,
            tuple(matched + unmeasurable),
            f"측정 가능 {n_checked}건은 전부 기준 충족했으나 크기 측정 불가 {len(unmeasurable)}건이 "
            f"함께 있어 PASS 를 내지 않는다(제외비율 {len(unmeasurable)}/{len(items)}, "
            "D-R0-78-1)",
            escalate_semantic=True,
        )

    reason = (
        f"대각선 6mm 기준 {n_checked}건 검사(측정불가 제외 {len(unmeasurable)}건), "
        f"기준 미달 {n_fail}건"
    )
    return ExpectationResult(verdict, tuple(matched + unmeasurable), reason)


# ── 2.4.2 제목 제공 ────────────────────────────────────────────────────────────
# `T-A-W3-SCHEMA-001` 요구#3 — A 지적: "존재로 PASS 를 주는 것은 존재로 terminal 을
# 주는 것과 같은 형태다"(`D-R0-70` 존재≠작동, 이 세션의 4번째 사례로 등재됨).
# 그래서 **비대칭**으로 나눈다:
#   - title 이 비어있음 → FAIL. 이건 결정적(deterministic)이다 — "제목이 아예
#     없다"는 그 자체로 2.4.2 위반이고, 존재/작동 구분이 필요 없는 방향이다
#     (없음의 관측은 모호하지 않다).
#   - title 이 존재함 → **더 이상 PASS 를 주지 않는다.** candidate_verdict=None +
#     escalate_semantic=True 로 다음 tier(semantic/사람 검토)에 "설명적인가"를
#     넘긴다. 존재라는 관측 자체는 evidence 로 남기되(matched_items), 그것이 곧
#     기준 충족이라고 주장하지 않는다.
def expect_2_4_2(items: list[dict]) -> ExpectationResult:
    vp = items[0]
    title = (vp.get("title") or "").strip()

    if not title:
        matched = ({**vp, "item_verdict": "FAIL"},)
        return ExpectationResult(VerdictState.FAIL, matched, "title 이 비어있음 — 결정적 위반")

    # title 존재 — PASS 를 주지 않는다. 적절성/설명성은 의미 판단이 필요하다.
    matched = ({**vp, "item_verdict": "EXISTS_ADEQUACY_UNVERIFIED"},)
    return ExpectationResult(
        None,
        matched,
        f"title={title!r} 존재는 확인했다 — 그러나 내용을 식별할 수 있을 만큼 "
        "설명적인지(적절성)는 Stage 1(deterministic)이 판단할 수 없다 "
        "(D-R0-70 존재≠작동). semantic/사람 검토로 넘긴다.",
        escalate_semantic=True,
    )


# ── 3.3.2 레이블 제공 ──────────────────────────────────────────────────────────
# 폼 컨트롤(input/select/textarea)에 aria-label · aria-labelledby · <label for> ·
# title 중 하나라도 있으면 이름 출처가 있다고 본다. `value`/`visible_text`는
# 컨트롤 자체 값이지 레이블이 아니라 근거로 쓰지 않는다.
def expect_3_3_2(items: list[dict]) -> ExpectationResult:
    matched = []
    verdict = VerdictState.PASS
    for it in items:
        has_name = (
            bool(it.get("aria_label"))
            or bool(it.get("aria_labelledby"))
            or bool(it.get("labelled_by_for"))
            or bool(it.get("title"))
        )
        matched.append({**it, "item_verdict": "PASS" if has_name else "FAIL"})
        if not has_name:
            verdict = VerdictState.FAIL

    if not matched:
        return ExpectationResult(None, (), "폼 컨트롤 후보 없음")

    n_fail = sum(1 for m in matched if m["item_verdict"] == "FAIL")
    reason = f"폼 컨트롤 {len(matched)}건 이름출처 검사, 미충족 {n_fail}건"
    return ExpectationResult(verdict, tuple(matched), reason)


#: criterion_id → Expectation 함수. 여기 없는 criterion 은 Stage 1 에서 candidate_verdict
#: 를 절대 만들지 않는다(`stage1_pipeline` 이 None 취급).
EXPECTATION_FUNCS = {
    "1.4.2": expect_1_4_2,
    "1.4.3": expect_1_4_3,
    "2.1.3": expect_2_1_3,
    "2.4.2": expect_2_4_2,
    "3.3.2": expect_3_3_2,
}
