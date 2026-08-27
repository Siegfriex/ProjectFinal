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
from collections.abc import Sequence
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


def derive_collection_markers(
    batches_dir: str | Path | Sequence[str | Path],
    *,
    allow_cross_cohort: bool = False,
) -> dict[str, Any]:
    """단일/복수 배치 디렉터리에서 가드 차단·E-6b 발화 계수를 파생한다.

    복수 소스 처리(워커별 출처 보존·소스별 독립 체인 검증·코호트 분리·이중 수집
    탐지)는 `derive_collection_markers_multi`가 한다 — 이 함수는 그 얇은 진입점이다.
    """
    return derive_collection_markers_multi(batches_dir, allow_cross_cohort=allow_cross_cohort)


def guard_blocked_target_ids(batches_dir: str | Path) -> set[str]:
    results, _ = load_batch_results(batches_dir)
    return {
        str(r.get("target_id"))
        for r in results
        if _is_guard_blocked(r) and r.get("target_id") is not None
    }


# ── 다중 배치 디렉터리(워커) 합산 ─────────────────────────────────────────
#
# E001은 워커 4개가 **독립적으로** 수집한다. 합산할 때 지켜야 할 것:
#
# 1. **워커별 출처를 잃지 않는다** — `by_source`에 worker_id와 디렉터리를 남겨
#    "특정 워커에서만 이상이 나왔다"를 나중에 볼 수 있게 한다.
# 2. **해시 체인은 디렉터리별로 독립이다** — 4개 체인을 하나로 이어붙이지 않는다.
#    체인 검증은 소스별로 하고 계수만 합산한다.
# 3. **E000과 E001을 자동 합산하지 않는다** — `execution_scope`가 다르면
#    (`E000_FAST` vs `E001_FULL`) 기본적으로 거부하고, 명시적 플래그로만 합친다.
# 4. **이중 수집을 조용히 합치지 않는다** — 아래 주석 참조.


class BatchCollectionError(ValueError):
    """배치 합산이 안전하지 않다 — 코호트 혼합·이중 수집 등."""


#: 코호트 식별 키. `execution_scope`가 `E000_FAST` / `E001_FULL`을 가른다.
_COHORT_KEY = "execution_scope"


def _worker_id_from_path(batches_dir: Path) -> str:
    """`.../artifacts/e001_w03/batches` → `e001_w03`. 못 찾으면 디렉터리명."""
    parts = list(batches_dir.resolve().parts)
    if parts and parts[-1] == "batches" and len(parts) >= 2:
        return parts[-2]
    return batches_dir.name


def _verify_chain(payloads: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """**한 디렉터리 안에서만** 해시 체인을 검증한다.

    `batch_index` 순으로 `previous_batch_hash`가 직전 `batch_hash`와 이어지는지
    본다. 첫 배치의 `previous_batch_hash`는 `None`이어야 한다. 다른 워커의
    체인과 이어붙이지 않는다 — 애초에 서로 독립된 체인이다.
    """
    ordered = sorted(payloads, key=lambda d: d.get("batch_index") or 0)
    previous_hash: str | None = None
    for payload in ordered:
        prev_recorded = payload.get("previous_batch_hash")
        if prev_recorded != previous_hash:
            return False, (
                f"batch_index={payload.get('batch_index')} 의 previous_batch_hash="
                f"{str(prev_recorded)[:16]} 가 직전 batch_hash={str(previous_hash)[:16]} 와 다르다"
            )
        previous_hash = payload.get("batch_hash")
    return True, None


def _load_source(batches_dir: str | Path) -> dict[str, Any]:
    """디렉터리 하나를 읽어 소스 레코드를 만든다(계수 + 체인 상태 + 출처)."""
    d = Path(batches_dir)
    files = find_batch_files(d)
    payloads: list[dict[str, Any]] = []
    for path in files:
        try:
            payloads.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "worker_id": _worker_id_from_path(d),
                "batches_dir": str(d),
                "exists": d.is_dir(),
                "n_batch_files": len(files),
                "read_error": f"{path.name}: {exc}",
                "results": [],
                "chain_ok": False,
                "chain_error": "파일을 읽지 못해 체인을 검증할 수 없다",
            }

    results: list[dict[str, Any]] = []
    batch_ids: list[str] = []
    target_ids: list[str] = []
    cohorts: set[str] = set()
    for payload in payloads:
        results.extend(payload.get("results", []) or [])
        batch_ids.append(str(payload.get("batch_id")))
        target_ids.extend(str(t) for t in (payload.get("target_ids") or []))
        scope = (payload.get("provenance") or {}).get(_COHORT_KEY)
        if scope:
            cohorts.add(str(scope))

    chain_ok, chain_error = _verify_chain(payloads) if payloads else (True, None)

    # 같은 디렉터리 안에서 batch_id가 중복되면 그 자체가 이상이다.
    dup_batch_ids = sorted({b for b in batch_ids if batch_ids.count(b) > 1})

    return {
        "worker_id": _worker_id_from_path(d),
        "batches_dir": str(d),
        "exists": d.is_dir(),
        "n_batch_files": len(files),
        "n_results": len(results),
        "batch_ids": batch_ids,
        "target_ids": target_ids,
        "duplicate_batch_ids_within_source": dup_batch_ids,
        "cohorts": sorted(cohorts),
        "chain_ok": chain_ok,
        "chain_error": chain_error,
        "results": results,
    }


