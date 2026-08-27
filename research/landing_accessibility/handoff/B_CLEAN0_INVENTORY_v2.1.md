# B CLEAN-0 INVENTORY — v2.1 POST-PILOT RECOVERY

- 작성: Claude B (Production / Measurement / Analysis Orchestrator)
- 기준 시각: 2026-08-27 20:48 KST
- 브랜치: `claude-b/clean0-v21`
- base SHA: `2281c853950d0c475c5d2c1678680b971c2804f4`
- 권위 문서: `SSOTV2/00~09` (LA-SSOT-2.1 / LA-RFDT-2.1 / LA-ORCH-2.1)
- **코드 변경 0줄.** 읽기 + 기존 산출물 재집계만 했다.
- 경로 약칭: `R/` = `research/landing_accessibility/`

---

## 0. 요약

`08_CURRENT_STATE_BASELINE_v2.1.md`의 remote SHA 8건은 **전건 원격과 일치**한다(OBSERVATION).
G1~G5는 current source에서 **전건 재현**됐다(OBSERVATION).

그리고 CLEAN-0에서 **baseline·audit 문서가 담지 않은 사실 5건**이 나왔다.
그중 B-N1·B-N2는 `RECOVERY_DATAFLOW_AUDIT.md`(SHA `2281c85`)의 실증거 수치를
**표본 n=14에서 전수 n=58로 교체**하며, 결론의 방향은 유지하되 **강도를 바꾼다**.

| ID | 내용 | type | priority |
|---|---|---|---|
| B-N1 | probe 실증거는 14건이 아니라 **58건**이다. 전수 재집계 결과가 audit §O-5 표와 다르다 | OBSERVATION | P1 |
| B-N2 | 실사이트에서 `declared_regions` 3건 / `declared_endpoints` 1건이 **실제로 검출된다** — audit F-1이 경고한 위양성 경로가 표본에 실재한다 | OBSERVATION | P1 |
| B-N3 | `search_inputs`가 **10/58**에서 검출됐다 — QUERY 실사이트 경로의 성립 가능성이 실증거로 뒷받침된다 | OBSERVATION | P2 |
| B-N4 | exactly-once가 **구현돼 있지 않다**. `run_id`는 timestamp 합성이고 idempotency key·target lock·`DUPLICATE_SUPPRESSED`가 저장소에 없다 | IMPLEMENTATION | P1 |
| B-N5 | `.agent_bus/`가 `.gitignore:48`에 있어 **Git 추적 0건**이다 — LA-ORCH-2.1 §16 투명성이 구조적으로 불가능하다 | OBSERVATION | P1 |

`ARTIFACT_RETENTION_MANIFEST_E001.json`을 신규 생성해 같은 커밋에 넣었다 —
LA-ORCH-2.1 §9가 요구하는 manifest가 **그 전까지 저장소에 존재하지 않았다**.

---

## 1. Exact remote state (OBSERVATION, `git ls-remote origin` 직접 확인)

| ref | SHA | baseline 문서와 |
|---|---|---|
| `refs/heads/research/landing-accessibility-main` | `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` | 일치 |
| `refs/heads/control/landing-orchestrator` | `084eff541836c2e16418b96bd230c1d58bcda663` | 일치 |
| `refs/heads/claude-b/analysis-current` | `82f631f1e6bd3708bc8f95f0b8edcd90e22cef0d` | 일치 |
| `refs/heads/claude-b/measurement-recovery` | `2281c853950d0c475c5d2c1678680b971c2804f4` | 일치 |
| `refs/heads/claude-c/assurance-current` | `1baa865b4a673af05033e6e6289fd2713676baa5` | 일치 |
| `refs/heads/handoff/landing-a-20260827` | `7c8facebe95ec3793756a82d809be37ca17b6b6e` | 일치 |
| `refs/heads/handoff/landing-b-20260827` | `66aa655400f872197e64390522225823e93b5628` | 일치 |
| `refs/heads/handoff/landing-c-20260827` | `3d84741656ce08991ceb06572b2b242470f1f9e3` | 일치 |

추가 관측 — baseline 문서에 없는 사실:

- `refs/heads/agent/landing-v2-exec` = `bc0b7a08…` — authoritative main과 **동일 SHA**다.
- `refs/heads/main` = `a835d5d8b06a15d5a75dee9ba34a3654555fc930` — landing 연구 계보와 별개다.

## 1.1 Integration base 후보 (OBSERVATION)

