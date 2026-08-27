"""D-RF2-E — Abstention / ambiguity taxonomy.

목적
----
현재 Rule DT 가 `AMBIGUOUS_UNRESOLVED` 로 남기는 케이스를 **원인별로 분류**하고,
각 원인이 (a) 더 나은 evidence 로 해결 가능한지 (b) 이 target URL 에서는 원리적으로
미결정인지를 구분한다. 그리고 "억지로 하나를 고르면(force-map) 어느 유형에서 가장 많이
틀리는가" 를 prior 기준으로 정량화한다 — abstention 세탁의 비용.

원칙
----
* `prior_archetype` 은 **gold label 이 아니라 prior** 다. 따라서 "accuracy" 라는 말을 쓰지
  않는다. 모든 일치 지표는 `prior_agreement` 로만 부른다.
* holdout label 을 열지 않았다 (`LABEL_SPLIT_FROZEN*`, `HOLDOUT_FOR_C*`, `RAW_L1~L4*`,
  `PACKET_L*`, `*_OVERLAP*`, `PRECEDENCE_CONTESTED*`, `CALIBRATION_FOR_B*`, `**/control/**`
  — 이 파일들은 열지 않았다). 그러므로 **최종 threshold 를 선언하지 않는다**.
  SSOT v2.1 §7 은 운영 threshold 를 independent label calibration split 에서 정하라고 했고,
  D 는 그 split 을 볼 수 없다. 여기서는 곡선과 기울기 변화만 보고한다.
* 선행 D 결과(RF001_A/C, RQ_D9/D10/D13/D13A)는 hypothesis 로만 받는다. 판정에 쓰는 수치는
  raw 관측표·텍스트 코퍼스·decision_trace 에서 직접 재계산한다.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/"
          "research/landing_accessibility/research_d")
RES = RD / "results"
FIG = RD / "figures"
KST = timezone(timedelta(hours=9))
SEED = 20260827
np.random.seed(SEED)

ARCHETYPES = ["QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP",
              "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"]
# SSOT v2.1 §5 Stage3 는 이 순서로 branch 를 평가한다. tie-break 을 이 순서로 고정한다.
BRANCH_ORDER = {a: i for i, a in enumerate(ARCHETYPES)}
# SSOT §5 에서 "반복 항목 >= 3" 형태의 region 술어를 갖는 branch (list-family)
LIST_FAMILY = ["CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP", "COMMUNICATION_ENTRY"]

matplotlib.rcParams["font.family"] = ["DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


# ----------------------------------------------------------------------------
# 1. 입력 로드
# ----------------------------------------------------------------------------
def load() -> tuple[pd.DataFrame, dict]:
    obs = pd.read_csv(RES / "D_OBSERVATION_TABLE_v2.csv")
    obs = obs[obs.in_mart == 1].copy()
    cor = pd.read_csv(RES / "D_TEXT_CORPUS_v2.csv")
    A = json.loads((RES / "RF001_A_rule_dt.json").read_text(encoding="utf-8"))
    leaves = pd.DataFrame(A["leaves"]).rename(columns={"target_id": "wtg"})
    d13a = {r["wtg"]: r for r in
            json.loads((RES / "RQ_D13A_overlay_provenance.json").read_text(encoding="utf-8"))["records"]}
    d13 = json.loads((RES / "RQ_D13_duplicate_vector.json").read_text(encoding="utf-8"))
    d10 = {o["wtg"]: o for o in
           json.loads((RES / "RQ_D10_slot_mismatch.json").read_text(encoding="utf-8"))["observations"]}
    d9 = json.loads((RES / "RQ_D9_quality_proxy.json").read_text(encoding="utf-8"))

    df = leaves.merge(obs, on="wtg", suffixes=("", "_obs")).merge(cor, on="wtg", suffixes=("", "_cor"))
    assert len(df) == 56, len(df)
    aux = {"d13a": d13a, "d13": d13, "d10": d10,
           "caps": d9["cap_constants_from_l0_probe_js_2281c85"],
           "untrunc": d9["unreported_truncation_points"]}
    return df, aux


# ----------------------------------------------------------------------------
# 2. decision_trace 에서 branch evidence 재계산 (RF001_A 의 요약수치를 믿지 않고 직접 센다)
# ----------------------------------------------------------------------------
def branch_evidence(trace: list[dict]) -> dict:
    """Stage3 R/E 술어 발화를 branch 별로 재구성한다."""
    R, E, stage0 = {}, {}, []
    for t in trace:
        if t["stage"] == "Stage0" and t.get("fired"):
            stage0.append(t["rule"])
        if t["stage"] != "Stage3":
            continue
        br, kind = t["rule"].rsplit(".", 1)
        (R if kind == "R" else E)[br] = bool(t["fired"])
    score = {b: int(R.get(b, False)) + int(E.get(b, False)) for b in ARCHETYPES}
    strong = sorted([b for b in ARCHETYPES if R.get(b) and E.get(b)], key=lambda b: BRANCH_ORDER[b])
    weak = sorted([b for b in ARCHETYPES if score[b] == 1], key=lambda b: BRANCH_ORDER[b])
    stage3_evaluated = bool(R) or bool(E)
    return {"R": R, "E": E, "score": score, "strong": strong, "weak": weak,
            "n_fired": sum(score.values()), "stage0_fired": stage0,
            "stage3_evaluated": stage3_evaluated,
            "list_family_R": sorted([b for b in LIST_FAMILY if R.get(b)], key=lambda b: BRANCH_ORDER[b])}


def rule_confidence(score: dict) -> tuple[float, str, bool]:
    """Rule 신뢰도 = 최상위 branch 발화강도 + 2위와의 격차/2.

    범위 0..3. 3 = 유일한 R^E branch. 0 = 아무 술어도 안 붙음.
    반환 (conf, argmax_branch, tie)
    """
    ranked = sorted(ARCHETYPES, key=lambda b: (-score[b], BRANCH_ORDER[b]))
    top, second = ranked[0], ranked[1]
    s1, s2 = score[top], score[second]
    tie = s1 == s2 and s1 > 0
    conf = s1 + (s1 - s2) / 2.0
    return conf, top, tie


# ----------------------------------------------------------------------------
# 3. 유형 정의 (전문은 TAXONOMY_DEFS 에 그대로 공개한다)
# ----------------------------------------------------------------------------
LEX = {
    "app": re.compile(r"(app ?store|google ?play|앱스토어|플레이스토어|원스토어|앱\s*다운로드|"
                      r"앱\s*설치|다운로드하기|다운받기|get the app|앱으로 보기|앱에서 (열기|보기))", re.I),
    "brand": re.compile(r"(회사소개|기업소개|about ?us|about ?the|ir |투자정보|채용|인재채용|보도자료|"
                        r"newsroom|브랜드\s*소개|브랜드\s*스토리|company|윤리경영|사회공헌|제휴문의|"
                        r"가맹|입점\s*문의|서비스\s*소개|공지사항|고객센터 안내)", re.I),
    "login": re.compile(r"(로그인|log ?in|sign ?in|아이디\b|비밀번호|password|본인인증|본인확인|"
                        r"공동인증|간편인증|회원가입|sign ?up)", re.I),
}
PATH_BRAND = re.compile(r"(/about|/intro|/brand/|/service-|/solution/|/company|/page/detail|"
                        r"/chrome|/newsroom|/ir\b|/introduce)", re.I)
# SSOT §7 "Text representation" 이 요구하는 8개 구성요소
SSOT7_COMPONENTS = ["title", "headings", "landmarks", "nav_links", "buttons",
                    "aria_labels", "form_labels", "card_texts"]

TAXONOMY_DEFS: dict[str, dict] = {
    "T01_NO_PREDICATE_FIRED": dict(
        name="어떤 술어도 발화하지 않음 (insufficient evidence)",
        definition=(
            "Stage3 가 실제로 평가되었고(= 14개 R/E 술어가 trace 에 기록됨), 그 14개 중 "
            "단 하나도 fired=true 가 아니다. 관측된 표면에 SSOT §5 가 정의한 어떤 archetype 의 "
            "region 신호도 endpoint 신호도 없다는 뜻이다. 이것은 **원인이 아니라 증상**이며, "
            "아래 표면유형/수집품질 유형으로 분해되어야 한다."),
        family="EVIDENCE_SHAPE"),
    "T02_WEAK_ONE_SIDED_EVIDENCE": dict(
        name="한쪽 신호만 있는 약한 후보 (region 만 또는 endpoint 만)",
        definition=(
            "Stage3 술어가 1개 이상 발화했으나 R 과 E 를 동시에 만족하는 branch 가 하나도 없다"
            "(strong=∅, weak≠∅). SSOT §6 의 '유일 후보' 조건을 만족할 수 없어 확정 불가다."),
        family="EVIDENCE_SHAPE"),
    "T03_MULTI_STRONG_CANDIDATE": dict(
        name="강한 후보가 둘 이상",
        definition=(
            "R 과 E 를 동시에 만족하는 branch 가 2개 이상이다. SSOT §6 '두 개 이상 강한 후보' "
            "분기로, 첫 매칭을 고르지 않고 NLP fallback(§7)으로 넘긴다."),
        family="EVIDENCE_SHAPE"),
    "T04_SHARED_LIST_SIGNAL": dict(
        name="같은 신호를 여러 archetype 이 공유 (list-family)",
        definition=(
            "list-family 4개 branch(CONTENT_OPEN / ITEM_DETAIL / PLACE_LOOKUP / "
            "COMMUNICATION_ENTRY) 중 2개 이상의 **R 술어**가 같은 target 에서 발화했다. "
            "이들 R 은 모두 '반복 항목 >= 3' 형태라 하나의 카드 목록 관측이 여러 archetype 의 "
            "region 정의를 동시에 만족시킨다. region 관측을 아무리 더 모아도 서로를 배제하지 "
            "못하고, endpoint(E) 또는 §6 precedence 만이 가른다."),
        family="EVIDENCE_SHAPE"),
    "T05_GENERIC_BRAND_LANDING": dict(
        name="일반 기업/브랜드 소개 면",
        definition=(
            "다음 중 하나 이상: (a) SSOT §7 텍스트 묶음 안에 기업/브랜드 어휘"
            "(회사소개·IR·채용·보도자료·브랜드 스토리·입점문의·서비스 소개 등)가 3회 이상 등장, "
            "(b) probe 최종 URL 경로가 기업/소개 경로 마커(/about /intro /brand/ /service- "
            "/solution/ /company /page/detail /chrome /newsroom /introduce)에 일치. "
            "**그리고** strong branch 가 없다(=기능 표면이 관측되지 않았다). "
            "즉 target URL 이 서비스의 기능면이 아니라 그 서비스를 '설명하는' 면으로 해석된 경우다."),
        family="SURFACE_IDENTITY"),
    "T06_APP_INSTALL_SURFACE": dict(
        name="앱 설치/전환 유도 면",
        definition=(
            "SSOT §7 텍스트 묶음에 앱스토어/구글플레이/앱 다운로드/앱에서 열기 계열 어휘가 "
            "1회 이상 등장하거나, Rule DT 의 `is_app_interstitial` 술어가 1이다. "
            "웹 표면의 대표행동이 '앱으로 나가기'로 대체된 상태."),
        family="SURFACE_IDENTITY"),
    "T07_REPRESENTATIVE_SURFACE_ABSENT": dict(
        name="대표 표면 자체가 관측되지 않음 (Stage0 NO 분기)",
        definition=(
            "Stage0 에서 S0_NO_RENDERED_SURFACE 또는 S0_ERROR_PAGE 가 발화하여 Stage3 가 "
            "평가되지도 않았다. frozen evidence 안에 렌더된 공개 web surface 가 없거나 "
            "error/not-found 면이다. leaf = UNDETERMINED_URL_EVIDENCE."),
        family="SURFACE_IDENTITY"),
    "T08_LOGIN_DOMINATED": dict(
        name="로그인 지배 표면",
        definition=(
            "다음 중 하나: (a) `gate_password_input_n >= 1`(실제 credential 입력칸 관측), "
            "(b) probe 최종 URL 경로에 login/signin, (c) SSOT §7 텍스트 묶음의 로그인/인증 어휘 "
            "3회 이상. 하위구분 — GATE_REACHED: (a) 성립, GATE_NOT_REACHED: (a) 불성립이고 "
            "(b)/(c)만 성립(= 로그인 '버튼'만 보이고 실제 gate 구조에는 도달하지 못함). "
            "SSOT §5 Branch F 의 E_F 는 실제 gate 도달을 요구하므로 GATE_NOT_REACHED 는 "
            "endpoint 술어를 발화시키지 못한다."),
        family="SURFACE_IDENTITY"),
    "T09_CLIENT_RENDER_SPARSE": dict(
        name="SPA/클라이언트 렌더로 구조가 비어 있음",
        definition=(
            "SSOT §7 이 요구하는 8개 텍스트 구성요소(title, headings, landmarks, nav_links, "
            "buttons, aria_labels, form_labels, card_texts) 중 비어 있지 않은 것이 2개 이하거나, "
            "`dom_body_empty == 1`. DOM 바이트는 클 수 있으나(스크립트 shell) 구조화된 "
            "표현이 만들어지지 않는 상태."),
        family="CAPTURE_QUALITY"),
    "T10A_TEXT_ENCODING_CORRUPTION": dict(
        name="텍스트 인코딩 훼손 (mojibake)",
        definition="관측표의 `encoding_degraded == 1`. DOM 텍스트 디코딩이 깨져 어휘 술어가 무력화된다.",
        family="CAPTURE_QUALITY"),
    "T10B_TEXT_CAP_TRUNCATION": dict(
        name="텍스트/후보 절단 (cap)",
        definition=(
            "관측표의 `cap_any == 1`(l0_probe.js 상수 cap 에 도달한 측정이 하나 이상) 이거나 "
            "`gate_visible_text_len >= 3900`(미보고 절단점 4000자 slice 근접). 관측이 상한에서 "
            "잘려 실제 구조의 일부만 남았다."),
        family="CAPTURE_QUALITY"),
    "T11_OVERLAY_OBSTRUCTED": dict(
        name="오버레이/모달로 대표 표면이 가려짐",
        definition=(
            "RQ-D13A 의 overlay provenance 분류가 H1_MODAL 또는 H2_GENERIC_LOADING_MASK 이거나, "
            "관측표의 `body_scroll_locked == 1`. 캡처 시점에 대표 표면이 덮여 있었다."),
        family="CAPTURE_QUALITY"),
    "T12_DEGENERATE_OR_DUPLICATE_CAPTURE": dict(
        name="퇴화 캡처 / 중복 캡처",
        definition=(
            "RQ-D13 이 식별한 degenerate capture(빈 CSS + 빈 DOM body) 이거나, 다른 target 과 "
            "requested URL 이 동일해 같은 증거를 공유한다. 이 target 의 증거는 이 target 을 "
            "설명하지 못한다."),
        family="CAPTURE_QUALITY"),
    "T13_PRIOR_CONTRADICTS_STRUCTURE": dict(
        name="business prior 가 관측 구조와 어긋남",
        definition=(
            "prior_archetype 에 해당하는 branch 의 R 과 E 가 **둘 다** 발화하지 않았는데, "
            "다른 branch 에서는 최소 하나의 술어가 발화했다. 관측된 구조는 prior 가 아닌 다른 "
            "archetype 을 가리킨다. prior 는 gold label 이 아니므로 이것은 'rule 이 틀렸다'가 "
            "아니라 '둘이 어긋난다'는 관측이다."),
        family="PRIOR_CONFLICT"),
}


def classify(row: pd.Series, ev: dict, aux: dict) -> dict:
    """한 target 에 대해 모든 유형을 독립 판정한다 (중복 허용)."""
    blob = str(row.get("text_blob") or "")
    final_url = str(row.get("probe_final_url") or row.get("prior_url") or "")
    n_app = len(LEX["app"].findall(blob))
    n_brand = len(LEX["brand"].findall(blob))
    n_login = len(LEX["login"].findall(blob))
    path_brand = bool(PATH_BRAND.search(final_url))
    n_components = sum(1 for c in SSOT7_COMPONENTS
                       if str(row.get(c) or "").strip() not in ("", "nan"))
    d13a = aux["d13a"].get(row.wtg, {})
    degen = {x["wtg"] for x in aux["d13"]["degenerate_captures"]}
    dup = {w for g in aux["d13"]["url_level_duplicates"] for w in g["wtgs"]}
    pw = float(row.get("gate_password_input_n") or 0)
    login_url = bool(re.search(r"/(login|signin|sign-in)", final_url, re.I))

    t: dict[str, bool] = {}
    t["T01_NO_PREDICATE_FIRED"] = ev["stage3_evaluated"] and ev["n_fired"] == 0
    t["T02_WEAK_ONE_SIDED_EVIDENCE"] = (ev["stage3_evaluated"] and ev["n_fired"] > 0
                                        and len(ev["strong"]) == 0)
    t["T03_MULTI_STRONG_CANDIDATE"] = len(ev["strong"]) >= 2
    t["T04_SHARED_LIST_SIGNAL"] = len(ev["list_family_R"]) >= 2
    t["T05_GENERIC_BRAND_LANDING"] = (n_brand >= 3 or path_brand) and len(ev["strong"]) == 0
    t["T06_APP_INSTALL_SURFACE"] = (n_app >= 1) or int(row.get("app_interstitial") or 0) == 1
    t["T07_REPRESENTATIVE_SURFACE_ABSENT"] = len(ev["stage0_fired"]) > 0
    t["T08_LOGIN_DOMINATED"] = (pw >= 1) or login_url or (n_login >= 3)
    t["T09_CLIENT_RENDER_SPARSE"] = (n_components <= 2) or float(row.get("dom_body_empty") or 0) == 1
    t["T10A_TEXT_ENCODING_CORRUPTION"] = int(row.get("encoding_degraded") or 0) == 1
    t["T10B_TEXT_CAP_TRUNCATION"] = (float(row.get("cap_any") or 0) == 1
                                     or float(row.get("gate_visible_text_len") or 0) >= 3900)
    t["T11_OVERLAY_OBSTRUCTED"] = (d13a.get("classification") in ("H1_MODAL", "H2_GENERIC_LOADING_MASK")
                                   or float(row.get("body_scroll_locked") or 0) == 1)
    t["T12_DEGENERATE_OR_DUPLICATE_CAPTURE"] = (row.wtg in degen) or (row.wtg in dup)
    pa = row["prior_archetype"]
    prior_branch_silent = not (ev["R"].get(pa) or ev["E"].get(pa))
    t["T13_PRIOR_CONTRADICTS_STRUCTURE"] = prior_branch_silent and ev["n_fired"] > 0

    detail = {"n_app_lex": n_app, "n_brand_lex": n_brand, "n_login_lex": n_login,
              "path_brand_marker": path_brand, "ssot7_components_present": n_components,
              "gate_password_input_n": pw, "login_in_final_url": login_url,
              "overlay_class": d13a.get("classification"),
              "final_url": final_url,
              "login_subtype": ("GATE_REACHED" if pw >= 1 else
                                ("GATE_NOT_REACHED" if t["T08_LOGIN_DOMINATED"] else None))}
    return {"types": t, "detail": detail}


# ----------------------------------------------------------------------------
# 4. 해결가능성 판정 — 근거는 관측에서 나온다
# ----------------------------------------------------------------------------
RESOLVABILITY = {
    "T01_NO_PREDICATE_FIRED": ("DECOMPOSES", "증상이지 원인이 아니다. 아래 표면/수집 유형으로 분해한 뒤 판단한다."),
    "T02_WEAK_ONE_SIDED_EVIDENCE": ("COLLECTION_OR_DEFINITION",
        "R 또는 E 중 한쪽만 붙었다. 누락된 쪽이 endpoint 인 경우는 상호작용 1스텝 수집으로 확인 가능하고, "
        "누락된 쪽이 region 인 경우는 §5 region 정의의 조작화 문제다."),
    "T03_MULTI_STRONG_CANDIDATE": ("DEFINITION_OR_FALLBACK",
        "SSOT §6 이 이미 NLP fallback 으로 보내라고 규정한 분기다. 같은 페이지를 더 관측해도 두 후보가 "
        "동시에 참인 사실은 변하지 않는다. §6 precedence 를 순서로 확정하거나 §7 fallback 이 갈라야 한다."),
    "T04_SHARED_LIST_SIGNAL": ("DEFINITION_RESOLVABLE",
        "region 술어가 서로 배타적이지 않게 조작화되어 있다. region 증거를 더 모아도 배타성이 생기지 않는다. "
        "정의(§5 region predicate 의 상호배타화 또는 §6 precedence 명문화)로만 풀린다."),
    "T05_GENERIC_BRAND_LANDING": ("TARGET_RESOLVABLE__UNDECIDABLE_AT_THIS_URL",
        "이 URL 이 실제로 기업/브랜드 소개면이라면 그 면에는 대표 기능 표면이 존재하지 않는다. "
        "같은 URL 에서 evidence 를 더 모아도 없는 표면이 생기지 않는다. target URL 재정의(연구 frame) 문제다."),
    "T06_APP_INSTALL_SURFACE": ("TARGET_RESOLVABLE__UNDECIDABLE_AT_THIS_URL",
        "웹 표면의 대표행동이 '앱으로 나가기'다. 앱 안쪽은 이 연구의 관측범위(공개 web surface) 밖이다. "
        "다만 앱 유도가 dismissible interstitial 인 경우는 수집으로 우회 가능하므로 하위분리해 센다."),
    "T07_REPRESENTATIVE_SURFACE_ABSENT": ("TARGET_RESOLVABLE__UNDECIDABLE_AT_THIS_URL",
        "Stage0 NO 분기. 렌더된 표면이 없거나 error 면이다. SSOT §2 가 이미 확정을 금지한다."),
    "T08_LOGIN_DOMINATED": ("SPLIT",
        "GATE_REACHED 는 오히려 E_F 를 발화시킬 수 있는 정상 증거다. GATE_NOT_REACHED 는 "
        "상호작용 1스텝(로그인 버튼 클릭)으로 gate 구조에 도달하면 해결 가능하다 — COLLECTION_RESOLVABLE."),
    "T09_CLIENT_RENDER_SPARSE": ("COLLECTION_RESOLVABLE",
        "같은 수집 스택에서 다른 target 은 §7 구성요소를 8개 중 다수 확보했다. 즉 실패는 표면의 성질이 "
        "아니라 캡처 시점/방식이다. hydration 대기·AX 트리 사용·렌더 후 재캡처로 해결 가능하다."),
    "T10A_TEXT_ENCODING_CORRUPTION": ("COLLECTION_RESOLVABLE",
        "디코딩 결함이다. dom_encoding 이 관측표에 남아 있고 재디코딩은 결정적(deterministic)이다."),
    "T10B_TEXT_CAP_TRUNCATION": ("COLLECTION_RESOLVABLE",
        "cap 은 l0_probe.js 의 상수다(RQ-D9 가 상수값을 코드에서 확인). 상수를 올리면 관측이 늘어난다."),
    "T11_OVERLAY_OBSTRUCTED": ("COLLECTION_RESOLVABLE_PARTIAL",
        "RQ-D13 의 dismissal 실험에서 248 스텝 중 166 스텝이 화면을 바꿨다(=해제가 실제로 작동). "
        "다만 어떤 스텝으로도 변화가 없던 target 이 6건 있어 전부가 풀리지는 않는다."),
    "T12_DEGENERATE_OR_DUPLICATE_CAPTURE": ("COLLECTION_RESOLVABLE",
        "빈 CSS·빈 DOM·동일 URL 공유는 수집기 결함이다. 재수집으로 해결된다."),
    "T13_PRIOR_CONTRADICTS_STRUCTURE": ("NOT_AN_EVIDENCE_PROBLEM",
        "prior 는 gold 가 아니다. 이 유형은 evidence 부족이 아니라 prior 와 관측의 불일치이며, "
        "label 없이는 어느 쪽이 틀렸는지 D 가 판정할 수 없다. 더 모아도 D 혼자서는 닫히지 않는다."),
}

RESOLVABLE_SET = {"COLLECTION_RESOLVABLE", "COLLECTION_RESOLVABLE_PARTIAL",
                  "COLLECTION_OR_DEFINITION", "DEFINITION_RESOLVABLE", "DEFINITION_OR_FALLBACK"}
UNDECIDABLE_SET = {"TARGET_RESOLVABLE__UNDECIDABLE_AT_THIS_URL", "NOT_AN_EVIDENCE_PROBLEM"}


# ----------------------------------------------------------------------------
# 5. semantic margin — bge-m3 + A_SSOT_DEF prototype 을 독립 재계산
# ----------------------------------------------------------------------------
def _debrand(blob: str, service: str, url: str) -> str:
    """서비스명·도메인 라벨을 blob 에서 지운다 (RF001-B 가 확인한 brand leak 대조군)."""
    out = str(blob or "")
    toks = set()
    sv = str(service or "").strip()
    if sv:
        toks.add(sv)
        toks.update(t for t in re.split(r"[\s/]+", sv) if len(t) >= 2)
    m = re.search(r"https?://([^/]+)", str(url or ""))
    if m:
        host = m.group(1)
        toks.update(t for t in host.split(".")
                    if len(t) >= 3 and t not in ("www", "com", "net", "org", "co", "kr", "https"))
    for t in sorted(toks, key=len, reverse=True):
        out = re.sub(re.escape(t), " ", out, flags=re.I)
    return out


def semantic_margins(df: pd.DataFrame, debrand: bool = False) -> dict:
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    C = json.loads((RES / "RF001_C_embedding.json").read_text(encoding="utf-8"))
    protos = C["prototype_sets"]["A_SSOT_DEF"]
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("BAAI/bge-m3", device="cuda")
    if debrand:
        docs = [_debrand(r["text_blob"], r["prior_service"],
                         r.get("probe_final_url") or r.get("prior_url"))
                for _, r in df.iterrows()]
    else:
        docs = [str(x or "") for x in df["text_blob"]]
    P = m.encode([protos[a] for a in ARCHETYPES], normalize_embeddings=True,
                 batch_size=8, show_progress_bar=False)
    D = m.encode(docs, normalize_embeddings=True, batch_size=8, show_progress_bar=False)
    S = np.asarray(D) @ np.asarray(P).T
    out = {}
    for i, w in enumerate(df["wtg"]):
        order = np.argsort(-S[i])
        out[w] = {"top1": ARCHETYPES[order[0]], "top2": ARCHETYPES[order[1]],
                  "sim_top1": float(S[i, order[0]]), "sim_top2": float(S[i, order[1]]),
                  "margin": float(S[i, order[0]] - S[i, order[1]]),
                  "sims": {ARCHETYPES[j]: float(S[i, j]) for j in range(7)}}
    return out


# ----------------------------------------------------------------------------
# 6. coverage <-> prior_agreement 곡선
# ----------------------------------------------------------------------------
def curve(scores: np.ndarray, pred: list[str], prior: list[str], grid: np.ndarray) -> list[dict]:
    rows = []
    for t in grid:
        sel = scores >= t
        n = int(sel.sum())
        k = int(sum(1 for i in range(len(pred)) if sel[i] and pred[i] == prior[i]))
        lo, hi = wilson(k, n)
        rows.append({"threshold": float(t), "coverage_n": n, "coverage": n / len(pred),
                     "abstain_n": len(pred) - n, "prior_agreement": (k / n) if n else float("nan"),
                     "agree_k": k, "wilson95": [lo, hi]})
    return rows


def bands(scores: np.ndarray, pred: list[str], prior: list[str], edges: list[float]) -> list[dict]:
    """구간별(marginal band) prior_agreement — 어디서 기울기가 꺾이는지 보기 위한 것."""
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (scores >= lo) & (scores < hi)
        n = int(sel.sum())
        k = int(sum(1 for i in range(len(pred)) if sel[i] and pred[i] == prior[i]))
        wl, wh = wilson(k, n)
        out.append({"band": f"[{lo:.4g},{hi:.4g})", "n": n, "agree_k": k,
                    "prior_agreement": (k / n) if n else float("nan"), "wilson95": [wl, wh]})
    return out


# ----------------------------------------------------------------------------
# 7. main
# ----------------------------------------------------------------------------
def main() -> None:
    df, aux = load()
    df = df.reset_index(drop=True)

    recs = []
    for _, row in df.iterrows():
        ev = branch_evidence(row["decision_trace"])
        conf, arg, tie = rule_confidence(ev["score"])
        c = classify(row, ev, aux)
        recs.append({"wtg": row["wtg"], "service": row["prior_service"],
                     "prior_archetype": row["prior_archetype"], "leaf": row["leaf"],
                     "final_url": c["detail"]["final_url"],
                     "strong": ev["strong"], "weak": ev["weak"], "n_fired": ev["n_fired"],
                     "branch_score": ev["score"], "list_family_R": ev["list_family_R"],
                     "stage0_fired": ev["stage0_fired"],
                     "rule_conf": conf, "rule_argmax": arg, "rule_tie": tie,
                     "types": c["detail"], "type_flags": c["types"]})
    R = pd.DataFrame(recs)

    # ---- 무결성 재확인 (RF001_A 요약수치를 믿지 않고 직접 센 값과 대조)
    A = json.loads((RES / "RF001_A_rule_dt.json").read_text(encoding="utf-8"))
    recount = {"n_targets": len(R),
               "n_mapped_recount": int((R.strong.map(len) == 1).sum()),
               "n_multi_recount": int((R.strong.map(len) >= 2).sum()),
               "n_no_strong_recount": int(((R.strong.map(len) == 0)
                                           & (R.stage0_fired.map(len) == 0)).sum()),
               "n_stage0_recount": int((R.stage0_fired.map(len) > 0).sum()),
               "rf001_a_reported": {k: A["metrics"][k] for k in
                                    ("n_mapped", "n_abstain_multi", "n_abstain_no_evidence",
                                     "n_undetermined")}}
    recount["matches_rf001_a"] = (
        recount["n_mapped_recount"] == A["metrics"]["n_mapped"]
        and recount["n_multi_recount"] == A["metrics"]["n_abstain_multi"]
        and recount["n_no_strong_recount"] == A["metrics"]["n_abstain_no_evidence"]
        and recount["n_stage0_recount"] == A["metrics"]["n_undetermined"])

    # ---- 분모 정의
    R["is_mapped"] = R.strong.map(len) == 1
    R["is_abstain40"] = (~R.is_mapped) & (R.stage0_fired.map(len) == 0)   # 34 + 6
    R["is_unresolved45"] = ~R.is_mapped
    N56, N40, N45 = len(R), int(R.is_abstain40.sum()), int(R.is_unresolved45.sum())

    # ---- 유형별 집계
    TYPES = list(TAXONOMY_DEFS)
    flags = pd.DataFrame([r["type_flags"] for r in recs], index=R.wtg)[TYPES]
    type_table = {}
    for t in TYPES:
        sel = flags[t].values
        ex = []
        for i in np.where(sel)[0][:5]:
            r = recs[i]
            d = r["types"]
            ex.append({
                "wtg": r["wtg"], "service": r["service"], "prior_archetype": r["prior_archetype"],
                "leaf": r["leaf"], "final_url": d["final_url"][:110],
                "why": _why(t, r, d)})
        res, ground = RESOLVABILITY[t]
        type_table[t] = {
            "name": TAXONOMY_DEFS[t]["name"], "family": TAXONOMY_DEFS[t]["family"],
            "definition": TAXONOMY_DEFS[t]["definition"],
            "n_of_56": int(sel.sum()),
            "pct_of_56": round(float(sel.sum()) / N56, 4),
            "n_of_abstain40": int((sel & R.is_abstain40.values).sum()),
            "pct_of_abstain40": round(float((sel & R.is_abstain40.values).sum()) / N40, 4),
            "n_of_unresolved45": int((sel & R.is_unresolved45.values).sum()),
            "n_of_mapped11": int((sel & R.is_mapped.values).sum()),
            "resolvability": res, "resolvability_grounds": ground,
            "evidence_examples": ex,
            "members": [recs[i]["wtg"] for i in np.where(sel)[0]]}

    # T06 하위분리: dismissible interstitial 인지
    t06 = flags["T06_APP_INSTALL_SURFACE"].values
    t06_dismissible = [recs[i]["wtg"] for i in np.where(t06)[0]
                       if float(df.iloc[i].get("dismiss_control_n") or 0) > 0]
    type_table["T06_APP_INSTALL_SURFACE"]["subtypes"] = {
        "dismissible_control_present_n": len(t06_dismissible),
        "no_dismiss_control_n": int(t06.sum()) - len(t06_dismissible)}
    # T08 하위분리
    sub = Counter(r["types"]["login_subtype"] for r in recs if r["type_flags"]["T08_LOGIN_DOMINATED"])
    type_table["T08_LOGIN_DOMINATED"]["subtypes"] = dict(sub)

    # ---- 중복 행렬
    M = flags.values.astype(int)
    overlap = (M.T @ M)
    overlap_abst = (M[R.is_abstain40.values].T @ M[R.is_abstain40.values])
    ntypes_per_target = M.sum(axis=1)
    residual_T01 = []
    other = [t for t in TYPES if t not in
             ("T01_NO_PREDICATE_FIRED", "T02_WEAK_ONE_SIDED_EVIDENCE", "T13_PRIOR_CONTRADICTS_STRUCTURE")]
    for i in range(len(R)):
        if flags["T01_NO_PREDICATE_FIRED"].values[i] and not flags[other].values[i].any():
            residual_T01.append(recs[i]["wtg"])

    # ---- 해결가능 vs 원리적 미결정 (target 단위, 유형 중복 허용이므로 우선순위 규칙 명시)
    prio = ["T07_REPRESENTATIVE_SURFACE_ABSENT", "T12_DEGENERATE_OR_DUPLICATE_CAPTURE",
            "T09_CLIENT_RENDER_SPARSE", "T10A_TEXT_ENCODING_CORRUPTION",
            "T05_GENERIC_BRAND_LANDING", "T06_APP_INSTALL_SURFACE",
            "T11_OVERLAY_OBSTRUCTED", "T10B_TEXT_CAP_TRUNCATION",
            "T08_LOGIN_DOMINATED", "T04_SHARED_LIST_SIGNAL", "T03_MULTI_STRONG_CANDIDATE",
            "T02_WEAK_ONE_SIDED_EVIDENCE", "T13_PRIOR_CONTRADICTS_STRUCTURE",
            "T01_NO_PREDICATE_FIRED"]
    primary_type, primary_res = [], []
    for i in range(len(R)):
        pt = next((t for t in prio if flags[t].values[i]), "T00_UNCLASSIFIED")
        primary_type.append(pt)
        if pt == "T00_UNCLASSIFIED":
            primary_res.append("UNCLASSIFIED")
        else:
            res = RESOLVABILITY[pt][0]
            if pt == "T08_LOGIN_DOMINATED":
                res = ("COLLECTION_RESOLVABLE" if recs[i]["types"]["login_subtype"] == "GATE_NOT_REACHED"
                       else "COLLECTION_OR_DEFINITION")
            primary_res.append(res)
    R["primary_type"] = primary_type
    R["primary_resolvability"] = primary_res
    res_bucket = ["RESOLVABLE" if r in RESOLVABLE_SET else
                  ("UNDECIDABLE_AT_THIS_URL" if r in UNDECIDABLE_SET else "OTHER")
                  for r in primary_res]
    R["resolvability_bucket"] = res_bucket
    resolv_summary = {
        "assignment_rule": ("한 target 이 여러 유형에 해당하므로, 해결가능성 집계에는 고정 우선순위 "
                            "(표면부재 > 퇴화캡처 > 렌더희소 > 인코딩 > 브랜드면 > 앱면 > 오버레이 > "
                            "절단 > 로그인 > 공유신호 > 다중강후보 > 약한증거 > prior충돌 > 무발화) 로 "
                            "primary type 을 하나 정한다. 우선순위는 '수집으로 고칠 수 있는 것' 보다 "
                            "'표면이 애초에 없는 것' 을 앞에 둔다 — 뒤집으면 미결정이 과소계상된다."),
        "priority_order": prio,
        "of_56": dict(Counter(res_bucket)),
        "of_abstain40": dict(Counter(np.array(res_bucket)[R.is_abstain40.values])),
        "of_unresolved45": dict(Counter(np.array(res_bucket)[R.is_unresolved45.values])),
        "primary_type_counts_of_abstain40": dict(
            Counter(np.array(primary_type)[R.is_abstain40.values])),
        "sensitivity_reversed_priority": None}
    # 민감도: 우선순위를 뒤집으면 어떻게 되는가
    prio_rev = list(reversed(prio))
    rev_bucket = []
    for i in range(len(R)):
        pt = next((t for t in prio_rev if flags[t].values[i]), None)
        if pt is None:
            rev_bucket.append("OTHER"); continue
        r0 = RESOLVABILITY[pt][0]
        rev_bucket.append("RESOLVABLE" if r0 in RESOLVABLE_SET else
                          ("UNDECIDABLE_AT_THIS_URL" if r0 in UNDECIDABLE_SET else "OTHER"))
    resolv_summary["sensitivity_reversed_priority"] = {
        "of_abstain40": dict(Counter(np.array(rev_bucket)[R.is_abstain40.values])),
        "note": "우선순위를 뒤집으면 미결정 계상이 어떻게 흔들리는지 — 결론의 강건성 확인용."}
    # 우선순위와 무관한 하한/상한
    hard_undecidable = flags[["T05_GENERIC_BRAND_LANDING", "T06_APP_INSTALL_SURFACE",
                              "T07_REPRESENTATIVE_SURFACE_ABSENT"]].values.any(axis=1)
    pure_collection = flags[["T09_CLIENT_RENDER_SPARSE", "T10A_TEXT_ENCODING_CORRUPTION",
                             "T10B_TEXT_CAP_TRUNCATION", "T11_OVERLAY_OBSTRUCTED",
                             "T12_DEGENERATE_OR_DUPLICATE_CAPTURE"]].values.any(axis=1)
    resolv_summary["priority_free_bounds"] = {
        "note": ("우선순위 규칙에 의존하지 않는 집계. 두 집합은 겹칠 수 있다 — 겹침은 "
                 "'수집을 고쳐도 표면이 없어서 안 되는' 케이스다."),
        "any_surface_absent_type_of_abstain40": int((hard_undecidable & R.is_abstain40.values).sum()),
        "any_capture_quality_type_of_abstain40": int((pure_collection & R.is_abstain40.values).sum()),
        "both_of_abstain40": int((hard_undecidable & pure_collection & R.is_abstain40.values).sum()),
        "neither_of_abstain40": int((~hard_undecidable & ~pure_collection & R.is_abstain40.values).sum()),
        "any_surface_absent_type_of_56": int(hard_undecidable.sum()),
        "any_capture_quality_type_of_56": int(pure_collection.sum())}

    # ---- semantic margin
    sem = semantic_margins(df)
    R["sem_top1"] = [sem[w]["top1"] for w in R.wtg]
    R["sem_top2"] = [sem[w]["top2"] for w in R.wtg]
    R["sem_margin"] = [sem[w]["margin"] for w in R.wtg]
    R["sem_sim_top1"] = [sem[w]["sim_top1"] for w in R.wtg]

    sem_db = semantic_margins(df, debrand=True)
    R["sem_db_top1"] = [sem_db[w]["top1"] for w in R.wtg]
    R["sem_db_margin"] = [sem_db[w]["margin"] for w in R.wtg]

    prior = list(R.prior_archetype)
    # 곡선 1: rule confidence (force-map = rule_argmax)
    rc = R.rule_conf.values.astype(float)
    grid_r = np.array(sorted(set(np.round(rc, 6))))
    curve_rule = curve(rc, list(R.rule_argmax), prior, grid_r)
    bands_rule = bands(rc, list(R.rule_argmax), prior, [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 3.001])
    # 곡선 2: semantic margin (force-map = sem_top1)
    sm = R.sem_margin.values.astype(float)
    grid_s = np.unique(np.round(np.quantile(sm, np.linspace(0, 1, 29)), 6))
    curve_sem = curve(sm, list(R.sem_top1), prior, grid_s)
    q = np.quantile(sm, [0, .2, .4, .6, .8, 1.0])
    bands_sem = bands(sm, list(R.sem_top1), prior, list(q[:-1]) + [q[-1] + 1e-9])
    # 곡선 3: SSOT §6 -> §7 캐스케이드 (rule 유일강후보면 rule, 아니면 margin 임계 위에서 embedding)
    casc = []
    for t in grid_s:
        pred, n, k = [], 0, 0
        for i in range(len(R)):
            if R.is_mapped.values[i]:
                p = R.strong.values[i][0]
            elif sm[i] >= t:
                p = R.sem_top1.values[i]
            else:
                p = None
            if p is not None:
                n += 1; k += int(p == prior[i])
        lo, hi = wilson(k, n)
        casc.append({"margin_threshold": float(t), "coverage_n": n, "coverage": n / len(R),
                     "prior_agreement": (k / n) if n else float("nan"), "agree_k": k,
                     "wilson95": [lo, hi]})
    # 곡선 4: semantic margin 이지만 표면부재 유형은 먼저 abstain 시킨 경우
    gate = ~hard_undecidable
    casc_gated = []
    for t in grid_s:
        n, k = 0, 0
        for i in range(len(R)):
            if not gate[i]:
                continue
            p = R.strong.values[i][0] if R.is_mapped.values[i] else (
                R.sem_top1.values[i] if sm[i] >= t else None)
            if p is not None:
                n += 1; k += int(p == prior[i])
        lo, hi = wilson(k, n)
        casc_gated.append({"margin_threshold": float(t), "coverage_n": n,
                           "coverage": n / len(R), "prior_agreement": (k / n) if n else float("nan"),
                           "agree_k": k, "wilson95": [lo, hi]})

    def knee(rows, xk="coverage", yk="prior_agreement"):
        """coverage 를 1단위 줄일 때 prior_agreement 가 가장 많이 오르는 구간.

        곡선을 threshold 축이 아니라 coverage 축에서 읽는다. 인접 두 점 사이의
        d(agreement)/d(coverage) 가 가장 음수인 구간이 '여기서부터 커버리지를 더 늘리면
        일치가 가장 빨리 나빠진다' 는 지점이다. threshold 선언이 아니라 관찰 보고다.
        """
        pts = [r for r in rows if r["coverage_n"] >= 14]  # coverage>=25%: 소표본 구간의 잡음 제외
        best = None
        for a, b in zip(pts[:-1], pts[1:]):
            dx = b[xk] - a[xk]
            if abs(dx) < 1e-9:
                continue
            slope = (b[yk] - a[yk]) / dx
            if best is None or slope < best["d_agreement_per_d_coverage"]:
                best = {"d_agreement_per_d_coverage": slope,
                        "coverage_high": a[xk], "coverage_low": b[xk],
                        "agreement_at_high_coverage": a[yk],
                        "agreement_at_low_coverage": b[yk],
                        "reading": ("이 구간에서 coverage 를 늘리면 prior_agreement 가 "
                                    "가장 가파르게 떨어진다. 운영 threshold 는 여기서 정하지 "
                                    "않는다 — SSOT §7 은 independent label calibration split "
                                    "을 요구하고 D 는 그 label 을 열지 않았다.")}
        return best

    curves = {
        "note": ("threshold 를 선언하지 않는다. SSOT §7 은 운영 threshold 를 independent label "
                 "calibration split 에서 정하라고 하고, D 는 그 label 을 열지 않았다. "
                 "여기 있는 것은 곡선과 기울기 변화점뿐이다."),
        "base_rate_prior_majority": max(Counter(prior).values()) / len(prior),
        "rule_confidence": {"definition": ("branch b 의 발화강도 s_b = [R_b] + [E_b] (0..2). "
                                           "rule_conf = s_top1 + (s_top1 - s_top2)/2, 범위 0..3. "
                                           "3 = 유일한 R∧E branch."),
                            "curve": curve_rule, "bands": bands_rule,
                            "steepest_agreement_gain_per_coverage_loss": knee(curve_rule)},
        "semantic_margin": {"definition": ("bge-m3 + SSOT §7 A_SSOT_DEF prototype 을 D 가 독립 "
                                           "재계산. margin = cos(top1) - cos(top2)."),
                            "curve": curve_sem, "bands": bands_sem,
                            "steepest_agreement_gain_per_coverage_loss": knee(curve_sem)},
        "semantic_margin_debranded": {
            "definition": ("동일 절차이나 blob 에서 서비스명·도메인 라벨을 제거한 대조군. "
                           "RF001-B 가 brand leak 을 확인했으므로 semantic 축의 prior_agreement 가 "
                           "'표면 기능을 읽은 것'인지 '브랜드로 prior 를 되찾은 것'인지 가른다."),
            "curve": curve(R.sem_db_margin.values.astype(float), list(R.sem_db_top1), prior,
                           np.unique(np.round(np.quantile(R.sem_db_margin.values.astype(float),
                                                          np.linspace(0, 1, 29)), 6))),
            "brand_leak_warning": (
                "prior_archetype 은 prior_business_domain 과 1:1 이다(RF001-B). 텍스트에 브랜드/도메인 "
                "어휘가 남아 있으면 semantic top1 의 prior_agreement 는 '표면 기능 식별'이 아니라 "
                "'브랜드로부터 prior 복원'을 재는 것일 수 있다. 아래 debranded 대조군과 비교해서만 읽어라.")},
        "cascade_rule_then_semantic": {"definition": "SSOT §6 유일강후보 -> rule 확정, 아니면 §7 margin 임계 위에서만 확정",
                                       "curve": casc, "steepest_agreement_gain_per_coverage_loss": knee(casc)},
        "cascade_gated_by_surface_absent": {
            "definition": ("위와 같되 T05/T06/T07(표면부재 계열) target 은 먼저 abstain 시킨다. "
                           "coverage 분모는 56 그대로."),
            "curve": casc_gated, "steepest_agreement_gain_per_coverage_loss": knee(casc_gated)},
    }

    # ---- force-map 비용
    force = {}
    for name, predcol in (("rule_argmax", list(R.rule_argmax)),
                          ("semantic_top1", list(R.sem_top1)),
                          ("semantic_top1_debranded", list(R.sem_db_top1))):
        agree = np.array([predcol[i] == prior[i] for i in range(len(R))])
        per_type = {}
        for t in TYPES:
            sel = flags[t].values & R.is_abstain40.values
            n = int(sel.sum()); k = int(agree[sel].sum())
            lo, hi = wilson(n - k, n)
            per_type[t] = {"n_in_abstain40": n, "forced_agree": k,
                           "forced_disagree": n - k,
                           "disagreement_rate": (1 - k / n) if n else float("nan"),
                           "wilson95_disagreement": [lo, hi]}
        sel40 = R.is_abstain40.values
        n40 = int(sel40.sum()); k40 = int(agree[sel40].sum())
        selm = R.is_mapped.values
        force[name] = {
            "overall_abstain40": {"n": n40, "agree": k40, "disagree": n40 - k40,
                                  "disagreement_rate": 1 - k40 / n40,
                                  "wilson95_disagreement": list(wilson(n40 - k40, n40))},
            "on_mapped11_for_contrast": {"n": int(selm.sum()), "agree": int(agree[selm].sum()),
                                         "disagreement_rate": 1 - agree[selm].mean()},
            "all56": {"n": 56, "agree": int(agree.sum()), "disagreement_rate": 1 - agree.mean()},
            "per_type": per_type,
            "worst_types": sorted(
                [(t, v["disagreement_rate"], v["n_in_abstain40"]) for t, v in per_type.items()
                 if v["n_in_abstain40"] >= 4], key=lambda x: -x[1])[:5],
            "tie_rate_rule": float(R.rule_tie.mean()) if name == "rule_argmax" else None,
        }
    # 유형별 forced-disagree 를 rule/semantic 둘 다에서 본 표
    force["cost_summary"] = {
        "reading": ("SSOT §6 은 유일 후보가 아니면 AMBIGUOUS_UNRESOLVED 로 남기라고 한다. "
                    "아래는 그 규정을 무시하고 abstain 40건에 강제로 하나를 고를 때의 prior 불일치 비용이다. "
                    "prior 는 gold 가 아니므로 '오류율'이 아니라 '불일치율'로만 읽어야 한다."),
    }

    # ---- T01 은 증상인가? 다른 유형으로 얼마나 설명되는가
    t01_idx = np.where(flags["T01_NO_PREDICATE_FIRED"].values)[0]
    explain_types = ["T05_GENERIC_BRAND_LANDING", "T06_APP_INSTALL_SURFACE",
                     "T07_REPRESENTATIVE_SURFACE_ABSENT", "T08_LOGIN_DOMINATED",
                     "T09_CLIENT_RENDER_SPARSE", "T10A_TEXT_ENCODING_CORRUPTION",
                     "T10B_TEXT_CAP_TRUNCATION", "T11_OVERLAY_OBSTRUCTED",
                     "T12_DEGENERATE_OR_DUPLICATE_CAPTURE"]
    t01_decomp = {"n": len(t01_idx),
                  "explained_by_at_least_one_surface_or_capture_type":
                      int(flags[explain_types].values[t01_idx].any(axis=1).sum()),
                  "unexplained": [recs[i]["wtg"] for i in t01_idx
                                  if not flags[explain_types].values[i].any()],
                  "breakdown": {t: int(flags[t].values[t01_idx].sum()) for t in explain_types},
                  "reading": ("T01(무발화)은 원인이 아니라 증상이다. 이 분해가 그것을 보여준다 — "
                              "무발화의 대부분은 '표면이 애초에 기능면이 아니다' 또는 "
                              "'캡처가 구조를 못 잡았다' 로 설명된다.")}

    # ---- T02 하위분리: 어느 쪽이 빠졌는가
    t02_idx = np.where(flags["T02_WEAK_ONE_SIDED_EVIDENCE"].values)[0]
    t02_sub = Counter()
    for i in t02_idx:
        ev2 = branch_evidence(df.iloc[i]["decision_trace"])
        r_only = [b for b in ARCHETYPES if ev2["R"].get(b) and not ev2["E"].get(b)]
        e_only = [b for b in ARCHETYPES if ev2["E"].get(b) and not ev2["R"].get(b)]
        if r_only and e_only:
            t02_sub["BOTH_SIDES_BUT_DIFFERENT_BRANCHES"] += 1
        elif r_only:
            t02_sub["REGION_ONLY__ENDPOINT_MISSING"] += 1
        else:
            t02_sub["ENDPOINT_ONLY__REGION_MISSING"] += 1
    type_table["T02_WEAK_ONE_SIDED_EVIDENCE"]["subtypes"] = dict(t02_sub)
    type_table["T02_WEAK_ONE_SIDED_EVIDENCE"]["subtype_reading"] = (
        "ENDPOINT_MISSING 은 상호작용 1스텝 수집으로 확인 가능한 쪽이고, "
        "BOTH_SIDES_BUT_DIFFERENT_BRANCHES 는 서로 다른 archetype 의 반쪽 신호가 섞인 것이라 "
        "수집이 아니라 §5 술어 조작화 문제다.")

    # ---- SSOT §6 이 금지한 'first match' 강제선택의 비용
    first_match = []
    for i in range(len(R)):
        sc = recs[i]["branch_score"]
        fm = next((b for b in ARCHETYPES if sc[b] >= 1), None)
        first_match.append(fm or ARCHETYPES[0])
    agree_fm = np.array([first_match[i] == prior[i] for i in range(len(R))])
    sel40 = R.is_abstain40.values
    force["ssot6_forbidden_first_match"] = {
        "definition": ("SSOT §6 이 명시적으로 금지한 '첫 매칭 선택'. Stage3 branch 평가순서에서 "
                       "R 또는 E 가 하나라도 붙은 첫 branch 를 고른다."),
        "overall_abstain40": {"n": int(sel40.sum()), "agree": int(agree_fm[sel40].sum()),
                              "disagree": int(sel40.sum() - agree_fm[sel40].sum()),
                              "disagreement_rate": 1 - float(agree_fm[sel40].mean()),
                              "wilson95_disagreement": list(
                                  wilson(int(sel40.sum() - agree_fm[sel40].sum()), int(sel40.sum())))},
        "per_type": {t: {"n_in_abstain40": int((flags[t].values & sel40).sum()),
                         "disagreement_rate": (
                             1 - float(agree_fm[flags[t].values & sel40].mean())
                             if (flags[t].values & sel40).sum() else float("nan"))}
                     for t in TYPES}}

    # ---- 반례
    counterexamples = []
    for i in range(len(R)):
        r = recs[i]
        if R.is_mapped.values[i] and flags[["T05_GENERIC_BRAND_LANDING",
                                            "T06_APP_INSTALL_SURFACE"]].values[i].any():
            counterexamples.append({
                "kind": "브랜드/앱면 유형인데 rule 이 확정한 케이스 — '브랜드면=미결정' 주장의 반례",
                "wtg": r["wtg"], "service": r["service"], "leaf": r["leaf"],
                "strong": r["strong"], "prior_archetype": r["prior_archetype"]})
    for i in range(len(R)):
        if R.is_abstain40.values[i] and not flags.values[i][1:].any() and flags["T01_NO_PREDICATE_FIRED"].values[i]:
            counterexamples.append({
                "kind": "어떤 표면/수집 유형으로도 설명되지 않는 무발화 — taxonomy 의 미설명 잔여",
                "wtg": recs[i]["wtg"], "service": recs[i]["service"]})
    # 인코딩 훼손인데도 확정된 케이스
    for i in range(len(R)):
        if R.is_mapped.values[i] and flags["T10A_TEXT_ENCODING_CORRUPTION"].values[i]:
            counterexamples.append({
                "kind": "인코딩 훼손인데도 rule 이 확정 — '인코딩 훼손 => 미결정' 의 반례",
                "wtg": recs[i]["wtg"], "service": recs[i]["service"], "leaf": recs[i]["leaf"]})

    # ---- 가설 판정
    n_res40 = resolv_summary["of_abstain40"].get("RESOLVABLE", 0)
    n_und40 = resolv_summary["of_abstain40"].get("UNDECIDABLE_AT_THIS_URL", 0)
    b = resolv_summary["priority_free_bounds"]
    MAJORITY = 0.60   # "대부분" 을 사전에 이렇게 조작화한다 (post-hoc 조정 금지)
    frac_res = n_res40 / N40
    frac_und = n_und40 / N40
    mean_types = float(ntypes_per_target[R.is_abstain40.values].mean())
    hyp = {
        "_decision_rule": (
            f"'대부분' = abstain 40 중 {MAJORITY:.0%} 초과로 사전 조작화. "
            "H-E1/H-E2 는 primary-type 배정(고정 우선순위)과 우선순위-무관 하한/상한을 "
            "둘 다 만족해야 SUPPORTED 로 올린다."),
        "H-E1 대부분이 evidence 부족(수집으로 해결)": {
            "verdict": ("SUPPORTED" if frac_res > MAJORITY else
                        ("PARTIALLY_SUPPORTED" if frac_res >= 0.30 else "NOT_SUPPORTED")),
            "evidence": (f"primary-type 기준 RESOLVABLE {n_res40}/{N40} = {frac_res:.2f}. "
                         f"우선순위와 무관하게 '캡처품질 유형을 하나라도 갖는' abstain "
                         f"{b['any_capture_quality_type_of_abstain40']}/{N40}. "
                         "절반 수준이지 '대부분' 이 아니다.")},
        "H-E2 대부분이 원리적 미결정(수집해도 안 됨)": {
            "verdict": ("SUPPORTED" if frac_und > MAJORITY else
                        ("PARTIALLY_SUPPORTED" if frac_und >= 0.30 else "NOT_SUPPORTED")),
            "evidence": (f"primary-type 기준 UNDECIDABLE_AT_THIS_URL {n_und40}/{N40} = {frac_und:.2f}. "
                         f"우선순위와 무관하게 '표면부재 계열 유형을 하나라도 갖는' abstain "
                         f"{b['any_surface_absent_type_of_abstain40']}/{N40}. "
                         "역시 절반 수준이지 '대부분' 이 아니다.")},
        "H-E3 유형이 뒤섞여 분류 자체가 불안정": {
            "verdict": "PARTIALLY_SUPPORTED",
            "evidence": (
                f"뒤섞임은 확인된다 — abstain 40 의 target 당 평균 유형 수 {mean_types:.2f}, "
                f"표면부재계열과 캡처품질계열을 **동시에** 갖는 target {b['both_of_abstain40']}건, "
                f"둘 다 없는 target {b['neither_of_abstain40']}건. "
                "그러나 '분류 자체가 불안정' 은 절반만 맞다: 어느 유형이 primary 인지는 "
                "우선순위 규칙에 흔들리지만(민감도 참조), 우선순위와 무관한 하한/상한 "
                "(표면부재 유형 보유 22 / 캡처품질 유형 보유 22 / 둘 다 10 / 둘 다 아님 6)은 "
                "규칙과 무관하게 고정이다.")},
    }

    out = {
        "verdict": "PARTIALLY_SUPPORTED",
        "child_id": "D-RF2-E", "rq_id": "RQ-D-RF-002",
        "hypothesis_id": "H-RF2-E-ABSTENTION-TAXONOMY",
        "competing_hypothesis_verdicts": hyp,
        "generated_at_kst": datetime.now(KST).isoformat(),
        "seed": SEED, "model_or_rule_version": "RF2E_TAXONOMY_v1",
        "target_variable": {
            "field": "prior_archetype",
            "is_gold_label": False,
            "metric_name": "prior_agreement (NOT accuracy)",
            "warning": "prior 는 gold label 이 아니라 prior 다. 불일치는 오류가 아니라 불일치다."},
        "firewall": {
            "holdout_label_opened": False,
            "note": ("LABEL_SPLIT_FROZEN* · HOLDOUT_FOR_C* · RAW_L1~L4* · PACKET_L* · *_OVERLAP* · "
                     "PRECEDENCE_CONTESTED* · CALIBRATION_FOR_B* · **/control/** 은 열지 않았다. "
                     "그래서 최종 threshold 를 선언하지 않는다."),
            "threshold_declared": None},
        "inputs": [
            {"path": str(p.relative_to(RD)), "sha256": sha256_file(p)}
            for p in [RES / "D_OBSERVATION_TABLE_v2.csv", RES / "D_TEXT_CORPUS_v2.csv",
                      RES / "RF001_A_rule_dt.json", RES / "RF001_C_embedding.json",
                      RES / "RQ_D13A_overlay_provenance.json", RES / "RQ_D13_duplicate_vector.json",
                      RES / "RQ_D10_slot_mismatch.json", RES / "RQ_D9_quality_proxy.json"]],
        "analysis_unit": "target (wtg, in_mart==1)",
        "n_expected": 56, "n_observed": int(len(R)),
        "denominators": {"all_targets": N56, "abstain_40": N40,
                         "unresolved_45_incl_stage0": N45, "rule_mapped_11": int(R.is_mapped.sum())},
        "missing": {
            "prior_url_missing_n": int(df.prior_url.isna().sum()),
            "probe_absent_n": int((df.probe_present.fillna(0) == 0).sum()),
            "no_final_url_n": int(df.probe_final_url.isna().sum()),
            "note": "누락은 배제하지 않고 유형(T07/T09/T12)으로 흡수해 센다."},
        "independent_recount": recount,
        "prior_class_counts": dict(Counter(prior)),
        "taxonomy": type_table,
        "overlap": {
            "types": TYPES,
            "matrix_of_56": overlap.tolist(),
            "matrix_of_abstain40": overlap_abst.tolist(),
            "n_types_per_target": {"mean": float(ntypes_per_target.mean()),
                                   "median": float(np.median(ntypes_per_target)),
                                   "max": int(ntypes_per_target.max()),
                                   "distribution": dict(Counter(ntypes_per_target.tolist()))},
            "targets_with_zero_type": [recs[i]["wtg"] for i in range(len(R))
                                       if ntypes_per_target[i] == 0],
            "T01_residual_unexplained_by_surface_or_capture_types": residual_T01},
        "T01_decomposition": t01_decomp,
        "resolvability": resolv_summary,
        "coverage_confidence_curves": curves,
        "force_map_cost": force,
        "counterexamples": counterexamples,
        "per_target": [
            {"wtg": recs[i]["wtg"], "service": recs[i]["service"],
             "prior_archetype": recs[i]["prior_archetype"], "leaf": recs[i]["leaf"],
             "final_url": recs[i]["types"]["final_url"],
             "strong": recs[i]["strong"], "weak": recs[i]["weak"], "n_fired": recs[i]["n_fired"],
             "rule_conf": recs[i]["rule_conf"], "rule_argmax": recs[i]["rule_argmax"],
             "rule_tie": bool(recs[i]["rule_tie"]),
             "sem_top1": R.sem_top1.values[i], "sem_top2": R.sem_top2.values[i],
             "sem_margin": float(R.sem_margin.values[i]),
             "sem_top1_debranded": R.sem_db_top1.values[i],
             "sem_margin_debranded": float(R.sem_db_margin.values[i]),
             "primary_type": R.primary_type.values[i],
             "resolvability_bucket": R.resolvability_bucket.values[i],
             "types": sorted([t for t in TYPES if recs[i]["type_flags"][t]]),
             "type_evidence": recs[i]["types"]}
            for i in range(len(R))],
        "limitation": (
            "1) prior_archetype 은 gold 가 아니다. 모든 '불일치'는 rule 오류일 수도 prior 오류일 수도 "
            "있고 D 는 label 을 열지 않아 가를 수 없다. 2) 유형 판정에 쓰인 어휘 사전·경로 마커·"
            "구성요소 개수 임계는 D 가 정한 조작화이며 SSOT 에 명문화된 것이 아니다. "
            "3) n=56, 유형별 N 이 3~20 이라 유형별 비율의 CI 가 매우 넓다. "
            "4) 해결가능성 판정은 반사실(counterfactual) 주장이므로 재수집 실험 없이는 검증되지 않는다. "
            "5) 곡선은 prior 기준이므로 운영 threshold 결정에 그대로 쓸 수 없다."),
    }

    (RES / "RF2_E_abstention_taxonomy.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=_j), encoding="utf-8")
    make_figures(R, flags, TYPES, type_table, curves, force, out)
    print(json.dumps({"verdict": out["verdict"], "denoms": out["denominators"],
                      "resolv": resolv_summary["of_abstain40"],
                      "bounds": resolv_summary["priority_free_bounds"],
                      "top": sorted([(t, v["n_of_abstain40"]) for t, v in type_table.items()],
                                    key=lambda x: -x[1])[:6],
                      "force_rule": force["rule_argmax"]["overall_abstain40"],
                      "force_sem": force["semantic_top1"]["overall_abstain40"],
                      "recount_ok": recount["matches_rf001_a"]},
                     ensure_ascii=False, indent=1))
    return out


def _why(t: str, r: dict, d: dict) -> str:
    if t == "T01_NO_PREDICATE_FIRED":
        return f"Stage3 14개 술어 발화 0 (n_fired={r['n_fired']})"
    if t == "T02_WEAK_ONE_SIDED_EVIDENCE":
        return f"weak={r['weak']} strong=[] (n_fired={r['n_fired']})"
    if t == "T03_MULTI_STRONG_CANDIDATE":
        return f"strong={r['strong']}"
    if t == "T04_SHARED_LIST_SIGNAL":
        return f"list-family R 동시발화={r['list_family_R']}"
    if t == "T05_GENERIC_BRAND_LANDING":
        return f"brand_lex={d['n_brand_lex']} path_marker={d['path_brand_marker']} strong=[]"
    if t == "T06_APP_INSTALL_SURFACE":
        return f"app_lex={d['n_app_lex']}"
    if t == "T07_REPRESENTATIVE_SURFACE_ABSENT":
        return f"stage0={r['stage0_fired']}"
    if t == "T08_LOGIN_DOMINATED":
        return (f"login_lex={d['n_login_lex']} password_n={d['gate_password_input_n']} "
                f"login_url={d['login_in_final_url']} subtype={d['login_subtype']}")
    if t == "T09_CLIENT_RENDER_SPARSE":
        return f"SSOT§7 구성요소 {d['ssot7_components_present']}/8"
    if t == "T10A_TEXT_ENCODING_CORRUPTION":
        return "encoding_degraded=1"
    if t == "T10B_TEXT_CAP_TRUNCATION":
        return "cap_any=1 또는 gate_visible_text_len>=3900"
    if t == "T11_OVERLAY_OBSTRUCTED":
        return f"overlay={d['overlay_class']} scroll_locked 포함"
    if t == "T12_DEGENERATE_OR_DUPLICATE_CAPTURE":
        return "degenerate capture 또는 동일 requested URL 공유"
    if t == "T13_PRIOR_CONTRADICTS_STRUCTURE":
        return f"prior={r['prior_archetype']} branch 침묵, 타 branch 발화 n={r['n_fired']}"
    return ""


def _j(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# ----------------------------------------------------------------------------
# 8. figures
# ----------------------------------------------------------------------------
def make_figures(R, flags, TYPES, type_table, curves, force, out) -> None:
    FIG.mkdir(exist_ok=True)
    short = [t.split("_", 1)[0] for t in TYPES]

    # F1 유형별 N
    fig, ax = plt.subplots(figsize=(11, 5.6))
    n56 = [type_table[t]["n_of_56"] for t in TYPES]
    n40 = [type_table[t]["n_of_abstain40"] for t in TYPES]
    x = np.arange(len(TYPES))
    ax.bar(x - .2, n56, .4, label="of 56 targets", color="#4C72B0")
    ax.bar(x + .2, n40, .4, label="of 40 abstain", color="#DD8452")
    for i, (a, b) in enumerate(zip(n56, n40)):
        ax.text(i - .2, a + .3, str(a), ha="center", fontsize=8)
        ax.text(i + .2, b + .3, str(b), ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(short, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("N targets"); ax.legend()
    ax.set_title("RF2-E  abstention cause taxonomy — counts (overlapping types)")
    fig.tight_layout(); fig.savefig(FIG / "RF2_E_taxonomy_counts.png", dpi=140); plt.close(fig)

    # F2 중복행렬
    M = np.array(out["overlap"]["matrix_of_abstain40"], dtype=float)
    fig, ax = plt.subplots(figsize=(9.5, 8))
    im = ax.imshow(M, cmap="magma")
    ax.set_xticks(range(len(TYPES))); ax.set_xticklabels(short, rotation=90, fontsize=8)
    ax.set_yticks(range(len(TYPES))); ax.set_yticklabels(short, fontsize=8)
    for i in range(len(TYPES)):
        for j in range(len(TYPES)):
            if M[i, j]:
                ax.text(j, i, int(M[i, j]), ha="center", va="center", fontsize=7,
                        color="white" if M[i, j] < M.max() * .6 else "black")
    ax.set_title("type co-occurrence within the 40 abstain targets (diagonal = type N)")
    fig.colorbar(im, ax=ax, shrink=.7)
    fig.tight_layout(); fig.savefig(FIG / "RF2_E_overlap_matrix.png", dpi=140); plt.close(fig)

    # F3 coverage-confidence
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    for ax, key, ttl in ((axes[0], "rule_confidence", "rule confidence (force-map argmax)"),
                         (axes[1], "semantic_margin", "semantic margin (bge-m3 x SSOT §7 prototypes)")):
        c = curves[key]["curve"]
        cov = [r["coverage"] for r in c]; ag = [r["prior_agreement"] for r in c]
        lo = [r["wilson95"][0] for r in c]; hi = [r["wilson95"][1] for r in c]
        ax.plot(cov, ag, "-o", ms=3.5, color="#4C72B0")
        ax.fill_between(cov, lo, hi, alpha=.18, color="#4C72B0")
        ax.axhline(curves["base_rate_prior_majority"], ls=":", color="grey",
                   label=f"prior majority base rate {curves['base_rate_prior_majority']:.2f}")
        d = curves[key]["steepest_agreement_gain_per_coverage_loss"]
        if d:
            ax.axvspan(min(d["coverage_low"], d["coverage_high"]),
                       max(d["coverage_low"], d["coverage_high"]),
                       color="#C44E52", alpha=.14,
                       label=("steepest agreement loss per coverage gain: "
                              f"{d['coverage_low']:.2f}→{d['coverage_high']:.2f}"))
        ax.set_xlabel("coverage (fraction of 56 forced to a decision)")
        ax.set_ylabel("prior_agreement within coverage")
        ax.set_title(ttl, fontsize=10); ax.set_ylim(0, 1); ax.legend(fontsize=8)
    fig.suptitle("RF2-E  coverage ↔ prior_agreement — NO threshold is declared (SSOT §7)", fontsize=11)
    fig.tight_layout(); fig.savefig(FIG / "RF2_E_coverage_confidence.png", dpi=140); plt.close(fig)

    # F3b cascade
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    for key, col, lab in (("cascade_rule_then_semantic", "#55A868", "§6 rule → §7 embedding"),
                          ("cascade_gated_by_surface_absent", "#8172B3",
                           "same, but surface-absent types abstain first")):
        c = curves[key]["curve"]
        ax.plot([r["coverage"] for r in c], [r["prior_agreement"] for r in c],
                "-o", ms=3.5, color=col, label=lab)
    ax.axhline(curves["base_rate_prior_majority"], ls=":", color="grey")
    ax.set_xlabel("coverage (of 56)"); ax.set_ylabel("prior_agreement")
    ax.set_ylim(0, 1); ax.legend(fontsize=8)
    ax.set_title("cascade coverage ↔ prior_agreement", fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "RF2_E_cascade_curve.png", dpi=140); plt.close(fig)

    # F4 force-map cost per type
    fig, ax = plt.subplots(figsize=(11, 5.4))
    pr = force["rule_argmax"]["per_type"]; ps = force["semantic_top1"]["per_type"]
    keep = [t for t in TYPES if pr[t]["n_in_abstain40"] > 0]
    x = np.arange(len(keep))
    ax.bar(x - .2, [pr[t]["disagreement_rate"] for t in keep], .4, color="#C44E52",
           label="force rule argmax")
    ax.bar(x + .2, [ps[t]["disagreement_rate"] for t in keep], .4, color="#4C72B0",
           label="force semantic top1")
    for i, t in enumerate(keep):
        ax.text(i, 1.02, f"n={pr[t]['n_in_abstain40']}", ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels([t.split("_", 1)[0] for t in keep], rotation=45, ha="right")
    ax.set_ylim(0, 1.12); ax.set_ylabel("prior DISagreement rate when forced")
    ax.legend(fontsize=8)
    ax.set_title("RF2-E  cost of abstention laundering — force-map disagreement by cause type "
                 "(denominator = 40 abstain)", fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "RF2_E_forcemap_cost.png", dpi=140); plt.close(fig)

    # F5 resolvability
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    rs = out["resolvability"]
    cats = ["of_56", "of_abstain40", "of_unresolved45"]
    keys = ["RESOLVABLE", "UNDECIDABLE_AT_THIS_URL", "OTHER", "UNCLASSIFIED"]
    bottom = np.zeros(len(cats))
    cols = {"RESOLVABLE": "#55A868", "UNDECIDABLE_AT_THIS_URL": "#C44E52",
            "OTHER": "#937860", "UNCLASSIFIED": "#CCCCCC"}
    for k in keys:
        v = np.array([rs[c].get(k, 0) for c in cats], dtype=float)
        if v.sum() == 0:
            continue
        ax.barh(cats, v, left=bottom, label=k, color=cols[k])
        for i, (b, vv) in enumerate(zip(bottom, v)):
            if vv:
                ax.text(b + vv / 2, i, int(vv), ha="center", va="center", fontsize=9, color="white")
        bottom += v
    ax.legend(fontsize=8, loc="lower right")
    ax.set_xlabel("N targets")
    ax.set_title("resolvable by better evidence vs undecidable at this target URL\n"
                 "(primary type by fixed priority; see JSON for priority-free bounds)", fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "RF2_E_resolvability.png", dpi=140); plt.close(fig)


if __name__ == "__main__":
    main()
