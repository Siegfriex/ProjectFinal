#!/usr/bin/env python3
"""Remediation case 추출 — 뼈대 (목표 2.8, TIMEBOX EXECUTION SSOT).

**아직 실제 데이터가 없다.** 이 스크립트는 실제 E001 marts가 들어왔을 때 그대로
돌릴 수 있는 선택 로직의 **뼈대**다 — 지금은 synthetic universe로만 end-to-end를
검증했다. 실제 서비스 이름·화면을 이 스크립트가 만들지 않는다.

## 선택 기준 (오케스트레이터 지시 4항, 전부 게이트 — 가중합 종합점수 아님)

1. **evidence completeness** — `measurement_status=MEASURED` + `screenshot_path`·
   `dom_path` 존재.
2. **distinct mechanism** — `_MECHANISM_TAXONOMY`에 매칭되는, 이미 선택된 케이스와
   **다른** 결손 유형(예: dismiss control 부재 vs ARIA role 부재)이어야 한다.
   같은 메커니즘의 사례를 여러 개 뽑지 않는다 — 그러면 "대표 3건"이 사실 "1건의
   3배 반복"이 된다.
3. **clear screenshot** — `screenshot_path` 존재(evidence completeness와 겹치되,
   실제 데이터에서는 파일 존재와 별개로 crop 품질이 다를 수 있어 별도 필드로 남긴다).
4. **clear remediation** — 매칭된 mechanism이 알려진 시정안(`remediation_hint`)을
   갖고 있어야 한다. 시정안이 없는 mechanism은 후보에서 제외한다.

세 축(KWCAG/entry friction/certification)을 단일 점수로 합치지 않는 원칙과 같은
이유로, 이 네 기준도 **가중합 스코어로 합치지 않는다** — 전부 게이트(통과/탈락)로
쓰고, 게이트를 통과한 후보 중에서는 mechanism 다양성만으로 최대 `max_cases`건을 고른다.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # research/landing_accessibility

import pandas as pd
from analysis.marts.builders import BUILDERS
from analysis.marts.synthetic import generate_synthetic_universe

#: 알려진 결손 메커니즘 → 사람이 읽는 이름 + 시정 힌트. `interrupt` 행의 어떤
#: 필드 조합이 매칭되는지는 `_match_mechanism`이 판정한다. 실제 데이터가 들어오면
#: 이 표를 늘릴 수 있다 — 코드를 다시 짤 필요는 없다.
_MECHANISM_TAXONOMY: tuple[dict[str, Any], ...] = (
    {
        "mechanism_id": "MISSING_DISMISS_CONTROL",
        "label": "닫기 컨트롤 부재",
        "match": lambda row: str(row.get("dismiss_control_exists")) == "0",
        "remediation_hint": (
            "명시적 닫기 컨트롤(버튼 role, accessible name 포함, 최소 히트 영역 확보)을 "
            "모달 최상단에 추가한다."
        ),
    },
    {
        "mechanism_id": "DISMISS_CONTROL_NOT_VISIBLE",
        "label": "닫기 컨트롤 존재하나 비가시",
        "match": lambda row: (
            str(row.get("dismiss_control_exists")) == "1"
            and str(row.get("dismiss_control_visible")) == "0"
        ),
        "remediation_hint": "닫기 컨트롤을 viewport 안으로, 배경보다 충분한 대비로 이동한다.",
    },
    {
        "mechanism_id": "MISSING_ARIA_MODAL_SEMANTICS",
        "label": "role=dialog인데 aria-modal 부재",
        "match": lambda row: (
            str(row.get("role_dialog")) == "1" and str(row.get("aria_modal")) == "0"
        ),
        "remediation_hint": '`aria-modal="true"`를 부여하고 포커스 트랩을 확인한다.',
    },
    {
        "mechanism_id": "PRIMARY_ACTION_BLOCKED_NO_BACKDROP_CLICK",
        "label": "주요 액션을 가리는데 배경 클릭 닫기 미지원",
        "match": lambda row: (
            str(row.get("blocks_primary_action")) == "1"
            and str(row.get("backdrop_detected")) == "1"
            and str(row.get("dismiss_succeeded")) == "0"
        ),
        "remediation_hint": "배경(backdrop) 클릭 또는 Escape 키로 닫히도록 dismiss 경로를 추가한다.",
    },
)


@dataclass(frozen=True)
class RemediationCandidate:
    observation_id: str
    interrupt_id: str
    web_target_id: str | None
    mechanism_id: str
    mechanism_label: str
    remediation_hint: str
    screenshot_path: str | None
    dom_path: str | None
    final_label: str | None


def _match_mechanism(row: pd.Series) -> dict[str, Any] | None:
    for mechanism in _MECHANISM_TAXONOMY:
        if mechanism["match"](row):
            return mechanism
    return None


def _evidence_complete(landing_row: pd.Series | None) -> bool:
    if landing_row is None:
        return False
    if str(landing_row.get("measurement_status")) != "MEASURED":
        return False
    return bool(landing_row.get("screenshot_path")) and bool(landing_row.get("dom_path"))


def select_remediation_cases(
    marts: dict[str, pd.DataFrame], *, max_cases: int = 3
) -> list[RemediationCandidate]:
    """게이트 4개를 통과한 후보 중 mechanism이 서로 다른 최대 `max_cases`건을 고른다.

    빈 입력이면 빈 리스트를 돌려준다 — 실패하지 않는다.
    """
    interrupt = marts.get("fact_interrupt_element", pd.DataFrame())
    landing = marts.get("fact_landing_observation", pd.DataFrame())
    if interrupt.empty or landing.empty:
        return []

    landing_by_obs = landing.set_index("observation_id")

    candidates: list[RemediationCandidate] = []
    for _, row in interrupt.iterrows():
        obs_id = row.get("observation_id")
        landing_row = landing_by_obs.loc[obs_id] if obs_id in landing_by_obs.index else None

        # 게이트 1 · 3 — evidence completeness / clear screenshot.
        if not _evidence_complete(landing_row):
            continue

        # 게이트 2 · 4 — distinct mechanism이 있고 그 mechanism에 시정 힌트가 있어야 한다.
        mechanism = _match_mechanism(row)
        if mechanism is None:
            continue

        candidates.append(
            RemediationCandidate(
                observation_id=str(obs_id),
                interrupt_id=str(row.get("interrupt_id")),
                web_target_id=(
                    str(landing_row.get("web_target_id")) if landing_row is not None else None
                ),
                mechanism_id=mechanism["mechanism_id"],
                mechanism_label=mechanism["label"],
                remediation_hint=mechanism["remediation_hint"],
                screenshot_path=(
                    str(landing_row.get("screenshot_path")) if landing_row is not None else None
                ),
                dom_path=str(landing_row.get("dom_path")) if landing_row is not None else None,
                final_label=row.get("final_label"),
            )
        )

    # mechanism 다양성 — 같은 mechanism_id는 한 번만 대표로 남긴다.
    seen_mechanisms: set[str] = set()
    selected: list[RemediationCandidate] = []
    for candidate in candidates:
        if candidate.mechanism_id in seen_mechanisms:
            continue
        seen_mechanisms.add(candidate.mechanism_id)
        selected.append(candidate)
        if len(selected) >= max_cases:
            break
    return selected


_TEMPLATE_HEADER = """# REMEDIATION_CASES

