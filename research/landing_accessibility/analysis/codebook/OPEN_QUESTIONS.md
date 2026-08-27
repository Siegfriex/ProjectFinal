# OPEN QUESTIONS — P-A A4 Functional Codebook

- 제기자: P-A A4 (Functional Codebook) → **LANE A SHADOW 재정합** (2026-08-27)
- 판정 요청 대상: P-A 감사 (adversarial + ssot), 일부는 P-B/P-C로 이월
- 초판 base SHA: `6fad79fa98e1ec7d315122d79794b4d5442bb42e`
- **현재 base SHA: `d5f1da5652953542d5c8be377026cc3293f2075a`** (`status = SHADOW_PREPARATORY`)
- 이 문서의 미결 항목은 SHADOW lane이 **스스로 확정하지 않는다.** 아래 Q-1만 LANE 0의
  `A2` 개정으로 **닫혔고**, 그 확인은 문서 대조이지 SHADOW lane의 판정이 아니다.

| id | 제목 | 등급(제안) | 차단 대상 | 판정 권한 |
|---|---|---|---|---|
| ~~Q-1~~ | ~~gate가 endpoint인 archetype에서 `endpoint_status`를 무엇으로 기록하는가~~ | — | — | **CLOSED** — `A2` §1.5.1a (`V2-C003`·`V2-C004`, base `d5f1da5`) |
| Q-2 | `UTILITY_ENTRY` endpoint — U-1 채택 여부 | **P1 / blocking** | `ANALYSIS_AND_TASK_CODEBOOK_FROZEN` | P-A 감사 |
| Q-3 | `UTILITY_ENTRY`의 `ExcessDepth` 기준선 적격성 | P2 | `READY_FOR_E001_V2` | P-A 감사 → 분석 phase |
| Q-4 | 브라우저 네이티브 권한 프롬프트의 기록 슬롯 | P2 | `L0_L1_ENGINE_READY` | P-C |
| Q-5 | `ITEM_DETAIL` 「핵심 상품정보」 조작화 승인 | P2 | `TARGET_TASK_FRAME_FROZEN` | P-A 감사 |
| Q-6 | `business_domain`을 통계 검정 그룹으로 쓸 수 있는가 | P2 | 분석 phase | 분석 phase |
| Q-7 | `COMMUNICATION_ENTRY`의 1:1 메신저 포함 여부 | P2 | `TARGET_TASK_FRAME_FROZEN` | P-A 감사 |
| Q-8 | `mapping_freeze_stamp` / `mapping_run_manifest` 의 물리 저장 위치 | P2 | `ANALYSIS_AND_TASK_CODEBOOK_FROZEN` | P-A 감사 + P-B |
| **Q-9** | gate 종류(로그인 gate ↔ 본인인증 gate)의 판별 규칙 | **P1 / blocking** | `TARGET_TASK_FRAME_FROZEN`, `L0_L1_ENGINE_READY` | P-A 감사 + 코드북 |

---

## ~~Q-1~~ — **CLOSED** (LANE 0가 `A2` §1.5.1a로 닫았다)

| | |
|---|---|
| 닫힌 곳 | `A2_VOCABULARY_AND_SCHEMA_BINDING.md` §1.5.1a — 규칙 E-5 · E-6 · **E-6a** · E-7 · E-8 · E-9 · E-10 |
| 닫은 사이클 | `V2-C003`(신설) → `V2-C004`(감사 시정) |
| 확인 base SHA | `d5f1da5652953542d5c8be377026cc3293f2075a` |
| 확인 방법 | SHADOW lane이 `d5f1da5`의 `A2` 문면을 직접 대조. **SHADOW lane의 판정이 아니다** |

**채택된 답 (요지, 정본은 `A2` §1.5.1a 규범표).**
`00 §3` L1 표가 그 행에 명시한 종류의 gate가 관측되면
`endpoint_status = FUNCTION_ENDPOINT_REACHED` + `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE`,
`endpoint_reached = 1`, depth는 정수다. gate 종류는 archetype별로 갈린다 —
금융은 로그인·본인인증 둘 다, **커뮤니티는 로그인 gate만**이다.

**초판 제안 `GATE-1`은 폐기됐다.** 두 지점이 틀렸다.

1. **기록 슬롯** — `endpoint_signal_type = GATE_SIGNAL`이 아니라 `endpoint_status_detail`이다.
   규칙 E-8의 `auth gate` 유병률 합집합과 규칙 E-10의 층화가 후자를 조건으로 쓴다.
