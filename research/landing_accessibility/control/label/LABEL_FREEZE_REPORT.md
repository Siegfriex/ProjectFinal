# LABEL_FROZEN — 동결 보고

**ID** `LA-LABEL-FREEZE-2.1` · **발행** Claude A · **작성** 2026-08-27T21:25:40+09:00 (`date` 판독값)

```
LABELS_FROZEN.jsonl      sha256  f373004bec9a298c9ba5860144d106cbed97f28e1ee3c4d8ed717448e7e68883
LABEL_SPLIT_FROZEN.json  sha256  dbe4ed0f2cf715b653f2541946f474fdf3e1497de4fa507232e161c65bed48df
CALIBRATION_FOR_B.jsonl  sha256  140619aeba5835c08a40e43175394e94aed5725c5be58eb999f4c679709ab00e   n=30
HOLDOUT_FOR_C.jsonl      sha256  69a284275efd57c36808f8cc216ee1df7a4745b6cf81f73b7203d764a81612e7   n=26
```

**순서**: split 동결(`6612a08`) → labeler 배치 → label 산출 → label 동결. 역순이 아니다.

## §1 검증 — OBSERVATION

```
행 수                56        고유 target 56 / 기대 56
중복 라벨             0
누락                  0
evidence_ref 없는 행   0
생산자                L1(16) · L2(15) · L3(14) · L4(11) — B/C 와 무관
차단 확인             detector 출력 · mart · 통계 · WA 인증 · shadow CSV · 실사이트 접속
```

## §2 분포

| archetype | calibration | holdout | 계 |
|---|---|---|---|
| ITEM_DETAIL | 6 | 4 | 10 |
| CONTENT_OPEN | 5 | 4 | 9 |
| QUERY | 3 | 3 | 6 |
| PLACE_LOOKUP | 4 | 2 | 6 |
| FINANCIAL_ACTION_ENTRY | 3 | 2 | 5 |
| UTILITY_ENTRY | 1 | 4 | 5 |
| COMMUNICATION_ENTRY | **0** | 1 | 1 |
| AMBIGUOUS_UNRESOLVED | 8 | 6 | 14 |

```
abstention rate   14 / 56 = 0.250   →  coverage 0.750
confidence        HIGH 28 · MEDIUM 13 · LOW 15
```

**`coverage 0.750` 은 `D-R0-32` 의 하한 `≥ 0.75` 에 정확히 걸쳐 있다.** 여유가 없다.
다만 이것은 **labeler 의 abstention 이지 detector 의 coverage 가 아니다** — 두 지표를 같은
칸에 넣지 않는다. detector 가 이보다 높은 coverage 를 내면 그것은 성능이 아니라
**abstain 해야 할 것을 매핑했다는 신호일 수 있다.**

**`COMMUNICATION_ENTRY` 는 calibration 에 0건이다.** 이 archetype 은 calibration 으로
학습·조정할 수 없다. `D-R0-49` per-archetype 보고에서 이 사실을 명시한다.

---

## §3 F-A3 (P1) — frozen frame 의 prior 와 evidence 기반 label 이 절반만 일치한다

### 실측 — OBSERVATION

| archetype | frozen frame prior | labeled |
|---|---|---|
| ITEM_DETAIL | **26** | **10** |
| FINANCIAL_ACTION_ENTRY | 11 | 5 |
| UTILITY_ENTRY | 5 | 5 |
| COMMUNICATION_ENTRY | 4 | 1 |
| PLACE_LOOKUP | 4 | 6 |
| CONTENT_OPEN | 3 | 9 |
| QUERY | 3 | 6 |
| AMBIGUOUS_UNRESOLVED | 0 | 14 |

```
prior == label           22 / 56  =  0.393
abstain 제외             22 / 42  =  0.5238

> **[정정 · C-FACT_CORRECTION-213916]** 발행 시점의 21/42=0.500 은 A 가 prior 조인에서
> `mapping_status == CANDIDATE` 필터를 빠뜨린 last-wins 산물이었다. 정본 필터 적용 시 22/42.
> 결론의 방향은 불변이다.
```

### prior `ITEM_DETAIL` 26건이 실제로 무엇이었나

```
ITEM_DETAIL            9     실제로 상품 상세 구조
PLACE_LOOKUP           5     편의점 등 — 랜딩의 대표 행동이 매장찾기였다
CONTENT_OPEN           5     백화점·홈쇼핑 도메인이 실제로는 콘텐츠/IR 포털
AMBIGUOUS_UNRESOLVED   5
QUERY                  1
UTILITY_ENTRY          1
```

### 이것이 뜻하는 것 — 그리고 뜻하지 않는 것

