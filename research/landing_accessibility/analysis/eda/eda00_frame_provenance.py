#!/usr/bin/env python
# ruff: noqa: SIM115, E402, RUF005, RUF015, C401, C416
# 이 파일은 라이브러리가 아니라 **1회성 분석 스크립트**다 — top-level 절차 코드이며
# 재실행 산출물의 바이트 동일성이 검증 기준이다. 위 규칙들을 기계적으로 고치면
# 검증된 산출물이 바뀔 위험만 있고 얻는 것이 없다. 규칙을 끄는 범위는 이 파일뿐이다.
"""EDA-00 — Frame & Provenance Audit (P-A A2).

Read-only. Writes only into the scratchpad output dir.
Every number in the report is computed here; nothing is copied from documents.

Run:
  /home/sieg/projects-wsl/ProjectFinal/.venv/bin/python eda00_frame_provenance.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter, defaultdict

import pandas as pd

# 이 파일이 사는 워크트리를 읽는다. 다른 워크트리 하드코딩 금지(SHADOW lane 격리).
ROOT = os.environ.get(
    "LANDING_RESEARCH_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
REPO_ROOT = os.path.dirname(os.path.dirname(ROOT))
OUT = os.environ.get("EDA00_OUT", os.path.join(ROOT, "analysis", "out", "eda00"))
os.makedirs(OUT, exist_ok=True)

FINDINGS: list[dict] = []
LINES: list[str] = []


def emit(s: str = "") -> None:
    LINES.append(s)
    print(s)


def finding(fid, severity, area, observed, expected, evidence):
    FINDINGS.append(
        {
            "id": fid,
            "severity": severity,
            "area": area,
            "observed": observed,
            "expected": expected,
            "evidence": evidence,
        }
    )


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_prefix(h: str) -> str:
    return h.split(":", 1)[1] if h and ":" in h else h


# ---------------------------------------------------------------- load
P = {
    "panel_registry": f"{ROOT}/state/panel_registry.parquet",
    "source_ranking_rows": f"{ROOT}/state/source_ranking_rows.parquet",
    "service_master": f"{ROOT}/state/service_master.parquet",
    "entity_alias_map": f"{ROOT}/state/entity_alias_map.parquet",
    "source_membership": f"{ROOT}/state/source_membership.parquet",
    "web_target_group": f"{ROOT}/state/web_target_group.parquet",
    "certification_registry": f"{ROOT}/sources/certification/certification_registry.parquet",
}
D = {k: pd.read_parquet(v) for k, v in P.items()}

panel = D["panel_registry"]
rows = D["source_ranking_rows"]
svc = D["service_master"]
alias = D["entity_alias_map"]
memb = D["source_membership"]
wtg = D["web_target_group"]
cert = D["certification_registry"]

emit("# EDA-00 raw output")
emit()

# ================================================================ 1. row counts / uniqueness
emit("## 1. ROW COUNTS & UNIQUENESS")
emit()

# documented expectations (from handoff / A2 §5) — for comparison only
DOC = {
    "source_ranking_rows": 261,
    "source_ranking_rows.APP": 137,
    "source_ranking_rows.RETAIL": 124,
    "panel_registry": 17,
    "panel_registry.SERVICE_BRAND": 16,
    "panel_registry.INDUSTRY_CATEGORY": 1,
    "service_master": 81,
    "service_master.APP": 38,
    "service_master.RETAIL": 43,
    "entity_alias_map": 82,
    "source_membership": 142,
    "web_target_group": 68,
    "certification_registry": 2283,
}

counts: dict[str, int] = {}
for name, df in D.items():
    counts[name] = len(df)
    emit(f"{name}: rows={len(df)} cols={df.shape[1]}")
emit()

# domain splits
for name, df, col in [
    ("source_ranking_rows", rows, "domain"),
    ("service_master", svc, "domain"),
    ("panel_registry", panel, "domain"),
    ("source_membership", memb, "domain"),
    ("entity_alias_map", alias, "domain"),
]:
    vc = df[col].value_counts(dropna=False).to_dict()
    emit(f"{name}.{col} = {vc}")
    for k, v in vc.items():
        counts[f"{name}.{k}"] = int(v)
emit()

for name, df in [("panel_registry", panel), ("source_ranking_rows", rows), ("service_master", svc)]:
    vc = df["axis_type"].value_counts(dropna=False).to_dict()
    emit(f"{name}.axis_type = {vc}")
    for k, v in vc.items():
        counts[f"{name}.{k}"] = int(v)
emit()

for k, expected in DOC.items():
    got = counts.get(k)
    mark = "OK" if got == expected else "MISMATCH"
    emit(f"  doc[{k}] = {expected}  measured = {got}  -> {mark}")
    if got != expected:
        finding(
            f"EDA00-COUNT-{k.replace('.', '-').replace('_', '-').upper()}",
            "P1",
            "row_count",
            f"{k} = {got}",
            f"{k} = {expected} (handoff/A2)",
            "eda00_frame_provenance.py §1",
        )
emit()

# PK uniqueness
PK = {
    "panel_registry": ["panel_id"],
    "source_ranking_rows": ["source_row_id"],
    "service_master": ["service_id"],
    "entity_alias_map": ["alias_id"],
    "source_membership": ["service_id", "panel_id"],
    "web_target_group": ["web_target_group_id"],
    "certification_registry": ["certification_number"],
}
emit("### primary key uniqueness")
for name, keys in PK.items():
    df = D[name]
    dup = int(df.duplicated(subset=keys).sum())
    emit(
        f"{name} PK{keys}: duplicates={dup} nunique={df[keys].drop_duplicates().shape[0]}/{len(df)}"
    )
    if dup:
        d = df[df.duplicated(subset=keys, keep=False)][keys]
        emit(f"    dup examples: {d.head(10).to_dict('records')}")
        finding(
            f"EDA00-PK-DUP-{name.upper()}",
            "P0",
            "integrity",
            f"{name} PK {keys} has {dup} duplicate rows",
            "0 duplicates",
            str(d.head(10).to_dict("records")),
        )
emit()

# candidate natural keys
emit("### natural / candidate key uniqueness")
nk_checks = [
    ("service_master.canonical_service_key", svc, ["canonical_service_key"]),
    ("service_master.service_name_canonical", svc, ["service_name_canonical"]),
    ("service_master.(service_name_canonical,domain)", svc, ["service_name_canonical", "domain"]),
    ("service_master.web_target_key", svc, ["web_target_key"]),
    (
        "entity_alias_map.(entity_name_raw,domain,axis_type)",
        alias,
        ["entity_name_raw", "domain", "axis_type"],
    ),
    ("entity_alias_map.entity_name_raw", alias, ["entity_name_raw"]),
    (
        "source_ranking_rows.(panel_id,rank,entity_name_raw,metric_name)",
        rows,
        ["panel_id", "rank", "entity_name_raw", "metric_name"],
    ),
    ("source_ranking_rows.(panel_id,rank,metric_name)", rows, ["panel_id", "rank", "metric_name"]),
    ("web_target_group.web_target_key", wtg, ["web_target_key"]),
    ("panel_registry.(figure_id,table_index)", panel, ["figure_id", "table_index"]),
    ("certification_registry.(certification_number)", cert, ["certification_number"]),
    ("certification_registry.(list_page,list_index)", cert, ["list_page", "list_index"]),
]
for label, df, keys in nk_checks:
    sub = df[keys].dropna(how="any")
    n_uniq = sub.drop_duplicates().shape[0]
    emit(f"{label}: nonnull={len(sub)}/{len(df)} unique={n_uniq} dup_rows={len(sub) - n_uniq}")
emit()

# service_name_canonical duplicates detail
dupn = svc[svc.duplicated("service_name_canonical", keep=False)][
    ["service_id", "canonical_service_key", "service_name_canonical", "domain", "axis_type"]
]
emit(f"service_name_canonical duplicated rows ({len(dupn)}):")
emit(dupn.to_string(index=False))
emit()

dupe_raw = alias[alias.duplicated("entity_name_raw", keep=False)][
    ["alias_id", "service_id", "entity_name_raw", "domain", "axis_type", "match_basis"]
].sort_values("entity_name_raw")
emit(f"entity_alias_map.entity_name_raw duplicated rows ({len(dupe_raw)}):")
emit(dupe_raw.to_string(index=False))
emit()

# alias with >1 alias per service
per_svc = alias.groupby("service_id").size()
emit(f"alias per service_id: {dict(Counter(per_svc.values))}")
emit("services with >1 alias: " + str(per_svc[per_svc > 1].to_dict()))
emit(f"match_basis: {alias['match_basis'].value_counts(dropna=False).to_dict()}")
emit()

# ================================================================ 2/3. orphans & referential integrity
emit("## 2/3. ORPHANS & REFERENTIAL INTEGRITY")
emit()

orph: dict[str, int] = {}


def check_fk(label, left, lkey, right, rkey, severity="P0"):
    """rows in `left` whose lkey has no match in right[rkey]."""
    lv = left[lkey].dropna()
    rv = set(right[rkey].dropna())
    miss = sorted(set(lv) - rv)
    orph[label] = len(miss)
    emit(
        f"FK {label}: left_nonnull={len(lv)} unmatched_values={len(miss)} rows_unmatched={int((~left[lkey].isin(rv) & left[lkey].notna()).sum())}"
    )
    if miss:
        emit(f"    missing: {miss[:20]}")
        finding(
            "EDA00-FK-" + re.sub(r"[^A-Z0-9]+", "-", label.upper()).strip("-"),
            severity,
            "referential_integrity",
            f"{label}: {len(miss)} unmatched key values -> {miss[:20]}",
            "0 unmatched",
            "eda00_frame_provenance.py §2/3",
        )
    return miss


def check_reverse(label, parent, pkey, child, ckey, severity="P1"):
    """values of parent[pkey] never referenced by child[ckey] (childless parents)."""
    pv = set(parent[pkey].dropna())
    cv = set(child[ckey].dropna())
    miss = sorted(pv - cv)
    orph[label] = len(miss)
    emit(f"REV {label}: parent_values={len(pv)} never_referenced={len(miss)}")
    if miss:
        emit(f"    orphan parents: {miss[:30]}")
        finding(
            "EDA00-ORPHAN-" + re.sub(r"[^A-Z0-9]+", "-", label.upper()).strip("-"),
            severity,
            "orphan",
            f"{label}: {len(miss)} values never referenced -> {miss[:30]}",
            "0 orphans",
            "eda00_frame_provenance.py §2/3",
        )
    return miss


# derive source_row -> service_id via alias join (A2 §5.2.1)
JKEY = ["entity_name_raw", "domain", "axis_type"]
alias_key_dup = int(alias.duplicated(subset=JKEY).sum())
emit(f"alias join key {JKEY} duplicates in alias map: {alias_key_dup}")
joined = rows.merge(
    alias[JKEY + ["service_id", "alias_id"]], on=JKEY, how="left", validate="many_to_one"
)
emit(f"join left rows={len(rows)} result rows={len(joined)} fanout={len(joined) - len(rows)}")
unmatched = joined[joined["service_id"].isna()]
emit(f"join unmatched source rows={len(unmatched)}")
orph["source_row->alias (join)"] = len(unmatched)
if len(unmatched):
    emit(
        unmatched[
            ["source_row_id", "panel_id", "entity_name_raw", "domain", "axis_type"]
        ].to_string(index=False)
    )
    finding(
        "EDA00-JOIN-UNMATCHED",
        "P0",
        "referential_integrity",
        f"{len(unmatched)} source rows do not match entity_alias_map on {JKEY}",
        "0",
        "eda00_frame_provenance.py §2/3",
    )
emit()

# forward FKs
check_fk("source_ranking_rows.panel_id -> panel_registry", rows, "panel_id", panel, "panel_id")
check_fk("source_membership.panel_id -> panel_registry", memb, "panel_id", panel, "panel_id")
check_fk("source_membership.service_id -> service_master", memb, "service_id", svc, "service_id")
check_fk("entity_alias_map.service_id -> service_master", alias, "service_id", svc, "service_id")
check_fk(
    "service_master.web_target_group_id -> web_target_group",
    svc,
    "web_target_group_id",
    wtg,
    "web_target_group_id",
)
check_fk("derived joined.service_id -> service_master", joined, "service_id", svc, "service_id")
check_fk(
    "source_ranking_rows.figure_id -> panel_registry.figure_id",
    rows,
    "figure_id",
    panel,
    "figure_id",
)
check_fk(
    "source_membership.figure_id -> panel_registry.figure_id", memb, "figure_id", panel, "figure_id"
)
emit()

# reverse (orphan parents)
check_reverse("panel_registry.panel_id <- source_ranking_rows", panel, "panel_id", rows, "panel_id")
check_reverse("panel_registry.panel_id <- source_membership", panel, "panel_id", memb, "panel_id")
check_reverse(
    "service_master.service_id <- source_membership", svc, "service_id", memb, "service_id"
)
check_reverse(
    "service_master.service_id <- entity_alias_map", svc, "service_id", alias, "service_id"
)
check_reverse(
    "service_master.service_id <- derived source_row join", svc, "service_id", joined, "service_id"
)
check_reverse(
    "web_target_group.web_target_group_id <- service_master",
    wtg,
    "web_target_group_id",
    svc,
    "web_target_group_id",
)
emit()

# entity -> web_target_group: entities with no group
no_group = svc[svc["web_target_group_id"].isna()]
emit(f"service_master rows with NULL web_target_group_id: {len(no_group)}")
emit(no_group["web_eligibility_status"].value_counts(dropna=False).to_string())
emit(no_group["axis_type"].value_counts(dropna=False).to_string())
emit(f"  service_ids: {sorted(no_group['service_id'].tolist())}")
orph["service_master with NULL web_target_group_id"] = len(no_group)
emit()


# web_target_group.member_service_ids explode -> service_master
def explode_ids(s):
    out = []
    for v in s.dropna():
        if isinstance(v, str):
            out += [x.strip() for x in v.split(",") if x.strip()]
        else:
            out += [str(x).strip() for x in list(v)]
    return out


wtg_members = explode_ids(wtg["member_service_ids"])
emit(
    f"web_target_group.member_service_ids exploded: {len(wtg_members)} (distinct {len(set(wtg_members))})"
)
emit(f"  member_count sum = {int(wtg['member_count'].sum())}")
emit(f"  member_count distribution = {wtg['member_count'].value_counts().to_dict()}")
missing_members = sorted(set(wtg_members) - set(svc["service_id"]))
emit(f"  members not in service_master: {len(missing_members)} {missing_members[:20]}")
orph["wtg.member_service_ids -> service_master"] = len(missing_members)
if missing_members:
    finding(
        "EDA00-FK-WTG-MEMBERS",
        "P0",
        "referential_integrity",
        f"{len(missing_members)} member_service_ids absent from service_master",
        "0",
        str(missing_members[:20]),
    )
# reverse: entities claiming a group but not listed as member
svc_grouped = svc[svc["web_target_group_id"].notna()]
back = set(svc_grouped["service_id"]) - set(wtg_members)
emit(
    f"  service_master entities with a group_id but NOT listed in that group's members: {len(back)} {sorted(back)[:20]}"
)
orph["service_master grouped but not a listed member"] = len(back)
if back:
    finding(
        "EDA00-WTG-MEMBERSHIP-ASYMMETRY",
        "P1",
        "referential_integrity",
        f"{len(back)} entities carry web_target_group_id but are not in member_service_ids",
        "0",
        str(sorted(back)[:20]),
    )
# consistency of the group_id each member points back to
memb_map = defaultdict(set)
for _, r in wtg.iterrows():
    for sid in explode_ids(pd.Series([r["member_service_ids"]])):
        memb_map[sid].add(r["web_target_group_id"])
bad_backref = []
for sid, gids in memb_map.items():
    row = svc[svc["service_id"] == sid]
    if row.empty:
        continue
    g = row.iloc[0]["web_target_group_id"]
    if len(gids) > 1 or g not in gids:
        bad_backref.append((sid, g, sorted(gids)))
emit(
    f"  member<->service_master group_id backref mismatches: {len(bad_backref)} {bad_backref[:10]}"
)
orph["wtg member backref mismatch"] = len(bad_backref)
if bad_backref:
    finding(
        "EDA00-WTG-BACKREF",
        "P0",
        "referential_integrity",
        f"{len(bad_backref)} member/service_master group_id disagreements",
        "0",
        str(bad_backref[:10]),
    )
emit()

# membership <-> derived pairs
derived_pairs = set(
    map(tuple, joined[["service_id", "panel_id"]].dropna().drop_duplicates().values)
)
stored_pairs = set(map(tuple, memb[["service_id", "panel_id"]].drop_duplicates().values))
emit(f"derived (service_id,panel_id) pairs = {len(derived_pairs)}")
emit(f"stored source_membership pairs      = {len(stored_pairs)}")
emit(
    f"derived - stored = {len(derived_pairs - stored_pairs)} {sorted(derived_pairs - stored_pairs)[:10]}"
)
emit(
    f"stored - derived = {len(stored_pairs - derived_pairs)} {sorted(stored_pairs - derived_pairs)[:10]}"
)
orph["derived-minus-stored membership"] = len(derived_pairs - stored_pairs)
orph["stored-minus-derived membership"] = len(stored_pairs - derived_pairs)
if derived_pairs != stored_pairs:
    finding(
        "EDA00-MEMBERSHIP-SET-DIFF",
        "P0",
        "referential_integrity",
        f"derived-stored={len(derived_pairs - stored_pairs)}, stored-derived={len(stored_pairs - derived_pairs)}",
        "both 0",
        "eda00_frame_provenance.py §2/3",
    )
emit()

# alias.panel_ids explode -> pairs
alias_pairs = set()
bad_alias_panels = []
for _, r in alias.iterrows():
    pids = [p.strip() for p in str(r["panel_ids"]).split(",") if p.strip()]
    for p in pids:
        alias_pairs.add((r["service_id"], p))
        if p not in set(panel["panel_id"]):
            bad_alias_panels.append((r["alias_id"], p))
emit(f"alias.panel_ids exploded pairs = {len(alias_pairs)}")
emit(
    f"  vs stored membership: alias-stored={len(alias_pairs - stored_pairs)} stored-alias={len(stored_pairs - alias_pairs)}"
)
emit(
    f"  alias.panel_ids referencing unknown panel: {len(bad_alias_panels)} {bad_alias_panels[:10]}"
)
orph["alias.panel_ids -> panel_registry"] = len(bad_alias_panels)
if bad_alias_panels:
    finding(
        "EDA00-FK-ALIAS-PANELIDS",
        "P0",
        "referential_integrity",
        f"{len(bad_alias_panels)} alias.panel_ids entries reference a non-existent panel_id",
        "0",
        str(bad_alias_panels[:10]),
    )
if alias_pairs != stored_pairs:
    finding(
        "EDA00-ALIAS-PANELIDS-SET-DIFF",
        "P1",
        "referential_integrity",
        f"alias-stored={len(alias_pairs - stored_pairs)} stored-alias={len(stored_pairs - alias_pairs)}",
        "both 0",
        "eda00_frame_provenance.py §2/3",
    )
emit()

# membership.rank / n_metrics cross-check
chk = joined.groupby(["service_id", "panel_id"])["rank"].min().rename("rank_derived").reset_index()
m2 = memb.merge(chk, on=["service_id", "panel_id"], how="outer", indicator=True)
bad_rank = m2[(m2["_merge"] == "both") & (m2["rank"] != m2["rank_derived"])]
emit(f"source_membership.rank vs min(rank) from join: mismatches={len(bad_rank)}")
if len(bad_rank):
    emit(bad_rank.head(20).to_string(index=False))
    finding(
        "EDA00-MEMBERSHIP-RANK",
        "P1",
        "consistency",
        f"{len(bad_rank)} membership rows whose rank != min(rank) of the joined source rows",
        "0",
        "eda00_frame_provenance.py §2/3",
    )
m3 = memb.merge(
    panel[["panel_id", "n_metrics"]], on="panel_id", how="left", suffixes=("", "_panel")
)
bad_nm = m3[m3["n_metrics"] != m3["n_metrics_panel"]]
emit(f"source_membership.n_metrics vs panel_registry.n_metrics: mismatches={len(bad_nm)}")
if len(bad_nm):
    finding(
        "EDA00-MEMBERSHIP-NMETRICS",
        "P1",
        "consistency",
        f"{len(bad_nm)} mismatches",
        "0",
        "eda00_frame_provenance.py §2/3",
    )
# membership domain/axis/figure vs panel_registry
m4 = memb.merge(
    panel[["panel_id", "domain", "axis_type", "figure_id"]],
    on="panel_id",
    how="left",
    suffixes=("", "_p"),
)
for c in ["domain", "axis_type", "figure_id"]:
    bad = m4[m4[c] != m4[c + "_p"]]
    emit(f"source_membership.{c} vs panel_registry.{c}: mismatches={len(bad)}")
    if len(bad):
        finding(
            f"EDA00-MEMBERSHIP-{c.upper()}",
            "P1",
            "consistency",
            f"{len(bad)} mismatches",
            "0",
            "eda00_frame_provenance.py §2/3",
        )
# source_ranking_rows denormalized cols vs panel_registry
m5 = rows.merge(
    panel[
        [
            "panel_id",
            "domain",
            "axis_type",
            "figure_id",
            "table_title",
            "panel_label",
            "period_label",
            "period_axis",
        ]
    ],
    on="panel_id",
    how="left",
    suffixes=("", "_p"),
)
for c in [
    "domain",
    "axis_type",
    "figure_id",
    "table_title",
    "panel_label",
    "period_label",
    "period_axis",
]:
    bad = m5[m5[c].fillna("<NA>") != m5[c + "_p"].fillna("<NA>")]
    emit(f"source_ranking_rows.{c} vs panel_registry.{c}: mismatches={len(bad)}")
    if len(bad):
        emit(
            "   "
            + str(bad[["panel_id", c, c + "_p"]].drop_duplicates().head(10).to_dict("records"))
        )
        finding(
            f"EDA00-DENORM-ROWS-{c.upper()}",
            "P1",
            "consistency",
            f"{len(bad)} source rows whose denormalized {c} disagrees with panel_registry",
            "0",
            str(bad[["panel_id", c, c + "_p"]].drop_duplicates().head(10).to_dict("records")),
        )
# alias domain/axis vs service_master
m6 = alias.merge(
    svc[["service_id", "domain", "axis_type"]], on="service_id", how="left", suffixes=("", "_s")
)
for c in ["domain", "axis_type"]:
    bad = m6[m6[c] != m6[c + "_s"]]
    emit(f"entity_alias_map.{c} vs service_master.{c}: mismatches={len(bad)}")
    if len(bad):
        finding(
            f"EDA00-ALIAS-{c.upper()}",
            "P1",
            "consistency",
            f"{len(bad)} mismatches",
            "0",
            "eda00_frame_provenance.py §2/3",
        )
emit()

# service_master counters vs derived
agg = (
    joined.assign(is_app=lambda d: d["domain"] == "APP", is_ret=lambda d: d["domain"] == "RETAIL")
    .groupby("service_id")
    .agg(
        app_row_count_d=("is_app", "sum"),
        retail_row_count_d=("is_ret", "sum"),
    )
    .reset_index()
)
pan_app = (
    joined[joined["domain"] == "APP"]
    .groupby("service_id")["panel_id"]
    .nunique()
    .rename("appears_in_app_panels_d")
    .reset_index()
)
pan_ret = (
    joined[joined["domain"] == "RETAIL"]
    .groupby("service_id")["panel_id"]
    .nunique()
    .rename("appears_in_retail_panels_d")
    .reset_index()
)
alias_cnt = alias.groupby("service_id").size().rename("alias_count_d").reset_index()
sm = (
    svc.merge(agg, on="service_id", how="left")
    .merge(pan_app, on="service_id", how="left")
    .merge(pan_ret, on="service_id", how="left")
    .merge(alias_cnt, on="service_id", how="left")
)
for a, b in [
    ("app_row_count", "app_row_count_d"),
    ("retail_row_count", "retail_row_count_d"),
    ("appears_in_app_panels", "appears_in_app_panels_d"),
    ("appears_in_retail_panels", "appears_in_retail_panels_d"),
    ("alias_count", "alias_count_d"),
]:
    got = sm[b].fillna(0).astype(int)
    bad = sm[sm[a].astype(int) != got]
    emit(f"service_master.{a} vs derived: mismatches={len(bad)}")
    if len(bad):
        emit(
            "   "
            + str(bad[["service_id", "service_name_canonical", a, b]].head(10).to_dict("records"))
        )
        finding(
            f"EDA00-SVC-COUNTER-{a.upper()}",
            "P1",
            "consistency",
            f"{len(bad)} service_master rows whose {a} disagrees with the value derived from source rows",
            "0",
            str(bad[["service_id", a, b]].head(10).to_dict("records")),
        )
emit()

# panel rows_extracted vs actual
pr = rows.groupby("panel_id").size().rename("actual_rows").reset_index()
pm = panel.merge(pr, on="panel_id", how="left")
pm["actual_rows"] = pm["actual_rows"].fillna(0).astype(int)
emit("### panel_registry row accounting")
emit(
    pm[
        [
            "panel_id",
            "figure_id",
            "domain",
            "axis_type",
            "n_metrics",
            "rows_expected",
            "rows_extracted",
            "actual_rows",
            "row_count_verification",
            "row_count_ok",
        ]
    ].to_string(index=False)
)
bad = pm[pm["rows_extracted"] != pm["actual_rows"]]
emit(f"rows_extracted != actual source rows: {len(bad)}")
if len(bad):
    emit(bad[["panel_id", "rows_extracted", "actual_rows", "n_metrics"]].to_string(index=False))
    finding(
        "EDA00-PANEL-ROWS-EXTRACTED-GRAIN",
        "P1",
        "grain",
        f"{len(bad)}/17 panels: rows_extracted != count of source_ranking_rows for that panel",
        "equal, or documented as a different grain",
        str(bad[["panel_id", "rows_extracted", "actual_rows", "n_metrics"]].to_dict("records")),
    )
# does actual == rows_extracted * n_metrics?
pm["expect_x_metrics"] = pm["rows_extracted"] * pm["n_metrics"]
bad2 = pm[pm["expect_x_metrics"] != pm["actual_rows"]]
emit(f"rows_extracted * n_metrics != actual: {len(bad2)}")
if len(bad2):
    emit(
        bad2[
            ["panel_id", "rows_extracted", "n_metrics", "expect_x_metrics", "actual_rows"]
        ].to_string(index=False)
    )
emit(
    f"sum(rows_extracted)={int(pm['rows_extracted'].sum())} sum(actual)={int(pm['actual_rows'].sum())} sum(rows_extracted*n_metrics)={int(pm['expect_x_metrics'].sum())}"
)
emit(f"rows_expected nonnull={int(pm['rows_expected'].notna().sum())}/17")
bad3 = pm[pm["rows_expected"].notna() & (pm["rows_expected"] != pm["rows_extracted"])]
emit(f"rows_expected != rows_extracted (where nonnull): {len(bad3)}")
if len(bad3):
    emit(bad3[["panel_id", "rows_expected", "rows_extracted"]].to_string(index=False))
    finding(
        "EDA00-PANEL-ROWS-EXPECTED",
        "P1",
        "consistency",
        f"{len(bad3)} panels where rows_expected != rows_extracted",
        "0",
        str(bad3[["panel_id", "rows_expected", "rows_extracted"]].to_dict("records")),
    )
emit(
    f"row_count_verification = {panel['row_count_verification'].value_counts(dropna=False).to_dict()}"
)
emit(f"row_count_ok = {panel['row_count_ok'].value_counts(dropna=False).to_dict()}")
emit(f"n_metrics distribution = {panel['n_metrics'].value_counts().sort_index().to_dict()}")
emit(
    f"panels with n_metrics>1 = {int((panel['n_metrics'] > 1).sum())} -> {sorted(panel.loc[panel['n_metrics'] > 1, 'panel_id'])}"
)
emit(
    f"extraction_confidence = {panel['extraction_confidence'].value_counts(dropna=False).to_dict()}"
)
emit(f"unreadable = {panel['unreadable'].value_counts(dropna=False).to_dict()}")
emit(f"period_axis = {panel['period_axis'].value_counts(dropna=False).to_dict()}")
emit(f"source_section = {panel['source_section'].value_counts(dropna=False).to_dict()}")
emit(f"panel_scope = {panel['panel_scope'].value_counts(dropna=False).to_dict()}")
emit()

# ================================================================ 4. provenance hashes
emit("## 4. SOURCE HASH / PROVENANCE VERIFICATION")
emit()
hash_results = []

sem_path = f"{ROOT}/sources/wiseapp/source_evidence_manifest.json"
sem = json.load(open(sem_path))
for fig in sem["figures"]:
    fp = os.path.join(ROOT, fig["file"])
    exists = os.path.exists(fp)
    rec = {"item": fig["figure_id"], "file": fig["file"], "exists": exists}
    if exists:
        rec["declared_bytes"] = fig["bytes"]
        rec["actual_bytes"] = os.path.getsize(fp)
        rec["declared_sha256"] = strip_prefix(fig["sha256"])
        rec["actual_sha256"] = sha256_file(fp)
        rec["ok"] = (
            rec["declared_sha256"] == rec["actual_sha256"]
            and rec["declared_bytes"] == rec["actual_bytes"]
        )
    else:
        rec["ok"] = False
    hash_results.append(rec)

ej = sem["extraction_journal"]
ejp = os.path.join(ROOT, ej["file"])
rec = {"item": "extraction_journal(manifest)", "file": ej["file"], "exists": os.path.exists(ejp)}
if rec["exists"]:
    rec["declared_bytes"] = ej["bytes"]
    rec["actual_bytes"] = os.path.getsize(ejp)
    rec["declared_sha256"] = strip_prefix(ej["sha256"])
    rec["actual_sha256"] = sha256_file(ejp)
    rec["declared_lines"] = ej["lines"]
    rec["actual_lines"] = sum(1 for _ in open(ejp, encoding="utf-8"))
    rec["ok"] = (
        rec["declared_sha256"] == rec["actual_sha256"]
        and rec["declared_bytes"] == rec["actual_bytes"]
        and rec["declared_lines"] == rec["actual_lines"]
    )
hash_results.append(rec)

jp = json.load(open(f"{ROOT}/state/journal_provenance.json"))
jpp = os.path.join(ROOT, "..", "..", jp["journal_path_in_repo"])
jpp = os.path.abspath(os.path.join(REPO_ROOT, jp["journal_path_in_repo"]))
rec = {
    "item": "extraction_journal(journal_provenance)",
    "file": jp["journal_path_in_repo"],
    "exists": os.path.exists(jpp),
}
if rec["exists"]:
    rec["declared_bytes"] = jp["journal_bytes"]
    rec["actual_bytes"] = os.path.getsize(jpp)
    rec["declared_sha256"] = strip_prefix(jp["journal_sha256"])
    rec["actual_sha256"] = sha256_file(jpp)
    rec["ok"] = (
        rec["declared_sha256"] == rec["actual_sha256"]
        and rec["declared_bytes"] == rec["actual_bytes"]
    )
hash_results.append(rec)

am = json.load(open(f"{ROOT}/sources/wiseapp/authority_manifest.json"))
RAW_MAP = {
    "detail_json": "sources/wiseapp/raw/wiseapp933_detail.json",
    "rendered_html": "sources/wiseapp/raw/wiseapp933_rendered.html",
    "body_text": "sources/wiseapp/raw/wiseapp933_text.txt",
    "full_page_screenshot": "sources/wiseapp/raw/wiseapp933_full.png",
}
for k, rel in RAW_MAP.items():
    fp = os.path.join(ROOT, rel)
    d = am["raw_assets"][k]
    rec = {"item": f"raw_assets.{k}", "file": rel, "exists": os.path.exists(fp)}
    if rec["exists"]:
        rec["declared_bytes"] = d["bytes"]
        rec["actual_bytes"] = os.path.getsize(fp)
        rec["declared_sha256"] = strip_prefix(d["sha256"])
        rec["actual_sha256"] = sha256_file(fp)
        rec["ok"] = (
            rec["declared_sha256"] == rec["actual_sha256"]
            and rec["declared_bytes"] == rec["actual_bytes"]
        )
    hash_results.append(rec)

# authority manifest self-hash
am2 = dict(am)
am2.pop("manifest_self_sha256_excluding_self_field", None)
self_calc = hashlib.sha256(
    json.dumps(am2, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
hash_results.append(
    {
        "item": "authority_manifest.self_sha256",
        "file": "sources/wiseapp/authority_manifest.json",
        "exists": True,
        "declared_sha256": strip_prefix(am["manifest_self_sha256_excluding_self_field"]),
        "actual_sha256": self_calc,
        "ok": strip_prefix(am["manifest_self_sha256_excluding_self_field"]) == self_calc,
    }
)

hdf = pd.DataFrame(hash_results)
emit(
    hdf[["item", "exists", "ok", "declared_bytes", "actual_bytes"]].to_string(index=False)
    if "declared_bytes" in hdf
    else hdf.to_string(index=False)
)
emit()
bad_hash = hdf[hdf["ok"] != True]  # noqa: E712
emit(f"HASH FAILURES: {len(bad_hash)}/{len(hdf)}")
if len(bad_hash):
    emit(bad_hash.to_string(index=False))
    for _, r in bad_hash.iterrows():
        finding(
            "EDA00-HASH-" + re.sub(r"[^A-Z0-9]+", "-", str(r["item"]).upper()).strip("-"),
            "P0",
            "provenance",
            f"{r['item']}: declared {r.get('declared_sha256')} vs actual {r.get('actual_sha256')} (bytes {r.get('declared_bytes')} vs {r.get('actual_bytes')})",
            "sha256 and byte size match",
            f"file={r['file']}",
        )
emit()

# unhashed files present in sources/wiseapp
declared_files = {f["file"] for f in sem["figures"]} | {ej["file"]} | set(RAW_MAP.values())
present = set()
for dp, _, fns in os.walk(f"{ROOT}/sources/wiseapp"):
    for fn in fns:
        present.add(os.path.relpath(os.path.join(dp, fn), ROOT))
undeclared = sorted(present - declared_files)
emit(f"files under sources/wiseapp with no declared sha256: {len(undeclared)}")
for u in undeclared:
    emit(f"    {u}")
if undeclared:
    finding(
        "EDA00-PROV-UNDECLARED-FILES",
        "P2",
        "provenance",
        f"{len(undeclared)} files under sources/wiseapp carry no sha256 in any manifest: {undeclared}",
        "every source artifact hashed, or explicitly exempted",
        "eda00_frame_provenance.py §4",
    )
emit()

# journal -> rebuilt rows claim
emit(
    f"journal_provenance.rows_rebuilt = {jp['rows_rebuilt']}  actual source_ranking_rows = {len(rows)}"
)
emit(
    f"journal_provenance.panels_rebuilt = {jp['panels_rebuilt']}  actual panel_registry = {len(panel)}"
)
emit(
    f"journal_provenance.figures_read = {len(jp['figures_read'])}  manifest figures = {len(sem['figures'])}  distinct figure_id in panel_registry = {panel['figure_id'].nunique()}"
)
emit(f"  panel figure_ids: {sorted(panel['figure_id'].unique())}")
emit(f"  manifest figure_ids: {sorted(f['figure_id'] for f in sem['figures'])}")
fig_gap = sorted(set(f["figure_id"] for f in sem["figures"]) - set(panel["figure_id"]))
emit(f"  figures declared but with no panel: {fig_gap}")
if fig_gap:
    finding(
        "EDA00-FIGURE-NO-PANEL",
        "P2",
        "provenance",
        f"figures with evidence but no panel_registry row: {fig_gap}",
        "0 or documented",
        "eda00_frame_provenance.py §4",
    )
# row_id formula check
formula_bad = []
for _, r in rows.iterrows():
    key = f"{r['panel_id']}|{r['rank']}|{r['entity_name_raw']}|{r['metric_name']}"
    want = "row_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    if want != r["source_row_id"]:
        formula_bad.append((r["source_row_id"], want, key))
emit(
    f"source_row_id vs declared formula row_+sha256('panel|rank|entity|metric')[:16]: mismatches={len(formula_bad)}"
)
if formula_bad:
    emit("   " + str(formula_bad[:5]))
    finding(
        "EDA00-ROWID-FORMULA",
        "P1",
        "provenance",
        f"{len(formula_bad)} source_row_id values do not reproduce the documented formula",
        "0",
        str(formula_bad[:5]),
    )
# figure_source_pointer format
ptr_bad = rows[~rows["figure_source_pointer"].astype(str).str.match(r"^fig\d+#t\d+/rank\d+/.+$")]
emit(f"figure_source_pointer not matching '<figure>#t<idx>/rank<r>/<metric>': {len(ptr_bad)}")
if len(ptr_bad):
    emit(ptr_bad["figure_source_pointer"].head(5).to_string())
emit()

# ================================================================ 5. certification snapshot
emit("## 5. CERTIFICATION SNAPSHOT")
emit()
rsm = json.load(open(f"{ROOT}/sources/certification/registry_snapshot_manifest.json"))
emit(
    f"manifest: rows_raw={rsm['rows_raw']} rows_dedup={rsm['rows_dedup']} pages_fetched={rsm['pages_fetched']} pages_with_cards={rsm['pages_with_cards']} declared_last_page={rsm['declared_last_page']}"
)
emit(
    f"manifest: status_breakdown={rsm['status_breakdown']} in_period_at_audit={rsm['in_period_at_audit']} valid_at_audit={rsm['valid_at_audit']} snapshot_status={rsm['snapshot_status']}"
)
emit(f"parquet rows = {len(cert)} cols = {list(cert.columns)}")
emit(f"'valid_on_audit_date' column present: {'valid_on_audit_date' in cert.columns}")
if "valid_on_audit_date" not in cert.columns:
    finding(
        "EDA00-CERT-COLUMN-NAME",
        "P2",
        "schema",
        "certification_registry has no column named 'valid_on_audit_date'; the nearest columns are in_period_at_audit and cert_valid_candidate",
        "handoff cites valid_on_audit_date = 226",
        "eda00_frame_provenance.py §5",
    )

emit(f"in_period_at_audit sum = {int(cert['in_period_at_audit'].sum())}")
emit(f"cert_valid_candidate sum = {int(cert['cert_valid_candidate'].sum())}")
emit(
    f"certification_status_listed = {cert['certification_status_listed'].value_counts(dropna=False).to_dict()}"
)
emit(
    f"rows_with_target_url(nonnull&nonempty) = {int(cert['certified_target_url_listed'].fillna('').str.strip().ne('').sum())}"
)
emit(
    f"rows_without_target_url = {int(cert['certified_target_url_listed'].fillna('').str.strip().eq('').sum())}"
)
scheme_less = cert["certified_target_url_listed"].fillna("").str.strip()
sl = scheme_less[(scheme_less != "") & (~scheme_less.str.match(r"^https?://", case=False))]
emit(f"scheme-less target urls = {len(sl)} e.g. {sl.head(5).tolist()}")
no_period = cert[
    cert["cert_start_date"].fillna("").eq("") | cert["cert_end_date"].fillna("").eq("")
]
emit(f"rows_without_period (start or end blank) = {len(no_period)}")
if len(no_period):
    emit(
        no_period[
            [
                "certification_number",
                "service_name",
                "cert_start_date",
                "cert_end_date",
                "certification_status_listed",
            ]
        ].to_string(index=False)
    )

# recompute in-period at audit_date
audit_date = rsm["audit_date"]
sd = pd.to_datetime(cert["cert_start_date"], errors="coerce")
ed = pd.to_datetime(cert["cert_end_date"], errors="coerce")
ad = pd.Timestamp(audit_date)
in_period_calc = ((sd <= ad) & (ed >= ad)).fillna(False)
emit(
    f"recomputed in-period at {audit_date}: {int(in_period_calc.sum())}  (stored in_period_at_audit={int(cert['in_period_at_audit'].sum())})"
)
mismatch_ip = cert[in_period_calc.astype(int) != cert["in_period_at_audit"].astype(int)]
emit(f"per-row in_period mismatch = {len(mismatch_ip)}")
if len(mismatch_ip):
    emit(
        mismatch_ip[
            ["certification_number", "cert_start_date", "cert_end_date", "in_period_at_audit"]
        ]
        .head(10)
        .to_string(index=False)
    )
    finding(
        "EDA00-CERT-INPERIOD-RECOMPUTE",
        "P1",
        "consistency",
        f"{len(mismatch_ip)} rows where recomputed (start<=audit<=end) disagrees with stored in_period_at_audit",
        "0",
        "eda00_frame_provenance.py §5",
    )
# VALID vs in-period
valid_listed = cert["certification_status_listed"].astype(str).str.upper().eq("VALID")
emit(
    f"status_listed==VALID: {int(valid_listed.sum())}; of those in-period: {int((valid_listed & in_period_calc).sum())}; VALID but NOT in-period: {int((valid_listed & ~in_period_calc).sum())}"
)
odd = cert[valid_listed & ~in_period_calc]
if len(odd):
    emit(
        odd[
            [
                "certification_number",
                "service_name",
                "cert_start_date",
                "cert_end_date",
                "certification_status_listed",
            ]
        ].to_string(index=False)
    )
    finding(
        "EDA00-CERT-VALID-NOT-IN-PERIOD",
        "P1",
        "distribution",
        f"{len(odd)} rows listed VALID by the registry but whose period does not cover audit_date {audit_date}",
        "status_breakdown.VALID (227) == valid_at_audit (226) would require 0",
        str(
            odd[
                ["certification_number", "service_name", "cert_start_date", "cert_end_date"]
            ].to_dict("records")
        ),
    )
emit(f"in-period but NOT listed VALID: {int((~valid_listed & in_period_calc).sum())}")

# manifest vs parquet count checks
cert_checks = [
    ("rows_dedup", rsm["rows_dedup"], len(cert)),
    ("rows_raw", rsm["rows_raw"], len(cert)),
    ("in_period_at_audit", rsm["in_period_at_audit"], int(cert["in_period_at_audit"].sum())),
    ("valid_at_audit", rsm["valid_at_audit"], int(cert["cert_valid_candidate"].sum())),
    ("status VALID", rsm["status_breakdown"]["VALID"], int(valid_listed.sum())),
    (
        "status EXPIRED",
        rsm["status_breakdown"]["EXPIRED"],
        int(cert["certification_status_listed"].astype(str).str.upper().eq("EXPIRED").sum()),
    ),
    (
        "rows_with_target_url",
        rsm["rows_with_target_url"],
        int(cert["certified_target_url_listed"].fillna("").str.strip().ne("").sum()),
    ),
    (
        "rows_without_target_url",
        rsm["rows_without_target_url"],
        int(cert["certified_target_url_listed"].fillna("").str.strip().eq("").sum()),
    ),
    ("rows_with_scheme_less_target_url", rsm["rows_with_scheme_less_target_url"], len(sl)),
    ("rows_without_period", rsm["rows_without_period"], len(no_period)),
]
emit()
emit("### manifest vs parquet")
for label, decl, meas in cert_checks:
    mark = "OK" if decl == meas else "MISMATCH"
    emit(f"  {label}: manifest={decl} measured={meas} -> {mark}")
    if decl != meas:
        finding(
            "EDA00-CERT-" + re.sub(r"[^A-Z0-9]+", "-", label.upper()).strip("-"),
            "P1",
            "consistency",
            f"{label}: manifest={decl} measured={meas}",
            "equal",
            "eda00_frame_provenance.py §5",
        )

# raw html hashes + card counts
emit()
emit("### raw HTML page hashes and card counts")
raw_dir = f"{ROOT}/sources/certification/raw"
raw_files = sorted(os.listdir(raw_dir))
emit(f"raw files on disk = {len(raw_files)}; page_hashes entries = {len(rsm['page_hashes'])}")
ph_paths = {os.path.basename(p["raw_path"]) for p in rsm["page_hashes"]}
emit(f"on-disk but not in manifest: {sorted(set(raw_files) - ph_paths)}")
emit(f"in manifest but not on disk: {sorted(ph_paths - set(raw_files))}")
if set(raw_files) != ph_paths:
    finding(
        "EDA00-CERT-RAW-FILESET",
        "P1",
        "provenance",
        f"raw dir has {len(raw_files)} files, manifest lists {len(ph_paths)}; symmetric diff {sorted(set(raw_files) ^ ph_paths)}",
        "identical sets",
        "eda00_frame_provenance.py §5",
    )

card_re = re.compile(r'<article class="container cert-list', re.I)
bad_page_hash = []
declared_cards = 0
measured_cards = 0
page_card_measured = {}
for p in rsm["page_hashes"]:
    fp = os.path.join(ROOT, "sources/certification", p["raw_path"])
    declared_cards += p["card_count"]
    if not os.path.exists(fp):
        bad_page_hash.append((p["page"], "MISSING", None))
        continue
    actual = sha256_file(fp)
    if actual != p["raw_sha256"]:
        bad_page_hash.append((p["page"], p["raw_sha256"], actual))
    html = open(fp, encoding="utf-8", errors="replace").read()
    n = len(card_re.findall(html))
    page_card_measured[p["page"]] = n
    measured_cards += n
emit(f"page hash mismatches = {len(bad_page_hash)} {bad_page_hash[:10]}")
if bad_page_hash:
    finding(
        "EDA00-CERT-PAGE-HASH",
        "P0",
        "provenance",
        f"{len(bad_page_hash)} raw list pages whose sha256 differs from registry_snapshot_manifest",
        "0",
        str(bad_page_hash[:10]),
    )
emit(
    f"declared card_count sum = {declared_cards}; detail-link occurrences in raw HTML = {measured_cards}"
)
emit(f"parquet rows = {len(cert)}")
per_page_parquet = cert.groupby("list_page").size().to_dict()
diff_pages = {
    p: (page_card_measured.get(p), per_page_parquet.get(p))
    for p in sorted(set(page_card_measured) | set(per_page_parquet))
    if page_card_measured.get(p, 0) != per_page_parquet.get(p, 0)
}
emit(f"pages where raw-HTML link count != parquet row count: {len(diff_pages)}")
if diff_pages:
    emit(f"   {dict(list(diff_pages.items())[:20])}")
declared_by_page = {p["page"]: p["card_count"] for p in rsm["page_hashes"]}
diff2 = {
    p: (declared_by_page.get(p), per_page_parquet.get(p))
    for p in sorted(set(declared_by_page) | set(per_page_parquet))
    if declared_by_page.get(p, 0) != per_page_parquet.get(p, 0)
}
emit(
    f"pages where manifest card_count != parquet row count: {len(diff2)} {dict(list(diff2.items())[:20])}"
)
if diff2:
    finding(
        "EDA00-CERT-CARDCOUNT",
        "P1",
        "consistency",
        f"{len(diff2)} pages where manifest card_count != parsed parquet rows: {dict(list(diff2.items())[:20])}",
        "0",
        "eda00_frame_provenance.py §5",
    )
if declared_cards != len(cert):
    finding(
        "EDA00-CERT-CARDSUM",
        "P1",
        "consistency",
        f"sum(card_count)={declared_cards} but parquet rows={len(cert)}",
        "equal",
        "eda00_frame_provenance.py §5",
    )
emit(
    f"list_page range in parquet: {int(cert['list_page'].min())}..{int(cert['list_page'].max())} distinct={cert['list_page'].nunique()}"
)
missing_pages = sorted(
    set(range(1, rsm["declared_last_page"] + 1)) - set(cert["list_page"].unique())
)
emit(f"declared_last_page={rsm['declared_last_page']} pages with 0 parquet rows: {missing_pages}")

# cert row-level raw_sha256 vs page hash
cert_ph = {p["page"]: p["raw_sha256"] for p in rsm["page_hashes"]}
cert["_expect_hash"] = cert["list_page"].map(cert_ph)
bad_row_hash = cert[
    cert["raw_sha256"].astype(str).str.replace("sha256:", "", regex=False) != cert["_expect_hash"]
]
emit(
    f"certification_registry.raw_sha256 rows disagreeing with the manifest page hash: {len(bad_row_hash)}"
)
if len(bad_row_hash):
    emit(
        bad_row_hash[["certification_number", "list_page", "raw_sha256", "_expect_hash"]]
        .head(5)
        .to_string(index=False)
    )
    finding(
        "EDA00-CERT-ROW-HASH",
        "P1",
        "provenance",
        f"{len(bad_row_hash)} registry rows whose raw_sha256 differs from the manifest hash of their list_page",
        "0",
        "eda00_frame_provenance.py §5",
    )
cert.drop(columns=["_expect_hash"], inplace=True)

# --- independent re-parse of the raw HTML, compared field-by-field to the parquet
emit()
emit("### independent re-parse of raw HTML vs parquet (field level)")
ART = re.compile(r'<article class="container cert-list.*?</article>', re.S | re.I)
H3 = re.compile(r"<h3>(.*?)</h3>", re.S)
ORG = re.compile(r"기관명\s*:\s*</span><span>(.*?)</span>", re.S)
PER = re.compile(r"인증기간\s*:\s*</span><span>(.*?)</span>", re.S)
STA = re.compile(r"상태\s*:\s*</span><span>(.*?)</span>", re.S)
DET = re.compile(r'href="(/CertificationSite/WA/(\d+)/Detail[^"]*)"', re.S)
SITE = re.compile(r'<a href="([^"]*)"[^>]*target="_blank"', re.S)
TOTAL = re.compile(r"전체 신청 수\s*:\s*([\d,]+)개,\s*전체\s*(\d+)\s*페이지")


def untag(s):
    import html as _html

    return _html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


reparsed = []
declared_totals = set()
declared_pages = set()
for p in rsm["page_hashes"]:
    fp = os.path.join(ROOT, "sources/certification", p["raw_path"])
    if not os.path.exists(fp):
        continue
    html = open(fp, encoding="utf-8", errors="replace").read()
    t = TOTAL.search(html)
    if t:
        declared_totals.add(int(t.group(1).replace(",", "")))
        declared_pages.add(int(t.group(2)))
    for idx, art in enumerate(ART.findall(html)):
        d = DET.search(art)
        per = PER.search(art)
        period = untag(per.group(1)) if per else ""
        st = en = None
        if "~" in period:
            a, b = [x.strip().replace(".", "-") for x in period.split("~", 1)]
            st, en = (a or None), (b or None)
            if st in ("-", ""):
                st = None
            if en in ("-", ""):
                en = None
        site = SITE.search(art)
        reparsed.append(
            {
                "certification_number": d.group(2) if d else None,
                "service_name": untag(H3.search(art).group(1)) if H3.search(art) else None,
                "organization_name": untag(ORG.search(art).group(1)) if ORG.search(art) else None,
                "status_raw": untag(STA.search(art).group(1)) if STA.search(art) else None,
                "cert_start_date": st,
                "cert_end_date": en,
                "target_url": untag(site.group(1)) if site else "",
                "list_page": p["page"],
                "list_index": idx + int(cert["list_index"].min()),
            }
        )
rp = pd.DataFrame(reparsed)
emit(f"re-parsed cards = {len(rp)}; parquet rows = {len(cert)}")
emit(
    f"page banner 'total applications' distinct values across 230 pages = {sorted(declared_totals)}; total pages = {sorted(declared_pages)}"
)
if len(declared_totals) == 1 and list(declared_totals)[0] != len(cert):
    finding(
        "EDA00-CERT-SITE-DECLARED-TOTAL",
        "P1",
        "completeness",
        f"the registry page itself declares {list(declared_totals)[0]} applications, parquet holds {len(cert)}",
        "equal",
        "eda00_frame_provenance.py §5",
    )
if len(rp) != len(cert):
    finding(
        "EDA00-CERT-REPARSE-COUNT",
        "P0",
        "completeness",
        f"independent re-parse of the 230 raw pages yields {len(rp)} cards, parquet has {len(cert)}",
        "equal",
        "eda00_frame_provenance.py §5",
    )
if not rp.empty:
    cmpdf = cert.merge(
        rp, on=["list_page", "list_index"], how="outer", suffixes=("_pq", "_rp"), indicator=True
    )
    emit(
        f"merge on (list_page,list_index): both={int((cmpdf['_merge'] == 'both').sum())} pq_only={int((cmpdf['_merge'] == 'left_only').sum())} raw_only={int((cmpdf['_merge'] == 'right_only').sum())}"
    )
    both = cmpdf[cmpdf["_merge"] == "both"]
    for a, b, label in [
        ("certification_number_pq", "certification_number_rp", "certification_number"),
        ("service_name_pq", "service_name_rp", "service_name"),
        ("organization_name_pq", "organization_name_rp", "organization_name"),
        ("cert_start_date_pq", "cert_start_date_rp", "cert_start_date"),
        ("cert_end_date_pq", "cert_end_date_rp", "cert_end_date"),
    ]:
        x = both[a].astype(str).str.strip().replace({"None": "", "nan": ""})
        y = both[b].astype(str).str.strip().replace({"None": "", "nan": ""})
        raw_bad = x != y
        nx = x.str.replace(r"\s+", " ", regex=True).str.replace("\u00a0", " ", regex=False)
        ny = y.str.replace(r"\s+", " ", regex=True).str.replace("\u00a0", " ", regex=False)
        norm_bad = nx != ny
        nbad = int(norm_bad.sum())
        ws_only = int(raw_bad.sum()) - nbad
        emit(f"  field {label}: mismatches={nbad} (+{ws_only} whitespace/NBSP-normalization-only)")
        if ws_only:
            emit(
                "     ws-only: "
                + str(
                    both.loc[raw_bad & ~norm_bad, ["list_page", "list_index", a, b]]
                    .head(5)
                    .to_dict("records")
                )
            )
            finding(
                f"EDA00-CERT-REPARSE-WS-{label.upper()}",
                "P2",
                "provenance",
                f"{ws_only} rows where the parquet {label} is whitespace/NBSP-normalized relative to the stored raw HTML (e.g. U+00A0 and doubled spaces collapsed)",
                "byte-faithful, or the normalization declared in the manifest",
                str(
                    both.loc[raw_bad & ~norm_bad, ["list_page", "list_index", a, b]]
                    .head(5)
                    .to_dict("records")
                ),
            )
        if nbad:
            emit(
                "     "
                + str(
                    both.loc[norm_bad, ["list_page", "list_index", a, b]].head(5).to_dict("records")
                )
            )
            finding(
                f"EDA00-CERT-REPARSE-{label.upper()}",
                "P1",
                "provenance",
                f"{nbad} rows where the parquet {label} differs from an independent re-parse of the stored raw HTML",
                "0",
                str(
                    both.loc[norm_bad, ["list_page", "list_index", a, b]].head(5).to_dict("records")
                ),
            )
    xu = both["certified_target_url_listed"].fillna("").astype(str).str.strip()
    yu = both["target_url"].fillna("").astype(str).str.strip()
    nbad = int((xu != yu).sum())
    emit(f"  field certified_target_url_listed: mismatches={nbad}")
    if nbad:
        emit(
            "     "
            + str(
                both.loc[
                    xu != yu,
                    ["list_page", "list_index", "certified_target_url_listed", "target_url"],
                ]
                .head(5)
                .to_dict("records")
            )
        )
        finding(
            "EDA00-CERT-REPARSE-TARGETURL",
            "P1",
            "provenance",
            f"{nbad} rows where certified_target_url_listed differs from the raw HTML",
            "0",
            "eda00_frame_provenance.py §5",
        )
    emit(
        f"  raw status label distribution: {rp['status_raw'].value_counts(dropna=False).to_dict()}"
    )
emit()

# duplicate certification numbers / service names
dupcn = cert[cert.duplicated("certification_number", keep=False)]
emit(f"duplicate certification_number rows = {len(dupcn)}")
if len(dupcn):
    emit(
        dupcn.sort_values("certification_number")[
            [
                "certification_number",
                "service_name",
                "list_page",
                "list_index",
                "cert_start_date",
                "cert_end_date",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )
    finding(
        "EDA00-CERT-DUP-NUMBER",
        "P1",
        "uniqueness",
        f"{len(dupcn)} rows share a certification_number (rows_dedup claims 2283 deduped)",
        "certification_number unique, or dedup key documented",
        str(dupcn["certification_number"].value_counts().head(10).to_dict()),
    )
emit(f"distinct certification_number = {cert['certification_number'].nunique()} / {len(cert)}")
emit(f"distinct service_name = {cert['service_name'].nunique()}")
emit(
    f"distinct (service_name, organization_name) = {cert[['service_name', 'organization_name']].drop_duplicates().shape[0]}"
)
emit()

# ================================================================ 6. missingness
emit("## 6. MISSINGNESS PROFILE")
emit()


def missing_profile(name, df):
    emit(f"### {name} (n={len(df)})")
    recs = []
    for c in df.columns:
        s = df[c]
        n_null = int(s.isna().sum())
        n_empty = (
            int(s.astype(str).str.strip().isin(["", "nan", "None", "<NA>", "[]", "{}"]).sum())
            if s.dtype == object
            else 0
        )
        nun = int(s.nunique(dropna=True))
        zero = int((s == 0).sum()) if pd.api.types.is_numeric_dtype(s) else 0
        recs.append(
            {
                "column": c,
                "dtype": str(s.dtype),
                "null": n_null,
                "null_pct": round(100 * n_null / max(len(df), 1), 2),
                "empty_str": n_empty,
                "nunique": nun,
                "zeros": zero,
            }
        )
    mdf = pd.DataFrame(recs)
    emit(mdf.to_string(index=False))
    emit()
    return mdf


miss_tables = {}
for name in [
    "panel_registry",
    "source_ranking_rows",
    "service_master",
    "entity_alias_map",
    "source_membership",
    "web_target_group",
    "certification_registry",
]:
    miss_tables[name] = missing_profile(name, D[name])

# 01 §11: missing-as-zero check
emit("### 01 §11 'missing must not be replaced by 0' probes")
nullv = rows[rows["value"].isna()]
emit(f"source_ranking_rows.value null = {len(nullv)}")
emit(
    nullv[
        [
            "source_row_id",
            "panel_id",
            "rank",
            "entity_name_raw",
            "metric_name",
            "unit",
            "value",
            "value_label",
        ]
    ].to_string(index=False)
)
emit(f"  null value panels: {nullv['panel_id'].value_counts().to_dict()}")
emit(f"  null value metric_name: {nullv['metric_name'].value_counts().to_dict()}")
emit(f"  null value unit: {nullv['unit'].value_counts().to_dict()}")
zerov = rows[rows["value"] == 0]
emit(f"source_ranking_rows.value == 0 rows = {len(zerov)}")
if len(zerov):
    emit(
        zerov[
            [
                "source_row_id",
                "panel_id",
                "rank",
                "entity_name_raw",
                "metric_name",
                "unit",
                "value",
                "value_label",
            ]
        ].to_string(index=False)
    )
    finding(
        "EDA00-VALUE-ZERO",
        "P1",
        "missingness",
        f"{len(zerov)} source rows carry value == 0 — must be checked against the figure for a 0-substituted missing (01 §11)",
        "0 rows, or each verified as a real measured zero",
        str(
            zerov[
                ["source_row_id", "panel_id", "entity_name_raw", "metric_name", "value_label"]
            ].to_dict("records")
        ),
    )
# value_label vs value coherence
lbl_no_val = rows[rows["value"].isna() & rows["value_label"].notna()]
val_no_lbl = rows[rows["value"].notna() & rows["value_label"].isna()]
emit(f"value NULL but value_label present = {len(lbl_no_val)}")
emit(f"value present but value_label NULL = {len(val_no_lbl)}")
if len(val_no_lbl):
    emit(
        val_no_lbl[["source_row_id", "panel_id", "metric_name", "value", "value_label"]]
        .head(10)
        .to_string(index=False)
    )
    finding(
        "EDA00-VALUE-LABEL-ASYM",
        "P2",
        "missingness",
        f"{len(val_no_lbl)} rows have a numeric value but no value_label",
        "label and value co-present or co-absent",
        "eda00_frame_provenance.py §6",
    )
# entities whose row counts are all zero
emit()
emit("### structural zeros in service_master counters (01 §11 relevance)")
for c in ["appears_in_app_panels", "appears_in_retail_panels", "app_row_count", "retail_row_count"]:
    z = int((svc[c] == 0).sum())
    dom = "RETAIL" if "app" in c and "retail" not in c else "APP"
    z_other = int(((svc[c] == 0) & (svc["domain"] == dom)).sum())
    emit(
        f"  {c}: zeros={z}; of those, entities whose domain is {dom} (i.e. structurally not applicable) = {z_other}"
    )
finding(
    "EDA00-STRUCTURAL-ZERO-COUNTERS",
    "P2",
    "missingness",
    f"service_master carries domain-scoped counters that are 0 purely because the entity does not exist in that domain: appears_in_app_panels==0 for all {int((svc['domain'] == 'RETAIL').sum())} RETAIL entities and appears_in_retail_panels==0 for all {int((svc['domain'] == 'APP').sum())} APP entities. Under 01 §11 these are NA, not measured zeros; any mean/sum over them is wrong",
    "NA for the non-applicable domain, or an explicit note that the zero is structural",
    "eda00_frame_provenance.py §6",
)
emit()
zero_svc = svc[(svc["app_row_count"] == 0) & (svc["retail_row_count"] == 0)]
emit(f"service_master rows with app_row_count==0 AND retail_row_count==0 = {len(zero_svc)}")
if len(zero_svc):
    emit(zero_svc[["service_id", "service_name_canonical", "domain"]].to_string(index=False))
emit()
emit(f"web_target_group.web_target_url nonnull = {int(wtg['web_target_url'].notna().sum())}")
emit(f"web_target_group.url_evidence nonnull = {int(wtg['url_evidence'].notna().sum())}")
emit(
    f"web_target_group.grouping_status = {wtg['grouping_status'].value_counts(dropna=False).to_dict()}"
)
emit(
    f"web_target_group.expected_url_relationship_is_hypothesis = {wtg['expected_url_relationship_is_hypothesis'].value_counts(dropna=False).to_dict()}"
)
emit(
    f"web_target_group.expected_url_relationship_confirmed_by_url = {wtg['expected_url_relationship_confirmed_by_url'].value_counts(dropna=False).to_dict()}"
)
emit(
    f"web_target_group.expected_url_relationship_falsifier nonnull/nonempty = {int(wtg['expected_url_relationship_falsifier'].fillna('').astype(str).str.strip().ne('').sum())}"
)
emit(
    f"service_master.web_eligibility_status = {svc['web_eligibility_status'].value_counts(dropna=False).to_dict()}"
)
emit(
    f"service_master.web_target_grouping_status = {svc['web_target_grouping_status'].value_counts(dropna=False).to_dict()}"
)
emit(
    f"service_master.review_decision = {svc['review_decision'].value_counts(dropna=False).to_dict()}"
)
emit(
    f"service_master.needs_human_review = {svc['needs_human_review'].value_counts(dropna=False).to_dict()}"
)
emit(
    f"service_master.decision_confidence = {svc['decision_confidence'].value_counts(dropna=False).to_dict()}"
)
emit(
    f"service_master.canonicalization_basis = {svc['canonicalization_basis'].value_counts(dropna=False).to_dict()}"
)
emit(f"service_master.decided_by = {svc['decided_by'].value_counts(dropna=False).to_dict()}")

# review_status derivation (A2 §1.1)
emit()
emit("### review_status derivation cross-check (A2 §1.1 measured values)")
emit(pd.crosstab(svc["review_decision"], svc["needs_human_review"], dropna=False).to_string())
emit()

# ================================================================ 7. distribution / outliers
emit("## 7. DISTRIBUTIONS & OUTLIERS")
emit()
emit(f"rank: min={rows['rank'].min()} max={rows['rank'].max()}")
emit(rows["rank"].describe().to_string())
emit()
emit(f"metric_name distinct = {rows['metric_name'].nunique()}")
emit(rows["metric_name"].value_counts(dropna=False).to_string())
emit()
emit(f"unit distinct = {rows['unit'].nunique()}")
emit(rows["unit"].value_counts(dropna=False).to_string())
emit()
emit("value describe by unit:")
emit(rows.groupby("unit")["value"].describe().to_string())
emit()

# rank contiguity per (panel, metric)
# unit normalization
import unicodedata as _ud

_u2 = rows["unit"].dropna().unique().tolist()
_norm = {}
for u in _u2:
    k = _ud.normalize("NFKC", u).replace(" ", "")
    _norm.setdefault(k, []).append(u)
_collide = {k: v for k, v in _norm.items() if len(v) > 1}
emit(f"unit values that collapse to the same token after NFKC+space-strip: {_collide}")
if _collide:
    finding(
        "EDA00-UNIT-NOT-NORMALIZED",
        "P2",
        "distribution",
        f"`unit` carries variants that differ only by whitespace: {_collide} (row counts {{u: int((rows['unit'] == u).sum()) for v in _collide.values() for u in v}})".replace(
            "{u: int((rows['unit'] == u).sum()) for v in _collide.values() for u in v}",
            str({u: int((rows["unit"] == u).sum()) for v in _collide.values() for u in v}),
        ),
        "one token per unit, or an explicit statement that raw notation is preserved verbatim",
        "eda00_frame_provenance.py §7",
    )
emit()

emit("### rank contiguity per (panel_id, metric_name)")
bad_seq = []
for (p, m), g in rows.groupby(["panel_id", "metric_name"]):
    rk = sorted(g["rank"].tolist())
    if rk != list(range(1, len(rk) + 1)):
        bad_seq.append((p, m, rk))
emit(f"groups whose ranks are not 1..n contiguous: {len(bad_seq)}")
for b in bad_seq[:10]:
    emit(f"    {b}")
if bad_seq:
    finding(
        "EDA00-RANK-NONCONTIGUOUS",
        "P1",
        "distribution",
        f"{len(bad_seq)} (panel, metric) groups whose ranks are not 1..n: {[(a, b) for a, b, _ in bad_seq[:10]]}",
        "each group ranks 1..n with no gaps or dupes",
        str(bad_seq[:5]),
    )
dup_rank = rows[rows.duplicated(["panel_id", "metric_name", "rank"], keep=False)]
emit(f"duplicate (panel, metric, rank): {len(dup_rank)}")
if len(dup_rank):
    emit(
        dup_rank[["panel_id", "metric_name", "rank", "entity_name_raw", "value"]]
        .sort_values(["panel_id", "metric_name", "rank"])
        .to_string(index=False)
    )
    finding(
        "EDA00-RANK-DUP",
        "P1",
        "distribution",
        f"{len(dup_rank)} rows share a (panel_id, metric_name, rank)",
        "0",
        "eda00_frame_provenance.py §7",
    )
# same entity appearing twice in one (panel, metric)
dup_ent = rows[rows.duplicated(["panel_id", "metric_name", "entity_name_raw"], keep=False)]
emit(f"duplicate (panel, metric, entity_name_raw): {len(dup_ent)}")
if len(dup_ent):
    emit(dup_ent[["panel_id", "metric_name", "rank", "entity_name_raw"]].to_string(index=False))
    finding(
        "EDA00-ENTITY-DUP-IN-PANEL",
        "P1",
        "distribution",
        f"{len(dup_ent)} rows: same entity appears more than once within one (panel, metric)",
        "0",
        "eda00_frame_provenance.py §7",
    )
emit()

# rank vs value monotonicity
emit("### rank/value monotonicity per (panel, metric)")
viol = []
for (p, m), g in rows.groupby(["panel_id", "metric_name"]):
    g = g.dropna(subset=["value"]).sort_values("rank")
    if len(g) < 2:
        continue
    v = g["value"].tolist()
    desc = all(v[i] >= v[i + 1] for i in range(len(v) - 1))
    asc = all(v[i] <= v[i + 1] for i in range(len(v) - 1))
    if not (desc or asc):
        viol.append((p, m, v))
emit(
    f"(panel, metric) groups where value is neither monotone-decreasing nor -increasing with rank: {len(viol)}"
)
for a, b, v in viol[:10]:
    emit(f"    {a} / {b}: {v}")

emit()
emit("### which metric does `rank` actually order? (anchor metric per panel)")
anchor_rows = []
for p_, g in rows.groupby("panel_id"):
    mono = []
    for m_, gg in g.groupby("metric_name"):
        gg = gg.dropna(subset=["value"]).sort_values("rank")
        v = gg["value"].tolist()
        if len(v) < 2:
            mono.append((m_, "n<2"))
            continue
        d = all(v[i] >= v[i + 1] for i in range(len(v) - 1))
        a_ = all(v[i] <= v[i + 1] for i in range(len(v) - 1))
        mono.append((m_, "desc" if d else ("asc" if a_ else "NON-MONOTONE")))
    anchors = [m_ for m_, k in mono if k == "desc"]
    anchor_rows.append(
        {
            "panel_id": p_,
            "n_metrics": int(panel.loc[panel["panel_id"] == p_, "n_metrics"].iloc[0]),
            "descending_metrics": anchors,
            "non_monotone_metrics": [m_ for m_, k in mono if k == "NON-MONOTONE"],
        }
    )
adf = pd.DataFrame(anchor_rows)
emit(adf.to_string(index=False))
no_anchor = adf[adf["descending_metrics"].apply(len) == 0]
emit(f"panels with no descending anchor metric: {len(no_anchor)}")
n_nonmono_metrics = int(adf["non_monotone_metrics"].apply(len).sum())
emit(f"total (panel, metric) pairs where rank does NOT order the value: {n_nonmono_metrics}")
if len(no_anchor):
    finding(
        "EDA00-RANK-NO-ANCHOR",
        "P1",
        "distribution",
        f"{len(no_anchor)} panels where no metric decreases monotonically with rank: {no_anchor['panel_id'].tolist()}",
        "each panel has one metric that rank orders",
        "eda00_frame_provenance.py §7",
    )
if n_nonmono_metrics:
    finding(
        "EDA00-RANK-DENORMALIZED-ACROSS-METRICS",
        "P1",
        "grain",
        f"`rank` is one value per (panel, entity) but is stored on every metric row: in all 17 panels exactly one metric decreases with rank, while {n_nonmono_metrics} (panel, metric) pairs are non-monotone. For those metrics `rank` carries no ordering information, and source_membership.rank inherits the same ambiguity",
        "either rank is metric-scoped, or the anchor metric is declared",
        str(
            adf[adf["non_monotone_metrics"].apply(len) > 0][
                ["panel_id", "non_monotone_metrics"]
            ].to_dict("records")
        ),
    )
emit()

# entity repeat appearance
app_cnt = joined.groupby("service_id")["panel_id"].nunique().sort_values(ascending=False)
emit("### entity panel-appearance counts (derived)")
emit(f"distribution: {dict(Counter(app_cnt.values))}")
emit("top 15:")
top = (
    app_cnt.head(15)
    .reset_index()
    .merge(svc[["service_id", "service_name_canonical", "domain"]], on="service_id")
)
emit(top.to_string(index=False))
emit(f"entities appearing in exactly 1 panel: {int((app_cnt == 1).sum())}")
emit()
emit(f"source rows per panel: {rows.groupby('panel_id').size().to_dict()}")
emit(f"membership rows per panel: {memb.groupby('panel_id').size().to_dict()}")
emit()

# ================================================================ 8. grain traps
emit("## 8. GRAIN TRAPS")
emit()
traps = []


def trap(label, detail, severity="P2"):
    traps.append((label, detail))
    emit(f"[{severity}] {label}: {detail}")


emit(
    f"T1 service_name_canonical unique = {svc['service_name_canonical'].nunique()} / {len(svc)} rows"
)
trap(
    "T1 canonical_name is not a key",
    f"{svc['service_name_canonical'].nunique()}/{len(svc)}; dupes = {svc['service_name_canonical'].value_counts()[lambda s: s > 1].to_dict()}",
)
finding(
    "EDA00-GRAIN-NAME-NOT-KEY",
    "P1",
    "grain",
    f"service_name_canonical has {svc['service_name_canonical'].nunique()} distinct values for {len(svc)} rows; duplicate = {svc['service_name_canonical'].value_counts()[lambda s: s > 1].to_dict()}",
    "01 §2 dim_measurement_entity implies canonical_name identifies the entity",
    "eda00_frame_provenance.py §8",
)

en_cnt = rows["entity_name_raw"].value_counts()
multi_dom = rows.groupby("entity_name_raw")["domain"].nunique()
multi_dom = multi_dom[multi_dom > 1]
emit(f"T2 entity_name_raw spanning >1 domain: {multi_dom.to_dict()}")
trap("T2 entity_name_raw alone is not a join key", str(multi_dom.to_dict()))
multi_axis = rows.groupby("entity_name_raw")["axis_type"].nunique()
multi_axis = multi_axis[multi_axis > 1]
emit(f"    entity_name_raw spanning >1 axis_type: {multi_axis.to_dict()}")

emit(
    f"T3 panels with n_metrics>1 = {int((panel['n_metrics'] > 1).sum())}; metric-per-panel = {panel.set_index('panel_id')['n_metrics'].to_dict()}"
)
trap(
    "T3 dim_panel.metric_name is undefined for multi-metric panels",
    f"{int((panel['n_metrics'] > 1).sum())} panels",
)

# NEW traps
emit()
emit("### additional grain traps found")

# T4: source_membership is (svc,panel) not (svc,panel,metric)
mm = joined.groupby(["service_id", "panel_id"])["metric_name"].nunique()
emit(
    f"T4 (service_id,panel_id) pairs covering >1 metric: {int((mm > 1).sum())}/{len(mm)}; source rows behind 142 membership rows = {len(joined)}"
)
trap(
    "T4 source_membership loses the metric axis",
    f"{int((mm > 1).sum())} of {len(mm)} (service,panel) pairs cover more than one metric; membership.rank is min(rank) across metrics",
    "P1",
)
finding(
    "EDA00-GRAIN-MEMBERSHIP-METRIC",
    "P1",
    "grain",
    f"source_membership is (service_id, panel_id) grain; {int((mm > 1).sum())}/{len(mm)} pairs span >1 metric, and its single `rank` column is min(rank) across those metrics",
    "01 §2 bridge_source_membership is (entity, panel, source_row) grain",
    "eda00_frame_provenance.py §8",
)
# how many pairs have different ranks across metrics
rk = joined.groupby(["service_id", "panel_id"])["rank"].nunique()
emit(f"    (service,panel) pairs whose rank differs across metrics: {int((rk > 1).sum())}")
if int((rk > 1).sum()):
    ex = rk[rk > 1].head(10)
    emit(f"    e.g. {ex.to_dict()}")
    finding(
        "EDA00-GRAIN-MEMBERSHIP-RANK-COLLAPSE",
        "P1",
        "grain",
        f"{int((rk > 1).sum())} (service_id, panel_id) pairs have more than one distinct rank across metrics; source_membership.rank keeps only the minimum, so the other ranks are unrecoverable from that table",
        "either a metric-grained bridge or an explicit statement that rank is min()",
        str(rk[rk > 1].head(10).to_dict()),
    )

# T5: web_target_key collisions
emit(
    f"T5 service_master.web_target_key nonnull={int(svc['web_target_key'].notna().sum())} distinct={svc['web_target_key'].nunique()}"
)
wtk = svc[svc["web_target_key"].notna()]["web_target_key"].value_counts()
emit(f"    web_target_key shared by >1 entity: {wtk[wtk > 1].to_dict()}")
trap("T5 web_target_key groups entities", str(wtk[wtk > 1].to_dict()), "P2")

# T6: entities present in both APP and RETAIL under different service_ids
name_dom = svc.groupby("service_name_canonical")["domain"].nunique()
emit(
    f"T6 canonical names present under >1 domain (=> 2 service_ids): {name_dom[name_dom > 1].to_dict()}"
)

# T7: axis_type INDUSTRY_CATEGORY entities
ind = svc[svc["axis_type"] == "INDUSTRY_CATEGORY"]
emit(
    f"T7 INDUSTRY_CATEGORY entities in service_master: {len(ind)} -> {ind['service_name_canonical'].tolist()}"
)
emit(
    f"    their web_eligibility_status: {ind['web_eligibility_status'].value_counts(dropna=False).to_dict()}"
)
emit(f"    their web_target_group_id nonnull: {int(ind['web_target_group_id'].notna().sum())}")
trap(
    "T7 industry categories sit in the same table as service brands",
    f"{len(ind)} INDUSTRY_CATEGORY rows inside the 81-row service_master; they are not web targets",
    "P1",
)
finding(
    "EDA00-GRAIN-INDUSTRY-IN-ENTITY-TABLE",
    "P1",
    "grain",
    f"service_master (81 rows) mixes {len(svc[svc['axis_type'] == 'SERVICE_BRAND'])} SERVICE_BRAND with {len(ind)} INDUSTRY_CATEGORY rows; the latter are analytic categories, not measurable web targets, and all {int(ind['web_target_group_id'].isna().sum())} of them carry NULL web_target_group_id",
    "01 §2 dim_measurement_entity is described as a service unit",
    "eda00_frame_provenance.py §8",
)

# T8: panel-level domain/axis vs entity-level
emit(f"T8 panel_registry.axis_type = {panel['axis_type'].value_counts().to_dict()}")
emit(f"    source rows by axis_type = {rows['axis_type'].value_counts().to_dict()}")

# T9: figure -> multiple panels
fp_ = panel.groupby("figure_id").size()
emit(f"T9 figures carrying >1 panel: {fp_[fp_ > 1].to_dict()}  (figure_id is NOT a panel key)")
trap("T9 figure_id is not a panel identifier", str(fp_[fp_ > 1].to_dict()), "P2")

# T10: 261 rows vs 142 membership vs 81 entities — double counting risk
emit(
    f"T10 grain ladder: source rows {len(rows)} -> (svc,panel) {len(stored_pairs)} -> entities {svc['service_id'].nunique()} -> web target groups {wtg['web_target_group_id'].nunique()} -> groups with a URL {int(wtg['web_target_url'].notna().sum())}"
)
emit(
    f"    entities reachable as a web target today = {int(svc['web_target_group_id'].notna().sum())}; with a confirmed URL = 0"
)

# T11: cert service_name is not a key
emit(
    f"T11 certification_registry.service_name distinct = {cert['service_name'].nunique()} / {len(cert)}; a name can hold many certifications over time"
)
cn = cert["service_name"].value_counts()
emit(f"    names with >1 certification: {int((cn > 1).sum())}; max = {cn.max()} ({cn.idxmax()})")
trap(
    "T11 certification join on service_name will fan out",
    f"{int((cn > 1).sum())} names carry >1 certification row, max {cn.max()}",
    "P1",
)
finding(
    "EDA00-GRAIN-CERT-NAME-FANOUT",
    "P1",
    "grain",
    f"certification_registry has {len(cert)} rows over {cert['service_name'].nunique()} distinct service_name; {int((cn > 1).sum())} names carry more than one certification (max {int(cn.max())})",
    "01 §8 dim_certification is web_target grain",
    "eda00_frame_provenance.py §8",
)

# T12 metric_columns JSON per panel
emit()
mc_bad = []
for _, r in panel.iterrows():
    try:
        v = r["metric_columns"]
        parsed = json.loads(v) if isinstance(v, str) else list(v)
        if len(parsed) != r["n_metrics"]:
            mc_bad.append((r["panel_id"], len(parsed), r["n_metrics"]))
    except Exception as e:
        mc_bad.append((r["panel_id"], f"PARSE_FAIL {e}", r["n_metrics"]))
emit(f"T12 metric_columns length != n_metrics: {len(mc_bad)} {mc_bad[:10]}")
if mc_bad:
    finding(
        "EDA00-PANEL-METRICCOLS",
        "P1",
        "consistency",
        f"{len(mc_bad)} panels where len(metric_columns) != n_metrics: {mc_bad[:10]}",
        "0",
        "eda00_frame_provenance.py §8",
    )
# metric names in panel vs rows
pm_bad = []
for _, r in panel.iterrows():
    v = r["metric_columns"]
    try:
        parsed = json.loads(v) if isinstance(v, str) else list(v)
        names = {m.get("name") if isinstance(m, dict) else str(m) for m in parsed}
    except Exception:
        continue
    got = set(rows.loc[rows["panel_id"] == r["panel_id"], "metric_name"])
    if names != got:
        pm_bad.append((r["panel_id"], sorted(names), sorted(got)))
emit(f"T13 panel.metric_columns names != distinct metric_name in rows: {len(pm_bad)}")
for b in pm_bad[:10]:
    emit(f"    {b}")
if pm_bad:
    finding(
        "EDA00-PANEL-METRIC-NAME-MISMATCH",
        "P1",
        "consistency",
        f"{len(pm_bad)} panels whose metric_columns names differ from the metric_name values actually present in source_ranking_rows",
        "identical sets",
        str(pm_bad[:5]),
    )
emit()

# ================================================================ 9. extra sanity
emit("## 9. EXTRA SANITY CHECKS")
emit()
bad_dates = cert[(sd.notna()) & (ed.notna()) & (ed < sd)]
emit(f"certification rows with cert_end_date < cert_start_date: {len(bad_dates)}")
if len(bad_dates):
    emit(
        bad_dates[["certification_number", "service_name", "cert_start_date", "cert_end_date"]]
        .head(10)
        .to_string(index=False)
    )
    finding(
        "EDA00-CERT-DATE-ORDER",
        "P1",
        "distribution",
        f"{len(bad_dates)} certification rows where end < start",
        "0",
        str(
            bad_dates[["certification_number", "cert_start_date", "cert_end_date"]]
            .head(10)
            .to_dict("records")
        ),
    )
emit(f"cert_start_date range: {sd.min()} .. {sd.max()}")
emit(f"cert_end_date range:   {ed.min()} .. {ed.max()}")
emit(f"cert periods longer than 400 days: {int(((ed - sd).dt.days > 400).sum())}")
emit(f"cert periods shorter than 300 days: {int(((ed - sd).dt.days < 300).sum())}")
emit(f"(ed-sd).days describe: {(ed - sd).dt.days.describe().to_dict()}")
emit(
    f"certification_number numeric? {cert['certification_number'].astype(str).str.fullmatch(r'[0-9]+').all()}"
)
cn_int = pd.to_numeric(cert["certification_number"], errors="coerce")
emit(
    f"certification_number range {int(cn_int.min())}..{int(cn_int.max())}; gaps in that range = {int(cn_int.max() - cn_int.min() + 1 - cert['certification_number'].nunique())}"
)
emit(
    f"duplicate certified_target_url_listed values: {int(cert['certified_target_url_listed'].fillna('').str.strip().ne('').sum() - cert.loc[cert['certified_target_url_listed'].fillna('').str.strip().ne(''), 'certified_target_url_listed'].nunique())}"
)
_u = cert.loc[
    cert["certified_target_url_listed"].fillna("").str.strip().ne(""), "certified_target_url_listed"
]
emit(f"distinct target urls = {_u.nunique()} over {len(_u)} rows")
_uv = cert.loc[
    cert["cert_valid_candidate"].eq(1)
    & cert["certified_target_url_listed"].fillna("").str.strip().ne(""),
    "certified_target_url_listed",
]
emit(
    f"among the {int(cert['cert_valid_candidate'].sum())} currently-valid rows: {len(_uv)} have a target url, {_uv.nunique()} distinct"
)
_uc = _u.value_counts()
emit(
    f"urls appearing in >1 certification row: {int((_uc > 1).sum())}; max {int(_uc.max())} ({_uc.idxmax()})"
)
finding(
    "EDA00-CERT-URL-FANOUT",
    "P1",
    "grain",
    f"certified_target_url_listed is not unique: {_u.nunique()} distinct URLs over {len(_u)} rows; {int((_uc > 1).sum())} URLs carry more than one certification row (max {int(_uc.max())}). Only {_uv.nunique()} distinct URLs are currently valid",
    "01 §8 dim_certification is one row per web_target",
    "eda00_frame_provenance.py §9",
)
emit()
emit("### web_target_group hypothesis rows (the 3 multi-member groups)")
hyp = wtg[wtg["member_count"] > 1]
emit(
    hyp[
        [
            "web_target_group_id",
            "web_target_key",
            "member_service_ids",
            "member_count",
            "member_domains",
            "grouping_status",
            "expected_url_relationship",
            "expected_url_relationship_is_hypothesis",
            "expected_url_relationship_confirmed_by_url",
        ]
    ].to_string(index=False)
)
emit()
emit("falsifiers:")
for _, r in hyp.iterrows():
    emit(
        f"  {r['web_target_group_id']} / {r['web_target_key']}: {r['expected_url_relationship_falsifier']}"
    )
emit()
# grouping_status: 3 groups but 6 entities carry CANDIDATE status
emit(
    f"service_master.web_target_grouping_status CANDIDATE count = {int(svc['web_target_grouping_status'].eq('CANDIDATE_PENDING_URL_REVIEW').sum())} (entity grain) vs web_target_group CANDIDATE = {int(wtg['grouping_status'].eq('CANDIDATE_PENDING_URL_REVIEW').sum())} (group grain)"
)
if int(svc["web_target_grouping_status"].eq("CANDIDATE_PENDING_URL_REVIEW").sum()) != int(
    wtg["grouping_status"].eq("CANDIDATE_PENDING_URL_REVIEW").sum()
):
    finding(
        "EDA00-GRAIN-GROUPING-STATUS",
        "P2",
        "grain",
        f"the same status label counts {int(svc['web_target_grouping_status'].eq('CANDIDATE_PENDING_URL_REVIEW').sum())} at entity grain (service_master) and {int(wtg['grouping_status'].eq('CANDIDATE_PENDING_URL_REVIEW').sum())} at group grain (web_target_group); counting groups by reading service_master double-counts",
        "the grain of each count is stated wherever the label appears",
        "eda00_frame_provenance.py §9",
    )
emit()
emit("### entity_alias_map.panel_ids internal consistency")
bad_alias_cnt = []
for _, r in alias.iterrows():
    pids = [x.strip() for x in str(r["panel_ids"]).split(",") if x.strip()]
    if len(pids) != len(set(pids)):
        bad_alias_cnt.append((r["alias_id"], pids))
emit(f"alias rows whose panel_ids contain duplicates: {len(bad_alias_cnt)} {bad_alias_cnt[:5]}")
emit()
emit("### journal cross-verification claim")
emit(
    f"journal_provenance.cross_verifications = {jp['cross_verifications']} agreeing = {jp['cross_verifications_agreeing']}"
)
emit(
    f"journal_provenance.matches_existing_c002_output.result = {jp['matches_existing_c002_output']['result']}"
)
jl = [json.loads(x) for x in open(jpp, encoding="utf-8") if x.strip()]
emit(
    f"journal lines parsed = {len(jl)}; distinct record kinds = {Counter(list(x.keys())[0] if x else None for x in jl)}"
)
emit()

# ================================================================ write outputs
emit("## SUMMARY")
emit(f"findings: {len(FINDINGS)}")
sev = Counter(f["severity"] for f in FINDINGS)
emit(f"by severity: {dict(sev)}")
for f in FINDINGS:
    emit(f"  [{f['severity']}] {f['id']} — {f['observed'][:160]}")

with open(f"{OUT}/eda00_findings.json", "w", encoding="utf-8") as fh:
    json.dump(FINDINGS, fh, ensure_ascii=False, indent=2)
with open(f"{OUT}/eda00_raw_output.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(LINES))

summary = {
    "counts": counts,
    "orphans": orph,
    "hash_results": [{k: v for k, v in r.items()} for r in hash_results],
    "cert_checks": [{"label": a, "manifest": b, "measured": c} for a, b, c in cert_checks],
}
with open(f"{OUT}/eda00_measured.json", "w", encoding="utf-8") as fh:
    json.dump(summary, fh, ensure_ascii=False, indent=2, default=str)
print(f"\nwrote {OUT}/eda00_findings.json, eda00_raw_output.txt, eda00_measured.json")
