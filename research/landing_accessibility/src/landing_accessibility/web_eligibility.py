"""P-B 웹 적격성(web eligibility) 판정 인프라.

**verdict 가 아니다.** 이 모듈은 "이 measurement entity 를 모바일웹에서 잴 수 있는가"만
분류한다. KWCAG PASS/FAIL, MPFED, 접근성 판정은 이 모듈의 관할이 아니고 만들지도 않는다
(REAL TARGET 방화벽 · `docs/v2/00_SSOT_v2.0.md` §10 모델 사용 원칙 1~2단계).

## 정본

- `docs/v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md` §1.3 `web_eligibility_status` (6값)
- 같은 문서 §1.4 `web_target_status` (5값) · §1.4.1 supersede 경로
- `docs/v2/01_DATA_SPEC_v2.0.md` §3 `dim_web_target`
- `docs/v2/02_COLLECTION_MEASUREMENT_SPEC_v2.0.md` §13 (app-only 등 실패류)

## v1(`06`) 어휘와의 관계 — 왜 값을 그대로 옮기지 않았는가

`agent/landing-exec@87a0464e8159d5526069d5e654e648b0dae506ca` (C013, **UNVERIFIED
checkpoint, 어떤 감사도 거치지 않음**) 의 `build_web_eligibility_and_url_review.py` 는
v1 문서 `06_PROJECT_CLAUDE_MD_v2.0.md`(현재는 `research/landing_accessibility/CLAUDE.md`
가 가리키는 v2 문서팩으로 **대체됨**) §2-1 의 7값 어휘로 판정했다.

    WEB_SERVICE / OFFICIAL_PRODUCT_PAGE / APP_ONLY / SYSTEM_APP /
    RETAIL_OFFLINE_ONLY / EXCLUDED_INDUSTRY_AXIS / UNRESOLVED

v2 SSOT 는 그 문서를 superseded 로 표시했고 `A2` §1.3 이 **다른** 6값 어휘를 정본으로
확정했다. 이 모듈은 v1 산출 라벨을 그대로 리라벨링(1:1 매핑)하지 않는다 — 두 어휘의
경계가 다르기 때문이다 (예: v1 은 `RETAIL_OFFLINE_ONLY` 를 독립 상태값으로 두지만 v2 는
그런 상태값이 없다. v1 은 `SYSTEM_APP` 을 독립값으로 두지만 v2 는 `EXCLUDED_APP_ONLY` 하나로
흡수한다). 값을 새로 판정해야 한다.

살려 쓰는 것은 **판정 원칙**이다 (C013 docstring 의 (a)(b)(c), 이 모듈의 규칙 EL-1~EL-4로
재구현):

    (a) URL 존재 자체가 ELIGIBLE_WEB 의 근거가 아니다 — 그 URL 에서 서비스 핵심 기능을
        브라우저로 쓸 수 있는지가 근거다.
    (b) EXCLUDED_APP_ONLY / EXCLUDED_NO_PUBLIC_WEB_LANDING 확정은 부재를 **실제 확인**
        했을 때만이다. `state/_researcher_priors/system_app_hypothesis.json` 같은
        연구자 사전판단은 그 자체로 판정 근거가 아니다 (아래 `PRIOR_HYPOTHESIS` 참고).
    (c) 확인 불가는 `UNDETERMINED_URL_EVIDENCE` 이고, 제외로 바꾸지 않는다.

리테일 브랜드의 "기업 소개 사이트 vs 소비자 거래 사이트" 랜딩 선택 판단은 v2 에도
여전히 유효한 실무 판단이지만, v2 에는 그것을 위한 별도 상태값이 없다. 그 사실은
`eligibility_basis` 자유 텍스트에 남기고 상태값 집합은 확장하지 않는다 (A2 규칙 S-3,
"모든 열거형은 닫힌 집합이다").

## 이 모듈이 하지 않는 것

- 실제 서비스에 네트워크로 접속하지 않는다 (그건 `scripts/probe_official_urls.py`).
- AI/VLM 을 호출하지 않는다 (`00 §10` cascade 1~2단계까지만 — 결정적 신호 추출).
- Frame 값을 관측 행이 직접 고쳐 쓰게 허용하지 않는다 (A2 규칙 W-1 · S-2 — supersede
  경로는 `evaluate_supersede()` 로 별도 제공한다).

## SHADOW / PREPARATORY — `PHASE_GATES.md` §4.5 REAL-TARGET FIREWALL

`docs/v2/PHASE_GATES.md` §4.5 (A0 결정, 2026-08-27, `agent/landing-v2-exec@684c792`):

> URL availability/eligibility probe는 measurement가 아니라 target-preparation으로
> 분리하며, 그 probe에서도 accessibility verdict를 생성하지 않는다.

이 모듈이 다루는 "적격성"은 그 **target-preparation** 범주다 — KWCAG verdict 도, MPFED 도
아니다. `determine_web_eligibility()` 는 `execution_mode` 를 요구하며
`landing_accessibility.shadow_provenance.require_execution_mode()` 로 검증한다.
P0 종료 전에는 `FIXTURE` / `SHADOW_DRY_RUN` 만 허용되고 `REAL_TARGET` 은 hard FAIL 이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlsplit

from landing_accessibility.shadow_provenance import require_execution_mode

# ── 06 §... 이 아니라 A2 §1.3 / §1.4 정본 어휘 ──────────────────────────────

WEB_ELIGIBILITY_STATUS: frozenset[str] = frozenset(
    {
        "NOT_ASSESSED",
        "EXCLUDED_INDUSTRY_AXIS",
        "ELIGIBLE_WEB",
        "EXCLUDED_APP_ONLY",
        "EXCLUDED_NO_PUBLIC_WEB_LANDING",
        "UNDETERMINED_URL_EVIDENCE",
    }
)

#: 주 분석(Axis A/B 측정) 대상이 되는 유일한 값. A2 §1.3.
ANALYSIS_ELIGIBLE = "ELIGIBLE_WEB"

WEB_TARGET_STATUS: frozenset[str] = frozenset(
    {"DRAFT", "PENDING_URL_REVIEW", "FROZEN", "EXCLUDED", "SUPERSEDED"}
)

#: A2 §1.4 "5값은 상호배타이며 DRAFT → PENDING_URL_REVIEW → {FROZEN, EXCLUDED} 단방향이다.
#: FROZEN 에서 벗어나는 유일한 경로는 SUPERSEDED"
_ALLOWED_TARGET_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"PENDING_URL_REVIEW"}),
    "PENDING_URL_REVIEW": frozenset({"FROZEN", "EXCLUDED"}),
    "FROZEN": frozenset({"SUPERSEDED"}),
    "EXCLUDED": frozenset(),
    "SUPERSEDED": frozenset(),
}

#: A2 §1.2 — 수집 시점 반증의 동반 컬럼 값. `measurement_status = NOT_ELIGIBLE_AT_COLLECTION`
#: 일 때에만 non-null.
MEASUREMENT_STATUS_DETAIL: frozenset[str] = frozenset(
    {"APP_ONLY_AT_COLLECTION", "NO_PUBLIC_WEB_LANDING_AT_COLLECTION"}
)

#: A2 §1.3 대응표 — 수집 시점 반증이 supersede 후행에서 어느 Frame 값이 되는가.
MEASUREMENT_DETAIL_TO_ELIGIBILITY: dict[str, str] = {
    "APP_ONLY_AT_COLLECTION": "EXCLUDED_APP_ONLY",
    "NO_PUBLIC_WEB_LANDING_AT_COLLECTION": "EXCLUDED_NO_PUBLIC_WEB_LANDING",
}


class WebEligibilityError(ValueError):
    """이 모듈의 스키마·전이 규칙 위반. 조용히 흡수하지 않고 실패시킨다 (A2 규칙 S-3)."""


# ── url_evidence 원소 — 자유서술이 아니라 근거 유형을 못박는다 ────────────────

#: url_evidence 각 원소의 근거 유형. `PRIOR_HYPOTHESIS` 는 단독으로 배제 판정을
#: 정당화하지 못한다 (규칙 EL-2) — 원칙 (b)의 기계적 강제.
EVIDENCE_TYPES: frozenset[str] = frozenset(
    {
        "HTTP_PROBE",  # scripts/probe_official_urls.py 관측 (status/redirect/title)
        "DOM_INSPECTION",  # 실제 접속 후 구조 확인 (앱설치 인터스티셜, 로그인 벽 등)
        "SOURCE_LABEL_MATCH",  # A1 원문 표기 ↔ 서비스명 대조
        "REGISTERED_DOMAIN_MATCH",  # PSL 등록도메인 비교 (registered_domain.py)
        "PRIOR_HYPOTHESIS",  # 연구자 사전판단 — 단독 사용 금지 (규칙 EL-2)
        "MANUAL_REVIEW_NOTE",  # 사람/리뷰어의 자유 서술 보충
    }
)

#: 배제(EXCLUDED_*) 판정에 대한 실제 확인으로 인정되는 근거 유형 (원칙 (b)).
_CONFIRMING_EVIDENCE_TYPES: frozenset[str] = frozenset(
    {"HTTP_PROBE", "DOM_INSPECTION", "REGISTERED_DOMAIN_MATCH"}
)


@dataclass(frozen=True)
class UrlEvidenceItem:
    """`dim_web_target.url_evidence` 배열의 원소 하나."""

    evidence_type: str
    detail: str
    observed_at: str
    source_ref: str | None = None

    def __post_init__(self) -> None:
        if self.evidence_type not in EVIDENCE_TYPES:
            raise WebEligibilityError(
                f"evidence_type={self.evidence_type!r} 은 닫힌 집합 밖이다. "
                f"허용값: {sorted(EVIDENCE_TYPES)}"
            )
        if not self.detail or not self.detail.strip():
            raise WebEligibilityError("detail 이 비어 있는 evidence 는 근거가 아니다")
        # ISO8601 최소 검증 — 형식이 아니라 파싱 가능성만 확인한다.
        try:
            datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise WebEligibilityError(
                f"observed_at={self.observed_at!r} 이 ISO8601 이 아니다"
            ) from exc

    def as_dict(self) -> dict[str, str | None]:
        return {
            "evidence_type": self.evidence_type,
            "detail": self.detail,
            "observed_at": self.observed_at,
            "source_ref": self.source_ref,
        }


@dataclass(frozen=True)
class WebEligibilityDetermination:
    """`service_master`/`dim_web_target` 에 쓸 한 행의 적격성 판정 결과.

    01_DATA_SPEC 은 `dim_web_target`에 `web_eligibility_status`만 두지만, C013 이 지적한
    `eligibility-basis-fields-narrower-than-06-still-carried` 결손(state.json open_p2)을
    v2 어휘로 다시 닫기 위해 근거 필드를 함께 싣는다. 필드 이름은 v1 그대로 두되
    (하류 마이그레이션 비용을 줄이기 위해) **값 도메인만 v2 어휘로 교체**한다.
    """

    web_eligibility_status: str
    eligibility_basis: str
    eligibility_confidence: float
    eligibility_reviewer: str
    eligibility_reviewed_at: str
    eligibility_needs_review: bool
    execution_mode: str
    evidence: tuple[UrlEvidenceItem, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        require_execution_mode(self.execution_mode)  # §4.5 — REAL_TARGET 은 여기서 hard FAIL
        if self.web_eligibility_status not in WEB_ELIGIBILITY_STATUS:
            raise WebEligibilityError(
                f"web_eligibility_status={self.web_eligibility_status!r} 은 A2 §1.3 의 "
                f"6값 밖이다: {sorted(WEB_ELIGIBILITY_STATUS)}"
            )
        if not 0.0 <= self.eligibility_confidence <= 1.0:
            raise WebEligibilityError(
                f"eligibility_confidence={self.eligibility_confidence!r} 은 [0,1] 밖이다"
            )
        if self.web_eligibility_status != "NOT_ASSESSED" and not self.evidence:
            raise WebEligibilityError(
                f"{self.web_eligibility_status} 판정에는 evidence 가 최소 1건 필요하다 "
                "(NOT_ASSESSED 만 근거 없이 허용된다)"
            )
        if not self.eligibility_basis or not self.eligibility_basis.strip():
            raise WebEligibilityError("eligibility_basis 없이 판정할 수 없다")

    def as_row(self) -> dict[str, object]:
        """`service_master`/`dim_web_target` 머티리얼라이제이션에 바로 쓸 딕셔너리."""
        return {
            "web_eligibility_status": self.web_eligibility_status,
            "eligibility_basis": self.eligibility_basis,
            "eligibility_confidence": self.eligibility_confidence,
            "eligibility_reviewer": self.eligibility_reviewer,
            "eligibility_reviewed_at": self.eligibility_reviewed_at,
            "eligibility_needs_review": self.eligibility_needs_review,
            "execution_mode": self.execution_mode,
            "url_evidence": [e.as_dict() for e in self.evidence],
        }


# ── 규칙 EL-1~EL-4 강제 ──────────────────────────────────────────────────────


def _has_confirming_evidence(evidence: tuple[UrlEvidenceItem, ...]) -> bool:
    return any(e.evidence_type in _CONFIRMING_EVIDENCE_TYPES for e in evidence)


def determine_web_eligibility(
    *,
    status: str,
    basis: str,
    evidence: list[UrlEvidenceItem],
    confidence: float,
    reviewer: str,
    reviewed_at: str | None = None,
    needs_review: bool = False,
    execution_mode: str = "SHADOW_DRY_RUN",
) -> WebEligibilityDetermination:
    """규칙 EL-1~EL-4 를 강제하며 판정 레코드를 만든다.

    규칙 EL-1 (근거 요구). `NOT_ASSESSED` 를 제외한 모든 값은 evidence >= 1 을 요구한다
    (dataclass `__post_init__` 이 강제, 여기서는 사전 실패로 빠르게 알린다).

    규칙 EL-2 (사전판단 단독 배제 금지, 원칙 (b)). `EXCLUDED_APP_ONLY` /
    `EXCLUDED_NO_PUBLIC_WEB_LANDING` 은 `PRIOR_HYPOTHESIS` 만으로 확정할 수 없다.
    `state/_researcher_priors/system_app_hypothesis.json` 같은 사전 가설은 조사의
    출발점일 수 있지만, 실제 확인(`HTTP_PROBE`/`DOM_INSPECTION`/`REGISTERED_DOMAIN_MATCH`)
    이 최소 1건 있어야 한다.

    규칙 EL-3 (URL 존재 ≠ 적격, 원칙 (a)). `ELIGIBLE_WEB` 은 `HTTP_PROBE` 로 접속 가능함을
    확인한 것만으로는 부족하다 — 그 URL 이 **이 서비스 자신의** 진입점이라는 근거
    (`SOURCE_LABEL_MATCH` 또는 `REGISTERED_DOMAIN_MATCH` 또는 `DOM_INSPECTION`)가 함께
    있어야 한다.

    규칙 EL-4 (확인 불가는 제외가 아니다, 원칙 (c)). 이 함수는 `UNDETERMINED_URL_EVIDENCE`
    호출을 막지 않는다 — 오히려 EL-2/EL-3 을 만족하지 못하면 이 값을 쓰라는 것이 이 모듈의
    의도다. 호출자가 그 대신 `EXCLUDED_*` 를 억지로 쓰면 EL-2/EL-3 이 막는다.
    """
    ev = tuple(evidence)

    if status in {
        "EXCLUDED_APP_ONLY",
        "EXCLUDED_NO_PUBLIC_WEB_LANDING",
    } and not _has_confirming_evidence(ev):
        raise WebEligibilityError(
            f"{status} 는 실제 확인 근거가 필요하다 (규칙 EL-2). "
            f"evidence_type 이 {sorted(_CONFIRMING_EVIDENCE_TYPES)} 중 하나가 최소 1건 있어야 "
            "한다 — PRIOR_HYPOTHESIS 만으로는 배제 판정을 내릴 수 없다."
        )

    if status == "ELIGIBLE_WEB":
        has_probe_ok = any(e.evidence_type == "HTTP_PROBE" for e in ev)
        has_identity = any(
            e.evidence_type in {"SOURCE_LABEL_MATCH", "REGISTERED_DOMAIN_MATCH", "DOM_INSPECTION"}
            for e in ev
        )
        if not (has_probe_ok and has_identity):
            raise WebEligibilityError(
                "ELIGIBLE_WEB 은 접속 가능 근거(HTTP_PROBE)와 서비스 동일성 근거"
                "(SOURCE_LABEL_MATCH/REGISTERED_DOMAIN_MATCH/DOM_INSPECTION)가 "
                "모두 있어야 한다 (규칙 EL-3 — URL 존재만으로 적격은 아니다)."
            )

    reviewed = reviewed_at or datetime.now(UTC).isoformat()
    return WebEligibilityDetermination(
        web_eligibility_status=status,
        eligibility_basis=basis,
        eligibility_confidence=confidence,
        eligibility_reviewer=reviewer,
        eligibility_reviewed_at=reviewed,
        eligibility_needs_review=needs_review,
        execution_mode=execution_mode,
        evidence=ev,
    )


# ── deterministic 신호 추출 (00 §10 cascade 1단계, AI 호출 없음) ────────────

#: 리다이렉트 종착지가 앱스토어면 강한 신호 — 그러나 그 자체로 EXCLUDED_APP_ONLY 를
#: 확정하지 않는다(원칙 (b)). `needs_review=True` 로 사람/상위 cascade 에 넘긴다.
_APP_STORE_HOST_MARKERS: tuple[str, ...] = (
    "play.google.com",
    "apps.apple.com",
    "itunes.apple.com",
)
_APP_STORE_SCHEMES: tuple[str, ...] = ("itms-apps", "market")


@dataclass(frozen=True)
class ProbeSignal:
    """`probe_official_urls.py` 의 관측 1건에서 뽑아낸 결정적 신호. 판정이 아니다."""

    reachable: bool
    terminates_at_app_store: bool
    final_registered_domain: str | None
    target_registered_domain: str | None
    same_registered_domain: bool
    http_status: int | None
    error: str | None


def deterministic_probe_signal(probe_record: dict[str, object]) -> ProbeSignal:
    """`state/url_review_probe.json` 의 `probes[i]` 형태를 결정적 신호로 축약한다.

    `probe_official_urls.py` 가 이미 계산한 `final_registered_domain` /
    `target_registered_domain` 을 그대로 읽는다 — PSL 판정을 여기서 다시 하지 않는다
    (`00 §10` "브라우저가 이미 아는 정보는 AI가 다시 추정하지 않는다"의 결정적 계층 판)
    """
    final_url = probe_record.get("final_url")
    status = probe_record.get("http_status")
    error = probe_record.get("error")

    terminates_at_store = False
    if isinstance(final_url, str) and final_url:
        parsed = urlsplit(final_url)
        terminates_at_store = parsed.scheme in _APP_STORE_SCHEMES or bool(
            parsed.hostname and any(marker in parsed.hostname for marker in _APP_STORE_HOST_MARKERS)
        )

    final_rd = probe_record.get("final_registered_domain")
    target_rd = probe_record.get("target_registered_domain")
    same_rd = bool(final_rd) and final_rd == target_rd

    reachable = isinstance(status, int) and 200 <= status < 400 and not error

    return ProbeSignal(
        reachable=bool(reachable),
        terminates_at_app_store=terminates_at_store,
        final_registered_domain=final_rd if isinstance(final_rd, str) else None,
        target_registered_domain=target_rd if isinstance(target_rd, str) else None,
        same_registered_domain=same_rd,
        http_status=status if isinstance(status, int) else None,
        error=error if isinstance(error, str) else None,
    )


def suggest_status_from_probe_signal(signal: ProbeSignal) -> tuple[str, bool]:
    """(제안 status, needs_review). **최종 판정이 아니다.**

    이 함수는 사람/상위 cascade가 검토할 출발점만 제안한다. `determine_web_eligibility()`
    를 우회해 이 반환값을 그대로 `web_eligibility_status` 에 쓰지 않는다 — 규칙 EL-2/EL-3
    이 요구하는 evidence 검증을 이 함수는 수행하지 않는다.
    """
    if signal.terminates_at_app_store:
        return "EXCLUDED_APP_ONLY", True
    if not signal.reachable:
        return "UNDETERMINED_URL_EVIDENCE", True
    # 접속은 되지만 동일 서비스인지, 웹앱 진입점인지는 결정적으로 판정할 수 없다.
    return "UNDETERMINED_URL_EVIDENCE", True


# ── web_target_status 전이 가드 (A2 §1.4) ───────────────────────────────────


def validate_target_status_transition(current: str, new: str) -> None:
    if current not in WEB_TARGET_STATUS:
        raise WebEligibilityError(f"current={current!r} 은 A2 §1.4 5값 밖이다")
    if new not in WEB_TARGET_STATUS:
        raise WebEligibilityError(f"new={new!r} 은 A2 §1.4 5값 밖이다")
    if new not in _ALLOWED_TARGET_STATUS_TRANSITIONS[current]:
        raise WebEligibilityError(
            f"{current} → {new} 전이는 A2 §1.4 단방향 제약 위반이다. "
            f"{current} 에서 허용되는 전이: {sorted(_ALLOWED_TARGET_STATUS_TRANSITIONS[current]) or '없음(terminal)'}"
        )


# ── 수집 시점 반증 → Frame supersede (A2 §1.4.1, 규칙 W-1~W-3) ─────────────


@dataclass(frozen=True)
class SupersedeResult:
    """A2 §1.4.1 3단계 전부를 한 번에 반환한다. 호출자가 부분만 쓰지 않게 한다."""

    observation_measurement_status: str
    observation_measurement_status_detail: str
    superseded_web_target_status: str  # 기존 FROZEN 행에 쓸 값 — 항상 "SUPERSEDED"
    new_web_target_status: str  # 새 행 — 항상 "EXCLUDED"
    new_web_eligibility_status: str


def evaluate_supersede(
    *,
    current_target_status: str,
    measurement_status_detail: str,
) -> SupersedeResult:
    """`ELIGIBLE_WEB`로 동결된 타겟이 수집 시점에 반증됐을 때의 3단계 전이를 계산한다.

    규칙 W-1 (Frame 값은 관측이 아니라 재판정으로 바뀐다). 이 함수는 **새 값을 계산만**
    하고 아무것도 직접 쓰지 않는다 — 기존 `FROZEN` 행을 in-place 로 고치는 것은 규칙 S-2
    위반이다. 호출자가 계산 결과로 새 행을 만들고 기존 행은 `SUPERSEDED`로만 갱신해야 한다.

    규칙 W-2 (배제 방향으로만). 이 함수는 `EXCLUDED_*` 로 가는 경로만 계산한다.
    """
    if current_target_status != "FROZEN":
        raise WebEligibilityError(
            f"supersede 는 FROZEN 행에서만 발생한다 (A2 §1.4). 현재={current_target_status!r}"
        )
    if measurement_status_detail not in MEASUREMENT_STATUS_DETAIL:
        raise WebEligibilityError(
            f"measurement_status_detail={measurement_status_detail!r} 은 A2 §1.2 2값 밖이다: "
            f"{sorted(MEASUREMENT_STATUS_DETAIL)}"
        )
    validate_target_status_transition("FROZEN", "SUPERSEDED")
    new_eligibility = MEASUREMENT_DETAIL_TO_ELIGIBILITY[measurement_status_detail]
    return SupersedeResult(
        observation_measurement_status="NOT_ELIGIBLE_AT_COLLECTION",
        observation_measurement_status_detail=measurement_status_detail,
        superseded_web_target_status="SUPERSEDED",
        new_web_target_status="EXCLUDED",
        new_web_eligibility_status=new_eligibility,
    )


# ── C013 salvage: 결정적 신뢰도·서비스 동일성 helper ─────────────────────────
#
# 아래 3개 함수는 `agent/landing-exec@87a0464` 의 `build_web_eligibility_and_url_review.py`
# `confidence_of()` / `brand_tokens()` / `title_identifies_brand()` 를 **로직만** 살려
# v2 계약(문자열 등급이 아니라 [0,1] float, evidence 스키마와의 정합)에 맞게 다시 쓴 것이다.
# 전건 salvage 판단 근거는 `state/_shadow_pb_prework/c013_salvage_ledger.json` 참고.


def deterministic_confidence_from_probe(probe_record: dict[str, object]) -> float:
    """관측 품질만으로 신뢰도를 유도한다. 손으로 올리거나 내릴 수 없다.

    C013 `confidence_of()` 의 LOW/MEDIUM/HIGH 3단 등급을 그대로 3개 float 값으로
    사상했다 — 등급 자체를 세분화하지 않는다(그건 이 함수가 아니라 사람/AI 리뷰의 몫).
    """
    error = probe_record.get("error")
    status = probe_record.get("http_status")
    if error or not isinstance(status, int):
        return 0.2  # LOW
    if 200 <= status < 400 and probe_record.get("page_title"):
        return 0.9  # HIGH — 접속 + 제목 확보
    if 200 <= status < 400 or status in (401, 403, 429):
        return 0.5  # MEDIUM — 접속은 됐으나 신원 확인 근거(제목)가 없다, 또는 차단 신호
    return 0.2  # LOW


def brand_match_tokens(service_name: str, canonical_service_key: str, url: str | None) -> list[str]:
    """제목이 브랜드를 확인해주는지 검사할 토큰. **기계적으로만** 만든다.

    입력은 A1 원문 표기(`service_name`), `canonical_service_key`, 확정 URL 의 등록도메인
    첫 라벨뿐이다. 손으로 별칭을 보태면 검사가 원하는 결과에 맞춰 휘어진다(C013 원문 경고
    그대로 유지).
    """
    tokens: set[str] = set()
    for part in service_name.replace("/", " ").split():
        if len(part) >= 2:
            tokens.add(part.lower())
    tokens.add(service_name.replace("/", "").replace(" ", "").lower())
    for part in canonical_service_key.split("_"):
        if len(part) >= 3:
            tokens.add(part)
    tokens.add(canonical_service_key.replace("_", ""))
    if url:
        try:
            from landing_accessibility.registered_domain import registered_domain

            domain = registered_domain(url)
        except Exception:
            domain = None
        if domain:
            head = domain.split(".")[0]
            tokens.add(head)
            tokens.add(head.replace("-", ""))
    return sorted(t for t in tokens if len(t) >= 2)


def title_identifies_brand(probe_record: dict[str, object], tokens: list[str]) -> bool | None:
    """페이지 제목에 브랜드 토큰이 있는가. 제목이 없으면 판정하지 않는다(`None`).

    `True` 가 나오면 `SOURCE_LABEL_MATCH` evidence 를 자동 생성할 근거가 된다 — 다만
    이 함수 자체는 evidence 를 만들지 않는다. 호출자가 `UrlEvidenceItem` 으로 감싸야 한다
    (`determine_web_eligibility()` 의 EL-3 은 evidence 객체를 요구하지, bool 을 받지 않는다).
    """
    title = probe_record.get("page_title")
    if not isinstance(title, str) or not title:
        return None
    flat = title.lower().replace(" ", "")
    lowered = title.lower()
    return any(t in lowered or t.replace(" ", "") in flat for t in tokens)


def probe_evidence_detail(probe_record: dict[str, object], url: str | None) -> str:
    """`UrlEvidenceItem(evidence_type="HTTP_PROBE").detail` 에 쓸 사람이 읽을 수 있는 요약.

    C013 `evidence_of()` 의 문구 조립 로직을 그대로 살렸다 — "확인한 근거" 를 사람이
    검증 가능한 문장으로 남기라는 원칙(원칙 (a)(b)의 실제 확인 요구)의 실행부다.
    """
    if url is None:
        return "확정할 URL이 없다."
    error = probe_record.get("error")
    if error:
        return f"{url} — 접속 실패: {error}"
    status = probe_record.get("http_status")
    parts = [f"{url} → HTTP {status}"]
    final_url = probe_record.get("final_url")
    if final_url and final_url != url:
        parts.append(f"최종 URL {final_url}")
    hops = probe_record.get("redirect_chain") or []
    if isinstance(hops, list) and hops:
        parts.append(f"리다이렉트 {len(hops)}회")
    title = probe_record.get("page_title")
    if title:
        parts.append(f"페이지 제목 '{title}'")
    else:
        parts.append("페이지 제목 미획득(봇 차단 또는 비HTML 응답)")
    final_rd = probe_record.get("final_registered_domain")
    if final_rd:
        parts.append(f"등록도메인(PSL) {final_rd}")
    return " · ".join(str(p) for p in parts)
