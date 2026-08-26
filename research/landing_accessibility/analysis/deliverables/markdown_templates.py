"""목표 3 — 산출물 템플릿 생성기.

`ANALYSIS_DATA_DICTIONARY.md` · `EDA_REPORT.md` · `STATISTICAL_RESULTS.md` ·
`ROBUSTNESS_RESULTS.md` · `MODEL_DIAGNOSTICS.md`를 생성한다.
`DECISION_INPUT_TABLE.parquet/csv`는 `claim_table.py`가 만든다.

이 모듈은 **나중에 실제 E001 데이터로 다시 실행됐을 때도 그대로 동작**하도록
짜여 있다 — 지금은 synthetic summary를 채워 넣지만, 함수 시그니처는 실제
summary dict를 받아도 동일하게 동작한다. `docs/v2` 인용은 절 번호로 남겨
재검증 가능하게 한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..marts.schema import TABLE_SCHEMAS
from ..provenance import (
    INTERPRETATION_DISCIPLINE_NOTICE,
    ShadowProvenance,
    write_provenance_sidecar,
)


def _write(path: Path, lines: list[str], provenance: ShadowProvenance) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    write_provenance_sidecar(path, provenance)
    return path


def generate_data_dictionary(
    out_dir: str | Path, *, provenance: ShadowProvenance | None = None
) -> Path:
    """`ANALYSIS_DATA_DICTIONARY.md` — `marts/schema.py`의 7개 표를 그대로 문서화한다.

    스키마 자체에서 생성하므로 코드와 문서가 드리프트하지 않는다.
    """
    provenance = provenance or ShadowProvenance()
    lines = [
        "# ANALYSIS_DATA_DICTIONARY",
        "",
        f"`shadow_lane={provenance.shadow_lane}` · `base_sha={provenance.base_sha}`",
        "",
    ]
    lines.append(
        "컬럼 출처: `01_DATA_SPEC_v2.0.md` §4~§9 (물리 컬럼) · "
        "`A2_VOCABULARY_AND_SCHEMA_BINDING.md` §1 (허용값 도메인)."
    )
    lines.append("")
    for table, columns in TABLE_SCHEMAS.items():
        lines.append(f"## `{table}`")
        lines.append("")
        lines.append("| 컬럼 | grain 식별자 | NULL 허용 | 허용값 |")
        lines.append("|---|---|---|---|")
        for col in columns:
            enum_repr = ", ".join(f"`{v}`" for v in col.enum) if col.enum else "(자유형)"
            lines.append(
                f"| `{col.name}` | {'예' if col.required else ''} | "
                f"{'예' if col.nullable else '아니오'} | {enum_repr} |"
            )
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"> {INTERPRETATION_DISCIPLINE_NOTICE}")
    return _write(Path(out_dir) / "ANALYSIS_DATA_DICTIONARY.md", lines, provenance)


def generate_eda_report(
    eda_summaries: dict[str, dict[str, Any]],
    eda_markdown_paths: dict[str, Path],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
) -> Path:
    """`EDA_REPORT.md` — EDA-03~08 개별 note를 한 문서로 묶는다."""
    provenance = provenance or ShadowProvenance()
    titles = {
        "eda03": "EDA-03 Landing Accessibility",
        "eda04": "EDA-04 Popup / Obstruction",
        "eda05": "EDA-05 Entry Depth",
        "eda06": "EDA-06 Joint Profile",
        "eda07": "EDA-07 Certification Descriptive",
        "eda08": "EDA-08 Robustness",
    }
    lines = ["# EDA_REPORT", "", f"`shadow_lane={provenance.shadow_lane}` · `source=synthetic`", ""]
    for key, title in titles.items():
        lines.append(f"## {title}")
        lines.append("")
        summary = eda_summaries.get(key)
        if summary is None:
            lines.append("_(이 실행에서 생성되지 않음)_")
        else:
            for field_name, value in summary.items():
                lines.append(f"- `{field_name}`: {value}")
        md_path = eda_markdown_paths.get(key)
        if md_path is not None:
            lines.append(f"- 상세 note: `{md_path}`")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"> {INTERPRETATION_DISCIPLINE_NOTICE}")
    return _write(Path(out_dir) / "EDA_REPORT.md", lines, provenance)


def generate_statistical_results(
    claim_table_frame,
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
) -> Path:
    """`STATISTICAL_RESULTS.md` — `DECISION_INPUT_TABLE`의 claim들을 사람이 읽는 형태로 편다.

    Phase 5 통계 방법(Kruskal-Wallis/permutation · Spearman · Fisher exact)은
    synthetic 표본으로는 실행하되(예: EDA-06의 Spearman), **검정 통계량을 실제
    서비스 결론으로 인용하지 않는다** — 여기서도 그 원칙을 반복한다.
    """
    provenance = provenance or ShadowProvenance()
    lines = ["# STATISTICAL_RESULTS", "", f"`shadow_lane={provenance.shadow_lane}`", ""]
    lines.append(
        "| claim_id | metric | effect | sample_n | missing_n | undetermined_n | assumption | "
        "robustness_check | source_artifact_sha |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for _, row in claim_table_frame.iterrows():
        lines.append(
            f"| {row['claim_id']} | {row['metric']} | {row['effect']} | {row['sample_n']} | "
            f"{row['missing_n']} | {row['undetermined_n']} | {row['assumption']} | "
            f"{row['robustness_check']} | `{str(row['source_artifact_sha'])[:12]}` |"
        )
    lines.append("")
    lines.append(
        "방법론 목록(Phase 5): depth median/IQR/mode/ECDF · archetype 간 Kruskal-Wallis/permutation · "
        "Spearman association · binary Fisher exact. 이 lane에서는 EDA-06이 Spearman 예시를 실행했고,"
        " 나머지는 실제 데이터가 들어와야 유의미하다 — synthetic 표본으로 검정력을 주장하지 않는다."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"> {INTERPRETATION_DISCIPLINE_NOTICE}")
    return _write(Path(out_dir) / "STATISTICAL_RESULTS.md", lines, provenance)


def generate_robustness_results(
    eda08_summary: dict[str, Any],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
) -> Path:
    """`ROBUSTNESS_RESULTS.md` — EDA-08 산출을 그대로 문서화한다."""
    provenance = provenance or ShadowProvenance()
    lines = ["# ROBUSTNESS_RESULTS", "", f"`shadow_lane={provenance.shadow_lane}`", ""]
    lines.append("## leave-one-service-out")
    lines.append(f"- Δmedian(MPFED) 분포: {eda08_summary.get('leave_one_service_out_delta')}")
    lines.append("")
    lines.append("## leave-one-archetype-out")
    lines.append(f"- Δmedian(MPFED) 분포: {eda08_summary.get('leave_one_archetype_out_delta')}")
    lines.append("")
    lines.append("## UNDETERMINED stress")
    stress = eda08_summary.get("undetermined_stress", {})
    lines.append(f"- {stress}")
    lines.append(
        "- 두 경계(UNDETERMINED→FAIL / UNDETERMINED→PASS)를 병기했다. "
        "점추정 하나로 접지 않는다 (A2 규칙 N-7)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"> {INTERPRETATION_DISCIPLINE_NOTICE}")
    return _write(Path(out_dir) / "ROBUSTNESS_RESULTS.md", lines, provenance)


def generate_model_diagnostics(
    marts: dict,
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
) -> Path:
    """`MODEL_DIAGNOSTICS.md`.

    이 연구에는 전통적 통계/ML 모델이 없다 — `automation_grade` 사다리
    (deterministic → semantic → VLM A/B → arbiter → human ≤5, `00 §9`)가
    "모델"에 해당한다. 여기서는 그 cascade의 산출 분포를 진단한다:
    automation_grade 분포, reviewer agreement rate, abstention rate,
    human escalation 건수(≤5 예산 준수 여부, A2 §4.6).

    cascade 코드 자체(`ai_review.py`)는 `agent/landing-pc-fixture`가 소유하며
    이 lane은 그 **출력**만 진단한다.
    """
    provenance = provenance or ShadowProvenance()
    adjudication = marts.get("fact_ai_adjudication")
    criterion = marts.get("fact_criterion_result")

    lines = ["# MODEL_DIAGNOSTICS", "", f"`shadow_lane={provenance.shadow_lane}`", ""]
    lines.append(
        "이 연구의 '모델'은 통계 추정 모델이 아니라 AI review cascade "
        "(deterministic → semantic → VLM A/B → arbiter → human ≤5, `00 §9`)다. "
        "cascade 구현(`ai_review.py`)은 `agent/landing-pc-fixture` 소유이며, "
        "여기서는 그 출력(`fact_ai_adjudication`)만 진단한다."
    )
    lines.append("")

    if criterion is not None and not criterion.empty:
        grade_dist = criterion["automation_grade"].value_counts(dropna=False).to_dict()
        lines.append("## automation_grade 분포 (`fact_criterion_result`)")
        for grade, n in grade_dist.items():
            lines.append(f"- `{grade}`: {n}")
        lines.append("")

    if adjudication is not None and not adjudication.empty:
        agreement = adjudication["reviewer_agreement"].value_counts(dropna=False).to_dict()
        abstain_n = int((adjudication["final_status"] == "ABSTAIN").sum())
        human_n = int((adjudication["human_required"].astype(str) == "1").sum())
        lines.append("## AI review cascade 진단 (`fact_ai_adjudication`)")
        lines.append(f"- reviewer_agreement 분포: {agreement}")
        lines.append(f"- ABSTAIN 건수: {abstain_n} / {len(adjudication)}")
        lines.append(
            f"- human_required=1 건수: {human_n} "
            f"(`HUMAN_FINAL_REVIEW_MAX=5` 예산 {'준수' if human_n <= 5 else '**초과 — G-4 위반**'})"
        )
        lines.append("")
    else:
        lines.append("_(fact_ai_adjudication 입력 없음 — 진단할 것이 없다)_")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"> {INTERPRETATION_DISCIPLINE_NOTICE}")
    return _write(Path(out_dir) / "MODEL_DIAGNOSTICS.md", lines, provenance)
