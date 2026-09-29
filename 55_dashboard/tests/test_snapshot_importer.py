"""导入器纯逻辑单测（不连真库）：解析、类型转换、Cypher 生成、幂等语句形态。"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.snapshot_importer import (
    _coerce,
    build_cypher,
    parse_snapshot,
)

REAL_CSV = Path("/home/ubuntu/all-cooper/图数据库/ProxyLove_backup_20260926_213710.csv")


def make_csv(tmp_path, rows):
    p = tmp_path / "snap.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return p


# ── _coerce ──

def test_coerce_types():
    assert _coerce("") is None
    assert _coerce("true") is True
    assert _coerce("false") is False
    assert _coerce("11") == 11 and isinstance(_coerce("11"), int)
    assert _coerce("-1") == -1
    assert _coerce("0.86") == 0.86
    assert _coerce("陆择") == "陆择"
    assert _coerce("1.0.0") == "1.0.0"  # 多点非 float


# ── 解析：小样本 ──

MINI = [
    ["_id", "_labels", "id", "name", "status", "_start", "_end", "_type", "sync", "order"],
    ["0", ":Character", "N1", "陆择", "11", "", "", "", "", ""],
    ["1", ":Location", "N2", "酒店", "", "", "", "", "", ""],
    ["", "", "", "", "", "0", "1", "at", "true", ""],
]


def test_parse_mini(tmp_path):
    nodes, edges = parse_snapshot(make_csv(tmp_path, MINI))
    assert len(nodes) == 2 and len(edges) == 1
    assert nodes[0]["labels"] == ["Character"]
    assert nodes[0]["props"]["name"] == "陆择"
    assert nodes[0]["props"]["status"] == 11
    assert nodes[0]["props"]["id"] == "N1"  # 用属性列雪花 id，非 CSV 行号
    e = edges[0]
    assert e["type"] == "at" and e["start_id"] == "N1" and e["end_id"] == "N2"
    assert e["props"] == {"sync": True}


def test_parse_rejects_dangling_edge(tmp_path):
    bad = [
        ["_id", "_labels", "id", "name", "_start", "_end", "_type"],
        ["0", ":Character", "N1", "a", "", "", ""],
        ["", "", "", "", "0", "99", "at"],  # 99 不存在
    ]
    try:
        parse_snapshot(make_csv(tmp_path, bad))
        assert False, "应抛 ValueError"
    except ValueError as exc:
        assert "不存在" in str(exc)


def test_parse_rejects_missing_snowflake_id(tmp_path):
    bad = [
        ["_id", "_labels", "id", "name", "_start", "_end", "_type"],
        ["0", ":Character", "", "a", "", "", ""],
    ]
    try:
        parse_snapshot(make_csv(tmp_path, bad))
        assert False, "应抛 ValueError（缺雪花 id）"
    except ValueError as exc:
        assert "雪花 id" in str(exc)


# ── Cypher 生成 ──

def test_build_cypher_mini(tmp_path):
    nodes, edges = parse_snapshot(make_csv(tmp_path, MINI))
    stmts = build_cypher(nodes, edges)
    assert len(stmts) == 3
    assert stmts[0].startswith("MERGE (n:Character {id: 'N1'})")
    assert "n.status = 11" in stmts[0]
    assert "MERGE (n:Location {id: 'N2'})" in stmts[1]
    assert stmts[2].startswith("MATCH (a {id: 'N1'}), (b {id: 'N2'})")
    assert "MERGE (a)-[r:at]->(b)" in stmts[2]
    assert "r.sync = true" in stmts[2]


def test_build_cypher_escapes_quotes():
    stmts = build_cypher(
        [{"labels": ["Character"], "props": {"id": "X1", "name": "O'Neil"}}], []
    )
    assert "O\\'Neil" in stmts[0]


def test_build_cypher_empty_props_no_set():
    # 只有 id 时：无额外属性 SET，仅 MERGE + SET id（幂等无害）
    stmts = build_cypher([{"labels": ["Info"], "props": {"id": "I1"}}], [])
    assert stmts[0] == "MERGE (n:Info {id: 'I1'}) SET n.id = 'I1'"


# ── 真实快照验收值 ──

def test_parse_real_snapshot():
    if not REAL_CSV.exists():
        import pytest
        pytest.skip("真实快照不在本机")
    nodes, edges = parse_snapshot(REAL_CSV)
    assert len(nodes) == 544
    assert len(edges) == 935
    # spot check：江烈 VoiceDesign 候选待选
    vd = [n for n in nodes if "VoiceDesign" in n["labels"] and n["props"].get("name") == "江烈声音设计"]
    assert vd and vd[0]["props"]["status"] == 10
    assert vd[0]["props"]["candidates_path"].endswith("candidates/candidates.json")


def test_real_snapshot_statuses():
    if not REAL_CSV.exists():
        import pytest
        pytest.skip("真实快照不在本机")
    nodes, _ = parse_snapshot(REAL_CSV)
    sts = {n["props"]["status"] for n in nodes if "status" in n["props"]}
    assert sts <= {-1, 0, 1, 2, 10, 11}
