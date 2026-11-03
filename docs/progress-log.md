# Progress log

The work in order, newest last. Times are AEST, 2026-11-02 unless noted.

| When | What |
|---|---|
| 17:07 | Read the docs in the request's order. |
| 17:09 | Extracted the game (909 entries, 219 MiB) and the DLC (399 entries, 147 MiB); `pacman-nx` made from katamari-nx-public's files. |
| 17:14 | Katamari's addresses, hooks, natives, lists, pgo, icon, settings and DLC pack list out. First codegen: 117 files, no errors. |
| 17:20 | setjmp / longjmp, pointer and gap sweeps (101, seven removed as mid-function labels), jump tables clean, register diet audited and on. |
| 17:25 | First PC build attempts: git-ignored FFmpeg files, the shader dump folder, host tools, an empty-list fix in `tools/localize_native.py`. |
| 17:30 | D3D pairing: 321 of 356 hooks placed, device layout measured and checked against guwange-nx (the same XDK). |
| 17:50 | Emulated GPU: boots to the title screen, 60 fps, sound. |
| 18:05 | Renut on Vulkan: logo, title, menus, gameplay. Automatic front buffer added; the 4 run-time shaders captured. |
| 18:08 | Census of gameplay: 157 draws a frame, 100 % DrawVerticesUP, no command buffers, no memexport, no shadows. |
| 18:16 | First Switch NRO: 29.7 MB, 0 errors, deko3d only (NVK not linked); shader package 17 shaders, all compile with uam. |
| 18:18 | First Ryujinx run in this port's data folder: deko3d initialises, the title draws, the scripted pad reaches gameplay. |
| 18:30 | RenderDoc in Ryujinx: the white maze is the two 64 x 64 x 64 colour look-ups, whose slices past the first hold stale memory. The emulator's copy engine never reads the destination's Z. |
| 18:38 | `banjo_renut_volume_stacked`: a one-level volume as a host 2D array. On the PC, on and off give the same maze. |
| 18:46 | Ryujinx with the key on (`emu3_vol`): maze, ghosts and GAME SPEED match the PC; 60 fps in gameplay with the verify keys on, 99.8 % fast draws, every verify line 0 differences. |
| 18:54 | Idle run (`emu4_attract`, 195 s): the title stays up, so this game has no attract loop there (the demo is behind X in the start menu). |
| 18:58 | PC profile with `--banjo_pc_profile_top=400`: the list goes from 63 to 484 functions. First batch of eligible functions: 1,500, smallest first (1,984 in all). The gameplay profile in Ryujinx waits: free commit memory 7.2 to 7.9 GB, under the request's 8 GB. |
| 19:11 | Batch one (1,984 copies): PC verify 145 million calls compared, 0 differences, 938 reached. NRO 41.5 MB. |
| 19:24 | Batch one in Ryujinx: 984,634 calls compared, 0 differences, 944 reached, picture right. A first try read nothing: my test toml had its keys after `[input_p2]`, where they belong to that table. |
| 19:49 | Batch two (4,984 copies): NRO 55.6 MB, Switch build 10.5 minutes. |
| 20:02 | Menu tour on batch two: PC 257 million calls compared, 0 differences, 1,690 reached; Ryujinx 1.09 million, 0 differences, 1,608 reached. It stuck on the Leaderboards dialog, which asks for an Xbox LIVE sign-in. |
| 20:15 | Skin tour in Ryujinx: Types A to J draw, the DLC's included (`skinH` opened from the install), 2.48 million calls compared, 0 differences, 1,841 reached. A skin change is a load: 2.5 to 5.4 fps for up to 10 s with the guard on. |
| 20:16 | Batch three: the 665 eligible functions direct calls reach from sampled ones (5,649 in all). The other 3,873 eligible functions are reached by no direct call from sampled code. |
| 20:44 | Batch three on the PC: 126 million calls compared, 0 differences, 2,299 of 5,649 reached. |
| 21:07 | Batch three on the Switch: NRO 62.5 MB. |
| 21:08 | The user: enough testing on Windows. PC runs stop here; every later check is in Ryujinx. |
| 21:21 | A first long game in Ryujinx fell from 50 fps to 0.02 fps at timer 3:12 and never recovered in the 3 minutes left. |
| 21:35 | The same game again with `tools/host_sampler.ps1`: dips to 3.6 fps that recover to 55-60, during other sessions' builds and runs, free commit down to 5.1 GB. Timer past 3:12. |
| 21:36 | First package: `D:\pacman\builds\2026-11-02_2136_first_b3`. |
| 22:00 | A/B check in play (`emu14_abv`, 8 s halves, verify keys on): all 15 targets flipped, 0 differences, 2.04 million calls compared, 2,272 reached. The picture stays right through bomb, power pellet and the FAILED screen. 60 fps while the PC is quiet. |
| 22:10 | The user takes over to test on the console; emulator testing stops here. The shipping-conditions run (`emu15_play`) was stopped early, so the share of samples still in generated code was not measured and the results screens stay untested. The list stays at 5,649 copies: the other 3,873 eligible functions were not taken. Package `2026-11-02_2136_first_b3` is the one to test (NRO md5 865544ac1d348b159a38bf732edb869c, commit cdda066fc580). |
| 23:03 | The user's report of a `vpkuwus` aliasing bug: present in this SDK, as it is in `vpkd3d128` types 3 to 5; this game uses neither aliased. Builders fixed and the generator compiled. The NRO and package are unchanged. The user extended the time limit to 11 am and is testing on the console. |
| 23:23 | Ridge Racer 6's warning: the batches never re-ran the generator, only the passes, over their own output. Fresh generation compared function by function: 11,183 of 11,239 identical, the other 56 harmless (inline choice, 5 extra barriers, 17 folded constants that match the image). The NRO and package stay as they are. |
| 06:05 | Ridge Racer 6's write-up: the curve between Renut and the emulated GPU, which I had put down to the emulated GPU's output, is the display's gamma ramp. Computed from its formulas it lands within 0.6 of every level measured at the title. Notes corrected. `configs/renut_game_gamma.toml` added to the repo and the package for the user to decide on, never run here. The NRO is unchanged. |
| 07:30 | Viva Piñata's three translator gaps (a fetch's own filters, `cube()`, vertex kill on SPIR-V), checked at the user's request from the saved microcode with no run: all three are in the code and this game's 17 shaders reach none of them. 16 fetches all defer to the fetch constant, 0 cube instructions, 0 vertex kill exports. No fix needed. |
| 08:08 | Halo 3's loop-region miscompile (`loop_locals.py`, a region ending inside a switch): not hit here. Its check reports 0, the one function with the shape was read by hand, and the hot copies' 162 switches hold no write-backs. Its fix is not ported; nothing rebuilt. |
| 09:50 | First console logs. Boot: 90 s of CLI11 option registration, quadratic in the hot copies' cvars, fixed; Ryujinx shows frames in the second 10 s block. Exit: bejeweled3-nx's order fix, plus the watchdog and log writer closed before the exit. Double buffering and its queue drain from sa2-nx, on by default, with a release point for a game with no frame limiter. The final NRO has not been run: the user tests it on the console. |
| 10:51 | Second console run: boot and exit fixes confirmed. Input lag 64 ms at 60 fps, 51 ms of it waiting: every image late, the drain has no effect because this port has no frame pacing, and its margin cuts late input. Next: frame_cap = "60" on the console (no build). |
| 10:57 | futari-nx's frame pacing ported at the user's request, on by default: the display thread starts each frame at the refresh plus a measured phase, and a queue drain skips one start. Built, not run: the user tests it on the console. |
| 11:04 | Third console run, with Futari's pacing: input -> display 64 ms down to 33 ms at 60 fps, one window of a 63 s run. The display queue is still stuck after load hitches; two small fixes proposed. |
| 11:08 | Two pacing fixes at the user's go-ahead: the frame after a hitch waits for the next refresh, and a drain that worked resets the retry wait to 5 s. Built, not run: the user tests on the console. |
| 11:22 | Fourth console run: input -> display 16.6 ms at 60 fps in gameplay, down from 64 ms; 0 late images for over 2 minutes. |
| 14:36 | 1.0.0: LTO NRO, the user's icon, 1080 lines docked, only the player's options in the toml, logging off, `language`. Web installer from katamari-nx-installer. Clean install from its zip passes in Ryujinx. Published at the user's request. |
| 16:40 | The user: the game was missing title update 3. The base XEX never asks for DLC, so the DLC skins noted on 2026-11-02 were the base game's. |
| 17:30 | TU3 applied (v0.0.3.2, XDK 2.0.21250): new game folder, functions mapped, 323 hooks and the device layout moved, 5,428 of 5,649 hot copies kept (99.6 % of the console's samples). |
| 18:45 | First native PC run on TU3: stable, DLC mounted, 4 startup shaders captured, black picture. |
| 18:53 | Black picture: three guest table addresses left at the base's. Fixed: DX+ title, menu and gameplay draw. |
| 19:05 | The Achievements & Medals list drew over its panel: user clip planes never applied. Compared with the emulated GPU, applied as a scissor. |
| 19:37 | Everyday TU3 NRO 62.2 MB, 0 veneers. The user: go straight to LTO. |
| 20:05 | TU3 LTO NRO 63.3 MB, 25 minutes, 0 veneers. SD folder for the user's console test; it has not run. |
