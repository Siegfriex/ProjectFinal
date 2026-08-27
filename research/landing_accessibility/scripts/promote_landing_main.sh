#!/usr/bin/env bash
# v3.1 §5 (v2 상속) — verified baseline 을 research/landing-accessibility-main 으로 승격한다.
# 오케스트레이터 전용. hook 이 아니라 이 스크립트가 검사의 정본이다 (§6: hook 은 유일 보증수단이 아니다).
#
# V2-C002 시정 — adversarial V2-C001 `promotion-clean-check-targets-wrong-worktree` (P1/blocking)
#   이전 버전은 exec 워크트리 경로를 `.agent_worktrees/landing_exec` 로 하드코딩했다.
#   v2 executor 는 `.agent_worktrees/landing_v2_exec` 이므로 clean 가드가 엉뚱한 워크트리를
#   검사해 항상 통과했다(vacuous). 이제 대상 SHA/브랜치로부터 워크트리를 해석하며,
#   해석에 실패하면 조용히 통과하지 않고 fail 한다 (fail-closed).
#
# V2-C003 시정 — adversarial V2-C002 두 건
#   `promotion-verdict-check-treats-missing-verdict-as-pass` (P2/V2_SSOT_FROZEN-blocking)
#     → [AUDIT_VERDICT] 재작성. verdict 미기록은 더 이상 통과하지 않는다.
#   `verify-script-declared-in-promotion-path-but-never-called` (P2/V2_SSOT_FROZEN-blocking)
#   / ssot V2-C002 `execution-authority-overclaims-verify-script-invocation`
#     → [INSTALL_INTEGRITY] 신설. verify_v2_docs.py 를 exec 워크트리에서 실제로 실행한다.
#
# V2-C004 시정 — adversarial V2-C003 세 건 + ssot V2-C003 한 건
#   `promotion-reads-uncommitted-state-json-with-no-second-source` (P2/V2_SSOT_FROZEN-blocking)
#     → [ORCH_TREE] 신설. control 워크트리도 dirty 검사하고, state.json 은 **커밋된 ref**
#       (`git show <orch_sha>:…/state.json`)에서만 읽는다. 워킹트리 사본이 커밋본과 다르면
#       차단하고 차이를 보고한다. 이후 [BLOCKING_DEBT]·[AUDIT_VERDICT] 는 커밋본만 본다.
#   `promotion-audit-sha-argument-not-pinned-to-recorded-audit-sha` (P2/V2_SSOT_FROZEN-blocking)
#     → [AUDIT_VERDICT] 에 핀 추가. 인자 감사 SHA 가 state.audit_lag 의
#       latest_adversarial_audit_sha / latest_ssot_audit_sha 와 정확히 일치해야 한다.
#       "다른 사이클/다른 커밋의 PASS 보고서 SHA" 경로를 막는다.
#   `prepush-hook-silent-skip-is-not-detected-anywhere` (P2/POST_E001_DEBT)
#     → [HOOK_INSTALL] 신설. 가장 먼저 pre-push 훅 설치 상태를 검증한다. 끊긴 심링크·미설치·
#       실행권한 없음·정본과 내용 불일치는 전부 차단이다. git 은 없는 훅을 **경고 없이 rc=0 으로**
#       건너뛰므로(adversarial 이 git 2.43.0 에서 격리 재현), 침묵을 여기서 깨뜨린다.
#   ssot V2-C003 `control-state-and-promote-header-mislabel-verify-check-number` (P2/POST_E001_DEBT)
#     → 검사를 **번호가 아니라 이름으로** 부른다. 검사를 삽입하면 번호가 밀리고, 그때마다
#       state.json·헤더·권위문서의 번호 서술이 어긋난다. 이름은 삽입에 영향을 받지 않는다.
#
# V2-C005 시정 — adversarial(Codex) V2-C004 `promotion-reconciliation-sha-is-dead-and-control-state-is-only-local-single-source`
#   (P2 / V2_SSOT_FROZEN-blocking / ADV-C004-04)
#   감사가 실증한 것: `reconciliation_sha` 자리에 commit 으로 해석조차 되지 않는 리터럴
#   `NOT_A_COMMIT` 을 넣었는데 [HOOK_INSTALL]→[SHA_RESOLVE]→[PILOT_IMMUTABLE]→[AUDIT_ANCESTRY]
#   →[EXEC_TREE]→[ORCH_TREE]→[INSTALL_INTEGRITY] 를 **전부 통과**했다. `REC_SHA` 는 argv 대입 1회 +
#   최종 echo 1회뿐인 dead argument 였다. `ORCH_SHA` 도 **로컬** control 워크트리 HEAD 에만 묶여
#   원격 control/reconciliation 권위와 연결되지 않았고, [BLOCKING_DEBT] 는 그 로컬 커밋의 state JSON
#   **하나만** 읽고 pinned 감사 보고서에서 debt 를 재계산하지 않았다.
#   → 네 개의 이름 있는 검사를 신설해 감사가 제시한 닫힘조건 4가지에 1:1 로 대응시킨다.
#     [REC_RESOLVE]           (1) REC_SHA^{commit} fail-closed resolve
#     [REC_REMOTE_AUTHORITY]  (2) 원격 control 권위 tip / 승인된 ancestry 대조
#     [REC_STATE_BIND]        (3) state.json 을 reconciliation commit 에 bind + reconciliation 산출물 검증
#     [DEBT_RECOMPUTE]        (4) pinned 감사 보고서·원장에서 blocking count·cycle·target 독립 재계산
#   부수 시정 — [AUDIT_ANCESTRY] 가 감사 브랜치 이름을 하드코딩하고 있었다. V2-C004 adversarial 감사는
#   Claude 세션 한도 중단으로 독립 감사자(Codex)가 `audit/landing-adversarial-codex-c004` 에서 수행했고,
#   하드코딩된 `audit/landing-adversarial` 로는 그 보고서를 **읽을 수조차 없다**. 이제 감사 브랜치는
#   원장(audit_lag.latest_*_audit_branch)이 선언하고, 검사는 `audit/landing-*` 네임스페이스 강제 +
#   원격 실시간 tip(ls-remote) 조상 검증으로 fail-closed 확인한다.
#
# 검사 이름과 실행 순서 (번호는 이 목록의 순서일 뿐이며, 인용은 **이름**으로 한다):
#    1 [HOOK_INSTALL]         pre-push 훅 설치 상태 — 정본 존재 · 심링크 유효 · 실행권한 · 내용 동일
#    2 [SHA_RESOLVE]          exec/감사 SHA 실재 + 정규화, exec·control 워크트리 해석
#    3 [REC_RESOLVE]          reconciliation SHA 를 commit 으로 fail-closed resolve
#    4 [REC_REMOTE_AUTHORITY] 원격 control 권위(ls-remote tip)와 REC/ORCH 의 tip·승인된 ancestry 관계
#    5 [PILOT_IMMUTABLE]      Pilot(research/refcohort) diff = 0
#    6 [EXEC_TREE]            exec 워크트리 clean + HEAD == 승격 대상 SHA
#    7 [ORCH_TREE]            control 워크트리 clean + state.json 워킹트리 == 커밋본
#    8 [REC_STATE_BIND]       state.json == reconciliation commit 본 + reconciliation 산출물 검증
#    9 [AUDIT_ANCESTRY]       두 감사 SHA 가 **원장이 선언한** 감사 브랜치의 원격 tip 조상
#   10 [INSTALL_INTEGRITY]    verify_v2_docs.py 실호출 (exec 워크트리 기준, exit != 0 · 부재 모두 차단)
#   11 [BLOCKING_DEBT]        원장의 open P0/P1 · v2_transition.open_blocking_total
#   12 [DEBT_RECOMPUTE]       pinned 감사 보고서 + 원장 항목에서 blocking·cycle·target 독립 재계산·대조
#                              + (V2-C012) 수용 조건의 id 정본 대조 · owner 면제 폐지 · audit_sha 실검증
#                              · gate 어휘 열거 · V2_SSOT_FROZEN/E001_V2 **양쪽** C-6 실효 판정
#                              + ACCEPTED_BOUNDED_RESIDUAL_RISK 명시적 제외 검증·건수 출력·C-6 자동 실효 (V2-C010)
#   13 [AUDIT_VERDICT]        audit lag · target sha · verdict(state + 보고서 JSON) · 감사 SHA 핀
#   reconciliation 검사는 **입력 검증**이므로 가장 앞 층(3·4)에 두고, 원장 bind 는 원장을 읽을 수 있게 된
#   직후(8)에 둔다. 무결성 검증은 exec **트리** 검사이므로 clean/HEAD 와 같은 층에 둔다.
#   원장(state.json)·verdict(감사 브랜치) 검사는 그 다음 층이다.
#
# usage:
#   promote_landing_main.sh <exec_sha> <adversarial_sha> <ssot_sha> <reconciliation_sha> [options]
# options:
#   --dry-run                 모든 검사를 수행하되 push 하지 않는다
#   --exec-branch=<ref>       exec 브랜치를 명시 (기본: exec_sha 로부터 워크트리 역해석)
#   --exec-worktree=<path>    exec 워크트리를 명시 (자동해석 우회, 존재 검증은 그대로)
#   --orch-sha=<sha>          state.json 을 읽을 control 커밋을 명시한다.
#                             (기본: control 워크트리 HEAD. 명시하면 HEAD 와 일치해야 한다.)
#
# <reconciliation_sha> 는 더 이상 장식이 아니다. 반드시 commit 으로 해석되어야 하고, 원격
# control 권위(origin/control/landing-orchestrator)의 tip 이거나 승인된 ancestry 여야 하며,
# 그 커밋의 state.json 이 원장으로 bind 되고, 그 커밋이 담은 reconciliation 산출물
# `control/cycles/<CYCLE>_RECONCILIATION.json` 이 exec SHA·두 감사 SHA·verdict·open_blocking_total
# 을 선언해야 한다. 어느 하나라도 없으면 차단이다 (fail-closed).
set -euo pipefail

REPO="/home/sieg/projects-wsl/ProjectFinal"
MAIN="research/landing-accessibility-main"
ORCH_BRANCH="control/landing-orchestrator"
PILOT_SHA="32460b87334a67f6a74823ac55f85ca80a9f8980"
STATE_REL="research/landing_accessibility/control/state.json"
# setup_worktree.sh 가 만드는 환경 심링크. 저장소 내용이 아니므로 dirty 판정에서 제외한다.
# (`.gitignore` 의 `.venv/` `node_modules/` 는 디렉터리 패턴이라 심링크에는 매치되지 않는다.)
ENV_SYMLINKS=".venv env node_modules"

fail() { echo "PROMOTION BLOCKED: $*" >&2; exit 1; }
note() { echo "  · $*"; }

TMPDIR_PROMOTE=""
cleanup() { [ -n "$TMPDIR_PROMOTE" ] && rm -rf "$TMPDIR_PROMOTE" || true; }
trap cleanup EXIT
TMPDIR_PROMOTE="$(mktemp -d)"

[ $# -ge 4 ] || fail "usage: promote_landing_main.sh <exec_sha> <adversarial_sha> <ssot_sha> <reconciliation_sha> [--dry-run] [--exec-branch=REF] [--exec-worktree=PATH] [--orch-sha=SHA]"
EXEC_SHA_IN="$1"; ADV_SHA_IN="$2"; SSOT_SHA_IN="$3"; REC_SHA_IN="$4"; shift 4
REC_SHA=""   # [REC_RESOLVE] 가 채운다. 그 전에는 비어 있다 — dead argument 재발 방지.

DRY_RUN=0
EXEC_BRANCH=""
EXEC_WT=""
ORCH_SHA_IN=""
for arg in "$@"; do
  case "$arg" in
    --dry-run)          DRY_RUN=1 ;;
    --exec-branch=*)    EXEC_BRANCH="${arg#*=}" ;;
    --exec-worktree=*)  EXEC_WT="${arg#*=}" ;;
    --orch-sha=*)       ORCH_SHA_IN="${arg#*=}" ;;
    *) fail "unknown option: $arg" ;;
  esac
done

git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || fail "$REPO 가 git 저장소가 아니다"

# ================================================================ [HOOK_INSTALL]
# V2-C004 시정 — adversarial V2-C003 `prepush-hook-silent-skip-is-not-detected-anywhere`
#   git 은 훅이 없거나 심링크가 끊겼거나 실행권한이 없으면 **경고 한 줄 없이 rc=0 으로**
#   push 를 통과시킨다(감사가 git 2.43.0 격리 저장소에서 재현). 훅은 유일 보증수단이 아니지만
#   (이 스크립트가 정본이다) 신뢰경계가 **조용히** 사라지는 것 자체가 결함이다.
#   승격 경로에서 가장 먼저 이 침묵을 깨뜨린다. 통과 우회 옵션은 두지 않는다 (fail-closed).
#
#   설치 방식은 심링크가 옳다 — adversarial V2-C003 §2.3 판정:
#     core.hooksPath 는 수명 의존이 동일하면서 저장소의 다른 훅을 전부 무효화하고,
#     복사 모드는 정본과 drift 한다(그 drift 가 V2-C002 finding 자체였다).
#   따라서 방식은 유지하고 **탐지**를 붙인다. 이 검사는 .git/hooks/ 를 수정하지 않는다.
HOOK_SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/hooks"
CANON_HOOK="$HOOK_SRC_DIR/pre-push"
[ -f "$CANON_HOOK" ] \
  || fail "pre-push 훅 정본이 없다: $CANON_HOOK (저장소 정본 부재 — 설치 상태를 대조할 기준이 없다)"

