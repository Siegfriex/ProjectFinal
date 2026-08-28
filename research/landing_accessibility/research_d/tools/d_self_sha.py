"""산출이 **자기 자신의 sha** 를 기록하는가. [D-DEF-97]

`D-V3-FINDING-088` 에서 `PRESENTATION_EDA_PROVENANCE.json` 이 `outputs` 에 자기
자신을 넣어 둔 것을 찾았다 — **파일은 자기 sha 를 옳게 기록할 수 없다**(기록한
뒤 쓰면 값이 달라진다). 그때 한계로 "**다른 산출은 세지 않았다**" 고 적었다.

**값으로는 못 찾는다.** 기록된 sha 가 파일의 실제 sha 와 같은지 보는 방법은
**원리적으로 늘 0** 이다 — 자기참조라면 정의상 안 맞기 때문이다. 그 0 을
'없다' 로 읽으면 안심이 되지만 **아무것도 잰 것이 아니다**. 그래서 **키 이름**으로
찾는다: sha 값을 담은 키에 그 파일 자신의 이름이 들어 있는가.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

RD = Path(__file__).resolve().parents[1]
HEX = re.compile(r"^[0-9a-f]{64}$")


def _walk(o, path: str, fname: str, out: list, depth: int = 0) -> None:
    if depth > 8:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(k, str) and isinstance(v, str) and HEX.match(v) and fname in k:
                out.append({"key": k, "at": path})
            _walk(v, f"{path}.{k}", fname, out, depth + 1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:200]):
            _walk(v, f"{path}[{i}]", fname, out, depth + 1)


def scan(root: Path | None = None) -> dict:
    root = root or RD
    n_json = 0
    hits = []
    for p in sorted(root.rglob("*.json")):
        if ".git" in p.parts:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                           # noqa: BLE001
            continue
        n_json += 1
        found: list = []
        _walk(d, "$", p.name, found)
        if found:
            hits.append({"file": str(p.relative_to(root)),
                         "keys": [f["key"] for f in found][:3],
                         "recorded_can_never_match": True})
    return {"verdict": "INFO",           # **판정이 아니다** — 산출은 D 가 고치지 않는다
            "n_json": n_json,
            "n_self_referencing": len(hits), "self_referencing": hits,
            "**값으로는 못 찾는다**": (
                "기록된 sha 가 파일의 실제 sha 와 같은지 보는 방법은 **원리적으로 늘 0** 이다 "
                "— 자기참조라면 정의상 안 맞는다. 그 `0` 을 '없다' 로 읽으면 "
                "**아무것도 잰 것이 아니다**. 그래서 **키 이름**으로 찾는다"),
            "남는_사각": ("키에 파일 이름이 안 들어가고 자기를 가리키는 경우"
                     "(예: `self_sha256` 같은 이름)는 **이름으로도 값으로도 못 본다**"),
            "D_는_고치지_않는다": ("산출기가 자기 sha 를 적는 것은 **재생성**으로만 고쳐진다 — "
                          "분석 산출을 건드리는 일이라 A 지정 없이 하지 않는다(00 §13)")}


def controls() -> dict:
    import tempfile
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        h = "a" * 64
        # 자기 이름을 키로 가진 산출 — **잡혀야 한다**
        (t / "SELF.json").write_text(json.dumps({"outputs": {"SELF.json": h}}), encoding="utf-8")
        # 남의 이름만 가진 산출 — 잡히면 안 된다
        (t / "OTHER.json").write_text(json.dumps({"outputs": {"FIG.png": h}}), encoding="utf-8")
        # sha 가 아닌 값 — 잡히면 안 된다
        (t / "NOTSHA.json").write_text(json.dumps({"outputs": {"NOTSHA.json": "abc"}}),
                                       encoding="utf-8")
        r = scan(t)
        files = {x["file"] for x in r["self_referencing"]}
        case("자기 이름을 키로 가진 산출은 잡힌다", "SELF.json" in files, True, negative=True)
        case("남의 이름만 있으면 안 잡힌다", "OTHER.json" in files, False)
        case("64자 hex 가 아니면 안 잡힌다", "NOTSHA.json" in files, False)
        case("세 파일을 다 읽었다 — 0 이면 검사가 무효다", r["n_json"], 3)

    # **값 기준 방법이 왜 무효인지**를 대조군으로 굳힌다
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        f = t / "X.json"
        f.write_text(json.dumps({"self": "b" * 64}), encoding="utf-8")
        own = hashlib.sha256(f.read_bytes()).hexdigest()
        case("기록한 sha 가 자기 실제 sha 와 같을 수 없다 — 값 기준은 늘 0",
             own == "b" * 64, False)

    live = scan()
    case("현재 산출에서 자기참조는 1건(알려진 것)", live["n_self_referencing"], 1)
    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    c = controls()
    print(json.dumps({"scan": scan(), "controls": c}, ensure_ascii=False, indent=1))
    raise SystemExit(0 if c["verdict"] == "PASS" else 3)
