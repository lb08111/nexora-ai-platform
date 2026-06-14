!include LogicLib.nsh
!include nsDialogs.nsh

Var JotaDuoCliPathCheckbox
Var JotaDuoCliPathState

Page custom JOTADUO_CLI_PATH_PAGE JOTADUO_CLI_PATH_PAGE_LEAVE

!macro JOTADUO_UPDATE_CLI_PATH ACTION
  InitPluginsDir
  File /oname=$PLUGINSDIR\jotaduo-update-path.ps1 "..\..\..\..\nsis\update-jotaduo-path.ps1"
  nsExec::ExecToStack `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\jotaduo-update-path.ps1" -Action "${ACTION}" -Path "$INSTDIR\binaries\jotaduo-backend"`
  Pop $0
  Pop $1
!macroend

!macro JOTADUO_ADD_CLI_PATH_IF_SELECTED
  ${If} $JotaDuoCliPathState == 0
    DetailPrint "$(jotaduoCliPathSkipped)"
  ${Else}
    IfFileExists "$INSTDIR\binaries\jotaduo-backend\jotaduo.exe" 0 jotaduo_cli_path_missing
    !insertmacro JOTADUO_UPDATE_CLI_PATH "Add"
    ${If} $0 == 0
      DetailPrint "$(jotaduoCliPathAdded)"
    ${Else}
      DetailPrint "$(jotaduoCliPathUpdateFailed)"
      DetailPrint "$1"
    ${EndIf}
    Goto jotaduo_cli_path_done
    jotaduo_cli_path_missing:
      DetailPrint "$(jotaduoCliPathMissing)"
    jotaduo_cli_path_done:
  ${EndIf}
!macroend

!macro JOTADUO_REMOVE_CLI_PATH
  !insertmacro JOTADUO_UPDATE_CLI_PATH "Remove"
  ${If} $0 != 0
    DetailPrint "$(jotaduoCliPathUpdateFailed)"
    DetailPrint "$1"
  ${EndIf}
!macroend

Function JOTADUO_CLI_PATH_PAGE
  ${GetOptions} $CMDLINE "/NO_JOTADUO_PATH" $0
  ${IfNot} ${Errors}
    StrCpy $JotaDuoCliPathState 0
    Abort
  ${EndIf}

  ${GetOptions} $CMDLINE "/P" $0
  ${IfNot} ${Errors}
    StrCpy $JotaDuoCliPathState 1
    Abort
  ${EndIf}

  ${If} ${Silent}
    StrCpy $JotaDuoCliPathState 1
    Abort
  ${EndIf}

  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}

  !insertmacro MUI_HEADER_TEXT "$(jotaduoCliPathPageTitle)" "$(jotaduoCliPathPageSubtitle)"
  ${NSD_CreateLabel} 0 0 100% 28u "$(jotaduoCliPathPageDescription)"
  Pop $0
  ${NSD_CreateCheckbox} 0 44u 100% 12u "$(jotaduoCliPathCheckbox)"
  Pop $JotaDuoCliPathCheckbox

  ${If} $JotaDuoCliPathState == 0
    SendMessage $JotaDuoCliPathCheckbox ${BM_SETCHECK} 0 0
  ${Else}
    SendMessage $JotaDuoCliPathCheckbox ${BM_SETCHECK} 1 0
  ${EndIf}

  nsDialogs::Show
FunctionEnd

Function JOTADUO_CLI_PATH_PAGE_LEAVE
  ${NSD_GetState} $JotaDuoCliPathCheckbox $JotaDuoCliPathState
FunctionEnd

!macro JOTADUO_STOP_BACKEND_SIDECAR
  ; The Python backend is a Tauri sidecar, not a user-facing window. If it is
  ; left behind during update/uninstall, stop only the copy under $INSTDIR and
  ; wait for the PyInstaller backend bundle to release its file handles.
  ; The script is unpacked to NSIS' temporary plugin directory. Bypass is scoped
  ; to this unsigned local installer helper so user PowerShell policy is not
  ; permanently changed.
  InitPluginsDir
  File /oname=$PLUGINSDIR\jotaduo-stop-backend-sidecar.ps1 "..\..\..\..\nsis\stop-backend-sidecar.ps1"
  nsExec::ExecToStack `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\jotaduo-stop-backend-sidecar.ps1" -InstallDir "$INSTDIR"`
  Pop $0
  Pop $1
!macroend

!macro NSIS_HOOK_PREINSTALL
  !insertmacro JOTADUO_STOP_BACKEND_SIDECAR
!macroend

!macro NSIS_HOOK_POSTINSTALL
  !insertmacro JOTADUO_ADD_CLI_PATH_IF_SELECTED
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  !insertmacro JOTADUO_STOP_BACKEND_SIDECAR
  !insertmacro JOTADUO_REMOVE_CLI_PATH
!macroend
