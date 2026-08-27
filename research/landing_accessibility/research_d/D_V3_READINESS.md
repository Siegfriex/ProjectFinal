# D — SSOT v3.0 내재화 및 준비 상태

작성 2026-08-28 · D HEAD `8fafa0a` · 브랜치 `claude-d/research-sandbox-v21`
**SSOT**: `/home/sieg/projects-wsl/ProjectFinal/SSOTV3` — 유일 SSOT. v2.1/SSOTV2 는 §12 supersession 범위에서 대체된다.

## 0. 무결성 독립 검증

`MANIFEST_v3.0.json` 의 20개 파일을 sha256 과 byte 길이로 재계산했다 — **불일치 0**.
`08_CURRENT_STATE_BASELINE` 이 기록한 6개 plane SHA 도 전부 로컬에 실재하는 commit 이다.

## 1. D 의 v3 정체 (14_PROMPT_D · 06 §1)

Independent **Measurement** Research Sandbox. v2.1 의 "DS/ML Research Sandbox" 에서 이름이 바뀌었고 대상이 바뀌었다.

> v3 의 연구대상은 **classifier accuracy 가 아니라 Cross-Service Task Entry Flow 측정의 타당성**이다.

우선 연구 8개: spatial dispersion 조작화 · visible label vs accessible name 변이 ·
icon-only/control-type/reveal-direction taxonomy · action sequence normalization 과 edit distance sensitivity ·
Depth 와 sequence divergence 의 비동일성 · auth-gate stage variation · task-specific obstruction · missingness/slot dependency.

금지(v2.1 과 동일): production 수정 · REAL target 독자 실행 · **task gold 생성/변경** · GO/NO-GO · holdout 접근.
라우팅: `to=C, cc=A` 기본. A 가 명시 요청한 경우만 예외 (v3 §4 가 v2.1 의 무조건 C 경유보다 한 칸 완화됐다 — 그래도 기본은 C).

## 2. 연구 construct 전환

| | v2.1 | v3.0 |
|---|---|---|
| primary construct | Representative Function → Depth | **Cross-Service Task Entry Flow Divergence** |
| task 결정 | 화면에서 추론 (RF 7-way classifier) | **수집 전 동결** (Task Contract) |
| raw primary | NED/IED/MPFED | **ordered Action Sequence** (Depth 는 derived) |
| 본표본 | 59 | **50 = 5 families × 10 services** (candidate, precheck+freeze 필요) |
| 59 의 지위 | 본연구 분모 | USAGE_BENCHMARK / ROBUSTNESS_CORPUS |
| 12 의 지위 | 진단 파일럿 | METHOD_QUALIFICATION_SET (효과크기 표본 아님) |
| 7 archetype | sampling quota | legacy metadata / codebook |
| 해석 | — | STFP = **다축 profile, 단일 합산점수 금지** |

## 3. D 의 기존 산출 재배치

**감사 이력으로 보존 (v3 §Legacy closeout 명시)**: RF001-A/B/C · RF-002-A~F · RQ-D15 · D-FACT-01.
이것들은 "왜 RF auto-classification 을 main critical path 에서 내렸는가" 의 근거다. **폐기 아님, 신규 queue 아님.**

**v3 primary 로 직접 승계되는 것** — 이미 v3 codebook 변수와 1:1 대응한다:

| D 산출 | v3 대응 |
|---|---|
| PILOT-E slot 공유 행렬 (E-P1~P5) | `04` 변수 간 slot 의존 · `03 §9` task-specific obstruction |
| RQ-E-1 icon_only ablation | `entry_label_modality` 의 `ICON_ONLY_AX_NAMED` vs `ICON_ONLY_UNNAMED` 분리 |
| RQ-D13a overlay coverage 반증 | `D3-12` — max coverage 대신 `task_control_occlusion` primary |
| RQ-D6b/6b-1 셀렉터 비대칭 | `03 §4` task-specific candidate binding |
| RQ-D7 분모 사슬 (미완) | `05 §6` denominator chain 단계별 보고 |
| html_decode / 코퍼스 v3 | `visible_label_text` 인코딩 정합성의 전제 |

**퇴역**: 신규 classifier 개선, prior_agreement 기반 실험, archetype 예측.

## 4. 버스 티켓 상호 비교 — v3 스키마 대조 결과

D 가 발행한 16건을 `15_TICKET_PROTOCOL_SCHEMA_v3.0.json` 으로 검사했다.

