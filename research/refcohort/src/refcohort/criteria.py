"""수집된 적용기회를 KWCAG 2.2 검사항목별 verdict로 판정한다.

프로토콜 v2 §5를 따른다.
  - 적용기회가 없으면 NA (PASS도 0점도 아니다)
  - Metric = PASS 비율, 분모가 0이면 None
  - OBSERVED_STRICT_PASS = 적용기회가 있고 FAIL이 하나도 없을 때만 TRUE
  - 자동 판정 불가 항목은 UNDETERMINED로 남기고 PASS로 바꾸지 않는다
자동 검사 결과는 AUTO_FLAG이며 최종 FAIL 확정은 사람 검토를 거친다(§8-7).
"""

from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path
from typing import Any

CODEBOOK = json.loads(
    (Path(__file__).parents[2] / "codebook" / "kwcag22_criteria.json").read_text(encoding="utf-8")
)
CRITERIA = {c["id"]: c for c in CODEBOOK["criteria"]}

PASS, FAIL, NA, UNDET = "PASS", "FAIL", "NA", "UNDETERMINED"

# 이 값 미만이면 조작 가능 크기 미달 후보로 본다 (WCAG 2.5.8 최소 타겟 24 CSS px 기준)
TARGET_MIN_CSS_PX = 24.0
# 인접 간격이 이보다 좁으면 오조작 위험 신호로 함께 기록한다
TARGET_GAP_MIN_CSS_PX = 24.0


def _op(probe: dict, key: str) -> list[dict]:
    return (probe.get("opportunities") or {}).get(key) or []


def _result(
    cid: str, opportunities: list[dict], *, note: str = "", forced: str | None = None
) -> dict:
    """적용기회 리스트(각 항목에 verdict 포함)를 집계한다."""
    meta = CRITERIA[cid]
    total = len(opportunities)
    if forced:
        return {
            "criterion_id": cid,
            "criterion_name": meta["name"],
            "principle": meta["principle"],
            "automation": meta["automation"],
            "applicable_count": total,
            "pass_count": 0,
            "fail_count": 0,
            "undetermined_count": total,
            "metric": None,
            "observed_strict_pass": forced,
            "verdict_state": forced,
            "note": note,
            "failing": [],
        }
    if total == 0:
        return {
            "criterion_id": cid,
            "criterion_name": meta["name"],
            "principle": meta["principle"],
            "automation": meta["automation"],
            "applicable_count": 0,
            "pass_count": 0,
            "fail_count": 0,
            "undetermined_count": 0,
            "metric": None,
            "observed_strict_pass": NA,
            "verdict_state": NA,
            "note": note or "적용기회 없음",
            "failing": [],
        }
    p = sum(1 for o in opportunities if o["verdict"] == PASS)
    f = sum(1 for o in opportunities if o["verdict"] == FAIL)
    u = sum(1 for o in opportunities if o["verdict"] == UNDET)
    strict = FAIL if f > 0 else (UNDET if u == total else PASS)
    return {
        "criterion_id": cid,
        "criterion_name": meta["name"],
        "principle": meta["principle"],
        "automation": meta["automation"],
        "applicable_count": total,
        "pass_count": p,
        "fail_count": f,
        "undetermined_count": u,
        "metric": round(p / total, 6),
        "observed_strict_pass": "TRUE"
        if strict == PASS
        else ("FALSE" if strict == FAIL else UNDET),
        "verdict_state": strict,
        "note": note,
        "failing": [
            {k: o.get(k) for k in ("selector", "reason", "detail") if k in o}
            for o in opportunities
            if o["verdict"] == FAIL
        ][:25],
    }


# ─────────────────────────── 항목별 판정기 ───────────────────────────


