# V3 채택 기록 — A / Authority Plane

발행 2026-08-28 KST · A `control/landing-orchestrator`
근거 Director 지시: "SSOTV3 가 유일 SSOT로 선정한다"
SSOT `SSOTV3/` 21 파일 · MANIFEST sha256 `1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a`

---

## 1. 무결성 — 독립 재계산

| 항목 | 결과 |
|---|---|
| MANIFEST 등재 20 파일 sha256 + byte length | 불일치 **0/20** |
| 매니페스트 밖 디스크 파일 | `MANIFEST_v3.0.json` 1건 (자기참조 제외, 정상) |
| D 평면 독립 재계산 (D-V3-FINDING-001) | 불일치 0/20 — **A 와 독립 일치** |

두 평면이 서로의 숫자를 받지 않고 각자 계산해 같은 결과에 도달했다. T2 수준 사실이다.

## 2. 채택 범위와 실행권한

SSOTV3 는 **연구설계·측정계약의 유일 권위**로 채택한다. 동시에 다음은 그대로다.

- v3 는 새 REAL scope 를 **발행하지 않는다** (00 §13, 09 D3-20, README 권위경계).
- 현재 유효한 REAL 은 A 가 발행한 `V2_DIAGNOSTIC` 12 target 뿐이다.
- `E001_FULL` 59 는 SUSPENDED 유지. v3 는 이를 재개하지 않는다.
- v3 main 50 은 **candidate frame** 이며 precheck + A manifest freeze 전에는 REAL 수집 금지.

**따라서 채택은 릴리스가 아니다.** 문서 권위가 바뀌었을 뿐 접속 권한은 한 건도 늘지 않았다.

## 3. Supersession — A 가 보존한 방법론과의 대조

`control/method/METHODOLOGY_PRESERVED.md` 는 피벗 전에 "무엇이 대상과 무관하게 살아남는가"를 §1~§8 로 동결해 두었다. v3 00 §12 의 승계 목록과 대조한다.

| METHODOLOGY_PRESERVED | v3 대응 | 판정 |
|---|---|---|
| §1 Plane 구조 (생산자/판정자 분리) | 06 §1 A/B/C/D 역할 | 승계 — D 라우팅이 `to=C, cc=A` 로 명문화되어 더 강해짐 |
| §2 진실 위계 T1~T6 | 06 §2 동일 6단계 | 승계 — 문면 일치 |
| §3 검증 규율 (대조군·양성대조·독립재계산) | 06 §8 완결 게이트, 13 C 규칙 | 승계 |
| §4 게이트 운영 | 07 Stop Conditions, 06 §8 | 승계 — 게이트 *수치*는 v3 에 없음(정상, 대상 특정값) |
| §5 `presence ≠ operative` 실패 카탈로그 | 00 §6 auth, 03 §9 obstruction, 04 entry_label_modality | **승계이자 v3 의 설계 동기** — "login 존재로 중단 금지", "geometry 겹침만으로 modal 확정 금지" 는 같은 결함군의 시정이다 |
| §6 안전·실행 통제 | 00 §6, 03 §7·§8, 07 Stop Conditions | 승계 — credential/transaction/CAPTCHA 금지 문면 유지 |
| §7 사전등록 규율 | 00 §5 "결과를 본 뒤 task/endpoint/target 변경 금지", 05 §5 sensitivity 사전정의 | 승계 — 강화됨 |
| §8 재현 가능성 | 02 §8 append-only identity, 06 §6 exactly-once | 승계 |

**§0 의 "보존하지 않는다" 목록이 v3 로 채워진 대응:**

