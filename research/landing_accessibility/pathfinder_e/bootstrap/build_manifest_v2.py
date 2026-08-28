"""P1 — A의 실제 동결 FINAL_MAIN50_MANIFEST.json(v3.0.2) 기준 재구축.

Director 지시(2026-08-28, "재시작, 현시점 기준으로 이후부터 A가 발행한 티켓을 바탕으로
작업시작하라")에 따라, P0 에서 candidate frame 으로 만들었던 산출물을 A 의 실제 frozen
authority manifest 로 교체·보강한다.

바뀌는 것: target 순서(collection_order) · stratum · is_pilot_5 · A 자신의 forbidden_actions
(한국어, family 단위가 아니라 target 단위로 이미 병합돼 있음) · replacement_reserve 31건.
바뀌지 않는 것: target/task/endpoint 자체(A 가 "재정렬하지 않았다"고 명시) — P0 QA 에서 이미
candidate frame 과 50/50 일치 확인됨.

여전히 REAL 아님: real_target_allowed=false 그대로. E 는 여전히 어떤 target 도 열지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path

A_MANIFEST = Path(
    "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_a_control/"
    "research/landing_accessibility/control/v3/FINAL_MAIN50_MANIFEST.json"
)
OUT = Path(__file__).resolve().parent
OLD_MANIFEST = OUT / "ROUTE_WORK_MANIFEST.json"


def main() -> None:
    a = json.loads(A_MANIFEST.read_text(encoding="utf-8"))
    old = json.loads(OLD_MANIFEST.read_text(encoding="utf-8"))
    old_by_id = {t["target_id"]: t for t in old["targets"]}

    qa = {"checks": [], "status": "PASS"}

    def check(name: str, ok: bool, detail: str = "") -> None:
        qa["checks"].append({"check": name, "ok": ok, "detail": detail})
        if not ok:
            qa["status"] = "FAIL"

    check("a_target_count_50", len(a["targets"]) == 50, f"count={len(a['targets'])}")
    check("a_replacement_reserve_31", len(a["replacement_reserve"]) == 31,
          f"count={len(a['replacement_reserve'])}")
    check("real_target_allowed_false", a["real_target_allowed"] is False)
    check("status_frozen", a["status"] == "FROZEN", f"status={a['status']}")

    targets_v2 = []
    for at in sorted(a["targets"], key=lambda t: t["collection_order"]):
        tid = at["target_id"]
        old_t = old_by_id.get(tid)
        # 원본 task/endpoint/URL 은 candidate frame 과 동일해야 한다 — P0 QA 는 이미 확인했으나
        # 여기서도 재확인(entry_url/endpoint_contract 바이트 비교).
        url_match = old_t and old_t["official_entry_url"] == at["starting_url"]
        endpoint_match = old_t and old_t["endpoint_contract"] == at["endpoint_contract"]
        check(f"{tid}_url_unchanged", bool(url_match), f"A={at['starting_url']!r} old={old_t['official_entry_url'] if old_t else None!r}")
        check(f"{tid}_endpoint_unchanged", bool(endpoint_match))

        targets_v2.append({
            "target_id": tid,
            "collection_order": at["collection_order"],
            "family_id": at["family_id"],
            "task_family": at["task_family"],
            "service_name": at["service_name"],
            "provider_type": at["provider_type"],
            "stratum": at["stratum"],
            "starting_url": at["starting_url"],
            "frozen_task": at["frozen_task"],
            "task_instruction": at["task_instruction"],
            "fixed_fixture": at["fixed_fixture"] or None,
            "fixture_override": at["fixture_override"] or None,
            "endpoint_contract": at["endpoint_contract"],
            "forbidden_actions_authoritative": at["forbidden_actions"],
            "mobile_web_eligibility": at["mobile_web_eligibility"],
            "mobile_web_eligibility_note": (
                "A 원본값 그대로 보존 — 여전히 PRECHECK_REQUIRED. E 는 판정하지 않는다."
            ),
            "is_pilot_5": at["is_pilot_5"],
            "e_working_task_contract_hash": old_t["e_working_task_contract_hash"] if old_t else None,
            "e_working_endpoint_contract_hash": old_t["e_working_endpoint_contract_hash"] if old_t else None,
            "scout_status": "NOT_STARTED",
        })

    check("pilot5_count_5", sum(1 for t in targets_v2 if t["is_pilot_5"]) == 5)
    check("pilot5_matches_family_worker_queue",
          sorted(t["target_id"] for t in targets_v2 if t["is_pilot_5"])
          == ["F1-01", "F2-01", "F3-01", "F4-01", "F5-01"])

    manifest_v2 = {
        "manifest_kind": "E_ROUTE_WORK_MANIFEST_V2",
        "authority_status": "AUXILIARY_EXECUTION_EVIDENCE",
        "canonical": False,
        "self_approved": False,
        "generated_by": "claude-e/pathfinder-v3",
        "source": "A 의 실제 동결 authority manifest (P0 의 SSOTV3 candidate frame 대체)",
        "source_path": "research/landing_accessibility/control/v3/FINAL_MAIN50_MANIFEST.json",
        "source_version": a["version"],
        "source_manifest_sha256": a["manifest_sha256"],
        "source_frozen_at_kst": a["frozen_at_kst"],
        "source_frozen_by": a["frozen_by"],
        "real_target_allowed": a["real_target_allowed"],
        "note": (
            "target/task/endpoint 자체는 P0 candidate frame 과 동일함을 재확인(50/50 URL+endpoint "
            "byte match). 새로 반영된 것: collection_order(A 동결 순서, SSOTV3 registry 원순서 그대로) "
            "· stratum(F1 시중7/지방3, F5 ground5/air5) · is_pilot_5 · A 자신의 target-level "
            "forbidden_actions(한국어, 기존 global/family 분리 대신 병합형)."
        ),
        "ordering_rule": "A 의 collection_order 필드 그대로 — 재정렬 금지 원칙 승계",
        "target_count": len(targets_v2),
        "strata": a["strata"],
        "replacement_reserve": a["replacement_reserve"],
        "replacement_rule": a["replacement_rule"],
        "targets": targets_v2,
    }

    (OUT / "ROUTE_WORK_MANIFEST_V2.json").write_text(
        json.dumps(manifest_v2, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "RECONCILE_V2_QA_REPORT.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"QA status: {qa['status']} ({sum(1 for c in qa['checks'] if c['ok'])}/{len(qa['checks'])} pass)")
    for c in qa["checks"]:
        if not c["ok"]:
            print("  [FAIL]", c["check"], c["detail"])
    print(f"wrote: {OUT / 'ROUTE_WORK_MANIFEST_V2.json'}")
    print(f"wrote: {OUT / 'RECONCILE_V2_QA_REPORT.json'}")


if __name__ == "__main__":
    main()
