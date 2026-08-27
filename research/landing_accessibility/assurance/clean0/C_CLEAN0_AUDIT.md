# C_CLEAN0_AUDIT — A CLEAN-0 산출 독립 감사 + exactly-once 재발위험

**ticket** `T-A-R0-C-002` · **producer** C (claude-fable-5, `claude-c/assurance-v21`, base `1baa865`)
**audit target** `control/landing-orchestrator@0d831489fc0769fb35e5356f9c2a25de8ed884b7` (`control/clean0/**` 10 파일)
**production_modified** false · **labels_produced** 0 · **REAL_TARGET access** 0
**method** 모든 수치는 C 가 raw 에서 직접 재계산(`clean0/qa_retention.py` — B/A 코드 import 없음).

---

## §1 CURRENT_REMOTE_HEADS.json 12 ref 재확인 — OBSERVATION · MATCH

`git ls-remote origin` (C 세션 20:41 KST, full ref) 결과가 A 의 12개 값과 **전건 일치**.
추가로 C 가 관측한 것: 세션 중 `control/landing-orchestrator` 가 `084eff5 → 0d83148`,
`claude-b/clean0-v21 = 4ae6df0a`(신규) 로 전진. A 문서의 heads 는 20:43 시점 스냅샷으로 정확.

TRAP-01/02 도 C 가 독립 확인: primary worktree 는 `research/refcohort-r1@32460b8` 이며
`research/landing_accessibility/` 가 없다. merge-base(bc0b7a0, 32460b8)=32460b8 (조상). 일치.

## §2 ARTIFACT_RETENTION_MANIFEST.json 재해싱 — OBSERVATION · **MATCH (단위 주석 1건)**

A 는 "바이트 재해싱은 하지 않았다" 고 명시했다. C 가 **5 lane 전 파일을 바이트 재해싱**했다.
결과 파일: `clean0/QA_RETENTION_MANIFEST_AUDIT.json` (audited manifest sha256 `8acd1f90…36d9`, 커밋본과 동일).

| 검사 | 결과 |
|---|---|
| manifest.jsonl 항목 전건 sha256+bytes 재해시 일치 | **0 mismatch / 0 missing** (E001 4 lane + E000) |
| manifest 에 없는 파일 | 0 (manifest.jsonl / run.json 제외) |
| A `manifest_rollup_sha256` 재현 | **69/69 run 일치** (w01 15 · w02 18 · w03 13 · w04 14 · E000 9), trailing-newline 변형 0 |
| run_id 집합 A ↔ 디스크 | 차이 0 |
| BATCH_CHAIN 연결성 (`previous_batch_hash` 사슬) | 5 lane 전건 OK (4/4/4/4/2) |
| E001 evidence dirs / distinct obs / no-manifest dirs | **66 / 60 / 6** — A 와 일치 |
| mart 56 ⊂ evidence 60 (고아) | **0** |
| evidence − mart | 4 obs (`42812b3e… 9ec3d2fe… a57fb56b… d30bbdb4…`) — A 와 일치 |

**단위 주석 (P4, 정정 아님)**: A 의 lane `total_files/total_bytes` 는 **manifest.jsonl 과 run.json 을 제외한** 값이다
(w01 285/237,035,045). C 가 evidence 서브트리 전체를 세면 315/237,113,389 이고, 메타 2종을 빼면 A 값과 **정확히 일치**.
`ORIGINAL_E001_READONLY_DECLARATION §1` 의 "1,103 파일 / 753,676,839 bytes" 도 같은 단위다. 문서에 "메타파일 제외" 를 명기하면 된다.

**추가 관측**: manifest 없는 6 디렉터리는 **파일 0개·0 bytes(빈 디렉터리)** 다. 해시되지 않은 raw byte 는 존재하지 않는다.

**이 검사가 검증하지 않은 것**: `batch_hash` 는 canonical JSON 해시라 파일 바이트 해시로는 검산되지 않는다 —
C 는 사슬 연결성만 확인했고 batch 내용 해시 재계산은 하지 않았다 (`ledger.py:compute_batch_hash` 규칙 재구현 필요, 이월).

## §3 세 개의 retention manifest — 단위가 셋 다 다르다 (P2, A DECISION 필요)

| 산출 | 위치 | 단위 | E001 계수 |
|---|---|---|---|
| A `ARTIFACT_RETENTION_MANIFEST.json` | control@0d83148 | evidence 파일, 메타 제외 | 1,103 파일 / 753,676,839 B (+E000 159/118,545,321) |
| B `ARTIFACT_RETENTION_MANIFEST_E001.json` | clean0-v21@4ae6df0a | `artifacts/` 루트 전체(배치·로그·체인·mart 포함) | 1,265 파일 / 791,908,794 B (5 root, analysis_current mart 14 파일 포함) |
| C `QA_RETENTION_MANIFEST_AUDIT.json` | assurance-v21 | evidence 서브트리, 메타 포함 | 1,223 파일 (315+365+272+271) |