`git merge-base --is-ancestor bc0b7a08 2281c85` → **YES**.
`git diff --stat bc0b7a08...2281c85` → 128 files / +40,481.

authoritative main `bc0b7a08`에는 `engine/`·`e001_runner/`가 **없다**. 측정 production
code 전체가 `2281c85`에만 있다. 따라서 **integration base 후보는 `2281c85`이며,
`bc0b7a08`은 그 조상**이다. W1~W4는 전부 `2281c85`를 base로 잡아야 한다.

---

## 2. G1~G5 current-source 재현 (OBSERVATION)

| 갭 | SSOT 진술 | 재현 위치 (@`2281c85`) | 판정 |
|---|---|---|---|
| G1 guard granularity | target-level kill | `R/src/landing_accessibility/e001_runner/guard.py:170-182` — 첫 위험 후보에서 `return risk`, 호출부가 `Scout` 미생성 | **재현됨** |
| G2 task wiring | 실행 경계에서 필드 유실 | `…/e001_runner/executor.py:66-75` — `region_definition=None`·`endpoint_definition=None`·`*_signal_type=CODEBOOK_PENDING` 4개 전부 **인자 무관 상수** | **재현됨** |
| G3 real-site detector | synthetic marker 의존 | `…/engine/l1_engine.py:213-218` (`declared_regions`), `:221-231` (`declared_endpoints`/`body_endpoint_reached`) — 생산자는 `l0_probe.js`의 `[data-region]`/`[data-endpoint]` | **재현됨** |
| G4 KWCAG evaluator | production adjudicator 부재 | `grep -rn "KWCAG" R/src` → 어휘 언급 2건뿐. `l0_collector.py:9`가 **"이 모듈도 KWCAG verdict를 만들지 않는다"**고 명시. criterion adjudicator 심볼 0개 | **재현됨 (부재 확인)** |
| G5 Axis C semantic | geometry 있음 / classification 미완결 | `l0_collector.py:258-283` `classify_interrupt`는 **결정적 1순위만** 수행하고 나머지는 `AMBIGUOUS`+`UNKNOWN`. semantic/VLM은 `ai_review` 층 | **재현됨** |

G3에 대한 보강 — QUERY 분기(`l1_engine.py:206-212`)는 `region_definition`을 읽지 않고
`search_inputs`의 `visible ∧ in_form ∧ has_submit`만 본다. **synthetic marker에 의존하지
않는 유일한 실사이트 경로**이며, 이 사실이 §3의 B-N3와 직접 연결된다.

---

## 3. 실증거 전수 재집계 — audit 표본 교체 (OBSERVATION)

`RECOVERY_DATAFLOW_AUDIT.md` §O-5는 "E001 실증거 14건의 `probe.json`"을 재집계했다.
CLEAN-0에서 retention manifest를 만들며 확인한 실제 개수는 **58건**이다.
신호는 `probe.json` 최상위가 아니라 `raw_features` 아래에 있다.

경로: `.agent_worktrees/claude_b_e001_worker_0*/artifacts/*/evidence/*/*/l0a/probe.json`

| 신호 | audit (n=14) | **전수 (n=58)** |
|---|---|---|
| `declared_endpoints` 길이 0 | 14 | **57** — 길이 2가 **1건** |
| `declared_regions` 길이 0 | 13 | **55** — 길이 1이 **3건** |
| `search_inputs` 길이 0 | 12 | **48** — 길이 1이 9건, 길이 2가 1건 |
| `body_endpoint_reached` = null | 14 | **58** (전건) |
| `article_present` > 0 | (미집계) | **14건** |
| `primary_action_candidates` 존재 | (미집계) | **58/58** |
| `modal_overlay_candidates` 존재 | (미집계) | **58/58** |

### 3.1 결론의 방향은 유지, 강도는 바뀐다

- **유지**: `body_endpoint_reached`는 전수 58/58 null이다. audit F-1의 핵심 주장
  — "실사이트는 `data-endpoint-reached`를 내보내지 않으므로 wiring만 고쳐도 endpoint는
  전건 False" — 는 **전수에서 더 강하게 확인**된다.
