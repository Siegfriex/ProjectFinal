# RQ-E-1 — dismiss detector `icon_only` ablation → Axis B activation pool 회복량

| | |
|---|---|
| plane | D (independent research sandbox) |
| authority | **NON_CANONICAL** |
| claim_kind | ANALYSIS |
| verdict | **PARTIALLY_SUPPORTED** |
| hypothesis_id | H-E1-RECOVERY (경쟁가설 3개 병기 판정) |
| code SHA read | `2281c853950d0c475c5d2c1678680b971c2804f4` (읽기 전용, 실행 안 함) |
| MLflow run | `2ae10cc3be9840e7a20c9fbc4ae23569` (parent `27d10a01df5442b681ee73062e01c123`) |
| superseded run | `e87a3ff50e4c40ed80b772e3d67d0e28` — HARM 규칙 정의 결함 시정 전 판본 |
| seed | 20260828 |
| 결과 JSON | `results/RQ_E1_icononly_ablation.json` |
| 노트북 | `notebooks/d_research/RQ_E1_icononly_ablation.ipynb` (Restart→Run All 에러 0) |

> **GO/NO_GO 아님. threshold 아님. 수정 권고 아님.** icon_only 를 끌지 말지는 A 의 construct 권한이다.
> 이 문서는 회복량과 회복분의 성질만 보고한다.
> **인과 주장 없음** — 코드를 고쳐 재수집한 것이 아니라 frozen probe flag 로 filter 를 재계산한 **반사실**이다.

---

## 0. 먼저: 내 주가설이 어디서 틀렸는지

주가설 `H-E1-RECOVERY`(회복이 크다)는 **pool grain 에서 맞았다**. 그러나 같은 증거가
`H-E1-IRRELEVANT`(회복이 결과에 도달하지 않는다)도 **동시에 참**으로 만든다.
두 가설은 배타적이지 않고, 실제로 둘 다 참이다. 그래서 전체 verdict 를 SUPPORTED 가 아니라
**PARTIALLY_SUPPORTED** 로 낮췄다.

또한 `H-E1-HARM` 을 검정하려고 처음 세운 규칙군에 **내 쪽 정의 결함이 두 건** 있었다.
아래 §4 에 수정 내역을 그대로 싣는다. 첫 판본은 MLflow 에서 SUPERSEDED 로 표시했다.

---

## 1. 무엇을 어떻게 쟀나

### 기전 (exact SHA 코드 독해)

```
l0_probe.js:384-390   containers = dialog ∪ [role=dialog] ∪ [role=alertdialog] ∪ [aria-modal=true]
                                 ∪ {position:fixed|sticky} ∪ {z-index >= 100}
l0_probe.js:392-393   controls  = button, [role=button], a[href], [role=link], form[method=dialog] button
l0_probe.js:394       name      = aria-label || title || textContent
l0_probe.js:400       matches_close_vocabulary = CLOSE_WORDS.test(name) || CLOSE_GLYPH.test(name)
l0_probe.js:402       icon_only = !textContent && (aria-label || 자식 img/svg 존재)
l0_probe.js:409       .filter(x => x.matches_close_vocabulary || x.icon_only)   ← ablation 대상
l1_engine.py:346-350  dismiss_selectors = { ctrl.selector }  (컨테이너 전부 flatten, hittable 무관)
l1_engine.py:351-357  activation 후보 = hittable ∧ selector 존재 ∧ selector ∉ dismiss_selectors
```

`l1_engine` 이 만드는 것은 **selector 문자열의 set** 이다. 따라서 같은 selector 가 여러 컨테이너에서
나오면 flag 를 OR 로 합친 것과 동치다 — 이 분석은 그 grain(=`dismiss_selector`)을 정본으로 삼았다.
(PILOT-E 는 selector 당 첫 entry 만 봤다. 제거후보 57 중 6개가 복수 entry 를 갖지만 결과는 일치했다.)

