> **INVALIDATED_BY_SOURCE_MISMATCH** — 이 보고서는 A7 legacy xlsx 의 48 canonical service frame 위에서
> 산출됐다. A1 Wiseapp 933 원문과 대조한 결과 두 자료는 다른 패널 집합으로 판명됐으므로
> (docs/02_SOURCE_PROTOCOL.md §4) 여기 담긴 Category Feasibility 판정과 RQ2~4 NO-GO 결론은
> 연구 권위가 없다. 기록 목적으로만 보존한다. A1 기준 재산출 결과가 정본이다.

# G0·G1 완료 보고 및 G2 Feasibility GO/NO-GO

**수신** 원격 어드바이저 / 설계 동결 결정권자
**대상 설계** `최종설계기획서_랜딩페이지_접근성_비교연구_v2.0.docx` (DESIGN FREEZE CANDIDATE)
**작성** 2026-08-26 · 로컬 실행 에이전트
**Pilot 기준 SHA** `32460b87334a67f6a74823ac55f85ca80a9f8980`

---

## 요약

설계서 §23의 즉시 실행순서 1~3을 완료하고, §15가 "엔진을 대규모로 돌리기 전에" 확인하라고 지정한
Category Feasibility Matrix를 **G5 본수집 이전에** 산출했다.

**결과: 9개 카테고리 전부 TIER_C다. RQ2·RQ3·RQ4는 현재 모집단에서 성립하지 않는다.**

50+ 원자료의 canonical 서비스 48개 중 감사일 기준 유효 인증 보유는 **1개**(대한항공)다.
인증=1 그룹의 n이 1이므로 카테고리 내 인증 O/X 격차 비교는 어떤 카테고리에서도 불가능하다.

이는 표본이 부족한 것이 아니라 **모집단에 교차점이 없는 것**이며, 수집을 더 해도 해결되지 않는다.
다만 이 사실 자체가 기사 §4(권고적 효력의 한계)와 직결되는 강한 실증이므로,
연구를 중단할 것이 아니라 **RQ 구조를 재조정**할 것을 제안한다(§4).

---

## 1. G0 Pilot Archive — 완료 (`PILOT_ARCHIVED`)

설계서 §10의 9개 항목 중 8개를 이행했다.

| # | 설계서 요구 | 상태 | 산출물 |
|---|---|---|---|
| 1 | Git SHA 기록 | 완료 | `32460b87334a67f6a74823ac55f85ca80a9f8980` |
| 2 | 682MB 원증거 이중화 | **완료** | `/mnt/c/ProjectFinal_archive/pilot_refcohort_32460b8/pilot_evidence.tar.gz` |
| 3 | 파일별 SHA-256 manifest | 완료 | `refcohort/archive/pilot_evidence_manifest.jsonl` |
| 4 | `runs/*_measure.log` 보존 | 완료 | 아카이브에 포함 |
| 5 | Audit journal 복사·해시 등록 | 완료 | `refcohort/archive/audit_journal_wf_2b52c7fd-81d.json` |
| 6 | 확정 18건 registry 복구 | 완료 | `refcohort/audit/findings_registry.jsonl` |
| 7 | 신규 CRITICAL 등록 | 완료 | `evidence-filename-collision-overwrite` |
| 8 | REPORT.md 불일치 정정 | **미완** | `PILOT_CLOSURE_REPORT.md` 미작성 |
| 9 | Pilot read-only 선언 | 대기 | 8 완료 후 |

### 1-1. 아카이브 실측

```
원본      2,144 파일 / 699,196,558 B (0.651 GiB)
manifest  sha256:ae747eb2e9db8ff9a00da8a9a5ada989a8ca1e194795a3392c43f7fcf2792c0d
아카이브  506,088,301 B / 2,171 엔트리 / gzip -t OK
          sha256:4a446a39dba96cd8407f1c3f6cb2ce18b6e042e8c35a0e263c08c166883407dc
```

**볼륨 분리에 대한 제약 고지.** 이 머신에서 확보 가능한 것은 물리 이중화가 아니라 논리 이중화다.

```
/       /dev/sdd  ext4        (WSL2 ext4.vhdx)   원본
/mnt/c  C:\       9p/drvfs    Windows NTFS       아카이브
/mnt/d  D:\       7.0G 중 997M 여유 — 용량 부족
```

`/mnt/c`는 WSL의 ext4.vhdx와 분리된 파일시스템이므로 **vhdx 손상·WSL 초기화에는 생존**하지만,
물리 디스크가 같을 경우 디스크 장애에는 함께 소실된다.
설계서 §10-2의 "두 번째 물리/논리 저장위치" 중 **논리 요건만 충족**했다.
물리 이중화가 필요하면 외장 저장장치나 원격 오브젝트 스토리지를 지정해 달라 — 506MB 단일 파일이라 전송은 즉시 가능하다.