- **바뀜 (B-N2, P1)**: `declared_regions`가 3건, `declared_endpoints`가 1건 **실제로
  검출된다**. audit은 이를 "우연 일치가 생기면 위양성"이라고 **가능성**으로 경고했으나,
  전수에서는 **가능성이 아니라 표본에 실재하는 조건**이다. W2가 `[data-*]` 경로를
  남겨 두면 이 4건에서 위양성 area/endpoint 신호가 발생할 수 있다. → W2는 marker 경로를
  "추가로 구현하지 않는" 수준이 아니라 **명시적으로 제거하거나 실사이트에서 비활성화**해야
  한다. C에게 adversarial fixture 대상으로 지정 요청.
- **바뀜 (B-N3, P2)**: `search_inputs`가 **10/58**에서 검출됐다. G3의 유일한 실사이트
  경로가 실제로 신호를 만든다는 뜻이다. 다만 QUERY archetype 5건은 전부 가드로
  Scout 이전에 죽었으므로(audit §3.1), 이 10건과 QUERY 5건의 교집합은 **아직 확인되지
  않았다** — W1 완료 후 검증 항목으로 넘긴다. (`AMBIGUOUS_UNRESOLVED`로 둔다.)

### 3.2 재집계 방법 정정

첫 집계에서 `probe.json` 최상위에 `region_signals`를 찾아 전건 0으로 읽었다.
실제 구조는 `{collected_at, probe_version, raw_features, url}`이며 신호는
`raw_features` 아래다. 위 표는 `raw_features` 기준 재집계 결과다.

---

## 4. Raw artifact retention manifest (신규 산출, OBSERVATION)

LA-ORCH-2.1 §9가 요구하는 manifest가 **저장소에 존재하지 않았다**
(`find -iname '*RETENTION*MANIFEST*'` → 0 hit). 이번 커밋에서 신규 생성한다.

`ARTIFACT_RETENTION_MANIFEST_E001.json`:

| 항목 | 값 |
|---|---|
| root 수 | 5 |
| artifact 총 개수 | **1,265** |
| 총 bytes | **791,908,794** (≈755 MiB) |
| per-file sha256 | 전건 수록 |
| root별 aggregate sha256 | 수록 |
| evidence run id 총수 | **60** |
| distinct web_target_group | **56** |
| producer SHA | `2281c853950d0c475c5d2c1678680b971c2804f4` |
| read_only | true |

root 내역:

| root | files | bytes |
|---|---|---|
| `claude_b_e001_worker_01/artifacts` | 322 | 246,834,004 |
| `claude_b_e001_worker_02/artifacts` | 372 | 241,246,832 |
| `claude_b_e001_worker_03/artifacts` | 279 | 122,633,641 |
| `claude_b_e001_worker_04/artifacts` | 278 | 180,921,638 |
| `claude_b_analysis_current/artifacts` | 14 | 272,679 |

### 4.1 run 60 vs target 56 (OBSERVATION, P2)

4개 target이 evidence run을 2개씩 갖는다:
`wtg_13ed070478ef62c3` · `wtg_9390ef32addf32bf` · `wtg_b728911c9782edb8` · `wtg_e1fadb214cde51c0`.

네 건 모두 **`e001_w02/batches/batch_0001_b0001.json` 한 파일에만** 최종 outcome이
1건씩 기록돼 있다(CAPTCHA 1 / ACCOUNT_ACTION_BLOCKED 3). 따라서 이것은 **중복 발사가
아니라 retry가 evidence run을 분기시킨 결과**로 판정한다. `DUPLICATE_SUPPRESSED`
사건이 아니다.

**다만 분모 위험이 남는다**: batch 결과 레코드에 `run_id` 필드가 없어(전건 `None`)
evidence run과 outcome을 join할 키가 산출물에 없다. audit F-4-1이 지적한
"`task_id` join key 부재"와 같은 계열의 결함이다. mart 단계에서 evidence run을
분모로 세면 56이 아니라 60이 되어 **4건 과대계산**이 발생한다. → W4 필수 점검 항목.

---

## 5. Exactly-once 경로 (IMPLEMENTATION, B-N4, P1)

`grep -rn "idempoten|DUPLICATE_SUPPRESSED|run_id" R/src/landing_accessibility/e001_runner/`
전수 결과:

- `batch.py:358` `run_id = f"e001-{target.target_id}-{_utc_now_iso()…}"` — **timestamp 합성**.
  같은 target을 다시 돌리면 **다른 run_id가 나오고 실행이 그대로 진행된다.**
- `idempotency_key` 심볼 **0건**.
- `DUPLICATE_SUPPRESSED` 심볼 **0건**.
- target 단위 lock **0건**.

