#!/usr/bin/env python3
"""pacman-nx (2026-11-02): the machine track's "no profile needed" list (docs/optimising-functions.md, "What to do next"):
counts every generated function by switch_hot_bulk.py's rules and, with --take, adds the next batch of eligible functions
to app/src/cpu/hot/localized_bulk.txt. The same filters as a profile's: tiny leaves, what the copy tool refuses, what a source
mentions and what is already listed stay out.

  python -I tools/bulk_batch.py                       the survey
  python -I tools/bulk_batch.py --take 500 [--max-instructions 4000]   the next batch, smallest functions first
  python -I tools/bulk_batch.py --take all
"""
import argparse
import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import localize_native as ln  # noqa: E402
import store_cards  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--take', default='')
    ap.add_argument('--tiny', type=int, default=12)
    ap.add_argument('--max-instructions', type=int, default=0, help='leave out larger functions (0: no limit)')
    ap.add_argument('--bulk', default=ln.BULK)
    ap.add_argument('--near', action='store_true', help='only what direct calls reach from sampled functions, nearest first')
    a = ap.parse_args()
    index = ln.Index(ln.GEN)
    listed = [e[0] for e in ln.list_entries(ln.LIST)]
    hand = ln.hand_entries()
    bulk_text = open(a.bulk, encoding='utf-8').read()
    have = {'sub_' + m.upper() for m in re.findall(r'^\s*([0-9A-Fa-f]{8})\b', bulk_text, re.M)}
    hooks = ln.Hooks(listed + sorted(have))
    sizes = ln.addresses(ln.GEN)

    def raw_ok(sub):
        for _, l in index.body(sub):
            l = store_cards.restore_text(l)
            if 'REX_RAW_ADDR(' in l and not (ln.RAW_VECTOR_STORE.match(l) or ln.RAW_MEMSET.match(l) or ln.RAW_LOAD.match(l)):
                return False
        return True

    count = collections.Counter()
    eligible = []
    for sub, f in index.funcs.items():
        if not sub.startswith('sub_'):
            count['named helper'] += 1
            continue
        if sub in listed or sub in hand or sub in have:
            count['on a list'] += 1
            continue
        insns = sizes.get(sub, (0, 4 * (a.tiny + 1)))[1] // 4
        if not f['callees'] and not f['unknown'] and insns <= a.tiny:
            count['tiny leaf'] += 1
            continue
        if hooks.replaced(sub):
            count['a source mentions it'] += 1
            continue
        why = ln.fits(index, hooks, sub)
        if why == 'raw guest access' and raw_ok(sub):
            why = None
        if why:
            count['refused: ' + why.split(':')[0].split(',')[0][:30]] += 1
            continue
        count['eligible'] += 1
        eligible.append((insns, sub, len(f['callees'])))
    for k, v in count.most_common():
        print(f'{v:7d} {k}')
    eligible.sort()
    print(f'eligible instructions: {sum(e[0] for e in eligible)} ({len(eligible)} functions); largest {eligible[-1][:2] if eligible else None}')
    if a.near:
        # pacman-nx (2026-11-02): code that runs first: by direct calls from the functions a profile sampled, nearest first.
        seeds = {'sub_' + m.upper() for m in re.findall(r'^\s*([0-9A-Fa-f]{8})\b[^\n]*samples', bulk_text, re.M)}
        distance = {s: 0 for s in seeds}
        frontier = sorted(seeds)
        while frontier:
            following = []
            for sub in frontier:
                f = index.funcs.get(sub)
                for callee in (f['callees'] if f else ()):
                    callee = callee.removeprefix('__imp__')  # a hooked callee's original: the same function
                    if callee not in distance:
                        distance[callee] = distance[sub] + 1
                        following.append(callee)
            frontier = following
        by_distance = collections.Counter(distance.get(e[1], -1) for e in eligible)
        print(f'{len(seeds)} sampled seeds; eligible by call distance (-1: not reached by direct calls):',
              ', '.join(f'{d}: {n}' for d, n in sorted(by_distance.items())))
        eligible = sorted([e for e in eligible if e[1] in distance], key=lambda e: (distance[e[1]], e[0]))
    if not a.take:
        return
    take = eligible if a.take == 'all' else eligible[:int(a.take)]
    if a.max_instructions:
        take = [e for e in take if e[0] <= a.max_instructions]
    lines = bulk_text.rstrip('\n').split('\n')
    for insns, sub, calls in take:
        lines.append(f'{sub[4:]} eligible, {insns} instructions, {calls} direct callees')
    open(a.bulk, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print(f'{len(take)} functions added to {a.bulk}')


if __name__ == '__main__':
    main()
