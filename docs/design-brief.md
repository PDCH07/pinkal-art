# pinkal.art — Design brief and implementation contract

Status: final. Design director's decisions after four concepts and three judge reports. Every value below is a decision, not a suggestion. Where a fact depends on the artist, the brief names the data field that holds it and what renders while the field is empty. Numbers marked *(est.)* are estimates with their basis stated; every other number was measured this session (`tools/images.py` output in `data/images.json`, source files in `images/fulls/`, contrast and clamp arithmetic run against the token values below).

Source of truth for the collection: 42 image ids exist (01–11, 13–42, 99). `04.jpg` and `09.jpg` are byte-identical (md5 equal), so 09 is a duplicate record; 99 is a photograph of eight small canvases on easels, not a painting. **The collection is 40 paintings plus one studio photograph. No count is ever typed into copy; the build computes it.**

## 1. Vision in one paragraph, and the three things a visitor must remember

A solo exhibition on a warm, light wall. One painting hangs first, whole and flat, on a wall tinted a near-neutral shade of its own colour, with a museum label beside it; the words come second. The route through the work is five rooms built from the artist's real motifs (rain and umbrellas, subjects from India, landscapes, animals, music and colour), hung at true proportion in justified rows, never masonry, never cropped, never framed or tilted. Darkness has exactly one meaning: the viewing room, a native dialog lit by the painting's own deep colour, where a collector can step through the collection, zoom into brushwork where the photograph allows it, and ask about a painting with one tap. Underneath sits a build pipeline that renders every page from data, refuses to publish an unconfirmed fact or an unfinished legal page, and serves a 390 px phone a painting within the first second.

Three things a visitor must remember: (1) the painting was the first thing on the screen, large, sharp and uncropped; (2) these are real places, animals and gods painted brighter than life, by a painter in Ludwigsburg; (3) any painting can be asked about in one tap, in English or German.

## 2. Positioning, hero line, tagline, voice rules, placeholders

**Positioning.** Pinkal paints things people already know — the Taj Mahal, Paris, an Alpine lake town, Ganesha, swans, horses, butterflies, couples under umbrellas — in colour brighter than life and in places that never met (a palace on a waterfall, rain as drips of paint). Recognisable subjects, unexpected colour, original canvases from a studio in Ludwigsburg.

**Hero line (EN):** The known world, painted brighter.
**Tagline (EN):** Everything here exists. Not like this.
**Hero line (DE):** Bekannte Welten. Unerwartete Farben.
**Tagline (DE):** Alles hier gibt es wirklich. Nur nicht so.
**Deck (EN, home `.thesis`):** "Pinkal paints in Ludwigsburg. The Taj Mahal above a waterfall, Paris under red trees, Ganesha in saffron on black, seven horses through moonlit surf: real places, animals and gods, brighter than life."
**Deck (DE):** „Pinkal malt in Ludwigsburg. Das Taj Mahal über einem Wasserfall, Paris unter roten Bäumen, Ganesha in Safran auf Schwarz, sieben Pferde in mondheller Brandung: echte Orte, Tiere und Götter, leuchtender als im Leben.“
**Enquiry cue (button text until price data exists):** EN "Ask about size, price and availability" / DE „Nach Größe, Preis und Verfügbarkeit fragen“.

