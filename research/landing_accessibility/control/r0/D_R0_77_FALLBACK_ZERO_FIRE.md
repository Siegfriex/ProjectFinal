# D-R0-77 — fallback 이 0건 발화했다: HOLD 조건 도달 여부 판정

**발행** Claude A · **작성** 2026-08-27T23:42:38+09:00 · **assertion_type** `DECISION`
**근거** `D-R0-74-2.B` completion (B, P1) @ W2 `b28aaa5cad736082a6a76c0ca6a9f6be330bbcfb`

---

## §1 B 가 밟은 것

```
구현      _nlp_fallback_resolve 를 resolve_representative_function 에 배선
5조건     전건 준수 — calibration only · deterministic ambiguity 이후 · 7 archetype 이탈 0 ·
          force-map 금지 · offline 강제(HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE)
테스트    test_w2_rf_detector 47 pass · 전체 486 passed / 0 failed · ruff·mypy clean
소유      l1_engine.py 와 tests/test_w2_ 밖 변경 0건
```

```
결과   calibration 에서 fallback 발화 0건. coverage 는 해결되지 않았다
```

## §2 결정적 발견 — fallback 이 틀리면서 rule 결함을 드러냈다

```
첫 진단   fallback 이 calibration 에서 4건 발화, 그중 3/4 오답
          (daangn · daum · google · lottemart — 전부 PLACE_LOOKUP 오판)
원인      fallback 이 아니라 rule 결함이었다
          _real_region_by_signal_type 이 PLACE_LOOKUP 과 QUERY 에
          동일한 일반 검색창 신호를 공유시켰다
          → 애초에 '가짜 tie' 였고 fallback 은 존재하지 않는 경합을 풀려다 틀렸다
시정      PLACE_LOOKUP 을 _place_region_evidence 전용 신호만 쓰도록 변경
          그 4건이 rule 만으로 유일-MAPPED 가 됐고 fallback 발화가 4→0
```

**fallback 은 실패함으로써 rule 의 결함을 찾아냈다.** 이것이 이번 작업의 실질 성과다.

**`D-R0-67-2`(list-family 판별 신호)가 지목한 문제의 한 사례이기도 하다** — 공유 신호가
archetype 을 가르지 못한다. C 가 관측한 `PLACE_LOOKUP 22 쏠림` 이 이것으로 설명될 가능성이
있으나 **미확인이다** (C 재채점 대상).

## §3 B 의 귀속 규율 — 계약으로 올린다

```
rule-only (시정 후)    25/30 abstain
rule + fallback         25/30 abstain   (변화 없음 — 발화 0건)
시정 전                 29/30 abstain
```

```
B: "29→25 는 fallback 성과가 아니라 rule 결함 시정 덕분이다.
    fallback 성과로 인용하면 안 된다."
```

**이것을 인용 규칙으로 고정한다.**

```
D-R0-77-1
   두 변경이 같은 커밋 구간에 들어갔을 때 개선을 어느 쪽에 귀속시킬지는
   분리 측정 없이 주장하지 않는다.
   분리할 수 없으면 '분리되지 않았다' 고 적는다
```

**이것을 지키지 않으면 "NLP fallback 도입으로 abstain 29→25 개선" 이라는 문장이 만들어진다.**
그 문장은 **모든 단어가 참이면서 전체가 거짓**이다.

## §4 threshold 0.10 의 지위

```
값        NLP_FALLBACK_MARGIN_THRESHOLD = 0.10
도출      calibration 발화 표본 0건 → margin 분포에서 도출 불가
근거      손으로 구성한 대조 텍스트 sanity check 의 관측 범위(0.12~0.37) 참고한 보수적 기본값
지위      provisional. calibration-validated 가 아니다
표기      코드 주석과 W2 보고 양쪽에 명시됨 (B 확인)
```

`D-R0-13` 은 *"threshold 를 임의 숫자로 영구 선언하지 않는다 — calibration split 에서 정한다"* 로
정했다. **표본이 0건이면 도출할 수 없다** — 이는 규칙 위반이 아니라 규칙이 적용될 조건이 없는 것이다.

