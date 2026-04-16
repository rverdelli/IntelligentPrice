@echo off
cd /d "%~dp0"

echo ==========================================
echo  Marchiol Pricing Cockpit
echo ==========================================
echo.

REM ── Backend ──────────────────────────────
echo [Backend] Avvio su http://localhost:8000 ...
cd backend

if not exist ".venv" (
    echo     Installazione dipendenze backend...
    where uv >nul 2>&1
    if %errorlevel% == 0 (
        uv sync --extra test
    ) else (
        python -m venv .venv
        call .venv\Scripts\activate.bat
        pip install -r requirements.txt
        goto start_backend
    )
)
call .venv\Scripts\activate.bat

:start_backend
start "Marchiol Backend" cmd /k "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
cd ..

REM ── Frontend ─────────────────────────────
echo [Frontend] Avvio su http://localhost:3000 ...
cd frontend

if not exist "node_modules" (
    echo     Installazione dipendenze frontend...
    pnpm install
)

start "Marchiol Frontend" cmd /k "pnpm run dev"
cd ..

REM ── Done ─────────────────────────────────
echo.
echo  Backend  → http://localhost:8000
echo  API docs → http://localhost:8000/docs
echo  Frontend → http://localhost:3000
echo.
timeout /t 3 >nul
start http://localhost:3000

echo Premi un tasto per chiudere questa finestra.
pause >nul
