# C 검증 — T-B-BLK-003 (gate_observed 어휘 단독 오탐) @2281c85

**producer** C · 21:48 KST · raw 재계산(probe 58, batches 16)

## §1 코드 (T1)
- `gate_classifier.py:70-73` `_LOGIN_TEXT` = (로그인|아이디 찾기|비밀번호 찾기|비밀번호|회원가입|자동 로그인|sign in|log in|sign up) — B 목록에 **영문 3종 추가**로 실제 범위가 더 넓다.
- `:150-155` password_input 있으면 basis 추가, 어휘 매칭도 `login_vocabulary` basis 추가.
- `l1_engine.py:234-243 gate_observed`: `gate_kind is None` 이어도 `login_basis or identity_basis` 만으로 True. **어휘 단독으로 gate_observed=True 성립** — B 진술 CONFIRMED.

## §2 raw (L0-a 랜딩, activation 0)
n=58: `_LOGIN_TEXT` 매칭 **28** · password_input>0 **4** · 어휘만(구조 신호 0) **24** — B 수치와 정확히 일치. 예: samsungcard·band.us/about·m.daum·kbcard·samsungsvc·m.naver·google.com/chrome.

## §3 파일럿 AUTH_GATE 12건의 activation 수 (C 신규)
`detail.steps` 길이: **0 step = 8/12** (wtg_5beeafea·22ffba7a·dd2cec4c·8195b68a·8fd5d30f·a215c45b·efda6e0b·e67be795), 1 step = 2, 2 step = 2(그중 1 은 PAYMENT_GATE).
→ AUTH_GATE 12 중 **8 건은 activation 0 회에서 종료** = 랜딩 어휘만으로 gate 판정된 형태와 일치. B 가 "유력한 원인" 이라 한 것을 C 는 **8/12 가 0-step 종료라는 사실**로 뒷받침한다(개별 basis 는 미열람 — 8건 전부가 어휘 단독인지는 `notes` 의 basis 를 열어야 확정, 이월).

## §4 C 판단 (B requested_decision 에 대해)
1. 소유: `l1_engine.py`/`gate_classifier.py` 는 W2 소유이므로 **W2 scope 에 추가**가 자연스럽다(별도 worker 는 같은 파일 충돌). 단 joint gate 통과 조건에 명시.
2. 계약(A DECISION 필요, D-R0-03/04 의 논리적 귀결): `gate_observed` 는 (a) **chosen path 의 현재 state** 에서 (b) **구조 신호**(password/otp/identity/simple-auth provider 입력 또는 login form 이 primary surface 인 상태)가 있을 때만 True. 어휘는 candidate annotation(`login_control_present`) 으로만 기록하고 gate 판정·terminal 에 쓰지 않는다. `gate_kind None ∧ basis=vocab only` 는 gate 아님.
3. W1 은 fixture 우회 금지 — 동의. C 픽스처 `naver_like_login_plus_query.html`(로그인 링크 + 검색폼) 이 정확히 이 결함의 음성 대조군이며, 시정 후 `gate_observed=False`·QUERY area=True 여야 한다.
4. ORIGINAL_E001 판정은 수정하지 않는다(READ_ONLY). "AUTH_GATE 12 중 8 이 0-step" 은 파일럿 결함 기록으로 등재.

## §5 미확인
8건의 실제 gate basis 문자열(notes) · Scout 진행 중 state 에서의 오탐률 · 시정 후 재현(W2 completion 시 C 픽스처로 채점)
