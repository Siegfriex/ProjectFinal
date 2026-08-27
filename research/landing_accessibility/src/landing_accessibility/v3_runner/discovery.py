"""V3 task-specific candidate discovery + Scout 바인딩 — `T-B-V3-STEP1-001` → W5D1.

## 범위 (Director 오케스트레이션 지침 — worker 당 narrow responsibility 하나)

이 파일 **하나만** W5D1 소유다. 병렬로 도는 다른 lane(W5A 계약 로더, W5B flow 정규화,
W5C surface 측정, W5D obstruction/terminal, W5E fixture 13종)의 파일은 여기서
만들지도 참조하지도 않는다 — `v3_runner/contracts.py`가 아직 없으므로 `task_contract`
파라미터는 **구조적 타입(duck typing)** 으로만 받는다(`TaskContractLike` 참고).
W5A 의 실제 dataclass 가 이 shape 을 만족하면 import 없이 그대로 맞물린다.

## 대표기능을 추론하지 않는다

`T-A-V3-SUPERSEDE-001` — RF 7-way classifier 는 v3 main critical path 에서
퇴역했다. 이 모듈의 어떤 함수도 candidate 의 "task label"을 추론·부여하지
않는다. 입력에 이미 `frozen_task`/`endpoint_contract`가 동결돼 들어오고,
`discover_task_candidates`는 구조적으로 관측 가능한 candidate 를 **열거·랭킹**
할 뿐이다 — 어떤 candidate가 "그 task 의 진짜 버튼인가"를 판정하지 않는다.
그 판정은 Scout 의 BFS 가 endpoint_contract 를 실제로 만족하는 경로를 찾는가로
사후에 결정된다(`03 §5` Scout → Freeze → Replay).

## Scout 바인딩 — freeze 를 건드리지 않는다

`engine/l1_engine.py`(Scout·Path Freeze·`replay()`)는 **W2 소유·`b28aaa5`
NOT_PASSED freeze** 다. `T-A-V3-SUPERSEDE-001`이 W2 코드 삭제 금지·freeze
유지를 명시했으므로 이 파일은 그 파일을 **한 글자도 고치지 않고** import 로만
읽는다. `run_task_aware_scout()`가 그 바인딩이다 — `TaskDefinition`을
`task_contract`로부터 만들어 **기존 `Scout`를 그대로** 호출한다(`e001_runner.
executor.default_task_definition`/`run_l1_if_safe`와 같은 패턴, V2 TargetSpec
대신 V3 task_contract 를 쓴다는 것만 다르다).

**한계 — 문서로 남긴다(설계 제약, "불가능하면 왜 불가능한지 적고 멈춰라")**:
`Scout._activation_candidates`(BFS 내부 tie-break)는 `l0_collector.min4_sort_key`
를 **하드코딩**해 호출한다(l1_engine.py 안에서 직접, 인자로 주입받지 않는다).
그 파일을 고치지 않는 한 Scout 내부의 실제 분기 순서를 이 모듈이 갈아끼울 수
없다 — **불가능하다.** 그래서 이 모듈의 `policy` 인자는 (1) `discover_task_
candidates`가 돌려주는 evidence용 랭킹에 적용되고, (2) Scout 자신의 BFS 에는
적용되지 않는다. 오늘은 두 랭킹이 항상 같다 — `policy` 기본값이 `min4_sort_key`
그 자체를 감싼 것이고 Scout 도 같은 함수를 쓰기 때문이다. A 가 `ruling_10`으로
"경로선택 규칙이 전 target 에 균일해야 한다"를 요구했는데, 지금 상태(Scout 가
하드코딩된 MIN-4 만 씀)가 이미 그 요구를 만족한다 — 모든 target 이 예외 없이
같은 규칙을 강제로 쓴다. `policy` 인터페이스는 (a) A 가 MIN 승계를 확정하지
않고 다른 규칙을 정할 경우를 위한 자리, (b) 언젠가 task-aware Scout 가 freeze
파일을 대체하며 실제로 주입 가능해질 때의 어댑터 경계로 남겨 둔다.

## 안전 — guard 를 그대로 쓴다

`e001_runner.guard`(내 소유)의 `ActionCategory`·`CandidateActionState`·
`blocking_state`·`DISABLED_OR_INERT`·`assess_reachable_candidates`를 새로
만들지 않고 그대로 재사용한다. 금지 행위 후보(credential·transaction·CAPTCHA
등)는 **존재는 evidence 로 남기고 활성화만 차단**한다(`D-R0-06`). 이 경계를
넘는 새 판정 로직을 여기서 만들지 않는다 — guard.py 가 유일한 정본이다.
"""

