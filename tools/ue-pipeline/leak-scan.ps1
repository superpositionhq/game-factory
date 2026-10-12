<#
.SYNOPSIS
  Byte search (case-insensitive, ASCII and UTF-16LE) for strings that must not ship, across every file under a folder.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File leak-scan.ps1 C:\Users\Xiang\Work\builds\tower-defense\52a6f2a1-shipping
  powershell -ExecutionPolicy Bypass -File leak-scan.ps1 <dir> -Patterns xiang,superposition,game-factory

  Default patterns: the Windows user name inside paths (\<name>\ and /<name>/: source, PDB and temp paths compiled in;
  a bare-name search also hits the engine's 'zh_XIANG'/'zh-xiang' locale ids) and the names the games must not contain. Prints hits per file with a short ASCII context; exit 1 if anything is found. build.ps1 runs the same
  scan (Find-LeakedStrings) after packaging and records the result.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Dir,
    [string[]]$Patterns = $null
)
. (Join-Path $PSScriptRoot 'common.ps1')
if (-not $Patterns) { $Patterns = $UserNamePatterns + @('superposition', 'game-factory', 'game_factory', 'gamefactory') }
$hits = @(Find-LeakedStrings $Dir $Patterns)
foreach ($h in $hits) { "{0,6}  {1}  {2}  e.g. {3}" -f $h.count, $h.pattern, $h.file, $h.example }
"{0} hits in {1} files under {2} (patterns: {3})" -f (($hits | Measure-Object count -Sum).Sum + 0), $hits.Count, $Dir, ($Patterns -join ', ')
if ($hits.Count) { exit 1 }
