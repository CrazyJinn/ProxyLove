"""cascade.py — sync 级联：影响预览（只读 BFS）+ 执行（下游 status → -1）。

规则（Schema总览）：人改节点属性时，沿 `sync=true` 出边把所有可达下游 status 重置 -1。
管理页的审批操作不触发级联；级联只由 Cypher 控制台确认写属性后执行。
"""

from __future__ import annotations


def sync_downstream(repo, node_id: str, cap: int = 200) -> list[dict]:
    """沿 sync=true 出边 BFS，返回将受影响的下游节点（不含起点）。"""
    visited = {node_id}
    frontier = [node_id]
    out: list[dict] = []
    while frontier and len(out) < cap:
        found = repo.run(
            """
            UNWIND $ids AS x
            MATCH (a {id:x})-[r]->(b)
            WHERE r.sync = true
            RETURN a.id AS aid, b.id AS bid, labels(b)[0] AS blabel,
                   coalesce(b.name, b.title, b.id) AS bname, b.status AS bst
            """,
            {"ids": frontier},
        )
        nxt = []
        for e in found:
            if e["bid"] in visited:
                continue
            visited.add(e["bid"])
            out.append({
                "id": e["bid"], "label": e["blabel"], "name": e["bname"],
                "status": e["bst"], "from": e["aid"],
            })
            nxt.append(e["bid"])
        frontier = nxt
    return out


def apply_cascade(repo, node_id: str) -> list[str]:
    """执行级联：下游有 status 的节点置 -1，返回受影响 id 列表。"""
    down = sync_downstream(repo, node_id)
    ids = [d["id"] for d in down]
    if ids:
        repo.run_write(
            """
            UNWIND $ids AS x
            MATCH (n {id:x})
            WHERE n.status IS NOT NULL
            SET n.status = -1
            """,
            {"ids": ids},
        )
    return ids


def execute_with_cascade(repo, cypher: str, confirm_cascade: bool) -> dict:
    """控制台写操作统一入口：执行语句 + 按语句目标做 sync 级联（与预览一致）。

    级联对象 = 语句中 {id:'…'} 提取到的全部目标节点；confirm_cascade=False 时
    若存在级联下游则拒绝执行（应由确认页先走预览）。
    """
    counters = repo.run_write(cypher)
    cascaded: list[str] = []
    for tid in extract_target_ids(cypher):
        cascaded.extend(apply_cascade(repo, tid))
    return {"counters": counters, "cascaded": cascaded}


# ── Cypher 控制台辅助 ──

import re

WRITE_KEYWORD_RE = re.compile(
    r"\b(SET|CREATE|MERGE|DELETE|REMOVE|DETACH|DROP|CALL)\b", re.IGNORECASE
)
TARGET_ID_RE = re.compile(
    r"\{\s*id\s*:\s*['\"]([^'\"]+)['\"]\s*\}|\bid\s*=\s*['\"]([^'\"]+)['\"]"
)


def is_write(cypher: str) -> bool:
    return bool(WRITE_KEYWORD_RE.search(cypher))


def extract_target_ids(cypher: str) -> list[str]:
    ids = []
    for m in TARGET_ID_RE.finditer(cypher):
        sid = m.group(1) or m.group(2)
        if sid and sid not in ids:
            ids.append(sid)
    return ids
