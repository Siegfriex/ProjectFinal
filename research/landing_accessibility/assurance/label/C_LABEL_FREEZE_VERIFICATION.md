# C_LABEL_FREEZE_VERIFICATION — LABELS_FROZEN @ control 5b826e3a61

**producer** C · labels_produced 0 · 감사 시각 21:28 KST · holdout 은 C 만 열람(HOLDOUT_FOR_C)

## §1 동결 무결성 — MATCH
| 검사 | 결과 |
|---|---|
| sha256 재계산 LABELS_FROZEN / CALIBRATION_FOR_B / HOLDOUT_FOR_C | f373004b… / 140619ae… / 69a28427… — REPORT·meta·RELEASE_HASHES 와 전건 일치 |
| 순서 split(6612a08 21:09:01) → RAW L1/L3/L4(d8f8595 21:22:00) → L2+freeze(5b826e3 21:26:25) | 역순 없음 ✓ |
| 56 = split 56 = mart 56; 중복 0 | ✓ |
| CALIBRATION_FOR_B ids ⊂ calibration(30), HOLDOUT_FOR_C ids = holdout(26), 교집합 0 | ✓ — B 파일에 holdout 누출 0 |
| frozen 행 내용 = RAW 행 (archetype/evidence_ref/decision_trace/confidence) | diff 0; 동결 시 추가된 키 = `split` 뿐 |
| detector calibration 착수 전 동결 | B W2 커밋 0 (`claude-b/w2-rf-detector` = 2281c85) ✓ |

## §2 L2 (holdout 15) provenance
rows=partition ✓ · 어휘 ✓ · 금지입력 0 · evidence 출처 dom/ax/probe · **decision_trace 빈 행 3** (wtg_517b8047·e296af22·e7bb158c, 전부 AMBIGUOUS — 근거는 `unresolved_reason` 에 있음). T-A-LABEL-001 per_row_required 위반 형식상 3건, 실질 0 (P3, 수정 아닌 기록).

## §3 관측 archetype × split (C 재계산, A §2 표와 일치)
COMMUNICATION_ENTRY calibration **0** / holdout 1 · UTILITY calibration 1 / holdout 4 · AMBIGUOUS 8/6. prior 로 층화한 split 이 관측 archetype 기준으로는 불균형 — holdout_scorer 는 per-archetype n 을 병기하며 n<5 archetype 의 agreement 를 gate 에 쓰지 않는다(D-R0-49).
prior 일치 22/42 (0.524) — A 의 21/42 와 1 차이: C 는 CSV frozen CANDIDATE 행 기준 prior, A 는 frame prior. 어느 표를 prior 로 쓰는지 명시 필요(P3).

## §4 F-A3 · D-A-후보-5/6 에 대한 C 판단
- **inter-labeler agreement 없이 label 로 frame 오류율을 주장하지 않는다 — 동의(핵심).** 자연 복제 1건(NH 쌍) 0/1 불일치, 원인 = evidence slot 차이(dom/ax vs probe visible_text). C-BLOCKER-211259 의 remedy(겹침 16건 이중라벨)가 그대로 답이며, **이중라벨 지시문에 "읽을 slot 집합" 을 고정**해야 slot 차이가 agreement 를 오염시키지 않는다.
- D-A-후보-5(W2 는 probe 렌더후 신호 포함, 읽은 slot 기록) **동의**. 단 slot 을 늘리면 marker 경로(D-R0-42)와 같은 위양성 통로가 생길 수 있으므로 probe 의 `region_signals/endpoint_signals` 중 marker 계열은 REAL_TARGET 에서 여전히 disabled.
- D-A-후보-6(slot 시점 불일치를 evidence 품질 지표로) **동의**. 구현 제안: 관측단위 플래그 `dom_body_empty`, `probe_primary_action_n`, `slot_disagreement`.

## §5 T-B-FINDING-002 (probe 하드 cap) — C 독립 재계산
| 신호 | cap | C n==cap /58 | B |
|---|---|---|---|
| accessible_name_sources | 300 | 13 | 13 ✓ |
| primary_action_candidates | 200 | **8** | 7 (1 차이 — B 재확인 요) |
| target_size | 300 | 6 | 6 ✓ |
| contrast | 400 | **8** (정확히 400) | "max 400 의심" → 확정 |
cap-hit 관측 15 target: prior ITEM_DETAIL 11/15 (73%) vs 전체 25/58 (43%) → **대형 커머스 편향 확인**(B 의 미검정 가설을 C 가 기술통계로 확인, 검정은 하지 않음). labeled 기준 ITEM_DETAIL 8/15.
C 판단: (1) cap 도달 플래그를 관측단위로 mart 에 기록 — 동의 (2) 절단 관측의 Axis A/C 판정은 **해당 criterion/지표만** UNDETERMINED 후보로 낮추고 관측 전체를 낮추지 않는다 — criterion 별 evidence slot 이 cap 영향권인지 W3 manifest 의 evidence_source 로 결정 (3) 재수집은 A GO 사안 — 동의.

## §6 확인하지 않은 것
라벨 정확성(gold 의 gold 없음) · 절단이 실제 판정을 바꿨는지(W3/W4 이후) · D 브랜치 산출(승격 전 비감사)
