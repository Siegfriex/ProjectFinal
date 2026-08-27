# D-R0-80 — Director Phase Transition: V2_DIAGNOSTIC_REAL_EVIDENCE_PILOT

**발행** Claude A · **작성** 2026-08-27T23:54:38+09:00 · **assertion_type** `DECISION`
**권한** Research Director · **amends** `A7` (diagnostic collection 한정) · **supersedes 없음**

---

## §1 Phase 선언

```
phase    V2_DIAGNOSTIC_REAL_EVIDENCE_PILOT
status   PARTIAL_READY_WITH_BLOCKER
```

**W2 HOLD 는 수용되고 프로젝트 전체는 HOLD 되지 않는다.**

## §2 유지되는 것 — 완화 없음

```
W2 release gate      agreement >= 0.85 · coverage >= 0.75      유지
W2 b28aaa5           NOT_PASSED 로 freeze
threshold 완화       금지
force-map            금지
holdout 재선택       금지
prohibited action set · exactly-once · no-login · no-CAPTCHA-bypass   전부 유지
```

**게이트는 살아 있다.** 이번 결정은 **W2 acceptance 와 raw evidence acquisition 을 분리**한 것이지
게이트를 완화한 것이 아니다.

## §3 A7 amendment — diagnostic collection 한정

```
A7-3 (W2 clean-18 holdout validation) 은 diagnostic collection 을 막지 않는다
그 외 A7 조건은 그대로다
canonical analysis 진입에는 여전히 W2 acceptance 가 필요하다
```

**이것이 `D-R0-76 §4` 의 순환 문제를 푸는 방식이다.** A 는 그 순환을 지적하고 결정하지 않았고,
Director 가 **"pilot 의 목적을 detector 평가가 아닌 것으로 한정"** 해서 풀었다.
**pilot 이 detector 를 평가하지 않으면 순환이 아니다.**

## §4 pilot 의 목적과 PASS 기준

```
목적   evidence sufficiency
       collector integrity
       representative-surface observability
아님   W2 performance acceptance pilot
```

```
PASS 기준   detector score 가 아니다
            D-R0-31 systemic measurement mismatch 유무
            W1 safety / exactly-once 계약 준수
```

**`D-R0-31` 이 원래 정한 그대로다** — *"파일럿 결과가 좋고 나쁨은 release 기준이 아니다.
systemic measurement mismatch 가 있는지가 기준이다."*

## §5 D RF-002 의 지위 — 참고하되 canonical 아님

```
D 결과   L0 landing snapshot 은 business/domain semantics 는 상대적으로 강하나
         representative interaction semantics 는 약하다
지위     C-confirmed / NON_CANONICAL research evidence
용도     "offline detector tuning 을 더 반복하기보다 richer evidence 획득을
          다음 정보획득 단계로" 라는 Director 판단의 근거
```

**A 는 D RF-002 를 직접 읽지 않았다** (`A6`). Director 가 인용한 범위로만 안다.
**그리고 그것이 정상이다** — D 결과가 A 를 거치지 않고 Director 판단에 들어간 것은
`A6` 이 막으려던 경로(A 가 자동 채택)가 아니다.

## §6 표본 — run 이전 동결

```
manifest   control/pilot/DIAGNOSTIC_PILOT_MANIFEST.json
sha256     4d3209cad1a316caad117255934617097fdb96f77da67666feb42f71e2c86fc2
seed       LA-DIAG-PILOT-2026-08-27-V2
n          12
```

### 규칙 — Director 요건 대응

| Director 요건 | 이행 |
|---|---|
| hidden holdout label 미사용 | `LABELS_FROZEN` 미참조. 층화는 frame 의 prior archetype |
| frozen non-label metadata 만 | `representative_task_candidate_shadow.csv @2281c85 ∧ CANDIDATE` |
| 7 archetype 전부 | quota 로 강제 — 전 archetype ≥1 |
| QUERY/ITEM_DETAIL/PLACE_LOOKUP 추가 배정 | 2/3/2 — 세 계열이 12 중 7 |
| corporate/app-like · evidence-poor 포함 | quota≥2 archetype 에 evidence-poor 1건 우선 배정 → 3건 포함 |
| split membership 과 독립 | split 파일 미참조 |
| deterministic rule | `sha256(seed + '\|' + web_target_id)` 정렬. 난수 없음 |
| manifest + seed/hash 를 run 전 freeze | 본 커밋에서 동결. run 이전이다 |

### 선정 결과

```
COMMUNICATION_ENTRY   1   카카오톡
CONTENT_OPEN          1   TikTok
FINANCIAL_ACTION_ENTRY 2  NH스마트뱅킹(POOR·degenerate) · 토스
ITEM_DETAIL           3   롯데하이마트(POOR·FAILED) · 메가커피 · 농협하나로마트
PLACE_LOOKUP          2   네이버지도 · 티맵
QUERY                 2   삼성 인터넷 브라우저(POOR·unobserved) · 다음
UTILITY_ENTRY         1   V3 Mobile Plus
```

**evidence-poor 3건이 서로 다른 계열이다** — degenerate · FAILED_EVIDENCE_INCOMPLETE · unobserved.
`D-R0-45`(삼성 3종 unobserved) · `F-A1`(FAILED 3건) · `F-A2`(NH 동일 바이트)에서 등재한
문제 사례가 각각 하나씩 들어갔다. **이번 pilot 이 그것들을 실제로 재관측한다.**

## §7 full-59 승인 권한

```
조건   pilot 에서 C0 없음 · systemic collection defect 없음 · evidence acquisition 정상
       → A 가 별도 Director 개입 없이 full-59 RAW COLLECTION 을 승인할 수 있다
```

**full-59 에서도 유지되는 것**

```
W2                        NOT_PASSED 유지
AMBIGUOUS                 ABSTAIN
MPFED 불능                NULL
canonical Axis-B association   W2 acceptance 전 금지
```

**raw collection 승인이 분석 승인이 아니다.** 수집된 evidence 로 무엇을 주장할 수 있는지는
여전히 `W2 acceptance` 가 정한다.

## §8 병렬 진행

```
W3   D-R0-78 시정 계속
W1   safety mask 계속 (장바구니 FORBIDDEN_TRANSACTION P1)
W4   현재 accepted SHA 유지
```

## §9 A 가 이 pilot 에서 지킬 것

```
1  pilot evidence 를 결과 검증 전 canonical analysis 에 쓰지 않는다
2  pilot 결과가 좋다는 이유로 W2 게이트를 재평가하지 않는다 — 다른 것을 재는 pilot 이다
3  systemic mismatch 판정에 detector score 를 섞지 않는다
4  full-59 승인 시 C0/systemic defect 부재를 근거로 명시하고, 그 판단의 근거를 A run 에 남긴다
5  exactly-once 는 이번이 duplicate launch 사건 이후 첫 REAL_TARGET 이다 — 억제 실패는 C0 다
```

**5번을 특히 못박는다.** `2026-08-27 05:14 w02` 의 재발 여부가 이 pilot 에서 실측된다.

## §10 검증하지 않은 것

```
pilot 실행 결과            미실행
표본의 대표성              12/59 이며 통계적 대표성을 주장하지 않는다 — 진단 표본이다
D RF-002 의 내용           A 는 읽지 않았다. Director 인용 범위로만 안다
evidence-poor 3건의 재관측 성공 여부   미지 — 그것을 보는 것이 목적의 일부다
```
