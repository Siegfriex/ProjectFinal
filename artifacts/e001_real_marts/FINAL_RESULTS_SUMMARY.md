# FINAL_RESULTS_SUMMARY — E001

**스냅샷** 2026-08-27T16:16:51+09:00 (Asia/Seoul) · **등급** PILOT / PRELIMINARY
**mart manifest** `FROZEN_MART_MANIFEST.json` (`sha256:256ae9a9d8721e0d…`)

## 1. 오늘 결론의 핵심

> **코드는 이것을 정직하게 거부했다.** `default_task_definition()`의 docstring이 그렇게 적고 있다 — *"그것이 정직한 결과다 — codebook 없이 endpoint를 만들어내지 않는다"*. 없는 codebook을 추측으로 채워 endpoint를 만들어냈다면 MPFED 값은 나왔겠지만 그것은 관측이 아니라 날조였을 것이다. **측정되지 않은 것을 측정된 것처럼 만들지 않은 설계 선택의 결과다.**

**우리가 값을 못 얻은 것이 아니라, 값을 만들어내지 않기로 한 설계가 작동한 것이다.** 이 구분이 오늘 산출물 전체의 성격을 정한다 — 빈 자리는 실패의 흔적이 아니라 측정되지 않은 것을 측정된 것처럼 만들지 않은 결과다.

## 2. 세 축의 상태

**세 축이 서로 다른 단계에서 막혔다.** 축 A — **판정기 부재**(criterion evaluator가 없다). 축 B — **입력 미연결**(task definition이 `CODEBOOK_PENDING`으로 고정돼 판정기가 쓸 입력이 연결되지 않았다). 축 C — **판정기 미완**(semantic 단계 없이 결정론 규칙만 돈다). 세 축을 한 문장으로 뭉뚱그리면(예: '수집기는 만들어졌고 판정기는 만들어지지 않았다') 축 B가 틀린 서술이 된다 — 축 B의 판정기는 존재하며, 쓸 입력이 없었다.

**MPFED 0/59는 수집을 돌리기 전에 구조적으로 확정돼 있었다.** `e001_runner/executor.py`의 `default_task_definition()`이 스스로 밝힌다 — P-A endpoint codebook이 동결되기 전에는 서비스별 `region_definition`/`endpoint_definition`이 존재하지 않아 `CODEBOOK_PENDING`을 그대로 두며, **그 상태에서 Scout를 돌리면 QUERY를 제외한 모든 archetype은 area/endpoint 신호가 결코 성립하지 않는다.** 유일한 예외인 QUERY 5건은 **전부 Scout 이전에 차단됐다**(4건 `ACCOUNT_ACTION_BLOCKED` scout_invoked=false, 1건 `SKIPPED_RETRY_EXHAUSTED`). **충분원인이 둘이고 서로 겹치지 않으므로** MPFED가 산출될 경로는 애초에 없었다.

## 3. 수집 커버리지

- `attempted_observations` **59** (시도한 관측 건수)
- `unique_targets` **59** (서로 다른 서비스 수)
- `coverage` 59 / 59 = **1.0**
- `joint_valid_n` **0** — J3(MPFED 산출)이 충족되지 않았다. 이 숫자를 살리려 정의를 바꾸지 않았다.
- `l0_analyzable_n` **0** — J4(older-relevant 중 1건 이상 판정)가 충족되지 않았다(축 A 미평가).
- `attempted_observations`(시도한 관측 건수)와 `unique_targets`(서로 다른 서비스 수)는 **다른 숫자다** — 재시도·중복발사 격리분이 관측 수를 부풀린다. 'N건 시도'를 'N개 서비스'로 쓰지 않는다.

### 탐색이 인증 gate에 도달해 종결된 서비스

**12건**이다. 이 서비스들은 진입 깊이 표본에서 빠지지만 **빠졌다는 사실 자체가 결과다** — 서술에서 사라지면 은폐가 된다.

다만 이것은 **탐색이 그 지점에서 종결됐다**는 관측이지, 대표기능의 위치에 관한 확인이 아니다. 그 확인을 하려면 gate를 통과해야 하고 통과는 금지돼 있다 — **우리는 원리적으로 모른다.**

