"""pacman-nx (2026-11-03, title update 3): the D3D library's functions, old against new, for placing hooks by hand.

The update's D3D is a new compile (a newer XDK), so tools/map_functions.py leaves some of it unpaired or 'doubtful'. For each old
function in the range: its pair and status, or for an unpaired one the unclaimed new functions between its paired neighbours,
best first by how alike the mnemonic histograms are (the linker kept the library's order).

  python -I tools/tu_region_pairs.py --maps <dir> --lo 0x821B5B58 --hi 0x821DC800 [--only A,B,...] [--status changed,doubtful,none]
"""
import argparse
import bisect
import json
import os


def alike(a, b):
    common = sum(min(a.get(k, 0), b.get(k, 0)) for k in set(a) | set(b))
    return common / max(sum(a.values()), sum(b.values()), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--maps', required=True)
    ap.add_argument('--lo', type=lambda s: int(s, 16), required=True)
    ap.add_argument('--hi', type=lambda s: int(s, 16), required=True)
    ap.add_argument('--only', default='')
    ap.add_argument('--status', default='')
    a = ap.parse_args()
    fmap = json.load(open(os.path.join(a.maps, 'func_map.json')))
    old = json.load(open(os.path.join(a.maps, 'base_sigs.json')))
    new = json.load(open(os.path.join(a.maps, 'tu_sigs.json')))
    only = {x.strip().upper() for x in a.only.split(',') if x.strip()}
    want = {x.strip() for x in a.status.split(',') if x.strip()}
    starts = sorted(k for k in old if a.lo <= int(k, 16) < a.hi)
    new_starts = sorted(new, key=lambda k: int(k, 16))
    new_ints = [int(k, 16) for k in new_starts]
    claimed = {v[0] for v in fmap.values()}
    for i, o in enumerate(starts):
        pair = fmap.get(o)
        st = pair[1] if pair else 'none'
        if only and o not in only:
            continue
        if want and st not in want:
            continue
        count = old[o][2]
        if pair:
            sim = alike(old[o][5], new[pair[0]][5])
            print(f'{o} n={count} -> {pair[0]} n={new[pair[0]][2]} {st} alike {sim:.2f}')
            continue
        lo = next((fmap[starts[j]][0] for j in range(i - 1, -1, -1) if starts[j] in fmap), None)
        hi = next((fmap[starts[j]][0] for j in range(i + 1, len(starts)) if starts[j] in fmap), None)
        l = bisect.bisect_right(new_ints, int(lo, 16)) if lo else 0
        h = bisect.bisect_left(new_ints, int(hi, 16)) if hi else len(new_ints)
        cands = [(alike(old[o][5], new[c][5]), c) for c in new_starts[l:h]]
        cands.sort(reverse=True)
        text = ', '.join(f'{c}{"*" if c in claimed else ""} n={new[c][2]} {s:.2f}' for s, c in cands[:5])
        print(f'{o} n={count} none, between {lo} and {hi}: {text}')


if __name__ == '__main__':
    main()
