#!/usr/bin/env python3
"""marts 빌드 CLI — 목표 1.

기본은 synthetic universe로 7개 mart를 빌드해 `--out-dir`에 parquet+csv로 쓴다.
`--empty`를 주면 모든 표를 빈 입력으로 빌드해 (c) 빈 입력 안전성을 직접 눈으로
확인할 수 있다.

이 스크립트는 실제 서비스 데이터를 읽지 않는다 (`PHASE_GATES.md §4.5`
`execution_mode=FIXTURE`에 해당).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # research/landing_accessibility

from analysis.marts.builders import BUILDERS, write_mart
from analysis.marts.synthetic import generate_synthetic_universe
from analysis.provenance import ShadowProvenance, write_provenance_sidecar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="artifacts/analysis_current/marts")
    parser.add_argument("--n-services", type=int, default=24)
    parser.add_argument("--empty", action="store_true", help="빈 입력으로 전 표를 빌드한다")
    args = parser.parse_args()

    if args.empty:
        universe_dict = {name: [] for name in BUILDERS}
    else:
        universe_dict = generate_synthetic_universe(n_services=args.n_services).as_dict()

    provenance = ShadowProvenance(source_kind="EMPTY" if args.empty else "SYNTHETIC")
    for table, rows in universe_dict.items():
        result = BUILDERS[table](rows)
        paths = write_mart(result, args.out_dir)
        write_provenance_sidecar(paths["csv"], provenance)
        write_provenance_sidecar(paths["parquet"], provenance)
        print(
            f"{table}: {result.row_count} rows (empty_input={result.empty_input}) -> {paths['parquet']}"
        )


if __name__ == "__main__":
    main()
