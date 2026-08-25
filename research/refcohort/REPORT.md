# 모바일웹 접근성 실증 검증 — 작업 보고서

**작성 시각** 2026-08-26 (KST) · **브랜치** `research/refcohort-r1` · **최신 커밋** `a0ead79`
**작업 루트** `/home/sieg/projects-wsl/ProjectFinal/research/refcohort`

---

## 1. 목표 재정의

### 1-1. 처음 지시와 실제 목적함수

지시는 "`manus/fast_collection`을 이해하고, 자율적으로 진행하라"였고, 마지막에 최종 목적이 명시됐다 — **`파이널 기사_인덱스_초안_2.docx`의 5장**.

그 5장은 현재 이렇게 비어 있다.

```
# 5. 실증 검증 — 한국디지털접근성진흥원 지침, 실제로 지켜지고 있나
[※ 협업자 분석 진행 중 — 결과 반영 예정]
 - 한국디지털접근성진흥원이 제시하는 웹·앱 접근성 평가 지침 개요
 - 평가 대상 웹·앱 목록 및 선정 기준
 - 지침 이행 여부 분석 결과 (통과/미흡 항목별 정리)
 - 이 결과를 4번 섹션의 "권고적 효력에 그치는 지침"이라는 한계와 연결
```

따라서 **목적함수는 "네 개의 빈칸을 방어 가능한 실측 데이터로 채우는 것"**이다. 코드를 잘 만드는 것이 목표가 아니라, 기자가 그대로 인용해도 반박당하지 않는 수치를 만드는 것이 목표다.

### 1-2. 기존 자산(`manus/fast_collection`)이 목적함수에 못 미쳤던 이유

인계받은 fast_collection은 **"수집이 가능한가"를 O/X로 기록**한 것이지 **"지침을 지켰는가"를 잰 것이 아니다.** 전수 파악에서 확인한 격차는 다음과 같다.

| 항목 | fast_collection | 기사 5장이 요구하는 것 |
|---|---|---|
| 측정 대상 | 15건 (키워드 36개 검색) | 모집단 전체 |
| 측정 내용 | 수집 가능성 O/X | KWCAG 검사항목별 통과/미흡 |
| 접근성 트리 | **15건 전부 UNKNOWN** (Firecrawl이 AX를 주지 않음) | 필수 증거 |
| 비교 대조군 | 없음 | 인증 없는 실사용 서비스 |
| 재현 가능성 | 경로가 `/home/ubuntu/...` 하드코딩 | 이 환경에서 재실행 |

특히 **AX 트리 부재**가 결정적이었다. 대체텍스트·레이블·역할 판정은 접근성 트리 없이는 불가능하다.

### 1-3. 재정의된 설계

기사 §4가 "지침은 있지만 강제력이 없다"를 다뤘으므로, §5는 그 **다음 질문**을 실증해야 한다.

> 강제력이 없을 때, 지침은 실제로 지켜지는가?

이를 위해 두 집단을 **완전히 동일한 조건**으로 측정하는 구조를 잡았다.

- **참조군(REFERENCE)** — 감사일 기준 유효한 웹접근성 품질인증 보유 사이트 **전수**
  → *국가가 "지침을 지켰다"고 인정한 곳조차 지금 어떤가*
- **비교군(COMPARISON)** — 50세 이상 실사용 상위 앱/서비스의 공식 모바일웹
  → *인증 제도 밖의 서비스는 어떤가*

법령 근거가 이 설계를 뒷받침한다 (`reports/legal_basis.md`). 디지털포용법상 접근성 품질인증은 **신청주의**이고, 민간에는 "권고할 수 있다"가 전부이며, **인증 취소 사유는 거짓 인증과 표시 위반 둘뿐**이다. 인증 후 접근성이 나빠져도 취소되지 않고, 1년 유효기간 중 재측정 조항도 없다. **한 번 받으면 1년간 아무도 다시 확인하지 않는다** — 이 공백을 메우는 것이 §5다.

---

