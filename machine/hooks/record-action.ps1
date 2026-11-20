# Agent hook (Claude Code: PostToolUse / PostToolUseFailure / Stop, and UserPromptSubmit / SessionEnd with -Messages;
# Codex: PostToolUse / Stop, and UserPromptSubmit / SessionEnd / SubagentStop with -Messages; all with -Agent codex):
# append every tool call of a game-building or replay session to <root>\.recording\<project>\actions.jsonl, and every
# prompt the person typed, every reply the model wrote and every reasoning summary the agent saved to
# <root>\.recording\<project>\messages.jsonl. A tool call's row holds its whole result (up to 1,000,000 chars; a
# picture or other binary payload as a short marker; a long command output that Claude Code cut in the result and saved
# to a file, the result's persistedOutputPath, is read from that file while it is there).
# Both agents send the same hook JSON on stdin (session_id, transcript_path, cwd, hook_event_name, tool_name,
# tool_input, tool_response, tool_use_id). Codex names its shell tool "Bash" (tool_input.command, a string) and its
# file edits "apply_patch" (tool_input.command = the patch text); it has no PostToolUseFailure (a failed call is a
# PostToolUse whose response carries the exit code). Every row says which agent made it ("agent").
# Antigravity (PostToolUse / Stop, with -Agent antigravity; its CLI agy, its App and its IDE alike) sends its own hook
# JSON (camelCase: conversationId, transcriptPath, cwd, hookEventName, toolCall {id, name, args}, stepIdx, error;
# https://antigravity.google/docs/hooks) without the tool's result, and reads every hook's answer from stdout as a
# JSON object ({} here: nothing to change). Its input is turned into the fields above (session_id = conversationId,
# tool_name / tool_input = toolCall.name / args, for finding the project). The rows themselves come from the
# transcript: transcriptPath is <app data>\brain\<conversation id>\.system_generated\logs\transcript_full.jsonl
# (transcript.jsonl beside it is the same with long fields cut; the full one is read), one step per line (step_index,
# source, type, status, created_at, content, thinking, tool_calls, media, model). A PLANNER_RESPONSE step is the model's
# reply (content), its reasoning (thinking) and its tool calls (tool_calls, without ids); the k-th call's result is the
# step at that step's step_index + 1 + k (stepIdx in the call's PostToolUse). Antigravity writes that result after the
# hook has run, so every hook call of a recorded session writes the calls the transcript completed since the last one
# (recording-antigravity.json next to this file), status "from_transcript": a call's row lands at the next hook call,
# the Stop at the latest. Its tool_use_id is "<conversation id>:<result step>". A USER_INPUT step from USER_EXPLICIT is
# a prompt (the text inside its <USER_REQUEST>, without what Antigravity adds around it). Antigravity has no
# PostToolUseFailure (a failed call is a step with status ERROR, its text the row's error), no SessionEnd and no
# subagent tag: a subagent is a conversation of its own, recorded as a session when its own calls name a game.
# A session is tied to a project the first time one of its tool calls names a path under
# <root>\games\<slug> or <root>\<extra project> (config "record_extra_projects", default none);
# after that, all its calls are recorded there.
# Backfill: at that first mapping, the session's earlier tool calls are imported once from its transcript
# (transcript_path in the hook input; Claude Code: subagent transcripts beside it; Codex: the rollout file's completed
# CommandExecution / FileChange / McpToolCall items, and those of the subagents' rollouts it names; a subagent's hook
# names its own rollout, and the session's is read instead), in order, before the mapping call's own row,
# with status "from_transcript". Calls older than the transcript file (copied context of a fork) are not imported.
# A subagent's call carries "subagent": Claude Code "agent-<agent_id>" (its transcript's name), Codex its thread id
# (the end of its rollout's name). A live row takes it from the hook input's agent_id, with "agent_type".
# `record-action.ps1 -Backfill <session id> [-TranscriptPath <file>]` does the same for a session mapped before this
# existed: the rows go in just before that session's first row. Each session is backfilled at most once
# (recording-backfill.json next to this file), and a call already in actions.jsonl is never written twice.
# On Stop, leftover changes in a game repo are committed ("WIP") so no work stays uncommitted.
# Messages (schema superposition.agent-message/v0: time, project, session_id, agent, role "user" | "assistant" | "thinking",
# message_id, text; "model"; "images" = pictures attached to a prompt; "mid_turn" for a prompt typed while the model
# was working; Codex "phase"; "subagent" for a subagent's messages: Claude Code its transcript, where "user" is the
# prompt the session gave it; Codex its rollout, read at SubagentStop and whenever the parent's rollout names it, where
# "user" is a message another agent sent it, only its readable header since Codex encrypts the payload, with
# "encrypted": true) are read from the session's transcript, never
# from the hook input, so each is written once, with the transcript's own id and time. Every Stop, and every -Messages
# call (UserPromptSubmit, SessionEnd: they write no actions.jsonl row), reads what the transcript gained since the last
# read (recording-messages.json next to this file: transcript file -> bytes read), so a session mapped late gets its
# earlier messages too. A call waits up to 2 s for its own message (Stop: the turn's last reply; UserPromptSubmit: the
# prompt) to reach the transcript (Antigravity's Stop: a last step that is a reply without tool calls). Not recorded: tool
# calls and results (actions.jsonl), reasoning the agent saved without readable text (a "thinking" row with
# "redacted": true and no text marks it: Claude Code saves the text when its showThinkingSummaries setting is on, Codex
# when model_reasoning_summary is and its model gives summaries; bootstrap.ps1 sets both), text the agent tool puts into a turn itself (Claude Code
# isMeta rows, compaction summaries, background-task notices, API error notices) and a fork's copied context.
# `record-action.ps1 -Backfill <session id>` also imports that session's messages; `-Backfill all` imports the messages
# of every mapped session whose transcript is still on this machine (any agent), and nothing else.
# Both read each transcript from its start, so what an earlier read left out (the reasoning summaries of a session
# recorded before they were) is added, and the session's rows are put back in the transcript's order.
# Nothing is recorded when GF_NO_RECORDING is set: tools/task-try.py sets it for the agent it runs on a task.
# <root> = the machine root (gf-root.ps1 next to this file; machine/lib/gf-root.ps1 in the repo).
# machine/bootstrap.ps1 installs this into the hooks dir (config "hooks_dir") and wires it into Claude Code
# (machine/hooks/settings-hooks.json -> ~\.claude\settings.json), Codex (machine/hooks/codex-hooks.json ->
# ~\.codex\hooks.json, pre-trusted in ~\.codex\config.toml) and Antigravity (machine/hooks/antigravity-hooks.json ->
# ~\.gemini\config\hooks.json).
param([switch]$Stop, [switch]$Messages, [string]$Backfill, [string]$TranscriptPath, [ValidateSet('claude', 'codex', 'antigravity')][string]$Agent = 'claude')
$ErrorActionPreference = 'Stop'
# Antigravity reads the hook's answer from stdout, whatever this script does next: {} changes nothing
if ($Agent -eq 'antigravity' -and -not $Backfill) { [Console]::Out.Write('{}'); [Console]::Out.Flush() }
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
$antigravityFile = Join-Path $hooks 'recording-antigravity.json'
$excludeFile = Join-Path $hooks 'recording-exclude.txt'
$maxText = 200000   # chars kept per string field of tool_input
$maxResp = 1000000  # chars kept of a tool's result: the whole result unless it is larger than this

