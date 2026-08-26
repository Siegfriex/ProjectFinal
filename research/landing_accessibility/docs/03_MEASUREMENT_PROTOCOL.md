# 03 — Landing-only 측정 프로토콜 (E001 전 동결 대상)

**상태** DRAFT — `engine_integrity` gate 통과 시 동결
**전제** E001 본수집은 Research Director GO 없이 실행하지 않는다.

## 0. 이 문서가 존재하는 이유

판정 임계값은 E001 이후에도 바꿀 수 있다. Evidence 와 Judgment 를 분리했기 때문이다.

```
E001 + J001
E001 + J002   ← 판정규칙만 교체, 사이트 재방문 없음
E001 + J003
```

그러나 **probe 가 애초에 수집하지 않은 raw feature 는 재판정으로 복구할 수 없다.**
따라서 **관측 스키마는 수집 전에 동결한다.** 이것이 이 문서의 목적이다.

## 1. 관측 단위

```
observation = service_id × official_landing_url × audit_date × protocol_version
```

한 `web_target_group` 에 여러 `measurement_entity` 가 묶여 있어도 **관측은 정확히 1회**다.
쿠팡 APP 지표와 쿠팡 RETAIL 지표는 별개 measurement_entity 지만 랜딩 URL 이 같으면 수집은 한 번이다.

## 2. 공통 브라우저 환경 (Pilot 검증분 승계)

```
viewport            390 × 844 CSS px
device_scale_factor 3
locale              ko-KR
timezone_id         Asia/Seoul
is_mobile           true
has_touch           true
user_agent          모바일 UA (고정 문자열, protocol_version 에 포함)
storage_state       없음 — 로그인·쿠키·세션 일절 없음
context             관측마다 새 context
```

로딩 안정화 정책도 고정한다.

```
goto            wait_until="domcontentloaded", timeout=45000
그 다음         wait_for_load_state("networkidle", timeout=2500)
타임아웃 시     NETWORKIDLE_TIMEOUT 을 기록하고 계속 진행 (실패 아님)
```

**이 블록 전체의 sha256 이 `PROTOCOL_SHA` 다.** E001 시작 후 변경 금지.

## 3. 두 관측 범위

### 3-1. Initial Viewport — 최초 가시영역

사용자가 접속 직후 실제로 보는 것. 스크롤 없음.

- 접근성 적응기능 노출 여부
- 팝업·오버레이 가림 여부와 그 면적
- 최초 화면 내 텍스트 대비
- 최초 화면 내 조작요소 크기
- 최초 화면 내 주요 버튼의 accessible name

### 3-2. Landing Document — 랜딩 문서 전체

같은 문서의 DOM/AX 전체를 정적으로 관측한다.

- 이미지 대체텍스트 / 레이블·폼 연결 / 링크 텍스트
- 명도대비 / 조작가능 요소 / 언어·제목 / 자동재생
- 기타 validated KWCAG 적용기회

**로그인 이후·결제 이후·검색 결과 이후는 주 분석에서 제외한다.**
Pilot 의 `TASK_ENTRY` 휴리스틱은 폐기한다 — 이동·조작 없이 "과업 진입을 관측했다"고 주장할 수 없다.
관측 범위 상한은 `LANDING_ONLY` 다.

## 4. 증거 식별자 — Pilot CRITICAL 재발 차단

**표시명·한글명·record_id 의 정규식 치환 결과를 파일명으로 쓰지 않는다.**

```python
service_id     = "svc_" + sha256(canonical_service_key)[:16]
observation_id = "obs_" + sha256(service_id + canonical_url + audit_date + protocol_version)[:20]
```

```
evidence/E001/dom/{observation_id}.html
evidence/E001/ax/{observation_id}.json
evidence/E001/screen/{observation_id}.png
evidence/E001/probe/{observation_id}.json
```

## 5. 1:1 증거 불변식 — 하나라도 깨지면 Run 전체 INVALID

1. 측정 성공 레코드 수 == DOM 파일 수 == AX 파일 수 == Screen 파일 수 == Probe 파일 수
2. 모든 `observation_id` 가 run 내 유일
3. probe 내부의 `service_id` / `target_url` 이 records 와 일치
4. 각 파일의 sha256 이 manifest 와 일치
5. 동일 파일경로에 두 observation 이 매핑되지 않음
6. 기존 run 디렉터리가 존재하면 **write 를 거부**
7. records.jsonl 작성 후 raw evidence manifest 를 다시 검증

