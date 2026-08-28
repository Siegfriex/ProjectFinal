#!/usr/bin/env python3
"""C bus scanner (JSON-parsing, not grep). Returns tickets addressed to C (to or cc) that lack a C ack.
Malformed JSON is reported explicitly as PARSE_ERROR — never silently counted as 'nothing to receive'.

Report-only checks added 2026-08-28 (RULING_INDEX_COVERAGE_C rows Δ6-a / Δ4 / Δ13-R17 / Δ5-vr / Δ21), all over v3-era tickets
(created_at_kst >= 2026-08-28T02:12:00+09:00 = T-A-V3-P0-001 adoption; file mtime when the ticket carries no timestamp):
  (a) Δ6-a   plane enum: from / to[] / cc[] ⊆ {A,B,C,D,E,DIRECTOR}; a REAL-bearing ticket with E in from∪to must carry the 5
             mandatory fields real_scope_id, release_doc, target_manifest_sha256, allowlist_ref, task_contract_sha256 (top level or payload).
  (b) Δ4     --ref-lint: bare `research/landing-accessibility-main` (no `origin/` / `refs/remotes/origin/` prefix) in C's *.py / *.md under
             assurance/ and in v3-era bus tickets; lines containing `ls-remote` are ignored (remote-tip reads are compliant in substance).
  (c) Δ13-R17 FACT_CORRECTION / FACTUAL_CORRECTION tickets lacking a how-known field (how_known / evidence / measurement / method /
             verified_against / how_*found* / how_it_surfaced / artifact_refs / what_is_actually_true / corrected_facts, top level or payload).
  (d) Δ5-vr  FINDING tickets whose finding_class is VALIDITY_RISK with priority ∉ {P0, P1} (type VALIDITY_RISK_CANDIDATE below P1 is listed
             separately as informational — the ruling names finding_class).
  (e) Δ21    ruling-index ↔ ticket cross-check. Ruling tokens mentioned in v3-era A tickets (`Δ\\d+(-[A-Za-z0-9]+)?`, `R\\d+[a-z]?`) are resolved
             against V3_RULING_INDEX.json read from `origin/control/landing-orchestrator` — **id AND aliases[]** (T-A-V3-STEP1-023: the index declares
             its own aliases; consumers do not infer them — the Δn-Rm↔Rm pattern rule of T-A-V3-FC-004 misses bare Δn rows, T-B-V3-FINDING-005).
             Matching is token-bounded and case-sensitive (no partial match). Alias qualification = index v9 `alias_rules` / delta Δ25
             (T-B-V3-FINDING-007): an alias is EXCLUDED from matching iff it is a lowercase single word without separators and ≤ 6 characters
             (auth · vr · domax · skip); R1 · R3a · Δ2 · R13b · THREE_TURN_RUNBOOK · scrollfix are kept. Excluded aliases are reported under
             ruling_record_gaps.unsafe_aliases; purely alphabetic aliases shorter than 3 characters are listed as an index defect
             (ruling_record_gaps.short_alpha_aliases). An alias mapped to ≥ 2 rows is reported under ruling_record_gaps.alias_collisions and never
             resolved by this tool (T-B-V3-FINDING-006). Rows with an empty aliases[] are reported. Built-in controls run BEFORE the main check and
             the tool refuses to run it (exit 2) if any fails: positive R21→Δ21, R20→Δ18-R20, Δ18-R20→Δ18-R20; negative STEP1↛Δ20, R15↛Δ20.
             A bare section / prefix token (Δ12 where the index has Δ12-R15/R16/C; Δ8-R3 → Δ8-R3a/b; R13 → R13a/b) is reported under
             section_mentions_resolved_by_subrows, not as a gap. Unresolved tokens → ruling_record_gaps.unrecorded_mentions; delta `## Δn`
             headings with neither a row nor sub-rows → ruling_record_gaps.delta_headings_without_index_row.
  (f) Δ26    v3-era tickets: base_sha must resolve to a real object — `git -C <repo> cat-file -e <sha>^{commit}` (a ref such as origin/… is
             accepted via rev-parse --verify). Classified NO_FIELD / NOT_A_SHA (not hex) / MISSING (hex, cat-file fails) / OK_ABBREV (resolves,
             shorter than 40 — reported, not hidden: C's own v3-era tickets carry 10-12 char shas) / OK; unresolvable = NO_FIELD+NOT_A_SHA+MISSING.
             Report-only (the FINDING-007-SHANOTE case). bus.py::emit now refuses/expands at issue time.
  selftest   `c_bus_scan.py selftest` builds a temp bus: ticket X + acks/X.C-1.json (R19 re-ACK → NOT dangling), acks/Y.C.json without a ticket
             (dangling), and base_sha classification cases (absent / 'origin/nonexistent-ref' / 40-hex fake / real short / real full).

  Δ46 declared failure behaviour (R40 / Δ46-declared) — demonstrated by gate1/control_failure_demo_c.py on a MUTATED COPY, never here:
             if any built-in ruling-index control FAILs, `ruling_record_gaps.status` = CONTROLS_FAILED_MAIN_CHECK_REFUSED, the block carries only
             diagnostics (index identity, the control table, alias diagnostics that are inputs to the controls) and NONE of MAIN_CHECK_KEYS,
             and the summary line prints `n/a` (not 0) for every main-check counter; exit 2. The sidecar gate1/CONTROL_FAILURE_DEMOS_C.json records
             the tool sha256 at demo time; `failure_behaviour_demo.valid_for_this_commit` is true only when that sha equals this file's sha now
             AND every demo case for this tool PASSed — editing this file invalidates the demonstration until the demonstrator is re-run.
  exit codes (Δ46-exit2, same convention as A's check_ruling_index.py / a_publish_guard.py):
             0 = ran, controls passed (all findings are report-only and live in the JSON) · 1 = ran and FAILED (scan status PARSE_ERRORS_PRESENT:
             the bus holds malformed JSON; `selftest` failure) · 2 = DID NOT RUN — controls failed / index unavailable (main check refused) OR an
             uncaught exception ("did not run — read neither as pass nor fail") · 3 = usage error (unknown flag).

Usage: c_bus_scan.py [bus_dir] [--ref-lint] [--assurance-root DIR] [--repo DIR] [--index-ref REF] [--index-file PATH]
       -> prints JSON {pending, parse_errors, dangling_refs_v3_era, content_changed_after_ack, plane_enum, ref_lint, fact_correction_how_known,
                       validity_risk_priority, ruling_record_gaps, base_sha_unresolvable, failure_behaviour_demo, summary, status}
Last run (2026-08-28 08:5x KST, --ref-lint, exit 0; `selftest` OK; gate1/control_failure_demo_c.py 7/7 cases + 4/4 binding controls PASS):
  SUMMARY: scanned=270 pending=2 parse_errors=0 dangling=1 changed_after_ack=1 plane_enum_violations=0 e_real_field_gaps=3 ref_lint_hits=13 fact_correction_missing_how_known=32 validity_risk_below_p1=0 vrc_type_below_p1=2 ruling_unrecorded_mentions=2 resolved_by_subrows=20 alias_collisions=1 unsafe_aliases=0 empty_alias_rows=0 delta_headings_without_index_row=0 base_sha[no_field/not_sha/missing/ok_abbrev/ok]=5/0/0/11/114 controls=PASS demo_valid_for_this_commit=True
"""
import json, glob, os, sys, re, hashlib, subprocess, pathlib, collections
# ACKs whose ticket_sha256 legitimately differs from the current file (documented provenance events); never silently drop
EXPLAINED_CHANGES = {('T-A-V3-FC-001','T-A-V3-FC-001.C-1.json'): 'acked replaced content (now T-A-V3-FC-002); FC-001 restored by A STEP1-014'}
V3_CUTOFF_EPOCH = 1787500320  # 2026-08-28T02:12:00+09:00 (T-A-V3-P0-001 adoption)
V3_CUTOFF_ISO = "2026-08-28T02:12:00"
PLANES = {"A", "B", "C", "D", "E", "DIRECTOR"}
ACK_SUFFIX_RE = re.compile(r"(\.(A|B|C|D|E)(-\d+)?)+$")   # R19: re-ACK never overwrites → X.C-1.json is an ACK of ticket X
E_REAL_REQUIRED = ("real_scope_id", "release_doc", "target_manifest_sha256", "allowlist_ref", "task_contract_sha256")
HOW_KNOWN_RE = re.compile(r"^(how_known|evidence|evidence_refs|measurement|method|verified_against|how_.*(found|surfaced|happened).*|how_it_surfaced|artifact_refs|what_is_actually_true|corrected_facts|the_measurement)$", re.I)
BARE_REF_RE = re.compile(r"(?<!origin/)(?<!refs/remotes/origin/)research/landing-accessibility-main")
SHA40_RE = re.compile(r"\b[0-9a-f]{40}\b")
DELTA_TOKEN_RE = re.compile(r"Δ\d+(?:-[A-Za-z0-9]+)?")
R_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_\-Δ])R\d+[a-z]?(?![A-Za-z0-9_])")
DEFAULT_REPO = "/home/sieg/projects-wsl/ProjectFinal"
# T-A-V3-FC-007 (R39): what A has published is defined ONLY by what A pushed. C reads `origin/control/landing-orchestrator`
# after an explicit fetch — never the local branch (that is A's unpublished working state; producer ≠ reviewer at the byte
# layer). The v29-vs-v33 staleness of 08:38 was A not pushing 12 commits, not a C defect (A ruled), so the fix is fetch-first.
CONTROL_REF = "origin/control/landing-orchestrator"
def fetch_control(repo: str) -> dict:
    import datetime as _dt
    r = subprocess.run(["git", "-C", repo, "fetch", "-q", "origin", "control/landing-orchestrator"], capture_output=True, text=True, timeout=60)
    sha = subprocess.run(["git", "-C", repo, "rev-parse", CONTROL_REF], capture_output=True, text=True).stdout.strip()
    return {"fetched_at_kst": _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9))).isoformat(timespec="seconds"), "fetch_rc": r.returncode, "control_ref": CONTROL_REF, "control_commit": sha}
