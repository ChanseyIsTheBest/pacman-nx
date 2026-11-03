#!/usr/bin/env python3
"""pacman-nx: which keys of banjo-nx's docs/enhancements-reference.md this port's sources define, and which are missing.
The reference's marked "SLOWER ON THE CONSOLE" table is listed apart. Prints the missing keys with the first line each is on.
  python tools/enhancement_gap.py [reference.md]
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = sys.argv[1] if len(sys.argv) > 1 else r'D:\Banjo kazooie port\banjo-nx\docs\enhancements-reference.md'
KEY = re.compile(r'`((?:banjo|masseffect|katamari|renut|rex|kernel|thread|log)_[a-z0-9_]+)`')
DEFINE = re.compile(r'REXCVAR_DEFINE_[A-Z0-9]+\(\s*([a-z0-9_]+)')


def defined_keys():
    keys = set()
    for base in ('app/src', 'sdk/src', 'sdk/include'):
        for d, _, files in os.walk(os.path.join(ROOT, base)):
            for name in files:
                if name.endswith(('.cpp', '.h', '.inl', '.cc')):
                    try:
                        text = open(os.path.join(d, name), encoding='utf-8', errors='replace').read()
                    except OSError:
                        continue
                    keys.update(DEFINE.findall(text))
    return keys


def main():
    lines = open(REF, encoding='utf-8').read().split('\n')
    first = {}
    for i, line in enumerate(lines, 1):
        for key in KEY.findall(line):
            first.setdefault(key, (i, line.strip()))
    have = defined_keys()
    missing = sorted(k for k in first if k not in have)
    print(f'{len(first)} keys in the reference, {len(first) - len(missing)} defined here, {len(missing)} missing; {len(have)} keys defined here')
    for key in missing:
        i, line = first[key]
        print(f'{key:52} line {i}: {line[:110]}')


if __name__ == '__main__':
    main()
