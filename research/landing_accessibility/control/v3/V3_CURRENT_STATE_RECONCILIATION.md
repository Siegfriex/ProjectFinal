# V3_CURRENT_STATE_RECONCILIATION

발행 A · 2026-08-28T02:07 KST · base `5c22faebaeb6699049fc9af5646f8b492b6a4068`
근거 Director "ProjectFinal V3 — Director Orchestration Master Directive" + "DIRECTOR → A : V3 START INJECTION"
측정 방법 `git ls-remote origin` — **하트비트 자기보고가 아니다**

---

## 1. Exact heads — Director 표 대 origin 실측

| plane | branch | Director 기재 | origin 실측 | 판정 |
|---|---|---|---|---|
| A | `control/landing-orchestrator` | `5c22faeb…` | `5c22faebaeb6699049fc9af5646f8b492b6a4068` | 일치 |
| B | `claude-b/diag-pilot-integration` | `01041bc2…` | `01041bc213a2e61f6cb224e469087d9a11324349` | 일치 |
| C | `claude-c/assurance-v21` | `52df8a64…` | `807192bcf5cb9591e3a82bd86bef5338bd719be3` | **불일치 — C 가 2 커밋 앞섬** |
| D | `claude-d/research-sandbox-v21` | `8fafa0a4…` | `cf05035cc14a2f1a3ddcaff61c805aa6e9cafb19` | **불일치 — D 가 1 커밋 앞섬** |
| promoted main | `research/landing-accessibility-main` | `bc0b7a08…` | `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` | 일치 (**로컬 ref 위험, §3**) |
| pilot manifest | `control/pilot-manifest` | `54a0c7a4…` | `54a0c7a4149adc17c086e398be83bc7c117a66b0` | 일치 |

### 불일치는 오류가 아니라 진행이다 — 계보 검증

```
C  52df8a6 → 41fa3b0 → 807192b        52df8a6 은 807192b 의 조상 (YES)
   52df8a6  V2_DIAGNOSTIC 3방향 PASS @01041bc + 음성대조 2종
   41fa3b0  bus emit 에 v3 티켓 스키마 필수필드 추가
   807192b  미ACK 8건 지연 ACK + FC-011·V3-FINDING-001 ACK 미러

D  8fafa0a → cf05035                  8fafa0a 은 cf05035 의 조상 (YES)
   cf05035  SSOTV3 내재화 — 정체·construct 전환·티켓 스키마 대조·heartbeat 규약
```

**rewrite 없음. 두 평면 모두 fast-forward 다.** Director 표는 각 평면의 하트비트 자기보고 시점(01:5x)에서 채취됐고, 그 뒤 C·D 가 v3 내재화를 커밋·push 했다. 표가 틀린 것이 아니라 5~10분 뒤처졌다.

**규칙**: 이 사례는 `08_CURRENT_STATE_BASELINE_v3.0.md` §Installation caution 이 예고한 그대로다. **하트비트 SHA 를 게이트 근거로 쓰지 않는다.** 게이트 판정의 근거는 `git ls-remote` 실측뿐이다.

### 08 Baseline 과의 추가 차이

`08_CURRENT_STATE_BASELINE_v3.0.md` 는 A 를 `8f413527`, D 를 `bcaa634b`, C 를 `claude-c/assurance-current @ 1baa865b` 로 기재한다. 08 은 스스로 "release document 가 아니라 기준선"이라 밝히므로 **결함이 아니라 갱신 대상**이다. 갱신은 v3.0.1 successor 에서 하며 **원본 팩을 덮어쓰지 않는다.**

C 는 두 브랜치가 모두 실재한다: `assurance-current @ 1baa865b`(08 기재) 와 `assurance-v21 @ 807192bc`(실작업). C 산출 인용 시 어느 쪽인지 명시해야 한다.

## 2. SSOTV3 팩 무결성 — 원본 bytes 재해시

| 항목 | 결과 |
|---|---|
| MANIFEST 등재 20 파일 sha256 + byte length | 불일치 **0/20** |
| `MANIFEST_v3.0.json` 자체 sha256 | `1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a` |
| 매니페스트 밖 디스크 파일 | `MANIFEST_v3.0.json` 1건 (자기참조, 정상) |
| 팩 원본 수정 | **0 — A 는 SSOTV3 에 write 하지 않았다.** 재확인 시점에도 20/20 일치 |
| D 독립 재계산 (`D-V3-FINDING-001`) | 0/20 불일치 — A 와 독립 일치 |

두 평면이 서로의 숫자를 받지 않고 각자 계산해 같은 결과에 도달했다. T2 수준이다.

## 3. 로컬 ref 참조 위험 — P1, 즉시 적용

