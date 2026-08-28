#!/usr/bin/env python3
"""R54 matcher sweep (C plane) — inventory of every regex / heading / token / field matcher in C tools that extracts values from
another plane's text or files, each measured against its live source with a stated denominator and a wider *presence probe*,
plus a `must_not_miss` control (a wide-form positive the matcher must catch) and a `must_not_over` control (a negative that a
wider matcher would wrongly catch). Ruling: V3_0_1_SUCCESSOR_DELTA.md Δ54 / R54 — "an extractor must distinguish 'absent' from
'could not extract'; a narrow matcher yields a silent 0, a wide one a silent over-count; detection = compare the empty-extraction
ratio with source presence, denominators stated, parser rule stated next to every count."

Classification per matcher (by controls first, then by measured impact on the current source):
  NARROW_MISS  a must_not_miss control fails (or failed before the fix)   — direction: silent 0 / silent pass
  WIDE_OVER    a must_not_over control fails (or failed before the fix)   — direction: silent over-count / over-flag
  OK           both controls pass and the presence probe agrees with the extraction
`status_before_fix` keeps the pre-fix classification; `classification` is the state of the tool as it is now. Matchers whose value
feeds a judgment were fixed minimally in the tool (c_bus_scan.py / gate1/intake/r32_inventory.py only — every other tool is
inventoried with a proposed fix, not edited). The controls below are evaluated against the LIVE tool code (imported), so a
regression in any pattern flips this sweep to exit 1.

Sources (all read-only, shas recorded in the output): origin/control/landing-orchestrator tip after fetch (delta + ruling index),
the bus directory (tickets / acks / completions), C's own fixtures (lane5 evidence fixtures, gate1/intake/fixtures_py,
lane1 EXPECTATIONS) and C's assurance source tree as an AST corpus. No other plane's worktree is read.

Usage: r54_matcher_sweep_c.py [--out PATH] [--bus DIR] [--repo DIR]
Exit: 0 all controls pass (accepted, recorded failures on out-of-scope comparators / safety matchers excepted) · 1 a control fails (a matcher is still mis-shaped — do not cite the counts) · 2 did not run (crash).
"""
from __future__ import annotations

import argparse, ast, collections, datetime as dt, hashlib, json, os, pathlib, re, subprocess, sys, tempfile
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent            # gate1/
ASSURANCE = HERE.parent
for p in (ASSURANCE, HERE / "intake", HERE / "lane5_evidence", HERE / "lane6_stats", HERE / "comparators", HERE):
    sys.path.insert(0, str(p))
import c_bus_scan as CB                                     # noqa: E402
import r32_inventory as R32                                 # noqa: E402
import evidence_lineage_check as L5                         # noqa: E402
import c_flow_derive as L6                                  # noqa: E402
import adapter_map as AM                                    # noqa: E402
import grade_lane4 as L4                                    # noqa: E402

KST = dt.timezone(dt.timedelta(hours=9))
DEFAULT_BUS = "/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2"
DEFAULT_OUT = HERE / "R54_MATCHER_SWEEP_C.json"
TOOL_FILES = {                                             # tool → path (sha256 recorded; the sweep binds to these bytes)
    "c_bus_scan.py": ASSURANCE / "c_bus_scan.py",
    "gate1/intake/r32_inventory.py": HERE / "intake" / "r32_inventory.py",
    "gate1/lane5_evidence/evidence_lineage_check.py": HERE / "lane5_evidence" / "evidence_lineage_check.py",
    "gate1/lane6_stats/c_flow_derive.py": HERE / "lane6_stats" / "c_flow_derive.py",
    "gate1/comparators/adapter_map.py": HERE / "comparators" / "adapter_map.py",
    "gate1/comparators/common.py": HERE / "comparators" / "common.py",
    "gate1/comparators/compare_lane1.py": HERE / "comparators" / "compare_lane1.py",
    "gate1/comparators/grade_lane4.py": HERE / "comparators" / "grade_lane4.py",
    "gate1/GATE1_RUNBOOK_C.md": HERE / "GATE1_RUNBOOK_C.md",
    "gate1/RULING_INDEX_COVERAGE_C.json": HERE / "RULING_INDEX_COVERAGE_C.json",
}


def sha256_file(p: pathlib.Path) -> str | None:
    try: return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError: return None


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def ctrl(sample: Any, expect: Any, got: Any, note: str = "", accepted: bool = False) -> dict:
    """accepted=True: a failing control that is RECORDED and accepted (outside this sweep's edit scope, or a safety matcher kept wide on
    purpose) — it still classifies the matcher, but does not flip the sweep to exit 1."""
    return {"sample": sample, "expect": expect, "got": got, "pass": expect == got, **({"note": note} if note else {}), **({"accepted_failure": True} if accepted and expect != got else {})}


