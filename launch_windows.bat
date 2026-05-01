@echo off
REM EDAO-NMS Onboarding Tool v2.6 — Windows launcher
REM Double-click this file to start the tool.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python not found. Install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

python edao_onboard.py
if %errorlevel% neq 0 (
    echo.
    echo The tool exited with an error. Press any key to close.
    pause
)
