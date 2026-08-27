# C PREFLIGHT — DIAG-PILOT-001 (T-A-PILOT-ASSURE-001) @ integration 4bbbc229

**C / Fable · 2026-08-28 00:12 KST · claim_kind OBSERVATION · authority ASSURANCE_RESULT · real_target 접속 0**
대상: control `9a9197ffd6`(manifest/contract) · integration `4bbbc2299f924aceb20203ddc7798cab41b37471`(W1 fed031f5 ⊃ W2 b28aaa5, + W4 35d5c2e) · frame `2281c85` · 모든 실행은 FIXTURE 모드 scratchpad clone.

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| 1 | manifest sha256 독립 재계산 | **MATCH** | `git show 21783ad:…MANIFEST.json`·`9a9197f:…` 둘 다 `4d3209ca…fc2` |
| 2 | sampling 규칙 재현 (seed `LA-DIAG-PILOT-2026-08-27-V2`) | **11/12 MATCH · 1 불일치** | `pilot/preflight_sampling.py` — frame CANDIDATE 59 · order_key 12/12 일치 · quota 합 12 · 7 archetype. 불일치 = CONTENT_OPEN: C 재현은 `wtg_13ed07`(Netflix), manifest 는 `wtg_5beeaf`(TikTok). 원인은 아래 F1 |
| 3 | split membership 미참조 | **VERIFIED_BY_REPRODUCTION (코드 미공개)** | 선정 스크립트가 control 에 없어 코드 검사는 불가. C 가 split 없이 재현해 11/12. 집계: 12 중 holdout26 5 · holdout18 3 · calibration 6 · 미관측 1 — 관측 11 중 holdout 5/11(0.45) ≈ 기저 26/56(0.46). 의존 징후 없음 |
| 4 | gold label(LABELS_FROZEN) 미참조 | **NOT_MET (간접 참조) — F1 P1** | manifest `evidence_class_source` 의 "degenerate 6" 은 관측 규칙으로 재현되지 않는다(C 관측 규칙: 바이트 동일 = 2건). A 의 `FRAME_INTEGRITY_FINDING_A.md` F-A1b 에 따르면 degenerate 목록은 **labeler 의 abstain 판정(L1/L3/L4)** 에서 왔다(netflix·monimo·composecoffee 등). abstain 은 label 기록의 일부다. 따라서 "LABELS_FROZEN 미참조" 는 직접 참조로는 참이나 lineage 로는 거짓이며, 그 결과가 12 중 1건(CONTENT_OPEN)의 선정을 바꿨다 |
| 5 | quota | **MATCH** | 1/1/2/3/2/2/1 = 12 · Director 요건(QUERY/ITEM/PLACE 2/3/2, 7 archetype ≥1, evidence-poor 3 계열 상이) 충족 |
| 6 | exactly-once 하네스 이식 | **READY · 4bbbc22 FIXTURE 경로 실측 PASS** | `w1/dup_launch_harness.py` 2-process 동시 기동: evidence run 3/3 target 각 1회, `DUPLICATE_SUPPRESSED` 1(2번 프로세스 batch 단계 억제, `batches=0 targets=0`), post-hoc block 없음, key = `ticket::run_id::target::collector_sha::protocol_sha` 5성분(batch.py:208-222), attempt_id 기록. 양성대조 = 2281c85 에서 target 당 2 run(`w1/positive_control_2281c85.json`). **최종 integration SHA 에서 재실행 필요** |

## 추가 관측 (Director C 지시 PRE-RUN 2·6)

**F2 (P1, result-affecting for C0 "거래 control 활성화")** — 4bbbc22 에서 `item_detail_purchase_present` 픽스처의 `장바구니` 후보 state = **SAFE** (`바로구매` 만 FORBIDDEN_TRANSACTION). `guard.py` 는 ef7db33→fed031f 사이 변경 0(diff 파일 목록에 없음); `장바구니` 어휘는 W2 `l1_engine.py:214` 에만 있다. B `T-B-PILOT-INT-001` 의 composition 기술 "T-A-W1-P2-DECIDED mask" 는 4bbbc22 에서 **관측되지 않는다**. → A launch gate 2(W1 completion 검산) 미충족 확인. `disabled_inert_controls` 는 후보에서 제거됨(활성화 불가이므로 안전상 비차단), `overlay_blocks_control` 의 가려진 `검색` 은 `DISABLED_OR_INERT`(픽스처 기대 BLOCKED_BY_OVERLAY — 안전 비차단, W1 acceptance 용 메모).

**F3 (B `T-B-BLK-006` 독립 확인)** — `engine/firewall.py` ExecutionScope 는 {E000_FAST, E001_FULL}, `real_target_permitted()` 영구 False, scope 필수·fail-closed(`layer_firewall.py:47`). V2_DIAGNOSTIC scope 부재 → A S1(D-R0-82) 에 동의. C 는 구현 도착 시 **양방향** 테스트(manifest 12 허용 · manifest 밖 target 거부 · manifest sha 변조 시 거부)를 독립 실행한다.

**F4 (기록)** — C 도 Director 로부터 `[C — V2 DIAGNOSTIC PILOT ASSURANCE]` 를 C 세션에서 직접 받았다(HOLD 23:49 이후). 내용은 T-A-PILOT-ASSURE-001 과 일치하며 C 는 A 티켓을 권한 근거로 행동한다. W3 오배송(T-A-FC-002)과 별개다.

## 판정
`PREFLIGHT_PARTIAL` — 1·3·5·6 충족, 2 는 11/12, 4 는 lineage 결함(F1). **launch 전 A 결정 필요**: (i) F1 을 문서화된 caveat 로 수용(pilot 이 detector 를 평가하지 않으므로 label 누출이 gate 로 흐르지 않음 — 단 manifest 의 "gold label 미참조" 문구는 정정) 또는 (ii) degenerate 규칙을 관측 전용(예: 바이트 동일)으로 재정의해 manifest 재동결(Netflix↔TikTok 교체, sha 변경). C 는 어느 쪽도 권고하지 않는다. F2·F3 은 A 가 이미 gate 로 잡은 항목이며 4bbbc22 는 launch 대상 SHA 가 아니다.

## 이 preflight 가 검증하지 않은 것
REAL_TARGET 경로 자체(FIXTURE 만 실행) · W4 probe 의 REAL 모드 동작 · retention manifest(run 이후) · evidence sufficiency(run 이후).

---
## Addendum — manifest v2 재동결 (control `fa6780d902`, 00:14 A 결정 F1_OPTION_II_REFREEZE)
- sha256 독립 재계산 `78f2e32a8fc1e732e485debc41ccdec618a63a832813de83e19a2cf50b51b799` = A 주장 **MATCH**
- sampling 재현(같은 `preflight_sampling.py`, 입력 = frame@2281c85 + mart + dom 바이트 + seed, split/label 미사용): **12/12 MATCH** — order_key 12/12 · selection_trace 7/7 동일 · evidence class 12/12 (POOR 3 = R3 NH스마트뱅킹 · R2 롯데하이마트 · R1 삼성 인터넷 브라우저). CONTENT_OPEN = Netflix `wtg_13ed07`(C 의 v1 재현과 일치)
- 항목 2·4 → **MET**. 항목 1·3·5 유지. 항목 6 은 최종 integration SHA 에서 재실행.
- Netflix 는 `/kr/login` URL — D-R0-03(credential 입력·login submit 금지) 재확인. 로그인 폼 도달은 gate observation.
