#!/usr/bin/env python3
"""STATS 산출물 — `CLAIM_GOVERNANCE.md`(2026-08-27 14:58 개정본) 기준.

**계약이 지정한 통계 분석은 계산 불가능하다.** 그 자리를 대체물로 채우지 않는다.
비어 있다는 것을 결함으로 서술하지도 않는다 — **계약이 지정한 분석이 계산
불가능하다는 사실을 보고하는 것이 오늘의 통계 산출물이다**(A 명시).

구성 4종:
  1. 축 C 기술통계 (raw 실측 · 분류 미완)
  2. 축 B 원인 분해 6종 + 반사실
  3. 축 A 미평가 사실
  4. 방법론적 결론

모든 숫자는 mart에서 읽는다 — 손으로 타이핑하지 않는다(드리프트 방지).
모든 claim에 등급을 붙인다. 오늘 쓸 수 있는 등급은 정의·기술통계·직접 관측뿐이다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics as st
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

#: C 스캐너 반려 패턴. 산출 직전에 우리 문서를 우리가 먼저 스캔한다.
FORBIDDEN_PATTERNS: tuple[str, ...] = (
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

CLAIM_GRADE = "A"  # 정의·기술통계·직접 관측 + lineage 완전


class ForbiddenPatternFound(ValueError):
    """반려 패턴이 산출물에 들어갔다."""


def assert_clean(text: str) -> None:
    hits = [p for p in FORBIDDEN_PATTERNS if p in text]
    if hits:
        raise ForbiddenPatternFound(f"반려 패턴이 산출물에 있다: {hits}")


def _snapshot() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


def build_claims(mart_dir: Path) -> dict[str, Any]:
    summary = json.loads((mart_dir / "REAL_RUN_SUMMARY.json").read_text(encoding="utf-8"))
    landing = json.loads((mart_dir / "fact_landing_observation.json").read_text(encoding="utf-8"))
    interrupts = json.loads((mart_dir / "fact_interrupt_element.json").read_text(encoding="utf-8"))

    sample = summary["collection_markers"]["analysis_sample"]
    axis_c = summary["analysis_axes"]["axis_c_initial_screen_obstruction"]
    attribution = summary["cause_attribution"]["attribution"]
    recovery = summary["depth_recovery_analysis"]

    attempted = sample["attempted_observations"]
    coverage_vals = sorted(
        float(row["max_overlay_coverage"])
        for row in landing
        if row.get("max_overlay_coverage") is not None
    )
    n_obs = len(coverage_vals)
    full = [v for v in coverage_vals if v >= 0.999]
    zero = [v for v in coverage_vals if v <= 0.0001]
    middle = [v for v in coverage_vals if 0.0001 < v < 0.999]

    label_table = axis_c["interrupt_final_label_table"]
    unknown = next(r for r in label_table if r["label"] == "UNKNOWN")
    paths = {
        (p["dismiss_control_exists"], p["dismiss_succeeded"]): p["n"]
        for p in axis_c["dismissal_paths"]
    }

    def claim(text: str, basis: str) -> dict[str, str]:
        return {"grade": CLAIM_GRADE, "claim": text, "basis": basis}

    # ── 1. 축 C 기술통계 ────────────────────────────────────────────
    axis_c_claims = [
        claim(
            f"L0 산출물을 보유한 {n_obs}개 관측에서 방해요소 {len(interrupts)}건이 탐지됐다.",
            "fact_landing_observation · fact_interrupt_element 행수",
        ),
        claim(
            f"그 {len(interrupts)}건 중 `final_label`이 `UNKNOWN`인 것이 "
            f"{unknown['n']}건({unknown['pct']}%)으로 최대 범주다.",
            "fact_interrupt_element.final_label 집계",
        ),
        claim(
            f"{n_obs}개 관측 중 {len(full)}건"
            f"({round(len(full) / n_obs * 100, 1)}%)에서 방해요소가 뷰포트를 완전히 덮었고, "
            f"{len(zero)}건은 겹침이 없었으며, 나머지 {len(middle)}건의 median은 "
            f"{round(st.median(middle), 4)}이다.",
            "max_overlay_coverage 3구간 분해 (median 단독 인용 금지 규칙 준수)",
        ),
        claim(
            f"닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우 "
            f"{paths[('0', '1')]}건, 컨트롤이 탐지됐으나 닫기가 실패한 경우 "
            f"{paths[('1', '0')]}건, 컨트롤이 탐지되고 닫힌 경우 {paths[('1', '1')]}건, "
            f"컨트롤이 탐지되지 않고 닫히지도 않은 경우 {paths[('0', '0')]}건이다.",
            "dismiss_control_exists x dismiss_succeeded 4조합 동등 비중",
        ),
    ]

    # ── 2. 축 B 원인 분해 ───────────────────────────────────────────
    guard = attribution["guard_granularity"]
    rule = attribution["archetype_endpoint_rule"]
    unres = attribution["unresolved"]
    axis_b_claims = [
        claim(
            f"{attempted}개 서비스 전수를 시도해 대표기능 진입 깊이(MPFED)가 산출된 것은 0건이다.",
            "fact_task_entry.MPFED 전건 NULL",
        ),
        claim(
            f"관측된 초기 화면 중 {guard['n']}개에 로그인/구매/가입 관련 텍스트 후보가 존재했고, "
            f"계정행동 가드가 그 지점에서 탐색을 중단시켰다"
            f"(LOGIN {guard.get('by_category', {}).get('LOGIN', '—') if isinstance(guard.get('by_category'), dict) else '—'} 등).",
            "batch outcome=ACCOUNT_ACTION_BLOCKED · blocked_category",
        ),
        claim(
            f"본 연구 계약이 대표기능 endpoint로 인정하지 않는 archetype에서 gate에 도달해 "
            f"진입 깊이가 정의상 산출되지 않은 경우가 {rule['n']}건이다.",
            "archetype-endpoint 규칙 (계약 설계)",
        ),
        claim(
            f"탐색이 종결 상태에 이르지 못한 경우가 {unres['n']}건이며, 사유별로 "
            f"{unres['by_budget_reason']}로 분해된다. 사유가 기록되지 않은 "
            f"{unres['by_budget_reason'].get('unresolved_reason_unrecorded', 0)}건은 "
            f"다른 사유로 배정하지 않고 미기록으로 남겼다.",
            "budget_reason 기준 분해 (endpoint_status_detail 단독 근거 사용 안 함)",
        ),
        claim(
            f"gate 종류 판별이 UNDETERMINED로 떨어져 fail-closed 규칙이 endpoint 승격을 "
            f"거부한 발화가 {summary['cause_attribution']['e6b_fired_n']}건이고, 그중 실제로 "
            f"결과를 바꾼 것은 {summary['cause_attribution']['e6b_binding_n']}건이다.",
            "발화와 구속의 구분 — 발화 횟수를 원인으로 쓰면 과대평가된다",
        ),
        claim(
            f"가드가 개입하지 않고 탐색이 실제로 수행된, 계약상 승격 불가 archetype "
            f"{recovery['scout_ran_non_promoting_endpoint_reached'].split('/')[1].strip()}건에서 "
            f"endpoint 도달은 "
            f"{recovery['scout_ran_non_promoting_endpoint_reached'].split('/')[0].strip()}건이다.",
            "반사실 대조 — 가드가 구속 조건인지 확인",
        ),
    ]

    # ── 3. 축 A 미평가 사실 ─────────────────────────────────────────
    axis_a_claims = [
        claim(
            "본 수집에서 KWCAG criterion 판정은 수행되지 않았다 — 판정기가 구현돼 있지 않다.",
            "저장소 전체에 criterion 평가 실행 경로 부재 · fact_criterion_result 0행",
        ),
        claim(
            f"프레임 {attempted}개 중 현행 WA 인증 join 3요건 충족은 0건이었다.",
            "dim_certification 0행",
        ),
    ]

    return {
        "axis_c": axis_c_claims,
        "axis_b": axis_b_claims,
        "axis_a": axis_a_claims,
        "attempted": attempted,
        "n_obs": n_obs,
        "summary": summary,
    }


def render_process_findings() -> list[str]:
    """`CLAIM_GOVERNANCE §4.5` — 과정에서 발견된 것.

    **서술 순서가 고정돼 있다: 오류가 먼저, 그것을 잡은 구조가 나중이다.**
    이 절을 "잘 했다"로 쓰면 그 순간 기록의 값이 사라진다.
    """
    lines: list[str] = []
    add = lines.append

    add("## 4.5 과정에서 발견된 것")
    add("")
    add(
        "**이 절은 성과 보고가 아니다.** 오늘 검증 실수가 7건 있었고 **그중 상당수는 "
        "결론을 바꿀 수 있었다.** 오류를 먼저 적고, 그것이 산출물에 남지 않은 경위를 "
        "나중에 적는다."
    )
    add("")

    # ── (a) ────────────────────────────────────────────────────────
    add("### (a) 점검 목록에 한 칸이 비어 있었다")
    add("")
    add(
        "'있다고 가정했으나 없었던' 것이 세 번 나왔다. **이것은 서로 다른 세 사고가 "
        "아니라 한 개의 점검 누락이 세 번 발현된 것이다.** '세 번 실수했다'가 아니라 "
        "**'점검 목록에 한 칸이 비어 있었다'**가 정확하다."
    )
    add("")
    add("**비어 있던 칸의 이름:**")
    add("")
    add('> **"이 단계의 산출물을 만드는 코드가 실재하는가"**')
    add("> — 상류 산출물의 존재를 하류 단계의 존재로 추론하지 않는다.")
    add("")
    add("**세 번 다 같은 칸이 비어 있었다:**")
    add("")
    add("| 시각 | 추론 | 없었던 것 | 발견 시점 |")
    add("|---|---|---|---|")
    add(
        "| 12:24 | 수집 evidence가 있으니 → 실행 경로가 있으리라 | REAL_TARGET 실행 경로 | 발사 직전 |"
    )
    add("| 13:58 | 실행 경로가 있으니 → E001도 되리라 | E001_FULL 실행 경로 | 발사 직전 |")
    add("| 14:38 | 수집이 끝났으니 → 판정이 따라오리라 | KWCAG criterion 평가기 | mart 빌드 중 |")
    add("")
    add(
        "셋 다 상류는 있고 하류가 없었으며, 셋 다 '준비 완료' 보고 이후에 발견됐다. "
        "이것은 축별 관측(**수집기는 만들어졌고 판정기는 만들어지지 않았다**)과 같은 "
        "형태다 — 코드에서 나타난 구조가 프로세스에서도 같은 모양으로 나타났다. "
        "마지막 건은 오늘의 통계 산출물이 계산 불가능해진 직접 원인이다."
    )
    add("")

    # ── (b) ────────────────────────────────────────────────────────
    add("### (b) 검증 실수 7건 — 두 유형으로 압축된다")
    add("")
    add("7건을 나열하는 대신 두 유형으로 정리한다. 다음 수행자가 점검할 항목이 둘로 줄어든다.")
    add("")
    add("**유형 1 — 형식 미확인.** 값을 보고 형식을 확인하지 않고 비교·해석했다.")
    add("")
    add("| 사례 | 주체 | 잡은 쪽 |")
    add("|---|---|---|")
    add("| `scout_invoked` 필드를 보고도 워커 표현을 그대로 옮김 | B | C |")
    add("| `manifest` 키 이름을 보고 값 내용을 추론 | B | B 자신 |")
    add("| sha256 선언값의 `sha256:` 접두 미제거 후 비교 → 5/5 불일치 오판 | A | A 자신 |")
    add("")
    add("**유형 2 — 범위 확장.** 확인한 것을 확인하지 않은 것으로 일반화했다.")
    add("")
    add("| 사례 | 주체 | 잡은 쪽 |")
    add("|---|---|---|")
    add("| `SCOUT_ERROR` 표본 1건의 notes를 3건 전체로 서술 | A | C |")
    add("| 실행 경로 1개 확인 후 전 단계 존재 추론 — (a)의 3회 발현 | B | 발사 직전/빌드 중 |")
    add("| 시각을 셸에서 읽지 않고 앞 메시지에서 외삽 | B | B 자신 |")
    add("| `§1-2` 판정 근거를 B 보고에서 인용하고 원본 미확인 | A | C |")
    add("")
    add(
        "마지막 건은 유형 2에 두되 구별되는 특징이 있다 — **확인 대상을 원본에서 "
        "중간 보고로 대체**한 것이다. 범위를 넓힌 것이 아니라 출처를 바꾼 것이므로, "
        "점검할 때는 '얼마나 넓게 일반화했는가'와 함께 '무엇을 근거로 삼았는가'도 봐야 한다."
    )
    add("")
    add("**누가 잡았는가**")
    add("")
    add("```")
    add("C → A  2건      A 자신  1건")
    add("A → B  1건      B 자신  2건      C → B  1건")
    add("```")
    add("")
    add(
        "**C가 A를 두 번 잡았다.** 역할과 도구가 다른 행위자들에게서 같은 두 유형이 "
        "나왔다는 것, 그리고 하위가 상위를 잡은 사례가 있다는 것이 이 실수들을 개인의 "
        "부주의가 아니라 **구조적 패턴**으로 읽어야 하는 근거다."
    )
    add("")

    # ── (c) ────────────────────────────────────────────────────────
    add("### (c) 서로 다른 경로가 같은 값에 도달한 지점")
    add("")
    add(
        "핵심은 **같은 코드를 여러 번 돌린 것이 아니라 서로 다른 경로가 같은 값에 "
        "도달했다**는 것이다. 대표 사례 — C가 `mapping_status` 필터 없는 다른 조인 경로"
        "(`web_eligibility_shadow` ⋈ `representative_task_candidate` on "
        "`canonical_service_key`, frozen_order 59키 제한)로 축 B 귀속 6종을 재계산해 "
        "전건 일치했다. 같은 스크립트를 두 번 돌렸다면 이 일치는 아무것도 증명하지 못한다."
    )
    add("")
    add("**하위 실행자가 상위 지시의 범위를 넘어 결함을 잡은 사례가 세 층 모두에서 나왔다.**")
    add("")
    add("| 층 | 발견 |")
    add("|---|---|")
    add("| 워커 → B | `§1-7`의 `protocol_version` 누락(지시는 두 SHA만) |")
    add(
        "| C → A | `§1-2` 판정 근거가 사실과 다름 · `CLAIM_GOVERNANCE` 초판이 축 A 산출을 전제한 오류 |"
    )
    add("| B → A | control tip이 계속 움직여 승격 명령이 매번 stale해지는 구조 |")
    add("")
    add("**상위가 하위를 검사하는 단방향 구조였으면 이 중 어느 것도 안 잡혔다.**")
    add("")
    add("**검사를 넘어 거부까지 간 사례 1건**")
    add("")
    add(
        "`batch_id` 중복을 이중 수집 신호로 판별하라는 지시를 실행하지 않고 되돌린 건은 "
        "**검사가 아니라 거부다.** 실측 확인 결과 워커들이 각자 `b0001`부터 번호를 매기므로 "
        "**지시대로 구현했으면 정상적인 4워커 수집이 매번 오류로 막혔을 것이다.** "
        "판별 키를 `target_id` 중복으로 바꿔 지시의 의도(이중 수집 탐지)는 지켰다. "
        "지시를 따르면서 결과가 틀리는 경우가 있고, 그때는 실행 전에 되돌려야 한다 — "
        "검사보다 한 단계 더 나간 행동이라 따로 적는다."
    )
    add("")

    return lines


def render_limitations(mart_dir: Path) -> str:
    """`LIMITATIONS` — A가 "숨기면 안 된다"로 의무화한 항목 전부.

    문장은 **새로 쓰지 않는다** — A 원문(`assurance/out/C_BACKLOG.json`의
    `limitations_sentence`, `older_relevance_registry.LIMITATIONS_REQUIRED_ITEMS`,
    `REAL_RUN_SUMMARY`의 확정 문구)을 그대로 옮긴다.
    """
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from analysis.older_relevance_registry import (
        LIMITATIONS_REQUIRED_ITEMS,
        NOT_AN_EXTERNAL_STANDARD_NOTICE,
    )

    summary = json.loads((mart_dir / "REAL_RUN_SUMMARY.json").read_text(encoding="utf-8"))
    recovery = summary["depth_recovery_analysis"]
    axis_c = summary["analysis_axes"]["axis_c_initial_screen_obstruction"]
    markers = summary["collection_markers"]

    lines: list[str] = []
    add = lines.append
    add("# LIMITATIONS — E001")
    add("")
    add(f"**스냅샷** {_snapshot()} (Asia/Seoul)")
    add("")
    add(
        "아래 항목은 **숨기면 안 되는 것**으로 등재됐다. 문장은 A 원문을 그대로 옮겼다 "
        "— 요약하거나 완화하지 않는다."
    )
    add("")

    # ── 1 ──
    add("## 1. 로컬 추적 ref 위조 가능성 (미해소)")
    add("")
    add(
        "수집 개시 판정이 읽는 릴리스 문서 경로가 로컬 추적 ref 기반이며, 이는 로컬 쓰기 "
        "권한을 가진 행위자가 위조할 수 있다. 오늘 수집에서는 발사 직전 fetch 로 완화했다."
    )
    add("")
    add(
        "firewall이 릴리스 문서를 `git show origin/control/...`로 읽는데 "
        "`refs/remotes/origin/*`는 로컬 파일이라 `git update-ref`로 위조 가능하다. "
        "**V2-C015에서 승격 스크립트에 대해 시정한 것과 동일 결함 계열이며, "
        "오늘은 완화했을 뿐 해소하지 않았다.**"
    )
    add("")

    # ── 2 ──
    add("## 2. `E000_PLAN` 부모 해시 재현 불가")
    add("")
    add(
        "E000_PLAN.json 의 e000_plan_hash_candidate 는 placeholder 바이트를 해싱한 뒤 "
        "덮어쓴 구조라 최종 산출물만으로 재현할 수 없다. 부모 계보는 "
        "parent_plan.commit_sha 로 검증되며, **해시 필드는 검증 기능을 갖지 않는다.**"
    )
    add("")

    # ── 3 ──
    add("## 3. `PROTOCOL_VERSION` 명명 부채")
    add("")
    add(
        "PROTOCOL_VERSION 문자열에 fixture 가 남아 있으나 이는 observation_id 안정성을 "
        "위해 유지된 것이며 **실행 종류를 나타내지 않는다.**"
    )
    add("")

    # ── 4 ──
    add("## 4. 반사실의 비무작위 배정 한계")
    add("")
    add(f"{recovery['inference_limit']}")
    add("")
    add(
        f"따라서 회복 상한 {recovery['depth_recovery_upper_bound']}(정직한 범위 "
        f"`{recovery['honest_range']}`)은 **현재 collector/measurement 구현 하에서의 "
        "조건부 값**이다. 이 값을 '올바른 task-definition wiring과 signal detector를 "
        "구현해도 depth는 최대 8'로 확대해 읽으면 **거짓이다.**"
    )
    add("")

    # ── 5 ──
    add("## 5. older-relevant 태깅은 연구진 판정이다")
    add("")
    add(f"> {NOT_AN_EXTERNAL_STANDARD_NOTICE}")
    add("")
    for i, item in enumerate(LIMITATIONS_REQUIRED_ITEMS, start=1):
        add(f"{i}. {item}")
    add("")

    # ── 6 ──
    add("## 6. E000 batch-0 재사용 무효 — 분석 표본이 아니다")
    add("")
    add(f"{markers['cohort_policy_note']}")
    add("")
    add(
        "collector SHA가 상이하므로(E000 `a86b4c7` / E001 `222ef2c`) E000 6건은 "
        "**분석 표본이 아니라 측정기·evidence lineage 검증 산출물**이다."
    )
    add("")

    # ── 7 ──
    add("## 7. E000 `§1-2` FAIL 예외 등재")
    add("")
    add(
        "E000이 `MART_ACCEPTANCE §1-2`(`observation_id` 유일·NULL 0·중복 0) 기준을 "
        "충족하지 못했다. **기준을 재해석해 통과시키지 않고 예외로 등재한다** — "
        "미충족을 충족으로 바꾸는 재해석은 기준 자체를 무효화하기 때문이다. "
        "E000은 위 6항에 따라 분석 표본이 아니므로 이 예외가 분석 결과에 들어가지 않는다."
    )
    add("")

    # ── 8 ──
    add("## 8. 축 C 47% 미분류")
    add("")
    add(f"{axis_c['classification_incomplete_note']}")
    add("")
    add(
        f"`final_label`이 `UNKNOWN`인 것이 "
        f"{axis_c['interrupt_final_label_unknown_n']}건"
        f"({axis_c['interrupt_final_label_unknown_pct']}%)으로 최대 범주다. "
        "유형 분포를 인용할 때 이 값을 각주로 빼지 않는다."
    )
    add("")

    # ── 9 ──
    add("## 9. `NOT_AUTOMATABLE`로 인한 `EligibleOlderRelevant` 축소")
    add("")
    add(f"{LIMITATIONS_REQUIRED_ITEMS[3]}")
    add("")
    add(
        "오늘은 축 A가 평가되지 않아 이 축소가 실제 값으로 나타나지도 못했다 — "
        "분모 자체가 산출되지 않았다."
    )
    add("")

    # ── 10 (기존 항목 유지) ──
    add("## 10. `DUPLICATE_AUTOMATED_REQUESTS_TO_REAL_HOSTS`")
    add("")
    add(
        "발사 명령 중복 투입으로 두 차례에 걸쳐 실제 서비스 호스트 7곳에 중복 자동요청이 "
        "발생했다. 데이터 무결성에는 영향이 없으나(중복 run 은 격리·미참조), 대상 서버에 "
        "불필요한 부하를 준 사실을 기록한다."
    )
    add("")
    add(
        "E000_FAST 에서 발사 명령 중복으로 두 수집 프로세스가 동시에 실행되어 실제 "
        "호스트에 중복 요청이 나갔다. 참조되지 않은 3개 run 은 "
        "CONCURRENT_LAUNCH_SUPERSEDED 로 격리했으며 분석에 쓰지 않는다."
    )
    add("")
    add("**세 지점이 모두 기여했다** — 명령 전달 방식 자체가 중복에 취약했다.")
    add("")
    add("| 주체 | 기여 |")
    add("|---|---|")
    add("| A | 발사 명령을 여러 차례 제시했다 (E000) |")
    add("| B | 4워커 명령을 한 덩어리로 전달해 워커별 성공 확인이 어려웠다 (E001 w02) |")
    add("| Director | 오타 복구 재실행 (`--worker01` 붙여쓰기 · `ccd` 오타 → Exit 1 후 재시도) |")
    add("")
    add(
        "배타 생성 가드가 두 번 다 막았고 데이터 무결성 영향은 0이다. 그러나 **실제 상용 "
        "호스트 7곳에 중복 요청이 나간 사실은 남는다 — 데이터가 오염되지 않았다고 없던 "
        "일이 되지 않는다.** 이 항목은 검증 실수가 아니라 오케스트레이션 실수이므로 "
        "STATS §4.5의 검증 실수 표에 포함하지 않는다."
    )
    add("")
    return "\n".join(lines)


def render_markdown(data: dict[str, Any], mart_dir: Path) -> str:
    summary = data["summary"]
    recovery = summary["depth_recovery_analysis"]
    axis_c = summary["analysis_axes"]["axis_c_initial_screen_obstruction"]
    manifest_ref = summary["manifest"]

    lines: list[str] = []
    add = lines.append
    add("# STATISTICAL_RESULTS — E001")
    add("")
    add(f"**스냅샷** {_snapshot()} (Asia/Seoul)")
    add(f"**등급** {summary['grade']} — {summary['grade_note']}")
    add(f"**mart manifest** `{manifest_ref['path']}` (`{manifest_ref['sha256'][:23]}…`)")
    add("")
    add("## 0. 이 산출물이 무엇인가")
    add("")
    add(
        "**계약이 지정한 통계 분석은 오늘 evidence로 계산 불가능하다.** 종속변수가 "
        "존재하지 않기 때문이다(§3 참조). 그 자리를 대체 분석으로 채우지 않았다 — "
        "쓸 수 있는 데이터를 보고 분석을 고르면 그것은 계약을 결과에 맞추는 것이 된다."
    )
    add("")
    add(
        "**비어 있다는 것은 결함이 아니라 결과다.** 계약이 지정한 분석이 계산 불가능하다는 "
        "사실을 보고하는 것이 오늘의 통계 산출물이다. 아래 네 절이 그 내용이다."
    )
    add("")
    add(
        "모든 claim에 등급을 붙였다. 오늘 산출된 등급은 **정의·기술통계·직접 관측**뿐이며, "
        "association 기반 상위 등급은 계산 대상 자체가 없어 존재하지 않는다."
    )
    add("")

    add("## 1. 축 C — 초기 화면 방해요소 (기술통계)")
    add("")
    add(f"상태: `{axis_c['status']}` — {axis_c['status_expansion']}")
    add("")
    for c in data["axis_c"]:
        add(f"- **[{c['grade']}]** {c['claim']}")
        add(f"  - 근거: {c['basis']}")
    add("")
    add(f"- 분포 형태: {axis_c['max_overlay_coverage']['bimodal_note']}")
    add(f"- 분류 미완: {axis_c['classification_incomplete_note']}")
    add("")
    add("**서술 제약**")
    add("")
    for key in ("dismissal_narrative_constraint", "full_coverage_narrative_constraint"):
        block = axis_c[key]
        add(f"- ○ {block['correct']}")
        for forbidden in block["forbidden"]:
            add(f"  - ✗ {forbidden}")
        add(f"  - {block['principle']}")
    add("")

    add("## 2. 축 B — 진입 깊이 미산출의 원인 분해")
    add("")
    for c in data["axis_b"]:
        add(f"- **[{c['grade']}]** {c['claim']}")
        add(f"  - 근거: {c['basis']}")
    add("")
    add("### 축 B는 수집 전에 구조적으로 확정돼 있었다")
    add("")
    add(f"{summary['analysis_axes']['axis_b_predetermined']}")
    add("")
    add(f"{summary['analysis_axes']['axis_b_honest_refusal']}")
    add("")
    add("### 반사실 — 가드는 구속 조건인가")
    add("")
    add(f"- {recovery['finding']}")
    add(f"- 회복 상한: {recovery['honest_range']} — {recovery['honest_range_note']}")
    add(f"- **적용 범위**: {recovery['scope_condition']}")
    add(f"- **추론 한계**: {recovery['inference_limit']}")
    add("")
    add(
        "- 이 결과는 **가드 입도를 정밀화하면 달라질 수 있다**(post-E001 backlog 등재). "
        "동시에, 안전 계약(로그인·결제·본인인증 금지)을 유지하는 한 자동 관측에는 "
        "**원리적 상한이 있을 수 있다** — 이것이 방법론적 시사점이며, 오늘 데이터로 그 "
        "상한의 크기를 확정하지는 못한다."
    )
    add("")

    add("## 3. 축 A — 미평가")
    add("")
    for c in data["axis_a"]:
        add(f"- **[{c['grade']}]** {c['claim']}")
        add(f"  - 근거: {c['basis']}")
    add("")
    add(
        "이 축은 **평가되지 않았다.** 수집 실패가 아니라 평가 단계 자체가 부재했다. "
        "따라서 계약이 지정한 통계 분석의 종속변수가 존재하지 않으며, 그것이 위 §0의 "
        "계산 불가 사유다."
    )
    add("")

    lines.extend(render_process_findings())

    add("## 5. 방법론적 결론")
    add("")
    add(f"{summary['analysis_axes']['unified_finding']}")
    add("")
    add(f"{summary['analysis_axes']['methodological_conclusion']}")
    add("")
    add("---")
    add("")
    add(
        "> 본 연구는 실제 고령자의 행동·포기·학습효과를 직접 관측하지 않았다. "
        "어떤 결과도 그것을 말하지 않는다. 오늘 N은 작고 그 사실이 모든 문장에 따라다닌다."
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mart-dir", required=True)
    args = parser.parse_args()

    mart_dir = Path(args.mart_dir)
    data = build_claims(mart_dir)
    markdown = render_markdown(data, mart_dir)

    # 우리 문서를 우리가 먼저 스캔한다 — 반려 패턴이 있으면 산출 자체를 실패시킨다.
    assert_clean(markdown)

    md_path = mart_dir / "STATISTICAL_RESULTS.md"
    md_path.write_text(markdown, encoding="utf-8")

    ledger = {
        "document_type": "STATISTICAL_RESULTS",
        "snapshot_at": _snapshot(),
        "grade": data["summary"]["grade"],
        "contract_specified_analysis": {
            "status": "NOT_COMPUTABLE",
            "reason": "종속변수가 존재하지 않는다 — 판정기 부재로 축 A가 평가되지 않았다.",
            "substitute_made": False,
            "substitute_policy": (
                "대체 분석을 만들지 않는다. 쓸 수 있는 데이터를 보고 분석을 고르면 "
                "계약을 결과에 맞추는 것이 된다."
            ),
        },
        "claims": {
            "axis_c_descriptive": data["axis_c"],
            "axis_b_cause_attribution": data["axis_b"],
            "axis_a_not_evaluated": data["axis_a"],
        },
        "claim_count": len(data["axis_c"]) + len(data["axis_b"]) + len(data["axis_a"]),
        "all_claims_graded": True,
        "grades_used": [CLAIM_GRADE],
        "forbidden_pattern_scan": {"patterns_checked": len(FORBIDDEN_PATTERNS), "hits": 0},
        "markdown": {
            "path": md_path.name,
            "sha256": f"sha256:{hashlib.sha256(md_path.read_bytes()).hexdigest()}",
        },
        "mart_manifest_ref": data["summary"]["manifest"],
    }
    limitations = render_limitations(mart_dir)
    assert_clean(limitations)
    lim_path = mart_dir / "LIMITATIONS.md"
    lim_path.write_text(limitations, encoding="utf-8")
    ledger["limitations"] = {
        "path": lim_path.name,
        "sha256": f"sha256:{hashlib.sha256(lim_path.read_bytes()).hexdigest()}",
    }

    ledger_text = json.dumps(ledger, ensure_ascii=False, indent=2)
    assert_clean(ledger_text)
    (mart_dir / "STATISTICAL_RESULTS.json").write_text(ledger_text, encoding="utf-8")
    print(f"claims={ledger['claim_count']} · forbidden_hits=0 · {md_path}")


if __name__ == "__main__":
    main()
