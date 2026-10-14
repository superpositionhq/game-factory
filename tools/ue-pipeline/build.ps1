<#
.SYNOPSIS
  Build (and optionally package and smoke-test) one game at a commit. See docs/ue-pipeline.md.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File build.ps1 stealth -Package -Smoke
  powershell -ExecutionPolicy Bypass -File build.ps1 rally-racer -Commit milestone/autoplay-1 -Package

  Builds from a private clone (C:\UEB\src\<game>: outside the user profile, so no user name is compiled into the exe)
  of the committed tree, never from the game's working copy:
  the game session's editor keeps its DLLs and half-edited files to itself. Uncommitted changes are not built.
  Output: builds\<game>\<short-sha>\Windows\<Project>.exe, build_info.json, logs\. One row per run in
  .recording\<game>\builds.jsonl. Holds the pipeline lock (one heavy job at a time).
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [string]$Commit = 'HEAD',
    [switch]$Package,
    [switch]$Smoke,
    [switch]$Force,
    [ValidateSet('auto', 'Development', 'Shipping')][string]$Config = 'auto'
)

. (Join-Path $PSScriptRoot 'common.ps1')

$info = Get-GameInfo $Game
$commandLine = "build.ps1 $Game -Commit $Commit" + $(if ($Package) { ' -Package' } else { '' }) + $(if ($Smoke) { ' -Smoke' } else { '' }) + $(if ($Force) { ' -Force' } else { '' })

$sha = (Invoke-Git $info.Dir @('rev-parse', '--verify', "$Commit^{commit}")).Trim()
$short = $sha.Substring(0, 8)
# Packaged config. Shipping compiles out UE's trace runtime, whose TCP listener (0.0.0.0, Development/Test builds, no
# runtime switch in 5.3) makes Windows Firewall prompt for every new exe path. Shipping also ignores -ini: overrides, so
# 'auto' picks it only when the game sets bAllowHighDPIInGameMode=True in Config/DefaultEngine.ini (record.ps1 needs that).
if ($Config -eq 'auto') {
    $engineIni = (Invoke-Git $info.Dir @('show', "${sha}:Config/DefaultEngine.ini") -AllowFail) -join "`n"
    $Config = if ($engineIni -match '(?im)^\s*bAllowHighDPIInGameMode\s*=\s*True') { 'Shipping' } else { 'Development' }
    if ($Config -eq 'Development') { Write-Step "no bAllowHighDPIInGameMode=True in Config/DefaultEngine.ini: packaging Development (Windows Firewall will prompt once per new exe path)" }
}
$outDir = Join-Path (Join-Path $BuildsRoot $Game) $(if ($Config -eq 'Shipping') { "$short-shipping" } else { $short })
$logDir = Join-Path $outDir 'logs'
$exePath = Join-Path $outDir "Windows\$($info.ProjectName).exe"
$buildInfoPath = Join-Path $outDir 'build_info.json'

$existing = Read-JsonFile $buildInfoPath
# A build made before store-content hydration existed is stale if the game has git-ignored Content dirs.
if ($existing -and $existing.PSObject.Properties.Name -notcontains 'hydrated_content' -and
    @(Invoke-Git $info.Dir @('ls-files', '--others', '--ignored', '--exclude-standard', '--directory', '--', 'Content') -AllowFail | Where-Object { $_ -and $_.Trim() }).Count) {
    Write-Step "$Game $short was built before store-content hydration: rebuilding"
    $existing = $null
}
if (-not $Force -and $existing -and $existing.status -eq 'ok' -and (-not $Package -or $existing.packaged) -and (-not $Smoke -or $existing.smoke.status -ne 'not_run')) {
    Write-Step "$Game $short already built ($outDir); use -Force to rebuild"
    return $existing
}