`shadow_lane=ANALYSIS_CURRENT` · 최대 3건 · 선택 기준: evidence completeness ·
distinct mechanism · clear screenshot · clear remediation (4개 게이트, 가중합
아님 — `scripts/extract_remediation_cases.py` docstring 참조).

> **Evidence-based redesign proposal; user outcome not evaluated.**
> 아래 시정안은 관측된 evidence(DOM/AX/geometry/screenshot)에 근거한 제안이며,
> 고령층 사용자의 실제 성공률·만족도를 측정하거나 예측하지 않는다 (`00 §Hard Scope`
> — full-task usability·실제 고령자 성공률 추정은 이 연구의 범위 밖이다).

"""


def render_remediation_cases_md(candidates: list[RemediationCandidate]) -> str:
    lines = [_TEMPLATE_HEADER.rstrip()]
    lines.append("")
    if not candidates:
        lines.append(
            "_(현재 후보 없음 — 실제 데이터가 들어오기 전이거나, 게이트를 통과한 사례가 없다.)_"
        )
        lines.append("")
        lines.append(
            "게이트를 통과한 사례가 0건인 것은 실패가 아니라 사실이다. 억지로 채우지 않는다."
        )
        lines.append("")
        lines.append("> Evidence-based redesign proposal; user outcome not evaluated.")
        return "\n".join(lines)

    for idx, candidate in enumerate(candidates, start=1):
        lines.append(f"## Case {idx} — {candidate.mechanism_label}")
        lines.append("")
        lines.append(f"- `mechanism_id`: `{candidate.mechanism_id}`")
        lines.append(f"- `web_target_id`: `{candidate.web_target_id}`")
        lines.append(f"- `observation_id`: `{candidate.observation_id}`")
        lines.append(f"- `interrupt_id`: `{candidate.interrupt_id}`")
        lines.append(f"- `final_label`: `{candidate.final_label}`")
        lines.append(f"- screenshot: `{candidate.screenshot_path}`")
        lines.append(f"- DOM evidence: `{candidate.dom_path}`")
        lines.append("")
        lines.append(f"**시정 제안**: {candidate.remediation_hint}")
        lines.append("")
        lines.append(
            "> Evidence-based redesign proposal; user outcome not evaluated. "
            "이 제안은 evidence 기반 재설계 제안이며 실제 사용자 성과를 평가하지 않았다."
        )
        lines.append("")
    return "\n".join(lines)


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-path", default="artifacts/analysis_current/REMEDIATION_CASES.md")
    parser.add_argument("--n-services", type=int, default=24)
    parser.add_argument("--max-cases", type=int, default=3)
    parser.add_argument("--empty", action="store_true", help="빈 입력 경로를 확인한다")
    args = parser.parse_args()

    if args.empty:
        rows_by_table: dict[str, list[dict[str, Any]]] = {name: [] for name in BUILDERS}
    else:
        rows_by_table = generate_synthetic_universe(n_services=args.n_services).as_dict()
    marts = {table: BUILDERS[table](rows).frame for table, rows in rows_by_table.items()}

    candidates = select_remediation_cases(marts, max_cases=args.max_cases)
    md = render_remediation_cases_md(candidates)

    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"REMEDIATION_CASES → {out_path} ({len(candidates)}건)")


if __name__ == "__main__":
    _main()
