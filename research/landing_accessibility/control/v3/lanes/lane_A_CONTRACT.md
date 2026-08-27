# Lane A-CONTRACT — SSOTV3 task/endpoint/replacement/authority 계약 의미론 검토

세션 orchestrator HEAD: `ede241321b5b8599161d95a59bc38034590283e8`
검토 범위: SSOTV3/00·01·03·04·05 + `FINAL_MAIN50_MANIFEST.json` + `V3_0_1_SUCCESSOR_DELTA.md`
방법: byte 대조 아님. "문자로는 일관되지만 의미로는 성립하지 않는 지점"만 찾는다.

---

### Q1 endpoint 도달가능성의 비대칭 — F1 AUTH_GATE 구조적 단축

**관측**
- `00_SSOT_v3.0_CROSS_SERVICE_FLOW.md` §4 F1 endpoint 요지: "사용자가 이체/송금 경로를 선택한 뒤 task-specific transfer surface가 **열리거나 LOGIN/IDENTITY gate가 불가피하게 나타나는 최초 상태**." — F1만 endpoint 자체에 `OR AUTH_GATE` 분기가 내장돼 있다. F2~F5 endpoint 요지에는 이런 분기가 없다(예: F2 "개별 상품 상세면에서 상품명과 가격… 확인되는 최초 상태").
- `05_ANALYSIS_PLAN_v3.0.md` §5 Sensitivity 사전등록 항목은 F5 mode-stratum, temporal transition, app-required, evidence defect 4종뿐이다. F1의 AUTH_GATE 조기종료가 다른 family보다 sequence 관찰창을 구조적으로 짧게 만들 수 있다는 caveat는 목록에 없다.
- §2-E "Flow Topology"는 family별 sequence dispersion(고유 sequence 수, 정규화 편집거리)을 1차 산출물로 삼는다. family 비교는 "기술통계 중심"(§4)이라고만 완화돼 있을 뿐, F1의 짧은 dispersion이 "은행 UI가 실제로 덜 다양해서"인지 "endpoint 정의가 더 일찍 끊겨서"인지 분리하는 규칙은 없다.

**판정**: `GAP_FOUND`

**근거**: endpoint_contract가 family마다 "관찰이 멈추는 지점"의 성격을 다르게 정의한다(F1=조기 auth 허용, 나머지=결과면 도달까지 요구). 이것 자체는 task 의미상 정당하다(은행은 인증 없이 이체 surface에 못 감) — 그런데 이 비대칭이 05 §2-E의 "sequence divergence" 산출물 해석에 미치는 영향을 어디서도 명시적으로 분리하지 않는다. `endpoint_status`(REACHED/AUTH_GATE)와 `auth_gate_stage` 필드는 이미 수집되므로 사후 stratify는 가능하지만, 계약 문서 어디에도 "F1의 dispersion을 다른 family와 나란히 놓고 읽지 마라" 또는 "F1은 endpoint_status별로 분리 보고하라"는 사전등록 규칙이 없다. 이는 05 §7의 금지("접근성 지침 위반이다" 같은 과잉해석 금지)와 같은 층위의 위험 — 계약이 있는데도 정작 여기엔 없다.

**A 결정이 필요한 것**: 05 §5 Sensitivity 목록에 "F1 AUTH_GATE-truncated vs REACHED 분리 보고"를 사전등록 항목으로 추가할지, 아니면 F1의 짧은 dispersion을 cross-family 기술통계에서 아예 각주 처리할지 A가 명시해야 한다. (임계값/새 변수 신설 아님 — 이미 있는 `endpoint_status`/`auth_gate_stage`로 보고 방식만 결정하면 된다.)

---

### Q2 fixture의 서비스 간 적용가능성 — F4 지도서비스 vs 전문검색

