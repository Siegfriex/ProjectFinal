# R0 — RECOVERY CONTRACT FREEZE v2.1

**ID** `LA-R0-CONTRACT-2.1` · **발행** Claude A · **assertion_type** `DECISION`
**base** `control@0d831489` · **작성** 2026-08-27 20:58 KST (실측)
**상태** `FROZEN_PENDING_C_CONTRADICTION_CHECK`

> **이 문서는 연구계약이다.** 새 endpoint 도 새 archetype 도 발명하지 않는다.
> SSOT v2.1 과 RF-DT v2.1 에 이미 있는 것을 **실행 가능한 계약으로 고정**할 뿐이다.
> 계약이 사실을 만들지 않는다 — 구현 여부는 B 가, 검증은 C 가 한다.

---

## §0 이 freeze 가 여는 것과 열지 않는 것

```
연다      B 의 W1 / W3 / W4 착수, W2 의 rule-DT 부분 착수
열지 않음  W2 의 semantic/NLP calibration  → label freeze 이후
열지 않음  REAL_TARGET                    → 여전히 NO-GO
```

`R0_GO` 의 정식 발효는 C 의 contradiction check 통과 시점이다. 그 전까지 B 는
**되돌릴 수 있는 구현**만 진행하고 threshold·정의를 확정하지 않는다.

---

## §1 Guard — candidate/state-level

**`D-R0-01`** target-level `login present ⇒ Scout kill` 을 **폐기**한다.
안전성은 target 이 아니라 **activation candidate 와 current state** 수준에서 판단한다.

**`D-R0-02`** candidate action mask 는 SSOT §7.5 의 9상태를 그대로 쓴다.

```
SAFE · AUTH_ENTRY_ALLOWED_CONDITIONALLY · FORBIDDEN_CREDENTIAL_INPUT
FORBIDDEN_TRANSACTION · FORBIDDEN_PERSONAL_DATA · FORBIDDEN_CAPTCHA_BYPASS
DISABLED_OR_INERT · BLOCKED_BY_OVERLAY · UNKNOWN
```

Scout 는 `SAFE` 또는 **현재 archetype 에서 허용된** `AUTH_ENTRY` 만 확장한다.

**`D-R0-03`** 존재와 행동을 분리한다.

| | 처리 |
|---|---|
| login control **존재** | raw feature / candidate annotation. **terminal 아님** |
| login candidate **활성화** | archetype + current path 에 따라 조건부 허용 |
| credential field 입력 | **절대 금지** |
| login submit | **절대 금지** |

**`D-R0-04`** auth gate 가 endpoint 가 되는 archetype 은 **둘뿐**이다.

```
FINANCIAL_ACTION_ENTRY   LOGIN 또는 IDENTITY_VERIFICATION gate 가 endpoint 가 될 수 있음
COMMUNICATION_ENTRY      LOGIN gate 가 endpoint 가 될 수 있음
그 외 5개 archetype      auth gate 는 기능 endpoint 가 아니다
```

그리고 **chosen path 가 실제로 그곳에 도달했을 때만** gate observation 이다.
정의상 도달 가능하다는 것은 도달했다는 뜻이 아니다 (`DEFINITION ≠ OBSERVATION`).

**`D-R0-05`** CAPTCHA. DOM 내 코드·문구 존재는 **terminal 이 아니다.**
현재 chosen path 의 다음 진행을 막는 **visible / active challenge 가 실제로 나타난 순간**만
`CAPTCHA` terminal 로 기록한다. 해결·우회 금지.

**`D-R0-06`** 구매·결제 control 의 **존재 관측은 허용**, **활성화는 금지**.
`ITEM_DETAIL` 에서 거래 control 의 존재는 상세 endpoint 확인의 evidence 가 될 수 있다.

> **완화하지 않는 것**: prohibited action set 자체는 그대로다. 이 계약은 **guard 의 입도만
> 정밀화**한다. 금지 행위 목록을 줄이지 않는다.

---

## §2 Task definition wiring — 59/59

**`D-R0-07`** 새로 만들지 않는다. **existing definition 의 exact field lineage 를 복원**한다.