def _count_results(results: list[dict[str, Any]]) -> dict[str, Any]:
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
        "guard_blocked_n": guard_n,
        "guard_blocked_by_category": guard_by_category,
        "e6b_fired_n": e6b_n,
        "e6b_value_corroborated_n": e6b_corroborated,
        "outcome_counts": outcome_counts,
    }


def derive_collection_markers_multi(
    batches_dirs: str | Path | Sequence[str | Path],
    *,
    allow_cross_cohort: bool = False,
) -> dict[str, Any]:
    """여러 배치 디렉터리(워커)를 **출처를 유지한 채** 합산한다.

    - 해시 체인은 소스별로 독립 검증한다(이어붙이지 않는다).
    - `execution_scope`가 섞이면(E000_FAST + E001_FULL) `allow_cross_cohort=True`
      가 없는 한 `BatchCollectionError`. collector가 다르므로 기본은 분리다.
    - **이중 수집 탐지는 `target_id` 기준이다.** 워커는 `batch_id`를 각자
      `b0001`부터 매기므로 `batch_id` 중복은 정상이며(실측 확인: w01·w02·w03 모두
      `b0001` 보유), 그걸로 오류를 내면 정상 다중 워커 수집이 전부 막힌다.
      같은 **target**이 두 소스에 나타나는 것이 진짜 이중 수집 신호다.
      `batch_id` 중복은 **같은 디렉터리 안**에서만 이상으로 본다.
    """
    if isinstance(batches_dirs, (str, Path)):
        dirs: list[str | Path] = [batches_dirs]
    else:
        dirs = list(batches_dirs)

    sources = [_load_source(d) for d in dirs]
    existing = [s for s in sources if s["exists"]]
    with_files = [s for s in sources if s.get("n_batch_files")]

    # ── 코호트 혼합 검사 (E000 vs E001 자동 합산 금지) ──
    all_cohorts = sorted({c for s in sources for c in s.get("cohorts", [])})
    if len(all_cohorts) > 1 and not allow_cross_cohort:
        raise BatchCollectionError(
            f"서로 다른 execution_scope를 자동 합산할 수 없다: {all_cohorts}. "
            "E000과 E001은 collector가 다르므로 기본적으로 분리한다 — 합치려면 "
            "allow_cross_cohort=True(CLI: --allow-cross-cohort)를 명시하고 "
            "provenance에 코호트 구분을 남겨라."
        )

    # ── 이중 수집 검사 (target_id 기준, **코호트 안에서**) ──
    #
    # 같은 코호트의 두 워커가 같은 target을 재면 그것은 이중 수집이다 → 오류.
    # 반면 **코호트가 다르면**(E000이 잰 target을 E001이 다시 잰 경우) 그것은
    # 이중 수집이 아니라 **재측정**이다 — collector가 달라 의도된 것이므로
    # 오류로 막지 않고 `cross_cohort_repeated_targets`로 드러내기만 한다.
    duplicate_targets: dict[str, list[str]] = {}
    for cohort in all_cohorts or [None]:
        seen: dict[str, str] = {}
        for source in sources:
            if cohort is not None and cohort not in source.get("cohorts", []):
                continue
            for target in source.get("target_ids", []):
                if target in seen and seen[target] != source["worker_id"]:
                    duplicate_targets.setdefault(target, [seen[target]]).append(source["worker_id"])
                else:
                    seen.setdefault(target, source["worker_id"])
    if duplicate_targets:
        raise BatchCollectionError(
            f"**같은 코호트 안에서** 같은 target이 여러 소스에 나타난다(이중 수집 신호): "
            f"{dict(list(duplicate_targets.items())[:5])}. "
            "조용히 합치지 않는다 — 수집 배치를 확인해야 한다."
        )

    # 코호트 간 재측정은 오류가 아니지만 **반드시 보인다**.
    cohort_targets: dict[str, set[str]] = {}
    for source in sources:
        for cohort in source.get("cohorts", []):
            cohort_targets.setdefault(cohort, set()).update(source.get("target_ids", []))
    cross_cohort_repeated = sorted(
        set.intersection(*cohort_targets.values()) if len(cohort_targets) > 1 else set()
    )

    dup_within = {
        s["worker_id"]: s["duplicate_batch_ids_within_source"]
        for s in sources
        if s.get("duplicate_batch_ids_within_source")
    }
    if dup_within:
        raise BatchCollectionError(
            f"같은 디렉터리 안에서 batch_id가 중복된다: {dup_within}. 조용히 합치지 않는다."
        )

    if not with_files:
        return {
            "batches_found": False,
            "n_sources": len(dirs),
            "n_sources_existing": len(existing),
            "n_batch_files": 0,
            "n_results": 0,
            "cohorts": all_cohorts,
            "cross_cohort_repeated_targets": [],
            "guard_blocked_n": None,
            "guard_blocked_by_category": {},
            "e6b_fired_n": None,
            "outcome_counts": {},
            "by_source": [{k: v for k, v in s.items() if k != "results"} for s in sources],
            "note": (
                "지정된 디렉터리에서 batch_*.json을 하나도 찾지 못했다 — 가드/E-6b 계수는 "
                "**확인 불가**이며 0건이 아니다. (수집이 아직 시작되지 않았을 수 있다.)"
            ),
        }

    all_results = [r for s in sources for r in s["results"]]
    totals = _count_results(all_results)

    by_source = []
    for source in sources:
        record = {k: v for k, v in source.items() if k not in {"results", "target_ids"}}
        record["n_targets"] = len(source.get("target_ids", []))
        record.update(_count_results(source["results"]))
        by_source.append(record)

    chain_all_ok = all(s["chain_ok"] for s in sources)
    return {
        "batches_found": True,
        "n_sources": len(dirs),
        "n_sources_existing": len(existing),
        "n_sources_with_files": len(with_files),
        "n_batch_files": sum(s["n_batch_files"] for s in sources),
        "n_results": len(all_results),
        "cohorts": all_cohorts,
        "cross_cohort_merged": len(all_cohorts) > 1,
        # 코호트 간 **재측정**된 target — 이중 수집이 아니라 의도된 재측정이지만,
        # 합산 계수에는 두 번 들어가므로 반드시 드러낸다.
        "cross_cohort_repeated_targets": cross_cohort_repeated,
        "cross_cohort_repeated_n": len(cross_cohort_repeated),
        "cross_cohort_note": (
            (
                f"코호트 {all_cohorts}를 명시적으로 합산했다. target "
                f"{len(cross_cohort_repeated)}건이 두 코호트에서 재측정됐고 합산 계수에 "
                "**두 번** 들어간다 — 서비스 단위 비율을 이 합산값으로 계산하면 안 된다."
            )
            if len(all_cohorts) > 1
            else "단일 코호트 — 코호트 간 재측정 없음."
        ),
        # 소스별 출처 유지 — "특정 워커에서만 이상이 나왔다"를 볼 수 있게 한다.
        "by_source": by_source,
        "chain_verified_all_sources": chain_all_ok,
        "chain_errors": {s["worker_id"]: s["chain_error"] for s in sources if not s["chain_ok"]},
        "chain_note": (
            "해시 체인은 **소스(워커)별로 독립 검증**했다 — 서로 다른 워커의 체인을 "
            "이어붙이지 않았다. 계수만 합산했다."
        ),
        **totals,
        "derivation": (
            "guard_blocked = outcome ACCOUNT_ACTION_BLOCKED (scout_invoked=false, "
            "blocked_category 보유). e6b_fired = detail.notes의 'gate 판별: UNDETERMINED' "
            "마커(규칙 E-6b fail-closed). 수집기를 바꾸지 않고 배치 결과에서 파생했다."
        ),
    }
