/* L0 raw feature probe — 02 §3 · §4 · §5 · §6.
   판정하지 않는다. 임계값을 갖지 않는다. 원시 관측값만 낸다.

   Pilot(research/refcohort/src/refcohort/probe.js)에서 **기능 단위로** 가져온 것:
     - 상대휘도/명도대비 산식, 유효 배경색 상승 탐색, 안정 selector 생성, 가시성 판정.
   가져오지 않은 것:
     - KWCAG 임계값 비교(`required`), large_text 분류, 판정 문자열.
       그것은 02 §4 가 분리하라고 한 verdict 층의 일이다.

   출력의 모든 수치는 CSS px 이며 devicePixelRatio 를 곱하지 않는다 (A1 §3.2).

   ## execution_mode 인자 (W2 · D-R0-42 · Director 지시)

   `data-region` / `data-endpoint` / `data-endpoint-reached` 세 marker 신호는 REAL_TARGET
   모드에서 **읽기 시도 자체가 일어나지 않는다** — 코드를 지우는 게 아니라 호출을
   `execution_mode === 'REAL_TARGET'` 분기로 완전히 건너뛴다. 기존 호출부(`l0_collector.py`)는
   인자를 넘기지 않으므로 `execution_mode === undefined` 가 되어 기존 동작(FIXTURE 취급)이
   그대로 유지된다 — 이 인자 추가는 후방호환이다.

   ## probe_truncation (W2 · T-B-FINDING-002 대응)

   `primary_action_candidates`/`accessible_name_sources`/`target_size`/`motion` 스캔/`contrast`
   텍스트노드/`gate_signals.visible_text` 는 전부 하드 cap 을 갖는다(성능·페이로드 상한).
   B 의 n=58 전수 재집계: 7/58 이 `primary_action_candidates` cap(200)에, 13/58 이
   `accessible_name_sources` cap(300)에 정확히 도달했고 전부 대형 커머스/포털이었다.
   cap 자체는 여기서 올리지 않는다(A 결정 사항, 재수집 필요) — 대신 각 cap 도달 여부를
   `probe_truncation` 에 남겨, 하류 판정기가 "신호 없음"과 "절단으로 못 봤을 수 있음"을
   구분할 수 있게 한다. */
