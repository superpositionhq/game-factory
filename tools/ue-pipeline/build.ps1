<#
.SYNOPSIS
  Build (and optionally package and smoke-test) one game at a commit. See docs/ue-pipeline.md.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File build.ps1 stealth -Package -Smoke
  powershell -ExecutionPolicy Bypass -File build.ps1 rally-racer -Commit milestone/autoplay-1 -Package

  Builds from a private clone (builds\_src\<game>) of the committed tree, never from the game's working copy:
  the game session's editor keeps its DLLs and half-edited files to itself. Uncommitted changes are not built.
  Output: builds\<game>\<short-sha>\Windows\<Project>.exe, build_info.json, logs\. One row per run in
  .recording\<game>\builds.jsonl. Holds the pipeline lock (one heavy job at a time).
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [string]$Commit = 'HEAD',
    [switch]$Package,
    [switch]$Smoke,
    [switch]$Force
)

. (Join-Path $PSScriptRoot 'common.ps1')

$info = Get-GameInfo $Game
$commandLine = "build.ps1 $Game -Commit $Commit" + $(if ($Package) { ' -Package' } else { '' }) + $(if ($Smoke) { ' -Smoke' } else { '' }) + $(if ($Force) { ' -Force' } else { '' })

$sha = (Invoke-Git $info.Dir @('rev-parse', '--verify', "$Commit^{commit}")).Trim()
$short = $sha.Substring(0, 8)
$outDir = Join-Path (Join-Path $BuildsRoot $Game) $short
$logDir = Join-Path $outDir 'logs'
$exePath = Join-Path $outDir "Windows\$($info.ProjectName).exe"
$buildInfoPath = Join-Path $outDir 'build_info.json'

$existing = Read-JsonFile $buildInfoPath
if (-not $Force -and $existing -and $existing.status -eq 'ok' -and (-not $Package -or $existing.packaged) -and (-not $Smoke -or $existing.smoke.status -ne 'not_run')) {
    Write-Step "$Game $short already built ($outDir); use -Force to rebuild"
    return $existing
}

Set-BelowNormalPriority
Enter-PipelineLock "build $Game $short"
$start = Get-Date
$steps = New-Object System.Collections.ArrayList
$failure = ''
$autoplayVersion = $null
$status = 'ok'
$smokeResult = [ordered]@{ status = 'not_run'; note = '' }
$stamp = $start.ToString('yyyyMMdd-HHmmss')

