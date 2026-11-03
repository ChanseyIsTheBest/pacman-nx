# PAC-MAN Championship Edition DX port: notes

This file records the port: what each step found, with its evidence. The project starts from a copy of katamari-nx
(`D:\beautifulkatamari\katamari-nx-public`, commit `f6c0efcd`, its files and not its history), itself from banjo-nx
(`D:\Banjo kazooie port\banjo-nx`). Both are read-only references. Comments that say "banjo-nx", "katamari-nx",
"sa2-nx" or "peggle2-nx" record findings from those ports. Where docs differ, katamari-nx's win, then banjo-nx's.

The request (2026-11-02, from 17:07 AEST): port PAC-MAN CE DX to the PC and the Switch with ReXGlue, the Switch the main
goal; work uninterrupted until 06:00 AEST without asking; package for the console by then.

## Decisions (made without asking, as the request said)

| What | Decision | Why |
|---|---|---|
| Game files | `D:\pacman\game` (the LIVE package `38D034D6...`), `D:\pacman\dlc` (`AllinOnePack`) | the request |
| `app/assets` | a junction to `D:\pacman\game` | no second copy; git-ignored |
| Internal project name | `renut`, as banjo-nx and katamari-nx | its CMake, post-codegen passes and glue name `renut_*`; the NRO, its title and the SD folder are pacman-nx |
| Bootstrap generator | katamari-nx's built `rexglue.exe` copied to `out/` for the first codegen runs | the build needs a generated tree first; the build then uses the generator it builds from `sdk/` |
| Git-ignored files the public base lacks | copied from the private `D:\beautifulkatamari\katamari-nx` (FFmpeg's `config.h`, `avconfig.h`, `ffversion.h`, the `*_list.c`, XenosRecomp's `dxc-bin`) | the public copy leaves out what their `.gitignore` covers, and the SDK does not build without them |
| Host tools | glslangValidator, spirv-cross, uam copied from katamari-nx's `out/` | built from the same sources this tree carries |
| Sources no CMake file names | removed (`native/*` but the capture, `renut_engine/hooks.cpp`, `townsfolk.cpp`, `me/banjo_me_hooks.cpp`, ...) | other games' addresses: "Stale mentions" in `docs/optimising-functions.md` |
| Hand-written natives | none, the header holds only the common code | the request: only from a console profile |

## The game (2026-11-02)

- `default.xex`: title **58410A8C** ("PAC-MAN CE DX"), media `491BC35A`, version 0.0.0.2, built 2010-10-26; base
  `0x82000000`, entry `0x820FA448`, image `0x7C0000` (8 MB); AES + LZX. Code range (generated `REX_CODE_BASE / SIZE`)
  `0x820F0000-0x82458B7C` (3.4 MB, 11,246 functions).
- XDK: every static library **2.0.11164** (XAPILIB, D3D9, D3DX9, XGRAPHC, XACT3, X3DAUD, XONLINE, XAUD, XMCORE; XAUDIO2 and
  XAPOBA QFE 3), LINK 10.0.10224, C1/C2 16.0.10224. **The same XDK as Guwange** (guwange-nx, `D:\mushihemesama`), between
  Futari's 9328 and Bangai-O's 20209 in the "XDK versions of our Xbox 360 ports" doc.
- Imports `xam.xex` (94) and `xboxkrnl.exe` (260), 2.0.11164, minimum 2.0.9199.
- Data: 222 MB. `data/` (`gamedata*.bin`, fonts `.abc`, 788 PNG including skins `skinA..H`, `cskinA..F`, `DemoData`),
  `geui/` (45 `.geui` UI layouts, `X360/_Textures.rs`, `_TextTables.rs`), `data/xb360` (XACT: `.xgs`, `.xsb`, `.xwb`). No other
  code module. It is an XBLA game (`ArcadeInfo.xml`).
- DLC (`AllinOnePack`, "All-in-One Pack", content type 2): 147 MB: `data/gamedata{1-4}_addition.bin`, 364 PNG, four sound banks
  `data/xb360/pcedlc{0-3}*`. No code.

## Code generation (2026-11-02)

- Config: `app/renut_config.toml`. First run (katamari-nx's built generator, 4.5 s): 117 files, 58 MB, **no** "target not in
  any function", no unresolved branch.
- **setjmp / longjmp** by shape: setjmp `0x823F88E0` (`stfd f14,0(r3)`, the only one), longjmp `0x823F85C0` (`lfd f14,0(r7)`,
  the only one).
- **Pointer sweep** (`tools/pointer_fixpoint.py`): 5,604 gaps, 51 candidates, 48 accepted; fixpoint in pass 2.
  **Gap sweep** (`tools/gap_sweep.py`): 136 candidates, 53 accepted; fixpoint in pass 2.
- **Seven of those were not functions** and are removed (`tools/override_labels_check.py`, new: SEH, FALL and BRANCH shapes):
  `0x820FDFA4` starts with `mr r8,r8`, MSVC's scope marker (the pointer is in a `__try` scope table, conditional branches of its
  parent go to it); `0x821A4750`, `0x821A506C`, `0x822BC914`, `0x822BD340`, `0x822BD4A0`, `0x8241D5A0` have an instruction
  running into them (exception-filter code and epilogue tails: `li r3,8` then `bl`; `ld r31,-16(r1)` then `blr`). As functions they
  read r31 / r30 from zeroed locals under `non_volatile_as_local`. 94 entries remain.
- **Jump tables** (`tools/switch_check.py`): 139 switches, 137 indirect; truncated 0, wrong targets 0, missed 0, switches at a call
  through a function table 0. Two with no bound in the code (`sub_8221F6E8` 17 cases, `sub_822D6190` 16 cases). Three odd shapes:
  `0x823BF2E8` and `0x823C1050` are indirect calls through function tables (right), `0x823D7658` is a 22-case switch on a 16-bit
  index the caller bounds.

