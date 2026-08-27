"""`ExecutionScope.V2_DIAGNOSTIC` — 12-target REAL diagnostic pilot 게이트
(`D-R0-82`, `T-B-BLK-006` 시정).

## 배경

B가 `T-B-BLK-006`(P0)으로 찾은 것: `ExecutionScope`에 diagnostic pilot용 값이
없어서, 실행기가 `E001_FULL`로 열면 firewall이 12가 아니라 **59**를 허용한다.
A가 S1(새 `ExecutionScope` + 전용 allowlist 로더 + 전용 릴리스 문서)을 택했다 —
S2(실행기에서만 제한)를 기각한 이유는 "firewall의 존재 이유가 scope 강제를
실행기의 정확성에 의존하지 않게 하는 것"이기 때문이다(`D_R0_82_DIAGNOSTIC_SCOPE.md`).

## 이 파일이 고정하는 것 — 3방향 + 부재(4방향)

`D-R0-82` §4 요구 6이 A 결정으로 3방향이 됐고(`C-COMPLETION-001151.A`), B가
`T-B-BLK-007`에서 4번째(부재)를 추가로 요구했다:

1. manifest 의 12 target 은 허용된다.
2. manifest **밖** target(E001 59 중 나머지 47에서 표본)은 거부된다.
3. manifest 파일이 **바이트 단위로** 변조되면(의미상 무해한 공백/키 순서
   변경이어도) 거부된다 — 값을 검증하는 게 아니라 파일 해시를 검증한다.
4. manifest 파일이 **아예 없으면** 거부된다(`T-B-BLK-007` — 지금 integration
   트리(`288025ff`)·이 브랜치·모든 worker 의 base(`2281c85`) 어디에도 manifest
   가 git 이력에 없는, 실제로 일어나는 상황이다).

한 방향만 보면 "아무것도 허용하지 않는" 구현도 통과한다(`D-R0-65-3`·`D-R0-70-3`
과 같은 이유) — 그래서 네 방향을 전부 이 파일에서 증명한다.

## `T-B-BLK-007` — 이 파일이 실제 파일 위치에 의존하지 않는 이유

B가 발견: `git cat-file -e <sha>:.../DIAGNOSTIC_PILOT_MANIFEST.json` 이
integration(`288025ff`)·이 브랜치(`4ec538b5`)·worker base(`2281c853`) 어디서도
파일을 찾지 못한다 — manifest 는 `control/landing-orchestrator` 브랜치에만
커밋돼 있다. 로더의 기본 후보 경로(`DIAGNOSTIC_PILOT_MANIFEST_CANDIDATES`)가
로컬에서 그 파일을 찾는 것은 이 개발 환경에 `claude_a_control` 워크트리가
우연히 그 브랜치를 체크아웃해 두고 있기 때문일 뿐, git SHA 로 재현되는 사실이
아니다 — B 가 지적한 "부재와 빈 내용을 구분하지 못할 뻔했다"는 함정과 같은
성격(조회 방식이 답을 만드는 이 세션의 반복 패턴, `D_R0_82_DIAGNOSTIC_SCOPE.md`
§5)이 여기서도 재발할 수 있다.

그래서 **이 파일의 모든 테스트는 `path=` 로 명시적 파일을 로더에 넘긴다** —
기본 후보 경로 탐색(`load_v2_diagnostic_allowlist()` 인자 없이 호출)에 의존하는
테스트가 하나도 없다. 실제 manifest 원본 바이트를
`tests/fixtures/w1_diagnostic_pilot_manifest_v2.json`(이 커밋에 포함, sha256
`78f2e32a…` 로 자기 검증)로 고정해 두고 그것만 쓴다. 최종 경로가 `T-B-BLK-007`
의 S-a/S-b/S-c 중 무엇으로 정해지든 로더의 핵심 계약(경로에서 읽는다 → 파일
바이트 sha256 을 동결값과 대조한다 → 불일치·부재·읽기실패는 전부 거부한다)은
바뀌지 않는다 — 이 파일이 고정하는 것은 정확히 그 계약이다.

## manifest v2 (v1 폐기)

`DIAGNOSTIC_PILOT_MANIFEST_SHA256`은 v2 값(`78f2e32a…`)이다. v1(`4d3209ca…`)은
A가 `C-COMPLETION-001151.A`(decision=`F1_OPTION_II_REFREEZE`)로 폐기했다 — v1의
evidence-poor "degenerate 6" 집합이 labeler 산출에서 유래해 "gold label 미참조"
주장이 lineage 로 거짓이었다. v2는 evidence-poor를 관측 전용 3규칙으로만
재정의했다. CONTENT_OPEN 표본이 TikTok → Netflix(`wtg_13ed070478ef62c3`,
`https://www.netflix.com/kr/login`)로 바뀌었다.

**이 파일의 어떤 테스트도 실제 서비스에 접속하지 않는다.**
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine import firewall  # noqa: E402
from landing_accessibility.engine.firewall import (  # noqa: E402
    DIAGNOSTIC_PILOT_MANIFEST_SHA256,
    AllowlistUnavailableError,
    ExecutionScope,
    ExecutionScopeBlockedError,
    ReleaseDocument,
    TargetAllowlist,
    TargetNotAllowlistedError,
    assert_mode_allowed,
    assert_navigation_allowed,
    assert_real_target_scope_allowed,
    assert_target_allowlisted,
    evaluate_execution_scope,
    load_e001_full_targets,
    load_scope_allowlist,
    load_v2_diagnostic_allowlist,
)

#: 실제 v2 manifest 원본 바이트의 커밋된 사본. `T-B-BLK-007` 시정 —
#: `DIAGNOSTIC_PILOT_MANIFEST_CANDIDATES`(운영 경로 탐색)에 의존하지 않는다.
MANIFEST_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "w1_diagnostic_pilot_manifest_v2.json"
)

#: 표본 자체(`D-R0-82` 근거 메시지에 실린 12개 `web_target_id`, v2).
DIAGNOSTIC_MANIFEST_V2_IDS = frozenset(
    {
        "wtg_699a5e2f3f410152",  # 카카오톡 — COMMUNICATION_ENTRY
        "wtg_13ed070478ef62c3",  # Netflix — CONTENT_OPEN (v1 TikTok 대체)
        "wtg_95967b50683649f2",  # NH스마트뱅킹 — FINANCIAL_ACTION_ENTRY, POOR/R3
        "wtg_35319a420294ee17",  # 토스 — FINANCIAL_ACTION_ENTRY
        "wtg_ef06dc942ef3ccc9",  # 롯데하이마트 — ITEM_DETAIL, POOR/R2
        "wtg_ea031f85e857140e",  # 메가커피 — ITEM_DETAIL
        "wtg_517b8047eb5be716",  # 농협하나로마트 — ITEM_DETAIL
        "wtg_efda6e0b8457d63c",  # 네이버지도 — PLACE_LOOKUP
        "wtg_60d4d22e3809f780",  # 티맵 — PLACE_LOOKUP
        "wtg_ff3ee504792f6cfc",  # 삼성 인터넷 브라우저 — QUERY, POOR/R1
        "wtg_91b952863c62993d",  # 다음 — QUERY
        "wtg_190b4501e4415d5e",  # V3 Mobile Plus — UTILITY_ENTRY
    }
)

RELEASED_V2_DIAGNOSTIC: dict[str, Any] = {
    "status": "RELEASED",
    "v2_diagnostic_allowed": True,
    "real_target_allowed": True,
    "promoted_main_sha": "e45d18d0000000000000000000000000000000",
    "manifest_sha256": DIAGNOSTIC_PILOT_MANIFEST_SHA256,
}


def _doc(payload: dict[str, Any] | None, error: str | None = None) -> ReleaseDocument:
    return ReleaseDocument(
        ref="test-ref", path="test-path", data=payload, sha256="0" * 64, error=error
    )


def _inject(monkeypatch: pytest.MonkeyPatch, doc: ReleaseDocument) -> None:
    monkeypatch.setattr(firewall, "read_release_document", lambda **_kw: doc)


def _diag_allowlist() -> TargetAllowlist:
    """이 파일 전체가 쓰는 유일한 진입점 — 항상 커밋된 fixture 사본을 명시적으로
    넘긴다. 기본 후보 경로 탐색을 절대 타지 않는다(`T-B-BLK-007`)."""
    return load_v2_diagnostic_allowlist(MANIFEST_FIXTURE)


def _manifest_rows() -> list[dict[str, Any]]:
    return json.loads(MANIFEST_FIXTURE.read_text(encoding="utf-8"))["targets"]


@pytest.fixture(autouse=True)
def _clear_caches() -> Any:
    firewall.reset_release_cache()
    firewall.reset_allowlist_cache()
    yield
    firewall.reset_release_cache()
    firewall.reset_allowlist_cache()


# ══════════════════════════════════════════════════════════════════════════
# 0. fixture 자기검증 — 커밋된 사본이 동결값과 일치하는가
# ══════════════════════════════════════════════════════════════════════════
def test_manifest_fixture_matches_the_frozen_sha256() -> None:
    """이 fixture 파일 자체가 실수로(줄바꿈 정규화 등) 손상되면 아래 모든
    "허용" 테스트가 오히려 "거부"로 통과해버려 아무것도 증명하지 못하는 조용한
    실패가 된다 — 그 가능성을 이 테스트가 먼저 차단한다."""
    import hashlib

    digest = hashlib.sha256(MANIFEST_FIXTURE.read_bytes()).hexdigest()
    assert digest == DIAGNOSTIC_PILOT_MANIFEST_SHA256


# ══════════════════════════════════════════════════════════════════════════
# 1. allowlist — manifest 12 target 이 허용된다 (4방향 중 방향 1)
# ══════════════════════════════════════════════════════════════════════════
def test_v2_diagnostic_allowlist_has_exactly_the_frozen_twelve_targets() -> None:
    allowlist = _diag_allowlist()
    assert allowlist.scope == "V2_DIAGNOSTIC"
    assert allowlist.target_ids == DIAGNOSTIC_MANIFEST_V2_IDS
    assert len(allowlist.target_ids) == 12
    assert allowlist.plan_sha256 == DIAGNOSTIC_PILOT_MANIFEST_SHA256
    assert load_scope_allowlist(ExecutionScope.V2_DIAGNOSTIC, path=MANIFEST_FIXTURE) == allowlist


def test_v2_diagnostic_manifest_is_a_subset_of_the_frozen_e001_fifty_nine() -> None:
    """`D-R0-82` §7 — S1 에서는 부분집합 여부가 실행 조건이 아니다(allowlist 가
    manifest 자체이므로). 그래도 이 사실 자체는 이 세션에서 B 가 조회 방식
    오류로 "교집합 0" 이라고 잘못 산출했던 것과 같은 실수를 이 테스트가 반복하지
    않는다는 것을 보인다 — `target_id`(`web_target_id`) 형식으로 직접 비교한다.

    `load_e001_full_targets()`(E001 로더)는 이 문제(`T-B-BLK-007`)의 영향을
    받지 않는다 — `E001_MASTER_PLAN.json`은 실제로 이 워크트리 안에 있다."""
    e001_ids = {r.target_id for r in load_e001_full_targets()}
    diagnostic_ids = _diag_allowlist().target_ids
    assert diagnostic_ids <= e001_ids
    assert len(e001_ids - diagnostic_ids) == 47


@pytest.mark.parametrize("target_id", sorted(DIAGNOSTIC_MANIFEST_V2_IDS))
def test_each_manifest_target_passes_allowlist_membership(target_id: str) -> None:
    assert_target_allowlisted(
        ExecutionScope.V2_DIAGNOSTIC, target_id=target_id, allowlist=_diag_allowlist()
    )


def test_manifest_target_with_url_passes_full_scope_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release 문서까지 포함한 전체 경로(`assert_real_target_scope_allowed`) —
    manifest 안의 target 은 url 로도 통과한다."""
    _inject(monkeypatch, _doc(RELEASED_V2_DIAGNOSTIC))
    row = next(t for t in _manifest_rows() if t["web_target_id"] == "wtg_699a5e2f3f410152")
    verdict = assert_real_target_scope_allowed(
        ExecutionScope.V2_DIAGNOSTIC,
        target_id=row["web_target_id"],
        url=row["url"],
        allowlist=_diag_allowlist(),
    )
    assert verdict.allowed is True