| 폐기·유보한 대상 특정값 | v3 가 넣은 것 |
|---|---|
| 7 archetype (sampling quota) | legacy metadata / codebook 으로 강등 (09 D3-04) — 삭제 아님 |
| MPFED/NED/IED primary | Flow 가 primary, Depth 는 derived (09 D3-05) |
| OverlayCoverage | `task_control_occlusion` 이 primary, coverage 는 보조 (09 D3-12) |
| 59 frame | USAGE_BENCHMARK / ROBUSTNESS_CORPUS (09 D3-15) |
| W1~W4 범위 | 07 Phase V3-5 "기존 W1/W3/W4 instrumentation 최대 재사용" |
| 0.85 / 0.75 게이트 수치 | v3 에 없음 — 새 대상의 게이트는 아직 정의되지 않았다 |
| KWCAG criterion set | Axis A 독립축으로 존치 (00 §3) |

대조 결과 **METHODOLOGY_PRESERVED §1~§8 중 폐기된 항목은 없다.** 피벗은 방법론이 아니라 대상을 바꿨다. 이는 피벗 전 A 의 예측과 일치한다.

## 4. v3 가 명시적으로 뒤집는 v2.1 해석

1. 대표기능 자동매핑(RF-DT/NLP fallback)의 **본수집 필수성** — 해제. W2 detector 는 삭제하지 않되 main critical path 의존에서 제거(07 Legacy closeout).
2. 59 를 본연구 단일 분석 frame 으로 보는 해석 — 폐기.
3. Depth 를 primary construct 로 보는 해석 — 폐기.

이 세 건은 **A 가 v2.1 에서 내린 결정의 전제를 무효화한다.** 특히 `T-A-HOLD-001`(W2 detector 게이트 FAIL) 의 성격이 바뀐다 — 아래 §6.

## 5. 08 Baseline 대조 — 7건 중 5 일치 · 2 stale · 1 참조위험

| plane | 08 기재 | 실측(원격) | 판정 |
|---|---|---|---|
| A `control/landing-orchestrator` | `8f413527` | `5c22faeb` | **STALE** — 8f41352 는 5c22fae 의 조상. 2 커밋(99377bb, 5c22fae) 뒤. rewrite 아님 |
| promoted main | `bc0b7a08` | `bc0b7a08` (origin) | 일치 — **단 로컬 ref 위험, §5.1** |
| B `claude-b/diag-pilot-integration` | `01041bc2` | `01041bc2` | 일치 |
| B W2 `claude-b/w2-rf-detector` | `b28aaa5c` | `b28aaa5c` | 일치 |
| C `claude-c/assurance-current` | `1baa865b` | `1baa865b` | 일치 — **단 C 작업 브랜치는 `claude-c/assurance-v21 @ 41fa3b01`, §5.2** |
| D `claude-d/research-sandbox-v21` | `bcaa634b` | `cf05035c` | **STALE** — 4 커밋 뒤 |
| `control/pilot-manifest` | `54a0c7a4` | `54a0c7a4` | 일치 |

08 은 스스로 "release document 가 아니라 기준선"이라고 밝힌다. stale 2건은 **pack 의 결함이 아니라 갱신 대상**이다. 그러나 갱신 전까지 08 의 SHA 를 실행 근거로 인용하면 안 된다.

### 5.1 로컬 ref 참조 위험 — P1

```
refs/heads/research/landing-accessibility-main          = 32460b87   ← 로컬
refs/remotes/origin/research/landing-accessibility-main = bc0b7a08   ← promoted main 정본
32460b8 은 bc0b7a08 의 조상 (merge-base = 32460b8)
```

로컬 브랜치가 promoted main 보다 **뒤처진 지점을 같은 이름으로 가리키고 있다.** 어떤 평면이든 `git rev-parse research/landing-accessibility-main` 을 쓰면 `32460b8` 을 얻는다 — A 의 릴리스 문서가 참조하는 `bc0b7a08` 이 아니다. 32460b8 은 A `state.json` 이 `READ_ONLY_HISTORICAL_REGRESSION_ASSET` 으로 기재한 refcohort 자산이다.

**규칙**: promoted main 참조는 `origin/research/landing-accessibility-main` 또는 exact SHA `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` 로만 한다. bare 브랜치명 금지.

이는 `orchestrator-absolute-path-discipline` 과 같은 결함군이다 — 이름이 가리키는 대상이 문맥에 따라 달라진다.

