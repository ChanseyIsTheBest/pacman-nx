@echo off
rem pacman-nx: the released NRO (docs/building.md), in a build folder of its own: LTO, no PGO, and no game shader inside but
rem the 4 the game makes at run time, which no installer finds in its files. The others come from deko3d_glsl.bin beside
rem the NRO, which the web installer makes from the player's files. tools\renut_release_shaders.py makes the files it builds
rem with. A folder of its own because LTO recompiles everything, as GIMPLE, and the everyday build's objects are not.
rem Output: app\out\switch-lto\renut.nro
set "BUILD_DIR=%~dp0..\app\out\switch-lto"
set "CMAKE_EXTRA=-DBANJO_SWITCH_LTO=ON -DBANJO_RENUT_RELEASE_SHADERS=ON"
if "%JOBS%"=="" set "JOBS=4"
call "%~dp0build_switch.bat" %*
