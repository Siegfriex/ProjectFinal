# Lane 2 — DIAG-PILOT-001 12건 HISTORICAL_METHOD_ASSURANCE 동결 인벤토리

**작성** A 평면 문서화 lane · **기준 SHA** `control/landing-orchestrator @ ede241321b5b8599161d95a59bc38034590283e8`
**작성 시각 기준일** 2026-08-28

---

## 1. 동결 선언

Director 가 2026-08-28, 8-phase → 3-STEP 축약 지시에서 다음을 명령했다 (원문 인용):

> "기존 DIAG-PILOT-001 12건은 더 이상 실행하지 않는다. `HISTORICAL_METHOD_ASSURANCE` 로 freeze 한다.
> 그동안 확보한 firewall / exactly-once / scope / guard / fixture / C assurance 는 보존한다."
>
> "기존 E001_FULL 59건은 계속 SUSPENDED 다. 12 PASS → 59 GO 같은 연결은 폐기한다."

이 지시는 `research/landing_accessibility/control/v3/V3_PHASE_RESTRUCTURE.md` (작업 트리, `git status --short` 상
`??` — 아직 `ede2413`에 커밋되지 않은 워킹트리 산출물) 10행에 다음으로 반영돼 있다:

```
| P1 `Q12_METHOD_QUALIFICATION` | 취소 — 12건 미실행. `HISTORICAL_METHOD_ASSURANCE` 동결 |
```

**사실관계 — 12건은 한 번도 실행되지 않았다.** A 자신이 발행한 `T-A-PIVOT-PRESERVE-001` 티켓
(`research/landing_accessibility/control/bus_mirror_a/tickets/T-A-PIVOT-PRESERVE-001.json`,
`created_at: 2026-08-28T01:48:11+09:00`)의 `current_state_frozen` 블록이 다음을 명시한다:

```
"REAL_TARGET": "NO-GO"
"E001_FULL": "SUSPENDED — fail-closed"
"V2 구동기": "부재 — launch 경로 없음"
"REAL_TARGET 접속 흔적": "0건"
```

같은 티켓의 `nothing_to_undo` 필드: *"아무것도 실행되지 않은 상태에서 멈췄다. 피벗이 무엇이든
되돌릴 것이 없다."*

**측정 명령과 출력 (REAL 접속 흔적 부재의 독립 확인):**

```
$ find research/landing_accessibility -type d -iname "*batch*"
(결과 없음 — 0줄)
```

**양성대조 (같은 grep 이 실제로 무언가를 찾아낼 수 있다는 증거):**

```
$ grep -rl "DIAG-PILOT-001" research/landing_accessibility/control/ | wc -l
5
```
→ `DIAGNOSTIC_PILOT_CONTRACT.md`, `V2_DIAGNOSTIC_RELEASE.json`,
`bus_mirror_a/acks/T-B-PILOT-INT-001.A.json`, `bus_mirror_a/tickets/T-A-PILOT-EXEC-001.json`,
`bus_mirror_a/tickets/T-A-PHASE-V2-DIAG.json`. 즉 **계획·릴리스·티켓 문서는 존재하지만 실행 산출물
디렉터리(batch, evidence)는 0건** — 부재가 검색 실패가 아니라 실측이다.

**이것은 실패 서술이 아니다.** 경로가 8-phase에서 3-STEP으로 재구조화되면서 `Q12_METHOD_QUALIFICATION`
phase 자체가 불필요해진 것이며, 12건이 시도됐다가 좌절된 것이 아니다.

---

## 2. 보존 자산 인벤토리

**구조적 선행 사실 (중요):** A의 정본 브랜치 `control/landing-orchestrator`의 exact HEAD
`ede2413`은 실제 소스 코드(firewall/scope/guard/exactly-once 구현)를 **전혀 포함하지 않는다** —
문서·티켓·bus mirror만 담고 있다.

```
$ git ls-tree -r ede241321b5b8599161d95a59bc38034590283e8 --name-only | grep -c "^research/landing_accessibility/src/"
0
```

양성대조 (동일 명령이 B 브랜치에서는 hit함):

```
$ git ls-tree -r 01041bc213a2e61f6cb224e469087d9a11324349 --name-only | grep -c "^research/landing_accessibility/src/"
5개 이상 (engine/firewall.py, e001_runner/{batch,ledger,layer_firewall}.py 등 포함)
```

