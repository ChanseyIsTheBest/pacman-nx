# pacman-nx: what the host is doing during a test run: every -Every seconds a line with the free memory and the processes
# that used the most CPU since the last line, so a slowdown in the emulator can be told from a machine busy with something
# else. Reads process lists only.
#   powershell -File tools/host_sampler.ps1 -Seconds 400 -Out out\emu_runs\host.txt [-Every 10]
param([int]$Seconds = 300, [string]$Out = "host.txt", [int]$Every = 10)
$cores = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
$last = @{}
$deadline = (Get-Date).AddSeconds($Seconds)
Set-Content -Path $Out -Value ("# {0} logical processors; each line: time, free commit and physical GB, % of all processors in the top processes" -f $cores)
while ((Get-Date) -lt $deadline) {
    $now = @{}
    $rows = foreach ($p in Get-Process) {
        $cpu = 0.0
        try { $cpu = [double]$p.TotalProcessorTime.TotalSeconds } catch { continue }
        $key = "{0}:{1}" -f $p.Id, $p.ProcessName
        $now[$key] = $cpu
        if ($last.ContainsKey($key)) {
            [pscustomobject]@{ Name = $key; Used = ($cpu - $last[$key]) }
        }
    }
    $last = $now
    $os = Get-CimInstance Win32_OperatingSystem
    $top = $rows | Sort-Object Used -Descending | Select-Object -First 6 |
        ForEach-Object { "{0} {1:N0}%" -f $_.Name, (100.0 * $_.Used / ($Every * $cores)) }
    Add-Content -Path $Out -Value ("{0} commit {1:N1} phys {2:N1} | {3}" -f (Get-Date -Format HH:mm:ss), ($os.FreeVirtualMemory / 1MB), ($os.FreePhysicalMemory / 1MB), ($top -join ', '))
    Start-Sleep -Seconds $Every
}
