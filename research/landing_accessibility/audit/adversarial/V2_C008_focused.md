# Landing Accessibility v2 — V2-C008 Adversarial Focused Adjudication

| 항목 | 값 |
|---|---|
| Auditor | adversarial (Claude), 전용 워크트리 `.agent_worktrees/landing_adversarial` · 브랜치 `audit/landing-adversarial` |
| Audit type | **FOCUSED CLASSIFICATION ADJUDICATION** — 시정 검증이 아니라 **분류 판정**이다. 전면 재감사가 아니다 |
| Phase / Gate | `P0_V2_REFREEZE` / `V2_SSOT_FROZEN` |
| Cycle | `V2-C008` |
| 판정 대상 finding | `rc-6-r1-same-authorization-local-reexecution-unbounded` (P2 · blocking · class `E001_V2`) |
| Exec SHA (문면 실측 기준) | `2025e5667686d42e832298f2dce77b0c7aa6bc07` (`agent/landing-v2-exec`) |
| Control SHA (원장 실측 기준) | `1d6cedb6aca6933a701275c7c8e14fd7d4628c73` (`control/landing-orchestrator`) |
| Base | `5a9015d1e95b15304aaf53a73efb475934610b82` (`origin/research/landing-accessibility-main`) |
| Pilot | `32460b87334a67f6a74823ac55f85ca80a9f8980` — READ_ONLY, 이 감사에서 미열람·미변경 |
| 직전 adversarial (내 것) | `cd0a4e62fc1e1582bd56678cec35d688edc695ed` (V2-C007 PASS) |
| 직전 ssot | `68a715bb250630553b292e96ee992d5880d31b48` |
| **판정** | **`ACCEPT_RECLASSIFY`** |
| 새 분류 | `ACCEPTED_BOUNDED_RESIDUAL_RISK` (blocking=false · counted_as_open=false) |
| 조건 | **6건. 전건 필수. 미충족 시 자동 실효(C-6)** |
| 신규 finding | 1건 (P2, **비차단** — 조건 C-2로 흡수) |

---

## 1. 판정

**`ACCEPT_RECLASSIFY`.** `rc-6-r1-same-authorization-local-reexecution-unbounded` 를
`ACCEPTED_BOUNDED_RESIDUAL_RISK` 로 재분류하고 `open_blocking_total` 에서 제외하는 것을
**독립 감사로서 승인한다.** 단, 아래 **조건 C-1 ~ C-6 전건을 이행할 것을 전제로** 승인하며,
어느 하나라도 정해진 시점에 미충족이면 **이 수용은 자동으로 실효되고 항목은 OPEN/blocking 으로 되돌아간다.**

이 판정 하나로 게이트가 열리지는 않는다 — 반영 후 `open_blocking_total` 은 **10 → 9** 이며
`00_SSOT_v2.0 §15` 의 `= 0` 은 여전히 미충족이다(§6).

---

## 2. 이 판정을 내릴 권한이 어디서 오는가 — 내가 만든 경로가 아니다

원장은 **이 id 에 한해 닫힘 경로 두 개를 미리 지정해 두었다.** 내가 새로 만든 것이 아니다.

`control@1d6cedb:control/cycles/V2_C006_orchestrator.json` `not_done[8]`:

> `rc-6-r1-same-authorization-local-reexecution-unbounded` — 등재만 했다.
> **저장소 밖 통제 설계 또는 감사의 명시적 잔여위험 수용**이 있어야 닫힌다.

`control@1d6cedb:control/state.json` 같은 항목 `why_counted`:

> … `E001_V2` 전에 저장소 밖 통제(예: 인가 시점 관측·외부 타임스탬프)로 다루거나,
> **감사가 잔여 위험 수용을 명시적으로 판정해야 닫힌다.**

그리고 오케스트레이터는 그 판정을 **스스로 내리기를 명시적으로 거부**했다
(`V2_C006_orchestrator.json` `r1_counting_note`):

> **그 판정을 오케스트레이터가 미리 내리지 않는다** — 지금은 둘 다 계상한다(fail-closed).
> 과소계상은 게이트를 뚫고 과대계상은 게이트를 늦출 뿐이므로 안전한 쪽을 택했다.
> `counted_as_open=false` 를 걸지 않은 것도 같은 이유다 — **제외에는 감사 판정이라는 근거가 있어야 한다.**

