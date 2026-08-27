"""`DECISION_INPUT_TABLE` — 모든 산출물이 공유하는 claim 레코드.

오케스트레이터 지시: "각 산출물에 metric/effect/sample N/missing N/UNDET N/
assumption/robustness/source artifact SHA를 명시하는 필드가 있어야 한다."

이 모듈이 그 8필드를 가진 `ClaimRecord`를 정의하고, EDA-03~08의 summary JSON에서
**기계적으로** 몇 개를 뽑아 예시 행을 만든다. 실제 데이터가 들어오면 같은 구조를
그대로 채우면 된다 — 필드를 새로 발명하지 않는다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ..provenance import ShadowProvenance


@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    metric: str
    effect: Any
    sample_n: int | None
    missing_n: int | None
    undetermined_n: int | None
    assumption: str
    robustness_check: str
    source_artifact_sha: str
    status: str = "SHADOW_PREPARATORY_EXAMPLE"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


COLUMNS = [
    "claim_id",
    "metric",
    "effect",
    "sample_n",
    "missing_n",
    "undetermined_n",
    "assumption",
    "robustness_check",
    "source_artifact_sha",
    "status",
]


def build_decision_input_table(
    eda_summaries: dict[str, dict[str, Any]],
    source_shas: dict[str, str],
) -> pd.DataFrame:
    """EDA summary dict들에서 claim 레코드를 뽑는다.

    `eda_summaries`는 `{"eda03": {...summary...}, ...}` 형태다 (각 EDA `run_edaNN`이
    돌려주는 `EDAOutputPaths.summary_json_path`를 읽어 만든다).
    `source_shas`는 `{"eda03": "<sha256>", ...}` — `provenance.file_sha256`로 만든다.

    입력이 비어 있으면(모든 summary가 `n=0` 류) 빈 claim이 아니라 **N=0으로 명시된
    claim 행**을 만든다 — "N=0"과 "행이 없다"는 다른 사실이다(A2 규칙 N-3과 같은 원칙).
    """
    records: list[ClaimRecord] = []

    eda03 = eda_summaries.get("eda03", {})
    coverage = eda03.get("decision_coverage_overall", {}) or {}
    records.append(
        ClaimRecord(
            claim_id="EDA03-DECISION-COVERAGE",
            metric="decision_coverage_rate (PASS/FAIL 확정 비율, A2 §4.2)",
            effect=coverage.get("rate"),
            sample_n=coverage.get("denominator_applicable"),
            missing_n=coverage.get("na_excluded"),
            undetermined_n=coverage.get("undetermined"),
            assumption="NA(적용기회 없음)는 분모 제외. NOT_ELIGIBLE_AT_COLLECTION은 별도 분리(A2 §4.1).",
            robustness_check="EDA-08 UNDETERMINED stress bound 참조 (worst/best case pass rate).",
            source_artifact_sha=source_shas.get("eda03", ""),
        )
    )

    eda05 = eda_summaries.get("eda05", {})
    excess = eda05.get("excess_depth", {}) or {}
    records.append(
        ClaimRecord(
            claim_id="EDA05-EXCESS-DEPTH",
            metric="ExcessDepth median/IQR (= MPFED - archetype median, `00 §7`)",
            effect={"median": excess.get("median"), "iqr": excess.get("iqr")},
            sample_n=excess.get("n"),
            missing_n=eda05.get("censored_total"),
            undetermined_n=None,
            assumption="절대 threshold(depth>=N=bad) 미도입. archetype 내부 상대 비교만.",
            robustness_check="EDA-08 leave-one-archetype-out Δmedian(MPFED) 참조.",
            source_artifact_sha=source_shas.get("eda05", ""),
        )
    )

    eda05_auth = eda05.get("auth_gate", {}) or {}
    records.append(
        ClaimRecord(
            claim_id="EDA05-AUTH-GATE-PREVALENCE",
            metric="auth_gate_observed rate (A2 규칙 E-8 2항 합집합)",
            effect=eda05_auth.get("observed_rate_overall"),
            sample_n=eda05.get("n_tasks"),
            missing_n=None,
            undetermined_n=None,
            assumption=(
                "endpoint_status='AUTH_GATE_REACHED' 단독 집계가 아니라 "
                "auth_gate_before_endpoint=1 OR endpoint_status_detail=ENDPOINT_VIA_AUTH_GATE 합집합."
            ),
            robustness_check=(
                f"naive(단독 집계) 대비 차이 = "
                f"{eda05_auth.get('observed_n')} - {eda05_auth.get('naive_endpoint_status_only_n')}"
            ),
            source_artifact_sha=source_shas.get("eda05", ""),
        )
    )

    eda07 = eda_summaries.get("eda07", {})
    records.append(
        ClaimRecord(
            claim_id="EDA07-CERTIFICATION-MODE",
            metric="certified_current 분포 및 비교축 가용성",
            effect=eda07.get("mode"),
            sample_n=eda07.get("n"),
            missing_n=None,
            undetermined_n=None,
            assumption=eda07.get("reason", ""),
            robustness_check="has_variance=False면 비교 claim을 만들지 않는다 (강제 비교축 금지).",
            source_artifact_sha=source_shas.get("eda07", ""),
        )
    )

    eda08 = eda_summaries.get("eda08", {})
    stress = eda08.get("undetermined_stress", {}) or {}
    records.append(
        ClaimRecord(
            claim_id="EDA08-UNDETERMINED-STRESS-BOUND",
            metric="pass_rate bound under UNDETERMINED→FAIL vs UNDETERMINED→PASS",
            effect={
                "worst": stress.get("pass_rate_if_undetermined_treated_as_fail"),
                "best": stress.get("pass_rate_if_undetermined_treated_as_pass"),
                "bound_width": stress.get("bound_width"),
            },
            sample_n=stress.get("denominator_applicable"),
            missing_n=None,
            undetermined_n=stress.get("undetermined_n"),
            assumption="UNDETERMINED를 삭제하거나 point estimate로 접지 않는다 (규칙 N-7).",
            robustness_check="두 경계를 항상 병기. bound_width가 좁아도 하나만 보고하지 않는다.",
            source_artifact_sha=source_shas.get("eda08", ""),
        )
    )

    return pd.DataFrame([r.as_dict() for r in records], columns=COLUMNS)


def write_decision_input_table(
    frame: pd.DataFrame, out_dir: str | Path, *, provenance: ShadowProvenance | None = None
) -> dict[str, Path]:
    from ..provenance import write_provenance_sidecar

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "DECISION_INPUT_TABLE.csv"
    parquet_path = out_dir / "DECISION_INPUT_TABLE.parquet"
    # `effect`는 행마다 스칼라(rate)이거나 dict(예: median/IQR 묶음)일 수 있다. Arrow는
    # 한 컬럼에 한 타입만 허용하므로, parquet에 쓰기 전에 **전 행을 균일하게 문자열화**한다
    # (일부만 str로 바꾸면 나머지 float/None과 섞여 스키마 추론이 실패한다).
    import json as _json

    safe = frame.copy()
    safe["effect"] = safe["effect"].apply(
        lambda v: (
            v
            if isinstance(v, str) or v is None
            else _json.dumps(v, ensure_ascii=False, default=str)
        )
    )
    safe.to_csv(csv_path, index=False)
    safe.to_parquet(parquet_path, index=False)
    paths = {"csv": csv_path, "parquet": parquet_path}
    if provenance is not None:
        write_provenance_sidecar(csv_path, provenance)
        write_provenance_sidecar(parquet_path, provenance)
    return paths