## 2. 어떻게 수행했는가

### 2-1. 기준 동결 (SSOT)

`manus/fast_collection/eda/config`의 법령·지침 16종을 절대 기준으로 삼았다. 그중 검사 기준은 두 PDF에서 추출했다.

- `kwcag2.1&2.2_검사항목_대조표.pdf` → **KWCAG 2.2 = 4원칙 · 14지침 · 33검사항목**
- `웹 접근성 지침 해설서(kwcag 2.2 기준).pdf` (102p) → 항목별 판정 근거

33개 항목을 자동화 가능성으로 3분류해 `codebook/kwcag22_criteria.json`에 동결했다.

| 분류 | 개수 | 취급 |
|---|---:|---|
| `AUTO_DECIDABLE` | 15 | 기계 판정, 수치로 보고 |
| `AUTO_FLAG_ONLY` | 10 | 미흡 **후보**만, 최종 판정은 사람 몫 |
| `NOT_AUTOMATABLE` | 8 | 판정하지 않고 확인 불가로 남김 |

**핵심 원칙: 확인 불가를 통과로 바꾸지 않는다.** 적용 대상이 없으면 `NA`(해당 없음)이지 통과가 아니고, 증거가 부족하면 `UNDETERMINED`이지 무결점이 아니다. 이 구분을 뭉개면 통과율이 실제보다 높아진다.

### 2-2. 증거 수집기 — fast_collection의 AX 공백 해소

Playwright 1.62에서 `page.accessibility` API가 제거되어, **CDP 세션의 `Accessibility.getFullAXTree`**로 우회했다. 검증 결과:

```
role=button  name='검색 실행'    ← aria-label 해석
role=image   name='대체텍스트'   / role=image name=''  ← alt 누락 탐지
role=textbox name='질의'        ← label for= 연결 확인
```

이로써 프로토콜 v2 §4가 요구하는 **DOM · AX · Screen · Interaction 4종 증거**를 로컬에서 전부 수집한다. 외부 API 키가 필요 없다.

측정 조건은 고정했다 — **390×844 CSS px, DPR 3, ko-KR, Asia/Seoul, 모바일 UA, 터치 활성화.**

`src/refcohort/probe.js`(22KB)가 브라우저 안에서 28종 적용기회를 한 번에 수집하고, `criteria.py`(24KB)의 판정기 25개가 이를 KWCAG 항목별 verdict로 변환한다.

**게이트 경계는 절대 넘지 않는다.** 로그인·결제·본인확인·CAPTCHA를 감지하면 관측을 멈추고 태그만 기록한다. 우회 코드 자체를 넣지 않았다.

### 2-3. 모집단 — 키워드 검색을 전수 크롤로 교체

fast_collection은 키워드 36개로 검색해 78건→15건을 얻었고, 5개 유형이 0건이었다. **키워드는 등록명 표기에 의존하므로 "0건 = 공급 부재"인지 "0건 = 키워드 실패"인지 구분할 수 없다.**

전수 크롤로 바꿨다.

```
230페이지 순회 → 인증 이력 전체 2,283건 (VALID 227 / EXPIRED 2,056)
                 → 감사일 기준 유효 226건, 전부 대상 URL 보유
```

키워드 검색의 **15배**다. 그리고 fast_collection의 0건이 무엇이었는지 판정됐다.

| 유형 | 키워드 검색 | 전수 크롤 | 결론 |
|---|---:|---:|---|
| DELIVERY, VOTE, CALL | 0 | **0** | 전수에서도 없음 → **공급 제약 증거 확정** |
| BUY, PARTNER | 0 | 2, 1 | 존재함 → **키워드 실패였음** |
| PUBLIC | 4 | 153 | 키워드가 대부분을 놓쳤음 |

### 2-4. 라운드 진행 — R1 → R2 → R3

