/* pinkal.art — exhibition mode (/show/). ES2020 module, no dependencies.
   Runs the eligible works from #room-data on <main class="show">: 8 s hold,
   1.2 s dissolve (hard cuts under reduced motion), caption and QR per work,
   Space or the Pause button pauses, Fullscreen button, screen wake lock,
   cursor hidden after 3 s, a click on the painting opens its page. */

const doc = document, main = doc.querySelector('main.show');

function start() {
  main.dataset.ready = '1';
  let data; try { data = JSON.parse(doc.getElementById('room-data').textContent); } catch { return; }
  const list = (data.works || []).filter(w => w.avif || w.jpg); if (!list.length) return;
  const S = data.strings || {}, $ = s => main.querySelector(s);
  const stage = $('.show__stage'), img0 = $('.show__img'), no = $('.show__no'), subj = $('.show__subject'), qr = $('.show__qr');
  const pauseBtn = $('.show__pause'), fullBtn = $('.show__fullscreen'), prog = $('.show__progress'), sheet = $('.show__sheet');
  if (!stage || !img0) return;
  const hold = +main.dataset.interval || 8000;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches, fade = reduced ? 0 : 1200;
  let avif = true, k = -1, front = img0, back, timer = null, t0 = 0, left = hold, paused = false, anim = null;

  // Two image layers for the dissolve; the second is a clone of the first.
  if (getComputedStyle(stage).position === 'static') stage.style.position = 'relative';
  back = img0.cloneNode(); back.alt = ''; back.removeAttribute('fetchpriority'); back.setAttribute('aria-hidden', 'true');
  [img0, back].forEach(im => { im.style.cssText += ';position:absolute;inset:0;margin:auto;width:100%;height:100%;object-fit:contain'; im.draggable = false; });
  back.style.opacity = '0';
  stage.append(back);
  if (sheet) sheet.hidden = true;

  const sizes = ar => Math.round(Math.min(innerWidth * 0.92, innerHeight * 0.92 * ar)) + 'px';
  const set = (im, w) => { im.sizes = sizes(w.ar); im.srcset = (avif && w.avif) || w.jpg; if (w.fallback) im.src = w.fallback; im.width = w.w; im.height = w.h; };
  const load = (im, w) => im.decode().catch(() => {
    if (avif && w.jpg && im.srcset !== w.jpg) { avif = false; im.srcset = w.jpg; return im.decode(); }
  }).catch(() => {});

  function show(n) {
    const w = list[n]; k = n;
    back.alt = w.alt || '';
    set(back, w);
    return load(back, w).then(() => {
      main.style.setProperty('--art-deep', w.deep || ''); main.style.setProperty('--art-wall', w.wall || '');
      if (no) no.textContent = w.no;
      if (subj) subj.textContent = w.title || w.subject;
      if (qr) { if (w.qr) { qr.src = w.qr; qr.hidden = false; } else qr.hidden = true; }
      doc.title = `${w.no} · ${w.title || w.subject}`;
      const out = front, inn = back;
      if (fade) {
        inn.animate([{ opacity: 0 }, { opacity: 1 }], { duration: fade, easing: 'ease-in-out', fill: 'forwards' }).onfinish = () => { inn.style.opacity = '1'; };
        out.animate([{ opacity: 1 }, { opacity: 0 }], { duration: fade, easing: 'ease-in-out', fill: 'forwards' }).onfinish = () => { out.style.opacity = '0'; };
      } else { inn.style.opacity = '1'; out.style.opacity = '0'; }
      inn.removeAttribute('aria-hidden'); out.setAttribute('aria-hidden', 'true');
      front = inn; back = out;
      const next = list[(k + 1) % list.length], pre = new Image(); set(pre, next); // warm the next one
      schedule(hold);
    });
  }

  function schedule(d) {
    clearTimeout(timer); left = d; t0 = performance.now();
    if (prog) { prog.style.transformOrigin = '0 50%'; anim?.cancel(); anim = prog.animate([{ transform: `scaleX(${1 - d / hold})` }, { transform: 'scaleX(1)' }], { duration: d, easing: 'linear', fill: 'forwards' }); }
    timer = setTimeout(() => show((k + 1) % list.length), d);
  }
  function pause() {
    if (paused) return; paused = true;
    clearTimeout(timer); left = Math.max(0, left - (performance.now() - t0)); anim?.pause();
    main.classList.add('show--paused'); main.classList.remove('show--playing');
    if (pauseBtn) { pauseBtn.setAttribute('aria-pressed', 'true'); if (S.play) pauseBtn.textContent = S.play; }
  }
  function resume() {
    if (!paused) return; paused = false;
    main.classList.add('show--playing'); main.classList.remove('show--paused');
    if (pauseBtn) { pauseBtn.setAttribute('aria-pressed', 'false'); if (S.pause) pauseBtn.textContent = S.pause; }
    schedule(left || hold);
  }
  const toggle = () => paused ? resume() : pause();

  pauseBtn?.addEventListener('click', toggle);
  if (fullBtn) {
    if (!doc.fullscreenEnabled) fullBtn.hidden = true;
    fullBtn.addEventListener('click', () => doc.fullscreenElement ? doc.exitFullscreen().catch(() => {}) : doc.documentElement.requestFullscreen().catch(() => {}));
  }
  doc.addEventListener('keydown', e => {
    if (e.key === ' ' && !e.target.closest('button, a, input, textarea')) { e.preventDefault(); toggle(); }
  });
  stage.addEventListener('click', e => { if (k >= 0 && !e.target.closest('button, a')) location.href = list[k].url; });

  // Cursor hides after 3 s without pointer movement.
  let idle = null;
  const wake = () => {
    clearTimeout(idle); main.classList.remove('show--idle'); main.style.cursor = ''; stage.style.cursor = 'pointer';
    idle = setTimeout(() => { main.classList.add('show--idle'); main.style.cursor = stage.style.cursor = 'none'; }, 3000);
  };
  addEventListener('pointermove', wake, { passive: true });
  addEventListener('pointerdown', wake, { passive: true });
  wake();

  // Keep the screen on while the show runs.
  const keep = () => { if (navigator.wakeLock && doc.visibilityState === 'visible') navigator.wakeLock.request('screen').catch(() => {}); };
  doc.addEventListener('visibilitychange', keep);
  keep();

  main.classList.add('show--playing');
  if (pauseBtn && S.pause) pauseBtn.textContent = S.pause;
  const first = list[0];
  if (img0.srcset === first.avif || img0.getAttribute('src') === first.fallback) { k = 0; schedule(hold); }   // the page already shows the first work
  else show(0);
}

if (main && !main.dataset.ready) start();
