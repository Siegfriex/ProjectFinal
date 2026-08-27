"""Stage 1 — Applicability(부분) + Required evidence slots.

`probe.json`(`raw_features`, 물리 evidence slot `"probe"`) 만 읽는다. `dom`/`ax`는
읽지 않는다(`stage1_types.PHYSICAL_EVIDENCE_SLOT` 참조).

criterion → raw_features 키 매핑은 이 파일이 유일한 정본이다. 매핑이 없는
criterion(= 이 L0 probe 스키마가 그 신호를 아예 모으지 않음)은 정직하게
`ABSENT_FROM_PROBE_SCHEMA` 로 남긴다 — 있지도 않은 신호를 있는 척 만들지 않는다.

`D-R0-53` cap: `accessible_name_sources`(300) · `target_size`(300) · `contrast`(400).
cap_hit 판정은 **길이 휴리스틱**이다(`len(raw list) >= cap`) — `l0_probe.js` 가
`.slice(0, cap)` 로 자르면서 별도 truncation 플래그를 남기지 않기 때문에, 원래
정확히 cap개였던 페이지와 잘린 페이지를 이 파일만으로는 구분할 수 없다. 그래서
**과소평가(cap_hit=False로 놓치는 방향)가 아니라 과대평가(진짜 cap이 아닌데
cap_hit=True로 보는 방향)로 치우치게** 설계했다 — PASS를 UNDETERMINED로
낮추는 데만 쓰이므로(`stage1_pipeline._finalize`), 과대평가의 대가는 "확정 가능한
PASS를 UNDETERMINED로 조금 더 자주 낮춘다"이지 "FAIL을 숨긴다"가 아니다.

## `T-A-W3-SCHEMA-001` — schema gap 4건 개별 재심사 (정본)

A ACCEPT(`D-R0-51` ACCEPTED_WITH_ONE_DIVERGENCE) 이후 발행된 요구#1: "채울 수
있으면 결함이므로 채운다 / 채울 수 없으면 근거를 제시한다." `l0_probe.js` 전문을
다시 읽고 real evidence(58건)를 스캔해 4건 각각을 판정했다 — coverage 를 올리는
것 자체가 목표가 아니므로(`D-R0-56` 취지), "일단 채워보고 보인다"는 기준이 아니라
"이 신호가 이 criterion 의 official condition 을 실제로 측정하는가"를 기준으로
삼았다.

| criterion | 판정 | 근거 |
|---|---|---|
| `2.2.1` 응답시간 조절 | **못 채운다** | `l0_probe.js` 전문에 `refresh`/`meta[http-equiv]`/session-timeout 관련 코드가 전혀 없다. `raw_features` 12개 키 중 시간제한을 측정하는 것이 하나도 없다. |
| `2.4.1` 반복영역 건너뛰기 | **채울 수 있어 보이지만 안 채운다(의도적)** | `region_signals.declared_regions` 가 존재는 하지만, `l0_probe.js` 를 보면 이건 실제 ARIA landmark(`main`/`nav`/`banner` role)나 skip-link 를 보는 게 아니라 **`[data-region]` fixture 전용 커스텀 마커**만 센다(`querySelectorAll('[data-region]')`). 실 pilot 증거(`OLDER_RELEVANT_KWCAG_SUBSET.md` 동결 근거 T-B-FC-001, n=58)에서 `declared_regions` 길이 0 이 55/58 이었다 — 이 신호로 Applicability 를 내리면 실제 랜드마크/skip-link 유무와 무관하게 거의 항상 "적용기회 없음"을 낸다. 이건 "신호가 없다"보다 나쁘다 — **잘못된 신호로 조용히 결정하는 것**이기 때문이다. 그래서 매핑을 만들지 않았다. |
| `2.5.4` 동작기반 작동 | **못 채운다** | `devicemotion`/`deviceorientation` 이벤트 리스너 등록 여부를 정적 DOM/CSS 관측으로는 볼 수 없다. `motion` raw_features 는 CSS 애니메이션/자동재생만 담고 기기 동작 센서 API 사용 여부는 전혀 담지 않는다. |
| `3.3.4` 반복 입력 정보 | **매핑 누락이었다 — 고쳤다. 단, Outcome 은 그대로 UNDETERMINED** | `gate_signals.username_autocomplete_count`/`tel_autocomplete_count` 는 `input[autocomplete~=...]` 를 직접 세는 **실재하는 비-fixture 신호**다(누락은 초기 구현 실수). 매핑을 추가해 evidence_slot 투명성은 개선했다 — 그러나 이 신호는 "있음"만 셀 수 있고 "있어야 하는데 없음"은 셀 수 없다(속성이 없는 필드는 애초에 이 selector 에 안 걸린다). 그래서 `count==0` 이 "적용기회 없음"인지 "적용기회는 있는데 결함"인지 구분 불가하고, `count>0` 도 다른 필드의 결함을 배제 못한다. **Applicability/Outcome 어느 쪽도 안전하게 못 내려** `_STRUCTURALLY_ASYMMETRIC_EVIDENCE_IDS` 로 강제 UNDETERMINED 처리한다(아래 참조). |

**`D-R0-52` 실측 상한 변경 없음.** 위 재심사 결과 새로 PASS/FAIL 을 낼 수 있게 된
criterion 은 0건이다(`3.3.4` 는 evidence 투명성만 개선됐지 판정 가능해진 게
아니다). 실측 상한은 여전히 **5/22**(`stage1_expectations.EXPECTATION_FUNCS`).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from . import CRITERION_MANIFEST_PATH
from .stage1_types import (
    PHYSICAL_EVIDENCE_SLOT,
    ApplicabilityResult,
    ApplicabilityStatus,
    EvidenceSlotResult,
    EvidenceSlotStatus,
)

# ── manifest 재사용 — Stage 0 이 동결한 22개(applicability != OTHER)를 유일한 정본으로 쓴다.
with open(CRITERION_MANIFEST_PATH, encoding="utf-8") as _f:
    _MANIFEST: dict[str, Any] = json.load(_f)

_MANIFEST_BY_ID: dict[str, dict[str, Any]] = {
    row["criterion_id"]: row for row in _MANIFEST["criteria"]
}

#: `D-R0-52` 분모 — `criterion_manifest.json` 에서 유도한다(하드코딩 재복제 금지).
OLDER_RELEVANT_IDS: frozenset[str] = frozenset(
    cid for cid, row in _MANIFEST_BY_ID.items() if row["applicability"] != "OTHER"
)

#: 22개의 codebook automation_grade — manifest 에서 유도(하드코딩 재복제 금지).
CODEBOOK_AUTOMATION_GRADE: dict[str, str] = {
    cid: row["automation_grade"]
    for cid, row in _MANIFEST_BY_ID.items()
    if cid in OLDER_RELEVANT_IDS
}

#: `D-R0-53` — 세 plane(B/A/C) 합의 cap. `probe_version` 이 바뀌어 cap 이 바뀌면
#: 이 표부터 갱신해야 한다.
PROBE_SLOT_CAPS: dict[str, int] = {
    "accessible_name_sources": 300,
    "target_size": 300,
    "contrast": 400,
}

_MISSING = object()


def _raw_feature(probe: dict, key: str) -> Any:
    return (probe.get("raw_features") or {}).get(key, _MISSING)


# ── criterion 별 extract 함수 — raw_features 를 그 criterion 이 다루는 "후보 항목 리스트"로
# 좁힌다. 반환값 규약: `_MISSING` 이면 이 probe 에 해당 raw_features 키가 없다는 뜻이고
# (스키마 자체가 없는 게 아니라 이 한 건에서 못 모았다는 뜻일 수도 있다 — 둘을 이 계층에서는
# 구분하지 않는다. `probe_version` 차이로 구분해야 한다면 그건 Stage 2의 몫이다),
# 그 외에는 `list[dict]`.


def _extract_1_4_2(probe: dict) -> Any:
    motion = _raw_feature(probe, "motion")
    if motion is _MISSING:
        return _MISSING
    return list(motion.get("autoplay_media") or [])


def _extract_1_4_3(probe: dict) -> Any:
    contrast = _raw_feature(probe, "contrast")
    if contrast is _MISSING:
        return _MISSING
    return list(contrast)


def _extract_2_1_3(probe: dict) -> Any:
    target_size = _raw_feature(probe, "target_size")
    if target_size is _MISSING:
        return _MISSING
    return list(target_size)


def _extract_2_4_2(probe: dict) -> Any:
    viewport = _raw_feature(probe, "viewport")
    if viewport is _MISSING:
        return _MISSING
    # 2.4.2(제목 제공)는 개별 DOM 요소가 아니라 **페이지 전체**에 적용되는 보편 기준이다 —
    # 후보를 "페이지 1개"로 표현해 나머지 파이프라인(Applicability=항목 존재 여부로 판단)과
    # 균일하게 맞춘다.
    return [dict(viewport)]


def _extract_3_3_2(probe: dict) -> Any:
    names = _raw_feature(probe, "accessible_name_sources")
    if names is _MISSING:
        return _MISSING
    return [n for n in names if n.get("tag") in ("input", "select", "textarea")]


def _extract_2_2_2(probe: dict) -> Any:
    motion = _raw_feature(probe, "motion")
    if motion is _MISSING:
        return _MISSING
    items: list[dict] = []
    if motion.get("infinite_animation_count"):
        items.append({"kind": "infinite_animation", "count": motion["infinite_animation_count"]})
    if motion.get("marquee_count"):
        items.append({"kind": "marquee", "count": motion["marquee_count"]})
    for m in motion.get("autoplay_media") or []:
        items.append({"kind": "autoplay_media", **m})
    return items


def _extract_2_4_3(probe: dict) -> Any:
    names = _raw_feature(probe, "accessible_name_sources")
    if names is _MISSING:
        return _MISSING
    return [n for n in names if n.get("tag") == "a"]


def _extract_3_3_3(probe: dict) -> Any:
    gate = _raw_feature(probe, "gate_signals")
    if gate is _MISSING:
        return _MISSING
    keys = (
        "otp_input_count",
        "password_input_count",
        "identity_number_input_count",
        "simple_auth_provider_count",
        "carrier_option_count",
    )
    return [{"kind": k, "count": gate.get(k)} for k in keys if (gate.get(k) or 0) > 0]


def _extract_3_3_4(probe: dict) -> Any:
    """`T-A-W3-SCHEMA-001` 요구#1 — 매핑 누락이었다. `gate_signals` 의
    `username_autocomplete_count`/`tel_autocomplete_count` 는 `input[autocomplete~=X]`
    를 직접 센 실재 신호다(fixture 아님). 다만 "긍정 신호가 있었다"만 알려줄 뿐
    Applicability/Outcome 을 안전하게 결정하기엔 부족하다 — 그래서 이 신호는
    evidence_slot 투명성에만 쓰고, `applicability()` 에서 `_STRUCTURALLY_ASYMMETRIC_
    EVIDENCE_IDS` 로 강제 UNDETERMINED 처리한다(아래 참조)."""
    gate = _raw_feature(probe, "gate_signals")
    if gate is _MISSING:
        return _MISSING
    keys = ("username_autocomplete_count", "tel_autocomplete_count")
    return [{"kind": k, "count": gate.get(k)} for k in keys if (gate.get(k) or 0) > 0]


#: criterion_id → (raw_features 키들, extract 함수 | None).
#: extract 가 None 이면 이 L0 probe 스키마에 대응하는 신호가 아예 없다는 뜻이다
#: (ABSENT_FROM_PROBE_SCHEMA 로 항상 귀결) — Stage 1 의 "구현 안 함"이 아니라
#: "수집기가 이 신호를 안 모은다"는 사실을 그대로 코드에 남긴다.
_SLOT_SPEC: dict[str, tuple[tuple[str, ...], Callable[[dict], Any] | None]] = {
    # AUTO_DECIDABLE — Expectation 까지 실제 구현
    "1.4.2": (("motion",), _extract_1_4_2),
    "1.4.3": (("contrast",), _extract_1_4_3),
    "2.1.3": (("target_size",), _extract_2_1_3),
    "2.4.2": (("viewport",), _extract_2_4_2),
    "3.3.2": (("accessible_name_sources",), _extract_3_3_2),
    # AUTO_DECIDABLE — 이 L0 probe 스키마에 대응 신호 없음 (schema gap, T-A-W3-SCHEMA-001
    # 재심사 결과 "못 채운다" 확정 — 근거는 이 파일 모듈 docstring 표 참조)
    "2.2.1": ((), None),
    # `region_signals.declared_regions` 는 존재하지만 `[data-region]` fixture 마커만
    # 감지한다(실 ARIA landmark/skip-link 아님, pilot 55/58 이 항상 빈 배열) — 의도적으로
    # 매핑하지 않았다. 신호가 없는 것보다, 틀린 신호로 조용히 결정하는 게 더 나쁘다.
    "2.4.1": ((), None),
    "2.5.4": ((), None),
    # AUTO_DECIDABLE — 신호는 실재하나(T-A-W3-SCHEMA-001 재심사로 새로 매핑) 구조적으로
    # 비대칭이라 Outcome 을 못 낸다 — `_STRUCTURALLY_ASYMMETRIC_EVIDENCE_IDS` 참조.
    "3.3.4": (("gate_signals",), _extract_3_3_4),
    # AUTO_FLAG_ONLY — Applicability/evidence 는 실제 구현하되 Outcome 은 항상 UNDETERMINED
    # 로 cap 된다(`stage1_pipeline._finalize`, `DECISION-1`). Expectation 은 구현하지 않는다
    # (candidate_verdict 는 항상 None) — 어차피 outcome 에 반영되지 않을 verdict 를 굳이
    # 만들어 오해를 살 위험을 만들지 않는다.
    "2.2.2": (("motion",), _extract_2_2_2),
    "2.4.3": (("accessible_name_sources",), _extract_2_4_3),
    "3.3.3": (("gate_signals",), _extract_3_3_3),
    # AUTO_FLAG_ONLY — schema gap
    "1.3.2": ((), None),
    "3.2.1": ((), None),
    "3.2.2": ((), None),
    # NOT_AUTOMATABLE — 코드북 정의상 적용기회 자체를 자동 확정 불가. slot 조회 자체를
    # 시도하지 않는다(시도해도 의미가 없다 — Applicability 가 항상 UNDETERMINED).
    "1.3.3": ((), None),
    "1.4.1": ((), None),
    "1.4.4": ((), None),
    "2.4.4": ((), None),
    "2.5.1": ((), None),
    "2.5.2": ((), None),
    "3.3.1": ((), None),
}

assert set(_SLOT_SPEC) == OLDER_RELEVANT_IDS, (
    set(_SLOT_SPEC) ^ OLDER_RELEVANT_IDS
)  # 등록 누락/과잉을 import 시점에 즉시 잡는다.


def get_slot_items(criterion_id: str, probe: dict) -> Any:
    """이 criterion 이 다루는 필터링된 후보 항목 리스트. `_MISSING` = 확장 불가(스키마 없음)."""
    _slot_names, extract = _SLOT_SPEC[criterion_id]
    if extract is None:
        return _MISSING
    return extract(probe)


#: `T-A-W3-SCHEMA-001` 요구#1 — evidence slot 은 실재하지만(fixture 아님) "긍정 신호만
#: 셀 수 있고 결측/위반은 셀 수 없는" 구조적으로 비대칭인 criterion. Applicability 를
#: 안전하게 APPLICABLE 도 NOT_APPLICABLE 도 내릴 수 없다 — count>0 이 곧 "완전 준수"를
#: 뜻하지 않고, count==0 이 "적용기회 없음"과 "결측"을 구분해주지 않는다. coverage 를
#: 올리는 게 목표가 아니므로(`D-R0-56`), 신호가 생겼다고 바로 판정에 쓰지 않는다.
_STRUCTURALLY_ASYMMETRIC_EVIDENCE_IDS: frozenset[str] = frozenset({"3.3.4"})
_STRUCTURALLY_ASYMMETRIC_EVIDENCE_REASON: dict[str, str] = {
    "3.3.4": (
        "gate_signals.username_autocomplete_count/tel_autocomplete_count 는 실재하는 "
        "신호이나 'input[autocomplete~=X]' 매칭이라 속성이 없는 개인정보 필드는 애초에 "
        "후보에 안 잡힌다 — count==0 이 '적용기회 없음'인지 '적용기회는 있는데 결측'인지 "
        "구분 불가하고, count>0 도 다른 필드의 결측을 배제 못한다. Applicability/Outcome "
        "어느 쪽도 안전하게 내릴 수 없다(T-A-W3-SCHEMA-001)."
    ),
}


def applicability(criterion_id: str, probe: dict) -> ApplicabilityResult:
    """`Applicability` 단계 — criterion 이 이 관측에 적용되는가.

    `NOT_AUTOMATABLE` 은 코드북 정의상("정적/단일 세션 자동 관측으로는 적용기회
    자체를 확정할 수 없음") 항상 `UNDETERMINED` 다 — evidence 를 보기 전에 이미
    정해진 구조적 상한이다(`D-R0-52`).
    """
    grade = CODEBOOK_AUTOMATION_GRADE[criterion_id]
    if grade == "NOT_AUTOMATABLE":
        return ApplicabilityResult(
            ApplicabilityStatus.UNDETERMINED,
            "automation_grade=NOT_AUTOMATABLE — 코드북 정의상 적용기회 자체를 자동 확정할 수 없다",
        )

    if criterion_id in _STRUCTURALLY_ASYMMETRIC_EVIDENCE_IDS:
        items = get_slot_items(criterion_id, probe)
        found = 0 if items is _MISSING else len(items)
        return ApplicabilityResult(
            ApplicabilityStatus.UNDETERMINED,
            f"{_STRUCTURALLY_ASYMMETRIC_EVIDENCE_REASON[criterion_id]} "
            f"(참고: 이번 관측에서 긍정신호 {found}건 — 판정에는 쓰지 않았다)",
        )

    items = get_slot_items(criterion_id, probe)
    if items is _MISSING:
        return ApplicabilityResult(
            ApplicabilityStatus.UNDETERMINED,
            "이 criterion 이 필요로 하는 raw_features 키가 이 probe 에 없다 (schema gap)",
        )
    if len(items) == 0:
        return ApplicabilityResult(
            ApplicabilityStatus.NOT_APPLICABLE, "관련 후보 항목이 0개 — 적용기회 없음"
        )
    return ApplicabilityResult(
        ApplicabilityStatus.APPLICABLE, f"관련 후보 항목 {len(items)}개 관측"
    )


def required_evidence_slots(criterion_id: str, probe: dict) -> EvidenceSlotResult:
    """`Required evidence slots` 단계 — 어떤 raw_features 키를 봤고, cap 절단
    의심이 있는지를 기록한다."""
    slot_names, extract = _SLOT_SPEC[criterion_id]
    if extract is None:
        return EvidenceSlotResult(
            slot_names=slot_names,
            physical_evidence_slot=PHYSICAL_EVIDENCE_SLOT,
            status=EvidenceSlotStatus.ABSENT_FROM_PROBE_SCHEMA,
            cap_hit=False,
            item_count=None,
            reason="이 criterion 에 대응하는 raw_features 매핑이 Stage 1 registry 에 없다",
        )

    items = get_slot_items(criterion_id, probe)
    if items is _MISSING:
        return EvidenceSlotResult(
            slot_names=slot_names,
            physical_evidence_slot=PHYSICAL_EVIDENCE_SLOT,
            status=EvidenceSlotStatus.ABSENT_FROM_PROBE_SCHEMA,
            cap_hit=False,
            item_count=None,
            reason=f"probe.raw_features 에 {slot_names} 키가 없다",
        )

    cap_hit = False
    for key in slot_names:
        cap = PROBE_SLOT_CAPS.get(key)
        if cap is None:
            continue
        raw_list = (probe.get("raw_features") or {}).get(key)
        raw_len = len(raw_list) if isinstance(raw_list, list) else None
        if raw_len is not None and raw_len >= cap:
            cap_hit = True

    if len(items) == 0:
        status = EvidenceSlotStatus.EMPTY
        reason = "필터 이후 항목 0개"
    elif cap_hit:
        status = EvidenceSlotStatus.PRESENT_CAP_AMBIGUOUS
        reason = (
            f"raw_features[{slot_names}] 길이가 cap({[PROBE_SLOT_CAPS.get(k) for k in slot_names]})"
            " 과 같다 — 원래 그 개수였는지 잘린 것인지 이 파일만으로는 구분 불가(D-R0-53)"
        )
    else:
        status = EvidenceSlotStatus.PRESENT
        reason = f"항목 {len(items)}개, cap 미도달"

    return EvidenceSlotResult(
        slot_names=slot_names,
        physical_evidence_slot=PHYSICAL_EVIDENCE_SLOT,
        status=status,
        cap_hit=cap_hit,
        item_count=len(items),
        reason=reason,
    )
