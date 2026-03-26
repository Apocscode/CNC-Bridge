; CNC Bridge — Inno Setup Installer Script
; Builds a Windows installer for CNC Bridge Desktop Application
;
; Prerequisites:
;   1. Build the standalone .exe first:
;      cd bridge-app
;      pyinstaller --onefile --windowed --name CNC-Bridge --icon assets/icon.ico src/main.py
;   2. The built exe will be in bridge-app/dist/CNC-Bridge.exe
;   3. Install Inno Setup 6: https://jrsoftware.org/isinfo.php
;   4. Open this .iss file in Inno Setup Compiler and click Build
;
; Output: installer/Output/CNC-Bridge-Setup-v2.0.0.exe

[Setup]
AppName=CNC Bridge
AppVersion=2.0.0
AppPublisher=Apocscode
AppPublisherURL=https://github.com/Apocscode/CNC-Bridge
AppSupportURL=https://github.com/Apocscode/CNC-Bridge/issues
AppUpdatesURL=https://github.com/Apocscode/CNC-Bridge/releases
DefaultDirName={autopf}\CNC Bridge
DefaultGroupName=CNC Bridge
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=CNC-Bridge-Setup-v2.0.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application executable (built with PyInstaller)
Source: "..\bridge-app\dist\CNC-Bridge.exe"; DestDir: "{app}"; Flags: ignoreversion

; Post processor for Fusion 360
Source: "..\post-processor\anilam-crusader-m.cps"; DestDir: "{app}\post-processor"; Flags: ignoreversion

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CONTRIBUTING.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\quickstart.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\troubleshooting.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\quick-reference-card.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\wiring\*.svg"; DestDir: "{app}\docs\wiring"; Flags: ignoreversion

; PDF manuals (if present)
Source: "..\bridge-app\docs\*.pdf"; DestDir: "{app}\docs"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\CNC Bridge"; Filename: "{app}\CNC-Bridge.exe"
Name: "{group}\Quick Start Guide"; Filename: "{app}\docs\quickstart.md"
Name: "{group}\{cm:UninstallProgram,CNC Bridge}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CNC Bridge"; Filename: "{app}\CNC-Bridge.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CNC-Bridge.exe"; Description: "{cm:LaunchProgram,CNC Bridge}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandirs; Name: "{app}\config"
Type: filesandirs; Name: "{app}\logs"
Type: filesandirs; Name: "{app}\backups"
Type: filesandirs; Name: "{app}\__pycache__"
