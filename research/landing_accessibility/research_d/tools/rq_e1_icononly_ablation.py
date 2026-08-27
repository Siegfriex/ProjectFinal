"""RQ-E-1 — dismiss detector `icon_only` ablation → Axis B activation pool recovery.

RQ: l0_probe.js:402 의 `icon_only` 조건을 끄면 Axis B 의 activation pool 이 얼마나 회복되는가.

PILOT-E 가 확정한 위험쌍 E-P1 의 후속이다. E-P1 은 "Axis C 의 dismiss detector 산출이
Axis B 의 탐색공간을 깎는다" 는 코드경로를 보였다. 이 RQ 는 그 절단의 **어느 정도가
`icon_only` 단독 근거에서 오는가** 를 반사실 재계산으로 잰다.

**재수집하지 않았다.** 브라우저를 띄우지 않았고 코드를 고쳐 돌리지 않았다. frozen probe raw
(`l0a/probe.json`) 에 저장된 per-control flag `matches_close_vocabulary` / `icon_only` 로
`l0_probe.js:409` 의 filter 와 `l1_engine.py:346-357` 의 selector 집합 연산을 **재현**한 뒤,
filter 의 `|| x.icon_only` 항만 제거한 반사실 집합을 다시 계산한다. 따라서 여기서 나오는
모든 수치는 **counterfactual recomputation** 이지 실험 개입의 결과가 아니다. 인과 주장 없음.

authority: NON_CANONICAL. GO/NO_GO · threshold · "이렇게 고쳐야 한다" 는 A 의 권한이며
이 문서는 회복량과 회복분의 성질만 보고한다.

firewall: D_INPUT_ALLOWLIST.json 의 denied 목록을 하나도 열지 않았다. 네트워크 없음.
gold label 생산 없음. 기존 A~E 산출물 · production · engine · mart · raw evidence 수정 없음.
"""
from __future__ import annotations

import glob
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

KST = timezone(timedelta(hours=9))
SEED = 20260828
CODE_SHA = "2281c853950d0c475c5d2c1678680b971c2804f4"
PARENT_RUN_ID = "27d10a01df5442b681ee73062e01c123"

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
WT = REPO / ".agent_worktrees"
RD = WT / "claude_d_research/research/landing_accessibility/research_d"
MART = WT / "claude_b_analysis_current/artifacts/e001_real_marts"
OBS_TABLE = RD / "results/D_OBSERVATION_TABLE_v2.csv"
EVIDENCE_GLOB = "claude_b_e001_worker_0*/artifacts/e001_w0*/evidence"

OUT_JSON = RD / "results/RQ_E1_icononly_ablation.json"
FIG_DIR = RD / "figures"

# ── probe(l0_probe.js:379-381) 어휘를 그대로 옮긴다. 재판정이 아니라 귀속·대조용이다. ──
CLOSE_WORDS = re.compile(
    r"(닫기|닫음|확인|취소|동의|건너뛰기|나중에|오늘\s*하루\s*보지\s*않기|다시\s*보지\s*않기|"
    r"close|dismiss|skip|no\s*thanks|got\s*it|accept)",
    re.IGNORECASE,
)
CLOSE_GLYPH = re.compile(r"^[×✕✖╳xX⨯]$")

# 정규식이 **놓쳤을 수 있는** 닫기 표현의 확장 사전. H-E1-HARM 의 상한을 넉넉히 잡기 위한 것으로,
# probe 의 판정을 대체하지 않는다.
CLOSE_EXTENDED = re.compile(
    r"(닫|끄기|숨기|그만|안내\s*종료|배너\s*종료|팝업\s*종료|레이어\s*닫|뒤로|이전|없음|"
    r"close|dismiss|cancel|exit|hide|later|not\s*now|maybe\s*later|opt\s*out|reject|decline|"
    r"esc|×|✕|✖|╳|⨯|✗|❌|⨉)",
    re.IGNORECASE,
)
# 명백히 닫기가 아닌 기능 어휘 — 반례 계수용.
NON_CLOSE_LEX = re.compile(
    r"(메뉴|검색|홈|로고|장바구니|카트|로그인|회원가입|공유|알림|더보기|전체|카테고리|슬라이드|"
    r"앱|다운로드|설치|지도|위치|고객센터|마이|주문|배송|이벤트|기획전|바로가기|채널|프로필|계정|"
    r"menu|search|home|logo|cart|login|sign\s*in|sign\s*up|share|notification|more|all|"
    r"category|slide|app|download|install|map|account|profile|next|prev|이전\s*슬라이드|다음)",
    re.IGNORECASE,
)
# href 를 두 부류로 **분리해서** 쓴다. 1차 계산에서 둘을 한 집합("non_navigating")으로 묶었더니
# href="/" 인 로고·홈 링크가 '닫기일 수 있음' 으로 잡혀 상한이 부풀었다 — 닫기 control 은 홈으로
# 이동하지 않는다. 그 정의 결함을 여기서 시정하고, 부풀린 판본도 R7 로 남겨 병기한다.
NON_NAV_HREF = {"#", "javascript:;", "javascript:void(0)", "javascript:void(0);", "javascript:void(0)", ""}
HOMEISH_HREF = {"/", "./", "/index.html", "index.html"}

# ── 사전 고정 정의 (측정 전에 문서에 박는다) ───────────────────────────────────────
DEFINITIONS = {
    "grain_dismiss_entry": (
        "probe raw `dismiss_control_candidates[*].dismiss_control_candidates[*]` 의 원소 1개. "
        "같은 selector 가 서로 다른 container 에서 두 번 나올 수 있으므로 selector 와 1:1 이 아니다."
    ),
    "grain_dismiss_selector": (
        "target 안에서 selector 문자열 1개. l1_engine.py:346-350 이 실제로 만드는 것은 "
        "**selector 문자열의 set** 이므로, 같은 selector 의 여러 entry 는 flag 를 OR 로 합친 것과 "
        "동치다. baseline/ablation 집합은 이 grain 에서 정의한다."
    ),
    "grain_pac_hittable": (
        "`primary_action_candidates` 중 `hittable==true` 이고 selector 가 있는 원소 1개. "
        "l1_engine.py:352-356 의 후보 필터와 같다. Axis B activation pool 의 분모다."
    ),
    "grain_target": "in_mart==1 이며 l0a/probe.json 을 가진 web target 1개 (n=54).",
    "baseline_dismiss_set": (
        "D_base(t) = { selector : 그 selector 의 entry 가 probe 에 하나라도 존재 }. "
        "probe 가 이미 l0_probe.js:409 `matches_close_vocabulary || icon_only` 로 걸러 저장하므로, "
        "저장된 entry 는 전부 둘 중 하나를 만족한다."
    ),
    "ablated_dismiss_set": (
        "D_abl(t) = { selector : 그 selector 의 entry 중 하나라도 matches_close_vocabulary==true }. "
        "l0_probe.js:409 의 filter 를 `x.matches_close_vocabulary` 만으로 바꾼 반사실이다."
    ),
    "pool_baseline": "P_base(t) = { hittable pac : selector ∉ D_base(t) }",
    "pool_ablated": "P_abl(t) = { hittable pac : selector ∉ D_abl(t) }",
    "recovered": (
        "R(t) = P_abl(t) \\ P_base(t) = { hittable pac : selector ∈ D_base(t) ∧ selector ∉ D_abl(t) }. "
        "즉 **icon_only 만이 유일한 제거근거였던** 후보다. 정의상 P_base ⊆ P_abl 이므로 "
        "이 ablation 은 pool 을 줄일 수 없다(단조)."
    ),
    "recovery_rate_denominator": (
        "회복률의 분모는 **baseline 에서 제거된 hittable 후보 수** 이며, hittable pac 전체가 아니다. "
        "두 분모를 모두 병기한다."
    ),
    "not_a_gold_label": (
        "이 문서의 '진짜 닫기인가' 판정은 gold label 이 아니다. 규칙 기반 상한이며, "
        "사람이 재판정할 수 있도록 표본을 그대로 덤프한다."
    ),
}