2. **gate 종류 일반화** — 두 archetype을 똑같이 "로그인/인증 gate"로 묶은 것이
   `00 §3` 커뮤니티 행을 넓히는 SSOT 침범이었다. `V2-C003` 감사가
   `a2-1-5-1a-widens-00-3-community-gate-clause-to-any-auth-gate`로 지적해 `V2-C004`가 시정했다.

**남은 이행 의무 (Q-1이 닫히면서 생긴 것).**

- 규칙 E-10 층화 병기 — 두 archetype의 `MPFED`·`ExcessDepth`·`mart_archetype_summary` 지표를
  `ENDPOINT_VIA_AUTH_GATE` 여부로 갈라 병기한다. **P-H 소관.**
- 규칙 E-6a의 실행 전제인 **gate 종류 판별 규칙**이 아직 없다 → **Q-9로 신설.**

---

## Q-2 — `UTILITY_ENTRY` endpoint 채택 여부 (**핵심 과제**)

### 사실

`00` §6은 `UTILITY_ENTRY`를 archetype에 열거했으나 `00` §3 L1 표에 대응 행이 없다.
`A1` §1.2가 endpoint 정의를 명시적으로 **P-A endpoint codebook으로 이관**했고,
그때까지 `mapping_status` 미동결 유지를 지시했다. `A2` 규칙 P-2가 그것을 강제한다
(`region_signal_type = CODEBOOK_PENDING` → `FROZEN` 불가).

### A4 제안 (U-1, 권고)

> **대표 유틸리티 기능의 전용 기능면(function surface)이 열리고,
> 그 기능의 1차 조작 대상(primary control)이 PRESENT ∧ HITTABLE 상태로 관측된 순간.**

- `PRESENT ∧ HITTABLE`은 `A1` §1.1이 이미 정의한 술어의 **재사용**이다. 새 술어 없음.
- 1차 조작 대상은 `02` §6 후보 랭킹의 그 state SELECTED 후보(`A1` §5와 동일 개념).
- **control을 누르지 않는다.** 노출·조작가능 관측까지.
- `gate_is_endpoint = false`, `endpoint_signal_type` 기본 `DOM_AX_ROLE`.

### 근거

| # | 근거 |
|---|---|
| G1 | **명명 정합** — `_ENTRY` 접미사 family(`COMMUNICATION_ENTRY`·`FINANCIAL_ACTION_ENTRY`)의 `00` §3 endpoint는 진입형("작성영역 진입", "금융기능 진입")이다 |
| G2 | **깊이 수준 정합** — `00` §3의 7 endpoint는 전부 완료가 아닌 진입이며 `A1` §2.1이 통상 경로를 4 이내로 상정했다 |
| G3 | **절대 제외 미침범** — 발급·전환·신청 완료 앞에서 멈춘다 |
| G4 | **관측 가능성** — DOM/AX + hit-test로 `02` §1 우선순위 1단계에서 닫힌다 |
| G5 | **이질성 봉쇄** — 도구 종류와 무관하게 "기능면 도달"은 같은 의미를 갖는다 |

### 대안 (감사가 고를 수 있는 선택지)

| id | 내용 | 장점 | 위험 |
|---|---|---|---|
| **U-1** *(권고)* | 기능면 도달 + 1차 조작 대상 PRESENT ∧ HITTABLE | G1~G5 | 단일목적 유틸리티에서 랜딩=기능면 → `MPFED=0` 질량 (→ Q-3) |
| **U-1g** | U-1 + gate 분기(`gate_is_endpoint = true`) | 로그인 선행형 유틸리티의 depth가 `NULL`로 사라지지 않는다 | `00` §3이 gate 분기를 두 행에만 부여했다. 세 번째로의 확장은 SSOT 미부여 권한 |
| **U-2** | 유틸리티 기능이 1회 실행돼 결과 상태가 화면에 반영된 순간 | `QUERY`·`CONTENT_OPEN`과 같은 행위 완결형 | 결과 정의가 서비스마다 이질(G5). 발급·신청류에서 **절대 제외 침범 위험** |
| **U-3** | archetype 폐지 — 6종 강제 배정, 불가하면 `EXCLUDED` | 새 정의를 만들지 않는다 | `00` §6 열거값 삭제 = SSOT 위반. 강제 분류는 `00` §9 정신 위반 + 6종 중앙값 오염 |
| **U-4** | U-1 채택 + `ExcessDepth` 기준선에서 제외 | 이질 잔여군이 상대깊이를 오염시키지 않는다 | `00` §7·§11에 없는 **분석 규칙 신설** → A4 권한 밖 (→ Q-3) |

