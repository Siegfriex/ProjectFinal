#!/usr/bin/env bash
# v3.1 §5 — verified source-layer baseline 을 research/landing-accessibility-main 으로 승격한다.
# 오케스트레이터 전용. hook 이 아니라 이 스크립트가 검사의 정본이다 (§6: hook 은 유일 보증수단이 아니다).
set -euo pipefail
REPO="/home/sieg/projects-wsl/ProjectFinal"
MAIN="research/landing-accessibility-main"
PILOT_SHA="32460b87334a67f6a74823ac55f85ca80a9f8980"
EXEC_SHA="${1:?usage: promote_landing_main.sh <exec_sha> <adversarial_sha> <ssot_sha> <reconciliation_sha>}"
ADV_SHA="${2:?}"; SSOT_SHA="${3:?}"; REC_SHA="${4:?}"
cd "$REPO"
fail() { echo "PROMOTION BLOCKED: $*" >&2; exit 1; }

# 1. Pilot 불변
[ -z "$(git diff --stat "$PILOT_SHA" "$EXEC_SHA" -- research/refcohort)" ] || fail "Pilot path diff != 0"
# 2. 두 감사가 같은 exec SHA 를 대상으로 했는가
for A in "$ADV_SHA:audit/landing-adversarial" "$SSOT_SHA:audit/landing-ssot"; do
  sha="${A%%:*}"; br="${A##*:}"
  git merge-base --is-ancestor "$sha" "origin/$br" 2>/dev/null || fail "$br 에 $sha 없음"
done
# 3. 워킹트리 clean
[ -z "$(git -C "$REPO/.agent_worktrees/landing_exec" status --porcelain)" ] || fail "exec 워크트리 dirty"
# 4. open P0 = 0
P0=$(python3 -c "
import json,sys
s=json.load(open('$REPO/.agent_worktrees/landing_orchestrator/research/landing_accessibility/control/state.json'))
print(len([x for x in s.get('open_p0',[]) if x.get('state','').startswith('OPEN')]))")
[ "$P0" = "0" ] || fail "open P0 = $P0"
# 5. reconciliation 이 current 인가
python3 -c "
import json,sys
s=json.load(open('$REPO/.agent_worktrees/landing_orchestrator/research/landing_accessibility/control/state.json'))
al=s['audit_lag']
assert al['latest_adversarial_target_sha']=='$EXEC_SHA', 'adversarial target != exec'
assert al['latest_ssot_target_sha']=='$EXEC_SHA', 'ssot target != exec'
assert al['unaudited_cycle_depth']<=1, 'audit lag > 1'
" || fail "audit lag / target sha 불일치"

MAIN_BEFORE=$(git rev-parse "origin/$MAIN")
echo "PROMOTION PRECHECK PASS"
echo "  exec=$EXEC_SHA  adv=$ADV_SHA  ssot=$SSOT_SHA  rec=$REC_SHA"
echo "  main: $MAIN_BEFORE -> $EXEC_SHA"
LA_PROMOTION=ORCHESTRATOR_PROMOTION_ONLY git push origin "$EXEC_SHA:refs/heads/$MAIN"
echo "PROMOTED"
