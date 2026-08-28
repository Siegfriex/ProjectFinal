"""D 연구 run을 MLflow에 기록한다.

왜 필요한가: D는 notebook과 script를 계속 만든다. 어떤 입력 스냅샷에서 어떤
코드 SHA로 어떤 숫자가 나왔는지가 run 단위로 남지 않으면, 나중에 "그 수치가
어느 시점 것이냐"를 다시 재구성해야 한다. MLflow는 그 lineage를 붙잡는 용도다.

MLflow는 연구 결론의 권위가 아니다. canonical 산출은 Git의 results/*.json 이고
MLflow는 그것을 가리키는 index다. run 은 idempotent 하게 기록된다
(rq_id + result 파일 sha256 이 같으면 다시 만들지 않는다).

usage:
    d_mlflow.py sync            # results/ 를 스캔해 신규/변경된 RQ만 기록
    d_mlflow.py list            # 기록된 run 요약
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import mlflow

TRACKING_URI = "http://127.0.0.1:5000"
EXPERIMENT = "landing_accessibility_D_v21"

RD = Path(__file__).resolve().parents[1]
WT = RD.parents[2]
NB_DIR = RD.parent / "notebooks" / "d_research"
BASE_SHA = "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d"
BRANCH = "claude-d/research-sandbox-v21"

VERDICTS = ("SUPPORTED", "PARTIALLY_SUPPORTED", "REFUTED", "NOT_SUPPORTED",
            "INCONCLUSIVE", "NOT_TESTABLE")
KEY_OK = re.compile(r"[^A-Za-z0-9_\-./: ]")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=WT, capture_output=True, text=True).stdout.strip()


def flatten_numeric(obj, prefix: str = "", out: dict | None = None) -> dict:
    """중첩 JSON에서 숫자 leaf만 dotted key 로 뽑는다. bool 은 0/1 로."""
    out = {} if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten_numeric(v, f"{prefix}{k}." if not prefix else f"{prefix}{k}.", out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        key = KEY_OK.sub("_", prefix.rstrip("."))[:240]
        if key:
            out[key] = float(obj)
    elif isinstance(obj, bool):
        key = KEY_OK.sub("_", prefix.rstrip("."))[:240]
        if key:
            out[key] = float(obj)
    return out


def parse_verdict(md: Path) -> str:
    if not md.exists():
        return "UNKNOWN"
    head = md.read_text(encoding="utf-8")[:4000]
    for v in sorted(VERDICTS, key=len, reverse=True):
        if v in head:
            return v
    return "UNKNOWN"


def parse_limitation(md: Path) -> str:
    """[A STEP1-037 전수 재수행] 예전에는 **파일 부재**와 **한계 절 없음**을
    둘 다 빈 문자열로 냈다. 빈 한계는 MLflow 에서 **'한계가 없다'** 로 읽힌다 —
    이 세션의 중심 결함이 메타데이터 층에 나타난 형태다. 셋을 가른다.
    """
    if not md.exists():
        return "NOT_STATED[rule=FINDINGS.md 파일 없음]"
    txt = md.read_text(encoding="utf-8")
    # [시정] `^##+\s*Limitations?` 는 **번호가 붙은 표제를 못 잡는다.**
    # D 산출은 `## 12. Limitation` · `## 8. 가장 무거운 limitation` 형태를 쓴다.
    # 이 정규식 때문에 **한계가 있는 18건이 '한계 절 없음' 으로 나왔다** —
    # 빈 값이었을 때는 조용했고, 직전 회차에 sentinel 을 넣자 그것이
    # **'한계가 없다' 는 적극적 주장**이 될 뻔했다. 표제 안 어디든 허용한다.
    m = re.search(r"^#{2,4}\s*[^\n]*?\blimitations?\b[^\n]*$(.*?)(?=^#{2,4}\s|\Z)",
                  txt, re.M | re.S | re.I)
    if not m:
        # R54 — `NOT_STATED` 는 **파서 규칙을 병기**한다. 규칙 없이 '없음' 만
        # 적으면 다음 사람이 그 '없음' 을 원문의 성질로 읽는다.
        return ("NOT_STATED[rule=heading matching /^#{2,4}.*\\blimitations?\\b/i]")
    body = [ln.strip(" -*0123456789.") for ln in m.group(1).splitlines() if ln.strip()]
    return (body[0] if body else "EMPTY[절은 있고 내용이 비었다]")[:480]


# RQ -> notebook 매핑. 번호가 1:1이 아니므로 추론하지 않고 명시한다.
NOTEBOOK_MAP = {
    "RQ-D1": "D00_pilot_forensic_reconstruction.ipynb",
}


def discover(base=None) -> list[dict]:
    """results/ 에서 RQ 단위 산출을 찾는다. rq_id 는 파일명에서만 뽑는다.

    [D-DEF-06 시정] 이전 정규식 `RQ_(D\\d+)_` 는 숫자 뒤에 `_` 를 요구해
    하위 RQ(RQ_D13A, RQ_D12A, RQ_D6B1 …)와 RF001/RF2/DSUP/PILOT 계열을 전부 놓쳤다.
    36개 산출 중 10개만 색인되고 있었다. prefix 규칙(`<prefix>_FINDINGS.md`)으로 바꾼다.
    """
    import re as _re

    # RQ 산출이 아닌 것 — 관측 테이블·결함기록·방화벽·부모런·사전등록
    SKIP = _re.compile(
        r"^(D_OBSERVATION_TABLE|D_DEF_|D_INPUT_|D_CORPUS_|D_DASHBOARD|D_FACT_"
        r"|PILOT_PREREGISTRATION)|_PARENT_RUN\.json$|_MLFLOW_RUN\.json$"
    )

    def rq_id_of(prefix: str) -> str | None:
        if m := _re.fullmatch(r"RQ_(D[0-9A-Za-z]+)", prefix):
            return f"RQ-{m.group(1)}"
        if m := _re.fullmatch(r"RQ_E(\d+[a-z]?)", prefix):
            return f"RQ-E-{m.group(1)}"
        if m := _re.fullmatch(r"(RF001|RF2)_([A-Z])", prefix):
            return f"{m.group(1)}-{m.group(2)}"
        if m := _re.fullmatch(r"DSUP(\d+)", prefix):
            return f"D-SUP-{m.group(1)}"
        if prefix == "PILOT_E":
            return "RQ-D-PILOT-001-E"
        return None

    def prefix_of(name: str) -> str | None:
        stem = name.rsplit(".", 1)[0]
        parts = stem.split("_")
        # 가장 긴 것부터 시도해 `<prefix>_FINDINGS.md` 규칙과 맞는 지점을 찾는다
        for k in range(min(3, len(parts)), 0, -1):
            cand = "_".join(parts[:k])
            if rq_id_of(cand):
                return cand
        return None

    found: dict[str, dict] = {}
    root = Path(base) if base else (RD / "results")
    for f in sorted(root.glob("*.json")):
        if SKIP.search(f.name):
            continue
        prefix = prefix_of(f.name)
        if not prefix:
            continue
        rq = rq_id_of(prefix)
        e = found.setdefault(rq, {
            "rq_id": rq,
            "md": root / f"{prefix}_FINDINGS.md",
            "json": None,
        })
        # [D-DEF-10 시정] 같은 prefix 에 JSON 이 여럿이면 알파벳 첫 파일을 집었다.
        # RQ_D13b12 는 134바이트 MLflow 사이드카가 먼저 잡혀 결과 JSON 을 가렸고,
        # 완결 게이트가 "verdict 없음" 이라고 보고했다 — 그 파일에 대해선 참이지만
        # 그 RQ 에 대해선 거짓이다. 최상위 verdict 를 가진 파일을 우선한다.
        try:
            has_verdict = "verdict" in json.loads(f.read_text())
        except Exception:
            has_verdict = False
        if e["json"] is None or (has_verdict and not e.get("_json_has_verdict")):
            e["json"] = f
            e["_json_has_verdict"] = has_verdict
    return [{k: v for k, v in e.items() if not k.startswith("_")} for e in found.values()]


def authoritative_verdict(js: Path | None, md: Path) -> tuple[str, str]:
    """verdict 는 **JSON 최상위**에서 읽는다. md 파서는 대체 경로일 뿐이다.

    예전에는 `parse_verdict(md)` 하나만 색인에 실었다. 그 파서는
    `sorted(VERDICTS, key=len, reverse=True)` 로 **앞 4000자에서 가장 긴
    토큰**을 고른다 — 가설별 판정표에 `PARTIALLY_SUPPORTED` 가 먼저 나오면
    그것이 RQ 의 판정으로 색인된다.

    실측: JSON 정본과 md 파서가 **11건에서 갈렸고 둘은 정반대**였다
    (`RQ-D12A` json=REFUTED / md=SUPPORTED · `D-SUP-02` json=SUPPORTED /
    md=NOT_SUPPORTED). **완결 게이트가 이미 JSON 최상위 verdict 를 요구한다**
    — 정본이 어디인지는 정해져 있었고 색인만 다른 것을 읽고 있었다.

    반환: (verdict, source)
    """
    if js and js.exists():
        try:
            v = json.loads(js.read_text(encoding="utf-8")).get("verdict")
        except Exception:                                    # noqa: BLE001
            v = None
        if isinstance(v, dict):          # RQ-D8 형태 — 값이 구조를 갖는다
            v = v.get("value") or v.get("verdict")
        if isinstance(v, str) and v.strip():
            return v.strip(), "json_top_level"
    mv = parse_verdict(md) if md.exists() else "UNKNOWN"
    return mv, "md_heuristic_fallback"


def extraction_health() -> dict:
    """R54 — **추출 결과가 빈 비율을 원문의 존재 여부와 대조한다.**

    D 의 한계 파서 결함(18/27 을 빈 값으로)은 **일회성 대조**로 드러났다.
    A 가 STEP1-039 에서 적었다 — "분모 없이 빈 값만 보면 그것은 관측처럼
    보인다". 그 대조를 매 sync 마다 한다.

    분모는 **FINDINGS.md 를 가진 산출 수**이고, 분자는 추출이 값을 낸 수다.
    비율이 떨어지면 파서를 의심한다 — 산출이 갑자기 한계를 안 적기 시작할
    가능성보다 파서가 표기 변화를 못 따라갔을 가능성이 크다.
    """
    rows = {"with_md": 0, "limitation_value": 0, "limitation_not_stated": 0,
            "limitation_empty": 0, "verdict_json": 0, "verdict_fallback": 0}
    not_stated = []
    for it in discover():
        md, js = it["md"], it["json"]
        if not md.exists():
            continue
        rows["with_md"] += 1
        lim = parse_limitation(md)
        if lim.startswith("NOT_STATED"):
            rows["limitation_not_stated"] += 1
            not_stated.append(it["rq_id"])
        elif lim.startswith("EMPTY"):
            rows["limitation_empty"] += 1
        else:
            rows["limitation_value"] += 1
        _, src = authoritative_verdict(js, md)
        rows["verdict_json" if src == "json_top_level" else "verdict_fallback"] += 1
    d = rows["with_md"] or 1
    rows["limitation_value_ratio"] = round(rows["limitation_value"] / d, 3)
    rows["not_stated_ids"] = not_stated[:10]
    rows["how_to_read"] = ("`NOT_STATED` 가 0 이 아니면 **원문을 직접 열어** "
                           "다른 표기를 쓰는지 확인한다. 파서를 먼저 의심한다 — "
                           "이 검사는 그 대조를 강제하려고 있다.")
    rows["denominator"] = "FINDINGS.md 를 가진 산출 수"
    return rows


def gate(rq: str, md: Path, js: Path | None, nb_dir: Path) -> tuple[bool, str]:
    """완결 게이트 — 세 조건. `sync()` 안에 있던 것을 함수로 뺐다.

    안에 박혀 있는 동안 이 게이트에는 **대조군이 없었다.** 그리고 이 게이트가
    *닫힌 채로* 망가지면 출력이 지금과 구분되지 않는다 — 대부분의 legacy RQ 가
    이미 `미완` 이라, 전부 `미완` 이 되어도 똑같아 보인다. 열린 채로 망가지면
    D-DEF-07(빈 run 영구 잔존)이 재발한다. 양쪽 다 조용하다.

    D 의 결함 이력이 이 함수에 다 들어 있다:
      D-DEF-07  게이트 자체가 없어 in-flight 산출이 색인됐다
      D-DEF-10  sidecar 가 정렬상 먼저 와서 본 결과를 가렸다 → 내용 계약으로 선택
      D-DEF-10b 노트북 glob 이 k=1 까지 내려가 남의 노트북을 잡았다 → k>=2
    """
    if js and js.exists():
        try:
            if "verdict" not in json.loads(js.read_text()):
                return False, "미완: verdict 없음"
        except Exception:
            return False, "미완: JSON 파싱 실패"
        if not md.exists():
            return False, "미완: FINDINGS.md 없음"
        prefix = js.name.rsplit(".", 1)[0]
        parts = prefix.split("_")
        nbs = []
        if rq in NOTEBOOK_MAP:                       # 이름이 규칙과 다른 예외
            nbs = [nb_dir / NOTEBOOK_MAP[rq]] if (nb_dir / NOTEBOOK_MAP[rq]).exists() else []
        for k in range(min(3, len(parts)), 1, -1):
            if nbs:
                break
            nbs = sorted(nb_dir.glob("_".join(parts[:k]) + "*.ipynb"))
            if nbs:
                break
        if not nbs:
            return False, "미완: 노트북 없음"
    return True, "OK"


def gate_controls() -> dict:
    """게이트가 아직 무언가를 막고 있는가 — 매 sync 마다 확인한다.

    임시 디렉터리에만 쓴다. 실제 results/ 와 notebooks/ 는 건드리지 않는다.
    """
    import tempfile
    cases, ok = [], True
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        nb = t / "nb"; nb.mkdir()
        def mk(name, body, findings=True, notebook=True):
            js = t / f"{name}.json"
            js.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            md = t / f"{name}_FINDINGS.md"
            if findings:
                md.write_text("# f", encoding="utf-8")
            if notebook:
                (nb / f"{name}.ipynb").write_text("{}", encoding="utf-8")
            return md, js

        md, js = mk("RQ_DXX_thing", {"verdict": "SUPPORTED"})
        cases.append(("완결 산출은 통과", gate("RQ-DXX", md, js, nb), True))
        md, js = mk("RQ_DYY_thing", {"headline": "x"})          # verdict 없음
        cases.append(("verdict 없으면 막힘", gate("RQ-DYY", md, js, nb), False))
        md, js = mk("RQ_DZZ_thing", {"verdict": "X"}, findings=False)
        cases.append(("FINDINGS.md 없으면 막힘", gate("RQ-DZZ", md, js, nb), False))
        md, js = mk("RQ_DWW_thing", {"verdict": "X"}, notebook=False)
        cases.append(("노트북 없으면 막힘", gate("RQ-DWW", md, js, nb), False))
        # D-DEF-10b 회귀: 남의 노트북이 있어도 통과하면 안 된다
        (nb / "RQ_OTHER_unrelated.ipynb").write_text("{}", encoding="utf-8")
        md, js = mk("RQ_DVV_thing", {"verdict": "X"}, notebook=False)
        cases.append(("남의 노트북으로 통과하지 않음 (D-DEF-10b)",
                      gate("RQ-DVV", md, js, nb), False))
        bad = t / "RQ_DUU_thing.json"
        bad.write_text("{not json", encoding="utf-8")
        cases.append(("JSON 깨지면 막힘",
                      gate("RQ-DUU", t / "RQ_DUU_thing_FINDINGS.md", bad, nb), False))

    rows = []
    for name, (got_ok, reason), want in cases:
        good = got_ok is want
        ok &= good
        rows.append({"case": name,
                     "expectation": "must_not_flag" if want else "must_flag",
                     "passed_gate": got_ok, "expected": want,
                     "reason": reason, "ok": good})
    return {"verdict": "PASS" if ok else "FAIL", "cases": rows,
            "naming": "Δ40 — must_flag(게이트가 막아야 함) / must_not_flag(통과해야 함)",
            "why": "대조군이 실패하면 sync 를 돌리지 않는다 — 닫힌 채 망가진 게이트의 "
                   "'전부 미완' 은 정상 출력과 구분되지 않는다"}


def sync() -> int:
    ctl = gate_controls()
    if ctl["verdict"] != "PASS":
        print("!! 완결 게이트 대조군 실패 — sync 를 돌리지 않는다")
        for c in ctl["cases"]:
            if not c["ok"]:
                print(f"   {c['case']}: passed={c['passed_gate']} expected={c['expected']}")
        return 3
    print(f"gate_controls={ctl['verdict']} ({len(ctl['cases'])}/{len(ctl['cases'])})")
    _eh = extraction_health()
    print(f"extraction_health: md보유 {_eh['with_md']} · 한계값 {_eh['limitation_value']} "
          f"({_eh['limitation_value_ratio']}) · NOT_STATED {_eh['limitation_not_stated']} "
          f"· verdict 정본 {_eh['verdict_json']}/fallback {_eh['verdict_fallback']}")
    if _eh["limitation_not_stated"]:
        print(f"   NOT_STATED: {_eh['not_stated_ids']} — 원문을 열어 표기를 확인하라")

    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    snap = RD / "INPUT_SNAPSHOT_v21.json"
    snap_sha = sha256(snap) if snap.exists() else "MISSING"
    head = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))

    # [A STEP1-040 R56] **재계산 키는 (입력 sha, 도구 sha) 쌍이다.**
    # 예전에는 `(rq, result_sha)` 만 봤다 — **도구를 고쳐도 입력이 같으면
    # 건너뛰어 도구 수정이 산출에 도달하지 않았다.** verdict 파서를 고쳤는데
    # 잘못된 18건이 그대로 남은 것이 그 결과다. R38(측정값에 입력 신원)의 뒷면.
    _tool_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    existing = {}
    exp = mlflow.get_experiment_by_name(EXPERIMENT)
    if exp:
        for r in mlflow.search_runs([exp.experiment_id], output_format="list"):
            existing[(r.data.tags.get("d.rq_id"),
                      r.data.tags.get("d.result_sha256"),
                      r.data.tags.get("d.tool_sha256"))] = r.info.run_id

    logged, skipped = [], []
    for item in discover():
        rq, md, js = item["rq_id"], item["md"], item["json"]
        payload = js if js and js.exists() else md
        if not payload.exists():
            continue
        # [D-DEF-07/10/10b 시정] 완결 게이트는 `gate()` 로 뺐다 — 안에 박혀
        # 있는 동안 대조군을 붙일 수 없었고, 그래서 없었다.
        nb_dir = RD.parent / "notebooks" / "d_research"
        ok, reason = gate(rq, md, js, nb_dir)
        if not ok:
            skipped.append(f"{rq}({reason})")
            continue
        rsha = sha256(payload)
        if (rq, rsha, _tool_sha) in existing:
            skipped.append(rq)
            continue
        metrics = {}
        if js and js.exists():
            # [A STEP1-037] 빈 metrics 로 삼키면 **지표 0개 run 이 영구히 남는다**
            # — D-DEF-07 의 형태다. 게이트가 이미 파싱을 요구했으므로 여기 도달하면
            # 게이트 이후 파일이 바뀐 것이고, 색인하지 않는다.
            try:
                metrics = flatten_numeric(json.loads(js.read_text(encoding="utf-8")))
            except Exception as _e:                      # noqa: BLE001
                skipped.append(f"{rq}(게이트 이후 JSON 파싱 실패: {type(_e).__name__})")
                continue
        _verdict, _vsrc = authoritative_verdict(js, md)
        nb_name = NOTEBOOK_MAP.get(rq)
        nb = (NB_DIR / nb_name) if nb_name and (NB_DIR / nb_name).exists() else None
        with mlflow.start_run(run_name=f"{rq}") as run:
            mlflow.set_tags({
                "d.rq_id": rq,
                "d.result_sha256": rsha,
                "d.plane": "D_INDEPENDENT_RESEARCH_SANDBOX",
                "d.authority": "NON_AUTHORITATIVE",
                "d.branch": BRANCH,
                "d.head_sha": head,
                "d.base_sha": BASE_SHA,
                "d.worktree_dirty": str(dirty),
                "d.input_snapshot_sha256": snap_sha,
                "d.verdict": _verdict,
                "d.verdict_source": _vsrc,
                "d.tool_sha256": _tool_sha,
                "d.production_modified": "false",
                "d.labels_produced": "false",
                "d.holdout_accessed": "false",
                "d.limitation": parse_limitation(md),
            })
            mlflow.log_params({
                "rq_id": rq,
                "base_sha": BASE_SHA[:12],
                "head_sha": head[:12],
                "input_snapshot_sha256": snap_sha[:16],
                "verdict": _verdict,
                "verdict_source": _vsrc,
                "notebook": nb.name if nb else "none",
            })
            if metrics:
                mlflow.log_metrics(metrics)
            for f in (md, js, snap):
                if f and f.exists():
                    mlflow.log_artifact(str(f), artifact_path="result")
            if nb:
                mlflow.log_artifact(str(nb), artifact_path="notebook")
            for tool in (RD / "tools").glob("*.py"):
                mlflow.log_artifact(str(tool), artifact_path="code")
            logged.append((rq, run.info.run_id, len(metrics)))

    for rq, rid, n in logged:
        print(f"logged  {rq}  run={rid}  metrics={n}")
    for rq in skipped:
        print(f"skipped {rq}  (동일 result sha 이미 기록됨)")
    print(f"\nMLflow UI: {TRACKING_URI}  experiment={EXPERIMENT}")
    return 0


def list_runs() -> int:
    mlflow.set_tracking_uri(TRACKING_URI)
    exp = mlflow.get_experiment_by_name(EXPERIMENT)
    if not exp:
        print("experiment 없음")
        return 1
    for r in mlflow.search_runs([exp.experiment_id], output_format="list"):
        t = r.data.tags
        print(f"{t.get('d.rq_id','?'):<8} {t.get('d.verdict','?'):<22} "
              f"metrics={len(r.data.metrics):<4} head={t.get('d.head_sha','')[:8]} run={r.info.run_id}")
    return 0


MLFLOW_STORE = Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/mlflow_d")


def manifest() -> int:
    """03 §9 — Git 밖 artifact 는 Git 안 manifest 로 노출한다.

    MLflow store 는 .gitignore 된 artifacts/ 아래에 있으므로, 여기서 파일 단위
    hash 목록을 만들어 D branch 에 commit 한다. "로컬에 있다"는 문장만으로
    인계하지 않는다.
    """
    mlflow.set_tracking_uri(TRACKING_URI)
    exp = mlflow.get_experiment_by_name(EXPERIMENT)
    runs = []
    if exp:
        for r in mlflow.search_runs([exp.experiment_id], output_format="list"):
            runs.append({
                "run_id": r.info.run_id,
                "rq_id": r.data.tags.get("d.rq_id"),
                "verdict": r.data.tags.get("d.verdict"),
                "head_sha": r.data.tags.get("d.head_sha"),
                "input_snapshot_sha256": r.data.tags.get("d.input_snapshot_sha256"),
                "result_sha256": r.data.tags.get("d.result_sha256"),
                "metric_count": len(r.data.metrics),
                "start_time": r.info.start_time,
            })
    files = [f for f in MLFLOW_STORE.rglob("*") if f.is_file()]
    doc = {
        "manifest_id": "D-MLFLOW-RETENTION-MANIFEST",
        "root_path": str(MLFLOW_STORE),
        "git_tracked": False,
        "read_only": False,
        "note": "MLflow 는 D 연구의 index 이지 권위가 아니다. canonical 산출은 Git 의 results/*.json 이다.",
        "tracking_uri": TRACKING_URI,
        "experiment": EXPERIMENT,
        "producer_sha": git("rev-parse", "HEAD"),
        "created_at_kst": subprocess.run(["date", "-Iseconds"], env={"TZ": "Asia/Seoul", "PATH": "/usr/bin:/bin"},
                                         capture_output=True, text=True).stdout.strip(),
        "artifact_count": len(files),
        "bytes": sum(f.stat().st_size for f in files),
        "runs": runs,
        "files": {str(f.relative_to(MLFLOW_STORE)): {"sha256": sha256(f), "bytes": f.stat().st_size}
                  for f in sorted(files) if f.stat().st_size < 50_000_000},
    }
    out = RD / "MLFLOW_RETENTION_MANIFEST.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"runs={len(runs)} files={len(files)} bytes={doc['bytes']:,}")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sync"
    raise SystemExit({"sync": sync, "list": list_runs, "manifest": manifest}.get(cmd, sync)())