from __future__ import annotations

import dataclasses
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

_RESEARCH_ROOT = Path(__file__).resolve().parents[3]
if str(_RESEARCH_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_RESEARCH_ROOT / "src"))

from enum import StrEnum  # noqa: E402

from landing_accessibility.e001_runner.guard import (  # noqa: E402
    ActionRisk,
    CandidateActionState,
    assess_reachable_candidates,
    classify_candidate_state,
)
from landing_accessibility.engine.evidence import EvidenceRun  # noqa: E402
from landing_accessibility.engine.firewall import ExecutionMode  # noqa: E402
from landing_accessibility.engine.l0_collector import (  # noqa: E402
    FixtureTarget,
    L0Collector,
    min4_sort_key,
)
from landing_accessibility.engine.l1_engine import (  # noqa: E402
    Scout,
    ScoutBudget,
    TaskDefinition,
    TaskEntry,
    TaskManifest,
)
from landing_accessibility.engine.vocabulary import (  # noqa: E402
    InteractionArchetype,
    RegionSignalType,
)

from .tiebreak import (  # noqa: E402
    TASK_BINDING_CANDIDATE_SOURCE_ABSENT,
    V3_TIEBREAK_TOTAL_ORDER,
    v3_tiebreak_sort_key,
)


# ══════════════════════════════════════════════════════════════════════════
# task_contract — duck-typed. W5A 의 `contracts.py` 가 아직 없다.
# ══════════════════════════════════════════════════════════════════════════
@runtime_checkable
class TaskContractLike(Protocol):
    """`SSOTV3/02_DATA_SCHEMA_v3.0.md` `dim_task_contract`와 같은 필드 이름을
    쓴다 — W5A 의 실제 dataclass 가 이 이름을 쓰면 import 없이 구조적으로
    맞물린다(structural typing). 이 모듈은 이 Protocol 을 **강제하지 않는다**
    (아래 함수들은 `Mapping`도 받는다) — 최소 계약을 문서화하는 용도다.
    """

    task_id: str
    endpoint_contract: Any
    fixture_json: str
    #: `dim_task_family.legacy_archetype` — v3 는 archetype 을 추론하지 않고
    #: 동결된 값을 그대로 옮긴다(RF 7-way 미사용, `T-A-V3-SUPERSEDE-001`).
    legacy_archetype: str


TaskContract = TaskContractLike | Mapping[str, Any]


def _tc_get(task_contract: TaskContract, key: str, default: Any = None) -> Any:
    """`task_contract`가 dataclass 든 dict 든 같은 방식으로 읽는다."""
    if isinstance(task_contract, Mapping):
        return task_contract.get(key, default)
    return getattr(task_contract, key, default)


def _resolve_endpoint_contract(
    raw: Any,
) -> tuple[str | None, RegionSignalType]:
    """`endpoint_contract`는 SSOT 어디에도 내부 shape 이 분해돼 있지 않다
    (`02_DATA_SCHEMA_v3.0.md`·`03_COLLECTION_MEASUREMENT_SPEC_v3.0.md` 둘 다
    opaque blob 으로만 쓴다) — 그래서 이 함수가 **관대하게** 두 형태를 받는다:

    - 문자열 — 그대로 `endpoint_definition`, `signal_type`은 `TaskDefinition`
      기본값(`DOM_AX_ROLE`)을 쓴다.
    - `{"definition": ..., "signal_type": ...}` 매핑 — 둘 다 명시적으로 읽는다.

    W5A 의 `contracts.py`가 실제 shape 을 확정하면 이 함수만 바뀌면 된다 —
    나머지 파이프라인은 `TaskDefinition`만 보고 그 앞단을 모른다.
    """
    if raw is None:
        return None, RegionSignalType.CODEBOOK_PENDING
    if isinstance(raw, Mapping):
        definition = raw.get("definition")
        signal_raw = raw.get("signal_type")
        try:
            signal_type = (
                RegionSignalType(signal_raw) if signal_raw else RegionSignalType.DOM_AX_ROLE
            )
        except ValueError:
            signal_type = RegionSignalType.CODEBOOK_PENDING
        return (str(definition) if definition else None), signal_type
    return str(raw), RegionSignalType.DOM_AX_ROLE


