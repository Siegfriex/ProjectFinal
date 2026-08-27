# Data Schema v3.0 — Cross-Service Task Entry Flow

## 1. 계보

`Usage/Policy Rationale → Task Family → Service Candidate → Mobile-Web Eligibility → Frozen Task Contract → L0/Scroll Surface State → Task-Aware Scout → Frozen Path → Replay → Flow/Obstruction/KWCAG Mart → Family Analysis`

대표기능 classifier는 v3 main lineage에 없다.

## 2. 신규/개정 Dimension

### `dim_task_family`
- `family_id`
- `task_family`
- `domain`
- `legacy_archetype`
- `matched_task`
- `task_instruction`
- `fixed_fixture`
- `endpoint_contract`
- `forbidden_actions`
- `version`

### `dim_service_target`
- `service_id`
- `family_id`
- `service_name`
- `provider_type`
- `official_entry_url`
- `requested_url`
- `final_url`
- `mobile_web_eligibility`
- `eligibility_evidence`
- `target_manifest_version`

### `dim_task_contract`
- `task_id`
- `family_id`
- `service_id`
- `task_instruction`
- `fixture_json`
- `endpoint_contract`
- `auth_terminal_allowed`
- `forbidden_action_set`
- `contract_sha256`
- `freeze_status`

## 3. Surface observation

### `fact_surface_state`
한 행 = 한 target의 한 scroll state.

- `observation_id`
- `service_id`
- `task_id`
- `state_index` (`S0`, `S1`...)
- `scroll_y`
- `viewport_width/height`
- `task_control_visible`
- `task_control_candidate_count`
- `entry_x_norm / entry_y_norm`
- `entry_zone`
- `entry_control_type`
- `entry_label_modality`
- `visible_label_text`
- `accessible_name`
- `accessible_name_source`
- `label_relation`
- `nav_container_type`
- `reveal_direction`
- DOM/AX/screenshot/probe manifest pointers

## 4. Flow

### `fact_flow_observation`
한 행 = 한 service-task의 한 run.

- `flow_observation_id`
- `task_id`
- `service_id`
- `endpoint_status`
- `task_flow_sequence`
- `experienced_flow_sequence`
- `activation_depth`
- `flow_step_count`
- `menu_dependency`
- `nav_container_depth`
- `auth_gate_stage`
- `forced_dismissal_count`
- `task_control_occlusion`
- legacy compatibility: `NED`, `IED`, `MPFED`
- `path_manifest_path`

### `fact_flow_step`
- `flow_observation_id`
- `step_index`
- `action_token`
- `state_before_id / state_after_id`
- `control_selector`
- `control_role`
- `control_visible_text`
- `control_accessible_name`
- `bbox_before`
- `url_before / url_after`
- `auth_gate_detected`
- `endpoint_signal_detected`
- before/after DOM/AX/screenshot hashes

## 5. Task-path obstruction

### `fact_task_obstruction`
- `observation_id`
- `interrupt_id`
- `interrupt_type`
- `overlay_coverage` — 보조 설명값
- `task_control_occlusion` — primary
- `dismiss_control_exists`
- `dismiss_control_visible`
- `dismiss_control_accessible_name`
- `dismiss_required_for_task`
- `dismiss_succeeded`

`max_overlay_coverage`만으로 modal obstruction을 대표하지 않는다.

## 6. Axis A / certification

`fact_criterion_result`, `dim_certification`은 v2.1 schema를 승계한다. cross-service flow와 합산점수로 묶지 않는다.

## 7. Legacy mapping

- `dim_representative_task` → historical only. v3 main은 `dim_task_contract` 사용.
- `fact_task_entry` → 삭제하지 않음. v3 `fact_flow_observation`으로 materialize하며 NED/IED/MPFED compatibility 유지.
- 기존 59 mart → read-only robustness cohort.

## 8. Identity / append-only

- `service_id + task_id + run_id`로 observation identity 구성.
- display name을 file id로 사용 금지.
- 재수집은 새 run, 재판정은 새 judgment version.
- path manifest와 evidence manifest는 hash로 연결.
