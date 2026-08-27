#!/usr/bin/env python3
"""fake_runner_rand.py FIXTURE OUT — fake runner that INJECTS RANDOMNESS (negative control for determinism_check).
Same page reading as fake_runner_det, but: (1) selector form for each control is chosen at random among 3
equivalent forms (unstated tie-break), (2) dismissal order of equally-ranked containers is shuffled,
(3) OPEN_GLOBAL_MENU is inserted with p=0.5 (unstated stop condition). Seeded from os.urandom — no fixed seed.
P(3 runs identical) is < 1/1000 for f04, so a PASS from this runner would indicate a broken check."""
import json, os, random, sys, time, pathlib
from lxml import html as LH
rng = random.Random(int.from_bytes(os.urandom(8), "big"))

def style(el):
    return dict((k.strip().lower(), v.strip().lower()) for k, v in (p.split(":", 1) for p in (el.get("style") or "").split(";") if ":" in p))

def sel_forms(el):
    i = el.get("id"); tag = el.tag
    return ["#" + i, f'{tag}[id="{i}"]', f"{tag}#{i}"]

def main(fixture, out):
    root = LH.fromstring(pathlib.Path(fixture).read_bytes())
    task = root.xpath('//*[@data-c-control="task-entry"]')[0]
    conts = [el for el in root.iter() if isinstance(el.tag, str) and style(el).get("position") in ("fixed", "sticky") and el is not task and task not in el.iter()]
    rng.shuffle(conts)                                    # (2) unstated ordering
    steps = []
    for c in conts:
        btns = [b for b in c.iter("button") if "닫기" in (b.get("aria-label") or "") + "".join(b.itertext())]
        if btns:
            steps.append({"action_token": "DISMISS_OBSTRUCTION", "control_selector": rng.choice(sel_forms(btns[0]))})  # (1)
    if rng.random() < 0.5:                                # (3) unstated detour
        steps.append({"action_token": "OPEN_GLOBAL_MENU", "control_selector": "#menu"})
    steps.append({"action_token": "SELECT_FUNCTION", "control_selector": rng.choice(sel_forms(task))})
    steps.append({"action_token": "ENDPOINT_REACHED", "control_selector": None})
    doc = {"runner": "fake_runner_rand", "generated_at": time.time(), "fixture": pathlib.Path(fixture).name,
           "task_flow_sequence": [s["action_token"] for s in steps if s["action_token"] != "DISMISS_OBSTRUCTION"],
           "experienced_flow_sequence": [s["action_token"] for s in steps], "steps": steps}
    pathlib.Path(out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
