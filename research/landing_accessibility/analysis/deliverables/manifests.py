"""목표 3 — 산출물 스키마 확정: `FROZEN_MART_MANIFEST.json` · `COLLECTION_COVERAGE.json`
· `STATISTICAL_RESULTS.json` · `ANALYSIS_HANDOFF.json`.

(`EDA_REPORT.md` · `ROBUSTNESS_RESULTS.md`는 `markdown_templates.py`가 만든다.)

이 모듈은 **필드 이름·타입을 지금 확정**하고 synthetic 데이터로 한 번씩 실제로
써 봐서 형식을 검증한다 — 값 자체(내용)는 비어 있어도 된다는 오케스트레이터
지시를 따른다. 필드를 나중에 늘릴 수는 있어도(하위 호환), 여기 정의된 필드의
**이름을 바꾸거나 타입을 바꾸는 것은 downstream을 깬다** — 실제 E001 데이터가
들어온 뒤에는 이 스키마가 계약이다.

JSON 산출물은 전부 `PHASE_GATES.md §4.3` provenance 블록(`provenance.py`)을
최상위 `provenance` 키에 그대로 담는다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..provenance import ShadowProvenance, file_sha256, write_provenance_sidecar

# 아래 마트 목록/컬럼 헬퍼는 로컬에서만 참조한다 — 순환 import를 피하기 위해
# 타입 힌트에는 쓰지 않는다.


def _write_json(
    data: dict[str, Any], out_dir: str | Path, name: str, provenance: ShadowProvenance
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_provenance_sidecar(path, provenance)
    return path


# ── FROZEN_MART_MANIFEST.json ────────────────────────────────────────────


def build_frozen_mart_manifest(
    mart_results: dict[str, Any],  # table -> MartBuildResult
    mart_paths: dict[str, dict[str, Path]],  # table -> {"csv": Path, "parquet": Path}
    *,
    provenance: ShadowProvenance,
) -> dict[str, Any]:
    """`FROZEN_MART_MANIFEST` 스키마.

    필드:
    - `manifest` (str, 고정값 `"FROZEN_MART_MANIFEST"`)
    - `frozen` (bool) — 이 lane에서는 항상 `false`다. P0(`V2_SSOT_FROZEN`) 종료 전
      synthetic/fixture 산출물이 "frozen"일 수 없다 — 이름은 스키마가 실제
      freeze 절차와 같은 필드 계약을 미리 확정해 둔다는 뜻이다.
    - `frozen_reason` (str)
    - `provenance` (dict, `ShadowProvenance.as_dict()`)
    - `tables` (dict[str, dict]) — 표별 `row_count`·`empty_input`·`columns`·
      `csv_sha256`·`parquet_sha256`.
    """
    tables: dict[str, Any] = {}
    for table, result in mart_results.items():
        paths = mart_paths.get(table, {})
        tables[table] = {
            "row_count": result.row_count,
            "empty_input": result.empty_input,
            "columns": list(result.frame.columns),
            "csv_sha256": f"sha256:{file_sha256(paths['csv'])}" if paths.get("csv") else None,
            "parquet_sha256": (
                f"sha256:{file_sha256(paths['parquet'])}" if paths.get("parquet") else None
            ),
        }
    manifest = {
        "manifest": "FROZEN_MART_MANIFEST",
        "shadow_lane": provenance.shadow_lane,
        "status": "SHADOW_PREPARATORY",
        "frozen": False,
        "frozen_reason": (
            "P0(V2_SSOT_FROZEN)이 아직 종료되지 않았고, 이 산출물의 입력은 synthetic/"
            f"fixture다 (source_kind={provenance.source_kind}). freeze 대상은 실제 E001 데이터로 재실행된 "
            "마트다."
        ),
        "tables": tables,
        "provenance": provenance.as_dict(),
    }
    return manifest


# ── COLLECTION_COVERAGE.json ─────────────────────────────────────────────


def build_collection_coverage(
    marts: dict[str, Any],  # table -> pd.DataFrame
    *,
    provenance: ShadowProvenance,
) -> dict[str, Any]:
    """`COLLECTION_COVERAGE` 스키마.

    필드:
    - `manifest` (str, 고정값)
    - `n_web_targets` (int) · `n_observations` (int)
    - `evidence_completeness` (dict) — `eda/common.evidence_completeness()`와 같은 키.
    - `decision_coverage` (dict) — `eda/common.decision_coverage()`와 같은 키.
    - `measurement_status_distribution` (dict[str, int])
    - `certification_variance` (dict) — `{"has_variance": bool, "mode": str}`.
    - `provenance` (dict)
    """
    from ..eda.common import decision_coverage, evidence_completeness, has_variance

    landing = marts.get("fact_landing_observation")
    criterion = marts.get("fact_criterion_result")
    certification = marts.get("dim_certification")

    landing_empty = landing is None or landing.empty
    criterion_empty = criterion is None or criterion.empty
    certification_empty = certification is None or certification.empty

    coverage: dict[str, Any] = {
        "manifest": "COLLECTION_COVERAGE",
        "shadow_lane": provenance.shadow_lane,
        "n_web_targets": (int(landing["web_target_id"].nunique()) if not landing_empty else 0),
        "n_observations": len(landing) if not landing_empty else 0,
        "evidence_completeness": (
            evidence_completeness(landing["measurement_status"])
            if not landing_empty
            else {
                "denominator": 0,
                "numerator_measured": 0,
                "rate": None,
                "not_eligible_at_collection_excluded": 0,
            }
        ),
        "decision_coverage": (
            decision_coverage(criterion["verdict_state"])
            if not criterion_empty
            else {
                "denominator_applicable": 0,
                "decided": 0,
                "undetermined": 0,
                "rate": None,
                "na_excluded": 0,
            }
        ),
        "measurement_status_distribution": (
            landing["measurement_status"].value_counts(dropna=False).to_dict()
            if not landing_empty
            else {}
        ),
        "certification_variance": (
            {
                "has_variance": bool(has_variance(certification["certified_current"])),
                "distribution": certification["certified_current"]
                .value_counts(dropna=False)
                .to_dict(),
            }
            if not certification_empty
            else {"has_variance": False, "distribution": {}}
        ),
        "provenance": provenance.as_dict(),
    }
    return coverage


# ── STATISTICAL_RESULTS.json ─────────────────────────────────────────────


def build_statistical_results_json(
    eda_summaries: dict[str, dict[str, Any]],
    *,
    provenance: ShadowProvenance,
) -> dict[str, Any]:
    """`STATISTICAL_RESULTS` 스키마 (기계가 읽는 버전 — 사람이 읽는 버전은
    `markdown_templates.generate_statistical_results`가 `.md`로 낸다).

    필드 (각 결과 항목에 `claim_grade` — Research Director 확정 등급 시스템,
    `A`(정의/기술통계/직접 관측+evidence lineage complete) · `B`(association+
    min-N 충족+robustness 방향 유지) · `C`(exploratory/low-N/sensitivity-dependent)
    · `UNSUPPORTED`(표본/측정으로 말할 수 없음). association 항목은 `A`를 절대
    받지 않는다 — headline은 `A` 또는 robust `B`만 허용, `C`는 반드시 exploratory로
    명시한다):

    - `manifest` (str, 고정값)
    - `primary_association` (dict, `claim_grade` 포함) — EDA-09 `primary_association` 그대로
      (Spearman(MPFED, OlderRelevantKWCAGFailRate), A0 — raw structural depth ↔
      barrier burden association으로만 해석, difficulty causation 표현 금지).
    - `primary_structure_adjusted_association` (dict, `claim_grade` 포함) — EDA-09
      `primary_structure_adjusted_association` (Spearman(ExcessDepth, OlderRelevantKWCAGFailRate)).
    - `secondary_association` (dict, `claim_grade` 포함) — EDA-09 `secondary_association` 그대로.
    - `kruskal_wallis_mpfed_by_archetype` (dict) — EDA-09 그대로 (tier·executed·
      dropped_groups_below_min_n 포함).
    - `quadrant_classification` (dict) — EDA-09 `quadrant_classification_rule`.
    - `archetype_descriptive` (dict, `claim_grade="A"` — 기술통계/직접 관측) — EDA-05
      `by_archetype` (median/IQR/mode/ECDF 요약, joint-valid n 포함).
    - `undetermined_stress_bound` (dict) — EDA-08 `undetermined_stress`.
    - `provenance` (dict)

    각 하위 dict 자체가 이미 `effect`+`n`+`missing_n`+`undetermined_n`+`claim_grade`
    구조를 담고 있다(association) — 여기서 다시 만들지 않는다, 있는 그대로 참조한다.
    """
    eda05 = eda_summaries.get("eda05", {})
    eda08 = eda_summaries.get("eda08", {})
    eda09 = eda_summaries.get("eda09", {})

    return {
        "manifest": "STATISTICAL_RESULTS",
        "shadow_lane": provenance.shadow_lane,
        "claim_grade_system_note": (
            "A=정의/기술통계/직접 관측(evidence lineage complete). "
            "B=association/inferential + min-N(>=10) 충족 + robustness(leave-one-archetype-out) "
            "방향 유지. C=exploratory/low-N/sensitivity-dependent(반드시 exploratory로 명시). "
            "UNSUPPORTED=표본/측정으로 말할 수 없음. headline은 A 또는 robust B만 허용한다."
        ),
        "primary_association": eda09.get("primary_association"),
        "primary_structure_adjusted_association": eda09.get(
            "primary_structure_adjusted_association"
        ),
        "secondary_association": eda09.get("secondary_association"),
        "kruskal_wallis_mpfed_by_archetype": eda09.get("kruskal_wallis_mpfed_by_archetype"),
        "quadrant_classification": eda09.get("quadrant_classification_rule"),
        "archetype_descriptive": eda05.get("by_archetype", {}),
        "archetype_descriptive_claim_grade": "A",
        "undetermined_stress_bound": eda08.get("undetermined_stress", {}),
        "three_axes_not_combined_note": (
            "KWCAG standard accessibility / entry friction / WA certification은 "
            "이 산출물에서도 단일 종합점수로 합치지 않는다."
        ),
        "provenance": provenance.as_dict(),
    }


# ── ANALYSIS_HANDOFF.json ────────────────────────────────────────────────


def build_analysis_handoff(
    *,
    branch: str,
    commit_sha: str | None,
    base_sha: str,
    artifact_paths: dict[str, Path],
    adjudication_schema_bound: bool,
    open_issues: list[str],
    provenance: ShadowProvenance,
) -> dict[str, Any]:
    """`ANALYSIS_HANDOFF` 스키마 — 이 lane의 최종 인계 매니페스트.

    `handoff/INTEGRATION_READY.json`(같은 연구의 다른 lane)과 같은 관례(sha256:
    접두 다이제스트, `provenance` 블록, `open_issues` 리스트)를 따른다.

    필드:
    - `manifest` (str, 고정값) · `producer` (str) · `branch` (str) ·
      `commit_sha` (str|null, 커밋 전이면 null) · `base_sha` (str)
    - `adjudication_schema_bound` (bool) — 목표 1 완료 여부.
    - `artifacts` (dict[str, str]) — 산출물 경로 → `sha256:` 다이제스트.
    - `real_target` (bool, 항상 `false`) · `real_target_outcome_used` (bool, 항상 `false`)
    - `ready_for_e000` (bool, 항상 `false` — 이 lane 혼자 E000을 승인하지 않는다)
    - `open_issues` (list[str])
    - `provenance` (dict)
    """
    artifacts: dict[str, str] = {}
    for label, path in artifact_paths.items():
        if path is None or not Path(path).exists():
            continue
        artifacts[label] = f"sha256:{file_sha256(path)}"

    return {
        "manifest": "ANALYSIS_HANDOFF",
        "producer": "Claude B (Parallel Delivery Orchestrator worker) -- WORKER-ANALYSIS-CURRENT",
        "branch": branch,
        "commit_sha": commit_sha,
        "base_sha": base_sha,
        "adjudication_schema_bound": adjudication_schema_bound,
        "artifacts": artifacts,
        "real_target": False,
        "real_target_outcome_used": False,
        "ready_for_e000": False,
        "ready_for_e000_reasoning": [
            "이 lane은 P0(V2_SSOT_FROZEN) 종료 전 synthetic/fixture 파이프라인 준비 작업이다 "
            "(`created_before_p0_close=true`) — 실제 데이터 도착 시 즉시 재사용 가능하도록 "
            "스키마·통계 로직·산출물 계약을 확정했을 뿐, E000 착수를 스스로 승인하지 않는다."
        ],
        "open_issues": open_issues,
        "provenance": provenance.as_dict(),
    }


__all__ = [
    "build_analysis_handoff",
    "build_collection_coverage",
    "build_frozen_mart_manifest",
    "build_statistical_results_json",
]