### 판정 요청

1. U-1 / U-1g / U-2 / U-3 / U-4 중 무엇을 채택하는가?
2. 채택 시 `region_signal_type`·`endpoint_signal_type`을 `CODEBOOK_PENDING` → `DOM_AX_ROLE`로 전이시키는 주체와 시점은?
3. 기각 시 `UTILITY_ENTRY` task는 P-B 이후에도 계속 미동결로 남는가, `EXCLUDED`로 가는가?

---

### Q-2 보충 — LANE A SHADOW가 정리한 근거 (2026-08-27) · **결정 없음**

> **SHADOW lane은 Q-2를 결정하지 않는다.** A0 결정(`PHASE_GATES` §4)은 SHADOW lane에
> preparatory 작업만 허용하고, `A2` §6.4가 `UTILITY_ENTRY` endpoint를 P-A 소관으로 유지한다.
> 아래는 감사·Director가 판정할 때 필요한 **사실과 문면**을 모아둔 것이며 권고를 갱신하지 않는다.

**(가) `d5f1da5` 시점에도 SSOT는 여전히 비어 있다.** 재확인한 문면:

| 위치 | 문면 |
|---|---|
| `A2` §1.5.1a 규범표 | `UTILITY_ENTRY`는 `QUERY`·`CONTENT_OPEN`·`ITEM_DETAIL`·`PLACE_LOOKUP`과 같은 행에 묶여 **모든 gate 종류가 `AUTH_GATE_REACHED`** |
| `A2` §1.5.1a 규칙 E-6 | *"`UTILITY_ENTRY`는 `00 §3`에 대응 행 자체가 없으므로 …"* — endpoint 승격 확대 금지 대상으로 명시 |
| `A2` §1.9 규칙 P-2 | `region_signal_type = CODEBOOK_PENDING` 인 task는 `mapping_status = FROZEN` 전이 **불가** |
| `A2` §6.4 | `UTILITY_ENTRY` archetype의 endpoint 정의 → 산출 phase **P-A** |

**Q-1의 해소가 Q-2에 준 것.** `A2` 규칙 E-6이 gate-as-endpoint 확대를 **명시적으로** 금지하면서
`UTILITY_ENTRY`를 그 대상으로 호명했다. 즉 초판이 열어둔 선택지 **U-1g는 이제 SSOT 문면과 직접 충돌한다.**
U-1g를 채택하려면 `A2` §1.5.1a 규칙 E-6과 `00 §3`을 함께 개정해야 하며, 그것은 P-A 권한 밖이다.
**이것은 U-1g의 기각이 아니라 채택 비용의 확정이다** — 판정은 여전히 감사의 몫이다.

**(나) 차단 상태의 실제 크기.** `ANALYSIS_AND_TASK_CODEBOOK_FROZEN`과
`TARGET_TASK_FRAME_FROZEN`이 규칙 P-2로 막혀 있다. 다만 SHADOW lane의 실측으로는
**차단 규모의 상한이 아직 미측정**이다 — `UTILITY_ENTRY`로 분류될 entity 수는 pilot mapping
표본(15건) 밖에서는 세지 않았고, 전수 매핑은 P-B 소관이다. 감사가 규모를 근거로 삼으려면
그 수를 먼저 확정해야 한다.

**(다) SHADOW pilot mapping이 관측한 것.** `analysis/pilot/` 15건에서 `UTILITY_ENTRY`
후보로 몰린 건은 **전부 `abstain`** 처리됐다 — endpoint 정의가 없으면 archetype을 붙여도
task가 성립하지 않기 때문이다. 이는 U-3(archetype 폐지)의 논거가 아니라
**"정의가 없으면 강제분류가 아니라 abstain으로 흐른다"는 경로가 실제로 작동한다**는 관측이다
(`A2` §2.3 강제분류 미유발 경로).

**(라) 판정 시 함께 볼 것.** Q-3(`ExcessDepth` 기준선 적격성)은 Q-2의 **결과에 종속**이다.
U-1을 채택하면 단일목적 도구에서 `MPFED = 0` 질량이 생겨 Q-3이 즉시 발화한다.
두 질문을 따로 판정하면 Q-2 채택 직후 Q-3이 blocking으로 되돌아온다.

---

## Q-3 — `UTILITY_ENTRY`의 `ExcessDepth` 기준선 적격성

### 문제