DEFAULT_INDEX_REF = CONTROL_REF + ":research/landing_accessibility/control/v3/V3_RULING_INDEX.json"
DEFAULT_DELTA_REF = CONTROL_REF + ":research/landing_accessibility/control/v3/V3_0_1_SUCCESSOR_DELTA.md"
ASSURANCE_ROOT = pathlib.Path(__file__).resolve().parent
# Δ46/R40: sidecar written by gate1/control_failure_demo_c.py (isolated mutated copies); this tool only READS it and compares shas.
DEMO_SIDECAR = ASSURANCE_ROOT / "gate1" / "CONTROL_FAILURE_DEMOS_C.json"
TOOL_REL = "c_bus_scan.py"
# keys of the ruling-index block that exist ONLY when the main check ran (controls passed). Declared: never emitted on refusal.
MAIN_CHECK_KEYS = ("a_tickets_v3_era", "tokens_mentioned", "index_to_delta_reachability", "unrecorded_mentions", "resolved_only_via_unsafe_alias",
                   "section_mentions_resolved_by_subrows", "index_rows_unmentioned_in_A_tickets", "delta_headings_without_index_row", "delta_sha256",
                   "delta_heading_counts")
DID_NOT_RUN_MSG = "c_bus_scan: did not run — read neither as pass nor fail (exit 2)"

