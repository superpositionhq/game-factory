# Agent hook (Claude Code: PostToolUse / PostToolUseFailure / Stop, and UserPromptSubmit / SessionEnd with -Messages;
# Codex: PostToolUse / Stop, and UserPromptSubmit / SessionEnd with -Messages; all with -Agent codex):
# append every tool call of a game-building or replay session to <root>\.recording\<project>\actions.jsonl, and every
# prompt the person typed and every reply the model wrote to <root>\.recording\<project>\messages.jsonl.
# Both agents send the same hook JSON on stdin (session_id, transcript_path, cwd, hook_event_name, tool_name,
# tool_input, tool_response, tool_use_id). Codex names its shell tool "Bash" (tool_input.command, a string) and its
# file edits "apply_patch" (tool_input.command = the patch text); it has no PostToolUseFailure (a failed call is a
# PostToolUse whose response carries the exit code). Every row says which agent made it ("agent").
# A session is tied to a project the first time one of its tool calls names a path under
# <root>\games\<slug> or <root>\<extra project> (config "record_extra_projects", default none);
# after that, all its calls are recorded there.
# Backfill: at that first mapping, the session's earlier tool calls are imported once from its transcript
# (transcript_path in the hook input; Claude Code: subagent transcripts beside it; Codex: the rollout file's completed
# CommandExecution / FileChange / McpToolCall items), in order, before the mapping call's own row,
# with status "from_transcript". Calls older than the transcript file (copied context of a fork) are not imported.
# `record-action.ps1 -Backfill <session id> [-TranscriptPath <file>]` does the same for a session mapped before this
# existed: the rows go in just before that session's first row. Each session is backfilled at most once
# (recording-backfill.json next to this file), and a call already in actions.jsonl is never written twice.
# On Stop, leftover changes in a game repo are committed ("WIP") so no work stays uncommitted.
# Messages (schema superposition.agent-message/v0: time, project, session_id, agent, role "user" | "assistant",
# message_id, text; "model"; "images" = pictures attached to a prompt; "mid_turn" for a prompt typed while the model
# was working; Codex "phase"; "subagent" for a Claude Code subagent's transcript, where "user" is the prompt the
# session gave it) are read from the session's transcript, never
# from the hook input, so each is written once, with the transcript's own id and time. Every Stop, and every -Messages
# call (UserPromptSubmit, SessionEnd: they write no actions.jsonl row), reads what the transcript gained since the last
# read (recording-messages.json next to this file: transcript file -> bytes read), so a session mapped late gets its
# earlier messages too. A call waits up to 2 s for its own message (Stop: the turn's last reply; UserPromptSubmit: the
# prompt) to reach the transcript. Not recorded: tool
# calls and results (actions.jsonl), the model's reasoning, text the agent tool puts into a turn itself (Claude Code
# isMeta rows, compaction summaries, background-task notices, API error notices) and a fork's copied context.
# `record-action.ps1 -Backfill <session id>` also imports that session's messages; `-Backfill all` imports the messages
# of every mapped session whose transcript is still on this machine (either agent), and nothing else.
# Nothing is recorded when GF_NO_RECORDING is set: tools/task-try.py sets it for the agent it runs on a task.
# <root> = the machine root (gf-root.ps1 next to this file; machine/lib/gf-root.ps1 in the repo).
# machine/bootstrap.ps1 installs this into the hooks dir (config "hooks_dir") and wires it into Claude Code
# (machine/hooks/settings-hooks.json -> ~\.claude\settings.json) and Codex (machine/hooks/codex-hooks.json ->
# ~\.codex\hooks.json, pre-trusted in ~\.codex\config.toml).
param([switch]$Stop, [switch]$Messages, [string]$Backfill, [string]$TranscriptPath, [ValidateSet('claude', 'codex')][string]$Agent = 'claude')
$ErrorActionPreference = 'Stop'
if ($env:GF_NO_RECORDING) { exit 0 }   # a task try's agent (tools/task-try.py): not a game session, never recorded
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
$backfillFile = Join-Path $hooks 'recording-backfill.json'
$messagesFile = Join-Path $hooks 'recording-messages.json'
$excludeFile = Join-Path $hooks 'recording-exclude.txt'
$maxText = 200000   # chars kept per string field of tool_input
$maxResp = 8000     # chars kept of the tool response

