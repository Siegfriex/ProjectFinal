# C_LABEL_INDEPENDENCE_AUDIT — T-A-LABEL-001 (label 산출 전 감사)

**target** `control/landing-orchestrator@6612a086ea198913b27c0e339d2a2ce727b4ded3` `control/label/{LABEL_SPLIT_FROZEN.json, PACKET_L1..L4.json}`
**producer** C · labels_produced 0 · production_modified false · 감사 시각 21:12 KST (`date`)

## §1 통과 항목 (C 재계산)
| 검사 | 결과 |
|---|---|
| split 동결 시점 < label 산출 | commit 6612a08 21:09:01 KST; label 산출물 0건(label/* 브랜치 없음) → **선후 OK** |
| calibration / holdout | 30 / 26, overlap 0, 합집합 = mart 56 target 정확히 |
| 층화(prior archetype, 결정적 짝홀) | cal ITEM 13·FIN 6·UTIL 3·QUERY 2·COMM 2·PLACE 2·CONTENT 2 / hold ITEM 13·FIN 4·UTIL 2·QUERY 2·COMM 2·PLACE 2·CONTENT 1 — 균형 |
| labeler 파티션 | L1 16·L2 15·L3 14·L4 11 = 56, 중복 0, 패킷 = 파티션 |
| 패킷 금지입력 | 필드 6종(`web_target_id, observation_id, requested_url, final_url, evidence_dir, evidence_rel`) 뿐. archetype prior 0 hit(대조군: split 문서에서는 hit). detector/mart/MPFED/KWCAG 0 hit — "mart" 문자열 hit 는 emart/lottemart URL(위양성, 문맥 확인) |
| label producer ≠ B/C | A 의 워커 L1~L4 (B/C 브랜치·워크트리에 라벨 산출 없음) |

## §2 결함 — P1 · **labeler 파티션이 split 과 완전 정렬** (교락)

```
          calibration  holdout
L1            16          0
L2             0         15
L3            14          0
L4             0         11
```

labeler 정체성 = split 소속. 함의:
- holdout agreement 는 "L1/L3 라벨로 calibration 된 detector 가 **L2/L4 라벨**과 얼마나 맞는가" 가 된다. 라벨러 간 해석 편차(엄격도·abstain 성향)가 **detector 오차로 위장**되거나 그 반대.
- inter-labeler agreement 를 추정할 겹침이 0 이라 이 교락을 사후에 분리할 수 없다.
- 라벨러가 split 을 모르므로 **누출은 아니다**. 그러나 construct validity 결함이다(holdout 수치가 detector 성능을 재지 않는다).

## §3 요구 (라벨 산출 전이므로 지금 고칠 수 있다)
1. **파티션을 split 과 직교로 재배정** — archetype 정렬 목록을 4 라벨러에 round-robin(각 라벨러가 cal/hold 를 모두 가짐). split 자체는 동결 유지(변경 불필요).
2. 이미 산출이 시작됐다면: 겹침 표본(예: 각 라벨러 4건, 총 16건 이중 라벨)을 추가해 **inter-labeler agreement 를 holdout agreement 의 상한(ceiling)** 으로 병기.
3. 어느 경우든 gate 판정문에 `labeler×split 교차표` 와 `inter-labeler agreement(n)` 을 기재.

## §4 이 감사가 확인하지 않은 것
라벨러 워커의 실제 prompt/입력(패킷 외 컨텍스트) · 라벨러가 evidence_dir 밖 파일(batches/mart)을 열지 않았는가(산출 후 provenance 로 확인) · 라벨 파일 sha256 동결(산출 후) · Human Final ≤5 준수(산출 후).