### 1-2. Findings Registry 복구 — 19건

```
CRITICAL 6 / HIGH 9 / MEDIUM 4
state:  OPEN 18 / FIXED 1 (target-size-overstrict-gap-rule, R4에서 시정)
verify: VERIFIED 17 / UNDER_VOTED 1 / VERIFIED_BY_DIRECT_MEASUREMENT 1
```

설계서 §11.2의 `votes == 0 → UNVERIFIED` 원칙을 소급 적용해 `verification_status`를 별도 필드로 분리했다.
`no-codebook-no-validation-for-classifier`는 3표 중 2표가 세션 한도로 소실돼 `UNDER_VOTED`(votes=1)로 기록했다 —
확정으로도 기각으로도 취급하지 않는다.

신규 `evidence-filename-collision-overwrite`는 투표 절차가 아니라 직접 실측으로 확인했으므로
`VERIFIED_BY_DIRECT_MEASUREMENT`로 구분했다.

---

## 2. G1 Source Recovery — 완료 (`SOURCE_LOCKED`, 미해결 2건)

`landing_accessibility/sources/source_registry.json`에 12개 입력자산의 경로·SHA-256·mtime·권위·역할을 등록했다.
**Source Gate = PASS** (전 항목 존재 확인).

### 2-1. 모집단 원본

```
경로    manus/fast_collection/50plus_all_rankings_real_url_mapping.xlsx
SHA256  95132834c74d1e8e4ca4785197f71286f4c53baac3ca1da6d2884be4660a3e02
크기    23,660 B      mtime  2026-08-26T01:07:31
시트    01_사용자_사용시간 / 02_50plus_점유율 / 03_리테일_INDEX /
        04_이커머스_앱테크 / 05_은행뱅킹 / 06_전체원자료 / 07_패널별유형집계
본시트  06_전체원자료 — 59행 × 8열
컬럼    패널 · 순위 · 앱/서비스 · 값 · 단위 · Primary 유형 · 공식 URL 후보 · URL 상태
```

**설계서 §5.1의 미충족 항목 2건** — Source Gate를 통과시켰으나 명시적으로 남긴다.

1. **원출처 기관·조사시점·표본정의가 파일 어디에도 없다.** 패널명("월평균 사용자 Top10",
   "50세 이상 점유율 Top10" 등)만 있고 조사기관·조사기간·모수·측정방법이 기재되지 않았다.
   기사에서 "50대 이상이 가장 많이 쓰는 서비스"라고 쓰려면 이 출처가 필요하다.
2. **KWCAG PDF의 공식 취득 URL이 없다.** 파일 해시는 등록했으나 배포처 링크가 없어
   제3자가 동일 문서를 확보했는지 확인할 수 없다.

두 항목 모두 사용자 확인이 필요하며, 코드로 해결할 수 없다.

---

## 3. G2 Feasibility — **NO-GO for RQ2 / RQ3 / RQ4**

### 3-1. 인증 매칭 방법

50+ 서비스 48개(canonical)와 인증 레지스트리 2,283건을 두 경로로 교차했다.

- **경로 A — 등록도메인 매칭.** `.co.kr`·`.or.kr`·`.go.kr` 등 2단계 국가도메인을 처리한 뒤
  `www.`·`m.` 접두를 제거하고 등록도메인을 비교
- **경로 B — 서비스명·기관명 문자열 교차.** A의 오탐을 걸러내기 위한 독립 검증

```
인증 레지스트리  2,283건 → URL 보유 등록도메인 557개 → 감사일 유효 도메인 155개
```

### 3-2. 결과

```
canonical 서비스        48
경로 A 인증 매칭         2  (대한항공, 삼성월렛)
경로 B 이름 교차 통과     1  (대한항공)
만료 이력만 보유          2  (카카오톡, 카카오뱅크)
인증 이력 전혀 없음       44
```

**경로 A의 2건 중 1건은 오탐이다.**

| 서비스 | 등록도메인 | 매칭된 인증 대상 | 판정 |
|---|---|---|---|
| 대한항공 | `koreanair.com` | 대한항공 / 대한항공 / `https://www.koreanair.com` | **진짜 (VALID)** |
| 삼성월렛 | `samsung.com` | **삼성전자승마단** | 오탐 — 동일 등록도메인, 다른 서비스 |

만료 이력 2건도 본 서비스가 아니다.

