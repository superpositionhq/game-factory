# __TITLE__: heavy Unreal jobs through the machine-wide limiter (<root>\tools\ue-heavy.ps1).
#   powershell -ExecutionPolicy Bypass -File Scripts/ue.ps1 build                          (editor target, Development)
#   powershell -ExecutionPolicy Bypass -File Scripts/ue.ps1 script -Script Scripts/<name>.py [-Reason "..."]
#   powershell -ExecutionPolicy Bypass -File Scripts/ue.ps1 game -Map /Game/Maps/<Map> [-Render] [-Extra "..."]
# `script` runs one editor Python script headless (UnrealEditor-Cmd -run=pythonscript). Keep this call shape: the
# creation replay recognises "ue.ps1 script -Script Scripts/<name>.py" in the recorded command, with the script as a
# literal, project-relative path. The script logs its own workflow.jsonl rows; -Reason reaches it as $env:UE_RUN_REASON.
# Engine: $env:UE_ENGINE, else the default UE 5.3 install. Limiter: $env:GF_ROOT\tools, else two folders up (<root>).
param(
  [Parameter(Position = 0)][ValidateSet('build', 'script', 'game')][string]$Mode,
  [string]$Script = '',
  [string]$Reason = '',
  [string]$Target = '__PROJECT__Editor',
  [string]$Config = 'Development',
  [string]$Map = '',
  [switch]$Render,
  [string]$Extra = '',
  [string]$Tag = 'test'
)
$ErrorActionPreference = 'Continue'
$Proj = Split-Path $PSScriptRoot -Parent
$Engine = if ($env:UE_ENGINE) { $env:UE_ENGINE } else { 'C:\Program Files\Epic Games\UE_5.3' }
$Root = if ($env:GF_ROOT) { $env:GF_ROOT } else { Split-Path (Split-Path $Proj -Parent) -Parent }
$Heavy = Join-Path $Root 'tools\ue-heavy.ps1'
$UProject = Join-Path $Proj '__PROJECT__.uproject'
$Logs = Join-Path $Proj 'Saved\Logs'
New-Item -ItemType Directory -Force $Logs | Out-Null
$t0 = Get-Date
switch ($Mode) {
  'build' {
    $log = Join-Path $Logs "build_$Target.log"
    # the limiter starts the job as its own process (no output passthrough): redirect inside a small batch file
    $bat = Join-Path $Logs "build_$Target.bat"
    [IO.File]::WriteAllText($bat, "@echo off`r`ncall `"$Engine\Engine\Build\BatchFiles\Build.bat`" $Target Win64 $Config -Project=`"$UProject`" -WaitMutex -NoHotReloadFromIDE > `"$log`" 2>&1`r`nexit /b %ERRORLEVEL%`r`n")
    & $Heavy -Label "__SLUG__ build $Target" -- $bat *> $null
    $code = $LASTEXITCODE
    Select-String -Path $log -Pattern 'error C\d+|error LNK|error :|\): error' | Select-Object -First 15 | ForEach-Object { $_.Line.Trim() }
    Write-Host "exit code $code ($([int]((Get-Date) - $t0).TotalSeconds) s)"
    exit $code
  }
  'script' {
    if (-not $Script -or $Script -match '^[A-Za-z]:|^[\\/]') { Write-Error 'pass -Script Scripts/<name>.py (project-relative)'; exit 2 }
    $name = [IO.Path]::GetFileNameWithoutExtension($Script)
    $abs = (Resolve-Path (Join-Path $Proj $Script)).Path
    $log = Join-Path $Logs "editor_$name.log"
    $env:UE_PYTHONPATH = Join-Path $Proj 'Scripts'
    $env:UE_RUN_REASON = $Reason
    & $Heavy -Label "__SLUG__ editor $name" -- "$Engine\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" $UProject -run=pythonscript "-script=$abs" -unattended -nop4 -nosplash -nullrhi -NoSound "-abslog=$log" *> $null
    $code = $LASTEXITCODE
    Select-String -Path $log -Pattern 'LogPython: Error|Traceback|Error: ' | Select-Object -Last 40 | ForEach-Object { $_.Line }
    Write-Host "exit code $code ($([int]((Get-Date) - $t0).TotalSeconds) s)"
    exit $code
  }
  'game' {
    $log = Join-Path $Logs "game_$Tag.log"
    if ($Render) { $exe = 'UnrealEditor.exe'; $rhi = @('-windowed', '-ResX=1280', '-ResY=720', '-ForceRes') } else { $exe = 'UnrealEditor-Cmd.exe'; $rhi = @('-nullrhi', '-nosound') }
    $a = @($UProject, $Map, '-game') + $rhi + @('-unattended', '-nosplash', "-abslog=$log") + ($Extra -split ' ' | Where-Object { $_ })
    & $Heavy -Label "__SLUG__ game $Tag" -- "$Engine\Engine\Binaries\Win64\$exe" @a *> $null
    $code = $LASTEXITCODE
    Write-Host "exit code $code ($([int]((Get-Date) - $t0).TotalSeconds) s)"
    exit $code
  }
}
