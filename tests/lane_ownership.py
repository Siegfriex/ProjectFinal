"""lane 소유 경계를 **lane 자신의 diff** 로 재는 공용 도구 (W5M).

## 왜 이 모듈이 생겼나

12 lane 병합 회귀에서 두 개의 격리 단언이 깨졌다. 둘 다 지키려던 명제 — "이 lane 은
engine 을 고치지 않는다" — 는 **여전히 참**이었고, 재는 대상이 틀렸다.

- `[인용]` `test_w5j_scroll_state.py::test_this_lane_does_not_touch_the_engine`:
  ``assert '9ea01038...' == '4090ada1...'`` — `l0_collector.py` 의 **절대 sha256** 을 쟀다.
  W5J 는 그 파일을 건드리지 않았는데, 같은 병합에 들어온 W5I 의 승인된 가산 수정
  (+37/-0) 때문에 깨졌다.
- `[인용]` `test_w5h_session_driver.py::...::test_engine_files_are_byte_identical_to_base`:
  ``git diff --name-only HEAD`` — **작업 트리 vs HEAD** 를 쟀다. 커밋된 순간 무조건
  빈 문자열이라 병합 뒤에는 무엇도 잡지 못한다(조용한 통과).

파일의 절대 상태를 재면 **다른 lane 의 승인된 변경까지 잡는다**. 작업 트리만 재면
**커밋된 위반을 놓친다**. 둘 다 소유 경계를 재는 도구가 아니다.

여기서는 lane 이 base 로부터 **자기가 만든 diff** 를 잰다. 그러면 단언이 오히려 강해진다:

- 다른 lane 의 변경에 면역이다 — 그 변경은 이 lane 의 diff 에 없다.
- 자기 lane 의 위반은 커밋했든 안 했든 잡는다 — 커밋된 lane diff 와 작업 트리 변경을
  합집합으로 본다.

## lane tip 을 못 찾으면 조용히 통과시키지 않는다

식별에 실패하면 `LaneTipUnresolvable` 을 던진다. 소유 경계를 못 쟀는데 초록불을 켜는 것이
바로 A 가 금지한 "시끄러운 실패를 조용한 통과로" 다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: 12 lane 이 공통으로 갈라져 나온 base. W5H/W5I/W5J 모두 이 커밋이 merge-base 다
#: (`git merge-base 7c5ae70 claude-b/w5{h,i,j}-*` 실측). W5J 테스트가 원래
#: `BASE_ENGINE_SHA256` 의 근거로 적어 둔 것과 같은 커밋이다.
LANE_BASE = "7c5ae70def2da675f7d2d586a0b678ba9fdfc6dc"

ENGINE_DIR = "research/landing_accessibility/src/landing_accessibility/engine"


class LaneTipUnresolvable(RuntimeError):
    """lane 의 끝점을 특정하지 못했다 — 소유 경계를 잴 수 없다."""


def _git(*args: str, repo: Path = REPO) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise LaneTipUnresolvable(f"git {' '.join(args)} 실패: {proc.stderr.strip()}")
    return proc.stdout


def _rev(ref: str, *, repo: Path = REPO) -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout.strip()
    return out or None


def resolve_lane_tip(
    lane_branch: str, *, base: str = LANE_BASE, repo: Path = REPO
) -> tuple[str, str]:
    """lane 의 끝 커밋을 찾는다. `(찾은 방법, sha)`.

    세 상황 모두에서 같은 답이 나와야 한다.

    1. **병합 전** — lane 브랜치 위에서 돌 때. 브랜치 ref 가 곧 tip 이다.
    2. **병합 후, 브랜치 ref 가 남아 있을 때** — 마찬가지로 브랜치 ref.
    3. **병합 후, 브랜치 ref 가 정리됐을 때** — `base..HEAD` 의 병합 커밋 중 이 lane 을
       들여온 것을 찾아 그 **두 번째 부모**를 쓴다. 병합 커밋의 부모는 ref 가 지워져도
       남는다.
    """
    branch_sha = _rev(lane_branch, repo=repo)
    if branch_sha:
        return ("branch-ref", branch_sha)

    slug = lane_branch.split("/")[-1]
    log = _git("log", "--merges", "--format=%H%x00%P%x00%s", f"{base}..HEAD", repo=repo)
    for line in log.splitlines():
        sha, parents, subject = line.split("\x00", 2)
        parent_list = parents.split()
        if len(parent_list) < 2:
            continue
        if slug in subject or lane_branch in subject:
            return (f"merge-commit {sha[:12]}", parent_list[1])
    raise LaneTipUnresolvable(
        f"{lane_branch} 의 tip 을 찾지 못했다 — 브랜치 ref 도, {base[:7]}..HEAD 안의 "
        "병합 커밋도 이 lane 을 가리키지 않는다. 소유 경계를 잴 수 없으므로 통과시키지 않는다."
    )


def lane_committed_paths(
    lane_branch: str, *, base: str = LANE_BASE, repo: Path = REPO
) -> tuple[str, ...]:
    """lane 이 base 이후 **커밋으로** 바꾼 경로. 다른 lane 의 변경은 여기 없다."""
    _how, tip = resolve_lane_tip(lane_branch, base=base, repo=repo)
    fork = _git("merge-base", base, tip, repo=repo).strip()
    out = _git("diff", "--name-only", f"{fork}..{tip}", repo=repo)
    return tuple(sorted(p for p in out.splitlines() if p.strip()))


def worktree_paths(*, repo: Path = REPO) -> tuple[str, ...]:
    """아직 커밋되지 않은 변경 — 추적 파일 수정 + 새로 생긴 미추적 파일.

    작업 트리의 미커밋 변경은 어느 lane 소유인지 git 이 말해 주지 않는다. 지금 이
    워크트리에서 일하는 lane 의 것으로 보는 것이 가장 안전한 귀속이다.
    """
    tracked = _git("diff", "--name-only", "HEAD", repo=repo).splitlines()
    untracked = _git("ls-files", "--others", "--exclude-standard", repo=repo).splitlines()
    return tuple(sorted({p for p in [*tracked, *untracked] if p.strip()}))


def lane_changed_paths(
    lane_branch: str,
    *,
    base: str = LANE_BASE,
    repo: Path = REPO,
    include_worktree: bool = True,
) -> tuple[str, ...]:
    """이 lane 에 귀속되는 변경 경로 전체 (커밋 + 작업 트리 합집합)."""
    paths = set(lane_committed_paths(lane_branch, base=base, repo=repo))
    if include_worktree:
        paths |= set(worktree_paths(repo=repo))
    return tuple(sorted(paths))


def paths_under(paths: tuple[str, ...], prefix: str) -> tuple[str, ...]:
    """`prefix` 아래에 있는 경로만 고른다 — 파일 이름 열거보다 넓게 잡는다."""
    root = prefix.rstrip("/") + "/"
    return tuple(p for p in paths if p == prefix or p.startswith(root))
