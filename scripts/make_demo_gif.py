#!/usr/bin/env python3
"""
make_demo_gif.py — assemble frames captured by record_demo.mjs into the demo GIF
used in README.md.

    node scripts/record_demo.mjs http://localhost:8770/roadbook.html /tmp/frames
    python3 scripts/make_demo_gif.py /tmp/frames docs/screenshots/roadbook-demo.gif

Frames are captured at 2x for crispness and scaled down here, which also
antialiases the text nicely. A single global palette is built from all frames
rather than letting each pick its own — per-frame adaptive palettes flicker
badly on a dark UI.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("error: Pillow required (pip install pillow)", file=sys.stderr)
    sys.exit(1)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("frames_dir")
    ap.add_argument("out", nargs="?", default="docs/screenshots/roadbook-demo.gif")
    ap.add_argument("--width", type=int, default=340, help="output width in px")
    ap.add_argument("--colors", type=int, default=128, help="GIF palette size")
    ap.add_argument("--loop-hold", type=int, default=None,
                    help="override the final frame's hold (ms)")
    args = ap.parse_args(argv[1:])

    src = sorted(glob.glob(os.path.join(args.frames_dir, "*.png")))
    if not src:
        print(f"error: no PNG frames in {args.frames_dir}", file=sys.stderr)
        return 1

    holds_path = os.path.join(args.frames_dir, "holds.json")
    if os.path.exists(holds_path):
        holds = json.load(open(holds_path))
        if len(holds) != len(src):
            print(f"  ⚠ holds.json has {len(holds)} entries for {len(src)} frames; "
                  f"using a uniform delay")
            holds = None
    else:
        holds = None
    if holds is None:
        holds = [800] * len(src)
    if args.loop_hold is not None:
        holds[-1] = args.loop_hold

    first = Image.open(src[0])
    height = round(first.height * args.width / first.width)
    frames = []
    for p in src:
        im = Image.open(p).convert("RGB")
        frames.append(im.resize((args.width, height), Image.LANCZOS))

    # One palette for the whole animation.
    stack = Image.new("RGB", (args.width, height * len(frames)))
    for i, f in enumerate(frames):
        stack.paste(f, (0, i * height))
    pal = stack.quantize(colors=args.colors, method=Image.MEDIANCUT)
    quantized = [f.quantize(palette=pal, dither=Image.FLOYDSTEINBERG) for f in frames]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    quantized[0].save(args.out, save_all=True, append_images=quantized[1:],
                      duration=holds, loop=0, optimize=True)

    size = os.path.getsize(args.out)
    print(f"  {args.out}")
    print(f"    {len(frames)} frames · {args.width}x{height} · "
          f"{sum(holds)/1000:.1f}s · {size/1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
