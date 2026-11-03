#!/usr/bin/env python3
"""pacman-nx (2026-11-02): the hand edits that move Renut's Direct3D layer to PAC-MAN CE DX (XDK 2.0.11164), after
tools/renut_hook_remap_pacman.py (hooks) and tools/renut_device_offsets_pacman.py (the device-offset sites).
docs/pacman-notes.md, "Renut's Direct3D at this game's addresses", has the evidence. From bangaio-nx's
bangaio_renut_port.py, whose XDK has the same layout up to 0x4188.

Each edit is an exact (file, old, new) text pair; a pair whose new text is already there is skipped (idempotent), one whose
old text is missing is reported.

  python -I tools/renut_port_pacman.py [--check]
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GPU = os.path.join(ROOT, 'app', 'src', 'renut_engine', 'gpu')

EDITS = [
    # 1. Guest data addresses (tools/d3d_data_addrs_pacman.py).
    ('d3d/d3d_native_state.cpp', 'kRenderStateTable = 0x82AD8E48;', 'kRenderStateTable = 0x8246A250;  // pacman-nx: tools/renut_state_tables.py;'),
    ('d3d/d3d_native_state.cpp', 'kSamplerStateTable = 0x82AD9308;', 'kSamplerStateTable = 0x8246A710;  // pacman-nx: tools/renut_state_tables.py;'),
    ('d3d/d3d_native_state.cpp', 'kFormatTable = 0x820FA9D0;', 'kFormatTable = 0x82061AD8;  // pacman-nx: Katamari\'s 128 bytes, word for word;'),
    ('d3d/hooks/resource.cpp', 'kFormatTable = 0x820FA9D0;', 'kFormatTable = 0x82061AD8;  // pacman-nx: Katamari\'s 128 bytes, word for word;'),
    ('d3d/hooks/device.cpp', 'kGlobalQwordVa = 0x82AD93F8;', 'kGlobalQwordVa = 0x8246A868;  // pacman-nx: the build qword 2.0.11164.0;'),
    ('d3d/hooks/device.cpp', 'kVdGlobalDeviceImportSlot = 0x82000750;', 'kVdGlobalDeviceImportSlot = 0x82000500;  // pacman-nx: loaded value 0xFFCAE000, as Katamari\'s;'),
    ('d3d/hooks/device.cpp', 'kDeviceCapsVa = 0x820FC1F8;', 'kDeviceCapsVa = 0x82061E58;  // pacman-nx: Katamari\'s 304 bytes, word for word;'),
    ('d3d/hooks/draw.cpp', 'kFullViewport = 0x820FAEB4;', 'kFullViewport = 0x820617BC;  // pacman-nx: Katamari\'s 24 bytes, word for word;'),
    ('d3d/hooks/resource.cpp', 'kGameNoLargePagesVa = 0x8315DFE0;', 'kGameNoLargePagesVa = 0x8277C58C;  // pacman-nx: XPhysicalAlloc sub_821B4988;'),
    ('d3d/hooks/resource.cpp', 'kHiZOwnerVa = 0x8315E830;', 'kHiZOwnerVa = 0x8277C5B0;  // pacman-nx: CreateSurface sub_821C4040, Destroy sub_821C0A10;'),
    ('d3d/hooks/resource.cpp', 'REX_IMPORT(__imp__sub_824CAB98, GameXMemFree', 'REX_IMPORT(__imp__sub_823FBDE8, GameXMemFree'),
    ('d3d/hooks/device.cpp', 'REX_IMPORT(__imp__sub_824C1C10, GuestGetCurrentThreadId', 'REX_IMPORT(__imp__sub_821B4660, GuestGetCurrentThreadId'),
    # 2. XDK behaviour read in this game's code: SetTexture(NULL) clears the fetch constant's type bits (`lwzx r10,r11,r31;
    # rlwinm r10,r10,0,0,29; stwx` at 0x821C43A8 of sub_821C42A0), as Bangai-O's and Peggle 2's and unlike N&B's.
    ('d3d/d3d_native_state.cpp', '''    device.SetW(Fetch(sampler, 4), dword4);
    device.Dirty(kPendingFetch, FetchBit(sampler));
  }
  device.SetW(off::Textures + sampler * 4, texture);''', '''    device.SetW(Fetch(sampler, 4), dword4);
    device.Dirty(kPendingFetch, FetchBit(sampler));
  } else {
    // pacman-nx: this game's SetTexture (sub_821C42A0, XDK 2.0.11164) clears a NULL texture's fetch constant type bits
    // (`lwzx; rlwinm r10,r10,0,0,29; stwx` at 0x821C43A8), as Bangai-O's and Peggle 2's do; N&B's does not.
    device.SetW(Fetch(sampler, 0), device.W(Fetch(sampler, 0)) & ~3u);
  }
  device.SetW(off::Textures + sampler * 4, texture);'''),
    # 2b. The device's own vertex declaration (no comment for the offset tool to read): InitializeApiState sub_821CF3D0
    # `stw r11,12368(r31)`, N&B's update +0x2FA8 + 168.
    ('render/draw.cpp', 'constexpr u32 kDeviceDeclarationOffset = 0x2F98;',
     'constexpr u32 kDeviceDeclarationOffset = 0x3050;  // pacman-nx: sub_821CF3D0 `stw r11,12368(r31)`'),
    # 3. The chunk boundaries of the replay's delta compare and census: N&B's 11776 is 11944 here; the last multiple of 64
    # from 10112 below it is 11904 (bangaio-nx's value, the same layout there).
    ('backend/queued.cpp', 'constexpr u32 kDeltaPrivateUnreadBegin = 10880, kDeltaPrivateUnreadEnd = 11776;',
     'constexpr u32 kDeltaPrivateUnreadBegin = 10880, kDeltaPrivateUnreadEnd = 11904;  // pacman-nx: XDK 2.0.11164 (bangaio-nx\'s value)'),
    ('render/draw.cpp', 'static_assert(kCensusTailBegin < 10880 && 11776 < d3d::kDeviceSnapshotSize);',
     'static_assert(kCensusTailBegin < 10880 && 11904 < d3d::kDeviceSnapshotSize);'),
    ('render/draw.cpp', 'state = XXH3_64bits_withSeed(device_state + 11776, d3d::kDeviceSnapshotSize - 11776, state);',
     'state = XXH3_64bits_withSeed(device_state + 11904, d3d::kDeviceSnapshotSize - 11904, state);'),
    # 4. XDK 2.0.11164's snapshot is 0x3258 bytes (12888, as Bangai-O's): its last chunk is 24 bytes; 40 chunks are read.
    ('backend/queued.cpp', 'static_assert(kDeltaReadChunks.count == 39);  // N&B (SA2 40)',
     'static_assert(kDeltaReadChunks.count == 40);  // pacman-nx: as bangaio-nx (N&B 39, SA2 40)'),
    ('guest/command_buffers.cpp', 'static_assert(kLastChunkBytes == 32, "TakeLastChunk\'s loads");',
     '// pacman-nx: XDK 2.0.11164\'s snapshot (12888 bytes) ends in a chunk of 24 bytes.\nstatic_assert(kLastChunkBytes == 24, "TakeLastChunk\'s loads");'),
    ('guest/command_buffers.cpp', '''  const uint8x16_t a0 = vld1q_u8(device), a1 = vld1q_u8(device + 16);
  const uint8x16_t d0 = veorq_u8(a0, vld1q_u8(shadow)), d1 = veorq_u8(a1, vld1q_u8(shadow + 16));
  vst1q_u8(shadow, a0);
  vst1q_u8(shadow + 16, a1);
  return vmaxvq_u8(vorrq_u8(d0, d1)) != 0;''', '''  // pacman-nx: 24 bytes (16 + 8; Katamari's 32 were 16 + 16).
  const uint8x16_t a0 = vld1q_u8(device);
  const uint8x8_t a1 = vld1_u8(device + 16);
  const uint8x16_t d0 = veorq_u8(a0, vld1q_u8(shadow));
  const uint8x8_t d1 = veor_u8(a1, vld1_u8(shadow + 16));
  vst1q_u8(shadow, a0);
  vst1_u8(shadow + 16, a1);
  return (vmaxvq_u8(d0) | vmaxv_u8(d1)) != 0;'''),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    done = skipped = 0
    bad = []
    for rel, old, new in EDITS:
        p = os.path.join(GPU, rel.replace('/', os.sep))
        t = open(p, encoding='utf-8', errors='surrogateescape', newline='').read()
        crlf = '\r\n' in t
        o, n = (old.replace('\n', '\r\n'), new.replace('\n', '\r\n')) if crlf else (old, new)
        if n in t:
            skipped += 1
        elif o in t:
            if not a.check:
                t = t.replace(o, n, 1)
                open(p, 'w', encoding='utf-8', errors='surrogateescape', newline='').write(t)
            done += 1
        else:
            bad.append((rel, old[:70]))
    print(f'{done} edits applied, {skipped} already there, {len(bad)} missing')
    for b in bad:
        print('MISSING', b)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
