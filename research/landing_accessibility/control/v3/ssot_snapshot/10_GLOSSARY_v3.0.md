# Glossary v3.0

| 용어 | 정의 |
|---|---|
| Cross-Service Task Entry Flow Divergence | 동일 생활과업을 서로 다른 서비스에서 수행할 때 위치·명칭·control·menu/reveal·sequence·depth·auth가 달라지는 구조적 차이. |
| CSEC | Cross-Service Entry Consistency. ‘일관성’ 관점의 개념명. 실제 분석은 divergence/variation을 직접 측정. |
| STFP | Structural Transfer Friction Proxy. 한 서비스의 조작지식이 다른 서비스로 전이되기 어렵게 만들 수 있는 구조적 재학습 요구의 proxy. 실제 인지부하 점수 아님. |
| Task Family | 서로 다른 서비스에 동일하게 적용할 사전 동결 생활과업 묶음. |
| Task Contract | task instruction, fixture, endpoint, auth rule, forbidden action을 포함한 수집 전 계약. |
| Matched Task | family 내 모든 서비스에 동일한 의미로 적용되는 비교 과업. |
| Task Flow | 서비스 자체 navigation/task 구조. forced dismissal 제외. |
| Experienced Flow | 실제 사용자가 겪은 경로. 필요한 popup dismissal 포함. |
| Action Sequence | 정규화된 ordered action token 열. Flow의 원자료. |
| Activation Depth | Flow에서 state-changing activation 수만 센 파생값. |
| Menu Dependency | task control이 바로 보이지 않고 reveal/menu action이 필요한지. Action Sequence에서 파생. |
| Visible Label | 사용자 화면에 실제 보이는 rendered text. |
| Accessible Name | 브라우저 AX naming computation이 계산한 보조기술용 이름. |
| Entry Zone | task entry control 위치의 요약 구역. 원 좌표 x/y도 함께 보존. |
| Reveal Direction | drawer/menu/sheet가 어느 방향에서 드러나는지. |
| AUTH_GATE | 사전지정 task path에서 인증이 불가피해지는 terminal. 로그인 버튼 단순 존재와 다름. |
| Task-specific Occlusion | popup/modal이 실제 task control bbox를 가리는 비율. |
| METHOD_QUALIFICATION_SET | 현재 12 diagnostic. 측정기 검증용이며 main effect sample이 아님. |
| USAGE_BENCHMARK_FRAME | 기존 59. broad robustness/development corpus. |
| SUBSTANTIVE MAIN FRAME | mobile-web precheck와 manifest freeze를 통과한 matched-task 50. |
| Legacy Archetype | QUERY/CONTENT_OPEN/ITEM_DETAIL/PLACE_LOOKUP/COMMUNICATION_ENTRY/FINANCIAL_ACTION_ENTRY/UTILITY_ENTRY. v3에서 metadata/codebook 역할. |