즉 이 자리는 **설계자가 자기 결함을 스스로 닫는 자리가 아니라, 독립 감사가 판정해야만 채워지는
빈칸으로 남겨져 있었다.** 그 빈칸을 채우는 것이 이 문서다. `05 §6` executor self-approval 금지는
그대로 지켜진다 — 등재한 쪽(A2 설계 담당·오케스트레이터)과 수용을 판정하는 쪽(이 감사)이 다르다.

---

## 3. `00_SSOT_v2.0 §15` 문면 판단 — 이것이 SSOT 의 의도인가

`2025e566:docs/v2/00_SSOT_v2.0.md §15 실행 종료점` 전문(13항)을 직접 읽었다.

```
본수집 전 반드시 다음을 충족한다.
- final web target frozen / representative task frozen / interaction archetype frozen
- KWCAG subset frozen / L0 collector validated / L1 scout/replay validated
- popup/obstruction detector validated / AI review cascade validated
- evidence manifest validated / HUMAN_FINAL queue policy validated
- E000_V2 smoke PASS / independent adversarial audit PASS / independent SSOT audit PASS
- open blocking P0/P1/P2 = 0
```

**판단: §15 는 "해소 가능한 결함이 남아 있지 않은가"를 묻는 착수 준비도 체크리스트다.
"원리적으로 해소 불가능한 잔여가 세상에 존재하지 않는가"를 묻는 절이 아니다.** 근거 넷.

1. **13항 전부가 도달 가능한 상태다.** frozen · validated · PASS 는 모두 유한 작업으로 도달한다.
   그 목록의 마지막 항만 "도달 불가능한 이상 상태"를 요구한다고 읽는 것은 목록의 성격과 어긋난다.
2. **불가능한 조건으로 읽으면 게이트가 영구히 닫힌다.** R-1 은 "커밋되지 않은 로컬 실행"이며,
   저장소만 보는 어떤 검사도 **일어나지 않은 커밋을 조사할 수 없다.** 이것은 RC-6 의 설계 결함이 아니라
   "committed artifact 만 감사한다"는 이 감사 체계 전체의 정의역이다. blocking 으로 유지하면
   `§15` 는 논리적으로 만족 불가능해지고, 본수집은 영원히 착수할 수 없다.
   그것은 SSOT 가 `§15` 를 **착수 조건**으로 쓴 목적과 정면으로 모순된다.
3. **정직한 등재를 처벌하는 유인구조가 된다.** R-1 은 A2 설계 담당이 **자기 설계를 실제 git 저장소로
   공격해 확인하고 자진 등재**한 항목이다(`state.json` `found_by`). 이것을 영구 blocking 으로 묶으면,
   같은 잔여를 **적지 않은** 설계는 게이트를 통과하고 **적은** 설계는 통과하지 못한다.
   `§15` 를 그렇게 읽으면 SSOT 는 은폐를 보상하게 된다.
4. **`§14` 와 함께 읽어야 한다.** SSOT 의 무결성 장치는 `§14 Claim Boundary` 다 — 무엇을 주장하고
   무엇을 주장하지 않는지를 명시하는 것. 원리적 잔여의 올바른 처리는 **게이트 봉쇄가 아니라 경계 명시**이며,
   그것이 조건 **C-5** 다.

**그래서 나는 `§15` 를 개정하지 않는다.** 개정할 권한도 없다(FROZEN). 내가 하는 것은
`§15` 가 세는 `open` 의 외연을 판정하는 것이다 — **직접 공격으로 환원 불가능성이 입증되고,
단일 차원으로 좁혀지고, 원장에 영구 기록되고, 운영 통제에 묶이고, 한계로 공표된 잔여는 `open` 이 아니라
`adjudicated` 다.** 그리고 그 판정 권한은 §2 에서 보인 대로 원장이 이 감사에 명시적으로 위임해 둔 것이다.

---

## 4. 잔여 위험의 실제 크기 — 실측

`2025e566` 문면과 `1d6cedb` 원장을 직접 읽어 확인했다. 재인용이 아니라 실측이다.

### 4.1 좁혀진 정도 — 사실이다

