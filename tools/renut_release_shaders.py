#!/usr/bin/env python3
"""katamari-nx (2026-11-02, futari-nx's and peggle2-nx's tools/renut_release_shaders.py): the Switch build's Renut shader
files for a build that can be distributed (app/out/renut_switch_release/), and the file the web installer makes, for tests.

    python tools/renut_release_shaders.py [--glsl out/deko3d_shaders/glsl_opt] [--runtime app/out/pc/shader_capture]
                                          [--cache app/out/renut_switch/shader_cache_switch.cpp]

Writes into app/out/renut_switch_release/:
  shader_cache_switch.cpp   the shader table (numbers: hashes, fetch masks, vertex input formats) without the SPIR-V
                            (the deko3d back end never reads it; the PC's Vulkan one does)
  deko3d_glsl_switch.cpp    the 4 shaders the game makes at run time, built into the NRO. It compiles their HLSL with its
                            own D3DX at start, so they are in none of its files for the installer to find.
  sd/deko3d_glsl.bin        the package of the 13 shaders stored in default.xex, which the web installer makes from the
                            player's files and puts beside the NRO (this one is the Python tools' copy: game data, for
                            tests only, never distributed)
app/cmake/banjo_renut_gpu.cmake (BANJO_RENUT_RELEASE_SHADERS) builds with these files.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def package(glsl_dir, names, out_dir):
    """tools/deko3d_shader_package.py over the given shaders only."""
    os.makedirs(out_dir, exist_ok=True)
    src = os.path.join(out_dir, 'glsl')
    shutil.rmtree(src, ignore_errors=True)
    os.makedirs(src)
    for n in names:
        shutil.copyfile(os.path.join(glsl_dir, n), os.path.join(src, n))
    subprocess.run([sys.executable, '-P', os.path.join(ROOT, 'tools', 'deko3d_shader_package.py'), '--glsl', src,
                    '--out', out_dir, '--raw'], check=True)
    shutil.rmtree(src)


def strip_spirv(text):
    """shader_cache_switch.cpp without the SPIR-V: the assembler's .incbin goes, its sizes are 0, and every entry's
    SPIR-V offset and size (the 4th and 5th numbers of g_shaderCacheEntries' lines) are 0."""
    text, n = re.subn(r'// banjo-nx: the compressed SPIR-V.*?\.previous\\n"\);\n',
                      'const uint8_t g_compressedSpirvCache[] = {0};  // no SPIR-V (deko3d reads none)\n',
                      text, flags=re.S)
    if n != 1:
        sys.exit('renut_release_shaders: the SPIR-V block of shader_cache_switch.cpp not found')
    text = re.sub(r'(g_spirvCache(?:Compressed|Decompressed)Size\s*=\s*)\d+', r'\g<1>0', text)

    def entry(m):
        fields = m.group(2).split(', ')
        fields[3] = fields[4] = '0'
        return m.group(1) + ', '.join(fields)
    text, n = re.subn(r'^(\t\{ )(0x[0-9A-F]+, \d+, \d+, \d+, \d+)', entry, text, flags=re.M)
    if not n:
        sys.exit('renut_release_shaders: no entry of g_shaderCacheEntries found')
    if 'incbin' in text:
        sys.exit('renut_release_shaders: an .incbin is left in the shader table')
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glsl', default=os.path.join(ROOT, 'out', 'deko3d_shaders', 'glsl_opt'))
    ap.add_argument('--cache', default=os.path.join(ROOT, 'app', 'out', 'renut_switch', 'shader_cache_switch.cpp'))
    ap.add_argument('--runtime', default=os.path.join(ROOT, 'app', 'out', 'pc', 'shader_capture'),
                    help='the captures of the shaders the game makes at run time: built into the NRO')
    ap.add_argument('--out', default=os.path.join(ROOT, 'app', 'out', 'renut_switch_release'))
    a = ap.parse_args()
    names = sorted(f for f in os.listdir(a.glsl) if re.fullmatch(r'(vs|ps)_[0-9A-F]{16}\.glsl', f))
    if not names:
        sys.exit(f'renut_release_shaders: no shaders in {a.glsl}')
    os.makedirs(a.out, exist_ok=True)
    runtime = {f[:-4].upper().replace('VS_', 'vs_').replace('PS_', 'ps_') + '.glsl' for f in os.listdir(a.runtime)
               if re.fullmatch(r'(vs|ps)_[0-9a-fA-F]{16}\.bin', f)}
    if not runtime or not runtime <= set(names):
        sys.exit(f'renut_release_shaders: the run-time shaders of {a.runtime} are not all in {a.glsl}')
    package(a.glsl, sorted(set(names) - runtime), os.path.join(a.out, 'sd'))
    os.remove(os.path.join(a.out, 'sd', 'deko3d_glsl_switch.cpp'))  # the installer's file is never built in
    package(a.glsl, sorted(runtime), a.out)
    text = open(a.cache, encoding='utf-8').read()
    with open(os.path.join(a.out, 'shader_cache_switch.cpp'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(strip_spirv(text))
    print(f'renut_release_shaders: {len(runtime)} shaders built in, {len(names) - len(runtime)} beside the NRO -> {a.out}')


if __name__ == '__main__':
    main()