# ══════════════════════════════════════════════════════════════════════════
# 2. allowlist — manifest 밖 target 은 거부된다 (4방향 중 방향 2)
# ══════════════════════════════════════════════════════════════════════════
def test_e001_target_outside_the_manifest_is_rejected() -> None:
    """E001 59 중 manifest 12 에 없는 47 에서 표본 하나를 뽑아 확인한다."""
    e001_ids = {r.target_id for r in load_e001_full_targets()}
    diagnostic_ids = _diag_allowlist().target_ids
    outside_candidates = sorted(e001_ids - diagnostic_ids)
    assert len(outside_candidates) == 47
    outside = outside_candidates[0]
    assert outside not in diagnostic_ids

    with pytest.raises(TargetNotAllowlistedError):
        assert_target_allowlisted(
            ExecutionScope.V2_DIAGNOSTIC, target_id=outside, allowlist=_diag_allowlist()
        )


def test_arbitrary_wtg_not_in_manifest_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(RELEASED_V2_DIAGNOSTIC))
    allowlist = _diag_allowlist()
    with pytest.raises(TargetNotAllowlistedError):
        assert_real_target_scope_allowed(
            ExecutionScope.V2_DIAGNOSTIC,
            target_id="wtg_not_in_manifest_at_all",
            allowlist=allowlist,
        )
    with pytest.raises(TargetNotAllowlistedError):
        assert_real_target_scope_allowed(
            ExecutionScope.V2_DIAGNOSTIC, url="https://evil.example.com/", allowlist=allowlist
        )
    with pytest.raises(TargetNotAllowlistedError):
        assert_navigation_allowed(
            "REAL_TARGET",
            "https://evil.example.com/x",
            scope="V2_DIAGNOSTIC",
            allowlist=allowlist,
        )


