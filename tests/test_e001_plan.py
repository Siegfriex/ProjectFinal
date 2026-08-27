"""E001 배치 러너 — plan 로더가 Worker E의 `E000_PLAN.json` 형식과 호환되는가.

`tests/fixtures/e000_plan_snapshot.json`은 `claude-b/e000-plan` lane이 만든
`E000_PLAN.json`을 그대로 복사한 스냅샷이다(compatibility fixture) — 이
테스트는 실제 target의 `official_url`을 어디에도 열지 않는다. 파싱만 한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.plan import (  # noqa: E402
    PlanValidationError,
    load_plan,
    load_plan_dict,
    validate_no_real_navigation_fields_required,
)

SNAPSHOT = Path(__file__).resolve().parent / "fixtures" / "e000_plan_snapshot.json"


def test_load_e000_plan_snapshot_is_compatible():
    specs = load_plan(SNAPSHOT)
    assert len(specs) == 11
    ids = [s.target_id for s in specs]
    assert len(ids) == len(set(ids))
    daum = next(s for s in specs if s.canonical_service_key == "daum")
    assert daum.official_url == "https://m.daum.net/?nil_top=mobile"
    assert daum.interaction_archetype == "QUERY"
    assert daum.fixture_override is None  # 원본 plan에는 이 러너 전용 필드가 없다


def test_official_url_never_read_by_loader_itself():
    """로더 자체는 어떤 URL도 열지 않는다 — TargetSpec은 순수 데이터일 뿐이다."""
    specs = load_plan(SNAPSHOT)
    assert all(s.official_url.startswith("https://") for s in specs)
    # fixture_override로 새로 만든 인스턴스도 official_url을 그대로 보존한다(변조하지 않는다).
    fx = specs[0].with_fixture_override("simple_article.html")
    assert fx.official_url == specs[0].official_url
    assert fx.fixture_override == "simple_article.html"


def test_missing_required_field_rejected():
    with pytest.raises(PlanValidationError):
        load_plan_dict({"targets": [{"target_id": "x", "canonical_service_key": "x"}]})


def test_duplicate_target_id_rejected():
    row = {
        "target_id": "dup",
        "canonical_service_key": "svc",
        "official_url": "https://example.com",
        "interaction_archetype": "CONTENT_OPEN",
    }
    with pytest.raises(PlanValidationError):
        load_plan_dict({"targets": [row, dict(row)]})


def test_unknown_plan_kind_rejected():
    with pytest.raises(PlanValidationError):
        load_plan_dict({"plan_kind": "SOMETHING_ELSE", "targets": []})


def test_empty_targets_rejected():
    with pytest.raises(PlanValidationError):
        load_plan_dict({"targets": []})


def test_validate_no_real_navigation_fields_required():
    specs = load_plan(SNAPSHOT)
    with pytest.raises(PlanValidationError):
        validate_no_real_navigation_fields_required(specs)  # fixture_override 전부 없음

    fixed = [s.with_fixture_override("simple_article.html") for s in specs]
    validate_no_real_navigation_fields_required(fixed)  # 이제는 통과해야 한다
