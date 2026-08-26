"""EDA-03~08 공용 유틸 — I/O, 통계 헬퍼, 산출물 규약.

목표 2가 요구한 4종 산출물(CSV/Parquet · summary JSON · PNG/SVG · Markdown note)을
모든 EDA 스크립트가 같은 방식으로 내도록 여기 모은다. `mmdc`(mermaid-cli)는 쓰지
않는다 — matplotlib(Agg 백엔드)만으로 충분하고, headless 환경에서 안정적이다.

**해석 절제.** 이 모듈이 만드는 어떤 summary/markdown에도 `depth >= N = bad`류
임의 임계값을 넣지 않는다 (`00 §7`). `ExcessDepth`는 항상 "같은 archetype 중앙값
대비"로만 정의한다.
"""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless — mmdc/디스플레이 불필요
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 한글 라벨이 두부(tofu) 박스로 깨지지 않도록, 설치돼 있으면 나눔/Noto CJK 계열을
# 우선한다. matplotlib의 폰트 캐시가 이 파일들보다 먼저 만들어졌을 수 있어
# `ttflist` 조회만으로는 잡히지 않는 경우가 있으므로, 알려진 경로는 `addfont`로
# 명시적으로 등록한 뒤 고른다. 없으면 조용히 DejaVu Sans로 폴백한다(그림은 여전히 유효하다).
_KNOWN_KOREAN_FONT_PATHS = (
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)
for _path in _KNOWN_KOREAN_FONT_PATHS:
    if Path(_path).exists():
        with contextlib.suppress(Exception):  # 폰트 등록 실패는 치명적이지 않다
            fm.fontManager.addfont(_path)

_KOREAN_FONT_CANDIDATES = (
    "NanumGothic",
    "NanumSquareRound",
    "Noto Sans CJK KR",
    "Noto Sans KR",
    "AppleGothic",
    "Malgun Gothic",
)
_installed = {f.name for f in fm.fontManager.ttflist}
for _candidate in _KOREAN_FONT_CANDIDATES:
    if _candidate in _installed:
        plt.rcParams["font.family"] = _candidate
        break
plt.rcParams["axes.unicode_minus"] = False

from ..provenance import (  # noqa: E402
    INTERPRETATION_DISCIPLINE_NOTICE,
    ShadowProvenance,
    write_provenance_sidecar,
)


@dataclass(frozen=True)
class EDAOutputPaths:
    name: str
    csv_path: Path | None
    parquet_path: Path | None
    summary_json_path: Path
    figure_paths: tuple[Path, ...]
    markdown_path: Path


def ensure_out_dir(out_dir: str | Path) -> Path:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_table(df: pd.DataFrame, out_dir: str | Path, name: str) -> tuple[Path, Path]:
    """CSV + Parquet — 빈 `DataFrame`도 정상적으로 쓴다 (컬럼만 있는 빈 표)."""
    out_dir = ensure_out_dir(out_dir)
    csv_path = out_dir / f"{name}.csv"
    parquet_path = out_dir / f"{name}.parquet"
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)
    return csv_path, parquet_path


def write_summary_json(summary: dict[str, Any], out_dir: str | Path, name: str) -> Path:
    out_dir = ensure_out_dir(out_dir)
    path = out_dir / f"{name}.summary.json"
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return path


def savefig(fig: plt.Figure, out_dir: str | Path, name: str, *, fmt: str = "png") -> Path:
    out_dir = ensure_out_dir(out_dir)
    path = out_dir / f"{name}.{fmt}"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def write_markdown_note(
    title: str,
    body_lines: list[str],
    out_dir: str | Path,
    name: str,
    *,
    provenance: ShadowProvenance | None = None,
) -> Path:
    out_dir = ensure_out_dir(out_dir)
    path = out_dir / f"{name}.md"
    lines = [f"# {title}", ""]
    lines.extend(body_lines)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"> {INTERPRETATION_DISCIPLINE_NOTICE}")
    path.write_text("\n".join(lines), encoding="utf-8")
    if provenance is not None:
        write_provenance_sidecar(path, provenance)
    return path


def stamp_all(out_dir: str | Path, name: str, provenance: ShadowProvenance) -> None:
    """이 EDA 실행이 낸 산출물 전부에 같은 provenance sidecar를 붙인다."""
    out_dir = Path(out_dir)
    for suffix in (".csv", ".parquet", ".summary.json", ".png", ".svg"):
        for path in out_dir.glob(f"{name}*{suffix}"):
            write_provenance_sidecar(path, provenance)


