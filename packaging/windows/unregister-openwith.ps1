<#
.SYNOPSIS
  Entfernt die "Öffnen mit"-Registrierung von kimbaview (nur aktueller Benutzer).
.DESCRIPTION
  Entfernt ausschließlich die von register-openwith.ps1 angelegten Einträge.
  Andere Programme, die für dieselben Endungen registriert sind, bleiben unberührt.
  Mit -WhatIf wird nur angezeigt, was passieren würde.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    # nur für Tests: anderer Registrierungszweig
    [string]$ClassesRoot = 'HKCU:\Software\Classes'
)
$ErrorActionPreference = 'Stop'

$progId     = 'kimbaview.Document'
$extensions = @('.md', '.markdown', '.mediawiki', '.wiki')
$classes    = $ClassesRoot

foreach ($key in @("$classes\$progId", "$classes\Applications\kimbaview.exe")) {
    if (Test-Path -LiteralPath $key) {
        if ($PSCmdlet.ShouldProcess($key, 'Schlüssel entfernen')) {
            Remove-Item -LiteralPath $key -Recurse -Force
        }
    }
}
foreach ($ext in $extensions) {
    $k = "$classes\$ext\OpenWithProgids"
    if ((Test-Path -LiteralPath $k) -and ($null -ne (Get-ItemProperty -LiteralPath $k -Name $progId -ErrorAction SilentlyContinue))) {
        if ($PSCmdlet.ShouldProcess("$k [$progId]", 'Wert entfernen')) {
            Remove-ItemProperty -LiteralPath $k -Name $progId -Force
        }
    }
}
if ($PSCmdlet.ShouldProcess('Explorer', 'Dateizuordnungen neu laden')) {
    Add-Type -Namespace KimbaView -Name Shell -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(int eventId, uint flags, System.IntPtr item1, System.IntPtr item2);
'@
    [KimbaView.Shell]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
}
Write-Host 'kimbaview-Registrierung entfernt.'
