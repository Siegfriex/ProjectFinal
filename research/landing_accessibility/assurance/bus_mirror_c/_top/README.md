# AGENT BUS — landing_v2

**이 디렉터리는 research authority 가 아니다. orchestration transport 다.**

canonical authority 는 언제나 **git artifacts / SHA** 다. 버스의 어떤 파일도
연구 사실을 확정하지 않는다. 버스와 git 이 어긋나면 **git 이 옳고**, 버스 파일이 결함이다.

`.gitignore` 에 등재돼 있어 커밋되지 않는다 — 의도된 것이다. 세션 간 전송 수단일 뿐이다.

## 평면

| | 역할 | 세션 |
|---|---|---|
| **A** | Authority — 결정·게이트·수용 | `projectfinal-64` (Claude A) |
| **B** | Production — 수집·판정·mart·분석 실행 | `projectfinal-55` (Claude B) |
| **C** | Independent Assurance — evidence/data/stats 검증 | (A 가 필요 시 기동) |

**A decides · B produces · C independently verifies · A accepts.**

## 디렉터리

```
tickets/       발행된 ticket (immutable — 수정 금지)
acks/          수신 확인
completions/   완료 보고
heartbeats/    생존 신호 (A.json · B.json · C.json)
escalations/   SLA 위반·차단 사유
event_log.jsonl  append-only 이벤트 흐름
```

## ticket 규약

- 파일명 `tickets/<ticket_id>.json`, **immutable**. 고칠 일이 생기면 새 ticket 을 낸다.
- ACK 는 `acks/<ticket_id>.<actor>.json`, 완료는 `completions/<ticket_id>.<actor>.json`.
- `idempotency_key` 가 같은 ticket 은 같은 작업이다 — 중복 수행하지 않는다.
- ticket 생성 직후 해당 세션에 **direct message** 도 보낸다 (fast wake-up + durable payload 이중신호).

## 역할 경계 (A0 §7·§8)

**A 만 할 수 있는 것** — main promotion · gate close · P0_RELEASE · E000 acceptance ·
E001 release · GLOBAL HARD STOP · mart acceptance · statistical claim acceptance · final integration.

**A 가 하지 않는 것** — collector / mart / stats / plot / ML 구현.

**C 가 하지 않는 것** — security exploit hunting · promotion mutation test ·
new governance hardening · collector 구현 · canonical write.
**C 를 새 P0 adversarial auditor 로 만들지 않는다.** C 는 evidence/data/stats verifier 다.

## SLA

- GATE ticket ACK <= 60s. 없으면 direct re-message 1회.
- heartbeat 가 2~3분 이상 stale 이면 actor unavailable 로 취급.
- **C unavailable 이 E000 assurance 의 single point of failure 가 되지 않는다** —
  C timeout 시 A 가 minimal acceptance checklist 를 fallback 수행한다.
- **B unavailable 은 production blocker** — 즉시 Research Director 에게 escalation.
- 어떤 ticket 도 무기한 대기하지 않는다: retry once → fallback / isolate / escalate.
  작업 가능한 다른 lane 은 계속 진행한다.
