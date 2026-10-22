<#
.SYNOPSIS
  Create a new game repo from templates\ue-game (UE 5.7, the version its .uproject names): project skeleton, AutoPlay drop-in, Scripts\ue.ps1 (builds and
  editor-script runs through the heavy-job limiter), ReplayConfig.json ("live": true: the creation replay runs after
  every commit, docs/ue-replay.md section 3), first workflow.jsonl row, git + LFS, the post-commit hook (commit
  recorder + live replay), first commit, and the private GitHub repo <org>/game-<slug> (not pushed; <org> = -Org, else
  the config's github_org).
.DESCRIPTION
  Placeholders replaced in file names and contents: __PROJECT__ (module/project name), __SLUG__, __TITLE__,
  __DESCRIPTION__, __PROJECT_GUID__. tools\ue-pipeline\autoplay\AutoPlaySubsystem.h/.cpp are copied unchanged into
  Source\<Project>\AutoPlay\. The first workflow.jsonl row (op project.create) is written at the moment the project
  is created; the first commit names it. Pushing is left to the coordinator's go-ahead (commit-always skill).
  -Path is required: the absolute project folder <root>\games\<slug>, written out in the command (the recording hooks
  see the command text, so %GF_ROOT% or $env:GF_ROOT would not map the session). That call files this session under
  the game, and the hooks import its earlier calls from the transcript.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File <root>\game-factory\templates\new-game.ps1 -Slug <game> `
      -Path <root>\games\<game> -Title "<Title>" -Description "<one line>" -Reason "<why>"
  (<root> written out, e.g. C:\Users\<you>\Work)
#>
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[a-z0-9][a-z0-9-]*[a-z0-9]$')][string]$Slug,
    [string]$Path,                      # required: the absolute <root>\games\<slug>, written out
    [ValidatePattern('^[A-Z][A-Za-z0-9]{1,30}$')][string]$Project,   # default from the slug: island-survival -> IslandSurvival
    [string]$Title,                     # default from the slug: Island Survival
    [string]$Description = '',
    [string]$IdPrefix,                  # workflow row id prefix; default the slug's initials (is, rr, td) or its first two letters
    [string]$Reason = 'Create the project from the standard UE skeleton (Live Coding off, Shipping/HiDPI config, AutoPlay drop-in, LFS for every binary type)',
    [string]$Root,
    [string]$HooksDir,                  # default: the config's hooks_dir (machine/lib/gf-root.ps1 Get-GFHooksDir)
    [string]$Org,                       # default: the config's github_org (GF_ORG)
    [switch]$NoGitHub                   # skip creating the GitHub repo (tests, offline)
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
. (Join-Path $repo 'machine\lib\gf-root.ps1')
if (-not $Root) { $Root = Get-GFRoot }
if (-not $HooksDir) { $HooksDir = Get-GFHooksDir }
if (-not $Org) { $Org = Get-GFOrg }
if (-not $Org -and -not $NoGitHub) { throw 'no GitHub org: set github_org (machine/bootstrap.ps1 -Org <org>), pass -Org, or -NoGitHub' }
# Pre-flight, first: the recording hooks tie this session to the game when a tool call names the project folder as an
# absolute path, so the call must carry -Path <root>\games\<slug> literally (not %GF_ROOT% / $env:GF_ROOT, which the hook
# sees unexpanded). The session's earlier calls are then imported from its transcript (machine/README.md, "Recording").
$want = Join-Path $Root "games\$Slug"
if (-not $Path) { throw "pass -Path $want (the absolute project folder, written out, so the recording hooks file this session under the game)" }
if (-not [IO.Path]::IsPathRooted($Path) -or [IO.Path]::GetFullPath($Path).TrimEnd('\') -ne [IO.Path]::GetFullPath($want).TrimEnd('\')) {
    throw "-Path must be the absolute folder $want (got '$Path')"
}
Write-Host "project folder: $Path (this call maps the session to $Slug for recording)"
$words = $Slug -split '-'
if (-not $Project) { $Project = ($words | ForEach-Object { $_.Substring(0, 1).ToUpper() + $_.Substring(1) }) -join '' }
if (-not $Title) { $Title = ($words | ForEach-Object { $_.Substring(0, 1).ToUpper() + $_.Substring(1) }) -join ' ' }
if (-not $IdPrefix) { $IdPrefix = if ($words.Count -ge 2) { ($words | ForEach-Object { $_[0] }) -join '' } else { $Slug.Substring(0, 2) } }
if ($Project -notmatch '^[A-Z][A-Za-z0-9]{1,30}$') { throw "project name '$Project' must be PascalCase letters/digits (pass -Project)" }

# Names that must never appear inside a game (code, config, commits, builds).
foreach ($v in @($Slug, $Project, $Title, $Description, $Reason)) {
    if ($v -match '(?i)superposition|game[-_ ]?factory|claude|anthropic|openai' -or ($Org -and $v -match ('(?i)' + [regex]::Escape($Org)))) { throw "banned name in '$v' (see the game-session skill)" }
}
if ((Test-Path -LiteralPath $Path) -and @(Get-ChildItem -LiteralPath $Path -Force).Count) { throw "$Path exists and is not empty" }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git not found (run machine\bootstrap.ps1 first)' }

$template = Join-Path $PSScriptRoot 'ue-game'
$engineVer = [string]([IO.File]::ReadAllText((Join-Path $template '__PROJECT__.uproject')) | ConvertFrom-Json).EngineAssociation
$guid = [guid]::NewGuid().ToString('N').ToUpperInvariant()
$map = [ordered]@{ '__PROJECT_GUID__' = $guid; '__PROJECT__' = $Project; '__SLUG__' = $Slug; '__TITLE__' = $Title; '__DESCRIPTION__' = $Description }
$utf8 = New-Object Text.UTF8Encoding($false)
function Expand([string]$s) { foreach ($k in $map.Keys) { $s = $s.Replace($k, $map[$k]) }; return $s }

New-Item -ItemType Directory -Force $Path | Out-Null
$Path = (Resolve-Path -LiteralPath $Path).Path
$count = 0
foreach ($f in Get-ChildItem -LiteralPath $template -Recurse -File -Force) {
    $rel = Expand ($f.FullName.Substring($template.Length + 1))
    $dst = Join-Path $Path $rel
    New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
    [IO.File]::WriteAllText($dst, (Expand ([IO.File]::ReadAllText($f.FullName))), $utf8)
    $count++
}
$apDir = Join-Path $Path "Source\$Project\AutoPlay"
New-Item -ItemType Directory -Force $apDir | Out-Null
foreach ($n in 'AutoPlaySubsystem.h', 'AutoPlaySubsystem.cpp') {
    Copy-Item -LiteralPath (Join-Path $repo "tools\ue-pipeline\autoplay\$n") (Join-Path $apDir $n)
    $count++
}
$contract = if ((Get-Content (Join-Path $apDir 'AutoPlaySubsystem.h') -Raw) -match 'ContractVersion\s*=\s*(\d+)') { [int]$Matches[1] } else { $null }

# workflow.jsonl, first row: the operation this script just performed.
$scriptSha = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
$templateCommit = (& git -C $repo rev-parse --short=12 HEAD 2>$null)
$rowId = '{0}-{1:D5}' -f $IdPrefix, 1
$row = [ordered]@{
    schema = 'ue-workflow/v0'; id = $rowId; seq = 1; time = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
    actor = 'agent'; op = 'project.create'; target = "$Project.uproject"
    params = [ordered]@{ engine = $engineVer; template = 'ue-game'; template_commit = $templateCommit; files = $count; autoplay_contract = $contract; module = $Project }
    reason = $Reason; reason_source = 'agent_note'; status = 'observed'
    source = [ordered]@{ script = 'new-game.ps1'; sha256 = $scriptSha; commit = $null }
}
[IO.File]::WriteAllText((Join-Path $Path 'workflow.jsonl'), ($row | ConvertTo-Json -Compress -Depth 6) + "`n", $utf8)

# git + LFS + recorder, then the first commit (the post-commit hook records it).
$old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
& git -C $Path init -q -b main 2>&1 | Out-Null
& git -C $Path lfs install --local 2>&1 | Out-Null
$ErrorActionPreference = $old
& (Join-Path $repo 'machine\install-git-hook.ps1') -Repo $Path -HooksDir $HooksDir | Out-Null
$ErrorActionPreference = 'Continue'
& git -C $Path add -A 2>&1 | Out-Null
$msg = "Create the $Title project (UE $engineVer skeleton)`n`nLive Coding off, Shipping + HiDPI config, AutoPlay drop-in v$contract,`nroot-anchored .gitignore, LFS for every binary type.`n`nworkflow: $rowId"
$msgFile = Join-Path $env:TEMP "new-game-$PID.txt"
[IO.File]::WriteAllText($msgFile, $msg, $utf8)
& git -C $Path commit -q -F $msgFile 2>&1 | Out-Null
$code = $LASTEXITCODE
Remove-Item $msgFile -ErrorAction SilentlyContinue
$ErrorActionPreference = $old
if ($code -ne 0) { throw "first commit failed (git user.name / user.email set?)" }
$sha = (& git -C $Path rev-parse --short HEAD)

$remote = $null
if (-not $NoGitHub) {
    $full = "$Org/game-$Slug"
    $ErrorActionPreference = 'Continue'
    & gh repo view $full --json name 2>&1 | Out-Null
    $exists = ($LASTEXITCODE -eq 0)
    if (-not $exists) { & gh repo create $full --private --description $Title 2>&1 | Out-Host }
    $ErrorActionPreference = $old
    if ($exists -or $LASTEXITCODE -eq 0) {
        & git -C $Path remote add origin "https://github.com/$full.git"
        $remote = "https://github.com/$full (private; not pushed: push when the coordinator says)"
    } else { Write-Warning "could not create $full; create it later: gh repo create $full --private" }
}

Write-Host "created $Title ($Project) at $Path"
Write-Host "  files: $count, AutoPlay contract v$contract, first row $rowId, commit $sha"
Write-Host "  remote: $(if ($remote) { $remote } else { 'none (-NoGitHub)' })"
Write-Host "  next: write the design doc, build the editor target through ue-heavy.ps1, log every operation in workflow.jsonl"
