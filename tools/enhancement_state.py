#!/usr/bin/env python3
"""pacman-nx: each key of banjo-nx's docs/enhancements-reference.md table ("Every key") against what this port ships: the
value in dist/switch/pacman-nx/renut.toml, else in app/pacman_switch_defaults.toml, else the source's default. Prints the
keys that differ from the reference's "shipped" column, and the marked SLOWER ON THE CONSOLE ones with their value here.
  python tools/enhancement_state.py [reference.md]
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = sys.argv[1] if len(sys.argv) > 1 else r'D:\Banjo kazooie port\banjo-nx\docs\enhancements-reference.md'
ROW = re.compile(r'^\|\s*`([a-z0-9_]+)`\s*\|\s*([^|]*?)\s*\|\s*`?([^|`]*?)`?\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|$')
DEFINE = re.compile(r'REXCVAR_DEFINE_[A-Z0-9]+\(\s*([a-z0-9_]+)\s*,\s*("[^"]*"|[^,]+),')
SLOWER = ('banjo_renut_replay_lookahead', 'banjo_renut_shadow_sort', 'banjo_renut_texture_slot_skip',
          'banjo_renut_inline_line_compare')


def toml_values(path):
    out = {}
    for line in open(path, encoding='utf-8'):
        if line.startswith('['):
            break
        m = re.match(r'^([a-z0-9_]+)\s*=\s*(.*?)\s*(#.*)?$', line)
        if m:
            out[m.group(1)] = m.group(2).strip('"')
    return out


def source_defaults():
    out = {}
    for base in ('app/src', 'sdk/src', 'sdk/include'):
        for d, _, files in os.walk(os.path.join(ROOT, base)):
            for name in files:
                if name.endswith(('.cpp', '.h', '.inl', '.cc')):
                    text = open(os.path.join(d, name), encoding='utf-8', errors='replace').read()
                    for key, value in DEFINE.findall(text):
                        out.setdefault(key, value.strip().strip('"'))
    return out


def main():
    shipped = toml_values(os.path.join(ROOT, 'dist', 'switch', 'pacman-nx', 'renut.toml'))
    built_in = toml_values(os.path.join(ROOT, 'app', 'pacman_switch_defaults.toml'))
    source = source_defaults()
    rows = []
    for line in open(REF, encoding='utf-8'):
        m = ROW.match(line.rstrip())
        if m and m.group(1) not in {r[0] for r in rows}:
            rows.append(m.groups())
    same = differ = absent = 0
    for key, group, ref_value, kind, entry in rows:
        where, value = None, None
        for name, table in (('renut.toml', shipped), ('built-in', built_in), ('source', source)):
            if key in table:
                where, value = name, table[key]
                break
        if value is None:
            absent += 1
            print(f'ABSENT  {key:48} reference {ref_value:10} {kind:10} {entry[:40]}')
        elif value.lower() == ref_value.lower():
            same += 1
        else:
            differ += 1
            print(f'DIFFERS {key:48} reference {ref_value:10} here {value:10} ({where}) {kind:10} {entry[:40]}')
    print(f'{len(rows)} rows: {same} the same, {differ} differ, {absent} absent')
    print('marked SLOWER ON THE CONSOLE:')
    for key in SLOWER:
        print(f'  {key}: renut.toml {shipped.get(key)}, built-in {built_in.get(key)}, source {source.get(key)}')


if __name__ == '__main__':
    main()
