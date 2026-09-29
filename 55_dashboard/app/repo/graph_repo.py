"""graph_repo.py — 图数据库访问层（Memgraph via neo4j driver）。

连接约定与 cypher_exec.py 一致：bolt://127.0.0.1:7687，user neo4j，
密码来自 settings.json: neo4j_password / NEO4J_PASSWORD 环境变量。
本机 Memgraph 无密码——空密码也放行连接（与 cypher_exec 的区别：
cypher_exec 硬性要求非空密码，这里空串直接 auth=None）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[2]      # → 55_dashboard/
PROJECT_ROOT = ROOT.parent                      # 仓库根 = 产物根（镜像代恋项目结构）
SETTINGS_PATH = ROOT / "settings.json"          # 55_dashboard/settings.json


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return {}


def get_client():
    s = load_settings()
    uri = os.environ.get("NEO4J_URI", s.get("neo4j_uri", "bolt://127.0.0.1:7687"))
    user = os.environ.get("NEO4J_USER", s.get("neo4j_user", "neo4j"))
    password = os.environ.get("NEO4J_PASSWORD", s.get("neo4j_password", ""))
    return GraphRepo(uri, user, password)


class GraphRepo:
    """薄封装：参数化查询 + 写事务；页面层唯一图入口。"""

    def __init__(self, uri: str, user: str, password: str):
        auth = (user, password) if password else None
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── 读 ──
    def run(self, cypher: str, params: dict | None = None) -> list[dict]:
        with self.driver.session() as sess:
            return [dict(r) for r in sess.run(cypher, params or {})]

    # ── 写（返回 neo4j Counters 的 dict 形式）──
    def run_write(self, cypher: str, params: dict | None = None) -> dict:
        with self.driver.session() as sess:
            rec = sess.execute_write(
                lambda tx: tx.run(cypher, params or {}).consume()
            )
            c = rec.counters
            return {
                "nodes_created": c.nodes_created,
                "nodes_deleted": c.nodes_deleted,
                "relationships_created": c.relationships_created,
                "relationships_deleted": c.relationships_deleted,
                "properties_set": c.properties_set,
            }

    def run_write_many(self, cyphers: list[str]) -> list[dict]:
        """单事务顺序执行多条写语句（导入场景）。"""
        def _tx(tx):
            out = []
            for c in cyphers:
                summary = tx.run(c).consume()
                ct = summary.counters
                out.append(
                    {
                        "nodes_created": ct.nodes_created,
                        "nodes_deleted": ct.nodes_deleted,
                        "relationships_created": ct.relationships_created,
                        "relationships_deleted": ct.relationships_deleted,
                        "properties_set": ct.properties_set,
                    }
                )
            return out

        with self.driver.session() as sess:
            return sess.execute_write(_tx)
