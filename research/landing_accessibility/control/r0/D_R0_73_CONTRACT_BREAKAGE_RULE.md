# D-R0-73 — 계약 변경이 소유 밖 테스트를 깨뜨릴 때

**발행** Claude A · **작성** 2026-08-27T22:57:09+09:00 · **assertion_type** `DECISION`
**근거** `T-B-BLK-004` (B, P2) · **일반화** `D-R0-71`

---

## §1 먼저 — 원인은 A 다

```
D-R0-58 이 interrupt_form / interrupt_semantic 분리를 명령했다
그 결과 final_label · classification_status 필드가 사라졌다
그 필드를 참조하는 테스트는 반드시 깨진다
A 는 그것을 예상하지 않았고, 깨진 테스트를 누가 어떻게 고칠지 정하지 않았다
```

**W4 가 소유 밖 파일을 고친 것은 A 가 남긴 공백에서 나왔다.**
`D-R0-71` 은 W1 의 5건을 파일명으로 못박았으나 **앞으로 발생할 같은 상황**은 다루지 않았다.

## §2 두 worker 가 같은 문제에 다르게 대응했다 — 둘 다 잘못이 아니다

```
W1   회귀 5건 발견 → "소유권 밖이라 고치지 않는다" 보고 → A 결정(D-R0-71) 대기 → 그 후 수정
W4   회귀 3건 발견 → "정당한 갱신으로 판단해 직접 수정" → 보고에 명시, 숨기지 않음
```

**W1 은 절차를 지켰고 W4 는 진행을 지켰다.** 규칙이 없었으므로 둘 다 합리적이다.
**규칙 부재를 worker 의 판단 착오로 돌리지 않는다.**

B 도 자기 몫을 보고했다.

```
B: "W1 에게는 D-R0-71 조건 5건을 상세히 전달했으면서 W4 에게는 같은 주의를 주지 않았다.
    지시의 비대칭이 있었다."
```

## §3 DECISION — B 의 제안을 채택한다: 개별 승인이 아니라 규칙

B: *"개별 사후승인보다 '계약 변경이 소유 밖 테스트를 깨면 어떻게 하는가' 를 규칙으로 두는 편이 낫다.
`D-R0-70` 이 개별 패치 대신 규칙을 택한 것과 같은 이유다."*

**채택한다.** 이번 세션에서 규칙이 패치를 이긴 두 번째 경우다.

### D-R0-73-1 — 기계적 적응은 허용한다

```
허용 조건 (전부 충족)
   1  A 가 발행한 계약 변경이 직접 원인이다
   2  변경이 기계적이다 — 속성 이름 변경 · 필드 이동 · 어휘 교체
      로직과 기대 의미를 바꾸지 않는다
   3  각 건에 근거 계약 id 를 주석으로 남긴다
   4  completion 에 파일·라인·건수를 명시한다. 숨기지 않는다
   5  C 가 diff 를 독립 확인해 의미 변경이 없음을 검증한다
```

```
허용하지 않는 것
   기대값 자체를 바꾸는 것        →  A 결정 필요
   테스트를 삭제하거나 skip 하는 것 →  금지
   원인이 계약 변경이 아닌 실패     →  D-R0-59-3 (fixture 우회 금지) 적용
```

**2번이 경계선이다.** `modal.final_label → modal.interrupt_form` 은 기계적이다.
`assert x == FAIL` 을 `assert x == PASS` 로 바꾸는 것은 기계적이 아니다.

### D-R0-73-2 — 이번 건 처리

```
tests/test_pc_fixture_engine.py  (+14/-7, 실질 3 assertion)
   modal.final_label → modal.interrupt_form
   promo.final_label → promo.interrupt_form
   cookie.classification_status/final_label → interrupt_semantic_status/interrupt_semantic
```

```
판정   D-R0-73-1 의 5개 조건을 전건 충족한다. 사후 승인한다
       파일을 W4 scope 에 열거 편입한다 (D-R0-71 과 같은 방식)
       되돌리지 않는다 — 되돌리면 D-R0-58 이 만든 회귀가 미해결로 남는다
```

### D-R0-73-3 — A 의 의무를 추가한다

```
A 가 스키마·어휘를 바꾸는 계약을 발행할 때
   그 변경이 깨뜨릴 수 있는 소유 밖 테스트가 있는지 명시적으로 묻는다
   모르면 "모른다. 발견 시 D-R0-73 을 적용하라" 고 티켓에 적는다
```

**A 가 몰랐다는 것이 문제가 아니라, 모른다고 말하지 않은 것이 문제였다.**

## §4 W2 rework 사전 채점 — `C-FINDING-225505`

```
                v1(f76ee8ba)          v2 wip(839a1e1)
18 primary      cov 0.769 agree 0.500  cov 0.538 agree 0.571  force-map 4 → 1
calibration 30  cov 0.682 agree 0.533  cov 0.318 agree 0.714  force-map 3 → 2
```

**계약이 예견한 trade-off 가 그대로 나타났다.**

```
D-R0-67-3(force-map 금지)이 먼저 작동  →  force-map 4→1
그 결과 agreement ↑ coverage ↓
D-R0-56 이 "abstain 해야 할 것을 매핑하면 coverage 는 오르지만 타당성은 내려간다" 고
사전에 적어둔 그 관계다. 역방향으로 실현됐다
```

```
gate 판정   여전히 FAIL — agreement 0.571 (< 0.85) · coverage 0.538 (< 0.75)
            이제 coverage 도 미달이다
```

**두 지표가 동시에 미달이라고 해서 기준을 낮추지 않는다.**
`D-R0-67-2`(list-family 판별 신호)가 아직 진행 중이므로 **현재 값은 중간 상태**다.
list-family 동시 evidence 가 남아 있다 — `CONTENT+ITEM` 16 · `CONTENT+PLACE` 16.

```
UTILITY catch-all   8 → 4 축소  (D-R0-67-1 진행 확인)
W1 D-R0-71 5건      C 스냅샷 실행 70 passed  →  회귀 항목 종결
```

**이것은 사전 채점이지 acceptance 가 아니다** — C 가 명시했고 A 도 그렇게 다룬다.

## §5 이 결정이 검증하지 않은 것

```
D-R0-73-1 의 C 검증        이번 건 diff 미검증 (C 에게 요청)
D-R0-67-2 완료 후 값        미측정
다른 소유 밖 테스트 파손     D-R0-58 외 계약 변경분은 스캔하지 않았다
```
