# Codex hook wiring for the recording hooks. Dot-source it; Windows PowerShell 5.1 compatible.
#
# Codex (codex-cli 0.15x) runs a hook from ~\.codex\hooks.json only once it is trusted: config.toml holds
#   [hooks.state."<hooks.json path>:<event>:<group index>:<handler index>"]
#   trusted_hash = "sha256:<hex>"
# where <hex> is the SHA-256 of the compact, key-sorted JSON of the hook's normalized identity
#   {"event_name": "post_tool_use", "matcher": "*", "hooks": [{"type": "command", "command": "...", "timeout": 60, "async": true}]}
# (codex-rs hooks/src/engine/discovery.rs hook_hash, config/src/fingerprint.rs version_for_toml; commandWindows is not
# part of it, a missing timeout counts as 600, a missing matcher is left out). An untrusted or changed hook is skipped
# without an error, so bootstrap.ps1 writes these entries for the game-factory hooks (and only those), and check.ps1
# compares them. Typing /hooks in Codex shows the same trust state and can trust them by hand.

$script:CodexEventLabels = @{ PreToolUse = 'pre_tool_use'; PermissionRequest = 'permission_request'; PostToolUse = 'post_tool_use'
    PreCompact = 'pre_compact'; PostCompact = 'post_compact'; SessionStart = 'session_start'; SessionEnd = 'session_end'
    UserPromptSubmit = 'user_prompt_submit'; SubagentStart = 'subagent_start'; SubagentStop = 'subagent_stop'; Stop = 'stop'; Interrupt = 'interrupt' }

function Get-GFCodexHome { if ($env:CODEX_HOME) { return $env:CODEX_HOME } return (Join-Path $env:USERPROFILE '.codex') }

# JSON as serde_json writes it after sort_all_objects: no spaces, keys in byte order, only " \ and control characters
# escaped (non-ASCII stays as is).
function ConvertTo-GFCanonicalJson($Value) {
    if ($null -eq $Value) { return 'null' }
    if ($Value -is [bool]) { if ($Value) { return 'true' } else { return 'false' } }
    if ($Value -is [int] -or $Value -is [long] -or $Value -is [int16] -or $Value -is [byte] -or $Value -is [uint32] -or $Value -is [uint64]) { return [string]$Value }
    if ($Value -is [string]) {
        $sb = New-Object Text.StringBuilder
        [void]$sb.Append('"')
        foreach ($ch in $Value.ToCharArray()) {
            $c = [int]$ch
            switch ($c) {
                34 { [void]$sb.Append('\"') } 92 { [void]$sb.Append('\\') } 8 { [void]$sb.Append('\b') } 12 { [void]$sb.Append('\f') }
                10 { [void]$sb.Append('\n') } 13 { [void]$sb.Append('\r') } 9 { [void]$sb.Append('\t') }
                default { if ($c -lt 0x20) { [void]$sb.Append(('\u{0:x4}' -f $c)) } else { [void]$sb.Append($ch) } }
            }
        }
        [void]$sb.Append('"')
        return $sb.ToString()
    }
    if ($Value -is [Collections.IDictionary]) {
        $keys = [string[]]@($Value.Keys | ForEach-Object { [string]$_ })
        [Array]::Sort($keys, [StringComparer]::Ordinal)
        return '{' + (($keys | ForEach-Object { (ConvertTo-GFCanonicalJson $_) + ':' + (ConvertTo-GFCanonicalJson $Value[$_]) }) -join ',') + '}'
    }
    if ($Value -is [Collections.IEnumerable]) { return '[' + ((@($Value) | ForEach-Object { ConvertTo-GFCanonicalJson $_ }) -join ',') + ']' }
    throw "ConvertTo-GFCanonicalJson: unsupported value of type $($Value.GetType().FullName)"
}

function Get-GFSha256Hex([string]$Text) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return (($sha.ComputeHash((New-Object Text.UTF8Encoding($false)).GetBytes($Text)) | ForEach-Object { $_.ToString('x2') }) -join '') }
    finally { $sha.Dispose() }
}

