"""exporter + cascade 纯逻辑测试（不连真库的部分用假 repo）。"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.cascade import extract_target_ids, is_write
from app.services.exporter import export_snapshot


class FakeRepo:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges

    def run(self, cypher, params=None):
        if "properties(n)" in cypher:
            return [
                {"id": n["id"], "labels": n["labels"], "props": n["props"]}
                for n in self.nodes
            ]
        if "type(r)" in cypher:
            return self.edges
        raise AssertionError(f"unexpected cypher: {cypher}")


def test_export_roundtrip_format(tmp_path):
    repo = FakeRepo(
        [
            {"id": "N1", "labels": ["Character"], "props": {"id": "N1", "name": "陆择", "status": 11}},
            {"id": "N2", "labels": ["Scene"], "props": {"id": "N2", "name": "酒店", "sync_flag": True}},
        ],
        [{"src": "N1", "dst": "N2", "type": "at", "props": {"sync": False, "type": "居住"}}],
    )
    out = tmp_path / "snap.csv"
    r = export_snapshot(repo, out)
    assert r["nodes"] == 2 and r["edges"] == 1
    rows = list(csv.reader(open(out, newline="", encoding="utf-8")))
    header = rows[0]
    assert header[0] == "_id" and header[1] == "_labels"
    assert "_start" in header and "_type" in header
    # bool 序列化
    i_flag = header.index("sync_flag")
    assert rows[2][i_flag] == "true"
    # 边行
    edge_row = rows[3]
    assert edge_row[header.index("_start")] == "0"
    assert edge_row[header.index("_end")] == "1"
    assert edge_row[header.index("_type")] == "at"
    assert edge_row[header.index("sync")] == "false"  # 边属性列
    # 可被导入器解析
    from app.services.snapshot_importer import parse_snapshot
    nodes, edges = parse_snapshot(out)
    assert len(nodes) == 2 and len(edges) == 1
    assert nodes[0]["props"]["name"] == "陆择"
    assert edges[0]["props"]["type"] == "居住"


def test_export_empty():
    repo = FakeRepo([], [])
    out = "/tmp/_never_written.csv"
    r = export_snapshot(repo, out)
    assert r["nodes"] == 0 and r["edges"] == 0
    Path(out).unlink(missing_ok=True)


def test_is_write():
    assert is_write("MATCH (n) SET n.x = 1")
    assert is_write("MERGE (n:X {id:'a'})")
    assert is_write("MATCH (n) DETACH DELETE n")
    assert not is_write("MATCH (n) RETURN n")
    assert not is_write("MATCH (n) WHERE n.id IS NOT NULL RETURN count(n)")


def test_extract_target_ids():
    ids = extract_target_ids("MATCH (n {id: 'ABC123'}) SET n.slug = '短发'")
    assert ids == ["ABC123"]
    ids = extract_target_ids("MATCH (n) WHERE n.id = 'X1' OR n.id = 'X2' SET n.x = 1")
    assert ids == ["X1", "X2"]
    assert extract_target_ids("MATCH (n:Character) RETURN n") == []
