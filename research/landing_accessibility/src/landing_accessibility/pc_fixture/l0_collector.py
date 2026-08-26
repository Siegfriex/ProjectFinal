"""L0 수집기 — 로컬/합성 픽스처 전용.

이 레인은 SHADOW/PREPARATORY 다(``docs/v2/PHASE_GATES.md`` §4). Playwright 는
실제로 쓰지만 목적지는 항상 로컬 ``file://`` 픽스처다 — ``execution_mode`` 가
그 경계를 코드로 강제한다 (``execution_mode.py``).

닫는 결함(Pilot 감사 no-interaction-evidence-but-called-complete, MEDIUM):
    refcohort 는 dom/ax/screen/probe 4종 정적 증거만 모으고도 플래그 이름을
    ``evidence_complete`` 라고 불렀다. 여기서는 정적 4종 완결을
    ``static_evidence_complete`` 로, 실제 interaction evidence(L1 Scout 가
    남기는 activation trace) 유무를 ``interaction_evidence_present`` 로
    분리해서 이름 자체가 거짓말하지 않게 한다. L0 만 수행한 관측은 항상
    ``interaction_evidence_present=False`` 다.
"""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import ViewportSize, sync_playwright

from .domain_scope import scope_relation as compute_scope_relation
from .execution_mode import enforce_real_target_firewall
from .gate import GateEvidence, GateSignal, detect_gate
from .guarded_writer import GuardedEvidenceWriter, ObservationRecord
from .identity import observation_id as make_observation_id
from .probe_eval import PROBE_JS

# scope_relation 값 중 이 두 값은 requested/final URL 일관성이 깨졌다는 신호다.
# (닫는 결함: scope-relation-suffix-truncation 의 2차 증상 — report 가 이 값을
# 참조하지 않아 범위 밖 관측이 조용히 집계에 섞였다. 여기서는 관측 시점에
# note 로 남긴다.)
_WRONG_URL_SCOPES = frozenset({"EXTERNAL_PARTNER_DOMAIN", "UNRESOLVED"})

VIEWPORT: ViewportSize = {"width": 390, "height": 844}
LOCALE = "ko-KR"


@dataclass
class L0Observation:
    observation_id: str
    record: ObservationRecord
    probe: dict[str, Any]
    gate: GateSignal
    static_evidence_complete: bool


def _ax_tree(context, page) -> tuple[list[dict], int]:
    """CDP 로 AX 트리를 가져온다. Playwright 최신판은 page.accessibility 를
    제거했으므로 CDP 를 직접 쓴다(Pilot collect.py 와 동일 패턴, 참고용 포팅)."""
    cdp = context.new_cdp_session(page)
    try:
        cdp.send("Accessibility.enable")
        full = cdp.send("Accessibility.getFullAXTree")
        nodes = full.get("nodes", [])
        slim = [
            {
                "role": (n.get("role") or {}).get("value"),
                "name": (n.get("name") or {}).get("value"),
            }
            for n in nodes
            if (n.get("role") or {}).get("value") not in (None, "none", "generic", "InlineTextBox")
        ]
        return slim, len(nodes)
    finally:
        with contextlib.suppress(Exception):
            cdp.detach()


