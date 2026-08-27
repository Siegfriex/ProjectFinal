# RQ-D11 — E001 원장과 evidence 는 **완전히 일치한다**

**verdict**: `REFUTED` (H1_OCCURRED) · **H2_CONSISTENT 지지**
**부수 결과**: RQ-D1 F4 의 "3 target 이 조용히 사라진다" 를 **한 층 좁혔다**
**재현**: `.venv/bin/python research_d/tools/rq_d11_ledger_vs_evidence.py`
**산출**: `results/RQ_D11_ledger_vs_evidence.json`

---

## RQ

C 가 `C-BLOCKER-220418` 에서 W1 fixture e2e 의 원장 귀속 분열을 보고하며
**"2026-08-27 05:14 w02 형태에서 정확히 재발할 구조"** 라고 썼다.
그 구조가 **E001 raw 에서 실제로 발생했는가?**

C 의 주장을 사실로 받지 않고 E001 batch 파일과 evidence 디렉터리에서 독립 재계산했다.

## 결과

| worker | batch 파일 | 원장 target | evidence target | ORPHAN | GHOST | SUPPRESSED_BUT_MEASURED |
|---|---|---|---|---|---|---|
| w01 | 4 | 15 | 15 | 0 | 0 | 0 |
| w02 | 4 | 15 | 15 | 0 | 0 | 0 |
| w03 | 4 | 15 | 15 | 0 | 0 | 0 |
| w04 | 4 | 14 | 14 | 0 | 0 | 0 |
| **합** | **16** | **59** | **59** | **0** | **0** | **0** |

**총 불일치 0.** 원장 target 집합과 evidence target 집합이 정확히 같고, 합계 59 는
RQ-D1 이 확인한 attempted 59 와 일치한다.

## F1 (OBSERVATION) — C 가 지목한 구조는 E001 에 없다

`ORPHAN`(evidence 는 있는데 원장에 행이 없음) = **0**. C 의 fixture 관측은 W1 harness 에서
두 프로세스가 같은 out dir 를 공유했을 때 나타난 것이고, E001 은 worker 별로 디렉터리가
분리돼 있어 그 조건이 성립하지 않는다.

**C 가 틀렸다는 뜻이 아니다.** C 의 관측은 fixture e2e 에서 참이고, C 는 그것이
"재발할 구조" 라고 **예측**했다. D 는 그 예측이 E001 에서는 실현되지 않았음을 확인했을 뿐이다.

## F2 (OBSERVATION) — 원장은 중복 실행을 **정확히 dedup 했다**

evidence 디렉터리가 2개인 target 7건(w02 5 · w03 2)이 **전부 원장에서 1행**이다.
RQ-D1 F3 이 mart 에서 확인한 "duplicate observation rows = 0" 과 같은 방향이며,
dedup 이 mart 단계가 아니라 **원장 단계에서 이미 이뤄졌음**을 보여준다.

## F3 (OBSERVATION · **RQ-D1 F4 를 한 층 좁힌다**) — 원장은 실패 3건을 정직하게 기록했다

RQ-D1 F4 에서 나는 "3 target 이 mart 에서 조용히 사라지고 `NO_EVIDENCE` 행조차 없다" 고 썼다.
이제 그 손실이 **어느 층에서** 일어났는지 안다.

| outcome | w01 | w02 | w03 | w04 | 합 |
|---|---|---|---|---|---|
| `ACCOUNT_ACTION_BLOCKED` | 5 | 7 | 6 | 7 | 25 |
| `UNRESOLVED` | 5 | 3 | 4 | 6 | 18 |
| `AUTH_GATE` | 5 | 3 | 3 | 1 | 12 |
| `CAPTCHA` | – | 1 | – | – | 1 |
| **`SKIPPED_RETRY_EXHAUSTED`** | – | **1** | **2** | – | **3** |

