PAC-MAN Championship Edition DX on the Switch: notes for this package
======================================================================

Written for the first package, which has now run on a console. The sections below still hold, with these changes.

Changed after the first console test (2026-11-03)
-------------------------------------------------
Faster boot: about 90 s came off every start. The log's "[boot]" line gives the stages. Not yet measured on a console.
Exit Game: the crash on exit is fixed. Not yet run on a console.
Double buffering and its input-lag fix are on by default. To compare, set either in pacman.toml:
  pacman_renut_double_buffer = false
  pacman_renut_queue_drain = false
The display's refresh now starts the game's frames, Futari's way (input lag). To compare, in pacman.toml:
  pacman_vblank_display_sync = false
It needs frame_cap = "Off", as shipped: a number uses the old limiter instead.
The "[display]" line every 10 s gives the phase, misses, late images, queue drains, late input margin and frames started.
A console profile now works: renut.toml's switch_profile_stacks really does turn the sampler on, which it did not in the
first console run. That costs some speed, so judge how the game plays with renut_play.toml.

Install
-------
1. Copy COPY_TO_SD_switch_pacman-nx to sdmc:/switch/pacman-nx/ on the SD card.
2. Put your extracted game in game_root/ (on this PC: D:\pacman\game) and, if you want the DLC skins, the AllinOnePack
   package in dlc/ (D:\pacman\PAC MAN CE DX (1)\PAC MAN CE DX\58410A8C\00000002\AllinOnePack). The package holds neither.
3. Copy the toml you want over pacman.toml. That is the file the port reads: a renut.toml beside it is not read. Without a
   pacman.toml the NRO uses its built-in settings, which match renut.toml's picture and speed keys.

Which toml
----------
renut_play.toml  to play: no render-thread diagnostics, no stack sampler, no stall watchdog.
renut.toml       the shipped settings with logs and the stack sampler on. Use this one for a console profile.
renut_ab.toml    the in-run A/B: 14 targets and the control, 30 s halves, 15 minutes a round. Play for 45 minutes for three rounds.

What to test first
------------------
1. The maze's colours. The maze should be clean coloured neon. White, warped outlines mean the look-up textures are wrong:
   send the log. (This was the one big picture bug in the emulator: see "Volume textures" below.)
2. Start a Score Attack and play through to its end. In the emulator a game has reached the FAILED screen, but no run went
   past it: the results screens, and a game that lasts the full 5 minutes, are untested.
3. Frame rate in play, handheld and docked, and whether it holds over a long game. In the emulator gameplay holds about 60 fps
   when the PC is otherwise idle. One long emulator run fell to 0.02 fps at timer 3:12 and never recovered; later runs passed
   that point, and other sessions were loading the PC. A frame rate that falls and stays down on the console would be news:
   please send the log.
4. Changing Visuals in the start menu, the DLC skins (Types E to J) included. Each change loads that skin's PNGs: a pause is
   expected, and how long it takes on the console is worth noting. In the emulator it stalled for up to 10 s with the guard on.
5. Sound: the music and effects in play. The emulator cannot judge sound quality or latency.
6. Leaderboards and other Xbox LIVE items answer "You must be signed into a gamer profile": that is expected.

How to turn on a console profile
--------------------------------
1. Copy renut.toml over pacman.toml (switch_profile_stacks = true is already in it).
2. Play for a few minutes, the stretch you want measured.
3. Send back logs/rex/rex_profile.log and logs/renut_001.log. The first line after the header of rex_profile.log should say
   "Stack sampling: active". pacman-nx.elf in this package maps its addresses to source lines; keep it with the log.

If something misbehaves
-----------------------
banjo_cpu_native_bulk = false in pacman.toml turns off all 5,649 machine copies. Only about 2,300 of them ran under the
checks; the rest have never been reached by a test. If a crash goes away with that key off, the copies are the place to look.

Volume textures: a decision to look at
--------------------------------------
The game colours its maze through two 64 x 64 x 64 look-up textures. Ryujinx's copy engine ignores the Z of a 3D image's
upload, so the patched Ryubing showed a white maze. This package hosts them as 2D arrays instead (banjo_renut_volume_stacked),
the same pixels at two texture fetches for one where the shader reads a look-up. The console's copy engine does honour Z, so
configs/renut_volume_native.toml puts the 3D images back. It should be slightly cheaper on the GPU, and it has never been seen
running: the emulator cannot show it and it has not been on a console.

Options that change the picture (off, for you to decide)
--------------------------------------------------------
configs/renut_720_docked.toml    720 lines docked, the Xbox 360's own
configs/renut_smaa.toml          SMAA
configs/renut_648_864.toml       banjo-nx's internal resolution
configs/renut_dynamic.toml       dynamic resolution
configs/renut_game_gamma.toml    the display's gamma ramp: darks darker (added 2026-11-03, see below)

The display's gamma ramp (configs/renut_game_gamma.toml)
--------------------------------------------------------
The Xbox 360 puts every frame through a gamma ramp at scan-out, and this renderer skips it unless this key is on. So this
package's darks are brighter than the emulated GPU's, by up to 18 levels: 16 becomes 6, 64 becomes 48, 128 becomes 115, and
0 and 255 stay put. The bright colours barely move. Compare the maze's dark background and the logo's darker colours.
This config has never been run on this port. The file was added to the package after it was built, and the NRO is the same
one. Swapping the toml is all it takes, and it costs a 4 KB upload per frame and one look-up per pixel at scan-out.
