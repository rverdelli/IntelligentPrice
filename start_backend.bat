@echo off
cd /d "%~dp0backend"

if not exist ".venv" (
    echo [1/2] Virtual environment non trovato, installo dipendenze...

    where uv >nul 2>&1
    if %errorlevel% == 0 (
        echo     usando uv...
        uv sync --extra test
    ) else (
        echo     uv non trovato, uso pip...
        python -m venv .venv
        call .venv\Scripts\activate.bat
        pip install -r requirements.txt
        goto start
    )
)

call .venv\Scripts\activate.bat

:start
echo [2/2] Avvio backend Marchiol Pricing su http://localhost:8000
echo       Premi Ctrl+C per fermare.
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
