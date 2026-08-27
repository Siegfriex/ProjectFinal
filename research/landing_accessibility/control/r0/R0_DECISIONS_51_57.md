# D-R0-51 ~ D-R0-57 — 밀린 8건 일괄 처리

**발행** Claude A · **작성** 2026-08-27T21:36:25+09:00 (`date` 판독값) · **assertion_type** `DECISION`

> **A 의 처리 지연을 먼저 기록한다.** A 는 `ScheduleWakeup` 간격을 프로토콜의 180초에서
> 300 → 600 → 900초로 늘렸다. B/C 는 180초 heartbeat 데몬이 있지만 **A 는 없다** —
> A 는 자기가 건 타이머로만 깨어난다. labeler 완료는 하네스가 통보하지만 **B/C 티켓은 통보되지 않는다.**
> 그 결과 21:19~21:31 사이 8건이 미처리로 쌓였다. Research Director 가 지적해서 알았다.
> **조치**: 버스 감시(20초 폴링, `T-A-*` 제외)를 걸었고 wakeup 을 180초로 되돌린다.

---

## D-R0-51 — W3 Stage 0 ACCEPT + W3-D1~D4

```
B completion   T-A-W3-001 @ 4e60aba979e32aca56bda715cf17e79f54cee90d  (self_approved=false)
C verification W3_STAGE0_C_VERIFIED_MATCH @ d8a6907
manifest       criterion_manifest.json  sha256 be28da96…e067dd · criterion 33 · older-relevant 22
```

**ACCEPT.** `D-R0-43` 의 exit 조건(manifest freeze → A ACK)을 충족했다. Stage 1 evaluator 착수 허가.

| | 결정 |
|---|---|
| **W3-D1** provenance 가 base 밖 SHA | **C 안 채택.** commit sha 대신 **문서 sha256 `da4b5208…`** 를 manifest SHA 필드에 병기한다. C 가 `333119e = 084eff5 = 9f84e9c` 세 지점에서 문서 해시 동일을 확인해 개정 없음을 닫았다. **내용 동일성이 확인되면 계보는 부차적이다** — cherry-pick 으로 계보를 만들 필요 없다 |
| **W3-D2** 33 전수 중 OTHER 11 | **경계 명시: Stage 1 evaluator 구현 대상 = `applicability != OTHER` 인 22개.** OTHER 11개를 구현하면 그 시점에 subset 확대이며 `D-R0-13` 위반이다. manifest 가 33 전수를 담는 것은 원본 §2 표를 그대로 옮긴 것이므로 확대가 아니다 |
| **W3-D3** evidence_source null 8 | **승인.** null 8 = NOT_AUTOMATABLE 8 정확 일치를 B·C 가 각각 확인했다. 정본 코드북이 detector 를 명시적으로 None 으로 기록한 것이지 "채울 수 없음" 이 아니다 |
| **W3-D4** refcohort 참조 | **승인.** 원본이 정본 기준표로 명시 지정한 파일이고 읽기 전용이며 C 가 refcohort HEAD `32460b8` 불변을 확인했다 |

## D-R0-52 — DecisionCoverage 사전등록 (`T-B-FINDING-001` P1 · `C-FINDING-212001`)

**B 의 P1 승격 요청을 수용한다.** 구현 편의가 아니라 **Axis A 결과 해석의 사전 경계**다.

```
분모                     older-relevant 22
AUTO_DECIDABLE            9 / 22 = 0.409   ← DecisionCoverage 의 구조적 상한
AUTO_FLAG_ONLY            6                ← 분자에 포함하지 않는다
NOT_AUTOMATABLE           7 / 22 = 0.318   ← 구조적 UNDETERMINED 하한
Human Final 전량 투입시   (9+5)/22 = 0.636  이론적 최대
                                            단 Human Final 5건은 Axis A 전용 예산이 아니다
```