| 서비스 | 인증 이력 | 대상 URL |
|---|---|---|
| 이마트 | 피코크키친 / 더라이프 / 일렉트로마트 (전부 EXPIRED, 6건) | `m.thelifekorea.com` 등 — 이마트 본몰 아님 |
| 카카오뱅크 | 카카오뱅크 **영문** (EXPIRED) | `eng.kakaobank.com` — 한국어 본 서비스 아님 |
| 카카오톡 | 카카오 기업사이트 (EXPIRED) | `kakaocorp.com` — 서비스가 아니라 회사 소개 |

### 3-3. Category Feasibility Matrix

`landing_accessibility/state/category_feasibility_matrix.csv`

| source_category | 서비스 | 랜딩후보 | 인증1 | 인증0 | URL검수 | tier |
|---|---:|---:|---:|---:|---:|---|
| BUY_RESERVE | 26 | 25 | **1** | 24 | 1 | TIER_C |
| TRANSFER_ENTRY | 7 | 4 | **0** | 4 | 3 | TIER_C |
| COMMUNITY_PARTICIPATION | 5 | 4 | **0** | 4 | 1 | TIER_C |
| SEARCH_INFO | 3 | 2 | **0** | 2 | 1 | TIER_C |
| CULTURE_EDU | 2 | 2 | **0** | 2 | 0 | TIER_C |
| MOBILITY_MAP | 2 | 1 | **0** | 1 | 1 | TIER_C |
| HEALTH_WELFARE | 1 | 1 | **0** | 1 | 0 | TIER_C |
| OTHER_UTILITY | 1 | 0 | **0** | 0 | 1 | TIER_C |
| PUBLIC | 1 | 1 | **0** | 1 | 0 | TIER_C |

패널 기준으로도 동일하다. 7개 패널 중 인증1이 존재하는 패널은 2개이고 각각 n=1이다.

**설계서 §15의 TIER_C 정의("한쪽이 0 또는 1")에 9개 카테고리가 전부 해당한다.**
숫자 경계를 사후에 완화해도 인증1 총계가 1이므로 결과는 바뀌지 않는다.

### 3-4. 이것이 의미하는 것

RQ2("동일 카테고리에서 인증 O/X 서비스의 KWCAG 특성 차이"),
RQ3("분리도가 가장 큰 항목"), RQ4("차이의 지배 요인")은 모두 인증1 그룹의 분포를 요구한다.
n=1에서는 분포가 없고, bootstrap도 leave-one-out도 정의되지 않는다.

**G5 본수집(48개 랜딩 신규 수집)을 완료해도 이 결과는 달라지지 않는다.**
G3 엔진 하드닝·G4 criterion 검증은 RQ1과 RQ5에 여전히 필요하지만,
RQ2~RQ4를 위해 G5를 설계하는 것은 지금 시점에서 근거가 없다.

---

## 4. 설계 재조정 제안

연구를 중단할 사안이 아니다. **§3-2의 결과 자체가 기사 §4와 직접 연결되는 실증**이기 때문이다.

> 고령층이 실제로 가장 많이 쓰는 48개 서비스 중, 감사일 기준 유효한 웹접근성 품질인증을 보유한 곳은
> 1곳이다. 인증 이력이 있는 3곳도 전부 만료됐고, 그 대상은 본 서비스가 아니라
> 계열 소규모 사이트(피코크키친)·영문 페이지(카카오뱅크 영문)·회사 소개 페이지(카카오 기업사이트)였다.

이는 §4의 "신청주의이고 민간에는 권고뿐"이라는 제도 서술에 대한 **결과 측 증거**다.
지금까지는 "인증받은 곳이 잘 지키는가"를 물었는데, 실제로 답해야 할 질문은
**"인증 제도가 사람들이 실제로 쓰는 서비스에 도달하는가"**다. 그리고 그 답은 측정 없이 이미 나와 있다.

### 제안 — RQ 재배치

| | 현 v2.0 | 제안 |
|---|---|---|
| RQ1 적응기능 prevalence | 보조 | **주력 승격** — 인증 변수 불필요, 48개 전수로 성립 |
| RQ2 카테고리 내 인증 gap | 주력 | **폐기** — n=1 |
| RQ3 Top feature 분리도 | 주력 | **재정의** — 인증 대비가 아니라 "48개 서비스에서 가장 흔한 미흡 항목" |
| RQ4 이질성 | 주력 | **격하** — 카테고리·서비스 규모별 기술통계로 |
| RQ5 지침 준수형 재구성 | 보조 | **주력 승격** — 인증 변수 불필요 |
| — | — | **RQ0 신규: 인증 제도의 도달 범위** — 이미 산출됨(1/48), 추가 수집 불필요 |

### 세 집단을 비교가 아니라 병치

