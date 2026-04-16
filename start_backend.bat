@echo off
cd /d "%~dp0backend"

if not exist ".venv" (
    echo [1/2] Virtual environment non trovato, installo dipendenze...
    uv sync --extra test
) else (
    echo [1/2] Virtual environment trovato.
)

call .venv\Scripts\activate.bat

echo [2/2] Avvio backend Marchiol Pricing su http://localhost:8000
echo       Premi Ctrl+C per fermare.
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
