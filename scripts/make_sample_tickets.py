#!/usr/bin/env python3
"""
make_sample_tickets.py — render fully synthetic ticket images for the example.

The example trip ships with ticket artwork, but shipping someone's real boarding
passes and museum QR codes in a public repo would leak live credentials. So the
example's tickets are *generated* instead: invented routes, invented booking
references, and a deliberate "SAMPLE DATA — NOT A REAL TICKET" stamp on every
one. Scanning them gets you nothing.

    python3 scripts/make_sample_tickets.py examples/italy-switzerland/trip.yaml
"""

from __future__ import annotations

import hashlib
import html as _html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import browser  # noqa: E402

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

WIDTH = 1050
SAMPLE_REF = "SAMPLE-%04d"

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Helvetica Neue",Helvetica,Arial,"PingFang SC",sans-serif;
     background:#eef1f4;padding:18px;color:#111}
.ticket{background:#fff;border-radius:10px;overflow:hidden;
        box-shadow:0 1px 3px rgba(0,0,0,.14);position:relative}
.head{display:flex;align-items:center;gap:10px;padding:13px 22px;color:#fff}
.head .carrier{font-size:17px;font-weight:800;letter-spacing:.6px}
.head .code{margin-left:auto;font-size:11.5px;font-family:Menlo,monospace;opacity:.9}
.body{padding:18px 22px 8px}
.route{display:flex;align-items:center;gap:14px;padding:6px 0 16px;border-bottom:1px dashed #d3d8de}
.route .st{flex:1}
.route .st.r{text-align:right}
.route .city{font-size:16px;font-weight:800;letter-spacing:.2px}
.route .time{font-size:26px;font-weight:800;font-variant-numeric:tabular-nums;margin-top:2px}
.route .mid{color:#9aa4b0;font-size:20px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px 10px;padding:15px 0}
.f .k{font-size:9.5px;letter-spacing:.9px;color:#8b95a3;text-transform:uppercase;font-weight:700}
.f .v{font-size:13.5px;font-weight:700;margin-top:3px}
.f .v.big{font-size:15px}
.rows{padding:2px 0 12px}
.row{display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #eef1f4;font-size:13px}
.row .lbl{width:130px;color:#8b95a3;font-weight:600;flex:none}
.row .val{font-weight:600}
.bar{padding:14px 22px 6px;display:flex;align-items:flex-end;gap:14px}
.bar .bars{display:flex;align-items:flex-end;gap:1.5px;height:44px}
.bar .bars i{display:block;background:#111;height:100%}
.bar .ref{font-family:Menlo,monospace;font-size:11px;color:#5b6673;padding-bottom:3px}
.stamp{padding:10px 22px 16px;font-size:10.5px;letter-spacing:1.6px;
       color:#c0392b;font-weight:800;text-align:center;border-top:1px dashed #d3d8de}
.wm{position:absolute;inset:0;pointer-events:none;overflow:hidden;display:grid;place-items:center}
.wm span{font-size:74px;font-weight:900;letter-spacing:12px;color:rgba(192,57,43,.075);
         transform:rotate(-20deg);white-space:nowrap}
.terms{padding:16px 22px 20px;font-size:11.5px;line-height:1.65;color:#5b6673}
.terms h3{font-size:12.5px;color:#111;margin-bottom:7px}
.terms li{margin-left:16px;margin-bottom:4px}
"""

PALETTE = {
    "train":    "#1c5f9e",
    "flight":   "#b3241f",
    "museum":   "#2d6a4f",
    "lodging":  "#3730a3",
}


def esc(s):
    return _html.escape(str(s or ""), quote=False)


def strip_markup(s):
    return re.sub(r"\*\*(.+?)\*\*", r"\1", str(s or ""))


def barcode(seed, n=56):
    h = hashlib.sha256(seed.encode()).digest()
    return "".join(f'<i style="width:{1 + (h[i % len(h)] % 3)}px"></i>' for i in range(n))


def page_shell(title, accent, inner, ref, page=None, total=None):
    tag = f" · 第 {page}/{total} 页" if total and total > 1 else ""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="ticket">
  <div class="head" style="background:{accent}">
    <span class="carrier">{esc(title)}</span>
    <span class="code">{esc(ref)}{esc(tag)}</span>
  </div>
  {inner}
  <div class="wm"><span>SAMPLE</span></div>
</div>
</body></html>"""


# ------------------------------------------------------------------ templates

def train_ticket(tk, day, transport, ref):
    sub = strip_markup(transport.get("sub", "")) if transport else tk.get("label", "")
    times = re.findall(r"\d{1,2}:\d{2}", sub)
    parts = [p.strip() for p in re.split(r"→", sub) if p.strip()]
    frm = re.sub(r"\s*\d{1,2}:\d{2}\s*$", "", parts[0]).strip() if parts else "—"
    to = re.sub(r"\s*\d{1,2}:\d{2}\s*$", "", parts[1]).strip() if len(parts) > 1 else "—"
    dep, arr = (times + ["—", "—"])[:2]
    date = day["date"] if day else "—"
    label = tk.get("label", "")
    number = ""
    m = re.search(r"\b([A-Z]{2,}\s?\d{2,5}|\d{4,5})\b", strip_markup(transport.get("title", "")) if transport else label)
    if m:
        number = m.group(1)
    meta = strip_markup(transport.get("meta", "")) if transport else ""

    inner = f"""
  <div class="body">
    <div class="route">
      <div class="st"><div class="city">{esc(frm)}</div><div class="time">{esc(dep)}</div></div>
      <div class="mid">→</div>
      <div class="st r"><div class="city">{esc(to)}</div><div class="time">{esc(arr)}</div></div>
    </div>
    <div class="grid">
      <div class="f"><div class="k">Date</div><div class="v">{esc(date)}</div></div>
      <div class="f"><div class="k">Train</div><div class="v big">{esc(number or '—')}</div></div>
      <div class="f"><div class="k">Coach</div><div class="v big">6</div></div>
      <div class="f"><div class="k">Seat</div><div class="v big">5 · 6</div></div>
      <div class="f"><div class="k">Class</div><div class="v">{esc(meta.split('·')[0].strip() if meta else '2nd')}</div></div>
      <div class="f"><div class="k">Passengers</div><div class="v">2 Adults</div></div>
      <div class="f"><div class="k">Fare</div><div class="v">SAMPLE</div></div>
      <div class="f"><div class="k">Status</div><div class="v" style="color:#2e7d32">Paid</div></div>
    </div>
  </div>
  <div class="bar">
    <div class="bars">{barcode(ref)}</div>
    <div class="ref">{esc(ref)}</div>
  </div>
  <div class="stamp">SAMPLE DATA — NOT A REAL TICKET</div>"""
    return page_shell(f"{tk.get('label','Train ticket')}", PALETTE["train"], inner, ref)


def flight_ticket(tk, day, transports, ref):
    legs = []
    for t in transports[:4]:
        sub = strip_markup(t.get("sub", ""))
        codes = re.findall(r"\(([A-Z]{3})\)", sub) or re.findall(r"\b([A-Z]{3})\b", sub)
        times = re.findall(r"\d{1,2}:\d{2}", sub)
        title = strip_markup(t.get("title", ""))
        legs.append((title, " → ".join(codes[:2]) or "—",
                     times[0] if times else "—", times[1] if len(times) > 1 else "—",
                     strip_markup(t.get("meta", ""))))
    rows = "".join(
        f"""<div class="row"><div class="lbl">{esc(a)}</div>
        <div class="val">{esc(b)}</div>
        <div class="val" style="margin-left:auto;font-variant-numeric:tabular-nums">{esc(c)} → {esc(d)}</div></div>"""
        for a, b, c, d, _ in legs
    )
    inner = f"""
  <div class="body">
    <div class="route">
      <div class="st"><div class="city">Hangzhou (HGH)</div><div class="time">00:10</div></div>
      <div class="mid">→</div>
      <div class="st r"><div class="city">Rome (FCO)</div><div class="time">20:05</div></div>
    </div>
    <div class="rows">{rows}</div>
    <div class="grid">
      <div class="f"><div class="k">Passengers</div><div class="v">2 Adults</div></div>
      <div class="f"><div class="k">Class</div><div class="v">Economy</div></div>
      <div class="f"><div class="k">Ticket No.</div><div class="v">{esc(ref)}</div></div>
      <div class="f"><div class="k">Status</div><div class="v" style="color:#2e7d32">Confirmed</div></div>
    </div>
  </div>
  <div class="bar">
    <div class="bars">{barcode(ref)}</div>
    <div class="ref">{esc(ref)}</div>
  </div>
  <div class="stamp">SAMPLE DATA — NOT A REAL TICKET</div>"""
    return page_shell("Emirates · E-Ticket Itinerary / 电子客票行程单",
                      PALETTE["flight"], inner, ref)


def museum_ticket(tk, day, ref):
    label = strip_markup(tk.get("label", ""))
    m = re.search(r"(\d{1,2}):(\d{2})", label)
    time_s = m.group(0) if m else "—"
    name = re.sub(r"\s*\d+/\d+\s*\d{1,2}:\d{2}\s*$", "", label).strip()
    date = day["date"] if day else "—"
    inner = f"""
  <div class="body">
    <div class="rows" style="padding-top:4px">
      <div class="row"><div class="lbl">Attraction</div><div class="val">{esc(name)}</div></div>
      <div class="row"><div class="lbl">Date</div><div class="val">{esc(date)}</div></div>
      <div class="row"><div class="lbl">Entry time</div>
        <div class="val" style="font-size:19px">{esc(time_s)}</div></div>
      <div class="row"><div class="lbl">Admission</div><div class="val">Reserved timed entry · 2 Adults</div></div>
      <div class="row"><div class="lbl">Booking ref.</div><div class="val">{esc(ref)}</div></div>
    </div>
    <div class="grid">
      <div class="f"><div class="k">Ticket type</div><div class="v">Full price</div></div>
      <div class="f"><div class="k">Entry point</div><div class="v">Main entrance</div></div>
      <div class="f"><div class="k">Valid</div><div class="v">Single entry</div></div>
      <div class="f"><div class="k">Status</div><div class="v" style="color:#2e7d32">Paid</div></div>
    </div>
  </div>
  <div class="bar">
    <div class="bars">{barcode(ref)}</div>
    <div class="ref">{esc(ref)}</div>
  </div>
  <div class="stamp">SAMPLE DATA — NOT A REAL TICKET</div>"""
    return page_shell("Reserved Timed Entry Ticket", PALETTE["museum"], inner, ref)


def lodging_ticket(tk, stay, ref):
    stay = stay or {}
    ci, co = stay.get("checkin") or {}, stay.get("checkout") or {}
    host = stay.get("host")
    rows = [
        ("Property type", stay.get("type_en") or stay.get("type") or "Accommodation"),
        ("Host", host or "—"),
        ("Address", stay.get("address", "—")),
        ("Check-in", f"{ci.get('date','—')}  {ci.get('time','')}".strip()),
        ("Check-out", f"{co.get('date','—')}  {co.get('time','')}".strip()),
        ("Nights", str(stay.get("nights", "—"))),
    ]
    body = "".join(
        f'<div class="row"><div class="lbl">{esc(k)}</div><div class="val">{esc(v)}</div></div>'
        for k, v in rows
    )
    inner = f"""
  <div class="body">
    <div class="rows" style="padding-top:4px">{body}</div>
    <div class="grid">
      <div class="f"><div class="k">Guests</div><div class="v">2 Adults</div></div>
      <div class="f"><div class="k">Booking ref.</div><div class="v">{esc(ref)}</div></div>
      <div class="f"><div class="k">Payment</div><div class="v" style="color:#2e7d32">Paid in full</div></div>
      <div class="f"><div class="k">Platform</div><div class="v">{esc(stay.get('platform','—'))}</div></div>
    </div>
  </div>
  <div class="bar">
    <div class="bars">{barcode(ref)}</div>
    <div class="ref">{esc(ref)}</div>
  </div>
  <div class="stamp">SAMPLE DATA — NOT A REAL BOOKING</div>"""
    return page_shell("Booking Confirmation / 预订确认单", PALETTE["lodging"], inner, ref)


def terms_page(tk, ref):
    inner = f"""
  <div class="terms">
    <h3>Conditions of carriage — sample page {esc(ref)}</h3>
    <p>This page exists so that multi-page tickets are represented faithfully in
       the generated roadbook (a real 5-page rail ticket should show as five
       pages, not one).</p>
    <ul>
      <li>Tickets must be validated before boarding where required.</li>
      <li>Passengers should present the digital or printed ticket on request.</li>
      <li>This document is generated sample data and confers no right to travel.</li>
      <li>No real booking reference, QR code or barcode is contained here.</li>
    </ul>
  </div>
  <div class="stamp">SAMPLE DATA — NOT A REAL TICKET</div>"""
    return page_shell("Terms &amp; Conditions (sample)", "#6b7280", inner, ref)


# ------------------------------------------------------------------ driver

def build_index(raw):
    """Map ticket id -> (day, [transports]) and lodging id -> stay."""
    by_ticket, stays = {}, {}
    for stay in raw.get("lodging") or []:
        for tid in stay.get("tickets") or []:
            stays[tid] = stay
    for day in raw.get("days") or []:
        for cat, ids in (day.get("tickets") or {}).items():
            for tid in ids or []:
                by_ticket.setdefault(tid, (day, day.get("transport") or []))
    return by_ticket, stays


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    trip_path = argv[1]
    base = os.path.dirname(os.path.abspath(trip_path))

    with open(trip_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    err = browser.find()
    if not err:
        print("error: no Chromium-family browser found (needed to render tickets)",
              file=sys.stderr)
        return 1

    by_ticket, stays = build_index(raw)
    made = 0
    for i, tk in enumerate(raw.get("tickets") or [], 1):
        tid = tk.get("id")
        files = tk.get("files") or ([tk["file"]] if tk.get("file") else [])
        day, transports = by_ticket.get(tid, (None, []))
        ref = SAMPLE_REF % (i * 7 % 10000)

        for page_no, rel in enumerate(files, 1):
            out = os.path.join(base, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if page_no > 1:
                html, h = terms_page(tk, f"{ref}-p{page_no}"), 520
            elif tid in stays:
                html, h = lodging_ticket(tk, stays[tid], ref), 620
            elif (tk.get("category") or "") == "scenic":
                html, h = museum_ticket(tk, day, ref), 600
            elif tid == "flight":
                html, h = flight_ticket(tk, day, transports, ref), 720
            else:
                match = None
                for t in transports:
                    if strip_markup(t.get("title", "")) and strip_markup(t["title"])[:6] in strip_markup(tk.get("label", "")):
                        match = t
                        break
                html, h = train_ticket(tk, day, match or (transports[0] if transports else {}), ref), 560
            browser.screenshot(html, out, WIDTH, h, scale=2, trim=True)
            made += 1
            print(f"  {rel}")

    print(f"\n{made} sample ticket image(s) written under {base}/tickets")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
