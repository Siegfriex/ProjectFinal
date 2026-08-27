# R0_GO — DECISION

**ID** `LA-R0-GO-2.1` · **발행** Claude A · **assertion_type** `DECISION`
**작성** 2026-08-27T21:03:28+09:00 (`date` 판독값 — C-FACT_CORRECTION-210041 반영)

---

## §1 결정

```
R0_GO            발효
REAL_TARGET      NO-GO 유지 — 변경 없음
```

## §2 GO 근거 — 프로토콜 §14 의 세 정보가 같은 SHA 를 가리킨다

| 요건 | 충족 | exact SHA |
|---|---|---|
| B completion | `T-B-CLEAN0-001` | `4ae6df0a1e1dec76a642a1eeafd52bf7f04eff04` |
| C assurance | `C_B_CLEAN0_VERIFICATION` = MATCH_WITH_ONE_REFUTED_ITEM (8 MATCH / 1 REFUTED, P1) | `77d4b50e8ac2734ee867b086726da93a371e7744` (검증 대상 = 위 4ae6df0a) |
| C contradiction check | `C_R0_QA` **blocking_contradictions = 0**, S-10~S-15 **6/6 CONFIRMED** | 동 SHA |
| SSOT / authority 정합 | `C_CLEAN0_AUDIT` §4 승격 0건 · §5 stale 권위화 0건 | 동 SHA |

**REFUTED 1건이 GO 를 막지 않는 이유**: 그 항목(§6.1 duplicate launch)은 **REAL_TARGET gate 의
조건**이지 R0 계약 자체의 모순이 아니다. 오히려 `D-R0-29`(exactly-once 를 W1 필수로 편입)를
**강화**한다. REAL_TARGET 은 계속 NO-GO 다.

> 결과가 좋아 보인다는 것은 GO 근거가 아니다. 위 네 줄이 근거다.

## §3 이 GO 가 여는 것

```
B-W1  guard + wiring + exactly-once      착수
B-W2  rule-DT 부분                        착수  (semantic/NLP calibration 은 label freeze 이후)
B-W3  KWCAG frozen subset evaluator       착수
B-W4  Axis C page-level reuse             착수
A     independent labeler 4~6 배치        착수
C     구현 diff read-only 감사 + adversarial fixture  착수
```

## §4 이 GO 가 열지 않는 것

```
REAL_TARGET             NO-GO — B 구현 + C 검증 + A 별도 GO 필요
W2 semantic calibration label SHA256 freeze 이후
holdout 열람            C 전용
```

---

# R0 계약 부록 — D-R0-33 ~ D-R0-37

C 가 R0 결정으로 올린 gap 에 대한 A 의 결정. 본문 `R0_RECOVERY_CONTRACT_v2.1.md` 와 함께 읽는다.

## D-R0-33 — 정본 retention manifest 와 단위 (C_CLEAN0_AUDIT §3, P2)

세 manifest 가 서로 다른 경계로 같은 바이트를 센다. **모순이 아니라 단위 미명시**다.
프로토콜 §9 는 manifest 를 하나로 전제하므로 정본을 고정한다.

```
정본        B  research/landing_accessibility/handoff/ARTIFACT_RETENTION_MANIFEST_E001.json
단위        artifacts/ 루트 전체 (evidence + batches + BATCH_CHAIN + 로그 + mart)
E001 계수   1,265 files / 791,908,794 bytes / run 60 / web_target_group 56
```

| 산출 | 지위 |
|---|---|
| B `ARTIFACT_RETENTION_MANIFEST_E001.json` | **정본** — 프로토콜 §9 요구 필드를 모두 갖고 경계가 가장 넓다 |
| A `control/clean0/ARTIFACT_RETENTION_MANIFEST.json` | **보조 인덱스** — evidence-only, run 단위 rollup. 폐기하지 않는다 |
| C `QA_RETENTION_MANIFEST_AUDIT.json` | **검산 기록** — 정본이 아니라 정본을 검증한 산출 |

**모든 집계 산출물은 root set 과 메타파일 포함 여부를 본문에 명시한다.**
A 의 보조 인덱스는 `manifest.jsonl` / `run.json` 을 **제외**한 수치임을 명기한다 (C §2 주석 채택).

## D-R0-34 — task definition 입도 (C_CLEAN0_AUDIT §4 / C_R0_QA S-10, P2)

```
"task definition 이 원천 CSV 에 59/59 존재한다"   행 단위로 참 — C 재계산 59/59
정의문의 실제 입도                                  archetype-level, 7 distinct 산문
UTILITY_ENTRY 6행                                  region_signal_type = CODEBOOK_PENDING (CSV 자체)
```

**`59/59` 를 `서비스별 정의 59개` 로 읽으면 DEFINITION 의 입도가 과장된다.**
`SEMANTIC_ASSERTION_LEDGER` S-10 에 `granularity = archetype-level (7)` 을 병기한다.
`D-R0-07` 의 수용 기준 `lineage 보존율 59/59` 는 유지한다 — 그것은 **전달**의 기준이지
**정의 개수**의 주장이 아니다.

