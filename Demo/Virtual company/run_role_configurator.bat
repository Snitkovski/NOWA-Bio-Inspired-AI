@echo off
setlocal EnableExtensions

rem NOWA Role Configurator — visual layer over role_config.py
rem List / edit / validate / dry-run company roles.

cd /d "%~dp0"
set "DEMO_ROOT=%CD%"
set "PYTHONPATH=%DEMO_ROOT%\src;%PYTHONPATH%"

if not exist "results" mkdir "results"

echo.
echo ============================================
echo   NOWA Role Configurator
echo   Demo: %DEMO_ROOT%
echo ============================================
echo.

python -m nowa_body.gui_configurator %*
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" (
    echo.
    echo [Role Configurator] Failed with exit code %ERR%.
    pause
)
exit /b %ERR%
