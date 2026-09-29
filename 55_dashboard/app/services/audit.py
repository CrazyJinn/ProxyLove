"""audit.py — 操作日志（jsonl 追加写，不入图库）。"""

from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # → 55_dashboard/
PROJECT_ROOT = ROOT.parent                   # 仓库根（audit/data 归 55_dashboard/data）
AUDIT_PATH = ROOT / "data" / "audit.jsonl"


def log(node_id: str, label: str, action: str, detail: str = "") -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "node_id": node_id,
        "label": label,
        "action": action,
        "detail": detail,
    }
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def tail(n: int = 100) -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    lines = AUDIT_PATH.read_text(encoding="utf-8").splitlines()
    out = []
    for ln in lines[-n:]:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out