def bind_task_definition(task_contract: TaskContract) -> TaskDefinition:
    """`task_contract`(V3, 동결)로 `TaskDefinition`(l1_engine.py, W2 소유·읽기전용)을
    만든다 — Scout 가 이해하는 유일한 입력 형태이므로, V3 계약을 Scout 에
    맞물리려면 이 변환이 있어야 한다.

    `region_definition`은 V3 계약에 대응 개념이 없다(V3 는 endpoint_contract
    만 갖는다, `03 §4`) — `None`으로 둔다. `TaskDefinition.mapping_frozen_
    allowed()`는 그래서 `region_signal_type`이 채워지지 않는 한 `False`이고,
    `NED` 는 이 경로에서 항상 `NULL`이 된다 — 지어내지 않는다(`D-R0-09`와 같은
    원칙). endpoint_contract 는 존재하므로 v2 engine 의 IED/MPFED 산출 경로
    (`detect_endpoint_signal`)는 그대로 동작한다.

    .. note:: **`NED`/`IED`/`MPFED` 라는 이름의 뜻 — v2.1 의 것이고 v3 의 주장이 아니다.**

       **v2.1 에서** 이 이름들은 *"영역/endpoint 도달에 필요한 최소 activation 수"* 를
       뜻했다. 그 정의는 v2.1 의 것이며 **v3 는 그 주장을 하지 않는다** (`Δ36` ① —
       v3 의 탐색은 탐욕적 하강이고 최소성을 주장하지 않는다). `SSOTV3` 21 파일 어디에도
       이 세 이름의 정의가 없다(A 실측, `Δ37`).

       그래서 `Δ37` 이 판정했다 — v3 관측 행은 이 컬럼을 **`NULL`** 로 두고
       `legacy_depth_null_reason` 을 함께 싣는다(`runner.LEGACY_DEPTH_NULL_REASON`).
       위 문장의 "최소" 는 **v2.1 의 정의를 인용한 것**이지 v3 산출에 대한 진술이
       아니다 — 이 서술을 지우면 왜 `NULL` 인지가 코드에서 사라진다.
    """
    archetype_raw = _tc_get(task_contract, "legacy_archetype") or _tc_get(
        task_contract, "archetype"
    )
    if not archetype_raw:
        raise ValueError(
            "task_contract 에 legacy_archetype(또는 archetype)이 없다 — Scout 는 "
            "TaskDefinition.archetype 없이 gate 종류를 archetype 별로 가를 수 없다 "
            "(A2 §1.5.1a 규칙 E-6a). v3 도 이 값을 추론하지 않고 동결값을 그대로 옮긴다."
        )
    archetype = InteractionArchetype(archetype_raw)

    endpoint_definition, endpoint_signal_type = _resolve_endpoint_contract(
        _tc_get(task_contract, "endpoint_contract")
    )

    return TaskDefinition(
        task_id=str(_tc_get(task_contract, "task_id") or ""),
        archetype=archetype,
        region_definition=None,
        endpoint_definition=endpoint_definition,
        region_signal_type=RegionSignalType.CODEBOOK_PENDING,
        endpoint_signal_type=endpoint_signal_type,
    )


# ══════════════════════════════════════════════════════════════════════════
# 경로선택 정책 — 주입 가능. 기본값은 MIN-4(`min4_sort_key`, 읽기전용 재사용)
# ══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class PathSelectionPolicy:
    """`A1 §2.6` 규칙 MIN-4(전순서 tie-break)를 갈아끼울 수 있게 감싼 것.

    `name`은 evidence 에 어떤 정책을 썼는지 남기기 위한 것이다(A `ruling_10`
    — 경로선택 규칙이 전 target 에 균일해야 matched comparison 이 성립한다).
    `sort_key`는 `l0_collector.min4_sort_key`와 같은 시그니처
    (`dict[str, Any] -> tuple`, 오름차순 정렬 키)여야 한다.

    이 정책은 **`discover_task_candidates`의 랭킹에만** 적용된다. `Scout` 내부
    BFS 는 여전히 `min4_sort_key`를 하드코딩해서 쓴다(모듈 docstring "Scout
    바인딩 — 설계 제약" 참고) — 오늘은 두 값이 항상 같으므로 실제 동작에는
    차이가 없다.
    """

    name: str
    sort_key: Callable[[dict[str, Any]], tuple[Any, ...]]
    #: `Δ36` part4 — 선언된 전순서. path manifest 의 `candidate_nomination_rule` 이
    #: 이 값을 읽는다(`runner._observed_nomination_rule`). 비어 있으면 runner 는
    #: `NOT_OBSERVABLE_FROM_INJECTED_IMPLEMENTATION` 을 적는다 — 지어내지 않는다.
    total_order: tuple[str, ...] = ()