def failure_demo_binding(tool_path: pathlib.Path = pathlib.Path(__file__), sidecar: pathlib.Path = DEMO_SIDECAR, tool_rel: str = TOOL_REL) -> dict:
    """R40 binding: valid_for_this_commit iff the sidecar's tool sha256 (recorded at demo time) == this file's sha256 now and all demo cases PASSed."""
    now = hashlib.sha256(tool_path.read_bytes()).hexdigest()
    out = {"rule": "Δ46/R40: failure behaviour demonstrated on a mutated copy by gate1/control_failure_demo_c.py; binding = tool sha256", "sidecar": str(sidecar),
           "tool_sha256_now": now, "sidecar_present": sidecar.is_file(), "sidecar_tool_sha256": None, "sha_match": False, "cases": [], "demo_all_pass": False,
           "valid_for_this_commit": False, "reason": None}
    if not sidecar.is_file():
        out["reason"] = "NO_SIDECAR: demonstration never run (or not for this checkout)"; return out
    try:
        sc = json.loads(sidecar.read_text(encoding="utf-8"))
        cases = [c for c in sc.get("cases", []) if c.get("tool_path") == tool_rel]
    except Exception as e:
        out["reason"] = f"SIDECAR_UNREADABLE: {type(e).__name__}: {e}"[:160]; return out
    out["sidecar_measured_at_kst"] = sc.get("measured_at_kst"); out["sidecar_sha256"] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
    shas = sorted({c.get("tool_sha256_at_demo") for c in cases})
    out["cases"] = [{"case_name": c.get("case_name"), "result": c.get("result")} for c in cases]
    if not cases: out["reason"] = "NO_CASES_FOR_THIS_TOOL"; return out
    if len(shas) != 1: out["reason"] = f"SIDECAR_INCONSISTENT: {len(shas)} distinct tool shas for one tool"; return out
    out["sidecar_tool_sha256"] = shas[0]; out["sha_match"] = shas[0] == now
    out["demo_all_pass"] = all(c.get("result") == "PASS" for c in cases)
    out["valid_for_this_commit"] = out["sha_match"] and out["demo_all_pass"]
    out["reason"] = "OK" if out["valid_for_this_commit"] else ("TOOL_CHANGED_SINCE_DEMO: re-run gate1/control_failure_demo_c.py" if not out["sha_match"] else "DEMO_CASE_FAILED")
    return out

def _ts(d: dict) -> str:
    return str(d.get("created_at_kst") or d.get("created_at") or "")

def is_v3_era(d: dict, path: str) -> bool:
    ts = _ts(d)
    if ts:
        return ts >= V3_CUTOFF_ISO          # ISO-KST string compare (monotonic here); a 'Z'/UTC created_at is at most 9h off and rare
    try: return os.stat(path).st_mtime >= V3_CUTOFF_EPOCH
    except OSError: return False

def _as_list(v):
    return [v] if isinstance(v, str) else list(v or [])

def _keys(d: dict) -> set:
    ks = set(d.keys())
    p = d.get("payload")
    if isinstance(p, dict): ks |= set(p.keys())
    return ks

def _get(d: dict, k: str):
    if d.get(k) not in (None, ""): return d[k]
    p = d.get("payload")
    return p.get(k) if isinstance(p, dict) else None

def scan(bus_dir: str, plane: str = "C") -> dict:
    tdir = os.path.join(bus_dir, "tickets"); adir = os.path.join(bus_dir, "acks")
    acked = {os.path.basename(p)[: -len(f".{plane}.json")] for p in glob.glob(os.path.join(adir, f"*.{plane}.json"))}
    files = sorted(glob.glob(os.path.join(tdir, "*.json")))
    pending, errors, changed, unrecorded = [], [], [], []
    for p in files:
        tid = os.path.basename(p)[:-5]
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            errors.append({"file": os.path.basename(p), "error": f"{type(e).__name__}: {e}"[:120]}); continue
        to = _as_list(d.get("to")); cc = _as_list(d.get("cc"))
        if (plane in to or plane in cc) and d.get("from") != plane and tid in acked:
            # D-DEF-13 class: bind ACK to ticket bytes
            cur = hashlib.sha256(open(p, "rb").read()).hexdigest()
            readable_acks = 0
            for ap in sorted(glob.glob(os.path.join(adir, f"{tid}.{plane}*.json"))):
                try: a = json.load(open(ap, encoding="utf-8"))
                except Exception as e:   # D-V3-FINDING-023 class: an unreadable ACK is NOT an ACK and NOT 'old format'
                    errors.append({"file": "acks/" + os.path.basename(ap), "kind": "ACK_UNREADABLE", "error": f"{type(e).__name__}: {e}"[:120]}); continue
                readable_acks += 1
                s_ = a.get("ticket_sha256")
                if s_ is None: unrecorded.append(tid)
                elif s_ != cur: changed.append({"ticket_id": tid, "ack": os.path.basename(ap), "acked_sha": s_[:12], "current_sha": cur[:12], "explained": EXPLAINED_CHANGES.get((tid, os.path.basename(ap)))})
            if readable_acks == 0:   # every ACK file for this ticket was unreadable ⇒ treat as un-ACKed (fail-closed)
                pending.append({"ticket_id": tid, "from": d.get("from"), "type": d.get("type"), "priority": d.get("priority"), "via": "to" if plane in to else "cc", "note": "ACK_UNREADABLE — no readable ACK file"})
        if (plane in to or plane in cc) and d.get("from") != plane and tid not in acked:
            pending.append({"ticket_id": tid, "from": d.get("from"), "type": d.get("type"), "priority": d.get("priority"), "via": "to" if plane in to else "cc"})
    # T-A-V3-STEP1-008 forward rule: no ACK/completion without a ticket file (v3-era only, checked by mtime >= cutoff)
    ticket_ids = {os.path.basename(f)[:-5] for f in files}
    dangling = []
    for sub in ("acks", "completions"):
        for p2 in glob.glob(os.path.join(bus_dir, sub, "*.json")):
            base = os.path.basename(p2)[:-5]
            tid = ACK_SUFFIX_RE.sub("", base)  # strip plane suffixes incl. R19 re-ACKs (X.C-1) and meta-ACKs (X.A.B)
            if tid in ticket_ids:
                continue
            try:
                j = json.load(open(p2, encoding="utf-8")); ts = str(j.get("created_at_kst") or j.get("acked_at") or j.get("created_at") or j.get("completed_at") or "")
            except Exception as e:   # unreadable ≠ pre-v3: report, and count as dangling-unverifiable rather than silently old
                errors.append({"file": f"{sub}/{os.path.basename(p2)}", "kind": "REF_UNREADABLE", "error": f"{type(e).__name__}: {e}"[:120]})
                dangling.append({"file": f"{sub}/{os.path.basename(p2)}", "missing_ticket": tid, "note": "UNREADABLE — era undeterminable"}); continue
            if ts >= V3_CUTOFF_ISO:  # v3 adoption (T-A-V3-P0-001); string compare on ISO-KST is monotonic here
                dangling.append({"file": f"{sub}/{os.path.basename(p2)}", "missing_ticket": tid})
    import datetime as _dt
    _kst=_dt.timezone(_dt.timedelta(hours=9))
    return {"measured_at_kst": _dt.datetime.now(_kst).isoformat(timespec="seconds"), "scanned": len(files), "pending": pending, "parse_errors": errors, "dangling_refs_v3_era": dangling, "content_changed_after_ack": changed, "acked_sha_unrecorded_n": len(set(unrecorded)), "status": "PARSE_ERRORS_PRESENT" if errors else "OK"}

