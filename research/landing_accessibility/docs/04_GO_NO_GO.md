# 04 — Measurement Readiness Gate 및 E001 GO 조건

**절대 규칙** E001 본수집은 Research Director 의 명시적 GO 없이 실행하지 않는다.
로컬 하네스의 자율 수행 상한선은 **E000-SMOKE 완료 + Measurement Readiness Report 제출**이다.

---

## 0. GO 판정의 성격

**`pytest green` 은 GO 조건이 아니다.**

Pilot 도 `ruff check` 통과, `pytest` 9건 통과 상태였다. 그런데 실사용군 41건 중 30건의
증거 파일이 서로 덮어써져 있었고, 아무 테스트도 그것을 잡지 못했다.

GO 를 결정하는 것은 세 문장이다.

1. **누구를 측정할지가 완전히 확정되어 있는가.**
   Wiseapp 원문 → 서비스 canonicalization → 실제 landing URL → 인증 0/1 → 카테고리가 freeze 되어야 한다.
2. **한 서비스에서 나온 증거가 절대로 다른 서비스에 붙을 수 없는가.**
   Pilot 의 가장 큰 실패가 정확히 이것이었다.
3. **지금 수집한 raw evidence 로 나중에 판정규칙이 바뀌어도 사이트를 다시 방문하지 않고 재판정할 수 있는가.**

이 셋이 성립하면 Collection GO 다.

---

## 1. Gate 목록

| Gate | PASS 조건 | 현재 |
|---|---|---|
| `pilot_archive` | Pilot raw evidence + audit journal 백업 + SHA manifest 완료 | **PASS (논리 이중화만)** |
| `source_asset_discovery` | Wiseapp 원문·KWCAG 원문·인증 소스 위치/해시 등록 | **PASS** |
| `population_source_freeze` | Wiseapp 933 원문이 모집단 Authority 로 동결 | **PASS** |
| `source_row_reconciliation` | 모든 panel 의 rank/value 가 원문과 일치, 행 손실 0 | **PASS (figure 수준)** |
| `canonical_entity` | 모든 raw row 가 정확히 하나의 canonical entity 에 연결 | PASS_PENDING_AUDIT |
| `membership_preservation` | APP/RETAIL membership 보존, 원자료 행 미삭제 | PASS_PENDING_AUDIT |
| `certification_snapshot` | 정상 종료된 A2 스냅샷 확보, 완결성 게이트가 코드로 강제 | **PASS** |
| `web_eligibility` | 모든 entity 가 0/1 + reason. 선탑재/시스템 앱 분류 완료 | NOT_RUN |
| `url_review` | web eligible 전부 공식 landing URL 확정 또는 명시적 제외사유 | NOT_RUN |
| `certification_join` | 모든 web eligible entity 가 `certified_current ∈ {0,1}` | NOT_RUN |
| `feasibility` | source refreeze 기준으로 재산출 | INVALIDATED (재산출 대기) |
| `engine_integrity` | hash ID · append-only · 1:1 evidence · PSL · 게이트 근거 기록 | NOT_RUN |
| `evidence_identity` | measured N = DOM N = AX N = Screen N = Probe N | NOT_RUN |
| `append_only` | 기존 Evidence Run 에 write 시도 시 프로그램이 **실제로 거부** | NOT_RUN |
| `judgment_semantics` | PASS/FAIL/NA/UNDET 규칙 수정 및 test PASS | NOT_RUN |
| `automation_split` | machine_confirmed / review_flag / undetermined 분리 | NOT_RUN |
| `criterion_probe_coverage` | E001 에 필요한 raw probe 필드가 전부 존재 | NOT_RUN |
| `smoke_e000` | collision 0 / wrong-reference 0 / silent loss 0 | NOT_RUN |
| `adversarial_audit` | 최신 exec SHA 대상 PASS | PASS (C002-C003) |
| `ssot_audit` | 최신 exec SHA 대상 PASS | PASS (C002-C003) |
| `open_p0` | 0 | 1 (시정 중) |

**하나라도 FAIL 이면 E001 금지.**

---

## 2. Gate 가 아닌 것

다음은 GO 조건이 **아니다.** 혼동하면 Pilot 을 반복한다.

- 측정 성공률이 높은 것 — HTTP 403 이 2건이어도 문제가 아닐 수 있다
- 테스트가 초록인 것 — Pilot 도 초록이었다
- 에이전트를 많이 돌린 것 — Pilot 은 225개를 돌리고 시정 큐를 못 만들었다
- 코드가 많은 것

중요한 것은 **레코드 손실 0 / 엉뚱한 증거 참조 0 / 파일 overwrite 0** 이다.
측정 실패는 허용하지만 **설명되지 않은 손실은 허용하지 않는다.**

