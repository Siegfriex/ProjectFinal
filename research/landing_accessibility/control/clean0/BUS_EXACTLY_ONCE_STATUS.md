# BUS / EXACTLY-ONCE STATUS — CLEAN-0

**ID** `LA-BUS-2.1-20260827T2055` · **assertion_type** `OBSERVATION`

## §1 현 상태

```
bus root            .agent_bus/landing_v2/          (승계 — 프로토콜 §11 이 승계 허용)
tickets/            5
acks/               5
completions/        6
heartbeats/         3   (A 12:44 · B 16:20 · C 17:48)
escalations/        0   (비어 있음 = 미해결 에스컬레이션 없음)
event_log.jsonl     13,077 bytes · 마지막 이벤트 2026-08-27T17:48:03 C SESSION_CLOSE
locks/              **부재**
```

## §2 결함

### BUS-F1 — `locks/` 디렉터리가 없다 · P1

프로토콜 §10 은 real-target 실행에 **target 단위 worker lock** 을 요구한다.
현재 bus 에 `locks/` 가 없다. **이전 duplicate launch 7건의 재발 방지 장치가 물리적으로 부재한다.**

`OBSERVATION` — 지금은 실행 중이 아니므로 즉시 위험은 아니다.
`DECISION` — REAL_TARGET 발사 전에 반드시 존재해야 한다. R0 에서 B 에게 요구한다.

### BUS-F2 — idempotency key 경로 미확인 · P1

> **[정정 · D-R0-35]** 아래 서술은 **틀렸다.** C 가 raw 로 확인한 바 2026-08-27 05:14 w02 에서
> **duplicate launch 가 실제로 일어났다** (worker_02 프로세스 2개, batch_0001 attempts=1 전건,
> run B 가 run A sealed 이전 시작). 실사이트 접속 단위에서는 억제가 없었고 batch 원장
> exclusive-create 가 **사후에** 막았을 뿐이다. **사후 원장 차단은 exactly-once 가 아니다.**
> 원문은 발행 시점 상태로 보존한다.

`ticket_id + run_id + target_id + collector_sha + protocol_sha` 로 구성된 key 가
실제 실행 경로에서 소비되는지 **A 는 확인하지 않았다** (코드 확인은 B/C 의 영역).
`DUPLICATE_SUPPRESSED` 이벤트 타입이 event_log 에 한 번도 나타난 적 없다 —
**억제가 작동한 적 없다는 뜻이 아니라, 억제 경로가 실행된 적 없다는 뜻이다. 둘을 구분한다.**
→ C 에게 exactly-once 감사 티켓 발행.

### BUS-F3 — A heartbeat 이 8시간 stale · P3

`heartbeats/A.json` 마지막 12:44. 이번 세션에서 갱신한다.

### BUS-F4 — bus 가 Git 밖이다 · P2 (정책 충돌)

`.gitignore` 최종행 `.agent_bus/`.
사유는 명시적이다 — *"orchestration transport, not research authority (canonical = git artifacts/SHA)"*.
그러나 프로토콜 §16 투명성 목표(GitHub 만 보고 phase/blocker/ticket 파악)와 충돌한다.
→ `CURRENT_AUTHORITY_MAP §7 ISSUE-A-001` 로 등재. R0 에서 A 가 DECISION.

## §3 지금 하지 않는 것

기존 티켓·completion 을 수정하지 않는다. 정정은 새 `FACT_CORRECTION` / `SUPERSEDE` 로만 한다.
CLEAN-0 을 bus hardening loop 으로 확장하지 않는다 (roadmap §2 Exit 조건).
