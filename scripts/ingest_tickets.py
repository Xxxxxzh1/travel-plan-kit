#!/usr/bin/env python3
"""
ingest_tickets.py — turn whatever format a ticket arrives in into a small JPEG
that can be embedded in the offline roadbook.

Tickets come from a dozen places (airline PDFs, Trenitalia PDFs, Booking.com
screenshots, phone screenshots). Embedding them raw makes a 20 MB page, so
everything is normalised: PDFs get rasterised per page, images get downscaled,
and everything becomes JPEG.

Used as a library by gen_roadbook.py, and standalone:

    python3 scripts/ingest_tickets.py <trip.yaml> [--out DIR] [--width 1050]
"""

from __future__ import annotations

import base64
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".tif", ".tiff", ".bmp"}
PDF_EXT = {".pdf"}

DEFAULT_MAX_WIDTH = 1050   # ~phone width at 3x; keeps QR codes scannable
DEFAULT_QUALITY = 62


class IngestError(Exception):
    pass


# --------------------------------------------------------------- capabilities

def have(cmd):
    return shutil.which(cmd) is not None


def _pillow():
    try:
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False


def capabilities():
    return {
        "pdftoppm": have("pdftoppm"),
        "pillow": _pillow(),
        "sips": have("sips"),
    }


def describe_capabilities():
    caps = capabilities()
    lines = []
    if not caps["pdftoppm"]:
        lines.append("  ⚠ pdftoppm not found — PDF tickets cannot be rasterised.")
        lines.append("      macOS: brew install poppler   |   Debian: apt install poppler-utils")
    if not (caps["pillow"] or caps["sips"]):
        lines.append("  ⚠ neither Pillow nor sips found — images will be embedded unresized.")
        lines.append("      pip install pillow   (recommended: keeps the output small)")
    return lines


# --------------------------------------------------------------- conversion

def _cache_key(path):
    st = os.stat(path)
    raw = f"{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def _pdf_to_jpegs(src, out_dir, prefix, width, quality):
    """Rasterise every page of a PDF to a JPEG. Returns the page paths in order."""
    if not have("pdftoppm"):
        raise IngestError(
            f"cannot read PDF ticket {os.path.basename(src)}: pdftoppm is not installed\n"
            "      macOS: brew install poppler   |   Debian: apt install poppler-utils"
        )
    # 105 dpi puts an A4 page at roughly `width` px, which is the sweet spot
    # between legible text and file size.
    tmp = tempfile.mkdtemp()
    try:
        stem = os.path.join(tmp, "p")
        _run(["pdftoppm", "-jpeg", "-r", "105",
              "-jpegopt", f"quality={quality}", src, stem])
        pages = sorted(
            (os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".jpg")),
            key=lambda p: int("".join(c for c in os.path.basename(p) if c.isdigit()) or 0),
        )
        out = []
        for i, page in enumerate(pages):
            dst = os.path.join(out_dir, f"{prefix}-p{i + 1}.jpg")
            _shrink(page, dst, width, quality)
            out.append(dst)
        if not out:
            raise IngestError(f"pdftoppm produced no pages for {os.path.basename(src)}")
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _shrink(src, dst, width, quality):
    """Downscale + re-encode an image. Falls back to a plain copy."""
    if _pillow():
        from PIL import Image
        with Image.open(src) as im:
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            if im.width > width:
                h = round(im.height * width / im.width)
                im = im.resize((width, h), Image.LANCZOS)
            im.save(dst, "JPEG", quality=quality, optimize=True)
        return dst

    if have("sips"):
        _run(["sips", "-s", "format", "jpeg",
              "-s", "formatOptions", str(quality),
              "-Z", str(width), src, "--out", dst])
        return dst

    shutil.copyfile(src, dst)
    return dst


# --------------------------------------------------------------- public API

def normalize(src, cache_dir, width=DEFAULT_MAX_WIDTH, quality=DEFAULT_QUALITY):
    """Normalise one ticket file. Returns a list of JPEG paths (one per page)."""
    if not os.path.exists(src):
        raise IngestError(f"ticket file not found: {src}")

    ext = os.path.splitext(src)[1].lower()
    os.makedirs(cache_dir, exist_ok=True)
    prefix = _cache_key(src)

    if ext in PDF_EXT:
        existing = sorted(
            f for f in os.listdir(cache_dir) if f.startswith(prefix + "-p")
        )
        if existing:
            return [os.path.join(cache_dir, f) for f in existing]
        return _pdf_to_jpegs(src, cache_dir, prefix, width, quality)

    if ext in IMAGE_EXT:
        dst = os.path.join(cache_dir, prefix + ".jpg")
        if not os.path.exists(dst):
            _shrink(src, dst, width, quality)
        return [dst]

    raise IngestError(
        f"unsupported ticket format {ext!r} ({os.path.basename(src)}). "
        f"Supported: PDF, {', '.join(sorted(IMAGE_EXT))}"
    )


def data_uri(path):
    mime = "image/jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "image/png"
    with open(path, "rb") as fh:
        return f"data:{mime};base64," + base64.b64encode(fh.read()).decode()


# --------------------------------------------------------------- CLI

def _main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Normalise ticket files for embedding.")
    ap.add_argument("trip", help="path to trip.yaml")
    ap.add_argument("--out", default=None, help="cache dir (default: <trip dir>/.cache/tickets)")
    ap.add_argument("--width", type=int, default=DEFAULT_MAX_WIDTH)
    ap.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    args = ap.parse_args(argv[1:])

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import model

    for line in describe_capabilities():
        print(line)

    trip = model.load(args.trip)
    out_dir = args.out or os.path.join(trip.base_dir, ".cache", "tickets")

    total_in = total_out = 0
    for tid, tk in trip.tickets.items():
        srcs = tk.get("_files") or []
        for src in srcs:
            pages = normalize(src, out_dir, args.width, args.quality)
            si = os.path.getsize(src)
            so = sum(os.path.getsize(p) for p in pages)
            total_in += si
            total_out += so
            note = f" ({len(pages)} pages)" if len(pages) > 1 else ""
            print(f"  {tid:<18} {si/1024:7.0f} KB -> {so/1024:6.0f} KB{note}")

    if total_in:
        print(f"\n  total {total_in/1048576:.1f} MB -> {total_out/1048576:.1f} MB "
              f"({100 * total_out / total_in:.0f}%)")
    print(f"  cache: {out_dir}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_main(sys.argv))
    except IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