현재 REAL_TARGET을 막고 있는 것은 exactly-once가 아니라 `engine/firewall.py`의
`evaluate_execution_scope` hard block과 allowlist다(`layer_firewall.py:3,143`).
즉 **scope gate가 열리는 순간 중복 방지 장치는 없다.**

LA-ORCH-2.1 §10이 요구하는 `ticket_id + run_id + target_id + collector_sha + protocol_sha`
키는 **구현 항목이지 기존 자산이 아니다.** W1 범위에 포함시켜야 한다.

---

## 6. Agent bus 상태 (OBSERVATION, B-N5, P1)

- 위치: `.agent_bus/landing_v2/` — `tickets/ acks/ completions/ heartbeats/ escalations/ _b_tools/ event_log.jsonl`
- 파일 28건. 최신 ticket은 `FINAL_READY-161836-d4cddb`, `STATS_READY-152106-227315`,
  `MART_READY-145415-cc76cf` — **이전 라운드(E001 종료 시점)의 것이며 v2.1 티켓은 아직 없다.**
- `.gitignore:48`에 `.agent_bus/`가 있고 `git ls-files .agent_bus` → **0건**.

LA-ORCH-2.1 §11은 bus 승계를 허용하지만 §16은 "GitHub만 보고도 현재 phase·blocker·
ticket 소재를 알 수 있어야 한다"고 요구한다. 현재 구성에서는 **bus가 원격에 전혀 나타나지
않으므로 §16이 구조적으로 충족 불가능**하다. A의 결정이 필요하다 — bus를 Git 추적으로
전환할지, 아니면 별도 Git-tracked mirror를 둘지.

B는 이 결정을 스스로 하지 않는다(SSOT 기준 변경 금지).

---

## 7. Stale / default task path 목록 (IMPLEMENTATION)

REAL_TARGET 본수집이 실제로 타는 경로:

```
batch.py:258  run_l1_if_safe_real(target, run=run, scope=scope)   # task= 미전달
   └─ real_executor.py:138  resolved_task = task or default_task_definition(target)
        └─ executor.py:66-75  4개 필드 상수화
```

`task=`를 넘기는 호출부는 저장소에 **없다**. 즉 59/59 전건이 `CODEBOOK_PENDING` task로
간다. `mapping_frozen_allowed()`(`l1_engine.py:100-105`)가 이를 막도록 구현돼 있으나
**호출부가 `tests/test_pc_fixture_engine.py:491-492`뿐**이라 실행 경로에 배선돼 있지 않다
(audit F-2 재확인).

→ W1은 배관 복구와 함께 **이 게이트를 실행 경로에 배선**해야 한다. 그러지 않으면
다음 수집도 같은 방식으로 조용히 진행된다.

---

## 8. B가 CLEAN-0에서 하지 않은 것 (범위 명시)

- REAL_TARGET 접속 0건.
- 코드 수정 0줄. `2281c85` 트리의 어떤 파일도 바꾸지 않았다.
- frozen MART·E001 산출물 수정 0건. 읽기 전용 재집계만.
- gold label 생성·열람 0건. holdout 탐색 0건.
- endpoint/archetype 신규 정의 0건.
- `SSOTV2/` 설치·이동·수정 0건 — A 소관이다. 현재 메인 워킹트리에 **untracked**로 존재한다.
- P-A endpoint codebook 존재 여부 미확인 — A 소관.
- KWCAG older-relevant frozen subset의 실제 내용 미확인 — R0에서 A가 scope를 고정한 뒤 W3에서 확인한다.

---

## 9. B가 A에게 요구하는 R0 결정

1. **integration base**를 `2281c85`로 고정할 것인지 (B 권고: 고정)
2. **bus Git 가시성** — `.gitignore:48` 유지 여부 (B-N5)
3. **`[data-*]` marker 경로 처리** — 제거인지 비활성화인지 (B-N2, 표본에 실재)
4. **exactly-once 구현을 W1 범위에 넣을 것인지** (B-N4)
5. **KWCAG frozen older-relevant subset의 exact 파일/SHA** — W3의 입력
6. **label calibration set 전달 경로와 SHA** — B는 holdout을 찾지 않는다

## 10. 현재 판정

- REAL_TARGET: **NO-GO** (A GO 없음, 그리고 B-N4로 exactly-once 미구현)
- B self-approval: **없음** — 이 문서는 `self_approved=false`
- 다음 gate: **R0_GO**

---

