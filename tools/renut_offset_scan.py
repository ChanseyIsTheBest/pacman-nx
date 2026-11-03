#!/usr/bin/env python3
"""pacman-nx (2026-11-02): literals in Renut's sources that could still be device offsets at another layout: in the part of
the device that moved between XDKs (0x2B00-0x5F00), on lines neither tools/renut_device_offsets_pacman.py nor
tools/renut_port_pacman.py touched. Each line it prints is read by hand.

  python -I tools/renut_offset_scan.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GPU = os.path.join(ROOT, 'app', 'src', 'renut_engine', 'gpu')
NUM = re.compile(r'(?<![0-9A-Za-z_.])(0x[0-9A-Fa-f]+|\d+)(?:[uU])?(?![0-9A-Za-z_.])')
USE = re.compile(r'\b(W|B|F|Q|H|SetW|SetB|SetF|SetQ|SetH|bytes|device|TouchBits|kDevice\w*|off::\w+)\b')

for d, _, fs in os.walk(GPU):
    for f in fs:
        if not f.endswith(('.cpp', '.h', '.inc')):
            continue
        p = os.path.join(d, f)
        for i, line in enumerate(open(p, encoding='utf-8', errors='replace')):
            code = line.partition('//')[0]
            if 'pacman-nx' in line or not code.strip():
                continue
            hits = [n for n in NUM.findall(code) if not (n.startswith('0') and not n.startswith('0x') and n != '0') and 0x2B00 <= int(n, 0) < 0x5F00]
            if hits and USE.search(code):
                print(f'{os.path.relpath(p, GPU)}:{i + 1}: {hits} | {code.strip()[:110]}')