# ══════════════════════════════════════════════════════════════════════════
# 3. allowlist — manifest 파일 변조 시 거부된다 (4방향 중 방향 3)
# ══════════════════════════════════════════════════════════════════════════
def test_tampered_manifest_with_a_forged_target_is_refused(tmp_path: Path) -> None:
    """값을 바꿔 target 을 몰래 추가/치환해도 sha256 대조로 거부된다."""
    data = json.loads(MANIFEST_FIXTURE.read_text(encoding="utf-8"))
    data["targets"][0]["web_target_id"] = "wtg_forged0000000"
    forged = tmp_path / "DIAGNOSTIC_PILOT_MANIFEST.json"
    forged.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(AllowlistUnavailableError, match="sha256"):
        load_v2_diagnostic_allowlist(forged)


def test_tampered_manifest_with_only_whitespace_changed_is_still_refused(tmp_path: Path) -> None:
    """`D-R0-82` §4 요구 6 3항 — 값을 검증하는 게 아니라 **파일 해시**를
    검증한다. 의미상 무해한 변경(공백 하나 추가)도 거부돼야 한다."""
    raw = MANIFEST_FIXTURE.read_bytes()
    forged = tmp_path / "DIAGNOSTIC_PILOT_MANIFEST.json"
    forged.write_bytes(raw + b" ")
    with pytest.raises(AllowlistUnavailableError, match="sha256"):
        load_v2_diagnostic_allowlist(forged)


