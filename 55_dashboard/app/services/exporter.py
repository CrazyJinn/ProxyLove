"""exporter.py — 当前图库 → Neo4j-admin 风格 CSV 快照（与导入器同格式，可回导）。

格式：`_id,_labels,<节点属性列…>,_start,_end,_type,<边属性列…>`
  节点行 = 行号索引 + ":Label"；边行引用行号。bool → true/false，None → 空串。
"""

from __future__ import annotations

import csv
import time
from pathlib import Path


def _cell(v) -> str:
    if v is None:
        return ""
    if v is True:
        return "true"
    if v is False:
        return "false"
    return str(v)


def export_snapshot(repo, out_path: str | Path) -> dict:
    nodes = repo.run(
        "MATCH (n) RETURN n.id AS id, labels(n) AS labels, properties(n) AS props ORDER BY id"
    )
    edges = repo.run(
        """
        MATCH (a)-[r]->(b)
        RETURN a.id AS src, b.id AS dst, type(r) AS type, properties(r) AS props
        """
    )
    node_prop_cols: list[str] = []
    for n in nodes:
        for k in n["props"]:
            if k not in node_prop_cols:
                node_prop_cols.append(k)
    node_prop_cols.sort()
    edge_prop_cols: list[str] = []
    for e in edges:
        for k in e["props"]:
            if k not in edge_prop_cols:
                edge_prop_cols.append(k)
    edge_prop_cols.sort()
    header = (
        ["_id", "_labels", *node_prop_cols, "_start", "_end", "_type", *edge_prop_cols]
    )
    i_labels = 2
    i_start = 2 + len(node_prop_cols)
    i_type = i_start + 2

    id_to_row: dict[str, str] = {}
    rows: list[list[str]] = []
    for idx, n in enumerate(nodes):
        id_to_row[n["id"]] = str(idx)
        row = [""] * len(header)
        row[0] = str(idx)
        row[1] = ":" + ":".join(n["labels"])
        for k, v in n["props"].items():
            row[i_labels + node_prop_cols.index(k)] = _cell(v)
        rows.append(row)
    n_edge_rows = 0
    for e in edges:
        row = [""] * len(header)
        row[i_start] = id_to_row[e["src"]]
        row[i_start + 1] = id_to_row[e["dst"]]
        row[i_type] = e["type"]
        for k, v in e["props"].items():
            row[i_type + 1 + edge_prop_cols.index(k)] = _cell(v)
        rows.append(row)
        n_edge_rows += 1

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return {"nodes": len(nodes), "edges": n_edge_rows, "path": str(out_path)}
