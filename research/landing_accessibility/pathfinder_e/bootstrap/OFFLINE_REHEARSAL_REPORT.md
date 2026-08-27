# Offline Fixture Route Rehearsal — P0 Report

## 무엇을 했는가

네트워크 접근이 전혀 없는 상태에서 내 산출물 3종(trace/route-candidate/summary)의 **스키마
완결성**을 검증했다. target F1-03(신한은행)을 예시로 골랐지만 모든 DOM/AX/screenshot/bbox 값은
`build_synthetic_example.py`가 지어낸 SYNTHETIC placeholder다 — 실제 신한은행 페이지를 관측한
값이 아니다.

절차: OPEN_GLOBAL_MENU(전체메뉴 열기) → SELECT_FUNCTION(이체 선택) → AUTH_GATE(로그인 불가피)
3-state 가상 경로를 만들고, 각 state 가 내 역할 §7 이 요구하는 44개 evidence 필드를 전부 채우는지
스크립트로 assert 했다.

**결과: PASS — 3개 state 전부 44/44 필드 존재.** (`build_synthetic_example.py` 실행 로그 참조)

## 이게 검증하는 것 / 안 하는 것

검증함:
- §7 evidence 필드 목록이 자기모순 없이 실제로 채워질 수 있는 구조인가
- §8B route-candidate JSON 예시 스키마가 target-agnostic하게 재사용 가능한가 (F1-03 데이터로
  채워봐도 깨지지 않음)
- action_token 이 04_FLOW_CODEBOOK 18종 중 실제 값(OPEN_GLOBAL_MENU, SELECT_FUNCTION)으로
  채워지는 경로가 route-candidate 의 `route[]` 배열과 자연스럽게 매핑되는가

검증하지 않음(의도적으로 범위 밖):
- 실제 웹사이트에서 candidate 여러 개가 경쟁할 때의 ranking 로직 — synthetic 예시는 candidate
  경쟁 상황을 단순화했다(§6.3 deterministic branching 은 실제 DOM 다양성 위에서만 진짜로 시험됨)
- fixture corpus 기반 대규모 리허설 — `claude-b/pc-fixture`(로컬 합성 픽스처, Playwright 기반,
  27종 fixture 언급)가 이미 존재하지만 이번 P0 에서는 열어보지 않았다. LA-ORCH-3E §12 가 이걸
  P3("offline flow-engine fixture scouting 적극 사용")으로 명시적으로 나중 단계로 분류하고
  있어서, P0 범위를 "내 스키마 자체가 self-consistent한가"로 좁혔다 — B의 fixture corpus를
  재사용하는 본격 리허설은 P3 진입 시 별도로 할 일로 남긴다.
- 실제 액션 실행(클릭/스크롤) — Playwright 자체를 이번에 띄우지 않았다. P0 는 OFFLINE 이므로
  브라우저 프로세스를 실행하지 않는 게 맞는 경계라고 판단했다.

## B가 replay 할 때 주의할 것 (§8C 요구사항)

- 이 synthetic 예시의 `trace_ref`/hash 값은 전부 가짜(`synthfake_` prefix)다 — 실제 replay
  검증에 이 파일을 evidence로 쓰면 안 된다. 스키마 템플릿으로만 참조.
- route-candidate의 `task_contract_hash`/`endpoint_contract_hash`는 `TASK_CONTRACT_INVENTORY.json`을
  가리키는 참조일 뿐 이 문서 자체에 값을 복제하지 않았다 — 단일 진실 소스 유지 목적.

## Unresolved ambiguity

- E 자신의 scout_status 어휘(10종)와 v3 endpoint_status 어휘(7종)가 문자 그대로 다르다
  (`ACTION_TOKEN_COMPATIBILITY_CHECK.md` §5) — B가 canonical replay로 승격할 때 이 매핑을
  누가 공식화할지 A 판단 필요. E가 임의로 매핑표를 만들어 canonical화하지 않는다.
- candidate 경쟁 상황(동일 state에서 여러 후보)의 실제 ranking 안정성은 synthetic 리허설로
  검증 불가 — 실제 REAL scout 또는 fixture corpus 리허설에서만 확인 가능.
