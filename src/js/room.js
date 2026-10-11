/* pinkal.art — the viewing room (<dialog class="room" id="room">).
   ES2020 module, import()ed by site.js on first use.
   export default open(list, index, opener, opts?)
     list    works from #room-data (the page's list), index the work to show,
     opener  the element that receives focus again on close,
     opts    { share, toast } helpers from site.js; { fromHistory } when a
             popstate re-opens the room (no new history entry then). */

const doc = document, root = doc.documentElement;
const $ = (s, c = doc) => c.querySelector(s);
const $$ = (s, c = doc) => [...c.querySelectorAll(s)];
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const abs = u => new URL(u, location.href).href;

// Durations come from the CSS tokens (0 ms under reduced motion); fallbacks for a page without them.
function ms(token, dflt) {
  if (reduced()) return 0;
  const v = getComputedStyle(root).getPropertyValue(token).trim();
  if (!v) return dflt;
  const n = parseFloat(v); return isNaN(n) ? dflt : /ms$/.test(v) ? n : n * 1000;
}

// AVIF support: assume yes, let a tiny probe correct it; a failing <img> also falls back to the JPEG set.
let AVIF = true;
{
  const p = new Image();
  p.onload = () => { AVIF = p.width > 0; }; p.onerror = () => { AVIF = false; };
  p.src = 'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADybWV0YQAAAAAAAAAoaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAGxpYmF2aWYAAAAADnBpdG0AAAAAAAEAAAAeaWxvYwAAAABEAAABAAEAAAABAAABGgAAAB0AAAAoaWluZgAAAAAAAQAAABppbmZlAgAAAAABAABhdjAxQ29sb3IAAAAAamlwcnAAAABLaXBjbwAAABRpc3BlAAAAAAAAAAIAAAACAAAAEHBpeGkAAAAAAwgICAAAAAxhdjFDgQ0MAAAAABNjb2xybmNseAACAAIAAYAAAAAXaXBtYQAAAAAAAAABAAEEAQKDBAAAACVtZGF0EgAKCBgANogQEAwgMg8f8D///8WfhwB8+ErK42A=';
}

let dlg = null, E = {}, S = {}, H = {};      // dialog, elements, strings, helpers
let list = [], i = 0, opener = null, base = null, viaPop = false;
let zoom = null, play = null, swipe = null, peek = null, seq = 0;
const pointers = new Map();
let pinch = null, lastTap = 0;

const fmt = (s, o) => s.replace(/\{(\w+)\}/g, (_, k) => o[k] ?? '');
const cur = () => list[i];
const zoomable = w => !!(w.zoom && w.zoomSrc);
function toastFn(text) {
  if (H.toast) return H.toast(text);
  const t = doc.createElement('div'); t.className = 'toast'; t.setAttribute('role', 'status'); t.textContent = text;
  doc.body.append(t); setTimeout(() => t.remove(), 2500);
}

function label(btn, text) {
  if (!btn || !text) return;
  btn.setAttribute('aria-label', text);
  const t = btn.querySelector('[data-text]');
  if (t) t.textContent = text; else if (!btn.children.length) btn.textContent = text;
}

/* ---------- geometry ---------- */

function stageBox() {
  const r = E.stage.getBoundingClientRect();
  return r.width && r.height ? r : { width: innerWidth - (innerWidth >= 1024 ? 128 : 0), height: innerHeight - 112, left: 0, top: 0 };
}
const fitW = ar => { const b = stageBox(); return Math.min(b.width, b.height * ar); };
const sizes = ar => Math.round(fitW(ar)) + 'px';

/* ---------- image loading ---------- */

function srcset(w) { return (AVIF && w.avif) || w.jpg || ''; }

