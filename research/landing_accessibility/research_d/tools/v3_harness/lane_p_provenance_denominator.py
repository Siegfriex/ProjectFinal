#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lane P — Provenance / Denominator chain / Metric redundancy harness  (Claude D, V3)

base SHA        : 7448184a811f5d7d8772f21488bb75418fde3313  (claude-d/research-sandbox-v21)
SSOTV3 MANIFEST : 1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a

책임 (4개, 그 이상 아님)
  1. 분모 사슬 계산기        — 05_ANALYSIS_PLAN_v3.0.md §6
  2. lineage hole 탐지기     — Director P1 B 항 사슬 9노드
  3. 실패 사유 분해기        — Director P1 C 항 8종, 구분 불가 시 UNRESOLVED_FAILURE_CLASS
  4. metric redundancy 스캐폴드 — 8축(05 §3). 계산 틀만. 데이터 없음 -> 수치 없음.

금지사항 (이 파일이 지키는 것)
  * 새 조작화 없음. SSOT/Director 문안이 정하지 않은 것은 AMBIGUOUS_DEFINITION 으로 올린다.
  * threshold / cut-off / composite score 없음. "중복이다/아니다" 판정선 없음. 값만 낸다.
  * family n = 10. 45 pair 를 n=45 로 쓰지 않는다.
  * REAL 접속 없음. production / mart / raw evidence 수정 없음. git 없음.
  * 실패 사유를 추정으로 채우지 않는다.

MAIN50 실측 데이터는 아직 없다. 이 파일은 outcome-independent 준비물이다.
실행:  python lane_p_provenance_denominator.py            (fixture self-verification)
      python lane_p_provenance_denominator.py --input DIR (실입력 채점; 없으면 INPUT_ABSENT)
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

KST = timezone(timedelta(hours=9))

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
          "/research/landing_accessibility/research_d")
SSOTV3 = Path("/home/sieg/projects-wsl/ProjectFinal/SSOTV3")
OUT_DIR = RD / "results" / "harness" / "lane_p"
OUT_JSON = OUT_DIR / "LANE_P_HARNESS.json"
OUT_MD = OUT_DIR / "LANE_P_FINDINGS.md"

BASE_SHA = "7448184a811f5d7d8772f21488bb75418fde3313"
SSOT_MANIFEST_SHA = "1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a"

# 05 §1. 분석단위. 모든 비율에 붙는다.
GRAIN_PRIMARY = "service x frozen task"
FAMILY_N_FROZEN = 10          # 01 §2 / 05 §4 — family 별 고정 분모
FAMILY_IDS = ["F1", "F2", "F3", "F4", "F5"]


# =====================================================================
# 0. 변이(mutation) 스위치 — 탐지기를 일부러 틀리게 만들었을 때 fixture 가
#    잡는지 확인하기 위한 것. 컨텍스트 매니저가 항상 원복한다.
# =====================================================================
_MUTATIONS: set[str] = set()

MUTATION_CATALOG = {
    "M1_FILE_ABSENT_AS_PRESENT":
        "lineage 탐지기가 '파일 없음'을 PRESENT 로 처리한다 (파일/필드/값 3상태 뭉개기)",
    "M2_NULL_AS_KEY_MISSING":
        "lineage 탐지기가 FIELD_NULL 을 KEY_MISSING 과 같은 상태로 반환한다",
    "M3_NO_INPUT_ABSENT_GUARD":
        "빈/부재 입력에서 INPUT_ABSENT 를 내지 않고 '정상, hole 0' 처럼 보이게 한다",
    "M4_DENOMINATOR_NOT_NESTED":
        "분모 사슬이 단계 중첩을 강제하지 않아 앞 단계에서 빠진 target 이 뒤 단계에 다시 산입된다",
    "M5_GUESS_FAILURE_CLASS":
        "실패 사유 분해기가 구분 불가 케이스를 UNRESOLVED 로 두지 않고 TIMEOUT 으로 추정해 채운다",
}


@contextmanager
def mutation(*names: str):
    """변이를 켜고 반드시 원복한다."""
    before = set(_MUTATIONS)
    for n in names:
        if n not in MUTATION_CATALOG:
            raise KeyError(f"unknown mutation {n}")
        _MUTATIONS.add(n)
    try:
        yield
    finally:
        _MUTATIONS.clear()
        _MUTATIONS.update(before)


def _mut(name: str) -> bool:
    return name in _MUTATIONS


# =====================================================================
# 1. 입력 계약 + INPUT_ABSENT 구분
#    "빈 결과 함정 방어": 입력이 없을 때 절대 'hole 0 / 정상' 으로 보이면 안 된다.
# =====================================================================

INPUT_CONTRACT = {
    "layout": {
        "input_root/targets.jsonl":
            "한 줄 = 한 (family_id, service_id, task_id, run_id) 레코드. "
            "02 §8 identity = service_id + task_id + run_id.",
        "input_root/evidence/":
            "선택. lineage 포인터가 가리키는 evidence 파일 루트. "
            "이 디렉터리가 있어야 'FILE_ABSENT' 와 'FIELD_NULL' 을 구분할 수 있다.",
    },
    "record_fields": {
        "family_id": "01 §2 F1..F5",
        "service_id": "02 §2 dim_service_target.service_id",
        "task_id": "02 §2 dim_task_contract.task_id",
        "run_id": "02 §8. 없으면 attempted 아님",
        "precheck_status": "03 §2 ELIGIBLE_PUBLIC_MOBILE_WEB / APP_REQUIRED_EXCLUDE / "
                           "ACCESS_BLOCKED_REVIEW / URL_REMAP_REQUIRED",
        "freeze_status": "02 §2 dim_task_contract.freeze_status",
        "requested_url": "02 §2 / 03 §1",
        "final_url": "02 §2 / 03 §1",
        "l0_manifest_path": "03 §3 L0 surface capture manifest pointer",
        "ax_manifest_path": "03 §10 AX",
        "dom_manifest_path": "03 §10 DOM",
        "probe_manifest_path": "03 §10 probe/CSS geometry",
        "screenshot_manifest_path": "03 §10 screenshot",
        "evidence_manifest_sha": "03 §10 manifest SHA / 02 §8",
        "steps": "02 §4 fact_flow_step 배열",
        "endpoint_status": "04 §4 REACHED/AUTH_GATE/PUBLIC_WEB_UNOBSERVABLE/APP_REQUIRED/"
                           "EVIDENCE_DEFECT/BLOCKED/ABSTAIN",
        "task_flow_sequence": "04 §3 dismissal 제외 서비스 자체 task 경로",
        "ledger_entry": "원장 귀속 레코드 (D queue RQ-D11 / C-BLOCKER-220418 계열)",
        "failure_class_signal": "수집기가 명시 기록한 Director 8종 토큰. 없으면 추정하지 않는다",
        "termination_reason": "수집기가 명시 기록한 종료 사유 원문 토큰",
        "forbidden_action_terminal": "03 §6/§8 forbidden_action_set 때문에 종료했는지 (bool)",
    },
    "note": "필드가 '없는 것'과 'null 인 것'과 '0/빈 것'은 서로 다른 입력이다. "
            "이 하네스는 셋을 절대 같은 상태로 반환하지 않는다.",
}


def load_input(input_root: str | os.PathLike | None) -> dict:
    """
    입력을 읽는다. 다음을 서로 다른 상태로 구분해 반환한다.
      INPUT_ABSENT_PATH_NOT_GIVEN   경로 자체가 주어지지 않음
      INPUT_ABSENT_PATH_MISSING     경로가 존재하지 않음
      INPUT_ABSENT_NOT_A_DIR        경로가 디렉터리가 아님
      INPUT_ABSENT_MANIFEST_MISSING 디렉터리는 있으나 targets.jsonl 이 없음
      INPUT_ABSENT_ZERO_RECORDS     targets.jsonl 은 있으나 레코드 0건
      INPUT_PRESENT                 레코드 >= 1
    어떤 부재 상태에서도 records 는 비고, status 는 절대 INPUT_PRESENT 가 되지 않는다.
    """
    if _mut("M3_NO_INPUT_ABSENT_GUARD"):
        # 변이: 부재를 정상으로 위장한다.
        return {"status": "INPUT_PRESENT", "records": [], "input_root": str(input_root),
                "n_records": 0, "parse_errors": []}

    if input_root is None:
        return {"status": "INPUT_ABSENT_PATH_NOT_GIVEN", "records": [], "input_root": None,
                "n_records": 0, "parse_errors": []}
    p = Path(input_root)
    if not p.exists():
        return {"status": "INPUT_ABSENT_PATH_MISSING", "records": [], "input_root": str(p),
                "n_records": 0, "parse_errors": []}
    if not p.is_dir():
        return {"status": "INPUT_ABSENT_NOT_A_DIR", "records": [], "input_root": str(p),
                "n_records": 0, "parse_errors": []}
    manifest = p / "targets.jsonl"
    if not manifest.exists():
        return {"status": "INPUT_ABSENT_MANIFEST_MISSING", "records": [], "input_root": str(p),
                "n_records": 0, "parse_errors": [],
                "expected_manifest": str(manifest)}
    records, errors = [], []
    for i, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append({"line": i, "error": str(e)})
    if not records:
        return {"status": "INPUT_ABSENT_ZERO_RECORDS", "records": [], "input_root": str(p),
                "n_records": 0, "parse_errors": errors}
    return {"status": "INPUT_PRESENT", "records": records, "input_root": str(p),
            "n_records": len(records), "parse_errors": errors,
            "evidence_root": str(p / "evidence") if (p / "evidence").is_dir() else None}


def is_input_absent(loaded: dict) -> bool:
    return str(loaded.get("status", "")).startswith("INPUT_ABSENT")


# =====================================================================
# 2. lineage hole 탐지기  (Director P1 B)
#    사슬: requested URL -> final URL -> L0 -> AX -> DOM -> probe -> step
#          -> terminal -> ledger
#    파일 없음 / 필드 null / 값 0 을 서로 다른 상태로 낸다.
# =====================================================================

LINEAGE_CHAIN_VERBATIM = ("requested URL -> final URL -> L0 -> AX -> DOM -> probe -> step "
                          "-> terminal -> ledger")

# (node, kind, record_key)
LINEAGE_NODES: list[tuple[str, str, str]] = [
    ("requested_url", "SCALAR_URL", "requested_url"),
    ("final_url",     "SCALAR_URL", "final_url"),
    ("l0",            "ARTIFACT_POINTER", "l0_manifest_path"),
    ("ax",            "ARTIFACT_POINTER", "ax_manifest_path"),
    ("dom",           "ARTIFACT_POINTER", "dom_manifest_path"),
    ("probe",         "ARTIFACT_POINTER", "probe_manifest_path"),
    ("step",          "COLLECTION", "steps"),
    ("terminal",      "SCALAR_CATEGORICAL", "endpoint_status"),
    ("ledger",        "RECORD", "ledger_entry"),
]

NODE_STATES = {
    "PRESENT":       "값이 있고, 포인터면 파일이 실재하며 비어있지 않다",
    "KEY_MISSING":   "레코드에 그 키 자체가 없다",
    "FIELD_NULL":    "키는 있으나 값이 null 이다",
    "VALUE_EMPTY":   "값이 빈 문자열/빈 리스트/빈 객체다",
    "VALUE_ZERO":    "값이 수치 0 이다 (예: step 수 0)",
    "FILE_ABSENT":   "포인터 값은 있으나 그 경로에 파일이 없다",
    "FILE_EMPTY":    "파일은 있으나 0 바이트다",
    "EVIDENCE_ROOT_UNKNOWN":
        "포인터 값은 있으나 evidence_root 가 주어지지 않아 파일 실재를 확인할 수 없다 "
        "(FILE_ABSENT 라고 주장하지 않는다)",
}
HOLE_STATES = {s for s in NODE_STATES if s != "PRESENT"}


