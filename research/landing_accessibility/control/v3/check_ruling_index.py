#!/usr/bin/env python3
"""V3_RULING_INDEX 자체검사 — 서술이 아니라 실행 가능한 검사기다 (Δ34).

`self_check.last_run` 이 낡은 채로 '깨끗하다' 고 말한 사건(T-B-V3-FINDING-009)에서 나왔다.
누구든 이것을 돌려 색인의 주장을 검증할 수 있다.

    python3 check_ruling_index.py            # 검사만
    python3 check_ruling_index.py --write     # 검사 후 last_run 갱신
"""
import json, re, sys, collections, hashlib, subprocess, os

HERE = os.path.dirname(os.path.abspath(__file__))
IDX = os.path.join(HERE, "V3_RULING_INDEX.json")
DELTA = os.path.join(HERE, "V3_0_1_SUCCESSOR_DELTA.md")
BND = r'(?<![0-9A-Za-z_-])%s(?![0-9A-Za-z_-])'


def token_match(tok, text):
    return bool(re.search(BND % re.escape(tok), text))


def run(idx, delta_text):
    rows = idx["rulings"]
    fail = []

    # 1. 별칭 유일성
    own = collections.defaultdict(list)
    for r in rows:
        for a in r["aliases"]:
            own[a].append(r["id"])
    intentional = idx["self_check"].get("intentional_multi", {})
    dup = {a: v for a, v in own.items() if len(v) > 1}
    unexpected = {a: v for a, v in dup.items() if a not in intentional}
    if unexpected:
        fail.append(("alias_uniqueness", unexpected))

    # 2. 별칭 특정성 — 무관 산문에 걸리면 안 된다
    corpus = idx["alias_rules"]["control_corpus"]
    hits = [(r["id"], a) for r in rows for a in r["aliases"] if token_match(a, corpus)]
    if hits:
        fail.append(("alias_specificity", hits))

    # 3. 유령 별칭 — delta 어디에도 없는 서술 별칭 (Δ25 기준)
    ghost = [(r["id"], a) for r in rows for a in r["aliases"]
             if (re.search(r'[가-힣]', a) or ' ' in a)
             and not token_match(a, delta_text) and a not in delta_text]
    if ghost:
        fail.append(("ghost_alias", ghost))

    # 4. delta 절 커버리지 (delta → index)
    heads = [h.strip() for h in re.findall(
        r'^#{2,3}\s+(Δ[0-9]+(?:-[A-Za-z0-9\-]+)?|R\d+)(?![0-9A-Za-z_-])', delta_text, re.M)]
    allref = set()
    for r in rows:
        allref.add(r["id"]); allref.update(r["aliases"]); allref.add(r.get("authority", ""))
    cont = set(idx.get("container_sections", {}).get("list", []))
    uncovered = [h for h in heads if h not in allref and h not in cont]
    if uncovered:
        fail.append(("delta_section_coverage", uncovered))

    # 5. 역방향 도달성 (index → delta)
    #    경로 4종: id 헤더 · authority 헤더 · 별칭 본문 토큰경계 · split_rows 부모
    #    D-V3-FINDING-015 — 선언에 authority 경로가 빠져 있었고 구현은 쓰고 있었다
    split = idx.get("split_rows", {}).get("map", {})
    hs = set(heads)
    unreachable = []
    for r in rows:
        toks = {r["id"], r.get("authority", "")} | set(r["aliases"])
        if split.get(r["id"]) in hs:
            continue
        if any(t and (t in hs or token_match(t, delta_text)) for t in toks):
            continue
        unreachable.append(r["id"])
    if unreachable:
        fail.append(("index_to_delta_reachability", unreachable))

    # 6. 필수 필드
    need = ("id", "requires", "must_appear_in", "verified_by", "due", "authority", "aliases")
    missing = [(r["id"], k) for r in rows for k in need if not r.get(k)]
    if missing:
        fail.append(("required_field", missing))

    # 7. count 정합
    if idx.get("count") != len(rows):
        fail.append(("count_mismatch", {"count": idx.get("count"), "actual": len(rows)}))

    return fail, {"rows": len(rows), "total_aliases": len(own),
                  "duplicate": len(dup), "unexpected_duplicate": len(unexpected)}


