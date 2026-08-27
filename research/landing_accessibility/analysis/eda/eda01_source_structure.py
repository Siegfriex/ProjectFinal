#!/usr/bin/env python
# ruff: noqa: E402, B905, E712
# 이 파일은 라이브러리가 아니라 **1회성 분석 스크립트**다 — top-level 절차 코드이며
# 재실행 산출물의 바이트 동일성이 검증 기준이다. 위 규칙들을 기계적으로 고치면
# 검증된 산출물이 바뀔 위험만 있고 얻는 것이 없다. 규칙을 끄는 범위는 이 파일뿐이다.
"""EDA-01 -- Wiseapp Source Structure (P-A A3).

READ-ONLY. Reads only research/landing_accessibility/state/*.parquet.
Writes only under analysis/out/eda01 (or $EDA01_OUT).

All numbers printed by this script are computed here, not copied from docs.
Observation only -- no accessibility / certification interpretation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

# 이 파일이 사는 워크트리를 읽는다. 다른 워크트리 하드코딩 금지(SHADOW lane 격리).
RESEARCH_ROOT = Path(
    os.environ.get("LANDING_RESEARCH_ROOT", str(Path(__file__).resolve().parents[2]))
)
STATE = Path(os.environ.get("LANDING_STATE_DIR", str(RESEARCH_ROOT / "state")))
OUT = Path(os.environ.get("EDA01_OUT", str(RESEARCH_ROOT / "analysis" / "out" / "eda01")))
FIGS = OUT / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 400)

REPORT: list[str] = []


def say(*parts: object) -> None:
    line = " ".join(str(p) for p in parts)
    print(line)
    REPORT.append(line)


def head(title: str) -> None:
    say("")
    say("=" * 78)
    say(title)
    say("=" * 78)


# ---------------------------------------------------------------- load
panel = pd.read_parquet(STATE / "panel_registry.parquet")
rows = pd.read_parquet(STATE / "source_ranking_rows.parquet")
svc = pd.read_parquet(STATE / "service_master.parquet")
memb = pd.read_parquet(STATE / "source_membership.parquet")
alias = pd.read_parquet(STATE / "entity_alias_map.parquet")
wtg = pd.read_parquet(STATE / "web_target_group.parquet")

head("0. SHAPES")
for nm, df in [
    ("panel_registry", panel),
    ("source_ranking_rows", rows),
    ("service_master", svc),
    ("source_membership", memb),
    ("entity_alias_map", alias),
    ("web_target_group", wtg),
]:
    say(f"{nm:24s} rows={len(df):5d} cols={df.shape[1]}")

# entity id resolution: (entity_name_raw, domain, axis_type) -> service_id
J = rows.merge(
    alias[["service_id", "entity_name_raw", "domain", "axis_type"]],
    on=["entity_name_raw", "domain", "axis_type"],
    how="left",
    validate="m:1",
)
say(f"resolved source rows = {len(J)}  unmatched service_id = {int(J.service_id.isna().sum())}")

# ============================================================= 1. GRAIN
head("1. GRAIN OF source_ranking_rows -- what is a 'source row'?")
say(
    "dup (panel_id, entity_name_raw, metric_name) =",
    int(rows.duplicated(["panel_id", "entity_name_raw", "metric_name"]).sum()),
)
say(
    "dup (panel_id, service_id) =",
    int(
        J.drop_duplicates(["panel_id", "service_id", "metric_name"])
        .duplicated(["panel_id", "service_id", "metric_name"])
        .sum()
    ),
)
ent_rows_per_panel = J.groupby("panel_id").service_id.nunique()
say("sum of distinct entities over 17 panels =", int(ent_rows_per_panel.sum()))
say("sum of panel_registry.rows_extracted   =", int(panel.rows_extracted.sum()))
say("sum(rows_extracted * n_metrics)        =", int((panel.rows_extracted * panel.n_metrics).sum()))
say("len(source_ranking_rows)               =", len(rows))
say("=> grain(source_ranking_rows) = panel x entity x metric, NOT panel x entity.")
say("   The 142 (entity,panel) memberships expand to 261 rows via 1..4 metrics per panel.")

# ============================================================= 2. PANELS
head("2. PANEL-LEVEL N AND COMPOSITION")
pv = panel.copy()
pv["entities"] = pv.panel_id.map(ent_rows_per_panel).astype(int)
pv["source_rows"] = pv.panel_id.map(J.groupby("panel_id").size()).astype(int)
pv["rows_expected"] = pv["rows_expected"]  # Int64, nullable
pv["exp_vs_extr"] = np.where(
    pv.rows_expected.isna(),
    "EXPECTED_NULL",
    np.where(pv.rows_expected.fillna(-1).astype("int64") == pv.rows_extracted, "MATCH", "MISMATCH"),
)
cols = [
    "panel_id",
    "figure_id",
    "domain",
    "axis_type",
    "source_section",
    "period_axis",
    "rows_expected",
    "rows_extracted",
    "entities",
    "n_metrics",
    "source_rows",
    "row_count_verification",
    "row_count_ok",
    "exp_vs_extr",
    "extraction_confidence",
]
say(pv[cols].to_string(index=False))
say("")
say(
    "rows_expected NULL panels:",
    int(pv.rows_expected.isna().sum()),
    "->",
    sorted(pv.loc[pv.rows_expected.isna(), "panel_id"]),
)
say(
    "rows_expected != rows_extracted (where both present):",
    int((pv.exp_vs_extr == "MISMATCH").sum()),
)
say("row_count_verification:", pv.row_count_verification.value_counts().to_dict())
say("extraction_confidence:", pv.extraction_confidence.value_counts().to_dict())
say("unreadable:", pv.unreadable.value_counts(dropna=False).to_dict())
say(
    "domain:",
    pv.domain.value_counts().to_dict(),
    "| axis_type:",
    pv.axis_type.value_counts().to_dict(),
    "| period_axis:",
    pv.period_axis.value_counts().to_dict(),
)
say("n_metrics distribution:", pv.n_metrics.value_counts().sort_index().to_dict())
say("source_section:", pv.source_section.value_counts().sort_index().to_dict())
say("panel_scope prefix:", pv.panel_scope.str.split(":").str[0].value_counts().to_dict())

head("2b. METRIC / UNIT VOCABULARY (row level)")
say("distinct metric_name =", rows.metric_name.nunique(), "| distinct unit =", rows.unit.nunique())
say(json.dumps(rows.metric_name.value_counts().to_dict(), ensure_ascii=False, indent=0))
say("unit:", json.dumps(rows.unit.value_counts().to_dict(), ensure_ascii=False))
say(
    "value NULL rows =",
    int(rows.value.isna().sum()),
    "-> panels",
    sorted(rows.loc[rows.value.isna(), "panel_id"].unique()),
    "metric",
    sorted(rows.loc[rows.value.isna(), "metric_name"].unique()),
)
say("value_label NULL rows =", int(rows.value_label.isna().sum()))

# ============================================================= 3. ENTITY
head("3. ENTITY REPEAT APPEARANCE")
app_cnt = J.groupby("service_id").panel_id.nunique()
row_cnt = J.groupby("service_id").size()
fig_cnt = J.groupby("service_id").figure_id.nunique()
say("entities =", app_cnt.size)
say("panel appearance count distribution:", app_cnt.value_counts().sort_index().to_dict())
say("  1 panel only:", int((app_cnt == 1).sum()), "| >=2 panels:", int((app_cnt > 1).sum()))
say("figure appearance count distribution:", fig_cnt.value_counts().sort_index().to_dict())
say("source-row count per entity distribution:", row_cnt.value_counts().sort_index().to_dict())
say(
    "appearance count: median",
    float(app_cnt.median()),
    "mean",
    round(float(app_cnt.mean()), 3),
    "max",
    int(app_cnt.max()),
)

name = svc.set_index("service_id")["service_name_canonical"]
key = svc.set_index("service_id")["canonical_service_key"]
dom = svc.set_index("service_id")["domain"]
ax = svc.set_index("service_id")["axis_type"]
top = pd.DataFrame(
    {
        "canonical_key": key,
        "name": name,
        "domain": dom,
        "axis_type": ax,
        "panels": app_cnt,
        "figures": fig_cnt,
        "source_rows": row_cnt,
    }
).sort_values(["panels", "source_rows"], ascending=False)
say("")
say("entities appearing in >= 3 panels:")
say(top[top.panels >= 3].to_string())
say("")
say("appearance count x domain:")
say(pd.crosstab(top.panels, top.domain).to_string())
say("appearance count x axis_type:")
say(pd.crosstab(top.panels, top.axis_type).to_string())

# ============================================================= 4. NORM RANK
head("4. PANEL-NORMALIZED RANK")
say("Definition (this analysis):")
say("  For panel p with N_p = number of distinct entities in p, and raw rank r in 1..N_p,")
say("     norm_rank = (r - 1) / (N_p - 1)        in [0,1], 0 = top of panel, 1 = bottom")
say("     rank_pct  = r / N_p                    in (0,1], share-of-panel position")
say("  norm_rank is UNDEFINED when N_p == 1 (no panel here has N_p == 1).")
say("  Rationale: panels differ in N (3,5,10,15) so raw rank is not comparable across panels.")
say("  This is descriptive only -- it does NOT mean an entity is 'more important'.")

mem = J.drop_duplicates(["panel_id", "service_id"])[
    ["panel_id", "service_id", "domain", "axis_type", "rank"]
].copy()
Np = mem.groupby("panel_id").size().rename("N_p")
mem = mem.merge(Np, on="panel_id")
say("")
say(
    "rank integrity per panel: rank set == 1..N_p for every panel:",
    bool(
        mem.groupby("panel_id")
        .apply(lambda d: sorted(d["rank"]) == list(range(1, len(d) + 1)), include_groups=False)
        .all()
    ),
)
mem["norm_rank"] = (mem["rank"] - 1) / (mem["N_p"] - 1)
mem["rank_pct"] = mem["rank"] / mem["N_p"]
say("memberships =", len(mem))
say("norm_rank describe:")
say(mem.norm_rank.describe().round(4).to_string())
say("norm_rank by domain (median / IQR):")
say(mem.groupby("domain").norm_rank.describe().round(3).to_string())
say("NOTE: because every panel's ranks are exactly 1..N_p, norm_rank is uniform BY")
say("      CONSTRUCTION within each panel. Its distribution is a property of the panel")
say("      size mix, not of the entities. Only the ENTITY-level aggregate below carries")
say("      per-entity information.")

best = mem.groupby("service_id").agg(
    best_norm_rank=("norm_rank", "min"),
    mean_norm_rank=("norm_rank", "mean"),
    best_raw_rank=("rank", "min"),
    panels=("panel_id", "nunique"),
)
best["name"] = name
best["domain"] = dom
say("")
say("entity best_norm_rank describe:")
say(best.best_norm_rank.describe().round(4).to_string())
say(
    "entities with best_norm_rank == 0 (rank 1 in at least one panel):",
    int((best.best_norm_rank == 0).sum()),
)
say(best[best.best_norm_rank == 0].sort_values("panels", ascending=False).to_string())

# ============================================================= 5. DOMAIN
head("5. SOURCE DOMAIN CROSSING")
say("service_master.domain:", svc.domain.value_counts().to_dict())
say("axis_type x domain (entity level):")
say(pd.crosstab(svc.axis_type, svc.domain).to_string())

rec_p = J.groupby(["service_id", "domain"]).panel_id.nunique().unstack(fill_value=0)
rec_r = J.groupby(["service_id", "domain"]).size().unstack(fill_value=0)
chk = svc.set_index("service_id")[
    [
        "appears_in_app_panels",
        "appears_in_retail_panels",
        "app_row_count",
        "retail_row_count",
        "alias_count",
    ]
].copy()
chk["rec_app_panels"] = (
    rec_p.get("APP", pd.Series(0, index=chk.index)).reindex(chk.index).fillna(0).astype(int)
)
chk["rec_ret_panels"] = (
    rec_p.get("RETAIL", pd.Series(0, index=chk.index)).reindex(chk.index).fillna(0).astype(int)
)
chk["rec_app_rows"] = (
    rec_r.get("APP", pd.Series(0, index=chk.index)).reindex(chk.index).fillna(0).astype(int)
)
chk["rec_ret_rows"] = (
    rec_r.get("RETAIL", pd.Series(0, index=chk.index)).reindex(chk.index).fillna(0).astype(int)
)
chk["rec_alias"] = alias.groupby("service_id").size().reindex(chk.index).fillna(0).astype(int)
say("")
say("stored vs reconstructed (mismatch counts):")
for a, b in [
    ("appears_in_app_panels", "rec_app_panels"),
    ("appears_in_retail_panels", "rec_ret_panels"),
    ("app_row_count", "rec_app_rows"),
    ("retail_row_count", "rec_ret_rows"),
    ("alias_count", "rec_alias"),
]:
    bad = chk[a].astype(int) != chk[b].astype(int)
    say(f"  {a:26s} vs {b:16s}: mismatch {int(bad.sum())}")
    if bad.any():
        say(chk.loc[bad, [a, b]].to_string())
say("")
say("IMPORTANT: app_row_count / retail_row_count count SOURCE ROWS (metric-expanded).")
say(
    "  sum(app_row_count) =",
    int(chk.app_row_count.sum()),
    "sum(retail_row_count) =",
    int(chk.retail_row_count.sum()),
    "total =",
    int(chk.app_row_count.sum() + chk.retail_row_count.sum()),
)
say(
    "  sum(appears_in_app_panels) =",
    int(chk.appears_in_app_panels.sum()),
    "sum(appears_in_retail_panels) =",
    int(chk.appears_in_retail_panels.sum()),
    "total =",
    int(chk.appears_in_app_panels.sum() + chk.appears_in_retail_panels.sum()),
)
say("")
say(
    "entities with rows in BOTH domains:",
    int(((chk.rec_app_rows > 0) & (chk.rec_ret_rows > 0)).sum()),
)
say("  -> 0 by construction: `domain` is part of the entity identity key,")
say("     so an APP row and a RETAIL row can never land on the same service_id.")
say("  Cross-domain identity therefore only exists ABOVE the entity level:")
nm_dom = svc.groupby("service_name_canonical").domain.nunique()
say(
    "  canonical NAME present in both domains:",
    int((nm_dom > 1).sum()),
    "->",
    list(nm_dom[nm_dom > 1].index),
)
k_dom = svc.dropna(subset=["web_target_key"]).groupby("web_target_key").domain.nunique()
say(
    "  web_target_key spanning both domains:",
    int((k_dom > 1).sum()),
    "->",
    sorted(k_dom[k_dom > 1].index),
)
say("  service_name_canonical: 81 rows /", svc.service_name_canonical.nunique(), "distinct")
say("  canonical_service_key : 81 rows /", svc.canonical_service_key.nunique(), "distinct")

# ============================================================= 6. ALIAS
head("6. ALIAS STRUCTURE")
say("alias rows =", len(alias), "| distinct service_id =", alias.service_id.nunique())
say("aliases per entity:", alias.groupby("service_id").size().value_counts().to_dict())
say("match_basis:", alias.match_basis.value_counts().to_dict())
say(
    "join key (entity_name_raw, domain, axis_type) duplicates in alias map:",
    int(alias.duplicated(["entity_name_raw", "domain", "axis_type"]).sum()),
)
say(
    "entity_name_raw alone -- duplicated values:",
    sorted(alias.entity_name_raw[alias.entity_name_raw.duplicated(keep=False)].unique()),
)
multi = alias.service_id[alias.service_id.duplicated(keep=False)].unique()
say("")
say("multi-alias entity/entities:")
say(
    alias[alias.service_id.isin(multi)][
        ["alias_id", "service_id", "entity_name_raw", "domain", "panel_ids", "match_basis"]
    ].to_string(index=False)
)
say("reviewer_note:", alias.loc[alias.match_basis == "REVIEWED", "reviewer_note"].iloc[0][:300])
say("")
# alias.panel_ids explode cross-check
ex = alias.assign(pid=alias.panel_ids.str.split(",")).explode("pid")
ex["pid"] = ex["pid"].str.strip()
s_alias = set(map(tuple, ex[["service_id", "pid"]].drop_duplicates().values))
s_join = set(map(tuple, J[["service_id", "panel_id"]].drop_duplicates().values))
s_memb = set(map(tuple, memb[["service_id", "panel_id"]].values))
say(
    "(service_id,panel_id) sets -- alias explode:",
    len(s_alias),
    "| join derived:",
    len(s_join),
    "| source_membership:",
    len(s_memb),
)
say("all three identical:", s_alias == s_join == s_memb)
mm = memb.merge(
    mem[["service_id", "panel_id", "rank"]],
    on=["service_id", "panel_id"],
    suffixes=("_stored", "_derived"),
)
say(
    "source_membership.rank vs derived rank mismatch:",
    int((mm.rank_stored != mm.rank_derived).sum()),
)
mn = memb.merge(panel[["panel_id", "n_metrics"]], on="panel_id", suffixes=("_stored", "_panel"))
say(
    "source_membership.n_metrics vs panel_registry.n_metrics mismatch:",
    int((mn.n_metrics_stored != mn.n_metrics_panel).sum()),
)

# ============================================================= 7. WEB TARGET
head("7. WEB TARGET GROUP STRUCTURE")
say("groups =", len(wtg), "| distinct web_target_group_id =", wtg.web_target_group_id.nunique())
say("member_count distribution:", wtg.member_count.value_counts().sort_index().to_dict())
say("sum(member_count) =", int(wtg.member_count.sum()))
say("grouping_status (GROUP level):", wtg.grouping_status.value_counts().to_dict())
say(
    "service_master.web_target_grouping_status (ENTITY level):",
    svc.web_target_grouping_status.value_counts(dropna=False).to_dict(),
)
say(
    "service_master.web_target_group_id nonnull =",
    int(svc.web_target_group_id.notna().sum()),
    "| null =",
    int(svc.web_target_group_id.isna().sum()),
    "| distinct groups referenced =",
    svc.web_target_group_id.nunique(),
)
say(
    "group ids in web_target_group but not referenced by any entity:",
    len(set(wtg.web_target_group_id) - set(svc.web_target_group_id.dropna())),
)
say(
    "group ids referenced by entities but absent from web_target_group:",
    len(set(svc.web_target_group_id.dropna()) - set(wtg.web_target_group_id)),
)
say("")
say("hypothesis flags:")
say(
    "  expected_url_relationship_is_hypothesis True =",
    int((wtg.expected_url_relationship_is_hypothesis == True).sum()),
    "| notnull =",
    int(wtg.expected_url_relationship_is_hypothesis.notna().sum()),
)
say(
    "  expected_url_relationship_confirmed_by_url True =",
    int((wtg.expected_url_relationship_confirmed_by_url == True).sum()),
)
say(
    "  web_target_url nonnull =",
    int(wtg.web_target_url.notna().sum()),
    "| url_evidence nonnull =",
    int(wtg.url_evidence.notna().sum()),
)
say(
    "  expected_url_relationship values:",
    wtg.expected_url_relationship.value_counts(dropna=False).to_dict(),
)
say("")
say("multi-member groups (the 3 hypotheses):")
for _, r in wtg[wtg.member_count > 1].iterrows():
    say("-" * 70)
    say(
        "group_id :",
        r.web_target_group_id,
        "| key:",
        r.web_target_key,
        "| members:",
        r.member_canonical_keys,
        "| domains:",
        r.member_domains,
    )
    say("relation :", r.expected_url_relationship, "| status:", r.grouping_status)
    say("basis    :", r.expected_url_relationship_basis)
    say("falsifier:", r.expected_url_relationship_falsifier)
    say("risk     :", r.expected_url_relationship_risk)
say("-" * 70)
say(
    "singleton grouping_basis sample:",
    wtg[wtg.member_count == 1].grouping_basis.value_counts().head(3).to_dict(),
)

# ============================================================= 8. INDUSTRY
head("8. INDUSTRY_CATEGORY AXIS -- THE 10 EXCLUDED ENTITIES")
ind = svc[svc.axis_type == "INDUSTRY_CATEGORY"]
say("count =", len(ind))
say(
    ind[
        [
            "service_id",
            "canonical_service_key",
            "service_name_canonical",
            "domain",
            "web_eligibility_status",
            "web_target_group_id",
            "appears_in_retail_panels",
            "retail_row_count",
        ]
    ].to_string(index=False)
)
say("")
say("all 10 come from which panels?")
ind_rows = J[J.service_id.isin(ind.service_id)]
say(
    "  panels:",
    sorted(ind_rows.panel_id.unique()),
    "| source rows:",
    len(ind_rows),
    "| distinct entities:",
    ind_rows.service_id.nunique(),
)
p7 = panel[panel.panel_id == "fig07_t1"].iloc[0]
say(
    "  fig07_t1 axis_type =",
    p7.axis_type,
    "| domain =",
    p7.domain,
    "| period_axis =",
    p7.period_axis,
)
say("  fig07_t1 table_title  :", p7.table_title)
say("  fig07_t1 panel_scope  :", p7.panel_scope)
say("  fig07_t1 universe_def :", str(p7.universe_definition)[:400])
say("")
say("Are these entities EXCLUSIVE to fig07_t1?", bool(ind_rows.panel_id.nunique() == 1))
say(
    "Does any SERVICE_BRAND entity also appear in fig07_t1?",
    int(J[(J.panel_id == "fig07_t1") & (J.axis_type == "SERVICE_BRAND")].service_id.nunique()),
)
say("web_eligibility_status of the 10:", ind.web_eligibility_status.unique().tolist())
say("web_eligibility_basis (verbatim):", ind.web_eligibility_basis.unique().tolist())
say("web_target_group_id null for all 10:", bool(ind.web_target_group_id.isna().all()))
say("")
say("Observation: fig07_t1 is the only panel whose axis_type is INDUSTRY_CATEGORY;")
say("its 10 row labels are industry buckets (edible/appliance/delivery/... categories),")
say("not brands, and the panel_scope says brands were AGGREGATED into industries.")
say("They therefore have no web landing of their own -- no URL can be assigned.")

# ============================================================= 9. TARGETS
head("9. WHAT IS ACTUALLY MAPPABLE (P-A A4/A5 and P-B input counts)")
brand = svc[svc.axis_type == "SERVICE_BRAND"]
say("total entities                       =", len(svc))
say("  minus INDUSTRY_CATEGORY (excluded) =", len(ind))
say("  SERVICE_BRAND entities             =", len(brand))
say("     by domain:", brand.domain.value_counts().to_dict())
say("web_eligibility_status:", svc.web_eligibility_status.value_counts().to_dict())
say("review_decision (raw column):", svc.review_decision.value_counts(dropna=False).to_dict())
say("needs_human_review:", svc.needs_human_review.value_counts(dropna=False).to_dict())
say("canonicalization_basis:", svc.canonicalization_basis.value_counts(dropna=False).to_dict())
say("")
say("web target group cardinality bounds (P-B):")
say("  groups today                       =", len(wtg))
say("  if all 3 SAME_LANDING hypotheses HOLD  -> web targets =", len(wtg))
say("  if all 3 hypotheses are FALSIFIED (SPLIT) -> web targets =", len(brand))
say("  so the P-B target count lies in [", len(wtg), ",", len(brand), "]")
say("")
say("mapping load for representative task (SSOT §6: 1 task per measurement entity):")
say("  entities needing a representative task =", len(brand))
say(
    "  of which appear in >= 2 panels          =",
    int((app_cnt.reindex(brand.service_id).fillna(0) > 1).sum()),
)
say(
    "  of which appear in exactly 1 panel      =",
    int((app_cnt.reindex(brand.service_id).fillna(0) == 1).sum()),
)
say(
    "  entities in a multi-member web target group =",
    int(svc.web_target_group_id.isin(wtg[wtg.member_count > 1].web_target_group_id).sum()),
)

# per-entity export for downstream
entity_tab = pd.DataFrame(
    {
        "service_id": svc.service_id.values,
        "canonical_service_key": svc.canonical_service_key.values,
        "name": svc.service_name_canonical.values,
        "domain": svc.domain.values,
        "axis_type": svc.axis_type.values,
    }
).set_index("service_id")
entity_tab["panels"] = app_cnt.reindex(entity_tab.index).fillna(0).astype(int)
entity_tab["source_rows"] = row_cnt.reindex(entity_tab.index).fillna(0).astype(int)
entity_tab["best_raw_rank"] = best.best_raw_rank.reindex(entity_tab.index)
entity_tab["best_norm_rank"] = best.best_norm_rank.reindex(entity_tab.index).round(4)
entity_tab["mean_norm_rank"] = best.mean_norm_rank.reindex(entity_tab.index).round(4)
entity_tab["web_target_group_id"] = svc.set_index("service_id").web_target_group_id
entity_tab["web_eligibility_status"] = svc.set_index("service_id").web_eligibility_status
entity_tab.sort_values(["panels", "source_rows"], ascending=False).to_csv(
    OUT / "entity_structure.csv", encoding="utf-8-sig"
)
pv[cols].to_csv(OUT / "panel_summary.csv", index=False, encoding="utf-8-sig")
mem.to_csv(OUT / "membership_normalized_rank.csv", index=False, encoding="utf-8-sig")
say("")
say("wrote entity_structure.csv / panel_summary.csv / membership_normalized_rank.csv")

# ============================================================= FIGURES
import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

KFONT = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
try:
    fm.fontManager.addfont(KFONT)
    fm.fontManager.addfont("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")
    FAM = "NanumGothic"
except Exception:
    FAM = "DejaVu Sans"
plt.rcParams.update(
    {
        "font.family": FAM,
        "axes.unicode_minus": False,
        "figure.facecolor": "#fcfcfb",
        "axes.facecolor": "#fcfcfb",
        "savefig.facecolor": "#fcfcfb",
        "font.size": 10,
        "axes.edgecolor": "#c9c8c3",
        "axes.labelcolor": "#52514e",
        "xtick.color": "#52514e",
        "ytick.color": "#52514e",
        "text.color": "#0b0b0b",
    }
)
BLUE, ORANGE = "#2a78d6", "#eb6834"  # validated 2-slot categorical (dataviz skill)
GRID = "#e6e5e1"
INK, INK2 = "#0b0b0b", "#52514e"


def finish(ax, title, sub, xlab):
    ax.set_title(title, fontsize=13, color=INK, loc="left", pad=30, weight="bold")
    ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=INK2, va="bottom")
    ax.set_xlabel(xlab, fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# --- Fig 1: panel composition
d = pv.sort_values(["domain", "panel_id"]).reset_index(drop=True)
y = np.arange(len(d))[::-1]
fig, ax = plt.subplots(figsize=(9.5, 6.4))
h = 0.36
ax.barh(
    y + h / 2 + 0.02,
    d.entities,
    height=h,
    color="#b9b8b3",
    zorder=3,
    label="distinct entities in panel (N_p)",
)
colors = [BLUE if x == "APP" else ORANGE for x in d.domain]
ax.barh(
    y - h / 2 - 0.02,
    d.source_rows,
    height=h,
    color=colors,
    zorder=3,
    label="source rows (= N_p x n_metrics)",
)
for yi, e, r, m in zip(y, d.entities, d.source_rows, d.n_metrics):
    ax.text(e + 0.6, yi + h / 2 + 0.02, str(e), va="center", fontsize=8, color=INK2)
    ax.text(r + 0.6, yi - h / 2 - 0.02, f"{r}  ({m}m)", va="center", fontsize=8, color=INK2)
ax.set_yticks(y)
ax.set_yticklabels([f"{p}  {dm}" for p, dm in zip(d.panel_id, d.domain)], fontsize=9)
ax.xaxis.grid(True, color=GRID, zorder=0)
ax.set_axisbelow(True)
ax.set_xlim(0, max(d.source_rows) * 1.16)
from matplotlib.patches import Patch

ax.legend(
    handles=[
        Patch(color="#b9b8b3", label="distinct entities (N_p)"),
        Patch(color=BLUE, label="source rows - APP panel"),
        Patch(color=ORANGE, label="source rows - RETAIL panel"),
    ],
    loc="lower right",
    frameon=False,
    fontsize=9,
)
finish(
    ax,
    "Panel size and metric expansion",
    f"17 panels · {int(d.entities.sum())} (entity,panel) memberships expand to "
    f"{int(d.source_rows.sum())} source rows.  '(km)' = metrics per panel.",
    "count",
)
fig.tight_layout()
fig.savefig(FIGS / "fig1_panel_composition.png", dpi=180)
plt.close(fig)

# --- Fig 2: panel appearance count
cross = pd.crosstab(top.panels, top.domain).reindex(columns=["APP", "RETAIL"], fill_value=0)
xs = np.arange(len(cross))
fig, ax = plt.subplots(figsize=(7.6, 4.6))
w = 0.38
ax.bar(xs - w / 2 - 0.01, cross["APP"], width=w, color=BLUE, zorder=3, label="APP")
ax.bar(xs + w / 2 + 0.01, cross["RETAIL"], width=w, color=ORANGE, zorder=3, label="RETAIL")
for xi, a, r in zip(xs, cross["APP"], cross["RETAIL"]):
    if a:
        ax.text(xi - w / 2 - 0.01, a + 0.8, str(a), ha="center", fontsize=9, color=INK2)
    if r:
        ax.text(xi + w / 2 + 0.01, r + 0.8, str(r), ha="center", fontsize=9, color=INK2)
ax.set_xticks(xs)
ax.set_xticklabels([str(i) for i in cross.index])
ax.yaxis.grid(True, color=GRID, zorder=0)
ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9)
n_ind1 = int(((top.panels == 1) & (top.axis_type == "INDUSTRY_CATEGORY")).sum())
finish(
    ax,
    "How many panels does one entity appear in?",
    f"{len(top)} measurement entities.  {int((top.panels == 1).sum())} appear in a "
    f"single panel ({n_ind1} of them are the INDUSTRY_CATEGORY rows of fig07_t1);\n"
    f"{int((top.panels > 1).sum())} recur across 2-5 panels.",
    "number of panels the entity appears in",
)
ax.set_ylabel("entities", fontsize=9)
fig.tight_layout()
fig.savefig(FIGS / "fig2_entity_panel_appearance.png", dpi=180)
plt.close(fig)

# --- Fig 3: ECDF of entity best_norm_rank by domain
fig, ax = plt.subplots(figsize=(7.6, 4.8))
for dm, c in [("APP", BLUE), ("RETAIL", ORANGE)]:
    v = np.sort(best.loc[best.domain == dm, "best_norm_rank"].dropna().values)
    if not len(v):
        continue
    yv = np.arange(1, len(v) + 1) / len(v)
    ax.step(
        np.concatenate([[0], v]),
        np.concatenate([[0], yv]),
        where="post",
        color=c,
        lw=2,
        label=f"{dm} (n={len(v)})",
    )
ax.set_xlim(-0.02, 1.02)
ax.set_ylim(0, 1.02)
ax.yaxis.grid(True, color=GRID, zorder=0)
ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9, loc="lower right")
finish(
    ax,
    "ECDF of entity best panel-normalized rank",
    "norm_rank = (rank-1)/(N_p-1) per (entity,panel);\n"
    "entity value = min over its panels.  0 = rank 1 somewhere.  Descriptive only.",
    "best panel-normalized rank (0 = rank 1 in some panel)",
)
ax.set_ylabel("cumulative share of entities", fontsize=9)
fig.tight_layout()
fig.savefig(FIGS / "fig3_best_norm_rank_ecdf.png", dpi=180)
plt.close(fig)

say("")
say("figures written:", sorted(p.name for p in FIGS.glob("*.png")))

(OUT / "eda01_console.txt").write_text("\n".join(REPORT), encoding="utf-8")