### 반사실

`filter(x => x.matches_close_vocabulary || x.icon_only)` → `filter(x => x.matches_close_vocabulary)`.
정의상 `P_base ⊆ P_abl` 이므로 이 ablation 은 pool 을 줄일 수 없다(단조). 코드가 이를 점검한다 — 통과.

### 분모 (섞지 않는다)

| grain | n | 무엇 |
|---|---|---|
| target | 54 | in_mart==1 ∧ probe 보유 (기대 56, probe 부재 2) |
| hittable pac | 854 | Axis B activation pool 의 분모 |
| removed hittable pac | 57 | baseline 에서 dismiss set 에 걸려 빠진 후보 |
| recovered | 35 | icon_only 가 **유일한** 제거근거였던 후보 |
| dismiss selector (target×selector) | 395 | Axis C 쪽 반대급부의 분모 |

---

## 2. 중복 근거 분해 — `H-E1-NULL` 직접 검정

제거된 57개(hittable pac grain)의 3분할:

| 셀 | n / 57 | Wilson95 |
|---|---|---|
| `icon_only` 만 | **35** (0.614) | 0.484 – 0.729 |
| `close_vocabulary` 만 | 17 (0.298) | 0.194 – 0.430 |
| **둘 다** (중복 근거) | **5** (0.088) | 0.038 – 0.190 |
| (참고) `close_vocabulary` 를 가진 것 전체 | 22 (0.386) | 0.270 – 0.517 |
| (참고) `icon_only` 가 걸린 것 전체 | 40 (0.702) | 0.573 – 0.804 |

`close_vocabulary` 를 가진 후보는 22/57 로 PILOT-E 보고치와 일치하고, `icon_only` 단독 35 도 일치한다.
PILOT-E 의 "icon_only 35 vs close_vocabulary 22" 는 상호배타 우선순위 표기였고, 3분할하면
**중복 근거는 5개뿐**이다.

→ **`H-E1-NULL` REFUTED.** "대부분 close_vocabulary 로도 잡히므로 회복이 미미하다" 는 데이터에서 지지되지 않는다.

---

## 3. 회복량 — `H-E1-RECOVERY`

### candidate grain

| 항목 | 분자/분모 | 비율 | Wilson95 |
|---|---|---|---|
| baseline 제거 | 57 / 854 hittable pac | 0.0667 | 0.0519 – 0.0855 |
| ablation 후 제거 | 22 / 854 hittable pac | 0.0258 | 0.0171 – 0.0387 |
| **회복 (제거분 기준)** | **35 / 57 removed** | **0.614** | **0.484 – 0.729** |
| 회복 (hittable 전체 기준) | 35 / 854 hittable pac | 0.0410 | 0.0296 – 0.0565 |

pool 총량 797 → 832 (**+4.39%**, grain=hittable pac).

### target grain

| 항목 | 분자/분모 | 비율 |
|---|---|---|
| 회복이 하나라도 있는 target | 22 / 54 target | 0.407 |
| pool 이 빈 target (baseline) | **5 / 54 target** | 0.093 |
| pool 이 빈 target (ablation) | **0 / 54 target** | 0.000 |
| 비었다가 안 비게 되는 target | **5 / 5** | 1.000 |

**단, 이 5 target 은 애초에 `n_hittable` 이 2~3 이었다.** "빈 pool 이 전부 회복된다" 는
그 페이지들이 원래 hittable 후보가 거의 없었다는 사실과 함께 읽어야 한다.

| wtg | hittable | removed | pool_base | recovered | pool_abl |
|---|---|---|---|---|---|
| e7bb158c1c8d9fe7 | 2 | 2 | 0 | 1 | 1 |
| 190b4501e4415d5e | 2 | 2 | 0 | 1 | 1 |
| b728911c9782edb8 | 2 | 2 | 0 | 1 | 1 |
| 0ee385d0c964e560 | 3 | 3 | 0 | 2 | 2 |
| 35319a420294ee17 | 2 | 2 | 0 | 2 | 2 |

