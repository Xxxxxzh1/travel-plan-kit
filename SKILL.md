---
name: travel-plan-kit
description: "Turn one trip.yaml into a full set of travel documents: a Markdown itinerary table, a print-ready styled HTML/PDF, and a mobile roadbook (路书) — a single self-contained HTML file with every ticket image embedded, so it opens on a phone with no network. Optionally emits a password-encrypted roadbook (AES-256-GCM) safe to host on a public GitHub Pages site. Use when the user wants a travel itinerary, roadbook, 路书, 行程单, 行程规划文档, wants to organise flight/train/hotel tickets into something readable, or wants a phone-friendly offline page for a trip. Requires: Python 3 + PyYAML; Chrome/Chromium for PDF and ticket rendering; Node for the encrypted variant."
version: 1.0.0
license: MIT
homepage: https://github.com/Janz/travel-plan-kit
metadata:
  author: Janz
---

# travel-plan-kit

One declarative `trip.yaml` is the single source of truth. Everything else is
generated from it, so the Markdown, the HTML, the PDF and the mobile roadbook
can never contradict each other.

```
trip.yaml ──► itinerary.md      master table
          ──► itinerary.html    styled, landscape A4
          ──► itinerary.pdf     printed / handed to a border officer
          ──► roadbook.html     mobile, offline, tickets embedded
          ──► roadbook.enc.html password-encrypted (optional)
```

## When to use this

Trigger on: travel itinerary, roadbook, 路书, 行程单, trip plan document, "turn
my tickets into something I can read on my phone", "make a printable itinerary",
"plan out this trip".

Do **not** reach for this for a one-off table — a plain Markdown list is fine if
the user just wants to see their dates.

## Workflow

### 1. Gather the trip, then write `trip.yaml`

Do not start generating until you have the itinerary. Ask for whatever is
missing rather than inventing it — dates, cities, transport legs, lodging, and
which tickets exist as files.

Write the file next to the user's tickets. Start from `trip.example.yaml` at the
repo root, or copy `examples/italy-switzerland/trip.yaml` for a fuller model.

The schema is documented in `references/data-model.md`. The two decisions worth
getting right up front:

- **`lodging` is a top-level list; a day references it by `id`.** Never inline a
  stay into each day — a three-night stay would then exist in three places.
- **`tickets` is a top-level list; a day references ticket `id`s.** The caption
  lives once, on the ticket.

### 2. Validate before building

```bash
python3 scripts/model.py path/to/trip.yaml
```

This catches the mistakes that actually happen: a `nights` count that disagrees
with the check-in/check-out dates, a day pointing at a lodging id that does not
exist, a ticket id with no file behind it, dates out of order. Fix everything it
reports; it lists all problems at once rather than stopping at the first.

### 3. Build

```bash
python3 scripts/build.py path/to/trip.yaml                       # md + html + pdf + roadbook
python3 scripts/build.py path/to/trip.yaml --encrypt 'passphrase' # + encrypted roadbook
python3 scripts/build.py path/to/trip.yaml --skip pdf             # skip if no Chrome
```

Outputs land in `<trip dir>/out/`. The script self-checks the environment first
and tells you exactly what is missing rather than failing halfway through.

### 4. Deliver

- `itinerary.pdf` — print it. Give the traveller a copy per person; border
  officers sometimes question people separately.
- `roadbook.html` — this is the one that matters in the field. It is a single
  file with every ticket embedded; the traveller opens it with no signal.
- `roadbook.enc.html` — if they want it reachable from anywhere, host it. See
  "Hosting" below.

## Hosting an encrypted roadbook

The roadbook contains live ticket QR codes, so it should not simply be dropped
on a public site. Two hard-won facts:

- **GitHub Pages sites are always public on free and Pro plans.** Publishing
  Pages *privately* requires GitHub Enterprise Cloud. A private repository does
  **not** give you a private site.
- A JavaScript "enter password" overlay over plaintext data is theatre — view
  source and the tickets are right there.

`--encrypt` therefore encrypts the whole payload (itinerary, lodging, and every
ticket image) with AES-256-GCM under a PBKDF2-derived key, gzip-compressed
first so the base64 framing isn't paid twice. The file is inert without the
password, so it is safe in a public repo.

**Say this to the user plainly:** encryption strength equals password strength.
The default 400,000 PBKDF2 iterations make each guess cost something, but a
dictionary word is still a dictionary word. Recommend a passphrase. And note the
trade-off — an encrypted roadbook needs a network connection to fetch the file;
an unencrypted one they AirDropped works on a plane.

## Gotchas worth knowing

These cost real time to discover. Do not re-learn them.

- **iOS will not open a local HTML file in Safari.** There is no browser
  registered for the `file://` HTML type, so "Open in…" never offers Safari. To
  use a local roadbook on an iPhone the user needs a file manager with a built-in
  browser (Documents by Readdle, Alook), or the file must be hosted.
- **Headless Chrome clamps its window to ~500px wide.** To check a 390px phone
  layout, inject `<style>html,body{width:390px!important}</style>` rather than
  trusting `--window-size`.
- **Headless Chrome's virtual clock does not wait for Web Crypto.** Never verify
  the encrypted roadbook with `--screenshot`; it will capture a half-decrypted
  page. Drive Chrome over CDP and poll for completion instead.
- **YAML turns `2027-09-24` into a `date` object**, which is not JSON
  serialisable. `model.py` normalises these to strings; keep it that way.
- **Chrome is the only rendering engine that works here.** There is no
  wkhtmltopdf/weasyprint/pandoc on the machines this was built for, and headless
  Chrome handles flexbox, grid and `@page` far better anyway.

## References

| Read this | When |
|---|---|
| `references/data-model.md` | writing or editing a `trip.yaml` — every field, with examples |
| `references/build-pipeline.md` | changing a template, or debugging a broken output |
| `references/ticket-ingest.md` | tickets are PDFs / photos / wrong size, or the roadbook is too big |

## Repository layout

```
SKILL.md  README.md  LICENSE  trip.example.yaml
schema/trip.schema.json      machine-readable schema for editors
scripts/                     model.py, build.py, gen_*.py, ingest_tickets.py, browser.py
templates/                   tokens.css, itinerary.html, roadbook.html
references/                  the detail behind the three topics above
examples/italy-switzerland/  a complete, fully synthetic worked example
```

## Verifying your changes

After touching a template or generator, rebuild the built-in example and check
it still behaves:

```bash
python3 scripts/build.py examples/italy-switzerland/trip.yaml
grep -c 'src="http' examples/italy-switzerland/out/roadbook.html   # must be 0 (offline)
```

Then open `out/roadbook.html` and confirm the day cards, the ticket drawer and
the lightbox all still work. The example's tickets are generated by
`scripts/make_sample_tickets.py` and are deliberately synthetic — never replace
them with real ticket images in a repo you intend to publish.
