#!/usr/bin/env python3
"""fake_runner_det.py FIXTURE OUT — tiny DETERMINISTIC fake runner (positive control for determinism_check).
Reads the fixture DOM with lxml; every fixed/sticky container whose dismiss lexicon button exists yields a
DISMISS_OBSTRUCTION step (order: z-index desc, then document order); then SELECT_FUNCTION on the task control,
then ENDPOINT_REACHED. Selector tie-break: always '#id'. No randomness, no time-dependent decisions
(a generated_at timestamp is written on purpose: raw files differ, extracted fields must not)."""
import json, sys, time, pathlib
from lxml import html as LH

def style(el):
    return dict((k.strip().lower(), v.strip().lower()) for k, v in (p.split(":", 1) for p in (el.get("style") or "").split(";") if ":" in p))

def main(fixture, out):
    root = LH.fromstring(pathlib.Path(fixture).read_bytes())
    order = {el: i for i, el in enumerate(root.iter())}
    task = root.xpath('//*[@data-c-control="task-entry"]')[0]
    conts = [el for el in root.iter() if isinstance(el.tag, str) and style(el).get("position") in ("fixed", "sticky") and el is not task and task not in el.iter()]
    steps = []
    for c in sorted(conts, key=lambda c: (-int(style(c).get("z-index", "0") or 0), order[c])):
        btns = [b for b in c.iter("button") if "닫기" in (b.get("aria-label") or "") + "".join(b.itertext())]
        if btns:
            steps.append({"action_token": "DISMISS_OBSTRUCTION", "control_selector": "#" + btns[0].get("id")})
    steps.append({"action_token": "SELECT_FUNCTION", "control_selector": "#" + task.get("id")})
    steps.append({"action_token": "ENDPOINT_REACHED", "control_selector": None})
    doc = {"runner": "fake_runner_det", "generated_at": time.time(), "fixture": pathlib.Path(fixture).name,
           "task_flow_sequence": [s["action_token"] for s in steps if s["action_token"] != "DISMISS_OBSTRUCTION"],
           "experienced_flow_sequence": [s["action_token"] for s in steps], "steps": steps}
    pathlib.Path(out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    try:
        _rc = main(sys.argv[1], sys.argv[2])
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("fake_runner_det: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
