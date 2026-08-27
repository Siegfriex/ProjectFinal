# D-R0-71 — 의도된 회귀 5건: 소유 예외로 편입한다

**발행** Claude A · **작성** 2026-08-27T22:41:55+09:00 · **assertion_type** `DECISION`
**근거** `T-B-FC-006` (B 자진 정정, P2) · **supersedes** `D-R0-66-2` (건수 부분)

---

## §1 4건이 아니라 5건이었다 — 그리고 원인이 익숙하다

```
B 정정   5건이다. 3개 파일에 분산. 전부 같은 원인(G1-a target-level kill 폐기)
원인     W1 의 회귀 스윕 범위가 tests/test_e001_* + test_pc_* + test_w1_* 로 좁았고
         tests/test_e000_real_target_scope_gate.py 를 포함하지 않았다
B 명시   "4→5 로 늘어난 것이 아니라 처음부터 5였다. 원장귀속 커밋(fd7fd918)과 무관하다"
```

**스캔 범위가 답을 정했다. 이 세션에서 네 번째다.**

```
A   degenerate capture 를 파일 크기로 스캔        →  132KB·676KB 를 놓쳤다
A   gate_signals 를 최상위에서 조회               →  0건. 실제 경로는 raw_features 아래였다
C   grep 을 research/landing_accessibility 로 제한 →  repo-root tests/ 를 놓쳤다
W1  회귀 스윕을 test_e001_*/test_pc_*/test_w1_* 로  →  test_e000_* 를 놓쳤다
```

**네 건 모두 "0 또는 N 을 얻었는데 범위가 답을 만들었다" 이고, 네 건 모두 다른 사람이 잡았다.**
`D-R0-57 SUPERSEDED §5` 에 A 에 대해 적은 것이 plane 을 가리지 않고 성립한다.

## §2 A 가 기록하는 두 가지 처신

### W1

```
B: "W1 이 4·5번을 실패 메시지만 보고 '고장' 으로 넘기지 않고 개별 traceback 을 열어
    '테스트의 진짜 취지가 살아있는지' 를 확인한 것이 이 분류의 핵심이다.
    두 건 다 검증 대상 동작은 정상이고 하드코딩 상수만 옛 계약을 담고 있었다."
```

**실패한 테스트를 통과시키는 가장 쉬운 길은 기대값을 바꾸는 것이다.**
W1 은 그렇게 하지 않고 **무엇을 검증하려던 테스트인지** 를 먼저 봤다.
그리고 자기 집계 누락을 스스로 정정했다.

### B

```
B 가 D-R0-69 전용 워크트리에서 fd7fd918 을 체크아웃해 tests/ 전체를 돌렸다
475 passed / 5 failed / 1 xfailed — W1 분류와 정확히 일치
```

**`D-R0-69` 가 나온 지 몇 분 만에 그 규칙대로 검산했다.** worker 워크트리를 건드리지 않았다.

## §3 DECISION — (a) 도 (b) 도 아닌 명시적 편입

B 가 물은 것: (a) 소유자가 수정 (b) W1 scope 에 예외 편입.

```
문제   (a) 의 '소유자' 가 없다. 세 파일은 W2/W3/W4 어느 소유도 아니다
       W2 = l1_engine · l0_probe · gate_classifier
       W3 = kwcag
       W4 = l0_collector.classify_interrupt · build_mart_axisc
       세 test 파일은 공유 코드베이스에 있고 전담 worker 가 없다
```

```
DECISION  (b) 를 택하되 파일을 열거해 편입한다
   tests/test_e000_real_target_scope_gate.py
   tests/test_e001_account_action_guard.py
   tests/test_e001_default_executor_l0_l1.py
   → W1 scope 에 명시적 예외로 편입. 이 세 파일의 소유자는 W1 이다
```

**열거하는 이유**: "소유 밖 파일을 고쳐도 된다" 로 열면 §2 가 무너진다.
**세 파일을 이름으로 못박으면 소유는 여전히 단일하다.**

## §4 조건 — `D-R0-66-2` 를 5건으로 갱신해 승계

```
1  갱신 대상은 정확히 그 5건이다. diff 에 다른 assertion 변경이 섞이면 거부한다
2  각 건에 '무엇을 기대했고 계약이 어떻게 바뀌었는지' 를 주석으로 남긴다
3  C 가 diff 를 독립 확인해 다른 assertion 이 약화되지 않았음을 검증한다
4  D-R0-59-3 'fixture 로 우회 금지' 와 구분된다 —
   그것은 production 결함 은폐 금지이고 이것은 폐기된 계약을 검사하는 테스트의 갱신이다
5  [신규] 갱신 후 tests/ 전체를 다시 돌려 새 실패가 없음을 확인한다.
   범위를 좁힌 스윕으로 확인하지 않는다 — 이번 undercount 의 원인이 그것이다
```

**5번이 이번 정정에서 배운 것이다.**

## §5 MLflow — immutability 준수 기록

```
B: "정정본을 새 run 으로 기록했다. 과거 run(d434ee93, 4건 기재)의 metric 은 수정하지 않았다"
```

Director 계약의 *"결과를 덮어쓰지 않는다. 새 실험은 새 run"* 이 실제로 지켜졌다.
**틀린 값이 남아 있는 것이 정상이다** — 그것이 정정 이력이다.

## §6 이 결정이 검증하지 않은 것

```
5건 갱신 diff        아직 없다
갱신 후 tests/ 전체   미실행
다른 파일의 동종 회귀  전체 스윕이 5건을 찾았으나 '전체' 가 tests/ 로 한정된다
```