def _classify_node(rec: dict, key: str, kind: str, evidence_root: Path | None) -> dict:
    if key not in rec:
        st = "KEY_MISSING"
        if _mut("M2_NULL_AS_KEY_MISSING"):
            pass  # KEY_MISSING 은 그대로
        return {"state": st, "raw": None}
    v = rec[key]
    if v is None:
        st = "KEY_MISSING" if _mut("M2_NULL_AS_KEY_MISSING") else "FIELD_NULL"
        return {"state": st, "raw": None}

    if kind == "COLLECTION":
        if isinstance(v, (list, tuple)):
            if len(v) == 0:
                return {"state": "VALUE_ZERO", "raw": 0, "count": 0}
            return {"state": "PRESENT", "raw": len(v), "count": len(v)}
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return ({"state": "VALUE_ZERO", "raw": 0, "count": 0} if v == 0
                    else {"state": "PRESENT", "raw": v, "count": int(v)})
        return {"state": "VALUE_EMPTY", "raw": v}

    if isinstance(v, str):
        if v.strip() == "":
            return {"state": "VALUE_EMPTY", "raw": ""}
    elif isinstance(v, dict):
        return ({"state": "VALUE_EMPTY", "raw": {}} if len(v) == 0
                else {"state": "PRESENT", "raw": f"<record:{len(v)} keys>"})
    elif isinstance(v, (int, float)) and not isinstance(v, bool):
        if v == 0:
            return {"state": "VALUE_ZERO", "raw": 0}

    if kind == "ARTIFACT_POINTER":
        if evidence_root is None:
            return {"state": "EVIDENCE_ROOT_UNKNOWN", "raw": v}
        fp = Path(v)
        if not fp.is_absolute():
            fp = evidence_root / v
        if not fp.exists():
            if _mut("M1_FILE_ABSENT_AS_PRESENT"):
                return {"state": "PRESENT", "raw": v}
            return {"state": "FILE_ABSENT", "raw": v, "resolved_path": str(fp)}
        if fp.is_file() and fp.stat().st_size == 0:
            return {"state": "FILE_EMPTY", "raw": v, "resolved_path": str(fp)}
        return {"state": "PRESENT", "raw": v, "resolved_path": str(fp)}

    return {"state": "PRESENT", "raw": v}


def detect_lineage_holes(rec: dict, evidence_root: Path | None = None) -> dict:
    """
    한 target 의 9노드 사슬 상태를 낸다.
    하류 노드를 상류 결손으로 가리지 않는다 — 각 노드를 독립 평가하고 전부 보고한다.
    """
    nodes: dict[str, dict] = {}
    for name, kind, key in LINEAGE_NODES:
        r = _classify_node(rec, key, kind, evidence_root)
        r["kind"] = kind
        r["record_key"] = key
        nodes[name] = r
    holes = [n for n, r in nodes.items() if r["state"] in HOLE_STATES]
    order = [n for n, _, _ in LINEAGE_NODES]
    first_break = next((n for n in order if nodes[n]["state"] in HOLE_STATES), None)
    return {
        "target_key": target_key(rec),
        "chain": LINEAGE_CHAIN_VERBATIM,
        "nodes": nodes,
        "hole_nodes": holes,
        "hole_count": len(holes),
        "hole_states": {n: nodes[n]["state"] for n in holes},
        "first_break_node": first_break,
        "intact": len(holes) == 0,
    }


def target_key(rec: dict) -> str:
    """02 §8 — service_id + task_id + run_id 로 identity 구성. display name 을 id 로 쓰지 않는다."""
    return "|".join(str(rec.get(k)) for k in ("service_id", "task_id", "run_id"))


def lineage_report(loaded: dict) -> dict:
    if is_input_absent(loaded):
        return {"status": loaded["status"], "computed": False,
                "reason": "입력 부재. hole 0 이 아니라 '측정하지 않았다'.",
                "n_targets": 0, "per_target": [], "hole_node_frequency": {}}
    er = loaded.get("evidence_root")
    evidence_root = Path(er) if er else None
    per = [detect_lineage_holes(r, evidence_root) for r in loaded["records"]]
    freq: dict[str, dict[str, int]] = {}
    for p in per:
        for n, st in p["hole_states"].items():
            freq.setdefault(n, {}).setdefault(st, 0)
            freq[n][st] += 1
    return {
        "status": "COMPUTED", "computed": True,
        "evidence_root_available": evidence_root is not None,
        "n_targets": len(per),
        "n_intact": sum(1 for p in per if p["intact"]),
        "n_with_holes": sum(1 for p in per if not p["intact"]),
        "hole_node_frequency": freq,
        "per_target": per,
    }


# =====================================================================
# 3. 분모 사슬 계산기  (05 §6)
#    candidate 10 -> eligible/frozen 10 -> attempted 10
#                 -> evidence-bearing n -> flow-evaluable n
# =====================================================================

DENOMINATOR_CHAIN_VERBATIM = ("candidate 10 → eligible/frozen 10 → attempted 10 "
                              "→ evidence-bearing n → flow-evaluable n")

# 03 §10 이 열거한 evidence package 구성요소.
EVIDENCE_COMPONENTS = [
    ("dom", "dom_manifest_path"),
    ("ax", "ax_manifest_path"),
    ("screenshot", "screenshot_manifest_path"),
    ("probe", "probe_manifest_path"),
    ("url", "final_url"),
    ("manifest_sha", "evidence_manifest_sha"),
]


def _present(rec: dict, key: str, kind: str, evidence_root: Path | None) -> bool:
    return _classify_node(rec, key, kind, evidence_root)["state"] == "PRESENT"


def stage_candidate(rec: dict, evidence_root=None) -> bool:
    # 01 §4 frame 에 실린 모든 후보. 입력 레코드 존재 자체.
    return True


def stage_eligible_frozen(rec: dict, evidence_root=None) -> bool:
    # 03 §2 precheck + 02 §2 freeze_status
    return (rec.get("precheck_status") == "ELIGIBLE_PUBLIC_MOBILE_WEB"
            and str(rec.get("freeze_status", "")).upper() == "FROZEN")


def stage_attempted(rec: dict, evidence_root=None) -> bool:
    # 02 §8 run identity 가 있으면 시도된 것.
    v = rec.get("run_id")
    return isinstance(v, str) and v.strip() != ""


def stage_evidence_bearing_strict(rec: dict, evidence_root=None) -> bool:
    """03 §10 이 열거한 구성요소가 전부 PRESENT."""
    for _, key in EVIDENCE_COMPONENTS:
        kind = "ARTIFACT_POINTER" if key.endswith("_path") else "SCALAR_URL"
        if not _present(rec, key, kind, evidence_root):
            return False
    return True


def stage_evidence_bearing_permissive(rec: dict, evidence_root=None) -> bool:
    """구성요소 중 하나라도 PRESENT."""
    for _, key in EVIDENCE_COMPONENTS:
        kind = "ARTIFACT_POINTER" if key.endswith("_path") else "SCALAR_URL"
        if _present(rec, key, kind, evidence_root):
            return True
    return False


def stage_flow_evaluable_strict(rec: dict, evidence_root=None) -> bool:
    """
    04 §3 task_flow_sequence 가 비어있지 않고, 04 §4 endpoint_status 가
    경로가 끝까지 확정된 값(REACHED / AUTH_GATE)인 경우.
    """
    seq = rec.get("task_flow_sequence")
    if not isinstance(seq, (list, tuple)) or len(seq) == 0:
        return False
    return rec.get("endpoint_status") in ("REACHED", "AUTH_GATE")


def stage_flow_evaluable_permissive(rec: dict, evidence_root=None) -> bool:
    """task_flow_sequence 가 비어있지 않기만 하면 된다 (terminal 값 무관)."""
    seq = rec.get("task_flow_sequence")
    return isinstance(seq, (list, tuple)) and len(seq) > 0


# variant 이름 -> 4·5단계 predicate 쌍. 어느 쪽이 옳은지 이 하네스는 고르지 않는다.
DENOM_VARIANTS = {
    "STRICT": (stage_evidence_bearing_strict, stage_flow_evaluable_strict),
    "PERMISSIVE": (stage_evidence_bearing_permissive, stage_flow_evaluable_permissive),
}


def denominator_chain(records: Sequence[dict], evidence_root: Path | None = None,
                      variant: str = "STRICT") -> dict:
    """
    family 별 단계별 분모 + 각 단계에서 빠지는 target id 목록.
    중첩 강제: 단계 k 를 통과하려면 k-1 을 통과해야 한다.
    """
    ev_pred, flow_pred = DENOM_VARIANTS[variant]
    stages = [
        ("candidate", stage_candidate),
        ("eligible_frozen", stage_eligible_frozen),
        ("attempted", stage_attempted),
        ("evidence_bearing", ev_pred),
        ("flow_evaluable", flow_pred),
    ]
    by_fam: dict[str, list[dict]] = {}
    for r in records:
        by_fam.setdefault(str(r.get("family_id")), []).append(r)

    out: dict[str, Any] = {"variant": variant, "grain": GRAIN_PRIMARY,
                           "chain": DENOMINATOR_CHAIN_VERBATIM, "families": {}}
    for fam in sorted(by_fam):
        recs = by_fam[fam]
        surviving = list(recs)
        fam_stages, drops = {}, {}
        prev_name = None
        for name, pred in stages:
            if _mut("M4_DENOMINATOR_NOT_NESTED"):
                pool = list(recs)          # 변이: 중첩 무시, 매 단계 전체 모집단에서 재평가
            else:
                pool = surviving
            # 값 동등(==)이 아니라 객체 identity 로 가른다. 결정적 predicate 에서는 값 비교로도
            # 같은 수가 나오지만, 중복 레코드가 섞였을 때 귀속을 값에 의존시키지 않기 위한 방어다.
            passed = [r for r in pool if pred(r, evidence_root)]
            passed_ids = {id(r) for r in passed}
            dropped = [r for r in pool if id(r) not in passed_ids]
            fam_stages[name] = len(passed)
            drops[name] = {
                "n_dropped_here": len(dropped),
                "dropped_target_ids": sorted(target_key(r) for r in dropped),
                "dropped_from_stage": prev_name,
            }
            surviving = passed
            prev_name = name

        n_frame = len(recs)
        fam_stages_declared = dict(fam_stages)

        # 02 §8 identity 중복 — 같은 service_id+task_id+run_id 가 두 번 실리면 분모가 조용히
        # 부풀거나(중복 계상) target 이 가려진다. 합치지 않고 사실대로 드러낸다.
        key_counts: dict[str, int] = {}
        for r in recs:
            k = target_key(r)
            key_counts[k] = key_counts.get(k, 0) + 1
        dup_keys = {k: c for k, c in key_counts.items() if c > 1}
        # 05 §4 — family 분모는 n=10 으로 고정. 입력이 10 이 아니면 사실대로 표시한다.
        frame_note = None
        if n_frame != FAMILY_N_FROZEN:
            frame_note = (f"입력 레코드 {n_frame} 건. 05 §4 는 family 분모를 "
                          f"{FAMILY_N_FROZEN} 으로 고정한다 — 불일치를 은닉하지 않는다.")

        ratios = {}
        for name in ("eligible_frozen", "attempted", "evidence_bearing", "flow_evaluable"):
            ratios[f"{name}_over_candidate"] = ratio(
                fam_stages[name], fam_stages["candidate"], GRAIN_PRIMARY,
                f"{name} / candidate, family {fam}")
        ratios["flow_evaluable_over_frozen_10"] = ratio(
            fam_stages["flow_evaluable"], FAMILY_N_FROZEN, GRAIN_PRIMARY,
            f"flow_evaluable / 고정 frozen 분모 10, family {fam}")

        out["families"][fam] = {
            "n_input_records": n_frame,
            "n_distinct_target_keys": len(key_counts),
            "duplicate_target_keys": dup_keys,
            "duplicate_identity_present": bool(dup_keys),
            "frame_note": frame_note,
            "stage_denominators": fam_stages_declared,
            "drops": drops,
            "ratios": ratios,
            "silent_loss_total": fam_stages["candidate"] - fam_stages["flow_evaluable"],
            "silent_loss_ids": sorted(
                set(itertools.chain.from_iterable(
                    d["dropped_target_ids"] for d in drops.values()))),
        }
    return out


def ratio(num: int, den: int, grain: str, label: str) -> dict:
    """비율에는 언제나 분자/분모/grain 을 붙인다 (D queue ruling_11)."""
    return {"numerator": int(num), "denominator": int(den), "grain": grain, "label": label,
            "value": (round(num / den, 6) if den else None),
            "value_undefined_reason": (None if den else "denominator == 0")}


def denominator_report(loaded: dict) -> dict:
    if is_input_absent(loaded):
        return {"status": loaded["status"], "computed": False,
                "reason": "입력 부재. 단계별 분모를 0 으로 보고하지 않는다 — 측정 자체가 없다.",
                "variants": {}}
    er = loaded.get("evidence_root")
    evidence_root = Path(er) if er else None
    return {"status": "COMPUTED", "computed": True,
            "variants": {v: denominator_chain(loaded["records"], evidence_root, v)
                         for v in DENOM_VARIANTS},
            "variant_selection": "NOT_SELECTED — 어느 predicate 가 SSOT 의도인지 정해져 있지 "
                                 "않다. AMBIGUOUS_DEFINITION AD-02/AD-03 참조."}


# =====================================================================
# 4. 실패 사유 분해기  (Director P1 C — 8종)
#    추정으로 채우지 않는다. 8종을 하나로 묶지 않는다.
# =====================================================================