#: **v2 정책** — `min4_sort_key`를 그대로 감싼다(재구현하지 않는다). 1차 키가
#: `marked_primary` 라서 **v3 의 기본값이 아니다**(`Δ30` 이 그 키를 퇴역시켰다).
#: v2 산출과 대조할 때만 명시적으로 주입해서 쓴다.
MIN4_POLICY = PathSelectionPolicy(
    name="MIN-4",
    sort_key=min4_sort_key,
    total_order=("marked_primary desc", "dom_order asc", "selector asc"),
)

#: **v3 기본 정책** (`Δ30`) — `(task_binding_candidate desc, dom_order asc, selector asc)`.
#: `tiebreak.py` 가 정본이고 여기서는 감싸기만 한다. 1차 키 소스가 트리에 없다는 측정
#: 사실은 `TASK_BINDING_CANDIDATE_SOURCE_ABSENT` 에 적혀 있다.
V3_TIEBREAK_POLICY = PathSelectionPolicy(
    name="Δ30-V3-TIEBREAK",
    sort_key=v3_tiebreak_sort_key,
    total_order=V3_TIEBREAK_TOTAL_ORDER,
)

#: `Δ30` 승계 이후 v3 경로선택의 기본값. **`MIN4_POLICY` 가 아니다.**
DEFAULT_V3_PATH_POLICY = V3_TIEBREAK_POLICY


# ══════════════════════════════════════════════════════════════════════════
# fixture_input_mode (A Δ8-R5, 2026-08-28 확정) — SELECT_ORIGIN/DESTINATION/DATE
# 의 activation_depth 포함 여부를 가르는 관측 입력. `04_FLOW_CODEBOOK_v3.0.md`
# 원문 22필드 표가 동결된 뒤에 A 가 추가한 delta 라 그 문서에는 없다.
# ══════════════════════════════════════════════════════════════════════════
class FixtureInputMode(StrEnum):
    """A 규칙: "서비스가 먼저 제시하는 수단을 쓴다 — 수집자가 고르지 않는다."
    닫힌 집합이다 — 이 다섯 값 밖을 만들지 않는다."""

    FREE_TEXT = "FREE_TEXT"
    DROPDOWN = "DROPDOWN"
    MIXED = "MIXED"
    MAP_PAN = "MAP_PAN"
    OTHER = "OTHER"


def _infer_fixture_input_mode(candidate: Mapping[str, Any]) -> FixtureInputMode | None:
    """**구조 신호(tag/role/type)만** 본다 — candidate 가 어떤 task 용도인지는
    보지 않는다(모듈 상단 "대표기능을 추론하지 않는다"와 같은 이유: "OTHER 서비스는
    지도로 목적지를 고른다"를 라벨/문구로 추측하면 그건 관측이 아니라 대표기능
    추론의 재발이다). 신호가 전혀 없으면 `None`이다 — `OTHER`로 단정하지 않는다
    (`OTHER`는 "버튼/링크류로 관측됐지만 다섯 카테고리 중 더 좁게 구조적으로
    가를 수 없다"는 뜻이지 "모름"이 아니다).

    **known limitation** — `primary_action_candidates`(`discover_task_
    candidates`의 유일한 candidate source, 위 함수 docstring 참고) 쿼리는
    `input[type=submit|button]`만 잡고 일반 `<input type=text>`/`<select>`/
    지도 위젯(보통 스크립트가 그리는 `<div>`, 시맨틱 role 이 없는 경우가 흔하다)
    은 잡지 않는다. 그래서 `FREE_TEXT`/`DROPDOWN`/`MAP_PAN`은 **구조적으로
    거의 관측되지 않는다** — 실제로 관측되는 것은 그런 위젯을 여는 트리거
    button/link(`OTHER`) 인 경우가 대부분이다. 이 한계는 `discover_task_
    candidates`의 candidate-source 한계와 같은 근본 원인(`l0_probe.js` 읽기
    전용)이고 새로 만든 것이 아니다.
    """
    tag = str(candidate.get("tag") or "").strip().lower()
    role = str(candidate.get("role") or "").strip().lower()
    input_type = str(candidate.get("type") or candidate.get("input_type") or "").strip().lower()

    if role == "combobox":
        return FixtureInputMode.MIXED
    if tag == "select" or role in ("listbox", "menu"):
        return FixtureInputMode.DROPDOWN
    if tag == "input" and input_type not in (
        "submit",
        "button",
        "checkbox",
        "radio",
        "hidden",
    ):
        return FixtureInputMode.FREE_TEXT
    if role == "application" or "map" in tag:
        # 구조적으로 지도 위젯임이 명시된 경우만(role=application 은 흔치 않은
        # 명시적 신호) — 라벨/문구로 "지도"를 추측하지 않는다.
        return FixtureInputMode.MAP_PAN
    if tag in ("button", "a") or role in ("button", "link", "tab"):
        return FixtureInputMode.OTHER
    return None


