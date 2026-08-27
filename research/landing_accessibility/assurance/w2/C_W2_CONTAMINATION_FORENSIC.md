# C_W2_CONTAMINATION_FORENSIC — Director C2 (holdout-derived 3건의 W2 전달 흔적 조사)

**대상** `claude-b/w2-rf-detector` 커밋 1de537c(21:40) → bd5e33d(21:56) → f76ee8b(22:03). 누출 시점: D-R0-61 push 21:52:45 → B 가 W2 에 전달(B attestation) → 이후 커밋 = bd5e33d, f76ee8b.
**방법** 누출 전후 diff(`bd5e33d..f76ee8b`)와 전체 diff(`2281c85..f76ee8b`)에 대해 (1) 누출 식별자 grep(gsretail/gs25/toss/daiso/wtg_12e3942c/35319a42/377983572b + 나머지 holdout 노출 5건 id/도메인), (2) target 특화 조건문·threshold·tie-break, (3) 테스트/픽스처 삽입. 대조군: `PLACE_LOOKUP` 6 hit(스캐너 생존).

| 검사 | 결과 |
|---|---|
| holdout 3건 id/site/domain | **0 hit** (전후 diff 모두) |
| 나머지 holdout 노출 5건 id/domain | 0 hit |
| candidate 쌍 특화 조건문 | 없음 — 추가된 `_tier2_primary_surface_favors` 는 "list 계열 vs 검색 계열" 만 가르는 **generic** 규칙(MIN-4 1위 candidate 소속), list-vs-list 는 명시적으로 AMBIGUOUS 유지, NLP 미사용, threshold 상수 없음 |
| 테스트 | tier2 search-vs-list / query-favored / list-vs-list-ambiguous / custom-URI-scheme 4건 — 전부 generic 합성 픽스처. `mplweb.ahnlab.com` 언급 1건은 **calibration** 항목(Director 허용 명시) |
| l0_probe.js 누출 후 diff | 어휘/selector 추가 없음(cap·truncation·marker 게이팅만) |

**판정: `CLEAN`** — 누출된 3건에 대한 target 특화 흔적 없음, 규칙은 RF-DT §6 Stage 4 계약에서 도출된 generic 규칙.
**caveat(설계 수준 노출 위험, 오염 아님)**: tier2 규칙이 경합 유형 중 "검색 vs list"(daiso 유형)만 가를 수 있게 설계된 것은 D-R0-61 이 공개한 경합 *유형* 지식과 일치한다. 유형 지식은 D-R0-61 SUPERSEDE 후에도 남는 공개 계약 정보이므로 오염으로 보지 않되, holdout 채점에서 PRECEDENCE_CONTESTED 제외값(23)을 병기하는 이유가 바로 이것이다.
**미확인**: W2 worker 의 로컬 미커밋 상태 · 향후 커밋(completion SHA 에서 재실행).
