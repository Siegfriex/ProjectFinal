# C_LABEL_RAW_AUDIT — RAW_L1/L3/L4 (41행) provenance·coverage·quality 감사 + F-A1/F-A2 재계산

**target** `control@d8f8595c01d20cde8a01e749bffafa8c1c697ef5` `control/label/RAW_{L1,L3,L4}.jsonl` (L2 미도착) · **producer** C · labels_produced 0
**감사 시각** 21:24 KST (`date`)

## §1 provenance / coverage — PASS
| 검사 | L1 | L3 | L4 |
|---|---|---|---|
| rows = partition, 중복 0 | 16 ✓ | 14 ✓ | 11 ✓ |
| 필수필드(archetype·evidence_ref·decision_trace) 100% | ✓ | ✓ | ✓ |
| archetype ∈ 7 ∪ AMBIGUOUS_UNRESOLVED | ✓ | ✓ | ✓ |
| evidence_ref 출처 | dom/ax/screenshot 만 | dom/ax/probe/screenshot | dom/ax/computed_css |
| 금지입력(mart/detector/MPFED/KWCAG/outcome) 참조 | 0 | 0 | 0 |
| split 소속 | cal 16 / hold 0 | cal 14 / hold 0 | cal 0 / hold 11 |

**교락(C-BLOCKER-211259) 은 실현됐다** — L4(holdout 11) 는 이미 산출됐다. 재배정 대신 §3 의 겹침 이중라벨이 필요하다.

## §2 quality — 관측 구조가 prior 를 42% 뒤집는다 (ANALYSIS, 사전등록 필요)
```
41 rows = mapped 31 + AMBIGUOUS_UNRESOLVED 10 (24%)
mapped 31 중 prior(CSV archetype) 와 일치 18 (58%) · 불일치 13 (42%)
```
불일치 13 (prior → label): ITEM_DETAIL→PLACE_LOOKUP ×4(편의점 3·기타1) · ITEM_DETAIL→CONTENT_OPEN ×3 · ITEM_DETAIL→QUERY ×1 · UTILITY→CONTENT_OPEN ×2 · UTILITY→ITEM_DETAIL ×1 · COMM→QUERY ×1 · PLACE→CONTENT_OPEN ×1.
abstain 10 은 전부 "prior 는 강하지만 관측 DOM 에 region 없음"(스플래시·로그인 URL·로딩 스켈레톤·SPA 부트스트랩·기업소개·404).

**함의(C 판단)**
1. D-R0-10 "observed 가 이긴다" 를 적용하면 **archetype n 분포가 prior 와 크게 다르다**: ITEM_DETAIL 26 이 유지되지 않고 PLACE_LOOKUP/CONTENT_OPEN 이 커진다. SSOT §12 n 규칙과 ExcessDepth baseline(같은 archetype median)은 **관측 archetype** 기준이어야 하며, 어느 쪽을 쓰는지 지금 DECISION 으로 고정해야 한다(결과 후 선택 금지).
2. split 은 prior 로 층화했으므로 관측 archetype 기준으로는 **불균형**할 수 있다 — L2 도착 후 C 가 교차표 제시. split 을 바꾸지는 않는다(동결).
3. detector holdout gate `agreement ≥ 0.85` 의 정답은 이 라벨이다. 라벨 자체가 prior 와 58% 만 일치하므로 **B 가 prior(CSV archetype) 를 Layer P 입력으로 강하게 쓰면 holdout 에서 구조적으로 실패**한다 — 이는 detector 결함이 아니라 계약대로의 결과다. B 에 사전 고지 가치 있음(라벨 내용은 노출하지 않음, 통계만).
4. abstain 24% → coverage gate 0.75 는 evidence 품질(degenerate capture) 때문에 **detector 와 무관하게** 위태롭다. coverage 분모에서 라벨이 AMBIGUOUS 인 관측을 제외할지 A 가 사전 결정.

## §3 C-BLOCKER-211259 갱신 — 라벨 산출 후 remedy
L1·L3 (calibration) 와 L4 (holdout) 이미 산출. **요구**: 겹침 표본 — holdout 에서 8건을 L1/L3 가, calibration 에서 8건을 L2/L4 가 추가 라벨(라벨러는 split 을 모른 채) → inter-labeler agreement 를 holdout ceiling 으로 gate 판정문에 병기.

## §4 F-A1 / F-A2 독립 재계산 — MATCH
- F-A1: mart 56 = MEASURED 53 + FAILED_EVIDENCE_INCOMPLETE 3 (coupangeats·shinhan·e-himart) ✓. 4층 분모(59/56/53/3) 동의.
- F-A2: mart 56 관측 dom.html sha256 전수 — 중복군 **1군뿐** (`b783cbd0…` NH스마트뱅킹·NH콕뱅크), final_url 중복군도 동일 1군 ✓. dom 크기 표(314/1657/1657/6072/132077/675876/20481) ✓.

## §5 D-A-후보-1~4 에 대한 C 판단
| 후보 | C |
|---|---|
| 1 분모 매 지표 명시 | **동의**. 추가: 지표별 분모를 mart 컬럼이 아니라 `analysis_frame_layer ∈ {attempted59, bytes56, measured53, labeled_mapped}` 로 기계판독 필드화(W4) |
| 2 NH 쌍 중복 표시+묶음 감도 | **동의**. 독립 관측 가정 위반이므로 primary 분석에서는 1건으로 접고(서비스 단위 frame 이지만 관측 단위가 같음), 둘로 세는 쪽을 감도분석으로 두는 것이 보수적. 어느 쪽이 primary 인지 사전 고정 |
| 3 degenerate 3건 UNDET 유지 | **동의**. 단 라벨러가 abstain 한 degenerate 는 3건이 아니라 **10건 계열**(§2) — Axis A 에서도 이들은 criterion applicability 자체가 성립하지 않을 수 있음(NA vs UNDET 구분 필요) |
| 4 informative missingness 확장 | **동의, 주장 아님**. 결측/degenerate 가 금융·앱중심에 몰리는지는 W4 에서 archetype×status 교차표로 기술만. n 이 작아 검정 금지 |

## §6 이 감사가 확인하지 않은 것
L2 라벨(미도착) · 라벨러 워커의 실제 프롬프트 · 라벨 파일 sha256 동결(미동결 — A 가 L2 통합 후) · degenerate 원인(WAF/NetFunnel/JS) · NH 두 서비스의 실제 랜딩 수렴 여부
