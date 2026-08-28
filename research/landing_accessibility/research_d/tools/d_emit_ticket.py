"""D 티켓 발행 단일 경로 — 발행 전에 스키마를 강제한다.

D 는 `D-V3-FINDING-012` 를 `base_sha` 없이 발행했다. v3 Δ26 은 v3 이후 발행분에
해석 가능한 `base_sha` 를 요구한다. 그 누락은 **A 의 전수감사(STEP1-024)에 걸리고
나서야** 보였다 — 발행 시점에 아무것도 막지 않았기 때문이다.

여기서 막는다. 검사에 걸리면 파일을 쓰지 않는다.

  base_sha       실재하는 커밋이어야 한다 (`git cat-file -e <sha>^{commit}`)
  to             D 의 substantive finding 은 `to=[C]` 다 (A6/v3 §4)
  claim_kind     판정어가 아니어야 한다 — D 는 GO/NO-GO/BLOCKER/SUPERSEDE 를 내지 않는다
  heredoc 금지    이 모듈은 dict 를 받는다. 셸 heredoc 은 backtick 을 삼킨다(실제로 겪었다)
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

_LA = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
           "/research/landing_accessibility")
_BASES = [_LA / "research_d", _LA, _LA.parent.parent,
          Path("/home/sieg/projects-wsl/ProjectFinal")]
_PATHLIKE = re.compile(
    r"^(?:research|research_d|tools|results|notebooks|figures|SSOTV3)"
    r"[\w./\-]*\.(?:json|md|ipynb|py|csv|png|jsonl)$")

D_BRANCH = "claude-d/research-sandbox-v21"
D_REMOTE = f"origin/{D_BRANCH}"

BUS = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2")
_HEX40 = re.compile(r"[0-9a-f]{40}")
_BARE_INDEP = re.compile(r"독립\s*(?:재계산|확인|검증|열거|적으로|도달)")
# 측정을 담고 있음을 드러내는 키 이름. 보수적으로 넓게 잡는다 —
# 측정이 아닌데 시각을 요구하는 쪽이, 측정인데 시각 없이 나가는 쪽보다 싸다.
_MEASURE_KEYS = ("measurement", "실측", "measured", "재계산", "recount", "관측된_순서", "the_measurement")
FORBIDDEN_TYPES = {"GO", "NO_GO", "NO-GO", "BLOCKER", "DIRECTIVE", "SUPERSEDE"}


def _sh(*a: str) -> str:
    return subprocess.run(a, capture_output=True, text=True).stdout.strip()


def _reachable_from_remote(sha: str) -> bool:
    """sha 가 D 원격 브랜치에서 도달 가능한가. 원격 ref 를 못 읽으면 True 로 둔다.

    원격을 못 읽는 것은 네트워크·설정 문제이지 티켓의 결함이 아니다.
    거기서 막으면 **막을 이유가 없는 것을 막는다**. 다만 그 경우 검사를
    한 것이 아니므로 self_test 가 그 상태를 드러낸다.
    """
    if subprocess.run(["git", "rev-parse", "--verify", D_REMOTE],
                      capture_output=True).returncode != 0:
        return True
    return subprocess.run(["git", "merge-base", "--is-ancestor", sha, D_REMOTE],
                          capture_output=True).returncode == 0


def check(t: dict) -> list[str]:
    errs: list[str] = []
    tid = t.get("ticket_id", "")
    if not tid.startswith("D-"):
        errs.append(f"ticket_id 는 D- 로 시작해야 한다: {tid!r}")
    if t.get("from") != "D":
        errs.append(f"from 은 'D' 여야 한다: {t.get('from')!r}")

    bs = t.get("base_sha")
    if not bs:
        errs.append("base_sha 누락 — Δ26")
    elif subprocess.run(["git", "cat-file", "-e", f"{bs}^{{commit}}"],
                        capture_output=True).returncode != 0:
        errs.append(f"base_sha 가 실재 커밋이 아니다: {bs}")
    elif not _reachable_from_remote(bs):
        # **다른 평면이 조회할 수 있어야 한다.** 로컬에만 있는 커밋을 base_sha 로
        # 적으면 A 에게는 '해석 불가' 로 보인다 — A 가 STEP1-025 에서 그 사각을
        # 명시했고("A 는 A 의 object store 에 있는 객체만 해석할 수 있다"),
        # 그때는 D 것이 전부 push 돼 있어서 물지 않았다. 물지 않은 것과
        # 막혀 있는 것은 다르다.
        errs.append(f"base_sha 가 {D_REMOTE} 에서 도달 불가 — 먼저 push 하라: {bs}")

    if t.get("type") in FORBIDDEN_TYPES:
        errs.append(f"D 는 {t['type']} 를 발행하지 않는다 (NON_CANONICAL)")
    to = t.get("to")
    if t.get("type") in {"FINDING", "RESEARCH_FINDING", "VALIDITY_RISK_CANDIDATE"} \
            and to != ["C"]:
        errs.append(f"D 의 substantive finding 은 to=[C] 다 (A6/v3 §4): to={to!r}")
    if "claim_kind" not in t:
        errs.append("claim_kind 누락")
    if not t.get("limitation") and not t.get("known_limitation"):
        errs.append("limitation 누락 — 한계 없는 보고는 발행하지 않는다")

    # R26 (T-A-V3-STEP1-026): 측정을 담은 보고에는 측정 시각이 있어야 한다.
    # A 대 D 의 base_sha 수 차이는 방법 차이가 아니라 **시각 차이**였다. 시각 없는
    # 수치는 대조할 수 없고, 대조하면 없는 결함이 만들어진다.
    if not t.get("measured_at_kst"):
        m = [p for p, _ in _walk(t) if any(w in p.lower() for w in _MEASURE_KEYS)]
        if m:
            errs.append(f"measured_at_kst 누락 — R26. 측정 필드: {m[0]}")

    # 인용한 산출물 경로는 발행 시점에 실재해야 한다. base_sha 와 같은 층이다 —
    # 없는 파일을 증거로 적으면 받는 쪽은 그것을 확인할 수 없고, 확인 실패가
    # **상대의 결함**처럼 보인다. 기준 디렉터리를 넓게 잡는다: 경로 표기가
    # 티켓마다 달라서(research_d/… · tools/… · research/…) 좁게 잡으면
    # 실재하는 파일을 없다고 보고한다 — D 가 이 검사를 만들다 실제로 겪었다.
    for path, val in _walk(t):
        if not (isinstance(val, str) and _PATHLIKE.match(val.strip())):
            continue
        rel = val.strip()
        if not any((b / rel).exists() for b in _BASES):
            errs.append(f"인용 경로가 실재하지 않는다: {path} = {rel}")

    # R45 — '독립' 을 단독으로 쓰지 않는다. 세 뜻이 섞여 있었다:
    #   시점독립(읽기 전에 쟀다) · 방법독립(다른 도구·경로) · 주체독립(다른 평면)
    # Δ40 이 '양성대조' 에 내린 판정과 같다 — 한 단어가 두 뜻을 가지면 버린다.
    for path, val in _walk(t):
        if not isinstance(val, str):
            continue
        for m in _BARE_INDEP.finditer(val):
            around = val[max(0, m.start() - 40):m.end() + 40]
            if any(q in around for q in ("시점독립", "방법독립", "주체독립",
                                         "시점 독립", "방법 독립", "주체 독립")):
                continue
            errs.append(f"'독립' 을 한정 없이 썼다 (R45): {path} … {m.group(0)}")
            break

    # 본문 어디의 40자 hex 든 실재 커밋이어야 한다 (B 의 b_ticket_precheck 에서 채택).
    # base_sha 만 보면 본문에 적은 증거 sha 의 조작·오타는 통과한다. B 가 실제로
    # 축약 sha 에 0 을 채운 값을 발행했다(T-B-V3-FINDING-007-SHANOTE).
    # `old_`·`_before` 는 **틀린 값을 증거로 보존한 필드**라 예외다 — 고치면 증거가 사라진다.
    for path, val in _walk(t):
        if not (isinstance(val, str) and _HEX40.fullmatch(val)):
            continue
        leaf = path.rsplit(".", 1)[-1]
        if leaf.startswith("old_") or leaf.endswith("_before") or "superseded" in leaf:
            continue
        if subprocess.run(["git", "cat-file", "-e", f"{val}^{{commit}}"],
                          capture_output=True).returncode != 0:
            errs.append(f"본문 sha 가 실재 커밋이 아니다: {path} = {val}")
    return errs


def _walk(o, p: str = ""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, f"{p}.{k}" if p else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk(v, f"{p}[{i}]")
    else:
        yield p, o


def self_test() -> dict:
    """발행 가드가 아직 무언가를 막고 있는가 — 매 발행마다 확인한다.

    `emit()` 은 `check()` 만 믿는다. `check()` 가 조용히 통과하게 되면
    (정규식 변경 · 예외 삼킴 · 리팩터링) **모든 불량 티켓이 그대로 나가고
    출력은 지금과 똑같다.** 방화벽에서 발견한 것과 같은 형태이고,
    B 가 T-B-V3-FINDING-010 에서 잡은 것과도 같다 —
    **조용한 통과는 실패보다 오래 산다.**

    고정 fixture 두 개를 매번 통과시킨다. 파일을 쓰지 않는다.
    """
    head = _sh("git", "rev-parse", "HEAD")
    good = {"ticket_id": "D-SELFTEST-GOOD", "from": "D", "type": "FINDING",
            "to": ["C"], "claim_kind": "OBSERVATION", "base_sha": head,
            "limitation": "자체 대조군 fixture",
            "artifact_refs": {"tool": "research/landing_accessibility/research_d/"
                                      "tools/d_emit_ticket.py"}}
    bad = {"ticket_id": "D-SELFTEST-BAD", "from": "D", "type": "FINDING",
           "to": ["A"],                       # 라우팅 위반
           "claim_kind": "OBSERVATION",
           "base_sha": "0" * 40,              # 실재하지 않는 커밋
           "measurement": {"n": 1},           # 측정인데 measured_at_kst 없음 (R26)
           "evidence": ["results/__NO_SUCH_FILE__.json"],  # 없는 경로
           "note": "C 가 독립 확인했다"}                      # R45 위반 (한정 없는 '독립')
    # limitation 도 없다 → 최소 5종이 걸려야 한다
    # 원격 도달 불가 fixture — 실재하는 커밋이되 D 브랜치 조상이 아닌 것.
    # `origin/main` 을 쓴다(존재하지만 D 브랜치에 병합되지 않았다).
    off = subprocess.run(["git", "rev-parse", "origin/main"],
                         capture_output=True, text=True).stdout.strip()
    unreachable = dict(good)
    unreachable["ticket_id"] = "D-SELFTEST-UNREACHABLE"
    # **fixture 선정에 검사 대상 함수를 쓰지 않는다.** 처음엔 그렇게 했는데,
    # `_reachable_from_remote` 를 무력화하면 fixture 가 사라지고 그 SKIP 이
    # 통과로 읽혔다 — 검사가 죽어도 대조군이 초록불이다.
    # 독립 명령으로 고른다.
    _is_anc = (off and len(off) == 40 and subprocess.run(
        ["git", "merge-base", "--is-ancestor", off, D_REMOTE],
        capture_output=True).returncode == 0)
    if off and len(off) == 40 and not _is_anc:
        unreachable["base_sha"] = off
    else:
        off = ""                      # 적당한 fixture 가 없다 — 아래에서 FAIL 로 낸다

    g, b = check(good), check(bad)
    u = check(unreachable) if off else None
    expect = {"base_sha 가 실재": any("실재 커밋이 아니다" in e for e in b),
              # fixture 를 못 세우면 **통과가 아니라 실패**다. 검사하지 않은 것을
              # 검사해서 문제없음으로 적지 않는다.
              "원격 도달성": (any("도달 불가" in e for e in u) if u is not None else False),
              "to=[C] 라우팅": any("to=[C]" in e for e in b),
              "limitation 필수": any("limitation" in e for e in b),
              "R26 measured_at": any("measured_at_kst" in e for e in b),
              "인용 경로 실재": any("인용 경로가" in e for e in b),
              "R45 한정 없는 독립": any("R45" in e for e in b)}
    ok = not g and all(v is True for v in expect.values())
    return {"verdict": "PASS" if ok else "FAIL",
            "good_fixture_errors": g,
            "bad_fixture_caught": expect,
            "remote_reachability_fixture": off[:12] if off else None,
            "why": "대조군이 실패하면 발행하지 않는다 — 못 막는 가드의 '오류 0' 은 0 이 아니다"}


def emit(t: dict, *, dry_run: bool = False) -> dict:
    """검사를 통과하면 티켓을 쓰고 event_log 에 append 한다."""
    t = dict(t)
    t.setdefault("from", "D")
    t.setdefault("base_sha", _sh("git", "rev-parse", "HEAD"))
    t.setdefault("created_at_kst", _sh("date", "-Iseconds"))
    t.setdefault("expected_response", "ACK")
    t.setdefault("not_a_verdict", "D 는 NON_CANONICAL. 조치·판정은 A 소관이다.")

    st = self_test()
    if st["verdict"] != "PASS":
        return {"emitted": False,
                "errors": ["발행 가드 자체 대조군 실패 — 티켓을 내보내지 않는다",
                           json.dumps(st, ensure_ascii=False)]}

    errs = check(t)
    if errs:
        return {"emitted": False, "errors": errs}
    if dry_run:
        return {"emitted": False, "errors": [], "dry_run": True}

    p = BUS / "tickets" / f"{t['ticket_id']}.json"
    if p.exists():
        return {"emitted": False,
                "errors": [f"이미 존재한다. 발행분은 덮어쓰지 않는다: {p.name}"]}
    p.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    (BUS / "event_log.jsonl").open("a").write(json.dumps(
        {"ts": t["created_at_kst"], "actor": "D", "event": "EMIT",
         "ticket_id": t["ticket_id"], "to": t.get("to"), "cc": t.get("cc"),
         "ticket_sha256": sha, "base_sha": t["base_sha"]}, ensure_ascii=False) + "\n")
    return {"emitted": True, "path": str(p), "ticket_sha256": sha}


def audit_emitted(v3_since: str = "2026-08-28T02:12") -> dict:
    """D 발행분 전수 — v3 이후 base_sha 해석 여부. 스캐너가 매 회 호출한다."""
    rows = []
    for p in sorted((BUS / "tickets").glob("D-*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:                      # noqa: BLE001
            rows.append({"file": p.name, "state": "UNPARSED", "error": str(e)})
            continue
        if d.get("from") != "D":
            continue
        ts = d.get("created_at_kst") or d.get("created_at") or ""
        bs = d.get("base_sha")
        if bs is None:
            st = "NO_FIELD"
        elif subprocess.run(["git", "cat-file", "-e", f"{bs}^{{commit}}"],
                            capture_output=True).returncode == 0:
            st = "OK"
        else:
            st = "MISSING"
        rows.append({"file": p.name, "created": ts, "state": st,
                     "v3_era": ts >= v3_since})
    bad = [r for r in rows if r.get("v3_era") and r.get("state") not in ("OK", None)]
    return {"n": len(rows), "v3_era": sum(1 for r in rows if r.get("v3_era")),
            "v3_era_non_resolving": bad,
            "verdict": "PASS" if not bad else "FAIL",
            "pre_v3_not_amended": "소급 개정하지 않는다 (STEP1-024)"}


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        print(json.dumps(self_test(), ensure_ascii=False, indent=1))
        raise SystemExit(0)
    print(json.dumps({"self_test": self_test()["verdict"],
                      "emitted_audit": audit_emitted()}, ensure_ascii=False, indent=1))
