@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem NOWA Procurement Sandbox launcher
rem Run from anywhere; always resolves to this demo folder.

cd /d "%~dp0"
set "DEMO_ROOT=%CD%"
set "PYTHONPATH=%DEMO_ROOT%\src;%PYTHONPATH%"

if not exist "results" mkdir "results"
if not exist "checkpoints" mkdir "checkpoints"

rem Pass-through mode: run_sandbox.bat --stage 1a --quarters 30 ...
if not "%~1"=="" (
    echo [Sandbox] Running with CLI args: %*
    echo.
    python "src\nowa_sandbox\run_sandbox.py" %*
    set "ERR=!ERRORLEVEL!"
    goto :done
)

echo.
echo ============================================
echo   NOWA Procurement Sandbox
echo   Demo: %DEMO_ROOT%
echo ============================================
echo.
echo   1^) Stage 1a  - rotating suppliers ^(trade school^)
echo   2^) Stage 1b  - persistent suppliers ^(internship^)
echo   3^) Stage 1a  - full 30-quarter run + checkpoint
echo   4^) Stage 1b  - 20 quarters from Stage 1a checkpoint
echo   5^) Summarize Stage 1a seed sweep / write baseline
echo   6^) Custom command ^(raw CLI flags^)
echo   0^) Exit
echo.
set /p "CHOICE=Select [0-6]: "

if "%CHOICE%"=="0" goto :eof
if "%CHOICE%"=="1" goto :stage1a_quick
if "%CHOICE%"=="2" goto :stage1b_quick
if "%CHOICE%"=="3" goto :stage1a_full
if "%CHOICE%"=="4" goto :stage1b_from_ckpt
if "%CHOICE%"=="5" goto :report
if "%CHOICE%"=="6" goto :custom

echo Unknown choice.
set "ERR=1"
goto :done

:stage1a_quick
set /p "SEED=Seed [default 42]: "
if "%SEED%"=="" set "SEED=42"
set /p "QUARTERS=Quarters [default 10]: "
if "%QUARTERS%"=="" set "QUARTERS=10"
set "OUT=results\stage1a_seed%SEED%.json"
set "CKPT=checkpoints\stage1a_seed%SEED%.ckpt"
echo.
echo [Stage 1a] seed=%SEED% quarters=%QUARTERS%
echo   output     %OUT%
echo   checkpoint %CKPT%
echo.
python "src\nowa_sandbox\run_sandbox.py" ^
  --config "configs\default_world.yaml" ^
  --stage 1a ^
  --seed %SEED% ^
  --quarters %QUARTERS% ^
  --no-stop-on-graduation ^
  --output "%OUT%" ^
  --checkpoint "%CKPT%"
set "ERR=!ERRORLEVEL!"
goto :done

:stage1b_quick
set /p "SEED=Seed [default 42]: "
if "%SEED%"=="" set "SEED=42"
set /p "QUARTERS=Quarters [default 10]: "
if "%QUARTERS%"=="" set "QUARTERS=10"
set /p "BASELINE=Baseline JSON [default results\stage_1a_baseline.json]: "
if "%BASELINE%"=="" set "BASELINE=results\stage_1a_baseline.json"
if not exist "%BASELINE%" (
    echo.
    echo ERROR: baseline not found: %BASELINE%
    echo Run option 5 after a graduated Stage 1a sweep, or point to a graduated Stage 1a result JSON.
    set "ERR=1"
    goto :done
)
set "OUT=results\stage1b_seed%SEED%.json"
set "CKPT=checkpoints\stage1b_seed%SEED%.ckpt"
echo.
echo [Stage 1b] seed=%SEED% quarters=%QUARTERS%
echo   baseline   %BASELINE%
echo   output     %OUT%
echo   checkpoint %CKPT%
echo.
python "src\nowa_sandbox\run_sandbox.py" ^
  --config "configs\default_world.yaml" ^
  --stage 1b ^
  --baseline-from "%BASELINE%" ^
  --seed %SEED% ^
  --quarters %QUARTERS% ^
  --no-stop-on-graduation ^
  --output "%OUT%" ^
  --checkpoint "%CKPT%"
set "ERR=!ERRORLEVEL!"
goto :done

:stage1a_full
set /p "SEED=Seed [default 42]: "
if "%SEED%"=="" set "SEED=42"
set "OUT=results\stage1a_seed%SEED%.json"
set "CKPT=checkpoints\stage1a_seed%SEED%.ckpt"
echo.
echo [Stage 1a full] 30 quarters, seed=%SEED%
echo   This usually takes 10-20 minutes.
echo.
python "src\nowa_sandbox\run_sandbox.py" ^
  --config "configs\default_world.yaml" ^
  --stage 1a ^
  --seed %SEED% ^
  --quarters 30 ^
  --no-stop-on-graduation ^
  --output "%OUT%" ^
  --checkpoint "%CKPT%"
set "ERR=!ERRORLEVEL!"
goto :done

:stage1b_from_ckpt
set /p "SEED=Stage 1a seed to resume from [default 42]: "
if "%SEED%"=="" set "SEED=42"
set /p "QUARTERS=Extra Stage 1b quarters [default 20]: "
if "%QUARTERS%"=="" set "QUARTERS=20"
set /p "BASELINE=Baseline JSON [default results\stage_1a_baseline.json]: "
if "%BASELINE%"=="" set "BASELINE=results\stage_1a_baseline.json"
set "RESUME=checkpoints\stage1a_seed%SEED%.ckpt"
set "OUT=results\stage1b_from_seed%SEED%.json"
set "CKPT=checkpoints\stage1b_from_seed%SEED%.ckpt"
if not exist "%RESUME%" (
    echo ERROR: Stage 1a checkpoint not found: %RESUME%
    set "ERR=1"
    goto :done
)
if not exist "%BASELINE%" (
    echo ERROR: baseline not found: %BASELINE%
    set "ERR=1"
    goto :done
)
echo.
echo [Stage 1b from checkpoint] resume=%RESUME%
echo   baseline %BASELINE%  quarters=%QUARTERS%
echo.
python "src\nowa_sandbox\run_sandbox.py" ^
  --config "configs\default_world.yaml" ^
  --stage 1b ^
  --baseline-from "%BASELINE%" ^
  --seed %SEED% ^
  --quarters %QUARTERS% ^
  --no-stop-on-graduation ^
  --resume-from "%RESUME%" ^
  --output "%OUT%" ^
  --checkpoint "%CKPT%"
set "ERR=!ERRORLEVEL!"
goto :done

:report
echo.
echo Summarizing results\stage1a_seed*.json ...
python "src\nowa_sandbox\stage1a_report.py" results\stage1a_seed*.json ^
  --write-baseline results\stage_1a_baseline.json
set "ERR=!ERRORLEVEL!"
goto :done

:custom
echo.
echo Example:
echo   --stage 1a --seed 7 --quarters 5 --output results\my_run.json
echo.
set /p "ARGS=Flags: "
python "src\nowa_sandbox\run_sandbox.py" --config "configs\default_world.yaml" %ARGS%
set "ERR=!ERRORLEVEL!"
goto :done

:done
echo.
if not defined ERR set "ERR=0"
if "!ERR!"=="0" (
    echo [Sandbox] Done.
) else (
    echo [Sandbox] Failed with exit code !ERR!.
)
echo.
pause
exit /b !ERR!
