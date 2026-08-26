# 파이럿 R1–R4 종료 보고 — 원격 커밋 기준 실측 대조

**문서 목적** 원격 어드바이저가 GitHub `research/refcohort-r1` 브랜치만 보고 내린 진단에 대해,
로컬에서만 관측 가능한 사실을 붙여 의사결정을 지원한다.
이 문서는 작업 내역이 아니라 **파이럿의 시행착오 결과와 그로부터 확정된 제약 조건**을 기록한다.

| 항목 | 값 |
|---|---|
| 원격 HEAD | `32460b87334a67f6a74823ac55f85ca80a9f8980` (`research/refcohort-r1`) |
| 로컬 HEAD | 동일 — **커밋 격차 없음** |
| 로컬 워킹트리 미커밋 | `CLAUDE.md`, `tsconfig.json` 수정 / `manus/`, `ts/` 미추적 (모두 refcohort와 무관) |
| 작성 시각 | 2026-08-26 |
| 코드 규모 | 파이썬 11파일 2,129줄 + `probe.js` 364줄 |
| 품질 게이트 | `ruff check` 통과 · `pytest` 9건 통과 · `ruff format` 1건 미준수(`src/refcohort/__init__.py:2`) |

---

## 0. 어드바이저가 원격에서 볼 수 없는 것 — 먼저 읽을 것

원격 저장소는 **판정 결과만** 담고 있고 **원증거는 담고 있지 않다.**
`.gitignore` 하단이 이를 명시적으로 배제한다.

```gitignore
# ── 연구 run 산출물 (증거는 로컬 보존, 레코드만 추적) ──
/research/refcohort/runs/*/dom/
/research/refcohort/runs/*/screen/
/research/refcohort/runs/*/ax/
/research/refcohort/runs/*/probe/
```

따라서 원격에서 보이는 `runs/r*/records.jsonl`과 `report.json`은 **로컬 원증거를 근거로 만들어진 파생물**이며,
원격만으로는 그 파생 과정을 검증할 수 없다.

| 자산 | 원격 | 로컬 | 비고 |
|---|---|---|---|
| `runs/r1/{dom,ax,screen,probe}` | 없음 | 231×4 = 322MB | R1 원증거 |
| `runs/r2/{dom,ax,screen,probe}` | 없음 | 238×4 = 332MB | **R3·R4 판정의 실제 입력** |
| `runs/r1-pilot`, `runs/smoke` | 없음 | 9MB | 초기 검증 |
| `runs/*_measure.log` | 없음 (`*.log` 제외) | 있음 | 실행 타임스탬프·진행 로그 |
| 감사 워크플로 저널 | 없음 | `~/.claude/projects/…/workflows/wf_2b52c7fd-81d.json` 540KB | §2-A 참조 |

**결론: 원증거 682MB는 단일 로컬 머신에만 존재하며 백업이 없다.** 이것이 현재 재현성의 실질적 상한이다.

---

## 1. 어드바이저 진단 대조표

| # | 어드바이저 지적 | 실측 결과 | 판정 |
|---|---|---|---|
| 1 | 감사기록 관리 30/100, `/tmp` 의존이 치명적 | 저장소의 `audit/*.json`은 실제로 `[]` 빈 배열. 그러나 원본은 `/tmp`가 아니라 `~/.claude/projects/…/workflows/wf_2b52c7fd-81d.json`에 **확정 18건 전문이 온전히 보존**돼 있다 | **부분 정정** — 손실 아님, 복구 가능 |
| 2 | R2 원수집 257 측정 = 녹색 | 레코드는 257이나 **증거 파일은 238개**. 실사용군 41건 중 30건이 6개 파일로 상호 덮어씀 | **정정 — 녹색 아님** |
| 3 | 실사용군 평균 5.90 = 노란색(조건부 사용 가능) | R3·R4는 `rejudge.py`가 **디스크 증거를 다시 읽어** 판정한다. 실사용군 30건은 다른 사이트 증거로 판정됨 | **정정 — 빨간색** |
| 4 | `criterion_table`이 두 코호트 합산 | 사실. `report.py:26`이 `_measured(records)` 전체를 받는다. 코호트 분리 시 방향이 뒤집히는 항목 존재 (§4-3) | **확인** |
| 5 | UNDETERMINED가 PASS로 흡수 | 사실. `criteria.py:80` 한 줄. 실측 60건, 전부 1.4.3 (§4-4) | **확인 · 정량화** |
| 6 | `criteria_fail`에 AUTO_FLAG 혼입 | 사실. `criteria.py:681-682`. REFERENCE 3.54 = 확정 2.67 + 신호 0.88 (§4-5) | **확인 · 정량화** |
| 7 | 과업분류 35/100, `PUBLIC`은 주체지 과업 아님 | 사실. `targets.py:78`이 서비스명과 기관명을 한 문자열로 합쳐 매칭 | **확인** |
| 8 | Interaction evidence는 과장 | 사실. `collect.py`에 클릭·키 입력 코드 없음. 플래그명만 `evidence_complete` | **확인** |
| 9 | "7개는 모바일웹 자체가 없다" 검증 필요 | 실사용군 미측정 7건 중 `NO_URL`은 **1건(원기날씨)**. 나머지 6건은 전송 실패·증거 부족 | **확인 — 현 REPORT.md 서술 오류** |
| 10 | "1년간 아무도 다시 확인하지 않는다" 낮춰야 함 | 사실. `reports/legal_basis.md`는 "재측정 조항을 찾지 못했다"까지만 근거함 | **확인** |
| 11 | append-only 미강제 | 사실. `guard.py:168` `check_append_only`가 정의만 되고 호출부 없음. `pipeline.py:106`이 `"w"` 모드 | **확인** |
| 12 | 중복 endpoint 이중계상 | 사실. final_url 정규화 기준 **7그룹 14레코드**, 전부 REFERENCE (§4-6) | **확인 · 정량화** |
| — | *(어드바이저가 알 수 없었던 것)* | **증거 파일명 충돌 → R3·R4 실사용군 판정 오염** | **신규 CRITICAL** |

