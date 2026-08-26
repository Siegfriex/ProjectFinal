# Pilot 스냅샷 대조 노트 (참고용)

- Main Study 스냅샷: `KWACC_WA_20260826` — `research/landing_accessibility/sources/certification/`
- Pilot 스냅샷(A6, READ_ONLY 참조): `research/refcohort/runs/r1-discovery/official_registry.jsonl`
- 대조 목적: **Pilot 수치를 정답으로 삼기 위한 것이 아니다.** 두 독립 수집의 차이 자체를 관측 사실로 남긴다.
- Pilot은 A6 자산이라 A2 권위 경로에 인용하지 않는다. 이 문서는 대조 기록일 뿐 근거 문서가 아니다.

## 수집 시각

| | Pilot | Main Study |
|---|---|---|
| 첫 페이지 요청 | 2026-08-25T16:23:06Z | 2026-08-26T03:24:39Z |
| 마지막 페이지 요청 | 2026-08-25T16:25:57Z | 2026-08-26T03:27:46Z |
| 간격 | — | Pilot 대비 약 11시간 뒤 |

## 집계 대조

| 지표 | Pilot | Main Study | 차이 |
|---|---:|---:|---:|
| pages_fetched | 230 | 230 | 0 |
| pages_with_cards | (미기록) | 229 | — |
| declared_last_page (목록이 선언한 마지막 페이지) | (미수집) | 229 | — |
| rows_raw | 2,283 | 2,283 | 0 |
| rows_dedup | 2,283 | 2,283 | 0 |
| VALID | 227 | 227 | 0 |
| EXPIRED | 2,056 | 2,056 | 0 |
| UNKNOWN | 0 | 0 | 0 |
| 감사일(2026-08-26) 유효 건수 | 226 | 226 | 0 |
| 대상 URL 보유 행 | 2,279 | 2,279 | 0 |
| 종료 사유 | `NO_CARDS` | `NO_CARDS_AT_DECLARED_END` | 사유 어휘가 다르다(아래) |
| snapshot_status | (개념 없음) | `COMPLETE` | — |

## 레코드 단위 대조

`certification_number`(상세 URL 일련번호)를 키로 2,283건 전건이 양쪽에 존재한다.
한쪽에만 있는 키는 **0건**이다. 공통 키에 대해 아래 필드를 전수 비교한 결과 **불일치 0건**이다.

- `service_name`, `organization_name`, `certification_status_listed`
- `cert_start_date`, `cert_end_date`
- `certified_target_url_listed`, `certification_detail_url`
- `list_page`, `list_index`

## 원문 해시 대조

230개 페이지 전부 **원문 sha256이 Pilot과 완전히 동일하다** (일치 230 / 불일치 0).

관측 사실로서의 함의:

1. 11시간 간격의 두 수집에서 목록 HTML이 바이트 단위로 동일했다. 이 목록 페이지는
   요청 시각·세션에 따라 바뀌는 부분(타임스탬프, 토큰, 광고 등)이 없다.
2. 따라서 이 대조는 **내용의 독립 검증이 아니다.** 같은 서버 응답을 두 번 받은 것이고,
   서버가 틀린 값을 준다면 두 스냅샷 모두 같은 방식으로 틀린다.
3. 반대로 **수집 절차의 독립성은 성립한다.** Main Study는 자체 요청·자체 원문 저장·자체 매니페스트로
   스냅샷을 확보했고, Pilot 산출물을 입력으로 쓰지 않았다. A2 권위 요건은 이 경로로 충족된다.
4. 이 대조를 A2 근거의 "교차 확인"으로 승격하지 않는다. 확인된 것은 두 수집이 같은 원문을 봤다는 사실뿐이다.

## 다른 점 (수치가 아닌 차이)

| 항목 | Pilot | Main Study |
|---|---|---|
| 종료 판정 | 카드 0건 페이지에 도달하면 종료. 그 종료가 정상인지 검증하지 않았다. | 목록 1페이지 페이지네이터가 선언한 마지막 페이지(229)와 실제 카드 보유 페이지 수(229)를 대조해 `COMPLETE` 확정. |
| 완결성 상태 | 필드 없음 | `snapshot_status` = COMPLETE / INCOMPLETE |
| 부정 판정 보호 | 없음 | `valid_at_audit_rows()` 가 INCOMPLETE 스냅샷에서 `IncompleteSnapshotError` 를 던진다 |
| 전송 실패 처리 | 1회 실패 시 전수 크롤 종료 | 지수 백오프 3회 재시도 후에도 실패하면 `TRANSPORT_OR_STATUS` → INCOMPLETE |
| 원문 저장 검증 | 저장만 | 저장 직후 되읽어 sha256 재계산, 불일치 시 즉시 중단 |
| 필드 추출 | 평문 정규식 (`기관명\s*:\s*([^인]+?)\s*인증기간`) + span 순서 폴백 | `sr-only` 라벨 앵커 기반 |
| 재파싱 | 없음 (파서 수정 시 전수 재크롤) | `--reparse` 로 저장된 원문에서만 재생성 (해시 재검증 포함) |

Pilot의 기관명 정규식은 기관명에 '인'이 들어가면 매칭이 깨지지만, span 순서 폴백이 같은 값을 집어내
결과적으로 산출물에는 차이가 남지 않았다(불일치 0건). 즉 **결함은 있었으나 이번 목록에서는 발현하지 않았다.**

## Main Study 스냅샷에서 관측된 목록 자체의 결함

Pilot 대조와 무관하게, 원문 자체가 갖고 있는 문제다. 하류 단계에서 URL을 쓸 때 반드시 처리해야 한다.

- 대상 URL 링크가 아예 없는 행: **4건** (1954, 803, 689, 549 — 모두 EXPIRED)
- 스킴(`http://`/`https://`)이 빠진 `href`: **26건** (예: `namdogallery.or.kr`, `www.high1.com`).
  값은 정규화하지 않고 원문 그대로 보존했다. 정규화는 하류의 몫이며 매니페스트의
  `rows_with_scheme_less_target_url` 로 개수를 고지한다.
- 그중 3건은 URL이 아니라 텍스트다: `보건복지부 홈페이지`(27), `국립중앙도서관 홈페이지`(25), `-`(1812).
- 인증기간이 비어 있는 행: **1건** (1812, `service_name` 도 `-`). `in_period_at_audit=0` 으로 처리됐다.
- `VALID` 인데 감사일 기준 기간 밖인 행: **1건** (2521 국립망향의동산, 2026-08-27 ~ 2027-08-26).
  인증기간이 감사일 다음 날 시작한다. `certification_status_listed=VALID` 이지만
  `cert_valid_candidate=0`. VALID 227건과 감사일 유효 226건의 차이가 정확히 이 1건이다.
