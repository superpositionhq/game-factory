<#
.SYNOPSIS
  Remove the names "Superposition" and "game-factory" from a finished game's git history: text file contents in every
  commit, commit messages, author/committer names and e-mails. Nothing else changes (workflow.jsonl and all record
  files stay). The untouched original is archived and verified first. DRY RUN BY DEFAULT; -Apply rewrites.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scrub-history.ps1 rally-racer                 # dry run: what would change
  powershell -ExecutionPolicy Bypass -File scrub-history.ps1 rally-racer -Apply
  powershell -ExecutionPolicy Bypass -File scrub-history.ps1 rally-racer -ReplaceMap names.json -Apply

  Replacements are applied in order (Perl regex -> literal text). Defaults:
    superposition.(schema)  -> ""             e.g. "superposition.ue-workflow/v0" -> "ue-workflow/v0"
    Superposition / superposition / SUPERPOSITION -> Studio / studio / STUDIO
    game-factory / Game-Factory / GAME-FACTORY / game_factory -> studio-tools / Studio-Tools / STUDIO-TOOLS / studio_tools
  -ReplaceMap JSON: [ { "match": "<perl regex>", "replace": "<text>" }, ... ] replaces the defaults.

  Only text blobs are rewritten (no NUL byte in the first 8 KB). Binary blobs and Git LFS content (uassets etc. are
  stored outside git) are never edited; the dry run lists binary blobs and LFS files in HEAD that contain the names.
  Safety: refuses while the game's session looks active (.recording\<game>\actions.jsonl written within
  -QuietMinutes, or an editor has the project open) or with uncommitted changes; archives a verified git bundle of
  all refs (+ a copy of .git\lfs\objects) to .recording\<game>\original-history\ before rewriting; verifies afterwards
  that no reachable text blob, message or identity still contains the names; never pushes, never runs gc.
  Engine: git filter-branch (ships with Git for Windows; git filter-repo would need Python) with Git's perl.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [string]$ReplaceMap,
    [int]$QuietMinutes = 120,
    [switch]$Apply,
    [switch]$KeepBackupRefs,
    [string]$RepoPath,      # testing only: scrub this repo instead of games\<game>
    [string]$ArchiveDir     # testing only: archive here instead of .recording\<game>\original-history
)

