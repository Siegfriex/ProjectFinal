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