# ══════════════════════════════════════════════════════════════════════════
# TaskCandidate — discovery 결과 한 건
# ══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class TaskCandidate(Mapping[str, Any]):
    """`discover_task_candidates`가 돌려주는 후보 하나. `raw`는 probe 원본을
    그대로 보존한다(존재 evidence, `D-R0-03`) — 이 dataclass 의 다른 필드는
    그 원본에서 뽑은 것일 뿐 새 관측이 아니다.

    ## `Mapping` 인 이유 (`Δ32` P0 시정)

    `runner.CandidateBinder.bind` 는 `Sequence[Mapping[str, Any]]` 를 선언하고,
    `runner.ScoutStrategy.propose_next` 와 `V3Runner.run` 의 `candidates` 도 같은
    타입이다 — **통합 소유자(W5F runner)가 세 자리에서 같은 계약을 선언**한다. 이
    클래스가 평범한 dataclass 이던 동안 `MinPathScoutStrategy.propose_next` 의
    `isinstance(c, Mapping)` 이 전건을 탈락시켰고, 결과는 예외도 refusal 도 없는
    **깨끗한 0-activation 행**이었다(`Δ32` 측정).

    **어느 쪽을 맞출지의 판단**: 선언된 계약(`Mapping`)이 이긴다. 근거 셋 —
    ① 계약이 세 자리에 선언돼 있고 구현은 한 자리다. ② `Mapping` 이 더 넓은 구조적
    타입이라 이 클래스가 그것을 만족해도 **어떤 소비자도 잃는 것이 없다**(dataclass
    속성 접근 `c.selector` 는 그대로 살아 있고, W5D1 자신의 테스트가 그것을 쓴다).
    ③ 반대로 `discover_task_candidates` 가 평범한 dict 를 내도록 바꾸면 `guard_state`
    ·`usable`·`rank`·`fixture_input_mode` 같은 파생 판정이 **타입 없는 문자열 키로
    흩어져** 소비자가 스키마를 다시 추측하게 된다 — 그건 계약을 넓히는 게 아니라 없애는
    것이다.

    Mapping view 는 `raw`(probe 원본) 키 위에 이 dataclass 의 필드를 덮어쓴 것이다.
    `in_list_container` 처럼 dataclass 필드가 아닌 probe 신호도 그대로 읽힌다 —
    `scout_strategy._classify_action_token` 이 그 키를 본다. `raw` 자신은 view 에
    넣지 않는다(자기 중첩 방지). **값을 새로 만들지 않는다** — 이 view 는 표현 변경일
    뿐 관측 추가가 아니다.
    """

    selector: str
    tag: str | None
    role: str | None
    aria_label: str | None
    visible_text: str | None
    dom_order: int
    marked_primary: bool
    hittable: bool | None
    enabled: bool | None
    #: `guard.classify_candidate_state`의 9-state 판정 — 존재는 항상 기록되고
    #: (`D-R0-03`), 활성화 차단 여부는 `usable`로 별도 표시한다.
    guard_state: CandidateActionState
    #: `guard_state`가 SAFE·AUTH_ENTRY_ALLOWED_CONDITIONALLY 일 때만 True —
    #: Scout 가 실제로 클릭을 시도해도 안전한 후보라는 뜻이다.
    usable: bool
    #: `policy.sort_key` 적용 후 순위(0-based). `BRANCHING_LIMIT` 절단선이
    #: 이 순서를 본다(Scout 자신의 순서와, 정책이 MIN-4 인 한 일치한다).
    rank: int
    #: A `Δ8-R5`(2026-08-28) — `SELECT_ORIGIN`/`DESTINATION`/`DATE` 의
    #: `activation_depth` 포함 여부를 가르는 관측 입력. 구조 신호만으로 판정하고
    #: (`_infer_fixture_input_mode`), 신호가 없으면 `None`이다(추측하지 않는다).
    fixture_input_mode: FixtureInputMode | None
    raw: dict[str, Any] = field(repr=False)

    # ── `Mapping` 구현 — 계약을 만족시키기 위한 읽기전용 view ──────────────
    def _mapping_view(self) -> dict[str, Any]:
        view: dict[str, Any] = dict(self.raw)
        for f in dataclasses.fields(self):
            if f.name == "raw":
                continue
            view[f.name] = getattr(self, f.name)
        return view

    def __getitem__(self, key: str) -> Any:
        return self._mapping_view()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._mapping_view())

    def __len__(self) -> int:
        return len(self._mapping_view())


