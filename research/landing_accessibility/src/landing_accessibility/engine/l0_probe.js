/* L0 raw feature probe — 02 §3 · §4 · §5 · §6.
   판정하지 않는다. 임계값을 갖지 않는다. 원시 관측값만 낸다.

   Pilot(research/refcohort/src/refcohort/probe.js)에서 **기능 단위로** 가져온 것:
     - 상대휘도/명도대비 산식, 유효 배경색 상승 탐색, 안정 selector 생성, 가시성 판정.
   가져오지 않은 것:
     - KWCAG 임계값 비교(`required`), large_text 분류, 판정 문자열.
       그것은 02 §4 가 분리하라고 한 verdict 층의 일이다.

   출력의 모든 수치는 CSS px 이며 devicePixelRatio 를 곱하지 않는다 (A1 §3.2). */
() => {
  const VIEW_W = window.innerWidth;
  const VIEW_H = window.innerHeight;
  const T = (s) => (s || '').replace(/\s+/g, ' ').trim();

  const sel = (el) => {
    if (!el || el.nodeType !== 1) return null;
    const parts = [];
    let n = el, depth = 0;
    while (n && n.nodeType === 1 && depth < 8) {
      let p = n.tagName.toLowerCase();
      if (n.id) { parts.unshift(p + '#' + CSS.escape(n.id)); break; }
      const sib = n.parentElement
        ? [...n.parentElement.children].filter((c) => c.tagName === n.tagName) : [];
      if (sib.length > 1) p += ':nth-of-type(' + (sib.indexOf(n) + 1) + ')';
      parts.unshift(p); n = n.parentElement; depth++;
    }
    return parts.join('>');
  };

  const box = (el) => {
    try {
      const r = el.getBoundingClientRect();
      return { x: +r.x.toFixed(2), y: +r.y.toFixed(2), w: +r.width.toFixed(2), h: +r.height.toFixed(2) };
    } catch (e) { return null; }
  };

  const visible = (el) => {
    try {
      const s = getComputedStyle(el), r = el.getBoundingClientRect();
      return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.01
        && r.width > 0 && r.height > 0;
    } catch (e) { return false; }
  };

  const intersectArea = (a, b) => {
    if (!a || !b) return 0;
    const w = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x));
    const h = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
    return +(w * h).toFixed(2);
  };
  const viewportBox = { x: 0, y: 0, w: VIEW_W, h: VIEW_H };

  /* hit-test 최상위 대상이 그 요소(또는 그 후손)인가 — A1 §1.1 HITTABLE */
  const hittable = (el, b) => {
    if (!b || b.w <= 0 || b.h <= 0) return false;
    const cx = Math.min(Math.max(b.x + b.w / 2, 0), VIEW_W - 1);
    const cy = Math.min(Math.max(b.y + b.h / 2, 0), VIEW_H - 1);
    if (cx < 0 || cy < 0 || cx >= VIEW_W || cy >= VIEW_H) return false;
    const top = document.elementFromPoint(cx, cy);
    return !!top && (top === el || el.contains(top) || top.contains(el));
  };

  /* ── 색: pilot 의 산식을 기능 단위로 가져온다 ── */
  const parseColor = (c) => {
    const m = (c || '').match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(',').map((x) => parseFloat(x));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const effectiveBg = (el) => {
    let n = el, hasImage = false, depth = 0;
    while (n && n.nodeType === 1 && depth < 30) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') hasImage = true;
      const c = parseColor(cs.backgroundColor);
      if (c && c.a > 0.5) return { ...c, resolved: true, behindImage: hasImage };
      n = n.parentElement; depth++;
    }
    return { r: 255, g: 255, b: 255, a: 1, resolved: false, behindImage: hasImage };
  };
  const contrastRatio = (fg, bg) => {
    const L1 = lum(fg), L2 = lum(bg);
    const hi = Math.max(L1, L2), lo = Math.min(L1, L2);
    return +(((hi + 0.05) / (lo + 0.05)).toFixed(2));
  };

  const out = {
    probe_version: 'pc-fixture-1',
    collected_at: new Date().toISOString(),
    url: location.href,
    raw_features: {},
  };
  const push = (k, v) => { out.raw_features[k] = v; };

  /* ── viewport / 문서 메타 (02 §2 · A1 §6.1) ── */
  push('viewport', {
    layout_width: VIEW_W,
    layout_height: VIEW_H,
    device_pixel_ratio: window.devicePixelRatio,
    document_scroll_width: document.documentElement.scrollWidth,
    document_scroll_height: document.documentElement.scrollHeight,
    lang: document.documentElement.lang || null,
    title: document.title || null,
    final_url: location.href,
  });

  /* ── contrast raw feature (02 §4) — 임계값 비교 없음 ── */
  {
    const res = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node, seen = 0;
    while ((node = walker.nextNode()) && seen < 400) {
      const t = T(node.nodeValue); if (t.length < 2) continue;
      const el = node.parentElement; if (!el || !visible(el)) continue;
      const cs = getComputedStyle(el);
      const fg = parseColor(cs.color); if (!fg) continue;
      const bg = effectiveBg(el);
      const b = box(el);
      res.push({
        selector: sel(el),
        text: t.slice(0, 60),
        font_px: +(parseFloat(cs.fontSize) || 0).toFixed(2),
        font_weight: parseInt(cs.fontWeight, 10) || 400,
        fg_rgb: [fg.r, fg.g, fg.b], fg_alpha: fg.a,
        bg_rgb: [bg.r, bg.g, bg.b],
        bg_resolved: bg.resolved === true,
        behind_image: bg.behindImage === true,
        contrast_ratio: contrastRatio(fg, bg),
        box: b,
        in_viewport: intersectArea(b, viewportBox) > 0,
      });
      seen++;
    }
    push('contrast', res);
  }

  /* ── target size raw feature (02 §4) — CSS px, DPR 곱하지 않음 ── */
  {
    const q = 'a[href],button,input:not([type=hidden]),select,textarea,'
      + '[role=button],[role=link],[role=checkbox],[role=radio],[role=tab]';
    const ctrls = [...document.querySelectorAll(q)].filter(visible).slice(0, 300);
    const boxes = ctrls.map((el) => ({ el, b: box(el) })).filter((x) => x.b && x.b.w > 0);
    push('target_size', boxes.map(({ el, b }, i) => {
      let gap = null;
      for (let j = 0; j < boxes.length; j++) {
        if (i === j) continue;
        const o = boxes[j].b;
        const dx = Math.max(0, Math.max(b.x - (o.x + o.w), o.x - (b.x + b.w)));
        const dy = Math.max(0, Math.max(b.y - (o.y + o.h), o.y - (b.y + b.h)));
        const d = Math.sqrt(dx * dx + dy * dy);
        if (gap === null || d < gap) gap = d;
      }
      return {
        selector: sel(el), tag: el.tagName.toLowerCase(), role: el.getAttribute('role'),
        width_css_px: b.w, height_css_px: b.h,
        min_side_css_px: +Math.min(b.w, b.h).toFixed(2),
        nearest_neighbor_gap_css_px: gap === null ? null : +gap.toFixed(2),
        box: b,
      };
    }));
  }

  /* ── accessible name raw feature — 이름의 "원천"만 남기고 계산된 이름은 AX tree 가 준다 ── */
  {
    const q = 'a[href],button,input:not([type=hidden]),select,textarea,img,'
      + '[role=button],[role=link],[role=img],[role=checkbox],[role=radio],[role=tab]';
    push('accessible_name_sources', [...document.querySelectorAll(q)].slice(0, 300).map((el) => ({
      selector: sel(el), tag: el.tagName.toLowerCase(), role: el.getAttribute('role'),
      aria_label: el.getAttribute('aria-label'),
      aria_labelledby: el.getAttribute('aria-labelledby'),
      title: el.getAttribute('title'),
      alt: el.hasAttribute('alt') ? el.getAttribute('alt') : null,
      has_alt_attr: el.hasAttribute('alt'),
      value: el.tagName === 'INPUT' ? (el.getAttribute('value') || null) : null,
      visible_text: T(el.textContent).slice(0, 80) || null,
      labelled_by_for: el.id ? !!document.querySelector('label[for="' + CSS.escape(el.id) + '"]') : false,
      aria_hidden: el.getAttribute('aria-hidden'),
      visible: visible(el),
      box: box(el),
    })));
  }

  /* ── modal / overlay candidate — 02 §5 1차·2차 ── */
  {
    const seen = new Set();
    const cands = [];
    const consider = (el, sources) => {
      if (!el || seen.has(el)) return;
      const cs = getComputedStyle(el);
      const b = box(el);
      const z = parseInt(cs.zIndex, 10);
      const fixed = cs.position === 'fixed' || cs.position === 'sticky';
      const hasBackdrop = el.hasAttribute('data-backdrop')
        || /(^|[^a-z])(backdrop|dimmed|overlay|mask)([^a-z]|$)/i.test(el.className || '');
      if (!sources.length && !fixed && !(z >= 100)) return;
      seen.add(el);
      const overlap = intersectArea(b, viewportBox);
      cands.push({
        selector: sel(el),
        tag: el.tagName.toLowerCase(),
        role: el.getAttribute('role'),
        aria_modal: el.getAttribute('aria-modal'),
        candidate_sources: sources.concat(
          fixed ? ['position_' + cs.position] : [],
          Number.isFinite(z) && z >= 100 ? ['high_z_index'] : [],
          hasBackdrop ? ['backdrop_like'] : []),
        z_index: Number.isFinite(z) ? z : null,
        position: cs.position,
        pointer_events: cs.pointerEvents,
        accessible_text: T(el.textContent).slice(0, 200) || null,
        aria_label: el.getAttribute('aria-label'),
        box: b,
        visible: visible(el),
        viewport_overlap_css_px2: overlap,
        viewport_coverage: +(overlap / (VIEW_W * VIEW_H)).toFixed(4),
        hittable: hittable(el, b),
        contains_focus: el.contains(document.activeElement),
      });
    };
    document.querySelectorAll('dialog').forEach((el) => consider(el, ['dialog_element']));
    document.querySelectorAll('[role=dialog],[role=alertdialog]').forEach((el) => consider(el, ['role_dialog']));
    document.querySelectorAll('[aria-modal=true]').forEach((el) => consider(el, ['aria_modal']));
    document.querySelectorAll('body *').forEach((el) => {
      const cs = getComputedStyle(el);
      if (cs.position === 'fixed' || cs.position === 'sticky') consider(el, []);
      else if ((parseInt(cs.zIndex, 10) || 0) >= 100) consider(el, []);
    });
    push('modal_overlay_candidates', cands);
  }

  /* ── body scroll lock (02 §3 · §5) ── */
  {
    const bs = getComputedStyle(document.body);
    const hs = getComputedStyle(document.documentElement);
    push('body_scroll_lock', {
      body_overflow: bs.overflow, body_position: bs.position,
      html_overflow: hs.overflow,
      locked: bs.overflow === 'hidden' || hs.overflow === 'hidden' || bs.position === 'fixed',
    });
  }

  /* ── motion signal (02 §3) ── */
  {
    const animated = [];
    [...document.querySelectorAll('body *')].slice(0, 3000).forEach((el) => {
      const cs = getComputedStyle(el);
      const name = cs.animationName;
      if (name && name !== 'none') {
        animated.push({
          selector: sel(el), animation_name: name,
          iteration_count: cs.animationIterationCount,
          duration: cs.animationDuration, play_state: cs.animationPlayState,
          infinite: (cs.animationIterationCount || '').split(',').some((v) => v.trim() === 'infinite'),
        });
      }
    });
    push('motion', {
      animated_elements: animated.slice(0, 60),
      infinite_animation_count: animated.filter((a) => a.infinite).length,
      marquee_count: document.querySelectorAll('marquee').length,
      autoplay_media: [...document.querySelectorAll('video[autoplay],audio[autoplay]')].map((el) => ({
        selector: sel(el), tag: el.tagName.toLowerCase(),
        muted: el.muted, loop: el.hasAttribute('loop'), controls: el.hasAttribute('controls'),
      })),
      prefers_reduced_motion_supported:
        typeof window.matchMedia === 'function'
        && window.matchMedia('(prefers-reduced-motion: reduce)').media !== 'not all',
    });
  }

  /* ── primary action candidate (02 §6 · A1 §5.1) ── */
  {
    const q = 'a[href],button,input[type=submit],input[type=button],'
      + '[role=button],[role=link],[role=tab],nav a';
    const cands = [...document.querySelectorAll(q)].filter(visible).slice(0, 200).map((el) => {
      const b = box(el);
      let heading = null, n = el;
      for (let d = 0; d < 6 && n; d++, n = n.parentElement) {
        const h = n.querySelector ? n.querySelector('h1,h2,h3,h4,h5,h6') : null;
        if (h) { heading = T(h.textContent).slice(0, 80); break; }
      }
      return {
        selector: sel(el), tag: el.tagName.toLowerCase(), role: el.getAttribute('role'),
        aria_label: el.getAttribute('aria-label'),
        visible_text: T(el.textContent).slice(0, 80) || null,
        nearby_heading: heading,
        href: el.getAttribute('href'),
        marked_primary: el.hasAttribute('data-primary-action'),
        box: b,
        area_css_px2: b ? +(b.w * b.h).toFixed(2) : null,
        viewport_visible: intersectArea(b, viewportBox) > 0,
        hittable: hittable(el, b),
      };
    });
    push('primary_action_candidates', cands);
  }

  /* ── 영역진입 control 신호 (A1 §1.1 PRESENT / HITTABLE) ── */
  {
    const regions = [...document.querySelectorAll('[data-region]')].map((el) => {
      const b = box(el);
      return {
        selector: sel(el), region: el.getAttribute('data-region'),
        present: true, visible: visible(el), hittable: hittable(el, b), box: b,
      };
    });
    const searchInputs = [...document.querySelectorAll(
      'input[type=search],[role=searchbox],[role=combobox]')].map((el) => {
      const b = box(el);
      return {
        selector: sel(el), role: el.getAttribute('role') || 'searchbox',
        in_form: !!el.closest('form'),
        has_submit: !!(el.closest('form') && el.closest('form').querySelector(
          'button[type=submit],input[type=submit],button:not([type])')),
        visible: visible(el), hittable: hittable(el, b), box: b,
      };
    });
    push('region_signals', { declared_regions: regions, search_inputs: searchInputs });
  }

  /* ── endpoint / gate 원시 신호 — 판정은 L1 엔진이 archetype 별로 한다 ── */
  {
    const text = T(document.body.innerText || '').slice(0, 4000);
    push('endpoint_signals', {
      declared_endpoints: [...document.querySelectorAll('[data-endpoint]')].map((el) => ({
        selector: sel(el), endpoint: el.getAttribute('data-endpoint'), visible: visible(el),
      })),
      body_endpoint_reached: document.body.getAttribute('data-endpoint-reached'),
      article_present: document.querySelectorAll('article').length,
      video_playing: [...document.querySelectorAll('video')].some((v) => !v.paused && !v.ended),
    });
    /* gate 종류 판별의 입력. 판별 자체는 gate_classifier 가 하고, probe 는 신호만 낸다.
       `data-gate-kind` 는 fixture 의 **기대값 메타데이터**이며 판별 입력이 아니다 —
       판별기가 그것을 읽으면 조작화가 아니라 정답 열람이 된다 (Q-9). */
    const autocompleteCount = (v) => document.querySelectorAll(
      'input[autocomplete~="' + v + '"]').length;
    const CARRIERS = ['SKT', 'KT', 'LG U+', 'LGU+', '알뜰폰'];
    const SIMPLE_AUTH = ['PASS', '카카오', '네이버', '토스', '삼성패스', 'KB모바일', '페이코'];
    const optionTexts = [...document.querySelectorAll(
      'option,[role=radio],input[type=radio],button,label')].map((el) => T(
        el.textContent || el.getAttribute('aria-label') || el.value || ''));
    push('gate_signals', {
      declared_gate: document.body.getAttribute('data-gate-kind'),
      visible_text: text,
      password_input_count: document.querySelectorAll('input[type=password]').length,
      username_autocomplete_count: autocompleteCount('username'),
      tel_autocomplete_count: autocompleteCount('tel'),
      identity_number_input_count: [...document.querySelectorAll(
        'input,label')].filter((el) => /주민등록번호|생년월일|birth|rrn/i.test(
          (el.getAttribute('name') || '') + (el.getAttribute('id') || '')
          + (el.getAttribute('aria-label') || '') + T(el.textContent))).length,
      otp_input_count: [...document.querySelectorAll('input')].filter((el) => /인증번호|otp|認証/i.test(
        (el.getAttribute('name') || '') + (el.getAttribute('id') || '')
        + (el.getAttribute('aria-label') || '')
        + (el.getAttribute('placeholder') || ''))).length,
      carrier_option_count: optionTexts.filter(
        (t) => CARRIERS.some((c) => t.replace(/\s+/g, '').includes(c.replace(/\s+/g, '')))).length,
      simple_auth_provider_count: optionTexts.filter(
        (t) => SIMPLE_AUTH.some((c) => t.replace(/\s+/g, '').includes(c))).length,
      captcha_iframe_count: [...document.querySelectorAll('iframe')].filter(
        (f) => /recaptcha|hcaptcha|captcha/i.test(f.src || '')).length,
      payment_input_count: document.querySelectorAll(
        'input[autocomplete~="cc-number"],input[name*=card i]').length,
      personal_data_keyword: /주민등록번호|계좌번호|여권번호/i.test(text),
    });
  }

  /* ── dismiss control 5차 (A1 §3.2) — 조작하지 않는다 ── */
  {
    const CLOSE_WORDS = /(닫기|닫음|확인|취소|동의|건너뛰기|나중에|오늘\s*하루\s*보지\s*않기|다시\s*보지\s*않기|close|dismiss|skip|no\s*thanks|got\s*it|accept)/i;
    const PERSIST_WORDS = /(오늘\s*하루|다시\s*보지\s*않기|하루\s*동안|일주일\s*동안)/i;
    const CLOSE_GLYPH = /^[×✕✖╳xX⨯]$/;
    const perContainer = [];
    const containers = new Set();
    document.querySelectorAll('dialog,[role=dialog],[role=alertdialog],[aria-modal=true]')
      .forEach((el) => containers.add(el));
    document.querySelectorAll('body *').forEach((el) => {
      const cs = getComputedStyle(el);
      if (cs.position === 'fixed' || cs.position === 'sticky'
        || (parseInt(cs.zIndex, 10) || 0) >= 100) containers.add(el);
    });
    containers.forEach((c) => {
      const controls = [...c.querySelectorAll(
        'button,[role=button],a[href],[role=link],form[method=dialog] button')].map((el) => {
        const name = T(el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent);
        const b = box(el);
        const cs = getComputedStyle(el);
        return {
          selector: sel(el),
          accessible_name_source: name || null,
          matches_close_vocabulary: CLOSE_WORDS.test(name) || CLOSE_GLYPH.test(name),
          persistence_hint: PERSIST_WORDS.test(name),
          icon_only: !T(el.textContent) && !!(el.getAttribute('aria-label') || el.querySelector('img,svg')),
          width_css_px: b ? b.w : null, height_css_px: b ? b.h : null,
          display: cs.display, visibility: cs.visibility, opacity: cs.opacity,
          viewport_overlap_css_px2: intersectArea(b, viewportBox),
          hittable: hittable(el, b),
          box: b,
        };
      }).filter((x) => x.matches_close_vocabulary || x.icon_only);
      perContainer.push({
        container_selector: sel(c),
        is_dialog_element: c.tagName === 'DIALOG',
        has_form_method_dialog: !!c.querySelector('form[method=dialog]'),
        dismiss_control_candidates: controls,
      });
    });
    push('dismiss_control_candidates', perContainer);
  }

  return out;
}
