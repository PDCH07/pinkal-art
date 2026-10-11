/* pinkal.art — site behaviour. ES2020 module, no dependencies, no build step.
   Loaded on every page. Everything here is an enhancement: without it every
   link navigates, the form posts to Formspree and the images still show.
   The viewing room (room.js) is import()ed on first use; its hashed URL is
   <html data-room-src="/assets/room.xxxxxxxx.js">. */

const doc = document, root = doc.documentElement;
const $ = (s, c = doc) => c.querySelector(s);
const $$ = (s, c = doc) => [...c.querySelectorAll(s)];
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const noMods = e => e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey;

let data = null;
try { data = JSON.parse($('#room-data')?.textContent || 'null'); } catch { /* no page data */ }
const works = data?.works || [];
const strings = data?.strings || {};
const dialog = $('dialog#room');
const isShow = !!$('main.show');

/* ---------- shared helpers (also handed to room.js) ---------- */

export function toast(text) {
  $$('.toast').forEach(t => t.remove());
  const t = doc.createElement('div');
  t.className = 'toast'; t.setAttribute('role', 'status'); t.textContent = text;
  doc.body.append(t);
  setTimeout(() => t.remove(), 2500);
}

export async function share(title, url, copied) {
  if (navigator.share) {
    try { await navigator.share({ title, url }); return; }
    catch (e) { if (e && e.name === 'AbortError') return; }
  }
  let ok = false;
  try { await navigator.clipboard.writeText(url); ok = true; } catch { /* fall through */ }
  if (!ok) {
    const ta = doc.createElement('textarea');
    ta.value = url; ta.readOnly = true; ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
    doc.body.append(ta); ta.select();
    try { ok = doc.execCommand('copy'); } catch { /* not available */ }
    ta.remove();
  }
  toast(ok ? copied : url);
}

/* ---------- plates: fade in after decode, mark errors ---------- */

function initPlates() {
  const mark = (img, ok) => {
    img.closest('.plate__img')?.classList.add(ok ? 'is-loaded' : 'is-error');
    if (ok) { const h = img.closest('.hang'); if (h) h.dataset.loaded = ''; }
  };
  const settle = img => img.decode().then(() => mark(img, true), () => mark(img, img.naturalWidth > 0));
  $$('.plate__img img').forEach(img => {
    if (img.complete) { img.naturalWidth ? settle(img) : mark(img, false); return; }
    img.addEventListener('load', () => settle(img), { once: true });
    img.addEventListener('error', () => mark(img, false), { once: true });
  });
}

/* ---------- the viewing room: lazy module, open on click ---------- */

let roomMod = null;
const loadRoom = () => roomMod || (roomMod = import(root.dataset.roomSrc || new URL('room.js', import.meta.url).href));

function pageList() {
  const active = $('.chips__chip[aria-current="page"]');
  if (active && active.dataset.room !== 'all') {
    const ids = new Set($$('.hang__row:not([hidden]) [data-work]').map(e => e.dataset.work));
    const sub = works.filter(w => ids.has(w.id));
    if (sub.length) return sub;
  }
  return works;
}

async function openRoom(id, opener, opts) {
  const list = pageList(), i = list.findIndex(w => w.id === id);
  if (i < 0) return false;
  const mod = await loadRoom();
  mod.default(list, i, opener, { share, toast, ...opts });
  return true;
}

function initRoomTriggers() {
  if (!dialog || isShow) return;
  const warm = e => {
    if (!e.target.closest?.('a.plate__link[data-work], [data-open-room]')) return;
    doc.removeEventListener('pointerover', warm); doc.removeEventListener('focusin', warm);
    loadRoom().catch(() => {});
  };
  doc.addEventListener('pointerover', warm, { passive: true });
  doc.addEventListener('focusin', warm);

  doc.addEventListener('click', e => {
    if (e.defaultPrevented || !noMods(e)) return;
    const el = e.target.closest('a.plate__link[data-work], [data-open-room]');
    if (!el) return;
    const id = el.dataset.work || $('[data-open-room][data-work]')?.dataset.work || $('.plate[data-work]')?.dataset.work;
    if (!id || !works.some(w => w.id === id)) return;       // unknown work: let the link navigate
    e.preventDefault();
    openRoom(id, el).catch(() => { if (el.href) location.href = el.href; });
  });

  // Forward into a room entry before room.js was loaded: open it from here (room.js handles it once loaded).
  addEventListener('popstate', e => {
    const id = e.state && e.state.room;
    if (id && !roomMod && !dialog.open) openRoom(id, null, { fromHistory: true }).catch(() => {});
  });
}

/* ---------- chips: filter the hang in place ---------- */