`SKIPPED_RETRY_EXHAUSTED` **3건**은 RQ-D1 이 LONG 재시도 실패로 분류한 그 3 target
(w02 `ff3ee504`, w03 `2cd43b99`·`dd5061eb`)과 정확히 일치한다.

> **수집기와 원장은 결함이 아니다. 실패를 정확한 이름으로 기록했다.**
> 손실은 **원장 → mart 사이**에서 일어난다. mart 빌더가 이 3행을 옮기지 않았다.

RQ-D1 F4 의 P1 제안("mart 에 `NO_EVIDENCE` 행을 남길 것")은 유지되지만, **책임 지점이 바뀐다** —
수집 단계가 아니라 mart 빌드 단계다. 그리고 원장에 이미 정확한 outcome 이 있으므로
**새로 만들 필요 없이 옮기기만 하면 된다.**

## 자기 정정 1건

1차 실행에서 `is_suppressed()` 가 `SUPPRESS`/`DUPLICATE` 만 걸러 `SKIPPED_RETRY_EXHAUSTED` 를
"측정됨" 으로 분류했고, 그 결과 **GHOST 3건** 이 나왔다. 원장은 정직하게 기록했는데 D 의 분류가
그것을 결함처럼 보이게 만든 것이다. `NOT_MEASURED` 어휘를
`SUPPRESS* / DUPLICATE* / SKIPPED* / *RETRY_EXHAUSTED* / ABORT*` 로 시정했고,
시정 전 수치를 결과 JSON `pre_correction_totals` 에 남겼다.

**이것이 이 RQ 에서 가장 중요한 교훈이다** — "불일치" 를 세는 코드가 어휘를 모르면
정상 동작을 결함으로 만든다. D 는 같은 실수를 D-DEF-03 에서도 했다(스키마 오독).

## 반례 / 대안설명

- *"batch 파일이 사후에 정리됐을 수 있다"* → `BATCH_CHAIN.jsonl` 의 hash chain 이
  `previous_batch_hash` 로 연결돼 있고 4 worker × 4 batch 가 모두 연결된다. 다만 D 는
  chain hash 를 **재계산해 검증하지 않았다** — 이건 한계다.
- *"worker 내부에서 프로세스가 갈렸을 수 있다"* → E001 은 worker 당 1 프로세스로 보이나
  D 는 실행 로그를 보지 않았다. 프로세스 수는 확인하지 않았다.

## Limitations

1. **batch hash chain 을 재계산해 검증하지 않았다.** 파일이 스스로 주장하는 연결만 읽었다.
2. worker 당 프로세스 수를 확인하지 않았다. C 가 지목한 조건(두 프로세스, 같은 out dir)이
   E001 에 없었다는 것은 **디렉터리 분리로부터의 추론**이지 실행 로그 확인이 아니다.
3. outcome 어휘의 완전한 목록을 SSOT 나 코드에서 확인하지 않았다. 관측된 5종만 봤다.
4. mart 빌더 코드를 읽어 3행이 왜 누락됐는지 확인하지 않았다 → RQ-D13c 로 이월.

## Production implication (제안일 뿐. A ADOPT 전에는 implementation candidate 도 아니다)

- **P2**: mart 빌더가 원장의 `SKIPPED_RETRY_EXHAUSTED` 행을 옮기면 RQ-D1 F4 의 분모 손실이 해소된다.
  값을 새로 만들 필요가 없다 — 원장에 이미 있다.
- **P3**: C 의 W1 fixture 관측은 E001 에서 재현되지 않았다. 다만 **미래 조건**(두 프로세스, 공유 out dir)에
  대한 C 의 경고는 이 결과로 무효화되지 않는다.

## 후속 연구질문

- **RQ-D11a**: batch hash chain 을 재계산해 무결성을 검증
- **RQ-D13c**: mart 빌더가 `SKIPPED_RETRY_EXHAUSTED` 행을 어디서 떨어뜨리는가 (코드 exact SHA)
