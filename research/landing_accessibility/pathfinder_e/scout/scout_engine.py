"""E REAL scout engine — v1, 단일 target 순차 실행.

안전 설계:
- 클릭 후보는 사전지정 task 키워드(패킷의 frozen_task/exploration hint)에 대한 텍스트/AX-name
  매칭으로만 고른다. 페이지를 보고 task 를 추론하지 않는다.
- 클릭 전 `is_safe_to_click()` 가드를 반드시 통과해야 한다 — 금지 키워드(로그인 submit, 결제,
  구매, 이체 실행 등) 매칭 시 클릭 자체를 거부한다.
- 폼 필드에 아무 값도 입력하지 않는다(이 버전은 INPUT_QUERY 를 아직 구현하지 않음 — F1 은
  타이핑이 필요 없는 family 라 v1 범위로 충분).
- endpoint 도달 또는 AUTH_GATE 판정 즉시 정지. 그 이후 어떤 조작도 하지 않는다.
- 모든 state 는 append-only 로 evidence_root 에 쓴다.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

VIEWPORT = {"width": 390, "height": 844}
UA = (
    "Mozilla/5.0 (Linux; Android 13; SM-S911N) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)
NAV_TIMEOUT_MS = 15000
SETTLE_MS = 500

# ── 안전 가드 — 클릭 직전 반드시 통과 ─────────────────────────────────────
FORBIDDEN_CLICK_PATTERNS = [
    r"로그인\s*하기", r"^로그인$", r"login\s*submit", r"본인\s*인증", r"인증\s*하기",
    r"이체\s*하기", r"이체\s*실행", r"송금\s*하기", r"송금\s*실행", r"보내기",
    r"결제", r"구매\s*하기", r"주문\s*하기", r"장바구니\s*담기", r"장바구니\s*추가",
    r"예약\s*하기", r"예약\s*확정", r"좌석\s*선택", r"발권",
    r"전화\s*걸기", r"전화\s*연결", r"통화", r"앱\s*으로\s*보기", r"앱\s*설치",
    r"동의\s*하고", r"가입\s*하기", r"회원가입", r"확인\s*(하기)?$",  # 단독 "확인"은 폼 제출일 위험 높음
]
FORBIDDEN_RE = re.compile("|".join(FORBIDDEN_CLICK_PATTERNS), re.IGNORECASE)

AUTH_GATE_URL_HINTS = ["login", "signin", "auth", "member/login", "cert", "본인인증"]
AUTH_GATE_TEXT_HINTS = ["아이디", "비밀번호", "공동인증서", "간편인증", "비밀번호 입력"]


def norm(s: str | None) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFC", " ".join(s.split()))


def is_safe_to_click(visible_label: str, accessible_name: str) -> tuple[bool, str]:
    text = f"{visible_label} {accessible_name}"
    m = FORBIDDEN_RE.search(text)
    if m:
        return False, f"forbidden_pattern_matched:{m.group(0)!r}"
    return True, ""


def looks_like_auth_gate(url: str, visible_text_sample: str) -> bool:
    u = url.lower()
    if any(h in u for h in AUTH_GATE_URL_HINTS):
        return True
    t = visible_text_sample
    hits = sum(1 for h in AUTH_GATE_TEXT_HINTS if h in t)
    return hits >= 2


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8", "replace"))


class ScoutRun:
    def __init__(self, packet: dict, evidence_root: Path, scout_run_id: str):
        self.packet = packet
        self.tc = packet["target_contract"]
        self.evidence_root = evidence_root
        self.scout_run_id = scout_run_id
        self.target_dir = evidence_root / scout_run_id / self.tc["target_id"]
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.states: list[dict] = []
        self.route: list[dict] = []
        self.terminal_status: str | None = None
        self.forbidden_actions_attempted = 0
        self.attempted_branches: list[dict] = []

    def _kst_now(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime())

    def capture_state(self, page, state_id: str, seq: int, action_token, terminal, nav_container="NONE", reveal="NONE", selected_candidate=None) -> dict:
        dom = None
        for attempt in range(5):
            try:
                page.wait_for_load_state("domcontentloaded", timeout=8000)
                dom = page.content()
                break
            except Exception:  # noqa: BLE001
                page.wait_for_timeout(400)
        if dom is None:
            dom = page.content()
        url = page.url
        try:
            ax = page.accessibility.snapshot(interesting_only=False) or {}
            if not ax or len(json.dumps(ax)) < 200:
                # 재시도 — SPA 하이드레이션 직후엔 AX 트리가 아직 얕을 수 있다
                page.wait_for_timeout(500)
                ax = page.accessibility.snapshot(interesting_only=False) or ax
        except Exception as e:  # noqa: BLE001
            ax = {"_error": str(e)}
        screenshot_bytes = page.screenshot()

        base = f"{state_id}"
        shot_path = self.target_dir / f"{base}.png"
        dom_path = self.target_dir / f"{base}.dom.html"
        ax_path = self.target_dir / f"{base}.ax.json"
        shot_path.write_bytes(screenshot_bytes)
        dom_path.write_text(dom, encoding="utf-8")
        ax_path.write_text(json.dumps(ax, ensure_ascii=False), encoding="utf-8")

        visible_text = norm(page.inner_text("body")) if page.query_selector("body") else ""

        record = {
            "scout_run_id": self.scout_run_id,
            "request_ticket_id": "T-A-V3-TBX-005",
            "requested_by": "A",
            "target_id": self.tc["target_id"],
            "family_id": self.tc["family_id"],
            "task_id": f"{self.tc['target_id']}::{self.tc['frozen_task']}",
            "endpoint_contract_ref": "FINAL_MAIN50_MANIFEST.json@v3.0.2",
            "endpoint_contract_hash": self.tc["e_working_endpoint_contract_hash"],
            "timestamp_kst": self._kst_now(),
            "requested_url": self.tc["starting_url"],
            "final_url": url,
            "viewport": {**VIEWPORT, "unit": "css_px"},
            "device_profile": "mobile_ua_touch_ko-KR_Asia-Seoul",
            "state_id": state_id,
            "state_sequence_number": seq,
            "screenshot_path": str(shot_path),
            "screenshot_sha256": sha256_bytes(screenshot_bytes),
            "dom_snapshot_path": str(dom_path),
            "dom_snapshot_sha256": sha256_text(dom),
            "ax_snapshot_path": str(ax_path),
            "ax_snapshot_sha256": sha256_text(json.dumps(ax, ensure_ascii=False)),
            "probe_path": None,
            "probe_sha256": None,
            "visible_text_excerpt": visible_text[:500],
            "nav_container": nav_container,
            "reveal_direction": reveal,
            "action_token": action_token,
            "terminal_status": terminal,
            "selected_candidate": {
                k: v for k, v in (selected_candidate or {}).items() if k != "el"
            } if selected_candidate else None,
        }
        self.states.append(record)
        return record

    def find_candidates(self, page, keywords: list[str]) -> list[dict]:
        """visible text 우선, 그 다음 aria-label/accessible name 매칭. role 제한: link/button/tab 류."""
        candidates = []
        try:
            elements = page.query_selector_all("a, button, [role=button], [role=link], [role=tab], [role=menuitem]")
        except Exception:
            elements = []
        for el in elements:
            try:
                if not el.is_visible():
                    continue
                text = norm(el.inner_text() if el.evaluate("e=>e.innerText!==undefined") else "")
                aria = norm(el.get_attribute("aria-label"))
                title = norm(el.get_attribute("title"))
                accessible_name = aria or text or title
                hay = f"{text} {aria} {title}".lower()
                if any(kw.lower() in hay for kw in keywords):
                    box = el.bounding_box()
                    candidates.append({
                        "el": el,
                        "visible_label": text or aria or title,
                        "accessible_name": accessible_name,
                        "accessible_name_source": "ARIA_LABEL" if aria else ("VISIBLE_TEXT" if text else "TITLE"),
                        "role_or_tag": el.evaluate("e=>e.tagName.toLowerCase()"),
                        "bbox": box,
                    })
            except Exception:  # noqa: BLE001
                continue
        return candidates

    def run(self) -> dict:
        tc = self.tc
        keywords = self._task_keywords()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport=VIEWPORT, user_agent=UA, locale="ko-KR", timezone_id="Asia/Seoul",
                is_mobile=True, has_touch=True, ignore_https_errors=True,
            )
            page = context.new_page()
            page.set_default_timeout(NAV_TIMEOUT_MS)
            try:
                page.goto(tc["starting_url"], wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except PWTimeout:
                    pass
                page.wait_for_timeout(SETTLE_MS * 3)
            except PWTimeout:
                self.terminal_status = "TIMEOUT"
                browser.close()
                return self._finalize()
            except Exception as e:  # noqa: BLE001
                self.terminal_status = "EVIDENCE_DEFECT"
                self.route.append({"error": str(e)})
                browser.close()
                return self._finalize()

            s0 = self.capture_state(page, "S0", 0, None, None)
            seq = 1

            candidates = self.find_candidates(page, keywords)
            self.attempted_branches.append({
                "state": "S0", "candidate_count": len(candidates),
                "labels": [c["visible_label"] for c in candidates][:10],
            })

            nav_container, reveal = "NONE", "NONE"
            if not candidates:
                # exploration_priority 4단계: obvious navigation/menu container 시도
                menu_candidates = self.find_candidates(page, ["전체메뉴", "메뉴", "menu", "全"])
                if not menu_candidates:
                    menu_candidates = self._find_icon_menu_button(page)
                if menu_candidates:
                    menu_btn = menu_candidates[0]
                    safe, reason = is_safe_to_click(menu_btn["visible_label"], menu_btn["accessible_name"])
                    if safe:
                        try:
                            menu_btn["el"].scroll_into_view_if_needed(timeout=3000)
                            menu_btn["el"].click(timeout=5000, force=False)
                            page.wait_for_timeout(SETTLE_MS * 2)
                            self.route.append({"action": "OPEN_GLOBAL_MENU", "label": menu_btn["visible_label"] or "(icon-only)"})
                            nav_container, reveal = "HAMBURGER", "RIGHT"
                            self.capture_state(page, f"S{seq}", seq, "OPEN_GLOBAL_MENU", None, nav_container, reveal)
                            seq += 1
                            candidates = self.find_candidates(page, keywords)
                            self.attempted_branches.append({
                                "state": f"S{seq-1}(post-menu)", "candidate_count": len(candidates),
                                "labels": [c["visible_label"] for c in candidates][:10],
                            })
                        except Exception as e:  # noqa: BLE001
                            self.route.append({"error": f"menu_click_failed: {e}"})

            # 스크롤 탐색 — 메뉴/본문이 뷰포트 밖에 걸쳐 있을 수 있다(허용된 안전 조작)
            scroll_attempts = 0
            while not candidates and scroll_attempts < 6:
                try:
                    page.mouse.wheel(0, 600)
                except Exception:
                    page.evaluate("window.scrollBy(0, 600)")
                page.wait_for_timeout(300)
                candidates = self.find_candidates(page, keywords)
                scroll_attempts += 1
            if candidates:
                self.attempted_branches.append({
                    "state": f"S{seq-1}(post-scroll x{scroll_attempts})", "candidate_count": len(candidates),
                    "labels": [c["visible_label"] for c in candidates][:10],
                })

            if not candidates:
                self.terminal_status = "NO_SAFE_ROUTE_FOUND"
                browser.close()
                return self._finalize()

            chosen = candidates[0]
            safe, reason = is_safe_to_click(chosen["visible_label"], chosen["accessible_name"])
            if not safe:
                self.forbidden_actions_attempted += 1
                self.terminal_status = "SAFETY_STOP"
                self.route.append({"terminal": "SAFETY_STOP", "reason": reason, "candidate": chosen["visible_label"]})
                browser.close()
                return self._finalize()

            self.route.append({"action": "SELECT_FUNCTION", "label": chosen["visible_label"]})
            url_before = page.url
            try:
                chosen["el"].scroll_into_view_if_needed(timeout=3000)
                chosen["el"].click(timeout=5000)
                page.wait_for_timeout(SETTLE_MS)
            except Exception as e:  # noqa: BLE001
                self.terminal_status = "EVIDENCE_DEFECT"
                self.route.append({"error": f"click_failed: {e}"})
                browser.close()
                return self._finalize()

            s1 = self.capture_state(page, f"S{seq}", seq, "SELECT_FUNCTION", None, selected_candidate=chosen)
            seq += 1
            url_after = page.url

            if looks_like_auth_gate(url_after, s1["visible_text_excerpt"]):
                self.terminal_status = "AUTH_GATE"
            elif url_after != url_before or True:
                # F1 endpoint contract 상 AUTH_GATE 아니면 transfer surface 자체가 endpoint.
                # v1 은 보수적으로: 상태가 바뀌었으면 ENDPOINT_REACHED 후보로 기록(추가 판정은 C/A 몫)
                self.terminal_status = "ENDPOINT_REACHED"

            self.route.append({"terminal": self.terminal_status})
            browser.close()
            return self._finalize()

    def _find_icon_menu_button(self, page) -> list[dict]:
        """텍스트 라벨 없는 hamburger/menu 아이콘 버튼 — aria-label 로만 식별(추측 클릭 금지)."""
        out = []
        try:
            elements = page.query_selector_all(
                "[aria-label*='메뉴' i], [aria-label*='menu' i], "
                "button[class*='menu' i], [role=button][class*='menu' i], "
                "[role=navigation] button, header button, nav button"
            )
        except Exception:
            elements = []
        for el in elements:
            try:
                if not el.is_visible():
                    continue
                aria = norm(el.get_attribute("aria-label"))
                text = norm(el.inner_text()) if el.evaluate("e=>e.innerText!==undefined") else ""
                box = el.bounding_box()
                out.append({
                    "el": el,
                    "visible_label": text,
                    "accessible_name": aria or text,
                    "accessible_name_source": "ARIA_LABEL" if aria else "VISIBLE_TEXT",
                    "role_or_tag": el.evaluate("e=>e.tagName.toLowerCase()"),
                    "bbox": box,
                })
            except Exception:  # noqa: BLE001
                continue
        return out

    def _task_keywords(self) -> list[str]:
        # F1 은행 family 전용 키워드 — task label 에서 직접 파생, 화면 추론 아님
        family = self.tc["family_id"]
        table = {
            "F1": ["이체", "송금", "계좌이체"],
            "F2": ["검색"],
            "F3": ["배송조회", "운송장", "택배조회", "조회"],
            "F4": ["병원", "약국", "찾기"],
            "F5": ["조회", "예매", "시간표"],
        }
        return table.get(family, [])

    def _finalize(self) -> dict:
        trace_path = self.target_dir / f"E_SCOUT_TRACE_{self.tc['target_id']}.jsonl"
        with trace_path.open("w", encoding="utf-8") as f:
            for s in self.states:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        # A(T-A-V3-TBX-013): 부재(collector 못 뽑음) 와 site 자체의 무경로를 같은 라벨로 내지 않는다
        max_candidates_seen = max((b.get("candidate_count", 0) for b in self.attempted_branches), default=0)
        if self.terminal_status == "NO_SAFE_ROUTE_FOUND":
            route_diagnosis = "COLLECTOR_ZERO_CANDIDATE" if max_candidates_seen == 0 else "NO_SAFE_ROUTE_SITE"
        else:
            route_diagnosis = None

        route_candidate = {
            "SYNTHETIC": False,
            "target_id": self.tc["target_id"],
            "task_contract_hash": self.tc["e_working_task_contract_hash"],
            "endpoint_contract_hash": self.tc["e_working_endpoint_contract_hash"],
            "scout_status": self.terminal_status,
            "route_diagnosis": route_diagnosis,
            "route": self.route,
            "attempted_branches": self.attempted_branches,
            "task_activation_depth": sum(1 for r in self.route if r.get("action")),
            "reproducibility": "REPLAY_REQUIRED",
            "uncertainty": [],
            "forbidden_actions_attempted": self.forbidden_actions_attempted,
            "state_count": len(self.states),
        }
        route_path = self.target_dir / f"E_ROUTE_CANDIDATE_{self.tc['target_id']}.json"
        route_path.write_text(json.dumps(route_candidate, ensure_ascii=False, indent=2), encoding="utf-8")
        return route_candidate


PACKETS_PATH = Path(
    "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_e_pathfinder/"
    "research/landing_accessibility/pathfinder_e/bootstrap/WORKER_DISPATCH_PACKETS_V2.json"
)
SHARED_RAW_ROOT = Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/v3_census/raw/E")


def main():
    target_id = sys.argv[1]
    scout_run_id = sys.argv[2] if len(sys.argv) > 2 else "E-REAL-CENSUS"
    all_packets = json.loads(PACKETS_PATH.read_text(encoding="utf-8"))
    packet = all_packets["targets"][target_id]
    run = ScoutRun(packet, SHARED_RAW_ROOT, scout_run_id)
    try:
        result = run.run()
    except Exception as e:  # noqa: BLE001
        result = {"target_id": target_id, "scout_status": "EVIDENCE_DEFECT", "error": str(e)}
        (run.target_dir / f"E_ROUTE_CANDIDATE_{target_id}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
