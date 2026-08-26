# Landing Accessibility — 문서 인덱스

**현행 실행권위는 `docs/v2/` 다.** 권위 서열의 정본은 `docs/v2/EXECUTION_AUTHORITY.md`,
Gate의 정본은 `docs/v2/PHASE_GATES.md`.

이 파일이 **읽기 순서의 정본**이다. `docs/v2/README.md`는 원본 pack의 읽기 안내로
비권위이며 설치 후 경로와 어긋나는 부분이 있다(해당 파일 배너 참조).

## Current (v2)

| 순위 | 파일 | 역할 |
|---|---|---|
| 1 | `v2/00_SSOT_v2.0.md` | **최상위 실행권위.** 목표·범위·단위·해석 |
| 2 | `v2/01_DATA_SPEC_v2.0.md` | 데이터 표·변수 |
| 3 | `v2/02_COLLECTION_MEASUREMENT_SPEC_v2.0.md` | 수집·측정·정지조건 |
| 4 | `v2/03_CRISP_DM_EXECUTION_PLAN_v2.0.md` | 분석 단계·Phase |
| 5 | `v2/04_GLOSSARY_v2.0.md` | 용어 |
| 6 | `v2/05_REPO_ORCHESTRATION_PLAN_v2.0.md` | Git·감사 운영 |
| 7 | `v2/PHASE_GATES.md` | Gate 이름·통과조건·판정권한 |
| 8 | `v2/A1_MEASUREMENT_OPERATIONALIZATION.md` | 측정 조작화 (NED/IED 경계·episode·dismiss 절차·scout budget·primary action identity·L0 evidence 슬롯) |
| 9 | `v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md` | 상태값 어휘·품질지표 산식·논리↔물리 스키마 대응 |
| 10 | `07_EVIDENCE_MANIFEST_CONTRACT.md` | evidence identity / manifest 계약 (v1 산물, **현행 유효**) |
| — | `../CLAUDE.md` | 프로젝트 컨텍스트 (`PROJECT_CONTEXT_DERIVED`) |
| — | `v2/EXECUTION_AUTHORITY.md` | 권위·supersede·부채승계·기준선 선언 |
| — | `v2/INSTALL_MANIFEST.json` | 설치본 무결성 앵커 |

`08`부터 시작하는 새 v2 보충명세는 `A`-접두 번호를 이어 붙인다.

## 비권위

| 파일 | 지위 |
|---|---|
| `v2/README.md` | `NON_AUTHORITATIVE_READING_GUIDE` |
| `v2/bootstrap/07_CLAUDE_FIRST_SESSION_PROMPT_v2.0.md` | `NON_AUTHORITATIVE_BOOTSTRAP_RECORD`. 실행규칙 근거로 인용 금지 |

## Superseded / 역사 자료

v1 실행지침·인계문서는 `control/landing-orchestrator` 브랜치에 보존돼 있으며 이 브랜치에는
없다. 지위는 `v2/EXECUTION_AUTHORITY.md` §3 표를 따른다. **삭제·이동하지 않는다.**

supersede는 선언만으로 성립하지 않는다 — 해당 브랜치의 인계문서가 실제로 v2로 라우팅해야
실효를 갖는다(`EXECUTION_AUTHORITY.md` §3).

## 검증

```bash
python research/landing_accessibility/scripts/verify_v2_docs.py
pytest tests/test_v2_docs_integrity.py -q
```
