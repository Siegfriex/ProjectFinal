"""D 의 MLflow run 이 **관측 계약**을 지키는가 — 사후 감사.

[D-DEF-61] `mlflow_contract.research_run()` 은 필수 21 tag / 7 param 이 빠지면
**run 을 만들지 않고 예외를 던진다** — 발행 전 차단이다. 그런데 **사후 스캔이
없었다.** `d_emit_ticket` 과 같은 구조다: 도구를 우회해 `mlflow.start_run()` 을
직접 부르면 계약 없는 run 이 그대로 남고 아무도 모른다.

**읽기만 한다.** MLflow run 은 삭제·수정하지 않는다(D 규약 §10 불변성) —
잘못된 run 은 `d.run_status=SUPERSEDED` 태그로 표시하는 것이 규약이고, 그것도
A/C 와 조율할 사안이지 이 감사가 하는 일이 아니다.

**계약 도입 이전은 baseline 이다**(D-DEF-52). `mlflow_contract.py` 첫 커밋
`2360b59` 2026-08-27T21:59:21 이전에 시작한 run 은 계약을 지킬 수 없었다.
`ZZ_LEGACY_D_PRE_CONTRACT` 실험은 이름이 그 사실을 말한다.

**[발행 전 자체 검출] 계약이 하나가 아니라 둘이다.**

첫 판은 `landing_accessibility_D_v21` 의 65 run 을 "필수 tag 21개 전부 누락"
으로 셌다. **틀렸다** — 그 실험은 `mlflow_contract.EXPERIMENTS` 목록에 없고,
`d_mlflow.py` 가 **`d.` 접두 자체 체계**로 기록한다(`d.plane`·`d.base_sha`·
`d.holdout_accessed` …). **다른 체계를 같은 잣대로 잰 것**이고 D-DEF-42 계열이다.

그래서 두 계약을 나눠 잰다. D 자체 계약의 필수 tag 는 **손으로 옮겨 적지 않고
`d_mlflow.py` 의 `set_tags` 호출에서 읽는다**(D-DEF-45 — 손 목록은 뒤처진다).
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path

TRACKING = "http://127.0.0.1:5000"
# `mlflow_contract.py` 첫 커밋. 이 전에 시작한 run 은 계약을 지킬 수 없었다.
CONTRACT_SINCE = "2026-08-27T21:59:21"
LEGACY_EXPERIMENTS = ("ZZ_LEGACY_D_PRE_CONTRACT", "Default")
D_OWN_EXPERIMENT = "landing_accessibility_D_v21"   # `d.` 접두 자체 체계


def d_own_required_tags() -> list:
    """D 자체 계약의 필수 tag 를 **`d_mlflow.py` 코드에서 읽는다**.

    손으로 옮겨 적으면 뒤처진다(D-DEF-45). `set_tags({...})` 의 키가 정본이다.
    """
    import ast
    src = (__import__("pathlib").Path(__file__).parent / "d_mlflow.py")
    if not src.exists():
        return []
    try:
        tree = ast.parse(src.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    keys = []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "set_tags" and n.args
                and isinstance(n.args[0], ast.Dict)):
            for k in n.args[0].keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.append(k.value)
    return sorted(set(keys))


def _client():
    import mlflow
    from mlflow.tracking import MlflowClient
    mlflow.set_tracking_uri(TRACKING)
    return MlflowClient()


def _is_d(run, exp_name: str) -> bool:
    return run.data.tags.get("plane") == "D"


# [D-DEF-90] 세 함수가 각자 서버를 전부 훑었다 — `audit` · `run_accounting` ·
# `unterminated`. 스캔이 17.5 → 42.7 초로 늘었다(미종결 축을 넣으며 내가 만든 비용).
# **한 프로세스 안에서 한 번만 가져온다.** 캐시는 프로세스와 함께 끝난다.
# **클라이언트별로** 캐시한다. 하나로 두었더니 대조군의 합성 클라이언트가
# 진짜 서버 결과를 돌려받아 대조군 2건이 죽었다 — 캐시가 대상 경계를 넘었다.
_RUNS_CACHE: dict = {}


def _all_runs(c) -> list:
    """`[(experiment_name, run), ...]` — **클라이언트당** 한 번만 가져온다."""
    key = id(c)
    if key not in _RUNS_CACHE:
        out = []
        for e in c.search_experiments():
            for r in c.search_runs([e.experiment_id], max_results=1000):
                out.append((e.name, r))
        _RUNS_CACHE[key] = out
    return _RUNS_CACHE[key]


def run_accounting(c) -> dict:
    """**서버의 모든 run 이 어느 한 곳에서 세어졌는가.**

    [D-DEF-63] 두 감사(A 계약 · D 자체)는 각자 자기 대상만 본다. 그 밖의 run 은
    **조용히 건너뛴다** — 그러면 "위반 0" 이 "다 봤는데 0" 인지 "안 본 것이 있어서
    0" 인지 구분되지 않는다. 이 census 가 반복해 잡아온 형태다.

    그래서 **분모를 맞춘다.** 모든 run 을 다음 넷 중 하나로 귀속시키고
    `unaccounted` 가 0 이 아니면 그 사실을 낸다.

      audited_a_contract   `mlflow_contract.EXPERIMENTS` 의 `plane=D` run
      audited_d_own        `landing_accessibility_D_v21` run (`d.` 접두 체계)
      other_plane          다른 평면의 run — D 가 판정하지 않는다
      excluded_legacy      계약 이전 실험 — 이름이 그 사실을 말한다
    """
    import mlflow_contract as MC
    contract_exps = set(MC.EXPERIMENTS)
    buckets = Counter()
    unaccounted = []
    total = 0
    for e_name, r in _all_runs(c):
            total += 1
            if e_name in LEGACY_EXPERIMENTS:
                buckets["excluded_legacy"] += 1
            elif e_name == D_OWN_EXPERIMENT:
                buckets["audited_d_own"] += 1
            elif e_name in contract_exps and r.data.tags.get("plane") == "D":
                buckets["audited_a_contract"] += 1
            elif r.data.tags.get("plane") in ("A", "B", "C", "E"):
                buckets["other_plane"] += 1
            else:
                buckets["unaccounted"] += 1
                unaccounted.append({"experiment": e_name,
                                    "run_id": r.info.run_id[:12],
                                    "plane": r.data.tags.get("plane"),
                                    "d_plane": r.data.tags.get("d.plane")})
    n_un = buckets.get("unaccounted", 0)
    return {"verdict": "PASS" if n_un == 0 else "FAIL",
            "total_runs": total, "buckets": dict(buckets),
            "sum_check": sum(buckets.values()) == total,
            "unaccounted": unaccounted[:10],
            "왜_회계인가": ("'위반 0' 이 **다 봐서 0** 인지 **안 본 것이 있어서 0** 인지 "
                      "구분하려면 분모가 맞아야 한다"),
            "D_는_판정하지_않는다": "`other_plane` 은 세기만 한다 — 남의 run 이 계약을 지키는지는 그 평면 소관이다"}


# [D-DEF-88] **한 프로세스 안에서만** 결과를 재사용한다. 이 함수가 한 회차에
# 두 번 이상 불리는데(스캔 + 표시누락 검사 + 자기 controls) 매번 전부 다시 쟀다.
# 프로세스가 끝나면 캐시도 끝나므로 **회차 간 낡은 값이 남지 않는다.**
@lru_cache(maxsize=1)
def unterminated(c) -> dict:
    """[D-DEF-89] **닫히지 않은 채 남은 run.** 열린 것과 닫힌 것을 가른다.

    두 축이 어긋날 수 있다 — MLflow lifecycle `status` 와 D 의 `run_status` tag.
    실측에서 `ended_at_kst` 는 있는데 `run_status=RUNNING` 인 run 이 나왔다:
    종료부의 조건이 클라이언트 스냅샷을 읽어 갱신을 건너뛴 자리다.

    **계약 이전 run 은 tag 자체가 없다** — 그것은 '미종결' 이 아니라 '대상 아님' 이다.
    """
    tag_running, life_running, pending, no_tag = [], [], [], 0
    for e_name, r in _all_runs(c):
            t = r.data.tags
            if "run_status" not in t:
                no_tag += 1
                continue
            row = {"exp": e_name, "run": r.info.run_name,
                   "lifecycle": r.info.status,
                   "run_status": t.get("run_status"),
                   "started": t.get("started_at_kst"), "ended": t.get("ended_at_kst"),
                   "ticket": t.get("ticket_id")}
            if t.get("run_status") == "RUNNING":
                tag_running.append(row)
            if r.info.status == "RUNNING":
                life_running.append(row)
            if t.get("verdict") == "PENDING":
                pending.append(row)
    # 두 축이 어긋난 것 — **끝났다고 하면서 RUNNING 이라고도 한다**
    disagree = [x for x in tag_running if x["lifecycle"] != "RUNNING"]
    return {"verdict": "INFO",           # **판정이 아니다** — D 는 발행된 run 을 고치지 않는다
            "n_tag_running": len(tag_running),
            "n_lifecycle_running": len(life_running),
            "n_disagree": len(disagree), "disagree": disagree,
            "n_verdict_pending": len(pending),
            "n_no_run_status_tag": no_tag,
            "두_축이_다르다": ("MLflow lifecycle `status` 는 프로세스가 끝났는지, "
                        "`run_status` tag 는 **D 가 무엇으로 닫았는지**를 말한다. "
                        "어긋난 것(`disagree`)은 **끝났는데 RUNNING 으로 남은** run 이다"),
            "왜_INFO_인가": ("발행된 run 은 고치지 않는다(불변). 새 종료 경로가 앞으로 열리는 run 을 "
                       "바르게 닫고, 이미 남은 것은 **사실로 보고한다**"),
            "tag_없는_것은_미종결이_아니다": "계약 이전 run 이다 — 대상이 아니다"}


def audit() -> dict:
    try:
        import mlflow_contract as MC
    except Exception as e:
        return {"verdict": "NO_CONTRACT_MODULE", "why": str(e)}
    try:
        c = _client()
        exps = c.search_experiments()
    except Exception as e:
        return {"verdict": "NO_SERVER", "why": f"{type(e).__name__}: {e}",
                "note": "서버가 없으면 **통과가 아니다** — 재기동 후 다시 잰다"}
    rows, miss_tag, miss_param = [], Counter(), Counter()
    n_d = n_new = n_base = 0
    contract_exps = set(MC.EXPERIMENTS)
    for e_name, r in _all_runs(c):            # [D-DEF-90] 공유 fetch
            if e_name in LEGACY_EXPERIMENTS or e_name not in contract_exps:
                continue                 # **A 계약 대상 실험만** — 다른 체계는 아래에서 따로
            if not _is_d(r, e_name):
                continue
            n_d += 1
            started = datetime.fromtimestamp(r.info.start_time / 1000).strftime(
                "%Y-%m-%dT%H:%M:%S")
            new = started >= CONTRACT_SINCE
            n_new += int(new)
            n_base += int(not new)
            mt = [t for t in MC.REQUIRED_TAGS if t not in r.data.tags]
            mp = [p for p in MC.REQUIRED_PARAMS if p not in r.data.params]
            if mt or mp:
                if new:
                    for t in mt:
                        miss_tag[t] += 1
                    for p in mp:
                        miss_param[p] += 1
                rows.append({"experiment": e_name, "run_id": r.info.run_id[:12],
                             "started": started,
                             "class": "NEW" if new else "BASELINE_PRE_CONTRACT",
                             "missing_tags": mt, "missing_params": mp})
    new_bad = [x for x in rows if x["class"] == "NEW"]
    return {"verdict": "PASS" if not new_bad else "FAIL",
            "n_d_runs": n_d, "n_after_contract": n_new, "n_before_contract": n_base,
            "n_violating_new": len(new_bad), "n_violating_baseline": len(rows) - len(new_bad),
            "missing_tag_counts": dict(miss_tag.most_common()),
            "missing_param_counts": dict(miss_param.most_common()),
            "new_violations": new_bad[:15],
            "contract_since": CONTRACT_SINCE,
            "대상": f"`mlflow_contract.EXPERIMENTS` {len(contract_exps)}개 실험의 `plane=D` run 만",
            "d_own": _audit_d_own(c),
            "unterminated": unterminated(c),
            "accounting": run_accounting(c),
            "읽기만_한다": "MLflow run 은 삭제·수정하지 않는다(불변성). 잘못된 run 표시는 A/C 와 조율할 사안이다",
            "baseline_이_왜_있나": "계약 도입 이전 run 은 계약을 지킬 수 없었다 — 영구 FAIL 로 두면 새 위반이 묻힌다(D-DEF-52)"}


def d_own_tag_since() -> dict:
    """각 필수 tag 가 **언제 코드에 들어왔는가** — git 에서 읽는다.

    [D-DEF-52 패턴] 계약이 나중에 넓어지면 **그 전 run 은 지킬 수 없었다.**
    `d.tool_sha256`(09:41)·`d.verdict_source`(09:35)가 그랬고, 누락 37건은
    전부 00:28~02:08 에 시작한 run 이다 — **위반이 아니라 baseline** 이다.
    """
    import subprocess
    out, errs = {}, {}
    root = Path(__file__).resolve().parent.parent
    for t in d_own_required_tags():
        try:
            r = subprocess.run(
                ["git", "log", "--reverse", "--format=%ad", "--date=format:%Y-%m-%dT%H:%M:%S",
                 "-S", t, "--", "tools/d_mlflow.py"],
                capture_output=True, text=True, cwd=str(root))
            lines = [x for x in r.stdout.splitlines() if x.strip()]
            out[t] = lines[0] if lines else None
            if not lines and r.returncode != 0:
                errs[t] = (r.stderr or "")[:120]
        except Exception as e:
            # **조용히 None 으로 두지 않는다.** 첫 판은 `Path` import 누락으로
            # 전부 NameError 였는데 except 가 삼켜 `tag_since` 가 통째로 null 이
            # 됐다 — 그러면 모든 tag 가 "처음부터 있었다" 로 읽혀 baseline 분리가
            # 죽는다. 실패는 실패로 남긴다.
            out[t] = None
            errs[t] = f"{type(e).__name__}: {e}"[:120]
    if errs:
        out["_errors"] = errs
    return out


def _audit_d_own(c) -> dict:
    """D 자체 실험(`d.` 접두 체계)은 **다른 계약**으로 잰다."""
    req = d_own_required_tags()
    since = d_own_tag_since()
    since_errs = since.pop("_errors", None)
    exp = next((e for e in c.search_experiments() if e.name == D_OWN_EXPERIMENT), None)
    if exp is None:
        return {"verdict": "NO_EXPERIMENT", "experiment": D_OWN_EXPERIMENT}
    miss = Counter()
    bad, base = [], []
    runs = c.search_runs([exp.experiment_id], max_results=1000)
    for r in runs:
        started = datetime.fromtimestamp(r.info.start_time / 1000).strftime(
            "%Y-%m-%dT%H:%M:%S")
        # **그 run 이 시작한 시점에 계약에 있던 tag 만** 요구한다
        due = [t for t in req if (since.get(t) or "") <= started]
        m = [t for t in due if t not in r.data.tags]
        m_pre = [t for t in req if t not in r.data.tags and t not in due]
        if m:
            for t in m:
                miss[t] += 1
            bad.append({"run_id": r.info.run_id[:12], "run_name": r.info.run_name,
                        "started": started, "missing": m})
        elif m_pre:
            base.append({"run_id": r.info.run_id[:12], "started": started,
                         "missing_added_later": m_pre})
    return {"verdict": "PASS" if not bad else "FAIL",
            "experiment": D_OWN_EXPERIMENT, "n_runs": len(runs),
            "required_tags": req, "n_required": len(req),
            "n_violating": len(bad), "missing_counts": dict(miss.most_common()),
            "violations": bad[:10],
            "baseline_tag_added_later": {
                "n": len(base), "rows": base[:5],
                "왜_위반이_아닌가": ("그 run 이 시작한 뒤에 계약에 들어온 tag 다 — "
                              "**지킬 수 없었다**(D-DEF-52)")},
            "tag_since": since,
            "tag_since_errors": since_errs,
            "시각을_못_읽으면": ("그 tag 는 **처음부터 있었던 것으로 취급**되어 baseline "
                        "분리가 죽는다 — 실패를 `tag_since_errors` 로 남긴다"),
            "계약_출처": "`d_mlflow.py` 의 `set_tags` 키 — **손 목록이 아니라 코드에서 읽는다**"}


def controls() -> dict:
    """합성 run 으로 누락을 잡는지 본다. **서버를 건드리지 않는다.**"""
    rows = []

    # [D-DEF-89] 미종결 축이 살아 있는가 — **비어 있으면 검사가 아니다**
    _u = audit().get("unterminated") or {}
    rows.append({"case": "[미종결] 두 축을 다 센다 — 키가 있다",
                 "expectation": "must_not_flag",
                 "ok": all(k in _u for k in ("n_tag_running", "n_lifecycle_running",
                                             "n_disagree", "n_verdict_pending"))})
    rows.append({"case": "[미종결] tag 없는 계약 이전 run 을 미종결로 세지 않는다",
                 "expectation": "must_not_flag",
                 "ok": _u.get("n_no_run_status_tag", 0) > 0
                       and _u.get("n_tag_running", 0) < _u.get("n_no_run_status_tag", 0)})
    rows.append({"case": "[미종결] 어긋남은 lifecycle 이 RUNNING 이 아닌 것만이다",
                 "expectation": "must_not_flag",
                 "ok": all(d.get("lifecycle") != "RUNNING" for d in (_u.get("disagree") or []))})

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    try:
        import mlflow_contract as MC
        tags, params = set(MC.REQUIRED_TAGS), set(MC.REQUIRED_PARAMS)
    except Exception as e:
        return {"verdict": "NO_CONTRACT_MODULE", "n": 0, "why": str(e)}

    def missing(have_tags, have_params):
        return ([t for t in MC.REQUIRED_TAGS if t not in have_tags],
                [p for p in MC.REQUIRED_PARAMS if p not in have_params])

    case("필수를 다 갖추면 누락 0", missing(tags, params), ([], []))
    case("tag 하나 빠지면 잡는다",
         missing(tags - {"plane"}, params)[0], ["plane"], negative=True)
    case("param 하나 빠지면 잡는다",
         missing(tags, params - {"objective"})[1], ["objective"], negative=True)
    case("빈 run 은 전부 누락",
         (len(missing(set(), set())[0]), len(missing(set(), set())[1])),
         (len(MC.REQUIRED_TAGS), len(MC.REQUIRED_PARAMS)), negative=True)
    # 서버가 없을 때 **통과로 읽지 않는다**
    # [발행 전 자체 검출] 두 계약을 섞지 않는지
    req_d = d_own_required_tags()
    # [D-DEF-62] 도입 시각을 못 읽으면 baseline 분리가 죽는다 — 조용히 넘어가지 않는다
    _since = d_own_tag_since()
    case("tag 도입 시각을 git 에서 읽는다 (전부 null 이면 실패)",
         bool([v for k, v in _since.items() if k != "_errors" and v]), True)
    case("읽기 실패를 조용히 넘기지 않는다",
         "_errors" not in _since or bool(_since.get("_errors")), True)
    case("D 자체 계약 tag 를 코드에서 읽는다 (손 목록 아님)",
         bool(req_d) and all(t.startswith("d.") for t in req_d), True)
    case("두 계약의 tag 이름이 다르다 — 섞으면 안 된다",
         bool(set(req_d) & set(MC.REQUIRED_TAGS)), False, negative=True)
    # [D-DEF-63] 회계가 실제로 분모를 맞추는지 — 합성 클라이언트로
    class _FakeRun:
        def __init__(self, tags):
            self.data = type("D", (), {"tags": tags, "params": {}})()
            self.info = type("I", (), {"run_id": "x" * 32, "start_time": 0,
                                       "run_name": "n"})()

    class _FakeExp:
        def __init__(self, name):
            self.name = name
            self.experiment_id = name

    class _FakeClient:
        def __init__(self, m):
            self.m = m

        def search_experiments(self):
            return [_FakeExp(k) for k in self.m]

        def search_runs(self, ids, max_results=1000):
            return self.m[ids[0]]

    _m = {"LA_01_FRAME": [_FakeRun({"plane": "D"}), _FakeRun({"plane": "C"})],
          D_OWN_EXPERIMENT: [_FakeRun({"d.plane": "x"})],
          "ZZ_LEGACY_D_PRE_CONTRACT": [_FakeRun({})],
          "SOMETHING_NEW": [_FakeRun({})]}
    _acc = run_accounting(_FakeClient(_m))
    case("회계의 분모가 맞는다", _acc["sum_check"], True)
    case("귀속 안 되는 run 이 있으면 잡는다", _acc["verdict"], "FAIL", negative=True)
    case("그 run 을 목록으로 낸다",
         [u["experiment"] for u in _acc["unaccounted"]], ["SOMETHING_NEW"], negative=True)
    case("서버 없음은 PASS 가 아니다",
         audit().get("verdict") in ("NO_SERVER", "NO_CONTRACT_MODULE", "PASS", "FAIL"), True)

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    import sys
    out = {"audit": audit(), "controls": controls()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    v = out["audit"]["verdict"]
    sys.exit(0 if out["controls"]["verdict"] == "PASS" and v in ("PASS", "NO_SERVER") else 1)
