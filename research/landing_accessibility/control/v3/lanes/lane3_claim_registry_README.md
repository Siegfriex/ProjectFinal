# Lane 3 Claim Registry — 사용법

**대상 파일**: `lane3_claim_registry_skeleton.json`
**지위**: STEP 3 전용 빈 틀. 결과 없이 작성됨. `claim_text` 는 전부 `null` — 채우는 순간이 STEP 3 실제 판정 시점이다.

## 1. 이 registry 가 존재하는 이유

결과가 나오기 전에 "무엇이 채워져야 승인되는가"를 고정해 둔다. 결과를 본 뒤 slot 구조나 denominator 정의를 바꾸면, 그 순간부터 이 registry 는 결과의존 서술을 방어할 수 없다. 그래서 slot 신설/denominator 변경/축 재정의는 STEP 3 진입 이후 원칙적으로 금지하며, 예외가 필요하면 §5 를 따른다.

## 2. STEP 3 승인 절차 (slot 당)

1. B 가 산출한 값과 evidence artifact 를 `evidence_refs` 에 실제 경로/hash 로 채운다 (`status: PENDING_PRODUCTION_BY_B` → 실제 artifact 경로).
2. C 가 `independent_recompute` 에 적힌 절차대로 동일 raw 에서 독립 재계산한다. B 값과 C 값이 다르면 그 자체를 기록하고 승인 보류(`SLOT_EMPTY` 유지).
3. B/C 값이 일치하면 A 가 `claim_text` 를 채운다. 이때 문장은 반드시:
   - `denominator` 에 명시된 chain 단계(§4 참조)를 문장 안에 노출한다 (예: "family n=10 중 evidence-bearing n=9 에서…").
   - `scope_limit` 을 넘지 않는다.
   - `forbidden_upgrade` 에 나열된 표현을 쓰지 않는다.
4. A 는 `status` 를 `SLOT_EMPTY` → `SLOT_FILLED_PENDING_C` → `SLOT_APPROVED` 순으로만 전진시킨다. 역행(승인 취소)은 가능하지만 단계를 건너뛰는 승격은 불가.
5. 반려 시 사유를 `claim_text` 옆에 새 필드 `rejection_note` 로 남기고 `status` 는 `SLOT_EMPTY` 로 되돌린다. slot 자체를 삭제하지 않는다 — append-only.

## 3. 유형 간 승격 금지 (claim_type)

`DEFINITION / IMPLEMENTATION / OBSERVATION / ANALYSIS / DECISION / PROJECTION` 중 하나로 slot 생성 시 고정된다.

- `ANALYSIS` slot(8개 axis + family-level + cross-family)이 결과를 보니 더 강하게 쓰고 싶어져 `PROJECTION`(해석)으로 바뀌는 것 금지.
- `PROJECTION` 은 이 registry 에서 `CLAIM-STFP-PROFILE` 단 하나에만 허용된다 — SSOT §11 이 STFP 를 "secondary interpretation" 으로 명시적으로 지정했기 때문이다. 다른 slot 이 STFP 언어(구조적 재학습 요구, transfer friction)를 빌려 쓰려면 별도 STFP slot 을 통해서만 가능하다.
- 유형을 바꿔야 한다고 판단되면 기존 slot 은 폐기(`status: SLOT_RETIRED`, 사유 기록)하고 새 `claim_id` 로 새 slot 을 연다. 기존 slot 의 `claim_type` 을 in-place 로 고치지 않는다.

## 4. 분모 사슬 검증 절차

모든 claim 은 승인 전에 다음 5단계 중 정확히 어느 단계가 분모인지 명시해야 한다:

```
candidate_10 → eligible_frozen_10 → attempted_10 → evidence_bearing_n → flow_evaluable_n
```

검증자(A)는:
1. 문장에 등장하는 n 이 `denominator.stage` 와 일치하는지 확인한다.
2. family 당 독립 n 은 10(또는 그 이하로 줄어든 실측 n)이며, **service-pair 45 는 절대 독립 표본 n 이 아니다** — E(Flow Topology), B(Spatial) slot 에 이 함정이 forbidden_upgrade 로 이미 박혀 있다.
3. cross-family 비교가 5개 family 를 pooling 해 n=50 으로 취급하지 않았는지 확인한다.
4. `evidence_bearing_n` 과 `flow_evaluable_n` 이 다르면(즉 일부 target 이 초기 상태까지만 도달하고 완주하지 못함) 그 차이를 `CLAIM-LIMITATIONS-MISSINGNESS` slot 과 상호 참조해 설명이 존재하는지 확인한다. 설명 없이 갭을 넘기면 반려.

## 5. slot 신설/수정이 필요할 때

원칙적으로 STEP 3 진입 후 slot 추가 금지(사전등록 규율, METHOD_PRESERVED §7). 불가피한 경우:

- 새 측정변수/새 임계값/새 archetype 을 근거로 한 slot 신설은 **항상 금지** — 04 codebook 밖의 정의는 이 registry 에 들어올 수 없다.
- 04/05 안에 이미 있었으나 이 skeleton 이 놓친 항목을 뒤늦게 추가하는 것은 허용하되, 반드시 "결과를 보기 전에 발견했다"는 타임스탬프 증거(커밋 시각, 결과 산출 시각 비교)를 남긴다. 결과를 본 뒤 발견했다면 그 slot 은 `ANALYSIS` 이상으로 쓸 수 없고 `PROJECTION`/강한 해석 문구를 붙일 수 없다.

## 6. 요약

12 slot: axis A~H(8) + STFP profile(1) + family-level 기술통계(1) + cross-family 비교(1) + 결측/분모 사슬 보고(1). 전부 `claim_text: null`, `status: SLOT_EMPTY`.