def c_1_1_1(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "img_alt_ax_name"):
        if o.get("aria_hidden") == "true" or o.get("role") in ("presentation", "none"):
            continue  # 접근성 트리에서 제거된 이미지는 적용기회가 아니다
        name = o.get("alt") or o.get("aria_label") or ""
        if o.get("alt") == "":
            v, reason = PASS, "빈 alt(장식용 선언)"
        elif not o.get("has_alt_attr") and not o.get("aria_label") and not o.get("aria_labelledby"):
            v, reason = FAIL, "대체 텍스트 없음"
        elif name.strip() and name.strip().lower() in (
            "image",
            "img",
            "photo",
            "이미지",
            "사진",
            "그림",
        ):
            v, reason = FAIL, "의미 없는 대체 텍스트"
        else:
            v, reason = PASS, "대체 텍스트 존재"
        ops.append({**o, "verdict": v, "reason": reason, "detail": (o.get("src") or "")[:80]})
    return _result("1.1.1", ops, note="alt 존재 여부는 기계 판정, 내용 적절성은 사람 검토 필요")


def c_1_2_1(probe: dict) -> dict:
    """자막은 음성 정보의 대체 수단이다. 음성이 없는 미디어는 적용기회가 아니다.

    자동재생·음소거·제어 없음의 조합은 배경 장식 영상이며 KWCAG 2.2 자막 제공의 대상이 아니다.
    사용자가 음소거를 해제할 수 있는(controls) 경우에만 음성 존재 가능성을 인정한다.
    """
    ops = []
    for o in _op(probe, "media_track"):
        muted_decorative = o.get("muted") and not o.get("controls")
        if muted_decorative:
            continue  # 적용기회 아님 → NA에 기여
        if o.get("has_caption_track"):
            ops.append({**o, "verdict": PASS, "reason": "자막 트랙 있음"})
        elif o.get("muted"):
            ops.append(
                {**o, "verdict": UNDET, "reason": "음소거 상태이나 제어 제공 — 음성 유무 확인 필요"}
            )
        else:
            ops.append({**o, "verdict": FAIL, "reason": "음성 재생 미디어에 자막 트랙 없음"})
    for o in _op(probe, "media_embed"):
        ops.append({**o, "verdict": UNDET, "reason": "외부 임베드 플레이어 — 자막 확인 불가"})
    return _result("1.2.1", ops, note="음소거·제어 없는 배경 장식 영상은 적용기회에서 제외")


def c_1_3_1(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "table_structure"):
        if o.get("layout_candidate"):
            continue  # 레이아웃 목적 표는 데이터표 적용기회가 아니다
        problems = []
        if not o.get("has_caption") and not o.get("summary"):
            problems.append("제목/요약 없음")
        if o.get("th_count", 0) == 0:
            problems.append("제목 셀(th) 없음")
        elif o.get("th_with_scope", 0) == 0 and o.get("td_with_headers", 0) == 0:
            problems.append("scope/headers 연결 없음")
        v = FAIL if problems else PASS
        ops.append({**o, "verdict": v, "reason": ", ".join(problems) or "표 구성 요건 충족"})
    return _result("1.3.1", ops)


def c_1_3_2(probe: dict) -> dict:
    o = (_op(probe, "dom_visual_order") or [{}])[0]
    rate = o.get("inversion_rate")
    if rate is None:
        return _result("1.3.2", [], note="선형구조 표본 부족")
    v = FAIL if rate > 0.15 else PASS
    return _result(
        "1.3.2",
        [
            {
                **o,
                "verdict": v,
                "reason": f"DOM/시각 순서 불일치율 {rate:.1%}",
                "selector": "document",
            }
        ],
        note="자동 신호이며 최종 판정은 사람 검토 필요",
    )


def c_1_4_2(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "autoplay_media"):
        dur = o.get("duration")
        if o.get("muted") and not o.get("loop"):
            v, r = PASS, "음소거 자동재생"
        elif o.get("controls"):
            v, r = PASS, "정지 제어 제공"
        elif dur is not None and dur <= 3:
            v, r = PASS, "3초 이하"
        else:
            v, r = FAIL, "제어 없는 자동 재생"
        ops.append({**o, "verdict": v, "reason": r})
    return _result("1.4.2", ops)