function Invoke-Step([string]$Name, [string]$Exe, [string]$Arguments, [string]$WorkDir = $null) {
    $log = Join-Path $logDir "$stamp-$Name.log"
    Write-Step "$Name ..."
    $t0 = Get-Date
    $code = Invoke-Logged $Exe $Arguments $log $WorkDir "pipeline $Game $short $Name"
    $t1 = Get-Date
    $row = [ordered]@{
        name = $Name; command = "`"$Exe`" $Arguments"; start = $t0.ToString('o'); end = $t1.ToString('o')
        duration_s = [math]::Round(($t1 - $t0).TotalSeconds, 1); exit_code = $code; log_path = $log
        error_excerpt = $(if ($code -ne 0) { Get-ErrorExcerpt $log } else { '' })
    }
    [void]$steps.Add($row)
    Write-Step ("{0} exit {1} in {2}s" -f $Name, $code, $row.duration_s)
    return $row
}

try {
    New-Item -ItemType Directory -Force $logDir | Out-Null

    # ---- source: private clone at the exact commit, LFS files copied from the game's own LFS store ----
    $src = Join-Path (Join-Path $BuildsRoot '_src') $Game
    $env:GIT_LFS_SKIP_SMUDGE = '1'
    if (-not (Test-Path (Join-Path $src '.git'))) {
        Write-Step "cloning $($info.Dir) -> $src"
        New-Item -ItemType Directory -Force (Split-Path $src) | Out-Null
        Invoke-Git $WorkRoot @('clone', '--quiet', '--no-checkout', '--local', $info.Dir, $src) | Out-Null
    }
    Invoke-Git $src @('fetch', '--quiet', '--force', '--tags', 'origin', '+refs/heads/*:refs/remotes/origin/*') | Out-Null
    Invoke-Git $src @('-c', 'advice.detachedHead=false', 'checkout', '--quiet', '--force', $sha) | Out-Null
    Invoke-Git $src @('clean', '-ffdq') | Out-Null
    $commonDir = (Invoke-Git $info.Dir @('rev-parse', '--git-common-dir')).Trim()
    if (-not [System.IO.Path]::IsPathRooted($commonDir)) { $commonDir = Join-Path $info.Dir $commonDir }
    $lfsStore = Join-Path $commonDir 'lfs\objects'
    $missing = New-Object System.Collections.ArrayList
    $copied = 0
    $lfsList = @(Invoke-Git $src @('lfs', 'ls-files', '-l') -AllowFail)
    foreach ($line in $lfsList) {
        if ($line.Length -lt 68) { continue }
        $oid = $line.Substring(0, 64); $rel = $line.Substring(67)
        $target = Join-Path $src $rel
        $item = Get-Item -LiteralPath $target -ErrorAction SilentlyContinue
        if ($item -and $item.Length -lt 1024 -and ((Get-Content -LiteralPath $target -TotalCount 1) -like 'version https://git-lfs*')) {
            $obj = Join-Path $lfsStore ("{0}\{1}\{2}" -f $oid.Substring(0, 2), $oid.Substring(2, 2), $oid)
            if (Test-Path -LiteralPath $obj) { Copy-Item -LiteralPath $obj -Destination $target -Force; $copied++ }
            else { [void]$missing.Add($rel) }
        }
    }
    Remove-Item Env:\GIT_LFS_SKIP_SMUDGE
    if ($missing.Count -gt 0) { throw "LFS objects missing from $lfsStore for: $($missing -join ', ')" }
    Write-Step "source at $short in $src ($($lfsList.Count) LFS files, $copied copied)"
    # Which AutoPlay drop-in version the game ships (record.ps1 picks the matching flags).
    $apHeader = Get-ChildItem (Join-Path $src 'Source') -Recurse -Filter AutoPlaySubsystem.h -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($apHeader -and ((Get-Content $apHeader.FullName -Raw) -match 'ContractVersion\s*=\s*(\d+)')) { $autoplayVersion = [int]$matches[1] }

    $uproject = Join-Path $src $info.UProjectName
    $editorTarget = Find-Target $src 'Editor'
    $gameTarget = Find-Target $src 'Game'
    if (-not $editorTarget -or -not $gameTarget) { throw "Editor/Game Target.cs not found under $src\Source" }

    # ---- 1. editor target ----
    $r = Invoke-Step 'build-editor' (Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat') `
        "$editorTarget Win64 Development -Project=`"$uproject`" -WaitMutex -NoHotReloadFromIDE"
    if ($r.exit_code -ne 0) { throw 'editor build failed' }

    # ---- 2. package ----
    if ($Package) {
        $r = Invoke-Step 'package' (Join-Path $EngineRoot 'Engine\Build\BatchFiles\RunUAT.bat') `
            ("-WaitForUATMutex BuildCookRun -project=`"$uproject`" -target=$gameTarget -noP4 -platform=Win64 -clientconfig=Development " +
             "-build -cook -stage -pak -archive -archivedirectory=`"$outDir`" -nocompileeditor -unattended -utf8output")
        if ($r.exit_code -ne 0) { throw 'package failed' }
        if (-not (Test-Path $exePath)) { throw "package succeeded but $exePath is missing" }
    }

    # ---- 3. smoke test (only if the game defines <Project>.Smoke) ----
    if ($Smoke) {
        $testName = "$($info.ProjectName).Smoke"
        $defined = @(Get-ChildItem (Join-Path $src 'Source') -Recurse -Include *.cpp, *.h -File | Select-String -SimpleMatch "`"$testName" -List)
        if ($defined.Count -eq 0) {
            $smokeResult = [ordered]@{ status = 'skipped'; note = "no automation test named $testName* in Source/" }
            Write-Step "smoke skipped: $($smokeResult.note)"
        } else {
            $reportDir = Join-Path $logDir "$stamp-smoke-report"
            $r = Invoke-Step 'smoke' (Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe') `
                ("`"$uproject`" -ExecCmds=`"Automation RunTests $testName; Quit`" -TestExit=`"Automation Test Queue Empty`" " +
                 "-ReportExportPath=`"$reportDir`" -nullrhi -unattended -nopause -nosplash -nosound -stdout")
            $report = Read-JsonFile (Join-Path $reportDir 'index.json')
            if ($report -and $report.failed -eq 0 -and $report.succeeded -gt 0) {
                $smokeResult = [ordered]@{ status = 'passed'; note = "$($report.succeeded) passed"; report = $reportDir }
            } else {
                $note = if ($report) { "$($report.succeeded) passed, $($report.failed) failed" } else { "no report (exit $($r.exit_code))" }
                $smokeResult = [ordered]@{ status = 'failed'; note = $note; report = $reportDir }
                throw "smoke test failed: $note"
            }
        }
    }
} catch {
    $status = 'failed'
    $failure = $_.Exception.Message
    Write-Step "FAILED: $failure"
} finally {
    Remove-Item Env:\GIT_LFS_SKIP_SMUDGE -ErrorAction SilentlyContinue
    Exit-PipelineLock
}

$end = Get-Date
$failedStep = $steps | Where-Object { $_.exit_code -ne 0 } | Select-Object -First 1
$lastStep = $steps | Select-Object -Last 1
$subject = "$(Invoke-Git $info.Dir @('log', '-1', '--format=%s', $sha) -AllowFail)"
$commitTime = "$(Invoke-Git $info.Dir @('log', '-1', '--format=%cI', $sha) -AllowFail)"
$row = [ordered]@{
    schema = 'ue-build/1'   # neutral: build_info.json sits next to the game build
    game = $Game; project = $info.ProjectName
    commit = $sha; short_sha = $short; requested = $Commit; commit_subject = $subject; commit_time = $commitTime
    command = $commandLine
    start = $start.ToString('o'); end = $end.ToString('o'); duration_s = [math]::Round(($end - $start).TotalSeconds, 1)
    status = $status
    exit_code = $(if ($failedStep) { $failedStep.exit_code } elseif ($status -eq 'ok') { 0 } else { -1 })
    error_excerpt = $(if ($failedStep) { $failedStep.error_excerpt } elseif ($status -ne 'ok') { $failure } else { '' })
    log_path = $(if ($failedStep) { $failedStep.log_path } elseif ($lastStep) { $lastStep.log_path } else { $null })
    output_path = $(if ($status -eq 'ok' -and $Package) { $outDir } else { $null })
    exe_path = $(if ($status -eq 'ok' -and $Package) { $exePath } else { $null })
    packaged = [bool]($status -eq 'ok' -and $Package)
    smoke = $smokeResult
    autoplay_version = $autoplayVersion
    engine = $EngineRoot
    steps = @($steps)
}
Add-JsonLine (Join-Path $info.LogDir 'builds.jsonl') $row
if ($status -eq 'ok' -and $Package) { Write-JsonFile $buildInfoPath $row }   # describes the packaged output only
Write-Step ("{0} {1}: {2} in {3}s" -f $Game, $short, $status, $row.duration_s)
$row
if ($status -ne 'ok') { exit 1 }
