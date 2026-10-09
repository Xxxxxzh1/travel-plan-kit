#!/usr/bin/env python3
"""
build.py — turn one trip.yaml into every output format.

    python3 scripts/build.py examples/italy-switzerland/trip.yaml
    python3 scripts/build.py my-trip.yaml --out ./out --encrypt 'my passphrase'

Outputs (into <trip dir>/out by default):
    itinerary.md      the master table, plain Markdown
    itinerary.html    the same table, styled for print
    itinerary.pdf     the HTML rendered to landscape A4
    roadbook.html     the mobile roadbook — one self-contained offline file
    roadbook.enc.html password-encrypted roadbook (only with --encrypt)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import browser  # noqa: E402
import ingest_tickets  # noqa: E402
import model  # noqa: E402

try:
    import gen_itinerary
    import gen_roadbook
except ImportError as exc:  # pragma: no cover
    print(f"error: cannot import generators: {exc}", file=sys.stderr)
    sys.exit(1)


def check_environment(need_pdf, need_roadbook, need_encrypt):
    """Report what's missing up front, rather than failing halfway through."""
    problems, notes = [], []

    if not browser.find():
        msg = ("no Chromium-family browser found — needed for PDF and ticket rendering.\n"
               "      Install Google Chrome, or set CHROME=/path/to/chrome")
        if need_pdf or need_roadbook:
            problems.append(msg)
        else:
            notes.append(msg)

    caps = ingest_tickets.capabilities()
    if not caps["pdftoppm"]:
        notes.append("pdftoppm not found — PDF tickets cannot be embedded.\n"
                     "      macOS: brew install poppler   |   Debian: apt install poppler-utils")
    if not caps["pillow"] and not caps["sips"]:
        notes.append("neither Pillow nor sips found — ticket images will not be resized.\n"
                     "      pip install pillow   (keeps the roadbook small)")

    if need_encrypt and not shutil.which("node"):
        problems.append("Node.js not found — required for --encrypt.")

    for n in notes:
        print(f"  ⚠ {n}")
    return problems


def main(argv):
    ap = argparse.ArgumentParser(description="Build every travel document from one trip.yaml.")
    ap.add_argument("trip")
    ap.add_argument("--out", default=None, help="output dir (default: <trip dir>/out)")
    ap.add_argument("--encrypt", metavar="PASSWORD", nargs="?", const="",
                    help="also emit an encrypted roadbook (prompted/generated if no value)")
    ap.add_argument("--skip", default="", help="comma list of: pdf,roadbook")
    args = ap.parse_args(argv[1:])

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    try:
        trip = model.load(args.trip)
    except model.TripError as exc:
        print("trip file has problems:", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1

    out_dir = args.out or os.path.join(trip.base_dir, "out")
    os.makedirs(out_dir, exist_ok=True)

    need_pdf = "pdf" not in skip
    need_roadbook = "roadbook" not in skip
    need_encrypt = args.encrypt is not None and need_roadbook

    problems = check_environment(need_pdf, need_roadbook, need_encrypt)
    if problems:
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)
        return 1

    print(f"\n{trip.title_zh or trip.title} · {trip.start} → {trip.end} · "
          f"{len(trip.days)} days · {len(trip.lodging)} stays · {trip.total_tickets} ticket images\n")

    print("itinerary")
    gen_itinerary.main([argv[0], args.trip, "--out", out_dir])

    if need_roadbook:
        print("\nroadbook")
        gen_roadbook.main([argv[0], args.trip, "--out", out_dir])

    if need_pdf:
        print("\npdf")
        html_path = os.path.join(out_dir, "itinerary.html")
        pdf_path = os.path.join(out_dir, "itinerary.pdf")
        try:
            browser.print_pdf(html_path, pdf_path)
            size = os.path.getsize(pdf_path) / 1024
            print(f"  {os.path.relpath(pdf_path, trip.base_dir)}  ({size:.0f} KB)")
        except browser.BrowserError as exc:
            print(f"  ✗ {exc}", file=sys.stderr)

    if need_encrypt:
        print("\nencrypted roadbook")
        password = args.encrypt
        if not password:
            import secrets
            words = ["harbour", "lantern", "meadow", "compass", "thistle",
                     "juniper", "anchor", "foxglove", "quarry", "beacon"]
            password = "-".join(secrets.choice(words) for _ in range(3)) + str(secrets.randbelow(90) + 10)
            print(f"  generated passphrase: {password}")
            print("  (store it in a password manager — it cannot be recovered)")
        roadbook = os.path.join(out_dir, "roadbook.html")
        enc_out = os.path.join(out_dir, "roadbook.enc.html")
        proc = subprocess.run(
            ["node", os.path.join(HERE, "encrypt_roadbook.mjs"), roadbook, "-o", enc_out,
             "-p", password],
            capture_output=True, text=True)
        sys.stdout.write(proc.stdout)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr)
            return proc.returncode

    print("\ndone.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
