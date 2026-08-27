"""E000/E001 배치 결과 JSON에서 수집 마커를 파생한다 — **수집기를 바꾸지 않는다.**

가드 차단과 E-6b 발화는 이미 `<out_dir>/batches/batch_*.json`의 `results[].detail`에
전부 들어 있다. 수집기에 새 필드(`l1_guard_blocked`/`e6b_fired`)를 요구하면
collector SHA가 바뀌므로, **읽는 쪽에서 파생**한다.

## 파생 규칙 — 실제 배치 파일과 엔진 코드를 읽고 정했다(추측 아님)

**가드 차단** (`guard_blocked`)
: `outcome == "ACCOUNT_ACTION_BLOCKED"`. 이 건들은 `detail.scout_invoked == false`이며
  `blocked_category`(LOGIN/PURCHASE/SIGNUP …)와 `blocked_reason`을 갖는다. Scout가
  아예 돌지 않았으므로 endpoint/MPFED 필드 자체가 없다.

**E-6b 발화** (`e6b_fired`) — `A2 §1.5.1a` 규칙 E-6b(비대칭 fail-closed)
: gate는 관측됐으나 **gate 종류를 확정하지 못해**(`auth_gate_kind = UNDETERMINED`)
  endpoint 승격을 거부한 경우다. 배치 파일에서는 `detail.notes`에 판별기가 남긴
  `"gate 판별: UNDETERMINED - …"` 문자열이 **명시적 마커**로 들어온다
  (`engine/gate_classifier.py`가 강제분류를 거부하며 기록한다).
  보강 조건으로 `endpoint_status == "AUTH_GATE_REACHED"` ·
  `endpoint_status_detail != "ENDPOINT_VIA_AUTH_GATE"` · `auth_gate_observed == 1`을
  함께 확인한다 — 승격되지 않았음을 값으로도 확인한다.

  **주의**: endpoint_status 조합만으로는 E-6b(종류 미확정)와 E-6a(그 archetype이
  애초에 gate를 endpoint로 인정하지 않음)를 구분할 수 없다. 그래서 `notes` 마커를
  **1차 근거**로 쓰고, 마커가 없으면 `e6b_fired`로 세지 않는다(과대계상 금지).

## 배치 미발견과 0건의 구분

배치 디렉터리를 **못 찾은 경우**(`batches_found=False`)와 **찾았는데 0건인 경우**를
구분한다. 전자는 "확인 불가"이고 후자만 "0건"이다 — 이 구분이 없으면 수집이 안 된
것과 가드가 안 걸린 것이 같아 보인다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

#: `gate_classifier`가 종류 미확정 시 남기는 마커 (규칙 E-6b fail-closed).
_E6B_NOTE_RE = re.compile(r"gate\s*판별\s*:\s*UNDETERMINED")

GUARD_BLOCKED_OUTCOME = "ACCOUNT_ACTION_BLOCKED"


def find_batch_files(batches_dir: str | Path) -> list[Path]:
    d = Path(batches_dir)
    if not d.is_dir():
        return []
    return sorted(d.glob("batch_*.json"))


def load_batch_results(batches_dir: str | Path) -> tuple[list[dict[str, Any]], list[Path]]:
    """`batch_*.json`들의 `results[]`를 이어붙여 돌려준다. (results, 읽은 파일들)."""
    files = find_batch_files(batches_dir)
    results: list[dict[str, Any]] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        results.extend(payload.get("results", []) or [])
    return results, files


def _is_guard_blocked(result: dict[str, Any]) -> bool:
    detail = result.get("detail") or {}
    if str(result.get("outcome") or detail.get("outcome")) == GUARD_BLOCKED_OUTCOME:
        return True
    # 보강 — Scout가 아예 호출되지 않았고 차단 사유가 기록된 경우.
    return detail.get("scout_invoked") is False and bool(detail.get("blocked_category"))


def _is_e6b_fired(result: dict[str, Any]) -> bool:
    detail = result.get("detail") or {}
    notes = detail.get("notes") or []
    return any(_E6B_NOTE_RE.search(str(n)) for n in notes)


def _e6b_value_corroborated(result: dict[str, Any]) -> bool:
    """값 쪽에서도 '승격되지 않은 gate'인지 확인한다(마커의 보강 근거)."""
    detail = result.get("detail") or {}
    return (
        str(detail.get("endpoint_status")) == "AUTH_GATE_REACHED"
        and str(detail.get("endpoint_status_detail")) != "ENDPOINT_VIA_AUTH_GATE"
        and str(detail.get("auth_gate_observed")) in {"1", "True"}
    )


def derive_collection_markers(batches_dir: str | Path) -> dict[str, Any]:
    """배치 결과에서 가드 차단·E-6b 발화 계수를 파생한다.

    배치를 못 찾으면 `batches_found=False`이며 **계수를 0으로 단정하지 않는다**.
    """
    results, files = load_batch_results(batches_dir)
    if not files:
        return {
            "batches_found": False,
            "batches_dir": str(batches_dir),
            "n_batch_files": 0,
            "n_results": 0,
            "guard_blocked_n": None,
            "guard_blocked_by_category": {},
            "e6b_fired_n": None,
            "outcome_counts": {},
            "note": (
                f"배치 디렉터리에서 batch_*.json을 찾지 못했다({batches_dir}) — "
                "가드/E-6b 계수는 **확인 불가**이며 0건이 아니다."
            ),
        }

    guard_by_category: dict[str, int] = {}
    guard_n = 0
    e6b_n = 0
    e6b_corroborated = 0
    outcome_counts: dict[str, int] = {}
    for result in results:
        detail = result.get("detail") or {}
        outcome = str(result.get("outcome") or detail.get("outcome") or "UNKNOWN")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        if _is_guard_blocked(result):
            guard_n += 1
            category = str(detail.get("blocked_category") or "UNSPECIFIED")
            guard_by_category[category] = guard_by_category.get(category, 0) + 1
        if _is_e6b_fired(result):
            e6b_n += 1
            if _e6b_value_corroborated(result):
                e6b_corroborated += 1

    return {
        "batches_found": True,
        "batches_dir": str(batches_dir),
        "n_batch_files": len(files),
        "n_results": len(results),
        "guard_blocked_n": guard_n,
        "guard_blocked_by_category": guard_by_category,
        "e6b_fired_n": e6b_n,
        "e6b_value_corroborated_n": e6b_corroborated,
        "outcome_counts": outcome_counts,
        "derivation": (
            "guard_blocked = outcome ACCOUNT_ACTION_BLOCKED (scout_invoked=false, "
            "blocked_category 보유). e6b_fired = detail.notes의 'gate 판별: UNDETERMINED' "
            "마커(규칙 E-6b fail-closed). 수집기를 바꾸지 않고 배치 결과에서 파생했다."
        ),
    }


def guard_blocked_target_ids(batches_dir: str | Path) -> set[str]:
    results, _ = load_batch_results(batches_dir)
    return {
        str(r.get("target_id"))
        for r in results
        if _is_guard_blocked(r) and r.get("target_id") is not None
    }
