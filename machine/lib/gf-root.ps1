# Machine root for game-factory tooling. Dot-source it; Windows PowerShell 5.1 compatible.
#
# Everything machine-specific hangs off one root (the "Work" folder holding games\, builds\, recordings\, .recording\,
# deliverables\, asset-library\, tools\ and the game-factory clone). Resolution order:
#   1. $env:GF_ROOT
#   2. "root" in the config file: $env:GF_CONFIG, else %USERPROFILE%\.game-factory\config.json (bootstrap.ps1 writes it)
#   3. %USERPROFILE%\Work (the original machine's layout)
# The same config file also holds "ueb" (private build clones, outside the user profile so the user name is not compiled
# into Shipping exes), "engine" (UE 5.3 root) and "record_extra_projects" (top-level folders under the root that the
# recording hooks treat as projects besides games\<slug>). Installed copies of the hooks and ue-heavy.ps1 carry a copy of
# this file next to them.

function Get-GFConfigPath {
    if ($env:GF_CONFIG) { return $env:GF_CONFIG }
    return (Join-Path $env:USERPROFILE '.game-factory\config.json')
}

function Get-GFConfig {
    $cfg = [ordered]@{
        root                  = (Join-Path $env:USERPROFILE 'Work')
        ueb                   = 'C:\UEB'
        engine                = 'C:\Program Files\Epic Games\UE_5.3'
        record_extra_projects = @()
    }
    $path = Get-GFConfigPath
    if (Test-Path -LiteralPath $path) {
        $json = [IO.File]::ReadAllText($path) | ConvertFrom-Json
        foreach ($p in $json.PSObject.Properties) { $cfg[$p.Name] = $p.Value }
    }
    if ($env:GF_ROOT) { $cfg.root = $env:GF_ROOT }
    foreach ($k in 'root', 'ueb', 'engine') {
        $v = ([string]$cfg[$k]).TrimEnd('\', '/')
        if ($v -match '^[A-Za-z]:$') { $v += '\' }
        $cfg[$k] = [IO.Path]::GetFullPath($v)
    }
    $cfg.record_extra_projects = @($cfg.record_extra_projects | Where-Object { $_ })
    return [pscustomobject]$cfg
}

function Get-GFRoot { return (Get-GFConfig).root }

# Output root for packages, dataset zips and their staging folders: $env:GF_OUT, else "out" in the config file, else
# <root>\deliverables. Point it at a roomy drive (packages and zips run to tens of GB per game).
function Get-GFOut {
    if ($env:GF_OUT) { return [IO.Path]::GetFullPath($env:GF_OUT.TrimEnd('\', '/')) }
    $cfg = Get-GFConfig
    if ($cfg.PSObject.Properties['out'] -and $cfg.out) { return [IO.Path]::GetFullPath(([string]$cfg.out).TrimEnd('\', '/')) }
    return (Join-Path $cfg.root 'deliverables')
}

# Refuse to start a disk-heavy job (packaging, creation replay) when the drive holding $Path has less than the floor
# free: $env:GF_MIN_FREE_GB, else "min_free_gb" in the config file, else 50. A full disk mid-job corrupts the result.
function Assert-GFFreeSpace([string]$Path, [string]$What = 'this job') {
    $min = 50
    $cfg = Get-GFConfig
    if ($cfg.PSObject.Properties['min_free_gb'] -and $cfg.min_free_gb) { $min = [double]$cfg.min_free_gb }
    if ($env:GF_MIN_FREE_GB) { $min = [double]$env:GF_MIN_FREE_GB }
    $full = [IO.Path]::GetFullPath($Path)
    $drive = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($full))
    $free = [math]::Round($drive.AvailableFreeSpace / 1GB, 1)
    if ($free -lt $min) {
        throw ("{0}: only {1} GB free on {2} (floor {3} GB; GF_MIN_FREE_GB / min_free_gb). Free space or point GF_OUT / work_root at another drive." -f $What, $free, $drive.Name, $min)
    }
    return $free
}

# Regex matching a path under the root in the spellings tool calls use: C:\a\b, C:/a/b, /c/a/b (Git Bash), /mnt/c/a/b.
# Append the part after the root yourself, e.g. (Get-GFRootPattern) + '[\\/]+games[\\/]+([A-Za-z0-9_-]+)'.
function Get-GFRootPattern([string]$Root = (Get-GFRoot)) {
    $full = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    $drive = $full.Substring(0, 1)
    $rest = @($full.Substring(2).Split('\') | Where-Object { $_ } | ForEach-Object { [regex]::Escape($_) })
    $head = "(?:$drive`:|/$drive|/mnt/$drive)"
    if ($rest.Count -eq 0) { return "(?i)$head" }
    return "(?i)$head[\\/]+" + ($rest -join '[\\/]+')
}