# 부록 A — `T-A-CLEAN0-B-001` 미충족 항목 보완

A의 `T-A-CLEAN0-B-001`(P1, base `2281c85`, deadline 21:30 KST) 수용기준 6개 중
①G1~G5 exact 위치 ②stale/default task path ④integration base ancestry는 본문
§2·§7·§1.1에서 이미 충족했다. 아래는 **③ W1~W4 scoped ownership**과
**⑤ exactly-once 소비 지점 + locks 계획**, **⑥ locks/ 사용 여부**를 채운 것이다.

## A.1 W1~W4 worktree / branch / scoped file ownership `DECISION(제안)`

전 worker 공통 base SHA = **`2281c853950d0c475c5d2c1678680b971c2804f4`**
(§1.1 근거: authoritative main `bc0b7a08`에는 production code가 없고 그 조상이다).

| worker | worktree | branch | 소유 파일 (배타) |
|---|---|---|---|
| **W1** Guard + Wiring + ExactlyOnce | `.agent_worktrees/claude_b_w1` | `claude-b/w1-guard-wiring` | `e001_runner/guard.py`<br>`e001_runner/executor.py`<br>`e001_runner/real_executor.py`<br>`e001_runner/plan.py`<br>`e001_runner/batch.py`<br>`scripts/run_e001_real.py`<br>`engine/firewall.py` (loader `:542-730`만) |
| **W2** RF / Endpoint Detector | `.agent_worktrees/claude_b_w2` | `claude-b/w2-rf-detector` | `engine/l1_engine.py`<br>`engine/l0_probe.js`<br>`engine/depth.py` |
| **W3** KWCAG Evaluator | `.agent_worktrees/claude_b_w3` | `claude-b/w3-kwcag` | `engine/kwcag/**` (신규)<br>`engine/vocabulary.py` |
| **W4** Axis C + Mart | `.agent_worktrees/claude_b_w4` | `claude-b/w4-axisc-mart` | `engine/l0_collector.py`<br>`engine/ai_review.py`<br>mart 산출 스크립트 (신규) |

### A.1.1 잠재 충돌 3건과 그 해소 `DECISION(제안)`

같은 파일을 두 worker가 만지지 않게 하기 위한 사전 규칙이다.

1. **`l1_engine.py` — W1 vs W2.**
   `TaskDefinition`(`:83-105`)은 W2 소유 파일 안에 있지만, W1의 wiring 복구는
   **dataclass를 바꿀 필요가 없다** — `region_definition`·`endpoint_definition`·
   `region_signal_type`·`endpoint_signal_type` 네 필드가 **이미 존재**하고
   (`:93-97`), W1이 할 일은 `executor.py:68-75`의 상수를 실제 값으로 교체하는 것뿐이다.
   따라서 W1은 `l1_engine.py`를 **읽기 전용**으로 쓴다. 필드 추가가 필요해지면
   W1은 직접 고치지 않고 W2에 ticket을 낸다.

2. **`l0_probe.js` — W2 vs W4.**
   W2는 `region_signals`/`endpoint_signals`(`:307-340`)를, W4는
   `modal_overlay_candidates`/`primary_action_candidates`를 쓴다.
   SSOT `00 §10`이 "page-level overlay geometry는 **기존 evidence에서 우선 재사용**"이라
   정했으므로 **W4는 `l0_probe.js`를 수정하지 않는다** — 전수 58/58에서
   두 후보 배열이 이미 존재함을 §3에서 확인했다. 파일은 W2 단독 소유.

3. **`vocabulary.py` — W3 vs W1.**
   `outcomes.py:6`이 KWCAG 판정 어휘를 이 파일에서 가져온다. W3 단독 소유로 두고
   W1은 읽기만 한다. W1이 새 outcome 어휘를 필요로 하면 W3에 ticket을 낸다.

### A.1.2 게이트 묶음 `DECISION(제안)`

`RECOVERY_DATAFLOW_AUDIT.md` §6.3이 형식 판정한 대로 **갱 1(wiring)과 갱 2(detector)는
독립이며 어느 한쪽 단독 완료도 검증 가능한 결과를 내지 않는다.**
따라서 **W1과 W2는 한 게이트에서 함께 검증하고, 그 사이에 재수집을 넣지 않는다.**
W3·W4는 별개 게이트로 병렬 진행 가능하다.

## A.2 Exactly-once — 소비 지점 `IMPLEMENTATION(제안)`