즉 firewall/scope/exactly-once의 **실제 구현은 A에 merge된 적이 없고**, B의 세 브랜치
(`claude-b/diag-pilot-integration @ 01041bc`, `claude-b/w1-guard-wiring @ e2bb63e`,
`claude-b/w2-rf-detector @ b28aaa5`)에만 존재한다. 이 세 SHA는 서로 다른 위치에서도 **완전히
동일한 scope 목록**을 낸다 (아래 표에서 반복 확인 — 코드 드리프트 없음). 매니페스트만
`control/pilot-manifest @ 54a0c7a4`을 거쳐 A의 `ede2413`에 실제로 커밋돼 있다(§2 자산 7 참조).

| # | 자산 | exact SHA | 경로 | 확인 방법 | 측정값 |
|---|---|---|---|---|---|
| 1 | firewall (2층) | `01041bc2`(동일 결과: `e2bb63e`,`b28aaa5c`) | `research/landing_accessibility/src/landing_accessibility/engine/firewall.py` (1층/engine)<br>`.../e001_runner/layer_firewall.py` (2층/batch) | `git show <SHA>:<path> \| grep -n ExecutionScope` (engine) / `grep -n "E000_FAST\|E001_FULL\|V2_DIAGNOSTIC"` (batch) | engine 층: `ExecutionScope` 참조 27곳, 3개 scope(E000_FAST/E001_FULL/V2_DIAGNOSTIC) 전부 인지.<br>batch 층: `BATCH_LAYER_REAL_SCOPES` 딕셔너리에 `E000_FAST`·`E001_FULL` 둘만 등재, **`V2_DIAGNOSTIC` 부재** — 4개 SHA(`01041bc2`,`e2bb63e`,`b28aaa5c`,`54a0c7a4`) 전부 동일. 이 층은 "여기 없는 scope는 fail-closed"로 설계돼 있음(`layer_firewall.py` 146행 `if scope_value not in BATCH_LAYER_REAL_SCOPES`) — batch 층은 V2_DIAGNOSTIC을 몰라서 열지 못하는 게 아니라 알려진 두 값 외엔 전부 막는 설계다. |
| 2 | exactly-once | `01041bc2` | `.../e001_runner/ledger.py` (`BatchLedger`, exclusive-create append) · `.../e001_runner/batch.py` (`_idempotency_components`, `idempotency_key` 조립) · `tests/test_w1_exactly_once.py` | `git grep -ln "idempotency\|exactly_once\|duplicate" 01041bc2 -- '*.py'` → 17개 파일 hit (양성대조: 동일 grep이 `refcohort` 등 무관 파일도 hit해 grep 자체가 죽지 않았음을 확인). `git show 01041bc2:.../batch.py \| grep -c "idempotency\|duplicate"` → 17건. | `idempotency_key = ticket_id+run_id+target_id+collector_sha+protocol_sha`(batch.py 119행 주석). `BatchLedger.append`는 파일 **배타적 생성**을 가정(중복 시도는 `suppressed_ledger.jsonl`에 기록, `duplicate_suppressed_reason` 필드). `tests/test_w1_exactly_once.py` 테스트 함수 12개(아래 자산 4와 중복 목록). |
| 3 | scope (`ExecutionScope` enum) | `01041bc2` | `.../engine/firewall.py:89` | `git grep -n "class ExecutionScope" 01041bc2 -- '*.py'` → 1곳(`firewall.py:89`). 멤버는 `sed -n '89,113p'`로 직접 확인. | `class ExecutionScope(StrEnum)`, 멤버 3개: `E000_FAST="E000_FAST"`, `E001_FULL="E001_FULL"`, `V2_DIAGNOSTIC="V2_DIAGNOSTIC"` (112~114행 부근). `DIAGNOSTIC_PILOT_MANIFEST_SHA256` 상수(244~246행)가 이 scope 전용 바인딩값을 하드코딩. |
| 4 | guard (W1 guard wiring) | `e2bb63e`(동일 목록: `01041bc2`) | `tests/test_w1_guard_wiring.py`<br>`tests/test_w1_task_wiring.py`<br>`tests/test_w1_exactly_once.py`<br>`tests/test_w1_v2_diagnostic_scope.py` | `git ls-tree -r e2bb63e --name-only \| grep -E "tests/test_w1_.*\.py$"` → 4개 파일. 각 파일 `git show <SHA>:<path> \| grep -c "^def test_"`. | `test_w1_guard_wiring.py`=28개, `test_w1_v2_diagnostic_scope.py`=21개, `test_w1_exactly_once.py`=12개, `test_w1_task_wiring.py`=4개. **합계 65개 테스트 함수**, 4개 SHA 모두 파일 목록 동일(코드 드리프트 없음). |
| 5 | fixture (`tests/fixtures/`, V2_DIAGNOSTIC 관련) | `01041bc2` | `tests/fixtures/w1_diagnostic_pilot_manifest_v2.json` | `git ls-tree -r 01041bc2 --name-only \| grep "^tests/fixtures/"` → 2개 파일(`e000_plan_snapshot.json`, `w1_diagnostic_pilot_manifest_v2.json`) 중 1개가 diagnostic 관련. 양성대조: `research/landing_accessibility/fixtures/`(별도 위치, HTML fixture 46개)는 grep이 정상 작동함을 보여주는 대조군 — `git ls-tree -r 01041bc2 --name-only \| grep -c "fixtures/"` → 48. | `tests/fixtures/w1_diagnostic_pilot_manifest_v2.json` 1개 파일이 V2_DIAGNOSTIC scope 테스트 하네스의 fixture manifest 역할. |
| 6 | C assurance (12건 관련) | A 자체 SHA `ede2413` (working tree와 diff 0줄 확인) | `research/landing_accessibility/control/bus_mirror_a/acks/C-COMPLETION-001706.A.json`<br>`.../T-B-PILOT-INT-002.A.json` | `cat <path>` 직접 열람 (A의 control 트리 안, 네트워크 접속 없이 로컬 파일). | `C-COMPLETION-001706.A.json`: "manifest v2 sha256 78f2e32a… MATCH · sampling 12/12 MATCH · order_key 12/12 · selection_trace 7/7 · evidence class 12/12". `T-B-PILOT-INT-002.A.json`: A가 `merge-base`로 독립 확인 — "firewall.py에 V2_DIAGNOSTIC 0건(gate 3 미충족 확인)" (이는 gate-3 구현 완료 **이전** 시점의 중간 확인 기록이며, 이후 `01041bc2` 통합에서 gate 3이 충족돼 3개 scope 전부 등재됨 — 두 기록은 서로 다른 시점을 가리키므로 모순 아님). |
| 7 | manifest | `control/pilot-manifest @ 54a0c7a4` (A의 `ede2413`에도 동일 blob으로 커밋돼 있음) | `research/landing_accessibility/control/pilot/DIAGNOSTIC_PILOT_MANIFEST.json` | `sha256sum <path>`(워킹트리) 및 `git show 54a0c7a4:<path> \| sha256sum`(git blob) 대조. `git rev-parse ede2413:<path>`와 `git rev-parse 54a0c7a4:<path>`로 blob 해시 자체를 직접 비교. `git diff ede2413 -- <path>` (0줄 = 동일). | 재계산 sha256 = `78f2e32a8fc1e732e485debc41ccdec618a63a832813de83e19a2cf50b51b799` (64 hex, 지시받은 값과 **완전 일치**). 워킹트리·`54a0c7a4` git blob·`ede2413` git blob 세 곳의 blob object hash가 전부 `c4241832f8025319811c2bccfbd1c867cecfbf3e`로 동일. `firewall.py`의 `DIAGNOSTIC_PILOT_MANIFEST_SHA256` 상수(자산 3)와도 문자열 동일. `DIAGNOSTIC_PILOT_MANIFEST.sha256.json`이 부기: v1(`4d3209ca…`)을 v2가 대체(labeler 유래 degenerate 집합 재현 불가 시정), `n=12`, `frozen_before_run: true`. |
| 8 | 릴리스 문서 | A 자체 SHA `ede2413` | `research/landing_accessibility/control/V2_DIAGNOSTIC_RELEASE.json`<br>`research/landing_accessibility/control/E001_RELEASE.json` | `cat <path>`; `git diff ede2413 -- <path>` (0줄 = 워킹트리와 커밋본 동일 확인). | `V2_DIAGNOSTIC_RELEASE.json`: `"status": "RELEASED"`, `"released_at": "2026-08-28T00:48:11+09:00"`, `"target_count": 12`, `"run_id": "DIAG-PILOT-001"`. **주의** — 이 문서의 `status` 필드는 아직 문자 그대로 `RELEASED`이며 Director의 이후 freeze 지시(HISTORICAL_METHOD_ASSURANCE)를 반영해 수정된 바 없다(§5 참조 — 본 lane은 파일 수정 금지 하에 작업했다). `E001_RELEASE.json`: `"status": "SUSPENDED"`, `"suspended_at": "2026-08-28T00:47:26+09:00"`, `"e001_allowed": true`이나 `status != RELEASED`이므로 `evaluate_execution_scope`가 fail-closed로 거부(`suspension_effect` 필드 원문). |