def c_1_4_3(probe: dict) -> dict:
    """배경색을 실제로 확정한 텍스트만 판정한다.

    불투명 배경을 찾지 못했거나 배경 이미지 위에 놓인 텍스트는 계산된 대비가 실제와 다르다.
    이런 지점을 FAIL로 세면 미흡률이 측정 오류만큼 부풀려지므로 UNDETERMINED로 분리한다.
    """
    ops = []
    for o in _op(probe, "contrast_ratio"):
        req = o.get("required", 4.5)
        ratio = o.get("ratio")
        if ratio is None or o.get("offscreen"):
            continue
        unresolved = (not o.get("bg_resolved")) or o.get("behind_image")
        if unresolved:
            ops.append(
                {
                    **o,
                    "verdict": UNDET,
                    "reason": "배경색 미확정(투명 조상 또는 배경 이미지) — 대비 계산 불가",
                    "detail": (o.get("text") or "")[:40],
                }
            )
            continue
        if ratio <= 1.05:
            ops.append(
                {
                    **o,
                    "verdict": UNDET,
                    "reason": f"전경·배경 동색으로 산출(ratio={ratio}) — 측정 실패로 간주",
                    "detail": (o.get("text") or "")[:40],
                }
            )
            continue
        ops.append(
            {
                **o,
                "verdict": PASS if ratio >= req else FAIL,
                "reason": f"대비 {ratio} (요구 {req})",
                "detail": (o.get("text") or "")[:40],
            }
        )
    return _result(
        "1.4.3", ops, note="배경 미확정·배경 이미지 위·동색 산출 지점은 UNDETERMINED로 분리"
    )


def c_2_1_1(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "keyboard_operable"):
        if o.get("onclick_only"):
            v, r = FAIL, "클릭 핸들러만 있고 키보드 초점 불가"
        elif o.get("negative_tabindex") and (o.get("role") in ("button", "link")):
            v, r = FAIL, "tabindex 음수로 키보드 접근 차단"
        else:
            v, r = PASS, "키보드 초점 가능"
        ops.append({**o, "verdict": v, "reason": r})
    return _result("2.1.1", ops, note="실제 키 조작 결과가 아닌 정적 초점 가능성 신호")


def c_2_1_2(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "keyboard_operable"):
        if o.get("positive_tabindex"):
            ops.append({**o, "verdict": FAIL, "reason": "양수 tabindex로 초점 순서 왜곡"})
        else:
            ops.append({**o, "verdict": PASS, "reason": "초점 순서 왜곡 없음"})
    return _result("2.1.2", ops, note="초점 시각화(focus visible)는 정적 관측으로 확정 불가")


def c_2_1_3(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "target_size"):
        if o.get("inline_in_text"):
            continue  # 문장 속 인라인 링크는 예외
        m = o.get("min_side")
        gap = o.get("nearest_neighbor_gap_css_px")
        if m is None:
            continue
        if m >= TARGET_MIN_CSS_PX:
            v, r = PASS, f"최소변 {m}px"
        elif gap is not None and gap >= TARGET_GAP_MIN_CSS_PX:
            v, r = PASS, f"최소변 {m}px이나 인접 간격 {gap}px 확보"
        else:
            v, r = FAIL, f"최소변 {m}px, 인접 간격 {gap}px"
        ops.append({**o, "verdict": v, "reason": r})
    return _result(
        "2.1.3",
        ops,
        note=f"CSS px 기준 {TARGET_MIN_CSS_PX}px. 물리 mm는 산출하지 않음(기기 실측 필요)",
    )


def c_2_1_4(probe: dict) -> dict:
    ops = [
        {
            **o,
            "verdict": FAIL,
            "reason": f"단일 문자 단축키 '{o.get('accesskey')}' — 해제/재정의 수단 확인 필요",
        }
        if len((o.get("accesskey") or "").strip()) == 1
        else {**o, "verdict": PASS, "reason": "수식키 조합"}
        for o in _op(probe, "accesskey")
    ]
    return _result("2.1.4", ops)


def c_2_2_1(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "meta_refresh_timeout"):
        s = o.get("seconds")
        v = PASS if (s is not None and s == 0) else FAIL
        ops.append(
            {
                **o,
                "verdict": v,
                "reason": "즉시 리다이렉트"
                if v == PASS
                else f"{s}초 후 자동 갱신 — 조절 수단 없음",
                "selector": "meta[http-equiv=refresh]",
            }
        )
    return _result("2.2.1", ops)