function Clip($v, $n) {
  if ($v -is [string] -and $v.Length -gt $n) { return $v.Substring(0, $n) + "...[truncated $($v.Length - $n) chars]" }
  return $v
}
function Read-JsonMap([string]$Path) {
  $h = @{}
  if (Test-Path $Path) { ([IO.File]::ReadAllText($Path) | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $h[$_.Name] = $_.Value } }
  return $h
}
function Get-RecordedIds([string]$File, [string]$Key = 'tool_use_id') {   # tool_use_ids already in actions.jsonl (message_ids in messages.jsonl)
  $ids = New-Object 'System.Collections.Generic.HashSet[string]'
  if (Test-Path $File) { foreach ($l in [IO.File]::ReadLines($File)) { $m = [regex]::Match($l, '"' + $Key + '":"([^"]+)"'); if ($m.Success) { [void]$ids.Add($m.Groups[1].Value) } } }
  return , $ids
}
function Get-CodexHome { if ($env:CODEX_HOME) { return $env:CODEX_HOME } return (Join-Path $env:USERPROFILE '.codex') }
function Find-Transcript([string]$Sid) {
  $p = if ($Agent -eq 'codex') {   # Codex: <CODEX_HOME>\sessions\YYYY\MM\DD\rollout-<time>-<thread id>.jsonl
    Get-ChildItem (Join-Path (Get-CodexHome) 'sessions') -Recurse -Filter "rollout-*$Sid*.jsonl" -ErrorAction SilentlyContinue | Select-Object -First 1
  } else { Get-ChildItem (Join-Path $env:USERPROFILE '.claude\projects') -Recurse -Filter "$Sid.jsonl" -ErrorAction SilentlyContinue | Select-Object -First 1 }
  if ($p) { return $p.FullName } else { return $null }
}
# Codex rollout (one JSON object per line: timestamp, type, payload): each finished tool call is an event_msg
# "item_completed" whose item.id is the tool_use_id the hooks see. Shell commands -> tool "Bash" with input.command
# (the command string the shell ran), file edits -> "apply_patch" with input.changes (path -> kind and content or diff;
# the rollout keeps no patch text for them), MCP calls -> "mcp__<server>__<tool>" with their arguments.
function Get-CodexTranscriptCalls([string]$Sid, [string]$Path, [string]$Until) {
  $created = (Get-Item $Path).CreationTimeUtc.AddSeconds(-5)
  $calls = [ordered]@{}; $results = @{}; $bad = 0; $n = 0
  foreach ($line in [IO.File]::ReadLines($Path)) {
    if ($line -notmatch '"item_completed"') { continue }
    try { $o = $line | ConvertFrom-Json } catch { $bad++; continue }
    $p = $o.payload
    if ($o.type -ne 'event_msg' -or $p.type -ne 'item_completed' -or -not $p.item -or -not $o.timestamp) { continue }
    if ($p.thread_id -and [string]$p.thread_id -ne $Sid) { continue }
    $ts = [DateTimeOffset]::Parse([string]$o.timestamp, [Globalization.CultureInfo]::InvariantCulture)
    if ($ts.UtcDateTime -lt $created) { continue }
    $it = $p.item; $id = [string]$it.id
    if (-not $id -or $calls.Contains($id)) { continue }
    $cwd = if ($it.cwd) { ([string]$it.cwd -replace '^file:///(?=[A-Za-z]:)', '' -replace '^file://', '') } else { $null }
    $name = $null   # (a `continue` inside switch only leaves the switch, so unknown item types leave $name empty)
    switch ([string]$it.type) {
      'CommandExecution' {
        $c = @($it.command)
        $cmd = if ($c.Count -ge 3 -and [string]$c[-2] -match '^(-lc|-c|/c|-Command|-NoProfile)$') { [string]$c[-1] } else { ($c | ForEach-Object { [string]$_ }) -join ' ' }
        $name = 'Bash'; $inp = [pscustomobject]@{ command = $cmd }
        $resp = [string]$it.aggregated_output; $err = ($null -ne $it.exit_code -and [int]$it.exit_code -ne 0) -or [string]$it.status -eq 'failed'
      }
      'FileChange' {
        $name = 'apply_patch'; $inp = [pscustomobject]@{ changes = $it.changes }
        $resp = (@([string]$it.stdout, [string]$it.stderr) | Where-Object { $_ }) -join "`n"; $err = [string]$it.status -ne 'completed'
      }
      'McpToolCall' {
        $name = "mcp__$($it.server)__$($it.tool)"; $inp = if ($it.arguments) { $it.arguments } else { [pscustomobject]@{} }
        $resp = if ($it.result) { $it.result | ConvertTo-Json -Depth 8 -Compress } else { [string]$it.error }; $err = [bool]$it.error
      }
    }
    if (-not $name) { continue }   # reasoning, messages, web searches, plans: not tool calls with effects
    $calls[$id] = [pscustomobject]@{ id = $id; name = $name; input = $inp; ts = $ts; cwd = $cwd; agent = $null; n = $n++ }
    $results[$id] = [pscustomobject]@{ resp = $resp; error = $err; text = $resp; ts = $ts }
  }
  $stop = if ($Until -and $calls.Contains($Until)) { $calls[$Until].ts } else { $null }
  $out = @($calls.Values | Where-Object { $_.id -ne $Until -and (-not $stop -or $_.ts -le $stop) } | Sort-Object ts, n)
  return [pscustomobject]@{ calls = $out; results = $results; unparsed_lines = $bad }
}
# The session's tool calls from its transcript (and its subagents' transcripts), oldest first. Only calls with a result,
# made by this session, and no older than the transcript file. -Until: stop before this tool_use_id (the mapping call).
function Get-TranscriptCalls([string]$Sid, [string]$Path, [string]$Until) {
  if ($Agent -eq 'codex') { return (Get-CodexTranscriptCalls $Sid $Path $Until) }
  $files = @($Path)
  $sub = Join-Path (Join-Path (Split-Path $Path) $Sid) 'subagents'
  if (Test-Path $sub) { $files += @(Get-ChildItem $sub -Filter '*.jsonl' | ForEach-Object FullName) }
  $created = (Get-Item $Path).CreationTimeUtc.AddSeconds(-5)
  $calls = [ordered]@{}; $results = @{}; $bad = 0; $n = 0
  foreach ($f in $files) {
    $agent = if ($f -eq $Path) { $null } else { [IO.Path]::GetFileNameWithoutExtension($f) }
    foreach ($line in [IO.File]::ReadLines($f)) {
      if ($line -notmatch '"tool_(use|result)"') { continue }
      try { $o = $line | ConvertFrom-Json } catch { $bad++; continue }
      if ([string]$o.sessionId -ne $Sid -or -not $o.timestamp) { continue }
      $ts = [DateTimeOffset]::Parse([string]$o.timestamp, [Globalization.CultureInfo]::InvariantCulture)
      if ($ts.UtcDateTime -lt $created) { continue }
      foreach ($b in @($o.message.content)) {
        if ($b.type -eq 'tool_use' -and -not $calls.Contains([string]$b.id)) {
          $calls[[string]$b.id] = [pscustomobject]@{ id = [string]$b.id; name = [string]$b.name; input = $b.input; ts = $ts; cwd = [string]$o.cwd; agent = $agent; n = $n++ }
        } elseif ($b.type -eq 'tool_result') {
          $text = if ($b.content -is [string]) { $b.content } else { (@($b.content) | Where-Object { $_.type -eq 'text' } | ForEach-Object { $_.text }) -join "`n" }
          $resp = if ($null -ne $o.toolUseResult -and $o.toolUseResult -isnot [string]) { $o.toolUseResult | ConvertTo-Json -Depth 8 -Compress } elseif ($o.toolUseResult) { [string]$o.toolUseResult } else { $text }
          $results[[string]$b.tool_use_id] = [pscustomobject]@{ resp = $resp; error = [bool]$b.is_error; text = $text; ts = $ts }
        }
      }
    }
  }
  $stop = if ($Until -and $calls.Contains($Until)) { $calls[$Until].ts } else { $null }
  $out = @($calls.Values | Where-Object { $_.id -ne $Until -and $results.ContainsKey($_.id) -and (-not $stop -or $_.ts -le $stop) } | Sort-Object ts, n)
  return [pscustomobject]@{ calls = $out; results = $results; unparsed_lines = $bad }
}
function New-BackfillRows([string]$Sid, [string]$Project, $Got, $Skip) {
  $rows = New-Object System.Collections.Generic.List[string]; $script:BackfillIds = @()
  foreach ($c in $Got.calls) {
    if ($Skip.Contains($c.id)) { continue }
    $script:BackfillIds += $c.id
    $r = $Got.results[$c.id]
    $row = [ordered]@{
      schema     = 'superposition.agent-action/v0'
      time       = $c.ts.ToLocalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
      project    = $Project
      session_id = $Sid
      agent      = $Agent
      event      = $(if ($r.error -and $Agent -ne 'codex') { 'PostToolUseFailure' } else { 'PostToolUse' })
      cwd        = $c.cwd
      status     = 'from_transcript'
      tool       = $c.name
      tool_use_id = $c.id
    }
    if ($c.agent) { $row.subagent = $c.agent }
    $inp = [ordered]@{}
    if ($c.input) { foreach ($p in $c.input.PSObject.Properties) { $inp[$p.Name] = Clip $p.Value $maxText } }
    $row.input = $inp
    if ($r.error) { $row.error = Clip $r.text $maxResp }
    $row.response = Clip $r.resp $maxResp
    $row.result_time = $r.ts.ToLocalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
    $rows.Add(($row | ConvertTo-Json -Depth 12 -Compress))
  }
  return , $rows
}
function Save-BackfillState([string]$Sid, [string]$Project, [string]$Path, $Rows, $Got) {
  $state = Read-JsonMap $backfillFile
  $state[$Sid] = [ordered]@{ project = $Project; time = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz'); transcript = $Path
    rows = $Rows.Count; transcript_calls = @($Got.calls).Count; unparsed_lines = $Got.unparsed_lines; tool_use_ids = @($script:BackfillIds) }
  [IO.File]::WriteAllText($backfillFile, ($state | ConvertTo-Json -Depth 4 -Compress), $utf8)
}

