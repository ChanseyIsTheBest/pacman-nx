#!/usr/bin/env python3
"""pacman-nx (2026-11-03, title update 3): Renut's Direct3D device offsets, from the base game's layout (XDK 2.0.11164) to the
update's (XDK 2.0.21250), which is NiGHTS's and Peggle 2's.

Zones measured with tools/tu_offset_delta.py on this game's two D3D libraries, and checked against nights-nx's and sasrt-nx's
d3d.h (every named constant agrees). The numbers below 0x2A80 did not move. Rewrites each decimal or hex literal in the zones on
a line that names a device offset; with --list it only prints them, for reading.

  python -I tools/renut_device_offsets_tu3.py [--list] [--dry-run]
"""
import argparse
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GPU = os.path.join(ROOT, 'app', 'src', 'renut_engine', 'gpu')
# (first, last, delta) in the base's offsets
ZONES = [
    (0x2A80, 0x2AC7, 0x80),    # CreationThreadId 0x2A88->0x2B08, fence tags 0x2A9C->0x2B1C, swap flags 0x2ABD->0x2B3D
    (0x2AC8, 0x2AFF, 0x84),
    (0x2B00, 0x2C8F, 0x8C),
    (0x2C90, 0x2EE7, 0xF8),    # the declaration 0x2ED8->0x2FD0
    (0x2EE8, 0x2F43, 0x100),
    (0x2F5E, 0x2F91, 0xE6),
    (0x2FAC, 0x2FFF, 0xCC),
    (0x3000, 0x345F, 0xC8),    # index buffer 0x3144->0x320C .. predication 0x3254->0x331C, snapshot 0x3258->0x3320
    (0x3460, 0x4183, 0xC0),    # VerticesRingEnd 0x3554->0x3614, CommandBuffer 0x35A0->0x3660, present tag 0x3B30->0x3BF0
    (0x4184, 0x552F, 0xC4),    # SwapCount 0x4184->0x4248
    (0x5530, 0x5EFF, 0xC8),    # BehaviorFlags 0x5E80->0x5F48
]
EXPLICIT = {
    0x5F00: 0x6080,  # kDeviceAllocSize: Direct3D_CreateDevice `li r3,24704; li r4,128`
    0x2F44: 0x2A70,  # MaxAnisotropy, back in the public part
    0x2F92: 0x2A8A,  # ZFilter
}
LIT = re.compile(r'(?<![0-9A-Za-z_.])(0x[0-9A-Fa-f]+|\d+)(u|U)?(?![0-9A-Za-z_.])')
PACNOTE = re.compile(r'pacman-nx: ?((?:0x[0-9A-Fa-f]+|\d+)->(0x[0-9A-Fa-f]+|\d+)(?:, ?(?:0x[0-9A-Fa-f]+|\d+)->(?:0x[0-9A-Fa-f]+|\d+))*)')
ONE = re.compile(r'(0x[0-9A-Fa-f]+|\d+)->(0x[0-9A-Fa-f]+|\d+)')


def moved(x):
    if x in EXPLICIT:
        return EXPLICIT[x]
    for lo, hi, d in ZONES:
        if lo <= x <= hi:
            return x + d
    return None


def respell(old, new):
    return f'0x{new:X}' if old.lower().startswith('0x') else str(new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true', help='print every literal in the zones on lines this tool does not rewrite')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    changed = 0
    left = []
    for d, _, fs in os.walk(GPU):
        for f in fs:
            if not f.endswith(('.cpp', '.h', '.inc')):
                continue
            p = os.path.join(d, f)
            t = open(p, encoding='utf-8', errors='surrogateescape', newline='').read()
            lines = t.split('\n')
            dirty = False
            for i, line in enumerate(lines):
                code, sep, comment = line.partition('//')
                note = PACNOTE.search(comment)
                if 'tu3:' in comment:
                    continue
                if note:
                    notes = []
                    for _, ys in ONE.findall(note.group(1)):
                        y = int(ys, 0)
                        new = moved(y)
                        if new is None:
                            continue
                        rx = re.compile(r'(?<![0-9A-Za-z_.])' + re.escape(ys) + r'(?:[uU])?(?![0-9A-Za-z_.])')
                        if rx.search(code):
                            code = rx.sub(respell(ys, new), code, count=1)
                            notes.append(f'{ys}->{respell(ys, new)}')
                    if notes:
                        lines[i] = code + sep + comment.rstrip('\r') + ' (tu3: ' + ', '.join(notes) + ')' + ('\r' if line.endswith('\r') else '')
                        dirty = True
                        changed += 1
                    continue
                for m in LIT.finditer(code):
                    x = int(m.group(1), 16 if m.group(1).lower().startswith('0x') else 10)
                    if moved(x) is not None:
                        left.append(f'{os.path.relpath(p, GPU)}:{i + 1}: {m.group(1)} -> {respell(m.group(1), moved(x))}: {code.strip()[:100]}')
            if dirty and not a.dry_run:
                open(p, 'w', encoding='utf-8', errors='surrogateescape', newline='').write('\n'.join(lines))
    print(f'{changed} lines rewritten; {len(left)} other literals in the zones')
    if a.list:
        print('\n'.join(left))


if __name__ == '__main__':
    main()
