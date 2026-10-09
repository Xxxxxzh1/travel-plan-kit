# The build pipeline

`scripts/build.py` is the entry point. It loads and validates the trip, checks
the environment, then dispatches to the generators.

```
trip.yaml
   │
   ├─ model.py ──────────── parses, validates, resolves id references
   │
   ├─ gen_itinerary.py ──── build_rows(trip, fmt) ──┬─► itinerary.md
   │                                                └─► itinerary.html
   ├─ browser.print_pdf() ─────────────────────────────► itinerary.pdf
   │
   ├─ ingest_tickets.py ─── normalise each ticket to JPEG
   ├─ gen_roadbook.py ───── build_data(trip) + assets ─► roadbook.html
   │
   └─ encrypt_roadbook.mjs ────────────────────────────► roadbook.enc.html
```

## The idea that holds it together

Every format renders from the same data. `gen_itinerary.build_rows()` returns
one dict per day, and the Markdown and HTML emitters both consume it — they take
a `fmt` argument that only changes how inline markup becomes text (spans vs
Markdown), never the structure.

That matters because the alternative was tried and failed. In the version this
tool replaced, the Markdown table and the HTML table were separate hand-edited
copies. They drifted: months after tickets for a museum had been purchased, one
of the two still said the museum was unbooked. Anything both documents must
agree on belongs in one place.

## Why there are no template-engine dependencies

Data-driven HTML is built with Python string assembly, and the two HTML
templates (`templates/itinerary.html`, `templates/roadbook.html`) use a plain
`@@TOKEN@@` replacement driven from `subs` dicts. No Jinja, no dependency
beyond PyYAML.

`templates/tokens.css` holds the shared design tokens and is **inlined** into
both templates at build time — the generated files must be self-contained.

Every renderer asserts that no `@@TOKEN@@` survives to the output:

```python
left = re.findall(r"@@[A-Z_]+@@", tpl)
if left:
    raise SystemExit(f"unsubstituted tokens: {set(left)}")
```

Keep that check. A silently unsubstituted token ships as visible litter.

## Chrome is the rendering engine

There is no wkhtmltopdf, weasyprint or pandoc on the machines this was built
for. Headless Chrome produces both PDFs and the PNG ticket images, and it
handles flexbox, grid, `@page` and `print-color-adjust` properly — all of which
matter here.

`scripts/browser.py` locates a Chromium-family binary (Chrome, Chromium, Edge,
Brave, or anything on `PATH`) and honours a `CHROME` environment override.

`browser.screenshot(..., trim=True)` crops the capture to the content bounding
box. Without it, a short ticket floats in dead whitespace, because headless
Chrome can only screenshot a fixed window size.

## Changing a template

1. Edit `templates/*.html` or `tokens.css`.
2. Rebuild the example: `python3 scripts/build.py examples/italy-switzerland/trip.yaml`
3. Check the specific output you touched:
   - **PDF**: `pdfinfo out/itinerary.pdf` — confirm `Pages` and that the page
     size is landscape A4 (`841.92 x 594.96 pts`). `pdfinfo` prints just `(A4)`
     either way, so read the numbers, not the label.
   - **Roadbook**: screenshots at a simulated 390px width. Remember headless
     Chrome clamps windows to ~500px, so inject
     `<style>html,body{width:390px!important}</style>` to actually get a phone
     layout.
4. Confirm it is still offline-capable:
   `grep -c 'src="http\|href="http' out/roadbook.html` must be `0`.

## Extending

A new output format is a new `gen_*.py` exposing `main(argv)`, called from
`build.py`. Follow the existing pattern: read the trip via `model.load()`, never
re-parse the YAML, and never inline a lodging object — always `trip.stay_for(day)`.
