"""W5E — v3 offline fixture 13종과 그 판별 행렬.

**이 파일의 PASS/FAIL 은 synthetic offline fixture 에 대한 명세 검사 결과다.**
실제 서비스에 대한 research finding 이 아니며 그렇게 인용할 수 없다.

여기서 검사하는 것은 "측정기가 옳은가" 가 아니라 **"fixture 집합이 무엇을 판별하는지의
선언이 자기 자신과 일치하는가"** 다. 측정 파이썬 로직은 W5B/W5C/W5D 담당이고 이 파일에 없다.

핵심은 `contrast_pair` 다. fixture 하나만으로는 "그 값이 나온다" 만 보이고 "그 fixture 가
그것을 재고 있다" 는 못 본다. 구조가 같고 판별 대상만 다른 짝이 있어야 한다 — 그래서
짝으로 선언된 두 fixture 의 DOM 태그 시퀀스를 **기계적으로 비교**한다.

기대값의 정본은 `research/landing_accessibility/fixtures/v3/FIXTURE_DISCRIMINATION_MATRIX.json`,
값 집합의 정본은 `SSOTV3/04_FLOW_CODEBOOK_v3.0.md §4` 다.

의존성은 표준 라이브러리뿐이다 (브라우저 없이 회귀에 항상 포함된다).
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
V3 = REPO / "research" / "landing_accessibility" / "fixtures" / "v3"
MATRIX_PATH = V3 / "FIXTURE_DISCRIMINATION_MATRIX.json"

# Director 가 지정한 13종 — 이 목록 자체가 계약이다.
FIXTURE_IDS = [
    "direct_text_button",
    "icon_text",
    "icon_only_ax_named",
    "icon_only_unnamed",
    "hamburger",
    "left_drawer",
    "right_drawer",
    "bottom_sheet",
    "nested_menu",
    "task_first_auth",
    "login_first_auth",
    "modal_obstruction",
    "evidence_defect",
]

MEASURED_FIELDS = [
    "s0_task_control_visible",
    "first_visible_scroll_state",
    "entry_x_norm",
    "entry_y_norm",
    "entry_zone",
    "entry_control_type",
    "entry_label_modality",
    "visible_label_text",
    "accessible_name",
    "accessible_name_source",
    "label_relation",
    "nav_container_type",
    "reveal_direction",
    "menu_dependency",
    "nav_container_depth",
    "activation_depth",
    "flow_step_count",
    "auth_gate_stage",
    "forced_dismissal_count",
    "task_control_occlusion",
    "endpoint_status",
]

# `SSOTV3/04_FLOW_CODEBOOK_v3.0.md §4` 를 이 파일에서 **독립적으로 한 번 더** 옮겨 적는다.
# matrix 의 전사본과 교차 대조하므로 어느 한쪽의 오타가 잡힌다.
CODEBOOK_CATEGORICALS = {
    "entry_zone": ["TOP_LEFT", "TOP_CENTER", "TOP_RIGHT", "MID", "BOTTOM", "FLOATING", "DRAWER"],
    "entry_control_type": [
        "TEXT_LINK",
        "TEXT_BUTTON",
        "ICON_TEXT",
        "ICON_ONLY",
        "TAB",
        "BOTTOM_NAV",
        "HAMBURGER",
        "CARD",
        "SEARCHBOX",
        "LIST_ITEM",
        "OTHER",
    ],
    "entry_label_modality": [
        "EXPLICIT_TEXT",
        "ICON_TEXT",
        "ICON_ONLY_AX_NAMED",
        "ICON_ONLY_UNNAMED",
        "HIDDEN_UNTIL_REVEAL",
    ],
    "accessible_name_source": [
        "VISIBLE_TEXT",
        "ARIA_LABEL",
        "ARIA_LABELLEDBY",
        "LABEL",
        "ALT",
        "TITLE",
        "VALUE",
        "MIXED",
        "NONE",
    ],
    "label_relation": ["MATCH", "SEMANTIC_EQUIV", "DIFFERENT", "VISIBLE_ONLY", "AX_ONLY", "NONE"],
    "nav_container_type": [
        "NONE",
        "HAMBURGER",
        "LEFT_DRAWER",
        "RIGHT_DRAWER",
        "TOP_DROPDOWN",
        "BOTTOM_SHEET",
        "MODAL_MENU",
        "INLINE_EXPAND",
    ],
    "reveal_direction": ["NONE", "LEFT", "RIGHT", "TOP", "BOTTOM", "CENTER", "INLINE"],
    "auth_gate_stage": ["NONE", "BEFORE_TASK_DISCOVERY", "AFTER_TASK_SELECT", "AT_ENDPOINT"],
    "endpoint_status": [
        "REACHED",
        "AUTH_GATE",
        "PUBLIC_WEB_UNOBSERVABLE",
        "APP_REQUIRED",
        "EVIDENCE_DEFECT",
        "BLOCKED",
        "ABSTAIN",
    ],
}

BOOL_FIELDS = {"s0_task_control_visible", "menu_dependency"}
COUNT_FIELDS = {
    "nav_container_depth",
    "activation_depth",
    "flow_step_count",
    "forced_dismissal_count",
}
UNIT_FIELDS = {"entry_x_norm", "entry_y_norm", "task_control_occlusion"}
TEXT_FIELDS = {"visible_label_text", "accessible_name"}
SCROLL_STATE_RE = re.compile(r"^S(0|[1-9][0-9]*)$")

VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

VIEWPORT_W, VIEWPORT_H = 390, 844


# ── 파서 도구 ────────────────────────────────────────────────────────────────
class _BodyStructure(HTMLParser):
    """body 안의 시작 태그를 문서 순서대로 모으고, 동시에 중첩 정합성을 확인한다."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.saw_body = False
        self.tags: list[str] = []
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag == "body":
            self.in_body = True
            self.saw_body = True
            return
        if self.in_body:
            self.tags.append(tag)
            if tag not in VOID_TAGS:
                self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: object) -> None:
        if self.in_body:
            self.tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "body":
            self.in_body = False
            return
        if not self.in_body or tag in VOID_TAGS:
            return
        if not self.stack:
            self.errors.append(f"닫는 태그 </{tag}> 에 대응하는 여는 태그가 없다")
        elif self.stack[-1] != tag:
            self.errors.append(f"중첩 불일치: <{self.stack[-1]}> 안에서 </{tag}> 를 닫는다")
            self.stack.pop()
        else:
            self.stack.pop()


