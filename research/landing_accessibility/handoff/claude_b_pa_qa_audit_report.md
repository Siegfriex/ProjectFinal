# P-A-QA — 독립검증 보고 (Claude B)

- lane: `claude-b/pa-qa`
- 감사 대상: `agent/landing-pa-shadow` @ `0f46203` ("shadow(LANE-A): P-A 선행산출 이관·재현검증 …")
- 감사자는 `0f46203`을 직접 수정하지 않았다. 이 문서와 `claude_b_change_requests/*.md`만 새로 추가했다.
- 참고(대조군, 정답 아님): `.agent_worktrees/claude_b_pa_shadow` — 같은 범위를 독립적으로 재구현한 다른 워커의 산출물

## 1. 무결성/재현 (실측)

| 항목 | 결과 |
|---|---|
| `SHADOW_MANIFEST.json.artifact_sha256` 27건 재계산 | **26/27 일치, 1건 불일치** → `CR-001` |
| `SHADOW_MANIFEST.json.source_frame_sha` (state/*.parquet 6종) | 6/6 일치 |
| `analysis/mapping` pytest | 24 passed (재확인) |
| `ruff check .` / `ruff format --check .` | 전부 통과 (재확인) |
| `mypy analysis_interface.py test_analysis_interface.py pilot_mapping.py` | 통과 (재확인) |
| `eda00_frame_provenance.py` 재실행 → `EDA00_OUT` scratch 비교 | findings/measured/raw_output 3종 **바이트 동일** |
| `eda01_source_structure.py` 재실행 → `EDA01_OUT` scratch 비교 | console/csv 3종 + PNG 3종 **바이트 동일** |
| `pilot_mapping.py` 재실행 → `PILOT_OUT` scratch 비교 | `pilot_mapping.jsonl` **바이트 동일**. `mapping_run_manifest.json`은 타임스탬프·워크트리 절대경로 필드만 다름(예상됨, `CR-001` 참고) |
| EDA-00 severity 재확인 | P1 9 / P2 6 — 커밋 메시지가 밝힌 시정치와 일치 |

## 2. Adversarial contamination 시험 (직접 수행)

- `pilot_mapping.py`의 `builtins.open` 가드가 **pandas.read_parquet 경로도 실제로 가로채는지** 별도 스크립트로
  확인 — `pd.read_parquet()`이 pyarrow 백엔드를 쓰더라도 `builtins.open`을 실제로 통과함을 실측 확인
  (manifest의 "pandas.read_parquet 도 이 open 을 거친다" 주장이 사실임을 독립 재현).
- `service_master` 컬럼 화이트리스트(`SERVICE_MASTER_T1_COLUMNS`)가 로드 직후 실제로 슬라이스됨을 코드 추적으로 확인
  — 선언이 아니라 강제.
- `load_allowed()`의 닫힌 allowlist(`ALLOWED_FILES` dict) 밖 이름은 `InputAllowlistViolation`을 던짐 — 코드 추적 확인.
- `denied_inputs`에 문서로만 적힌 `state/web_target_group.parquet`은 `DENY_PATH_FRAGMENTS` 키워드 목록에는
  없지만(경로에 "web_target_group"이라는 조각이 없다), 스크립트 전체에서 실제로 한 번도 열리지 않음을 grep으로 확인
  — 서술과 동작이 일치. (참고: 이 파일명이 우연히 `DENY_PATH_FRAGMENTS`에 걸리지 않는다는 사실 자체는, 이 스크립트가
  그 파일을 여는 코드를 새로 추가할 경우 아무것도 막지 못한다는 뜻이기도 하다 — 지금은 위험하지 않지만
  방어심층 목적이라면 `web_target_group`도 조각 목록에 추가해두는 편이 안전하다. blocking 사유는 아니다.)
- `guard_selftest`(certification_registry.parquet 프로브)가 재실행에서도 `GUARD_WORKS`로 재현됨.

## 3. Codebook ↔ SSOT 대조

- Business Domain 8종·Interaction Archetype 7종의 코드와 순서가 `00_SSOT_v2.0.md §6`과 정확히 일치
  (`PORTAL_SEARCH, CONTENT_VIDEO, NEWS_CONTENT, SHOPPING_COMMERCE, MAP_MOBILITY, FINANCE_PAYMENT,
  SOCIAL_COMMUNICATION, UTILITY_OTHER` / `QUERY, CONTENT_OPEN, ITEM_DETAIL, PLACE_LOOKUP,
  COMMUNICATION_ENTRY, FINANCIAL_ACTION_ENTRY, UTILITY_ENTRY`). 결함 없음.
- `mapping_status` 값 자체는 A2 §1.9 전이표와 어긋남 → **`CR-002` (P1 제안)**.

## 4. gate-kind / UTILITY_ENTRY 정직성 (task #8)

- SSOT §6은 `UTILITY_ENTRY`를 archetype으로 열거하지만 §3 L1 endpoint 표에는 대응 행이 없다.
- 코드북은 이를 숨기지 않고 `Q-2 (P1/blocking)`로 등재했고, pilot에서 `UTILITY_ENTRY`로 떨어진 2건
  (`device_care`, `my_files`)은 `region_signal_type = "CODEBOOK_PENDING"` + `freeze_blocked_by`에
  `"FRZ-4 (region_signal_type=CODEBOOK_PENDING · Q-2 미결)"`을 명시적으로 달았다. **강제분류 없음. 정직한 처리.**
- gate 종류(로그인 vs 본인인증) 판별 규칙 미비는 `Q-9`로 스스로 신설해 등재했고, 실제 gate 화면을 관측하지 않고
  규칙을 만들면 임의 조작화가 된다는 이유로 **판별기준 자체를 만들지 않음** — P0 종료 전 real-target 금지(§4.1)를
  존중한 결정. 결함 아님.

## 5. Abstain path / HUMAN_FINAL_REVIEW_MAX (task #6)

- pilot cascade는 실제로 강제분류하지 않고 6/15를 abstain(`AMBIGUOUS_UNRESOLVED`)으로 흘려보냈다 —
  경로 자체는 작동한다.
- **다만 이 abstain의 원인은 "모호해서"가 아니라 "stage 4(AI review)가 P0 이전이라 아예 실행 불가"다.**
  이 사실은 `PA_FINDINGS_REGISTRY.json`의 `PILOT-ABSTAIN-CAUSE-IS-GATE-NOT-AMBIGUITY`(P2, OPEN)로
  이미 자체 등재돼 있음을 확인했다 — 독립적으로도 같은 결론에 도달했다.
- 따라서 **`HUMAN_FINAL_REVIEW_MAX = 5` 상한 자체(초과분이 실제로 인간 큐에서 잘리는지)는 이 pilot에서
  전혀 검증되지 않았다** — stage 4/5/6이 구조적으로 실행되지 않기 때문이다. 이것은 `0f46203`의 결함이 아니라
  A0 SHADOW 정책(§4.1)이 의도한 제약이며, `PILOT_MAPPING_REPORT.md`도 이를 숨기지 않고 명시한다.
  P-C 엔진이 준비돼 real-target 수집이 열리기 전까지는 이 항목이 **미검증 상태로 남는다**는 점을
  후속 감사가 명확히 인지해야 한다.

## 6. 15건 pilot mapping replay (task #7)

- `0f46203`이 뽑은 15개 서비스의 `DOMAIN_RULES`/`ARCHETYPE_RULES` 정규식 매칭을 손으로 재추적해
  9건의 RULE 해소와 6건의 abstain을 각각 검증했다. **9건의 RESOLVED 판정에 이견 없음.**
  6건의 abstain(`11st`, `baemin`, `chrome`, `coupang_eats`, `kakaotalk`, `mega_coffee`)도 각각
  이름에 archetype 키워드가 없고 stage3 임베딩 마진이 노이즈 수준(≤0.02)이라는 점에서 **abstain이 맞다** —
  사람이 외부 지식으로는 쉽게 분류할 수 있는 항목(`chrome`=브라우저 등)이라도 source-only 원칙상
  강제분류하지 않은 것은 설계 의도대로다.
- `claude_b_pa_shadow`(대조군, 다른 15건 표본 선정 — 겹치는 4건: `device_care`, `emart`, `hana_bank`, `kakaotalk`)와
  비교: `emart`·`hana_bank`는 domain/archetype 완전 일치. `device_care`는 대조군이 별도 prior 파일
  (`_researcher_priors/system_app_hypothesis.json`, T1 allowlist 밖)을 근거로 abstain했고 `0f46203`은
  RULE 매칭으로 resolve — 후자는 T1 입력만으로 정직하게 도달한 결론이라 절차상 옳다(대조군이 T1 밖 입력을
  썼다는 점이 오히려 대조군 쪽의 절차 이탈).
  **`kakaotalk`에서 유의미한 불일치**: `0f46203`은 소스맥락 신호 없음 + 낮은 임베딩 마진으로 abstain했는데,
  대조군은 `"메신저/커뮤니케이션 서비스로 공개적으로 알려져 있다"`는 **공개 배경지식**으로 resolve했다.
  대조군 자신도 다른 항목(`band`)에서는 "공개적 배경지식을 끌어오면 강제분류가 된다"며 명시적으로 거부한 바로
  그 방법을 `kakaotalk`·`netflix`·`youtube`·`daum`·`naver_app`·`kakaomap`·`tmap`·`coupang_app`·`cashwalk`에는
  적용했다 — 대조군 내부에서 방법론 일관성이 깨진 것으로 보인다. 이 사례는 `0f46203` 쪽이 아니라
  **대조군의 약점**이며, `0f46203`의 더 보수적인 abstain이 PHASE_GATES §4.2 "source-only mapping" 원칙에
  더 부합한다는 근거로 본다. (대조군 파일은 수정하지 않았다 — 참고만 했다.)

## 7. 최종 판단

`0f46203`은 스스로 주장한 재현성·오염차단·정직한 미결 처리 대부분을 독립 재현에서 **실제로 통과**했다.
발견한 결함은 두 건이며 둘 다 새 real-target 접근이나 안전 위반이 아니라 **provenance 문서/어휘 정합성** 문제다:

- `CR-001` (P2) — manifest 자기 해시 불일치 1/27건
- `CR-002` (P1 제안) — `mapping_status` 값이 A2 §1.9 전이표를 따르지 않음

둘 다 `agent/landing-pa-shadow`를 직접 고치지 않고 proposal로만 등재했다. P-A 감사(adversarial/ssot)가
판정 권한을 갖는다.