| 확인 항목 | 실측 위치 | 결과 |
|---|---|---|
| 재수집 자체가 예외 경로 | `A2:1162` `MAX_RECOLLECTION_RUNS_PER_WEB_TARGET = 1 (기본값)` | **확인.** web target 당 정본에 쓸 수 있는 재수집 run 은 기본 1건. 상한 초과분은 정본 지표 제외 + 건수 보고(RC-1·RC-5) |
| 비인가 id 생성 봉쇄 | `A2:1348-1360` 유도식 `f` · `A2:1370` A-6 | **확인.** 유효 id 는 `f` 의 상(image)뿐이고 `f` 의 입력에 control 인가 커밋이 들어간다. 인가 전에는 통과하는 id 를 계산할 수 없다 |
| 이중 제출 봉쇄 | `A2:1368` A-7 | **확인.** 인가 1 ↔ 실행 1 ↔ run 1 의 1:1:1 |
| id 집합 상한 | `A2:1372` A-8 | **확인.** control 이 executor 와 **독립적으로** 세는 `E` 로 상한. 인가받고 숨기면 원장이 아니라 control 쪽 수와 어긋나 잡힌다 |
| 판정 결과가 중단조건이 아님 | `A2:1203-1210` RC-2 중단규칙 | **확인.** 중단조건 2 는 `expected_evidence` 산출 여부만 읽는다. `verdict_state` 는 어느 검사에도 입력되지 않는다 |

**나는 이 세 갈래(비인가 id 생성 · 인가받고 은닉 · 이중 제출)를 V2-C006 에서 직접 공격해
실제로 봉쇄됨을 확인했다**(`7674375` §4). 이번 판정은 그 실측 위에 선다.

남는 차원은 **정확히 하나** — `인가 1건당 몇 번 돌렸는가`.

### 4.2 정직하게 등재됐다 — 세 곳 전건 실측

| # | 위치 | 내용 |
|---|---|---|
| 1 | `A2:1400` 잔여 위험표 **R-1** 행 | `저장소 내부 검사로는 배제 불가`를 명시 |
| 2 | `A2:1390` 닫힘 논거표 | **`닫히지 않는다`** 로 적고, `V2-C005` 판의 과장된 단언(`은닉은 정본 선택에 아무 이득을 주지 못한다`)을 **철회**함을 명기 |
| 3 | `A2:2353` 실패주입 **I-41** | 기대결과를 **`차단되지 않는다`** 로 적었다. 사유까지 적혀 있다 — *"가드가 이것을 막는다고 주장하지 않기 위해서다"* |

추가로 `A2:2308` · `A2:2406`(규칙 13 요약)에도 같은 경계가 반복된다.
**닫힌 것처럼 기록한 자리가 한 곳도 없다.** 이것이 수용의 최소 전제이며, 충족됐다.

### 4.3 탐지·억제층은 실재한다 (닫는 층이 아니라 옮기는 층)

- `RC-5`(`A2:1252-1272`) — `03 Phase 5` 에 **재수집 전후 값 병기**(최초 run 만으로 계산한 값 / RC-3 정본 run 으로 계산한 값), 정본 교체 건수, 상한 초과 run 수, 미선언 run 수(**0이어야**), 중단 사유 분포, RC-7 양방향 대조 4수치, `disposition` 9값 분포, A-1~A-8 통과 여부, **실행 인가 대조 3수(`E` ↔ `EXECUTION` ↔ 제출 run, 세 수가 같아야)**.
- `RC-7`(`A2:1414-1420`) — 원장→run · run→원장 · **인가→원장** 3방향 + `ledger_seq`/`attempt_index`/`execution_index` 조밀성.
- `05 §6` executor self-approval 금지 · `MAX_UNAUDITED_EXEC_CYCLES = 1` · 두 독립 감사 병행.
- R-1 은 **재수집이 실제로 실행되기 전에는 행사될 수 없다** — 즉 `E001_V2` 안쪽 사건이며,
  그 시점에는 위 층이 전부 작동한다.

### 4.4 그러나 — 유일한 실질 완화층이 **코드로 존재하지 않는다**

`A2:1400` R-1 행의 `무엇에 기대는가` 열은 **`수집 도구와 수집자`** 다.
그 `수집 도구`를 확인했다:

- `claude-b/e001-runner` @ `2025e56` — **exec tip 과 동일**. 러너 코드 없음.
- `research/landing_accessibility/` 아래 수집 러너 산출물 없음.
- `2025e566:docs/v2/02_COLLECTION_MEASUREMENT_SPEC_v2.0.md` — 단일 실행 강제·재실행 거부에 관한 문면 없음(`재실행`·`한 번만`·`1회`·`K회` grep 0건).