def load_tickets(bus_dir: str) -> list:
    out = []
    for p in sorted(glob.glob(os.path.join(bus_dir, "tickets", "*.json"))):
        try: d = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        out.append((os.path.basename(p)[:-5], p, d, is_v3_era(d, p)))
    return out

# ---------------------------------------------------------------- (a) Δ6-a
def check_plane_enum(tickets) -> dict:
    viol, e_gaps, n_e_real = [], [], 0
    for tid, p, d, v3 in tickets:
        if not v3: continue
        for field in ("from", "to", "cc"):
            for v in _as_list(d.get(field)):
                if str(v).strip() not in PLANES:
                    viol.append({"ticket_id": tid, "field": field, "value": v})
        frm, to = str(d.get("from")), [str(x) for x in _as_list(d.get("to"))]
        if "E" in {frm, *to}:
            real = bool(d.get("real_target")) or any(re.search(r"\bREAL(_TARGET)?\b", str(_get(d, k) or "")) for k in ("scope", "mode", "execution_mode", "real_scope_id", "type", "claim_kind", "headline"))
            if real:
                n_e_real += 1
                missing = [k for k in E_REAL_REQUIRED if _get(d, k) in (None, "")]
                if missing: e_gaps.append({"ticket_id": tid, "from": frm, "to": to, "missing": missing})
    return {"rule": "Δ6-a: from/to/cc ⊆ {A,B,C,D,E,DIRECTOR}; E REAL ticket needs " + ", ".join(E_REAL_REQUIRED), "v3_era_checked": sum(1 for t in tickets if t[3]),
            "violations": viol, "e_real_tickets": n_e_real, "e_real_field_gaps": e_gaps}

# ---------------------------------------------------------------- (b) Δ4 --ref-lint
def ref_lint(tickets, root: pathlib.Path) -> dict:
    hits = []
    self_path = pathlib.Path(__file__).resolve()
    for p in sorted(root.rglob("*")):
        if p.suffix not in (".py", ".md") or "__pycache__" in p.parts or p.resolve() == self_path: continue
        try: lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError: continue
        for i, ln in enumerate(lines, 1):
            if "ls-remote" in ln: continue
            if BARE_REF_RE.search(ln):
                hits.append({"where": f"{p.relative_to(root)}:{i}", "kind": "c_file", "sha_on_same_line": bool(SHA40_RE.search(ln)), "text": ln.strip()[:160]})
    for tid, p, d, v3 in tickets:
        if not v3: continue
        for i, ln in enumerate(json.dumps(d, ensure_ascii=False, indent=1).splitlines(), 1):
            if "ls-remote" in ln: continue
            if BARE_REF_RE.search(ln):
                hits.append({"where": f"tickets/{tid}.json#L{i}", "kind": "v3_ticket", "sha_on_same_line": bool(SHA40_RE.search(ln)), "text": ln.strip()[:160]})
    return {"rule": "Δ4: promoted main only as origin/<branch> or exact SHA; bare branch name forbidden (ls-remote lines ignored)", "scanned_root": str(root), "hits": hits}

# ---------------------------------------------------------------- (c) Δ13-R17
def check_fact_correction(tickets) -> dict:
    rows = []
    for tid, p, d, v3 in tickets:
        t = str(d.get("type") or "")
        if not (t in ("FACT_CORRECTION", "FACTUAL_CORRECTION") or "FACT_CORRECTION" in tid or re.search(r"-FC-\d+", tid)): continue
        ks = _keys(d)
        hk = sorted(k for k in ks if HOW_KNOWN_RE.match(k))
        if not hk:
            rows.append({"ticket_id": tid, "from": d.get("from"), "type": t, "v3_era": v3, "keys": sorted(ks)[:25]})
    return {"rule": "Δ13-R17: a retraction/correction states how it was known (how_known / evidence / measurement-like field)", "missing_how_known": rows}

# ---------------------------------------------------------------- (d) Δ5-vr
def check_validity_risk(tickets) -> dict:
    below, vrc = [], []
    for tid, p, d, v3 in tickets:
        fc = str(_get(d, "finding_class") or "")
        pr = str(d.get("priority") or "")
        if "VALIDITY_RISK" in fc.upper() and pr not in ("P0", "P1"):
            below.append({"ticket_id": tid, "from": d.get("from"), "type": d.get("type"), "finding_class": fc, "priority": pr, "v3_era": v3})
        if str(d.get("type")) == "VALIDITY_RISK_CANDIDATE" and pr not in ("P0", "P1"):
            vrc.append({"ticket_id": tid, "from": d.get("from"), "priority": pr, "v3_era": v3})
    return {"rule": "Δ5-vr: finding_class VALIDITY_RISK only at P0/P1", "below_p1": below, "informational_type_VALIDITY_RISK_CANDIDATE_below_p1": vrc}