---

## 2. 파이럿이 확정한 것 — 그대로 승계할 자산

### 2-A. 적대적 감사 워크플로는 실행됐고 기록이 남아 있다

원격에는 `audit/r1_findings_raw.json`과 `r1_confirmed_findings.json`이 `[]`로 커밋돼 있어
어드바이저가 "감사기록 30/100"으로 평가한 것은 원격 기준으로 정당하다. 그러나 실제 실행 기록은 존재한다.

```
runId    wf_2b52c7fd-81d
status   completed
agents   225        durationMs 1,882,074 (31.4분)
tokens   6,289,825  toolCalls 1,985
결과     발견 73건 → 확정 18 / 기각 55 / synthesize 단계 실패(queue=null)
```

구조는 `Audit(5차원) → Refute(발견당 3렌즈) → Synthesize`였고, 5차원은
`criteria-fidelity` · `probe-coverage` · `classification-validity` · `contract-drift` · `article-readiness`다.

**시행착오 1 — 생존 판정식이 미검증을 기각으로 흡수했다.**

```js
survives: v.length > 0 && refutedCount < Math.ceil(v.length / 2)
```

반증 에이전트가 세션 한도로 죽어 `v.length === 0`이 되면 발견이 자동 기각된다.
확정 18건 중 `no-codebook-no-validation-for-classifier`는 `votes=1`로 살아남았다 —
3표 중 2표가 죽은 것이다. **따라서 "기각 55건"은 반증된 55건이 아니라 미검증이 섞인 55건이다.**

재실행 시 판정식은 `votes === 0 → UNVERIFIED`로 분리해야 하며, 기각과 같은 버킷에 넣으면 안 된다.

**시행착오 2 — 에이전트 수를 늘려도 종합 단계가 실패하면 산출물이 0이다.**
225개 에이전트가 31분간 629만 토큰을 쓰고도 시정 큐는 생성되지 않았다.
확정 발견은 저널의 `result.confirmed_findings` 배열에서 직접 꺼내야 한다.

### 2-B. 모집단 구축 방식 — 유지

키워드 검색(78→15건, 5개 유형 0건)에서 공식 목록 230페이지 전수 크롤로 전환했다.
`discovery.py:79`의 종료 조건이 세 가지(`TRANSPORT_OR_STATUS` / `NO_CARDS` / `DUPLICATE_PAGE`)로
명시돼 있어 크롤 중단 사유가 `crawl_summary.json`에 남는다.

```
인증 이력 2,283건 → 목록 상태 VALID 227 / EXPIRED 2,056 → 감사일 기간 내 226건
```

`VALID 227`과 `감사일 기준 226`의 1건 차이는 `discovery.py:161`의
`in_period_at_audit` 판정에서 갈린다. 두 수치를 혼용하면 안 된다는 어드바이저 지적은 코드상 근거가 있다.

### 2-C. 자기교정 4건 — 방법론적 자산

