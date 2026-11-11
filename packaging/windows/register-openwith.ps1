<#
.SYNOPSIS
  Registriert kimbaview als "Öffnen mit"-Programm für .md, .markdown, .mediawiki und .wiki.
.DESCRIPTION
  Nur für den aktuellen Benutzer (HKCU), keine Administratorrechte nötig.
  Das Standardprogramm wird NICHT geändert – kimbaview erscheint lediglich in
  "Öffnen mit" (Windows 11: unter "Weitere Apps" bzw. direkt in der Liste).
  Rückgängig machen:  unregister-openwith.ps1
  Mit -WhatIf wird nur angezeigt, was passieren würde.
.PARAMETER ExePath
  Pfad zu kimbaview.exe. Standard: dist\kimbaview\kimbaview.exe im Projektordner.
  Für eine pip-Installation funktioniert auch ...\.venv\Scripts\kimbaview.exe.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$ExePath = '',
    # nur für Tests: anderer Registrierungszweig
    [string]$ClassesRoot = 'HKCU:\Software\Classes'
)
$ErrorActionPreference = 'Stop'

if (-not $ExePath) {
    $here = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ExePath = Join-Path $here '..\..\dist\kimbaview\kimbaview.exe'
}
if (-not (Test-Path -LiteralPath $ExePath -PathType Leaf)) {
    throw "kimbaview.exe nicht gefunden: $ExePath  (zuerst packaging\windows\build.ps1 ausführen oder -ExePath angeben)"
}
$exe = (Resolve-Path -LiteralPath $ExePath).ProviderPath
if ($exe -notlike '*.exe') { throw "ExePath muss auf eine .exe zeigen: $exe" }

$progId     = 'kimbaview.Document'
$extensions = @('.md', '.markdown', '.mediawiki', '.wiki')
$classes    = $ClassesRoot
$command    = "`"$exe`" `"%1`""

function Ensure-Key([string]$Path) {
    # Bestehende Schlüssel nie überschreiben (New-Item -Force würde Werte löschen).
    if (-not (Test-Path -LiteralPath $Path)) {
        if ($PSCmdlet.ShouldProcess($Path, 'Registrierungsschlüssel anlegen')) {
            New-Item -Path $Path -Force | Out-Null
        }
    }
}
function Set-Value([string]$Path, [string]$Name, $Value, [string]$Type = 'String') {
    Ensure-Key $Path
    if ($PSCmdlet.ShouldProcess("$Path [$Name]", "Wert setzen: $Value")) {
        New-ItemProperty -LiteralPath $Path -Name $Name -Value $Value -PropertyType $Type -Force | Out-Null
    }
}

# 1) ProgID mit Öffnen-Befehl
Set-Value "$classes\$progId" '(default)' 'Markdown-/MediaWiki-Dokument'
Set-Value "$classes\$progId" 'FriendlyTypeName' 'Markdown-/MediaWiki-Dokument'
Set-Value "$classes\$progId\DefaultIcon" '(default)' "`"$exe`",0"
Set-Value "$classes\$progId\shell\open" 'FriendlyAppName' 'kimbaview'
Set-Value "$classes\$progId\shell\open\command" '(default)' $command

# 2) Anwendungseintrag (Name in der "Öffnen mit"-Liste, unterstützte Typen)
$app = "$classes\Applications\kimbaview.exe"
Set-Value $app 'FriendlyAppName' 'kimbaview'
Set-Value "$app\shell\open" 'FriendlyAppName' 'kimbaview'
Set-Value "$app\shell\open\command" '(default)' $command
foreach ($ext in $extensions) { Set-Value "$app\SupportedTypes" $ext '' }

# 3) Pro Endung als zusätzliche Option eintragen (OpenWithProgids, REG_NONE)
foreach ($ext in $extensions) {
    Set-Value "$classes\$ext\OpenWithProgids" $progId ([byte[]]@()) 'None'
}

# Explorer über die Änderung informieren
if ($PSCmdlet.ShouldProcess('Explorer', 'Dateizuordnungen neu laden')) {
    Add-Type -Namespace KimbaView -Name Shell -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(int eventId, uint flags, System.IntPtr item1, System.IntPtr item2);
'@
    [KimbaView.Shell]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
}
Write-Host "kimbaview ist als 'Öffnen mit'-Programm registriert für: $($extensions -join ', ')"
Write-Host "Programm: $exe"