# ---- prompts and replies: messages.jsonl ------------------------------------------------------------------------------
function ConvertTo-Time($v) {   # a transcript timestamp (PowerShell 7's ConvertFrom-Json has already made it a date)
  if ($v -is [DateTimeOffset]) { return $v }
  if ($v -is [datetime]) { return [DateTimeOffset]$v }
  return [DateTimeOffset]::Parse([string]$v, [Globalization.CultureInfo]::InvariantCulture)
}
# The complete lines a file gained after byte $From (at most 256 MB a call; the rest at the next), and where they end.
function Read-TranscriptTail([string]$Path, [long]$From) {
  $fs = New-Object IO.FileStream($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
  try {
    if ($From -gt $fs.Length) { $From = 0 }   # a shorter file took its place
    $n = [int][Math]::Min($fs.Length - $From, 268435456)
    $buf = New-Object byte[] $n
    $fs.Position = $From; $got = 0
    while ($got -lt $n) { $r = $fs.Read($buf, $got, $n - $got); if ($r -le 0) { break }; $got += $r }
  } finally { $fs.Dispose() }
  $end = if ($got) { [Array]::LastIndexOf($buf, [byte]10, $got - 1) } else { -1 }
  if ($end -lt 0) {   # no complete line yet; a line longer than one read is skipped, not waited for
    return [pscustomobject]@{ lines = @(); next = $(if ($got -eq 268435456) { $From + $got } else { $From }) }
  }
  return [pscustomobject]@{ lines = $utf8.GetString($buf, 0, $end).Split("`n"); next = $From + $end + 1 }
}
# Claude Code: a "user" row whose content holds text or a picture is a prompt (a tool result holds neither), an
# "assistant" row's text blocks are a reply (thinking and tool_use blocks are not text). A prompt typed while the model
# was working is an "attachment" row of type queued_command from a person ("mid_turn" in its row).
function Get-ClaudeMessages([string]$Sid, $Lines, [datetime]$Created) {
  $out = New-Object System.Collections.Generic.List[object]
  foreach ($line in $Lines) {
    if ($line -notmatch '"sessionId"' -or $line -match '"toolUseResult"') { continue }
    $queued = $line -match '"type":"attachment"' -and $line -match '"queued_command"'
    if (-not $queued -and $line -notmatch '"type":"(?:user|assistant)"') { continue }
    # a pasted picture is megabytes of base64 in its row: counted below by its block, never parsed
    if ($line.Length -gt 100000) { $line = [regex]::Replace($line, '"data":"[A-Za-z0-9+/=]{2000,}"', '"data":""') }
    try { $o = $line | ConvertFrom-Json } catch { continue }
    if ([string]$o.type -eq 'attachment') {
      $a = $o.attachment
      if ([string]$a.type -ne 'queued_command' -or [string]$o.sessionId -ne $Sid -or -not $o.timestamp -or -not $o.uuid) { continue }
      if (($a.PSObject.Properties['origin'] -and $a.origin -and [string]$a.origin.kind -ne 'human') -or ($a.PSObject.Properties['commandMode'] -and [string]$a.commandMode -ne 'prompt')) { continue }
      $ts = ConvertTo-Time $o.timestamp
      if ($ts.UtcDateTime -lt $Created) { continue }
      $text = if ($a.prompt -is [string]) { $a.prompt } else { (@(foreach ($b in @($a.prompt)) { if ($b.type -eq 'text') { [string]$b.text } }) -join "`n") }
      if ("$text".Trim()) { $out.Add([pscustomobject]@{ id = [string]$o.uuid; role = 'user'; ts = $ts; text = "$text"; images = 0; model = ''; phase = ''; mid = $true }) }
      continue
    }
    $role = [string]$o.type
    if (($role -ne 'user' -and $role -ne 'assistant') -or [string]$o.sessionId -ne $Sid -or -not $o.timestamp -or -not $o.uuid) { continue }
    if ($o.isMeta -or $o.isCompactSummary -or $o.isApiErrorMessage) { continue }
    if ($o.PSObject.Properties['origin'] -and $o.origin -and [string]$o.origin.kind -ne 'human') { continue }   # e.g. a background task's notice
    $ts = ConvertTo-Time $o.timestamp
    if ($ts.UtcDateTime -lt $Created) { continue }
    $c = $o.message.content; $images = 0
    $text = if ($c -is [string]) { $c } else {
      (@(foreach ($b in @($c)) { if ($b.type -eq 'text') { [string]$b.text } elseif ($b.type -eq 'image') { $images++ } }) -join "`n")
    }
    if (-not "$text".Trim() -and -not $images) { continue }
    $model = if ($role -eq 'assistant') { [string]$o.message.model } else { '' }
    $out.Add([pscustomobject]@{ id = [string]$o.uuid; role = $role; ts = $ts; text = "$text"; images = $images; model = $model; phase = ''; mid = $false })
  }
  return , $out
}
# Codex: the rollout's finished UserMessage and AgentMessage items (item.id is the message's id).
function Get-CodexMessages([string]$Sid, $Lines, [datetime]$Created) {
  $out = New-Object System.Collections.Generic.List[object]
  foreach ($line in $Lines) {
    if ($line -notmatch '"item_completed"' -or $line -notmatch '"(?:UserMessage|AgentMessage)"') { continue }
    try { $o = $line | ConvertFrom-Json } catch { continue }
    $p = $o.payload
    if ($o.type -ne 'event_msg' -or $p.type -ne 'item_completed' -or -not $p.item -or -not $o.timestamp) { continue }
    if ($p.thread_id -and [string]$p.thread_id -ne $Sid) { continue }
    $it = $p.item
    $role = if ([string]$it.type -eq 'UserMessage') { 'user' } elseif ([string]$it.type -eq 'AgentMessage') { 'assistant' } else { '' }
    if (-not $role -or -not $it.id) { continue }
    $ts = ConvertTo-Time $o.timestamp
    if ($ts.UtcDateTime -lt $Created) { continue }
    $images = 0
    $text = (@(foreach ($b in @($it.content)) { if ($b.PSObject.Properties['text'] -and $b.text) { [string]$b.text } elseif ([string]$b.type -match '(?i)image') { $images++ } }) -join "`n")
    if (-not "$text".Trim() -and -not $images) { continue }
    $out.Add([pscustomobject]@{ id = [string]$it.id; role = $role; ts = $ts; text = "$text"; images = $images; model = ''; phase = [string]$it.phase; mid = $false })
  }
  return , $out
}
# Append to <project>\messages.jsonl what the session's transcript (and, Claude Code, its subagents' transcripts) gained
# since the last read. Returns the number of rows written; $script:Read collects the session's own messages read
# ("<role> <text>").
$script:Read = New-Object System.Collections.Generic.List[string]
function Sync-Messages([string]$Sid, [string]$Project, [string]$Path) {
  if (-not $Path) { $Path = Find-Transcript $Sid }
  if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return 0 }   # a session's first prompt comes before its transcript
  $files = @($Path)
  if ($Agent -ne 'codex') {
    $sub = Join-Path (Join-Path (Split-Path $Path) $Sid) 'subagents'
    if (Test-Path -LiteralPath $sub) { $files += @(Get-ChildItem -LiteralPath $sub -Filter '*.jsonl' | ForEach-Object FullName) }
  }
  $created = (Get-Item -LiteralPath $Path).CreationTimeUtc.AddSeconds(-5)   # older rows are a fork's copied context
  $state = Read-JsonMap $messagesFile
  $dir = Join-Path $recRoot $Project
  $file = Join-Path $dir 'messages.jsonl'
  $seen = $null; $moved = $false
  $rows = New-Object System.Collections.Generic.List[string]
  foreach ($f in $files) {
    $from = if ($state.ContainsKey($f)) { [long]$state[$f] } else { [long]0 }
    $tail = Read-TranscriptTail $f $from
    if ($tail.next -eq $from) { continue }
    $state[$f] = $tail.next; $moved = $true
    # a transcript read from its start (first read, or the state file was lost): never write a message twice
    if ($tail.next -lt $from -or $from -eq 0) { if ($null -eq $seen) { $seen = Get-RecordedIds $file 'message_id' } }
    $subagent = if ($f -eq $Path) { '' } else { [IO.Path]::GetFileNameWithoutExtension($f) }
    $msgs = if ($Agent -eq 'codex') { Get-CodexMessages $Sid $tail.lines $created } else { Get-ClaudeMessages $Sid $tail.lines $created }
    foreach ($m in $msgs) {
      if (-not $subagent) { $script:Read.Add("$($m.role) $($m.text)") }
      if ($null -ne $seen -and -not $seen.Add($m.id)) { continue }
      $row = [ordered]@{
        schema     = 'superposition.agent-message/v0'
        time       = $m.ts.ToLocalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffzzz', [Globalization.CultureInfo]::InvariantCulture)
        project    = $Project
        session_id = $Sid
        agent      = $Agent
        role       = $m.role
        message_id = $m.id
      }
      if ($subagent) { $row.subagent = $subagent }
      if ($m.model) { $row.model = $m.model }
      if ($m.phase) { $row.phase = $m.phase }
      if ($m.images) { $row.images = $m.images }
      if ($m.mid) { $row.mid_turn = $true }
      $row.text = Clip $m.text $maxText
      $rows.Add(($row | ConvertTo-Json -Depth 4 -Compress))
    }
  }
  if ($rows.Count) {
    New-Item -ItemType Directory -Force $dir | Out-Null
    [IO.File]::AppendAllText($file, (($rows -join "`n") + "`n"), $utf8)
  }
  if ($moved) { [IO.File]::WriteAllText($messagesFile, ($state | ConvertTo-Json -Compress), $utf8) }
  return $rows.Count
}
# Is the message the hook was called for (UserPromptSubmit's prompt, Stop's last_assistant_message) among those read
# from the transcript? The transcript may hold it with other text around it, or a part of it.
function Test-MessageRead([string]$Role, [string]$Text) {
  $want = ($Text -replace '\s+', ' ').Trim()
  if (-not $want) { return $true }
  foreach ($r in $script:Read) {
    if (-not $r.StartsWith("$Role ")) { continue }
    $have = ($r.Substring($Role.Length + 1) -replace '\s+', ' ').Trim()
    if ($have -and ($have -eq $want -or $want.Contains($have) -or $have.Contains($want))) { return $true }
  }
  return $false
}

