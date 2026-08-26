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
# 검사 이름과 실행 순서 (번호는 이 목록의 순서일 뿐이며, 인용은 **이름**으로 한다):
#   1 [HOOK_INSTALL]      pre-push 훅 설치 상태 — 정본 존재 · 심링크 유효 · 실행권한 · 내용 동일
#   2 [SHA_RESOLVE]       exec/감사 SHA 실재 + 정규화, exec·control 워크트리 해석
#   3 [PILOT_IMMUTABLE]   Pilot(research/refcohort) diff = 0
#   4 [AUDIT_ANCESTRY]    두 감사 SHA 가 원격 감사 브랜치의 조상
#   5 [EXEC_TREE]         exec 워크트리 clean + HEAD == 승격 대상 SHA
#   6 [ORCH_TREE]         control 워크트리 clean + state.json 워킹트리 == 커밋본
#   7 [INSTALL_INTEGRITY] verify_v2_docs.py 실호출 (exec 워크트리 기준, exit != 0 · 부재 모두 차단)
#   8 [BLOCKING_DEBT]     커밋된 state.json 의 open P0/P1 · v2_transition.open_blocking_total
#   9 [AUDIT_VERDICT]     audit lag · target sha · verdict(state + 보고서 JSON) · 감사 SHA 핀
#   무결성 검증은 exec **트리** 검사이므로 clean/HEAD 와 같은 층에 둔다.
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

[ $# -ge 4 ] || fail "usage: promote_landing_main.sh <exec_sha> <adversarial_sha> <ssot_sha> <reconciliation_sha> [--dry-run] [--exec-branch=REF] [--exec-worktree=PATH] [--orch-sha=SHA]"
EXEC_SHA_IN="$1"; ADV_SHA_IN="$2"; SSOT_SHA_IN="$3"; REC_SHA="$4"; shift 4

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

# ================================================================ [PILOT_IMMUTABLE]
[ -z "$(git -C "$REPO" diff --stat "$PILOT_SHA" "$EXEC_SHA" -- research/refcohort)" ] \
  || fail "Pilot path diff != 0 (research/refcohort 는 READ_ONLY, 수정 시 P0)"
note "[PILOT_IMMUTABLE] OK"

# ================================================================ [AUDIT_ANCESTRY]
for A in "$ADV_SHA:audit/landing-adversarial" "$SSOT_SHA:audit/landing-ssot"; do
  sha="${A%%:*}"; br="${A##*:}"
  git -C "$REPO" merge-base --is-ancestor "$sha" "origin/$br" 2>/dev/null || fail "$br 에 $sha 없음"
done
note "[AUDIT_ANCESTRY] 두 감사 SHA 가 원격 감사 브랜치의 조상 OK"

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
TMPDIR_PROMOTE="$(mktemp -d)"
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
# 입력은 커밋된 state.json ($STATE) 하나다 — [ORCH_TREE] 가 워킹트리 사본과의 동일성을 이미 단언했다.
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
note "[BLOCKING_DEBT] open P0/P1 = 0 · v2_transition.open_blocking_total = 0 OK (원장 = $ORCH_SHA 커밋본)"

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
echo "  exec=$EXEC_SHA  adv=$ADV_SHA  ssot=$SSOT_SHA  rec=$REC_SHA  orch=$ORCH_SHA"
echo "  exec worktree=$EXEC_WT"
echo "  main: $MAIN_BEFORE -> $EXEC_SHA"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN — push 하지 않는다."
  exit 0
fi

LA_PROMOTION=ORCHESTRATOR_PROMOTION_ONLY git -C "$REPO" push origin "$EXEC_SHA:refs/heads/$MAIN"
echo "PROMOTED"
