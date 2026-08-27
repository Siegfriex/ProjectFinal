#!/usr/bin/env python
"""P-A A5 pilot mapping — **SHADOW / source-context only**.

목적은 매핑 **결과**가 아니라 cascade **구조가 실제로 작동하는가**의 실증이다
(`PHASE_GATES` §4.2 `pilot mapping` · codebook `mapping_rules.cascade`).

강제되는 것:

* **입력 allowlist (T1)** — `codebook.json mapping_rules.input_allowlist`.
  파일과 **컬럼**을 둘 다 좁힌다. allowlist 밖 경로를 여는 시도는 예외로 끊는다.
* **denylist** — 인증(certification) · KWCAG · popup · depth · accessibility outcome은
  **한 바이트도 읽지 않는다** (`PHASE_GATES` §4.6 교차오염 금지).
  읽지 않았음을 사후에 주장하지 않고, `open()` 을 감싸 **실제 접근 흔적**으로 증명한다 (규칙 IN-2).
* **동결 금지** — 이 실행은 `mapping_status`를 `FROZEN`으로 올리지 않는다.
  `ANALYSIS_AND_TASK_CODEBOOK_FROZEN`은 P0 종료 전이라 닫을 수 없다.

Run:
  /home/sieg/projects-wsl/ProjectFinal/.venv/bin/python pilot_mapping.py
"""

from __future__ import annotations

import builtins
import hashlib
import json
import os
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

RESEARCH_ROOT = Path(
    os.environ.get("LANDING_RESEARCH_ROOT", str(Path(__file__).resolve().parents[2]))
)
STATE = Path(os.environ.get("LANDING_STATE_DIR", str(RESEARCH_ROOT / "state")))
CODEBOOK = RESEARCH_ROOT / "analysis" / "codebook" / "codebook.json"
OUT = Path(os.environ.get("PILOT_OUT", str(RESEARCH_ROOT / "analysis" / "out" / "pilot")))
OUT.mkdir(parents=True, exist_ok=True)

BASE_SHA = "d5f1da5652953542d5c8be377026cc3293f2075a"
SAMPLE_SIZE = 15

# --- T1 입력 allowlist -------------------------------------------------------
# codebook mapping_rules.input_allowlist.tiers[T1]. P-A pilot은 T1만 쓴다.
ALLOWED_FILES: dict[str, Path] = {
    "panel_registry": STATE / "panel_registry.parquet",
    "source_ranking_rows": STATE / "source_ranking_rows.parquet",
    "source_membership": STATE / "source_membership.parquet",
    "service_master": STATE / "service_master.parquet",
    "entity_alias_map": STATE / "entity_alias_map.parquet",
    "codebook": CODEBOOK,
}
# service_master는 **네 컬럼만** 허용된다. 나머지(web_eligibility_status·review_*·
# web_target_group_id 등)는 T1이 아니므로 로드 직후 버린다.
SERVICE_MASTER_T1_COLUMNS = [
    "service_id",  # 조인 키 — 이름이 유일키가 아니므로(EDA-00 F-14) 반드시 필요하다
    "canonical_service_key",
    "service_name_canonical",
    "domain",
    "axis_type",
    "canonicalization_basis",
]

# 이 실행이 절대 열지 않아야 하는 것. 경로 조각으로 검사한다.
DENY_PATH_FRAGMENTS = [
    "certification",
    "인증",
    "criterion_result",
    "landing_observation",
    "interrupt_element",
    "task_entry",
    "task_step",
    "ai_adjudication",
    "mart_",
    "evidence/",
    "kwcag",
]

_ACCESS_LOG: list[str] = []  # 실제로 **열린** 경로
_REFUSED_LOG: list[str] = []  # 차단돼 한 바이트도 읽지 못한 경로
_REAL_OPEN = builtins.open


class InputAllowlistViolation(RuntimeError):
    """allowlist 밖 입력을 열려 했다. 그 run은 무효다 (codebook 규칙 IN-2)."""