---

## 3. 폐기되는 연결

- **"12 PASS → 59 GO" 연결은 폐기된다.** `V3_PHASE_RESTRUCTURE.md` 말미: *"`E001_FULL` 59
  SUSPENDED 유지. **12 PASS → 59 GO 연결 폐기.**"* 12건이 실행조차 되지 않았으므로 애초에
  "PASS"라는 사건 자체가 존재하지 않는다 — 폐기되는 것은 가상의 인과관계 규칙이다.
- **`E001_RELEASE.json`은 계속 `SUSPENDED`다.** §2 자산 8에서 재확인: `status: "SUSPENDED"`,
  `suspended_at: 2026-08-28T00:47:26+09:00`. 이 상태는 이번 lane 작업 중 변경하지 않았다(파일
  미수정 확인 — `git diff ede2413 -- E001_RELEASE.json` = 0줄).
- `E001_RELEASE.json`이 직접 남긴 교훈(`suspension_reason` 필드 원문)이 이 폐기 결정의 근거와
  같은 계열이다: *"deadline은 코드가 검사하지 않는다 — firewall.py에 deadline 언급 0건(대조군:
  status 5건). 즉 마감은 문서상 표기일 뿐 강제되지 않았다."* — 문서상의 연결(12→59, deadline)은
  런타임이 강제하지 않으므로 사람이 명시적으로 폐기 선언을 해야 한다는 것이 반복 확인된 패턴이다.

