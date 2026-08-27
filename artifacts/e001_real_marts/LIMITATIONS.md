# LIMITATIONS — E001

**스냅샷** 2026-08-27T15:33:02+09:00 (Asia/Seoul)

아래 항목은 **숨기면 안 되는 것**으로 등재됐다. 문장은 A 원문을 그대로 옮겼다 — 요약하거나 완화하지 않는다.

## 1. 로컬 추적 ref 위조 가능성 (미해소)

수집 개시 판정이 읽는 릴리스 문서 경로가 로컬 추적 ref 기반이며, 이는 로컬 쓰기 권한을 가진 행위자가 위조할 수 있다. 오늘 수집에서는 발사 직전 fetch 로 완화했다.

firewall이 릴리스 문서를 `git show origin/control/...`로 읽는데 `refs/remotes/origin/*`는 로컬 파일이라 `git update-ref`로 위조 가능하다. **V2-C015에서 승격 스크립트에 대해 시정한 것과 동일 결함 계열이며, 오늘은 완화했을 뿐 해소하지 않았다.**

## 2. `E000_PLAN` 부모 해시 재현 불가

E000_PLAN.json 의 e000_plan_hash_candidate 는 placeholder 바이트를 해싱한 뒤 덮어쓴 구조라 최종 산출물만으로 재현할 수 없다. 부모 계보는 parent_plan.commit_sha 로 검증되며, **해시 필드는 검증 기능을 갖지 않는다.**

## 3. `PROTOCOL_VERSION` 명명 부채

PROTOCOL_VERSION 문자열에 fixture 가 남아 있으나 이는 observation_id 안정성을 위해 유지된 것이며 **실행 종류를 나타내지 않는다.**

## 4. 반사실의 비무작위 배정 한계

무작위 배정이 아니다 — 가드 발화가 페이지 텍스트에 의존하므로 Scout이 돈 25건과 가드에 막힌 17건이 체계적으로 다를 수 있다. 뒷받침하는 근거는 두 집단의 archetype 구성이 유사하고(양쪽 ITEM_DETAIL 지배) Scout 쪽이 예외 없이 0/25라는 것이다. 확정하려면 가드를 고친 뒤 같은 프레임을 재수집해야 하고 오늘 하지 않았다.

따라서 회복 상한 8(정직한 범위 `0~8`)은 **현재 collector/measurement 구현 하에서의 조건부 값**이다. 이 값을 '올바른 task-definition wiring과 signal detector를 구현해도 depth는 최대 8'로 확대해 읽으면 **거짓이다.**

## 5. older-relevant 태깅은 연구진 판정이다

> KWCAG에는 '고령자 관련'이라는 공식 지정이 없다. 이 표는 외부 표준이 아니라 본 연구진(Claude A, Analysis Governor)의 판정이며, 다른 연구가 다르게 배정할 수 있다. KWCAG threshold 자체는 건드리지 않았다 — 이 표는 '어느 criterion을 분모에 넣는가'만 정한다.

1. 이 태깅은 외부 표준이 아니라 본 연구진의 판정이다. KWCAG에 공식 '고령자 관련' 지정은 없다. 배정 근거는 정본 문서 §2에 criterion 단위로 공개돼 있으며, 다른 배정이 가능하다.
2. 데이터 관측 이전에 동결됐다 (2026-08-27 12:25 KST, REAL TARGET evidence 0건 상태).
3. 청각 도메인이 어휘에 없다. 노인성 난청은 실재하는 노화 변화지만 본 프로토콜이 청각 접근을 측정하지 않아 `1.2.1`이 `OTHER`로 분류됐다. 청각 장벽의 부재를 뜻하지 않는다.
4. `NOT_AUTOMATABLE`로 인해 태깅된 22개 중 실제로 판정되는 것은 그보다 훨씬 적다. `EligibleOlderRelevant`·`undetermined_n`·`undetermined_rate`를 반드시 병기한다.
5. 서비스별 `EligibleOlderRelevant_i = 0`인 경우 `FailRate = NULL`이며 그 건수를 보고한다.

