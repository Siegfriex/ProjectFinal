"""Stage 1 — Expectation(공식 기준 조건).

**AUTO_DECIDABLE 5개만** 실제 조건 검사를 구현한다: `1.4.2` `1.4.3` `2.1.3` `2.4.2`
`3.3.2`. 나머지 4개 `AUTO_DECIDABLE`(`2.2.1` `2.4.1` `2.5.4` `3.3.4`)은 evidence
slot 자체가 없어(`stage1_evidence.ABSENT_FROM_PROBE_SCHEMA`) Expectation 까지
가지 않는다. `AUTO_FLAG_ONLY` 6개는 최종 Outcome 이 항상 `UNDETERMINED` 로
cap 되므로(`DECISION-1`) 여기서 candidate_verdict 를 만들지 않는다 — 반영되지 않을
verdict 를 만들어 오해를 살 이유가 없다.

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


def _is_large_text(font_px: float | None, font_weight: int | None) -> bool:
    if font_px is None:
        return False
    if font_px >= LARGE_TEXT_MIN_PX:
        return True
    return bool(
        font_weight and font_weight >= BOLD_WEIGHT_MIN and font_px >= LARGE_TEXT_BOLD_MIN_PX
    )


def expect_1_4_3(items: list[dict]) -> ExpectationResult:
    # 배경 미확정·배경 이미지 위 텍스트는 계산된 ratio 가 실제와 다를 수 있어 측정
    # 실패로 취급한다(refcohort c_1_4_3 과 같은 원칙) — FAIL 로 세지 않는다.
    resolvable = [it for it in items if it.get("bg_resolved") and not it.get("behind_image")]
    if not resolvable:
        return ExpectationResult(None, (), "전 항목 배경 미확정/이미지 배경 — 대비 계산 불가")

    matched = []
    verdict = VerdictState.PASS
    for it in resolvable:
        ratio = it.get("contrast_ratio")
        if ratio is None:
            continue
        required = (
            CONTRAST_LARGE_THRESHOLD
            if _is_large_text(it.get("font_px"), it.get("font_weight"))
            else CONTRAST_NORMAL_THRESHOLD
        )
        ok = ratio >= required
        matched.append({**it, "required": required, "item_verdict": "PASS" if ok else "FAIL"})
        if not ok:
            verdict = VerdictState.FAIL

    if not matched:
        return ExpectationResult(None, (), "배경 확정 항목 중 유효 contrast_ratio 없음")

    n_fail = sum(1 for m in matched if m["item_verdict"] == "FAIL")
    reason = f"대비 검사 {len(matched)}건, 기준 미달 {n_fail}건"
    return ExpectationResult(verdict, tuple(matched), reason)


# ── 2.1.3 조작 가능 ────────────────────────────────────────────────────────────
# KWCAG 2.2 해설서: "CSS 픽셀 기준 대각선 길이 6mm 이상". 96dpi 환산 1px≈0.2646mm.
# 값 출처: `research/refcohort/src/refcohort/criteria.py` `c_2_1_3`
# (commit `32460b8` — "2.1.3 조작 가능 임계값을 KWCAG 2.2 해설서 원문 기준으로 시정").
# 이 worktree 는 그 값을 재계산해 재사용한다(같은 상수를 두 번 발명하지 않는다).
CSS_PX_TO_MM = 25.4 / 96.0
TARGET_DIAGONAL_MIN_MM = 6.0


def expect_2_1_3(items: list[dict]) -> ExpectationResult:
    matched = []
    verdict = VerdictState.PASS
    for it in items:
        w, h = it.get("width_css_px"), it.get("height_css_px")
        if not w or not h:
            continue
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

    if not matched:
        return ExpectationResult(None, (), "유효 width/height 없음")

    n_fail = sum(1 for m in matched if m["item_verdict"] == "FAIL")
    reason = f"대각선 6mm 기준 {len(matched)}건 검사, 기준 미달 {n_fail}건"
    return ExpectationResult(verdict, tuple(matched), reason)


# ── 2.4.2 제목 제공 ────────────────────────────────────────────────────────────
# KWCAG 2.2 2.4.2 는 코드북에서 AUTO_DECIDABLE — "제목이 존재하는가"만 기계 판정
# 대상이다. "내용을 식별할 수 있을 만큼 설명적인가"는 의미 판단이라 Stage 1
# (deterministic 단계)에서 다루지 않는다 — 그건 이 criterion 안에서도 candidate_verdict
# 를 낼 뿐, "완전한 2.4.2 판정"이라 주장하지 않는다(§ 보고서 "검증하지 않은 것" 참조).
def expect_2_4_2(items: list[dict]) -> ExpectationResult:
    vp = items[0]
    title = (vp.get("title") or "").strip()
    ok = bool(title)
    matched = ({**vp, "item_verdict": "PASS" if ok else "FAIL"},)
    reason = f"title={title!r} (존재만 검사, 설명성은 미검사)" if ok else "title 이 비어있음"
    return ExpectationResult(VerdictState.PASS if ok else VerdictState.FAIL, matched, reason)


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