실행 경계를 통과해야 하는 필드:

```
task_id · region_definition · region_signal_type
          endpoint_definition · endpoint_signal_type
```

**`D-R0-08`** 수용 기준은 **"측정 가능해진 개수"가 아니라 lineage 보존율 59/59** 다.
`default_task_definition()` 이 `None` / `CODEBOOK_PENDING` 을 하드코딩하는 경로는 제거한다.

**`D-R0-09`** `CODEBOOK_PENDING` 은 **부재(미도달)** 이지 **거부** 가 아니다.
두 개념을 같은 필드·같은 단어로 표현하지 않는다. 묶으면 1건짜리 실제 거부가
54건짜리 미도달을 정당화하는 데 쓰인다.

---

## §3 Representative Function — RF-DT v2.1

**`D-R0-10`** 대표기능 매핑은 `01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md` 를 따른다.
2층 구조: **Layer P (prior)** 는 후보를 만들고, **Layer O (observed interaction)** 가 확정한다.
business domain 과 observed task shape 가 충돌하면 **observed 가 이긴다.**

**`D-R0-11`** archetype 은 **일곱 개로 닫혀 있다.** 신규 archetype 금지.

```
QUERY · CONTENT_OPEN · ITEM_DETAIL · PLACE_LOOKUP
COMMUNICATION_ENTRY · FINANCIAL_ACTION_ENTRY · UTILITY_ENTRY
```

**`D-R0-12`** Evidence precedence (Stage 4) 를 그대로 쓴다:
actual user-operation structure > public primary interaction surface > DOM/AX/form state change
> source/business prior > service name token.

유일 후보 → RULE 확정. 강한 후보 2개 이상 → NLP fallback. evidence 없음 → `AMBIGUOUS_UNRESOLVED`.
**force-map 금지.**

**`D-R0-13`** NLP fallback 은 **deterministic ambiguity 가 발생한 뒤에만** 쓴다.
출력은 일곱 archetype 밖으로 나갈 수 없다.
**threshold 를 임의 숫자로 영구 선언하지 않는다** — independent label 의 calibration split 에서 정한다.
VLM 은 icon/image/canvas/visual-hierarchy ambiguity 에만. Human Final 최대 5건.

---

## §4 Real-site detector — synthetic marker 제거

**`D-R0-14`** frozen signal family 를 실제 DOM/AX 에서 구현한다.

```
DOM_AX_ROLE · FORM_STRUCTURE · URL_PATTERN   (필요 시 MEDIA_STATE / GATE_SIGNAL)
```

**`D-R0-15`** `data-region` / `data-endpoint` marker 경로는 **보완이 아니라 제거 또는 비활성화**한다.

근거 — **`T-B-FC-001` (B, P1) 을 A 가 채택한다.** B 의 전수 재집계(n=58 probe, 이전 표본 n=14):

```
declared_endpoints  길이 0 = 57   (길이 2 가 1건)
declared_regions    길이 0 = 55   (길이 1 이 3건)
search_inputs       길이 0 = 48   (1~2개가 10건)
body_endpoint_reached  null = 58 / 58
```

**"우연 일치 위양성"은 가능성이 아니라 표본에 실재하는 조건이다.** marker 경로를 남겨두면
실사이트에서 4건이 marker 로 성립해버린다. 따라서 제거가 계약이다.

**`D-R0-16`** `*_signal_type` 은 프로덕션 판정에서 **실제로 소비**돼야 한다.
이는 "복구"가 아니라 **프로덕션 최초 배선**이다. 용어를 정확히 쓴다.

**`D-R0-17`** 픽스처 PASS 는 갭2 를 증명하지 못한다. 픽스처가 심는 마커가 현행 detector 가
읽는 바로 그것이기 때문이다. **모든 PASS 문서는 "이 게이트가 검증하지 않은 것" 절을 포함한다.**

**`D-R0-18`** 갭1(wiring)과 갭2(detector)는 **한 게이트에서 함께 검증**한다.
중간 재수집을 넣지 않는다 — 한쪽만 고치고 재수집하면 결과가 오늘과 동일하고 접속 예산만 쓴다.

