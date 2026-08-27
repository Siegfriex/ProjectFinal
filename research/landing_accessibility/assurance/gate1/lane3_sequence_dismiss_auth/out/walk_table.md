| fixture | role | recorded steps | S0 occl (hit/geo) | S0 overlay cov | fvss | terminal | result |
|---|---|---|---|---|---|---|---|
| seq_menu_category_function_endpoint | POSITIVE | 6/6 | 0.00/0.00 | 0.000 | NONE | ENDPOINT_REACHED | PASS |
| seq_with_forced_dismissal | POSITIVE | 7/7 | 1.00/1.00 | 1.000 | NONE | ENDPOINT_REACHED | PASS |
| seq_non_blocking_banner | NEGATIVE | 6/6 | 0.00/0.00 | 0.076 | NONE | ENDPOINT_REACHED | PASS |
| auth_generic_login_present_no_gate | NEGATIVE | 1/1 | 0.00/0.00 | 0.000 | S0 | ENDPOINT_REACHED | PASS |
| auth_gate_after_task_select | POSITIVE | 1/1 | 0.00/0.00 | 0.000 | S0 | AUTH_GATE | PASS |
| auth_gate_before_discovery | POSITIVE | 0/0 | n/a | 0.000 | NONE | AUTH_GATE | PASS |
| auth_gate_at_endpoint | POSITIVE | 4/4 | 0.00/0.00 | 0.000 | S0 | AUTH_GATE | PASS |
| seq_typing_and_scroll_not_depth | POSITIVE | 3/3 | n/a | 0.000 | S1 | ENDPOINT_REACHED | PASS |

RESULT: ALL PASS (8/8 fixtures) -> /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane3_sequence_dismiss_auth/out/walk_result.json
