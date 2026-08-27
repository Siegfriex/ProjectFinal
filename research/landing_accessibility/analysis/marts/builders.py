"""fact/dim mart 빌드 스크립트 — 스키마 검증 → `pandas.DataFrame` → parquet/csv 기록.

목표 1의 (a)(b)(c)를 여기서 충족한다.

  (a) 스키마 검증 — `schema.validate_rows`로 매 행을 검사하고, 위반이 있으면
      `MartBuildError`로 산출을 실패시킨다 (A2 규칙 S-3 — 조용히 흡수하지 않는다).
  (b) synthetic/fixture 입력에 대해 정상 동작 — `marts/synthetic.py`가 만든 행을
      그대로 통과시킨다 (`tests/test_analysis_marts.py`가 증명한다).
  (c) 빈 입력에도 안전 — 빈 리스트를 넣으면 에러 없이 컬럼만 있는 빈 mart를 만든다.

이 모듈은 실제 서비스 데이터를 읽지 않는다. 입력은 항상 호출자가 만든 행 리스트다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .schema import TABLE_SCHEMAS, column_names, validate_rows


class MartBuildError(ValueError):
    """스키마 검증 실패 — 산출을 실패시킨다 (조용히 흡수하지 않는다, A2 규칙 S-3)."""


@dataclass(frozen=True)
class MartBuildResult:
    table: str
    frame: pd.DataFrame
    row_count: int
    empty_input: bool


def build_mart(table: str, rows: list[dict[str, Any]]) -> MartBuildResult:
    """제네릭 mart 빌더. 빈 입력이면 컬럼만 있는 빈 `DataFrame`을 돌려준다."""
    if table not in TABLE_SCHEMAS:
        raise MartBuildError(f"알 수 없는 표: {table!r}")

    if not rows:
        empty = pd.DataFrame(columns=column_names(table))
        return MartBuildResult(table=table, frame=empty, row_count=0, empty_input=True)

    errors = validate_rows(table, rows)
    if errors:
        preview = "\n".join(f"  - {e}" for e in errors[:20])
        more = "" if len(errors) <= 20 else f"\n  ... 외 {len(errors) - 20}건"
        raise MartBuildError(f"{table}: 스키마 검증 실패 {len(errors)}건\n{preview}{more}")

    frame = pd.DataFrame(rows)
    # 스키마에 있는 컬럼은 값이 한 행도 없어도 열로는 존재하게 한다 (분석 스크립트가
    # `df["col"]`을 항상 안전하게 참조할 수 있도록).
    for name in column_names(table):
        if name not in frame.columns:
            frame[name] = pd.NA
    ordered = column_names(table)
    extra = [c for c in frame.columns if c not in ordered]
    frame = frame[ordered + extra]
    return MartBuildResult(table=table, frame=frame, row_count=len(frame), empty_input=False)


def write_mart(result: MartBuildResult, out_dir: str | Path) -> dict[str, Path]:
    """mart를 parquet + csv로 쓰고 경로를 돌려준다. 빈 mart도 정상적으로 쓴다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{result.table}.csv"
    parquet_path = out_dir / f"{result.table}.parquet"
    result.frame.to_csv(csv_path, index=False)
    result.frame.to_parquet(parquet_path, index=False)
    return {"csv": csv_path, "parquet": parquet_path}


# ── 표별 얇은 래퍼 — 오케스트레이터 지시가 표 이름으로 개별 스크립트를 요구했으므로 둔다.
def build_fact_landing_observation(rows: list[dict[str, Any]]) -> MartBuildResult:
    return build_mart("fact_landing_observation", rows)


def build_fact_task_entry(rows: list[dict[str, Any]]) -> MartBuildResult:
    return build_mart("fact_task_entry", rows)


def build_fact_task_step(rows: list[dict[str, Any]]) -> MartBuildResult:
    return build_mart("fact_task_step", rows)


def build_fact_interrupt_element(rows: list[dict[str, Any]]) -> MartBuildResult:
    return build_mart("fact_interrupt_element", rows)


def build_fact_criterion_result(rows: list[dict[str, Any]]) -> MartBuildResult:
    return build_mart("fact_criterion_result", rows)


def build_fact_ai_adjudication(rows: list[dict[str, Any]]) -> MartBuildResult:
    return build_mart("fact_ai_adjudication", rows)


def build_dim_certification(rows: list[dict[str, Any]]) -> MartBuildResult:
    return build_mart("dim_certification", rows)


BUILDERS = {
    "fact_landing_observation": build_fact_landing_observation,
    "fact_task_entry": build_fact_task_entry,
    "fact_task_step": build_fact_task_step,
    "fact_interrupt_element": build_fact_interrupt_element,
    "fact_criterion_result": build_fact_criterion_result,
    "fact_ai_adjudication": build_fact_ai_adjudication,
    "dim_certification": build_dim_certification,
}
