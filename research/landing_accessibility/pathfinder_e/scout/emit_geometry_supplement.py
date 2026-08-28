"""A(T-A-V3-TBX-016): entry_x_norm/entry_control_type 0/35 결측 보완.

내 trace JSONL 에 selected_candidate.bbox 가 이미 있다 — B 의 사후 DOM 추출과 별개로,
1차 관측 시점의 원자료에서 직접 계산해 append-only supplement 로 낸다. 기존 manifest
줄은 건드리지 않는다(불변). B/C 가 target_id 로 join.
"""
from __future__ import annotations

import json
from pathlib import Path

RAW_ROOT = Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/v3_census/raw")
OUT_PATH = RAW_ROOT / "GEOMETRY_SUPPLEMENT_E.jsonl"
VIEWPORT_W, VIEWPORT_H = 390, 844


def entry_zone(x_norm: float, y_norm: float) -> str:
    if y_norm < 1 / 3:
        band = "TOP"
    elif y_norm < 2 / 3:
        return "MID"
    else:
        return "BOTTOM"
    if x_norm < 1 / 3:
        return f"{band}_LEFT"
    elif x_norm < 2 / 3:
        return f"{band}_CENTER"
    return f"{band}_RIGHT"


def control_type(role_or_tag: str, visible_label: str | None) -> str:
    role = (role_or_tag or "").lower()
    if role in ("a",):
        return "TEXT_LINK" if visible_label else "ICON_ONLY"
    if role in ("button",):
        return "ICON_TEXT" if visible_label else "ICON_ONLY"
    if "menuitem" in role:
        return "LIST_ITEM"
    if "tab" in role:
        return "TAB"
    return "OTHER"


def main() -> None:
    manifest = [json.loads(l) for l in (RAW_ROOT / "EVIDENCE_MANIFEST.jsonl").open(encoding="utf-8")]
    seen = set()
    written = 0
    with OUT_PATH.open("w", encoding="utf-8") as out:
        for rec in manifest:
            tid = rec["target_id"]
            key = (tid, rec["evidence_dir"])
            if key in seen:
                continue
            seen.add(key)
            trace_path = Path(rec["evidence_dir"]) / f"E_SCOUT_TRACE_{tid}.jsonl"
            if not trace_path.exists():
                continue
            states = [json.loads(l) for l in trace_path.open(encoding="utf-8")]
            # SELECT_FUNCTION action 을 낸 state 우선, 없으면 마지막 selected_candidate 있는 state
            target_state = None
            for s in states:
                if s.get("action_token") == "SELECT_FUNCTION" and s.get("selected_candidate"):
                    target_state = s
            if target_state is None:
                for s in reversed(states):
                    if s.get("selected_candidate"):
                        target_state = s
                        break
            if target_state is None:
                out.write(json.dumps({
                    "target_id": tid, "evidence_dir": rec["evidence_dir"],
                    "entry_x_norm": None, "entry_y_norm": None, "entry_zone": "NOT_OBSERVED",
                    "entry_control_type": "NOT_OBSERVED",
                    "missing_reason": "no_candidate_selected_in_trace",
                }, ensure_ascii=False) + "\n")
                written += 1
                continue

            cand = target_state["selected_candidate"]
            bbox = cand.get("bbox")
            if not bbox:
                out.write(json.dumps({
                    "target_id": tid, "evidence_dir": rec["evidence_dir"],
                    "entry_x_norm": None, "entry_y_norm": None, "entry_zone": "NOT_OBSERVED",
                    "entry_control_type": control_type(cand.get("role_or_tag"), cand.get("visible_label")),
                    "missing_reason": "bbox_null_element_not_visible_at_capture",
                }, ensure_ascii=False) + "\n")
                written += 1
                continue

            cx = bbox["x"] + bbox["width"] / 2
            cy = bbox["y"] + bbox["height"] / 2
            x_norm = max(0.0, min(1.0, cx / VIEWPORT_W))
            y_norm = max(0.0, min(1.0, cy / VIEWPORT_H))
            out.write(json.dumps({
                "target_id": tid, "evidence_dir": rec["evidence_dir"],
                "entry_x_norm": round(x_norm, 4), "entry_y_norm": round(y_norm, 4),
                "entry_zone": entry_zone(x_norm, y_norm),
                "entry_control_type": control_type(cand.get("role_or_tag"), cand.get("visible_label")),
                "source_state_id": target_state.get("state_id"),
                "missing_reason": None,
            }, ensure_ascii=False) + "\n")
            written += 1
    print(f"wrote {written} lines -> {OUT_PATH}")


if __name__ == "__main__":
    main()
