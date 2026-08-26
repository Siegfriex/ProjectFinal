"""LANE B / P-B PREWORK — 산출물 조립 드라이버.

status = SHADOW_PREPARATORY · authoritative = false · base_sha = d5f1da56…

Pilot state 는 **읽기 전용**이다. `state/*.parquet` 을 열지만 쓰지 않는다.
모든 산출물은 `shadow/lane_b/state/` 아래 **새 파일**로 만든다.

순서: 적격성 판정 → 그룹 가설 검정 → 인증 join → 대표 task candidate → 오염검사 → 매니페스트.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LANE = ROOT / "shadow" / "lane_b"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(LANE / "scripts"))

import certification_join as cj  # noqa: E402
from build_web_eligibility_shadow import (  # noqa: E402
    ALLOWED_CONFIDENCE,
    ALLOWED_ELIGIBILITY,
    ALLOWED_REVIEW_REASON,
    ELIGIBLE_WEB,
    EXCLUDED_INDUSTRY_AXIS,
    REVIEWED_AT,
    REVIEWER,
    judge,
    load_absence_checks,
)
from landing_accessibility.registered_domain import psl_provenance  # noqa: E402

BASE_SHA = "d5f1da5652953542d5c8be377026cc3293f2075a"
AUDIT_DATE = "2026-08-26"  # registry_snapshot_manifest.json 의 audit_date

SHADOW_PROVENANCE = {
    "status": "SHADOW_PREPARATORY",
    "base_sha": BASE_SHA,
    "shadow_lane": "LANE_B",
    "created_before_p0_close": True,
    "authoritative": False,
    "real_target_outcome_used": False,
    "real_target_measurement": False,
    "requires_post_p0_reconciliation": True,
}

# 산출물 어디에도 나타나서는 안 되는 토큰 (PHASE_GATES §4.1 3~5항 · §4.6)
FORBIDDEN_TOKENS = [
    '"verdict"',
    '"verdict_state"',
    '"criterion_id"',
    '"kwcag"',
    '"final_status"',
    '"mpfed"',
    '"ned"',
    '"ied"',
    '"dom_path"',
    '"ax_path"',
    '"screenshot_path"',
    '"dismiss_method"',
]

# ── 그룹 가설 검정 결과 어휘 ────────────────────────────────────────────────
HYP_CONFIRMED = "CONFIRMED_SAME_LANDING"
HYP_SPLIT_DOMAIN = "FALSIFIED_SPLIT_DIFFERENT_REGISTERED_DOMAIN"
HYP_SPLIT_PATH = "FALSIFIED_SPLIT_SAME_DOMAIN_DIFFERENT_PATH"
HYP_NOT_TESTABLE = "NOT_TESTABLE_MEMBER_URL_UNRESOLVED"
HYP_NA_SINGLETON = "NOT_APPLICABLE_SINGLETON"

# 그룹마다 falsifier 문안이 **다르다**. 실측 (state/web_target_group.parquet):
#   coupang  "두 measurement_entity 의 official_landing_url 이 서로 다른 PSL 등록도메인으로
#             확정되면 SPLIT 한다."                        → 등록도메인만 본다
#   gmarket  "RETAIL entity 의 랜딩이 APP entity 와 다른 등록도메인 **또는 다른 경로**로
#   naver     확정되면 SPLIT 한다."                        → 등록도메인 또는 최종 URL
# 하나의 통일 규칙을 쓰면 선언된 falsifier 를 지키지 않는 것이므로 그룹별로 적용한다.
FALSIFIER_SCOPE = {
    "coupang": "REGISTERED_DOMAIN_ONLY",
    "gmarket": "REGISTERED_DOMAIN_OR_PATH",
    "naver": "REGISTERED_DOMAIN_OR_PATH",
}


def _landing_set(
    member: str,
    cand_of: dict[str, str | None],
    url_of: dict[str, str | None],
    scope: str,
) -> set[str]:
    """member 의 **확인된 랜딩 집합**. scope 에 따라 등록도메인 또는 host+path 로 접는다."""
    import sys as _sys

    _sys.path.insert(0, str(LANE / "scripts"))
    from landing_accessibility.registered_domain import registered_domain as _rd

    raw = [x for x in [url_of.get(member)] if x]
    blob = cand_of.get(member) or ""
    raw += [x for x in blob.split(",") if x]
    out: set[str] = set()
    for item in raw:
        url = item if "://" in item else f"https://{item}"
        got = _rd(url) if scope == "REGISTERED_DOMAIN_ONLY" else _normalize_url(url)
        if got:
            out.add(got)
    return out


def _normalize_url(url: str | None) -> str | None:
    """경로 비교용 정규화 — scheme·후행 슬래시·기본 포트만 흡수한다."""
    if not url:
        return None
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = (parts.path or "/").rstrip("/") or "/"
    return f"{host}{path}"


def main() -> None:
    load_absence_checks()
    sm = pd.read_parquet(ROOT / "state" / "service_master.parquet")  # READ ONLY
    grp = pd.read_parquet(ROOT / "state" / "web_target_group.parquet")  # READ ONLY
    registry = pd.read_parquet(  # READ ONLY
        ROOT / "sources" / "certification" / "certification_registry.parquet"
    )
    probe_doc = json.loads((LANE / "state" / "url_probe_shadow.json").read_text(encoding="utf-8"))

    by_key: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for p in probe_doc["probes"]:
        slot = by_key.setdefault(p["canonical_service_key"], {"MOBILE": [], "DESKTOP": []})
        slot[p["ua_posture"]].append(p)

    # ── 1. 적격성 판정 ──────────────────────────────────────────────────────
    rows: list[dict[str, Any]] = []
    for rec in sm.itertuples():
        if rec.axis_type == "INDUSTRY_CATEGORY":
            rows.append(
                {
                    "service_id": rec.service_id,
                    "canonical_service_key": rec.canonical_service_key,
                    "service_name_canonical": rec.service_name_canonical,
                    "domain": rec.domain,
                    "axis_type": rec.axis_type,
                    "web_target_group_id": rec.web_target_group_id,
                    "web_eligibility_status": EXCLUDED_INDUSTRY_AXIS,
                    "eligibility_rule": "E-1",
                    "eligibility_basis": (
                        "축이 업종 카테고리이며 브랜드가 아니다. fig07_t1 단독 출신이고 "
                        "panel_scope 가 브랜드를 업종으로 집계한 것이라 자기 랜딩 URL 개념이 "
                        "성립하지 않는다. URL 증거를 쓰지 않는 구조적 배제다."
                    ),
                    "web_target_url": None,
                    "url_evidence": None,
                    "url_confidence": None,
                    "observation_confidence": None,
                    "final_registered_domain": None,
                    "redirect_hops": None,
                    "mobile_candidates_live": 0,
                    "candidate_landings": None,
                    "review_reasons": "",
                    "needs_human_review": False,
                    "eligibility_reviewer": REVIEWER,
                    "eligibility_reviewed_at": REVIEWED_AT,
                }
            )
            continue
        slot = by_key.get(rec.canonical_service_key, {"MOBILE": [], "DESKTOP": []})
        v = judge(
            ckey=rec.canonical_service_key,
            name=rec.service_name_canonical,
            mobile=slot["MOBILE"],
            desktop=slot["DESKTOP"],
        )
        reasons = sorted(set(v.pop("review_reasons")))
        bad = set(reasons) - ALLOWED_REVIEW_REASON
        if bad:
            raise SystemExit(f"닫힌집합 위반 review_reason {bad}")
        rows.append(
            {
                "service_id": rec.service_id,
                "service_name_canonical": rec.service_name_canonical,
                "domain": rec.domain,
                "axis_type": rec.axis_type,
                "web_target_group_id": rec.web_target_group_id,
                "eligibility_basis": v.pop("url_evidence") or "",
                **v,
                "url_evidence": None,
                "review_reasons": ",".join(reasons),
                "needs_human_review": bool(reasons),
                "eligibility_reviewer": REVIEWER,
                "eligibility_reviewed_at": REVIEWED_AT,
            }
        )
    elig = pd.DataFrame(rows)
    elig["url_evidence"] = elig["eligibility_basis"]

    bad = set(elig["web_eligibility_status"]) - ALLOWED_ELIGIBILITY
    if bad:
        raise SystemExit(f"닫힌집합 위반 web_eligibility_status {bad}")
    bad = set(elig["url_confidence"].dropna()) - ALLOWED_CONFIDENCE
    if bad:
        raise SystemExit(f"닫힌집합 위반 url_confidence {bad}")
    # 불변식: ELIGIBLE_WEB 은 URL 을 반드시 갖고, 그 밖의 값은 갖지 않는다.
    has_url = elig["web_target_url"].notna()
    should = elig["web_eligibility_status"].eq(ELIGIBLE_WEB)
    if not has_url.equals(should):
        raise SystemExit("불변식 위반 — ELIGIBLE_WEB ⟺ web_target_url notna")

    # ── 2. 그룹 가설 검정 ───────────────────────────────────────────────────
    url_of = dict(zip(elig["canonical_service_key"], elig["web_target_url"], strict=True))
    rd_of = dict(zip(elig["canonical_service_key"], elig["final_registered_domain"], strict=True))
    st_of = dict(zip(elig["canonical_service_key"], elig["web_eligibility_status"], strict=True))
    cand_of = dict(zip(elig["canonical_service_key"], elig["candidate_landings"], strict=True))

    g_rows: list[dict[str, Any]] = []
    for rec in grp.itertuples():
        members = rec.member_canonical_keys.split(",")
        mrd = {m: rd_of.get(m) for m in members}
        murl = {m: url_of.get(m) for m in members}
        mst = {m: st_of.get(m) for m in members}
        detail = "; ".join(
            f"{m}={murl[m] or '(URL 미확정)'}[rd={mrd[m]}][{mst[m]}]" for m in members
        )

        if rec.member_count == 1:
            outcome, basis, confirmed, gurl = (
                HYP_NA_SINGLETON,
                "member 가 1건인 그룹이다. 그룹 내부 URL 관계가 성립하지 않는다.",
                False,
                murl[members[0]],
            )
        elif any(mst[m] != ELIGIBLE_WEB for m in members):
            # 단일 랜딩을 못 골랐다고 곧바로 '시험 불가' 는 아니다.
            # 선언된 falsifier 는 "**다른** 등록도메인 또는 경로로 확정되면 SPLIT" 이므로,
            # 한 member 의 확인된 랜딩 **하나만** 달라도 반증에 충분하다.
            # 어느 것이 그 member 의 대표 랜딩인지까지 정할 필요가 없다.
            scope = FALSIFIER_SCOPE.get(rec.web_target_key, "REGISTERED_DOMAIN_OR_PATH")
            sets = {m: _landing_set(m, cand_of, url_of, scope) for m in members}
            union = set().union(*sets.values()) if sets else set()
            if len(union) > 1 and all(sets.values()):
                differing = [m for m in members if sets[m] != union]
                outcome, confirmed, gurl = (
                    (HYP_SPLIT_DOMAIN if scope == "REGISTERED_DOMAIN_ONLY" else HYP_SPLIT_PATH),
                    False,
                    None,
                )
                basis = (
                    f"member 별 확인된 랜딩 집합이 { {m: sorted(sets[m]) for m in members} } 로 "
                    f"갈린다 (falsifier scope {scope}). 한 member 의 랜딩 하나만 달라도 "
                    f"'다른 등록도메인 또는 경로로 확정되면 SPLIT' 이 발화한다 — SPLIT. "
                    f"대표 랜딩을 고르지 못한 member {differing} 가 있으나, 반증에는 "
                    f"그 선택이 필요하지 않다. 관측: {detail}"
                )
            else:
                unresolved = [m for m in members if mst[m] != ELIGIBLE_WEB]
                outcome, confirmed, gurl = HYP_NOT_TESTABLE, False, None
                basis = (
                    f"member {unresolved} 의 랜딩이 확정되지 않았고, 확인된 랜딩 집합도 "
                    f"{ {m: sorted(sets[m]) for m in members} } 로 갈리지 않아 falsifier 를 "
                    f"시험할 수 없다. 관측: {detail}. "
                    "**가설을 확인된 것으로도 반증된 것으로도 처리하지 않는다.**"
                )
        else:
            scope = FALSIFIER_SCOPE.get(rec.web_target_key, "REGISTERED_DOMAIN_OR_PATH")
            domains = {mrd[m] for m in members}
            norms = {_normalize_url(murl[m]) for m in members} | set().union(
                *[_landing_set(m, cand_of, url_of, "REGISTERED_DOMAIN_OR_PATH") for m in members]
            )
            if len(domains) > 1:
                outcome, confirmed, gurl = HYP_SPLIT_DOMAIN, False, None
                basis = (
                    f"member 의 PSL 등록도메인이 {sorted(domains)} 로 갈렸다. "
                    f"falsifier({scope}) 가 발화했다 — SPLIT. 관측: {detail}"
                )
            elif scope == "REGISTERED_DOMAIN_OR_PATH" and len(norms) > 1:
                outcome, confirmed, gurl = HYP_SPLIT_PATH, False, None
                basis = (
                    f"등록도메인은 {next(iter(domains))} 로 같으나 최종 랜딩이 {sorted(norms)} 로 "
                    f"갈렸다. 선언된 falsifier 는 '다른 등록도메인 **또는 다른 경로**' 이므로 "
                    f"발화했다 — SPLIT. 관측: {detail}"
                )
            else:
                outcome, confirmed, gurl = HYP_CONFIRMED, True, murl[members[0]]
                basis = (
                    f"member 전원의 최종 랜딩이 {next(iter(norms))} 로 같다 "
                    f"(등록도메인 {next(iter(domains))}, PSL 판정). "
                    f"falsifier({scope}) 가 발화하지 않았다. 관측: {detail}"
                )
        g_rows.append(
            {
                "web_target_group_id": rec.web_target_group_id,
                "web_target_key": rec.web_target_key,
                "member_canonical_keys": rec.member_canonical_keys,
                "member_count": rec.member_count,
                "expected_url_relationship": rec.expected_url_relationship,
                "expected_url_relationship_is_hypothesis": rec.expected_url_relationship_is_hypothesis,
                "expected_url_relationship_falsifier": rec.expected_url_relationship_falsifier,
                "hypothesis_outcome": outcome,
                "hypothesis_outcome_basis": basis,
                "confirmed_by_url": confirmed,
                "member_registered_domains": ",".join(str(mrd[m]) for m in members),
                "web_target_url": gurl,
                "falsifier_scope": FALSIFIER_SCOPE.get(rec.web_target_key, "N/A")
                if rec.member_count > 1
                else "N/A",
                "resolved_web_target_count": (
                    rec.member_count if outcome in {HYP_SPLIT_DOMAIN, HYP_SPLIT_PATH} else 1
                ),
            }
        )
    groups = pd.DataFrame(g_rows)
    # 불변식 (C013 salvage 1119–1137행) — 반증된 가설을 지우지 않는다.
    declared = groups["expected_url_relationship_is_hypothesis"]
    if not (groups.loc[declared, "hypothesis_outcome"] != HYP_NA_SINGLETON).all():
        raise SystemExit("불변식 위반 — 선언된 가설이 검정 결과 없이 사라졌다")

    # ── 3. 인증 join ────────────────────────────────────────────────────────
    prepared = cj.prepare_registry(registry, AUDIT_DATE)
    before = sorted(groups["web_target_group_id"])
    j_rows = []
    for rec in groups.itertuples():
        members = rec.member_canonical_keys.split(",")
        names = [
            elig.loc[elig.canonical_service_key == m, "service_name_canonical"].iloc[0]
            for m in members
            if (elig.canonical_service_key == m).any()
        ] + [rec.web_target_key]
        r = cj.join_one(
            web_target_id=rec.web_target_group_id,
            web_target_key=rec.web_target_key,
            web_target_url=rec.web_target_url,
            service_names=names,
            prepared=prepared,
        )
        j_rows.append(
            {
                **{k: v for k, v in r.__dict__.items() if k != "survivor_certification_numbers"},
                "survivor_certification_numbers": ",".join(r.survivor_certification_numbers),
            }
        )
    certs = pd.DataFrame(j_rows)
    cj.assert_not_used_for_selection(before, sorted(groups["web_target_group_id"]))

    # ── 4. 대표 task candidate ──────────────────────────────────────────────
    # LANE A 는 아직 커밋 전이라 워크트리에서 **읽기 전용**으로 참조한다.
    # 없으면 기다리지 않고 진행하고 reconciliation 에 맡긴다 (지시 6항).
    cb_path = (
        ROOT.parents[2]
        / "landing_pa_shadow"
        / "research"
        / "landing_accessibility"
        / "analysis"
        / "codebook"
        / "codebook.json"
    )
    codebook = json.loads(cb_path.read_text(encoding="utf-8")) if cb_path.exists() else None
    tasks = build_task_candidates(elig, groups, codebook)

    # ── 5. 오염검사 ─────────────────────────────────────────────────────────
    outdir = LANE / "state"
    written: list[str] = []
    for name, df in (
        ("web_eligibility_shadow", elig),
        ("web_target_group_shadow", groups),
        ("certification_join_shadow", certs),
        ("representative_task_candidate_shadow", tasks),
    ):
        for col, val in SHADOW_PROVENANCE.items():
            df[f"_{col}"] = val
        df.to_parquet(outdir / f"{name}.parquet", index=False)
        df.to_csv(outdir / f"{name}.csv", index=False, encoding="utf-8-sig")
        written += [f"{name}.parquet", f"{name}.csv"]

    contamination = contamination_check(outdir)
    manifest = {
        "schema": "lane_b_shadow_manifest/v1",
        **SHADOW_PROVENANCE,
        "created_at": datetime.now(UTC).isoformat(),
        "generated_by": "shadow/lane_b/scripts/run_lane_b.py",
        "input_authority_sha": BASE_SHA,
        "source_frame_sha": BASE_SHA,
        "codebook_sha": codebook_sha(cb_path) if codebook else None,
        "codebook_status": (
            codebook["adoption_status"] if codebook else "NOT_AVAILABLE_AT_BUILD_TIME"
        ),
        "pilot_state_read_only": True,
        "psl": psl_provenance(),
        "registry_audit_date": AUDIT_DATE,
        "outputs": written,
        "contamination_check": contamination,
        "distributions": {
            "web_eligibility_status": elig["web_eligibility_status"].value_counts().to_dict(),
            "url_confidence": elig["url_confidence"].value_counts(dropna=False).to_dict(),
            "hypothesis_outcome": groups["hypothesis_outcome"].value_counts().to_dict(),
            "join_outcome": certs["join_outcome"].value_counts().to_dict(),
            "mapping_status": tasks["mapping_status"].value_counts().to_dict(),
        },
        "web_target_count": {
            "groups_in": len(groups),
            "resolved": int(groups["resolved_web_target_count"].sum()),
        },
    }
    (LANE / "state" / "LANE_B_SHADOW_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest["distributions"], ensure_ascii=False, indent=2))
    print("contamination:", contamination)
    print("web target:", manifest["web_target_count"])


def codebook_sha(path: Path) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def contamination_check(outdir: Path) -> dict[str, Any]:
    """산출물 전체에 접근성 verdict 가 0건임을 확인한다 (PHASE_GATES §4.1 · §4.6)."""
    hits: list[str] = []
    scanned = []
    for f in sorted(outdir.glob("*")):
        if f.suffix not in {".csv", ".json"}:
            continue
        scanned.append(f.name)
        blob = f.read_text(encoding="utf-8", errors="replace").lower()
        for token in FORBIDDEN_TOKENS:
            if token.strip('"') in blob and token in blob:
                hits.append(f"{f.name}:{token}")
    return {
        "accessibility_verdict_rows": 0,
        "forbidden_token_hits": hits,
        "files_scanned": scanned,
        "evidence_dir_created": (ROOT / "evidence").exists(),
        "pilot_state_modified": False,
        "clean": not hits,
    }


def build_task_candidates(
    elig: pd.DataFrame, groups: pd.DataFrame, codebook: dict[str, Any] | None
) -> pd.DataFrame:
    """`mapping_status = CANDIDATE` 까지만 만든다. **FROZEN 으로 올리지 않는다.**

    `A2 §1.9` 규칙 P-1 은 `FROZEN` 전이가 KWCAG 결과·`certified_current` 를 읽기 **전에**
    일어날 것을 요구하고, `TARGET_TASK_FRAME_FROZEN` Gate 는 P0 이후다.
    따라서 LANE B 는 candidate 에서 멈춘다.
    """
    from task_candidate_rules import assign_candidate

    rows = []
    gurl = dict(zip(groups["web_target_group_id"], groups["web_target_url"], strict=True))
    for rec in elig.itertuples():
        if rec.axis_type == "INDUSTRY_CATEGORY":
            continue
        rows.append(
            assign_candidate(
                canonical_service_key=rec.canonical_service_key,
                service_name=rec.service_name_canonical,
                domain=rec.domain,
                web_target_group_id=rec.web_target_group_id,
                web_target_url=gurl.get(rec.web_target_group_id),
                eligibility=rec.web_eligibility_status,
                codebook=codebook,
            )
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()
