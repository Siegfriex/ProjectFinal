# V3_REFREEZE_DECISION — Phase P0

발행 A · 2026-08-28T02:07 KST · base `5c22faeb`
Phase `P0 V3_CONTRACT_REFREEZE` · REAL scope `NO_REAL` · Exit gate `V3_CONTRACT_FROZEN`

---

## 1. 채택 선언

`SSOTV3/` 21 파일을 **연구설계·측정계약의 유일 권위**로 채택한다.

동시에 다음이 성립한다 — 채택은 릴리스가 아니다.

- v3 는 새 REAL scope 를 발행하지 않는다 (00 §13 · 09 D3-20 · README 권위경계).
- `E001_FULL` 59 는 SUSPENDED 유지. **12 PASS → full59 자동승격은 영구 금지.**
- v3 main 50 은 candidate 이며 precheck + A manifest freeze 전 REAL 금지.
- 유효 REAL 은 `V2_DIAGNOSTIC` 12 뿐이다.

원본 팩은 **byte 단위로 수정하지 않는다.** 수정이 필요한 항목은 §4 의 v3.0.1 successor delta 로 처리한다.

## 2. 보존 확인 — METHODOLOGY_PRESERVED §1~§8

피벗 전 A 가 동결한 `control/method/METHODOLOGY_PRESERVED.md` 와 v3 00 §12 를 대조한 결과 **§1~§8 중 폐기된 항목은 0 이다.** 상세 대조표는 `V3_ADOPTION_RECORD.md` §3.

요지: 피벗은 방법론이 아니라 **대상**을 바꿨다. §0 의 "보존하지 않는다" 목록(7 archetype · MPFED/NED/IED · OverlayCoverage · 59 frame · W1~W4 범위 · 0.85/0.75)이 v3 의 대응물로 채워졌고, 게이트 *수치*는 아직 비어 있다 — 새 대상의 게이트는 정의되지 않았다. **A 는 지금 새 게이트 수치를 만들지 않는다.**

이 대조는 A 의 자기판정이다. Director 지시에 따라 **C 에게 독립검증을 요청**한다 (`T-A-V3-ASSURE-001`).

## 3. D3-01 ~ D3-20 판정

**18 ACCEPT · 2 MODIFY · 0 REJECT.**

| ID | 판정 | 사유 |
|---|---|---|
| D3-01 Cross-Service Task Entry Flow Divergence 를 primary construct | ACCEPT | 관측가능한 단위이고 claim boundary 가 00 §11 에 명시돼 있다 |
| D3-02 task 는 화면 관측 전 deterministic contract 로 고정 | ACCEPT | 결과의존 자유도를 상류에서 제거한다. v2.1 최대 병목의 정확한 시정 |
| D3-03 RF 7-way 를 main critical path 에서 퇴역 | ACCEPT | 삭제가 아니라 의존 제거. §5 참조 |
| D3-04 7 archetype 을 legacy metadata 로 유지 | ACCEPT | quota 강제 없음. 단 §6 한계 참조 |
| D3-05 Flow raw primary / Depth derived | ACCEPT | Depth null 이 상류 관측부재와 뒤섞이던 문제를 구조적으로 분리한다 |
| D3-06 5 families × 10 = 50 candidate | **MODIFY** | frame 은 수용. **두 개의 freeze-time 조건 추가** — §4.1 |
| D3-07 금융 secondary 는 main n 을 늘리지 않음 | ACCEPT | within-provider repeated task. 분모 오염 방지 |
| D3-08 APP_REQUIRED/APP_ONLY 는 precheck 에서 사전 replacement | **MODIFY** | 원칙 수용. **replacement 명부 사전등록 요구** — §4.2 |
| D3-09 generic login 존재로 중단 금지, 불가피 시점만 AUTH_GATE | ACCEPT | `presence ≠ operative` 결함군의 직접 시정 |
| D3-10 visible label / accessible name 분리 저장 | ACCEPT | 두 값이 다르다는 것 자체가 관측대상이다 |
| D3-11 menu_dependency 를 action sequence 에서 파생 | ACCEPT | 수기 라벨의 판단 자유도 제거 |
| D3-12 task-specific occlusion 이 primary, page max coverage 는 보조 | ACCEPT | 기하 겹침→방해 라는 D-R0-72 결함군의 시정 |
| D3-13 STFP 단일 합산점수 금지 | ACCEPT | 가중치가 곧 미검증 가설이 된다 |
| D3-14 12 는 METHOD_QUALIFICATION, 자동진행 금지 | ACCEPT | Director Master Directive §3 과 동일 |
| D3-15 59 는 USAGE_BENCHMARK/ROBUSTNESS | ACCEPT | 폐기가 아니라 역할 재지정 |
| D3-16 cross-provider 차이를 WCAG 위반으로 판정하지 않음 | ACCEPT | WCAG 규범 범위는 동일 set of web pages 내부다. 축을 분리해야 둘 다 살아남는다 |
| D3-17 D 는 flow/spatial/label/sequence 측정연구로 이동 | ACCEPT | 비권위 유지 조건 그대로 |
| D3-18 Task family 는 gold label 문제가 아니라 research contract | ACCEPT | 화면 관측으로 변경 금지가 핵심 |
| D3-19 인지부하/전이효과는 person-level 연구 전까지 확정 금지 | ACCEPT | STFP 는 proxy 라는 명칭 자체가 이 경계를 담고 있다 |
| D3-20 v3 팩 자체는 새 REAL release 아님 | ACCEPT | 본 결정문이 이를 재확인한다 |

## 4. v3.0.1 Successor Delta — 원본 무수정