---

## 4. V3로 승계되는 것 / 승계 불가한 것

**재사용 가능 (V3 MAIN50 경로에서):**

| 자산 | 승계 형태 |
|---|---|
| `ExecutionScope` enum 패턴 · engine/batch 2층 firewall 구조 | 코드 아키텍처로서 재사용 가능. V3가 새 scope(예: `MAIN50_*`)를 추가할 때 같은 enum에 값만 늘리고, batch 층에도 동일하게 `BATCH_LAYER_REAL_SCOPES`에 등재해야 한다는 **패턴**(그리고 "등재 누락 시 fail-closed"라는 방어 설계)이 승계 대상. |
| exactly-once 메커니즘 (`idempotency_key` 조립 규칙, `BatchLedger` 배타적 생성, `suppressed_ledger.jsonl`) | 대상(target)에 무관한 범용 인프라 — `ledger.py`/`batch.py` 코드 자체가 그대로 재사용 가능. |
| W1 guard wiring 테스트 스위트의 **패턴**(원자적 획득 테스트, 동시 스레드/프로세스 테스트, fail-closed 테스트) | 테스트 설계 방법론으로 승계. |
| C assurance 절차(`preflight 1~6` 체크리스트 방식, sampling/order_key/selection_trace/evidence class 독립 재계산) | `METHODOLOGY_PRESERVED.md`가 명시하는 "검증 규율 5종"의 구체 사례로 승계. |
| plane 구조·티켓 규약·진실 위계(T1~T6)·producer≠reviewer | `T-A-PIVOT-PRESERVE-001.json`과 `METHODOLOGY_PRESERVED.md`가 이미 명시적으로 "대상이 바뀌어도 유지"로 선언 — 12건 자산과 별개로 상위 계층에서 이미 보존 결정됨. |

**재사용 불가 (12-target 특정):**