_USABLE_STATES = frozenset(
    {CandidateActionState.SAFE, CandidateActionState.AUTH_ENTRY_ALLOWED_CONDITIONALLY}
)


def discover_task_candidates(
    probe_state: Mapping[str, Any],
    task_contract: TaskContract,
    policy: PathSelectionPolicy | None = None,
) -> list[TaskCandidate]:
    """`probe_state`(L0 raw_features, `L0Observation.raw_features`) 에서 task
    candidate 를 열거·guard 판정·랭킹한다. **대표기능을 추론하지 않는다** — 이
    함수는 candidate 의 "task label"을 정하지 않는다(모듈 docstring 참고).

    후보 source(`03 §4`): `primary_action_candidates`(l0_probe.js) 하나만
    쓴다 — 그 소스가 `dom_order`(MIN-4 tie-break 의 필수 구조값,
    `Min4ProbeContractError`)를 갖는 **유일한** raw feature 군이고, `Scout.
    _activation_candidates`가 실제로 분기하는 후보 집합과 정확히 같다.

    **known limitation** — `03 §4`가 나열한 candidate source(button/link/tab
    /**menuitem**/input/**searchbox**/card)는 `primary_action_candidates`
    쿼리(`a[href],button,input[type=submit|button],[role=button|link|tab],
    nav a`)보다 넓다. `menuitem`/`searchbox`/일반 텍스트 `input`은 `l0_probe.js`
    의 다른 raw feature 군(`utility_input_widgets`·`region_signals.search_
    inputs`)에 있지만 그것들은 `dom_order`를 갖지 않는다 — `l0_probe.js`는
    W2 소유·읽기전용이라 이 함수가 그 결측을 채워 넣지 않는다(값을 지어내면
    그게 조작이다). 그래서 이 함수의 candidate universe 는 `primary_action_
    candidates`로 좁다 — 그런데 이건 타협이 아니라 **Scout 와의 일치를
    보장하는 선택**이다: Scout 자신도 그 두 raw feature 군을 전혀 보지 않으므로,
    거기 있는 요소를 후보로 냈어도 Scout 는 절대 클릭할 수 없다.
    """
    resolved_policy = policy or DEFAULT_V3_PATH_POLICY
    raw_candidates = list(probe_state.get("primary_action_candidates") or [])

    ranked = sorted(raw_candidates, key=resolved_policy.sort_key)
    seen: set[str] = set()
    out: list[TaskCandidate] = []
    for rank, c in enumerate(ranked):
        if not isinstance(c, dict):
            continue
        sel = str(c.get("selector") or "")
        if not sel or sel in seen:
            continue
        seen.add(sel)
        state = classify_candidate_state(c)
        out.append(
            TaskCandidate(
                selector=sel,
                tag=c.get("tag"),
                role=c.get("role"),
                aria_label=c.get("aria_label"),
                visible_text=c.get("visible_text"),
                dom_order=int(c["dom_order"]),
                marked_primary=bool(c.get("marked_primary")),
                hittable=c.get("hittable"),
                enabled=c.get("enabled"),
                guard_state=state,
                usable=state in _USABLE_STATES,
                rank=rank,
                fixture_input_mode=_infer_fixture_input_mode(c),
                raw=c,
            )
        )
    return out