Set-BelowNormalPriority
# Build tools (UBT, the linker, UAT) write temp files under %TEMP% and the linker records that path in the PDB:
# keep them outside the user profile too.
New-Item -ItemType Directory -Force $BuildTempRoot | Out-Null
$savedTemp = $env:TEMP; $savedTmp = $env:TMP
$env:TEMP = $BuildTempRoot; $env:TMP = $BuildTempRoot
Enter-PipelineLock "build $Game $short" -Game $Game
$start = Get-Date
$steps = New-Object System.Collections.ArrayList
$failure = ''
$autoplayVersion = $null
$hydration = New-Object System.Collections.ArrayList
$missingAssets = $null
$missingByPipeline = New-Object System.Collections.ArrayList
$missingInGame = New-Object System.Collections.ArrayList
$cookedBytes = $null
$leakScan = $null
$freeCommitGB = $null
$maxParallelActions = $null
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
    $src = Join-Path $SrcRoot $Game
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

    # Store content kept out of git on purpose (Fab/Marketplace packs, generated meshes): copy every working-tree
    # directory under Content/ that is git-ignored AT THE COMMIT BEING BUILT (asked of the clone, which has that
    # commit's .gitignore and index) into the clone. Asking the working tree instead misses content that a later commit
    # started tracking (a game that later moved its packs into LFS cooked without them). Without this
    # the build has no art. robocopy /MIR is incremental (the clone keeps ignored dirs between builds).
    $contentRoot = Join-Path $info.Dir 'Content'
    $candidates = @(Get-ChildItem $contentRoot -Recurse -Directory -ErrorAction SilentlyContinue | ForEach-Object { 'Content/' + $_.FullName.Substring($contentRoot.Length + 1).Replace('\', '/') + '/' })
    $ignoredAll = New-Object System.Collections.ArrayList
    for ($k = 0; $k -lt $candidates.Count; $k += 100) {   # as arguments (stdin from PowerShell adds CR), in batches
        $batch = $candidates[$k..([math]::Min($k + 99, $candidates.Count - 1))]
        foreach ($line in @(Invoke-Git $src (@('-c', 'core.quotepath=false', 'check-ignore', '--') + $batch) -AllowFail)) { if ("$line".Trim().StartsWith('Content/')) { [void]$ignoredAll.Add("$line".Trim()) } }
    }
    $ignored = @($ignoredAll | Sort-Object -Unique | Where-Object { $d = $_; -not @($ignoredAll | Where-Object { $_ -ne $d -and $d.StartsWith($_) }).Count })
    foreach ($rel in $ignored) {
        $rel = $rel.Trim().TrimEnd('/')
        $from = Join-Path $info.Dir $rel; $to = Join-Path $src $rel
        if (-not (Test-Path $from)) { continue }
        if (-not (Test-Path $from -PathType Container)) { Copy-Item -Force $from $to; continue }
        & robocopy.exe $from $to /MIR /NJH /NJS /NP /NFL /NDL /R:2 /W:2 | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "hydrating $rel failed (robocopy $LASTEXITCODE)" }
        $files = @(Get-ChildItem $to -Recurse -File -ErrorAction SilentlyContinue)
        $bytes = 0; foreach ($f in $files) { $bytes += $f.Length }
        [void]$hydration.Add([ordered]@{ dir = $rel; files = $files.Count; bytes = $bytes })
    }
    if ($hydration.Count) {
        $totalMB = [math]::Round((($hydration | ForEach-Object { $_.bytes }) | Measure-Object -Sum).Sum / 1MB, 1)
        Write-Step "hydrated $($hydration.Count) git-ignored Content dirs from the working tree ($totalMB MB): $(($hydration | ForEach-Object { $_.dir }) -join ', ')"
    }
    # Which AutoPlay drop-in version the game ships (record.ps1 picks the matching flags).
    $apHeader = Get-ChildItem (Join-Path $src 'Source') -Recurse -Filter AutoPlaySubsystem.h -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($apHeader -and ((Get-Content $apHeader.FullName -Raw) -match 'ContractVersion\s*=\s*(\d+)')) { $autoplayVersion = [int]$matches[1] }

    $uproject = Join-Path $src $info.UProjectName
    # The game's own engine (its EngineAssociation): games made on an older UE keep building on it.
    $script:EngineRoot = Get-GFEngine $uproject $GFConfig
    Write-Step "engine $EngineRoot"
    $editorTarget = Find-Target $src 'Editor'
    $gameTarget = Find-Target $src 'Game'
    if (-not $editorTarget -or -not $gameTarget) { throw "Editor/Game Target.cs not found under $src\Source" }

    # Compile parallelism: every cl.exe with a PCH reserves a large block of commit. When the machine's free commit is
    # low (other sessions' editors and games, a leaking service), parallel compiles fail with C3859 "Failed to create
    # virtual memory for PCH" / C1076 (seen with 92 % of the commit limit in use): below a quarter of the commit limit
    # free, cap UBT's actions.
    function Get-UbtParallelArg {
        $os = Get-CimInstance Win32_OperatingSystem
        $freeGB = [math]::Round($os.FreeVirtualMemory / 1MB, 1)   # KB -> GB
        $floorGB = [math]::Round($os.TotalVirtualMemorySize / 1MB / 4, 1)
        $script:freeCommitGB = $freeGB
        if ($freeGB -lt $floorGB) { $script:maxParallelActions = 4; Write-Step "free commit $freeGB GB (< $floorGB, a quarter of the limit): UBT -MaxParallelActions=4"; return ' -MaxParallelActions=4' }
        return ''
    }

    # ---- 1. editor target ----
    $par = Get-UbtParallelArg
    $r = Invoke-Step 'build-editor' (Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat') `
        "$editorTarget Win64 Development -Project=`"$uproject`" -WaitMutex -NoHotReloadFromIDE$par"
    if ($r.exit_code -ne 0) { throw 'editor build failed' }

    # ---- 2. package ----
    if ($Package) {
        # -WaitMutex: BuildCookRun's own UBT call otherwise fails at once ("A conflicting instance of UnrealBuildTool is
        # already running") while another session's UBT runs. If it still happens
        # (e.g. a UBT that ignores the mutex), the package step is retried once.
        foreach ($attempt in 1, 2) {
            $par = Get-UbtParallelArg
            $ubtArgs = " -ubtargs=`"-WaitMutex$par`""
            $r = Invoke-Step $(if ($attempt -eq 1) { 'package' } else { 'package-retry' }) (Join-Path $EngineRoot 'Engine\Build\BatchFiles\RunUAT.bat') `
                ("-WaitForUATMutex BuildCookRun -project=`"$uproject`" -target=$gameTarget -noP4 -platform=Win64 -clientconfig=$Config " +
                 "-build -cook -stage -pak -archive -archivedirectory=`"$outDir`" -nocompileeditor -unattended -utf8output$ubtArgs")
            if ($r.exit_code -eq 0 -or $attempt -eq 2) { break }
            if (-not (Select-String -Path $r.log_path -SimpleMatch 'A conflicting instance of UnrealBuildTool is already running' -Quiet)) { break }
            $r['retried'] = $true   # kept in steps[] for the record; not the build's failing step
            Write-Step 'package: another UnrealBuildTool was running; retrying the package step once'
        }
        if ($r.exit_code -ne 0) { throw 'package failed' }
        if (-not (Test-Path $exePath)) { throw "package succeeded but $exePath is missing" }
        # Missing game assets in the cook (e.g. store content not present) must fail the build, not ship an empty game.
        $missingPattern = '(?i)(Failed to load|Unable to load package|Couldn.t find file|ImportFailed|Missing import|Can.t find file).{0,200}/Game/'
        $missingLines = @(Select-String -Path $r.log_path -Pattern $missingPattern -ErrorAction SilentlyContinue | ForEach-Object { $_.Line.Trim() })
        $missingAssets = $missingLines.Count
        # Each missing package: if the game's working tree has it, the pipeline lost it (fail); if the game lacks it too,
        # it is a broken reference in the game/store pack itself (the game's own build has the same hole): warn, record.
        $missingPkgs = @($missingLines | ForEach-Object { [regex]::Matches($_, "/Game/[^'`"\s:]+") | ForEach-Object { $_.Value.TrimEnd('.', ',') } } | Sort-Object -Unique)
        foreach ($pkg in $missingPkgs) {
            $rel = 'Content\' + $pkg.Substring(6).Split('.')[0].Replace('/', '\')
            $inGame = (Test-Path -LiteralPath (Join-Path $info.Dir "$rel.uasset")) -or (Test-Path -LiteralPath (Join-Path $info.Dir "$rel.umap"))
            if ($inGame) { [void]$missingByPipeline.Add($pkg) } else { [void]$missingInGame.Add($pkg) }
        }
        $paks = @(Get-ChildItem (Join-Path $outDir 'Windows') -Recurse -File -Include *.pak, *.ucas, *.utoc -ErrorAction SilentlyContinue)
        $cookedBytes = 0; foreach ($f in $paks) { $cookedBytes += $f.Length }
        Write-Step ("cooked content {0:N1} MB; missing-asset lines in the cook log: {1} ({2} packages the game has but the build lost, {3} missing in the game itself)" -f ($cookedBytes / 1MB), $missingAssets, $missingByPipeline.Count, $missingInGame.Count)
        if ($missingInGame.Count) { Write-Step "WARNING: broken references in the game's own content (its own build has them too): $($missingInGame -join ', ')" }
        if ($missingByPipeline.Count -gt 0) {
            $failure = "cook is missing $($missingByPipeline.Count) packages that exist in the game's working tree: $(($missingByPipeline | Select-Object -First 5) -join ', ')"
            throw $failure
        }
        # Strings that must not ship: the user name (compiled-in source/PDB paths) and $ForbiddenNamePatterns (common.ps1).
        # Recorded and warned about; recording still works, but such a build must not be handed out.
        $leakHits = @(Find-LeakedStrings (Join-Path $outDir 'Windows') @($UserNamePatterns + $ForbiddenNamePatterns))
        $leakScan = [ordered]@{ scanned = 'Windows\'; hits = @($leakHits | ForEach-Object { [ordered]@{ file = $_.file; pattern = $_.pattern; count = $_.count; example = $_.example } }) }
        if ($leakHits.Count) { Write-Step "WARNING: shipped files contain names that must not ship: $(($leakHits | ForEach-Object { "$($_.file) ($($_.pattern) x$($_.count))" }) -join '; ')" }
        else { Write-Step 'leak scan: no user name or forbidden names in the packaged files' }
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
    $env:TEMP = $savedTemp; $env:TMP = $savedTmp
    Exit-PipelineLock
}

$end = Get-Date
$failedStep = $steps | Where-Object { $_.exit_code -ne 0 -and -not $_.Contains('retried') } | Select-Object -First 1
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
    hydrated_content = @($hydration)
    missing_asset_lines = $missingAssets
    missing_assets_lost_by_build = @($missingByPipeline)
    missing_assets_in_game = @($missingInGame)
    cooked_content_mb = $(if ($null -ne $cookedBytes) { [math]::Round($cookedBytes / 1MB, 1) } else { $null })
    leak_scan = $leakScan
    free_commit_gb = $freeCommitGB
    max_parallel_actions = $maxParallelActions
    engine = $EngineRoot
    config = $Config
    steps = @($steps)
}
Add-JsonLine (Join-Path $info.LogDir 'builds.jsonl') $row
if ($status -eq 'ok' -and $Package) { Write-JsonFile $buildInfoPath $row }   # describes the packaged output only
Write-Step ("{0} {1}: {2} in {3}s" -f $Game, $short, $status, $row.duration_s)
$row
if ($status -ne 'ok') { exit 1 }