**관측**
- manifest 실측: F4-01(건강보험심사평가원, 공공 전문검색)과 F4-06(네이버지도, 일반 지도검색)의 `fixed_fixture`와 `task_instruction`이 **글자 그대로 동일**하다 — `"지역=서울특별시 중구; 진료과/키워드=내과; 위치권한 허용 안 함"` / `"공식 모바일웹에서 고정 조건 '서울특별시 중구 내과'에 해당하는 의료기관을 찾는 검색 기능에 진입해…"`. `fixture_override`는 두 target 모두 빈 문자열이다.
- 대조: F5는 정확히 이 문제(mode마다 입력 형식이 다름 — 철도역 vs 공항)를 `fixture_override` 필드로 해결한다. `01_TASK_FAMILY_TARGET_FRAME_v3.0.md` §2: "mode별 출발/도착 지점은 target row의 fixture_override 사용." F5-01 실측 `fixture_override: "출발=서울역; 도착=부산역; 날짜=T+1; 성인=1"`.
- F4에는 이 메커니즘이 전혀 쓰이지 않는다. HIRA(구조화 드롭다운: 시/도→구→진료과 코드 선택형)와 네이버지도(자유텍스트 검색창)는 근본적으로 다른 입력 양식인데, 계약은 이를 같은 문자열 fixture로 "그대로 넣으라"고 요구한다.

**판정**: `GAP_FOUND`

**근거**: F5는 archetype 차이(철도역 vs 공항)를 이미 `fixture_override`로 흡수하는 선례를 만들어 놓고, F4는 archetype 차이(전문검색 드롭다운 vs 지도 자유검색)가 F5보다 결코 작지 않은데도 동일 메커니즘을 쓰지 않는다. 결과적으로 "지역=서울특별시 중구; 진료과=내과를 어떻게 입력에 반영할 것인가"는 각 target을 실제로 수집하는 collector/scout의 재량에 맡겨진다 — 03 §4가 "Rule/NLP/embedding을 후보 ranking 보조로 쓸 수 있으나 task label을 변경할 수 없다"고 하는 것은 control 탐색 규칙이지, fixture를 검색창에 어떤 문자열/절차로 밀어넣을지에 대한 규칙이 아니다. 이 조작화 격차(operationalization gap)는 "서비스 구조 차이"와 "collector가 fixture를 다르게 넣은 차이"를 혼동시킬 위험을 만든다 — 이는 정확히 00 §1이 말하는 "화면 title/text/domain을 보고 task 자체를 바꾸지 않는다"는 원칙의 반대편에 있는, 아직 규정되지 않은 자유도다.

**A 결정이 필요한 것**: F4의 10개 target(특히 F4-06/07/08 지도 3종 vs F4-01~05 전문검색 5종 vs F4-09/10 민간검색 2종)에 대해서도 F5식 `fixture_override`(또는 최소한 "지도형은 자유텍스트 '서울 중구 내과'로, 전문검색형은 구조화 필드로 넣는다"는 명시적 매핑 규칙)를 사전 동결할지 A가 결정해야 한다. 현재는 명시 규칙 없이 fixture 문자열만 동일하고 입력 절차는 미정의다.

---

### Q3 forbidden_actions 완전성

**관측**
- 프로그램적으로 50개 target 전체를 검사: `00_SSOT_v3.0_CROSS_SERVICE_FLOW.md` §6(credential 입력·login submit·본인인증 수행·CAPTCHA 해결/우회·거래 state-changing activation)과 `03_COLLECTION_MEASUREMENT_SPEC_v3.0.md` §7·§8(동일 auth/거래/CAPTCHA 항목)이 요구하는 9개 baseline 항목이 **50/50 target 전원**의 `forbidden_actions`에 문자 그대로 존재한다(스크립트 대조 결과: `NONE — all 50 have all 9 baseline items`).
- family별 추가 항목도 endpoint_contract의 family-specific 금지와 일치한다: F1은 "수취계좌·금액 입력"/"이체 실행", F2는 "장바구니 담기"/"구매하기·결제 control 활성화", F3은 "실사용 운송장/등기번호 입력"/"조회 submit", F4는 "예약"/"전화 걸기"/"외부 앱 실행"/"위치권한 허용", F5는 "좌석 선택"/"예약"/"결제" — 각각 00 §4 해당 family endpoint 요지의 금지 문구와 대응한다.

**판정**: `NO_GAP`

**근거**: 00 §6과 03 §7·§8이 요구하는 항목은 baseline 9종으로 환원되며, manifest는 이를 전 target에 균일하게 적용하고 family-specific 항목을 추가로 얹었다. 빠진 항목 없음. (참고: 00 §9의 프로세스 금지 — RF classifier 재결정, NLP fallback, replay 실패 시 자유탐색 대체, 결과 후 target 교체 — 는 이 3개 조항 범위 밖이며 `forbidden_actions` 필드가 다루는 층위(개별 target에서 하지 말아야 할 조작)가 아니라 수집기 운영 규칙 층위이므로 여기 없는 것이 결함이 아니다.)