**즉 R-1 의 유일한 실질 완화층은 현재 vaporware 다.** 이것이 조건 **C-3** 의 근거이며,
내가 이 수용을 **무조건 승인하지 않는 이유**다. 나는 V2-C006 §4.3 말미에서 이미 같은 요구를 적었고,
이번에 그것이 아직 이행되지 않았음을 실측으로 확인했다.

---

## 5. 신규 발견 — 수용 경계가 실제보다 좁게 그어져 있다 (P2, 비차단, 조건 C-2 로 흡수)

**id**: `rc-6-initial-run-anchor-exemption-rationale-is-false-under-r1-threat-model`

`A2:1378` (RC-6 절, 잔여 위험표 바로 위):

> 이 규칙은 재수집 run에만 적용된다. **최초 run은 앵커를 요구하지 않는다 — 선택할 대상이 없기 때문이다.**

**뒷문장이 R-1 위협모델 아래에서 거짓이다.**

"선택할 대상이 없다"는 **커밋된 산출물의 세계**에서만 참이다. R-1 이 지적하는 선택은
**커밋되지 않은 로컬 run 사이의 선택**이며, 최초 run 은 그 선택에 **완전히 열려 있다** —
게다가 앵커 자체가 없으므로 A-1~A-8 어느 것도 적용되지 않는다. 실측:

- `A1:549` — `evidence_run_id` → `evidence/<run_id>`. 최초 run 의 id 에 유도식 제약 없음.
- `A1:577` — `observation_id = hash(web_target_id, evidence_run_id, …)`. id 는 자유값.
- RC-6 은 재수집 전용(`A2:1378`). 최초 run 에 대응하는 인가·유도·대조 검사 **0건**.

즉 최초 수집을 로컬에서 K회 돌리고 하나만 커밋하는 것은 저장소상 단일 run 과 **구분 불가능**하며,
어떤 잔여로도 등재돼 있지 않다.

**이것이 R-1 판정에 직접 하중을 준다.** 4.3 에서 본 대로 R-1 수용이 기대는 최상위 탐지층은
RC-5 의 **재수집 전후 병기**인데, 그 `전` 값의 기준선이 바로 최초 run 이다.
최초 run 자체가 선별될 수 있다면 **그 기준선이 오염되고, R-1 을 탐지하는 층 자체가 약해진다.**

**이것은 `V2-C005` 에서 철회된 `A2:1334` 단언(`은닉은 정본 선택에 아무 이득을 주지 못한다`)과
같은 종류의 범주 오류다** — 커밋된 것에 대해 참인 문장을 커밋되지 않은 것까지 덮는 것처럼 적은 것.
같은 절 안에서 같은 오류가 한 번 더 남아 있다.

**분류: P2 · 비차단.** 새 탈출로를 *만드는* 문장이 아니라 이미 존재하는 노출을 *과소기술*하는 문장이며,
문면 수정으로 해소된다. 별건 blocking 으로 세우지 않고 **조건 C-2 로 흡수한다** —
즉 이 수용의 경계를 실제 크기로 다시 긋는 것을 수용의 조건으로 삼는다.
**좁은 경계로 수용해 주면, 내가 실제보다 작은 잔여를 인증하는 것이 되기 때문이다.**

---

## 6. 왜 (b) KEEP_BLOCKING 도 아니고 (c) 다른 방안도 아닌가

**(b) blocking 유지** — 기각한다. §3-2 대로 `§15` 를 만족 불가능하게 만들고 본수집을 영구 봉쇄한다.
게다가 blocking 유지는 **아무것도 개선하지 않는다.** blocking 표시는 "고칠 것이 있다"는 신호인데,
고칠 대상이 저장소 안에 없다. 위험은 그대로 두고 게이트만 잠그는 것은 안전이 아니라 마비다.

**(c) 대안 검토** — 다음을 검토하고 각각 기각했다.

