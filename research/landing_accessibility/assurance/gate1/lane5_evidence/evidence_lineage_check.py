#!/usr/bin/env python3
"""C-Evidence lane: independent EVIDENCE COMPLETENESS & LINEAGE checker (GATE 1 -> unchanged at GATE 2/3).

Reads RAW FILES ONLY (manifests + artifacts on disk). Never reads B's summary/mart.

Usage:
  evidence_lineage_check.py ROOT [--path-manifest PATH.json] [--out report.json] [--quiet]
Exit code: 0 iff no SYSTEMIC defect (verdict COMPLETE or COMPLETE_WITH_ISOLATED_DEFECTS); 2 on SYSTEMIC_DEFECT; 3 on usage error.

Rules are fixed by EVIDENCE_CONTRACT_C.md. The ONLY thing expected to change once B's real
layout is known is the FIELD_ALIASES / ARTIFACT_ALIASES tables below (name mapping), not the rules.

Discovery heuristics (documented so they can be pre-registered):
  D1  walk ROOT; a "manifest" is any file whose name matches *.jsonl, or *manifest*.json (case-insensitive),
      excluding path_manifest*.json (the path manifest is never an evidence manifest) and *.sha256 sidecars.
      If --path-manifest is omitted and ROOT/path_manifest.json exists, it is auto-detected (reported in JSON).
  D2  *.jsonl -> one JSON object per non-empty line. *.json -> list => records; dict with a list under any of
      {records, states, steps, observations, entries} => concatenated; other dict => single record.
  D3  a record is a STATE if it has step_index absent and (state_index or observation_id) present;
      a STEP if it has step_index present; otherwise UNKNOWN (counted, not a defect).
  D4  artifact paths are resolved relative to the manifest's directory, then relative to ROOT.
  D5  identity spine = (service_id, task_id, run_id); state identity = spine + attempt_id + state_index;
      observation_id must be globally unique.
  D6  manifest SHA binding: with --path-manifest, every discovered evidence manifest must be listed there
      with a matching sha256; without it, a sidecar <manifest>.sha256 must exist and match.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- adaptation tables (field-name mapping only)
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    # canonical            : accepted source names (first match wins)
    "observation_id":        ("observation_id", "state_id", "obs_id"),
    "flow_observation_id":   ("flow_observation_id", "flow_id"),
    "service_id":            ("service_id", "service"),
    "task_id":               ("task_id", "task"),
    "run_id":                ("run_id", "run"),
    "attempt_id":            ("attempt_id", "attempt"),
    "state_index":           ("state_index", "state"),
    "step_index":            ("step_index", "step"),
    "url":                   ("url", "page_url"),
    "captured_at":           ("captured_at", "timestamp", "ts", "observed_at"),
    "collector_sha":         ("collector_sha", "collector_git_sha", "collector_version_sha"),
    "protocol_sha":          ("protocol_sha", "protocol_git_sha", "ssot_sha"),
    "task_contract_sha256":  ("task_contract_sha256", "task_contract_sha"),
    "endpoint_contract_sha256": ("endpoint_contract_sha256", "endpoint_contract_sha"),
    "action_token":          ("action_token", "action"),
    "state_before_id":       ("state_before_id", "before_state_id"),
    "state_after_id":        ("state_after_id", "after_state_id"),
    "url_before":            ("url_before",),
    "url_after":             ("url_after",),
    "artifacts":             ("artifacts", "evidence", "files"),
    "display_name":          ("display_name", "service_name", "service_display_name"),
}
# artifact kinds required per STATE (SSOTV3 03 §10: DOM, AX, screenshot, probe/CSS geometry, control facts; URL is a field)
ARTIFACT_ALIASES: dict[str, tuple[str, ...]] = {
    "dom":           ("dom", "dom_html", "html"),
    "ax":            ("ax", "ax_tree", "accessibility_tree"),
    "screenshot":    ("screenshot", "png", "image"),
    "probe":         ("probe", "geometry", "css_geometry", "probe_geometry"),
    "control_facts": ("control_facts", "selected_control_facts", "controls"),
}
# STEP hash fields (02 §4: before/after DOM/AX/screenshot hashes) -> (artifact kind, side)
STEP_HASH_FIELDS: dict[str, tuple[str, str]] = {
    "dom_sha256_before": ("dom", "before"), "dom_sha256_after": ("dom", "after"),
    "ax_sha256_before": ("ax", "before"), "ax_sha256_after": ("ax", "after"),
    "screenshot_sha256_before": ("screenshot", "before"), "screenshot_sha256_after": ("screenshot", "after"),
}
STATE_REQUIRED = ("observation_id", "service_id", "task_id", "run_id", "attempt_id", "state_index", "url",
                  "captured_at", "collector_sha", "protocol_sha", "task_contract_sha256",
                  "endpoint_contract_sha256", "artifacts")
STEP_REQUIRED = ("flow_observation_id", "service_id", "task_id", "run_id", "attempt_id", "step_index",
                 "action_token", "state_before_id", "state_after_id", "url_before", "url_after", "captured_at",
                 "collector_sha", "protocol_sha", "task_contract_sha256", "endpoint_contract_sha256",
                 *STEP_HASH_FIELDS)

# ---------------------------------------------------------------- defect catalogue (severity fixed by contract)
ALWAYS_SYSTEMIC = {"OVERWRITE_DETECTED", "IDENTITY_COLLISION", "MANIFEST_SHA_UNBOUND"}
SPINE_FIELDS = ("service_id", "task_id", "run_id")   # DISPLAY_NAME_AS_ID here => systemic (identity of whole run)
ID_FIELDS = SPINE_FIELDS + ("attempt_id", "observation_id", "flow_observation_id")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-:]*$")  # ASCII, no whitespace; display names fail this
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
STATE_INDEX_RE = re.compile(r"^S\d+$")
OVERWRITE_MTIME_TOLERANCE_S = 1.0


class Report:
    def __init__(self, root: Path, path_manifest: Path | None):
        self.root, self.path_manifest = root, path_manifest
        self.defects: list[dict] = []
        self.n_manifests = self.n_states = self.n_steps = self.n_unknown = self.n_artifacts_checked = 0

    def add(self, kind: str, path: str, detail: str, *, systemic: bool | None = None) -> None:
        if systemic is None:
            systemic = kind in ALWAYS_SYSTEMIC
        self.defects.append({"kind": kind, "severity": "systemic" if systemic else "isolated",
                             "path": path, "detail": detail})

    def finish(self) -> dict:
        systemic = any(d["severity"] == "systemic" for d in self.defects)
        verdict = ("SYSTEMIC_DEFECT" if systemic else
                   "COMPLETE_WITH_ISOLATED_DEFECTS" if self.defects else "COMPLETE")
        return {
            "checker": "evidence_lineage_check.py", "contract": "EVIDENCE_CONTRACT_C.md",
            "root": str(self.root), "path_manifest": str(self.path_manifest) if self.path_manifest else None,
            "n_manifests": self.n_manifests, "n_states": self.n_states, "n_steps": self.n_steps,
            "n_unknown_records": self.n_unknown, "n_artifacts_checked": self.n_artifacts_checked,
            "counts_by_kind": dict(sorted(Counter(d["kind"] for d in self.defects).items())),
            "defects": self.defects, "systemic": systemic, "verdict": verdict,
        }


# ---------------------------------------------------------------- helpers
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def get(rec: dict, canonical: str):
    for name in FIELD_ALIASES.get(canonical, (canonical,)):
        if name in rec and rec[name] not in (None, ""):
            return rec[name]
    return None


def rel(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def parse_iso(s) -> float | None:
    if not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def discover_manifests(root: Path, path_manifest: Path | None) -> list[Path]:
    out = []
    for dirpath, _, files in os.walk(root):
        for fn in files:
            p = Path(dirpath) / fn
            low = fn.lower()
            if path_manifest and p.resolve() == path_manifest.resolve():
                continue
            if low.endswith(".sha256") or low.startswith("path_manifest"):
                continue
            if low.endswith(".jsonl") or (low.endswith(".json") and "manifest" in low):
                out.append(p)
    return sorted(out)


def load_records(mp: Path, rep: Report) -> list[dict]:
    text = mp.read_text(encoding="utf-8")
    recs: list = []
    if mp.suffix.lower() == ".jsonl":
        for ln, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as e:
                rep.add("MISSING_FIELD", f"{rel(rep.root, mp)}:{ln}", f"unparseable manifest line: {e}")
    else:
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            rep.add("MISSING_FIELD", rel(rep.root, mp), f"unparseable manifest: {e}")
            return []
        if isinstance(obj, list):
            recs = obj
        elif isinstance(obj, dict):
            lists = [obj[k] for k in ("records", "states", "steps", "observations", "entries")
                     if isinstance(obj.get(k), list)]
            recs = [r for lst in lists for r in lst] if lists else [obj]
    return [r for r in recs if isinstance(r, dict)]


def classify(rec: dict) -> str:
    if get(rec, "step_index") is not None:
        return "step"
    if get(rec, "state_index") is not None or get(rec, "observation_id") is not None:
        return "state"
    return "unknown"


def resolve_artifacts(rec: dict) -> dict[str, dict]:
    """Return {canonical_kind: {"path":..., "sha256":...}} from nested or flat forms."""
    found: dict[str, dict] = {}
    nested = get(rec, "artifacts")
    if isinstance(nested, dict):
        for kind, aliases in ARTIFACT_ALIASES.items():
            for a in aliases:
                v = nested.get(a)
                if isinstance(v, dict):
                    found[kind] = {"path": v.get("path") or v.get("file"), "sha256": v.get("sha256") or v.get("sha")}
                    break
                if isinstance(v, str):  # bare path; sha may live in <kind>_sha256
                    found[kind] = {"path": v, "sha256": rec.get(f"{a}_sha256")}
                    break
    for kind, aliases in ARTIFACT_ALIASES.items():  # flat form: dom_path / dom_sha256
        if kind in found:
            continue
        for a in aliases:
            if rec.get(f"{a}_path"):
                found[kind] = {"path": rec[f"{a}_path"], "sha256": rec.get(f"{a}_sha256")}
                break
    return found


# ---------------------------------------------------------------- checks
def check_ids(rec: dict, where: str, rep: Report) -> None:
    display = get(rec, "display_name")
    for f in ID_FIELDS:
        v = get(rec, f)
        if v is None:
            continue
        s = str(v)
        bad = (not ID_RE.match(s)) or (display is not None and s == str(display))
        if bad:
            rep.add("DISPLAY_NAME_AS_ID", where,
                    f"{f}={s!r} is not an identifier (whitespace/non-ASCII/equals display_name)",
                    systemic=f in SPINE_FIELDS)


def check_required(rec: dict, required: tuple[str, ...], where: str, rep: Report) -> None:
    for f in required:
        if get(rec, f) is None:
            rep.add("MISSING_FIELD", where, f"required field absent/empty: {f}")
    for f in ("collector_sha", "protocol_sha", "task_contract_sha256", "endpoint_contract_sha256"):
        v = get(rec, f)
        if v is not None and not re.match(r"^[0-9a-f]{7,64}$", str(v)):
            rep.add("MISSING_FIELD", where, f"{f} is not a hex digest: {v!r}")
    ts = get(rec, "captured_at")
    if ts is not None and parse_iso(ts) is None:
        rep.add("MISSING_FIELD", where, f"captured_at not ISO-8601: {ts!r}")
    si = get(rec, "state_index")
    if si is not None and not STATE_INDEX_RE.match(str(si)):
        rep.add("MISSING_FIELD", where, f"state_index malformed (expect S<n>): {si!r}")


def check_state_artifacts(rec: dict, mp: Path, m_mtime: float, where: str, rep: Report) -> dict[str, str]:
    """Verify presence + sha256 of every artifact; return {kind: manifest_sha}."""
    arts = resolve_artifacts(rec)
    shas: dict[str, str] = {}
    captured = parse_iso(get(rec, "captured_at"))
    for kind in ARTIFACT_ALIASES:
        a = arts.get(kind)
        if not a or not a.get("path"):
            rep.add("MISSING_ARTIFACT", where, f"no {kind} artifact referenced in manifest")
            continue
        declared = a.get("sha256")
        if not declared or not SHA_RE.match(str(declared)):
            rep.add("MANIFEST_SHA_UNBOUND", where, f"{kind} artifact has no valid sha256 in manifest",
                    systemic=False)  # per-artifact: isolated; run-level binding handled separately
        p = mp.parent / a["path"]
        if not p.exists():
            p2 = rep.root / a["path"]
            if p2.exists():
                p = p2
            else:
                rep.add("MISSING_ARTIFACT", f"{where} -> {a['path']}", f"{kind} file not found on disk")
                continue
        actual = sha256_file(p)
        rep.n_artifacts_checked += 1
        if declared and SHA_RE.match(str(declared)):
            shas[kind] = str(declared)
            if actual != declared:
                a_mtime = p.stat().st_mtime
                after_seal = a_mtime > m_mtime + OVERWRITE_MTIME_TOLERANCE_S or \
                             (captured is not None and a_mtime > captured + OVERWRITE_MTIME_TOLERANCE_S)
                rep.add("HASH_MISMATCH", rel(rep.root, p),
                        f"{kind}: manifest={declared[:12]}.. actual={actual[:12]}..")
                if after_seal:
                    rep.add("OVERWRITE_DETECTED", rel(rep.root, p),
                            f"{kind} rewritten after manifest seal (artifact mtime {a_mtime:.0f} > "
                            f"manifest mtime {m_mtime:.0f})")
    return shas


def check_manifest_binding(mp: Path, bindings: dict[str, str] | None, rep: Report) -> None:
    actual = sha256_file(mp)
    where = rel(rep.root, mp)
    if bindings is not None:
        declared = bindings.get(where) or bindings.get(mp.name) or bindings.get(str(mp))
        if declared is None:
            rep.add("MANIFEST_SHA_UNBOUND", where, "evidence manifest not referenced by path manifest")
        elif declared != actual:
            rep.add("MANIFEST_SHA_UNBOUND", where,
                    f"path manifest sha {declared[:12]}.. != actual {actual[:12]}.. (manifest mutated after freeze)")
        return
    side = mp.with_name(mp.name + ".sha256")
    if not side.exists():
        rep.add("MANIFEST_SHA_UNBOUND", where, "no --path-manifest and no <manifest>.sha256 sidecar")
    elif side.read_text().split()[0].strip() != actual:
        rep.add("MANIFEST_SHA_UNBOUND", where, "sidecar sha256 != actual manifest sha256")


def load_path_manifest(pm: Path, root: Path, rep: Report) -> dict[str, str]:
    obj = json.loads(pm.read_text(encoding="utf-8"))
    runs = obj.get("runs") if isinstance(obj, dict) else obj
    out: dict[str, str] = {}
    if not isinstance(runs, list):
        rep.add("MANIFEST_SHA_UNBOUND", rel(root, pm), "path manifest has no 'runs' list")
        return out
    for r in runs:
        if not isinstance(r, dict):
            continue
        p = r.get("evidence_manifest") or r.get("evidence_manifest_path") or r.get("manifest")
        s = r.get("evidence_manifest_sha256") or r.get("manifest_sha256") or r.get("sha256")
        if p and s:
            out[str(p)] = str(s)
        else:
            rep.add("MANIFEST_SHA_UNBOUND", rel(root, pm), f"run entry lacks evidence_manifest/sha256: {r}")
    return out


def run(root: Path, path_manifest: Path | None) -> dict:
    rep = Report(root, path_manifest)
    bindings = load_path_manifest(path_manifest, root, rep) if path_manifest else None
    manifests = discover_manifests(root, path_manifest)
    rep.n_manifests = len(manifests)
    if not manifests:
        rep.add("MISSING_ARTIFACT", str(root), "no evidence manifest discovered (D1)")

    states: dict[str, dict] = {}                         # observation_id -> {rec, shas, where}
    state_identity: dict[tuple, list[tuple]] = defaultdict(list)   # spine+attempt+state_index -> [(obs_id, shas, where)]
    spine_dirs: dict[tuple, set[str]] = defaultdict(set)  # spine -> manifest dirs
    steps: list[tuple[dict, str]] = []

    for mp in manifests:
        check_manifest_binding(mp, bindings, rep)
        m_mtime = mp.stat().st_mtime
        for i, rec in enumerate(load_records(mp, rep)):
            where = f"{rel(root, mp)}#{i}"
            kind = classify(rec)
            check_ids(rec, where, rep)
            spine = tuple(str(get(rec, f)) for f in SPINE_FIELDS)
            spine_dirs[spine].add(rel(root, mp.parent))
            if kind == "state":
                rep.n_states += 1
                check_required(rec, STATE_REQUIRED, where, rep)
                shas = check_state_artifacts(rec, mp, m_mtime, where, rep)
                oid = str(get(rec, "observation_id"))
                if oid in states:
                    rep.add("IDENTITY_COLLISION", where,
                            f"observation_id {oid!r} already declared at {states[oid]['where']}")
                else:
                    states[oid] = {"rec": rec, "shas": shas, "where": where}
                state_identity[spine + (str(get(rec, "attempt_id")), str(get(rec, "state_index")))].append((oid, shas, where))
            elif kind == "step":
                rep.n_steps += 1
                check_required(rec, STEP_REQUIRED, where, rep)
                steps.append((rec, where))
            else:
                rep.n_unknown += 1

    # identity: same (spine, attempt, state_index) declared twice
    for ident, decls in state_identity.items():
        if len(decls) < 2:
            continue
        first_oid, first_shas, first_where = decls[0]
        for oid, shas, where in decls[1:]:
            if shas and first_shas and shas != first_shas:
                rep.add("OVERWRITE_DETECTED", where,
                        f"identity {ident} re-declared with different artifact hashes (first at {first_where}); "
                        f"re-collection must be a new run_id")
            else:
                rep.add("IDENTITY_COLLISION", where, f"identity {ident} declared twice (first at {first_where})")
    for spine, dirs in spine_dirs.items():
        if len(dirs) > 1 and all(x != "None" for x in spine):
            rep.add("IDENTITY_COLLISION", ";".join(sorted(dirs)),
                    f"run identity {spine} declared in {len(dirs)} directories")

    # lineage: step -> state references, url continuity, hash chain
    seen_step_ids: set[tuple] = set()
    for rec, where in steps:
        spine = tuple(str(get(rec, f)) for f in SPINE_FIELDS)
        sid = spine + (str(get(rec, "attempt_id")), str(get(rec, "step_index")))
        if sid in seen_step_ids:
            rep.add("IDENTITY_COLLISION", where, f"step identity {sid} declared twice")
        seen_step_ids.add(sid)
        for side in ("before", "after"):
            ref = get(rec, f"state_{side}_id")
            st = states.get(str(ref)) if ref is not None else None
            if st is None:
                rep.add("LINEAGE_BREAK", where, f"state_{side}_id={ref!r} does not resolve to any state record")
                continue
            if tuple(str(get(st["rec"], f)) for f in SPINE_FIELDS) != spine:
                rep.add("LINEAGE_BREAK", where, f"state_{side}_id belongs to a different run identity")
            su, ru = get(st["rec"], "url"), get(rec, f"url_{side}")
            if su is not None and ru is not None and str(su) != str(ru):
                rep.add("LINEAGE_BREAK", where, f"url_{side}={ru!r} != referenced state url {su!r}")
            for field, (akind, fside) in STEP_HASH_FIELDS.items():
                if fside != side:
                    continue
                claimed, actual = get(rec, field), st["shas"].get(akind)
                if claimed is not None and actual is not None and str(claimed) != actual:
                    rep.add("HASH_MISMATCH", where,
                            f"{field}={str(claimed)[:12]}.. != state {ref} manifest {akind} sha {actual[:12]}..")
    return rep.finish()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--path-manifest", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None, help="write JSON report here (also printed unless --quiet)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    if not a.root.is_dir():
        print(f"root is not a directory: {a.root}", file=sys.stderr)
        return 3
    if a.path_manifest and not a.path_manifest.is_file():
        print(f"path manifest not found: {a.path_manifest}", file=sys.stderr)
        return 3
    pm = a.path_manifest
    autodetected = False
    if pm is None and (a.root / "path_manifest.json").is_file():
        pm, autodetected = a.root / "path_manifest.json", True
    report = run(a.root.resolve(), pm.resolve() if pm else None)
    report["path_manifest_autodetected"] = autodetected
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if a.out:
        a.out.write_text(text + "\n", encoding="utf-8")
    if not a.quiet:
        print(text)
    return 0 if not report["systemic"] else 2


if __name__ == "__main__":
    sys.exit(main())
