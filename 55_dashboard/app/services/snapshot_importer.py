"""snapshot_importer.py — Neo4j 风格 CSV 快照 → Memgraph 导入器（幂等 MERGE）。

快照格式（neo4j-admin export 的节点+边合一 CSV）：
  - 节点行：`_labels` 非空（如 ":Character"），后续列 = 节点属性列（全图属性列的并集）
  - 边行：  `_type` 非空，`_start`/`_end` 引用节点行的 `_id`（行号），边属性列在 `_type` 之后
  - 空串 = 无该属性

类型转换（仅按值形态，列名无关，快照已扫描确认无误伤）：
  "true"/"false" → bool；整数/小数字面量 → int/float；其余保持 str。

用法：
  CLI:  uv run python -m app.services.snapshot_importer <csv路径> [--wipe]
  模块: from app.services.snapshot_importer import import_snapshot
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Any

INT_RE = re.compile(r"^-?\d+$")
FLOAT_RE = re.compile(r"^-?\d+\.\d+$")


def _coerce(value: str) -> Any:
    """字符串 → 属性值。空串转 None（表示删除该属性，配合 SET n += 前的排除）。"""
    if value == "":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if INT_RE.match(value):
        # 保留 id 为字符串（雪花 Base62 可能恰好全数字，且 id 语义就是 string）
        return int(value)
    if FLOAT_RE.match(value):
        return float(value)
    return value


def parse_snapshot(csv_path: str | Path) -> tuple[list[dict], list[dict]]:
    """解析快照 → (nodes, edges)。

    node: {labels: [str], props: {列名: 值}}，含 _csv_id
    edge: {type: str, start_csv_id: str, end_csv_id: str, props: {}}
    """
    csv_path = Path(csv_path)
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        i_id = header.index("_id")
        i_labels = header.index("_labels")
        i_start = header.index("_start")
        i_end = header.index("_end")
        i_type = header.index("_type")
        node_prop_cols = list(range(i_labels + 1, i_start))
        edge_prop_cols = list(range(i_type + 1, len(header)))

        nodes: list[dict] = []
        edges: list[dict] = []
        csvid_to_id: dict[str, str] = {}
        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue
            if row[i_labels].strip():
                labels = [s for s in row[i_labels].strip().lstrip(":").split(":") if s]
                if not labels:
                    raise ValueError(f"节点行 _labels 格式异常: {row[:3]}")
                props = {
                    header[i]: _coerce(row[i])
                    for i in node_prop_cols
                    if i < len(row) and row[i] != ""
                }
                # 真正的节点 id 是属性列 id（雪花 Base62）；CSV _id 仅是行号，
                # 边的 _start/_end 引用它。id 恒为字符串（跳过类型转换）。
                if not props.get("id"):
                    raise ValueError(f"节点缺雪花 id 属性（CSV _id={row[i_id]}）")
                props["id"] = str(props["id"])
                csvid_to_id[row[i_id]] = props["id"]
                nodes.append({"labels": labels, "props": props, "csv_id": row[i_id]})
            elif row[i_type].strip():
                props = {
                    header[i]: _coerce(row[i])
                    for i in edge_prop_cols
                    if i < len(row) and row[i] != ""
                }
                edges.append(
                    {
                        "type": row[i_type].strip(),
                        "start_csv_id": row[i_start],
                        "end_csv_id": row[i_end],
                        "props": props,
                    }
                )

        for e in edges:
            if e["start_csv_id"] not in csvid_to_id or e["end_csv_id"] not in csvid_to_id:
                raise ValueError(
                    f"边引用的节点 _id 不存在: {e['type']} {e['start_csv_id']}->{e['end_csv_id']}"
                )
            e["start_id"] = csvid_to_id[e["start_csv_id"]]
            e["end_id"] = csvid_to_id[e["end_csv_id"]]
        return nodes, edges


# ── Cypher 生成 ────────────────────────────────────────────────

def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _cypher_literal(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return f"'{_esc(v)}'"


def build_cypher(nodes: list[dict], edges: list[dict]) -> list[str]:
    """生成按依赖排序的语句序列（先节点后边；内层先子句后语句）。"""
    stmts: list[str] = []
    for n in nodes:
        label = ":" + ":".join(n["labels"])
        sets = ", ".join(
            f"n.{k} = {_cypher_literal(v)}" for k, v in n["props"].items() if v is not None
        )
        stmts.append(f"MERGE (n{label} {{id: '{_esc(n['props']['id'])}'}}) " + (f"SET {sets}" if sets else ""))
    for e in edges:
        # 快照已验证无 (type,start,end) 平行边 → MERGE 裸类型边足够；sync 等属性 SET 补齐
        sets = ", ".join(f"r.{k} = {_cypher_literal(v)}" for k, v in e["props"].items() if v is not None)
        stmts.append(
            f"MATCH (a {{id: '{_esc(e['start_id'])}'}}), (b {{id: '{_esc(e['end_id'])}'}}) "
            f"MERGE (a)-[r:{e['type']}]->(b) " + (f"SET {sets}" if sets else "")
        )
    return stmts


def import_snapshot(client, csv_path: str | Path, wipe: bool = False, batch_size: int = 200) -> dict:
    """导入快照到图库。幂等（按 id MERGE；重复导入零新增）。

    wipe=True 先清空全库（MATCH (n) DETACH DELETE n）。
    返回 {nodes, edges, created, statements}。
    """
    nodes, edges = parse_snapshot(csv_path)
    if wipe:
        client.run("MATCH (n) DETACH DELETE n")

    stmts = build_cypher(nodes, edges)
    created = 0
    for i in range(0, len(stmts), batch_size):
        batch = stmts[i : i + batch_size]
        for summary in client.run_write_many(batch):
            created += (summary.get("nodes_created") or 0) + (summary.get("relationships_created") or 0)
    return {"nodes": len(nodes), "edges": len(edges), "created": created, "statements": len(stmts)}


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python -m app.services.snapshot_importer <csv> [--wipe]", file=sys.stderr)
        return 2
    csv_arg = sys.argv[1]
    wipe = "--wipe" in sys.argv[2:]

    from app.repo.graph_repo import get_client

    result = import_snapshot(get_client(), csv_arg, wipe=wipe)
    print(
        f"导入完成: 节点 {result['nodes']} / 边 {result['edges']}，"
        f"实际新建 {result['created']}（语句 {result['statements']} 条）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
