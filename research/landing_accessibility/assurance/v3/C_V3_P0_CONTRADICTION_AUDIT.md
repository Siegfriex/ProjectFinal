# C V3 P0 — METHODOLOGY_PRESERVED §1~§8 ↔ SSOTV3 모순 독립감사

**C / claude-c/assurance-v21 · 2026-08-28 02:2x KST · claim_kind ASSURANCE · 티켓 T-A-V3-P0-C-001 task 1**
대상: `control/method/METHODOLOGY_PRESERVED.md` @`5c22faeb`(286행) · `SSOTV3/` 원본(MANIFEST 20/20 MATCH, 무수정) · 대조는 A 의 `V3_ADOPTION_RECORD.md §3` 표를 **참조하지 않고** C 가 v3 원문을 직접 읽어 작성. 방법: 각 항목에 v3 exact 조항을 지목하거나 "대응 없음" 을 명시. **대응 없음 ≠ 폐기** — v3 00 §12 는 v2.1 중 정확히 3개 해석만 폐기 대상으로 지정하고 방법론(C 독립 assurance·Scout→Freeze→Replay 등)을 승계 목록에 두므로, v3 에 대응 조항이 없는 방법론 항목은 METHODOLOGY_PRESERVED(A T4 결정) 로 계속 구속력을 갖는다.

## 판정: **CONFIRMED — 폐기 0 · 완화(재해석) 1 · 대응 없음 7**

## 1. §1~§8 대조

| METHODOLOGY_PRESERVED | v3 대응 조항(exact) | 판정 |
|---|---|---|
| §1 plane 분리 A/B/C/D, B self-approve 금지, C production 미수정, D 는 C replication 경유로만 승격 | 06 §1 역할 4종; 06 §4 "D→C, cc A"; 14 "Finding은 to=C, cc=A 를 기본"; 06 §1 D "non-canonical, production 수정 금지" | 승계 |
| §1 "**A 가 D 를 직접 읽지 않는다**" | 06 §4 "D가 A로 직접 canonical conclusion을 우회 전달하지 않음 **(A explicit request 예외)**"; 15 `x_v3_routing_notes.D_FINDING` "…unless A explicitly requested direct delivery" | **완화(재해석)** — METHODOLOGY 에 없는 예외가 v3 에 있다. 폐기는 아니나 §1 의 근거("오염 방지")와 긴장. A 결정 필요: 예외를 유지하면 "A explicit request" 의 기록 형식(티켓 id·사유)을 사전 규정할 것 |
| §2 진실 위계 T1~T6, "A 의 권위는 T4" | 06 §2 "1 exact bytes/runtime/evidence · 2 independently reproducible computation · 3 frozen task/target/schema/codebook · 4 accepted SSOT/decision · 5 prose · 6 agent narrative" | 승계 — 6단계 문면 일치 |
| §3 규율1 0건=대조군 필요 | 대응 없음 (07 V3-6 실패주입 목록이 음성대조 역할을 일부 담당) | 대응 없음 — METHODOLOGY 로 구속 |
| §3 규율2 비율은 n·구간 | 05 §4 "n=10 denominator 고정 · median/IQR/range"; 05 §1·13 "pairwise 45 ≠ n=45" | 부분 승계 (구간 요구는 명시 없음) |
| §3 규율3 귀속은 분리측정 후 | 05 §5 "사전 정의만 허용" (감도분석) | 부분 승계 |
| §3 규율4 composition 은 diff | 06 §5 "commit 직후 git show --stat 으로 message와 포함파일 대조"; 06 §8 "코드가 있다가 완료가 아니다 — exact SHA + 실행결과 + artifact" | 승계 |
| §3 규율5 제거 확인 | 대응 없음 | 대응 없음 — METHODOLOGY 로 구속 |
| §4 게이트 사전 확정·결과 후 재정의 금지 | 00 §9 금지 "결과를 본 뒤 target 교체/endpoint 변경"; 07 Stop "task contract change after evidence observation"; 01 §1 "결과를 본 뒤 unfavorable 제외 금지" | 승계·강화 |
| §4 A GO 3정합(B completion·C PASS·authority) | 06 §8 완결 요건; (Director Master Directive §0 — pack 밖) | 승계 |
| §4 PASS 문서 "검증하지 않은 것" 절 | 06 §8 "claim boundary + known limitation 필요" | 승계 |
| §4 조건부 HOLD 사전 선언 | 07 Stop Conditions 목록 | 부분 승계 |
| §5 presence≠operative 카탈로그 | 00 §6 "generic login 존재 이유로 중단하지 않는다"; 03 §9 "geometry overlap만으로 modal 확정 금지"; 04 `entry_label_modality` ICON_ONLY_AX_NAMED/UNNAMED 분리; 00 §8 visible/accessible 분리 | 승계 — v3 설계 동기 자체 |
| §5 양방향 대조군 | 07 V3-6 실패주입(wrong task_id·hash mismatch·outside-manifest·app-only…) | 부분 승계 (양성 방향 명시 없음) |
| §5 측정실패→PASS/FAIL 전이 금지 | 05 §5 "evidence defect는 structural failure로 재분류하지 않는다"; 03 §5 "REPLAY_BROKEN — 자유탐색 대체 금지"; 04 endpoint_status EVIDENCE_DEFECT 별도 값; 00 §7 "MPFED 불능 NULL" | 승계 |
| §6 exactly-once launch 이전·오프라인 증명 | 06 §6 "frozen manifest hash + release document + allowlist + final navigation guard · outside-manifest 0 · 새 run id · overwrite 금지" | 승계 ("launch 이전"·"오프라인 증명" 문구는 없음 → METHODOLOGY 로 구속) |
| §6 방어 겹·fail-closed·승인 바인딩 | 06 §6 4겹; 01 §5 "manifest_sha256 mismatch면 REAL 거부"; 15 routing REAL 조건 | 승계 |
| §6 자기선언 발신자 ≠ 인증 | 대응 없음 | 대응 없음 — METHODOLOGY 로 구속 |
| §6 소유 경계 (한 파일 두 worker 금지) | 06 §5 "git add -A 금지, 확정 파일만 stage" | 부분 승계 |
| §6 검산은 읽기 (타 워크트리 git 상태 불변) | 대응 없음 | 대응 없음 — METHODOLOGY 로 구속 |
| §7 사전등록 (분모·상한·결측·감도) | 00 §5; 05 §5 "사전 정의만"; 05 §6 분모 체인 단계별 보고; 07 V3-4 freeze 후 교체=새 version | 승계·강화 |
| §8 재현 가능한 표본 | 01 §1 replacement 는 collection 전 + 재freeze; 01 §5 freeze contract(hash) | 승계 |
| §8 root set·필터·조인 키 명시 | 대응 없음 | 대응 없음 |
| §8 Git 밖 산출물 해시 | 06 §5 "manifest 존재 후 commit"; 03 §10 manifest SHA | 부분 승계 |
| §8 결과 덮어쓰기 금지·새 run | 02 §8 "재수집은 새 run, 재판정은 새 judgment version"; 06 §6 | 승계 |

