#!/usr/bin/env python
"""W4 — Axis C(Initial Obstruction) mart 빌더.

    python research/landing_accessibility/scripts/build_mart_axisc.py \\
        --out artifacts/mart_axisc

**이 스크립트는 네트워크에 접속하지 않고 브라우저를 열지 않는다.** 이미 디스크에 있는
`E001_FULL` L0 evidence(`probe.json` 등)를 **읽기 전용**으로 다시 읽어 mart 행을 만든다.

- `D-R0-24`: page-level `OverlayCoverage`는 기존 evidence 재사용(재측정·재계산 아님) —
  `axis_c_page_level_from_probe()`는 이미 저장된 스칼라만 필터링·max·count 한다.
- `D-R0-25`: semantic interrupt classification 은
  `deterministic rule → text/NLP → VLM → abstain` 순
  (`landing_accessibility.engine.l0_collector.classify_interrupt`, VLM 은 미구현·명시적 abstain).

## grain

한 행 = 한 `web_target_id`(= service) 의 E001_FULL 관측 시도 하나. task-level grain
(representative function 별 행)은 아직 만들지 않는다 — task definition wiring(W1)과
endpoint detector(W2)가 아직 복구 중이므로, `task_id`가 이 mart 에는 없다
(`task_id_status = "PENDING_TASK_BINDING"`).

## page-level 과 task-level 을 코드에서 분리한다 (Research Director 지시, 2026-08-27)

- `axis_c_page_level_from_probe()` 는 `modal_overlay_candidates`/`dismiss_control_candidates`/
  `body_scroll_lock` 안의 **이미 저장된 스칼라**만 읽고 집계(필터링·max·count)한다.
  두 geometry 를 새로 조합하는 계산(`box` vs `box` overlap 등)은 **절대 하지 않는다** —
  그것이 task-specific `PrimaryActionOcclusion` 이고, 이 함수의 코드 경로 안에 아예 없다.
- `primary_action_occlusion` 필드는 이 mart 전체에서 상수 `None` 이고,
  `primary_action_occlusion_status` 는 상수 `"PENDING_TASK_BINDING"` 이다.
  task binding(W1 wiring + W2 detector)이 끝나기 전까지 이 스크립트는 이 값을 만들 **능력이
  없다** — 이것을 `tests/test_w4_axisc_mart.py` 가 구조적으로 증명한다.

## 4층 모집단 프레임 (`T-A-FINDING-001` F-A1, `D-R0-28`)

denominator 를 하드코딩하지 않는다. `E001_MASTER_PLAN.json.frozen_collection_order`
(59 개 서비스명, freeze 된 1차 소스)에서 attempted 를 읽고, `.agent_worktrees/
claude_b_e001_worker_0*/artifacts/*/evidence/e001_full-wtg_*` 디렉터리를 스캔해
아래 4층을 **디스크에서 직접** 유도한다. **단일 n 을 쓰지 않는다** — 지표마다 맞는
분모가 다르므로 `compute_denominators()` 가 명명된 분모 dict 를 돌려주고, 이 파일 어디서도
`len(rows)` 를 그대로 "the" 분모로 쓰지 않는다.

```
attempted (frozen_collection_order)                       = 59
  stub(0 bytes, 실제 관측 없음) → population_status=UNOBSERVED_STUB
                                                            -   3  (samsung_internet_browser ·
                                                                    samsung_notes · samsung_wallet)
  ─────────────────────────────────────────────────────────
  evidence_bytes (= 예전에 "observed"라 부르던 것, in_main_population) =  56
    duplicate launch 로 제외된 추가 run
      → population_status=EXCLUDED_DUPLICATE_LAUNCH        -   4  (netflix · chrome · hyundai_card ·
                                                                    cashwalk, 각 2회 launch 중
                                                                    나중 것을 제외)
  ─────────────────────────────────────────────────────────
    canonical 관측 (denominator: "evidence_bytes")          =  56
      structural/degenerate 측정 실패
        → measurement_status=FAILED_EVIDENCE_INCOMPLETE     -   3  (coupang_eats[내용 불일치] ·
                                                                    shinhan_sol_bank[probe 없음] ·
                                                                    lotte_himart[probe 없음])
  ─────────────────────────────────────────────────────────
    MEASURED(denominator: "measured", axis_c 계산 가능)      =  53
```

`FAILED_EVIDENCE_INCOMPLETE` 3건은 **`UNDETERMINED` 로 유지**하고 `FAIL` 로 전이시키지
않는다(`D-R0-23`) — 측정 실패는 접근성 실패가 아니다. 이 3건의 판정 근거는 `T-A-FINDING-001`
(Claude A)이며, **파일 크기가 아니라 관측된 상호작용/콘텐츠 구조**로 확인됐다(A 는 자신의
초기 dom 크기 휴리스틱을 스스로 철회했다 — `coupang_eats` 132KB·`netflix/login` 676KB 처럼
큰 파일도 degenerate 였다). 이 mart 는 그 근거를 재현하지 않고 A 가 확인한 결과만 반영한다
(`KNOWN_DEGENERATE_CAPTURE`, 출처를 코드에 명시).

`wtg()` 해시는 `scripts/build_canonical_entities.py::wtg()` 와 **동일한 규약**
(`"wtg_" + sha256(web_target_key)[:16]`)이다 — 새 규약을 발명하지 않는다.

## L0 probe 의 하드 cap — `primary_action_candidates` 절단이 있다

`l0_probe.js`(W2 소유, 이 스크립트는 읽기만 한다)에 배열 상한이 있고, B 의 전수 조사
(n=58)에서 **실제로 절단이 관측됐다**:

B·C 독립 재계산이 일치해 아래 수치는 **확정**이다(n=58 probe.json 전수):

| raw_features 필드 | cap | 58건 중 cap 도달 | 이 mart 의 대응 |
|---|---|---|---|
| `primary_action_candidates` | 200 | 7건 | `pac_len`/`pac_truncated` 컬럼 |
| `accessible_name_sources` | 300 | 13건 | `ans_len`/`ans_truncated` 컬럼 |
| `target_size` | 300 | 6건 | `ts_len`/`ts_truncated` 컬럼 |
| `contrast` | 400 | 8건 | `contrast_len`/`contrast_at_400` 컬럼 |
| `motion.animated_elements` | 60 | ≥1건 | `anim_len`/`anim_truncated` 컬럼 (Axis C 판정에 안 씀, 참고용) |
| `modal_overlay_candidates` | cap 무관(관측 최대 44) | 0건 | 절단 없음 — **OverlayCoverage 는 안전** |
| `dismiss_control_candidates` | cap 무관(관측 최대 44) | 0건 | 절단 없음 |

**모든 cap 컬럼은 bool 이 아니라 개수(`*_len`) 자체를 먼저 남긴다** — cap 기준이 나중에
바뀌어도(실제로 `primary_action_candidates` 는 B/C 사이에서 7 vs 8 로 한 번 갈렸다가
스캐너 키 분리 오류로 확인돼 7 로 정정됐다) mart 를 다시 만들지 않고 재계산할 수 있다.

## slot 원자재 — `dom_body_empty`/`slot_disagreement` 는 **정의를 열어 둔다**

`T-A-LABEL-FROZEN-001` F-A3.1: NH 쌍에서 라벨러 두 명이 갈린 원인은 판단력 차이가 아니라
**어느 evidence slot 을 읽었는가**였다 — 한 명은 `dom.html`/`ax.json`(거의 빈 SPA
bootstrap: `computed_css.json` 길이 0, `ax.json` 길이 1)을 봤고 다른 한 명은 `probe.json`
(primary_action 24 · modal_overlay 15, 렌더된 뱅킹 메뉴)을 봤다. 이건 dom.html **byte 크기**
문제가 아니다 — 크기로 판정하는 방법은 A(F-A1b)와 코디네이터가 이미 폐기했다(가장 작은
1657 bytes 관측이 정상이었고, 4.7MB 관측(`band.us/about`)이 오히려 빈약했다).

이 mart 는 **원자재만 저장**한다 — `dom_bytes`·`dom_body_element_count`(computed_css.json
길이, 이미 저장된 스칼라의 재사용)·`ax_node_count`(ax.json 길이)·`probe_primary_action_n`
(=`pac_len`). `dom_body_empty`/`slot_disagreement` **자체는 항상 `None`** 이고
`*_status = "DEFINITION_PENDING_D_LAYER"` 로 남긴다 — 정의는 `T-B-RQ-D-001` Q3 의 D-layer
답변이 A/Director 승격을 받은 뒤에 정해진다. **W4 가 지금 임의 임계값으로 bool 을
확정하지 않는다.**

**`PrimaryActionOcclusion` 함의(문서화만, 지금 해결하지 않는다 — 어차피
`PENDING_TASK_BINDING`)**: `primary_action_candidates` 가 절단된 관측에서는 실제
representative-function primary action 이 목록 밖에 있을 수 있다. probe 가 `dom_order`
순으로 담으므로 "primary action 은 보통 상단이라 괜찮다"는 완화 가정이 가능하지만, **이는
검증되지 않은 가정이다** — task binding 을 구현할 때 `pac_truncated=True` 인 관측은 이 가정을
명시적으로 확인해야 한다.

**page-level(`OverlayCoverage`) 은 이 cap 과 무관하다** — `modal_overlay_candidates`/
`dismiss_control_candidates` 는 관측된 최댓값이 44로, 어떤 cap 후보보다도 훨씬 작다. 이
스크립트가 전수(axis_c 계산 대상 전원)를 다시 스캔해 확인한다(`verify_overlay_fields_not_capped()`).
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RESEARCH = Path(__file__).resolve().parents[1]
_WORKTREE_ROOT = RESEARCH.parents[1]  # .agent_worktrees/claude_b_w4 (이 워크트리 자신)
#: 실제 evidence 는 **다른** 워크트리(`claude_b_e001_worker_0*`)에 있다 — 그것들은 이
#: 워크트리의 하위가 아니라 `PROJECT_FINAL_ROOT/.agent_worktrees/` 의 형제 디렉터리다.
#: `PROJECT_FINAL_ROOT` 환경변수(세션에 자동 주입됨, `CLAUDE.md` 참고)를 우선 쓰고,
#: 없으면 이 워크트리 경로에서 유도한다.
PROJECT_ROOT = Path(os.environ.get("PROJECT_FINAL_ROOT", str(RESEARCH.parents[3])))
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.l0_collector import classify_interrupt  # noqa: E402
from landing_accessibility.engine.vocabulary import ClassificationStatus  # noqa: E402

MASTER_PLAN_PATH = RESEARCH / "shadow" / "e001_plan" / "E001_MASTER_PLAN.json"
#: `D-R0-55` — A 가 analysis frame archetype(prior 기준이냐 관측 기준이냐)을 명시적으로
#: 유보했다. 이 mart 는 어느 쪽으로도 확정하지 않고 둘 다 컬럼으로 남긴다.
#: `prior_archetype` 은 Layer P(SSOT §6.1) 후보값 — RF-DT 의 실행 산출물이 아니라
#: **읽기 전용으로 참조**하는 P-B prework 결과다(W1/A 소관, W4 는 만들지 않는다).
PRIOR_ARCHETYPE_CSV_PATH = (
    RESEARCH / "shadow" / "lane_b" / "state" / "representative_task_candidate_shadow.csv"
)
EVIDENCE_ROOT_GLOB = str(
    PROJECT_ROOT / ".agent_worktrees" / "claude_b_e001_worker_0*" / "artifacts" / "*" / "evidence"
)
_RUN_DIR_RE = re.compile(r"^e001_full-(wtg_[0-9a-f]{16})-(\d{4}-\d{2}-\d{2}T\d+Z)$")

#: 이미 B 의 CLEAN-0 조사로 확인된 3건의 unobserved target 의 archetype.
#: 별도 codebook 파일을 새로 읽지 않는다 — W4 브리핑에 이미 확인된 사실만 기록한다.
#: (task definition/archetype codebook 자체는 W1 소유이며 이 스크립트는 그것을 재발명하지 않는다.)
KNOWN_UNOBSERVED_ARCHETYPE: dict[str, str] = {
    "samsung_internet_browser": "QUERY",
    "samsung_notes": "UTILITY_ENTRY",
    "samsung_wallet": "FINANCIAL_ACTION_ENTRY",
}

#: `T-A-FINDING-001` — Claude A 가 관측된 상호작용/콘텐츠 구조로 확인한 measurement
#: 실패 3건. **W4 는 이 판정을 재현하지 않는다** — 파일 크기 휴리스틱은 A 가 이미
#: 폐기했다(F-A1b). W4 는 이 중 2건(probe 자체 부재)만 독립적으로 직접 확인했다
#: (`shinhan_sol_bank`/`lotte_himart` 는 `l0a/probe.json` 파일이 디스크에 없다 — grep 로 확인).
#: `coupang_eats` 는 probe.json 은 있지만 캡처된 콘텐츠가 실제 서비스 도메인과 다르다는
#: A 의 판정을 그대로 수용한다(W4 가 재현 검증하지 않음 — 아래 명시).
KNOWN_DEGENERATE_CAPTURE: dict[str, str] = {
    "coupang_eats": "STRUCTURAL_DEGENERATE_CAPTURE",  # A 확인, W4 미재현
    "shinhan_sol_bank": "PROBE_MISSING_EVIDENCE_INCOMPLETE",  # W4 직접 확인 (probe.json 없음)
    "lotte_himart": "PROBE_MISSING_EVIDENCE_INCOMPLETE",  # W4 직접 확인 (probe.json 없음)
}

#: B/C 독립 재계산 일치로 확정된 `l0_probe.js` 하드 cap (n=58 probe.json 전수).
#: `raw_features` 최상위 키만 담는다 — `animated_elements` 는 `motion` 아래 중첩이라
#: `_NESTED_PROBE_CAPS` 에 별도로 둔다.
KNOWN_PROBE_CAPS: dict[str, tuple[int, bool]] = {
    "primary_action_candidates": (200, True),
    "accessible_name_sources": (300, True),
    "target_size": (300, True),
    "contrast": (400, True),
}

#: 중첩 경로 cap. `l0_probe.js:262` `animated_elements .slice(0, 60)` — B 확인, 우선순위는
#: 낮지만(Axis C 판정에 쓰는 키 아님) 개수를 남겨 두면 나중에 재계산 가능하다.
_NESTED_PROBE_CAPS: dict[str, tuple[tuple[str, ...], int, bool]] = {
    "animated_elements": (("motion", "animated_elements"), 60, True),
}


def _get_nested(d: dict[str, Any], path: tuple[str, ...]) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


#: 이름 패턴 기반 **약한 힌트**일 뿐이다 — RF-DT archetype 판정이 아니다(W1/A 소관).
#: informative-missingness 분포를 서술하는 용도로만 쓴다(해석·인과 주장 없음).
_FINANCIAL_NAME_NEEDLES = ("bank", "card", "pay", "wallet", "himart", "cok")
_SAMSUNG_SYSTEM_APP_PREFIX = "samsung_"

#: W1/W2 소관 frame(target URL) 정의 결함 후보 — W4 는 고치지 않는다. `probe_url` 패턴
#: 기반 **약한 힌트**이며, 코디네이터가 직접 확인해 준 4건(band/about, netflix/login,
#: kakaotalk→kakaocorp.com, naver_map→navercorp.com)과 실제로 일치한다(아래에서 재확인).
_FRAME_DEFECT_URL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("/login", "LOGIN_WALL_NOT_LANDING"),
    ("corp.", "CORPORATE_INFO_PAGE_NOT_APP"),
    ("/about", "ABOUT_PAGE_NOT_LANDING"),
)


def wtg(web_target_key: str) -> str:
    """`build_canonical_entities.py::wtg()` 와 동일한 해시 규약."""
    return "wtg_" + hashlib.sha256(web_target_key.encode("utf-8")).hexdigest()[:16]


#: 실행 시점에 evidence 가 기록된 `web_target_id` 가 계획의 표시명과 달랐던 것으로
#: 보이는 2건(`build_canonical_entities.py` 의 entity 병합 관행과 일치하는 canonical
#: key 축약). W4 가 직접 확인한 사실만 적는다 — `wtg("naver_app")`/`wtg("gmarket_app")`
#: 에는 evidence 가 전혀 없고(stub 도 없음), `wtg("naver")`/`wtg("gmarket")` 에는 real
#: evidence(각각 probe.json 포함)가 있다. 이 치환을 적용해야만 `frozen_collection_order`
#: 59 개 전원이 **정확히 하나**의 evidence identity(stub 포함, 초과·누락 없음)에
#: 대응한다 — 치환 없이는 59 attempted 중 2건이 "미관측"으로 이중 집계되고 2개의 real
#: evidence run 이 어느 attempted 항목에도 속하지 않는 고아가 된다.
#: **이것은 population 정합만 보정한다** — service_name(계획의 원래 표시명)은 바꾸지
#: 않고, canonical entity/task wiring 자체는 고치지 않는다(W1 소관, G2 부류 결함).
_ATTEMPTED_NAME_ALIAS: dict[str, str] = {
    "naver_app": "naver",
    "gmarket_app": "gmarket",
}


def frame_defect_hint(url: str | None) -> str | None:
    """W1/W2 소관 frame 결함 후보 — **약한 URL 패턴 힌트**. W4 는 고치지 않고 플래그만 남긴다."""
    if not url:
        return None
    lowered = url.lower()
    for needle, tag in _FRAME_DEFECT_URL_PATTERNS:
        if needle in lowered:
            return tag
    return None


def informative_missingness_name_hint(service_name: str) -> str | None:
    """**이름 패턴 힌트일 뿐** — archetype 판정이 아니다. 분포 서술 전용."""
    if service_name.startswith(_SAMSUNG_SYSTEM_APP_PREFIX):
        return "SAMSUNG_SYSTEM_APP_NAME_PATTERN"
    if any(n in service_name for n in _FINANCIAL_NAME_NEEDLES):
        return "FINANCIAL_NAME_PATTERN"
    return None


# ── 1. 디스크에서 run 디렉터리 발견 (읽기 전용) ──────────────────────────────


@dataclass
class RunDirInfo:
    wtg_id: str
    run_id: str
    run_timestamp: str
    path: Path
    file_count: int
    observation_ids: list[str]
    probe_paths: dict[str, Path] = field(default_factory=dict)


def discover_run_dirs(evidence_root_glob: str = EVIDENCE_ROOT_GLOB) -> list[RunDirInfo]:
    """`e001_full-wtg_*` run 디렉터리를 전부 찾는다. 아무것도 열거나 수정하지 않는다."""
    infos: list[RunDirInfo] = []
    for evidence_dir in sorted(glob.glob(evidence_root_glob)):
        ev_path = Path(evidence_dir)
        if not ev_path.is_dir():
            continue
        for run_dir in sorted(ev_path.glob("e001_full-wtg_*")):
            if not run_dir.is_dir():
                continue
            m = _RUN_DIR_RE.match(run_dir.name)
            if not m:
                continue
            wtg_id, ts = m.group(1), m.group(2)
            files = [f for f in run_dir.rglob("*") if f.is_file()]
            obs_ids: list[str] = []
            run_json_path = run_dir / "run.json"
            if run_json_path.exists():
                try:
                    run_json = json.loads(run_json_path.read_text(encoding="utf-8"))
                    obs_ids = list(run_json.get("observations", []))
                except json.JSONDecodeError:
                    obs_ids = []
            probe_paths: dict[str, Path] = {}
            for oid in obs_ids:
                probe = run_dir / oid / "l0a" / "probe.json"
                if probe.exists():
                    probe_paths[oid] = probe
            infos.append(
                RunDirInfo(
                    wtg_id=wtg_id,
                    run_id=run_dir.name,
                    run_timestamp=ts,
                    path=run_dir,
                    file_count=len(files),
                    observation_ids=obs_ids,
                    probe_paths=probe_paths,
                )
            )
    return infos


def _manifest_field(run_dir: Path, relpath: str, field_name: str) -> Any:
    """manifest.jsonl 에서 `relpath` 행의 `field_name` 을 읽는다 — 파일을 다시 열거나
    재계산하지 않는다(append-only manifest 를 그대로 재사용, `02 §12`)."""
    manifest_path = run_dir / "manifest.jsonl"
    if not manifest_path.exists():
        return None
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if relpath not in line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("relpath") == relpath:
            return rec.get(field_name)
    return None


def _dom_sha256(run_dir: Path, observation_id: str) -> str | None:
    sha = _manifest_field(run_dir, f"{observation_id}/l0a/dom.html", "sha256")
    return str(sha) if sha else None


def _dom_bytes(run_dir: Path, observation_id: str) -> int | None:
    n = _manifest_field(run_dir, f"{observation_id}/l0a/dom.html", "bytes")
    return int(n) if n is not None else None


def _l0a_json_len(run_dir: Path, observation_id: str, filename: str) -> int | None:
    """`l0a/{filename}` 이 저장한 JSON 배열의 길이를 읽는다 — DOM/AX slot 원자재
    (`dom_body_element_count`/`ax_node_count`). **크기 임계값으로 empty 를 판정하지
    않는다** — 여기선 개수만 반환하고, 해석(`dom_body_empty`)은 만들지 않는다."""
    path = run_dir / observation_id / "l0a" / filename
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return len(data) if isinstance(data, list) else None


# ── 2. 모집단 재구성 — 하드코딩 없이 디스크 + 동결 계획에서 유도 ──────────────


def load_attempted_population(master_plan_path: Path = MASTER_PLAN_PATH) -> dict[str, str]:
    """`{wtg_id: service_name}` — `frozen_collection_order` 그대로, 재정렬하지 않는다.

    `web_target_id` 는 `_ATTEMPTED_NAME_ALIAS` 로 치환한 키에서 계산하지만
    `service_name`(표시명)은 계획 원문 그대로 남긴다 — 이름을 바꾸는 게 아니라
    evidence 조회 키만 실제 수집 identity 에 맞춘다.
    """
    plan = json.loads(master_plan_path.read_text(encoding="utf-8"))
    names = plan["frozen_collection_order"]
    return {wtg(_ATTEMPTED_NAME_ALIAS.get(name, name)): name for name in names}


def load_prior_archetype(csv_path: Path = PRIOR_ARCHETYPE_CSV_PATH) -> dict[str, str]:
    """`{wtg_id: interaction_archetype}` — `D-R0-55` prior 컬럼. Layer P(SSOT §6.1)
    산출물을 **읽기 전용으로 참조**한다(W1/A 소관 CSV, W4 는 archetype 을 만들지 않는다).

    `web_target_id` 로 직접 조인한다(이름 alias 추측이 필요 없다) — 이 CSV 는
    `frozen_collection_order` 59 개 전원을 이미 `wtg_id` 로 커버한다(W4 확인: 59/59).
    """
    import csv as _csv

    out: dict[str, str] = {}
    if not csv_path.exists():
        return out
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        for row in _csv.DictReader(fh):
            wid = row.get("web_target_id")
            archetype = row.get("interaction_archetype")
            if wid and archetype:
                out[wid] = archetype
    return out


def build_population_rows(
    attempted: dict[str, str], run_dirs: list[RunDirInfo]
) -> list[dict[str, Any]]:
    """서비스당 최소 1행 — observed 는 canonical 1행 + duplicate 는 별도 EXCLUDED 행.

    stub(빈 디렉터리, `file_count == 0`)는 **행에 넣지 않는다** — 그 target 이 진짜
    unobserved 인지, 첫 attempt 만 stub 이고 재시도가 성공했는지는 `real_runs` 유무로
    판단한다(stub 존재 자체는 population 판정에 관여하지 않는다).

    duplicate 그룹의 canonical 은 **가장 이른 launch** 를 쓴다 — "나중 launch 를 제외한다"
    (코디네이터 확인) 그대로다.
    """
    real_by_target: dict[str, list[RunDirInfo]] = {}
    for r in run_dirs:
        if r.file_count == 0:
            continue  # stub — 빈 디렉터리는 관측이 아니다
        real_by_target.setdefault(r.wtg_id, []).append(r)

    rows: list[dict[str, Any]] = []
    for wtg_id, name in attempted.items():
        group = sorted(real_by_target.get(wtg_id, []), key=lambda r: r.run_timestamp)
        if not group:
            rows.append(
                {
                    "web_target_id": wtg_id,
                    "service_name": name,
                    "population_status": "UNOBSERVED_STUB",
                    "in_main_population": False,
                    "excluded_reason": "UNOBSERVED",
                    "measurement_status": "UNOBSERVED",
                    "run_id": None,
                    "observation_id": None,
                    "probe_path": None,
                    "probe_available": False,
                    "dom_sha256": None,
                    "dom_bytes": None,
                    "dom_body_element_count": None,
                    "ax_node_count": None,
                }
            )
            continue

        canonical = group[0]
        duplicates = group[1:]
        canonical_obs = canonical.observation_ids[0] if canonical.observation_ids else None
        canonical_probe = canonical.probe_paths.get(canonical_obs) if canonical_obs else None
        rows.append(
            {
                "web_target_id": wtg_id,
                "service_name": name,
                "population_status": "OBSERVED",
                "in_main_population": True,
                "excluded_reason": None,
                "is_duplicate_launch_group": len(group) > 1,
                "duplicate_launch_excluded_count": len(duplicates),
                "run_id": canonical.run_id,
                "observation_id": canonical_obs,
                "probe_path": (str(canonical_probe) if canonical_probe else None),
                "probe_available": canonical_probe is not None,
                "dom_sha256": (
                    _dom_sha256(canonical.path, canonical_obs) if canonical_obs else None
                ),
                # ── slot 원자재 (T-A-LABEL-FROZEN-001 F-A3.1) — probe 유무와 무관하게
                # dom.html/ax.json/computed_css.json 은 L0-a 단계에서 항상 먼저 저장된다.
                "dom_bytes": (_dom_bytes(canonical.path, canonical_obs) if canonical_obs else None),
                "dom_body_element_count": (
                    _l0a_json_len(canonical.path, canonical_obs, "computed_css.json")
                    if canonical_obs
                    else None
                ),
                "ax_node_count": (
                    _l0a_json_len(canonical.path, canonical_obs, "ax.json")
                    if canonical_obs
                    else None
                ),
            }
        )
        for d in duplicates:
            d_obs = d.observation_ids[0] if d.observation_ids else None
            rows.append(
                {
                    "web_target_id": wtg_id,
                    "service_name": name,
                    "population_status": "EXCLUDED_DUPLICATE_LAUNCH",
                    "in_main_population": False,
                    "excluded_reason": "DUPLICATE_LAUNCH",
                    "measurement_status": "EXCLUDED_DUPLICATE_LAUNCH",
                    "canonical_run_id_kept": canonical.run_id,
                    "run_id": d.run_id,
                    "observation_id": d_obs,
                    "probe_path": None,
                    "probe_available": None,
                    "dom_sha256": (_dom_sha256(d.path, d_obs) if d_obs else None),
                    "dom_bytes": (_dom_bytes(d.path, d_obs) if d_obs else None),
                    "dom_body_element_count": (
                        _l0a_json_len(d.path, d_obs, "computed_css.json") if d_obs else None
                    ),
                    "ax_node_count": (_l0a_json_len(d.path, d_obs, "ax.json") if d_obs else None),
                }
            )
    return rows


# ── 3. Axis C page-level — 이미 저장된 스칼라만 읽고 집계 ────────────────────


def _dismiss_control_visible(control: dict[str, Any]) -> bool:
    """이미 probe 가 저장한 속성만 읽는다 — 새 geometry 계산 없음."""
    return bool(
        control.get("display") != "none"
        and control.get("visibility") != "hidden"
        and float(control.get("opacity") or 1) > 0.01
        and float(control.get("viewport_overlap_css_px2") or 0) > 0
        and bool(control.get("hittable"))
    )


def axis_c_page_level_from_probe(raw_features: dict[str, Any]) -> dict[str, Any]:
    """`D-R0-24` page-level 재사용. `modal_overlay_candidates`/`dismiss_control_candidates`/
    `body_scroll_lock` 의 **이미 계산된 스칼라**만 필터링·max·count 한다.

    **여기 없는 것**: `box` 대 `box` overlap, `primary_action_candidates` 와의 결합.
    그것은 task-specific `PrimaryActionOcclusion` 이고, task binding 이 끝나기 전에는
    이 함수 코드 경로 어디에도 존재하지 않는다(`tests/test_w4_axisc_mart.py` 가 증명한다).

    이 함수가 읽는 두 필드(`modal_overlay_candidates`/`dismiss_control_candidates`)는
    `l0_probe.js` 의 배열 cap 과 무관하다(관측 최대 44, cap 후보 200/300/400 보다 훨씬
    작다) — page-level `OverlayCoverage` 는 절단 영향이 없다.
    """
    modal_candidates = raw_features.get("modal_overlay_candidates") or []
    visible = [c for c in modal_candidates if c.get("visible")]

    interrupts: list[dict[str, Any]] = []
    tier_counts = {s.value: 0 for s in ClassificationStatus}
    for idx, cand in enumerate(visible):
        status, label = classify_interrupt(cand)  # 순수함수 — geometry 안 건드림 (D-R0-25)
        tier_counts[status.value] += 1
        interrupts.append(
            {
                "interrupt_index": idx,
                "selector": cand.get("selector"),
                # 아래 두 값은 probe.js 가 수집 시점에 이미 계산해 저장한 스칼라의
                # 그대로 복사본이다 — 여기서 다시 계산하지 않는다.
                "viewport_overlap_css_px2": cand.get("viewport_overlap_css_px2"),
                "viewport_coverage": cand.get("viewport_coverage"),
                "candidate_sources": list(cand.get("candidate_sources") or []),
                "classification_status": status.value,
                "final_label": label.value,
            }
        )

    overlay_coverage = max((c.get("viewport_coverage") or 0.0) for c in visible) if visible else 0.0

    dismiss_candidates = raw_features.get("dismiss_control_candidates") or []
    present_count = 0
    visible_count = 0
    for container in dismiss_candidates:
        controls = container.get("dismiss_control_candidates") or []
        if controls:
            present_count += 1
            if any(_dismiss_control_visible(c) for c in controls):
                visible_count += 1

    scroll_lock = raw_features.get("body_scroll_lock") or {}

    cap_flags: dict[str, dict[str, Any]] = {}
    for field_name, (cap, confirmed) in KNOWN_PROBE_CAPS.items():
        values = raw_features.get(field_name)
        n = len(values) if isinstance(values, list) else None
        cap_flags[field_name] = {
            "len": n,
            "cap": cap,
            "cap_confirmed_in_source": confirmed,
            "truncated": (n == cap) if n is not None else None,
        }
    for field_name, (path, cap, confirmed) in _NESTED_PROBE_CAPS.items():
        values = _get_nested(raw_features, path)
        n = len(values) if isinstance(values, list) else None
        cap_flags[field_name] = {
            "len": n,
            "cap": cap,
            "cap_confirmed_in_source": confirmed,
            "truncated": (n == cap) if n is not None else None,
        }

    # `D-R0-53` DECISION-1 — `cap_hit_<key>` bool 플래그를 키별로 남긴다. 개수(`*_len`)와
    # 함께 쓴다(코디네이터 지시): bool 만 있으면 cap 기준이 바뀔 때 재계산이 안 된다.
    cap_hit_flags = {f"cap_hit_{k}": v["truncated"] for k, v in cap_flags.items()}

    return {
        "interrupt_count_visible": len(visible),
        "overlay_coverage": overlay_coverage,
        "interrupts": interrupts,
        "classification_tier_counts": tier_counts,
        "body_scroll_locked": bool(scroll_lock.get("locked")),
        "dismiss_control_present_count": present_count,
        "dismiss_control_visible_count": visible_count,
        "modal_overlay_candidates_len": len(modal_candidates),
        "dismiss_control_candidates_len": len(dismiss_candidates),
        # ── probe cap 절단. 개수(`*_len`)와 `cap_hit_<key>` bool 을 함께 남긴다
        # (`D-R0-53` DECISION-1). `D-R0-53` DECISION-2: 절단은 그 필드에 의존하는
        # 지표만 UNDETERMINED 후보다 — 이 관측의 axis_c_valid 전체를 낮추지 않는다.
        # modal_overlay_candidates/dismiss_control_candidates 는 cap 과 무관(최대 44)
        # 이므로 OverlayCoverage 등 page-level geometry 는 절단 영향이 없다.
        "pac_len": cap_flags["primary_action_candidates"]["len"],
        "pac_truncated": cap_flags["primary_action_candidates"]["truncated"],
        # `D-R0-53` DECISION-1 확정 이름 — Axis C PrimaryActionOcclusion 함의(문서 상단)와 직결.
        "probe_primary_action_n": cap_flags["primary_action_candidates"]["len"],
        "ans_len": cap_flags["accessible_name_sources"]["len"],
        "ans_truncated": cap_flags["accessible_name_sources"]["truncated"],
        "ts_len": cap_flags["target_size"]["len"],
        "ts_truncated": cap_flags["target_size"]["truncated"],
        "contrast_len": cap_flags["contrast"]["len"],
        "contrast_at_400": cap_flags["contrast"]["truncated"],
        "anim_len": cap_flags["animated_elements"]["len"],
        "anim_truncated": cap_flags["animated_elements"]["truncated"],
        "probe_cap_flags": cap_flags,
        **cap_hit_flags,
        # ── slot 원자재 3종(F-A3.1, `D-R0-53` DECISION-1 이름 확정) — 정의는 열어
        # 둔다, bool 을 만들지 않는다 ──
        "dom_body_empty": None,
        "dom_body_empty_status": "DEFINITION_PENDING_D_LAYER",
        "slot_disagreement": None,
        "slot_disagreement_status": "DEFINITION_PENDING_D_LAYER_T-B-RQ-D-001-Q3",
        # ── task-level, 절대 값을 만들지 않는다 (Research Director 지시 2026-08-27) ──
        "primary_action_occlusion": None,
        "primary_action_occlusion_status": "PENDING_TASK_BINDING",
    }


def verify_overlay_fields_not_capped(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """`modal_overlay_candidates`/`dismiss_control_candidates` 가 실제로 cap 에 걸리지
    않았는지 mart 행 전체에서 재확인한다(B 의 보고를 W4 가 독립적으로 재검산)."""
    modal_lens = [
        r["modal_overlay_candidates_len"]
        for r in rows
        if r.get("modal_overlay_candidates_len") is not None
    ]
    dismiss_lens = [
        r["dismiss_control_candidates_len"]
        for r in rows
        if r.get("dismiss_control_candidates_len") is not None
    ]
    return {
        "modal_overlay_candidates_max_observed": max(modal_lens) if modal_lens else None,
        "dismiss_control_candidates_max_observed": max(dismiss_lens) if dismiss_lens else None,
        "n_checked": len(modal_lens),
        "safe_from_cap": (
            (max(modal_lens) if modal_lens else 0) < 200
            and (max(dismiss_lens) if dismiss_lens else 0) < 200
        ),
    }


_CAP_HIT_FIELDS_FOR_DESCRIPTIVE_STATS = (
    "cap_hit_primary_action_candidates",
    "cap_hit_accessible_name_sources",
    "cap_hit_target_size",
    "cap_hit_contrast",
)


def cap_hit_prior_archetype_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """**기술통계일 뿐이다 — 검정이 아니다**(A 결정, 코디네이터 지시).

    cap 이 하나라도 걸린 관측(`cap_hit_*` 중 하나라도 True)의 `prior_archetype` 분포를
    전체 `MEASURED` 관측의 분포와 나란히 낸다. **이 함수는 결론을 내지 않는다** —
    "절단이 특정 archetype 에 몰려 비교가 왜곡된다" 같은 주장은 이 mart 의 소관이 아니다
    (A 결정: 지금 그렇게 주장하지 않는다). 소비자가 스스로 판단하도록 분포만 남긴다.
    """
    measured = [r for r in rows if r["measurement_status"] == "MEASURED"]
    cap_hit = [r for r in measured if any(r.get(f) for f in _CAP_HIT_FIELDS_FOR_DESCRIPTIVE_STATS)]

    def _dist(subset: list[dict[str, Any]]) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in subset:
            key = r.get("prior_archetype") or "UNKNOWN"
            out[key] = out.get(key, 0) + 1
        return out

    return {
        "note": "DESCRIPTIVE_ONLY_NOT_A_TEST — 통계적 유의성 주장 없음, archetype 비교 왜곡 결론 없음",
        "cap_hit_n": len(cap_hit),
        "measured_n": len(measured),
        "cap_hit_prior_archetype_counts": _dist(cap_hit),
        "measured_prior_archetype_counts": _dist(measured),
    }


# ── 4. duplicate content capture — dom.html sha256 전수 스캔 (데이터 유도, 하드코딩 아님) ──


def annotate_duplicate_capture_groups(rows: list[dict[str, Any]]) -> None:
    """`in_main_population` 행들의 `dom_sha256` 이 겹치면 같은 그룹으로 묶는다.

    **삭제하지 않는다** — 그룹 표시만 남겨서 A 가 합칠지 말지 결정하게 한다(F-A2).
    `duplicate_capture_group_size == 1` 이면 겹치는 상대가 없다는 뜻이다.

    `D-R0-54`(`C-FINDING-212458` 처리) — A 가 **주분석 = 그룹당 1건으로 접기,
    2건 계수는 감도분석으로 함께 낸다**를 채택했다. 그룹 내 `collapse_role` 로
    표시한다: 대표(주분석에 남는 쪽)는 `service_name` 사전순으로 **결정적**으로
    고른다(가장 이른 launch 처럼 임의성 없이 재현 가능해야 한다).
    """
    sha_to_indices: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        if not row.get("in_main_population"):
            row["duplicate_capture_group"] = None
            row["duplicate_capture_group_size"] = None
            row["collapse_role"] = None
            continue
        sha = row.get("dom_sha256")
        if not sha:
            row["duplicate_capture_group"] = None
            row["duplicate_capture_group_size"] = None
            row["collapse_role"] = "PRIMARY_REPRESENTATIVE"
            continue
        sha_to_indices.setdefault(sha, []).append(i)

    group_counter = 0
    for idxs in sha_to_indices.values():
        if len(idxs) > 1:
            group_counter += 1
            gid = f"DUPCAP-{group_counter:03d}"
            representative_idx = min(idxs, key=lambda i: rows[i]["service_name"])
            for i in idxs:
                rows[i]["duplicate_capture_group"] = gid
                rows[i]["duplicate_capture_group_size"] = len(idxs)
                rows[i]["collapse_role"] = (
                    "PRIMARY_REPRESENTATIVE" if i == representative_idx else "COLLAPSED_IN_PRIMARY"
                )
        else:
            rows[idxs[0]]["duplicate_capture_group"] = None
            rows[idxs[0]]["duplicate_capture_group_size"] = 1
            rows[idxs[0]]["collapse_role"] = "PRIMARY_REPRESENTATIVE"


# ── 5. 조립 ──────────────────────────────────────────────────────────────


def build_mart_rows(
    attempted: dict[str, str] | None = None,
    run_dirs: list[RunDirInfo] | None = None,
    prior_archetype: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if attempted is None:
        attempted = load_attempted_population()
    if run_dirs is None:
        run_dirs = discover_run_dirs()
    if prior_archetype is None:
        prior_archetype = load_prior_archetype()

    rows = build_population_rows(attempted, run_dirs)
    for row in rows:
        # task_id 는 이 mart 의 grain 에 없다 — task binding(W1)이 아직 복구 중이다.
        row["task_id"] = None
        row["task_id_status"] = "PENDING_TASK_BINDING"
        row["informative_missingness_name_hint"] = informative_missingness_name_hint(
            row["service_name"]
        )
        # `D-R0-55` — prior/observed 둘 다 컬럼으로 남기고 어느 쪽도 "the" archetype 으로
        # 확정하지 않는다. observed(Layer O, RF-DT 검증)는 task binding 이 끝나야 나온다.
        row["prior_archetype"] = prior_archetype.get(row["web_target_id"])
        row["observed_archetype"] = None
        row["observed_archetype_status"] = "PENDING_TASK_BINDING"

        probe_path = row.get("probe_path")
        degenerate_reason = KNOWN_DEGENERATE_CAPTURE.get(row["service_name"])

        if row["population_status"] == "UNOBSERVED_STUB":
            row["measurement_status"] = "UNOBSERVED"
            row["axis_c_missingness_reason"] = "UNOBSERVED_STUB"
            row["informative_missingness_candidate"] = True
            row["informative_missingness_archetype_hint"] = KNOWN_UNOBSERVED_ARCHETYPE.get(
                row["service_name"]
            )
        elif row["population_status"] == "EXCLUDED_DUPLICATE_LAUNCH":
            row["measurement_status"] = "EXCLUDED_DUPLICATE_LAUNCH"
            row["axis_c_missingness_reason"] = "EXCLUDED_DUPLICATE_LAUNCH"
            row["informative_missingness_candidate"] = False
            row["informative_missingness_archetype_hint"] = None
        elif not probe_path:
            row["measurement_status"] = "FAILED_EVIDENCE_INCOMPLETE"
            row["axis_c_missingness_reason"] = (
                degenerate_reason or "PROBE_MISSING_EVIDENCE_INCOMPLETE"
            )
            row["informative_missingness_candidate"] = True
            row["informative_missingness_archetype_hint"] = None
        elif degenerate_reason:
            row["measurement_status"] = "FAILED_EVIDENCE_INCOMPLETE"
            row["axis_c_missingness_reason"] = degenerate_reason
            row["informative_missingness_candidate"] = True
            row["informative_missingness_archetype_hint"] = None
        else:
            row["measurement_status"] = "MEASURED"
            row["axis_c_missingness_reason"] = None
            row["informative_missingness_candidate"] = False
            row["informative_missingness_archetype_hint"] = None

        row["axis_c_valid"] = (
            bool(row["in_main_population"]) and row["measurement_status"] == "MEASURED"
        )

        # probe.json 이 물리적으로 있으면(=coupang_eats 처럼 degenerate 여도) URL/시각은
        # 읽어서 남긴다 — frame_defect_hint 계산에 필요하고, 결측 처리와는 별개다.
        if probe_path:
            probe = json.loads(Path(probe_path).read_text(encoding="utf-8"))
            row["probe_collected_at"] = probe.get("collected_at")
            row["probe_url"] = probe.get("url")
            row["frame_defect_hint"] = frame_defect_hint(probe.get("url"))
        else:
            row["probe_collected_at"] = None
            row["probe_url"] = None
            row["frame_defect_hint"] = None

        if not row["axis_c_valid"]:
            # 결측을 0 이나 상한값으로 대체하지 않는다 — NULL 은 NULL 이다.
            for k in (
                "interrupt_count_visible",
                "overlay_coverage",
                "interrupts",
                "classification_tier_counts",
                "body_scroll_locked",
                "dismiss_control_present_count",
                "dismiss_control_visible_count",
                "modal_overlay_candidates_len",
                "dismiss_control_candidates_len",
                "pac_len",
                "pac_truncated",
                "ans_len",
                "ans_truncated",
                "ts_len",
                "ts_truncated",
                "contrast_len",
                "contrast_at_400",
                "anim_len",
                "anim_truncated",
                "probe_primary_action_n",
                "probe_cap_flags",
                "dom_body_empty",
                "slot_disagreement",
                "cap_hit_primary_action_candidates",
                "cap_hit_accessible_name_sources",
                "cap_hit_target_size",
                "cap_hit_contrast",
                "cap_hit_animated_elements",
            ):
                row[k] = None
            row["dom_body_empty_status"] = "DEFINITION_PENDING_D_LAYER"
            row["slot_disagreement_status"] = "DEFINITION_PENDING_D_LAYER_T-B-RQ-D-001-Q3"
            row["primary_action_occlusion"] = None
            row["primary_action_occlusion_status"] = "PENDING_TASK_BINDING"
            continue

        probe = json.loads(Path(probe_path).read_text(encoding="utf-8"))
        axis_c = axis_c_page_level_from_probe(probe.get("raw_features", {}))
        row.update(axis_c)

    annotate_duplicate_capture_groups(rows)

    # `D-R0-54` 주분석 flag — axis_c_valid 이면서 duplicate_capture 그룹에서 접힌
    # 쪽(COLLAPSED_IN_PRIMARY)이 아닌 행만 주분석 분모에 들어간다. 감도분석(uncollapsed)
    # 은 axis_c_valid 그대로 쓰면 된다 — 별도 컬럼을 또 만들지 않는다.
    for row in rows:
        row["axis_c_valid_primary"] = (
            bool(row.get("axis_c_valid")) and row.get("collapse_role") != "COLLAPSED_IN_PRIMARY"
        )

    return rows


# ── 6. 분모 — 절대 `len(rows)` 를 그대로 "the" 분모로 쓰지 않는다 ────────────


def compute_denominators(rows: list[dict[str, Any]]) -> dict[str, int]:
    """지표마다 다른 분모를 **이름 붙여** 돌려준다. `T-A-FINDING-001` F-A1 4층 프레임."""
    attempted = len(rows) - sum(
        1 for r in rows if r["population_status"] == "EXCLUDED_DUPLICATE_LAUNCH"
    )
    evidence_bytes = sum(1 for r in rows if r["in_main_population"])
    unobserved = sum(1 for r in rows if r["population_status"] == "UNOBSERVED_STUB")
    excluded_duplicate_launch = sum(
        1 for r in rows if r["population_status"] == "EXCLUDED_DUPLICATE_LAUNCH"
    )
    measured = sum(1 for r in rows if r["measurement_status"] == "MEASURED")
    failed_evidence_incomplete = sum(
        1 for r in rows if r["measurement_status"] == "FAILED_EVIDENCE_INCOMPLETE"
    )
    axis_c_valid = sum(1 for r in rows if r.get("axis_c_valid"))
    informative_missingness = sum(1 for r in rows if r.get("informative_missingness_candidate"))
    duplicate_capture_groups = len(
        {r["duplicate_capture_group"] for r in rows if r.get("duplicate_capture_group")}
    )

    # `D-R0-54` — 주분석은 duplicate_capture 그룹을 1건으로 접은 값이다(A 확정).
    # uncollapsed(그룹을 안 접은, `measured`/`axis_c_valid` 그대로)는 감도분석으로
    # **함께** 낸다 — 두 값 다 여기서 계산해 둔다.
    axis_c_valid_primary = sum(1 for r in rows if r.get("axis_c_valid_primary"))

    return {
        "attempted": attempted,
        "evidence_bytes": evidence_bytes,
        "unobserved": unobserved,
        "excluded_duplicate_launch": excluded_duplicate_launch,
        "measured": measured,
        "failed_evidence_incomplete": failed_evidence_incomplete,
        "informative_missingness_candidates": informative_missingness,
        "duplicate_capture_groups": duplicate_capture_groups,
        # ── D-R0-54: primary = collapsed, sensitivity = uncollapsed. 이름에 명시한다. ──
        "axis_c_valid_primary_collapsed": axis_c_valid_primary,
        "axis_c_valid_sensitivity_uncollapsed": axis_c_valid,
        # 하위호환 별칭(기존 이름 그대로도 유지 — 기존 소비자가 있을 수 있다).
        "axis_c_valid": axis_c_valid,
        "measured_n_raw": measured,
        "measured_n_collapsed_duplicate_capture": axis_c_valid_primary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=_WORKTREE_ROOT / "artifacts" / "mart_axisc",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    attempted = load_attempted_population()
    run_dirs = discover_run_dirs()
    rows = build_mart_rows(attempted, run_dirs)

    out_jsonl = args.out / "mart_axisc_observations.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    denominators = compute_denominators(rows)
    cap_check = verify_overlay_fields_not_capped(rows)
    cap_hit_archetype_stats = cap_hit_prior_archetype_distribution(rows)

    manifest = {
        "mart": "axisc",
        "owner": "W4",
        "row_count": len(rows),
        "grain": "web_target_id (task-level pending W1/W2 binding)",
        "denominators": denominators,
        "overlay_cap_check": cap_check,
        "cap_hit_prior_archetype_distribution": cap_hit_archetype_stats,
        "decisions_applied": {
            "D-R0-53_DECISION-1": (
                "cap_hit_<key> bool + *_len 개수를 함께 저장 (dom_body_empty/"
                "probe_primary_action_n/slot_disagreement 이름도 이 결정대로 확정)"
            ),
            "D-R0-53_DECISION-2": (
                "cap 절단은 그 필드에 의존하는 지표만 UNDETERMINED 후보다 — 관측 전체를 "
                "낮추지 않는다. modal_overlay_candidates/dismiss_control_candidates 는 "
                f"cap 무관(관측 최대 {cap_check['modal_overlay_candidates_max_observed']}) "
                "이므로 OverlayCoverage 등 page-level geometry 는 절단 영향이 없다 "
                f"(safe_from_cap={cap_check['safe_from_cap']})."
            ),
            "D-R0-53_DECISION-3": "cap 상향 재수집을 이 mart 는 제안하지 않는다 — REAL_TARGET_GO 는 A 소관.",
            "D-R0-54": (
                "NH스마트뱅킹/NH콕뱅크 duplicate_capture_group — 주분석은 1건으로 접힘"
                f"(axis_c_valid_primary_collapsed={denominators['axis_c_valid_primary_collapsed']}), "
                f"2건 계수 감도분석을 함께 낸다(axis_c_valid_sensitivity_uncollapsed="
                f"{denominators['axis_c_valid_sensitivity_uncollapsed']})."
            ),
            "D-R0-55": (
                "analysis frame archetype(prior/observed) 결정을 A 가 유보 — 이 mart 는 "
                "prior_archetype(Layer P, 읽기 전용 참조)과 observed_archetype"
                "(PENDING_TASK_BINDING)을 각각 컬럼으로 남기고 어느 쪽도 확정하지 않는다."
            ),
        },
        "self_approved": False,
        "not_verified_by_this_gate": [
            "task-specific PrimaryActionOcclusion — task binding 미완료, 값 전부 NULL/PENDING_TASK_BINDING. "
            "구현될 때 pac_truncated=True 행은 'primary action이 상위 200개 안에 있다'는 검증되지 않은 가정을 "
            "명시적으로 확인해야 한다.",
            "dismiss 성공/실패 — l0c 산출물에 구조화된 결과가 저장되지 않아 이 mart 는 그 값을 복원하지 않는다",
            "Axis A/B — 이 mart 는 Axis C 전용이며 KWCAG 판정이나 depth 는 포함하지 않는다",
            "semantic 분류의 정확도 — deterministic+text tier 까지만 구현했고 독립 label 대비 정밀도는 아직 측정되지 않았다",
            "coupang_eats 의 STRUCTURAL_DEGENERATE_CAPTURE 판정 — Claude A(T-A-FINDING-001)의 판정을 그대로 "
            "수용했고 W4 가 독립적으로 재현 검증하지 않았다",
            "informative_missingness_name_hint/frame_defect_hint — 이름/URL 패턴 기반 약한 힌트이며 archetype "
            "이나 인과 판정이 아니다. 통계적 유의성 검정을 하지 않았다(코디네이터 지시: 해석은 A/C 몫)",
            "duplicate_capture_group — dom_sha256 일치만 근거. NH 쌍은 JS 렌더 이전 공용 SSR shell로 추정되나 "
            "W4 가 그 원인을 독립 검증하지 않았다",
            "cap_hit_prior_archetype_distribution — 기술통계다. archetype 비교가 절단으로 왜곡된다는 결론을 "
            "이 mart 는 내리지 않는다(A 결정).",
        ],
    }
    (args.out / "mart_axisc_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
