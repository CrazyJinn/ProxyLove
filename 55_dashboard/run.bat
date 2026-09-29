@echo off
rem Start 55_dashboard (FastAPI/uvicorn, http://localhost:8502). Double-click or run run.bat
setlocal
cd /d "%~dp0"

if not exist settings.json (
  echo [warn] settings.json not found - create it in 55_dashboard\ with neo4j_password first
)

where uv >nul 2>&1
if %errorlevel%==0 goto :uv

rem ---- pip fallback (no uv) ----
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo [error] failed to create .venv
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import fastapi" >nul 2>&1
if not %errorlevel%==0 (
  ".venv\Scripts\python.exe" -m pip install fastapi uvicorn jinja2 neo4j python-multipart pytest
)
echo Starting dashboard at http://localhost:8502 ...
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8502
pause
exit /b 0

:uv
uv sync --quiet
echo Starting dashboard at http://localhost:8502 ...
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8502
pause
exit /b 0