# ---------------------------------------------------------------- (e) Δ21
def git_show(repo: str, ref: str) -> str | None:
    try: return subprocess.run(["git", "-C", repo, "show", ref], capture_output=True, text=True, timeout=30, check=True).stdout
    except Exception: return None

def shape_unsafe_alias(a: str) -> bool:
    """Δ25 shape proxy (kept as a *report-only* proxy after Δ33): lowercase single word (no separators), length <= 6."""
    return len(a) <= 6 and a == a.lower() and re.fullmatch(r"[a-z][a-z0-9]*", a) is not None

# Δ33 (index v17 alias_rules): the criterion is specificity, not shape — an alias is unsafe iff it fires in prose that has
# nothing to do with any ruling. C keeps its own control corpus (independent of A's self_check corpus); token-bounded match.
ALIAS_CONTROL_CORPUS = (
    "This document describes a build pipeline. It has a cache, b-tree indexes, and c-style comments. Contact plane C for details. "
    "The coverage report is generated per manifest; each container runs one strategy and stores evidence under an auth token. "
    "Please skip the vr headset demo, the domax vendor call, and the scrollbar fix; the runbook lives in the wiki. "
    "이 문단은 판정과 무관하다. 커버리지 보고서는 매니페스트별로 생성되고, 컨테이너는 하나의 전략을 실행하며 증거를 인증 토큰 아래에 저장한다. "
    "회의는 3층 회의실에서 열리고 자료는 공유 폴더에 있다. 예산은 다음 분기에 확정된다."
)

def alias_fires_in_corpus(a: str, corpus: str = ALIAS_CONTROL_CORPUS) -> bool:
    return re.search(r"(?<![\w-])" + re.escape(a) + r"(?![\w-])", corpus) is not None

def unsafe_alias(a: str) -> bool:
    """Δ33: unsafe iff it fires in the ruling-unrelated control corpus (measured), regardless of shape."""
    return alias_fires_in_corpus(a)

class RulingIndex:
    def __init__(self, obj: dict, source: str, sha256: str):
        self.source, self.sha256, self.version = source, sha256, obj.get("version")
        self.rows = obj["rulings"]; self.ids = [r["id"] for r in self.rows]
        self.empty_alias_rows = [r["id"] for r in self.rows if not r.get("aliases")]
        amap = collections.defaultdict(list)
        for r in self.rows:
            for a in r.get("aliases") or []:
                if r["id"] not in amap[a]: amap[a].append(r["id"])
        self.alias_map = dict(amap)
        self.collisions = {a: ids for a, ids in amap.items() if len(ids) > 1}
        self.unsafe = sorted(a for a in amap if unsafe_alias(a))
        self.short_alpha = sorted(a for a in amap if len(a) < 3 and a.isascii() and a.isalpha())   # Δ25: index defect report
        self.shape_unsafe = sorted(a for a in amap if shape_unsafe_alias(a))                          # Δ25 proxy, report-only
        self.alias_rules = obj.get("alias_rules")
        self.safe_alias_map = {a: ids for a, ids in amap.items() if not unsafe_alias(a)}
        # second channel (report-only): A's own control corpus from index alias_rules, if declared — never replaces C's corpus
        ar = obj.get("alias_rules") or {}
        a_corpus = ar.get("control_corpus") if isinstance(ar, dict) else None
        if isinstance(a_corpus, list): a_corpus = " ".join(str(x) for x in a_corpus)
        self.a_corpus_present = isinstance(a_corpus, str) and bool(a_corpus.strip())
        self.unsafe_by_a_corpus = sorted(a for a in amap if self.a_corpus_present and alias_fires_in_corpus(a, a_corpus)) if self.a_corpus_present else None
    def resolve(self, token: str) -> list:
        """ids for a token: exact id, else safe alias (token-bounded, case-sensitive equality on the whole token)."""
        if token in self.ids: return [token]
        return list(self.safe_alias_map.get(token, []))
    def resolve_unsafe(self, token: str) -> list:
        return [] if token in self.ids else list(self.alias_map.get(token, [])) if unsafe_alias(token) else []
    def resolve_by_subrows(self, token: str) -> list:
        """bare section 'Δ12' → rows 'Δ12-*'; 'Δ8-R3' → 'Δ8-R3a'/'Δ8-R3b'; 'R13' → rows aliased 'R13a'/'R13b'."""
        ids = [i for i in self.ids if i.startswith(token + "-")]
        if not ids: ids = [i for i in self.ids if re.fullmatch(re.escape(token) + r"[a-z]", i)]
        if not ids: ids = sorted({i for a, ids_ in self.safe_alias_map.items() for i in ids_ if re.fullmatch(re.escape(token) + r"[a-z]", a)})
        return ids

def index_controls(idx: RulingIndex) -> list:
    """Positive/negative controls (T-B-V3-FINDING-005 pattern): run before the main check; any failure → refuse."""
    checks = [
        ("positive R21→Δ21", idx.resolve("R21") == ["Δ21"]),
        ("positive R20→Δ18-R20", idx.resolve("R20") == ["Δ18-R20"]),
        ("positive Δ18-R20→Δ18-R20", idx.resolve("Δ18-R20") == ["Δ18-R20"]),
        ("negative STEP1↛Δ20", "Δ20" not in idx.resolve("STEP1") and "Δ20" not in idx.resolve_unsafe("STEP1")),
        ("negative R15↛Δ20", "Δ20" not in idx.resolve("R15")),
        ("Δ33 positive: shape-clean prose words fire in corpus", all(alias_fires_in_corpus(w) for w in ("coverage", "manifest", "container", "strategy", "evidence", "auth", "skip"))),
        ("Δ33 negative: real ruling names do not fire in corpus", not any(alias_fires_in_corpus(w) for w in ("Δ18-R20", "R21", "GAP-07", "scrollfix", "THREE_TURN_RUNBOOK", "DOM/AX 불일치"))),
    ]
    return [{"control": n, "result": "PASS" if ok else "FAIL"} for n, ok in checks]

