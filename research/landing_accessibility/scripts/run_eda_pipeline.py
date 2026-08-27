#!/usr/bin/env python3
"""EDA-03~08 파이프라인 CLI — 목표 2.

synthetic universe로 marts를 만들고 EDA-03~08을 전부 돌린다. `--empty`를 주면
빈 입력으로 돌려 (c) 빈 입력 안전성을 직접 확인할 수 있다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # research/landing_accessibility


from analysis.eda import RUNNERS
from analysis.marts.builders import BUILDERS
from analysis.marts.synthetic import generate_synthetic_universe
from analysis.provenance import ShadowProvenance


def _split_batches_dirs(raw: list[str] | None) -> list[str] | None:
    """`--batches-dir`를 반복 지정 + 콤마 구분 양쪽으로 받는다."""
    if not raw:
        return None
    out: list[str] = []
    for item in raw:
        out.extend(part.strip() for part in item.split(",") if part.strip())
    return out or None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="artifacts/analysis_current/eda")
    parser.add_argument("--n-services", type=int, default=24)
    parser.add_argument("--empty", action="store_true")
    parser.add_argument(
        "--batches-dir",
        action="append",
        default=None,
        help="batch_*.json 디렉터리. 반복 지정 가능하며 콤마 구분도 허용한다(워커별 디렉터리).",
    )
    parser.add_argument(
        "--allow-cross-cohort",
        action="store_true",
        help="E000/E001처럼 execution_scope가 다른 배치를 명시적으로 합산한다(기본은 분리).",
    )
    args = parser.parse_args()
    batches_dirs = _split_batches_dirs(args.batches_dir)

    if args.empty:
        rows_by_table = {name: [] for name in BUILDERS}
    else:
        rows_by_table = generate_synthetic_universe(n_services=args.n_services).as_dict()

    marts = {table: BUILDERS[table](rows).frame for table, rows in rows_by_table.items()}
    provenance = ShadowProvenance(source_kind="EMPTY" if args.empty else "SYNTHETIC")

    for key, runner in RUNNERS.items():
        out = Path(args.out_dir) / key
        paths = (
            runner(
                marts,
                out,
                provenance=provenance,
                batches_dir=batches_dirs,
                allow_cross_cohort=args.allow_cross_cohort,
            )
            if key == "eda09"
            else runner(marts, out, provenance=provenance)
        )
        print(f"{key}: {paths.summary_json_path}")


if __name__ == "__main__":
    main()
