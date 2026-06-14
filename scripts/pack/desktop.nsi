; JotaDuo Desktop NSIS installer. Run makensis from repo root after
; building dist/win-unpacked (see scripts/pack/build_win.ps1).
; Usage: makensis /DJOTADUO_VERSION=1.2.3 /DOUTPUT_EXE=dist\JotaDuo-Setup-1.2.3.exe scripts\pack\desktop.nsi

!include "MUI2.nsh"
!define MUI_ABORTWARNING
; Use custom icon from unpacked env (copied by build_win.ps1)
!define MUI_ICON "${UNPACKED}\icon.ico"
!define MUI_UNICON "${UNPACKED}\icon.ico"

!ifndef JOTADUO_VERSION
  !define JOTADUO_VERSION "0.0.0"
!endif
!ifndef OUTPUT_EXE
  !define OUTPUT_EXE "dist\JotaDuo-Setup-${JOTADUO_VERSION}.exe"
!endif

Name "JotaDuo Desktop"
OutFile "${OUTPUT_EXE}"
InstallDir "$LOCALAPPDATA\JotaDuo"
InstallDirRegKey HKCU "Software\JotaDuo" "InstallPath"
RequestExecutionLevel user

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"

; Pass /DUNPACKED=full_path from build_win.ps1 so path works when cwd != repo root
!ifndef UNPACKED
  !define UNPACKED "dist\win-unpacked"
!endif

Section "JotaDuo Desktop" SEC01
  SetOutPath "$INSTDIR"
  File /r "${UNPACKED}\*.*"
  WriteRegStr HKCU "Software\JotaDuo" "InstallPath" "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Main shortcut - uses VBS to hide console window
  CreateShortcut "$SMPROGRAMS\JotaDuo Desktop.lnk" "$INSTDIR\JotaDuo Desktop.vbs" "" "$INSTDIR\icon.ico" 0
  CreateShortcut "$DESKTOP\JotaDuo Desktop.lnk" "$INSTDIR\JotaDuo Desktop.vbs" "" "$INSTDIR\icon.ico" 0
  
  ; Debug shortcut - shows console window for troubleshooting
  CreateShortcut "$SMPROGRAMS\JotaDuo Desktop (Debug).lnk" "$INSTDIR\JotaDuo Desktop (Debug).bat" "" "$INSTDIR\icon.ico" 0
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\JotaDuo Desktop.lnk"
  Delete "$SMPROGRAMS\JotaDuo Desktop (Debug).lnk"
  Delete "$DESKTOP\JotaDuo Desktop.lnk"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "Software\JotaDuo"
SectionEnd
