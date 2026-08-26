() => {
  function bbox(el) {
    const r = el.getBoundingClientRect();
    return { x: r.x, y: r.y, width: r.width, height: r.height };
  }
  function isVisible(el) {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || parseFloat(cs.opacity) === 0) {
      return false;
    }
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  function accessibleName(el) {
    return (
      el.getAttribute("aria-label") ||
      (el.textContent || "").trim().slice(0, 120) ||
      el.getAttribute("alt") ||
      el.getAttribute("title") ||
      null
    );
  }

  // contrast raw feature — 판정하지 않는다(02 §4). WCAG relative luminance 공식으로
  // ratio 만 계산해서 저장하고, PASS/FAIL 은 이 레인 밖(실제 KWCAG 판정기)의 책임이다.
  function parseRgb(str) {
    const m = (str || "").match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const parts = m[1].split(",").map((s) => parseFloat(s.trim()));
    if (parts.length < 3 || parts.some((n) => Number.isNaN(n))) return null;
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  }
  function relLuminance(rgb) {
    const chan = [rgb.r, rgb.g, rgb.b].map((c) => {
      const v = c / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2];
  }
  function effectiveBackground(el) {
    let cur = el;
    for (let i = 0; i < 8 && cur; i++) {
      const bg = parseRgb(getComputedStyle(cur).backgroundColor);
      if (bg && bg.a > 0) return bg;
      cur = cur.parentElement;
    }
    return { r: 255, g: 255, b: 255, a: 1 }; // 끝까지 못 찾으면 흰 배경 가정(raw feature 한계 명시)
  }
  function contrastRatio(el) {
    const fg = parseRgb(getComputedStyle(el).color);
    if (!fg) return null;
    const bg = effectiveBackground(el);
    const l1 = relLuminance(fg);
    const l2 = relLuminance(bg);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return Math.round(((lighter + 0.05) / (darker + 0.05)) * 100) / 100;
  }

  const interactive = Array.from(
    document.querySelectorAll(
      "a[href], button, input, select, textarea, [role=button], [role=link], [role=tab]"
    )
  ).map((el) => {
    const b = bbox(el);
    return {
      tag: el.tagName.toLowerCase(),
      role: el.getAttribute("role") || null,
      accessible_name: accessibleName(el),
      href: el.getAttribute("href") || null,
      bbox: b,
      visible: isVisible(el),
      target_size_ok: b.width >= 24 && b.height >= 24,
      contrast_ratio: contrastRatio(el),
      is_primary_action:
        el.hasAttribute("data-primary-action") || el.classList.contains("primary-action"),
    };
  });

  const DISMISS_SELECTOR = '[aria-label*="close" i], [aria-label*="닫기"], .close, .dismiss';

  const overlayCandidates = Array.from(
    document.querySelectorAll("dialog, [role=dialog], [aria-modal=true], .overlay, .modal, .popup")
  ).map((el) => {
    const cs = getComputedStyle(el);
    const b = bbox(el);
    const dismissEl = el.querySelector(DISMISS_SELECTOR);
    const dismissBbox = dismissEl ? bbox(dismissEl) : null;
    return {
      ref: el.id || el.className || el.tagName.toLowerCase(),
      bbox: b,
      is_dialog_tag: el.tagName.toLowerCase() === "dialog",
      role_dialog: el.getAttribute("role") === "dialog",
      aria_modal: el.getAttribute("aria-modal") === "true",
      is_fixed_or_sticky: cs.position === "fixed" || cs.position === "sticky",
      high_z_index: (parseInt(cs.zIndex, 10) || 0) > 100,
      accessible_name: accessibleName(el),
      dom_text_sample: (el.textContent || "").trim().slice(0, 300),
      dismiss_control_present: !!dismissEl,
      dismiss_control_visible: !!dismissEl && isVisible(dismissEl),
      dismiss_control_accessible_name: dismissEl ? accessibleName(dismissEl) : null,
      dismiss_control_bbox: dismissBbox,
      dismiss_control_target_size_ok: !!(dismissBbox && dismissBbox.width >= 24 && dismissBbox.height >= 24),
      dismiss_control_contrast_ratio: dismissEl ? contrastRatio(dismissEl) : null,
    };
  });

  const bodyScrollLocked =
    getComputedStyle(document.body).overflow === "hidden" ||
    document.documentElement.style.overflow === "hidden";

  // gate.py 오탐 방지 핵심: landmark 텍스트는 main/form/dialog 근처로만 한정한다.
  // footer 등 본문 전체를 넣지 않는다 (Pilot 감사 gate-detection-false-negative 재발 방지).
  const landmarkEls = Array.from(document.querySelectorAll("main, form, [role=dialog], [role=main]"));
  const landmarkText = landmarkEls
    .map((e) => e.textContent || "")
    .join(" ")
    .slice(0, 4000);

  const formActions = Array.from(document.querySelectorAll("form")).map(
    (f) => f.getAttribute("action") || ""
  );

  const animatedElements = Array.from(
    document.querySelectorAll("video[autoplay], audio[autoplay], [class*=carousel], [class*=slider], marquee")
  ).map((el) => ({ tag: el.tagName.toLowerCase(), autoplay: el.hasAttribute("autoplay") }));

  const endpointMarker = document.querySelector('[data-endpoint="true"]');

  return {
    page_title: document.title || "",
    interactive_elements: interactive,
    overlay_candidates: overlayCandidates,
    body_scroll_locked: bodyScrollLocked,
    landmark_text: landmarkText,
    form_actions: formActions,
    has_password_input: !!document.querySelector('input[type="password"]'),
    animated_elements: animatedElements,
    is_function_endpoint: !!(endpointMarker && isVisible(endpointMarker)),
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      device_pixel_ratio: window.devicePixelRatio || 1,
    },
    page_scroll_height: document.documentElement.scrollHeight,
    page_scroll_top: window.scrollY,
  };
};
