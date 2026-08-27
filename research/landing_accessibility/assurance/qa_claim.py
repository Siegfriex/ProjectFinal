#!/usr/bin/env python3
"""CLAIM QA (Claude C) — CLAIM_GOVERNANCE.md §2 forbidden-phrase scan, §4 procedure, number cross-check vs C replay.

Usage: python qa_claim.py --claims FINAL_RESULTS_SUMMARY.md [CLAIM_REGISTRY.md LIMITATIONS.md ...] --replay out/QA_STAT_REPLAY.json --recon out/QA_MART_RECONCILIATION.json --out out/QA_CLAIM_LEDGER.md
Statuses per claim sentence: SUPPORTED / SUPPORTED_WITH_LIMITATION / EXPLORATORY_ONLY / UNSUPPORTED / MISMATCH. Final headline decision is A's.
"""
from __future__ import annotations
import argparse, json, pathlib, re, datetime
KST = datetime.timezone(datetime.timedelta(hours=9)); now = lambda: datetime.datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")

FORBIDDEN = [  # (pattern, rule, note)
    (r"고령자가?\s*대표기능에\s*도달할\s*수\s*없", "§2.1", "도구 한계→대상 성질"),
    (r"대표기능이\s*로그인\s*뒤에", "§2.1", "가드는 단어 존재만 탐지"),
    (r"진입\s*깊이가\s*(깊|얕)", "§2.1", "MPFED 미산출"),
    (r"서비스가\s*접근을\s*막", "§2.1", "수집기가 중단한 것"),
    (r"고령자가?\s*(포기|실패|길을\s*잃|사용할\s*수\s*없)", "§2.2", "실제 고령자 행동 미관측"),
    (r"고령자\s*사용성이\s*향상", "§2.2", "금지 표현"),
    (r"인증제도가\s*놓쳤", "§2.3", "variance 0"),
    (r"인증\s*(때문에|덕분에|효과)", "§2.3", "비교 불성립"),
    (r"(때문에|로 인해|초래|야기|원인|영향을\s*미친|효과가\s*있)", "§2.4", "인과표현 — 문맥 확인 필요"),
    (r"(종합\s*점수|composite\s*score|\bscore\b|점수)", "§2.4", "단일 종합점수/score 금지"),
    (r"(depth\s*(>=|≥)\s*3|3\s*이상이면)", "§2.4", "절대 cutoff 금지"),
    (r"측정기가?\s*(실패|작동하지\s*않|고장)", "§3", "원인 3종(가드 입도·archetype-endpoint 규칙·E-6b 구속) 분리 없이 뭉뚱그림 (A 14:31)"),
    (r"E-?6b[^.]{0,40}(8\s*건|8회)[^.]{0,40}(원인|때문)", "§3", "E-6b 발화 8 ≠ 구속 1 — 발화 횟수를 원인 계수로 쓰지 말 것"),
    (r"가드(만|를)\s*(고치|정밀화|완화)[^.]{0,30}(측정된다|산출된다|살아난다|해결)", "counterfactual", "반사실 과잉확정(긍정): 회복 상한 0~8, 무작위 배정 아님 (A 14:38)"),
    (r"가드(는|가)\s*(아무|전혀)?\s*(영향|관계)\s*(없|무관)", "counterfactual", "반사실 과잉확정(부정): 비무작위 배정 한계 문장 필요 (A 14:38)"),
    (r"(고령자가|사용자가)[^.]{0,20}(방해요소|팝업|모달|오버레이)[^.]{0,20}(닫지\s*못|닫을\s*수\s*없)", "axis-C", "자동화 dismissal 결과 ≠ 사용자 행동 (A 14:45)"),
    (r"닫을\s*수\s*없는\s*(방해요소|팝업|모달)[^.]{0,10}\d+\s*건", "axis-C", "'시각적 닫기 컨트롤 미탐지 상태에서 ESC/배경클릭으로 닫힘' 으로 서술"),
]
AXIS_C_CHECKS = [  # (trigger, required-companion, note)
    (r"(방해요소|interrupt|overlay)[^.]{0,30}(유형|분류|label)[^.]{0,30}(분포|비율)", r"UNKNOWN|미분류", "final_label 분포는 UNKNOWN(110/235, 47%) 병기 필수 (A 14:45)"),
    (r"(overlay\s*coverage|OverlayCoverage|오버레이\s*(면적|비율))[^.]{0,40}(median|중앙값)", r"q3|IQR|사분위|1\.0|전면", "median 단독 인용 금지 — q3=1.0, 22/56 전면 (A 14:45)"),
    (r"축\s*C[^.]{0,20}(측정됨|관측됨|측정되었)", r"미분류|UNKNOWN|47\s*%", "축 C = raw 실측 235 + 분류 47% 미분류 로 서술 (A 14:45)"),
    (r"(exists\s*=\s*0|닫기\s*컨트롤이?\s*없)[^.]{0,40}102", r"38|컨트롤이\s*있[^.]{0,10}실패", "102 만 강조 금지 — (exists=1, succeeded=0) 38 병기 (A 14:45)"),
]
_FORBIDDEN_TAIL = None
# CLAIM_GOVERNANCE rev 14:58: association NOT_COMPUTABLE, substitute_made=false → any association/GRADE B/C claim is out today
TODAY_RULES = [
    (r"(Spearman|ρ\s*=|rho\s*=|순위\s*상관|상관(계수|을|이)\s*보|Kruskal|association)", "rev14:58 §1", "오늘 association 없음 — GRADE B/C claim 존재 불가 (substitute_made=false)"),
    (r"GRADE\s*[BC]\b", "rev14:58 §1", "오늘 GRADE B/C 태그 자체가 무효 — A 또는 UNSUPPORTED 만"),
    (r"축\s*A[^.]{0,20}(관측됨|측정됨|산출)", "rev14:58 §0", "축 A = NOT_EVALUATED (판정기 부재) 로만 서술"),
    (r"(KWCAG|접근성\s*장벽)[^.]{0,30}(FAIL\s*비율|비율\s*분포|median)", "rev14:58 §0", "KWCAG 판정 미수행 — FailRate 서술 불가"),
]
HEDGE_N = r"(대부분|대다수|많은|거의\s*모든|majority|most)"
GRADE = r"\[(GRADE\s*[ABC]|UNSUPPORTED|EXPLORATORY)[^\]]*\]|GRADE\s*[ABC]\b|\bgrade\s*[ABC]\b"

