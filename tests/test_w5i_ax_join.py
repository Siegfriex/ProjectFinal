"""W5I — DOM 후보(selector) <-> CDP AX slim node 조인 회귀.

**이 파일의 PASS/FAIL 은 offline fixture 위의 engine test 결과다.** 실제 서비스에 대한
research finding 이 아니며 그렇게 인용할 수 없다.

검증하는 것은 셋이다.

1. **조인이 실제로 이어지는가** — 그리고 못 이을 때 값을 지어내지 않는가.
   대조군이 없으면 "이어졌다" 와 "빈 결과가 통과했다" 가 같은 출력으로 나온다. 그래서
   모든 성공 케이스에 **구조가 같고 AX 노드만 없는 짝**을 붙였다.
2. **`ICON_ONLY_AX_NAMED` <-> `ICON_ONLY_UNNAMED` 를 실제로 가르는가** — W5E 의
   icon_only 짝(태그 시퀀스 완전 일치, `aria-label` 유무만 다름)으로 본다. 두 fixture 의
   판정 차이는 accessible name computation 에서만 나올 수 있으므로, 갈린다면 그것은
   조인이 실제로 AX 를 읽었다는 뜻이다.
3. **가산성** — 조인이 꺼진 수집기는 base 와 같은 것을 내고, 켠 수집기는 artifact 를
   **하나만 더 낸다**. 기존 슬롯도 `L0Observation` 필드도 바뀌지 않는다.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.l0_collector import L0Observation  # noqa: E402
from landing_accessibility.v3_runner.ax_join import (  # noqa: E402
    AX_JOIN_RELPATH,
    AX_JOIN_VERSION,
    CAPTURE_STACK_ABSENT,
    CAPTURE_STACK_COMPLETE,
    CAPTURE_STACK_COMPLETENESS_NOTE_PREFIX,
    CAPTURE_STACK_LAYERS,
    CAPTURE_STACK_MEMBERS,
    CAPTURE_STACK_METHOD,
    CAPTURE_STACK_METHOD_NOTE_PREFIX,
    CAPTURE_STACK_NONE,
    CAPTURE_STACK_NOTE_PREFIX,
    CAPTURE_STACK_PARTIAL,
    CAPTURE_STACK_UNREADABLE,
    COLLECTOR_SHA256_METHOD,
    COLLECTOR_SHA256_METHOD_NOTE_PREFIX,
    COLLECTOR_SHA256_NOTE_PREFIX,
    COLLECTOR_SOURCE_FILES,
    DEFAULT_SELECTOR_FEATURES,
    AxJoinPayload,
    JoinStatus,
    Note,
    SelectorResolution,
    ax_join_relpath_for,
    build_ax_join_payload,
    capture_stack,
    capture_stack_notes,
    collect_ax_join,
    collector_provenance,
    collector_provenance_notes,
    collector_sha256,
    index_ax_nodes,
    join_resolutions,
    probe_selectors,
    resolve_selectors,
    selector_ax_index,
    task_control_ax_field,
)

FIXTURES = RESEARCH / "fixtures"
V3_FIXTURES = FIXTURES / "v3"


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────
def _ax(bid: int, *, name: Any = "이름", computed: bool = True, **kw: Any) -> dict[str, Any]:
    """CDP slim node 모양 그대로 (`l0_collector.L0Collector._ax_tree` 산출)."""
    node = {
        "nodeId": str(bid),
        "backendDOMNodeId": bid,
        "role": kw.pop("role", "button"),
        "name": name,
        "name_computed": computed,
        "ignored": kw.pop("ignored", False),
        "properties": kw.pop("properties", []),
    }
    node.update(kw)
    return node


def _res(sel: str, bid: int | None, count: int | None = 1, **kw: Any) -> SelectorResolution:
    return SelectorResolution(selector=sel, backend_dom_node_id=bid, match_count=count, **kw)


# ── 1. selector 수집 (순수) ──────────────────────────────────────────────────
def test_probe_selectors_reads_the_three_features_w5c_actually_looks_at() -> None:
    """조인 대상이 W5C `_merge_control` 이 보는 곳보다 좁으면 W5C 가 쓸 수 없다."""
    assert DEFAULT_SELECTOR_FEATURES == (
        "primary_action_candidates",
        "accessible_name_sources",
        "utility_input_widgets",
    )
    probe = {
        "raw_features": {
            "primary_action_candidates": [{"selector": "button#a"}, {"selector": "a#b"}],
            "accessible_name_sources": [{"selector": "a#b"}, {"selector": "img#c"}],
            "utility_input_widgets": [{"selector": "input#d"}],
            "modal_overlay_candidates": [{"selector": "div#ignored"}],
        }
    }
    assert probe_selectors(probe) == ["button#a", "a#b", "img#c", "input#d"]


def test_probe_selectors_accepts_either_shape_and_extra_selectors() -> None:
    raw = {"primary_action_candidates": [{"selector": "button#a"}]}
    assert probe_selectors({"raw_features": raw}) == probe_selectors(raw) == ["button#a"]
    assert probe_selectors(raw, extra_selectors=["button#a", "div#task"]) == [
        "button#a",
        "div#task",
    ]


def test_probe_selectors_survives_malformed_rows() -> None:
    raw = {
        "primary_action_candidates": [
            {"selector": None},
            "nope",
            {"no_selector": 1},
            {"selector": ""},
        ],
        "accessible_name_sources": "not-a-list",
    }
    assert probe_selectors(raw) == []


# ── 2. AX 색인 (순수) ────────────────────────────────────────────────────────
def test_index_ax_nodes_keys_on_backend_dom_node_id_first_wins() -> None:
    """AX tree 는 문서 순서다. 뒤엣것으로 덮으면 조용히 이름이 바뀐다."""
    idx = index_ax_nodes([_ax(7, name="첫번째"), _ax(7, name="두번째"), _ax(9)])
    assert set(idx) == {7, 9}
    assert idx[7]["name"] == "첫번째"


def test_index_ax_nodes_rejects_non_integer_and_boolean_ids() -> None:
    """`True` 는 파이썬에서 `int` 다. 걸러내지 않으면 backend id 1 로 색인된다."""
    idx = index_ax_nodes(
        [
            {"backendDOMNodeId": None, "name": "x"},
            {"backendDOMNodeId": True, "name": "y"},
            {"backendDOMNodeId": "3", "name": "z"},
            _ax(3, name="ok"),
        ]
    )
    assert idx == {3: idx[3]} and idx[3]["name"] == "ok"


# ── 3. 조인 본체 + 대조군 (순수) ─────────────────────────────────────────────
def test_join_succeeds_and_the_structurally_identical_control_yields_none() -> None:
    """**핵심 대조군.** 두 resolution 은 완전히 같은 모양이다. 다른 것은 AX 색인이
    그 backend id 를 갖고 있느냐 하나뿐이다. 하나는 이름이 나오고 하나는 `None` 이다."""
    ax_index = index_ax_nodes([_ax(100, name="운행정보 조회")])

    joined, control = join_resolutions(
        [_res("button#entry", 100), _res("button#entry-control", 200)],
        ax_index,
        full_ax_backend_ids=[100],
    )

    assert joined.join_status == JoinStatus.JOINED
    assert joined.ax_node is not None and joined.ax_node["name"] == "운행정보 조회"
    assert Note.AX_NODE_ABSENT not in joined.notes

    assert control.join_status == JoinStatus.AX_NODE_ABSENT
    assert control.ax_node is None
    assert Note.AX_NODE_ABSENT in control.notes
    assert Note.NOT_IN_AX_TREE in control.notes


def test_join_failure_never_becomes_a_value() -> None:
    """DOM 속성이 아무리 이름처럼 생겼어도 조인 실패는 `None` 이다 (00 §8 분리)."""
    entry = join_resolutions([_res("button#x", 1)], {}, full_ax_backend_ids=[])[0]
    payload = entry.as_dict()
    assert payload["ax_node"] is None
    # 산출물 어디에도 이름 비슷한 값이 스며들지 않았다.
    assert "name" not in json.dumps(payload)


def test_dom_side_failure_is_told_apart_from_ax_side_failure() -> None:
    """selector 가 문서에 없는 것과 AX 에 노드가 없는 것은 다른 사건이다."""
    no_dom, no_ax = join_resolutions(
        [_res("button#gone", None, count=0), _res("button#here", 5)],
        {},
        full_ax_backend_ids=[],
    )
    assert no_dom.join_status == JoinStatus.DOM_NODE_UNRESOLVED
    assert Note.DOM_NO_MATCH in no_dom.notes and Note.AX_NODE_ABSENT in no_dom.notes
    assert no_ax.join_status == JoinStatus.AX_NODE_ABSENT
    assert Note.DOM_NO_MATCH not in no_ax.notes


def test_backend_id_unresolved_is_not_reported_as_no_match() -> None:
    entry = join_resolutions([_res("button#x", None, count=1)], {})[0]
    assert Note.BACKEND_ID_UNRESOLVED in entry.notes
    assert Note.DOM_NO_MATCH not in entry.notes


def test_absence_reason_is_left_unclassified_when_not_compared() -> None:
    """full AX tree 와 대조하지 않았으면 부재 사유를 안다고 적지 않는다."""
    entry = join_resolutions([_res("button#x", 1)], {})[0]
    assert Note.ABSENCE_UNCLASSIFIED in entry.notes
    assert Note.NOT_IN_AX_TREE not in entry.notes
    assert Note.FILTERED_FROM_AX_JSON not in entry.notes


def test_filtered_from_ax_json_is_told_apart_from_not_in_ax_tree() -> None:
    """slim 필터(role none/InlineTextBox)에 걸려 빠진 것과 AX 에 아예 없는 것은 다르다."""
    filtered, absent = join_resolutions(
        [_res("span#pres", 11), _res("img#deco", 12)],
        {},
        full_ax_backend_ids=[11],
    )
    assert Note.FILTERED_FROM_AX_JSON in filtered.notes
    assert Note.NOT_IN_AX_TREE in absent.notes
    assert filtered.ax_node is absent.ax_node is None


def test_ambiguous_selector_is_flagged_not_silently_resolved() -> None:
    """probe `sel()` 은 8단계에서 잘린다 — 재해소가 여러 개를 맞출 수 있다."""
    amb, single = join_resolutions(
        [_res("main>button", 1, count=3), _res("button#u", 2, count=1)],
        index_ax_nodes([_ax(1), _ax(2)]),
    )
    assert Note.SELECTOR_AMBIGUOUS in amb.notes and amb.match_count == 3
    assert Note.SELECTOR_AMBIGUOUS not in single.notes


def test_two_selectors_landing_on_one_backend_id_are_flagged() -> None:
    a, b = join_resolutions([_res("x", 9), _res("y", 9)], index_ax_nodes([_ax(9)]))
    assert Note.BACKEND_ID_COLLISION in a.notes and Note.BACKEND_ID_COLLISION in b.notes


def test_ignored_ax_node_is_joined_but_marked() -> None:
    """`ignored` 노드는 있는 것이다. 버리면 W5C 가 divergence 를 볼 수 없다 (Δ15)."""
    entry = join_resolutions([_res("x", 3)], index_ax_nodes([_ax(3, ignored=True)]))[0]
    assert entry.join_status == JoinStatus.JOINED
    assert entry.ax_node is not None
    assert Note.AX_NODE_IGNORED in entry.notes


def test_invalid_selector_is_recorded_as_invalid_not_as_zero_matches() -> None:
    entry = join_resolutions([_res("a[[bad", None, count=None, selector_invalid=True)], {})[0]
    assert Note.SELECTOR_INVALID in entry.notes
    assert entry.match_count is None
    assert Note.DOM_NO_MATCH not in entry.notes


# ── 4. 집계 ──────────────────────────────────────────────────────────────────
def test_join_rate_of_an_empty_target_set_is_null_not_zero() -> None:
    """대상이 0개면 성공률은 정의되지 않는다. 0.0 으로 쓰면 '전부 실패' 로 읽힌다."""
    stats = build_ax_join_payload([], []).stats
    assert stats["selectors_total"] == 0
    assert stats["join_rate"] is None
    assert stats["ax_name_computed_rate"] is None


def test_name_computed_and_name_nonempty_are_counted_separately() -> None:
    """빈 이름도 계산 결과다. 합치면 ICON_ONLY 두 값을 가르는 정보가 사라진다."""
    stats = build_ax_join_payload(
        [_res("a", 1), _res("b", 2), _res("c", 3)],
        [_ax(1, name="검색"), _ax(2, name=""), _ax(3, name=None, computed=False)],
    ).stats
    assert stats == {
        "selectors_total": 3,
        "joined": 3,
        "join_rate": 1.0,
        "joined_with_ax_name_computed": 2,
        "joined_with_nonempty_ax_name": 1,
        "ax_name_computed_rate": round(2 / 3, 6),
        "nonempty_ax_name_rate": round(1 / 3, 6),
        "by_status": {"JOINED": 3, "AX_NODE_ABSENT": 0, "DOM_NODE_UNRESOLVED": 0},
    }


# ── 5. 하류(W5C) 계약 ────────────────────────────────────────────────────────
def test_failed_selectors_stay_as_keys_with_none() -> None:
    """W5C 는 `"ax_node" in task_control` 로 '안 알려줬다' 와 'AX 에 없다' 를 가른다."""
    payload = build_ax_join_payload([_res("a", 1), _res("b", 2)], [_ax(1)])
    index = selector_ax_index(payload)
    assert set(index) == {"a", "b"}
    assert index["a"] is not None and index["b"] is None


def test_selector_ax_index_reads_the_serialized_payload_too() -> None:
    payload = build_ax_join_payload([_res("a", 1), _res("b", 2)], [_ax(1)])
    round_tripped = json.loads(json.dumps(payload.as_dict(), ensure_ascii=False))
    assert selector_ax_index(round_tripped) == selector_ax_index(payload)


def test_a_selector_we_never_tried_gets_no_ax_node_key_at_all() -> None:
    """시도조차 안 한 것에 `{"ax_node": None}` 을 주면 '찾아봤는데 없다' 로 읽힌다."""
    payload = build_ax_join_payload([_res("a", 1)], [_ax(1)])
    assert task_control_ax_field(payload, "a") == {"ax_node": payload.entries[0].ax_node}
    assert task_control_ax_field(payload, "b") == {}
    assert task_control_ax_field(build_ax_join_payload([_res("b", 9)], []), "b") == {
        "ax_node": None
    }


# ── 6. collector_sha256 (조건 3) ─────────────────────────────────────────────
def test_collector_sha256_covers_the_collector_and_the_joiner() -> None:
    digests = collector_sha256()
    assert set(digests) == {*COLLECTOR_SOURCE_FILES, "combined"}
    assert COLLECTOR_SOURCE_FILES == (
        "engine/l0_probe.js",
        "engine/l0_collector.py",
        "v3_runner/ax_join.py",
    )
    pkg = RESEARCH / "src" / "landing_accessibility"
    for rel in COLLECTOR_SOURCE_FILES:
        assert digests[rel] == hashlib.sha256((pkg / rel).read_bytes()).hexdigest()


def test_collector_sha256_changes_when_any_collector_file_changes(tmp_path: Path) -> None:
    """legacy 59 / 12 diagnostic 을 낸 수집기와 v3 수집기의 경계가 데이터에 남아야 한다."""
    for rel in COLLECTOR_SOURCE_FILES:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(b"v1")
    before = collector_sha256(tmp_path)
    (tmp_path / COLLECTOR_SOURCE_FILES[0]).write_bytes(b"v2")
    after = collector_sha256(tmp_path)
    assert before["combined"] != after["combined"]
    assert before[COLLECTOR_SOURCE_FILES[1]] == after[COLLECTOR_SOURCE_FILES[1]]


def test_unreadable_collector_file_is_marked_not_silently_skipped(tmp_path: Path) -> None:
    digests = collector_sha256(tmp_path)
    assert all(digests[rel] == "UNREADABLE" for rel in COLLECTOR_SOURCE_FILES)


def test_payload_carries_the_fingerprint_and_survives_json(tmp_path: Path) -> None:
    payload = build_ax_join_payload([_res("a", 1)], [_ax(1)])
    blob = json.loads(json.dumps(payload.as_dict(), ensure_ascii=False))
    assert blob["ax_join_version"] == AX_JOIN_VERSION
    assert blob["collector_sha256"]["combined"]
    assert blob["full_ax_compared"] is False
    assert blob["entries"][0]["ax_node"]["backendDOMNodeId"] == 1


# ── 7. CDP 해소 (fake CDP — 브라우저 없이) ──────────────────────────────────
class _FakeCDP:
    """`Runtime.evaluate` / `getProperties` / `DOM.describeNode` 만 흉내낸다."""

    def __init__(self, *, counts: list[int], backends: dict[int, int | None]) -> None:
        self.counts = counts
        self.backends = backends
        self.calls: list[str] = []
        self.released: list[str] = []

    def send(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append(method)
        params = params or {}
        if method in ("DOM.enable", "DOM.getDocument", "Accessibility.enable"):
            return {}
        if method == "Runtime.evaluate":
            if "querySelectorAll(s).length" in params["expression"]:
                return {"result": {"value": list(self.counts)}}
            return {"result": {"objectId": "arr-1"}}
        if method == "Runtime.getProperties":
            out = [{"name": "length", "value": {"value": len(self.counts)}}]
            for i in range(len(self.counts)):
                if self.backends.get(i) is None:
                    out.append({"name": str(i), "value": {"type": "object", "subtype": "null"}})
                else:
                    out.append({"name": str(i), "value": {"objectId": f"obj-{i}"}})
            return {"result": out}
        if method == "DOM.describeNode":
            idx = int(str(params["objectId"]).split("-")[1])
            return {"node": {"backendNodeId": self.backends[idx]}}
        if method == "Runtime.releaseObject":
            self.released.append(params["objectId"])
            return {}
        raise AssertionError(f"예상치 못한 CDP 호출: {method}")


def test_resolve_selectors_maps_each_selector_to_its_backend_id() -> None:
    cdp = _FakeCDP(counts=[1, 0, 2, -1], backends={0: 41, 1: None, 2: 42, 3: None})
    got = resolve_selectors(cdp, ["a", "b", "c", "d[["])
    assert [r.backend_dom_node_id for r in got] == [41, None, 42, None]
    assert [r.match_count for r in got] == [1, 0, 2, None]
    assert [r.selector_invalid for r in got] == [False, False, False, True]
    assert cdp.released == ["arr-1"]


def test_resolve_selectors_sends_one_describe_per_resolved_element() -> None:
    """selector 수만큼 왕복이 늘어나지, selector 수의 제곱으로 늘어나지 않는다."""
    cdp = _FakeCDP(counts=[1, 1, 0], backends={0: 1, 1: 2, 2: None})
    resolve_selectors(cdp, ["a", "b", "c"])
    assert cdp.calls.count("Runtime.evaluate") == 2
    assert cdp.calls.count("DOM.describeNode") == 2


def test_resolve_selectors_on_empty_input_touches_the_browser_zero_times() -> None:
    cdp = _FakeCDP(counts=[], backends={})
    assert resolve_selectors(cdp, []) == []
    assert cdp.calls == []


def test_collect_ax_join_wires_probe_selectors_to_the_stored_slim_nodes() -> None:
    cdp = _FakeCDP(counts=[1, 1], backends={0: 41, 1: 77})
    payload = collect_ax_join(
        cdp,
        probe={
            "raw_features": {"primary_action_candidates": [{"selector": "a"}, {"selector": "b"}]}
        },
        ax_nodes=[_ax(41, name="예매")],
        classify_absence=False,
    )
    assert isinstance(payload, AxJoinPayload)
    assert payload.stats["joined"] == 1
    assert payload.stats["join_rate"] == 0.5
    assert payload.full_ax_compared is False
    assert selector_ax_index(payload) == {"a": payload.entries[0].ax_node, "b": None}


# ── 8. 브라우저 위에서 — 실측 ────────────────────────────────────────────────
pytest.importorskip("playwright.sync_api")

from landing_accessibility.engine.evidence import EvidenceRun  # noqa: E402
from landing_accessibility.engine.firewall import ExecutionMode  # noqa: E402
from landing_accessibility.engine.l0_collector import FixtureTarget, L0Collector  # noqa: E402
from landing_accessibility.engine.vocabulary import InteractionArchetype as A  # noqa: E402

#: W5E `8496c700` 의 icon_only 짝을 그대로 쓴다. 아직 병합되지 않은 lane 이면 같은 성질
#: (태그 시퀀스 완전 일치, `aria-label` 유무만 다름)을 갖는 짝을 tmp 에 만들어 쓰고,
#: 어느 경로든 그 성질 자체를 아래 테스트가 기계로 다시 확인한다.
_ICON_ONLY_TEMPLATE = """<!doctype html>
<!--
FIXTURE: {name}    W5I 대조짝 (W5E icon_only 짝과 같은 성질)
검증 대상: aria-label 유무만 다른 짝. 태그 시퀀스가 완전히 같으므로 판정 차이는
accessible name computation 에서만 나올 수 있다.
-->
<html lang="ko"><head><meta charset="utf-8">
<title>{name}</title>
<style>
 body{{margin:0;width:390px;height:844px;background:#fff;color:#111}}
 .task{{position:fixed;left:318px;top:72px;width:48px;height:48px;padding:0;line-height:0}}
 .ico{{display:inline-block;width:20px;height:20px;border:2px solid currentColor;border-radius:50%}}
</style></head>
<body data-fixture="{name}">
<h1 class="hdr">시외버스 예매</h1>
<main class="page">
<p class="note">우측 상단 진입 control 은 아이콘만 보인다.</p>
<button type="button" class="task" id="entry"{label}><span class="ico" aria-hidden="true"></span></button>
</main>
</body></html>
"""


@pytest.fixture(scope="module")
def icon_only_pair(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    named = V3_FIXTURES / "icon_only_ax_named.html"
    unnamed = V3_FIXTURES / "icon_only_unnamed.html"
    if named.is_file() and unnamed.is_file():
        return {"root": V3_FIXTURES, "named": named, "unnamed": unnamed}
    root = tmp_path_factory.mktemp("w5i-icon-only")
    (root / "icon_only_ax_named.html").write_text(
        _ICON_ONLY_TEMPLATE.format(name="icon_only_ax_named", label=' aria-label="운행정보 조회"'),
        encoding="utf-8",
    )
    (root / "icon_only_unnamed.html").write_text(
        _ICON_ONLY_TEMPLATE.format(name="icon_only_unnamed", label=""),
        encoding="utf-8",
    )
    return {
        "root": root,
        "named": root / "icon_only_ax_named.html",
        "unnamed": root / "icon_only_unnamed.html",
    }


def _tag_sequence(html: str) -> list[str]:
    body = html.split("<body", 1)[-1]
    return re.findall(r"<\s*([a-zA-Z][a-zA-Z0-9-]*)", body)


def test_the_icon_only_pair_differs_only_by_the_aria_label(
    icon_only_pair: dict[str, Path],
) -> None:
    """짝의 성질을 먼저 확인한다. 성질이 무너지면 아래 판정 차이는 근거가 못 된다."""
    named = icon_only_pair["named"].read_text(encoding="utf-8")
    unnamed = icon_only_pair["unnamed"].read_text(encoding="utf-8")
    assert _tag_sequence(named) == _tag_sequence(unnamed)
    assert 'aria-label="운행정보 조회"' in named
    assert "aria-label" not in unnamed.split("<button", 1)[1].split(">", 1)[0]


def _collect(root: Path, fixtures: list[str], *, ax_join: bool, tmp: Path) -> dict[str, Any]:
    run = EvidenceRun.create(tmp, "w5i-l0", execution_mode=ExecutionMode.FIXTURE)
    collector = L0Collector(run, fixture_root=root, ax_join=ax_join)
    obs = {
        name: collector.collect(
            FixtureTarget(web_target_id=f"wt-{name}", fixture=name, archetype=A.UTILITY_ENTRY)
        )
        for name in fixtures
    }
    return {"run": run, "obs": obs}


@pytest.fixture(scope="module")
def joined_pair(
    icon_only_pair: dict[str, Path], tmp_path_factory: pytest.TempPathFactory
) -> dict[str, Any]:
    out = _collect(
        icon_only_pair["root"],
        ["icon_only_ax_named.html", "icon_only_unnamed.html"],
        ax_join=True,
        tmp=tmp_path_factory.mktemp("w5i-evidence"),
    )
    payloads = {}
    for name, obs in out["obs"].items():
        assert obs.measurement_status == "MEASURED", f"{name}: {obs.notes}"
        path = out["run"].run_dir / ax_join_relpath_for(obs.observation_id)
        payloads[name] = json.loads(path.read_text(encoding="utf-8"))
    out["payloads"] = payloads
    return out


def test_the_join_actually_reaches_the_ax_tree_on_a_real_page(
    joined_pair: dict[str, Any],
) -> None:
    for name, payload in joined_pair["payloads"].items():
        index = {e["selector"]: e for e in payload["entries"]}
        entry = index["button#entry"]
        assert entry["join_status"] == JoinStatus.JOINED, f"{name}: {entry['notes']}"
        assert isinstance(entry["backend_dom_node_id"], int)
        assert entry["ax_node"]["role"] == "button"
        assert payload["full_ax_compared"] is True


def test_icon_only_ax_named_and_icon_only_unnamed_are_actually_told_apart(
    joined_pair: dict[str, Any],
) -> None:
    """이 lane 이 없으면 두 fixture 는 **구분 불가능**했다 — 축이 없었다.

    태그 시퀀스가 완전히 같으므로, 아래 차이는 브라우저 naming computation 을 실제로
    읽었을 때에만 나온다. 최종 `entry_label_modality` 판정은 W5C 소유이므로 여기서
    재구현하지 않고, W5C 가 그 판정을 내리는 **입력이 갈리는가**만 본다.
    """
    named = {
        e["selector"]: e for e in joined_pair["payloads"]["icon_only_ax_named.html"]["entries"]
    }
    unnamed = {
        e["selector"]: e for e in joined_pair["payloads"]["icon_only_unnamed.html"]["entries"]
    }
    a, b = named["button#entry"]["ax_node"], unnamed["button#entry"]["ax_node"]

    assert a["name"] == "운행정보 조회"
    # 이름이 계산은 됐고 결과가 비어 있다. `name_computed=False`(계산 안 됨)와 다른 상태다.
    assert b["name_computed"] is True and (b["name"] or "").strip() == ""

    # W5C `_accessible_name_from_ax` 의 계약 그대로: 비어 있으면 `None` 이다.
    assert bool((a["name"] or "").strip()) is True
    assert bool((b["name"] or "").strip()) is False


def test_w5c_splits_the_pair_when_it_is_available(joined_pair: dict[str, Any]) -> None:
    """W5C `surface.py` 가 병합돼 있으면 끝까지 통과시켜 본다 (없으면 skip)."""
    surface = pytest.importorskip("landing_accessibility.v3_runner.surface")
    got = {}
    for name, payload in joined_pair["payloads"].items():
        obs = joined_pair["obs"][name]
        node = selector_ax_index(payload)["button#entry"]
        measurement = surface.measure_surface(
            task_control={"selector": "button#entry", "ax_node": node},
            probe_state=obs.raw_features,
            viewport=(obs.viewport_width, obs.viewport_height),
        )
        got[name] = measurement.entry_label_modality
    assert got["icon_only_ax_named.html"] == "ICON_ONLY_AX_NAMED"
    assert got["icon_only_unnamed.html"] == "ICON_ONLY_UNNAMED"


@pytest.fixture(scope="module")
def legacy_join(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """AX 노드가 **정말로 없는** DOM 후보를 담은 기존 fixture 로 대조군을 만든다."""
    return _collect(
        FIXTURES,
        ["missing_accessible_name.html"],
        ax_join=True,
        tmp=tmp_path_factory.mktemp("w5i-legacy"),
    )


def test_a_decorative_image_has_no_ax_node_and_the_join_says_so(
    legacy_join: dict[str, Any],
) -> None:
    """`alt=""` img 는 Chrome AX tree 에 노드가 없다 — **실측된 자연 대조군**이다.

    같은 fixture 안의 형제 control 들은 전부 이어졌다. 구조도 probe 취급도 같은데 한
    노드만 `None` 이 나온다면, 그 `None` 은 조인기의 침묵이 아니라 AX 의 부재다.
    """
    obs = legacy_join["obs"]["missing_accessible_name.html"]
    payload = json.loads(
        (legacy_join["run"].run_dir / ax_join_relpath_for(obs.observation_id)).read_text(
            encoding="utf-8"
        )
    )
    entries = {e["selector"]: e for e in payload["entries"]}

    deco = entries["a#icon-c>img"]
    assert deco["join_status"] == JoinStatus.AX_NODE_ABSENT
    assert deco["ax_node"] is None
    assert Note.AX_NODE_ABSENT in deco["notes"]
    assert Note.NOT_IN_AX_TREE in deco["notes"]
    # DOM 쪽은 멀쩡히 찾았다. 즉 실패 지점이 AX 라는 것까지 데이터가 말한다.
    assert deco["backend_dom_node_id"] is not None and deco["match_count"] == 1

    assert entries["a#icon-c"]["join_status"] == JoinStatus.JOINED
    assert entries["button#named-a"]["ax_node"]["name"] == "검색"
    # `aria-label` 없는 아이콘 버튼은 이어지되 이름이 비어 있다 (부재가 아니라 빈 이름).
    assert entries["button#icon-a"]["ax_node"]["name"] == ""

    assert payload["stats"]["selectors_total"] == 6
    assert payload["stats"]["joined"] == 5
    assert payload["stats"]["joined_with_nonempty_ax_name"] == 2


# ── 9. 가산성 ────────────────────────────────────────────────────────────────
def test_l0_observation_gained_no_field(joined_pair: dict[str, Any]) -> None:
    """`L0Observation.as_dict()` 는 `e001_runner/executor.py` 가 그대로 직렬화해 ledger
    해시에 넣는다. 필드를 하나라도 더하면 기존 산출물의 바이트가 바뀐다."""
    names = [f.name for f in fields(L0Observation)]
    assert "ax_join_path" not in names and "ax_join" not in names
    assert names[-4:] == ["interrupts", "primary_action_candidates", "raw_features", "notes"]
    assert set(joined_pair["obs"]["icon_only_unnamed.html"].as_dict()) == set(names)


def test_the_joiner_is_off_by_default() -> None:
    """켜지 않은 수집기는 base 수집기다. 이것이 가산성 주장의 근거다."""
    import inspect

    sig = inspect.signature(L0Collector.__init__)
    assert sig.parameters["ax_join"].default is False


def test_turning_the_joiner_on_adds_exactly_one_artifact_and_changes_nothing_else(
    icon_only_pair: dict[str, Path], tmp_path: Path
) -> None:
    """**대조군 있는 가산성 증명.** 같은 fixture 를 끄고 한 번, 켜고 한 번 수집해
    산출물 집합과 각 산출물의 바이트를 대조한다.

    `probe.json` 만 원본 비교에서 제외한다 — `l0_probe.js` 가 `collected_at` 타임스탬프를
    싣기 때문이고, 그 키를 뺀 나머지는 바이트 동일함을 함께 확인한다.
    """

    def snapshot(flag: bool, tag: str) -> tuple[dict[str, str], dict[str, Any]]:
        out = _collect(
            icon_only_pair["root"],
            ["icon_only_ax_named.html"],
            ax_join=flag,
            tmp=tmp_path / tag,
        )
        run = out["run"]
        obs = out["obs"]["icon_only_ax_named.html"]
        assert obs.measurement_status == "MEASURED", obs.notes
        digests = {
            str(p.relative_to(run.run_dir / obs.observation_id)): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in sorted((run.run_dir / obs.observation_id).rglob("*"))
            if p.is_file()
        }
        probe = json.loads((run.run_dir / obs.probe_path).read_text(encoding="utf-8"))
        probe.pop("collected_at", None)
        digests["probe.json::without_collected_at"] = hashlib.sha256(
            json.dumps(probe, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return digests, obs.as_dict()

    off, off_obs = snapshot(False, "off")
    on, on_obs = snapshot(True, "on")

    assert set(on) - set(off) == {AX_JOIN_RELPATH}
    assert set(off) - set(on) == set()
    changed = {k for k in set(off) & set(on) if off[k] != on[k]}
    # 타임스탬프를 실은 probe.json 원본 외에는 한 바이트도 다르지 않다.
    assert changed == {"l0a/probe.json"}
    assert off["probe.json::without_collected_at"] == on["probe.json::without_collected_at"]
    assert set(off_obs) == set(on_obs)


def test_joining_never_downgrades_the_measurement(joined_pair: dict[str, Any]) -> None:
    for name, obs in joined_pair["obs"].items():
        assert obs.measurement_status == "MEASURED", f"{name}: {obs.notes}"
        assert not [n for n in obs.notes if n.startswith("AX_JOIN_FAILED")]


def test_the_run_still_verifies_with_the_extra_artifact(
    icon_only_pair: dict[str, Path], tmp_path: Path
) -> None:
    out = _collect(icon_only_pair["root"], ["icon_only_unnamed.html"], ax_join=True, tmp=tmp_path)
    out["run"].seal()
    assert out["run"].verify()["status"] == "VERIFIED"


def test_the_relpath_contract_is_what_the_collector_actually_writes(
    joined_pair: dict[str, Any],
) -> None:
    """`L0Observation` 에 경로 필드를 더하지 않았으므로 경로 규약이 유일한 접점이다."""
    obs = joined_pair["obs"]["icon_only_unnamed.html"]
    expected = joined_pair["run"].run_dir / f"{obs.observation_id}/{AX_JOIN_RELPATH}"
    assert expected.is_file()
    assert ax_join_relpath_for(obs.observation_id) == f"{obs.observation_id}/{AX_JOIN_RELPATH}"


# ── 10. reveal-gated control — 측정으로 확인한 경계 ──────────────────────────
_REVEAL_TEMPLATE = """<!doctype html>
<!--
FIXTURE: {name}    W5I 대조짝 (reveal gating)
검증 대상: 조상의 `hidden` 속성 하나만 다른 짝. task control 자체는 완전히 같다.
-->
<html lang="ko"><head><meta charset="utf-8"><title>{name}</title>
<style>[hidden]{{display:none !important}} body{{margin:0;width:390px;height:844px}}</style>
</head>
<body data-fixture="{name}">
<h1 class="hdr">시외버스 예매</h1>
<button type="button" id="open" aria-expanded="false">전체메뉴</button>
<nav id="panel"{hidden} aria-label="전체메뉴">
<button type="button" id="entry">운행정보 조회</button>
</nav>
</body></html>
"""


def test_a_reveal_gated_control_has_no_ax_node_until_it_is_revealed(tmp_path: Path) -> None:
    """**측정으로 확인한 경계다 — 판단이 아니다.**

    `hidden` 조상 안의 control 은 `display:none` 이라 Chrome AX tree 에 노드가 아예 없다.
    두 fixture 는 조상의 `hidden` 속성 하나만 다르고 control 은 같다. DOM 해소는 양쪽 다
    성공하는데(backend id 가 나온다) AX 노드는 드러난 쪽에만 있다. 즉 이 `None` 은
    조인기의 실패가 아니라 **S0 시점 AX 의 부재**다.

    v3 의 drawer/sheet/menu 진입 control 은 대부분 이 상태다 — 그 `accessible_name` 은
    reveal 이후 상태에서 다시 조인해야 관측된다. 조인기가 채워 넣을 수 있는 값이 아니다.
    """
    for name, hidden in (("gated.html", " hidden"), ("revealed.html", "")):
        (tmp_path / name).write_text(
            _REVEAL_TEMPLATE.format(name=name.removesuffix(".html"), hidden=hidden),
            encoding="utf-8",
        )
    out = _collect(tmp_path, ["gated.html", "revealed.html"], ax_join=True, tmp=tmp_path / "ev")

    got = {}
    for name, obs in out["obs"].items():
        assert obs.measurement_status == "MEASURED", obs.notes
        payload = json.loads(
            (out["run"].run_dir / ax_join_relpath_for(obs.observation_id)).read_text(
                encoding="utf-8"
            )
        )
        got[name] = next(e for e in payload["entries"] if e["selector"] == "button#entry")

    gated, revealed = got["gated.html"], got["revealed.html"]
    # DOM 쪽은 양쪽 다 찾았다. 차이는 오직 AX 쪽이다.
    assert gated["backend_dom_node_id"] is not None
    assert revealed["backend_dom_node_id"] is not None

    assert gated["join_status"] == JoinStatus.AX_NODE_ABSENT
    assert gated["ax_node"] is None
    assert Note.NOT_IN_AX_TREE in gated["notes"]

    assert revealed["join_status"] == JoinStatus.JOINED
    assert revealed["ax_node"]["name"] == "운행정보 조회"


# ── 11. Δ20 — collector_sha256 은 수집기 산출물 + 관측 행 둘 다에 ────────────
def test_collector_provenance_names_the_combining_method() -> None:
    """색인이 결합 방식을 정하지 않았다. W5I 가 정했고 그 방식이 값과 함께 실린다.

    방식 식별자가 없으면 두 관측의 `collector_sha256` 이 다를 때 '수집기가 달랐다' 와
    '합치는 방식이 달랐다' 를 사후에 가릴 수 없다.
    """
    prov = collector_provenance()
    assert prov["collector_sha256"] == collector_sha256()["combined"]
    assert prov["collector_sha256_method"] == COLLECTOR_SHA256_METHOD
    assert set(prov["collector_sha256_files"]) == set(COLLECTOR_SOURCE_FILES)
    assert prov["ax_join_version"] == AX_JOIN_VERSION


def test_provenance_notes_carry_both_the_digest_and_the_method() -> None:
    notes = collector_provenance_notes()
    # `R22` 가 줄을 더 붙이므로 총 개수를 고정하지 않는다. 대신 `Δ20` 두 줄이 **각각
    # 정확히 하나씩** 있는 것을 본다 — 개수 고정보다 이쪽이 계약에 가깝다.
    assert sum(n.startswith(COLLECTOR_SHA256_NOTE_PREFIX) for n in notes) == 1
    assert sum(n.startswith(COLLECTOR_SHA256_METHOD_NOTE_PREFIX) for n in notes) == 1
    digest = next(n for n in notes if n.startswith(COLLECTOR_SHA256_NOTE_PREFIX))
    method = next(n for n in notes if n.startswith(COLLECTOR_SHA256_METHOD_NOTE_PREFIX))
    assert digest.removeprefix(COLLECTOR_SHA256_NOTE_PREFIX) == collector_sha256()["combined"]
    assert method.removeprefix(COLLECTOR_SHA256_METHOD_NOTE_PREFIX) == COLLECTOR_SHA256_METHOD


def test_every_v3_observation_row_carries_the_collector_fingerprint(
    joined_pair: dict[str, Any],
) -> None:
    """`Δ20` must_appear_in 의 '관측 행' 쪽. 행 하나도 빠지지 않는다."""
    expected = collector_sha256()["combined"]
    for name, obs in joined_pair["obs"].items():
        row = obs.as_dict()
        digests = [
            n.removeprefix(COLLECTOR_SHA256_NOTE_PREFIX)
            for n in row["notes"]
            if n.startswith(COLLECTOR_SHA256_NOTE_PREFIX)
        ]
        assert digests == [expected], f"{name}: {row['notes']}"
        assert any(n.startswith(COLLECTOR_SHA256_METHOD_NOTE_PREFIX) for n in row["notes"])


def test_the_collector_artifact_carries_it_too(joined_pair: dict[str, Any]) -> None:
    """`Δ20` must_appear_in 의 '수집기' 쪽 — 파일별 해시까지 남는다."""
    for payload in joined_pair["payloads"].values():
        assert payload["collector_sha256"]["combined"] == collector_sha256()["combined"]
        for rel in COLLECTOR_SOURCE_FILES:
            assert payload["collector_sha256"][rel]


def test_legacy_rows_gain_no_fingerprint_note(
    icon_only_pair: dict[str, Path], tmp_path: Path
) -> None:
    """가산성의 반대편 대조군 — 조인을 끄면 행은 base 와 같다."""
    out = _collect(icon_only_pair["root"], ["icon_only_unnamed.html"], ax_join=False, tmp=tmp_path)
    notes = out["obs"]["icon_only_unnamed.html"].notes
    assert not [n for n in notes if n.startswith("COLLECTOR_SHA256")]
    assert notes == []


def test_the_fingerprint_survives_a_failed_observation(tmp_path: Path) -> None:
    """항해가 실패해도 '어느 수집기가 낸 관측인가' 는 남아야 한다.

    지문을 브라우저 열기 **전에** 붙이는 이유다. 실패한 행에 지문이 없으면 그 실패가
    어느 수집기의 실패인지 사후에 말할 수 없다.
    """
    root = tmp_path / "fx"
    root.mkdir()
    out = _collect(root, ["does_not_exist.html"], ax_join=True, tmp=tmp_path / "ev")
    obs = out["obs"]["does_not_exist.html"]
    assert obs.measurement_status != "MEASURED"
    assert any(n.startswith(COLLECTOR_SHA256_NOTE_PREFIX) for n in obs.notes), obs.notes


# ── 12. R22 — capture_stack (engine sha 하나로는 부족하다) ────────────────────
#
# `T-A-V3-STEP1-021`: "포착 동작이 호출자(session.py)에 있으면 engine sha 만으로는
# '어느 코드가 이 관측을 냈는가' 가 불완전하다" · "둘 중 하나만 있으면 재현 시 다른 쪽이
# 바뀐 것을 알 수 없다".
#
# 이 절의 두 음성대조가 핵심이다. **AttributeError 가 사라지는 것은 수용기준이 아니고,
# 시끄러운 실패를 조용한 통과로 바꾸는 것도 아니다.** 그래서 (a) 구성원 1바이트 변경이
# 지문에 반드시 나타나는가, (b) 구성원 부재가 값으로 남는가(건너뛰지도 죽지도 않는가)
# 를 각각 본다.

_MEMBER_SEED = {rel: f"seed:{rel}".encode() for rel in CAPTURE_STACK_MEMBERS}


def _plant(root: Path, members: dict[str, bytes]) -> Path:
    """가짜 패키지 루트에 구성원 파일을 심는다."""
    for rel, blob in members.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    return root


def test_capture_stack_covers_engine_and_driver_not_engine_alone() -> None:
    """`R22` 가 요구한 구성원이 실제로 전부 들어 있는가."""
    assert set(CAPTURE_STACK_MEMBERS) == {
        "engine/l0_collector.py",
        "engine/l0_probe.js",
        "v3_runner/ax_join.py",
        "v3_runner/runner.py",
        "v3_runner/session.py",
    }
    # driver 층이 비어 있으면 `R22` 를 만족하지 못한다 — engine sha 만 남는 셈이다.
    assert CAPTURE_STACK_LAYERS["driver"] == ("v3_runner/runner.py", "v3_runner/session.py")
    stack = capture_stack()
    assert set(stack["members"]) == set(CAPTURE_STACK_MEMBERS)
    assert set(stack["layers"]) == set(CAPTURE_STACK_LAYERS)
    assert stack["method"] == CAPTURE_STACK_METHOD


def test_capture_stack_is_a_superset_of_the_delta20_fingerprint() -> None:
    """`collector_sha256` 을 대체하지 않고 감싼다 — 같은 이름에 두 뜻을 주지 않기 위해서다."""
    assert set(COLLECTOR_SOURCE_FILES) < set(CAPTURE_STACK_MEMBERS)
    # 결합 방식이 같아도 대상 집합이 다르므로 두 지문은 같을 수 없다.
    assert capture_stack()["combined"] != collector_sha256()["combined"]


@pytest.mark.parametrize("target", CAPTURE_STACK_MEMBERS)
def test_capture_stack_changes_when_one_member_byte_changes(tmp_path: Path, target: str) -> None:
    """**음성대조 (a)** — 구성원 하나를 1바이트 바꾸면 지문이 달라진다.

    이 테스트가 없으면 "지문을 뜬다" 와 "상수를 낸다" 가 같은 출력으로 통과한다.
    구성원 전부에 대해 돈다 — 하나라도 결합에서 빠져 있으면 그 파라미터가 실패한다.
    """
    root = _plant(tmp_path, dict(_MEMBER_SEED))
    before = capture_stack(root)
    assert before["completeness"] == CAPTURE_STACK_COMPLETE

    # 정확히 1바이트를 더한다.
    (root / target).write_bytes(_MEMBER_SEED[target] + b"!")
    after = capture_stack(root)

    assert after["members"][target] != before["members"][target], target
    assert after["combined"] != before["combined"], target
    # 바뀐 구성원이 속한 층만 움직이고 나머지 층은 그대로다 — 층 지문이 실제로
    # 층별로 계산됐다는 뜻이다.
    changed = {name for name, rels in CAPTURE_STACK_LAYERS.items() if target in rels}
    for layer in CAPTURE_STACK_LAYERS:
        if layer in changed:
            assert after["layers"][layer] != before["layers"][layer], (target, layer)
        else:
            assert after["layers"][layer] == before["layers"][layer], (target, layer)
    # 나머지 구성원은 한 글자도 안 바뀐다.
    for rel in CAPTURE_STACK_MEMBERS:
        if rel != target:
            assert after["members"][rel] == before["members"][rel]


def test_a_missing_member_is_named_absent_not_skipped_and_does_not_raise(
    tmp_path: Path,
) -> None:
    """**음성대조 (b)** — 구성원 부재가 **값**으로 남는다.

    `runner.py` / `session.py` 는 다른 lane(W5F/W5H) 소유라 이 워크트리에 없다.
    없는 파일을 만들지 않았다. 그래서 부재 처리가 셋 중 어느 것도 아니어야 한다:

    1. 예외로 죽는다 — 수집 전체가 넘어간다.
    2. 조용히 건너뛴다 — 부재 스택의 지문이 완전 스택의 지문과 **같아진다**. 그러면
       `R22` 가 막으려던 "다른 쪽이 바뀐 것을 알 수 없다" 가 그대로 재현된다.
    3. `null` / 빈 문자열 — `Δ15-GAP04` 위반.

    셋 다 아님을 하나씩 확인한다.
    """
    absent = ("v3_runner/runner.py", "v3_runner/session.py")
    present = {rel: blob for rel, blob in _MEMBER_SEED.items() if rel not in absent}
    root = _plant(tmp_path, present)

    stack = capture_stack(root)  # (1) 예외로 죽지 않는다

    # 키가 사라지지 않는다. 값이 명시적 표지다. `null` 도 빈 문자열도 아니다.
    for rel in absent:
        assert rel in stack["members"]
        assert stack["members"][rel] == CAPTURE_STACK_ABSENT == "ABSENT_IN_THIS_TREE"
        assert stack["members"][rel] not in (None, "")
    assert stack["absent_members"] == list(absent)
    assert stack["unreadable_members"] == []
    assert stack["completeness"] == CAPTURE_STACK_PARTIAL

    # (2) 조용한 통과가 아님의 증명 — 부재 구성원을 결합에서 **빼면** 다른 값이 나온다.
    #     즉 부재는 결합에 실제로 기여한다.
    skipped = hashlib.sha256(
        "".join(f"{rel}:{stack['members'][rel]}\n" for rel in sorted(present)).encode("utf-8")
    ).hexdigest()
    assert stack["combined"] != skipped

    # 그리고 그 파일이 나중에 생기면 지문이 바뀐다 — `R22` 가 요구한 바로 그 성질이다.
    _plant(root, {rel: _MEMBER_SEED[rel] for rel in absent})
    filled = capture_stack(root)
    assert filled["completeness"] == CAPTURE_STACK_COMPLETE
    assert filled["absent_members"] == []
    assert filled["combined"] != stack["combined"]
    assert filled["layers"]["driver"] != stack["layers"]["driver"]
    # engine/joiner 는 안 건드렸으므로 그대로여야 한다 — 부재가 다른 층으로 새지 않는다.
    assert filled["layers"]["engine"] == stack["layers"]["engine"]
    assert filled["layers"]["joiner"] == stack["layers"]["joiner"]


def test_unreadable_is_not_collapsed_into_absent(tmp_path: Path) -> None:
    """읽기 실패와 부재는 서로 다른 사실이다 — 한 값으로 뭉개면 사후 대응이 갈리지 않는다."""
    root = _plant(tmp_path, dict(_MEMBER_SEED))
    victim = root / "v3_runner/session.py"
    victim.chmod(0o000)
    try:
        stack = capture_stack(root)
    finally:
        victim.chmod(0o644)
    if stack["members"]["v3_runner/session.py"] == CAPTURE_STACK_UNREADABLE:
        assert stack["unreadable_members"] == ["v3_runner/session.py"]
        assert stack["absent_members"] == []
        assert stack["completeness"] == CAPTURE_STACK_PARTIAL
    else:  # root 로 돌면 chmod 가 막지 못한다 — 그때는 이 대조를 세울 수 없다.
        pytest.skip("이 실행 계정은 0o000 파일을 읽을 수 있다 (root)")


def test_this_tree_actually_reports_the_driver_as_absent() -> None:
    """실측 — W5I 워크트리에 `runner.py`/`session.py` 는 **없다**. 없는 것을 없다고 낸다.

    이 테스트는 다른 lane 이 병합되면 자연히 `COMPLETE` 로 넘어간다. 그때 값이 바뀌는
    것이 정상이고, 바뀌는 것이 보이는 것이 `R22` 의 목적이다.
    """
    stack = capture_stack()
    pkg = RESEARCH / "src" / "landing_accessibility"
    for rel in CAPTURE_STACK_MEMBERS:
        on_disk = (pkg / rel).is_file()
        assert (stack["members"][rel] != CAPTURE_STACK_ABSENT) is on_disk, rel
    assert stack["completeness"] == (
        CAPTURE_STACK_COMPLETE if not stack["absent_members"] else CAPTURE_STACK_PARTIAL
    )


def test_capture_stack_notes_name_the_incompleteness(tmp_path: Path) -> None:
    """행에 지문만 남기고 완전성을 안 남기면 `PARTIAL` 지문이 `COMPLETE` 와 섞여 비교된다."""
    root = _plant(tmp_path, {r: b for r, b in _MEMBER_SEED.items() if r != "v3_runner/session.py"})
    notes = capture_stack_notes(root)
    stack = capture_stack(root)
    got = dict(n.split("=", 1) for n in notes)
    assert got["CAPTURE_STACK"] == stack["combined"]
    assert got["CAPTURE_STACK_METHOD"] == CAPTURE_STACK_METHOD
    assert got["CAPTURE_STACK_COMPLETENESS"] == CAPTURE_STACK_PARTIAL
    assert got["CAPTURE_STACK_ABSENT"] == "v3_runner/session.py"
    assert got["CAPTURE_STACK_UNREADABLE"] == CAPTURE_STACK_NONE
    # 완전한 스택에서는 빈 문자열이 아니라 `NONE` 이다.
    (root / "v3_runner/session.py").write_bytes(b"x")
    full = dict(n.split("=", 1) for n in capture_stack_notes(root))
    assert full["CAPTURE_STACK_COMPLETENESS"] == CAPTURE_STACK_COMPLETE
    assert full["CAPTURE_STACK_ABSENT"] == CAPTURE_STACK_NONE != ""


def test_every_v3_observation_row_carries_the_capture_stack(
    joined_pair: dict[str, Any],
) -> None:
    """`R22` 의 '모든 v3 관측 행' — 행 하나도 빠지지 않는다."""
    stack = capture_stack()
    for name, obs in joined_pair["obs"].items():
        notes = obs.as_dict()["notes"]
        # `CAPTURE_STACK=` 뒤는 `=`, 나머지는 `_` 로 갈리므로 접두사가 겹치지 않는다.
        digests = [
            n.removeprefix(CAPTURE_STACK_NOTE_PREFIX)
            for n in notes
            if n.startswith(CAPTURE_STACK_NOTE_PREFIX)
        ]
        assert digests == [stack["combined"]], f"{name}: {notes}"
        assert any(n.startswith(CAPTURE_STACK_METHOD_NOTE_PREFIX) for n in notes)
        assert any(n.startswith(CAPTURE_STACK_COMPLETENESS_NOTE_PREFIX) for n in notes)


def test_the_join_artifact_carries_the_capture_stack_sub_object(
    joined_pair: dict[str, Any],
) -> None:
    """구성원별 해시는 하위 객체로 남는다 — 행의 note 는 결합값만 담을 수 있다."""
    stack = capture_stack()
    for payload in joined_pair["payloads"].values():
        got = payload["capture_stack"]
        assert got["combined"] == stack["combined"]
        assert set(got["members"]) == set(CAPTURE_STACK_MEMBERS)
        assert got["completeness"] in (CAPTURE_STACK_COMPLETE, CAPTURE_STACK_PARTIAL)


def test_provenance_carries_the_capture_stack_for_the_row_schema() -> None:
    """행 스키마를 소유한 lane(W5F/W5H)이 그대로 병합할 수 있는 모양인가."""
    prov = collector_provenance()
    assert prov["capture_stack"] == capture_stack()
    assert json.loads(json.dumps(prov)) == prov  # 직렬화 가능해야 행에 실린다


def test_legacy_rows_gain_no_capture_stack_note(
    icon_only_pair: dict[str, Path], tmp_path: Path
) -> None:
    """가산성 대조군 — 조인을 끄면 `R22` 줄도 붙지 않는다."""
    out = _collect(icon_only_pair["root"], ["icon_only_unnamed.html"], ax_join=False, tmp=tmp_path)
    assert out["obs"]["icon_only_unnamed.html"].notes == []