function Clip($v, $n) {
  if ($v -is [string] -and $v.Length -gt $n) { return $v.Substring(0, $n) + "...[truncated $($v.Length - $n) chars]" }
  return $v
}
# A tool's result as recorded: the whole text (up to $maxResp chars; a longer one is cut and the row says so in
# <key>_chars and <key>_truncated). A picture or other binary payload inside it (base64) becomes a short marker.
# Claude Code keeps only the start of a long command output in the result and saves all of it to a file
# (persistedOutputPath, persistedOutputSize): the row takes the saved text (its first 64 MB) while the file is there.
function Expand-Saved($r) {
  try {
    if ($null -eq $r -or $r -is [string] -or $r -is [array] -or -not $r.PSObject.Properties['persistedOutputPath'] -or -not $r.PSObject.Properties['stdout']) { return $r }
    $p = [string]$r.persistedOutputPath
    if (-not $p -or -not (Test-Path -LiteralPath $p -PathType Leaf)) { return $r }
    $fs = New-Object IO.FileStream($p, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    try {
      $n = [int][Math]::Min($fs.Length, 67108864)
      $buf = New-Object byte[] $n
      $got = 0
      while ($got -lt $n) { $k = $fs.Read($buf, $got, $n - $got); if ($k -le 0) { break }; $got += $k }
    } finally { $fs.Dispose() }
    $text = $utf8.GetString($buf, 0, $got)
    if ($text.Length -gt ([string]$r.stdout).Length) { $r.stdout = $text }
  } catch { }   # the result as the tool gave it
  return $r
}
function Set-Output($Row, [string]$Key, $Value) {
  if ($null -eq $Value) { $Row[$Key] = $null; return }
  $s = if ($Value -is [string]) { $Value } else { (Expand-Saved $Value) | ConvertTo-Json -Depth 8 -Compress }
  if ($null -eq $s) { $Row[$Key] = $null; return }   # an empty list serializes to nothing
  $s = [regex]::Replace($s, '"(data|base64|bytes|image)"\s*:\s*"([A-Za-z0-9+/=\\]{2000,})"',
    [System.Text.RegularExpressions.MatchEvaluator] { param($m) '"' + $m.Groups[1].Value + '":"[binary ' + $m.Groups[2].Value.Length + ' chars]"' })
  if ($s.Length -gt $maxResp) { $Row[$Key + '_chars'] = $s.Length; $Row[$Key + '_truncated'] = $true }
  $Row[$Key] = Clip $s $maxResp
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
  if ($Agent -eq 'antigravity') {   # <app data>\brain\<id>\.system_generated\logs: the CLI's, the App's or the IDE's
    foreach ($app in 'antigravity-cli', 'antigravity', 'antigravity-ide') {
      $logs = Join-Path $env:USERPROFILE ".gemini\$app\brain\$Sid\.system_generated\logs"
      foreach ($f in 'transcript_full.jsonl', 'transcript.jsonl') { $t = Join-Path $logs $f; if (Test-Path -LiteralPath $t) { return $t } }
    }
    return $null
  }
  $p = if ($Agent -eq 'codex') {   # Codex: <CODEX_HOME>\sessions\YYYY\MM\DD\rollout-<time>-<thread id>.jsonl
    Get-ChildItem (Join-Path (Get-CodexHome) 'sessions') -Recurse -Filter "rollout-*$Sid*.jsonl" -ErrorAction SilentlyContinue | Select-Object -First 1
  } else { Get-ChildItem (Join-Path $env:USERPROFILE '.claude\projects') -Recurse -Filter "$Sid.jsonl" -ErrorAction SilentlyContinue | Select-Object -First 1 }
  if ($p) { return $p.FullName } else { return $null }
}
# Codex rollout (one JSON object per line: timestamp, type, payload): each finished tool call is an event_msg
# "item_completed" whose item.id is the tool_use_id the hooks see. Shell commands -> tool "Bash" with input.command
# (the command string the shell ran), file edits -> "apply_patch" with input.changes (path -> kind and content or diff;
# the rollout keeps no patch text for them), MCP calls -> "mcp__<server>__<tool>" with their arguments.
# A subagent has its own rollout (rollout-<time>-<its thread id>.jsonl; session_meta: id = its thread, session_id = the
# session's, parent_thread_id, source.subagent.thread_spawn.agent_path). It starts with a copy of the parent's context;
# the subagent's own items carry its thread id. The parent's rollout names it in SubAgentActivity items
# (agent_thread_id). A subagent's hook input has session_id = the session's, agent_id = its thread id and
# transcript_path = its rollout; SubagentStop has agent_transcript_path.
# A file Codex is still writing: read it without blocking the writer.
function Open-SharedReader([string]$Path) {
  $fs = New-Object IO.FileStream($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
  return (New-Object IO.StreamReader($fs, $utf8))
}
# A rollout's session_meta (its first line): thread, session, and a subagent's parent thread and agent path.
function Get-CodexRolloutMeta([string]$Path) {
  try {
    $sr = Open-SharedReader $Path
    try { $line = $sr.ReadLine() } finally { $sr.Dispose() }
    $o = $line | ConvertFrom-Json
    if ($o.type -ne 'session_meta') { return $null }
    $p = $o.payload
    $spawn = if ($p.source -and $p.source.PSObject.Properties['subagent'] -and $p.source.subagent.thread_spawn) { $p.source.subagent.thread_spawn } else { $null }
    $parent = if ($p.parent_thread_id) { [string]$p.parent_thread_id } elseif ($spawn) { [string]$spawn.parent_thread_id } else { '' }
    $agentPath = if ($spawn -and $spawn.agent_path) { [string]$spawn.agent_path } elseif ($p.PSObject.Properties['agent_path']) { [string]$p.agent_path } else { '' }
    return [pscustomobject]@{ thread = [string]$p.id; session = [string]$p.session_id; parent = $parent; agent_path = $agentPath }
  } catch { return $null }
}
# The session's own rollout for a path that may be a subagent's (a subagent's hook names its own as transcript_path).
function Resolve-CodexRoot([string]$Sid, [string]$Path) {
  $meta = Get-CodexRolloutMeta $Path
  if (-not $meta -or -not $meta.parent -or $meta.thread -eq $Sid) { return $Path }
  $root = Find-Transcript $Sid
  if ($root) { return $root } else { return $Path }
}
# A subagent's rollout by its thread id: beside its parent's (same day), else anywhere under sessions\.
function Find-CodexRollout([string]$Near, [string]$Thread) {
  $p = Get-ChildItem -LiteralPath (Split-Path $Near) -Filter "rollout-*$Thread.jsonl" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($p) { return $p.FullName }
  return (Find-Transcript $Thread)
}
# The subagents that rollout lines of thread $Thread name (SubAgentActivity items): their thread ids.
function Get-CodexSubagents($Lines, [string]$Thread) {
  $ids = New-Object System.Collections.Generic.List[string]
  foreach ($line in $Lines) {
    if ($line -notmatch '"SubAgentActivity"') { continue }
    try { $o = $line | ConvertFrom-Json } catch { continue }
    $p = $o.payload
    if ($o.type -ne 'event_msg' -or $p.type -ne 'item_completed' -or -not $p.item -or [string]$p.item.type -ne 'SubAgentActivity') { continue }
    if ($p.thread_id -and [string]$p.thread_id -ne $Thread) { continue }
    $id = [string]$p.item.agent_thread_id
    if ($id -and -not $ids.Contains($id)) { $ids.Add($id) }
  }
  return , $ids
}
# The session's calls from its rollout and its subagents' rollouts (each read with its own thread id; a subagent's
# calls tagged with it), whichever of them $Path names.
function Get-CodexTranscriptCalls([string]$Sid, [string]$Path, [string]$Until) {
  $Path = Resolve-CodexRoot $Sid $Path
  $calls = [ordered]@{}; $results = @{}; $bad = 0; $n = 0
  $todo = New-Object System.Collections.Generic.Queue[object]
  $todo.Enqueue([pscustomobject]@{ path = $Path; thread = $Sid; agent = $null })
  $threads = @{ $Sid = $true }
  while ($todo.Count) {
    $src = $todo.Dequeue()
    $created = (Get-Item -LiteralPath $src.path).CreationTimeUtc.AddSeconds(-5)
    $sr = Open-SharedReader $src.path
    try {
      while ($null -ne ($line = $sr.ReadLine())) {
        if ($line -notmatch '"item_completed"') { continue }
        try { $o = $line | ConvertFrom-Json } catch { $bad++; continue }
        $p = $o.payload
        if ($o.type -ne 'event_msg' -or $p.type -ne 'item_completed' -or -not $p.item -or -not $o.timestamp) { continue }
        if ($p.thread_id -and [string]$p.thread_id -ne $src.thread) { continue }   # a copied context's item
        $it = $p.item
        if ([string]$it.type -eq 'SubAgentActivity') {   # a subagent: its calls are in its own rollout
          $child = [string]$it.agent_thread_id
          if ($child -and -not $threads.ContainsKey($child)) {
            $threads[$child] = $true
            $cp = Find-CodexRollout $src.path $child
            if ($cp) { $todo.Enqueue([pscustomobject]@{ path = $cp; thread = $child; agent = $child }) }
          }
          continue
        }
        $ts = [DateTimeOffset]::Parse([string]$o.timestamp, [Globalization.CultureInfo]::InvariantCulture)
        if ($ts.UtcDateTime -lt $created) { continue }
        $id = [string]$it.id
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
        $calls[$id] = [pscustomobject]@{ id = $id; name = $name; input = $inp; ts = $ts; cwd = $cwd; agent = $src.agent; n = $n++ }
        $results[$id] = [pscustomobject]@{ resp = $resp; error = $err; text = $resp; ts = $ts }
      }
    } finally { $sr.Dispose() }
  }
  $stop = if ($Until -and $calls.Contains($Until)) { $calls[$Until].ts } else { $null }
  $out = @($calls.Values | Where-Object { $_.id -ne $Until -and (-not $stop -or $_.ts -le $stop) } | Sort-Object ts, n)
  return [pscustomobject]@{ calls = $out; results = $results; unparsed_lines = $bad }
}
# Antigravity: the transcript as the module header describes it. transcript.jsonl named in the hook input becomes the
# transcript_full.jsonl beside it, whose fields are never cut.
function Resolve-AntigravityTranscript([string]$Path) {
  if (-not $Path) { return $Path }
  if ((Split-Path -Leaf $Path) -eq 'transcript.jsonl') {
    $full = Join-Path (Split-Path $Path) 'transcript_full.jsonl'
    if (Test-Path -LiteralPath $full) { return $full }
  }
  return $Path
}
function Get-AntigravityText($Step) {   # a step's content as text (a prompt, a reply, a tool's result)
  if ($null -eq $Step.content) { return '' }
  if ($Step.content -is [string]) { return $Step.content }
  return ($Step.content | ConvertTo-Json -Depth 8 -Compress)
}
# The last complete step of the transcript, read from its end; $null when there is none.
function Read-AntigravityLastStep([string]$Path) {
  if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return $null }
  $fs = New-Object IO.FileStream($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
  try {
    $len = $fs.Length; $size = [long]1048576
    while ($true) {
      $from = [Math]::Max([long]0, $len - $size)
      $n = [int]($len - $from)
      $buf = New-Object byte[] $n
      $fs.Position = $from; $got = 0
      while ($got -lt $n) { $r = $fs.Read($buf, $got, $n - $got); if ($r -le 0) { break }; $got += $r }
      $end = if ($got) { [Array]::LastIndexOf($buf, [byte]10, $got - 1) } else { -1 }   # a line still being written is not read
      $lines = if ($end -ge 0) { $utf8.GetString($buf, 0, $end).Split("`n") } else { @() }
      $first = if ($from -gt 0) { 1 } else { 0 }   # the first piece may be the end of a longer line
      for ($i = $lines.Count - 1; $i -ge $first; $i--) {
        if (-not $lines[$i].Trim()) { continue }
        try { return ($lines[$i] | ConvertFrom-Json) } catch { return $null }
      }
      if ($from -eq 0 -or $size -ge 268435456) { return $null }
      $size *= 4
    }
  } finally { $fs.Dispose() }
}
# Has the turn ended in the transcript: is its last step a reply without tool calls?
function Test-AntigravityTurnEnded([string]$Path) {
  $s = Read-AntigravityLastStep $Path
  return ($s -and [string]$s.type -eq 'PLANNER_RESPONSE' -and -not @($s.tool_calls | Where-Object { $_ }).Count)
}
function ConvertFrom-AntigravityHook($A) {
  $cwd = if ($A.cwd) { [string]$A.cwd } elseif ($A.workspacePaths) { [string]@($A.workspacePaths)[0] } else { '' }
  $o = [ordered]@{ session_id = [string]$A.conversationId; transcript_path = (Resolve-AntigravityTranscript ([string]$A.transcriptPath))
    cwd = $cwd; hook_event_name = [string]$A.hookEventName; prompt = [string]$A.lastUserInput; tool_name = ''; tool_input = $null }
  if ($A.toolCall) { $o.tool_name = [string]$A.toolCall.name; $o.tool_input = $A.toolCall.args }
  return [pscustomobject]$o
}
# The tool calls that transcript lines complete. A PLANNER_RESPONSE's calls wait in $Pending (id -> call) until their
# result steps come; each call with its result goes into $Got (calls in the transcript's order, results by id).
function Add-AntigravityCalls([string]$Sid, $Lines, [datetime]$Created, $Pending, $Got) {
  foreach ($line in $Lines) {
    if (-not $line.Trim()) { continue }
    try { $o = $line | ConvertFrom-Json } catch { $Got.unparsed_lines++; continue }
    if ($null -eq $o.step_index -or -not $o.created_at) { continue }
    $ts = ConvertTo-Time $o.created_at
    $idx = [int]$o.step_index
    if ([string]$o.type -eq 'PLANNER_RESPONSE') {
      if ($ts.UtcDateTime -lt $Created) { continue }   # a fork's copied context
      $k = 0
      foreach ($c in @($o.tool_calls | Where-Object { $_ })) {
        $id = "${Sid}:$($idx + 1 + $k)"; $k++
        $Pending[$id] = [pscustomobject]@{ id = $id; name = [string]$c.name; input = $c.args; ts = $ts.ToString('o') }
      }
    } elseif ([string]$o.type -ne 'USER_INPUT' -and $Pending.Contains("${Sid}:$idx")) {
      $c = $Pending["${Sid}:$idx"]; $Pending.Remove("${Sid}:$idx")
      $Got.calls.Add([pscustomobject]@{ id = $c.id; name = $c.name; input = $c.input; ts = (ConvertTo-Time $c.ts); cwd = ''; agent = $null; n = $Got.calls.Count })
      $text = Get-AntigravityText $o
      $Got.results[$c.id] = [pscustomobject]@{ resp = $text; error = ([string]$o.status -eq 'ERROR'); text = $text; ts = $ts }
    }
  }
}
function New-AntigravityGot { return [pscustomobject]@{ calls = (New-Object System.Collections.Generic.List[object]); results = @{}; unparsed_lines = 0 } }
function Get-AntigravityTranscriptCalls([string]$Sid, [string]$Path, [string]$Until) {
  $got = New-AntigravityGot
  Add-AntigravityCalls $Sid ([IO.File]::ReadLines($Path)) ((Get-Item -LiteralPath $Path).CreationTimeUtc.AddSeconds(-5)) ([ordered]@{}) $got
  $stop = @($got.calls | Where-Object { $_.id -eq $Until } | ForEach-Object { $_.n })
  $calls = @($got.calls | Where-Object { -not $stop.Count -or $_.n -lt $stop[0] })
  return [pscustomobject]@{ calls = $calls; results = $got.results; unparsed_lines = $got.unparsed_lines }
}
# Every hook call of a recorded Antigravity session: append to actions.jsonl the calls whose results the transcript
# gained since the last read (recording-antigravity.json next to this file: transcript file -> bytes read and the
# calls still waiting for their results), in the transcript's order. A call's own PostToolUse comes before its result
# reaches the transcript, so its row is written at the next hook call (the Stop at the latest).
function Sync-AntigravityCalls([string]$Sid, [string]$Project, [string]$Path) {
  if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return 0 }
  $state = Read-JsonMap $antigravityFile
  $from = [long]0; $pending = [ordered]@{}
  if ($state.ContainsKey($Path)) {
    $from = [long]$state[$Path].offset
    foreach ($c in @($state[$Path].pending | Where-Object { $_ })) { $pending[[string]$c.id] = $c }
  }
  $tail = Read-TranscriptTail $Path $from
  if ($tail.next -lt $from) { $pending = [ordered]@{} }   # a shorter file took its place: read it from its start
  if ($tail.next -eq $from) { return 0 }
  $got = New-AntigravityGot
  Add-AntigravityCalls $Sid $tail.lines ((Get-Item -LiteralPath $Path).CreationTimeUtc.AddSeconds(-5)) $pending $got
  $file = Join-Path (Join-Path $recRoot $Project) 'actions.jsonl'
  $seen = if ($from -eq 0 -or $tail.next -lt $from) { Get-RecordedIds $file } else { New-Object 'System.Collections.Generic.HashSet[string]' }
  $rows = New-BackfillRows $Sid $Project $got $seen
  if ($rows.Count) { [IO.File]::AppendAllText($file, (($rows -join "`n") + "`n"), $utf8) }
  $state[$Path] = [ordered]@{ session = $Sid; offset = $tail.next; pending = @($pending.Values) }
  [IO.File]::WriteAllText($antigravityFile, ($state | ConvertTo-Json -Depth 12 -Compress), $utf8)
  return $rows.Count
}
# The session's tool calls from its transcript (and its subagents' transcripts), oldest first. Only calls with a result,
# made by this session, and no older than the transcript file. -Until: stop before this tool_use_id (the mapping call).
function Get-TranscriptCalls([string]$Sid, [string]$Path, [string]$Until) {
  if ($Agent -eq 'codex') { return (Get-CodexTranscriptCalls $Sid $Path $Until) }
  if ($Agent -eq 'antigravity') { return (Get-AntigravityTranscriptCalls $Sid $Path $Until) }
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
          $resp = if ($null -ne $o.toolUseResult -and $o.toolUseResult -isnot [string]) { (Expand-Saved $o.toolUseResult) | ConvertTo-Json -Depth 8 -Compress } elseif ($o.toolUseResult) { [string]$o.toolUseResult } else { $text }
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
      event      = $(if ($r.error -and $Agent -eq 'claude') { 'PostToolUseFailure' } else { 'PostToolUse' })
      cwd        = $c.cwd
      status     = 'from_transcript'
      tool       = $c.name
      tool_use_id = $c.id
    }
    if ($c.agent) { $row.subagent = $c.agent }
    $inp = [ordered]@{}
    if ($c.input) { foreach ($p in $c.input.PSObject.Properties) { $inp[$p.Name] = Clip $p.Value $maxText } }
    $row.input = $inp
    if ($r.error) { Set-Output $row 'error' $r.text }
    Set-Output $row 'response' $r.resp
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
# "assistant" row's text blocks are a reply, its thinking blocks the turn's reasoning summary (role "thinking";
# tool_use blocks are in actions.jsonl). A prompt typed while the model
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
      if ("$text".Trim()) { $out.Add([pscustomobject]@{ id = [string]$o.uuid; role = 'user'; ts = $ts; text = "$text"; images = 0; model = ''; phase = ''; mid = $true; redacted = $false }) }
      continue
    }
    $role = [string]$o.type
    if (($role -ne 'user' -and $role -ne 'assistant') -or [string]$o.sessionId -ne $Sid -or -not $o.timestamp -or -not $o.uuid) { continue }
    if ($o.isMeta -or $o.isCompactSummary -or $o.isApiErrorMessage) { continue }
    if ($o.PSObject.Properties['origin'] -and $o.origin -and [string]$o.origin.kind -ne 'human') { continue }   # e.g. a background task's notice
    $ts = ConvertTo-Time $o.timestamp
    if ($ts.UtcDateTime -lt $Created) { continue }
    $c = $o.message.content; $images = 0; $hidden = 0
    $think = New-Object System.Collections.Generic.List[string]
    $text = if ($c -is [string]) { $c } else {
      (@(foreach ($b in @($c)) {
          if ($b.type -eq 'text') { [string]$b.text } elseif ($b.type -eq 'image') { $images++ }
          elseif ($b.type -eq 'thinking') { if ("$($b.thinking)".Trim()) { $think.Add([string]$b.thinking) } else { $hidden++ } }
          elseif ($b.type -eq 'redacted_thinking') { $hidden++ }
        }) -join "`n")
    }
    $model = if ($role -eq 'assistant') { [string]$o.message.model } else { '' }
    # the reasoning summary of the turn, as the agent saved it; a block saved without readable text is a row with none
    if ($role -eq 'assistant' -and ($think.Count -or $hidden)) {
      $out.Add([pscustomobject]@{ id = [string]$o.uuid + ':thinking'; role = 'thinking'; ts = $ts; text = ($think -join "`n"); images = 0; model = $model; phase = ''; mid = $false; redacted = ($think.Count -eq 0) })
    }
    if (-not "$text".Trim() -and -not $images) { continue }
    $out.Add([pscustomobject]@{ id = [string]$o.uuid; role = $role; ts = $ts; text = "$text"; images = $images; model = $model; phase = ''; mid = $false; redacted = $false })
  }
  return , $out
}
# Codex: the rollout's finished UserMessage, AgentMessage and Reasoning items of thread $Thread (item.id is the
# message's id). A Reasoning item's summary_text (and raw_content, when the rollout holds it as text) is the reasoning
# summary; one saved without readable text is a row with none. In a subagent's rollout ($AgentPath = its agent path),
# a message another agent sent it (a response_item "agent_message" to that path: its task, a follow-up, a result) is a
# "user" row. Codex encrypts such a message's payload (encrypted_content), so the row holds only its readable header
# (message type, task name, sender) and "encrypted": true.
function Get-CodexMessages([string]$Thread, $Lines, [datetime]$Created, [string]$AgentPath) {
  $out = New-Object System.Collections.Generic.List[object]
  foreach ($line in $Lines) {
    if ($AgentPath -and $line -match '"agent_message"' -and $line -match '"response_item"') {
      try { $o = $line | ConvertFrom-Json } catch { continue }
      $p = $o.payload
      if ($o.type -ne 'response_item' -or $p.type -ne 'agent_message' -or [string]$p.recipient -ne $AgentPath -or -not $p.id -or -not $o.timestamp) { continue }
      $ts = ConvertTo-Time $o.timestamp
      if ($ts.UtcDateTime -lt $Created) { continue }
      $enc = $false
      $parts = @(foreach ($b in @($p.content)) {
          if ([string]$b.type -eq 'encrypted_content') { $enc = $true } elseif ($b.PSObject.Properties['text'] -and $b.text) { [string]$b.text }
        })
      $text = ($parts -join "`n").TrimEnd()
      if (-not $text -and -not $enc) { continue }
      $out.Add([pscustomobject]@{ id = [string]$p.id; role = 'user'; ts = $ts; text = $text; images = 0; model = ''; phase = ''; mid = $false; redacted = $false; encrypted = $enc })
      continue
    }
    if ($line -notmatch '"item_completed"' -or $line -notmatch '"(?:UserMessage|AgentMessage|Reasoning)"') { continue }
    try { $o = $line | ConvertFrom-Json } catch { continue }
    $p = $o.payload
    if ($o.type -ne 'event_msg' -or $p.type -ne 'item_completed' -or -not $p.item -or -not $o.timestamp) { continue }
    if ($p.thread_id -and [string]$p.thread_id -ne $Thread) { continue }   # another thread's, or a copied context's
    $it = $p.item
    $role = if ([string]$it.type -eq 'UserMessage') { 'user' } elseif ([string]$it.type -eq 'AgentMessage') { 'assistant' } elseif ([string]$it.type -eq 'Reasoning') { 'thinking' } else { '' }
    if (-not $role -or -not $it.id) { continue }
    $ts = ConvertTo-Time $o.timestamp
    if ($ts.UtcDateTime -lt $Created) { continue }
    if ($role -eq 'thinking') {
      $parts = @(foreach ($b in (@($it.summary_text) + @($it.raw_content))) {
          if ($b -is [string]) { $b } elseif ($b -and $b.PSObject.Properties['text'] -and $b.text) { [string]$b.text }
        })
      $text = (@($parts | Where-Object { "$_".Trim() }) -join "`n")
      $out.Add([pscustomobject]@{ id = [string]$it.id; role = 'thinking'; ts = $ts; text = "$text"; images = 0; model = ''; phase = ''; mid = $false; redacted = (-not "$text".Trim()) })
      continue
    }
    $images = 0
    $text = (@(foreach ($b in @($it.content)) { if ($b.PSObject.Properties['text'] -and $b.text) { [string]$b.text } elseif ([string]$b.type -match '(?i)image') { $images++ } }) -join "`n")
    if (-not "$text".Trim() -and -not $images) { continue }
    $out.Add([pscustomobject]@{ id = [string]$it.id; role = $role; ts = $ts; text = "$text"; images = $images; model = ''; phase = [string]$it.phase; mid = $false; redacted = $false })
  }
  return , $out
}
# Antigravity: the transcript's USER_INPUT steps from USER_EXPLICIT (the text inside <USER_REQUEST>; "media" are the
# pictures attached) and PLANNER_RESPONSE steps (content: the reply; thinking: the reasoning as saved, role
# "thinking"). A message's id is "<conversation id>:<step_index>" (":thinking" for the reasoning).
function Get-AntigravityMessages([string]$Sid, $Lines, [datetime]$Created) {
  $out = New-Object System.Collections.Generic.List[object]
  foreach ($line in $Lines) {
    if ($line -notmatch '"type"\s*:\s*"(?:USER_INPUT|PLANNER_RESPONSE)"') { continue }
    try { $o = $line | ConvertFrom-Json } catch { continue }
    if ($null -eq $o.step_index -or -not $o.created_at) { continue }
    $ts = ConvertTo-Time $o.created_at
    if ($ts.UtcDateTime -lt $Created) { continue }
    $id = "${Sid}:$([int]$o.step_index)"
    $text = Get-AntigravityText $o
    if ([string]$o.type -eq 'USER_INPUT') {
      if ([string]$o.source -ne 'USER_EXPLICIT') { continue }
      $m = [regex]::Match($text, '(?s)<USER_REQUEST>\r?\n?(.*?)\r?\n?</USER_REQUEST>')
      if ($m.Success) { $text = $m.Groups[1].Value }
      $images = @($o.media | Where-Object { $_ }).Count
      if (-not "$text".Trim() -and -not $images) { continue }
      $out.Add([pscustomobject]@{ id = $id; role = 'user'; ts = $ts; text = "$text"; images = $images; model = ''; phase = ''; mid = $false; redacted = $false })
      continue
    }
    $model = [string]$o.model
    if ("$($o.thinking)".Trim()) {
      $out.Add([pscustomobject]@{ id = "${id}:thinking"; role = 'thinking'; ts = $ts; text = [string]$o.thinking; images = 0; model = $model; phase = ''; mid = $false; redacted = $false })
    }
    if (-not "$text".Trim()) { continue }
    $out.Add([pscustomobject]@{ id = $id; role = 'assistant'; ts = $ts; text = "$text"; images = 0; model = $model; phase = ''; mid = $false; redacted = $false })
  }
  return , $out
}
# Append to <project>\messages.jsonl what the session's transcript (and its subagents' transcripts) gained
# since the last read. Returns the number of rows written; $script:Read collects the session's own messages read
# ("<role> <text>"). -All (the backfill): every transcript from its start, whatever was read before, and then the
# session's rows in the order read ($script:Order: message id -> its place).
$script:Read = New-Object System.Collections.Generic.List[string]
$script:Order = @{}
$script:WaitFor = ''   # whose messages Test-MessageRead looks among: '' the session's own, else a subagent's tag
# The session's rows of a messages.jsonl back in the transcript's order (time, then the order read), in the places
# its rows already hold; every other session's rows stay where they are.
function Sort-SessionRows([string]$File, [string]$Sid) {
  $lines = [IO.File]::ReadAllLines($File, $utf8)
  $want = '"session_id":"' + $Sid + '"'
  $at = New-Object System.Collections.Generic.List[int]
  $items = New-Object System.Collections.Generic.List[object]
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if (-not $lines[$i].Contains($want)) { continue }
    $t = [DateTimeOffset]::MinValue
    [void][DateTimeOffset]::TryParse([regex]::Match($lines[$i], '"time":"([^"]+)"').Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$t)
    $id = [regex]::Match($lines[$i], '"message_id":"([^"]+)"').Groups[1].Value
    $ord = if ($id -and $script:Order.ContainsKey($id)) { [int]$script:Order[$id] } else { 0 }
    $at.Add($i)
    $items.Add([pscustomobject]@{ line = $lines[$i]; t = [long]$t.UtcTicks; ord = $ord; i = $i })
  }
  $sorted = @($items | Sort-Object t, ord, i)
  $changed = $false
  for ($k = 0; $k -lt $at.Count; $k++) {
    if ($lines[$at[$k]] -cne $sorted[$k].line) { $lines[$at[$k]] = $sorted[$k].line; $changed = $true }
  }
  if ($changed) {
    $tmp = "$File.sort-tmp"
    [IO.File]::WriteAllText($tmp, (($lines -join "`n") + "`n"), $utf8)
    Move-Item -Force $tmp $File
  }
}
function Sync-Messages([string]$Sid, [string]$Project, [string]$Path, [switch]$All, [string]$ChildPath) {
  if (-not $Path) { $Path = Find-Transcript $Sid }
  if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return 0 }   # a session's first prompt comes before its transcript
  if ($Agent -eq 'codex') { $Path = Resolve-CodexRoot $Sid $Path }
  elseif ($Agent -eq 'antigravity') { $Path = Resolve-AntigravityTranscript $Path }
  # read: the session's transcript, then its subagents' (Claude Code: <session>\subagents\*.jsonl; Codex: the rollouts
  # that what this call reads of the parent's rollout names, the one a SubagentStop names ($ChildPath), and theirs)
  $todo = New-Object System.Collections.Generic.Queue[object]
  $todo.Enqueue([pscustomobject]@{ path = $Path; thread = $Sid; tag = ''; agent_path = '' })
  $threads = @{ $Sid = $true }
  if ($Agent -eq 'claude') {
    $sub = Join-Path (Join-Path (Split-Path $Path) $Sid) 'subagents'
    if (Test-Path -LiteralPath $sub) {
      foreach ($sf in @(Get-ChildItem -LiteralPath $sub -Filter '*.jsonl' | ForEach-Object FullName)) {
        $todo.Enqueue([pscustomobject]@{ path = $sf; thread = $Sid; tag = [IO.Path]::GetFileNameWithoutExtension($sf); agent_path = '' })
      }
    }
  }
  $addChild = {   # a Codex subagent's rollout: read with its own thread id, its rows tagged with it
    param([string]$ChildFile)
    if (-not $ChildFile -or -not (Test-Path -LiteralPath $ChildFile)) { return }
    $meta = Get-CodexRolloutMeta $ChildFile
    if (-not $meta -or -not $meta.thread -or $threads.ContainsKey($meta.thread)) { return }
    $threads[$meta.thread] = $true
    $todo.Enqueue([pscustomobject]@{ path = $ChildFile; thread = $meta.thread; tag = $meta.thread; agent_path = $meta.agent_path })
  }
  if ($Agent -eq 'codex' -and $ChildPath) { & $addChild $ChildPath }
  $created = (Get-Item -LiteralPath $Path).CreationTimeUtc.AddSeconds(-5)   # older rows are a fork's copied context
  $state = Read-JsonMap $messagesFile
  $dir = Join-Path $recRoot $Project
  $file = Join-Path $dir 'messages.jsonl'
  $seen = $null; $moved = $false
  $rows = New-Object System.Collections.Generic.List[string]
  while ($todo.Count) {
    $src = $todo.Dequeue(); $f = $src.path
    $from = if (-not $All -and $state.ContainsKey($f)) { [long]$state[$f] } else { [long]0 }
    while ($true) {   # one read a call; -All: read after read (256 MB each) to the transcript's end
      $tail = Read-TranscriptTail $f $from
      if ($tail.next -eq $from) { break }
      $state[$f] = $tail.next; $moved = $true
      # a transcript read from its start (first read, the state file was lost, or -All): never write a message twice
      if ($All -or $tail.next -lt $from -or $from -eq 0) { if ($null -eq $seen) { $seen = Get-RecordedIds $file 'message_id' } }
      $subagent = $src.tag
      $msgs = if ($Agent -eq 'codex') { Get-CodexMessages $src.thread $tail.lines $created $src.agent_path }
              elseif ($Agent -eq 'antigravity') { Get-AntigravityMessages $Sid $tail.lines $created }
              else { Get-ClaudeMessages $Sid $tail.lines $created }
      if ($Agent -eq 'codex') {
        foreach ($k in (Get-CodexSubagents $tail.lines $src.thread)) { if (-not $threads.ContainsKey($k)) { & $addChild (Find-CodexRollout $f $k) } }
      }
      foreach ($m in $msgs) {
        if ($subagent -eq $script:WaitFor -and $m.role -ne 'thinking') { $script:Read.Add("$($m.role) $($m.text)") }
        if ($All -and -not $script:Order.ContainsKey($m.id)) { $script:Order[$m.id] = $script:Order.Count }
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
        if ($m.redacted) { $row.redacted = $true }
        if ($m.encrypted) { $row.encrypted = $true }
        $row.text = Clip $m.text $maxText
        $rows.Add(($row | ConvertTo-Json -Depth 4 -Compress))
      }
      if (-not $All -or $tail.next -lt $from) { break }
      $from = $tail.next
    }
  }
  if ($rows.Count) {
    New-Item -ItemType Directory -Force $dir | Out-Null
    [IO.File]::AppendAllText($file, (($rows -join "`n") + "`n"), $utf8)
    if ($All) { Sort-SessionRows $file $Sid }
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

# The subagent a hook call comes from ('' for the session itself): Claude Code and Codex put agent_id (and agent_type)
# in the input of a hook that fires inside a subagent. The tag is what the subagent's transcript is called, as on its
# rows imported from it: Claude Code "agent-<agent_id>" (subagents\agent-<agent_id>.jsonl), Codex its thread id.
function Get-SubagentTag($E) {
  $id = [string]$E.agent_id
  if (-not $id -or $id -eq [string]$E.session_id) { return '' }
  if ($Agent -eq 'claude' -and $id -notmatch '^agent-') { return "agent-$id" }
  return $id
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
        foreach ($a in 'claude', 'codex', 'antigravity') { $Agent = $a; $t = Find-Transcript $s; if ($t) { break } }
        if (-not $t) { continue }
        $found++; $n = Sync-Messages $s ([string]$map[$s]) $t -All; $total += $n
        if ($n) { Write-Host "$n message(s) of session $s ($Agent) -> $([string]$map[$s])\messages.jsonl" }
      }
      Write-Host "imported $total message(s) from $found of $($map.Count) mapped session(s)$(if ($found -lt $map.Count) { '; the others have no transcript on this machine' })"
      exit 0
    }
    if (-not $map.ContainsKey($Backfill)) { throw "session $Backfill is not mapped to a project (recording-sessions.json)" }
    $n = Sync-Messages $Backfill ([string]$map[$Backfill]) $TranscriptPath -All
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
if ($Agent -eq 'antigravity') { $e = ConvertFrom-AntigravityHook $e }
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
  # Antigravity's tools name paths and commands in arguments of their own (CommandLine, Cwd, Path, TargetFile, ...)
  if ($Agent -eq 'antigravity' -and $e.tool_input) { foreach ($p in $e.tool_input.PSObject.Properties) { if ($p.Value -is [string]) { $texts += $p.Value } } }
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
  if ($newlyMapped -and -not $Stop -and $Agent -ne 'antigravity' -and $e.transcript_path -and (Test-Path ([string]$e.transcript_path)) -and -not (Read-JsonMap $backfillFile).ContainsKey($sid)) {
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
      # SubagentStop (Codex): the subagent's rollout is agent_transcript_path, its rows are tagged with agent_id
      $subStop = [string]$e.hook_event_name -eq 'SubagentStop'
      $script:WaitFor = if ($subStop) { Get-SubagentTag $e } else { '' }
      $childPath = if ($subStop -and $Agent -eq 'codex') { [string]$e.agent_transcript_path } else { '' }
      [void](Sync-Messages $sid $project ([string]$e.transcript_path) -ChildPath $childPath)
      # the message this call is about may reach the transcript a moment after the hook starts: the turn's last reply
      # (Stop; SubagentStop: the subagent's), the prompt just typed (UserPromptSubmit)
      $role = if ($Stop -or $subStop) { 'assistant' } else { 'user' }
      $text = if ($Stop -or $subStop) { [string]$e.last_assistant_message } else { [string]$e.prompt }
      # Antigravity's Stop names no reply: the turn's end is a last step that is a reply without tool calls
      $read = if ($Agent -eq 'antigravity' -and $Stop) { { Test-AntigravityTurnEnded ([string]$e.transcript_path) } } else { { Test-MessageRead $role $text } }
      for ($i = 0; $i -lt 7 -and -not (& $read); $i++) {
        Start-Sleep -Milliseconds 300
        [void](Sync-Messages $sid $project ([string]$e.transcript_path) -ChildPath $childPath)
      }
    } catch { }
    if ($Messages) { exit 0 }   # UserPromptSubmit, SessionEnd: no row in actions.jsonl
  }
  # a call already imported from the transcript is not written twice
  $bf = Read-JsonMap $backfillFile
  if ($e.tool_use_id -and $bf.ContainsKey($sid) -and (@($bf[$sid].tool_use_ids) -contains [string]$e.tool_use_id)) { exit 0 }
  # Antigravity: its hook input holds no result, and the result reaches the transcript after the hook; every call
  # writes the calls the transcript completed since the last one (a newly mapped session's earlier calls too)
  if ($Agent -eq 'antigravity') {
    [void](Sync-AntigravityCalls $sid $project ([string]$e.transcript_path))
    if (-not $Stop) { exit 0 }
  }

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
    $tag = Get-SubagentTag $e
    if ($tag) { $row.subagent = $tag; if ($e.agent_type) { $row.agent_type = [string]$e.agent_type } }
    $inp = [ordered]@{}
    if ($e.tool_input) { foreach ($p in $e.tool_input.PSObject.Properties) { $inp[$p.Name] = Clip $p.Value $maxText } }
    $row.input = $inp
    if ($e.error) { Set-Output $row 'error' ([string]$e.error) }
    Set-Output $row 'response' $e.tool_response
  }
  [IO.File]::AppendAllText($actions, ($row | ConvertTo-Json -Depth 12 -Compress) + "`n", $utf8)
} finally { $mutex.ReleaseMutex() }
exit 0
