> ## ⚠ SUPERSEDED_FOR_SCOPE — v2 라우팅 배너
>
> **이 문서는 v1 인계문서다. 아래 본문의 실행범위(`LANDING_ONLY`)와 phase 이름은 무효다.**
>
> | 항목 | 현행 값 |
> |---|---|
> | 현행 실행권위 | `research/landing-accessibility-main` 브랜치의 `research/landing_accessibility/docs/v2/00_SSOT_v2.0.md` |
> | 권위 선언 | 같은 브랜치의 `research/landing_accessibility/docs/v2/EXECUTION_AUTHORITY.md` |
> | SCOPE | `L0_INITIAL_LANDING + L1_SHALLOW_REPRESENTATIVE_ENTRY` (v1 `LANDING_ONLY` 를 대체) |
> | HUMAN_FINAL_REVIEW_MAX | 5 |
> | 정지점 | `READY_FOR_E001_V2` (v1 `READY_FOR_E001` 이 아니다) |
> | Pilot | `research/refcohort-r1` @ `32460b8` — `READ_ONLY`. 수정 시 P0 |
>
> **이 문서에서 무엇이 유효한가**
>
> - 유효: 검증된 **사실** — SHA, 카운트, 데이터 상태, Hard Prohibitions.
> - 무효: **실행범위·phase 순서·다음 헌장 지정.** v2 문서가 대체한다.
> - 아래 본문은 이력 보존을 위해 **삭제하지 않는다.**
>
> **v2 문서를 읽는 법.** 이 브랜치(`control/landing-orchestrator`) 체크아웃에는 `docs/v2/` 가
> 파일로 존재하지 않는다. 다음 중 하나로 읽는다.
>
> ```bash
> git -C /home/sieg/projects-wsl/ProjectFinal show \
>   origin/research/landing-accessibility-main:research/landing_accessibility/docs/v2/EXECUTION_AUTHORITY.md
> # (v2 승격 전에는 아직 exec 브랜치에만 있다)
> git -C /home/sieg/projects-wsl/ProjectFinal show \
>   origin/agent/landing-v2-exec:research/landing_accessibility/docs/v2/00_SSOT_v2.0.md
> ```
>
> 근거: adversarial V2-C001 finding `orchestrator-entrypoint-still-routes-to-v1-scope` (P1/blocking).
> 시정: V2-C002 orchestrator.

---

# NEXT SESSION ENTRYPOINT

이 파일을 먼저 읽고 순서대로 진행한다.

1. **`docs/HANDOFF_PRE_ANALYSIS_START.md`** 를 읽는다.
2. **`docs/ProjectFinal_Landing_Accessibility_Data_Analysis_SSOT_v1.0.md`** 를 읽는다.
   (원격 사본: `control/handoff/preserved/`)
3. **remote refs를 재확인한다.** handoff 문서의 SHA를 현재값이라 가정하지 마라.
   ```bash
   git -C /home/sieg/projects-wsl/ProjectFinal fetch --all
   git -C /home/sieg/projects-wsl/ProjectFinal ls-remote --heads origin
   ```
4. **authoritative main만 분석 입력으로 사용한다.**
   `research/landing-accessibility-main` = `5a9015d1e95b1530...` (PROM-002)
5. **executor checkpoint `87a0464e` 는 UNVERIFIED다.**
   감사·승격을 거치지 않았다. 어떤 수치도 여기서 읽지 마라.
6. **P-A ANALYSIS FOUNDATION 부터 시작한다.**
7. **`READY_FOR_E001` 에서 반드시 정지한다.** E001은 Research Director GO 이후에만.

---

운영 헌장:

**`docs/PHASE_EXECUTION_DIRECTIVE_v5.0.md`**

---

현재 상태 요약:

```
status                SESSION_CLOSED_PRE_ANALYSIS
automation            HALTED
E001                  NOT STARTED
analysis SSOT drift   0
open P0               0
open blocking P1      0
open blocking P2      6
C013 WIP              21 files @ 87a0464e (UNVERIFIED)
```