| 자산 | 불가 사유 |
|---|---|
| `DIAGNOSTIC_PILOT_MANIFEST.json` (12 target, `DIAG-PILOT-001` 표본) | `V3_0_1_SUCCESSOR_DELTA.md`/`FINAL_MAIN50_MANIFEST.json` 등 V3는 별도의 50-target(MAIN50) manifest를 쓴다 — 표본 자체가 다르다. |
| `DIAGNOSTIC_PILOT_MANIFEST_SHA256` 상수(firewall.py 하드코딩값) | 이 상수는 이 특정 12-target manifest의 해시이므로 V3 manifest에는 적용되지 않는다. 값 자체를 재사용하는 것이 아니라 "release doc이 manifest sha256을 바인딩한다"는 **바인딩 메커니즘**만 승계 대상. |
| `ExecutionScope.V2_DIAGNOSTIC` 값 자체 | scope 이름이 pilot 전용이며, V3가 같은 enum에 새 scope 값을 추가하는 방식이 될 것으로 보이나 이는 추측이며 본 lane이 확인한 사실이 아니다. |
| `V2_DIAGNOSTIC_RELEASE.json` 문서 자체(released_at/target_count=12/run_id=DIAG-PILOT-001) | target-특정 릴리스 문서이며 V3 collection에는 새 릴리스 문서가 필요하다. |
| `tests/test_w1_v2_diagnostic_scope.py`의 21개 테스트 중 manifest 12-target 값에 하드코딩된 assertion(있다면) | 본 lane은 이 파일의 각 테스트 바디까지 assertion 값 단위로 검사하지 않았다 — §5 참조. |

---

## 5. 검증하지 않은 것

- **12건이 실제로 "한 번도 실행되지 않았다"는 명제를 A의 자체 보고 문서(`T-A-PIVOT-PRESERVE-001.json`)
  및 로컬 디렉터리 부재(`find ... -iname "*batch*"` = 0건)로만 확인했다.** 원격(origin) 저장소나
  다른 워크트리(`.agent_worktrees/claude_b_*`, `landing_v2_exec` 등)의 디스크 내용은 뒤지지 않았다
  — 다른 B 워크트리 안에 우발적으로 남은 실행 흔적이 있는지는 **미확인**이다. 네트워크 접속
  0건 지시를 따랐으므로 원격 브랜치의 최신 상태도 확인하지 않았다(로컬 refs만 사용).
- **`V2_DIAGNOSTIC_RELEASE.json`의 `status` 필드는 여전히 문자 그대로 `"RELEASED"`다.** Director의
  freeze 지시(`HISTORICAL_METHOD_ASSURANCE`)가 이 문서 자체를 아직 개정하지 않았다는 사실을
  발견했지만, 본 lane은 "파일을 수정하지 마라"는 지시에 따라 **고치지 않았다**. 이 불일치를
  누가/언제 해소할지는 본 lane의 범위 밖이며 판단하지 않았다.
- `01041bc2`/`e2bb63e`/`b28aaa5c`/`54a0c7a4` 4개 SHA에서 `layer_firewall.py`의
  `BATCH_LAYER_REAL_SCOPES`가 동일하게 `V2_DIAGNOSTIC`을 결여한다는 사실은 확인했으나, **이것이
  의도된 설계(engine 층만 열면 충분)인지 미완의 배선(batch 층도 열어야 하는데 빠진 것)인지는
  판정하지 않았다** — 자산의 품질 평가는 본 lane의 임무가 아니다. `V2_DIAGNOSTIC_RELEASE.json`의
  `launch_gates_at_release_time.3_V2_DIAGNOSTIC_scope` 필드가 "구동기 배선은 T-B-BLK-008로
  미해결"이라 적어 두었다는 정황만 인용하며, T-B-BLK-008 티켓 본문 자체는 열람하지 않았다.
- `tests/test_w1_*.py` 4개 파일의 테스트 함수 **개수**만 셌다(`grep -c "^def test_"`). 각 테스트의
  통과/실패 여부, 즉 65개 테스트가 실제로 green인지는 **실행하지 않았고 확인하지 않았다** — 개수
  집계이지 실행 결과 검증이 아니다.
- `research/landing_accessibility/control/pilot/` 아래 `SHARED_SLOT_REGISTER.json`,
  `R1_OPERATIONALIZATION_NOTE.json`은 열람해 §1/§2 근거로 일부 인용했으나, `bus_mirror_a/tickets`·
  `bus_mirror_a/acks` 전체(136개 JSON 파일)를 전수 검토하지는 않았다 — `DIAG-PILOT-001`/
  `V2_DIAGNOSTIC` 문자열이 걸린 파일만 추출해 그중 가장 직접적인 근거 문서 몇 건만 열었다.
- 다른 lane(`v3/lanes/lane1_manifest_consistency.json`)의 내용은 확인하지 않았다 — 중복·모순
  여부를 대조하지 않았다.