→ **`H-E1-RECOVERY` SUPPORTED** (pool grain 한정).

### Axis C 쪽 반대급부 (크기만 보고, 정오 판단 없음)

dismiss selector 395 → 165 (**−230, 0.582** 축소; Wilson95 0.533 – 0.630, grain=target×selector).
baseline 에 dismiss selector 가 있던 51 target 중 **9 (0.176)** 은 dismiss 집합이 완전히 빈다.
어느 쪽이 옳은지는 Axis C gold 없이 정해지지 않으며, 그 판단은 A 의 권한이다.

---

## 4. `H-E1-HARM` — 회복분이 진짜 닫기 control 인가

gold label 이 없다. 규칙 기반 **보수적 상한**을 7개 세우고, 느슨해질수록 상한이 커지도록 설계해
**방향이 규칙 전반에서 유지되는지**를 봤다.

판정규칙(사전 고정): 임계 0.5("다수"). `min(all) > 0.5` → SUPPORTED. `max(R1..R6) < 0.5` → NOT_SUPPORTED.
그 사이 → INCONCLUSIVE. R7 은 의도적 과대계상이라 NOT_SUPPORTED 판정에서 제외하되 수치는 병기한다.

| 규칙 | 정의 | n/35 | 상한 | Wilson95 |
|---|---|---|---|---|
| R1 | 의미적 dialog 컨테이너 ∧ href 없음 ∧ 이름 전무 ∧ ≤2500px² | 0 | **0.000** | 0.000 – 0.099 |
| R2 | href 없음 ∧ 이름 전무 ∧ ≤2500px² | 2 | 0.057 | 0.016 – 0.185 |
| R3 | href 없음 ∧ 명백한 비-닫기 어휘 아님 | 5 | 0.143 | 0.063 – 0.291 |
| R4 | href 없음 | 13 | 0.371 | 0.232 – 0.537 |
| R5 | 확장 닫기 사전 적중 | 0 | **0.000** | 0.000 – 0.099 |
| R6 | href 없음 ∨ 비-내비게이션 href(`#`/`javascript:`) | 17 | 0.486 | 0.331 – 0.643 |
| R7 | R1~R6 ∪ href 가 사이트 루트(`/`) — **의도적 과대계상** | 22 | 0.629 | 0.463 – 0.768 |

- 최댓값(R7 제외) **0.486 < 0.5** → **`H-E1-HARM` NOT_SUPPORTED**.
- 확장 닫기 사전 적중이 **0/35**. probe 정규식이 좁아서 놓친 닫기 표현은 회복분에 하나도 없다.
- 반대로 명백한 비-닫기 기능어휘(메뉴/검색/홈/로고/앱/슬라이드…) 적중이 **11/35 (0.314)**.
- 회복분 중 **1/35** 만이 의미적 dialog(`<dialog>`/`role=dialog`/`aria-modal`) 컨테이너 소속이다.

### 규칙군 수정 고지 (숨기지 않는다)

1차 계산 뒤 규칙군을 한 번 고쳤다.

- **(a)** 최초 R1 은 컨테이너 판정에 `modal_overlay_candidates` 소속을 썼는데, 그 목록의 후보조건
  (`l0_probe.js:195-199` fixed/sticky/z≥100)이 dismiss 컨테이너 스캔조건(`l0_probe.js:386-390`)과
  **사실상 같아서 판별력이 0** 이었다 — 회복분 **35/35** 가 전부 "오버레이 안"으로 잡혔다.
  그래서 R1 을 `candidate_sources ∈ {dialog_element, role_dialog, aria_modal}` 인
  **의미적 dialog** 로 좁혔다. (이 자체가 부수 발견이다: 두 스캔이 같은 휴리스틱을 쓰므로
  "오버레이 안에 있다" 는 이 파이프라인에서 거의 항상 참이다.)
