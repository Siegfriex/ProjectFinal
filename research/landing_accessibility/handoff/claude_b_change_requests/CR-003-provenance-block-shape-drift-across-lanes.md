# CR-003 — SHADOW provenance 블록의 `source_frame_sha`/`codebook_sha` 형식이 lane마다 다르다

- 제기자: Claude B — WORKER-I 통합 준비 (lane `claude-b/integration-prep-c007`,
  base `agent/landing-v2-exec` @ `2025e56`)
- 대상: `agent/landing-pa-shadow` @ `0f46203`, `agent/landing-pb-prework` @ `9999857`,
  `agent/landing-pc-fixture` @ `0c36c95` — 이 CR은 세 브랜치 중 어느 것도 직접 수정하지 않는다.
  통합 트리(`research/landing_accessibility/analysis/SHADOW_MANIFEST.json` ·
  `shadow/lane_b/state/LANE_B_SHADOW_MANIFEST.json` ·
  `src/landing_accessibility/engine/provenance.py`/`SHADOW_PROVENANCE.json`)에 세 lane을
  selective port로 한 tree에 모으는 과정에서 발견했다.
- 심각도(제안): **P3** — real-target 오염이나 판정 오류는 아니다. `PHASE_GATES §4.3`이 요구하는
  필수 5필드(`status`/`base_sha`/`created_at`/`created_before_p0_close`/`authoritative`/
  `real_target_outcome_used`/`requires_post_p0_reconciliation`)는 세 lane 모두 정확히 채운다.
  이 CR은 §4.3이 "가능하면" 권장하는 두 필드(`source_frame_sha`·`codebook_sha`)의 **형식**만
  다루며, 필수 계약 위반이 아니다.
- 판정 권한: 세 lane의 각 감사(P-A/P-B/P-C adversarial + ssot) 또는 §4.7 reconciliation 담당

## 발견한 것

`PHASE_GATES.md §4.3`은 `source_frame_sha`·`codebook_sha`를 "가능하면 … 함께 기록한다"고만
말하고 값의 **형태**(스칼라/딕셔너리, 접두어 유무)를 정의하지 않는다. 세 lane이 각자 다른
형태로 채웠다.

### 1. `source_frame_sha` — 딕셔너리 vs 문자열

| lane | 파일 | 형태 | 값 |
|---|---|---|---|
| P-A | `analysis/SHADOW_MANIFEST.json` | `dict[str, str]` — `state/*.parquet` 6개 파일 각각의 sha256 | `{"entity_alias_map.parquet": "3c2ab5…", "panel_registry.parquet": "1b71bc…", …}` |
| P-B | `shadow/lane_b/state/LANE_B_SHADOW_MANIFEST.json` | 스칼라 문자열 | `"d5f1da5652953542d5c8be377026cc3293f2075a"` — **`base_sha`/`input_authority_sha`와 같은 git commit SHA를 그대로 복사한 값**이다 |
| P-C | `src/landing_accessibility/engine/provenance.py` (`ShadowProvenance`) | 런타임에서 optional, 기본값 `None`. 예시 파일(`SHADOW_PROVENANCE.json`)에는 아예 없음 | 미기록 |

P-A의 형태는 실제로 `state/*.parquet` 6종의 **데이터 무결성**(입력 프레임이 그 사이 바뀌지
않았는가)을 검증 가능하게 만든다 — 실제로 P-A-QA 독립검증(`claude-b/pa-qa`)이 이 6개 해시를
재계산해 전건 일치를 확인했다. P-B의 값은 git commit SHA를 재사용한 것이라 `base_sha`/
`input_authority_sha`와 항상 동일하며, **입력 데이터 파일의 내용을 전혀 검증하지 않는다** —
필드 이름이 약속하는 것(“이 lane이 읽은 frame 데이터의 해시”)과 실제로 기록된 것(“이 lane이
갈라져 나온 git commit”)이 다르다.

### 2. `codebook_sha` — 접두어 유무

| lane | 값 |
|---|---|
| P-A | `"49cc10484fa4f5cf344be96ed828dcb1ae93ccbab61b4e59caeaec1b8deb239e"` (bare hex) |
| P-B | `"sha256:49cc10484fa4f5cf344be96ed828dcb1ae93ccbab61b4e59caeaec1b8deb239e"` (`sha256:` 접두) |

같은 `codebook.json` 파일의 같은 해시값인데 표기 형식만 다르다. P-B의 `psl.list_sha256`도
같은 `sha256:` 접두 관례를 쓴다.

## 왜 등재하는가

이 통합 워커의 지시서는 "서로 다른 가정으로 만든 스키마/인터페이스가 있으면 SSOT/A2 문서를
근거로 정합시키고, 판단 근거가 없으면 change request로 넘겨라"를 요구한다.
`PHASE_GATES §4.3`·`A2`·`00`~`05` 어디에도 이 두 필드의 형태를 지정한 조항이 없어 **이 통합
워커에게는 어느 쪽이 맞는지 판단할 권한이 없다.** 세 lane을 감사하는 P-A/P-B/P-C 감사가
정본을 정해야 한다.

## 권고

1. `source_frame_sha`의 **의미를 명문화**한다 — "이 lane이 실제로 읽은 입력 파일들의 내용
   해시"로 고정한다면 P-A의 dict-of-file-hash 형태가 그 의미를 실제로 충족하고, P-B의 현재
   값(git commit SHA 재사용)은 **의미상 오기**이므로 P-B 자신의 lane에서 시정이 필요하다
   (또는 P-B가 의도적으로 "frame 자체가 아니라 frame이 속한 commit"을 기록하려 했다면 필드를
   `source_frame_commit_sha` 등으로 개명해 `codebook_sha`류와 구분해야 한다).
2. `codebook_sha`의 표기 형식(`sha256:` 접두 여부)을 `PHASE_GATES §4.3`이나 `07_EVIDENCE_MANIFEST_CONTRACT`
   수준에서 한 가지로 고정하고, 두 lane 중 한쪽을 그에 맞춰 시정한다.
3. 이 CR은 P0 blocking이 아니다 — §4.7 reconciliation(각 lane의 공식 promotion 시점)에서
   처리해도 된다.

## 통합 트리에서의 처리

이 워커는 위 드리프트를 **판단하지 않고 그대로 포팅**했다 — P-A/P-B/P-C의 원본 값을
각자의 형태 그대로 유지했다. 유일한 예외는 P-A 쪽 `analysis/SHADOW_MANIFEST.json`에
`integration_note`/`non_reproducible_artifacts` 키를 추가한 것뿐이며(CR-001/CR-002 처리
기록), `source_frame_sha`/`codebook_sha`의 형태 자체는 건드리지 않았다.
