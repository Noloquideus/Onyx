; Inno Setup script for Onyx CLI Windows installer
; This script expects that PyInstaller has already produced:
;   dist\onyx-windows.exe

#define MyAppName "Onyx CLI"
#define MyAppVersion "0.5.1"
#define MyAppExeName "onyx-windows.exe"

[Setup]
AppId={{B9F7D9B4-7C9C-4D3A-9A9D-ONYX-CLI}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher="Noloquideus"
DefaultDirName={pf}\Onyx
DefaultGroupName=Onyx
DisableDirPage=no
DisableProgramGroupPage=yes
OutputBaseFilename=onyx-setup
; Place the installer next to the dist\ folder at repo root
OutputDir=..\dist
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "addtopath"; Description: "Add Onyx install directory to PATH"; Flags: unchecked

[Files]
; exe is built into repo-root\dist, script lives in installer\
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Onyx CLI"; Filename: "{app}\{#MyAppExeName}"

[Registry]
; Append {app} to the current user's PATH when the addtopath task is selected
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
  ValueData: "{olddata};{app}"; Tasks: addtopath; Flags: preservestringtype

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Onyx CLI"; Flags: nowait postinstall skipifsilent


