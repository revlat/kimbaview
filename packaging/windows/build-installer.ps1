<#
.SYNOPSIS
  Baut das Programm (PyInstaller) und daraus den Installer dist\installer\kimbaview-setup-<version>.exe.
.DESCRIPTION
  Voraussetzung: Inno Setup 6  (winget install JRSoftware.InnoSetup)
  Aufruf aus dem Projektordner:
    powershell -ExecutionPolicy Bypass -File packaging\windows\build-installer.ps1
  Mit -SkipBuild wird ein vorhandenes dist\kimbaview verwendet.
#>
[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [string]$Iscc = ''
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $here '..\..')
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not $SkipBuild) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here 'build.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Programm-Build fehlgeschlagen.' }
}
if (-not (Test-Path (Join-Path $root 'dist\kimbaview\kimbaview.exe'))) {
    throw 'dist\kimbaview\kimbaview.exe fehlt – zuerst ohne -SkipBuild ausführen.'
}

if (-not $Iscc) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
    )
    $Iscc = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if (-not $Iscc) {
        $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($cmd) { $Iscc = $cmd.Source }
    }
}
if (-not $Iscc) { throw 'Inno Setup (ISCC.exe) nicht gefunden. Installation: winget install JRSoftware.InnoSetup' }

$version = (& $python -c "import kimbaview; print(kimbaview.__version__)").Trim()
& $Iscc "/DAppVersion=$version" (Join-Path $here 'kimbaview.iss')
if ($LASTEXITCODE -ne 0) { throw "Inno Setup ist fehlgeschlagen (Code $LASTEXITCODE)." }
Write-Host "Fertig: $(Join-Path $root "dist\installer\kimbaview-setup-$version.exe")"
