# P-C Fixture 세트 — LANE C

```
status                          = SHADOW_PREPARATORY
shadow_lane                     = LANE_C
base_sha                        = d5f1da5652953542d5c8be377026cc3293f2075a
created_before_p0_close         = true
authoritative                   = false
real_target_outcome_used        = false
fixture_only                    = true
real_target_measurement         = false
requires_post_p0_reconciliation = true
```

## 이 디렉터리가 존재하는 이유

`PHASE_GATES.md §4.5` REAL-TARGET FIREWALL 은 P0(`V2_SSOT_FROZEN`) 종료 전
**실제 서비스에 접속해 접근성 결과를 만드는 것을 금지**한다. 그런데 `§4.2` 는
`local/synthetic fixture 기반 collector 구현`을 명시적으로 허용한다.

측정기를 검증하려면 **정답을 아는 대상**이 필요하다. 실제 서비스는 정답을 모르고,
알아내려는 순간 금지된 real-target 측정이 된다. 이 fixture 세트가 그 자리를 대신한다.

> **여기서 나오는 PASS/FAIL 은 synthetic fixture 에 대한 engine test 결과다.**
> 실제 서비스에 대한 research finding 이 아니며 그렇게 인용할 수 없다 (`§4.1` · `§4.3` · `§4.6`).

## 규약

1. 모든 fixture 는 파일 상단 주석에 **무엇을 검증하려는 것인가** 와 **기대값**을 적는다.
2. 기대값의 기계 판독본은 `expectations.json` 이고, 테스트가 그 파일을 읽는다.
3. fixture 는 **외부 자원을 참조하지 않는다.** `http(s)://` 가 한 글자라도 들어가면
   그 순간 real-target 수집이 되고, `test_fixtures_never_reference_a_live_service` 가 막는다.
4. 값을 고칠 때는 `expectations.json` 과 상단 주석을 **함께** 고친다.
   한쪽만 고치면 그 자체가 drift 다.

## 무엇을 검증하는가

| fixture | 검증 대상 | 근거 |
|---|---|---|
| `simple_article.html` | L0 기본 수집 경로 · 랜딩이 곧 endpoint | `02 §3` |
| `search_dispatch.html` | QUERY 영역 신호 · 제출 endpoint · `text_input_episode` | `A1 §1.2` · `§4.2` |
| `auth_login_gate.html` | 로그인 gate 판별 · archetype 별 분기 | `A2 §1.5.1a` E-5 |
| `auth_identity_gate.html` | 본인인증 gate 판별 · 금융/커뮤니티가 갈리는 지점 | `A2 §1.5.1a` E-6a |
| `auth_ambiguous_gate.html` | 판별 불가 gate 의 **abstain 경로** | `A2 §1.5.1a` |
| `blocking_modal.html` | popup 4단계 검출 · dismiss 5차·6차 · 대표기능 완전 가림 | `02 §5` · `A1 §3` |
| `promo_modal.html` | 가리지 않는 modal · `dismiss_persistence_hint` | `02 §5` · `A1 §3.2` |
| `cookie_consent.html` | 결정적 의미분류 | `02 §5` 4차 |
| `motion_banner.html` | motion raw feature | `02 §3` |
| `missing_accessible_name.html` | accessible name 부재가 **관측된 사실**로 남는가 | `A2 §1.6` |
| `small_target.html` | target size raw feature (CSS px, DPR 미적용) | `A1 §3.2` |
| `low_contrast_control.html` | contrast raw feature — probe 가 임계값을 갖지 않는가 | `02 §4` |
| `overlay_primary_action.html` | `PrimaryActionOcclusion` 의 분자·분모 보존 | `A2` 규칙 C-2 |
| `depth_path_0/1/3.html` | NED / IED 분리와 경계 | `A1 §1.3` · `§1.4` |
| `unresolved_route.html` | 예산 발화 + `NULL` 보존 (`MPFED = 8` 이 아니다) | `A1 §2` · X-5 |

`depth_path_3_s1` · `depth_path_3_s2` · `unresolved_route_b` 는 위 경로의 중간 상태다.

## gate 종류 판별 (Q-9)

`A2 §1.5.1a` 는 gate **종류**로 endpoint 를 가르지만(금융은 로그인·본인인증 둘 다,
커뮤니티는 로그인만), 관측된 gate 가 어느 쪽인지 **판별하는 규칙이 없었다.**

`auth_login_gate.html` · `auth_identity_gate.html` · `auth_ambiguous_gate.html` 세 fixture 가
그 판별의 근거다. 각 파일 주석에 **어떤 신호가 있고 어떤 신호가 없는지**를 대조군까지 적었다.
판별기(`engine/gate_classifier.py`)는 fixture 의 `data-gate-kind` 를 **읽지 않는다** —
읽으면 조작화가 아니라 정답 열람이 된다. `data-gate-kind` 는 테스트의 기대값일 뿐이다.

판별 불가일 때는 **강제분류하지 않는다.** `UNDETERMINED` 로 남기고 어느 archetype 에서도
endpoint 로 승격시키지 않는다 — `A2 §1.5.1a` 의 *모호할 때 endpoint 로 올리는 방향의
기본값을 두지 않는다* 를 그대로 이행한다.

본인인증 UI 의 신호(통신사 선택·간편인증 제공자·인증번호 입력)는 일반적으로 알려진 구성이며
**특정 서비스의 실측이 아니다.** `[추정]` 표시가 붙은 항목은 실관측 대조가 필요한 가설이고,
신호 사전의 서비스별 적용은 **P-A endpoint codebook 이 동결한다** (`A2 §1.9` 규칙 P-1).
실제 로그인/인증 화면을 열어 대조하는 것은 `PHASE_GATES §4.5` 위반이므로 하지 않았다.

## 실행

```bash
python research/landing_accessibility/scripts/run_fixture_engine.py --out artifacts/pc_fixture
```
