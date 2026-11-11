<#
.SYNOPSIS
  Baut dist\kimbaview\kimbaview.exe mit PyInstaller (ohne Konsolenfenster).
.DESCRIPTION
  Aufruf aus dem Projektordner:  powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
  Voraussetzung: virtuelle Umgebung in .venv mit  pip install -e ".[build]"
  Ergebnis ist ein Ordner-Build (onedir): startet schneller als --onefile und
  löst seltener Fehlalarme von Virenscannern aus.
#>
[CmdletBinding()]
param(
    [string]$Python = ''
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $here '..\..')
if (-not $Python) { $Python = Join-Path $root '.venv\Scripts\python.exe' }
Push-Location $root
try {
    # Versionsressource (Herausgeber/Copyright in den Dateieigenschaften)
    New-Item -ItemType Directory -Force (Join-Path $root 'build') | Out-Null
    $versionFile = Join-Path $root 'build\version_info.txt'
    & $Python (Join-Path $here 'make_version_info.py') $versionFile
    if ($LASTEXITCODE -ne 0) { throw 'Versionsressource konnte nicht erzeugt werden.' }

    & $Python -m PyInstaller --noconfirm --clean `
        --name kimbaview `
        --windowed `
        --icon (Join-Path $root 'src\kimbaview\assets\kimbaview.ico') `
        --version-file $versionFile `
        --onedir `
        --collect-data kimbaview `
        --collect-submodules pygments.lexers `
        --collect-submodules pygments.styles `
        --exclude-module PIL `
        --distpath dist --workpath build\pyinstaller --specpath build\pyinstaller `
        packaging\launcher.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller ist fehlgeschlagen (Code $LASTEXITCODE)." }
    # Lizenzen beilegen (eigene MIT-Lizenz + Texte aller gebündelten Pakete)
    Copy-Item (Join-Path $root 'LICENSE') (Join-Path $root 'dist\kimbaview\LICENSE.txt') -Force
    Copy-Item (Join-Path $root 'README.md') (Join-Path $root 'dist\kimbaview\README.md') -Force
    Copy-Item (Join-Path $root 'README.de.md') (Join-Path $root 'dist\kimbaview\README.de.md') -Force
    # Bilder der Anleitung (Icon, Screenshot)
    Copy-Item (Join-Path $root 'docs') (Join-Path $root 'dist\kimbaview\docs') -Recurse -Force
    & $Python (Join-Path $root 'packaging\collect_licenses.py') (Join-Path $root 'dist\kimbaview\THIRD-PARTY-LICENSES.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Lizenzdatei konnte nicht erzeugt werden.' }
    $exe = Join-Path $root 'dist\kimbaview\kimbaview.exe'
    Write-Host "Fertig: $exe"
    Write-Host "Optional als 'Öffnen mit'-Programm registrieren:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File packaging\windows\register-openwith.ps1"
}
finally { Pop-Location }