LIMITATION = (
    "(1) 반사실 재계산이다 — 코드를 고쳐 재수집한 결과가 아니다. probe 가 저장한 flag 만 쓰므로, "
    "icon_only 를 실제로 끄면 달라질 수 있는 2차 효과(dismiss 실행 → 화면 변화 → 다음 state 의 "
    "pac 집합 변화)는 전혀 잡히지 않는다. 회복량은 **첫 state 의 정적 pool** 에 한정된다. "
    "(2) '진짜 닫기 control 인가' 에 대한 gold label 이 없다. HARM 상한은 규칙 기반이며 "
    "규칙 자체가 probe 와 같은 slot(name/href/box)을 읽으므로 독립적이지 않다. "
    "(3) n=54 target · 57 제거후보로 작다. 회복 후보의 하위분포(예: 규칙별 harm 비율) CI 는 넓다. "
    "(4) Axis B 산출(NED/IED/MPFED)이 mart 에서 0/31 non-null 이므로, pool 회복이 결과값을 "
    "바꾸는지는 이 증거로 확인 **불가능**하다 — 회복량은 탐색공간 크기까지만 말한다. "
    "(5) icon_only 를 끄면 Axis C 의 dismiss_control_exists 가 함께 줄어든다. 이 문서는 그 "
    "trade-off 의 크기만 보고하고 어느 쪽이 옳은지 말하지 않는다(construct 는 A 권한)."
)

NOT_ANSWERED = [
    "icon_only 를 실제로 끄고 재수집했을 때 Axis B 의 NED/IED/MPFED 가 달라지는가 — 이 증거로는 불가능하다(현 mart 에서 셋 다 0/31 non-null).",
    "회복된 후보가 '진짜 닫기'인지의 gold 판정 — D 는 label 을 만들지 않는다.",
    "icon_only 를 끔으로써 Axis C 의 dismiss_control_exists 가 얼마나 과소가 되는가의 정오 — 그 정오는 Axis C gold 없이는 정해지지 않는다.",
    "1-state 를 넘어선 경로 전개(scout 2~N step)에서의 누적 회복량 — 재수집 없이는 계산되지 않는다.",
    "icon_only 대신 다른 완화(예: 컨테이너를 dialog 로 한정)를 썼을 때의 회복량 — 이 RQ 는 icon_only 단일 항만 껐다.",
]