- **First boot stop** (emulated GPU): `Call to invalid or unregistered function at guest address 0x82306978`, a comparator passed to a
  sort (`lis r11,0x8230; li r5,4; addi r6,r11,27000` at `0x8231FC7C`), its tail `0x823069EC` taken for a function by the generator. Declared
  over the whole body (`app/config/renut_funcs.toml`). `tools/wide_pointer_scan.py` (new: katamari-nx's three wider scans as one tool: every
  `lis`/`addi` pair with no window, every data word into the code, every vcall-thunk shape) finds no other: its 23 gap hits are this one, the
  save / restore helpers and import thunks (named functions), the entry point, and `__except` scope labels (reached only by the exception
  dispatcher, which this runtime does not run).

### Codegen options: the register diet (2026-11-02)

All on. `tools/non_argument_audit.py --noreturn=823F85C0,8219F2C0` (longjmp and `_CxxThrowException`, which the audit must know
or the callers of the two throw helpers `sub_820FEFB8` / `sub_820FEFF0` show as false RETs): ENTRY 285 (the helpers kept by name,
MSVC unwind funclets `addi r31,r12,-N`, `sub_823069EC` taking r11, `sub_823F8594` the stack probe), RET 1 (`sub_821AFC58` with
`sub_821AFD20`), HANDOVER 0. `tools/diet_keep_list.py` writes the keep list: 67 + 2 functions.

`tools/read_before_write.py` on code generated WITH the options: 37 lines, none a split piece after the seven removals:
functions with a prologue that save the registers they read on paths a state machine never takes (the image decoders, 0x822E-
0x8237); setjmp and its callers (`env.*` copies, handled by the generator); `xor r30,r30,r30`; `subfe` of one register; and
`sub_821ACDD4`, a data word (`0x821ACE00`) in front of `sub_821ACDDC`, never run. **No `share_registers` needed.**
`non_volatile_as_local_keep = ["v64-v127"]` from the start (katamari-nx's rc3 finding).

### First runs on the PC (2026-11-02)

- **Emulated GPU** (`banjo_renderer = "emulated"`, run `emu_gpu2`, after the comparator): boots to the title screen at 60 fps with sound, on the first
  full run. No CPU, kernel or file-system fix was needed beyond the function table. `license_mask = 1` for the full game.
- **The path wizard:** on the PC with Renut the app waits in `PathSetupWizard` unless `renut.cfg` (`game_data_root`, `user_data_root`) is next to the exe.
- **The FPS overlay crashes on the PC** (`FpsOverlayDialog::OnDraw` -> `ImGui::Begin`, read of 0x8): the dialog draws with the executable's ImGui copy, which
  has no frame open. katamari-nx's `crash.txt` has the same crash. `banjo_show_fps` now defaults to false.
- **The game's shaders.** The image holds 14 containers (13 unique): 6 vertex and 7 pixel. It also holds HLSL text (`uiVertexShader` / `uiPixelShader` at
  `0x82004D5F`, `FontVertexShader` at `0x820513A0`) and links the D3DX HLSL compiler: **it compiles those at run time**, at start. Their containers are
  deterministic, so Renut's capture finds them on the first run (2 + 2 so far, 17 in `out/renut_shader_dump`); the Switch gets them from the dump.
