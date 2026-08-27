# R0 — DIRECTOR CENTRAL RECONCILIATION

**ID** `LA-R0-DIRECTOR-2.1` · **권한** Research Director (최종 의사결정권자)
**A 반영** 2026-08-27T21:06:12+09:00 (`date` 판독값) · **assertion_type** `DECISION`
**supersedes** `D-R0-15` (부분) · **amends** `R0_RECOVERY_CONTRACT_v2.1.md`, `R0_GO_DECISION.md`

---

## §0 Director 지정 heads 재확인 — OBSERVATION

Director 가 지정한 5개를 `git ls-remote` 로 21:05 KST 재확인했다.

| ref | Director 지정 | 21:05 실측 | 판정 |
|---|---|---|---|
| `control/landing-orchestrator` | `606b0b36…` | `606b0b36ba9c2978afb453873e960c4088036923` | 일치 |
| `claude-c/assurance-v21` | `77d4b50e…` | `77d4b50e8ac2734ee867b086726da93a371e7744` | 일치 |
| `claude-b/measurement-recovery` (integration base) | `2281c853…` | `2281c853950d0c475c5d2c1678680b971c2804f4` | 일치 |
| `research/landing-accessibility-main` | `bc0b7a087…` | `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` | 일치 |
| `claude-b/clean0-v21` | `d5edbefc…` | **`f52367e224661fd0a82193f0f404b2ba4946b14f`** | **전진함** |

**`claude-b/clean0-v21` 은 Director 관측 이후 다시 전진했다.** B 가 활발히 push 중이다.
acceptance 는 branch 가 아니라 **exact SHA** 로 한다 — 현재 accepted B SHA 는 여전히
`4ae6df0a` (C 가 검증한 그 SHA) 이며, `f52367e` 는 **미검증**이다.

### D4 계보 실측 — 선언이 아니라 확인

```
2281c85  IS descendant of  bc0b7a0     ← authority parent 가 이미 계보에 포함돼 있다
d5edbefc IS descendant of  2281c85
```

따라서 `recovery branch = 2281c85 의 descendant` + `authority parent = bc0b7a0` 은
**주장이 아니라 merge-base 로 확인된 사실**이다. provenance 기록은 이 실측을 인용한다.

---

## §1 Director 결정 반영표

| | Director 결정 | A 계약과의 관계 | 조치 |
|---|---|---|---|
| **D1** | R0_GO 발행, REAL_TARGET NO-GO 유지 | `T-A-R0-GO-001` 과 **동일** | 유지 |
| **D2** | duplicate launch 정정, exactly-once 를 W1 의 REAL_TARGET blocking acceptance criterion 으로 승격 | `D-R0-35` 와 **동일**, 다만 "blocking acceptance criterion" 지위를 명시 | **D-R0-38** 로 지위 승격 |
| **D3** | bus 로컬 유지 + plane별 mirror, **ACK/COMPLETION/HEARTBEAT namespace 분리** | `D-R0-30` 과 동일하나 **namespace 분리는 신규** | **D-R0-39** |
| **D4** | integration base = 2281c85, provenance 에 authority parent bc0b7a0 기록 | `D-R0-36` 과 **동일** + provenance 요구 신규 | **D-R0-40** |
| **D5** | frozen 59 유지 · **RF-DT Branch U 를 UTILITY_ENTRY 의 frozen operational definition 으로 채택** | `D-R0-34` 가 남긴 공백을 **Director 가 닫음** | **D-R0-41** |
| **D6** | marker 경로 **삭제하지 않음**. FIXTURE 전용, REAL_TARGET 에서 disabled | `D-R0-15`("제거 또는 비활성화")를 **좁힌다** | **D-R0-42 · D-R0-15 SUPERSEDED** |
| **D7** | W3 착수 전 KWCAG criterion manifest 추출·freeze | **신규 선행 게이트** | **D-R0-43** |
| **D8** | Labeler 4~6 즉시 배치, n=56, calibration/holdout 사전 동결 | `D-R0-26/27/28` 과 동일 + **즉시 배치** | 유지 + 실행 |
| **D9** | W1~W4 즉시 병렬. **W1+W2 는 한 gate 에서 함께 통과, 중간 REAL_TARGET 재수집 금지** | `D-R0-18` 과 동일 | 유지 |
| **D10** | **CLEAN loop 종료.** C0 또는 결과를 바꾸는 C1 만 blocking, 나머지는 backlog | **신규 운영 규율** | **D-R0-44** |

---

## D-R0-38 — exactly-once 의 지위 (D2)

```
지위    W1 의 REAL_TARGET blocking acceptance criterion
        (권고사항 아님 · 이월 불가 · W1 완료 판정의 구성요소)
근거    가설이 아니라 2026-08-27 05:14 w02 에서 실제 발생한 사건 (C_CLEAN0_AUDIT §6.1)
canonical ledger  "w02 duplicate launch 4건"
superseded        B "retry 분기" · A "superseded retry" — 둘 다 철회됨
```

억제는 **launch 이전**에 일어나야 한다. batch 원장 exclusive-create 의 사후 차단은
exactly-once 가 아니다 — 실사이트 접속이 이미 끝난 뒤다.

## D-R0-39 — bus mirror namespace 분리 (D3)