`00` §7: `ExcessDepth = MPFED - 같은 archetype의 중앙값`.
`UTILITY_ENTRY`는 **성격상 잔여군**이라 내부 이질성이 다른 6종보다 크다.
U-1을 채택하면 단일목적 도구에서 `MPFED = 0`이 다수 나올 수 있고,
그러면 이 archetype의 중앙값이 0이 되어 `ExcessDepth`가 사실상 `MPFED` 원값과 같아진다.

### A4가 하지 않은 것

U-4(기준선에서 제외)는 `00` §7·§11에 없는 **분석 규칙 신설**이므로 채택하지 않았다.
A4는 새 연구기준을 만들 권한이 없다.

### 판정 요청

1. `UTILITY_ENTRY`를 `ExcessDepth` 기준선 archetype으로 그대로 쓰는가?
2. 쓰지 않는다면 그 결정은 어느 문서·어느 phase의 권한인가?
3. archetype 내부 이질성 진단(예: 하위군집 존재 여부 보고)을 요구할 것인가?
   — 요구한다면 그것은 `00` §11 robustness(`leave-one-archetype-out`)로 이미 부분적으로 커버되는가?

---

## Q-4 — 브라우저 네이티브 권한 프롬프트의 기록 슬롯

### 문제

`PLACE_LOOKUP` 경로에서 **브라우저 위치권한 프롬프트**가 흔히 나타난다.
- `02` §5 popup/modal 검출은 **DOM 요소**를 대상으로 하므로 네이티브 프롬프트를 잡지 못한다.
- `AUTH_GATE_REACHED`도 `PERSONAL_DATA_REQUIRED`도 아니다(로그인도 개인정보 입력도 아니므로).
- 그런데 화면을 덮고 조작을 막는다는 점에서 Axis B의 초기진입 마찰 그 자체다.

A4의 잠정 처리: **종료조건이 아니다.** 권한을 부여하지 않고 텍스트 검색 경로로 진행한다.
카메라·알림·마이크 권한 프롬프트도 같다.

### 판정 요청

1. 네이티브 권한 프롬프트를 `fact_interrupt_element`에 기록하는가, 별도 슬롯을 두는가, 기록하지 않는가?
2. 기록한다면 `02` §5의 검출 절차(DOM 기반)를 어떻게 확장하는가 — Playwright 권한 이벤트 훅?
3. 이 결정은 `A1` §3(dismiss control 수집절차)의 범위인가?

---

## Q-5 — `ITEM_DETAIL` 「핵심 상품정보」 조작화 승인

### 사실

`00` §3 「쇼핑」 endpoint = *"상품 상세와 **핵심 상품정보**가 보인 순간"*.
`00`·`01`·`02`·`A1`·`A2` 어디에도 "핵심 상품정보"의 정의가 없다.
정의 없이는 endpoint 관측이 재현 불가능하다.

### A4 제안

**동시 충족 조건** — (a) 개별 상품을 식별하는 **상품명 텍스트** + (b) **가격 표기**(품절·가격미표기 등 명시적 부재 문구 포함) + (c) **1차 거래 control**(구매/주문/장바구니 등)이 DOM·AX에 **PRESENT**.
세 요소가 **같은 상세 문서 안에서** 관측되면 충족.

- 이는 `A1` §0.4의 **수집 파라미터**(관측을 재현 가능하게 하는 판정 규칙)이며 **해석 임계값이 아니다.**
- **(c)는 control의 존재이지 누름이 아니다.** 누르면 E-SHAPE 위반.

### 위험

- (a)(b)(c) 중 하나라도 없으면 endpoint 미도달로 처리되므로, **정의가 좁으면 `UNRESOLVED`가 과다**해진다.
- 반대로 (a)만으로 완화하면 목록 카드와 구분되지 않는다.

### 판정 요청

1. (a)+(b)+(c) 동시 충족을 승인하는가? (b)의 "명시적 부재 문구 포함"을 승인하는가?
2. 이것이 **수집 파라미터**라는 분류에 동의하는가? 해석 임계값으로 본다면 `00` §14 금지에 걸린다.
3. 승인 시 P-C `E000_V2`에서 이 조작화의 오탐·미탐을 검증 항목으로 넣는가?

---

## Q-6 — `business_domain`을 통계 검정 그룹으로 쓸 수 있는가

### 사실

`00` §6: Business Domain = **해석·보고용**, Interaction Archetype = **Depth 비교용**.
`00` §11 「그룹 비교」는 Kruskal–Wallis / pairwise permutation / FDR을 열거하지만 **그룹 변수를 명시하지 않는다.**
`00` §11 「기술통계」에는 `domain/archetype 분포`가 함께 있다.