| 대안 | 기각 사유 |
|---|---|
| 외부 timestamp/seal(RFC 3161 · OpenTimestamps)을 필수화 | 이미 `A2:1382` 가 **허용되는 보강**으로 열어 뒀다. 그러나 seal 은 *커밋된 것*에 시각을 부여할 뿐 **버려진 로컬 run 을 드러내지 못한다.** R-1 을 조금도 좁히지 않는다 |
| `MAX_RECOLLECTION_RUNS_PER_WEB_TARGET = 0`(재수집 전면 금지) | R-1 은 사라지지만 `UNDETERMINED` 의 유일한 복구 경로가 사라져 측정 품질이 되레 악화된다. 그리고 §5 대로 **최초 run 노출은 그대로 남는다** — 문제를 옮길 뿐이다 |
| 전 수집을 CI/원격 러너에서만 실행 | 실질적으로 옳은 방향이고 **조건 C-3 이 그 축소판이다.** 그러나 이것도 R-1 을 *닫지* 못한다 — 러너를 로컬에서 K회 호출하는 것을 러너 자신은 막을 수 없고, 결국 `수집자` 신뢰로 되돌아온다. 완전판(격리 실행환경 강제)은 이 연구 규모에 비해 과잉이며 `§15` 어디에도 요구돼 있지 않다 |
| 잔여를 non-blocking finding 으로 강등만 하고 수용 판정은 안 함 | **가장 나쁜 선택.** 기록은 남되 아무 조건도 붙지 않아 C-3/C-5 가 사라진다. "조용히 약화"이며 내가 §3-3 에서 비판한 은폐 유인과 같은 자리에 선다 |

**(a) 를 택하되 조건부로 택한다** — 무조건 수용은 잔여를 지우는 것이고, 조건부 수용은
**잔여를 blocking 원장에서 운영 통제 원장으로 옮기는 것**이다. 후자가 이 위험의 실제 성격에 맞다.

---

## 7. 수용 조건 — 전건 필수

### C-1 · 원장 영구 기록 (즉시 · `V2_SSOT_FROZEN` 선언 이전)

`control/state.json` 의 해당 항목을 **삭제하지 않고** 다음으로 전이한다.

```
state:            ACCEPTED_BOUNDED_RESIDUAL_RISK
blocking:         false
counted_as_open:  false
accepted_by:      adversarial audit V2-C008 (audit/landing-adversarial, 이 커밋 SHA)
accepted_at:      <ISO8601>
basis:            V2_C006_orchestrator.json not_done[8] · state.json why_counted
                  ("감사의 명시적 잔여위험 수용")이 지정한 닫힘 경로
scope:            §7 C-2 가 정하는 확대 경계
conditions:       [C-1..C-6]
lapse_rule:       C-6
```

- `ACCEPTED_BOUNDED_RESIDUAL_RISK` 는 원장에 **새로 도입되는 상태값**이다
  (현행 어휘: OPEN · CLOSED · CLOSED_VERIFIED · CLOSED_IN_SPEC · OPEN_PARTIAL ·
  REMEDIATION_CLAIMED_PENDING_AUDIT · WITHDRAWN_*). 상태값 정의를 원장에 함께 적는다:
  **"환원 불가능성이 감사에 의해 입증·수용됐고, 운영 통제와 공표 의무에 묶인 잔여.
  CLOSED 가 아니다 — 결함이 해소된 것이 아니라 성격이 재분류된 것이다."**
- 이후 **모든** `open_blocking_total` 재계산에서 이 항목은 **"명시적으로 제외된 한 줄"로 표시**한다.
  합계에서 조용히 사라지는 형태(항목 삭제·누락)는 금지한다.
  `promote_landing_main.sh` `[DEBT_RECOMPUTE]` 블록도 이 상태값을 인식하도록 갱신하고,
  **제외 건수를 별도 출력**한다.

### C-2 · 수용 경계를 실제 크기로 (즉시 · `V2_SSOT_FROZEN` 선언 이전)

이 수용이 덮는 것은 R-1 이라는 개별 항목이 아니라 **위험 부류**다:

> **선별적 로컬 재실행** — 수집을 로컬에서 K회 실행한 뒤 선호하는 1회만 커밋하는 것.
> **재수집 run(RC-6/R-1)과 최초 E001 run 양쪽에 적용된다.**

