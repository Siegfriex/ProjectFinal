# 쉬운 용어집 v2.0

| 용어 | 쉬운 뜻 |
|---|---|
| SSOT | 프로젝트에서 가장 우선하는 기준문서. 다른 문서와 충돌하면 SSOT가 우선 |
| CRISP-DM | 문제정의 → 데이터 이해 → 데이터 준비 → 분석/모델 → 평가 → 활용 순서의 데이터분석 방법 |
| IPOM-C | Input, Process, Output, Metric, Control. 각 작업을 무엇을 넣고, 뭘 하고, 뭘 만들고, 어떻게 확인하고, 무엇을 막을지로 쪼개는 방식 |
| Source Row | Wiseapp 원문 표의 한 행 |
| Measurement Entity | 원자료의 의미를 보존한 서비스 단위 |
| Web Target | 실제 모바일웹에서 검사할 공식 URL |
| L0 | URL에 처음 접속했을 때의 첫 화면/랜딩 |
| L1 | 대표기능의 첫 진입점까지만 가는 얕은 경로 |
| Representative Function | 그 서비스가 제공하는 대표적인 첫 기능 |
| Endpoint | “대표기능에 들어왔다”고 판단하고 멈추는 상태 |
| Business Domain | 금융, 쇼핑, 뉴스처럼 서비스의 사업/내용 유형 |
| Interaction Archetype | 실제로 사용자가 하는 행동의 유형. 검색, 콘텐츠 열기, 상품 상세 보기 등 |
| NED | 대표기능이 있는 영역까지 몇 번 눌러야 하는지 |
| IED | 그 영역에서 실제 endpoint까지 몇 번 더 눌러야 하는지 |
| MPFED | NED + IED. 대표기능 첫 진입까지의 최소 클릭/탭 깊이 |
| ExcessDepth | 같은 기능유형의 일반적인 깊이보다 몇 단계 더 깊은지 |
| KWCAG | 한국형 웹 콘텐츠 접근성 지침 |
| Criterion | KWCAG의 개별 검사 기준 |
| PASS | 기준 충족이 확인됨 |
| FAIL | 기준 미충족이 확인됨 |
| UNDETERMINED | 자료가 부족해 확정할 수 없음 |
| NA | 그 페이지에는 해당 기준을 적용할 대상 자체가 없음 |
| DOM | 브라우저가 이해하는 HTML 구조 |
| AX Tree | 스크린리더 등 보조기술이 읽는 접근성 구조 |
| Bounding Box | 화면에서 요소가 차지하는 사각형 위치와 크기 |
| Overlay | 화면 위를 덮는 팝업·모달 같은 요소 |
| Modal | 다른 작업을 하기 전에 닫거나 처리하도록 화면 위에 뜨는 대화상자 |
| Overlay Coverage | 최초 화면 중 popup 등이 차지한 면적 비율 |
| Primary Action Occlusion | 대표기능 버튼이 popup에 가려진 비율 |
| Forced Dismissal | 대표기능으로 가기 전에 반드시 popup을 닫아야 하는 행동 |
| Visual Clutter | 화면에 요소·링크·광고 등이 너무 많아 복잡한 정도 |
| Probe | 브라우저에서 색, 크기, 위치 등의 원시 측정값을 뽑는 코드 |
| Evidence | 판정의 근거가 되는 DOM, AX, screenshot, probe 등 |
| Evidence Manifest | 어떤 증거파일이 어느 관측에 속하는지 기록한 목록 |
| Provenance | 데이터가 어디서 왔고 어떤 과정을 거쳤는지에 대한 계보 |
| Append-only | 과거 증거를 덮어쓰지 않고 새 버전으로만 추가하는 방식 |
| VLM / MLLM | 이미지와 텍스트를 함께 이해하는 대형 멀티모달 AI |
| AI Reviewer | 애매한 화면/문맥을 정해진 라벨 중 하나로 분류하는 멀티모달 AI |
| Abstain | 확신할 수 없어서 억지로 분류하지 않는 것 |
| Human Final | 마지막에 사람이 직접 보는 극소수 사례. 최대 5건 |
| Gold Label | 실제 정답으로 신뢰하는 사람 라벨. 본 연구에서 WA 인증이나 AI 라벨을 gold truth라고 부르지 않음 |
| WA 인증 | 공인 웹접근성 품질인증. 외부 참조축으로 사용 |
| EDA | 데이터 모양·분포·이상치·관계를 먼저 살펴보는 탐색적 데이터분석 |
| Robustness | 일부 서비스가 빠져도 결과가 크게 흔들리지 않는지 확인하는 과정 |
| Spearman | 값 자체보다 순위가 같이 움직이는지 보는 상관계수 |
| Kruskal–Wallis | 여러 집단의 분포가 다른지 보는 비모수 검정 |
| Fisher Exact | 작은 표본에서 두 범주형 변수의 관계를 보는 검정 |
| Bootstrap | 데이터를 여러 번 다시 뽑아 결과가 얼마나 흔들리는지 보는 방법. 본 연구에서는 모집단 신뢰구간보다 안정성 확인 목적 |
| Gate | 다음 단계로 넘어가기 전에 반드시 통과해야 하는 조건 |
| P0 / P1 / P2 | 문제의 심각도. P0는 즉시 중단, P1은 현재 단계에서 해결, P2는 차단 여부에 따라 처리 |
| Promotion | 독립감사를 통과한 작업을 authoritative main 기준선으로 올리는 것 |