FAILURE_CLASSES = {
    "PUBLIC_MOBILE_WEB_ABSENT":
        "public mobile web 부재 — 01 §1 제외조건 / 03 §2 APP_REQUIRED_EXCLUDE",
    "WAF_CHALLENGE":
        "WAF·challenge — 03 §8 'CAPTCHA 해결/우회 금지. active blocking challenge만 terminal'",
    "TIMEOUT":
        "timeout — 수집기 종료 사유. SSOT 에 대응 endpoint_status 값 없음",
    "EVIDENCE_DEFECT":
        "evidence defect — 04 §4 EVIDENCE_DEFECT / 05 §5 'structural failure로 재분류하지 않는다'",
    "DISABLED_INERT":
        "disabled·inert — 대응 SSOT 필드 없음. 명시 signal 로만 확정",
    "FORBIDDEN_ACTION":
        "forbidden action — 02 §2 forbidden_action_set / 03 §6·§8 금지행위로 진행 불가",
    "AUTH_GATE":
        "auth gate — 03 §7 / 04 §2·§4 AUTH_GATE",
    "GENUINE_TASK_SURFACE_ABSENCE":
        "genuine task surface absence — 서비스에 해당 과업 surface 자체가 없음",
    "UNRESOLVED_FAILURE_CLASS":
        "입력이 위 8종을 구분하지 못한다. 추정으로 채우지 않는다",
}

# AUTH_GATE 는 01 §1 에서 '정당한 종료'로 포함조건에 들어있다. Director 목록에 실패사유로
# 함께 열거돼 있으나 SSOT 상 지위가 다르므로 표시를 붙인다 (아래 is_ssot_legitimate_terminal).
SSOT_LEGITIMATE_TERMINALS = {"AUTH_GATE"}

# SSOT 문안이 값을 일의적으로 정하는 경우에만 파생한다. 나머지는 파생하지 않는다.
_TERMINAL_DERIVATION = {
    "AUTH_GATE": ("AUTH_GATE", "04 §4 endpoint_status=AUTH_GATE; 03 §7 auth terminal"),
    "EVIDENCE_DEFECT": ("EVIDENCE_DEFECT",
                        "04 §4 endpoint_status=EVIDENCE_DEFECT; 05 §5 재분류 금지"),
    "APP_REQUIRED": ("PUBLIC_MOBILE_WEB_ABSENT",
                     "04 §4 endpoint_status=APP_REQUIRED; 03 §2 APP_REQUIRED_EXCLUDE"),
}
# 일의적이지 않은 terminal 값 -> 왜 못 가르는지.
_TERMINAL_AMBIGUOUS = {
    "BLOCKED": "WAF_CHALLENGE 와 TIMEOUT 을 구분하지 못한다. 04 §4 는 BLOCKED 하나만 둔다",
    "PUBLIC_WEB_UNOBSERVABLE":
        "PUBLIC_MOBILE_WEB_ABSENT 와 GENUINE_TASK_SURFACE_ABSENCE 를 구분하지 못한다",
    "ABSTAIN": "04 §2 ABSTAIN 은 '억지 판정하지 않는다'는 선언이지 사유 분류가 아니다",
}


def resolve_failure_class(rec: dict) -> dict:
    """
    한 target 의 실패 사유를 8종 중 하나로 확정하거나 UNRESOLVED_FAILURE_CLASS 로 남긴다.
    확정 근거는 두 가지뿐이다.
      (a) 수집기가 명시 기록한 failure_class_signal / termination_reason / forbidden_action_terminal
      (b) SSOT 문안이 일의적으로 정하는 terminal 값 파생
    (a)와 (b)가 충돌하면 조용히 고르지 않고 SIGNAL_CONFLICT 로 남긴 뒤 UNRESOLVED 로 둔다.
    """
    evidence: list[dict] = []
    explicit = None
    sig = rec.get("failure_class_signal")
    if isinstance(sig, str) and sig.strip():
        s = sig.strip().upper()
        if s in FAILURE_CLASSES and s != "UNRESOLVED_FAILURE_CLASS":
            explicit = s
            evidence.append({"source": "failure_class_signal", "value": s, "kind": "EXPLICIT"})
        else:
            evidence.append({"source": "failure_class_signal", "value": sig,
                             "kind": "UNRECOGNISED_TOKEN"})
    tr = rec.get("termination_reason")
    if explicit is None and isinstance(tr, str) and tr.strip().upper() in FAILURE_CLASSES:
        explicit = tr.strip().upper()
        evidence.append({"source": "termination_reason", "value": explicit, "kind": "EXPLICIT"})
    if explicit is None and rec.get("forbidden_action_terminal") is True:
        explicit = "FORBIDDEN_ACTION"
        evidence.append({"source": "forbidden_action_terminal", "value": True,
                         "kind": "EXPLICIT", "cites": "03 §6/§8"})

    derived, derived_why = None, None
    term = rec.get("endpoint_status")
    if term in _TERMINAL_DERIVATION:
        derived, derived_why = _TERMINAL_DERIVATION[term]
        evidence.append({"source": "endpoint_status", "value": term, "kind": "SSOT_DERIVED",
                         "cites": derived_why})
    elif term in _TERMINAL_AMBIGUOUS:
        evidence.append({"source": "endpoint_status", "value": term, "kind": "SSOT_AMBIGUOUS",
                         "cites": _TERMINAL_AMBIGUOUS[term]})

    conflict = (explicit is not None and derived is not None and explicit != derived)
    if conflict:
        cls, basis = "UNRESOLVED_FAILURE_CLASS", "SIGNAL_CONFLICT"
    elif explicit is not None:
        cls, basis = explicit, "EXPLICIT_SIGNAL"
    elif derived is not None:
        cls, basis = derived, "SSOT_DERIVED"
    else:
        cls, basis = "UNRESOLVED_FAILURE_CLASS", "NO_DISTINGUISHING_INPUT"
        if _mut("M5_GUESS_FAILURE_CLASS"):
            cls, basis = "TIMEOUT", "GUESSED"

    return {
        "target_key": target_key(rec),
        "failure_class": cls,
        "basis": basis,
        "explicit_signal": explicit,
        "ssot_derived": derived,
        "signal_conflict": conflict,
        "is_ssot_legitimate_terminal": cls in SSOT_LEGITIMATE_TERMINALS,
        "evidence": evidence,
    }


def failure_report(loaded: dict) -> dict:
    if is_input_absent(loaded):
        return {"status": loaded["status"], "computed": False,
                "reason": "입력 부재. 실패 분류 분포를 0 으로 보고하지 않는다.",
                "distribution": {}, "per_target": []}
    per = [resolve_failure_class(r) for r in loaded["records"]]
    dist: dict[str, int] = {}
    for p in per:
        dist[p["failure_class"]] = dist.get(p["failure_class"], 0) + 1
    n = len(per)
    return {
        "status": "COMPUTED", "computed": True,
        "n_targets": n,
        "distribution": dist,
        "distribution_ratios": {k: ratio(v, n, GRAIN_PRIMARY, f"failure_class={k}")
                                for k, v in dist.items()},
        "n_unresolved": dist.get("UNRESOLVED_FAILURE_CLASS", 0),
        "n_signal_conflict": sum(1 for p in per if p["signal_conflict"]),
        "per_target": per,
    }


# =====================================================================
# 5. metric redundancy 평가 스캐폴드  (05 §3 — 8축)
#    계산 틀만. 데이터 없음 -> 수치 없음. 판정선 없음.
# =====================================================================

STFP_AXES = ["Spatial", "Label", "Control", "Reveal", "Sequence", "Depth", "Auth", "Obstruction"]

AXIS_SOURCE_FIELDS = {   # 05 §2 / 04 §4 에서 각 축이 소비하는 변수
    "Spatial": ["entry_x_norm", "entry_y_norm", "entry_zone"],
    "Label": ["visible_label_text", "accessible_name", "accessible_name_source", "label_relation"],
    "Control": ["entry_control_type", "entry_label_modality"],
    "Reveal": ["nav_container_type", "reveal_direction", "nav_container_depth", "menu_dependency"],
    "Sequence": ["task_flow_sequence", "experienced_flow_sequence", "flow_step_count"],
    "Depth": ["activation_depth"],
    "Auth": ["auth_gate_stage"],
    "Obstruction": ["forced_dismissal_count", "task_control_occlusion"],
}


def _rankdata(a: np.ndarray) -> np.ndarray:
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), float)
    ranks[order] = np.arange(1, len(a) + 1, dtype=float)
    # 동점 평균 순위
    vals, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    for i, c in enumerate(cnt):
        if c > 1:
            m = inv == i
            ranks[m] = ranks[m].mean()
    return ranks