초기 화면에 로그인/구매/가입 관련 텍스트 후보가 존재해 계정행동 가드가 탐색을 중단시킨 경우는 별도로 25건이다.

## 4. 축 C — 초기 화면 방해요소 (오늘 유일한 실측 축)

상태 `RAW_MEASURED_CLASSIFICATION_INCOMPLETE` — raw 는 실측(235건) · 분류는 47% 미분류

- L0 산출물을 보유한 56개 관측에서 방해요소 235건이 탐지됐다.
- `final_label`이 `UNKNOWN`인 것이 110건(46.8%)으로 **최대 범주**다.
- 겹침 분포는 **양극**이다 — 완전히 덮은 관측 22건(39.3%) · 겹침 없음 6건 · 가운데 구간(0.25~0.75) 2건뿐. median 단독 인용은 오도한다.
- dismissal 4조합:
  - 102건 — 닫기 컨트롤 미관측 · 해제됨 (ESC/backdrop 경로)
  - 64건 — 닫기 컨트롤 관측 · 해제됨
  - 38건 — 닫기 컨트롤 관측 · 해제 실패
  - 30건 — 닫기 컨트롤 미관측 · 해제 안 됨
  - 1건 — 기타/미기록
- 우리가 관측한 것은 **자동화 도구의 dismissal 결과**이지 사용자 행동이 아니다 (축 B의 '우리 도구의 도달 한계이지 사용자의 도달 한계가 아니다'와 같은 구분).

## 5. 축 B — 진입 깊이 미산출의 원인 분해 (관측 outcome 층위)

**이 6종은 관측 가능한 outcome 층위의 분해이며, 원인 설명의 완결이 아니다.** 각 관측이 '어떤 결과로 끝났는가'를 가른 것이지 '왜 그 층에 도달했는가'까지 내려간 것이 아니다. 그 아래 층 — task definition이 측정기에 전달되는가 · probe가 실사이트에서 볼 신호가 있는가 — 은 post-E001 recovery lane에서 **별도 감사 중**이며, 그 결과에 따라 이 분해가 '그 위에 더 근본적인 원인이 있었다'로 재해석될 수 있다(`LIMITATIONS.md` §11).

- **25건** (42.4%) `OUR_TOOL_CONSTRAINT` — 가드 입도 — 우리 도구의 제약
- **11건** (18.6%) `OUR_CONTRACT_DESIGN` — archetype-endpoint 규칙 자체 — 본 연구 계약의 설계
- **18건** (30.5%) `MIXED` — UNRESOLVED — budget_reason으로 분해
- **3건** (5.1%) `OUR_CIRCUMSTANCE` — SKIPPED_RETRY_EXHAUSTED — 우리 쪽 사정
- **1건** (1.7%) `TARGET_PROPERTY` — CAPTCHA — 대상의 성질
- **1건** (1.7%) `MEASUREMENT_LIMIT` — E-6b 구속 — 측정기 한계

- E-6b는 8건에서 **발화**했으나 실제로 결과를 바꾼 것(구속)은 1건이다. 승격은 `A2 §1.5.1`+`00_SSOT §3`이 FINANCIAL_ACTION_ENTRY·COMMUNICATION_ENTRY 2종으로 한정하므로, 나머지 archetype에서는 gate 종류를 정확히 판별했어도 MPFED가 NULL이다. **발화 횟수를 원인으로 쓰면 과대평가다.**

### 반사실 — 가드는 구속 조건인가

