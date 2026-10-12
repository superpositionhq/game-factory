<#
.SYNOPSIS
  Download, checksum-verify and unpack the pinned ffmpeg the recording pipeline uses (idempotent).
.DESCRIPTION
  Pinned build: gyan.dev ffmpeg 8.1.2 "full_build" .7z (166,721,853 bytes, SHA-256 below, matching gyan.dev's
  published .7z.sha256). Result: <root>\tools\ffmpeg-8.1.2\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe, which
  tools/ue-pipeline/common.ps1 (Find-FFmpeg) prefers over anything on PATH. Binaries are never committed.
  The archive is kept next to the folder with a .sha256 file, as on the original machine. A download whose hash does
  not match is deleted and the script fails; nothing from it is unpacked or run.
  Unpacks with 7-Zip when installed, else Windows' tar.exe (libarchive reads .7z on Windows 11).
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File machine\get-ffmpeg.ps1
  powershell -ExecutionPolicy Bypass -File machine\get-ffmpeg.ps1 -Archive D:\downloads\ffmpeg-8.1.2-full_build.7z
#>
param(
    [string]$Root,                       # machine root; default from machine/lib/gf-root.ps1
    [string]$Archive,                    # use an already downloaded .7z instead of downloading (still verified)
    [string]$Version = '8.1.2',
    [string]$Sha256 = '0fff188997a499b5382e0f66e845d4556c48c54f0113ebed4853d556dbdd7059',
    [long]$Bytes = 166721853,
    [string[]]$Urls = @(
        'https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-8.1.2-full_build.7z',
        'https://github.com/GyanD/codexffmpeg/releases/download/8.1.2/ffmpeg-8.1.2-full_build.7z'
    ),
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\gf-root.ps1')
if (-not $Root) { $Root = Get-GFRoot }
$name = "ffmpeg-$Version-full_build"
$dir = Join-Path $Root "tools\ffmpeg-$Version"
$exe = Join-Path $dir "$name\bin\ffmpeg.exe"
$dest = Join-Path $dir "$name.7z"

function Get-Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }

if ((Test-Path -LiteralPath $exe) -and (Test-Path -LiteralPath $dest) -and -not $Force) {
    if ((Get-Sha256 $dest) -eq $Sha256) { Write-Host "ffmpeg $Version present and verified: $exe"; return $exe }
    Write-Warning "archive next to ffmpeg does not match the pinned hash; re-fetching"
}
New-Item -ItemType Directory -Force $dir | Out-Null

if ($Archive) {
    if ((Get-Sha256 $Archive) -ne $Sha256) { throw "SHA-256 mismatch for $Archive (expected $Sha256)" }
    if ([IO.Path]::GetFullPath($Archive) -ne [IO.Path]::GetFullPath($dest)) { Copy-Item -LiteralPath $Archive $dest -Force }
} elseif (-not ((Test-Path -LiteralPath $dest) -and (Get-Sha256 $dest) -eq $Sha256)) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $tmp = "$dest.part"
    $ok = $false
    foreach ($u in $Urls) {
        try {
            Write-Host "downloading $u"
            Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
            $wc = New-Object Net.WebClient
            $wc.Headers.Add('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            $wc.DownloadFile($u, $tmp)
            $len = (Get-Item -LiteralPath $tmp).Length
            $h = Get-Sha256 $tmp
            if ($h -ne $Sha256) { Write-Warning "hash mismatch from $u ($len bytes, sha256 $h); discarded"; Remove-Item -LiteralPath $tmp -Force; continue }
            if ($len -ne $Bytes) { Write-Warning "size $len differs from the pinned $Bytes but the hash matches" }
            Move-Item -LiteralPath $tmp $dest -Force
            $ok = $true; break
        } catch { Write-Warning "download failed from ${u}: $($_.Exception.Message)" }
    }
    if (-not $ok) { throw "could not fetch a verified $name.7z; download it by hand and pass -Archive" }
}
[IO.File]::WriteAllText("$dest.sha256", $Sha256, (New-Object Text.UTF8Encoding($false)))

# Unpack into a fresh folder next to the target, then swap it in.
$stage = Join-Path $dir "_unpack-$PID"
Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $stage | Out-Null
$sevenZip = @("$env:ProgramFiles\7-Zip\7z.exe", "${env:ProgramFiles(x86)}\7-Zip\7z.exe") | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if ($sevenZip) { & $sevenZip x -y "-o$stage" $dest | Out-Null } else { & "$env:SystemRoot\System32\tar.exe" -xf $dest -C $stage }
if ($LASTEXITCODE -ne 0) { throw "unpacking $dest failed (exit $LASTEXITCODE)" }
if (-not (Test-Path -LiteralPath (Join-Path $stage "$name\bin\ffmpeg.exe"))) { throw "unexpected archive layout: no $name\bin\ffmpeg.exe" }
Remove-Item -LiteralPath (Join-Path $dir $name) -Recurse -Force -ErrorAction SilentlyContinue
Move-Item -LiteralPath (Join-Path $stage $name) (Join-Path $dir $name)
Remove-Item -LiteralPath $stage -Recurse -Force
Write-Host "ffmpeg $Version ready: $exe"
return $exe
