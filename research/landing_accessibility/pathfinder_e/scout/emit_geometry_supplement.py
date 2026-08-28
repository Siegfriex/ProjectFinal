"""A(T-A-V3-TBX-016): entry_x_norm/entry_control_type 0/35 결측 보완.

R1/R2 실행분은 selected_candidate 를 저장하지 않는 구현 결함이 있었다(수정: R3).
R3 에서 실제로 후보를 선택/클릭한 8개 target(ENDPOINT_REACHED 6 + AUTH_GATE 2)만
bbox 원자료가 있다. 나머지 target 은 애초에 후보를 못 찾았으므로 entry position 자체가
NOT_OBSERVED 인 게 맞는 값이다(지어내지 않는다).

이 파일은 EVIDENCE_MANIFEST.jsonl 의 해시체인 계약 밖의 보조 산출물이라, target_id 당
정확히 1행이 되도록 매번 깨끗하게 재생성한다(append-only 불변 대상 아님 — B/C 에 명시).
"""
from __future__ import annotations

import json
from pathlib import Path

RAW_ROOT = Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/v3_census/raw")
OUT_PATH = RAW_ROOT / "GEOMETRY_SUPPLEMENT_E.jsonl"
VIEWPORT_W, VIEWPORT_H = 390, 844

R3_TARGETS = ["F1-03", "F5-02", "F5-05", "F2-01", "F2-08", "F3-06", "F1-05", "F3-02"]
R3_RUN = RAW_ROOT / "E" / "E-REAL-CENSUS-1230-R3"


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


def control_type(role_or_tag: str | None, visible_label: str | None) -> str:
    role = (role_or_tag or "").lower()
    if role == "a":
        return "TEXT_LINK" if visible_label else "ICON_ONLY"
    if role == "button":
        return "ICON_TEXT" if visible_label else "ICON_ONLY"
    if "menuitem" in role:
        return "LIST_ITEM"
    if "tab" in role:
        return "TAB"
    return "OTHER"


def geometry_for(tid: str, evidence_dir: Path) -> dict:
    trace_path = evidence_dir / f"E_SCOUT_TRACE_{tid}.jsonl"
    base = {"target_id": tid, "evidence_dir": str(evidence_dir)}
    if not trace_path.exists():
        return {**base, "entry_x_norm": None, "entry_y_norm": None, "entry_zone": "NOT_OBSERVED",
                "entry_control_type": "NOT_OBSERVED", "missing_reason": "no_trace_file"}

    states = [json.loads(l) for l in trace_path.open(encoding="utf-8")]
    target_state = next(
        (s for s in states if s.get("action_token") == "SELECT_FUNCTION" and s.get("selected_candidate")),
        None,
    )
    if target_state is None:
        return {**base, "entry_x_norm": None, "entry_y_norm": None, "entry_zone": "NOT_OBSERVED",
                "entry_control_type": "NOT_OBSERVED",
                "missing_reason": "no_candidate_selected_in_trace collector 가 task-entry control 을 못 찾음"}

    cand = target_state["selected_candidate"]
    bbox = cand.get("bbox")
    if not bbox:
        return {**base, "entry_x_norm": None, "entry_y_norm": None, "entry_zone": "NOT_OBSERVED",
                "entry_control_type": control_type(cand.get("role_or_tag"), cand.get("visible_label")),
                "missing_reason": "bbox_null_element_not_visible_at_capture"}

    cx = bbox["x"] + bbox["width"] / 2
    cy = bbox["y"] + bbox["height"] / 2
    x_norm = max(0.0, min(1.0, cx / VIEWPORT_W))
    y_norm = max(0.0, min(1.0, cy / VIEWPORT_H))
    return {**base, "entry_x_norm": round(x_norm, 4), "entry_y_norm": round(y_norm, 4),
            "entry_zone": entry_zone(x_norm, y_norm),
            "entry_control_type": control_type(cand.get("role_or_tag"), cand.get("visible_label")),
            "source_state_id": target_state.get("state_id"), "missing_reason": None}


def main() -> None:
    manifest = [json.loads(l) for l in (RAW_ROOT / "EVIDENCE_MANIFEST.jsonl").open(encoding="utf-8")]
    by_target: dict[str, dict] = {}
    for rec in manifest:
        by_target[rec["target_id"]] = rec  # 마지막(최신) 줄 우선 — R2 가 R1 을 덮는 순서와 일치

    rows = []
    for tid, rec in sorted(by_target.items()):
        evidence_dir = R3_RUN / tid if tid in R3_TARGETS else Path(rec["evidence_dir"])
        rows.append(geometry_for(tid, evidence_dir))

    with OUT_PATH.open("w", encoding="utf-8") as out:
        for r in rows:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_ok = sum(1 for r in rows if r["entry_x_norm"] is not None)
    print(f"wrote {len(rows)} lines ({n_ok} with geometry, {len(rows) - n_ok} NOT_OBSERVED) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