- 가드 입도는 25건에서 L1 탐색을 차단했으나 **구속 조건은 아니다.** 가드가 개입하지 않은 25건에서도 endpoint 도달이 0이었다. 더 근본적인 제약은 **이 측정 접근이 이 프레임의 대표기능 진입점에 닿지 못한다**는 것이며, archetype-endpoint 규칙이 그것을 정의 수준에서 확정한다.
- 회복 상한 `0~8` · 라벨 `CURRENT_IMPLEMENTATION_CONDITIONAL_COUNTERFACTUAL`
- **적용 범위**: **이 결론은 현재 collector/measurement 구현 하에서만 성립한다.** task definition이 `CODEBOOK_PENDING`으로 고정된 상태를 전제한 값이므로, *'올바른 task-definition wiring과 signal detector를 구현해도 depth는 최대 8'*로 확대해 읽으면 **거짓이다.** 그 경우의 상한은 오늘 데이터로 알 수 없다.
- **추론 한계**: 무작위 배정이 아니다 — 가드 발화가 페이지 텍스트에 의존하므로 Scout이 돈 25건과 가드에 막힌 17건이 체계적으로 다를 수 있다. 뒷받침하는 근거는 두 집단의 archetype 구성이 유사하고(양쪽 ITEM_DETAIL 지배) Scout 쪽이 예외 없이 0/25라는 것이다. 확정하려면 가드를 고친 뒤 같은 프레임을 재수집해야 하고 오늘 하지 않았다.

### 더 아래 층 — 감사 중 (`claude-b/measurement-recovery`)

- task definition wiring — CODEBOOK_PENDING 고정으로 Scout에 전달되지 않는다
- 실웹 signal detector — probe가 보는 data-region/data-endpoint 속성은 fixture가 심는 것이며 실사이트에는 없다
- wiring을 고쳐도 probe가 실사이트에서 볼 신호가 없다 — 원인이 이 표보다 한 층 더 아래에 있다는 뜻이다. **이 표가 틀린 것이 아니라 층이 다른 것이다.**

## 6. 등급

**PILOT / PRELIMINARY** — 커버리지 100%가 등급을 올리지 않는다 — 결과가 예상보다 좋다는 이유로 사전 규칙을 뒤집는 것도 나쁠 때 뒤집는 것과 같은 실패다. 등급과 커버리지를 둘 다 보고한다.

## 7. 과정에서 발견된 것

**검증 실수가 7건 있었고 그중 상당수는 결론을 바꿀 수 있었다.** 상세는 `STATISTICAL_RESULTS.md` §4.5에 있다 — 오류를 먼저, 그것을 잡은 구조를 나중에 적었다.

요약: '있다고 가정했으나 없었던' 것이 3회 나왔고 이는 **한 개의 점검 누락이 세 번 발현된 것**이다(비어 있던 칸: `이 단계의 산출물을 만드는 코드가 실재하는가`). 검증 실수 7건은 **형식 미확인**과 **범위 확장** 두 유형으로 압축된다. **상위가 하위를 검사하는 단방향 구조였으면 이 중 어느 것도 안 잡혔다.**

## 8. 한계

`LIMITATIONS.md` 11개 항목을 참조한다. 특히:

- §4 반사실의 비무작위 배정 한계 (회복 상한은 현재 구현 하의 조건부 값)
- §5 older-relevant 태깅은 연구진 판정 (청각 도메인 부재 포함)
- §8 축 C 47% 미분류
- §11 원인 귀속표 전체가 recovery lane 감사 결과에 따라 재해석될 수 있다

---

> 본 연구는 실제 고령자의 행동·포기·학습효과를 직접 관측하지 않았다. 어떤 결과도 그것을 말하지 않는다. 오늘 N은 작고 그 사실이 모든 문장에 따라다닌다. **우리가 관측한 것은 우리 도구의 도달 한계이지 사용자의 도달 한계가 아니다.**

입력 SHA: `{"collector_sha": "222ef2c28ed5971b3c9f8b07120b7627d2617476", "plan_hash": "b48be3cb5e2cb992c0b9ee44306a4f3bd3cee8fbd601de5f14ebb82f75a9e2bc", "older_relevance_registry_sha256": "da4b5208c91dd7634fc9e50d7a883674ad7666fc3828f359e4f428b3be863f8e", "protocol_version": "v2.0-pc-fixture-1", "e001_release_control_sha256": "ba745758aa3d324aca6dd4a520a9cdc47de97f7b68cd8a4ef46dcf2d75276c23", "promoted_main_sha": "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d", "note": "MART_ACCEPTANCE §1-7 입력 SHA. 이 블록은 FROZEN_MART_MANIFEST.json과 REAL_RUN_SUMMARY.json 양쪽에 동일하게 실린다."}`