A4는 규칙 BD-USE-4로 **domain을 depth 검정 그룹으로 세우려면 별도 승인이 필요하다**고 잠정 처리했다.

### 판정 요청

1. `00` §11 「그룹 비교」의 그룹은 archetype과 `certified_current`에 한정되는가?
2. domain을 그룹으로 하는 검정을 허용한다면, `00` §6의 "해석·보고용" 규정과 어떻게 정합시키는가?
3. domain 단위 KWCAG PASS/FAIL 비교(depth가 아닌 Axis A)는 별개로 허용되는가?

---

## Q-7 — `COMMUNICATION_ENTRY`의 1:1 메신저 포함 여부

### 사실

`00` §6 archetype 코드명은 `COMMUNICATION_ENTRY`(넓다). `00` §3 L1 표의 대응 행 라벨은 **「커뮤니티」**(좁다).
1:1 메신저(대화방 진입)는 코드명에는 들어가나 표 라벨에는 안 들어간다.

A4 잠정 처리: `00` §6의 archetype 목록이 정본이고 `00` §3 표는 `예:`로 시작하는 **예시**이므로 **포함**으로 판정.
단 판정 근거를 `mapping_basis`에 남긴다.

### 판정 요청

1. 이 확장 해석을 승인하는가?
2. 승인 시 대화방 진입의 endpoint 문안은 무엇인가 — "작성영역 진입"에 준하는가, 별도 분기를 추가하는가?
   (별도 분기 추가는 `00` §3 문안의 확장이므로 A4가 하지 않았다.)
3. 기각 시 메신저류 서비스는 어느 archetype인가 — `UTILITY_ENTRY`인가 `EXCLUDED`인가?

---

## Q-8 — `mapping_freeze_stamp` / `mapping_run_manifest` 의 물리 저장 위치

### 사실

`A2` 규칙 P-1: *"동결 시각과 접근성 산출물 생성 시각의 **순서를 artifact로 남긴다**."*
`PHASE_GATES` P-A: *"인증·KWCAG outcome **차단 확인**"*.
그러나 `01`의 논리표에도 `A2` §5 물리 대응표에도 이 artifact를 담을 슬롯이 없다.
`A2` §5.6은 나머지 논리표가 전부 ABSENT임을 확인했다.

A4가 §3.2에서 정의한 두 artifact:

| artifact | 내용 |
|---|---|
| `mapping_run_manifest` | 실행 시각, base SHA, **허용 입력 경로 목록과 각각의 content hash** |
| `mapping_freeze_stamp` | 동결 시각(UTC), 동결된 행 집합의 hash, base SHA |

이 둘이 없으면 §3.3 입력 allowlist와 §3.2 F5 순서 검증이 **선언에 그친다**
(= V2-C001 감사가 지적한 `선언과 강제수단의 간극`과 동형).

### 판정 요청

1. 두 artifact를 어디에 저장하는가 — `research/landing_accessibility/state/` 아래 새 파일인가, `control/state.json` 확장인가, `07_EVIDENCE_MANIFEST_CONTRACT` 소관인가?
2. F5 순서 검증을 자동화하는 스크립트·테스트를 누가 만드는가 (P-A인가 P-B인가)?
3. `IN-2`의 "manifest에 없는 경로를 읽은 흔적" 탐지는 실현 가능한가 — 실현 불가라면 allowlist는 명예 규정으로 남는데, 그것을 감수하는가?

---

## Q-9 — gate 종류(로그인 gate ↔ 본인인증 gate)의 판별 규칙 `[LANE A SHADOW 신설]`

### 왜 생겼나

Q-1이 닫히면서 `A2` §1.5.1a 규칙 E-6a가 **gate 종류에 따라 endpoint 판정을 가르게** 됐다.
`COMMUNICATION_ENTRY`에서 로그인 gate는 endpoint이고 본인인증 gate는 `AUTH_GATE_REACHED`다.
그런데 `A2`는 그 판별을 **수집기의 재량이 아니라고** 못박으면서 판별 규칙 자체는
codebook 소관으로 넘겼다 — 그리고 그 규칙은 **아직 없다.**

`A2` §1.5.1a 문면: *"codebook이 가르지 못한 gate는 `endpoint_definition` 미충족으로 보아
endpoint로 승격시키지 않는다."*

### 결과

