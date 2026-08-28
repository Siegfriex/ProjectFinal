# 발표 문안 — 써도 되는 것 / 쓰면 안 되는 것

mart `5290e0c306ff7a11…` 기준. 각 문장의 근거는
`PRESENTATION_EDA_METRICS.json` 에 있다.

## 써도 되는 문장

1. **"동일한 생활과업을 기준으로 50개 모바일웹 서비스를 전수 시도했고, 그중 8개에서만
   비교 가능한 과업경로 증거를 확보했다."**
   근거: attempted 50/50 · USABLE_PATH_EVIDENCE 8/50 (ASSURED_RECALCULATED).

2. **"관측된 8개 사례에서는 진입 위치(5종/8)와 control 형태(2종/8)가 갈렸지만,
   조작순서·활성화 깊이·메뉴의존은 8건 모두 같았다."**
   근거: TASK C (DESCRIPTIVE_VERIFIED). **selected case series** 임을 함께 말한다.

3. **"미도달 44건 중 21건은 사이트에 경로가 없었다는 뜻이 아니라 수집기가 후보를 찾지
   못했다는 뜻이다."**
   근거: COLLECTOR_ZERO_CANDIDATE 21 vs NO_SAFE_ROUTE_SITE 16 (A R74 분리).

## 쓰면 안 되는 문장

1. ❌ **"50개 중 8개 서비스가 접근 가능했다"** / "접근성 성공률 16%"
   → 8 은 acquisition 결과이지 reachability 가 아니다. frozen frame 기술값이지
   population estimate 가 아니다.

2. ❌ **"평균 활성화 깊이는 0.56단계였다"** (또는 50 분모로 낸 어떤 depth 통계)
   → `activation_depth == 0` 22건은 **관측이 아니라 시퀀스 부재**다. 이 축의 분모는 **28**.

3. ❌ **"라벨 일치율이 28/28 이었다"** / "visible label 과 accessible name 이 대체로 일치했다"
   → **browser-computed AX 는 0/50** 이다. 채워진 값은 visible text 복사이고
   독립 관측 쌍은 **0** 이다. 라벨 축은 사이트 간 결과지표에서 제외됐다.

   ❌ 그리고 **"AX 는 원리적으로 못 얻는다"** 도 쓰지 마라 — probe v2 가 `aria_snapshot()`
   으로 21/21 실제 트리를 얻었다. 맞는 표현은 **"이번 census 에서 AX 캡처가 실패했고
   그 raw 로는 복구할 수 없다"** 까지다(A R130).

## 반드시 붙일 단서

- selected case series n=8 — random sample 이 아니다.
- 관측된 8건이 전부 얕은 경로였던 것은 **수집기가 깊은 경로를 뚫지 못했기 때문일 수 있다**
  (선택편향). "사이트가 얕다" 로 해석하지 않는다.
- Collection run 은 교환가능한 반복측정이 아니다 — R2/R3 는 이전 관측 결과에 따라 대상이
  선택된 rescue pass 이므로 run 별 분포를 성능 비교에 쓰지 않았다.
