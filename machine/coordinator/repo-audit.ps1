# Coordinator: audit a game repo for anything a push would miss: untracked files, ignored source/content, large
# non-LFS blobs, binaries tracked in plain git, README images missing or absent (exit 1). Run before telling a game
# session to push.
#   powershell -ExecutionPolicy Bypass -File machine\coordinator\repo-audit.ps1 -Game stealth
param([Parameter(Mandatory = $true)][string]$Game, [string]$Root)
. (Join-Path $PSScriptRoot '..\lib\gf-root.ps1')
if (-not $Root) { $Root = Get-GFRoot }
$p = Join-Path $Root "games\$Game"
$buildDirs = '^(Binaries|Intermediate|Saved|DerivedDataCache|Build|Packaged|\.vs)(/|$)|/(Binaries|Intermediate)/'
$untracked = @(git -C $p -c core.quotepath=off ls-files --others --exclude-standard)
$ignored = @(git -C $p -c core.quotepath=off ls-files --others --ignored --exclude-standard --directory | Where-Object { $_ -notmatch $buildDirs -and $_ -notmatch '__pycache__|\.pyc$|\.sln$|\.VC\.db|\.suo$' })
$ignBytes = 0; foreach ($d in $ignored) { $ignBytes += (Get-ChildItem (Join-Path $p $d) -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum }
$bigNonLfs = @(git -C $p rev-list --objects --all | git -C $p cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' | Where-Object { $_ -match '^blob (\d+) (.+)$' -and [long]$Matches[1] -gt 50MB } | ForEach-Object { $_ -replace '^blob ', '' })
$lfsPatterns = @(git -C $p lfs track 2>$null | Where-Object { $_ -match '^\s+\S' } | ForEach-Object { ($_.Trim() -split ' ')[0] })
# binary files tracked in plain git (should be LFS)
$binExt = '(?i)\.(uasset|umap|uexp|ubulk|fbx|obj|glb|abc|blend|png|jpg|jpeg|tga|exr|hdr|psd|dds|bmp|tif|tiff|wav|ogg|mp3|flac|wem|bnk|mp4|mov|mkv|ttf|otf|ufont|bin|zip|7z|pdf)$'
$lfsFiles = @{}; git -C $p lfs ls-files --name-only 2>$null | ForEach-Object { $lfsFiles[$_] = 1 }
$binInGit = @(git -C $p -c core.quotepath=off ls-files | Where-Object { $_ -match $binExt -and -not $lfsFiles[$_] })
# README images (user rule: real gameplay screenshots on GitHub): every local image README.md links must be committed
# at that ref, and the README must show at least one. Checked at HEAD (what a push ships) and at origin/main (what
# GitHub shows now; run `git fetch` first for a current view). HTML comments (the template's placeholder) are skipped.
function Get-ReadmeImageCheck([string]$Ref) {
    if (-not (git -C $p rev-parse --verify --quiet "$Ref^{commit}")) { return $null }
    $md = (git -C $p -c core.quotepath=off show "${Ref}:README.md" 2>$null) -join "`n"
    if (-not $md) { return [pscustomobject]@{ ref = $Ref; images = 0; missing = @(); problem = 'no README.md' } }
    $md = [regex]::Replace($md, '(?s)<!--.*?-->', '')
    $links = @([regex]::Matches($md, '!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)') | ForEach-Object { $_.Groups[1].Value }) +
             @([regex]::Matches($md, '(?i)<img\b[^>]*\bsrc\s*=\s*["'']([^"'']+)["'']') | ForEach-Object { $_.Groups[1].Value })
    $local = @($links | Where-Object { $_ -notmatch '^(?i)(https?:|data:)' } | ForEach-Object { [Uri]::UnescapeDataString(($_ -split '[?#]')[0]) -replace '^\./', '' -replace '^/', '' } | Select-Object -Unique)
    $missing = @($local | Where-Object { git -C $p cat-file -e "${Ref}:$_" 2>$null; $LASTEXITCODE -ne 0 })
    $problem = if ($missing.Count) { "README links $($missing.Count) image(s) not committed at $Ref" } elseif (-not $local.Count) { "README at $Ref shows no gameplay image" } else { '' }
    [pscustomobject]@{ ref = $Ref; images = $local.Count; missing = $missing; problem = $problem }
}
$readme = @(Get-ReadmeImageCheck 'HEAD'; Get-ReadmeImageCheck 'origin/main') | Where-Object { $_ }
$readmeProblems = @($readme | Where-Object { $_.problem } | ForEach-Object { $_.problem + $(if ($_.missing.Count) { ': ' + (($_.missing | Select-Object -First 4) -join '; ') } else { '' }) })
[pscustomobject]@{
    game = $Game; untracked = $untracked.Count; untracked_sample = ($untracked | Select-Object -First 5) -join '; '
    ignored_content = $ignored.Count; ignored_GB = [math]::Round($ignBytes / 1GB, 2); ignored_sample = ($ignored | Select-Object -First 6) -join '; '
    big_non_lfs_blobs = $bigNonLfs.Count; big_sample = ($bigNonLfs | Select-Object -First 3) -join '; '
    binaries_in_plain_git = $binInGit.Count; bin_sample = ($binInGit | Select-Object -First 4) -join '; '
    lfs_patterns = $lfsPatterns -join ' '
    readme_images = ($readme | ForEach-Object { "$($_.ref) $($_.images)" }) -join '; '
    readme_problems = $readmeProblems -join ' | '
}
if ($readmeProblems.Count) { Write-Host "FAIL: $($readmeProblems -join ' | ')" -ForegroundColor Red; exit 1 }
