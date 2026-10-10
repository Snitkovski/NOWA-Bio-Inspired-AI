@echo off
setlocal EnableExtensions

rem NOWA Procurement Sandbox — full laboratory GUI
rem Soft-stop between quarters; sweep / report / results browser.

cd /d "%~dp0"
set "DEMO_ROOT=%CD%"
set "PYTHONPATH=%DEMO_ROOT%\src;%PYTHONPATH%"

if not exist "results" mkdir "results"
if not exist "checkpoints" mkdir "checkpoints"

echo.
echo ============================================
echo   NOWA Procurement Sandbox Lab
echo   Demo: %DEMO_ROOT%
echo ============================================
echo.

python -m nowa_sandbox.gui_app %*
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" (
    echo.
    echo [Lab] Failed with exit code %ERR%.
    pause
)
exit /b %ERR%
