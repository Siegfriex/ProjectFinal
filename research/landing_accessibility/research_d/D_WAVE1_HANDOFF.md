# D — Wave 1 Handoff (DRAFT, 진행 중)

**상태**: DRAFT. Wave 1 은 아직 닫히지 않았고 A 가 요청하지 않았다.
Director §8 이 요구한 항목을 **미리 조립**한다 — 마감에 몰아 쓰면 "무엇을 검증하지 않았는가" 가 부실해진다.

**D exact HEAD**: `3f5c6be7f390922404f1f420666bb235206a6564` · 브랜치 `claude-d/research-sandbox-v21`
**작성 시각**: 2026-08-28 03:57 KST (이후 갱신 시 이 문서를 덮어쓰고 커밋으로 이력을 남긴다)

---

## 1. Director §8 요구 항목 대조

| 요구 | 상태 |
|---|---|
| `D-V3-RELIABILITY-001` | **완료** — C 가 exact `369cbec` clone 에서 직접 실행해 `D_CONFIRMED` |
| `D-V3-Q12-MEASUREMENT-AUDIT-001` | **해당 없음** — 12건은 실행 없이 `HISTORICAL_METHOD_ASSURANCE` 로 종결됐다(REAL 접속 누적 0). 감사할 evidence 가 존재하지 않는다 |
| `D-V3-FRAME-CONSTRUCT-AUDIT-001` | **미착수** — A 배정이 "STEP 3 적대분석이 본업, 그때까지 C 요청분만" 이고 C 요청이 없었다 |
| `D-V3-RESEARCH-QUEUE-PREREG_v1` | **미작성** — Director §4 가 "P2 종료 이후에만" 으로 제한했다 |
| exact HEAD / MLflow run refs / 완결게이트 상태 | 아래 §2·§3 |
| unresolved risks | §5 |
| what D explicitly did NOT test | §6 |

## 2. 산출 (전부 `NON_CANONICAL`)

**발행 티켓 13건** — FACT_CORRECTION 2 · FINDING 10 · RELIABILITY 1. 전부 `to=[C]`, A 는 cc.

**하네스 8종**
| namespace | verdict |
|---|---|
| lane_s `LANE_S_HARNESS` / `R7_CONVERGENCE` | `READY_WITH_AMBIGUITY` / `CONVERGED_WITH_AMBIGUITY` |
| lane_l `LANE_L_HARNESS` | `READY_WITH_AMBIGUITY` |
| lane_f `LANE_F_HARNESS` / `DELTA9_CONVERGENCE` | `READY_WITH_AMBIGUITY` / `CONVERGED_WITH_AMBIGUITY` |
| lane_a `LANE_A_HARNESS` | `READY_WITH_AMBIGUITY` |
| lane_p `LANE_P_HARNESS` | `READY_WITH_AMBIGUITY` |
| converge `CONVERGE_DUP_VARS` | `DIFFERENT_QUANTITIES` |

**서브에이전트 31 run** (`AGENT_RUN_REGISTRY.jsonl`, append-only).
**상시 통제 2종** — SSOTV3 매니페스트 · endpoint 사전관측 lock. 드리프트 로그는 `D_STANDING_CONTROL_DRIFT_LOG.jsonl`.

## 3. 완결 게이트 상태

3조건(최상위 `verdict` + `FINDINGS.md` + 노트북 Restart→Run All 에러 0)을 코드로 강제한다.
**게이트를 통과하지 못한 산출은 MLflow 색인·git 커밋·티켓 발행 어느 것도 하지 않는다.**
현재 lane 하네스는 노트북 조건 대상이 아니다(분석 산출이 아니라 계산기 준비이며, 각 lane 이 자체 fixture 실행 로그를 낸다).

## 4. D 자신의 결함 — 13건, 전부 보존

`D-DEF-01`(charset 메커니즘 서술 UNCONFIRMED) · `03` · `04` · `05` · `06`(색인 30%) · `07`(미완 색인) ·
`08`(git add -A) · `09`(버스 스캐너 실명) · `10`+`10b`(사이드카 마스킹·게이트 헐거움) ·
`11`(reconciler 이름추출) · `12`(입력 의존성 분할 누락) · `13`(ACK 이 내용에 결속되지 않음).

`D-DEF-13` 은 A 가 `R18` 로 전 평면 규약화했고 B 가 자기 노출 116건을 셌다.
D 자신의 노출은 52건 중 49건 대조 불가(`D_ACK_BINDING_EXPOSURE.json`) — **소급 기입하지 않는다.**

## 5. unresolved risks

1. **`AMB-X02`** — `nav_container_depth` 에 endpoint cut 적용 여부. 수렴검사가 남긴 유일한 미해결 정의.
2. **정의 모호성 53건** 중 상당수가 열려 있다. lane 별 `ambiguous_definitions` 에 있으나 **단일 목록으로 커버리지를 말할 수단이 없다** — `V3_RULING_INDEX.json` 이 D allowlist 밖이다.
3. **ACK 결속 노출 49건** — 시간이 지나도 줄지 않는다. 복원 불가로 기록했다.
4. **`D-DEF-01` 메커니즘 미해명** — 조치는 유효하나 "왜 6/60 만 mojibake 인가" 는 답이 없다. 대체 가설 둘(선언 부재·lookahead)도 반증됐다.
5. **lane 별 green ≠ 통합 정확성** — 세 사례로 관측(§6-c).

## 6. what D explicitly did NOT test

- **MAIN50 실측 데이터를 한 번도 다루지 않았다.** 모든 하네스가 합성 fixture 결과이며 **구조 검증이지 분포 검증이 아니다.**
- **B 수집기의 실제 컬럼명과 정합을 검증하지 않았다.** 필드명이 다르면 전부 `KEY_MISSING` 으로 떨어진다.
- **REAL target 접속 0건.** 50 candidate URL 을 열지 않았다.
- **AX naming computation 을 구현하지 않았다** — Lane L 은 `accessible_name` 을 pass-through 로만 다룬다. `T-B-BLK-012` gap_1 이 이 전제를 건드린다.
- **`auth_gate_stage` UNDETERMINED 판정 로직** — Lane A 소관이나 R13 확정 이후 재수렴하지 않았다.
- **holdout·gold 관련 어떤 것도.** task gold 생성 0.
- **A·B·C 의 워크트리 내용** — D 는 그들의 수치를 재계산하지 않고 보고를 인용할 때 출처를 명시했다.

**(c) 가장 무거운 한계** — *검사의 범위가 곧 보증의 범위다.*
fixture 가 묻지 않은 것은 변이도 흔들지 못하고(Lane S precedence 결함이 60/60 green·변이 8/8 상태에서 생존),
lane 안에서 닫힌 것은 lane 경계를 넘지 못하며(`nav_container_depth` 중복이 reconcile 로만 드러남),
fake 로 만족된 Protocol 은 실물 연결을 보장하지 않는다(B 의 `RECON-002`).
**세 사례 모두 worker 완료를 그대로 canonical 로 채택했으면 드러나지 않았다.**

그리고 그 위에 한 겹 더 있다 — **두 독립 구현이 일치해도 같은 읽기에서 쓰였을 수 있다.**
`AMB-S14` 가 반대로 판정됐다면 Lane S 의 green 전부가 틀린 읽기에 대한 green 이었다.
A 가 `R20` 과 `R14` 로 같은 층을 겨냥했고, **이 구조 안에서 잡을 수 없는 경우**(전 평면이 같은 구절을 같게 오독)를
A 가 한계로 명시한 것에 D 도 동의한다.
