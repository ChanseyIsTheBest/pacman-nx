#!/usr/bin/env python3
"""pacman-nx (2026-11-02): moves Renut's hook table (app/src/renut_engine/gpu/d3d/hooks/*.cpp, at Beautiful Katamari's
addresses) to PAC-MAN CE DX's, from out/renut_map/hook_map.json (tools/renut_hook_map_pacman.py).

A placed hook becomes BANJO_RENUT_HOOK... (sub_<this game>, ...) with `// pacman-nx: Katamari sub_K, N&B sub_N; routes`.
One with no place becomes BANJO_RENUT_UNHOOKED_... (unlinked_<K>, ...): the handler compiles and nothing is registered,
and no address stays in the code ("Stale mentions" in docs/optimising-functions.md: an address another game's hook names
would block a copy of an unrelated function here). Two hooks may not map to one address: the second is left unhooked and
reported. Idempotent on a tree already moved (lines with `pacman-nx:` are skipped).

  python -I tools/renut_hook_remap_pacman.py [--dry-run]
"""
import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, 'app', 'src', 'renut_engine', 'gpu', 'd3d', 'hooks')
LINE = re.compile(r'^(\s*)BANJO_RENUT_(UNHOOKED_)?HOOK(_RAW)?(_SHARED)?\(\s*sub_([0-9A-F]{8})(.*)$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    hm = json.load(open(os.path.join(ROOT, 'out', 'renut_map', 'hook_map.json')))
    used, placed, off, dup = {}, 0, 0, []
    for name in sorted(os.listdir(HOOKS)):
        if not name.endswith('.cpp'):
            continue
        path = os.path.join(HOOKS, name)
        text = open(path, encoding='utf-8', newline='').read()
        nl = '\r\n' if '\r\n' in text else '\n'
        lines = text.split(nl)
        changed = False
        for k, line in enumerate(lines):
            m = LINE.match(line)
            if not m or 'pacman-nx:' in line:
                continue
            indent, was_off, raw, shared, addr, rest = m.groups()
            v = hm.get(f'{name}:{k + 1}:{addr}')
            if v is None:
                raise SystemExit(f'{name}:{k + 1}: not in the hook map (run tools/renut_hook_map_pacman.py on this tree)')
            target = v['target']
            if target and target in used:
                dup.append((name, k + 1, addr, target, used[target]))
                target = None
            suffix = f'{raw or ""}{shared or ""}'
            code, sep, comment = rest.partition('//')
            note = f'// pacman-nx: Katamari sub_{addr}' if not was_off else f'// pacman-nx: N&B sub_{addr}'
            if v['nb'] and not was_off:
                note += f', N&B sub_{v["nb"]}'
            if target:
                used[target] = addr
                routes = ','.join(sorted(v['routes']))
                lines[k] = f'{indent}BANJO_RENUT_HOOK{suffix}(sub_{target}{code.rstrip()}  {note}; {routes}{" " + v["why"][:90] if v["why"] else ""}'
                placed += 1
            else:
                lines[k] = f'{indent}BANJO_RENUT_UNHOOKED_HOOK{suffix}(unlinked_{addr}{code.rstrip()}  {note}; not in this game{": " + v["why"][:90] if v["why"] else ""}'
                off += 1
            changed = True
        if changed and not a.dry_run:
            open(path, 'w', encoding='utf-8', newline='').write(nl.join(lines))
    print(f'{placed} hooks placed, {off} unhooked, {len(dup)} duplicates')
    for d in dup:
        print('DUPLICATE', d)


if __name__ == '__main__':
    main()
