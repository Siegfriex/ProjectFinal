# STALE / SUPERSEDED 문서 목록 — CLEAN-0

**ID** `LA-STALE-2.1-20260827T2100` · **assertion_type** `DECISION`

> **삭제하지 않는다.** superseded 는 지위 표기이지 제거가 아니다 (SSOT v2.1 §14, D-16).
> 이 목록의 목적은 **다음 세션이 옛 문서를 현재 권위로 오독하지 않게 하는 것**이다.

## §1 SUPERSEDED — 승계자가 있다

| 문서 | 승계자 | 살아남는 부분 |
|---|---|---|
| `docs/v2/**` (v2 문서군) | `docs/v2_1/**` | 연구질문 · L0+L1 범위 · 3축 · NED/IED/MPFED 정의 · KWCAG 어휘 · evidence append-only/hash lineage · outcome-blind freeze · Human Final ≤5 · 새 supervised 모델 금지 · archetype 내부 상대깊이 — **전부 승계된다** |
| `control/POST_E001_MEASUREMENT_RECOVERY_PLAN.md` (개정 1·2) | `docs/v2_1/02_MEASUREMENT_RECOVERY_ROADMAP_v2.1.md` | 라벨러 전용워커 지정 · 라벨 해시 동결 · 모집단 56 확정 — **유효** |
| `SSOTV2/` (repo root, untracked) | `docs/v2_1/` (control 브랜치 설치본) | 내용 동일. 해시로 대조 가능 (`V2_1_PACK_HASHES.txt`) |

## §2 HISTORICAL — 승계자 없이 종료

| 문서 | 사유 |
|---|---|
| `control/TIMEBOX_1630_EXECUTION_SSOT.md` | 타임박스 종료. **measurement semantics 를 override 하지 않았다**는 기록으로 보존 |
| `E001_LAUNCH.md` (repo root, untracked) | E001 실행 지침. 실행 종료 |
| `docs/_invalidated/**`, `state/_invalidated/**` | 이미 무효화 표기 완료 |
| `handoff/C013_WIP.patch` | 적용 여부 미확인 패치. **R0 대상 아님** |

## §3 STALE 위험 — 코드 사실로 소비되면 안 되는 산문

| 위치 | 내용 | 왜 위험한가 |
|---|---|---|
| `executor.py:68-75` `default_task_definition()` docstring | *"codebook 없이 endpoint 를 만들어내지 않는다"* | **원천 CSV 에 59/59 정의가 있었다.** 이 docstring 은 설계 의도를 서술했으나 실제로는 wiring 갭을 가렸다. T5 가 T1 에 진 확정 사례 |
| 산문 SSOT 부재 (backlog 등재) | 숫자는 파일에서 읽는데 **산문은 생성기 안에 상수로 박혀 있다** | 산출물만 고치면 다음 생성에서 되살아난다. 실제로 `scripts/build_real_marts.py:879-880` 이 잔여 문구의 원본이었다 |
| `CODEBOOK_PENDING` 문자열 | 입력 미도달 표기 | **거부(refusal)로 읽히면 안 된다.** E-6b 실제 거부 1건과 묶이면 1건이 54건을 정당화하는 데 쓰인다 |

**→ C 의 CLEAN-0 감사 항목**: stale prose 가 코드 사실로 소비되는 경로 탐지 (roadmap §2 C).

## §4 이번 CLEAN-0 에서 등재만 하고 손대지 않은 backlog

R0 중에 직접 관련되지 않는 한 다시 열지 않는다 (인계 §G).

```
locally-forgeable tracking-ref firewall 잔여
prepush-hook-symlink-depends-on-control-worktree-lifetime
게이트 이름이 생산자·판정자를 구분하지 않음
CLAIM_GOVERNANCE §4 문서 내 상호모순 검사 항목 부재
서술 SSOT 부재
그 외 post-E001 부채
```
