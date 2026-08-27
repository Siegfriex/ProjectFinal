#!/usr/bin/env python3
"""C GATE1 lane1 self-check: fixtures parse, contracts hash, expectations align.

Independent of any B code. Exit 0 on success, 1 on any failure.
Run:  python3 selfcheck.py   (from anywhere; paths resolve relative to this file)
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys

from lxml import html as lhtml

HERE = os.path.dirname(os.path.abspath(__file__))
CANON = ("family_id", "task_id", "task_instruction", "fixed_fixture", "endpoint_contract")
VOCAB = {"REACHED", "AUTH_GATE", "PUBLIC_WEB_UNOBSERVABLE", "APP_REQUIRED", "EVIDENCE_DEFECT", "BLOCKED", "ABSTAIN"}
AUTH_VOCAB = {"NONE", "BEFORE_TASK_DISCOVERY", "AFTER_TASK_SELECT", "AT_ENDPOINT"}
EXTERNAL = re.compile(r"^\s*(https?:)?//", re.I)
CSV_CANDIDATES = [
    os.environ.get("SSOTV3_REGISTRY_CSV", ""),
    os.path.join(HERE, *([".."] * 5), "SSOTV3", "CROSS_SERVICE_TASK_REGISTRY_50_v3.0.csv"),  # worktree root
    "/home/sieg/projects-wsl/ProjectFinal/SSOTV3/CROSS_SERVICE_TASK_REGISTRY_50_v3.0.csv",  # main repo root
]

fails: list[str] = []
warns: list[str] = []


def fail(msg: str) -> None:
    fails.append(msg)


def canon_sha(c: dict) -> str:
    payload = json.dumps({k: c[k] for k in CANON}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load(name: str) -> dict:
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return json.load(fh)


def check_fixture(path: str, exp: dict) -> None:
    abs_path = os.path.join(HERE, path)
    if not os.path.isfile(abs_path):
        fail(f"{path}: missing fixture file")
        return
    raw = open(abs_path, "rb").read()
    doc = lhtml.fromstring(raw)
    # self-contained: no external URLs in href/src/action/srcset, no <script src>, no <link>
    for el in doc.iter():
        for attr in ("href", "src", "action", "srcset", "poster", "data"):
            v = el.get(attr)
            if v and EXTERNAL.match(v):
                fail(f"{path}: external reference {el.tag}[{attr}]={v}")
    if doc.xpath("//script[@src]") or doc.xpath("//link[@href]") or doc.xpath("//iframe"):
        fail(f"{path}: remote-loading element present")
    if not doc.xpath("//meta[@name='viewport']"):
        fail(f"{path}: missing viewport meta")
    if not doc.xpath("//title/text()"):
        fail(f"{path}: missing <title>")
    body = doc.xpath("//body")
    if not body or body[0].get("data-c-fixture") != os.path.splitext(os.path.basename(path))[0]:
        fail(f"{path}: body[data-c-fixture] must equal fixture basename")
    endpoints = set(doc.xpath("//*/@data-c-endpoint"))
    decoys = set(doc.xpath("//*/@data-c-decoy-endpoint"))
    for m in exp["expect"]["terminal_state_must_show"]:
        if m not in endpoints:
            fail(f"{path}: expected endpoint marker {m} not present in DOM")
    for m in exp["expect"]["terminal_state_must_not_show"]:
        if m not in endpoints | decoys:
            fail(f"{path}: must-not-show marker {m} is not even present in DOM (trap missing)")
    if exp["control_type"] == "NEGATIVE_CONTROL" and not (decoys or exp["expect"]["terminal_state_must_not_show"]):
        fail(f"{path}: negative control without any decoy marker")
    if exp["expect"].get("generic_login_present_on_s0") and not doc.xpath("//*[@data-c-generic-login='true']"):
        fail(f"{path}: generic login control expected on S0 but absent")
    if "REACHED" not in exp["expect"]["endpoint_status_allowed"] and endpoints:
        fail(f"{path}: fixture declares a true endpoint {endpoints} but expectation forbids REACHED")
    if not doc.xpath("//*[@data-c-forbidden]"):
        fail(f"{path}: no forbidden-action trap present")


def check_registry_verbatim(contracts: list[dict], tc: dict) -> None:
    csv_path = next((p for p in CSV_CANDIDATES if p and os.path.isfile(p)), None)
    if not csv_path:
        warns.append("registry CSV not found; verbatim check skipped (set SSOTV3_REGISTRY_CSV)")
        return
    raw = open(csv_path, "rb").read()
    if hashlib.sha256(raw).hexdigest() != tc["registry_source"]["file_sha256"]:
        warns.append(f"registry CSV sha256 differs from the one recorded at authoring time ({csv_path})")
    with open(csv_path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    fam: dict[str, set] = {}
    for r in rows:
        fam.setdefault(r["family_id"], set()).add((r["task_instruction"], r["fixed_fixture"], r["endpoint_contract"]))
    for c in contracts:
        s = fam.get(c["family_id"])
        if not s:
            fail(f"{c['task_id']}: family {c['family_id']} not in registry")
            continue
        if len(s) != 1:
            fail(f"{c['task_id']}: registry family {c['family_id']} has non-unique contract strings")
        if (c["task_instruction"], c["fixed_fixture"], c["endpoint_contract"]) not in s:
            fail(f"{c['task_id']}: task_instruction/fixed_fixture/endpoint_contract not verbatim from registry")


def main() -> int:
    tc = load("task_contracts.json")
    ex = load("EXPECTATIONS.json")
    contracts = tc["contracts"]
    by_id = {c["task_id"]: c for c in contracts}
    if len(by_id) != len(contracts):
        fail("duplicate task_id in task_contracts.json")
    if set(ex["endpoint_status_vocabulary_04_s4"]) != VOCAB:
        fail("EXPECTATIONS endpoint_status vocabulary != 04 §4")
    # 1) hash recompute
    for c in contracts:
        h = canon_sha(c)
        if h != c["contract_sha256"]:
            fail(f"{c['task_id']}: contract_sha256 mismatch (stored {c['contract_sha256'][:12]}, recomputed {h[:12]})")
        if c["freeze_status"] != "FROZEN_C_FIXTURE":
            fail(f"{c['task_id']}: unexpected freeze_status")
    # 2) expectations <-> contracts
    exp_ids = [e["task_id"] for e in ex["expectations"]]
    if set(exp_ids) != set(by_id) or len(exp_ids) != len(set(exp_ids)):
        fail(f"expectation task_ids {exp_ids} != contract task_ids {sorted(by_id)}")
    for e in ex["expectations"]:
        c = by_id.get(e["task_id"])
        if not c:
            continue
        x = e["expect"]
        if e["control_type"] not in ("POSITIVE_CONTROL", "NEGATIVE_CONTROL"):
            fail(f"{e['task_id']}: bad control_type")
        if x["task_id_out"] != c["task_id"] or x["family_id_out"] != c["family_id"]:
            fail(f"{e['task_id']}: expected ids must equal input ids (never re-bound)")
        if e["input_contract_sha256"] != c["contract_sha256"] or x["contract_sha256_out"] != c["contract_sha256"]:
            fail(f"{e['task_id']}: expected contract_sha256 must equal contract's")
        if x["endpoint_contract_out_verbatim"] != c["endpoint_contract"]:
            fail(f"{e['task_id']}: endpoint_contract echo not verbatim")
        if e["fixture_path"] != c["fixture_path"]:
            fail(f"{e['task_id']}: fixture_path mismatch")
        if not set(x["endpoint_status_allowed"]) <= VOCAB or set(x["endpoint_status_allowed"]) & set(x["endpoint_status_forbidden"]):
            fail(f"{e['task_id']}: endpoint_status sets invalid")
        if set(x["endpoint_status_allowed"]) | set(x["endpoint_status_forbidden"]) != VOCAB:
            fail(f"{e['task_id']}: allowed+forbidden must partition 04 §4 vocabulary")
        if not set(x["auth_gate_stage_allowed"]) <= AUTH_VOCAB:
            fail(f"{e['task_id']}: auth_gate_stage vocabulary")
        if set(CANON) - set(x["immutable_fields"]) - {"contract_sha256"}:
            fail(f"{e['task_id']}: immutable_fields must cover canonical hash fields")
        if x["legacy_archetype_if_present_must_equal"] != c["legacy_archetype"]:
            fail(f"{e['task_id']}: legacy_archetype expectation drift")
        check_fixture(c["fixture_path"], e)
    # 3) registry verbatim
    check_registry_verbatim(contracts, tc)
    # 4) positive control present
    if not any(e["control_type"] == "POSITIVE_CONTROL" for e in ex["expectations"]):
        fail("no POSITIVE_CONTROL fixture (negative results would be uninterpretable)")

    for w in warns:
        print(f"WARN {w}")
    for f in fails:
        print(f"FAIL {f}")
    n_fx = len(ex["expectations"])
    n_pos = sum(e["control_type"] == "POSITIVE_CONTROL" for e in ex["expectations"])
    status = "PASS" if not fails else "FAIL"
    print(f"SELFCHECK {status}: fixtures={n_fx} (pos={n_pos}, neg={n_fx - n_pos}) contracts={len(contracts)} "
          f"sha_recomputed={len(contracts)} fails={len(fails)} warns={len(warns)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