**`D-R0-19`** 최소경로는 bounded BFS + Path Freeze + Replay 를 유지한다.
`minimal` = **동결된 search space 안에서의** 최소 activation 수.
scroll / typing / redirect / passive wait / popup dismissal 은 depth 에 합산하지 않는다.

**`D-R0-20`** partial depth 를 보존한다. endpoint 미도달이라도 **region 이 관측되면 NED 는 남긴다.**
IED / MPFED 만 NULL.

---

## §5 KWCAG evaluator

**`D-R0-21`** **frozen older-relevant subset 만.** 연구 중 subset 확대 금지.
criterion 마다 `Applicability → Required evidence slots → Expectation → Outcome`.
각 criterion 은 raw evidence 와 **exact evaluator version** 에 연결한다.

**`D-R0-22`** 자동화 우선순위: browser-native/AX → deterministic geometry/CSS → semantic text/embedding
→ VLM → Human Final. AI 는 ambiguity 에만 쓴다.

**`D-R0-23`** 금지 — measurement failure 를 FAIL 로 전이 / evidence 없는 PASS·FAIL 생성 /
UNDETERMINED 세탁 / service-level 결과를 criterion row 로 복제.

---

## §6 Axis C — page-level 과 task-level 을 섞지 않는다

**`D-R0-24`** page-level `OverlayCoverage` 는 기존 evidence 를 **재사용**한다 (재측정 아님).
task-specific `PrimaryActionOcclusion` 은 **task binding(D-R0-07 + D-R0-14) 복구 이후**에만 재계산·재검증한다.

**`D-R0-25`** semantic interrupt classification 은 `deterministic rule → text/NLP → VLM → abstain` 순.
**semantic 분류가 geometry 값을 바꾸지 않는다.** dismissal 전후 evidence 를 섞지 않는다.

---

## §7 Independent labeler

**`D-R0-26`** gold label producer 는 **B 도 C 도 아니다.** A 가 별도 worker 4~6 을 조직한다.
labeler 는 통계결과·detector 결과를 보지 않고 DOM/AX/evidence 만 읽는다. row 마다 evidence ref 필수.

**`D-R0-27`** 통합 label 파일을 **detector calibration 이전에** SHA256 동결하고,
동결 해시를 게이트 판정문에 기재한다. calibration / holdout split 도 사전 동결.
B 는 calibration 만 사용하고 holdout 을 찾거나 읽지 않는다. C 가 holdout 을 독립 검증한다.

**`D-R0-28`** 모집단 — `RECONCILE_A_B_CLEAN0.md §4` 의 정정을 반영한다.

```
주모집단   n = 56   observation 이자 web_target_group (여기서는 1:1, 확인됨)
제외       superseded retry 4 observation (타깃 누락 아님 — 커버리지 56/56)
제외       빈 stub 디렉터리 6
sensitivity-only   E000 9 observation / 6 고유 타깃 — 주 결과와 미합산
```

---

## §8 Exactly-once — `T-B-BLK-001` 에 대한 A 의 결정

**`D-R0-29` `GO`** — exactly-once 구현을 **W1 범위에 포함**한다.

이것은 새 요구가 아니다. SSOT §15 의 `REAL_START_READY` 조건 7번이
*"evidence manifest 및 exactly-once launch 검증"* 을 이미 요구한다. B 의 발견은
그 조건이 **현재 미충족임을 실측으로 확인**한 것이다.

```
idempotency_key = ticket_id + run_id + target_id + collector_sha + protocol_sha
target 단위 lock          .agent_bus/landing_v2/locks/  (A 가 디렉터리 생성 완료)
중복 요청                 launch 하지 않고 DUPLICATE_SUPPRESSED event
억제 테스트               같은 key 2회 요청 → 1회만 launch
```

**A 는 B 의 입장을 지지한다** — 미구현 상태에서 REAL_TARGET pilot 을 수락하지 않는 것이 옳다.
`batch.py` 의 timestamp 합성 `run_id` 는 idempotency key 가 아니다.

