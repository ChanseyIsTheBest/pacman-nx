"""pacman-nx (2026-11-03): who builds a guest address and who calls a function, from the generator's `// mnemonic operands` comments.

An address is found as `lis rX,hi` followed within a few instructions by `addi rY,rX,lo` / a load or store with that displacement.
A function is found by its `bl` and `b` sites. Prints the containing function and the instruction address of each.

  python -I tools/ppc_xrefs.py <generated dir> 0x820A83E8 [0x821B4078 ...] [--around 12]
"""
import argparse
import glob
import os
import re

FUNC = re.compile(r'^DEFINE_REX_FUNC\(sub_([0-9A-F]+)\)')
INSN = re.compile(r'^\s*// ([a-z][a-z0-9.+\-]*)(?:\s+(.*))?$')
LIS = re.compile(r'r(\d+),(-?\d+)$')
DISP = re.compile(r'r\d+,r(\d+),(-?\d+)$|[rf]\d+,(-?\d+)\(r(\d+)\)$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gen')
    ap.add_argument('addrs', nargs='+')
    ap.add_argument('--around', type=int, default=0)
    a = ap.parse_args()
    want = [int(x, 16) for x in a.addrs]
    hits = []
    for path in sorted(glob.glob(os.path.join(a.gen, 'renut_recomp.*.cpp'))):
        start = None
        insns = []

        def flush():
            if start is None:
                return
            regs = {}
            for k, (m, ops) in enumerate(insns):
                if m == 'lis':
                    g = LIS.search(ops)
                    if g:
                        regs[g.group(1)] = (int(g.group(2)) << 16, k)
                elif m in ('bl', 'b', 'beq', 'bne', 'blt', 'bgt', 'ble', 'bge'):
                    t = re.search(r'0x([0-9a-f]+)$', ops)
                    if t and int(t.group(1), 16) in want:
                        hits.append((int(t.group(1), 16), start, k, m + ' ' + ops, insns))
                g = DISP.search(ops) if m not in ('lis', 'bl', 'b') else None
                if g:
                    reg, lo = (g.group(1), g.group(2)) if g.group(1) else (g.group(4), g.group(3))
                    if reg in regs and k - regs[reg][1] < 32:
                        addr = (regs[reg][0] + int(lo)) & 0xFFFFFFFF
                        if addr in want:
                            hits.append((addr, start, k, m + ' ' + ops, insns))

        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                h = FUNC.match(line)
                if h:
                    flush()
                    start = int(h.group(1), 16)
                    insns = []
                    continue
                i = INSN.match(line)
                if i and start is not None:
                    insns.append((i.group(1), i.group(2) or ''))
        flush()
    for addr, start, k, text, insns in sorted(hits, key=lambda x: (x[0], x[1], x[2])):
        print(f'{addr:08X}: sub_{start:08X}+{k * 4:#x} at {start + k * 4:08X}: {text}')
        if a.around:
            for j in range(max(0, k - a.around), min(len(insns), k + a.around + 1)):
                mark = '>' if j == k else ' '
                print(f'   {mark} {start + j * 4:08X} {insns[j][0]} {insns[j][1]}')


if __name__ == '__main__':
    main()