| 라운드 | 무엇을 했나 | 결과 |
|---|---|---|
| **R1** | 274 대상 최초 측정 | 253 측정 / guard OK |
| — | **자체 검증**으로 과탐 3건 + 수집기 결함 2건 발견·시정 | 아래 2-5 |
| **R2** | 수정된 수집기로 274 전체 **재측정** | 257 측정 / guard OK |
| — | 적대적 감사 워크플로 (5차원 × 3표 반증) | 확정 18건 |
| **R3** | 2.2.2 수정 누락분 반영 후 **R2 증거로 재판정** | 257 판정 / guard OK |

R3는 사이트에 다시 요청하지 않는다. `rejudge.py`가 보존된 probe 증거로 판정만 다시 한다 — 부하가 없고 원 증거 해시가 유지된다.

### 2-5. R1 자체 검증에서 잡은 과탐 — 결과를 덜 극적으로 만든 수정

R1 최초 결과는 자막 100%·정지기능 100%·명도대비 93.7% 미흡이었다. **극적인 수치일수록 의심해야 한다.** 직접 근거를 열어본 결과 전부 판정 결함이었다.

| 항목 | 과탐의 실체 | 조치 |
|---|---|---|
| 1.2.1 자막 | FAIL 51건 중 **49건이 음소거 비디오**. 자막은 음성 정보의 대체 수단이므로 무음 배경영상은 적용 대상이 아님 | 적용기회에서 제외 → 적용 27건→3건 |
| 2.2.2 정지기능 | 전부 **로딩 스피너**(`spinner-rotator`, `loading-*`)와 **스크롤 유도 화살표**(`scrollDown`, `chevronFade`). 정보를 전달하지 않는 장식 | 제외 + 남은 것도 FAIL 아닌 UNDETERMINED → 미흡 26건→0건 |
| 1.4.3 명도대비 | 실패 6,400건 중 **2,887건이 `ratio=1`(흰 글씨 위 흰 배경)**. 배경 추적 실패로 75.3%가 순백 기본값 | 배경 미확정·배경이미지 위·동색 산출은 UNDETERMINED로 분리 → 93.7%→74.9% |

수집기 결함 2건도 함께 고쳤다.

- `page.evaluate`가 `None`을 반환할 때 가드가 없어 **4건이 통째로 손실**(국립중앙도서관 등) → None 가드 + 1회 재시도
- HTTP 4xx/5xx를 성공 경로로 태움 (**쿠팡 403 봇차단이 dom 289B로 통과 시도**) → `access_block` 필드로 명시 분류, 분모에는 유지

---

## 3. 현재 결과 (R3)

### 3-1. 코호트

| 집단 | 대상 | 측정 | 차단 | 미흡 0건 | 서비스당 평균 미흡 | 확인된 미흡 지점 / 적용기회 |
|---|---:|---:|---:|---:|---:|---:|
| 인증 보유군 | 226 | 216 | 10 | **6** | 4.01 (0~8) | 5,104 / 91,479 |
| 실사용 상위군 | 48 | 41 | 7 | **0** | 6.46 (3~8) | 3,513 / 25,574 |

### 3-2. 검사항목별 (적용 서비스가 있는 항목, 미흡률순)

| 항목 | 이름 | 자동화 | 적용 | 미흡 | 미흡률 | 지점 통과율 |
|---|---|---|---:|---:|---:|---:|
| 2.1.3 | 조작 가능 | 판정 | 256 | 230 | 89.8% | 75.9% |
| 1.4.2 | 자동 재생 금지 | 판정 | 30 | 25 | 83.3% | 18.8% |
| 1.4.3 | 텍스트 명도 대비 | 판정 | 251 | 188 | 74.9% | 57.1% |
| 2.5.3 | 레이블과 네임 | 판정 | 94 | 69 | 73.4% | 45.2% |
| 4.2.1 | 웹앱 접근성 준수 | 판정 | 200 | 117 | 58.5% | 53.7% |
| 2.4.3 | 적절한 링크 텍스트 | 신호 | 256 | 111 | 43.4% | 97.0% |
| 3.3.2 | 레이블 제공 | 판정 | 108 | 43 | 39.8% | 66.4% |
| 2.4.2 | 제목 제공 | 판정 | 257 | 85 | 33.1% | 86.9% |
| 4.1.1 | 마크업 오류 방지 | 판정 | 257 | 56 | 21.8% | 77.7% |
| 2.4.1 | 반복 영역 건너뛰기 | 판정 | 257 | 43 | 16.7% | 83.3% |
| 1.1.1 | 적절한 대체 텍스트 | 신호 | 257 | 40 | 15.6% | 99.2% |
| 2.1.1 | 키보드 사용 보장 | 신호 | 257 | 34 | 13.2% | 99.0% |
| 3.1.1 | 기본 언어 표시 | 판정 | 257 | 10 | 3.9% | 96.1% |

