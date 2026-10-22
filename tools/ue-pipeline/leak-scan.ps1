<#
.SYNOPSIS
  Byte search (case-insensitive, ASCII and UTF-16LE) for strings that must not ship, across every file under a folder.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File leak-scan.ps1 %GF_ROOT%\builds\tower-defense\52a6f2a1-shipping
  powershell -ExecutionPolicy Bypass -File leak-scan.ps1 <dir> -Patterns <user-name>,superposition,game-factory

  Default patterns: the Windows user name inside paths (\<name>\ and /<name>/: source, PDB and temp paths compiled in;
  a bare-name search also hits the engine's 'zh_XIANG'/'zh-xiang' locale ids) and the names that must not ship ($ForbiddenNamePatterns in common.ps1). Prints hits per file with a short ASCII context; exit 1 if anything is found. build.ps1 runs the same
  scan (Find-LeakedStrings) after packaging and records the result.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Dir,
    [string[]]$Patterns = $null
)
. (Join-Path $PSScriptRoot 'common.ps1')
if (-not $Patterns) { $Patterns = $UserNamePatterns + $ForbiddenNamePatterns }
$hits = @(Find-LeakedStrings $Dir $Patterns)
foreach ($h in $hits) { "{0,6}  {1}  {2}  e.g. {3}" -f $h.count, $h.pattern, $h.file, $h.example }
$total = 0; foreach ($h in $hits) { $total += $h.count }
"{0} hits in {1} files under {2} (patterns: {3})" -f $total, $hits.Count, $Dir, ($Patterns -join ', ')
if ($hits.Count) { exit 1 }