| 항목 | 최초 | 시정 후 | 원인 |
|---|---:|---:|---|
| 1.2.1 자막 | 100% 미흡 | 적용 27→3건 | FAIL 51건 중 49건이 음소거 배경영상 |
| 2.2.2 정지기능 | 100% 미흡 | 미흡 0건 | 전부 로딩 스피너·스크롤 유도 |
| 1.4.3 명도대비 | 93.7% | 74.9% | 실패 6,400건 중 2,887건이 `ratio=1` |
| 2.1.3 조작 가능 | 89.8% | 41.0% | WCAG 2.5.8 차용(최소변 24px) → KWCAG 해설서(대각선 6mm) |

2.1.3 시정은 `criteria.py:26-32`에 근거 원문이 주석으로 박혀 있다.

```python
# KWCAG 2.2 해설서 2.1.3 체크사항:
#   "CSS의 픽셀 크기를 기준으로 대각선 길이 6mm 이상으로 구현해야 합니다. …"
CSS_PX_TO_MM = 25.4 / 96.0
TARGET_DIAGONAL_MIN_MM = 6.0
TARGET_DIAGONAL_MIN_CSS_PX = TARGET_DIAGONAL_MIN_MM / CSS_PX_TO_MM  # ≈ 22.68 px
```

경계 검증(17×17 → 6.36mm PASS / 16×16 → 5.99mm FAIL)이 해설서의 "약 17px" 서술과 일치한다.
**이 패턴(원문 인용 → 상수화 → 경계 검증 → 재판정)이 나머지 고위험 항목에 반복 적용할 템플릿이다.**

### 2-D. 재판정 경로 — 유지하되 전제 조건 있음

`rejudge.py`는 사이트에 재요청하지 않고 판정만 다시 한다. R3·R4가 이 경로로 만들어졌다.

```python
ref = r.get("probe_ref")
if r.get("collection_status") == "MEASURED" and ref and Path(ref).exists():
    probe = json.loads(Path(ref).read_text(encoding="utf-8"))
    j = judge(probe)
```

설계는 옳다. **그러나 디스크 증거의 무결성을 전제한다.** 이 전제가 §3에서 깨진다.

---

## 3. 신규 CRITICAL — 증거 파일명 충돌과 R3·R4 오염

### 3-1. 원인

`collect.py:194` 한 줄이다.

```python
safe = re.sub(r"[^A-Za-z0-9_.-]", "_", record_id)
```

`targets.py:139`가 실사용군 `record_id`를 서비스명으로 만든다.

```python
record_id=f"CMP:{re.sub(r'[^0-9A-Za-z가-힣]+', '_', name)[:40]}",
```

즉 `record_id`에는 한글이 남고, 파일명 생성에서 그 한글이 전부 `_`로 치환된다.
**글자 수가 같은 서비스는 같은 파일명이 된다.**

```
CMP___       ← 밴드 · 당근 · 티맵 · 토스 · 다음 · 틱톡 · 퀸잇 · 테무   (8건)
CMP____      ← 유튜브 · 네이버 · 이마트                              (3건)
CMP_____     ← 카카오톡 · 홈앤쇼핑 · 다음메일 · 홈플러스 · 코스트코 · 롯데마트 (6건)
CMP______    ← 인스타그램 · 롯데홈쇼핑 · 현대홈쇼핑 · 똑똑계산기 · … (9건)
CMP_______   ← 네이버_지도 · 신세계백화점                            (2건)
CMP__________← 네이버_네이버페이 · 레브잇_올웨이즈_                    (2건)
```

디스크에 남은 실제 내용은 마지막에 기록한 프로세스의 것이다.

```
runs/r2/probe/CMP___.json      → url = https://www.temu.com/
runs/r2/probe/CMP_____.json    → url = https://www.lotteon.com/m/display/main/lotteon
runs/r2/probe/CMP____.json     → url = https://m-emart.ssg.com/
```

참조군은 `REF:2451` → `REF_2451`로 인증번호가 살아남아 **영향이 없다.**

### 3-2. 영향 범위

| | R1 | R2 |
|---|---:|---:|
| MEASURED 레코드 | 253 | 257 |
| 실제 증거 파일 | 231 | 238 |
| 충돌로 소실 | 22 | 19 |
| 충돌 영향 레코드 | — | **30건 (전부 COMPARISON, 41건 중 73%)** |

- **R1·R2의 판정 수치 자체는 유효하다.** `pipeline.py:65`가 수집 직후 메모리의 `res.probe`로 판정하기 때문이다.
- **R3·R4는 오염됐다.** `rejudge.py`가 디스크에서 읽으므로 30건이 남의 증거로 판정됐다.
- **R1·R2의 증거 추적도 불가능하다.** 실사용군 레코드의 `probe_ref`·`dom_ref`·`screen_ref`가 가리키는 파일은 다른 사이트의 것이다.