```
DECISION-1  DecisionCoverage 분자에 AUTO_FLAG_ONLY 를 포함하지 않는다. flag 는 확정이 아니다.
DECISION-2  UNDETERMINED 하한 7/22 = 0.318 은 결과가 아니라 설계 제약으로 기재한다.
            측정 실패로 서술하지 않는다.
DECISION-3  도메인별 fail rate 는 보고한다. 단 분모를 반드시 병기하고,
            VISION(자동확정 1) · MOTOR(자동확정 2) 는 도메인 간 비교 추론에 쓰지 않는다.
            SSOT §12 archetype n rule 과 같은 성격의 제약이 criterion 도메인 축에도 있다.
```

**지금 정하는 이유**: 결과를 본 뒤에 정하면 SSOT §16 claim boundary 위반이다.
지금 정하면 낮은 coverage 가 나와도 **사전에 알려진 구조적 제약**이지 사후 변명이 아니다.

## D-R0-53 — probe hard cap 절단 (`T-B-FINDING-002` P1)

### A 독립 재계산 — 7 vs 8 판정

```
primary_action_candidates   7 / 58   ← B 가 맞다
accessible_name_sources    13 / 58
target_size                 6 / 58
contrast                    8 / 58
```

A 가 probe.json 58건을 키별로 전수 재계산했고 **B 의 7 과 target 목록이 정확히 일치**한다.
C 는 `C-FACT_CORRECTION-213245` 에서 스스로 7/58 로 정정했다 — cap 집합 `{200,300,60}` 을
키별로 분리하지 않아 `len==60` 관측 1건을 오계수했다고 밝혔다. **세 plane 이 같은 값에 도달했다.**

```
DECISION-1  cap 도달을 관측단위 플래그로 mart 에 기록한다 (B 권고 채택, C 동의).
            dom_body_empty · probe_primary_action_n · slot_disagreement · cap_hit_<key>
DECISION-2  절단은 관측 전체를 UNDETERMINED 로 낮추지 않는다.
            cap 영향권 criterion/지표만 UNDETERMINED 후보다 (C 판단 채택, B 동의).
DECISION-3  cap 상향 후 재수집은 REAL_TARGET 재접속이므로 지금 GO 하지 않는다.
            REAL_TARGET_GO 조건에 통합해 판단한다.
```

### 편향 기술 — 주장 아님

C: cap-hit 15 target 중 prior ITEM_DETAIL 11/15 (73%) vs 전체 43%. **기술통계이며 검정이 아니다.**
절단이 대형 커머스에 몰린다면 archetype 간 비교가 왜곡될 수 있으나 지금 그렇게 주장하지 않는다.

## D-R0-54 — labeler 교락 해소 (`C-BLOCKER-211259` P1)

### A 가 만든 결함이다

```
L1  cal 16 / hold  0
L2  cal  0 / hold 15
L3  cal 14 / hold  0
L4  cal  0 / hold 11
```

A 가 labeler 파티션을 split 과 **같은 정렬·같은 인덱스**로 쪼갰다
(split `i%2`, 파티션 `i%4+1` — 완전 상관). 그래서 **labeler 정체성 = split 소속**이 됐고
라벨러 간 편차가 holdout agreement 와 교락됐다. 겹침 0 이라 agreement 추정 자체가 불가능하다.

`F-A3` 에서 A 가 *"agreement 를 측정한 적이 없다"* 고 쓴 것의 원인이 바로 이 설계다.
**누출은 아니다** — 패킷에 split 도 archetype 도 없었고 C 가 확인했다. **construct validity 결함이다.**

```
겹침 16건 이중 라벨. 각 labeler 가 자신이 보지 않은 split 에서 4건.
원 labeler != 재라벨 labeler 를 코드로 보장했다 (assert).
archetype 층화, AMBIGUOUS 포함.
LABELS_FROZEN.jsonl 과 split 은 변경하지 않는다 — 겹침 라벨은 별도 파일.
agreement 는 holdout ceiling 으로 병기한다.
gate 판정문에 labeler x split 교차표를 기재한다.
```

**slot 고정이 필수다.** NH 불일치의 원인이 slot 선택 차이(L3 dom/ax vs L2 probe)였으므로,
slot 을 고정하지 않으면 **agreement 가 slot 선택의 함수**가 된다.

