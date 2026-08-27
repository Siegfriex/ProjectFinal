# D-R0-63 — Director Control Amendment A1~A7 반영

**발행** Claude A · **작성** 2026-08-27T22:08:32+09:00 (`date` 판독값) · **assertion_type** `DECISION`
**권한** Research Director · **amends** `D-R0-62`

---

## §0 exact SHA 재확인 — Director 지시대로 full fetch 후 대조

```
ref                              Director 지정   실측(22:07)    판정
control/landing-orchestrator     2dd8440         018fa46        2dd8440 IS ancestor — 정상 전진
claude-b/clean0-v21              7b261bc         7b261bc        일치
claude-c/assurance-v21           a6b07dd         615fc68        a6b07dd IS ancestor — C 전진
claude-d/research-sandbox-v21    a53b284         a53b284        일치
claude-b/w1-guard-wiring         0e1f5f2f        860e4e80       전진
claude-b/w2-rf-detector          bd5e33d3        f76ee8ba       전진
claude-b/w3-kwcag                94cbf8b6        94cbf8b6       일치
```

**네 SHA 전부 실재하고 전부 조상이다.** Director 스냅샷은 21:53~21:56 시점에서 정확했고
이후 A·C·W1·W2 가 전진했다. **불일치가 아니라 드리프트다.**

---

## A1 — Holdout Recovery

```
full contaminated reference   26
sensitivity (PRECEDENCE_CONTESTED 3 제외)   23
primary independent evaluation (exposed 8 제외)   18
```

**`D-R0-62-1` 을 Director 결정으로 대체한다.** A 는 "부분 제외로 독립성이 복구되지 않는다" 는
이유로 26 전체 보고를 제안했으나, Director 가 **clean 18 을 primary 로** 확정했다.

### A 가 남기는 사실 주석 — 결정을 바꾸지 않되 경계를 정확히 한다

Director 는 26 을 *"full contaminated reference"* 로 명명해 26 전체가 오염 참조임을
이미 인정했다. 그 위에서 `clean 18` 의 의미를 정확히 못박는다.

```
"clean 18" 이 뜻하는 것       OVERLAP_L* / D-R0-61 경로로 노출된 8 을 제외했다
"clean 18" 이 뜻하지 않는 것   파일 수준에서 접근 불가였다는 것
                              LABELS_FROZEN.jsonl · RAW_L2 · RAW_L4 는 5b826e3(21:26:25)부터
                              control 브랜치에 있었고 holdout 26 전부의 라벨을 담았다
                              18 도 그 경로로는 물리적으로 가용했다
```

**따라서 모든 보고에 다음 한 줄을 병기한다.**

```
primary n=18 — OVERLAP/DIRECTIVE 경로 비노출.
파일 경로(LABELS_FROZEN·RAW_L2·RAW_L4)로는 26 전부가 21:26:25 이후 가용했다.
```

이것은 **validation independence 복구**이지 label definition 변경이 아니다 (Director 명시).

## A2 — Information Firewall

```
holdout 유래 per-target 정보를 절대 넣지 않는다
   A control branch · B-readable ticket · D-readable research notice · shared MLflow artifact

B / D 가 받을 수 있는 것
   aggregate holdout metric · generic error taxonomy · class-level summary

C-only
   target_id · true label · candidate pair · per-target error detail
```

**이미 노출된 이력은 삭제로 "없던 일" 처리하지 않는다.** `EXPOSED_HISTORY` manifest 에 기록한다
(`control/label/EXPOSED_HISTORY.json`). `D-R0-62-4` 의 force-push 금지와 같은 근거다.

## A3 — W2 Contamination Recovery

W2 에 즉시 요구한다.

```
1  leaked 3 target 기반 target-specific rule / threshold / exception 이 들어갔는지 attestation
2  leakage 전달 전 SHA 와 현재 SHA 의 diff
3  target name / target id / leaked candidate pair 기반 코드·fixture·rule 이 있으면 제거
4  generic RF-DT rule 자체는 holdout 에서 유래하지 않았다면 유지
```

**`C 가 diff 를 독립 검증하기 전 W2 validation PASS 금지.`**

4번이 중요하다 — B 가 이미 같은 판단을 했다. *"Stage 4 precedence 구현 자체는 RF-DT §6 계약에서
나온 것이지 holdout 에서 나온 것이 아니다."* **경합 유형이라는 일반 개념과 3건의 구체적 후보쌍을
함께 버리면 과잉 대응이다.**

## A4 — Unaffected Work Continues

```
P0 는 holdout validation integrity 에 국소적이다
W1 exactly-once / guard        계속
W3 criterion evaluator          계속
W4 Axis C rework                계속
broad rollback                  금지
```

W2 도 **비오염 부분은 계속**한다 — 멈추는 것은 validation PASS 이지 구현이 아니다.

## A5 — MLflow Control Layer

```
MLflow 는 SSOT 가 아니다. 관측계층이다
A 는 직접 실험하지 않고 Decision Run 만 생성한다
```

필수 A run:

```
HOLDOUT_RECOVERY_DECISION   ← 본 결정으로 생성
W1_W2_JOINT_GATE            대기
W3_ACCEPTANCE               대기
W4_ACCEPTANCE               대기
OFFLINE_VALIDATION_GATE     대기
REAL_PILOT_GO_NO_GO         대기
```

각 A run 에 source B/C/D run_id 와 Git SHA 를 연결한다.

## A6 — D Research Broadcast

```
D 는 계속 NON_CANONICAL Research Lab 이다
D 는 A/B/C 에게 직접 directive 를 보내지 않는다
D 의 VALIDITY_RISK_CANDIDATE  →  C 자동 replication queue
C 가 CONFIRMED 한 result-affecting finding 만  →  A decision queue
```

**A 가 D 의 모든 finding 을 직접 읽어 병목이 되지 않게 한다.**
현재 미처리인 `D-RESEARCH_FINDING-001` · `D-ATTESTATION-001` 은 이 경로로 재라우팅한다.

## A7 — Next Gate

REAL pilot 전 필수 전건:

```
1  holdout recovery accepted
2  W1 C PASS
3  W2 clean-18 C holdout validation
4  unsafe endpoint FP = 0
5  W3 C independent validation
6  W4 same-SHA C validation
7  A explicit GO
```

```
이 전 REAL_TARGET 금지
새 governance hardening 이나 adjacent audit 을 critical path 에 추가하지 않는다
```

**마지막 줄은 A 에게 적용되는 구속이다.** A 는 이후 새 governance 산출물을 만들지 않고
위 7개 게이트 판정에만 집중한다 (`D-R0-44` 재확인).

---

## §이 결정이 검증하지 않은 것

```
W2 오염이 실제 코드에 반영됐는지   W2 attestation + C diff 검증 대기
clean 18 의 파일 수준 청정성       확보되지 않았다 — §A1 주석 참조
D finding 의 내용                 C replication queue 경유 전까지 A 는 읽지 않는다
```
