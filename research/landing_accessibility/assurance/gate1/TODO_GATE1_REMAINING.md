# GATE 1 — remaining C tasks (after worker interruption 04:2x, session limit)
Done by interrupted worker (verified by C 06:45): R11 table unified (`gate1/c_terminal_table.py`, lane5+lane6 import it; lane6 30/30, lane5 COMPLETE/SYSTEMIC/SYSTEMIC), lane3 field rename → `endpoint_surface_rendered_before_gate` (walk 8/8), lane5 `collector_sha256` alias, bus.emit `base_sha` guard.
Remaining:
- [ ] lane4: "guard fired" positive control in forbidden_action_matrix.json + GATE1_SAFETY_PLAN.md (Δ18-R20)
- [ ] fixtures: lane3 `seq_conditional_date_picker.html` / `seq_conditional_date_freetext.html` (Δ8-R5 / STEP1-006 CONDITIONAL); lane2 `drawer_nested_accordion.html` (GAP-06); `occluded_but_hittable.html` (GAP-05); lane2 `dom_ax_divergence_positive.html` (STEP1-012)
- [ ] c_bus_scan.py: Δ6-a enum/5-field check, Δ4 `--ref-lint`, Δ13-R17 FACT_CORRECTION how_known check, Δ5-vr VALIDITY_RISK≥P1, Δ21 delta↔ticket cross-check
- [ ] lane5: `driver_sha256` (Δ22-R22) required alongside collector_sha256
- [ ] coverage table: flip PARTIAL/UNCOVERED rows to COVERED after the above; re-run run_gate1 --dry-run