- **The automatic front buffer.** This game asks D3D for automatic front and back buffers (`p[14] = p[15] = 0`, unlike N&B, whose Renut logged "an automatic
  front buffer is not supported"), and ends a frame with `D3DDevice_Present` (`sub_8218AB20`, a tail call), which Katamari never called. Without the texture,
  Present resolved nothing and swapped 0. `native::CreateFrontBufferTexture`: the game's own call, `CreateTexture(w, h, 1, 1, 0, format, 0, 3)` at `0x821CF740`.

### What the game decides (porting-guide-renderer.md section 2; census of gameplay on the PC, 2026-11-02)

Run `census1` (Renut on Vulkan, `--frame_cap=60`, the scripted pad into a Beginner game with the sticks wandering; the 10-s lines):

| Question | PAC-MAN CE DX | N&B | Katamari |
|---|---|---|---|
| Where draws come from | 100 % immediate, 100 % `DrawVerticesUP`; 0 recorded command buffers (the game links none) | 98.5 % recorded | direct, 83-84 % UP in menus |
| Draws a frame in gameplay | about 157 (94,000 per 10 s) | about 5,000 | about 450 |
| Where resources come from | textures 100 % Create hook or `D3D_SetTextureHeader`; 0 vertex or index buffers bound for those draws | 5 % / 26 % | 100 % |
| Locks in play | 0 vertex, 0 index, 0 texture | | none |
| How state is set | hooked setters; every field group differs from draw to draw in the census (`fetch ... vertex fetch 100 %`) | 99.9 % setters | 87-88 % |
| Memexport | none | nearly all | none |
| Shadow passes, depth-only draws | none | ~2,200 draws | none |
| Targets | 2 render targets 11 MB (x1), 5 resolve targets 18 MB, 36 textures 84 MB | | |
| Threads (PC, % of all cores) | main 10 %, render 9.6 %, audio `XThread462C` 8.3 %, others 3-12 % | render 95 % of a core | |

So: the record-time items built for N&B's recorded buffers (resource / geometry objects, the replay stream, record lookups: A/B 45-50), the geometry
caches (whole-buffer copies, mesh objects: nothing but UP draws) and the memexport items have **nothing to act on here**; they cost nothing either
(no draws reach them), and the census numbers are their evidence. What applies: the per-draw fast path, pipelines by content, pushed constants, the
device snapshot deltas, the texture memo. Render thread 0.6-0.7 ms a frame and GPU 2.5-2.8 ms on the RTX 3060.

The game ticks per frame: at the PC display's 120 Hz it runs at double speed (timer 40 game-seconds in about 25 s). `--frame_cap=60` is the PC reference.
The Switch's 60 Hz is the game's own.

### Renut against the emulated GPU: which colours are right (2026-11-02)

`tools/compare_captures.py` (new): the title in Renut on Vulkan and in the emulated GPU differ on 9.2 % of the pixels, by at most 18 levels, the same in every
frame. Level by level it is one smooth curve: Renut 16 -> emulated 6, 32 -> 16, 64 -> 48, 128 -> 115, 192 -> 185, 240 -> 238, 0 and 255 fixed. The logo's flat colours
settle it, counted in the game's source art (`geui/X360/loadingmainmune.png`, 2048 x 2048): Renut's (85,77,35), (0,163,122), (253,204,0) appear 24,568, 15,872 and
14,217 times; the emulated GPU's (70,62,19), (0,153,109), (253,198,0) appear 0, 10 and 7 times. **Renut shows the art unchanged; the emulated GPU's output path applies a
curve.** Renut on Vulkan stays the reference, as the request says. (Katamari saw the same kind of difference against D3D12 and did not chase it.)

**Corrected 2026-11-03: that curve is the display's gamma ramp, not an emulator quirk.** The art count shows that Renut draws the art unchanged. It says nothing about what the 360 does to the picture at scan-out, so it was wrong to take it as proof that Renut's colours are the right ones. Ridge Racer 6's session traced the same curve in its game: the D3D device starts with a linear ramp corrected through `VdGetCurrentDisplayGamma` (type 2 in the SDK: sRGB decode, then BT.709 encode), and Renut's present skips the ramp unless `banjo_renut_game_gamma` is on.

Those two formulas, computed, against what was measured above (no new run):

| Renut | Emulated GPU, measured | Computed |
|---|---|---|
| 16 | 6 | 5.9 |
| 32 | 16 | 16.6 |
| 64 | 48 | 48.4 |
| 128 | 115 | 115.3 |
| 192 | 185 | 184.8 |
| 240 | 238 | 238.2 |
| (85,77,35) | (70,62,19) | (70.0, 61.7, 19.3) |
| (0,163,122) | (0,153,109) | (0.0, 153.1, 108.9) |
| (253,204,0) | (253,198,0) | (252.8, 198.1, 0.0) |

- **The ramp's offset here is `+0x3B70`.** `sub_821B8440` (`D3DDevice_SetGammaRamp`) compares its 1,536 bytes at `r31 + 15216`, and `Video::NoteGameGamma` reads the same place.
- **This game loads no ramp of its own.** The only call to `sub_821B8440` in the generated code is inside `sub_821CF638`, which the native device start replaces (`hooks/device.cpp`), and that sets the corrected linear ramp.
- **The hook's arguments are the wrong form for this XDK, and it never runs.** `D3DDevice_SetGammaRamp_hook` takes (device, ramp), Katamari's TU3 form. Here the ramp is the third argument (`mr r4,r5` at entry, the caller passes `li r4,0`), so the hook would return at its `!ramp_va` check. Fix it at the next rebuild.
- **Shipped off, as a config.** It changes the picture, so `configs/renut_game_gamma.toml` is the user's decision. It has never run on this port, on any renderer. Ridge Racer 6 reports it working on D3D12 and deko3d in Ryujinx. The curve matches the emulated GPU; a real 360 has not been compared.
- **Not checked here:** Halo 3's gamma textures, gamma targets and target exponent bias (Renut's `TextureSign::Gamma` is unused and there is no `renutGammaFetch` here), and whether this game's glow is weak against the emulated GPU. Only the title was compared with it, and the numbers above cover that difference.

### Three translator gaps this game doesn't reach (2026-11-03)

Viva Piñata's session reported three gaps in the shared translator. All three are in this tree's code, and none of this game's 17 shaders reaches them. `tools/shader_fetch_census.py` (new) reads the saved containers' microcode, with no run:

| Gap | Where in the code | This game |
|---|---|---|
| A fetch's own mag, min and mip filters are ignored | `magFilter` and the others appear only in `shader_code.h`'s struct | 16 fetches, all in pixel shaders. All 16 leave mag, min, mip and aniso to the fetch constant, which Renut does follow |
| `cube()` returns 0 | `shader_common.h` | 0 cube instructions, 0 cube fetches |
| Vertex kill on SPIR-V is a NaN position | `shader_recompiler.cpp`, `hasVertexKill` | 0 of the 8 vertex shaders export a kill; they export position and interpolators only |

- **The decoder holds up.** The walk reaches every instruction in all 17 containers, apart from one all-zero word at the end of each. Sampler names and 2D or 3D dimensions line up with each container's constant table (`rgb2hsvTex`, `hsv2rgbTex` as 3D).
- **Is the set complete?** The 17 are the image's 13 unique containers plus 4 the game compiled from HLSL text at run time and Renut captured, and the runs logged no missing shader. The game's and DLC's data files (366 MB) hold 0 containers by the same header check, though a compressed file would not show. A shader compiled only in a scene no run reached would not be in the dump.
- **No fix needed here.** The picture and the NRO are unchanged. The filter fix would matter on this game only if a later census found a fetch naming its own filter.

### Loop regions ending inside a switch: not hit here (2026-11-03)

Halo 3's session found a miscompile in `tools/loop_locals.py`: when a loop region's last jump back is a case of a `switch`, the region ends mid-switch, and the later cases leave it without writing its locals back. This tree's copy of the pass has the same logic, but no generated function goes wrong because of it.

- **Halo's check** (`D:/halo 3/halo3-nx/tools/loop_switch_check.py`, run without `--fix`): 0 case jumps to repair.
- **The one function with the shape, `sub_821E93B0`, read by hand:** its region does end inside the switch, but at case 13, the last case. Every other case goes out through a stub that writes `r3` back, and only `default:`, a trap, comes after it.
- **The hot copies, which Halo's script does not scan:** 162 switches in the 5,649 copies, none with a write-back inside.
- **A switch with no write-back inside is safe to skip.** The pass adds a store at the region's end unless it has nothing to store, or its last line is a plain jump (a case's indented `goto` does not count as one; `sub_821E93B0` has that store).