def token_in(text: str, tok: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(tok) + r"(?![A-Za-z0-9_])", text) is not None

def check_ruling_index(tickets, repo: str, index_ref: str, index_file: str | None, delta_ref: str) -> dict:
    raw = None; source = None
    fetch_info = fetch_control(repo)
    if index_file:
        raw = pathlib.Path(index_file).read_text(encoding="utf-8"); source = index_file
    else:
        raw = git_show(repo, index_ref); source = f"git show {index_ref}"
    if raw is None:
        return {"status": "INDEX_UNAVAILABLE", "source": source}
    idx_obj = json.loads(raw)
    idx = RulingIndex(idx_obj, source, hashlib.sha256(raw.encode("utf-8")).hexdigest())
    controls = index_controls(idx)
    out = {"index_source": source, "control_fetch": fetch_info, "index_version": idx.version, "index_rows": len(idx.rows), "index_sha256": idx.sha256, "controls": controls,
           "alias_rule_applied": "index v17 alias_rules / Δ33: alias unsafe iff it fires in C's ruling-unrelated control corpus (specificity, measured); Δ25 shape rule kept as report-only proxy; token-boundary matching",
           "index_alias_rules_present": idx.alias_rules is not None,
           "alias_collisions": idx.collisions, "unsafe_aliases": idx.unsafe, "unsafe_aliases_by_index_control_corpus": idx.unsafe_by_a_corpus, "index_control_corpus_declared": idx.a_corpus_present, "shape_unsafe_aliases_delta25_proxy": idx.shape_unsafe, "short_alpha_aliases": idx.short_alpha, "empty_alias_rows": idx.empty_alias_rows}
    if any(c["result"] == "FAIL" for c in controls):
        out["status"] = "CONTROLS_FAILED_MAIN_CHECK_REFUSED"; return out
    a_tickets = [(tid, d) for tid, p, d, v3 in tickets if v3 and str(d.get("from")) == "A"]
    mentions = collections.defaultdict(set)          # token -> ticket ids
    for tid, d in a_tickets:
        text = json.dumps(d, ensure_ascii=False)
        for m in DELTA_TOKEN_RE.findall(text): mentions[m].add(tid)
        for m in R_TOKEN_RE.findall(text): mentions[m].add(tid)
    unrecorded, via_unsafe, via_sub, resolved_rows = [], [], [], set()
    for tok, tids in sorted(mentions.items()):
        ids = idx.resolve(tok)
        if ids:
            resolved_rows.update(ids); continue
        sr = idx.resolve_by_subrows(tok)
        if sr:
            resolved_rows.update(sr); via_sub.append({"token": tok, "rows": sr, "tickets": sorted(tids)}); continue
        u = idx.resolve_unsafe(tok)
        if u: via_unsafe.append({"token": tok, "would_resolve_to": u, "tickets": sorted(tids)}); continue
        unrecorded.append({"token": tok, "tickets": sorted(tids)})
    # aliases present in A tickets (id/alias tokens that the regexes do not extract, e.g. 'GAP-06', 'STEP1-015')
    for tid, d in a_tickets:
        text = json.dumps(d, ensure_ascii=False)
        for a, ids in idx.safe_alias_map.items():
            if token_in(text, a): resolved_rows.update(ids)
        for i in idx.ids:
            if token_in(text, i): resolved_rows.add(i)
    delta = git_show(repo, delta_ref) or ""
    # v21: delta headings include `### Rn` sub-headings (resolve via alias); id may carry inner hyphens; token-bounded end
    heads = [h.strip() for h in re.findall(r"^#{2,3}\s+(Δ\d+(?:-[A-Za-z0-9\-]+)?|R\d+)(?![0-9A-Za-z_-])", delta, re.M)]
    heads_without_row = sorted({h for h in heads if not idx.resolve(h) and not idx.resolve_by_subrows(h)})
    # (g) Δ21/STEP1-029 index→delta reachability: a row is reachable iff (a) its id is a delta heading, (b) any id/alias token
    # appears in the delta body (token-bounded, C's single boundary regex — Δ33 specificity, no shape filter), or
    # (c) it is a declared split row whose parent section exists (index `split_rows.map`). Positive control: fake row Δ999-R99.
    split_map = ((idx_obj.get("split_rows") or {}).get("map") or {}) if isinstance(idx_obj, dict) else {}
    def _tok_delta(t: str) -> bool:
        return re.search(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", delta) is not None
    def _reachable(row: dict) -> str | None:
        """v21 declared 4-path rule: (a) id heading (b) authority heading (c) id/alias token in body (d) split_rows parent.
        Order matters for the 'anchor-only' report: content-specific paths (a)(c) are tried before parent anchors (b)(d)."""
        rid = row["id"]
        if rid in heads: return "heading"
        if any(_tok_delta(t) for t in [rid] + list(row.get("aliases") or [])): return "token"
        auth = row.get("authority") or ""
        if auth and auth in heads: return "authority_heading"
        parent = split_map.get(rid)
        if parent and (parent in heads or _tok_delta(parent)): return "split_parent"
        return None
    reach = {r["id"]: _reachable(r) for r in idx.rows}
    unreachable_rows = sorted(k for k, v in reach.items() if v is None)
    # NB: A's own positive control 'Δ999-R99' is written into the delta text (Δ33/self_check prose), so it is now *reachable* by
    # token — a contaminated control. C uses a fake that no document mentions and reports A's as a separate observation.
    reach_controls = [{"control": "positive: fake row Δ997-R97 (never written anywhere) unreachable", "result": "PASS" if _reachable({"id": "Δ997-R97", "aliases": ["R97", "C_FAKE_ALIAS_NEVER_WRITTEN"]}) is None else "FAIL"},
                      {"control": "observation: A's control Δ999-R99 reachable-by-token in delta (contaminated if true)", "result": "CONTAMINATED" if _reachable({"id": "Δ999-R99", "aliases": ["R99"]}) else "CLEAN"},
                      {"control": "negative: Δ21 reachable", "result": "PASS" if reach.get("Δ21") else "FAIL"},
                      # D-V3-FINDING-015: a fake CHILD whose parent section exists discriminates the declared (split_rows-only) rule
                      # from an all-hyphen-ids-inherit rule; under C's declared-rule implementation it must be unreachable.
                      {"control": "discriminating: fake child Δ15-NOSUCH without authority → unreachable", "result": "PASS" if _reachable({"id": "Δ15-NOSUCH", "aliases": []}) is None else "FAIL"},
                      {"control": "documented: fake child Δ15-NOSUCH with authority=Δ15 → reachable via parent anchor under v21 rule (shows the rule's blind spot)", "result": "AS_DOCUMENTED" if _reachable({"id": "Δ15-NOSUCH", "aliases": [], "authority": "Δ15"}) == "authority_heading" else "UNEXPECTED"}]
    out.update({"status": "OK", "a_tickets_v3_era": len(a_tickets), "tokens_mentioned": len(mentions),
                "index_to_delta_reachability": {"rule": "v21: id heading | id/alias token | authority heading | split_rows parent (STEP1-029 + D-V3-FINDING-015)", "split_rows_declared": len(split_map),
                                                "unreachable_rows": unreachable_rows, "reached_only_via_split_parent": sorted(k for k, v in reach.items() if v == "split_parent"),
                                                "reached_only_via_parent_anchor": sorted(k for k, v in reach.items() if v in ("authority_heading", "split_parent")),
                                                "note": "rows in reached_only_via_parent_anchor satisfy the v21 rule but have no row-specific token in the delta (D-V3-FINDING-015 caveat) — reported, not a defect",
                                                "controls": reach_controls},
                "unrecorded_mentions": unrecorded, "resolved_only_via_unsafe_alias": via_unsafe, "section_mentions_resolved_by_subrows": via_sub,
                "index_rows_unmentioned_in_A_tickets": sorted(set(idx.ids) - resolved_rows),
                "delta_headings_without_index_row": heads_without_row, "delta_source": f"git show {delta_ref}",
                "delta_sha256": hashlib.sha256(delta.encode("utf-8")).hexdigest(), "delta_heading_counts": {"##_only_distinct": len({h for h in heads if not h.startswith("R")}), "all_with_dups": len(heads), "all_distinct": len(set(heads))}})
    return out

# ---------------------------------------------------------------- (f) Δ26
BASE_SHA_CLASSES = ("NO_FIELD", "NOT_A_SHA", "MISSING", "OK_ABBREV", "OK")

def classify_base_sha(bs, repo: str) -> str:
    """Δ26: NO_FIELD (absent/empty) · NOT_A_SHA (not hex; a ref like origin/x is still checked and reported as NOT_A_SHA if it does not resolve)
    · MISSING (hex but git cat-file -e fails) · OK_ABBREV (resolves but shorter than 40) · OK (40 lowercase hex that resolves)."""
    if not isinstance(bs, str) or not bs.strip(): return "NO_FIELD"
    bs = bs.strip()
    if not re.fullmatch(r"[0-9a-f]{7,40}", bs):
        ok = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "--quiet", f"{bs}^{{commit}}"], capture_output=True).returncode == 0
        return "OK_ABBREV" if ok else "NOT_A_SHA"          # a resolving ref is usable but not an exact object id → reported like an abbreviation
    ok = subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{bs}^{{commit}}"], capture_output=True).returncode == 0
    if not ok: return "MISSING"
    return "OK" if len(bs) == 40 else "OK_ABBREV"