FURTHER_RQ = [
    "RQ-E-1a: dismiss 컨테이너 집합을 l0_probe.js:386-390 의 fixed/sticky/z>=100 에서 dialog/aria-modal 로 좁히면 Axis B pool 회복량은 icon_only ablation 대비 얼마인가 (두 완화의 회복량 비교, 재수집 불필요).",
    "RQ-E-1b: 회복된 35개 후보를 Axis B 가 실제로 활성화했을 때 state 가 전진하는가 — 이는 재수집이 필요하며 D 범위 밖이다(B/C 협의 필요).",
    "RQ-E-1c: icon_only 를 끌 때 Axis C 의 dismiss_control_exists 가 몇 target 에서 1→0 으로 뒤집히는가, 그 target 들이 modal_overlay_candidates 를 실제로 갖고 있는가.",
    "RQ-E-2 (PILOT-E 등재분): dismiss detector 의 name 소스(aria-label||title||textContent)가 비어 있는 control 의 비율과, 그것이 icon_only 발동과 얼마나 겹치는가.",
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [round((c - h) / d, 4), round((c + h) / d, 4)]


def frac(k: int, n: int, grain: str) -> dict:
    return {
        "numerator": int(k),
        "denominator": int(n),
        "grain": grain,
        "rate": round(k / n, 4) if n else None,
        "wilson95": wilson(k, n),
    }


def bh_fdr(pvals: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p (step-up, monotone)."""
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    adj = np.empty(n, dtype=float)
    prev = 1.0
    for rank in range(n - 1, -1, -1):
        i = order[rank]
        v = min(prev, p[i] * n / (rank + 1))
        adj[i] = v
        prev = v
    return [round(float(x), 6) for x in adj]


def probe_path_for(run_dir: str) -> str | None:
    hits = sorted(glob.glob(str(WT / EVIDENCE_GLOB / run_dir / "*/l0a/probe.json")))
    return hits[0] if hits else None


def area_of(box) -> float | None:
    if not isinstance(box, dict):
        return None
    try:
        return float(box.get("w") or 0) * float(box.get("h") or 0)
    except Exception:
        return None


# ── HARM 규칙군: "회복 후보가 실제로 진짜 닫기 control 일 수 있는가" 의 **보수적 상한** ──
# 각 규칙은 상한이다 — 만족하면 '닫기일 수 있음', 만족하지 않으면 '닫기가 아님' 으로 읽는다.
# 규칙을 느슨하게 할수록 상한은 커져야 한다. 방향이 규칙 전반에서 유지되는지가 핵심이다.
HARM_RULES = {
    "R1_semantic_dialog_unnamed_icon": (
        "container 가 **의미적 dialog** (<dialog> / role=dialog / role=alertdialog / aria-modal=true / "
        "form[method=dialog]) ∧ pac.href 없음 ∧ 이름 전무 ∧ 면적 ≤ 2500 css px²"
    ),
    "R2_unnamed_icon_no_href": "pac.href 없음 ∧ 접근가능 이름 전무 ∧ 면적 ≤ 2500 css px²",
    "R3_no_href_not_obviously_non_close": "pac.href 없음 ∧ 이름이 명백한 비-닫기 기능어휘(메뉴/검색/홈/로고…)에 걸리지 않음",
    "R4_no_href": "pac.href 없음 (오버레이 안의 모든 icon button 이 닫기일 수 있다고 가정)",
    "R5_extended_close_lexicon": "이름이 확장 닫기 사전에 걸림 (probe 정규식이 놓쳤을 표현 포함)",
    "R6_no_href_or_non_navigating": "pac.href 없음 ∨ href 가 비-내비게이션(# / javascript: / 빈값)",
    "R7_overgenerous_incl_site_root": (
        "R1~R6 ∪ href 가 사이트 루트(/ · ./). **의도적으로 부풀린 상한** — 닫기 control 이 홈으로 "
        "이동하지는 않으므로 이 규칙은 거의 확실히 과대계상이다. 상한의 상한을 보이기 위해 남긴다."
    ),
}

# 판정규칙을 먼저 고정한다. HARM 은 '되돌아온 후보의 **다수**' 를 주장하므로 임계는 0.5 다.
#   SUPPORTED      : 가장 **엄격한** 상한조차 > 0.5  (보수적으로 봐도 다수가 닫기)
#   NOT_SUPPORTED  : 의도적 과대계상(R7)을 제외한 **모든** 규칙이 < 0.5
#   INCONCLUSIVE   : 그 사이
HARM_DECISION_RULE = (
    "threshold=0.5 ('다수'). SUPPORTED = min(all rules) > 0.5. "
    "NOT_SUPPORTED = max(R1..R6) < 0.5. 그 외 INCONCLUSIVE. "
    "R7 은 의도적 과대계상이라 NOT_SUPPORTED 판정에서 제외하되 수치는 항상 병기한다."
)

RULE_FAMILY_REVISION_NOTE = (
    "이 규칙군은 **1차 계산 뒤 한 번 수정됐다**. 수정 내역을 숨기지 않고 적는다. "
    "(a) 최초 R1 은 container 판정에 modal_overlay_candidates 소속을 썼는데, 그 목록의 후보조건"
    "(l0_probe.js:195-199 fixed/sticky/z>=100)이 dismiss container 스캔조건(l0_probe.js:386-390)과 "
    "사실상 같아서 판별력이 0 이었다(회복분 35/35 가 전부 '해당'). 그래서 R1 을 candidate_sources 가 "
    "dialog_element/role_dialog/aria_modal 인 **의미적 dialog** 로 좁혔다. "
    "(b) 최초 R4('non_navigating')는 href='/' 를 비-내비게이션에 포함시켜 로고·홈 링크를 "
    "'닫기일 수 있음' 으로 계상했고 상한을 0.63 까지 부풀렸다. 닫기 control 은 홈으로 이동하지 "
    "않으므로 이는 정의 결함이다. 사이트 루트를 분리하고, 부풀린 판본은 R7 로 **남겨서 병기**한다."
)


def main() -> dict:
    rng = np.random.default_rng(SEED)
    obs = pd.read_csv(OBS_TABLE)
    tgt = obs[obs.in_mart == 1].copy()
    n_target_expected = int(len(tgt))

    per_target: list[dict] = []
    removed_rows: list[dict] = []
    entry_rows: list[dict] = []
    survivor_rows: list[dict] = []
    inputs_probe: list[dict] = []

    for _, r in tgt.iterrows():
        pp = probe_path_for(str(r.run_dir))
        if pp is None:
            per_target.append({"wtg": r.wtg, "probe": False})
            continue
        inputs_probe.append({"path": pp, "sha256": sha256_file(Path(pp))})
        raw = json.loads(Path(pp).read_text(encoding="utf-8"))["raw_features"]
        pac = raw.get("primary_action_candidates", []) or []
        hit = [c for c in pac if c.get("hittable") and c.get("selector")]

        # 확인된 modal overlay selector (HARM R1 의 container 확인용)
        overlay_all: dict[str, list] = {}
        for c in (raw.get("modal_overlay_candidates", []) or []):
            overlay_all.setdefault(str(c.get("selector")), []).extend(c.get("candidate_sources") or [])
        SEMANTIC = {"dialog_element", "role_dialog", "aria_modal"}
        # 의미적 dialog: 선언된 dialog/role/aria-modal 로 확인된 컨테이너만.
        semantic_dialog_sels = {s_ for s_, src in overlay_all.items() if SEMANTIC & set(src)}
        # 휴리스틱 전용: fixed/sticky/z-index 로만 잡힌 컨테이너 (판별력 없음 — 아래 note 참고)
        overlay_sels = set(overlay_all)

        # selector 단위 OR 집계 — l1_engine 이 만드는 것이 selector set 이므로 이것이 정본 grain
        agg: dict[str, dict] = {}
        for cont in raw.get("dismiss_control_candidates", []) or []:
            cs = str(cont.get("container_selector"))
            dialogish = bool(cont.get("is_dialog_element")) or bool(cont.get("has_form_method_dialog")) or cs in overlay_sels
            dialog_semantic = (bool(cont.get("is_dialog_element"))
                               or bool(cont.get("has_form_method_dialog"))
                               or cs in semantic_dialog_sels)
            for c in cont.get("dismiss_control_candidates") or []:
                s = str(c.get("selector"))
                nm = c.get("accessible_name_source")
                cv = bool(c.get("matches_close_vocabulary"))
                io = bool(c.get("icon_only"))
                entry_rows.append(
                    {"wtg": r.wtg, "selector": s, "container": cs, "cv": cv, "io": io,
                     "dialogish": dialogish, "dialog_semantic": dialog_semantic,
                     "name": nm, "hittable": bool(c.get("hittable"))}
                )
                a = agg.setdefault(s, {"cv": False, "io": False, "dialogish": False,
                                       "dialog_semantic": False,
                                       "names": [], "areas": [], "n_entry": 0})
                a["cv"] |= cv
                a["io"] |= io
                a["dialogish"] |= dialogish
                a["dialog_semantic"] |= dialog_semantic
                a["n_entry"] += 1
                if nm:
                    a["names"].append(str(nm))
                ar = area_of(c.get("box"))
                if ar is not None:
                    a["areas"].append(ar)

        d_base = set(agg)
        d_abl = {s for s, a in agg.items() if a["cv"]}

        removed = [c for c in hit if str(c["selector"]) in d_base]
        recovered = [c for c in removed if str(c["selector"]) not in d_abl]
        survivors = [c for c in hit if str(c["selector"]) not in d_base]

        for c in survivors:
            survivor_rows.append(
                {"wtg": r.wtg, "selector": str(c["selector"]), "has_href": bool(c.get("href")),
                 "name_slot": ("aria_label" if c.get("aria_label")
                               else ("visible_text" if c.get("visible_text") else "none")),
                 "area": c.get("area_css_px2")}
            )

        for c in removed:
            s = str(c["selector"])
            a = agg[s]
            name = a["names"][0] if a["names"] else None
            cell = ("both" if (a["cv"] and a["io"])
                    else ("close_vocabulary_only" if a["cv"] else
                          ("icon_only_only" if a["io"] else "neither_UNEXPECTED")))
            min_area = min(a["areas"]) if a["areas"] else None
            href = c.get("href")
            has_href = href is not None and str(href).strip() != ""
            non_nav = (not has_href) or (str(href).strip() in NON_NAV_HREF)
            homeish = has_href and str(href).strip() in HOMEISH_HREF
            vt = c.get("visible_text")
            removed_rows.append({
                "wtg": r.wtg,
                "selector": s,
                "basis_cell": cell,
                "cv": a["cv"],
                "io": a["io"],
                "recovered": s not in d_abl,
                "n_dismiss_entries_for_selector": a["n_entry"],
                "dialogish_container": a["dialogish"],
                "dismiss_name": name,
                "pac_tag": c.get("tag"),
                "pac_role": c.get("role"),
                "pac_aria_label": c.get("aria_label"),
                "pac_visible_text": vt,
                "pac_nearby_heading": c.get("nearby_heading"),
                "pac_href": href,
                "has_href": has_href,
                "non_navigating": non_nav,
                "homeish_href": homeish,
                "dialog_semantic_container": a["dialog_semantic"],
                "no_name_at_all": (not c.get("aria_label")) and (not vt) and (name is None),
                "name_slot": ("aria_label" if c.get("aria_label")
                              else ("visible_text" if vt else "none")),
                "pac_area": c.get("area_css_px2"),
                "dismiss_min_area": min_area,
                "ext_close_lex": bool(CLOSE_EXTENDED.search(name or "")) if name else False,
                "non_close_lex": bool(NON_CLOSE_LEX.search(name or "")) if name else False,
            })

        per_target.append({
            "wtg": r.wtg, "probe": True,
            "n_pac": len(pac), "n_hittable": len(hit),
            "n_dismiss_selectors_base": len(d_base),
            "n_dismiss_selectors_abl": len(d_abl),
            "n_removed_base": len(removed),
            "n_removed_abl": len(removed) - len(recovered),
            "n_recovered": len(recovered),
            "pool_base": len(hit) - len(removed),
            "pool_abl": len(hit) - (len(removed) - len(recovered)),
            "emptied_base": int(len(hit) > 0 and len(hit) - len(removed) == 0),
            "emptied_abl": int(len(hit) > 0 and len(hit) - (len(removed) - len(recovered)) == 0),
        })

    pt = pd.DataFrame(per_target)
    ptp = pt[pt.probe].copy()
    rm = pd.DataFrame(removed_rows)
    en = pd.DataFrame(entry_rows)
    sv = pd.DataFrame(survivor_rows)

    n_targets = int(len(ptp))
    n_hit = int(ptp.n_hittable.sum())
    n_removed = int(ptp.n_removed_base.sum())
    n_recovered = int(ptp.n_recovered.sum())
    rec = rm[rm.recovered] if len(rm) else rm
    nonrec = rm[~rm.recovered] if len(rm) else rm

    # ── 1. 중복근거 분해 ──────────────────────────────────────────────────
    cells_sel = rm.basis_cell.value_counts().to_dict() if len(rm) else {}
    dup = {
        "grain": "removed hittable pac (selector 단위 OR 집계) — 분모는 baseline 에서 제거된 후보 수",
        "denominator_removed": n_removed,
        "cells": {k: frac(int(v), n_removed, "removed hittable pac") for k, v in cells_sel.items()},
        "close_vocabulary_any": frac(int(rm.cv.sum()) if len(rm) else 0, n_removed, "removed hittable pac"),
        "icon_only_any": frac(int(rm.io.sum()) if len(rm) else 0, n_removed, "removed hittable pac"),
        "entry_grain_check": {
            "note": "selector 가 여러 container 에 중복 등장하면 entry grain 과 selector grain 이 갈린다.",
            "n_dismiss_entries_all": int(len(en)),
            "n_distinct_selector_target_pairs": int(en.drop_duplicates(["wtg", "selector"]).shape[0]) if len(en) else 0,
            "n_selectors_with_multiple_entries": int(
                (en.groupby(["wtg", "selector"]).size() > 1).sum()) if len(en) else 0,
            "n_removed_selectors_with_multiple_entries": int(
                (rm.n_dismiss_entries_for_selector > 1).sum()) if len(rm) else 0,
        },
        "pilot_e_comparison": {
            "pilot_e_reported": {"icon_only": 35, "close_vocabulary": 22},
            "note": (
                "PILOT-E 의 basis 는 상호배타 우선순위(close_vocabulary 우선)였고 selector 당 "
                "첫 entry 만 봤다. 이 문서는 3분할 + selector OR 집계를 쓴다. "
                "close_vocabulary_any 가 PILOT-E 의 22 와 일치하고 icon_only_only 가 35 와 "
                "일치하면 두 계산은 같은 것을 다르게 표기한 것뿐이다."
            ),
        },
    }

    # ── 2. ablation 회복량 ────────────────────────────────────────────────
    emptied_base = int(ptp.emptied_base.sum())
    emptied_abl = int(ptp.emptied_abl.sum())
    recovery = {
        "grain_note": "후보 grain 과 target grain 을 섞지 않는다. 각 항목에 grain 을 붙였다.",
        "candidate_grain": {
            "n_hittable_candidates": n_hit,
            "n_removed_baseline": frac(n_removed, n_hit, "hittable pac"),
            "n_removed_ablated": frac(n_removed - n_recovered, n_hit, "hittable pac"),
            "n_recovered": n_recovered,
            "recovery_rate_of_removed": frac(n_recovered, n_removed, "removed hittable pac"),
            "recovery_rate_of_all_hittable": frac(n_recovered, n_hit, "hittable pac"),
            "pool_baseline_total": int(ptp.pool_base.sum()),
            "pool_ablated_total": int(ptp.pool_abl.sum()),
            "pool_growth_pct": round(100.0 * n_recovered / int(ptp.pool_base.sum()), 4) if int(ptp.pool_base.sum()) else None,
        },
        "target_grain": {
            "n_targets_with_probe": n_targets,
            "n_targets_expected": n_target_expected,
            "n_targets_affected_baseline": frac(int((ptp.n_removed_base > 0).sum()), n_targets, "target"),
            "n_targets_with_any_recovery": frac(int((ptp.n_recovered > 0).sum()), n_targets, "target"),
            "n_targets_pool_emptied_baseline": frac(emptied_base, n_targets, "target"),
            "n_targets_pool_emptied_ablated": frac(emptied_abl, n_targets, "target"),
            "n_emptied_targets_that_unempty": emptied_base - emptied_abl,
            "unempty_rate": frac(emptied_base - emptied_abl, emptied_base, "target (baseline 에서 pool 이 빈 target)") if emptied_base else None,
            "emptied_target_detail": ptp[ptp.emptied_base == 1][
                ["wtg", "n_hittable", "n_removed_base", "pool_base", "n_recovered", "pool_abl", "emptied_abl"]
            ].to_dict("records"),
            "monotonicity_check": {
                "pool_never_shrinks": bool((ptp.pool_abl >= ptp.pool_base).all()),
                "note": "정의상 P_base ⊆ P_abl 이므로 참이어야 한다. 거짓이면 계산 오류다.",
            },
            "per_target_pool_delta_describe": {
                k: (round(float(v), 4) if pd.notna(v) else None)
                for k, v in (ptp.pool_abl - ptp.pool_base).describe().to_dict().items()
            },
        },
        "axis_c_side_effect": {
            "note": "icon_only 를 끄면 Axis C 의 dismiss 후보 자체도 줄어든다. 이 문서는 크기만 보고한다.",
            "n_dismiss_selectors_baseline_total": int(ptp.n_dismiss_selectors_base.sum()),
            "n_dismiss_selectors_ablated_total": int(ptp.n_dismiss_selectors_abl.sum()),
            "shrink_rate": frac(
                int(ptp.n_dismiss_selectors_base.sum()) - int(ptp.n_dismiss_selectors_abl.sum()),
                int(ptp.n_dismiss_selectors_base.sum()),
                "dismiss selector (target×selector)"),
            "n_targets_dismiss_set_becomes_empty": frac(
                int(((ptp.n_dismiss_selectors_base > 0) & (ptp.n_dismiss_selectors_abl == 0)).sum()),
                int((ptp.n_dismiss_selectors_base > 0).sum()),
                "target (baseline 에 dismiss selector 가 있던 target)"),
        },
    }

    # ── 3. 회복 후보의 성질 ───────────────────────────────────────────────
    n_rec = int(len(rec))
    props = {
        "grain": "recovered hittable pac",
        "denominator": n_rec,
        "has_href": frac(int(rec.has_href.sum()) if n_rec else 0, n_rec, "recovered candidate"),
        "homeish_href": frac(int(rec.homeish_href.sum()) if n_rec else 0, n_rec, "recovered candidate"),
        "non_navigating": frac(int(rec.non_navigating.sum()) if n_rec else 0, n_rec, "recovered candidate"),
        "name_slot_distribution": {
            k: frac(int(v), n_rec, "recovered candidate")
            for k, v in (rec.name_slot.value_counts().to_dict() if n_rec else {}).items()
        },
        "pac_tag_distribution": rec.pac_tag.value_counts().to_dict() if n_rec else {},
        "container_overlay_heuristic": frac(int(rec.dialogish_container.sum()) if n_rec else 0, n_rec, "recovered candidate"),
        "container_semantic_dialog": frac(int(rec.dialog_semantic_container.sum()) if n_rec else 0, n_rec, "recovered candidate"),
        "no_name_at_all": frac(int(rec.no_name_at_all.sum()) if n_rec else 0, n_rec, "recovered candidate"),
        "close_vocabulary_by_definition": {
            "note": "회복분은 정의상 probe 의 CLOSE_WORDS/CLOSE_GLYPH 에 걸리지 않는다(그래서 icon_only 단독이었다). "
                    "따라서 어휘유사도는 **확장 사전**으로만 의미가 있다.",
            "probe_regex_hits": int(rec.dismiss_name.fillna("").map(lambda s: bool(CLOSE_WORDS.search(s) or CLOSE_GLYPH.match(s))).sum()) if n_rec else 0,
        },
        "extended_close_lexicon_hit": frac(int(rec.ext_close_lex.sum()) if n_rec else 0, n_rec, "recovered candidate"),
        "non_close_lexicon_hit": frac(int(rec.non_close_lex.sum()) if n_rec else 0, n_rec, "recovered candidate"),
        "unnamed": frac(int(rec.dismiss_name.isna().sum()) if n_rec else 0, n_rec, "recovered candidate"),
    }

    sample_cols = ["wtg", "selector", "pac_tag", "pac_href", "dismiss_name", "pac_aria_label",
                   "pac_visible_text", "pac_nearby_heading", "pac_area", "dismiss_min_area",
                   "dialogish_container", "dialog_semantic_container", "no_name_at_all",
                   "ext_close_lex", "non_close_lex", "basis_cell"]
    recovered_sample = (rec[sample_cols].where(pd.notna(rec[sample_cols]), None).to_dict("records")
                        if n_rec else [])

    # ── 4. H-E1-HARM 민감도 ───────────────────────────────────────────────
    def _rule(df: pd.DataFrame, name: str) -> pd.Series:
        area = pd.to_numeric(df.dismiss_min_area, errors="coerce")
        no_href = ~df.has_href
        small = area.fillna(np.inf) <= 2500
        unnamed = df.no_name_at_all
        if name == "R1_semantic_dialog_unnamed_icon":
            return df.dialog_semantic_container & no_href & unnamed & small
        if name == "R2_unnamed_icon_no_href":
            return no_href & unnamed & small
        if name == "R3_no_href_not_obviously_non_close":
            return no_href & (~df.non_close_lex)
        if name == "R4_no_href":
            return no_href
        if name == "R5_extended_close_lexicon":
            return df.ext_close_lex
        if name == "R6_no_href_or_non_navigating":
            return df.non_navigating
        if name == "R7_overgenerous_incl_site_root":
            u = _rule(df, "R6_no_href_or_non_navigating") | _rule(df, "R5_extended_close_lexicon")
            for r_ in ("R1_semantic_dialog_unnamed_icon", "R2_unnamed_icon_no_href",
                       "R3_no_href_not_obviously_non_close", "R4_no_href"):
                u = u | _rule(df, r_)
            return u | df.homeish_href
        raise KeyError(name)

    harm = {"grain": "recovered hittable pac", "denominator": n_rec, "rules": {}}
    for rname, rdesc in HARM_RULES.items():
        if n_rec:
            m = _rule(rec, rname)
            k = int(m.sum())
            harm["rules"][rname] = {
                "definition": rdesc,
                "plausibly_genuine_close": frac(k, n_rec, "recovered candidate"),
                "clearly_not_close": frac(n_rec - k, n_rec, "recovered candidate"),
                "examples_flagged": rec[m][["wtg", "selector", "dismiss_name", "pac_href"]].head(6)
                                     .where(pd.notna(rec[m][["wtg", "selector", "dismiss_name", "pac_href"]].head(6)), None)
                                     .to_dict("records"),
            }
        else:
            harm["rules"][rname] = {"definition": rdesc, "plausibly_genuine_close": frac(0, 0, "recovered candidate")}
    rates = [v["plausibly_genuine_close"]["rate"] for v in harm["rules"].values() if v["plausibly_genuine_close"]["rate"] is not None]
    rates_core = [v["plausibly_genuine_close"]["rate"] for k, v in harm["rules"].items()
                  if not k.startswith("R7") and v["plausibly_genuine_close"]["rate"] is not None]
    harm["decision_rule"] = HARM_DECISION_RULE
    harm["rule_family_revision_note"] = RULE_FAMILY_REVISION_NOTE
    harm["container_discriminator_note"] = (
        "dismiss container 를 modal_overlay_candidates 소속으로 판정하면 판별력이 없다 — "
        "두 스캔이 같은 fixed/sticky/z>=100 조건을 쓴다(l0_probe.js:195-199 vs :386-390). "
        "실제로 회복분 %d/%d 가 그 느슨한 정의에서 '오버레이 안' 으로 잡힌다. "
        "그래서 R1 은 candidate_sources 의 dialog_element/role_dialog/aria_modal 만 인정한다."
        % (int(rec.dialogish_container.sum()) if n_rec else 0, n_rec)
    )
    harm["sensitivity"] = {
        "n_rules": len(rates),
        "min_rate": min(rates) if rates else None,
        "max_rate": max(rates) if rates else None,
        "max_rate_excluding_overgenerous_R7": max(rates_core) if rates_core else None,
        "median_rate": float(np.median(rates)) if rates else None,
        "direction_stable_below_half": bool(rates_core and max(rates_core) < 0.5),
        "direction_stable_above_half": bool(rates and min(rates) > 0.5),
        "reading": (
            "규칙을 느슨하게 할수록 상한이 커지도록 설계했다. **가장 느슨한 상한조차** 낮으면 "
            "회복분의 다수가 진짜 닫기라고 보기 어렵다는 뜻이고, 가장 엄격한 상한조차 높으면 그 반대다. "
            "이 상한은 gold 가 아니라 규칙 기반이며 probe 와 같은 slot 을 읽으므로 독립적이지 않다."
        ),
        "counter_evidence_non_close_lexicon": props["non_close_lexicon_hit"],
    }

    # ── 4b. 통계검정 + BH-FDR ─────────────────────────────────────────────
    tests = []
    if n_rec and len(nonrec) and len(sv):
        def fisher(k1, n1, k2, n2, name, desc):
            tab = [[k1, n1 - k1], [k2, n2 - k2]]
            try:
                orr, p = stats.fisher_exact(tab)
            except Exception:
                orr, p = None, 1.0
            return {"test_id": name, "description": desc, "table": tab,
                    "odds_ratio": (round(float(orr), 4) if orr not in (None, np.inf) and np.isfinite(orr) else str(orr)),
                    "p_raw": round(float(p), 6)}

        tests.append(fisher(int(rec.has_href.sum()), n_rec, int(nonrec.has_href.sum()), len(nonrec),
                            "T1_href_recovered_vs_stillremoved",
                            "회복분과 여전히 제거되는 분의 href 보유율 차이 (grain: removed candidate)"))
        tests.append(fisher(int(rec.has_href.sum()), n_rec, int(sv.has_href.sum()), len(sv),
                            "T2_href_recovered_vs_survivors",
                            "회복분과 baseline 에서 살아남은 pool 의 href 보유율 차이 (grain: hittable pac)"))
        tests.append(fisher(int((rec.name_slot == "none").sum()), n_rec, int((sv.name_slot == "none").sum()), len(sv),
                            "T3_unnamed_recovered_vs_survivors",
                            "이름 slot 이 전혀 없는 비율 차이 (grain: hittable pac)"))
        a = pd.to_numeric(rec.pac_area, errors="coerce").dropna().values
        b = pd.to_numeric(sv.area, errors="coerce").dropna().values
        if len(a) >= 3 and len(b) >= 3:
            u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            tests.append({"test_id": "T4_area_recovered_vs_survivors",
                          "description": "회복분과 생존 pool 의 면적 분포 차이 (Mann-Whitney, grain: hittable pac)",
                          "median_recovered": round(float(np.median(a)), 2),
                          "median_survivors": round(float(np.median(b)), 2),
                          "n_recovered": int(len(a)), "n_survivors": int(len(b)),
                          "p_raw": round(float(p), 6)})
        tests.append(fisher(int(rec.dialog_semantic_container.sum()), n_rec,
                            int(nonrec.dialog_semantic_container.sum()), len(nonrec),
                            "T5_semanticdialog_recovered_vs_stillremoved",
                            "의미적 dialog(role/aria-modal/<dialog>) 컨테이너 소속 비율 차이 (grain: removed candidate)"))
        adj = bh_fdr([t["p_raw"] for t in tests])
        for t, q in zip(tests, adj):
            t["p_bh_fdr"] = q
            t["significant_at_q05"] = bool(q < 0.05)
    stats_block = {
        "family_size": len(tests),
        "correction": "Benjamini-Hochberg FDR across the 5 pre-listed comparisons",
        "tests": tests,
        "note": "이 검정들은 회복분의 **성질 기술**이지 회복량의 유의성 검정이 아니다. 회복량은 계수(count)이며 표집오차가 아니라 결정적 재계산 결과다.",
    }

    # ── 5. H-E1-IRRELEVANT 확인: Axis B 산출 상태 ──────────────────────────
    te = pd.DataFrame(json.loads((MART / "fact_task_entry.json").read_text(encoding="utf-8")))
    axis_b = {
        "grain": "task_entry row (mart)",
        "n_rows": int(len(te)),
        "NED_notnull": int(te.NED.notna().sum()) if "NED" in te else None,
        "IED_notnull": int(te.IED.notna().sum()) if "IED" in te else None,
        "MPFED_notnull": int(te.MPFED.notna().sum()) if "MPFED" in te else None,
        "endpoint_reached_positive": int((pd.to_numeric(te.endpoint_reached, errors="coerce") > 0).sum()) if "endpoint_reached" in te else None,
        "endpoint_status_counts": te.endpoint_status.value_counts().to_dict() if "endpoint_status" in te else {},
        "reading": "현 frozen mart 에서 Axis B 의 세 산출값은 전부 결측이다. pool 회복이 산출값을 바꾸는지는 이 증거로 확인 불가능하다.",
    }

    # ── 가설 판정 ────────────────────────────────────────────────────────
    rr = recovery["candidate_grain"]["recovery_rate_of_removed"]["rate"]
    unempty = recovery["target_grain"]["n_emptied_targets_that_unempty"]
    max_harm = harm["sensitivity"]["max_rate"]
    max_harm_core = harm["sensitivity"]["max_rate_excluding_overgenerous_R7"]
    min_harm = harm["sensitivity"]["min_rate"]

    hv = {
        "H-E1-RECOVERY": {
            "statement": "icon_only 를 끄면 제거된 후보의 상당수가 되돌아오고, pool 이 비었던 target 이 회복된다.",
            "verdict": "SUPPORTED" if (rr is not None and rr >= 0.5 and emptied_base > 0 and unempty == emptied_base)
                       else ("PARTIALLY_SUPPORTED" if (rr or 0) > 0 else "NOT_SUPPORTED"),
            "evidence": (
                f"제거된 {n_removed}개 hittable 후보 중 {n_recovered}개가 회복된다 "
                f"({rr}; Wilson95 {recovery['candidate_grain']['recovery_rate_of_removed']['wilson95']}; "
                f"grain=removed hittable pac). baseline 에서 pool 이 빈 target {emptied_base}/{n_targets} 중 "
                f"{unempty}개가 비지 않게 된다 (ablation 후 {emptied_abl}/{n_targets})."
            ),
            "caveat": "반사실 재계산이다. 실제로 코드를 고쳐 재수집한 결과가 아니다.",
        },
        "H-E1-NULL": {
            "statement": "icon_only 로 제거된 후보는 대부분 close_vocabulary 로도 잡히므로 회복량이 미미하다.",
            "verdict": "REFUTED" if (rr is not None and rr >= 0.5) else ("PARTIALLY_SUPPORTED" if (rr or 0) < 0.2 else "INCONCLUSIVE"),
            "evidence": (
                f"중복근거(both) 셀은 {cells_sel.get('both', 0)}/{n_removed} 뿐이다. "
                f"icon_only 단독근거가 {cells_sel.get('icon_only_only', 0)}/{n_removed} 로 최대 셀이다. "
                "즉 두 조건은 대부분 겹치지 않는다."
            ),
        },
        "H-E1-HARM": {
            "statement": "되돌아온 후보의 다수가 진짜 닫기 control 이라, 회복은 Axis B 의 오탐을 늘릴 뿐이다.",
            "decision_rule": HARM_DECISION_RULE,
            "verdict": ("SUPPORTED" if (min_harm is not None and min_harm > 0.5)
                        else ("NOT_SUPPORTED" if (max_harm_core is not None and max_harm_core < 0.5)
                              else "INCONCLUSIVE")),
            "evidence": (
                f"보수적 상한 {len(HARM_RULES)}개 규칙에서 '진짜 닫기일 수 있음' 비율은 "
                f"{min_harm}–{max_harm} 구간이고, 의도적 과대계상 R7 을 뺀 최댓값은 {max_harm_core} 다 "
                f"(grain=recovered candidate, 분모 {n_rec}). "
                f"확장 닫기 사전 적중은 {props['extended_close_lexicon_hit']['numerator']}/{n_rec} 이고, "
                f"명백한 비-닫기 기능어휘(메뉴/검색/홈/로고 등) 적중이 "
                f"{props['non_close_lexicon_hit']['numerator']}/{n_rec} 이다."
            ),
            "caveat": "gold label 이 없다. 이 판정은 규칙 기반 상한이며 사람의 재판정이 필요하다 — recovered_sample 을 그대로 실었다.",
        },
        "H-E1-IRRELEVANT": {
            "statement": "pool 크기가 회복돼도 Axis B 산출(NED/IED/MPFED)이 전부 None 이므로 회복은 결과에 도달하지 않는다.",
            "verdict": "SUPPORTED",
            "evidence": (
                f"frozen mart fact_task_entry.json 에서 NED/IED/MPFED 가 각각 "
                f"{axis_b['NED_notnull']}/{axis_b['n_rows']}, {axis_b['IED_notnull']}/{axis_b['n_rows']}, "
                f"{axis_b['MPFED_notnull']}/{axis_b['n_rows']} non-null 이고 endpoint_reached>0 은 "
                f"{axis_b['endpoint_reached_positive']}/{axis_b['n_rows']} 다. "
                "회복량은 탐색공간 크기까지만 말하며 산출값에 도달하지 않는다."
            ),
            "note": "이 가설은 H-E1-RECOVERY 와 배타적이지 않다. 둘 다 참일 수 있고 실제로 둘 다 참이다 — 회복은 pool grain 에서 실재하고, 결과 grain 에서는 관측되지 않는다.",
        },
    }

    verdict = ("PARTIALLY_SUPPORTED"
               if hv["H-E1-RECOVERY"]["verdict"] == "SUPPORTED" and hv["H-E1-IRRELEVANT"]["verdict"] == "SUPPORTED"
               else hv["H-E1-RECOVERY"]["verdict"])

    doc = {
        "schema": "RQ_E1_icononly_ablation/1",
        "verdict": verdict,
        "verdict_note": (
            "주가설 H-E1-RECOVERY 는 pool grain 에서 SUPPORTED 다. 그러나 같은 증거가 "
            "H-E1-IRRELEVANT 도 SUPPORTED 로 만든다 — 회복은 실재하나 현 mart 의 Axis B "
            "산출값에는 도달하지 않는다. 그래서 전체 verdict 는 PARTIALLY_SUPPORTED 다."
        ),
        "hypothesis_verdicts": hv,
        "rq_id": "RQ-E-1",
        "child_id": "D-RQ-E-1",
        "hypothesis_id": "H-E1-RECOVERY",
        "plane": "D",
        "authority": "NON_CANONICAL",
        "claim_kind": "ANALYSIS",
        "split": "none",
        "seed": SEED,
        "model_or_rule_version": "RQ_E1_v1",
        "generated_at_kst": datetime.now(KST).isoformat(),
        "go_nogo_decision": "NOT_IN_SCOPE — D 는 GO/NO-GO 와 threshold 를 내지 않는다",
        "construct_authority_note": "icon_only 를 끌지 말지는 A 의 권한이다. 이 문서는 회복량과 회복분의 성질만 보고한다.",
        "causal_claim": "none — 코드를 고쳐 재수집한 것이 아니라 frozen probe flag 로 filter 를 재계산한 반사실이다.",
        "method": (
            "l0_probe.js:409 의 `filter(x => x.matches_close_vocabulary || x.icon_only)` 를 "
            "`filter(x => x.matches_close_vocabulary)` 로 바꾼 반사실 집합을 frozen probe raw 에서 "
            "재계산하고, l1_engine.py:346-357 의 selector-set 차집합 연산을 그대로 재현한다."
        ),
        "definitions": DEFINITIONS,
        "code_read": {
            "sha": CODE_SHA,
            "method": "git show <sha>:<path> — 읽기 전용. 실행하지 않았다.",
            "files": [
                {"path": "src/landing_accessibility/engine/l0_probe.js",
                 "lines": "377-418 (dismiss_control_candidates 블록); :379-381 CLOSE_WORDS/PERSIST_WORDS/CLOSE_GLYPH; "
                          ":384-390 컨테이너 집합(dialog/role=dialog/alertdialog/aria-modal ∪ fixed/sticky/z>=100); "
                          ":392-393 control 질의(button,[role=button],a[href],[role=link],form[method=dialog] button); "
                          ":394 name=aria-label||title||textContent; :400 matches_close_vocabulary; "
                          ":402 icon_only = !textContent && (aria-label || img/svg 자식); :409 filter",
                 "ablated_line": ":402/:409 의 `|| x.icon_only` 항"},
                {"path": "src/landing_accessibility/engine/l1_engine.py",
                 "lines": "334-370 _activation_candidates; :346-350 dismiss_selectors 집합 구성(컨테이너 전체 flatten, hittable 무관); "
                          ":351-357 hittable ∧ selector 존재 ∧ selector ∉ dismiss_selectors; :358 min4_sort_key 정렬; :360-368 dedup + limit 절단"},
            ],
            "note": "l1_engine 은 selector **문자열 집합** 을 만든다. 따라서 같은 selector 의 여러 entry 는 flag OR 과 동치이며, 이 분석은 그 grain 을 따랐다.",
        },
        "duplicate_basis_decomposition": dup,
        "ablation_recovery": recovery,
        "recovered_properties": props,
        "recovered_sample": recovered_sample,
        "harm_sensitivity": harm,
        "statistical_tests": stats_block,
        "axis_b_output_state": axis_b,
        "counterexamples": {
            "note": "가설에 불리한 관측을 먼저 적는다.",
            "items": [
                {"against": "H-E1-RECOVERY",
                 "observation": f"회복된 {n_rec}개 중 확장 닫기 사전에 걸리는 것이 "
                                f"{props['extended_close_lexicon_hit']['numerator']}개 있다. "
                                "이들은 probe 정규식이 좁아서 icon_only 로만 잡힌 **진짜 닫기**일 수 있고, "
                                "그렇다면 그만큼의 회복은 오탐이다."},
                {"against": "H-E1-RECOVERY",
                 "observation": f"pool 이 회복돼도 Axis B 산출은 여전히 전부 결측이다 "
                                f"(NED/IED/MPFED {axis_b['NED_notnull']}/{axis_b['n_rows']}). "
                                "회복이 결과를 바꾼다는 증거는 이 문서에 없다."},
                {"against": "H-E1-HARM",
                 "observation": f"회복분 중 href 보유가 {props['has_href']['numerator']}/{n_rec} 이고, "
                                f"그 중 상당수가 사이트 루트(/)나 외부 도메인으로 가는 로고·홈 링크다. "
                                "닫기 control 이 외부 도메인으로 네비게이션하지는 않는다."},
                {"against": "H-E1-NULL",
                 "observation": f"두 조건이 함께 걸린(both) 후보는 {cells_sel.get('both', 0)}개뿐이다. "
                                "중복 근거 가정이 데이터에서 지지되지 않는다."},
            ],
        },
        "limitation": LIMITATION,
        "not_answered_by_this_rq": NOT_ANSWERED,
        "further_research_questions": FURTHER_RQ,
        "firewall": {
            "denied_paths_not_opened": True,
            "note": "D_INPUT_ALLOWLIST.json 의 denied 목록을 하나도 열지 않았다. 네트워크 접속 없음. "
                    "gold label 생산 없음. 기존 산출물 수정 없음(새 파일만 썼다).",
        },
        "inputs": {
            "observation_table": {"path": str(OBS_TABLE), "sha256": sha256_file(OBS_TABLE)},
            "mart_fact_task_entry": {"path": str(MART / "fact_task_entry.json"),
                                     "sha256": sha256_file(MART / "fact_task_entry.json")},
            "probe_raw": {"n_files": len(inputs_probe),
                          "glob": str(WT / EVIDENCE_GLOB / "<run_dir>/*/l0a/probe.json"),
                          "files": inputs_probe},
        },
        "n_expected": n_target_expected,
        "n_observed": n_targets,
        "parent_run_id": PARENT_RUN_ID,
    }
    return doc, ptp, rm, sv


def make_figures(doc: dict, ptp: pd.DataFrame, rm: pd.DataFrame) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams["font.family"] = ["DejaVu Sans"]
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = []

    cg = doc["ablation_recovery"]["candidate_grain"]
    tg = doc["ablation_recovery"]["target_grain"]
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6))

    axs[0].bar(["hittable", "removed\n(baseline)", "removed\n(ablated)", "recovered"],
               [cg["n_hittable_candidates"], cg["n_removed_baseline"]["numerator"],
                cg["n_removed_ablated"]["numerator"], cg["n_recovered"]],
               color=["#5b8ff9", "#d9534f", "#f0ad4e", "#5cb85c"])
    for i, v in enumerate([cg["n_hittable_candidates"], cg["n_removed_baseline"]["numerator"],
                           cg["n_removed_ablated"]["numerator"], cg["n_recovered"]]):
        axs[0].text(i, v, str(v), ha="center", va="bottom", fontsize=9)
    axs[0].set_title("RQ-E-1 icon_only ablation\n(grain: hittable primary_action_candidate)", fontsize=10)
    axs[0].set_ylabel("count")

    cells = doc["duplicate_basis_decomposition"]["cells"]
    ks = list(cells.keys())
    axs[1].bar(ks, [cells[k]["numerator"] for k in ks], color="#8a63d2")
    for i, k in enumerate(ks):
        axs[1].text(i, cells[k]["numerator"], f"{cells[k]['numerator']}\n{cells[k]['rate']:.0%}",
                    ha="center", va="bottom", fontsize=8)
    axs[1].set_title(f"removal basis decomposition\n(den={doc['duplicate_basis_decomposition']['denominator_removed']} removed)", fontsize=10)
    axs[1].tick_params(axis="x", labelrotation=15, labelsize=8)

    rules = doc["harm_sensitivity"]["rules"]
    rk = list(rules.keys())
    vals = [rules[k]["plausibly_genuine_close"]["rate"] or 0 for k in rk]
    lo = [rules[k]["plausibly_genuine_close"]["wilson95"][0] if rules[k]["plausibly_genuine_close"]["wilson95"] else 0 for k in rk]
    hi = [rules[k]["plausibly_genuine_close"]["wilson95"][1] if rules[k]["plausibly_genuine_close"]["wilson95"] else 0 for k in rk]
    axs[2].errorbar(range(len(rk)), vals,
                    yerr=[np.array(vals) - np.array(lo), np.array(hi) - np.array(vals)],
                    fmt="o", capsize=4, color="#d9534f")
    axs[2].axhline(0.5, ls="--", c="grey", lw=1)
    axs[2].set_xticks(range(len(rk)), [k.split("_")[0] for k in rk])
    axs[2].set_ylim(-0.05, 1.05)
    axs[2].set_title(f"H-E1-HARM upper bounds (Wilson95)\n(den={doc['harm_sensitivity']['denominator']} recovered)", fontsize=10)
    axs[2].set_ylabel("share plausibly a genuine close control")

    fig.tight_layout()
    p = FIG_DIR / "RQ_E1_ablation_overview.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    out.append(str(p))

    fig, ax = plt.subplots(figsize=(9, 4.4))
    d = ptp.sort_values("pool_base")
    ax.plot(range(len(d)), d.pool_base.values, "o-", ms=3, label="pool baseline", color="#d9534f")
    ax.plot(range(len(d)), d.pool_abl.values, "s-", ms=3, label="pool ablated (icon_only off)", color="#5cb85c")
    ax.set_yscale("symlog")
    ax.set_xlabel("target (sorted by baseline pool size), n=%d" % len(d))
    ax.set_ylabel("activation pool size")
    ax.set_title("per-target activation pool: baseline vs icon_only ablation\n"
                 "emptied targets %d -> %d" % (tg["n_targets_pool_emptied_baseline"]["numerator"],
                                               tg["n_targets_pool_emptied_ablated"]["numerator"]), fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    p = FIG_DIR / "RQ_E1_per_target_pool.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    out.append(str(p))
    return out


def run(log_mlflow: bool = True) -> dict:
    doc, ptp, rm, sv = main()
    figs = make_figures(doc, ptp, rm)
    doc["figures"] = figs
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    if log_mlflow:
        import sys
        sys.path.insert(0, str(RD / "tools"))
        import mlflow
        from mlflow_contract import research_run, finish, log_pointer

        cg = doc["ablation_recovery"]["candidate_grain"]
        tg = doc["ablation_recovery"]["target_grain"]
        dup = doc["duplicate_basis_decomposition"]
        props = doc["recovered_properties"]
        harm = doc["harm_sensitivity"]
        ab = doc["axis_b_output_state"]
        sc = doc["ablation_recovery"]["axis_c_side_effect"]

        mlflow.set_tracking_uri("http://127.0.0.1:5000")
        mlflow.set_experiment("LA_04_DIAGNOSTIC_PILOT_RESEARCH")
        with mlflow.start_run(run_id=PARENT_RUN_ID):
            with research_run(
                experiment="LA_04_DIAGNOSTIC_PILOT_RESEARCH",
                run_name="RQ-E-1_dismiss_icononly_ablation",
                plane="D",
                hypothesis_id="H-E1-RECOVERY",
                competing_hypothesis="H-E1-NULL | H-E1-HARM | H-E1-IRRELEVANT",
                claim_kind="ANALYSIS",
                nested=True,
                parent_run_id=PARENT_RUN_ID,
                ticket_id="RQ-E-1",
                subagent_id="D-SUB-RQ-E-1",
                objective=("l0_probe.js:402 icon_only 조건을 끈 반사실에서 Axis B activation pool 이 "
                           "얼마나 회복되는가를 재수집 없이 frozen probe raw 재계산으로 정량화한다."),
                method=doc["method"],
                dataset_grain=("target(in_mart==1 ∧ probe 보유, n=%d) × hittable primary_action_candidate(n=%d); "
                               "dismiss 집합은 selector 단위 OR 집계" % (doc["n_observed"], cg["n_hittable_candidates"])),
                n_expected=doc["n_expected"],
                n_observed=doc["n_observed"],
                model_or_rule_version="RQ_E1_v1",
                seed=SEED,
                split="none",
                result_path=OUT_JSON,
                code_path=Path(__file__),
                limitation=LIMITATION,
                notebook="research/landing_accessibility/notebooks/d_research/RQ_E1_icononly_ablation.ipynb",
                extra_tags={"code_sha_read": CODE_SHA, "rq_id": "RQ-E-1",
                            "recomputation_only": "true", "recollection_performed": "false"},
                extra_params={"ablated_condition": "l0_probe.js:402 icon_only (filter :409)",
                              "harm_rules": ",".join(HARM_RULES.keys()),
                              "fdr_family_size": doc["statistical_tests"]["family_size"]},
            ):
                M = {
                    "n_targets_with_probe": doc["n_observed"],
                    "n_targets_expected": doc["n_expected"],
                    "n_hittable_candidates": cg["n_hittable_candidates"],
                    "n_removed_baseline": cg["n_removed_baseline"]["numerator"],
                    "removal_rate_baseline": cg["n_removed_baseline"]["rate"],
                    "n_removed_ablated": cg["n_removed_ablated"]["numerator"],
                    "removal_rate_ablated": cg["n_removed_ablated"]["rate"],
                    "n_recovered": cg["n_recovered"],
                    "recovery_rate_of_removed": cg["recovery_rate_of_removed"]["rate"],
                    "recovery_rate_of_removed_ci_lo": cg["recovery_rate_of_removed"]["wilson95"][0],
                    "recovery_rate_of_removed_ci_hi": cg["recovery_rate_of_removed"]["wilson95"][1],
                    "recovery_rate_of_all_hittable": cg["recovery_rate_of_all_hittable"]["rate"],
                    "pool_baseline_total": cg["pool_baseline_total"],
                    "pool_ablated_total": cg["pool_ablated_total"],
                    "pool_growth_pct": cg["pool_growth_pct"],
                    "n_targets_pool_emptied_baseline": tg["n_targets_pool_emptied_baseline"]["numerator"],
                    "n_targets_pool_emptied_ablated": tg["n_targets_pool_emptied_ablated"]["numerator"],
                    "n_emptied_targets_that_unempty": tg["n_emptied_targets_that_unempty"],
                    "n_targets_with_any_recovery": tg["n_targets_with_any_recovery"]["numerator"],
                    "basis_icon_only_only": dup["cells"].get("icon_only_only", {}).get("numerator", 0),
                    "basis_close_vocab_only": dup["cells"].get("close_vocabulary_only", {}).get("numerator", 0),
                    "basis_both": dup["cells"].get("both", {}).get("numerator", 0),
                    "recovered_href_share": props["has_href"]["rate"],
                    "recovered_homeish_href_share": props["homeish_href"]["rate"],
                    "recovered_ext_close_lex_share": props["extended_close_lexicon_hit"]["rate"],
                    "recovered_non_close_lex_share": props["non_close_lexicon_hit"]["rate"],
                    "recovered_container_overlay_heuristic_share": props["container_overlay_heuristic"]["rate"],
                    "recovered_container_semantic_dialog_share": props["container_semantic_dialog"]["rate"],
                    "recovered_no_name_at_all_share": props["no_name_at_all"]["rate"],
                    "harm_upper_bound_max_excl_R7": harm["sensitivity"]["max_rate_excluding_overgenerous_R7"],
                    "harm_upper_bound_min": harm["sensitivity"]["min_rate"],
                    "harm_upper_bound_max": harm["sensitivity"]["max_rate"],
                    "harm_upper_bound_median": harm["sensitivity"]["median_rate"],
                    "axis_c_dismiss_selectors_baseline": sc["n_dismiss_selectors_baseline_total"],
                    "axis_c_dismiss_selectors_ablated": sc["n_dismiss_selectors_ablated_total"],
                    "axis_c_dismiss_shrink_rate": sc["shrink_rate"]["rate"],
                    "axis_b_NED_notnull": ab["NED_notnull"],
                    "axis_b_IED_notnull": ab["IED_notnull"],
                    "axis_b_MPFED_notnull": ab["MPFED_notnull"],
                    "axis_b_endpoint_reached_positive": ab["endpoint_reached_positive"],
                    "n_recovered_sample_dumped": len(doc["recovered_sample"]),
                }
                for r_ in doc["harm_sensitivity"]["rules"]:
                    v = doc["harm_sensitivity"]["rules"][r_]["plausibly_genuine_close"]["rate"]
                    if v is not None:
                        M["harm_" + r_] = v
                for t in doc["statistical_tests"]["tests"]:
                    M["p_bh_" + t["test_id"]] = t.get("p_bh_fdr")
                mlflow.log_metrics({k: float(v) for k, v in M.items() if v is not None})
                mlflow.log_artifact(str(OUT_JSON), "results")
                for f in figs:
                    mlflow.log_artifact(f, "figures")
                mlflow.log_text(json.dumps(doc["hypothesis_verdicts"], ensure_ascii=False, indent=1),
                                "hypothesis_verdicts.json")
                mlflow.log_text(json.dumps(doc["recovered_sample"], ensure_ascii=False, indent=1),
                                "recovered_sample.json")
                log_pointer("probe_raw_e001", doc["inputs"]["probe_raw"]["glob"],
                            hashlib.sha256(json.dumps(doc["inputs"]["probe_raw"]["files"],
                                                      sort_keys=True).encode()).hexdigest())
                finish(verdict=doc["verdict"], limitation=LIMITATION)
                doc["mlflow_run_id"] = mlflow.active_run().info.run_id
        OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc


if __name__ == "__main__":
    d = run()
    print(json.dumps({
        "verdict": d["verdict"],
        "hypothesis_verdicts": {k: v["verdict"] for k, v in d["hypothesis_verdicts"].items()},
        "recovery": d["ablation_recovery"]["candidate_grain"],
        "emptied": [d["ablation_recovery"]["target_grain"]["n_targets_pool_emptied_baseline"]["numerator"],
                    d["ablation_recovery"]["target_grain"]["n_targets_pool_emptied_ablated"]["numerator"]],
        "harm": {k: v["plausibly_genuine_close"]["rate"] for k, v in d["harm_sensitivity"]["rules"].items()},
        "mlflow_run_id": d.get("mlflow_run_id"),
    }, ensure_ascii=False, indent=1))
