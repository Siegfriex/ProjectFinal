"""모바일웹 endpoint에서 DOM·AX·Screen·Interaction 증거를 한 세션으로 수집한다.

프로토콜 v2 §4를 따른다. 판정하지 않고 적용기회와 원시 관측값만 남긴다.
로그인·결제·본인확인·CAPTCHA 경계는 감지 즉시 관측을 멈추고 태그만 기록한다.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Error as PWError
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

PROBE = (Path(__file__).parent / "probe.js").read_text(encoding="utf-8")

VIEWPORT = {"width": 390, "height": 844}
DEVICE_SCALE = 3
LOCALE = "ko-KR"
TIMEZONE = "Asia/Seoul"
UA = (
    "Mozilla/5.0 (Linux; Android 13; SM-S911N) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
)

GATE_TAGS = {
    "login_form": "LOGIN_REQUIRED",
    "login_keyword": "LOGIN_REQUIRED",
    "identity_keyword": "IDENTITY_VERIFICATION_REQUIRED",
    "payment_keyword": "PAYMENT_REQUIRED",
    "captcha_keyword": "CAPTCHA_REQUIRED",
    "personal_data_keyword": "PERSONAL_DATA_REQUIRED",
}


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def sha256_obj(o: Any) -> str:
    return sha256_bytes(json.dumps(o, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def scope_relation(cert_url: str, final_url: str | None) -> str:
    """프로토콜 v2 §2.2의 scope_relation 판정."""
    if not final_url:
        return "UNRESOLVED"
    c, f = urlparse(cert_url), urlparse(final_url)
    if c.scheme == f.scheme and c.netloc == f.netloc and c.path.rstrip("/") == f.path.rstrip("/"):
        return "EXACT_URL"
    if c.netloc == f.netloc:
        return "SAME_ORIGIN_PATH"
    cn, fn = c.netloc.lower(), f.netloc.lower()
    bare_c = cn[4:] if cn.startswith("www.") else cn
    bare_f = fn[2:] if fn.startswith("m.") else (fn[4:] if fn.startswith("www.") else fn)
    if bare_c == bare_f:
        return "MOBILE_SUBDOMAIN_REDIRECT"
    # 등록 도메인이 같으면 동일 서비스의 서브도메인 이동으로 본다
    if ".".join(bare_c.split(".")[-2:]) == ".".join(bare_f.split(".")[-2:]):
        return "MOBILE_SUBDOMAIN_REDIRECT"
    return "EXTERNAL_PARTNER_DOMAIN"


@dataclass
class CollectResult:
    record_id: str
    target_url: str
    run_id: str
    collected_at: str
    final_url: str | None = None
    http_status: int | None = None
    redirect_chain: list[dict] = field(default_factory=list)
    scope_relation: str = "UNRESOLVED"
    transport_error: str | None = None
    probe: dict | None = None
    ax_nodes: int | None = None
    ax_ref: str | None = None
    dom_ref: str | None = None
    screen_ref: str | None = None
    probe_ref: str | None = None
    dom_sha256: str | None = None
    screen_sha256: str | None = None
    ax_sha256: str | None = None
    gated_boundary_tag: str = "NONE"
    observability_scope: str = "NOT_OBSERVED"
    viewport_css_px: str = f"{VIEWPORT['width']}x{VIEWPORT['height']}"
    device_pixel_ratio: int = DEVICE_SCALE
    physical_mm_estimate: None = None
    physical_mm_estimate_method: str = "UNAVAILABLE"
    physical_mm_estimate_confidence: str = "NONE"
    evidence_complete: bool = False
    access_block: str | None = None
    frame_count: int = 0
    notes: list[str] = field(default_factory=list)


def _ax_tree(context, page) -> tuple[list[dict], int]:
    """CDP로 전체 접근성 트리를 가져온다. Playwright 1.62에서 page.accessibility가 제거되어 CDP를 쓴다."""
    cdp = context.new_cdp_session(page)
    try:
        cdp.send("Accessibility.enable")
        full = cdp.send("Accessibility.getFullAXTree")
        nodes = full.get("nodes", [])
        slim = []
        for n in nodes:
            role = (n.get("role") or {}).get("value")
            name = (n.get("name") or {}).get("value")
            if role in (None, "none", "generic", "InlineTextBox"):
                continue
            slim.append(
                {
                    "nodeId": n.get("nodeId"),
                    "backendDOMNodeId": n.get("backendDOMNodeId"),
                    "role": role,
                    "name": name,
                    "description": (n.get("description") or {}).get("value"),
                    "value": (n.get("value") or {}).get("value"),
                    "ignored": n.get("ignored", False),
                    "properties": [
                        {"name": p.get("name"), "value": (p.get("value") or {}).get("value")}
                        for p in (n.get("properties") or [])
                        if p.get("name")
                        in (
                            "focusable",
                            "focused",
                            "hidden",
                            "disabled",
                            "required",
                            "invalid",
                            "level",
                            "checked",
                            "expanded",
                        )
                    ],
                }
            )
        return slim, len(nodes)
    finally:
        with contextlib.suppress(Exception):
            cdp.detach()


def _gate_from_probe(probe: dict | None) -> str:
    if not isinstance(probe, dict):
        return "NONE"
    sig = (probe.get("opportunities") or {}).get("gate_signal") or [{}]
    sig = sig[0] if sig else {}
    for key, tag in GATE_TAGS.items():
        if sig.get(key):
            return tag
    return "NONE"


def _scope_from_probe(probe: dict | None, gate: str) -> str:
    if not isinstance(probe, dict):
        return "NOT_OBSERVED"
    page = (probe.get("opportunities") or {}).get("page_signal") or [{}]
    page = page[0] if page else {}
    text_len = page.get("text_length") or 0
    controls = page.get("visible_control_count") or 0
    links = page.get("visible_link_count") or 0
    if text_len < 30 and controls == 0 and links == 0:
        return "NOT_OBSERVED"
    if gate != "NONE":
        return "LANDING_ONLY"
    if page.get("search_input") or controls >= 3:
        return "TASK_ENTRY"
    return "LANDING_ONLY"


def collect_one(
    record_id: str,
    target_url: str,
    run_dir: Path,
    run_id: str,
    timeout_ms: int = 45000,
    wait_after_load_ms: int = 2500,
) -> CollectResult:
    """endpoint 하나에서 4종 증거를 수집한다."""
    res = CollectResult(
        record_id=record_id,
        target_url=target_url,
        run_id=run_id,
        collected_at=datetime.now(UTC).isoformat(),
    )
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", record_id)
    for sub in ("dom", "ax", "screen", "probe"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=DEVICE_SCALE,
            locale=LOCALE,
            timezone_id=TIMEZONE,
            is_mobile=True,
            has_touch=True,
            user_agent=UA,
            ignore_https_errors=True,
        )
        page = context.new_page()
        chain: list[dict] = []
        page.on(
            "response",
            lambda r: (
                chain.append({"url": r.url, "status": r.status})
                if r.request.is_navigation_request()
                else None
            ),
        )
        try:
            resp = page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
            res.http_status = resp.status if resp else None
            try:
                page.wait_for_load_state("networkidle", timeout=wait_after_load_ms)
            except PWTimeout:
                res.notes.append("NETWORKIDLE_TIMEOUT")
            res.final_url = page.url
            res.redirect_chain = chain[:20]
            res.scope_relation = scope_relation(target_url, res.final_url)

            probe = page.evaluate(PROBE)
            if not isinstance(probe, dict):
                # 네비게이션 중 실행 컨텍스트가 교체되면 undefined가 돌아온다. 안정화 후 1회 재시도한다.
                res.notes.append("PROBE_NULL_RETRY")
                with contextlib.suppress(PWTimeout):
                    page.wait_for_load_state("domcontentloaded", timeout=8000)
                probe = page.evaluate(PROBE)
            if not isinstance(probe, dict):
                res.notes.append("PROBE_NULL_AFTER_RETRY")
                probe = None
            res.probe = probe
            res.final_url = page.url
            res.gated_boundary_tag = _gate_from_probe(probe)
            res.observability_scope = _scope_from_probe(probe, res.gated_boundary_tag)

            ax, ax_total = _ax_tree(context, page)
            res.ax_nodes = ax_total

            dom = page.content().encode("utf-8")
            shot = page.screenshot(full_page=False)

            dom_p = run_dir / "dom" / f"{safe}.html"
            ax_p = run_dir / "ax" / f"{safe}.json"
            sc_p = run_dir / "screen" / f"{safe}.png"
            pr_p = run_dir / "probe" / f"{safe}.json"
            dom_p.write_bytes(dom)
            ax_p.write_text(json.dumps(ax, ensure_ascii=False), encoding="utf-8")
            sc_p.write_bytes(shot)
            pr_p.write_text(json.dumps(probe, ensure_ascii=False), encoding="utf-8")

            res.dom_ref, res.ax_ref, res.screen_ref, res.probe_ref = (
                str(dom_p.relative_to(run_dir.parent.parent)),
                str(ax_p.relative_to(run_dir.parent.parent)),
                str(sc_p.relative_to(run_dir.parent.parent)),
                str(pr_p.relative_to(run_dir.parent.parent)),
            )
            res.dom_sha256 = sha256_bytes(dom)
            res.screen_sha256 = sha256_bytes(shot)
            res.ax_sha256 = sha256_obj(ax)

            # HTTP 오류 상태는 접근성 결함이 아니라 관측 차단이다. 분모에는 남기되 측정 성공으로 세지 않는다.
            if res.http_status is not None and res.http_status >= 400:
                res.access_block = f"HTTP_{res.http_status}"
                res.notes.append(f"ACCESS_BLOCKED_HTTP_{res.http_status}")

            # 증거 완결성: 4종이 모두 있고 비어 있지 않아야 한다 (fast_collection의 3KB 빈 스크린샷 방지)
            res.evidence_complete = (
                probe is not None
                and res.access_block is None
                and len(dom) > 512
                and len(shot) > 8192
                and ax_total > 3
                and res.observability_scope != "NOT_OBSERVED"
            )
            if not res.evidence_complete:
                res.notes.append(
                    f"EVIDENCE_THIN dom={len(dom)}B shot={len(shot)}B ax={ax_total} scope={res.observability_scope}"
                )
        except (PWError, PWTimeout) as e:
            res.transport_error = f"{type(e).__name__}:{str(e)[:300]}"
            res.notes.append("TRANSPORT_FAILURE")
        finally:
            with contextlib.suppress(Exception):
                context.close()
                browser.close()
    return res


def to_row(res: CollectResult) -> dict:
    d = asdict(res)
    d.pop("probe", None)  # 원본은 probe/*.json에 별도 보존
    return d
