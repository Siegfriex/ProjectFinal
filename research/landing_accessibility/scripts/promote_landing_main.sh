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
#     → 검사 5 재작성. verdict 미기록은 더 이상 통과하지 않는다.
#   `verify-script-declared-in-promotion-path-but-never-called` (P2/V2_SSOT_FROZEN-blocking)
#   / ssot V2-C002 `execution-authority-overclaims-verify-script-invocation`
#     → 검사 6 신설. verify_v2_docs.py 를 exec 워크트리에서 실제로 실행한다.
#
# 검사 순서: 0 SHA 실재 · 워크트리 해석 · 1 Pilot · 2 감사 SHA · 3 clean+HEAD
#            · 4 설치 무결성(verify_v2_docs.py 실호출) · 5 blocking debt · 6 verdict(fail-closed)
#   무결성 검증은 exec **트리** 검사이므로 clean/HEAD 와 같은 층(3 바로 뒤)에 둔다.
#   원장(state.json)·verdict(감사 브랜치) 검사는 그 다음 층이다.
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

# ---------------------------------------------------------------- 4. 설치 무결성 검증 실호출
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
note "4. verify_v2_docs.py exit 0 OK — $(printf '%s' "$VERIFY_OUT" | tail -1)"

# ---------------------------------------------------------------- 5. open P0 = 0 + blocking debt = 0
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
note "5. open P0/P1 = 0 · v2_transition.open_blocking_total = 0 OK"

# ---------------------------------------------------------------- 6. audit lag / target sha / verdict
# V2-C003 시정 — adversarial V2-C002 `promotion-verdict-check-treats-missing-verdict-as-pass`
#   이전 버전은 `assert v is None or v == "PASS"` 였다. verdict 미기록(키 부재·null)이
#   명시적으로 통과했다 — fail-open 이 코드에 적혀 있었다. 이제 두 감사의 verdict 가
#   **명시적으로 PASS** 여야만 통과하며, state.json 자기기록만 믿지 않고 원격 감사 브랜치의
#   보고서 JSON 을 직접 읽어 재확인한다. 파일 부재·파싱 실패·필드 부재·target_sha 불일치는
#   전부 차단이다 (fail-closed).
python3 - "$STATE" "$EXEC_SHA" "$REPO" "$ADV_SHA" "$SSOT_SHA" <<'PY' || fail "audit lag / target sha / verdict 불일치"
import json
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

# 5-b. 감사 보고서 JSON 원본 재확인 — state.json 하나를 잘못 쓰면 검사 4·5 가 함께 무력화되므로
#      승격 인자로 받은 감사 SHA 에서 보고서를 직접 읽어 대조한다.
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
note "6. audit lag / target sha / verdict (state + 감사보고서 JSON 양쪽 PASS) OK"

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