### 5.2 C 브랜치 이름 불일치

08 은 `claude-c/assurance-current @ 1baa865b` 를 기재하나, C 하트비트의 작업 브랜치는 `claude-c/assurance-v21 @ 52df8a6` (base 1baa865b) 이고 원격 `claude-c/assurance-v21` 은 `41fa3b01` 이다. 두 브랜치 모두 실재한다. C 산출을 인용할 때 어느 쪽인지 명시해야 한다.

### 5.3 D 하트비트 자기보고 지연

D 하트비트 `head_sha = 8fafa0a`, 실제 원격 head `cf05035`. cf05035 는 8fafa0a 의 자식이며 v3 내재화 커밋이다. D 는 커밋 직후 하트비트를 갱신하지 않았다. 경미하나 **하트비트 SHA 를 실행 근거로 쓸 수 없다는 사례**다 — 근거는 `git ls-remote` 다.

## 6. 12 diagnostic 구동기 배선 — exact SHA 재확인

`11_PROMPT_A_v3.0` 첫 임무 2 항목. `01041bc2` 에서 재측정했다.

```
양성대조  V2_DIAGNOSTIC 을 포함한 파일 5개 존재
          src/landing_accessibility/engine/firewall.py
          control/pilot/DIAGNOSTIC_PILOT_MANIFEST.json
          tests/fixtures/w1_diagnostic_pilot_manifest_v2.json
          tests/test_w1_guard_wiring.py
          tests/test_w1_v2_diagnostic_scope.py

측정      scripts/ 아래 V2_DIAGNOSTIC = 0 건
          run_e001_real.py 의 E001_FULL / load_e001_full_* 하드코딩 = 11 개소
          (L2,19,57,58,92,117,122,123,127,147,148,164)
```

양성대조가 발화한 상태에서 얻은 0 이다. **T-B-BLK-008 은 여전히 열려 있다** — scope 는 RELEASED 이나 소비하는 caller 가 0 이다. 08 의 blocker 기술은 정확하다.

`T-A-BLK-008-DECIDE-AND-PAUSE` 에서 A 가 이미 선택한 (ii) 신규 전용 구동기 — hardcoded scope, scope 인자 없음 — 는 v3 07 Phase V3-1 과 충돌하지 않는다.

## 7. 티켓 스키마 전환

141 티켓을 15 스키마로 검사했다.

| v3 필수필드 | 결손 |
|---|---|
| `created_at_kst` | 139/141 |
| `status` | 136/141 |
| `scope` | 112/141 |
| `base_sha` | 31/141 |
| `claim_kind` | 5/141 |
| `priority` | 3/141 |

v3 enum 밖 `type` 34건 / 14종:
`WORK_REQUEST`(13) `RESEARCH_FINDING`(6) `VALIDITY_RISK_CANDIDATE`(4) `GO_NO_GO`(2) 그리고 `FINAL_READY` `P0_RELEASED` `FACTUAL_CORRECTION` `ADDENDUM` `MART_READY` `STATS_READY` `E001_RELEASE` `RESEARCH_QUESTION` `SUPERSEDE` `HARD_STOP_CANDIDATE` 각 1.

B 와 D 가 각각 독립적으로 같은 결론에 도달했다: **소급 개정하지 않는다.** A 는 이를 승인한다. 발행된 티켓은 발행 시점의 기록이며, 사후 수정하면 그 시점에 무엇이 알려져 있었는지가 소멸한다. §8 결정 D3A-03 에 매핑표를 둔다.

## 8. 이 기록이 하지 않는 것

- v3 의 연구설계 타당성을 판정하지 않는다. 50 candidate frame 의 적절성, F1~F5 의 matched 성립 여부, endpoint contract 의 관측가능성은 **precheck 이전에는 판정 근거가 없다.**
- 새 REAL scope 를 발행하지 않는다.
- B/C/D 에 새 작업을 지시하지 않는다. Director 가 피벗 지침을 예고했고 대기를 지시했다.
