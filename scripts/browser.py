#!/usr/bin/env python3
"""
browser.py — locate a Chromium-family browser and drive it headlessly for
"render HTML to PNG" and "render HTML to PDF".

There is no wkhtmltopdf / weasyprint / pandoc on the machines this was built
for, and headless Chrome gives far better CSS support than any of them anyway
(flexbox, grid, `@page`, print-color-adjust), so it is the single rendering
engine for every output format.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
]


class BrowserError(Exception):
    pass


def find():
    for c in CANDIDATES:
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
        else:
            found = shutil.which(c)
            if found:
                return found
    return None


def require():
    path = find()
    if not path:
        raise BrowserError(
            "no Chromium-family browser found — this is needed for PDF and PNG output.\n"
            "      Install Google Chrome, or point CHROME at an existing binary:\n"
            "        export CHROME=/path/to/chrome"
        )
    return os.environ.get("CHROME") or path


def _base_args(binary):
    return [binary, "--headless", "--disable-gpu", "--hide-scrollbars",
            "--no-sandbox", "--disable-dev-shm-usage", "--allow-file-access-from-files"]


def _trim(path, margin):
    """Crop away background beyond the content, keeping `margin` px of it.

    Headless Chrome only screenshots a fixed window size, so a short page ends
    up floating in dead whitespace. Trimming to the content bounding box (taken
    against the corner pixel, i.e. the page background) gives a tight image.
    """
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return path
    im = Image.open(path).convert("RGB")
    bg = im.getpixel((0, 0))
    diff = ImageChops.difference(im, Image.new("RGB", im.size, bg))
    box = diff.getbbox()
    if not box:
        return path
    left, top, right, bottom = box
    w, h = im.size
    im.crop((max(0, left - margin), max(0, top - margin),
             min(w, right + margin), min(h, bottom + margin))).save(path)
    return path


def screenshot(html, out_png, width, height, scale=2, extra_wait_ms=0, trim=False, margin=18):
    """Render an HTML string to a PNG of exactly width*scale x height*scale."""
    binary = require()
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "page.html")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(html)
        cmd = _base_args(binary) + [
            f"--force-device-scale-factor={scale}",
            f"--window-size={width},{height}",
            f"--screenshot={os.path.abspath(out_png)}",
        ]
        if extra_wait_ms:
            cmd.append(f"--virtual-time-budget={extra_wait_ms}")
        cmd.append("file://" + src)
        proc = subprocess.run(cmd, capture_output=True)
        if not os.path.exists(out_png):
            raise BrowserError(
                f"browser produced no screenshot for {out_png}\n"
                f"{(proc.stderr or b'').decode()[:400]}"
            )
    if trim:
        _trim(out_png, margin * scale)
    return out_png


def print_pdf(html_path, out_pdf):
    """Render an HTML *file* to PDF, honouring the document's own @page rules."""
    binary = require()
    out_pdf = os.path.abspath(out_pdf)
    if os.path.exists(out_pdf):
        os.remove(out_pdf)
    cmd = _base_args(binary) + [
        "--no-pdf-header-footer",
        f"--print-to-pdf={out_pdf}",
        "file://" + os.path.abspath(html_path),
    ]
    subprocess.run(cmd, capture_output=True)
    if not os.path.exists(out_pdf):
        raise BrowserError(f"browser produced no PDF at {out_pdf}")
    return out_pdf


if __name__ == "__main__":
    p = find()
    print(p if p else "not found")
    sys.exit(0 if p else 1)