def body_structure(path: Path) -> _BodyStructure:
    parser = _BodyStructure()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def _fixture_attr(path: Path) -> str | None:
    m = re.search(r'<body[^>]*\bdata-fixture="([^"]+)"', path.read_text(encoding="utf-8"))
    return m.group(1) if m else None


# ── pytest fixture ───────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def matrix() -> dict:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def by_id(matrix: dict) -> dict:
    return {f["fixture_id"]: f for f in matrix["fixtures"]}


def _gate1_added_ids() -> list[str]:
    """`Δ47` ③ 가산분 — **matrix 가 선언한 것만** 이 디렉터리에 있어도 된다.

    선언을 matrix 에서 읽는다. 이 파일에 목록을 다시 적으면 두 곳이 어긋나는 날이 온다.
    """
    section = json.loads(MATRIX_PATH.read_text("utf-8")).get("gate1_depth_signal_fixtures", {})
    return sorted(f["fixture_id"] for f in section.get("must_flag_fixtures", []))


# ── 1. fixture 파일 자체 ─────────────────────────────────────────────────────
def test_the_thirteen_fixture_files_exist() -> None:
    """Director 지정 13종은 그대로 있고, 그 밖의 파일은 **선언된 가산분뿐**이다.

    `Δ47` ③ 이 `aria-haspopup`/`aria-controls` 가산을 허용·요구해 파일이 늘었다.
    "그 밖의 파일이 없다" 를 "선언된 것만 있다" 로 **좁힌다** — 선언 없이 늘어나는 것은
    여전히 실패다(`Δ31` — 다시 좁히는 것은 되고 지우는 것은 안 된다).
    """
    missing = [fid for fid in FIXTURE_IDS if not (V3 / f"{fid}.html").is_file()]
    assert not missing, f"없는 fixture: {missing}"
    declared = set(FIXTURE_IDS) | set(_gate1_added_ids())
    extra = sorted(p.stem for p in V3.glob("*.html") if p.stem not in declared)
    assert not extra, f"어디에도 선언되지 않은 fixture 가 v3 에 있다: {extra}"