function loadImage(w, cross) {
  const id = ++seq, img = E.img, wrap = E.wrap;
  let ghost = null;
  if (cross && img.naturalWidth) {                 // slideshow: the old picture stays until the new one is decoded
    ghost = img.cloneNode(); ghost.className = 'room__ghost'; ghost.alt = ''; ghost.setAttribute('aria-hidden', 'true');
    ghost.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none;opacity:1';
    wrap.append(ghost);
  }
  wrap.classList.remove('is-loaded', 'is-error');
  wrap.style.backgroundImage = w.lqip ? `url("${w.lqip}")` : '';
  wrap.style.setProperty('--ar', w.ar);
  img.alt = w.alt || ''; img.width = w.w; img.height = w.h;
  img.sizes = sizes(w.ar); img.srcset = srcset(w); if (w.fallback) img.src = w.fallback; else img.removeAttribute('src');
  const done = ok => {
    if (id !== seq) { ghost?.remove(); return; }
    wrap.classList.add(ok ? 'is-loaded' : 'is-error');
    const d = cross ? ms('--d-4', 500) : ms('--d-2', 200);
    if (d) img.animate([{ opacity: 0 }, { opacity: 1 }], { duration: d, easing: 'ease-out' });
    if (ghost) {
      if (d) ghost.animate([{ opacity: 1 }, { opacity: 0 }], { duration: d, easing: 'ease-in-out', fill: 'forwards' }).onfinish = () => ghost.remove();
      else ghost.remove();
    }
  };
  const attempt = () => img.decode().then(() => done(true), () => {
    if (id !== seq) return;
    if (AVIF && w.jpg && img.srcset !== w.jpg) { AVIF = false; img.srcset = w.jpg; attempt(); } // format fallback
    else done(img.naturalWidth > 0);
  });
  attempt();
}

const kept = [];
function preload(k) {
  const w = list[k]; if (!w) return;
  const im = new Image(); im.sizes = sizes(w.ar); im.srcset = srcset(w); if (w.fallback) im.src = w.fallback;
  kept.push(im); if (kept.length > 4) kept.shift();
}

/* ---------- rendering ---------- */

function titleFor(w) {
  const t = base?.title || doc.title, cut = Math.max(t.lastIndexOf(' — '), t.lastIndexOf(' – '));
  return `${w.no} · ${w.title || w.subject}${cut > 0 ? t.slice(cut) : ''}`;
}

function render(k, o = {}) {
  i = k;
  const w = cur(), n = list.length, name = w.title || w.subject;
  unzoom(true); clearPeek(); E.wrap.style.transform = '';
  const counter = fmt(S.counter || '{i} / {n}', { i: i + 1, n });
  E.counter.textContent = counter;
  E.no.textContent = w.no; E.title.textContent = name;
  E.fig.setAttribute('aria-label', [S.painting, w.no, name, counter].filter(Boolean).join(', '));
  dlg.style.setProperty('--art-deep', w.deep || ''); dlg.style.setProperty('--art-wall', w.wall || ''); dlg.style.setProperty('--ar', w.ar);
  E.prev.disabled = i === 0; E.next.disabled = i === n - 1;
  E.play.hidden = n < 2; E.zoom.hidden = !zoomable(w); E.full.hidden = !doc.fullscreenEnabled;
  E.ask.href = w.ask || '#'; E.open.href = w.url; if (w.alt_url && E.lang) E.lang.href = w.alt_url;
  doc.title = titleFor(w);
  loadImage(w, o.cross);
  preload(i + 1); preload(i - 1);
}

function go(k, o = {}) {
  if (k < 0 || k >= list.length || k === i) return;
  render(k, o);
  history.replaceState({ room: cur().id }, '', cur().url);
}

/* ---------- open / close / history ---------- */

export default function open(newList, index, newOpener, opts = {}) {
  if (!init()) { location.href = newList[index].url; return; }
  H = opts;
  list = newList; i = Math.max(0, Math.min(index, list.length - 1));
  opener = newOpener || $(`.plate__link[data-work="${list[i].id}"]`) || opener;
  const was = dlg.open;
  if (!was) {
    if (!opts.fromHistory) base = { url: location.href, title: doc.title };
    else base = base || { url: $('link[rel=canonical]')?.href || location.href, title: doc.title };
    root.classList.add('room-open'); root.style.overflow = 'hidden';
    dlg.showModal();
  }
  render(i, {});
  if (!was && !opts.fromHistory) {
    const w = cur(), same = new URL(w.url, location.href).pathname === location.pathname;
    history.pushState({ room: w.id }, '', same ? w.url + '#room' : w.url);
  }
  if (!was) E.fig.focus({ preventScroll: true });
}

