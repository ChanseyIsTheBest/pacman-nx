"""pacman-nx (2026-11-03, title update 3): adds to tools/map_functions.py's func_map.json the pairs of tools/d3d_propagate.py (unique shapes,
state tables, aligned call sites: base_to_tu.json) and a last pass by place, and reports what stays unpaired.

- A propagate pair replaces a 'doubtful' or 'changed' map pair it disagrees with (the hooks' routes showed the map is the one that slips
  in the re-linked D3D library), and fills a hole.
- By place: an unpaired old function, between two paired neighbours, takes the unclaimed new function between their partners whose
  mnemonics match (the same skeleton, or a histogram at least 0.8 alike) and whose size is within 15 %. Only performance lists use these
  ('place'): a copy is made from the new function's own text, so a wrong pair costs a copy of the wrong function, not correctness. Hooks do
  not use them (tools/renut_hook_map_tu3.py asks for two routes).

  python -I tools/tu_map_merge.py --maps <dir> --pairs out/renut_map/base_to_tu.json
"""
import argparse
import bisect
import collections
import json
import os


def alike(a, b):
    common = sum(min(a.get(k, 0), b.get(k, 0)) for k in set(a) | set(b))
    return common / max(sum(a.values()), sum(b.values()), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--maps', required=True)
    ap.add_argument('--pairs', required=True)
    a = ap.parse_args()
    path = os.path.join(a.maps, 'func_map.json')
    fmap = json.load(open(path))
    old = json.load(open(os.path.join(a.maps, 'base_sigs.json')))
    new = json.load(open(os.path.join(a.maps, 'tu_sigs.json')))
    pairs = json.load(open(a.pairs))
    claimed = {v[0]: k for k, v in fmap.items()}
    count = collections.Counter()
    for o, v in pairs.items():
        n = v['nights']
        if o not in old or n not in new:
            continue
        cur = fmap.get(o)
        if cur and cur[0] == n:
            continue
        if cur and cur[1] in ('same', 'shape', 'skel'):
            count['kept the map over propagate'] += 1
            continue
        holder = claimed.get(n)
        if holder and holder != o:
            if fmap[holder][1] in ('same', 'shape', 'skel'):
                count['target held by a better pair'] += 1
                continue
            del fmap[holder]
            count['displaced a weak pair'] += 1
        if cur:
            claimed.pop(cur[0], None)
        fmap[o] = [n, 'propagate', old[o][2], new[n][2], None]
        claimed[n] = o
        count['propagate'] += 1
    # by place
    starts = sorted(old, key=lambda k: int(k, 16))
    new_starts = sorted(new, key=lambda k: int(k, 16))
    new_ints = [int(k, 16) for k in new_starts]
    for i, o in enumerate(starts):
        if o in fmap:
            continue
        lo = next((fmap[starts[j]][0] for j in range(i - 1, -1, -1) if starts[j] in fmap), None)
        hi = next((fmap[starts[j]][0] for j in range(i + 1, len(starts)) if starts[j] in fmap), None)
        if not lo or not hi or int(hi, 16) <= int(lo, 16):
            continue
        l, h = bisect.bisect_right(new_ints, int(lo, 16)), bisect.bisect_left(new_ints, int(hi, 16))
        best = None
        for c in new_starts[l:h]:
            if c in claimed:
                continue
            ca, cb = old[o][2], new[c][2]
            if abs(ca - cb) > 0.15 * max(ca, cb):
                continue
            s = 1.0 if old[o][3] == new[c][3] else alike(old[o][5], new[c][5])
            if s >= 0.8 and (best is None or s > best[0]):
                best = (s, c)
        if best:
            fmap[o] = [best[1], 'place', old[o][2], new[best[1]][2], None]
            claimed[best[1]] = o
            count['place'] += 1
    json.dump(dict(sorted(fmap.items())), open(path, 'w'))
    st = collections.Counter(v[1] for v in fmap.values())
    print(dict(count))
    print('pairs', len(fmap), 'of', len(old), dict(st))


if __name__ == '__main__':
    main()