# ---- manual backfill of a session that was mapped before the backfill existed ---------------------------------------
if ($Backfill) {
  $mutex = New-Object Threading.Mutex($false, 'Global\claude-recording-hooks')
  [void]$mutex.WaitOne(30000)
  try {
    $map = Read-JsonMap $mapFile
    if ($Backfill -eq 'all') {   # messages only: every mapped session whose transcript is still here, whichever agent ran it
      $total = 0; $found = 0
      foreach ($s in @($map.Keys | Sort-Object)) {
        $t = $null
        foreach ($a in 'claude', 'codex') { $Agent = $a; $t = Find-Transcript $s; if ($t) { break } }
        if (-not $t) { continue }
        $found++; $n = Sync-Messages $s ([string]$map[$s]) $t; $total += $n
        if ($n) { Write-Host "$n message(s) of session $s ($Agent) -> $([string]$map[$s])\messages.jsonl" }
      }
      Write-Host "imported $total message(s) from $found of $($map.Count) mapped session(s)$(if ($found -lt $map.Count) { '; the others have no transcript on this machine' })"
      exit 0
    }
    if (-not $map.ContainsKey($Backfill)) { throw "session $Backfill is not mapped to a project (recording-sessions.json)" }
    $n = Sync-Messages $Backfill ([string]$map[$Backfill]) $TranscriptPath
    Write-Host "imported $n message(s) of session $Backfill into $(Join-Path (Join-Path $recRoot ([string]$map[$Backfill])) 'messages.jsonl')"
    if ((Read-JsonMap $backfillFile).ContainsKey($Backfill)) { Write-Host "session $Backfill was already backfilled; nothing to do"; exit 0 }
    $project = $map[$Backfill]
    if (-not $TranscriptPath) { $TranscriptPath = Find-Transcript $Backfill }
    if (-not $TranscriptPath -or -not (Test-Path $TranscriptPath)) { throw "no transcript found for session $Backfill" }
    $file = Join-Path (Join-Path $recRoot $project) 'actions.jsonl'
    $lines = @(if (Test-Path $file) { [IO.File]::ReadAllLines($file, $utf8) })
    $firstIdx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match ('"session_id":"' + [regex]::Escape($Backfill) + '"')) { $firstIdx = $i; break } }
    $until = if ($firstIdx -ge 0) { [regex]::Match($lines[$firstIdx], '"tool_use_id":"([^"]+)"').Groups[1].Value } else { $null }
    $got = Get-TranscriptCalls $Backfill $TranscriptPath $until
    $rows = New-BackfillRows $Backfill $project $got (Get-RecordedIds $file)
    if ($rows.Count) {
      $out = New-Object System.Collections.Generic.List[string]
      if ($firstIdx -lt 0) { $out.AddRange([string[]]$lines); $out.AddRange($rows) }
      else { for ($i = 0; $i -lt $lines.Count; $i++) { if ($i -eq $firstIdx) { $out.AddRange($rows) }; $out.Add($lines[$i]) } }
      $tmp = "$file.backfill-tmp"
      [IO.File]::WriteAllText($tmp, (($out -join "`n") + "`n"), $utf8)
      Move-Item -Force $tmp $file
    }
    Save-BackfillState $Backfill $project $TranscriptPath $rows $got
    Write-Host "backfilled $($rows.Count) call(s) of session $Backfill into $file (before row $([Math]::Max($firstIdx, 0) + 1); $($got.unparsed_lines) unparsed transcript lines)"
  } finally { $mutex.ReleaseMutex() }
  exit 0
}