def c_2_2_2(probe: dict) -> dict:
    """대상은 '자동 시작되어 5초 이상 지속되며 정보를 전달하는' 움직임이다.

    로딩 인디케이터, 스크롤 유도 화살표, aria-hidden 장식은 정보를 전달하지 않으므로
    적용기회가 아니다. 정지 수단의 실제 제공 여부는 자동 관측으로 확정할 수 없으므로
    남은 대상도 FAIL이 아니라 UNDETERMINED로 둔다.
    """
    ops = []
    for o in _op(probe, "autoplay_motion_control"):
        if o.get("loader_like") or o.get("scroll_hint_like"):
            continue
        if o.get("aria_hidden") == "true":
            continue
        if (o.get("text_len") or 0) == 0 and (o.get("area") or 0) < 4000:
            continue
        ops.append(
            {
                **o,
                "verdict": UNDET,
                "reason": f"반복 애니메이션({o.get('animation')}) — 정지 수단 제공 여부 사람 검토 필요",
            }
        )
    return _result("2.2.2", ops, note="로딩·스크롤 유도 장식 제외. 정지 수단 존재는 자동 확인 불가")


def c_2_4_1(probe: dict) -> dict:
    links = _op(probe, "skip_navigation")
    lm = (_op(probe, "landmark") or [{}])[0]
    skip = [x for x in links if x.get("looks_like_skip")]
    if skip:
        working = [x for x in skip if x.get("target_exists")]
        v = PASS if working else FAIL
        r = "건너뛰기 링크 동작" if working else "건너뛰기 링크의 대상이 존재하지 않음"
        ops = [{**skip[0], "verdict": v, "reason": r}]
    elif lm.get("main", 0) > 0:
        ops = [
            {
                "selector": "main",
                "verdict": PASS,
                "reason": "main 랜드마크로 반복영역 건너뛰기 제공",
            }
        ]
    else:
        ops = [
            {
                "selector": "document",
                "verdict": FAIL,
                "reason": "건너뛰기 링크와 main 랜드마크 모두 없음",
            }
        ]
    return _result("2.4.1", ops)


def c_2_4_2(probe: dict) -> dict:
    o = (_op(probe, "page_frame_title") or [{}])[0]
    ops = []
    title = (o.get("title") or "").strip()
    if not title:
        ops.append({"selector": "title", "verdict": FAIL, "reason": "페이지 제목 없음"})
    elif len(title) < 2:
        ops.append({"selector": "title", "verdict": FAIL, "reason": "제목이 너무 짧음"})
    else:
        ops.append({"selector": "title", "verdict": PASS, "reason": f"제목 '{title[:40]}'"})
    for f in o.get("frames") or []:
        v = PASS if (f.get("title") or "").strip() else FAIL
        ops.append(
            {
                "selector": f.get("selector"),
                "verdict": v,
                "reason": "프레임 제목 " + ("있음" if v == PASS else "없음"),
            }
        )
    seq = o.get("heading_sequence") or []
    if seq:
        skips = sum(1 for a, b in pairwise(seq) if b - a > 1)
        ops.append(
            {
                "selector": "headings",
                "verdict": FAIL if skips > 0 else PASS,
                "reason": f"제목 레벨 건너뜀 {skips}회" if skips else "제목 레벨 순차",
            }
        )
    return _result("2.4.2", ops)


def c_2_4_3(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "link_text"):
        if o.get("empty_name"):
            v, r = FAIL, "링크 이름 없음"
        elif o.get("ambiguous"):
            v, r = FAIL, f"맥락 없는 링크 텍스트 '{o.get('text')}'"
        else:
            v, r = PASS, "링크 텍스트 존재"
        ops.append({**o, "verdict": v, "reason": r, "detail": (o.get("href") or "")[:60]})
    return _result(
        "2.4.3", ops, note="주변 문맥으로 목적이 드러나는 경우는 사람 검토에서 구제 가능"
    )


def c_2_5_3(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "label_in_name"):
        v = PASS if o.get("label_contained") else FAIL
        ops.append(
            {
                **o,
                "verdict": v,
                "reason": "접근가능이름에 시각 레이블 포함"
                if v == PASS
                else f"시각 '{o.get('visual_text')}' ≠ 이름 '{o.get('aria_label')}'",
            }
        )
    return _result("2.5.3", ops)