(execution_mode) => {
  const VIEW_W = window.innerWidth;
  const VIEW_H = window.innerHeight;
  const REAL_TARGET_MODE = execution_mode === 'REAL_TARGET';
  const truncation = {};
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

  /* W2 · D-R0-70 — HITTABLE(기하학적 hit-test) 은 ENABLED(기능적으로 조작 가능함) 를
     함의하지 않는다. `<input disabled>`/`<button disabled>` 도 `elementFromPoint` 에는
     여전히 걸린다 — geometry 는 그대로지만 클릭이 무효다. `D-R0-02` 9상태 mask 의
     `DISABLED_OR_INERT` 를 region/endpoint 판정이 실제로 소비하려면 이 신호가 있어야
     한다(이전에는 어디에도 없었다). */
  const enabled = (el) => {
    if (!el) return false;
    if (el.disabled) return false;
    if (el.getAttribute('aria-disabled') === 'true') return false;
    if (el.closest('[inert]')) return false;
    return true;
  };

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
    const CONTRAST_CAP = 400;
    const res = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node, seen = 0, cappedExtra = false;
    while ((node = walker.nextNode())) {
      const t = T(node.nodeValue); if (t.length < 2) continue;
      const el = node.parentElement; if (!el || !visible(el)) continue;
      if (seen >= CONTRAST_CAP) { cappedExtra = true; break; }
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
    /* W2 · T-B-FINDING-002 — cap 도달 여부만 남긴다(cap 자체는 올리지 않는다, A 결정 사항). */
    truncation.contrast = { cap: CONTRAST_CAP, matched: res.length, truncated: cappedExtra };
  }

  /* ── target size raw feature (02 §4) — CSS px, DPR 곱하지 않음 ── */
  {
    const TARGET_SIZE_CAP = 300;
    const q = 'a[href],button,input:not([type=hidden]),select,textarea,'
      + '[role=button],[role=link],[role=checkbox],[role=radio],[role=tab]';
    const allTargets = [...document.querySelectorAll(q)].filter(visible);
    const ctrls = allTargets.slice(0, TARGET_SIZE_CAP);
    truncation.target_size = {
      cap: TARGET_SIZE_CAP, matched: allTargets.length, truncated: allTargets.length > TARGET_SIZE_CAP,
    };
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
    const NAME_SOURCE_CAP = 300;
    const q = 'a[href],button,input:not([type=hidden]),select,textarea,img,'
      + '[role=button],[role=link],[role=img],[role=checkbox],[role=radio],[role=tab]';
    const allNamed = [...document.querySelectorAll(q)];
    truncation.accessible_name_sources = {
      cap: NAME_SOURCE_CAP, matched: allNamed.length, truncated: allNamed.length > NAME_SOURCE_CAP,
    };
    push('accessible_name_sources', allNamed.slice(0, NAME_SOURCE_CAP).map((el) => ({
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
    const MOTION_SCAN_CAP = 3000;
    const allBodyEls = [...document.querySelectorAll('body *')];
    truncation.motion_scan = {
      cap: MOTION_SCAN_CAP, matched: allBodyEls.length, truncated: allBodyEls.length > MOTION_SCAN_CAP,
    };
    const animated = [];
    allBodyEls.slice(0, MOTION_SCAN_CAP).forEach((el) => {
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
    const PRIMARY_ACTION_CAP = 200;
    const q = 'a[href],button,input[type=submit],input[type=button],'
      + '[role=button],[role=link],[role=tab],nav a';
    const allPrimary = [...document.querySelectorAll(q)].filter(visible);
    truncation.primary_action_candidates = {
      cap: PRIMARY_ACTION_CAP, matched: allPrimary.length,
      truncated: allPrimary.length > PRIMARY_ACTION_CAP,
    };
    const cands = allPrimary.slice(0, PRIMARY_ACTION_CAP).map((el, dom_order) => {
      const b = box(el);
      let heading = null, n = el;
      for (let d = 0; d < 6 && n; d++, n = n.parentElement) {
        const h = n.querySelector ? n.querySelector('h1,h2,h3,h4,h5,h6') : null;
        if (h) { heading = T(h.textContent).slice(0, 80); break; }
      }
      // A Δ36 ④ (Δ20 이 허용한 가산적 구조 신호) — Δ9 IN 10종을 라벨 해석 없이 가르기
      // 위한 신호다. 값은 전부 DOM/ARIA 속성이거나 HTML 명세가 정한 파생이며, 문구·의미
      // 해석은 하나도 없다. 기존 키는 한 줄도 바꾸지 않는다(삭제 0).
      const tagLower = el.tagName.toLowerCase();
      const typeLower = (el.getAttribute('type') || '').toLowerCase();
      // HTML 명세: `<button>` 의 type 기본값은 submit 이고, form 소속일 때만 제출이 된다.
      // `<input type=submit|image>` 도 제출 control 이다. 라벨을 읽지 않는다.
      const inForm = !!el.closest('form');
      // `aria-controls` 는 이 control 이 **무엇을** 여닫는지에 대한 명시적 구조 링크다.
      // 대상의 역할이 nav/menu 면 메뉴 열기, 그 밖이면 disclosure(아코디언)다.
      // id 를 못 찾으면 null 이다 — 추측하지 않는다.
      let controlsRole = null, controlsIsNavLandmark = null;
      const controlsId = el.getAttribute('aria-controls');
      if (controlsId) {
        const t = document.getElementById(controlsId.split(/\s+/)[0]);
        if (t) {
          controlsRole = t.getAttribute('role') || t.tagName.toLowerCase();
          controlsIsNavLandmark =
            t.tagName.toLowerCase() === 'nav' || t.getAttribute('role') === 'navigation';
        }
      }
      const submitControl =
        (tagLower === 'input' && (typeLower === 'submit' || typeLower === 'image'))
        || (tagLower === 'button' && (typeLower === 'submit' || (typeLower === '' && inForm)));
      return {
        selector: sel(el), tag: el.tagName.toLowerCase(), role: el.getAttribute('role'),
        aria_label: el.getAttribute('aria-label'),
        visible_text: T(el.textContent).slice(0, 80) || null,
        nearby_heading: heading,
        href: el.getAttribute('href'),
        marked_primary: el.hasAttribute('data-primary-action'),
        enabled: enabled(el),
        // W2 · D-R0-61(PRECEDENCE_CONTESTED) — Stage 4 precedence #2
        // "public page primary interaction surface" 판정에 쓴다: MIN-4 로 정한 1위
        // candidate 가 list-container 소속인지(반복 카드/리스트 표면)를 알아야 경합하는
        // archetype 후보 중 실제로 페이지의 대표 표면이 어느 쪽인지 가릴 수 있다.
        in_list_container: !!el.closest('ul,ol,[role=list],[role=listbox],[role=menu],[role=feed]'),
        box: b,
        area_css_px2: b ? +(b.w * b.h).toFixed(2) : null,
        // A1 §2.6 규칙 MIN-4 / A2 §1.13 — tie-break 2차 키. 구조값이므로 NULL이 없고
        // 이 문서(프레임) 안에서 0-based 단조 증가한다. `filter(visible)` 이후의 열거
        // 순서를 그대로 쓴다 — querySelectorAll 자체가 이미 문서 순서(tree order)를
        // 보장하고, filter는 상대 순서를 보존하므로 단조성이 깨지지 않는다.
        dom_order,
        viewport_visible: intersectArea(b, viewportBox) > 0,
        hittable: hittable(el, b),
        // ── A Δ36 ④ 가산 신호 (구조값만) ────────────────────────────────────
        // `aria-haspopup` 이 있으면 이 control 은 메뉴/팝업을 연다(ARIA 명세). 어떤
        // 메뉴인지는 묻지 않는다 — nav/banner landmark 소속이면 전역, 아니면 지역이다.
        aria_haspopup: el.getAttribute('aria-haspopup'),
        // `aria-expanded` 는 있는데 `aria-haspopup` 이 없으면 disclosure(아코디언)다.
        aria_expanded: el.getAttribute('aria-expanded'),
        has_aria_controls: el.hasAttribute('aria-controls'),
        controls_role: controlsRole,
        controls_is_nav_landmark: controlsIsNavLandmark,
        input_type: el.getAttribute('type'),
        in_form: inForm,
        submit_control: submitControl,
        in_nav_landmark: !!el.closest('nav,[role=navigation],header,[role=banner]'),
        in_tablist: !!el.closest('[role=tablist]'),
        in_disclosure: tagLower === 'summary' || !!el.closest('details'),
        in_menu_container: !!el.closest('[role=menu],[role=menubar]'),
      };
    });
    push('primary_action_candidates', cands);
  }

  /* ── utility 도구 입력 위젯 (W2 rework · D-R0-67-1) — `primary_action_candidates`
     쿼리(`a[href],button,input[type=submit],input[type=button],...`)는 일반 데이터
     입력용 `<input type=text|number|...>`/`<select>`/`<textarea>` 를 잡지 않는다(제출
     버튼류만 잡는다). Branch U 의 "single-purpose tool surface" 는 버튼이 아니라 실제
     "값을 입력받는 위젯"의 존재로 판정해야 하므로 별도 신호가 필요하다. `type=search` 는
     QUERY 영역(`region_signals.search_inputs`)이 이미 다루므로 여기서는 제외한다. */
  {
    const q = 'input:not([type=hidden]):not([type=submit]):not([type=button])'
      + ':not([type=search]),select,textarea';
    push('utility_input_widgets', [...document.querySelectorAll(q)].filter(visible).map((el) => {
      const b = box(el);
      return {
        selector: sel(el), tag: el.tagName.toLowerCase(), type: el.getAttribute('type'),
        hittable: hittable(el, b), enabled: enabled(el), box: b,
      };
    }));
  }

  /* ── 반복 카드/리스트 구조 신호 (02 §6 Stage2 "repeated card/list structures") — W2 신규.
     실사이트에서 archetype 의 Region(콘텐츠 카드/상품 카드/장소 목록/스레드 목록)을
     marker 없이 판정하려면 "list-like container 안의 hittable link" 라는 구조 신호가
     필요하다. 단순 nav 링크 나열과 구분하기 위해 list container(ul/ol/[role=list] 등)
     소속 여부로만 좁힌다 — heading 근접성(`nearby_heading`)은 작은 페이지에서 거의 항상
     참이 되어 판별력이 없다(실측으로 확인). cap 을 두지 않는다(신규 신호이므로 절단 위험을
     새로 만들지 않는다). */
  {
    const LIST_CONTAINER_SEL = 'ul,ol,[role=list],[role=listbox],[role=menu],[role=feed]';
    const links = [...document.querySelectorAll('a[href],[role=link]')].filter(visible);
    const inList = links.filter((el) => el.closest(LIST_CONTAINER_SEL));
    push('repeated_structure', {
      list_container_count: document.querySelectorAll(LIST_CONTAINER_SEL).length,
      list_item_link_count: inList.length,
      hittable_list_item_link_count: inList.filter((el) => hittable(el, box(el))).length,
      // W2 · D-R0-70 — aria-disabled 링크(있다면)를 제외한 버전. 링크는 native `disabled`
      // 를 가질 수 없어 `enabled()` 는 aria-disabled/inert 만 본다.
      hittable_enabled_list_item_link_count: inList.filter(
        (el) => hittable(el, box(el)) && enabled(el)).length,
    });
  }

  /* ── family-specific 판별 신호 (W2 · D-R0-67-2) — RF-DT §4 Stage2 가 family 별로
     이미 지정한 신호를 구현한다. `repeated_structure`(list-container 소속 링크) 하나로
     Item/Place/Content/Communication 4개 archetype 을 전부 evidenced 시키면(공유 신호)
     변별력이 없다(C 진단: 36/56 동시발화, tie-break PLACE_LOOKUP 22 로 쏠림). structured
     data(JSON-LD)는 파싱 실패해도 판정하지 않는다 — 신호가 없는 것으로만 처리한다. */
  {
    const structuredDataTypes = [];
    document.querySelectorAll('script[type="application/ld+json"]').forEach((s) => {
      try {
        const data = JSON.parse(s.textContent || '{}');
        const collect = (item) => {
          if (!item || typeof item !== 'object') return;
          const t = item['@type'];
          if (t) structuredDataTypes.push(...(Array.isArray(t) ? t : [t]));
          if (Array.isArray(item['@graph'])) item['@graph'].forEach(collect);
        };
        (Array.isArray(data) ? data : [data]).forEach(collect);
      } catch (e) { /* 파싱 실패 — 신호 없음으로 처리, 판정하지 않는다 */ }
    });

    const bodyText = T(document.body.innerText || '').slice(0, 4000);
    const PRICE_PATTERN = /(₩\s?[\d,]{3,}|[\d,]{3,}\s?원)/;
    const ADDRESS_VOCAB = /(서울|경기|인천|대구|대전|광주|부산|울산|세종|제주특별자치도|[가-힣]{1,4}(시|군|구)\s|[가-힣]{1,6}(동|로|길)\s?\d|매장\s?찾기|지점\s?찾기|가까운\s?매장|주소\s?검색)/;
    const COMMUNITY_VOCAB = /(게시글|게시판|댓글\s?\d|답글|작성자|조회\s?\d|추천\s?\d|자유게시판|커뮤니티\s?홈|채팅방)/;
    const MAP_CONTROL_VOCAB = /(지도|매장\s?찾기|위치\s?검색|장소\s?검색|내\s?주변)/;

    const mapControlPresent = [...document.querySelectorAll('input,button,a')].some((el) => {
      if (!visible(el) || !enabled(el)) return false;
      const label = T(el.getAttribute('aria-label') || el.textContent
        || el.getAttribute('placeholder') || '');
      return MAP_CONTROL_VOCAB.test(label);
    });

    push('family_signals', {
      structured_data_types: [...new Set(structuredDataTypes)],
      price_pattern_present: PRICE_PATTERN.test(bodyText),
      address_vocabulary_present: ADDRESS_VOCAB.test(bodyText),
      community_vocabulary_present: COMMUNITY_VOCAB.test(bodyText),
      compose_textarea_present: [...document.querySelectorAll('textarea')].some(
        (el) => visible(el) && enabled(el)),
      map_control_present: mapControlPresent,
    });
  }

  /* ── 영역진입 control 신호 (A1 §1.1 PRESENT / HITTABLE) ──
     `[data-region]` marker 경로 — D-R0-42 · Director 지시: REAL_TARGET 모드에서는
     이 querySelectorAll 자체를 호출하지 않는다(읽기 시도 자체가 없다). FIXTURE 회귀
     스위트만 이 경로를 쓴다. 실사이트 판정은 `search_inputs`(FORM_STRUCTURE, marker
     비의존, 항상 계산)와 `repeated_structure`/`endpoint_signals`(DOM_AX_ROLE)가 맡는다. */
  {
    const regions = REAL_TARGET_MODE ? [] : [...document.querySelectorAll('[data-region]')].map((el) => {
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
        visible: visible(el), hittable: hittable(el, b), enabled: enabled(el), box: b,
      };
    });
    push('region_signals', {
      declared_regions: regions, search_inputs: searchInputs, marker_path_disabled: REAL_TARGET_MODE,
    });
  }

  /* ── endpoint / gate 원시 신호 — 판정은 L1 엔진이 archetype 별로 한다 ──
     `[data-endpoint]` · `data-endpoint-reached` marker 경로도 REAL_TARGET 모드에서
     querySelectorAll/getAttribute 호출 자체를 건너뛴다(위와 같은 이유, 같은 계약). */
  {
    const GATE_TEXT_CAP = 4000;
    const fullText = T(document.body.innerText || '');
    const text = fullText.slice(0, GATE_TEXT_CAP);
    truncation.gate_visible_text = {
      cap: GATE_TEXT_CAP, matched: fullText.length, truncated: fullText.length > GATE_TEXT_CAP,
    };
    push('endpoint_signals', {
      declared_endpoints: REAL_TARGET_MODE ? [] : [...document.querySelectorAll('[data-endpoint]')].map((el) => ({
        selector: sel(el), endpoint: el.getAttribute('data-endpoint'), visible: visible(el),
      })),
      body_endpoint_reached: REAL_TARGET_MODE ? null : document.body.getAttribute('data-endpoint-reached'),
      article_present: document.querySelectorAll('article').length,
      video_playing: [...document.querySelectorAll('video')].some((v) => !v.paused && !v.ended),
      marker_path_disabled: REAL_TARGET_MODE,
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
    /* W2 · C-BLOCKER-221347(P1) · D-R0-65(T-A-W2-CAPTCHA-001) 확정 — CAPTCHA "visible/active challenge" 신호.
       `D-R0-05` 원문: "DOM 안에 CAPTCHA 코드·문구가 있다는 사실만으로 terminal 처리하지
       않는다. 현재 chosen path 의 다음 진행을 막는 visible/active challenge 가 실제로
       나타난 순간만 terminal 로 기록한다." `captcha_iframe_count`(존재 카운트, 아래 유지)
       는 raw feature 로만 남고 이 신호가 판정을 대신한다: dialog/aria-modal 소속 +
       captcha 입력 또는 이미지 존재 + viewport 가시성을 **전부** 요구한다.
       되돌리기: `gate_classifier.classify_gate_kind`/`_gate_structural_signal_present`
       가 이 필드 대신 `captcha_iframe_count` 를 다시 참조하게 하면 이전 동작으로 돌아간다
       — 이 raw feature 블록 자체는 그대로 둬도 무해하다(소비하지 않으면 그만이다). */
    {
      const CAPTCHA_INPUT_SEL = 'input[name*=captcha i],input[id*=captcha i],'
        + 'input[aria-label*=captcha i],input[placeholder*=captcha i],'
        + 'input[placeholder*="자동입력" i],input[placeholder*="보안문자" i],'
        + 'input[aria-label*="보안문자" i],input[aria-label*="자동입력" i]';
      const CAPTCHA_IMAGE_SEL = 'img[alt*=captcha i],img[src*=captcha i],'
        + 'canvas[aria-label*=captcha i],img[alt*="보안문자" i],img[alt*="자동입력" i]';
      const dialogs = [...document.querySelectorAll(
        'dialog,[role=dialog],[role=alertdialog],[aria-modal=true]')];
      const challengeCandidates = dialogs.map((el) => {
        const hasInput = !!el.querySelector(CAPTCHA_INPUT_SEL);
        const hasImage = !!el.querySelector(CAPTCHA_IMAGE_SEL);
        const b = box(el);
        return {
          selector: sel(el),
          visible: visible(el),
          hittable: hittable(el, b),
          viewport_overlap_css_px2: intersectArea(b, viewportBox),
          has_captcha_input: hasInput,
          has_captcha_image: hasImage,
          box: b,
        };
      }).filter((c) => c.has_captcha_input || c.has_captcha_image);
      push('captcha_challenge_candidates', challengeCandidates);
    }
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

  /* W2 · T-B-FINDING-002 — cap 도달 여부의 정본. 하류(`l1_engine.detect_*`)가 "신호 없음"과
     "cap 때문에 못 봤을 수 있음"을 구분하는 데 쓴다. cap 수치 자체는 여기서 바꾸지 않는다. */
  push('probe_truncation', truncation);

  return out;
}