Halo's `switch_end` fix is not ported, because nothing here needs it and it would change `sub_821E93B0`'s generated text. Port it before generating code for a changed executable.

### The first console run: boot, exit, double buffering (2026-11-03)

**Boot: about 90 s at every start, caused by the hot copies' keys.** The console's `rex_profile.log` has nine 10 s blocks of `main (UI)` at 100 % and 0 fps before the log's first line. After that the game reached the title menu in about 10 s, about 5 s of it a "Now Loading" screen with no file activity.

- **Cause:** `rex::cvar::Init` gave CLI11 every cvar as an option, and CLI11's `add_option` compares each new option with all the ones before it. Each of the 5,649 copies has a cvar, so about 6,500 options, quadratic.
- **The old emulator runs show the same growth,** seconds at 0 fps before the first frames: 0 copies 0 s, 1,984 copies 40 s, 4,984 copies 110-130 s, 5,649 copies 120-280 s. I had put those slow starts down to the emulator retranslating a new NRO. That was wrong, and the batches should have been judged on boot time as well.
- **Fix:** `cvar::Init` registers only the cvars the command line names. A homebrew launch names none.
- **Measured in Ryujinx, not yet on a console:** the `[boot]` line (new) gave `static constructors 4806 ms, command line 65 ms, app start 9393 ms`, the emulator's JIT included, and frames began in the second 10 s block.
- **It also explains `Stack sampling: disabled` on the console and in the emulator.** The sampler reads `switch_profile_stacks` once, after its warm-up, and the toml had not been loaded yet. Sampling now really is on with `renut.toml`, at 1 ms, so that toml costs more than it did in the first console run. `renut_play.toml` is the one to judge the game by.
- **First start only:** the DLC install took 46 s (147 MB). Not changed; it does not repeat.

**Exit: three fixes.**

1. `std::terminate` from `MnkInputDriver::DetachFromWindow`: `ReXApp::OnDestroy` reset the window before the runtime. Fixed as peggle1-nx and bejeweled3-nx did: the runtime first.
2. After `ISelfController::Exit`, Ryujinx (which stubs it) showed the stall watchdog faulting in `fwrite` to `banjo_profiler.log`, the file system being closed. `banjo::profiler::Stop` at `OnShutdown` ends the watchdog and closes that log.
3. Then the log writer thread faulted the same way. `rex::CloseLogFile` in `ExitProcess` ends it and closes the file.

Faults 2 and 3 come after the process has asked to end, and were seen only in Ryujinx; a console ends the process there. Fix 1 and fix 2 were run in Ryujinx: `ServiceAm Exit` reached with no `rex_crash.log`. Fix 3 has not been run, nor the exit on a console.

