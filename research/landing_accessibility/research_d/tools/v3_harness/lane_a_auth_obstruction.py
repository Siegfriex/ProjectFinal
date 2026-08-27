#!/usr/bin/env python3
"""
Lane A — Auth timing / Obstruction 분석 하네스 + 반례 탐지기 (Claude D / V3 sandbox)

책임 범위
  - auth_gate_stage 분류기 (NONE / BEFORE_TASK_DISCOVERY / AFTER_TASK_SELECT / AT_ENDPOINT)
  - fact_task_obstruction 해석기 (dismissal 3분 구분 + primary=task_control_occlusion)
  - 결측 표현 불일치(0.0 vs None) 탐지기
  - 반례 탐지기 2종
  - 합성 fixture 양방향 대조 + 변이(mutation) 검사

명시적 비범위
  - task_flow_sequence / experienced_flow_sequence 길이 계산 (Lane F 소관)
  - REAL 접속, DOM/AX 수집, geometry 로부터 occlusion 재도출
  - threshold / cut-off / composite score
  - gold label, GO/NO-GO

안전
  - 순수 함수 모듈. 네트워크/브라우저/파일-쓰기(결과 디렉터리 제외) 없음.
  - credential 입력·login submit·CAPTCHA·거래 activation 경로를 구성하지 않는다.
  - 자기 소스에 대한 금지 API 정적 self-check 를 포함한다 (safety_selfcheck()).

SSOT: /home/sieg/projects-wsl/ProjectFinal/SSOTV3
      MANIFEST_v3.0.json self-sha256 = 1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a
Base SHA: 7448184a811f5d7d8772f21488bb75418fde3313 (claude-d/research-sandbox-v21)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

# =============================================================================
# 0. Codebook verbatim (인용. 이 하네스는 아래 문장 밖의 조작화를 새로 만들지 않는다)
# =============================================================================

CODEBOOK_VERBATIM: dict[str, dict[str, str]] = {
    "auth_gate_stage": {
        "source": "SSOTV3/04_FLOW_CODEBOOK_v3.0.md §4 Measurement Variables",
        "text": "| auth_gate_stage | Flow | categorical | NONE/BEFORE_TASK_DISCOVERY/AFTER_TASK_SELECT/AT_ENDPOINT |",
    },
    "AUTH_GATE_token": {
        "source": "SSOTV3/04_FLOW_CODEBOOK_v3.0.md §2 Canonical tokens",
        "text": "| AUTH_GATE | 사전지정 task 경로에서 인증이 불가피해지는 상태에 도달한다 |",
    },
    "DISMISS_OBSTRUCTION_token": {
        "source": "SSOTV3/04_FLOW_CODEBOOK_v3.0.md §2 Canonical tokens",
        "text": "| DISMISS_OBSTRUCTION | task path 진행에 필수인 방해요소를 허용된 닫기 control로 제거한다 |",
    },
    "auth_contract": {
        "source": "SSOTV3/00_SSOT_v3.0_CROSS_SERVICE_FLOW.md §6 Auth / Credential / Transaction 계약",
        "text": (
            "- landing에 generic login이 **존재**한다는 이유로 중단하지 않는다.\n"
            "- 사전지정 task path를 따라가다가 인증이 불가피해지는 최초 상태에서 `AUTH_GATE` terminal 허용.\n"
            "- `BEFORE_TASK_DISCOVERY / AFTER_TASK_SELECT / AT_ENDPOINT`를 구분.\n"
            "- credential 입력, login submit, 본인인증 수행, CAPTCHA 해결/우회 금지."
        ),
    },
    "auth_spec": {
        "source": "SSOTV3/03_COLLECTION_MEASUREMENT_SPEC_v3.0.md §7 Auth",
        "text": (
            "- generic login 버튼 존재만으로 중단 금지.\n"
            "- task-specific path를 따라가다 auth가 불가피한 순간 `AUTH_GATE` terminal.\n"
            "- auth stage를 `BEFORE_TASK_DISCOVERY / AFTER_TASK_SELECT / AT_ENDPOINT`로 기록.\n"
            "- credential 입력·login submit·본인인증 금지."
        ),
    },
    "AUTH_GATE_glossary": {
        "source": "SSOTV3/10_GLOSSARY_v3.0.md",
        "text": "| AUTH_GATE | 사전지정 task path에서 인증이 불가피해지는 terminal. 로그인 버튼 단순 존재와 다름. |",
    },
    "fact_task_obstruction": {
        "source": "SSOTV3/02_DATA_SCHEMA_v3.0.md §5 Task-path obstruction",
        "text": (
            "### `fact_task_obstruction`\n"
            "- `observation_id`\n- `interrupt_id`\n- `interrupt_type`\n"
            "- `overlay_coverage` — 보조 설명값\n"
            "- `task_control_occlusion` — primary\n"
            "- `dismiss_control_exists`\n- `dismiss_control_visible`\n"
            "- `dismiss_control_accessible_name`\n- `dismiss_required_for_task`\n- `dismiss_succeeded`\n\n"
            "`max_overlay_coverage`만으로 modal obstruction을 대표하지 않는다."
        ),
    },
    "obstruction_spec": {
        "source": "SSOTV3/03_COLLECTION_MEASUREMENT_SPEC_v3.0.md §9 Obstruction",
        "text": (
            "popup/modal/banner/fixed/sticky 후보를 수집하되 primary obstruction은 **task-specific**으로 판정한다.\n"
            "- `task_control_occlusion`\n- `dismiss_required_for_task`\n- `forced_dismissal_count`\n\n"
            "geometry overlap만으로 modal 의미를 확정하지 않는다."
        ),
    },
    "task_control_occlusion": {
        "source": "SSOTV3/04_FLOW_CODEBOOK_v3.0.md §4",
        "text": "| task_control_occlusion | Obstruction | 0~1 | task-entry control bbox와 blocking obstruction의 실제 겹침 비율 |",
    },
    "forced_dismissal_count": {
        "source": "SSOTV3/04_FLOW_CODEBOOK_v3.0.md §4",
        "text": "| forced_dismissal_count | Obstruction | count | task 진행에 실제 필요했던 dismissal 수 |",
    },
    "flow_split": {
        "source": "SSOTV3/04_FLOW_CODEBOOK_v3.0.md §3 Task Flow vs Experienced Flow",
        "text": (
            "- `task_flow_sequence`: `DISMISS_OBSTRUCTION`을 제외한 서비스 자체 task navigation.\n"
            "- `experienced_flow_sequence`: 실제 진행에 필요했던 dismissal까지 포함."
        ),
    },
    "analysis_G_H": {
        "source": "SSOTV3/05_ANALYSIS_PLAN_v3.0.md §2-G, §2-H",
        "text": (
            "### G. Auth\n- auth-gate occurrence\n- auth gate stage distribution\n\n"
            "### H. Obstruction\n- forced dismissal distribution\n- task-control occlusion"
        ),
    },
    "denominator_rule": {
        "source": "SSOTV3/05_ANALYSIS_PLAN_v3.0.md §6 Missingness / denominator",
        "text": "candidate 10 → eligible/frozen 10 → attempted 10 → evidence-bearing n → flow-evaluable n / 모든 분모를 단계별로 보고.",
    },
}

# =============================================================================
# 1. 값 도메인 (codebook 그대로. 새 값 추가 금지)
# =============================================================================

AUTH_STAGE_NONE = "NONE"
AUTH_STAGE_BEFORE = "BEFORE_TASK_DISCOVERY"
AUTH_STAGE_AFTER_SELECT = "AFTER_TASK_SELECT"
AUTH_STAGE_AT_ENDPOINT = "AT_ENDPOINT"
AUTH_STAGE_DOMAIN = (AUTH_STAGE_NONE, AUTH_STAGE_BEFORE, AUTH_STAGE_AFTER_SELECT, AUTH_STAGE_AT_ENDPOINT)

# codebook 도메인 밖. 판정 불능을 NONE 으로 흘리지 않기 위한 하네스 전용 sentinel.
AUTH_STAGE_UNDETERMINED = "UNDETERMINED__NOT_IN_CODEBOOK_DOMAIN"

CANONICAL_TOKENS = (
    "OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SWITCH_TAB", "EXPAND_ACCORDION",
    "SELECT_CATEGORY", "SELECT_FUNCTION", "INPUT_QUERY", "SELECT_ORIGIN",
    "SELECT_DESTINATION", "SELECT_DATE", "SUBMIT_QUERY", "SELECT_RESULT",
    "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL", "DISMISS_OBSTRUCTION",
    "AUTH_GATE", "ENDPOINT_REACHED", "ABSTAIN",
)

# dismissal 3분 + 2 (SSOT 에 null 의미 규정이 없어 병합하지 않고 분리 보존)
DISMISS_NO_TARGET = "NO_DISMISS_TARGET"          # 닫을 대상이 없음
DISMISS_FAILED = "DISMISS_FAILED"                # 닫기를 시도했으나 실패
DISMISS_SUCCEEDED = "DISMISS_SUCCEEDED"          # 닫기 성공
DISMISS_UNRECORDED = "DISMISS_OUTCOME_UNRECORDED"  # exists=True, succeeded=None
DISMISS_INCONSISTENT = "INCONSISTENT_DISMISS_RECORD"
DISMISS_UNKNOWN_EXISTENCE = "DISMISS_EXISTENCE_UNKNOWN"

DISMISS_THREE_WAY_CORE = (DISMISS_NO_TARGET, DISMISS_FAILED, DISMISS_SUCCEEDED)


# =============================================================================
# 2. 세 축 라벨링이 강제되는 카운터
#    (1) 단위 unit  (2) 모집단 population  (3) 원천 필드 source_fields
#    세 축 없이는 인스턴스화 자체가 안 되고, 비율도 나오지 않는다.
# =============================================================================

UNIT_DOMAIN = ("service_task_run", "flow_step", "obstruction_interrupt", "service_task_unit")


class ThreeAxisViolation(ValueError):
    pass


@dataclass(frozen=True)
class ThreeAxisCounter:
    name: str
    unit: str                       # 축 1 — 무엇 하나가 1인가
    population: str                 # 축 2 — 분모 모집단(전체/조건부 + 조건 명시)
    source_fields: tuple[str, ...]  # 축 3 — 원천 필드
    numerator: int
    denominator: int
    population_is_conditional: bool
    note: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ThreeAxisViolation("counter name required")
        if self.unit not in UNIT_DOMAIN:
            raise ThreeAxisViolation(f"[{self.name}] unit must be one of {UNIT_DOMAIN}, got {self.unit!r}")
        if not self.population or len(self.population) < 8:
            raise ThreeAxisViolation(f"[{self.name}] population(모집단) must be stated explicitly")
        if not self.source_fields:
            raise ThreeAxisViolation(f"[{self.name}] source_fields(원천 필드) must be stated")
        if self.population_is_conditional and "conditional_on" not in self.population:
            raise ThreeAxisViolation(f"[{self.name}] conditional population must name its condition via 'conditional_on:'")
        if self.numerator < 0 or self.denominator < 0:
            raise ThreeAxisViolation(f"[{self.name}] negative count")
        if self.denominator and self.numerator > self.denominator:
            raise ThreeAxisViolation(f"[{self.name}] numerator > denominator")

    def rate(self) -> float | None:
        """세 축이 없으면 애초에 객체가 안 만들어진다. 분모 0 이면 비율을 만들지 않는다."""
        if self.denominator == 0:
            return None
        return self.numerator / self.denominator

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["source_fields"] = list(self.source_fields)
        d["rate"] = self.rate()
        d["rate_undefined_reason"] = None if self.denominator else "EMPTY_DENOMINATOR"
        d["three_axis"] = {
            "unit": self.unit,
            "population": self.population,
            "source_fields": list(self.source_fields),
        }
        return d


# =============================================================================
# 3. auth_gate_stage 분류기
# =============================================================================

@dataclass(frozen=True)
class AuthStagePolicy:
    """
    stage 경계에 필요한 '무엇이 task select 인가' 는 SSOT 에 열거돼 있지 않다.
    하네스가 임의로 정하지 않고, 명시적 policy 로 노출하고 AMBIGUOUS 에 등재한다.
    default 는 codebook §2 가 '사전지정 task 기능 control 을 선택한다' 로 정의한 SELECT_FUNCTION 만.
    """
    task_select_tokens: tuple[str, ...] = ("SELECT_FUNCTION",)
    use_endpoint_signal_for_at_endpoint: bool = True
    policy_id: str = "LANE_A_DEFAULT_v1"

    # ---- mutation 검사 전용 플래그 (기본 전부 False = 정상 구현) ----
    MUTANT_landing_login_counts_as_gate: bool = False
    MUTANT_ignore_endpoint_signal: bool = False


DEFAULT_AUTH_POLICY = AuthStagePolicy()

# 분류기가 읽어도 되는 입력 필드 화이트리스트.
# landing_login_control_present 는 의도적으로 제외한다 — 존재만으로 gate 가 아니다(00 §6, 03 §7).
AUTH_ALLOWED_INPUT_FIELDS = (
    "flow_observation_id", "service_id", "task_id", "endpoint_status",
    "steps", "task_flow_sequence", "experienced_flow_sequence",
)
AUTH_FORBIDDEN_INPUT_FIELDS = (
    "landing_login_control_present",
    "landing_login_control_selector",
    "landing_login_accessible_name",
    "header_login_button_visible",
)


def project_auth_inputs(record: dict[str, Any]) -> dict[str, Any]:
    """generic login 존재 계열 필드를 구조적으로 잘라낸 projection. 분류기는 이것만 본다."""
    return {k: record.get(k) for k in AUTH_ALLOWED_INPUT_FIELDS}


@dataclass
class AuthStageResult:
    flow_observation_id: str | None
    auth_gate_stage: str
    auth_gate_present: bool | None
    auth_step_index: int | None
    evidence_source_fields: list[str]
    defects: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_auth_gate_stage(record: dict[str, Any], policy: AuthStagePolicy = DEFAULT_AUTH_POLICY) -> AuthStageResult:
    """
    codebook 정의 그대로:
      - AUTH_GATE = '사전지정 task 경로에서 인증이 불가피해지는 상태에 도달' (04 §2)
      - landing 의 generic login 존재는 gate 가 아니다 (00 §6, 03 §7, 10 Glossary)
    stage 판정 원천 = fact_flow_step.auth_gate_detected / action_token / endpoint_signal_detected (02 §4)
    """
    proj = project_auth_inputs(record)
    res = AuthStageResult(
        flow_observation_id=record.get("flow_observation_id"),
        auth_gate_stage=AUTH_STAGE_UNDETERMINED,
        auth_gate_present=None,
        auth_step_index=None,
        evidence_source_fields=[
            "fact_flow_step.auth_gate_detected",
            "fact_flow_step.action_token",
            "fact_flow_step.endpoint_signal_detected",
        ],
    )

    # --- 금지 입력이 실제로 차단됐는지 구조적 확인 ---
    for f in AUTH_FORBIDDEN_INPUT_FIELDS:
        if f in proj:
            res.defects.append(f"GUARD_BREACH_generic_login_field_reached_classifier:{f}")

    # --- MUTANT M1: generic login 존재를 gate 로 취급 (정상 구현에서는 절대 실행되지 않음) ---
    if policy.MUTANT_landing_login_counts_as_gate and record.get("landing_login_control_present") is True:
        res.auth_gate_stage = AUTH_STAGE_BEFORE
        res.auth_gate_present = True
        res.notes.append("MUTANT_M1_active")
        return res

    steps = proj.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        res.defects.append("NO_STEP_EVIDENCE")
        res.notes.append("증거 없음을 NONE 으로 흘리지 않는다 (NONE 은 '인증 게이트 없음' 이라는 실측 주장이다)")
        return res

    exp_seq = proj.get("experienced_flow_sequence") or []
    tok_has_auth = "AUTH_GATE" in list(exp_seq)

    auth_idx: int | None = None
    for i, st in enumerate(steps):
        if st.get("auth_gate_detected") is True:
            auth_idx = i
            break

    flag_has_auth = auth_idx is not None

    # --- token stream 과 step flag 의 불일치는 조용히 한쪽을 고르지 않는다 ---
    if tok_has_auth != flag_has_auth:
        res.defects.append(
            f"AUTH_TOKEN_FLAG_MISMATCH(sequence_has_AUTH_GATE={tok_has_auth},"
            f"step_auth_gate_detected={flag_has_auth})"
        )
        res.auth_gate_present = None
        return res

    if not flag_has_auth:
        res.auth_gate_stage = AUTH_STAGE_NONE
        res.auth_gate_present = False
        return res

    assert auth_idx is not None
    res.auth_gate_present = True
    res.auth_step_index = auth_idx
    auth_step = steps[auth_idx]

    use_ep = policy.use_endpoint_signal_for_at_endpoint and not policy.MUTANT_ignore_endpoint_signal
    if use_ep and auth_step.get("endpoint_signal_detected") is True:
        res.auth_gate_stage = AUTH_STAGE_AT_ENDPOINT
        return res
    if policy.MUTANT_ignore_endpoint_signal:
        res.notes.append("MUTANT_M5_active")

    selected_before = any(
        (steps[j].get("action_token") in policy.task_select_tokens) for j in range(auth_idx)
    )
    res.auth_gate_stage = AUTH_STAGE_AFTER_SELECT if selected_before else AUTH_STAGE_BEFORE
    res.notes.append(f"task_select_tokens={list(policy.task_select_tokens)} (policy {policy.policy_id})")
    return res


# =============================================================================
# 4. Obstruction 해석기 — dismissal 3분 구분 + primary/보조 분리
# =============================================================================

@dataclass(frozen=True)
class ObstructionPolicy:
    # ---- mutation 검사 전용 ----
    MUTANT_collapse_no_target_and_failed: bool = False
    MUTANT_overlay_coverage_as_primary: bool = False
    MUTANT_null_zero_conflation: bool = False
    MUTANT_dismiss_rate_denominator_all_interrupts: bool = False


DEFAULT_OBS_POLICY = ObstructionPolicy()


@dataclass
class InterruptResult:
    observation_id: str | None
    interrupt_id: str | None
    interrupt_type: str | None
    dismissal_outcome: str
    dismiss_control_visible_given_exists: bool | None
    dismiss_control_has_accessible_name: bool | None
    dismiss_required_for_task: bool | None
    primary_task_control_occlusion: float | None
    secondary_overlay_coverage: float | None
    primary_field: str
    defects: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_dismissal_outcome(row: dict[str, Any], policy: ObstructionPolicy = DEFAULT_OBS_POLICY) -> str:
    """
    승계된 구분(legacy D 코호트에서 수치는 재사용하지 않고 구분만 승계):
      닫을 대상이 없음 / 닫기를 시도했으나 실패 / 닫기 성공 — 셋은 서로 다르다.
    """
    exists = row.get("dismiss_control_exists")
    succeeded = row.get("dismiss_succeeded")

    if exists is None:
        return DISMISS_UNKNOWN_EXISTENCE
    if exists is False:
        if succeeded is True:
            return DISMISS_INCONSISTENT  # 대상이 없는데 성공했다는 기록
        if policy.MUTANT_collapse_no_target_and_failed:
            return DISMISS_FAILED        # MUTANT M2: 무대상과 실패를 뭉갬
        return DISMISS_NO_TARGET
    # exists is True
    if succeeded is True:
        return DISMISS_SUCCEEDED
    if succeeded is False:
        return DISMISS_FAILED
    return DISMISS_UNRECORDED


def interpret_interrupt(row: dict[str, Any], policy: ObstructionPolicy = DEFAULT_OBS_POLICY) -> InterruptResult:
    exists = row.get("dismiss_control_exists")
    acc_name = row.get("dismiss_control_accessible_name")

    primary_field = "task_control_occlusion"
    if policy.MUTANT_overlay_coverage_as_primary:
        primary_field = "overlay_coverage"  # MUTANT M3: 보조 설명값을 primary 로 승격

    res = InterruptResult(
        observation_id=row.get("observation_id"),
        interrupt_id=row.get("interrupt_id"),
        interrupt_type=row.get("interrupt_type"),
        dismissal_outcome=classify_dismissal_outcome(row, policy),
        dismiss_control_visible_given_exists=(row.get("dismiss_control_visible") if exists is True else None),
        dismiss_control_has_accessible_name=(
            (isinstance(acc_name, str) and acc_name.strip() != "") if exists is True else None
        ),
        dismiss_required_for_task=row.get("dismiss_required_for_task"),
        primary_task_control_occlusion=row.get(primary_field),
        secondary_overlay_coverage=row.get("overlay_coverage"),
        primary_field=primary_field,
    )

    if exists is False and row.get("dismiss_succeeded") is False:
        res.notes.append(
            "EXISTS_FALSE_WITH_SUCCEEDED_FALSE — 'false 를 기본값으로 채운 것' 인지 '시도했다 실패' 인지 "
            "SSOT 에 규정이 없다. 무대상으로 판정하되 표식을 남긴다 (AMB-O2)")
    if exists is True and row.get("dismiss_control_visible") is False:
        res.notes.append("DISMISS_CONTROL_EXISTS_BUT_NOT_VISIBLE (무대상과 별개 상태로 보존)")
    if res.dismissal_outcome == DISMISS_INCONSISTENT:
        res.defects.append("dismiss_control_exists=False 인데 dismiss_succeeded=True")
    if row.get("task_control_occlusion") is None and row.get("overlay_coverage") is not None:
        res.notes.append("primary 결측·보조만 존재 — overlay_coverage 로 대표하지 않는다 (02 §5)")
    return res


def derive_occlusion_from_geometry(*_args: Any, **_kwargs: Any) -> dict[str, str]:
    """
    03 §9: 'geometry overlap만으로 modal 의미를 확정하지 않는다.'
    기하 겹침만으로 occlusion/modal 을 확정하는 경로는 이 하네스에서 명시적으로 거부한다.
    """
    return {
        "status": "REFUSED_GEOMETRY_ONLY_DERIVATION",
        "reason": "SSOTV3/03 §9 — geometry overlap만으로 modal 의미를 확정하지 않는다",
        "action": "upstream 이 계산한 task_control_occlusion 을 pass-through 로만 사용",
    }


# =============================================================================
# 5. 결측 표현 불일치 탐지기 (같은 행 안에서 0.0 과 None 이 섞이는 상태)
# =============================================================================

NUMERIC_FIELDS_INTERRUPT = ("overlay_coverage", "task_control_occlusion")
NUMERIC_FIELDS_RUN = ("forced_dismissal_count",)
BOOL_FIELDS_INTERRUPT = (
    "dismiss_control_exists", "dismiss_control_visible", "dismiss_required_for_task", "dismiss_succeeded",
)


def detect_missingness_encoding(row: dict[str, Any], policy: ObstructionPolicy = DEFAULT_OBS_POLICY) -> dict[str, Any]:
    """
    legacy 마트에서 실제로 있었던 형태: 같은 행에서 어떤 필드는 0.0, 어떤 필드는 None.
    탐지해서 '보고' 만 한다. 어느 쪽이 옳은지 정하지 않는다(그건 새 조작화다).
    """
    out: dict[str, Any] = {"flags": [], "detail": {}}
    numeric_present = [f for f in (NUMERIC_FIELDS_INTERRUPT + NUMERIC_FIELDS_RUN) if f in row]
    zeros = [f for f in numeric_present if isinstance(row[f], (int, float)) and not isinstance(row[f], bool) and row[f] == 0]
    nulls = [f for f in numeric_present if row[f] is None]
    nonzero = [f for f in numeric_present if isinstance(row[f], (int, float)) and not isinstance(row[f], bool) and row[f] != 0]

    if policy.MUTANT_null_zero_conflation:
        # MUTANT M4: None 을 0 으로 간주 → 불일치가 보이지 않는다
        nulls = []

    if zeros and nulls:
        out["flags"].append("MIXED_NULL_ZERO_ENCODING")
        out["detail"]["zero_fields"] = zeros
        out["detail"]["null_fields"] = nulls
    if numeric_present and len(nulls) == len(numeric_present):
        out["flags"].append("ALL_NUMERIC_NULL")
    if numeric_present and len(zeros) == len(numeric_present):
        out["flags"].append("ALL_NUMERIC_ZERO")

    bool_present = [f for f in BOOL_FIELDS_INTERRUPT if f in row]
    b_false = [f for f in bool_present if row[f] is False]
    b_null = [f for f in bool_present if row[f] is None]
    if b_false and b_null and not policy.MUTANT_null_zero_conflation:
        out["flags"].append("MIXED_NULL_FALSE_ENCODING")
        out["detail"]["false_fields"] = b_false
        out["detail"]["null_bool_fields"] = b_null

    if row.get("interrupt_type") is None and (zeros or nonzero):
        out["flags"].append("NULL_INTERRUPT_TYPE_WITH_NUMERIC_MAGNITUDE")

    out["fields_examined"] = numeric_present + bool_present + (["interrupt_type"] if "interrupt_type" in row else [])
    return out


# =============================================================================
# 6. 반례 탐지기
# =============================================================================

def detect_ce_auth_timing_only(records: Sequence[dict[str, Any]],
                               policy: AuthStagePolicy = DEFAULT_AUTH_POLICY) -> dict[str, Any]:
    """
    CE-1: 다른 축은 같은데 auth_gate_stage 만 다른 경우.
    '다른 축' 은 Lane A 가 계산하지 않는다 — 호출자가 other_axis_signature(dict) 로 넘긴다.
    (flow 길이·spatial·label 은 각 lane 소관이라 여기서 계산·독해하지 않는다)
    """
    keyed: dict[str, list[tuple[str, str]]] = {}
    per_record = []
    for r in records:
        sig = r.get("other_axis_signature")
        if not isinstance(sig, dict) or not sig:
            per_record.append({"flow_observation_id": r.get("flow_observation_id"),
                               "status": "SKIPPED_NO_SIGNATURE"})
            continue
        sig_key = json.dumps(sig, sort_keys=True, ensure_ascii=False)
        stage = classify_auth_gate_stage(r, policy).auth_gate_stage
        keyed.setdefault(sig_key, []).append((str(r.get("flow_observation_id")), stage))
        per_record.append({"flow_observation_id": r.get("flow_observation_id"),
                           "auth_gate_stage": stage, "signature": sig})

    pairs = []
    for sig_key, items in keyed.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i][1] != items[j][1]:
                    pairs.append({
                        "signature": json.loads(sig_key),
                        "a": {"flow_observation_id": items[i][0], "auth_gate_stage": items[i][1]},
                        "b": {"flow_observation_id": items[j][0], "auth_gate_stage": items[j][1]},
                    })
    return {
        "detector_id": "CE-1_AUTH_TIMING_ONLY",
        "definition": "other_axis_signature 가 동일한데 auth_gate_stage 만 다른 record 쌍",
        "signature_source": "CALLER_SUPPLIED (Lane A 는 다른 축을 계산하지 않는다)",
        "unit": "service_task_run pair",
        "population": "other_axis_signature 가 제공된 run 전체 (conditional_on: signature present)",
        "n_records_with_signature": sum(1 for p in per_record if "auth_gate_stage" in p),
        "n_pairs_detected": len(pairs),
        "pairs": pairs,
        "per_record": per_record,
    }


def detect_ce_obstruction_input_positive(run: dict[str, Any],
                                         policy: ObstructionPolicy = DEFAULT_OBS_POLICY) -> dict[str, Any]:
    """
    CE-2: 'modal 때문에 experienced flow 만 길어지는 경우' 의 **obstruction 쪽 입력만** 판정.
    task_flow / experienced_flow 길이 계산은 Lane F 소관 — 여기서 계산하지도, Lane F 파일을 읽지도 않는다.
    산출은 '입력 조건 충족 여부' 이며, flow 길이 차이 자체를 주장하지 않는다.
    """
    fdc = run.get("forced_dismissal_count")
    interrupts = run.get("interrupts") or []
    required = [i for i in interrupts if i.get("dismiss_required_for_task") is True]
    required_and_succeeded = [i for i in required if classify_dismissal_outcome(i, policy) == DISMISS_SUCCEEDED]
    required_but_failed = [i for i in required if classify_dismissal_outcome(i, policy) == DISMISS_FAILED]
    required_no_target = [i for i in required if classify_dismissal_outcome(i, policy) == DISMISS_NO_TARGET]

    defects: list[str] = []
    if isinstance(fdc, int) and fdc > 0 and not required:
        defects.append("FORCED_DISMISSAL_WITHOUT_REQUIRED_INTERRUPT")
    if isinstance(fdc, int) and fdc == 0 and required_and_succeeded:
        defects.append("REQUIRED_DISMISSAL_SUCCEEDED_BUT_FORCED_COUNT_ZERO")
    if fdc is None and interrupts:
        defects.append("FORCED_DISMISSAL_COUNT_NULL_WITH_INTERRUPT_ROWS")

    if fdc is None:
        verdict = "UNDETERMINED"
    elif isinstance(fdc, int) and fdc > 0 and required_and_succeeded:
        verdict = "OBSTRUCTION_SIDE_POSITIVE"
    elif required_but_failed or required_no_target:
        verdict = "OBSTRUCTION_SIDE_REQUIRED_BUT_NOT_DISMISSED"
    else:
        verdict = "OBSTRUCTION_SIDE_NEGATIVE"

    return {
        "detector_id": "CE-2_OBSTRUCTION_INPUT_FOR_EXPERIENCED_FLOW",
        "flow_observation_id": run.get("flow_observation_id"),
        "verdict": verdict,
        "forced_dismissal_count": fdc,
        "n_interrupts": len(interrupts),
        "n_dismiss_required": len(required),
        "n_required_and_succeeded": len(required_and_succeeded),
        "n_required_but_failed": len(required_but_failed),
        "n_required_no_target": len(required_no_target),
        "defects": defects,
        "not_computed_here": [
            "task_flow_sequence 길이",
            "experienced_flow_sequence 길이",
            "두 길이의 차이",
        ],
        "handoff": "flow 길이 비교는 Lane F 가 수행한다. Lane A 는 obstruction 쪽 입력만 판정한다.",
    }


# =============================================================================
# 7. 세 축 카운터 산출 (모든 비율에 unit/population/source 부착)
# =============================================================================

def build_counters(runs: Sequence[dict[str, Any]],
                   auth_policy: AuthStagePolicy = DEFAULT_AUTH_POLICY,
                   obs_policy: ObstructionPolicy = DEFAULT_OBS_POLICY) -> list[ThreeAxisCounter]:
    counters: list[ThreeAxisCounter] = []

    auth_results = [classify_auth_gate_stage(r, auth_policy) for r in runs]
    evaluable = [a for a in auth_results if a.auth_gate_stage in AUTH_STAGE_DOMAIN]

    counters.append(ThreeAxisCounter(
        name="auth_gate_occurrence",
        unit="service_task_run",
        population="auth 판정 가능한 run 전체 (conditional_on: auth_gate_stage in codebook domain; UNDETERMINED 제외)",
        source_fields=("fact_flow_step.auth_gate_detected", "fact_flow_observation.experienced_flow_sequence"),
        numerator=sum(1 for a in evaluable if a.auth_gate_present is True),
        denominator=len(evaluable),
        population_is_conditional=True,
        note="분모에 UNDETERMINED 를 넣지 않는다. 05 §6 단계별 분모 규칙.",
    ))

    for stage in AUTH_STAGE_DOMAIN:
        counters.append(ThreeAxisCounter(
            name=f"auth_stage_share__{stage}",
            unit="service_task_run",
            population="auth 판정 가능한 run 전체 (conditional_on: auth_gate_stage in codebook domain)",
            source_fields=("fact_flow_step.auth_gate_detected", "fact_flow_step.action_token",
                           "fact_flow_step.endpoint_signal_detected"),
            numerator=sum(1 for a in evaluable if a.auth_gate_stage == stage),
            denominator=len(evaluable),
            population_is_conditional=True,
        ))

    counters.append(ThreeAxisCounter(
        name="auth_stage_undetermined",
        unit="service_task_run",
        population="입력된 run 전체 (무조건)",
        source_fields=("fact_flow_step.auth_gate_detected", "fact_flow_observation.experienced_flow_sequence"),
        numerator=sum(1 for a in auth_results if a.auth_gate_stage == AUTH_STAGE_UNDETERMINED),
        denominator=len(auth_results),
        population_is_conditional=False,
    ))

    interrupts: list[dict[str, Any]] = []
    for r in runs:
        interrupts.extend(r.get("interrupts") or [])
    outcomes = [classify_dismissal_outcome(i, obs_policy) for i in interrupts]

    counters.append(ThreeAxisCounter(
        name="interrupt_with_dismiss_target",
        unit="obstruction_interrupt",
        population="fact_task_obstruction 행 전체 (무조건)",
        source_fields=("fact_task_obstruction.dismiss_control_exists",),
        numerator=sum(1 for i in interrupts if i.get("dismiss_control_exists") is True),
        denominator=len(interrupts),
        population_is_conditional=False,
    ))

    for oc in (DISMISS_NO_TARGET, DISMISS_FAILED, DISMISS_SUCCEEDED, DISMISS_UNRECORDED,
               DISMISS_INCONSISTENT, DISMISS_UNKNOWN_EXISTENCE):
        counters.append(ThreeAxisCounter(
            name=f"dismissal_outcome__{oc}",
            unit="obstruction_interrupt",
            population="fact_task_obstruction 행 전체 (무조건)",
            source_fields=("fact_task_obstruction.dismiss_control_exists", "fact_task_obstruction.dismiss_succeeded"),
            numerator=sum(1 for o in outcomes if o == oc),
            denominator=len(interrupts),
            population_is_conditional=False,
            note="무대상/실패/성공을 하나로 뭉개지 않는다.",
        ))

    # 성공률의 분모는 '닫을 대상이 있고 결과가 기록된' 조건부 모집단이다.
    cond = [i for i in interrupts
            if i.get("dismiss_control_exists") is True and i.get("dismiss_succeeded") is not None]
    if obs_policy.MUTANT_dismiss_rate_denominator_all_interrupts:
        cond = list(interrupts)  # MUTANT M6
    counters.append(ThreeAxisCounter(
        name="dismiss_success_rate",
        unit="obstruction_interrupt",
        population="conditional_on: dismiss_control_exists=True AND dismiss_succeeded is not null",
        source_fields=("fact_task_obstruction.dismiss_control_exists", "fact_task_obstruction.dismiss_succeeded"),
        numerator=sum(1 for i in cond if i.get("dismiss_succeeded") is True),
        denominator=len(cond),
        population_is_conditional=True,
        note="전체 interrupt 를 분모로 쓰면 '닫을 대상 없음' 이 실패로 섞인다.",
    ))

    exists_rows = [i for i in interrupts if i.get("dismiss_control_exists") is True]
    counters.append(ThreeAxisCounter(
        name="dismiss_control_visible_given_exists",
        unit="obstruction_interrupt",
        population="conditional_on: dismiss_control_exists=True",
        source_fields=("fact_task_obstruction.dismiss_control_visible",),
        numerator=sum(1 for i in exists_rows if i.get("dismiss_control_visible") is True),
        denominator=len(exists_rows),
        population_is_conditional=True,
    ))
    counters.append(ThreeAxisCounter(
        name="dismiss_control_named_given_exists",
        unit="obstruction_interrupt",
        population="conditional_on: dismiss_control_exists=True",
        source_fields=("fact_task_obstruction.dismiss_control_accessible_name",),
        numerator=sum(1 for i in exists_rows
                      if isinstance(i.get("dismiss_control_accessible_name"), str)
                      and i["dismiss_control_accessible_name"].strip() != ""),
        denominator=len(exists_rows),
        population_is_conditional=True,
    ))
    counters.append(ThreeAxisCounter(
        name="dismiss_required_for_task",
        unit="obstruction_interrupt",
        population="fact_task_obstruction 행 전체 (무조건)",
        source_fields=("fact_task_obstruction.dismiss_required_for_task",),
        numerator=sum(1 for i in interrupts if i.get("dismiss_required_for_task") is True),
        denominator=len(interrupts),
        population_is_conditional=False,
    ))
    runs_with_fdc = [r for r in runs if isinstance(r.get("forced_dismissal_count"), int)]
    counters.append(ThreeAxisCounter(
        name="run_with_forced_dismissal",
        unit="service_task_run",
        population="conditional_on: forced_dismissal_count is not null",
        source_fields=("fact_flow_observation.forced_dismissal_count",),
        numerator=sum(1 for r in runs_with_fdc if r["forced_dismissal_count"] > 0),
        denominator=len(runs_with_fdc),
        population_is_conditional=True,
    ))
    return counters


# =============================================================================
# 8. 합성 fixture (REAL 아님. 모두 이 파일 안에서 생성)
# =============================================================================

def _step(idx: int, token: str, auth: bool = False, endpoint: bool = False) -> dict[str, Any]:
    return {"step_index": idx, "action_token": token,
            "auth_gate_detected": auth, "endpoint_signal_detected": endpoint}


def auth_fixtures() -> list[dict[str, Any]]:
    return [
        {   # ★ 필수: AUTH_GATE 오탐 fixture — landing 에 로그인 버튼이 있으나 task path 와 무관
            "id": "A-F01_landing_login_present_but_task_path_unrelated",
            "polarity": "NEGATIVE",
            "expected": AUTH_STAGE_NONE,
            "record": {
                "flow_observation_id": "FX-A01", "service_id": "SVC_X", "task_id": "F3_T",
                "landing_login_control_present": True,
                "landing_login_accessible_name": "로그인",
                "task_flow_sequence": ["SELECT_FUNCTION", "INPUT_QUERY", "ENDPOINT_REACHED"],
                "experienced_flow_sequence": ["SELECT_FUNCTION", "INPUT_QUERY", "ENDPOINT_REACHED"],
                "steps": [_step(0, "SELECT_FUNCTION"), _step(1, "INPUT_QUERY"),
                          _step(2, "ENDPOINT_REACHED", endpoint=True)],
                "endpoint_status": "REACHED",
            },
        },
        {
            "id": "A-F02_auth_before_task_discovery",
            "polarity": "POSITIVE",
            "expected": AUTH_STAGE_BEFORE,
            "record": {
                "flow_observation_id": "FX-A02", "service_id": "SVC_Y", "task_id": "F1_T",
                "landing_login_control_present": True,
                "task_flow_sequence": ["OPEN_GLOBAL_MENU", "AUTH_GATE"],
                "experienced_flow_sequence": ["OPEN_GLOBAL_MENU", "AUTH_GATE"],
                "steps": [_step(0, "OPEN_GLOBAL_MENU"), _step(1, "AUTH_GATE", auth=True)],
                "endpoint_status": "AUTH_GATE",
            },
        },
        {
            "id": "A-F03_auth_after_task_select",
            "polarity": "POSITIVE",
            "expected": AUTH_STAGE_AFTER_SELECT,
            "record": {
                "flow_observation_id": "FX-A03", "service_id": "SVC_Z", "task_id": "F1_T",
                "landing_login_control_present": False,
                "task_flow_sequence": ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"],
                "experienced_flow_sequence": ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"],
                "steps": [_step(0, "OPEN_GLOBAL_MENU"), _step(1, "SELECT_FUNCTION"),
                          _step(2, "AUTH_GATE", auth=True)],
                "endpoint_status": "AUTH_GATE",
            },
        },
        {
            "id": "A-F04_auth_at_endpoint",
            "polarity": "POSITIVE",
            "expected": AUTH_STAGE_AT_ENDPOINT,
            "record": {
                "flow_observation_id": "FX-A04", "service_id": "SVC_W", "task_id": "F1_T",
                "landing_login_control_present": False,
                "task_flow_sequence": ["SELECT_FUNCTION", "AUTH_GATE"],
                "experienced_flow_sequence": ["SELECT_FUNCTION", "AUTH_GATE"],
                "steps": [_step(0, "SELECT_FUNCTION"), _step(1, "AUTH_GATE", auth=True, endpoint=True)],
                "endpoint_status": "AUTH_GATE",
            },
        },
        {
            "id": "A-F05_token_flag_mismatch",
            "polarity": "NEGATIVE",
            "expected": AUTH_STAGE_UNDETERMINED,
            "expected_defect_substr": "AUTH_TOKEN_FLAG_MISMATCH",
            "record": {
                "flow_observation_id": "FX-A05", "service_id": "SVC_V", "task_id": "F1_T",
                "task_flow_sequence": ["SELECT_FUNCTION", "AUTH_GATE"],
                "experienced_flow_sequence": ["SELECT_FUNCTION", "AUTH_GATE"],
                "steps": [_step(0, "SELECT_FUNCTION"), _step(1, "AUTH_GATE", auth=False)],
                "endpoint_status": "AUTH_GATE",
            },
        },
        {   # A-F02 의 양방향 대조군: 같은 step 열, auth flag/token 만 없음
            "id": "A-F06_control_for_A_F02_no_auth_flag",
            "polarity": "NEGATIVE",
            "expected": AUTH_STAGE_NONE,
            "record": {
                "flow_observation_id": "FX-A06", "service_id": "SVC_Y2", "task_id": "F1_T",
                "landing_login_control_present": True,
                "task_flow_sequence": ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION"],
                "experienced_flow_sequence": ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION"],
                "steps": [_step(0, "OPEN_GLOBAL_MENU"), _step(1, "SELECT_FUNCTION")],
                "endpoint_status": "REACHED",
            },
        },
        {   # landing login 존재가 stage 를 만들지도, 지우지도 않는다
            "id": "A-F07_landing_login_present_and_real_gate_after_select",
            "polarity": "POSITIVE",
            "expected": AUTH_STAGE_AFTER_SELECT,
            "record": {
                "flow_observation_id": "FX-A07", "service_id": "SVC_U", "task_id": "F1_T",
                "landing_login_control_present": True,
                "task_flow_sequence": ["SELECT_FUNCTION", "AUTH_GATE"],
                "experienced_flow_sequence": ["SELECT_FUNCTION", "AUTH_GATE"],
                "steps": [_step(0, "SELECT_FUNCTION"), _step(1, "AUTH_GATE", auth=True)],
                "endpoint_status": "AUTH_GATE",
            },
        },
        {
            "id": "A-F08_no_step_evidence",
            "polarity": "NEGATIVE",
            "expected": AUTH_STAGE_UNDETERMINED,
            "expected_defect_substr": "NO_STEP_EVIDENCE",
            "record": {
                "flow_observation_id": "FX-A08", "service_id": "SVC_T", "task_id": "F2_T",
                "landing_login_control_present": True,
                "task_flow_sequence": [], "experienced_flow_sequence": [], "steps": [],
                "endpoint_status": "ABSTAIN",
            },
        },
    ]


def obstruction_fixtures() -> list[dict[str, Any]]:
    return [
        {"id": "O-F01_no_dismiss_target", "expected_outcome": DISMISS_NO_TARGET,
         "row": {"observation_id": "FX-O01", "interrupt_id": "i1", "interrupt_type": "MODAL",
                 "overlay_coverage": 0.71, "task_control_occlusion": 0.44,
                 "dismiss_control_exists": False, "dismiss_control_visible": False,
                 "dismiss_control_accessible_name": None,
                 "dismiss_required_for_task": True, "dismiss_succeeded": None}},
        {"id": "O-F02_dismiss_attempted_and_failed", "expected_outcome": DISMISS_FAILED,
         "row": {"observation_id": "FX-O02", "interrupt_id": "i1", "interrupt_type": "MODAL",
                 "overlay_coverage": 0.68, "task_control_occlusion": 0.52,
                 "dismiss_control_exists": True, "dismiss_control_visible": True,
                 "dismiss_control_accessible_name": "닫기",
                 "dismiss_required_for_task": True, "dismiss_succeeded": False}},
        {"id": "O-F03_dismiss_succeeded", "expected_outcome": DISMISS_SUCCEEDED,
         "row": {"observation_id": "FX-O03", "interrupt_id": "i1", "interrupt_type": "MODAL",
                 "overlay_coverage": 0.66, "task_control_occlusion": 0.50,
                 "dismiss_control_exists": True, "dismiss_control_visible": True,
                 "dismiss_control_accessible_name": "닫기",
                 "dismiss_required_for_task": True, "dismiss_succeeded": True}},
        {"id": "O-F04_outcome_unrecorded", "expected_outcome": DISMISS_UNRECORDED,
         "row": {"observation_id": "FX-O04", "interrupt_id": "i1", "interrupt_type": "BANNER",
                 "overlay_coverage": 0.12, "task_control_occlusion": 0.0,
                 "dismiss_control_exists": True, "dismiss_control_visible": True,
                 "dismiss_control_accessible_name": "", "dismiss_required_for_task": False,
                 "dismiss_succeeded": None}},
        {"id": "O-F05_inconsistent_record", "expected_outcome": DISMISS_INCONSISTENT,
         "row": {"observation_id": "FX-O05", "interrupt_id": "i1", "interrupt_type": "MODAL",
                 "overlay_coverage": 0.30, "task_control_occlusion": 0.10,
                 "dismiss_control_exists": False, "dismiss_control_visible": False,
                 "dismiss_control_accessible_name": None,
                 "dismiss_required_for_task": True, "dismiss_succeeded": True}},
        {"id": "O-F06_high_coverage_zero_task_occlusion", "expected_outcome": DISMISS_SUCCEEDED,
         "expected_primary_value": 0.0,
         "row": {"observation_id": "FX-O06", "interrupt_id": "i1", "interrupt_type": "FIXED_BOTTOM",
                 "overlay_coverage": 0.92, "task_control_occlusion": 0.0,
                 "dismiss_control_exists": True, "dismiss_control_visible": True,
                 "dismiss_control_accessible_name": "닫기",
                 "dismiss_required_for_task": False, "dismiss_succeeded": True}},
        {"id": "O-F07_mixed_null_zero_same_row", "expected_missing_flag": "MIXED_NULL_ZERO_ENCODING",
         "expected_outcome": DISMISS_UNKNOWN_EXISTENCE,
         "row": {"observation_id": "FX-O07", "interrupt_id": "i1", "interrupt_type": "MODAL",
                 "overlay_coverage": 0.0, "task_control_occlusion": None,
                 "dismiss_control_exists": None, "dismiss_control_visible": None,
                 "dismiss_control_accessible_name": None,
                 "dismiss_required_for_task": None, "dismiss_succeeded": None}},
        {"id": "O-F08_all_zero_consistent", "expected_missing_flag_absent": "MIXED_NULL_ZERO_ENCODING",
         "expected_outcome": DISMISS_NO_TARGET,
         "row": {"observation_id": "FX-O08", "interrupt_id": "i1", "interrupt_type": "BANNER",
                 "overlay_coverage": 0.0, "task_control_occlusion": 0.0,
                 "dismiss_control_exists": False, "dismiss_control_visible": False,
                 "dismiss_control_accessible_name": None,
                 "dismiss_required_for_task": False, "dismiss_succeeded": False}},
        {"id": "O-F09_all_null_consistent", "expected_missing_flag": "ALL_NUMERIC_NULL",
         "expected_missing_flag_absent": "MIXED_NULL_ZERO_ENCODING",
         "expected_outcome": DISMISS_UNKNOWN_EXISTENCE,
         "row": {"observation_id": "FX-O09", "interrupt_id": "i1", "interrupt_type": None,
                 "overlay_coverage": None, "task_control_occlusion": None,
                 "dismiss_control_exists": None, "dismiss_control_visible": None,
                 "dismiss_control_accessible_name": None,
                 "dismiss_required_for_task": None, "dismiss_succeeded": None}},
    ]


def ce_fixtures() -> dict[str, Any]:
    base_steps_none = [_step(0, "SELECT_FUNCTION"), _step(1, "ENDPOINT_REACHED", endpoint=True)]
    base_steps_after = [_step(0, "SELECT_FUNCTION"), _step(1, "AUTH_GATE", auth=True)]
    sig_a = {"entry_zone": "TOP_LEFT", "entry_control_type": "HAMBURGER", "menu_dependency": 1}
    sig_b = {"entry_zone": "BOTTOM", "entry_control_type": "BOTTOM_NAV", "menu_dependency": 0}

    ce1_records = [
        {"flow_observation_id": "CE1-R1", "other_axis_signature": sig_a,
         "experienced_flow_sequence": ["SELECT_FUNCTION", "ENDPOINT_REACHED"], "steps": base_steps_none},
        {"flow_observation_id": "CE1-R2", "other_axis_signature": sig_a,   # 같은 축, 다른 auth timing → 탐지
         "experienced_flow_sequence": ["SELECT_FUNCTION", "AUTH_GATE"], "steps": base_steps_after},
        {"flow_observation_id": "CE1-R3", "other_axis_signature": sig_b,   # 다른 축 + 다른 timing → 미탐지
         "experienced_flow_sequence": ["SELECT_FUNCTION", "AUTH_GATE"], "steps": base_steps_after},
        {"flow_observation_id": "CE1-R4", "other_axis_signature": sig_b,   # 같은 축, 같은 timing → 미탐지
         "experienced_flow_sequence": ["SELECT_FUNCTION", "AUTH_GATE"], "steps": base_steps_after},
        {"flow_observation_id": "CE1-R5", "experienced_flow_sequence": [], "steps": base_steps_none},  # signature 없음
    ]

    ce2_runs = [
        {"id": "O-F10_forced_count_without_required_interrupt",
         "expected_verdict": "OBSTRUCTION_SIDE_NEGATIVE",
         "expected_defect": "FORCED_DISMISSAL_WITHOUT_REQUIRED_INTERRUPT",
         "run": {"flow_observation_id": "CE2-R1", "forced_dismissal_count": 2,
                 "interrupts": [{"interrupt_id": "i1", "dismiss_control_exists": True,
                                 "dismiss_required_for_task": False, "dismiss_succeeded": True}]}},
        {"id": "O-F11_required_and_succeeded",
         "expected_verdict": "OBSTRUCTION_SIDE_POSITIVE", "expected_defect": None,
         "run": {"flow_observation_id": "CE2-R2", "forced_dismissal_count": 1,
                 "interrupts": [{"interrupt_id": "i1", "dismiss_control_exists": True,
                                 "dismiss_required_for_task": True, "dismiss_succeeded": True}]}},
        {"id": "O-F12_no_obstruction_input",
         "expected_verdict": "OBSTRUCTION_SIDE_NEGATIVE", "expected_defect": None,
         "run": {"flow_observation_id": "CE2-R3", "forced_dismissal_count": 0, "interrupts": []}},
        {"id": "O-F13_required_but_no_dismiss_target",
         "expected_verdict": "OBSTRUCTION_SIDE_REQUIRED_BUT_NOT_DISMISSED", "expected_defect": None,
         "run": {"flow_observation_id": "CE2-R4", "forced_dismissal_count": 0,
                 "interrupts": [{"interrupt_id": "i1", "dismiss_control_exists": False,
                                 "dismiss_required_for_task": True, "dismiss_succeeded": None}]}},
        {"id": "O-F14_fdc_null_with_interrupts",
         "expected_verdict": "UNDETERMINED",
         "expected_defect": "FORCED_DISMISSAL_COUNT_NULL_WITH_INTERRUPT_ROWS",
         "run": {"flow_observation_id": "CE2-R5", "forced_dismissal_count": None,
                 "interrupts": [{"interrupt_id": "i1", "dismiss_control_exists": True,
                                 "dismiss_required_for_task": True, "dismiss_succeeded": True}]}},
    ]
    return {"ce1_records": ce1_records, "ce2_runs": ce2_runs}


# =============================================================================
# 9. Fixture 실행 (양방향 대조)
# =============================================================================

def run_fixture_suite(auth_policy: AuthStagePolicy = DEFAULT_AUTH_POLICY,
                      obs_policy: ObstructionPolicy = DEFAULT_OBS_POLICY) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    for fx in auth_fixtures():
        r = classify_auth_gate_stage(fx["record"], auth_policy)
        ok = (r.auth_gate_stage == fx["expected"])
        if fx.get("expected_defect_substr"):
            ok = ok and any(fx["expected_defect_substr"] in d for d in r.defects)
        # 가드 위반은 어떤 경우에도 실패
        ok = ok and not any(d.startswith("GUARD_BREACH") for d in r.defects)
        results.append({"fixture_id": fx["id"], "kind": "AUTH", "polarity": fx["polarity"],
                        "expected": fx["expected"], "actual": r.auth_gate_stage,
                        "defects": r.defects, "status": "PASS" if ok else "FAIL"})

    for fx in obstruction_fixtures():
        ir = interpret_interrupt(fx["row"], obs_policy)
        miss = detect_missingness_encoding(fx["row"], obs_policy)
        ok = True
        detail: dict[str, Any] = {"actual_outcome": ir.dismissal_outcome,
                                  "missing_flags": miss["flags"],
                                  "primary_field": ir.primary_field,
                                  "primary_value": ir.primary_task_control_occlusion,
                                  "secondary_overlay_coverage": ir.secondary_overlay_coverage}
        if "expected_outcome" in fx:
            ok = ok and ir.dismissal_outcome == fx["expected_outcome"]
        if "expected_primary_value" in fx:
            ok = ok and ir.primary_task_control_occlusion == fx["expected_primary_value"]
        if "expected_missing_flag" in fx:
            ok = ok and fx["expected_missing_flag"] in miss["flags"]
        if "expected_missing_flag_absent" in fx:
            ok = ok and fx["expected_missing_flag_absent"] not in miss["flags"]
        results.append({"fixture_id": fx["id"], "kind": "OBSTRUCTION",
                        "expected": {k: v for k, v in fx.items() if k.startswith("expected")},
                        "actual": detail, "status": "PASS" if ok else "FAIL"})

    ces = ce_fixtures()
    ce1 = detect_ce_auth_timing_only(ces["ce1_records"], auth_policy)
    ce1_ids = {tuple(sorted([p["a"]["flow_observation_id"], p["b"]["flow_observation_id"]])) for p in ce1["pairs"]}
    ce1_ok = (ce1_ids == {("CE1-R1", "CE1-R2")})
    results.append({"fixture_id": "CE1-F_auth_timing_only_detection", "kind": "COUNTEREXAMPLE",
                    "expected": "정확히 {CE1-R1,CE1-R2} 한 쌍만 탐지 (다른 축이 다르거나 timing 이 같으면 미탐지)",
                    "actual": sorted([list(x) for x in ce1_ids]),
                    "status": "PASS" if ce1_ok else "FAIL"})

    for fx in ces["ce2_runs"]:
        out = detect_ce_obstruction_input_positive(fx["run"], obs_policy)
        ok = out["verdict"] == fx["expected_verdict"]
        if fx.get("expected_defect"):
            ok = ok and fx["expected_defect"] in out["defects"]
        else:
            ok = ok and not out["defects"]
        results.append({"fixture_id": fx["id"], "kind": "COUNTEREXAMPLE",
                        "expected": {"verdict": fx["expected_verdict"], "defect": fx.get("expected_defect")},
                        "actual": {"verdict": out["verdict"], "defects": out["defects"]},
                        "status": "PASS" if ok else "FAIL"})

    # geometry-only 유도 거부
    g = derive_occlusion_from_geometry(bbox_control=[0, 0, 10, 10], bbox_overlay=[0, 0, 10, 10])
    results.append({"fixture_id": "O-F15_geometry_only_derivation_refused", "kind": "OBSTRUCTION",
                    "expected": "REFUSED_GEOMETRY_ONLY_DERIVATION", "actual": g["status"],
                    "status": "PASS" if g["status"] == "REFUSED_GEOMETRY_ONLY_DERIVATION" else "FAIL"})

    # 세 축 없는 카운터 생성 시도는 거부돼야 한다
    try:
        ThreeAxisCounter(name="bad", unit="service_task_run", population="", source_fields=(),
                         numerator=1, denominator=2, population_is_conditional=False)
        three_axis_ok = False
    except ThreeAxisViolation:
        three_axis_ok = True
    results.append({"fixture_id": "X-F01_counter_without_three_axes_rejected", "kind": "GUARD",
                    "expected": "ThreeAxisViolation", "actual": "raised" if three_axis_ok else "not raised",
                    "status": "PASS" if three_axis_ok else "FAIL"})

    # 조건부 모집단인데 조건을 명시하지 않은 카운터도 거부
    try:
        ThreeAxisCounter(name="bad2", unit="obstruction_interrupt", population="일부 행만 사용",
                         source_fields=("x",), numerator=1, denominator=2, population_is_conditional=True)
        cond_ok = False
    except ThreeAxisViolation:
        cond_ok = True
    results.append({"fixture_id": "X-F02_conditional_population_must_name_condition", "kind": "GUARD",
                    "expected": "ThreeAxisViolation", "actual": "raised" if cond_ok else "not raised",
                    "status": "PASS" if cond_ok else "FAIL"})

    # 안전 스캐너 자체의 변이 검사: 금지 문자열을 심은 합성 소스를 잡아야 한다
    planted = "def f():\n    requests.post(url, data={'pw': pw})\n"   # SAFETY_DECL (합성 문자열, 실행 안 함)
    planted_res = safety_selfcheck(source_override=planted)
    clean_res = safety_selfcheck(source_override="def f():\n    return 1\n")
    scanner_ok = planted_res["status"] == "FAIL" and clean_res["status"] == "PASS"
    results.append({"fixture_id": "X-F03_safety_scanner_catches_planted_forbidden_call", "kind": "GUARD",
                    "expected": "planted=FAIL, clean=PASS",
                    "actual": {"planted": planted_res["status"], "clean": clean_res["status"]},
                    "status": "PASS" if scanner_ok else "FAIL"})

    n_pass = sum(1 for r in results if r["status"] == "PASS")
    return {"n_total": len(results), "n_pass": n_pass, "n_fail": len(results) - n_pass, "results": results}


# =============================================================================
# 10. 변이(mutation) 검사 — 일부러 틀리게 바꿔 fixture 가 잡는지 확인 후 원복
#     mutant 는 policy 플래그이므로 원복은 구조적으로 보장된다(원본 소스 불변).
# =============================================================================

MUTANTS: list[dict[str, Any]] = [
    {"mutant_id": "M1_landing_login_counts_as_auth_gate",
     "description": "landing 의 generic login 존재를 AUTH_GATE 로 취급 (00 §6 위반)",
     "auth_kwargs": {"MUTANT_landing_login_counts_as_gate": True}, "obs_kwargs": {},
     "must_fail_fixtures": ["A-F01_landing_login_present_but_task_path_unrelated"]},
    {"mutant_id": "M2_collapse_no_target_and_failed",
     "description": "'닫을 대상 없음' 과 '닫기 실패' 를 하나로 뭉갬",
     "auth_kwargs": {}, "obs_kwargs": {"MUTANT_collapse_no_target_and_failed": True},
     "must_fail_fixtures": ["O-F01_no_dismiss_target", "O-F08_all_zero_consistent"]},
    {"mutant_id": "M3_overlay_coverage_as_primary",
     "description": "보조 설명값 overlay_coverage 를 primary 로 승격 (02 §5 위반)",
     "auth_kwargs": {}, "obs_kwargs": {"MUTANT_overlay_coverage_as_primary": True},
     "must_fail_fixtures": ["O-F06_high_coverage_zero_task_occlusion"]},
    {"mutant_id": "M4_null_zero_conflation",
     "description": "None 을 0 으로 간주해 결측 표현 불일치를 은폐",
     "auth_kwargs": {}, "obs_kwargs": {"MUTANT_null_zero_conflation": True},
     "must_fail_fixtures": ["O-F07_mixed_null_zero_same_row"]},
    {"mutant_id": "M5_ignore_endpoint_signal",
     "description": "endpoint_signal_detected 를 무시해 AT_ENDPOINT 를 AFTER_TASK_SELECT 로 오분류",
     "auth_kwargs": {"MUTANT_ignore_endpoint_signal": True}, "obs_kwargs": {},
     "must_fail_fixtures": ["A-F04_auth_at_endpoint"]},
]


def run_mutation_tests() -> dict[str, Any]:
    baseline = run_fixture_suite()
    out: list[dict[str, Any]] = []
    for m in MUTANTS:
        ap = AuthStagePolicy(**m["auth_kwargs"])
        op = ObstructionPolicy(**m["obs_kwargs"])
        suite = run_fixture_suite(ap, op)
        failed = {r["fixture_id"] for r in suite["results"] if r["status"] == "FAIL"}
        caught = [f for f in m["must_fail_fixtures"] if f in failed]
        missed = [f for f in m["must_fail_fixtures"] if f not in failed]
        out.append({
            "mutant_id": m["mutant_id"], "description": m["description"],
            "expected_to_break": m["must_fail_fixtures"],
            "actually_failed_fixtures": sorted(failed),
            "caught": caught, "missed": missed,
            "status": "DETECTED" if not missed else "NOT_DETECTED",
        })
    # M6 은 fixture 가 아니라 카운터 분모 불변식으로 잡는다
    runs = _counter_probe_runs()
    normal = {c.name: c for c in build_counters(runs)}
    mutated = {c.name: c for c in build_counters(runs, obs_policy=ObstructionPolicy(
        MUTANT_dismiss_rate_denominator_all_interrupts=True))}
    m6_detected = normal["dismiss_success_rate"].denominator != mutated["dismiss_success_rate"].denominator
    out.append({
        "mutant_id": "M6_dismiss_rate_denominator_all_interrupts",
        "description": "dismiss_success_rate 분모를 전체 interrupt 로 바꿔 '닫을 대상 없음' 을 실패로 섞음",
        "expected_to_break": ["counter_invariant:dismiss_success_rate.denominator"],
        "actually_failed_fixtures": [],
        "caught": ["counter_invariant:dismiss_success_rate.denominator"] if m6_detected else [],
        "missed": [] if m6_detected else ["counter_invariant:dismiss_success_rate.denominator"],
        "observed": {"normal_denominator": normal["dismiss_success_rate"].denominator,
                     "mutated_denominator": mutated["dismiss_success_rate"].denominator},
        "status": "DETECTED" if m6_detected else "NOT_DETECTED",
    })

    reverted = run_fixture_suite()  # 원복 확인 (mutant 는 플래그이므로 소스 불변)
    return {
        "baseline": {"n_total": baseline["n_total"], "n_pass": baseline["n_pass"], "n_fail": baseline["n_fail"]},
        "mutants": out,
        "n_mutants": len(out),
        "n_detected": sum(1 for m in out if m["status"] == "DETECTED"),
        "revert_check": {"n_total": reverted["n_total"], "n_pass": reverted["n_pass"],
                         "n_fail": reverted["n_fail"],
                         "identical_to_baseline": reverted["n_fail"] == baseline["n_fail"]
                                                  and reverted["n_pass"] == baseline["n_pass"]},
        "revert_mechanism": "mutant 는 frozen policy dataclass 의 플래그다. 소스 파일을 편집하지 않으므로 원복이 구조적으로 보장된다.",
    }


def _counter_probe_runs() -> list[dict[str, Any]]:
    """카운터 산출 경로를 합성 입력으로 실행하기 위한 probe (수치 자체는 주장하지 않는다)."""
    interrupts = [fx["row"] for fx in obstruction_fixtures()]
    runs: list[dict[str, Any]] = []
    for i, fx in enumerate(auth_fixtures()):
        rec = dict(fx["record"])
        rec["forced_dismissal_count"] = [1, 0, 2, 0, None, 0, 1, None][i % 8]
        rec["interrupts"] = interrupts if i == 0 else []
        runs.append(rec)
    return runs


# =============================================================================
# 11. AMBIGUOUS_DEFINITION 등재부 — 새 조작화를 만들지 않고 올린다
# =============================================================================

AMBIGUOUS_DEFINITIONS: list[dict[str, Any]] = [
    {"id": "AMB-A1", "axis": "auth",
     "issue": "BEFORE_TASK_DISCOVERY 와 AFTER_TASK_SELECT 의 경계인 'task select' 에 해당하는 token 집합이 열거돼 있지 않다.",
     "ssot_ref": "04 §2 tokens / 04 §4 auth_gate_stage",
     "affected": ["SELECT_CATEGORY", "SWITCH_TAB", "INPUT_QUERY", "SUBMIT_QUERY",
                  "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL", "SELECT_RESULT"],
     "harness_behavior": "AuthStagePolicy.task_select_tokens 기본값 = ('SELECT_FUNCTION',) 만. "
                         "04 §2 가 SELECT_FUNCTION 을 '사전지정 task 기능 control 선택' 으로 정의한 문장에만 근거한다. "
                         "확장은 A 의 결정 없이 하지 않는다.",
     "resolution_owner": "A"},
    {"id": "AMB-A2", "axis": "auth",
     "issue": "AT_ENDPOINT 의 판정 원천이 명시돼 있지 않다. 게다가 00 §4 F1 의 endpoint contract 는 "
              "'LOGIN/IDENTITY gate 가 불가피하게 나타나는 최초 상태' 자체를 endpoint 로 정의하므로 "
              "family 에 따라 AUTH_GATE 와 ENDPOINT 가 같은 상태일 수 있다.",
     "ssot_ref": "00 §4 F1 endpoint / 04 §4 auth_gate_stage / 02 §4 fact_flow_step.endpoint_signal_detected",
     "harness_behavior": "fact_flow_step.endpoint_signal_detected 를 원천으로 사용. family 별 규칙은 만들지 않았다.",
     "resolution_owner": "A"},
    {"id": "AMB-A3", "axis": "auth",
     "issue": "auth_gate_stage 는 fact_flow_observation(=run) 단위인데, 분석단위는 service × frozen task 다. "
              "run 이 복수일 때 run→service_task_unit 집계 규칙이 없다.",
     "ssot_ref": "02 §4 / 02 §8 identity / 05 §1",
     "harness_behavior": "모든 카운터의 unit 을 service_task_run 으로 고정 표기. unit 변환을 하지 않았다.",
     "resolution_owner": "A"},
    {"id": "AMB-A4", "axis": "auth",
     "issue": "auth_gate_stage 도메인에 '판정 불능' 값이 없다. endpoint_status 에는 ABSTAIN/EVIDENCE_DEFECT 가 있으나 "
              "auth_gate_stage 에는 없어서, 증거 없는 run 을 NONE 으로 적으면 '인증 게이트 없음' 이라는 허위 실측 주장이 된다.",
     "ssot_ref": "04 §4 auth_gate_stage / 04 §4 endpoint_status",
     "harness_behavior": "codebook 도메인 밖 sentinel 'UNDETERMINED__NOT_IN_CODEBOOK_DOMAIN' 을 하네스 내부에서만 사용하고 "
                         "카운터 분모에서 분리했다. codebook 값으로 승격하지 않았다.",
     "resolution_owner": "A"},
    {"id": "AMB-O1", "axis": "obstruction",
     "issue": "task_control_occlusion 정의가 'blocking obstruction' 과의 겹침이라고 하는데 'blocking' 의 판정 기준이 없다.",
     "ssot_ref": "04 §4 task_control_occlusion / 03 §9",
     "harness_behavior": "blocking 판정선을 만들지 않았다. upstream 이 준 task_control_occlusion 을 pass-through 하고, "
                         "geometry 로부터의 재도출 요청은 REFUSED_GEOMETRY_ONLY_DERIVATION 으로 거부한다.",
     "resolution_owner": "A"},
    {"id": "AMB-O2", "axis": "obstruction",
     "issue": "dismiss_succeeded 의 null/false 의미가 규정돼 있지 않다. "
              "null = 미시도/결과 미기록/해당없음 중 무엇인지, "
              "그리고 dismiss_control_exists=False 이면서 dismiss_succeeded=False 인 행이 "
              "'false 기본값 채움' 인지 '시도했다 실패' 인지 구분할 수 없다. "
              "이 구분이 무너지면 '닫을 대상 없음' 과 '닫기 실패' 가 뭉개진다.",
     "ssot_ref": "02 §5",
     "harness_behavior": "null 을 실패로도 성공으로도 접지 않고 별도 값 DISMISS_OUTCOME_UNRECORDED 로 분리 보존. "
                         "dismiss_success_rate 분모에서 제외했다.",
     "resolution_owner": "A"},
    {"id": "AMB-O3", "axis": "obstruction",
     "issue": "task_control_occlusion 이 02 §4(run 단위 fact_flow_observation)와 02 §5(interrupt 단위 fact_task_obstruction) "
              "양쪽에 있는데 interrupt→run 집계 규칙이 없다. 02 §5 는 max 로 대표하는 것을 금지하지만 대체 집계자를 주지 않는다.",
     "ssot_ref": "02 §4 / 02 §5",
     "harness_behavior": "집계하지 않았다. interrupt 단위 값만 보고한다.",
     "resolution_owner": "A"},
    {"id": "AMB-O4", "axis": "obstruction",
     "issue": "dismiss_required_for_task 의 판정 기준이 없다. '필요했다' 는 dismissal 없이도 진행 가능했는지의 "
              "반사실을 요구하는데 수집 절차상 그 대조는 관측되지 않는다.",
     "ssot_ref": "02 §5 / 03 §9 / 04 §2 DISMISS_OBSTRUCTION",
     "harness_behavior": "upstream 이 준 boolean 을 그대로 읽는다. 재도출·보정하지 않는다.",
     "resolution_owner": "A"},
    {"id": "AMB-O5", "axis": "obstruction",
     "issue": "forced_dismissal_count 의 grain 이 문서 간 불일치. 02 §4 는 fact_flow_observation(run) 필드로 두는데 "
              "Lane A 지시문의 fact_task_obstruction 필드 목록에는 forced_dismissal_count 가 포함돼 있다. "
              "또한 이 count 가 interrupt 행들과 어떻게 대응되는지(필요&성공만? 모든 시도?) 규정이 없다.",
     "ssot_ref": "02 §4 / 02 §5 / 04 §4",
     "harness_behavior": "run grain 으로만 읽고, interrupt 행과의 불일치는 판정하지 않고 defect 로 보고만 한다 "
                         "(FORCED_DISMISSAL_WITHOUT_REQUIRED_INTERRUPT 등).",
     "resolution_owner": "A"},
    {"id": "AMB-O6", "axis": "obstruction",
     "issue": "overlay_coverage 의 분모(viewport 면적 / document 면적 / 가시영역)가 규정돼 있지 않다.",
     "ssot_ref": "02 §5 / 04 §4",
     "harness_behavior": "보조 설명값으로만 pass-through 하고 어떤 판정에도 쓰지 않는다.",
     "resolution_owner": "A"},
    {"id": "AMB-O7", "axis": "obstruction",
     "issue": "'허용된 닫기 control' (04 §2 DISMISS_OBSTRUCTION) 의 허용 범위가 열거돼 있지 않다. "
              "dismiss_control_exists 가 X 버튼만인지, 배경 탭/ESC/'오늘 그만보기' 를 포함하는지 불명.",
     "ssot_ref": "04 §2 DISMISS_OBSTRUCTION / 02 §5 dismiss_control_exists",
     "harness_behavior": "control 종류를 판별하지 않는다. exists boolean 만 읽는다.",
     "resolution_owner": "A"},
]


# =============================================================================
# 12. 안전 self-check
# =============================================================================

# 금지 API 정적 패턴. 이 리스트 리터럴이 있는 줄 자체는 SAFETY_DECL 마커로 스캔에서 제외한다.
FORBIDDEN_SOURCE_PATTERNS = [                                          # SAFETY_DECL
    r"requests\.(get|post|put|delete|Session)",                        # SAFETY_DECL
    r"\burllib\b",                                                    # SAFETY_DECL
    r"\bhttpx\b",                                                     # SAFETY_DECL
    r"\bplaywright\b",                                                # SAFETY_DECL
    r"\bselenium\b",                                                  # SAFETY_DECL
    r"\bwebdriver\b",                                                 # SAFETY_DECL
    r"\bsocket\.(socket|create_connection)",                          # SAFETY_DECL
    r"\bsend_keys\b",                                                 # SAFETY_DECL
    r"\.fill\(",                                                       # SAFETY_DECL
    r"\.click\(",                                                      # SAFETY_DECL
    r"\.press\(",                                                      # SAFETY_DECL
    r"solve_captcha|bypass_captcha",                                   # SAFETY_DECL
    r"login_submit|submit_credentials|do_login",                       # SAFETY_DECL
]                                                                      # SAFETY_DECL

SAFETY_DECL_MARKER = "SAFETY_" + "DECL"


def scan_source_for_forbidden(src: str) -> list[dict[str, Any]]:
    """SAFETY_DECL 마커가 붙지 않은 모든 줄을 금지 패턴으로 스캔한다."""
    hits: list[dict[str, Any]] = []
    for lineno, line in enumerate(src.splitlines(), start=1):
        if SAFETY_DECL_MARKER in line:
            continue
        for pat in FORBIDDEN_SOURCE_PATTERNS:
            if re.search(pat, line):
                hits.append({"pattern": pat, "line": lineno, "text": line.strip()[:160]})
    return hits


def safety_selfcheck(source_override: str | None = None) -> dict[str, Any]:
    """
    자기 소스에 금지 API 사용이 없는지 정적 확인.
    source_override 는 이 검사기 자체의 변이 검사용(합성 소스에 금지 문자열을 심어 잡히는지 확인).
    """
    if source_override is not None:
        src = source_override
        target = "<synthetic_source_for_mutation_test>"
    else:
        target = os.path.abspath(__file__)
        try:
            with open(target, encoding="utf-8") as f:
                src = f.read()
        except Exception as e:  # pragma: no cover
            return {"status": "UNVERIFIED", "reason": str(e)}
    hits = scan_source_for_forbidden(src)
    return {
        "status": "PASS" if not hits else "FAIL",
        "scanned": target,
        "n_checked_patterns": len(FORBIDDEN_SOURCE_PATTERNS),
        "hits": hits,
        "network_access": "NONE",
        "credential_input_or_login_submission_path": "ABSENT",
        "captcha_path": "ABSENT",
        "transaction_activation_path": "ABSENT",
        "writes": "results/harness/lane_a/ 만",
    }


# =============================================================================
# 13. main
# =============================================================================

RD_DEFAULT = ("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/"
              "research/landing_accessibility/research_d")


def _sha256_file(p: str) -> str | None:
    try:
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def build_report() -> dict[str, Any]:
    suite = run_fixture_suite()
    mut = run_mutation_tests()
    counters = build_counters(_counter_probe_runs())
    ce1 = detect_ce_auth_timing_only(ce_fixtures()["ce1_records"])
    ce2 = [detect_ce_obstruction_input_positive(fx["run"]) for fx in ce_fixtures()["ce2_runs"]]
    safety = safety_selfcheck()

    all_pass = suite["n_fail"] == 0
    all_mut = mut["n_detected"] == mut["n_mutants"]
    reverted = mut["revert_check"]["identical_to_baseline"]

    if not (all_pass and all_mut and reverted and safety["status"] == "PASS"):
        verdict = "NOT_READY"
    elif AMBIGUOUS_DEFINITIONS:
        verdict = "READY_WITH_AMBIGUITY"
    else:
        verdict = "READY"

    return {
        "lane": "A",
        "title": "Auth timing / Obstruction 분석 하네스 + 반례 탐지기",
        "verdict": verdict,
        "generated_at_utc": _dt.datetime.now(_dt.UTC).isoformat(),
        "provenance": {
            "base_sha": "7448184a811f5d7d8772f21488bb75418fde3313",
            "branch": "claude-d/research-sandbox-v21",
            "ssot_root": "/home/sieg/projects-wsl/ProjectFinal/SSOTV3",
            "ssot_manifest_self_sha256": "1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a",
            "ssot_manifest_self_sha256_recomputed": _sha256_file(
                "/home/sieg/projects-wsl/ProjectFinal/SSOTV3/MANIFEST_v3.0.json"),
            "data_status": "NO_MAIN50_REAL_DATA — outcome-independent 준비. 모든 입력은 이 파일 안의 합성 fixture.",
        },
        "codebook_definitions_verbatim": CODEBOOK_VERBATIM,
        "implemented_variables": {
            "auth_gate_stage": {
                "domain": list(AUTH_STAGE_DOMAIN),
                "out_of_domain_sentinel": AUTH_STAGE_UNDETERMINED,
                "source_fields": ["fact_flow_step.auth_gate_detected", "fact_flow_step.action_token",
                                  "fact_flow_step.endpoint_signal_detected",
                                  "fact_flow_observation.experienced_flow_sequence"],
                "explicitly_excluded_inputs": list(AUTH_FORBIDDEN_INPUT_FIELDS),
                "exclusion_rule": "landing 에 generic login 이 존재한다는 이유만으로 AUTH_GATE 가 아니다 (00 §6, 03 §7, 10 Glossary). "
                                  "project_auth_inputs() 가 해당 필드를 구조적으로 제거하고, "
                                  "분류기가 그 필드에 닿으면 GUARD_BREACH defect 를 낸다.",
                "policy": asdict(AuthStagePolicy()),
            },
            "fact_task_obstruction": {
                "fields_read": ["interrupt_type", "overlay_coverage", "task_control_occlusion",
                                "dismiss_control_exists", "dismiss_control_visible",
                                "dismiss_control_accessible_name", "dismiss_required_for_task",
                                "dismiss_succeeded"],
                "run_grain_field_read": ["forced_dismissal_count"],
                "primary": "task_control_occlusion",
                "secondary_descriptive_only": "overlay_coverage",
                "dismissal_outcome_domain": [DISMISS_NO_TARGET, DISMISS_FAILED, DISMISS_SUCCEEDED,
                                             DISMISS_UNRECORDED, DISMISS_INCONSISTENT, DISMISS_UNKNOWN_EXISTENCE],
                "inherited_three_way_distinction": {
                    "no_target": DISMISS_NO_TARGET,
                    "attempted_but_failed": DISMISS_FAILED,
                    "succeeded": DISMISS_SUCCEEDED,
                    "inherited_from": "D legacy 코호트에서 확정된 '구분' 만 승계. 수치는 재사용하지 않는다(다른 코호트).",
                    "never_collapsed": True,
                },
                "geometry_only_derivation": derive_occlusion_from_geometry(),
            },
        },
        "three_axis_labeling": {
            "rule": "모든 카운터는 (1) 단위 (2) 모집단 (3) 원천 필드 세 축을 갖는다. "
                    "세 축이 없으면 ThreeAxisCounter 생성 자체가 ThreeAxisViolation 으로 실패하고, 비율도 만들 수 없다.",
            "enforced_by": "ThreeAxisCounter.__post_init__ / ThreeAxisCounter.rate()",
            "unit_domain": list(UNIT_DOMAIN),
            "counters": [c.to_dict() for c in counters],
            "counter_values_disclaimer": "위 카운터의 수치는 합성 fixture 를 통과시킨 실행 증거일 뿐 어떤 실측 주장도 아니다.",
        },
        "fixture_results": {
            "synthetic_only": True,
            "bidirectional_control": "각 stage/outcome 에 대해 성립 fixture 와 비성립 대조 fixture 를 함께 둔다 "
                                     "(A-F02↔A-F06, A-F01↔A-F07, O-F07↔O-F08/O-F09, CE1 탐지쌍↔미탐지쌍).",
            **suite,
            "mutation_testing": mut,
        },
        "counterexample_detectors": {
            "CE-1_AUTH_TIMING_ONLY": {
                "spec": "다른 축은 같은데 auth_gate_stage 만 다른 경우",
                "implemented": True,
                "other_axis_source": "CALLER_SUPPLIED other_axis_signature — Lane A 는 다른 축을 계산하지 않는다",
                "run_on_fixtures": ce1,
            },
            "CE-2_OBSTRUCTION_INPUT_FOR_EXPERIENCED_FLOW": {
                "spec": "modal 때문에 experienced flow 만 길어지는 경우 — obstruction 쪽 입력만 판정",
                "implemented": True,
                "scope_limit": "task_flow/experienced_flow 길이는 계산하지 않는다. Lane F 파일을 읽지 않았다.",
                "verdict_domain": ["OBSTRUCTION_SIDE_POSITIVE", "OBSTRUCTION_SIDE_NEGATIVE",
                                   "OBSTRUCTION_SIDE_REQUIRED_BUT_NOT_DISMISSED", "UNDETERMINED"],
                "run_on_fixtures": ce2,
            },
        },
        "missingness_encoding_detector": {
            "purpose": "같은 행 안에서 어떤 필드는 0.0, 어떤 필드는 None 인 상태를 탐지해 보고 (legacy 마트 실사례 재발 감시)",
            "flags": ["MIXED_NULL_ZERO_ENCODING", "MIXED_NULL_FALSE_ENCODING", "ALL_NUMERIC_NULL",
                      "ALL_NUMERIC_ZERO", "NULL_INTERRUPT_TYPE_WITH_NUMERIC_MAGNITUDE"],
            "numeric_fields_interrupt": list(NUMERIC_FIELDS_INTERRUPT),
            "numeric_fields_run": list(NUMERIC_FIELDS_RUN),
            "bool_fields": list(BOOL_FIELDS_INTERRUPT),
            "behavior": "탐지·보고만 한다. 어느 인코딩이 옳은지 정하지 않는다(그건 새 조작화다).",
        },
        "ambiguous_definitions": AMBIGUOUS_DEFINITIONS,
        "safety_selfcheck": safety,
        "limitation": [
            "MAIN50 실측 데이터가 없다. 모든 통과는 합성 fixture 에 대한 통과이며 실데이터 타당성 증거가 아니다.",
            "합성 fixture 는 이 파일의 저자가 정의를 읽고 만든 것이므로, 정의 자체를 오독했다면 fixture 도 같이 틀린다. "
            "변이 검사는 구현 오류를 잡지 실측 오독을 잡지 못한다.",
            "auth_gate_stage 는 upstream 이 fact_flow_step.auth_gate_detected 를 정확히 기록한다는 것을 전제한다. "
            "그 플래그 자체의 타당성은 Lane A 가 검증하지 않았다.",
            "task_control_occlusion / dismiss_required_for_task / dismiss_succeeded 는 pass-through 다. "
            "upstream 판정이 틀리면 Lane A 산출도 틀린다.",
            "CE-1 의 '다른 축' 은 호출자가 넘기는 signature 에 전적으로 의존한다. signature 구성이 부실하면 오탐이 난다.",
            "CE-2 는 flow 길이를 계산하지 않으므로 'experienced flow 만 길어졌다' 를 확정하지 못한다. 입력 조건만 판정한다.",
            "run→service_task_unit 집계를 하지 않았으므로 05 §1 의 분석단위로 바로 쓸 수 없다.",
        ],
        "not_implemented": [
            "task_flow_sequence / experienced_flow_sequence 길이·차이 계산 (Lane F 소관)",
            "activation_depth / flow_step_count / menu_dependency / nav_container_depth",
            "occlusion 구간화, 'blocking' 판정선, dismissal 필요 여부 임계 — 새 조작화 금지로 만들지 않았다",
            "composite score / weighted index / threshold / cut-off",
            "geometry 로부터의 occlusion 재도출 (명시적 REFUSED)",
            "interrupt → run occlusion 집계자",
            "run → service_task_unit auth stage 집계자",
            "REAL 접속·수집, production/mart/raw evidence 접근 또는 수정",
            "gold label / task gold 생성, holdout 접근, GO/NO-GO 판단",
            "git 조작",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lane A — auth timing / obstruction harness (synthetic fixtures only)")
    ap.add_argument("--rd", default=RD_DEFAULT)
    ap.add_argument("--print-only", action="store_true")
    args = ap.parse_args(argv)

    report = build_report()
    outdir = os.path.join(args.rd, "results", "harness", "lane_a")
    if not args.print_only:
        os.makedirs(outdir, exist_ok=True)
        p = os.path.join(outdir, "LANE_A_HARNESS.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        print(f"WROTE {p}")
    print(json.dumps({
        "verdict": report["verdict"],
        "fixtures": {k: report["fixture_results"][k] for k in ("n_total", "n_pass", "n_fail")},
        "mutants": {"n": report["fixture_results"]["mutation_testing"]["n_mutants"],
                    "detected": report["fixture_results"]["mutation_testing"]["n_detected"],
                    "reverted_ok": report["fixture_results"]["mutation_testing"]["revert_check"]["identical_to_baseline"]},
        "ambiguous": [a["id"] for a in report["ambiguous_definitions"]],
        "safety": report["safety_selfcheck"]["status"],
    }, ensure_ascii=False, indent=1))
    return 0 if report["verdict"] != "NOT_READY" else 1


if __name__ == "__main__":
    sys.exit(main())
