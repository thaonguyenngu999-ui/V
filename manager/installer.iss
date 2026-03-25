; S Manage Cloud Installer Script
; Inno Setup Script - Build với Inno Setup Compiler

#define MyAppName "S Manage Cloud"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "S Manage Team"
#define MyAppExeName "SManage_Cloud.exe"

[Setup]
; Thông tin cơ bản
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Output
OutputDir=installer_output
OutputBaseFilename=SManage_Cloud_Setup_v1.0
; Không dùng icon riêng, dùng icon mặc định
; SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Compression - LZMA2 nén tốt nhất
Compression=lzma2/ultra64
SolidCompression=yes
; UI
WizardStyle=modern
; Quyền admin để cài vào Program Files
PrivilegesRequired=admin
; Kiến trúc 64-bit
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main EXE
Source: "dist\SManage_Cloud.exe"; DestDir: "{app}"; Flags: ignoreversion

; Credentials (OAuth)
Source: "dist\credentials.json"; DestDir: "{app}"; Flags: ignoreversion

; Browser folder (Chromium) - đệ quy copy tất cả
Source: "dist\browser\*"; DestDir: "{app}\browser"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Chạy app sau khi cài xong (tùy chọn)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Xóa các file cache khi gỡ cài đặt
Type: filesandordirs; Name: "{localappdata}\SManage"
