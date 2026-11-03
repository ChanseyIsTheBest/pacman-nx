#!/usr/bin/env python3
"""pacman-nx (2026-11-03, title update 3): applies the update's hook addresses (out/renut_map/hook_map_tu3.json, from
tools/renut_hook_map_tu3.py), its guest data addresses and the device words tools/renut_device_offsets_tu3.py leaves to the sources.

A hook line keeps its comment and adds ` (base sub_<address>)`. Idempotent: lines already carrying `tu3` or `(base sub_` are skipped.

  python -I tools/renut_apply_tu3.py [--dry-run]
"""
import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GPU = os.path.join(ROOT, 'app', 'src', 'renut_engine', 'gpu')
HOOKS = os.path.join(GPU, 'd3d', 'hooks')

# The hooks the update links that the base did not (Peggle 2 and NiGHTS place them, and both agree).
ENABLE = {
    'D3DDevice_BeginExport_hook': '82235278',
    'D3DDevice_EndExport_hook': '82235370',
    'D3DLineTexture_LockRect_hook': '82238E60',
}

# (file, the literal text in the code, its replacement): one line each, checked to occur once.
EDITS = [
    ('d3d/hooks/device.cpp', 'kGlobalQwordVa = 0x8246A868', 'kGlobalQwordVa = 0x824F52D0'),
    ('d3d/hooks/device.cpp', 'kVdGlobalDeviceImportSlot = 0x82000500', 'kVdGlobalDeviceImportSlot = 0x82000544'),
    ('d3d/hooks/device.cpp', 'kDeviceCapsVa = 0x82061E58', 'kDeviceCapsVa = 0x820B6EB8'),
    ('d3d/hooks/device.cpp', 'kDeviceOffsetFlags = 10940', 'kDeviceOffsetFlags = 11068'),
    ('d3d/hooks/device.cpp', 'kDeviceOffsetFlags2 = 10941', 'kDeviceOffsetFlags2 = 11069'),
    ('d3d/hooks/device.cpp', 'kDeviceOffsetFenceCompletion = 10896', 'kDeviceOffsetFenceCompletion = 11024'),
    ('d3d/hooks/device.cpp', 'kDeviceOffsetGlobalQword = 10880', 'kDeviceOffsetGlobalQword = 11008'),
    ('d3d/hooks/device.cpp', 'd.SetW(0x2AA4, 0xE)', 'd.SetW(0x2B24, 0xE)'),
    ('d3d/hooks/device.cpp', 'kDeviceOffsetOwnerThread = 0x2A88', 'kDeviceOffsetOwnerThread = 0x2B08'),
    ('d3d/hooks/draw.cpp', 'kFullViewport = 0x820617BC', 'kFullViewport = 0x820B6664'),
    ('d3d/hooks/resource.cpp', 'kFormatTable = 0x82061AD8', 'kFormatTable = 0x820B6990'),
    ('d3d/hooks/resource.cpp', 'kHiZOwnerVa = 0x8277C5B0', 'kHiZOwnerVa = 0x828236EC'),
    ('d3d/hooks/resource.cpp', '__imp__sub_823FBDE8', '__imp__sub_82475E50'),
    ('d3d/d3d.h', 'kDeviceOffsetCreationThreadId = 10888', 'kDeviceOffsetCreationThreadId = 11016'),
    ('d3d/d3d.h', 'kDeviceOffsetIsTitleProcess = 10892', 'kDeviceOffsetIsTitleProcess = 11020'),
    ('d3d/d3d.h', 'kDeviceOffsetFenceTag = 0x2A9C', 'kDeviceOffsetFenceTag = 0x2B1C'),
    ('d3d/d3d.h', 'kDeviceOffsetSwapFenceTag = 0x2AB0', 'kDeviceOffsetSwapFenceTag = 0x2B30'),
    ('d3d/d3d.h', 'kDeviceOffsetSwapFlags = 0x2ABD', 'kDeviceOffsetSwapFlags = 0x2B3D'),
    ('d3d/d3d_native.h', 'FenceCompletion = 0x2A90', 'FenceCompletion = 0x2B10'),
    ('d3d/d3d_native.h', 'u32 FenceTag = 0x2A9C', 'u32 FenceTag = 0x2B1C'),
    ('d3d/d3d_native.h', 'CommandBufferTagMask = 0x2AA0', 'CommandBufferTagMask = 0x2B20'),
    ('d3d/d3d_native.h', 'TilePredication = 0x2AB4', 'TilePredication = 0x2B34'),
    ('d3d/d3d_native.h', 'RunPredication = 0x2AB8', 'RunPredication = 0x2B38'),
    ('d3d/d3d_native.h', 'u32 Flags = 0x2ABC', 'u32 Flags = 0x2B3C'),
    ('d3d/d3d_native.h', 'u32 Flags1 = 0x2ABD', 'u32 Flags1 = 0x2B3D'),
    ('d3d/d3d_native.h', 'u32 Flags2 = 0x2ABE', 'u32 Flags2 = 0x2B3E'),
    ('d3d/d3d_native.h', 'u32 Flags3 = 0x2ABF', 'u32 Flags3 = 0x2B3F'),
    ('d3d/d3d_native_state.cpp', 'kGprAllocation = 0x2AA8', 'kGprAllocation = 0x2B28'),
    ('d3d/d3d_native_state.cpp', 'kScreenExtentQueryMode = 0x2AA4', 'kScreenExtentQueryMode = 0x2B24'),
    ('render/draw.cpp', 'kDeviceDeclarationOffset = 0x3050', 'kDeviceDeclarationOffset = 0x3118'),
]
LIVE = re.compile(r'^(\s*(?:BANJO_RENUT_\w*HOOK\w*|REX_IMPORT|GUEST_FUNCTION_HOOK\w*)\s*\(\s*(?:__imp__)?sub_)([0-9A-Fa-f]{8})(\b.*)$')
OFF = re.compile(r'^(\s*)BANJO_RENUT_UNHOOKED_(HOOK\w*)\(unlinked_[0-9A-Fa-f]{8},\s*(\w+)\);(.*)$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    table = json.load(open(os.path.join(ROOT, 'out', 'renut_map', 'hook_map_tu3.json')))
    moved = enabled = 0
    missing = []
    for name in sorted(os.listdir(HOOKS)):
        if not name.endswith('.cpp'):
            continue
        p = os.path.join(HOOKS, name)
        text = open(p, encoding='utf-8', errors='surrogateescape', newline='').read()
        lines = text.split('\n')
        for i, line in enumerate(lines):
            end = '\r' if line.endswith('\r') else ''
            body = line.rstrip('\r')
            if '(base sub_' in body:
                continue
            m = LIVE.match(body)
            if m:
                old = m.group(2).upper()
                if old not in table or not table[old]['target']:
                    missing.append(f'{name}:{i + 1} {old}')
                    continue
                note = f' (base sub_{old})' if '//' in m.group(3) else f'  // base sub_{old}'
                lines[i] = m.group(1) + table[old]['target'] + m.group(3) + note + end
                moved += 1
                continue
            m = OFF.match(body)
            if m and m.group(3) in ENABLE:
                lines[i] = (f'{m.group(1)}BANJO_RENUT_{m.group(2)}(sub_{ENABLE[m.group(3)]}, {m.group(3)});{m.group(4)}'
                            f' (tu3: the update links it; Peggle 2 and NiGHTS place it here)' + end)
                enabled += 1
        if not a.dry_run:
            open(p, 'w', encoding='utf-8', errors='surrogateescape', newline='').write('\n'.join(lines))
    print(f'{moved} hooks moved, {enabled} enabled; {len(missing)} without a place: {missing}')
    done = 0
    for rel, old, new in EDITS:
        p = os.path.join(GPU, *rel.split('/'))
        text = open(p, encoding='utf-8', errors='surrogateescape', newline='').read()
        n = text.count(old)
        if n != 1:
            print(f'NOT ONCE ({n}): {rel}: {old}')
            continue
        done += 1
        if not a.dry_run:
            open(p, 'w', encoding='utf-8', errors='surrogateescape', newline='').write(text.replace(old, new))
    print(f'{done} of {len(EDITS)} literal edits')


if __name__ == '__main__':
    main()