### 3-3. 데이터에 이미 남아 있던 증상

R3는 2.2.2 과탐만 제거한 재판정이므로 미흡이 줄어야 했다. 실제로는 실사용군이 **늘었다.**

| | R2 (수집 직후 판정) | R3 (디스크 증거 재판정) |
|---|---:|---:|
| COMPARISON 평균 미흡 | 5.63 | **6.46** |
| COMPARISON 미흡 지점 | 2,161 | **3,513** |
| COMPARISON 적용기회 | 24,235 | **25,574** |

레코드 단위로 1.1.1 적용기회가 22건에서 달라졌다.

```
CMP:유튜브     r2=2   → r3=92
CMP:현대홈쇼핑  r2=76  → r3=11
CMP:네이버_지도 r2=4   → r3=31
```

### 3-4. 오염 제외 시 실사용군

```
전체 41건        평균 미흡 5.90  (min 3 / max 8)
충돌 제외 11건    평균 미흡 5.09  (min 3 / max 7)
REFERENCE 216건  평균 미흡 3.54  ← 오염 없음
```

**실사용군에서 오염되지 않은 표본은 11건이다.** 이 규모로는 집단 수치를 산출할 수 없다.
어드바이저의 "실사용군을 맥락군으로 격하" 권고는 통계 설계상으로도 옳지만,
**현 시점에서는 격하 이전에 재수집이 선행돼야 한다.**

---

## 4. 어드바이저 지적의 정량화

### 4-1. 미측정 17건 전수 — "모바일웹이 없다"는 1건뿐

```
[REF] 서울바이오허브          EVIDENCE_THIN
[REF] 한국학사서 글로벌 네트워크  EVIDENCE_THIN
[REF] 사서지원서비스          EVIDENCE_THIN
[REF] 국립중앙도서관          EVIDENCE_THIN
[REF] 저작권 배움터           EVIDENCE_THIN
[REF] 키움예스저축은행         TRANSPORT_FAILURE
[REF] 시각장애인업무지원시스템    TRANSPORT_FAILURE
[REF] 하티오더               TRANSPORT_FAILURE
[REF] 대한항공               TRANSPORT_FAILURE
[REF] 생태계 기후대응 통합정보관리 TRANSPORT_FAILURE
[COM] 쿠팡                  EVIDENCE_THIN        ← 403 봇차단
[COM] 캐시워크 / Bill Letter / 삼성월렛 / 이마트 트레이더스 / 대한항공  TRANSPORT_FAILURE
[COM] 원기날씨               URL_DISCOVERY_REQUIRED  ← 유일한 NO_URL
```

현 `REPORT.md` 부록의 "실사용 상위 48개 중 7개는 모바일웹 자체가 없다"는 **레코드와 일치하지 않는다.**
`NO_URL`은 1건이고, 나머지 6건은 접속 실패·증거 부족이다. 이 문장은 삭제하거나 재검증 후 재작성해야 한다.

또한 **대한항공이 REFERENCE와 COMPARISON 양쪽에 존재**한다 — 코호트 배타성이 보장되지 않는다.

### 4-2. `criteria_fail`의 자동화 등급 분해

`criteria.py:681-682`가 두 등급을 구분하지 않는다.

```python
applicable = [r for r in results.values() if r["verdict_state"] not in (NA, UNDET)]
fails = [r for r in applicable if r["verdict_state"] == FAIL]
```

실측:

| 코호트 | n | 평균 FAIL | 기계 확정 | 사람 검토 필요 | FAIL 0건 | 확정 FAIL만 0건 |
|---|---:|---:|---:|---:|---:|---:|
| REFERENCE | 216 | 3.54 | **2.67** | 0.88 | 12 | **20** |
| COMPARISON* | 41 | 5.90 | 4.27 | 1.63 | 0 | 0 |

\* 오염 포함 수치이므로 참고용

**"미흡 0건 12곳"은 기계 확정 기준으로는 20곳이다.** 어드바이저가 요구한 세 갈래 분리
(`machine_confirmed_fail` / `review_required_flag` / `undetermined`)는 기존 필드로 산출 가능하며
재측정이 필요 없다.

### 4-3. 코호트 분리 `criterion_table` — 합산이 방향을 뒤집는 항목

`report.py:26`이 전체를 받는다. 코호트를 분리하면 다음과 같다.
(CTX = 실사용군 중 오염되지 않은 11건. 분모가 작아 참고용)