$raw = [Console]::In.ReadToEnd()
if (-not $raw.Trim()) { exit 0 }
$e = $raw | ConvertFrom-Json
$sid = [string]$e.session_id
if ((Test-Path $excludeFile) -and ((Get-Content $excludeFile) -contains $sid)) { exit 0 }

# One mutex for every writer of the recording (both agents' hooks, record-commit.ps1); the name predates Codex support
# and stays so that older and newer copies still exclude each other.
$mutex = New-Object Threading.Mutex($false, 'Global\claude-recording-hooks')
[void]$mutex.WaitOne(30000)
try {
  $map = Read-JsonMap $mapFile

  # which project does this call name?
  $texts = @([string]$e.cwd)
  if ($e.tool_input) { foreach ($k in 'file_path', 'path', 'notebook_path', 'command', 'cwd') { if ($e.tool_input.$k) { $texts += [string]$e.tool_input.$k } } }
  $project = $null
  foreach ($t in $texts) {
    $m = [regex]::Match($t, $projectRx)
    if ($m.Success) { $project = if ($m.Groups[1].Success) { $m.Groups[1].Value } else { $m.Groups[2].Value }; break }
  }
  $newlyMapped = $false
  if ($project -and $project -ne '.recording' -and -not $map.ContainsKey($sid)) {
    $map[$sid] = $project
    [IO.File]::WriteAllText($mapFile, ($map | ConvertTo-Json -Compress), $utf8)
    $newlyMapped = $true
  }
  if (-not $map.ContainsKey($sid)) { exit 0 }
  $project = $map[$sid]
  $dir = Join-Path $recRoot $project
  New-Item -ItemType Directory -Force $dir | Out-Null
  $actions = Join-Path $dir 'actions.jsonl'

  # first mapping: the session's earlier calls from its transcript, before this call's own row
  if ($newlyMapped -and -not $Stop -and $e.transcript_path -and (Test-Path ([string]$e.transcript_path)) -and -not (Read-JsonMap $backfillFile).ContainsKey($sid)) {
    try {
      $got = Get-TranscriptCalls $sid ([string]$e.transcript_path) ([string]$e.tool_use_id)
      $rows = New-BackfillRows $sid $project $got (Get-RecordedIds $actions)
      if ($rows.Count) { [IO.File]::AppendAllText($actions, (($rows -join "`n") + "`n"), $utf8) }
      Save-BackfillState $sid $project ([string]$e.transcript_path) $rows $got
    } catch { }   # never lose the live row over a transcript problem
  }
  # the session's prompts and replies: what its transcript gained since the last read (never at the cost of the row)
  if ($Stop -or $Messages) {
    try {
      [void](Sync-Messages $sid $project ([string]$e.transcript_path))
      # the message this call is about may reach the transcript a moment after the hook starts: the turn's last reply
      # (Stop), the prompt just typed (UserPromptSubmit)
      $role = if ($Stop) { 'assistant' } else { 'user' }
      $text = if ($Stop) { [string]$e.last_assistant_message } else { [string]$e.prompt }
      for ($i = 0; $i -lt 7 -and -not (Test-MessageRead $role $text); $i++) {
        Start-Sleep -Milliseconds 300
        [void](Sync-Messages $sid $project ([string]$e.transcript_path))
      }
    } catch { }
    if ($Messages) { exit 0 }   # UserPromptSubmit, SessionEnd: no row in actions.jsonl
  }
  # a call already imported from the transcript is not written twice
  $bf = Read-JsonMap $backfillFile
  if ($e.tool_use_id -and $bf.ContainsKey($sid) -and (@($bf[$sid].tool_use_ids) -contains [string]$e.tool_use_id)) { exit 0 }

  $row = [ordered]@{
    schema     = 'superposition.agent-action/v0'
    time       = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
    project    = $project
    session_id = $sid
    agent      = $Agent
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
  [IO.File]::AppendAllText($actions, ($row | ConvertTo-Json -Depth 12 -Compress) + "`n", $utf8)
} finally { $mutex.ReleaseMutex() }
exit 0