def test_the_gate1_additions_are_declared_and_present() -> None:
    """`Δ47` ③ — 가산분이 matrix 에 선언돼 있고 파일이 실재한다. 선언만 있고 파일이
    없으면 `GATE 1` 이 존재하지 않는 fixture 로 통과한다."""
    added = _gate1_added_ids()
    assert added, "Δ47 ③ 가산분이 matrix 에 하나도 선언되지 않았다"
    missing = [fid for fid in added if not (V3 / f"{fid}.html").is_file()]
    assert not missing, f"선언됐는데 파일이 없다: {missing}"
    # 13종은 **고치지 않는다** — 가산분이 그 목록에 섞여 들어오지 않았는가.
    assert not (set(added) & set(FIXTURE_IDS)), "가산분이 Director 13종 목록을 덮었다"


def test_the_gate1_section_states_the_fixture_only_limitation() -> None:
    """`Δ47` 이 **반드시 적으라**고 한 한계 문장이 matrix 에 있다.

    `[Δ47 인용]` *"fixture 에 신호를 넣는 것이 실사이트에 그 신호가 있다는 근거는 아니다.
    pilot 5 실측 전까지 v3 의 `menu_dependency` 양성 관측은 fixture 근거만 갖는다."*
    """
    section = json.loads(MATRIX_PATH.read_text("utf-8"))["gate1_depth_signal_fixtures"]
    limitation = section["limitation"]
    assert "실사이트에 그 신호가 있다는 근거는 아니다" in limitation
    assert "fixture 근거만" in limitation
    assert "pilot 5" in limitation


@pytest.mark.parametrize("fid", _gate1_added_ids())
def test_gate1_additions_obey_the_same_fixture_hygiene(fid: str) -> None:
    """가산분도 13종과 같은 위생 규칙을 받는다 — 실서비스 참조 0 · 자격증명 0 ·
    자기 id 선언 · 모바일 viewport."""
    text = (V3 / f"{fid}.html").read_text("utf-8")
    assert _fixture_attr(V3 / f"{fid}.html") == fid
    for scheme in ("https://", "http://", "//cdn", 'src="//'):
        assert scheme not in text, f"{fid} 가 외부 자원을 참조한다: {scheme}"
    for m in re.finditer(r"<input\b[^>]*>", text):
        assert "value=" not in m.group(0), f"{fid}: input 에 value 가 채워져 있다"
    assert 'name="viewport"' in text
    assert f"width:{VIEWPORT_W}px" in text.replace(" ", "")
    assert f"height:{VIEWPORT_H}px" in text.replace(" ", "")
    assert "검증 대상" in text
    # 한계 문장을 fixture 파일 자신도 갖는다 — matrix 만 보는 사람과 파일만 보는 사람이
    # 서로 다른 것을 읽으면 안 된다.
    assert "실사이트에 그 신호가 있다는 근거는 아니다" in text


@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_each_fixture_parses_with_consistent_nesting(fid: str) -> None:
    s = body_structure(V3 / f"{fid}.html")
    assert s.saw_body, f"{fid}: <body> 가 없다"
    assert not s.errors, f"{fid}: {s.errors}"
    assert not s.stack, f"{fid}: 닫히지 않은 태그 {s.stack}"
    assert s.tags, f"{fid}: body 가 비어 있다"


@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_each_fixture_declares_what_it_validates(fid: str) -> None:
    """기대값 없는 fixture 는 테스트의 근거가 되지 못한다 (부모 디렉터리 README 규약 1)."""
    head = (V3 / f"{fid}.html").read_text(encoding="utf-8")[:2500]
    assert f"FIXTURE: {fid}" in head, f"{fid}: 상단 FIXTURE 주석이 없거나 id 가 다르다"
    assert "검증 대상" in head, f"{fid}: '검증 대상' 서술이 없다"


@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_fixtures_never_reference_a_live_service(fid: str) -> None:
    """fixture 가 외부를 참조하면 그 순간 real-target 수집이 된다 (README 규약 3)."""
    text = (V3 / f"{fid}.html").read_text(encoding="utf-8")
    for scheme in ("https://", "http://", "//cdn", 'src="//'):
        assert scheme not in text, f"{fid} 가 외부 자원을 참조한다: {scheme}"


@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_body_declares_its_own_fixture_id(fid: str) -> None:
    assert _fixture_attr(V3 / f"{fid}.html") == fid


