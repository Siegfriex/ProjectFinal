# C_W4_PRE_COMPLETION_DIFF_AUDIT — claude-b/w4-axisc-mart @cf8dbd70af (completion 전 read-only)

**producer** C · production_modified false · 감사 시각 21:43 KST · 대상 diff 2281c85..cf8dbd7 (l0_collector.py 수정 1, build_mart_axisc.py 신규, test_w4_axisc_mart.py 신규)

## §1 통과 (코드 구조 + C SUT 실행)
- geometry 불변: `classify_interrupt` 는 (status,label) 만 반환, `axis_c_page_level_from_probe` 는 저장된 스칼라만 집계, box-overlap 미호출 — B 테스트가 구조적으로 증명(monkeypatch 검사 포함). C SUT 실행에서도 status 전이는 라벨과 독립.
- 4층 분모(59/56/53/3) 디스크 유도, 하드코딩 금지 테스트, duplicate launch 4건 EXCLUDED 행 유지, NH 쌍 same-group 플래그, cap 플래그(pac/ans/ts/contrast/anim), `primary_action_occlusion` 상수 None + PENDING_TASK_BINDING, degenerate 3건 UNDET 유지 — 전부 D-R0-24/25/45/53/55 와 정합.
- `SEMANTIC_MODEL` 어휘는 2281c85 vocabulary 에 이미 존재(신규 어휘 0).

## §2 FINDING (P2, construct validity) — tier 재배열이 의미 라벨을 `BANNER` 로 붕괴시킨다
2281c85 는 텍스트 어휘 → 구조 순, cf8dbd7 은 구조 → 텍스트 순(D-R0-25 문구 그대로). C 가 B 함수를 두 SHA 로 실행해 E001 probe 58건의 modal_overlay_candidates **635건**을 대조:

```
label 변경 22 / 635  (관측 17건)          status: DETERMINISTIC→SEMANTIC_MODEL 17, 나머지 불변
  LOGIN_PROMPT      → BANNER   9
  PROMOTION_MODAL   → BANNER   5      PROMOTION_MODAL → BLOCKING_MODAL 1
  CHAT_WIDGET       → BANNER   2      APP_INSTALL_PROMPT → BANNER 1 / → PROMOTION_MODAL 1
  COOKIE_CONSENT    → BANNER   2      ADVERTISEMENT → BANNER 1
```
원인: tier 1 의 `position_sticky/fixed → BANNER` 와 `dialog/aria-modal → BLOCKING/PROMOTION_MODAL` 은 **형태(geometry class)** 규칙인데 **의미 라벨 필드** 를 선점한다. 그 결과 "로그인 유도 sticky bar" 가 LOGIN_PROMPT 를 잃고 BANNER 가 된다. D-R0-25 의 취지(확신도 tier)가 구현에서는 **의미 정보 손실**이 됐다 — 이는 "semantic 이 geometry 를 바꾸지 않는다" 의 역방향, **geometry class 가 semantic 을 덮는** 결함이다.

권고(구현 방식은 B 재량): interrupt 를 두 축으로 분리 — `form ∈ {BLOCKING_MODAL, PROMOTION_MODAL, BANNER, …}` (구조 tier) 와 `semantic ∈ {LOGIN_PROMPT, COOKIE_CONSENT, CHAT_WIDGET, APP_INSTALL_PROMPT, ADVERTISEMENT, …}` (텍스트 tier), 각각 status 병기. 어느 쪽도 다른 쪽을 덮지 않는다. 이것이 SSOT §3 Axis C "interrupt type" 의 construct 를 보존한다.

또한 canonical FINAL(82f631f) 의 interrupt 라벨 분포(UNKNOWN 110/235 등)와 새 mart 의 분포는 **분류기 버전이 달라** 직접 비교 불가 — W4 completion 은 `classifier_version` 과 old→new 전이표를 provenance 로 남겨야 한다.

## §3 미확인
build_mart_axisc.py 실행 산출(B completion 시 artifact sha 로 검산) · 4층 분모 실계수(C 는 59/56/53/3 을 이미 독립 재계산함 — 동일해야 함) · duplicate EXCLUDED 4행의 target 매핑
