#!/usr/bin/env python3
"""pacman-nx (2026-11-03, title update 3): where each of Renut's Direct3D hooks lives in the update (XDK 2.0.21250).

Every live hook line in app/src/renut_engine/gpu/d3d/hooks/*.cpp stands at the base game's address (XDK 2.0.11164). Routes:

  MAP  the base's address -> tools/map_functions.py's func_map.json
  PB   the base's address -> tools/d3d_propagate.py's base_to_tu.json (unique shapes, state tables, aligned call sites)
  P2   the same handler's address in Peggle 2's tree (XDK 2.0.21256) -> p2_to_tu.json
  NI   the same handler's address in NiGHTS's tree (XDK 2.0.21173) -> nights_to_tu.json

Each port's own tree is the truth for its hooks (nights-notes.md). A hook is placed when the routes that answer agree; a
disagreement is listed and left out until tools/renut_hook_map_tu3.txt answers it (`<base address> <the update's address or
-> <evidence>`: the file wins over everything). MAP's 'doubtful' and 'changed' pairs do not count against a route that agrees
with another: a new compile of a library is what they measure.

  python -I tools/renut_hook_map_tu3.py --maps <dir> [--write]
Writes out/renut_map/hook_map_tu3.json ({base address: {target, routes, handler}}) and prints the coverage.
"""
import argparse
import collections
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, 'app', 'src', 'renut_engine', 'gpu', 'd3d', 'hooks')
PEERS = {
    'P2': ('D:/peggle 2/peggle2-nx/app/src/renut_engine/gpu/d3d/hooks', 'p2_to_tu.json'),
    'NI': ('D:/nights/nights-nx/app/src/renut_engine/gpu/d3d/hooks', 'nights_to_tu.json'),
}
LINE = re.compile(r'^\s*(BANJO_RENUT_\w*HOOK\w*|REX_IMPORT|GUEST_FUNCTION_HOOK\w*)\s*\(\s*(?:__imp__)?sub_([0-9A-Fa-f]{8})\s*,\s*(.*)$')


def hook_lines(folder):
    out = []
    for path in sorted(glob.glob(os.path.join(folder, '*.cpp'))):
        with open(path, encoding='utf-8', errors='replace') as f:
            for n, line in enumerate(f, 1):
                m = LINE.match(line)
                if not m or 'UNHOOKED' in m.group(1):
                    continue
                rest = m.group(3).split('//')[0]
                handler = re.sub(r'\s+', '', rest).rstrip(';').rstrip(')')
                out.append((os.path.basename(path), n, m.group(1), m.group(2).upper(), handler))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--maps', required=True)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    rmap = os.path.join(ROOT, 'out', 'renut_map')
    fmap = json.load(open(os.path.join(a.maps, 'func_map.json')))
    base_pairs = json.load(open(os.path.join(rmap, 'base_to_tu.json')))
    routes = {}
    for key, (folder, name) in PEERS.items():
        pairs = json.load(open(os.path.join(rmap, name)))
        by = collections.defaultdict(set)
        for _, _, _, addr, handler in hook_lines(folder):
            by[handler].add(addr)
        routes[key] = (by, pairs)
    hand = {}
    hp = os.path.join(ROOT, 'tools', 'renut_hook_map_tu3.txt')
    if os.path.exists(hp):
        for line in open(hp, encoding='utf-8'):
            p = line.split('#')[0].split(None, 2)
            if len(p) >= 2:
                hand[p[0].upper()] = p[1].upper()
    result = {}
    agree = collections.Counter()
    problems = []
    for fname, n, macro, addr, handler in hook_lines(HOOKS):
        votes = {}
        status = None
        if addr in fmap:
            votes['MAP'] = fmap[addr][0]
            status = fmap[addr][1]
        if addr in base_pairs:
            votes['PB'] = base_pairs[addr]['nights']
        for key, (by, pairs) in routes.items():
            hits = {pairs[x]['nights'] for x in by.get(handler, ()) if x in pairs}
            if len(hits) == 1:
                votes[key] = hits.pop()
        distinct = set(votes.values())
        key = f'{fname}:{n}'
        if addr in hand:
            target = None if hand[addr] == '-' else hand[addr]
            result[addr] = {'target': target, 'routes': 'hand', 'handler': handler, 'line': key}
            agree['hand'] += 1
        elif len(distinct) == 1 and len(votes) >= 2:
            result[addr] = {'target': distinct.pop(), 'routes': ','.join(sorted(votes)), 'handler': handler, 'line': key}
            agree['two or more routes'] += 1
        elif len(distinct) == 1 and status in ('same', 'shape'):
            result[addr] = {'target': distinct.pop(), 'routes': 'MAP:' + status, 'handler': handler, 'line': key}
            agree['map only, same or shape'] += 1
        else:
            problems.append((key, addr, handler, status, votes))
            agree['open'] += 1
    print(dict(agree))
    for key, addr, handler, status, votes in problems:
        print(f'  OPEN {key} {addr} {handler[:44]} map:{status} {votes}')
    if a.write:
        json.dump(result, open(os.path.join(rmap, 'hook_map_tu3.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