@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_no_fixture_ships_a_credential(fid: str) -> None:
    """03 §7 — credential 입력 금지. 로그인 폼이 있어도 값이 미리 채워져 있으면 안 된다."""
    text = (V3 / f"{fid}.html").read_text(encoding="utf-8")
    for m in re.finditer(r"<input\b[^>]*>", text):
        assert "value=" not in m.group(0), f"{fid}: input 에 value 가 채워져 있다 — {m.group(0)}"


def test_fixtures_are_mobile_viewport_documents() -> None:
    for fid in FIXTURE_IDS:
        text = (V3 / f"{fid}.html").read_text(encoding="utf-8")
        assert 'name="viewport"' in text, f"{fid}: viewport meta 가 없다"
        assert f"width:{VIEWPORT_W}px" in text.replace(" ", ""), f"{fid}: 390px 폭 선언이 없다"
        assert f"height:{VIEWPORT_H}px" in text.replace(" ", ""), f"{fid}: 844px 높이 선언이 없다"


# ── 2. matrix 와 fixture 의 대응 ─────────────────────────────────────────────
def test_matrix_covers_exactly_the_thirteen_fixtures(matrix: dict) -> None:
    assert [f["fixture_id"] for f in matrix["fixtures"]] == sorted(
        [f["fixture_id"] for f in matrix["fixtures"]], key=FIXTURE_IDS.index
    )
    assert sorted(f["fixture_id"] for f in matrix["fixtures"]) == sorted(FIXTURE_IDS)


def test_every_matrix_file_actually_exists(matrix: dict) -> None:
    for f in matrix["fixtures"]:
        assert (V3 / f["file"]).is_file(), f"{f['fixture_id']}: {f['file']} 가 없다"
        assert f["file"] == f"{f['fixture_id']}.html"


def test_matrix_declares_the_provenance_of_a_fixture_only_artifact(matrix: dict) -> None:
    p = matrix["provenance"]
    assert p["fixture_only"] is True
    assert p["real_target_measurement"] is False
    assert p["external_resource_referenced"] is False
    assert p["self_approved"] is False


# ── 3. contrast pair ─────────────────────────────────────────────────────────
def test_contrast_pairs_are_mutual(by_id: dict) -> None:
    for fid, f in by_id.items():
        pair = f["contrast_pair"]
        if pair is None:
            assert f.get("contrast_pair_absent_reason"), f"{fid}: 짝이 없는 이유가 없다"
            continue
        assert pair in by_id, f"{fid}: 없는 fixture 를 짝으로 가리킨다 — {pair}"
        assert by_id[pair]["contrast_pair"] == fid, (
            f"{fid} 의 짝은 {pair} 인데 {pair} 의 짝은 {by_id[pair]['contrast_pair']} 다"
        )
        assert pair != fid, f"{fid}: 자기 자신을 짝으로 가리킨다"


def test_paired_fixtures_agree_on_what_the_pair_isolates(by_id: dict) -> None:
    for fid, f in by_id.items():
        pair = f["contrast_pair"]
        if pair is None:
            continue
        assert sorted(f["discriminates"]) == sorted(by_id[pair]["discriminates"]), (
            f"{fid} 와 {pair} 가 판별 대상을 다르게 선언한다"
        )


def test_pair_dom_tag_sequence_declaration_is_true_in_both_directions(by_id: dict) -> None:
    """선언된 판별 대상 외에는 DOM 구조가 같은가를 태그 시퀀스로 기계 검사한다.

    - `dom_tag_sequence_identical_to_pair: true`  → 태그 시퀀스가 실제로 완전히 같아야 한다.
    - `dom_tag_sequence_identical_to_pair: false` → 실제로 **달라야** 하고(선언이 공허하면 안 된다)
      무엇이 다른지 `structural_diff_note` 가 있어야 한다.
    """
    seqs = {fid: body_structure(V3 / f"{fid}.html").tags for fid in FIXTURE_IDS}
    for fid, f in by_id.items():
        pair = f["contrast_pair"]
        if pair is None:
            assert f["dom_tag_sequence_identical_to_pair"] is None
            continue
        declared = f["dom_tag_sequence_identical_to_pair"]
        assert declared == by_id[pair]["dom_tag_sequence_identical_to_pair"], (
            f"{fid} 와 {pair} 가 구조 동일성 선언을 서로 다르게 한다"
        )
        same = seqs[fid] == seqs[pair]
        if declared:
            assert same, (
                f"{fid} 와 {pair} 는 태그 시퀀스가 같다고 선언했지만 실제로 다르다:\n"
                f"  {fid}: {seqs[fid]}\n  {pair}: {seqs[pair]}"
            )
            assert not f.get("structural_diff_note"), (
                f"{fid}: 구조가 같다고 선언했는데 structural_diff_note 가 있다"
            )
        else:
            assert not same, (
                f"{fid} 와 {pair} 는 태그 시퀀스가 다르다고 선언했지만 실제로 같다 — "
                "선언이 공허하다"
            )
            assert f.get("structural_diff_note"), (
                f"{fid}: 구조가 다르다고 선언했으면 무엇이 다른지 적어야 한다"
            )