---

### Q4 replacement 사유의 커버리지 — 5번째 사유 필요 여부

**관측**
- manifest `replacement_rule.allowed_reasons`: `APP_REQUIRED_EXCLUDE / NO_PUBLIC_MOBILE_WEB / DEAD_OR_INVALID_URL / PRECHECK_EVIDENCE_DEFECT`.
- 동일 필드의 `F5_reading`: "F5에서 서비스가 서울권→부산권 노선을 운행하지 않으면 그 과업을 수행할 공개 모바일웹 surface가 없는 것이므로 `NO_PUBLIC_MOBILE_WEB`으로 읽는다. 새 사유를 만들지 않는다."
- 그런데 `01_TASK_FAMILY_TARGET_FRAME_v3.0.md` §1 제외 조건은 **두 개**를 나란히 열거한다: "① 앱 설치/앱 전환만 강제하고 public mobile web task surface가 없는 경우" / "② **다른 서비스와 과업 의미가 근본적으로 달라 matched comparison이 성립하지 않는 경우**." ①은 APP_REQUIRED_EXCLUDE에 대응한다. ②는 "사이트는 살아있고 모바일웹도 있지만, 그 과업 의미 자체가 이 서비스에 대해 성립하지 않는 경우"를 가리키는 **별개 조건**이다.
- `03_COLLECTION_MEASUREMENT_SPEC_v3.0.md` §2의 precheck 결과 enum: `ELIGIBLE_PUBLIC_MOBILE_WEB / APP_REQUIRED_EXCLUDE / ACCESS_BLOCKED_REVIEW / URL_REMAP_REQUIRED` — 여기에도 `NO_PUBLIC_MOBILE_WEB`이라는 정확한 라벨은 없다. manifest의 `NO_PUBLIC_MOBILE_WEB`은 03 §2 enum의 어떤 값과도 문자 그대로 일치하지 않는 새로 만들어진 표현이다.

**판정**: `GAP_FOUND`

**근거**: A가 "노선 미운행"을 `NO_PUBLIC_MOBILE_WEB`으로 읽는 것은 **01 §1의 ①(채널 부재)과 ②(과업 의미 불성립)를 하나로 합치는 것**이다. F5 노선 미운행 사례는 실제로는 "사이트도 있고 모바일웹도 있는데, 그 서비스는 애초에 이 task(서울-부산 운행)를 제공하는 provider가 아니다" — 이는 채널(mobile web 존재 여부) 문제가 아니라 **task-provider match 문제**다. 01 §1이 이 둘을 별개 문장으로 구분해 놓았는데 replacement_rule의 4종 사유는 ②에 해당하는 이름을 갖고 있지 않다. Q4가 제시한 "서비스는 살아있고 모바일웹도 있는데 그 과업만 제공하지 않는 경우"는 정확히 01 §1의 ②이며, A는 이를 이름이 다른 ①(NO_PUBLIC_MOBILE_WEB, 채널 부재)로 흡수했다. 문자로는 "새 사유를 만들지 않는다"고 일관되지만, 의미로는 "채널이 없다"와 "이 서비스는 그 과업을 하지 않는다"가 서로 다른 부적격 사유임에도 하나의 라벨 아래 뭉쳐져 있다.

**A 결정이 필요한 것**: 다음 중 하나를 A가 명시적으로 선택해야 한다 — (a) `NO_PUBLIC_MOBILE_WEB`의 정의를 "이 서비스가 이 matched task를 수행할 수 있는 공개 모바일웹 surface가 없음"으로 **명문 확장**하여 01 §1 ①·② 둘 다 포괄한다고 문서에 명기, 또는 (b) 01 §1 ②를 위한 5번째 사유(예: `TASK_NOT_OFFERED_BY_SERVICE`)를 replacement_rule에 별도로 추가. 현재는 어느 쪽도 문서화되지 않은 채 F5 개별 주석 하나로만 실무 처리되고 있다.

---

### Q5 분모 사슬 — replacement가 어느 단계 숫자를 바꾸는가