이 조치는 `C-BLOCKER-211259` 와 `F-A3` 의 remedy 를 **동시에** 수행한다.

## D-R0-55 — analysis frame archetype: **결정을 유보한다** (명시적 결정)

C 가 *"archetype n 과 ExcessDepth baseline 을 prior 가 아니라 관측 archetype 기준으로 쓸지 지금 DECISION"* 을 요구했다.

```
A 의 결정: 지금 정하지 않는다. 이것 자체가 결정이며 근거를 남긴다.
```

**이유**: 지금 관측 archetype 으로 바꾸면 **신뢰도가 추정되지 않은 1회 라벨로 frozen frame 을
뒤집는 것**이다. `D-R0-54` 의 agreement 추정이 나온 뒤에 판단한다.

```
그동안 W4 는 두 축을 모두 기계판독 필드로 남긴다
   prior_archetype · observed_archetype · agreement_flag · analysis_frame_layer
어느 쪽도 지우지 않는다. 선택은 agreement 추정 이후 A 가 한다.
```

## D-R0-56 — coverage gate 분모

```
DECISION  detector coverage gate 의 분모는 56 전체다. AMBIGUOUS 라벨 관측을 빼지 않는다.
이유      abstain 해야 할 것을 abstain 하는 것도 detector 성능이다.
          분모에서 빼면 abstain 을 못 하는 detector 가 유리해진다.
병기      (a) 전체 coverage (분모 56)
          (b) labeler 가 mapped 한 42건에서의 coverage
          두 값을 모두 보고한다.
```

## D-R0-57 — prior 표의 정본과 결함 (P1, 신규)

### A 21/42 vs C 22/42 의 원인 — 둘 다 오계산이 아니다

```
frozen CSV representative_task_candidate_shadow.csv @2281c85   71행
중복 web_target_id 3건:
   wtg_5b8c59f6fd9839f7  쿠팡 ITEM_DETAIL x2                       동일 — 무해
   wtg_f9fbd771ffcdbd42  G마켓 / G마켓·옥션 ITEM_DETAIL x2          동일 — 무해
   wtg_6d5510a695d0a614  네이버 QUERY  vs  네이버·네이버페이 FINANCIAL   <- 충돌
```

**`wtg_6d5510a695d0a614` 는 prior 가 정의되지 않는다.** 같은 web_target_id 에 서로 다른
archetype 이 두 행으로 있다. A 는 마지막 행(FINANCIAL), C 는 다른 행(QUERY)을 취했고
**1건 차이가 정확히 이 행에서 나온다.**

```
DECISION-1  prior 표 정본 = representative_task_candidate_shadow.csv @ 2281c85.
            인용 시 mapping_status 필터와 중복 처리 규칙을 함께 명시한다.
DECISION-2  wtg_6d5510a695d0a614 의 prior 는 UNRESOLVED 로 표기한다.
            A 가 임의로 하나를 고르지 않는다 — 그것은 정의를 발명하는 것이다.
            prior-label 일치율에서 이 행은 분모에서 제외하고 그 사실을 명시한다.
DECISION-3  이 중복은 frame 결함으로 등재한다. netflix/kr/login · kakaocorp 404 ·
            navercorp/map · band.us 와 같은 계열이며 W1/W2 로 고쳐지지 않는다.
```

**네이버가 QUERY 이기도 하고 FINANCIAL 이기도 한 것은 실제로 참일 수 있다** — 한 서비스가
두 대표기능을 가진 경우다. 그러나 **연구 frame 은 target 당 하나의 대표기능을 전제**한다.
이 전제와 데이터가 어긋나는 지점이며, 지금 해소하지 않고 등재만 한다.

---

## 이 결정들이 검증하지 않은 것

```
Stage 1 evaluator                 미구현
절단이 실제 판정을 바꿨는지         확인하지 않았다 — cap 도달은 가능성이지 오류 확정이 아니다
절단의 archetype 편향 유의성        검정하지 않았다 (기술통계만)
겹침 16건의 agreement              아직 산출 전
dom slot 이 항상 렌더 이전인지      B 가 NH 1건에서만 확인. 전수 미검증
```
