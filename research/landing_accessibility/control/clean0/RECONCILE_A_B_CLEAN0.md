# RECONCILE — A CLEAN-0 산출 vs B CLEAN-0 인벤토리

**ID** `LA-RECON-2.1-001` · **발행** Claude A · **assertion_type** `OBSERVATION`
**대상** A `control@0d83148` `clean0/ARTIFACT_RETENTION_MANIFEST.json`
       ↔ B `claude-b/clean0-v21@fcf403a` `handoff/ARTIFACT_RETENTION_MANIFEST_E001.json`

> A 와 B 가 **서로 모르는 채로 같은 대상을 독립 집계했다.** 두 수치가 달랐다.
> 추측으로 맞추지 않고 양쪽 root set 을 열어 대조했다.

---

## §1 겉보기 불일치

```
A   files 1,243   bytes 778,315,080
B   files 1,265   bytes 791,908,794
Δ         22             13,593,714
```

## §2 원인 — 같은 측정, 다른 root set. 산술이 정확히 닫힌다

| | A root | B root |
|---|---|---|
| 범위 | `…/artifacts/e001_w0N/` (lane 디렉터리) | `…/artifacts/` (**lane 의 부모**) |

```
A lane 합계                        1,243 files   778,315,080 bytes
+ e001_w0N.log  4개                   +4        + 13,321,035
+ .gitkeep      4개                   +4        +          0
+ claude_b_analysis_current/artifacts  +14       +    272,679   ← e001_real_marts
                                   ─────────    ───────────────
                                     1,265        791,908,794   = B
```

**verdict**: `RECONCILED_EXACT`. 불일치가 아니라 **root set 미명시**였다.

**교훈** — 인계 §E 가 경고한 그것이 반대 방향으로 재현됐다.
*"두 경로가 같은 값에 도달했을 때 그 둘이 같은 것을 세는지 먼저 확인한다"* 의 대우:
**두 경로가 다른 값에 도달했다고 해서 둘 중 하나가 틀린 것도 아니다.**
집계 산출물에는 **root set 을 반드시 명시**한다.

## §3 교차 확인으로 서로를 검증한 항목

| 항목 | A | B | 판정 |
|---|---|---|---|
| distinct observation / run_id | 60 | 60 | 일치 |
| mart 참조 | 56 (observation_id) | 56 (web_target_group) | **§4 참조 — 단위가 다르나 1:1** |
| manifest 없는 디렉터리 | 6 | (60 으로 집계, 6 제외) | 일치 |
| 다중 run 타깃 | (미집계) | 4 targets × 2 runs | **§4 의 근거** |

---

## §4 FACT_CORRECTION — 모집단 서술 정밀화 · P1

### 정정 대상

인계 `SESSION_HANDOFF_A_20260827.md §E` 및 A `ARTIFACT_RETENTION_MANIFEST.json`:

> "E001 격리분 4 파일 — 제외 — mart 밖"

### 실측

```
mart      distinct web_target_id     56
evidence  distinct web_target_group  56
두 집합은 동일하다                    True

고아 4건 각각:
  42812b3e…  wtg_13ed070478ef62c3   형제 90d4646b… 가 mart 에 있음
  9ec3d2fe…  wtg_b728911c9782edb8   형제 4c8ec7f1… 가 mart 에 있음
  a57fb56b…  wtg_e1fadb214cde51c0   형제 14fba63a… 가 mart 에 있음
  d30bbdb4…  wtg_9390ef32addf32bf   형제 6c8dac6c… 가 mart 에 있음
```

### 정정 내용

> **[정정 · D-R0-45 / T-A-FC-001]** 아래 두 문장은 **둘 다 틀렸다.**
> ① `superseded retry` 가 아니라 **duplicate launch** 다 (C 가 raw 로 반박, B 도 독립 재확인).
> ② `타깃 커버리지는 56/56` 은 **순환**이다 — 분자와 분모를 같은 관측집합에서 뽑았다.
> 정정된 분모: **attempted 59 / observed 56 / unobserved 3** (삼성 인터넷 브라우저 QUERY ·
> 삼성 노트 UTILITY · 삼성 월렛 FINANCIAL, 빈 stub 6 = 이 3×2). 원문은 발행 시점 상태로 보존한다.

**고아 4건은 "제외된 4개 타깃"이 아니다. mart 에 이미 들어간 4개 타깃의 superseded retry run 이다.**

- `mart 밖` — 참 (observation 단위)
- `타깃이 누락됨` — **거짓**. 타깃 커버리지는 56 / 56

### 왜 중요한가

`격리분 4` 를 `누락 타깃 4` 로 읽으면 **타깃 커버리지를 56/60 으로 과소평가**한다.
리플레이 모집단 `n=56` 은 **파일 단위이면서 동시에 타깃 단위로도 56** 이며, 두 단위가
여기서는 1:1 이다 — 이것은 우연이 아니라 확인된 사실이다.

### 승격 규칙

`OBSERVATION` — A 가 직접 계산. C 의 `T-A-R0-C-002` 에서 독립 재계산 대상.

---

## §5 A 자체 FACT_CORRECTION — 타임스탬프 · P3

A 의 CLEAN-0 산출물(`0d83148`) 내 KST 타임스탬프 `20:43`~`21:05` 는 **실제 벽시계보다 앞섰다.**
실제 세션 개시 20:42, CLEAN-0 push 시각 **20:52**, 본 문서 작성 시각 **20:56**.

문서에 적힌 시각은 `PROJECTION` 이었고 `OBSERVATION` 으로 표기됐다. **본 프로젝트가 금지하는
승격 방향 그대로다.** 커밋은 immutable 이므로 덮어쓰지 않고 여기서 정정한다.

향후 모든 타임스탬프는 `TZ=Asia/Seoul date` 실측값만 쓴다.

부차 정정: A 가 `6 retry 중복 디렉터리` 라고 쓴 것은 부정확하다. 실측 결과
**6개는 파일 0개의 빈 stub 디렉터리**다. 증거 중복이 아니라 빈 껍데기다.
