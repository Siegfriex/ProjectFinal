# Action-Token Compatibility Check — v3 Flow Codebook vs 기존 Collector

**대상**: `SSOTV3/04_FLOW_CODEBOOK_v3.0.md` §2 (18 canonical action token, ABSTAIN 포함)
**대조군**: `claude-b/integration-current`@397a10d (316 테스트, dom_order 최신 authority — B 계열에서 가장
최신·통합된 브랜치) 의 `research/landing_accessibility/src/landing_accessibility/engine/{l1_engine.py,vocabulary.py}`
**방법**: 코드 직접 읽기(class/enum member 열거). 이름 유사성으로 짐작하지 않았다.

## 결론 (한 줄)

**기존 collector 엔진에는 v3 의 action_token 개념 자체가 없다.** v2.1 엔진은 "클릭이 발생했다 +
신호 boolean 4개"만 기록하는 raw event 모델이고, v3 는 "무슨 의미의 행동이었는가"를 18개 고정
어휘로 라벨링하는 semantic sequence 모델이다. 이건 필드 이름을 바꾸는 문제가 아니라 새 분류 로직이
필요한 gap이다.

## 1. v3 18 token (XLSX `04_FLOW_CODEBOOK` 시트로 실측, 마크다운 문서와 일치 확인됨)

```
OPEN_GLOBAL_MENU, OPEN_LOCAL_MENU, SWITCH_TAB, EXPAND_ACCORDION, SELECT_CATEGORY,
SELECT_FUNCTION, INPUT_QUERY, SELECT_ORIGIN, SELECT_DESTINATION, SELECT_DATE,
SUBMIT_QUERY, SELECT_RESULT, OPEN_ITEM_DETAIL, OPEN_PLACE_DETAIL, DISMISS_OBSTRUCTION,
AUTH_GATE, ENDPOINT_REACHED, ABSTAIN
```

## 2. 기존 엔진 (`l1_engine.py`) 이 실제로 기록하는 것

`TaskStep` dataclass (step_index, state_id, url, **clicked_selector**, control_role,
accessible_name, area_signal_detected, endpoint_signal_detected, auth_gate_detected,
popup_present, counts_toward_depth, depth_segment) — **action_token 필드가 없다.**
"어떤 종류의 행동인가"는 저장되지 않고, "CSS selector 하나를 클릭했다 + 그 결과로 무슨 신호가
켜졌는가"만 저장된다. `TaskManifest.path` 도 `list[dict[str, Any]]`로 미타입, 18-token vocabulary에
바인딩돼 있지 않다.

## 3. `vocabulary.py` 의 20개 StrEnum — 전부 확인, 겹치는 게 없다

`vocabulary.py`는 action-sequence 어휘가 아니라 **상태/분류 어휘**다:
`MeasurementStatus`, `EndpointStatus`(FUNCTION_ENDPOINT_REACHED/AUTH_GATE_REACHED/
PAYMENT_GATE_REACHED/PERSONAL_DATA_REQUIRED/CAPTCHA/BLOCKED/UNRESOLVED), `AreaSignalStatus`,
`DepthSegment`, `InteractionArchetype`(7-way RF), `GateKind`, `RegionSignalType`,
`ClassificationStatus`, `InterruptLabel`, `DismissMethod`, `DismissFailureMode`, `VerdictState`,
`AdjudicationStatus`, `ReviewTaskType`, `TriageLabel`, `ImpactLevel`, `AIReviewStatus`,
`AutomationGrade`, `EpisodeKind`(TEXT_INPUT/SCROLL), `EpisodeEndedBy`, `InputMode`,
`SelectionBasis`, `SelectionStatus`. 18개 action token 중 문자 그대로 일치하는 것은 **0개**.

## 4. 항목별 대조

