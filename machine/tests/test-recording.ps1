<#
.SYNOPSIS
  The recording hook (record-action.ps1) and the agents' reasoning-summary settings (lib\codex-hooks.ps1), run on
  made-up transcripts in the shapes Claude Code, Codex and Antigravity write, in a scratch folder under %TEMP%. Nothing of this
  machine's recording, agent settings or games is read or written.
.DESCRIPTION
  Checks: a tool call's whole output in actions.jsonl (live rows and rows imported from the transcript), the cut at
  1,000,000 characters with "response_truncated" and "response_chars", the marker in place of a picture's base64, a
  long command output read from
  the file Claude Code saved it to; the reasoning summaries as role "thinking" rows of messages.jsonl in the
  transcript's order (Claude Code thinking blocks, Codex Reasoning items, a summary saved without text as "redacted",
  Codex raw_content kept when it is text), written once; -Backfill adding them to a session recorded before they were and
  putting its rows back in order; Antigravity's own hook input (the result read from transcript_full.jsonl, the
  prompt without what Antigravity adds, {} answered on stdout every time); and config.toml's reasoning-summary settings
  read and set without touching other lines.
  Exit code: the number of failed checks.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File machine\tests\test-recording.ps1
#>
$ErrorActionPreference = 'Stop'
$utf8 = New-Object Text.UTF8Encoding($false)
$machine = Split-Path -Parent $PSScriptRoot
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('gf-rec-test-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
$root = Join-Path $tmp 'Work'
$hooks = Join-Path $tmp 'hooks'
$fakeHome = Join-Path $tmp 'home'
$fails = New-Object System.Collections.Generic.List[string]
function Check([string]$Name, $Ok, [string]$Detail = '') {
  if ($Ok) { Write-Host "ok   $Name" } else { Write-Host "FAIL $Name $Detail" -ForegroundColor Red; $fails.Add($Name) }
}
function Line($o) { return ($o | ConvertTo-Json -Depth 12 -Compress) }
function Rows([string]$File) {
  if (-not (Test-Path -LiteralPath $File)) { return @() }
  return @([IO.File]::ReadAllLines($File, $utf8) | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })
}
$t0 = [DateTime]::UtcNow
function T([int]$i) { return $t0.AddMilliseconds($i * 10).ToString('yyyy-MM-ddTHH:mm:ss.fffZ', [Globalization.CultureInfo]::InvariantCulture) }

