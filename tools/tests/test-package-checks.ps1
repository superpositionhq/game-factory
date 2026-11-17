<#
.SYNOPSIS
  Exercise package-dataset.ps1's actual writer-check invocation without packaging a game.
  Runs a native Python fixture through the AST-extracted command block so stderr never
  enters JSON stdout; also checks the temporary opt-out and pinned tasks ref forwarding.
.EXAMPLE
  pwsh -NoProfile -File tools/tests/test-package-checks.ps1
#>
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
$tools = Split-Path -Parent $PSScriptRoot
$source = Join-Path $tools 'package-dataset.ps1'
$tokens = $null; $parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($source, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$assignments = @($ast.FindAll({ param($node) $node -is [Management.Automation.Language.AssignmentStatementAst] }, $true))
$first = @($assignments | Where-Object { $_.Left.Extent.Text -eq '$checkArgs' -and $_.Operator -eq 'Equals' })
$last = @($assignments | Where-Object { $_.Left.Extent.Text -eq '$checkMetadata' -and $_.Right.Extent.Text -match 'ConvertFrom-Json' })
if ($first.Count -ne 1 -or $last.Count -ne 1) { throw 'cannot identify the writer-check invocation block' }
$text = [IO.File]::ReadAllText($source)
$block = $text.Substring($first[0].Extent.StartOffset, $last[0].Extent.EndOffset - $first[0].Extent.StartOffset)
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction Stop }
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('gf-package-checks-test-' + [guid]::NewGuid().ToString('N'))
$utf8 = New-Object Text.UTF8Encoding($false)
$count = 0
function Check([string]$Name, $Ok) {
    if (-not $Ok) { throw "FAIL $Name" }
    $script:count++
    Write-Host "ok $Name"
}
try {
    New-Item -ItemType Directory $tmp | Out-Null
    $fixture = @'
import json
import sys

if "fail" in sys.argv:
    print("not JSON: failure must be handled before parsing stdout")
    print("checks fixture: failure detail", file=sys.stderr)
    sys.exit(2)
print(json.dumps({"last_commit_at": {"repair-hud": "2026-11-17T10:00:00+00:00"},
                  "arguments": sys.argv[1:]}, indent=2))
if "warning" in sys.argv or "--no-writer-checks" in sys.argv:
    print("warning: checks fixture warning", file=sys.stderr)
'@
    [IO.File]::WriteAllText((Join-Path $tmp 'package-checks.py'), $fixture, $utf8)
    $wrapper = @'
param([string]$Python, [string]$Mode = 'quiet', [switch]$NoWriterChecks, [string]$TasksCommit = '')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
function Get-Prop($Object, [string]$Name) { return $Object.$Name }
$py = $Python; $info = [pscustomobject]@{ Dir = $Mode }
$tasksDir = 'split tasks'; $checksDir = 'writer checks'; $mapTsv = 'map with spaces.tsv'
$man = [pscustomobject]@{ tasks_commit = $TasksCommit }
$checkMetadata = $null; $failure = $null
try {
'@
    $wrapper += "`n" + $block + "`n" + @'
} catch { $failure = $_.Exception.Message }
[pscustomobject]@{
    Metadata = $checkMetadata
    Failure = $failure
    Preference = $ErrorActionPreference
    Stderr = $checksStderr
    TempRemoved = -not (Test-Path -LiteralPath $checksErrPath)
}
'@
    $script = Join-Path $tmp 'invoke-checks.ps1'
    [IO.File]::WriteAllText($script, $wrapper, $utf8)

    $records = @(& $script -Python $py.Source)
    $r = $records[0]
    Check 'default ships writer checks' ($records.Count -eq 1 -and -not $r.Failure -and $r.Metadata.arguments -notcontains '--no-writer-checks')
    Check 'arguments with spaces stay intact' ($r.Metadata.arguments -contains 'split tasks' -and $r.Metadata.arguments -contains 'map with spaces.tsv')
    Check 'quiet stdout parses as JSON' ($r.Metadata.last_commit_at.'repair-hud' -eq '2026-11-17T10:00:00+00:00' -and -not $r.Stderr)
    Check 'success restores error preference and removes stderr file' ($r.Preference -eq 'Stop' -and $r.TempRemoved)

    $records = @(& $script -Python $py.Source -Mode warning -TasksCommit ('a' * 40) 6>&1)
    $messages = @($records | Where-Object { $_ -is [Management.Automation.InformationRecord] })
    $r = @($records | Where-Object { $_ -isnot [Management.Automation.InformationRecord] })[0]
    Check 'stderr warning leaves JSON stdout clean' (-not $r.Failure -and $r.Metadata.last_commit_at.'repair-hud' -eq '2026-11-17T10:00:00+00:00')
    Check 'stderr warning is shown once' ($messages.Count -eq 1 -and $messages[0].ToString() -eq 'warning: checks fixture warning')
    $argsSent = @($r.Metadata.arguments)
    Check 'pinned tasks ref is forwarded' ($argsSent -contains '--tasks-ref' -and $argsSent[-1] -eq ('a' * 40))

    $records = @(& $script -Python $py.Source -NoWriterChecks 6>&1)
    $messages = @($records | Where-Object { $_ -is [Management.Automation.InformationRecord] })
    $r = @($records | Where-Object { $_ -isnot [Management.Automation.InformationRecord] })[0]
    Check 'opt-out is forwarded with one warning' (-not $r.Failure -and $r.Metadata.arguments -contains '--no-writer-checks' -and $messages.Count -eq 1)

    $r = & $script -Python $py.Source -Mode fail
    Check 'failure includes exit code and separate stderr' ($r.Failure -match 'exit 2' -and $r.Failure -match 'checks fixture: failure detail')
    Check 'failure is handled before parsing non-JSON stdout' ($null -eq $r.Metadata -and $r.Failure -notmatch 'ConvertFrom-Json')
    Check 'failure restores error preference and removes stderr file' ($r.Preference -eq 'Stop' -and $r.TempRemoved)
} finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host "PASS $count checks"
