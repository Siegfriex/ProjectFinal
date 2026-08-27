"""C GATE 1 comparators — turn a runner's fixture output into PASS/FAIL/UNMAPPED items against C expectations.

adapter_map    dict-driven field/file mapping (spec defaults from gate1_adapter_spec.md); missing mapping ⇒ UNMAPPED
compare_lane1  task binding + contract hash (lane1_task_binding)
compare_lane2  label / reveal surface-state rows (lane2_label_reveal)
compare_lane3  sequence / dismiss / auth (lane3_sequence_dismiss_auth)
grade_lane4    safety battery pass rules S1/S1b/S2/S3/S4 (lane4_safety_adapter)
selftest       synthetic runner output (spec-exact) → PASS, mutated copy → FAIL
"""
