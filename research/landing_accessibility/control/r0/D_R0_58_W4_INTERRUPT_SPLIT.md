# D-R0-58 — W4 P2 REWORK: interrupt form 과 semantic 을 분리한다

**발행** Claude A · **작성** 2026-08-27T21:44:31+09:00 · **assertion_type** `DECISION`
**amends** `D-R0-25` · **근거** `C-FINDING-214214` (P2) · **대상** `claude-b/w4-axisc-mart @ cf8dbd70afc3d3ca518916dd6aea8b29bd4588a1`

---

## §1 판정

```
T-A-W4-001 completion @ cf8dbd70   HOLD_PENDING_REWORK  (P2, scoped)
scope                              classify_interrupt 의 semantic 라벨 붕괴만
그 외 W4 산출                       통과 — C 가 PASS 로 확인한 항목들
REAL_TARGET                        NO-GO 유지 (변경 없음)
```

**C 의 사전 감사가 completion 보다 7초 먼저 도착했다.** 프로토콜 §8 대로 같은 SHA 에서
C 의 P2 가 B 의 completion 보다 우선하며, A 가 reconcile 한다.

## §2 C 가 관측한 것 — OBSERVATION

C 가 B 의 `classify_interrupt` 를 `2281c85` 와 `cf8dbd7` 두 SHA 로 SUT 실행해 대조했다.
E001 probe 58건 · 후보 635건 중 **22건의 라벨이 바뀌었다** (관측 17건).

```
LOGIN_PROMPT      → BANNER            9
PROMOTION_MODAL   → BANNER            5
CHAT_WIDGET       → BANNER            2
COOKIE_CONSENT    → BANNER            2
APP_INSTALL       → BANNER/PROMOTION  2
ADVERTISEMENT     → BANNER            1
PROMOTION         → BLOCKING_MODAL    1
```

**geometry 값은 불변이다.** 바뀐 것은 **semantic 라벨**이다.
geometry class(`sticky`/`fixed`/`dialog`)가 semantic 필드를 선점해서,
*"로그인 유도 sticky bar"* 가 `LOGIN_PROMPT` 를 잃고 `BANNER` 가 된다.

## §3 A 의 계약 문구에 구멍이 있었다

`D-R0-25` 의 원문:

> **semantic 분류가 geometry 값을 바꾸지 않는다.**

**B 는 이것을 문자 그대로 지켰고 테스트로 보장했다.** B 의 compliance 기술은 정확하다.
문제는 이 문장이 **한 방향만** 막았다는 것이다.

```
A 가 막은 것      semantic  →  geometry      (geometry 값 보호)
A 가 막지 않은 것  geometry  →  semantic      (semantic 라벨 보호)
```

Axis C 의 측정 대상은 geometry(`OverlayCoverage`)**와** interrupt type **둘 다**다.
한쪽만 보호하면 다른 쪽이 조용히 사라진다. **B 의 구현 결함이라기보다 A 의 명세 결함이다.**

## §4 DECISION

### D-R0-58-1 — 두 필드로 분리한다 (C 권고 채택)

```
interrupt_form       구조 tier    BLOCKING_MODAL · PROMOTION_MODAL · BANNER · …
                                  판정 근거 = geometry / DOM 구조
interrupt_semantic   텍스트 tier  LOGIN_PROMPT · COOKIE_CONSENT · CHAT_WIDGET ·
                                  APP_INSTALL · ADVERTISEMENT · …
                                  판정 근거 = 텍스트 / 사전 / 모델
각 필드에 독립적인 status 를 둔다 (RESOLVED / UNRESOLVED / NOT_APPLICABLE)
상호 덮어쓰기 금지 — 한 필드가 다른 필드를 비우거나 대체하지 않는다
```

**한 overlay 는 form 과 semantic 을 동시에 가질 수 있다.** *"로그인 유도 sticky bar"* 는
`form = BANNER` 이면서 `semantic = LOGIN_PROMPT` 다. 이것을 하나의 필드에 담으려 한 것이
붕괴의 원인이다. **둘은 배타적 범주가 아니라 직교하는 축이다.**

### D-R0-58-2 — provenance 요구

```
completion 에 classifier_version 을 기재한다
old → new 전이표를 provenance 로 첨부한다 (C 가 이미 산출한 22건 표를 인용 가능)
```

### D-R0-58-3 — canonical 과의 직접 비교 금지

```
canonical 82f631f 의 interrupt label 분포와 새 분류기 분포를 직접 비교하지 않는다.
분류기가 바뀌었으므로 분포 차이는 사이트 변화가 아니라 분류기 변화다.
비교하려면 두 분류기를 같은 입력에 돌린 전이표로만 한다.
```

### D-R0-58-4 — `D-R0-25` 개정

```
개정 전  semantic 분류가 geometry 값을 바꾸지 않는다
개정 후  semantic 분류와 구조 분류는 서로의 필드를 바꾸지 않는다.
         geometry 값은 semantic 이 바꾸지 않고,
         semantic 라벨은 geometry class 가 선점하지 않는다.
         dismissal 전후 evidence 를 섞지 않는다 (유지)
```

---

