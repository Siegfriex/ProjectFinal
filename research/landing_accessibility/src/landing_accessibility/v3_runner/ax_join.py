"""W5I — DOM 후보(selector) ↔ CDP AX slim node 조인.

## 왜 이 모듈이 필요한가 (측정된 사실)

`l0_probe.js` 는 **accessible name 을 계산하지 않는다.** `accessible_name_sources`
raw feature 가 내는 것은 이름의 *출처*(`aria-label`/`aria-labelledby`/`title`/`alt`/
`value`/`label[for]` 유무)뿐이고, 브라우저 naming computation 의 결과인 **계산된 이름**
은 거기에 없다. 계산된 이름은 `l0_collector.L0Collector._ax_tree` 가 CDP
`Accessibility.getFullAXTree` 로 받아 `l0a/ax.json` 에 저장하는 slim node 에만 있다.

그런데 slim node 는 selector 가 아니라 **`backendDOMNodeId`** 로 키잉된다. base 어디에도
`selector ↔ backendDOMNodeId` 를 잇는 코드가 없었다. 그래서 `SSOTV3/00 §8` 의
`visible_label_text` / `accessible_name` 분리도, `04 §4` 의 `accessible_name` ·
`accessible_name_source` · `label_relation` 도, `entry_label_modality` 의
`ICON_ONLY_AX_NAMED` ↔ `ICON_ONLY_UNNAMED` 구분도 산출될 수 없었다. 축 자체가 없었다.

이 모듈이 그 다리를 놓는다.

## 다리를 어디에 놓았는가 — probe 가 아니라 collector 다

`backendDOMNodeId` 는 **페이지 JS 에서 관측 불가능하다.** DevTools 프로토콜 내부의 노드
식별자이고 DOM API 로 노출되지 않는다. 따라서 `l0_probe.js` 가 후보마다 그 값을 낼 수
있게 만드는 경로는 원리적으로 존재하지 않는다 — probe 를 어떻게 고쳐도 안 된다.
그래서 조인은 CDP 를 쥐고 있는 **collector 쪽**에서 한다. 결과적으로
`l0_probe.js` 는 **한 글자도 바뀌지 않는다**(W5I 가산성의 가장 강한 형태다).

방향은 **DOM → AX** 다. probe 가 이미 낸 selector 문자열을 살아 있는 문서에서 다시
찾아(`document.querySelectorAll`) 그 element 의 `backendNodeId` 를 `DOM.describeNode`
로 얻고, 그 값으로 slim node 를 찾는다. 반대 방향(AX 노드마다 `DOM.resolveNode` 후
selector 를 재생성)을 쓰지 않은 이유는 명확하다 — 그 경로는 `l0_probe.js` 의 `sel()`
알고리즘을 파이썬으로 재구현해야 하고, 재구현은 언젠가 원본과 어긋난다. 어긋나면 조인이
**조용히** 실패한다. selector 문자열을 probe 에서 그대로 받아 쓰면 그 표류가 없다.

## 조인 실패를 값으로 바꾸지 않는다

못 이으면 `ax_node` 는 `None` 이고 `AX_NODE_ABSENT` note 가 남는다. DOM 속성으로
이름을 추정하지 않는다 — 추정하는 순간 `visible_label_text` 와 출처가 겹쳐 `00 §8` 의
분리가 무너진다. W5C `surface.py` 의 `_accessible_name_from_ax` 가 정확히 그 계약을
구현했고, 이 모듈의 산출은 그 함수의 입력(`task_control["ax_node"]`)으로 그대로 들어간다.

## 무엇을 만들었고 무엇을 만들지 않았는가

- 만든 것: selector → backendDOMNodeId → AX slim node 조인, 조인 성공률 집계,
  수집기 `collector_sha256` 기록.
- 만들지 않은 것: 새 조작화. `accessible_name` / `accessible_name_source` /
  `label_relation` / `entry_label_modality` 를 **계산하지 않는다**. 그것은 W5C 소유다.
  이 모듈은 W5C 가 계산할 수 있도록 입력을 공급할 뿐이다.

## `collector_sha256` 을 어디에 싣는가 (`Δ20`)

색인의 `must_appear_in` 은 **수집기 + 관측 행**이다. 두 곳 다 채웠다.

- **수집기 산출물**: `l0a/ax_join.json` 이 파일별 sha256 과 `combined` 을 함께 싣는다.
- **관측 행**: `ax_join` 을 켠 수집에서 `L0Observation.notes` 에
  `COLLECTOR_SHA256=<combined>` 와 `COLLECTOR_SHA256_METHOD=<방식>` 두 줄이 붙는다.
  브라우저를 열기 **전에** 붙으므로 조인이나 항해가 실패한 관측 행에도 남는다.
- **v3 행 스키마**: `collector_provenance()` 가 병합용 dict 를 낸다. v3 관측 행 스키마는
  W5F/W5H 소유라 W5I 가 그 파일을 고칠 수 없어 값과 함수만 공급한다.

`notes` 를 쓴 이유는 하나다 — `L0Observation` 에 필드를 더하면 `as_dict()` 가
`e001_runner/executor.py` 에서 그대로 직렬화돼 ledger 해시에 들어가므로 legacy 산출물의
바이트가 바뀐다. 가산성이 깨진다. `notes` 는 이미 있는 필드이고 v3 경로에서만 늘어난다.

합치는 방식(`COLLECTOR_SHA256_METHOD`)은 **색인이 정하지 않아 W5I 가 정했다** —
relpath 사전순으로 `"<relpath>:<sha256(file)>\n"` 을 이어 붙인 바이트열의 sha256 이다.
파일 하나만 바뀌어도 값이 바뀌고 열거 순서에 의존하지 않는다.

## `capture_stack` — engine sha 하나로는 부족하다 (`R22`)

`T-A-V3-STEP1-021`: "포착 동작이 호출자(`session.py`)에 있으면 engine sha 만으로는
'어느 코드가 이 관측을 냈는가' 가 불완전하다" · "모든 v3 관측 행은 engine sha +
driver/session sha 를 함께 기록한다" · "engine 은 바이트 동일한데 포착 능력은 driver
에 있었다".

그래서 `capture_stack` 은 `collector_sha256`(engine + joiner)의 **상위 집합**이다.
구성원은 `engine/l0_collector.py` · `engine/l0_probe.js` · `v3_runner/ax_join.py` ·
`v3_runner/runner.py` · `v3_runner/session.py` 다섯이고, 층은 `engine` / `joiner` /
`driver` 셋이다. 층 배정은 `R22` 가 정하지 않아 W5I 가 정했다.

`Δ20` 지문의 정의를 넓히지 않고 새 이름을 만든 이유: `collector_sha256` 은 이미 산출된
관측 행에 실려 있다. 같은 이름이 두 가지 뜻을 갖게 되면 비교가 성립하지 않는다.

**`runner.py` 와 `session.py` 는 W5I 워크트리에 없다** (각각 W5F / W5H 소유). 만들지
않았다. 대신 그 부재를 값으로 낸다 — `ABSENT_IN_THIS_TREE` 다. `null` 도 빈 문자열도
아니고 조용한 생략도 아니다(`SSOTV3 Δ15-GAP04`: categorical 결측은 명시적 표지).
부재 구성원도 그 값 그대로 `combined` 에 들어가므로, 나중에 그 파일이 생기면 지문이
바뀐다 — "둘 중 하나만 있으면 다른 쪽이 바뀐 것을 알 수 없다" 가 `R22` 가 막으려던
것이고, 부재를 건너뛰면 정확히 그 구멍이 다시 생긴다.

행에는 `CAPTURE_STACK=` · `_METHOD=` · `_COMPLETENESS=` · `_ABSENT=` · `_UNREADABLE=`
다섯 줄이 붙고, 구성원별 해시가 들어간 하위 객체는 `collector_provenance()
["capture_stack"]` 과 `l0a/ax_join.json` 의 `capture_stack` 이 싣는다.

## 측정으로 확인한 경계 — reveal gating

`hidden`(= `display:none`) 조상 안의 control 은 **Chrome AX tree 에 노드가 아예 없다.**
DOM 해소는 성공해 `backendDOMNodeId` 가 나오는데 AX 노드가 없다. 조상의 `hidden` 하나만
다른 짝으로 확인했다(`tests/test_w5i_ax_join.py` 의 reveal 대조군 — 같은 control, 드러난
쪽만 `JOINED` + 이름 관측).

따라서 drawer / bottom sheet / hamburger panel 뒤에 있는 진입 control 의
`accessible_name` 은 **S0 조인으로 관측되지 않는다.** 이것은 조인기가 채울 수 있는 값이
아니다 — reveal 이후 상태에서 다시 조인해야 나온다. 그 재조인을 언제 어느 state 에서
할지는 flow/state 소유 lane 의 결정이라 여기서 정하지 않는다.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

__all__ = [
    "AX_JOIN_RELPATH",
    "AX_JOIN_VERSION",
    "CAPTURE_STACK_ABSENT",
    "CAPTURE_STACK_ABSENT_NOTE_PREFIX",
    "CAPTURE_STACK_COMPLETE",
    "CAPTURE_STACK_COMPLETENESS_NOTE_PREFIX",
    "CAPTURE_STACK_LAYERS",
    "CAPTURE_STACK_MEMBERS",
    "CAPTURE_STACK_METHOD",
    "CAPTURE_STACK_METHOD_NOTE_PREFIX",
    "CAPTURE_STACK_NONE",
    "CAPTURE_STACK_NOTE_PREFIX",
    "CAPTURE_STACK_PARTIAL",
    "CAPTURE_STACK_UNREADABLE",
    "CAPTURE_STACK_UNREADABLE_NOTE_PREFIX",
    "COLLECTOR_SHA256_METHOD",
    "COLLECTOR_SHA256_METHOD_NOTE_PREFIX",
    "COLLECTOR_SHA256_NOTE_PREFIX",
    "COLLECTOR_SOURCE_FILES",
    "DEFAULT_SELECTOR_FEATURES",
    "AxJoinEntry",
    "AxJoinPayload",
    "CDPLike",
    "JoinStatus",
    "Note",
    "SelectorResolution",
    "ax_join_relpath_for",
    "build_ax_join_payload",
    "capture_stack",
    "capture_stack_notes",
    "collect_ax_join",
    "collector_provenance",
    "collector_provenance_notes",
    "collector_sha256",
    "index_ax_nodes",
    "join_resolutions",
    "probe_selectors",
    "resolve_selectors",
    "selector_ax_index",
    "task_control_ax_field",
]

#: 이 조인기의 버전. 산출물에 실려 사후에 "어느 조인기가 낸 관측인가" 를 답한다.
AX_JOIN_VERSION = "w5i-ax-join-1"

#: 조인 산출물이 evidence run 안에서 갖는 관측 기준 상대경로.
#: `L0Observation` 에 필드를 **더하지 않는다** — `L0Observation.as_dict()` 는
#: `e001_runner/executor.py` 가 그대로 직렬화해 ledger 해시에 들어가므로, 필드를 하나라도
#: 더하면 기존 산출물의 바이트가 바뀐다. 그래서 경로 규약으로만 노출한다.
AX_JOIN_RELPATH = "l0a/ax_join.json"


def ax_join_relpath_for(observation_id: str) -> str:
    """`EvidenceRun.run_dir` 기준 조인 산출물 경로 (`L0Collector._store` 의 네임스페이싱)."""
    return f"{observation_id}/{AX_JOIN_RELPATH}"


class JoinStatus:
    """조인 결과 상태 — 상호배타 3값."""

    JOINED = "JOINED"
    #: selector 는 살아 있는 문서에서 찾았지만 그 backendDOMNodeId 를 가진 AX slim node 가 없다.
    AX_NODE_ABSENT = "AX_NODE_ABSENT"
    #: selector 자체가 살아 있는 문서에서 element 로 해소되지 않았다 (조인 이전의 실패).
    DOM_NODE_UNRESOLVED = "DOM_NODE_UNRESOLVED"


class Note:
    """조인 note 어휘.

    `AX_NODE_ABSENT` 는 W5C `surface.py` 가 쓰는 것과 **같은 토큰**이다 — 지시가
    "`AX_NODE_ABSENT` 계열 note" 를 요구했고, 하류가 같은 이름으로 읽어야 한다.
    나머지는 `AX_JOIN_` 접두사로 조인 진단 전용임을 표시한다. 이들은 `04` codebook 의
    필드값이 아니다 — **새 조작화가 아니라 조인기 자신의 진단**이다.
    """

    AX_NODE_ABSENT = "AX_NODE_ABSENT"
    #: selector 가 문서에서 0개를 매칭했다.
    DOM_NO_MATCH = "AX_JOIN_DOM_NO_MATCH"
    #: selector 는 매칭했으나 CDP 가 backendNodeId 를 주지 못했다.
    BACKEND_ID_UNRESOLVED = "AX_JOIN_BACKEND_ID_UNRESOLVED"
    #: selector 가 2개 이상을 매칭했다 — 첫 번째를 썼다. probe 의 `sel()` 이 8단계에서
    #: 잘리므로 원리적으로 발생 가능하다. 값으로 덮지 않고 표시한다.
    SELECTOR_AMBIGUOUS = "AX_JOIN_SELECTOR_AMBIGUOUS"
    #: selector 문법 오류 등으로 querySelectorAll 자체가 던졌다.
    SELECTOR_INVALID = "AX_JOIN_SELECTOR_INVALID"
    #: backendNodeId 가 full AX tree 에는 있으나 `ax.json` slim 필터
    #: (role in {None, "none", "InlineTextBox"})에 걸려 빠졌다.
    FILTERED_FROM_AX_JSON = "AX_JOIN_FILTERED_FROM_AX_JSON"
    #: backendNodeId 가 full AX tree 에도 없다.
    NOT_IN_AX_TREE = "AX_JOIN_NOT_IN_AX_TREE"
    #: full AX tree 대조를 수행하지 않아 부재 사유를 가르지 못했다.
    ABSENCE_UNCLASSIFIED = "AX_JOIN_ABSENCE_UNCLASSIFIED"
    #: 서로 다른 selector 둘 이상이 같은 backendDOMNodeId 로 해소됐다.
    BACKEND_ID_COLLISION = "AX_JOIN_BACKEND_ID_COLLISION"
    #: 조인된 AX 노드가 `ignored: true` 다. 노드는 있으나 접근성 트리에서 제외된 상태다.
    AX_NODE_IGNORED = "AX_JOIN_AX_NODE_IGNORED"


#: probe raw feature 중 selector 를 가진 것들. W5C `surface.py` 의 `_merge_control`
#: 이 control 을 찾는 세 곳과 같다 — 조인 대상이 그보다 좁으면 W5C 가 쓸 수 없다.
DEFAULT_SELECTOR_FEATURES: tuple[str, ...] = (
    "primary_action_candidates",
    "accessible_name_sources",
    "utility_input_widgets",
)


# ── 수집기 지문 ──────────────────────────────────────────────────────────────

#: `collector_sha256` 이 지문을 뜨는 파일들. 패키지 루트(`landing_accessibility/`) 기준.
#: legacy 59 와 12 diagnostic 을 낸 수집기와 v3 를 낼 수집기의 **경계가 데이터에 남는다.**
COLLECTOR_SOURCE_FILES: tuple[str, ...] = (
    "engine/l0_probe.js",
    "engine/l0_collector.py",
    "v3_runner/ax_join.py",
)


def _package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def collector_sha256(package_root: Path | None = None) -> dict[str, str]:
    """수집기 파일들의 sha256 + 그것들을 묶은 `combined` 지문.

    `combined` 는 `"<relpath>:<sha256>\\n"` 을 relpath 사전순으로 이은 바이트열의
    sha256 이다 — 파일이 하나라도 바뀌면 값이 바뀌고, 순서에 의존하지 않는다.
    """
    root = package_root if package_root is not None else _package_root()
    out: dict[str, str] = {}
    for rel in COLLECTOR_SOURCE_FILES:
        path = root / rel
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            digest = "UNREADABLE"
        out[rel] = digest
    joined = "".join(f"{rel}:{out[rel]}\n" for rel in sorted(out))
    out["combined"] = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return out


#: `combined` 을 만드는 방식의 식별자. **A 의 판정 색인(`Δ20`)은 어느 파일들의 해시를
#: 어떻게 합칠지를 정하지 않았다 — W5I 가 정했다.** 방식을 바꾸면 이 문자열도 바꾼다.
#: 그래야 두 관측의 `collector_sha256` 이 다를 때 "수집기가 달랐다" 와 "합치는 방식이
#: 달랐다" 를 사후에 가릴 수 있다.
COLLECTOR_SHA256_METHOD = "sha256(concat(sorted('<relpath>:<sha256(file)>\\n')))/w5i-1"

#: `L0Observation.notes` 에 실리는 접두사. 관측 **행 자체**가 지문을 갖게 하는 경로다
#: (`Δ20` must_appear_in: 수집기 + 관측 행).
COLLECTOR_SHA256_NOTE_PREFIX = "COLLECTOR_SHA256="
COLLECTOR_SHA256_METHOD_NOTE_PREFIX = "COLLECTOR_SHA256_METHOD="


def collector_provenance(package_root: Path | None = None) -> dict[str, Any]:
    """v3 관측 행에 그대로 병합할 provenance 조각.

    v3 관측 행 스키마를 소유한 lane(W5F `evidence.py`/`runner.py`, W5H `session.py`)이
    이것을 행에 합치면 `Δ20` 의 "모든 v3 관측 행" 요구가 스키마 수준에서 충족된다.
    W5I 는 그 파일들을 수정할 수 없으므로 **함수와 값**만 공급한다.
    """
    digests = collector_sha256(package_root)
    return {
        "collector_sha256": digests["combined"],
        "collector_sha256_files": {k: v for k, v in digests.items() if k != "combined"},
        "collector_sha256_method": COLLECTOR_SHA256_METHOD,
        # `R22` — engine sha 만으로는 "어느 코드가 이 관측을 냈는가" 가 불완전하다.
        # driver 층까지 포함한 하위 객체를 **행 스키마에 그대로 실을 수 있는 모양**으로 낸다.
        "capture_stack": capture_stack(package_root),
        "ax_join_version": AX_JOIN_VERSION,
    }


def collector_provenance_notes(package_root: Path | None = None) -> list[str]:
    """`L0Observation.notes` 에 넣을 provenance 줄 전부 (`Δ20` 2줄 + `R22` 5줄).

    `L0Observation` 에 **새 필드를 더할 수 없어서** 고른 경로다. `as_dict()` 는
    `e001_runner/executor.py` 가 그대로 직렬화해 ledger 해시에 넣으므로, 필드를 하나
    더하면 legacy 59 와 12 diagnostic 산출물의 바이트가 바뀐다 — 가산적이지 않다.
    `notes` 는 이미 존재하는 list 필드이고, **`ax_join` 이 켜진 v3 수집에서만** 이 줄들이
    붙으므로 legacy 경로의 바이트는 한 글자도 바뀌지 않는다.
    """
    prov = collector_provenance(package_root)
    return [
        f"{COLLECTOR_SHA256_NOTE_PREFIX}{prov['collector_sha256']}",
        f"{COLLECTOR_SHA256_METHOD_NOTE_PREFIX}{prov['collector_sha256_method']}",
        # `R22` — 같은 규율로 포착 스택 지문도 행에 붙인다. `Δ20` 지문만 있으면
        # driver 가 바뀐 것을 재현 시 알 수 없다.
        *capture_stack_notes(package_root),
    ]


# ── R22 — 포착 스택 지문 (capture_stack) ─────────────────────────────────────
#
# `T-A-V3-STEP1-021` 원문: "`collector_sha256` 하나로는 부족하다. **포착 동작이
# 호출자(session.py)에 있으면 engine sha 만으로는 '어느 코드가 이 관측을 냈는가' 가
# 불완전하다**" · "모든 v3 관측 행은 **engine sha + driver/session sha** 를 함께
# 기록한다" · "둘 중 하나만 있으면 재현 시 다른 쪽이 바뀐 것을 알 수 없다. 이번 건이
# 정확히 그 사례다 — engine 은 바이트 동일한데 포착 능력은 driver 에 있었다".
#
# `collector_sha256` 은 engine + joiner 만 덮는다(`Δ20` 이 그렇게 굳었고 이미 관측
# 행에 실려 있다). `capture_stack` 은 그 위에 driver 층을 얹은 **상위 집합**이다.
# 둘을 한 값으로 합치지 않은 이유: `Δ20` 지문은 이미 산출된 관측 행에 실려 있고, 그
# 정의를 바꾸면 같은 이름의 값이 두 가지 뜻을 갖게 된다. 새 이름에 새 뜻을 담는다.

#: 층별 구성원. **어느 파일이 어느 층인지는 `R22` 가 정하지 않았다 — W5I 가 정했다.**
#: `R22` 는 "engine sha + driver/session sha" 를 함께 기록하라고만 했다.
#: `joiner` 를 engine 에서 떼어 놓은 것도 W5I 의 결정이다: 조인기는 engine 도 driver 도
#: 아니고 v3 에서만 도는 제3의 코드라, engine 에 합치면 engine 이 바뀐 것으로 잘못 읽힌다.
CAPTURE_STACK_LAYERS: dict[str, tuple[str, ...]] = {
    "engine": ("engine/l0_collector.py", "engine/l0_probe.js"),
    "joiner": ("v3_runner/ax_join.py",),
    #: **다른 lane(W5F `runner.py` / W5H `session.py`) 소유다.** W5I 워크트리에는 없다.
    #: 읽어서 해시만 뜬다 — 만들지도, 고치지도 않는다. 없으면 없다고 적는다.
    "driver": ("v3_runner/runner.py", "v3_runner/session.py"),
}

#: 지문을 뜨는 구성원 전부. 패키지 루트(`landing_accessibility/`) 기준 relpath.
CAPTURE_STACK_MEMBERS: tuple[str, ...] = tuple(
    sorted({rel for rels in CAPTURE_STACK_LAYERS.values() for rel in rels})
)

#: 구성원 파일이 **이 트리에 존재하지 않을 때**의 값. `null` 도 빈 문자열도 쓰지 않는다.
#: `SSOTV3 Δ15-GAP04`: 결측은 numeric=`null`, categorical=명시적 표지, 빈 문자열 금지.
#: 조용히 건너뛰면 "그 파일이 있었는데 안 떴다" 와 "애초에 없었다" 가 구분되지 않는다.
CAPTURE_STACK_ABSENT = "ABSENT_IN_THIS_TREE"
#: 파일은 있으나 읽지 못했을 때. **부재와 같은 값으로 뭉개지 않는다** — 부재는 lane 병합
#: 전이라는 뜻이고, 읽기 실패는 환경 결함이라는 뜻이다. 사후 대응이 서로 다르다.
CAPTURE_STACK_UNREADABLE = "UNREADABLE_IN_THIS_TREE"

#: 스택이 전부 지문화됐는가. 하나라도 부재/불가면 `combined` 은 **불완전한 스택**의
#: 지문이므로, 그 사실 자체가 행에 남아야 한다.
CAPTURE_STACK_COMPLETE = "COMPLETE"
CAPTURE_STACK_PARTIAL = "PARTIAL"

#: 결합 방식 식별자. 방식을 바꾸면 이 문자열도 바꾼다 — 그래야 두 관측의 `combined` 이
#: 다를 때 "코드가 달랐다" 와 "합치는 방식이 달랐다" 를 가릴 수 있다.
CAPTURE_STACK_METHOD = "sha256(concat(sorted('<relpath>:<member>\\n')))/r22-w5i-1"

#: `L0Observation.notes` 접두사. 관측 **행 자체**가 포착 스택 지문을 갖게 하는 경로다.
CAPTURE_STACK_NOTE_PREFIX = "CAPTURE_STACK="
CAPTURE_STACK_METHOD_NOTE_PREFIX = "CAPTURE_STACK_METHOD="
CAPTURE_STACK_COMPLETENESS_NOTE_PREFIX = "CAPTURE_STACK_COMPLETENESS="
#: 부재/읽기불가 구성원을 **행에 이름으로** 남긴다. 둘은 서로 다른 사실이라 줄을 나눈다.
#: 비어 있으면 `NONE` 이다 — 빈 문자열을 쓰지 않는다(`Δ15-GAP04`).
CAPTURE_STACK_ABSENT_NOTE_PREFIX = "CAPTURE_STACK_ABSENT="
CAPTURE_STACK_UNREADABLE_NOTE_PREFIX = "CAPTURE_STACK_UNREADABLE="
CAPTURE_STACK_NONE = "NONE"


def _combine(digests: Mapping[str, str], relpaths: Iterable[str]) -> str:
    """`"<relpath>:<값>\n"` 을 relpath 사전순으로 이어 붙인 바이트열의 sha256.

    열거 순서에 의존하지 않고, 구성원 하나만 바뀌어도 값이 바뀐다.
    """
    joined = "".join(f"{rel}:{digests[rel]}\n" for rel in sorted(relpaths))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _member_digest(path: Path) -> str:
    """구성원 하나의 값. 부재/읽기불가를 **예외로 죽지도, 조용히 건너뛰지도 않고** 값으로 낸다."""
    if not path.is_file():
        return CAPTURE_STACK_ABSENT
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return CAPTURE_STACK_UNREADABLE


def capture_stack(package_root: Path | None = None) -> dict[str, Any]:
    """`R22` 포착 스택 지문 — engine + joiner + driver 를 한 객체로.

    키:

    - `members`: `{relpath: sha256 | ABSENT_IN_THIS_TREE | UNREADABLE_IN_THIS_TREE}`
    - `layers`: `{engine|joiner|driver: <층 결합 지문>}`
    - `absent_members` / `unreadable_members`: 지문을 못 뜬 구성원 이름
    - `completeness`: `COMPLETE` | `PARTIAL`
    - `combined`: 구성원 전부의 결합 지문
    - `method`: 결합 방식 식별자

    부재 구성원도 `combined` 에 **`ABSENT_IN_THIS_TREE` 라는 값으로** 들어간다. 그래서
    나중에 그 파일이 생기면 `combined` 이 바뀐다 — "다른 쪽이 바뀐 것을 알 수 없다" 가
    `R22` 가 막으려던 것이고, 부재를 건너뛰면 정확히 그 구멍이 다시 생긴다.
    """
    root = package_root if package_root is not None else _package_root()
    members = {rel: _member_digest(root / rel) for rel in CAPTURE_STACK_MEMBERS}
    absent = [rel for rel in CAPTURE_STACK_MEMBERS if members[rel] == CAPTURE_STACK_ABSENT]
    unreadable = [rel for rel in CAPTURE_STACK_MEMBERS if members[rel] == CAPTURE_STACK_UNREADABLE]
    return {
        "members": members,
        "layers": {layer: _combine(members, rels) for layer, rels in CAPTURE_STACK_LAYERS.items()},
        "absent_members": absent,
        "unreadable_members": unreadable,
        "completeness": (
            CAPTURE_STACK_COMPLETE if not (absent or unreadable) else CAPTURE_STACK_PARTIAL
        ),
        "combined": _combine(members, CAPTURE_STACK_MEMBERS),
        "method": CAPTURE_STACK_METHOD,
    }


def capture_stack_notes(package_root: Path | None = None) -> list[str]:
    """`L0Observation.notes` 에 넣을 포착 스택 다섯 줄.

    `notes` 는 평평한 문자열 리스트라 하위 객체를 담을 수 없다. 그래서 행에는 **지문 +
    방식 + 완전성 + 부재 구성원 이름**을 남기고, 구성원별 해시가 들어간 하위 객체는
    `collector_provenance()["capture_stack"]` 과 `l0a/ax_join.json` 이 싣는다.
    완전성과 부재 이름을 행에 남기지 않으면 `PARTIAL` 지문이 `COMPLETE` 지문과 구분되지
    않은 채로 비교돼, "왜 지문이 다르지" 를 사후에 풀 수 없다.
    """
    stack = capture_stack(package_root)
    return [
        f"{CAPTURE_STACK_NOTE_PREFIX}{stack['combined']}",
        f"{CAPTURE_STACK_METHOD_NOTE_PREFIX}{stack['method']}",
        f"{CAPTURE_STACK_COMPLETENESS_NOTE_PREFIX}{stack['completeness']}",
        CAPTURE_STACK_ABSENT_NOTE_PREFIX
        + (",".join(stack["absent_members"]) or CAPTURE_STACK_NONE),
        CAPTURE_STACK_UNREADABLE_NOTE_PREFIX
        + (",".join(stack["unreadable_members"]) or CAPTURE_STACK_NONE),
    ]


# ── 자료구조 ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SelectorResolution:
    """selector 하나를 살아 있는 문서에서 해소한 결과 (AX 는 아직 보지 않았다)."""

    selector: str
    backend_dom_node_id: int | None
    #: `document.querySelectorAll(selector).length`. `None` 은 세지 못했다는 뜻이다.
    match_count: int | None
    #: querySelectorAll 이 던진 경우의 표시.
    selector_invalid: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AxJoinEntry:
    """selector 하나의 조인 결과."""

    selector: str
    backend_dom_node_id: int | None
    #: CDP AX slim node 그대로. 조인 실패면 `None` 이다 — **절대 추정값을 넣지 않는다.**
    ax_node: dict[str, Any] | None
    join_status: str
    match_count: int | None
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["notes"] = list(self.notes)
        return d


@dataclass(frozen=True)
class AxJoinPayload:
    """`l0a/ax_join.json` 에 실리는 것 전부."""

    ax_join_version: str
    collector_sha256: dict[str, str]
    entries: tuple[AxJoinEntry, ...]
    stats: dict[str, Any]
    notes: tuple[str, ...] = ()
    ax_nodes_total: int = 0
    full_ax_compared: bool = False
    source_features: tuple[str, ...] = field(default=DEFAULT_SELECTOR_FEATURES)
    #: `R22` 포착 스택 지문. `collector_sha256` 의 상위 집합이고 driver 층을 포함한다.
    #: 기본값이 빈 dict 인 것은 순수 구성 테스트가 파일시스템을 만지지 않게 하기 위해서다 —
    #: 실제 수집 경로는 `build_ax_join_payload` 가 항상 채운다.
    capture_stack: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ax_join_version": self.ax_join_version,
            "collector_sha256": dict(self.collector_sha256),
            "capture_stack": dict(self.capture_stack),
            "ax_nodes_total": self.ax_nodes_total,
            "full_ax_compared": self.full_ax_compared,
            "source_features": list(self.source_features),
            "stats": dict(self.stats),
            "notes": list(self.notes),
            "entries": [e.as_dict() for e in self.entries],
        }


# ── selector 수집 (순수) ─────────────────────────────────────────────────────


def probe_selectors(
    probe: Mapping[str, Any],
    *,
    features: Sequence[str] = DEFAULT_SELECTOR_FEATURES,
    extra_selectors: Iterable[str] = (),
) -> list[str]:
    """probe 산출물에서 조인 대상 selector 를 문서 순서로 모은다 (중복 제거).

    `probe` 는 `l0_probe.js` 의 반환값 전체(`{"raw_features": {...}}`)도, raw_features
    자체도 받는다 — 호출자가 어느 쪽을 들고 있든 같은 결과가 나와야 한다.
    """
    raw = probe.get("raw_features") if isinstance(probe.get("raw_features"), Mapping) else probe
    seen: dict[str, None] = {}
    for key in features:
        rows = raw.get(key) if isinstance(raw, Mapping) else None
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            sel = row.get("selector")
            if isinstance(sel, str) and sel:
                seen.setdefault(sel, None)
    for sel in extra_selectors:
        if isinstance(sel, str) and sel:
            seen.setdefault(sel, None)
    return list(seen)


# ── AX 색인 (순수) ───────────────────────────────────────────────────────────


def index_ax_nodes(ax_nodes: Sequence[Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    """slim node 들을 `backendDOMNodeId` 로 색인한다.

    같은 backendDOMNodeId 가 두 번 나오면 **먼저 나온 것**을 쓴다. AX tree 는 문서 순서라
    먼저 나온 쪽이 그 DOM 노드의 주 노드다. 뒤엣것으로 덮으면 조용히 값이 바뀐다.
    """
    out: dict[int, dict[str, Any]] = {}
    for node in ax_nodes:
        if not isinstance(node, Mapping):
            continue
        bid = node.get("backendDOMNodeId")
        if isinstance(bid, bool) or not isinstance(bid, int):
            continue
        out.setdefault(bid, dict(node))
    return out


# ── 조인 (순수) ──────────────────────────────────────────────────────────────


def join_resolutions(
    resolutions: Sequence[SelectorResolution],
    ax_index: Mapping[int, Mapping[str, Any]],
    *,
    full_ax_backend_ids: Iterable[int] | None = None,
) -> list[AxJoinEntry]:
    """해소된 selector 들을 AX 색인에 붙인다.

    `full_ax_backend_ids` 는 slim 필터 **이전**의 backendDOMNodeId 집합이다. 주면 부재
    사유를 `FILTERED_FROM_AX_JSON` 과 `NOT_IN_AX_TREE` 로 가른다. 주지 않으면 가르지
    않고 `ABSENCE_UNCLASSIFIED` 를 남긴다 — 모르는 것을 안다고 적지 않는다.
    """
    full_ids = set(full_ax_backend_ids) if full_ax_backend_ids is not None else None

    counts: dict[int, int] = {}
    for r in resolutions:
        if r.backend_dom_node_id is not None:
            counts[r.backend_dom_node_id] = counts.get(r.backend_dom_node_id, 0) + 1

    entries: list[AxJoinEntry] = []
    for r in resolutions:
        notes: list[str] = []
        if r.selector_invalid:
            notes.append(Note.SELECTOR_INVALID)
        if r.match_count is not None and r.match_count > 1:
            notes.append(Note.SELECTOR_AMBIGUOUS)

        bid = r.backend_dom_node_id
        if bid is None:
            notes.append(Note.AX_NODE_ABSENT)
            notes.append(Note.DOM_NO_MATCH if (r.match_count == 0) else Note.BACKEND_ID_UNRESOLVED)
            entries.append(
                AxJoinEntry(
                    selector=r.selector,
                    backend_dom_node_id=None,
                    ax_node=None,
                    join_status=JoinStatus.DOM_NODE_UNRESOLVED,
                    match_count=r.match_count,
                    notes=tuple(notes),
                )
            )
            continue

        if counts.get(bid, 0) > 1:
            notes.append(Note.BACKEND_ID_COLLISION)

        node = ax_index.get(bid)
        if node is None:
            notes.append(Note.AX_NODE_ABSENT)
            if full_ids is None:
                notes.append(Note.ABSENCE_UNCLASSIFIED)
            elif bid in full_ids:
                notes.append(Note.FILTERED_FROM_AX_JSON)
            else:
                notes.append(Note.NOT_IN_AX_TREE)
            entries.append(
                AxJoinEntry(
                    selector=r.selector,
                    backend_dom_node_id=bid,
                    ax_node=None,
                    join_status=JoinStatus.AX_NODE_ABSENT,
                    match_count=r.match_count,
                    notes=tuple(notes),
                )
            )
            continue

        if node.get("ignored") is True:
            notes.append(Note.AX_NODE_IGNORED)
        entries.append(
            AxJoinEntry(
                selector=r.selector,
                backend_dom_node_id=bid,
                ax_node=dict(node),
                join_status=JoinStatus.JOINED,
                match_count=r.match_count,
                notes=tuple(notes),
            )
        )
    return entries


def _stats(entries: Sequence[AxJoinEntry]) -> dict[str, Any]:
    total = len(entries)
    by_status: dict[str, int] = {
        JoinStatus.JOINED: 0,
        JoinStatus.AX_NODE_ABSENT: 0,
        JoinStatus.DOM_NODE_UNRESOLVED: 0,
    }
    computed = 0
    nonempty = 0
    for e in entries:
        by_status[e.join_status] = by_status.get(e.join_status, 0) + 1
        if e.join_status == JoinStatus.JOINED:
            node = e.ax_node or {}
            name = node.get("name")
            if node.get("name_computed") is True and isinstance(name, str):
                # 계산이 **일어났다**. 빈 문자열도 계산 결과다 (`A2 §1.6` NAME_ABSENT 와
                # NAME_EMPTY 는 다른 상태다).
                computed += 1
                if name.strip():
                    nonempty += 1
    joined = by_status[JoinStatus.JOINED]
    return {
        "selectors_total": total,
        "joined": joined,
        # 미측정을 0 으로 쓰지 않는다 — 대상이 0개면 성공률은 정의되지 않는다.
        "join_rate": round(joined / total, 6) if total else None,
        # "이름 계산이 일어났다" 와 "이름이 비어 있지 않다" 는 다른 수다. 합치면
        # `ICON_ONLY_AX_NAMED` 와 `ICON_ONLY_UNNAMED` 를 가르는 바로 그 정보가 사라진다.
        "joined_with_ax_name_computed": computed,
        "joined_with_nonempty_ax_name": nonempty,
        "ax_name_computed_rate": round(computed / total, 6) if total else None,
        "nonempty_ax_name_rate": round(nonempty / total, 6) if total else None,
        "by_status": by_status,
    }


def build_ax_join_payload(
    resolutions: Sequence[SelectorResolution],
    ax_nodes: Sequence[Mapping[str, Any]],
    *,
    full_ax_backend_ids: Iterable[int] | None = None,
    source_features: Sequence[str] = DEFAULT_SELECTOR_FEATURES,
    package_root: Path | None = None,
    notes: Sequence[str] = (),
) -> AxJoinPayload:
    ax_index = index_ax_nodes(ax_nodes)
    ids = None if full_ax_backend_ids is None else list(full_ax_backend_ids)
    entries = join_resolutions(resolutions, ax_index, full_ax_backend_ids=ids)
    return AxJoinPayload(
        ax_join_version=AX_JOIN_VERSION,
        collector_sha256=collector_sha256(package_root),
        capture_stack=capture_stack(package_root),
        entries=tuple(entries),
        stats=_stats(entries),
        notes=tuple(notes),
        ax_nodes_total=len(ax_index),
        full_ax_compared=ids is not None,
        source_features=tuple(source_features),
    )


# ── 하류(W5C) 로 넘기는 형태 ─────────────────────────────────────────────────


def selector_ax_index(
    payload: AxJoinPayload | Mapping[str, Any],
) -> dict[str, dict[str, Any] | None]:
    """`{selector: ax_node or None}`.

    조인 실패한 selector 도 **키로 남는다.** W5C `surface.py` 는 `"ax_node" in
    task_control` 로 "호출자가 알려주지 않았다" 와 "AX 에 없다" 를 가르므로, 조인을
    시도했으나 실패한 것은 키를 두고 값을 `None` 으로 줘야 그 구분이 유지된다.
    """
    rows = payload.entries if isinstance(payload, AxJoinPayload) else payload.get("entries", [])
    out: dict[str, dict[str, Any] | None] = {}
    for row in rows:
        if isinstance(row, AxJoinEntry):
            out[row.selector] = dict(row.ax_node) if row.ax_node is not None else None
        elif isinstance(row, Mapping):
            sel = row.get("selector")
            node = row.get("ax_node")
            if isinstance(sel, str):
                out[sel] = dict(node) if isinstance(node, Mapping) else None
    return out


def task_control_ax_field(
    payload: AxJoinPayload | Mapping[str, Any], selector: str
) -> dict[str, Any]:
    """W5C `measure_surface(task_control=...)` 에 합칠 조각.

    조인을 시도한 selector 면 `{"ax_node": node_or_None}` 을, 아예 시도하지 않은
    selector 면 **빈 dict** 를 돌려준다. 후자에 `{"ax_node": None}` 을 주면 "찾아봤는데
    없다" 로 읽혀 divergence 판정을 오염시킨다.
    """
    index = selector_ax_index(payload)
    if selector not in index:
        return {}
    return {"ax_node": index[selector]}


# ── CDP 경로 ─────────────────────────────────────────────────────────────────


class CDPLike(Protocol):
    """Playwright sync `CDPSession` 중 이 모듈이 쓰는 부분만."""

    def send(self, method: str, params: dict[str, Any] | None = None) -> Any: ...


_COUNT_JS = """
(function () {
  var SEL = __SELECTORS__;
  return SEL.map(function (s) {
    try { return document.querySelectorAll(s).length; } catch (e) { return -1; }
  });
})()
"""

_ELEMENTS_JS = """
(function () {
  var SEL = __SELECTORS__;
  return SEL.map(function (s) {
    try { var els = document.querySelectorAll(s); return els.length ? els[0] : null; }
    catch (e) { return null; }
  });
})()
"""


def _expr(template: str, selectors: Sequence[str]) -> str:
    return template.replace("__SELECTORS__", json.dumps(list(selectors)))


def resolve_selectors(cdp: CDPLike, selectors: Sequence[str]) -> list[SelectorResolution]:
    """selector 들을 살아 있는 문서에서 backendDOMNodeId 로 해소한다.

    CDP 왕복은 selector 수 + 3 회다. element 배열을 **한 번의 `Runtime.evaluate`** 로
    만들고 `Runtime.getProperties` 로 handle 을 한 번에 받은 뒤, handle 당
    `DOM.describeNode` 하나만 보낸다.
    """
    if not selectors:
        return []

    cdp.send("DOM.enable", {})
    # nodeId 공간을 연다. describeNode 는 objectId 로도 동작하지만 문서를 먼저 얻어 두는
    # 편이 구현체 차이에 안전하다.
    cdp.send("DOM.getDocument", {"depth": 0})

    counts_res = cdp.send(
        "Runtime.evaluate",
        {"expression": _expr(_COUNT_JS, selectors), "returnByValue": True},
    )
    raw_counts = ((counts_res or {}).get("result") or {}).get("value") or []
    counts: list[int | None] = []
    for i in range(len(selectors)):
        v = raw_counts[i] if i < len(raw_counts) else None
        counts.append(v if isinstance(v, int) and not isinstance(v, bool) else None)

    els_res = cdp.send(
        "Runtime.evaluate",
        {"expression": _expr(_ELEMENTS_JS, selectors), "returnByValue": False},
    )
    array_object_id = ((els_res or {}).get("result") or {}).get("objectId")

    object_ids: dict[int, str] = {}
    if array_object_id:
        props = cdp.send(
            "Runtime.getProperties",
            {"objectId": array_object_id, "ownProperties": True},
        )
        for prop in (props or {}).get("result") or []:
            name = prop.get("name")
            if not isinstance(name, str) or not name.isdigit():
                continue
            oid = ((prop.get("value") or {}) or {}).get("objectId")
            if isinstance(oid, str) and oid:
                object_ids[int(name)] = oid

    out: list[SelectorResolution] = []
    for i, sel in enumerate(selectors):
        count = counts[i]
        invalid = count == -1
        backend: int | None = None
        oid = object_ids.get(i)
        if oid:
            try:
                described = cdp.send("DOM.describeNode", {"objectId": oid})
            except Exception:
                described = None
            node = (described or {}).get("node") or {}
            bid = node.get("backendNodeId")
            if isinstance(bid, int) and not isinstance(bid, bool):
                backend = bid
        out.append(
            SelectorResolution(
                selector=sel,
                backend_dom_node_id=backend,
                match_count=(None if invalid else count),
                selector_invalid=invalid,
            )
        )

    if array_object_id:
        # 해제 실패는 관측을 바꾸지 않는다 - 컨텍스트가 곧 닫히고 handle 도 함께 사라진다.
        with contextlib.suppress(Exception):
            cdp.send("Runtime.releaseObject", {"objectId": array_object_id})
    return out


def full_ax_backend_ids(cdp: CDPLike) -> list[int]:
    """slim 필터 **이전**의 AX 노드가 가리키는 backendDOMNodeId 전부.

    부재 사유를 `FILTERED_FROM_AX_JSON` 과 `NOT_IN_AX_TREE` 로 가르기 위해서만 쓴다.
    조인되는 `ax_node` 값 자체는 언제나 `ax.json` 에 저장된 slim node 에서 온다 —
    증거 파일과 조인 산출물이 서로 다른 트리를 말하면 안 된다.
    """
    cdp.send("Accessibility.enable", {})
    nodes = (cdp.send("Accessibility.getFullAXTree", {}) or {}).get("nodes") or []
    ids: list[int] = []
    for n in nodes:
        bid = n.get("backendDOMNodeId")
        if isinstance(bid, int) and not isinstance(bid, bool):
            ids.append(bid)
    return ids


def collect_ax_join(
    cdp: CDPLike,
    *,
    probe: Mapping[str, Any],
    ax_nodes: Sequence[Mapping[str, Any]],
    features: Sequence[str] = DEFAULT_SELECTOR_FEATURES,
    extra_selectors: Iterable[str] = (),
    classify_absence: bool = True,
    package_root: Path | None = None,
) -> AxJoinPayload:
    """살아 있는 페이지에서 조인 산출물을 만든다.

    `ax_nodes` 는 **이미 수집돼 `l0a/ax.json` 에 저장된** slim node 를 그대로 받는다.
    여기서 AX 트리를 다시 뜨지 않는 이유는 하나다 — 증거 파일이 말하는 트리와 조인이
    말하는 트리가 갈리면 그 조인은 증거를 설명하지 못한다.
    """
    selectors = probe_selectors(probe, features=features, extra_selectors=extra_selectors)
    notes: list[str] = []
    resolutions = resolve_selectors(cdp, selectors)

    ids: list[int] | None = None
    if classify_absence:
        try:
            ids = full_ax_backend_ids(cdp)
        except Exception as exc:  # 대조 실패는 조인 실패가 아니다
            notes.append(f"{Note.ABSENCE_UNCLASSIFIED}: {type(exc).__name__}")
            ids = None

    return build_ax_join_payload(
        resolutions,
        ax_nodes,
        full_ax_backend_ids=ids,
        source_features=features,
        package_root=package_root,
        notes=notes,
    )