## 2. 음성대조 — §0 "보존하지 않는다" 항목이 v3 에서 실제로 강등·대체됐는가

| 항목 | v3 실측 | main critical path 잔존? |
|---|---|---|
| 7 archetype (sampling quota) | 00 §1.5 "sampling quota가 아니라 legacy metadata/codebook"; `archetype` 언급 파일 3개(00·02·09)뿐; registry 의 `legacy_archetype` 열은 metadata. 50 frame 의 distinct legacy archetype = **4**(UTILITY 20·FIN 10·ITEM 10·PLACE 10) — A REFREEZE §6 와 C 재계산 일치 | 아니오 |
| MPFED/NED/IED primary | 00 §7 "Depth는 파생"; 02 §4 "legacy compatibility"; 05 §2F "optional legacy" | 아니오 (derived only) |
| OverlayCoverage | 02 §5 `overlay_coverage` 보조, `task_control_occlusion` primary; 09 D3-12 | 아니오 |
| 59 frame | 00 §10 USAGE_BENCHMARK/ROBUSTNESS; 07 legacy closeout "E001_FULL SUSPENDED" | 아니오 |
| W1~W4 범위 | 07 V3-5·12 "W1 guard·W3 KWCAG·W4 obstruction 자산 최대 재사용" — W2 는 제외(07 "삭제하지 않되 필수 dependency 제거") | 자산 재사용만, acceptance 범위로는 잔존 없음 |
| 0.85 / 0.75 | v3 21 파일 grep `0.85|0.75|agreement` **0건** | 아니오 |
| KWCAG criterion set | 00 §3 Axis A 독립축 존치 — §0 가 "보존하지 않는다" 로 분류한 것과 달리 v3 는 대상을 **유지**했다. 모순이 아니라 "대상 특정 항목은 새 대상의 것으로 채운다" 규칙이 '유지' 로 채워진 사례 | Axis A 로 잔존(의도) |
| RF classifier | 02 §1 "대표기능 classifier는 v3 main lineage에 없다"; 07 V3-5 "RF 7-way inference bypass"; 07 Stop "silent fallback to RF classifier" | 아니오 |

A 의 supersession 판정(폐기 0)은 **C 독립 재검토에서도 유지된다.**

## 3. 이 감사가 검증하지 않은 것
- v3 연구설계 타당성(50 frame 의 matched 성립, endpoint 관측가능성) — precheck 이전 근거 없음.
- Director Master Directive 원문(pack 밖)과 pack 의 정합 — A 접수기록만 존재하며 C 는 원문을 받지 않았다.
- `THREE_TURN_RUNBOOK.md`(02:11:06 SSOTV3 에 추가, MANIFEST 미기재) 의 권위 지위 — pack audit 참조.
