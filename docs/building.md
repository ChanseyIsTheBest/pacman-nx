# Building pacman-nx

You need your own copy of the game: the code generator and the shader tools read it. Nothing made from it is committed
(`.gitignore`): `app/assets`, `app/generated`, `out/`, `app/out/`, `tools/switch/icon/`.

## Tools

Windows; LLVM clang and the Visual Studio Build Tools (CMake and Ninja) for the PC build (`tools/pc_env.bat` names the
paths); devkitA64, libnx and deko3d from [devkitPro](https://devkitpro.org) for the Switch; Python 3 with `xxhash` and
`Pillow`. The deko3d host tools (`out/deko3d_tools`: SPIRV-Cross and the PC uam) come from `tools/deko3d_build_tools.sh`,
glslangValidator from `tools/build_glslang.bat`.

## 1. The game

```bat
python tools\stfs_extract.py <the LIVE package 38D034D6...> D:\pacman\game
python tools\stfs_extract.py <AllinOnePack> D:\pacman\dlc
mklink /J app\assets D:\pacman\game
```

Files git leaves out of a fresh copy of the SDK, which its CMake needs: FFmpeg's generated `config.h`, `libavutil/avconfig.h`,
`libavutil/ffversion.h` and the `*_list.c` files, and XenosRecomp's `thirdparty/dxc-bin`. Generate them, or copy them from a
working tree.

## 2. The PC build: code generation and the shader translator

```bat
tools\build_pc.bat
```

The first time, `out/renut_shader_dump` must exist before the configure:

```bash
python tools/renut_shader_dump.py --image out/renut_image.bin --out out/renut_shader_dump
```

The PC build runs the code generator (`app/renut_manifest.toml`), the post-codegen passes (`tools/post_codegen.py`) and Renut's
XenosRecomp over `out/renut_shader_dump`. Run it with `tools/run_pc.ps1`. `HOOKS=OFF` builds with Renut's hooks unregistered
(for the emulated GPU's first boot of a new game); `RENUT=OFF` leaves the renderer out.

## 3. The Switch build's shaders

```bat
powershell -File tools\switch_shaders.ps1
```

translates every shader of `out/renut_shader_dump` to GLSL and makes the everyday build's files (`app/out/renut_switch`, every
shader built into the NRO). `tools/deko3d_variant_cache.py` makes the prebuilt DKSH cache `deko3d_shaders.bin` that goes next to the NRO.

## 4. The Switch build

```bat
tools\build_switch.bat
```

The everyday build: `app/out/switch`, every shader built in, no LTO. `BUILD_DIR` and `CMAKE_EXTRA` select another folder and options.
Never run two of these builds at once: they share the SDK's archives in `sdk/out/switch-arm64`.

The released NRO (1.0.0: LTO, no PGO), in `app/out/switch-lto`:

```bat
python tools\renut_release_shaders.py
tools\build_switch_release.bat
```

It holds the shader table's numbers and the 4 shaders the game makes at run time, which no installer finds in its files
(`app/out/pc/shader_capture`); it reads the other 13 from `deko3d_glsl.bin` beside it, which
[pacman-nx-installer](https://github.com/ChanseyIsTheBest/pacman-nx-installer) makes from the player's files.

The fixed settings are `app/pacman_switch_defaults.toml`, compiled in; the player's are `app/pacman_switch.toml`, written next to the
NRO as `pacman.toml` when it is missing. A key added to `pacman.toml` overrides a fixed one (the test runs use that:
`tools/run_ryujinx.ps1 -Toml <file>`).
