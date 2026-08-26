# state/_invalidated — 폐기된 산출물 보존소

여기 있는 파일은 **어떤 용도로도 사용하지 않는다.** 삭제하지 않는 이유는 하나다:
무엇이 왜 폐기됐는지 추적 가능해야 하기 때문이다.

| 파일 | 무효 사유 |
|---|---|
| `category_feasibility_matrix.csv` | A7 `UNSOURCED_INCOMPATIBLE_PANEL_SET` 파생. 카테고리별 비교가능성 판정(TIER_C)이 오염된 모집단 위에서 계산됐다. |
| `service_certification_match_draft.csv` | 같은 A7 파생. panels 컬럼에 원문에 없는 패널명('월평균 사용자 Top10', '리테일 INDEX Top20')이 들어 있고, url 컬럼은 URL 증거 절차를 거치지 않았다. |

판정 근거: `sources/wiseapp/authority_manifest.json` → `legacy_asset_assessment`

두 파일 모두 첫 줄부터 `#` 주석 블록으로 무효 사유를 달았다. 주석 때문에 그냥 `pd.read_csv`
하면 깨진다 — 의도한 것이다. 데이터로 읽히면 안 되는 파일이다.

인증 결합은 C006 에서 새로 확보한 A2 스냅샷(`sources/certification/`)으로 다시 수행한다.
