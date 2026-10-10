@echo off
setlocal EnableExtensions

rem NOWA Body Layer Lab — Phase 1 MockMCP GUI
rem Tick / approve / inspect memory and sleep.

cd /d "%~dp0"
set "DEMO_ROOT=%CD%"
set "PYTHONPATH=%DEMO_ROOT%\src;%PYTHONPATH%"

if not exist "results" mkdir "results"

echo.
echo ============================================
echo   NOWA Body Layer Lab
echo   Demo: %DEMO_ROOT%
echo ============================================
echo.

python -m nowa_body.gui_app %*
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" (
    echo.
    echo [Body Lab] Failed with exit code %ERR%.
    pause
)
exit /b %ERR%