$saved = @{}
foreach ($k in 'GF_ROOT', 'GF_CONFIG', 'USERPROFILE', 'CODEX_HOME', 'GF_NO_RECORDING', 'UGF_NO_RECORDING') { $saved[$k] = [Environment]::GetEnvironmentVariable($k) }
try {
  New-Item -ItemType Directory -Force (Join-Path $root 'games\demo'), $hooks, (Join-Path $fakeHome '.claude\projects\p'), (Join-Path $fakeHome '.codex\sessions\2026\11\11') | Out-Null
  Copy-Item -LiteralPath (Join-Path $machine 'hooks\record-action.ps1') -Destination $hooks
  Copy-Item -LiteralPath (Join-Path $machine 'lib\gf-root.ps1') -Destination $hooks
  $hook = Join-Path $hooks 'record-action.ps1'
  $exe = (Get-Process -Id $PID).Path
  $env:GF_ROOT = $root
  $env:GF_CONFIG = Join-Path $tmp 'no-config.json'
  $env:USERPROFILE = $fakeHome
  $env:CODEX_HOME = Join-Path $fakeHome '.codex'
  $env:GF_NO_RECORDING = $null
  $env:UGF_NO_RECORDING = $null
  function Invoke-Hook([string]$Json, [string[]]$HookArgs = @()) {
    $Json | & $exe -NoProfile -ExecutionPolicy Bypass -File $hook @HookArgs | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "the hook exited $LASTEXITCODE ($($HookArgs -join ' '))" }
  }
  $cwd = Join-Path $root 'games\demo'
  $actions = Join-Path $root '.recording\demo\actions.jsonl'
  $messages = Join-Path $root '.recording\demo\messages.jsonl'

  # ---- Claude Code ---------------------------------------------------------------------------------------------------
  Write-Host 'Claude Code'
  $t0 = [DateTime]::UtcNow   # rows older than their transcript file are a fork's copied context: stamp them after it
  $sid = [Guid]::NewGuid().ToString()
  $tr = Join-Path $fakeHome ".claude\projects\p\$sid.jsonl"
  $big = ('line of build output' + "`n") * 1000 + 'END-OF-OUTPUT'   # 21,013 characters: rows held 8,000 before
  $lines = @(
    (Line ([ordered]@{ type = 'user'; sessionId = $sid; uuid = 'u-1'; timestamp = (T 1); cwd = $cwd; message = [ordered]@{ role = 'user'; content = 'Make the door open.' } })),
    (Line ([ordered]@{ type = 'assistant'; sessionId = $sid; uuid = 'a-1'; timestamp = (T 2); cwd = $cwd; message = [ordered]@{ role = 'assistant'; model = 'model-x'; content = @([ordered]@{ type = 'thinking'; thinking = 'The door needs a hinge first.'; signature = 'c2lnbmF0dXJl' }) } })),
    (Line ([ordered]@{ type = 'assistant'; sessionId = $sid; uuid = 'a-2'; timestamp = (T 3); cwd = $cwd; message = [ordered]@{ role = 'assistant'; model = 'model-x'; content = @([ordered]@{ type = 'thinking'; thinking = ''; signature = 'c2lnbmF0dXJl' }) } })),
    (Line ([ordered]@{ type = 'assistant'; sessionId = $sid; uuid = 'a-3'; timestamp = (T 4); cwd = $cwd; message = [ordered]@{ role = 'assistant'; model = 'model-x'; content = @([ordered]@{ type = 'tool_use'; id = 'toolu_1'; name = 'Bash'; input = [ordered]@{ command = 'dir' } }) } })),
    (Line ([ordered]@{ type = 'user'; sessionId = $sid; uuid = 'u-2'; timestamp = (T 5); cwd = $cwd; toolUseResult = [ordered]@{ stdout = $big; stderr = ''; interrupted = $false; isImage = $false }; message = [ordered]@{ role = 'user'; content = @([ordered]@{ type = 'tool_result'; tool_use_id = 'toolu_1'; content = 'cut for the model' }) } })),
    (Line ([ordered]@{ type = 'assistant'; sessionId = $sid; uuid = 'a-4'; timestamp = (T 6); cwd = $cwd; message = [ordered]@{ role = 'assistant'; model = 'model-x'; content = @([ordered]@{ type = 'text'; text = 'The door opens now.' }) } }))
  )
  [IO.File]::WriteAllText($tr, ($lines -join "`n") + "`n", $utf8)

  # a live call: maps the session, imports the earlier call from the transcript, then its own row
  $live = 'live output ' * 2000 + 'END-OF-LIVE'
  Invoke-Hook (Line ([ordered]@{ session_id = $sid; transcript_path = $tr; cwd = $cwd; hook_event_name = 'PostToolUse'; tool_name = 'Bash'; tool_use_id = 'toolu_2'
        tool_input = [ordered]@{ command = "git -C $cwd status" }; tool_response = [ordered]@{ stdout = $live; stderr = ''; interrupted = $false } }))
  $a = @(Rows $actions)
  Check 'the earlier call is imported from the transcript with its whole output' ($a.Count -eq 2 -and $a[0].tool_use_id -eq 'toolu_1' -and $a[0].status -eq 'from_transcript' -and ([string]$a[0].response).Contains('END-OF-OUTPUT') -and $null -eq $a[0].response_truncated) "rows: $($a.Count)"
  Check 'a live row holds its whole output' ($a.Count -eq 2 -and $a[1].tool_use_id -eq 'toolu_2' -and ([string]$a[1].response).Contains('END-OF-LIVE') -and ([string]$a[1].response).Length -gt 24000 -and $null -eq $a[1].response_truncated)

  # an output over the cap
  Invoke-Hook (Line ([ordered]@{ session_id = $sid; transcript_path = $tr; cwd = $cwd; hook_event_name = 'PostToolUse'; tool_name = 'Bash'; tool_use_id = 'toolu_3'
        tool_input = [ordered]@{ command = 'type huge.log' }; tool_response = ('yes ' * 300000) }))
  $r = @(Rows $actions)[-1]
  Check 'an output over 1,000,000 characters is cut there and marked' ($r.tool_use_id -eq 'toolu_3' -and $r.response_truncated -eq $true -and $r.response_chars -eq 1200000 -and ([string]$r.response).StartsWith('yes yes ') -and ([string]$r.response).Length -ge 1000000 -and ([string]$r.response).Length -lt 1000100) "length $(([string]$r.response).Length), response_truncated $($r.response_truncated), response_chars $($r.response_chars)"

  # a picture: base64 in the result
  Invoke-Hook (Line ([ordered]@{ session_id = $sid; transcript_path = $tr; cwd = $cwd; hook_event_name = 'PostToolUse'; tool_name = 'Read'; tool_use_id = 'toolu_4'
        tool_input = [ordered]@{ file_path = (Join-Path $cwd 'shot.png') }; tool_response = [ordered]@{ type = 'image'; file = [ordered]@{ base64 = ('QUJD' * 1500); type = 'image/png'; originalSize = 4500 } } }))
  $r = @(Rows $actions)[-1]
  Check 'a picture is a marker with its size, beside its type' ($r.tool_use_id -eq 'toolu_4' -and ([string]$r.response).Contains('[binary 6000 chars]') -and ([string]$r.response).Contains('image/png') -and -not ([string]$r.response).Contains('QUJDQUJD') -and $null -eq $r.response_truncated) ([string]$r.response).Substring(0, [Math]::Min(200, ([string]$r.response).Length))

  # a long command output Claude Code cut in the result and saved to a file
  $savedOut = Join-Path $tmp 'saved-output.txt'
  [IO.File]::WriteAllText($savedOut, ('saved line' + "`n") * 5000 + 'END-OF-SAVED', $utf8)
  Invoke-Hook (Line ([ordered]@{ session_id = $sid; transcript_path = $tr; cwd = $cwd; hook_event_name = 'PostToolUse'; tool_name = 'Bash'; tool_use_id = 'toolu_5'
        tool_input = [ordered]@{ command = 'build' }; tool_response = [ordered]@{ stdout = 'saved line'; stderr = ''; interrupted = $false; persistedOutputPath = $savedOut; persistedOutputSize = 55012 } }))
  $r = @(Rows $actions)[-1]
  Check 'an output saved to a file is read from the file' ($r.tool_use_id -eq 'toolu_5' -and ([string]$r.response).Contains('END-OF-SAVED'))

  # a subagent's call: the hook input names it (agent_id, agent_type)
  Invoke-Hook (Line ([ordered]@{ session_id = $sid; transcript_path = $tr; cwd = $cwd; hook_event_name = 'PostToolUse'; tool_name = 'Bash'; tool_use_id = 'toolu_6'; agent_id = 'a1b2c3'; agent_type = 'Explore'
        tool_input = [ordered]@{ command = 'dir' }; tool_response = [ordered]@{ stdout = 'ok'; stderr = ''; interrupted = $false } }))
  $a = @(Rows $actions)
  Check 'a subagent''s live call carries subagent (its transcript''s name) and agent_type' ($a[-1].tool_use_id -eq 'toolu_6' -and $a[-1].subagent -eq 'agent-a1b2c3' -and $a[-1].agent_type -eq 'Explore')
  Check 'the session''s own live call carries neither' ($a[-2].tool_use_id -eq 'toolu_5' -and $null -eq $a[-2].subagent -and $null -eq $a[-2].agent_type)

  # the end of the turn: prompts, replies and reasoning summaries from the transcript
  $stop = Line ([ordered]@{ session_id = $sid; transcript_path = $tr; cwd = $cwd; hook_event_name = 'Stop'; last_assistant_message = 'The door opens now.' })
  Invoke-Hook $stop @('-Stop')
  $m = @(Rows $messages)
  Check 'messages.jsonl: prompt, two reasoning summaries, reply, in the transcript''s order' ((@($m | ForEach-Object { "$($_.role) $($_.message_id)" }) -join ', ') -ceq 'user u-1, thinking a-1:thinking, thinking a-2:thinking, assistant a-4') (@($m | ForEach-Object { "$($_.role) $($_.message_id)" }) -join ', ')
  Check 'a reasoning summary holds the saved text, its agent and model' ($m.Count -eq 4 -and $m[1].text -ceq 'The door needs a hinge first.' -and $m[1].agent -eq 'claude' -and $m[1].model -eq 'model-x' -and $m[1].session_id -eq $sid -and $null -eq $m[1].redacted)
  Check 'a summary saved without text is an empty, redacted row' ($m.Count -eq 4 -and $m[2].text -ceq '' -and $m[2].redacted -eq $true)
  Check 'the reply row is unchanged' ($m.Count -eq 4 -and $m[3].text -ceq 'The door opens now.' -and $null -eq $m[3].redacted)
  Invoke-Hook $stop @('-Stop')
  Check 'a second read writes nothing twice' (@(Rows $messages).Count -eq 4)

  # a session recorded before reasoning summaries were: -Backfill adds them, in order, once
  $old = @([IO.File]::ReadAllLines($messages, $utf8) | Where-Object { $_ -notmatch '"role":"thinking"' })
  [IO.File]::WriteAllText($messages, ($old -join "`n") + "`n", $utf8)
  & $exe -NoProfile -ExecutionPolicy Bypass -File $hook -Backfill $sid -TranscriptPath $tr | Out-Null
  $m = @(Rows $messages)
  Check '-Backfill adds the summaries and puts the session''s rows back in order' ((@($m | ForEach-Object { "$($_.role) $($_.message_id)" }) -join ', ') -ceq 'user u-1, thinking a-1:thinking, thinking a-2:thinking, assistant a-4') (@($m | ForEach-Object { "$($_.role) $($_.message_id)" }) -join ', ')
  & $exe -NoProfile -ExecutionPolicy Bypass -File $hook -Backfill all | Out-Null
  Check '-Backfill all a second time adds nothing' (@(Rows $messages).Count -eq 4)

  # ---- Codex -----------------------------------------------------------------------------------------------------------
  Write-Host 'Codex'
  $t0 = [DateTime]::UtcNow   # rows older than their transcript file are a fork's copied context: stamp them after it
  $sid2 = [Guid]::NewGuid().ToString()
  $roll = Join-Path $fakeHome ".codex\sessions\2026\11\11\rollout-2026-11-11T10-00-00-$sid2.jsonl"
  function Item($i, $item) { return (Line ([ordered]@{ timestamp = (T $i); type = 'event_msg'; payload = [ordered]@{ type = 'item_completed'; thread_id = $sid2; turn_id = 'turn-1'; item = $item } })) }
  $lines = @(
    (Item 20 ([ordered]@{ type = 'UserMessage'; id = 'um-1'; content = @([ordered]@{ type = 'text'; text = 'Add a lamp.' }) })),
    (Item 21 ([ordered]@{ type = 'Reasoning'; id = 'rs-1'; summary_text = @('Plan the lamp.', 'Then wire it.'); raw_content = @('Raw reasoning kept as text.') })),
    (Item 22 ([ordered]@{ type = 'Reasoning'; id = 'rs-2'; summary_text = @(); raw_content = @() })),
    (Item 23 ([ordered]@{ type = 'CommandExecution'; id = 'call-1'; command = @('cmd', '/c', 'dir'); cwd = $cwd; status = 'completed'; aggregated_output = $big; exit_code = 0 })),
    (Item 24 ([ordered]@{ type = 'AgentMessage'; id = 'am-1'; content = @([ordered]@{ type = 'Text'; text = 'Lamp added.' }); phase = 'final' }))
  )
  [IO.File]::WriteAllText($roll, ($lines -join "`n") + "`n", $utf8)
  Invoke-Hook (Line ([ordered]@{ session_id = $sid2; transcript_path = $roll; cwd = $cwd; hook_event_name = 'PostToolUse'; tool_name = 'Bash'; tool_use_id = 'call-2'
        tool_input = [ordered]@{ command = "dir $cwd" }; tool_response = 'ok' })) @('-Agent', 'codex')
  $c = @(Rows $actions | Where-Object { $_.session_id -eq $sid2 })
  Check 'Codex: the earlier call is imported from the rollout with its whole output' ($c.Count -eq 2 -and $c[0].tool_use_id -eq 'call-1' -and $c[0].agent -eq 'codex' -and ([string]$c[0].response).Contains('END-OF-OUTPUT') -and $c[1].tool_use_id -eq 'call-2') "rows: $($c.Count)"
  Invoke-Hook (Line ([ordered]@{ session_id = $sid2; transcript_path = $roll; cwd = $cwd; hook_event_name = 'Stop'; last_assistant_message = 'Lamp added.' })) @('-Stop', '-Agent', 'codex')
  $m = @(Rows $messages | Where-Object { $_.session_id -eq $sid2 })
  Check 'Codex: prompt, two reasoning summaries, reply, in the rollout''s order' ((@($m | ForEach-Object { "$($_.role) $($_.message_id)" }) -join ', ') -ceq 'user um-1, thinking rs-1, thinking rs-2, assistant am-1') (@($m | ForEach-Object { "$($_.role) $($_.message_id)" }) -join ', ')
  Check 'Codex: a summary''s parts are one row; one without a summary is redacted' ($m.Count -eq 4 -and $m[1].text -ceq "Plan the lamp.`nThen wire it.`nRaw reasoning kept as text." -and $m[1].agent -eq 'codex' -and $null -eq $m[1].redacted -and $m[2].text -ceq '' -and $m[2].redacted -eq $true)
  Check 'the other session''s rows are as they were' (@(Rows $messages | Where-Object { $_.session_id -eq $sid }).Count -eq 4)

  # ---- Codex subagent: its own rollout, named in the parent's by SubAgentActivity items ------------------------------
  Write-Host 'Codex subagent'
  $t0 = [DateTime]::UtcNow
  $sid3 = [Guid]::NewGuid().ToString()
  $kid = [Guid]::NewGuid().ToString()
  $proll = Join-Path $fakeHome ".codex\sessions\2026\11\11\rollout-2026-11-11T11-00-00-$sid3.jsonl"
  $kroll = Join-Path $fakeHome ".codex\sessions\2026\11\11\rollout-2026-11-11T11-00-05-$kid.jsonl"
  function Ev($i, $thread, $item) { return (Line ([ordered]@{ timestamp = (T $i); type = 'event_msg'; payload = [ordered]@{ type = 'item_completed'; thread_id = $thread; turn_id = 'turn-1'; item = $item } })) }
  function AgentNote($i, $to, $text) {
    return (Line ([ordered]@{ timestamp = (T $i); type = 'response_item'; payload = [ordered]@{ type = 'agent_message'; id = "amsg-$i"; author = '/root'; recipient = $to
            content = @([ordered]@{ type = 'input_text'; text = $text }, [ordered]@{ type = 'encrypted_content'; encrypted_content = 'gAAAAAsecret' }) } }))
  }
  # the session starts outside every project: the subagent's call naming games\demo maps it
  $plines = @(
    (Ev 30 $sid3 ([ordered]@{ type = 'UserMessage'; id = 'pum-1'; content = @([ordered]@{ type = 'text'; text = 'Make a sign.' }) })),
    (Ev 31 $sid3 ([ordered]@{ type = 'CommandExecution'; id = 'p-call-1'; command = @('cmd', '/c', 'dir'); cwd = $root; status = 'completed'; aggregated_output = 'parent listing'; exit_code = 0 })),
    (Ev 32 $sid3 ([ordered]@{ type = 'SubAgentActivity'; id = 'spawn-1'; kind = 'started'; agent_thread_id = $kid; agent_path = '/root/sign' })),
    (Ev 40 $sid3 ([ordered]@{ type = 'SubAgentActivity'; id = 'subagent-completed-1'; kind = 'completed'; agent_thread_id = $kid; agent_path = '/root/sign' })),
    (Ev 41 $sid3 ([ordered]@{ type = 'AgentMessage'; id = 'pam-1'; content = @([ordered]@{ type = 'Text'; text = 'Sign made.' }); phase = 'final_answer' }))
  )
  $klines = @(
    (Line ([ordered]@{ timestamp = (T 33); type = 'session_meta'; payload = [ordered]@{ id = $kid; session_id = $sid3; parent_thread_id = $sid3; thread_source = 'subagent'
            source = [ordered]@{ subagent = [ordered]@{ thread_spawn = [ordered]@{ parent_thread_id = $sid3; depth = 1; agent_path = '/root/sign' } } } } })),
    (Ev 33 $sid3 ([ordered]@{ type = 'UserMessage'; id = 'pum-1'; content = @([ordered]@{ type = 'text'; text = 'Make a sign.' }) })),   # copied context
    (AgentNote 33 '/root' "Message Type: FINAL_ANSWER`nSender: /root/other"),   # copied context: a message to the parent
    (AgentNote 34 '/root/sign' "Message Type: NEW_TASK`nTask name: /root/sign`nSender: /root`nPayload:`n"),
    (Ev 35 $kid ([ordered]@{ type = 'CommandExecution'; id = 'k-call-1'; command = @('cmd', '/c', 'dir'); cwd = $root; status = 'completed'; aggregated_output = 'child listing'; exit_code = 0 })),
    (Ev 36 $kid ([ordered]@{ type = 'CommandExecution'; id = 'k-call-2'; command = @('cmd', '/c', "echo hi > $cwd\sign.txt"); cwd = $root; status = 'completed'; aggregated_output = ''; exit_code = 0 })),
    (Ev 37 $kid ([ordered]@{ type = 'AgentMessage'; id = 'kam-1'; content = @([ordered]@{ type = 'Text'; text = 'finished' }); phase = 'final_answer' }))
  )
  [IO.File]::WriteAllText($proll, ($plines -join "`n") + "`n", $utf8)
  [IO.File]::WriteAllText($kroll, ($klines -join "`n") + "`n", $utf8)
  Invoke-Hook (Line ([ordered]@{ session_id = $sid3; transcript_path = $kroll; cwd = $root; hook_event_name = 'PostToolUse'; tool_name = 'Bash'; tool_use_id = 'k-call-2'; agent_id = $kid; agent_type = 'default'
        tool_input = [ordered]@{ command = "echo hi > $cwd\sign.txt" }; tool_response = '' })) @('-Agent', 'codex')
  $c = @(Rows $actions | Where-Object { $_.session_id -eq $sid3 })
  $got = @($c | ForEach-Object { "$($_.tool_use_id)|$($_.subagent)|$($_.status)" }) -join ', '
  Check 'Codex subagent: its call maps the session; the parent''s and its earlier calls come from their rollouts, its own tagged' ($got -ceq "p-call-1||from_transcript, k-call-1|$kid|from_transcript, k-call-2|$kid|") $got
  Check 'Codex subagent: its live row carries agent_type' ($c.Count -eq 3 -and $c[2].agent_type -eq 'default' -and $null -eq $c[0].agent_type)
  Invoke-Hook (Line ([ordered]@{ session_id = $sid3; transcript_path = $proll; agent_transcript_path = $kroll; cwd = $root; hook_event_name = 'SubagentStop'; agent_id = $kid; agent_type = 'default'; last_assistant_message = 'finished' })) @('-Agent', 'codex', '-Messages')
  $m = @(Rows $messages | Where-Object { $_.session_id -eq $sid3 })
  $got = @($m | ForEach-Object { "$($_.role) $($_.message_id) $($_.subagent)" }) -join ', '
  Check 'Codex subagent: SubagentStop records the session''s messages and the subagent''s, tagged; no copied context' ($got -ceq "user pum-1 , assistant pam-1 , user amsg-34 $kid, assistant kam-1 $kid") $got
  $k = @($m | Where-Object { $_.message_id -eq 'amsg-34' })
  Check 'Codex subagent: its task is the readable header only, marked encrypted' ($k.Count -eq 1 -and ([string]$k[0].text) -ceq "Message Type: NEW_TASK`nTask name: /root/sign`nSender: /root`nPayload:" -and $k[0].encrypted -eq $true) ([string]$k[0].text)
  Invoke-Hook (Line ([ordered]@{ session_id = $sid3; transcript_path = $proll; cwd = $root; hook_event_name = 'Stop'; last_assistant_message = 'Sign made.' })) @('-Stop', '-Agent', 'codex')
  Check 'Codex subagent: the parent''s Stop writes nothing twice' (@(Rows $messages | Where-Object { $_.session_id -eq $sid3 }).Count -eq 4)
  # a session whose subagent was never read (recorded before this): -Backfill all finds it from the parent's rollout
  $keep = @([IO.File]::ReadAllLines($messages, $utf8) | Where-Object { $_ -notmatch ('"subagent":"' + $kid + '"') })
  [IO.File]::WriteAllText($messages, ($keep -join "`n") + "`n", $utf8)
  & $exe -NoProfile -ExecutionPolicy Bypass -File $hook -Backfill all | Out-Null
  $m = @(Rows $messages | Where-Object { $_.session_id -eq $sid3 })
  $got = @($m | ForEach-Object { "$($_.message_id) $($_.subagent)" }) -join ', '
  Check 'Codex subagent: -Backfill all reads the subagent the parent''s rollout names and puts the rows in order' ($got -ceq "pum-1 , amsg-34 $kid, kam-1 $kid, pam-1 ") $got

  # ---- Antigravity: its own hook input, the result and the messages read from its transcript -------------------------
  Write-Host 'Antigravity'
  $t0 = [DateTime]::UtcNow
  $cid = [Guid]::NewGuid().ToString()
  $logs = Join-Path $fakeHome ".gemini\antigravity-cli\brain\$cid\.system_generated\logs"
  New-Item -ItemType Directory -Force $logs | Out-Null
  $full = Join-Path $logs 'transcript_full.jsonl'
  $short = Join-Path $logs 'transcript.jsonl'
  function Step($i, $o) { $s = [ordered]@{ step_index = $i; created_at = (T $i) }; foreach ($k in $o.Keys) { $s[$k] = $o[$k] }; return (Line $s) }
  $agLong = ('compile line' + "`n") * 1000 + 'END-OF-AG-OUTPUT'
  $agSteps = @(
    (Step 0 ([ordered]@{ source = 'USER_EXPLICIT'; type = 'USER_INPUT'; status = 'DONE'; content = "<USER_REQUEST>`nAdd a lamp.`n</USER_REQUEST>`n<ADDITIONAL_METADATA>`nThe current local time is: now.`n</ADDITIONAL_METADATA>" })),
    (Step 1 ([ordered]@{ source = 'MODEL'; type = 'PLANNER_RESPONSE'; status = 'DONE'; model = 'model-g'; thinking = 'Look first.'; tool_calls = @([ordered]@{ name = 'run_command'; args = [ordered]@{ CommandLine = 'dir'; Cwd = $root } }) })),
    (Step 2 ([ordered]@{ source = 'MODEL'; type = 'GENERIC'; status = 'DONE'; content = "Command exited with code 0.`nEARLIER-AG" })),
    (Step 3 ([ordered]@{ source = 'MODEL'; type = 'PLANNER_RESPONSE'; status = 'DONE'; model = 'model-g'; content = 'Writing the lamp.'
        tool_calls = @([ordered]@{ name = 'write_file'; args = [ordered]@{ Path = (Join-Path $cwd 'lamp.txt'); Content = 'lamp' } }, [ordered]@{ name = 'run_command'; args = [ordered]@{ CommandLine = 'build lamp' } }) }))
  )
  # as the hook of the first call of step 3 runs: its result is not in the transcript yet
  [IO.File]::WriteAllText($full, ($agSteps -join "`n") + "`n", $utf8)
  [IO.File]::WriteAllText($short, ($agSteps -join "`n") + "`n", $utf8)
  function Invoke-AgHook([string]$Json, [string[]]$More = @()) {
    $out = $Json | & $exe -NoProfile -ExecutionPolicy Bypass -File $hook -Agent antigravity @More
    if ($LASTEXITCODE -ne 0) { throw "the hook exited $LASTEXITCODE (antigravity $($More -join ' '))" }
    return (@($out) -join '')
  }
  function AgCall([int]$Step, [string]$Name, $ArgsObj) {
    return (Line ([ordered]@{ conversationId = $cid; workspacePaths = @($root); transcriptPath = $short; artifactDirectoryPath = (Split-Path (Split-Path $logs)); modelName = 'model-g'
          lastUserInput = 'Add a lamp.'; hookEventName = 'PostToolUse'; cwd = $root; stepIdx = $Step; error = ''; toolCall = [ordered]@{ id = "toolu_ag_$Step"; name = $Name; args = $ArgsObj } }))
  }
  $before = @(Rows $actions).Count
  $said = Invoke-AgHook (AgCall 4 'write_file' ([ordered]@{ Path = (Join-Path $cwd 'lamp.txt'); Content = 'lamp' }))
  $a = @(Rows $actions | Select-Object -Skip $before)
  Check 'Antigravity: the hook answers {} on stdout' ($said -ceq '{}') $said
  Check 'Antigravity: a call naming the game maps the session; the call the transcript completed is written, the hook''s own waits' ($a.Count -eq 1 -and $a[0].tool_use_id -eq "${cid}:2" -and $a[0].status -eq 'from_transcript' -and $a[0].tool -eq 'run_command' -and $a[0].agent -eq 'antigravity' -and $a[0].session_id -eq $cid -and ([string]$a[0].response).Contains('EARLIER-AG') -and $a[0].input.CommandLine -eq 'dir') "rows: $($a.Count)"
  # both results reach the transcript (the compact copy cuts the long one); the next call's hook writes both rows
  [IO.File]::AppendAllText($full, (Step 4 ([ordered]@{ source = 'MODEL'; type = 'GENERIC'; status = 'DONE'; content = $agLong })) + "`n" + (Step 5 ([ordered]@{ source = 'MODEL'; type = 'GENERIC'; status = 'ERROR'; content = 'Command exited with code 1. LAMP-FAILED' })) + "`n", $utf8)
  [IO.File]::AppendAllText($short, (Step 4 ([ordered]@{ source = 'MODEL'; type = 'GENERIC'; status = 'DONE'; content = 'compile line'; truncated_fields = @('content') })) + "`n", $utf8)
  [void](Invoke-AgHook (AgCall 5 'run_command' ([ordered]@{ CommandLine = 'build lamp' })))
  $a = @(Rows $actions | Select-Object -Skip $before)
  Check 'Antigravity: the waiting call''s row holds the whole result, read from transcript_full.jsonl' ($a.Count -eq 3 -and $a[1].tool_use_id -eq "${cid}:4" -and $a[1].tool -eq 'write_file' -and ([string]$a[1].response).Contains('END-OF-AG-OUTPUT') -and $a[1].input.Content -eq 'lamp' -and $a[1].event -eq 'PostToolUse') "rows: $($a.Count)"
  Check 'Antigravity: a step with status ERROR is the row''s error' ($a.Count -eq 3 -and $a[2].tool_use_id -eq "${cid}:5" -and ([string]$a[2].error).Contains('LAMP-FAILED') -and ([string]$a[2].response).Contains('LAMP-FAILED'))
  [void](Invoke-AgHook (AgCall 5 'run_command' ([ordered]@{ CommandLine = 'build lamp' })))
  Check 'Antigravity: a hook call with nothing new writes nothing' (@(Rows $actions | Select-Object -Skip $before).Count -eq 3)
  # the end of the turn: a reply without tool calls is the last step
  [IO.File]::AppendAllText($full, (Step 6 ([ordered]@{ source = 'MODEL'; type = 'PLANNER_RESPONSE'; status = 'DONE'; model = 'model-g'; content = 'The lamp is in.' })) + "`n", $utf8)
  $agStop = Line ([ordered]@{ conversationId = $cid; transcriptPath = $short; cwd = $root; hookEventName = 'Stop'; executionNum = 0; terminationReason = 'NO_TOOL_CALL'; fullyIdle = $true; continuationActive = $false })
  $said = Invoke-AgHook $agStop @('-Stop')
  $m = @(Rows $messages | Where-Object { $_.session_id -eq $cid })
  $got = @($m | ForEach-Object { "$($_.role) $($_.message_id)" }) -join ', '
  Check 'Antigravity: prompt, reasoning, replies, in the transcript''s order' ($said -ceq '{}' -and $got -ceq "user ${cid}:0, thinking ${cid}:1:thinking, assistant ${cid}:3, assistant ${cid}:6") $got
  Check 'Antigravity: the prompt is the text the person typed, without what Antigravity added' ($m.Count -eq 4 -and $m[0].text -ceq 'Add a lamp.' -and $m[1].text -ceq 'Look first.' -and $m[1].model -eq 'model-g' -and $m[3].agent -eq 'antigravity') ([string]$m[0].text)
  $stopRow = @(Rows $actions)[-1]
  Check 'Antigravity: Stop writes its row, and no call twice' ($stopRow.event -eq 'Stop' -and $stopRow.session_id -eq $cid -and $stopRow.agent -eq 'antigravity' -and @(Rows $actions | Select-Object -Skip $before).Count -eq 4)
  [void](Invoke-AgHook $agStop @('-Stop'))
  Check 'Antigravity: a second Stop writes no message twice' (@(Rows $messages | Where-Object { $_.session_id -eq $cid }).Count -eq 4)
  # a conversation that never names a game is not recorded, and the hook still answers
  $n = @(Rows $actions).Count
  $other = Line ([ordered]@{ conversationId = [Guid]::NewGuid().ToString(); transcriptPath = $short; cwd = $tmp; hookEventName = 'PostToolUse'; stepIdx = 2; toolCall = [ordered]@{ id = 'x'; name = 'run_command'; args = [ordered]@{ CommandLine = 'dir' } } })
  $said = Invoke-AgHook $other
  Check 'Antigravity: a conversation that names no game writes nothing' ($said -ceq '{}' -and @(Rows $actions).Count -eq $n)
  $env:GF_NO_RECORDING = '1'
  $said = Invoke-AgHook (AgCall 5 'run_command' ([ordered]@{ CommandLine = 'build lamp' }))
  $env:GF_NO_RECORDING = $null
  Check 'Antigravity: with GF_NO_RECORDING nothing is written and the hook still answers' ($said -ceq '{}' -and @(Rows $actions).Count -eq $n)

  # ---- config.toml: the settings that make Codex show and save its reasoning summaries ------------------------------
  Write-Host 'Codex config.toml'
  . (Join-Path $machine 'lib\codex-hooks.ps1')
  $want = $script:GFCodexSummary
  function Off([string]$Path) { $top = Get-GFCodexTopLevel $Path; return @($want.Keys | Where-Object { $top[$_] -ne $want[$_] }) }
  $toml = Join-Path $tmp 'config.toml'
  [IO.File]::WriteAllText($toml, "model = `"m`"`n`n[features]`nx = true`n", $utf8)
  Check 'not set: both settings are off' (@(Off $toml).Count -eq 2)
  Set-GFCodexTopLevel $toml $want
  $text = [IO.File]::ReadAllText($toml, $utf8)
  Check 'set: both before every table, every other line as it was' (@(Off $toml).Count -eq 0 -and $text.StartsWith("model = `"m`"`n") -and $text.EndsWith("[features]`nx = true`n") -and $text.IndexOf('model_reasoning_summary') -lt $text.IndexOf('[features]') -and $text.IndexOf('hide_agent_reasoning') -lt $text.IndexOf('[features]')) $text
  Set-GFCodexTopLevel $toml $want
  Check 'set again: nothing changes' ([IO.File]::ReadAllText($toml, $utf8) -ceq $text)
  $profile1 = "[profiles.quiet]`nmodel_reasoning_summary = `"none`"`n"
  [IO.File]::WriteAllText($toml, "model_reasoning_summary = `"none`"`nhide_agent_reasoning = true`n" + $profile1, $utf8)
  Check '"none" and hidden: off' (@(Off $toml).Count -eq 2)
  Set-GFCodexTopLevel $toml $want
  $text = [IO.File]::ReadAllText($toml, $utf8)
  Check 'both replaced where they stood; a profile is not edited' (@(Off $toml).Count -eq 0 -and $text.EndsWith($profile1) -and ([regex]::Matches($text, 'model_reasoning_summary')).Count -eq 2) $text
  [IO.File]::WriteAllText($toml, $profile1, $utf8)
  Check 'a key inside a table is not the top-level key' (@(Off $toml).Count -eq 2)
  Set-GFCodexTopLevel $toml $want
  Check 'then set before the table' (@(Off $toml).Count -eq 0 -and [IO.File]::ReadAllText($toml, $utf8).EndsWith($profile1))
} finally {
  foreach ($k in $saved.Keys) { [Environment]::SetEnvironmentVariable($k, $saved[$k]) }
  Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host ''
if ($fails.Count) { Write-Host "FAIL  $($fails.Count) check(s): $($fails -join '; ')" -ForegroundColor Red } else { Write-Host 'PASS  the recording hook and the reasoning-summary settings' }
exit $fails.Count
