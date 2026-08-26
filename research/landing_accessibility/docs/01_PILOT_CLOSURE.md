# 01 — Pilot R1–R4 종료 보고 및 알려진 불일치 정정

**Pilot** `research/refcohort-r1` @ `32460b87334a67f6a74823ac55f85ca80a9f8980`
**지위** `READ_ONLY / HISTORICAL / REGRESSION-ASSET`
**작성** Main Study 오케스트레이터 · 2026-08-26

Pilot 디렉터리는 봉인됐으므로 정정을 그 안에 쓰지 않는다.
**`research/refcohort/REPORT.md` 를 읽는 사람은 반드시 이 문서를 함께 봐야 한다.**

---

## 1. Pilot 의 지위

R1–R4 는 최종 분석이 아니다. **측정엔진·판정엔진·증거계보 설계의 실패학습 자산**이다.

| Pilot 산출 | Main Study 사용 |
|---|---|
| 인증 이력 2,283건 수집 방법 | 재사용 (A2 수집기로 포팅, 계보 기록) |
| R1/R2 실사용군 즉시판정 수치 | **금지** — 증거계보 파손 |
| R3/R4 실사용군 수치 | **금지** — 오염된 디스크 증거로 재판정됨 |
| R3/R4 REFERENCE 수치 | Pilot 회귀테스트만. 본 연구 수치와 혼합 금지 |
| 2.1.3 대각선 6mm 교정 | 재사용 — criterion 검증 템플릿 |
| 자막·정지·대비 과탐 교정 | 재사용 — 적용대상 판정·UNDET 처리 규칙 |
| `TYPE_MAP` / `CLASSIFY_RULES` | **폐기** |
| `TASK_ENTRY` 휴리스틱 | **폐기** |

## 2. Pilot 을 종료시킨 CRITICAL — 증거 파일명 충돌

`collect.py:194` 한 줄이다.

```python
safe = re.sub(r"[^A-Za-z0-9_.-]", "_", record_id)
```

`targets.py:139` 가 실사용군 `record_id` 를 한글 서비스명으로 만들었기 때문에, **글자 수가 같은 서비스가 같은 파일명으로 수렴**했다.

```
CMP___       ← 밴드·당근·티맵·토스·다음·틱톡·퀸잇·테무   (8건)
CMP____      ← 유튜브·네이버·이마트                     (3건)
CMP_____     ← 카카오톡·홈앤쇼핑·다음메일·홈플러스·코스트코·롯데마트 (6건)
CMP______    ← 인스타그램·롯데홈쇼핑·현대홈쇼핑·똑똑계산기·… (9건)
CMP_______  ← 네이버_지도·신세계백화점                  (2건)
CMP__________← 네이버_네이버페이·레브잇_올웨이즈_          (2건)
```

디스크에 남은 내용은 마지막에 기록한 프로세스의 것이다 — `runs/r2/probe/CMP___.json` 의 url 은 `https://www.temu.com/` 이다.

| | R1 | R2 |
|---|---:|---:|
| MEASURED 레코드 | 253 | 257 |
| 실제 증거 파일 | 231 | 238 |
| 충돌로 소실 | 22 | 19 |
| 충돌 영향 레코드 | — | **30건 (실사용군 41건 중 73%)** |

참조군은 `REF_<인증번호>` 로 ASCII 가 남아 영향이 없다.

**R1/R2 의 판정 수치 자체는 유효하다** — `pipeline.py:65` 가 수집 직후 메모리의 probe 로 판정했다.
**R3/R4 는 오염됐다** — `rejudge.py` 가 디스크에서 다시 읽는다.

증상이 데이터에 남아 있다. 2.2.2 과탐만 걷어낸 R3 에서 실사용군 평균 미흡이 **5.63 → 6.46 으로 올라갔다.**

## 3. `REPORT.md` 의 알려진 불일치 — 정정

### 3-1. "미흡이 하나도 없던 곳은 6곳" (374행)

**틀렸다.** R3 잔여 수치다. 149행 표는 R4 값 12곳이다.

정확히는 세 층으로 나뉜다.

| 기준 | 참조군 216곳 중 |
|---|---:|
| 전 항목 FAIL 0 (R4) | 12 |
| **기계 확정 FAIL 만 0** | **20** |
| R3 시점 수치 (폐기) | 6 |

`criteria.py:681-682` 가 `AUTO_DECIDABLE` 과 `AUTO_FLAG_ONLY` 를 구분하지 않는다.
참조군 평균 3.54 = 기계확정 2.67 + 사람검토필요 0.88 이다.

### 3-2. "실사용 상위 48개 중 7개는 모바일웹 자체가 없다" (부록)

**레코드와 일치하지 않는다.** 실사용군 미측정 7건의 실제 사유는 이렇다.

```
NO_URL (URL_DISCOVERY_REQUIRED)  1건 — 원기날씨
EVIDENCE_THIN                    1건 — 쿠팡 (403 봇차단)
TRANSPORT_FAILURE                5건 — 캐시워크·Bill Letter·삼성월렛·이마트 트레이더스·대한항공
```

"모바일웹이 없다"고 말할 수 있는 것은 **1건**이다. 나머지는 접속 실패·증거 부족이며 서로 다른 사실이다.

