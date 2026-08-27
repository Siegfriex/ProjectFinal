"""EDA-07 — Certification Descriptive (`03_CRISP_DM_EXECUTION_PLAN_v2.0.md` Phase 4/5).

`dim_certification`을 소비한다. **Claude A(governor) 확정 규칙**
(LA-TB-1630-20260827, 결과를 보기 전에 고정, 사후 변경 금지) — 관측 프레임
실측(59건)에서 `certified_current`는 상수다(CERTIFIED 0건, NOT_CERTIFIED 55건,
UNDETERMINED 13건). 이 스크립트는:

1. **인증 관련 inferential test(상관·집단비교·회귀)를 일절 만들지 않는다** —
   분산 유무를 감지해 조건부로 여는 게 아니라, 애초에 그런 경로 자체가 이 모듈에
   없다. `certified_current`가 상수이므로 분모가 0이다.
2. `NOT_CERTIFIED`(만료·애초 미보유 등)와 `UNDETERMINED`(요건 시험 자체가
   불가했음)를 **구분해서** 보고한다 — 왜 0인지가 사라지지 않게 한다. 원인
   (만료/애초 미보유/join 기준이 엄격해서 탈락)은 **데이터로 구분하지 못한다**는
   사실 자체를 감춘다.
3. 고정 문장 템플릿(`descriptive_sentence`)으로만 서술한다 — 자유 텍스트로
   결론을 유도하지 않는다.
4. claim 등급은 `CERTIFICATION_CLAIM_GRADE`("SUPPORTED_WITH_LIMITATION")로
   고정하고, `FORBIDDEN_CERTIFICATION_PHRASES`에 등재된 표현은 이 모듈이 내는
   어떤 텍스트에도 나타나지 않는다(`assert_no_forbidden_certification_phrasing`
   가 산출 직전에 강제한다 — 조용히 넘어가지 않는다).

이 자동전환/금지 로직 자체가 오케스트레이터·governor 지시의 핵심이다 — 무분산
상태에서 비교·인과 결론을 만들어내는 것은 그 자체로 결론 유도(`00 §14` 금지)다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from ..provenance import ShadowProvenance
from .common import (
    EDAOutputPaths,
    has_variance,
    savefig,
    stamp_all,
    write_markdown_note,
    write_summary_json,
    write_table,
)

NAME = "eda07_certification_descriptive"

#: Claude A(governor) 확정 — 인증 claim은 항상 이 등급으로 고정한다. 비교축이
#: 없다는 사실 자체가 "지지되지 않음"이 아니라 "제한부로 지지됨"이다 — 관측
#: 범위에서 비교가 성립하지 않았을 뿐, 인증 미보유 자체는 실측 사실이기 때문이다.
CERTIFICATION_CLAIM_GRADE = "SUPPORTED_WITH_LIMITATION"

#: 이 표현들은 인과·비교 결론을 인증 데이터가 뒷받침하지 않는데도 뒷받침하는
#: 것처럼 읽힌다 — 이 모듈이 내는 어떤 텍스트에도 등장하면 안 된다(governor 지시,
#: 금지 표현 원문 그대로).
FORBIDDEN_CERTIFICATION_PHRASES: tuple[str, ...] = (
    "인증제도가 이 장벽들을 놓쳤다",
    "인증이 접근성을 담보하지 못한다",
    "인증 미보유가 장벽의 원인이다",
)

#: governor가 승인한 표현 — 비교 자체가 성립하지 않았다는 사실만 말한다.
APPROVED_CERTIFICATION_PHRASE = "본 관측범위에서 현행 인증 보유 서비스가 없어 인증 유무와 관측 지표의 비교 자체가 성립하지 않았다."


class ForbiddenCertificationPhrasingError(ValueError):
    """`FORBIDDEN_CERTIFICATION_PHRASES` 중 하나가 산출 텍스트에 들어갔다."""


def assert_no_forbidden_certification_phrasing(text: str) -> None:
    hits = [p for p in FORBIDDEN_CERTIFICATION_PHRASES if p in text]
    if hits:
        raise ForbiddenCertificationPhrasingError(
            f"금지 표현이 인증 산출물 텍스트에 들어갔다: {hits} — governor 지시 위반"
        )


def descriptive_sentence(n_total: int, n_certified: int) -> str:
    """고정 문장 템플릿 (governor 지시 원문 형식)."""
    return (
        f"관측 프레임 {n_total}개 서비스 중 유효기간·대상범위·서비스 동일성 3요건을 "
        f"충족하는 현행 WA 인증 보유 서비스는 {n_certified}건이었다."
    )


def _match_status_breakdown(certification: pd.DataFrame) -> dict:
    if "certification_match_status" not in certification.columns:
        return {"available": False}
    status = certification["certification_match_status"].astype(str)
    reason = certification.get("certification_undetermined_reason")
    breakdown: dict[str, object] = {
        "available": True,
        "CERTIFIED": int((status == "CERTIFIED").sum()),
        "NOT_CERTIFIED": int((status == "NOT_CERTIFIED").sum()),
        "UNDETERMINED": int((status == "UNDETERMINED").sum()),
    }
    if reason is not None:
        undetermined_mask = status == "UNDETERMINED"
        breakdown["UNDETERMINED_by_reason"] = (
            reason[undetermined_mask].astype(str).value_counts(dropna=False).to_dict()
        )
    breakdown["cause_not_distinguishable_note"] = (
        "NOT_CERTIFIED의 원인(만료/애초 미보유/이 연구의 join 기준이 엄격해서 탈락)은 "
        "현재 수집 데이터로 구분하지 못한다 — 이 구분이 안 된다는 사실 자체를 보고한다."
    )
    return breakdown


def run_eda07(
    marts: dict[str, pd.DataFrame],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
) -> EDAOutputPaths:
    """인증 관련 비교/inferential 경로는 이 함수에 **존재하지 않는다** — 항상
    descriptive-only다. (이전 skeleton 버전에 있던 `comparison_marts` 조건부
    비교 경로는 governor 지시로 완전히 제거했다: 분산이 있어도 만들지 않는다.)
    """
    provenance = provenance or ShadowProvenance()
    certification = marts.get("dim_certification", pd.DataFrame())

    if certification.empty:
        distribution = pd.DataFrame(columns=["certified_current", "n"])
        summary = {
            "n": 0,
            "mode": "DESCRIPTIVE_ONLY",
            "reason": "빈 입력",
            "claim_grade": CERTIFICATION_CLAIM_GRADE,
            "descriptive_sentence": descriptive_sentence(0, 0),
            "match_status_breakdown": {"available": False},
        }
    else:
        distribution = (
            certification["certified_current"]
            .value_counts(dropna=False)
            .rename_axis("certified_current")
            .reset_index(name="n")
        )
        variance = has_variance(certification["certified_current"])
        n_total = len(certification)
        n_certified = int((certification["certified_current"].astype(str) == "1").sum())
        summary = {
            "n": n_total,
            "certified_current_distribution": certification["certified_current"]
            .value_counts(dropna=False)
            .to_dict(),
            "has_variance": bool(variance),
            # 항상 DESCRIPTIVE_ONLY다 — 인증 비교/inferential 경로는 이 모듈에 없다
            # (governor 지시, 분산 유무와 무관하게 일절 만들지 않는다).
            "mode": "DESCRIPTIVE_ONLY",
            "claim_grade": CERTIFICATION_CLAIM_GRADE,
            "descriptive_sentence": descriptive_sentence(n_total, n_certified),
            "match_status_breakdown": _match_status_breakdown(certification),
        }
        if not variance:
            summary["reason"] = APPROVED_CERTIFICATION_PHRASE
        else:
            # 분산이 있어도(예: 실제 데이터가 CERTIFIED>0을 낳더라도) 여전히
            # descriptive-only다 — 이 모듈은 인증 비교 경로 자체를 두지 않는다.
            summary["reason"] = (
                "certified_current에 분산이 관측됐지만, 인증 관련 inferential test는 "
                "이 모듈에 구현하지 않는다(governor 지시) — descriptive만 보고한다."
            )

    csv_path, parquet_path = write_table(distribution, out_dir, NAME)
    summary_path = write_summary_json(summary, out_dir, NAME)

    fig, ax = plt.subplots(figsize=(5, 4))
    if not distribution.empty:
        distribution.set_index("certified_current")["n"].plot(kind="bar", ax=ax)
        ax.set_title(f"certified_current 분포 ({summary['mode']})")
        ax.set_ylabel("web_target count")
    else:
        ax.text(0.5, 0.5, "빈 입력", ha="center", va="center")
        ax.set_axis_off()
    fig_path = savefig(fig, out_dir, NAME)

    body = [
        f"- 표본: {summary['n']}건",
        f"- 모드: **{summary['mode']}** (claim_grade={summary['claim_grade']})",
        f"- {summary['descriptive_sentence']}",
        f"- 사유: {summary.get('reason')}",
        f"- match_status 분해: {summary.get('match_status_breakdown')}",
        "- 인증 관련 상관·집단비교·회귀는 이 산출물에 없다 — descriptive만 낸다.",
    ]
    for line in body:
        assert_no_forbidden_certification_phrasing(line)

    md_path = write_markdown_note(
        "EDA-07 — Certification Descriptive", body, out_dir, NAME, provenance=provenance
    )
    stamp_all(out_dir, NAME, provenance)

    return EDAOutputPaths(
        name=NAME,
        csv_path=csv_path,
        parquet_path=parquet_path,
        summary_json_path=summary_path,
        figure_paths=(fig_path,),
        markdown_path=md_path,
    )


def _main() -> None:
    from ..marts.synthetic import generate_synthetic_universe

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="artifacts/analysis_current/eda/eda07")
    parser.add_argument("--n-services", type=int, default=24)
    args = parser.parse_args()

    universe = generate_synthetic_universe(n_services=args.n_services).as_dict()
    marts = {name: pd.DataFrame(rows) for name, rows in universe.items()}
    paths = run_eda07(marts, args.out_dir)
    print(f"EDA-07 done → {paths.summary_json_path}")


if __name__ == "__main__":
    _main()
