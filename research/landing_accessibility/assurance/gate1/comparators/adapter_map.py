#!/usr/bin/env python3
"""adapter_map — the single dict-driven mapping layer between C expectation fields and B runner output.

Every runner-field access in the comparators goes through `AdapterMap` / `RunnerOutput`. A field that has no
mapping (no entry, or an explicit null) yields `Lookup(status="UNMAPPED")` — never a default VALUE. A field that
is mapped but absent in the runner's file also yields UNMAPPED (reason says "absent in runner output"), so an
empty output can never PASS.

Map JSON shape (`--adapter-map`):
    {"evidence_root": "<dir>",                       # lane5 tree (unchanged, read by run_gate1.py)
     "use_spec_defaults": true,                       # start from gate1_adapter_spec.md §3 names, then overlay
     "files":  {"<table>": "<relative path>[#dotted.path]" | "@files.<key in run_result.json>" | null},
     "fields": {"<table>.<C field>": "<runner key (dotted allowed)>" | null}}
Tables: run_result · flow (fact_flow_observation row) · steps (fact_flow_step rows) · surface (fact_surface_state
rows) · obstruction (fact_task_obstruction rows) · action_log (jsonl) · candidate_states · terminal_dom (C request,
not in the spec) · path_manifest.

    python3 adapter_map.py --write-default adapter_map.default.json     # template = spec defaults
    python3 adapter_map.py --show MAP.json                              # resolved table incl. UNMAPPED rows
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

# ----------------------------------------------------------------------------------------------- spec defaults
# Source: gate1_adapter_spec.md §2-§3 (the interface C requested from B). Names B may choose are `@files.<key>`
# (resolved through run_result.json "files"), names the spec fixes are literal. `None` = the spec has no such
# field/file → UNMAPPED until C's spec request is extended and B answers.
SPEC_FILES: dict[str, str | None] = {
    "run_result": "run_result.json",
    "flow": "flow.json",                          # single fact_flow_observation row (+ steps)
    "steps": "flow.json#steps",                   # fact_flow_step rows, ordered by step_index
    "surface": "@files.fact_surface_state",       # spec §3: name is B's choice, listed in run_result.files
    "obstruction": "@files.fact_task_obstruction",
    "action_log": "action_log.jsonl",
    "candidate_states": "candidate_states.json",
    "path_manifest": "path_manifest.json",
    "terminal_dom": None,                         # NOT IN SPEC: terminal DOM capture (body attrs, visible markers)
}
SPEC_FIELDS: dict[str, str | None] = {
    # run_result.json (§3)
    "run_result.sha": "sha", "run_result.exit": "exit", "run_result.files": "files",
    "run_result.refusal_reason": "refusal_reason", "run_result.non_file_requests_aborted": "non_file_requests_aborted",
    "run_result.route_policy_doc": "route_policy_doc", "run_result.route_policy_sha256": "route_policy_sha256",
    "run_result.entry_selector_ignored": None,    # spec §2 says "say so in run_result.json" without naming the field
    # fact_flow_observation echo (§2) + derived (§3)
    "flow.task_id": "task_id", "flow.family_id": "family_id", "flow.endpoint_contract": "endpoint_contract",
    "flow.contract_sha256": "contract_sha256",
    "flow.task_instruction": "task_instruction", "flow.fixed_fixture": "fixed_fixture", "flow.task_family": "task_family",
    "flow.legacy_archetype": "legacy_archetype",
    "flow.task_flow_sequence": "task_flow_sequence", "flow.experienced_flow_sequence": "experienced_flow_sequence",
    "flow.activation_depth": "activation_depth", "flow.flow_step_count": "flow_step_count",
    "flow.menu_dependency": "menu_dependency", "flow.nav_container_depth": "nav_container_depth",
    "flow.forced_dismissal_count": "forced_dismissal_count", "flow.auth_gate_stage": "auth_gate_stage",
    "flow.endpoint_status": "endpoint_status", "flow.terminal_reason": "terminal_reason", "flow.terminal_note": "terminal_note",
    "flow.task_role": "task_role", "flow.fixture_input_mode": "fixture_input_mode", "flow.depth_input_modes": "depth_input_modes",
    "flow.endpoint_surface_rendered_before_gate": "endpoint_surface_rendered_before_gate",
    "flow.first_visible_scroll_state": "first_visible_scroll_state",
    # fact_flow_step (§3)
    "step.step_index": "step_index", "step.state_before": "state_before_id", "step.action_token": "action_token",
    "step.state_after": "state_after_id", "step.control_selector": "control_selector",
    "step.url_before": "url_before", "step.url_after": "url_after",
    "step.entry_bbox_before": "bbox_before", "step.entry_bbox_after": "bbox_after",   # C reading: bbox of the task-entry control
    # fact_surface_state (§3)
    "surface.state_index": "state_index", "surface.visible_label_text": "visible_label_text",
    "surface.accessible_name": "accessible_name", "surface.accessible_name_source": "accessible_name_source",
    "surface.label_relation": "label_relation", "surface.entry_label_modality": "entry_label_modality",
    "surface.entry_control_type": "entry_control_type", "surface.entry_x_norm": "entry_x_norm",
    "surface.entry_y_norm": "entry_y_norm", "surface.entry_zone": "entry_zone",
    "surface.entry_observed_state": "entry_observed_state", "surface.nav_container_type": "nav_container_type",
    "surface.nav_container_chain": "nav_container_chain", "surface.reveal_direction": "reveal_direction",
    "surface.menu_dependency": "menu_dependency", "surface.nav_container_depth": "nav_container_depth",
    "surface.task_control_visible": "task_control_visible", "surface.dom_ax_divergence": "dom_ax_divergence",
    "surface.first_visible_scroll_state": "first_visible_scroll_state",
    "surface.entry_selector": None,               # NOT IN SPEC: selector of the control the row describes
    "surface.entry_is_floating": None,            # NOT IN SPEC: R7 FLOATING flag (computed position fixed/sticky)
    "surface.visible_text_provenance": None,      # NOT IN SPEC: 04 §7 PSEUDO_ELEMENT / INPUT_VALUE provenance
    "surface.rendered_pseudo_text": None,         # NOT IN SPEC: alternative encoding of the pseudo-element label
    # fact_task_obstruction (§3)
    "obstruction.state_index": "state_index", "obstruction.task_control_occlusion": "task_control_occlusion",
    "obstruction.overlay_coverage": "overlay_coverage", "obstruction.dismiss_required_for_task": "dismiss_required_for_task",
    "obstruction.dismiss_control_accessible_name": "dismiss_control_accessible_name",
    "obstruction.dismiss_control_selector": "dismiss_control_selector",
    # action_log.jsonl (§3)
    "action.ts": "ts", "action.type": "type", "action.target_selector": "target_selector",
    "action.accessible_name": "accessible_name", "action.value_len": "value_len", "action.step_index": "step_index",
    "action.refused": "refused", "action.reason": "reason", "action.log_active": "log_active", "action.heartbeat": "heartbeat",
    # candidate_states.json (§3)
    "candidate.selector": "selector", "candidate.state": "state", "candidate.accessible_name": "accessible_name",
    # terminal_dom (C request, not in spec)
    "terminal_dom.body_attrs": None, "terminal_dom.visible_markers": None, "terminal_dom.input_values": None,
    "terminal_dom.text_by_id": None,
}


class Lookup:
    __slots__ = ("status", "value", "reason", "path")

    def __init__(self, status: str, value: Any = None, reason: str | None = None, path: str | None = None):
        self.status, self.value, self.reason, self.path = status, value, reason, path

    @property
    def ok(self) -> bool:
        return self.status == "OK"

    def __repr__(self) -> str:
        return f"Lookup({self.status}, {self.value!r}, {self.reason!r})"


def _dig(obj: Any, dotted: str) -> tuple[bool, Any]:
    """Follow a dotted path; returns (found, value). '' → the object itself."""
    if not dotted:
        return True, obj
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return False, None
    return True, cur


class AdapterMap:
    """Field/file binding. `AdapterMap.none()` = no map given → every lookup UNMAPPED."""

    def __init__(self, files: dict | None, fields: dict | None, *, present: bool, source: str | None = None,
                 evidence_root: str | None = None):
        self.present = present
        self.files = dict(files or {})
        self.fields = dict(fields or {})
        self.source = source
        self.evidence_root = evidence_root

    @classmethod
    def none(cls) -> "AdapterMap":
        return cls({}, {}, present=False, source=None)

    @classmethod
    def spec_defaults(cls, source: str = "gate1_adapter_spec.md defaults") -> "AdapterMap":
        return cls(dict(SPEC_FILES), dict(SPEC_FIELDS), present=True, source=source)

    @classmethod
    def from_dict(cls, d: dict, source: str | None = None) -> "AdapterMap":
        use_defaults = d.get("use_spec_defaults", True)
        files = dict(SPEC_FILES) if use_defaults else {}
        fields = dict(SPEC_FIELDS) if use_defaults else {}
        files.update(d.get("files") or {})
        fields.update(d.get("fields") or {})
        return cls(files, fields, present=True, source=source, evidence_root=d.get("evidence_root"))

    @classmethod
    def load(cls, path: str | pathlib.Path | None) -> "AdapterMap":
        if path is None:
            return cls.none()
        p = pathlib.Path(path)
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")), source=str(p))

    def to_dict(self) -> dict:
        return {"use_spec_defaults": False, "evidence_root": self.evidence_root, "files": self.files, "fields": self.fields}

    # -- binding queries --------------------------------------------------------------------------
    def file_spec(self, table: str) -> Lookup:
        if not self.present:
            return Lookup("UNMAPPED", reason="no --adapter-map given (GATE1_RUNBOOK_C.md §3 table not filled)")
        spec = self.files.get(table)
        if not spec:
            return Lookup("UNMAPPED", reason=f"files.{table} not mapped (null/absent in adapter map)")
        return Lookup("OK", spec, path=spec)

    def field_key(self, cfield: str) -> Lookup:
        if not self.present:
            return Lookup("UNMAPPED", reason="no --adapter-map given (GATE1_RUNBOOK_C.md §3 table not filled)")
        key = self.fields.get(cfield)
        if not key:
            return Lookup("UNMAPPED", reason=f"fields.{cfield} not mapped (null/absent in adapter map)")
        return Lookup("OK", key, path=key)

    def unmapped_rows(self) -> list[str]:
        rows = [f"files.{k}" for k, v in self.files.items() if not v]
        rows += [f"fields.{k}" for k, v in self.fields.items() if not v]
        return rows


class RunnerOutput:
    """One fixture's runner output directory seen through an AdapterMap. Missing dir ⇒ every lookup UNMAPPED."""

    def __init__(self, out_dir: str | pathlib.Path | None, amap: AdapterMap):
        self.dir = pathlib.Path(out_dir) if out_dir else None
        self.map = amap
        self._cache: dict[str, Any] = {}

    # -- files ------------------------------------------------------------------------------------
    def _resolve_spec(self, spec: str) -> Lookup:
        """'@files.<key>' → look the path up in run_result.json files{}; else literal relative path[#dotted]."""
        if spec.startswith("@"):
            rr = self.record("run_result")
            if not rr.ok:
                return Lookup("UNMAPPED", reason=f"{spec}: run_result.json unreadable ({rr.reason})")
            found, val = _dig(rr.value, spec[1:])
            if not found or not val:
                return Lookup("UNMAPPED", reason=f"{spec}: key absent in run_result.json (spec §3: B must list the file)")
            return Lookup("OK", str(val))
        return Lookup("OK", spec)

    def file_path(self, table: str) -> Lookup:
        fs = self.map.file_spec(table)
        if not fs.ok:
            return fs
        if self.dir is None:
            return Lookup("UNMAPPED", reason="no runner output directory (runner not invoked)")
        r = self._resolve_spec(fs.value)
        if not r.ok:
            return r
        rel, _, sub = r.value.partition("#")
        p = (self.dir / rel) if not pathlib.Path(rel).is_absolute() else pathlib.Path(rel)
        if not p.exists():
            return Lookup("UNMAPPED", reason=f"files.{table} → {rel}: absent in runner output dir {self.dir}", path=str(p))
        return Lookup("OK", (p, sub), path=str(p) + ("#" + sub if sub else ""))

    def _load(self, table: str) -> Lookup:
        if table in self._cache:
            return self._cache[table]
        fp = self.file_path(table)
        if not fp.ok:
            self._cache[table] = fp
            return fp
        p, sub = fp.value
        try:
            if p.suffix == ".jsonl":
                data: Any = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
            else:
                data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            res = Lookup("UNMAPPED", reason=f"files.{table} → {p}: unreadable ({type(e).__name__}: {e})", path=str(p))
            self._cache[table] = res
            return res
        found, val = _dig(data, sub)
        if not found:
            res = Lookup("UNMAPPED", reason=f"files.{table} → {p}#{sub}: path absent in file", path=fp.path)
        else:
            res = Lookup("OK", val, path=fp.path)
        self._cache[table] = res
        return res

    def record(self, table: str) -> Lookup:
        """A single JSON object table (run_result, flow, terminal_dom, path_manifest)."""
        r = self._load(table)
        if r.ok and not isinstance(r.value, dict):
            return Lookup("UNMAPPED", reason=f"files.{table}: expected a JSON object, got {type(r.value).__name__}", path=r.path)
        return r

    def table(self, table: str) -> Lookup:
        """A list-of-rows table (steps, surface, obstruction, action_log, candidate_states). A dict with a single
        list value is unwrapped; a dict of rows keyed by id is converted to its values."""
        r = self._load(table)
        if not r.ok:
            return r
        v = r.value
        if isinstance(v, dict):
            lists = [x for x in v.values() if isinstance(x, list)]
            if len(lists) == 1:
                v = lists[0]
            elif v and all(isinstance(x, dict) for x in v.values()):
                v = list(v.values())
            else:
                return Lookup("UNMAPPED", reason=f"files.{table}: expected a list of rows, got object with keys {list(v)[:6]}", path=r.path)
        if not isinstance(v, list):
            return Lookup("UNMAPPED", reason=f"files.{table}: expected a list of rows, got {type(v).__name__}", path=r.path)
        return Lookup("OK", v, path=r.path)

    # -- fields -----------------------------------------------------------------------------------
    def field(self, cfield: str, row: Any) -> Lookup:
        """Value of C field `<table>.<name>` inside `row` (a dict). Key present with null ⇒ OK(None)."""
        fk = self.map.field_key(cfield)
        if not fk.ok:
            return fk
        if not isinstance(row, dict):
            return Lookup("UNMAPPED", reason=f"{cfield}: row is not an object", path=fk.value)
        found, val = _dig(row, fk.value)
        if not found:
            return Lookup("UNMAPPED", reason=f"{cfield} mapped to '{fk.value}' but absent in runner output", path=fk.value)
        return Lookup("OK", val, path=fk.value)

    def rec_field(self, table: str, name: str) -> Lookup:
        rec = self.record(table)
        if not rec.ok:
            return rec
        return self.field(f"{table}.{name}", rec.value)

    def has_field(self, cfield: str, row: Any) -> bool:
        fk = self.map.field_key(cfield)
        return fk.ok and isinstance(row, dict) and _dig(row, fk.value)[0]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="C adapter map (spec defaults, show, write template)")
    ap.add_argument("--write-default", metavar="OUT.json")
    ap.add_argument("--show", metavar="MAP.json")
    a = ap.parse_args(argv)
    if a.write_default:
        m = AdapterMap.spec_defaults()
        pathlib.Path(a.write_default).write_text(json.dumps(
            {"_comment": "C GATE 1 adapter map template = gate1_adapter_spec.md defaults. Fill null rows from "
                         "GATE1_RUNBOOK_C.md §2 findings at B's SHA; a null row stays UNMAPPED (NOT_TESTABLE).",
             **m.to_dict()}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {a.write_default}: {len(m.files)} files, {len(m.fields)} fields, {len(m.unmapped_rows())} UNMAPPED rows")
    if a.show:
        m = AdapterMap.load(a.show)
        for k, v in m.files.items():
            print(f"files.{k:<18} → {v or 'UNMAPPED'}")
        for k, v in m.fields.items():
            print(f"fields.{k:<45} → {v or 'UNMAPPED'}")
        print(f"UNMAPPED rows: {len(m.unmapped_rows())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