def test_every_pair_declares_what_differs(by_id: dict) -> None:
    for fid, f in by_id.items():
        if f["contrast_pair"] is None:
            assert f["what_differs_from_pair"] is None
        else:
            assert f["what_differs_from_pair"], f"{fid}: 짝과 무엇이 다른지 적혀 있지 않다"


def test_secondary_contrast_targets_exist_and_are_not_self(by_id: dict) -> None:
    for fid, f in by_id.items():
        for sc in f["secondary_contrasts"]:
            assert sc["fixture_id"] in by_id, (
                f"{fid}: 없는 fixture 를 가리킨다 — {sc['fixture_id']}"
            )
            assert sc["fixture_id"] != fid
            assert sc["differs_in"], f"{fid}→{sc['fixture_id']}: 무엇이 다른지 비어 있다"
            unknown = [x for x in sc["differs_in"] if x not in MEASURED_FIELDS]
            assert not unknown, f"{fid}→{sc['fixture_id']}: 04 에 없는 필드 {unknown}"


def test_pair_summary_agrees_with_the_fixture_entries(matrix: dict, by_id: dict) -> None:
    declared_pairs = {tuple(sorted(p["pair"])) for p in matrix["contrast_pairs"]}
    actual_pairs = {
        tuple(sorted([fid, f["contrast_pair"]]))
        for fid, f in by_id.items()
        if f["contrast_pair"] is not None
    }
    assert declared_pairs == actual_pairs
    for p in matrix["contrast_pairs"]:
        a = by_id[p["pair"][0]]
        assert sorted(p["isolates"]) == sorted(a["discriminates"])
        assert p["dom_tag_sequence_identical"] == a["dom_tag_sequence_identical_to_pair"]
    unpaired = sorted(fid for fid, f in by_id.items() if f["contrast_pair"] is None)
    assert unpaired == sorted(matrix["unpaired_fixtures"])


# ── 4. 값 집합 (04 codebook) ─────────────────────────────────────────────────
def test_matrix_transcription_of_the_codebook_matches_this_files_transcription(
    matrix: dict,
) -> None:
    """04 §4 값 집합을 matrix 와 이 테스트가 각각 전사했다. 둘이 어긋나면 어느 쪽이든 오타다."""
    assert {k: list(v) for k, v in matrix["allowed_values"].items()} == CODEBOOK_CATEGORICALS


def test_transcription_matches_the_ssot_codebook_when_it_is_present() -> None:
    """SSOTV3 는 현재 git 추적 밖이라 워크트리에 없을 수 있다 — 있을 때만 원문과 대조한다."""
    candidates = [REPO / "SSOTV3" / "04_FLOW_CODEBOOK_v3.0.md"]
    if REPO.parent.name == ".agent_worktrees":
        candidates.append(REPO.parents[1] / "SSOTV3" / "04_FLOW_CODEBOOK_v3.0.md")
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        pytest.skip("SSOTV3/04_FLOW_CODEBOOK_v3.0.md 를 찾을 수 없다 (추적 밖)")
    parsed: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[2] != "categorical":
            continue
        tokens = [t.strip() for t in cells[3].split("/")]
        if all(re.fullmatch(r"[A-Z][A-Z0-9_]*", t) for t in tokens):
            parsed[cells[0]] = tokens
    assert parsed == CODEBOOK_CATEGORICALS, (
        "04 원문의 값 집합과 전사본이 다르다.\n"
        f"원문: {json.dumps(parsed, ensure_ascii=False, indent=2)}"
    )


