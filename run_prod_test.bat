@echo off
REM Robust production runner for Task Scheduler / cron-like usage
REM - Always sync dependencies (uv sync)
REM - Run update_script.py and verify exit code before running main.py
REM - Produce timestamped logs and rotate old logs
REM - Manage venv creation if missing

setlocal enabledelayedexpansion

:: ========== CONFIG ==========
set "PROJECT_DIR=D:\PY_ARG_NFE_Alert"
set "VENV_DIR=%PROJECT_DIR%\.venv\Scripts"
set "VENV_PY=%VENV_DIR%\python.exe"
set "LOG_DIR=%PROJECT_DIR%\logs"
set "LOG_RETENTION_DAYS=30"
set "FORCE_UV_SYNC=1"    REM 1 = always run uv sync, 0 = skip
:: ============================

:: Ensure log dir
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%" 2>nul
)

:: Timestamp for log filenames (sanitized)
set "now=%date%_%time%"
set "now=%now::=-%"
set "now=%now:/=-%"
set "now=%now:.=-%"
set "now=%now: =_%"
set "now=%now:,=-%"

set "UPDATE_LOG=%LOG_DIR%\update_%now%.log"
set "MAIN_LOG=%LOG_DIR%\main_%now%.log"
set "RUN_LOG=%LOG_DIR%\run_prod_%now%.log"

echo [%date% %time%] Starting run_prod_copy.bat > "%RUN_LOG%"

:: Change to project dir (supports different drive letters)
cd /d "%PROJECT_DIR%" || (
    echo [%date% %time%] ERROR: Could not cd to %PROJECT_DIR% >> "%RUN_LOG%"
    exit /b 1
)

:: Create virtualenv if missing
if not exist "%PROJECT_DIR%\.venv" (
    echo [%date% %time%] .venv not found. Attempting to create... >> "%RUN_LOG%"
    REM Try using py launcher first, then system python
    py -3 -m venv "%PROJECT_DIR%\.venv" >> "%RUN_LOG%" 2>&1
    if errorlevel 1 (
        echo [%date% %time%] py launcher failed, trying system python -m venv >> "%RUN_LOG%"
        python -m venv "%PROJECT_DIR%\.venv" >> "%RUN_LOG%" 2>&1
    )
    if not exist "%VENV_PY%" (
        echo [%date% %time%] ERROR: Failed to create virtualenv at %PROJECT_DIR%\.venv >> "%RUN_LOG%"
        exit /b 2
    )
    echo [%date% %time%] Virtualenv created successfully. >> "%RUN_LOG%"
) else (
    echo [%date% %time%] Virtualenv exists. >> "%RUN_LOG%"
)

:: Basic check the venv python exists
if not exist "%VENV_PY%" (
    echo [%date% %time%] ERROR: venv python not found at %VENV_PY% >> "%RUN_LOG%"
    exit /b 3
)

:: Optional: upgrade pip and install uv (ensure uv present)
echo [%date% %time%] Ensuring pip and uv are installed... >> "%RUN_LOG%"
"%VENV_PY%" -m pip install --upgrade pip >> "%RUN_LOG%" 2>&1
if %FORCE_UV_SYNC% EQU 1 (
    "%VENV_PY%" -m pip install --upgrade uv >> "%RUN_LOG%" 2>&1
    echo [%date% %time%] Running uv sync (pre-update) ... >> "%RUN_LOG%"
    "%VENV_PY%" -m uv sync >> "%RUN_LOG%" 2>&1
    if errorlevel 1 (
        echo [%date% %time%] WARNING: uv sync (pre-update) returned non-zero. Continuing but check logs. >> "%RUN_LOG%"
    ) else (
        echo [%date% %time%] uv sync (pre-update) completed OK. >> "%RUN_LOG%"
    )
) else (
    echo [%date% %time%] Skipping uv sync (pre-update) by config. >> "%RUN_LOG%"
)

:: Run update_script.py and capture output & exit code
echo [%date% %time%] Running update_script.py ... >> "%RUN_LOG%"
"%VENV_PY%" "%PROJECT_DIR%\update_script.py" >> "%UPDATE_LOG%" 2>&1
set "UPDATE_EXIT=%ERRORLEVEL%"
echo [%date% %time%] update_script.py exit code: %UPDATE_EXIT% >> "%RUN_LOG%"

:: After update, sync dependencies again (optional)
if %FORCE_UV_SYNC% EQU 1 (
    echo [%date% %time%] Running uv sync (post-update) ... >> "%RUN_LOG%"
    "%VENV_PY%" -m uv sync >> "%RUN_LOG%" 2>&1
    if errorlevel 1 (
        echo [%date% %time%] WARNING: uv sync (post-update) returned non-zero. >> "%RUN_LOG%"
    ) else (
        echo [%date% %time%] uv sync (post-update) completed OK. >> "%RUN_LOG%"
    )
)

:: If update failed, do not run main.py
if not "%UPDATE_EXIT%"=="0" (
    echo [%date% %time%] update_script.py failed (exit %UPDATE_EXIT%). Skipping main.py >> "%RUN_LOG%"
    echo See logs: %UPDATE_LOG% >> "%RUN_LOG%"
    rem exit with update exit code
    endlocal
    exit /b %UPDATE_EXIT%
)

:: Run main.py and capture output
echo [%date% %time%] Running main.py ... >> "%RUN_LOG%"
"%VENV_PY%" "%PROJECT_DIR%\main.py" >> "%MAIN_LOG%" 2>&1
set "MAIN_EXIT=%ERRORLEVEL%"
echo [%date% %time%] main.py exit code: %MAIN_EXIT% >> "%RUN_LOG%"

:: Rotate / cleanup old logs (delete older than LOG_RETENTION_DAYS)
if defined LOG_RETENTION_DAYS (
    forfiles /p "%LOG_DIR%" /s /m *.log /d -%LOG_RETENTION_DAYS% /c "cmd /c del @path" 2>nul
)

echo [%date% %time%] Run finished. update exit=%UPDATE_EXIT% main exit=%MAIN_EXIT% >> "%RUN_LOG%"

endlocal
exit /b %MAIN_EXIT%