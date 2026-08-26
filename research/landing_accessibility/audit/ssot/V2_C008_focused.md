# V2-C008 / SSOT · Authority Audit — 초점 감사 1건

| 항목 | 값 |
|---|---|
| cycle | `V2-C008` |
| auditor | `ssot` (SSOT / Authority Auditor) |
| 감사 성격 | **초점 감사** — finding 1건의 최종 판정. 전면 재감사 아님 |
| 대상 finding | `ssot-00-3-auth-gate-endpoint-contradicts-a2-1-5-1` |
| 원 severity | P1, `blocking_class = V2_SSOT_FROZEN` |
| 등재 | orchestrator (P-A codebook Q-1), `V2-C003` |
| 직전 상태 | `REMEDIATION_CLAIMED_PENDING_AUDIT` (V2-C003 이래 6사이클 미판정) |
| target | `agent/landing-v2-exec` @ `2025e5667686d42e832298f2dce77b0c7aa6bc07` |
| base | `research/landing-accessibility-main` @ `5a9015d1e95b15304aaf53a73efb475934610b82` |
| control | `control/landing-orchestrator` @ `1d6cedb6aca6933a701275c7c8e14fd7d4628c73` |
| adversarial | `audit/landing-adversarial` @ `cd0a4e62fc1e1582bd56678cec35d688edc695ed` |
| 직전 ssot 감사 | `383c7a053e8099342a62d294449b170a7ee8bcb2` (V2-C007, PASS) |
| 감사일 | 2026-08-27 |
| **verdict** | **CLOSED** |

---

## 0. 판정 태도에 관한 사전 선언

과거 사이클들은 이 id에 대해 "실질은 해소된 것으로 보이나 self-approval 금지에 따라 CLOSED로
단정하지 않는다"는 태도를 반복했다. **그 태도는 잘못 적용된 것이다.** self-approval 금지는
**executor가 자기 시정을 스스로 닫는 것**을 막는 규칙이지, **독립 감사자의 판정 의무**를
면제하는 규칙이 아니다. 이 감사는 exec lane과 분리된 `audit/landing-ssot`에서 수행되며,
따라서 이 보고서의 CLOSED 판정은 self-approval이 아니다. 근거는 아래 §2에 전건 열거한다.

## 1. 원 지적의 재구성 (처음부터 재검토)

원 지적의 구조는 세 명제의 연쇄다.

1. `00 §3` L1 표가 **금융·커뮤니티 두 행의 endpoint 정의 안에 gate 절을 넣었다**
   — 금융 `금융기능 진입 또는 로그인/인증 gate가 나타난 순간`, 커뮤니티 `게시물/스레드/작성영역 진입 또는 로그인 gate`.
2. 당시 `A2 §1.5.1`은 `AUTH_GATE_REACHED`를 **모든 archetype에 대한 일반규칙**으로 두어
   `endpoint_reached = 0`, `NED/IED/MPFED = NULL`로 규정했다.
3. 1과 2가 겹치면 `FINANCIAL_ACTION_ENTRY`·`COMMUNICATION_ENTRY`의 depth가 **구조적으로 전부 NULL**이 되어
   `00 §11` archetype별 Depth 분포, `00 §7` `ExcessDepth` 기준선(= 같은 archetype의 중앙값),
   `01 §10 mart_archetype_summary`의 `MPFED median`·`MPFED IQR`·`endpoint reach`가 그 두 행에서 성립하지 않는다.

명제 1은 target에서 **여전히 참**이다 — `00 §3` L1 표를 직접 읽어 두 행의 원문이 위와 글자 그대로
같음을 확인했다(`00`은 프리즈 문서이며 이 시정 과정에서 바이트가 수정되지 않았다: `A2 §0` 6항).
따라서 시정은 **`A2` 쪽에서만** 이루어져야 했고, 실제로 그렇게 됐다.

## 2. 명제 2의 소멸 — 항목별 확인

### 2.1 두 archetype에서 gate 도달 시 `endpoint_reached = 1` · `MPFED` 산출 (확인 1)

`A2 §1.5.1a` 규범표가 다음을 명시한다.