def check_base_sha(tickets, repo: str) -> dict:
    by = {c: [] for c in BASE_SHA_CLASSES}; n = 0
    for tid, p, d, v3 in tickets:
        if not v3: continue
        n += 1
        bs = d.get("base_sha"); c = classify_base_sha(bs, repo)
        by[c].append({"ticket_id": tid, "from": d.get("from"), "base_sha": bs})
    out = {"rule": "Δ26: base_sha must be a real object (git cat-file -e <sha>^{commit}); classes NO_FIELD / NOT_A_SHA / MISSING / OK_ABBREV / OK",
           "v3_era_checked": n, "counts": {c: len(v) for c, v in by.items()},
           "unresolvable": by["NO_FIELD"] + by["NOT_A_SHA"] + by["MISSING"],
           "ok_abbrev": by["OK_ABBREV"], "ok_full_n": len(by["OK"])}
    return out

def selftest(repo: str = DEFAULT_REPO) -> int:
    """Controls for the scanner's own rules (verification-requires-control-group): exit 0 iff every case behaves as declared."""
    import tempfile
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    fails = []
    with tempfile.TemporaryDirectory(prefix="c_bus_scan_selftest_") as td:
        t = pathlib.Path(td); (t / "tickets").mkdir(); (t / "acks").mkdir(); (t / "completions").mkdir()
        v3 = {"created_at_kst": "2026-08-28T05:00:00+09:00", "from": "A", "to": ["C"], "type": "FINDING", "priority": "P2"}
        (t / "tickets" / "X.json").write_text(json.dumps({"ticket_id": "X", **v3, "base_sha": head}))
        (t / "acks" / "X.C-1.json").write_text(json.dumps({"kind": "ACK", "ticket_id": "X", "acked_at": "2026-08-28T05:01:00+09:00", "ticket_sha256": hashlib.sha256((t / "tickets" / "X.json").read_bytes()).hexdigest()}))
        (t / "acks" / "X.C.json").write_text(json.dumps({"kind": "ACK", "ticket_id": "X", "acked_at": "2026-08-28T05:00:30+09:00", "ticket_sha256": hashlib.sha256((t / "tickets" / "X.json").read_bytes()).hexdigest()}))
        (t / "acks" / "X.A.B.json").write_text(json.dumps({"kind": "ACK", "acked_at": "2026-08-28T05:02:00+09:00"}))
        (t / "acks" / "Y.C.json").write_text(json.dumps({"kind": "ACK", "ticket_id": "Y", "acked_at": "2026-08-28T05:03:00+09:00"}))
        r = scan(str(t))
        dang = sorted(x["missing_ticket"] for x in r["dangling_refs_v3_era"])
        if dang != ["Y"]: fails.append(f"dangling: expected ['Y'] (X.C-1 / X.A.B must strip to X), got {dang}")
        cases = {None: "NO_FIELD", "origin/nonexistent-ref-for-selftest": "NOT_A_SHA", "deadbeef" * 5: "MISSING", head[:10]: "OK_ABBREV", head: "OK", "0123abcd": "MISSING"}
        for bs, want in cases.items():
            got = classify_base_sha(bs, repo)
            if got != want: fails.append(f"base_sha {bs!r}: expected {want}, got {got}")
    for f in fails: print("SELFTEST FAIL:", f)
    print("SELFTEST", "OK" if not fails else "FAILED", "(dangling re-ACK strip + base_sha classes)")
    return 0 if not fails else 1

