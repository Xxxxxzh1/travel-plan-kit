#!/usr/bin/env python3
"""
gen_roadbook.py — build the mobile roadbook: a single self-contained HTML file
with every ticket image embedded, so it opens on a phone with no network.

Two things here are worth knowing about:

* Tickets are embedded as base64 data URIs. That makes the file big, but it is
  the whole point — abroad, on a train, in an alpine valley, the page still
  works. It is also why ticket images get normalised first (see
  ingest_tickets.py): raw airline PDFs would balloon this to tens of MB.

* `days[].lodging` stays an id reference and `tickets` are referenced by slug.
  The renderer looks them up at runtime, so a three-night stay and a rail pass
  used on three days are each stored once.

    python3 scripts/gen_roadbook.py <trip.yaml> --out DIR
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest_tickets  # noqa: E402
import model  # noqa: E402

TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")

BADGE_CLASS = {"已购": "bdg-ok", "现场": "bdg-wn", "补票": "bdg-rd",
               "paid": "bdg-ok", "onsite": "bdg-wn", "topup": "bdg-rd"}
TRAIN_ICONS = {"🚄", "🚞", "🚊", "🚉", "🚅"}


def _flags(s):
    """Split a run of regional-indicator pairs into individual flag emoji."""
    return re.findall(r"[\U0001F1E6-\U0001F1FF]{2}", s or "")


def build_hero(trip):
    n = len(trip.days)
    flags = _flags(trip.emoji)
    if len(flags) >= 2:
        title = f"{flags[0]} {trip.title_zh or trip.title} {n}日路书 {flags[-1]}"
    else:
        title = f"{trip.emoji} {trip.title_zh or trip.title} {n}日路书".strip()

    explicit = trip.hero.get("meta")
    if explicit:
        meta = explicit
    else:
        route = trip.meta.get("route")
        if not route:
            route = []
            for d in trip.days:
                last = re.sub(r"（.*?）", "", str(d["city"]).split("→")[-1]).strip()
                if last and (not route or route[-1] != last):
                    route.append(last)
        meta = (f"{trip.start:%Y.%m.%d} — {trip.end:%m.%d} · " + " → ".join(route))

    stats = trip.hero.get("stats")
    if not stats:
        trains = sum(
            1 for d in trip.days for t in (d["transport"] or [])
            if t.get("icon") in TRAIN_ICONS
        )
        stats = [f"🗓 {n} 天 {trip.nights_total} 晚", f"🚄 {trains} 段列车"]

    return {
        "title": title,
        "meta": meta,
        "who": trip.hero.get("who") or [],
        "stats": stats,
    }


def build_data(trip, assets, cache_dir):
    days = []
    for d in trip.days:
        tickets = {c: [] for c in model.VALID_TICKET_CATEGORIES}
        for e in trip.ticket_list(d):
            tickets[e["category"]].append(e["slug"])

        weather = d.get("weather") or {}
        days.append({
            "n": d["n"],
            "date": d["date"],
            "label": d["label"],
            "wd": d["wd"],
            "city": d["city"],
            "country": d["country"],
            "weather": {"t": weather.get("temp", ""), "wear": weather.get("wear", ""),
                        "cold": bool(weather.get("cold"))},
            "slots": [{"k": s.get("key", ""), "i": s.get("icon", ""),
                       "v": model.inline(s.get("text", ""))} for s in (d["slots"] or [])],
            "transport": [{
                "icon": t.get("icon", ""),
                "title": t.get("title", ""),
                "sub": model.inline(t.get("sub", "")),
                "meta": model.inline(t.get("meta", "")),
                "badge": t.get("badge", ""),
                "badgeC": BADGE_CLASS.get(t.get("badge", ""), "bdg-ok"),
            } for t in (d["transport"] or [])],
            "lodging": d.get("lodging") or None,
            "tickets": tickets,
        })

    lodging = {}
    for sid, s in trip.lodging.items():
        ci, co = s.get("checkin") or {}, s.get("checkout") or {}
        bits = []
        if ci.get("time"):
            bits.append(f'入住 {ci["time"]}')
        if co.get("time"):
            bits.append(f'退房 {co["time"]}')
        if s.get("nights"):
            bits.append(f'{s["nights"]} 晚')
        lodging[sid] = {
            "name": s["_name"],
            "address": s.get("address", ""),
            "map": s.get("map_query", ""),
            "checkin": ci,
            "checkout": co,
            "checkinTime": " · ".join(bits),
            "nights": s.get("nights"),
            "note": s.get("note", ""),
            "phone": s.get("phone", ""),
        }

    tickets = {}
    for tid, tk in trip.tickets.items():
        n = len(tk["_files"])
        for idx in range(n):
            tickets[f"{tid}_{idx}"] = {
                "label": tk.get("label") or tid,
                "category": tk["category"],
                "page": idx + 1,
                "pages": n,
            }

    notes = []
    for nt in trip.notes:
        lvl = nt.get("level") or ""
        notes.append({"c": "red" if lvl == "red" else ("todo" if lvl == "todo" else ""),
                      "v": model.inline(nt.get("text", ""))})

    exit_ = trip.summary.get("exit") or {}
    departure = trip.meta.get("departure_note") or (
        f'{exit_.get("date","")} {exit_.get("place","")} {exit_.get("time","")} 起飞'.strip()
        if exit_ else "")

    return {
        "start": trip.start.isoformat(),
        "end": trip.end.isoformat(),
        "hero": build_hero(trip),
        "days": days,
        "lodging": lodging,
        "tickets": tickets,
        "notes": notes,
        "foot": trip.footer,
        "departureNote": departure,
        "countries": trip.countries(),
        "countryNames": trip.meta.get("countries") or {},
    }


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("trip")
    ap.add_argument("--out", default=None, help="output dir (default: <trip dir>/out)")
    ap.add_argument("--name", default="roadbook.html")
    ap.add_argument("--width", type=int, default=ingest_tickets.DEFAULT_MAX_WIDTH)
    ap.add_argument("--quality", type=int, default=ingest_tickets.DEFAULT_QUALITY)
    args = ap.parse_args(argv[1:])

    for line in ingest_tickets.describe_capabilities():
        print(line)

    trip = model.load(args.trip)
    out_dir = args.out or os.path.join(trip.base_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    cache_dir = os.path.join(trip.base_dir, ".cache", "tickets")

    assets = {}
    for day in trip.days:
        for e in trip.ticket_list(day):
            if e["slug"] in assets:
                continue
            pages = ingest_tickets.normalize(e["file"], cache_dir, args.width, args.quality)
            idx = e["page"] - 1
            src = pages[idx] if idx < len(pages) else pages[0]
            assets[e["slug"]] = ingest_tickets.data_uri(src)

    data = build_data(trip, assets, cache_dir)

    with open(os.path.join(TEMPLATES, "roadbook.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    with open(os.path.join(TEMPLATES, "tokens.css"), encoding="utf-8") as fh:
        tpl = tpl.replace("/* @@TOKENS@@ */", fh.read())
    tpl = tpl.replace("@@TITLE@@", trip.title_zh or trip.title)

    tpl = tpl.replace("/* @@ASSETS@@ */",
                      "const ASSETS = " + json.dumps(assets, ensure_ascii=False).replace("</", "<\\/") + ";")
    tpl = tpl.replace("/* @@DATA@@ */",
                      "const TRIP = " + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";")

    left = re.findall(r"@@[A-Z_]+@@", tpl)
    if left:
        raise SystemExit(f"unsubstituted tokens: {set(left)}")

    out_path = os.path.join(out_dir, args.name)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(tpl)

    print(f"  {os.path.relpath(out_path, trip.base_dir)}  "
          f"({os.path.getsize(out_path)/1048576:.1f} MB, {len(assets)} ticket image(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
