"""RQ-D13 — duplicate measurement-vector detection.

파생 근거: RQ-D9 worker 가 "서로 다른 두 target 이 byte-identical 관측을 생성" 을 발견했다.
D amendment D5 의 우선순위 4번 항목이다.

RQ: wtg 단위 dedup 으로는 잡히지 않는 중복이 몇 건이며, 그것은 수집기 결함인가
    서비스가 실제로 랜딩을 공유한 것인가?

경쟁가설
  H1 COLLECTOR  수집기가 같은 페이지를 두 target 에 기록했다 (결함)
  H2 SHARED     두 서비스가 실제로 같은 모바일웹 랜딩을 공유한다 (frame 문제이지 결함 아님)
  H3 BLOCKPAGE  WAF/에러/앱설치 유도 페이지가 서로 다른 target 에 동일하게 반환됐다
  H4 NONE       중복이 아니라 우연히 요약 통계만 같다 (원본 바이트는 다르다)

판별 증거
  - manifest.jsonl 의 per-artifact sha256 (T1 바이트 동일성)
  - requested URL / final_url 의 host 비교
  - probe 의 title / final_url

read-only. 산출: results/RQ_D13_duplicate_vector.json
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
RD = Path(__file__).resolve().parents[1]
TABLE = RD / "results" / "D_OBSERVATION_TABLE.csv"
EVIDENCE_ROOTS = {
    f"w{n}": REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}/evidence"
    for n in ("01", "02", "03", "04")
}
SLOTS = ("dom.html", "ax.json", "probe.json", "computed_css.json",
         "screen_initial.png", "screen_fullpage.png")
MART = REPO / ".agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts"
DEGENERATE_CSS_BYTES = 100   # computed_css 가 이보다 작으면 사실상 빈 캡처

# 측정 벡터: 식별자·prior·문자열을 제외한 수치 feature
EXCLUDE = {"in_mart", "sealed", "dom_parse_ok", "probe_present", "has_l0c"}


def host(u: str | None) -> str:
    if not u:
        return ""
    try:
        return (urlparse(u).hostname or "").lower().removeprefix("www.").removeprefix("m.")
    except Exception:
        return ""


def artifact_hashes() -> dict[str, dict[str, str]]:
    """run_dir -> {slot: sha256}"""
    out: dict[str, dict[str, str]] = {}
    for root in EVIDENCE_ROOTS.values():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            man = d / "manifest.jsonl"
            if not man.exists():
                continue
            slots = {}
            for line in man.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                name = r["relpath"].rsplit("/", 1)[-1]
                if name in SLOTS:
                    slots[name] = r["sha256"]
            out[d.name] = slots
    return out


def url_duplicates(rows: list[dict]) -> list[dict]:
    """서로 다른 wtg 가 **동일한 요청 URL** 을 가지는가. 이것은 수집기가 아니라 frame 문제다."""
    by_url = defaultdict(set)
    meta = {}
    for r in rows:
        u = (r["prior_url"] or "").strip()
        if u:
            by_url[u].add(r["wtg"])
            meta.setdefault(r["wtg"], r)
    out = []
    for u, wtgs in by_url.items():
        if len(wtgs) > 1:
            out.append({"requested_url": u, "wtgs": sorted(wtgs),
                        "services": sorted(meta[w].get("prior_service") for w in wtgs),
                        "archetypes": sorted(meta[w].get("prior_archetype") for w in wtgs),
                        "in_mart": {w: meta[w]["in_mart"] for w in sorted(wtgs)}})
    return out


def degenerate_captures(rows: list[dict], man_bytes: dict[str, dict[str, int]]) -> list[dict]:
    """빈 캡처 서명: computed_css 가 사실상 비어 있거나 body 가 비어 있다."""
    out = []
    for r in rows:
        css = man_bytes.get(r["run_dir"], {}).get("computed_css.json")
        empty_css = css is not None and css < DEGENERATE_CSS_BYTES
        empty_body = r.get("dom_body_empty") == "1"
        if empty_css or empty_body:
            out.append({"wtg": r["wtg"], "service": r.get("prior_service"),
                        "requested_url": r.get("prior_url"),
                        "computed_css_bytes": css, "empty_css": empty_css,
                        "dom_bytes": int(r["dom_bytes"]) if r.get("dom_bytes") else None,
                        "dom_body_empty": empty_body,
                        "dom_interactive_n": r.get("dom_interactive_n"),
                        "probe_present": r.get("probe_present"), "in_mart": r["in_mart"]})
    return out


def mart_status_consistency(degen: list[dict]) -> dict:
    lo = json.loads((MART / "fact_landing_observation.json").read_text())
    by_t = {r["web_target_id"].replace("wtg_", ""): r for r in lo}
    rows = []
    for d in degen:
        m = by_t.get(d["wtg"])
        if not m:
            rows.append({**d, "mart": "ABSENT"})
            continue
        rows.append({**d, "measurement_status": m["measurement_status"],
                     "max_overlay_coverage": m["max_overlay_coverage"],
                     "max_primary_action_occlusion": m["max_primary_action_occlusion"]})
    statuses = defaultdict(list)
    for r in rows:
        statuses[r.get("measurement_status", "ABSENT")].append(r["wtg"])
    return {"rows": rows, "status_split": {k: v for k, v in statuses.items()},
            "inconsistent": len(statuses) > 1}


def axis_c_sensitivity(degen_wtgs: set[str]) -> dict:
    import statistics as st
    lo = json.loads((MART / "fact_landing_observation.json").read_text())
    cov = [(r["web_target_id"].replace("wtg_", ""), r["max_overlay_coverage"]) for r in lo]
    allv = [c for _, c in cov if c is not None]
    keep = [c for w, c in cov if c is not None and w not in degen_wtgs]
    ones = [w for w, c in cov if c == 1.0]
    return {
        "n_all": len(allv), "median_all": round(st.median(allv), 4), "mean_all": round(st.mean(allv), 4),
        "n_excl_degenerate": len(keep), "median_excl": round(st.median(keep), 4),
        "mean_excl": round(st.mean(keep), 4),
        "coverage_eq_1_n": len(ones),
        "coverage_eq_1_degenerate_n": sum(1 for w in ones if w in degen_wtgs),
        "note": ("coverage==1.0 의 대다수는 정상 DOM 을 가진 페이지다. 퇴화 관측은 소수이며 "
                 "median 을 바꾸지 않는다. 그러나 그 소수는 서로 같은 URL 이라 독립 관측이 아니다."),
    }


def dismissal_effect() -> dict:
    """l0c step 별 screen_before == screen_after — 강제 dismissal 이 화면을 바꿨는가."""
    step_re = re.compile(r"l0c/(\d+)/screen_(before|after)\.png$")
    same = diff = 0
    per_target = defaultdict(lambda: [0, 0])
    for root in EVIDENCE_ROOTS.values():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            m = re.match(r"^e001_full-wtg_([0-9a-f]+)-", d.name)
            man = d / "manifest.jsonl"
            if not m or not man.exists():
                continue
            steps = defaultdict(dict)
            for line in man.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                mm = step_re.search(r["relpath"])
                if mm:
                    steps[mm.group(1)][mm.group(2)] = r["sha256"]
            for v in steps.values():
                if "before" in v and "after" in v:
                    if v["before"] == v["after"]:
                        same += 1
                        per_target[m.group(1)][0] += 1
                    else:
                        diff += 1
                        per_target[m.group(1)][1] += 1
    tot = same + diff
    no_change_targets = [w for w, (s_, d_) in per_target.items() if d_ == 0 and s_ > 0]
    return {"steps_total": tot, "no_visual_change": same,
            "no_visual_change_rate": round(same / tot, 4) if tot else None,
            "changed": diff, "targets_with_l0c": len(per_target),
            "targets_no_change_in_any_step": len(no_change_targets),
            "no_change_target_ids": sorted(no_change_targets)}


def main() -> int:
    rows = [r for r in csv.DictReader(TABLE.open(encoding="utf-8"))]
    hashes = artifact_hashes()
    man_bytes: dict[str, dict[str, int]] = {}
    for root in EVIDENCE_ROOTS.values():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            man = d / "manifest.jsonl"
            if not man.exists():
                continue
            b = {}
            for line in man.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    b[r["relpath"].rsplit("/", 1)[-1]] = r["bytes"]
            man_bytes[d.name] = b

    # ---- 1. 바이트 동일 artifact 를 공유하는 서로 다른 wtg 쌍 (T1) ----
    by_slot_sha: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        for slot, sha in hashes.get(r["run_dir"], {}).items():
            by_slot_sha[(slot, sha)].append(r)

    cross_target = defaultdict(lambda: {"slots": [], "rows": []})
    for (slot, sha), group in by_slot_sha.items():
        wtgs = {g["wtg"] for g in group}
        if len(wtgs) > 1:
            key = tuple(sorted(wtgs))
            cross_target[key]["slots"].append({"slot": slot, "sha256": sha, "n_obs": len(group)})
            cross_target[key]["rows"] = group

    pairs = []
    for wtgs, info in cross_target.items():
        gs = info["rows"]
        shared = sorted(s["slot"] for s in info["slots"])
        by_wtg = {}
        for g in gs:
            by_wtg.setdefault(g["wtg"], g)
        hosts = {w: host(g["prior_url"]) for w, g in by_wtg.items()}
        finals = {w: host(g.get("probe_final_url")) for w, g in by_wtg.items()}
        titles = {w: (g.get("probe_title") or g.get("dom_title") or "")[:80] for w, g in by_wtg.items()}
        services = {w: g.get("prior_service") for w, g in by_wtg.items()}
        archs = {w: g.get("prior_archetype") for w, g in by_wtg.items()}

        same_host = len(set(hosts.values())) == 1
        same_final = len(set(v for v in finals.values() if v)) == 1 and any(finals.values())
        # 가설 판정
        if "dom.html" in shared and same_final and not same_host:
            verdict = "H2_SHARED_LANDING"
            why = "요청 host 는 다르나 final_url host 가 같다 — 두 서비스가 같은 랜딩으로 수렴했다"
        elif "dom.html" in shared and same_host:
            verdict = "H1_COLLECTOR_OR_SAME_TARGET"
            why = "요청 host 까지 같다 — 사실상 같은 target 이 두 wtg 로 등록됐거나 수집기가 같은 페이지를 두 번 기록"
        elif "dom.html" in shared:
            verdict = "H1_OR_H3_UNRESOLVED"
            why = "dom 바이트가 같은데 host 와 final_url 로는 공유/차단 페이지를 구분할 수 없다"
        else:
            verdict = "H4_PARTIAL_SLOT_ONLY"
            why = f"공유 slot 이 {shared} 뿐 — dom 본문은 다르다"
        pairs.append({
            "wtgs": list(wtgs), "shared_slots": shared,
            "n_shared_slots": len(shared),
            "services": services, "archetypes": archs,
            "requested_hosts": hosts, "final_hosts": finals, "titles": titles,
            "same_requested_host": same_host, "same_final_host": same_final,
            "hypothesis_verdict": verdict, "why": why,
            "shared_sha_sample": info["slots"][:6],
        })

    # ---- 2. 수치 측정벡터 동일성 (약한 신호) ----
    num_cols = [c for c in rows[0]
                if c not in EXCLUDE and re.match(r"^(n_|cap_|dom_|probe_|modal_|dismiss_|"
                                                 r"search_|declared_|article_|motion_|gate_|ax_|css_)", c)]
    vec_map: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if r["probe_present"] != "1":
            continue
        vec_map[tuple(r[c] for c in num_cols)].append(r)
    vec_dupes = []
    for v, group in vec_map.items():
        wtgs = {g["wtg"] for g in group}
        if len(wtgs) > 1:
            vec_dupes.append({"wtgs": sorted(wtgs),
                              "n_obs": len(group),
                              "services": sorted({g["prior_service"] for g in group}),
                              "byte_identical_dom": any(
                                  set(hashes.get(g["run_dir"], {}).get("dom.html") for g in group) == {
                                      hashes.get(group[0]["run_dir"], {}).get("dom.html")}
                                  for _ in [0])})

    out = {
        "rq": "RQ-D13",
        "title": "duplicate measurement-vector detection — wtg dedup 이 놓치는 중복",
        "derived_from": ["RQ-D9 부수발견(byte-identical 관측)", "D amendment D5 우선순위 4"],
        "competing_hypotheses": {
            "H1_COLLECTOR": "수집기가 같은 페이지를 두 target 에 기록 (결함)",
            "H2_SHARED": "두 서비스가 실제로 같은 랜딩 공유 (frame 문제, 결함 아님)",
            "H3_BLOCKPAGE": "WAF/에러/앱설치 페이지가 동일하게 반환",
            "H4_NONE": "요약 통계만 같고 원본 바이트는 다름",
        },
        "grain": "observation (66) / web_target_group (59)",
        "n_observations": len(rows),
        "n_targets": len({r["wtg"] for r in rows}),
        "n_with_manifest": len(hashes),
        "byte_identical_cross_target_pairs": len(pairs),
        "pairs": pairs,
        "numeric_vector_duplicate_groups": len(vec_dupes),
        "numeric_vector_duplicates": vec_dupes,
        "numeric_vector_columns_used": num_cols,
        "verdict": None,
    }
    n_h1 = sum(1 for p in pairs if p["hypothesis_verdict"].startswith("H1"))
    n_h2 = sum(1 for p in pairs if p["hypothesis_verdict"] == "H2_SHARED_LANDING")
    if not pairs:
        out["verdict"] = "NOT_SUPPORTED"
    elif n_h2 and not n_h1:
        out["verdict"] = "REFUTED"      # 수집기 결함 가설이 반증됨
    elif n_h1:
        out["verdict"] = "PARTIALLY_SUPPORTED"
    else:
        out["verdict"] = "INCONCLUSIVE"
    out["summary"] = {"H1_like": n_h1, "H2_shared": n_h2,
                      "H4_partial_slot_only": sum(1 for p in pairs
                                                  if p["hypothesis_verdict"] == "H4_PARTIAL_SLOT_ONLY")}

    url_dupes = url_duplicates(rows)
    degen = degenerate_captures([r for r in rows if r["in_mart"] == "1"], man_bytes)
    degen_wtgs = {d["wtg"] for d in degen}
    out["url_level_duplicates"] = url_dupes
    out["distinct_requested_urls"] = len({(r["prior_url"] or "").strip() for r in rows if r["prior_url"]})
    out["degenerate_captures"] = degen
    out["mart_status_consistency"] = mart_status_consistency(degen)
    out["axis_c_sensitivity"] = axis_c_sensitivity(degen_wtgs)
    out["dismissal_effect"] = dismissal_effect()

    (RD / "results" / "RQ_D13_duplicate_vector.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"observations={len(rows)} targets={out['n_targets']} manifests={len(hashes)}")
    print(f"byte-identical cross-target pairs = {len(pairs)}  {out['summary']}")
    for p in pairs:
        print(f"  {p['wtgs']} slots={p['shared_slots']}")
        print(f"    services={list(p['services'].values())} arch={list(p['archetypes'].values())}")
        print(f"    req_hosts={list(p['requested_hosts'].values())} final={list(p['final_hosts'].values())}")
        print(f"    -> {p['hypothesis_verdict']}: {p['why']}")
    print(f"numeric-vector duplicate groups = {len(vec_dupes)}")
    for v in vec_dupes:
        print(f"  {v['wtgs']} services={v['services']}")
    print()
    print(f"=== URL 수준 중복: {len(url_dupes)} 그룹 | distinct 요청 URL = {out['distinct_requested_urls']} (attempted target {out['n_targets']}) ===")
    for u in url_dupes:
        print(f"  {u['requested_url']}  ->  {u['services']}  wtgs={u['wtgs']}")
    print()
    print(f"=== 퇴화 캡처: {len(degen)}/56 mart target ===")
    for d in out["mart_status_consistency"]["rows"]:
        print(f"  {d['wtg']} {str(d.get('service')):<14} css={d.get('computed_css_bytes')}B dom={d.get('dom_bytes')}B "
              f"interactive={d.get('dom_interactive_n')} -> {d.get('measurement_status')} "
              f"cov={d.get('max_overlay_coverage')} occl={d.get('max_primary_action_occlusion')}")
    print(f"  status 분열 = {out['mart_status_consistency']['inconsistent']} "
          f"{ {k: len(v) for k, v in out['mart_status_consistency']['status_split'].items()} }")
    print()
    ac = out["axis_c_sensitivity"]
    print(f"=== Axis C 민감도: median {ac['median_all']} -> {ac['median_excl']} (퇴화 제외), "
          f"mean {ac['mean_all']} -> {ac['mean_excl']}, coverage==1.0 은 {ac['coverage_eq_1_n']}/56 중 퇴화 {ac['coverage_eq_1_degenerate_n']} ===")
    de = out["dismissal_effect"]
    print(f"=== dismissal 무효과: {de['no_visual_change']}/{de['steps_total']} steps ({de['no_visual_change_rate']:.1%}), "
          f"모든 step 무변화 target {de['targets_no_change_in_any_step']}/{de['targets_with_l0c']} ===")
    print(f"\nverdict = {out['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
