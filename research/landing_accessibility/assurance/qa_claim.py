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
            # A 14:21: '0건' must be written as 'N건 중 0건' — bare zero reads as 'not measured'
            if re.search(r"(?<![\d/])0\s*건", s) and not re.search(r"\d+\s*건\s*(중|가운데|에서)\s*0\s*건|0\s*/\s*\d+|\d+\s*(건|개)\s*(을|를)?\s*시도", s): issues.append("분모 없는 '0건' — 'N건 중 0건' 으로")
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
