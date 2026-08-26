#!/usr/bin/env python3
"""C009(B6) — A1 원문(와이즈앱 인사이트 933) 취득 경로를 코드로 고정한다.

C001 은 원문을 확보했지만 취득 절차가 매니페스트 산문("curl_cffi POST …", "playwright render …")
으로만 남아 있어서 제3자가 같은 자료를 다시 만들 수 없었다. 감사 지적 B6 을 받아 그 절차를
실행 가능한 코드로 옮긴다.

세 가지 모드
    --verify    (기본) 네트워크를 쓰지 않는다. 이미 동결된 raw 자산의 sha256 을
                authority_manifest.json / source_evidence_manifest.json 과 대조한다.
                clone 만 받은 사람이 동결본 무결성을 확인하는 경로다.
    --acquire   원문을 새로 취득해 --out 디렉터리에 쓴다. **동결본을 덮어쓰지 않는다.**
                발행처가 모집단 변경을 사전 공지(nid=127, 종료일 없음)한 상태라 재취득 결과가
                동결본과 다를 수 있고, 그 차이는 지워야 할 오류가 아니라 기록해야 할 사실이다.
    --diff      --acquire 산출물과 동결본의 sha256 을 대조해 판본 변화만 보고한다.

취득 경로 (원문 구조에 의존하는 부분을 명시한다)
    1. POST https://www.wiseapp.co.kr/insight/detail/getDetail.json
       body {insightNid: "933", preview: 0}  → 메타데이터 + 본문 HTML + imgInfoList
       봇 차단이 있어 curl_cffi 의 chrome impersonation 을 쓴다.
    2. Playwright(chromium) 로 인사이트 상세 페이지를 렌더링해
       (a) 렌더된 HTML, (b) 본문 텍스트, (c) full-page 스크린샷,
       (d) <img> 목록(src/alt/naturalWidth/naturalHeight),
       (e) 페이지가 발생시킨 XHR 응답(getlist.json 공지 포함)을 남긴다.
       figure 이미지는 CDN 직접 요청이 403 이라 렌더링 경로로만 확보된다.
    3. imgInfoList(13건) 중 렌더된 본문이 참조하는 11건만 figure 로 채택한다.
       제외 2건의 근거는 authority_manifest.image_inventory_reconciliation 에 있다.

예의
    순차 요청만 쓰고 요청 간 1초 이상 쉰다. User-Agent 에 연구 목적과 연락 경로를 밝힌다.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WISEAPP = ROOT / "sources" / "wiseapp"
FROZEN_RAW = WISEAPP / "raw"

sys.path.insert(0, str(ROOT / "src"))

from landing_accessibility import authority_manifest as am  # noqa: E402

INSIGHT_NID = "933"
INSIGHT_SLUG = "2025-active-senior-app-retail-trend"
BASE = "https://www.wiseapp.co.kr"
DETAIL_API = f"{BASE}/insight/detail/getDetail.json"
PAGE_URL = f"{BASE}/insight/detail/{INSIGHT_NID}/{INSIGHT_SLUG}"

UA = (
    "LandingAccessibilityResearch/1.0 "
    "(academic study of Korean web accessibility; non-commercial; "
    "sequential requests, >=1s delay; contact: 6siegfriex@gmail.com)"
)
DELAY_SEC = 1.0

# 동결본 파일 ↔ authority_manifest.raw_assets 키
FROZEN_ASSETS: dict[str, str] = {
    "wiseapp933_detail.json": "detail_json",
    "wiseapp933_rendered.html": "rendered_html",
    "wiseapp933_text.txt": "body_text",
    "wiseapp933_full.png": "full_page_screenshot",
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_prefix(digest: str) -> str:
    return digest.split(":", 1)[1] if ":" in digest else digest


# ── verify ─────────────────────────────────────────────────────────────────


def verify() -> int:
    """네트워크 없이 동결본 무결성을 확인한다."""
    manifest = json.loads((WISEAPP / "authority_manifest.json").read_text(encoding="utf-8"))
    evidence = json.loads((WISEAPP / "source_evidence_manifest.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    for filename, key in FROZEN_ASSETS.items():
        path = FROZEN_RAW / filename
        declared = manifest["raw_assets"].get(key)
        if declared is None:
            failures.append(f"{key}: 매니페스트에 선언이 없다")
            continue
        if not path.exists():
            failures.append(f"{filename}: 파일이 없다 (선언 sha256={declared['sha256']})")
            continue
        actual = sha256_of(path)
        if actual != _strip_prefix(declared["sha256"]):
            failures.append(
                f"{filename}: sha256 불일치\n  선언 {declared['sha256']}\n  실제 {actual}"
            )
        elif path.stat().st_size != declared["bytes"]:
            failures.append(
                f"{filename}: 바이트 수 불일치 {path.stat().st_size} != {declared['bytes']}"
            )
        else:
            print(f"OK  {filename}  {actual[:16]}…  {declared['bytes']:,} bytes")

    for fig in evidence["figures"]:
        path = ROOT / fig["file"]
        if not path.exists():
            failures.append(f"{fig['figure_id']}: {fig['file']} 이 없다")
            continue
        actual = sha256_of(path)
        if actual != _strip_prefix(fig["sha256"]):
            failures.append(f"{fig['figure_id']}: sha256 불일치")
        else:
            print(f"OK  {fig['figure_id']}  {actual[:16]}…  {fig['bytes']:,} bytes")

    # imgInfoList 정합 — 제외 2건의 근거가 매니페스트에 남아 있는지까지 확인한다.
    recon = manifest.get("image_inventory_reconciliation")
    if recon is None:
        failures.append("image_inventory_reconciliation 이 매니페스트에 없다")
    else:
        detail = json.loads((FROZEN_RAW / "wiseapp933_detail.json").read_text(encoding="utf-8"))
        n_imgs = len(detail["insightInfo"]["imgInfoList"])
        if n_imgs != recon["img_info_list_count"]:
            failures.append(f"imgInfoList {n_imgs}건 != 선언 {recon['img_info_list_count']}건")
        if len(evidence["figures"]) != recon["figures_in_evidence_manifest"]:
            failures.append("figure 수가 선언과 다르다")
        rendered = (FROZEN_RAW / "wiseapp933_rendered.html").read_text(
            encoding="utf-8", errors="replace"
        )
        for excluded in recon["excluded"]:
            name = excluded["img_path"].split("/")[-1]
            if rendered.count(name) != 0:
                failures.append(f"제외본 {name} 이 렌더된 본문에서 참조된다 — 제외 근거가 깨졌다")

    # V2-C008: 판본 계약과 해시 등재 커버리지를 같은 명령에서 확인한다.
    #   이 두 검사는 지금까지 src 모듈에만 있었고 운영 경로(--verify)에서 한 번도 호출되지
    #   않았다. 부르지 않는 검증기는 검증이 아니다.
    #   커버리지 검사는 sources/wiseapp 아래 **모든** 파일이 등재됐는지 본다 — v1 승계부채
    #   a1-raw-payload-files-not-hash-registered-in-authority-manifest 를 닫는 검사다.
    try:
        version = am.verify(WISEAPP / "authority_manifest.json")
        print(
            f"OK  authority_manifest 판본 rev{version['manifest_revision']} "
            f"({version['revised_at']}) 자기해시 일치"
        )
    except am.AuthorityManifestError as exc:
        failures.append(f"authority_manifest 판본 계약: {exc}")
    try:
        coverage = am.verify_hash_registry(WISEAPP / "authority_manifest.json", ROOT)
        print(
            f"OK  해시 등재 커버리지 {coverage['files_present']}파일 "
            f"(직접 {coverage['declared_directly']} / 위임 {coverage['declared_by_delegation']} / "
            f"자기해시 {coverage['self_hash_exempt']}) 미선언 0"
        )
    except am.AuthorityManifestError as exc:
        failures.append(f"해시 등재 커버리지: {exc}")

    if failures:
        print("\n실패:")
        for f in failures:
            print(" -", f)
        return 1
    print("\n동결본 무결성 확인 완료 — 모든 sha256 이 매니페스트 선언과 일치한다.")
    return 0


# ── acquire ────────────────────────────────────────────────────────────────


def fetch_detail_json() -> bytes:
    from curl_cffi import requests as cffi_requests

    response = cffi_requests.post(
        DETAIL_API,
        data={"insightNid": INSIGHT_NID, "preview": "0"},
        headers={"User-Agent": UA, "Referer": PAGE_URL},
        impersonate="chrome",
        timeout=60,
    )
    if response.status_code != 200:
        raise SystemExit(f"getDetail.json HTTP {response.status_code}")
    return response.content


def render_page(out_dir: Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    captured: list[dict[str, Any]] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(user_agent=UA, viewport={"width": 1600, "height": 1200})
        page = context.new_page()

        def on_response(resp: Any) -> None:
            # 페이지가 스스로 부른 XHR 만 남긴다. 공지(getlist.json)가 여기 들어온다.
            if ".json" not in resp.url:
                return
            # 바이너리/스트림 응답은 건너뛴다
            with contextlib.suppress(Exception):
                captured.append({"url": resp.url, "status": resp.status, "body": resp.text()})

        page.on("response", on_response)
        page.goto(PAGE_URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(3000)

        rendered_html = page.content()
        body_text = page.inner_text("body")
        images = page.eval_on_selector_all(
            "img",
            "els => els.map(e => ({src: e.src, alt: e.alt,"
            " w: e.naturalWidth, h: e.naturalHeight}))",
        )
        page.screenshot(path=str(out_dir / "wiseapp933_full.png"), full_page=True)
        browser.close()

    (out_dir / "wiseapp933_rendered.html").write_text(rendered_html, encoding="utf-8")
    (out_dir / "wiseapp933_text.txt").write_text(body_text, encoding="utf-8")
    (out_dir / "wiseapp933_images.json").write_text(
        json.dumps(images, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "wiseapp933_api.json").write_text(
        json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"images": images, "xhr_captured": len(captured)}


def acquire(out_dir: Path) -> int:
    if out_dir.resolve() == FROZEN_RAW.resolve():
        raise SystemExit(
            "동결본 디렉터리에 직접 쓰지 않는다. --out 으로 다른 경로를 지정하라.\n"
            "재취득 결과가 동결본과 다르면 그것은 판본 변화이며 기록 대상이다."
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    detail = fetch_detail_json()
    (out_dir / "wiseapp933_detail.json").write_bytes(detail)
    print(f"detail_json  {len(detail):,} bytes  sha256={hashlib.sha256(detail).hexdigest()[:16]}…")
    time.sleep(DELAY_SEC)

    info = render_page(out_dir)
    print(f"rendered     images={len(info['images'])}  xhr_json={info['xhr_captured']}")

    # figure 채택 규칙 — 렌더된 본문이 참조하는 CDN 이미지만 쓴다.
    rendered = (out_dir / "wiseapp933_rendered.html").read_text(encoding="utf-8")
    img_list = json.loads((out_dir / "wiseapp933_detail.json").read_text(encoding="utf-8"))[
        "insightInfo"
    ]["imgInfoList"]
    adopted: list[str] = []
    excluded: list[str] = []
    for entry in img_list:
        name = str(entry["imgPath"]).split("/")[-1]
        (adopted if rendered.count(name) else excluded).append(name)
    print(f"imgInfoList  {len(img_list)}건 → 채택 {len(adopted)} / 제외 {len(excluded)}")
    for name in excluded:
        print(f"  제외 {name} (렌더된 본문 미참조)")

    summary = {
        "acquired_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "page_url": PAGE_URL,
        "detail_api": DETAIL_API,
        "user_agent": UA,
        "img_info_list": len(img_list),
        "figures_adopted": adopted,
        "figures_excluded": excluded,
        "sha256": {p.name: sha256_of(p) for p in sorted(out_dir.glob("wiseapp933_*"))},
    }
    (out_dir / "acquisition_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n취득 요약: {out_dir / 'acquisition_summary.json'}")
    return 0


def diff(out_dir: Path) -> int:
    """재취득본과 동결본의 sha256 을 대조한다. 차이는 오류가 아니라 판본 변화다."""
    changed = 0
    for filename in sorted(FROZEN_ASSETS):
        new, old = out_dir / filename, FROZEN_RAW / filename
        if not new.exists():
            print(f"?   {filename}: 재취득본 없음")
            continue
        if not old.exists():
            print(f"?   {filename}: 동결본 없음")
            continue
        same = sha256_of(new) == sha256_of(old)
        print(f"{'==' if same else '!='}  {filename}")
        changed += 0 if same else 1
    if changed:
        print(
            f"\n{changed}개 자산이 동결본과 다르다. 발행처가 모집단 변경을 사전 공지한 상태이므로 "
            "이것은 판본 변화일 수 있다. 동결본을 덮어쓰지 말고 새 판본으로 기록하라 "
            "(authority_manifest.freeze_validity_window 참조)."
        )
    else:
        print("\n재취득본이 동결본과 바이트 단위로 같다.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--verify", action="store_true", help="동결본 sha256 대조 (기본, 네트워크 없음)"
    )
    mode.add_argument("--acquire", action="store_true", help="원문 재취득 (네트워크 사용)")
    mode.add_argument("--diff", action="store_true", help="재취득본과 동결본 대조")
    ap.add_argument("--out", type=Path, default=WISEAPP / "reacquired", help="재취득 산출물 경로")
    args = ap.parse_args()

    if args.acquire:
        return acquire(args.out)
    if args.diff:
        return diff(args.out)
    return verify()


if __name__ == "__main__":
    sys.exit(main())
