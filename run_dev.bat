@echo off

:: Define project and virtual environment directories (use absolute paths like dfe.bat)
set PROJECT_DIR="C:\Users\lmarinaro\Documents\dfe\DFEPW"
set VENV_DIR="%PROJECT_DIR%\\.venv\\Scripts"

:: Cambiar al directorio del proyecto
cd %PROJECT_DIR%

REM Step 1: Check if virtual environment exists, if not, create it
if not exist %PROJECT_DIR%\\.venv (
    echo Creating virtual environment...
    python -m venv %PROJECT_DIR%\\.venv
)

REM Step 2: Activate the virtual environment
call %VENV_DIR%\\activate

REM Step 3: Install or verify uv
%VENV_DIR%\\python.exe -m pip install uv

REM Step 4: Update dependencies with uv
%VENV_DIR%\\python.exe -m uv sync

REM Step 5: Execute update_script.py
echo Running update_script.py...
%VENV_DIR%\\python.exe %PROJECT_DIR%\\update_script.py

REM Step 6: Update dependencies with uv
%VENV_DIR%\\python.exe -m uv sync

REM Step 7: Execute main.py
echo Running main.py...
%VENV_DIR%\\python.exe %PROJECT_DIR%\\main.py

REM Step 8: Deactivate the virtual environment
call %VENV_DIR%\\deactivate

echo Process completed.