@echo off

REM Step 1: Check if virtual environment exists, if not, create it
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Step 2: Activate the virtual environment
call .venv\Scripts\activate

REM Step 3: Install or verify uv
pip install uv

REM Step 4: Update dependencies with uv
uv sync

REM Step 5: Execute update_script.py
echo Running update_script.py...
python update_script.py

REM Step 6: Update dependencies with uv
uv sync

REM Step 7: Execute main.py
echo Running main.py...
python main.py

REM Step 8: Deactivate the virtual environment
deactivate

echo Process completed.