@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_expected_values_are_inside_the_codebook_value_sets(by_id: dict, fid: str) -> None:
    for field, value in by_id[fid]["expected_values"].items():
        assert field in MEASURED_FIELDS, f"{fid}: 04 에 없는 필드 {field}"
        if field in CODEBOOK_CATEGORICALS:
            assert value in CODEBOOK_CATEGORICALS[field], (
                f"{fid}.{field} = {value!r} 는 04 의 정의된 값 집합에 없다"
            )
        elif field in BOOL_FIELDS:
            assert isinstance(value, bool), f"{fid}.{field} 는 bool 이어야 한다"
        elif field in COUNT_FIELDS:
            assert isinstance(value, int) and not isinstance(value, bool) and value >= 0
        elif field in UNIT_FIELDS:
            assert isinstance(value, (int, float)) and not isinstance(value, bool)
            assert 0.0 <= float(value) <= 1.0, f"{fid}.{field} 가 0~1 밖이다"
        elif field in TEXT_FIELDS:
            assert isinstance(value, str)
        elif field == "first_visible_scroll_state":
            assert isinstance(value, str) and SCROLL_STATE_RE.match(value)
        else:  # pragma: no cover - 위 분기가 21 필드를 모두 덮는다
            raise AssertionError(f"{fid}: 분류되지 않은 필드 {field}")


def test_no_field_is_expected_outside_the_twentyone(by_id: dict) -> None:
    for fid, f in by_id.items():
        for bucket in ("discriminates", "does_not_discriminate"):
            unknown = [x for x in f[bucket] if x not in MEASURED_FIELDS]
            assert not unknown, f"{fid}.{bucket}: 04 에 없는 필드 {unknown}"
        for bucket in ("blocked_by_codebook_gap", "not_asserted_measurement_dependent"):
            unknown = [x for x in f.get(bucket, {}) if x not in MEASURED_FIELDS]
            assert not unknown, f"{fid}.{bucket}: 04 에 없는 필드 {unknown}"


# ── 5. 필드 분류의 완전성 ────────────────────────────────────────────────────
@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_field_buckets_partition_the_twentyone_fields(by_id: dict, fid: str) -> None:
    f = by_id[fid]
    buckets = {
        "discriminates": list(f["discriminates"]),
        "does_not_discriminate": list(f["does_not_discriminate"]),
        "blocked_by_codebook_gap": list(f.get("blocked_by_codebook_gap", {})),
        "not_asserted_measurement_dependent": list(f.get("not_asserted_measurement_dependent", {})),
    }
    flat = [x for v in buckets.values() for x in v]
    assert len(flat) == len(set(flat)), f"{fid}: 여러 분류에 중복된 필드 {sorted(flat)}"
    assert set(flat) == set(MEASURED_FIELDS), (
        f"{fid}: 분류에서 빠진 필드 {sorted(set(MEASURED_FIELDS) - set(flat))}"
    )
    assert f["does_not_discriminate"], f"{fid}: does_not_discriminate 가 비어 있을 수 없다"


@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_a_field_is_never_both_expected_and_declared_unassertable(by_id: dict, fid: str) -> None:
    f = by_id[fid]
    unassertable = set(f.get("blocked_by_codebook_gap", {})) | set(
        f.get("not_asserted_measurement_dependent", {})
    )
    overlap = unassertable & set(f["expected_values"])
    assert not overlap, f"{fid}: 확정 못한다고 해놓고 기대값을 적은 필드 {sorted(overlap)}"


@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_every_discriminated_field_actually_has_an_expected_value(by_id: dict, fid: str) -> None:
    missing = [x for x in by_id[fid]["discriminates"] if x not in by_id[fid]["expected_values"]]
    assert not missing, f"{fid}: 판별한다면서 기대값이 없는 필드 {missing}"


def test_gap_ids_referenced_by_fixtures_are_all_defined(matrix: dict) -> None:
    defined = {g["id"] for g in matrix["codebook_gaps"]}
    for f in matrix["fixtures"]:
        for field, gap_id in f.get("blocked_by_codebook_gap", {}).items():
            assert gap_id in defined, f"{f['fixture_id']}.{field}: 정의되지 않은 gap {gap_id}"
    used = {g for f in matrix["fixtures"] for g in f.get("blocked_by_codebook_gap", {}).values()}
    unused = defined - used - {"GAP-06", "GAP-07"}
    assert not unused, f"어느 fixture 도 참조하지 않는 gap 선언 {sorted(unused)}"


