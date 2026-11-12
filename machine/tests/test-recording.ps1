<#
.SYNOPSIS
  The recording hook (record-action.ps1) and the agents' reasoning-summary settings (lib\codex-hooks.ps1), run on
  made-up transcripts in the shapes Claude Code and Codex write, in a scratch folder under %TEMP%. Nothing of this
  machine's recording, agent settings or games is read or written.
.DESCRIPTION
  Checks: a tool call's whole output in actions.jsonl (live rows and rows imported from the transcript), the cut at
  1,000,000 characters with "response_truncated" and "response_chars", the marker in place of a picture's base64, a
  long command output read from
  the file Claude Code saved it to; the reasoning summaries as role "thinking" rows of messages.jsonl in the
  transcript's order (Claude Code thinking blocks, Codex Reasoning items, a summary saved without text as "redacted",
  Codex raw_content kept when it is text), written once; -Backfill adding them to a session recorded before they were and
  putting its rows back in order; and config.toml's reasoning-summary settings read and set without touching other lines.
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
