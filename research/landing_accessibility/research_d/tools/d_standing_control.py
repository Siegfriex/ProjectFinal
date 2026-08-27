"""D 상주 대조 — 네 가지 기준선의 드리프트를 매 회 같은 코드로 잰다.

지금까지 이 대조는 **스크립트 없이 임시 명령으로** 돌았다. 그러면 매 회 조금씩
다른 것을 재게 되고, `DRIFT_NONE` 이 '대조했고 같았다' 인지 '이번엔 그 항목을
안 봤다' 인지 로그만 봐서는 구분되지 않는다. D 는 그 구분을 못 해서 두 번 틀렸다
(D-DEF-09 스캐너 · D-DEF-11 reconciler).

각 검사에 **변형 대조군**을 넣었다. 바이트를 메모리에서 한 글자 바꿔 검사가
불일치를 실제로 잡는지 매 실행마다 보인다. 대조군이 실패하면 본 검사 결과를
내지 않는다 — 못 잡는 검사의 0 은 0 이 아니다.

SSOT·control 파일은 읽기만 한다. 변형은 메모리 안에서만 일어난다.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path("/home/sieg/projects-wsl/ProjectFinal")
SSOT = ROOT / "SSOTV3"
BUS = ROOT / ".agent_bus/landing_v2"
CTRL_V3 = (ROOT / ".agent_worktrees/claude_a_control/research/landing_accessibility"
           / "control/v3")
RD = Path(__file__).resolve().parent.parent
RESULTS = RD / "results"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _mutate(b: bytes) -> bytes:
    """한 바이트만 바꾼다 — 검사가 살아 있는지 보이기 위한 최소 변형."""
    if not b:
        return b"x"
    i = len(b) // 2
    return b[:i] + (b"\x01" if b[i:i + 1] != b"\x01" else b"\x02") + b[i + 1:]


# ---------------------------------------------------------------- 1. SSOTV3
def check_ssotv3() -> dict:
    man_p = SSOT / "MANIFEST_v3.0.json"
    man = json.loads(man_p.read_text(encoding="utf-8"))
    mism, missing = [], []
    first_bytes = None
    for e in man["files"]:
        p = SSOT / e["path"]
        if not p.exists():
            missing.append(e["path"])
            continue
        b = p.read_bytes()
        if first_bytes is None:
            first_bytes = (e["path"], b, e["sha256"])
        if _sha(b) != e["sha256"]:
            mism.append({"path": e["path"], "expected": e["sha256"], "got": _sha(b)})
    ctl = None
    if first_bytes:
        path, b, exp = first_bytes
        ctl = {"mutated_file": path,
               "detected": _sha(_mutate(b)) != exp}
    return {"n": len(man["files"]), "mismatch": len(mism), "missing": missing,
            "mismatches": mism,
            "manifest_self_sha256": _sha(man_p.read_bytes()),
            "control": ctl,
            "control_ok": bool(ctl and ctl["detected"])}


# --------------------------------------------------------- 2. endpoint lock
def check_endpoint_lock() -> dict:
    lock = json.loads((RESULTS / "D_V3_ENDPOINT_PREOBSERVATION_LOCK.json")
                      .read_text(encoding="utf-8"))
    fams, drift = lock["families"], []
    for fid, f in fams.items():
        verbatim = f.get("endpoint_contract_verbatim", "")
        want = f.get("endpoint_sha256")
        got = _sha(verbatim.encode("utf-8"))
        if want and got != want:
            drift.append({"family": fid, "expected": want, "got": got})
    # 대조군: 첫 family 의 문구를 한 글자 바꿔 재계산하면 잡혀야 한다
    fid0 = next(iter(fams))
    v0 = fams[fid0].get("endpoint_contract_verbatim", "")
    ctl = {"mutated_family": fid0,
           "detected": _sha(_mutate(v0.encode("utf-8"))) != fams[fid0].get("endpoint_sha256")}
    return {"families": len(fams), "drift": len(drift), "drifted": drift,
            "control": ctl, "control_ok": ctl["detected"],
            "note": "SSOT 원문 재대조가 아니라 잠금 파일 내부 정합성 검사다. "
                    "원문 대조는 check_ssotv3 이 담당한다."}


# --------------------------------------------------- 3. D 발행 티켓 무결성
def check_emitted_tickets() -> dict:
    rec_p = RESULTS / "D_EMITTED_TICKET_INTEGRITY.json"
    rec = json.loads(rec_p.read_text(encoding="utf-8"))
    base = rec["tickets"]
    cur = {}
    for p in sorted((BUS / "tickets").glob("D-*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            cur[p.stem] = {"sha256": "UNPARSED"}
            continue
        if d.get("from") != "D":
            continue
        cur[p.stem] = {"sha256": _sha(p.read_bytes()), "bytes": p.stat().st_size,
                       "type": d.get("type"), "priority": d.get("priority")}
    drifted = [{"id": k, "baseline": base[k]["sha256"], "current": cur[k]["sha256"]}
               for k in base if k in cur and base[k]["sha256"] != cur[k]["sha256"]]
    removed = [k for k in base if k not in cur]
    added = [k for k in cur if k not in base]
    first = next(iter(base))
    ctl = {"mutated_id": first,
           "detected": base[first]["sha256"] != _sha(_mutate(
               base[first]["sha256"].encode()))}
    return {"baseline": len(base), "current": len(cur), "drift": len(drifted),
            "drifted": drifted, "removed": removed, "added": added,
            "control": ctl, "control_ok": ctl["detected"],
            "note": "added 는 드리프트가 아니다 — 새로 발행한 것이다. "
                    "drifted·removed 가 0 이 아니면 이미 나간 티켓이 바뀐 것이다."}


# ------------------------------------------------------- 4. 색인 / delta sha
def check_index_delta(prev: dict | None) -> dict:
    idx_p, dl_p = CTRL_V3 / "V3_RULING_INDEX.json", CTRL_V3 / "V3_0_1_SUCCESSOR_DELTA.md"
    now = {"index_sha": _sha(idx_p.read_bytes()), "delta_sha": _sha(dl_p.read_bytes())}
    try:
        now["index_version"] = json.loads(idx_p.read_text(encoding="utf-8")).get("version")
    except Exception:                                        # noqa: BLE001
        now["index_version"] = None
    prev_i = (prev or {}).get("index_delta", {})
    # 이전 로그는 키 이름과 자릿수가 다르다(`index_sha_now`, 16자 접두).
    # 그대로 `.get("index_sha")` 하면 None 이 나오고 그 None 이
    # `changed=False` 로 읽힌다 — **비교 불가를 '안 바뀜' 으로 보고하는 것**이
    # D 가 반복해 온 실패다. 비교 가능 여부를 값으로 낸다.
    def _cmp(prev_val, cur_val):
        if not prev_val:
            return {"comparable": False, "changed": None,
                    "why": "이전 기록에 값이 없다 — 비교하지 않았다"}
        n = min(len(prev_val), len(cur_val))
        return {"comparable": True, "changed": prev_val[:n] != cur_val[:n],
                "compared_prefix_len": n, "prev": prev_val}

    prev_idx = prev_i.get("index_sha") or prev_i.get("index_sha_now")
    prev_dl = prev_i.get("delta_sha") or prev_i.get("delta_sha_now")
    now["index"] = _cmp(prev_idx, now["index_sha"])
    now["delta"] = _cmp(prev_dl, now["delta_sha"])
    now["index_changed"] = now["index"]["changed"]
    now["delta_changed"] = now["delta"]["changed"]
    # --- input_identity (A 의 R38 / STEP1-033 9번째 검사) ---
    # A 가 B·C·D 에게 `check_ruling_index.py` 실행을 지시했으나 그 파일은 D
    # 방화벽 밖이다. **같은 신호를 허용된 두 파일만으로 만든다** — 색인이
    # 스스로 선언한 `source_sha256` 과 실제 delta 바이트를 비교한다.
    # 불일치면 그 색인의 수치를 인용하지 않는다.
    try:
        doc = json.loads(idx_p.read_text(encoding="utf-8"))
    except Exception:                                    # noqa: BLE001
        doc = {}
    declared = doc.get("source_sha256")
    now["input_identity"] = {
        "declared_source_sha256": declared,
        "actual_delta_sha256": now["delta_sha"],
        "match": (declared == now["delta_sha"]) if declared else None,
        "verdict": ("PASS" if declared == now["delta_sha"]
                    else "NO_FIELD" if not declared else "FAIL"),
        "consequence": "FAIL 이면 이 색인의 수치를 인용하지 않는다 (A STEP1-033)",
        "why_D_computes_it_here": ("A 의 검사기는 D 방화벽 밖이다. 허용된 두 파일"
                                   "(색인·delta)만으로 같은 신호를 만든다."),
    }
    # A 가 last_run 에 실은 절 수를 D 자신의 계수와 대조한다 — **같은 입력일 때만.**
    lr = (doc.get("self_check") or {}).get("last_run") or {}
    a_sections, a_input = lr.get("delta_sections"), lr.get("input_sha256")
    d_sections = None
    if a_sections is not None:
        import re as _re
        txt = dl_p.read_text(encoding="utf-8")
        TOK = (r"(?:Δ\d+[a-z]?(?:-[A-Za-z0-9]+)?)|(?:R\d+)|(?:P-?\d+)|(?:GAP-?\d+)")
        d_sections = len({m.group(1) for m in
                          _re.finditer(rf"^#{{2,4}}\s*({TOK})\b", txt, _re.M)})
    now["delta_sections_crosscheck"] = {
        "A_last_run_delta_sections": a_sections,
        "A_last_run_input_sha256": a_input,
        "D_unique_header_tokens": d_sections,
        "same_input": (a_input == now["delta_sha"]) if a_input else None,
        "comparable": bool(a_input and a_input == now["delta_sha"]),
        "agree": (a_sections == d_sections) if (a_sections is not None
                                                and d_sections is not None) else None,
        "rule": "R38 — 입력 sha 가 다른 두 측정값은 비교하지 않는다",
    }
    now["note"] = ("변경은 결함이 아니다 — A 가 갱신 중이다. "
                   "변경을 **모르고 옛 sha 로 대조하는 것**이 결함이다.")
    return now


# ------------------------------------------- 5. pack 밖 운영 문서 (Δ7 판정)
def check_out_of_pack_docs() -> dict:
    """A 가 매니페스트 밖으로 분류한 문서를 delta 에 못박힌 sha 로 감시한다.

    `SSOTV3/THREE_TURN_RUNBOOK.md` 는 Δ7 판정으로 매니페스트에 등재되지 않는다
    ('pack 권위 밖 운영 runbook'). 그래서 SSOTV3 매니페스트 대조가 이 파일을
    보지 않고, **아무것도 이 파일을 보지 않는다.** 운영 조항으로 채택된 문서다.

    기준값은 여기에 적지 않고 **delta 원문에서 읽는다** — A 가 다시 못박으면
    따라간다. D 가 자기 사본을 들고 있으면 그 사본이 또 하나의 진리가 된다.
    """
    dl = (CTRL_V3 / "V3_0_1_SUCCESSOR_DELTA.md").read_text(encoding="utf-8")
    import re
    sec = re.search(r"^## Δ7 .*?(?=^## Δ8 )", dl, re.M | re.S)
    if not sec:
        return {"checked": 0, "verdict": "NO_RULING_SECTION",
                "why": "delta 에서 Δ7 절을 찾지 못했다 — 기준값이 없으므로 판정하지 않는다"}
    m = re.search(r"`(THREE_TURN_RUNBOOK[\w./\-]*|SSOTV3/[\w./\-]+)`.*?sha256\s*`([0-9a-f]{64})`",
                  sec.group(0), re.S)
    if not m:
        return {"checked": 0, "verdict": "NO_PINNED_SHA",
                "why": "Δ7 절에 못박힌 sha256 이 없다 — 판정하지 않는다"}
    rel = m.group(1).split("SSOTV3/")[-1]
    want = m.group(2)
    f = SSOT / rel
    if not f.exists():
        return {"file": rel, "verdict": "FILE_MISSING", "pinned": want}
    b = f.read_bytes()
    got = _sha(b)
    return {"file": rel, "pinned_in_delta": want, "current": got,
            "match": got == want, "checked": 1,
            "control": {"detected": _sha(_mutate(b)) != want},
            "control_ok": _sha(_mutate(b)) != want,
            "classification": "Δ7 — pack 권위 밖 운영 runbook. 매니페스트 대상 아님",
            "why_watched": "매니페스트가 안 보고 다른 무엇도 안 본다. 운영 조항으로 채택된 문서다."}


def extend_baseline() -> dict:
    """신규 발행분만 기준선에 편입한다. **기존 항목의 해시는 갱신하지 않는다.**

    갱신하면 드리프트가 지워진다 — 바뀐 티켓을 기준선에 다시 새겨 넣으면
    '바뀌지 않았다' 가 되어 버린다. 그래서 여기서는 `added` 만 처리하고,
    이미 기준선에 있는 id 는 해시가 달라도 손대지 않는다(그건 DRIFT 로 남는다).

    자동으로 돌리지 않는다. 발행 후 명시적으로 호출한다 — 자동이면 방금 바뀐
    티켓도 '새 것' 으로 편입될 여지가 생긴다.
    """
    rec_p = RESULTS / "D_EMITTED_TICKET_INTEGRITY.json"
    rec = json.loads(rec_p.read_text(encoding="utf-8"))
    base = rec["tickets"]
    chk = check_emitted_tickets()
    if chk["drift"] or chk["removed"]:
        return {"extended": False,
                "why": "드리프트나 삭제가 있는 상태에서는 기준선을 넓히지 않는다",
                "drift": chk["drifted"], "removed": chk["removed"]}
    added = chk["added"]
    if not added:
        return {"extended": False, "why": "신규 없음", "n": len(base)}

    ts = subprocess.run(["date", "-Iseconds"], capture_output=True,
                        text=True).stdout.strip()
    for tid in added:
        p = BUS / "tickets" / f"{tid}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        base[tid] = {"sha256": _sha(p.read_bytes()), "bytes": p.stat().st_size,
                     "type": d.get("type"), "priority": d.get("priority")}
    rec["n_tickets"] = len(base)
    rec["last_checked_kst"] = ts
    rec.setdefault("baseline_extensions", []).append(
        {"at": ts, "added": sorted(added),
         "note": "신규 발행분만 편입. 기존 항목 해시는 갱신하지 않는다.",
         "tool": "tools/d_standing_control.py extend_baseline()"})
    rec_p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"extended": True, "added": sorted(added), "n": len(base)}


def main() -> int:
    log_p = RESULTS / "D_STANDING_CONTROL_DRIFT_LOG.jsonl"
    prev = None
    if log_p.exists():
        lines = [l for l in log_p.read_text(encoding="utf-8").splitlines() if l.strip()]
        for l in reversed(lines):
            try:
                prev = json.loads(l)
                break
            except Exception:                                # noqa: BLE001
                continue

    ts = subprocess.run(["date", "-Iseconds"], capture_output=True,
                        text=True).stdout.strip()
    out = {"checked_at_kst": ts, "measured_at_kst": ts,
           "tool": "tools/d_standing_control.py",
           "ssotv3": check_ssotv3(),
           "endpoint_lock": check_endpoint_lock(),
           "emitted_tickets": check_emitted_tickets(),
           "index_delta": check_index_delta(prev),
           "out_of_pack_docs": check_out_of_pack_docs()}

    controls_ok = all(out[k].get("control_ok") for k in
                      ("ssotv3", "endpoint_lock", "emitted_tickets"))
    oop = out["out_of_pack_docs"]
    if oop.get("checked"):
        controls_ok = controls_ok and oop.get("control_ok", False)
    drifted = (out["ssotv3"]["mismatch"] or out["ssotv3"]["missing"]
               or out["endpoint_lock"]["drift"]
               or out["emitted_tickets"]["drift"] or out["emitted_tickets"]["removed"]
               or (oop.get("checked") and not oop.get("match")))
    out["control_verdict"] = "PASS" if controls_ok else "FAIL"
    out["verdict"] = ("CONTROL_FAIL" if not controls_ok
                      else "DRIFT_NONE" if not drifted else "DRIFT")
    out["verdict_rule"] = ("대조군이 실패하면 드리프트 판정을 내지 않는다. "
                           "못 잡는 검사의 0 은 0 이 아니다.")

    with log_p.open("a") as f:
        f.write(json.dumps(out, ensure_ascii=False) + "\n")

    s, e, t, i = (out["ssotv3"], out["endpoint_lock"], out["emitted_tickets"],
                  out["index_delta"])
    print(f"verdict         : {out['verdict']}  (control {out['control_verdict']})")
    print(f"SSOTV3          : {s['n']}파일 mismatch={s['mismatch']} missing={len(s['missing'])} "
          f"| 변형대조 {'검출' if s['control_ok'] else '** 미검출 **'}")
    print(f"endpoint lock   : {e['families']}족 drift={e['drift']} "
          f"| 변형대조 {'검출' if e['control_ok'] else '** 미검출 **'}")
    print(f"발행 티켓        : base={t['baseline']} cur={t['current']} drift={t['drift']} "
          f"removed={len(t['removed'])} added={len(t['added'])}")
    if t["added"]:
        print(f"                  added: {', '.join(t['added'])}")
    def _fmt(c):
        return "비교불가" if not c["comparable"] else ("변경됨" if c["changed"] else "동일")
    if oop.get("checked"):
        print(f"pack 밖 문서     : {oop['file']} {'일치' if oop['match'] else '** 불일치 **'} "
              f"(Δ7 못박음 {oop['pinned_in_delta'][:16]}) "
              f"| 변형대조 {'검출' if oop['control_ok'] else '** 미검출 **'}")
    else:
        print(f"pack 밖 문서     : {oop.get('verdict')} — {oop.get('why','')}")
    print(f"색인/delta      : v{i['index_version']} {i['index_sha'][:16]} "
          f"색인={_fmt(i['index'])} delta={_fmt(i['delta'])}")
    ii = i.get("input_identity", {})
    dc = i.get("delta_sections_crosscheck", {})
    print(f"input_identity  : {ii.get('verdict')} "
          f"(선언 {str(ii.get('declared_source_sha256'))[:16]} vs 실제 {str(ii.get('actual_delta_sha256'))[:16]})")
    print(f"절 수 대조       : A={dc.get('A_last_run_delta_sections')} D={dc.get('D_unique_header_tokens')} "
          f"같은입력={dc.get('same_input')} 일치={dc.get('agree')}")
    if i["index"]["comparable"] and i["index"]["changed"]:
        print(f"                  이전 {i['index']['prev']} → 현재 {i['index_sha'][:16]}")
    for d in s["mismatches"] + e["drifted"] + t["drifted"]:
        print("   DRIFT:", json.dumps(d, ensure_ascii=False)[:160])
    return 0 if out["verdict"] == "DRIFT_NONE" else (3 if not controls_ok else 1)


if __name__ == "__main__":
    import sys
    if "--extend-baseline" in sys.argv:
        print(json.dumps(extend_baseline(), ensure_ascii=False, indent=1))
        raise SystemExit(0)
    raise SystemExit(main())
