#!/usr/bin/env python3
"""pacman-nx (2026-11-02): compares a run's captures with a reference run's (the Switch build in Ryujinx against the PC build
on Vulkan). For each capture of the run, the reference capture closest in picture (the game's scenes do not line up in time)
and how far apart they are: pixels that differ by more than --tol in any channel, the largest difference and its bounding box.
Writes `<out>/<name>_diff.png` (differing pixels white, on the run's capture darkened) for the ones over --max-share.

  python tools/compare_captures.py out/emu_runs/emu1 out/pc_runs/renut6 [--tol 8] [--max-share 0.2] [--out out/cmp/emu1]
"""
import argparse
import glob
import os

from PIL import Image, ImageChops


def load(path):
    return Image.open(path).convert('RGB').resize((1280, 720), Image.NEAREST)


def stats(a, b, tol):
    diff = ImageChops.difference(a, b)
    r, g, bl = diff.split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    hist = m.histogram()
    over = sum(hist[tol + 1:])
    worst = max((i for i, c in enumerate(hist) if c), default=0)
    mask = m.point(lambda v: 255 if v > tol else 0)
    return over / (1280 * 720), worst, mask.getbbox(), mask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run')
    ap.add_argument('reference')
    ap.add_argument('--tol', type=int, default=8)
    ap.add_argument('--max-share', type=float, default=0.2, help='percent of the picture over which a diff image is written')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    refs = [(p, load(p)) for p in sorted(glob.glob(os.path.join(a.reference, '*.png')))]
    if not refs:
        raise SystemExit(f'no captures in {a.reference}')
    if a.out:
        os.makedirs(a.out, exist_ok=True)
    print(f'{"capture":28} {"closest reference":28} {"% over":>7} {"max":>4}  box')
    for p in sorted(glob.glob(os.path.join(a.run, '*.png'))):
        img = load(p)
        best = min(((stats(img, r, a.tol), q) for q, r in refs), key=lambda x: x[0][0])
        (share, worst, box, mask), q = best
        print(f'{os.path.basename(p):28} {os.path.basename(q):28} {100 * share:7.3f} {worst:4}  {box}')
        if a.out and 100 * share > a.max_share:
            dark = img.point(lambda v: v // 3)
            dark.paste((255, 255, 255), mask=mask)
            dark.save(os.path.join(a.out, os.path.splitext(os.path.basename(p))[0] + '_diff.png'))


if __name__ == '__main__':
    main()