function close() { if (dlg.open) dlg.close(); }

function onClosed() {
  stopPlay(); unzoom(true); clearPeek(); E.wrap.style.transform = ''; swipe = null; pointers.clear();
  if (doc.fullscreenElement === dlg) doc.exitFullscreen().catch(() => {});
  root.classList.remove('room-open'); root.style.overflow = '';
  if (base) doc.title = base.title;
  if (viaPop) viaPop = false;
  else if (history.state && history.state.room) history.back();
  else if (base) history.replaceState(null, '', base.url);
  if (opener && opener.isConnected) opener.focus();
}

function onPop(e) {
  const id = e.state && e.state.room;
  if (id) {
    const k = list.findIndex(w => w.id === id); if (k < 0) return;
    if (dlg.open) { if (k !== i) render(k); }
    else open(list, k, opener, { ...H, fromHistory: true });
  } else if (dlg.open) { viaPop = true; dlg.close(); }
}

/* ---------- zoom 1:1 ---------- */

function place(x, y, from) {
  const z = zoom, sw = E.stage.clientWidth, sh = E.stage.clientHeight;
  z.x = z.w <= sw ? (sw - z.w) / 2 : Math.min(0, Math.max(sw - z.w, x));
  z.y = z.h <= sh ? (sh - z.h) / 2 : Math.min(0, Math.max(sh - z.h, y));
  const to = `translate(${z.x}px,${z.y}px)`;
  z.anim?.cancel(); z.anim = null;
  if (from && !reduced()) z.anim = z.el.animate([{ transform: from }, { transform: to }], { duration: 250, easing: 'cubic-bezier(.2,.7,.2,1)' });
  z.el.style.transform = to;
}
const fitted = () => {          // transform that lays the 1:1 layer exactly over the fitted image
  const s = E.stage.getBoundingClientRect(), r = E.img.getBoundingClientRect();
  return `translate(${r.left - s.left}px,${r.top - s.top}px) scale(${r.width / zoom.w})`;
};

function zoomIn(px, py) {
  const w = cur(); if (!zoomable(w) || zoom) return;
  stopPlay();
  const el = doc.createElement('img'), badge = doc.createElement('span');
  el.className = 'room__zoom-img'; el.alt = ''; el.draggable = false;
  el.style.cssText = 'position:absolute;left:0;top:0;max-width:none;max-height:none;transform-origin:0 0;cursor:grab;touch-action:none;user-select:none';
  badge.className = 'room__badge'; badge.textContent = '1:1';
  badge.style.cssText = 'position:absolute;right:16px;bottom:16px;padding:4px 8px;font:500 13px/1 system-ui,sans-serif;color:#141210;background:#f5f0e8;border-radius:2px;pointer-events:none';
  zoom = { el, badge, x: 0, y: 0, w: 0, h: 0, src: w.zoomSrc };
  el.src = w.zoomSrc;
  el.decode().then(() => {
    if (!zoom || zoom.el !== el) return;
    const r = E.img.getBoundingClientRect(), s = E.stage.getBoundingClientRect(), dpr = devicePixelRatio || 1;
    zoom.w = el.naturalWidth / dpr; zoom.h = el.naturalHeight / dpr;
    el.style.width = zoom.w + 'px'; el.style.height = zoom.h + 'px';
    const ax = px ?? r.left + r.width / 2, ay = py ?? r.top + r.height / 2;
    const fx = (ax - r.left) / r.width, fy = (ay - r.top) / r.height;      // anchor stays under the pointer
    E.stage.append(el, badge);
    place(ax - s.left - fx * zoom.w, ay - s.top - fy * zoom.h, fitted());
    dlg.classList.add('room--zoomed'); label(E.zoom, S.zoom_out); E.zoom.setAttribute('aria-pressed', 'true');
  }).catch(() => { zoom = null; });
}

