pacman-nx: PAC-MAN Championship Edition DX+ (Xbox 360, title 58410A8C, Title Update 3) on the Nintendo Switch
=============================================================================================================

A ReXGlue static recompilation, built from katamari-nx (Beautiful Katamari's port) and through it banjo-nx (Banjo-Kazooie:
Nuts & Bolts' port): the SDK fork, the post-codegen CPU passes and reNut's Direct3D-level renderer on plume's deko3d back end
(no NVK, no PM4 ring, no EDRAM model). Your own game files are needed; nothing of the game is in this package except the
recompiled code.

Credits: reNut's renderer by masterspike52 (its author permits its reuse in these ports), katamari-nx, banjo-nx, sa2-nx
(input, CPU items), NetherSX2_nx by NaGaa95 (the four-core layout, MIT), battd_nx (the GPU arena), bejeweled3-nx and the zuma
ports (the hot-function method). GPL-3.0 where the sources are.

SD card layout
--------------
sdmc:/switch/pacman-nx/pacman-nx.nro      the program
sdmc:/switch/pacman-nx/pacman.toml        settings (copy one of the tomls below over it)
sdmc:/switch/pacman-nx/game_root/         the game's files: default.xex, data/, geui/ and the rest, and Title Update 3's
                                          default.xexp (extract your LIVE packages with tools/stfs_extract.py)
sdmc:/switch/pacman-nx/update/            Title Update 3's other files (the game opens them as UPDATE:\)
sdmc:/switch/pacman-nx/dlc/               the DLC package AllinOnePack (an Xbox 360 LIVE file, content type 2), optional.
                                          It holds the extra skins, game data and sound banks, no code. Installed at the
                                          first start into sdmc:/switch/pacman-nx/renut/ (dlc/installed.txt lists it).

The tomls
---------
renut.toml        the shipped settings: Renut on deko3d, 720 lines handheld and 1080 docked,
                  every exact enhancement that applies on, the items measured SLOWER ON THE CONSOLE in banjo-nx off, logs and
                  diagnostics on. Copy it over pacman.toml: pacman.toml is the file the port reads.
renut_play.toml   the same with the diagnostics off (for playing).
renut_ab.toml     the same with an in-run A/B list, 30 s halves, target 1 as the do-nothing control (a Vulkan-only key). Keep
                  playing for 15 minutes or more; the log's "[renut A/B]" lines give each target.
configs/          options one key away from renut.toml each. The ones that change the picture are for you to decide on.

Cores
-----
The port runs on the three cores a homebrew launch gets. Four cores are optional and off: with banjo_forwarder_program_id set
to your forwarder's id, the NRO writes that forwarder's four-core NPDM (NetherSX2_nx's layout, CPU 0-3) to
sdmc:/atmosphere/contents/<id>/exefs/main.npdm, and the next launch has CPU 0-3 (the log's "[banjo] system core:" line says
whether the fourth core was granted). Delete that main.npdm to go back to three cores.

Profiling
---------
The ELF (pacman-nx.elf) and the source snapshot (source_<commit>.tgz) are the ones this NRO was built from: a console profile
maps to source lines with them. renut.toml has switch_profile_stacks on; the report is logs/rex/rex_profile.log (the first
line says "Stack sampling: active"), and it goes with this package's ELF. Send both back.

The CPU work in this port
-------------------------
banjo_cpu_native_sub_*    machine-made copies of the game's functions (tools/localize_native.py; see PACKAGE_NOTES.txt for how
                          many this package has). Each has its key. A/B target 70 turns them all off in its off half.
No hand-written natives: those wait for a console profile. A guard compares a copy with the generated original
(banjo_hot_guard_calls / _period, off in the shipped tomls, on in configs/renut_verify.toml); a difference switches that one copy
off and logs "[hot] DIFFERENCE".
