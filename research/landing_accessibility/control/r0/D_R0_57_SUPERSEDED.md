# D-R0-57 SUPERSEDED — A 의 조인 결함이었다

**발행** Claude A · **작성** 2026-08-27T21:40:32+09:00 · **assertion_type** `OBSERVATION`
**supersedes** `D-R0-57` (전체) · **근거** `C-FACT_CORRECTION-213916`

---

## §1 A 가 틀렸다

A 는 `D-R0-57` 에서 *"frozen CSV 에 `wtg_6d5510a695d0a614` 가 두 행으로 있고 archetype 이
충돌하므로 prior 가 정의되지 않는다 → UNRESOLVED, frame 결함으로 등재"* 라고 결정했다.

**frame 결함이 아니라 A 의 조인 결함이다.**

## §2 A 가 직접 재확인한 사실 — OBSERVATION

```
wtg_6d5510a695d0a614   naver_app         QUERY                    mapping_status = CANDIDATE
wtg_6d5510a695d0a614   naver_naverpay    FINANCIAL_ACTION_ENTRY   mapping_status = AMBIGUOUS_UNRESOLVED
wtg_5b8c59f6fd9839f7   coupang_app       ITEM_DETAIL              AMBIGUOUS_UNRESOLVED
wtg_5b8c59f6fd9839f7   coupang_retail    ITEM_DETAIL              AMBIGUOUS_UNRESOLVED
wtg_f9fbd771ffcdbd42   gmarket_app       ITEM_DETAIL              CANDIDATE
wtg_f9fbd771ffcdbd42   gmarket_auction   ITEM_DETAIL              AMBIGUOUS_UNRESOLVED
```

```
mapping_status == CANDIDATE 필터 →  정확히 59행
필터 후 중복 web_target_id      →  0건
label 56 중 CANDIDATE prior 가 없는 것 →  0건
naver 의 CANDIDATE prior        →  QUERY.  label 도 QUERY.  일치한다
```

**`naver_naverpay` 행은 frozen 59 에 애초에 포함되지 않았다** — 계획 동결 시점에 이미 배제됐다.
`frozen frame` 안에서 충돌은 존재하지 않는다.

## §3 정정된 수치

```
prior 표 정본   representative_task_candidate_shadow.csv @ 2281c85
                  ∧ mapping_status == CANDIDATE
                  ∧ E001_MASTER_PLAN frozen_collection_order 59

prior == label   22 / 42 = 0.5238     ← C 값이 맞다
A 의 21 / 42     mapping_status 미필터 last-wins 조인의 산물. 폐기한다
```

`F-A3` 의 `0.500` 을 **`0.5238`** 로 정정한다. **결론의 방향은 바뀌지 않는다** —
prior 와 관측 label 이 절반 남짓만 일치한다는 사실도, `D-R0-55`(결정 유보)도 그대로다.

## §4 살아남는 것 — C 가 기록 가치를 인정한 부분

```
동일 web_target_id 가 서로 다른 서비스 key 에 매핑된다
   naver_app / naver_naverpay      →  같은 랜딩
   coupang_app / coupang_retail    →  같은 랜딩
   gmarket_app / gmarket_auction   →  같은 랜딩
```

이것은 **frame 의 관측 단위 문제**이며 `F-A2`(NH 스마트뱅킹 / NH 콕뱅크가 같은 바이트)와 **같은 계열**이다.

```
연구 frame 의 단위   서비스
관측의 단위          랜딩 페이지
서비스 여러 개가 한 랜딩으로 수렴하면 두 단위가 어긋난다
```

`F-A2` 는 그 수렴이 **관측까지 도달한** 경우이고, 여기 3건은 **frame 단계에서 이미
AMBIGUOUS_UNRESOLVED 로 배제된** 경우다. 배제됐다는 사실 자체가 frame 이 이 문제를
인지하고 있었다는 증거다. **F-A2 만 미해결로 남는다.**

## §5 A 의 오류 패턴 — 기록

이번 세션에서 A 의 오류 세 건이 모두 **데이터 판독이 아니라 유도 방법**에서 나왔다.

| | 오류 | 잡은 쪽 |
|---|---|---|
| `F-A1b` | degenerate capture 를 파일 크기로 스캔 — 대리변수가 부적절 | labeler · B |
| `D-R0-45` | 커버리지 56/56 — 분자와 분모를 같은 관측집합에서 뽑은 순환 | C |
| `D-R0-57` | prior 조인에 `mapping_status` 필터 누락 — last-wins | C |

```
공통 형태   raw 를 잘못 읽은 것이 아니라, raw 에서 값을 만드는 절차가 틀렸다
함의        A 의 산출은 '무엇을 읽었나' 보다 '어떻게 계산했나' 를 명시해야 검산 가능하다
조치        이후 A 의 모든 집계에 필터 조건·조인 키·중복 처리 규칙을 산출물에 기재한다
            (root set 명시 규칙 — RECONCILE §2 — 과 같은 계열의 요구다)
```

**세 건 모두 다른 plane 이 잡았다.** 독립 검증 구조가 실제로 작동하고 있다는 뜻이며,
동시에 **A 의 자기 검산만으로는 이 계열의 오류를 못 잡는다**는 뜻이다.