def main(argv: list) -> int:
    if argv[:1] == ["selftest"]: return selftest()
    bus = "/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2"; do_lint = False
    root = ASSURANCE_ROOT; repo = DEFAULT_REPO; index_ref = DEFAULT_INDEX_REF; index_file = None
    it = iter(argv)
    for a in it:
        if a == "--ref-lint": do_lint = True
        elif a == "--assurance-root": root = pathlib.Path(next(it))
        elif a == "--repo": repo = next(it)
        elif a == "--index-ref": index_ref = next(it)
        elif a == "--index-file": index_file = next(it)
        elif a.startswith("--"): print(f"unknown flag {a}", file=sys.stderr); return 3
        else: bus = a
    res = scan(bus)
    tickets = load_tickets(bus)
    res["plane_enum"] = check_plane_enum(tickets)
    res["ref_lint"] = ref_lint(tickets, root) if do_lint else {"skipped": "pass --ref-lint"}
    res["fact_correction_how_known"] = check_fact_correction(tickets)
    res["validity_risk_priority"] = check_validity_risk(tickets)
    res["ruling_record_gaps"] = check_ruling_index(tickets, repo, index_ref, index_file, DEFAULT_DELTA_REF)
    res["base_sha_unresolvable"] = check_base_sha(tickets, repo)
    res["failure_behaviour_demo"] = failure_demo_binding()
    rg = res["ruling_record_gaps"]
    ctl = "PASS" if rg.get("status") == "OK" else rg.get("status")
    ran = rg.get("status") == "OK"          # declared: on refusal no main-check number is emitted — `n/a`, never 0
    def _n(key, *, dict_=False):
        return len(rg.get(key, {} if dict_ else [])) if ran else "n/a"
    res["summary"] = ("SUMMARY: scanned={scanned} pending={p} parse_errors={pe} dangling={dg} changed_after_ack={ch} plane_enum_violations={pv} e_real_field_gaps={eg} "
                      "ref_lint_hits={rl} fact_correction_missing_how_known={fc} validity_risk_below_p1={vr} vrc_type_below_p1={vrc} ruling_unrecorded_mentions={ru} "
                      "resolved_by_subrows={rs} alias_collisions={ac} unsafe_aliases={ua} empty_alias_rows={ea} delta_headings_without_index_row={dh} "
                      "base_sha[no_field/not_sha/missing/ok_abbrev/ok]={bc} controls={ctl} demo_valid_for_this_commit={dv}").format(
        scanned=res["scanned"], p=len(res["pending"]), pe=len(res["parse_errors"]), dg=len(res["dangling_refs_v3_era"]), ch=len(res["content_changed_after_ack"]),
        pv=len(res["plane_enum"]["violations"]), eg=len(res["plane_enum"]["e_real_field_gaps"]), rl=len(res["ref_lint"].get("hits", [])) if do_lint else "skipped",
        fc=len(res["fact_correction_how_known"]["missing_how_known"]), vr=len(res["validity_risk_priority"]["below_p1"]),
        vrc=len(res["validity_risk_priority"]["informational_type_VALIDITY_RISK_CANDIDATE_below_p1"]), ru=_n("unrecorded_mentions"),
        rs=_n("section_mentions_resolved_by_subrows"), ac=_n("alias_collisions", dict_=True), ua=_n("unsafe_aliases"),
        ea=_n("empty_alias_rows"), dh=_n("delta_headings_without_index_row"),
        bc="/".join(str(res["base_sha_unresolvable"]["counts"][c]) for c in BASE_SHA_CLASSES), ctl=ctl, dv=res["failure_behaviour_demo"]["valid_for_this_commit"])
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(res["summary"], file=sys.stderr)
    if rg.get("status", "OK") != "OK":
        print(f"REFUSED: ruling-index controls failed or index unavailable ({rg.get('status')}) — Δ21 main check not run (exit 2 = did not run)", file=sys.stderr); return 2
    if res["status"] != "OK":
        print(f"FAILED: scan ran, bus status {res['status']} (exit 1 = ran and failed)", file=sys.stderr); return 1
    return 0

if __name__ == "__main__":
    try:
        _rc = main(sys.argv[1:])
    except Exception:                       # Δ46-exit2: an uncaught exception is NOT a failure verdict — it is "did not run"
        import traceback; traceback.print_exc()
        print(DID_NOT_RUN_MSG, file=sys.stderr); _rc = 2
    sys.exit(_rc)
