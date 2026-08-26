# 00 — 권위 서열과 확정 결정

**하네스** orchestrator-constitution-v3 · **Phase** P1_ISOLATION_AND_SOURCE_REFREEZE

## 1. 권위 서열 (변경 불가)

```
A0  Research Director 명시적 결정
A1  Wiseapp Insight 933 원문                → 모집단 권위
A2  한국디지털접근성진흥원 공식 인증목록      → certified_current 0/1 권위
A3  KWCAG 2.2 공식 원문                     → 판정 기준 권위
A4  KWCAG 해설서                            → 판정 해석 보조
A5  Main Study structured derivatives
A6  Pilot R1-R4                             → 실패학습·회귀검증만
A7  기존 xlsx / comparison_targets / old feasibility → INVALIDATED DERIVED ASSET
```

**A7 은 A1 을 대체할 수 없다.**

## 2. 모집단 권위 — 확보 완료

| | |
|---|---|
| authority_id | `WISEAPP_ACTIVE_SENIOR_2025H2_933` |
| 발행처 | 와이즈앱·리테일·굿즈 (주식회사 아이디어웨어) |
| baseDT | 2026-03-05 |
| 측정기간 | 2025년 하반기 · 전년 동기간 대비 |
| 코호트 | 액티브시니어+ 세대 = **50대 이상** |
| 영역 | `bapp=1` AND `bretail=1` — APP·RETAIL 양쪽 |
| 원문 구조 | 4 chapter / 11 section / `<table>` 0개 / `<img>` 11개 |

취득 경로 2종을 상호 교차검증했다.

1. `POST /insight/detail/getDetail.json` body `{"insightNid":"933","preview":0}` → 154KB JSON
2. Playwright chromium 렌더 → HTML · 본문텍스트 · full-page 스크린샷

**모든 순위표가 이미지로만 존재한다.** 텍스트 파싱 경로가 없으므로 figure 판독이 유일한 데이터화 경로이며,
판독 결과는 반드시 적대적 재확인을 거친다.

## 3. A7 강등 근거 — 원문과 파생자료의 실제 충돌

| 항목 | A1 원문 | A7 xlsx | 판정 |
|---|---|---|---|
| Chapter1(1) 깊이 | **TOP15** | `01_사용자_사용시간` Top10 표기 | MISMATCH |
| 카카오톡 사용자 | **1,377만 명** | 1379 만명 | MISMATCH (2만 명) |
| 코호트 라벨 | 액티브시니어+ 세대(50대 이상) | `50plus` / `50세 이상` 혼용 | 정합 확인 필요 |
| 영역 구분 | APP / RETAIL 분리 | `Primary 유형` 단일 축으로 혼재 | 구조 불일치 |

기존 48 canonical service frame 은 이 불일치가 해소되기 전까지 모집단 권위가 없다.

## 4. 철회된 결론

| id | 상태 | 사유 |
|---|---|---|
| `RQ2_RQ3_RQ4_NO_GO` | `WITHDRAWN_PENDING_SOURCE_REFREEZE` | NO-GO 판정이 A7 파생 frame 위에서 산출됨. 원문 재동결 후 재산출한다. |
| `OLD_CATEGORY_FEASIBILITY` | `INVALIDATED_BY_SOURCE_MISMATCH` | 동일. 파일은 삭제하지 않고 INVALIDATED 로 보존. |

**철회는 "틀렸다"가 아니라 "권위 없는 입력으로 계산됐다"는 뜻이다.**
재동결 후 같은 결론이 다시 나올 수 있으며, 그때는 A1 근거를 갖는다.

## 5. 인증 결합 원칙

인증목록은 **모집단이 아니라 lookup** 이다.

```
certified_current = 1  ⟺  valid_on_audit_date
                        AND certification_target_scope_match
                        AND service_identity_match
```

등록도메인 일치만으로 1 을 부여하지 않는다.
Pilot 에서 `삼성월렛 → samsung.com → 삼성전자승마단` 오탐이 실제로 발생했다.

## 6. 절대 금지

- E001 본수집 — Research Director GO 없이 실행 금지
- Pilot 디렉터리 수정 — `research/refcohort` 는 READ_ONLY
- Pilot R3/R4 COMPARISON 통계 재사용
- `CLASSIFY_RULES` / `TYPE_MAP` / `TASK_ENTRY` 휴리스틱 포팅
- 사용자 승인 없는 RQ 구조 변경
