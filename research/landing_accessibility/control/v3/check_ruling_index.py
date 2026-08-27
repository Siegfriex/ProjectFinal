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


def run(idx, delta_text, delta_sha=None, writing=False):
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

    # 7-a. 측정값 단일 출처 — 하위 블록에 last_run 이 있으면 사본이 갈린다 (Δ38)
    dupmeas = [k for k, v in idx["self_check"].items()
               if k != "last_run" and isinstance(v, dict) and "last_run" in v]
    if dupmeas:
        fail.append(("measurement_single_source", dupmeas))

    # 7. count 정합
    if idx.get("count") != len(rows):
        fail.append(("count_mismatch", {"count": idx.get("count"), "actual": len(rows)}))

    # 8. 입력 신원 — 측정값만 있고 무엇을 측정했는지가 없으면 시점 간 비교가 불가능하다 (Δ44)
    #    `--write` 중에는 건너뛴다. 갱신이 곧 이 검사의 시정이므로 교착이 된다.
    #    검사만 돌리는 쪽(B/C/D)에게는 **색인이 낡았음**을 알리는 유일한 신호다.
    if not writing and delta_sha is not None:
        decl = idx.get("source_sha256")
        if decl != delta_sha:
            fail.append(("input_identity", {"declared": decl, "actual_delta": delta_sha,
                                            "뜻": "색인이 현재 delta 로 재생성되지 않았다. --write 로 갱신하라"}))

    sections = sorted(set(re.findall(
        r'^#{2,3}\s+(Δ[0-9]+(?:-[A-Za-z0-9\-]+)?|R\d+)(?![0-9A-Za-z_-])', delta_text, re.M)))
    return fail, {"rows": len(rows), "total_aliases": len(own),
                  "duplicate": len(dup), "unexpected_duplicate": len(unexpected),
                  "delta_sections": len(sections), "input_sha256": delta_sha}


def positive_control(idx, delta_text, delta_sha=None):
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

    # 도달성은 **두 방향**으로 고정한다 (C-FINDING-074834).
    #   불 probe  — 어느 경로로도 못 닿는 행 → 반드시 잡혀야 한다
    #   무 probe  — authority 경로로만 닿는 행 → 잡히면 안 된다(선언된 넓은 규칙)
    # 하나만 두면 좁은 규칙과 넓은 규칙을 구분하지 못한다.
    # `Δ999-R99` 는 A 가 Δ33 부기에 그 문자열을 써버려 delta 에서 도달 가능해졌다 —
    # 문서가 자기 양성대조를 무력화한 사례이므로 주석으로 남긴다.
    # probe 값은 **런타임에 delta 에 없는 것으로 고른다.**
    # 고정 리터럴을 쓰면 그 값을 문서에 인용하는 순간 probe 가 죽는다 —
    # A 가 `Δ999-R99` 로 한 번, `Δ90001` 로 또 한 번 그렇게 만들었다.
    # 이제 **모든 토큰의 부재를 확인**하고, 걸리면 다음 후보로 넘어간다.
    def pick(prefix):
        for i in range(900001, 900050):
            rid, auth = f"Δ{i}-R901", f"Δ{i}"
            if all(t not in delta_text for t in (rid, auth)):
                return rid, auth
        raise AssertionError("delta 에 없는 probe 값을 찾지 못했다")

    orphan_id, orphan_auth = pick("orphan")
    probe("index_to_delta_reachability",
          lambda m: m["rulings"].append({"id": orphan_id, "requires": "x",
                                         "must_appear_in": "x", "verified_by": "x",
                                         "due": "상시", "authority": orphan_auth,
                                         "aliases": [orphan_id]}))

    # 음성 대조 — 부모 절이 실재하는 가짜 자식은 authority 경로로 도달해야 한다.
    # 잡히면 구현이 (a)(b)(c) 로 좁혀졌다는 뜻이고 선언과 어긋난다.
    child = next(c for c in (f"Δ32-probe{i}" for i in range(1, 50)) if c not in delta_text)
    m = json.loads(json.dumps(base))
    m["rulings"].append({"id": child, "requires": "x", "must_appear_in": "x",
                         "verified_by": "x", "due": "상시", "authority": "Δ32",
                         "aliases": [child]})
    m["count"] = len(m["rulings"])
    f, _ = run(m, delta_text)
    caught = "index_to_delta_reachability" in {k for k, _ in f}
    results["reachability_authority_path_declared"] = not caught
    probe("required_field",
          lambda m: m["rulings"][0].__setitem__("requires", ""))
    probe("count_mismatch",
          lambda m: m.__setitem__("count", 99999))
    # 입력 신원 — 선언된 source_sha256 을 흐트러뜨리면 잡혀야 한다.
    # 이 probe 만 writing=False 로 돈다(검사 자체가 --write 중 비활성이므로).
    m = json.loads(json.dumps(base))
    m["source_sha256"] = "0" * 64
    m["count"] = len(m["rulings"])
    f, _ = run(m, delta_text, delta_sha=(delta_sha or "1" * 64), writing=False)
    results["input_identity"] = "input_identity" in {k for k, _ in f}

    probe("measurement_single_source",
          lambda m: m["self_check"].setdefault("alias_rules_probe", {}).__setitem__(
              "last_run", {"stale": True}))

    return {"per_check": results, "ok": all(results.values())}


