# pinkal.art

The studio gallery of **Pinkal Art** — forty-two original paintings from pure imagination.
Live at **[pinkal.art](https://pinkal.art/)**, served by GitHub Pages from `main`.

## Stack

Hand-written HTML, CSS and JavaScript. No framework, no bundler, no build step —
push to `main` and it deploys. The only external request is the Google Fonts
stylesheet (Bodoni Moda + Jost).

```
index.html      the whole site: hero, statement, featured works, gallery, studio, inquiry
styles.css      design tokens + every component
script.js       masonry, filters, lightbox, reveals, contact form
404.html        branded not-found page
images/fulls/   full-resolution paintings, shown in the lightbox
images/thumbs/  downscaled versions (max 1000px) used by the grid
CNAME           custom domain
```

## Adding a painting

1. Drop the full-resolution file into `images/fulls/` as `NN.jpg`.
2. Add a downscaled copy to `images/thumbs/` — **max 1000px on the long edge, JPEG quality ~82.**
   The grid loads all 42 thumbnails, so full-resolution files here would cost visitors
   tens of megabytes.
3. Copy an existing `<article class="work">` block in `index.html` and update:
   - `data-id` — the artwork number shown in the UI
   - `data-title` and `data-desc` — used by the lightbox
   - `data-cat` — one of `places`, `figures`, `creatures`, `nature`
   - the `src`, `href`, `alt`, and the `width`/`height` of the **thumbnail**
     (these prevent layout shift, so they must be the real pixel dimensions)
4. Bump the counts in the filter buttons near the top of the gallery section.

Nothing else needs touching — the lightbox, masonry and filters read straight from the DOM.

## Local preview

```sh
python -m http.server 8000
# then open http://localhost:8000
```

Opening `index.html` directly via `file://` mostly works, but a server is closer to production.

## Contact form

Posts to [Formspree](https://formspree.io/) (`action` on `#contactForm` in `index.html`).
JavaScript intercepts the submit for inline status messages; without JavaScript the form
still submits normally.

## Notes

- The design is deliberately dark so the paintings supply all the colour.
- `prefers-reduced-motion` is fully honoured — parallax, reveals and the marquee all stop.
- `LICENSE.txt` is the CCA 3.0 license from *Lens* by [HTML5 UP](https://html5up.net), the
  template this site originally started from. None of that code remains — the site was
  rewritten from scratch — but the credit is kept here with thanks.