따라서 `A2:1378` 을 시정한다. 최초 run 에 앵커가 없는 참된 이유는
**"앵커를 걸 선행 커밋 run 이 없기 때문"** 이지 **"선택할 대상이 없기 때문"이 아니다.**
후자는 §5 대로 R-1 위협모델 아래에서 거짓이며, 철회된 `A2:1334` 와 같은 범주 오류다.
`A2 §1.11.2` 잔여 위험표에 **최초 run 노출을 R-1 의 적용 범위로 명기**한다
(새 잔여 번호를 만들든 R-1 행을 확장하든 무방하나, **닫힌 것처럼 적지 않는다**).

### C-3 · 운영 통제 — 코드 (`E001_V2` **실행 이전**, `E001_V2` 게이트 선행조건)

§4.4 에서 실측한 대로 유일한 실질 완화층이 존재하지 않는다. `E001_V2` 착수 전에 다음을 구현·검증한다.

1. **실행 잠금.** 러너는 인가 튜플 `(ledger_record_sha256, execution_index)` 마다 **영속 lock** 을 획득하고,
   같은 튜플에 대한 **2회차 실행을 거부**한다. lock 은 프로세스 종료로 해제되지 않는다.
2. **단일 호출 내 커밋·push.** evidence tree 생성 → 원장 `EXECUTION`/`DISPOSITION` 기록 → commit → push 가
   **하나의 비대화형 호출** 안에서 끝난다. *결과를 본 뒤 커밋 여부를 결정할 인간의 틈*을 프로세스 수준에서 없앤다.
3. **최초 run 에도 동일 적용.** 최초 E001 수집도 `(web_target_id, collection_wave)` 키로 같은 lock 을 건다 (C-2 귀결).
4. **실행 환경 기록.** run manifest 에 `execution_environment` 를 기계 기록한다 —
   host · wall-clock start/end · tool version · lock id · process id. 이는 `preregistered_at` 같은
   자기신고가 아니라 **러너가 쓰는 값**이며, RC-5 대조에 자기신고 아닌 시각 기록을 하나 공급한다.

**이것은 R-1 을 닫지 않는다.** 러너를 로컬에서 여러 번 호출하는 것을 러너가 막을 수는 없다.
닫는 것이 아니라 **인간이 조작할 수 있는 틈을 프로세스 수준에서 좁히는 것**이며,
그것이 정확히 원장이 말한 `저장소 밖 통제` 다. `E000_V2` smoke 에서 두 감사가 각각 검증한다.

### C-4 · `E001_V2` 수집 시 실제 준수 검증 (`E001_V2` 종료 시)

`RC-5` 보고에 다음을 **추가로** 싣고 두 감사가 각각 대조한다.

| # | 검증 항목 | 통과 기준 |
|---|---|---|
| i | 인가 대조 3수 — control `E` ↔ 원장 `EXECUTION` ↔ 제출 evidence run | **세 수가 같다** (기존 RC-5 요구, 재확인) |
| ii | 러너 lock 기록 ↔ `EXECUTION` 레코드 | **1:1**. lock 은 있는데 `EXECUTION` 이 없으면 곧 은닉된 실행이다 |
| iii | **수집자 귀속 선언** — "폐기된 로컬 run 이 존재하지 않는다"를 수집 담당이 원장에 서명 기입하고 control 이 countersign | 전 web target · 전 인가 건에 대해 존재 |
| iv | `execution_environment` wall-clock 이 evidence 타임스탬프·commit 순서와 모순되지 않는다 | 모순 0건 |

**(iii) 은 증명이 아니다.** 서명이 거짓일 수 있다. 그러나 그것은
**탐지 불가능한 행위를 기록된 허위진술로 전환**한다 — 책임 소재가 달라지며, 이것이
`저장소 밖 통제`가 실제로 할 수 있는 일의 전부다. 증명으로 포장하지 않는다.

### C-5 · 한계 공표 (문서: 즉시 / 최종 산출물: 보고 시점)

**수용이 은폐가 되지 않게 하는 조건이며, 내가 이 수용을 승인하는 근거의 절반이다.**

1. `00_SSOT_v2.0 §14 Claim Boundary` 또는 `03 Phase 5` 에 다음 취지의 한계 절을 둔다:
   > 정본 run 선택의 검증은 **커밋된 산출물에 한정된다.** 수집을 로컬에서 여러 번 실행한 뒤
   > 하나만 커밋하는 경로는 저장소 측 어떤 검사로도 배제되지 않으며, 본 연구는 이에 대해
   > 프로세스 통제(단일 실행 잠금·단일 호출 커밋)와 역할 분리(수집자 ≠ 인가자 ≠ 감사자),
   > 그리고 재수집 전후 값 병기 보고에 의존한다. 이 잔여는 **독립 감사가 검토·수용한 것**이며
   > 해소된 것이 아니다.
