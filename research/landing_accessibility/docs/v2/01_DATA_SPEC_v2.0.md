# 데이터 명세 v2.0

이 문서는 “각 데이터 표에 무엇을 넣는가”를 설명한다.

기존 `state/*.parquet` 파일은 삭제·rename·migration하지 않는다. 분석용 표는 **매핑/머티리얼라이제이션 레이어**로 만든다.

---

## 1. 데이터 계보

`Wiseapp → Measurement Entity → Web Target → Landing Observation → Representative Task → Feature → Judgment → Analysis Mart`

---

## 2. 기존 정형 데이터

### `dim_panel`

패널 정보.

주요 변수:

- `panel_id`
- `domain`: APP / RETAIL
- `axis_type`
- `source_section`
- `period_axis`
- `metric_name`
- `unit`
- `rows_expected`

### `fact_source_ranking`

Wiseapp 원문 순위행.

- `source_row_id`
- `panel_id`
- `measurement_entity_id`
- `rank`
- `raw_label`
- `raw_value`
- `raw_unit`

### `dim_measurement_entity`

- `measurement_entity_id`
- `canonical_name`
- `source_domain`
- `entity_type`
- `review_status`

### `bridge_source_membership`

한 entity가 어떤 source panel에 등장했는지.

- `measurement_entity_id`
- `panel_id`
- `source_row_id`

---

## 3. 신규 Target / Task 데이터

### `dim_web_target`

- `web_target_id`
- `measurement_entity_id`
- `web_eligibility_status`
- `official_landing_url`
- `final_url`
- `registered_domain`
- `url_evidence`
- `url_confidence`
- `web_target_status`

### `dim_representative_task`

- `task_id`
- `measurement_entity_id`
- `web_target_id`
- `business_domain`
- `interaction_archetype`
- `primary_function_name`
- `endpoint_definition`
- `endpoint_signal_type`
- `mapping_basis`
- `mapping_status`
- `mapping_ai_review_status`
- `human_final_required`

---

## 4. L0 랜딩 관측

### `fact_landing_observation`

한 행 = 한 웹 타겟의 한 수집회차.

- `observation_id`
- `web_target_id`
- `audit_date`
- `protocol_version`
- `requested_url`
- `final_url`
- `redirect_count`
- `measurement_status`
- `viewport_width`
- `viewport_height`
- `screenshot_path`
- `dom_path`
- `ax_path`
- `probe_path`
- `manifest_path`

요약 변수:

- `primary_action_visible_initial`
- `interactive_element_count`
- `visible_link_count`
- `visible_button_count`
- `moving_element_count`
- `modal_candidate_count`
- `blocking_modal_count`
- `max_overlay_coverage`
- `max_primary_action_occlusion`

---

## 5. Popup / Modal

### `fact_interrupt_element`

한 행 = 하나의 방해요소 후보.

- `observation_id`
- `interrupt_id`
- `selector`
- `candidate_source`
- `interrupt_type`
- `bbox_x`
- `bbox_y`
- `bbox_w`
- `bbox_h`
- `viewport_intersection_area`
- `overlay_coverage`
- `z_index`
- `position_type`
- `aria_modal`
- `role_dialog`
- `backdrop_detected`
- `body_scroll_lock`
- `blocks_primary_action`
- `primary_action_occlusion`
- `dismiss_control_exists`
- `dismiss_control_visible`
- `dismiss_control_accessible_name`
- `dismiss_control_width`
- `dismiss_control_height`
- `dismiss_succeeded`
- `classification_status`
- `ai_review_status`
- `final_label`

---

## 6. L1 대표기능 진입

### `fact_task_entry`

한 행 = 한 web target의 대표 task.

- `task_observation_id`
- `task_id`
- `web_target_id`
- `interaction_archetype`
- `endpoint_definition`
- `endpoint_status`
- `NED`
- `IED`
- `MPFED`
- `text_input_episode_count`
- `scroll_episode_count`
- `forced_dismissal_count`
- `auth_gate_before_endpoint`
- `redirect_count`
- `endpoint_reached`
- `path_manifest_path`

### `fact_task_step`

한 행 = 사용자 activation 한 번.

- `task_observation_id`
- `step_index`
- `state_before_id`
- `control_selector`
- `control_role`
- `control_accessible_name`
- `control_visual_text`
- `control_bbox`
- `action_type`
- `url_before`
- `url_after`
- `screenshot_before`
- `screenshot_after`
- `modal_encountered`
- `auth_gate_detected`
- `endpoint_signal_detected`

---

## 7. KWCAG

### `fact_criterion_result`

- `observation_id`
- `criterion_id`
- `older_relevance`
- `applicable_count`
- `pass_count`
- `fail_count`
- `undetermined_count`
- `verdict_state`
- `automation_grade`
- `ai_review_required`
- `final_status`

`older_relevance`:

- VISION
- MOTOR
- COGNITIVE_NAVIGATION
- OTHER

---

## 8. 인증

### `dim_certification`

- `web_target_id`
- `certified_current`
- `certification_number`
- `cert_start`
- `cert_end`
- `target_scope_match`
- `service_identity_match`
- `match_basis`

`certified_current = 1`은 유효기간 + 대상범위 + 서비스 동일성이 모두 맞아야 한다.

---

## 9. AI 검토

### `fact_ai_adjudication`

- `review_item_id`
- `review_task_type`
- `evidence_package_id`
- `deterministic_label`
- `semantic_model_label`
- `reviewer_a_label`
- `reviewer_b_label`
- `reviewer_agreement`
- `arbiter_label`
- `evidence_gap`
- `impact_level`
- `review_priority`
- `final_status`
- `human_required`

---

## 10. 분석용 Mart

### `mart_service_summary`

서비스별 한 행.

핵심:

- KWCAG V/M/C fail
- undetermined
- decision coverage
- MPFED
- ExcessDepth
- modal
- overlay
- forced dismissal
- primary action visibility
- auth gate
- certification

### `mart_archetype_summary`

interaction archetype별:

- n
- MPFED median
- MPFED IQR
- endpoint reach
- modal prevalence
- KWCAG summary

---

## 11. 결측과 상태값

결측을 0으로 바꾸지 않는다.

예:

- URL 없음 ≠ 0
- 적용기회 없음 = NA
- 판단불가 = UNDETERMINED
- 수집 실패 = MEASUREMENT_FAILED
- 로그인 전까지만 가능 = AUTH_GATE_REACHED

상태와 수치는 분리한다.