```
refs/heads/research/landing-accessibility-main          = 32460b87   ← 로컬
refs/remotes/origin/research/landing-accessibility-main = bc0b7a08   ← 정본
merge-base(32460b8, bc0b7a08) = 32460b8   → 로컬이 정본의 조상, 즉 뒤처져 있다
```

어떤 평면이든 `git rev-parse research/landing-accessibility-main` 을 쓰면 `32460b8` 을 얻는다. 그것은 A `state.json` 이 `READ_ONLY_HISTORICAL_REGRESSION_ASSET` 으로 기재한 refcohort 자산이지 promoted main 이 아니다.

**규칙 — 전 평면 즉시 적용**: promoted main 은 `origin/research/landing-accessibility-main` 또는 exact SHA `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` 로만 참조한다. bare 브랜치명 금지.

Director Master Directive §0 "Branch name만으로 완료를 선언하지 않는다" 의 구체적 실례다.

## 4. Director 가 지목한 경로의 실재 여부

| 경로 | 상태 |
|---|---|
| `directives/DIRECTOR_TO_A_START.md` | **ABSENT** |
| `00_MASTER_DIRECTIVE.md` | **ABSENT** |
| `phases/P0…P7` | **ABSENT** |
| `SSOTV3/00_MASTER_DIRECTIVE.md` · `SSOTV3/phases` · `SSOTV3/directives` | **ABSENT** |

Director 는 파일 대신 지시문 본문을 직접 주입했다. A 는 **그 본문을 권위 원문으로 접수**하고 `DIRECTOR_V3_MASTER_DIRECTIVE_RECEIVED.md` 에 원문 그대로 기록한다.

A 는 존재하지 않는 파일을 SSOTV3 안에 만들어 채우지 않는다 — 팩은 Director 가 준 candidate bytes 이며, A 가 거기에 쓰면 그 순간 hash 가 깨지고 "무엇이 Director 가 준 것이고 무엇이 A 가 쓴 것인가"가 소멸한다. Phase 계획은 A 의 control 트리에 A 의 산출로 둔다.

## 5. 현재 REAL 권한 — 변동 없음

| scope | 상태 | 근거 |
|---|---|---|
| `E000_FAST` | RELEASED | 기존 |
| `E001_FULL` (59) | **SUSPENDED** | `E001_RELEASE.json` — 유지. v3 는 재개하지 않는다 |
| `V2_DIAGNOSTIC` (12) | RELEASED · `manifest_sha256 78f2e32a…` | `V2_DIAGNOSTIC_RELEASE.json` |
| `V3_MAIN50` | **미발행** | candidate frame. precheck + A freeze 전 REAL 금지 |
| `V3_FLOW_PILOT_10` | **미발행** | P4. P2·P3 종결 전 금지 |

**이 문서는 새 REAL scope 를 한 건도 발행하지 않는다.**

## 6. 구동기 배선 — exact SHA 재측정 @`01041bc2`

```
양성대조  V2_DIAGNOSTIC 포함 파일 5개 실재
          src/landing_accessibility/engine/firewall.py
          control/pilot/DIAGNOSTIC_PILOT_MANIFEST.json
          tests/fixtures/w1_diagnostic_pilot_manifest_v2.json
          tests/test_w1_guard_wiring.py
          tests/test_w1_v2_diagnostic_scope.py

측정      scripts/ 아래 V2_DIAGNOSTIC = 0 건
          run_e001_real.py 의 E001_FULL / load_e001_full_* = 11 개소
          L2 L19 L57 L58 L92 L117 L122 L123 L127 L147 L148 L164
```

양성대조가 발화한 상태에서 얻은 0 이다. `T-B-BLK-008` 은 **열려 있다** — scope 는 RELEASED 이나 소비 caller 가 0 이다.

Director 지시와 A 의 기존 결정이 일치한다: **full59 runner 에 scope switch 를 넣지 않고 dedicated 12-only V2_DIAGNOSTIC caller 를 만든다.** 이는 `T-A-BLK-008-DECIDE-AND-PAUSE` 의 (ii) 와 동일하다.

## 7. 검증하지 않은 것

- v3 연구설계의 타당성 — 50 candidate 의 matched 성립 여부, endpoint contract 의 실제 관측가능성. precheck 이전에는 판정 근거가 없다.
- C·D 가 커밋한 v3 내재화 내용의 정확성 — SHA 계보만 확인했고 내용은 읽지 않았다.
- B `claude-b/clean0-v21 @ 1aa18c66` 의 상태 — B 하트비트가 현재 작업 브랜치로 보고하나 Director 표에 없다. P0 ACK 에서 B 가 어느 SHA 를 P0 대상으로 지목하는지 확인해야 한다.