세 값은 **서로 모순이 아니다** — 같은 바이트를 다른 경계로 센다. B 의 루트 계수(322/372/279/278)는 C 의 `artifacts/` 디렉터리 계수와 정확히 일치.
**요구**: 프로토콜 §9 는 manifest 를 "하나" 전제한다. A 가 정본 manifest 와 단위(evidence-only vs root-all)를 R0 DECISION 으로 고정할 것.

## §4 SEMANTIC_ASSERTION_LEDGER — DEFINITION→OBSERVATION 승격 탐지

승격 사례 **0건**. 단 정밀화 필요 1건:

- **S-10** "task definition 이 원천 CSV 에 59/59 존재" `OBSERVATION` — 행 단위로 참(C 재계산 59/59). 그러나 정의문은 **archetype 당 1개(7 distinct 산문)** 이며 UTILITY_ENTRY 6행은 CSV 자체가 `region_signal_type=CODEBOOK_PENDING` 이다.
  "59/59 존재" 가 "서비스별 정의 59개 존재" 로 읽히면 DEFINITION 의 입도가 과장된다. 대장에 `granularity=archetype-level (7)` 을 병기할 것 (P2).

BLOCKER_LEDGER 의 `A_UNVERIFIED` 표기는 정직했다 — S-10~S-15 는 이제 `C_R0_QA.json` 에서 전건 CONFIRMED(S-10 은 qualifier 포함).

## §5 CURRENT_AUTHORITY_MAP — stale prose 가 권위로 올라간 곳

**0건**. §3 표의 T3 행 "task definition CSV 59/59" 는 §4 의 입도 주석이 붙어야 한다(같은 건).
`E001_LAUNCH.md`·`TIMEBOX` HISTORICAL 처리, `executor.py` docstring stale 등재 — 적절.

## §6 exactly-once 재발위험 — IMPLEMENTATION · **미구현 확인 (대조군 포함)**

스캔 대상: `2281c85` `.py` 50 파일 + `scripts/`. 양성 대조군 `grep 'exclusive create'` → `ledger.py:115` 1 hit.

| 장치 (프로토콜 §10) | 2281c85 실재 | 근거 |
|---|---|---|
| idempotency key (`ticket_id+run_id+target_id+collector_sha+protocol_sha`) | **없음** | 심볼 0 hit |
| `DUPLICATE_SUPPRESSED` 이벤트 | **없음** | 코드 0 hit · event_log 0 hit(74행) |
| target 단위 lock | **없음** | `locks/` 는 A 가 방금 생성한 빈 디렉터리; 소비 코드 0 |
| run_id | timestamp 합성 (`batch.py:358`) — 같은 target 재실행이 새 run_id 로 그냥 진행 | |
| 유일한 기존 장치 | batch 파일 `open(...,"x")` exclusive create + 체인 연속성 (`ledger.py:140`) — **batch commit 단위**이지 launch 단위가 아니다 | |

### §6.1 재발이 실제로 있었다 — B CLEAN-0 §4.1 분류 REFUTED (P1, FACT_CORRECTION 발행)

B 는 w02 의 이중 run 4건을 *"retry 가 evidence run 을 분기시킨 결과, 중복 발사 아님"* 으로 판정했다. raw 는 반대를 말한다:

| target | run A start → sealed | run B start → sealed | batch_0001 `attempts` |
|---|---|---|---|
| wtg_13ed0704… | 05:14:30 → 05:14:40 | 05:14:38 → 05:14:47 | 1 |
| wtg_9390ef32… | 05:14:40 → 05:14:47 | 05:14:47 → 05:14:54 | 1 |
| wtg_b728911c… | 05:14:47 → 05:15:00 | 05:14:54 → 05:15:06 | 1 |
| wtg_e1fadb21… | 05:15:00 → 05:15:06 | 05:15:06 → 05:15:12 | 1 |

- `attempts=1` 전건 → retry 아님 (retry 면 2).
- run B 가 run A **sealed 이전에 시작** → 한 프로세스의 순차 retry 로는 불가능. 두 개의 순차 사슬이 6~8초 간격으로 교차 = **worker_02 프로세스 2개**.
- 이중 대상 4건 = `batch_0001` target 집합 전체 → 두 번째 프로세스가 첫 batch 를 재실행하다 exclusive-create 에서 막힘. 이것이 C 인계(`ASSURANCE_HANDOFF.json research_conduct: w02 duplicate launch 4 runs quarantined`)와 일치.

