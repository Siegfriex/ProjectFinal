#!/usr/bin/env python3
"""A 발행 전건 — 해시를 공표하기 전에 push 한다 (Δ45/R39).

A 는 이 규칙을 B 에게 걸어 두고(T-B-BLK-010) 자신은 12 커밋 동안 어겼다.
문장으로 둔 규칙은 우회된다(Δ23). 실행 가능한 형태로 둔다.

    python3 a_publish_guard.py            # 발행 가능한가
    python3 a_publish_guard.py --sha X    # X 가 원격에 있는가까지 확인

exit 0 = 발행 가능 · 1 = 미push · 2 = 검사 자체가 못 돌았다
"""
import subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))


def git(*a):
    r = subprocess.run(["git", "-C", HERE, *a], capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    rc, br, _ = git("rev-parse", "--abbrev-ref", "HEAD")
    if rc:
        print("!! 브랜치를 못 읽었다 — 검사가 돌지 않았다. 통과로 읽지 마라")
        return 2
    rc, head, _ = git("rev-parse", "HEAD")
    if rc:
        print("!! HEAD 를 못 읽었다 — 검사가 돌지 않았다")
        return 2

    git("fetch", "-q", "origin", br)          # 원격을 새로 읽지 않으면 낡은 것과 비교한다
    rc, remote, err = git("rev-parse", f"origin/{br}")
    if rc:
        print(f"!! origin/{br} 이 없다 — 아직 한 번도 push 되지 않았다: {err}")
        return 1

    rc, ahead, _ = git("rev-list", "--count", f"origin/{br}..HEAD")
    ahead = int(ahead or 0)

    want = None
    if "--sha" in sys.argv:
        want = sys.argv[sys.argv.index("--sha") + 1]

    print(f"branch={br}\nlocal ={head}\nremote={remote}\nahead ={ahead}")
    if ahead:
        print(f"\n!! 미push {ahead} 커밋. **이 상태의 sha 를 티켓에 적으면 다른 평면이 읽을 수 없다.**")
        print("   git push origin " + br)
        return 1

    if want:
        rc, _, _ = git("merge-base", "--is-ancestor", want, f"origin/{br}")
        if rc:
            print(f"\n!! {want} 는 origin/{br} 의 조상이 아니다 — 공표할 수 없다")
            return 1
        print(f"\n{want} 는 원격에 있다")

    print("\n발행 가능")
    return 0


if __name__ == "__main__":
    sys.exit(main())