표본이 작은 항목(1.2.1 자막 3건, 3.3.4 반복입력 6건, 3.3.3 인증 12건)은 100%·58% 등이 나오지만 **분모가 작아 기사에 비율로 쓰면 안 된다.**

### 3-3. 관측 범위

| | 인증 보유군 | 실사용 상위군 |
|---|---|---|
| 과업 진입까지 관측 | 122 | 11 |
| 랜딩까지만 | 94 | 30 |
| 게이트 없음 | 142 | 15 |
| 로그인 요구 | 66 | 21 |
| 본인확인 요구 | 7 | 0 |
| 결제 요구 | 1 | 5 |

---

## 4. 직접 확인하는 방법

### 4-1. 먼저 환경

```bash
cd /home/sieg/projects-wsl/ProjectFinal
git checkout research/refcohort-r1
source scripts/activate.sh
cd research/refcohort
```

### 4-2. 최종 수치를 눈으로 보기

```bash
# 코호트 요약
python -c "
import json; r=json.load(open('runs/r3/report.json'))
[print(c['cohort'], c['measured'], c['observed_strict_pass'], c['failed_criteria_per_service']['mean']) for c in r['cohorts']]"

# 검사항목별 표 전체
python -c "
import json; r=json.load(open('runs/r3/report.json'))
[print(f\"{x['criterion_id']:<7}{x['criterion_name'][:20]:<22}{x['services_applicable']:>4}{x['services_fail']:>5}\")
 for x in r['criterion_table'] if x['services_applicable']]"
```

### 4-3. **개별 판정이 맞는지 검증** (가장 중요)

수치를 믿기 전에 표본 몇 개를 직접 열어보는 것이 좋다. 모든 판정에는 근거가 붙어 있다.

```bash
# 특정 서비스의 항목별 판정과 실패 근거
python -c "
import json
rows=[json.loads(l) for l in open('runs/r3/records.jsonl')]
r=[x for x in rows if '129' in str(x.get('target_url'))][0]
print(r['service_name'], r['target_url'], r['final_url'])
for cid,c in r['criteria'].items():
    if c['verdict_state']=='FAIL':
        print(f\"  {cid} {c['criterion_name']}  {c['pass_count']}/{c['applicable_count']}\")
        for f in c['failing'][:3]: print('     ', f['reason'], '|', f.get('selector','')[:60])
"
```

**증거 원본**은 사이트별로 4종이 그대로 남아 있다.

```bash
ls runs/r2/dom/     # 렌더된 HTML 238건
ls runs/r2/screen/  # 390x844 스크린샷 238건
ls runs/r2/ax/      # 접근성 트리 238건
ls runs/r2/probe/   # 수집된 적용기회 원본 238건
```

스크린샷을 직접 보면 판정이 타당한지 눈으로 확인할 수 있다.

```bash
xdg-open runs/r2/screen/REF_2451.png
python -c "
import json; a=json.load(open('runs/r2/ax/REF_2451.json'))
[print(n['role'], repr(n['name'])) for n in a[:30]]"
```

### 4-4. 재현

```bash
python run_measure.py <run_id>        # 전체 재측정 (사이트에 실제 요청, 약 6분)
python rejudge.py r2 <run_id>         # 재요청 없이 기존 증거로 판정만 다시
```

