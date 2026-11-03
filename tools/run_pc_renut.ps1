# pacman-nx: one PC run on Renut's Vulkan back end (the request's PC reference), visible (Renut presents and captures only
# with a swapchain), the full game (license_mask), with the given scripted pad and captures.
#   powershell -File tools/run_pc_renut.ps1 -Seconds 120 -Name renut1 [-Every 15] [-Script "12:A,20:START"] [-Extra "--key=value"]
param([int]$Seconds = 120, [string]$Name = "renut", [int]$Every = 15, [string]$Script = "", [string]$Extra = "")
$root = Split-Path -Parent $PSScriptRoot
$a = "--banjo_renderer=renut --renut_gpu_backend=vulkan --license_mask=1 --masseffect_renderer_native=false"
if ($Script) { $a += " --input_script=$Script" }
$a += " $Extra"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "tools\run_pc.ps1") -Seconds $Seconds -Name $Name -Every $Every -Visible -Extra $a
