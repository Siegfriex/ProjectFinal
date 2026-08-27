"""ruling_id_norm 의 양방향 대조 — 좁으면 오탐, 넓으면 미탐.

positive: 실제로 관측된 표기 쌍이 present 로 나와야 한다 (D 가 겪은 두 오탐 포함)
negative: 다른 판정으로 잘못 걸리면 안 된다
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ruling_id_norm import present, variants

POS = [
    ("Δ21",      "## Δ21 — R21 판정 색인 (정본화)",      "R21 ↔ Δ21 — 2차 오탐의 형태"),
    ("Δ21",      "티켓 본문은 R21 로만 부른다",           "티켓 표기"),
    ("Δ14-P06",  "P-06 SWITCH_TAB 은 reveal 이 아니다",   "D-DEF-14 의 형태"),
    ("Δ15-GAP07","GAP-07 행이 자기 시점을 선언한다",      "GAP 하이픈"),
    ("Δ10-R13a", "### Δ10-R13 auth_gate_stage",           "접미 a 제거"),
    ("Δ8-R3b",   "R3 는 task_role 을 추가한다",           "접두 제거 + 접미 제거"),
    ("Δ22-R22",  "### R22 — 관측은 포착 스택 전체의",     "절 접두 제거"),
]
NEG = [
    ("Δ21",      "Δ2 와 Δ1 만 언급한다",                  "부분 숫자 매칭 금지"),
    ("Δ14-P06",  "P-060 이라는 다른 표기",                "경계 초과 매칭 금지"),
    ("Δ10-R13a", "R1 과 R3 만 있다",                      "R13 을 R1+R3 로 오인 금지"),
    ("Δ22-R22",  "R2 만 언급",                            "R22 를 R2 로 오인 금지"),
]

def main() -> int:
    fails = []
    for rid, text, why in POS:
        ok = present(rid, text)
        print(f"  {'OK  ' if ok else 'FAIL'} positive {rid:<12} in {text[:38]!r:<42} ({why})")
        if not ok:
            fails.append(f"positive 미검출 {rid}")
    for rid, text, why in NEG:
        ok = not present(rid, text)
        print(f"  {'OK  ' if ok else 'FAIL'} negative {rid:<12} vs {text[:38]!r:<42} ({why})")
        if not ok:
            fails.append(f"negative 오탐 {rid}")
    print()
    if fails:
        print(f"SELFTEST FAIL — {len(fails)}건"); [print("  -", f) for f in fails]; return 1
    print(f"SELFTEST PASS — positive {len(POS)}/{len(POS)} · negative {len(NEG)}/{len(NEG)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