`runs/`는 append-only다. 기존 run을 덮어쓰지 않는다.

### 4-5. 계약 위반 여부

```bash
cat runs/r3/guard_report.json   # status: OK / WARN / HALT
```

`guard.py`가 매 run마다 검사하는 것 — 산출 금지 변수(`reference_deviation_score` 등 5개)가 null인지, NA/UNDETERMINED가 PASS로 환산되지 않았는지, 게이트 뒤를 관측했다고 주장하지 않는지, 증거 없이 판정하지 않았는지.

### 4-6. 봐야 할 파일

| 파일 | 내용 |
|---|---|
| `codebook/kwcag22_criteria.json` | 33검사항목 동결본 + 자동화 분류 |
| `src/refcohort/criteria.py` | **판정 규칙 25개. 수치가 의심되면 여기부터** |
| `src/refcohort/probe.js` | 브라우저에서 무엇을 수집하는지 |
| `src/refcohort/guard.py` | 계약 위반 감시 불변식 |
| `reports/legal_basis.md` | 기사 §5-4용 법령 인용 |
| `runs/r1-discovery/official_registry.jsonl` | 인증 이력 전수 2,283건 |
| `state/reference_targets.json` | 참조군 226건 |
| `state/comparison_targets.json` | 비교군 48건 (evidence row 보존) |
| `runs/r3/report.json` | **최종 집계** |
| `runs/r3/records.jsonl` | 서비스별 전체 판정 (4.6MB) |

### 4-7. git

```bash
git log --oneline research/refcohort-r1
# a0ead79  2.2.2 수정 누락분 + 재판정 경로
# da1b76e  R1 자체검증 과탐 3건 + 수집기 결함 2건 시정
# 8b86915  전수 크롤 + 두 코호트 + 측정 파이프라인
# ca0e082  코드북 동결 + 수집기 + 판정 엔진
```

원격에도 푸시돼 있다: `origin/research/refcohort-r1`

---

## 5. 아직 신뢰하면 안 되는 것

### 5-1. 적대적 감사가 절반만 완주했다

5차원 감사 + 발견별 3표 반증 워크플로를 돌렸으나, **225개 에이전트 중 110개가 세션 한도(`resets 5:20am`)로 실패**했다. 최종 종합 단계도 실패해 시정 큐가 생성되지 않았다.

더 중요한 문제 — 워크플로의 생존 판정이 `votes > 0 && 반증 < 과반`이라, **반증 에이전트가 죽어 votes=0이 된 발견은 자동 기각**됐다. "기각 55건"은 반증된 55건이 아니라 **검증되지 못한 것이 섞인 55건**이다.

원본: `/tmp/claude-1000/-home-sieg-projects-wsl-ProjectFinal/55f933c2-4846-4af3-b30d-02f3018be22a/tasks/wf4pqcxm3.output` (415KB)

### 5-2. 확정 18건 중 1건만 시정했다

3표 전원 확인을 통과한 발견 18건(CRITICAL 5 / HIGH 9 / MEDIUM 4) 중 **2.2.2 관련 1건만 반영**했다. 나머지 17건은 미시정이다.

**기사에 직접 영향을 주는 것 두 개:**

- `cohort-code-space-mismatch` (CRITICAL) — 참조군은 정규식 자동분류, 비교군은 엑셀 인간 라벨. 같은 대상에 두 방식을 적용하면 **일치율 31.2%**. 코드 공간도 달라 참조군은 `SEARCH`/`HEALTH`/`CULTURE`를 구조적으로 산출할 수 없다.
- `public-is-provider-not-task` (CRITICAL) — PUBLIC 153건은 과업 유형이 아니라 **운영주체**를 잰 것. 53건이 한 글자 토큰(원/부/처/청)으로 매칭됐고, 국립중앙도서관·국립부곡병원·박물관이 전부 PUBLIC으로 흡수됐다.