function unzoom(instant) {
  const z = zoom; if (!z) return;
  zoom = null;
  dlg.classList.remove('room--zoomed'); label(E.zoom, S.zoom); E.zoom.setAttribute('aria-pressed', 'false');
  z.badge.remove();
  if (instant || reduced() || !z.w || !z.el.isConnected) { z.el.remove(); return; }
  const s = E.stage.getBoundingClientRect(), r = E.img.getBoundingClientRect();
  z.el.animate([{ transform: z.el.style.transform }, { transform: `translate(${r.left - s.left}px,${r.top - s.top}px) scale(${r.width / z.w})` }],
    { duration: 250, easing: 'cubic-bezier(.2,.7,.2,1)' }).onfinish = () => z.el.remove();
}
let lastToggle = 0;
const toggleZoom = (x, y) => { lastToggle = performance.now(); zoom ? unzoom() : zoomIn(x, y); };
const pan = (dx, dy) => zoom && place(zoom.x + dx, zoom.y + dy);

/* ---------- slideshow ---------- */

function startPlay() {
  if (play || list.length < 2) return;
  if (i === list.length - 1) go(0);
  play = {};
  dlg.classList.add('room--playing'); label(E.play, S.pause); E.play.setAttribute('aria-pressed', 'true');
  tick();
}
function tick() {
  if (E.progress) {
    E.progress.style.transformOrigin = '0 50%';
    play.anim = E.progress.animate([{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }], { duration: 6000, easing: 'linear', fill: 'forwards' });
  }
  play.timer = setTimeout(() => {
    if (i < list.length - 1) { go(i + 1, { cross: true }); tick(); } else stopPlay();
  }, 6000);
}
function stopPlay() {
  if (!play) return;
  clearTimeout(play.timer); play.anim?.cancel(); play = null;
  dlg.classList.remove('room--playing'); label(E.play, S.play); E.play.setAttribute('aria-pressed', 'false');
}

/* ---------- swipe (follow the finger; the neighbour's placeholder slides in) ---------- */

function peekFor(k) {
  if (peek && peek.k === k) return peek.el;
  clearPeek();
  const w = list[k]; if (!w) return null;
  const b = stageBox(), pw = fitW(w.ar), ph = pw / w.ar;
  const el = doc.createElement('div');
  el.className = 'room__peek'; el.setAttribute('aria-hidden', 'true');
  el.style.cssText = `position:absolute;width:${pw}px;height:${ph}px;top:${(b.height - ph) / 2}px;left:${(b.width - pw) / 2 + (k > i ? b.width : -b.width)}px;` +
    `background:${w.deep || '#000'} url("${w.lqip || ''}") center/contain no-repeat;pointer-events:none`;
  E.stage.append(el); peek = { k, el };
  return el;
}
function clearPeek() { if (peek) { peek.el.remove(); peek = null; } }

function slide(dx, dy) {
  const t = dy ? `translateY(${dy}px)` : `translateX(${dx}px)`;
  E.wrap.style.transform = t; if (peek) peek.el.style.transform = t;
}
function settle(toX, then) {               // animate wrap (+ peek) to toX, then clean up
  const d = ms('--d-1', 150), from = E.wrap.style.transform || 'translate(0,0)', to = `translateX(${toX}px)`;
  const els = [E.wrap, peek && peek.el].filter(Boolean);
  const anims = d ? els.map(el => el.animate([{ transform: from }, { transform: to }], { duration: d, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'forwards' })) : [];
  const finish = () => { anims.forEach(a => a.cancel()); E.wrap.style.transform = ''; clearPeek(); then && then(); };
  if (!d) return finish();
  setTimeout(finish, d + 20);
}