GIT_COMMON_DIR="$(git -C "$REPO" rev-parse --git-common-dir)"
case "$GIT_COMMON_DIR" in /*) ;; *) GIT_COMMON_DIR="$REPO/$GIT_COMMON_DIR" ;; esac
HOOKS_PATH_CFG="$(git -C "$REPO" config --get core.hooksPath || true)"
if [ -n "$HOOKS_PATH_CFG" ]; then
  case "$HOOKS_PATH_CFG" in /*) ;; *) HOOKS_PATH_CFG="$REPO/$HOOKS_PATH_CFG" ;; esac
  ACTIVE_HOOK="$HOOKS_PATH_CFG/pre-push"
  HOOK_MODE="core.hooksPath=$HOOKS_PATH_CFG"
else
  ACTIVE_HOOK="$GIT_COMMON_DIR/hooks/pre-push"
  HOOK_MODE="core.hooksPath unset → $GIT_COMMON_DIR/hooks"
fi

if [ -L "$ACTIVE_HOOK" ] && [ ! -e "$ACTIVE_HOOK" ]; then
  fail "pre-push 훅 심링크가 끊겼다 (dangling): $ACTIVE_HOOK -> $(readlink "$ACTIVE_HOOK")"$'\n'"  git 은 이 상태에서 훅을 **경고 없이 건너뛴다** — Pilot 보호·main 직접 push 차단·감사 계보 append-only 가 전부 무력화된다."$'\n'"  복구: research/landing_accessibility/scripts/install_hooks.sh --symlink"
fi
[ -e "$ACTIVE_HOOK" ] \
  || fail "pre-push 훅이 설치돼 있지 않다: $ACTIVE_HOOK ($HOOK_MODE)"$'\n'"  git 은 훅 부재를 오류로 알리지 않는다 — 승격 경로에서 차단한다."$'\n'"  설치: research/landing_accessibility/scripts/install_hooks.sh --symlink"
[ -f "$ACTIVE_HOOK" ] \
  || fail "pre-push 훅이 일반 파일이 아니다: $ACTIVE_HOOK"
[ -x "$ACTIVE_HOOK" ] \
  || fail "pre-push 훅에 실행권한이 없다: $ACTIVE_HOOK — git 은 실행권한 없는 훅을 조용히 건너뛴다"
cmp -s "$CANON_HOOK" "$ACTIVE_HOOK" \
  || fail "pre-push 훅 내용이 저장소 정본과 다르다 (DRIFT): $ACTIVE_HOOK != $CANON_HOOK"$'\n'"  추적되지 않는 로컬 사본이 정본을 가리는 상태다 (adversarial V2-C002 repo-canonical-pre-push-hook-is-inert-legacy-copy-in-effect 의 재발)."
if [ -L "$ACTIVE_HOOK" ]; then
  note "[HOOK_INSTALL] OK — $ACTIVE_HOOK -> $(readlink "$ACTIVE_HOOK") (내용 = 정본, 실행권한 있음, $HOOK_MODE)"
else
  note "[HOOK_INSTALL] OK — $ACTIVE_HOOK (일반 파일, 내용 = 정본, 실행권한 있음, $HOOK_MODE)"
fi

# ================================================================ [SHA_RESOLVE]
EXEC_SHA="$(git -C "$REPO" rev-parse --verify --quiet "${EXEC_SHA_IN}^{commit}" || true)"
[ -n "$EXEC_SHA" ] || fail "exec SHA 를 해석할 수 없다: $EXEC_SHA_IN"
[ "$EXEC_SHA" = "$EXEC_SHA_IN" ] || note "exec sha 정규화: $EXEC_SHA_IN -> $EXEC_SHA"

# 감사 SHA 도 정규화한다 — [AUDIT_VERDICT] 의 핀이 state 기록(40-hex)과 문자열 비교이기 때문이다.
ADV_SHA="$(git -C "$REPO" rev-parse --verify --quiet "${ADV_SHA_IN}^{commit}" || true)"
[ -n "$ADV_SHA" ] || fail "adversarial 감사 SHA 를 해석할 수 없다: $ADV_SHA_IN"
SSOT_SHA="$(git -C "$REPO" rev-parse --verify --quiet "${SSOT_SHA_IN}^{commit}" || true)"
[ -n "$SSOT_SHA" ] || fail "ssot 감사 SHA 를 해석할 수 없다: $SSOT_SHA_IN"

# `git worktree list --porcelain` 을 파싱해 (path, HEAD, branch) 3튜플을 뽑는다.
worktree_table() {
  git -C "$REPO" worktree list --porcelain | awk '
    /^worktree /  { if (p != "") print p "\t" h "\t" b; p=substr($0,10); h=""; b="" }
    /^HEAD /      { h=substr($0,6) }
    /^branch /    { b=substr($0,8) }
    /^detached$/  { b="(detached)" }
    END           { if (p != "") print p "\t" h "\t" b }
  '
}

# $1 = 찾을 branch ref (refs/heads/...) — 매칭되는 worktree path 를 출력
worktree_for_branch() {
  worktree_table | awk -F'\t' -v b="$1" '$3==b { print $1 }'
}
# $1 = 찾을 HEAD sha — 매칭되는 worktree path 를 출력
worktree_for_head() {
  worktree_table | awk -F'\t' -v h="$1" '$2==h { print $1 }'
}

resolve_exec_worktree() {
  local found=""
  if [ -n "$EXEC_BRANCH" ]; then
    found="$(worktree_for_branch "refs/heads/${EXEC_BRANCH#refs/heads/}")"
    [ -n "$found" ] || fail "exec 브랜치 '$EXEC_BRANCH' 에 붙은 워크트리가 없다 (git worktree list 확인)"
  else
    found="$(worktree_for_head "$EXEC_SHA")"
    if [ -z "$found" ]; then
      # HEAD 가 정확히 일치하는 워크트리가 없다 — 브랜치 경유로 한 번 더 시도한다.
      local br
      br="$(git -C "$REPO" for-each-ref --format='%(refname)' --contains "$EXEC_SHA" refs/heads/ 2>/dev/null | head -1 || true)"
      [ -n "$br" ] || fail "exec SHA $EXEC_SHA 를 포함하는 로컬 브랜치가 없다 — 워크트리를 해석할 수 없다"
      found="$(worktree_for_branch "$br")"
      [ -n "$found" ] || fail "exec SHA $EXEC_SHA 에 대응하는 워크트리를 찾지 못했다 (후보 브랜치 $br). --exec-worktree= 로 명시하거나 워크트리를 생성하라"
    fi
  fi
  [ "$(printf '%s\n' "$found" | wc -l)" -eq 1 ] \
    || fail "exec 워크트리 후보가 여러 개다 — --exec-worktree= 로 명시하라:"$'\n'"$found"
  printf '%s' "$found"
}

# dirty 판정: 추적파일 변경은 무조건 dirty. 미추적 항목은 환경 심링크 3종만 면제한다.
worktree_dirty_lines() {
  local wt="$1" line status path
  git -C "$wt" status --porcelain | while IFS= read -r line; do
    status="${line:0:2}"; path="${line:3}"
    if [ "$status" = "??" ]; then
      for allow in $ENV_SYMLINKS; do
        if { [ "$path" = "$allow" ] || [ "$path" = "$allow/" ]; } && [ -L "$wt/$allow" ]; then
          continue 2
        fi
      done
    fi
    printf '%s\n' "$line"
  done
}

if [ -n "$EXEC_WT" ]; then
  [ -d "$EXEC_WT" ] || fail "--exec-worktree 경로가 없다: $EXEC_WT"
  git -C "$EXEC_WT" rev-parse --git-dir >/dev/null 2>&1 || fail "--exec-worktree 가 git 워크트리가 아니다: $EXEC_WT"
else
  EXEC_WT="$(resolve_exec_worktree)"
fi
note "exec worktree = $EXEC_WT"

ORCH_WT="$(worktree_for_branch "refs/heads/$ORCH_BRANCH")"
[ -n "$ORCH_WT" ] || fail "orchestrator 브랜치 '$ORCH_BRANCH' 에 붙은 워크트리가 없다 — state.json 을 읽을 수 없다"
[ "$(printf '%s\n' "$ORCH_WT" | wc -l)" -eq 1 ] || fail "orchestrator 워크트리 후보가 여러 개다:"$'\n'"$ORCH_WT"
ORCH_HEAD="$(git -C "$ORCH_WT" rev-parse HEAD)"
if [ -n "$ORCH_SHA_IN" ]; then
  ORCH_SHA="$(git -C "$REPO" rev-parse --verify --quiet "${ORCH_SHA_IN}^{commit}" || true)"
  [ -n "$ORCH_SHA" ] || fail "--orch-sha 를 해석할 수 없다: $ORCH_SHA_IN"
  [ "$ORCH_SHA" = "$ORCH_HEAD" ] \
    || fail "control 워크트리 HEAD($ORCH_HEAD) != --orch-sha($ORCH_SHA) — 원장을 읽을 커밋과 워크트리가 다르다"
else
  ORCH_SHA="$ORCH_HEAD"
fi
note "orchestrator worktree = $ORCH_WT @ $ORCH_SHA"

# ================================================================ [REC_RESOLVE]
# V2-C005 시정 (1/4) — adversarial(Codex) V2-C004 ADV-C004-04 닫힘조건 ①
#   `REC_SHA^{commit}` 을 fail-closed 로 resolve 한다. 해석 불가·미존재·commit 이 아닌 객체는
#   즉시 차단이다. 감사가 통과시킨 리터럴 `NOT_A_COMMIT` 이 바로 여기서 죽는다.
REC_SHA="$(git -C "$REPO" rev-parse --verify --quiet "${REC_SHA_IN}^{commit}" || true)"
[ -n "$REC_SHA" ] \
  || fail "reconciliation SHA 를 commit 으로 해석할 수 없다: $REC_SHA_IN"$'\n'"  reconciliation_sha 는 장식이 아니다 — 이 인자는 승격 판정의 원장을 고정하는 커밋이어야 한다."$'\n'"  (adversarial V2-C004 ADV-C004-04: 이전 버전은 이 값을 해석조차 하지 않고 출력만 했다.)"
[ "$REC_SHA" = "$REC_SHA_IN" ] || note "reconciliation sha 정규화: $REC_SHA_IN -> $REC_SHA"
note "[REC_RESOLVE] reconciliation commit = $REC_SHA OK"

# ================================================================ [REC_REMOTE_AUTHORITY]
# V2-C005 시정 (2/4) — 닫힘조건 ②
#   로컬 HEAD 는 권위가 아니다. 원격 control 브랜치의 **실시간 tip** 을 ls-remote 로 직접 읽어
#   (a) reconciliation commit 이 그 tip 이거나 **승인된 ancestry** 인지, (b) 원장을 읽을 control
#   커밋(ORCH_SHA)이 실제로 push 돼 있는지를 확인한다.
#   승인된 ancestry 정의 — REC_SHA 가 tip 의 조상이면서, tip 의 state.json 이 REC_SHA 의 것과
#   **바이트 동일**할 때만 허용한다. 그 사이 원장이 갱신됐다면 reconciliation 은 current 가 아니다
#   (PHASE_GATES §2 '오케스트레이터 reconciliation 이 current').
#   로컬 원격추적 ref(origin/…)는 stale 할 수 있으므로 신뢰하지 않는다.
REMOTE_ORCH_LINE="$(git -C "$REPO" ls-remote origin "refs/heads/$ORCH_BRANCH" 2>/dev/null || true)"
[ -n "$REMOTE_ORCH_LINE" ] \
  || fail "원격에 control 브랜치가 없다: origin/$ORCH_BRANCH"$'\n'"  원격 reconciliation 권위를 조회할 수 없으면 승격하지 않는다 (fail-closed)."
REMOTE_ORCH_TIP="${REMOTE_ORCH_LINE%%$'\t'*}"
case "$REMOTE_ORCH_TIP" in
  [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) ;;
  *) fail "원격 control tip 을 해석할 수 없다: '$REMOTE_ORCH_LINE'" ;;
esac
git -C "$REPO" fetch --quiet origin "refs/heads/$ORCH_BRANCH" \
  || fail "원격 control 브랜치를 fetch 할 수 없다: origin/$ORCH_BRANCH (오프라인 통과 금지 — fail-closed)"
git -C "$REPO" rev-parse --verify --quiet "$REMOTE_ORCH_TIP^{commit}" >/dev/null \
  || fail "원격 control tip 객체를 로컬에서 해석할 수 없다: $REMOTE_ORCH_TIP"

git -C "$REPO" merge-base --is-ancestor "$REC_SHA" "$REMOTE_ORCH_TIP" 2>/dev/null \
  || fail "reconciliation commit 이 원격 control 권위와 무관하다."$'\n'"  rec=$REC_SHA"$'\n'"  origin/$ORCH_BRANCH tip=$REMOTE_ORCH_TIP"$'\n'"  reconciliation 은 원격에 게시된 control 계보 위에서만 성립한다 (PHASE_GATES §2 / 05 §10)."
git -C "$REPO" merge-base --is-ancestor "$ORCH_SHA" "$REMOTE_ORCH_TIP" 2>/dev/null \
  || fail "원장을 읽을 control 커밋이 원격에 push 되지 않았다 (local-only)."$'\n'"  orch=$ORCH_SHA"$'\n'"  origin/$ORCH_BRANCH tip=$REMOTE_ORCH_TIP"$'\n'"  push 되지 않은 로컬 clean 커밋 하나가 zero debt 와 감사 핀을 주장하는 경로를 막는다 (ADV-C004-04)."

if [ "$REC_SHA" = "$REMOTE_ORCH_TIP" ]; then
  note "[REC_REMOTE_AUTHORITY] reconciliation == 원격 control tip ($REMOTE_ORCH_TIP) OK"
else
  git -C "$REPO" show "$REC_SHA:$STATE_REL" > "$TMPDIR_PROMOTE/state.rec.json" 2>/dev/null \
    || fail "reconciliation commit 에 state.json 이 없다: $REC_SHA:$STATE_REL"
  git -C "$REPO" show "$REMOTE_ORCH_TIP:$STATE_REL" > "$TMPDIR_PROMOTE/state.tip.json" 2>/dev/null \
    || fail "원격 control tip 에 state.json 이 없다: $REMOTE_ORCH_TIP:$STATE_REL"
  cmp -s "$TMPDIR_PROMOTE/state.rec.json" "$TMPDIR_PROMOTE/state.tip.json" \
    || fail "reconciliation commit 이후 원격 control 원장이 갱신됐다 — reconciliation 이 current 가 아니다."$'\n'"  rec=$REC_SHA"$'\n'"  origin/$ORCH_BRANCH tip=$REMOTE_ORCH_TIP"$'\n'"  더 새로운 원장이 원격에 있으면 그 원장으로 다시 reconcile 한 뒤 승격한다 (PHASE_GATES §2)."
  note "[REC_REMOTE_AUTHORITY] reconciliation($REC_SHA) 은 원격 tip($REMOTE_ORCH_TIP) 의 승인된 ancestry — 원장 바이트 동일 OK"
fi

# ================================================================ [PILOT_IMMUTABLE]
[ -z "$(git -C "$REPO" diff --stat "$PILOT_SHA" "$EXEC_SHA" -- research/refcohort)" ] \
  || fail "Pilot path diff != 0 (research/refcohort 는 READ_ONLY, 수정 시 P0)"
note "[PILOT_IMMUTABLE] OK"

# ================================================================ [EXEC_TREE]
WT_HEAD="$(git -C "$EXEC_WT" rev-parse HEAD)"
[ "$WT_HEAD" = "$EXEC_SHA" ] \
  || fail "exec 워크트리 HEAD($WT_HEAD) != 승격 대상 SHA($EXEC_SHA) — 검증한 트리와 승격되는 SHA 가 다르다"
DIRTY="$(worktree_dirty_lines "$EXEC_WT")"
[ -z "$DIRTY" ] || fail "exec 워크트리 dirty ($EXEC_WT):"$'\n'"$DIRTY"
note "[EXEC_TREE] clean + HEAD == $EXEC_SHA OK (환경 심링크 $ENV_SYMLINKS 만 면제)"

# ================================================================ [ORCH_TREE]
# V2-C004 시정 — adversarial V2-C003 `promotion-reads-uncommitted-state-json-with-no-second-source`
#   이전 버전은 state.json 을 control 워크트리의 **워킹트리 파일**에서 읽으면서 dirty 검사는
#   exec 워크트리에만 걸었다. control 워크트리에서 open_blocking_total 을 커밋 없이 0 으로
#   고치면 [BLOCKING_DEBT] 가 통과했고, 그 편집은 승격 커밋에 남지도 않았다.
#   이제 (1) control 워크트리도 dirty 검사하고 (2) 원장은 커밋된 ref 에서만 읽으며
#   (3) 워킹트리 사본이 커밋본과 다르면 차단하고 차이를 보고한다.
ORCH_DIRTY="$(worktree_dirty_lines "$ORCH_WT")"
[ -z "$ORCH_DIRTY" ] || fail "control(orchestrator) 워크트리 dirty ($ORCH_WT):"$'\n'"$ORCH_DIRTY"$'\n'"  state.json 은 승격 판정의 원장이다. 커밋되지 않은 편집은 승격 근거가 될 수 없다."
STATE_COMMITTED="$TMPDIR_PROMOTE/state.committed.json"
git -C "$REPO" show "$ORCH_SHA:$STATE_REL" > "$STATE_COMMITTED" 2>/dev/null \
  || fail "커밋된 state.json 을 읽을 수 없다: $ORCH_SHA:$STATE_REL"
STATE_WT="$ORCH_WT/$STATE_REL"
[ -f "$STATE_WT" ] || fail "state.json 워킹트리 사본이 없다: $STATE_WT"
if ! cmp -s "$STATE_COMMITTED" "$STATE_WT"; then
  STATE_DIFF="$(diff -u "$STATE_COMMITTED" "$STATE_WT" | head -40 || true)"
  fail "state.json 워킹트리 사본이 커밋본($ORCH_SHA)과 다르다."$'\n'"  커밋본: $ORCH_SHA:$STATE_REL"$'\n'"  워킹트리: $STATE_WT"$'\n'"$STATE_DIFF"
fi
# 이후 모든 원장 검사는 **커밋본만** 읽는다. 워킹트리 사본은 더 이상 입력이 아니다.
STATE="$STATE_COMMITTED"
note "[ORCH_TREE] clean + state.json 워킹트리 == 커밋본($ORCH_SHA) OK — 원장은 커밋본에서 읽는다"

# ================================================================ [REC_STATE_BIND]
# V2-C005 시정 (3/4) — 닫힘조건 ③
#   원장(state.json)을 reconciliation commit 에 **bind** 한다. [ORCH_TREE] 가 확인한 것은
#   "워킹트리 == ORCH_SHA 커밋본" 까지이며, 그 커밋이 reconciliation 과 같은 원장을 담는다는
#   보장이 없었다. 이제 REC_SHA 의 state.json 을 읽어 ORCH_SHA 의 것과 바이트 대조하고,
#   **이후 모든 원장 검사의 입력을 REC_SHA 본으로 바꾼다.**
#   또한 reconciliation 이 무엇인지를 산출물로 못박는다 — control/cycles/<CYCLE>_RECONCILIATION.json
#   이 exec SHA·두 감사 SHA·두 verdict·open_blocking_total·promotion_authorized 를 담아야
#   "reconciliation 이 current" 라고 말할 수 있다. 부재·파싱실패·필드부재·불일치는 전부 차단이다.
STATE_REC="$TMPDIR_PROMOTE/state.reconciliation.json"
git -C "$REPO" show "$REC_SHA:$STATE_REL" > "$STATE_REC" 2>/dev/null \
  || fail "reconciliation commit 에 state.json 이 없다: $REC_SHA:$STATE_REL"
if ! cmp -s "$STATE_REC" "$STATE_COMMITTED"; then
  BIND_DIFF="$(diff -u "$STATE_REC" "$STATE_COMMITTED" | head -40 || true)"
  fail "원장이 reconciliation commit 에 bind 되지 않는다."$'\n'"  reconciliation: $REC_SHA:$STATE_REL"$'\n'"  control 커밋본: $ORCH_SHA:$STATE_REL"$'\n'"$BIND_DIFF"
fi
# 원장의 정본은 이제 reconciliation commit 본이다.
STATE="$STATE_REC"

python3 - "$STATE" "$REPO" "$REC_SHA" "$EXEC_SHA" "$ADV_SHA" "$SSOT_SHA" <<'PY' || fail "reconciliation 산출물 검증 실패"
import json, re, subprocess, sys

state_path, repo, rec_sha, exec_sha, adv_sha, ssot_sha = sys.argv[1:7]
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


try:
    s = json.load(open(state_path, encoding="utf-8"))
except Exception as e:  # noqa: BLE001
    die("reconciliation commit 의 state.json 파싱 실패: %s" % e)

al = s.get("audit_lag")
if not isinstance(al, dict):
    die("reconciliation commit 의 state.json 에 audit_lag 가 없다")
cycle = al.get("latest_exec_cycle")
if not isinstance(cycle, str) or not cycle:
    die("audit_lag.latest_exec_cycle 가 없다 — 어느 사이클의 reconciliation 인지 알 수 없다")
if al.get("latest_reconciled_cycle") != cycle:
    die("audit_lag.latest_reconciled_cycle(%r) != latest_exec_cycle(%r) — reconciliation 이 current 가 아니다 "
        "(PHASE_GATES §2)" % (al.get("latest_reconciled_cycle"), cycle))

rel = "research/landing_accessibility/control/cycles/%s_RECONCILIATION.json" % cycle.replace("-", "_")
r = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (rec_sha, rel)], capture_output=True)
if r.returncode != 0:
    die("reconciliation 산출물이 없다: %s:%s\n"
        "  reconciliation 은 선언이 아니라 **파일**이어야 한다 — exec SHA·두 감사 SHA·verdict 를 담은\n"
        "  control/cycles/<CYCLE>_RECONCILIATION.json 이 그 앵커다 (ADV-C004-04 닫힘조건).\n"
        "  %s" % (rec_sha, rel, r.stderr.decode("utf-8", "replace").strip()))
try:
    rc = json.loads(r.stdout.decode("utf-8"))
except Exception as e:  # noqa: BLE001
    die("reconciliation 산출물 JSON 파싱 실패: %s:%s (%s)" % (rec_sha, rel, e))
if not isinstance(rc, dict):
    die("reconciliation 산출물이 객체가 아니다: %s:%s" % (rec_sha, rel))

if rc.get("schema") != "landing-accessibility-reconciliation-v1":
    die("reconciliation 산출물 schema(%r) 불일치 — 'landing-accessibility-reconciliation-v1' 이어야 한다"
        % (rc.get("schema"),))
if rc.get("cycle") != cycle:
    die("reconciliation 산출물 cycle(%r) != audit_lag.latest_exec_cycle(%r)" % (rc.get("cycle"), cycle))
if rc.get("target_exec_sha") != exec_sha:
    die("reconciliation 산출물 target_exec_sha(%r) != 승격 대상 exec(%s)" % (rc.get("target_exec_sha"), exec_sha))

for auditor, argv_sha in (("adversarial", adv_sha), ("ssot", ssot_sha)):
    blk = rc.get(auditor)
    if not isinstance(blk, dict):
        die("reconciliation 산출물에 %s 블록이 없다" % auditor)
    rec_audit_sha = blk.get("audit_sha")
    if not isinstance(rec_audit_sha, str) or not HEX40.match(rec_audit_sha):
        die("reconciliation 산출물 %s.audit_sha(%r) 가 40-hex 가 아니다" % (auditor, rec_audit_sha))
    if rec_audit_sha != argv_sha:
        die("reconciliation 산출물 %s.audit_sha(%s) != 승격 인자(%s) — reconciliation 이 고정한 감사와 "
            "승격 인자가 다르다" % (auditor, rec_audit_sha, argv_sha))
    if blk.get("verdict") != "PASS":
        die("reconciliation 산출물 %s.verdict = %r — PASS 가 아닌 reconciliation 으로는 승격할 수 없다 "
            "(PHASE_GATES 「판정 권한」절 = §5: 두 감사 PASS + reconciliation 후 Gate close. "
            "절 제목으로 부른다 — 절 번호는 절 신설로 밀린다)" % (auditor, blk.get("verdict")))

obt = rc.get("open_blocking_total")
if not isinstance(obt, int) or isinstance(obt, bool):
    die("reconciliation 산출물 open_blocking_total 이 정수가 아니다 (%r)" % (obt,))
if obt != 0:
    die("reconciliation 산출물 open_blocking_total = %d — 00_SSOT_v2.0 §15 open blocking = 0 위반" % obt)
if rc.get("decision") != "PROMOTE":
    die("reconciliation 산출물 decision = %r — 'PROMOTE' 가 아니다" % (rc.get("decision"),))
if rc.get("promotion_authorized") is not True:
    die("reconciliation 산출물 promotion_authorized 가 true 가 아니다 (%r)" % (rc.get("promotion_authorized"),))
if not rc.get("reconciled_at"):
    die("reconciliation 산출물에 reconciled_at 이 없다")
PY
note "[REC_STATE_BIND] 원장 == $REC_SHA:$STATE_REL · reconciliation 산출물 검증 OK — 이후 원장은 reconciliation 본에서 읽는다"

# ================================================================ [AUDIT_ANCESTRY]
# V2-C005 시정 — 감사 브랜치 하드코딩 제거.
#   이전 버전은 `audit/landing-adversarial` / `audit/landing-ssot` 를 문자열로 박아 두었다.
#   V2-C004 adversarial 감사는 Claude 세션 한도 중단으로 독립 감사자(Codex)가
#   `audit/landing-adversarial-codex-c004` 에서 수행했고, 하드코딩된 이름으로는 그 보고서를
#   읽을 수도 계보를 확인할 수도 없다. 브랜치는 원장이 선언하고, 여기서 fail-closed 로 검증한다:
#     · audit_lag.latest_{adversarial,ssot}_audit_branch 필수 (부재 = 차단)
#     · `audit/landing-*` 네임스페이스만 허용 (임의 브랜치로의 우회 차단)
#     · 원격에 실재해야 한다 — **ls-remote 실시간 tip** 을 쓴다. 로컬 origin/… 추적 ref 는 stale 할
#       수 있고, "감사 보고서가 아직 push 되지 않았다" 를 통과시키면 안 된다.
AUDIT_BRANCH_DECL="$(python3 - "$STATE" 2>&1 <<'PY'
import json, re, sys
try:
    al = json.load(open(sys.argv[1], encoding="utf-8")).get("audit_lag")
except Exception as e:  # noqa: BLE001
    sys.exit("state.json 파싱 실패: %s" % e)
if not isinstance(al, dict):
    sys.exit("state.json 에 audit_lag 가 없다")
NS = re.compile(r"^audit/landing-[A-Za-z0-9._/-]+$")
rows = []
for auditor, key in (("adversarial", "latest_adversarial_audit_branch"),
                     ("ssot", "latest_ssot_audit_branch")):
    br = al.get(key)
    if not isinstance(br, str) or not br:
        sys.exit("audit_lag.%s 가 없다 — 감사 브랜치를 하드코딩하지 않으므로 원장이 선언해야 한다 (fail-closed)" % key)
    if not NS.match(br):
        sys.exit("audit_lag.%s = %r 가 audit/landing-* 네임스페이스가 아니다 — 임의 브랜치는 감사 계보가 아니다" % (key, br))
    rows.append("%s\t%s" % (auditor, br))
print("\n".join(rows))
PY
)" || fail "감사 브랜치 선언을 읽을 수 없다:"$'\n'"$AUDIT_BRANCH_DECL"

ADV_BRANCH=""; SSOT_BRANCH=""
while IFS="$(printf '\t')" read -r _who _br; do
  case "$_who" in
    adversarial) ADV_BRANCH="$_br" ;;
    ssot)        SSOT_BRANCH="$_br" ;;
  esac
done <<EOF
$AUDIT_BRANCH_DECL
EOF
[ -n "$ADV_BRANCH" ] && [ -n "$SSOT_BRANCH" ] || fail "감사 브랜치 선언 파싱 실패:"$'\n'"$AUDIT_BRANCH_DECL"

for A in "adversarial|$ADV_SHA|$ADV_BRANCH" "ssot|$SSOT_SHA|$SSOT_BRANCH"; do
  who="${A%%|*}"; rest="${A#*|}"; sha="${rest%%|*}"; br="${rest#*|}"
  line="$(git -C "$REPO" ls-remote origin "refs/heads/$br" 2>/dev/null || true)"
  [ -n "$line" ] \
    || fail "$who 감사 브랜치가 원격에 없다: origin/$br"$'\n'"  감사 보고서가 push 되지 않았으면 승격 검사가 원격 보고서를 읽을 수 없다 (fail-closed)."
  tip="${line%%$'\t'*}"
  git -C "$REPO" fetch --quiet origin "refs/heads/$br" \
    || fail "$who 감사 브랜치를 fetch 할 수 없다: origin/$br"
  git -C "$REPO" merge-base --is-ancestor "$sha" "$tip" 2>/dev/null \
    || fail "$who 감사 SHA 가 원격 감사 브랜치 tip 의 조상이 아니다: $sha !<= origin/$br($tip)"
  note "[AUDIT_ANCESTRY] $who $sha <= origin/$br ($tip)"
done
note "[AUDIT_ANCESTRY] 두 감사 SHA 가 원장이 선언한 감사 브랜치의 원격 tip 조상 OK"

# ================================================================ [INSTALL_INTEGRITY]
# V2-C003 시정 — adversarial V2-C002 `verify-script-declared-in-promotion-path-but-never-called`
#                / ssot V2-C002 `execution-authority-overclaims-verify-script-invocation`
#   EXECUTION_AUTHORITY §8 은 '이 스크립트는 … 승격 경로에서 호출된다' 고 선언했으나 실제
#   호출이 0건이었다(선언이 거짓). PHASE_GATES `V2_SSOT_FROZEN` 통과조건
#   (`scripts/verify_v2_docs.py exit 0`)을 여기서 실제로 실행해 강제한다.
#   경로는 exec 워크트리 기준으로 해석하고, 없으면 조용히 건너뛰지 않고 차단한다.
VERIFY_SCRIPT="$EXEC_WT/research/landing_accessibility/scripts/verify_v2_docs.py"
[ -f "$VERIFY_SCRIPT" ] \
  || fail "무결성 검증 스크립트가 exec 워크트리에 없다: $VERIFY_SCRIPT"$'\n'"  (EXECUTION_AUTHORITY §8 / PHASE_GATES V2_SSOT_FROZEN 통과조건 — 부재는 건너뛰기가 아니라 차단이다)"
VERIFY_OUT="$(python3 "$VERIFY_SCRIPT" 2>&1)" \
  || fail "verify_v2_docs.py exit != 0 — 설치 무결성 검증 실패 ($VERIFY_SCRIPT):"$'\n'"$VERIFY_OUT"
note "[INSTALL_INTEGRITY] verify_v2_docs.py exit 0 OK — $(printf '%s' "$VERIFY_OUT" | tail -1)"

# ================================================================ [BLOCKING_DEBT]
# 입력은 reconciliation commit 의 state.json ($STATE) 이다 — [ORCH_TREE] 가 워킹트리 == ORCH_SHA 커밋본을,
# [REC_STATE_BIND] 가 ORCH_SHA 커밋본 == REC_SHA 커밋본을 이미 단언했다.
# 이 검사는 원장이 **주장하는** 값을 읽는다. 그 주장의 독립 재계산은 다음 [DEBT_RECOMPUTE] 가 한다.
BLOCK="$(python3 - "$STATE" <<'PY'
import json, sys
s = json.load(open(sys.argv[1], encoding="utf-8"))
msgs = []
p0 = [x for x in s.get("open_p0", []) if str(x.get("state", "")).startswith("OPEN")]
if p0:
    msgs.append("open P0 = %d (%s)" % (len(p0), ", ".join(x.get("id", "?") for x in p0)))
p1 = [x for x in s.get("open_p1", []) if str(x.get("state", "")).startswith("OPEN")]
if p1:
    msgs.append("open P1 = %d (%s)" % (len(p1), ", ".join(x.get("id", "?") for x in p1)))
v2 = s.get("v2_transition")
if v2 is None:
    msgs.append("v2_transition 이 state.json 에 없다 — v2 부채 승계가 선언되지 않았다 "
                "(adversarial V2-C001 v1-open-debt-ledger-not-adopted-by-v2-authority)")
else:
    obt = v2.get("open_blocking_total")
    if not isinstance(obt, dict) or "total" not in obt:
        msgs.append("v2_transition.open_blocking_total 이 없거나 형식이 잘못됐다")
    elif int(obt["total"]) != 0:
        # breakdown 은 사이클마다 항목이 늘 수 있으므로 하드코딩하지 않고 전량 출력한다.
        parts = ", ".join("%s=%s" % (k, v) for k, v in obt.items()
                          if k not in ("formula", "total", "gate", "gate_satisfied", "note",
                                       "recomputation") and not isinstance(v, (dict, list)))
        msgs.append("v2_transition.open_blocking_total = %d (%s) "
                    "— 00_SSOT_v2.0 §15 open blocking = 0 위반"
                    % (int(obt["total"]), parts))
print("\n".join(msgs))
PY
)"
[ -z "$BLOCK" ] || fail "blocking debt:"$'\n'"$BLOCK"
# 명시적 제외(ACCEPTED_BOUNDED_RESIDUAL_RISK)는 합계가 0 이어도 **항상 한 줄로 보인다.**
# 합계만 출력하면 수용된 잔여가 승격 로그에서 조용히 사라진다 (adversarial fed3e70 §7 C-1).
ACCEPTED_LINE="$(python3 - "$STATE" <<'PY'
import json, sys
obt = (json.load(open(sys.argv[1], encoding="utf-8")).get("v2_transition") or {}).get("open_blocking_total") or {}
n = obt.get("accepted_bounded_residual_risk") or 0
ids = obt.get("accepted_residual_ids") or []
print("명시적 제외 %s건%s" % (n, (" — " + "; ".join(str(i).split(" — ")[0] for i in ids)) if ids else ""))
PY
)"
note "[BLOCKING_DEBT] open P0/P1 = 0 · v2_transition.open_blocking_total = 0 OK (원장 = $REC_SHA reconciliation 본) · $ACCEPTED_LINE"

# ================================================================ [DEBT_RECOMPUTE]
# V2-C005 시정 (4/4) — 닫힘조건 ④
#   [BLOCKING_DEBT] 는 원장이 **주장하는** 스칼라 open_blocking_total 하나만 읽는다.
#   그 값이 틀렸거나 조작됐으면 게이트 전체가 무력화된다(ADV-C004-04: single source).
#   여기서는 두 개의 독립 원천에서 다시 센다.
#     (A) pinned 감사 보고서 JSON — counts 를 믿지 않고 findings[] 에서 직접 센 뒤 counts 와 대조한다.
#         보고서의 cycle·target_sha·auditor 도 원장 기록과 대조한다.
#     (B) 원장의 **항목들** — v1 debt_inheritance.items, v2_audit_findings.cycles[*].{adversarial,ssot}.findings,
#         orchestrator_registered.findings 를 직접 세어 스칼라 total 과 대조한다.
#     (C) v1 승계분의 **독립 원천** — state.debt_ledger(v1 시절 원장) 와 그 원장의 git 앵커
#         (debt_inheritance.v1_ledger_git_anchor). V2-C006 신설. (B) 하나만 보면 v1 항목을
#         지우고 total 을 1 낮춘 자기일관적 state 가 통과한다 — 감사가 실측한 구멍이다.
#     (D) ACCEPTED_BOUNDED_RESIDUAL_RISK **명시적 제외**. V2-C010 신설 — adversarial V2-C008
#         focused (fed3e70) §7 C-1 이행. 이 상태값은 CLOSED 가 아니다: 결함은 해소되지 않았고
#         감사가 잔여 위험을 조건부로 수용한 것이다. 따라서 합계에서 빠지되 **조용히 사라져서는 안 된다.**
#         이 블록은 그 항목을 (a) 원장의 상태값 정의 존재, (b) 필수 근거 필드 전건,
#         (c) accepted_by_audit_sha 커밋에서 실제로 읽히는 감사 보고서의
#             id 일치 · verdict=ACCEPT_RECLASSIFY · new_class=ACCEPTED_BOUNDED_RESIDUAL_RISK,
#         (d) C-6-2 선례 제한 3요건 기록, (e) 선언된 제외 카운터·id 열거와의 일치
#         로 검증하고 **제외 건수를 별도 출력**한다. 하나라도 없으면 차단이다 —
#         근거 없는 제외로 total 을 낮추는 경로는 counted_as_open=false 쪽과 똑같이 막는다.
#         또 C-6 **자동 실효**를 검사한다 (V2-C012 에서 전면 재작성 — adversarial V2-C011 §5.4):
#         두 트리거 게이트 각각에 대해 필수 조건 집합을 **명시적으로** 검사한다.
#           gates.V2_SSOT_FROZEN 이 achieved 어휘로 선언 → C-1 · C-2 · C-5-1 전건 SATISFIED 요구
#           gates.E001_V2       이 achieved 어휘로 선언 → C-3 · C-4 · C-5-2 전건 SATISFIED 요구
#         하나라도 아니면 그 항목을 **다시 open blocking 으로 센다** (새 감사 finding 없이 실효되므로).
#         조건 id 집합은 스크립트 하드코딩 정본과 정확히 일치해야 하고, SATISFIED 는 **owner 와 무관하게
#         전부** audit_sha 실검증(40-hex · commit resolve · 감사 브랜치 조상 · 보고서 판정)을 요구한다.
#         V2-C010 판의 owner=="control" 면제는 **폐지됐다** — owner 는 공격자가 편집하는 필드였다.
#   (A)와 (B)와 (C)와 스칼라가 전부 일치하고 0 일 때만 통과한다. 하나라도 어긋나면 차단이다.
#   중복계상 제외(counted_as_open=false)는 duplicate_of / superseded_by 근거가 있을 때만 허용한다 —
#   근거 없는 조용한 제외로 total 을 낮추는 경로를 막는다.
#   이 블록은 argv 만으로 독립 실행 가능하게 썼다 (감사자가 그대로 떼어내 공격할 수 있어야 한다).
#   V2-C012 에서 추출 지점을 마커로 명시했다 — (D) 판정부만 떼어내려면
#     DR_HEAD_BEGIN..DR_HEAD_END  +  DR_D_BEGIN..DR_D_SKIP_BEGIN  +  DR_D_SKIP_END..DR_D_END
#     + 구동부(tally 호출 · obt 바인딩)  +  DR_D2_BEGIN..DR_D2_END
#   를 이어 붙이면 된다. (A)/(C) 는 pinned 감사 보고서를 요구하므로 SKIP 구간에 넣었다.
python3 - "$STATE" "$REPO" "$EXEC_SHA" "$ADV_SHA" "$SSOT_SHA" "$REC_SHA" <<'PY' || fail "blocking debt 독립 재계산 불일치"
# ---8<--- DR_HEAD_BEGIN
import json, re, subprocess, sys

state_path, repo, exec_sha, adv_sha, ssot_sha, rec_sha = sys.argv[1:7]
HEX40 = re.compile(r"^[0-9a-f]{40}$")
state_rel = "research/landing_accessibility/control/state.json"


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def closed(state_str):
    return str(state_str or "OPEN").upper().startswith("CLOSED")


try:
    s = json.load(open(state_path, encoding="utf-8"))
except Exception as e:  # noqa: BLE001
    die("state.json 파싱 실패: %s" % e)

al = s.get("audit_lag")
v2 = s.get("v2_transition")
if not isinstance(al, dict) or not isinstance(v2, dict):
    die("state.json 에 audit_lag / v2_transition 이 없다")
# ---8<--- DR_HEAD_END

# ---8<--- DR_D_BEGIN
# --- (D) ACCEPTED_BOUNDED_RESIDUAL_RISK 준비 ---
#
# V2-C012 시정 — adversarial V2-C011 (0dfb6d5788631347d4d50793f25d3f689251e1bd) §5.4
#   `c-6-lapse-machine-check-bypassable-and-e001-half-unimplemented`
#
#   감사는 이 블록을 원문 그대로 떼어내 21종을 주입했다. control 이 주장한 13종은 **전부 재현 차단**됐으나
#   감사가 새로 만든 8종(N1~N7 · N9)은 **전부 통과**했다. 8종 전부가 C-6 자동 실효 트리거의 우회다.
#   감사 원문이 이름 붙인 구멍은 **H-1~H-5 다섯 개**다 (H-6·H-7·H-8 은 원문에 존재하지 않는다).
#
#     H-1 조건 식별의 무결성 없음        N2 항목삭제 · N3 소문자 · N4 null · N7 뒤 공백 1개
#     H-2 owner 가 자기신고 필드          N1 owner 를 "exec" → "control" 로 갈아끼움
#     H-3 조건 audit_sha 가 truthiness    N5 쓰레기 문자열 "x"
#     H-4 gate 선언이 접두 매칭           N6 "DECLARED / FROZEN — 선언 완료"
#     H-5 E001_V2 절반이 미구현           N9 gates.E001_V2=ACHIEVED + C-3/C-4 미충족
#
#   아래가 그 다섯을 닫는다. 설계 원칙은 **fail-closed** 다 — 판단이 서지 않는 입력은 통과가 아니라 차단이다.
#
#   H-1 → _ABRR_CANON 하드코딩 정본과 `conditions` · `conditions_status` 의 **id 집합 정확 일치**를
#         강제한다. 한쪽에만 있는 id 는 차단. 정규화는 strip + 내부공백 축약 + upper 이며,
#         정규화 **후 충돌**(서로 다른 조건이 같아짐)이 생기면 그 자체로 차단이다.
#         `due_before` 는 문자열/None 형식 검증 후 정본과 **정확 대조**한다 — 정본을 조용히 채택하지 않고,
#         어긋나면 차단이다. 소문자·공백·null·임의값이 전부 여기서 죽는다.
#   H-2 → **owner 기반 면제를 폐지했다.** owner 는 더 이상 검증 강도를 정하지 않는다.
#         SATISFIED 로 적힌 조건은 owner 와 무관하게 **전부 동일 강도**로 audit_sha 근거를 요구한다.
#         면제가 있던 실질 근거(C-1 은 control 소관이고 원장 문면 자체로 기계검증된다)는 소멸했다 —
#         adversarial V2-C011 §5 가 C-1 을 독립 판정했으므로 C-1 에도 감사 근거가 실재한다.
#         owner 는 정본 대조 대상으로만 남는다(H-1 경로). 자기신고가 검증을 약화시키는 구조 자체를 없앴다.
#   H-3 → verify_condition_audit_sha() 가 [AUDIT_ANCESTRY] 와 **같은 강도**로 검증한다:
#         (a) 40-hex, (b) git 에서 commit 으로 resolve, (c) 원장이 선언한 audit/landing-* 브랜치 tip 의 조상,
#         (d) 그 커밋의 감사 보고서 JSON 이 **그 조건 id 를 실제로 긍정 판정**했는지.
#   H-4 → gate_declared_achieved() 가 선언값의 첫 토큰을 열거 어휘와 **정확 대조**한다.
#         접두 매칭을 쓰지 않으므로 "DECLARED"·"FROZEN"·"TRUE" 가 전부 achieved 로 잡히고,
#         어휘 밖 토큰은 fail-open 이 아니라 **차단**이다. 트리거 게이트 키의 **부재도 차단**이다
#         (키를 지워 트리거를 잠재우는 경로).
#   H-5 → _ABRR_CANON[*]["gate_required"] 로 **게이트별 필수 조건 집합을 명시적으로** 코딩한다.
#         어휘의 lapse_rule 이 요구하는 두 집합이 서로 다르므로 그 차이를 그대로 적는다:
#             V2_SSOT_FROZEN ← C-1 · C-2 · C-5-1        (문서 조건)
#             E001_V2        ← C-3 · C-4 · C-5-2        (산출물 조건)
#         여기에 due_before → 게이트 사상(_DUE_BEFORE_GATE)을 **합집합**으로 더한다. 둘 중
#         어느 경로로든 잡히면 실효다 — 더 강한 쪽을 취한다.
#
#   **정직한 한계 (원장이 자기 검사에 대해 실제보다 강하게 주장하지 않는다):**
#     L-1 조건 근거 판정 검사는 audit_sha 커밋 트리의 감사 보고서 JSON **전부**를 훑어
#         「그 id 를 긍정 판정한 자리가 하나라도 있는가」를 본다. 같은 트리의 **더 오래된** 보고서가
#         그 조건을 부정 판정하고 있어도 veto 하지 않는다 (신판이 구판을 대체하는 것이 정상이므로).
#         따라서 「그 조건을 긍정 판정한 적이 있는 감사 커밋」을 고르는 자유는 남는다.
#         브랜치 조상 검사와 정본 대조가 그 자유를 audit/landing-* 계보 안으로 가둔다.
#     L-2 `_ABRR_CANON` 은 **이 파일**이 정본이다. 새 수용을 부여하려면 감사 판정과 함께 여기에
#         정본을 추가해야 한다 — 정본이 없는 id 의 ABRR 은 제외되지 않고 **차단**된다.
#         이것은 의도된 마찰이다(원장 자기신고만으로 제외를 만들 수 없게 한다).
#     L-3 `FINAL_REPORT` 는 원장 `gates` 에 선언된 키가 아니다. 따라서 C-5-2 의 due_before 경로는
#         현재 **비활성**이며, C-5-2 는 gate_required 의 E001_V2 집합 쪽에서만 잡힌다.
#         원장 lapse_rule 문면이 C-5-② 를 E001_V2 절에 묶었으므로 그 문면을 따랐고, 그쪽이 더 엄격하다.
#     L-4 이 블록은 원장 **문면**을 검사한다. 조건의 실질 이행 자체는 감사 보고서가 판정한다.
ABRR = "ACCEPTED_BOUNDED_RESIDUAL_RISK"
residual_seen = []      # 원장에 있는 ABRR 항목 전부 (선언값 대조용)
accepted_residual = []  # 그중 수용이 유효한 것 — 합계에서 제외
lapsed_residual = []    # C-6 자동 실효로 open 복귀한 것
pending_residual = []   # 아직 선언 전이라 유효하나 미충족 조건이 남은 것
verified_residual = []  # 조건 근거(audit_sha) 실검증 결과 — 무엇을 근거로 SATISFIED 인지 출력한다
VOCAB = (v2.get("finding_state_vocabulary") or {}).get(ABRR)

# --- 조건 정본 (H-1 · H-2 · H-5) — 원장이 아니라 이 파일이 정본이다 ---
_ABRR_CANON = {
    "rc-6-r1-same-authorization-local-reexecution-unbounded": {
        "granted_by": "adversarial fed3e70ba8430e0fad4f27df11d2eca550f33d30 §7 C-1..C-6",
        # id -> (owner, due_before)   due_before None = 기한 개념이 없는 조건(C-6 은 실효 규칙 자신이다)
        "conditions": {
            "C-1":   ("control",      "V2_SSOT_FROZEN"),
            "C-2":   ("exec",         "V2_SSOT_FROZEN"),
            "C-3":   ("exec/control", "E001_V2_EXECUTION"),
            "C-4":   ("두 감사",       "E001_V2_COMPLETION"),
            "C-5-1": ("exec",         "V2_SSOT_FROZEN"),
            "C-5-2": ("연구자",        "FINAL_REPORT"),
            "C-6":   ("-",            None),
        },
        # 게이트별 필수 조건 집합 — 어휘 lapse_rule (C-6-1) 을 그대로 코딩한 것이다.
        # 두 집합은 서로 다르다. 그 차이가 H-5 의 본체다.
        "gate_required": {
            "V2_SSOT_FROZEN": ("C-1", "C-2", "C-5-1"),
            "E001_V2":        ("C-3", "C-4", "C-5-2"),
        },
    },
}
_DUE_BEFORE_GATE = {
    "V2_SSOT_FROZEN":     "V2_SSOT_FROZEN",
    "E001_V2_EXECUTION":  "E001_V2",
    "E001_V2_COMPLETION": "E001_V2",
    "FINAL_REPORT":       "FINAL_REPORT",
}
# --- gate 선언 어휘 (H-4) — 접두 매칭을 쓰지 않는다 ---
_GATE_TOKEN_ACHIEVED = frozenset((
    "ACHIEVED", "DECLARED", "FROZEN", "PROMOTED", "PROMOTED_VERIFIED", "PASS", "PASSED",
    "TRUE", "YES", "MET", "SATISFIED", "COMPLETE", "COMPLETED", "DONE", "SET", "ON",
))
_GATE_TOKEN_NOT_ACHIEVED = frozenset((
    "NOT_ACHIEVED", "NOT_DECLARED", "NOT_RUN", "NOT_YET", "NOT_MET", "NOT_SET", "NOT_FROZEN",
    "UNACHIEVED", "BLOCKED", "PENDING", "DEFERRED", "IN_PROGRESS", "OPEN",
    "FAIL", "FAILED", "FALSE", "NO", "INVALIDATED", "SUPERSEDED", "WITHDRAWN",
))


def norm_token(x):
    """공백 정규화 + 대문자. 정규화가 서로 다른 값을 같게 만들 수 있으므로 호출부에서 충돌을 검사한다."""
    return re.sub(r"\s+", " ", str(x)).strip().upper()


def gate_declared_achieved(gate_name):
    """H-4 — 게이트 선언값의 첫 토큰을 열거 어휘와 정확 대조한다.

    키 부재 · 비문자열 · 어휘 밖 토큰은 전부 **차단**이다. '모르는 값 = 미선언' 으로 넘기면
    실효 트리거를 임의 문구로 잠재울 수 있다(N6).
    """
    gates = s.get("gates")
    if not isinstance(gates, dict):
        die("state.json 에 gates 객체가 없다 — 게이트 선언 없이 C-6 실효를 판정할 수 없다 (fail-closed)")
    if gate_name not in gates:
        die("gates.%s 선언이 없다 — C-6 실효 트리거 게이트는 원장에 **명시적으로** 선언돼 있어야 한다. "
            "키를 지워 트리거를 잠재우는 경로를 막는다 (fail-closed)" % gate_name)
    raw = gates.get(gate_name)
    if not isinstance(raw, str) or not raw.strip():
        die("gates.%s(%r) 가 비어 있지 않은 문자열이 아니다 — 게이트 선언 어휘를 읽을 수 없다" % (gate_name, raw))
    m = re.match(r"[A-Za-z0-9_]+", raw.strip().upper())
    if not m:
        die("gates.%s 선언(%r)에서 상태 토큰을 읽을 수 없다" % (gate_name, raw[:120]))
    tok = m.group(0)
    if tok in _GATE_TOKEN_NOT_ACHIEVED:
        return False
    if tok in _GATE_TOKEN_ACHIEVED:
        return True
    die("gates.%s 선언의 상태 토큰 %r 이 열거 어휘 밖이다 (원문 앞 120자: %r)\n"
        "  achieved     = %s\n  not achieved = %s\n"
        "  어휘 밖 값을 '미선언' 으로 통과시키지 않는다 — 접두 매칭 우회를 막는다 (H-4, fail-closed)"
        % (gate_name, tok, raw[:120],
           ", ".join(sorted(_GATE_TOKEN_ACHIEVED)), ", ".join(sorted(_GATE_TOKEN_NOT_ACHIEVED))))


# --- 조건 audit_sha 실검증 (H-3) ---
_AUDIT_TIPS = {}
_REPORTS_AT = {}
_ADJ_AFFIRM = ("SATISFIED", "MET", "FULFILLED", "이행", "충족")
_ADJ_NEGATE = ("NOT_SATISFIED", "NOT SATISFIED", "UNSATISFIED", "UNMET", "NOT_MET", "NOT MET",
               "NOT_YET_DUE", "NOT YET DUE", "NOT_TRIGGERED", "미충족", "미이행", "불충족", "미도래")


def audit_branch_tips():
    """원장이 선언한 감사 브랜치의 tip. [AUDIT_ANCESTRY] 와 같은 원천을 쓴다."""
    if _AUDIT_TIPS:
        return _AUDIT_TIPS
    for key in ("latest_adversarial_audit_branch", "latest_ssot_audit_branch"):
        br = al.get(key)
        if not isinstance(br, str) or not re.match(r"^audit/landing-[A-Za-z0-9._/-]+$", br):
            die("audit_lag.%s(%r) 가 audit/landing-* 네임스페이스가 아니다 — 조건 근거의 계보를 "
                "확인할 기준 브랜치가 없다 (fail-closed)" % (key, br))
        tip = ""
        rp = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "--quiet",
                             "refs/remotes/origin/%s^{commit}" % br], capture_output=True)
        if rp.returncode == 0:
            tip = rp.stdout.decode("utf-8", "replace").strip()
        else:
            lsr = subprocess.run(["git", "-C", repo, "ls-remote", "origin", "refs/heads/%s" % br],
                                 capture_output=True)
            if lsr.returncode == 0 and lsr.stdout.strip():
                tip = lsr.stdout.decode("utf-8", "replace").split("\t", 1)[0].strip()
        if not HEX40.match(tip or ""):
            die("감사 브랜치 origin/%s 의 tip 을 확인할 수 없다 — 계보를 확인할 수 없는 근거로 조건을 "
                "SATISFIED 로 적을 수 없다 (fail-closed)" % br)
        _AUDIT_TIPS[br] = tip
    return _AUDIT_TIPS


def reports_at(sha):
    """그 커밋 트리의 감사 보고서 JSON 전부. 경로를 원장이 고르게 두지 않는다."""
    if sha in _REPORTS_AT:
        return _REPORTS_AT[sha]
    out = []
    lt = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only", sha,
                         "research/landing_accessibility/audit/"], capture_output=True)
    if lt.returncode == 0:
        for path in lt.stdout.decode("utf-8", "replace").splitlines():
            if not path.endswith(".json"):
                continue
            rr = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (sha, path)], capture_output=True)
            if rr.returncode != 0:
                continue
            try:
                out.append((path, json.loads(rr.stdout.decode("utf-8", "replace"))))
            except Exception:  # noqa: BLE001
                continue
    _REPORTS_AT[sha] = out
    return out


def adjudication_hits(node, want):
    """보고서 어딘가에서 조건 want 를 **긍정 판정**한 자리를 찾는다.

    보고서마다 자리가 다르다 — condition_adjudications[] · acceptance_conditions_status.conditions[] ·
    c_5_1_verdict 처럼 조건 id 를 **키 이름**에 담은 필드까지 재귀로 훑는다.
    부정 어휘가 섞인 값은 긍정으로 세지 않는다("UNMET" 이 "MET" 로 잡히는 것을 막는다).
    """
    alias = want.lower().replace("-", "_")
    hits = []

    def affirmative(blob):
        t = norm_token(blob)
        if any(n.upper() in t for n in _ADJ_NEGATE):
            return False
        return any(a.upper() in t for a in _ADJ_AFFIRM)

    def walk(n, keyed):
        if isinstance(n, dict):
            if keyed or norm_token(n.get("id")) == want:
                for vk in ("verdict", "state", "status", "result", "adjudication"):
                    v = n.get(vk)
                    if isinstance(v, str) and affirmative(v):
                        hits.append("%s=%s" % (vk, v[:80]))
            for k, v in n.items():
                walk(v, alias in str(k).lower().replace("-", "_"))
        elif isinstance(n, list):
            for v in n:
                walk(v, keyed)

    walk(node, False)
    return hits


def verify_condition_audit_sha(where, cid, raw_sha):
    """H-3 — 조건 근거 SHA 를 [AUDIT_ANCESTRY] 와 같은 강도로 검증한다."""
    if not isinstance(raw_sha, str) or not HEX40.match(raw_sha.strip()):
        die("%s 의 조건 %s 가 SATISFIED 인데 audit_sha(%r) 가 40-hex 전체 SHA 가 아니다 — "
            "truthiness 로 충족되지 않는다. owner 와 무관하게 **모든** 조건에 같은 강도를 적용한다 "
            "(H-2·H-3, self-approval 금지)" % (where, cid, raw_sha))
    sha = raw_sha.strip()
    rp = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "--quiet", "%s^{commit}" % sha],
                        capture_output=True)
    if rp.returncode != 0 or rp.stdout.decode("utf-8", "replace").strip() != sha:
        die("%s 의 조건 %s audit_sha(%s) 가 이 저장소의 커밋으로 resolve 되지 않는다" % (where, cid, sha))
    tips = audit_branch_tips()
    on = [br for br, tip in sorted(tips.items())
          if subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", sha, tip],
                            capture_output=True).returncode == 0]
    if not on:
        die("%s 의 조건 %s audit_sha(%s) 가 원장이 선언한 감사 브랜치(%s) tip 의 조상이 아니다 — "
            "감사 계보 밖 커밋은 조건 충족 근거가 아니다 (fail-closed)"
            % (where, cid, sha, ", ".join("origin/%s" % b for b in sorted(tips))))
    hits = []
    for path, rep in reports_at(sha):
        for h in adjudication_hits(rep, cid):
            hits.append("%s [%s]" % (path.rsplit("/", 1)[-1], h))
    if not hits:
        die("%s 의 조건 %s audit_sha(%s) 커밋의 감사 보고서 어디에도 %s 를 긍정 판정한 자리가 없다 — "
            "그 보고서가 **그 조건을 실제로 판정했는지**까지 본다. 계보만 맞는 임의 감사 커밋을 "
            "근거로 붙일 수 없다 (H-3, fail-closed)" % (where, cid, sha, cid))
    return "%s <= %s · %s" % (sha[:7], "/".join("origin/%s" % b for b in on), hits[0])

# ---8<--- DR_D_SKIP_BEGIN
#   (A)/(원장 사이클 대조) 구간. pinned 감사 보고서를 요구하므로 (D) 판정부만 떼어내 공격할 때는
#   이 구간을 건너뛴다. DR_D_SKIP_END 까지가 그 범위다.
cycle = al.get("latest_exec_cycle")
if not isinstance(cycle, str) or not cycle:
    die("audit_lag.latest_exec_cycle 가 없다")

# --- 감사 SHA 핀 (이 블록만 떼어내 실행해도 성립해야 한다) ---
PINS = (("adversarial", adv_sha, "latest_adversarial_audit_sha", "latest_adversarial_audited_cycle",
         "latest_adversarial_target_sha", "latest_adversarial_audit_branch"),
        ("ssot", ssot_sha, "latest_ssot_audit_sha", "latest_ssot_audited_cycle",
         "latest_ssot_target_sha", "latest_ssot_audit_branch"))

reports = {}
for auditor, argv_sha, sha_key, cyc_key, tgt_key, br_key in PINS:
    rec = al.get(sha_key)
    if not isinstance(rec, str) or not HEX40.match(rec):
        die("audit_lag.%s 가 40-hex 전체 SHA 가 아니다 (%r)" % (sha_key, rec))
    if rec != argv_sha:
        die("%s 감사 SHA 핀 불일치: 인자 %s != audit_lag.%s %s" % (auditor, argv_sha, sha_key, rec))
    cyc = al.get(cyc_key)
    if cyc != cycle:
        die("audit_lag.%s(%r) != latest_exec_cycle(%r) — 승격 대상 사이클을 감사한 보고서가 아니다"
            % (cyc_key, cyc, cycle))
    if al.get(tgt_key) != exec_sha:
        die("audit_lag.%s(%r) != exec(%s)" % (tgt_key, al.get(tgt_key), exec_sha))

    path = "research/landing_accessibility/audit/%s/%s.json" % (auditor, str(cyc).replace("-", "_"))
    r = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (argv_sha, path)], capture_output=True)
    if r.returncode != 0:
        die("%s 감사 보고서를 읽을 수 없다: %s:%s (%s)"
            % (auditor, argv_sha, path, r.stderr.decode("utf-8", "replace").strip()))
    try:
        rep = json.loads(r.stdout.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        die("%s 감사 보고서 JSON 파싱 실패: %s:%s (%s)" % (auditor, argv_sha, path, e))
    if rep.get("cycle") != cycle:
        die("%s 보고서 cycle(%r) != %r" % (auditor, rep.get("cycle"), cycle))
    if rep.get("target_sha") != exec_sha:
        die("%s 보고서 target_sha(%r) != 승격 대상(%s)" % (auditor, rep.get("target_sha"), exec_sha))
    if rep.get("auditor") != auditor:
        die("%s 보고서 auditor 필드(%r) 불일치" % (auditor, rep.get("auditor")))
    reports[auditor] = rep

# --- (A) 보고서에서 직접 센다. counts 는 대조 대상이지 근거가 아니다. ---
report_blocking = {}
for auditor, rep in reports.items():
    findings = rep.get("findings")
    if not isinstance(findings, list):
        die("%s 보고서에 findings 배열이 없다 — 재계산 불가 (fail-closed)" % auditor)
    counted = [f for f in findings
               if f.get("blocking") is True and not closed(f.get("status", f.get("state")))]
    n = len(counted)
    declared = (rep.get("counts") or {}).get("blocking")
    if not isinstance(declared, int) or isinstance(declared, bool):
        die("%s 보고서 counts.blocking 이 정수가 아니다 (%r)" % (auditor, declared))
    if declared != n:
        die("%s 보고서 내부 불일치: counts.blocking=%d 인데 findings[] 에서 센 open blocking=%d "
            "(%s)" % (auditor, declared, n, ", ".join(str(f.get("id")) for f in counted)))
    report_blocking[auditor] = n

# --- 원장이 그 사이클을 어떻게 등재했는지 대조 ---
vaf = v2.get("v2_audit_findings")
if not isinstance(vaf, dict) or not isinstance(vaf.get("cycles"), list):
    die("v2_transition.v2_audit_findings.cycles 가 없다")
cyc_entry = None
for c in vaf["cycles"]:
    if c.get("cycle") == cycle:
        cyc_entry = c
        break
if cyc_entry is None:
    die("원장에 사이클 %s 이(가) 등재돼 있지 않다 — 감사 결과가 원장에 반영되기 전에는 승격할 수 없다" % cycle)
if cyc_entry.get("target_sha") != exec_sha:
    die("원장 cycles[%s].target_sha(%r) != exec(%s)" % (cycle, cyc_entry.get("target_sha"), exec_sha))
for auditor in ("adversarial", "ssot"):
    blk = cyc_entry.get(auditor)
    if not isinstance(blk, dict):
        die("원장 cycles[%s].%s 가 없다" % (cycle, auditor))
    if blk.get("audit_sha") != (adv_sha if auditor == "adversarial" else ssot_sha):
        die("원장 cycles[%s].%s.audit_sha(%r) != 승격 인자" % (cycle, auditor, blk.get("audit_sha")))
    if blk.get("verdict") != reports[auditor].get("verdict"):
        die("원장 cycles[%s].%s.verdict(%r) != 보고서 verdict(%r)"
            % (cycle, auditor, blk.get("verdict"), reports[auditor].get("verdict")))
    reg = blk.get("findings")
    if not isinstance(reg, list):
        die("원장 cycles[%s].%s.findings 가 없다" % (cycle, auditor))
    reg_blocking = len([f for f in reg if f.get("blocking") is True])
    if reg_blocking != report_blocking[auditor]:
        die("원장이 등재한 %s blocking finding 수(%d) != 보고서에서 센 수(%d) — 원장이 감사 보고서를 "
            "그대로 반영하지 않았다" % (auditor, reg_blocking, report_blocking[auditor]))

# ---8<--- DR_D_SKIP_END
# --- (B) 원장 항목에서 total 을 다시 센다 ---
excluded = []


def residual_in_force(f, label):
    """(D) ACCEPTED_BOUNDED_RESIDUAL_RISK 항목을 검증한다.

    근거가 없으면 die — 근거 없는 제외는 counted_as_open=false 와 똑같이 차단이다.
    근거는 있으나 C-6 실효가 성립하면 False 를 돌려 **다시 open blocking 으로 세게** 한다.
    """
    fid = str(f.get("id"))
    where = "%s 의 %r" % (label, fid)
    residual_seen.append("%s:%s" % (label, fid))

    if not isinstance(VOCAB, dict):
        die("%s 이 %s 인데 원장에 상태값 정의(v2_transition.finding_state_vocabulary.%s)가 없다 — "
            "정의 없는 상태값으로 합계에서 빼지 않는다 (fail-closed)" % (where, ABRR, ABRR))
    for key in ("definition", "counting_rule", "grant_conditions", "lapse_rule"):
        if not VOCAB.get(key):
            die("finding_state_vocabulary.%s 에 %r 이 없다 — 상태값 정의가 불완전하다 (fail-closed)"
                % (ABRR, key))

    if (f.get("blocking") is not False or f.get("counted_as_open") is not False
            or f.get("excluded_from_total") is not True):
        die("%s 이 %s 인데 blocking=false / counted_as_open=false / excluded_from_total=true 가 아니다 — "
            "제외의 형식 요건 미달 (fail-closed)" % (where, ABRR))

    for key in ("accepted_by_audit_sha", "accepted_by_audit_branch", "accepted_by_audit_report",
                "accepted_at", "basis", "scope", "conditions", "conditions_status",
                "lapse_rule", "precedent_limits_satisfied"):
        if not f.get(key):
            die("%s 이 %s 인데 %r 근거가 없다 — 근거 없는 제외는 total 조작 경로다 (fail-closed)"
                % (where, ABRR, key))

    a_sha = str(f.get("accepted_by_audit_sha"))
    if not HEX40.match(a_sha):
        die("%s 의 accepted_by_audit_sha(%r) 가 40-hex 전체 SHA 가 아니다" % (where, a_sha))
    a_br = str(f.get("accepted_by_audit_branch"))
    if not a_br.startswith("audit/landing-"):
        die("%s 의 accepted_by_audit_branch(%r) 가 audit/landing-* 네임스페이스가 아니다 — "
            "임의 브랜치의 판정으로 제외할 수 없다" % (where, a_br))

    rep_path = str(f.get("accepted_by_audit_report"))
    rr = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (a_sha, rep_path)], capture_output=True)
    if rr.returncode != 0:
        die("%s 의 수용 판정 보고서를 읽을 수 없다: %s:%s — 감사 보고서로 확인되지 않는 수용은 "
            "제외 근거가 아니다 (%s)" % (where, a_sha, rep_path,
                                        rr.stderr.decode("utf-8", "replace").strip()))
    try:
        adj = json.loads(rr.stdout.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        die("%s 의 수용 판정 보고서 JSON 파싱 실패: %s:%s (%s)" % (where, a_sha, rep_path, e))
    if not isinstance(adj, dict):
        die("%s 의 수용 판정 보고서가 객체가 아니다: %s:%s" % (where, a_sha, rep_path))
    if adj.get("id") != fid:
        die("%s 의 수용 판정 보고서가 다른 id 를 판정했다 — 보고서 id=%r" % (where, adj.get("id")))
    if adj.get("verdict") != "ACCEPT_RECLASSIFY":
        die("%s 의 수용 판정 보고서 verdict=%r — ACCEPT_RECLASSIFY 가 아니다" % (where, adj.get("verdict")))
    if adj.get("new_class") != ABRR:
        die("%s 의 수용 판정 보고서 new_class=%r != %s" % (where, adj.get("new_class"), ABRR))

    plim = f.get("precedent_limits_satisfied")
    if not isinstance(plim, dict):
        die("%s 의 precedent_limits_satisfied 가 객체가 아니다" % where)
    for key in ("i_reproduced_irreducibility", "ii_single_named_dimension",
                "iii_self_registered_before_audit"):
        if not str(plim.get(key, "")).strip().upper().startswith("YES"):
            die("%s 의 선례 제한 %r 이 YES 로 기록돼 있지 않다 — 직접 공격 재현 · 단일 차원 축소 · "
                "지적 전 자진 등재 셋을 **전부** 만족하는 항목만 이 경로를 쓸 수 있다 (C-6-2)"
                % (where, key))

    # --- 조건 식별의 무결성 (H-1) + owner 자기신고 제거 (H-2) + 근거 실검증 (H-3)
    #     + gate 어휘 (H-4) + 게이트별 조건 집합 (H-5) → C-6 자동 실효 ---
    canon = _ABRR_CANON.get(fid)
    if not isinstance(canon, dict):
        die("%s 이 %s 인데 [DEBT_RECOMPUTE] 에 이 id 의 조건 정본(_ABRR_CANON)이 없다 — 정본이 없으면 "
            "조건 집합·owner·기한이 전부 원장 자기신고가 된다. 새 수용을 부여하려면 감사 판정과 함께 "
            "이 파일에 정본을 추가해야 한다 (fail-closed)" % (where, ABRR))
    canon_conds = canon["conditions"]

    decl = f.get("conditions")
    if not isinstance(decl, list) or not decl:
        die("%s 의 conditions 열거가 비어 있다 — 조건 없이 제외할 수 없다" % where)
    decl_ids = [norm_token(x) for x in decl]
    if any(not x or x == "NONE" for x in decl_ids):
        die("%s 의 conditions 열거에 빈 id 가 있다 (%r)" % (where, decl))
    if len(set(decl_ids)) != len(decl_ids):
        die("%s 의 conditions 열거가 정규화(strip·공백축약·대문자) 후 충돌한다 (%r → %r) — "
            "정규화로 서로 다른 조건이 같아지는 입력은 받지 않는다 (H-1, fail-closed)"
            % (where, decl, decl_ids))

    cs = f.get("conditions_status")
    if not isinstance(cs, list) or not cs:
        die("%s 의 conditions_status 가 비어 있다 — 조건 이행 상태 없이 제외할 수 없다" % where)
    for c in cs:
        if not isinstance(c, dict):
            die("%s 의 conditions_status 원소가 객체가 아니다" % where)
    cs_ids = [norm_token(c.get("id")) for c in cs]
    if any(not x or x == "NONE" for x in cs_ids):
        die("%s 의 conditions_status 에 id 없는 항목이 있다" % where)
    if len(set(cs_ids)) != len(cs_ids):
        die("%s 의 conditions_status id 가 정규화 후 충돌한다 (%r) — 정규화로 서로 다른 조건이 "
            "같아지는 입력은 받지 않는다 (H-1, fail-closed)" % (where, cs_ids))

    canon_set, decl_set, cs_set = set(canon_conds), set(decl_ids), set(cs_ids)
    if decl_set != cs_set:
        die("%s 의 conditions 열거와 conditions_status 의 id 집합이 다르다 (H-1) — "
            "conditions 에만: %s · conditions_status 에만: %s\n"
            "  한쪽에만 있는 id 는 차단이다. 항목을 지워 실효를 잠재우는 경로를 막는다 (fail-closed)"
            % (where, sorted(decl_set - cs_set) or "없음", sorted(cs_set - decl_set) or "없음"))
    if cs_set != canon_set:
        die("%s 의 조건 id 집합이 [DEBT_RECOMPUTE] 정본과 다르다 (H-1) — "
            "정본에만: %s · 원장에만: %s\n"
            "  조건 집합은 원장이 아니라 이 파일이 정본이다. 개편하려면 감사 판정과 함께 정본을 "
            "고쳐야 한다 (fail-closed)"
            % (where, sorted(canon_set - cs_set) or "없음", sorted(cs_set - canon_set) or "없음"))

    status = {}
    evidence_note = []
    for c in cs:
        cid = norm_token(c.get("id"))
        canon_owner, canon_due = canon_conds[cid]

        # owner — **정본 대조만** 한다. 검증 강도를 정하지 않는다 (H-2).
        got_owner = re.sub(r"\s+", " ", str(c.get("owner") or "")).strip()
        if got_owner.casefold() != str(canon_owner).casefold():
            die("%s 의 조건 %s owner(%r) 가 정본(%r)과 다르다 — owner 는 공격자가 편집하는 같은 객체의 "
                "필드이므로 정본과 대조한다. 이 값은 더 이상 검증 강도를 정하지 않는다 (H-2, fail-closed)"
                % (where, cid, got_owner, canon_owner))

        # due_before — 형식 검증 후 정본과 정확 대조 (H-1)
        raw_due = c.get("due_before")
        if raw_due is None:
            got_due = None
        elif isinstance(raw_due, str):
            got_due = norm_token(raw_due)
            if not re.match(r"^[A-Z0-9_]+$", got_due):
                die("%s 의 조건 %s due_before(%r) 가 기한 토큰 형식([A-Z0-9_]+)이 아니다 (H-1)"
                    % (where, cid, raw_due))
        else:
            die("%s 의 조건 %s due_before(%r) 가 문자열도 null 도 아니다 (H-1)" % (where, cid, raw_due))
        if got_due != canon_due:
            die("%s 의 조건 %s due_before 가 정본과 다르다 — 원장 %r (정규화 %r) != 정본 %r\n"
                "  소문자·앞뒤 공백·null·임의값으로 실효 스캔을 비껴가는 경로를 전부 막는다 "
                "(H-1, fail-closed)" % (where, cid, raw_due, got_due, canon_due))

        st = norm_token(c.get("state"))
        if not st or st == "NONE":
            die("%s 의 조건 %s 에 state 가 없다 — 상태 없는 조건은 충족으로 보지 않는다 (fail-closed)"
                % (where, cid))
        status[cid] = st

        # SATISFIED 는 owner 와 무관하게 **전부 동일 강도**로 감사 근거를 요구한다 (H-2·H-3)
        if st == "SATISFIED":
            evidence_note.append("%s:%s" % (cid, verify_condition_audit_sha(where, cid, c.get("audit_sha"))))

    # --- 실효 트리거 — 게이트별 필수 조건 집합(정본) ∪ due_before 사상 (H-5) ---
    trigger = {}
    for gate_name, req in canon["gate_required"].items():
        trigger.setdefault(gate_name, set()).update(req)
        missing = [x for x in req if x not in status]
        if missing:
            die("%s 의 실효 트리거 게이트 %s 가 요구하는 조건 %s 이 conditions_status 에 없다 — "
                "어휘 lapse_rule 이 이름으로 지정한 조건은 **존재하고** 판정돼 있어야 한다 "
                "(H-1·H-5, fail-closed)" % (where, gate_name, missing))
    for cid in status:
        g = _DUE_BEFORE_GATE.get(canon_conds[cid][1])
        if g in trigger:
            trigger[g].add(cid)

    unmet, pending = [], []
    for gate_name in sorted(trigger):
        achieved = gate_declared_achieved(gate_name)   # 어휘 밖·키 부재는 여기서 차단된다 (H-4)
        for cid in sorted(trigger[gate_name]):
            if status.get(cid) == "SATISFIED":
                continue
            if achieved:
                unmet.append("%s ← %s=%s" % (gate_name, cid, status.get(cid) or "?"))
            else:
                pending.append("%s ← %s=%s" % (gate_name, cid, status.get(cid) or "?"))

    if unmet:
        lapsed_residual.append("%s [%s]" % (fid, "; ".join(unmet)))
        return False
    if pending:
        pending_residual.append("%s (미충족: %s — 해당 게이트를 ACHIEVED 로 선언하는 순간 자동 실효)"
                                % (fid, "; ".join(pending)))
    if evidence_note:
        verified_residual.append("%s — %s" % (fid, " · ".join(evidence_note)))

    accepted_residual.append("%s:%s" % (label, fid))
    return True


def tally(items, label):
    n = 0
    for f in items:
        st = str(f.get("state", f.get("status")) or "OPEN").strip().upper()
        if st == ABRR:
            if residual_in_force(f, label):
                continue
            # C-6 자동 실효 — OPEN / blocking=true / counted_as_open=true 로 복귀시켜 센다.
            n += 1
            continue
        if f.get("blocking") is not True:
            continue
        if closed(f.get("state", f.get("status"))):
            continue
        if f.get("counted_as_open") is False:
            if not (f.get("duplicate_of") or f.get("superseded_by")):
                die("%s 의 %r 이 counted_as_open=false 인데 duplicate_of/superseded_by 근거가 없다 — "
                    "근거 없는 제외는 total 조작 경로다 (fail-closed)" % (label, f.get("id")))
            excluded.append("%s:%s" % (label, f.get("id")))
            continue
        n += 1
    return n
# ---8<--- DR_D_END


ledger = 0
di = v2.get("debt_inheritance")
if not isinstance(di, dict) or not isinstance(di.get("items"), list):
    die("v2_transition.debt_inheritance.items 가 없다 — v1 승계 원장 없이 blocking 0 을 선언할 수 없다 "
        "(PHASE_GATES 「공통 통과조건」절 = §2 부채 승계 조건)")
items = di["items"]

# --- (C) v1 승계분의 **독립 원천** ---
# V2-C006 시정 — adversarial V2-C005 `debt-recompute-has-no-second-source-for-v1-inherited-items`
#   이전 판은 v1 승계 blocking 을 debt_inheritance.items **한 소스에서만** 셌다. 감사 실측:
#   v1 항목 하나를 지우고 total 을 1 낮추면 그 state 는 자기일관적이라 탐지되지 않는다.
#   v2 신규분은 pinned 감사 보고서라는 외부 원천이 있는데 v1 승계분만 없었다.
#   이제 두 개의 v1 원천을 더 쓴다.
#     C1  state.debt_ledger — v1 시절 원장. 승계 목록으로 옮겨쓴 적이 없고 삭제되지도 않았다.
#         모집단 크기 · class 인구 · E001_BLOCKING 수를 여기서 다시 세어 items 와 대조한다.
#     C2  그 원장이 **처음 커밋된 시점의 git 객체** (debt_inheritance.v1_ledger_git_anchor).
#         같은 파일 안의 두 키를 함께 고치는 공격까지 막는다 — anchor 는 이미 게시된
#         reconciliation 커밋의 조상이어야 하므로 과거를 고치려면 control 계보를 다시 써야 한다.
#   두 원천이 items 와 한 자리라도 어긋나면 차단이다 (fail-closed).
v1l = s.get("debt_ledger")
if not isinstance(v1l, dict):
    die("state.debt_ledger (v1 원장) 가 없다 — v1 승계분의 두 번째 원천이 사라졌다. "
        "한 소스만으로 v1 blocking 을 세지 않는다 (fail-closed)")
tri = (v1l.get("triage") or {}).get("counts")
if not isinstance(tri, dict) or not tri:
    die("debt_ledger.triage.counts 가 없다 — v1 승계분을 독립 재계산할 수 없다 (fail-closed)")
try:
    tri = {str(k): int(v) for k, v in tri.items()}
except Exception as e:  # noqa: BLE001
    die("debt_ledger.triage.counts 값이 정수가 아니다 (%s)" % e)
for k in ("total", "closed_verified", "open"):
    if not isinstance(v1l.get(k), int) or isinstance(v1l.get(k), bool):
        die("debt_ledger.%s 가 정수가 아니다 (%r)" % (k, v1l.get(k)))

# C1-a  v1 원장 자체의 산술이 성립하는가
if v1l["closed_verified"] + v1l["open"] != v1l["total"]:
    die("v1 원장 산술 불일치: closed_verified(%d) + open(%d) != total(%d)"
        % (v1l["closed_verified"], v1l["open"], v1l["total"]))
if sum(tri.values()) != v1l["total"]:
    die("debt_ledger.triage.counts 합(%d) != debt_ledger.total(%d) — v1 원장이 스스로와 어긋난다"
        % (sum(tri.values()), v1l["total"]))
if tri.get("CLOSED") != v1l["closed_verified"]:
    die("debt_ledger.triage.counts.CLOSED(%r) != debt_ledger.closed_verified(%d)"
        % (tri.get("CLOSED"), v1l["closed_verified"]))

# C1-b  승계 모집단의 **크기** — 항목을 조용히 지우는 경로를 여기서 죽인다
if len(items) != v1l["open"]:
    die("v1 승계 항목수(%d) != v1 원장 debt_ledger.open(%d) — 승계 목록에서 항목이 사라졌거나 늘었다.\n"
        "  v1 승계분은 이제 두 원천에서 센다. 한 소스만 고쳐 total 을 낮추는 경로는 여기서 막힌다 "
        "(adversarial V2-C005 debt-recompute-has-no-second-source-for-v1-inherited-items)."
        % (len(items), v1l["open"]))

# C1-c  class 인구조사 — 항목을 지우는 대신 class 를 갈아끼우는 경로도 막는다
census = {}
for i in items:
    census[str(i.get("v1_debt_class"))] = census.get(str(i.get("v1_debt_class")), 0) + 1
expect_census = {k: v for k, v in tri.items() if k != "CLOSED"}
if census != expect_census:
    die("v1 승계 항목의 class 인구 %r != v1 원장 triage.counts 미종결분 %r" % (census, expect_census))

# C1-d  debt_inheritance 가 스스로 선언한 v1 수치도 v1 원장과 대조한다
for fld, val in (("v1_total", v1l["total"]), ("v1_closed_verified", v1l["closed_verified"]),
                 ("v1_open", v1l["open"]), ("inherited_open", v1l["open"]),
                 ("v1_open_e001_blocking", tri.get("E001_BLOCKING"))):
    if di.get(fld) != val:
        die("debt_inheritance.%s(%r) != v1 원장 값(%r)" % (fld, di.get(fld), val))

# C2  v1 원장의 git 앵커 — 같은 파일의 두 키를 함께 고치는 공격을 막는다
anchor = di.get("v1_ledger_git_anchor")
if not isinstance(anchor, str) or not HEX40.match(anchor):
    die("debt_inheritance.v1_ledger_git_anchor 가 40-hex 전체 SHA 가 아니다 (%r) — "
        "v1 원장의 git 앵커 없이는 승계분을 두 번째로 셀 수 없다 (fail-closed)")
r = subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", anchor, rec_sha],
                   capture_output=True)
if r.returncode != 0:
    die("v1_ledger_git_anchor(%s) 가 reconciliation 커밋(%s)의 조상이 아니다 — "
        "게시된 control 계보 밖의 커밋은 앵커가 될 수 없다" % (anchor, rec_sha))
r = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (anchor, state_rel)], capture_output=True)
if r.returncode != 0:
    die("v1 원장 앵커 커밋에서 state.json 을 읽을 수 없다: %s:%s (%s)"
        % (anchor, state_rel, r.stderr.decode("utf-8", "replace").strip()))
try:
    anchored = json.loads(r.stdout.decode("utf-8")).get("debt_ledger")
except Exception as e:  # noqa: BLE001
    die("v1 원장 앵커 커밋의 state.json 파싱 실패: %s (%s)" % (anchor, e))
if not isinstance(anchored, dict):
    die("v1 원장 앵커 커밋(%s)에 debt_ledger 가 없다 — 앵커가 v1 원장 수립 커밋이 아니다" % anchor)
a_tri = (anchored.get("triage") or {}).get("counts")
if not isinstance(a_tri, dict):
    die("v1 원장 앵커 커밋(%s)의 debt_ledger.triage.counts 가 없다" % anchor)
a_tri = {str(k): int(v) for k, v in a_tri.items()}
if a_tri != tri:
    die("v1 원장이 앵커 이후 조용히 바뀌었다: 현재 triage.counts %r != 앵커(%s) %r\n"
        "  v1 승계분은 닫힌 원장이다. 바꾸려면 근거와 함께 v1 원장 자체를 개정해야 한다."
        % (tri, anchor, a_tri))
for k in ("total", "closed_verified", "open"):
    if anchored.get(k) != v1l[k]:
        die("v1 원장이 앵커 이후 바뀌었다: debt_ledger.%s 현재 %r != 앵커 %r"
            % (k, v1l[k], anchored.get(k)))

# --- 두 경로로 v1 open blocking 을 센다 ---
v1_universe = tri.get("E001_BLOCKING")
if not isinstance(v1_universe, int):
    die("debt_ledger.triage.counts.E001_BLOCKING 이 없다 — v1 blocking 모집단을 알 수 없다")
blocking_items = [i for i in items if i.get("blocks_ready_for_e001_v2") is True]
bids = di.get("blocking_ids")
if not isinstance(bids, list):
    die("debt_inheritance.blocking_ids 가 없다")
if sorted(bids) != sorted([str(i.get("id")) for i in blocking_items]) or len(bids) != len(blocking_items):
    die("debt_inheritance.blocking_ids(%d건) 와 blocks_ready_for_e001_v2=true 항목(%d건)이 다르다\n"
        "  ids=%r\n  items=%r"
        % (len(bids), len(blocking_items), sorted(bids), sorted([str(i.get("id")) for i in blocking_items])))
if len(blocking_items) != v1_universe:
    die("v1 승계 blocking 모집단 불일치: items 에서 센 %d != v1 원장 triage.counts.E001_BLOCKING %d\n"
        "  두 원천이 어긋나면 차단이다 (adversarial V2-C005 "
        "debt-recompute-has-no-second-source-for-v1-inherited-items)."
        % (len(blocking_items), v1_universe))

v1_closed_ids = []
for i in blocking_items:
    if not closed(i.get("state")):
        continue
    if not (i.get("closure_evidence") or i.get("closed_evidence") or i.get("closed_in_cycle")
            or i.get("closed_by_audit")):
        die("v1 승계 blocking %r 이 CLOSED 인데 closure_evidence / closed_evidence / closed_in_cycle / "
            "closed_by_audit 근거가 없다 — 근거 없는 종결은 total 조작 경로다 (fail-closed)"
            % i.get("id"))
    v1_closed_ids.append(str(i.get("id")))

v1_by_items = len(blocking_items) - len(v1_closed_ids)     # 경로 A: 승계 목록
v1_by_ledger = v1_universe - len(v1_closed_ids)            # 경로 B: v1 원장(+앵커)
if v1_by_items != v1_by_ledger:
    die("v1 승계 open blocking 두 경로 불일치: items %d != v1 원장 %d" % (v1_by_items, v1_by_ledger))
v1_blocking = v1_by_items
ledger += v1_blocking

per_cycle = {}
for c in vaf["cycles"]:
    n = 0
    for auditor in ("adversarial", "ssot"):
        blk = c.get(auditor) or {}
        n += tally(blk.get("findings") or [], "%s/%s" % (c.get("cycle"), auditor))
    per_cycle[c.get("cycle")] = n
    ledger += n

orch = vaf.get("orchestrator_registered") or {}
orch_blocking = tally(orch.get("findings") or [], "orchestrator_registered")
ledger += orch_blocking

obt = v2.get("open_blocking_total")
if not isinstance(obt, dict) or not isinstance(obt.get("total"), int):
    die("v2_transition.open_blocking_total.total 이 없거나 정수가 아니다")
declared_total = obt["total"]

# ---8<--- DR_D2_BEGIN
# --- (D) 명시적 제외의 가시성 강제 — 조용히 사라지는 것을 금지한다 ---
declared_acc = obt.get("accepted_bounded_residual_risk")
declared_acc_ids = obt.get("accepted_residual_ids")
if residual_seen or declared_acc or declared_acc_ids:
    if not isinstance(declared_acc, int) or isinstance(declared_acc, bool):
        die("원장에 %s 항목이 %d건 있는데 open_blocking_total.accepted_bounded_residual_risk 카운터가 "
            "정수로 선언돼 있지 않다 (%r) — 제외는 합계와 나란히 **명시적으로 표시**돼야 한다 "
            "(adversarial fed3e70 §7 C-1)" % (ABRR, len(residual_seen), declared_acc))
    if declared_acc != len(residual_seen):
        die("선언된 accepted_bounded_residual_risk(%d) != 원장 항목에서 센 %s 항목수(%d)\n  항목: %s"
            % (declared_acc, ABRR, len(residual_seen), ", ".join(residual_seen) or "없음"))
    if not isinstance(declared_acc_ids, list) or len(declared_acc_ids) != len(residual_seen):
        die("open_blocking_total.accepted_residual_ids 가 %d건으로 열거돼 있지 않다 (%r) — "
            "카운터만 있고 id 열거가 없으면 '명시적으로 제외된 한 줄' 요건 미달이다"
            % (len(residual_seen), declared_acc_ids))
    for ent in residual_seen:
        fid = ent.split(":", 1)[1]
        if not any(fid in str(x) for x in declared_acc_ids):
            die("accepted_residual_ids 열거에 %r 이 없다 — 합계에서 빠진 항목은 반드시 열거돼야 한다" % fid)
    if not obt.get("exclusion_line"):
        die("open_blocking_total.exclusion_line 이 없다 — 제외가 무엇을 뜻하는지(CLOSED 가 아님) 적은 "
            "한 줄이 있어야 한다 (C-1)")
if lapsed_residual:
    die("%s 수용이 **자동 실효**됐다 (C-6): 실효 트리거 게이트가 ACHIEVED 어휘로 선언됐는데 "
        "그 게이트 이전 조건이 미충족이다.\n  %s\n"
        "  실효된 항목은 OPEN / blocking=true / counted_as_open=true 로 복귀해 다시 계상된다."
        % (ABRR, "\n  ".join(lapsed_residual)))
# ---8<--- DR_D2_END

breakdown = ("v1=%d, %s, orchestrator=%d, 제외(%s)=%d%s"
             % (v1_blocking, ", ".join("%s=%d" % (k, v) for k, v in per_cycle.items()), orch_blocking,
                ABRR, len(accepted_residual),
                (" [" + ", ".join(accepted_residual) + "]") if accepted_residual else ""))
if ledger != declared_total:
    die("원장 항목 재계산(%d) != 선언된 open_blocking_total.total(%d)\n  재계산 내역: %s\n"
        "  중복계상 제외: %s\n  스칼라 하나를 고쳐 게이트를 통과시키는 경로를 막는다 (ADV-C004-04)."
        % (ledger, declared_total, breakdown, ", ".join(excluded) or "없음"))

if ledger != 0:
    die("독립 재계산 open blocking = %d (선언값과 일치하지만 0 이 아니다)\n  내역: %s\n"
        "  00_SSOT_v2.0 §15 open blocking = 0 위반" % (ledger, breakdown))
if report_blocking["adversarial"] or report_blocking["ssot"]:
    die("pinned 감사 보고서의 open blocking = adversarial %d / ssot %d — 0 이 아니다"
        % (report_blocking["adversarial"], report_blocking["ssot"]))

print("DEBT_RECOMPUTE OK — 보고서 blocking adv=%d ssot=%d · 원장 재계산 %d == 선언 %d (%s)"
      % (report_blocking["adversarial"], report_blocking["ssot"], ledger, declared_total, breakdown))
print("DEBT_RECOMPUTE 명시적 제외 — %s %d건%s"
      % (ABRR, len(accepted_residual),
         (": " + ", ".join(accepted_residual)) if accepted_residual else " (없음)"))
for _p in pending_residual:
    print("DEBT_RECOMPUTE 경고 — 수용 조건 미충족 잔여: %s" % _p)
for _v in verified_residual:
    print("DEBT_RECOMPUTE 조건 근거 실검증 (40-hex · commit resolve · 감사 브랜치 조상 · 보고서 판정) — %s" % _v)
PY
note "[DEBT_RECOMPUTE] 보고서·원장 항목에서 독립 재계산 == 선언값 == 0 OK (ACCEPTED_BOUNDED_RESIDUAL_RISK 제외 건수는 위 출력에 별도 표시)"

# ================================================================ [AUDIT_VERDICT]
# V2-C003 시정 — adversarial V2-C002 `promotion-verdict-check-treats-missing-verdict-as-pass`
#   이전 버전은 `assert v is None or v == "PASS"` 였다. verdict 미기록(키 부재·null)이
#   명시적으로 통과했다 — fail-open 이 코드에 적혀 있었다. 이제 두 감사의 verdict 가
#   **명시적으로 PASS** 여야만 통과하며, state.json 자기기록만 믿지 않고 원격 감사 브랜치의
#   보고서 JSON 을 직접 읽어 재확인한다. 파일 부재·파싱 실패·필드 부재·target_sha 불일치는
#   전부 차단이다 (fail-closed).
# V2-C004 시정 — adversarial V2-C003 `promotion-audit-sha-argument-not-pinned-to-recorded-audit-sha`
#   argv 로 받은 감사 SHA 가 state.audit_lag 의 기록과 대조되지 않아, cycle/target_sha/auditor
#   3필드만 맞으면 **다른 커밋의 보고서**(예: 아직 PASS 였던 초안 커밋)를 넘길 여지가 있었다.
#   이제 argv 감사 SHA 는 latest_adversarial_audit_sha / latest_ssot_audit_sha 와 정확히
#   일치해야 한다. state 기록은 40-hex 여야 하며, 축약형은 state 결함으로 차단한다.
#   (원격 tip 과의 일치까지 요구하지는 않는다 — 감사자가 다음 사이클 보고서를 push 하면
#    tip 이 앞서가는 것이 정상이고, 핀은 state 기록 쪽이 정본이기 때문이다.)
python3 - "$STATE" "$EXEC_SHA" "$REPO" "$ADV_SHA" "$SSOT_SHA" <<'PY' || fail "audit lag / target sha / verdict / 감사 SHA 핀 불일치"
import json
import re
import subprocess
import sys

state_path, exec_sha, repo, adv_sha, ssot_sha = sys.argv[1:6]


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


try:
    s = json.load(open(state_path, encoding="utf-8"))
except Exception as e:  # noqa: BLE001
    die("state.json 파싱 실패: %s" % e)

al = s.get("audit_lag")
if not isinstance(al, dict):
    die("state.json 에 audit_lag 가 없다")

for k in ("latest_adversarial_target_sha", "latest_ssot_target_sha"):
    if al.get(k) != exec_sha:
        die("%s(%r) != exec(%s)" % (k, al.get(k), exec_sha))
if al.get("both_audits_same_target_sha") is not True:
    die("audit_lag.both_audits_same_target_sha 가 true 가 아니다 (%r) — "
        "05 §6 '두 독립감사가 exact same target SHA' 위반" % (al.get("both_audits_same_target_sha"),))
try:
    depth = int(al["unaudited_cycle_depth"])
except Exception:  # noqa: BLE001
    die("audit_lag.unaudited_cycle_depth 가 없거나 정수가 아니다")
if depth > int(al.get("MAX_UNAUDITED_EXEC_CYCLES", 1)):
    die("audit lag > bound (unaudited_cycle_depth=%d)" % depth)

# 5-a. state 자기기록 verdict — 미기록·null·FAIL 전부 차단
for k in ("latest_adversarial_verdict", "latest_ssot_verdict"):
    v = al.get(k)
    if v != "PASS":
        die("state.audit_lag.%s = %r — PASS 가 아니다. "
            "verdict 미기록(키 부재/null)도 통과시키지 않는다 (fail-closed)." % (k, v))

# 5-b. 감사 SHA 핀 — argv 로 받은 SHA 가 원장이 기록한 감사 커밋과 정확히 일치해야 한다.
#      불일치 시 '다른 사이클/다른 커밋의 PASS 보고서' 를 인자로 넘기는 경로가 열린다.
HEX40 = re.compile(r"^[0-9a-f]{40}$")
PINS = (
    ("adversarial", adv_sha, "latest_adversarial_audit_sha"),
    ("ssot", ssot_sha, "latest_ssot_audit_sha"),
)
for auditor, argv_sha, key in PINS:
    rec = al.get(key)
    if not isinstance(rec, str) or not rec:
        die("audit_lag.%s 가 없다 — 승격 인자로 받은 감사 SHA 를 대조할 기준이 없다 (fail-closed)" % key)
    if not HEX40.match(rec):
        die("audit_lag.%s = %r 가 40-hex 전체 SHA 가 아니다 — 축약형은 핀이 될 수 없다. "
            "state.json 을 전체 SHA 로 고쳐라." % (key, rec))
    if rec != argv_sha:
        die("%s 감사 SHA 핀 불일치: 인자 %s != audit_lag.%s %s"
            % (auditor, argv_sha, key, rec)
            + " — 원장이 기록한 감사 커밋이 아닌 SHA 로는 승격할 수 없다"
              " (다른 사이클/다른 커밋의 PASS 보고서 우회 차단).")

# 5-c. 감사 보고서 JSON 원본 재확인 — state.json 하나를 잘못 쓰면 원장·verdict 검사가 함께
#      무력화되므로, 핀이 확인된 감사 SHA 에서 보고서를 직접 읽어 대조한다.
AUDITORS = (
    ("adversarial", adv_sha, "latest_adversarial_audited_cycle"),
    ("ssot", ssot_sha, "latest_ssot_audited_cycle"),
)
for auditor, audit_sha, cyc_key in AUDITORS:
    cyc = al.get(cyc_key)
    if not cyc:
        die("audit_lag.%s 가 없다 — 어느 보고서를 읽어야 할지 알 수 없다" % cyc_key)
    path = "research/landing_accessibility/audit/%s/%s.json" % (auditor, str(cyc).replace("-", "_"))
    r = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (audit_sha, path)], capture_output=True)
    if r.returncode != 0:
        die("%s 감사 보고서를 읽을 수 없다: %s:%s (%s) — 보고서 부재는 차단이다"
            % (auditor, audit_sha, path, r.stderr.decode("utf-8", "replace").strip()))
    try:
        rep = json.loads(r.stdout.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        die("%s 감사 보고서 JSON 파싱 실패: %s:%s (%s) — 파싱 실패는 차단이다"
            % (auditor, audit_sha, path, e))
    if not isinstance(rep, dict) or "verdict" not in rep:
        die("%s 감사 보고서에 verdict 필드가 없다: %s:%s — 필드 부재는 차단이다"
            % (auditor, audit_sha, path))
    if rep["verdict"] != "PASS":
        die("%s 감사 보고서 verdict = %r (PASS 아님): %s:%s"
            % (auditor, rep["verdict"], audit_sha, path))
    if rep.get("target_sha") != exec_sha:
        die("%s 감사 보고서 target_sha(%r) != 승격 대상(%s) — 감사한 트리와 승격 트리가 다르다"
            % (auditor, rep.get("target_sha"), exec_sha))
    if rep.get("cycle") != cyc:
        die("%s 감사 보고서 cycle(%r) != audit_lag.%s(%r)" % (auditor, rep.get("cycle"), cyc_key, cyc))
    if rep.get("auditor") != auditor:
        die("%s 감사 보고서 auditor 필드(%r) 불일치" % (auditor, rep.get("auditor")))
PY
note "[AUDIT_VERDICT] audit lag / target sha / verdict(state + 보고서 JSON) / 감사 SHA 핀 OK"

MAIN_BEFORE="$(git -C "$REPO" rev-parse "origin/$MAIN")"
echo "PROMOTION PRECHECK PASS"
echo "  exec=$EXEC_SHA  adv=$ADV_SHA(origin/$ADV_BRANCH)  ssot=$SSOT_SHA(origin/$SSOT_BRANCH)"
echo "  rec=$REC_SHA  orch=$ORCH_SHA  remote-control-tip=$REMOTE_ORCH_TIP"
echo "  exec worktree=$EXEC_WT"
echo "  main: $MAIN_BEFORE -> $EXEC_SHA"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN — push 하지 않는다."
  exit 0
fi

LA_PROMOTION=ORCHESTRATOR_PROMOTION_ONLY git -C "$REPO" push origin "$EXEC_SHA:refs/heads/$MAIN"
echo "PROMOTED"
