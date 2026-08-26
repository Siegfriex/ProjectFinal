# PHASE-ORIENTED EXECUTION DIRECTIVE v5.0

**적용 시작** 다음 세션
**전제 baseline** `research/landing-accessibility-main @ 5a9015d1e95b15304aaf53a73efb475934610b82` (PROM-002)
**종착점** `READY_FOR_E001` — 그 지점에서 자동화를 멈추고 Research Director에게 GO/HOLD를 요청한다.

이 헌장은 v3 / v3.1 / v4.0 을 대체하지 않는다. 그 위에서 **Phase 단위로 실행**하는 방법을 정한다.

---

## 0. 승계되는 불변 규칙

| 규칙 | 출처 |
|---|---|
| `MAX_UNAUDITED_EXEC_CYCLES = 1` | v3.1 §2 |
| 신뢰경계 `EXECUTED → PRECHECK → INDEPENDENTLY_AUDITED → RECONCILED → PROMOTED` | v3.1 §1 |
| promotion 조건: adversarial PASS AND ssot PASS AND open_p0 = 0 | v3.1 §5 |
| Pilot READ_ONLY (`lock_branch`) | v3 |
| 인증은 모집단이 아니라 attribute | 분석 SSOT §3 |
| UNDETERMINED를 PASS로 흡수 금지 | 분석 SSOT §30-6 |
| 목적함수 = `ZERO E001-BLOCKING FINDINGS` | v4.0 §2 |

---

## 1. Phase 정의

### P-A ANALYSIS FOUNDATION

승격된 baseline만으로 가능하다. **웹 접속이 필요 없다.**

```
1. Mapping Layer          SSOT §5.2 명세 ↔ 현재 state/*.parquet
2. EDA-00                 Frame & Provenance Audit
3. EDA-01                 Wiseapp Source Structure
4. Analysis Manifest      분석 재현 계약
5. independent audit      adversarial + ssot
6. promotion              PROM-003
```

**핵심 원칙: source state artifact를 rename/migrate 하지 않는다.**
`state/*.parquet` 은 그대로 두고 **매핑/머티리얼라이제이션 레이어**를 얹는다.
SSOT §5.2의 `dim_panel` / `fact_source_ranking` / `dim_measurement_entity` /
`bridge_source_membership` 은 뷰로 제공한다.

EDA-00·EDA-01의 산출물은 **기술통계와 계보 검증**이며 접근성 결과가 아니다.

### P-B TARGET FRAME CLOSURE

```
1. C013 WIP 복원 및 검토   87a0464e — UNVERIFIED, 재검증 대상
2. web eligibility        71건 판정 (06 §2-1 어휘)
3. official landing URL   WEB_SERVICE 에 대해서만
4. final target frame     그룹 CONFIRMED / SPLIT
5. EDA-02                 Web Eligibility & Target Frame
6. audit → promotion
```

**E001-blocking P2 4건을 여기서 닫는다.**
`eligibility-basis-fields-narrower-than-06` / `a1-raw-payload-files-not-hash-registered` /
`queue-membership-still-hand-set` / `merge-decision-merges-nothing`

URL 확인 접속은 허용하되 **DOM/AX/screen/probe 저장 금지**(그것이 E001이다).

### P-C CERTIFICATION & FEASIBILITY

```
1. certification join     certified_current ∈ {0,1}
2. certification reach    도달률
3. feasibility            A1 기준 재산출
4. EDA-03                 Certification Reach
5. audit → promotion
```

`certified_current = 1 ⟺ valid_on_audit_date AND target_scope_match AND service_identity_match`.
**등록도메인 일치만으로 1을 주지 않는다.**
`AMBIGUOUS` 를 최종 분석 데이터에 남기지 않는다 — QA에서 0/1로 해소한다.

RQ2/RQ3 생존 여부를 **여기서만** 계산한다. 결과가 `NOT_FEASIBLE` 이어도
**Research Director 승인 없이 RQ 구조를 바꾸지 않는다.** 추천안만 기록하고 P-D를 계속한다.

### P-D MEASUREMENT READINESS