2. **논문/최종 보고서의 limitation 절에 같은 취지를 싣는다.**
   감사 수준에서 수용됐으나 서술에서 빠진 잔여는 **정직한 등재를 은폐로 되돌리는 것**이며,
   내가 §3-3 에서 수용의 근거로 삼은 것과 정반대가 된다.
   `§14` 는 FROZEN 이므로 문면 추가가 SSOT 개정에 해당한다면 `EXC` 절차를 따른다 —
   **그 절차 부담을 이유로 이 조건을 생략할 수는 없다.**

### C-6 · 실효 규칙과 선례 제한

1. **실효.** C-1 · C-2 · C-5-①(문서) 미충족 상태로 `V2_SSOT_FROZEN` 을 선언할 수 없다.
   C-3 · C-4 · C-5-②(산출물) 미충족 상태로 `E001_V2` 를 **실행·종료**할 수 없다.
   어느 하나라도 정해진 시점에 미충족이면 **새 감사 finding 없이** 이 수용은 실효되고
   항목은 `OPEN` / `blocking=true` / `counted_as_open=true` 로 자동 복귀한다.
2. **선례 아님.** 이 판정은 **다른 어떤 blocking finding 도** "환원 불가능"을 선언하는 것만으로
   수용될 수 있다는 뜻이 아니다. 다음 셋을 **전부** 만족하는 항목만 이 경로를 쓸 수 있다:
   (i) **직접 공격으로** 환원 불가능성이 입증됐다 (주장이 아니라 재현),
   (ii) 잔여가 **단일하게 명명된 차원**으로 좁혀졌고 나머지 갈래는 실제로 봉쇄됐다,
   (iii) 감사가 지적하기 **전에** 설계자가 스스로 정직하게 등재했다.
   R-1 은 셋을 전부 만족한다. `e-6a-accepts-misclassified-gate-kind-…`(엔진 측 방어는 있으나
   A2 문면 미시정) 와 `ned-ied-path-minimality-not-operationalized`(미착수) 는 **만족하지 않는다** —
   이 판정을 근거로 그 둘을 닫는 것을 **명시적으로 금지한다.**

---

## 8. 원장 반영 예상값

| 항목 | 현재 (`1d6cedb` `V2_C007_RECONCILIATION.json`) | 이 판정 반영 시 |
|---|---|---|
| `open_blocking_total` | 10 | **9** |
| `orchestrator_registered.open_blocking` | 3 | **2** |
| `e001_v2_blocking_class_ids` | 3건 | **2건** (`ned-ied-path-minimality-…` · `e-6a-accepts-misclassified-…`) |
| `v2_ssot_frozen_blocking_class_count` | 1 | 1 (무변) |
| `v1_inherited` | 6 | 6 (무변) |
| `accepted_bounded_residual_risk` (신설 카운터) | — | **1** (명시적 제외 표시) |

**`00_SSOT_v2.0 §15` 는 여전히 미충족(9 ≠ 0)이며 `V2_SSOT_FROZEN` 은 `NOT_ACHIEVED` 다.**
promotion · P-A · `E001_V2` 는 전부 금지 상태를 유지한다.
**이 판정을 게이트 통과로 읽어서는 안 된다.**

---

## 9. 이 감사가 하지 않은 것

- 전면 재감사를 하지 않았다. `V2-C007` PASS 이후 exec/control tip 재감사는 이 배정 범위 밖이다.
- **실제 웹사이트에 접속하지 않았다.**
- Pilot(`32460b8`)을 열람·변경하지 않았다.
- 다른 워크트리를 쓰지 않았다(읽기 전용 `git show`/`git grep` 만 사용).
- 남은 blocking 9건 중 R-1 외 8건에 대해 어떤 판정도 하지 않았다. 특히 `C-6-2` 대로
  `e-6a-accepts-misclassified-…` 와 `ned-ied-path-minimality-…` 는 이 경로로 닫히지 않는다.
- 미추적 draft `audit/adversarial/V2_C004.{md,json}` 은 건드리지 않았다(이전 중단 세션 잔재).
