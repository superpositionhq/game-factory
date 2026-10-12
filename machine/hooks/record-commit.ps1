# Called by each game repo's git post-commit hook: append the new commit to
# <root>\.recording\<repo name>\commits.jsonl, whoever made it. <root> = the machine root (gf-root.ps1 next to this
# file; machine/lib/gf-root.ps1 in the repo). machine/install-git-hook.ps1 adds the hook line to a repo.
param([string]$Repo)
$ErrorActionPreference = 'Continue'   # git warnings on stderr must not abort the record
$utf8 = New-Object Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8   # git writes UTF-8; read it as such
$Repo = (Resolve-Path $Repo).Path
$project = Split-Path -Leaf $Repo
$gfLib = @((Join-Path $PSScriptRoot 'gf-root.ps1'), (Join-Path $PSScriptRoot '..\lib\gf-root.ps1')) | Where-Object { Test-Path $_ } | Select-Object -First 1
. $gfLib
$dir = Join-Path (Join-Path (Get-GFRoot) '.recording') $project
New-Item -ItemType Directory -Force $dir | Out-Null
$sha = git -C $Repo rev-parse HEAD
$fmt = git -C $Repo log -1 --format='%P%x00%an%x00%aI%x00%cI%x00%B' $sha
$parts = ($fmt -join "`n") -split "`0", 5
$files = @(git -C $Repo -c core.quotepath=off show --name-status --format= $sha | Where-Object { $_ } | ForEach-Object {
  $f = $_ -split "`t"; [ordered]@{ status = $f[0]; path = $f[-1] } })
$row = [ordered]@{
  schema      = 'superposition.commit/v0'
  recorded_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  project     = $project
  sha         = $sha
  parents     = @($parts[0] -split ' ' | Where-Object { $_ })
  author      = $parts[1]
  author_time = $parts[2]
  commit_time = $parts[3]
  message     = $parts[4].Trim()
  files       = $files
}
$mutex = New-Object Threading.Mutex($false, 'Global\claude-recording-hooks')
[void]$mutex.WaitOne(30000)
try { [IO.File]::AppendAllText((Join-Path $dir 'commits.jsonl'), ($row | ConvertTo-Json -Depth 6 -Compress) + "`n", $utf8) }
finally { $mutex.ReleaseMutex() }