function onDown(e) {
  if (e.button !== 0) return;
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    pinch = { d0: Math.hypot(a.x - b.x, a.y - b.y), mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2, done: false };
    swipe = null; E.wrap.style.transform = ''; clearPeek();
    return;
  }
  try { E.stage.setPointerCapture(e.pointerId); } catch { /* pointer already gone */ }
  swipe = { id: e.pointerId, x0: e.clientX, y0: e.clientY, t0: e.timeStamp, dx: 0, dy: 0, axis: '', type: e.pointerType, zx: zoom && zoom.x, zy: zoom && zoom.y };
  if (zoom) zoom.el.style.cursor = 'grabbing';
}
function onMove(e) {
  const p = pointers.get(e.pointerId); if (!p) return;
  p.x = e.clientX; p.y = e.clientY;
  if (pinch && pointers.size === 2) {
    const [a, b] = [...pointers.values()], d = Math.hypot(a.x - b.x, a.y - b.y), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    if (zoom) { pan(mx - pinch.mx, my - pinch.my); pinch.mx = mx; pinch.my = my; }
    if (!pinch.done) {
      if (!zoom && d / pinch.d0 > 1.3 && zoomable(cur())) { pinch.done = true; zoomIn(mx, my); }
      else if (zoom && d / pinch.d0 < 0.75) { pinch.done = true; unzoom(); }
    }
    return;
  }
  if (!swipe || e.pointerId !== swipe.id) return;
  const dx = swipe.dx = e.clientX - swipe.x0, dy = swipe.dy = e.clientY - swipe.y0;
  if (zoom) { place(swipe.zx + dx, swipe.zy + dy); swipe.axis = 'pan'; return; }
  if (!swipe.axis && Math.hypot(dx, dy) > 8) swipe.axis = Math.abs(dx) > Math.abs(dy) ? 'x' : dy > 0 ? 'y' : 'none';
  if (swipe.axis === 'x') {
    const k = dx < 0 ? i + 1 : i - 1, has = !!list[k];
    if (has) peekFor(k); else clearPeek();
    slide(has ? dx : dx / 3, 0);
  } else if (swipe.axis === 'y') slide(0, dy);
}
function onUp(e) {
  pointers.delete(e.pointerId);
  if (pointers.size < 2) pinch = null;
  if (!swipe || e.pointerId !== swipe.id) return;
  const { dx, dy, axis, type } = swipe, dt = Math.max(1, e.timeStamp - swipe.t0);
  swipe = null;
  if (zoom) zoom.el.style.cursor = 'grab';
  if (e.type === 'pointercancel') { if (!zoom) settle(0); return; }
  if (zoom && axis === 'pan' && Math.hypot(dx, dy) > 6) return;
  if (axis === 'x') {
    const dir = dx < 0 ? 1 : -1, b = stageBox();
    if ((Math.abs(dx) >= 48 || Math.abs(dx) / dt > 0.4) && list[i + dir]) settle(-dir * b.width, () => go(i + dir));
    else settle(0);
  } else if (axis === 'y') {
    if (dy > 80) { E.wrap.style.transform = ''; close(); } else settle(0);
  } else if (!axis || axis === 'pan') {                        // a tap or click
    if (e.target.closest('button, a')) return;
    if (type === 'touch') { const now = e.timeStamp; if (now - lastTap < 300) { lastTap = 0; toggleZoom(e.clientX, e.clientY); } else lastTap = now; }
    else if (performance.now() - lastToggle > 350) toggleZoom(e.clientX, e.clientY);   // a double-click is one toggle
  }
}

/* ---------- keyboard ---------- */

function onKey(e) {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key, onCtl = !!e.target.closest('button, a, [tabindex="0"]');
  if (play && k !== 's' && k !== 'S' && !(onCtl && (k === 'Enter' || k === ' '))) stopPlay();
  let used = true;
  switch (k) {
    case 'ArrowLeft': if (zoom) pan(40, 0); else go(i - 1); break;
    case 'ArrowRight': if (zoom) pan(-40, 0); else go(i + 1); break;
    case 'ArrowUp': if (zoom) pan(0, 40); else used = false; break;
    case 'ArrowDown': if (zoom) pan(0, -40); else used = false; break;
    case 'Home': go(0); break;
    case 'End': go(list.length - 1); break;
    case 'Escape': if (zoom) unzoom(); else close(); break;
    case 'z': case 'Z': toggleZoom(); break;
    case '+': case '=': zoomIn(); break;
    case '-': case '_': case '0': unzoom(); break;
    case 's': case 'S': play ? stopPlay() : startPlay(); break;
    case 'f': case 'F': toggleFull(); break;
    case 'i': case 'I': toggleBar(); break;
    case 'Enter': if (e.target === E.fig || e.target === E.stage) toggleZoom(); else used = false; break;
    default: used = false;
  }
  if (used) e.preventDefault();
}