---

## 3. 감사 유효성 조건

오케스트레이터는 다음을 만족하는 감사 보고서만 받는다.

```
audit.target_exec_sha == current_exec_head
audit.target_ssot_sha == current_ssot_sha
```

불일치하면 `STALE_AUDIT` 으로 버린다.

각 감사 보고서는 다음을 갖춰야 한다.

```
cycle_id / target_exec_sha / target_ssot_sha / source_authority_sha
audit_agent_version / started_at / finished_at / verdict / findings
```

### 재결 규칙

| CASE | 조건 | 처리 |
|---|---|---|
| 1 | PASS + PASS | 다음 phase directive |
| 2 | PASS + REWORK | REWORK |
| 3 | REWORK + PASS | REWORK |
| 4 | P0 finding | HARD STOP |
| 5 | auditor disagreement | **오케스트레이터가 증거를 직접 확인.** 어느 agent 의 주장도 자동 우선하지 않음 |
| 6 | READY_FOR_E001 | main promotion 가능 / E001 실행 금지 / Research Director 에게 GO 요청 |

`votes == 0` 은 `UNVERIFIED` 이며 **자동 REJECT 하지 않는다.**
Pilot 은 반증 에이전트가 죽어 votes=0 이 된 발견을 자동 기각했고, "기각 55건" 에 미검증이 섞였다.

---

## 4. Promotion Policy

exec 는 감사를 기다리지 않고 다음 cycle 을 진행할 수 있다. 파이프라인을 하드스톱으로 끊지 않기 위해서다.

그러나 `research/landing-accessibility-main` 으로의 **promotion 은 해당 SHA 가 다음을 모두 만족할 때만** 오케스트레이터가 수행한다.

```
adversarial PASS  AND  ssot PASS  AND  open_p0 == 0
```

---

## 5. 최종 STOP 보고 형식

`READY_FOR_E001` 도달 시 다음을 출력하고 모든 agent 를 대기시킨다.

```
MEASUREMENT READINESS REPORT

Population Authority:
Wiseapp source snapshot:
Panel count:
Raw ranking row count:
Canonical entity count:
APP entities:
RETAIL entities:
Web eligible:
Non-web:
Certified current:
Non-certified:
Certification denominator:
Feasibility by panel/category:

Source reconciliation mismatch:     0 required
Evidence ID collision:              0 required
Smoke measured / blocked:
Silent loss:                        0 required
Adversarial audit:                  PASS required
SSOT audit:                         PASS required
Open P0:                            0 required

FULL COLLECTION:  READY / NOT STARTED

Frozen:
  TARGET_SET_SHA / PROTOCOL_SHA / COLLECTOR_SHA / PROBE_SHA / AUDIT_DATE

Known exclusions:
Known limitations:
User decisions required:

Research Director decision:  GO / HOLD
```

---

## 6. 현재 미해결 — Research Director 결정 필요

| # | 항목 | 상태 |
|---|---|---|
| 1 | **Pilot 원증거 물리 이중화** | `/` 는 WSL ext4.vhdx, `/mnt/c` 는 NTFS 로 **논리 분리만** 확보. `/mnt/d` 는 여유 997MB 로 부족. 외장 저장장치 또는 원격 위치 지정 필요 |
| 2 | **Wiseapp 원문 조사 상세** | 표본 크기·조사 방법론의 전체 기술이 원문 본문에 없다. APP `한국인 Android+iOS 스마트폰 사용자 추정`, RETAIL `계좌이체·현금거래·상품권 제외` 까지만 확인됨 |
| 3 | **발행처 모집단 변경** | 2026-08-25 09:00 게시, 종료일 없음. 동결본을 "2026-08-26 시점 판본"으로 한정했으나 변경 내용 자체는 미확인 |
| 4 | **RQ 구조** | 이전 NO-GO 판정을 철회했다. A1 기준 feasibility 재산출 후 RQ2~4 성립 여부를 다시 판단해야 한다 |

---

## 7. E001 이전 금지 사항

- Pilot R3/R4 COMPARISON 을 "살릴 수 있나" 하며 추가 보정하지 말 것
- Pilot `targets.py` 를 수정해 새 분류체계로 재활용하지 말 것
- Main Study 와 Pilot 코드를 같은 package 에 섞지 말 것
- E000 결과를 기사 결과처럼 분석하지 말 것
- E000 실패 시 사이트별 예외코드를 계속 추가하지 말 것
  → 공통 오류면 protocol 수정, 사이트 특이현상이면 상태값으로 남긴다
- **Research Director 승인 없이 E001 을 시작하지 말 것**
