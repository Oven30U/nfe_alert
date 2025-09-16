@echo off

REM Step 1: Check if virtual environment exists, if not, create it
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    pause
)

REM Step 2: Activate the virtual environment
call venv\Scripts\activate
pause

REM Step 3: Install or verify uv
pip install uv
pause

REM Step 4: Update dependencies with uv
uv sync
pause

REM Step 5: Execute update_script.py
echo Running update_script.py...
python update_script.py
pause

REM Step 6: Execute main.py
echo Running main.py...
python main.py
pause

REM Step 7: Deactivate the virtual environment
deactivate
pause

echo Process completed.