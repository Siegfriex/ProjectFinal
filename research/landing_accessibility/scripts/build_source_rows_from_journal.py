"""C009(D5) — 261행 원자료를 판독 저널에서 재생성한다.

C002 산출물(`state/source_ranking_rows.parquet`, `state/panel_registry.parquet`)은
figure 판독 결과만 커밋돼 있어 산출물로부터 재현이 불가능했다. 감사 지적 D5 를 받아
판독이 실제로 일어난 워크플로 저널을 입력으로 삼는 재생성 경로를 코드로 남긴다.

입력 (읽기 전용):
    저널 JSONL — figure 11종의 판독 결과(figure_id 보유) + 교차검증 결과(agrees 보유)
    기본 경로는 --journal 로 덮어쓸 수 있다. 저널이 없으면 스크립트는 실패하며,
    기존 산출물을 덮어쓰지 않는다.

출력:
    state/source_ranking_rows.parquet / .csv   261행 (+ axis_type, figure_source_pointer)
    state/panel_registry.parquet / .csv        17패널 (판독 저널 기반 필드 + C009 스키마)
    state/journal_provenance.json              저널 → 행 매핑 요약

행별 출처 포인터
    각 행에 `figure_source_pointer` 를 남긴다. 형식:
        `<figure_id>#t<table_index>/rank<rank>/<metric_name>`
    이 포인터는 `sources/wiseapp/images/<figure_id>.png` 의 어느 표·어느 순위·어느 지표를
    읽은 값인지를 가리킨다. figure_id 는 source_evidence_manifest.json 의 sha256 로 고정돼 있다.

불변식
    - 행 수는 261 이어야 한다.
    - source_row_id = 'row_' + sha256(f"{panel_id}|{rank}|{entity_name_raw}|{metric_name}")[:16]
      기존 C002 산출물과 동일한 식이며, 재생성 결과가 기존 id 와 어긋나면 실패한다(--check).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"

DEFAULT_JOURNAL = Path(
    "/home/sieg/.claude/projects/-home-sieg-projects-wsl-ProjectFinal/"
    "11974cfd-b959-4a0e-9910-610e70f08ac8/subagents/workflows/wf_bc403111-047/journal.jsonl"
)

EXPECTED_ROWS = 261
EXPECTED_PANELS = 17
EXPECTED_FIGURES = 11

# ── C009(D3) 원문 index 와 1:1 대조가 끝난 장·절. 더 이상 추측이 아니다. ──────
# authority_manifest.json 의 index_from_source 와 figure 순서를 대조한 결과다.
FIGURE_SECTION: dict[str, tuple[int, int, str]] = {
    "fig01": (1, 1, "(1) 앱 사용자 및 사용시간 평균 TOP15"),
    "fig02": (1, 2, "(2) 앱 사용자 점유율 순위 TOP15"),
    "fig03": (1, 3, "(3) 앱 사용자 성장률 순위 TOP10"),
    "fig04": (2, 1, "(1) 사용자 비율이 높은 주요 금융 앱"),
    "fig05": (2, 2, "(2) 사용자가 많이 성장한 주요 쇼핑 앱"),
    "fig06": (3, 1, "(1) 순 결제추정금액 합 인덱스 및 총 결제횟수 평균 TOP15"),
    "fig07": (3, 2, "(2) 업종별 순 결제추정금액 TOP10"),
    "fig08": (3, 3, "(3) 순 결제추정금액 점유율 순위 TOP10"),
    "fig09": (3, 4, "(4) 순 결제추정금액 성장률 TOP5"),
    "fig10": (4, 1, "(1) 순 결제추정금액 비율이 높은 주요 홈쇼핑 리테일 브랜드"),
    "fig11": (4, 2, "(2) 순 결제추정금액이 많이 성장한 주요 오프라인 마트 리테일 브랜드"),
}

CHAPTER_TITLE: dict[int, str] = {
    1: "25년 하반기 액티브시니어+ 세대 앱 동향",
    2: "25년 하반기 액티브시니어+ 세대가 많이 사용한 앱",
    3: "25년 하반기 액티브시니어+ 세대 결제 동향",
    4: "25년 하반기 액티브시니어+ 세대가 많이 결제한 리테일 브랜드",
}

# ── C009(D1/D7) 축 유형 — fig07_t1 만 업종 축이다 (COR-002 판독 근거) ────────
INDUSTRY_AXIS_PANELS = {"fig07_t1"}

# ── C009(D4) 원문이 TOP N 을 선언한 패널과, 표기 없이 시각 계수만 가능한 패널 ──
# 선언 패널은 rows_expected 를 원문에서 읽었으므로 rows_extracted 와의 일치가 검증력을 갖는다.
# 미선언 패널은 rows_expected 를 판독 행 수로 채웠을 뿐이라 항상 참이다 → 통과로 계상하지 않는다.
DECLARED_TOP_N_PANELS = {
    "fig01_t1",
    "fig01_t2",
    "fig02_t1",
    "fig03_t1",
    "fig06_t1",
    "fig06_t2",
    "fig07_t1",
    "fig08_t1",
    "fig09_t1",
}

# ── C009(B2) fig07 기간 축 시정 ─────────────────────────────────────────────
# alt 텍스트는 '25년 하반기' 로 적혀 있으나 본문은 '25년 12월 … 전년 동월 대비' 다.
# 본문(raw/wiseapp933_text.txt) 표기를 권위로 삼는다.
PERIOD_OVERRIDE: dict[str, tuple[str, str]] = {
    "fig07_t1": (
        "25년 12월 (전년 동월 24년 12월 대비)",
        "SINGLE_MONTH",
    ),
}
DEFAULT_PERIOD_AXIS = "HALF_YEAR"


def row_id(panel_id: str, rank: int, entity: str, metric: str) -> str:
    key = f"{panel_id}|{rank}|{entity}|{metric}"
    return "row_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def load_journal(path: Path) -> tuple[dict[str, dict], list[dict]]:
    """저널에서 (figure_id -> 판독결과, 교차검증결과 목록) 을 뽑는다."""
    if not path.exists():
        raise SystemExit(f"판독 저널이 없다: {path}")
    records = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    readings: dict[str, dict] = {}
    verifications: list[dict] = []
    for rec in records:
        result = rec.get("result")
        if not isinstance(result, dict):
            continue
        if "figure_id" in result:
            fid = result["figure_id"]
            if fid in readings and readings[fid] != result:
                raise SystemExit(f"{fid}: 저널에 서로 다른 판독 결과가 둘 이상 있다")
            readings[fid] = result
        elif "agrees" in result:
            verifications.append(result)
    if len(readings) != EXPECTED_FIGURES:
        raise SystemExit(f"figure 판독 결과가 {len(readings)}건이다 (기대 {EXPECTED_FIGURES})")
    return readings, verifications


def build(readings: dict[str, dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    row_recs: list[dict[str, Any]] = []
    panel_recs: list[dict[str, Any]] = []

    for figure_id in sorted(readings):
        fig = readings[figure_id]
        domain = fig["domain"]
        chapter, section, section_title = FIGURE_SECTION[figure_id]
        for table_index, table in enumerate(fig["tables"], 1):
            panel_id = f"{figure_id}_t{table_index}"
            axis_type = "INDUSTRY_CATEGORY" if panel_id in INDUSTRY_AXIS_PANELS else "SERVICE_BRAND"
            metrics = table["metric_columns"]
            period_label, period_axis = PERIOD_OVERRIDE.get(
                panel_id, (table["period_label"], DEFAULT_PERIOD_AXIS)
            )

            n_rows = 0
            for row in table["rows"]:
                for j, metric in enumerate(metrics):
                    # fig07_t1 성장률 7셀은 원문 이미지에 값이 렌더링돼 있지 않다(판독 불가).
                    # 판독자가 None 을 남겼고 value_labels 도 짧다. 결측을 결측으로 보존한다.
                    raw_value = row["values"][j]
                    labels = row["value_labels"]
                    row_recs.append(
                        {
                            "source_row_id": row_id(
                                panel_id, row["rank"], row["entity_name"], metric["name"]
                            ),
                            "panel_id": panel_id,
                            "figure_id": figure_id,
                            "domain": domain,
                            "axis_type": axis_type,
                            "table_title": table["table_title"],
                            "panel_label": table["panel_label"],
                            "rank": row["rank"],
                            "entity_name_raw": row["entity_name"],
                            "metric_name": metric["name"],
                            "unit": metric["unit"],
                            "value": float(raw_value) if raw_value is not None else float("nan"),
                            "value_label": labels[j] if j < len(labels) else None,
                            "figure_source_pointer": (
                                f"{figure_id}#t{table_index}/rank{row['rank']}/{metric['name']}"
                            ),
                        }
                    )
                    n_rows += 1

            declared = panel_id in DECLARED_TOP_N_PANELS
            panel_recs.append(
                {
                    "panel_id": panel_id,
                    "figure_id": figure_id,
                    "table_index": table_index,
                    "domain": domain,
                    "axis_type": axis_type,
                    "source_chapter": chapter,
                    "source_section": section,
                    "source_section_title": section_title,
                    "source_chapter_title": CHAPTER_TITLE[chapter],
                    "table_title": table["table_title"],
                    "subtitle": table.get("subtitle"),
                    "panel_label": table["panel_label"],
                    "period_label": period_label,
                    "period_axis": period_axis,
                    # C009(D4): 원문 미선언 패널은 rows_expected 를 비운다.
                    "rows_expected": pd.NA if not declared else int(table["rows_expected"]),
                    "rows_extracted": int(table["rows_extracted"]),
                    "row_count_verification": "DECLARED_TOP_N" if declared else "VISUAL_COUNT_ONLY",
                    "row_count_ok": (
                        pd.NA
                        if not declared
                        else bool(int(table["rows_expected"]) == int(table["rows_extracted"]))
                    ),
                    "metric_columns": json.dumps(metrics, ensure_ascii=False),
                    "n_metrics": len(metrics),
                    "universe_definition": fig.get("universe_definition"),
                    "source_note": fig.get("source_note"),
                    "footnotes": json.dumps(table.get("footnotes", []), ensure_ascii=False),
                    "extraction_confidence": fig.get("overall_confidence"),
                    "unreadable": json.dumps(
                        table.get("unreadable", fig.get("unreadable", [])), ensure_ascii=False
                    ),
                }
            )

    rows = pd.DataFrame(row_recs)
    panels = pd.DataFrame(panel_recs)
    panels["rows_expected"] = panels["rows_expected"].astype("Int64")
    panels["row_count_ok"] = panels["row_count_ok"].astype("boolean")
    return rows, panels


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    ap.add_argument(
        "--check",
        action="store_true",
        help="기존 산출물과 대조만 하고 쓰지 않는다",
    )
    args = ap.parse_args()

    readings, verifications = load_journal(args.journal)
    rows, panels = build(readings)

    if len(rows) != EXPECTED_ROWS:
        raise SystemExit(f"행 수가 {len(rows)} 다 (기대 {EXPECTED_ROWS})")
    if len(panels) != EXPECTED_PANELS:
        raise SystemExit(f"패널 수가 {len(panels)} 다 (기대 {EXPECTED_PANELS})")
    if rows["source_row_id"].duplicated().any():
        raise SystemExit("source_row_id 중복")

    existing = STATE / "source_ranking_rows.parquet"
    if existing.exists():
        old = pd.read_parquet(existing)
        shared = [c for c in old.columns if c in rows.columns]
        merged = old[shared].merge(rows[shared], on=shared, how="outer", indicator=True)
        drift = merged[merged["_merge"] != "both"]
        if not drift.empty:
            raise SystemExit(
                f"저널 재생성 결과가 기존 C002 원자료와 다르다 ({len(drift)}행)\n"
                f"{drift.head(10).to_string()}"
            )

    provenance = {
        "schema": "journal_provenance/v1",
        "generated_by": "research/landing_accessibility/scripts/build_source_rows_from_journal.py",
        "journal_path": str(args.journal),
        "journal_sha256": hashlib.sha256(args.journal.read_bytes()).hexdigest(),
        "figures_read": sorted(readings),
        "cross_verifications": len(verifications),
        "cross_verifications_agreeing": sum(1 for v in verifications if v.get("agrees")),
        "rows_rebuilt": len(rows),
        "panels_rebuilt": len(panels),
        "row_id_formula": "row_ + sha256('{panel_id}|{rank}|{entity_name_raw}|{metric_name}')[:16]",
        "row_pointer_format": "<figure_id>#t<table_index>/rank<rank>/<metric_name>",
        "matches_existing_c002_output": existing.exists(),
    }

    if args.check:
        print(json.dumps(provenance, ensure_ascii=False, indent=2))
        return

    rows.to_parquet(STATE / "source_ranking_rows.parquet", index=False)
    rows.to_csv(STATE / "source_ranking_rows.csv", index=False, encoding="utf-8-sig")
    panels.to_parquet(STATE / "panel_registry.parquet", index=False)
    panels.to_csv(STATE / "panel_registry.csv", index=False, encoding="utf-8-sig")
    (STATE / "journal_provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"source_ranking_rows : {len(rows)} 행")
    print(f"panel_registry      : {len(panels)} 패널")
    print(panels["row_count_verification"].value_counts().to_string())
    print(panels["period_axis"].value_counts().to_string())
    print(f"rows_expected null  : {int(panels['rows_expected'].isna().sum())} 패널")
    print(
        f"교차검증            : {provenance['cross_verifications_agreeing']}"
        f"/{provenance['cross_verifications']} agree"
    )


if __name__ == "__main__":
    main()