function toggleFull() {
  if (doc.fullscreenElement) doc.exitFullscreen().catch(() => {});
  else if (dlg.requestFullscreen) dlg.requestFullscreen().catch(() => {});
}
function toggleBar() {
  E.bottom.hidden = !E.bottom.hidden;
  dlg.classList.toggle('room--bare', E.bottom.hidden);
}

/* ---------- setup (once per page) ---------- */

function init() {
  if (dlg) return true;
  const d = $('dialog#room'); if (!d || typeof d.showModal !== 'function') return false;
  dlg = d;
  try { S = JSON.parse($('#room-data').textContent).strings || {}; } catch { S = {}; }
  const q = s => $(s, dlg);
  E = {
    counter: q('.room__counter'), lang: q('.room__lang'), close: q('.room__close'), prev: q('.room__prev'), next: q('.room__next'),
    stage: q('.room__stage'), fig: q('.room__figure'), wrap: q('.room__img-wrap'), img: q('.room__img'),
    bottom: q('.room__bar-bottom'), no: q('#room-caption-no'), title: q('#room-caption-title'),
    ask: q('.room__ask'), share: q('.room__share'), zoom: q('.room__zoom'), play: q('.room__play'),
    full: q('.room__fullscreen'), open: q('.room__open'), progress: q('.room__progress'),
  };
  for (const k in E) if (!E[k] && k !== 'lang' && k !== 'progress') { console.warn('room: missing .room__' + k); E[k] = doc.createElement(k === 'ask' || k === 'open' ? 'a' : 'span'); }
  if (!E.counter.hasAttribute('aria-live')) E.counter.setAttribute('aria-live', 'polite');
  if (getComputedStyle(E.stage).position === 'static') E.stage.style.position = 'relative';
  if (getComputedStyle(E.wrap).position === 'static') E.wrap.style.position = 'relative';
  E.stage.style.overflow = 'hidden'; E.stage.style.touchAction = 'none';
  dlg.style.overscrollBehavior = 'contain';
  E.img.draggable = false;
  if (E.fig.tabIndex < 0 && !E.fig.hasAttribute('tabindex')) E.fig.tabIndex = -1;

  dlg.addEventListener('close', onClosed);
  dlg.addEventListener('cancel', e => { e.preventDefault(); if (zoom) unzoom(); else close(); });
  dlg.addEventListener('keydown', onKey);
  dlg.addEventListener('pointerdown', e => { if (!e.target.closest('.room__play')) stopPlay(); }, true);
  dlg.addEventListener('wheel', e => { stopPlay(); if (e.ctrlKey) return; if (zoom) pan(-e.deltaX, -e.deltaY); e.preventDefault(); }, { passive: false });
  dlg.addEventListener('dragstart', e => e.preventDefault());
  E.stage.addEventListener('pointerdown', onDown);
  E.stage.addEventListener('pointermove', onMove);
  E.stage.addEventListener('pointerup', onUp);
  E.stage.addEventListener('pointercancel', onUp);
  E.close.addEventListener('click', close);
  E.prev.addEventListener('click', () => { stopPlay(); go(i - 1); });
  E.next.addEventListener('click', () => { stopPlay(); go(i + 1); });
  E.zoom.addEventListener('click', () => toggleZoom());
  E.play.addEventListener('click', () => play ? stopPlay() : startPlay());
  E.full.addEventListener('click', toggleFull);
  E.share.addEventListener('click', () => {
    const w = cur(), copied = S.share_copied || 'Link copied';
    if (H.share) H.share(titleFor(w), abs(w.url), copied);
    else navigator.clipboard?.writeText(abs(w.url)).then(() => toastFn(copied), () => toastFn(abs(w.url)));
  });
  E.open.addEventListener('click', () => {         // let the dialog image morph into the artwork stage
    const n = 'work-' + cur().id;
    $$(`[style*="${n}"]`).forEach(el => { if (el !== E.img) el.style.viewTransitionName = ''; });
    E.img.style.viewTransitionName = n;
  });
  doc.addEventListener('fullscreenchange', () => E.full.setAttribute('aria-pressed', String(doc.fullscreenElement === dlg)));
  addEventListener('resize', () => { if (zoom) place(zoom.x, zoom.y); });
  addEventListener('popstate', onPop);
  return true;
}
