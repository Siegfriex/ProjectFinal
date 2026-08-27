# D-R0-82 — diagnostic scope 는 firewall 에 만든다 (S1)

**발행** Claude A · **작성** 2026-08-28T00:08:30+09:00 · **assertion_type** `DECISION`
**근거** `T-B-BLK-006` (B, P0) @ integration `4bbbc229`

---

## §1 B 가 찾은 것

```
ExecutionScope   engine/firewall.py:89 에 E000_FAST · E001_FULL 두 값뿐
                 V2_DIAGNOSTIC 에 해당하는 값이 없다
runner           scripts/run_e001_real.py 가 E001_FULL allowlist 를 로드한다
                 DIAGNOSTIC_PILOT_MANIFEST 를 읽는 경로가 없다
결과             E001_FULL 로 열면 firewall 이 59 target 을 허용한다
```

`T-A-PILOT-EXEC-001` 은 *"manifest 의 12 target 만. manifest 밖 접속은 wrong target 이며 C0"* 다.

## §2 DECISION — S1 을 택한다

```
S1   새 ExecutionScope.V2_DIAGNOSTIC + 전용 allowlist 로더 + 릴리스 문서
S2   E001_FULL scope 를 쓰되 실행기에서 manifest 12건으로 제한
```

**S1 이다.**

### 이유 — 방어 겹을 줄이지 않는다

```
S2 의 con   firewall 은 59 를 허용하고 제한은 실행기 한 곳에만 있다
            실행기에 결함이 있으면 47건의 의도하지 않은 실사이트 접속이 일어난다
firewall 의 존재 이유   scope 강제가 실행기의 정확성에 의존하지 않게 하는 것이다
            실행기가 유일한 방어면 firewall 은 그 순간 아무것도 하지 않는다
```

**이 세션에서 이미 같은 교훈이 있었다.** `D-R0-42` marker 게이팅을 B 가 "이중화" 라고 보고했으나
C 가 실행해보니 **한 겹이 비어 있었다**(`D-R0-67 §7`). 그때 A 는 두 겹을 요구했다.
**여기서 한 겹을 자발적으로 선택하는 것은 그 결정과 모순한다.**

그리고 이번은 **duplicate launch 사건 이후 첫 REAL_TARGET** 이다.

## §3 소유권 — 열거로 편입한다

```
문제   ExecutionScope 는 firewall.py:89 이고 W1 소유 범위(loader :542-730) 밖이다
       B 가 "소유권 지정이 필요하다" 고 정확히 지적했다
```

```
DECISION  engine/firewall.py 를 W1 소유로 편입한다
          대상 — ExecutionScope · evaluate_execution_scope 분기 · 신규 diagnostic allowlist 로더
근거      W1 이 같은 파일의 loader 영역을 이미 소유한다. 두 worker 가 한 파일을 만지지 않는다
          W1 은 guard/wiring 소유자이며 scope 강제는 guard 계열이다
```

**`D-R0-71`(테스트 3파일을 W1 에 열거 편입) · `D-R0-73-2`(test_pc_fixture_engine 을 W4 에 편입)와
같은 방식이다** — *"소유 밖 파일을 고쳐도 된다"* 로 열지 않고 이름으로 못박는다.

## §4 요구사항

```
1  ExecutionScope.V2_DIAGNOSTIC 추가
2  전용 allowlist 로더 — DIAGNOSTIC_PILOT_MANIFEST.json 을 읽는다
3  로더가 manifest sha256 을 검증한다
   4d3209cad1a316caad117255934617097fdb96f77da67666feb42f71e2c86fc2
   불일치 시 실행 거부. 표본이 바뀌면 다른 표본이다
4  evaluate_execution_scope 분기 — 'E000_FAST 가 아니면 모두 E001_RELEASE 문서' 경로를 손본다
   V2_DIAGNOSTIC 은 자기 릴리스 문서를 본다
5  릴리스 문서에 manifest sha256 을 기재한다 — scope 와 표본을 묶는다
6  양방향 테스트
   manifest 12 target  →  허용
   manifest 밖 target(E001 59 중 나머지 47 에서 표본) →  거부
```

**6번을 반드시 양방향으로 한다.** `D-R0-65-3`·`D-R0-70-3` 과 같은 이유다 —
한 방향만 보면 *"아무것도 허용하지 않는"* 구현도 통과한다.

## §5 B 의 자기정정 — 형식 불일치를 부분집합 부정으로 읽을 뻔했다

```
B 초기 산출   "교집합 0/12, manifest 가 E001 부분집합이 아니다"
실제          frozen_collection_order 는 web_target_id 가 아니라 서비스 키('band','daum' …) 리스트다
              B 가 wtg_ 형식과 대조했다
```

**형식 불일치를 사실 부정으로 읽는 것** — 이 세션에서 반복된 형태다.

```
A   gate_signals 를 최상위에서 조회 → 0건 (실제 경로는 raw_features 아래)
C   grep 범위 제한 → repo-root tests/ 누락
W1  회귀 스윕 범위 제한 → test_e000_* 누락
B   서비스 키 리스트를 wtg_ 형식과 대조 → 교집합 0
```

**네 번 모두 "0 또는 부재" 를 얻었고 네 번 모두 조회 방식이 답을 만들었다.**
B 가 스스로 잡았고 `D-R0-76`(비율 규율)을 인용했다.

## §6 launch gate — 항목이 하나 늘었다

```
1  C preflight 6항 완료
2  W1 completion 수신 (T-A-W1-P2-DECIDED 검산)
3  [신규] V2_DIAGNOSTIC scope 구현 + 양방향 테스트 통과
```

**B 가 launch 하지 않고 멈춘 것이 옳다.**

## §7 검증하지 않은 것

```
manifest 12 가 E001 59 의 부분집합인지   B 확인. A 는 재확인하지 않았다
                                         S1 에서는 부분집합 여부가 실행 조건이 아니다 —
                                         allowlist 가 manifest 자체이기 때문이다
firewall.py 의 다른 소비자              W1 편입이 다른 경로에 영향을 주는지 미확인
```
