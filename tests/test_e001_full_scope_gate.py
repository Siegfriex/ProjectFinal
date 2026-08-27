"""E001 본수집 게이트 — `REAL_TARGET` + `ExecutionScope.E001_FULL`.

이 파일이 고정하는 것:

1. **닫힌다** — `E001_RELEASE.json` 이 없거나·status 가 RELEASED 가 아니거나·
   `promoted_main_sha` 가 비었거나·`e001_allowed` 가 false 면 **엔진 층과 배치 층
   양쪽에서** 차단된다. 여기가 뚫리면 무제한 REAL_TARGET 이 열린다.
2. **열린다** — 문서가 RELEASED 이고 target 이 E001_FULL allowlist 안일 때만.
3. allowlist 는 동결 계획(`E001_MASTER_PLAN.json`) 의 59 key 를 P-B 산출물과 조인해
   만들어지고, 계획 해시(`b48be3cb…`)가 재계산으로 대조된다.
4. 워커 4분할은 서로 겹치지 않고 누락도 없다 (합집합 59 / 교집합 공집합).

**이 파일의 어떤 테스트도 실제 서비스에 접속하지 않는다.**
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner import layer_firewall  # noqa: E402
from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.layer_firewall import (  # noqa: E402
    BatchRealTargetBlockedError,
    assert_batch_execution_mode_safe,
)
from landing_accessibility.e001_runner.plan import (  # noqa: E402
    TargetSpec,
    validate_real_target_scope_allowlist,
)
from landing_accessibility.engine import firewall  # noqa: E402
from landing_accessibility.engine.firewall import (  # noqa: E402
    E001_FROZEN_PLAN_HASH,
    E001_WORKER_IDS,
    AllowlistUnavailableError,
    ExecutionScope,
    ExecutionScopeBlockedError,
    ReleaseDocument,
    TargetNotAllowlistedError,
    assert_mode_allowed,
    assert_navigation_allowed,
    assert_real_target_scope_allowed,
    evaluate_execution_scope,
    load_e001_full_allowlist,
    load_e001_full_targets,
    load_scope_allowlist,
)

FIXTURES = RESEARCH / "fixtures"
E001_N = 59

RELEASED_E001: dict[str, Any] = {
    "status": "RELEASED",
    "e001_allowed": True,
    "real_target_allowed": True,
    "authority_refs": {"promoted_main_sha": "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d"},
}


def _doc(payload: dict[str, Any] | None, error: str | None = None) -> ReleaseDocument:
    return ReleaseDocument(
        ref="test-ref", path="test-path", data=payload, sha256="0" * 64, error=error
    )


@pytest.fixture(autouse=True)
def _clear_caches() -> Any:
    firewall.reset_release_cache()
    firewall.reset_allowlist_cache()
    yield
    firewall.reset_release_cache()
    firewall.reset_allowlist_cache()


def _inject(monkeypatch: pytest.MonkeyPatch, doc: ReleaseDocument) -> None:
    monkeypatch.setattr(firewall, "read_release_document", lambda **_kw: doc)


# ── 1. 릴리스 문서 fail-closed (엔진 층) ─────────────────────────────────────
def test_e001_blocked_when_release_document_is_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(None, error="git show 실패"))
    verdict = evaluate_execution_scope(ExecutionScope.E001_FULL)
    assert verdict.allowed is False
    with pytest.raises(ExecutionScopeBlockedError):
        assert_real_target_scope_allowed(ExecutionScope.E001_FULL)
    with pytest.raises(ExecutionScopeBlockedError):
        assert_mode_allowed("REAL_TARGET", scope=ExecutionScope.E001_FULL)


@pytest.mark.parametrize(
    "mutation",
    [
        {"status": "CANDIDATE_NOT_FROZEN"},
        {"status": None},
        {"status": "released"},
        {"authority_refs": {}},
        {"authority_refs": {"promoted_main_sha": ""}},
        {"authority_refs": "not-an-object"},
        {"e001_allowed": False},
        {"e001_allowed": None},
        {"e001_allowed": "true"},
        {"real_target_allowed": False},
    ],
)
def test_e001_blocked_when_a_release_condition_is_unmet(
    monkeypatch: pytest.MonkeyPatch, mutation: dict[str, Any]
) -> None:
    _inject(monkeypatch, _doc({**RELEASED_E001, **mutation}))
    verdict = evaluate_execution_scope(ExecutionScope.E001_FULL)
    assert verdict.allowed is False, verdict.reason
    with pytest.raises(ExecutionScopeBlockedError):
        assert_mode_allowed("REAL_TARGET", scope=ExecutionScope.E001_FULL)


def test_e001_allowed_only_when_the_document_is_released(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(RELEASED_E001))
    verdict = evaluate_execution_scope(ExecutionScope.E001_FULL)
    assert verdict.allowed is True
    assert verdict.promoted_main_sha == "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d"


def test_e001_reads_its_own_release_document_not_p0(monkeypatch: pytest.MonkeyPatch) -> None:
    """E000 과 **다른 파일**을 읽는다 — P0_RELEASE 하나로 E001 이 열리지 않는다."""
    seen: list[str] = []

    def spy(**kw: Any) -> ReleaseDocument:
        seen.append(str(kw.get("path")))
        return _doc(RELEASED_E001)

    monkeypatch.setattr(firewall, "read_release_document", spy)
    evaluate_execution_scope(ExecutionScope.E001_FULL)
    evaluate_execution_scope(ExecutionScope.E000_FAST)
    assert seen == [firewall.E001_RELEASE_PATH, firewall.P0_RELEASE_PATH]


# ── 2. 릴리스 문서 fail-closed (배치 층 — 독립) ──────────────────────────────
def test_batch_layer_blocks_e001_when_its_own_read_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """엔진 층이 통과시켜도 배치 층이 자기 힘으로 막는다."""
    _inject(monkeypatch, _doc(RELEASED_E001))
    monkeypatch.setattr(layer_firewall, "_release_document", lambda *_a, **_k: None)
    with pytest.raises(BatchRealTargetBlockedError):
        assert_batch_execution_mode_safe("REAL_TARGET", "E001_FULL")


@pytest.mark.parametrize(
    "payload",
    [
        {**RELEASED_E001, "status": "DRAFT"},
        {**RELEASED_E001, "e001_allowed": False},
        {**RELEASED_E001, "authority_refs": {}},
        {**RELEASED_E001, "real_target_allowed": False},
    ],
)
def test_batch_layer_blocks_e001_on_unmet_conditions(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]
) -> None:
    monkeypatch.setattr(layer_firewall, "_release_document", lambda *_a, **_k: payload)
    assert layer_firewall.batch_layer_real_target_released(None, "E001_FULL") is False
    with pytest.raises(BatchRealTargetBlockedError):
        assert_batch_execution_mode_safe("REAL_TARGET", "E001_FULL")


def test_batch_layer_uses_the_e001_document_for_e001(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def spy(_repo: Any = None, path: str = layer_firewall.BATCH_LAYER_RELEASE_PATH) -> Any:
        seen.append(path)
        return RELEASED_E001

    monkeypatch.setattr(layer_firewall, "_release_document", spy)
    assert layer_firewall.batch_layer_real_target_released(None, "E001_FULL") is True
    assert seen == [layer_firewall.BATCH_LAYER_E001_RELEASE_PATH]


def test_batch_layer_still_refuses_an_unknown_scope() -> None:
    with pytest.raises(BatchRealTargetBlockedError):
        assert_batch_execution_mode_safe("REAL_TARGET", "E999_EVERYTHING")


def test_batch_layer_refuses_e001_without_a_scope() -> None:
    with pytest.raises(BatchRealTargetBlockedError):
        assert_batch_execution_mode_safe("REAL_TARGET")


# ── 3. allowlist ────────────────────────────────────────────────────────────
def test_e001_allowlist_has_the_frozen_fifty_nine_targets() -> None:
    allowlist = load_scope_allowlist(ExecutionScope.E001_FULL)
    assert allowlist.scope == "E001_FULL"
    assert len(allowlist.target_ids) == E001_N
    assert len(allowlist.canonical_service_keys) == E001_N
    assert allowlist.plan_sha256 == E001_FROZEN_PLAN_HASH
    assert load_e001_full_allowlist() == allowlist


def test_e001_frozen_plan_hash_is_recomputable() -> None:
    chosen, data = firewall.load_e001_master_plan()
    assert chosen.is_file()
    recomputed = firewall.recompute_plan_hash(data, firewall.E001_FROZEN_PLAN_HASH_FIELD)
    assert recomputed == E001_FROZEN_PLAN_HASH


def test_a_tampered_frozen_plan_is_refused(tmp_path: Path) -> None:
    import json

    _chosen, data = firewall.load_e001_master_plan()
    data["frozen_collection_order"] = list(data["frozen_collection_order"])[:5]  # type: ignore[arg-type]
    forged = tmp_path / "E001_MASTER_PLAN.json"
    forged.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(AllowlistUnavailableError):
        load_e001_full_allowlist(forged)


def test_e001_target_outside_the_allowlist_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(RELEASED_E001))
    with pytest.raises(TargetNotAllowlistedError):
        assert_real_target_scope_allowed(ExecutionScope.E001_FULL, target_id="wtg_not_in_plan")
    with pytest.raises(TargetNotAllowlistedError):
        assert_real_target_scope_allowed(
            ExecutionScope.E001_FULL, url="https" + "://evil.example.com/"
        )
    with pytest.raises(TargetNotAllowlistedError):
        assert_navigation_allowed(
            "REAL_TARGET", "https" + "://evil.example.com/x", scope="E001_FULL"
        )


def test_e001_allowlisted_target_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(RELEASED_E001))
    row = load_e001_full_targets()[0]
    verdict = assert_real_target_scope_allowed(
        ExecutionScope.E001_FULL,
        target_id=row.target_id,
        url=row.official_url,
        canonical_service_key=row.canonical_service_key,
    )
    assert verdict.allowed is True
    assert (
        assert_navigation_allowed(
            "REAL_TARGET", row.official_url, scope="E001_FULL", target_id=row.target_id
        )
        == row.official_url
    )


def test_e000_and_e001_allowlists_do_not_bleed_into_each_other(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """한 scope 의 allowlist 가 다른 scope 를 열어 주지 않는다."""
    _inject(monkeypatch, _doc({**RELEASED_E001, "e000_allowed": True}))
    e000 = firewall.load_e000_fast_allowlist()
    e001 = load_e001_full_allowlist()
    stranger = next(iter(sorted(e001.target_ids - e000.target_ids)))
    with pytest.raises(TargetNotAllowlistedError):
        assert_real_target_scope_allowed(ExecutionScope.E000_FAST, target_id=stranger)
    e000_only = next(iter(sorted(e000.target_ids - e001.target_ids)), None)
    if e000_only is not None:
        with pytest.raises(TargetNotAllowlistedError):
            assert_real_target_scope_allowed(ExecutionScope.E001_FULL, target_id=e000_only)


# ── 4. 워커 분할 ────────────────────────────────────────────────────────────
def test_worker_partition_is_a_clean_cover_of_the_frozen_order() -> None:
    rows = load_e001_full_targets()
    assert len(rows) == E001_N
    buckets = {
        w: {r.canonical_service_key for r in rows if r.worker_id == w} for w in E001_WORKER_IDS
    }
    union: set[str] = set()
    for worker_id, bucket in buckets.items():
        assert bucket, worker_id
        assert union.isdisjoint(bucket), f"{worker_id} 가 다른 워커와 겹친다"
        union |= bucket
    assert len(union) == E001_N
    assert union == {r.canonical_service_key for r in rows}
    assert sorted(len(b) for b in buckets.values()) == [14, 15, 15, 15]


def test_worker_sublists_keep_the_frozen_order() -> None:
    """워커별 목록은 동결 순서의 부분수열이다 — 재정렬하지 않는다."""
    rows = load_e001_full_targets()
    order = [r.canonical_service_key for r in rows]
    for worker_id in E001_WORKER_IDS:
        sub = [r.canonical_service_key for r in rows if r.worker_id == worker_id]
        assert sub == [k for k in order if k in set(sub)]


def test_joined_rows_carry_real_navigable_targets() -> None:
    from urllib.parse import urlparse

    rows = load_e001_full_targets()
    for row in rows:
        assert urlparse(row.official_url).scheme in {"https", "http"}
        assert row.target_id.startswith("wtg_")
        assert row.interaction_archetype


# ── 5. 배치 경로 (실제 접속 없이 executor 주입) ──────────────────────────────
def _worker_plan(worker_id: str = "worker_01") -> list[TargetSpec]:
    return [
        TargetSpec(
            target_id=r.target_id,
            canonical_service_key=r.canonical_service_key,
            official_url=r.official_url,
            interaction_archetype=r.interaction_archetype,
        )
        for r in load_e001_full_targets()
        if r.worker_id == worker_id
    ]


def test_plan_level_validation_rejects_a_stranger(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(RELEASED_E001))
    plan = [
        *_worker_plan()[:1],
        TargetSpec(
            target_id="wtg_stranger",
            canonical_service_key="stranger",
            official_url="https" + "://stranger.example.com/",
            interaction_archetype="QUERY",
        ),
    ]
    with pytest.raises(TargetNotAllowlistedError):
        validate_real_target_scope_allowlist(plan, scope=ExecutionScope.E001_FULL)


def test_e001_batch_keeps_every_safety_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(RELEASED_E001))
    monkeypatch.setattr(layer_firewall, "batch_layer_real_target_released", lambda *_a: True)

    calls: list[str] = []

    def injected(target: TargetSpec) -> dict[str, Any]:
        calls.append(target.canonical_service_key)
        return {"measurement_status": "MEASURED", "endpoint_status": "REACHED"}

    plan = _worker_plan()[:5]
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=4)
    manifests = runner.run(
        plan,
        execution_mode="REAL_TARGET",
        execution_scope=ExecutionScope.E001_FULL,
        target_executor=injected,
    )
    assert calls == [s.canonical_service_key for s in plan]  # frozen 순서 유지
    assert len(manifests) == 2
    manifest = manifests[0].as_dict()
    assert manifest["execution_mode"] == "REAL_TARGET"
    assert manifest["provenance"]["execution_scope"] == "E001_FULL"
    assert manifest["provenance"]["real_target_measurement"] is True
    assert manifest["provenance"]["max_retries_per_target"] == 1
    assert runner.target_wall_clock_cap_s == 360.0
    chain = runner.ledger.verify_chain()
    assert chain["status"] == "OK", chain
    assert chain["entries"] == 2, chain


def test_e001_batch_refuses_a_non_allowlisted_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inject(monkeypatch, _doc(RELEASED_E001))
    monkeypatch.setattr(layer_firewall, "batch_layer_real_target_released", lambda *_a: True)

    def spy(_target: TargetSpec) -> dict[str, Any]:
        raise AssertionError("allowlist 밖 target 이 executor 까지 도달했다")

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES)
    with pytest.raises(TargetNotAllowlistedError):
        runner.run(
            [
                TargetSpec(
                    target_id="wtg_stranger",
                    canonical_service_key="stranger",
                    official_url="https" + "://stranger.example.com/",
                    interaction_archetype="QUERY",
                )
            ],
            execution_mode="REAL_TARGET",
            execution_scope=ExecutionScope.E001_FULL,
            target_executor=spy,
        )


def test_e001_batch_is_blocked_when_the_release_document_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """게이트가 닫혀 있으면 executor 는 단 한 번도 불리지 않는다."""
    _inject(monkeypatch, _doc(None, error="git show 실패"))
    monkeypatch.setattr(layer_firewall, "_release_document", lambda *_a, **_k: None)

    def spy(_target: TargetSpec) -> dict[str, Any]:
        raise AssertionError("게이트가 닫혔는데 executor 가 불렸다")

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES)
    with pytest.raises(BatchRealTargetBlockedError):
        runner.run(
            _worker_plan()[:1],
            execution_mode="REAL_TARGET",
            execution_scope=ExecutionScope.E001_FULL,
            target_executor=spy,
        )


# ── 6. 구동 스크립트 ────────────────────────────────────────────────────────
def test_runner_script_requires_a_known_worker() -> None:
    import subprocess

    proc = subprocess.run(
        [
            sys.executable,
            str(RESEARCH / "scripts" / "run_e001_real.py"),
            "--worker",
            "99",
            "--check-only",
        ],
        capture_output=True,
        cwd=REPO,
        timeout=120,
    )
    assert proc.returncode != 0
