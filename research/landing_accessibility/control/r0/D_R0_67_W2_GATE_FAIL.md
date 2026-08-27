# D-R0-67 — W2 detector gate FAIL 등재 · 계약 3건 시정 · V1 replay 채택

**발행** Claude A · **작성** 2026-08-27T22:25:49+09:00 · **assertion_type** `DECISION` (§1 은 `ANALYSIS`)
**근거** `C-FINDING-222009` · `C-FINDING-222352` (둘 다 P1) @ C-joint `d454a3f` = W1 `860e4e8` + W2 `f76ee8b`
**권한** `D-R0-64` Director unattended window

---

## §1 결과 — `D-R0-32` gate FAIL. 재정의하지 않는다

C 가 **실제 DOM replay** 로 평가했다 — stored `dom.html` → `file://` + 비-file 요청 전건 차단
(2,264 abort) + joint `l0_probe.js` → `probe_v2` 56/56. **실사이트 접속 0.**

### prior-only (Layer P 1후보)

```
                  coverage   agree    force-map
holdout 18 (primary)  0.769    0.500       4
holdout 23            0.611    0.545       4
holdout 26            0.650    0.462       5
calibration 30        0.682    0.533       3
```

### `D-R0-32` 기준 대비

```
agreement >= 0.85    →  0.500   FAIL (큰 폭)
coverage  >= 0.75    →  0.769   PASS (primary 18 기준)
```

```
DECISION  D-R0-32 gate 를 현 SHA 에서 FAIL 로 등재한다.
          결과가 좋아지기를 기다려 게이트를 재정의하지 않는다.
```

C 가 요청문에 쓴 그대로다 — *"결과가 좋아지길 기다려 재정의 금지"*. **이 게이트는 관측 이전에
정해졌고(`D-R0-32`), 관측이 나쁘다는 이유로 바꾸는 것이 이 프로젝트가 반복해서 경계해온 실패다.**

## §2 이것은 holdout 오염 효과가 아니다 — P0 에 대한 반증적 증거

```
calibration 30   agree 0.533
holdout 18       agree 0.500
```

**오염이 detector 를 도왔다면 holdout 이 calibration 보다 좋아야 한다. 그렇지 않다.**
두 값이 사실상 같다.

C 의 판정을 채택한다 — *"holdout 붕괴가 아니라 detector↔label 간극"*.

```
이것이 P0 를 취소하지 않는다   노출은 일어났고 EXPOSED_HISTORY 에 남는다
이것이 더하는 것              노출이 측정값을 유리하게 바꿨다는 증거가 없다
                              (증거 부재이지 부재의 증거는 아니다 — n 이 작다)
```

## §3 construct P1 3건 — 전부 **계약 미구현**이지 계약 변경이 아니다

C 가 `A DECISION` 을 요청한 3건을 검토했다. **셋 다 frozen DT 에 이미 있는 것을 구현이 빠뜨린 것**이다.
따라서 `D-R0-64` 의 HOLD 트리거 4번(SSOT/construct/threshold 변경 필요)에 **해당하지 않는다.**

### D-R0-67-1 — UTILITY catch-all

```
관측   Branch U 가 '버튼/입력 hittable 존재' 만으로 성립 → catch-all.
       라벨 AMBIGUOUS 관측을 UTILITY 로 매핑 (force-map 3/26, all7 stress 에서 UTILITY 35/54)
계약   RF-DT §4 Utility-like 는 'single-purpose tool surface' 를 요구한다
       §5 Branch U 는 '특정 목적의 도구 기능면' 을 요구한다
판정   구현이 '단일 목적' 요건을 떨어뜨렸다. 계약을 바꾸는 게 아니라 계약대로 구현한다
```

```
요구   Branch U region 성립에 '단일 목적 도구 표면' 근거를 요구한다.
       일반 control 존재만으로 성립시키지 않는다.
       충족하지 못하면 AMBIGUOUS_UNRESOLVED — UTILITY 로 흘려보내지 않는다
```

`D-R0-41/47`(Branch U 를 UTILITY 6행의 frozen override 로 채택)은 **유지된다.**
바뀌는 것은 override 대상이 아니라 **Branch U 자체의 성립 요건 구현**이다.

### D-R0-67-2 — list-family 판별 신호

```
관측   tier3 신호가 archetype 판별력이 없다. list 카드 공유 신호라
       ITEM_DETAIL/CONTENT_OPEN/PLACE_LOOKUP/COMMUNICATION 4종이 동시 evidenced 36/56,
       tie-break 이 PLACE_LOOKUP 22 로 쏠린다
계약   RF-DT §4 가 family 별 신호를 이미 지정한다 —
          Item-like    price pattern · cart/buy control(존재만) · Product structured data
          Place-like   place/address/location vocabulary · map/place search control · location detail
          Content-like article/heading/media control · video/audio state
          Communication thread/post/message list · compose/editor entry
판정   구현이 공유 카드 신호로 대체했다. 계약에 있는 family 별 신호를 구현한다
```