| archetype | 인정 gate | `endpoint_status` | `endpoint_status_detail` | `endpoint_reached` | `NED/IED/MPFED` |
|---|---|---|---|---|---|
| `FINANCIAL_ACTION_ENTRY` | 로그인 gate **또는** 인증(본인인증) gate | `FUNCTION_ENDPOINT_REACHED` | `ENDPOINT_VIA_AUTH_GATE` | **1** | 정수(`m` 확정, `A1 §1.3`) |
| `COMMUNICATION_ENTRY` | **로그인 gate만** | `FUNCTION_ENDPOINT_REACHED` | `ENDPOINT_VIA_AUTH_GATE` | **1** | 정수(`m` 확정, `A1 §1.3`) |

`§1.5.1` `AUTH_GATE_REACHED` 행 자신이 그 예외를 본문에 담고 있어(`단 00 §3 L1 표가 그 archetype의
endpoint 정의 안에 넣은 종류의 gate에서는 이 값을 쓰지 않는다`) **두 절이 서로를 참조 없이 어긋나는
경로가 없다.** `endpoint_reached ≡ (endpoint_status = FUNCTION_ENDPOINT_REACHED)` 동치식도
`§1.5.1` 말미에서 분기 이후에도 유지됨이 명시된다 — 분기는 저장값을 가를 뿐 동치식을 건드리지 않는다.
따라서 **명제 2가 두 archetype에 대해 더 이상 성립하지 않고, 명제 3의 전건이 끊긴다.**

`§1.5.2`는 `ENDPOINT_VIA_AUTH_GATE`를 `endpoint_status_detail`의 값으로 두고 roll-up 상위값을
`FUNCTION_ENDPOINT_REACHED` **하나로만** 고정한다(그 외 조합은 규칙 S-3으로 존재 불가).
7값 집합은 확장되지 않는다(규칙 E-1).

### 2.2 나머지 5 archetype에서는 일반규칙이 그대로 (확인 2)

같은 규범표의 나머지 두 행:

- `QUERY` · `CONTENT_OPEN` · `ITEM_DETAIL` · `PLACE_LOOKUP` · `UTILITY_ENTRY` — **모든 gate 종류**에서
  `AUTH_GATE_REACHED`(개인정보 입력 요구 시 `PERSONAL_DATA_REQUIRED`), `endpoint_reached = 0`, depth `NULL`.
  근거: `00 §3` 해당 행에 gate 문구 **없음** + `01 §11` 문면 그대로.
- `COMMUNICATION_ENTRY`의 **본인인증 gate** — 같은 취급. 근거: `00 §3` 커뮤니티 행에 인증 gate 문구 없음.

`A1 §1.2` 신호표와 대조해 archetype 7종의 분류가 정확히 갈렸음을 확인했다 — `00 §3`의 7행
(검색/뉴스/영상/쇼핑/지도/금융/커뮤니티)이 `CONTENT_OPEN`에서 뉴스·영상 두 행을 합치므로
gate 절이 있는 행은 금융·커뮤니티 **둘뿐**이고, `UTILITY_ENTRY`는 `00 §3`에 **대응 행 자체가 없다**
(규칙 E-6이 명시적으로 이 예외의 대상에서 제외).

**원 지적이 문제 삼은 "일반규칙"은 archetype별로, 그리고 그 안에서 다시 gate 종류별로 정확히 갈렸다.**
분기 축이 `00 §3` 문면(어느 행에 어떤 gate 절이 있는가)과 **1:1**이며, 그 이상도 이하도 아니다:
규칙 E-6(확대 금지) · E-6a(gate 종류의 archetype별 한정) · §7 11항(금지사항)이 세 자리에서 같은 경계를 반복한다.
`00`보다 넓지도(커뮤니티 본인인증 gate를 endpoint로 올리지 않음) 좁지도(금융의 인증 gate를 빠뜨리지 않음) 않으므로
`A2 §0` 8항(`00`과의 충돌은 언제나 이 문서의 결함)을 위반하지 않는다.

### 2.3 `00 §7` ExcessDepth 기준선 · `00 §11` archetype 분포의 층화 (확인 3)

명제 3이 지목한 두 산출물이 **살아났을 뿐 아니라, 되살아나면서 생긴 2차 위험도 닫혀 있다.**

