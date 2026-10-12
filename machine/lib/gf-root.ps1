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