| v3 대상 | 기존 코드 대응 | 상태 |
|---|---|---|
| 18개 action token (OPEN_GLOBAL_MENU 등) | 없음 — `clicked_selector`(raw) 만 존재 | **GAP** — 신규 분류 로직 필요 |
| `endpoint_status` (REACHED/AUTH_GATE/PUBLIC_WEB_UNOBSERVABLE/APP_REQUIRED/EVIDENCE_DEFECT/BLOCKED/ABSTAIN) | `EndpointStatus`(FUNCTION_ENDPOINT_REACHED/AUTH_GATE_REACHED/PAYMENT_GATE_REACHED/PERSONAL_DATA_REQUIRED/CAPTCHA/BLOCKED/UNRESOLVED) | **부분 대응, 값 불일치** — 명시적 mapping 표 필요. PUBLIC_WEB_UNOBSERVABLE/APP_REQUIRED/ABSTAIN 은 기존에 없음. PAYMENT_GATE/PERSONAL_DATA/CAPTCHA 를 별도 terminal 로 두는 것도 v3 엔드포인트 상태와는 다른 설계(v3 는 이런 상황 자체를 forbidden-action 으로 막고 진입 전 정지) |
| `entry_zone`/`entry_control_type`/`entry_label_modality`/`accessible_name_source`/`label_relation`/`nav_container_type`/`reveal_direction` | 없음 | **GAP** — vocabulary.py 에 대응 enum 전무 |
| `legacy_archetype`(FINANCIAL_ACTION_ENTRY 등) | `InteractionArchetype` 7-way | **재사용 가능** — v3 CSV `legacy_archetype` 컬럼값과 1:1 이름 일치(FINANCIAL_ACTION_ENTRY/ITEM_DETAIL/UTILITY_ENTRY/PLACE_LOOKUP). D3-03/D3-04 대로 critical path 아닌 legacy metadata 로만 사용 |
| `DISMISS_OBSTRUCTION` + obstruction 필드군 | `InterruptLabel`/`DismissMethod`/`DismissFailureMode` | **재사용 가능** — 개념적으로 가장 가까운 대응. 방해요소 감지·해제 로직은 이미 있음 |
| depth 산출 시 scroll/typing 제외 | `EpisodeKind`(TEXT_INPUT/SCROLL) 로 depth 비가산 처리 이미 구현 | **재사용 가능** |
| `NED`/`IED`/`MPFED` | `TaskEntry.ned/ied/mpfed` | **호환** — v3 문서(§7)가 "legacy compatibility"로 명시적으로 유지하라고 한 필드와 일치 |

## 5. E 자신의 scout-status 어휘와 v3 endpoint_status 도 다르다는 점 (자체 점검)

내 역할(§9)의 route 상태 vocabulary — `ENDPOINT_REACHED / AUTH_GATE / PUBLIC_WEB_UNOBSERVABLE /
APP_REQUIRED / WAF_OR_CHALLENGE / TIMEOUT / EVIDENCE_DEFECT / NO_SAFE_ROUTE_FOUND /
CONTRACT_AMBIGUITY / SAFETY_STOP` — 도 v3 `04_FLOW_CODEBOOK`의 `endpoint_status`
(REACHED/AUTH_GATE/PUBLIC_WEB_UNOBSERVABLE/APP_REQUIRED/EVIDENCE_DEFECT/BLOCKED/ABSTAIN)와
글자 그대로 같지 않다(WAF_OR_CHALLENGE/TIMEOUT/NO_SAFE_ROUTE_FOUND/CONTRACT_AMBIGUITY/
SAFETY_STOP 은 E 고유, BLOCKED/ABSTAIN 은 v3 고유). B 가 canonical replay 로 승격할 때
이 둘 사이의 명시적 mapping 이 필요하다 — E 의 scout_status 를 v3 endpoint_status 로
그대로 밀어넣지 않는다(canonical=false 원칙, Scout Route ≠ Canonical Measurement).

## 6. 결론이 B/A 에게 의미하는 것 (E 는 결정하지 않음, 관측만)

- 18-token action 분류기는 이 세션 시점 기준 **아무 브랜치에도 없다.** B 의 task-first runner 구현
  범위에 이게 포함되는지 A 가 명시적으로 스코프에 넣어야 한다.
- `entry_zone`/`nav_container_type`/`reveal_direction`/`label_relation` 등 공간/라벨 측정 변수도
  전무 — v3 Flow Codebook §4 의 측정 변수 대부분이 신규 구현 대상이다.
- 재사용 가능한 것(obstruction 감지/해제, episode 비가산 처리, NED/IED/MPFED, legacy archetype)은
  분명히 있다 — 전체를 새로 짜야 하는 건 아니다.
