#!/usr/bin/env python3
"""`FINAL_RESULTS_SUMMARY.md` · `CLAIM_REGISTRY.md` — A0 §21 필수 산출물.

**새 분석을 하지 않는다.** 이미 검증된 산출물에서 값을 읽어 문서화만 한다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

FORBIDDEN = (
    "Spearman",
    "spearman",
    "ρ",
    "순위상관",
    "Kruskal",
    "kruskal",
    "GRADE B",
    "GRADE C",
    "축 A 관측됨",
    "고령자가 대표기능에 도달할 수 없다",
    "대표기능이 로그인 뒤에 있다",
    "인증제도가 놓쳤다",
)


class ForbiddenPatternFound(ValueError):
    pass


def assert_clean(text: str) -> None:
    hits = [p for p in FORBIDDEN if p in text]
    if hits:
        raise ForbiddenPatternFound(f"반려 패턴: {hits}")


def _snap() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


def build_final(d: Path) -> str:
    summary = json.loads((d / "REAL_RUN_SUMMARY.json").read_text(encoding="utf-8"))
    manifest = json.loads((d / "FROZEN_MART_MANIFEST.json").read_text(encoding="utf-8"))
    axes = summary["analysis_axes"]
    axis_c = axes["axis_c_initial_screen_obstruction"]
    ov = axis_c["max_overlay_coverage"]
    sample = summary["collection_markers"]["analysis_sample"]
    attr = summary["cause_attribution"]
    recovery = summary["depth_recovery_analysis"]
    outcomes = summary["collection_markers"]["outcome_counts"]

    L: list[str] = []
    a = L.append
    a("# FINAL_RESULTS_SUMMARY — E001")
    a("")
    a(f"**스냅샷** {_snap()} (Asia/Seoul) · **등급** {summary['grade']}")
    a(
        f"**mart manifest** `{summary['manifest']['path']}` (`{summary['manifest']['sha256'][:23]}…`)"
    )
    a("")

    a("## 1. 오늘 결론의 핵심")
    a("")
    a(f"> {axes['axis_b_honest_refusal']}")
    a("")
    a(
        "**우리가 값을 못 얻은 것이 아니라, 값을 만들어내지 않기로 한 설계가 작동한 "
        "것이다.** 이 구분이 오늘 산출물 전체의 성격을 정한다 — 빈 자리는 실패의 흔적이 "
        "아니라 측정되지 않은 것을 측정된 것처럼 만들지 않은 결과다."
    )
    a("")

    a("## 2. 세 축의 상태")
    a("")
    a(f"{axes['unified_finding']}")
    a("")
    a(f"{axes['axis_b_predetermined']}")
    a("")

    a("## 3. 수집 커버리지")
    a("")
    a(f"- `attempted_observations` **{sample['attempted_observations']}** (시도한 관측 건수)")
    a(f"- `unique_targets` **{sample['unique_targets']}** (서로 다른 서비스 수)")
    a(
        f"- `coverage` {sample['unique_targets']} / {sample['frame_size']} = **{sample['coverage']}**"
    )
    a(
        "- `joint_valid_n` **0** — J3(MPFED 산출)이 충족되지 않았다. 이 숫자를 살리려 정의를 바꾸지 않았다."
    )
    a(
        "- `l0_analyzable_n` **0** — J4(older-relevant 중 1건 이상 판정)가 충족되지 않았다(축 A 미평가)."
    )
    a(f"- {sample['counts_distinct_note']}")
    a("")
    a("### 탐색이 인증 gate에 도달해 종결된 서비스")
    a("")
    a(
        f"**{outcomes.get('AUTH_GATE', 0)}건**이다. 이 서비스들은 진입 깊이 표본에서 빠지지만 "
        "**빠졌다는 사실 자체가 결과다** — 서술에서 사라지면 은폐가 된다."
    )
    a("")
    a(
        "다만 이것은 **탐색이 그 지점에서 종결됐다**는 관측이지, 대표기능의 위치에 관한 "
        "확인이 아니다. 그 확인을 하려면 gate를 통과해야 하고 통과는 금지돼 있다 — "
        "**우리는 원리적으로 모른다.**"
    )
    a("")
    a(
        f"초기 화면에 로그인/구매/가입 관련 텍스트 후보가 존재해 계정행동 가드가 탐색을 "
        f"중단시킨 경우는 별도로 {attr['attribution']['guard_granularity']['n']}건이다."
    )
    a("")

    a("## 4. 축 C — 초기 화면 방해요소 (오늘 유일한 실측 축)")
    a("")
    a(f"상태 `{axis_c['status']}` — {axis_c['status_expansion']}")
    a("")
    a(
        f"- L0 산출물을 보유한 {axis_c['n_observations']}개 관측에서 방해요소 {axis_c['n_interrupts']}건이 탐지됐다."
    )
    a(
        f"- `final_label`이 `UNKNOWN`인 것이 {axis_c['interrupt_final_label_unknown_n']}건"
        f"({axis_c['interrupt_final_label_unknown_pct']}%)으로 **최대 범주**다."
    )
    a(
        f"- 겹침 분포는 **양극**이다 — 완전히 덮은 관측 {ov['n_at_full_coverage_1_0']}건"
        f"({ov['pct_at_full_coverage_1_0']}%) · 겹침 없음 {ov['n_at_zero_coverage']}건 · "
        f"가운데 구간(0.25~0.75) {ov['mass_0_25_to_0_75']}건뿐. median 단독 인용은 오도한다."
    )
    a("- dismissal 4조합:")
    for p in axis_c["dismissal_paths"]:
        a(f"  - {p['n']}건 — {p['label']}")
    a(f"- {axis_c['dismissal_narrative_constraint']['principle']}")
    a("")

    a("## 5. 축 B — 진입 깊이 미산출의 원인 분해 (관측 outcome 층위)")
    a("")
    a(f"{attr['layer_note']}")
    a("")
    for item in attr["attribution"].values():
        a(f"- **{item['n']}건** ({item['pct']}%) `{item['category']}` — {item['label']}")
    a("")
    a(f"- {attr['e6b_note']}")
    a("")
    a("### 반사실 — 가드는 구속 조건인가")
    a("")
    a(f"- {recovery['finding']}")
    a(f"- 회복 상한 `{recovery['honest_range']}` · 라벨 `{recovery['counterfactual_label']}`")
    a(f"- **적용 범위**: {recovery['scope_condition']}")
    a(f"- **추론 한계**: {recovery['inference_limit']}")
    a("")
    deeper = attr["deeper_layer_under_audit"]
    a(f"### 더 아래 층 — 감사 중 (`{deeper['lane']}`)")
    a("")
    for gap in deeper["observed_gaps"]:
        a(f"- {gap}")
    a(f"- {deeper['consequence_if_confirmed']}")
    a("")

    a("## 6. 등급")
    a("")
    a(f"**{summary['grade']}** — {summary['grade_note']}")
    a("")

    a("## 7. 과정에서 발견된 것")
    a("")
    a(
        "**검증 실수가 7건 있었고 그중 상당수는 결론을 바꿀 수 있었다.** 상세는 "
        "`STATISTICAL_RESULTS.md` §4.5에 있다 — 오류를 먼저, 그것을 잡은 구조를 나중에 적었다."
    )
    a("")
    a(
        "요약: '있다고 가정했으나 없었던' 것이 3회 나왔고 이는 **한 개의 점검 누락이 세 번 "
        "발현된 것**이다(비어 있던 칸: `이 단계의 산출물을 만드는 코드가 실재하는가`). "
        "검증 실수 7건은 **형식 미확인**과 **범위 확장** 두 유형으로 압축된다. "
        "**상위가 하위를 검사하는 단방향 구조였으면 이 중 어느 것도 안 잡혔다.**"
    )
    a("")

    a("## 8. 한계")
    a("")
    a("`LIMITATIONS.md` 11개 항목을 참조한다. 특히:")
    a("")
    a("- §4 반사실의 비무작위 배정 한계 (회복 상한은 현재 구현 하의 조건부 값)")
    a("- §5 older-relevant 태깅은 연구진 판정 (청각 도메인 부재 포함)")
    a("- §8 축 C 47% 미분류")
    a("- §11 원인 귀속표 전체가 recovery lane 감사 결과에 따라 재해석될 수 있다")
    a("")
    a("---")
    a("")
    a(
        "> 본 연구는 실제 고령자의 행동·포기·학습효과를 직접 관측하지 않았다. 어떤 결과도 "
        "그것을 말하지 않는다. 오늘 N은 작고 그 사실이 모든 문장에 따라다닌다. "
        "**우리가 관측한 것은 우리 도구의 도달 한계이지 사용자의 도달 한계가 아니다.**"
    )
    a("")
    a(f"입력 SHA: `{json.dumps(manifest['input_shas'], ensure_ascii=False)}`")
    return "\n".join(L)


def build_registry(d: Path) -> tuple[str, dict[str, Any]]:
    stats = json.loads((d / "STATISTICAL_RESULTS.json").read_text(encoding="utf-8"))
    manifest = json.loads((d / "FROZEN_MART_MANIFEST.json").read_text(encoding="utf-8"))
    summary = json.loads((d / "REAL_RUN_SUMMARY.json").read_text(encoding="utf-8"))
    sha_by_file = {f["file"]: f["sha256"] for f in manifest["mart_files"]}
    src = {
        "axis_c_descriptive": sha_by_file.get("fact_interrupt_element.json"),
        "axis_b_cause_attribution": sha_by_file.get("fact_task_entry.json"),
        "axis_a_not_evaluated": sha_by_file.get("fact_criterion_result.json"),
    }
    sample = summary["collection_markers"]["analysis_sample"]

    rows: list[dict[str, Any]] = []
    for group, claims in stats["claims"].items():
        for i, c in enumerate(claims, 1):
            rows.append(
                {
                    "claim_id": f"{group}-{i:02d}",
                    "grade": c["grade"],
                    "claim": c["claim"],
                    "metric": c["basis"],
                    "effect": "기술통계/직접 관측 — 효과크기 없음",
                    "sample_n": sample["attempted_observations"],
                    "missing_n": sample["archetype_unknown_n"]
                    if group == "axis_b_cause_attribution"
                    else 0,
                    "undetermined_n": 0,
                    "assumption": "축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.",
                    "robustness": "C 독립 재계산 전건 일치 (다른 조인 경로)",
                    "source_artifact_sha": src.get(group),
                }
            )

    L: list[str] = []
    a = L.append
    a("# CLAIM_REGISTRY — E001")
    a("")
    a(f"**스냅샷** {_snap()} (Asia/Seoul)")
    a("")
    a(
        "오늘 등재 가능한 등급은 **A**(정의·기술통계·직접 관측 + lineage 완전)뿐이다. "
        "association이 계산되지 않았으므로 그에 기반한 상위 등급은 **존재할 수 없고**, "
        "exploratory 등급도 **만들지 않았다** — 만들면 `substitute_made: false` 판정을 "
        "뒤집는 것이 된다."
    )
    a("")
    a(
        f"등재 claim **{len(rows)}건**, 전부 등급 A. 새 claim을 만들지 않았다 — "
        "`STATISTICAL_RESULTS.md`에 이미 검증된 문장을 근거와 함께 옮겼다."
    )
    a("")
    for r in rows:
        a(f"## `{r['claim_id']}` — GRADE {r['grade']}")
        a("")
        a(f"> {r['claim']}")
        a("")
        a(f"- **metric**: {r['metric']}")
        a(f"- **effect**: {r['effect']}")
        a(
            f"- **sample_n**: {r['sample_n']} · **missing_n**: {r['missing_n']} · "
            f"**undetermined_n**: {r['undetermined_n']}"
        )
        a(f"- **assumption**: {r['assumption']}")
        a(f"- **robustness**: {r['robustness']}")
        a(f"- **source_artifact_sha**: `{r['source_artifact_sha']}`")
        a("")
    a("---")
    a("")
    a(
        "계약이 지정한 통계 분석은 `NOT_COMPUTABLE`이며 대체물을 만들지 않았다"
        "(`STATISTICAL_RESULTS.json` `contract_specified_analysis`)."
    )
    return "\n".join(L), {"rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mart-dir", required=True)
    args = ap.parse_args()
    d = Path(args.mart_dir)

    final = build_final(d)
    assert_clean(final)
    (d / "FINAL_RESULTS_SUMMARY.md").write_text(final, encoding="utf-8")

    reg_md, reg = build_registry(d)
    assert_clean(reg_md)
    (d / "CLAIM_REGISTRY.md").write_text(reg_md, encoding="utf-8")
    ledger = {
        "document_type": "CLAIM_REGISTRY",
        "snapshot_at": _snap(),
        "claims": reg["rows"],
        "claim_count": len(reg["rows"]),
        "grades_used": sorted({r["grade"] for r in reg["rows"]}),
        "association_claims": 0,
        "substitute_made": False,
    }
    txt = json.dumps(ledger, ensure_ascii=False, indent=2)
    assert_clean(txt)
    (d / "CLAIM_REGISTRY.json").write_text(txt, encoding="utf-8")
    for f in ("FINAL_RESULTS_SUMMARY.md", "CLAIM_REGISTRY.md", "CLAIM_REGISTRY.json"):
        h = hashlib.sha256((d / f).read_bytes()).hexdigest()[:12]
        print(f"{f}  sha256:{h}  {len((d / f).read_text(encoding='utf-8').splitlines())} lines")
    print(f"claims={len(reg['rows'])} forbidden_hits=0")


if __name__ == "__main__":
    main()
