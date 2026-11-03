#!/usr/bin/env python3
"""pacman-nx (2026-11-02): which of this game's functions tools/localize_native.py's Hooks treats as replaced because a source
names their address, and whether anything really hooks them ("Stale mentions" in docs/optimising-functions.md). A mention
of a real function start that is no registered hook blocks a machine copy of an unrelated function.

  python -I tools/stale_mentions.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import localize_native as L  # noqa: E402

GEN = os.path.join(ROOT, 'app', 'generated')
starts = set()
for p in glob.glob(os.path.join(GEN, '*_recomp.*.cpp')):
    starts.update(re.findall(r'^DEFINE_REX_FUNC\(sub_([0-9A-F]{8})\)', open(p, errors='replace').read(), re.M))
hooks = L.Hooks([])
real = hooks.addresses & starts
print(f'{len(starts)} functions; sources mention {len(hooks.addresses)} addresses, {len(real)} of them this game\'s function starts')
# where each comes from
where = {a: [] for a in real}
for root in (os.path.join(ROOT, 'app', 'src'), os.path.join(ROOT, 'sdk', 'src'), os.path.join(ROOT, 'sdk', 'include')):
    for d, _, fs in os.walk(root):
        if os.path.abspath(d).startswith(os.path.abspath(os.path.join(ROOT, 'app', 'src', 'cpu', 'hot'))):
            continue
        for f in fs:
            if not f.endswith(('.cpp', '.h', '.inc', '.hpp', '.c')):
                continue
            text = L.strip_comments(open(os.path.join(d, f), encoding='utf-8', errors='ignore').read(), False)
            text = re.sub(r'__imp__\w+', ' ', text)
            for a in set(re.findall(r'(?<![0-9A-Fa-f])(82[0-9A-Fa-f]{6})(?![0-9A-Fa-f])', text)):
                if a.upper() in where:
                    where[a.upper()].append(os.path.relpath(os.path.join(d, f), ROOT).replace('\\', '/'))
by = {}
for a, fl in where.items():
    for f in fl:
        by.setdefault(f, []).append(a)
for f, l in sorted(by.items(), key=lambda x: -len(x[1])):
    print(f'{len(l):5} {f}  {" ".join(sorted(l)[:6])}')
