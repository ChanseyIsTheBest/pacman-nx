#!/usr/bin/env python3
"""pacman-nx (2026-11-03): what each saved shader container asks of the translator, read from its microcode without a run.

For every texture fetch: its own mag, min, mip and aniso filters ("const" = as the fetch constant says; XenosRecomp ignores
anything else). Also cube instructions (cube() returns 0 in shader_common.h, so a shader with no cube fetch reads a constant) and
vertex shaders exporting a vertex kill (on SPIR-V a NaN position, which drops a triangle with one killed vertex). The walk
over the control flow also says whether it reached every instruction. Bit layouts: XenosRecomp's shader_code.h and shader.h.

  python tools/shader_fetch_census.py [out/renut_shader_dump]
"""
import argparse
import collections
import glob
import os
import struct
import sys

FILTER = {0: 'point', 1: 'linear', 2: 'basemap', 3: 'const'}
ANISO = {0: 'off', 1: '1x', 2: '2x', 3: '4x', 4: '8x', 5: '16x', 7: 'const'}
DIM = {0: '1D', 1: '2D', 2: '3D', 3: 'Cube'}
EXEC_OPS = {1, 2, 3, 4, 5, 6, 13, 14}
VECTOR_CUBE = 18
EXPORT_KILL = 63


def be32(blob, offset):
    return struct.unpack_from('>I', blob, offset)[0]


def sampler_names(blob):
    """Sampler register -> name, from the container's D3DXSHADER_CONSTANTTABLE."""
    table = be32(blob, 0x10)
    if not table:
        return {}
    base = table + 4
    count, info = be32(blob, base + 12), be32(blob, base + 16)
    names = {}
    for i in range(count):
        entry = base + info + i * 20
        register_set, register = struct.unpack_from('>HH', blob, entry + 4)
        if register_set == 3:
            at = base + be32(blob, entry)
            names[register] = blob[at:blob.index(b'\0', at)].decode('ascii', 'replace')
    return names


def decode(path):
    blob = open(path, 'rb').read()
    shader = be32(blob, 0x18)
    start, size = be32(blob, 4) + be32(blob, shader), be32(blob, shader + 4)
    words = [be32(blob, start + i * 4) for i in range(size // 4)]
    names = sampler_names(blob)
    is_vs = bool(be32(blob, 0) & 1)
    result = {'name': os.path.basename(path)[:-4], 'vs': is_vs, 'fetches': [], 'other': [], 'cubes': [], 'kills': [], 'walked': set()}

    # The control flow: 3 words for 2 instructions, up to the first exec's address.
    first = len(words) // 3
    triple = 0
    while triple < first:
        w0, w1, w2 = words[triple * 3:triple * 3 + 3]
        for c0, c1 in ((w0, w1 & 0xFFFF), ((w1 >> 16) | ((w2 << 16) & 0xFFFFFFFF), w2 >> 16)):
            if (c1 >> 12) & 0xF not in EXEC_OPS:
                continue
            address, count, sequence = c0 & 0xFFF, (c0 >> 12) & 7, (c0 >> 16) & 0xFFF
            if count:
                first = min(first, address)
            for n in range(count):
                at = address + n
                result['walked'].add(at)
                d0, d1, d2 = words[at * 3:at * 3 + 3]
                if sequence & 1:
                    if d0 & 0x1F == 1:
                        register = (d0 >> 20) & 0x1F
                        result['fetches'].append({'at': at, 'register': register, 'name': names.get(register, '?'),
                                                  'mag': (d1 >> 12) & 3, 'min': (d1 >> 14) & 3, 'mip': (d1 >> 16) & 3,
                                                  'aniso': (d1 >> 18) & 7, 'dim': (d2 >> 14) & 3})
                    elif d0 & 0x1F:
                        result['other'].append((at, d0 & 0x1F))
                else:
                    if (d2 >> 24) & 0x1F == VECTOR_CUBE:
                        result['cubes'].append(at)
                    if is_vs and (d0 >> 15) & 1 and d0 & 0x3F == EXPORT_KILL and (((d0 >> 16) | (d0 >> 20)) & 4):
                        result['kills'].append(at)
                sequence >>= 2
        triple += 1
    result['unwalked'] = [(at, words[at * 3:at * 3 + 3]) for at in range(first, len(words) // 3) if at not in result['walked']]
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', nargs='?', default='out/renut_shader_dump')
    a = ap.parse_args()
    results = [decode(p) for p in sorted(glob.glob(os.path.join(a.folder, '*.bin')))]
    tally = collections.Counter()
    for r in results:
        print(r['name'], 'fetches', len(r['fetches']), 'other fetch ops', r['other'], 'cube', r['cubes'], 'kill', r['kills'],
              'not walked', [(at, ['%08X' % w for w in code]) for at, code in r['unwalked']])
        for f in r['fetches']:
            filters = (FILTER[f['mag']], FILTER[f['min']], FILTER[f['mip']], ANISO.get(f['aniso'], str(f['aniso'])))
            tally[('vs' if r['vs'] else 'ps',) + filters] += 1
            print('    @%-3d tf%-2d %-14s %-4s mag %s min %s mip %s aniso %s' % ((f['at'], f['register'], f['name'], DIM[f['dim']]) + filters))
    print('shaders %d (%d vs, %d ps)' % (len(results), sum(r['vs'] for r in results), sum(not r['vs'] for r in results)))
    for key, n in tally.most_common():
        print('fetches %d: %s mag %s min %s mip %s aniso %s' % ((n,) + key))
    print('with a cube instruction:', [r['name'] for r in results if r['cubes']])
    print('exporting a vertex kill:', [r['name'] for r in results if r['kills']])


if __name__ == '__main__':
    sys.exit(main())
