# Flow Codebook v3.0

## 1. 핵심

Flow는 **ordered intentional action sequence**다. 같은 Depth라도 순서·menu/reveal·auth 위치가 다르면 다른 Flow다.

## 2. Canonical tokens

| Token | 정의 |
|---|---|
| OPEN_GLOBAL_MENU | 전역 햄버거/전체메뉴를 연다 |
| OPEN_LOCAL_MENU | 과업 영역 내부 메뉴/더보기를 연다 |
| SWITCH_TAB | 탭을 전환한다 |
| EXPAND_ACCORDION | 접힌 영역을 펼친다 |
| SELECT_CATEGORY | 과업 관련 카테고리/서비스군을 선택한다 |
| SELECT_FUNCTION | 사전지정 task 기능 control을 선택한다 |
| INPUT_QUERY | 검색어/번호/키워드를 입력한다 |
| SELECT_ORIGIN | 출발지를 선택한다 |
| SELECT_DESTINATION | 도착지를 선택한다 |
| SELECT_DATE | 날짜를 선택한다 |
| SUBMIT_QUERY | 검색/조회 control을 실행한다 |
| SELECT_RESULT | 결과 목록에서 항목을 선택한다 |
| OPEN_ITEM_DETAIL | 상품 상세를 연다 |
| OPEN_PLACE_DETAIL | 장소/기관 상세를 연다 |
| DISMISS_OBSTRUCTION | task path 진행에 필수인 방해요소를 허용된 닫기 control로 제거한다 |
| AUTH_GATE | 사전지정 task 경로에서 인증이 불가피해지는 상태에 도달한다 |
| ENDPOINT_REACHED | 사전정의 endpoint가 충족된다 |
| ABSTAIN | 증거 부족/다중 후보/경로 불확정으로 억지 판정하지 않는다 |

## 3. Task Flow vs Experienced Flow

- `task_flow_sequence`: `DISMISS_OBSTRUCTION`을 제외한 서비스 자체 task navigation.
- `experienced_flow_sequence`: 실제 진행에 필요했던 dismissal까지 포함.

예:

`task_flow = OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE`

`experienced_flow = DISMISS_OBSTRUCTION > OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE`

## 4. Measurement Variables

| Variable | Layer | Type | Definition |
|---|---|---|---|
| s0_task_control_visible | Surface | bool | 최초 viewport에서 사전지정 task 진입 control이 직접 보이는가 |
| first_visible_scroll_state | Surface | S0,S1,... | task 진입 control이 최초 관측된 scroll state. scroll은 activation depth에 포함하지 않음 |
| entry_x_norm | Geometry | 0~1 | task-entry control 중심 x 좌표를 viewport로 정규화 |
| entry_y_norm | Geometry | 0~1 | task-entry control 중심 y 좌표를 viewport로 정규화 |
| entry_zone | Geometry | categorical | TOP_LEFT/TOP_CENTER/TOP_RIGHT/MID/BOTTOM/FLOATING/DRAWER |
| entry_control_type | DOM/AX/Visual | categorical | TEXT_LINK/TEXT_BUTTON/ICON_TEXT/ICON_ONLY/TAB/BOTTOM_NAV/HAMBURGER/CARD/SEARCHBOX/LIST_ITEM/OTHER |
| entry_label_modality | DOM/AX/Visual | categorical | EXPLICIT_TEXT/ICON_TEXT/ICON_ONLY_AX_NAMED/ICON_ONLY_UNNAMED/HIDDEN_UNTIL_REVEAL |
| visible_label_text | Rendered | text | 사람 화면에 실제 렌더된 task control 문구 |
| accessible_name | AX | text | 브라우저 accessibility tree가 계산한 이름 |
| accessible_name_source | DOM/AX | categorical | VISIBLE_TEXT/ARIA_LABEL/ARIA_LABELLEDBY/LABEL/ALT/TITLE/VALUE/MIXED/NONE |
| label_relation | Derived | categorical | MATCH/SEMANTIC_EQUIV/DIFFERENT/VISIBLE_ONLY/AX_ONLY/NONE |
| nav_container_type | Flow | categorical | NONE/HAMBURGER/LEFT_DRAWER/RIGHT_DRAWER/TOP_DROPDOWN/BOTTOM_SHEET/MODAL_MENU/INLINE_EXPAND |
| reveal_direction | Flow/Geometry | categorical | NONE/LEFT/RIGHT/TOP/BOTTOM/CENTER/INLINE |
| menu_dependency | Derived | bool | action_sequence에 OPEN/REVEAL 계열 token이 endpoint 이전에 존재하는지 |
| nav_container_depth | Derived | count | task control 노출 전 menu/drawer expansion 수 |
| task_flow_sequence | Flow | ordered tokens | 서비스 자체 task 경로. forced dismissal은 제외 |
| experienced_flow_sequence | Flow | ordered tokens | 실사용자가 실제 거친 경로. forced dismissal 포함 |
| activation_depth | Derived | count | scroll/typing/passive wait/dismiss 제외 state-changing activation 수 |
| flow_step_count | Derived | count | task-intent action token 수. typing/submit/auth encounter 포함, scroll/passive load 제외 |
| auth_gate_stage | Flow | categorical | NONE/BEFORE_TASK_DISCOVERY/AFTER_TASK_SELECT/AT_ENDPOINT |
| forced_dismissal_count | Obstruction | count | task 진행에 실제 필요했던 dismissal 수 |
| task_control_occlusion | Obstruction | 0~1 | task-entry control bbox와 blocking obstruction의 실제 겹침 비율 |
| endpoint_status | Flow | categorical | REACHED/AUTH_GATE/PUBLIC_WEB_UNOBSERVABLE/APP_REQUIRED/EVIDENCE_DEFECT/BLOCKED/ABSTAIN |
| action_sequence_raw | Evidence | json | 각 step의 raw control role/name/text/bbox/state/url/evidence identity |

## 5. Derived 규칙

- `menu_dependency = 1` iff endpoint 전 OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION 등 reveal token 존재.
- `activation_depth`: state-changing activation token 수. scroll/typing/passive/dismiss 제외.
- `nav_container_depth`: task control 노출 전 nested reveal 수.
- `flow_step_count`: task-intent token 수. typing/submit/auth encounter 포함, scroll/passive 제외.
- `label_relation`: Unicode normalize + whitespace normalize 후 exact; 사전 고정 synonym map으로 semantic-equivalent를 별도 표시. embedding similarity만으로 자동 merge 금지.

## 6. Spatial zone

Normalized center `(x,y)`를 보존하고 zone은 요약값으로만 쓴다. 좌표 원자료를 버리지 않는다.

## 7. Accessible name

visible text와 AX computed name을 별개로 저장. CSS는 주로 표시/위치/visibility를 결정하며 accessible name 자체는 DOM/ARIA/AX naming computation의 결과다. pseudo-element text가 의미있는 label이면 rendered evidence로 별도 provenance를 남긴다.
