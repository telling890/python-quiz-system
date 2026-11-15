@echo off
rem ===========================================================================
rem  Python Quiz System - one-click web launcher (Windows)
rem  Just double-click this file. All the logic lives in start_web.ps1
rem  (kept ASCII-only so cmd.exe never mangles Chinese text on any code page).
rem ===========================================================================
setlocal
cd /d "%~dp0"

where powershell >nul 2>nul
if errorlevel 1 (
  echo [ERROR] powershell not found. Use start_web.ps1 manually.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_web.ps1"
if errorlevel 1 pause
exit /b %errorlevel%