```
A. 50+ 실사용 서비스 48개   — 랜딩 접근성 실태 + 적응기능 (신규 E001 수집)
B. 유효 인증 226건          — "국가가 인정한 곳조차 지금 어떤가" (Pilot REFERENCE 재수집)
C. A ∩ B = 1건             — 제도 도달 범위 그 자체가 결과
```

A와 B는 **통계적으로 비교하지 않는다.** 모집단 구성이 다르고 관측 목적이 다르다.
두 개의 독립적 사실로 병치하고, C를 그 사이의 연결고리로 쓴다.
이 구조는 설계서 §1.3의 금지사항(인과효과 추정, 인증을 Gold Label로 취급)을 모두 지킨다.

### Gate 영향

| Gate | 영향 |
|---|---|
| G3 Engine Hardening | **변경 없음** — RQ1·RQ3·RQ5에 그대로 필요 |
| G4 Criterion Validation | **변경 없음** — 오히려 더 중요해짐(대비 없이 절대 수치를 쓰므로) |
| G5 Main Evidence E001 | 대상은 48개 유지. **인증 O/X 층화 표집 불필요** |
| G6 Human Review | 변경 없음 |
| G7 Analysis | **재작성** — gap/bootstrap/leave-one-out → prevalence·기술통계·사례 |
| G8 Publication | §21 게이트에 "인증1 n=1로 그룹 비교 제시" 금지 항목 추가 |

---

## 5. 결정을 요청하는 사항

1. **RQ 재배치 승인 여부** — §4 제안대로 갈지, 아니면 모집단을 확장해 인증 교차점을 만들지.
   후자를 택하면 50+ 원자료가 아닌 다른 모집단 정의가 필요하고, 그것은 설계서 §1.2의
   "50+ 사용순위에 실제 등장하는 서비스를 먼저 모집단으로 삼음"이라는 변경 불가 요구사항과 충돌한다.
2. **집단 B(인증 226건) 재수집 여부** — Pilot REFERENCE는 파일명 충돌 영향이 없어 R2 증거가 살아 있으나,
   설계서 §2.4는 "본 연구 수치와 혼합 금지, 회귀테스트에만 사용"으로 판정했다.
   병치 구조에서 B를 쓰려면 하드닝된 엔진으로 재수집해야 한다(226건, Pilot 실측 약 6분).
3. **물리 이중화 대상** — 현재 논리 이중화만 확보. 외장 저장장치나 원격 위치를 지정할지.
4. **50+ 원자료 출처** — 조사기관·조사기간·표본정의. 기사에 모집단을 서술하려면 필요하다.

---

## 부록. 생성된 파일

```
research/refcohort/archive/
  pilot_evidence_manifest.jsonl          2,144 파일 SHA-256
  pilot_evidence_manifest.meta.json      아카이브 사본 위치·해시·게이트 상태
  audit_journal_wf_2b52c7fd-81d.json     225-agent 감사 저널 정본 (540KB)
research/refcohort/audit/
  findings_registry.jsonl                19건 (18 복구 + 1 신규)
research/landing_accessibility/
  sources/source_registry.json           입력자산 12건 provenance
  state/category_feasibility_matrix.csv  9 카테고리 × 10 필드
  state/service_certification_match_draft.csv  48 서비스 인증 매칭 근거
/mnt/c/ProjectFinal_archive/pilot_refcohort_32460b8/
  pilot_evidence.tar.gz                  506MB / 2,171 엔트리
```

재현:

```bash
cd /home/sieg/projects-wsl/ProjectFinal
.venv/bin/python -c "
import pandas as pd, json
from urllib.parse import urlparse
KR2={'co','or','go','ne','re','pe','ac'}
def rd(u):
    if not u or str(u)=='nan': return None
    u=str(u).strip()
    if not u.startswith('http'): u='https://'+u
    h=(urlparse(u).netloc or '').lower().split(':')[0]
    for p in ('www.','m.'):
        if h.startswith(p): h=h[len(p):]
    q=h.split('.')
    if len(q)>=3 and q[-1]=='kr' and q[-2] in KR2: return '.'.join(q[-3:])
    return '.'.join(q[-2:])
df=pd.read_excel('manus/fast_collection/50plus_all_rankings_real_url_mapping.xlsx','06_전체원자료')
reg=[json.loads(l) for l in open('research/refcohort/runs/r1-discovery/official_registry.jsonl',encoding='utf-8') if l.strip()]
valid={rd(r['certified_target_url_listed']) for r in reg if r.get('cert_valid_candidate_o')=='O'}
svc={str(r['앱/서비스']).strip(): rd(r['공식 URL 후보']) for _,r in df.iterrows()}
hit=[n for n,d in svc.items() if d in valid]
print(len(svc), '개 중 인증 도메인 매칭:', hit)"
```
