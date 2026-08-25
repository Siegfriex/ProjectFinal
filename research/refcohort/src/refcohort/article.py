"""report.json → 기사 5장 실증 검증 초안.

기사 5장이 요구하는 네 가지를 순서대로 만든다.
  1) 지침 개요  2) 평가 대상과 선정 기준  3) 검사항목별 통과·미흡  4) 4장 한계와의 연결
프로토콜이 금지한 표현(단일 접근성 점수, 인증 적부 판정, NA→PASS 환산)을 쓰지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path

PRINCIPLE_ORDER = ["인식의 용이성", "운용의 용이성", "이해의 용이성", "견고성"]


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.1f}%"


def _cohort(rep: dict, name: str) -> dict:
    return next(c for c in rep["cohorts"] if c["cohort"] == name)


def render(rep: dict, *, registry_summary: dict | None = None) -> str:
    ref, cmp_ = _cohort(rep, "REFERENCE"), _cohort(rep, "COMPARISON")
    ct = rep["criterion_table"]
    measured_ct = [r for r in ct if r["services_applicable"] > 0]
    auto_dec = [r for r in measured_ct if r["automation"] == "AUTO_DECIDABLE"]
    flag_only = [r for r in measured_ct if r["automation"] == "AUTO_FLAG_ONLY"]
    not_auto = [r for r in ct if r["automation"] == "NOT_AUTOMATABLE"]

    L: list[str] = []
    add = L.append

    add("# 5. 실증 검증 — 한국디지털접근성진흥원 지침, 실제로 지켜지고 있나\n")
    add(
        f"> 감사일 {rep['audit_date']} · 코드북 `{rep['codebook_version']}` · run `{rep['run_id']}`\n"
    )

    # ── 5-1 지침 개요 ──
    add("## 5-1. 무엇을 기준으로 쟀나\n")
    add(
        "국내 웹 접근성 인증의 직접 기준은 **KWCAG 2.2**(한국형 웹 콘텐츠 접근성 지침 2.2)다. "
        "4개 원칙, 14개 지침, **33개 검사항목**으로 구성된다. "
        "인증은 디지털포용법에 근거해 과학기술정보통신부가 지정한 인증기관이 부여하며 유효기간은 1년이다.\n"
    )
    add(
        "이 검증은 33개 항목 전부를 같은 방식으로 다루지 않는다. "
        "브라우저에서 기계적으로 확정할 수 있는 항목과, 사람이 봐야만 판정되는 항목이 다르기 때문이다.\n"
    )
    add("| 자동화 수준 | 항목 수 | 이 검증에서의 취급 |")
    add("|---|---:|---|")
    add(
        f"| 기계 판정 가능 | {sum(1 for c in ct if c['automation'] == 'AUTO_DECIDABLE')} | 통과·미흡을 수치로 보고 |"
    )
    add(
        f"| 기계 신호만 가능 | {sum(1 for c in ct if c['automation'] == 'AUTO_FLAG_ONLY')} | 미흡 후보로만 보고, 최종 판정은 사람 검토 몫 |"
    )
    add(
        f"| 자동 관측 불가 | {sum(1 for c in ct if c['automation'] == 'NOT_AUTOMATABLE')} | 판정하지 않고 '확인 불가'로 남김 |"
    )
    add("")
    add(
        "**확인 불가를 통과로 바꾸지 않았다.** 적용할 대상이 아예 없는 항목(예: 동영상이 없는 페이지의 자막 항목)은 "
        "'해당 없음'이며 통과가 아니다. 이 구분을 뭉개면 통과율이 실제보다 높게 나온다.\n"
    )

    # ── 5-2 대상과 기준 ──
    add("## 5-2. 무엇을 쟀나 — 두 집단\n")
    if registry_summary:
        add(
            f"먼저 인증 목록 **전체 {registry_summary['rows_dedup']:,}건**을 수집했다"
            f"(유효 {registry_summary['status_breakdown']['VALID']}건, 만료 {registry_summary['status_breakdown']['EXPIRED']:,}건). "
            f"이 중 감사일 기준 인증이 살아 있는 **{registry_summary['valid_at_audit']}건**이 첫 번째 집단이다.\n"
        )
    add("| 집단 | 정의 | 대상 | 측정 성공 | 측정 불가 |")
    add("|---|---|---:|---:|---:|")
    add(
        f"| 인증 보유군 | 감사일 기준 유효한 웹 접근성 품질인증 사이트 전수 | {ref['targets']} | {ref['measured']} | {ref['blocked']} |"
    )
    add(
        f"| 실사용 상위군 | 50세 이상 이용 상위 앱·서비스의 공식 모바일웹 | {cmp_['targets']} | {cmp_['measured']} | {cmp_['blocked']} |"
    )
    add("")
    add(
        "두 집단은 **완전히 같은 조건**으로 측정했다. 390×844 모바일 화면, 한국어, 서울 시간대, "
        "로그인·결제·본인확인을 하지 않는 공개 화면까지만. 로그인 뒤 화면은 관측하지 않았고, "
        "관측하지 않은 것을 추정으로 채우지 않았다.\n"
    )

    # ── 5-3 결과 ──
    add("## 5-3. 결과 — 항목별 통과와 미흡\n")
    add(
        f"인증 보유군 {ref['measured']}곳 중 **관측한 화면에서 미흡이 하나도 없는 곳은 "
        f"{ref['observed_strict_pass'].get('TRUE', 0)}곳**이었다. "
        f"실사용 상위군은 {cmp_['measured']}곳 중 {cmp_['observed_strict_pass'].get('TRUE', 0)}곳이다.\n"
    )
    add("| 집단 | 측정 | 미흡 0건 | 서비스당 평균 미흡 항목 | 확인된 미흡 지점 총계 |")
    add("|---|---:|---:|---:|---:|")
    for c in (ref, cmp_):
        label = "인증 보유군" if c["cohort"] == "REFERENCE" else "실사용 상위군"
        add(
            f"| {label} | {c['measured']} | {c['observed_strict_pass'].get('TRUE', 0)} | "
            f"{c['failed_criteria_per_service']['mean']} | {c['observed_accessibility_failure_count_total']:,} |"
        )
    add("")

    add("### 기계 판정이 가능한 항목\n")
    add("| 검사항목 | 원칙 | 적용된 서비스 | 미흡 서비스 | 미흡률 | 지점 단위 통과율 |")
    add("|---|---|---:|---:|---:|---:|")
    for r in sorted(auto_dec, key=lambda x: -(x["service_fail_rate"] or 0)):
        add(
            f"| {r['criterion_id']} {r['criterion_name']} | {r['principle'][:2]} | {r['services_applicable']} | "
            f"{r['services_fail']} | {_pct(r['service_fail_rate'])} | {_pct(r['opportunity_pass_rate'])} |"
        )
    add("")

    if flag_only:
        add("### 기계 신호만 가능한 항목 (미흡 후보, 최종 판정 아님)\n")
        add("| 검사항목 | 적용된 서비스 | 미흡 후보 | 후보율 |")
        add("|---|---:|---:|---:|")
        for r in sorted(flag_only, key=lambda x: -(x["service_fail_rate"] or 0)):
            add(
                f"| {r['criterion_id']} {r['criterion_name']} | {r['services_applicable']} | "
                f"{r['services_fail']} | {_pct(r['service_fail_rate'])} |"
            )
        add("")

    add(
        f"나머지 {len(not_auto)}개 항목은 단일 공개 화면의 자동 관측으로는 판정할 수 없어 "
        "'확인 불가'로 남겼다. 통과로 처리하지 않았다.\n"
    )

    # ── 5-4 4장 연결 ──
    add("## 5-4. 4장과의 연결 — 강제력 없는 지침은 어떻게 되는가\n")
    add(
        "디지털포용법상 접근성 품질인증은 **받으려는 자가 신청**할 때만 이뤄진다. "
        "국가기관에는 인증 제품 우선구매 시책을 '마련하여야 한다'는 의무를 지우지만, "
        "민간에는 '우선적으로 활용 또는 구매하도록 **권고할 수 있다**'가 전부다.\n"
    )
    add(
        "그리고 인증을 취소할 수 있는 사유는 **거짓 인증**과 **표시·홍보 위반** 둘뿐이다. "
        "인증을 받은 뒤 실제 접근성이 나빠진 경우는 취소 사유에 없고, "
        "1년의 유효기간 동안 재측정하도록 하는 조항도 없다. "
        "**인증은 한 번 받으면 1년간 아무도 다시 확인하지 않는다.**\n"
    )
    add("이 검증이 메우는 것이 정확히 그 공백이다.\n")

    # ── 한계 ──
    add("## 5-5. 이 검증이 말하지 않는 것\n")
    for lim in rep["interpretation_limits"]:
        add(f"- {lim}")
    add("")
    add(
        "특히 이 결과는 **인증 재심사가 아니다.** 어떤 사이트의 인증이 잘못됐다거나 취소되어야 한다는 뜻이 아니다. "
        "인증 심사는 사이트 전체와 다수 화면을 대상으로 하고, 이 검증은 공개된 진입 화면 하나를 본다. "
        "두 관측 범위는 다르다.\n"
    )
    return "\n".join(L)


def build_article(
    report_path: Path, out_path: Path, registry_summary_path: Path | None = None
) -> Path:
    rep = json.loads(report_path.read_text(encoding="utf-8"))
    rs = (
        json.loads(registry_summary_path.read_text(encoding="utf-8"))
        if registry_summary_path and registry_summary_path.exists()
        else None
    )
    md = render(rep, registry_summary=rs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return out_path
