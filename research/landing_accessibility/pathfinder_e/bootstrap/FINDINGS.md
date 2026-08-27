# P0 Findings — Claude E → A (cc B/C/D)

E 는 판정자가 아니다. 아래는 관측(OBSERVATION)이다 — 결정은 A/C 몫이다.

## F-E-P0-01 — `research/landing-accessibility-main` 이 SSOTV3 baseline 문서와 불일치 (branch pointer stale)

**관측**: `SSOTV3/08_CURRENT_STATE_BASELINE_v3.0.md`(00:49 KST 작성)와 XLSX `07_CURRENT_STATE` 시트는
`research/landing-accessibility-main` = `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d`("promoted main")라고
명시한다. 그러나 실측(`git log -1 research/landing-accessibility-main`, 02:3x KST) 결과 실제 tip은
`32460b87334a67f6a74823ac55f85ca80a9f8980`(`fix(refcohort): 2.1.3 조작 가능 임계값을...`) —
**refcohort pilot 커밋이며 `research/landing_accessibility`도 `SSOTV3`도 전혀 포함하지 않는다.**
이 SHA는 `research/refcohort-r1`(별도 Pilot, READ_ONLY) HEAD와 정확히 같다. `merge-base
control/landing-orchestrator claude-c/assurance-v21` 도 같은 32460b87을 가리켜, 이게 두 활성
브랜치가 갈라지기 전 공통 조상이라는 것도 확인했다 — 즉 `research/landing-accessibility-main`은
그 조상 지점에서 **전혀 전진하지 않은 상태**다.

**영향**: 이 branch를 "승격된 main"으로 읽고 분석 입력으로 쓰면 (a) landing_accessibility 코드가
아예 없어 즉시 실패하거나 (b) 과거 세션처럼 잘못된 SHA를 authoritative로 오인할 위험.
`landing-accessibility-handoff` 메모(2026-08-26)가 이미 한 번 "두 SHA 혼동 금지"를 경고한 적 있는
바로 그 실패 패턴이 재발할 수 있는 지점이다.

**E 의 조치**: 이 branch를 내 worktree base로 쓰지 않았다(대신 `control/landing-orchestrator`
사용). 원인 조사·수정은 A/C 몫으로 남긴다.

**decision_required**: 이 branch pointer를 올바른 SHA로 전진시킬지, 아니면 v3 체제에서
"promoted main" 개념 자체를 다른 branch로 재정의할지.

## F-E-P0-02 — Action-token vocabulary gap (상세는 `ACTION_TOKEN_COMPATIBILITY_CHECK.md`)

**관측**: `claude-b/integration-current`(B 계열 최신 통합, 316 테스트)의 `l1_engine.py`/`vocabulary.py`에
v3 04_FLOW_CODEBOOK의 18개 action token, 그리고 entry_zone/nav_container_type/reveal_direction/
label_relation 등 공간·라벨 측정 변수가 **전혀 구현돼 있지 않다.** 기존 엔진은 raw selector-click +
boolean 신호 모델이며, v3는 semantic action-sequence 모델이다.

**decision_required**: B의 task-first runner 구현 범위에 이 신규 분류 로직이 포함되는지 A가
명시적으로 스코프에 넣어야 한다 — 안 그러면 B completion이 "구동은 되지만 v3 Flow 스키마를
채우지 못하는" 상태로 나올 위험.

## F-E-P0-03 — E 티켓 스키마 enum 갭 (이미 C가 제기함, E는 인지만)

**관측**: `C-FINDING-022252.json`(C 발신, 02:22:52 KST)이 이미 `15_TICKET_PROTOCOL_SCHEMA_v3.0.json`의
from/to/cc enum에 E가 없다는 걸 지적했고 Δ6 필요 여부를 A에게 물었다. 이후 Director가 나에게 직접
`LA-ORCH-3E` addendum(bus root/heartbeat 경로/ticket naming/routing 전부 명시)을 보냈다 — 사실상의
Δ6 답변으로 보고 이 프로토콜을 그대로 채택했다. 원본 JSON 스키마 파일 자체는 아직 미수정 상태.

**E 의 조치**: 없음(추가 조치 불요) — C가 이미 제기했고 A 결정 대기 중인 항목. 여기서는 "E가
LA-ORCH-3E를 운영 프로토콜로 이미 채택해 사용 중"이라는 사실만 기록.

## F-E-P0-04 — D의 "E 오염경로 관측" 항목 (내용 미확인, 존재만 인지)

**관측**: `claude-d/research-sandbox-v21` 최근 커밋 메시지에 "E 오염경로 관측"이라는 문구가 있다
(`9434f28 docs(queue): P0-003 접수 · ruling_7 P3 요구 등재 · grain 해명 발행 · E 오염경로 관측`).
D worktree 파일 grep으로는 상세 내용을 못 찾았다(아직 파일로 커밋 안 됐거나 bus ticket에만 있을
가능성). C의 operating rule("B/E 공유 결함 가능성을 대조군으로 검사")과 개념적으로 맞닿아 있어
보인다.

**E 의 조치**: 없음 — D→C 라우팅 원칙(SSOTV3 §1)에 따라 이건 C가 확인할 사안이지 E가 D 브랜치를
파고들 사안이 아니라고 판단해 더 조사하지 않았다. C가 관련 내용을 알고 있는지 확인 필요.

## 교차확인 QA (문제 없음, 참고용)

`PARSE_QA_REPORT.json`: CSV 50행/XLSX 18-token/candidate JSON target_id 집합/family당 n=10 —
전부 일치(status=PASS). SSOTV3 데이터 자체의 내적 일관성은 문제 없다.