**관측**
- `05_ANALYSIS_PLAN_v3.0.md` §6: "각 family에서: `candidate 10 → eligible/frozen 10 → attempted 10 → evidence-bearing n → flow-evaluable n`. 모든 분모를 단계별로 보고. replacement는 freeze 전에만."
- `V3_0_1_SUCCESSOR_DELTA.md` Δ2: replacement는 precheck 시작 전 동결된 순번 명부(`reserve_rank`)대로만 진행하며, "명부가 소진되면 해당 family를 n<10으로 보고한다. 임의 보충하지 않는다."
- manifest `replacement_reserve`에 F1 시중 4·지방 3, F2 6개 등 순번이 실제로 동결돼 있다.

**판정**: `GAP_FOUND`

**근거**: replacement는 "freeze 전에만" 일어나므로 사슬의 첫 단계 `candidate 10 → eligible/frozen 10` **내부에서** 흡수된다 — 그 결과 정상적으로 치환이 일어나도(명부 소진이 아닌 한) 사슬의 숫자는 10→10→10…으로 그대로 보여서 **치환이 있었다는 사실 자체가 표준 분모 보고에서 보이지 않는다**. 05 §6은 "모든 분모를 단계별로 보고"하라고만 하지, "몇 개 target이 원래 candidate에서 reserve로 치환됐는지"를 별도 투명성 지표로 보고하라는 요구가 없다. 이는 사소한 문제가 아니다 — 치환된 target(예: F1에서 수협은행 대신 카카오뱅크가 들어오는 경우 provider 성격이 인터넷전문은행으로 바뀜, F2에서 티몬 대신 컬리가 들어오면 오픈마켓→새벽배송 커머스로 archetype이 바뀜)은 matched comparison의 대표성에 영향을 줄 수 있는데, 이 정보가 최종 보고서의 분모 사슬 어디에도 명시적 자리가 없다. 데이터는 manifest에 남아있어(reserve_rank, 원래 01 §4 target 목록과의 diff) 사후 재구성 가능하지만, **05 §6의 표준 보고 스키마가 이를 요구하지 않는다.**
명부 소진 시나리오(Δ2 항목4)만은 자명하게 사슬에 `n<10`으로 드러난다 — 그 경로는 계약이 이미 커버한다.

**A 결정이 필요한 것**: 05 §6 분모 사슬에 `candidate 10 (of which replaced: k)` 같은 투명성 필드를 추가할지, 또는 family-level summary(05 §4)에 "치환 이력" 각주를 표준 항목으로 요구할지 A가 결정해야 한다.

---

### Q6 `AUTH_GATE`와 `ENDPOINT_REACHED`의 배타성

**관측**
- `04_FLOW_CODEBOOK_v3.0.md` §2 Canonical tokens: `AUTH_GATE` = "사전지정 task 경로에서 인증이 불가피해지는 상태에 도달한다", `ENDPOINT_REACHED` = "사전정의 endpoint가 충족된다" — 두 토큰은 **서로 다른 이름**으로 분리돼 있다.
- 같은 문서 §4 `endpoint_status` enum: `REACHED/AUTH_GATE/PUBLIC_WEB_UNOBSERVABLE/APP_REQUIRED/EVIDENCE_DEFECT/BLOCKED/ABSTAIN` — 여기서는 `ENDPOINT_REACHED`가 아니라 `REACHED`라는 **다른 문자열**을 쓴다.
- 00 §4 F1 endpoint 요지: transfer surface가 열리거나 **또는** AUTH_GATE가 불가피하게 나타나는 최초 상태 — F1만 endpoint_contract 문면에 AUTH_GATE를 "계약을 충족시키는" 대안 분기로 명시한다. F2~F5 endpoint 요지에는 이 분기가 없다.

**판정**: `NEEDS_A_DECISION`

