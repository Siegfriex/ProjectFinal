#!/usr/bin/env bash
# landing-accessibility harness — git hook 설치기.
#
# **오케스트레이터·에이전트는 이 스크립트를 자동 실행하지 않는다.**
# core.hooksPath 는 저장소 전역 설정이라 다른 워크트리·다른 작업까지 영향을 받는다.
# 설치 여부는 사용자(Research Director) 결정 사항이다.
#
# usage:
#   scripts/install_hooks.sh --check      현재 설치 상태만 보고한다 (기본)
#   scripts/install_hooks.sh --symlink    <common git dir>/hooks/pre-push 를 심링크로 설치 (권장)
#   scripts/install_hooks.sh --hookspath  core.hooksPath 를 scripts/hooks 로 설정
#   scripts/install_hooks.sh --uninstall  위 두 설치를 되돌린다
#
# --symlink 를 권장하는 이유: core.hooksPath 를 바꾸면 저장소의 나머지 훅(있다면)이
# 전부 무효화된다. 심링크는 pre-push 하나만 교체한다.
set -euo pipefail

REPO="/home/sieg/projects-wsl/ProjectFinal"
SRC_REL="research/landing_accessibility/scripts/hooks"
MODE="${1:---check}"

# 이 스크립트가 있는 control 워크트리를 기준으로 원본을 찾는다.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$HERE/hooks"
SRC="$SRC_DIR/pre-push"
[ -f "$SRC" ] || { echo "ERROR: 훅 원본이 없다: $SRC" >&2; exit 1; }

GITDIR="$(git -C "$REPO" rev-parse --git-common-dir)"
case "$GITDIR" in /*) ;; *) GITDIR="$REPO/$GITDIR" ;; esac
DST="$GITDIR/hooks/pre-push"

report() {
  echo "repo            : $REPO"
  echo "common git dir  : $GITDIR"
  echo "hook 원본       : $SRC"
  echo "core.hooksPath  : $(git -C "$REPO" config --get core.hooksPath || echo '(unset)')"
  if [ -L "$DST" ]; then
    echo "$DST : symlink -> $(readlink "$DST")"
  elif [ -f "$DST" ]; then
    echo "$DST : 일반 파일 (추적되지 않는 로컬 사본)"
    if cmp -s "$SRC" "$DST"; then echo "  내용: 원본과 동일"; else echo "  내용: 원본과 다름 (DRIFT)"; fi
  else
    echo "$DST : 없음"
  fi
}

case "$MODE" in
  --check)
    report
    echo
    echo "설치하려면: $0 --symlink   (또는 --hookspath)"
    ;;
  --symlink)
    mkdir -p "$GITDIR/hooks"
    if [ -e "$DST" ] && [ ! -L "$DST" ]; then
      cp -p "$DST" "$DST.bak.$(date +%Y%m%d%H%M%S)"
      echo "기존 훅을 백업했다: $DST.bak.*"
    fi
    ln -sfn "$SRC" "$DST"
    chmod +x "$SRC"
    echo "설치 완료: $DST -> $SRC"
    echo "주의: 심링크 대상은 control 워크트리 안이다. 그 워크트리를 지우면 훅이 죽는다."
    report
    ;;
  --hookspath)
    git -C "$REPO" config core.hooksPath "$SRC_DIR"
    chmod +x "$SRC"
    echo "설치 완료: core.hooksPath = $SRC_DIR"
    echo "주의: 저장소의 다른 훅은 이 디렉터리에 없으면 더 이상 실행되지 않는다."
    report
    ;;
  --uninstall)
    git -C "$REPO" config --unset core.hooksPath 2>/dev/null || true
    if [ -L "$DST" ]; then rm -f "$DST"; echo "심링크 제거: $DST"; fi
    report
    ;;
  *)
    echo "usage: $0 [--check|--symlink|--hookspath|--uninstall]" >&2; exit 2 ;;
esac