. (Join-Path $PSScriptRoot 'common.ps1')
$info = Get-GameInfo $Game
$repo = if ($RepoPath) { $RepoPath } else { $info.Dir }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$archive = if ($ArchiveDir) { $ArchiveDir } else { Join-Path $info.LogDir 'original-history' }
$work = Join-Path $archive "$Game-$stamp-scrub"
New-Item -ItemType Directory -Force $work | Out-Null
$problems = New-Object System.Collections.ArrayList
$perl = 'C:\Program Files\Git\usr\bin\perl.exe'
$bash = 'C:\Program Files\Git\bin\bash.exe'
function Note([string]$s) { Write-Host "  $s" }
function ToSh([string]$p) { '/' + $p.Substring(0, 1).ToLower() + $p.Substring(2).Replace('\', '/') }

Write-Host "== scrub-history $Game ($(if ($Apply) { 'APPLY' } else { 'dry run' }))  repo $repo"

# ---- rules ----
$rules = @(
    @{ match = '(?i)superposition\.(?=[a-z0-9_-]+/v?\d)'; replace = '' },
    @{ match = 'SUPERPOSITION'; replace = 'STUDIO' }, @{ match = 'Superposition'; replace = 'Studio' }, @{ match = '(?i)superposition'; replace = 'studio' },
    @{ match = 'GAME-FACTORY'; replace = 'STUDIO-TOOLS' }, @{ match = 'Game-Factory'; replace = 'Studio-Tools' },
    @{ match = '(?i)game_factory'; replace = 'studio_tools' }, @{ match = '(?i)game-factory'; replace = 'studio-tools' }
)
if ($ReplaceMap) { $rules = @((Read-JsonFile $ReplaceMap) | ForEach-Object { @{ match = $_.match; replace = $_.replace } }) }
$b64 = { param($s) [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($s)) }
[System.IO.File]::WriteAllText((Join-Path $work 'rules.tsv'), ((@($rules | ForEach-Object { "$(& $b64 $_.match)`t$(& $b64 $_.replace)" }) -join "`n") + "`n"), $Utf8NoBom)

# ---- Perl helpers (binary-safe, run with Git's perl) ----
$common = @'
use strict; use MIME::Base64;
sub load_rules { my ($f) = @_; open(my $h, '<', $f) or die "rules: $!"; my @r;
  while (<$h>) { chomp; next unless length; my ($m, $p) = split /\t/; push @r, [decode_base64($m), decode_base64($p // '')]; }
  close $h; return @r; }
sub apply_rules { my ($t, @r) = @_; for my $x (@r) { my ($re, $rep) = @$x; $t =~ s/$re/$rep/g; } return $t; }
our $BANNED = qr/superposition|game[-_]factory/i;
1;
'@
[System.IO.File]::WriteAllText((Join-Path $work 'common.pl'), $common, $Utf8NoBom)
# blobs.pl <mode scan|map> <rules> <report> [blobmap]: every reachable blob containing a name.
$blobs = @'
use strict; use IPC::Open2; use File::Basename;
require (dirname(__FILE__) . '/common.pl'); our $BANNED;
my ($mode, $rules, $report, $mapfile) = @ARGV; my @r = load_rules($rules);
my %path; open(my $rl, '-|', 'git', 'rev-list', '--all', '--objects') or die;
while (<$rl>) { chomp; my ($s, $p) = split / /, $_, 2; $path{$s} //= ($p // ''); } close $rl;
my $pid = open2(my $out, my $in, 'git', 'cat-file', '--batch'); binmode $out; binmode $in;
open(my $rep, '>', $report) or die; my $map; if ($mode eq 'map') { open($map, '>', $mapfile) or die; }
for my $s (sort keys %path) {
  print $in "$s\n"; $in->flush; my $h = <$out>; chomp $h; my (undef, $type, $size) = split / /, $h;
  my $data = ''; read($out, $data, $size) if $size; my $nl; read($out, $nl, 1);
  next unless $type eq 'blob' && $data =~ $BANNED;
  if (index(substr($data, 0, 8192), "\0") >= 0) { print $rep "binary\t$s\t-\t1\t$path{$s}\n"; next; }
  my @hits = ($data =~ /$BANNED/g); my $new = apply_rules($data, @r); my $left = ($new =~ $BANNED) ? 1 : 0;
  my $ns = '-';
  if ($mode eq 'map') {
    my $p2 = open2(my $ho, my $hi, 'git', 'hash-object', '-w', '--stdin'); binmode $hi; print $hi $new; close $hi;
    $ns = <$ho>; chomp $ns; waitpid($p2, 0); print $map "$s $ns\n";
  }
  print $rep "text\t$s\t$ns\t$left\t$path{$s}\t" . scalar(@hits) . "\n";
}
close $in; waitpid($pid, 0); close $rep; close $map if $map;
'@
[System.IO.File]::WriteAllText((Join-Path $work 'blobs.pl'), $blobs, $Utf8NoBom)
# text.pl <rules>: stdin -> rules -> stdout (commit messages, author/committer fields).
$text = @'
use strict; use File::Basename; require (dirname(__FILE__) . '/common.pl');
my @r = load_rules($ARGV[0]); binmode STDIN; binmode STDOUT; local $/; my $t = <STDIN>; $t = '' unless defined $t;
print apply_rules($t, @r);
'@
[System.IO.File]::WriteAllText((Join-Path $work 'text.pl'), $text, $Utf8NoBom)
# remap.pl <blobmap>: `git ls-files -s` lines whose blob is in the map, with the new blob (for update-index --index-info).
$remap = @'
use strict; my %m; open(my $h, '<', $ARGV[0]) or die; while (<$h>) { chomp; my ($a, $b) = split / /; $m{$a} = $b; } close $h;
while (<STDIN>) { if (/^(\d+) ([0-9a-f]{40}) (\d)\t(.*)$/s && exists $m{$2}) { print "$1 $m{$2} $3\t$4"; } }
'@
[System.IO.File]::WriteAllText((Join-Path $work 'remap.pl'), $remap, $Utf8NoBom)

function Invoke-Perl([string[]]$PerlArgs) {
    $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    Push-Location $repo
    $fwd = @($PerlArgs | ForEach-Object { $_.Replace('\', '/') })   # Git's msys perl wants forward slashes
    try { & $perl @fwd 2>&1 | ForEach-Object { "$_" }; $code = $LASTEXITCODE } finally { Pop-Location; $ErrorActionPreference = $eap }
    if ($code -ne 0) { throw "perl $($PerlArgs[0]) failed ($code)" }
}

# ---- 1. is the game's session still working on it? ----
$actions = Join-Path $info.LogDir 'actions.jsonl'
if (Test-Path $actions) {
    $age = ((Get-Date) - (Get-Item $actions).LastWriteTime).TotalMinutes
    Note ("session activity: actions.jsonl last written {0:N0} min ago (quiet needed: {1} min)" -f $age, $QuietMinutes)
    if ($age -lt $QuietMinutes) { [void]$problems.Add("the game's session was active $([int]$age) min ago") }
}
$editors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($repo) })
if ($editors.Count) { [void]$problems.Add("an editor has the project open (pid $($editors[0].ProcessId))") }
$dirty = @(Invoke-Git $repo @('status', '--porcelain', '--untracked-files=no') | Where-Object { "$_".Trim() })
if ($dirty.Count) { [void]$problems.Add("working tree has uncommitted changes ($($dirty.Count) files)") }

# ---- 2. what would change ----
$refs = @(Invoke-Git $repo @('show-ref') | Where-Object { $_ -and $_ -notmatch 'refs/original/' })
Note "refs: $($refs.Count), commits: $("$(Invoke-Git $repo @('rev-list', '--all', '--count'))".Trim())"
$badRefs = @($refs | Where-Object { $_ -match '(?i)superposition|game[-_]factory' })
if ($badRefs.Count) { Note "ref names containing a name (rename by hand): $($badRefs -join ', ')" }

$report = Join-Path $work 'blobs-dry.tsv'
Invoke-Perl @((Join-Path $work 'blobs.pl'), 'scan', (Join-Path $work 'rules.tsv'), $report) | Out-Null
$rows = @(Get-Content $report | ForEach-Object { $f = $_ -split "`t"; [pscustomobject]@{ kind = $f[0]; sha = $f[1]; left = $f[3]; path = $f[4]; hits = $(if ($f.Count -gt 5) { [int]$f[5] } else { 0 }) } })
$textRows = @($rows | Where-Object kind -eq 'text'); $binRows = @($rows | Where-Object kind -eq 'binary')
Note "text blobs containing a name: $($textRows.Count) (in $(@($textRows | Select-Object -Expand path -Unique).Count) paths, $(($textRows | Measure-Object hits -Sum).Sum) occurrences)"
$textRows | Group-Object path | Sort-Object Count -Descending | Select-Object -First 25 | ForEach-Object { Note ("    {0,4} versions  {1}" -f $_.Count, $_.Name) }
$leftRows = @($textRows | Where-Object left -eq '1')
if ($leftRows.Count) { Note "text blobs where a name survives the rules (adjust -ReplaceMap): $(@($leftRows | Select-Object -Expand path -Unique) -join ', ')" }
if ($binRows.Count) { Note "binary blobs containing a name (not edited): $(@($binRows | Select-Object -Expand path -Unique) -join ', ')" }

# Samples of the replacement in context (current tree).
$samples = @(Invoke-Git $repo @('grep', '-I', '-n', '-i', '-E', 'superposition|game[-_]factory', 'HEAD', '--') -AllowFail | Where-Object { $_ } | Select-Object -First 8)
foreach ($s in $samples) {
    $after = $s; foreach ($r in $rules) { $after = [regex]::Replace($after, $r.match, $r.replace) }
    Note "    $($s.Substring(0, [Math]::Min(150, $s.Length)))"
    Note "     -> $($after.Substring(0, [Math]::Min(150, $after.Length)))"
}

$msgHits = @(Invoke-Git $repo @('log', '--all', '--format=%h %s', '-i', '-E', '--grep=superposition|game[-_]factory') | Where-Object { $_ })
Note "commit messages containing a name: $($msgHits.Count)"
$msgHits | Select-Object -First 8 | ForEach-Object { Note "    $_" }
$ids = @(Invoke-Git $repo @('log', '--all', '--format=%an <%ae>%n%cn <%ce>') | Where-Object { $_ -match '(?i)superposition|game[-_]factory' } | Sort-Object -Unique)
foreach ($i in $ids) { $n = $i; foreach ($r in $rules) { $n = [regex]::Replace($n, $r.match, $r.replace) }; Note "identity: $i  ->  $n" }

# LFS-stored files are outside git: report HEAD's LFS files that contain a name (ASCII or UTF-16) so they can be fixed in the editor.
$lfsHits = New-Object System.Collections.ArrayList
foreach ($line in @(Invoke-Git $repo @('lfs', 'ls-files', '-n') -AllowFail | Where-Object { $_ })) {
    $f = Join-Path $repo $line
    if (-not (Test-Path -LiteralPath $f)) { continue }
    $bytes = [System.IO.File]::ReadAllBytes($f)
    $a = [Text.Encoding]::ASCII.GetString($bytes); $w = [Text.Encoding]::Unicode.GetString($bytes)
    if ($a -match '(?i)superposition|game[-_]factory' -or $w -match '(?i)superposition|game[-_]factory') { [void]$lfsHits.Add($line) }
}
Note "LFS files in HEAD containing a name (not edited here): $($lfsHits.Count) $(if ($lfsHits.Count) { '-> ' + (($lfsHits | Select-Object -First 10) -join ', ') })"

$lfsDir = Join-Path (Join-Path $repo '.git') 'lfs\objects'
$lfsBytes = 0
if (Test-Path $lfsDir) { foreach ($f in Get-ChildItem $lfsDir -Recurse -File) { $lfsBytes += $f.Length } }
Note ("archive: {0}\{1}-{2}.bundle + LFS objects {3:N1} MB" -f $archive, $Game, $stamp, ($lfsBytes / 1MB))

if (-not $Apply) {
    if ($problems.Count) { Write-Host "would REFUSE now: $($problems -join '; ')" }
    Write-Host "dry run: nothing changed (reports in $work). Re-run with -Apply to archive and rewrite."
    return
}
if ($problems.Count) { throw "refusing: $($problems -join '; ')" }

# ---- 3. archive the untouched original, verify ----
$bundle = Join-Path $archive "$Game-$stamp.bundle"
Invoke-Git $repo @('bundle', 'create', $bundle, '--all') | Out-Null
Invoke-Git $repo @('bundle', 'verify', $bundle) | Out-Null
$heads = @(Invoke-Git $repo @('bundle', 'list-heads', $bundle) | ForEach-Object { ("$_" -split '\s+')[1] })
foreach ($r in $refs) { $name = ("$r" -split '\s+')[1]; if ($name -notin $heads) { throw "bundle is missing $name" } }
[System.IO.File]::WriteAllText((Join-Path $archive "$Game-$stamp-refs.txt"), (($refs -join "`n") + "`n"), $Utf8NoBom)
if (Test-Path $lfsDir) {
    & robocopy.exe $lfsDir (Join-Path $archive "$Game-$stamp-lfs-objects") /E /NJH /NJS /NP /NFL /NDL | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "LFS object copy failed ($LASTEXITCODE)" }
}
Write-Host "archived and verified: $bundle ($([math]::Round((Get-Item $bundle).Length / 1MB, 1)) MB, $($heads.Count) refs)"

# ---- 4. rewrite ----
$blobMap = Join-Path $work 'blobmap.txt'
Invoke-Perl @((Join-Path $work 'blobs.pl'), 'map', (Join-Path $work 'rules.tsv'), (Join-Path $work 'blobs-apply.tsv'), $blobMap) | Out-Null
$P = { param($n) "'" + (ToSh (Join-Path $work $n)) + "'" }
$run = @"
set -e
cd '$(ToSh $repo)'
export FILTER_BRANCH_SQUELCH_WARNING=1
PERL='/usr/bin/perl'
git filter-branch -f \
  --index-filter "git ls-files -s | `$PERL $(& $P 'remap.pl') $(& $P 'blobmap.txt') | git update-index --index-info" \
  --msg-filter "`$PERL $(& $P 'text.pl') $(& $P 'rules.tsv')" \
  --env-filter ". $(& $P 'envfix.sh')" \
  --tag-name-filter cat -- --all
"@
$envfix = @"
f() { printf '%s' "`$1" | /usr/bin/perl $(& $P 'text.pl') $(& $P 'rules.tsv'); }
export GIT_AUTHOR_NAME="`$(f "`$GIT_AUTHOR_NAME")" GIT_AUTHOR_EMAIL="`$(f "`$GIT_AUTHOR_EMAIL")"
export GIT_COMMITTER_NAME="`$(f "`$GIT_COMMITTER_NAME")" GIT_COMMITTER_EMAIL="`$(f "`$GIT_COMMITTER_EMAIL")"
"@
[System.IO.File]::WriteAllText((Join-Path $work 'envfix.sh'), $envfix.Replace("`r`n", "`n"), $Utf8NoBom)
[System.IO.File]::WriteAllText((Join-Path $work 'run.sh'), $run.Replace("`r`n", "`n"), $Utf8NoBom)
$code = Invoke-Logged $bash "`"$(ToSh (Join-Path $work 'run.sh'))`"" (Join-Path $work 'filter-branch.log')
if ($code -ne 0) { throw "git filter-branch failed ($code); see $work\filter-branch.log. The original is in $bundle." }

# ---- 5. verify ----
if (-not $KeepBackupRefs) {
    foreach ($r in @(Invoke-Git $repo @('for-each-ref', '--format=%(refname)', 'refs/original/') | Where-Object { $_ })) { Invoke-Git $repo @('update-ref', '-d', "$r") | Out-Null }
}
$verify = Join-Path $work 'blobs-verify.tsv'
Invoke-Perl @((Join-Path $work 'blobs.pl'), 'scan', (Join-Path $work 'rules.tsv'), $verify) | Out-Null
$stillText = @(Get-Content $verify | Where-Object { $_ -like "text`t*" })
$stillMsg = @(Invoke-Git $repo @('log', '--branches', '--tags', '--format=%h', '-i', '-E', '--grep=superposition|game[-_]factory') | Where-Object { $_ })
$stillId = @(Invoke-Git $repo @('log', '--branches', '--tags', '--format=%an %ae %cn %ce') | Where-Object { $_ -match '(?i)superposition|game[-_]factory' })
Write-Host "after: text blobs with a name $($stillText.Count) (refs/original $(if ($KeepBackupRefs) { 'kept' } else { 'removed' })), messages $($stillMsg.Count), identities $($stillId.Count)"
if ($stillText.Count -or $stillMsg.Count -or $stillId.Count) { Write-Host "WARNING: names remain; see $verify. The original is in $bundle." }
Write-Host "The old objects stay in this repo until 'git reflog expire --expire=now --all; git gc --prune=now' (they are in the bundle)."
$remotes = @(Invoke-Git $repo @('remote') | Where-Object { $_ })
if ($remotes.Count) { Write-Host "remote(s) $($remotes -join ', '): publishing needs a force-push; not done here." }