def sentences(text):
    text = re.sub(r"`[^`]*`", " ", text)
    for para in text.split("\n"):
        p = para.strip()
        if not p or p.startswith("#") or p.startswith("|--"): continue
        for s in re.split(r"(?<=[.!?。])\s+|(?<=다\.)\s*", p):
            s = s.strip("-*> ").strip()
            if len(s) > 12: yield s

def numbers_in(s): return set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", s))

def flatten_numbers(obj, acc):
    if isinstance(obj, dict): [flatten_numbers(v, acc) for v in obj.values()]
    elif isinstance(obj, list): [flatten_numbers(v, acc) for v in obj]
    elif isinstance(obj, bool): pass
    elif isinstance(obj, (int, float)) and obj == obj:
        acc.add(str(int(obj)) if float(obj).is_integer() else str(round(obj, 3))); acc.add(str(round(obj, 2))); acc.add(str(round(obj, 1)))

def main(a):
    ref = set()
    for f in (a.replay, a.recon):
        if f and pathlib.Path(f).is_file(): flatten_numbers(json.loads(pathlib.Path(f).read_text(encoding="utf-8")), ref)
    rows = []
    for cf in a.claims:
        p = pathlib.Path(cf)
        if not p.is_file(): rows.append({"file": cf, "sentence": None, "status": "MISMATCH", "issues": ["file missing"]}); continue
        for s in sentences(p.read_text(encoding="utf-8")):
            issues = []; status = "SUPPORTED"
            for pat, rule, note in FORBIDDEN:
                if re.search(pat, s, re.I): issues.append(f"FORBIDDEN {rule}: {note}")
            has_grade = bool(re.search(GRADE, s, re.I)); has_n = bool(re.search(r"\b[nNmM]\s*=\s*\d+|\d+\s*건|\d+\s*/\s*\d+|\d+\s*개", s))
            is_claim = bool(re.search(r"(비율|분포|상관|median|IQR|ρ|rho|Spearman|Kruskal|산출|탐지|관측됐|관측되|FAIL|UNDETERMINED|N\s*=)", s))
            if re.search(HEDGE_N, s) and not has_n: issues.append("§2.5 N/분모 없는 일반화")
            for pat, rule, note in TODAY_RULES:
                if re.search(pat, s, re.I): issues.append(f"FORBIDDEN {rule}: {note}")
            for trig, comp, note in AXIS_C_CHECKS:
                if re.search(trig, s, re.I) and not re.search(comp, s, re.I): issues.append(f"AXIS_C: {note}")
            # A 14:21: '0건' must be written as 'N건 중 0건' — bare zero reads as 'not measured'
            if re.search(r"(?<![\d/])0\s*건", s) and not re.search(r"\d+\s*건\s*(중|가운데|에서)\s*0\s*건|0\s*/\s*\d+|\d+\s*(건|개)[^.]{0,25}시도", s): issues.append("분모 없는 '0건' — 'N건 중 0건' 으로")
            nums = numbers_in(s) - {"2026", "08", "27", "2", "1"}
            unmatched = sorted(n for n in nums if n not in ref and not re.match(r"^\d{1,2}$", n) is None and n not in ref)
            unmatched = sorted(n for n in nums if n not in ref)
            if is_claim and unmatched and ref: issues.append(f"NUMBER_NOT_IN_C_REPLAY: {unmatched[:6]}")
            if is_claim and not has_grade: issues.append("§4-2 grade 태그 없음")
            if any(i.startswith("FORBIDDEN") for i in issues): status = "MISMATCH" if any("NUMBER" in i for i in issues) else "UNSUPPORTED"
            elif any("NUMBER_NOT_IN" in i for i in issues): status = "MISMATCH"
            elif re.search(r"exploratory|EXPLORATORY|GRADE\s*C", s, re.I): status = "EXPLORATORY_ONLY"
            elif issues: status = "SUPPORTED_WITH_LIMITATION"
            if is_claim or issues: rows.append({"file": p.name, "sentence": s[:240], "status": status, "issues": issues, "grade_tag": has_grade, "has_n": has_n})
    out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    cnt = {}
    for r in rows: cnt[r["status"]] = cnt.get(r["status"], 0) + 1
    md = [f"# QA_CLAIM_LEDGER (C) — {now()}", "", f"기준: .agent_bus/landing_v2/CLAIM_GOVERNANCE.md §2/§4 · 재계산 참조: {a.replay}, {a.recon}", "", f"집계: {cnt}", "", "| file | status | issues | sentence |", "|---|---|---|---|"]
    for r in rows: md.append(f"| {r['file']} | **{r['status']}** | {'; '.join(r['issues']) or '-'} | {(r['sentence'] or '').replace('|','／')} |")
    md += ["", "> 최종 headline 판정은 A. C 는 §2 금지 스캔·grade 태그·N 병기·수치 일치만 판정한다. `NUMBER_NOT_IN_C_REPLAY` 는 A 가 인용하는 숫자가 C 재계산값 집합에 없다는 뜻이며, 반올림 차이일 수 있어 개별 확인 대상이다."]
    out.write_text("\n".join(md), encoding="utf-8"); print(json.dumps(cnt, ensure_ascii=False)); print("written", out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--claims", nargs="+", required=True); ap.add_argument("--replay"); ap.add_argument("--recon"); ap.add_argument("--out", default="out/QA_CLAIM_LEDGER.md"); main(ap.parse_args())