```
1. protocol freeze        PROTOCOL_SHA
2. collector              Pilot 로직 선택 포팅 (직접 import 금지)
3. probe                  PROBE_SHA
4. evidence identity      observation_id = hash(service_id + url + date + protocol)
5. append-only            실행 경로에서 강제
6. judgment semantics     FAIL > UNDET > PASS > NA 우선순위
7. automation split       machine_decidable / review_flag / undetermined
8. criterion coverage     E001에 필요한 raw feature 전수
9. SHA freeze             TARGET_SET / PROTOCOL / COLLECTOR / PROBE / AUDIT_DATE
10. audit → promotion
```

**E001-blocking P2 2건을 여기서 닫는다.**
`verify-run-mislabels-mode-and-symlink-bypasses-relpath-guard` /
`gitignore-evidence-pattern-single-level-only`

### P-E E000 & READY_FOR_E001

```
1. E000 smoke                8~12건, 위험 케이스 의도적 포함
2. adversarial failure injection  게이트가 실제로 잡는지 반례 주입
3. SSOT audit
4. final readiness report    FINAL_CLOSURE_REPORT.{md,json}
5. STOP
```

E000 통과 조건: `collision 0 / wrong-reference 0 / silent loss 0 / overwrite 0`.
측정 실패는 허용하지만 **설명되지 않은 손실은 허용하지 않는다.**

### GO 이후 (승인 전 착수 금지)

```
P-F E001 Evidence Collection
P-G J001 Judgment + Human Review
P-H Outcome EDA (EDA-04 ~ EDA-11)
P-I Publication Claim Registry + Article
```

---

## 2. Phase Gate 운영

각 Phase는 **하나의 gate**로 닫는다. Phase 내부 micro-task마다 승인을 요청하지 않는다.

```
directive → executor → adversarial ∥ ssot → reconciliation → promotion → 다음 Phase
```

Phase 내부에서 state-changing 커밋이 여러 번 나올 수 있으나,
**감사받지 않은 커밋이 2개 이상 쌓이면 안 된다**(`MAX_UNAUDITED_EXEC_CYCLES = 1`).

### 실패 정책

```
P0                     HARD STOP
P1                     현재 Phase 내부에서 수정 후 재감사
E001-blocking P2       현재 Phase 내부에서 수정
non-blocking P2        debt ledger 로 이관하고 계속 진행
```

사이트 몇 개가 차단되는 것은 실패가 아니다.
`silent loss` / `wrong identity` / `wrong evidence` / `unexplained exclusion` /
`unresolved certification status` / `provenance break` 는 실패다.

---

## 3. 사용자 개입 정책

다음은 스스로 해결한다 — 구현 세부, P2 triage, URL 증거 검증, 재시도, 감사 재결.

**mandatory stop은 `READY_FOR_E001` 하나뿐이다.**

RQ feasibility 결과가 나와도 추천안만 기록하고 Measurement Readiness를 계속 진행한다.

---

## 4. 분석 레이어 원칙 (SSOT §30 준수)

1. **Source와 Outcome 분리** — Wiseapp는 사용 맥락, KWCAG는 접근성 outcome
2. **Entity와 Web Target 분리** — 원자료 의미 보존 + 측정 중복 제거
3. **인증은 Attribute** — 모집단을 정의하지 않는다
4. **Service Equal Weighting** — unique web target 1개 = 1표
5. **원천 패널 보존** — 임의 재분류보다 Wiseapp panel/domain/axis 우선
6. **PASS와 Unknown 분리** — 미관측·불확정은 충족의 증거가 아니다
7. **Evidence와 Judgment 분리** — raw feature 보존, 판정규칙 versioning
8. **통계보다 계보 우선** — 분모·대상·증거가 불명확하면 산출하지 않는다
9. **조건부 비교** — 인증 O/X 비교가 성립하지 않아도 연구는 성립한다
10. **인과표현 금지** — 관측 연구다

단일 "접근성 점수"를 만들지 않는다.
`confirmed_fail_rate` + `undetermined_share` + `decision_coverage` 를 함께 쓴다.
bootstrap은 모집단 CI가 아니라 **서비스 구성 변화에 대한 stability analysis** 로만 사용한다.

---

## 5. 절대 금지

- Research Director GO 이전 **E001 실행 / target fetch / evidence 디렉터리 생성**
- Pilot 수정 (`research/refcohort/**`)
- legacy invalidated source 사용 (기존 xlsx)
- C013 WIP를 authoritative input으로 사용
- `state/*.parquet` destructive rename
- 인증목록으로 모집단 확장
- UNDETERMINED laundering
- 승인 없는 main promotion
- 승인 없는 RQ 구조 변경