현재 코드에는 소비 지점이 **없다**(§5). 있어야 할 자리를 exact 위치로 지정한다.

```
batch.py:237  _real_executor(target)
  :245-248      run_id = f"{scope}-{target_id}-{timestamp}"   ← ★ 현재 여기서 매번 새로 생성
  :249          EvidenceRun.create(...)                        ← evidence 디렉터리가 여기서 생긴다
  :258          run_l1_if_safe_real(...)                       ← 실제 네트워크 접속
```

**★ 지점(`batch.py:245`, `EvidenceRun.create` 직전)이 유일한 삽입 위치다.**
그 이전에는 target별 실행 단위가 확정되지 않고, 그 이후에는 evidence 디렉터리와
네트워크 접속이 이미 발생한 뒤라 억제해도 늦다.

삽입할 순서:

1. `idempotency_key = sha256(ticket_id | run_id | target_id | collector_sha | protocol_sha)`
   — LA-ORCH-2.1 §10 구성 그대로.
2. `locks/<idempotency_key>.lock`을 `O_CREAT|O_EXCL`로 획득 시도.
3. 실패(=이미 존재) → **launch하지 않고** `DUPLICATE_SUPPRESSED` event를
   `event_log.jsonl`에 append하고 기존 결과를 반환.
4. 성공 → `EvidenceRun.create` 이하 진행, 종료 시 lock에 결과 SHA를 기록(삭제하지 않는다 —
   삭제하면 재실행이 다시 열린다).

### A.2.1 `run_id` 어휘 충돌 (P1, 설계 전 반드시 정리) `OBSERVATION`

프로토콜 §10의 `run_id`와 코드의 `run_id`는 **다른 것**이다.

| | 의미 | 생성 |
|---|---|---|
| 프로토콜 §10 `run_id` | **수집 회차** 식별자 (한 batch 전체) | ticket과 함께 A가 부여 |
| `batch.py:245` `run_id` | **target 1건의 1회 시도** 식별자 | timestamp 합성 |

코드의 `run_id`를 그대로 키에 넣으면 timestamp가 들어가므로 **키가 매번 달라져
억제가 영원히 발화하지 않는다.** 키에는 **회차 run_id**를 쓰고, target별
timestamp 식별자는 `attempt_id`로 이름을 바꿔 evidence 디렉터리에만 남겨야 한다.

### A.2.2 retry와의 관계 `OBSERVATION`

`_run_target_isolated`(`batch.py:264-`)가 `run_with_retry(attempt)`로 감싸고,
`attempt`가 `_real_executor`를 재호출한다. 따라서 **retry 1회마다 새 evidence run이
생긴다** — §4.1에서 관측한 run 60 vs target 56(4건 차이)의 기전이 이것이다.

exactly-once 설계는 **retry를 중복 실행으로 억제하면 안 된다.** 같은
idempotency key 안에서 `attempt_id`만 증가시키고, lock은 **key 단위(=target×회차)**로
잡는다. worker lock도 LA-ORCH-2.1 §10대로 **target 단위**다.

## A.3 bus `locks/` 사용 여부 `DECISION(제안)`

A가 생성한 `.agent_bus/landing_v2/locks/`를 확인했다 — **현재 비어 있다**
(`ls -la` 결과 파일 0건).

**B는 쓴다.** 다만 두 종류를 구분해서 쓴다.

| lock | 경로 | 단위 | 목적 |
|---|---|---|---|
| worker 작업 lock | `locks/worker-<W#>.lock` | worker | 같은 파일을 두 worker가 잡지 않게 (A.1 소유권의 런타임 강제) |
| 실행 idempotency lock | `locks/exec-<idempotency_key>.lock` | target × 회차 | A.2의 중복 발사 억제 |

두 번째는 `.agent_bus/`가 Git 추적되지 않으므로(T-B-BLK-002) **로컬 파일시스템에만
존재한다**. 이는 exactly-once에 문제가 없다(같은 머신에서 실행되므로).
다만 억제 사건 자체는 감사 대상이므로 `DUPLICATE_SUPPRESSED` event는
Git-tracked mirror에도 남긴다.

## A.4 여전히 B가 결정하지 않는 것

A.1~A.3은 전부 **제안**이다. 본문 §9의 R0 결정 6건이 나오기 전에는 착수하지 않는다.
특히 A.2는 `T-B-BLK-001`의 대상이며, A가 "W1 범위에 포함"을 결정해야 구현에 들어간다.
