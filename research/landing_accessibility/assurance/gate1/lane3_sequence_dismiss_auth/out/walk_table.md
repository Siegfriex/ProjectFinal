| fixture | role | recorded steps | S0 occl (hit/geo) | S0 overlay cov | fvss | terminal | result |
|---|---|---|---|---|---|---|---|
| seq_menu_category_function_endpoint | POSITIVE | 6/6 | 0.00/0.00 | 0.000 | S0 | ENDPOINT_REACHED | PASS |
| seq_with_forced_dismissal | POSITIVE | 7/7 | 1.00/1.00 | 1.000 | S0 | ENDPOINT_REACHED | PASS |
| seq_non_blocking_banner | NEGATIVE | 6/6 | 0.00/0.00 | 0.076 | S0 | ENDPOINT_REACHED | PASS |
| auth_generic_login_present_no_gate | NEGATIVE | 1/1 | 0.00/0.00 | 0.000 | S0 | ENDPOINT_REACHED | PASS |
| auth_gate_after_task_select | POSITIVE | 1/1 | 0.00/0.00 | 0.000 | S0 | AUTH_GATE | PASS |
| auth_gate_before_discovery | POSITIVE | 0/0 | n/a | 0.000 | null | AUTH_GATE | PASS |
| auth_gate_at_endpoint | POSITIVE | 4/4 | 0.00/0.00 | 0.000 | S0 | AUTH_GATE | PASS |
| seq_typing_and_scroll_not_depth | POSITIVE | 3/3 | n/a | 0.000 | S1 | ENDPOINT_REACHED | PASS |
| seq_conditional_date_picker | POSITIVE | 3/3 | 0.00/0.00 | 0.000 | S0 | ENDPOINT_REACHED | PASS |
| seq_conditional_date_freetext | POSITIVE | 3/3 | 0.00/0.00 | 0.000 | S0 | ENDPOINT_REACHED | PASS |
| occluded_but_hittable | POSITIVE | 1/1 | 0.84/0.83 | 0.167 | S0 | ENDPOINT_REACHED | PASS |
| unoccluded_but_offscreen | POSITIVE | 1/1 | n/a | 0.000 | S1 | ENDPOINT_REACHED | PASS |
| PAIR:seq_conditional_date_picker\|seq_conditional_date_freetext | PAIR | - | - | - | - | - | PASS |

RESULT: ALL PASS (12/12 fixtures, 1/1 conditional pairs) -> out/walk_result.json  (r4 run 2026-08-28, walker exit 0, non-file requests aborted = 0)
