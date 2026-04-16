@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo  Marchiol Pricing Cockpit
echo ==========================================
echo.

REM ── Verifica prerequisiti ────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo ERRORE: Python non trovato. Installa da https://python.org
    pause & exit /b 1
)
where node >nul 2>&1
if errorlevel 1 (
    echo ERRORE: Node.js non trovato. Installa da https://nodejs.org
    pause & exit /b 1
)

REM ── BACKEND ──────────────────────────────
echo [Backend] Controllo dipendenze...
cd backend

if not exist ".venv" (
    echo   Creazione virtual environment...
    python -m venv .venv
    echo   Installazione pacchetti ^(prima volta, aspetta^)...
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
) else (
    call .venv\Scripts\activate.bat
)

REM Ingest DB se non esiste
if not exist "..\data\marchiol.db" (
    echo   Creazione database da CSV...
    python ..\scripts\ingest.py --db ..\data\marchiol.db --raw ..\data\raw
)

echo   Avvio API su http://localhost:8000 ...
start "Marchiol Backend :8000" cmd /k "cd /d "%~dp0backend" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
cd ..

REM ── FRONTEND ─────────────────────────────
echo [Frontend] Controllo dipendenze...
cd frontend

if not exist "node_modules" (
    echo   Installazione pacchetti npm ^(prima volta, aspetta^)...
    where pnpm >nul 2>&1 && pnpm install || npm install
)

echo   Avvio UI su http://localhost:3000 ...
where pnpm >nul 2>&1 && (
    start "Marchiol Frontend :3000" cmd /k "cd /d "%~dp0frontend" && pnpm run dev"
) || (
    start "Marchiol Frontend :3000" cmd /k "cd /d "%~dp0frontend" && npm run dev"
)
cd ..

REM ── Apri browser ─────────────────────────
echo.
echo  Backend  ^-^> http://localhost:8000
echo  API docs ^-^> http://localhost:8000/docs
echo  Frontend ^-^> http://localhost:3000
echo.
echo  Aspetto 5 secondi e apro il browser...
timeout /t 5 >nul
start http://localhost:3000

echo Premi un tasto per chiudere questa finestra.
pause >nul
