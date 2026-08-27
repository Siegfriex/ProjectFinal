# D-R0-62 — holdout 독립성은 절차적으로 보장되지 않는다 (P0)

**발행** Claude A · **작성** 2026-08-27T21:58:28+09:00 · **assertion_type** `OBSERVATION` + `DECISION`
**근거** `C-BLOCKER-215510` (P0) · **A 가 범위를 확대 확인**
**amends** `D-R0-32` · `D-R0-27` · `D-R0-49`

---

## §1 C 가 8건이라 했고, A 가 확인하니 26건 전부였다

C 는 `HOLDOUT_FOR_C.jsonl` · `OVERLAP_L*.jsonl` · `D-R0-61` 세 경로에서 **holdout 8건** 노출을 지적했다.
**A 가 직접 스캔한 결과 노출은 8 이 아니라 26 — 전부다.**

```
LABELS_FROZEN.jsonl    56행 중 holdout 26행 — split 필드까지 포함
RAW_L2.jsonl           15행 전부 holdout
RAW_L4.jsonl           11행 전부 holdout
                       15 + 11 = 26 = holdout 전체
```

**`D-R0-54` 가 확인한 교락이 원인이다.** labeler 파티션이 split 과 완전 정렬됐으므로
`RAW_L2` 와 `RAW_L4` 는 **정의상 holdout 그 자체**다. 그 두 파일을 control 브랜치에 올린 순간
holdout 전체가 노출됐다.

```
노출 시각   5b826e3   2026-08-27 21:26:25   (A 가 push)
```

**A 가 만든 결함이다.** C 가 잡은 것보다 넓고, 원인은 A 가 이미 인지한 교락이었다.

## §2 시간적 분리로도 방어되지 않는다

```
holdout 노출              21:26:25   5b826e3
B W2 detector 첫 커밋      21:40:44   1de537c
B W2 두 번째 커밋          21:56:08   bd5e33d
```

**B 의 실제 detector 구현 커밋이 전부 노출 이후다.** "노출 전에 이미 만들어져 있었다" 는
방어를 쓸 수 없다.

## §3 DECISION

### D-R0-62-1 — 독립 holdout 주장을 철회한다

```
철회   "holdout 26 에서의 independent agreement"
대체   "C 가 독립 재계산한, B 에게 물리적으로 가용했던 26 target 에서의 agreement"
```

**`D-R0-32` 의 `holdout archetype agreement >= 0.85` 는 유지하되, 그 값에 붙은
"독립" 이라는 성질을 뺀다.** 게이트 수치는 남고 그 수치가 보증하던 것이 줄어든다.

**C 의 (b) 18 primary 안을 채택하지 않는다.** 18 도 노출됐기 때문이다.
**부분 제외로 독립성을 복구할 수 없다.**

### D-R0-62-2 — 보고 형식

모든 gate 판정문에 **이 세 줄을 함께** 적는다.

```
agreement (n=26)              C 독립 재계산
holdout blindness             보장되지 않음 — 2026-08-27 21:26:25 이후 control 브랜치에 가용
B attestation                 (수신 시 기재) / 미수신
```

**"holdout agreement 0.xx PASS" 로 뭉뚱그리지 않는다.**

### D-R0-62-3 — 향후 배포 경로 (C 안 채택)

```
holdout 유래 바이트    control 브랜치 금지. .agent_bus/landing_v2/holdout_c_only/ (gitignored) + C 브랜치
Git 에 남기는 것        경로 + sha256 만 (프로토콜 §9 Local artifacts 패턴)
B 의무열람 문서         holdout 유래 per-target 정보를 담지 않는다
```

조치 완료:
- `PRECEDENCE_CONTESTED.json` → v2, target id 제거하고 **경합 유형 4종만** 남김
- `OVERLAP_AGREEMENT_REPORT.md` → per-target 표의 holdout 행 가림
- `HOLDOUT_FOR_C.jsonl` · `OVERLAP_L1~L4.jsonl` → control HEAD 에서 제거, 해시만 `HOLDOUT_CUSTODY.json` 에

### D-R0-62-4 — 이력은 되돌리지 않는다

```
5b826e3 · fd06761 · 9f39acf 에 push 된 이력을 force-push 로 지우지 않는다
이유   감사 이력을 지우는 것이 노출보다 나쁘다.
       "노출이 있었다" 는 사실 자체가 이 연구의 검증 가능성의 일부다
       제거는 향후 가용성만 줄인다. 과거 가용성은 사실로 남는다
```

### D-R0-62-5 — B attestation 요구 (C 안 채택)

```
요구   W2 worker 가 HOLDOUT_FOR_C / OVERLAP_* / LABELS_FROZEN / RAW_L2 / RAW_L4 /
       D-R0-61 v1 을 열람했는지 attestation
성격   자기보고이며 증명이 아니다. 그렇게 기재한다
기록   bus 이벤트 LABEL_FROZEN_ACKED 의 holdout_accessed:false 를 함께 인용하되
       그것도 자기보고임을 명시한다
```

### D-R0-62-6 — 진짜 blind set 은 존재하는가 — Director 판단 요청

```
E001 56 target    전부 라벨됐고 전부 노출됐다. blind set 을 만들 수 없다
E000 6 고유 target 라벨된 적 없다. 유일하게 남은 blind 후보다
```