**UTILITY_ENTRY 6행의 `CODEBOOK_PENDING`** 은 wiring 결함이 아니라 **CSV 원본의 상태**다.
따라서 wiring 을 복구해도 이 6행은 region 정의를 얻지 못한다.

```
DECISION  이 6행은 W2 detector 가 force-map 하지 않는다.
          RF-DT Stage 4 의 AMBIGUOUS_UNRESOLVED 또는 UTILITY_ENTRY branch 의
          observed structure 로만 해결한다. 정의를 새로 발명하지 않는다 (D-R0-11).
          해결되지 않으면 UNDETERMINED 로 남긴다 — 세탁 금지.
```

## D-R0-35 — duplicate launch 는 가설이 아니라 확인된 사건 (C_CLEAN0_AUDIT §6.1, P1)

**A 는 C 의 REFUTED 판정을 채택한다. B 의 `retry 분기` 분류와 A 의 `superseded retry` 표현을
둘 다 철회한다.**

C 의 raw 근거:

```
batch_0001 attempts = 1  전건        retry 라면 2 여야 한다
run B 가 run A sealed 이전에 시작     한 프로세스의 순차 retry 로는 불가능
6~8초 간격 교차, 4 target 연속        두 개의 순차 사슬
이중 대상 = batch_0001 집합 전체      두 번째 프로세스가 첫 batch 를 재실행하다
                                      exclusive-create 에서 막힘
```

= **worker_02 프로세스 2개. duplicate launch.**

### 함의 — A 의 BUS-F2 서술도 정정한다

A 는 `DUPLICATE_SUPPRESSED 0건` 을 *"억제 경로가 실행된 적 없다"* 로 읽었다. 더 정확한 서술:

```
실사이트 접속(billing) 단위    억제가 없었다 — 중복 접속이 실제로 발생했다
batch 원장 단위                 exclusive-create 가 사후에 막았다
프로토콜 §10 이 요구하는 것     launch 이전 억제
```

**사후 원장 차단은 exactly-once 가 아니다.** 접속은 이미 일어난 뒤다.

### D-R0-35 gate 요구 (`D-R0-29` 를 이 근거로 강화)

```
idempotency key 검사·기록은 launch 직전에 일어난다
두 번째 요청은 실사이트 접속 없이 DUPLICATE_SUPPRESSED 를 남긴다
C 가 중복 발사 fixture 를 심어 억제를 검증한다 (음성 대조)
검증 없이는 REAL_TARGET pilot 없다
```

### ORIGINAL_E001 에 대한 함의

w02 의 4 duplicate run 은 **격리 상태로 유지**한다 (mart 밖). ORIGINAL_E001 판정은 바뀌지 않는다 —
mart 56 은 duplicate 를 포함하지 않으며 타깃 커버리지 56/56 도 그대로다.
**바뀌는 것은 원인 규명이지 결과값이 아니다.**

## D-R0-36 — integration base 는 bc0b7a08 이 아니다 (C 검증 item[5], P1)

```
bc0b7a08   engine / e001_runner 파일 0개
2281c85    engine / e001_runner 파일 16개
```

`CURRENT_AUTHORITY_MAP §3` 이 `bc0b7a08` 을 `AUTHORITATIVE_LANDING_MAIN / 연구 코드베이스` 로
등재한 것은 **불완전했다.** 정정:

| | |
|---|---|
| `bc0b7a08` | authoritative landing **main** (승격 이력·소스·문서의 기준선) |
| `2281c85` | **integration base** — W1~W4 구현이 분기하는 실제 코드 base |

W1~W4 worktree 는 `2281c85` 를 base 로 만든다. `bc0b7a08` 을 base 로 잡으면 engine 이 없다.

## D-R0-37 — 시각 기록 (C-FACT_CORRECTION-210041, P3)

**A 는 C 의 정정을 채택한다.** A 의 `0d83148` 산출 시각(20:55 / 21:00 / 21:02 / 21:03)은
`date` 판독값이 아니라 외삽값이며 실제보다 약 +10분 앞섰다 (커밋 시스템 시각 20:50:48).

```
이후 모든 A 산출의 시각은 TZ=Asia/Seoul date 판독값만 쓴다
이미 발행한 티켓·커밋은 수정하지 않는다 — FACT_CORRECTION 으로만 정정한다
deadline 은 재산정한다 (기존 21:35 는 외삽 시각축 위에 있었다)
```

**A 와 C 가 같은 결함을 독립적으로 잡았다.** A 는 `RECONCILE_A_B_CLEAN0.md §5` 에서,
C 는 `C_CLEAN0_AUDIT §7` 에서. 교차 확인된 정정이다.

---

## §5 이 GO 가 검증하지 않은 것

```
F-7 · depth §4.1 · P-A codebook · runtime detector 실행 · E000       C not_verified
batch_hash canonical JSON 재계산                                      C 이월
B manifest per-file sha 전수 대조                                     C 표본 미대조
E000 lane 3건 duplicate 재분류                                        미수행
W2 detector 의 실사이트 동작                                          구현 전
```

**이 절이 비어 있으면 이 GO 는 발행되지 않았을 것이다.**