| 항목 | 이름 | 등급 | REF 적용 | REF 미흡 | **REF 미흡률** | CTX 적용 | CTX 미흡 | 현행 합산 미흡률 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 1.4.2 | 자동 재생 금지 | DECIDABLE | 11 | 10 | **90.9%** | 1 | 0 | 83.3% |
| 1.4.3 | 텍스트 명도 대비 | DECIDABLE | 211 | 150 | **71.1%** | 10 | 10 | 74.9% |
| 2.5.3 | 레이블과 네임 | DECIDABLE | 71 | 46 | **64.8%** | 3 | 3 | 73.4% |
| 4.2.1 | 웹앱 접근성 준수 | DECIDABLE | 161 | 84 | **52.2%** | 9 | 7 | 58.5% |
| 3.3.2 | 레이블 제공 | DECIDABLE | 89 | 42 | **47.2%** | 2 | 1 | 39.8% ↓ |
| 2.1.3 | 조작 가능 | DECIDABLE | 215 | 92 | **42.8%** | 11 | 3 | 41.0% |
| 2.4.3 | 적절한 링크 텍스트 | FLAG_ONLY | 215 | 91 | **42.3%** | 11 | 7 | 43.4% |
| 2.4.2 | 제목 제공 | DECIDABLE | 216 | 60 | **27.8%** | 11 | 6 | 33.1% |
| 4.1.1 | 마크업 오류 방지 | DECIDABLE | 216 | 47 | **21.8%** | 11 | 7 | 21.8% |
| 2.4.1 | 반복 영역 건너뛰기 | DECIDABLE | 216 | 35 | **16.2%** | 11 | 4 | 16.7% |
| 1.3.2 | 콘텐츠의 선형구조 | FLAG_ONLY | 216 | 34 | **15.7%** | 11 | 1 | 17.9% |
| 2.1.1 | 키보드 사용 보장 | FLAG_ONLY | 216 | 26 | **12.0%** | 11 | 0 | 13.2% |
| 1.1.1 | 적절한 대체 텍스트 | FLAG_ONLY | 216 | 17 | **7.9%** | 11 | 6 | 15.6% ↑↑ |
| 2.1.2 | 초점 이동 | FLAG_ONLY | 216 | 10 | **4.6%** | 11 | 0 | 3.9% |
| 3.1.1 | 기본 언어 표시 | DECIDABLE | 216 | 1 | **0.5%** | 11 | 0 | 3.9% ↑ |
| 3.2.2 | 찾기 쉬운 도움 정보 | FLAG_ONLY | 149 | 0 | **0.0%** | 10 | 0 | 0.0% |

표본 3건 미만 항목(1.2.1 자막 REF 1건, 3.3.4 반복입력 REF 6건, 3.3.3 인증 REF 10건)은 제외했다.

**1.1.1은 합산 15.6%가 참조군 7.9%의 두 배**이고, **3.1.1은 합산 3.9%가 참조군 0.5%의 여덟 배**다.
합산표를 인증 사이트의 이행률로 인용하면 참조군 값이 실제보다 나쁘게 제시된다.
반대로 3.3.2는 합산 39.8%가 참조군 47.2%보다 낮다 — **방향이 항목마다 다르다.**

### 4-4. UNDETERMINED → PASS 흡수

`criteria.py:80` 한 줄이다.

```python
strict = FAIL if f > 0 else (UNDET if u == total else PASS)
```

`u == total`일 때만 UNDETERMINED다. 하나라도 PASS가 섞이면 나머지가 전부 증거 불충분이어도 PASS가 된다.

실측: **PASS 판정 2,500건 중 60건이 UNDETERMINED 기회를 포함**하며, **전부 1.4.3(명도대비)이다.**
1.4.3의 PASS 63건 중 60건 — **95.2%의 "통과"가 부분 확인**이다.
1.4.3은 참조군 미흡률 71.1%로 두 번째로 높은 항목이므로, 이 흡수는 기사 핵심 수치에 직결된다.

### 4-5. 중복 endpoint — 7그룹 14레코드, 전부 참조군

final_url 정규화 기준:

```
x2 https://kr.lgappstv.com/main               LG Content Store(모바일웹) #2486 / LG Content Store #2485
x2 https://www.seniorro.or.kr                 노인일자리 여기(모바일웹) #2469 / 노인일자리 여기 #2400
x2 https://www.kordi.or.kr/m/main.do          한국노인인력개발원(모바일웹) #2460 / 한국노인인력개발원 #2344
x2 https://hrd.nhis.or.kr/portal/…            국민건강보험공단 인재개발원 #2428 / #2427
x2 https://gs.hycu.ac.kr/user/index.do        한양사이버대학원 #2389 / #2388
x2 https://www.nrc.go.kr/nrc/main.do          국립재활원 #2353 / #2352
x2 https://www.mcdonalds.co.kr/kor            맥도날드(모바일웹) #2333 / 맥도날드 #2332
```