**Voice rules.** Third person, always "Pinkal", never a pronoun or a gendered German noun (no "Künstlerin/Künstler"; write "Pinkal malt"). Name what is in the picture before interpreting it. No first-person sentence anywhere unless it comes from `site.artist_statement`, which is empty. No superlatives, no "dream", "visionary", "soul", "imagined", "never existed". Sentences under 22 words. Numbers appear only through template filters that read data (`{{ works|count }}`), never as literal digits in a strings file (the copy gate greps for them; the exceptions are postcodes, phone numbers and the painting's own visible counts such as "seven horses", "eight small canvases", which the vision catalog confirmed). English addresses the reader as "you"; German uses "Sie". German copy is written, not machine-translated, and proofread by a native speaker before launch (gate G7).

**Titles.** Every title in today's `works.json` is AI working text; several misname the subject (02, 03, 21). Decision: a title renders only when `title_status` is `confirmed`. Until then every work is labelled by its number and its `subject` line (a factual description verified against the image, listed in section 13), e.g. "No. 29 · Couple under an umbrella, Paris in autumn". No "working title" tags, no apologies. Day one deliverable to the artist: a 40-row review sheet (`build/REVIEW.csv`: id, thumbnail link, subject EN/DE, proposed title, panels, status fields) for sign-off.

**Placeholder register — copy elements that need the artist's written confirmation (field → what renders while empty):**

| Element | Field | While empty |
|---|---|---|
| Artist statement / quote | `site.artist_statement{en,de}` | nothing (no quote block) |
| Biography, origin, training ("self-taught") | `site.bio{en,de}`, `site.facts.self_taught` | nothing |
| Medium ("acrylic and oil") | `site.facts.medium{en,de}`, per-work `medium` | no medium row; JSON-LD omits `artMedium` |
| Dimensions | `width_cm`, `height_cm` per work | no dimensions row |
| Year | `year` per work | no year row |
| Panels (multi-canvas) | `panels` per work (set for 08, 11, 18, 19; 30 to confirm) | nothing |
| Availability | `status` per work | no status; button carries the enquiry cue |
| Price, VAT status | `price_eur`, `price_mode`, `site.legal.vat_mode` | nothing |
| Portrait photo | `images/portrait.jpg` | signature mark + studio photo only |
| Studio visits, shipping, reply time, certificates, commissions | `site.offers.*` | nothing; commission page not built |
| WhatsApp number | `site.whatsapp` | no WhatsApp button, no sticky WhatsApp |
| Legal identity (name, address, email, phone, VAT id) | `site.legal.*` | build refuses `--deploy` |
| 04 = 09 duplicate | `duplicate_of` on 09 | 09 excluded; owner asked whether a second painting exists |
| Titles | `title`, `title_status` | number + subject |
| Instagram post links | `instagram_url` per work | no "On Instagram" link |
| Hallstatt (32), Gandhi (03), Krishna (22), species names | not stated | subject lines describe what is visible, no proper names beyond Taj Mahal, Paris, Ganesha, Shri |

## 3. Pages and URLs

Static GitHub Pages, custom domain pinkal.art, trailing-slash directories with `index.html`. English at the root, German under `/de/` with German section slugs. Slugs are catalogue numbers, two digits, never titles (GitHub Pages cannot redirect; titles will change).

| Page | EN | DE |
|---|---|---|
| Home | `/` | `/de/` |
| The hang (all 40 in five rooms) | `/works/` | `/de/werke/` |
| Room pages (5) | `/rooms/rain/`, `/rooms/india/`, `/rooms/landscapes/`, `/rooms/animals/`, `/rooms/music-and-colour/` | `/de/raeume/regen/`, `/de/raeume/indien/`, `/de/raeume/landschaften/`, `/de/raeume/tiere/`, `/de/raeume/musik-und-farbe/` |
| Artwork (40) | `/works/NN/` for NN in 01–08, 10, 11, 13–42 | `/de/werke/NN/` |
| Enquiry form + no-JS thanks | `/enquire/`, `/enquire/thanks/` (noindex) | `/de/anfrage/`, `/de/anfrage/danke/` (noindex) |
| Exhibition mode | `/show/` (noindex) | `/de/show/` (noindex) |
| Impressum, Datenschutz (German, one copy, linked from every page in both languages, English summary paragraph at the end) | `/impressum/`, `/datenschutz/` | same URLs |
| Commission page (built only when `site.offers.commissions` is true) | `/commission/` | `/de/auftrag/` |
| Link-in-bio (built only when `site.now` exists) | `/now/` | `/de/jetzt/` |
| Not found (bilingual, single file) | `/404.html` | — |
| Machine files | `/sitemap.xml`, `/robots.txt`, `/og/NN.jpg` (40), `/og/home.jpg`, `/og/room-<slug>.jpg` (5), `/manifest.webmanifest` | — |

No `/works/09/` and no `/works/99/`: today's site has no per-work URLs, so nothing is broken by omitting them. The task sheet's "42" is corrected by the data.

**Head of every page:** `<html lang="en|de">`; `<link rel="canonical">` to itself; `<link rel="alternate" hreflang="en">`, `hreflang="de"`, `hreflang="x-default">` (x-default = English counterpart); legal pages emit `hreflang="de"` and `x-default` pointing to themselves. `<meta name="theme-color">` = the page's `--art-wall` (home: hero painting; artwork: that painting; others: `#f5f0e8`). `<meta name="robots" content="noindex">` on thanks, show and 404 only.

**Sitemap:** 98 indexable URLs computed by the build (48 EN + 48 DE + 2 legal), each `<url>` carrying `xhtml:link rel="alternate"` for en, de and x-default, `lastmod` from the git date of the page's data. `robots.txt`: `User-agent: * / Allow: / / Sitemap: https://pinkal.art/sitemap.xml`.

**Page titles (local search):** EN artwork "No. 29 · Couple under an umbrella, Paris in autumn — Pinkal, painter in Ludwigsburg"; DE „Nr. 29 · Paar unter einem Schirm, Paris im Herbst – Pinkal, Malerei aus Ludwigsburg“; DE home „Pinkal – Originale Gemälde aus Ludwigsburg“; EN home "Pinkal — Original paintings, Ludwigsburg". No "kaufen" phrasing until the artist confirms the tone.

## 4. Home page sections in order

Grid: 12 columns, gutter `--gutter: clamp(16px, 4vw, 64px)` (16 px at 390, 57.6 px at 1440, 64 px at 1920), column gap 24 px, content shell max 1520 px centred except where a section bleeds.

### 4.1 `.masthead` — orientation
Content: signature mark (SVG traced from the painted "Pinkal" on No. 13, accessible name "Pinkal — home", height 28 px), nav links "Works", "Enquire", language link "DE" (on `/de/`: "EN"), Instagram icon link (accessible name "Pinkal on Instagram"). No hamburger, no "Rooms" item (rooms are reached on the works page and in section 4.4).
1440: height 72 px, mark left, links right, 32 px apart, Instrument Sans 15 px, weight 500. 390: height 56 px, all four items fit (mark 24 px high, "Works", "Enquire", "DE", icon), 44 px touch targets. Static, not sticky. Data: `strings.nav.*`, `site.instagram`.

### 4.2 `.hero` — the painting hangs first
Content: one painting, `site.hero = "13"` (3051 × 2458 source, ratio 1.241), hung on `.hang` whose background is No. 13's `--art-wall`; `.label` (number, subject, room link); display line, tagline, one text link "All {count} works →".
1440: `.hang` spans columns 1–7 and bleeds to the left viewport edge (820 px wide at 1440, 1099 px at 1920); height `min(100svh − 72px, 860px)`; painting centred with 48 px padding, `max-width: calc(100% − 96px)`, `max-height: 72vh` → No. 13 renders 724 × 583 px at 1440 × 900 and 804 × 648 px at 1920 × 900. Columns 8–12: the display line (Fraunces, `--fs-display`, weight 300, opsz 144, three lines "The known / world, / painted brighter."), tagline below in `--fs-lede` italic, link in `--fs-body`; `.label` aligned to the painting's bottom edge.
390: masthead, then `.hang` full-bleed with 16 px side padding, painting width 358 px → No. 13 renders 358 × 288 px (cap `max-height: 62svh` = 523 px of an 844 px viewport, so portraits also fit); `.label` beneath (two lines, 13 px / 17 px italic); then the display line at 44 px over three lines, tagline at 20 px, link. Painting, label and the full headline sit within the first 844 px.
Data: `works[hero]`, `images[hero].wall`, `strings.hero.*`. States: the hero image is preloaded (`fetchpriority="high"`), the only motion is a 300 ms opacity fade of the label after the image's `decode()` resolves; none under reduced motion. Hero eligibility rule enforced by the build: source long edge ≥ 2400 px and `zoom`-quality photograph (currently 13; permitted alternates 29, 02, 31).

### 4.3 `.thesis` — the claim, with proof
Content: the deck (section 2) and four proof plates, each a link to its artwork page with a one-noun caption: 01 "Taj Mahal", 32 "Alpine lake town", 21 "Ganesha", 41 "Seven horses".
1440: deck in columns 1–5 (`--fs-lede`, measure 34ch); plates in columns 6–12 in one row, each ≤ 300 px wide, bottom-aligned, caption 13 px beneath. 390: deck full width, plates 2 × 2 at 171 px each. Low-resolution sources are safe here: 01 (868 px) and 41 (748 px) at ≤ 300 CSS px are below their `--maxw` caps. Data: `site.proof = ["01","32","21","41"]`, `strings.thesis.deck`. States: static; plates get the plate hover (section 9).

### 4.4 `.rooms` — five routes, Rain first
Content: H2 "Rooms"; the Rain room expanded as a rail of its four paintings in order 29, 23, 10, 13 with its wall text; then four doors: India (lead 02), Landscapes (lead 32), Animals (lead 14), Music and colour (lead 31), each door = lead painting on its `--art-wall`, room name, one-line wall text, "{count} paintings →".
1440: rail = horizontal `scroll-snap-type: x mandatory`, items 320 px tall at true ratio, 32 px gap, wall text in a 36ch column before the first item; doors in a 4-column row, each 280 px tall. 390: rail items 220 px tall, swipeable, scroll buttons hidden (`hover: none`); doors stacked, 200 px tall. Data: `rooms.json`. States: rail shows prev/next buttons at ≥ 1024 px (44 px, `aria-controls`); `scroll-behavior: auto` under reduced motion.

### 4.5 `.sheet` — all works on one wall
Content: every painting at true proportion in a justified panel, room order concatenated, no labels; hover or focus writes "No. 13 · subject" into one fixed caption line under the panel (`aria-live="polite"`); each tile links to its artwork page; H2 "The whole wall" and a link "Open the hang →" (`/works/`).
1440: row height 110 px, gap 6 px (≈ 6 rows). 390: row height 72 px, gap 4 px (≈ 11 rows). Data: all works, 200 px variants. States: tile `:hover/:focus-visible` raises the 1 px rule to `--ink`; nothing moves.

### 4.6 `.studio` — a real place, no invention
Content: signature mark large (240 px wide), studio photograph 99 (caption "Eight small canvases on easels"), three detail crops at 1:1 from the sharpest sources (02, 20, 31; rectangles in `data/crops.json`, each ≥ 1200 source px square, no canvas edge, glare or signature inside), captioned "Detail, No. 02"; paragraph from confirmed fields only: "Pinkal paints in Ludwigsburg, Baden-Württemberg. {medium sentence} {self_taught sentence} New work appears first on Instagram: @pinkal_art_kunst." Hidden slots: portrait, bio, exhibitions, visits.
1440: photo 99 in columns 1–6 (max 853 px wide, its cap), crops 3-up in columns 7–12 with the paragraph beneath. 390: photo, crops 3-up at 110 px, paragraph. Data: `site.facts`, `site.bio`, `crops.json`.

### 4.7 `.enquire` — the door
Content: H2 "Ask about a painting"; the form partial (section 5 lists fields); beside it the trust column: location line, Instagram, WhatsApp link (hidden until `site.whatsapp`), Impressum address line (rendered from `site.legal`, hidden until present), one privacy line linking `/datenschutz/`.
1440: form columns 1–7, trust columns 9–12. 390: stacked, 48 px fields, 52 px submit. States: idle, invalid (inline errors in `--accent-ink` with `aria-describedby`), sending (button disabled, text "Sending…"), sent (`role="status"` line "Thank you. Pinkal will reply by email."), failed (status line with a `mailto:` fallback from `site.legal.email`).

### 4.8 `.colophon`
Content: nav, DE/EN, Impressum, Datenschutz, Instagram, "No cookies, no tracking. Fonts and images are served from this site. Set in Fraunces and Instrument Sans." 1440: one row; 390: two rows. Static.

## 5. Artwork page `/works/NN/`

**1440 (light wall, not dark):** `.plate-stage` in columns 1–8 bleeding left: painting on a 24 px mat of its `--art-wall`, `max-height: calc(100vh − 160px)`, `max-width: min(100% − 48px, var(--maxw))`, 1 px inset `--rule`, `--shadow-hang`; click or Enter opens the viewing room (`#room`). `.label` in columns 9–12, `position: sticky; top: 32px`:
- `.label__no` "No. 13" (Fraunces, `--fs-no`, weight 200, tabular figures)
- `h1.label__title` = `title` if confirmed, else `subject`; when the title is confirmed the subject moves to `.label__subject` beneath (italic)
- `.label__room` link "Rain →"
- `dl.label__meta` rows rendered only when the field exists: Medium, Dimensions ("60 × 80 cm", `width_cm × height_cm`), Year, Painted across N canvases (`panels`), Signed (`signed`), Availability (`status`: Available / Reserved / Sold / Private collection), Price (`price_mode`: `show` → "€ {price_eur} incl. VAT, plus shipping" or, when `site.legal.vat_mode = kleinunternehmer`, "€ {price_eur}, no VAT shown under § 19 UStG, plus shipping"; `request` → "Price on request"; null → nothing). All rows empty → no `<dl>` at all.
- `.label__text`: `desc` only when `desc_approved`; prefixed "In Pinkal's words" only when `text_by = artist`
- `.label__actions`: primary button "Ask about size, price and availability" (→ `/enquire/?work=13`; text changes to "Ask about this painting" once any of medium/dimensions/price exists; "Ask about a similar painting" when `status = sold`); "View" (opens the room); "Share" (`navigator.share({title, url})`, fallback copies the URL and shows a `role="status"` toast "Link copied"); WhatsApp (hidden until `site.whatsapp`; `https://wa.me/<number>?text=<url>`); "On Instagram" (hidden until `instagram_url`).
Below the fold: `.related` "In the same room": four works, the two before and two after in room order (wrapping), 200 px tall plates; then `.pager`: prev/next in global hang order as two half-width cards (thumbnail, number, subject), with `rel="prev|next"`.

**390:** `.label__no` + `h1` first (two lines), `.plate-stage` full-bleed with 16 px mat, `max-height: 70svh`, then meta, text, related as a 140 px `scroll-snap` strip, pager 2-up with 44 px arrows. A sticky bottom bar `.inquiry-bar` (56 px + `env(safe-area-inset-bottom)`, background `--paper-2`, top rule) holds "Ask" (primary) and "View"; WhatsApp joins it when a number exists.

**Inquiry prefill:** `/enquire/?work=13` selects No. 13 in the form's `<select>`, sets hidden `_subject` = "Enquiry: No. 13 — {subject}" and hidden `work_url`. Formspree endpoint stays `https://formspree.io/f/xrbqdlkk` (index.html line 856).

**JSON-LD** (one `<script type="application/ld+json">`): `@graph` of `VisualArtwork` {`@id` = page URL, `name` = title if confirmed else "No. 13 — subject", `description` = subject, `image` = largest JPEG ≤ 2400, `url`, `inLanguage`, `artform: "Painting"`, `creator`: Person {`name: "Pinkal"`, `url: "https://pinkal.art/"`, `sameAs: ["https://www.instagram.com/pinkal_art_kunst/"]`}, `artMedium` only when `medium`, `width`/`height` as QuantitativeValue in cm only when known, `dateCreated` only when `year`, `isPartOf` = room page, `offers` (Offer with `price`, `priceCurrency: "EUR"`, `availability`) only when `price_mode = show` and `status = available`} plus `BreadcrumbList` (Home → Works → Room → No. NN). `og:type article`, `og:image /og/NN.jpg` 1200 × 630, `og:locale` and `og:locale:alternate`.

## 6. Gallery mechanics

**Rooms (derived from the vision catalog; one room per work; 40 works):**
- **Rain** (`rain` / `regen`): 29, 23, 10, 13. Lead 29.
- **India** (`india` / `indien`): 02, 01, 03, 21, 06, 19, 41, 28. Lead 02.
- **Landscapes** (`landscapes` / `landschaften`): 32, 42, 33, 38, 34, 36, 27, 37, 35, 04, 18. Lead 32.
- **Animals** (`animals` / `tiere`): 14, 05, 15, 07, 08, 16, 24, 30, 40, 17, 39, 11. Lead 14.
- **Music and colour** (`music-and-colour` / `musik-und-farbe`): 31, 22, 20, 25, 26. Lead 31.
Leads come only from sources ≥ 2400 px (02 05 06 08 13 14 15 19 20 21 23 24 25 26 29 31 32 42). Global hang order = rooms concatenated in the order above. Wall texts (≤ 45 words, subject first, no counts) live in `rooms.json`; EN examples: Rain — "Every painting in this room carries an umbrella: a couple in Paris, a girl in a white dress, a woman in red on wet steps, two silhouettes under a red canopy. Rain falls as streaks, flecks and drips of paint." India — "Ganesha in orange, in saffron and on blue; the Taj Mahal above a waterfall; a spinning wheel; a village well; a peacock's train; seven horses through surf. Subjects from India, painted in Ludwigsburg."

**Grid algorithm (the hang, `/works/` and room pages):** build-partitioned justified rows, never masonry. For each room the build runs a greedy partition at the reference content width 1376 px (1440 − 2 × 32) with gap 32 px and target row height 320 px: works are added to a row until the row's height at full width drops below 320 px; the row is closed when it is closer to 320 px than the next candidate would make it. Rules: 19 (ratio 2.30) and 18 (3.11) form single-work bands; 20 (0.415) and 42 (0.476) are never in the same row; a row never holds two low-cap works (`--maxw` < 500); the last row is not stretched (filler element). Each `.hang__row` is `display:flex; gap:32px`; each `figure.plate` has `flex: var(--ar) 1 0` and `aspect-ratio: var(--ar)`; the row scales with the viewport, so 700–1199 px uses the same rows at 165–280 px heights. Below 700 px: one column, each plate full width (358 px at 390), portraits capped at `70svh`. Row heights, gaps and `sizes` attributes are written per figure by the build.

**Sizing rules.** Every plate carries `--maxw` = floor(source width ÷ 1.5) CSS px (build-computed for all works, not a hard-coded list): 01 → 578, 04 → 635, 07 → 808, 10 → 590, 11 → 370, 16 → 575, 17 → 451, 18 → 825, 27 → 640, 28 → 452, 35 → 289, 36 → 984, 37 → 993, 39 → 399, 41 → 498, 99 → 853; larger sources never bind. When the cap binds, the painting centres on its slot's `--art-wall` mat ("a small plate on a wide mat"); no apology caption. The pipeline never upscales; at 2× DPR a capped work is browser-scaled at most 1.33×. Works with source long edge < 2400 px are excluded from hero, room leads, `/show/` and OG hero cards (they get an OG card of their own page at their own size). **Tondo 27:** `shape: round` → `.plate--round img { clip-path: circle(49.6%) }`, no inset rule, shadow via `filter: drop-shadow`, mat tinted; the circle centre/radius are tunable in `works.json` (`mask`).

**Filters.** On `/works/`, a `.chips` row of six `<a>` links (All, Rain, India, Landscapes, Animals, Music and colour) pointing at the room pages; JS intercepts, filters rows in place (rows re-partitioned client-side from the embedded per-room row data, 20 lines) and `pushState`s the room URL; `aria-current="page"` on the active chip; without JS the links simply navigate. No counts in chips. At ≥ 1200 px the room name sits `position: sticky; top: 24px` in the left margin while its rows pass.

**Lightbox vs page.** Both. Tapping a plate on `/works/`, a room page or the home opens `<dialog class="room">` via `showModal()`, loading the painting from the same `images` data embedded as `data-` attributes, and `pushState`s `/works/NN/` (Back closes the dialog; reload lands on the artwork page). On the artwork page, "View" opens the same dialog and sets `#room`. Prev/next inside the dialog `replaceState` the neighbour URL and preload ±1 at 1200 px. The dialog's list is the page's list (room page = that room; works page = current filter; home sheet = all 40).

**The viewing room (dialog).** Background `radial-gradient(120% 80% at 50% 30%, var(--art-deep), var(--room))`; painting `object-fit: contain` within `calc(100dvh − 112px)` × `calc(100vw − 128px)` at ≥ 1024 px, full width with 56 px top and bottom bars on phones; top bar: counter "13 / 40" (`aria-live="polite"`), close (44 px); bottom bar: number + subject, buttons Ask · Share · Zoom (if `zoom`) · Play · Open page. Prev/next 56 px round buttons at the viewport edges (≥ 1024 px) and as swipe on touch. Focus: on open, focus moves to the figure (`tabindex="-1"`, `aria-labelledby` the caption), not to the close button, so a screen reader announces the painting first; on close, focus returns to the plate that opened it. The page behind is inert (native). `overscroll-behavior: contain`.

**Zoom spec.** Only for works with `zoom: true` (human-set after the 1:1 QA check in gate G5; candidates are the 18 sources ≥ 2400 px; glare, canvas edges or colour casts disqualify). Trigger: Zoom button, `Z`, `+`, double-tap, pointer click on the stage. Behaviour: loads the 2400 px AVIF on demand, shows it at 1:1 device pixels anchored at the pointer/tap point, pan by drag or arrow keys (40 px per press), pinch on touch, `+`/`−` buttons for WCAG 2.2 dragging alternative, `0` or Esc returns to fit. A "1:1" badge while zoomed. Reduced motion: no 250 ms ease, instant.

**Slideshow spec.** Play button or `S`: advances every 6 s with a 500 ms crossfade; a visible Pause button replaces Play; paused by any key, pointer or touch; a 2 px progress line under the stage; stops at the list end. Under reduced motion the slideshow is still available but uses hard cuts; it never autostarts.

**Keyboard map (dialog):** `←`/`→` prev/next · `Home`/`End` first/last · `Esc` close (or exit zoom first) · `Z` toggle 1:1 · `+`/`−`/`0` zoom in/out/fit · arrows pan while zoomed · `S` play/pause · `F` fullscreen · `I` toggle label bar · `Enter` on stage = Zoom. Page (not dialog): `/` nothing; no global shortcuts.

**Swipe:** horizontal drag follows the finger with the neighbour sliding in; commit at 48 px or velocity > 0.4 px/ms, else spring back (150 ms); vertical swipe down > 80 px closes. Disabled while zoomed (pan instead).

**URL sync via history:** open → `pushState({room:true}, "", "/works/13/")`; next → `replaceState(…, "/works/14/")`; close → `history.back()` if the entry is ours, else `replaceState` to the originating page URL; `popstate` closes or re-opens accordingly; `document.title` follows the work.

## 7. Design tokens

```css
:root {
  /* surfaces (light, always; no prefers-color-scheme flip) */
  --paper: #f5f0e8;  --paper-2: #ece6db;  --rule: rgb(20 18 16 / .10);  --rule-strong: rgb(20 18 16 / .22);
  --ink: #141210;    --ink-2: #4a4440;    --ink-3: #6b625b;
  --accent: #b5472a; --accent-ink: #8f3620;  --focus: #1f5fa8;
  --ok: #2e6b45;     --reserved: #7a561b;    --sold: #8c2f2f;
  --room: #0e0d0c;   --room-ink: #e9e2d6;    --room-ink-2: #a39b90;  --focus-room: #9cc2ff;
  --art-wall: var(--paper-2); --art-deep: #1a1816;   /* overridden inline per painting */
  /* type */
  --font-display: "Fraunces", "Fraunces Fallback", Georgia, "Times New Roman", serif;
  --font-text: "Instrument Sans", "Instrument Sans Fallback", Arial, Helvetica, sans-serif;
  --fs-display: clamp(2.75rem, 1.5rem + 5.2vw, 6rem);     /* 44.3 → 96 px */
  --fs-no: clamp(3.5rem, 2.5rem + 4vw, 6rem);              /* 56 → 96 px */
  --fs-h1: clamp(2rem, 1.25rem + 2.6vw, 3.5rem);           /* 32 → 56 px */
  --fs-h2: clamp(1.625rem, 1.125rem + 1.4vw, 2.25rem);     /* 26 → 36 px */
  --fs-lede: clamp(1.25rem, 1.1rem + 0.7vw, 1.625rem);     /* 20.3 → 26 px */
  --fs-body: clamp(1.0625rem, 1rem + 0.25vw, 1.1875rem);   /* 17 → 19 px */
  --fs-small: 0.9375rem;  --fs-caption: 0.8125rem;         /* 15, 13 px; nothing smaller */
  --lh-display: 0.98; --lh-heading: 1.08; --lh-lede: 1.35; --lh-body: 1.55;
  --ls-display: -0.015em; --ls-caps: 0.08em;  --measure: 62ch;
  /* space (4-based) */
  --s-1: 4px; --s-2: 8px; --s-3: 12px; --s-4: 16px; --s-5: 24px; --s-6: 32px; --s-7: 48px; --s-8: 64px; --s-9: 96px; --s-10: 128px;
  --gutter: clamp(16px, 4vw, 64px); --col-gap: 24px; --shell: 1520px;
  /* radii, shadows */
  --r-0: 0; --r-1: 2px; --r-2: 6px; --r-pill: 999px;
  --shadow-hang: 0 1px 2px rgb(20 18 16 / .14), 0 12px 32px -16px rgb(20 18 16 / .30);
  --shadow-hang-2: 0 2px 4px rgb(20 18 16 / .16), 0 18px 44px -18px rgb(20 18 16 / .38);
  --shadow-bar: 0 -1px 0 var(--rule);
  /* motion */
  --ease-out: cubic-bezier(.2, .7, .2, 1); --ease-in-out: cubic-bezier(.65, 0, .35, 1);
  --d-1: 120ms; --d-2: 200ms; --d-3: 400ms; --d-4: 500ms;
  /* layers */
  --z-skip: 120; --z-toast: 110; --z-bar: 20; --z-chips: 15; --z-masthead: 10;
}
@media (prefers-reduced-motion: reduce) { :root { --d-1: 0ms; --d-2: 0ms; --d-3: 0ms; --d-4: 0ms; } }
```

Measured contrast (WCAG 2.x formula, run this session): on `--paper` — ink 16.47, ink-2 8.44, ink-3 5.25, accent 4.75 (large text and rules only), accent-ink 6.81, focus 5.68, ok 5.60, reserved 5.83, sold 7.22; on `--paper-2` — ink 15.05, ink-2 7.71, ink-3 4.80, accent-ink 6.22. On `--room` — room-ink 15.08, room-ink-2 7.07, focus-room 10.70. Button fill `--accent-ink` with `--paper` text: 6.81. Status colours always accompany a text label.

**Type roles:** display = Fraunces opsz 144, wght 300, `--fs-display`, `--lh-display`, `--ls-display`; h1 = Fraunces 400, `font-optical-sizing: auto`; subjects and taglines = Fraunces italic 400; numbers (`.label__no`, counters) = Fraunces 200 with `font-variant-numeric: tabular-nums`; body = Instrument Sans 400 at `--fs-body`; labels/eyebrows/chips = Instrument Sans 500, `--fs-caption`, uppercase, `--ls-caps`; forms = Instrument Sans 400 at 17 px minimum (prevents iOS zoom). German pages add `hyphens: auto; -webkit-hyphens: auto` on prose.

**Fonts to self-host (section 11 and 13 describe the build):** Fraunces (variable; keep axes opsz 9–144 and wght 300–700; pin SOFT = 30, WONK = 0; roman preloaded, italic lazy) and Instrument Sans (variable; keep wght 400–700; pin wdth = 100). Subsets latin + latin-ext (ß ä ö ü „ “ × ’ – €). Fallback faces "Fraunces Fallback" (Georgia, with `size-adjust`, `ascent-override`, `descent-override`, `line-gap-override` computed by the build with fontTools so swap shifts stay under 0.02 CLS) and "Instrument Sans Fallback" (Arial, same technique). Budget: the two preloaded files ≤ 130 KB together (est. Fraunces roman 70–90 KB, Instrument Sans 35–45 KB, basis: typical woff2 sizes of these families' latin + latin-ext variable subsets; the build measures and fails above budget), italic ≤ 80 KB.

## 8. Per-painting colour

**Extraction (build, `tools/images.py`, Pillow, OKLCH maths in pure Python):** from the 480 px variant, quantise to 8 clusters (`Image.quantize(8, method=MEDIANCUT)` as today), discard clusters with < 4 % share, convert the rest to OKLCH. Two outputs per work:
- `wall` — hue of the largest cluster with chroma ≥ 0.04 and L between 0.35 and 0.85 (the painting's "colour", not its sky); if none qualifies, hue of the largest cluster. Output OKLCH `L = 0.925`, `C = min(0.02, cluster C × 0.25)`, same hue → sRGB hex. Clamp range accepted on review: L 0.91–0.94, C ≤ 0.025.
- `deep` — hue of the darkest cluster with share ≥ 8 %, else the darkest of all. Output `L = 0.19`, `C = min(0.04, cluster C × 0.6)` → hex. Clamp range: L 0.16–0.22, C ≤ 0.05.
- Manual override: `colour: {wall, deep}` in `works.json` wins.
Sample outputs at the clamps (computed): wall hues 30°/90°/150°/210°/270°/330° give `#f3e2de #ebe6d8 #ddeadf #d8eaee #e1e6f4 #eee2ed`; deep gives `#230c09 #1b1300 #05190a #00181e #0d1226 #1e0d1c`.

**Build-time verification (gate G2):** `--ink` on `wall` ≥ 12:1 (worst case at the clamp edge L 0.91, C 0.025 measured 14.15:1); `--room-ink` on `deep` ≥ 10:1 (worst case at L 0.22, C 0.05 measured 13.11:1); `--room-ink-2` on `deep` ≥ 4.5:1 (worst 6.15:1). A failure lowers chroma in 0.005 steps until it passes and logs the change.

**Application (exactly these, nothing else):** `--art-wall` → hero wall, artwork mat, hang slot mat when the cap binds, OG card background, placeholder fill behind the LQIP, `theme-color`. `--art-deep` → viewing-room gradient, `/show/` background, dialog focus ring tint (`--focus-room` stays for the ring colour itself). Never for text, buttons, status or borders; never two tints on one surface. The deep colour crossfades over `--d-3` when stepping prev/next (moment 1).

## 9. Components (BEM)

| Block | Elements / modifiers | States | Reduced motion |
|---|---|---|---|
| `.masthead` | `__mark`, `__nav`, `__link`, `__lang`, `__ig` | link hover: underline 1 px `--ink`, offset 4 px; focus-visible: 2 px `--focus` outline, offset 3 px; `aria-current` link: underline persistent | none needed |
| `.skip-link` | — | visible on focus at top-left, `--ink` on `--paper-2`, z `--z-skip` | — |
| `.hang` | `--hero`, `--stage` | background `--art-wall`; `data-loaded` toggles label fade | label fade 0 ms |
| `.plate` | `__img`, `__caption`, `--round`, `--band`, `--capped` | 1 px inset `--rule`, `--shadow-hang`; hover: `--shadow-hang-2` and caption `--ink-3`→`--ink` over `--d-1`; focus-visible: 2 px `--focus` outline offset 4 px; loading: LQIP blurred 12 px under `--art-wall` until `decode()`, then 200 ms opacity; error: mat with number only | no shadow transition, no fade |
| `.label` | `__no`, `__title`, `__subject`, `__room`, `__meta`, `__text`, `__status`, `__price`, `__actions` | `__status--available/--reserved/--sold/--private` coloured dot + text; everything optional renders nothing when null | — |
| `.btn` | `--primary` (fill `--accent-ink`, text `--paper`), `--ghost` (1 px `--rule-strong`, text `--ink`), `--icon` (44 px square) | hover: primary darkens to `#7a2d1a`, ghost border `--ink`; active: translateY(1px); focus-visible: 2 px `--focus` outline offset 3 px; disabled: `--ink-3` text on `--paper-2`, `aria-disabled`; loading: text swap, `aria-busy` | no translate |
| `.chips` | `__chip` (`<a>`, 40 px high, pill, 8 px gap, row scrolls horizontally on phones with 16 px scroll padding) | `aria-current="page"`: fill `--ink`, text `--paper`; hover: border `--ink`; focus-visible as `.btn` | — |
| `.hang__row` | `--band` | — | — |
| `.room-label` | sticky room name at ≥ 1200 px | — | — |
| `.rail` | `__track`, `__item`, `__prev`, `__next`, `__text` | buttons hidden at list ends (`disabled`); `scroll-snap`; focus-visible on items | `scroll-behavior: auto` |
| `.door` | `__lead`, `__name`, `__text`, `__count` | whole card is one link; hover: lead shadow deepens; focus-visible outline on the card | — |
| `.sheet` | `__tile`, `__fill`, `__caption` (fixed line, `aria-live`) | tile hover/focus: inset rule `--ink`; caption updates | — |
| `.room` (dialog) | `__bar-top`, `__counter`, `__close`, `__stage`, `__img`, `__prev`, `__next`, `__bar-bottom`, `__caption`, `__actions`, `__progress`, `--zoomed`, `--playing` | open: `@starting-style` opacity 0→1 over `--d-2`, backdrop `rgb(14 13 12 / .92)`; zoomed: cursor grab/grabbing; playing: Pause shown; loading: LQIP; focus trap native | no entrance fade, hard cuts, no pan easing |
| `.inquiry-bar` | `__ask`, `__view`, `__wa` | shown < 1024 px on artwork pages; hidden while the dialog is open | — |
| `.form` | `__field`, `__label`, `__input`, `__select`, `__textarea`, `__error`, `__status`, `__honeypot`, `__privacy` | invalid: 2 px `--accent-ink` border + error text; focus: 2 px `--focus`; sending: `aria-busy`; sent: status text, fields read-only | — |
| `.toast` | — | `role="status"`, bottom centre, 2.5 s, z `--z-toast` | appears/disappears without slide |
| `.pager` | `__card`, `__thumb`, `__dir` | hover/focus as `.plate` | — |
| `.related` | `__item` | as `.plate` | — |
| `.legal` | `__section`, `__summary` (`lang="en"`) | — | — |
| `.show` (exhibition) | `__stage`, `__caption`, `__qr`, `__pause`, `__fullscreen` | playing/paused; cursor hidden after 3 s idle | hard cuts, 8 s hold |
| `.lang-hint` | one line on EN pages: "Diese Seite gibt es auch auf Deutsch →" shown when `navigator.language` starts with `de` (no storage, no cookie) | — | — |

Focus ring everywhere: 2 px solid `--focus` (or `--focus-room` on dark), offset 3–4 px, never removed. All interactive targets ≥ 44 × 44 CSS px (chips 40 px tall with 8 px gap count as 48 per WCAG 2.5.8 spacing exception; dialog arrows 56 px; bar buttons 56 px).

## 10. Signature moments (final 4)

1. **The wall is painted before the picture is hung.** Trigger: first paint of any page with a painting, and prev/next in the viewing room. Behaviour: the inline critical CSS carries `--art-wall` and a ≤ 650-byte LQIP (`data/images.json` `lqip`, measured mean 568 characters), so the first paint already shows the painting's wall and blur; the image fades in over 200 ms after `decode()`. In the room, `--art-deep` crossfades over 400 ms (`transition: background-color`) and the next image fades in over the previous one's LQIP. Fallback: no JS → image appears without fade, wall still tinted. Reduced motion: instant swaps. Cost: ≈ 0.6 KB per painting inline, 20 lines CSS, 15 lines JS.
2. **The wall becomes the room.** Trigger: navigating from a plate to its artwork page (full navigation path, no-JS path, and prev/next across artwork pages). Behaviour: `@view-transition { navigation: auto }` with `view-transition-name: work-NN` on the plate image and the stage image; the thumbnail grows into the stage over 400 ms `--ease-out` while the page crossfades; `<script type="speculationrules">` prerenders prev and next with `eagerness: "moderate"` on artwork pages. Fallback: browsers without cross-document view transitions get a plain navigation. Reduced motion: `::view-transition-group(*) { animation-duration: 0s }`. Cost: ≈ 30 lines CSS, 0 JS, prerender ≤ 2 HTML documents (≈ 10 KB gz each, est. from the HTML budget).
3. **All forty on one wall.** Trigger: scrolling to `.sheet` on the home. Behaviour: the whole collection at true proportion, 110 px rows at 1440, 72 px at 390; hover or focus writes number and subject into a fixed caption; a tap opens the viewing room over the home. Fallback: plain links. Reduced motion: unchanged (nothing animates). Cost: 40 × 200 px AVIF ≈ 160 KB lazy (est.: measured mean 22,676 B at 480 px scaled by pixel area), 12 lines JS.
4. **Exhibition mode with a QR per work** (`/show/`). Trigger: Play in the dialog, or the artist opens `/show/` on a television at a market stand. Behaviour: chromeless, `--art-deep` background, painting at `min(92vh, 92vw)` contain, 8 s hold, 1.2 s dissolve, caption "No. 13 · subject" with a build-time SVG QR (`segno`, pure Python, ≤ 2 KB each) linking to `https://pinkal.art/works/13/`; visible Pause and Fullscreen buttons, Space pauses, `wakeLock` requested when available, cursor hides after 3 s, click on the painting opens its page. Only works ≥ 2400 px are shown (18 works). Fallback: no JS → the page lists the 18 plates with QR codes as a printable sheet (useful on paper at the stand). Reduced motion: hard cuts, same 8 s. Cost: 2 KB JS, one 1600 px AVIF per step (measured 98–317 KB each for the eligible works).

## 11. Image pipeline contract

Sources stay in `sources/NN.jpg` (gitignored; today's `images/fulls/` moves there). Derived files are committed under `images/r/` and served; nothing above 2400 px is ever published.

- **Widths:** 200, 400, 800, 1200, 1600, 2000, 2400 — each generated only if ≤ source width; plus the source width itself when it falls between two steps (as today: `01-868`). The 2400 variant is generated only for works with `zoom: true`. Long edge logic: widths apply to the image width; for portraits the build also ensures a height ≤ 2400 px.
- **Formats and quality:** AVIF `quality=58, speed=6` (today's default) and progressive JPEG `quality=78, optimize=True` in `<picture>` (AVIF `<source>`, JPEG `<img>`). EXIF orientation applied, metadata stripped, sRGB.
- **`sizes` per placement (written by the build):** hero `(min-width: 1024px) calc(58vw - 96px), calc(100vw - 32px)`; artwork stage `(min-width: 1024px) min(62vw, {maxw}px), calc(100vw - 32px)`; hang plate `(min-width: 1200px) {round(ar/row_ar_sum × 1376)}px, (min-width: 700px) {round(ar/row_ar_sum × 92)}vw, calc(100vw - 32px)` computed per row; proof plates `(min-width: 1024px) 300px, 45vw`; rail items `(min-width: 1024px) {round(320×ar)}px, {round(220×ar)}px`; doors `(min-width: 1024px) 23vw, 100vw`; sheet `{round(110×ar)}px` with a `(max-width: 699px) {round(72×ar)}px` prefix; related/pager 200 px tall → `{round(200×ar)}px`.
- **Attributes:** `width`/`height` on every `<img>` (CLS 0), `decoding="async"`, `loading="lazy"` for everything after the hero and the first row of the hang, `fetchpriority="high"` on the hero only, `alt` from `alt`/`alt_de` (sheet and purely decorative repeats use `alt=""` with the link's accessible name carrying number + subject).
- **Placeholder:** 24 px JPEG data URI (`lqip`, ≤ 650 B) as `background-image` on `.plate__img` wrapper over `--art-wall`, `filter: blur(12px)` inside `overflow: hidden`, removed on decode.
- **Preload:** `<link rel="preload" as="image" imagesrcset="…" imagesizes="…" fetchpriority="high">` for the hero (home) and the stage (artwork pages); two font files; nothing else.
- **Expected weight (measured bytes from `data/images.json` for No. 13):** phone first viewport: HTML ≤ 12 KB gz + inline CSS ≤ 8 KB + fonts ≤ 130 KB + hero 800 px AVIF 51,982 B (2× DPR) or 1200 px AVIF 111,801 B (3× DPR) → ≈ 210–260 KB *(est. sum of a budget and two measurements)*. Desktop 1440 at 2× DPR: hero 1600 px AVIF 186,207 B. Budget gates: hero ≤ 120 KB on the phone candidate (1200 px) and ≤ 200 KB on the desktop candidate (1600 px); hang plates ≤ 40 KB average at 800 px (measured mean 53,762 B at 800 px today, so the hang serves 400 px to phones and 800 px only at ≥ 1200 px, and the build reports the average); OG cards ≤ 150 KB JPEG q80.
- **OG cards:** `/og/NN.jpg` 1200 × 630, painting whole at ≤ 1000 px wide on `--art-wall`, 1 px rule, "No. 13" and subject in the self-hosted fonts at bottom-left, "pinkal.art" bottom-right; `/og/home.jpg` with the hero line.
- **QR:** `images/qr/NN.svg` via `segno` for the 18 eligible works, error level M, 4-module quiet zone.

## 12. German version

**Scope.** Everything a German visitor reads: UI strings, hero, deck, room names and wall texts, subject lines (`subject_de`), alt texts (`alt_de`), form labels, errors and status lines, page titles and meta descriptions, OG text layers, 404, the `lang-hint`. Not translated: confirmed titles (unless `title_de` exists), the legal pages (German only, with an English summary paragraph). A missing German work field falls back to English wrapped in `<span lang="en">` and is listed in `build/CHECKLIST.md`.

**String table.** `data/strings.en.json` and `data/strings.de.json`, flat dotted keys, identical key sets (the build fails on a key present in one and not the other): `nav.works`, `nav.enquire`, `nav.lang`, `hero.line`, `hero.tagline`, `hero.all_works` ("All {count} works →" / „Alle {count} Werke →“), `thesis.deck`, `rooms.heading`, `rooms.count` ("{count} paintings" / „{count} Gemälde“), `sheet.heading`, `studio.*`, `label.no` ("No." / „Nr."), `label.medium`, `label.dimensions`, `label.year`, `label.panels` ("Painted across {n} canvases"), `label.status.available|reserved|sold|private`, `label.price.show|kleinunternehmer|request`, `actions.ask_default|ask_known|ask_sold|view|share|share_copied|whatsapp|instagram`, `room.counter` ("{i} / {n}"), `room.keys.*`, `form.*`, `legal.*`, `footer.*`, `error404.*`, `hint.de`. Placeholders use `{name}`; plural forms via explicit keys (`rooms.count_one`, `rooms.count_other`).

**Switch placement.** Masthead right: "DE" on English pages, "EN" on German pages, linking to the exact counterpart (artwork ↔ artwork, room ↔ room); repeated in the colophon and in the dialog's top bar. No browser-language redirect, no banner, no storage; the stateless `lang-hint` line only.

**SEO.** `hreflang` triplets everywhere; German `<title>` and descriptions written for local search ("Originale Gemälde aus Ludwigsburg", "Ganesha Gemälde", "Paris im Herbst, Gemälde"); German section slugs (`werke`, `raeume`, `anfrage`); `html lang="de"`; German typographic quotes „…“ and `hyphens: auto`; sitemap alternates; OG `og:locale de_DE` with `en_GB` alternate.

## 13. Build pipeline contract

**Repository layout:** `data/` (works.json, rooms.json, site.json, strings.en.json, strings.de.json, crops.json, images.json [generated]), `sources/` (originals, gitignored), `images/r/` (generated, committed), `images/qr/`, `fonts/` (generated, committed), `src/templates/` (Jinja2), `src/css/`, `src/js/`, `tools/` (`build.py`, `images.py`, `fonts.py`, `og.py`, `check.py`), `dist/` (output, not committed), `.github/workflows/pages.yml` (on push to main: `pip install -r tools/requirements.txt`, `python tools/build.py --deploy`, upload `dist/`, `actions/deploy-pages`). Python 3.12, Jinja2, Pillow + pillow-avif-plugin, fontTools (+ brotli), segno. Node is used only for Lighthouse CI in gate G6, never shipped.

**`data/works.json` schema (array; `*` = required):**
```
id*            "13"            two-digit string, unique, immutable
kind*          "painting" | "photo"        (99 is "photo"; photos never enter the collection count or get pages)
duplicate_of   "04"            (09 only); a work with this field is excluded everywhere
room*          "rain"          one of the five room slugs
order*         4               position within the room (integer, unique per room)
subject*       {"en": "...", "de": "..."}  factual label line, ≤ 12 words
alt*           {"en": "...", "de": "..."}  one descriptive sentence ≤ 125 characters
title          {"en": "...", "de": null}   rendered only when title_status == "confirmed"
title_status*  "none" | "proposed" | "confirmed"    (launch value: "proposed" for all)
desc           {"en": "...", "de": "..."}  wall text ≤ 45 words; desc_approved* false by default
text_by        "artist" | "studio"          only meaningful with desc
medium         {"en": "...", "de": "..."} | null
width_cm, height_cm, year    number | null
panels         integer | null       (08: 2, 11: 3, 18: 4, 19: 3)
signed         true | false | null
shape          "rect" | "round"     (27: "round"); mask {cx, cy, r} optional
status         "available" | "reserved" | "sold" | "private" | null
price_eur      number | null;  price_mode  "show" | "request" | null
zoom*          false            (true only after the 1:1 QA check)
instagram_url  string | null
colour         {"wall": "#…", "deep": "#…"} | null   (manual override)
```
Derived at build (never typed): `w`, `h`, `ar`, `maxw`, `variants`, `bytes`, `lqip`, `wall`, `deep`, `long_edge`, `eligible_lead`.

**Launch content for `works.json` (id · room · order · subject EN · subject DE):**
01 india 2 · Taj Mahal on a cliff of waterfalls · Taj Mahal auf einer Klippe aus Wasserfällen
02 india 1 · Ganesha in orange and gold on blue and red · Ganesha in Orange und Gold auf Blau und Rot
03 india 3 · Two men and a spinning wheel in a yellow room · Zwei Männer und ein Spinnrad im gelben Zimmer
04 landscapes 10 · Misty forest with red blossom and birds · Nebelwald mit roten Blüten und Vögeln
05 animals 2 · Bay horse with a raised foreleg, herd behind · Brauner mit erhobenem Vorderbein, Herde dahinter
06 india 5 · Village courtyard with a well, women, goats and a cow · Dorfhof mit Brunnen, Frauen, Ziegen und Kuh
07 animals 4 · Crimson rosella on a snowy berry branch · Pennantsittich auf verschneitem Beerenzweig
08 animals 5 · Blue butterfly with eyespots across two canvases · Blauer Schmetterling mit Augenflecken auf zwei Leinwänden
09 — duplicate_of 04
10 rain 3 · Woman in red with a white umbrella on stone steps · Frau in Rot mit weißem Schirm auf Steinstufen
11 animals 12 · Green-blue butterfly across three canvases · Grünblauer Schmetterling auf drei Leinwänden
13 rain 4 · Couple under a red umbrella, paint dripping from above · Paar unter rotem Schirm, Farbe tropft von oben
14 animals 1 · Two swans on a starlit lake at dusk · Zwei Schwäne auf einem Sternensee in der Dämmerung
15 animals 3 · Swan at a stepped waterfall in a sunlit glade · Schwan am Stufenwasserfall in sonniger Lichtung
16 animals 6 · Two bluebirds on a stump with purple flowers · Zwei Hüttensänger auf einem Stumpf mit lila Blüten
17 animals 10 · Two swans forming a heart on a park pond · Zwei Schwäne als Herz auf einem Parkteich
18 landscapes 11 · One tree in four seasons across four canvases · Ein Baum in vier Jahreszeiten auf vier Leinwänden
19 india 6 · Peacock with fanned train across three canvases · Pfau mit aufgeschlagenem Rad auf drei Leinwänden
20 music-and-colour 3 · Gold rays from a black disc on turquoise · Goldene Strahlen aus schwarzer Scheibe auf Türkis
21 india 4 · Ganesha in saffron and red on black, with mouse and modak · Ganesha in Safran und Rot auf Schwarz, mit Maus und Modak
22 music-and-colour 2 · Flute player whose music fills a night sky · Flötenspielerin, deren Musik den Nachthimmel füllt
23 rain 2 · Girl in white with a red umbrella in the rain · Mädchen in Weiß mit rotem Schirm im Regen
24 animals 7 · Blue butterfly on a bowl of flowers in rainbow swirls · Blauer Schmetterling auf einer Blumenschale in Regenbogenwirbeln
25 music-and-colour 4 · Dancers around a floating guitar in splashed colour · Tanzende um eine schwebende Gitarre in gespritzter Farbe
26 music-and-colour 5 · Lion's face in splashed and dripped paint · Löwengesicht aus gespritzter und getropfter Farbe
27 landscapes 7 · Red autumn trees by a grey river, round canvas · Rote Herbstbäume an grauem Fluss, runde Leinwand
28 india 8 · Ganesha in orange on blue with the word Shri · Ganesha in Orange auf Blau mit dem Wort Shri
29 rain 1 · Couple under an umbrella, Paris in autumn · Paar unter einem Schirm, Paris im Herbst
30 animals 8 · Large butterfly with three small ones on textured brown · Großer Schmetterling mit drei kleinen auf strukturiertem Braun
31 music-and-colour 1 · Flamenco dancer in a red skirt, dancing silhouettes behind · Flamencotänzerin im roten Rock, tanzende Silhouetten dahinter
32 landscapes 1 · Lakeside town with a church spire below snowy mountains · Seestadt mit Kirchturm unter verschneiten Bergen
33 landscapes 3 · White hillside town above a blue sea, gulls on a balustrade · Weiße Hangstadt über blauem Meer, Möwen auf einer Balustrade
34 landscapes 5 · Pink villa beside a tiered waterfall and stone bridge · Rosa Villa an einem Stufenwasserfall mit Steinbrücke
35 landscapes 9 · Stone cottage, stream, two swans and a bridge · Steinhaus, Bach, zwei Schwäne und eine Brücke
36 landscapes 6 · Log cabin below snowy mountains, couple at a footbridge · Blockhaus unter Schneebergen, Paar an einem Steg
37 landscapes 8 · Thatched cottage with a lily pond · Reetgedecktes Haus mit Seerosenteich
38 landscapes 4 · Sunset harbour with city silhouettes and a rowing boat · Hafen im Sonnenuntergang mit Stadtsilhouetten und Ruderboot
39 animals 11 · Autumn park with a stone bridge, swans and a tyre swing · Herbstpark mit Steinbrücke, Schwänen und Reifenschaukel
40 animals 9 · Girl kissing a white rabbit in tall grass · Mädchen küsst ein weißes Kaninchen im hohen Gras
41 india 7 · Seven horses galloping through moonlit surf · Sieben Pferde galoppieren durch mondhelle Brandung
42 landscapes 2 · Waterfalls down grey cliffs, a carriage on a stone bridge · Wasserfälle an grauen Klippen, eine Kutsche auf einer Steinbrücke
99 photo · Eight small canvases on easels · Acht kleine Leinwände auf Staffeleien

**`data/rooms.json`:** array of `{slug, slug_de, name{en,de}, text{en,de}, lead, order}`; membership and sequence come from the works' `room`/`order` fields, so a painting is never listed twice.

**`data/site.json`:** `name "Pinkal"`, `domain "https://pinkal.art"`, `instagram "https://www.instagram.com/pinkal_art_kunst/"`, `hero "13"`, `proof ["01","32","21","41"]`, `location {city "Ludwigsburg", region "Baden-Württemberg"}`, `formspree "xrbqdlkk"`, `whatsapp null`, `artist_statement {en null, de null}`, `bio {en null, de null}`, `facts {medium {en null, de null}, self_taught null}`, `offers {commissions false, visits null, shipping null, reply_days null, certificate null}`, `now null`, `legal {name "TODO", street "TODO", postcode "TODO", city "TODO", country "Deutschland", email "TODO", phone null, vat_id null, vat_mode "TODO" (one of "regular" | "kleinunternehmer"), responsible_mstv "TODO", form_consent_checkbox false}`.

**Templates:** `base.html` (head, masthead, colophon, hreflang, JSON-LD Person + WebSite on home), `home.html`, `works.html`, `room.html`, `work.html`, `enquire.html`, `thanks.html`, `show.html`, `legal_impressum.html`, `legal_datenschutz.html`, `404.html`, partials `plate.html`, `label.html`, `form.html`, `dialog.html`, `hang.html`. Every template renders twice (en, de) from one context.

**Outputs:** `dist/` tree per section 3; `styles.[hash8].css`, `site.[hash8].js`, `room.[hash8].js` (dialog code, `import()`ed on first open), fonts as `fraunces-[hash8].woff2` etc.; images keep content-derived names (`13-1200.avif`) because they change only with the pipeline; HTML references all hashed assets. Cache busting = hashed filenames; GitHub Pages' default caching needs nothing else.

**Build steps (`python tools/build.py`):** 1 `images.py` for new or changed sources (checks mtime + size), writes `images.json`; 2 `fonts.py` instance + subset + fallback metrics (only when `fonts/` is missing); 3 validate data (schema, uniqueness, room totals, key parity); 4 derive counts, caps, rows, colours, contrast; 5 render HTML, CSS (critical inline per template ≤ 8 KB + external), JS; 6 `og.py` and QR; 7 sitemap, robots, 404; 8 write `build/CHECKLIST.md` (per work: missing title confirmation, medium, dimensions, year, status, zoom QA, German fields; site: legal TODOs, duplicate 09, confirmation items) and `build/REVIEW.csv`; 9 `check.py` budgets; `--deploy` additionally refuses while any legal `TODO` remains or any gate fails.

**How the owner adds a painting in 3 steps:** (1) copy the photo to `sources/43.jpg` (long edge ≥ 2400 px for hero eligibility); (2) add one object to `data/works.json` with `id`, `kind`, `room`, `order`, `subject` (EN and DE), `alt` (EN and DE) — everything else may stay null; (3) run `python tools/build.py`, open `dist/index.html` to look, then `git add -A && git commit -m "Add No. 43" && git push` — Actions deploys in about two minutes.

## 14. Accessibility and performance acceptance criteria

Measured on `/`, `/works/`, `/works/13/`, `/de/`, `/de/werke/29/`, `/enquire/`, `/impressum/`:
- Lighthouse 12 mobile (default throttling, Moto G Power emulation): Performance ≥ 95, Accessibility 100, Best Practices 100, SEO 100; desktop Performance ≥ 98.
- Lab Web Vitals (Lighthouse mobile): LCP ≤ 2.2 s with the hero/stage `<img>` as the LCP element; CLS ≤ 0.02; TBT ≤ 100 ms; INP ≤ 200 ms in a manual Chrome DevTools interaction trace of open dialog → next → zoom → close.
- Byte budgets per page (build gate): HTML ≤ 60 KB raw / ≤ 14 KB gz for the home (40 inline LQIPs included), ≤ 25 KB raw for an artwork page; inline critical CSS ≤ 8 KB; external CSS ≤ 32 KB; `site.js` ≤ 12 KB gz; `room.js` ≤ 10 KB gz; two preloaded fonts ≤ 130 KB; zero third-party requests except the Formspree POST on submit.
- axe-core 4.x: 0 critical, 0 serious on every page and with the dialog open; HTML validated by the Nu checker with 0 errors; no broken internal links (`check.py` crawls `dist/`).
- Contrast: every text/background pair ≥ 4.5:1 (body) or ≥ 3:1 (≥ 24 px or 19 px bold), UI boundaries ≥ 3:1, verified by `check.py` from the token table and per-painting tints (section 8).
- Keyboard paths that must pass: (a) Tab from page load: skip link → mark → Works → Enquire → DE → Instagram → hero link → proof plates → rail items → doors → sheet tiles → studio links → form fields → submit → footer links, visible focus at every stop; (b) on a plate press Enter → dialog opens, focus on the figure, `←`/`→` move, `Z` zooms, `+`/`−` work, Esc closes, focus returns to the same plate; (c) `/works/13/` → Tab reaches View, Ask, Share, related, pager; (d) form: errors announced, submit confirmation announced via `role="status"`; (e) nothing requires hover or drag alone (sheet caption on focus, zoom via buttons, rail via buttons).
- Screen readers: NVDA + Firefox and VoiceOver + Safari iOS pass the paths above; dialog announces "Painting, No. 13, Couple under a red umbrella, 4 of 40" (counter wording in the strings).
- `prefers-reduced-motion: reduce`: no transition longer than 0 ms, no autoplay, no view transition, verified by a grep of the built CSS inside the media query and a manual check.
- Touch targets ≥ 44 × 44 CSS px measured in DevTools at 390 px; `scroll-padding-top: 24px`; no horizontal page scroll at 320–1920 px; text zoom 200 % keeps every page usable with no clipping.
- Visual regression: screenshots at 390, 768, 1024, 1440, 1920 for the seven pages above, compared per build; the painting must be visible in the first 844 px at 390 on `/`, `/de/` and every artwork page.

## 15. Legal pages (German, lawyer to confirm; fields from `site.legal`)

**`/impressum/` — Impressum (§ 5 DDG, § 18 Abs. 2 MStV)**
1. Angaben gemäß § 5 DDG: `{name}`, `{street}`, `{postcode} {city}`, `{country}`.
2. Kontakt: E-Mail `{email}`; Telefon `{phone}` (row hidden when null).
3. Umsatzsteuer: when `vat_mode = regular` and `vat_id` → "Umsatzsteuer-Identifikationsnummer gemäß § 27a UStG: {vat_id}"; when `kleinunternehmer` → "Kleinunternehmer gemäß § 19 UStG; es wird keine Umsatzsteuer ausgewiesen."
4. Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV: `{responsible_mstv}` with address.
5. Urheberrecht: all paintings, photographs and texts © Pinkal; reproduction requires written permission.
6. Haftung für Inhalte und Links (standard wording).
7. Verbraucherstreitbeilegung: not willing or obliged to take part in dispute resolution before a consumer arbitration board (§ 36 VSBG); no ODR-platform link (the EU platform was discontinued in 2025 — confirm with the lawyer).
8. English summary (`lang="en"`): who runs the site and how to contact them.

**`/datenschutz/` — Datenschutzerklärung (Art. 13 DSGVO)**
1. Verantwortlicher: `{name}`, address, `{email}`.
2. Überblick: no cookies, no tracking, no analytics, no embedded third-party content, fonts and images served from this domain, no `localStorage` use.
3. Hosting: GitHub Pages (GitHub, Inc., USA); server logs (IP address, time, requested URL, user agent) processed by GitHub; legal basis Art. 6 (1) (f) DSGVO; transfer to the USA under the EU-US Data Privacy Framework and standard contractual clauses (confirm GitHub's current certification); link to GitHub's privacy statement; retention per GitHub.
4. Kontaktformular: Formspree (Formspree, Inc., USA) receives name, e-mail address, message, the chosen painting and the IP address, and forwards them by e-mail to the Verantwortlicher; legal basis Art. 6 (1) (b) DSGVO (pre-contractual enquiry); transfer to the USA under DPF/SCCs; retention until the enquiry is settled and then deleted within `{retention_months}` months (placeholder); the honeypot field; the privacy line beside the form (a consent checkbox appears only if `form_consent_checkbox` is true, lawyer's choice).
5. WhatsApp (section rendered only when `site.whatsapp` exists): clicking opens WhatsApp (Meta Platforms Ireland); data processed by Meta per its own policy.
6. Externe Links: Instagram (Meta) opens in a new tab; no plugin, no pixel.
7. Betroffenenrechte: Art. 15–21 DSGVO, Widerruf, Beschwerderecht bei einer Aufsichtsbehörde (zuständig: Landesbeauftragter für den Datenschutz und die Informationsfreiheit Baden-Württemberg).
8. Keine automatisierte Entscheidungsfindung; keine Pflicht zur Bereitstellung außer für die Beantwortung einer Anfrage.
9. Stand: `{build date}`. English summary (`lang="en"`).

Both pages: `.legal` layout, measure 62ch, Fraunces headings, Instrument Sans body, linked from the colophon of every page and from the form. The build refuses `--deploy` while any `TODO` remains in `site.legal` or in these templates.

## 16. Kept, changed, removed from today's site

**Kept:** the domain, CNAME and GitHub Pages hosting; the Formspree endpoint `xrbqdlkk`; the 42 source photographs (moved to `sources/`); the idea of numbered works and a keyboard-capable viewer; true aspect ratios; `robots.txt`/`sitemap.xml`/`404.html` as files; vanilla JS without a framework; `prefers-reduced-motion` support; the Instagram handle.

**Changed:** dark theme → light warm paper with darkness only in the viewing room; Bodoni Moda + Jost from Google → self-hosted Fraunces + Instrument Sans; one-page site → 98 generated pages in EN and DE from data; the hero (tilted trio) → one painting hung flat, label beside, painting first on phones; copy ("a world that never existed", "imagination only", the quote, the process steps) → verifiable third-person copy with hidden slots; four categories (places/figures/creatures/nature) → five curated rooms from real motifs; masonry → build-partitioned justified rows; lightbox → native `<dialog>` viewing room synced to per-work URLs; AI titles shown → number + factual subject line until the artist confirms titles; alt text "X by Pinkal Art" → descriptive sentences in two languages; `images/thumbs` + `images/fulls` → responsive AVIF/JPEG variants ≤ 2400 px; home form only → form on home and `/enquire/` with prefill, thanks page and status states; README rewritten for the build.

**Removed:** the ticker, the fabricated quote, the stats bar ("Origin: imagination only"), the "how a world gets built" steps, the three tilted canvases, bevelled frames, gold dust, glow blobs, parallax hero stage, scroll-spy, the hamburger menu, hover zoom overlays, the "P" monogram (replaced by the painted signature), the Google Fonts request, category chip counts, 09 as a separate work, 99 as a painting, originals above 2400 px from the published site.

## 17. Build order and quality gates

**B0 — Data and truth (day 1–2).** Rewrite `works.json` to the schema with the launch content above; `rooms.json`, `site.json`, strings; produce `REVIEW.csv` for the artist (titles, subjects, panels, 04/09 question, medium, dimensions, status). Gate G1: schema valid, 40 paintings + 1 photo + 1 duplicate, every room total matches, strings key parity, no banned words (`grep -iE "imagin|dream|never existed|soul|visionary|self-taught|\b(she|her|he|his)\b"` over strings and templates returns nothing outside hidden slots), no literal digits in strings except the allowed list.

**B1 — Pipeline (day 2–4).** `images.py` with the new widths, colours and caps; `fonts.py` instancing Fraunces (SOFT 30, WONK 0) and Instrument Sans, subsets, fallback metrics; `og.py`; QR. Gate G2: no variant wider than its source; every work has `lqip`, `wall`, `deep`, `maxw`; contrast checks of section 8 pass; fonts within budget; `tnum` present (else numbers switch to Fraunces); all 2400 variants exist only for `zoom: true`.

**B2 — Tokens, templates, home and artwork page in English (day 4–8).** Critical CSS split; hero; thesis; rooms; sheet; studio; enquire; artwork page with label slots. Gate G3: screenshots at the five widths; painting within the first 844 px at 390; no horizontal scroll; byte budgets (`check.py`); CLS 0 in Lighthouse.

**B3 — Hang and viewing room (day 8–12).** Partition algorithm, works and room pages, chips, dialog with keys, swipe, URL sync, zoom, slideshow, focus management, speculation rules, view transitions. Gate G4: keyboard paths (a)–(e); axe 0 critical/serious with the dialog open; `popstate` round-trips (open → next → back → back) verified in Chrome, Safari iOS and Firefox; reduced-motion grep.

**B4 — German mirror (day 12–14).** All templates in `de`, strings complete, hreflang, sitemap. Gate G5: key parity; every DE page has its EN counterpart and vice versa; native-speaker proofreading sign-off recorded in `build/PROOFREAD.md`; zoom QA performed on the 18 candidates at 1:1 and `zoom` set accordingly.

**B5 — Form, thanks, legal (day 14–15).** Formspree flow with and without JS; Impressum and Datenschutz templates; CHECKLIST. Gate G6: Lighthouse thresholds of section 14 on all seven pages; Nu validator 0 errors; link check 0 broken; a real test submission arrives by e-mail; the Formspree plan limits (monthly cap, `_next` redirect support) confirmed by the owner.

**B6 — Exhibition mode and share cards (day 15–16).** `/show/`, QR, OG cards, WhatsApp preview test. Gate G7: OG cards render in the WhatsApp and Instagram link previews; QR codes resolve on a phone camera from a 1080p television at 3 m.

**Deploy gate (G8, automated in `build.py --deploy`, run by Actions):** G1–G7 artefacts present and green; no `TODO` in `site.legal` or legal templates; artist's sign-off on `REVIEW.csv` recorded (`data/signoff.json` with date); `desc_approved` false for every unsigned description; hero and leads pass the eligibility rule; budgets within limits. Anything red stops the deploy and prints the CHECKLIST.

**Post-launch, in order:** status and price data entry as the artist supplies it (no code change); commission page when `offers.commissions` is confirmed; `/now/`; re-photographing the thirteen paintings whose sources are under 1300 px (01, 04, 07, 10, 11, 16, 17, 18, 27, 28, 35, 39, 41; the six under 800 px — 11, 17, 28, 35, 39, 41 — first) so they can join the leads and zoom.
