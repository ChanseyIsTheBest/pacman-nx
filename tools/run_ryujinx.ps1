# katamari-nx: one emulator run of the NRO in the user's patched Ryubing with this port's own data folder
# (docs/porting-start-here.md of banjo-nx: "Build and test essentials"). Started minimised; refuses to start while any
# Ryujinx runs or when the free commit memory is under -MinCommitGB; stops only the process it started.
#   powershell -File tools/run_ryujinx.ps1 -Seconds 300 -Name emu1 [-Toml <a pacman.toml with test keys>]
param([int]$Seconds = 240, [string]$Name = "emu", [string]$Toml = "", [double]$MinCommitGB = 8)
$root = Split-Path -Parent $PSScriptRoot
$ryu = "D:\New folder\Ryubing-src\ryubing\build\Ryujinx.exe"
$data = "D:\New folder\ryu-data\pacman"
$sd = Join-Path $data "sdcard\switch\pacman-nx"
$nro = Join-Path $sd "pacman-nx.nro"
$out = Join-Path $root "out\emu_runs\$Name"
if (Get-Process -Name Ryujinx -ErrorAction SilentlyContinue) { Write-Output "a Ryujinx is running (another port's?): not starting"; exit 2 }
$os = Get-CimInstance Win32_OperatingSystem
$freeCommit = ($os.TotalVirtualMemorySize - ($os.TotalVirtualMemorySize - $os.FreeVirtualMemory)) / 1MB
if ($freeCommit -lt $MinCommitGB) { Write-Output ("free commit memory {0:N1} GB < {1} GB: not starting" -f $freeCommit, $MinCommitGB); exit 3 }
if (-not (Test-Path $nro)) { Write-Output "no NRO at $nro"; exit 4 }
if ($Toml) { Copy-Item $Toml (Join-Path $sd "pacman.toml") -Force }
New-Item -ItemType Directory -Force $out | Out-Null
$logs = Join-Path $sd "logs"
if (Test-Path $logs) { Remove-Item -Recurse -Force $logs }
$env:DOTNET_ROOT = "D:\New folder\dotnet10"
# katamari-nx (2026-10-31): the run's own start time ($p.StartTime filtered nothing: every run copied every capture
# the SD had ever kept, ~800 MB a run, 19 GB in out/emu_runs).
$started = Get-Date
$p = Start-Process -FilePath $ryu -ArgumentList @("-r", "`"$data`"", "`"$nro`"") -PassThru -WindowStyle Minimized `
     -RedirectStandardOutput (Join-Path $out "ryujinx_stdout.txt") -RedirectStandardError (Join-Path $out "ryujinx_stderr.txt")
Write-Output ("started Ryujinx pid {0} (free commit {1:N1} GB)" -f $p.Id, $freeCommit)
$deadline = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $deadline -and -not $p.HasExited) { Start-Sleep -Seconds 3 }
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force; Write-Output "stopped pid $($p.Id) after $Seconds s" }
else { Write-Output "Ryujinx exited by itself (code $($p.ExitCode))" }
Start-Sleep -Seconds 2
# pacman-nx: a second run under one name would otherwise nest its logs in logs\logs and leave the first run's to be read.
if (Test-Path (Join-Path $out "logs")) { Remove-Item -Recurse -Force (Join-Path $out "logs") }
if (Test-Path $logs) { Copy-Item -Recurse $logs (Join-Path $out "logs") -Force }
# pacman-nx: the sampling profile, which each run overwrites (tools/switch_hot_bulk.py takes it with this run's ELF).
$switchDir = Split-Path -Parent $sd
foreach ($f in "rex_profile.log", "banjo_profiler.log") {
    $from = Join-Path $switchDir $f
    if ((Test-Path $from) -and (Get-Item $from).LastWriteTime -ge $started) { Copy-Item $from $out -Force }
}
Set-Content -Path (Join-Path $out "run.nro.txt") -Value ("{0} {1}" -f (Get-Item $nro).Length, (Get-FileHash $nro -Algorithm MD5).Hash)
# This run's captures move out of the SD (the SD's folder no longer grows); older ones there are left alone.
# pacman-nx: only the captures folder: this game's DLC installs PNGs under renut/ at the first start, which -Recurse took too.
Get-ChildItem (Join-Path $sd "capturas") -Filter "*.png" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -ge $started } |
    Move-Item -Destination $out -Force
Get-ChildItem $out -Recurse | Select-Object FullName, Length