## 6. E000 batch-0 재사용 무효 — 분석 표본이 아니다

분석 표본은 `E001_FULL`만이다(Claude A 판정). E000은 고유 서비스를 0건 기여하고 측정기가 다르므로(E000 a86b4c7 / E001 222ef2c) 한 기술통계에 섞지 않는다 — 이득 0, 위험만 있다. E000은 측정기·evidence lineage 검증 산출물로만 보고한다.

collector SHA가 상이하므로(E000 `a86b4c7` / E001 `222ef2c`) E000 6건은 **분석 표본이 아니라 측정기·evidence lineage 검증 산출물**이다.

## 7. E000 `§1-2` FAIL 예외 등재

E000이 `MART_ACCEPTANCE §1-2`(`observation_id` 유일·NULL 0·중복 0) 기준을 충족하지 못했다. **기준을 재해석해 통과시키지 않고 예외로 등재한다** — 미충족을 충족으로 바꾸는 재해석은 기준 자체를 무효화하기 때문이다. E000은 위 6항에 따라 분석 표본이 아니므로 이 예외가 분석 결과에 들어가지 않는다.

## 8. 축 C 47% 미분류

축 C는 **'완전 측정'이 아니라 'raw 실측 + 분류 절반 미완'**이다. interrupt 분류기도 결정론 규칙만 돌고 semantic/VLM 단계가 없어(축 A·B와 같은 skeleton 구조) `final_label`의 최대 범주가 `UNKNOWN`이다. 유형 분포를 인용할 때 UNKNOWN을 각주로 빼면 실측 강도가 과대표시된다.

`final_label`이 `UNKNOWN`인 것이 110건(46.8%)으로 최대 범주다. 유형 분포를 인용할 때 이 값을 각주로 빼지 않는다.

## 9. `NOT_AUTOMATABLE`로 인한 `EligibleOlderRelevant` 축소

`NOT_AUTOMATABLE`로 인해 태깅된 22개 중 실제로 판정되는 것은 그보다 훨씬 적다. `EligibleOlderRelevant`·`undetermined_n`·`undetermined_rate`를 반드시 병기한다.

오늘은 축 A가 평가되지 않아 이 축소가 실제 값으로 나타나지도 못했다 — 분모 자체가 산출되지 않았다.

## 10. `DUPLICATE_AUTOMATED_REQUESTS_TO_REAL_HOSTS`

발사 명령 중복 투입으로 두 차례에 걸쳐 실제 서비스 호스트 7곳에 중복 자동요청이 발생했다. 데이터 무결성에는 영향이 없으나(중복 run 은 격리·미참조), 대상 서버에 불필요한 부하를 준 사실을 기록한다.

E000_FAST 에서 발사 명령 중복으로 두 수집 프로세스가 동시에 실행되어 실제 호스트에 중복 요청이 나갔다. 참조되지 않은 3개 run 은 CONCURRENT_LAUNCH_SUPERSEDED 로 격리했으며 분석에 쓰지 않는다.

**세 지점이 모두 기여했다** — 명령 전달 방식 자체가 중복에 취약했다.

| 주체 | 기여 |
|---|---|
| A | 발사 명령을 여러 차례 제시했다 (E000) |
| B | 4워커 명령을 한 덩어리로 전달해 워커별 성공 확인이 어려웠다 (E001 w02) |
| Director | 오타 복구 재실행 (`--worker01` 붙여쓰기 · `ccd` 오타 → Exit 1 후 재시도) |

배타 생성 가드가 두 번 다 막았고 데이터 무결성 영향은 0이다. 그러나 **실제 상용 호스트 7곳에 중복 요청이 나간 사실은 남는다 — 데이터가 오염되지 않았다고 없던 일이 되지 않는다.** 이 항목은 검증 실수가 아니라 오케스트레이션 실수이므로 STATS §4.5의 검증 실수 표에 포함하지 않는다.
