# katamari-nx: the Switch package (the request's step 7), as banjo-nx's builds/ folders:
#   builds/<date>_<time>_<name>/
#     COPY_TO_SD_switch_pacman-nx/   pacman-nx.nro, renut.toml (shipped), renut_play.toml, renut_ab.toml, configs/,
#                                      deko3d_shaders.bin (the prebuilt DKSH cache), game_root/ (your game files)
#     COPY_TO_SD_ROOT/atmosphere/contents/05D6EA1333487100/exefs/main.npdm   (the four-core forwarder NPDM; only with
#                                      -FourCore since rc6: the user runs on three cores)
#     pacman-nx.elf                  the unstripped ELF of this NRO (profiles map to it)
#     source_<commit>.tgz              the source snapshot (git archive of the commit; no game data, no generated code)
#     README.txt, PACKAGE_NOTES.txt
# Nothing of the game's data goes in by default (the NRO holds the recompiled code; the DKSH cache is compiled shader
# code). katamari-nx (2026-10-31, the user's request, for their own SD card): -GameRoot copies the extracted disc into
# game_root and -Dlc the DLC packages into dlc (installed at the first start). Never into git, never uploaded.
#   powershell -File tools/package_switch.ps1 -Name pgo_lto [-Build app\out\switch-pgo-use] [-Notes <file>]
#       [-GameRoot D:\pacman\game] [-Dlc D:\pacman\dlc]
param([string]$Name = "package", [string]$Build = "app\out\switch", [string]$Notes = "", [string]$GameRoot = "",
      [string]$Dlc = "", [switch]$FourCore)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$free = (Get-PSDrive D).Free / 1GB
if ($free -lt 2) { throw ("D: has {0:N1} GB free: not packaging (the request: stop and say so)" -f $free) }
$b = Join-Path $root $Build
$nro = Join-Path $b "renut.nro"
$elf = Join-Path $b "renut"
if (-not (Test-Path $nro)) { throw "no NRO at $nro" }
$stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$out = Join-Path (Split-Path -Parent $root) "builds\${stamp}_$Name"
$sd = Join-Path $out "COPY_TO_SD_switch_pacman-nx"
New-Item -ItemType Directory -Force $sd, (Join-Path $sd "configs"), (Join-Path $sd "game_root") | Out-Null
Copy-Item $nro (Join-Path $sd "pacman-nx.nro")
$dist = Join-Path $root "dist\switch\pacman-nx"
Copy-Item (Join-Path $dist "renut.toml"), (Join-Path $dist "renut_play.toml"), (Join-Path $dist "renut_ab.toml") $sd
Copy-Item (Join-Path $dist "configs\*.toml") (Join-Path $sd "configs")
$cache = Join-Path $root "out\deko3d_shaders\deko3d_shaders.bin"
if (Test-Path $cache) { Copy-Item $cache $sd }
if ($GameRoot) {
    $need = ((Get-ChildItem $GameRoot -Recurse -File | Measure-Object -Sum Length).Sum + 1GB) / 1GB
    if ((Get-PSDrive D).Free / 1GB -lt $need) { throw ("D: has too little space for the game files ({0:N1} GB needed)" -f $need) }
    & robocopy $GameRoot (Join-Path $sd "game_root") /E /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy of the game files failed ($LASTEXITCODE)" }
} else {
    Set-Content -Path (Join-Path $sd "game_root\PUT_YOUR_GAME_FILES_HERE.txt") -Encoding ascii -Value `
        "Extract your own PAC-MAN CE DX package here: default.xex, data/, geui/ and the rest (README.txt; tools/stfs_extract.py)."
}
New-Item -ItemType Directory -Force (Join-Path $sd "dlc") | Out-Null
if ($Dlc) {
    Copy-Item (Join-Path $Dlc "*") (Join-Path $sd "dlc") -Force
} else {
    Set-Content -Path (Join-Path $sd "dlc\PUT_THE_DLC_PACKAGES_HERE.txt") -Encoding ascii -Value `
        "Optional: PAC-MAN CE DX's DLC package (AllinOnePack, an Xbox 360 LIVE file, content type 2) here; installed at the first start."
}
if ($FourCore) {
    $npdm = Join-Path $out "COPY_TO_SD_ROOT\atmosphere\contents\05D6EA1333487100\exefs"
    New-Item -ItemType Directory -Force $npdm | Out-Null
    Copy-Item (Join-Path $root "tools\forwarder\pacman_main.npdm") (Join-Path $npdm "main.npdm")
}
if (Test-Path $elf) { Copy-Item $elf (Join-Path $out "pacman-nx.elf") }
Copy-Item (Join-Path $root "dist\switch\README.txt") $out
if ($Notes) { Copy-Item $Notes (Join-Path $out "PACKAGE_NOTES.txt") }
Push-Location $root
try {
    $sha = (& git rev-parse --short=12 HEAD).Trim()
    & git archive --format=tar.gz -o (Join-Path $out "source_$sha.tgz") HEAD
} finally { Pop-Location }
$md5 = (Get-FileHash -Algorithm MD5 (Join-Path $sd "pacman-nx.nro")).Hash.ToLower()
Write-Output "package: $out"
Write-Output ("NRO {0:N1} MB, md5 {1}; commit {2}" -f ((Get-Item (Join-Path $sd "pacman-nx.nro")).Length / 1MB), $md5, $sha)
Get-ChildItem -Recurse $out | Where-Object { -not $_.PSIsContainer } | Select-Object FullName, Length | Format-Table -AutoSize
