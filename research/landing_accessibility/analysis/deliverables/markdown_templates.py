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

from ..eda.statistics import DIRECTION_DEFINITION
from ..marts.schema import TABLE_SCHEMAS
from ..older_relevance_registry import (
    LIMITATIONS_REQUIRED_ITEMS,
    NOT_AN_EXTERNAL_STANDARD_NOTICE,
    registry_status,
)
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


def generate_final_results_summary(
    eda05_summary: dict[str, Any],
    eda07_summary: dict[str, Any],
    eda09_summary: dict[str, Any],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
) -> Path:
    """`FINAL_RESULTS_SUMMARY.md`.

    **Claude A(governor) 의무 보고 항목**: "대표기능이 인증 벽 뒤에 있는 서비스
    N건"을 명시적으로 싣는다. 그 서비스들은 MPFED를 잴 수 없어 joint-valid
    표본에서 빠지지만, **빠졌다는 이유로 서술에서 사라지면 은폐다** — 대표기능이
    로그인/본인확인/결제 벽 뒤에 있다는 것 자체가 entry friction에 관한 실질
    관측이기 때문이다.
    """
    provenance = provenance or ShadowProvenance()
    validity = eda05_summary.get("joint_validity", {}) or {}
    behind_gate = validity.get("behind_gate", {}) or {}

    lines = ["# FINAL_RESULTS_SUMMARY", "", f"`shadow_lane={provenance.shadow_lane}`", ""]

    lines.append("## 관측 범위")
    lines.append("")
    lines.append(
        f"- 시도 {validity.get('n_attempted')}건 · joint-valid {validity.get('n_joint_valid')}건 · "
        f"제외 {validity.get('n_excluded')}건"
    )
    lines.append(f"- 제외 사유별: {validity.get('excluded_by_reason')}")
    lines.append("")

    lines.append("## 대표기능이 인증 벽 뒤에 있는 서비스")
    lines.append("")
    lines.append(
        f"**{behind_gate.get('n_services', 0)}건** — 대표기능 진입이 로그인·본인확인·결제·"
        "CAPTCHA 같은 gate에 막혀 MPFED를 산출할 수 없었던 서비스다."
    )
    lines.append("")
    lines.append(f"- gate 종류별: {behind_gate.get('by_endpoint_status', {})}")
    lines.append(
        "- 이 서비스들은 joint-valid 표본(진입깊이 통계·association)에서 빠지지만, "
        "**빠졌다는 사실 자체가 결과다.** 대표기능이 벽 뒤에 있다는 것은 entry friction에 "
        "관한 실질 관측이며, transport failure·timeout 같은 **우리 쪽 수집 사정**과 "
        "합산하지 않는다(전자는 대상의 성질이다)."
    )
    lines.append(
        "- 이것을 '측정 실패'로 적으면 관측 결과를 수집 결함으로 오기하는 것이다 — "
        "제외 사유를 `GATE_REACHED_MPFED_NULL`로 분리해 두는 이유다."
    )
    lines.append("")

    refusal = validity.get("access_refusal", {}) or {}
    lines.append("## 자동 접근이 거절된 서비스")
    lines.append("")
    lines.append(
        f"**{refusal.get('n_total', 0)}건은 자동 접근이 거절되어 진입 설계를 관측하지 못했다** "
        f"(L1 `BLOCKED` {refusal.get('n_l1_blocked', 0)}건 · "
        f"L0 `FAILED_ACCESS_BLOCKED` {refusal.get('n_l0_access_blocked', 0)}건)."
    )
    lines.append(
        "- WAF·403은 **우리 자동화 도구에 대한 반응**이지 대상의 진입 설계가 아니다 — "
        "위의 인증 벽(gate, 대상의 성질)과 **합산하지 않는다.**"
    )
    lines.append("- 이 건들에 대해 진입 마찰을 어느 방향으로도 주장하지 않는다 — 관측이 없다.")
    lines.append("")

    lines.append("## older-relevant 분모")
    lines.append("")
    lines.append(
        f"- `EligibleOlderRelevant_i = 0`이라 `FailRate = NULL`인 서비스: "
        f"**{eda09_summary.get('n_fail_rate_null_zero_eligible', 0)}건**"
    )
    lines.append(
        "- 정본 태깅 소계 22는 **분모가 아니다** — 분모는 서비스마다 다르며 "
        "older-relevant 중 `final_status ∈ {PASS, FAIL}`로 판정된 것의 수다."
    )
    lines.append(
        "- 이 태깅은 **외부 표준이 아니라 본 연구진의 판정**이다(KWCAG에 공식 '고령자 관련' "
        "지정 없음) — 상세는 `LIMITATIONS.md` §5."
    )
    lines.append("")

    lines.append("## 인증(WA certification)")
    lines.append("")
    lines.append(f"- {eda07_summary.get('descriptive_sentence', '(EDA-07 미실행)')}")
    lines.append(
        f"- claim 등급: `{eda07_summary.get('claim_grade', 'SUPPORTED_WITH_LIMITATION')}` — "
        "인증 관련 상관·집단비교·회귀는 만들지 않았다(관측 프레임에서 무분산)."
    )
    lines.append("")

    lines.append("## Association (전부 exploratory 이하 — 아래 등급 참조)")
    lines.append("")
    for label, key in (
        ("primary (A0)", "primary_association"),
        ("구조보정", "primary_structure_adjusted_association"),
        ("secondary", "secondary_association"),
    ):
        assoc = eda09_summary.get(key) or {}
        if not assoc:
            continue
        lines.append(
            f"- {label}: {assoc.get('metric')} → effect={assoc.get('effect')} "
            f"(n={assoc.get('n')}, claim_grade=`{assoc.get('claim_grade')}`, "
            f"headline_eligible={assoc.get('headline_eligible')}, "
            f"sign_flip_axis=`{assoc.get('sign_flip_axis')}`)"
        )
    lines.append("")
    lines.append(
        "- 세 축(KWCAG / entry friction / WA certification)을 단일 종합점수로 합치지 않는다."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"> {INTERPRETATION_DISCIPLINE_NOTICE}")
    return _write(Path(out_dir) / "FINAL_RESULTS_SUMMARY.md", lines, provenance)


