# E Pathfinder — P0 Bootstrap

**plane**: E · **role**: PATHFINDER / DATA_RECONNAISSANCE_OPERATOR
**branch**: `claude-e/pathfinder-v3` (base `control/landing-orchestrator` @ `2e826a5`, A 소유 — read-only 참조, 직접 write 안 함)
**worktree**: `.agent_worktrees/claude_e_pathfinder`
**authority_status**: `AUXILIARY_EXECUTION_EVIDENCE` · **canonical**: `false` · **self_approved**: `false`
**phase**: `P0` — bootstrap / OFFLINE only (LA-ORCH-3E §12)

## 이 디렉터리가 하는 일

SSOTV3(`/home/sieg/projects-wsl/ProjectFinal/SSOTV3`, 절대경로 고정)를 코드로 파싱해
50 target route-work manifest·task/endpoint 해시 인벤토리·action-token 호환성 점검·
evidence checklist·offline schema rehearsal·target별 subagent dispatch packet을 만든다.

**하지 않는 일**: 어떤 target 도 실제로 열지 않는다. task/endpoint/family 를 바꾸지 않는다.
mobile_web_eligibility 를 판정하지 않는다(REAL precheck 필요, P0 범위 밖).

## bootstrap/ 파일 지도

| 파일 | 내용 |
|---|---|
| `build_manifest.py` | SSOTV3 CSV/XLSX/candidate JSON 파싱 + 교차검증 QA + family/target 해시 계산 |
| `ROUTE_WORK_MANIFEST.json` | 50 target 작업 매니페스트 (target_id 순서 고정, scout_status=NOT_STARTED) |
| `TASK_CONTRACT_INVENTORY.json` | family별 해시 계보 + 해시 산출 방식 명세 + fixture_override target 목록 |
| `PARSE_QA_REPORT.json` | CSV/XLSX/JSON 3원 교차검증 결과 |
| `build_worker_packets.py` / `WORKER_DISPATCH_PACKETS.json` | target별 self-contained subagent dispatch packet (REAL 인가 필드는 비어 있음) |
| `build_synthetic_example.py` / `synthetic_example/` | 가짜 데이터로 trace/route-candidate 스키마 완결성 리허설 (F1-03, 네트워크 접근 없음) |
| `ACTION_TOKEN_COMPATIBILITY_CHECK.md` | v3 18-token codebook vs 기존 collector(`l1_engine.py`/`vocabulary.py`) 격차 분석 |
| `EVIDENCE_CHECKLIST_TEMPLATE.md` | target별 필수 evidence 체크리스트 |
| `OFFLINE_REHEARSAL_REPORT.md` | 스키마 리허설 결과 + 범위 밖으로 남긴 것 |
| `FINDINGS.md` | P0 중 발견한 이상 징후 (A/C 보고용) |

## 다음 게이트

A 가 `SCOUT_REQUEST`(LA-ORCH-3E §4 스키마, `real_target_allowed=true` + manifest/authority/release 필드
완전 일치)를 발행할 때까지 REAL 접속 금지. 발행되면 `WORKER_DISPATCH_PACKETS.json`에서 해당
target_id packet 을 꺼내 `real_authorization` 블록을 채운 뒤 병렬 dispatch.
