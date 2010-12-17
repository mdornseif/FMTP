;--------------------------------
; Includes
;--------------------------------

!include "Library.nsh"
!include "MUI.nsh"

;--------------------------------
;General
;--------------------------------

Name "IPS Client"
OutFile "print_client_setup.exe"
InstallDir $PROGRAMFILES\IPSClient
InstallDirRegKey HKLM "Software\IPSClient" "Install_Dir"

;--------------------------------
; Pages
;--------------------------------

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages
;--------------------------------
 
!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; The stuff to install
;--------------------------------

Section ""

  SetOutPath $INSTDIR\gs
  File "C:\Program Files\gs\gs8.71\bin\*.*"
  File "C:\Program Files\gs\gs8.71\lib\*.*"
  File "C:\Program Files\Ghostgum\gsview\*.*"
  SetOutPath $INSTDIR\support
  File "dist\support\*.*"
  SetOutPath "$INSTDIR"
  File "dist\*.*"
  
  WriteRegStr HKLM SOFTWARE\IPSClient "Install_Dir" "$INSTDIR"
  
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\IPSClient" "DisplayName" "IPS Client"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\IPSClient" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\IPSClient" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\IPSClient" "NoRepair" 1
  WriteUninstaller "uninstall.exe"
  
SectionEnd


Section "Start Menu Shortcuts"

  CreateDirectory "$SMPROGRAMS\IPSClient"
  CreateShortCut "$SMPROGRAMS\IPSClient\printclient.lnk" "$INSTDIR\printclient.exe" "" "$INSTDIR\printclient.exe" 0
  CreateShortCut "$SMPROGRAMS\IPSClient\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
  
SectionEnd

;--------------------------------
; Uninstaller
;--------------------------------

Section "Uninstall"
  
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\IPSClient"
  DeleteRegKey HKLM SOFTWARE\IPSClient

  Delete "$SMPROGRAMS\IPSClient\*.*"
  RMDir /r "$SMPROGRAMS\IPSClient"
  
  Delete "$INSTDIR\support\*.*"
  RMDir "$INSTDIR\support"
  Delete "$INSTDIR\*.*"
  RMDir "$INSTDIR"

SectionEnd
