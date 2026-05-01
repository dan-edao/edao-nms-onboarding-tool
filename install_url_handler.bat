@echo off
REM EDAO-NMS Onboarding Tool — one-time URL handler installer (Windows).
REM
REM Registers edaonms-proxy-onboard:// with the current Windows user
REM (HKCU — no admin rights required) so that clicking Deploy Now! /
REM Redeploy in the Control Hub launches launch_windows.bat. Run once
REM after extracting the folder. Safe to re-run.

setlocal

set "TOOL_DIR=%~dp0"
if "%TOOL_DIR:~-1%"=="\" set "TOOL_DIR=%TOOL_DIR:~0,-1%"
set "LAUNCHER=%TOOL_DIR%\launch_windows.bat"

if not exist "%LAUNCHER%" (
    echo launch_windows.bat was not found in this folder:
    echo   %TOOL_DIR%
    echo.
    echo Make sure you extracted the whole edao-nms-onboarding-tool folder.
    pause
    exit /b 1
)

REM Build the registry command value with proper escaping. cmd /c
REM ensures the .bat runs in its own window even when invoked via
REM ShellExecute from the browser.
set "CMD_VALUE=cmd /c \"\"%LAUNCHER%\" \"%%1\"\""

reg add "HKCU\Software\Classes\edaonms-proxy-onboard" /ve /t REG_SZ /d "URL:EDAO-NMS Proxy Onboard Protocol" /f >nul
reg add "HKCU\Software\Classes\edaonms-proxy-onboard" /v "URL Protocol" /t REG_SZ /d "" /f >nul
reg add "HKCU\Software\Classes\edaonms-proxy-onboard\shell" /ve /t REG_SZ /d "open" /f >nul
reg add "HKCU\Software\Classes\edaonms-proxy-onboard\shell\open\command" /ve /t REG_SZ /d "%CMD_VALUE%" /f >nul

if %errorlevel% neq 0 (
    echo.
    echo Registration failed. Try running this script as Administrator.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  EDAO-NMS Onboarding Tool URL handler registered.
echo ============================================================
echo  The Control Hub Deploy Now! button will now launch this tool
echo  automatically (your browser will ask for confirmation the
echo  first time).
echo.
echo  Launcher: %LAUNCHER%
echo  Scheme:   edaonms-proxy-onboard://
echo ============================================================
echo.
pause
endlocal