function initChips() {
  const nav = $('nav.chips'); if (!nav) return;
  const chips = $$('a.chips__chip[data-room]', nav);
  const rows = $$('.hang__row[data-room], .room-label[data-room], .hang__room[data-room]');
  const rooms = new Set(rows.map(r => r.dataset.room));
  const can = room => room === 'all' ? rooms.size > 1 : rooms.has(room);
  const apply = room => {
    rows.forEach(r => { r.hidden = room !== 'all' && r.dataset.room !== room; });
    chips.forEach(c => c.dataset.room === room ? c.setAttribute('aria-current', 'page') : c.removeAttribute('aria-current'));
  };
  const fromUrl = () => chips.find(c => new URL(c.href, location.href).pathname === location.pathname)?.dataset.room;
  const r0 = fromUrl(); if (r0 && can(r0)) apply(r0);
  nav.addEventListener('click', e => {
    const c = e.target.closest('a.chips__chip[data-room]');
    if (!c || !noMods(e) || !can(c.dataset.room)) return;    // room page: let the link navigate
    e.preventDefault();
    apply(c.dataset.room);
    history.pushState({ chips: c.dataset.room }, '', c.href);
  });
  addEventListener('popstate', e => {
    const room = (e.state && e.state.chips) || fromUrl();
    if (room && can(room)) apply(room);
  });
}

/* ---------- rail: prev/next scroll by one item ---------- */

function initRails() {
  $$('section.rail').forEach(rail => {
    const track = $('.rail__track', rail), prev = $('.rail__prev', rail), next = $('.rail__next', rail);
    if (!track || !prev || !next) return;
    const update = () => {
      const over = track.scrollWidth > track.clientWidth + 1;
      prev.hidden = next.hidden = !over;
      prev.disabled = track.scrollLeft <= 1;
      next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 1;
    };
    const step = dir => {
      const t = track.getBoundingClientRect(), pad = parseFloat(getComputedStyle(track).scrollPaddingLeft) || 0;
      const items = $$('.rail__item', track), edge = t.left + pad;
      const target = dir > 0
        ? items.find(li => li.getBoundingClientRect().left > edge + 1)
        : items.reverse().find(li => li.getBoundingClientRect().left < edge - 1);
      if (!target) return;
      track.scrollBy({ left: target.getBoundingClientRect().left - edge, behavior: reduced() ? 'auto' : 'smooth' });
    };
    prev.addEventListener('click', () => step(-1));
    next.addEventListener('click', () => step(1));
    track.addEventListener('scroll', update, { passive: true });
    addEventListener('resize', update);
    update();
  });
}

/* ---------- sheet: hovered or focused tile names itself in the caption ---------- */

function initSheets() {
  $$('section.sheet').forEach(sheet => {
    const cap = $('.sheet__caption', sheet); if (!cap) return;
    const say = e => {
      const tile = e.target.closest?.('.sheet__tile[aria-label]');
      if (tile) cap.textContent = tile.getAttribute('aria-label');
    };
    sheet.addEventListener('mouseover', say);
    sheet.addEventListener('focusin', say);
  });
}

/* ---------- share buttons ---------- */

function initShare() {
  doc.addEventListener('click', e => {
    const b = e.target.closest('[data-share]'); if (!b) return;
    e.preventDefault();
    share(b.dataset.title || doc.title, new URL(b.dataset.url || location.href, location.href).href,
      strings.share_copied || b.dataset.copied || 'Link copied');
  });
}

/* ---------- enquiry form: prefill, inline validation, fetch submit ---------- */