## §5 B 의 W4-N1~N4 처리

### W4-N1 — netflix 는 duplicate launch 이면서 동시에 frame 결함 · ACCEPT

duplicate launch 4건의 정체가 밝혀졌다 — `netflix(www.netflix.com/kr/login)` · `chrome(google.com/chrome)` ·
`hyundai_card(mycompany.hyundaicard.com)` · `cashwalk(cashwalk.com)`.

`netflix.com/kr/login` 은 A 가 `T-A-FINDING-001` 에서 frame defect candidate 로 지목한 그 URL 이다.

> **B 의 지적이 정확하다** — *"어느 쪽으로 처리하든 다른 쪽이 남는다."*
> duplicate 를 제거해도 로그인 URL 이 frame 에 있다는 문제는 남고,
> frame 을 고쳐도 그 관측이 중복 발사됐다는 사실은 남는다. **두 장부에 각각 기록한다.**

### W4-N2 — B 의 자기정정 · ACCEPT

evidence 디렉터리 기준 run 2개인 target 은 4건이 아니라 **7건**이며, 추가 3건은 probe.json 이 없는 stub 이다.
이는 C 의 C1b `빈 stub 6 dir = 3×2` 와 정확히 일치한다.

```
duplicate launch 4건   batch_0001 집합 근거 — 유효하다
stub 3 × 2 = 6         launch 성공 자체가 없었다 — duplicate 로 합산하지 않는다
```

**B 가 "앞선 보고는 probe.json 기준이었다" 고 계수 기준을 밝힌 것이 중요하다.**
이번 세션에서 반복된 형태다 — 같은 대상을 다른 경계로 세면 다른 값이 나오고,
**경계를 밝히면 즉시 닫힌다.**

### W4-N3 — A 가 B 의 주장을 재현하지 못했다 · PARTIAL

B: *"naver_app/gmarket_app 과 naver/gmarket 의 wtg 해시가 불일치한다."*

A 가 frozen CSV 에서 확인한 것:

```
naver_app        wtg_6d5510a695d0a614   CANDIDATE              web_target_url = (빈 값)
naver_naverpay   wtg_6d5510a695d0a614   AMBIGUOUS_UNRESOLVED   web_target_url = (빈 값)
gmarket_app      wtg_f9fbd771ffcdbd42   CANDIDATE              web_target_url = (빈 값)
gmarket_auction  wtg_f9fbd771ffcdbd42   AMBIGUOUS_UNRESOLVED   web_target_url = (빈 값)
naver_map        wtg_efda6e0b8457d63c   CANDIDATE              https://www.navercorp.com/service/map
coupang_eats     wtg_054d78ed187cdd9f   CANDIDATE              https://www.coupangeats.com/
```

**A 는 `naver` / `gmarket` 이라는 별도 key 를 이 CSV 에서 찾지 못했다.** 따라서 B 가 말한
*"해시 불일치"* 를 재현하지 못했다. **재현하지 못했다는 것은 B 가 틀렸다는 뜻이 아니다** —
B 가 다른 산출물을 봤을 수 있다.

A 가 실제로 관측한 것은 다른 사실이다:

```
`_app` 접미 key 들은 web_target_url 이 비어 있으면서
형제 service key 와 같은 wtg 를 공유한다
```

이는 `D_R0_57_SUPERSEDED §4` 에 이미 등재한 **관측 단위 문제**와 같은 것이다.

```
DECISION  W4-N3 는 OPEN 으로 둔다. B 에게 어느 산출물에서 관측했는지 회신을 요청한다.
          A 는 재현하지 못한 주장을 등재하지 않는다.
```

### W4-N4 — 상태 어휘 정밀화 · ACCEPT

`shinhan` 과 `lotte_himart` 는 **probe.json 자체가 디스크에 없다.**
A 의 `FAILED_EVIDENCE_INCOMPLETE` 판정과 정합적이나 더 구체적인 상태다.

```
'evidence 가 불완전'   상태를 뭉뚱그린 표현
'probe 산출물 부재'    실제 상태
DECISION  W4 mart 는 후자를 기록한다. 전자는 mart status 에서 쓰지 않는다.
```

`coupang_eats` 의 `STRUCTURAL_DEGENERATE_CAPTURE` 는 **B 가 A 판정을 수용했을 뿐 재현하지 않았다** 고
명시했다. **이 명시가 옳다** — A 의 판정을 B 가 재현 없이 수용한 것은 T4 를 T1 으로 올린 것이므로,
그 사실이 기록돼야 나중에 검산 가능하다.

---

## §6 이 판정이 검증하지 않은 것

```
분리 후 semantic 정밀도        독립 label 대비 미검증 (B 도 not_verified 에 명시)
PrimaryActionOcclusion         전건 PENDING_TASK_BINDING — W1+W2 이후
pac_truncated 의 완화 가정      'primary action 이 상위 200 안에 있다' 는 미검증 가정이다.
                               B 가 이것을 가정이라고 명시한 것을 A 가 그대로 유지한다
dismiss 성공/실패              l0c 산출물에 구조화 결과 없음 — NULL 유지
W4-N3                          A 가 재현하지 못했다
```
