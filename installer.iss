; Inno Setup Script — Karaoke Manager Installer
; Tải Inno Setup tại: https://jrsoftware.org/isinfo.php
; Build: Mở file này bằng Inno Setup Compiler

#define AppName "Karaoke Manager"
#define AppVersion "1.0"
#define AppPublisher "Karaoke Manager"
#define AppExeName "KaraokeManager.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Tên file installer xuất ra
OutputBaseFilename=KaraokeManager_Setup_v{#AppVersion}
OutputDir=dist
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Icon của installer (thêm icon.ico nếu có)
; SetupIconFile=icon.ico
; Yêu cầu Windows 10+
MinVersion=10.0
; Không cần quyền Admin để cài (InstallForCurrentUser)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "vietnamese"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Tạo icon trên Desktop"; GroupDescription: "Tùy chọn:"; Flags: unchecked

[Files]
; Toàn bộ thư mục build từ PyInstaller
Source: "dist\KaraokeManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Gỡ cài đặt {#AppName}"; Filename: "{uninstallexe}"
; Desktop (nếu chọn)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Hỏi có muốn chạy ngay sau khi cài không
Filename: "{app}\{#AppExeName}"; \
    Description: "Khởi động {#AppName}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Xóa file log khi gỡ cài đặt
Type: files; Name: "{app}\*.log"

[Code]
// Kiểm tra xem app có đang chạy không trước khi cài/gỡ
function IsAppRunning(): Boolean;
var
  WbemLocator: Variant;
  WbemServices: Variant;
  WbemObjectSet: Variant;
begin
  Result := False;
  try
    WbemLocator := CreateOleObject('WbemScripting.SWbemLocator');
    WbemServices := WbemLocator.ConnectServer('', 'root\CIMV2');
    WbemObjectSet := WbemServices.ExecQuery(
      'SELECT * FROM Win32_Process WHERE Name = "KaraokeManager.exe"'
    );
    Result := (WbemObjectSet.Count > 0);
  except
    Result := False;
  end;
end;

function InitializeSetup(): Boolean;
begin
  if IsAppRunning() then
  begin
    MsgBox('Karaoke Manager đang chạy. Vui lòng đóng ứng dụng trước khi cài đặt.', mbError, MB_OK);
    Result := False;
  end else
    Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  if IsAppRunning() then
  begin
    MsgBox('Karaoke Manager đang chạy. Vui lòng đóng ứng dụng trước khi gỡ cài đặt.', mbError, MB_OK);
    Result := False;
  end else
    Result := True;
end;