**측정 실패는 허용하지만 설명되지 않은 손실은 허용하지 않는다.**

```
10 targets → 8 MEASURED + 2 ACCESS_BLOCKED
             레코드 손실 0 / 엉뚱한 증거 참조 0 / overwrite 0
```

성공률은 게이트가 아니다. 계보 무결성이 게이트다.

## 6. Append-only

```
코드 변경 없이 재수집 필요        → E002 (E001 수정 금지)
증거는 같고 판정규칙만 변경        → J002
E001 중 버그 발견                 → E001 을 INVALID/PARTIALLY_INVALID 선언 후 E002
```

`check_append_only` 를 정의만 하지 않고 **실제 실행 경로에서 호출**한다.
Pilot 은 이 함수를 만들어 두고 호출하지 않았고, `run_batch` 가 `"w"` 모드로 열어 같은 run_id 재실행 시 덮어썼다.

## 7. 판정 의미론 — Pilot 결함 시정

### 7-1. verdict_state

```python
if fail_count > 0:                                  verdict_state = FAIL
elif undetermined_count > 0:                        verdict_state = UNDETERMINED
elif pass_count > 0 and pass_count == applicable_count:  verdict_state = PASS
else:                                               verdict_state = NA
```

**UNDETERMINED 가 하나라도 있으면 서비스 수준 PASS 로 승격하지 않는다.**

Pilot 은 `strict = FAIL if f > 0 else (UNDET if u == total else PASS)` 였다.
`u == total` 일 때만 UNDETERMINED 라서, PASS 가 하나만 섞여도 나머지가 전부 증거 불충분인데 PASS 가 됐다.
실측 60건이 그렇게 통과했고 **전부 1.4.3 명도대비**였다 — 1.4.3 PASS 63건 중 60건이 부분 확인이었다.

### 7-2. 자동화 등급 분리

서비스-criterion 단위로 다음을 **구조적으로 분리**한다.

```
applicable_count
pass_count / fail_count / undetermined_count
decidable_count      = pass + fail
pass_rate_decided    = pass / decidable_count
undetermined_rate    = undetermined / applicable_count
machine_confirmed_fail   ← AUTO_DECIDABLE 만
review_required_flag     ← AUTO_FLAG_ONLY
human_final_verdict
```

Pilot 은 `criteria_fail` 하나에 둘을 합쳤다. 참조군 평균 3.54 = 확정 2.67 + 신호 0.88 이었다.
**기사 본문의 "미흡" 은 machine_confirmed 또는 사람검토를 거쳐 확정된 것만 쓴다.**

### 7-3. NA 와 UNDETERMINED

```
NA            적용기회 부재.       PASS 가 아니다. 0점도 아니다.
UNDETERMINED  증거 불충분·관측한계. 무결점이 아니다.
```

이 둘을 PASS 로 환산하는 경로가 하나라도 있으면 통과율이 실제보다 높아진다.

## 8. Criterion 승격 조건

각 criterion 은 다음 메타를 갖춰야 E001 대상이 된다.

```
criterion_id
source_document          KWCAG 2.2 원문 또는 공식 해설서
source_page_or_section   인용 위치
applicability_rule       적용기회 정의
exceptions               적용 제외
machine_observable_fields  probe 가 수집해야 할 raw feature 목록
unknown_rule             확정 불가 시 처리
boundary_tests           경계값 테스트 케이스
validated_for_main_study bool
```

**기사 Top feature 후보는 반드시 `validated_for_main_study=true` 여야 한다.**

기준 우선순위는 고정이다.

```
1. KWCAG 2.2 원문 / 공식 해설서
2. 국내 관련 공식 기술문서
3. WCAG 2.1/2.2 는 보조 해석
```

**WCAG 수치를 KWCAG 규칙으로 대체하지 않는다.** Pilot 은 2.1.3 에 WCAG 2.5.8 의 24px 을 차용해
미흡률 89.8% 를 만들었고, 해설서 원문(대각선 6mm ≈ 22.68 CSS px)으로 시정하니 41.0% 가 됐다.

