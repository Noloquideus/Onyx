; Inno Setup script for Onyx CLI Windows installer
; Expects that PyInstaller has already produced:
;   dist\onyx-windows.exe (portable CLI)

#define MyAppName "Onyx CLI"
#define MyAppVersion "0.5.6"
; Portable exe name in dist\
#define MyPortableExe "onyx-windows.exe"
; Installed exe name in {app} (what users will call from PATH)
#define MyAppExeName "onyx.exe"

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
; Copy portable exe from repo-root\dist to {app} as onyx.exe
Source: "..\dist\{#MyPortableExe}"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion

[Icons]
Name: "{group}\Onyx CLI"; Filename: "{app}\{#MyAppExeName}"

[Registry]
; Append {app} to the current user's PATH when the addtopath task is selected
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
  ValueData: "{olddata};{app}"; Tasks: addtopath; Flags: preservestringtype

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Onyx CLI"; Flags: nowait postinstall skipifsilent

