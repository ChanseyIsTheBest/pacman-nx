"""pacman-nx (2026-11-03, title update 3): how the XDK's structures moved between two executables, measured from their code.

The update was built with a newer XDK, so the D3D library is a new compile. For every function pair of tools/map_functions.py
in the given old address range, the two instruction lists are aligned (the mnemonics; registers and immediates left out) and each
aligned load or store contributes a vote old displacement -> new displacement. The result is the map of the offsets the
library uses: a run of equal deltas is a part of the structure that kept its layout.

  python -I tools/tu_offset_delta.py --maps <dir> --old-gen <dir> --new-gen <dir> --lo 0x821B4000 --hi 0x821D9000 [--min 256]
"""
import argparse
import collections
import difflib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from remap_addresses import Mapper  # noqa: E402

MEM = re.compile(r'^(lbz|lbzu|lhz|lhzu|lha|lwz|lwzu|ld|ldu|stb|stbu|sth|sthu|stw|stwu|std|stdu|lfs|lfd|stfs|stfd)$')
OPS = re.compile(r'^[rf]\d+,(-?\d+)\(r(\d+)\)$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--maps', required=True)
    ap.add_argument('--old-gen', required=True)
    ap.add_argument('--new-gen', required=True)
    ap.add_argument('--lo', type=lambda s: int(s, 16), required=True)
    ap.add_argument('--hi', type=lambda s: int(s, 16), required=True)
    ap.add_argument('--min', type=int, default=256)
    a = ap.parse_args()
    m = Mapper(a.maps, a.old_gen, a.new_gen)
    pairs = {k: v[0] for k, v in m.fmap.items() if a.lo <= int(k, 16) < a.hi}
    m.old.load(set(pairs))
    m.new.load(set(pairs.values()))
    votes = collections.defaultdict(collections.Counter)
    used = 0
    for o, n in pairs.items():
        ol, nl = m.old.insns.get(o), m.new.insns.get(n)
        if not ol or not nl:
            continue
        used += 1
        sm = difflib.SequenceMatcher(None, [x[0] for x in ol], [x[0] for x in nl], autojunk=False)
        for tag, i0, i1, j0, j1 in sm.get_opcodes():
            if tag != 'equal':
                continue
            for k in range(i1 - i0):
                x, y = ol[i0 + k], nl[j0 + k]
                if not MEM.match(x[0]):
                    continue
                p, q = OPS.match(x[1]), OPS.match(y[1])
                if not p or not q or p.group(2) == '1' or q.group(2) == '1':
                    continue
                d0, d1 = int(p.group(1)), int(q.group(1))
                if d0 >= a.min:
                    votes[d0][d1] += 1
    print(f'{used} function pairs; {len(votes)} old offsets at or above {a.min:#x}')
    run = None
    for d0 in sorted(votes):
        d1, c = votes[d0].most_common(1)[0]
        total = sum(votes[d0].values())
        delta = d1 - d0
        if delta != run:
            print(f'--- delta {delta:+#x} from {d0:#x}')
            run = delta
        note = '' if c == total else f'  (rivals {dict(votes[d0].most_common(4))})'
        print(f'  {d0:#07x} -> {d1:#07x}  votes {c}/{total}{note}')


if __name__ == '__main__':
    main()
