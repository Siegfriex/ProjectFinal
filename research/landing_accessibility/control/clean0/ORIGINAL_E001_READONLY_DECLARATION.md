# ORIGINAL_E001 — READ_ONLY 재고정

**ID** `LA-E001-RO-2.1-20260827T2055`
**발행** Claude A · **assertion_type** `DECISION` (§2 는 `OBSERVATION`)
**근거 SSOT** `docs/v2_1/00_SSOT_v2.1_POST_PILOT_RECOVERY.md §13`, `09_DECISION_LOG_SEED §D-02`

---

## §1 DECISION

```
ORIGINAL_E001 = READ_ONLY
덮어쓰기 금지 · 병합 금지 · 삭제 금지 · 재실행으로 대체 금지
recovery 결과는 ORIGINAL_E001 을 대체하지 않는다 — 층이 얹힐 뿐이다
```

**READ_ONLY 의 범위** (이하 전부):

| 대상 | 위치 | 지위 |
|---|---|---|
| E001 raw evidence 66 디렉터리 / 60 관측 / 1,103 파일 / 753,676,839 bytes | Git 밖 — `ARTIFACT_RETENTION_MANIFEST.json` 의 4개 lane root | `READ_ONLY` |
| canonical mart `artifacts/e001_real_marts/` (56행) | `claude-b/analysis-current@82f631f` | `FINAL_ACCEPTED (PILOT/PRELIMINARY)` |
| 판정문 `FINAL_CORRECTION_RECORD` / `AXIS_A_NOT_EVALUATED` / `AXIS_C_VERIFIED_RESULT` | `control@084eff5` | `IMMUTABLE_RECORD` |
| bus tickets / completions (기존) | `.agent_bus/landing_v2/` | `APPEND_ONLY` |

---

## §2 동결되는 사실 — OBSERVATION

```
attempted              59 / 59
grade                  PILOT / PRELIMINARY
Axis A (KWCAG)         NOT_EVALUATED          — production criterion adjudicator 부재
Axis B (MPFED)         mpfed_available 0 / 59 — task wiring 갭 + 실사이트 detector 갭
Axis C (obstruction)   raw measured, classification incomplete
planned association    NOT_COMPUTABLE
substitute analysis    none
forbidden action       0
```

**이것은 실패한 접근성 결과가 아니라 측정 시스템 파일럿 결과다.**

이번 CLEAN-0 에서 A 가 T1 수준으로 **독립 재확인한 것**:

```
mart 56 행 ⊂ evidence 60 관측         고아 0 건
evidence 60 − mart 56 = 격리 4 건      인계 §E 표와 일치
66 dirs − 60 obs = 6                   retry 중복 디렉터리(manifest.jsonl 없음)
```

인계 §E 의 경고가 실측으로 재확인됐다 — **`66` 은 디렉터리를 세고 `56` 은 mart 행을 센다.
단위가 다르므로 `56+4+6` 같은 합산은 하지 않는다.**

---

## §3 ORIGINAL_E001 로 할 수 있는 것

```
L0 raw evidence 재사용 (offline replay 주모집단 n = 56 파일)
guard failure 분포 근거
wiring 결함 증거
detector gap 증거
Axis C page-level raw geometry
provenance / duplicate-launch 교훈
```

## §4 ORIGINAL_E001 로 할 수 없는 것

```
MPFED 0/59 를 서비스 특성으로 해석
"Axis A 결과" 라고 주장
guard 차단을 접근성 실패로 해석
pilot 에서 계산 불가능했던 association 을 사후 대체
반사실 일반화 — "올바른 detector 였다면 depth 는 최대 8" 은 확인된 바 없다
```

## §5 offline replay 가 허용되는 이유

replay 는 **읽기**다. evidence 를 수정하지 않고, 새 실사이트 접속도 하지 않는다.
주모집단 `n = 56 (파일 단위)`. **E000 9 디렉터리 / 6 고유 타깃은 sensitivity-only 이며
n=56 에 합산하지 않는다.**

**replay 가 검증할 수 없는 것을 미리 못박는다** (인계 §F-6):
L1 step DOM 캡처가 없으므로 **갭2 의 endpoint 부분은 오프라인에서 검증 불가**다.
이 사실은 이후 어떤 PASS 문서에도 "검증하지 않은 것" 절로 반드시 남는다.