def positive_control(idx, delta_text):
    """검사별 변이 — 각 검사가 자기 결함만 잡는지 하나씩 확인한다.

    이전 판은 결함 하나에 별칭 두 개를 실어 어느 검사가 무엇을 잡았는지
    알 수 없었다. 그 상태의 0 은 근거가 아니다.
    """
    base = json.loads(json.dumps(idx))
    results = {}

    def probe(name, mutate):
        m = json.loads(json.dumps(base))
        m["count"] = len(m["rulings"])   # 변이 **전에** 정합시킨다 — 변이가 count 를 건드릴 수 있다
        mutate(m)
        f, _ = run(m, delta_text)
        results[name] = name in {k for k, _ in f}

    # 의도적 다중(D3-06)이 아닌 별칭을 골라야 한다 — 화이트리스트에 걸리면 못 잡는다
    intentional = set(base["self_check"].get("intentional_multi", {}))
    donor = next(a for r in base["rulings"] for a in r["aliases"] if a not in intentional)

    def dup_probe(m):
        for r in m["rulings"]:
            if donor not in r["aliases"]:
                r["aliases"].append(donor)
                return
    probe("alias_uniqueness", dup_probe)

    probe("alias_specificity",
          lambda m: m["rulings"][0]["aliases"].append("coverage"))
    probe("ghost_alias",
          lambda m: m["rulings"][0]["aliases"].append("존재하지 않는 서술 별칭 XYZ"))

    # delta 본문에 등장하지 않는 id 를 써야 한다.
    # `Δ999-R99` 는 A 가 Δ33 부기에 그 문자열을 쓰는 바람에 delta 에서 도달 가능해졌다 —
    # 문서가 자기 양성대조를 무력화한 사례이므로 여기 남긴다.
    fake = "Δ90001-R901"
    assert fake not in delta_text, "양성대조 id 가 delta 에 등장한다 — 다른 값을 써라"
    probe("index_to_delta_reachability",
          lambda m: m["rulings"].append({"id": fake, "requires": "x",
                                         "must_appear_in": "x", "verified_by": "x",
                                         "due": "상시", "authority": "Δ90001",
                                         "aliases": [fake]}))
    probe("required_field",
          lambda m: m["rulings"][0].__setitem__("requires", ""))
    probe("count_mismatch",
          lambda m: m.__setitem__("count", 99999))

    return {"per_check": results, "ok": all(results.values())}


def main():
    idx = json.load(open(IDX, encoding="utf-8"))
    delta_text = open(DELTA, encoding="utf-8").read()
    fail, stats = run(idx, delta_text)
    pc = positive_control(idx, delta_text)

    print(f"rows={stats['rows']} aliases={stats['total_aliases']} "
          f"dup={stats['duplicate']} unexpected={stats['unexpected_duplicate']}")
    print("positive_control (검사별 변이):")
    for k, v in pc["per_check"].items():
        print(f"    {k:32s} {'잡음' if v else '**못 잡음**'}")
    print(f"    → ok={pc['ok']}")
    if not pc["ok"]:
        print("!! 양성대조 실패 — 검사가 동작하지 않는다. 아래 결과를 근거로 쓰지 마라")
        return 2
    if fail:
        for k, v in fail:
            print(f"FAIL {k}: {v}")
        return 1
    print("PASS — 7개 검사 전부 통과")
    if "--write" in sys.argv:
        idx["self_check"]["last_run"] = {
            "at_kst": subprocess.run(["date", "+%Y-%m-%dT%H:%M:%S%z"], capture_output=True,
                                     text=True, env={**os.environ, "TZ": "Asia/Seoul"}).stdout.strip(),
            "index_version": idx["version"], **stats,
            "positive_control": pc,
            "checker": "control/v3/check_ruling_index.py",
            "staleness_rule": "rows 또는 index_version 이 현재 색인과 다르면 이 결과는 무효다. 그대로 인용하지 마라",
        }
        json.dump(idx, open(IDX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("last_run 갱신")
    return 0


if __name__ == "__main__":
    sys.exit(main())