`MPFED`가 두 archetype에서 산출되면 그 분포는 이제 **두 종류의 관측**(gate가 나타난 시점까지의 깊이
· 실제 기능 진입까지의 깊이)을 담는다. 층화하지 않으면 `00 §7`의 기준선이 혼합분포의 중앙값이 되어
`동종 대비 깊은가`가 아니라 `로그인 벽을 앞에 세웠는가`를 재게 된다. 규칙 **E-10**이 이것을 닫는다:

1. `00 §11` Depth(median/IQR/mode/ECDF/`0/1/2/3/4+`), `00 §7` `ExcessDepth` 기준선,
   `01 §10`의 `n`·`MPFED median`·`MPFED IQR`·`endpoint reach`를
   `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` 여부로 **층별 병기**. **합산값만 제시 금지.**
2. 정본 산식은 불변 — `ExcessDepth = MPFED − 같은 archetype의 중앙값`(`00 §7` 문면 그대로).
   층별 값은 **병기**이며 정본을 대체하지 않는다. → `00`의 바이트를 건드리지 않고 요구를 얹는 형식이다.
3. 층 크기(`endpoint_via_auth_gate_rate` + 층별 `n`)를 반드시 노출. 층 `n`이 작으면 그 사실을 적고 산출하지 않는다.
4. `00 §7 별도 기록`(auth gate를 Depth와 합치지 않는다)과 충돌하지 않음 — gate는 depth에 **더해지는 항**이
   아니라 depth의 **정지점**이며 `m`을 늘리지 않는다. 유병률은 규칙 E-8이 별도 집계한다.
5. 층화는 해석을 만들지 않는다(`00 §14` Claim Boundary 유지).

**섞인 분포로 되돌아가는 경로가 문서·파이프라인 양쪽에서 닫혀 있다**:
`A2 §7` 금지사항 **14항**(두 endpoint 의미를 한 분포에 섞어 제시하지 않는다),
`§6.3` 가드 행(`두 archetype의 MPFED 계열 지표가 층별 값 없이 합산값만 산출되면 실패`),
`§6.3.1` 실패주입 **I-9**(층 구분 없이 합산값만 산출 → **차단**). 즉 층화 누락은
보고 관행이 아니라 **파이프라인 실패 조건**이다.

부수적으로 `auth gate` 유병률 지표도 과소집계되지 않는다 — 규칙 **E-9**가
`fact_task_entry.auth_gate_before_endpoint`(`01 §6`의 **실재 컬럼**임을 직접 확인)의 허용값(`0`/`1`)·
정본 원천(`fact_task_step.auth_gate_detected`)·산식·경계 6사례를 확정하고,
규칙 **E-8**의 2항 합집합
`auth_gate_observed = (auth_gate_before_endpoint = 1) OR (endpoint_status_detail = 'ENDPOINT_VIA_AUTH_GATE')`
이 `00 §11`·`01 §10`의 `auth gate` 항목을 보존한다. `endpoint reach`와 `auth gate`가 서로를 대체하지 않음도 명시.

### 2.4 `01 §10 mart_archetype_summary`의 층화 반영 (확인 4)

`01 §10` 자체는 프리즈 문서라 바이트가 수정되지 않았고(목록은 `n` · `MPFED median` · `MPFED IQR` ·
`endpoint reach` · `modal prevalence` · `KWCAG summary` 그대로), 층화는 `A2`가 보충명세로 얹는다:

- `A2 §1.5.1a` 규칙 E-10 1항 — `01 §10`의 네 지표를 층별 병기 대상으로 **명시적으로 열거**.
- `A2 §6.3` P-C 산출물표 — `mart_archetype_summary 층화` 행이 `endpoint_via_auth_gate_rate` + 층별 `n`을 **컬럼으로 지정**.
- `A2 §6.3.1` I-9 — 위반 시 차단.
- `A2 §0` 7항 **EXC-2** — `01 §11`(`로그인 전까지만 가능 = AUTH_GATE_REACHED`)에서의 이탈이 예외 등재부에
  기재됐고, `보존되는 곳` 열이 `01 §10`·`00 §11` 지표의 유지 경로(E-8·E-9·E-10)를 지목한다.

즉 `01 §10`은 문면 그대로 두고, 그 지표를 **산출하는 방식**에 층화를 요구하는 구조다.
`A2 §0` 1항·2항(원본 우선, 원본의 값·정의·범위를 바꾸지 않는다)과 8항의 충돌해소 방향
(`00` > `01`, 충돌은 `A2`가 자기를 고쳐 해소)에 부합한다.

