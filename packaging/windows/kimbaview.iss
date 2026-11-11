; Inno-Setup-Skript für kimbaview
; Bauen:  powershell -ExecutionPolicy Bypass -File packaging\windows\build-installer.ps1
;
; Standard: Installation nur für den aktuellen Benutzer, OHNE Adminrechte, nach
; %LOCALAPPDATA%\Programs\kimbaview. Im Assistenten kann optional "für alle Benutzer"
; gewählt werden (dann mit Adminrechten nach C:\Program Files).

#ifndef AppVersion
  #define AppVersion "1.0.2"
#endif
#define AppName "kimbaview"
#define AppPublisher "revlat"
#define AppExe "kimbaview.exe"
#define ProgId "kimbaview.Document"

[Setup]
AppId={{A1A13738-26EA-4DAC-80ED-49DF9260F8AC}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=Copyright (c) 2026 {#AppPublisher}
AppComments=Viewer for Markdown and MediaWiki files
VersionInfoCompany={#AppPublisher}
VersionInfoCopyright=Copyright (c) 2026 {#AppPublisher}
VersionInfoDescription=kimbaview Setup
VersionInfoProductName={#AppName}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\..\LICENSE
OutputDir=..\..\dist\installer
OutputBaseFilename=kimbaview-setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\..\src\kimbaview\assets\kimbaview.ico
ChangesAssociations=yes
CloseApplications=yes
; Sprache des Assistenten nach Windows-Sprache; Dialog nur, wenn keine passt
ShowLanguageDialog=auto

[Languages]
; Englisch zuerst = Standard, wenn die Windows-Sprache weder Englisch noch Deutsch ist
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[CustomMessages]
en.TaskOpenWith=Offer in the context menu under "Open with" (.md, .markdown, .mediawiki, .wiki)
de.TaskOpenWith=Im Kontextmenü unter „Öffnen mit“ anbieten (.md, .markdown, .mediawiki, .wiki)
en.GroupIntegration=Integration:
de.GroupIntegration=Integration:
en.ShortcutComment=View Markdown and MediaWiki files
de.ShortcutComment=Markdown- und MediaWiki-Dateien anzeigen
en.DocTypeName=Markdown/MediaWiki document
de.DocTypeName=Markdown-/MediaWiki-Dokument
en.RunAfterInstall=Start kimbaview and show the guide
de.RunAfterInstall=kimbaview starten und Anleitung anzeigen
en.ReadmeFile=README.md
de.ReadmeFile=README_DE.md
en.WebView2Missing=Note: The Microsoft Edge WebView2 Runtime was not found. kimbaview needs it to display documents. Install:  winget install Microsoft.EdgeWebView2Runtime
de.WebView2Missing=Achtung: Die Microsoft-Edge-WebView2-Runtime wurde nicht gefunden. kimbaview braucht sie zur Anzeige. Installation:  winget install Microsoft.EdgeWebView2Runtime
en.PandocMissing=Note: MediaWiki files need Pandoc (Markdown works without it). Install:  winget install --id JohnMacFarlane.Pandoc
de.PandocMissing=Hinweis: Für MediaWiki-Dateien wird Pandoc benötigt (Markdown geht auch ohne). Installation:  winget install --id JohnMacFarlane.Pandoc

[Tasks]
Name: "openwith"; Description: "{cm:TaskOpenWith}"; GroupDescription: "{cm:GroupIntegration}"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\kimbaview\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "{cm:ShortcutComment}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; ProgID mit Öffnen-Befehl (HKA = HKCU bei Benutzerinstallation, HKLM bei Installation für alle)
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: ""; ValueData: "{cm:DocTypeName}"; Flags: uninsdeletekey; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: "FriendlyTypeName"; ValueData: "{cm:DocTypeName}"; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\{#ProgId}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"",0"; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\open"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: openwith
; Anwendungseintrag für die "Öffnen mit"-Liste
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".md"; ValueData: ""; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".markdown"; ValueData: ""; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".mediawiki"; ValueData: ""; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".wiki"; ValueData: ""; Tasks: openwith
; Leere Endungs-Schlüssel beim Deinstallieren aufräumen (nur wenn nichts anderes drinsteht).
; Muss VOR den OpenWithProgids-Zeilen stehen: Inno deinstalliert in umgekehrter Reihenfolge.
Root: HKA; Subkey: "Software\Classes\.md"; Flags: uninsdeletekeyifempty; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.markdown"; Flags: uninsdeletekeyifempty; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.mediawiki"; Flags: uninsdeletekeyifempty; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.wiki"; Flags: uninsdeletekeyifempty; Tasks: openwith
; Pro Endung nur als zusätzliche Option – das Standardprogramm bleibt unverändert
Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: string; ValueName: "{#ProgId}"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.markdown\OpenWithProgids"; ValueType: string; ValueName: "{#ProgId}"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.mediawiki\OpenWithProgids"; ValueType: string; ValueName: "{#ProgId}"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.wiki\OpenWithProgids"; ValueType: string; ValueName: "{#ProgId}"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty; Tasks: openwith

[Run]
Filename: "{app}\{#AppExe}"; Parameters: """{app}\{cm:ReadmeFile}"""; Description: "{cm:RunAfterInstall}"; Flags: postinstall nowait skipifsilent

[Code]
function WebView2Installed(): Boolean;
var
  V: String;
begin
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', V) and (V <> '') and (V <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', V) and (V <> '') and (V <> '0.0.0.0'));
end;

function PandocInstalled(): Boolean;
begin
  Result :=
    (FileSearch('pandoc.exe', GetEnv('PATH')) <> '') or
    FileExists(ExpandConstant('{localappdata}\Pandoc\pandoc.exe')) or
    FileExists(ExpandConstant('{commonpf64}\Pandoc\pandoc.exe'));
end;

procedure CurPageChanged(CurPageID: Integer);
var
  Notes: String;
begin
  if CurPageID = wpFinished then
  begin
    Notes := '';
    if not WebView2Installed() then
      Notes := Notes + #13#10#13#10 + CustomMessage('WebView2Missing');
    if not PandocInstalled() then
      Notes := Notes + #13#10#13#10 + CustomMessage('PandocMissing');
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption + Notes;
  end;
end;
