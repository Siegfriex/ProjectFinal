"""RQ-D11 — 원장(batch ledger)의 measured 집합과 evidence run 집합이 일치하는가.

파생 근거: C-BLOCKER-220418 이 W1 fixture e2e 에서 '두 프로세스가 target 을 나눠 가져
proc2 의 실측이 원장에 없고(고아 evidence) 원장은 그 target 을 억제됨으로 기록' 하는 구조를
보고했다. C 는 이것이 '2026-08-27 05:14 w02 형태에서 정확히 재발할 구조' 라고 썼다.

RQ: 그 구조가 **E001 raw 에서 실제로 발생했는가?**

경쟁가설
  H1 OCCURRED    E001 원장과 evidence 가 어긋난 target 이 있다
  H2 CONSISTENT  두 소스가 일치한다 — C 의 구조는 fixture 에서만 나타났다
  H3 PARTIAL     일부 worker 에서만 어긋난다

C 의 수치를 사실로 받지 않는다. E001 batch 파일과 evidence 디렉터리에서 독립 재계산한다.

read-only. 산출: results/RQ_D11_ledger_vs_evidence.json
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
RD = Path(__file__).resolve().parents[1]
WORKERS = ("01", "02", "03", "04")
RUN_RE = re.compile(r"^e001_full-wtg_([0-9a-f]+)-(.+)$")


def worker_root(n: str) -> Path:
    return REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}"


def main() -> int:
    per_worker = {}
    for n in WORKERS:
        root = worker_root(n)
        bdir, edir = root / "batches", root / "evidence"
        ledger: dict[str, list[dict]] = defaultdict(list)
        chain = []
        for bf in sorted(bdir.glob("*.json")) if bdir.exists() else []:
            b = json.loads(bf.read_text())
            chain.append({"batch_id": b.get("batch_id"), "index": b.get("batch_index"),
                          "committed_at": b.get("committed_at"),
                          "target_count": len(b.get("target_ids") or []),
                          "result_count": len(b.get("results") or []),
                          "prev": b.get("previous_batch_hash"), "hash": b.get("batch_hash")})
            for r in b.get("results") or []:
                ledger[r["target_id"].replace("wtg_", "")].append(
                    {"batch_id": b.get("batch_id"), "outcome": r.get("outcome"),
                     "attempts": r.get("attempts"), "error": r.get("error"),
                     "same_cause_on_retry": r.get("same_cause_on_retry")})
        ev: dict[str, list[str]] = defaultdict(list)
        for d in sorted(p for p in edir.iterdir() if p.is_dir()) if edir.exists() else []:
            m = RUN_RE.match(d.name)
            if not m:
                continue
            sealed = (d / "run.json").exists()
            man = d / "manifest.jsonl"
            nart = sum(1 for _ in man.open()) if man.exists() else 0
            ev[m.group(1)].append({"dir": d.name, "sealed": sealed, "artifacts": nart})

        led_t, ev_t = set(ledger), set(ev)
        outcomes = Counter(o["outcome"] for v in ledger.values() for o in v)
        # 원장이 '측정됨' 으로 본 것 = SUPPRESSED/DUPLICATE 계열이 아닌 것
        # 원장이 '측정 안 됨' 으로 명시한 outcome. SKIPPED_RETRY_EXHAUSTED 를 빠뜨리면
        # 원장이 정직하게 기록한 실패를 D 가 'ghost' 로 잘못 세게 된다 — 1차 실행에서 실제로 그랬다.
        NOT_MEASURED = ("SUPPRESS", "DUPLICATE", "SKIPPED", "RETRY_EXHAUSTED", "ABORT")

        def is_suppressed(o: str | None) -> bool:
            return bool(o) and any(k in o.upper() for k in NOT_MEASURED)
        measured_in_ledger = {t for t, v in ledger.items() if not all(is_suppressed(o["outcome"]) for o in v)}
        has_sealed_evidence = {t for t, v in ev.items() if any(x["sealed"] and x["artifacts"] > 0 for x in v)}

        per_worker[f"w{n}"] = {
            "batch_files": len(chain), "chain": chain,
            "ledger_targets": len(led_t), "evidence_targets": len(ev_t),
            "outcome_distribution": dict(outcomes),
            "ledger_only": sorted(led_t - ev_t),
            "evidence_only_ORPHAN": sorted(ev_t - led_t),
            "measured_in_ledger": len(measured_in_ledger),
            "has_sealed_evidence": len(has_sealed_evidence),
            "ledger_measured_but_no_evidence": sorted(measured_in_ledger - has_sealed_evidence),
            "evidence_but_ledger_suppressed": sorted(has_sealed_evidence - measured_in_ledger),
            "targets_with_multiple_evidence_dirs": {t: [x["dir"] for x in v]
                                                    for t, v in ev.items() if len(v) > 1},
            "targets_with_multiple_ledger_rows": {t: v for t, v in ledger.items() if len(v) > 1},
        }

    orphan = sum(len(w["evidence_only_ORPHAN"]) for w in per_worker.values())
    ghost = sum(len(w["ledger_measured_but_no_evidence"]) for w in per_worker.values())
    mismatch = sum(len(w["evidence_but_ledger_suppressed"]) for w in per_worker.values())
    total_mismatch = orphan + ghost + mismatch
    if total_mismatch == 0:
        verdict = "REFUTED"      # H1 미발생
    elif all(len(w["evidence_only_ORPHAN"]) == 0 for w in per_worker.values()):
        verdict = "PARTIALLY_SUPPORTED"
    else:
        verdict = "SUPPORTED"

    out = {
        "rq": "RQ-D11",
        "title": "E001 원장의 measured 집합과 evidence run 집합이 일치하는가",
        "derived_from": "C-BLOCKER-220418 (W1 fixture e2e 에서 관측된 원장 귀속 분열)",
        "c_claim_not_taken_as_fact": ("C 는 이 구조가 '2026-08-27 05:14 w02 형태에서 정확히 재발할 구조' "
                                      "라고 썼다. D 는 그 주장을 hypothesis 로만 받고 E001 batch 파일과 "
                                      "evidence 디렉터리에서 독립 재계산했다."),
        "competing_hypotheses": {
            "H1_OCCURRED": "E001 에서 원장과 evidence 가 어긋난 target 이 있다",
            "H2_CONSISTENT": "두 소스가 일치한다 — fixture 에서만 나타난 구조다",
            "H3_PARTIAL": "일부 worker 에서만 어긋난다",
        },
        "not_measured_outcomes": ["SUPPRESS*", "DUPLICATE*", "SKIPPED*", "*RETRY_EXHAUSTED*", "ABORT*"],
        "classification_correction": ("1차 실행에서 SKIPPED_RETRY_EXHAUSTED 를 '측정됨' 으로 분류해 "
                                      "ghost 3건이 나왔다. 원장은 그 3건을 정직하게 retry 소진으로 "
                                      "기록했고 결함이 아니었다. 분류를 시정했고 시정 전 수치도 남긴다."),
        "pre_correction_totals": {"orphan": 0, "ghost": 3, "suppressed_but_measured": 0},
        "definitions": {
            "ORPHAN": "evidence 디렉터리는 있는데 원장에 target 행이 없다",
            "GHOST": "원장은 측정됨으로 기록했는데 sealed evidence 가 없다",
            "SUPPRESSED_BUT_MEASURED": "원장은 억제/중복으로 기록했는데 sealed evidence 가 있다",
        },
        "grain": "web_target_group per worker",
        "totals": {"orphan": orphan, "ghost": ghost,
                   "suppressed_but_measured": mismatch, "total_mismatch": total_mismatch},
        "per_worker": per_worker,
        "verdict": verdict,
    }
    (RD / "results" / "RQ_D11_ledger_vs_evidence.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"{'worker':<7}{'batches':>8}{'ledger_t':>10}{'evid_t':>8}{'orphan':>8}{'ghost':>7}{'supp_but_meas':>15}")
    for w, v in per_worker.items():
        print(f"{w:<7}{v['batch_files']:>8}{v['ledger_targets']:>10}{v['evidence_targets']:>8}"
              f"{len(v['evidence_only_ORPHAN']):>8}{len(v['ledger_measured_but_no_evidence']):>7}"
              f"{len(v['evidence_but_ledger_suppressed']):>15}")
    print()
    for w, v in per_worker.items():
        print(f"{w} outcome: {v['outcome_distribution']}")
    print()
    for w, v in per_worker.items():
        if v["targets_with_multiple_evidence_dirs"]:
            print(f"{w} evidence 디렉터리 2개 이상인 target: {len(v['targets_with_multiple_evidence_dirs'])}")
            for t, dirs in v["targets_with_multiple_evidence_dirs"].items():
                rows = v["targets_with_multiple_ledger_rows"].get(t)
                print(f"   {t}: evidence x{len(dirs)}  원장행 {len(rows) if rows else 1}개 "
                      f"outcome={[r['outcome'] for r in (rows or [])] or '단일'}")
    print(f"\n총 불일치 = {total_mismatch} (orphan {orphan} / ghost {ghost} / supp_but_meas {mismatch})")
    print(f"verdict = {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