- **required 필드 누락**: `scope` 16/16 · `status` 16/16 · `created_at_kst` 16/16 · `base_sha` 15/16
  (v2.1 은 `created_at` 를 썼고 `scope`/`status` 개념이 없었다)
- **type enum 위반 11건**: `RESEARCH_FINDING` 6 · `VALIDITY_RISK_CANDIDATE` 4 · `ADDENDUM` 1
  → v3 enum 에는 이 셋이 없다. 대응: 전부 **`FINDING`** 으로 접는다. `ATTESTATION`/`HOLD-EVIDENCE`/`FACT_CORRECTION` 중
  `FACT_CORRECTION` 만 v3 enum 에 남아 있다.
- **claim_kind**: v2.1 의 `DECISION`/`PROJECTION`/`DEFINITION` 이 v3 에서 `AUTHORITY`/`ASSURANCE`/`PROPOSAL` 로 교체됐다.
  D 가 쓰던 `OBSERVATION`/`ANALYSIS`/`IMPLEMENTATION` 은 그대로 유효하다.

**기존 티켓은 소급 수정하지 않는다.** v2.1 계약 하에서 발행된 것이고, 고쳐 쓰면 발행 시점의 기록이 사라진다.
v3 채택 이후 발행분부터 새 스키마를 쓴다.

## 5. v3 프로토콜이 D 의 결함을 그대로 규칙으로 채택했다

`06 §5 Git` 은 D 가 이 세션에 낸 결함 세 건을 문장 그대로 담고 있다:

- "worker 실행 중 `git add -A` 금지. 확정 파일만 명시 stage" → **D-DEF-08**
- "완결 게이트: top-level verdict/result + FINDINGS/manifest 존재 후 commit" → **D-DEF-07**
- "commit 직후 `git show --stat` 으로 message 와 포함파일 대조" → **D-DEF-08 의 검출 절차**
- "history rewrite 로 결함 은폐 금지; superseding finding 으로 시정" → **D 불변성 규율**

D_PROTOCOL_SNAPSHOT.md 의 §11·§12 와 충돌 없이 일치한다. **방법론은 그대로 승계된다.**

## 6. heartbeat 규약 변경 (v3 §7)

3분 주기 · 필수 8항목. D heartbeat 에 4개가 없어 추가했다:
`worktree` · `artifact` · `next_gate` · `decision_needed`. 주기도 300초 → 180초.
미지정 값은 빈 문자열이 아니라 `NONE` 을 기록한다 — 빈 값과 "없음" 을 구분하지 않으면 그것 역시
빈 결과가 통과처럼 보이는 사례가 된다 (D-DEF-09 계열).

## 7. 검증된 델타 — 08 baseline 이 D HEAD 를 낡게 기록하고 있다

`08_CURRENT_STATE_BASELINE` 은 D 를 `bcaa634` (D-DEF-08) 로 적었다. 실제 D HEAD 는 **`8fafa0a`** 이며 그 사이 4 커밋이 있다:
`36824c7`(워커 재개) · `3d7a547`(정지 지시) · `bf0831e`(프로토콜 스냅샷) · `8fafa0a`(**D-DEF-09**).

특히 **D-DEF-09 는 baseline 작성 이후에 발견됐다** — D 버스 스캐너가 pretty-print 된 `to` 필드를 못 읽어
P0 4건·P1 4건 포함 14건을 놓치고 있었다. 시정 완료, 현재 미ACK 0.

다른 5개 plane SHA 는 전부 실재 확인. baseline 은 "기준선이지 release document 가 아니다" 라고 스스로 밝히므로
이 델타는 결함이 아니라 **갱신 필요 사항**이다. C 로 라우팅한다.

## 8. D 가 v3 에서 지금 하지 않는 것

`00 §13` 이 명시한다 — v3 pack 자체는 새 REAL 실행권한을 주지 않는다. 현재 허가된 REAL 은 `V2_DIAGNOSTIC` 12 뿐이다.
`T-A-PIVOT-PRESERVE-001` 의 constraint 도 유효하다: **대상이 정해지기 전 새 조작화·게이트 수치·archetype 을 만들지 않는다.**

따라서 D 는 다음을 **하지 않는다**: 50 candidate 에 대한 어떤 접속도 · 새 flow 지표 조작화 확정 ·
A 의 v3 역할 티켓 분배 전 자체 판단으로 연구 착수.

**대기 중**: A 의 v3 역할 티켓 (`11_PROMPT_A` 첫 임무 4 — "B/C/D 에 v3 역할을 티켓으로 분배").
