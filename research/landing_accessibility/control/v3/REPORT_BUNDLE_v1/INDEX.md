# REPORT_BUNDLE_v1 — 무엇이 어디에 있는가

**보고서 본문**: `00_REPORT.md`

| 파일 | 내용 |
|---|---|
| `00_REPORT.md` | **읽을 것은 이것이다.** 결과 2층 · 라벨축 폐기 사유 · 결함 전파경로 · 검증하지 않은 것 |
| `V3_CENSUS_CLAIM_REGISTRY.json` | claim → metric → evidence hash. claims 5 · limitations 15 · method notes 25 |
| `V3_TIMEBOX_CENSUS_CLOSEOUT.json` | 실행 요약 · §11 계약 대조 · 다음 단계 권고 |
| `V3_REPRODUCIBILITY_MANIFEST.json` | 17 파일 sha · **replay 면제 고지** |
| `V3_TIMEBOX_CENSUS_1230.json` | REAL 실행 허가 release |
| `FINAL_MAIN50_MANIFEST.json` | 동결 프레임 v3.0.2 (무수정) |
| `figures/report_fig1~4.png` | ① acquisition state ② n=8 개별사례 ③ n=8 flow ④ measurement boundary |
| `data/CANONICAL_MART_50.csv` | 정본 mart 50행 27컬럼 |
| `data/EVIDENCE_MANIFEST.jsonl` | 수집 원장 85줄 · chain break 0 |
| `data/GEOMETRY_SUPPLEMENT_E.jsonl` | n=8 geometry 보충 (**evidence_hash 없음 — NOT_ASSURED**) |
| `assurance/` | C 독립 검산 3종 |

## 인용 규칙

- **`figures/report_fig1~4` 만 최종 그림이다.** 원 디렉터리의 `_superseded_do_not_cite/`에 있는 6장은 인용하지 마라
- 검증 근거 인용은 `assurance/` 세 파일의 sha로 한다
- `data/CANONICAL_MART_50.csv` sha256 = `5290e0c306ff7a11375f8da1ee0439e4a424559f18e7a6a662588e46be8f5caf`

## 이 번들이 주장하지 않는 것

`PUBLICATION_READY` **아니다.** §11 completion contract 11항 중 **3항이 여전히 미충족**이다 — canonical B runner offline regression 미실행 · canonical tables 0종 · D ML/robustness 폐기. 번들 구성만 이 문서로 충족됐다.