동일 페이지의 동일 결함이 참조군 분모와 FAIL 수에 두 번 계상된다.
전부 같은 방향(증폭)으로 작용하므로 참조군 미흡률을 체계적으로 부풀린다.
`(모바일웹)` 접미가 붙은 별도 인증번호가 같은 URL을 가리키는 패턴이 4건이다.

### 4-6. 분류기 — 코드 한 줄이 원인

`targets.py:78`.

```python
hay = f"{service_name or ''} {org or ''}"
for pattern, code in CLASSIFY_RULES:
    if re.search(pattern, hay):
        return code
```

서비스명과 기관명을 합친 문자열에 부분문자열 정규식을 순서대로 적용하고 첫 매칭을 반환한다.
세 가지 결함이 한 줄에서 나온다.

1. **기관명이 라벨을 결정한다** — 226건 중 49건(21.7%)
2. **형태소 경계를 넘는다** — `공주문화관광재단`의 `공주문화`에서 `주문`이 매칭돼 `백제문화전당`이 BUY
3. **규칙 순서가 우선순위다** — PUBLIC이 마지막이라 복수 매칭 29건에서 전부 앞 규칙에 가로채임

현재 분포:

```
REFERENCE (정규식 자동)  PUBLIC 153 / OTHER 35 / TRANSFER 16 / SHARE 9 / MAP 8 / BUY 2 / COM 2 / PARTNER 1
COMPARISON (엑셀 인간)   BUY 26 / TRANSFER 7 / COM 5 / SEARCH 3 / CULTURE 2 / MAP 2 / HEALTH 1 / OTHER 1 / PUBLIC 1
```

참조군은 `SEARCH`·`HEALTH`·`CULTURE`를 **구조적으로 산출할 수 없다** — `CLASSIFY_RULES`에 해당 코드가 없다.
따라서 "인증 코호트에 문화·보건 서비스 0건"은 공급 부재가 아니라 코드 공간 부재다.

### 4-7. append-only 미강제

```python
# guard.py:168 — 정의만 존재, 호출부 없음
def check_append_only(run_dir: Path, baseline: dict[str, str] | None) -> list[Violation]:

# pipeline.py:106 — 같은 run_id 재실행 시 덮어씀
with out_path.open("w", encoding="utf-8") as f, ProcessPoolExecutor(max_workers=workers) as ex:
```

`run_measure.py`에서 `run_guard(records)`만 호출하고 `check_append_only`는 호출하지 않는다.
`guard_report.json`의 `status: OK`는 **append-only를 검증한 결과가 아니다.**

### 4-8. Interaction 증거 부재

`collect.py`의 수집 시퀀스는 `goto` → `wait_for_load_state` → `evaluate(PROBE)` → `getFullAXTree` →
`content()` → `screenshot()`이다. **클릭·키 입력·포커스 이동 코드가 없다.**

그럼에도 완결성 플래그는 `evidence_complete`다.

```python
res.evidence_complete = (
    probe is not None
    and res.access_block is None
    and len(dom) > 512
    and len(shot) > 8192
    and ax_total > 3
    and res.observability_scope != "NOT_OBSERVED"
)
```

키보드(2.1.1)·초점(2.1.2)·맥락 변화(3.2.1) 항목은 전부 정적 DOM 추론이며,
`criteria.py`의 각 note가 이를 명시하고 있으나 `report.json`에는 실리지 않는다.

```python
return _result("2.1.1", ops, note="실제 키 조작 결과가 아닌 정적 초점 가능성 신호")
return _result("2.1.2", ops, note="초점 시각화(focus visible)는 정적 관측으로 확정 불가")
```

플래그명을 `static_evidence_complete`로 바꾸고 note를 `criterion_table` 각 행에 실어야 한다.

### 4-9. `scope_relation` 접미사 절단

`collect.py:67`.

```python
if ".".join(bare_c.split(".")[-2:]) == ".".join(bare_f.split(".")[-2:]):
    return "MOBILE_SUBDOMAIN_REDIRECT"
```