- **(b)** 최초 R4(`non_navigating`)는 `href="/"` 를 비-내비게이션에 포함시켜 로고·홈 링크를
  "닫기일 수 있음"으로 계상했고 상한을 0.629 까지 부풀렸다. 닫기 control 은 홈으로 이동하지 않으므로
  이는 정의 결함이다. 사이트 루트를 분리하고, 부풀린 판본은 **R7 로 남겨 병기**했다.

### 사람이 재판정할 표본

35개 **전량**을 `RQ_E1_icononly_ablation.json` 의 `recovered_sample` 에 실었다 (요청 20개 이상).
이름이 있는 것들: `home` · `메뉴` · `메뉴 열기` · `슬라이드 2` · `Google Chrome Homepage` ·
`gnb열기` · `YouTube 홈` · `YouTube 검색` · `Google 앱` · `당근` · `THE HYUNDAI SEOUL` · `검색` ·
`음소거 해제` · `AI 챗봇 헤이디`. 나머지 19개는 이름이 없고 대부분 외부 도메인/프로모션으로 가는
배너 앵커다. 유일하게 애매한 부류는 **이름 없고 href 없는 작은 icon button 2개**(R2)다.

---

## 5. `H-E1-IRRELEVANT` — 회복이 결과에 도달하는가

frozen mart `fact_task_entry.json` (n=31 task row):

| 지표 | non-null |
|---|---|
| NED | **0 / 31** |
| IED | **0 / 31** |
| MPFED | **0 / 31** |
| endpoint_reached > 0 | **0 / 31** |

→ **`H-E1-IRRELEVANT` SUPPORTED.** pool 이 797→832 로 늘어도 현 mart 의 Axis B 산출값은 전부 결측이며,
회복이 산출값을 바꾸는지 이 증거로는 확인 **불가능**하다. 회복량은 **탐색공간 크기까지만** 말한다.

---

## 6. 통계검정 (BH-FDR, family=5)

회복분의 **성질 기술**이며 회복량의 유의성 검정이 아니다 — 35/57 은 표집오차가 아니라 결정적 재계산이다.
`p<0.05` 를 발견으로 포장하지 않는다.

| test | 내용 | p_raw | p_BH | q<0.05 |
|---|---|---|---|---|
| T1 | href 보유율: 회복분 22/35 vs 잔여제거분 5/22 | 0.0059 | 0.0146 | yes |
| T2 | href 보유율: 회복분 22/35 vs 생존 pool 633/797 | 0.0320 | 0.0533 | no |
| T3 | 이름 slot 전무: 회복분 22/35 vs 생존 pool 100/797 | <1e-6 | <1e-6 | yes |
| T4 | 면적 분포 (Mann-Whitney, 중앙값 2304 vs 5226) | 0.1898 | 0.2373 | no |
| T5 | 의미적 dialog 소속: 회복분 1/35 vs 잔여제거분 3/22 | 0.2875 | 0.2875 | no |

읽는 법: T3 이 가장 강하다 — 회복분은 **이름이 없는 요소**라는 점에서 생존 pool 과 크게 다르다.
이것은 `icon_only` 의 정의(`!textContent`)가 곧 이름 부재를 뜻하므로 **동어반복에 가깝다**.
발견으로 취급하지 않는다.

---

## 7. 반례 (가설에 불리한 관측 먼저)

- **against H-E1-RECOVERY** — pool 이 회복돼도 Axis B 산출은 여전히 전부 결측이다(NED/IED/MPFED 0/31).
  회복이 결과를 바꾼다는 증거는 이 문서에 **없다**.
- **against H-E1-RECOVERY** — 회복이 "빈 pool 을 5/5 되살린다" 는 문장의 그 5 target 은
  hittable 후보가 원래 2~3개뿐인 페이지다. 회복의 절대량은 target 당 1~2개다.