```
<plane>/bus_mirror_<x>/tickets/      DIRECTIVE · WORK_REQUEST · GO_NO_GO · FACT_CORRECTION · BLOCKER
<plane>/bus_mirror_<x>/acks/         ACK
<plane>/bus_mirror_<x>/completions/  COMPLETION
<plane>/bus_mirror_<x>/heartbeat/    HEARTBEAT (최신 1개 덮어쓰기)
```

A 는 본 커밋에서 기존 flat mirror 를 이 구조로 재배치한다.
B(`handoff/bus_mirror_b/`) · C(`assurance/bus_mirror_c/`) 도 동일 구조를 적용한다.

**이유**: flat 이면 ACK 와 원본 티켓이 같은 목록에 섞여 "무엇이 요청이고 무엇이 응답인지"가
파일명 규칙에만 의존한다. §16 투명성은 디렉터리 구조로 보장하는 편이 안전하다.

## D-R0-40 — integration base provenance (D4)

```
recovery implementation base   2281c853950d0c475c5d2c1678680b971c2804f4   [FROZEN]
authority parent               bc0b7a087faf2328cbafdfa9b40bd426c5080d7d
관계                           2281c85 IS descendant of bc0b7a0  (merge-base 실측)
```

**W1~W4 worktree 는 전부 `2281c85` 의 descendant 로 만든다.**
각 worker 의 completion ticket 과 산출 문서 provenance 에 두 SHA 를 **모두** 기록한다.

`bc0b7a08` 은 연구 authority 이지만 production `engine`/`e001_runner` 를 포함하지 않는다
(C 실측: bc0b7a08 = 0 파일, 2281c85 = 16 파일). **authority 와 code base 는 다른 축이다.**

## D-R0-41 — UTILITY_ENTRY frozen operational definition (D5)

`D-R0-34` 가 열어둔 공백 — CSV 의 UTILITY_ENTRY 6행 `region_signal_type = CODEBOOK_PENDING` —
을 Director 가 닫는다.

```
frozen operational definition = RF-DT v2.1 Branch U
  Region    function surface entry control
  Endpoint  function surface 가 열리고 primary control 이 present/actionable
  금지      도구별 완료작업 수행
```

**서비스 outcome 을 보고 서비스별 새 정의를 만드는 것은 금지된다.** 6행 전체가 동일한
Branch U 정의를 공유한다. 이것은 정의의 **발명이 아니라 이미 frozen 인 DT 의 적용**이다.

해결되지 않는 개별 사례는 `AMBIGUOUS_UNRESOLVED` 로 남긴다. force-map 금지는 유효하다.

## D-R0-42 — fixture marker (D6) · `D-R0-15` SUPERSEDED

```
[data-region] / [data-endpoint] 코드 경로    삭제하지 않는다
FIXTURE 실행                                 허용
REAL_TARGET 실행                             반드시 disabled
actual detector 가 쓰는 것                   URL_PATTERN · DOM_AX_ROLE · FORM_STRUCTURE
                                             + DT / NLP fallback
```

**`D-R0-15` 의 "제거 또는 비활성화" 를 "삭제 금지 + 실행 모드별 게이팅" 으로 대체한다.**

Director 판단이 A 의 초안보다 낫다 — marker 경로를 삭제하면 **기존 fixture 회귀 스위트가
같이 죽는다.** 필요한 것은 코드 제거가 아니라 **실행 모드에 따른 차단**이다.

C 가 확인한 위양성 조건(`data-region` = `'sg'`,`'ko_KR'` / `data-endpoint` = `'1'`,`'2'`)은
그대로 유효하며, 이제 **REAL_TARGET 모드 disable 로 차단**된다.

```
검증 요구  REAL_TARGET 모드에서 marker 경로가 호출되지 않음을 테스트로 증명한다
          (음성 대조: marker 를 심은 실사이트 유사 fixture 를 REAL_TARGET 모드로 돌려
           detector 가 그것을 읽지 않는지 확인)
```

## D-R0-43 — KWCAG criterion manifest 선행 freeze (D7)

**W3 착수 전 선행 게이트다.** 기존 SSOT / A1 / A2 에서 older-relevant **measurable** subset 을
exact criterion manifest 로 추출한다.

```
필수 필드   criterion_id · applicability · evidence_source · automation_grade · SHA
금지        새 criterion 생성 · 고령자 임의 threshold 생성 · subset 확대
출처        기존 control/OLDER_RELEVANT_KWCAG_SUBSET.md 및 A1/A2 — 새로 만들지 않는다
```

manifest freeze 이전에는 W3 evaluator 구현을 시작하지 않는다.

## D-R0-44 — CLEAN loop 종료 (D10)

```
critical path 에 넣지 않는다   새 broad audit · governance hardening · adjacent issue discovery
blocking 자격                  C0, 또는 현재 결과를 바꾸는 C1 만
그 외 전부                     backlog
```

**A 에게 적용되는 구속이기도 하다.** A 는 이후 새 governance 산출물을 만들지 않고
LABEL_FROZEN 과 W1~W4 완료 판정에만 집중한다.

---

## §2 다음 milestone

```
LABEL_FROZEN
W1~W4 IMPLEMENTATION_COMPLETE_CANDIDATE
```

## §3 REAL_TARGET_GO 조건 — 전건 충족 전 금지

```
1  W1 + W2 joint offline PASS      (한 gate · 중간 재수집 없음)
2  W3 criterion QA PASS
3  W4 mart compatibility PASS
4  C same-SHA assurance PASS
5  A explicit GO
```
