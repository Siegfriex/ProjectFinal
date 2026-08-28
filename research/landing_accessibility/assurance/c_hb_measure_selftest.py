#!/usr/bin/env python3
"""R43/R41 demonstration for c_hb_measure: the safety fields must (must_not_flag) read MEASURED-false/true in the normal
state, and (must_flag) turn into UNVERIFIED_* — never the safe value — when git/remote are unreadable; a dirty path
outside C's namespace must flip production_modified to True. exit 0 all controls OK · 1 a control failed · 2 did not run."""
from __future__ import annotations
import json, sys, importlib
def main() -> int:
    m = importlib.import_module("c_hb_measure")
    res = {}
    base = m.measure(); res["must_not_flag_normal"] = {"ok": base["production_modified"] is False and base["pushed"] in (True, False) and base["claim_provenance"]["production_modified"] == "MEASURED", "seen": {k: base[k] for k in ("production_modified", "pushed", "REAL_TARGET")}}
    real_git = m._git
    def git_broken(*a, **k): return (128, "", "fatal: not a git repository")
    m._git = git_broken
    b = m.measure(); res["must_flag_git_unreadable"] = {"ok": str(b["production_modified"]).startswith("UNVERIFIED") and str(b["pushed"]).startswith("UNVERIFIED"), "seen": {k: b[k] for k in ("production_modified", "pushed")}}
    def git_dirty_outside(*a, **k):
        if a[0] == "status": return (0, " M src/somewhere/outside.py", "")
        return real_git(*a, **k)
    m._git = git_dirty_outside
    c = m.measure(); res["must_flag_dirty_outside_namespace"] = {"ok": c["production_modified"] is True and "src/somewhere/outside.py" in c["production_modified_evidence"]["dirty_paths_outside_namespace"], "seen": c["production_modified"]}
    m._git = real_git
    d = m.measure(); res["must_not_flag_restored"] = {"ok": d["production_modified"] is False, "seen": d["production_modified"]}
    ok = all(v["ok"] for v in res.values()); print(json.dumps({"selftest": "c_hb_measure", "all_ok": ok, "controls": res}, ensure_ascii=False)); return 0 if ok else 1
if __name__ == "__main__":
    try: sys.exit(main())
    except SystemExit: raise
    except Exception:
        import traceback; traceback.print_exc(); print("c_hb_measure_selftest: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr); sys.exit(2)
