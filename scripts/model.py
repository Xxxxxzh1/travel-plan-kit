#!/usr/bin/env python3
"""
model.py — the single source of truth for a trip.

Loads a trip.yaml (or .json), normalises it, validates it, and resolves the
cross-references that keep a trip from being duplicated across outputs.

The important design decision here: `days[].lodging` holds an *id reference*
into the top-level `lodging` list, not an inlined copy. A stay that spans three
nights is stored once. Inlining it (as an earlier hand-rolled version of this
tool did) means the same address lives in three places and every edit has to be
made three times.

Authoring markup, kept deliberately tiny so user text is never raw HTML:
    **highlighted**   -> <span class="hl">highlighted</span>
    !!attention!!     -> <span class="warn">attention</span>
Everything else is HTML-escaped.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - surfaced as a friendly message
    yaml = None

WD_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
VALID_TICKET_CATEGORIES = ("transport", "scenic", "stay")


class TripError(Exception):
    """One or more problems with the trip file. `problems` holds them all."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("\n".join("  - " + p for p in self.problems))


# ---------------------------------------------------------------- utilities

def _parse_date(value, where, problems):
    if isinstance(value, _dt.date):
        return value
    try:
        return _dt.date.fromisoformat(str(value))
    except ValueError:
        problems.append(f"{where}: {value!r} is not an ISO date (expected YYYY-MM-DD)")
        return None


_BR = "\x00BR\x00"


def inline(text):
    """Render authoring markup to safe HTML. Everything else gets escaped.

    `<br>` is the one HTML tag authors are allowed to write, so it is held
    aside across the escaping pass rather than being escaped into literal text.
    """
    if text is None:
        return ""
    out = str(text).replace("<br>", _BR).replace("<br/>", _BR).replace("<br />", _BR)
    out = html.escape(out, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r'<span class="hl">\1</span>', out)
    out = re.sub(r"!!(.+?)!!", r'<span class="warn">\1</span>', out)
    return out.replace(_BR, "<br>")


def to_md(text):
    """Render authoring markup for Markdown.

    `**highlight**` is already valid Markdown bold, so it passes through
    unchanged. `!!attention!!` has no Markdown equivalent, so it gains a
    warning sign to keep the distinction visible in plain text.
    """
    if text is None:
        return ""
    return re.sub(r"!!(.+?)!!", r"**⚠ \1**", str(text))


def plain(text):
    """Strip authoring markup, for text-only contexts (captions, filenames)."""
    if text is None:
        return ""
    out = re.sub(r"\*\*(.+?)\*\*", r"\1", str(text))
    return re.sub(r"!!(.+?)!!", r"\1", out)


def _req(obj, key, where, problems, kind=None):
    if key not in obj or obj[key] in (None, "", []):
        problems.append(f"{where}: missing required field {key!r}")
        return None
    val = obj[key]
    if kind and not isinstance(val, kind):
        problems.append(f"{where}: {key!r} should be {kind.__name__}, got {type(val).__name__}")
        return None
    return val


# ---------------------------------------------------------------- the model