`.co.kr` / `.or.kr` / `.go.kr`에서 마지막 두 라벨만 비교하면 `a.or.kr`과 `b.or.kr`이 같은 등록 도메인으로 판정된다.
무관한 기관 사이트가 인증 대상의 범위 내로 흡수될 수 있고,
`EXTERNAL_PARTNER_DOMAIN` 레코드도 집계에서 배제되지 않는다.

---

## 5. 현 문서 상태의 내부 불일치

`REPORT.md` 두 곳이 서로 다른 라운드 수치를 담고 있다.

| 위치 | 서술 | 근거 |
|---|---|---|
| 149행 표 | 미흡 0건 **12** | R4 |
| 374행 부록 | "미흡이 하나도 없던 곳은 **6곳**" | R3 잔여 |

`REPORT.md` 5-1절이 지목한 감사 원본 경로 `/tmp/claude-1000/…/55f933c2-…/tasks/wf4pqcxm3.output`는
현재 존재하지 않는다. 실제 보존 위치는 §2-A에 기재했다.

---

## 6. 실행 순서에 대한 함의 — GATE 0을 앞에 둬야 한다

어드바이저의 GATE 1~6 로드맵은 타당하나, **§3의 오염이 GATE 1 앞에 놓여야 한다.**

이유는 의존 관계다. GATE 1(판정 의미론 수정 후 R2 증거로 재판정)은 `rejudge.py`를 쓴다.
`rejudge.py`는 디스크 증거를 읽는다. 디스크의 실사용군 증거 30건은 잘못돼 있다.
**지금 GATE 1을 실행하면 수정된 판정 로직이 오염된 입력 위에서 돌아 오염이 그대로 승계된다.**

```
GATE 0  증거 계보 복구           ← 신규, 최우선
  0-1  record_id 안전화 (인증번호/해시 기반) — collect.py:194 · targets.py:139
  0-2  실사용군 48건 재수집 (참조군 216건은 재수집 불필요, 오염 없음)
  0-3  probe_ref → dom_sha256 대조 불변식을 guard에 추가
  0-4  감사 저널에서 확정 18건을 audit/findings_registry.jsonl 로 복구
  0-5  runs/ 원증거 682MB 외부 백업 (현재 단일 머신 무백업)

GATE 1  판정 의미론              ← 참조군은 GATE 0 없이도 착수 가능
  criteria.py:80 (UNDETERMINED 흡수) · criteria.py:681 (등급 혼합)
  → 재판정 대상은 참조군 216건에 한정하고, 실사용군은 GATE 0 완료 후 합류

GATE 2~6  어드바이저 로드맵대로
```

**참조군과 실사용군의 작업 경로를 분리하면 GATE 0과 GATE 1을 병렬로 진행할 수 있다.**
참조군 216건은 오염이 없고, 어드바이저가 지적한 기사 핵심 수치는 대부분 참조군에서 나온다.

---

## 7. 현 시점에서 참조군만으로 말할 수 있는 것

§3의 오염은 실사용군에 한정되므로, 참조군 기반 진술은 지금도 유효하다.
다만 §4-2·4-3·4-4의 수정을 반영해야 한다.

| 진술 | 현 근거로 가능한가 | 조건 |
|---|---|---|
| 인증 이력 2,283건 전수 확보, 감사일 기준 유효 226건 | 가능 | `VALID 227`과 구별 표기 |
| 인증 보유 사이트 216곳을 동일 조건 재측정 | 가능 | 관측 범위를 "공개 진입 화면 1개"로 명시 |
| 자동 관측 범위에서 확정 미흡이 0인 곳은 216곳 중 20곳 | 가능 | 기계 확정 기준임을 명시 (§4-2) |
| 1.4.3 명도대비 참조군 미흡률 71.1% | **조건부** | PASS 63건 중 60건이 부분 확인 (§4-4) 해소 후 |
| 2.1.3 조작 가능 참조군 미흡률 42.8% | 가능 | 해설서 기준 시정 이력을 함께 제시 |
| 최초 자동 판정에 과탐이 있었고 수정했다 | 가능 | §2-C 4건 |
| 인증군 3.54 vs 실사용군 5.90 | **불가** | 실사용군 오염 (§3) + 집단 구성 상이 |
| 유형별 교차 비교 | **불가** | 코드 공간 불일치 (§4-6) |
| 공공기관이 인증의 68% | **불가** | PUBLIC은 주체 변수가 아님 (§4-6) |
| 실사용 48개 중 7개는 모바일웹 없음 | **불가** | 실제 `NO_URL` 1건 (§4-1) |
| 인증은 1년간 아무도 재확인하지 않는다 | **불가** | "재측정 의무 조항을 확인하지 못했다"까지만 |

---