**근거**: F1 내부에서는 정합적이다 — F1의 endpoint_contract가 AUTH_GATE를 명시적으로 "OR" 분기에 넣었으므로, F1에서 `endpoint_status=AUTH_GATE`는 계약 충족(=성공 termination)이고 `REACHED`(transfer surface가 실제로 열림)와 같은 층위의 "정상 종료"다. 문제는 **F2~F5**다. 이들의 endpoint_contract에는 AUTH_GATE 분기가 없으므로, F2~F5에서 로그인 벽에 막혀 `endpoint_status=AUTH_GATE`가 기록된 경우는 "계약이 충족된 성공"이 아니라 "endpoint에 도달하지 못하고 인증에 막힌 실패/차단"이어야 정합적이다. 그런데 00 §6은 family를 구분하지 않고 "사전지정 task path를 따라가다가 인증이 불가피해지는 최초 상태에서 AUTH_GATE terminal **허용**"이라고 일반 규칙으로 서술한다. 즉 **AUTH_GATE라는 하나의 enum 값이 F1에서는 "성공적 endpoint"를, F2~F5에서는 "endpoint 미도달"을 의미**하게 되는데, 이 family-dependent 이중 의미를 04 codebook이나 05 분석계획 어디에도 명시하지 않는다. 05 §6의 `flow-evaluable n`을 계산할 때 AUTH_GATE 종료 target을 포함할지 여부가 family마다 달라야 하는데 그 규칙이 없다. per-target `auth_rule` 필드(00 §5가 요구하는 필수 계약 필드)가 manifest 실측에 존재하지 않는 점도 이 family별 구분이 target 단위로 명문화되지 않았다는 정황과 맞닿아 있다(이 필드 부재 자체의 시비是비는 byte-대조 lane 소관이므로 여기선 정황 증거로만 사용).

**A 결정이 필요한 것**: F2~F5에서 `endpoint_status=AUTH_GATE`가 나올 경우 이를 (a) F1과 마찬가지로 "정상 종료"로 취급해 flow-evaluable에 포함할지, 아니면 (b) "endpoint 미도달 차단"으로 별도 분류해 flow-evaluable에서 제외할지 A가 family별로 명시해야 한다.

---

### Q7 secondary task의 분모 오염 위험

**관측**
- `00_SSOT_v3.0_CROSS_SERVICE_FLOW.md` §4 표본 해석: "F1의 잔액/계좌조회 secondary task는 같은 10개 은행 repeated task이며 본표본 n 증가로 세지 않음."
- `01_TASK_FAMILY_TARGET_FRAME_v3.0.md` §3: "이는 main n=50을 60으로 늘리는 것이 아니라 동일 provider의 within-provider repeated task다. **반드시 primary 송금 task와 별도 `task_id`로 저장한다.**"
- `05_ANALYSIS_PLAN_v3.0.md` §1: "Primary: `service × frozen task`. family n=10." — family 단위 분모는 `family_id` 기준으로 서술되고, secondary task도 F1의 `family_id`를 그대로 공유한다(같은 은행, 같은 family, 다른 `task_id`/다른 `frozen_task` 문자열).

**판정**: `GAP_FOUND`

**근거**: "별도 task_id로 저장한다"는 **저장 규칙**이지 **집계 규칙**이 아니다. family n=10을 계산하는 실제 mart 쿼리가 `family_id = 'F1'`로만 group-by하면 secondary task 10건이 자동으로 섞여 n=20이 된다. 이를 막으려면 쿼리가 `frozen_task`(또는 `matched_task`) 값까지 필터링해야 하는데, 이 요구사항이 00 §4/01 §3/05 §1 어디에도 명문 규칙으로 없다 — 있는 것은 "별도 task_id로 저장하라"는 수집 단계 지시뿐이다. `04_FLOW_CODEBOOK_v3.0.md`에도 `task_role: PRIMARY/SECONDARY` 같은 명시적 스키마 필드가 없다. 즉 계약은 "섞이지 않아야 한다"는 의도는 분명히 말하지만, "섞이지 않을 것을 보장하는 mart 필터/스키마 필드"는 어디에도 지정하지 않는다 — 저장 시점의 분리와 집계 시점의 분리 사이에 명시적 다리가 없다.

**A 결정이 필요한 것**: mart 스키마에 `task_role` 또는 동등한 필드를 필수화해 family-level 집계 쿼리가 이 필드로 primary만 필터링하도록 명문화할지, 아니면 `frozen_task` 문자열 자체를 집계 키에 포함하도록 05 §1을 개정할지 A가 결정해야 한다(단, 이는 새 측정변수 신설이 아니라 기존 데이터의 집계 방법 명문화임).

---

### Q8 `ABSTAIN`의 위치 — action token과 endpoint_status의 이름 충돌