def collect_l0_fixture(
    *,
    fixture_path: Path,
    service_id: str,
    canonical_url: str,
    audit_date: str,
    protocol_version: str,
    store: GuardedEvidenceWriter,
    execution_mode: str = "FIXTURE",
) -> L0Observation:
    """로컬 HTML 픽스처 하나에서 L0 증거를 수집하고 append-only 로 저장한다."""
    # REAL-TARGET FIREWALL — 이 함수의 어떤 副수효과보다 먼저 검사한다.
    enforce_real_target_firewall(execution_mode)
    if execution_mode != store.execution_mode:
        raise ValueError(
            f"execution_mode 불일치: 호출={execution_mode!r} writer={store.execution_mode!r}"
        )

    if not fixture_path.exists():
        raise FileNotFoundError(fixture_path)
    oid = make_observation_id(service_id, canonical_url, audit_date, protocol_version)
    fixture_url = fixture_path.resolve().as_uri()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(
                viewport=VIEWPORT, locale=LOCALE, is_mobile=True, has_touch=True
            )
            page = context.new_page()
            redirect_chain: list[dict[str, Any]] = []
            page.on(
                "response",
                lambda r: (
                    redirect_chain.append({"url": r.url, "status": r.status})
                    if r.request.is_navigation_request()
                    else None
                ),
            )
            try:
                resp = page.goto(fixture_url, wait_until="load", timeout=15000)
                # meta-refresh 등으로 최초 load 직후 다시 navigate 되는 픽스처가 있다
                # (예: wrong_url_redirect.html) — evaluate 시점에 실행 컨텍스트가
                # 이미 파괴됐을 수 있으므로 안정화를 한 번 더 기다리고 재시도한다.
                try:
                    probe = page.evaluate(PROBE_JS)
                except Exception:
                    with contextlib.suppress(Exception):
                        page.wait_for_load_state("load", timeout=8000)
                    probe = page.evaluate(PROBE_JS)
                ax, ax_total = _ax_tree(context, page)
                dom = page.content().encode("utf-8")
                shot = page.screenshot(full_page=False)
                shot_full = page.screenshot(full_page=True)
                final_url = page.url
                http_status = resp.status if resp else None
            finally:
                with contextlib.suppress(Exception):
                    context.close()
                    browser.close()
    except Exception as e:
        store.record_discarded_attempt(
            observation_id=oid,
            reason="L0_COLLECTION_EXCEPTION",
            detail=f"{type(e).__name__}: {e}",
        )
        raise

    if not isinstance(probe, dict):
        probe = {}

    gate_ev = GateEvidence(
        final_url_path=urlparse(final_url).path,
        page_title=probe.get("page_title", ""),
        http_status=http_status,
        has_password_input=bool(probe.get("has_password_input")),
        form_actions=list(probe.get("form_actions") or []),
        landmark_text=probe.get("landmark_text", ""),
    )
    gate = detect_gate(gate_ev)

    # requested/final URL 일관성 — "wrong URL" 실패주입이 잡아야 하는 자리.
    # 이 레인은 file:// 픽스처만 다루므로 canonical_url(운영 목표 URL, 보통
    # https://) 이 아니라 requested_url(fixture_url, 실제로 연 file://) 을
    # final_url 과 비교한다 — canonical_url 대조는 REAL_TARGET 배치 이후의 몫이다.
    scope = compute_scope_relation(fixture_url, final_url)
    notes: list[str] = [] if probe else ["PROBE_EMPTY_OR_NON_DICT"]
    if scope in _WRONG_URL_SCOPES:
        notes.append(f"WRONG_URL_SUSPECTED scope_relation={scope}")
    # scope_relation 의 file:// 특례(경로만 비교)는 "다른 corpus 묶음으로 튄" 리다이렉트를
    # 못 잡는다(둘 다 SAME_ORIGIN_PATH 로만 보인다) — 그래서 이 레인 전용으로 한 겹 더
    # 검사한다: 최종 경로의 부모 디렉터리가 요청 경로 부모와 같거나 그 하위가 아니면 의심스럽다.
    req_parent = Path(urlparse(fixture_url).path).parent
    final_parent = Path(urlparse(final_url).path).parent
    is_same_or_child = final_parent == req_parent or req_parent in final_parent.parents
    if not is_same_or_child:
        notes.append(
            f"WRONG_URL_SUSPECTED file_family_mismatch req={req_parent} final={final_parent}"
        )

    dom_entry = store.write_evidence_file(oid, "dom", f"{oid}.html", dom)
    ax_bytes = json.dumps(ax, ensure_ascii=False).encode("utf-8")
    ax_entry = store.write_evidence_file(oid, "ax", f"{oid}.json", ax_bytes)
    screen_entry = store.write_evidence_file(oid, "screen", f"{oid}.png", shot)
    screen_full_entry = store.write_evidence_file(oid, "screen_full", f"{oid}.png", shot_full)
    probe_bytes = json.dumps(probe, ensure_ascii=False).encode("utf-8")
    probe_entry = store.write_evidence_file(oid, "probe", f"{oid}.json", probe_bytes)

    static_complete = bool(probe) and len(dom) > 256 and len(shot) > 2048 and ax_total > 2
    if not static_complete:
        # "missing screenshot" / "malformed AX" 실패주입이 이 note 로 드러난다 — refcohort
        # 의 EVIDENCE_THIN 경보 자체는 유효한 아이디어였다. 틀린 건 플래그 **이름**이었다
        # (no-interaction-evidence-but-called-complete). 이름만 고쳐서 재사용한다.
        notes.append(f"STATIC_EVIDENCE_THIN dom={len(dom)}B shot={len(shot)}B ax_nodes={ax_total}")

    record = ObservationRecord(
        observation_id=oid,
        service_id=service_id,
        canonical_url=canonical_url,
        requested_url=fixture_url,
        audit_date=audit_date,
        protocol_version=protocol_version,
        collected_at=datetime.now(UTC).isoformat(),
        execution_mode=execution_mode,
        static_evidence_complete=static_complete,
        interaction_evidence_present=False,
        gated_boundary_tag=gate.tag,
        gate_fired_signals=gate.fired_signals,
        notes=notes,
        provenance=store.observation_provenance(),
        extra={
            "evidence_refs": {
                "dom": dom_entry.relpath,
                "ax": ax_entry.relpath,
                "screen": screen_entry.relpath,
                "screen_full": screen_full_entry.relpath,
                "probe": probe_entry.relpath,
            },
            "ax_node_count": ax_total,
            "http_status": http_status,
            "final_url": final_url,
            "redirect_chain": redirect_chain[:20],
            "scope_relation": scope,
            "viewport": probe.get("viewport"),
            "page_scroll_height": probe.get("page_scroll_height"),
        },
    )
    store.append_observation(record)

    return L0Observation(
        observation_id=oid,
        record=record,
        probe=probe,
        gate=gate,
        static_evidence_complete=static_complete,
    )
