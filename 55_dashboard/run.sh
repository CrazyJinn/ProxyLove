#!/usr/bin/env bash
# 启动 55_dashboard（FastAPI/uvicorn，http://localhost:8502）。用法：bash run.sh
set -e
cd "$(dirname "$0")"

if [ ! -f settings.json ]; then
  echo "⚠ 缺少 55_dashboard/settings.json（含 neo4j_password 等配置），请先创建" >&2
fi

if command -v uv >/dev/null 2>&1; then
  uv sync --quiet   # 按 uv.lock 建 .venv（含 dev 组 pytest）
  exec uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8502
fi

# pip 兜底（无 uv）
if [ ! -x ".venv/Scripts/python.exe" ] && [ ! -x ".venv/bin/python" ]; then
  python -m venv .venv
fi
if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"; else PY=".venv/bin/python"; fi
if ! "$PY" -c "import fastapi" >/dev/null 2>&1; then
  "$PY" -m pip install fastapi uvicorn jinja2 neo4j python-multipart pytest
fi
exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8502