def c_2_5_4(probe: dict) -> dict:
    o = (_op(probe, "motion_actuation") or [{}])[0]
    uses = (
        o.get("devicemotion_listener")
        or o.get("deviceorientation_listener")
        or (o.get("inline_motion_attr") or 0) > 0
    )
    if not uses:
        return _result("2.5.4", [], note="동작기반 작동 미사용")
    return _result(
        "2.5.4",
        [
            {
                "selector": "window",
                "verdict": UNDET,
                "reason": "동작 기반 작동 감지 — 대체 조작 수단 확인 필요",
            }
        ],
    )


def c_3_1_1(probe: dict) -> dict:
    o = (_op(probe, "html_lang") or [{}])[0]
    if o.get("valid"):
        v, r = PASS, f"lang='{o.get('lang')}'"
    elif o.get("lang"):
        v, r = FAIL, f"lang 값 형식 오류: '{o.get('lang')}'"
    else:
        v, r = FAIL, "html lang 속성 없음"
    return _result("3.1.1", [{"selector": "html", "verdict": v, "reason": r}])


def c_3_2_1(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "on_focus_change"):
        v = FAIL if o.get("context_change_hint") else PASS
        ops.append(
            {
                **o,
                "verdict": v,
                "reason": "초점/선택만으로 맥락 변화 가능" if v == FAIL else "맥락 변화 신호 없음",
            }
        )
    return _result("3.2.1", ops, note="실제 실행 결과가 아닌 인라인 핸들러 정적 신호")


def c_3_2_2(probe: dict) -> dict:
    o = (_op(probe, "help_mechanism") or [{}])[0]
    links = o.get("help_links") or []
    if not links:
        return _result("3.2.2", [], note="도움 정보 링크 미발견 — 다중 페이지 확인 필요")
    return _result(
        "3.2.2",
        [{"selector": "help", "verdict": PASS, "reason": f"도움 정보 링크 {len(links)}개"}],
        note="여러 페이지에서 동일 위치인지는 단일 페이지로 확인 불가",
    )


def c_3_3_2(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "form_label"):
        if o.get("any_programmatic_label"):
            v, r = PASS, "프로그래밍적 레이블 연결됨"
        elif o.get("placeholder") or o.get("title"):
            v, r = FAIL, "placeholder/title만 있고 레이블 없음"
        else:
            v, r = FAIL, "레이블 없음"
        ops.append({**o, "verdict": v, "reason": r})
    return _result("3.3.2", ops)


def c_3_3_3(probe: dict) -> dict:
    o = (_op(probe, "accessible_auth") or [{}])[0]
    n_cap = (o.get("captcha_iframe") or 0) + (o.get("captcha_img") or 0)
    ops = []
    if n_cap:
        ops.append(
            {
                "selector": "captcha",
                "verdict": FAIL,
                "reason": f"인지 기능 테스트(CAPTCHA) {n_cap}개, 대체 수단 미확인",
            }
        )
    if o.get("password_autocomplete_off"):
        ops.append(
            {
                "selector": "input[type=password]",
                "verdict": FAIL,
                "reason": "비밀번호 자동완성 차단 — 붙여넣기/자동입력 대체수단 확인 필요",
            }
        )
    if not ops and (o.get("password_fields") or 0) > 0:
        ops.append(
            {"selector": "input[type=password]", "verdict": PASS, "reason": "인지 테스트 없음"}
        )
    return _result("3.3.3", ops)


def c_3_3_4(probe: dict) -> dict:
    ops = []
    for o in _op(probe, "autocomplete"):
        if not o.get("identity_field_hint"):
            continue
        v = PASS if (o.get("autocomplete") or "").strip() not in ("", "off") else FAIL
        ops.append(
            {
                **o,
                "verdict": v,
                "reason": f"autocomplete='{o.get('autocomplete')}'"
                if v == PASS
                else "개인정보 입력란에 autocomplete 없음",
            }
        )
    return _result("3.3.4", ops)


