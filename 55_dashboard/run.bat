@echo off
rem 启动 55_dashboard（FastAPI/uvicorn，http://localhost:8502）。用法：双击或运行 run.bat
setlocal
cd /d "%~dp0"

if not exist settings.json (
  echo [warn] 缺少 55_dashboard\settings.json（含 neo4j_password 等配置），请先创建
)

where uv >nul 2>&1
if %errorlevel%==0 (
  uv sync --quiet
  uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8502
  goto :eof
)

rem pip 兜底（无 uv）
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo [error] .venv 创建失败
  exit /b 1
)
".venv\Scripts\python.exe" -c "import fastapi" >nul 2>&1
if not %errorlevel%==0 (
  ".venv\Scripts\python.exe" -m pip install fastapi uvicorn jinja2 neo4j python-multipart pytest
)
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8502