### 3-3. "인증은 한 번 받으면 1년간 아무도 다시 확인하지 않는다"

**근거를 넘어선 서술이다.** `reports/legal_basis.md` 가 실제로 확인한 것은
"유효기간 중 정기 재측정을 의무화한 조항을 찾지 못했다"까지다.

정확한 표현: *현행 법령 검토에서는 유효기간 중 정기적인 전수 재측정을 의무화한 조항을 확인하지 못했다.*

### 3-4. 감사 원본 경로

`REPORT.md` 5-1 이 지목한 `/tmp/claude-1000/…/tasks/wf4pqcxm3.output` 는 존재하지 않는다.
실제 정본은 아카이브에 보존돼 있다.

```
research/refcohort/archive/audit_journal_wf_2b52c7fd-81d.json
sha256:15312d3945ab5f96d8b276ac61403011fdef277f7663b7a483bb94b5e2271c06
```

### 3-5. 코호트 대조 수치 전반

`REFERENCE 3.54 vs COMPARISON 5.90` 을 어떤 형태로도 인용하지 않는다.
실사용군은 증거계보가 깨졌고, 두 집단은 모집단 구성이 다르며, 관측 범위도 다르다.

## 4. Pilot 감사 결과 — 확정 19건

`research/refcohort/audit/findings_registry.jsonl` 에 복구했다 (저널 18건 + 신규 CRITICAL 1건).

```
CRITICAL 6 / HIGH 9 / MEDIUM 4
state:  OPEN 18 / FIXED 1  (target-size-overstrict-gap-rule, R4 시정)
verify: VERIFIED 17 / UNDER_VOTED 1 / VERIFIED_BY_DIRECT_MEASUREMENT 1
```

`UNDER_VOTED` 1건은 3표 중 2표가 세션 한도로 죽어 `votes=1` 로 남은 것이다.
Pilot 워크플로는 `votes > 0 && 반증 < 과반` 을 생존 조건으로 써서 **반증자가 죽으면 자동 기각**됐다.
따라서 Pilot 의 "기각 55건" 은 반증된 55건이 아니라 미검증이 섞인 55건이다.

→ Main Study 규칙: `votes == 0 → UNVERIFIED`. **자동 REJECT 금지.**

## 5. Pilot Archive 상태

| 항목 | 상태 |
|---|---|
| Git SHA 기록 | `32460b87334a67f6a74823ac55f85ca80a9f8980` |
| 원증거 manifest | `archive/pilot_evidence_manifest.jsonl` — 2,144 파일 / 699,196,558 B |
| 아카이브 사본 | `/mnt/c/ProjectFinal_archive/pilot_refcohort_32460b8/pilot_evidence.tar.gz` |
| | 506,088,301 B / 2,171 엔트리 / `gzip -t` OK |
| | `sha256:4a446a39dba96cd8407f1c3f6cb2ce18b6e042e8c35a0e263c08c166883407dc` |
| 감사 저널 | `archive/audit_journal_wf_2b52c7fd-81d.json` (540KB) |
| findings registry | `audit/findings_registry.jsonl` 19건 |
| **물리 이중화** | **미완** |

`/` 는 WSL ext4.vhdx, `/mnt/c` 는 NTFS 로 **논리적으로만 분리**돼 있다.
vhdx 손상·WSL 초기화에는 생존하지만 물리 디스크 장애에는 함께 소실된다.
`/mnt/d` 는 여유 997MB 로 부족하다. **외장 저장장치나 원격 위치 지정이 필요하다.**

## 6. Main Study 가 승계한 방지 장치

| Pilot 실패 | Main Study 조치 | 검증 |
|---|---|---|
| 표시명 기반 파일키 | `service_id = svc_ + sha256(로마자슬러그)[:16]` | 80건 전부 `^svc_[0-9a-f]{16}$`, 한글 0, 충돌 0 (적대적 감사 실측) |
| 레코드↔증거 오대응 | figure 파일↔URL 바인딩 검증 | IHDR 높이 대조 11/11 일치, 높이 전부 상이해 순열 검출 가능 |
| 감사 기록 유실 | 저널을 저장소로 복사 + 해시 등록 | `archive/` 에 정본 보존 |
| 미검증을 기각으로 흡수 | `votes == 0 → UNVERIFIED` | 자동 REJECT 금지 규칙 |
| append-only 미강제 | `engine_integrity` gate | **E001 전 필수, 현재 NOT_RUN** |
| UNDETERMINED → PASS 흡수 | `judgment_semantics` gate | **E001 전 필수, 현재 NOT_RUN** |

## 7. 이 문서의 용도

Pilot 을 부정하는 문서가 아니다.
**R1–R4 가 없었다면 Main Study 는 같은 실패를 처음부터 다시 했을 것이다.**

특히 2.1.3 에서 확립된 절차 — *원문 인용 → 코드 상수화 → 경계값 테스트 → 동일 증거 재판정* — 은
Main Study 의 criterion 검증 템플릿으로 그대로 쓴다.
89.8% 라는 극적인 수치를 41.0% 로 스스로 낮춘 그 판단이 이 연구의 방법론 신뢰도를 만든다.
