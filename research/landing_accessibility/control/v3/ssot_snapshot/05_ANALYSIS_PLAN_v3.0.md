# Analysis Plan v3.0 — Cross-Service Flow Divergence

## 1. 분석단위

Primary: `service × frozen task`.

family n=10. 동일 family의 45 pair는 distance matrix의 cell이지 독립 표본 n=45가 아니다.

## 2. Primary dimensions

### A. Direct Discoverability
- S0 task control visible rate
- first visible scroll state
- menu dependency rate

### B. Spatial
- x/y distribution
- zone distribution / entropy
- service-pair spatial displacement

### C. Label / Identification
- visible label unique forms
- accessible name forms
- label relation
- icon-only rates

### D. Control / Reveal
- control type distribution
- nav container type
- reveal direction
- nav container depth

### E. Flow Topology
- unique sequence signatures
- normalized Levenshtein distance
- LCS similarity
- sequence cluster/heatmap

### F. Depth
- activation depth median/IQR/range
- optional legacy NED/IED/MPFED

### G. Auth
- auth-gate occurrence
- auth gate stage distribution

### H. Obstruction
- forced dismissal distribution
- task-control occlusion

## 3. STFP는 profile이지 단일 점수가 아니다

Primary report는 다음 vector/profile을 분리 보고한다.

`Spatial / Label / Control / Reveal / Sequence / Depth / Auth / Obstruction`

가중합 단일 score 생성 금지. Secondary visualization으로 Gower/mixed distance를 쓸 수 있으나 규범적 threshold나 ‘고령자 부담 점수’로 해석 금지.

## 4. Family-level summary

family별:
- n=10 denominator 고정
- median/IQR/range
- categorical distribution + entropy
- unique flow signatures
- pairwise matrix visualization

Cross-family 비교는 기술통계 중심. 작은 family n을 과도하게 모집단 일반화하지 않는다.

## 5. Sensitivity

사전 정의만 허용.

- F5 transport: mode-stratum(ground vs air) 병기.
- temporal service transition은 collection_date를 기록하고, 실제 서비스가 collection 시점에 이용 가능하면 원칙적으로 포함.
- app-required는 outcome을 본 뒤 제외하는 것이 아니라 precheck에서 frame 밖으로 replacement.
- evidence defect는 structural failure로 재분류하지 않는다.

## 6. Missingness / denominator

각 family에서:
`candidate 10 → eligible/frozen 10 → attempted 10 → evidence-bearing n → flow-evaluable n`

모든 분모를 단계별로 보고. replacement는 freeze 전에만.

## 7. Claim language

허용:
- “동일 과업의 flow 구조가 서비스마다 다양했다.”
- “공간/label/control/sequence variation이 관측됐다.”
- “한 서비스에서 학습한 procedural cue가 다른 서비스와 구조적으로 일치하지 않는 경우가 많았다.”

금지:
- “이 차이 때문에 고령자의 인지부하가 증가했다.”
- “전이율이 감소했다.”
- “접근성 지침 위반이다.” (KWCAG criterion evidence 없이)

## 8. 권장 시각화

- family별 flow small multiples
- sequence signature matrix
- service×service normalized edit-distance heatmap
- entry-coordinate scatter/small multiples
- label/control/reveal mismatch matrix
- activation-depth dot/range plot
- auth-stage and obstruction categorical plot
