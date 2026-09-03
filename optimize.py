#!/usr/bin/env python3
"""Recompress photos in build/assets in place (same path/format, so no HTML
changes needed). Originals are already backed up separately before this runs."""
from pathlib import Path
from PIL import Image

import sys

BUILD_ASSETS = Path("/sessions/ecstatic-sharp-allen/mnt/cgw-newsite/build/assets")
DONE_LOG = Path("/sessions/ecstatic-sharp-allen/mnt/cgw-newsite/.optimize_done")
BATCH = int(sys.argv[1]) if len(sys.argv) > 1 else 1000

done = set()
if DONE_LOG.exists():
    done = set(DONE_LOG.read_text().splitlines())

before_total = 0
after_total = 0
n = 0

all_imgs = [p for p in BUILD_ASSETS.rglob("*") if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png")]
todo = [p for p in all_imgs if str(p) not in done]
print(f"{len(all_imgs)} total images, {len(todo)} remaining, processing up to {BATCH} this run")

with DONE_LOG.open("a") as donef:
    for p in todo[:BATCH]:
        ext = p.suffix.lower()
        try:
            before = p.stat().st_size
            before_total += before
            img = Image.open(p)
            if ext in (".jpg", ".jpeg"):
                img = img.convert("RGB")
                img.save(p, "JPEG", quality=78, optimize=True, progressive=True)
            else:
                if img.mode not in ("RGBA", "P"):
                    img = img.convert("RGBA") if img.mode != "RGB" else img
                img.save(p, "PNG", optimize=True)
            after = p.stat().st_size
            after_total += after
            n += 1
            donef.write(str(p) + "\n")
        except Exception as e:
            print(f"skip {p}: {e}")
            donef.write(str(p) + "\n")

print(f"\n{n} images processed this run")
if before_total:
    print(f"before: {before_total/1e6:.1f}MB  after: {after_total/1e6:.1f}MB  saved: {(1-after_total/before_total)*100:.0f}%")
print(f"{len(todo)-n} remaining")