## 3. 판정

**`CLOSED`.**

원 지적은 "`00 §3`의 endpoint 정의와 `A2 §1.5.1`의 일반규칙이 상호모순이며, 그 모순이 두 archetype의
depth 계열 산출물을 구조적으로 무효화한다"는 것이었다. target `2025e566`에서:

| 원 지적의 요소 | 현재 상태 |
|---|---|
| `A2 §1.5.1`의 `AUTH_GATE_REACHED` 일반규칙이 `00 §3` 두 행을 덮음 | **해소** — `§1.5.1` 본문 자체가 두 archetype·해당 gate 종류를 예외로 뺀다 |
| 두 archetype의 `endpoint_reached`가 구조적으로 항상 0 | **해소** — 규범표가 `1`로 확정(`§1.5.1a`) |
| 두 archetype의 `MPFED`가 구조적으로 항상 NULL | **해소** — 정수(`m` 확정) |
| `00 §11` Depth 분포 불성립 | **해소 + 층화**(E-10, 파이프라인 차단 I-9) |
| `00 §7` ExcessDepth 기준선 불성립 | **해소 + 층화**, 정본 산식 불변 |
| `01 §10 mart_archetype_summary` 불성립 | **해소 + 층화 컬럼 지정**(§6.3) |
| 이탈의 예외 등재 부재 | **해소** — `§0` 7항 EXC-2 |

모순의 세 명제 중 명제 2가 소멸했고, 명제 3의 결론이 실제로 뒤집혔음을 원본 문면 대조로 확인했다.
분기 경계는 `00 §3` 문면과 1:1이며 `00`을 넓히지도 좁히지도 않는다. 확대 재발 경로는
규칙 E-6 · E-6a · §7 11항 · §6.3 가드 · §6.3.1 I-9의 다섯 자리에서 막혀 있다.
**추가로 필요한 것이 없다. 이 id는 닫힌다.**

## 4. 범위 밖 — 판정하지 않은 것

- `e-6a-accepts-misclassified-gate-kind-and-silently-flips-endpoint`(별도 open finding).
  **gate 종류 판별의 신뢰성**은 이 감사의 대상이 아니다. 이 감사는 `00 §3`의 endpoint 정의와
  `A2 §1.5.1` 계열이 **문서 간 상호모순인가**만 본다. 판별이 옳게 이뤄진다는 가정 하에 명세가
  정합적인가에 대한 답이 위 CLOSED이며, 판별 자체의 실패 가능성은 그 finding이 다룬다.
  두 판정은 독립이며, 이 CLOSED가 그 finding을 약화시키지 않는다.
- 그 밖의 target 전 범위 재감사(V2-C007에서 PASS).

## 5. 비차단 관찰 (새 finding으로 열지 않음)

`A2 §0` 5항은 "§6에 열거한 미존재 표·컬럼은 이 문서가 신설한 것이 아니라 `01`/`02`/`A1`이 이미
요구했으나 아직 물리적으로 없는 것"이며 "예외는 정확히 둘(EXC-3 · EXC-4)"이라고 적는다. 그런데
`§6.3`이 **컬럼**으로 지정한 `endpoint_via_auth_gate_rate`(규칙 E-10 3항)는 `01 §10`이 열거하지 않은,
`A2`가 층 크기 노출을 위해 요구하는 자리다(`superseded_from_web_target_id`도 같은 계열).
층화 자체는 새 분석 기준이 아니고(§7 14항 · E-10 2항) 기존 지표의 재산출이므로 **이 finding의 판정에
영향을 주지 않으며**, `01 §10`의 목록이 닫힌 스키마가 아니라 mart 내용의 예시 나열이라는 읽기도 가능하다.
다만 `§0` 5항의 "정확히 둘"이라는 **자기서술이 §6의 실제 열거와 완전히 일치하지는 않는다**는 점을
orchestrator reconciliation 참고사항으로 남긴다. **비차단, 새 finding 아님.**

---

**집계** — 이 초점 감사에서 새로 연 blocking finding **0건**.
`ssot-00-3-auth-gate-endpoint-contradicts-a2-1-5-1`(P1, `V2_SSOT_FROZEN`)은 **CLOSED**이며
다음 reconciliation에서 `open_blocking_total`에서 **차감되어야 한다**.