판별 규칙이 없는 동안 `COMMUNICATION_ENTRY`의 모든 gate는 안전측으로 **endpoint가 아니게** 된다.
그러면 Q-1이 풀려던 문제(그 archetype의 depth가 구조적으로 `NULL`)가 **커뮤니티에서 되살아난다.**
즉 Q-9는 Q-1의 해소를 실효화하는 **실행 전제**다.

### 무엇을 정해야 하는가

| # | 정할 것 |
|---|---|
| 1 | 로그인 gate와 본인인증 gate를 가르는 **관측 가능한** 판별 기준 (DOM/AX 신호, 문구, form 구조 중 무엇인가) |
| 2 | 한국 모바일웹의 실제 형태 — 통합인증(PASS 등) 진입, 소셜 로그인, QR/앱 전환, SMS 인증번호가 각각 어느 쪽인가 |
| 3 | 두 성격이 **한 화면에 공존**할 때(로그인 폼 + 본인인증 링크)의 우선순위 |
| 4 | 판별 실패 시의 기본값 — `A2` 문면대로 endpoint 미승격이 맞는가, 별도 세분값이 필요한가 |
| 5 | 이 규칙이 **수집 파라미터**인가 해석 임계값인가 (`00 §14` 금지 대상 여부) |

### SHADOW lane이 하지 않은 것

판별 기준을 **쓰지 않았다.** 실제 gate 화면을 관측하지 않고 문면만으로 만들면
`00 §14`가 금지한 임의 조작화가 되고, 실제 관측은 P-C real-target 영역이라
P0 종료 전에는 금지다(`PHASE_GATES` §4.1 2항). **fixture 기반 조작화는 P-C LANE과 함께 가야 한다.**

### 판정 요청

1. Q-9를 `TARGET_TASK_FRAME_FROZEN`·`L0_L1_ENGINE_READY`의 blocking으로 등재하는가?
2. 판별 규칙 작성 주체는 P-A(codebook)인가 P-C(수집 조작화)인가 — 둘의 협업이면 경계는 어디인가?
3. 규칙이 나오기 전까지 `COMMUNICATION_ENTRY`의 gate를 전부 미승격으로 두는 것을 감수하는가?

---

## 부록 — A4가 스스로 확정하지 **않은** 것 요약

| 항목 | 왜 확정하지 않았나 |
|---|---|
| `UTILITY_ENTRY` endpoint | SSOT가 정의하지 않은 것을 새로 만드는 일이라 감사 판정 대상 (Q-2) |
| gate-as-endpoint 기록 규칙 | `A2`가 어휘 권위이므로 `A2` 개정 없이 발효 불가 (Q-1) |
| `ExcessDepth` 기준선 제외 규칙 | 새 분석 규칙 신설은 A4 권한 밖 (Q-3) |
| 네이티브 권한 프롬프트 처리 | `02` §5 수집절차의 확장이라 P-C 소관 (Q-4) |
| domain 검정 그룹 허용 | `00` §11 해석 권한 (Q-6) |
| 서비스별 실제 매핑 | P-A A5 / P-B 소관. A4는 코드북(규칙)만 만든다 |
| `task_id` 생성 규칙 | P-B 소관 |
| endpoint 신호 탐지 구현 | P-C 소관 |

---

## 부록 2 — LANE A SHADOW가 스스로 확정하지 **않은** 것 `[2026-08-27]`

| 항목 | 왜 확정하지 않았나 |
|---|---|
| Q-2 `UTILITY_ENTRY` endpoint (U-1 채택 여부) | `A2` §6.4가 P-A 소관으로 유지. SHADOW lane은 **근거만 갱신**했고 권고를 바꾸지 않았다. 감사·Director 판정 사항 |
| Q-9 gate 종류 판별 기준의 **내용** | 실제 gate 화면 관측 없이 문면만으로 만들면 임의 조작화다. 실관측은 P0 종료 전 금지 |
| Q-3 ~ Q-8 | 초판 상태 그대로. SHADOW lane이 새로 판단할 근거를 얻지 못했다 |
| pilot mapping 15건의 매핑값 | `mapping_status ∈ {CANDIDATE, AMBIGUOUS_UNRESOLVED}` (stage1 RULE 확정 9건은 `CANDIDATE`, abstain 6건은 `CANDIDATE`를 경유해 `AMBIGUOUS_UNRESOLVED`). `FROZEN`으로 동결하지 않았고 `ANALYSIS_AND_TASK_CODEBOOK_FROZEN`을 닫지 않았다. (CR-002 시정 반영, integration-current) |
