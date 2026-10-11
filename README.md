# pinkal.art

The website of Pinkal, painter in Ludwigsburg: every page is generated from a few JSON files
and the photographs in `sources/`. English at `/`, German under `/de/`. Hosted by GitHub Pages
from the `main` branch; what is in the repo root is what is online.

## Requirements

- Python 3.12 or newer. Install the packages once:

      python -m pip install -r tools/requirements.txt
      playwright install chromium      # only for the share cards in og/; optional

- Git. Node is not needed to run the site (it is used only for quality tools).

## The one command

    python tools/build.py

It reads `data/`, renders every page into the repo root, writes the review sheet and the
checklist, generates share cards and QR codes, and ends with the quality checks. Then look at
the result:

    python -m http.server          # open http://localhost:8000/

and publish with `git add -A`, `git commit -m "..."`, `git push`.

Flags: `--no-images` skips the share cards and QR codes (fast preview); `--deploy` refuses to
finish while the legal data has `TODO`s or a check fails; `--data-dir DIR` builds from another
data folder; `--out DIR` writes somewhere else.

## Adding a painting in three steps

1. Copy the photograph to `sources/43.jpg` (two-digit number, JPEG, long edge of at least
   2400 px if it should be allowed as a hero, room lead or in the exhibition mode).
2. Add one object to `data/works.json`:

       {
         "id": "43", "kind": "painting", "room": "animals", "order": 13,
         "subject": {"en": "Fox in snow under a red moon", "de": "Fuchs im Schnee unter rotem Mond"},
         "alt": {"en": "A red fox walking through deep snow, a large red moon behind bare trees",
                 "de": "Ein Rotfuchs läuft durch tiefen Schnee, hinter kahlen Bäumen ein großer roter Mond"},
         "title_status": "none", "zoom": false, "desc_approved": false
       }

   `room` is one of `rain`, `india`, `landscapes`, `animals`, `music-and-colour`; `order` is the
   position inside that room. Everything else (`title`, `medium`, `width_cm`, `height_cm`,
   `year`, `panels`, `status`, `price_eur`, `price_mode`, `signed`, `shape`) may stay out or be
   `null` and simply does not render.
3. Run `python tools/build.py`, check `http://localhost:8000/works/43/`, commit and push.

The counts on the site ("All 41 works", "{n} paintings") follow the data; never type a number
into a text.

## Confirming a title

Titles are shown only when the artist has confirmed them. In `data/works.json` set

    "title": {"en": "Shared Monsoon", "de": null}, "title_status": "confirmed"

Until then the painting is labelled by its number and subject line ("No. 13 · Couple under a
red umbrella …"). `build/REVIEW.csv` lists every painting with its subject, the proposed title
and the fields still open; it is the sheet to go through with the artist. To preview all
proposed titles at once, set `"show_proposed_titles": true` in `data/site.json` (not for
publishing).

## Filling in the legal data

Open `data/site.json`, section `legal`, and replace every `"TODO"`: `name`, `street`,
`postcode`, `city`, `email`, `vat_mode` (`"regular"` or `"kleinunternehmer"`),
`responsible_mstv`; add `phone`, `vat_id` and `retention_months` when known. The Impressum and
the Datenschutzerklärung (`/impressum/`, `/datenschutz/`) are rendered from these fields.
`python tools/build.py --deploy` refuses to finish while a `TODO` remains, so the site cannot
go online with an incomplete legal page by accident. A lawyer should read both pages once.

Other facts that only render when present: `facts.medium`, `facts.self_taught`, `bio`,
`artist_statement`, `whatsapp` (adds WhatsApp buttons), per-work `status`, `price_eur`,
`price_mode`, `instagram_url`.

## Running the checks

`python tools/check.py` runs on its own too. It checks byte budgets (home page, artwork pages,
inline and external CSS, scripts), identical keys in `strings.en.json` and `strings.de.json`,
banned words and literal digits in the texts, colour contrast of the design tokens and of every
painting's wall tints, broken internal links, `width`/`height`/`alt` on every image, and
canonical plus hreflang tags on every page. It prints one line per check and exits with an
error when something fails. Missing share cards, QR codes or icons are only a warning unless
`--deploy` is used.

## What is generated and what is edited by hand

Hand-edited (the sources of truth):

    data/works.json         the paintings (see above)
    data/rooms.json         the five rooms: slugs, names, wall texts, lead painting, order
    data/site.json          name, domain, Instagram, hero, proof plates, location, legal data, facts
    data/strings.en.json    every interface text, English
    data/strings.de.json    the same keys in German (the build fails if a key is missing on one side)
    sources/NN.jpg          the original photographs (never linked from a page)
    src/templates/          Jinja2 templates (base, pages, partials)
    src/css/                critical.css (inlined) and site.css (external)
    src/js/                 site.js, room.js (viewing room), show.js (exhibition mode)
    tools/                  build.py, check.py, images.py, fonts.py, og.py, qr.py, icons.py

Generated by `python tools/build.py` (do not edit; they are overwritten on the next build):

    index.html 404.html works/ rooms/ de/ enquire/ show/ impressum/ datenschutz/
    assets/                 hashed stylesheet and scripts
    images/r/               responsive AVIF and JPEG variants (images.py)
    images/qr/              QR codes for the exhibition mode (qr.py)
    og/                     share cards (og.py)
    fonts/                  self-hosted Fraunces and Instrument Sans (fonts.py, once)
    data/images.json        measured sizes, colours and placeholders per photograph
    sitemap.xml robots.txt manifest.webmanifest .nojekyll
    build/CHECKLIST.md      what is still open, per painting and for the site
    build/REVIEW.csv        the review sheet for the artist
    build/manifest.json     every generated path; stale files of a previous build are removed

If a text is missing in `data/strings.*.json`, the build takes it from
`src/templates/_strings_needed.json` and says so; copy those keys into the two strings files.

## How the pages are built

- Rooms and order come from each painting's `room` and `order`. The works page partitions each
  room into justified rows at a reference width of 1376 px (gap 32 px, target height 320 px);
  panoramas (`width ÷ height ≥ 2.2`) get a row of their own, two very tall or two low-resolution
  paintings never share a row, and the last row is not stretched.
- A painting is never shown wider than its photograph allows (`width ÷ 1.5` CSS px); when the
  cap binds it sits centred on a mat tinted with its own wall colour.
- Hero, room leads and the exhibition mode accept only photographs with a long edge of at least
  2400 px. Re-photographing a small source lifts the restriction automatically.
- The viewing room, the chips filter, the form states and the slideshow are progressive: every
  page works without JavaScript (plain links, a normal form post).
