"""P-B Outcome Contamination Guard — 코드 레벨 allowlist 로 강제한다.

## 배경

`docs/v2/PHASE_GATES.md` §4.6 "교차오염 금지":

> P-B task selection은 certification outcome·accessibility 결과로 task를 고르지 않는다

와 오케스트레이터 지시서의 REAL TARGET 방화벽:

> accessibility 결과를 근거로 target/task를 선택하지 마라(순서가 거꾸로면 안 된다 —
> eligibility가 먼저, verdict 개입 금지).

이 두 문장은 **순서**를 요구한다. 이 모듈은 그 순서를 관례가 아니라 코드로 강제한다 —
target/task 선택에 쓰이는 입력 payload 를 스캔해서 금지된 개념이 섞여 있으면 예외를 던진다.

## 허용/금지 목록

오케스트레이터 지시서가 준 범주를 그대로 옮긴다. 새 범주를 이 모듈이 임의로 추가하지 않는다.

허용 입력: source frame, official service description, URL evidence, web availability,
service identity, source membership.

금지 입력: KWCAG, popup, MPFED, accessibility verdict, certified_current outcome(선택용),
real-target evidence.

## 이 모듈이 하지 않는 것

- 이 모듈은 P-B 의 다른 모듈(`web_eligibility.py` 등)을 자동으로 감싸지 않는다 — 그
  모듈들은 애초에 금지 개념을 다루지 않는다(별도 원칙으로 이미 지켜진다). 이 guard 는
  **P-A/P-B 의 target/task selection 함수**(현재 이 lane 의 범위 밖, `03_CRISP_DM` M0)가
  나중에 그 입력을 검증할 때 쓸 재사용 가능한 1차 방어선이다.
- 의미론적 판단을 하지 않는다 — 키 이름/문자열 패턴 매칭이다. 이름을 바꿔 우회하는
  것까지 막지는 못한다. 그래서 두 번째 방어선(설계 원칙: 애초에 그 데이터를 이 함수의
  스코프에 들이지 않는다)이 여전히 1차 방어다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

#: §4.6 · REAL TARGET 방화벽 — 오케스트레이터 지시서가 준 허용 범주(개념 수준).
ALLOWED_INPUT_CATEGORIES: frozenset[str] = frozenset(
    {
        "source_frame",
        "official_service_description",
        "url_evidence",
        "web_availability",
        "service_identity",
        "source_membership",
    }
)

#: 위 범주에 실제로 대응하는 필드명 패턴(소문자, 부분일치). 이 목록에 없는 키가
#: 나와도 실패시키지 않는다 — allowlist 는 "이것만 허용" 이 아니라 "이 필드는
#: 안전하다고 표시됐다" 는 화이트리스트다. **금지 목록이 우선한다** (아래 참고).
_ALLOWED_FIELD_PATTERNS: tuple[str, ...] = (
    "source_row",
    "source_frame",
    "panel_id",
    "measurement_entity",
    "canonical_service_key",
    "service_name",
    "service_description",
    "official_landing_url",
    "final_url",
    "registered_domain",
    "redirect_chain",
    "http_status",
    "page_title",
    "content_language",
    "url_evidence",
    "url_confidence",
    "web_eligibility_status",
    "web_target_status",
    "web_target_id",
    "eligibility_basis",
    "eligibility_reviewer",
    "eligibility_confidence",
    "source_membership",
    "alias",
    "domain",
    "axis_type",
)

#: 금지 개념 → 필드명/값에서 찾을 정규식 패턴(대소문자 무시). 오케스트레이터 지시서의
#: 금지 목록을 그대로 옮겼다. `certified_current` 는 **필드 자체가 금지가 아니다**
#: (certification_join.py 의 정당한 출력이다) — 금지는 그것을 **선택 입력으로 쓰는 것**이므로
#: 아래 `FORBIDDEN_SELECTION_KEYS` 에서 문맥 있는 별도 키로만 잡는다.
_FORBIDDEN_PATTERNS: dict[str, re.Pattern[str]] = {
    "KWCAG": re.compile(r"kwcag|criterion_result|verdict_state", re.IGNORECASE),
    "POPUP": re.compile(r"popup|modal|interrupt_element|overlay_coverage", re.IGNORECASE),
    "MPFED": re.compile(r"\bmpfed\b|\bned\b|\bied\b|excess_?depth", re.IGNORECASE),
    "ACCESSIBILITY_VERDICT": re.compile(
        r"accessibility_verdict|final_status.*criterion|pass_count|fail_count|"
        r"undetermined_count",
        re.IGNORECASE,
    ),
    "REAL_TARGET_EVIDENCE": re.compile(
        r"screenshot|dom_path|ax_path|probe_path|manifest_path|evidence_run_id",
        re.IGNORECASE,
    ),
}

#: `certified_current` 를 target/task **selection** 입력으로 쓰는 것만 금지한다
#: (infra로서의 존재 자체는 허용 — Axis C join 준비는 오케스트레이터가 명시 허용했다).
FORBIDDEN_SELECTION_KEYS: frozenset[str] = frozenset(
    {"certified_current", "certification_number", "cert_valid_candidate"}
)


class OutcomeContaminationError(RuntimeError):
    """target/task selection 입력에 금지된 개념이 섞여 들어왔다."""


@dataclass(frozen=True)
class ContaminationFinding:
    key_path: str
    category: str
    matched_text: str


def _walk(payload: Any, path: str = "$") -> list[tuple[str, str]]:
    """(key_path, stringified_key_or_value) 쌍을 재귀적으로 수집한다."""
    out: list[tuple[str, str]] = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            key_str = str(k)
            out.append((f"{path}.{key_str}", key_str))
            out.extend(_walk(v, f"{path}.{key_str}"))
    elif isinstance(payload, (list, tuple)):
        for i, v in enumerate(payload):
            out.extend(_walk(v, f"{path}[{i}]"))
    else:
        out.append((path, str(payload)))
    return out


def find_contamination(
    payload: dict[str, Any],
    *,
    selection_context: bool = True,
) -> list[ContaminationFinding]:
    """`payload` 를 재귀 스캔해 금지 개념이 있으면 전부 반환한다 (빈 리스트 = 깨끗함).

    `selection_context=True` (기본값) 일 때만 `FORBIDDEN_SELECTION_KEYS` 도 검사한다 —
    이 값들이 **target/task selection 입력**으로 쓰이는 맥락에서만 금지이기 때문이다.
    certification_join.py 의 출력 자체를 스캔할 때는 `selection_context=False` 로 호출한다.
    """
    findings: list[ContaminationFinding] = []
    for key_path, text in _walk(payload):
        for category, pattern in _FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                findings.append(ContaminationFinding(key_path, category, text))
        if selection_context:
            leaf_key = key_path.rsplit(".", 1)[-1].split("[")[0]
            if leaf_key in FORBIDDEN_SELECTION_KEYS:
                findings.append(
                    ContaminationFinding(key_path, "CERTIFIED_CURRENT_FOR_SELECTION", leaf_key)
                )
    return findings


def assert_selection_input_clean(payload: dict[str, Any], *, context: str) -> None:
    """target/task selection 함수의 입력 payload 를 검증한다. 오염이 있으면 즉시 실패한다.

    이 함수를 통과했다는 것이 "이 payload 가 안전하다"는 적극적 증명은 아니다
    (패턴 매칭의 한계, 모듈 docstring 참고). 다만 흔한 실수 — 접근성 산출물을 그대로
    selection 함수에 넘기는 것 — 는 확실히 잡는다.
    """
    findings = find_contamination(payload, selection_context=True)
    if findings:
        detail = "; ".join(
            f"{f.key_path} ({f.category}: {f.matched_text!r})" for f in findings[:10]
        )
        raise OutcomeContaminationError(
            f"[{context}] target/task selection 입력에 금지된 개념이 있다 (§4.6 교차오염 금지): "
            f"{detail}"
        )