def main():
    idx = json.load(open(IDX, encoding="utf-8"))
    delta_bytes = open(DELTA, "rb").read()
    delta_text = delta_bytes.decode("utf-8")
    delta_sha = hashlib.sha256(delta_bytes).hexdigest()
    writing = "--write" in sys.argv
    fail, stats = run(idx, delta_text, delta_sha=delta_sha, writing=writing)
    pc = positive_control(idx, delta_text, delta_sha=delta_sha)

    print(f"rows={stats['rows']} aliases={stats['total_aliases']} "
          f"dup={stats['duplicate']} unexpected={stats['unexpected_duplicate']} "
          f"sections={stats['delta_sections']}")
    print(f"input delta sha256={delta_sha}"
          f"{'' if writing else ('  선언=' + str(idx.get('source_sha256')))}")
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
    print(f"PASS — {len(pc['per_check'])}개 검사 전부 통과 (변이 probe 로 셈)")
    if writing:
        # R35 셋째 요소 — 실패 시 동작의 실증. **도구 sha 에 묶는다** (Δ46/R40).
        # 실증이 낡으면 `valid_for_this_commit: false` 이며, 없는 실증이 있는 것으로 읽히지 않는다.
        demo_path = os.path.join(HERE, "CONTROL_FAILURE_DEMO.json")
        try:
            demo = json.load(open(demo_path, encoding="utf-8"))
            cur = hashlib.sha256(open(__file__, "rb").read()).hexdigest()
            idx["failure_behavior_demo"] = {
                "sidecar": "control/v3/CONTROL_FAILURE_DEMO.json",
                "verdict": demo.get("verdict"),
                "demonstrated_for_checker_sha256": demo.get("checker_sha256"),
                "current_checker_sha256": cur,
                "valid_for_this_commit": demo.get("checker_sha256") == cur,
                "if_false": "검사기가 바뀌었고 실증은 낡았다. `python3 control_failure_demo.py` 를 다시 돌려라",
            }
        except FileNotFoundError:
            idx["failure_behavior_demo"] = {"verdict": None, "valid_for_this_commit": False,
                                            "if_false": "실증이 없다. control_failure_demo.py 를 돌려라"}
        # 입력 신원을 정본에 박는다 — 측정값만 남기면 시점 간 비교가 불가능하다 (Δ44)
        idx["source_sha256"] = delta_sha
        idx["authority_sha"] = subprocess.run(
            ["git", "-C", HERE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        idx["authority_sha_semantics"] = (
            "이 값을 쓴 시점의 git HEAD 다. **이 갱신 자체는 그 다음 커밋에 담기므로 항상 한 칸 뒤진다.** "
            "정확한 입력 신원은 `source_sha256`(delta 바이트) 이며 그쪽을 인용하라")
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
    # 크래시와 검사 실패가 같은 exit 을 내면 **미실행과 실패가 구분되지 않는다** (Δ46).
    # 이 저장소의 중심 결함이 이 파일 안에 있었다 — 잘못된 색인은 traceback + exit 1 이었고
    # 그것은 "검사가 돌아서 실패했다" 와 같은 코드다.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n!! 검사가 돌지 않았다({type(e).__name__}). 통과로도 실패로도 읽지 마라")
        sys.exit(2)