**관측**
- `04_FLOW_CODEBOOK_v3.0.md` §2 Canonical tokens: `ABSTAIN` = "증거 부족/다중 후보/경로 불확정으로 억지 판정하지 않는다" — 이것은 action_sequence 안에 들어갈 수 있는 **token**이다.
- 같은 문서 §4 `endpoint_status` enum에도 정확히 같은 문자열 `ABSTAIN`이 categorical 값으로 존재한다.
- 대조: `AUTH_GATE`도 token(§2)이자 endpoint_status 값(§4)으로 **동일 문자열**이 양쪽에 쓰인다. 반면 `ENDPOINT_REACHED`(token, §2)는 endpoint_status에서는 `REACHED`(§4)로 **의도적으로 다르게** 표기돼 있다 — 즉 코드북 저자는 최소 한 쌍에서는 이름 충돌을 피했다.

**판정**: `GAP_FOUND`

**근거**: `ENDPOINT_REACHED` → `REACHED`로 개명한 전례가 있다는 것은, 코드북이 "token 층위 이름"과 "endpoint_status 층위 이름"을 **구분해야 한다는 것을 인식하고 있었다**는 뜻이다. 그런데 `AUTH_GATE`와 `ABSTAIN`은 그 개명을 받지 않고 두 층위에 동일 문자열로 남아있다. 실무적으로 `action_sequence_raw`(json, 각 step의 raw token 나열)를 파싱해 "이 target의 sequence에 ABSTAIN이 몇 번 등장하는가"를 세는 쿼리와, `endpoint_status = 'ABSTAIN'`인 target 수를 세는 쿼리는 **의미가 전혀 다르다**(전자는 시퀀스 내 임의 시점의 미확정 관측, 후자는 target 전체의 최종 결과 분류) — 그러나 이름이 같으므로 스키마를 잘 모르는 분석자가 컬럼을 착각해 `WHERE token = 'ABSTAIN'`과 `WHERE endpoint_status = 'ABSTAIN'`을 혼용할 여지가 있다. `AUTH_GATE`도 같은 구조의 위험을 갖지만, Q6에서 다룬 family-dependent 의미 문제와 결합하면 위험이 이중이다(이름도 겹치고, 의미도 family마다 갈린다).

**A 결정이 필요한 것**: 최소한 코드북 문서 수준에서 "token 층위 `ABSTAIN`/`AUTH_GATE`"와 "endpoint_status 층위 `ABSTAIN`/`AUTH_GATE`"가 서로 다른 컬럼/네임스페이스에 속함을 명시하는 주석을 04 §2 또는 §4에 추가할지, 혹은 `ENDPOINT_REACHED→REACHED`처럼 한쪽을 개명할지 A가 결정해야 한다. (개명이 아니라도 "같은 문자열이 두 층위에 존재하며 컬럼으로 구분된다"는 한 문장이 계약에 없다는 것 자체가 gap이다.)

---

## A 결정 대기 목록 (우선순위 순)

1. **Q4** — 01 §1의 두 제외 조건(①채널 부재/②task-provider match 불성립)이 replacement_rule 4종 사유에서 하나(`NO_PUBLIC_MOBILE_WEB`)로 뭉쳐 있다. 정의 확장 명문화 또는 5번째 사유 신설 필요.
2. **Q6** — F2~F5에서 `endpoint_status=AUTH_GATE`가 "성공(flow-evaluable 포함)"인지 "실패(제외)"인지 family별로 미정의. F1과 동일 취급 여부 결정 필요.
3. **Q7** — secondary task(F1 잔액조회)가 family-level mart 집계에서 자동 필터링될 스키마/쿼리 보장이 문서에 없음. `task_role` 필드 등 필요.
4. **Q5** — replacement가 candidate→frozen 전환에서 흡수돼 표준 분모 사슬(05 §6)에 드러나지 않음. 투명성 필드 추가 여부 결정 필요.
5. **Q2** — F4 지도서비스(F4-06/07/08) vs 전문검색(F4-01~05)의 fixture 조작화 절차가 F5식 `fixture_override`로 흡수되지 않고 미정의.
6. **Q1** — F1의 AUTH_GATE 조기종료가 만드는 구조적 짧은 dispersion을 05 §5 사전등록 sensitivity 목록에 넣을지 결정 필요.
7. **Q8** — `ABSTAIN`/`AUTH_GATE`가 token 층위와 endpoint_status 층위에 동일 문자열로 존재(단, `ENDPOINT_REACHED→REACHED`는 이미 개명 전례 있음). 문서 내 네임스페이스 주석 또는 개명 결정 필요.