## 8. 재현 절차

```bash
cd /home/sieg/projects-wsl/ProjectFinal
git checkout research/refcohort-r1   # 32460b8
source scripts/activate.sh
cd research/refcohort
```

**§3 오염 재현** (원격 저장소 파일만으로 가능)

```bash
python - <<'EOF'
import json, re, collections
recs = [json.loads(l) for l in open("runs/r2/records.jsonl", encoding="utf-8") if l.strip()]
meas = [r for r in recs if r.get("collection_status") == "MEASURED"]
safe = lambda rid: re.sub(r"[^A-Za-z0-9_.-]", "_", rid)
c = collections.Counter(safe(r["record_id"]) for r in meas)
dups = {k: [r["record_id"] for r in meas if safe(r["record_id"]) == k] for k, n in c.items() if n > 1}
print("충돌 그룹", len(dups), "| 영향 레코드", sum(len(v) for v in dups.values()))
for k, v in dups.items(): print(" ", k, v)
EOF
```

**R2 → R3 수치 역전 재현**

```bash
python -c "
import json
for r in ('r2','r3','r4'):
    d=json.load(open(f'runs/{r}/report.json'))
    c=[x for x in d['cohorts'] if x['cohort']=='COMPARISON'][0]
    print(r, c['measured'], c['failed_criteria_per_service']['mean'], c['observed_accessibility_failure_count_total'])"
```

**감사 확정 18건 복원** (로컬 전용)

```bash
python -c "
import json,os
p=os.path.expanduser('~/.claude/projects/-home-sieg-projects-wsl-ProjectFinal/55f933c2-4846-4af3-b30d-02f3018be22a/workflows/wf_2b52c7fd-81d.json')
d=json.load(open(p))
print(d['agentCount'], d['durationMs'], d['result']['total'], d['result']['confirmed'], d['result']['rejected'])
for f in d['result']['confirmed_findings']: print(f['severity'], f['id'], 'votes=',f['votes'])"
```

---

## 부록. 확정 18건 목록 (감사 저널에서 복원)

| 심각도 | id | 차원 | votes | 시정 |
|---|---|---|---:|---|
| CRITICAL | `cohort-code-space-mismatch` | classification | 3/0 | 미시정 |
| CRITICAL | `public-is-provider-not-task` | classification | 3/0 | 미시정 |
| CRITICAL | `guard-blind-to-na-undetermined-laundering` | contract | 3/1 | 미시정 |
| CRITICAL | `criterion-table-not-cohort-split` | article | 3/0 | 미시정 |
| CRITICAL | `cohort-contrast-structurally-confounded` | article | 3/0 | 미시정 |
| HIGH | `substring-crosses-morpheme-boundary` | classification | 3/1 | 미시정 |
| HIGH | `rule-order-hijacks-later-rules` | classification | 3/0 | 미시정 |
| HIGH | `org-name-concatenation-drives-label` | classification | 3/1 | 미시정 |
| HIGH | `no-codebook-no-validation-for-classifier` | classification | **1/0** | 미시정 |
| HIGH | `undetermined-absorbed-into-pass` | contract | 3/0 | 미시정 |
| HIGH | `certification-eligible-not-computed` | contract | 3/1 | 미시정 |
| HIGH | `duplicate-endpoints-double-counted` | contract | 3/0 | 미시정 |
| HIGH | `scope-relation-suffix-truncation` | contract | 3/0 | 미시정 |
| HIGH | `target-size-overstrict-gap-rule` | article | 3/0 | **시정(R4)** |
| MEDIUM | `task-entry-claimed-without-navigation` | contract | 3/1 | 미시정 |
| MEDIUM | `no-interaction-evidence-but-called-complete` | contract | 3/1 | 미시정 |
| MEDIUM | `gate-detection-false-negative` | contract | 3/1 | 미시정 |
| MEDIUM | `append-only-not-enforced` | contract | 3/0 | 미시정 |

`votes`는 반증 투표 수 / 반증 성립 수다. `no-codebook-no-validation-for-classifier`의 `votes=1`은
3표 중 2표가 세션 한도로 소실됐음을 뜻한다(§2-A).

각 발견의 `evidence` · `impact_on_article` · `suggested_fix` 전문은 감사 저널
`~/.claude/projects/-home-sieg-projects-wsl-ProjectFinal/55f933c2-4846-4af3-b30d-02f3018be22a/workflows/wf_2b52c7fd-81d.json`
의 `result.confirmed_findings` 배열에 있다. GATE 0-4에서 `audit/findings_registry.jsonl`로 복구 대상이다.