절차는 이렇다: **원문 인용 → 코드 상수화 → 경계값 테스트 → 동일 증거 재판정.**

```python
CSS_PX_TO_MM = 25.4 / 96.0
TARGET_DIAGONAL_MIN_MM = 6.0
# 경계검증: 17×17 → 6.36mm PASS / 16×16 → 5.99mm FAIL (해설서 '약 17px' 서술과 일치)
```

## 9. 접근성 적응기능 — 별도 변수

적응기능은 **KWCAG PASS 의 대체물이 아니다.** 별도 사용자지원 특성으로 관측한다.

```
SENIOR_MODE / EASY_MODE / LARGE_TEXT / FONT_RESIZE / HIGH_CONTRAST / ACCESSIBILITY_MENU / OTHER / NONE
```

관측 항목: 존재 여부 · 최초 viewport 에서 발견 가능 여부 · accessible name 존재 ·
표시 텍스트/아이콘 · 1회 활성화 성공 여부 · 기본화면 대비 변화.

적응기능이 있으면 **기본 랜딩을 먼저 동일 조건으로 측정한 뒤**, 별도 paired observation 으로 활성화 후 화면을 추가 측정한다.

## 10. 게이트 경계

로그인·결제·본인확인·CAPTCHA 를 감지하면 **관측을 멈추고 태그만 기록한다.** 우회 코드를 넣지 않는다.

Pilot 의 게이트 감지는 `input[type=password]` 와 본문 키워드에만 의존해 미탐·오탐이 있었다.
Main Study 는 다음을 신호에 추가한다.

- 최종 URL 경로 (`/login`, `/signin`, `/auth`)
- 페이지 제목
- 폼 action
- HTTP 401/403

**게이트 판정 근거(어느 신호가 걸렸는지)를 레코드에 남겨 감사 가능하게 한다.**

## 11. Redirect 와 범위

`target_url` · `final_url` · `redirect_chain` 을 모두 보존한다.

등록도메인 비교는 **Public Suffix List 기반 파서**로 한다.
Pilot 은 마지막 두 라벨 문자열 비교(`".".join(netloc.split(".")[-2:])`)를 써서
`.co.kr` / `.or.kr` / `.go.kr` 에서 무관한 사이트를 같은 등록도메인으로 오판했다.

외부 파트너 도메인으로 최종 이동하면 자동으로 같은 서비스라고 가정하지 않고 **URL QA 큐**로 보낸다.

## 12. 증거 완결성 명명

Pilot 의 `evidence_complete` 는 과장이었다. 클릭·키 입력·포커스 이동을 수집하지 않으면서
"완결"이라 불렀고, 그 위에서 키보드(2.1.1)·초점(2.1.2)·맥락변화(3.2.1)를 판정했다.

→ **`static_evidence_complete`** 로 명명한다.
→ `interpretation_limits` 에 "상호작용 증거는 수집하지 않았으며 해당 항목은 정적 신호"를 명시한다.
→ `criterion_table` 각 행에 판정기의 `note` 를 실어 기사 표에 각주로 붙일 수 있게 한다.

## 13. E000-SMOKE — 자율 수행 상한선

E000 은 **코드 검증용 disposable run** 이다. 기사·통계에 쓰지 않는다.
8~12개 서비스로 하되 무작위가 아니라 **위험 케이스를 의도적으로 포함**한다.

| 케이스 | 목적 |
|---|---|
| 한글 이름 길이가 같은 서비스 2~3개 | 파일명 충돌 재발 방지 확인 |
| 인증 O 2개 이상 | registry join 확인 |
| 인증 X 2개 이상 | NOT_FOUND 처리 확인 |
| `m.` redirect 서비스 | redirect 처리 |
| `.co.kr` / `.or.kr` 서비스 | PSL 검증 |
| DOM 큰 서비스 | probe 부하 |
| 화면 동적 서비스 | network 안정화 |
| 적응기능 후보 서비스 | detector 점검 |

**E000 통과 조건**: collision 0 / wrong-reference 0 / silent loss 0.

## 14. E001 동결 대상

E001 시작 전에 다음 다섯을 freeze 하고, 시작 후에는 수정하지 않는다.

```
TARGET_SET_SHA
PROTOCOL_SHA
COLLECTOR_SHA
PROBE_SHA
AUDIT_DATE
```
