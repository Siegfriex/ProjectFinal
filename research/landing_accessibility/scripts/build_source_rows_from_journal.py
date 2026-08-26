"""C009(D5) — 261행 원자료를 판독 저널에서 재생성한다.

C002 산출물(`state/source_ranking_rows.parquet`, `state/panel_registry.parquet`)은
figure 판독 결과만 커밋돼 있어 산출물로부터 재현이 불가능했다. 감사 지적 D5 를 받아
판독이 실제로 일어난 워크플로 저널을 입력으로 삼는 재생성 경로를 코드로 남긴다.

입력 (읽기 전용):
    sources/wiseapp/extraction_journal/wf_bc403111-047_journal.jsonl
        figure 11종의 판독 결과(figure_id 보유) + 교차검증 결과(agrees 보유).
        C011(P2-3): 이 저널은 세션 경로에만 있어 clone 만으로는 261행 재현이 불가능했다.
        저장소 안으로 옮기고 sha256 을 source_evidence_manifest.json 에 등록했다.
        --journal 로 다른 경로를 지정할 수 있으나 기본값은 저장소 내부다.
        저널이 없으면 스크립트는 실패하며, 기존 산출물을 덮어쓰지 않는다.

실행 순서 (C011/P2-4) — 이 스크립트가 먼저다
    1) build_source_rows_from_journal.py   저널 → source_ranking_rows + panel_registry
    2) build_canonical_entities.py         위 두 산출물 → service_master / alias / membership /
                                           web_target_group, 그리고 panel_registry 에 panel_scope 를 얹는다
    panel_scope 의 소유자는 (2) 다. (1)을 단독 실행해도 (2)가 얹어 둔 panel_scope 를
    기존 panel_registry 에서 이어받아 스키마(26컬럼)를 깨지 않는다 — 그 컬럼이 사라지면
    test_axis_type_separates_industry_categories 가 깨진다는 사실을 감사가 실증했다.

출력:
    state/source_ranking_rows.parquet / .csv   261행 (+ axis_type, figure_source_pointer)
    state/panel_registry.parquet / .csv        17패널 (판독 저널 기반 필드 + C009 스키마)
    state/journal_provenance.json              저널 → 행 매핑 요약 (schema v3)

C012(D3) — 산출물에 절대경로를 적지 않는다
    v2 의 journal_provenance.json 은 `journal_path` 에 실행자 워크트리 절대경로를 적었다.
    그래서 "두 빌드 스크립트를 재실행하면 diff -r 이 바이트 동일" 이라는 C011 보고는 **같은
    워크트리에서만** 참이었다. 다른 clone 에서 재실행하면 그 1줄이 어긋난다.
    v3 은 `journal_path_in_repo`(저장소 상대경로)만 남기고, 절대경로는 실행 시점에만 존재하는
    값으로 `path_policy.resolved_at_runtime` 에 이름만 선언한다. 저널이 저장소 밖이면 실패한다.

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

# C011(P2-3): 저널을 저장소 안에 둔다. 세션 경로 의존은 단일 머신 재현성 함정이었다.
DEFAULT_JOURNAL = (
    ROOT / "sources" / "wiseapp" / "extraction_journal" / "wf_bc403111-047_journal.jsonl"
)

# panel_registry 에서 이 스크립트가 만들지 않는 컬럼 — 소유자는 build_canonical_entities.py 다.
# 단독 실행 시 기존 산출물에서 이어받아 스키마를 보존한다(C011/P2-4).
DOWNSTREAM_PANEL_COLUMNS = ("panel_scope",)

EXPECTED_ROWS = 261
EXPECTED_PANELS = 17
EXPECTED_FIGURES = 11

# ── C011(P1-3) 원문 INDEX 절 제목 — raw/wiseapp933_text.txt 본문 문자열 그대로다. ──
# C009 판본은 코호트 한정어 '액티브시니어+ 세대' 를 11개 절 전부에서 지웠고 Ch3(2)는
# 어순까지 바꿔 적었다. 그래서 "원문 index 와 1:1 대조" 라는 주장은 성립하지 않았다 —
# 실제로 대조된 것은 authority_manifest(파생 A) 와 panel_registry(파생 B) 였다.
# 파생물끼리의 일치는 검증이 아니다. 이제 두 파생물 모두 원문 본문을 복사한다.
# 원문 대조는 tests/test_c009_two_layer.py 가 raw/wiseapp933_text.txt 를 직접 파싱해 수행한다.
FIGURE_SECTION: dict[str, tuple[int, int, str]] = {
    # Chapter 1 의 세 절만 '세대' 뒤가 U+00A0(non-breaking space) 다. 원문 그대로 옮긴다 —
    # 눈에 보이지 않는 차이라도 verbatim 은 verbatim 이다.
    "fig01": (1, 1, "(1) 액티브시니어+ 세대\u00a0앱 사용자 및 사용시간 평균 TOP15"),
    "fig02": (1, 2, "(2) 액티브시니어+ 세대\u00a0앱 사용자 점유율 순위 TOP15"),
    "fig03": (1, 3, "(3) 액티브시니어+ 세대\u00a0앱 사용자 성장률 순위 TOP10"),
    "fig04": (2, 1, "(1) 액티브시니어+ 세대 앱 사용자 비율이 높은 주요 금융 앱"),
    "fig05": (2, 2, "(2) 액티브시니어+ 세대 앱 사용자가 많이 성장한 주요 쇼핑 앱"),
    "fig06": (3, 1, "(1) 액티브시니어+ 세대 순 결제추정금액 합 인덱스 및 총 결제횟수 평균 TOP15"),
    "fig07": (3, 2, "(2) 업종별 액티브시니어+ 세대 순 결제추정금액 TOP10"),
    "fig08": (3, 3, "(3) 액티브시니어+ 세대 순 결제추정금액 점유율 순위 TOP10"),
    "fig09": (3, 4, "(4) 액티브시니어+ 세대 순 결제추정금액 성장률 TOP5"),
    "fig10": (4, 1, "(1) 액티브시니어+ 세대 순 결제추정금액 비율이 높은 주요 홈쇼핑 리테일 브랜드"),
    "fig11": (
        4,
        2,
        "(2) 액티브시니어+ 세대 순 결제추정금액이 많이 성장한 주요 오프라인 마트 리테일 브랜드",
    ),
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
                            # C011(P2-5): 축 컬럼 중 axis_type 만 행에 전파돼 있었다.
                            # '성장률' 은 fig05_t1(HALF_YEAR)과 fig07_t1(SINGLE_MONTH)에
                            # 동시에 존재하는 유일한 metric_name 이라, 행 수준에서 기간 축이
                            # 없으면 metric_name 만으로 집계할 때 두 기간이 섞인다.
                            "period_label": period_label,
                            "period_axis": period_axis,
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

    # ── panel_scope 이어받기 (C011/P2-4) ─────────────────────────────────────
    # 이 스크립트를 단독으로 돌리면 panel_registry 가 26 → 25 컬럼이 되어 panel_scope 가
    # 사라지고 test_axis_type_separates_industry_categories 가 FAILED 했다(감사자 실증).
    # 소유자는 build_canonical_entities.py 지만, 단독 실행이 스키마를 깨지 않도록 이어받는다.
    carried: list[str] = []
    panel_registry_path = STATE / "panel_registry.parquet"
    if panel_registry_path.exists():
        prev = pd.read_parquet(panel_registry_path)
        for col in DOWNSTREAM_PANEL_COLUMNS:
            if col in prev.columns and col not in panels.columns:
                mapping = dict(zip(prev["panel_id"], prev[col], strict=True))
                panels[col] = panels["panel_id"].map(mapping)
                carried.append(col)
    missing_downstream = [c for c in DOWNSTREAM_PANEL_COLUMNS if c not in panels.columns]
    if missing_downstream:
        print(
            f"[주의] panel_registry 에 {missing_downstream} 가 없다. "
            "build_canonical_entities.py 를 이어서 실행해야 스키마가 완성된다."
        )

    # ── 기존 산출물과의 실제 동등성 비교 (C011/P2-4) ──────────────────────────
    # C009 판본은 `matches_existing_c002_output: existing.exists()` 였다. 파일이 있기만 하면
    # True 를 적었으므로 '재생성이 기존 산출물과 일치한다' 는 주장을 전혀 검증하지 않았다.
    # 감사 지적: 테스트가 통과를 위장했다. 이제 assert_frame_equal 로 실제 비교한다.
    existing = STATE / "source_ranking_rows.parquet"
    comparison: dict[str, Any] = {
        "compared": False,
        "method": "NO_EXISTING_OUTPUT",
        "columns_compared": [],
        "columns_only_in_existing": [],
        "columns_new_in_rebuild": sorted(rows.columns),
        "result": None,
    }
    if existing.exists():
        old = pd.read_parquet(existing)
        shared = [c for c in old.columns if c in rows.columns]
        left = old[shared].sort_values("source_row_id", ignore_index=True)
        right = rows[shared].sort_values("source_row_id", ignore_index=True)
        try:
            pd.testing.assert_frame_equal(left, right, check_dtype=False, check_like=False)
        except AssertionError as exc:
            raise SystemExit(
                f"저널 재생성 결과가 기존 C002 원자료와 다르다 (공통 {len(shared)}컬럼 비교)\n{exc}"
            ) from exc
        comparison = {
            "compared": True,
            "method": (
                "pandas.testing.assert_frame_equal(check_dtype=False) "
                "on shared columns sorted by source_row_id"
            ),
            "columns_compared": shared,
            "columns_only_in_existing": sorted(set(old.columns) - set(rows.columns)),
            "columns_new_in_rebuild": sorted(set(rows.columns) - set(old.columns)),
            "result": "IDENTICAL",
        }

    # C012(D3): 산출물에 실행자 워크트리 절대경로를 적지 않는다.
    #   C011 은 "두 빌드 스크립트를 재실행하면 diff -r 이 바이트 동일" 이라고 보고했으나
    #   journal_path 가 절대경로라 다른 워크트리·다른 clone 에서 재실행하면 이 1줄이 어긋난다.
    #   나머지 15개 산출물은 실제로 바이트 동일했으므로, 거짓이 된 것은 데이터가 아니라 주장이다.
    #   절대경로는 실행 시점에만 존재하는 값이므로 기록하지 않고, 기록하지 않았다는 사실만 남긴다.
    journal_path = args.journal.resolve()
    repo_root = ROOT.parents[1]
    try:
        journal_rel = str(journal_path.relative_to(repo_root))
    except ValueError as exc:
        raise SystemExit(
            f"저널이 저장소 밖에 있다: {journal_path}\n"
            f"provenance 는 저장소 상대경로만 기록한다 — 저장소 안의 저널을 지정하라."
        ) from exc

    provenance = {
        "schema": "journal_provenance/v3",
        "generated_by": "research/landing_accessibility/scripts/build_source_rows_from_journal.py",
        "path_policy": {
            "absolute_paths_recorded": False,
            "resolved_at_runtime": ["journal_path"],
            "reason": (
                "절대경로를 산출물에 적으면 실행 위치가 산출물의 일부가 되어 재실행 바이트 "
                "동일성이 성립하지 않는다(C011 P2 idempotency-claim-false-journal-path-absolute). "
                "저장소 상대경로만 기록한다."
            ),
        },
        "journal_path_in_repo": journal_rel,
        "journal_sha256": hashlib.sha256(args.journal.read_bytes()).hexdigest(),
        "journal_bytes": len(args.journal.read_bytes()),
        "figures_read": sorted(readings),
        "cross_verifications": len(verifications),
        "cross_verifications_agreeing": sum(1 for v in verifications if v.get("agrees")),
        "rows_rebuilt": len(rows),
        "panels_rebuilt": len(panels),
        "row_id_formula": "row_ + sha256('{panel_id}|{rank}|{entity_name_raw}|{metric_name}')[:16]",
        "row_pointer_format": "<figure_id>#t<table_index>/rank<rank>/<metric_name>",
        "build_order": [
            "scripts/build_source_rows_from_journal.py",
            "scripts/build_canonical_entities.py",
        ],
        "panel_columns_carried_from_downstream": carried,
        "matches_existing_c002_output": comparison,
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