원본 `09_DECISION_LOG_v3.0.md` 를 덮어쓰지 않는다. 아래 두 항목은 `V3_0_1_SUCCESSOR_DELTA.md` 에 successor 로 기록하며, **freeze 이전(P2)에 충족돼야 하는 조건**이다.

### 4.1 D3-06 MODIFY — 두 freeze-time 조건

**(a) F5 날짜 fixture 를 절대일자로 고정할 것.**
`01 §2` 는 F5 fixture 를 `날짜=T+1` 로 둔다. T 가 target 별 수집일이면 T+1 은 target 마다 달라지고, 요일·공휴일에 따라 운행편 자체가 달라진다. 그러면 관측된 결과 차이가 서비스 구조 차이인지 날짜 차이인지 분리되지 않는다. **matched comparison 의 전제가 깨진다.**
→ freeze 시 절대일자 1개를 manifest 에 박거나, 전 target 을 동일 수집일 창 안에서 수행하고 `collection_date_kst` 로 검증한다. 둘 중 무엇인지 freeze 전에 정한다.

**(b) family 내 비독립성 층을 사전등록할 것.**
`05 §5` 는 F5 에 ground/air 층을 이미 두었다. F1 은 없다. F1 10 은 시중은행 7 + 지방은행 3 이며, 지방은행은 공통 플랫폼을 쓸 개연성이 있어 "10 개 독립 서비스"가 자명하지 않다.
→ F1 에 `시중 7 / 지방 3` 층을 **precheck 시작 전에** 사전등록한다. 결과를 본 뒤 층을 만들면 그것은 사후 분할이다.

두 항목 모두 결과를 보기 전에 정해지므로 사전등록 규율에 위배되지 않는다.

### 4.2 D3-08 MODIFY — replacement 명부 사전등록

`01 §1` 은 "precheck 부적격이면 같은 family replacement 로 collection 전에 교체"라고만 정한다. 교체 **후보를 언제 정하는지**가 비어 있다. precheck 결과를 본 뒤 대체재를 고르면, 그것은 채널 적격성이라는 제한된 정보일지언정 관측 후 표본 선택이다.
→ family 별 **순서가 매겨진 예비 명부**를 precheck 시작 전에 동결하고 manifest hash 에 포함한다. 교체는 명부 순서대로만 한다. 명부가 소진되면 n<10 으로 보고하고 임의 보충하지 않는다.

## 5. V2 의존 supersede — 철회가 아니다

Director 지시 그대로 집행한다.

| 대상 | 처리 |
|---|---|
| W2 RF detector 게이트 `NOT_PASSED` @`b28aaa5c` | **철회하지 않는다.** `V2_RETIRED_PATH` 의 유효한 역사적 결과로 보존 |
| `T-A-HOLD-001` (W1_W2_JOINT_GATE HOLD) | **철회하지 않는다.** 같은 방식으로 보존 |
| V3 dependency graph 의 RF classifier gate | **제거한다** — `SUPERSEDE_FOR_V3_PATH` |

이 구분이 중요한 이유: W2 FAIL 을 철회하면 "게이트를 못 넘자 게이트를 없앴다"가 된다. FAIL 은 그대로 두고 **그 게이트가 걸려 있던 경로가 더 이상 main critical path 가 아니라는 사실**만 기록한다. 결과가 나빠서가 아니라 경로가 바뀌어서다. W2 코드도 삭제하지 않는다 (07 Legacy closeout).

동일 원칙으로 `RF001/RF002/D15` 는 "왜 RF auto-classification 을 main 에서 내렸는가"의 audit history 로 보존한다.

## 6. 채택하되 한계로 기록하는 것

- **50 frame 은 7 archetype 중 4개만 덮는다.** F1=FINANCIAL_ACTION_ENTRY, F2=ITEM_DETAIL, F3·F5=UTILITY_ENTRY, F4=PLACE_LOOKUP. QUERY · CONTENT_OPEN · COMMUNICATION_ENTRY 는 대응 family 가 없다. D3-04 가 archetype 을 quota 에서 뺐으므로 결함은 아니나, **59 corpus 와의 비교는 archetype 균형 비교가 아니다.** 보고 시 명시해야 한다.
- **family n=10 은 작다.** 05 §4 가 기술통계 중심으로 제한하나, cross-family 일반화 유혹은 분석 단계에서 다시 발생한다. P6 게이트에서 재확인한다.
- **F1 endpoint 는 대부분 AUTH_GATE 로 끝날 개연성이 높다.** 그 자체가 관측값(auth_gate_stage)이므로 결함은 아니지만, F1 의 flow 분산이 다른 family 보다 구조적으로 짧을 수 있다. 사전 예상으로 기록해 둔다 — 나중에 "예상대로였다"고 사후 서술하지 않기 위함이다.

## 7. P0 Exit 조건

`V3_CONTRACT_FROZEN` 은 다음이 **같은 exact state 를 가리킬 때** 판정한다.

1. B · C · D 의 P0 ACK 각 1건, 각자 exact head SHA 명시
2. C 의 manifest/authority audit — 팩 20/20 독립 재계산 + METHODOLOGY_PRESERVED 대 v3 모순 검증 verdict
3. D 의 bus scanner negative-control fixture 완결 보고
4. A 의 본 결정문 + reconciliation + successor delta (본 커밋)

**하나라도 다른 SHA 를 가리키면 FROZEN 을 선언하지 않는다.**

## 8. 검증하지 않은 것

- 50 candidate 의 실제 mobile-web 적격성 — P2 precheck 이전에는 근거 없음.
- F1~F5 endpoint contract 가 실제로 관측 가능한지 — P4 이전에는 근거 없음.
- C·D 가 커밋한 v3 내재화 내용 — SHA 계보만 확인했다.
- v3.0.1 delta 두 항목이 실행 가능한지 — freeze 시점에 검증한다.
