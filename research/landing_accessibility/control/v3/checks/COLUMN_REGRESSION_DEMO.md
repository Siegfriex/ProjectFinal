# 열별 관측수 회귀 검사 — 실증

**도구** `checks/column_regression_check.py`
**메운 자리** 시정이 새 결측을 만드는 경로. 기존 두 검사(`COLUMN_SENTINEL`·`undermapped_columns`)가 모두 통과시켰고 생산자의 눈이 잡았던 자리다.

## 대조군 4/4

| # | 종류 | 입력 | 기대 | 실측 |
|---|---|---|---|---|
| 1 | `must_not_flag` | 같은 파일 | 회귀 없음, exit 0 | **회귀 없음, exit 0** |
| 2 | `must_flag` | `entry_control_type` 19행을 인위로 비움 | 잡아냄, exit 1 | **28 → 14 (-14), exit 1** |
| 3 | 미실행 구분 | 존재하지 않는 입력 | exit **3** (실패 1이 아님) | **exit 3** |
| 4 | `must_flag` | 열 하나 삭제 | 사라진 열 보고, exit 1 | **`menu_dependency` 사라짐, exit 1** |

종료코드: `0` 돌았고 깨끗 · `1` 회귀 있음 · `2` 못 돌았다 · `3` 입력 없음.

## 실전 — `snapshot_30` → 최종 `5290e0c3`

```
+  새 열 3: collection_run, entry_geometry_provenance, superseded_runs
!! 관측수 회귀 2열
   auth_gate_stage    26 ->  8  (-18)
   label_relation     26 -> 22  (-4)
```

**둘 다 우리가 의도한 시정이다.**
- `auth_gate_stage` — endpoint 미도달 행의 `NONE`(“게이트 없었다”는 주장)을 `UNDETERMINED`로 바꿨다
- `label_relation` — `MATCH`(동어반복)를 `AX_NOT_INDEPENDENTLY_OBSERVED`로 바꿨다

## 그래서 이 검사의 성질

**회귀 flag 는 두 가지를 구분하지 못한다.**

1. 값이 **사라졌다** — 시정이 만든 결측 (`entry_control_type` 28→9 가 이것)
2. **거짓 관측이 정직한 미관측으로 바뀌었다** — 위 두 건이 이것

**검사는 flag 를 낼 뿐 판정하지 않는다.** 각 건은 사람이나 상위 평면이 둘 중 무엇인지 분류해야 한다.
이것을 자동 실패로 다루면 **정직한 시정이 회귀로 잡혀 검사가 무시된다.**

역으로 이 성질이 값을 하나 준다: **회귀 목록은 "우리가 무엇을 거짓 관측에서 정직한 미관측으로 바꿨는가"의 목록이기도 하다.** 위 -18 과 -4 가 그것이다.

## 사용

```bash
python3 checks/column_regression_check.py --prev <이전.csv> --curr <현재.csv> [--json out.json]
```

**동결 직전에 이전 동결본과 대조해 돌린다.** 회귀가 나오면 각 열을 위 1/2 로 분류하고, 1이면 동결하지 않는다.


## 전제 — 이번 실행에는 소급 적용할 수 없다

이 검사는 **비교 대상 판본의 CSV 바이트**를 요구한다. 그런데 MAIN50 census 의 재동결은 **한 파일을 덮어쓰는 방식**이었고, **폐기 판본의 바이트가 남아 있지 않다.**

즉 이 검사가 겨냥한 바로 그 사건(`entry_control_type` 28→9, 판본 `4e276cf9`)에 대해 **소급 실행이 불가능하다.** 위 실전 예시가 `snapshot_30`→최종인 것도 그 때문이다 — 스냅샷은 남아 있고 동결본은 남아 있지 않다.

**다음 실행 전제**: 판본별 CSV 를 보존한다. 그림에 적용한 `_superseded_do_not_cite/` 방식이 mart 에도 필요하다.

*(B 가 짚었다 — 도구를 만든 쪽이 못 본 전제를, 도구가 겨냥한 결함의 당사자가 짚었다.)*