function initForms() {
  $$('form.form[data-enhance]').forEach(form => {
    const d = form.dataset, btn = $('button[type=submit]', form), status = $('.form__status', form) || $('.form__status');
    const sel = $('select[name=work]', form), subj = $('input[name=_subject]', form), wurl = $('input[name=work_url]', form);
    const fields = $$('input:not([type=hidden]):not(.form__honeypot), select, textarea', form).filter(f => f.name && f.name[0] !== '_');
    form.noValidate = true;
    form.dataset.state = 'idle';

    // Subject and work URL follow the selected painting.
    const sync = () => {
      const o = sel && sel.selectedOptions[0];
      if (!o || !o.value) return;
      const text = (o.dataset.label || o.textContent).trim(), m = text.match(/^(.+?)\s[·•]\s(.+)$/);
      const no = m ? m[1] : text, subject = o.dataset.subject || (m ? m[2] : '');
      if (subj) subj.value = [d.subjectPrefix || subj.defaultValue, no, subject && '— ' + subject].filter(Boolean).join(' ');
      if (wurl) wurl.value = new URL(o.dataset.url || (root.lang === 'de' ? '/de/werke/' : '/works/') + o.value + '/', location.href).href;
    };
    const want = new URLSearchParams(location.search).get('work');
    if (want && sel && [...sel.options].some(o => o.value === want)) sel.value = want;
    sync();
    sel?.addEventListener('change', sync);

    // Inline validation: the empty .form__error named by aria-describedby carries the message.
    const errEl = f => {
      const id = (f.getAttribute('aria-describedby') || '').split(/\s+/).find(x => doc.getElementById(x)?.classList.contains('form__error'));
      return id ? doc.getElementById(id) : null;
    };
    const message = f => {
      const v = f.validity;
      if (v.valueMissing) return f.dataset.errorRequired || d.errorRequired;
      if (v.typeMismatch || v.patternMismatch) return f.dataset.errorFormat || (f.type === 'email' ? d.errorEmail : '');
      return '';
    };
    const check = f => {
      const ok = f.checkValidity(), el = errEl(f);
      if (ok) f.removeAttribute('aria-invalid'); else f.setAttribute('aria-invalid', 'true');
      f.closest('.form__field')?.classList.toggle('is-invalid', !ok);
      if (el) el.textContent = ok ? '' : (message(f) || f.validationMessage);
      return ok;
    };
    fields.forEach(f => {
      f.addEventListener('blur', () => { if (f.value || f.hasAttribute('aria-invalid')) check(f); });
      f.addEventListener('input', () => { if (f.hasAttribute('aria-invalid')) check(f); });
    });

    const setState = (s, text) => {
      form.dataset.state = s;
      if (status && text != null) status.textContent = text;
    };
    form.addEventListener('submit', async e => {
      e.preventDefault();
      if (form.dataset.state === 'sending' || form.dataset.state === 'sent') return;
      const bad = fields.filter(f => !check(f));
      if (bad.length) { bad[0].focus(); return; }
      const label = btn.textContent;
      btn.disabled = true; btn.setAttribute('aria-busy', 'true'); btn.textContent = d.sending || 'Sending…';
      setState('sending', '');
      try {
        if ($('input[name=_gotcha]', form)?.value) throw 0;      // honeypot: pretend nothing happened
        const r = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } });
        if (!r.ok) throw r.status;
        setState('sent', d.sent || 'Thank you. Pinkal will reply by email.');
        fields.forEach(f => { if ('readOnly' in f && f.tagName !== 'SELECT') f.readOnly = true; else f.setAttribute('aria-readonly', 'true'); });
      } catch (err) {
        if (err === 0) { setState('sent', d.sent || 'Thank you.'); return; }
        btn.disabled = false; btn.removeAttribute('aria-busy'); btn.textContent = label;
        setState('failed', d.failed || 'The message could not be sent.');
        if (d.mailto && status) {
          const a = doc.createElement('a');
          a.href = 'mailto:' + d.mailto + '?subject=' + encodeURIComponent(subj?.value || '');
          a.textContent = d.mailtoText || d.mailto;
          status.append(' ', a);
        }
      }
    });
  });
}

/* ---------- language hint (stateless) ---------- */

function initLangHint() {
  const hint = $('p.lang-hint[hidden]');
  if (hint && root.lang === 'en' && /^de(-|$)/i.test(navigator.language || '')) hint.hidden = false;
}

/* ---------- view transitions: name the hovered or focused plate image ---------- */

function initViewTransitions() {
  let named = null;
  const clear = () => { if (named) { named.style.viewTransitionName = ''; named = null; } };
  const name = link => {
    const img = $('img', link), id = link.dataset.work;
    if (!img || !id || img === named) return;
    if (img.style.viewTransitionName) return;                 // the stage image already owns its name
    clear(); img.style.viewTransitionName = 'work-' + id; named = img;
  };
  const isLink = el => el instanceof Element && el.matches('a.plate__link[data-work]');
  doc.addEventListener('pointerenter', e => { if (isLink(e.target)) name(e.target); }, true);
  doc.addEventListener('pointerleave', e => { if (named && e.target === named.closest('a.plate__link')) clear(); }, true);
  doc.addEventListener('focusin', e => { const l = e.target.closest?.('a.plate__link[data-work]'); if (l) name(l); });
  doc.addEventListener('focusout', e => { if (named && e.target.closest?.('a.plate__link') === named.closest('a.plate__link')) clear(); });
}

/* ---------- boot (once) ---------- */

if (!root.dataset.siteJs) {
  root.dataset.siteJs = '1';
  initPlates();
  initRoomTriggers();
  initChips();
  initRails();
  initSheets();
  initShare();
  initForms();
  initLangHint();
  initViewTransitions();
}