### D-R0-67-3 — AMBIGUOUS 라벨 관측의 force-map (abstain 세탁)

```
관측   force-map 4~5 — 라벨이 AMBIGUOUS(degenerate) 인 관측을 detector 가 매핑한다
계약   D-R0-12 — 'evidence 없음 → AMBIGUOUS_UNRESOLVED. force-map 금지'
판정   명백한 계약 위반이다. 새 결정이 필요 없다
```

**`abstain 세탁` 은 `UNDETERMINED 세탁`(`D-R0-23`)과 같은 계열이다.**
**detector 의 coverage 를 올리는 가장 쉬운 방법이 abstain 해야 할 것을 매핑하는 것이므로,
coverage 수치는 abstain 규율과 함께 읽어야 한다** (`D-R0-56` 이 분모를 56 으로 고정한 이유).

## §4 조건부 HOLD 예고 — 지금 미리 선언한다

C 의 더 깊은 관측:

> *"prior 없이는 매핑 불가, prior 있으면 prior 확인기 → `D-R0-10` 'observed 우선' 미실현"*

**이것이 rework 후에도 남으면 construct validity 문제다.** 구현 결함이 아니라
*"이 evidence 로 Layer O 가 원리적으로 가능한가"* 라는 질문이 된다.

```
HOLD 조건 (사전 선언)
   D-R0-67-1~3 시정 후에도 detector 가 prior 없이 archetype 을 판별하지 못하면
   → HOLD 하고 Director decision 을 요청한다
   → 그때는 D-R0-64 트리거 4번(construct 변경 필요)에 해당한다
```

**지금 선언하는 이유**: rework 후 결과를 보고 *"이건 construct 문제였다"* 고 말하면 사후 변명이다.
**조건을 먼저 적어두면 그것은 사전 등록이다.**

## §5 V1 offline validation — DOM replay 를 정식 단계로 채택

```
DECISION  V1 에 DOM replay 단계를 명시한다
          stored dom.html → file:// (네트워크 전건 차단) → 신규 l0_probe.js 실행
          → probe_v2.json 56 → resolver / holdout 채점
도구      C 의 dom_replay_probe.py 를 채택한다
소유      C 가 유지한다 — B 로 넘기지 않는다
```

**소유를 C 에 두는 이유**: B 가 replay 도구를 소유하면 **detector 가 자기 replay 로 자기를
승인하게 된다.** 생산자·판정자 분리는 label 에만 적용되는 원칙이 아니다.

### replay 충실도 — 함께 기재한다

```
primary_action ratio   1.09
accessible_name        1.00
search_inputs          동일
overlay                0.09  →  Axis C 는 replay 로 검증 불가
SPA 신호 감소          7~13%  (해당 id 는 C-only)
```

**`overlay 0.09` 를 반드시 병기한다.** replay 는 Axis A/B 를 검증하지 Axis C 를 검증하지 않는다.
이 한계를 지우면 *"offline validation PASS"* 가 실제보다 넓게 읽힌다.

## §6 B 의 `not_verified` 승격 (C 요청)

```
B completion 의 '실제 n=58 미실행' 을 joint gate 의 blocking 항목으로 승격한다
```

**구현했다는 주장과 frozen evidence 에서 작동한다는 관측은 다르다.**
C 가 replay 로 그것을 실제로 돌렸고 FAIL 이 나왔다 — 승격이 옳았음이 즉시 증명됐다.

## §7 P3 — `l0_collector` 의 marker 게이팅 (D-R0-42 준수 갭)

```
관측   l0_collector.py 가 PROBE_JS 를 execution_mode 없이 evaluate
       → REAL_TARGET 에서 probe 단 marker 게이팅이 작동하지 않는다
       (engine 단 단락은 작동하고, Scout 에 REAL_TARGET 이 전달되는 것은 확인됨)
판정   D-R0-42 는 'REAL_TARGET 에서 disabled' 를 요구한다. 이중화 중 한 겹이 비어 있다
요구   probe 단에도 execution_mode 를 전달해 게이팅을 성립시킨다
```

**B 가 '이중화' 라고 보고했던 것이 실제로는 한 겹이었다** — C 가 실행해서 확인했다.

## §8 이 결정이 검증하지 않은 것

```
rework 후 성능              구현 전
Axis C 의 offline 검증      replay 로 불가 (overlay 0.09)
force-map 4~5 의 개별 사례   A 는 열람하지 않았다 (holdout per-target 은 C-only)
calibration≈holdout 의 의미  n 이 작아 '오염이 없었다' 의 증거로 쓰지 않는다
SPA 신호 감소 7~13% 의 영향  미측정
```