> `DUPLICATE_SUPPRESSED` 가 event_log 에 0건인 것은 **억제가 작동했다는 뜻도, 실패했다는 뜻도
> 아니다. 경로가 실행된 적 없다는 뜻이다.** 세 가지를 구분한다.

---

## §9 Bus 가시성 — `T-B-BLK-002` / `ISSUE-A-001` 에 대한 A 의 결정

**`D-R0-30`** bus 는 **로컬 transport 로 유지**하고, **각 plane 이 자신의 outbound 를 자기 브랜치에
Git-tracked mirror 로 남긴다.**

```
A   control/clean0/PHASE_STATE.json          (phase · plane SHA · open blockers · next gate)
    control/r0/**                             (계약 · 결정)
B   handoff/bus_mirror_b/**                   ← B 가 fcf403a 에서 이미 선행 구현. A 가 이를 정본 패턴으로 채택
C   assurance/bus_mirror_c/**                 (동일 패턴)
```

**왜 공유 디렉터리가 아닌가**: 프로토콜 §2 는 *"같은 파일을 두 worker 가 동시에 수정하지 않는다"*
를 요구한다. plane 별 mirror 는 write 충돌이 구조적으로 불가능하다.

**왜 bus 전체를 Git 에 넣지 않는가**: 기존 `.gitignore` 사유
*"orchestration transport, not research authority (canonical = git artifacts/SHA)"* 는 유효하다.
heartbeat 노이즈가 연구 이력에 섞이면 §16 의 가독성이 오히려 나빠진다.

**§16 충족 판정**: mirror 3종 + `PHASE_STATE.json` 으로 외부 watcher 는 GitHub 만 보고
현재 phase / 각 plane exact SHA / 열린 blocker / 발행 티켓 / Git 밖 raw artifact / 다음 gate
를 알 수 있다. **이 결정은 되돌릴 수 있다** — Research Director 가 bus 전체 추적을 원하면 전환한다.

---

## §10 Pilot acceptance gate

**`D-R0-31`** stratified real pilot 8~12 targets, 가능하면 일곱 archetype 전부 포함.

**판정 기준은 결과의 좋고 나쁨이 아니라 systemic measurement mismatch 의 유무다.**

```
HOLD 조건 (하나라도 해당하면 full run 금지)
  unsafe action path 가 가능
  synthetic marker 의존 잔존
  endpoint definition 을 observed endpoint 로 혼동
  label leakage
  evidence identity mismatch
  duplicate real launch 억제 실패
  단일 사이트 실패는 HOLD 조건이 아니다 — isolate 한다
```

**`D-R0-32`** detector release gate (연구 threshold 아님, engineering 기준임을 문서에 명시):
unsafe endpoint false-positive = 0 · 모든 mapped leaf 에 evidence trace ·
unresolved 를 force-map 하지 않음 · holdout archetype agreement ≥ 0.85 · holdout coverage ≥ 0.75.
미달 시 full REAL_TARGET 을 막고 pilot subset 만 허용한다.

---

## §11 이 계약이 정하지 않는 것

```
구현 방식              B 의 재량
검증 방법              C 의 재량
detector 의 threshold  label calibration 이 정한다 — A 가 숫자를 지정하지 않는다
분석 결과              계약은 결과를 예약하지 않는다
```

**A 의 권위는 T4 다.** 이 문서의 어떤 문장도 T1(코드·raw)·T2(재현계산)·T3(정의)을 덮지 않는다.

---

## §12 이 freeze 가 검증하지 않은 것

```
G1~G4 의 코드 좌표     A 는 독립 재현하지 않았다. C 의 T-A-R0-C-001 대상
B 의 전수 재집계 n=58  A 는 채택했으나 재계산하지 않았다. C 의 독립 재계산 대상
B 인벤토리 fcf403a     C assurance 전까지 ACCEPT 아님 (self_approved=false)
계약 내부 모순         C 의 contradiction check 미완
```

**이 절이 비어 있으면 이 문서는 발행되지 않았을 것이다.**