**Double buffering and its input-lag fix, both on by default (the user's call).** From sa2-nx (`sa2_renut_double_buffer`, `sa2_renut_queue_drain`), itself from ketsui-nx through futari-nx. Keys here: `pacman_renut_double_buffer`, `pacman_renut_queue_drain`. Two swapchain images; the display thread counts new images not finished at their refresh, and after 60 in a row the game's next frame goes a refresh later, once.

- **Different from sa2-nx:** this game has no frame limiter (`frame_cap = "Off"`), so `renutFrameLimit` returned at once and the display thread never started: no `[display]` line in the console's logs. It now starts the thread when the drain is on and sleeps one refresh when asked. The release phase is not used: only the drain's `Start` and `TakeHold` run with the cap off.
- **So `banjo_display_sync` runs for the first time on this port.** The base's notes record stalls in Ryujinx with that thread active, so a future emulator run may need `banjo_display_sync = false`, which also turns the drain off.
- **Judged at the first refresh after the present,** sa2-nx's 60 fps form. NiGHTS changed this for its interval 2; this game presents every refresh.
- **Not run anywhere yet.** The 10 s `[display]` line gives the late images, the drains and the margin. Frequent drains would mean images are finishing close to the refresh, and each one costs a refresh of game time.

Viva Piñata's gamma finding (a XDK that only flags the default ramp at init, so the Swap's load overwrites the game's own) does not apply here: `sub_821CF638` calls `sub_821B8440` directly at init and nothing else calls it.

### Input lag on the console: the double buffer's queue stays stuck (2026-11-03)

The second console run (`renut_003.log`, handheld, `renut.toml`, stack sampler on) confirmed the boot fix (`[boot] static constructors 244 ms, command line 1 ms, app start 2040 ms`) and the exit (`Switch: exiting process (0)`, no new `rex_crash.log`). It also showed that double buffering as ported makes input lag worse.

In the 7 windows at a steady 60 fps, input -> display is 64.3 ms:

| Stage | ms | What it is |
|---|---:|---|
| Input read -> Swap | 4.1 | The game's own work |
| Swap -> present | 27.4 | The render thread is busy 2.7 ms a frame; the rest is the frame waiting its turn |
| Present -> GPU done | 16.4 | The GPU takes 6.8 ms a frame; the last list waits for the image the display still shows |
| GPU done -> on screen | 16.3 | Waits for the next refresh |

So 13.6 ms of work and 50.7 ms of waiting, 3 refreshes. `[display]` counts 4,204 of 4,204 new images not finished at their refresh, present -> display fixed at 32.7 ms, 5 drains over the run with no effect, and the late input margin at its +8 ms limit.

- **The margin costs lag.** It took the late input delay from 10.9 ms in the first console run to 1.6 ms, and input -> GPU done rose from 38.9 ms to 48.2 ms. The first run had no display thread, so its input -> display was not measured.
- **Why the drain does nothing here:** it holds one release a refresh late, which empties the queue only if the game then stays on that grid. sa2-nx (`sa2_renut_vblank_pacing`), NiGHTS (`nights_renut_swap_pacing`) and Ketsui all pace their frames. This port has `frame_cap = "Off"`: the game is paced by back-pressure from the render thread, so the sleep this port added in `renutFrameLimit` is absorbed at once and the queue refills. My note above that frequent drains would mean images finishing close to the refresh was wrong for this case: the queue is stuck, not close.
- **The fix: futari-nx's pacing, on by default (`pacman_vblank_display_sync`), the user's call.** Not sa2-nx's: sa2-nx holds the game at its Swap on a timer, with the phase judged from the refresh a frame reached. Futari's display-side vblank thread starts each frame. At each refresh it tests the newest image's fence, moves the phase (0.25 ms later after 3 s of images in time, 2 ms back and held 5 minutes at a miss), waits the phase and gives the tick; a queue drain skips one tick.
  - **What is the same as Futari:** the fence test, the phase rule, the skipped tick, the thread's priority 0x2C on core 2, and the 8 ms guard.
  - **What is different:** Futari's frames count vblanks, so it calls Direct3D's vblank handler. This game's frames do not, so the display thread (`display_sync.cpp`) wakes the game at its Swap (`renutFrameLimit` -> `WaitForFrameStart`), with a 50 ms timeout. A tick that came while the frame ran starts the next at once; several give one start.
  - **Lost:** the queue between the game and the screen was also a cushion. A frame that misses its refresh now waits a whole one, and the work is 13.6 ms of 16.7 ms, though those stages overlap.
  - **Not run anywhere yet.** The `[display]` line gives the phase, misses, late images, drains and frames started. Estimate: about 17 ms input -> display if an image makes the next refresh, 33 ms if it takes two. Ketsui's console went from about 27 ms to 10-11 ms present -> scan-out once its queue emptied.
  - **`frame_cap` must stay `"Off"` for this.** A number uses the old limiter instead.

### Input lag with Futari's pacing: the third console run (2026-11-03)

A 63 s run (`renut.toml`, stack sampler on, handheld). Only its last 10 s window is steady 60 fps at gameplay's GPU load (6.94 ms), so these numbers are one window:

| Stage | Back-pressure | Futari's pacing |
|---|---:|---:|
| Input -> Swap | 4.1 ms | 3.4 ms |
| Swap -> present | 27.4 ms | 1.0 ms |
| Present -> display | 32.7 ms | 28.9 ms |
| Input -> display | 64.3 ms | 33.3 ms (max 33.5) |

- **The render thread's queue is gone.** That took off 30 ms.
- **The display queue is still stuck:** 601 of 601 images late in that window, so one refresh more than needed. Input -> display should reach about 16.7 ms unstuck (an estimate).
- **Below 60 fps in the first 50 s:** the load hitches, nearly the same as before pacing (1,432, 517, 885, 401 ms against 1,379, 522, 891, 410 ms). No new stutter in this short run.
- **Best reading of why it stays stuck (the logs only give 10 s counts):** a load hitch empties the queue, but the next frame then starts at once, at any point in the refresh, misses it and fills the queue again. Each refill soon after a drain doubles the wait for the next one. After 4 drains in loading it was probably about 40 s, and the run ended 20-30 s after the last. The window with the fourth drain has 78 images on time, the most of any.
- **`input -> GPU done` no longer measures the GPU here.** It is noted at the next frame's kicks and presents, and with the game idle between frames that is up to a refresh late.
- **The phase stayed at 0:** every late image counts as a miss and holds it for 5 minutes. Once the queue is clear this could give a few more ms.

Two fixes followed, both in `display_sync.cpp`; built, not yet run:

- **After a hitch, the next frame waits for the next tick** (`WaitForFrameStart`, `kResyncTicks` = 3: a frame of about 50 ms or more). A frame only a little late still goes at once, so a scene just over the budget does not fall to 30 fps.
- **A drain that worked resets the wait to 5 s** (`kDrainWorkedImages` = 30 images in time since the last drain), instead of doubling.

### Input lag: 16.6 ms on the console (2026-11-03)

The fourth console run (3 min 50 s, handheld, `renut.toml`, stack sampler on) with the two pacing fixes. In gameplay, 14 windows at a steady 60.0 fps:

| Stage | Back-pressure | Futari's pacing | With the two fixes |
|---|---:|---:|---:|
| Input -> Swap | 4.1 ms | 3.4 ms | 4.3 ms |
| Swap -> present | 27.4 ms | 1.0 ms | 0.5 ms |
| Present -> display | 32.7 ms | 28.9 ms | 11.9 ms |
| Input -> display | 64.3 ms | 33.3 ms | 16.6 ms (worst 16.9) |

- **The display queue is clear:** 0 late images and no drains from 11:16:14 to 11:18:34, and no frame over 100 ms for over 10,000 frames. The margin decayed from +8 ms to 0.
- **Loads:** 7 drains and 5 windows of late images in the first 50 s; the lag came down by itself once they ended.
- **Two windows near the end** had 54 and 111 late images and 2 drains, with input -> display at 18.1 and 19.8 ms (worst 33.5). It recovered within those windows.
- **The phase stayed at 0.** A later start could take a few ms more, but each late image holds it for 5 minutes. Left as it is.
- **Pacing costs time at boot.** The title menu opens about 18 s after the log starts, against about 10 s in the second run. It is the pacing, not the sampler: `load3d` came at 8.3 s in the run with the sampler and no pacing, and at 13.4 and 16.2 s in the two paced runs. The user is fine with this (2026-11-03: "don't worry about the title menu its fine").

### Settings: what changes the picture (2026-11-02)

Shipped: 720 lines handheld **and docked** (this game's only layout, the Xbox 360's own; Katamari's 1080 docked is `configs/renut_1080_docked.toml`, your decision), no SMAA
(Katamari's fixed settings had the key on), N&B's fur and portrait keys at their exact defaults. `msaa_level` is out of the player's toml: this game makes no MSAA target
(`p[4] = 0`, 2 render targets at x1). `frame_cap = "30"` would halve the game's speed: it ticks once a frame.

## The Switch build in Ryujinx (2026-11-02)

First NRO (`app/out/switch/renut.nro`, 29.7 MB; deko3d only, NVK not linked), the user's patched Ryubing with this port's own data folder (`D:\New folder\ryu-data\pacman`:
katamari's system folders, keys and firmware, its own SD card), `tools/run_ryujinx.ps1`, `out/emu/emu_verify.toml` (configs/renut_verify.toml, the scripted pad, a capture every 15 s).

Run `emu1` (240 s, every verify key on): deko3d comes up, the title draws as on the PC, the pad reaches gameplay and Pac-Man moves, scores, loses lives. 91,000 draws per 10 s, 99.8 % on the fast
path, no shader missing, 2 `fast_draw_verify` notes on a provisional pipeline (the kept pipeline is the generic variant while uam builds the specialised one: the same pixels by
construction, banjo-nx's docs/deko3d-renderer.md).

**Visual differences against the PC, in gameplay:** the maze's neon is white and its outlines warped; the ghosts are black (the sleeping ones right); "GAME SPEED 01" is black. The logo, title, menus, score, timer,
dots, fruit and Pac-Man match.

Tried: the shader package **without any GLSL pass** (`out/nopass`, run `emu2_nopass`, `deko3d_glsl.bin` beside the NRO): the same picture, so banjo-nx's passes are not the cause. Both builds use the same
64 x 64 x 64 volume texture (`[textures] first volume (3D) texture`), which Katamari never had.

The run scripts: `tools/run_ryujinx.ps1` moved every recent PNG under the SD folder out of it, which took this game's installed DLC (PNGs under `renut/`): now only `capturas/`.

### White maze: the emulator's copy engine has no Z (2026-11-02)

RenderDoc on run `rdc1` (`tools/rdc_passes.py`, `tools/rdc_draws.py`, new `tools/rdc_slices.py`). The maze's draws (events 151, 165, 179 of the capture) run `ps_D984A2D0F25F6721`: a 2D texture's colour is looked up in one 64 x 64 x 64 volume, the result (cycled by a constant) in a second. Both volumes are bound as 3D (the two 1 x 1 entries RenderDoc shows are the unused 2D-array bindings of the same fetches). Their **contents are wrong**: slice 0 is a clean colour gradient, slices 1 to 63 hold pieces of other textures and empty memory.

The cause is in the emulator, not the port: `Engine/Dma/DmaClass.cs` of the patched Ryubing never reads `DmaTexture.RegionZ` (the field exists, nothing uses it). deko3d uploads a 3D image one slice at a time, setting that Z; in Ryujinx every slice lands on slice 0 and the other 63 keep whatever the memory held before. Katamari never had a volume texture, so this never showed.

Fix for this port: `banjo_renut_volume_stacked` (`render/textures.cpp`, on in `app/pacman_switch_defaults.toml`) makes a one-level volume a host 2D array, read through the path the shaders already have for stacked textures (`tfetchStacked`: the layer from `z * depth`, the filter between layers and the Z address mode from the fetch constant). A layer is its own address, so no Z is needed, on the emulator or the console. Cost: two fetches for one where the shader reads a look-up. `configs/renut_volume_native.toml` puts the 3D images back; the console's copy engine does honour Z, so that config is for the console only.

## Enhancements on this game (2026-11-02)

`tools/enhancement_gap.py` and `tools/enhancement_state.py` compare this port with banjo-nx's `docs/enhancements-reference.md`.

- **Keys:** 245 of the reference's 260 keys are defined here. The 15 missing: seven hand natives of Banjo's own functions (`banjo_cpu_native_constants_ps` and the like: hand natives wait for a console profile, by the request's rule), `banjo_gpu_fetch_spec` (tessellated draws only; this game has none), `banjo_pool_lock` (Banjo's), `banjo_renut_check_worker` and `_core`, and four `banjo_ring_prover*` keys the reference itself records as removed.
- **Values:** of the 139 rows of the reference's table, 136 ship at the reference's value. The other three are `banjo_native_reverb` (off: Banjo's address), `banjo_renut_check_worker` and `banjo_gpu_fetch_spec` (absent, as above).
- **SLOWER ON THE CONSOLE:** `banjo_renut_replay_lookahead`, `banjo_renut_shadow_sort`, `banjo_renut_texture_slot_skip`, `banjo_renut_inline_line_compare` are all off.

What has work to do here follows from the census (100 % `DrawVerticesUP`, no command buffers, no memexport, no shadows, no fur). In a 10 s report of gameplay in Ryujinx:

| Item | Count in 10 s of gameplay | Acts here? |
|---|---|---|
| fast draws (`banjo_renut_fast_draw`, A/B 25) | 95,826 of 95,981 (99.8 %) | yes |
| render states by content (A/B 28) | 95,826 found | yes |
| texture slots by the slot's last or the memo (A/B 32) | 98.7 % | yes |
| bound textures not read again (A/B 39) | 704,788 skipped, 130,199 read | yes |
| whole clears of a target holding that clear (A/B 67) | 1,200 of 3,600 not sent | yes |
| device snapshot deltas | 276 bytes kept a draw, of 12,888 | yes |
| whole buffers, merged draws, mesh, resource, geometry objects, fetch cache (A/B 22, 33, 42, 45, 48, 47) | 0 | no: nothing but `DrawVerticesUP` reaches them |

`renut_ab.toml`'s list follows this table, not Katamari's.

## Long runs in Ryujinx and the shared machine (2026-11-02)

Run `emu10_game` fell from 50 fps to 0.02 fps at timer 3:12 and stayed there for the 3 minutes it had left. The guest threads' CPU rose together (the timer queue from 8 % to 82 %, an XThread from 12 % to 77 %), and XMA contexts went from about 0.2 ms to 36 ms each: everything slowed by the same factor, not one loop. That run had no host log.

The same game with `tools/host_sampler.ps1` (`emu11_repro`) and the A/B check (`emu13_abv`, `emu14_abv`): the slow windows move and they recover, and they line up with other sessions' `renut`, `clang++`, `rexglue` and `XenosRecomp`. Free physical memory fell to about 4 GB, and in two samples Ryujinx itself got 1 % of the CPU. In `emu14_abv` the game ran past 3:12 to the FAILED screen and held 60 fps while the PC was quiet.

So the slowdowns read as contention on a PC several ports share. **That is the likely cause, not a proof for the 0.02 fps run itself**, which had no host log and did not recover. The console has none of this; a frame rate that falls and stays down on the console would be new information.

Ryujinx also takes 2 to 3 minutes to reach the game with this NRO (15 s with the first 29.7 MB NRO). It grows with the NRO's code. Scripted presses count from the game's start, but a slow machine still moves where they land, so the test scripts press A more often than the menus need.

## Pack instructions with the destination as a source (2026-11-02)

The user passed on a bug report from another port: `vpkuwus128 v63,v63,v62`, whose builder wrote vD piece by piece while still reading vA and vB. It was in this SDK too (`sdk/src/codegen/builders/vector.cpp`), in `build_vpkuwus` and `build_vpkuhus`.

**This game is not affected, and the NRO did not change.** Three checks agree: the generated code has 0 `vpkuhus` or `vpkuwus` and 3 `vpkd3d128`, none with vD = vB (`v63,v127,3,1,3`, `v63,v127,5,2,2`, `v0,v63,5,2,2`); a scan of `out/renut_image.bin` over the code range finds the same; and Halo 3's `tools/vector_alias_scan.py` finds only 3 `vadduwm` hits, on `REX_LOOP_IN` lines, the false positives it warns of.

The report said the other piecewise builders were fine. In this copy they are not: **`build_vpkd3d128` types 3, 4 and 5 (FLOAT16_2, NORMSHORT4, FLOAT16_4) have the same bug when vD = vB.** Halo 3's and Kameo's sessions found it separately, and Kameo's game hits it.

A simulation of the emitted statements (20,000 random trials each):

| Case | Old code wrong | Fixed |
|---|---|---|
| `vpkuwus` vD distinct | 0 | 0 |
| `vpkuwus` vD = vA | 12,647 | 0 |
| `vpkuwus` vD = vB | 15,174 | 0 |
| `vpkuwus` vD = vA = vB | 14,530 | 0 |
| `vpkd3d128` NORMSHORT4 vD = vB, shift 0 / 1 / 2 | 19,827 / 18,162 / 0 | not simulated |

The fix: `vpkuhus` and `vpkuwus` build in `vTemp` and copy at the end. `vpkd3d128` types 3 to 5 read from a scoped copy (`vPackSrc`) when vD = vB, and only then, because types 3 and 5 use `vTemp` as scratch. The generator compiles with it, but this game emits none of these paths, so **the fixed code has never run**. The other builders that write elements piecewise (`vlogefp`, `vsubsws`, `vsrb`, `vsrab`, `vrlw`, `vsraw`, `vsrw`, `vupkd3d128`) read each source element before anything overwrites it: read, not run.

### Forcing a regeneration: two stamps (2026-11-02)

Ridge Racer 6's session warned that rexglue skips the generator when `generated/codegen.stamp`'s fingerprint matches, and the fingerprint covers the inputs, not the generator's own code. Deleting `codegen.build.stamp` re-runs only the post-codegen passes.

- **A new hot-function list:** delete `codegen.build.stamp`. The copies are made by the passes, so that is enough.
- **A change to the generator's builders:** delete `codegen.stamp` as well, or the change never reaches the generated code.

Every batch here was forced with `codegen.build.stamp` alone (`Codegen summary: 0 written ... 1 module(s) up to date` in the build logs, `codegen.stamp` from 17:44), so the passes ran several times over their own output. To see what that did, a fresh generator run and the same passes went into a scratch folder, using the generator with the pack fix, and were compared with the tree the package's NRO was built from:

- **11,183 of 11,239 functions identical**, 56 differ, 205 changed lines. `renut_pch.h` is identical. The scratch run does not make the copies in `generated/hot`, so those were not compared; they are made from this same text.
- **Inline copy or the plain call** of the same function, most of the lines: the fresh run split the code over 111 files and the tree has 117, and which calls get an inline copy depends on the file.
- **5 more `REX_LOOP_BARRIER()` in the tree:** safe, a little slower.
- **17 vector loads folded to constants in the tree only**, all in `sub_821D5B10`: fresh loads the same register from memory. All 17 constants match the image at their addresses.

So the repeated passes did not change what the NRO does, and the pack fix leaves this game's functions unchanged: no difference between the two runs comes from it.

## 1.0.0, the final build and the installer (2026-11-03)

**Settings (the user: only these in the toml).** `app/pacman_switch_defaults.toml` is compiled in; `app/pacman_switch.toml` is written next to the NRO as `pacman.toml` when it is missing: `language`, `input_xbox_layout`, `input_joycon_sideways`, `input_joycon_sideways_stick`, `[input_p1]`. Version 1.0.0, author ChanseyIsTheBest, the user's icon, 1080 lines docked.

**Language.** `language` (`app/src/pacman_language.cpp`, from nights-nx and sa2-nx) sets `user_language`, which `XGetLanguage` answers. The game has 8 languages (`geui/X360`: `_ee _jj _ff _gg _ss _ii _cs _ct`). Ryujinx: `auto` with the system language French gives the French menu; `japanese` over that gives the Japanese text.

**Logging off.** With `log_level = "off"` no log, stderr file or profile report is written, as sa2-nx and bejeweled3-nx do it (`RexSwitchRedirectStderr`, `RexSwitchEnsureLogDir`, the report gated in `switch_perf.cpp`). `rex_crash.log` is still written if the game crashes. An empty `logs` folder is still made: `NextSequentialLogPath` runs before `every_level_off` clears the path (`sdk/src/core/logging.cpp`). Left as it is for 1.0.0: another LTO link for an empty folder.

**The profiler's warm-up** now also waits for the configuration to be read, so `switch_profile_stacks` cannot be read at its default on a slow start.

**Shaders outside the NRO.** 13 of the 17 are in `default.xex`. The other 4 (its interface and font shaders) the game compiles from HLSL with its own D3DX at start, so no installer can find them. As banjo-nx's distribution build does, those 4 stay in the NRO (`tools/renut_release_shaders.py`). `banjo_renut_deko3d.cpp` looks in `deko3d_glsl.bin` beside the NRO, then in the NRO's own package (`FindOwn`).

**LTO, no PGO** (the user's choice): `tools/build_switch_release.bat`, `app/out/switch-lto`, NRO 63.4 MB. It needs its temporary files off C: when C: is short of space (`TMP`), and the link can run out of memory on a busy machine: resuming is enough.

**The installer** ([pacman-nx-installer](https://github.com/ChanseyIsTheBest/pacman-nx-installer), from katamari-nx-installer; its translator and shader tools are byte-identical to this tree's). It reads the LIVE package in place with `lib/stfs.js`. `test/deko3d_node.mjs`: 13 shaders, 11 identical to the native chain's text and 2 identical once SPIR-V's temporaries are renamed. The zip against the extracted folder: 879 of 879 game files by CRC-32, the DLC too; 450 MB, about 5 s.

**Clean install from that zip, Ryujinx, the LTO NRO:**

| Run | Result |
|---|---|
| The game's own default settings | `pacman.toml` written with the 4 keys and `[input_p1]`; no log file; empty `logs` folder |
| `auto`, system French, docked | French menu, `Render resolution 1920x1080 (1.5x)`, 16.6 ms input -> display, 0 late images |
| `japanese`, system French, handheld, Exit Game | Japanese text, 16.6 ms, `Switch: exiting process (0)`, `ServiceAm Exit` with no fault after it |

**Not run on a console:** the LTO NRO, 1080 lines docked, and the shaders from `deko3d_glsl.bin`. The 16.6 ms on the console was measured on the non-LTO build, handheld.

**The public repository** is one commit of this tree with the noreply author, not this history. Audit of the tree: no game file, generated code, token, email address or Windows user name.

## Renut's Direct3D at this game's addresses (2026-11-02)

- **State tables** (`tools/renut_state_tables.py`): render `0x8246A250` x101, sampler `0x8246A710` x20, all paired by default.
- **Pairs** (`tools/d3d_propagate.py`, Bangai-O's: unique shapes, the state tables, aligned call sites): Guwange 6,313, N&B 4,288,
  Bangai-O 3,113, Katamari 1,321.
- **Hook map** (`tools/renut_hook_map_pacman.py` + `.txt`, `tools/renut_hook_remap_pacman.py`): 356 hook lines, **321 placed** (277 by two
  or more routes that agree, 0 conflicts), 35 not in this game. The hand list holds the evidence for each that the routes could not place.
- **This game's Direct3D use is small**: DrawVertices, DrawVerticesUP and BeginVertices only (no indexed draw is linked, no index
  buffer, no tiling, no command buffers, no memexport from the game). The range is `0x821B5B58-0x821DC800`.
- **Device layout** (`tools/d3d_device_layout.py`): Guwange -> PAC-MAN delta 0 everywhere (1,040 same-shape pairs), as it must be:
  the same XDK. Bangai-O -> PAC-MAN 0 below 0x4188, then -4, then -8 from 0x5538. N&B's update -> PAC-MAN (3,549 pairs):

  | N&B update offsets | delta | Evidence |
  |---|---|---|
  | below 11776 | 0 | ring, fetch constants, fences, flags |
  | 11776 .. 13192 | +168 | the declaration 0x2E30 -> 0x2ED8, private render state, index buffer .. predication 0x31AC -> 0x3254 |
  | 13193 .. 13227 | +176 | the tiling clear values (guwange-nx's draw.cpp) |
  | 13228 .. 13255 | +176 | InKickOff 13232 -> 13408 |
  | 13256 .. 13443 | +180 | 13256, 13260 |
  | 13444 .. 13515 | +208 | VerticesRingEnd 0x3484 -> 0x3554 |
  | 13516 .. 24063 | +212 | CommandBuffer 13516 -> 13728, SwapCount, gamma, BehaviorFlags 23980 -> 24192 |
  | device size 0x5E00 | 0x5F00 | `sub_821C2008`: `li r3,24320; li r4,128` |

  `tools/renut_device_offsets_pacman.py` applies them from katamari-nx's `X->Y` comments. Compared line by line with guwange-nx's sources
  (the same XDK): 151 of 151 sites found there agree (after moving the tiling words by these numbers); guwange-nx's d3d.h constants all agree.
- **Guest data** (`tools/d3d_data_addrs_pacman.py`): format table `0x82061AD8`, full viewport `0x820617BC`, D3DCAPS9 `0x82061E58` (Katamari's
  bytes, word for word); build qword `0x8246A868` (2.0.11164.0); VdGlobalDevice record `0x82000500` (loaded value 0xFFCAE000, as Katamari's
  and N&B's); HiZ owner `0x8277C5B0` (CreateSurface, Destroy); no-large-pages flag `0x8277C58C` (XPhysicalAlloc `sub_821B4988`);
  XMemFree `sub_823FBDE8` (the device init's `lis r4,0xB180; li r3,0; bl`).
- **XDK behaviours read in this game's code**: SetTexture(NULL) clears the fetch constant's type bits (`lwzx r10,r11,r31; rlwinm
  r10,r10,0,0,29` at `0x821C43A8`), as Bangai-O's and unlike N&B's.
