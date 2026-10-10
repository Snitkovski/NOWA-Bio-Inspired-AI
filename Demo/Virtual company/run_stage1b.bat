@echo off
rem Thin wrapper: Stage 1b with non-regression baseline.
rem Example: set SANDBOX_SEED=11 && run_stage1b.bat

cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
if not exist "results" mkdir "results"
if not exist "checkpoints" mkdir "checkpoints"

set "SEED=42"
set "QUARTERS=20"
set "BASELINE=results\stage_1a_baseline.json"

if defined SANDBOX_SEED set "SEED=%SANDBOX_SEED%"
if defined SANDBOX_QUARTERS set "QUARTERS=%SANDBOX_QUARTERS%"
if defined SANDBOX_BASELINE set "BASELINE=%SANDBOX_BASELINE%"

if not exist "%BASELINE%" (
    echo ERROR: baseline not found: %BASELINE%
    echo Create one with:
    echo   python src\nowa_sandbox\stage1a_report.py results\stage1a_seed*.json --write-baseline results\stage_1a_baseline.json
    echo Or pass a graduated Stage 1a result JSON via SANDBOX_BASELINE.
    exit /b 1
)

python "src\nowa_sandbox\run_sandbox.py" ^
  --config "configs\default_world.yaml" ^
  --stage 1b ^
  --baseline-from "%BASELINE%" ^
  --seed %SEED% ^
  --quarters %QUARTERS% ^
  --no-stop-on-graduation ^
  --output "results\stage1b_seed%SEED%.json" ^
  --checkpoint "checkpoints\stage1b_seed%SEED%.ckpt" ^
  %*

exit /b %ERRORLEVEL%
