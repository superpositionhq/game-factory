# Claude Code hook (PostToolUse / PostToolUseFailure / Stop): append every tool call of a
# game-building or replay session to <root>\.recording\<project>\actions.jsonl.
# A session is tied to a project the first time one of its tool calls names a path under
# <root>\games\<slug> or <root>\<extra project> (config "record_extra_projects", default none);
# after that, all its calls are recorded there.
# On Stop, leftover changes in a game repo are committed ("WIP") so no work stays uncommitted.
# <root> = the machine root (gf-root.ps1 next to this file; machine/lib/gf-root.ps1 in the repo).
# machine/bootstrap.ps1 installs this into ~\.claude\hooks\ and wires it with machine/hooks/settings-hooks.json.
param([switch]$Stop)
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.Encoding]::UTF8
$utf8 = New-Object Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8   # git writes UTF-8; read it as such
$hooks = Split-Path -Parent $MyInvocation.MyCommand.Path
$gfLib = @((Join-Path $hooks 'gf-root.ps1'), (Join-Path $hooks '..\lib\gf-root.ps1')) | Where-Object { Test-Path $_ } | Select-Object -First 1
. $gfLib
$gf = Get-GFConfig
$recRoot = Join-Path $gf.root '.recording'
$gamesRoot = Join-Path $gf.root 'games'
$extra = @($gf.record_extra_projects | ForEach-Object { [regex]::Escape([string]$_) })
$projectRx = (Get-GFRootPattern $gf.root) + '[\\/]+(?:games[\\/]+([A-Za-z0-9_-]+)' +
  $(if ($extra.Count) { '|(' + ($extra -join '|') + ')(?![A-Za-z0-9_-])' } else { '' }) + ')'
$mapFile = Join-Path $hooks 'recording-sessions.json'
$excludeFile = Join-Path $hooks 'recording-exclude.txt'
$maxText = 200000   # chars kept per string field of tool_input
$maxResp = 8000     # chars kept of the tool response

$raw = [Console]::In.ReadToEnd()
if (-not $raw.Trim()) { exit 0 }
$e = $raw | ConvertFrom-Json
$sid = [string]$e.session_id
if ((Test-Path $excludeFile) -and ((Get-Content $excludeFile) -contains $sid)) { exit 0 }

$mutex = New-Object Threading.Mutex($false, 'Global\claude-recording-hooks')
[void]$mutex.WaitOne(30000)
try {
  $map = @{}
  if (Test-Path $mapFile) { (Get-Content $mapFile -Raw | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $map[$_.Name] = $_.Value } }

  # which project does this call name?
  $texts = @([string]$e.cwd)
  if ($e.tool_input) { foreach ($k in 'file_path', 'path', 'notebook_path', 'command', 'cwd') { if ($e.tool_input.$k) { $texts += [string]$e.tool_input.$k } } }
  $project = $null
  foreach ($t in $texts) {
    $m = [regex]::Match($t, $projectRx)
    if ($m.Success) { $project = if ($m.Groups[1].Success) { $m.Groups[1].Value } else { $m.Groups[2].Value }; break }
  }
  if ($project -and $project -ne '.recording' -and -not $map.ContainsKey($sid)) {
    $map[$sid] = $project
    [IO.File]::WriteAllText($mapFile, ($map | ConvertTo-Json -Compress), $utf8)
  }
  if (-not $map.ContainsKey($sid)) { exit 0 }
  $project = $map[$sid]
  $dir = Join-Path $recRoot $project
  New-Item -ItemType Directory -Force $dir | Out-Null

  function Clip($v, $n) {
    if ($v -is [string] -and $v.Length -gt $n) { return $v.Substring(0, $n) + "...[truncated $($v.Length - $n) chars]" }
    return $v
  }
  $row = [ordered]@{
    schema     = 'superposition.agent-action/v0'
    time       = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
    project    = $project
    session_id = $sid
    event      = [string]$e.hook_event_name
    cwd        = [string]$e.cwd
  }
  if ($Stop) {
    $ErrorActionPreference = 'Continue'   # git warnings on stderr (e.g. CRLF) must not abort the commit
    $row.event = 'Stop'
    $repo = Join-Path $gamesRoot $project
    if ((Test-Path (Join-Path $repo '.git')) -and -not (Test-Path (Join-Path $repo '.git\index.lock'))) {
      $dirty = git -C $repo status --porcelain
      if ($dirty) {
        git -C $repo add -A 2>$null | Out-Null
        git -C $repo commit -q -m "WIP" 2>$null | Out-Null
        $row.auto_commit = [ordered]@{ sha = (git -C $repo rev-parse HEAD); files = @($dirty).Count }
      } else { $row.auto_commit = $null }
    }
  } else {
    $row.tool = [string]$e.tool_name
    $row.tool_use_id = [string]$e.tool_use_id
    $inp = [ordered]@{}
    if ($e.tool_input) { foreach ($p in $e.tool_input.PSObject.Properties) { $inp[$p.Name] = Clip $p.Value $maxText } }
    $row.input = $inp
    $resp = if ($e.tool_response -is [string]) { $e.tool_response } elseif ($null -ne $e.tool_response) { $e.tool_response | ConvertTo-Json -Depth 8 -Compress } else { $null }
    if ($e.error) { $row.error = Clip ([string]$e.error) $maxResp }
    $row.response = Clip $resp $maxResp
  }
  [IO.File]::AppendAllText((Join-Path $dir 'actions.jsonl'), ($row | ConvertTo-Json -Depth 12 -Compress) + "`n", $utf8)
} finally { $mutex.ReleaseMutex() }
exit 0