```
D-R0-77-2
   fallback 이 calibration 으로 검증되기 전까지 어떤 게이트 판정도 fallback 출력에 기대지 않는다
   현재 발화 0건이므로 실질적 영향은 없다
   재수집 후 발화 표본이 생기면 그때 threshold 를 실측으로 정한다
```

B 가 *"이 값을 근거로 어떤 성능 주장도 하지 않는다"* 고 먼저 선언한 것이 옳다.

## §5 `D-R0-74-3` HOLD 조건 도달 여부 — **아직 아니다**

`D-R0-74-3` 의 문언:

> `D-R0-13` NLP fallback 을 **계약대로 밟은 뒤에도** agreement 가 게이트에 도달하지 못할 때 HOLD

### 판정

```
밟았는가        구현·조건 준수 측면에서는 밟았다
그러나          fallback 이 0건 발화했으므로 '작동한 결과' 는 관측되지 않았다
0건의 원인      B 설명 두 겹
                (1) 구 probe 코퍼스에 이번 세션 신규 raw feature 가 없어
                    tier3 genuine tie 가 잘 생기지 않는다
                (2) 실제로 생겼던 4건은 rule 결함이 만든 가짜 tie 였고 시정하니 사라졌다
```

**(1) 이 결정적이다.** frozen `probe.json` 은 **구 `l0_probe.js`** 로 수집됐다.
C 가 `C-FINDING-222009` 에서 같은 것을 지적했다 —
*"frozen probe region_signals 는 `{declared_regions, search_inputs}` 뿐, W2 신규 신호 부재."*

```
그리고 C 는 그것 때문에 DOM replay 를 만들었다
   stored dom.html → file:// → 신규 l0_probe.js → probe_v2
   즉 신규 raw feature 가 재생성된다
```

```
DECISION  HOLD 하지 않는다
이유      B 의 completion 자체가 다음 단계를 지목한다 —
          "C 가 b28aaa5 에서 DOM replay 재채점 → A 의 D-R0-74-3 판정"
          fallback 이 0건 발화한 이유가 코퍼스 결함이고, 그 결함을 푸는 절차가
          이미 존재하며 아직 실행되지 않았다
```

### D-R0-77-3 — HOLD 조건을 마지막으로 좁혀 고정한다

**이 조건은 더 이상 미루지 않는다. 다음 측정이 마지막이다.**

```
C 가 b28aaa5 에서 DOM replay(probe_v2 재생성)로 재채점한 뒤
   coverage 가 여전히 게이트에 도달하지 못하면  →  HOLD, Director 판단 요청
   그때는 '계약이 허용한 모든 경로를 밟았고 코퍼스 결함도 해소했으나 도달하지 못했다' 이다
```

```
A 가 스스로 못박는 것
   이 다음에는 새로운 '아직 밟지 않은 경로' 를 찾지 않는다
   찾게 되면 그것은 경로가 아니라 HOLD 회피다
```

**`D-R0-74 §3` 에서 A 가 "HOLD 를 피하려고 이유를 찾는 것인가" 를 물었다.
같은 질문을 두 번 하면 답이 달라져야 한다.** 이번이 두 번째이므로 조건을 종결형으로 적는다.

## §6 B 의 처신

```
HOLD 여부를 선언하지 않고 A 에게 넘겼다
fallback 성과 귀속을 스스로 부인했다 (29→25 는 rule 시정 덕분)
threshold 를 provisional 로 표기하고 성능 주장을 스스로 봉인했다
not_verified 6항을 명시했다 — fallback 정확도 미검증 · threshold 실측 근거 없음 ·
   합성 sanity check 는 실사이트 성립을 증명하지 않음 · PLACE_LOOKUP 시정 효과 미확인 ·
   VLM 미구현 · REAL_TARGET 미실행
```

**성과로 보고할 수 있는 것을 성과가 아니라고 먼저 말했다.**

## §7 이 결정이 검증하지 않은 것

```
DOM replay 재채점 결과        미실시 — 이것이 다음 측정이다
PLACE_LOOKUP 시정의 효과      C 재채점 대상
fallback 정확도               발화 0건이라 검증 불가
threshold 0.10                실측 근거 없음
```
