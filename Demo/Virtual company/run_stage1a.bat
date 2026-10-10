@echo off
rem Thin wrapper: Stage 1a only. Extra args are forwarded.
rem Example: run_stage1a.bat --seed 11 --quarters 30

cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
if not exist "results" mkdir "results"
if not exist "checkpoints" mkdir "checkpoints"

set "SEED=42"
set "QUARTERS=30"

rem Allow overriding via env: set SEED=11 && run_stage1a.bat
if defined SANDBOX_SEED set "SEED=%SANDBOX_SEED%"
if defined SANDBOX_QUARTERS set "QUARTERS=%SANDBOX_QUARTERS%"

python "src\nowa_sandbox\run_sandbox.py" ^
  --config "configs\default_world.yaml" ^
  --stage 1a ^
  --seed %SEED% ^
  --quarters %QUARTERS% ^
  --no-stop-on-graduation ^
  --output "results\stage1a_seed%SEED%.json" ^
  --checkpoint "checkpoints\stage1a_seed%SEED%.ckpt" ^
  %*

exit /b %ERRORLEVEL%
