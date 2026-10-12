# Coordinator watcher: exits (waking the coordinator) as soon as anything material changes, or after -MaxMinutes as a
# heartbeat. Prints what changed. Run it in the background and re-arm it after every notification:
#   powershell -ExecutionPolicy Bypass -File machine\coordinator\watch.ps1 -MaxMinutes 15
param([int]$MaxMinutes = 15, [int]$PollSeconds = 30, [string]$Root)
. (Join-Path $PSScriptRoot '..\lib\gf-root.ps1')
if (-not $Root) { $Root = Get-GFRoot }
$W = $Root
function Snap {
    $s = [ordered]@{}
    foreach ($f in Get-ChildItem "$W\.recording" -Directory -ErrorAction SilentlyContinue) {
        foreach ($n in 'runs.jsonl', 'builds.jsonl', 'pipeline.jsonl') {
            $p = Join-Path $f.FullName $n
            if (Test-Path $p) { $s["$($f.Name)/$n"] = (Get-Item $p).Length }
        }
    }
    $s['queue'] = ((Get-ChildItem "$W\builds\_queue" -File -ErrorAction SilentlyContinue | ForEach-Object Name | Sort-Object) -join ';')
    # zips are rebuilt often; only a refusal (leak scan) is worth waking for
    $s['deliverables_refused'] = ((Get-ChildItem "$W\deliverables" -Recurse -Include *.refused -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-2) } | ForEach-Object Name | Sort-Object) -join ';')
    $s['tags'] = ((Get-ChildItem "$W\games" -Directory | Where-Object { Test-Path "$($_.FullName)\.git" } | ForEach-Object { "$($_.Name):" + ((git -C $_.FullName tag -l 'milestone/*') -join ',') }) -join ';')
    $s['gpu_procs'] = ((Get-Process *Shipping*, UnrealEditor -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch 'EOSOverlay' } | ForEach-Object Name | Sort-Object) -join ',')
    return $s
}
$a = Snap; $t0 = Get-Date
while (((Get-Date) - $t0).TotalMinutes -lt $MaxMinutes) {
    Start-Sleep -Seconds $PollSeconds
    $b = Snap
    $changes = @()
    foreach ($k in ($a.Keys + $b.Keys | Sort-Object -Unique)) {
        if ("$($a[$k])" -ne "$($b[$k])") { if ($k -ne 'gpu_procs') { $changes += "$k`n    before: $($a[$k])`n    after:  $($b[$k])" } }
    }
    if ($changes) { "CHANGED at $(Get-Date -Format HH:mm:ss):"; $changes; "gpu processes now: $($b['gpu_procs'])"; exit 0 }
}
"HEARTBEAT at $(Get-Date -Format HH:mm:ss): no material change in $MaxMinutes min. gpu processes: $((Snap)['gpu_procs'])"
