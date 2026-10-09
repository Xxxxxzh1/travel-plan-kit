#!/usr/bin/env python3
"""
gen_itinerary.py — emit the master itinerary as Markdown and as a styled HTML
table.

Both formats render from the *same* `build_rows()` result. That is deliberate:
in the hand-maintained version of these documents, the Markdown and the HTML
were separate hand-edited copies of the same table, and they drifted — one of
them still claimed a museum was unbooked months after tickets had been bought.

    python3 scripts/gen_itinerary.py <trip.yaml> --out DIR
"""

from __future__ import annotations

import argparse
import html as _html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model  # noqa: E402

TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")

COLUMNS = ["日期", "城市", "时间段", "行程内容",
           "交通（车票 / 起终站 / 发车时刻）", "当天住宿（名称 + 地址）",
           "天气和穿衣", "票附件"]


def _md_escape(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def build_rows(trip, fmt="html"):
    """One dict per day — the single source both emitters render from.

    `fmt` picks how the authoring markup is rendered: `html` produces spans,
    `md` produces Markdown. The *structure* is shared; only the inline markup
    conversion differs, so the two documents cannot drift apart.
    """
    conv = model.inline if fmt == "html" else model.to_md
    bold = (lambda s: f"<b>{s}</b>") if fmt == "html" else (lambda s: f"**{s}**")

    rows = []
    for day in trip.days:
        stay = trip.stay_for(day)

        slots = day["slots"] or []
        slot_keys = "<br>".join(conv(s.get("key", "")) for s in slots)
        slot_body = "<br>".join(
            (f'{s.get("icon","")} ' if s.get("icon") else "") + conv(s.get("text"))
            for s in slots
        )

        transport_lines = []
        for t in day["transport"] or []:
            bits = [f'{t.get("icon","")} {bold(conv(t.get("title","")))}']
            sub = conv(t.get("sub", ""))
            if sub:
                bits.append(f"：{sub}")
            meta = conv(t.get("meta", ""))
            if meta:
                bits.append(f"｜{meta}")
            transport_lines.append("".join(bits))

        if stay:
            stay_bits = [bold(conv(stay["_name"]))]
            stay_bits.append(f'📍{conv(stay.get("address",""))}')
            ci = stay.get("checkin") or {}
            co = stay.get("checkout") or {}
            when = []
            if ci.get("time"):
                when.append(f'入住 {ci["time"]}')
            if co.get("time"):
                when.append(f'退房 {co["time"]}')
            if when:
                stay_bits.append(" · ".join(when))
            if stay.get("note"):
                stay_bits.append(bold(conv(stay["note"])))
            stay_cell = "<br>".join(stay_bits)
        else:
            stay_cell = "—（当日离境）"

        files = [os.path.relpath(e["file"], trip.base_dir) for e in trip.ticket_list(day)]
        ticket_cell = "<br>".join(files) if files else "—（当日无预订票）"

        weather = day.get("weather") or {}
        weather_cell = "<br>".join(
            x for x in [weather.get("temp", ""), weather.get("wear", "")] if x
        )

        rows.append({
            "day": day,
            "no": day["n"],
            "date": day["label"],
            "wd": day["wd"],
            "city": day["city"],
            "country": day["country"],
            "slot_keys": slot_keys,
            "slot_body": slot_body,
            "transport_lines": transport_lines,
            "stay": stay,
            "stay_cell": stay_cell,
            "weather_cell": weather_cell,
            "ticket_cell": ticket_cell,
            "ticket_count": len(files),
        })
    return rows


# ------------------------------------------------------------------ Markdown

def emit_md(trip, rows):
    out = []
    title = f'{trip.emoji} {trip.title_zh or trip.title} 旅行计划'.strip()
    out.append(f"# {title}")
    nights = trip.nights_total
    span = f"{trip.start:%Y/%m/%d} — {trip.end:%m/%d}"
    who = " · ".join(trip.travelers)
    out.append(f"**{span} · {nights + 1}天{nights}晚 · 旅行者：{who}**")

    entry, exit_ = trip.summary.get("entry") or {}, trip.summary.get("exit") or {}
    if entry or exit_:
        parts = []
        if entry:
            parts.append(f'去程 {entry.get("date","")} {entry.get("flight","")} '
                         f'{entry.get("place","")} {entry.get("time","")}'.strip())
        if exit_:
            parts.append(f'回程 {exit_.get("date","")} {exit_.get("flight","")} '
                         f'{exit_.get("place","")} {exit_.get("time","")}'.strip())
        out.append("✈️ " + " ｜ ".join(parts))
    if trip.summary.get("status"):
        out.append("✅ " + trip.summary["status"])
    out.append("")

    out.append("| " + " | ".join(COLUMNS) + " |")
    out.append("|" + "---|" * len(COLUMNS))
    for r in rows:
        date_cell = f'**{r["date"]} {r["wd"]}**<br>Day {r["no"]}'
        out.append("| " + " | ".join(_md_escape(c) for c in [
            date_cell, r["city"], r["slot_keys"], r["slot_body"],
            "<br>".join(r["transport_lines"]) or "—",
            r["stay_cell"], r["weather_cell"] or "—", r["ticket_cell"],
        ]) + " |")
    out.append("")

    alerts = [n for n in trip.notes if (n.get("level") or "") in ("red", "warn")]
    todos = [n for n in trip.notes if (n.get("level") or "") == "todo"]
    others = [n for n in trip.notes if (n.get("level") or "") not in ("red", "warn", "todo")]

    if alerts or others:
        out.append("## ⚠️ 重要提醒")
        out.append("")
        for n in alerts + others:
            out.append("- " + model.to_md(str(n.get("text", ""))).replace("<br>", " "))
        out.append("")
    if todos:
        out.append("## ✅ 行前 To-Do")
        out.append("")
        for n in todos:
            out.append("- [ ] " + model.to_md(str(n.get("text", ""))))
        out.append("")

    if trip.footer:
        out.append("---")
        out.append("")
        out.append("*" + trip.footer.replace("<br>", " ") + "*")
        out.append("")

    return "\n".join(out)


# ---------------------------------------------------------------------- HTML

def _cell(text, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f"<td{c}>{text}</td>"


def rows_html(trip, rows):
    out = []
    for r in rows:
        day_cls = "it" if r["country"] == "it" else ("ch" if r["country"] == "ch" else "")
        out.append(f'<tr class="row-{day_cls}">')
        out.append(_cell(f'<b>{_html.escape(r["date"])}</b> {_html.escape(r["wd"])}'
                         f'<span class="dn">Day {r["no"]}</span>', "c-date"))
        out.append(_cell(_html.escape(r["city"]), "c-city"))
        out.append(_cell(r["slot_keys"], "c-slot"))
        out.append(_cell(r["slot_body"], "c-plan"))
        out.append(_cell("<br>".join(r["transport_lines"]) or "—", "c-trans"))
        out.append(_cell(r["stay_cell"], "c-stay"))
        out.append(_cell(r["weather_cell"] or "—", "c-weather"))
        out.append(_cell(r["ticket_cell"], "c-file"))
        out.append("</tr>")
    return "\n".join(out)


def notes_html(trip):
    def note(n):
        lvl = n.get("level") or ""
        return (f'<div class="note {lvl}"><span class="b"></span>'
                f'<span>{model.inline(n.get("text",""))}</span></div>')
    alerts = [n for n in trip.notes if (n.get("level") or "") in ("red", "warn", "")]
    todos = [n for n in trip.notes if (n.get("level") or "") == "todo"]
    parts = []
    if alerts:
        parts.append("<h3>⚠️ 重要提醒 / Important</h3>")
        parts.append('<div class="cols">' + "".join(note(n) for n in alerts) + "</div>")
    if todos:
        parts.append("<h3>✅ 行前 To-Do / Checklist</h3>")
        parts.append('<div class="cols">' + "".join(note(n) for n in todos) + "</div>")
    return "\n".join(parts)


def emit_html(trip, rows):
    tpl_path = os.path.join(TEMPLATES, "itinerary.html")
    with open(tpl_path, encoding="utf-8") as fh:
        tpl = fh.read()
    with open(os.path.join(TEMPLATES, "tokens.css"), encoding="utf-8") as fh:
        tpl = tpl.replace("/* @@TOKENS@@ */", fh.read())

    entry, exit_ = trip.summary.get("entry") or {}, trip.summary.get("exit") or {}
    flight_bits = []
    if entry:
        flight_bits.append(f'去程 <b>{entry.get("date","")}</b> {_html.escape(str(entry.get("flight","")))} '
                           f'{_html.escape(str(entry.get("place","")))} {entry.get("time","")}')
    if exit_:
        flight_bits.append(f'回程 <b>{exit_.get("date","")}</b> {_html.escape(str(exit_.get("flight","")))} '
                           f'{_html.escape(str(exit_.get("place","")))} {exit_.get("time","")}')

    subs = {
        "@@TITLE@@": _html.escape(f'{trip.title_zh or trip.title}'),
        "@@TITLE_EN@@": _html.escape(trip.title),
        "@@SPAN@@": f'{trip.start:%Y.%m.%d} — {trip.end:%m.%d}',
        "@@LEN@@": f'{trip.nights_total + 1} 天 {trip.nights_total} 晚',
        "@@WHO@@": _html.escape(" · ".join(trip.travelers)),
        "@@FLIGHTS@@": " ｜ ".join(flight_bits),
        "@@STATUS@@": _html.escape(str(trip.summary.get("status", ""))),
        "@@COLS@@": "".join(f"<th>{_html.escape(c)}</th>" for c in COLUMNS),
        "@@ROWS@@": rows_html(trip, rows),
        "@@NOTES@@": notes_html(trip),
        "@@FOOTER@@": trip.footer,
    }
    for k, v in subs.items():
        tpl = tpl.replace(k, v)
    left = re.findall(r"@@[A-Z_]+@@", tpl)
    if left:
        raise SystemExit(f"unsubstituted tokens in template: {set(left)}")
    return tpl


# -------------------------------------------------------------------- driver

def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("trip")
    ap.add_argument("--out", default=None, help="output dir (default: <trip dir>/out)")
    ap.add_argument("--name", default="itinerary", help="output basename")
    args = ap.parse_args(argv[1:])

    trip = model.load(args.trip)
    out_dir = args.out or os.path.join(trip.base_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    rows_md = build_rows(trip, "md")
    rows_html = build_rows(trip, "html")

    md_path = os.path.join(out_dir, args.name + ".md")
    html_path = os.path.join(out_dir, args.name + ".html")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(emit_md(trip, rows_md))
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(emit_html(trip, rows_html))

    print(f"  {os.path.relpath(md_path, trip.base_dir)}")
    print(f"  {os.path.relpath(html_path, trip.base_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
