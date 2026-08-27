# REMEDIATION_CASES

`shadow_lane=ANALYSIS_CURRENT` · 최대 3건 · 선택 기준: evidence completeness ·
distinct mechanism · clear screenshot · clear remediation (4개 게이트, 가중합
아님 — `scripts/extract_remediation_cases.py` docstring 참조).

이 파일은 **템플릿**이다. 실제 산출물은
`scripts/extract_remediation_cases.py --out-path <path>`가
`select_remediation_cases()` + `render_remediation_cases_md()`로 같은 형식을
기계적으로 생성한다 — 이 템플릿을 손으로 채우지 않는다.

> **Evidence-based redesign proposal; user outcome not evaluated.**
> 아래 시정안은 관측된 evidence(DOM/AX/geometry/screenshot)에 근거한 제안이며,
> 고령층 사용자의 실제 성공률·만족도를 측정하거나 예측하지 않는다 (`00 §Hard Scope`
> — full-task usability·실제 고령자 성공률 추정은 이 연구의 범위 밖이다).

---

## Case 1 — `<mechanism_label>`

- `mechanism_id`: `<MECHANISM_ID>`
- `web_target_id`: `<WT-xxxx>`
- `observation_id`: `<OBS-xxxx>`
- `interrupt_id`: `<INT-xxxx-n>`
- `final_label`: `<INTERRUPT_LABEL>`
- screenshot: `<screenshot_path>`
- DOM evidence: `<dom_path>`

**시정 제안**: `<remediation_hint — evidence에서 직접 도출된 구체적 수정안>`

> Evidence-based redesign proposal; user outcome not evaluated.

---

## Case 2 — `<mechanism_label>`

(Case 1과 동일한 필드 구조. mechanism_id는 Case 1과 **달라야 한다** — 같은
결손 유형을 두 번 대표 사례로 뽑지 않는다.)

> Evidence-based redesign proposal; user outcome not evaluated.

---

## Case 3 — `<mechanism_label>`

(위와 동일. 게이트를 통과하는 서로 다른 mechanism이 3개 미만이면 그만큼만
싣는다 — 억지로 3건을 채우지 않는다.)

> Evidence-based redesign proposal; user outcome not evaluated.

---

## 후보가 0건일 때

게이트(evidence completeness · distinct mechanism · clear screenshot · clear
remediation)를 통과한 사례가 없으면 "후보 없음"을 그대로 기록한다. 억지로
게이트 미달 사례를 끼워 넣지 않는다.

> Evidence-based redesign proposal; user outcome not evaluated.
