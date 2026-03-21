; --- Configuration Variables ---
#define MyAppName "AstroBasics"
#define MyAppVersion "0.0.1"
#define MyAppPublisher "Developer"
#define MyAppExeName "AstroBasics.exe"

[Setup]
; --- Application Information ---
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; --- Installation Directory Settings (Per-User) ---
; Installs to C:\Users\Username\AppData\Local\Astro Basics
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Tells Windows NOT to ask for Admin rights (No UAC prompt)
PrivilegesRequired=lowest

; --- Modern Installer Tweaks ---
; Skips the "Choose Start Menu Folder" page for a faster, streamlined install
DisableProgramGroupPage=yes
; Sets the app icon in the Windows "Add/Remove Programs" list
UninstallDisplayIcon={app}\icon.ico

; --- Output Settings ---
; Where the installer .exe will be saved
OutputDir=.\
OutputBaseFilename=Astro_Basics_Setup_v1.0
; The icon for the installer .exe itself
SetupIconFile=icon.ico

; --- Compression Settings ---
Compression=lzma2/ultra64
SolidCompression=yes

[Files]
; Core Application Files (Grabs everything from the PyInstaller dist folder)
Source: "dist\AstroBasics\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Explicitly copies the icon file into the app folder so shortcuts can use it
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu Shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"

; Start Menu Uninstaller Shortcut
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\icon.ico"

; Desktop Shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"

[Run]
; Checkbox option to launch the application when the installer finishes
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent