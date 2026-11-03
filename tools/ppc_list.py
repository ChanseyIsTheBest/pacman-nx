"""pacman-nx (2026-11-03): a generated function's PowerPC listing, from the generator's `// mnemonic operands` comments, with the
strings its lis / addi pairs build (ASCII or UTF-16) read from the image dump.

  python -I tools/ppc_list.py <generated dir> <image> sub_82178 9A0 ... : python -I tools/ppc_list.py G IMG 821789A0 [more] [--max 200]
"""
import argparse
import glob
import os
import re

FUNC = re.compile(r'^DEFINE_REX_FUNC\(sub_([0-9A-F]+)\)')
INSN = re.compile(r'^\s*// ([a-z][a-z0-9.+\-]*)(?:\s+(.*))?$')
BASE = 0x82000000


def text_at(img, addr):
    o = addr - BASE
    if not 0 <= o < len(img) - 2:
        return None
    e = img.find(b'\0', o)
    s = img[o:e]
    if 3 <= len(s) <= 120 and all(32 <= c < 127 for c in s):
        return repr(s.decode())
    if img[o] == 0 and 32 <= img[o + 1] < 127:
        k = o
        out = []
        while k + 2 <= len(img) and img[k:k + 2] != b'\0\0' and len(out) < 60:
            out.append(int.from_bytes(img[k:k + 2], 'big'))
            k += 2
        if len(out) >= 3:
            return 'L' + repr(''.join(chr(c) for c in out))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gen')
    ap.add_argument('image')
    ap.add_argument('funcs', nargs='+')
    ap.add_argument('--max', type=int, default=400)
    a = ap.parse_args()
    img = open(a.image, 'rb').read()
    want = {x.upper().replace('SUB_', '') for x in a.funcs}
    found = {}
    for path in glob.glob(os.path.join(a.gen, 'renut_recomp.*.cpp')):
        cur = None
        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                h = FUNC.match(line)
                if h:
                    cur = h.group(1) if h.group(1) in want else None
                    if cur:
                        found[cur] = []
                    continue
                if cur:
                    i = INSN.match(line)
                    if i:
                        found[cur].append((i.group(1), i.group(2) or ''))
    for name in a.funcs:
        key = name.upper().replace('SUB_', '')
        print(f'=== sub_{key}: {len(found.get(key, []))} instructions')
        regs = {}
        start = int(key, 16)
        for k, (m, ops) in enumerate(found.get(key, [])[:a.max]):
            note = ''
            if m == 'lis':
                g = re.search(r'r(\d+),(-?\d+)$', ops)
                if g:
                    regs[g.group(1)] = int(g.group(2)) << 16
            else:
                g = re.search(r'r\d+,r(\d+),(-?\d+)$|[rf]\d+,(-?\d+)\(r(\d+)\)$', ops)
                if g:
                    reg, lo = (g.group(1), g.group(2)) if g.group(1) else (g.group(4), g.group(3))
                    if reg in regs:
                        addr = (regs[reg] + int(lo)) & 0xFFFFFFFF
                        t = text_at(img, addr)
                        note = f'   ; {addr:08X}' + (f' {t}' if t else '')
            print(f'{start + k * 4:08X} {m} {ops}{note}')


if __name__ == '__main__':
    main()