def spearman_rho(x: Sequence[float], y: Sequence[float]) -> dict:
    """순위상관. 판정선 없음 — 값과 n 만."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y))
    n = int(ok.sum())
    if n < 3:
        return {"rho": None, "n_pairs": n, "grain": GRAIN_PRIMARY,
                "undefined_reason": "n_pairs < 3"}
    rx, ry = _rankdata(x[ok]), _rankdata(y[ok])
    sx, sy = rx.std(), ry.std()
    if sx == 0 or sy == 0:
        return {"rho": None, "n_pairs": n, "grain": GRAIN_PRIMARY,
                "undefined_reason": "zero variance in one rank vector"}
    return {"rho": float(np.corrcoef(rx, ry)[0, 1]), "n_pairs": n, "grain": GRAIN_PRIMARY}


def mutual_information_discrete(x: Sequence, y: Sequence, base: float = 2.0) -> dict:
    """
    범주형 두 축의 상호정보량 + 정규화 변형(NMI, 불확실성계수). 판정선 없음.
    None/NaN 은 결측으로 빼고, 뺀 수를 명시한다.
    """
    pairs = [(a, b) for a, b in zip(x, y)
             if a is not None and b is not None
             and not (isinstance(a, float) and math.isnan(a))
             and not (isinstance(b, float) and math.isnan(b))]
    n = len(pairs)
    n_dropped = len(list(x)) - n
    if n == 0:
        return {"mi": None, "n_pairs": 0, "n_dropped_missing": n_dropped,
                "grain": GRAIN_PRIMARY, "undefined_reason": "n_pairs == 0"}
    jx: dict = {}; mx: dict = {}; my: dict = {}
    for a, b in pairs:
        jx[(a, b)] = jx.get((a, b), 0) + 1
        mx[a] = mx.get(a, 0) + 1
        my[b] = my.get(b, 0) + 1
    log = lambda v: math.log(v, base)
    mi = sum((c / n) * log((c / n) / ((mx[a] / n) * (my[b] / n))) for (a, b), c in jx.items())
    hx = -sum((c / n) * log(c / n) for c in mx.values())
    hy = -sum((c / n) * log(c / n) for c in my.values())
    denom = math.sqrt(hx * hy)
    return {
        "mi": float(mi), "h_x": float(hx), "h_y": float(hy),
        "nmi_sqrt": (float(mi / denom) if denom > 0 else None),
        "uncertainty_coefficient_y_given_x": (float(mi / hy) if hy > 0 else None),
        "uncertainty_coefficient_x_given_y": (float(mi / hx) if hx > 0 else None),
        "n_pairs": n, "n_dropped_missing": n_dropped, "grain": GRAIN_PRIMARY,
        "log_base": base,
    }


def jaccard(a: Iterable, b: Iterable) -> dict:
    """집합 Jaccard. 판정선 없음."""
    sa, sb = set(a), set(b)
    u = len(sa | sb)
    return {"jaccard": (float(len(sa & sb) / u) if u else None),
            "intersection": len(sa & sb), "union": u,
            "n_a": len(sa), "n_b": len(sb), "grain": "set of tokens",
            "undefined_reason": (None if u else "union == 0")}


def axis_pair_grid() -> list[tuple[str, str]]:
    """8축의 28개 비순서쌍. family 45 pair 와 다른 대상이다 — 혼동 금지."""
    return list(itertools.combinations(STFP_AXES, 2))


def metric_redundancy_scaffold(axis_table: dict[str, Sequence] | None = None) -> dict:
    """
    8축 중복 평가 '틀'. 데이터가 없으면 수치를 내지 않고 NOT_COMPUTED_NO_DATA 를 낸다.
    이 함수는 '중복이다/아니다' 를 절대 판정하지 않는다 — threshold 를 갖지 않는다.
    """
    pairs = axis_pair_grid()
    base = {
        "axes": STFP_AXES,
        "axis_source_fields": AXIS_SOURCE_FIELDS,
        "n_axis_pairs": len(pairs),
        "axis_pairs": [f"{a}~{b}" for a, b in pairs],
        "measures_implemented": ["spearman_rho", "mutual_information_discrete", "jaccard"],
        "threshold_policy": "NO_THRESHOLD — 중복 판정선을 만들지 않는다. 값만 낸다.",
        "grain": GRAIN_PRIMARY,
        "n_warning": (f"family n={FAMILY_N_FROZEN}. family 내 45 pair 는 distance matrix cell "
                      f"이지 독립표본 n=45 가 아니다 (05 §1). 축쌍 28 도 관측단위가 아니다."),
    }
    if not axis_table:
        base["status"] = "NOT_COMPUTED_NO_DATA"
        base["reason"] = ("MAIN50 실측 없음. 05 §3 8축 vector 가 존재하지 않으므로 "
                          "상관·상호정보·Jaccard 를 산출하지 않는다.")
        base["results"] = None
        return base
    res = {}
    for a, b in pairs:
        if a not in axis_table or b not in axis_table:
            res[f"{a}~{b}"] = {"status": "AXIS_ABSENT"}
            continue
        va, vb = list(axis_table[a]), list(axis_table[b])
        cell: dict[str, Any] = {"status": "COMPUTED", "n_rows": len(va)}
        try:
            cell["spearman"] = spearman_rho([float(v) if v is not None else float("nan")
                                             for v in va],
                                            [float(v) if v is not None else float("nan")
                                             for v in vb])
        except (TypeError, ValueError):
            cell["spearman"] = {"rho": None,
                                "undefined_reason": "non-numeric axis; use mutual information"}
        cell["mutual_information"] = mutual_information_discrete(va, vb)
        cell["jaccard_of_observed_levels"] = jaccard(
            [v for v in va if v is not None], [v for v in vb if v is not None])
        res[f"{a}~{b}"] = cell
    base["status"] = "COMPUTED"
    base["results"] = res
    return base


# =====================================================================
# 6. Manski worst-case bound — 폭만. 판정선 없음.
#    방법만 RQ-D7 (tools/rq_d7_denominator_bounds.py) 에서 가져오고, 수치는 재사용하지 않는다.
# =====================================================================

def manski_proportion_bound(k_yes: int, k_no: int, n_unresolved: int,
                            denominator: int, grain: str = GRAIN_PRIMARY) -> dict:
    """
    분모가 고정(예: family n=10)인 비율에서 미해결 n_unresolved 건이 최악으로 배치됐을 때의
    하한/상한. 폭만 낸다 — '좁다/넓다' 판정 없음.
    """
    if denominator <= 0:
        return {"lower": None, "upper": None, "width": None, "denominator": 0,
                "grain": grain, "undefined_reason": "denominator == 0"}
    lo = k_yes / denominator
    hi = (k_yes + n_unresolved) / denominator
    return {
        "point_complete_case": (round(k_yes / (k_yes + k_no), 6) if (k_yes + k_no) else None),
        "complete_case_numerator": k_yes,
        "complete_case_denominator": (k_yes + k_no),
        "lower": round(lo, 6), "upper": round(min(hi, 1.0), 6),
        "width": round(min(hi, 1.0) - lo, 6),
        "n_unresolved": n_unresolved, "denominator": denominator, "grain": grain,
        "interpretation_policy": "폭만 보고한다. 식별/비식별 판정, threshold, 재수집 권고 없음.",
    }


def manski_rd_width(k1_yes: int, k1_no: int, m1: int, n1: int,
                    k2_yes: int, k2_no: int, m2: int, n2: int,
                    grain: str = GRAIN_PRIMARY) -> dict:
    """
    두 family 비율차(RD)의 worst-case bound 폭. 부호가 갈라지는지만 사실로 적고 판정하지 않는다.
    """
    b1 = manski_proportion_bound(k1_yes, k1_no, m1, n1, grain)
    b2 = manski_proportion_bound(k2_yes, k2_no, m2, n2, grain)
    if b1["lower"] is None or b2["lower"] is None:
        return {"rd_lower": None, "rd_upper": None, "rd_width": None,
                "grain": grain, "undefined_reason": "component bound undefined"}
    lo = b1["lower"] - b2["upper"]
    hi = b1["upper"] - b2["lower"]
    return {
        "rd_lower": round(lo, 6), "rd_upper": round(hi, 6), "rd_width": round(hi - lo, 6),
        "sign_constant_over_bound": bool(lo > 0 or hi < 0),
        "arm1": b1, "arm2": b2, "grain": grain,
        "interpretation_policy": "폭과 부호 불변 여부만 사실로 적는다. GO/NO-GO 없음.",
    }


# =====================================================================
# 7. 합성 fixture — 양방향 대조 + 3상태 구분 + INPUT_ABSENT + 변이 검사
# =====================================================================

def _intact_record(fam: str, i: int, ev_dir: Path) -> dict:
    sid = f"SYN-{fam}-{i:02d}"
    return {
        "family_id": fam,
        "service_id": sid,
        "task_id": f"T-{fam}-PRIMARY",
        "run_id": f"RUN-{sid}-001",
        "precheck_status": "ELIGIBLE_PUBLIC_MOBILE_WEB",
        "freeze_status": "FROZEN",
        "requested_url": f"https://synthetic.invalid/{sid}",
        "final_url": f"https://synthetic.invalid/{sid}/final",
        "l0_manifest_path": f"{sid}/l0.json",
        "ax_manifest_path": f"{sid}/ax.json",
        "dom_manifest_path": f"{sid}/dom.json",
        "probe_manifest_path": f"{sid}/probe.json",
        "screenshot_manifest_path": f"{sid}/shot.json",
        "evidence_manifest_sha": hashlib.sha256(sid.encode()).hexdigest(),
        "steps": [{"step_index": 0, "action_token": "SELECT_FUNCTION"}],
        "endpoint_status": "REACHED",
        "task_flow_sequence": ["SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "ledger_entry": {"ledger_run_id": f"RUN-{sid}-001", "measured": True},
    }


def _write_fixture(root: Path, records: Sequence[dict], with_files: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    ev = root / "evidence"
    if with_files:
        ev.mkdir(parents=True, exist_ok=True)
        for r in records:
            for k in ("l0_manifest_path", "ax_manifest_path", "dom_manifest_path",
                      "probe_manifest_path", "screenshot_manifest_path"):
                v = r.get(k)
                if isinstance(v, str) and v:
                    fp = ev / v
                    fp.parent.mkdir(parents=True, exist_ok=True)
                    if not fp.exists():
                        fp.write_text('{"synthetic": true}', encoding="utf-8")
    (root / "targets.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    return root


def run_fixtures(work: Path) -> dict:
    """양방향 대조. 통과/불통과를 명시적으로 낸다."""
    results: dict[str, Any] = {}
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: Any = None):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})
        return ok

    # ---- A. 온전한 사슬 -> hole 0 --------------------------------------
    fam_recs = [_intact_record("F1", i, work) for i in range(1, FAMILY_N_FROZEN + 1)]
    root_ok = _write_fixture(work / "intact", fam_recs)
    ld = load_input(root_ok)
    lr = lineage_report(ld)
    results["A_intact"] = {
        "input_status": ld["status"], "n_targets": lr["n_targets"],
        "n_intact": lr["n_intact"], "n_with_holes": lr["n_with_holes"],
    }
    check("A1_intact_input_present", ld["status"] == "INPUT_PRESENT", ld["status"])
    check("A2_intact_zero_holes", lr["n_with_holes"] == 0, lr["hole_node_frequency"])
    dr = denominator_report(ld)
    st = dr["variants"]["STRICT"]["families"]["F1"]["stage_denominators"]
    results["A_intact"]["denominator_STRICT"] = st
    check("A3_intact_all_stages_10",
          all(st[k] == FAMILY_N_FROZEN for k in st), st)

    # ---- B. 9노드 각각을 하나씩 끊는다 -> 정확히 그 노드만 잡혀야 한다 ----
    cut_specs = {
        "requested_url": ("requested_url", "DROP_KEY"),
        "final_url": ("final_url", "DROP_KEY"),
        "l0": ("l0_manifest_path", "DELETE_FILE"),
        "ax": ("ax_manifest_path", "DELETE_FILE"),
        "dom": ("dom_manifest_path", "DELETE_FILE"),
        "probe": ("probe_manifest_path", "DELETE_FILE"),
        "step": ("steps", "EMPTY_LIST"),
        "terminal": ("endpoint_status", "SET_NULL"),
        "ledger": ("ledger_entry", "SET_NULL"),
    }
    per_cut = {}
    for node, (key, how) in cut_specs.items():
        recs = [json.loads(json.dumps(r)) for r in fam_recs]
        victim = recs[0]
        if how == "DROP_KEY":
            victim.pop(key, None)
        elif how == "SET_NULL":
            victim[key] = None
        elif how == "EMPTY_LIST":
            victim[key] = []
        root = _write_fixture(work / f"cut_{node}", recs)
        if how == "DELETE_FILE":
            fp = root / "evidence" / victim[key]
            if fp.exists():
                fp.unlink()
        ldc = load_input(root)
        lrc = lineage_report(ldc)
        holed = [p for p in lrc["per_target"] if not p["intact"]]
        got_nodes = sorted(set(itertools.chain.from_iterable(p["hole_nodes"] for p in holed)))
        ok = (len(holed) == 1 and got_nodes == [node])
        per_cut[node] = {"expected_node": node, "observed_hole_nodes": got_nodes,
                         "n_targets_with_holes": len(holed),
                         "observed_state": (holed[0]["hole_states"].get(node) if holed else None),
                         "exact_match": ok}
        check(f"B_cut_{node}_exactly_that_node", ok, per_cut[node])
    results["B_single_node_cuts"] = per_cut

    # ---- C. 파일 없음 / 필드 null / 값 0 은 서로 다른 상태여야 한다 -----
    three: dict[str, str] = {}
    # C-1 파일 없음
    recs = [json.loads(json.dumps(r)) for r in fam_recs]
    root = _write_fixture(work / "three_file_absent", recs)
    (root / "evidence" / recs[0]["dom_manifest_path"]).unlink()
    three["FILE_ABSENT_case"] = lineage_report(load_input(root))["per_target"][0]["nodes"]["dom"]["state"]
    # C-2 필드 null
    recs = [json.loads(json.dumps(r)) for r in fam_recs]
    recs[0]["dom_manifest_path"] = None
    root = _write_fixture(work / "three_field_null", recs)
    three["FIELD_NULL_case"] = lineage_report(load_input(root))["per_target"][0]["nodes"]["dom"]["state"]
    # C-3 값 0 (step 수 0)
    recs = [json.loads(json.dumps(r)) for r in fam_recs]
    recs[0]["steps"] = []
    root = _write_fixture(work / "three_value_zero", recs)
    three["VALUE_ZERO_case"] = lineage_report(load_input(root))["per_target"][0]["nodes"]["step"]["state"]
    # C-4 키 자체 없음
    recs = [json.loads(json.dumps(r)) for r in fam_recs]
    recs[0].pop("dom_manifest_path", None)
    root = _write_fixture(work / "three_key_missing", recs)
    three["KEY_MISSING_case"] = lineage_report(load_input(root))["per_target"][0]["nodes"]["dom"]["state"]
    # C-5 evidence_root 없음 -> FILE_ABSENT 라고 주장하면 안 된다
    recs = [json.loads(json.dumps(r)) for r in fam_recs]
    root = _write_fixture(work / "three_no_evidence_root", recs, with_files=False)
    three["EVIDENCE_ROOT_UNKNOWN_case"] = \
        lineage_report(load_input(root))["per_target"][0]["nodes"]["dom"]["state"]
    results["C_three_state_discrimination"] = three
    check("C1_states_all_distinct", len(set(three.values())) == len(three), three)
    check("C2_file_absent_labelled", three["FILE_ABSENT_case"] == "FILE_ABSENT", three)
    check("C3_null_labelled", three["FIELD_NULL_case"] == "FIELD_NULL", three)
    check("C4_zero_labelled", three["VALUE_ZERO_case"] == "VALUE_ZERO", three)
    check("C5_no_root_not_claimed_absent",
          three["EVIDENCE_ROOT_UNKNOWN_case"] == "EVIDENCE_ROOT_UNKNOWN", three)

    # ---- D. INPUT_ABSENT — 빈 결과 함정 방어 ---------------------------
    absent_cases = {}
    for label, arg in [
        ("path_not_given", None),
        ("path_missing", work / "does_not_exist_at_all"),
        ("not_a_dir", None),
        ("manifest_missing", work / "empty_dir"),
        ("zero_records", work / "zero_rec"),
    ]:
        if label == "not_a_dir":
            f = work / "a_file.txt"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x", encoding="utf-8")
            arg = f
        if label == "manifest_missing":
            (work / "empty_dir").mkdir(parents=True, exist_ok=True)
        if label == "zero_records":
            (work / "zero_rec").mkdir(parents=True, exist_ok=True)
            (work / "zero_rec" / "targets.jsonl").write_text("", encoding="utf-8")
        lda = load_input(arg)
        la = lineage_report(lda)
        da = denominator_report(lda)
        fa = failure_report(lda)
        absent_cases[label] = {
            "load_status": lda["status"],
            "lineage_computed": la["computed"],
            "lineage_status": la["status"],
            "denominator_computed": da["computed"],
            "failure_computed": fa["computed"],
            "looks_like_clean_pass": (la.get("n_with_holes") == 0 and la["computed"]),
        }
        check(f"D_{label}_flagged_absent", lda["status"].startswith("INPUT_ABSENT"), lda["status"])
        check(f"D_{label}_not_silent_pass", absent_cases[label]["looks_like_clean_pass"] is False,
              absent_cases[label])
    results["D_input_absent"] = absent_cases

    # ---- E. 분모 사슬 이탈 회계 ----------------------------------------
    recs = [_intact_record("F2", i, work) for i in range(1, FAMILY_N_FROZEN + 1)]
    recs[0]["precheck_status"] = "APP_REQUIRED_EXCLUDE"          # eligible_frozen 에서 이탈
    recs[1]["freeze_status"] = "DRAFT"                            # eligible_frozen 에서 이탈
    recs[2]["run_id"] = ""                                        # attempted 에서 이탈
    recs[3]["dom_manifest_path"] = None                           # evidence_bearing 에서 이탈
    recs[4]["task_flow_sequence"] = []                            # flow_evaluable 에서 이탈
    recs[5]["endpoint_status"] = "BLOCKED"                        # STRICT 만 이탈
    root = _write_fixture(work / "denominator_drops", recs)
    lde = load_input(root)
    de = denominator_report(lde)
    fam2s = de["variants"]["STRICT"]["families"]["F2"]
    fam2p = de["variants"]["PERMISSIVE"]["families"]["F2"]
    results["E_denominator_drops"] = {
        "STRICT_stages": fam2s["stage_denominators"],
        "PERMISSIVE_stages": fam2p["stage_denominators"],
        "STRICT_drops": {k: v["dropped_target_ids"] for k, v in fam2s["drops"].items()
                         if v["n_dropped_here"]},
        "STRICT_ratios": fam2s["ratios"],
        "silent_loss_total_STRICT": fam2s["silent_loss_total"],
    }
    exp_strict = {"candidate": 10, "eligible_frozen": 8, "attempted": 7,
                  "evidence_bearing": 6, "flow_evaluable": 4}
    check("E1_strict_stage_counts_exact", fam2s["stage_denominators"] == exp_strict,
          {"expected": exp_strict, "observed": fam2s["stage_denominators"]})
    check("E2_drop_ids_named",
          fam2s["drops"]["eligible_frozen"]["dropped_target_ids"]
          == sorted([target_key(recs[0]), target_key(recs[1])]),
          fam2s["drops"]["eligible_frozen"])
    check("E3_permissive_differs_from_strict",
          fam2p["stage_denominators"] != fam2s["stage_denominators"],
          {"strict": fam2s["stage_denominators"], "permissive": fam2p["stage_denominators"]})
    check("E4_ratio_carries_num_den_grain",
          all(set(("numerator", "denominator", "grain")).issubset(v)
              for v in fam2s["ratios"].values()), list(fam2s["ratios"]))

    # ---- E2. 02 §8 identity 중복 + family n != 10 이 드러나는가 -----------
    #   (RQ-D1 F1 중복발사 / C-BLOCKER-220418 원장 귀속 분열 계열. 조용히 합치면 안 된다.)
    dup = [_intact_record("F4", i, work) for i in range(1, FAMILY_N_FROZEN + 1)]
    dup.append(json.loads(json.dumps(dup[0])))     # F4-01 을 같은 run_id 로 한 번 더 싣는다
    root = _write_fixture(work / "duplicate_identity", dup)
    ddup = denominator_report(load_input(root))
    fam4 = ddup["variants"]["STRICT"]["families"]["F4"]
    results["E2_duplicate_identity"] = {
        "n_input_records": fam4["n_input_records"],
        "n_distinct_target_keys": fam4["n_distinct_target_keys"],
        "duplicate_target_keys": fam4["duplicate_target_keys"],
        "frame_note": fam4["frame_note"],
        "stage_denominators": fam4["stage_denominators"],
        "candidate_ratio": fam4["ratios"]["flow_evaluable_over_frozen_10"],
    }
    check("E5_duplicate_identity_surfaced",
          fam4["duplicate_identity_present"] is True
          and fam4["n_input_records"] == 11 and fam4["n_distinct_target_keys"] == 10,
          results["E2_duplicate_identity"])
    check("E6_family_n_mismatch_not_hidden", fam4["frame_note"] is not None, fam4["frame_note"])
    check("E7_fixed_denominator_stays_10",
          fam4["ratios"]["flow_evaluable_over_frozen_10"]["denominator"] == FAMILY_N_FROZEN,
          fam4["ratios"]["flow_evaluable_over_frozen_10"])
    check("E8_duplicate_inflates_candidate_visibly",
          fam4["stage_denominators"]["candidate"] == 11,
          fam4["stage_denominators"])

    # ---- F. 실패 사유 8종 + UNRESOLVED ---------------------------------
    fcases = {
        "PUBLIC_MOBILE_WEB_ABSENT": {"endpoint_status": "APP_REQUIRED"},
        "WAF_CHALLENGE": {"endpoint_status": "BLOCKED", "failure_class_signal": "WAF_CHALLENGE"},
        "TIMEOUT": {"endpoint_status": "BLOCKED", "termination_reason": "TIMEOUT"},
        "EVIDENCE_DEFECT": {"endpoint_status": "EVIDENCE_DEFECT"},
        "DISABLED_INERT": {"endpoint_status": "ABSTAIN", "failure_class_signal": "DISABLED_INERT"},
        "FORBIDDEN_ACTION": {"endpoint_status": "ABSTAIN", "forbidden_action_terminal": True},
        "AUTH_GATE": {"endpoint_status": "AUTH_GATE"},
        "GENUINE_TASK_SURFACE_ABSENCE": {"endpoint_status": "PUBLIC_WEB_UNOBSERVABLE",
                                         "failure_class_signal": "GENUINE_TASK_SURFACE_ABSENCE"},
    }
    frecs, fobs = [], {}
    for i, (expected, patch) in enumerate(fcases.items(), start=1):
        r = _intact_record("F3", i, work); r.update(patch)
        frecs.append(r)
        got = resolve_failure_class(r)
        fobs[expected] = {"observed": got["failure_class"], "basis": got["basis"],
                          "match": got["failure_class"] == expected,
                          "is_ssot_legitimate_terminal": got["is_ssot_legitimate_terminal"]}
        check(f"F_class_{expected}", got["failure_class"] == expected, fobs[expected])
    # 구분 불가 3종
    unres = {}
    for label, patch in [
        ("blocked_alone", {"endpoint_status": "BLOCKED"}),
        ("public_web_unobservable_alone", {"endpoint_status": "PUBLIC_WEB_UNOBSERVABLE"}),
        ("no_terminal_no_signal", {"endpoint_status": None}),
    ]:
        r = _intact_record("F3", 90, work); r.update(patch)
        g = resolve_failure_class(r)
        unres[label] = {"observed": g["failure_class"], "basis": g["basis"]}
        check(f"F_unresolved_{label}", g["failure_class"] == "UNRESOLVED_FAILURE_CLASS",
              unres[label])
    # 신호 충돌
    rconf = _intact_record("F3", 91, work)
    rconf.update({"endpoint_status": "AUTH_GATE", "failure_class_signal": "TIMEOUT"})
    gconf = resolve_failure_class(rconf)
    check("F_signal_conflict_unresolved",
          gconf["failure_class"] == "UNRESOLVED_FAILURE_CLASS"
          and gconf["basis"] == "SIGNAL_CONFLICT", gconf)
    results["F_failure_classes"] = {"resolved": fobs, "unresolved": unres,
                                    "signal_conflict": {"observed": gconf["failure_class"],
                                                        "basis": gconf["basis"]}}
    check("F_all_8_classes_distinct",
          len({v["observed"] for v in fobs.values()}) == 8,
          sorted({v["observed"] for v in fobs.values()}))

    # ---- G. metric redundancy 스캐폴드 — 데이터 없으면 수치 없음 --------
    sc_empty = metric_redundancy_scaffold(None)
    results["G_redundancy_scaffold"] = {
        "status_without_data": sc_empty["status"],
        "n_axis_pairs": sc_empty["n_axis_pairs"],
        "results_is_none": sc_empty["results"] is None,
    }
    check("G1_no_data_no_numbers",
          sc_empty["status"] == "NOT_COMPUTED_NO_DATA" and sc_empty["results"] is None, sc_empty["status"])
    check("G2_axis_pairs_28", sc_empty["n_axis_pairs"] == 28, sc_empty["n_axis_pairs"])
    # 함수 자체 동작 확인 (합성 벡터. 실질 해석 없음.)
    fn_self = {
        "spearman_monotone": spearman_rho([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]),
        "spearman_reverse": spearman_rho([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]),
        "spearman_zero_variance": spearman_rho([1, 1, 1, 1], [1, 2, 3, 4]),
        "mi_identical": mutual_information_discrete(list("aabbcc"), list("aabbcc")),
        "mi_independent": mutual_information_discrete(list("aabb"), list("abab")),
        "mi_with_missing": mutual_information_discrete(["a", None, "b"], ["x", "y", None]),
        "jaccard_disjoint": jaccard([1, 2], [3, 4]),
        "jaccard_identical": jaccard([1, 2], [2, 1]),
        "jaccard_empty": jaccard([], []),
    }
    results["G_function_selftest"] = fn_self
    results["G_function_selftest_note"] = ("합성 입력에 대한 함수 동작 확인일 뿐 "
                                           "construct 중복에 관한 어떤 주장도 아니다.")
    check("G3_spearman_monotone_1", abs(fn_self["spearman_monotone"]["rho"] - 1.0) < 1e-9)
    check("G4_spearman_reverse_-1", abs(fn_self["spearman_reverse"]["rho"] + 1.0) < 1e-9)
    check("G5_spearman_zero_var_none", fn_self["spearman_zero_variance"]["rho"] is None)
    check("G6_mi_identical_equals_entropy",
          abs(fn_self["mi_identical"]["mi"] - fn_self["mi_identical"]["h_x"]) < 1e-9)
    check("G7_mi_independent_zero", abs(fn_self["mi_independent"]["mi"]) < 1e-9)
    check("G8_mi_reports_dropped_missing", fn_self["mi_with_missing"]["n_dropped_missing"] == 2,
          fn_self["mi_with_missing"])
    check("G9_jaccard_disjoint_0", fn_self["jaccard_disjoint"]["jaccard"] == 0.0)
    check("G10_jaccard_identical_1", fn_self["jaccard_identical"]["jaccard"] == 1.0)
    check("G11_jaccard_empty_undefined", fn_self["jaccard_empty"]["jaccard"] is None)

    # ---- H. Manski bound — 폭만 -----------------------------------------
    b_none = manski_proportion_bound(6, 4, 0, 10)
    b_some = manski_proportion_bound(6, 1, 3, 10)
    b_all = manski_proportion_bound(0, 0, 10, 10)
    rd = manski_rd_width(6, 1, 3, 10, 2, 6, 2, 10)
    results["H_manski"] = {"no_missing": b_none, "three_missing": b_some,
                           "all_missing": b_all, "rd_between_two_families": rd}
    check("H1_width_zero_when_complete", b_none["width"] == 0.0, b_none)
    check("H2_width_grows_with_missing", b_some["width"] > b_none["width"], [b_none, b_some])
    check("H3_all_missing_full_width", b_all["width"] == 1.0, b_all)
    check("H4_no_verdict_field",
          all("verdict" not in k and "decision" not in k for k in b_some),
          list(b_some))

    # ---- I. 변이 검사 — 탐지기를 틀리게 만들면 fixture 가 잡아야 한다 ----
    mut_results = {}

    # M1: 파일 없음을 PRESENT 로
    root = work / "cut_dom"
    with mutation("M1_FILE_ABSENT_AS_PRESENT"):
        lm = lineage_report(load_input(root))
    mut_results["M1_FILE_ABSENT_AS_PRESENT"] = {
        "fixture": "cut_dom", "holes_under_mutation": lm["n_with_holes"],
        "holes_normal": 1, "caught": lm["n_with_holes"] != 1}
    check("I_M1_caught", mut_results["M1_FILE_ABSENT_AS_PRESENT"]["caught"],
          mut_results["M1_FILE_ABSENT_AS_PRESENT"])

    # M2: null 을 KEY_MISSING 으로 뭉갬
    root = work / "three_field_null"
    with mutation("M2_NULL_AS_KEY_MISSING"):
        lm = lineage_report(load_input(root))
        st_m = lm["per_target"][0]["nodes"]["dom"]["state"]
    mut_results["M2_NULL_AS_KEY_MISSING"] = {
        "state_normal": "FIELD_NULL", "state_under_mutation": st_m,
        "caught": st_m != "FIELD_NULL"}
    check("I_M2_caught", mut_results["M2_NULL_AS_KEY_MISSING"]["caught"],
          mut_results["M2_NULL_AS_KEY_MISSING"])

    # M3: INPUT_ABSENT 가드 제거
    with mutation("M3_NO_INPUT_ABSENT_GUARD"):
        lda = load_input(work / "does_not_exist_at_all")
        la = lineage_report(lda)
    mut_results["M3_NO_INPUT_ABSENT_GUARD"] = {
        "load_status_under_mutation": lda["status"],
        "lineage_computed": la["computed"],
        "n_with_holes": la.get("n_with_holes"),
        "silent_clean_pass_produced": (la["computed"] and la.get("n_with_holes") == 0),
        "caught": not lda["status"].startswith("INPUT_ABSENT")}
    check("I_M3_caught", mut_results["M3_NO_INPUT_ABSENT_GUARD"]["caught"],
          mut_results["M3_NO_INPUT_ABSENT_GUARD"])

    # M4: 분모 중첩 해제
    with mutation("M4_DENOMINATOR_NOT_NESTED"):
        dm = denominator_report(load_input(work / "denominator_drops"))
        stm = dm["variants"]["STRICT"]["families"]["F2"]["stage_denominators"]
    mut_results["M4_DENOMINATOR_NOT_NESTED"] = {
        "stages_normal": exp_strict, "stages_under_mutation": stm,
        "caught": stm != exp_strict}
    check("I_M4_caught", mut_results["M4_DENOMINATOR_NOT_NESTED"]["caught"],
          mut_results["M4_DENOMINATOR_NOT_NESTED"])

    # M5: 구분 불가를 추정으로 채움
    r = _intact_record("F3", 90, work); r["endpoint_status"] = "BLOCKED"
    with mutation("M5_GUESS_FAILURE_CLASS"):
        gm = resolve_failure_class(r)
    mut_results["M5_GUESS_FAILURE_CLASS"] = {
        "class_normal": "UNRESOLVED_FAILURE_CLASS", "class_under_mutation": gm["failure_class"],
        "basis_under_mutation": gm["basis"],
        "caught": gm["failure_class"] != "UNRESOLVED_FAILURE_CLASS"}
    check("I_M5_caught", mut_results["M5_GUESS_FAILURE_CLASS"]["caught"],
          mut_results["M5_GUESS_FAILURE_CLASS"])

    results["I_mutations"] = {"catalog": MUTATION_CATALOG, "runs": mut_results,
                              "restored_after_run": (len(_MUTATIONS) == 0)}
    check("I_mutations_restored", len(_MUTATIONS) == 0, sorted(_MUTATIONS))

    # 변이 원복 뒤 A 케이스가 다시 통과하는지 (원복 실증)
    lr2 = lineage_report(load_input(work / "intact"))
    check("I_post_mutation_intact_still_clean", lr2["n_with_holes"] == 0, lr2["hole_node_frequency"])
    results["I_post_mutation_recheck"] = {"n_with_holes": lr2["n_with_holes"]}

    results["checks"] = checks
    results["n_checks"] = len(checks)
    results["n_failed"] = sum(1 for c in checks if not c["pass"])
    results["failed_checks"] = [c for c in checks if not c["pass"]]
    return results


def run_negative_control(work: Path) -> dict:
    """
    음성 대조. 각 변이를 **전역으로** 켠 채 fixture 스위트 전체를 돌려, 검사 스위트가 실제로
    실패하는지 확인한다. 전건 통과가 '검사가 무력해서'가 아님을 보이는 절차다.
    (스위트 내부의 I_mutations_* 검사는 전역 변이 상태 때문에 함께 깨진다 — 대조의 산물이다.)
    """
    import shutil
    out: dict[str, Any] = {}
    for mut in MUTATION_CATALOG:
        w = work / f"negctl_{mut}"
        if w.exists():
            shutil.rmtree(w)
        w.mkdir(parents=True, exist_ok=True)
        _MUTATIONS.clear(); _MUTATIONS.add(mut)
        try:
            r = run_fixtures(w)
            out[mut] = {"outcome": "CHECKS_FAILED" if r["n_failed"] else "SUITE_STILL_PASSED",
                        "n_failed": r["n_failed"], "n_checks": r["n_checks"],
                        "failed_checks": [c["check"] for c in r["failed_checks"]],
                        "suite_detected_the_break": r["n_failed"] > 0}
        except Exception as e:                                    # noqa: BLE001
            out[mut] = {"outcome": "SUITE_RAISED",
                        "exception": f"{type(e).__name__}: {e}",
                        "suite_detected_the_break": True,
                        "note": "예외로 중단되는 것도 '조용한 통과'가 아니므로 탐지로 본다."}
        finally:
            _MUTATIONS.clear()
    return {
        "purpose": "전건 통과가 검사 무력화 때문이 아님을 보이는 음성 대조",
        "per_mutation": out,
        "all_mutations_detected": all(v["suite_detected_the_break"] for v in out.values()),
        "mutations_restored_after": len(_MUTATIONS) == 0,
    }


# =====================================================================
# 8. 모호 정의 등록 — 채우지 않고 올린다
# =====================================================================

AMBIGUOUS_DEFINITIONS = [
    {
        "id": "AD-01",
        "where": "Director P1 C 8종  vs  04_FLOW_CODEBOOK §4 endpoint_status (7값)",
        "issue": "Director 가 요구한 8종 중 TIMEOUT / DISABLED_INERT / FORBIDDEN_ACTION / "
                 "GENUINE_TASK_SURFACE_ABSENCE 는 대응하는 SSOT endpoint_status 값이 없다. "
                 "BLOCKED 하나가 WAF·challenge 와 timeout 을 함께 삼키고, "
                 "PUBLIC_WEB_UNOBSERVABLE 하나가 'public mobile web 부재' 와 "
                 "'genuine task surface absence' 를 함께 삼킨다.",
        "harness_behaviour": "명시 signal 이 없으면 UNRESOLVED_FAILURE_CLASS. 추정하지 않는다.",
        "needed_from": "A (codebook 값 추가 또는 수집기 필수 signal 필드 지정)",
    },
    {
        "id": "AD-02",
        "where": "05_ANALYSIS_PLAN §6 'evidence-bearing n'",
        "issue": "03 §10 이 evidence package 구성요소를 열거하지만, target 하나가 "
                 "evidence-bearing 이려면 구성요소 '전부'가 필요한지 '하나라도'면 되는지 "
                 "SSOT 가 정하지 않는다.",
        "harness_behaviour": "STRICT/PERMISSIVE 두 분모를 나란히 낸다. 고르지 않는다.",
        "needed_from": "A",
    },
    {
        "id": "AD-03",
        "where": "05_ANALYSIS_PLAN §6 'flow-evaluable n'",
        "issue": "task_flow_sequence 만 있으면 되는지, endpoint_status 가 REACHED/AUTH_GATE 여야 "
                 "하는지 정의가 없다. ABSTAIN·BLOCKED 로 끝난 관측이 sequence 분석 분모에 "
                 "들어가는지가 05 §2-E 의 unique signature·Levenshtein 분모를 바꾼다.",
        "harness_behaviour": "STRICT/PERMISSIVE 두 분모를 나란히 낸다.",
        "needed_from": "A",
    },
    {
        "id": "AD-04",
        "where": "Director P1 C 목록에 AUTH_GATE 가 실패사유로 포함  vs  01 §1 포함조건",
        "issue": "01 §1 은 'legitimate AUTH_GATE로 종료 가능'을 frame 포함조건으로 둔다. "
                 "AUTH_GATE 를 실패사유로 세면 정당 종료가 손실로 계상돼 분모가 바뀐다.",
        "harness_behaviour": "class 는 그대로 내되 is_ssot_legitimate_terminal=true 플래그를 "
                             "함께 낸다. 어느 쪽으로도 합산하지 않는다.",
        "needed_from": "A",
    },
    {
        "id": "AD-05",
        "where": "Director P1 B 사슬의 'ledger' 노드",
        "issue": "ledger(원장) 레코드의 스키마가 SSOTV3 에 정의돼 있지 않다. 02 §8 은 "
                 "observation identity 만 규정한다. 무엇이 있어야 ledger 노드가 PRESENT 인지 "
                 "확정 기준이 없다.",
        "harness_behaviour": "비어있지 않은 record 이면 PRESENT. 내용 검증은 하지 않는다.",
        "needed_from": "A 또는 C (C-BLOCKER-220418 원장 귀속 계열)",
    },
    {
        "id": "AD-06",
        "where": "Director P1 B 'L0' 노드  vs  03 §3 S0..Sn",
        "issue": "L0 는 03 §3 의 S0 최초 안정화 capture 를 뜻하는 것으로 보이나 표기가 다르다. "
                 "S1..Sn scroll state 의 결손을 L0 노드가 대표하는지 여부가 불명확하다.",
        "harness_behaviour": "L0 를 단일 manifest 포인터로만 본다. scroll state 결손은 보지 않는다.",
        "needed_from": "A",
    },
    {
        "id": "AD-07",
        "where": "05 §6 'attempted 10'  vs  03 §5 REPLAY_BROKEN",
        "issue": "replay 가 깨져 REPLAY_BROKEN 인 run 이 attempted 에 계상되는지, "
                 "재수집 run 이 attempted 를 2 로 만드는지(02 §8 은 재수집을 새 run 으로 둔다) "
                 "정의가 없다. attempted 를 run 수로 세면 target 수와 grain 이 갈린다.",
        "harness_behaviour": "target grain 으로만 센다(run_id 존재 여부). run grain 은 내지 않는다.",
        "needed_from": "A / C (ruling_11 단위·모집단·원천 3축 명시 요구와 같은 계열)",
    },
    {
        "id": "AD-08",
        "where": "'metric redundancy' 의 대상 단위",
        "issue": "05 §3 은 8축을 profile 로 분리 보고하라고만 한다. 두 축이 '같은 construct 를 "
                 "중복 측정한다'의 조작적 정의가 SSOT 에 없다. 관측단위(target 8축 vector) 와 "
                 "축쌍 28 을 혼동하면 45-pair 오류와 같은 계열의 오류가 난다.",
        "harness_behaviour": "상관·상호정보·Jaccard 값만 내는 함수를 두고, 판정선을 만들지 않는다. "
                             "데이터가 없으므로 수치도 내지 않는다.",
        "needed_from": "A (D 는 조작화를 발명하지 않는다)",
    },
]

NOT_IMPLEMENTED = [
    "8축 중복 수치 산출 — MAIN50 실측 없음. NOT_COMPUTED_NO_DATA 로만 반환한다.",
    "중복 판정선 / threshold / cut-off / composite score — 금지 범위.",
    "실패 사유를 evidence 로부터 추론하는 규칙 — 새 조작화 금지. 명시 signal 과 "
    "SSOT 일의적 파생만 쓴다.",
    "REAL 접속·수집·replay — 금지.",
    "gold label / task gold / holdout 접근 — 금지.",
    "GO/NO-GO, 재수집 권고, target replacement 제안 — A 권한.",
    "45 pair 를 관측단위로 쓰는 어떤 집계도 넣지 않았다.",
    "ledger 레코드 내용 검증 (AD-05 미정의).",
    "S1..Sn scroll state 결손 탐지 (AD-06 미정의).",
    "run grain 분모 (AD-07 미정의; target grain 만).",
    "MLflow 기록 — STANDBY 범위 밖(D queue 2026-08-28 02:28 보류 결정).",
]

LIMITATIONS = [
    "MAIN50 실측이 없다. 여기의 모든 수치는 합성 fixture 에 대한 것이며 어떤 서비스에 관한 "
    "사실도 아니다.",
    "이 하네스는 입력이 SSOT v3 필드명을 따른다고 가정한다. B 의 실제 mart 필드명이 다르면 "
    "전부 KEY_MISSING 으로 떨어진다 — 그것이 조용한 통과보다 낫지만, 첫 실행 시 "
    "필드명 매핑 대조가 반드시 선행돼야 한다.",
    "evidence_root 가 주어지지 않으면 포인터 노드는 FILE_ABSENT 가 아니라 "
    "EVIDENCE_ROOT_UNKNOWN 이다. 이 둘을 같게 읽으면 결손을 과대계상한다.",
    "Manski bound 는 폭만 낸다. RQ-D7 의 수치는 재사용하지 않았고 방법만 가져왔다.",
    "실패 사유 8종 중 4종은 SSOT 대응 필드가 없어(AD-01) 실입력에서 대량 "
    "UNRESOLVED_FAILURE_CLASS 가 날 수 있다. 이것은 하네스의 결함이 아니라 "
    "수집 스키마의 미정의를 드러낸 것이다.",
    "변이 검사는 5개 변이만 덮는다. 탐지기의 다른 오류 양식은 덮지 못한다.",
]


# =====================================================================
# 9. main
# =====================================================================

def sha256_file(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None,
                    help="실입력 루트 (targets.jsonl 포함). 없으면 INPUT_ABSENT 로 기록된다.")
    ap.add_argument("--workdir", default=None, help="fixture 작업 디렉터리 (기본: 스크래치)")
    args = ap.parse_args(argv)

    work = Path(args.workdir) if args.workdir else (
        Path(os.environ.get("TMPDIR", "/tmp")) / "lane_p_fixtures")
    if work.exists():
        import shutil
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    fixtures = run_fixtures(work)
    fixtures["J_negative_control"] = run_negative_control(work / "_negctl")

    real = load_input(args.input)
    real_block = {
        "input_root": args.input,
        "load_status": real["status"],
        "n_records": real["n_records"],
        "lineage": (lineage_report(real) if not is_input_absent(real)
                    else {"status": real["status"], "computed": False}),
        "denominator": (denominator_report(real) if not is_input_absent(real)
                        else {"status": real["status"], "computed": False}),
        "failure_classes": (failure_report(real) if not is_input_absent(real)
                            else {"status": real["status"], "computed": False}),
        "metric_redundancy": metric_redundancy_scaffold(None),
    }

    n_failed = fixtures["n_failed"]
    if n_failed > 0:
        verdict = "NOT_READY"
    elif AMBIGUOUS_DEFINITIONS:
        verdict = "READY_WITH_AMBIGUITY"
    else:
        verdict = "READY"

    manifest_path = SSOTV3 / "MANIFEST_v3.0.json"
    payload = {
        "verdict": verdict,
        "verdict_basis": {
            "fixture_checks_total": fixtures["n_checks"],
            "fixture_checks_failed": n_failed,
            "n_ambiguous_definitions": len(AMBIGUOUS_DEFINITIONS),
            "rule": "fixture 1건이라도 실패하면 NOT_READY. 전부 통과해도 AMBIGUOUS_DEFINITION 이 "
                    "남아 있으면 READY_WITH_AMBIGUITY. 이것은 GO/NO-GO 가 아니라 하네스 자체의 "
                    "준비 상태 표시다.",
        },
        "lane": "P",
        "scope": "Provenance / Denominator chain / Metric redundancy",
        "generated_at_kst": datetime.now(KST).isoformat(),
        "base_sha": BASE_SHA,
        "ssot_manifest_sha_declared": SSOT_MANIFEST_SHA,
        "ssot_manifest_sha_observed": sha256_file(manifest_path),
        "ssot_manifest_sha_match": sha256_file(manifest_path) == SSOT_MANIFEST_SHA,
        "grain": GRAIN_PRIMARY,
        "family_n": FAMILY_N_FROZEN,
        "n45_policy": "family 내 45 pair 는 distance matrix cell 이지 독립표본 n=45 가 아니다 "
                      "(05 §1). 이 하네스는 어디서도 45 를 분모로 쓰지 않는다.",

        "definitions_verbatim": {
            "denominator_chain_05_6": DENOMINATOR_CHAIN_VERBATIM,
            "denominator_chain_05_6_source": "SSOTV3/05_ANALYSIS_PLAN_v3.0.md §6 "
                                             "'각 family에서: candidate 10 → eligible/frozen 10 "
                                             "→ attempted 10 → evidence-bearing n → "
                                             "flow-evaluable n / 모든 분모를 단계별로 보고. "
                                             "replacement는 freeze 전에만.'",
            "analysis_unit_05_1": "Primary: service × frozen task. family n=10. 동일 family의 "
                                  "45 pair는 distance matrix의 cell이지 독립 표본 n=45가 아니다.",
            "lineage_chain_director_p1_b": LINEAGE_CHAIN_VERBATIM,
            "lineage_chain_source": "Lane P worker directive (Director P1 B 항). "
                                    "PROVENANCE_NOTE: Director 원문 packet 은 이 워크트리에 "
                                    "파일로 존재하지 않는다 — 워커 지시문에 실린 문안을 그대로 "
                                    "구현했고, 원문 대조는 D/A 가 해야 한다.",
            "failure_classes_director_p1_c": [
                "public mobile web 부재", "WAF·challenge", "timeout", "evidence defect",
                "disabled·inert", "forbidden action", "auth gate",
                "genuine task surface absence"],
            "failure_classes_source": "Lane P worker directive (Director P1 C 항). "
                                      "동일 PROVENANCE_NOTE.",
            "stfp_axes_05_3": STFP_AXES,
            "stfp_axes_source": "SSOTV3/05_ANALYSIS_PLAN_v3.0.md §3 'Spatial / Label / Control / "
                                "Reveal / Sequence / Depth / Auth / Obstruction. "
                                "가중합 단일 score 생성 금지.'",
            "evidence_package_03_10": "각 state/step: DOM / AX / screenshot / probe·CSS geometry / "
                                      "URL / selected control facts / manifest SHA",
            "identity_02_8": "service_id + task_id + run_id 로 observation identity 구성. "
                             "display name을 file id로 사용 금지.",
            "endpoint_status_04_4": ["REACHED", "AUTH_GATE", "PUBLIC_WEB_UNOBSERVABLE",
                                     "APP_REQUIRED", "EVIDENCE_DEFECT", "BLOCKED", "ABSTAIN"],
            "precheck_03_2": ["ELIGIBLE_PUBLIC_MOBILE_WEB", "APP_REQUIRED_EXCLUDE",
                              "ACCESS_BLOCKED_REVIEW", "URL_REMAP_REQUIRED"],
        },

        "implemented_components": {
            "1_denominator_chain": {
                "status": "IMPLEMENTED",
                "entrypoints": ["denominator_chain()", "denominator_report()", "ratio()"],
                "stages": ["candidate", "eligible_frozen", "attempted",
                           "evidence_bearing", "flow_evaluable"],
                "nesting_enforced": True,
                "reports": "family 별 단계 분모 + 단계별 이탈 target id 목록 + "
                           "분자/분모/grain 을 붙인 비율 + silent_loss 합계 + "
                           "02 §8 identity 중복(duplicate_target_keys) + family n 불일치 표시",
                "variants": ["STRICT", "PERMISSIVE"],
                "variant_not_selected_reason": "AD-02 / AD-03",
            },
            "2_lineage_hole_detector": {
                "status": "IMPLEMENTED",
                "entrypoints": ["detect_lineage_holes()", "lineage_report()"],
                "nodes": [n for n, _, _ in LINEAGE_NODES],
                "node_states": NODE_STATES,
                "conflation_policy": "파일 없음(FILE_ABSENT) / 필드 null(FIELD_NULL) / "
                                     "값 0(VALUE_ZERO) / 키 부재(KEY_MISSING) / "
                                     "확인불가(EVIDENCE_ROOT_UNKNOWN) 를 서로 다른 상태로 낸다.",
                "downstream_masking": "없음 — 상류가 끊겨도 하류 노드를 독립 평가해 전부 보고한다.",
            },
            "3_failure_class_decomposer": {
                "status": "IMPLEMENTED_WITH_AMBIGUITY",
                "entrypoints": ["resolve_failure_class()", "failure_report()"],
                "classes": list(FAILURE_CLASSES),
                "basis_values": ["EXPLICIT_SIGNAL", "SSOT_DERIVED", "SIGNAL_CONFLICT",
                                 "NO_DISTINGUISHING_INPUT"],
                "inference_policy": "명시 signal 또는 SSOT 일의적 파생만. 그 외 추정 없음.",
                "ssot_coverage": "8종 중 SSOT endpoint_status 로 일의적 파생 가능한 것은 3종 "
                                 "(AUTH_GATE / EVIDENCE_DEFECT / APP_REQUIRED→"
                                 "PUBLIC_MOBILE_WEB_ABSENT). 나머지 5종은 명시 signal 필요. AD-01.",
            },
            "4_metric_redundancy_scaffold": {
                "status": "SCAFFOLD_ONLY_NO_NUMBERS",
                "entrypoints": ["metric_redundancy_scaffold()", "spearman_rho()",
                                "mutual_information_discrete()", "jaccard()", "axis_pair_grid()"],
                "axes": STFP_AXES,
                "n_axis_pairs": 28,
                "threshold_policy": "NO_THRESHOLD. 중복 판정 없음.",
                "why_no_numbers": "MAIN50 실측 없음 → NOT_COMPUTED_NO_DATA.",
            },
            "5_manski_worst_case_bound": {
                "status": "IMPLEMENTED",
                "entrypoints": ["manski_proportion_bound()", "manski_rd_width()"],
                "outputs": "lower / upper / width / sign_constant_over_bound",
                "policy": "폭만. 식별 판정·threshold·재수집 권고 없음.",
                "method_source": "tools/rq_d7_denominator_bounds.py (방법만; 수치 재사용 없음)",
            },
            "6_input_absent_guard": {
                "status": "IMPLEMENTED",
                "entrypoints": ["load_input()", "is_input_absent()"],
                "absent_states": ["INPUT_ABSENT_PATH_NOT_GIVEN", "INPUT_ABSENT_PATH_MISSING",
                                  "INPUT_ABSENT_NOT_A_DIR", "INPUT_ABSENT_MANIFEST_MISSING",
                                  "INPUT_ABSENT_ZERO_RECORDS"],
                "guarantee": "부재 상태에서 lineage/denominator/failure 리포트는 computed=false 를 "
                             "내며 '결손 0 / 정상' 으로 보이지 않는다.",
            },
        },

        "input_contract": INPUT_CONTRACT,
        "fixture_results": fixtures,
        "failure_class_taxonomy": {
            "classes": FAILURE_CLASSES,
            "ssot_derivation_table": {k: {"maps_to": v[0], "cites": v[1]}
                                      for k, v in _TERMINAL_DERIVATION.items()},
            "ssot_ambiguous_terminals": _TERMINAL_AMBIGUOUS,
            "legitimate_terminals": sorted(SSOT_LEGITIMATE_TERMINALS),
            "no_collapse_policy": "8종을 하나로 묶지 않는다. 구분 불가 시 UNRESOLVED_FAILURE_CLASS.",
        },
        "ambiguous_definitions": AMBIGUOUS_DEFINITIONS,
        "real_input_run": real_block,
        "limitation": LIMITATIONS,
        "not_implemented": NOT_IMPLEMENTED,
        "constraints_observed": {
            "real_target_accessed": False,
            "production_or_mart_modified": False,
            "raw_evidence_modified": False,
            "git_executed": False,
            "other_lane_files_accessed": False,
            "gold_or_holdout_accessed": False,
            "go_no_go_issued": False,
            "threshold_or_composite_created": False,
            "n45_used_as_sample_size": False,
        },
        "files_written": [str(OUT_JSON), str(OUT_MD),
                          str(RD / "tools/v3_harness/lane_p_provenance_denominator.py")],
        "routing": "to=C, cc=A (06 §4 — D 는 A 로 canonical conclusion 을 직접 우회 전달하지 않는다)",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_findings(payload), encoding="utf-8")
    print(json.dumps({"verdict": verdict,
                      "checks": fixtures["n_checks"],
                      "failed": n_failed,
                      "failed_names": [c["check"] for c in fixtures["failed_checks"]],
                      "ambiguities": len(AMBIGUOUS_DEFINITIONS),
                      "real_input_status": real["status"],
                      "out": str(OUT_JSON)}, ensure_ascii=False, indent=2))
    return 0 if n_failed == 0 else 1


def render_findings(p: dict) -> str:
    f = p["fixture_results"]
    L: list[str] = []
    A = L.append
    A("# LANE_P_FINDINGS — Provenance / 분모 사슬 / Metric redundancy 하네스")
    A("")
    A(f"**verdict**: `{p['verdict']}`  ")
    A(f"**base SHA**: `{p['base_sha']}`  ")
    A(f"**SSOTV3 MANIFEST sha256 대조**: declared `{p['ssot_manifest_sha_declared'][:16]}…` / "
      f"observed `{str(p['ssot_manifest_sha_observed'])[:16]}…` → "
      f"**{'MATCH' if p['ssot_manifest_sha_match'] else 'MISMATCH'}**  ")
    A(f"**생성**: {p['generated_at_kst']} (KST)  ")
    A(f"**routing**: {p['routing']}")
    A("")
    A("MAIN50 실측 데이터는 없다. 이 문서의 모든 수치는 **합성 fixture** 에 대한 것이며 "
      "어떤 서비스에 관한 사실도 아니다.")
    A("")
    A("---")
    A("")
    A("## 0. 무엇을 만들었나")
    A("")
    A("| # | 컴포넌트 | 상태 |")
    A("|---|---|---|")
    for k, v in p["implemented_components"].items():
        A(f"| {k.split('_')[0]} | {k.split('_', 1)[1].replace('_', ' ')} | `{v['status']}` |")
    A("")
    A("## 1. 정의는 원문 그대로 옮겼다")
    A("")
    A("```")
    A("05 §6  " + p["definitions_verbatim"]["denominator_chain_05_6"])
    A("P1 B   " + p["definitions_verbatim"]["lineage_chain_director_p1_b"])
    A("```")
    A("")
    A("> **PROVENANCE 경고.** 05 §6 · 02 · 03 · 04 는 `SSOTV3/` 파일 원문에서 직접 인용했고 "
      "MANIFEST sha256 이 일치한다. 반면 **Director P1 B/C 원문 packet 은 이 워크트리에 "
      "파일로 존재하지 않는다** — 워커 지시문에 실린 문안을 그대로 구현했다. "
      "원문 대조는 D/A 가 해야 한다. 이것이 이 하네스에서 가장 약한 provenance 고리다.")
    A("")
    A("## 2. 분모 사슬 (05 §6)")
    A("")
    A(f"grain = `{p['grain']}`. family 분모 = **{p['family_n']}** 고정. "
      f"{p['n45_policy']}")
    A("")
    A("모든 비율에 분자·분모·grain 을 붙였다. 단계 중첩을 강제하고, **각 단계에서 빠진 "
      "target id 를 이름으로 낸다** — 수만 세지 않는다.")
    A("")
    e = f["E_denominator_drops"]
    A("합성 F2(10건) 이탈 회계:")
    A("")
    A("| 단계 | STRICT | PERMISSIVE |")
    A("|---|---|---|")
    for k in ("candidate", "eligible_frozen", "attempted", "evidence_bearing", "flow_evaluable"):
        A(f"| {k} | {e['STRICT_stages'][k]} | {e['PERMISSIVE_stages'][k]} |")
    A("")
    A("이탈 target id (STRICT):")
    A("")
    for k, v in e["STRICT_drops"].items():
        A(f"- `{k}` — {v}")
    A("")
    A("**STRICT 와 PERMISSIVE 가 다른 값을 낸다.** 어느 쪽이 05 §6 의 의도인지 SSOT 가 정하지 "
      "않았으므로(AD-02/AD-03) 이 하네스는 **고르지 않고 둘 다 낸다.**")
    A("")
    d2 = f["E2_duplicate_identity"]
    A("### 2.1 identity 중복과 family n 불일치는 합치지 않는다")
    A("")
    A(f"F4 에 `service_id+task_id+run_id` 가 같은 레코드를 하나 더 실은 fixture: "
      f"입력 {d2['n_input_records']}건 / 구분되는 target key {d2['n_distinct_target_keys']}개 → "
      f"`duplicate_target_keys` 로 드러난다. candidate 분모는 "
      f"{d2['stage_denominators']['candidate']} 로 **부풀어 보인다** — 조용히 dedupe 하지 않고 "
      f"부푼 사실 자체를 낸다. 05 §4 고정 분모 비율은 분모 "
      f"{d2['candidate_ratio']['denominator']} 를 유지하므로 값이 1 을 넘어 이상이 드러난다 "
      f"(관측 {d2['candidate_ratio']['value']}).")
    A("")
    A(f"family n 불일치도 숨기지 않는다: `{d2['frame_note']}`")
    A("")
    A("## 3. lineage hole 탐지 (P1 B)")
    A("")
    A("9노드. **파일 없음 / 필드 null / 값 0 / 키 부재 / 확인불가를 서로 다른 상태로 낸다.**")
    A("")
    A("| fixture | 관측 상태 |")
    A("|---|---|")
    for k, v in f["C_three_state_discrimination"].items():
        A(f"| {k} | `{v}` |")
    A("")
    A("양방향 대조 — 온전한 사슬은 hole 0, 9노드를 하나씩 끊으면 **정확히 그 노드만** 잡혔다:")
    A("")
    A("| 끊은 노드 | 관측된 hole | 상태 | 일치 |")
    A("|---|---|---|---|")
    for node, v in f["B_single_node_cuts"].items():
        A(f"| {node} | {v['observed_hole_nodes']} | `{v['observed_state']}` | "
          f"{'O' if v['exact_match'] else 'X'} |")
    A("")
    A("상류가 끊겨도 하류 노드를 마스킹하지 않는다 — 각 노드를 독립 평가한다.")
    A("")
    A("## 4. 실패 사유 분해 (P1 C 8종)")
    A("")
    A("**8종을 하나로 묶지 않는다. 추정으로 채우지 않는다.**")
    A("")
    A("| Director 8종 | 확정 근거 | fixture 일치 |")
    A("|---|---|---|")
    for k, v in f["F_failure_classes"]["resolved"].items():
        A(f"| {k} | `{v['basis']}` | {'O' if v['match'] else 'X'} |")
    A("")
    A("구분 불가 케이스는 채우지 않았다:")
    A("")
    A("| 입력 | 결과 |")
    A("|---|---|")
    for k, v in f["F_failure_classes"]["unresolved"].items():
        A(f"| {k} | `{v['observed']}` ({v['basis']}) |")
    sc = f["F_failure_classes"]["signal_conflict"]
    A(f"| 명시 signal 과 SSOT 파생 충돌 | `{sc['observed']}` ({sc['basis']}) |")
    A("")
    A("> **가장 중요한 발견.** Director 가 요구한 8종 중 **SSOT `endpoint_status`(7값)로 "
      "일의적으로 갈 수 있는 것은 3종뿐이다.** `BLOCKED` 하나가 WAF·challenge 와 timeout 을 "
      "함께 삼키고, `PUBLIC_WEB_UNOBSERVABLE` 하나가 public mobile web 부재와 genuine task "
      "surface absence 를 함께 삼킨다. disabled·inert 와 forbidden action 은 대응 값 자체가 없다. "
      "**수집기가 명시 signal 을 남기지 않으면 MAIN50 에서 8종 분해는 원리적으로 불가능하다.** "
      "이것은 지금 고쳐야 하는 수집 스키마 문제지, 데이터가 온 뒤 분석으로 메울 수 있는 것이 "
      "아니다. → AD-01, to=C cc=A.")
    A("")
    A("## 5. metric redundancy 스캐폴드 (05 §3)")
    A("")
    A(f"8축 · 축쌍 {p['implemented_components']['4_metric_redundancy_scaffold']['n_axis_pairs']}개. "
      "상관(Spearman) · 상호정보(MI/NMI/불확실성계수) · Jaccard 함수를 구현했다.")
    A("")
    A(f"**수치는 내지 않았다** — `{f['G_redundancy_scaffold']['status_without_data']}`. "
      "MAIN50 실측이 없으므로 8축 vector 가 존재하지 않는다.")
    A("")
    A("**판정선을 만들지 않았다.** 이 스캐폴드에는 threshold 도 composite score 도 없고 "
      "'중복이다/아니다' 를 반환하는 경로가 없다. 함수 자체의 동작만 합성 벡터로 확인했다"
      "(monotone→1, reverse→-1, 무분산→None, 동일변수 MI=엔트로피, 독립변수 MI=0, "
      "Jaccard 0/1/undefined).")
    A("")
    A("## 6. Manski worst-case bound")
    A("")
    h = f["H_manski"]
    A("| 케이스 | lower | upper | width |")
    A("|---|---|---|---|")
    for k in ("no_missing", "three_missing", "all_missing"):
        A(f"| {k} | {h[k]['lower']} | {h[k]['upper']} | **{h[k]['width']}** |")
    A("")
    A(f"두 family RD bound 폭 = {h['rd_between_two_families']['rd_width']}, "
      f"부호 불변 = {h['rd_between_two_families']['sign_constant_over_bound']}.")
    A("")
    A("**폭만 낸다.** 식별/비식별 판정, threshold, 재수집 권고를 반환하지 않는다. "
      "RQ-D7 에서 방법만 가져왔고 수치는 재사용하지 않았다.")
    A("")
    A("## 7. 빈 결과 함정 방어 — INPUT_ABSENT")
    A("")
    A("이 프로젝트에서 '존재하지 않는 경로에 grep 을 걸고 0건을 정상으로 읽은' 실패가 여러 번 "
      "났다. 그래서 부재를 **5개 상태로 갈라** 명시 반환하고, fixture 로 실증했다.")
    A("")
    A("| 케이스 | load_status | computed | 정상처럼 보였나 |")
    A("|---|---|---|---|")
    for k, v in f["D_input_absent"].items():
        A(f"| {k} | `{v['load_status']}` | {v['lineage_computed']} | "
          f"**{'YES(결함)' if v['looks_like_clean_pass'] else 'NO'}** |")
    A("")
    A("## 8. 변이 검사 — 탐지기를 일부러 틀리게 만들었을 때")
    A("")
    A("| 변이 | 정상 | 변이 하 | 잡았나 |")
    A("|---|---|---|---|")
    m = f["I_mutations"]["runs"]
    A(f"| M1 파일없음→PRESENT | holes=1 | holes={m['M1_FILE_ABSENT_AS_PRESENT']['holes_under_mutation']} | "
      f"{'O' if m['M1_FILE_ABSENT_AS_PRESENT']['caught'] else 'X'} |")
    A(f"| M2 null→KEY_MISSING | `FIELD_NULL` | `{m['M2_NULL_AS_KEY_MISSING']['state_under_mutation']}` | "
      f"{'O' if m['M2_NULL_AS_KEY_MISSING']['caught'] else 'X'} |")
    A(f"| M3 INPUT_ABSENT 가드 제거 | `INPUT_ABSENT_PATH_MISSING` | "
      f"`{m['M3_NO_INPUT_ABSENT_GUARD']['load_status_under_mutation']}` "
      f"(조용한 통과 생성={m['M3_NO_INPUT_ABSENT_GUARD']['silent_clean_pass_produced']}) | "
      f"{'O' if m['M3_NO_INPUT_ABSENT_GUARD']['caught'] else 'X'} |")
    A(f"| M4 분모 중첩 해제 | {m['M4_DENOMINATOR_NOT_NESTED']['stages_normal']} | "
      f"{m['M4_DENOMINATOR_NOT_NESTED']['stages_under_mutation']} | "
      f"{'O' if m['M4_DENOMINATOR_NOT_NESTED']['caught'] else 'X'} |")
    A(f"| M5 실패사유 추정 채움 | `UNRESOLVED_FAILURE_CLASS` | "
      f"`{m['M5_GUESS_FAILURE_CLASS']['class_under_mutation']}` | "
      f"{'O' if m['M5_GUESS_FAILURE_CLASS']['caught'] else 'X'} |")
    A("")
    A(f"변이 원복 확인: `_MUTATIONS` 비었음 = {f['I_mutations']['restored_after_run']}, "
      f"원복 후 intact fixture hole 수 = {f['I_post_mutation_recheck']['n_with_holes']}.")
    A("")
    nc = f.get("J_negative_control")
    if nc:
        A("### 8.1 음성 대조 — 검사 스위트가 무력하지 않다")
        A("")
        A("전건 통과가 '검사가 아무것도 안 잡기 때문' 이 아님을 보이려고, 각 변이를 **전역으로** "
          "켠 채 스위트 전체를 다시 돌렸다.")
        A("")
        A("| 변이 | 결과 | 실패 검사 수 |")
        A("|---|---|---|")
        for k, v in nc["per_mutation"].items():
            n = v.get("n_failed", v.get("exception", "-"))
            A(f"| {k} | `{v['outcome']}` | {n} |")
        A("")
        A(f"모든 변이가 탐지됨 = **{nc['all_mutations_detected']}**, "
          f"원복 = {nc['mutations_restored_after']}.")
        A("")
    A(f"## 9. fixture 총계 — {f['n_checks']}건 중 실패 {f['n_failed']}건")
    A("")
    if f["n_failed"]:
        for c in f["failed_checks"]:
            A(f"- **FAIL** `{c['check']}` — {c['detail']}")
    else:
        A("전건 통과.")
    A("")
    A("## 10. AMBIGUOUS_DEFINITION — 채우지 않고 올린다")
    A("")
    for a in p["ambiguous_definitions"]:
        A(f"### {a['id']} — {a['where']}")
        A("")
        A(f"{a['issue']}")
        A("")
        A(f"- 하네스 동작: {a['harness_behaviour']}")
        A(f"- 필요한 판단 주체: **{a['needed_from']}**")
        A("")
    A("## 11. 하지 않은 것")
    A("")
    for n in p["not_implemented"]:
        A(f"- {n}")
    A("")
    A("## 12. 한계")
    A("")
    for n in p["limitation"]:
        A(f"- {n}")
    A("")
    A("---")
    A("")
    A("이 하네스는 GO/NO-GO 를 내지 않는다. `verdict` 는 **하네스 자체의 준비 상태** 표시이며 "
      "연구 판정이 아니다. 실입력 실행 전에 B 의 실제 mart 필드명과 이 하네스의 입력 계약을 "
      "먼저 대조해야 한다 — 필드명이 다르면 전부 `KEY_MISSING` 으로 떨어진다.")
    A("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