**뜻하는 것**: RF-DT §1 이 경고한 그대로다 — *business domain 은 prior 이지 최종 근거가 아니다.*
그 경고가 **frame 의 절반 규모로 실현됐다.**

**중요한 이유**: frozen 59 task definition 이 `endpoint_definition` 을 결정하고, 그것이 Axis B 를
결정한다. prior 가 절반만 맞는다면 **W2 detector 가 label 로 보정돼도, endpoint 정의는 여전히
prior 기반**이다. 두 축이 어긋난 채로 측정하게 된다.

**뜻하지 않는 것 — A 는 지금 이렇게 주장하지 않는다**

```
"frozen frame 이 틀렸다"                     주장하지 않는다
"label 이 정답이고 prior 가 오답이다"          주장하지 않는다
"ITEM_DETAIL 은 사실 10건이다"                주장하지 않는다
```

**이유 — label 의 신뢰도를 추정하지 않았다.** 각 target 은 **1회만** 라벨됐다.
inter-labeler agreement 를 잰 적이 없다. 즉 `0.500` 이 prior 의 오류율인지 label 의
분산인지 **구분할 수 없다.**

### §3.1 유일한 자연 복제 — 그리고 불일치했다

`F-A2` 의 NH 쌍은 **dom.html 바이트가 완전히 동일**하다. 서로 다른 labeler 에게 갔다.

| target | labeler | archetype | confidence |
|---|---|---|---|
| `wtg_95967b50683649f2` | L2 | `FINANCIAL_ACTION_ENTRY` | HIGH |
| `wtg_fb3d1841dddfd982` | L3 | `AMBIGUOUS_UNRESOLVED` | LOW |

```
동일 바이트에 대한 자연 복제 일치율   0 / 1
```

**그런데 불일치의 원인이 임의적이지 않다 — evidence slot 이 달랐다.**

```
L3   dom.html + ax.json 을 봤다        →  SPA bootstrap, body 비어 있음  →  abstain
L2   probe.json 의 visible_text 를 봤다 →  계좌조회·뱅킹·대출조회·환전신청
                                          메뉴가 실제로 렌더돼 있었다      →  FINANCIAL
```

### §3.2 이것은 detector 명세를 바꾼다 (P1)

**`F-A1b` 의 "degenerate capture" 판정이 부분적으로 무너진다.**
`m.nonghyup.com` 은 evidence 가 없는 게 아니라 **다른 slot 에 있었다.**

```
dom.html      JS 렌더 이전 상태를 담을 수 있다
probe.json    렌더 이후 visible_text 를 담는다
→ SPA / NetFunnel / 지연렌더 사이트에서 두 slot 이 서로 다른 시점을 본다
```

```
DECISION 후보 (B/C 검토 요청)
D-A-후보-5  W2 detector 는 dom/ax 만으로 판정하지 않는다.
            probe.json 의 렌더 후 신호를 signal family 에 명시적으로 포함한다.
            어느 slot 을 읽었는지를 판정 근거에 기록한다.
D-A-후보-6  evidence slot 간 시점 불일치를 evidence 품질 지표로 등재한다.
            "구조 없음" 과 "다른 slot 에 있음" 을 구분하지 못하면
            degenerate 판정이 slot 선택의 부산물이 된다.
```

### §3.3 A 가 요구하는 것 — 신뢰도 추정 없이 label 을 frame 판정에 쓰지 않는다

```
필요       replicate labeling — 부분집합을 2인 이상이 독립 라벨해 agreement 추정
범위       최소 abstain 을 포함한 층화 부분집합. 전수 재라벨은 불필요
금지       agreement 추정 전에 label 로 frozen frame 의 오류율을 주장하는 것
용도 구분   label 은 detector calibration 에 쓴다 (원래 목적)
           frame 판정에 쓰려면 별도의 신뢰도 근거가 필요하다
```

**이 구분을 지키지 않으면**, 1회 라벨의 분산이 frame 오류율로 둔갑한다.
그것은 이 프로젝트가 반복해서 경계해온 승격이다 — `OBSERVATION` 이 `ANALYSIS` 를 건너뛰고
`DECISION` 자리에 앉는 것.

---

## §4 이 동결이 검증하지 않은 것

```
inter-labeler agreement        측정하지 않았다 (각 target 1회 라벨)
label 의 정확성                 gold 의 gold 는 없다
COMMUNICATION_ENTRY calibration calibration 0건 — 조정 불가
endpoint label                 archetype 만 라벨했다. endpoint 도달은 라벨 대상이 아니었다
prior 와 label 중 무엇이 맞는지  판정하지 않았다 — §3.3 참조
```