def test_tampered_manifest_with_reordered_keys_is_still_refused(tmp_path: Path) -> None:
    """키 순서만 바꿔도(값 집합은 동일) 원본 바이트와 달라지므로 거부된다 —
    `json.dumps` 재직렬화는 원본 바이트 순서를 보존하지 않는다."""
    data = json.loads(MANIFEST_FIXTURE.read_text(encoding="utf-8"))
    reordered = {k: data[k] for k in reversed(list(data.keys()))}
    forged = tmp_path / "DIAGNOSTIC_PILOT_MANIFEST.json"
    forged.write_text(json.dumps(reordered, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(AllowlistUnavailableError, match="sha256"):
        load_v2_diagnostic_allowlist(forged)


def test_untampered_manifest_copy_is_accepted(tmp_path: Path) -> None:
    """대조군 — 바이트 그대로 복사한 사본은(변조가 아니면) 통과한다. 위 세
    거부 테스트가 "아무 파일이나 거부하는" 구현이 아니라는 것을 보인다."""
    raw = MANIFEST_FIXTURE.read_bytes()
    copy = tmp_path / "DIAGNOSTIC_PILOT_MANIFEST.json"
    copy.write_bytes(raw)
    allowlist = load_v2_diagnostic_allowlist(copy)
    assert allowlist.target_ids == DIAGNOSTIC_MANIFEST_V2_IDS


# ══════════════════════════════════════════════════════════════════════════
# 3b. allowlist — manifest 파일이 아예 없으면 거부된다 (4방향 중 방향 4, 신규
#     `T-B-BLK-007` — 지금 실제로 일어날 수 있는 상황)
# ══════════════════════════════════════════════════════════════════════════
def test_missing_manifest_file_is_refused_not_silently_empty(tmp_path: Path) -> None:
    """`T-B-BLK-007` 요구 — 파일이 아예 없을 때도 거부돼야 한다. B 가 지적한
    함정과 정확히 반대 방향을 여기서 검증한다: `git show`로 부재를 빈 문자열로
    읽어 "내용이 같다"로 오판할 수 있다는 것이었다 — 이 로더는 `Path.is_file()`
    로 존재 자체를 먼저 확인하므로 그 함정에 빠지지 않는다는 것을 이 테스트가
    고정한다. 에러 메시지도 sha256 불일치("sha256")가 아니라 부재
    ("찾지 못했다")여야 한다 — 두 실패 모드를 혼동하면 운영에서 원인 파악이
    늦어진다."""
    missing = tmp_path / "DIAGNOSTIC_PILOT_MANIFEST.json"
    assert not missing.exists()
    with pytest.raises(AllowlistUnavailableError, match="찾지 못했다") as exc_info:
        load_v2_diagnostic_allowlist(missing)
    assert "sha256" not in str(exc_info.value), (
        "부재를 sha256 불일치로 잘못 보고했다 — 실패 모드가 섞였다"
    )


def test_missing_manifest_file_default_candidates_all_absent_is_also_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """기본 후보 경로 탐색 자체가 전부 실패하는 경우(`T-B-BLK-007`이 실제로
    묘사하는 상황 — integration/이 브랜치/worker base 어디에도 manifest 가
    없다)도 예외 없이 fail-closed 여야 한다. 후보 목록을 전부 존재하지 않는
    경로로 바꿔치기해 그 상황을 직접 재현한다."""
    fake_candidates = (tmp_path / "does_not_exist_1.json", tmp_path / "does_not_exist_2.json")
    monkeypatch.setattr(firewall, "DIAGNOSTIC_PILOT_MANIFEST_CANDIDATES", fake_candidates)
    firewall.reset_allowlist_cache()
    with pytest.raises(AllowlistUnavailableError, match="찾지 못했다"):
        load_v2_diagnostic_allowlist()


# ══════════════════════════════════════════════════════════════════════════
# 4. 릴리스 문서 — `V2_DIAGNOSTIC`은 자기 문서를 본다 (요구 4) + manifest 바인딩 (요구 5)
# ══════════════════════════════════════════════════════════════════════════
def test_v2_diagnostic_reads_its_own_release_document_not_e001(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`D-R0-82` §4 요구 4 — 시정 전에는 `E000_FAST`가 아니면 전부
    `E001_RELEASE.json`을 봤다. `V2_DIAGNOSTIC`이 자기 문서(`V2_DIAGNOSTIC_
    RELEASE.json`)를 보는지, `E001_FULL`은 여전히 `E001_RELEASE.json`을
    보는지(회귀 없음) 둘 다 확인한다."""
    seen: list[str] = []

    def spy(**kw: Any) -> ReleaseDocument:
        seen.append(str(kw.get("path")))
        return _doc(RELEASED_V2_DIAGNOSTIC)

    monkeypatch.setattr(firewall, "read_release_document", spy)
    evaluate_execution_scope(ExecutionScope.V2_DIAGNOSTIC)
    evaluate_execution_scope(ExecutionScope.E001_FULL)
    evaluate_execution_scope(ExecutionScope.E000_FAST)
    assert seen == [
        firewall.V2_DIAGNOSTIC_RELEASE_PATH,
        firewall.E001_RELEASE_PATH,
        firewall.P0_RELEASE_PATH,
    ]
    assert firewall.V2_DIAGNOSTIC_RELEASE_PATH != firewall.E001_RELEASE_PATH


def test_v2_diagnostic_blocked_when_release_document_is_unreadable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject(monkeypatch, _doc(None, error="git show 실패"))
    verdict = evaluate_execution_scope(ExecutionScope.V2_DIAGNOSTIC)
    assert verdict.allowed is False
    with pytest.raises(ExecutionScopeBlockedError):
        assert_real_target_scope_allowed(ExecutionScope.V2_DIAGNOSTIC)
    with pytest.raises(ExecutionScopeBlockedError):
        assert_mode_allowed("REAL_TARGET", scope=ExecutionScope.V2_DIAGNOSTIC)


@pytest.mark.parametrize(
    "mutation",
    [
        {"status": "DRAFT"},
        {"status": None},
        {"promoted_main_sha": ""},
        {"promoted_main_sha": None},
        {"v2_diagnostic_allowed": False},
        {"v2_diagnostic_allowed": None},
        {"v2_diagnostic_allowed": "true"},
        {"real_target_allowed": False},
        # 요구 5 — manifest sha256 바인딩이 깨지면 막는다.
        {"manifest_sha256": None},
        {"manifest_sha256": ""},
        {"manifest_sha256": "0" * 64},  # 다른(가짜) 해시
        {
            "manifest_sha256": "4d3209cad1a316caad117255934617097fdb96f77da67666feb42f71e2c86fc2"
        },  # 폐기된 v1
    ],
)
def test_v2_diagnostic_blocked_when_a_release_condition_is_unmet(
    monkeypatch: pytest.MonkeyPatch, mutation: dict[str, Any]
) -> None:
    _inject(monkeypatch, _doc({**RELEASED_V2_DIAGNOSTIC, **mutation}))
    verdict = evaluate_execution_scope(ExecutionScope.V2_DIAGNOSTIC)
    assert verdict.allowed is False, verdict.reason
    with pytest.raises(ExecutionScopeBlockedError):
        assert_mode_allowed("REAL_TARGET", scope=ExecutionScope.V2_DIAGNOSTIC)


def test_v2_diagnostic_allowed_when_released_and_manifest_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject(monkeypatch, _doc(RELEASED_V2_DIAGNOSTIC))
    verdict = evaluate_execution_scope(ExecutionScope.V2_DIAGNOSTIC)
    assert verdict.allowed is True
    assert verdict.promoted_main_sha == RELEASED_V2_DIAGNOSTIC["promoted_main_sha"]


def test_v2_diagnostic_missing_manifest_binding_does_not_regress_e000_or_e001(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`expected_manifest_sha256`이 `None`인 scope(E000_FAST·E001_FULL)는 새 검사
    분기를 타지 않는다 — `manifest_sha256` 필드가 아예 없어도 기존 판정(다른
    조건이 갖춰지면 허용)이 그대로 유지된다."""
    released_e001 = {
        "status": "RELEASED",
        "e001_allowed": True,
        "real_target_allowed": True,
        "authority_refs": {"promoted_main_sha": "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d"},
    }
    _inject(monkeypatch, _doc(released_e001))
    verdict = evaluate_execution_scope(ExecutionScope.E001_FULL)
    assert verdict.allowed is True, verdict.reason


# ══════════════════════════════════════════════════════════════════════════
# 5. `ExecutionScope` 는 여전히 알려진 값만 받는다 (닫힌 집합 회귀)
# ══════════════════════════════════════════════════════════════════════════
def test_execution_scope_is_a_closed_set_including_the_new_value() -> None:
    assert {s.value for s in ExecutionScope} == {"E000_FAST", "E001_FULL", "V2_DIAGNOSTIC"}


def test_unknown_scope_string_still_fails_closed() -> None:
    from landing_accessibility.engine.firewall import UnknownExecutionScopeError

    with pytest.raises(UnknownExecutionScopeError):
        evaluate_execution_scope("V2_DIAGNOSTIC_TYPO")


# ══════════════════════════════════════════════════════════════════════════
# 6. 후보 경로 자체 — `T-B-BLK-007`(A, S-b) 트리 안 경로만 쓴다
# ══════════════════════════════════════════════════════════════════════════
def test_primary_candidate_is_the_in_tree_path_a_specified() -> None:
    """A 재기재 원문 — "트리 안 경로 `research/landing_accessibility/control/
    pilot/DIAGNOSTIC_PILOT_MANIFEST.json`을 읽는다. 트리 밖 경로를 읽지
    않는다." 1순위 후보가 정확히 그 경로여야 한다 — sibling 워크트리(다른
    브랜치 체크아웃) 후보는 없어야 한다."""
    candidates = firewall.DIAGNOSTIC_PILOT_MANIFEST_CANDIDATES
    expected = (
        firewall._RESEARCH_ROOT / "control" / "pilot" / "DIAGNOSTIC_PILOT_MANIFEST.json",
        firewall._MAIN_REPO_ROOT
        / "research"
        / "landing_accessibility"
        / "control"
        / "pilot"
        / "DIAGNOSTIC_PILOT_MANIFEST.json",
    )
    # `_plan_candidates`(E001 CSV 들과 같은 규칙)가 만드는 두 후보 — 이 워크트리
    # 자신 → 메인 저장소. 둘 다 **이 브랜치가 실제로 체크아웃한 트리**를 가리킨다
    # (이 워크트리 자신의 경로에 `.agent_worktrees/claude_b_w1`이 들어가는 것은
    # 당연하다 — 그건 "다른 브랜치를 체크아웃한 트리"가 아니라 이 트리 자신이다).
    # `.agent_worktrees/claude_a_control`(다른 브랜치) 같은 **세 번째** 후보가
    # 없어야 한다는 것이 `T-B-BLK-007`이 실제로 요구하는 것이다.
    assert candidates == expected, (
        f"기대: {expected}\n실제: {candidates} — 트리 밖(다른 브랜치) 후보가 섞였을 수 있다"
    )