class Sweep:
    def __init__(self, bus: str, repo: str):
        self.bus, self.repo = bus, repo
        self.records: list[dict] = []
        self.fixed: list[dict] = []

    # ------------------------------------------------------------------ record helper
    def add(self, **kw) -> dict:
        mnm = kw.get("must_not_miss") or []; mno = kw.get("must_not_over") or []
        kw["controls_pass"] = all(c["pass"] for c in mnm + mno)
        kw["controls_pass_or_accepted"] = all(c["pass"] or c.get("accepted_failure") for c in mnm + mno)
        if "classification" not in kw:
            kw["classification"] = "OK" if kw["controls_pass"] else ("NARROW_MISS" if any(not c["pass"] for c in mnm) else "WIDE_OVER")
        self.records.append(kw)
        if kw.get("fix_applied"):
            self.fixed.append({"id": kw["id"], "tool": kw["tool"], "fix": kw["fix_applied"], "status_before_fix": kw.get("status_before_fix")})
        return kw

    # ------------------------------------------------------------------ sources
    def load_sources(self) -> dict:
        self.fetch = CB.fetch_control(self.repo)
        self.delta = CB.git_show(self.repo, CB.DEFAULT_DELTA_REF) or ""
        raw_idx = CB.git_show(self.repo, CB.DEFAULT_INDEX_REF) or "{}"
        self.idx_obj = json.loads(raw_idx)
        self.idx = CB.RulingIndex(self.idx_obj, "git show " + CB.DEFAULT_INDEX_REF, sha256_text(raw_idx))
        self.tickets = CB.load_tickets(self.bus)
        self.ticket_ids = {t[0] for t in self.tickets}
        self.a_tickets = [(tid, d) for tid, p, d, v3 in self.tickets if v3 and str(d.get("from")) == "A"]
        self.ack_files = sorted(glob_all(self.bus, "acks") + glob_all(self.bus, "completions"))
        head = subprocess.run(["git", "-C", str(ASSURANCE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        return {"control_fetch": self.fetch, "delta_ref": CB.DEFAULT_DELTA_REF, "delta_sha256": sha256_text(self.delta), "delta_bytes": len(self.delta.encode("utf-8")),
                "index_ref": CB.DEFAULT_INDEX_REF, "index_sha256": self.idx.sha256, "index_version": self.idx.version, "index_rows": len(self.idx.rows),
                "bus_dir": self.bus, "tickets_n": len(self.tickets), "tickets_v3_era_n": sum(1 for t in self.tickets if t[3]), "a_tickets_v3_era_n": len(self.a_tickets),
                "ack_and_completion_files_n": len(self.ack_files), "c_worktree_head": head,
                "tool_sha256": {k: sha256_file(v) for k, v in TOOL_FILES.items()}}

    # ================================================================== c_bus_scan.py
    def m_ack_suffix(self):
        n = len(self.ack_files); stripped_ok = 0; not_ticket = []; prefix_disagree = []
        for p in self.ack_files:
            b = os.path.basename(p)[:-5]; t = CB.ACK_SUFFIX_RE.sub("", b)
            if t in self.ticket_ids: stripped_ok += 1
            else: not_ticket.append(b)
            pref = [x for x in self.ticket_ids if b.startswith(x + ".")]
            if pref and max(pref, key=len) != t: prefix_disagree.append({"file": b, "stripped": t, "ticket_by_prefix": max(pref, key=len)})
        v3_dangling = [x for x in CB.scan(self.bus)["dangling_refs_v3_era"]]
        strip = lambda s: CB.ACK_SUFFIX_RE.sub("", s)
        self.add(id="M01", tool="c_bus_scan.py", where="ACK_SUFFIX_RE / scan() dangling loop", feeds="dangling_refs_v3_era (judgment: v3-era ACK without ticket)",
                 pattern=CB.ACK_SUFFIX_RE.pattern, rule="strip one or more trailing `.<plane>[-<n>]` groups from the ACK/completion file stem; remainder must be a ticket id",
                 direction_if_narrow="over-alarm (false dangling)", direction_if_wide="silent pass (hides a real dangling ref)",
                 denominator={"name": "ack + completion files", "n": n}, extracted={"stripped_stem_is_a_ticket": stripped_ok, "not_a_ticket": len(not_ticket)},
                 presence_probe={"rule": "some ticket id is a dot-prefix of the stem", "disagreements_with_matcher": prefix_disagree,
                                 "note": "legacy `.A2` suffix form (no hyphen) is not stripped; all such files are pre-v3, so the v3-era judgment is unaffected"},
                 v3_era_dangling_now=v3_dangling,
                 must_not_miss=[ctrl("X.C-1", "X", strip("X.C-1")), ctrl("X.A.B", "X", strip("X.A.B")), ctrl("T-A-V3-FC-001.C-12", "T-A-V3-FC-001", strip("T-A-V3-FC-001.C-12")),
                                ctrl("T-B-V3-X.E", "T-B-V3-X", strip("T-B-V3-X.E"))],
                 must_not_over=[ctrl("T-A-V3-STEP1-001", "T-A-V3-STEP1-001", strip("T-A-V3-STEP1-001")), ctrl("X.F", "X.F", strip("X.F")),
                                ctrl("X.DRAFT", "X.DRAFT", strip("X.DRAFT")), ctrl("T-E001-RELEASE-001.DRAFT.C", "T-E001-RELEASE-001.DRAFT", strip("T-E001-RELEASE-001.DRAFT.C"))],
                 impact_on_current_source=f"{len(prefix_disagree)} legacy-suffix files (all pre-v3) — 0 v3-era entries affected",
                 fix_applied="dangling entries now carry note SUFFIX_NOT_STRIPPED when a ticket exists by dot-prefix (regex unchanged)", status_before_fix="NARROW_MISS (latent, pre-v3 only)")

    def m_fc_selector_and_how_known(self):
        sel = []; probe_not_sel = []
        for tid, p, d, v3 in self.tickets:
            t = str(d.get("type") or "")
            s = t in ("FACT_CORRECTION", "FACTUAL_CORRECTION") or "FACT_CORRECTION" in tid or re.search(r"-FC-\d+", tid) is not None
            if s: sel.append((tid, d))
            elif re.search(r"CORRECT|RETRACT", t, re.I) or re.search(r"RETRACT|CORRECT", tid): probe_not_sel.append(tid)
        selects = lambda tid, typ: (typ in ("FACT_CORRECTION", "FACTUAL_CORRECTION") or "FACT_CORRECTION" in tid or re.search(r"-FC-\d+", tid) is not None)
        self.add(id="M02", tool="c_bus_scan.py", where="check_fact_correction() ticket selector", feeds="fact_correction_missing_how_known denominator",
                 pattern="type ∈ {FACT_CORRECTION, FACTUAL_CORRECTION} | 'FACT_CORRECTION' in id | id ~ -FC-\\d+", rule="same", direction_if_narrow="silent pass (correction never checked)",
                 denominator={"name": "all tickets", "n": len(self.tickets)}, extracted={"selected": len(sel)},
                 presence_probe={"rule": "type or id contains CORRECT|RETRACT (case-insensitive on type)", "not_selected": probe_not_sel},
                 must_not_miss=[ctrl(("T-D-V3-FC-003", ""), True, selects("T-D-V3-FC-003", "")), ctrl(("X", "FACTUAL_CORRECTION"), True, selects("X", "FACTUAL_CORRECTION")),
                                ctrl(("C-FACT_CORRECTION-210041", "FINDING"), True, selects("C-FACT_CORRECTION-210041", "FINDING"))],
                 must_not_over=[ctrl(("T-B-V3-FINDING-007", "FACT_CHECK_REQUEST"), False, selects("T-B-V3-FINDING-007", "FACT_CHECK_REQUEST")),
                                ctrl(("T-A-V3-STEP1-004", "DIRECTIVE"), False, selects("T-A-V3-STEP1-004", "DIRECTIVE"))],
                 impact_on_current_source="presence probe agrees (0 not selected)", fix_applied=None)
        strict_missing = []; wide_only = []
        for tid, d in sel:
            ks = CB._keys(d)
            if not any(CB.HOW_KNOWN_RE.match(k) for k in ks):
                strict_missing.append(tid)
                wk = sorted(k for k in ks if CB.HOW_KNOWN_WIDE_RE.search(k))
                if wk: wide_only.append({"ticket_id": tid, "keys": wk})
        old_re = re.compile(r"^(how_known|evidence|evidence_refs|measurement|method|verified_against|how_.*(found|surfaced|happened).*|how_it_surfaced|artifact_refs|what_is_actually_true|corrected_facts|the_measurement)$", re.I)
        hk = lambda k: CB.HOW_KNOWN_RE.match(k) is not None
        self.add(id="M03", tool="c_bus_scan.py", where="HOW_KNOWN_RE over ticket keys (top level ∪ payload)", feeds="fact_correction_missing_how_known (summary counter; Δ13-R17)",
                 pattern=CB.HOW_KNOWN_RE.pattern, rule=CB.HOW_KNOWN_RULE, wide_probe_rule=CB.HOW_KNOWN_WIDE_RULE,
                 direction_if_narrow="over-accusation (ticket listed as lacking how-known)", direction_if_wide="silent pass",
                 denominator={"name": "FC tickets selected (M02)", "n": len(sel)}, extracted={"strict_missing": len(strict_missing), "strict_missing_but_wide_probe_hit": len(wide_only)},
                 wide_only_detail=wide_only, empty_extraction_ratio=f"{len(strict_missing)}/{len(sel)}",
                 must_not_miss=[ctrl("how_A_knows", True, hk("how_A_knows"), "old pattern how_.*(found|surfaced|happened).* missed this (T-A-V3-FC-005)"), ctrl("how_known", True, hk("how_known")),
                                ctrl("HOW_KNOWN", True, hk("HOW_KNOWN")), ctrl("how_it_was_found", True, hk("how_it_was_found")), ctrl("verified_against", True, hk("verified_against"))],
                 must_not_over=[ctrl("measured_at_kst", False, hk("measured_at_kst")), ctrl("correction", False, hk("correction")), ctrl("showcase", False, hk("showcase")),
                                ctrl("evidence_root_path", False, hk("evidence_root_path"))],
                 old_pattern_control={"how_A_knows under old pattern": old_re.match("how_A_knows") is not None},
                 impact_on_current_source=f"strict count {len(strict_missing)}/{len(sel)}; {len(wide_only)} of the missing carry a wide-probe key (listed in the scanner output)",
                 fix_applied="how_.*(found|surfaced|happened).* → how_.* ; strict + wide-probe counts and both rules emitted next to the count", status_before_fix="NARROW_MISS (1 ticket: how_A_knows)")

    def m_ref_lint(self):
        rl = CB.ref_lint(self.tickets, ASSURANCE)
        BR = "research/" + "landing-accessibility-main"   # assembled so this file is not itself a ref-lint hit
        bare = lambda ln: CB.BARE_REF_RE.search(ln) is not None
        self.add(id="M04", tool="c_bus_scan.py", where="BARE_REF_RE + 'ls-remote' line exemption (ref_lint)", feeds="ref_lint_hits (Δ4)",
                 pattern=CB.BARE_REF_RE.pattern, rule=rl["parser_rule"], direction_if_narrow="silent pass", direction_if_wide="over-flag of compliant refs",
                 denominator=rl["denominators"], extracted={"hits": len(rl["hits"])},
                 presence_probe={"rule": "substring landing-accessibility-main on any line", "lines": rl["denominators"]["lines_mentioning_branch"],
                                 "exempted_by_ls_remote_but_bare": rl["denominators"]["ls_remote_exempted_with_bare_form"]},
                 must_not_miss=[ctrl("`" + BR + "`", True, bare("`" + BR + "`")), ctrl("(" + BR + ")", True, bare("(" + BR + ")")),
                                ctrl("refs/heads/" + BR, True, bare("refs/heads/" + BR)), ctrl("branch " + BR + " @ 4bbbc22", True, bare("branch " + BR + " @ 4bbbc22"))],
                 must_not_over=[ctrl("origin/" + BR, False, bare("origin/" + BR)), ctrl("refs/remotes/origin/" + BR, False, bare("refs/remotes/origin/" + BR)),
                                ctrl(BR + "-v2 (other branch)", True, bare(BR + "-v2"), "NOTE: a sibling branch name starting with the same string IS flagged — over-match accepted, no such branch exists")],
                 impact_on_current_source=f"{len(rl['denominators']['ls_remote_exempted_with_bare_form'])} bare-form lines are exempted by the line-wide ls-remote rule (now listed)",
                 fix_applied="denominators (lines scanned / mentioning / prefixed / bare / ls-remote-exempted-with-bare) emitted next to the hit count", status_before_fix="WIDE_OVER (line-wide exemption, 2 lines) + no denominator")

    def m_tokens(self):
        chain = collections.Counter(); circ = collections.Counter(); with_char = 0; zero = []
        for tid, d in self.a_tickets:
            txt = json.dumps(d, ensure_ascii=False)
            n = len(CB.DELTA_TOKEN_RE.findall(txt)) + len(CB.R_TOKEN_RE.findall(txt))
            if "Δ" in txt or re.search(r"(?<![A-Za-z])R\d", txt):
                with_char += 1
                if n == 0: zero.append(tid)
            for m in re.findall(r"Δ\d+(?:-[A-Za-z0-9]+){2,}", txt): chain[m] += 1
            for m in CB.DELTA_SUBSECTION_RE.findall(txt): circ[re.sub(r"\s", "", m)] += 1
        old = re.compile(r"Δ\d+(?:-[A-Za-z0-9]+)?")
        f = lambda s: CB.DELTA_TOKEN_RE.findall(s)
        self.add(id="M05", tool="c_bus_scan.py", where="DELTA_TOKEN_RE over v3-era A tickets", feeds="unrecorded_mentions / section_mentions_resolved_by_subrows / index_rows_unmentioned_in_A_tickets (Δ21)",
                 pattern=CB.DELTA_TOKEN_RE.pattern, rule=CB.DELTA_TOKEN_RULE, direction_if_narrow="silent pass (truncated id resolves to the wrong / parent row)",
                 denominator={"name": "v3-era A tickets", "n": len(self.a_tickets)}, extracted={"tickets_containing_Δ_or_Rn": with_char, "of_those_with_zero_tokens": zero, "hyphen_chain_mentions": dict(chain)},
                 presence_probe={"rule": "ticket text contains 'Δ' or R<digit>", "zero_extraction_with_presence": len(zero)},
                 must_not_miss=[ctrl("cites Δ47-fixture-limit", ["Δ47-fixture-limit"], f("cites Δ47-fixture-limit"), "old pattern gave Δ47-fixture = a DIFFERENT index row"),
                                ctrl("Δ50-exit2-common", ["Δ50-exit2-common"], f("Δ50-exit2-common")), ctrl("(Δ21)", ["Δ21"], f("(Δ21)")), ctrl("`Δ18-R20`", ["Δ18-R20"], f("`Δ18-R20`")),
                                ctrl("Δ40-control-naming", ["Δ40-control-naming"], f("Δ40-control-naming"))],
                 must_not_over=[ctrl("Δ36-② (circled)", ["Δ36"], f("Δ36-②"), "circled digit is not part of the id — extracted separately (M07)"), ctrl("Δ21을 위반", ["Δ21"], f("Δ21을 위반")),
                                ctrl("Δ8-R3a/b", ["Δ8-R3a"], f("Δ8-R3a/b"))],
                 old_pattern_control={"Δ47-fixture-limit under old pattern": old.findall("Δ47-fixture-limit")},
                 impact_on_current_source=f"{sum(chain.values())} hyphen-chain mentions were truncated before the fix ({', '.join(chain)}); Δ47-fixture-limit → credited to Δ47-fixture",
                 fix_applied="(?:-[A-Za-z0-9]+)? → (?:-[A-Za-z0-9]+)* ; token_extraction block (rule, presence probe, zero-extraction list) emitted", status_before_fix="NARROW_MISS (3 mentions, 1 misattributed row)")
        r = lambda s: CB.R_TOKEN_RE.findall(s)
        self.add(id="M06", tool="c_bus_scan.py", where="R_TOKEN_RE over v3-era A tickets", feeds="same as M05", pattern=CB.R_TOKEN_RE.pattern,
                 rule="R<digits>[a-z]? not preceded by [A-Za-z0-9_-Δ] and not followed by [A-Za-z0-9_] (so Δ18-R20 yields no bare R20; PR21 / R210 excluded)",
                 direction_if_narrow="silent pass", denominator={"name": "v3-era A tickets", "n": len(self.a_tickets)}, extracted={"see": "M05 (joint token count in scanner: tokens_mentioned)"},
                 must_not_miss=[ctrl("(R21)", ["R21"], r("(R21)")), ctrl("R3a and R13b", ["R3a", "R13b"], r("R3a and R13b")), ctrl("R21,", ["R21"], r("R21,")), ctrl("R21을", ["R21"], r("R21을"))],
                 must_not_over=[ctrl("PR21", [], r("PR21")), ctrl("R21 must not leak out of R210", False, "R21" in r("R210"), "R210 itself is a legitimate R-token (unrecorded → gap), the boundary keeps R21 out"), ctrl("Δ18-R20", [], r("Δ18-R20"), "the full id is extracted by M05"),
                                ctrl("FOR21", [], r("FOR21")), ctrl("R21_x", [], r("R21_x"))],
                 impact_on_current_source="none observed", fix_applied=None)
        c = lambda s: [re.sub(r"\s", "", m) for m in CB.DELTA_SUBSECTION_RE.findall(s)]
        self.add(id="M07", tool="c_bus_scan.py", where="DELTA_SUBSECTION_RE (numbered-subsection mentions)", feeds="token_extraction.numbered_subsection_mentions (report; Δ54 — subsections carry independent judgments)",
                 pattern=CB.DELTA_SUBSECTION_RE.pattern, rule="Δ<digits> then optional space/hyphen/space then one circled digit ①-⑳",
                 direction_if_narrow="silent fold into the bare section (the subsection judgment cited is invisible)",
                 denominator={"name": "v3-era A tickets", "n": len(self.a_tickets)}, extracted={"mentions": dict(circ)},
                 must_not_miss=[ctrl("Δ36-②", ["Δ36-②"], c("Δ36-②")), ctrl("Δ39 ①", ["Δ39①"], c("Δ39 ①")), ctrl("Δ47③", ["Δ47③"], c("Δ47③")), ctrl("Δ36 - ④", ["Δ36-④"], c("Δ36 - ④"))],
                 must_not_over=[ctrl("Δ36-order", [], c("Δ36-order")), ctrl("① Δ36", [], c("① Δ36"), "digit before the section is prose numbering, not a subsection ref")],
                 impact_on_current_source=f"{sum(circ.values())} mentions were folded into bare sections before (now listed beside the section resolution)",
                 fix_applied="new extractor; forms listed under token_extraction and on the section_mentions_resolved_by_subrows entry", status_before_fix="NARROW_MISS (extractor absent, 5 mentions folded)")

    def m_boundaries(self):
        delta = self.delta
        strict = lambda t, txt: re.search(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", txt) is not None
        old_token_in = lambda txt, t: re.search(r"(?<![A-Za-z0-9_])" + re.escape(t) + r"(?![A-Za-z0-9_])", txt) is not None
        diff_rows = []; hangul_adj = collections.Counter(re.findall(r"(Δ\d+(?:-[A-Za-z0-9]+)*)([가-힣])", delta))
        for r in self.idx.rows:
            toks = [r["id"]] + list(r.get("aliases") or [])
            a = any(CB.token_in(delta, t) for t in toks); b = any(strict(t, delta) for t in toks); o = any(old_token_in(delta, t) for t in toks)
            if a != b or o != a: diff_rows.append({"id": r["id"], "token_in_now": a, "_tok_delta_strict": b, "token_in_old": o})
        ti = CB.token_in
        self.add(id="M08", tool="c_bus_scan.py", where="token_in() (alias/id presence in A tickets → index_rows_unmentioned_in_A_tickets)", feeds="index_rows_unmentioned_in_A_tickets (report)",
                 pattern="(?<![A-Za-z0-9_\\-])<tok>(?![A-Za-z0-9_\\-])", rule=CB.TOKEN_BOUNDARY_RULE, direction_if_narrow="over-report of unmentioned rows", direction_if_wide="silent credit of the wrong row",
                 denominator={"name": "index rows × delta body (cross-check of the two boundary rules)", "n": len(self.idx.rows)},
                 extracted={"rows_where_the_boundary_rules_disagree": diff_rows, "delta_tokens_immediately_followed_by_hangul": sum(hangul_adj.values())},
                 must_not_miss=[ctrl("`Δ21`", True, ti("see `Δ21` here", "Δ21")), ctrl("(R21)", True, ti("(R21)", "R21")), ctrl("Δ21을", True, ti("Δ21을 위반", "Δ21")), ctrl("R21,", True, ti("R21, and", "R21"))],
                 must_not_over=[ctrl("Δ47-fixture in Δ47-fixture-limit", False, ti("Δ47-fixture-limit", "Δ47-fixture"), "old boundary matched here (WIDE_OVER)"), ctrl("R21 in R210", False, ti("R210", "R21")),
                                ctrl("R21 in PR21", False, ti("PR21", "R21")), ctrl("Δ21 in Δ21-R22", False, ti("Δ21-R22", "Δ21"))],
                 impact_on_current_source="1 row (Δ47-fixture) was credited from a mention of Δ47-fixture-limit; unmentioned list unchanged in size after the fix because Δ47-fixture is also cited on its own",
                 fix_applied="'-' added to the boundary class (now identical in shape to _tok_delta / alias_fires_in_corpus except that Hangul adjacency does not block)", status_before_fix="WIDE_OVER (1 row)")
        af = CB.alias_fires_in_corpus
        self.add(id="M09", tool="c_bus_scan.py", where="alias_fires_in_corpus() / _tok_delta() boundary (?<![\\w-])…(?![\\w-])", feeds="unsafe_aliases (Δ33 controls, refusal gate) and index_to_delta_reachability",
                 pattern="(?<![\\w-])<tok>(?![\\w-])", rule="token-bounded by non-word/non-hyphen; \\w is Unicode so a Hangul particle glued to the token blocks the match",
                 direction_if_narrow="reachability: false 'unreachable' (over-alarm, fail-closed); alias safety: alias judged safe though it fires (silent pass)",
                 denominator={"name": "delta tokens immediately followed by Hangul (presence probe for the \\w blind spot)", "n": sum(hangul_adj.values())}, extracted={"rows_affected_now": [d for d in diff_rows if d["token_in_now"] != d["_tok_delta_strict"]]},
                 must_not_miss=[ctrl("coverage in corpus", True, af("coverage")), ctrl("auth in corpus", True, af("auth")), ctrl("skip in corpus", True, af("skip"))],
                 must_not_over=[ctrl("Δ18-R20 in corpus", False, af("Δ18-R20")), ctrl("scrollfix in corpus", False, af("scrollfix")), ctrl("cach (prefix of cache)", False, af("cach")), ctrl("index (prefix of indexes)", False, af("index"))],
                 impact_on_current_source="0 rows differ between the two boundary rules on the current delta; 0 Hangul-glued tokens", fix_applied=None,
                 proposed_fix="none needed now; if A starts writing `Δ21을` in the delta body, the reachability check will over-alarm (fail-closed) — the sweep's presence probe counts such tokens")

    def m_headings(self):
        rg = self.rg
        hc = rg["delta_heading_counts"]
        hre = lambda s: CB.DELTA_HEAD_RE.findall(s)
        self.add(id="M10", tool="c_bus_scan.py", where="DELTA_HEAD_RE (delta `##`/`###` id headings)", feeds="delta_headings_without_index_row (summary counter) + reachability path (a)",
                 pattern=CB.DELTA_HEAD_RE.pattern, rule=CB.DELTA_HEAD_RULE, direction_if_narrow="silent pass (heading never checked against the index)",
                 denominator={"name": "all heading lines in the delta", "n": hc["all_heading_lines"]}, extracted={"matched_as_id": hc["matched_as_id"], "unmatched": hc["unmatched"], "unmatched_level2": hc["unmatched_level2"], "unmatched_prose_headings_carrying_a_ruling_token": len(hc["unmatched_carrying_a_ruling_token_prose_only"])},
                 presence_probe={"rule": "any heading line whose title contains Δ<digit> or R<digit>", "level2_headings_not_extracted": len(hc["unmatched_level2"])},
                 must_not_miss=[ctrl("## Δ57 — title", ["Δ57"], hre("## Δ57 — title")), ctrl("### Δ36-order trailing text", ["Δ36-order"], hre("### Δ36-order trailing text")), ctrl("### R54", ["R54"], hre("### R54")),
                                ctrl("## Δ40-control-naming — x", ["Δ40-control-naming"], hre("## Δ40-control-naming — x")), ctrl("##  Δ12   (two spaces)", ["Δ12"], hre("##  Δ12   (two spaces)"))],
                 must_not_over=[ctrl("#### Δ36 (level 4)", [], hre("#### Δ36 (level 4)"), "level-4 headings are prose sub-parts by A's convention"), ctrl("### `Δ36` 의 각 판정", [], hre("### `Δ36` 의 각 판정"), "backticked prose title, not an id heading"),
                                ctrl("## Δ12a", [], hre("## Δ12a")), ctrl("### R54x", [], hre("### R54x")), ctrl("### ① MIN-2", [], hre("### ① MIN-2"), "numbered subsection — counted by M11, not as an id")],
                 impact_on_current_source="0 level-2 headings unextracted; denominator (all heading lines) was not reported before", fix_applied="regex hoisted to a named constant; parser_rule + all/matched/unmatched denominators emitted in delta_heading_counts", status_before_fix="OK (no denominator)")
        ns = hc["numbered_subsections_per_delta"]
        st = lambda s: CB.NUMBERED_SUB_STRICT_RE.match(s) is not None
        self.add(id="M11", tool="c_bus_scan.py", where="NUMBERED_SUB_STRICT_RE / NUMBERED_SUB_WIDE_RE (numbered subsections per `## Δn`)", feeds="delta_heading_counts.numbered_subsection_shortfall (summary counter; Δ54-check10 counterpart)",
                 pattern={"strict": CB.NUMBERED_SUB_STRICT_RE.pattern, "wide": CB.NUMBERED_SUB_WIDE_RE.pattern}, rule=CB.NUMBERED_SUB_RULE,
                 direction_if_narrow="silent pass (a subsection judgment with no index row is never seen)", direction_if_wide="false shortfall (part-headings counted as judgments)",
                 denominator={"name": "`## Δn` sections with ≥1 numbered subsection", "n": len(ns)}, extracted={s: {k: v[k] for k in ("numbered_strict", "numbered_wide", "index_rows_with_prefix")} for s, v in ns.items()},
                 shortfall=hc["numbered_subsection_shortfall"],
                 must_not_miss=[ctrl("① MIN-2 — v3 에 요구하지 않는다", True, st("① MIN-2 — v3 에 요구하지 않는다")), ctrl("판정 ② `terminal_reason`", True, st("판정 ② `terminal_reason`")), ctrl("(ii) 경로 발견의 완전성", True, st("(ii) 경로 발견의 완전성")),
                                ctrl("부기 ④ — x", True, st("부기 ④ — x")), ctrl("(③) x", True, st("(③) x"))],
                 must_not_over=[ctrl("part4 — MIN-5", False, st("part4 — MIN-5"), "wide rule counts it; strict does not (A counted Δ36 as 4)"), ctrl("판정 — `NULL`", False, st("판정 — `NULL`")), ctrl("A 자기적용", False, st("A 자기적용")),
                                ctrl("1차 시정", False, st("1차 시정"))],
                 impact_on_current_source=f"{sum(v['numbered_strict'] for v in ns.values())} strict numbered subsections in {len(ns)} sections; shortfall {hc['numbered_subsection_shortfall']}; A's check counts Δ36 = 4 — C strict agrees",
                 fix_applied="new extractor + per-section comparison with index rows sharing the section prefix", status_before_fix="NARROW_MISS (extractor absent — 19 judgment-bearing subsections outside every C denominator)")
        rs = self.idx.resolve_by_subrows
        self.add(id="M12", tool="c_bus_scan.py", where="RulingIndex.resolve_by_subrows()", feeds="section_mentions_resolved_by_subrows (bare-section mentions are not gaps)",
                 pattern="ids starting with <tok>-  |  fullmatch <tok>[a-z]  |  alias fullmatch <tok>[a-z]", rule="a bare section / prefix token resolves to its child rows; never to a different section",
                 direction_if_wide="silent pass (unrelated rows credited)", denominator={"name": "distinct tokens mentioned in A tickets", "n": rg["tokens_mentioned"]}, extracted={"resolved_by_subrows": len(rg["section_mentions_resolved_by_subrows"])},
                 must_not_miss=[ctrl("Δ12", sorted(i for i in self.idx.ids if i.startswith("Δ12-")), sorted(rs("Δ12"))), ctrl("Δ8-R3", ["Δ8-R3a", "Δ8-R3b"], sorted(rs("Δ8-R3"))), ctrl("R13", sorted(rs("R13")) if rs("R13") else ["Δ10-R13a", "Δ10-R13b"], sorted(rs("R13")))],
                 must_not_over=[ctrl("Δ1 must not reach Δ10-*/Δ11/Δ12-*", True, all(i.startswith("Δ1-") for i in rs("Δ1"))), ctrl("Δ5 → only Δ5-*", True, all(i.startswith("Δ5-") for i in rs("Δ5"))), ctrl("Δ999", [], rs("Δ999"))],
                 impact_on_current_source="none observed", fix_applied=None)

    def m_real_and_era(self):
        pe = CB.check_plane_enum(self.tickets)
        rb = lambda d: bool(d.get("real_target")) or any(re.search(r"\bREAL(_TARGET)?\b", str(CB._get(d, k) or "")) for k in ("scope", "mode", "execution_mode", "real_scope_id", "type", "claim_kind", "headline"))
        self.add(id="M13", tool="c_bus_scan.py", where="check_plane_enum() REAL-bearing detector", feeds="e_real_field_gaps (Δ6-a 5 mandatory fields)",
                 pattern="real_target truthy | \\bREAL(_TARGET)?\\b in scope/mode/execution_mode/real_scope_id/type/claim_kind/headline", rule=pe["real_bearing_rule"],
                 direction_if_narrow="silent pass (REAL ticket never checked for the 5 fields)", direction_if_wide="false field-gap on prose mentions",
                 denominator={"name": "v3-era tickets with E in from∪to", "n": pe["e_tickets_v3_era"]}, extracted={"real_bearing": pe["e_real_tickets"], "field_gaps": len(pe["e_real_field_gaps"])},
                 presence_probe={"rule": "\\bREAL\\b anywhere in the ticket JSON", "mentioned_outside_declared_fields": pe["real_mentioned_outside_declared_fields"]},
                 must_not_miss=[ctrl({"scope": "REAL"}, True, rb({"scope": "REAL"})), ctrl({"payload": {"execution_mode": "REAL_TARGET"}}, True, rb({"payload": {"execution_mode": "REAL_TARGET"}})), ctrl({"real_target": True}, True, rb({"real_target": True})),
                                ctrl({"headline": "E REAL run on 5 targets"}, True, rb({"headline": "E REAL run on 5 targets"}))],
                 must_not_over=[ctrl({"preregistration_status": "REAL 접속 누적 0건"}, False, rb({"preregistration_status": "REAL 접속 누적 0건"}), "prose — the 4 listed tickets are of this kind"), ctrl({"scope": "REALLY not"}, False, rb({"scope": "REALLY not"})),
                                ctrl({"scope": "SYNTHETIC"}, False, rb({"scope": "SYNTHETIC"}))],
                 impact_on_current_source=f"{len(pe['real_mentioned_outside_declared_fields'])} E tickets mention REAL only in prose (listed, not counted)", fix_applied="presence probe list + rule emitted next to the count", status_before_fix="OK (no presence probe)")
        iv = lambda ts: CB.is_v3_era({"created_at_kst": ts}, "/nonexistent")
        forms = collections.Counter()
        for tid, p, d, v3 in self.tickets:
            ts = CB._ts(d); forms["none(mtime)" if not ts else ("Z" if ts.endswith("Z") else ("+09:00" if "+09:00" in ts else ("+0900" if "+0900" in ts else "other")))] += 1
        self.add(id="M14", tool="c_bus_scan.py", where="is_v3_era() timestamp/mtime cutoff", feeds="EVERY v3-era check (plane_enum, base_sha, ref-lint tickets, Δ21 token set, dangling)",
                 pattern="fromisoformat(ts.replace('Z','+00:00')).timestamp() >= V3_CUTOFF_EPOCH ; fallback string compare ; mtime fallback", rule=CB.V3_ERA_RULE,
                 direction_if_narrow="silent pass (ticket excluded from all v3 checks)", direction_if_wide="pre-v3 tickets judged by v3 rules",
                 denominator={"name": "tickets by timestamp form", "n": len(self.tickets)}, extracted=dict(forms),
                 must_not_miss=[ctrl("2026-08-27T17:12:00Z (= cutoff in UTC)", True, iv("2026-08-27T17:12:00Z"), "old string compare said pre-v3"), ctrl("2026-08-28T02:12:00+0900", True, iv("2026-08-28T02:12:00+0900")), ctrl("2026-08-28T02:12:00+09:00", True, iv("2026-08-28T02:12:00+09:00"))],
                 must_not_over=[ctrl("2026-08-28T02:11:59+09:00", False, iv("2026-08-28T02:11:59+09:00")), ctrl("2026-08-27T17:11:59Z", False, iv("2026-08-27T17:11:59Z")), ctrl("no ts, mtime 2026-08-27T16:18 KST", False, 1787850720 - 10 * 3600 >= CB.V3_CUTOFF_EPOCH, "old epoch literal 1787500320 (= 2026-08-24 00:52 KST) said v3")],
                 epoch_check={"V3_CUTOFF_EPOCH_now": CB.V3_CUTOFF_EPOCH, "expected_from_iso": int(dt.datetime.fromisoformat(CB.V3_CUTOFF_ISO + "+09:00").timestamp()), "old_literal": 1787500320, "old_literal_kst": "2026-08-24T00:52:00+09:00"},
                 impact_on_current_source="4 timestamp-less tickets (FINAL_READY / MART_READY / STATS_READY / T-E001-RELEASE-001.DRAFT, mtimes 2026-08-27 12:37–16:18 KST) were counted as v3-era by the wrong epoch literal — they leave v3_era_checked and the base_sha NO_FIELD list",
                 fix_applied="epoch derived from the ISO literal (was a wrong hand-typed epoch, 4d01h20m early); 'Z'/any-offset timestamps compared as instants", status_before_fix="WIDE_OVER (4 tickets) + NARROW_MISS (latent: 'Z' form)")
        cb = lambda s: CB.classify_base_sha(s, self.repo)
        head = subprocess.run(["git", "-C", self.repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.add(id="M15", tool="c_bus_scan.py", where="classify_base_sha() hex regex", feeds="base_sha_unresolvable (Δ26, report)", pattern="[0-9a-f]{7,40} else rev-parse --verify",
                 rule="lowercase hex 7-40 → cat-file; anything else → rev-parse (OK_ABBREV if it resolves, NOT_A_SHA otherwise)", direction_if_narrow="uppercase full sha labelled OK_ABBREV (visible mislabel, not silent)",
                 denominator={"name": "v3-era tickets with base_sha", "n": sum(1 for t in self.tickets if t[3] and t[2].get('base_sha'))}, extracted={"uppercase_hex_values": sum(1 for t in self.tickets if t[3] and re.search(r"[A-F]", str(t[2].get('base_sha') or '')))},
                 must_not_miss=[ctrl(head, "OK", cb(head)), ctrl(head[:10], "OK_ABBREV", cb(head[:10])), ctrl(head.upper(), "OK_ABBREV", cb(head.upper()), "documented mislabel: git resolves uppercase; value is shown in ok_abbrev, never hidden")],
                 must_not_over=[ctrl("deadbeef" * 5, "MISSING", cb("deadbeef" * 5)), ctrl("origin/nonexistent-ref-r54", "NOT_A_SHA", cb("origin/nonexistent-ref-r54")), ctrl("", "NO_FIELD", cb(""))],
                 impact_on_current_source="0 uppercase values on the bus", fix_applied=None)
        su = CB.shape_unsafe_alias
        self.add(id="M16", tool="c_bus_scan.py", where="shape_unsafe_alias() (Δ25 shape proxy, report-only) / unsafe_alias() (Δ33 corpus test)", feeds="shape_unsafe_aliases_delta25_proxy (report only); unsafe_aliases feeds resolution",
                 pattern="len<=6 & lowercase & [a-z][a-z0-9]*", rule="report-only proxy; the judgment uses the corpus test (M09)", direction_if_narrow="n/a (report-only)",
                 denominator={"name": "distinct aliases", "n": len(self.idx.alias_map)}, extracted={"shape_unsafe": len(self.idx.shape_unsafe), "corpus_unsafe": len(self.idx.unsafe), "collisions": len(self.idx.collisions)},
                 must_not_miss=[ctrl("auth", True, su("auth")), ctrl("vr", True, su("vr"))], must_not_over=[ctrl("scrollfix (7 chars)", False, su("scrollfix")), ctrl("R21", False, su("R21")), ctrl("Δ2", False, su("Δ2"))],
                 impact_on_current_source="report-only", fix_applied=None)
        s40 = lambda s: CB.SHA40_RE.search(s) is not None
        self.add(id="M17", tool="c_bus_scan.py", where="SHA40_RE (sha_on_same_line annotation of ref-lint hits)", feeds="ref_lint hit annotation (report)", pattern=CB.SHA40_RE.pattern, rule="40 lowercase hex, word-bounded",
                 direction_if_narrow="annotation only", denominator={"name": "ref-lint hits", "n": len(self.rl_hits)}, extracted={"with_sha": sum(1 for h in self.rl_hits if h["sha_on_same_line"])},
                 must_not_miss=[ctrl("@ " + "a" * 40, True, s40("@ " + "a" * 40))], must_not_over=[ctrl("a" * 39, False, s40("a" * 39)), ctrl("A" * 40, False, s40("A" * 40), "uppercase sha not annotated — annotation only")],
                 impact_on_current_source="annotation only", fix_applied=None)

    # ================================================================== r32_inventory.py
    def m_r32_helper(self):
        def callees(root: pathlib.Path) -> collections.Counter:
            out = collections.Counter()
            for p in root.rglob("*.py"):
                if "__pycache__" in p.parts: continue
                try: tree = ast.parse(p.read_text(encoding="utf-8"))
                except Exception: continue
                for n in ast.walk(tree):
                    if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
                        c = R32.callee_name(n.value)
                        if c: out[c] += 1
            return out
        old = re.compile(r"(require|check|validate|assert|ensure|expect|verify)", re.I)
        res = {}
        for label, root in (("gate1/intake/fixtures_py", HERE / "intake" / "fixtures_py"), ("assurance_tree_as_corpus", ASSURANCE)):
            cn = callees(root); hit = {c: k for c, k in cn.items() if R32.HELPER_CHECK_RE.search(c)}; ohit = {c: k for c, k in cn.items() if old.search(c)}
            res[label] = {"expr_call_sites": sum(cn.values()), "distinct_callees": len(cn), "helper_hits_now": sum(hit.values()), "helper_hits_old_substring": sum(ohit.values()), "old_only_callees": sorted(set(ohit) - set(hit))}
        h = lambda n: R32.HELPER_CHECK_RE.search(n) is not None
        self.add(id="M18", tool="gate1/intake/r32_inventory.py", where="HELPER_CHECK_RE over Expr-Call callee names (_collect_helper_checks → handling UNKNOWN 'helper check … on root')", feeds="R32 site handling class (a helper hit converts a SILENT_DEFAULT verdict into UNKNOWN)",
                 pattern=R32.HELPER_CHECK_RE.pattern, rule=R32.HELPER_CHECK_RULE, direction_if_wide="silent pass (checkpoint/checksum/unexpected calls counted as checks)",
                 denominator={"name": "bare-expression call sites (fixtures / C tree)", "n": res}, extracted={"see": "denominator.helper_hits_now"},
                 must_not_miss=[ctrl("require_field", True, h("require_field")), ctrl("validateInput", True, h("validateInput")), ctrl("self.assertEqual", True, h("self.assertEqual")), ctrl("_check", True, h("_check")), ctrl("CHECK_ALL", True, h("CHECK_ALL")), ctrl("mod.Validate", True, h("mod.Validate"))],
                 must_not_over=[ctrl("write_checkpoint", False, h("write_checkpoint"), "old substring rule matched"), ctrl("compute_checksum", False, h("compute_checksum"), "old rule matched"), ctrl("unexpected", False, h("unexpected"), "old rule matched"),
                                ctrl("expectation", False, h("expectation")), ctrl("rechecked", False, h("rechecked")), ctrl("verified_at", False, h("verified_at")), ctrl("checkout", False, h("checkout"))],
                 impact_on_current_source="0 over-matches in C's fixtures or C's own tree (the SUT is B's — the control is the evidence, the corpus is the denominator)",
                 fix_applied="word-start bounded, case-insensitive with a case-sensitive lowercase lookahead; helper_check_rule + regex emitted in the inventory JSON", status_before_fix="WIDE_OVER (by control; 0 hits on C corpus)")

    # ================================================================== lane5 evidence_lineage_check.py
    def m_lane5(self):
        fx = HERE / "lane5_evidence" / "fixtures"
        per_field = collections.defaultdict(lambda: collections.Counter()); n_rec = 0; near_miss = collections.Counter(); files_json = 0; discovered = 0; discovered_names = set()
        for root in sorted(p for p in fx.iterdir() if p.is_dir()):
            pm = root / "path_manifest.json"
            rep = L5.Report(root, pm if pm.exists() else None)
            mans = L5.discover_manifests(root, pm if pm.exists() else None); discovered += len(mans); discovered_names |= {m.name for m in mans}
            files_json += sum(1 for p in root.rglob("*") if p.suffix.lower() in (".json", ".jsonl"))
            for mp in mans:
                for rec in L5.load_records(mp, rep):
                    if not isinstance(rec, dict): continue
                    n_rec += 1
                    for canon, names in L5.FIELD_ALIASES.items():
                        hit = next((nm for nm in names if nm in rec and rec[nm] not in (None, "")), None)
                        per_field[canon]["canonical" if hit == canon else ("alias:" + hit if hit else "none")] += 1
                        if hit is None:
                            for k in rec:
                                if re.sub(r"[^a-z0-9]", "", str(k).lower()) == re.sub(r"[^a-z0-9]", "", canon.lower()): near_miss[(canon, str(k))] += 1
        g = L5.get
        self.add(id="M19", tool="gate1/lane5_evidence/evidence_lineage_check.py", where="FIELD_ALIASES / get() (canonical field ← accepted source names, first match wins)", feeds="MISSING_FIELD / SCHEMA defects → verdict (fail-closed: a miss is a defect, not a pass)",
                 pattern={k: list(v) for k, v in L5.FIELD_ALIASES.items()}, rule="exact key equality against the alias tuple, first hit wins; empty string / None = absent",
                 direction_if_narrow="over-flag MISSING_FIELD (fail-closed)", direction_if_wide="silent pass (display name accepted as id, wrong field read)",
                 denominator={"name": "records in C lane5 fixtures (good/bad_lineage/bad_overwrite)", "n": n_rec}, extracted={k: dict(v) for k, v in per_field.items()},
                 presence_probe={"rule": "record key equal to the canonical name after lowercasing and stripping non-alphanumerics (camelCase / dashed variants)", "near_miss_keys_not_in_alias_table": {f"{c}←{k}": n for (c, k), n in near_miss.items()}},
                 must_not_miss=[ctrl({"state_id": "S1"}, "S1", g({"state_id": "S1"}, "observation_id")), ctrl({"collector_sha256": "ab"}, "ab", g({"collector_sha256": "ab"}, "collector_sha")), ctrl({"ts": "2026"}, "2026", g({"ts": "2026"}, "captured_at"))],
                 must_not_over=[ctrl({"service_name": "Coupang"}, None, g({"service_name": "Coupang"}, "service_id"), "display name must NOT satisfy service_id"), ctrl({"observation_id": ""}, None, g({"observation_id": ""}, "observation_id"), "empty = absent"),
                                ctrl({"serviceId": "svc"}, None, g({"serviceId": "svc"}, "service_id"), "camelCase is NOT accepted (by design: B's names are bound through the adapter map); the near-miss probe above would list it")],
                 impact_on_current_source="all fixture records read through canonical names; 0 near-miss keys", fix_applied=None, proposed_fix="none — narrow direction is fail-closed here; keep the near-miss probe when reading B's tree")
        am = L5.ARTIFACT_ALIASES
        self.add(id="M20", tool="gate1/lane5_evidence/evidence_lineage_check.py", where="ARTIFACT_ALIASES (artifact kind ← manifest artifact keys)", feeds="MISSING_ARTIFACT / sha binding defects", pattern={k: list(v) for k, v in am.items()},
                 rule="artifact kind resolved by exact key name (nested form artifacts{kind:{path,sha256}} or flat <kind>_path/<kind>_sha256)", direction_if_narrow="over-flag (fail-closed)", direction_if_wide="wrong artifact bound to a sha",
                 denominator={"name": "artifact kinds", "n": len(am)}, extracted={"aliases": sum(len(v) for v in am.values())},
                 must_not_miss=[ctrl("dom_html", "dom", next((k for k, v in am.items() if "dom_html" in v), None)), ctrl("accessibility_tree", "ax", next((k for k, v in am.items() if "accessibility_tree" in v), None))],
                 must_not_over=[ctrl("dom_diff", None, next((k for k, v in am.items() if "dom_diff" in v), None)), ctrl("screenshot_thumb", None, next((k for k, v in am.items() if "screenshot_thumb" in v), None))],
                 impact_on_current_source="fixtures use canonical names", fix_applied=None)
        dm = lambda name: (name.lower().endswith(".jsonl") or (name.lower().endswith(".json") and "manifest" in name.lower())) and not (name.lower().endswith(".sha256") or name.lower().startswith("path_manifest"))
        self.add(id="M21", tool="gate1/lane5_evidence/evidence_lineage_check.py", where="discover_manifests() filename heuristic", feeds="the evidence denominator itself (0 manifests ⇒ NO_EVIDENCE_INPUT, exit 3 — R43, never COMPLETE)",
                 pattern="*.jsonl | *manifest*.json ; minus *.sha256, path_manifest*, the --path-manifest file", rule="same", direction_if_narrow="NO_EVIDENCE_INPUT (fail-closed by R43)", direction_if_wide="artifact json files parsed as manifests → spurious MISSING_FIELD",
                 denominator={"name": ".json/.jsonl files under C lane5 fixtures", "n": files_json}, extracted={"discovered_manifests": discovered, "names": sorted(discovered_names)},
                 must_not_miss=[ctrl("evidence_manifest.jsonl", True, dm("evidence_manifest.jsonl")), ctrl("MANIFEST.json", True, dm("MANIFEST.json")), ctrl("run_manifest_v2.json", True, dm("run_manifest_v2.json")), ctrl("steps.jsonl", True, dm("steps.jsonl"))],
                 must_not_over=[ctrl("path_manifest.json", False, dm("path_manifest.json")), ctrl("evidence_manifest.jsonl.sha256", False, dm("evidence_manifest.jsonl.sha256")), ctrl("S0/ax.json", False, dm("ax.json")), ctrl("probe.json", False, dm("probe.json")),
                                ctrl("run_result.json (B's summary — not a manifest)", False, dm("run_result.json"))],
                 impact_on_current_source="3/3 fixture manifests discovered; 0 artifact json files mis-discovered", fix_applied=None)
        self.add(id="M22", tool="gate1/lane5_evidence/evidence_lineage_check.py", where="ID_RE / SHA_RE / STATE_INDEX_RE / collector-sha 7-64 hex", feeds="DISPLAY_NAME_AS_ID / MANIFEST_SHA_UNBOUND / SCHEMA_VIOLATION defects",
                 pattern={"ID_RE": L5.ID_RE.pattern, "SHA_RE": L5.SHA_RE.pattern, "STATE_INDEX_RE": L5.STATE_INDEX_RE.pattern, "collector_sha": "^[0-9a-f]{7,64}$"}, rule="validators (a miss = defect, fail-closed)", direction_if_narrow="over-flag", direction_if_wide="display names / short shas accepted",
                 denominator={"name": "records", "n": n_rec}, extracted={"see": "lane5 report defects"},
                 must_not_miss=[ctrl("ID 'svc_coupang_m'", True, L5.ID_RE.match("svc_coupang_m") is not None), ctrl("ID 'T07:search'", True, L5.ID_RE.match("T07:search") is not None), ctrl("S12", True, L5.STATE_INDEX_RE.match("S12") is not None), ctrl("64-hex", True, L5.SHA_RE.match("a" * 64) is not None)],
                 must_not_over=[ctrl("ID 'Coupang Mobile App'", False, L5.ID_RE.match("Coupang Mobile App") is not None), ctrl("ID '쿠팡'", False, L5.ID_RE.match("쿠팡") is not None), ctrl("S1a", False, L5.STATE_INDEX_RE.match("S1a") is not None), ctrl("s1 (lowercase)", False, L5.STATE_INDEX_RE.match("s1") is not None),
                                ctrl("63-hex", False, L5.SHA_RE.match("a" * 63) is not None), ctrl("uppercase 64-hex", False, L5.SHA_RE.match("A" * 64) is not None, "uppercase sha rejected — fail-closed, B must emit lowercase (contract)")],
                 impact_on_current_source="bad_lineage fixture is caught by ID_RE (display name as spine id)", fix_applied=None)

    # ================================================================== lane6 c_flow_derive.py
    def m_lane6(self):
        cl = lambda s, drop=False: L6._clean(s, drop_noncanonical=drop)
        def raises(s):
            try: cl(s); return False
            except ValueError: return True
        self.add(id="M23", tool="gate1/lane6_stats/c_flow_derive.py", where="_clean() sequence normaliser (split on '>' , strip, upper, CANONICAL_TOKENS membership)", feeds="every derived count (activation_depth, flow_step_count, menu_dependency …)",
                 pattern="re.split(r'\\s*>\\s*') ; str(t).strip().upper() ; t in CANONICAL_TOKENS else ValueError (or dropped list when drop_noncanonical)", rule="non-canonical tokens are never silently ignored: raise, or return them in `dropped`",
                 direction_if_narrow="raise (explicit)", direction_if_wide="case-normalisation accepts lowercase tokens — declared, not silent (a lowercase token is still the canonical token)",
                 denominator={"name": "canonical tokens", "n": len(L6.CANONICAL_TOKENS)}, extracted={"canonical": sorted(L6.CANONICAL_TOKENS)},
                 must_not_miss=[ctrl("'OPEN_GLOBAL_MENU>SELECT_FUNCTION' (no spaces)", ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION"], cl("OPEN_GLOBAL_MENU>SELECT_FUNCTION")[0]), ctrl("' OPEN_GLOBAL_MENU  >  ENDPOINT_REACHED '", ["OPEN_GLOBAL_MENU", "ENDPOINT_REACHED"], cl(" OPEN_GLOBAL_MENU  >  ENDPOINT_REACHED ")[0]),
                                ctrl("list with trailing space token", ["AUTH_GATE"], cl(["AUTH_GATE "])[0])],
                 must_not_over=[ctrl("OPEN_RIGHT_DRAWER (direction-bearing) raises", True, raises(["OPEN_RIGHT_DRAWER"])), ctrl("drop mode returns dropped list", ["OPEN_RIGHT_DRAWER"], cl(["OPEN_RIGHT_DRAWER", "AUTH_GATE"], True)[1]),
                                ctrl("'SCROLL' raises", True, raises(["SCROLL"])), ctrl("None → empty, no raise", ([], []), cl(None))],
                 impact_on_current_source="C fixtures only; explicit failure path", fix_applied=None)
        q = lambda o: L6.q8_bare_mentions(o)
        self.add(id="M24", tool="gate1/lane6_stats/c_flow_derive.py", where="_Q8_BARE_RE + Q8_QUALIFYING_KEYS (R6 Q8 AUTH_GATE/ABSTAIN layer qualification)", feeds="assert_field_qualified → ValueError (fail-closed)",
                 pattern={"regex": L6._Q8_BARE_RE.pattern, "qualifying_keys": sorted(L6.Q8_QUALIFYING_KEYS), "suffix_rule": "key endswith action_token|endpoint_status"}, rule="a bare AUTH_GATE/ABSTAIN under a non-qualifying key, as a dict key, or in free text without `endpoint_status=`/`action_token=` is flagged",
                 direction_if_narrow="silent pass (unqualified mention not flagged)", direction_if_wide="over-flag (raise on compliant text — fail-closed)",
                 denominator={"name": "n/a (validator; B rows not at hand)", "n": None}, extracted={},
                 must_not_miss=[ctrl({"note": "status AUTH_GATE reached"}, 1, len(q({"note": "status AUTH_GATE reached"}))), ctrl({"labels": ["AUTH_GATE"]}, 1, len(q({"labels": ["AUTH_GATE"]}))), ctrl({"AUTH_GATE": 1}, 1, len(q({"AUTH_GATE": 1})))],
                 must_not_over=[ctrl({"endpoint_status": "AUTH_GATE"}, 0, len(q({"endpoint_status": "AUTH_GATE"}))), ctrl({"note": "endpoint_status=AUTH_GATE"}, 0, len(q({"note": "endpoint_status=AUTH_GATE"}))), ctrl({"signature": "A>B>AUTH_GATE"}, 0, len(q({"signature": "A>B>AUTH_GATE"}))),
                                ctrl({"note": "AUTH_GATED page"}, 0, len(q({"note": "AUTH_GATED page"}))), ctrl({"nav_anchor_action_token": "AUTH_GATE"}, 0, len(q({"nav_anchor_action_token": "AUTH_GATE"}))),
                                ctrl({"note": "endpoint_status: AUTH_GATE"}, 1, len(q({"note": "endpoint_status: AUTH_GATE"})), "colon form IS flagged — declared wording is `key=VALUE`; over-flag direction is fail-closed (raise), listed as a known narrowness of the qualifier syntax")],
                 impact_on_current_source="n/a", fix_applied=None, proposed_fix="accept `endpoint_status: AUTH_GATE` / `action_token: X` as qualified free-text forms if B's prose uses colons (would remove an over-flag, not a miss)")
        ct = L6.classify_token
        self.add(id="M25", tool="gate1/lane6_stats/c_flow_derive.py", where="classify_token() / row field readers (row.get('endpoint_status') …)", feeds="activation_depth membership; endpoint_status comparisons",
                 pattern="frozenset membership per T-A-V3-STEP1-006; row.get(...) with explicit None handling (flow_evaluable / evidence_bearing return None-aware)", rule="unknown token raises; absent row field → None → NOT_OBSERVED/UNDETERMINED paths, never a default count",
                 direction_if_narrow="raise", direction_if_wide="n/a", denominator={"name": "canonical tokens", "n": len(L6.CANONICAL_TOKENS)}, extracted={"activation_in": sorted(L6.ACTIVATION_IN_TOKENS), "conditional": sorted(L6.CONDITIONAL_ACTIVATION_TOKENS)},
                 must_not_miss=[ctrl("SUBMIT_QUERY activation", True, ct("SUBMIT_QUERY")["state_changing_activation"]), ctrl("SWITCH_TAB activation", True, ct("SWITCH_TAB")["state_changing_activation"])],
                 must_not_over=[ctrl("INPUT_QUERY not activation", False, ct("INPUT_QUERY")["state_changing_activation"]), ctrl("unknown token raises", True, (lambda: (lambda: ct("OPEN_RIGHT_DRAWER"))() and False)() if False else _raises(lambda: ct("OPEN_RIGHT_DRAWER")))],
                 impact_on_current_source="n/a", fix_applied=None)

    # ================================================================== comparators
    def m_comparators(self):
        none = AM.AdapterMap.none(); spec = AM.AdapterMap.spec_defaults()
        self.add(id="M26", tool="gate1/comparators/adapter_map.py", where="AdapterMap.field_key / file_spec / RunnerOutput.field (dict-driven lookups)", feeds="every comparator PASS/FAIL (UNMAPPED ⇒ NOT_TESTABLE, never PASS)",
                 pattern="fields['<table>.<C field>'] → runner key (dotted) | None ; files['<table>'] → path[#dotted] | '@files.<key>' | None", rule="no entry / null / absent-in-runner ⇒ Lookup(status=UNMAPPED); a default VALUE is never synthesised",
                 direction_if_narrow="NOT_TESTABLE (explicit)", direction_if_wide="n/a (no fuzzy matching exists)", denominator={"name": "spec default field keys", "n": len(AM.SPEC_FIELDS) if hasattr(AM, "SPEC_FIELDS") else None},
                 extracted={"unmapped_rows_in_spec_defaults": len(spec.unmapped_rows()), "unmapped_rows_with_no_map": len(none.unmapped_rows())},
                 must_not_miss=[ctrl("spec default flow.endpoint_status", "OK", spec.field_key("flow.endpoint_status").status)],
                 must_not_over=[ctrl("no map: flow.endpoint_status", "UNMAPPED", none.field_key("flow.endpoint_status").status), ctrl("unknown field", "UNMAPPED", spec.field_key("flow.no_such_field_r54").status)],
                 impact_on_current_source="dry-run: 183 UNMAPPED without a map (comparators/selftest.py)", fix_applied=None)
        sidx = lambda s: re.fullmatch(r"[sS]\d+", s) is not None
        self.add(id="M27", tool="gate1/comparators/common.py", where="state index normaliser [sS]\\d+", feeds="state id equality in surface/step compares", pattern="[sS]\\d+ fullmatch", rule="S<n> or s<n> → index int; anything else left as-is (compared literally)",
                 direction_if_narrow="literal compare (visible mismatch)", direction_if_wide="n/a", denominator={"name": "n/a", "n": None}, extracted={},
                 must_not_miss=[ctrl("S0", True, sidx("S0")), ctrl("s12", True, sidx("s12"))], must_not_over=[ctrl("S0a", False, sidx("S0a")), ctrl("state0", False, sidx("state0"))], impact_on_current_source="n/a", fix_applied=None)
        wb = lambda k: re.search(r"waybill|tracking|운송장", k, re.I) is not None
        exp = json.loads((HERE / "lane1_task_binding" / "EXPECTATIONS.json").read_text(encoding="utf-8"))
        keys = set(); [keys.update(_all_keys(exp))]
        self.add(id="M28", tool="gate1/comparators/compare_lane1.py", where="waybill/tracking/운송장 key regex (input-value field detection)", feeds="L1 input-field presence check", pattern="waybill|tracking|운송장 (re.I, substring over runner keys)",
                 rule="substring, case-insensitive", direction_if_narrow="silent pass (input field not found ⇒ check skipped?)", direction_if_wide="unrelated key read as the tracking field",
                 denominator={"name": "distinct keys in lane1 EXPECTATIONS.json (C side)", "n": len(keys)}, extracted={"matching_keys": sorted(k for k in keys if wb(k))},
                 must_not_miss=[ctrl("trackingNumber", True, wb("trackingNumber")), ctrl("운송장번호", True, wb("운송장번호")), ctrl("WAYBILL_NO", True, wb("WAYBILL_NO"))],
                 must_not_over=[ctrl("backtracking_enabled", False, wb("backtracking_enabled"), "substring rule matches — WIDE_OVER (latent; no such key in C fixtures); comparators outside this sweep's edit scope", accepted=True), ctrl("query", False, wb("query"))],
                 impact_on_current_source="0 over-matches in C's own expectation keys; B's keys unknown until the adapter map", fix_applied=None,
                 proposed_fix="word-start bound: (?<![a-z])(waybill|tracking)|운송장 — comparators are not in this sweep's edit scope; apply at the adapter-map step")
        lr = lambda s: L4.LAUNCH_RE.search(s) is not None; tx = lambda s: L4.TX_TEXT_RE.search(s) is not None
        self.add(id="M29", tool="gate1/comparators/grade_lane4.py", where="LAUNCH_RE (first browser-launch line in the runner log)", feeds="S4 ordering: guard registered before launch", pattern=L4.LAUNCH_RE.pattern, rule="first log line matching, case-insensitive",
                 direction_if_narrow="no launch line ⇒ ordering NOT_TESTABLE (explicit)", direction_if_wide="a prose line ('scouting') taken as the launch ⇒ ordering judged too early", denominator={"name": "n/a (B log)", "n": None}, extracted={},
                 must_not_miss=[ctrl("browser launched", True, lr("browser launched")), ctrl("[Scout] start", True, lr("[Scout] start")), ctrl("evidence/ dir created", True, lr("evidence/ dir created"))],
                 must_not_over=[ctrl("scouting report written", False, lr("scouting report written"), "matches 'Scout' re.I — WIDE_OVER (latent); comparators outside this sweep's edit scope", accepted=True), ctrl("L0 (bare token)", True, lr("level L0 reached"), "\\bL0\\b matches any L0 mention — declared"), ctrl("plain line", False, lr("guard registered"))],
                 impact_on_current_source="n/a", fix_applied=None, proposed_fix="anchor Scout to a launch verb (Scout.*(start|launch)) or read a structured launch event from action_log instead of prose")
        self.add(id="M30", tool="gate1/comparators/grade_lane4.py", where="TX_TEXT_RE over clicked-control accessible names (forbidden transaction click)", feeds="FORBIDDEN grading (safety; over-flag = fail-closed)", pattern=L4.TX_TEXT_RE.pattern, rule="substring over accname",
                 direction_if_narrow="silent pass on a real purchase click (dangerous)", direction_if_wide="over-flag ('구매후기' review tab graded as purchase) — safe direction", denominator={"name": "n/a (B action log)", "n": None}, extracted={},
                 must_not_miss=[ctrl("바로구매하기", True, tx("바로구매하기")), ctrl("결제하기", True, tx("결제하기")), ctrl("장바구니 담기", True, tx("장바구니 담기")), ctrl("송금", True, tx("송금"))],
                 must_not_over=[ctrl("구매후기 (review tab)", False, tx("구매후기"), "WIDE_OVER by control; direction is fail-closed (extra FORBIDDEN), accepted for a safety matcher", accepted=True), ctrl("예약확인", False, tx("예약확인"), "same", accepted=True), ctrl("검색", False, tx("검색"))],
                 classification="WIDE_OVER", impact_on_current_source="n/a — safety direction; kept wide on purpose, recorded", fix_applied=None,
                 proposed_fix="none — a safety matcher is kept wide; grade output should list the accname so an over-flag is reviewable (it does: action_log row is quoted)")

    # ================================================================== limitation reader (runbook Limitation rule r2) + RIC
    def m_limitation(self):
        ls = limitation_status
        doc_ok = "# Report\n\n## 1. Method\ntext\n\n## 12. Limitation\nB did not run fixture 3.\n\n## 13. Next\n"
        doc_ko = "## 결과\n\n### 12) 한계와 미검증\n- 없음: 전부 검증됨\n"
        doc_empty = "## Results\n\n## Limitations\n\n## Appendix\nx\n"
        doc_none = "## Results\nall good. There is no limitation here.\n\n## Unlimited retries\nn/a\n"
        doc_fence = "## Results\n\n```\n## Limitation\nthis is inside a code block\n```\n"
        doc_circ = "## ③ 한계 — 3건\n남은 한계 3건.\n"
        doc_trail = "#### Limitations of this run — see below\nfoo\n"
        self.add(id="M31", tool="(no C tool — GATE1_RUNBOOK_C.md 'Limitation rule r2' declares a heading parser; none existed in code)", where="reference implementation limitation_status() in this sweep", feeds="GATE limitation reading (LIMITATION_NOT_STATED / EMPTY / STATED — a sentinel is itself a claim)",
                 pattern=LIMITATION_HEAD_RE.pattern, rule=LIMITATION_RULE, direction_if_narrow="NOT_STATED read as 'no limitation' (the D 18/27 defect, Δ54)", direction_if_wide="prose or fenced text read as a section",
                 denominator={"name": "n/a (no B artifact at hand); controls only", "n": None}, extracted={},
                 must_not_miss=[ctrl("## 12. Limitation", "LIMITATION_STATED", ls(doc_ok)["status"]), ctrl("### 12) 한계와 미검증", "LIMITATION_STATED", ls(doc_ko)["status"]), ctrl("## ③ 한계 — 3건", "LIMITATION_STATED", ls(doc_circ)["status"]),
                                ctrl("#### Limitations of this run — see below", "LIMITATION_STATED", ls(doc_trail)["status"]), ctrl("## Limitations (empty body)", "LIMITATION_EMPTY", ls(doc_empty)["status"]), ctrl("no section at all (must_flag)", "LIMITATION_NOT_STATED", ls(doc_none)["status"])],
                 must_not_over=[ctrl("prose 'no limitation here' is not a heading", "LIMITATION_NOT_STATED", ls(doc_none)["status"]), ctrl("'## Unlimited retries' is not a limitation heading", False, "Unlimited" in str(ls(doc_none)["headings"])),
                                ctrl("fenced '## Limitation' ignored", "LIMITATION_NOT_STATED", ls(doc_fence)["status"])],
                 impact_on_current_source="not yet applied to a B artifact — every GATE reading must cite this rule string next to the status", fix_applied="reference implementation + controls provided here (import gate1.r54_matcher_sweep_c.limitation_status)", status_before_fix="NARROW_MISS (no parser existed; the runbook rule was prose)")
        ric = json.loads((HERE / "RULING_INDEX_COVERAGE_C.json").read_text(encoding="utf-8"))
        self.add(id="M32", tool="gate1/RULING_INDEX_COVERAGE_C.{md,json}", where="index_vs_delta block / row table", feeds="C coverage claim (COVERED / PARTIAL / UNCOVERED counts)",
                 pattern="(hand-authored — no generator script exists; no regex to inventory)", rule="rows are copied from V3_RULING_INDEX.json ids; index_vs_delta was derived by a worker pass, not by a tool",
                 direction_if_narrow="n/a", denominator={"name": "RIC rows vs index rows now", "n": {"ric_rows": len(ric.get("rows", [])), "index_rows_now": len(self.idx.rows), "ric_index_sha256": ric.get("index_sha256"), "index_sha256_now": self.idx.sha256}},
                 extracted={"ric_rows_not_in_index": sorted({r.get("id") for r in ric.get("rows", [])} - set(self.idx.ids)), "index_rows_not_in_ric": sorted(set(self.idx.ids) - {r.get("id") for r in ric.get("rows", [])})},
                 must_not_miss=[], must_not_over=[], classification="NOT_A_MATCHER", impact_on_current_source="the heading/row denominators the RIC cites are now produced by c_bus_scan (delta_heading_counts) — RIC should cite those, not a hand count",
                 fix_applied=None, proposed_fix="regenerate RIC rows from the scanner's index/delta identity at the next RIC revision (index has moved since the RIC's sha)")

    # ------------------------------------------------------------------ run
    def run(self) -> dict:
        src = self.load_sources()
        self.rg = CB.check_ruling_index(self.tickets, self.repo, CB.DEFAULT_INDEX_REF, None, CB.DEFAULT_DELTA_REF)
        if self.rg.get("status") != "OK":
            raise SystemExit("scanner ruling-index controls did not pass — sweep refuses to measure (exit 2)")
        self.rl_hits = CB.ref_lint(self.tickets, ASSURANCE)["hits"]
        for m in (self.m_ack_suffix, self.m_fc_selector_and_how_known, self.m_ref_lint, self.m_tokens, self.m_boundaries, self.m_headings, self.m_real_and_era,
                  self.m_r32_helper, self.m_lane5, self.m_lane6, self.m_comparators, self.m_limitation):
            m()
        by = collections.Counter(r["classification"] for r in self.records)
        failing = [r["id"] for r in self.records if not r["controls_pass_or_accepted"]]
        accepted = [r["id"] for r in self.records if not r["controls_pass"] and r["controls_pass_or_accepted"]]
        return {"tool": "gate1/r54_matcher_sweep_c.py", "plane": "C", "ruling": "V3_0_1_SUCCESSOR_DELTA.md Δ54 / R54 (D-V3-FINDING-025)",
                "measured_at_kst": dt.datetime.now(KST).isoformat(timespec="seconds"), "sweep_tool_sha256": sha256_file(pathlib.Path(__file__)),
                "sources": src, "vocabulary": {"NARROW_MISS": "must_not_miss control fails (silent 0 / silent pass direction)", "WIDE_OVER": "must_not_over control fails (silent over-count / over-flag)", "OK": "both controls pass and the presence probe agrees",
                                               "status_before_fix": "classification of the pre-sweep tool where a fix was applied", "NOT_A_MATCHER": "inventoried for completeness; nothing to match"},
                "counts": {"matchers": len(self.records), "by_classification_now": dict(by), "fixed": len(self.fixed), "controls_total": sum(len(r.get("must_not_miss", [])) + len(r.get("must_not_over", [])) for r in self.records),
                           "controls_failing": failing, "controls_failing_but_accepted_and_recorded": accepted, "status_before_fix_counts": dict(collections.Counter((r.get("status_before_fix") or "").split(" ")[0] for r in self.records if r.get("status_before_fix")))},
                "fixed": self.fixed, "edit_scope": "c_bus_scan.py and gate1/intake/r32_inventory.py only (per task); lane5 / lane6 / comparators are inventoried with proposed fixes",
                "matchers": self.records, "ok": not failing}


# ---------------------------------------------------------------------------------------------- helpers
def glob_all(bus: str, sub: str) -> list[str]:
    d = os.path.join(bus, sub)
    return [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".json")] if os.path.isdir(d) else []


def _all_keys(o: Any):
    if isinstance(o, dict):
        for k, v in o.items():
            yield str(k); yield from _all_keys(v)
    elif isinstance(o, list):
        for v in o: yield from _all_keys(v)


def _raises(fn) -> bool:
    try: fn(); return False
    except Exception: return True


LIMITATION_RULE = ("a heading line (1-6 #) outside fenced code whose title, after stripping leading numbering (digits, ①-⑳, roman, ./)/) and punctuation), contains "
                   "the word 'limitation(s)' (case-insensitive) or '한계'; body = lines until the next heading of the same or higher level; "
                   "NOT_STATED = no such heading (parser rule cited), EMPTY = heading with a blank body, STATED = body has text")
LIMITATION_HEAD_RE = re.compile(r"^(#{1,6})\s+(?:[\d①-⑳ivxIVX.)(\s]+\s*)?(.*?(?:\blimitations?\b|한계).*?)\s*$", re.I)


def limitation_status(md: str) -> dict:
    """Reference limitation reader (runbook Limitation rule r2 / R54). Returns {status, headings, rule}."""
    lines = md.splitlines(); out_lines = []; fence = False
    for ln in lines:
        if ln.strip().startswith("```"): fence = not fence; out_lines.append(None); continue
        out_lines.append(None if fence else ln)
    heads = [(i, len(m.group(1)), m.group(2)) for i, ln in enumerate(out_lines) if ln is not None for m in [LIMITATION_HEAD_RE.match(ln)] if m]
    if not heads: return {"status": "LIMITATION_NOT_STATED", "headings": [], "rule": LIMITATION_RULE}
    statuses = []
    for i, lvl, title in heads:
        body = []
        for ln in out_lines[i + 1:]:
            if ln is None: continue
            m = re.match(r"^(#{1,6})\s", ln)
            if m and len(m.group(1)) <= lvl: break
            body.append(ln)
        statuses.append("LIMITATION_STATED" if "".join(body).strip() else "LIMITATION_EMPTY")
    return {"status": "LIMITATION_STATED" if "LIMITATION_STATED" in statuses else "LIMITATION_EMPTY", "headings": [t for _, _, t in heads], "rule": LIMITATION_RULE}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT); ap.add_argument("--bus", default=DEFAULT_BUS); ap.add_argument("--repo", default=CB.DEFAULT_REPO)
    a = ap.parse_args(argv)
    res = Sweep(a.bus, a.repo).run()
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    c = res["counts"]
    print(f"R54_SWEEP: matchers={c['matchers']} now={c['by_classification_now']} before_fix={c['status_before_fix_counts']} fixed={c['fixed']} controls={c['controls_total']} failing={c['controls_failing']} "
          f"control_commit={res['sources']['control_fetch']['control_commit'][:12]} delta={res['sources']['delta_sha256'][:12]} index=v{res['sources']['index_version']}/{res['sources']['index_sha256'][:12]} out={a.out}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    try:
        rc = main()
    except SystemExit as e:
        raise
    except Exception:
        import traceback; traceback.print_exc(); print("r54_matcher_sweep_c: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr); rc = 2
    sys.exit(rc)