def generate_limitations(
    eda05_summary: dict[str, Any],
    eda07_summary: dict[str, Any],
    out_dir: str | Path,
    *,
    eda09_summary: dict[str, Any] | None = None,
    provenance: ShadowProvenance | None = None,
) -> Path:
    """`LIMITATIONS.md` — Claude A(governor) 확정 지시를 반드시 담는다
    (LA-TB-1630-20260827, 결과를 보기 전에 고정):

    1. archetype별 **실제 joint-valid n**과 어느 archetype이 low-n이었는지 표로
       명시한다(빠지면 안 된다는 governor 지시).
    2. 인증 NOT_CERTIFIED vs UNDETERMINED 구분과, 그 원인을 데이터로 구분하지
       못한다는 사실.
    3. 오늘 도는 게이트가 `E000_FAST`이며 완료 상태값은 `E000_FAST_PASS`라는
       것 — `PHASE_GATES.md`의 `E000_V2_VALIDATED`(8~12타깃+두 독립감사)는
       오늘 충족되지 않는다. 이 문자열을 이 산출물이 닫힌 것처럼 오독되게 쓰지 않는다.
    4. **§2.1 결론의 방향 조작화** — 방향 = 해당 association의 Spearman rho
       부호이며, **두 민감도 축(표본 구성 · 측정 불확실성) 각각에서 판정**한다.
       어느 축에서 뒤집혔는지(`sign_flip_axis`)를 association별로 명시한다.
    """
    provenance = provenance or ShadowProvenance()
    eda09_summary = eda09_summary or {}
    lines = ["# LIMITATIONS", "", f"`shadow_lane={provenance.shadow_lane}`", ""]

    lines.append("## 1. Archetype 최소 N 규칙 (Claude A governor 확정, 결과 확인 전 고정)")
    lines.append("")
    lines.append("| archetype | joint-valid n | 상태 | ExcessDepth 산출 | Kruskal-Wallis 포함 |")
    lines.append("|---|---|---|---|---|")
    by_archetype = eda05_summary.get("by_archetype", {}) or {}
    if not by_archetype:
        lines.append("| _(현재 EDA-05 산출 없음)_ | | | | |")
    else:
        for archetype, entry in by_archetype.items():
            n = entry.get("joint_valid_n", entry.get("n"))
            status = entry.get("archetype_status", "?")
            excess_ok = entry.get("excess_depth_included")
            kw_ok = entry.get("kruskal_wallis_included")
            lines.append(f"| `{archetype}` | {n} | `{status}` | {excess_ok} | {kw_ok} |")
    lines.append("")
    lines.append(
        "규칙: joint-valid n>=5 → ExcessDepth 산출 + Kruskal-Wallis 포함 + joint figure 정상 표시. "
        "3<=n<=4 → ExcessDepth는 산출하되 `low_n_archetype=true` 플래그(joint figure에서 반투명/x "
        "마커로 구분), Kruskal-Wallis 제외. n<=2 → `ExcessDepth=NULL`(median 산출 자체는 되지만 "
        "쓰지 않는다), Kruskal-Wallis 제외, joint figure에는 나타나지 않고 descriptive에만 등장한다. "
        "**어떤 경우에도 서비스/행 자체를 버리지 않는다** — L0 접근성·obstruction descriptive는 "
        "joint-valid 여부와 무관하게 전부 보고한다."
    )
    lines.append("")

    validity = eda05_summary.get("joint_validity", {}) or {}
    lines.append("### joint-valid 시도/제외 분해")
    lines.append("")
    lines.append(
        f"- 시도 {validity.get('n_attempted')}건 중 joint-valid {validity.get('n_joint_valid')}건, "
        f"제외 {validity.get('n_excluded')}건"
    )
    lines.append(f"- 제외 사유별: {validity.get('excluded_by_reason')}")
    lines.append("")

    # ── §2.1 결론의 방향 조작화 (Claude A governor 확정) ──────────────────
    lines.append("## 2. 결론의 방향 — 두 민감도 축에서 각각 판정 (§2.1)")
    lines.append("")
    lines.append(f"**{DIRECTION_DEFINITION}**")
    lines.append("")
    lines.append("| 축 | 무엇을 흔드나 | 근거 조항 |")
    lines.append("|---|---|---|")
    lines.append(
        "| `sample_composition` | 표본 구성 (leave-one-archetype-out) | robustness (A0 §15) |"
    )
    lines.append(
        "| `measurement_uncertainty` | 측정 불확실성 (UNDETERMINED lower=전부 PASS / "
        "upper=전부 FAIL bound) | ANALYSIS_CONTRACT §2.1 |"
    )
    lines.append("")
    lines.append(
        "강등 규칙: **두 축 모두 부호 유지 → GRADE B 가능. 어느 한 축이라도 bound/부분표본 "
        "사이에서 부호가 뒤집히거나 확인 불가 → GRADE C 이하로 강등.**"
    )
    lines.append("")
    lines.append(
        "| association | rho | n | claim_grade | sample_composition | measurement_uncertainty | sign_flip_axis |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    _association_keys = (
        ("primary (A0)", "primary_association"),
        ("구조보정", "primary_structure_adjusted_association"),
        ("secondary", "secondary_association"),
    )
    _any_association = False
    for label, key in _association_keys:
        assoc = eda09_summary.get(key) or {}
        if not assoc:
            continue
        _any_association = True
        axes = (assoc.get("sign_stability", {}) or {}).get("by_axis", {}) or {}
        rho = (assoc.get("effect", {}) or {}).get("spearman_rho")
        lines.append(
            f"| {label} | {rho} | {assoc.get('n')} | `{assoc.get('claim_grade')}` | "
            f"{axes.get('sample_composition')} | {axes.get('measurement_uncertainty')} | "
            f"`{assoc.get('sign_flip_axis')}` |"
        )
    if not _any_association:
        lines.append("| _(현재 EDA-09 산출 없음)_ | | | | | | |")
    lines.append("")
    lines.append(
        "`NOT_APPLICABLE` = 그 축이 이 association에 구조적으로 적용되지 않는다 "
        "(예: secondary는 Y가 obstruction 변수라 UNDETERMINED 판정에 의존하지 않는다) — "
        "강등 사유가 아니다. `None`(null) = 적용 대상인데 평가 불가 → 확인 안 됨으로 취급해 강등한다."
    )
    lines.append("")

    # ── 선택편향 — primary 표본은 "대표기능에 도달 가능한 서비스"로 한정된다 ──
    behind_gate = validity.get("behind_gate", {}) or {}
    lines.append("## 3. 선택편향 — primary association 표본의 한정")
    lines.append("")
    lines.append(
        "**primary association의 표본은 '대표기능에 실제로 도달 가능한 서비스'로 한정된다.** "
        "joint-valid 조건 J3(MPFED 산출 가능)이 대표기능 진입에 성공했거나 최소한 깊이를 "
        "잴 수 있었던 관측만 남기기 때문이다."
    )
    lines.append("")
    lines.append(
        f"- 그 결과 **대표기능이 인증·결제·본인확인 벽 뒤에 있는 서비스 "
        f"{behind_gate.get('n_services', 0)}건**이 primary 표본에서 제외됐다 "
        f"(gate 종류별: {behind_gate.get('by_endpoint_status', {})})."
    )
    lines.append(
        "- 이 제외는 무작위가 아니다 — **진입 장벽이 가장 큰 서비스들이 선택적으로 빠진다.** "
        "따라서 primary association이 추정하는 관계는 '벽을 넘을 수 있었던 서비스들 안에서의' "
        "관계이며, 모집단 전체로 외삽하면 진입 마찰을 **과소평가**하는 방향으로 편향된다."
    )
    lines.append(
        "- 제외된 서비스들은 `FINAL_RESULTS_SUMMARY.md`가 별도 항목으로 보고한다 — "
        "표본에서 빠졌다는 이유로 서술에서 사라지지 않게 한다."
    )
    lines.append("")
    refusal = validity.get("access_refusal", {}) or {}
    lines.append("### 자동 접근 거절 — 진입 설계를 관측하지 못한 건")
    lines.append("")
    lines.append(
        f"**{refusal.get('n_total', 0)}건은 자동 접근이 거절되어 진입 설계를 관측하지 못했다** "
        f"(L1 `BLOCKED` {refusal.get('n_l1_blocked', 0)}건 · "
        f"L0 `FAILED_ACCESS_BLOCKED` {refusal.get('n_l0_access_blocked', 0)}건)."
    )
    lines.append(
        "- WAF·403 같은 반응은 **우리 자동화 도구에 대한 반응**이지 대상 서비스의 진입 "
        "설계가 아니다. 그래서 gate(대표기능이 인증 벽 뒤에 있다 = 대상의 성질)와 "
        "**합산하지 않는다** — 접근 거절을 진입 장벽으로 세면 대상이 하지 않은 설계를 "
        "대상 탓으로 돌리게 된다."
    )
    lines.append(
        "- 이 건들에 대해서는 진입 마찰을 **어느 방향으로도 주장하지 않는다** — 관측이 없다."
    )
    lines.append("")

    lines.append("## 4. 인증(certification) — NOT_CERTIFIED vs UNDETERMINED")
    lines.append("")
    lines.append(f"- {eda07_summary.get('descriptive_sentence', '(EDA-07 미실행)')}")
    breakdown = eda07_summary.get("match_status_breakdown", {}) or {}
    if breakdown.get("available"):
        lines.append(
            f"- CERTIFIED {breakdown.get('CERTIFIED')}건 · NOT_CERTIFIED {breakdown.get('NOT_CERTIFIED')}건 · "
            f"UNDETERMINED {breakdown.get('UNDETERMINED')}건"
        )
        lines.append(f"  - UNDETERMINED 사유별: {breakdown.get('UNDETERMINED_by_reason')}")
        lines.append(f"  - {breakdown.get('cause_not_distinguishable_note')}")
    else:
        lines.append("- (인증 match_status 분해 데이터 없음)")
    lines.append(f"- claim 등급: `{eda07_summary.get('claim_grade', 'SUPPORTED_WITH_LIMITATION')}`")
    lines.append(
        "- 인증 관련 상관·집단비교·회귀는 어디에도 없다 — `certified_current`가 관측 프레임 전체에서 "
        "상수라 분모가 0이며, 이 연구는 그 상태에서 비교 결과를 만들어내지 않는다."
    )
    lines.append("")

    # ── older_relevance 정본 미동결 ──────────────────────────────────
    # ── older_relevance 정본 — 동결됨. 연구진 판정임을 반드시 명시한다 ────
    status = registry_status()
    lines.append("## 5. `older_relevance` 정본 배정 — **연구진 판정이지 외부 표준이 아니다**")
    lines.append("")
    lines.append(f"> **{NOT_AN_EXTERNAL_STANDARD_NOTICE}**")
    lines.append("")
    if status.get("frozen"):
        lines.append(
            f"- 정본: `{status['doc_id']}` · `{status['source_path']}` "
            f"(control commit `{status['control_commit'][:12]}`, blob `{status['blob_sha'][:12]}`)"
        )
        lines.append(f"- 문서 `{status['source_sha256']}` · 매핑 `{status['mapping_sha256']}`")
        lines.append(
            f"- 동결 시각 {status['frozen_at']} — "
            f"REAL TARGET evidence 0건 상태에서 동결(outcome-blind): "
            f"`{status['frozen_before_any_real_evidence']}`"
        )
        lines.append(
            f"- 배정: 전수 {status['criterion_count']}개 · 도메인별 {status['domain_counts']} · "
            f"older-relevant 태깅 소계 {status['older_relevant_tagged_subtotal']} · "
            f"그중 Pilot 실증 적용기회 확인 {status['older_relevant_pilot_applied']}"
        )
        lines.append(f"- **분모 정합**: {status['denominator_note']}")
    else:
        lines.append(f"- **정본 미주입** — {status.get('note')}")
    lines.append("")
    lines.append(
        f"- **`EligibleOlderRelevant_i = 0`이라 `FailRate = NULL`인 서비스: "
        f"{eda09_summary.get('n_fail_rate_null_zero_eligible', 0)}건** "
        "(정본 §5-5 요구 보고 항목 — 0으로 대체하지 않고 NULL로 두고 건수를 보고한다)."
    )
    lines.append("")
    lines.append("### 정본 문서 §5가 요구한 필수 기재 5항목 (원문 그대로)")
    lines.append("")
    for i, item in enumerate(LIMITATIONS_REQUIRED_ITEMS, start=1):
        lines.append(f"{i}. {item}")
    lines.append("")

    lines.append("## 6. 게이트 지위 — E000_FAST, `E000_V2_VALIDATED` 아님")
    lines.append("")
    lines.append(
        "이번 타임박스(LA-TB-1630-20260827)는 **6개 타깃 스모크 검증(`E000_FAST`)** 이며, "
        "완료 시 상태값은 `E000_FAST_PASS`다. `PHASE_GATES.md`가 정의하는 `E000_V2_VALIDATED` "
        "게이트(8~12타깃 + 두 독립감사)는 **오늘 충족되지 않는다.** 이 산출물의 어떤 필드·"
        "파일명에도 `E000_V2_VALIDATED`를 완료값으로 쓰지 않는다 — 나중에 게이트가 닫힌 것처럼 "
        "오독되는 것을 막기 위해서다."
    )
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"> {INTERPRETATION_DISCIPLINE_NOTICE}")
    return _write(Path(out_dir) / "LIMITATIONS.md", lines, provenance)
