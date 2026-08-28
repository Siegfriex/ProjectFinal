"""D 입력 방화벽 — holdout_accessed=false 를 self-tag 가 아니라 스캔으로 검증한다.

A 의 P0 holdout contamination(T-A-HOLDOUT-SCOPE-001) 이후 D 가 스스로 좁힌 경계다.
D 가 소유한 모든 코드·노트북·결과 파일에서 경로 문자열을 뽑아 allowlist/denylist 로
분류하고, denied 가 하나라도 있으면 FAIL 을 낸다.

self-report 가 아니다. 파일 내용에서 실제 참조를 찾는다.

usage: d_input_firewall.py [--json]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from pathlib import Path

RD = Path(__file__).resolve().parents[1]
NB_DIR = RD.parent / "notebooks" / "d_research"
REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
MANIFEST = RD / "D_INPUT_ALLOWLIST.json"
KST = timezone(timedelta(hours=9))

# 파일 안에서 경로처럼 보이는 문자열
PATH_RE = re.compile(r"[A-Za-z0-9_./\-*{}]*(?:/[A-Za-z0-9_.\-*{}]+)+")
# denylist 는 파일명 토큰으로도 검사한다 (경로 없이 이름만 등장하는 경우)
NAME_TOKENS = ("HOLDOUT_FOR_C", "HOLDOUT_CUSTODY", "LABELS_FROZEN", "LABEL_SPLIT_FROZEN",
               "RAW_L1", "RAW_L2", "RAW_L3", "RAW_L4", "PACKET_L", "PRECEDENCE_CONTESTED",
               "CALIBRATION_FOR_B", "_OVERLAP")
# D 자신의 제약 선언·방화벽 정의는 '참조' 가 아니다. 이 파일들은 토큰 검사에서 제외한다.
SELF_DECLARATION_FILES = {"D_INPUT_ALLOWLIST.json", "d_input_firewall.py"}
# 스캔 결과 파일은 자기가 찾은 위반의 문맥을 그대로 담는다. 그것을 다시 스캔하면
# 자기참조로 WARN 이 누적된다. 파일명 접두로 제외한다 (내용은 D 자신의 스캔 기록이다).
SELF_DECLARATION_PREFIXES = ("D_INPUT_FIREWALL_VERIFICATION",)

# 금지 경로를 **감시 대상으로 나열하는 줄**은 접근이 아니라 선언이다.
# 파일 전체를 예외로 두면(SELF_DECLARATION_FILES) 그 파일의 실제 접근까지
# 놓친다. **줄 단위 표식**으로 좁힌다 — 표식은 코드에 보이고 opt-in 이며,
# 표식 없는 같은 경로는 그대로 FAIL 이다.
GUARD_MARKER = "FIREWALL_GUARD_DEFINITION"

SCAN_SUFFIX = (".py", ".ipynb", ".md", ".json", ".csv", ".sh", ".txt", ".jsonl")


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=RD, capture_output=True, text=True).stdout.strip()


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def denied_hit(text_path: str, patterns: list[dict]) -> str | None:
    for d in patterns:
        pat = d["pattern"]
        if fnmatch(text_path, pat) or fnmatch(f"**/{text_path}", pat):
            return pat
        core = pat.strip("*/")
        if core and core in text_path:
            return pat
        # 부분 경로도 잡는다: 'control/label/**' 은 문서에 'control/label/' 로만 등장할 수 있다.
        segs = [x for x in core.split("/") if x and "*" not in x]
        if len(segs) >= 2 and "/".join(segs[-2:]) in text_path:
            return pat
    return None


# "열지 않았다" 류의 경계선 선언은 참조가 아니다. 단 파일 접근 호출 옆에 있으면 선언이 아니다.
NEGATION_MARKERS = ("열지 않", "미열람", "미접근", "않았다", "않는다", "금지", "not open",
                    "did not read", "차단", "제외", "접근하지 않", "no access", "forbidden",
                    "미생산", "미접속", "denied", "경계",
                    # 기계가독 선언 키 — worker 가 JSON/노트북에 구조화해 남기는 형태.
                    # 한국어 부정어가 없어 1차 규칙이 전부 FAIL 로 잡았다 (D-DEF-05).
                    "not_opened", "not_accessed", "never_accessed", "not_read",
                    "denied_paths", "forbidden_paths", "firewall", "holdout_accessed",
                    "labels_produced", "real_target")
# 실제 파일 접근을 시사하는 토큰. 같은 줄에 있으면 선언으로 보지 않는다.
ACCESS_MARKERS = ("open(", "read_text", "read_bytes", "json.load", "loads(", "Path(",
                  "glob(", "rglob(", "iterdir", "DictReader", "np.load", "pd.read",
                  "cat ", "head ", "tail ", "grep ")
NEG_WINDOW = 2   # 앞뒤 2줄까지 본다 (산문은 줄바꿈으로 끊긴다)
# JSON/노트북은 선언 블록이 한 항목당 한 줄로 펼쳐진다. 같은 블록 안을 보려면 창이 더 넓어야 한다.
NEG_WINDOW_STRUCTURED = 10
STRUCTURED_SUFFIX = (".json", ".ipynb", ".jsonl")
# 리터럴 목록의 원소 줄 — 따옴표로 감싼 토큰과 쉼표뿐인 줄. 그 줄 자체에는 코드가 없으므로
# 관련 문맥은 목록을 감싼 선언부에 있다. 파일 확장자와 무관하게 창을 넓힌다 (D-DEF-05 계열, 2회차).
LIST_ELEMENT_RE = re.compile(r'^\s*[\"\'][^\"\']*[\"\']\s*,?\s*$')
NEG_WINDOW_LIST_ELEMENT = 12


# [T-A-V3-STEP1-002] A 가 발행한 **파일 단위 예외**는 D_INPUT_ALLOWLIST.json 이 authority 다.
# 블랭킷 면제가 아니라 allowlist 의 allowed 항목에 **정확히 그 경로**가 적힌 경우만 면제한다.
# A 가 예외를 철회하면 allowlist 에서 빠지고 스캐너는 즉시 다시 FAIL 을 낸다 — 그것이 목적이다.
def _explicit_allowed_paths() -> set[str]:
    import json as _j
    try:
        d = _j.loads((Path(__file__).resolve().parents[1] / "D_INPUT_ALLOWLIST.json").read_text())
    except Exception:
        return set()
    out = set()
    for a in (d.get("allowed") or d.get("allow") or []):
        for k in ("paths", "path"):
            v = a.get(k)
            if isinstance(v, str):
                out.add(v)
            elif isinstance(v, list):
                out.update(x for x in v if isinstance(x, str))
    return out


_ALLOWED_EXACT = _explicit_allowed_paths()


def severity(hit: dict, text: str) -> str:
    """파일 접근 호출 옆이면 FAIL. 부정 선언 문맥이면 WARN. 둘 다 아니면 보수적으로 FAIL.

    단 A 가 발행한 파일 단위 예외(_ALLOWED_EXACT)에 **정확히 일치하는 경로**는 면제한다.
    """
    ref = hit.get("reference")
    if ref in _ALLOWED_EXACT:
        return "ALLOWED_BY_EXCEPTION"
    # 허용목록은 저장소 상대경로다. D 도구가 같은 파일을 절대경로나 선행 `/` 형태로
    # 적으면 문자열이 달라 예외가 안 걸린다 — 파일은 같은데 표기만 다르다.
    # **꼬리가 허용 경로와 정확히 일치할 때만** 면제한다. 접두는 넓히지 않는다.
    if isinstance(ref, str):
        for a in _ALLOWED_EXACT:
            if a.endswith("/**"):
                continue
            if ref.endswith("/" + a):
                return "ALLOWED_BY_EXCEPTION"
    # allowlist 항목이 `.../**` 로 끝나면 그 디렉터리 접두만 면제한다.
    # 접두 매칭은 exact 매칭보다 넓으므로 `/**` 로 명시된 항목에만 적용한다.
    if isinstance(ref, str):
        for a in _ALLOWED_EXACT:
            if not a.endswith("/**"):
                continue
            d = a[:-3]                      # `/**` 를 떼어 디렉터리 경로만 남긴다
            if ref == d or ref.startswith(d + "/"):
                return "ALLOWED_BY_EXCEPTION"
            # 절대경로 표기도 같은 파일이다. 오늘 exact 예외에서 고친 것과 같은
            # 비대칭이 `/**` 쪽에 남아 있었다 — 상대 `…/ssot_snapshot/a.json` 은
            # 면제되고 절대 `/home/…/ssot_snapshot/a.json` 은 FAIL 이었다.
            #
            # 다만 디렉터리 접두는 파일 정확일치보다 넓으므로 **경로 구성요소가
            # 2개 이상인 허용 디렉터리에만** 적용한다. 그래야 짧은 이름
            # (`SSOTV3`)이 남의 트리에서 우연히 일치하지 않는다.
            if d.count("/") >= 1 and ("/" + d + "/") in ref:
                return "ALLOWED_BY_EXCEPTION"
    f = hit.get("file", "")
    line_no = hit.get("line")
    if not line_no:
        return "FAIL"
    lines = text.splitlines()
    cur = lines[line_no - 1] if line_no - 1 < len(lines) else ""
    if any(a in cur for a in ACCESS_MARKERS):
        hit["context"] = cur.strip()[:300]
        hit["why"] = "같은 줄에 파일 접근 호출이 있다"
        return "FAIL"
    if LIST_ELEMENT_RE.match(cur):
        win = NEG_WINDOW_LIST_ELEMENT
        hit["line_is_list_element"] = True
    elif f.endswith(STRUCTURED_SUFFIX):
        win = NEG_WINDOW_STRUCTURED
    else:
        win = NEG_WINDOW
    lo = max(0, line_no - 1 - win)
    hi = min(len(lines), line_no + win)
    ctx = " ".join(lines[lo:hi])
    if any(m in ctx for m in NEGATION_MARKERS):
        hit["context"] = ctx.strip()[:300]
        hit["why"] = "부정 선언 문맥 — 참조가 아니라 경계선 서술"
        return "WARN"
    hit["context"] = ctx.strip()[:300]
    hit["why"] = "접근 호출도 부정 문맥도 아님 — 보수적으로 FAIL"
    return "FAIL"


def scan_file(p: Path, denied: list[dict]) -> list[dict]:
    hits = []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [{"file": str(p), "kind": "UNREADABLE", "detail": str(e)}]
    self_decl = (p.name in SELF_DECLARATION_FILES
                 or p.name.startswith(SELF_DECLARATION_PREFIXES))
    for m in PATH_RE.finditer(text):
        cand = m.group(0)
        if len(cand) < 6:
            continue
        pat = denied_hit(cand, denied)
        if pat and not self_decl:
            line = text[:m.start()].count("\n") + 1
            src_line = text.splitlines()[line - 1] if line <= len(text.splitlines()) else ""
            if GUARD_MARKER in src_line:
                continue          # 감시 대상 선언 — 접근이 아니다
            try:
                _f = str(p.relative_to(RD.parent))
            except ValueError:
                _f = str(p)          # 대조군의 임시 파일은 트리 밖이다
            hits.append({"file": _f, "line": line,
                         "reference": cand[:200], "denied_pattern": pat, "kind": "DENIED_PATH"})
    if not self_decl:
        for h in hits:
            h["severity"] = severity(h, text)
        for tok in NAME_TOKENS:
            for m in re.finditer(re.escape(tok), text):
                line = text[:m.start()].count("\n") + 1
                hits.append({"file": str(p.relative_to(RD.parent)), "line": line,
                             "reference": tok, "denied_pattern": f"token:{tok}",
                             "kind": "DENIED_NAME_TOKEN"})
    for h in hits:
        h["severity"] = severity(h, text)
    return hits


def existence_check(denied: list[dict]) -> list[dict]:
    """D 워크트리 안에 금지 파일이 물리적으로 존재하는지."""
    out = []
    root = RD.parents[2]
    for tok in NAME_TOKENS:
        for p in root.rglob(f"*{tok}*"):
            if p.is_file() and p.name not in SELF_DECLARATION_FILES:
                out.append({"path": str(p), "kind": "DENIED_FILE_PRESENT", "token": tok})
    return out


def _override_root(root: Path, out_name: str) -> None:
    """임의 트리(예: 특정 SHA 를 풀어놓은 디렉터리)를 스캔 대상으로 바꾼다.

    Director 지시: RQ-D14 child 실행 시점의 exact HEAD 에서 방화벽을 다시 돌리고
    결과 commit 이후에도 post-run scan 을 남긴다. 두 기록은 서로 덮어쓰지 않는다.
    """
    global RD, NB_DIR, MANIFEST, OUT_NAME
    RD = root / "research/landing_accessibility/research_d"
    NB_DIR = root / "research/landing_accessibility/notebooks/d_research"
    MANIFEST = RD / "D_INPUT_ALLOWLIST.json"
    OUT_NAME = out_name


OUT_NAME = "D_INPUT_FIREWALL_VERIFICATION.json"
SCAN_LABEL = "current_worktree"


def run_controls(denied) -> dict:
    """매 실행 대조군 — 이 스캐너가 실제로 무언가를 막고 있는가.

    이 도구에는 대조군이 없었다. `verdict=PASS · FAIL=0` 이 (a) 정말 위반이
    없다 와 (b) **매처가 망가져 아무것도 안 걸린다** 를 같은 출력으로 낸다.
    D 의 `holdout_accessed=false` 주장 전체가 이 도구에 실려 있는데도 그랬다.

    B 가 T-B-V3-FINDING-010 에서 같은 형태를 잡았다 — `git diff --name-only HEAD`
    를 쓴 단언이 커밋 후 항상 빈 값이라 **한 번도 무언가를 잡은 적이 없고,
    깨진 적도 없어서 아무도 보지 않았다.** B 의 문장이 정확하다:
    **조용한 통과는 실패보다 오래 산다.**

    합성 경로로만 검사한다 — 파일을 만들지 않고 아무것도 읽지 않는다.
    """
    DENY = [
        ("label 절대경로", "/home/x/research/landing_accessibility/control/label/LABELS_FROZEN.jsonl"),
        ("holdout", "/home/x/research/landing_accessibility/control/label/HOLDOUT_FOR_C.json"),
        ("split 동결", "/home/x/research/landing_accessibility/control/label/LABEL_SPLIT_FROZEN.json"),
        ("control 기타", "/home/x/research/landing_accessibility/control/pilot/RESULT.json"),
        ("허용파일과 이름만 같은 남의 파일", "/home/x/evil/V3_RULING_INDEX.json"),
        ("짧은 허용 디렉터리명을 흉내낸 남의 트리", "/home/x/evil/SSOTV3/secret.json"),
    ]
    ALLOW = [
        ("허용 예외 상대경로", "research/landing_accessibility/control/v3/V3_RULING_INDEX.json"),
        ("허용 예외 절대경로", "/home/x/.agent_worktrees/claude_a_control/research/"
                          "landing_accessibility/control/v3/V3_0_1_SUCCESSOR_DELTA.md"),
        ("ssot_snapshot 하위 상대", "research/landing_accessibility/control/v3/ssot_snapshot/a.json"),
        ("ssot_snapshot 하위 절대", "/home/x/.agent_worktrees/claude_a_control/research/"
                              "landing_accessibility/control/v3/ssot_snapshot/a.json"),
    ]
    rows, ok = [], True
    for name, ref in DENY:
        got = severity({"reference": ref, "file": "control.py", "line": 1}, "")
        good = got.startswith("FAIL")
        ok &= good
        rows.append({"kind": "DENY", "expectation": "must_flag", "case": name,
                     "got": got, "expected": "FAIL", "ok": good})
    for name, ref in ALLOW:
        got = severity({"reference": ref, "file": "control.py", "line": 1}, "")
        good = got == "ALLOWED_BY_EXCEPTION"
        ok &= good
        rows.append({"kind": "ALLOW", "expectation": "must_not_flag", "case": name,
                     "got": got, "expected": "ALLOWED_BY_EXCEPTION", "ok": good})
    # 금지 패턴 목록 자체가 비어버리면 위 DENY 가 전부 통과할 수 없다는 보장이 없다
    n_denied = len(denied)
    # 줄 표식 대조 — 표식이 있으면 통과, 없으면 잡혀야 한다
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _td:
        _p = Path(_td) / "probe.py"
        _p.write_text('X = "research/landing_accessibility/control/label/x.json"'
                      f'  # {GUARD_MARKER}\n'
                      'Y = "research/landing_accessibility/control/label/y.json"\n',
                      encoding="utf-8")
        _h = scan_file(_p, denied)
        _marked = [x for x in _h if x.get("line") == 1]
        _plain = [x for x in _h if x.get("line") == 2]
        rows.append({"kind": "MARKER", "expectation": "must_not_flag",
                     "case": "표식 있는 줄은 잡히지 않는다", "got": len(_marked),
                     "expected": 0, "ok": len(_marked) == 0})
        rows.append({"kind": "MARKER", "expectation": "must_flag",
                     "case": "표식 없는 같은 경로는 잡힌다", "got": len(_plain),
                     "expected": ">=1", "ok": len(_plain) >= 1})
        ok &= (len(_marked) == 0 and len(_plain) >= 1)

    rows.append({"kind": "SANITY", "expectation": "must_flag", "case": "금지 패턴 개수",
                 "got": n_denied, "expected": ">=10", "ok": n_denied >= 10})
    ok &= n_denied >= 10
    return {"verdict": "PASS" if ok else "FAIL", "cases": rows,
            "naming": ("Δ40 — '양성/음성' 대신 `must_flag`/`must_not_flag`. "
                       "이 프로젝트에서 '양성대조' 가 두 뜻으로 쓰였다: "
                       "(a) 걸려야 하는 fixture, (b) 검색이 동작함을 보이는 확인. "
                       "이름을 고르지 않고 버린다."),
            "why": "대조군이 실패하면 스캔 결과를 PASS 로 내지 않는다 — "
                   "못 막는 스캐너의 FAIL=0 은 0 이 아니다"}


def _r35_block() -> dict:
    """Δ41-R35 (3)(4). 방화벽은 실패 시 **쓰지 않는** 것이 아니라
    `verdict=CONTROL_FAIL` 로 **기록하고** exit 2 한다 — 감사 흔적을 남기는 쪽이
    맞다고 보기 때문이다. 실증도 그 의미로 잰다."""
    import hashlib as _h, json as _j, subprocess as _s
    from pathlib import Path as _P
    tp = _P(__file__).resolve()
    rd = tp.parents[1]
    cur = _h.sha256(tp.read_bytes()).hexdigest()
    demo_p = rd / "results" / "CONTROL_FAILURE_DEMOS.json"
    demo = None
    if demo_p.exists():
        try:
            demo = _j.loads(demo_p.read_text(encoding="utf-8"))["demos"].get("d_input_firewall")
        except Exception:
            demo = None
    return {"rule": "Δ41-R35",
            "tool": {"path": "tools/d_input_firewall.py", "sha256": cur,
                     "commit": _s.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                      text=True).stdout.strip()},
            "on_control_failure": {
                "behavior": "verdict=CONTROL_FAIL 로 기록하고 exit 2 — 지우지 않고 남긴다",
                "demonstrated_in": "results/CONTROL_FAILURE_DEMOS.json",
                "demonstration": demo,
                "valid_for_this_commit": bool(demo and demo.get("tool_sha256") == cur
                                              and demo.get("verdict") == "PASS")}}


def main() -> int:
    global OUT_NAME, SCAN_LABEL
    args = sys.argv[1:]
    if "--root" in args:
        i = args.index("--root")
        root = Path(args[i + 1])
        out = args[args.index("--out") + 1] if "--out" in args else "D_INPUT_FIREWALL_VERIFICATION_alt.json"
        label = args[args.index("--label") + 1] if "--label" in args else str(root)
        _override_root(root, out)
        SCAN_LABEL = label
        # 산출은 항상 현재 워크트리의 results/ 에 쓴다 (임시 트리를 더럽히지 않는다)
        globals()["OUT_DIR_OVERRIDE"] = Path(__file__).resolve().parents[1] / "results"
    man = load_manifest()
    denied = man["denied"]
    files = [p for p in RD.rglob("*") if p.is_file() and p.suffix in SCAN_SUFFIX]
    files += [p for p in NB_DIR.rglob("*") if p.is_file() and p.suffix in SCAN_SUFFIX]

    controls = run_controls(denied)

    violations = []
    for p in files:
        violations.extend(scan_file(p, denied))
    violations.extend(existence_check(denied))

    # base SHA 에 label 경로가 있는지 (조상 관계 확인)
    base_label = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d"],
        cwd=REPO, capture_output=True, text=True).stdout
    base_label_hits = [l for l in base_label.splitlines()
                       if re.search(r"label|holdout", l, re.I)]

    for v in violations:
        v.setdefault("severity", "FAIL")
    fails = [v for v in violations if v["severity"] == "FAIL"]
    warns = [v for v in violations if v["severity"] == "WARN"]
    verdict = ("CONTROL_FAIL" if controls["verdict"] != "PASS"
               else "PASS" if not fails and not base_label_hits else "FAIL")
    doc = {
        "verification_id": "D-INPUT-FIREWALL-VERIFICATION",
        "scan_label": SCAN_LABEL,
        "scan_root": str(RD.parents[2]),
        "verdict": verdict,
        "claim_kind": "OBSERVATION",
        "checked_at_kst": datetime.now(KST).isoformat(),
        "d_head_sha": git("rev-parse", "HEAD"),
        "manifest_sha256": __import__("hashlib").sha256(MANIFEST.read_bytes()).hexdigest(),
        "scanned_files": len(files),
        # [R38] **무엇을 쟀는지의 바이트 신원.** 파일 수만 적으면 다음 실행과
        # 비교할 수 없다 — 같은 211개라도 내용이 다르면 다른 측정이다.
        # 파일별 sha 를 경로순으로 이어 해싱한다.
        "scanned_corpus_sha256": __import__("hashlib").sha256(
            "".join(f"{p.relative_to(RD.parents[2])}:"
                    f"{__import__('hashlib').sha256(p.read_bytes()).hexdigest()}\n"
                    for p in sorted(files)).encode()).hexdigest(),
        "corpus_identity_note": ("scanned_files 는 개수이고 이것은 신원이다. "
                                 "두 실행의 코퍼스 sha 가 다르면 FAIL 수를 비교하지 않는다 (R38)."),
        "scan_method": "경로 문자열 추출 + 금지 파일명 토큰 + 워크트리 물리 존재 확인",
        "controls": controls,
        "r35": _r35_block(),
        "exit_codes": {"0": "PASS", "2": "FAIL 또는 CONTROL_FAIL",
                       "4": "검사가 돌지 않았다 — 통과로도 실패로도 읽지 마라",
                       "note": "D 는 '돌지 않았다' 에 4 를 쓴다. A 는 2 를 쓰는데 "
                               "D 의 2 는 이미 FAIL 이라 바꾸면 나간 산출의 의미가 소급해 달라진다."},
        "verdict_rule": "대조군 PASS AND FAIL 등급 위반 0건 AND base SHA label 경로 0건 일 때만 PASS. WARN 은 산문 경계선 서술이라 PASS 를 막지 않지만 전부 기록한다.",
        "fail_count": len(fails),
        "warn_count": len(warns),
        "violations": violations,
        "base_sha_label_paths": base_label_hits,
        "base_sha": "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d",
        "self_declaration_files_excluded": sorted(SELF_DECLARATION_FILES),
        "self_declaration_prefixes_excluded": list(SELF_DECLARATION_PREFIXES),
        "residual_risk": ("파일시스템 접근 로그가 아니라 산출물 정적 스캔이다. worker 프로세스가 "
                          "읽고 아무 흔적을 남기지 않았을 가능성은 이 방법으로 배제되지 않는다. "
                          "다만 금지 파일이 D 워크트리에 존재하지 않고 D base 가 노출 커밋의 "
                          "조상이 아니므로 상대경로 접근 경로는 없다."),
    }
    out_dir = globals().get("OUT_DIR_OVERRIDE") or (RD / "results")
    out = out_dir / OUT_NAME
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    bad = [c for c in controls["cases"] if not c["ok"]]
    print(f"controls={controls['verdict']} ({len(controls['cases']) - len(bad)}"
          f"/{len(controls['cases'])})")
    for c in bad:
        print(f"  ** CONTROL FAIL ** {c['kind']} {c['case']}: got={c['got']} expected={c['expected']}")
    print(f"verdict={verdict}  scanned={len(files)} files  FAIL={len(fails)} WARN={len(warns)}  "
          f"base_sha_label_paths={len(base_label_hits)}")
    for v in fails[:20]:
        print("  FAIL", v["file"], v.get("line"), v["reference"][:80])
    for v in warns[:20]:
        print("  WARN", v["file"], v.get("line"), v["reference"][:60], "|", v.get("context", "")[:90])
    print(f"wrote {out}")
    return 0 if verdict == "PASS" else 2


import d_exit

if __name__ == "__main__":
    raise SystemExit(d_exit.run(main))