# ── 통계 헬퍼 — Phase 5 `03_CRISP_DM_EXECUTION_PLAN_v2.0.md` §Evaluation ──────────


def median_iqr(values: pd.Series) -> dict[str, float | None]:
    values = pd.to_numeric(values, errors="coerce").dropna()
    if values.empty:
        return {"n": 0, "median": None, "q1": None, "q3": None, "iqr": None}
    q1, med, q3 = np.percentile(values, [25, 50, 75])
    return {
        "n": int(values.shape[0]),
        "median": float(med),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(q3 - q1),
    }


def mode_value(values: pd.Series) -> float | None:
    values = pd.to_numeric(values, errors="coerce").dropna()
    if values.empty:
        return None
    m = values.mode()
    return float(m.iloc[0]) if not m.empty else None


def ecdf(values: pd.Series) -> pd.DataFrame:
    """경험적 누적분포함수 — (value, F(value)) 두 컬럼."""
    values = pd.to_numeric(values, errors="coerce").dropna().sort_values()
    if values.empty:
        return pd.DataFrame(columns=["value", "ecdf"])
    n = len(values)
    return pd.DataFrame(
        {"value": values.to_numpy(), "ecdf": (np.arange(1, n + 1) / n)}
    ).reset_index(drop=True)


def excess_depth(mpfed: pd.Series, archetype: pd.Series) -> pd.Series:
    """`ExcessDepth = MPFED - archetype median`. 절대 threshold를 도입하지 않는다 (`00 §7`)."""
    frame = pd.DataFrame({"mpfed": pd.to_numeric(mpfed, errors="coerce"), "archetype": archetype})
    medians = frame.groupby("archetype")["mpfed"].transform("median")
    return frame["mpfed"] - medians


def auth_gate_observed(df: pd.DataFrame) -> pd.Series:
    """A2 규칙 E-8 — 2항 합집합. `endpoint_status='AUTH_GATE_REACHED'` 단독 집계는
    gate가 endpoint인 두 archetype에서 과소집계된다 (`reporting.py auth_gate_prevalence`와 동식).
    """
    before = df.get("auth_gate_before_endpoint")
    detail = df.get("endpoint_status_detail")
    before_flag = pd.Series(False, index=df.index)
    if before is not None:
        before_flag = before.astype(str) == "1"
    detail_flag = pd.Series(False, index=df.index)
    if detail is not None:
        detail_flag = detail.astype(str) == "ENDPOINT_VIA_AUTH_GATE"
    return before_flag | detail_flag


def evidence_completeness(measurement_status: pd.Series) -> dict[str, Any]:
    """A2 §4.1 — `MEASURED` 분자 / 전체 분모. `NOT_ELIGIBLE_AT_COLLECTION`은 분모·분자 모두 제외."""
    s = measurement_status.astype(str)
    eligible = s[s != "NOT_ELIGIBLE_AT_COLLECTION"]
    denom = len(eligible)
    numer = int((eligible == "MEASURED").sum())
    return {
        "denominator": denom,
        "numerator_measured": numer,
        "rate": round(numer / denom, 4) if denom else None,
        "not_eligible_at_collection_excluded": int((s == "NOT_ELIGIBLE_AT_COLLECTION").sum()),
    }


def decision_coverage(verdict_state: pd.Series) -> dict[str, Any]:
    """A2 §4.2 — PASS/FAIL로 확정된 비율. `NA`는 분모에서 제외(적용기회 없음), `UNDETERMINED`는 분모에 남는다."""
    s = verdict_state.astype(str)
    applicable = s[s != "NA"]
    decided = applicable.isin(["PASS", "FAIL"])
    denom = len(applicable)
    return {
        "denominator_applicable": denom,
        "decided": int(decided.sum()),
        "undetermined": int((applicable == "UNDETERMINED").sum()),
        "rate": round(decided.sum() / denom, 4) if denom else None,
        "na_excluded": int((s == "NA").sum()),
    }


def has_variance(series: pd.Series) -> bool:
    """무분산 감지 — EDA-07이 비교축을 강제로 살리지 않기 위해 쓴다."""
    return series.dropna().nunique() > 1
