#!/usr/bin/env python3
"""C DOM-replay harness (V1 prerequisite): re-run a given l0_probe.js over stored dom.html snapshots.

Network: ZERO. Every request that is not file:// is aborted via Playwright routing. No REAL_TARGET access.
Purpose: produce probe_v2.json per frozen observation so that the W2 resolver (which reads new probe
signals) can be evaluated on the frozen E001 evidence. This does not modify any evidence (writes go to
a separate C-only output dir).

Usage: dom_replay_probe.py <probe_js_path> <out_dir> [execution_mode=REAL_TARGET] [limit]
"""
from __future__ import annotations
import sys, json, glob, pathlib, datetime, hashlib
try:
    from playwright.sync_api import sync_playwright
except ImportError as _e:  # Δ46-exit2: a probe that cannot import its browser driver did not run
    if __name__ != "__main__":
        raise
    print(f"dom_replay_probe: did not run — read neither as pass nor fail (exit 2): {_e!r}", file=sys.stderr); sys.exit(2)

MART = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts/fact_landing_observation.json")
EVID = "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_b_e001_worker_0*/artifacts/e001_w0*/evidence/*/*/l0a/dom.html"

def main(probe_js: str, out_dir: str, mode: str = "REAL_TARGET", limit: int = 0) -> int:
    js = pathlib.Path(probe_js).read_text(encoding="utf-8"); js_sha = hashlib.sha256(js.encode()).hexdigest()
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    mart = {c["observation_id"]: c for c in json.loads(MART.read_text())}
    doms = [p for p in sorted(glob.glob(EVID)) if p.split("/")[-3] in mart]
    if limit: doms = doms[:limit]
    log = []; blocked = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1, is_mobile=True, has_touch=True, locale="ko-KR", timezone_id="Asia/Seoul", java_script_enabled=True, offline=False)
        def route(r):
            nonlocal blocked
            if r.request.url.startswith("file://"): return r.continue_()
            blocked += 1; return r.abort()
        ctx.route("**/*", route)
        page = ctx.new_page(); page.set_default_timeout(20000)
        for p in doms:
            obs = p.split("/")[-3]; rec = {"observation_id": obs, "web_target_id": mart[obs]["web_target_id"], "dom_path": p, "dom_sha256": hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()}
            try:
                page.goto("file://" + p, wait_until="domcontentloaded")
                page.wait_for_timeout(300)
                raw = page.evaluate(js, mode)
                (out / f"{obs}.probe_v2.json").write_text(json.dumps({"observation_id": obs, "execution_mode_arg": mode, "probe_js_sha256": js_sha, "source_dom_sha256": rec["dom_sha256"], "replayed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "raw_features": raw.get("raw_features", raw)}, ensure_ascii=False))
                rec["status"] = "OK"; rec["keys"] = sorted((raw.get("raw_features", raw) or {}).keys())[:12]
            except Exception as e:
                rec["status"] = "ERROR"; rec["error"] = str(e)[:300]
            log.append(rec); print(obs[:8], rec["status"], flush=True)
        browser.close()
    manifest = {"artifact": "C_DOM_REPLAY_PROBE_MANIFEST", "probe_js_sha256": js_sha, "execution_mode_arg": mode, "n_dom": len(doms), "ok": sum(1 for r in log if r["status"] == "OK"), "network_requests_blocked": blocked, "real_target_access": 0, "records": log}
    (out / "REPLAY_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(json.dumps({k: manifest[k] for k in ("n_dom", "ok", "network_requests_blocked")}))
    return 0

if __name__ == "__main__":
    a = sys.argv[1:]
    try:
        _rc = main(a[0], a[1], a[2] if len(a) > 2 else "REAL_TARGET", int(a[3]) if len(a) > 3 else 0)
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("dom_replay_probe: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
