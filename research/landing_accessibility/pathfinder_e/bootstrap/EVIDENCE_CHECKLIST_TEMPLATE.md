# Target별 Expected Evidence Checklist

출처: `SSOTV3/02_DATA_SCHEMA_v3.0.md` §3–5, `03_COLLECTION_MEASUREMENT_SPEC_v3.0.md` §10, 내 역할 §7.
50 target 전부 **동일 스키마**를 쓴다 — family 마다 다른 건 endpoint_contract/forbidden_actions
내용이지 evidence 필드 구조가 아니다. 그래서 체크리스트는 하나, family별 주의사항만 별도 표기.

## A. State 공통 (S0 포함 모든 state)

- [ ] `observation_id` / `scout_run_id` / `state_id` / `state_sequence_number`
- [ ] `requested_url` / `final_url` / timestamp(KST)
- [ ] `viewport`(390×844 CSS px) / `device_profile`(mobile UA, touch, ko-KR, Asia/Seoul)
- [ ] DOM snapshot path + sha256
- [ ] AX snapshot path + sha256
- [ ] screenshot path + sha256
- [ ] probe/CSS geometry path + sha256
- [ ] `visible_text_excerpt`

## B. Task-entry control (task control 이 보이는 state에서)

- [ ] `s0_task_control_visible` (S0 기준) / `first_visible_scroll_state`
- [ ] `control_candidates`(순위 매겨 전부) + `selected_candidate`
- [ ] `visible_label_text` **와** `accessible_name` — 반드시 분리 저장
- [ ] `accessible_name_source` (VISIBLE_TEXT/ARIA_LABEL/ARIA_LABELLEDBY/LABEL/ALT/TITLE/VALUE/MIXED/NONE)
- [ ] `label_relation` (MATCH/SEMANTIC_EQUIV/DIFFERENT/VISIBLE_ONLY/AX_ONLY/NONE)
- [ ] `role`/`tag`
- [ ] `bbox` (raw) **와** `entry_x_norm`/`entry_y_norm` (정규화) — 원자료 보존, zone은 요약값일 뿐
- [ ] `entry_zone` / `entry_control_type` / `entry_label_modality`

## C. Navigation / Flow

- [ ] `nav_container_type` / `reveal_direction`
- [ ] `menu_dependency` (endpoint 이전 OPEN/REVEAL 계열 token 존재 여부에서 파생)
- [ ] `nav_container_depth`
- [ ] `task_flow_sequence` (forced dismissal 제외) **와** `experienced_flow_sequence` (포함) — 둘 다 별도 보존
- [ ] `activation_depth` / `flow_step_count`
- [ ] `action_token` per step (04_FLOW_CODEBOOK 18종 중 하나 — 없으면 `ABSTAIN`, 억지 라벨 금지)

## D. Auth

- [ ] `auth_gate_stage` (NONE/BEFORE_TASK_DISCOVERY/AFTER_TASK_SELECT/AT_ENDPOINT)
- [ ] AUTH_GATE 도달 시: 그 state 이후 조작 없음 증거(다음 state 없음 = 정지 증거)

## E. Obstruction (독립축, primary 는 task-specific occlusion)

- [ ] `interrupt_type` / `dismiss_control_exists` / `dismiss_control_visible` / `dismiss_control_accessible_name`
- [ ] `dismiss_required_for_task` / `dismiss_succeeded` / `forced_dismissal_count`
- [ ] `task_control_occlusion` (0~1, task-entry control bbox 실제 겹침 — `overlay_coverage` 는 보조값일 뿐 primary 아님)

## F. Step 전이 (action 발생 시)

- [ ] `url_before` / `url_after`
- [ ] `dom_hash_before` / `dom_hash_after`
- [ ] `ax_hash_before` / `ax_hash_after`
- [ ] `endpoint_signal_detected` / `auth_gate_detected`

## G. 종결

- [ ] `endpoint_status` (REACHED/AUTH_GATE/PUBLIC_WEB_UNOBSERVABLE/APP_REQUIRED/EVIDENCE_DEFECT/BLOCKED/ABSTAIN)
- [ ] `guard_safety_decision` (그 state 에서 왜 진행이 허용/차단됐는지)
- [ ] `forbidden_actions_attempted` = 0 (항상 확인)

## H. Family별 추가 주의 (endpoint_contract 원문 반영, 자동추출 아니고 직접 옮김)

| family | endpoint 도달 판정에서 특히 주의할 것 |
|---|---|
| F1 | LOGIN/IDENTITY gate 가 "task-specific transfer surface" 대신 나타나도 그 자체가 endpoint(AUTH_GATE) — 계정/금액 입력 필드가 보여도 절대 입력하지 않고 그 state 에서 정지 |
| F2 | 상품 상세면에서 가격/상품명 확인되면 endpoint — 장바구니/구매 버튼 존재는 evidence 로 기록하되 클릭 금지 |
| F3 | 운송장 입력 control + 조회 실행 control 이 "보이는" state 가 endpoint — submit 이전에 정지, 실제 번호 입력 자체를 하지 않음(fixture 도 "없음") |
| F4 | 결과 목록/지도가 표시되면 endpoint — 위치권한 프롬프트가 뜨면 허용하지 않고 그 상태를 그대로 기록(대체 텍스트 검색 경로 우선 시도) |
| F5 | mode별 fixture_override(출발/도착역·공항) 사용 — family 기본 fixture 그대로 쓰면 안 됨. 결과목록 표시가 endpoint, 좌석선택 진입 전 정지 |

## 사용법

Worker packet(`WORKER_DISPATCH_PACKETS.json`)에 이 체크리스트 필드명이 `required_evidence_fields_per_state`로
이미 압축돼 들어있다 — REAL scout 시작 시 이 문서를 사람이 다시 읽지 않아도 packet만으로 필드 완결성을
기계적으로 확인할 수 있다(실제로 `build_synthetic_example.py`가 이 원칙으로 44개 필드를 검증했다).
