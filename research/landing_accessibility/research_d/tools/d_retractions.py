"""철회된 라벨을 **정본에서 읽는다**.

[A R163 / T-A-V3-K8-003] B 의 관측: "내 검사들은 CSV 의 값을 보지 그 값이
사람에게 어떻게 읽히는지를 안 본다. `NO_SAFE_ROUTE_SITE` 가 CSV 에 남아 있어도
검사는 통과하고 읽는 사람만 오해한다. 그래서 `RETRACTIONS.md` 를 CSV 옆에
뒀는데 **그것도 검사가 아니라 문서다**."

**D 도 같은 형태를 냈다.** `d_coverage.py` 는 `NO_SAFE_ROUTE_SITE` 를 관측값
whitelist 에 넣으면서 "SITE 라벨은 R132/R137 로 철회됐다" 를 **주석에만** 적었다.
그리고 `d_v3_report.GROUPS` 는 그 토큰을 **"SITE-SIDE ROUTE NOT OBSERVED"**
라는 그룹명으로 묶었다 — RETRACTIONS.md 가 금지한 바로 그 형태다:
"이 토큰을 사이트에 대한 진술로 쓰면 안 된다."

주석은 검사가 아니다. 그래서 여기서 **정본을 읽는다.**

파싱 규칙은 보수적이다 — `— **철회됨**` 이 붙은 절만 철회로 본다.
같은 문서에 `**철회 아님. 유지**` 절(`COLLECTOR_ZERO_CANDIDATE`)이 있고
**그것을 철회로 잡으면 반대 방향의 오류**가 된다.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
RETRACTIONS = REPO / "artifacts/v3_census/mart/CANONICAL_MART_50.RETRACTIONS.md"

# `## \`TOKEN\` (16행) — **철회됨**`  /  `## \`TOKEN\` (21행) — **철회 아님. 유지**`
_SEC = re.compile(r"^##\s+`([A-Z0-9_]+)`.*?—\s*\*\*(.+?)\*\*", re.M)
_RETRACTED = "철회됨"

MARK = "RETRACTED"
# JSON 산출물에서 토큰이 **키**로 쓰이면 표시를 키에 붙일 수 없다 — 붙이면
# 그 파일을 읽는 도구가 키를 못 찾는다. 대신 파일이 이 필드로 **인용 사실을
# 명시**하면 인정한다. 값을 오염시키지 않으면서 읽는 사람에게 보이게 하는 자리다.
DECLARE_FIELD = "retracted_labels_cited"


def parse(text: str | None = None) -> dict:
    t = RETRACTIONS.read_text(encoding="utf-8") if text is None else text
    out = {}
    for m in _SEC.finditer(t):
        token, verdict = m.group(1), m.group(2).strip()
        out[token] = {"retracted": verdict.startswith(_RETRACTED),
                      "verdict_text": verdict}
    # 대체 라벨과 정확한 진술은 인용하는 쪽이 함께 실어야 한다.
    # **절 경계로 자른다** — 처음엔 첫 등장 이후 전체를 봤고, 그러면
    # `COLLECTOR_ZERO_CANDIDATE`(철회 아님)가 앞 절의 대체 라벨을 주워왔다.
    # 철회 아닌 토큰에 대체 라벨이 붙는 것은 **없는 사실을 만드는 것**이다.
    spans = [(m.group(1), m.start()) for m in _SEC.finditer(t)]
    for i, (token, start) in enumerate(spans):
        end = spans[i + 1][1] if i + 1 < len(spans) else len(t)
        seg = t[start:end]
        alt = re.search(r"\*\*대체 라벨\*\*:\s*`([A-Z0-9_]+)`", seg)
        say = re.search(r"\*\*정확한 진술\*\*:\s*(.+)", seg)
        out[token]["replacement"] = alt.group(1) if alt else None
        out[token]["accurate_statement"] = say.group(1).strip() if say else None
        out[token]["tickets"] = sorted(set(_TICKET_REF.findall(seg)))
    return out


def retracted_tokens() -> set:
    return {k for k, v in parse().items() if v["retracted"]}


def cite(token: str) -> str:
    """철회된 토큰은 **표시를 달아서만** 문자열로 나간다."""
    return f"{token} [{MARK}]" if token in retracted_tokens() else token


def audit_text(text: str, source: str = "") -> list:
    """어떤 산출물 텍스트가 철회 토큰을 **표시 없이** 인용하는가."""
    bad = []
    for tok in sorted(retracted_tokens()):
        for m in re.finditer(re.escape(tok), text):
            tail = text[m.end():m.end() + 40]
            head = text[max(0, m.start() - 40):m.start()]
            if MARK in tail or MARK in head:
                continue
            bad.append({"source": source, "token": tok,
                        "context": text[max(0, m.start() - 45):m.end() + 45]
                        .replace("\n", " ")})
    return bad


ANALYSIS = REPO / "artifacts/v3_census/analysis"
BUS_TICKETS = REPO / ".agent_bus/landing_v2/tickets"
_TICKET_REF = re.compile(r"`(T-[A-Z0-9\-]+)`")


def retracted_since(token: str) -> str | None:
    """그 라벨이 **언제부터** 철회인가.

    **철회 이전 인용은 위반이 아니다.** 시점을 보지 않으면 6건이 다 위반으로
    세어진다 — 실제로는 5건이 철회 전(11:29~11:55)이고 철회는 12:39 다.
    소급해서 세는 것은 이 연구가 반복해 잡아온 과대 계상 그대로다.

    성립 시각은 **근거 티켓 중 가장 이른 것**이다. 근거가 나중에 교체돼도
    (`R143`) 철회가 성립한 시점은 처음이다.
    """
    meta = parse().get(token)
    if not meta or not meta.get("retracted"):
        return None
    times = []
    for tid in meta.get("tickets", []):
        f = BUS_TICKETS / f"{tid}.json"
        if not f.exists():
            continue
        try:
            import json as _j
            d = _j.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        ts = str(d.get("created_at_kst") or d.get("created_at")
                 or d.get("created_at_measured") or "")
        if ts:
            times.append(ts[:19])
    return min(times) if times else None


def declared_in(obj) -> set:
    """그 JSON 이 `retracted_labels_cited` 로 **선언한** 토큰 집합.

    dict 든 list 든 받는다. 선언은 "이 문서는 이 토큰이 철회된 것을 알고
    인용한다" 는 뜻이고, 철회 자체를 다루는 보고에는 필요하다.
    """
    v = (obj or {}).get(DECLARE_FIELD) if isinstance(obj, dict) else None
    if isinstance(v, dict):
        return set(v.keys())
    if isinstance(v, (list, tuple, set)):
        return set(v)
    return set()


def audit_json_text(txt: str, source: str) -> list:
    """JSON 문서 하나를 감사한다 — **선언 인정은 여기 한 곳에만 있다**.

    [D-DEF-49] 처음엔 선언 인정을 `audit_artifacts` 안에만 넣고
    `audit_tickets` 에는 안 넣었다. 그래서 **발행 도구는 통과시킨 티켓을 사후
    감사가 위반으로 잡았다**(`D-V3-FINDING-049`). 같은 규칙을 두 곳에 손으로
    구현하면 갈라진다 — D-DEF-45·47 과 같은 뿌리다.
    """
    import json as _j
    try:
        declared = declared_in(_j.loads(txt))
    except Exception:
        declared = set()
    return [h for h in audit_text(txt, source) if h["token"] not in declared]


def audit_artifacts(root=None) -> dict:
    """**산출물**이 철회 토큰을 표시 없이 인용하는가.

    도구 소스는 대상이 아니다 — 거기서는 상수를 정의하고 이 모듈이 표시를
    붙인다. 사람이 읽는 것은 산출물이고, B 가 말한 "읽는 사람만 오해한다" 의
    그 자리다.
    """
    root = ANALYSIS if root is None else Path(root)
    bad = []
    for p in sorted(list(root.rglob("*.csv")) + list(root.rglob("*.md"))
                    + list(root.rglob("*.json"))):
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if p.suffix == ".json":
            bad += audit_json_text(txt, str(p.relative_to(root)))
            continue
        bad += audit_text(txt, str(p.relative_to(root)))
    return {"verdict": "PASS" if not bad else "FAIL", "n": len(bad),
            "files": sorted({b["source"] for b in bad}), "hits": bad[:20],
            "대상": "산출물만 — 도구 소스는 정의하는 곳이고 표시는 cite() 가 붙인다"}


def _ticket_time(p, d) -> tuple:
    """티켓의 발행 시각. **`created_at_kst` 는 자기신고다.**

    [D-DEF-52] D 가 손으로 만든 티켓 6건에서 자기신고 시각이 실제(파일 mtime)
    보다 **앞서** 있었다 — 최대 54분. 시점 경계 판정이 그 값에 의존하고 있었다.

    처음엔 **늦은 쪽**(`max`)을 썼다. 위반 판정에서는 안전했지만 **baseline 분류에서
    과대 계상**을 냈다 — 자기신고가 실제보다 늦게 적힌 3건이 "차단 이후 발행" 으로
    분류돼 새 위반 3건이라는 잘못된 경보가 됐다. **한 규칙을 두 용도에 쓰면서
    한쪽만 보았다.**

    그래서 **파일이 실제로 쓰인 시각(mtime)을 실제 발행 시각으로 쓴다.** 자기신고는
    함께 반환해 불일치를 드러낸다. 도구(`d_emit_ticket`)로 발행하면 두 값이 일치한다.
    """
    import datetime as _dt
    claimed = str(d.get("created_at_kst") or d.get("created_at") or "")[:19]
    try:
        mtime = _dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        mtime = ""
    used = mtime or claimed          # **실제로 쓰인 시각**이 정본이다
    return used, claimed, mtime


def ticket_time(path):
    """다른 검사도 같은 판정을 쓴다 — 규칙은 한 곳에만 둔다(D-DEF-49·51)."""
    import json as _j
    p = Path(path)
    try:
        d = _j.loads(p.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    return _ticket_time(p, d)


BUS_ACKS = REPO / ".agent_bus/landing_v2/acks"
# [D-DEF-100] ACK 파일은 **어느 검사도 보지 않았다.** 티켓만 봤다.
ACK_GUARD_SINCE = "2026-08-28T20:45:00"      # `emit_ack` 이 철회 검사를 거치기 시작한 시각


def audit_acks(plane: str = "D") -> dict:
    """D 가 쓴 ACK 파일의 철회 라벨 인용. **티켓과 같은 판정 경로**를 쓴다."""
    import datetime as _dt
    rows = []
    for p in sorted(BUS_ACKS.glob(f"*.{plane}.json")):
        txt = p.read_text(encoding="utf-8")
        for h in audit_json_text(txt, p.name):
            tok = h.get("token") if isinstance(h, dict) else str(h)
            since = retracted_since(tok)
            m = _dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")
            if since and m < since:
                cls = "BEFORE_RETRACTION"      # 철회 전에 쓴 것 — **위반이 아니다**
            elif m < ACK_GUARD_SINCE:
                cls = "BASELINE_PRE_GUARD"     # 철회 후·가드 전 — 고칠 수 없다
            else:
                cls = "NEW"
            rows.append({"file": p.name, "token": tok, "mtime": m,
                         "retracted_since": since, "class": cls})
    new = [r for r in rows if r["class"] == "NEW"]
    return {"verdict": "PASS" if not new else "FAIL",
            "n": len(rows), "n_new": len(new),
            "n_before_retraction": sum(1 for r in rows if r["class"] == "BEFORE_RETRACTION"),
            "n_baseline": sum(1 for r in rows if r["class"] == "BASELINE_PRE_GUARD"),
            "rows_ack": rows[:10], "guard_since": ACK_GUARD_SINCE,
            "**총수는 신호가 아니다**": (
                "`BEFORE_RETRACTION` 은 **철회 전에 쓴 것이라 위반이 아니고**, "
                "`BASELINE_PRE_GUARD` 는 `emit_ack` 이 검사를 거치기 전 것이라 **고칠 수 없다**. "
                "**`NEW` 만 신호다**"),
            "왜_이제_보나": "ACK 파일은 티켓 감사에도 스키마 감사에도 대상이 아니었다 [D-DEF-100]"}


def audit_tickets(plane: str = "D") -> dict:
    """**발행 티켓**이 철회 토큰을 표시 없이 인용하는가 — 철회 이후 발행분만.

    발행분은 불변이라 고치지 않는다. 사실만 보고한다.
    """
    import json as _j
    since = {t: retracted_since(t) for t in retracted_tokens()}
    bad, skipped, clock_drift = [], [], []
    for p in sorted(BUS_TICKETS.glob("*.json")):
        try:
            txt = p.read_text(encoding="utf-8")
            d = _j.loads(txt)
        except Exception:
            continue
        if d.get("from") != plane:
            continue
        ts, claimed, mtime = _ticket_time(p, d)
        if claimed and mtime and claimed[:16] != mtime[:16]:
            clock_drift.append({"ticket": p.name, "claimed": claimed, "mtime": mtime})
        for h in audit_json_text(txt, p.name):     # **선언 인정은 단일 경로**
            s0 = since.get(h["token"])
            if s0 and ts and ts < s0:
                skipped.append({**h, "created_at_kst": ts, "retracted_since": s0})
            else:
                bad.append({**h, "created_at_kst": ts, "retracted_since": s0,
                            "class": ("NEW" if ts >= RETRACTION_GUARD_SINCE
                                      else "BASELINE_PRE_GUARD")})
    new = [b for b in bad if b["class"] == "NEW"]
    return {"verdict": "PASS" if not new else "FAIL",
            "n_new": len(new), "n": len(bad),
            "new": new,
            "baseline_pre_guard": {
                "n": len(bad) - len(new),
                "tickets": sorted({b["source"] for b in bad if b["class"] != "NEW"}),
                "왜_PASS_인가": ("차단(`retraction_errors`, `d8e689c` 14:26:06) **이전** 발행분이라 "
                            "**고칠 수 없다**(불변). 영구 FAIL 로 두면 새 위반이 묻힌다 — "
                            "세되 verdict 를 좌우하지 않는다")},
            "guard_since": RETRACTION_GUARD_SINCE,
            "tickets": sorted({b["source"] for b in bad}), "hits": bad,
            "철회_이전_인용": {"n": len(skipped),
                          "tickets": sorted({s["source"] for s in skipped}),
                          "왜_세지_않나": "**철회 이전 인용은 위반이 아니다.** 소급해서 세면 과대 계상이다"},
            "발행분은_고치지_않는다": "불변이다 — 사실만 보고한다",
            "자기신고_시각_불일치": {
                "n": len(clock_drift), "rows": clock_drift[:10],
                "무엇": ("`created_at_kst` 는 **자기신고**다. 손으로 만든 티켓에서 실제"
                       "(파일 mtime)보다 앞선 값이 들어갔다 — 최대 54분"),
                "어떻게_처리하나": ("시점 판정에 **늦은 쪽**을 쓴다. 위반을 놓치는 쪽이 아니라 "
                             "과하게 세는 쪽으로 틀린다. 도구로 발행하면 두 값이 일치한다")}}


# ── 폐기된 **산출물** 인용 ────────────────────────────────────────────────
# [D-DEF-51] 철회된 **라벨**과 같은 형태가 그림에도 있다. `T-A-V3-TBX-022` 로
# 보고서 그림이 6장→4장으로 줄면서 옛 6장은 `_superseded_do_not_cite/` 로
# 옮겨졌고 디렉터리 이름이 "인용하지 마라" 라고 말한다. 그런데 D 의
# `CLAIM_CANDIDATES.json` 은 **경로 없이 파일명만** 적어 폐기본을 가리킨다.
#
# C 는 같은 파일들을 인용하되 **`_superseded_do_not_cite/` 경로를 명시**한다 —
# 그것이 옳은 형태다. 경로가 지위를 말한다.
SUPERSEDED_DIR = REPO / "artifacts/v3_census/analysis/figures/_superseded_do_not_cite"
_SUPERSEDED_MARK = "_superseded_do_not_cite"
# 철회 라벨의 `retracted_labels_cited` 와 같은 자리. **선언 필드 자신이 이름을
# 담기 때문에** 인정하지 않으면 선언한 문서가 걸린다 — D-DEF-49 에서 같은 형태를
# 이미 겪고도 폐기 쪽에 반복했다.
SUPERSEDED_DECLARE = "superseded_figures_cited"

# [D-DEF-52] **영구 FAIL 은 신호를 죽인다.** 발행분은 불변이라 고칠 수 없고,
# 그 위반이 매 스캔 그대로 뜨면 **새 위반이 하나 더해져도 차이를 놓친다**.
#
# 기준은 손 목록이 아니라 **차단이 도입된 시각**이다 — `d_emit_ticket.
# retraction_errors()` 가 들어간 커밋 `d8e689c` (2026-08-28T14:26:06).
# 그 뒤에 발행하고도 위반이면 **차단을 우회한 것**이고 그것이 진짜 새 위반이다.
# 이 값을 뒤로 미루면 baseline 이 커지는데, 코드 변경이라 커밋에 남는다.
RETRACTION_GUARD_SINCE = "2026-08-28T14:26:06"


def superseded_files() -> set:
    if not SUPERSEDED_DIR.is_dir():
        return set()
    return {p.name for p in SUPERSEDED_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in (".png", ".svg", ".csv", ".md")}


def audit_superseded(root=None) -> dict:
    """산출물이 폐기본 파일명을 **경로 없이** 인용하는가.

    경로(`_superseded_do_not_cite/`)를 붙이면 통과한다 — 지위가 드러나기 때문이다.
    """
    root = ANALYSIS if root is None else Path(root)
    names = superseded_files()
    bad = []
    for p in sorted(list(root.rglob("*.json")) + list(root.rglob("*.md"))
                    + list(root.rglob("*.csv"))):
        if _SUPERSEDED_MARK in str(p):
            continue                       # 폐기 디렉터리 자신은 대상이 아니다
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            continue
        declared = set()
        if p.suffix == ".json":
            try:
                import json as _j
                v = _j.loads(txt).get(SUPERSEDED_DECLARE)
                declared = set(v.keys()) if isinstance(v, dict) else set(v or [])
            except Exception:
                declared = set()
        for n in names:
            if n in declared:
                continue                   # 선언한 문서 — 통과
            for m in re.finditer(re.escape(n), txt):
                head = txt[max(0, m.start() - 60):m.start()]
                if _SUPERSEDED_MARK in head:
                    continue               # 경로를 밝힌 인용 — 통과
                bad.append({"source": str(p.relative_to(root)), "file": n,
                            "context": txt[max(0, m.start() - 60):m.end() + 40]
                            .replace("\n", " ")})
    return {"verdict": "PASS" if not bad else "FAIL", "n": len(bad),
            "files": sorted({b["source"] for b in bad}), "hits": bad[:12],
            "n_superseded": len(names),
            "규칙": "경로 `_superseded_do_not_cite/` 를 밝히면 통과한다 — 경로가 지위를 말한다"}


def controls() -> dict:
    """파싱과 감사가 **양방향으로** 맞는지 본다."""
    rows = []

    def case(name, got, want):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want})

    p = parse()
    case("NO_SAFE_ROUTE_SITE 는 철회됨", p.get("NO_SAFE_ROUTE_SITE", {}).get("retracted"), True)
    # **반대 방향** — 같은 문서의 '철회 아님' 절을 철회로 잡으면 안 된다
    case("COLLECTOR_ZERO_CANDIDATE 는 철회 아님",
         p.get("COLLECTOR_ZERO_CANDIDATE", {}).get("retracted"), False)
    case("대체 라벨을 읽는다",
         p.get("NO_SAFE_ROUTE_SITE", {}).get("replacement"), "ROUTE_NOT_REACHED_BY_COLLECTOR")
    # **반대 방향** — 철회 아닌 토큰에 대체 라벨이 붙으면 없는 사실을 만든 것이다.
    # 처음 판에서 실제로 그랬다(절 경계 없이 첫 등장 이후 전체를 봤다)
    case("철회 아닌 토큰에는 대체 라벨이 없다",
         p.get("COLLECTOR_ZERO_CANDIDATE", {}).get("replacement"), None)
    case("표시 없는 인용은 걸린다",
         len(audit_text("terminal_reason=NO_SAFE_ROUTE_SITE 16/50")), 1)
    case("표시 있는 인용은 안 걸린다",
         len(audit_text("NO_SAFE_ROUTE_SITE [RETRACTED] 16/50")), 0)
    case("철회 아닌 토큰은 안 걸린다",
         len(audit_text("COLLECTOR_ZERO_CANDIDATE 21/50")), 0)
    case("cite() 가 표시를 붙인다", cite("NO_SAFE_ROUTE_SITE"),
         "NO_SAFE_ROUTE_SITE [RETRACTED]")
    case("cite() 가 아무 데나 붙이지 않는다", cite("COLLECTOR_ZERO_CANDIDATE"),
         "COLLECTOR_ZERO_CANDIDATE")
    # 정본을 읽지 못하면 통과가 아니어야 한다 — 빈 문서에서 철회 집합이 비면 감사가 무력해진다
    case("빈 정본이면 철회 집합이 비고, 그 사실이 보인다", len(parse("")), 0)
    # 산출물 감사가 실제로 무언가를 세는지 — 합성 디렉터리로 양방향 확인
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "a.csv").write_text("x,NO_SAFE_ROUTE_SITE,16\n", encoding="utf-8")
        case("산출물 감사가 표시 없는 인용을 잡는다",
             audit_artifacts(d)["verdict"], "FAIL")
        (d / "a.csv").write_text("x,NO_SAFE_ROUTE_SITE [RETRACTED],16\n", encoding="utf-8")
        case("표시가 있으면 통과", audit_artifacts(d)["verdict"], "PASS")
        # JSON 은 키를 오염시키지 않고 선언 필드로 인정한다 — 양방향
        (d / "b.json").write_text('{"dist": {"NO_SAFE_ROUTE_SITE": 16}}', encoding="utf-8")
        case("JSON 이 선언 없이 인용하면 막힘", audit_artifacts(d)["verdict"], "FAIL")
        (d / "b.json").write_text(
            '{"dist": {"NO_SAFE_ROUTE_SITE": 16},'
            ' "retracted_labels_cited": {"NO_SAFE_ROUTE_SITE": "SITE 라벨 철회 — R137"}}',
            encoding="utf-8")
        case("JSON 이 선언하면 통과", audit_artifacts(d)["verdict"], "PASS")
    # 철회 시각을 정본의 근거 티켓에서 읽는다 — 없으면 시점 판정이 불가능하다
    # [D-DEF-49] 발행 도구와 사후 감사가 **같은 규칙을 쓰는가**
    _decl = ('{"headline":"NO_SAFE_ROUTE_SITE 16",'
             ' "retracted_labels_cited":{"NO_SAFE_ROUTE_SITE":"철회 인지"}}')
    case("선언한 JSON 은 통과 — 발행 도구와 같은 규칙",
         len(audit_json_text(_decl, "synth")), 0)
    case("선언 없는 JSON 은 걸린다",
         len(audit_json_text('{"headline":"NO_SAFE_ROUTE_SITE 16"}', "synth")), 1)
    case("다른 토큰을 선언해도 이 토큰은 걸린다",
         len(audit_json_text('{"headline":"NO_SAFE_ROUTE_SITE 16",'
                             ' "retracted_labels_cited":{"OTHER":"x"}}', "synth")), 1)
    # [D-DEF-51] 폐기 산출물 인용 — 양방향
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _td:
        _d = Path(_td)
        _n = sorted(superseded_files())
        if _n:
            (_d / "a.json").write_text('{"figure": "%s"}' % _n[0], encoding="utf-8")
            case("경로 없이 폐기본을 인용하면 걸린다",
                 audit_superseded(_d)["verdict"], "FAIL")
            (_d / "a.json").write_text(
                '{"figure": "figures/_superseded_do_not_cite/%s"}' % _n[0], encoding="utf-8")
            case("경로를 밝히면 통과 — C 방식", audit_superseded(_d)["verdict"], "PASS")
            (_d / "a.json").write_text('{"figure": "report_fig1_acquisition_state.png"}',
                                       encoding="utf-8")
            case("현행 그림은 안 걸린다", audit_superseded(_d)["verdict"], "PASS")
            # [D-DEF-49 반복] **선언 필드 자신이 이름을 담는다** — 인정하지 않으면
            # 선언한 문서가 걸린다. 철회 쪽에서 겪고도 폐기 쪽에 반복했다
            (_d / "a.json").write_text(
                '{"figure": "%s", "%s": {"%s": "경로를 밝혀 인용한다"}}'
                % (_n[0], SUPERSEDED_DECLARE, _n[0]), encoding="utf-8")
            case("선언하면 통과 — 선언 필드가 자기 이름에 걸리지 않는다",
                 audit_superseded(_d)["verdict"], "PASS")
    case("철회 시각을 근거 티켓에서 읽는다",
         bool(retracted_since("NO_SAFE_ROUTE_SITE")), True)
    case("철회 아닌 토큰엔 시각이 없다",
         retracted_since("COLLECTOR_ZERO_CANDIDATE"), None)

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps({"parsed": parse(), "retracted": sorted(retracted_tokens()),
                      "controls": controls()}, ensure_ascii=False, indent=1))
    sys.exit(0 if controls()["verdict"] == "PASS" else 1)
