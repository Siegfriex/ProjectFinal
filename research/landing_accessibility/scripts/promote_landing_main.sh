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
# usage:
#   promote_landing_main.sh <exec_sha> <adversarial_sha> <ssot_sha> <reconciliation_sha> [options]
# options:
#   --dry-run                 모든 검사를 수행하되 push 하지 않는다
#   --exec-branch=<ref>       exec 브랜치를 명시 (기본: exec_sha 로부터 워크트리 역해석)
#   --exec-worktree=<path>    exec 워크트리를 명시 (자동해석 우회, 존재 검증은 그대로)
set -euo pipefail

REPO="/home/sieg/projects-wsl/ProjectFinal"
MAIN="research/landing-accessibility-main"
ORCH_BRANCH="control/landing-orchestrator"
PILOT_SHA="32460b87334a67f6a74823ac55f85ca80a9f8980"
# setup_worktree.sh 가 만드는 환경 심링크. 저장소 내용이 아니므로 dirty 판정에서 제외한다.
# (`.gitignore` 의 `.venv/` `node_modules/` 는 디렉터리 패턴이라 심링크에는 매치되지 않는다.)
ENV_SYMLINKS=".venv env node_modules"

fail() { echo "PROMOTION BLOCKED: $*" >&2; exit 1; }
note() { echo "  · $*"; }

[ $# -ge 4 ] || fail "usage: promote_landing_main.sh <exec_sha> <adversarial_sha> <ssot_sha> <reconciliation_sha> [--dry-run] [--exec-branch=REF] [--exec-worktree=PATH]"
EXEC_SHA_IN="$1"; ADV_SHA="$2"; SSOT_SHA="$3"; REC_SHA="$4"; shift 4

DRY_RUN=0
EXEC_BRANCH=""
EXEC_WT=""
for arg in "$@"; do
  case "$arg" in
    --dry-run)          DRY_RUN=1 ;;
    --exec-branch=*)    EXEC_BRANCH="${arg#*=}" ;;
    --exec-worktree=*)  EXEC_WT="${arg#*=}" ;;
    *) fail "unknown option: $arg" ;;
  esac
done

git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || fail "$REPO 가 git 저장소가 아니다"

# ---------------------------------------------------------------- 0. SHA 실재 확인
EXEC_SHA="$(git -C "$REPO" rev-parse --verify --quiet "${EXEC_SHA_IN}^{commit}" || true)"
[ -n "$EXEC_SHA" ] || fail "exec SHA 를 해석할 수 없다: $EXEC_SHA_IN"
[ "$EXEC_SHA" = "$EXEC_SHA_IN" ] || note "exec sha 정규화: $EXEC_SHA_IN -> $EXEC_SHA"

# ---------------------------------------------------------------- 워크트리 해석
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
STATE="$ORCH_WT/research/landing_accessibility/control/state.json"
[ -f "$STATE" ] || fail "state.json 이 없다: $STATE"
note "state.json    = $STATE"

# ---------------------------------------------------------------- 1. Pilot 불변
[ -z "$(git -C "$REPO" diff --stat "$PILOT_SHA" "$EXEC_SHA" -- research/refcohort)" ] \
  || fail "Pilot path diff != 0 (research/refcohort 는 READ_ONLY, 수정 시 P0)"
note "1. Pilot 불변 OK"

# ---------------------------------------------------------------- 2. 두 감사가 같은 exec SHA
for A in "$ADV_SHA:audit/landing-adversarial" "$SSOT_SHA:audit/landing-ssot"; do
  sha="${A%%:*}"; br="${A##*:}"
  git -C "$REPO" merge-base --is-ancestor "$sha" "origin/$br" 2>/dev/null || fail "$br 에 $sha 없음"
done
note "2. 두 감사 SHA 가 원격 감사 브랜치의 조상 OK"

# ---------------------------------------------------------------- 3. exec 워크트리 clean + HEAD 일치
WT_HEAD="$(git -C "$EXEC_WT" rev-parse HEAD)"
[ "$WT_HEAD" = "$EXEC_SHA" ] \
  || fail "exec 워크트리 HEAD($WT_HEAD) != 승격 대상 SHA($EXEC_SHA) — 검증한 트리와 승격되는 SHA 가 다르다"
DIRTY="$(worktree_dirty_lines "$EXEC_WT")"
[ -z "$DIRTY" ] || fail "exec 워크트리 dirty ($EXEC_WT):"$'\n'"$DIRTY"
note "3. exec 워크트리 clean + HEAD == $EXEC_SHA OK (환경 심링크 $ENV_SYMLINKS 만 면제)"

# ---------------------------------------------------------------- 4. open P0 = 0 + blocking debt = 0
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
        msgs.append("v2_transition.open_blocking_total = %d "
                    "(v1 승계 %s + adversarial %s + ssot %s) — 00_SSOT_v2.0 §15 open blocking = 0 위반"
                    % (int(obt["total"]), obt.get("v1_inherited_blocking"),
                       obt.get("v2_adversarial_blocking"), obt.get("v2_ssot_blocking")))
print("\n".join(msgs))
PY
)"
[ -z "$BLOCK" ] || fail "blocking debt:"$'\n'"$BLOCK"
note "4. open P0/P1 = 0 · v2_transition.open_blocking_total = 0 OK"

# ---------------------------------------------------------------- 5. audit lag / target sha / verdict
python3 - "$STATE" "$EXEC_SHA" <<'PY' || fail "audit lag / target sha / verdict 불일치"
import json, sys
s = json.load(open(sys.argv[1], encoding="utf-8")); exec_sha = sys.argv[2]
al = s["audit_lag"]
assert al["latest_adversarial_target_sha"] == exec_sha, \
    "adversarial target(%s) != exec(%s)" % (al["latest_adversarial_target_sha"], exec_sha)
assert al["latest_ssot_target_sha"] == exec_sha, \
    "ssot target(%s) != exec(%s)" % (al["latest_ssot_target_sha"], exec_sha)
assert al["unaudited_cycle_depth"] <= al.get("MAX_UNAUDITED_EXEC_CYCLES", 1), "audit lag > bound"
for k in ("latest_adversarial_verdict", "latest_ssot_verdict"):
    v = al.get(k)
    assert v is None or v == "PASS", "%s = %s (PASS 아님)" % (k, v)
PY
note "5. audit lag / target sha / verdict OK"

MAIN_BEFORE="$(git -C "$REPO" rev-parse "origin/$MAIN")"
echo "PROMOTION PRECHECK PASS"
echo "  exec=$EXEC_SHA  adv=$ADV_SHA  ssot=$SSOT_SHA  rec=$REC_SHA"
echo "  exec worktree=$EXEC_WT"
echo "  main: $MAIN_BEFORE -> $EXEC_SHA"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN — push 하지 않는다."
  exit 0
fi

LA_PROMOTION=ORCHESTRATOR_PROMOTION_ONLY git -C "$REPO" push origin "$EXEC_SHA:refs/heads/$MAIN"
echo "PROMOTED"
