/* ============================================================
   Pinkal Art — atelier
   Vanilla, dependency-free. Everything degrades without JS.
   ============================================================ */
(function () {
  "use strict";

  var root = document.documentElement;
  root.classList.add("has-js");

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (sel, ctx) {
    return (ctx || document).querySelector(sel);
  };
  var $$ = function (sel, ctx) {
    return Array.prototype.slice.call((ctx || document).querySelectorAll(sel));
  };

  /* ---------- Footer year ---------- */
  var yearEl = $("#year");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  /* ---------- Scroll lock (without layout shift) ---------- */
  var lockCount = 0;
  function lockScroll() {
    if (lockCount++ > 0) return;
    var bar = window.innerWidth - root.clientWidth;
    if (bar > 0) document.body.style.paddingRight = bar + "px";
    document.body.classList.add("is-locked");
  }
  function unlockScroll() {
    if (--lockCount > 0) return;
    lockCount = 0;
    document.body.style.paddingRight = "";
    document.body.classList.remove("is-locked");
  }

  /* ---------- Progress bar + masthead behaviour ---------- */
  var masthead = $("#masthead");
  var progressBar = $("#progressBar");
  var lastY = window.scrollY;
  var ticking = false;

  function onScroll() {
    var y = window.scrollY;
    var max = document.documentElement.scrollHeight - window.innerHeight;

    if (progressBar) {
      progressBar.style.width = (max > 0 ? Math.min(y / max, 1) * 100 : 0) + "%";
    }

    if (masthead) {
      masthead.classList.toggle("is-stuck", y > 24);
      var goingDown = y > lastY;
      masthead.classList.toggle("is-hidden", goingDown && y > 480 && !document.body.classList.contains("is-locked"));
    }

    lastY = y;
    ticking = false;
  }

  window.addEventListener(
    "scroll",
    function () {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(onScroll);
      }
    },
    { passive: true }
  );
  onScroll();

  /* ---------- Active nav link ---------- */
  var navLinks = $$(".nav a[href^='#']");
  var sections = navLinks
    .map(function (a) {
      return document.getElementById(a.getAttribute("href").slice(1));
    })
    .filter(Boolean);

  if ("IntersectionObserver" in window && sections.length) {
    var navObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          navLinks.forEach(function (a) {
            a.classList.toggle("is-current", a.getAttribute("href") === "#" + entry.target.id);
          });
        });
      },
      { rootMargin: "-45% 0px -50% 0px" }
    );
    sections.forEach(function (s) {
      navObserver.observe(s);
    });
  }

  /* ---------- Mobile menu ---------- */
  var menu = $("#menu");
  var menuToggle = $("#menuToggle");

  function setMenu(open) {
    if (!menu || !menuToggle) return;
    menuToggle.setAttribute("aria-expanded", String(open));
    $(".sr-only", menuToggle).textContent = open ? "Close menu" : "Open menu";

    if (open) {
      menu.hidden = false;
      lockScroll();
      window.requestAnimationFrame(function () {
        menu.classList.add("is-open");
      });
      var first = $("a", menu);
      if (first) first.focus();
    } else {
      menu.classList.remove("is-open");
      unlockScroll();
      window.setTimeout(function () {
        menu.hidden = true;
      }, reduceMotion ? 0 : 400);
    }
  }

  if (menuToggle) {
    menuToggle.addEventListener("click", function () {
      setMenu(menuToggle.getAttribute("aria-expanded") !== "true");
    });
  }
  if (menu) {
    menu.addEventListener("click", function (event) {
      if (event.target.closest("a")) setMenu(false);
    });
  }

  /* ---------- Hero parallax ---------- */
  var stage = $(".hero__stage");
  if (stage && !reduceMotion && window.matchMedia("(hover: hover)").matches) {
    var canvases = $$(".canvas", stage);
    var pending = false;
    var px = 0;
    var py = 0;

    window.addEventListener(
      "pointermove",
      function (event) {
        px = event.clientX / window.innerWidth - 0.5;
        py = event.clientY / window.innerHeight - 0.5;
        if (pending) return;
        pending = true;
        window.requestAnimationFrame(function () {
          canvases.forEach(function (el) {
            var depth = parseFloat(el.dataset.depth || "16");
            el.style.transform =
              "translate3d(" + -px * depth + "px," + -py * depth + "px,0) rotate(" + px * depth * 0.06 + "deg)";
          });
          pending = false;
        });
      },
      { passive: true }
    );
  }

  /* ---------- Reveal on scroll ---------- */
  var revealTargets = $$(".reveal, .work");

  if (!("IntersectionObserver" in window) || reduceMotion) {
    revealTargets.forEach(function (el) {
      el.classList.add("is-in");
    });
  } else {
    var revealObserver = new IntersectionObserver(
      function (entries, obs) {
        var batch = 0;
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var delay = Math.min(batch++, 6) * 65;
          window.setTimeout(function () {
            entry.target.classList.add("is-in");
          }, delay);
          obs.unobserve(entry.target);
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -6% 0px" }
    );
    revealTargets.forEach(function (el) {
      revealObserver.observe(el);
    });
  }

  /* ---------- Masonry (true DOM order, no library) ---------- */
  var grid = $("#grid");
  var ROW = 8;
  var relayoutPending = false;

  function layoutGrid() {
    if (!grid) return;

    var items = $$(".work", grid).filter(function (el) {
      return !el.hidden;
    });

    // Measure at natural height first.
    grid.classList.remove("is-masonry");
    var gap = parseFloat(window.getComputedStyle(grid).rowGap) || 0;
    // offsetHeight, not getBoundingClientRect: cards carry a reveal scale()
    // transform that would otherwise shrink the measurement.
    var heights = items.map(function (el) {
      return el.offsetHeight;
    });

    // Single-column layouts do not need row spanning.
    var columns = window.getComputedStyle(grid).gridTemplateColumns.split(" ").length;
    if (columns < 2) return;

    items.forEach(function (el, i) {
      el.style.setProperty("--span", String(Math.max(1, Math.ceil((heights[i] + gap) / (ROW + gap)))));
    });
    grid.classList.add("is-masonry");
  }

  function scheduleLayout() {
    if (relayoutPending) return;
    relayoutPending = true;
    window.requestAnimationFrame(function () {
      relayoutPending = false;
      layoutGrid();
    });
  }

  if (grid) {
    scheduleLayout();
    window.addEventListener("load", scheduleLayout);
    window.addEventListener("resize", scheduleLayout);
    // Late-loading fonts or images can change intrinsic heights.
    $$("img", grid).forEach(function (img) {
      if (!img.complete) img.addEventListener("load", scheduleLayout, { once: true });
    });
  }

  /* ---------- Filters ---------- */
  var filters = $$(".filter");
  var emptyNote = $("#gridEmpty");

  filters.forEach(function (button) {
    button.addEventListener("click", function () {
      var value = button.dataset.filter;

      filters.forEach(function (b) {
        var on = b === button;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-pressed", String(on));
      });

      var shown = 0;
      $$(".work", grid).forEach(function (work) {
        var match = value === "all" || work.dataset.cat === value;
        work.hidden = !match;
        if (match) {
          shown++;
          work.classList.add("is-in");
        }
      });

      if (emptyNote) emptyNote.hidden = shown > 0;
      scheduleLayout();
    });
  });

  /* ---------- Lightbox ---------- */
  var works = $$(".work").map(function (el) {
    var link = $(".work__link", el);
    var img = $("img", link);
    return {
      id: el.dataset.id,
      title: el.dataset.title,
      desc: el.dataset.desc,
      full: link.getAttribute("href"),
      alt: img.alt,
      el: el,
      link: link,
    };
  });

  var lightbox = $("#lightbox");
  var lbImage = $("#lbImage");
  var lbSpinner = $("#lbSpinner");
  var lbNo = $("#lbNo");
  var lbTitle = $("#lbTitle");
  var lbDesc = $("#lbDesc");
  var lbNow = $("#lbNow");
  var lbTotal = $("#lbTotal");
  var lbPrev = $("#lbPrev");
  var lbNext = $("#lbNext");
  var lbClose = $("#lbClose");
  var lbInquire = $("#lbInquire");

  var current = 0;
  var lastFocused = null;

  if (lbTotal) lbTotal.textContent = String(works.length);

  function preload(src) {
    if (!src) return;
    var img = new Image();
    img.src = src;
  }

  function show(index) {
    var item = works[index];
    if (!item) return;
    current = index;

    lbImage.classList.remove("is-loaded");
    if (lbSpinner) lbSpinner.classList.add("is-on");

    lbImage.onload = function () {
      lbImage.classList.add("is-loaded");
      if (lbSpinner) lbSpinner.classList.remove("is-on");
    };
    lbImage.onerror = function () {
      if (lbSpinner) lbSpinner.classList.remove("is-on");
      lbImage.classList.add("is-loaded");
    };

    lbImage.src = item.full;
    lbImage.alt = item.alt;
    lbNo.textContent = "Work " + item.id;
    lbTitle.textContent = item.title;
    lbDesc.textContent = item.desc;
    lbNow.textContent = String(index + 1);

    preload((works[index + 1] || works[0]).full);
    preload((works[index - 1] || works[works.length - 1]).full);
  }

  function openLightbox(index) {
    if (!lightbox) return;
    lastFocused = document.activeElement;
    lightbox.hidden = false;
    lockScroll();
    show(index);
    window.requestAnimationFrame(function () {
      lightbox.classList.add("is-open");
    });
    if (lbClose) lbClose.focus();
  }

  function closeLightbox() {
    if (!lightbox || lightbox.hidden) return;
    lightbox.classList.remove("is-open");
    unlockScroll();
    window.setTimeout(
      function () {
        lightbox.hidden = true;
        lbImage.removeAttribute("src");
        lbImage.classList.remove("is-loaded");
      },
      reduceMotion ? 0 : 320
    );
    if (lastFocused && lastFocused.focus) lastFocused.focus();
  }

  function step(direction) {
    show((current + direction + works.length) % works.length);
  }

  function indexOfId(id) {
    for (var i = 0; i < works.length; i++) {
      if (works[i].id === id) return i;
    }
    return -1;
  }

  works.forEach(function (item, index) {
    item.link.addEventListener("click", function (event) {
      event.preventDefault();
      openLightbox(index);
    });
  });

  // Featured section triggers (both the image links and the text buttons).
  $$("[data-open]").forEach(function (trigger) {
    trigger.addEventListener("click", function (event) {
      var index = indexOfId(trigger.dataset.open);
      if (index < 0) return;
      event.preventDefault();
      openLightbox(index);
    });
  });

  if (lbPrev) lbPrev.addEventListener("click", function () { step(-1); });
  if (lbNext) lbNext.addEventListener("click", function () { step(1); });
  if (lbClose) lbClose.addEventListener("click", closeLightbox);

  if (lightbox) {
    lightbox.addEventListener("click", function (event) {
      if (event.target.hasAttribute("data-close")) closeLightbox();
    });

    // Swipe on touch devices.
    var touchX = 0;
    var touchY = 0;
    lightbox.addEventListener(
      "touchstart",
      function (event) {
        touchX = event.changedTouches[0].clientX;
        touchY = event.changedTouches[0].clientY;
      },
      { passive: true }
    );
    lightbox.addEventListener(
      "touchend",
      function (event) {
        var dx = event.changedTouches[0].clientX - touchX;
        var dy = event.changedTouches[0].clientY - touchY;
        if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy)) step(dx < 0 ? 1 : -1);
      },
      { passive: true }
    );
  }

  if (lbInquire) {
    lbInquire.addEventListener("click", function () {
      var item = works[current];
      var reference = $("#artworkReference");
      closeLightbox();
      if (reference) {
        reference.value = item.id + " — " + item.title;
        window.setTimeout(function () {
          var contact = document.getElementById("contact");
          if (contact) contact.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
          reference.focus({ preventScroll: true });
        }, 60);
      }
    });
  }

  /* ---------- Keyboard ---------- */
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      if (lightbox && !lightbox.hidden) closeLightbox();
      else if (menu && !menu.hidden) setMenu(false);
      return;
    }

    if (!lightbox || lightbox.hidden) return;

    if (event.key === "ArrowLeft") {
      event.preventDefault();
      step(-1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      step(1);
    } else if (event.key === "Tab") {
      // Keep focus inside the dialog.
      var focusables = $$("button, [href]", lightbox).filter(function (el) {
        return el.offsetParent !== null;
      });
      if (!focusables.length) return;
      var first = focusables[0];
      var last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  /* ---------- Contact form ---------- */
  var form = $("#contactForm");
  var status = $("#formStatus");

  if (form && status && "fetch" in window && "FormData" in window) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();

      var submit = $("button[type='submit']", form);
      status.className = "form-status";
      status.textContent = "Sending your message…";
      if (submit) submit.disabled = true;

      fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "application/json" },
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Request failed");
          form.reset();
          status.className = "form-status is-success";
          status.textContent = "Message sent. Pinkal will reply from the inquiry inbox.";
        })
        .catch(function () {
          status.className = "form-status is-error";
          status.innerHTML =
            'That did not go through. Please try again, or write via <a href="https://instagram.com/pinkal_art_kunst" target="_blank" rel="noreferrer">Instagram</a>.';
        })
        .then(function () {
          if (submit) submit.disabled = false;
        });
    });
  }
})();