> **따라서 기사에 "유형별로 인증 사이트와 실사용 서비스를 비교했다"는 표를 쓰면 그것은 허위다.** PUBLIC 153 vs 1은 실제 구성 차이가 아니라 라벨링 방식 차이다. **코호트 전체 수준의 검사항목별 결과는 유효하지만, 유형별 교차비교는 현재 쓸 수 없다.**

나머지 확정 발견: `criterion-table-not-cohort-split`, `certification-eligible-not-computed`, `undetermined-absorbed-into-pass`, `gate-detection-false-negative`, `target-size-overstrict-gap-rule`, `duplicate-endpoints-double-counted`, `append-only-not-enforced`, `guard-blind-to-na-undetermined-laundering`, `no-interaction-evidence-but-called-complete`, `task-entry-claimed-without-navigation`, `scope-relation-suffix-truncation`, `org-name-concatenation-drives-label`, `substring-crosses-morpheme-boundary`, `rule-order-hijacks-later-rules`, `no-codebook-no-validation-for-classifier`, `cohort-contrast-structurally-confounded`

### 5-3. 알려진 측정 한계

- **iframe 내부를 수집하지 않는다.** 프레임 기반 사이트(KsureOn 등 WebSquare)는 적용기회가 거의 0으로 나온다.
- **Shadow DOM을 순회하지 않는다.**
- **2.1.3 조작 가능의 24 CSS px 임계값**은 WCAG 2.5.8 기준을 차용한 것이고, KWCAG 2.2 해설서가 같은 수치를 쓰는지 원문 재확인이 필요하다. 이 항목이 미흡률 89.8%로 가장 높아 결론에 큰 영향을 준다.
- **최종 FAIL은 사람 검토를 거치지 않았다.** 프로토콜 v2 §8-7은 이중 평가와 합의를 요구한다. 현재 전부 자동 판정(AUTO_FLAG) 상태다.

### 5-4. 미착수

- 엑셀 URL ↔ 동일 유형 인증 참조 URL 매칭 (지시받은 다음 단계)
- 기사 §5 초안 실제 생성 (`article.py`는 작성했으나 실행하지 않음)
- 사람 검토(REVIEW) 큐 구축
- `ts/` 분리 작업이 워킹트리에만 있고 커밋되지 않음 (main 브랜치 건)

---

## 6. 다음에 할 일 (우선순위)

1. **CRITICAL 5건 시정** — 특히 코호트 분류 문제. 두 코호트의 라벨을 별도 필드로 분리하고, `by_task_code` 출력에 "기사 인용 금지" 표시를 넣는다.
2. **2.1.3 임계값을 KWCAG 2.2 해설서 원문으로 재확인** — 미흡률 1위 항목이라 여기가 틀리면 결론이 흔들린다.
3. **감사 재실행** (세션 한도 리셋 후) — 이번엔 반증 votes=0이면 "미검증"으로 남기고 자동 기각하지 않도록 워크플로를 고친다.
4. 기사 §5 초안 생성 및 검증
5. 엑셀 URL ↔ 인증 참조 URL 매칭

---

## 부록: 이번 작업에서 확인된 사실 중 기사에 쓸 만한 것

- 웹접근성 인증 이력 전체 2,283건 중 **현재 유효한 것은 227건뿐**이다(만료 2,056건).
- 유효 인증 226건 중 **153건(68%)이 공공기관**이다. 인증은 사실상 공공 부문 제도이며, 민간 생활서비스는 거의 신청하지 않는다. *(단, 이 68%는 5-2의 분류 결함 영향을 받으므로 "공공기관 운영 주체"라는 표현으로만 써야 한다.)*
- 인증 보유군 216곳 중 **관측한 공개 화면에서 미흡이 하나도 없던 곳은 6곳**이다.
- 실사용 상위군 41곳 중에는 **0곳**이다.
- 50+ 실사용 상위 서비스 48개 중 **7개는 모바일웹 자체가 없다**(앱 전용, 제품 소개 페이지만 존재). 원기날씨는 웹 버전이 아예 없어 측정 대상을 만들 수 없었다.
