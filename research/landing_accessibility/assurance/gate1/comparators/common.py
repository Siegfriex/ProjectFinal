"""Shared helpers for the C GATE 1 comparators (offline, no network).

Item vocabulary (per check): PASS | FAIL | UNMAPPED | NOT_TESTABLE.
  UNMAPPED      the C field is not bound to a runner field / file (adapter map), or the mapped key is absent in
                the runner output — never graded PASS by silence.
  NOT_TESTABLE  the inputs for this check do not exist (e.g. C reference geometry not generated, log inactive).
Severity: SYSTEMIC (default; a FAIL blocks) | ISOLATED (listed, does not block — README rule for e.g.
dom_ax_divergence "finding to inspect", precision defects in lane4).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unicodedata
from typing import Any

_WS = re.compile(r"\s+")


def norm(text: Any) -> str:
    """NFC + whitespace collapse + trim (04 §5). None → ''."""
    if text is None:
        return ""
    return _WS.sub(" ", unicodedata.normalize("NFC", str(text))).strip()


def item(fixture: str, check: str, expected: Any, observed: Any, status: str, reason: str | None = None,
         severity: str = "SYSTEMIC", **extra: Any) -> dict:
    assert status in ("PASS", "FAIL", "UNMAPPED", "NOT_TESTABLE"), status
    d = {"fixture": fixture, "check": check, "expected": expected, "observed": observed, "status": status,
         "severity": severity}
    if reason:
        d["reason"] = reason
    d.update(extra)
    return d


def eq_item(fixture: str, check: str, expected: Any, lookup, *, normalize: bool = False, severity: str = "SYSTEMIC",
            accept_none_for: Any = None, **extra: Any) -> dict:
    """Exact-equality item from a Lookup. accept_none_for: an expected value for which observed None also passes
    (GAP-04: NOT_OBSERVED may be encoded as null by the runner)."""
    if not lookup.ok:
        return item(fixture, check, expected, None, "UNMAPPED", lookup.reason, severity, **extra)
    obs = lookup.value
    if normalize:
        ok = norm(obs) == norm(expected)
    elif isinstance(expected, bool) or isinstance(obs, bool):
        ok = _as_bool(obs) == _as_bool(expected)
    else:
        ok = obs == expected
    if not ok and accept_none_for is not None and expected == accept_none_for and obs is None:
        ok = True
    return item(fixture, check, expected, obs, "PASS" if ok else "FAIL", None if ok else "mismatch", severity, **extra)


def _as_bool(v: Any) -> Any:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    if isinstance(v, str) and v.strip().lower() in ("true", "false", "0", "1"):
        return v.strip().lower() in ("true", "1")
    return v


def as_int(v: Any) -> int | None:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        return int(v.strip())
    return None


def bbox_center(b: Any) -> tuple[float, float] | None:
    """Accept {x,y,width,height} | {x,y,w,h} | {left,top,width,height} | [x,y,w,h]; None if not a bbox."""
    if b is None:
        return None
    if isinstance(b, (list, tuple)) and len(b) == 4:
        x, y, w, h = b
    elif isinstance(b, dict):
        x = b.get("x", b.get("left"))
        y = b.get("y", b.get("top"))
        w = b.get("width", b.get("w"))
        h = b.get("height", b.get("h"))
    else:
        return None
    try:
        return float(x) + float(w) / 2.0, float(y) + float(h) / 2.0
    except (TypeError, ValueError):
        return None


def state_key(v: Any) -> str:
    """Normalise a state_index value: 0 / '0' / 'S0' → 'S0'; 'POST_REVEAL:X' unchanged."""
    if v is None:
        return ""
    s = str(v).strip()
    if s.isdigit():
        return f"S{int(s)}"
    if re.fullmatch(r"[sS]\d+", s):
        return "S" + s[1:]
    return s


def contract_sha256(c: dict) -> str:
    """01 §5 recipe (lane1 task_contracts.json hash_recipe)."""
    canon = {k: c.get(k) for k in ("family_id", "task_id", "task_instruction", "fixed_fixture", "endpoint_contract")}
    return hashlib.sha256(json.dumps(canon, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def aggregate(items: list[dict]) -> dict:
    """Lane-item status from check items: any SYSTEMIC FAIL → FAIL; else any UNMAPPED/NOT_TESTABLE → NOT_TESTABLE;
    else PASS (ISOLATED FAILs are listed, not blocking)."""
    counts: dict[str, int] = {}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    sys_fail = [f"{i['fixture']}:{i['check']}" for i in items if i["status"] == "FAIL" and i.get("severity") != "ISOLATED"]
    iso_fail = [f"{i['fixture']}:{i['check']}" for i in items if i["status"] == "FAIL" and i.get("severity") == "ISOLATED"]
    unmapped = [f"{i['fixture']}:{i['check']}" for i in items if i["status"] == "UNMAPPED"]
    not_testable = [f"{i['fixture']}:{i['check']}" for i in items if i["status"] == "NOT_TESTABLE"]
    if not items:
        status, reason = "NOT_TESTABLE", "no check items produced"
    elif sys_fail:
        status, reason = "FAIL", f"{len(sys_fail)} systemic check(s) failed: {sys_fail[:6]}"
    elif unmapped or not_testable:
        status = "NOT_TESTABLE"
        reason = f"UNMAPPED {len(unmapped)} / NOT_TESTABLE {len(not_testable)}: {(unmapped + not_testable)[:6]}"
    else:
        status, reason = "PASS", None
    if iso_fail:
        reason = (reason + " · " if reason else "") + f"isolated (non-blocking) FAIL: {iso_fail[:6]}"
    return {"status": status, "reason": reason, "counts": counts, "systemic_fail": sys_fail, "isolated_fail": iso_fail,
            "unmapped": unmapped, "not_testable": not_testable, "n_items": len(items)}


def load_json(p: pathlib.Path | str) -> Any:
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
