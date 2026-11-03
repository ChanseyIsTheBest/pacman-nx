#!/usr/bin/env python3
"""pacman-nx (2026-11-02): where each of Renut's Direct3D hooks lives in PAC-MAN CE DX (XDK 2.0.11164).

Every hook line in app/src/renut_engine/gpu/d3d/hooks/*.cpp stands at Beautiful Katamari's address and names N&B's in its
comment (`N&B sub_X`), or at N&B's for the ones Katamari could not place (BANJO_RENUT_UNHOOKED_*). Routes to this game:

  KAT  Katamari's address -> out/renut_map/kat_to_pac.json
  NB   N&B's address      -> out/renut_map/nb_to_pac.json
  BO   N&B -> Bangai-O by its out/renut_map/nb_to_bangaio_final.json -> out/renut_map/bo_to_pac.json
  GW   a name in Guwange's guwange_d3d_functions.txt (the same XDK as this game) -> out/renut_map/gw_to_pac.json

(tools/d3d_propagate.py makes the pairs: unique shapes, the two state tables, aligned call sites.) A hook is placed when
the routes that answer agree. A disagreement is listed and left out until tools/renut_hook_map_pacman.txt answers it
(`<N&B or Katamari sub> <this game's address or -> <evidence>`: the file wins over everything).

  python -I tools/renut_hook_map_pacman.py
Writes out/renut_map/hook_map.json ({line key: {target, routes, name}}) and prints the coverage.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, 'app', 'src', 'renut_engine', 'gpu', 'd3d', 'hooks')
MAP = os.path.join(ROOT, 'out', 'renut_map')
LINE = re.compile(r'^\s*BANJO_RENUT_(UNHOOKED_)?HOOK(_RAW)?(_SHARED)?\(\s*sub_([0-9A-F]{8})')
NOTE_NB = re.compile(r'N&B sub_([0-9A-F]{8})')
NAME = re.compile(r'//\s*(\w+)')
BANGAIO_FINAL = r'D:\bango\bangaio-nx\out\renut_map\nb_to_bangaio_final.json'
GUWANGE_NAMES = r'D:\mushihemesama\guwange-nx\app\src\renut_engine\guwange_d3d_functions.txt'


def load(name):
    p = os.path.join(MAP, name)
    if not os.path.exists(p):
        return {}
    return {k: v['nights'] for k, v in json.load(open(p)).items()}


def main():
    kat, nb, bo, gw = load('kat_to_pac.json'), load('nb_to_pac.json'), load('bo_to_pac.json'), load('gw_to_pac.json')
    bo_final = {}
    if os.path.exists(BANGAIO_FINAL):
        for k, v in json.load(open(BANGAIO_FINAL)).items():
            t = v['target'] if isinstance(v, dict) else v
            if t:
                bo_final[k.replace('sub_', '').upper()] = t.replace('sub_', '').upper()
    gw_names = {}
    if os.path.exists(GUWANGE_NAMES):
        for line in open(GUWANGE_NAMES, encoding='utf-8', errors='replace'):
            m = re.match(r'\s*(?:sub_)?([0-9A-Fa-f]{8})\s+(\w+)', line) or re.match(r'\s*(\w+)\s+(?:sub_|0x)?([0-9A-Fa-f]{8})', line)
            if m:
                a, n = (m.group(1), m.group(2)) if re.fullmatch('[0-9A-Fa-f]{8}', m.group(1)) else (m.group(2), m.group(1))
                gw_names[n] = a.upper()
    hand = {}
    p = os.path.join(ROOT, 'tools', 'renut_hook_map_pacman.txt')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            if line.strip() and not line.startswith('#'):
                a, t, why = line.split(None, 2)
                hand[a.replace('sub_', '').upper()] = (None if t == '-' else t.replace('sub_', '').replace('0x', '').upper(), why.strip())
    out, placed, none, conflict = {}, 0, [], []
    for fn in sorted(os.listdir(HOOKS)):
        if not fn.endswith('.cpp'):
            continue
        for k, line in enumerate(open(os.path.join(HOOKS, fn), encoding='utf-8', errors='replace')):
            m = LINE.match(line)
            if not m:
                continue
            addr = m.group(4)
            note = NOTE_NB.search(line)
            unhooked = bool(m.group(1))
            nb_addr = addr if unhooked else (note.group(1) if note else None)
            name = None
            for c in NAME.finditer(line):
                if c.group(1) not in ('katamari', 'N'):
                    name = c.group(1)
                    break
            routes = {}
            if not unhooked and addr in kat:
                routes['KAT'] = kat[addr]
            if nb_addr and nb_addr in nb:
                routes['NB'] = nb[nb_addr]
            if nb_addr and nb_addr in bo_final and bo_final[nb_addr] in bo:
                routes['BO'] = bo[bo_final[nb_addr]]
            if name and name in gw_names and gw_names[name] in gw:
                routes['GW'] = gw[gw_names[name]]
            key = f'{fn}:{k + 1}:{addr}'
            target = None
            why = ''
            for a in (addr, nb_addr):
                if a and a in hand:
                    target, why = hand[a]
                    routes['HAND'] = target or '-'
                    break
            if 'HAND' not in routes:
                values = set(routes.values())
                if len(values) == 1:
                    target = values.pop()
                elif len(values) > 1:
                    conflict.append((key, name, routes))
            if target:
                placed += 1
            elif 'HAND' not in routes and not routes:
                none.append((key, name, nb_addr))
            out[key] = {'target': target, 'routes': routes, 'name': name, 'nb': nb_addr, 'unhooked_before': unhooked, 'why': why}
    json.dump(out, open(os.path.join(MAP, 'hook_map.json'), 'w'), indent=1)
    agree = sum(1 for v in out.values() if v['target'] and len(v['routes']) >= 2)
    print(f'{len(out)} hook lines: {placed} placed ({agree} by two or more routes), {len(conflict)} conflicts, {len(none)} no route')
    for key, name, routes in conflict:
        print('CONFLICT', key, name, routes)
    for key, name, nb_addr in none:
        print('NONE', key, name, 'N&B', nb_addr)
    one = [(k, v['name'], v['routes']) for k, v in out.items() if v['target'] and len(v['routes']) == 1]
    for k, n, r in one:
        print('ONE', k, n, r)


if __name__ == '__main__':
    main()