# ── 6. 기하 ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_declared_norms_are_recomputable_from_the_declared_box(by_id: dict, fid: str) -> None:
    f = by_id[fid]
    ev = f["expected_values"]
    if "entry_x_norm" not in ev:
        return
    b = f["entry_control_box_css_px"]
    tol = 0.0005
    assert abs((b["x"] + b["w"] / 2) / VIEWPORT_W - ev["entry_x_norm"]) < tol, f"{fid}: x 불일치"
    assert abs((b["y"] + b["h"] / 2) / VIEWPORT_H - ev["entry_y_norm"]) < tol, f"{fid}: y 불일치"
    assert b["x"] >= 0 and b["x"] + b["w"] <= VIEWPORT_W, f"{fid}: box 가 뷰포트 폭을 벗어난다"
    assert b["y"] >= 0 and b["y"] + b["h"] <= VIEWPORT_H, f"{fid}: box 가 뷰포트 높이를 벗어난다"


def test_entry_coordinates_actually_vary_across_the_set(by_id: dict) -> None:
    """좌표가 fixture 마다 실제로 달라야 entry_x_norm/entry_y_norm 이 의미를 갖는다."""
    centers = {
        fid: (f["expected_values"]["entry_x_norm"], f["expected_values"]["entry_y_norm"])
        for fid, f in by_id.items()
        if "entry_x_norm" in f["expected_values"]
    }
    assert len(set(centers.values())) >= 8, f"좌표 변주가 부족하다: {sorted(set(centers.values()))}"
    # 같은 좌표를 쓰는 것은 '좌표를 통제한 대조짝' 일 때뿐이어야 한다.
    seen: dict[tuple, list[str]] = {}
    for fid, c in centers.items():
        seen.setdefault(c, []).append(fid)
    for c, fids in seen.items():
        if len(fids) == 1:
            continue
        for fid in fids:
            partners = set(fids) - {fid}
            allowed = {by_id[fid]["contrast_pair"]} | {
                sc["fixture_id"] for sc in by_id[fid]["secondary_contrasts"]
            }
            assert partners <= allowed, (
                f"{fid} 가 좌표 {c} 를 {sorted(partners)} 와 공유하는데 대조 관계가 선언돼 있지 않다"
            )


# ── 7. 집합 수준 한계 ────────────────────────────────────────────────────────
def test_known_limitations_are_recomputed_from_the_fixture_entries(matrix: dict) -> None:
    """한계 선언이 손으로 적힌 주장이 아니라 fixture 항목에서 도출된 값인지 확인한다."""
    fixtures = matrix["fixtures"]
    pair_isolated = sorted({x for f in fixtures for x in f["discriminates"]})
    values: dict[str, set[str]] = {k: set() for k in MEASURED_FIELDS}
    for f in fixtures:
        for k, v in f["expected_values"].items():
            values[k].add(json.dumps(v, ensure_ascii=False))
    set_varying = sorted(k for k, v in values.items() if len(v) >= 2)
    never = sorted(k for k, v in values.items() if len(v) <= 1)
    lim = matrix["known_limitations"]
    assert lim["pair_isolated_fields"] == pair_isolated
    assert lim["set_level_varying_fields"] == set_varying
    assert lim["never_varying_across_the_set"] == never
    assert lim["varying_but_not_pair_isolated"] == sorted(
        k for k in set_varying if k not in pair_isolated
    )
    assert lim["does_not_discriminate_union"] == never
    assert never, "한계가 하나도 없다는 주장은 이 집합 크기에서 신뢰할 수 없다"


def test_uncovered_codebook_tokens_are_reported_truthfully(matrix: dict) -> None:
    values: dict[str, set] = {k: set() for k in CODEBOOK_CATEGORICALS}
    for f in matrix["fixtures"]:
        for k, v in f["expected_values"].items():
            if k in values:
                values[k].add(v)
    reported = matrix["known_limitations"]["uncovered_codebook_tokens"]
    for field, allowed in CODEBOOK_CATEGORICALS.items():
        assert reported[field]["covered"] == sorted(values[field]), f"{field}: covered 오기"
        assert reported[field]["not_covered"] == [t for t in allowed if t not in values[field]], (
            f"{field}: not_covered 오기"
        )