def c_4_1_1(probe: dict) -> dict:
    o = (_op(probe, "markup_validity") or [{}])[0]
    ops = []
    dup = o.get("duplicate_id_count") or 0
    ops.append(
        {
            "selector": "document",
            "verdict": FAIL if dup else PASS,
            "reason": f"중복 id {dup}개" if dup else "중복 id 없음",
            "detail": ", ".join((o.get("duplicate_ids") or [])[:8]),
        }
    )
    ni = o.get("nested_interactive") or 0
    if ni:
        ops.append({"selector": "document", "verdict": FAIL, "reason": f"대화형 요소 중첩 {ni}개"})
    for key, label in (("li_outside_list", "목록 밖 li"), ("td_outside_table", "표 밖 td/th")):
        n = o.get(key) or 0
        if n:
            ops.append({"selector": "document", "verdict": FAIL, "reason": f"{label} {n}개"})
    return _result("4.1.1", ops, note="전체 HTML 검증기가 아닌 핵심 구조 오류 탐지")


def c_4_2_1(probe: dict) -> dict:
    o = (_op(probe, "aria_validity") or [{}])[0]
    ops = []
    inv = o.get("invalid_role_count") or 0
    broken = o.get("broken_aria_ref_count") or 0
    hidden = o.get("aria_hidden_focusable") or 0
    if (o.get("role_count") or 0) == 0 and not (inv or broken or hidden):
        return _result("4.2.1", [], note="ARIA 미사용")
    ops.append(
        {
            "selector": "document",
            "verdict": FAIL if inv else PASS,
            "reason": f"유효하지 않은 role {inv}개" if inv else "role 값 유효",
        }
    )
    if broken:
        ops.append(
            {"selector": "document", "verdict": FAIL, "reason": f"끊어진 aria 참조 {broken}개"}
        )
    if hidden:
        ops.append(
            {
                "selector": "document",
                "verdict": FAIL,
                "reason": f"aria-hidden 안에 초점 가능 요소 {hidden}개",
            }
        )
    return _result("4.2.1", ops)


DETECTORS = {
    "1.1.1": c_1_1_1,
    "1.2.1": c_1_2_1,
    "1.3.1": c_1_3_1,
    "1.3.2": c_1_3_2,
    "1.4.2": c_1_4_2,
    "1.4.3": c_1_4_3,
    "2.1.1": c_2_1_1,
    "2.1.2": c_2_1_2,
    "2.1.3": c_2_1_3,
    "2.1.4": c_2_1_4,
    "2.2.1": c_2_2_1,
    "2.2.2": c_2_2_2,
    "2.4.1": c_2_4_1,
    "2.4.2": c_2_4_2,
    "2.4.3": c_2_4_3,
    "2.5.3": c_2_5_3,
    "2.5.4": c_2_5_4,
    "3.1.1": c_3_1_1,
    "3.2.1": c_3_2_1,
    "3.2.2": c_3_2_2,
    "3.3.2": c_3_3_2,
    "3.3.3": c_3_3_3,
    "3.3.4": c_3_3_4,
    "4.1.1": c_4_1_1,
    "4.2.1": c_4_2_1,
}


def judge(probe: dict) -> dict[str, Any]:
    """probe 결과 전체를 33개 검사항목으로 판정한다."""
    results = {}
    for cid in CRITERIA:
        fn = DETECTORS.get(cid)
        if fn is None:
            results[cid] = _result(
                cid,
                [],
                forced=UNDET,
                note="단일 세션 자동 관측으로 적용기회 확정 불가 — 사람 검토 대상",
            )
        else:
            results[cid] = fn(probe)
    applicable = [r for r in results.values() if r["verdict_state"] not in (NA, UNDET)]
    fails = [r for r in applicable if r["verdict_state"] == FAIL]
    return {
        "criteria": results,
        "summary": {
            "criteria_total": len(CRITERIA),
            "criteria_applicable": len(applicable),
            "criteria_na": sum(1 for r in results.values() if r["verdict_state"] == NA),
            "criteria_undetermined": sum(
                1 for r in results.values() if r["verdict_state"] == UNDET
            ),
            "criteria_pass": len(applicable) - len(fails),
            "criteria_fail": len(fails),
            "failed_criteria": sorted(r["criterion_id"] for r in fails),
            "observed_accessibility_failure_count": sum(r["fail_count"] for r in results.values()),
            "total_opportunities": sum(r["applicable_count"] for r in results.values()),
            "observed_strict_pass": "FALSE" if fails else ("TRUE" if applicable else UNDET),
        },
    }
