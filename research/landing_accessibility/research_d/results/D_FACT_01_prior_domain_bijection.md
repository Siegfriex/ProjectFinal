# D-FACT-01 — `prior_archetype` 과 `prior_business_domain` 은 완전 전단사다

**claim_kind**: `OBSERVATION`
**상태**: 검증됨 · 재현 가능 · **D 의 거의 모든 선행 결과에 소급 적용되는 제약**
**발견 경로**: D-RF2-D worker 가 limitation 으로 지적 → D orchestrator 가 독립 확인

---

## 사실

`D_OBSERVATION_TABLE_v2.csv` 의 `in_mart==1` 56행에서:

| business_domain | archetype | 관계 |
|---|---|---|
| `CONTENT_VIDEO` | `CONTENT_OPEN` | 1:1 |
| `FINANCE_PAYMENT` | `FINANCIAL_ACTION_ENTRY` | 1:1 |
| `MAP_MOBILITY` | `PLACE_LOOKUP` | 1:1 |
| `PORTAL_SEARCH` | `QUERY` | 1:1 |
| `SHOPPING_COMMERCE` | `ITEM_DETAIL` | 1:1 |
| `SOCIAL_COMMUNICATION` | `COMMUNICATION_ENTRY` | 1:1 |
| `UTILITY_OTHER` | `UTILITY_ENTRY` | 1:1 |

```
H(archetype) = 2.311 bits
H(domain)    = 2.311 bits
MI           = 2.311 bits
정규화 MI (MI / H(archetype)) = 1.000
domain 이 archetype 을 유일하게 결정하는 target = 56/56
```

**두 라벨은 같은 변수를 다르게 부른 것이다.**

---

## 이것이 무엇을 뜻하는가

### 1. `prior_agreement` 는 "도메인 배정 재현율" 이다

D 의 모든 실험이 보고한 `prior_agreement` 는 "관측 증거로부터 **업종 배정을 되찾는 비율**" 이다.
"대표기능을 맞히는 비율" 이 아니다. 이름이 archetype 일 뿐이다.

영향 받는 D 산출: RQ-D3A · RF001-A · RF001-C · RF2-A · RF2-B · RF2-C · RF2-D · D-SUP-01.
**수치는 바뀌지 않는다. 그 수치가 무엇을 재는지가 바뀐다.**

### 2. "interaction semantics vs domain semantics" 는 이 prior 로 판별 불가다

`prior_agreement` 만으로는 두 가설이 **원리적으로** 구분되지 않는다.
interaction 신호가 맞아도 domain 신호가 맞아도 같은 값이 나온다.
→ `D-SUP-01` 의 해당 부분은 `NOT_TESTABLE` 이며, 이 사실을 D-SUP-01 worker 에게 실행 중 전달했다.

**살아 있는 판별 경로**(prior 를 거치지 않는 것):
- `NO_BRAND_DOMAIN` 에서 **예측 자체가 얼마나 바뀌는가**
- `CONTROL_ONLY` vs `TOPIC_ONLY` 의 **예측 일치율**
- representation 별 margin · class coverage

Director 가 D-SUP-01 에 "top-1 보다 stability·top-2 stability·margin·class coverage 를 우선 보고" 하라고
지시한 것이 **바로 이 이유로 옳다** — 그 지표들은 prior 를 거치지 않는다.

### 3. RF2-B 의 결과가 다르게 읽힌다

RF2-B 는 16 feature 중 BH-FDR 통과 0개, 상위가 `accessible_name_richness`(구조량)라고 보고했다.
이제 그 문장은 이렇게 읽힌다: **관측 feature 로 업종을 되찾을 수 없다.**
"대표기능을 못 맞힌다" 보다 약한 주장인지 강한 주장인지는 자명하지 않다 —
업종은 archetype 보다 텍스트에서 더 잘 드러날 것으로 기대되는데도 안 됐기 때문이다.

### 4. RF2-D 의 반례가 이것과 맞물린다

RF2-D 는 Level 1 이 `QUERY_SUBMISSION` 으로 확정한 7건 중 prior 가 `QUERY` 인 건 1건뿐이고
나머지는 커머스·콘텐츠였다고 보고하며 **"L1 은 서비스의 대표기능이 아니라 랜딩이 지금 제공하는
affordance 를 측정한다"** 고 썼다. D-FACT-01 과 합치면:

> 관측 증거는 **랜딩이 지금 제공하는 것**을 재고, prior 는 **서비스의 업종**을 잰다.
> 둘이 안 맞는 것은 detector 결함이 아니라 **서로 다른 것을 재고 있기 때문**일 수 있다.

이것은 가설이지 확립된 사실이 아니다.

---

## 이 사실이 답하지 않는 것

- **prior 가 틀렸다는 뜻이 아니다.** 업종 기반 prior 는 SSOT 01 §1 Layer P 가 정한 정당한 출발점이고,
  §1 은 observed task shape 가 prior 를 이긴다고 이미 규정했다.
- **7 archetype 정의가 잘못됐다는 뜻도 아니다.** 전단사인 것은 이 **56 target 표본의 배정**이지
  archetype 정의 자체가 아니다. 다른 표본에서는 한 업종이 여러 archetype 을 가질 수 있다.
- gold label 이 있으면 이 문제는 사라진다. D 는 gold label 을 만들지 않고 열지도 않는다.

## Production implication (제안일 뿐)

- **P1**: D 의 모든 `prior_agreement` 수치를 인용할 때 "업종 배정 재현율" 임을 병기할 것.
- **P2**: detector 평가를 prior 로만 하면 업종 분류기를 만들게 된다. gold label 평가가 필요한 이유가 하나 더 생겼다.
- 어느 것도 D 의 권한이 아니다. A 검토 전에는 implementation candidate 도 아니다.

## 재현

```bash
.venv/bin/python - <<'PY'
import csv, math
from collections import Counter, defaultdict
from pathlib import Path
RD = Path("<research_d>")
rows = [r for r in csv.DictReader((RD/"results"/"D_OBSERVATION_TABLE_v2.csv").open())
        if r["in_mart"] == "1"]
d2a = defaultdict(set)
for r in rows:
    d2a[r["prior_business_domain"]].add(r["prior_archetype"])
print({d: sorted(a) for d, a in d2a.items()})
PY
```
