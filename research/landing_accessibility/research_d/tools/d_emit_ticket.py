"""D 티켓 발행 단일 경로 — 발행 전에 스키마를 강제한다.

D 는 `D-V3-FINDING-012` 를 `base_sha` 없이 발행했다. v3 Δ26 은 v3 이후 발행분에
해석 가능한 `base_sha` 를 요구한다. 그 누락은 **A 의 전수감사(STEP1-024)에 걸리고
나서야** 보였다 — 발행 시점에 아무것도 막지 않았기 때문이다.

여기서 막는다. 검사에 걸리면 파일을 쓰지 않는다.

  base_sha       실재하는 커밋이어야 한다 (`git cat-file -e <sha>^{commit}`)
  to             D 의 substantive finding 은 `to=[C]` 다 (A6/v3 §4)
  claim_kind     판정어가 아니어야 한다 — D 는 GO/NO-GO/BLOCKER/SUPERSEDE 를 내지 않는다
  heredoc 금지    이 모듈은 dict 를 받는다. 셸 heredoc 은 backtick 을 삼킨다(실제로 겪었다)

[D-DEF-47] 이 docstring 은 "스키마를 강제한다" 고 적혀 있었지만 **스키마 파일을
읽지 않았다.** 손으로 고른 4항목만 봤고 `scope` 와 `status` 는 필수인데 채우지도
검사하지도 않았다 — v3-era D 발행분 68건 중 55건이 위반이다.

**목록을 손으로 만들면 뒤처진다**(D-DEF-45 와 같은 형태). 이제 SSOTV3 의
`15_TICKET_PROTOCOL_SCHEMA_v3.0.json` **정본을 읽어** required 와 enum 을
검사한다. 스키마가 바뀌면 이 도구도 따라간다.
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


def _reachable_from_remote(sha: str):
    """sha 가 D 원격 브랜치에서 도달 가능한가. 원격 ref 를 못 읽으면 True 로 둔다.

    원격을 못 읽는 것은 네트워크·설정 문제이지 티켓의 결함이 아니다.
    거기서 막으면 **막을 이유가 없는 것을 막는다**. 다만 그 경우 검사를
    한 것이 아니므로 self_test 가 그 상태를 드러낸다.
    """
    if subprocess.run(["git", "rev-parse", "--verify", D_REMOTE],
                      capture_output=True).returncode != 0:
        # [A STEP1-037 지시로 시정] 예전에는 여기서 **True** 를 냈다 —
        # '원격을 못 읽었다' 를 '도달 가능하다' 로 읽은 것이다.
        # A·B·C 세 평면 도구에서 같은 오해가 나왔다(검사가 못 돈 것을
        # '안전하게 막혔다'/'문제없다' 로 읽음). D 도 같았다.
        return "UNVERIFIED"
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
    elif (_r := _reachable_from_remote(bs)) == "UNVERIFIED":
        errs.append(f"{D_REMOTE} 를 읽지 못했다 — **검사가 돌지 않았다.** "
                    "통과로 읽지 말고 fetch 후 다시 발행하라")
    elif not _r:
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


SSOT_SCHEMA = Path("/home/sieg/projects-wsl/ProjectFinal"
                   "/SSOTV3/15_TICKET_PROTOCOL_SCHEMA_v3.0.json")


def schema_errors(t: dict) -> list:
    """[D-DEF-47] **정본 스키마 파일을 읽어** required·enum 을 검사한다.

    손 목록이 아니다. 스키마가 바뀌면 이 검사가 따라간다.
    """
    try:
        s = json.loads(SSOT_SCHEMA.read_text(encoding="utf-8"))
    except Exception as e:                 # 읽지 못한 것을 통과로 읽지 않는다
        return [f"스키마 정본을 읽지 못했다 — 발행하지 않는다: {SSOT_SCHEMA} ({e})"]
    out = [f"스키마 필수 누락: {k}" for k in s["required"] if k not in t]
    for k, spec in s["properties"].items():
        if k in t and "enum" in spec and t[k] not in spec["enum"]:
            out.append(f"스키마 enum 밖: {k}={t[k]!r} (허용 {spec['enum']})")
        if k in t and spec.get("type") == "array" and "enum" in spec.get("items", {}):
            for v in (t[k] or []):
                if v not in spec["items"]["enum"]:
                    out.append(f"스키마 enum 밖: {k}[]={v!r}")
    return out


_ASK_A = __import__("re").compile(r"(A_에게|A_결정|A_소관|A_판정)")


def decision_field_errors(t: dict) -> list:
    """[D-DEF-66] **결정을 요청하면서 `decision_required` 를 비워두지 않는다.**

    D 는 `A_결정_요청`·`A_에게` 같은 **필드 이름**으로 A 의 결정을 물어왔다 —
    18건. 전부 `cc=[A]` 라 A 가 수신자이긴 했고 실제로 답을 받은 것도 있다
    (R167). 그러나 스키마에 `decision_required` 가 있는데 비워뒀고, 그래서
    **기계가 읽는 결정 대기 목록에 안 잡힌다.** D 자신의 `d_pending_response`
    도 그 18건을 결정 대기로 세지 않는다.

    B 가 `T-B-V3-DR-003` 에서 더 나쁜 형태를 보고했다 — "A 결정 사항" 이라
    적은 11건이 **D·C 앞 ACK 본문**에 있어 A 에게 간 적이 없었다. D 는 cc 로는
    갔지만 **읽을 수 있는 형태가 아니었다**는 점에서 같은 계열이다.
    """
    if t.get("decision_required"):
        return []
    keys = [k for k in t if _ASK_A.search(str(k))]
    if not keys:
        return []
    return [f"A 의 결정을 묻는 필드({keys})가 있는데 `decision_required` 가 비었다 — "
            f"기계가 읽는 결정 대기에 잡히지 않는다 [D-DEF-66]"]


def retraction_errors(t: dict) -> list:
    """[A R163 / D-DEF-48] 철회된 라벨을 **표시 없이** 인용하고 나가지 않는다.

    `D-V3-FINDING-048` 의 limitation 이 "발행 전에는 못 막는다" 였다. 여기서
    막는다 — 산출물 감사만 있으면 티켓은 그대로 새 나간다(실제로
    `D-V3-FINDING-043` 이 그렇게 나갔다).

    `retracted_labels_cited` 로 선언하면 통과한다. 토큰을 **논의 대상**으로
    삼는 티켓(철회 자체를 다루는 보고)이 실제로 있기 때문이다.
    """
    try:
        import d_retractions as _RET
    except Exception as e:
        return [f"철회 정본 도구를 불러오지 못했다 — 발행하지 않는다: {e}"]
    # [D-DEF-49] 선언 인정은 `d_retractions` 한 곳에만 둔다. 여기서 따로
    # 구현하면 사후 감사와 갈라진다 — 실제로 갈라졌다.
    hits = _RET.audit_json_text(json.dumps(t, ensure_ascii=False), t.get("ticket_id", "?"))
    return [f"철회 라벨을 표시 없이 인용했다: {h['token']} — "
            f"`{_RET.MARK}` 를 달거나 `{_RET.DECLARE_FIELD}` 로 선언하라"
            for h in {h["token"]: h for h in hits}.values()]


# [D-DEF-81] **시각도 측정치다.** `emit()` 은 `created_at_kst` 를 스탬프하지만
# 호출자가 값을 주면 그것이 이긴다 — 그래서 손으로 쓴 시각이 37건 발행됐고
# 최대 88분 앞섰다. B 가 `D-V3-FINDING-075` 를 **선언 발행시각보다 14분 먼저**
# ACK 한 것으로 기록돼 버스에 인과 역전이 남았다. 이제 어긋난 시각은 막는다.
CLOCK_TOLERANCE_SEC = 120
_CLOCK_FIELDS = ("created_at_kst", "measured_at_kst", "ack_at_kst")


def clock_errors(t: dict) -> list:
    """선언한 시각이 실제 시각과 어긋나면 막는다."""
    import datetime as _dt
    now_s = _sh("date", "-Iseconds")
    try:
        now = _dt.datetime.fromisoformat(now_s)
    except Exception:                               # noqa: BLE001
        return []                                   # 시계를 못 읽으면 판정하지 않는다
    out = []
    for f in _CLOCK_FIELDS:
        v = t.get(f)
        if not isinstance(v, str) or not v:
            continue
        try:
            d = _dt.datetime.fromisoformat(v)
        except Exception:                           # noqa: BLE001
            out.append(f"{f} 를 시각으로 읽을 수 없다: {v!r}")
            continue
        if d.tzinfo is None:
            d = d.replace(tzinfo=now.tzinfo)
        off = (d - now).total_seconds()
        if abs(off) > CLOCK_TOLERANCE_SEC:
            out.append(f"{f} 가 실제 시각과 {off:+.0f}초 어긋났다 "
                       f"(선언 {v} / 지금 {now_s}) — **시각을 손으로 쓰지 마라. "
                       f"필드를 빼면 도구가 스탬프한다** [D-DEF-81]")
    return out


def emit(t: dict, *, dry_run: bool = False) -> dict:
    """검사를 통과하면 티켓을 쓰고 event_log 에 append 한다."""
    t = dict(t)
    t.setdefault("from", "D")
    t.setdefault("base_sha", _sh("git", "rev-parse", "HEAD"))
    t.setdefault("created_at_kst", _sh("date", "-Iseconds"))
    t.setdefault("expected_response", "ACK")
    t.setdefault("not_a_verdict", "D 는 NON_CANONICAL. 조치·판정은 A 소관이다.")
    # [R65] 규약 필드를 **도구가 담는다.** C 가 짚은 원인 — 도구가 담지 않으면
    # 사람이 매번 적어야 하고 그러면 빠진다(D 는 54건 중 11건에만 있었다).
    # 이 값은 **발행 시점의 의도 선언**이며 자기신고라 증거로 인용하지 않는다.
    # 검증 가능한 형태는 구조 검사다 — `d_bus_lib.cross_plane_ack_audit`.
    t.setdefault("self_approved", False)
    t.setdefault("self_approved_note",
                 "자기신고다. 증거는 구조 검사(발행 평면 외 ACK ≥ 1)로 따로 낸다 — R65")
    # [D-DEF-47] 스키마 필수인데 아무도 채우지 않던 둘. `scope` 는 내용이라
    # 자동으로 지어내지 않는다 — 없으면 아래 스키마 검사에서 막힌다.
    t.setdefault("status", "OPEN")

    st = self_test()
    if st["verdict"] != "PASS":
        return {"emitted": False,
                "errors": ["발행 가드 자체 대조군 실패 — 티켓을 내보내지 않는다",
                           json.dumps(st, ensure_ascii=False)]}

    errs = check(t)
    errs = list(errs) + schema_errors(t)     # [D-DEF-47] 정본 스키마도 본다
    errs += retraction_errors(t)             # [D-DEF-48] 철회 라벨도 본다
    errs += decision_field_errors(t)         # [D-DEF-66] 결정 요청은 필드로 낸다
    errs += clock_errors(t)                  # [D-DEF-81] 시각도 측정치다
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


def emit_ack(ticket_id: str, body: dict, *, ack_type: str = "ACK",
             dry_run: bool = False) -> dict:
    """ACK 을 **시각 가드를 거쳐** 쓴다.

    [D-DEF-81 한계 해소] ACK 파일은 지금까지 `emit()` 을 안 거쳐 손으로 쓴 시각이
    그대로 들어갔다 — `C-FINDING-143044` ACK 은 실제 기록보다 **+5267초** 앞섰다.
    시각은 여기서 스탬프하고, 호출자가 준 값은 `clock_errors` 로 막는다.
    """
    tp = BUS / "tickets" / f"{ticket_id}.json"
    if not tp.exists():
        return {"acked": False, "errors": [f"티켓 파일이 없다: {tp.name}"]}
    a = dict(body)
    a["ticket_id"] = ticket_id
    a["ack_by"] = "D"
    a.setdefault("ack_type", ack_type)
    a.setdefault("ack_at_kst", _sh("date", "-Iseconds"))     # **도구가 스탬프한다**
    # [D-DEF-13] ACK 은 "그때 그 내용" 에 대한 것이다 — 해시를 박는다
    a["ticket_sha256"] = hashlib.sha256(tp.read_bytes()).hexdigest()
    a.setdefault("not_a_verdict", "D 는 NON_CANONICAL. 판정은 A 소관이다.")
    errs = clock_errors(a)
    if errs:
        return {"acked": False, "errors": errs}
    if dry_run:
        return {"acked": False, "errors": [], "dry_run": True}
    ap = BUS / "acks" / f"{ticket_id}.D.json"
    ap.write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
    (BUS / "event_log.jsonl").open("a").write(json.dumps(
        {"ts": a["ack_at_kst"], "actor": "D", "event": "ACK",
         "ticket_id": ticket_id, "via": "emit_ack",
         "ticket_sha256": a["ticket_sha256"]}, ensure_ascii=False) + "\n")
    return {"acked": True, "path": str(ap), "ticket_sha256": a["ticket_sha256"],
            "ack_at_kst": a["ack_at_kst"]}


def _v3_since() -> str:
    """v3 규약 발효 시각 — **정의는 `d_ticket_schema_check` 한 곳에 있다**.

    [D-DEF-49] 같은 개념이 두 곳에 하드코딩돼 있었다. 지금은 값이 같지만
    한쪽만 고치면 조용히 갈라진다.
    """
    try:
        from d_ticket_schema_check import V3_SINCE
        return V3_SINCE
    except Exception:
        return "2026-08-28T02:12"     # 불러오지 못해도 감사가 멈추지는 않는다


# `emit()` 이 event_log 에 남기기 시작한 경계. 그 이전 발행분은 baseline —
# **영구 FAIL 은 신호를 죽인다**(D-DEF-52). 경계는 손 목록이 아니라 시각이다.
EMIT_LOG_SINCE = "2026-08-28T07:00:00"


def emission_record() -> dict:
    """D 발행 티켓에 event_log 발행기록이 있는가."""
    log = BUS / "event_log.jsonl"
    seen, first_ts = set(), None
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except Exception:                       # noqa: BLE001
                continue
            if first_ts is None:
                first_ts = ev.get("ts")
            if ev.get("actor") == "D" and ev.get("event") in ("EMIT", "TICKET_ISSUED"):
                seen.add(ev.get("ticket_id"))
    # [D-DEF-82] **반대 방향도 잰다.** 지금까지 티켓→로그 한 쪽만 봤다.
    # 로그에 발행 기록이 있는데 **티켓 파일이 없는** 경우가 반대편이다 —
    # `T-B-CLOCKTEST-002`(B, 17:41)가 실제로 그랬다. D 자신의 것은 FAIL 축이고
    # 다른 평면 것은 **관측만 한다**(D 는 남을 판정하지 않는다).
    on_disk = {f.name[:-5] for f in (BUS / "tickets").glob("*.json")}
    logged_ids = {}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except Exception:                       # noqa: BLE001
                continue
            if ev.get("event") in ("EMIT", "TICKET_ISSUED"):
                logged_ids.setdefault(ev.get("actor"), set()).add(ev.get("ticket_id"))
    logged_no_file = {act: sorted(ids - on_disk)
                      for act, ids in logged_ids.items() if ids - on_disk}
    d_logged_no_file = logged_no_file.get("D", [])

    have, miss_new, miss_base, no_ts = 0, [], [], []
    for p in (BUS / "tickets").glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                           # noqa: BLE001
            continue
        if d.get("from") != "D":
            continue
        tid = d.get("ticket_id")
        ts = d.get("created_at_kst") or d.get("created_at") or ""
        if not ts:
            no_ts.append(tid)
        if tid in seen:
            have += 1
        elif ts and ts >= EMIT_LOG_SINCE:
            miss_new.append(tid)
        else:
            miss_base.append(tid)
    return {"verdict": "PASS" if not (miss_new or d_logged_no_file) else "FAIL",
            "n_logged_no_file_D": len(d_logged_no_file),
            "logged_no_file_D": d_logged_no_file,
            "logged_no_file_other_planes": logged_no_file,
            "반대_방향은_왜_보나": ("티켓→로그만 보면 **로그에만 있고 파일이 없는** 건을 못 본다. "
                          "D 자신의 것은 FAIL 축이고, 다른 평면 것은 **관측만 한다** — "
                          "왜 없는지(가드에 막힘·시험 후 삭제·기타)는 D 가 단정하지 않는다"),
            "n_with_record": have,
            "n_missing_new": len(miss_new), "missing_new": sorted(miss_new),
            "n_missing_baseline": len(miss_base),
            "n_no_created_at": len(no_ts),
            "log_first_ts": first_ts,
            "**로그_부재가_아니다**": ("event_log 는 티켓보다 이르게 시작한다 — "
                                "`log_first_ts` 를 티켓 최초 시각과 대조해 확인한다"),
            "baseline_경계": EMIT_LOG_SINCE,
            "이_수가_말하지_않는_것": ("기록이 없다는 것은 **`actor:D` 의 EMIT/TICKET_ISSUED 줄이 "
                             "없다**는 뜻이다. 그것이 곧 '우회 발행' 인지는 D 가 단정하지 않는다")}


def audit_emitted(v3_since: str | None = None) -> dict:
    v3_since = _v3_since() if v3_since is None else v3_since
    """D 발행분 전수 — v3 이후 base_sha 해석 여부. 스캐너가 매 회 호출한다."""
    rows = []

    # [D-DEF-80] **명명 규약을 저자 판정의 대리로 쓰지 않는다** (T-B-V3-FINDING-021).
    # 접두사는 `check()` 가 발행 시점에 강제하지만 그 보장은 **이 도구를 거친 발행에만**
    # 있다. 모집단은 `from` 으로 잡는다 — 현재 두 방식의 차는 0 이고, 그것도 측정치다.
    for p in sorted((BUS / "tickets").glob("*.json")):
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
    rec = emission_record()
    return {"n": len(rows), "v3_era": sum(1 for r in rows if r.get("v3_era")),
            "emission_record": rec,
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


def controls() -> dict:
    """[D-DEF-55] `self_test()` 를 표준 형태로 정규화한 래퍼. 원 함수는 그대로다."""
    st = self_test()
    cases = []
    for name, caught in (st.get("bad_fixture_caught") or {}).items():
        cases.append({"case": f"불량 fixture 를 막는다: {name}",
                      "expectation": "must_flag", "ok": bool(caught)})
    # [D-DEF-81] 손으로 쓴 시각을 막는가 — **`emit()` 의 errs 사슬에 들어간 검사다**
    import datetime as _dt
    _now = _dt.datetime.fromisoformat(_sh("date", "-Iseconds"))

    def _clk(name, delta, should_fail=True):
        v = (_now + _dt.timedelta(seconds=delta)).isoformat(timespec="seconds")
        flagged = bool(clock_errors({"created_at_kst": v}))
        cases.append({"case": f"[시각] {name}",
                      "expectation": "must_flag" if should_fail else "must_not_flag",
                      "ok": flagged == should_fail})

    _clk("15분 앞선 시각은 막힌다", 900)
    _clk("15분 뒤진 시각도 막힌다", -900)
    _clk("지금 시각은 통과한다", 0, should_fail=False)
    _clk("허용오차 안(60초)은 통과한다", 60, should_fail=False)
    # [D-DEF-81] ACK 경로도 같은 가드를 거치는가
    _ah = (_now + _dt.timedelta(seconds=900)).isoformat(timespec="seconds")
    _r = emit_ack("D-V3-FINDING-076", {"ack_at_kst": _ah}, dry_run=True)
    cases.append({"case": "[시각] ACK 도 손으로 쓴 시각이면 막힌다",
                  "expectation": "must_flag",
                  "ok": bool(_r.get("errors")) and not _r.get("acked")})
    # [D-DEF-82] 반대 방향 축이 살아 있는가
    _er = emission_record()
    cases.append({"case": "[발행기록] D 의 로그-only 건은 0",
                  "expectation": "must_not_flag", "ok": _er["n_logged_no_file_D"] == 0})
    cases.append({"case": "[발행기록] 반대 방향 키가 존재한다 — 죽은 축이 아니다",
                  "expectation": "must_not_flag",
                  "ok": "logged_no_file_other_planes" in _er})
    _r2 = emit_ack("__NO_SUCH_TICKET__", {}, dry_run=True)
    cases.append({"case": "[ACK] 없는 티켓에는 ACK 하지 않는다",
                  "expectation": "must_flag",
                  "ok": bool(_r2.get("errors")) and not _r2.get("acked")})
    cases.append({"case": "[시각] 필드가 없으면 판정하지 않는다",
                  "expectation": "must_not_flag", "ok": not clock_errors({})})

    good = st.get("good_fixture_errors") or []
    cases.append({"case": "정상 fixture 는 통과한다",
                  "expectation": "must_not_flag", "ok": not good,
                  "detail": good[:3]})
    _all_ok = all(c["ok"] for c in cases) and st.get("verdict") == "PASS"
    return {"verdict": "PASS" if _all_ok else "FAIL", "n": len(cases),
            "failed": [c["case"] for c in cases if not c["ok"]],
            "must_flag": sum(1 for c in cases if c["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for c in cases if c["expectation"] == "must_not_flag"),
            "cases": cases}