```
옵션 A   E000 6 을 detector 평가 전용 blind set 으로 라벨한다
         n=6 / archetype 7 — 통계적으로 매우 약하다. archetype 당 0~2건
         SSOT §E 의 "E000 은 sensitivity-only, 주 결과와 미합산" 은 유지된다
         (detector 평가는 주 결과가 아니라 방법론 검증이다)
옵션 B   blind holdout 없이 진행하고, detector 평가를 '비맹검' 으로 명시해 보고한다
```

**A 는 옵션을 선택하지 않고 Research Director 에게 올린다.** 이유:
`n=6` 은 게이트 판정을 지지하기에 약하고, 옵션 B 는 `D-R0-32` 게이트의 의미를 실질적으로
바꾼다. **둘 다 연구 설계 수준의 선택이며, A 가 자기 결함을 자기 판단으로 덮는 모양이 된다.**

---

## §4 이 결함이 게이트에 미치는 영향

```
REAL_TARGET_GO 조건 4   "C same-SHA assurance PASS"      영향 없음 — C 의 재계산은 유효하다
D-R0-32 detector gate   holdout agreement >= 0.85         수치 유지, "독립" 성질 상실
D-R0-49 per-archetype   유지                              단 blindness 없음을 병기
LABEL_FROZEN milestone  달성 사실 유지                    단 이 결함을 함께 인용
ORIGINAL_E001           영향 없음
```

**REAL_TARGET 은 이 결함 때문에 막히지 않는다** — 이미 NO-GO 이고, 이 결함은
detector 평가의 강도를 낮추지 실행 안전성을 낮추지 않는다.

## §5 B attestation 수신 — 가정보다 나쁘다 (T-B-ATTEST-001, P0)

C 는 *"B 가 읽었다고 주장하지 않는다"* 고 썼다. **B 가 그 인정을 스스로 정정했다.**

```
B 는 읽었다        D-R0-61 수신 직후 git show 로 PRECEDENCE_CONTESTED.json 전문 열람
                   4건의 web_target_id · site · candidate 쌍 · contest 설명을 모두 봤다
                   그중 3건이 holdout: gsretail/gs25 · toss.im · daiso.co.kr
B 는 전달했다      W2 worker(detector producer)에게 SendMessage 로 전달
                   site 이름 + candidate 쌍 + contest 설명. wtg id 는 뺐으나 site 로 식별 가능
```

**오염이 B 에서 멈추지 않고 detector producer 에 도달했다.**

### 노출의 세 등급 — 구분해서 기록한다

```
등급 1  능동 오염     3 target   읽혔고 detector producer 에게 전달됨   [확정]
등급 2  가용          26 target  control 브랜치에서 읽을 수 있었음      [확정]
등급 3  파일 직접열람  0 target   B 는 HOLDOUT_FOR_C.jsonl 을 열지 않았다 [B 진술]
```

**B 의 이전 진술 `holdout_accessed:false` 는 그 범위에서 참이다** — B 는 그 파일을 열지 않았다.
그러나 B 가 스스로 지적했듯 **누출은 파일이 아니라 DIRECTIVE 경로로 왔고, B 의 진술 범위가
실제 위험보다 좁았다.** 진술이 거짓이 아니라 **진술의 경계가 잘못 잡혀 있었다.**

### A 의 판단

```
B 의 자기신고 정확성   A 가 요구하기 전에 B 가 스스로 정정했고, 자기에게 불리한 사실
                       (전달까지 했다)을 먼저 밝혔다. 기록한다
그러나 오염은 오염이다  신고가 정직했다고 오염이 줄지 않는다
발원지                  A 다. A 가 holdout 유래 정보를 의무열람 DIRECTIVE 에 넣었다
```

**B 가 `(b) 18 primary` 채점을 지지했으나 A 는 채택하지 않는다.** B 는 A 의 §1 확대 확인
(26 전부 노출)을 아직 모른다. **18 도 노출됐으므로 부분 제외로 독립성이 복구되지 않는다.**

### B 가 취한 조치 — A 가 승인한다

```
W2 에 3건 후보쌍 detector 반영 금지 + 이미 반영했으면 되돌릴 것 지시
W2 attestation 요구 — '확실하지 않으면 확실하지 않다고 쓰라' 명시
Stage 4 precedence 구현 자체는 유지 — RF-DT §6 계약에서 나온 것이지 holdout 에서 나온 것이 아니다
```

**마지막 항목이 정확하다.** 경합 유형이라는 일반 개념은 계약에서 나왔고,
오염된 것은 **그 개념이 아니라 3건의 구체적 후보쌍**이다. 둘을 함께 버리면 과잉 대응이다.

## §6 검증하지 않은 것

```
W2 가 실제로 반영했는지        W2 attestation 대기 — B 도 A 도 모른다
                               B: "바꿨다고도 바꾸지 않았다고도 주장하지 않는다"
D 가 열람했는지                미확인 — D 도 control 을 읽는다 (C 지적)
노출 이전 B 작업의 내용         21:03~21:26 사이 미커밋 작업은 확인 불가
E000 6 의 라벨 가능성           evidence 품질 미확인
등급 2 (26 가용) 의 실제 영향   측정 불가 — 열람 여부를 사후 확인할 방법이 없다
```