# The trust entries for every command handler in $Hooks (a parsed hooks.json object) whose command matches $Pattern:
# objects { event, key, hash }. $HooksJsonPath is the path Codex reads (the key holds it as Codex displays it).
function Get-GFCodexHookTrust([string]$HooksJsonPath, $Hooks, [string]$Pattern = 'record-action\.ps1') {
    $out = @()
    if (-not $Hooks -or -not $Hooks.PSObject.Properties['hooks']) { return $out }
    foreach ($ev in $Hooks.hooks.PSObject.Properties) {
        $label = $script:CodexEventLabels[$ev.Name]
        if (-not $label) { continue }
        $groups = @($ev.Value)
        for ($gi = 0; $gi -lt $groups.Count; $gi++) {
            $g = $groups[$gi]
            $handlers = @($g.hooks)
            for ($hi = 0; $hi -lt $handlers.Count; $hi++) {
                $h = $handlers[$hi]
                if ([string]$h.type -ne 'command' -or [string]$h.command -notmatch $Pattern) { continue }
                $hd = [ordered]@{ type = 'command'; command = [string]$h.command
                    timeout = $(if ($h.PSObject.Properties['timeout'] -and $null -ne $h.timeout) { [long]$h.timeout } else { [long]600 })
                    async = [bool]($h.PSObject.Properties['async'] -and $h.async) }
                if ($h.PSObject.Properties['statusMessage'] -and $h.statusMessage) { $hd['statusMessage'] = [string]$h.statusMessage }
                $id = [ordered]@{ event_name = $label; hooks = @(, $hd) }
                if ($g.PSObject.Properties['matcher'] -and $null -ne $g.matcher) { $id['matcher'] = [string]$g.matcher }
                $hash = 'sha256:' + (Get-GFSha256Hex (ConvertTo-GFCanonicalJson $id))
                $out += [pscustomobject]@{ event = $ev.Name; key = "${HooksJsonPath}:${label}:${gi}:${hi}"; hash = $hash }
            }
        }
    }
    return $out
}

# hooks.state entries in a config.toml: key -> trusted_hash (a small reader for exactly these tables).
function Get-GFCodexTrustState([string]$ConfigToml) {
    $state = @{}
    if (-not (Test-Path -LiteralPath $ConfigToml)) { return $state }
    $key = $null
    foreach ($line in [IO.File]::ReadAllLines($ConfigToml)) {
        if ($line -match '^\s*\[') {
            $key = $null
            if ($line -match '^\s*\[\s*hooks\.state\.(?:"((?:[^"\\]|\\.)*)"|''([^'']*)'')\s*\]\s*(#.*)?$') {
                $key = if ($Matches[1]) { $Matches[1] -replace '\\(["\\])', '$1' } else { $Matches[2] }
            }
            continue
        }
        if ($key -and $line -match '^\s*trusted_hash\s*=\s*"([^"]*)"') { $state[$key] = $Matches[1] }
    }
    return $state
}

$script:CodexTrustMarker = '# game-factory recording hooks (machine/bootstrap.ps1): trusted so Codex runs them; /hooks in Codex shows them'
# Writes (or replaces) the hooks.state tables for $Entries in $ConfigToml; every other line stays as it was.
function Set-GFCodexTrustState([string]$ConfigToml, $Entries) {
    $keys = @{}; foreach ($e in $Entries) { $keys[$e.key] = $e.hash }
    $lines = if (Test-Path -LiteralPath $ConfigToml) { [IO.File]::ReadAllLines($ConfigToml) } else { @() }
    $out = New-Object Collections.Generic.List[string]
    $skip = $false
    foreach ($line in $lines) {
        if ($line -match '^\s*\[') {
            $skip = $false
            if ($line -match '^\s*\[\s*hooks\.state\.(?:"((?:[^"\\]|\\.)*)"|''([^'']*)'')\s*\]\s*(#.*)?$') {
                $k = if ($Matches[1]) { $Matches[1] -replace '\\(["\\])', '$1' } else { $Matches[2] }
                if ($keys.ContainsKey($k)) { $skip = $true; continue }
            }
        }
        if (-not $skip -and $line -ne $script:CodexTrustMarker) { $out.Add($line) }
    }
    while ($out.Count -and -not $out[$out.Count - 1].Trim()) { $out.RemoveAt($out.Count - 1) }
    $out.Add('')
    $out.Add($script:CodexTrustMarker)
    foreach ($e in $Entries) {
        $k = if ($e.key -notmatch "'") { "'$($e.key)'" } else { '"' + ($e.key -replace '\\', '\\' -replace '"', '\"') + '"' }
        $out.Add("[hooks.state.$k]")
        $out.Add("trusted_hash = `"$($e.hash)`"")
    }
    $text = ($out -join "`n") + "`n"
    New-Item -ItemType Directory -Force (Split-Path $ConfigToml) | Out-Null
    [IO.File]::WriteAllText($ConfigToml, $text, (New-Object Text.UTF8Encoding($false)))
}