- **against H-E1-HARM** — 회복분의 22/35 가 href 를 갖고, 그중 다수가 외부 도메인이나
  사이트 루트로 가는 로고·홈·배너 링크다. 닫기 control 은 외부 도메인으로 네비게이션하지 않는다.
- **against H-E1-NULL** — 두 조건이 함께 걸린 후보는 5개뿐이다. 중복 근거 가정이 데이터에서 지지되지 않는다.
- **분석 자체에 대한 반례** — 회복분 판정에 쓴 특징(name/href/box)은 probe 가 dismiss 판정에 쓰는
  것과 **같은 slot** 이다. HARM 상한은 probe 와 독립적이지 않다.

---

## 8. 가장 무거운 limitation

**반사실 재계산이라 1-state 정적 pool 까지만 말한다.** `icon_only` 를 실제로 끄면 Axis B 가
그 후보들을 눌러 화면이 바뀌고, 다음 state 의 `primary_action_candidates` 집합 자체가 달라진다.
그 2차 효과는 이 증거로 전혀 잡히지 않는다. "회복량 35" 는 **첫 state 에서 후보 목록에 다시 오르는 수**이지
"Axis B 가 실제로 35만큼 더 깊이 간다" 가 아니다.

그 다음으로 무거운 것: **'진짜 닫기인가' 의 gold 가 없다.** HARM 상한은 규칙 기반이며
probe 와 같은 slot 을 읽으므로 독립 검증이 아니다. n=35 로 CI 도 넓다.

---

## 9. 이 RQ 가 답하지 않는 것

- `icon_only` 를 실제로 끄고 재수집했을 때 NED/IED/MPFED 가 달라지는가 — 현 mart 에서 셋 다 0/31 이라 **불가능**.
- 회복분이 '진짜 닫기' 인지의 gold 판정 — D 는 label 을 만들지 않는다.
- `icon_only` 를 끔으로써 Axis C 의 `dismiss_control_exists` 가 과소가 되는 정오 — Axis C gold 없이는 정해지지 않는다.
- 1-state 를 넘어선 경로 전개에서의 누적 회복량 — 재수집 없이는 계산되지 않는다.
- `icon_only` 대신 다른 완화(컨테이너를 dialog 로 한정 등)를 썼을 때의 회복량 — 이 RQ 는 단일 항만 껐다.

## 10. 파생 연구질문

- **RQ-E-1a** dismiss 컨테이너 집합을 `l0_probe.js:386-390` 의 fixed/sticky/z≥100 에서
  dialog/aria-modal 로 좁히면 회복량은 `icon_only` ablation 대비 얼마인가 (재수집 불필요).
  §4 의 "컨테이너 판별력 0" 관측이 이 RQ 를 직접 가리킨다.
- **RQ-E-1b** 회복된 35개를 Axis B 가 실제로 활성화했을 때 state 가 전진하는가 — **재수집 필요, D 범위 밖**.
- **RQ-E-1c** `icon_only` 를 끌 때 `dismiss_control_exists` 가 1→0 으로 뒤집히는 9 target 이
  실제로 modal overlay 를 갖고 있는가.
- **RQ-E-2** dismiss detector 의 name 소스가 비어 있는 control 비율과 `icon_only` 발동의 중첩.

---

## 방화벽

`D_INPUT_ALLOWLIST.json` 의 denied 목록을 **하나도 열지 않았다**. 네트워크 접속 없음.
gold label 생산 없음. 기존 A~E 산출물 · production · engine · mart · raw evidence 수정 없음 —
새 파일만 썼다. 코드는 `git show <sha>:<path>` 로 읽기만 했고 실행하지 않았다.
`holdout_accessed` 는 self-report 가 아니라 `tools/d_input_firewall.py` 스캔 결과에서 채워졌다(`false`).