**함의**: "억제 경로가 실행된 적 없다"(A BUS-F2)가 아니라 **billing 단위(실사이트 접속)에서는 억제가 없었고, batch 원장 단위에서만 막혔다**. 프로토콜 §10 이 요구하는 것은 **launch 이전** 억제다.

### §6.2 duplicate real launch 재발 조건 (현 코드 그대로 gate 가 열릴 경우)

1. 같은 `--worker NN` 명령을 두 번 실행 (셸 재시도·오케스트레이터 중복 발사·`nohup` 이중 기동) — 2026-08-27 05:14 실사례.
2. 같은 target 을 다른 worker 파티션이 중복 배정 (현재는 `mutually_exclusive` 계획으로 회피, 코드 강제 없음).
3. 첫 batch commit 실패 후 재실행 — evidence run 은 이미 실사이트 접속을 마친 뒤.
4. run_id 가 timestamp 라 "같은 target·같은 ticket·같은 collector SHA" 를 같은 작업으로 인식할 키가 없음.
5. bus `locks/` 를 코드가 읽지 않으므로 디렉터리 존재 자체는 억제력 0.

**gate 요구(REAL_TARGET pilot 전 필수, T-B-BLK-001 과 동일 결론)**: idempotency key 를 **launch 직전**에 검사·기록하고 두 번째 요청은 접속 없이 `DUPLICATE_SUPPRESSED` 를 남기는 경로 + C 가 심는 중복 발사 fixture 로 억제 검증.

## §7 A 산출의 시각 필드 — PROJECTION 이 OBSERVATION 자리에 (P3)

commit `0d83148` 의 시스템 시각은 **20:50:48 KST**. 그 커밋에 든 문서의 자기 표기 시각: manifest `created_at 20:55`, SEMANTIC_LEDGER `21:00`, PHASE_STATE `21:02`. 티켓 4건 파일 mtime **20:51:44** ↔ `created_at 21:03:00`. event_log A 행 21:02:40 / 21:03:00 (C 관측 시각 20:53 이전에 존재).
→ A 의 `created_at`/`ts` 는 시계에서 읽은 값이 아니라 외삽값이다. 데드라인(21:35)·heartbeat stale 판정(§SLA 2~3분)이 이 시각축 위에 있으면 어긋난다. **정정 요청: 시각은 `date` 출력에서 읽고, 이미 발행한 티켓은 수정하지 않는다(FACT_CORRECTION 로만).**

## §8 B CLEAN-0 completion (`T-B-CLEAN0-001`, result_sha `4ae6df0a`) 동일 SHA 검증

| B 주장 | C 판정 |
|---|---|
| G1~G5 재현 위치 | **MATCH** (C_R0_QA S-11~S-14 와 동일 좌표) |
| B-N1 probe 58건 · 분포 | **MATCH** 정확히 일치 (57/1 · 55/3 · 48/9/1 · null 58) |
| B-N2 위양성 경로 표본 실재 | **MATCH** (값 'sg','ko_KR' / '1','2') |
| B-N4 exactly-once 미구현 | **MATCH** |
| B-N5 bus git 0건 | **MATCH** |
| §1.1 bc0b7a0 에 engine/e001_runner 없음, 2281c85 가 integration base | **MATCH** (engine 파일 bc0b7a0: 0 / 2281c85: 16) |
| 코드 변경 0줄 | **MATCH** (diff vs 2281c85 = handoff 2 파일만) |
| **§4.1 이중 run 4건 = retry, 중복 발사 아님** | **REFUTED** (§6.1) |
| manifest 계수 1,265 / 791,908,794 | **MATCH** (단위 = artifacts 루트 전체, §3) |

## §9 이 감사가 확인하지 않은 것

- `batch_hash` 내용 재계산(§2), F-7 · depth §4.1(→ C_R0_QA), E000 lane 의 duplicate launch 3건 재분류(인계값 그대로, 미재검)
- `V2_1_PACK_HASHES.txt` 11개 = `SSOTV2/` 원본 = 설치본 — **확인함**(11/11 일치). 단 `docs/v2_1` 이 bc0b7a0 계보(연구 코드베이스)가 아니라 control 브랜치에만 있음 — B worker 가 SSOT 를 읽을 base 가 다르다는 점은 운영상 주의(권위 문제 아님)
- 라벨러 독립성: 아직 라벨러가 spawn 되지 않아 검사 대상 없음 — `T-A-LABEL-PREP-001` ACK 만. 검사 항목은 준비됨(producer≠B/C · 결과 미열람 · evidence ref · 사전 sha256 · split 동결)