# ══════════════════════════════════════════════════════════════════════════
# `Δ36` ② — v3 는 v2 의 전순서로 고른 경로를 받지 않는다
# ══════════════════════════════════════════════════════════════════════════
class V3PathOrderDivergenceError(RuntimeError):
    """`Δ36` ② — v2 Scout 의 내부 전순서가 v3 의 전순서와 **갈리는** 후보 집합이다.

    ## 왜 예외인가 — 고칠 수 있는 자리가 여기뿐이다

    `[Δ36 인용]` *"`min4_sort_key` 의 1차 키를 바꾸면 v2 BFS 분기 순서가 바뀌어 v2 산출의
    재현성이 깨진다. 건드리지 않는다."* / *"v3 의 경로 선택은 v3 의 tiebreak 을 쓴다. …
    시정 방향은 v2 변경이 아니라 **v3 가 자기 것을 쓰게 하는 것**이다."*

    **B 실측**: `Scout._activation_candidates` 는 `@staticmethod` 이고 `min4_sort_key` 를
    본문에서 직접 부른다 — 인자로도 속성으로도 주입점이 없다. 그래서 "v3 가 자기 것을
    쓰게" 하는 방법은 두 가지뿐이다: (a) `l1_engine.py` 를 고친다 → `Δ36` 이 금지했다,
    (b) **v3 가 v2 순서로 고른 경로를 받지 않는다** → 이것이다.

    `[Δ36 인용]` *"`ruling_10` 위반 여부: **발산이 남으면 위반이다.**"* 그래서 조용히
    통과시키지 않는다. 발산하지 않는 후보 집합에서는 이 예외가 나지 않고 `Scout` 가
    그대로 돈다 — 두 순서가 같을 때 v2 경로를 쓰는 것은 v3 순서를 쓰는 것과 같다.

    ## 관측 손실이 아니다

    이 예외가 나도 `discover_task_candidates` 의 후보 열거와 guard 판정은 **이미 끝나
    있고**, 호출부가 그것을 받는다. 잃는 것은 v2 순서로 밟은 경로 하나뿐이다.
    """


def path_order_divergence(
    raw_candidates: Sequence[Mapping[str, Any]],
    *,
    policy: PathSelectionPolicy,
) -> tuple[list[str], list[str]] | None:
    """v2 전순서와 v3 전순서가 이 후보 집합에서 **갈리는가**. 갈리면 두 순서를 돌려준다.

    비교는 `selector` 열로 한다 — 두 정렬이 실제로 다른 후보를 1위로 올리는지가
    질문이고, 키 튜플의 모양이 아니다.

    `None` 이면 두 순서가 같다. 그때는 v2 Scout 을 타도 v3 가 골랐을 경로와 같은
    경로가 나온다 — `Δ36` 이 막는 발산이 성립하지 않는다.
    """
    usable = [dict(c) for c in raw_candidates if c.get("selector")]
    if len(usable) < 2:
        return None
    v2_order = [str(c["selector"]) for c in sorted(usable, key=min4_sort_key)]
    v3_order = [str(c["selector"]) for c in sorted(usable, key=policy.sort_key)]
    return None if v2_order == v3_order else (v2_order, v3_order)


# ══════════════════════════════════════════════════════════════════════════
# Scout 바인딩 — freeze(l1_engine.py) 를 읽기전용으로 호출한다
# ══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class TaskDiscoveryResult:
    """`run_task_aware_scout`의 반환값. `blocking`이 `None`이 아니면 `Scout`가
    **아예 만들어지지 않았다** — `entry`/`manifest`도 `None`이다(`D-R0-01`
    candidate/state-level 판정, `T-A-W1-001`과 같은 계약)."""

    task_id: str
    candidates: tuple[TaskCandidate, ...]
    blocking: ActionRisk | None
    entry: TaskEntry | None
    manifest: TaskManifest | None

    @property
    def scout_invoked(self) -> bool:
        return self.blocking is None


