# CR-002 — pilot mapping's `mapping_status` values violate the A2 §1.9 state machine

- 제기자: Claude B — P-A-QA (lane `claude-b/pa-qa`, base `agent/landing-pa-shadow` @ `0f46203`)
- 대상: `agent/landing-pa-shadow` @ `0f46203` — `analysis/pilot/pilot_mapping.py` `_finish()`
- 심각도(제안): **P1** — `ANALYSIS_AND_TASK_CODEBOOK_FROZEN` gate가 요구하는
  "abstain 경로 실증"의 evidence 필드 자체가 어휘 권위(A2)와 어긋난다
- 판정 권한: P-A 감사 (adversarial + ssot)

## SSOT 정의 (정본)

`docs/v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md` §1.9 `mapping_status` (`dim_representative_task`):

```
DRAFT               후보 매핑이 생성됐다
CANDIDATE           규칙·source context·embedding으로 후보가 좁혀졌으나 확정 전
FROZEN              00 §6 을 이행해 동결됐다
AMBIGUOUS_UNRESOLVED cascade와 사람 검토 예산으로도 확정하지 못했다
EXCLUDED            대표 task를 정의할 수 없어 L1 대상에서 제외했다

상호배타. 5값은 상호배타이며 DRAFT → CANDIDATE → {FROZEN, AMBIGUOUS_UNRESOLVED, EXCLUDED} 단방향이다.
```

`analysis/codebook/codebook.json`의 `shared_enums.mapping_status.transitions`도 이와 정확히 같은
그래프를 선언한다 (`DRAFT→CANDIDATE`, `CANDIDATE→{FROZEN, AMBIGUOUS_UNRESOLVED, EXCLUDED}`,
`"unidirectional": true`). 즉 codebook 자신도 이 규칙에 동의한다.

## 실제 동작 (`pilot_mapping.py` `_finish()`, L418-464)

```python
if abstained:
    record.update({"mapping_status": "AMBIGUOUS_UNRESOLVED", ...})
else:
    record.update({"mapping_status": "DRAFT", ...})   # FROZEN으로만 안 올린다는 주석뿐, CANDIDATE 언급 없음
```

`analysis/out/pilot/pilot_mapping.jsonl`(15건) 실측:

- stage 1 RULE로 domain·archetype이 **둘 다 확정**된 9건(`device_care`, `emart`,
  `gs_homeshopping_gsshop`, `hana_bank`, `hyundai_homeshopping_hmall`, `lotte_himart`,
  `my_files`, `nh_cok_bank`, `samsung_internet_browser`) 전부 `mapping_status = "DRAFT"`.
  A2 §1.9의 `CANDIDATE` 정의("규칙 … 으로 후보가 좁혀졌으나 확정 전")는 이 9건에
  글자 그대로 들어맞는다. `"CANDIDATE"`라는 문자열은 `pilot_mapping.py` 어디에도
  `mapping_status` 값으로 대입되지 않는다(grep 확인).
- 나머지 6건(`11st`, `baemin`, `chrome`, `coupang_eats`, `kakaotalk`, `mega_coffee`)은
  `mapping_status = "AMBIGUOUS_UNRESOLVED"`로 직접 대입된다. 이 6건 중 어느 것도
  중간에 `CANDIDATE` 상태를 거치지 않는다 — A2가 선언한 단방향 그래프는 `AMBIGUOUS_UNRESOLVED`로
  가는 유일한 간선이 `CANDIDATE →`라고 못박았는데, 이 구현은 `DRAFT`(또는 미지정 초기상태)에서
  바로 뛴다.

`analysis/codebook/OPEN_QUESTIONS.md` 부록 2(L340)도 "pilot mapping 15건의 매핑값 |
`mapping_status = DRAFT`"라고 **사실로 적어둔다** — 즉 이 상태는 이미 알려져 있었지만
A2 §1.9와의 불일치로 등재되지는 않았다 (`PA_FINDINGS_REGISTRY.json` 35건 중 이 항목 없음,
2026-08-27 기준).

## 왜 문제인가

`ANALYSIS_AND_TASK_CODEBOOK_FROZEN` 게이트의 통과조건(`PHASE_GATES §3`)은
"abstain 경로가 ambiguous를 강제분류하지 않고 abstain 가능함이 실증됨"이다.
그 실증의 근거가 `mapping_status` 필드 값인데, 그 필드 자체가 어휘 정본(A2 §1.9)이
선언한 유한상태기계를 따르지 않는다면 "실증"의 신뢰도가 떨어진다. 특히:

1. `CANDIDATE`를 건너뛴 9건은 이후 단계(P-B/승격)에서 "이 행이 실제로 규칙 기반으로
   좁혀진 적이 있는가"를 `mapping_status`만 보고는 구분할 수 없다(전부 `DRAFT`로 보인다).
2. `DRAFT → AMBIGUOUS_UNRESOLVED` 직행은 A2가 명시한 전이표 밖의 값이라, A2 §1.9를
   그대로 신뢰하는 하위 소비자(P-B 코드, 통계 파이프라인)가 있다면 이 값을 "정의되지 않은 전이"로
   거부하거나 조용히 잘못 해석할 수 있다.

## 권고

1. `_finish()`에서 stage 1/2 RESOLVED 결과는 `mapping_status = "CANDIDATE"`로,
   미해결 결과는 `"DRAFT" → "CANDIDATE"`를 거쳐 `"AMBIGUOUS_UNRESOLVED"`로 표기하도록 수정한다
   (즉 `CANDIDATE`가 "선택지가 좁혀졌지만 4단계 AI review로 확정하지 못해 넘어간" 중간 상태를
   명시적으로 나타내게 한다).
2. 또는, SHADOW pilot이 의도적으로 `DRAFT`에 머무르기로 한 것이라면 — 예: "SHADOW lane 결과는
   `CANDIDATE`를 자칭할 권한이 없다" 같은 정책적 이유가 있다면 — 그 이유를 A2 §1.9 대비
   **명시적 예외**로 `codebook.json`과 `OPEN_QUESTIONS.md`에 등재하고, A2 감사에게 그 편차를
   판정받는다. 현재는 편차가 조용히 존재할 뿐 등재되지 않았다.
3. 어느 쪽이든 `PA_FINDINGS_REGISTRY.json`에 새 finding으로 등재해 P-A 감사가 판정하게 한다.

## 검증 방법

```bash
PY=/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python
$PY -c "
import json
recs = [json.loads(l) for l in open('analysis/out/pilot/pilot_mapping.jsonl')]
print(sorted(set(r['mapping_status'] for r in recs)))
"
# → ['AMBIGUOUS_UNRESOLVED', 'DRAFT']  — 'CANDIDATE' 는 한 번도 등장하지 않는다
```

## 영향받지 않는 것

- `business_domain`/`interaction_archetype`의 실제 판정값(도메인 8종/아키타입 7종, RULE 정규식)은
  SSOT §6과 정확히 일치하며 별도 결함 없음.
- `mapping_status`가 `"FROZEN"`으로 잘못 올라가는 사례는 없음 — 그 금지는 코드가 정확히 지킨다.