class Trip:
    def __init__(self, raw, base_dir):
        self.raw = raw
        self.base_dir = os.path.abspath(base_dir)
        self.problems: list[str] = []
        self._build()
        self._validate()
        if self.problems:
            raise TripError(self.problems)

    # -- construction ------------------------------------------------------

    def _build(self):
        p = self.problems
        raw = self.raw
        if not isinstance(raw, dict):
            raise TripError(["trip file must be a mapping at the top level"])

        self.meta = raw.get("meta") or {}
        _req(self.meta, "start", "meta", p)
        _req(self.meta, "end", "meta", p)

        self.start = _parse_date(self.meta.get("start"), "meta.start", p)
        self.end = _parse_date(self.meta.get("end"), "meta.end", p)

        self.title = self.meta.get("title") or "Trip"
        self.title_zh = self.meta.get("title_zh") or ""
        self.slug = self.meta.get("slug") or "trip"
        self.travelers = self.meta.get("travelers") or []
        self.emoji = self.meta.get("emoji") or ""

        self.summary = raw.get("summary") or {}
        self.flights = raw.get("flights") or []
        self.notes = raw.get("notes") or []
        self.footer = raw.get("footer") or ""
        self.hero = raw.get("hero") or {}

        # lodging: list -> dict keyed by id (stored once, referenced many times)
        self.lodging: dict[str, dict] = {}
        for i, stay in enumerate(raw.get("lodging") or []):
            where = f"lodging[{i}]"
            sid = _req(stay, "id", where, p)
            if sid is None:
                continue
            if sid in self.lodging:
                p.append(f"{where}: duplicate lodging id {sid!r}")
                continue
            stay = dict(stay)
            stay["_where"] = where
            for key in ("checkin", "checkout"):
                when = stay.get(key)
                if isinstance(when, dict):
                    when = dict(when)
                    parsed = _parse_date(when.get("date"), f"{where}.{key}.date", p)
                    if parsed:
                        # YAML hands back a date object; normalise to a string so
                        # the value survives the trip into JSON.
                        when["date"] = parsed.isoformat()
                    stay[key] = when
                elif when is not None and not isinstance(when, dict):
                    p.append(f"{where}.{key}: expected a mapping like {{date, time}}")
            stay["_checkin"] = _parse_date((stay.get("checkin") or {}).get("date"),
                                           f"{where}.checkin.date", p)
            stay["_checkout"] = _parse_date((stay.get("checkout") or {}).get("date"),
                                            f"{where}.checkout.date", p)
            _req(stay, "city", where, p)
            _req(stay, "address", where, p)
            if not stay.get("map_query"):
                # A bare street name geocodes wrong; qualify it with the city.
                stay["map_query"] = ", ".join(
                    x for x in (stay.get("address"), stay.get("city_en") or stay.get("city")) if x
                )
            stay["_name"] = self._stay_name(stay)
            self.lodging[sid] = stay

        # tickets: list -> dict keyed by id, files resolved against disk
        self.tickets: dict[str, dict] = {}
        for i, tk in enumerate(raw.get("tickets") or []):
            where = f"tickets[{i}]"
            tid = _req(tk, "id", where, p)
            if tid is None:
                continue
            if tid in self.tickets:
                p.append(f"{where}: duplicate ticket id {tid!r}")
                continue
            tk = dict(tk)
            tk["_where"] = where
            cat = tk.get("category") or "transport"
            if cat not in VALID_TICKET_CATEGORIES:
                p.append(f"{where}: category {cat!r} must be one of {VALID_TICKET_CATEGORIES}")
            tk["category"] = cat
            tk["_files"] = self._resolve_files(tk, where, p)
            self.tickets[tid] = tk

        # days
        self.days = []
        for i, day in enumerate(raw.get("days") or []):
            where = f"days[{i}]"
            day = dict(day)
            day["_where"] = where
            day["n"] = day.get("n", i + 1)
            _req(day, "date", where, p)
            _req(day, "city", where, p)
            d = _parse_date(day.get("date"), f"{where}.date", p)
            day["_date"] = d
            if d:
                day["date"] = d.isoformat()
                day["label"] = day.get("label") or f"{d.month}/{d.day}"
                day["wd"] = day.get("wd") or WD_ZH[d.weekday()]
            day["country"] = (day.get("country") or "").lower()
            day["weather"] = day.get("weather") or {}
            day["slots"] = day.get("slots") or []
            day["transport"] = day.get("transport") or []
            day["tickets"] = day.get("tickets") or {}
            self.days.append(day)

    @staticmethod
    def _stay_name(stay):
        """'罗马民宿 · 房东 Marco' / 'Spiez Hotel' — built, not hand-written."""
        city = stay.get("city") or ""
        kind = stay.get("type") or stay.get("type_en") or ""
        name = f"{city}{kind}" if city and kind else (city or kind)
        host = stay.get("host")
        return f"{name} · 房东 {host}" if host else name

    def _resolve_files(self, tk, where, problems):
        """Ticket files may be given explicitly or globbed from the tickets dir."""
        files = tk.get("files") or ([tk["file"]] if tk.get("file") else [])
        if not files:
            problems.append(f"{where}: needs 'file' or 'files'")
            return []
        resolved = []
        for rel in files:
            path = os.path.join(self.base_dir, rel)
            if not os.path.exists(path):
                problems.append(f"{where}: file not found: {rel}")
                continue
            resolved.append(path)
        return resolved

    # -- validation --------------------------------------------------------

    def _validate(self):
        p = self.problems
        if not self.days:
            p.append("no days defined")

        if self.start and self.end and self.start > self.end:
            p.append(f"meta.start ({self.start}) is after meta.end ({self.end})")

        seen_ids = set()
        for i, day in enumerate(self.days):
            where = day["_where"]
            if day["n"] in seen_ids:
                p.append(f"{where}: duplicate day number {day['n']}")
            seen_ids.add(day["n"])

            d = day["_date"]
            if d and self.start and self.end and not (self.start <= d <= self.end):
                p.append(f"{where}: date {d} is outside meta range {self.start}..{self.end}")
            if i and self.days[i - 1]["_date"] and d and d < self.days[i - 1]["_date"]:
                p.append(f"{where}: date {d} is before the previous day")

            ref = day.get("lodging")
            if ref and ref not in self.lodging:
                p.append(f"{where}: lodging {ref!r} is not defined in the lodging list")

            for cat, ids in (day["tickets"] or {}).items():
                if cat not in VALID_TICKET_CATEGORIES:
                    p.append(f"{where}.tickets: unknown category {cat!r}")
                    continue
                for tid in ids or []:
                    if tid not in self.tickets:
                        p.append(f"{where}.tickets.{cat}: unknown ticket {tid!r}")

        for sid, stay in self.lodging.items():
            ci, co = stay.get("_checkin"), stay.get("_checkout")
            where = stay["_where"]
            if ci and co and co <= ci:
                p.append(f"{where}: checkout {co} must be after checkin {ci}")
            nights = stay.get("nights")
            if nights is not None and ci and co:
                actual = (co - ci).days
                if int(nights) != actual:
                    p.append(
                        f"{where}: nights={nights} but {ci}..{co} is {actual} night(s)"
                    )

    # -- accessors ---------------------------------------------------------

    def stay_for(self, day):
        ref = day.get("lodging")
        return self.lodging.get(ref) if ref else None

    def ticket_list(self, day, category=None):
        """Flat [{category, ticket, caption, slug, page, pages}] for a day."""
        out = []
        groups = [category] if category else list(VALID_TICKET_CATEGORIES)
        for cat in groups:
            for tid in (day["tickets"] or {}).get(cat) or []:
                tk = self.tickets.get(tid)
                if not tk:
                    continue
                n = len(tk["_files"])
                for idx, path in enumerate(tk["_files"]):
                    cap = tk.get("label") or tk["id"]
                    if n > 1:
                        cap = f"{cap} · 第 {idx + 1} 页"
                    out.append({
                        "category": cat,
                        "ticket": tk,
                        "file": path,
                        "slug": f"{tid}_{idx}",
                        "caption": cap,
                        "page": idx + 1,
                        "pages": n,
                    })
        return out

    @property
    def nights_total(self):
        return (self.end - self.start).days if (self.start and self.end) else 0

    @property
    def total_tickets(self):
        return sum(len(self.ticket_list(d)) for d in self.days)

    def countries(self):
        seen = []
        for d in self.days:
            c = d["country"]
            if c and c not in seen:
                seen.append(c)
        return seen


# ---------------------------------------------------------------- loading

def load(path):
    if not os.path.exists(path):
        raise TripError([f"trip file not found: {path}"])
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    if path.endswith(".json"):
        raw = json.loads(text)
    else:
        if yaml is None:
            raise TripError([
                "PyYAML is required to read .yaml trip files.",
                "    pip install pyyaml      (or use a .json trip file instead)",
            ])
        raw = yaml.safe_load(text)

    return Trip(raw, os.path.dirname(os.path.abspath(path)))


def _main(argv):
    if len(argv) != 2:
        print("usage: python3 scripts/model.py <trip.yaml>", file=sys.stderr)
        return 2
    try:
        trip = load(argv[1])
    except TripError as exc:
        print("trip file has problems:", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1

    print(f"ok — {trip.title} ({trip.slug})")
    print(f"  {trip.start} .. {trip.end}  ({trip.nights_total} nights)")
    print(f"  days      : {len(trip.days)}")
    print(f"  lodging   : {len(trip.lodging)}  ({', '.join(trip.lodging)})")
    print(f"  tickets   : {len(trip.tickets)} defined, {trip.total_tickets} image(s) after page-splitting")
    print(f"  countries : {', '.join(trip.countries()) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