def run_task_aware_scout(
    task_contract: TaskContract,
    *,
    fixture_root: Path,
    run: EvidenceRun,
    budget: ScoutBudget | None = None,
    policy: PathSelectionPolicy | None = None,
) -> TaskDiscoveryResult:
    """L0 관측 → `discover_task_candidates` → guard 사전검사 → (통과 시) `Scout.
    scout()`. FIXTURE 전용이다 — `execution_mode`를 인자로 받지 않는다(이 lane
    은 offline 만, `T-B-V3-STEP1-001` 범위 축소: "실사이트 접속 0 유지").

    `guard.assess_reachable_candidates`(`T-A-W1-P2-DECIDED`와 완전히 같은
    함수)가 reachable 후보 전부가 forbidden/DISABLED_OR_INERT 면 **Scout를
    만들지 않는다** — `e001_runner.executor.run_l1_if_safe`와 정확히 같은
    안전 계약이다(그 함수를 재구현하지 않고 같은 guard 함수를 그대로 쓴다).
    """
    resolved_budget = budget or ScoutBudget()
    resolved_policy = policy or DEFAULT_V3_PATH_POLICY
    task_id = str(_tc_get(task_contract, "task_id") or "")
    fixture_name = str(
        _tc_get(task_contract, "fixture_json") or _tc_get(task_contract, "fixed_fixture") or ""
    )
    if not fixture_name:
        raise ValueError(
            f"task_contract(task_id={task_id!r}) 에 fixture_json(또는 fixed_fixture)이 "
            "없다 — 이 lane 은 FIXTURE 전용이라 열 파일이 없으면 진행할 수 없다."
        )

    task_definition = bind_task_definition(task_contract)

    collector = L0Collector(run, fixture_root=fixture_root, execution_mode=ExecutionMode.FIXTURE)
    observation = collector.collect(
        FixtureTarget(
            web_target_id=task_id, fixture=fixture_name, archetype=task_definition.archetype
        )
    )
    probe_state = observation.raw_features
    candidates = discover_task_candidates(probe_state, task_contract, resolved_policy)

    raw_candidates = list(probe_state.get("primary_action_candidates") or [])
    assessment = assess_reachable_candidates(
        raw_candidates, branching_limit=resolved_budget.branching_limit
    )
    if assessment.blocking is not None:
        return TaskDiscoveryResult(
            task_id=task_id,
            candidates=tuple(candidates),
            blocking=assessment.blocking,
            entry=None,
            manifest=None,
        )

    # `Δ36` ② — v2 Scout 의 하드코딩된 `min4_sort_key` 가 v3 전순서와 갈리는 후보
    # 집합이면 여기서 멈춘다. Scout 를 만들기 **전에** 본다 — 만든 뒤에 보면 이미 v2
    # 순서로 분기한 뒤다.
    divergence = path_order_divergence(raw_candidates, policy=resolved_policy)
    if divergence is not None:
        v2_order, v3_order = divergence
        raise V3PathOrderDivergenceError(
            f"task_id={task_id!r} fixture={fixture_name!r} 의 후보 집합에서 v2 Scout 의 "
            f"전순서와 v3 전순서({resolved_policy.name})가 갈린다. "
            f"v2(min4)={v2_order[:5]} / v3={v3_order[:5]}. "
            "Scout 내부 tie-break 은 l1_engine.py 에 하드코딩돼 있어 주입할 수 없고, "
            "그 파일은 v2 재현성 때문에 고치지 않는다 (Δ36 ②). v3 는 v2 순서로 고른 "
            "경로를 자기 산출로 받지 않는다 — 발산이 남으면 ruling_10 위반이다."
        )

    scout = Scout(
        fixture_root=fixture_root,
        budget=resolved_budget,
        execution_mode=ExecutionMode.FIXTURE,
        run=run,
    )
    entry, manifest = scout.scout(
        web_target_id=task_id, entry_fixture=fixture_name, task=task_definition
    )
    return TaskDiscoveryResult(
        task_id=task_id,
        candidates=tuple(candidates),
        blocking=None,
        entry=entry,
        manifest=manifest,
    )


__all__ = [
    "DEFAULT_V3_PATH_POLICY",
    "MIN4_POLICY",
    "TASK_BINDING_CANDIDATE_SOURCE_ABSENT",
    "V3_TIEBREAK_POLICY",
    "V3_TIEBREAK_TOTAL_ORDER",
    "FixtureInputMode",
    "PathSelectionPolicy",
    "TaskCandidate",
    "TaskContract",
    "TaskContractLike",
    "TaskDiscoveryResult",
    "V3PathOrderDivergenceError",
    "bind_task_definition",
    "discover_task_candidates",
    "path_order_divergence",
    "run_task_aware_scout",
]