def _guarded_open(file, *args, **kwargs):
    path = os.fspath(file) if not isinstance(file, int) else ""
    if path:
        low = path.lower()
        mode = args[0] if args else kwargs.get("mode", "r")
        reading = "r" in str(mode) and "+" not in str(mode)
        inside_research = str(RESEARCH_ROOT) in path
        if reading and inside_research:
            for frag in DENY_PATH_FRAGMENTS:
                if frag in low:
                    # 차단된 경로는 `_ACCESS_LOG`에 넣지 않는다 — 열리지 않았기 때문이다.
                    # 시도 자체는 `_REFUSED_LOG`에 남겨 감사가 볼 수 있게 한다.
                    _REFUSED_LOG.append(path)
                    raise InputAllowlistViolation(
                        f"denylist 경로를 열려 했다: {path} (조각 {frag!r})"
                    )
        _ACCESS_LOG.append(path)
    return _REAL_OPEN(file, *args, **kwargs)


builtins.open = _guarded_open


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with _REAL_OPEN(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --- F0: mapping_run_manifest ------------------------------------------------
RUN_STARTED = datetime.now(UTC).isoformat()
MANIFEST: dict[str, Any] = {
    "artifact": "mapping_run_manifest",
    "note": "codebook freeze_protocol F0. 물리 저장 슬롯은 미결 Q-8 — 확정 전까지 analysis/out/pilot 에 둔다",
    "status": "SHADOW_PREPARATORY",
    "shadow_lane": "LANE_A",
    "base_sha": BASE_SHA,
    "run_started_at": RUN_STARTED,
    "created_before_p0_close": True,
    "authoritative": False,
    "real_target_outcome_used": False,
    "real_target_measurement": False,
    "requires_post_p0_reconciliation": True,
    "input_tier": "T1_SOURCE_CONTEXT_ONLY",
    "allowed_inputs": [
        {
            "name": name,
            "path_in_research": str(path.relative_to(RESEARCH_ROOT)),
            "sha256": sha256_file(path),
        }
        for name, path in ALLOWED_FILES.items()
    ],
    "service_master_columns_used": SERVICE_MASTER_T1_COLUMNS,
    "denied_inputs": [
        "sources/certification/** (dim_certification · certified_current · 인증목록 원자료)",
        "fact_criterion_result (KWCAG 판정 전 컬럼)",
        "fact_landing_observation measurement scalars",
        "fact_interrupt_element judgement results (popup/obstruction)",
        "fact_task_entry / fact_task_step (depth · endpoint 결과)",
        "mart_* (전부)",
        "state/web_target_group.parquet (T2 target identity — P-B 소관이라 이 run에서는 안 쓴다)",
    ],
}


def _guard_selftest() -> dict[str, Any]:
    """차단이 **실제로 발화하는지** 시험한다. 선언만 남기고 넘어가지 않는다.

    존재하는 denylist 경로를 골라 열어 보고 `InputAllowlistViolation`이 나는지 본다.
    파일 내용은 읽지 않는다 — `open()` 이 예외로 끊기기 때문이다.
    """
    probe = RESEARCH_ROOT / "sources" / "certification" / "certification_registry.parquet"
    fired = False
    try:
        with open(probe, "rb"):  # 감싼 open 을 일부러 호출한다
            pass
    except InputAllowlistViolation:
        fired = True
    return {
        "probe_path": str(probe.relative_to(RESEARCH_ROOT)),
        "probe_exists": probe.is_file(),
        "guard_fired": fired,
        "verdict": "GUARD_WORKS" if fired else "GUARD_DEAD",
    }


def load_allowed(name: str) -> pd.DataFrame:
    if name not in ALLOWED_FILES:
        raise InputAllowlistViolation(f"allowlist에 없는 입력: {name}")
    return pd.read_parquet(ALLOWED_FILES[name])


SELFTEST = _guard_selftest()
if SELFTEST["verdict"] != "GUARD_WORKS":
    raise SystemExit(f"차단 장치가 죽어 있다: {SELFTEST}")
MANIFEST["guard_selftest"] = SELFTEST

panel = load_allowed("panel_registry")
rows = load_allowed("source_ranking_rows")
memb = load_allowed("source_membership")
svc = load_allowed("service_master")[SERVICE_MASTER_T1_COLUMNS].copy()
alias = load_allowed("entity_alias_map")
with _REAL_OPEN(CODEBOOK, encoding="utf-8") as fh:
    codebook = json.load(fh)

ARCHETYPES = {a["code"]: a for a in codebook["interaction_archetype"]["values"]}
DOMAINS = {d["code"]: d for d in codebook["business_domain"]["values"]}


# --- 표본 선정 (outcome-blind) ------------------------------------------------
def select_sample(service_master: pd.DataFrame, n: int) -> pd.DataFrame:
    """`canonical_service_key` 정렬 후 domain 층별 균등 stride.

    **선정에 접근성·인증 결과를 쓰지 않는다.** 정렬 키도 표본 크기도 source context다.
    `axis_type = SERVICE_BRAND`만 대상이다 — 업종 카테고리는 웹 대상이 아니다(EDA-00 F-10).
    """
    brands = service_master[service_master["axis_type"] == "SERVICE_BRAND"].sort_values(
        "canonical_service_key"
    )
    picked: list[pd.DataFrame] = []
    total = len(brands)
    for _domain, group in brands.groupby("domain", sort=True):
        quota = round(n * len(group) / total)
        step = max(1, len(group) // max(1, quota))
        picked.append(group.iloc[::step].head(quota))
    out = pd.concat(picked).sort_values("canonical_service_key")
    return out.head(n)


sample = select_sample(svc, SAMPLE_SIZE)


# --- STAGE 1: deterministic rule ---------------------------------------------
# 기능어 사전. **브랜드명이 아니라 기능을 가리키는 낱말**만 쓴다 — 브랜드를 열거하면
# 그것은 규칙이 아니라 손라벨이고, 신조어·미등재 브랜드에서 조용히 무너진다.
# 출처는 codebook business_domain[*].inclusion / interaction_archetype[*].user_action 이다.
DOMAIN_RULES: list[tuple[str, str]] = [
    (r"은행|뱅킹|뱅크|bank|카드$|카드\b|페이|pay|월렛|wallet|증권|보험", "FINANCE_PAYMENT"),
    (r"쇼핑|백화점|마트|아울렛|편의점|홈쇼핑|몰\b|스토어|커머스|배달|이츠", "SHOPPING_COMMERCE"),
    (r"지도|맵|map|내비|navi|택시|대중교통", "MAP_MOBILITY"),
    (r"브라우저|browser|검색|포털", "PORTAL_SEARCH"),
    (r"노트|메모|계산기|파일|포토|photo|백신|보안|케어|캐시|걸음", "UTILITY_OTHER"),
]
ARCHETYPE_RULES: list[tuple[str, str]] = [
    (r"은행|뱅킹|뱅크|bank|카드$|카드\b|페이|pay|월렛|wallet", "FINANCIAL_ACTION_ENTRY"),
    (r"지도|맵|map|내비|navi", "PLACE_LOOKUP"),
    (r"브라우저|browser", "QUERY"),
    (r"노트|메모|계산기|파일|포토|photo|백신|보안|케어", "UTILITY_ENTRY"),
    (r"백화점|마트|아울렛|편의점|홈쇼핑|몰\b|스토어", "ITEM_DETAIL"),
]


def _match_all(patterns: list[tuple[str, str]], text: str) -> list[str]:
    hits = [code for pat, code in patterns if re.search(pat, text, flags=re.IGNORECASE)]
    return sorted(set(hits))


def stage1_rule(name: str) -> dict[str, Any]:
    dom_hits = _match_all(DOMAIN_RULES, name)
    arc_hits = _match_all(ARCHETYPE_RULES, name)
    resolved_domain = dom_hits[0] if len(dom_hits) == 1 else None
    resolved_archetype = arc_hits[0] if len(arc_hits) == 1 else None
    if resolved_domain and resolved_archetype:
        status = "RESOLVED"
    elif dom_hits or arc_hits:
        # 다중 매칭은 **확정이 아니다.** 임의로 하나를 고르면 강제분류다 (규칙 AB-2).
        status = "AMBIGUOUS_RULE_MATCH" if (len(dom_hits) > 1 or len(arc_hits) > 1) else "PARTIAL"
    else:
        status = "NO_RULE_MATCH"
    return {
        "stage": 1,
        "mapping_basis": "RULE",
        "domain_hits": dom_hits,
        "archetype_hits": arc_hits,
        "domain": resolved_domain,
        "archetype": resolved_archetype,
        "status": status,
    }


# --- STAGE 2: source context --------------------------------------------------
# 패널 문맥이 주는 것은 **domain 힌트뿐**이다. codebook cascade stage 2가
# "패널 카테고리는 사업분류라 archetype(행위 구조)을 직접 답하지 못한다"고 이미 적었다.
PANEL_CONTEXT_RULES: list[tuple[str, str]] = [
    (r"금융\s*앱", "FINANCE_PAYMENT"),
    (r"쇼핑\s*앱|홈쇼핑|마트\s*리테일|리테일\s*브랜드", "SHOPPING_COMMERCE"),
]


def panel_context_text(service_id: str) -> str:
    panels = memb.loc[memb["service_id"] == service_id, "panel_id"].tolist()
    sub = panel[panel["panel_id"].isin(panels)]
    parts: list[str] = []
    for col in ("source_section_title", "table_title", "panel_label", "universe_definition"):
        parts.extend(str(v) for v in sub[col].dropna().tolist())
    return " ".join(parts)


def stage2_source_context(service_id: str) -> dict[str, Any]:
    text = panel_context_text(service_id)
    hits = _match_all(PANEL_CONTEXT_RULES, text)
    panels = sorted(memb.loc[memb["service_id"] == service_id, "panel_id"].tolist())
    return {
        "stage": 2,
        "mapping_basis": "SOURCE_CONTEXT",
        "panels": panels,
        "n_panels": len(panels),
        "domain_candidates": hits,
        "domain": hits[0] if len(hits) == 1 else None,
        # archetype은 이 단계가 답할 수 없다. 따라서 이 단계 단독 확정은 **구조적으로 불가능**하다
        # (규칙 MAP-7: domain·archetype 중 하나라도 미확정이면 FROZEN 불가).
        "archetype": None,
        "status": "DOMAIN_CANDIDATE" if hits else "NO_CONTEXT_SIGNAL",
    }


# --- STAGE 3: embedding similarity (SHADOW 대체구현) --------------------------
# 정본 stage 3은 `02 §6` 후보 control의 accessible name·visible text에 대한 임베딩이다.
# 그 입력은 **실제 target의 DOM/AX**라서 P0 종료 전에는 수집이 금지다
# (`PHASE_GATES` §4.1 2항). 따라서 여기서는 입력을 **source context 텍스트로 대체**하고
# 유사도 함수도 네트워크 없는 결정적 char n-gram TF-IDF cosine으로 둔다.
# `fidelity = SOURCE_TEXT_SUBSTITUTE` 로 표시하며, **실측 대체물이 아니다.**
def _char_ngrams(text: str, n: int = 2) -> Counter[str]:
    t = re.sub(r"\s+", "", text.lower())
    return Counter(t[i : i + n] for i in range(max(0, len(t) - n + 1)))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    num = sum(a[k] * b[k] for k in common)
    da = sum(v * v for v in a.values()) ** 0.5
    db = sum(v * v for v in b.values()) ** 0.5
    return num / (da * db) if da and db else 0.0


def archetype_prototype_text(code: str) -> str:
    a = ARCHETYPES[code]
    parts = [a.get("label_ko", ""), a.get("user_action", ""), a.get("region_definition", "")]
    ep = a.get("endpoint_definition")
    if isinstance(ep, str):
        parts.append(ep)
    return " ".join(p for p in parts if p)


_PROTOTYPES = {code: _char_ngrams(archetype_prototype_text(code)) for code in ARCHETYPES}


def stage3_embedding(name: str, context: str) -> dict[str, Any]:
    query = _char_ngrams(f"{name} {context}")
    scores = sorted(
        ((code, round(_cosine(query, proto), 4)) for code, proto in _PROTOTYPES.items()),
        key=lambda kv: (-kv[1], kv[0]),
    )
    top1, top2 = scores[0], scores[1]
    return {
        "stage": 3,
        "mapping_basis": "EMBEDDING",
        "fidelity": "SOURCE_TEXT_SUBSTITUTE",
        "fidelity_note": (
            "정본 입력(02 §6 후보 control의 accessible name·visible text)은 real-target 수집이 필요해"
            " P0 종료 전 금지다. 순위는 참고이며 판정 근거가 아니다"
        ),
        "ranking": scores[:3],
        "top1": top1[0],
        "top1_score": top1[1],
        "margin": round(top1[1] - top2[1], 4),
        # 확정하지 않는다. codebook stage 3 cannot_do: "유사도는 순위이지 판정이 아니다 —
        # 임계값 자동 확정 금지". 규칙 CAS-2와의 긴장은 PILOT-F03 으로 등재했다.
        "domain": None,
        "archetype": None,
        "status": "RANKING_ONLY_ESCALATE",
    }


# --- STAGE 4: AI reviewer -----------------------------------------------------
def stage4_ai_review() -> dict[str, Any]:
    """`02 §10` evidence package가 없으면 4단계는 **실행되지 않는다.**

    package는 screenshot crop·DOM/AX fact·bbox를 요구하고 그것은 real-target 수집이다.
    P0 종료 전에는 금지이므로 이 단계는 `UNAVAILABLE_PRE_P0`를 반환하고,
    규칙 CAS-3 · AB-1에 따라 abstain 경로로 나간다.
    **판정을 지어내지 않는 것이 이 단계의 올바른 동작이다.**
    """
    return {
        "stage": 4,
        "mapping_basis": "AI_REVIEW",
        "status": "UNAVAILABLE_PRE_P0",
        "reason": (
            "02 §10 evidence package(screenshot crop · DOM/AX fact · bbox)는 real-target 수집 산물이며"
            " PHASE_GATES §4.1 2항으로 P0 종료 전 금지다. 근거 없이 라벨을 생성하지 않는다"
        ),
        "domain": None,
        "archetype": None,
    }


# --- cascade 실행 -------------------------------------------------------------
def run_cascade(row: pd.Series) -> dict[str, Any]:
    name = str(row["service_name_canonical"])
    context = panel_context_text(str(row["service_id"]))
    history: list[dict[str, Any]] = []

    s1 = stage1_rule(name)
    history.append(s1)
    if s1["status"] == "RESOLVED":
        return _finish(row, s1["domain"], s1["archetype"], "RULE", history, resolved_stage=1)

    s2 = stage2_source_context(str(row["service_id"]))
    history.append(s2)
    # stage 1의 부분 결과와 stage 2의 domain 후보를 합쳐도 archetype이 없으면 확정 불가(MAP-7).
    domain = s1["domain"] or s2["domain"]
    archetype = s1["archetype"]
    if domain and archetype:
        basis = "RULE" if (s1["domain"] and s1["archetype"]) else "SOURCE_CONTEXT"
        return _finish(row, domain, archetype, basis, history, resolved_stage=2)

    s3 = stage3_embedding(name, context)
    history.append(s3)
    s4 = stage4_ai_review()
    history.append(s4)
    return _finish(row, None, None, None, history, resolved_stage=None)


def _finish(
    row: pd.Series,
    domain: str | None,
    archetype: str | None,
    basis: str | None,
    history: list[dict[str, Any]],
    resolved_stage: int | None,
) -> dict[str, Any]:
    abstained = resolved_stage is None
    record: dict[str, Any] = {
        "measurement_entity_id": row["service_id"],
        "canonical_service_key": row["canonical_service_key"],
        "canonical_name": row["service_name_canonical"],
        "source_domain": row["domain"],
        "entity_type": row["axis_type"],
        "business_domain": domain,
        "interaction_archetype": archetype,
        "mapping_basis": basis,
        "resolved_at_stage": resolved_stage,
        "cascade_history": history,
    }
    # A2 §1.9 mapping_status FSM: DRAFT → CANDIDATE → {FROZEN, AMBIGUOUS_UNRESOLVED, EXCLUDED}
    # (5값 상호배타, 단방향). `mapping_status_history`는 이 selective-port 시점에
    # 새로 추가된 필드로, 각 행이 그 그래프의 어느 경로를 지나왔는지를 명시적으로
    # 남긴다 — 최종 저장값(`mapping_status`)만으로는 CANDIDATE 경유 여부가 보이지
    # 않기 때문이다 (닫는 CR: claude-b/pa-qa CR-002, mapping-status-fsm-drift).
    if abstained:
        # stage1(RULE)·stage2(SOURCE_CONTEXT)·stage3(EMBEDDING)로 후보를 좁히려
        # 시도했으나 확정하지 못했으므로 DRAFT 다음 CANDIDATE를 실제로 거친 뒤
        # cascade·사람 검토 예산(stage4 AI_REVIEW)까지 소진돼 AMBIGUOUS_UNRESOLVED로
        # 떨어진다. FSM이 허용하는 유일한 AMBIGUOUS_UNRESOLVED 진입 간선은
        # CANDIDATE → AMBIGUOUS_UNRESOLVED이며, 이전 판(0f46203)은 DRAFT에서
        # 직행해 그 간선 밖의 값을 만들었다(CR-002).
        record.update(
            {
                "mapping_status": "AMBIGUOUS_UNRESOLVED",
                "mapping_status_history": ["DRAFT", "CANDIDATE", "AMBIGUOUS_UNRESOLVED"],
                "mapping_ai_review_status": "ABSTAINED",
                "abstain_reason": "AI_REVIEW_UNAVAILABLE_PRE_P0",
                "counts_toward_archetype_denominator": False,
            }
        )
    else:
        # **FROZEN으로 올리지 않는다.** P0 종료 전이고 gate도 닫지 않는다.
        # RULE/SOURCE_CONTEXT 근거로 domain·archetype이 둘 다 확정된 결과는
        # A2 §1.9의 CANDIDATE 정의("규칙·source context·embedding으로 후보가
        # 좁혀졌으나 확정 전")에 글자 그대로 들어맞는다. 이전 판(0f46203)은 이
        # 9건 전부를 DRAFT로 남겨 CANDIDATE 상태 자체가 한 번도 관측되지
        # 않았다(CR-002) — RULE/SOURCE_CONTEXT로 좁혀진 결과를 DRAFT로 두면
        # "아직 후보조차 안 만들어졌다"는 뜻이 되어 실제로 일어난 일(좁혀짐)과
        # 어긋난다.
        pending = archetype == "UTILITY_ENTRY"
        record.update(
            {
                "mapping_status": "CANDIDATE",
                "mapping_status_history": ["DRAFT", "CANDIDATE"],
                "mapping_ai_review_status": "NOT_REQUIRED",
                "region_signal_type": "CODEBOOK_PENDING" if pending else "DOM_AX_ROLE",
                "freeze_blocked_by": ["FRZ-4 (region_signal_type=CODEBOOK_PENDING · Q-2 미결)"]
                if pending
                else ["P0 미종료 — ANALYSIS_AND_TASK_CODEBOOK_FROZEN 닫지 않음"],
                "counts_toward_archetype_denominator": False,
            }
        )
    return record


records = [run_cascade(row) for _, row in sample.iterrows()]

# --- 오염 검사 ----------------------------------------------------------------
opened_inside = sorted(
    {p for p in _ACCESS_LOG if str(RESEARCH_ROOT) in p and not p.startswith(str(OUT))}
)
allowed_paths = {str(p) for p in ALLOWED_FILES.values()}
unexpected = [p for p in opened_inside if p not in allowed_paths]
denied_touched = [p for p in opened_inside if any(f in p.lower() for f in DENY_PATH_FRAGMENTS)]

contamination = {
    "check": "PHASE_GATES §4.6 교차오염 금지 · codebook 규칙 IN-2",
    "method": (
        "builtins.open 을 감싸 이 프로세스가 연 모든 경로를 기록했다. 선언이 아니라 접근 흔적이다."
        " pandas.read_parquet 도 이 open 을 거친다"
    ),
    "research_root_paths_opened": opened_inside,
    "refused_open_attempts": sorted(set(_REFUSED_LOG)),
    "refused_note": "차단 자체 시험(guard_selftest)이 만든 시도다. 열리지 않았으므로 읽힌 바이트는 0이다",
    "allowlist_paths": sorted(allowed_paths),
    "outside_allowlist": unexpected,
    "denylist_paths_touched": denied_touched,
    "kwcag_result_used": False,
    "popup_result_used": False,
    "depth_result_used": False,
    "wa_certification_used": False,
    "accessibility_outcome_used": False,
    "real_target_measurement": False,
    "guard_selftest": SELFTEST,
    "verdict": "CLEAN"
    if (not unexpected and not denied_touched and SELFTEST["verdict"] == "GUARD_WORKS")
    else "VIOLATION",
}

summary = {
    "run_started_at": RUN_STARTED,
    "run_finished_at": datetime.now(UTC).isoformat(),
    "n_sampled": len(records),
    "n_resolved": sum(1 for r in records if r["resolved_at_stage"] is not None),
    "n_abstain": sum(1 for r in records if r["mapping_status"] == "AMBIGUOUS_UNRESOLVED"),
    "n_frozen": sum(1 for r in records if r["mapping_status"] == "FROZEN"),
    "resolved_by_stage": dict(
        Counter(r["resolved_at_stage"] for r in records if r["resolved_at_stage"] is not None)
    ),
    "archetype_distribution": dict(
        Counter(r["interaction_archetype"] for r in records if r["interaction_archetype"])
    ),
    "domain_distribution": dict(
        Counter(r["business_domain"] for r in records if r["business_domain"])
    ),
    "gate_closed": False,
    "gate_note": "ANALYSIS_AND_TASK_CODEBOOK_FROZEN 은 닫지 않았다. freeze candidate 까지다",
}
MANIFEST["summary"] = summary
MANIFEST["contamination_check"] = contamination

with _REAL_OPEN(OUT / "pilot_mapping.jsonl", "w", encoding="utf-8") as fh:
    for r in records:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
with _REAL_OPEN(OUT / "mapping_run_manifest.json", "w", encoding="utf-8") as fh:
    json.dump(MANIFEST, fh, ensure_ascii=False, indent=2)
    fh.write("\n")

print(json.dumps(summary, ensure_ascii=False, indent=2))
print()
print("contamination verdict:", contamination["verdict"])
print("outside allowlist:", contamination["outside_allowlist"])
print("denylist touched :", contamination["denylist_paths_touched"])
print()
for r in records:
    print(
        f"  {r['canonical_service_key']:30} {r['business_domain']!s:20}"
        f" {r['interaction_archetype']!s:24} stage={r['resolved_at_stage']}"
        f" {r['mapping_status']}"
    )
print()
print("wrote", OUT / "pilot_mapping.jsonl", "and", OUT / "mapping_run_manifest.json")

if contamination["verdict"] != "CLEAN":
    raise SystemExit("오염 검사 실패 — 이 run 은 무효다 (규칙 IN-2)")
