/* KWCAG 2.2 증거 수집 프로브 — 브라우저 컨텍스트에서 1회 실행.
   판정하지 않는다. 적용기회(opportunity)와 원시 관측값만 수집한다. */
() => {
  const T = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const sel = (el) => {
    if (!el || el.nodeType !== 1) return null;
    const parts = [];
    let n = el, depth = 0;
    while (n && n.nodeType === 1 && depth < 6) {
      let p = n.tagName.toLowerCase();
      if (n.id) { parts.unshift(p + '#' + n.id); break; }
      const sib = n.parentElement ? [...n.parentElement.children].filter(c => c.tagName === n.tagName) : [];
      if (sib.length > 1) p += ':nth-of-type(' + (sib.indexOf(n) + 1) + ')';
      parts.unshift(p); n = n.parentElement; depth++;
    }
    return parts.join('>');
  };
  const box = (el) => { try { const r = el.getBoundingClientRect(); return {x:+r.x.toFixed(2),y:+r.y.toFixed(2),w:+r.width.toFixed(2),h:+r.height.toFixed(2)}; } catch(e){ return null; } };
  const visible = (el) => {
    try { const s = getComputedStyle(el), r = el.getBoundingClientRect();
      return s.display!=='none' && s.visibility!=='hidden' && +s.opacity>0.01 && r.width>0 && r.height>0; } catch(e){ return false; }
  };
  // 시각적으로 숨겨진 skip-link 등도 "존재"로 인정해야 하므로 별도
  const inDom = (el) => !!el;

  /* ---------- 색 대비 ---------- */
  const parseColor = (c) => {
    const m = (c||'').match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(',').map(x => parseFloat(x));
    return {r:p[0], g:p[1], b:p[2], a:p.length>3?p[3]:1};
  };
  const lum = (c) => { const f=(v)=>{v/=255; return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4);};
    return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); };
  const effectiveBg = (el) => {
    let n = el, hasImage = false, depth = 0;
    while (n && n.nodeType === 1 && depth < 30) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') hasImage = true;
      const c = parseColor(cs.backgroundColor);
      if (c && c.a > 0.5) return {...c, resolved: true, behindImage: hasImage};
      n = n.parentElement; depth++;
    }
    // 불투명 배경을 못 찾았다. 캔버스 흰색으로 가정하되 추정임을 표시한다.
    return {r:255, g:255, b:255, a:1, resolved: false, behindImage: hasImage};
  };
  const contrast = (fg, bg) => { const L1=lum(fg), L2=lum(bg);
    const hi=Math.max(L1,L2), lo=Math.min(L1,L2); return +(((hi+0.05)/(lo+0.05)).toFixed(2)); };

  const out = { collected_at: new Date().toISOString(), url: location.href, opportunities: {} };
  const push = (k, arr) => { out.opportunities[k] = arr; };

  /* 1.1.1 대체 텍스트 — img/area/input[image]/svg */
  push('img_alt_ax_name', [...document.querySelectorAll('img,area,input[type=image],svg[role=img]')].map(el => ({
    selector: sel(el), tag: el.tagName.toLowerCase(),
    alt: el.hasAttribute('alt') ? el.getAttribute('alt') : null,
    has_alt_attr: el.hasAttribute('alt'),
    aria_label: el.getAttribute('aria-label'),
    aria_labelledby: el.getAttribute('aria-labelledby'),
    role: el.getAttribute('role'),
    aria_hidden: el.getAttribute('aria-hidden'),
    src: (el.getAttribute('src')||'').slice(0,200),
    visible: visible(el), box: box(el),
    decorative_candidate: el.getAttribute('alt') === '' || el.getAttribute('role') === 'presentation' || el.getAttribute('aria-hidden') === 'true'
  })));

  /* 1.2.1 자막 — video/audio */
  push('media_track', [...document.querySelectorAll('video,audio')].map(el => ({
    selector: sel(el), tag: el.tagName.toLowerCase(),
    tracks: [...el.querySelectorAll('track')].map(t => ({kind:t.kind, srclang:t.srclang, label:t.label})),
    has_caption_track: !!el.querySelector('track[kind=captions],track[kind=subtitles]'),
    autoplay: el.hasAttribute('autoplay'), muted: el.muted, controls: el.hasAttribute('controls'),
    duration_attr: el.getAttribute('duration')
  })));
  push('media_embed', [...document.querySelectorAll('iframe')].filter(f => /youtube|vimeo|kakao|naver.*(tv|video)|player/i.test(f.src||'')).map(f => ({
    selector: sel(f), src: (f.src||'').slice(0,200), title: f.getAttribute('title')
  })));

  /* 1.3.1 표의 구성 */
  push('table_structure', [...document.querySelectorAll('table')].map(el => {
    const rows = el.rows ? el.rows.length : 0;
    const ths = [...el.querySelectorAll('th')];
    return { selector: sel(el), rows, cols: el.rows && el.rows[0] ? el.rows[0].cells.length : 0,
      has_caption: !!el.querySelector('caption'), caption: T(el.querySelector('caption')?.textContent),
      th_count: ths.length, th_with_scope: ths.filter(t => t.hasAttribute('scope')).length,
      th_with_id: ths.filter(t => t.id).length,
      td_with_headers: [...el.querySelectorAll('td')].filter(t => t.hasAttribute('headers')).length,
      summary: el.getAttribute('summary'),
      role: el.getAttribute('role'),
      layout_candidate: ths.length === 0 && rows > 0, visible: visible(el) };
  }));

  /* 1.3.2 선형구조 — DOM 순서 vs 시각 좌표 순서 */
  {
    const els = [...document.querySelectorAll('h1,h2,h3,h4,p,li,button,a[href],input,section,article')].filter(visible).slice(0, 300);
    const withPos = els.map((el, i) => ({ i, b: box(el), s: sel(el) })).filter(x => x.b);
    const visualOrder = [...withPos].sort((a, b) => (a.b.y - b.b.y) || (a.b.x - b.b.x));
    let inversions = 0;
    for (let i = 1; i < visualOrder.length; i++) if (visualOrder[i].i < visualOrder[i-1].i) inversions++;
    push('dom_visual_order', [{ sampled: withPos.length, order_inversions: inversions,
      inversion_rate: withPos.length > 1 ? +(inversions / (withPos.length - 1)).toFixed(4) : null }]);
  }

  /* 1.4.2 자동 재생 */
  push('autoplay_media', [...document.querySelectorAll('video[autoplay],audio[autoplay]')].map(el => ({
    selector: sel(el), tag: el.tagName.toLowerCase(), muted: el.muted, loop: el.hasAttribute('loop'),
    controls: el.hasAttribute('controls'), duration: isFinite(el.duration) ? el.duration : null
  })));

  /* 1.4.3 명도 대비 — 보이는 텍스트 노드 */
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
      const fpx = parseFloat(cs.fontSize) || 16;
      const bold = (parseInt(cs.fontWeight,10) || 400) >= 700;
      const large = fpx >= 24 || (bold && fpx >= 18.66);
      const b = box(el);
      const offscreen = !b || b.y + b.h < 0 || b.x + b.w < 0 || b.x > (window.innerWidth || 390) + 2000;
      res.push({ selector: sel(el), text: t.slice(0,60), font_px: +fpx.toFixed(1), bold, large_text: large,
        fg: [fg.r,fg.g,fg.b], bg: [bg.r,bg.g,bg.b], ratio: contrast(fg,bg),
        required: large ? 3.0 : 4.5, box: b,
        bg_resolved: bg.resolved === true, behind_image: bg.behindImage === true,
        fg_alpha: fg.a, offscreen });
      seen++;
    }
    push('contrast_ratio', res);
  }

  /* 2.1.1 / 2.1.2 키보드 */
  {
    const interactive = [...document.querySelectorAll('a[href],button,input,select,textarea,[tabindex],[role=button],[role=link],[onclick]')];
    push('keyboard_operable', interactive.filter(visible).slice(0,300).map(el => ({
      selector: sel(el), tag: el.tagName.toLowerCase(), role: el.getAttribute('role'),
      tabindex: el.getAttribute('tabindex'),
      natively_focusable: /^(a|button|input|select|textarea)$/.test(el.tagName.toLowerCase()) && !(el.tagName==='A' && !el.hasAttribute('href')),
      has_href: el.hasAttribute('href'), disabled: el.hasAttribute('disabled'),
      onclick_only: !!el.getAttribute('onclick') && !/^(a|button|input|select|textarea)$/.test(el.tagName.toLowerCase()) && !el.hasAttribute('tabindex'),
      negative_tabindex: el.getAttribute('tabindex') !== null && parseInt(el.getAttribute('tabindex'),10) < 0,
      positive_tabindex: el.getAttribute('tabindex') !== null && parseInt(el.getAttribute('tabindex'),10) > 0
    })));
  }

  /* 2.1.3 조작 가능 — target size (CSS px) + 인접 간격 */
  {
    const ctrls = [...document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea,[role=button],[role=link],[role=checkbox],[role=radio],[role=tab]')].filter(visible).slice(0,300);
    const boxes = ctrls.map(el => ({ el, b: box(el) })).filter(x => x.b && x.b.w > 0);
    const res = boxes.map(({el,b}, i) => {
      let gap = null;
      for (let j = 0; j < boxes.length; j++) {
        if (i === j) continue; const o = boxes[j].b;
        const dx = Math.max(0, Math.max(b.x - (o.x + o.w), o.x - (b.x + b.w)));
        const dy = Math.max(0, Math.max(b.y - (o.y + o.h), o.y - (b.y + b.h)));
        const d = Math.sqrt(dx*dx + dy*dy);
        if (gap === null || d < gap) gap = d;
      }
      return { selector: sel(el), tag: el.tagName.toLowerCase(), role: el.getAttribute('role'),
        width_css_px: b.w, height_css_px: b.h, min_side: +Math.min(b.w,b.h).toFixed(2),
        nearest_neighbor_gap_css_px: gap === null ? null : +gap.toFixed(2),
        inline_in_text: el.tagName === 'A' && el.parentElement && /^(p|li|span|td|div)$/i.test(el.parentElement.tagName) && T(el.parentElement.textContent).length > T(el.textContent).length + 10,
        box: b };
    });
    push('target_size', res);
  }

  /* 2.1.4 문자 단축키 */
  push('accesskey', [...document.querySelectorAll('[accesskey]')].map(el => ({
    selector: sel(el), accesskey: el.getAttribute('accesskey'), tag: el.tagName.toLowerCase() })));

  /* 2.2.1 응답시간 조절 */
  push('meta_refresh_timeout', [...document.querySelectorAll('meta[http-equiv]')].filter(m => /refresh/i.test(m.getAttribute('http-equiv')||'')).map(m => ({
    content: m.getAttribute('content'), seconds: parseInt((m.getAttribute('content')||'').split(/[;,]/)[0], 10) })));

  /* 2.2.2 정지 기능 — 자동 움직임 */
  {
    const moving = [];
    [...document.querySelectorAll('*')].slice(0, 2000).forEach(el => {
      if (!visible(el)) return;
      const cs = getComputedStyle(el);
      const anim = cs.animationName && cs.animationName !== 'none';
      const iter = cs.animationIterationCount;
      if (anim && (iter === 'infinite' || parseFloat(iter) > 3)) {
        const nm = String(cs.animationName || '');
        const r = el.getBoundingClientRect();
        moving.push({ selector: sel(el), animation: nm, iteration: iter, duration: cs.animationDuration,
          // 로딩 인디케이터·스크롤 유도 등 정보를 전달하지 않는 장식은 2.2.2 적용 대상이 아니다
          loader_like: /spin|load|rotat|dash|circle|pulse|progress|skeleton|shimmer/i.test(nm),
          scroll_hint_like: /scroll|chevron|arrow|down|mouse|swipe/i.test(nm),
          role: el.getAttribute('role'), aria_hidden: el.getAttribute('aria-hidden'),
          text_len: T(el.textContent).length,
          area: Math.round((r.width || 0) * (r.height || 0)),
          tag: el.tagName.toLowerCase() });
      }
    });
    const marquee = [...document.querySelectorAll('marquee')].map(el => ({ selector: sel(el), animation: 'marquee', iteration: 'infinite' }));
    push('autoplay_motion_control', [...moving.slice(0,50), ...marquee]);
  }

  /* 2.4.1 반복 영역 건너뛰기 */
  {
    const anchors = [...document.querySelectorAll('a[href^="#"]')].slice(0, 40);
    const first = anchors.slice(0, 5).map(a => {
      const href = a.getAttribute('href');
      const target = href.length > 1 ? document.getElementById(decodeURIComponent(href.slice(1))) || document.querySelector('[name="' + CSS.escape(decodeURIComponent(href.slice(1))) + '"]') : null;
      return { selector: sel(a), href, text: T(a.textContent) || T(a.getAttribute('title')) || T(a.getAttribute('aria-label')),
        target_exists: !!target, dom_index: [...document.querySelectorAll('a')].indexOf(a) };
    });
    const skipPattern = /본문|바로가기|건너뛰|skip|content|main|메뉴/i;
    push('skip_navigation', first.map(x => ({ ...x, looks_like_skip: skipPattern.test(x.text || '') || skipPattern.test(x.href) })));
    push('landmark', [{ main: document.querySelectorAll('main,[role=main]').length,
      nav: document.querySelectorAll('nav,[role=navigation]').length,
      banner: document.querySelectorAll('header,[role=banner]').length,
      contentinfo: document.querySelectorAll('footer,[role=contentinfo]').length }]);
  }

  /* 2.4.2 제목 제공 */
  push('page_frame_title', [{
    title: T(document.title), title_len: T(document.title).length,
    h1_count: document.querySelectorAll('h1').length,
    h1_texts: [...document.querySelectorAll('h1')].slice(0,5).map(h => T(h.textContent)),
    heading_sequence: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].slice(0,60).map(h => +h.tagName[1]),
    frames: [...document.querySelectorAll('iframe,frame')].map(f => ({ selector: sel(f), title: f.getAttribute('title'), src: (f.getAttribute('src')||'').slice(0,120) }))
  }]);

  /* 2.4.3 적절한 링크 텍스트 */
  push('link_text', [...document.querySelectorAll('a[href]')].filter(visible).slice(0,300).map(el => ({
    selector: sel(el), text: T(el.textContent), aria_label: el.getAttribute('aria-label'),
    title: el.getAttribute('title'), href: (el.getAttribute('href')||'').slice(0,150),
    img_alt_inside: [...el.querySelectorAll('img')].map(i => i.getAttribute('alt')),
    target_blank: el.getAttribute('target') === '_blank',
    ambiguous: /^(여기|자세히|더보기|클릭|바로가기|more|click here|read more|link|상세)$/i.test(T(el.textContent)),
    empty_name: !T(el.textContent) && !el.getAttribute('aria-label') && !el.getAttribute('title') && ![...el.querySelectorAll('img')].some(i => T(i.getAttribute('alt')))
  })));

  /* 2.5.3 레이블과 네임 */
  push('label_in_name', [...document.querySelectorAll('button,a[href],[role=button],[role=link],input[type=submit],input[type=button]')].filter(visible).slice(0,300).map(el => {
    const visualText = T(el.tagName === 'INPUT' ? (el.value || '') : el.textContent);
    const accName = T(el.getAttribute('aria-label') || '');
    return { selector: sel(el), visual_text: visualText, aria_label: accName || null,
      has_both: !!(visualText && accName),
      label_contained: !!(visualText && accName) ? accName.replace(/\s/g,'').includes(visualText.replace(/\s/g,'')) : null };
  }).filter(x => x.has_both));

  /* 2.5.4 동작기반 작동 */
  push('motion_actuation', [{
    devicemotion_listener: !!(window.ondevicemotion),
    deviceorientation_listener: !!(window.ondeviceorientation),
    inline_motion_attr: document.querySelectorAll('[ondevicemotion],[ondeviceorientation]').length
  }]);

  /* 3.1.1 기본 언어 */
  push('html_lang', [{ lang: document.documentElement.getAttribute('lang'),
    xml_lang: document.documentElement.getAttribute('xml:lang'),
    valid: /^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$/.test(document.documentElement.getAttribute('lang') || ''),
    lang_changes: [...document.querySelectorAll('[lang]')].length - 1 }]);

  /* 3.2.1 사용자 요구에 따른 실행 */
  push('on_focus_change', [...document.querySelectorAll('[onfocus],[onchange],select[onchange]')].slice(0,60).map(el => ({
    selector: sel(el), tag: el.tagName.toLowerCase(),
    onfocus: (el.getAttribute('onfocus')||'').slice(0,120),
    onchange: (el.getAttribute('onchange')||'').slice(0,120),
    context_change_hint: /location|submit|open|href|window\./i.test((el.getAttribute('onfocus')||'') + (el.getAttribute('onchange')||''))
  })));

  /* 3.2.2 찾기 쉬운 도움 정보 */
  push('help_mechanism', [{
    help_links: [...document.querySelectorAll('a[href]')].filter(a => /도움말|고객센터|문의|help|contact|faq|자주\s*묻는/i.test(T(a.textContent) + (a.getAttribute('href')||''))).slice(0,10).map(a => ({ text: T(a.textContent), href: (a.getAttribute('href')||'').slice(0,120) }))
  }]);

  /* 3.3.2 레이블 제공 */
  push('form_label', [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]),select,textarea')].filter(visible).slice(0,200).map(el => {
    const id = el.id;
    const labelFor = id ? document.querySelector('label[for="' + CSS.escape(id) + '"]') : null;
    const wrap = el.closest('label');
    return { selector: sel(el), type: el.getAttribute('type') || el.tagName.toLowerCase(),
      id: id || null, has_label_for: !!labelFor, label_for_text: T(labelFor?.textContent),
      wrapped_in_label: !!wrap, wrap_text: T(wrap?.textContent),
      aria_label: el.getAttribute('aria-label'), aria_labelledby: el.getAttribute('aria-labelledby'),
      title: el.getAttribute('title'), placeholder: el.getAttribute('placeholder'),
      required: el.hasAttribute('required'),
      any_programmatic_label: !!(labelFor || wrap || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby')) };
  }));

  /* 3.3.3 접근 가능한 인증 */
  push('accessible_auth', [{
    captcha_iframe: [...document.querySelectorAll('iframe')].filter(f => /recaptcha|hcaptcha|captcha/i.test(f.src||'')).length,
    captcha_img: [...document.querySelectorAll('img')].filter(i => /captcha|보안문자/i.test((i.src||'') + (i.alt||''))).length,
    password_fields: document.querySelectorAll('input[type=password]').length,
    password_autocomplete_off: [...document.querySelectorAll('input[type=password]')].filter(i => /off|new-password/.test(i.getAttribute('autocomplete')||'')).length
  }]);

  /* 3.3.4 반복 입력 정보 */
  push('autocomplete', [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button])')].filter(visible).slice(0,120).map(el => ({
    selector: sel(el), type: el.getAttribute('type') || 'text', name: el.getAttribute('name'),
    autocomplete: el.getAttribute('autocomplete'),
    identity_field_hint: /name|tel|phone|email|mail|addr|zip|post|birth|card|이름|전화|주소|우편|생년/i.test((el.getAttribute('name')||'') + (el.id||'') + (el.getAttribute('placeholder')||''))
  })));

  /* 4.1.1 마크업 오류 방지 */
  {
    const ids = [...document.querySelectorAll('[id]')].map(e => e.id);
    const dupIds = ids.filter((v, i, a) => v && a.indexOf(v) !== i);
    push('markup_validity', [{
      total_elements: document.querySelectorAll('*').length,
      duplicate_ids: [...new Set(dupIds)].slice(0,50), duplicate_id_count: new Set(dupIds).size,
      nested_interactive: [...document.querySelectorAll('a a, button button, a button, button a')].length,
      li_outside_list: [...document.querySelectorAll('li')].filter(li => !/^(ul|ol|menu)$/i.test(li.parentElement?.tagName||'')).length,
      td_outside_table: [...document.querySelectorAll('td,th')].filter(td => !td.closest('table')).length,
      doctype: document.doctype ? document.doctype.name : null
    }]);
  }

  /* 4.2.1 웹앱 접근성 (ARIA 유효성) */
  {
    const VALID_ROLES = new Set(['alert','alertdialog','application','article','banner','button','cell','checkbox','columnheader','combobox','complementary','contentinfo','definition','dialog','directory','document','feed','figure','form','grid','gridcell','group','heading','img','link','list','listbox','listitem','log','main','marquee','math','menu','menubar','menuitem','menuitemcheckbox','menuitemradio','navigation','none','note','option','presentation','progressbar','radio','radiogroup','region','row','rowgroup','rowheader','scrollbar','search','searchbox','separator','slider','spinbutton','status','switch','tab','table','tablist','tabpanel','term','textbox','timer','toolbar','tooltip','tree','treegrid','treeitem']);
    const roleEls = [...document.querySelectorAll('[role]')];
    const bad = roleEls.filter(e => !VALID_ROLES.has((e.getAttribute('role')||'').trim().toLowerCase()));
    const refAttrs = ['aria-labelledby','aria-describedby','aria-controls','aria-owns'];
    const broken = [];
    refAttrs.forEach(a => {
      document.querySelectorAll('[' + a + ']').forEach(e => {
        (e.getAttribute(a)||'').split(/\s+/).filter(Boolean).forEach(idref => {
          if (!document.getElementById(idref)) broken.push({ selector: sel(e), attr: a, idref });
        });
      });
    });
    push('aria_validity', [{
      role_count: roleEls.length,
      invalid_roles: bad.slice(0,40).map(e => ({ selector: sel(e), role: e.getAttribute('role') })),
      invalid_role_count: bad.length,
      broken_aria_refs: broken.slice(0,40), broken_aria_ref_count: broken.length,
      aria_hidden_focusable: [...document.querySelectorAll('[aria-hidden=true]')].filter(e => e.querySelector('a[href],button,input,select,textarea,[tabindex]')).length
    }]);
  }

  /* 게이트 경계 탐지 — 로그인/결제/본인확인 (관측 중단 판정용) */
  {
    const bodyText = T(document.body ? document.body.innerText : '').slice(0, 8000);
    push('gate_signal', [{
      login_form: document.querySelectorAll('input[type=password]').length > 0,
      login_keyword: /로그인|Log\s?in|Sign\s?in|아이디\s*입력/i.test(bodyText),
      identity_keyword: /본인\s*확인|본인인증|휴대폰\s*인증|공동인증서|간편인증/i.test(bodyText),
      payment_keyword: /결제|카드번호|payment|checkout/i.test(bodyText),
      captcha_keyword: /보안문자|캡차|captcha/i.test(bodyText),
      personal_data_keyword: /주민등록번호|개인정보\s*수집|주민번호/i.test(bodyText)
    }]);
  }

  /* 공개 랜딩/과업 진입 관측 */
  push('page_signal', [{
    text_length: T(document.body ? document.body.innerText : '').length,
    visible_link_count: [...document.querySelectorAll('a[href]')].filter(visible).length,
    visible_control_count: [...document.querySelectorAll('button,input,select,textarea')].filter(visible).length,
    search_input: document.querySelectorAll('input[type=search],input[name*=search i],input[id*=search i],input[placeholder*="검색"]').length,
    body_text_head: T(document.body ? document.body.innerText : '').slice(0, 400)
  }]);

  return out;
}
