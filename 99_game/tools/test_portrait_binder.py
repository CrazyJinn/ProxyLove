"""portrait_binder 纯函数单测（build_candidates / build_actions）——不连 Neo4j。

candidates/apply 的图查询与写图经 monkeypatch 替换；split 主流程端到端验证见 E2E。
Event 驱动化：IllusDesign 解析改 `Section→includes→Event→refines→SubEvent→anchored_at→Scene`
的事件 `→appears_as` 单路直读；apply 不再补建 depicts/ref_style。
在 99_game/tools 下跑：python -m pytest test_portrait_binder.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "skills"
                        / "section-voice-publisher" / "scripts"))
import portrait_binder as pb  # noqa: E402


SEC = "SecAAA"
HEAD = {"sc_id": "SC1", "scene_blocks": [{"block": "s00_酒店", "scene_name": "酒店-客房"}]}
LINES = [
    {"node_id": "L1", "who": "陆择", "block": "s00_酒店", "text": "第一句", "status": 0,
     "current_stand": None},
    {"node_id": "L2", "who": "陆择", "block": "s00_酒店", "text": "第二句", "status": -1,
     "current_stand": "S9"},
]


class _FakeGen:
    def __init__(self):
        self._n = 0

    def next_id_base62(self):
        self._n += 1
        return f"NEW{self._n}"


@pytest.fixture
def base(monkeypatch):
    """固定头信息 / 待判行，收集写图语句。返回 (captured_stmts, monkeypatch)。"""
    monkeypatch.setattr(pb, "fetch_section_head", lambda sid: HEAD)
    monkeypatch.setattr(pb, "judgeable_lines", lambda sid: [dict(l) for l in LINES])
    captured = {"stmts": None, "called": False}

    def fake_multi(stmts):
        captured["stmts"] = stmts
        captured["called"] = True

    monkeypatch.setattr(pb, "_run_cypher_multi", fake_multi)
    monkeypatch.setattr(pb, "_scene_names_of", lambda ids: {"s00_酒店": "酒店-客房"})
    monkeypatch.setattr(pb, "_GEN", _FakeGen())
    return captured, monkeypatch


# ── resolve_illus：appears_as 单路直读与决定性 ──

def test_resolve_illus_single_hit(monkeypatch):
    monkeypatch.setattr(pb, "_run_cypher", lambda c: [{"illus_id": "I1"}])
    warnings = []
    assert pb.resolve_illus(SEC, "酒店-客房", "陆择", warnings) == ("I1", "appears_as")
    assert not warnings


def test_resolve_illus_query_shape(monkeypatch):
    """查询必须沿 includes→refines→SubEvent→anchored_at→Scene + appears_as 经着装链限定。"""
    seen = {}

    def fake(cypher):
        seen["cypher"] = cypher
        return []

    monkeypatch.setattr(pb, "_run_cypher", fake)
    pb.resolve_illus(SEC, "酒店-客房", "陆择", [])
    c = seen["cypher"]
    assert "-[:includes]->(e:Event)" in c
    assert "-[:refines]->(sub:SubEvent)" in c
    assert "-[:anchored_at]->(scn:Scene)" in c
    assert "WHERE scn.name = " in c                     # 块名过滤（scene_name 非空时）
    assert "-[:appears_as]->(il:IllusDesign)" in c
    assert "<-[:outfit_for]-(:CostumeStyle)<-[:has_costume]-(c0)" in c


def test_resolve_illus_scene_name_empty_degrades(monkeypatch):
    """scene_blocks 缺块定义（scene_name 空）→ 不按块名过滤，退化为节内全部事件。"""
    seen = {}

    def fake(cypher):
        seen["cypher"] = cypher
        return [{"illus_id": "I1"}]

    monkeypatch.setattr(pb, "_run_cypher", fake)
    assert pb.resolve_illus(SEC, "", "陆择", []) == ("I1", "appears_as")
    assert "WHERE scn.name" not in seen["cypher"]


def test_resolve_illus_multiple_takes_lexicographic_first(monkeypatch):
    monkeypatch.setattr(pb, "_run_cypher", lambda c: [
        {"illus_id": "B2"}, {"illus_id": "A1"}])
    warnings = []
    assert pb.resolve_illus(SEC, "x", "y", warnings) == ("A1", "appears_as")
    assert any("多个" in w for w in warnings)          # 歧义记 warning，结果决定性


def test_resolve_illus_scene_miss_warns(monkeypatch):
    monkeypatch.setattr(pb, "_run_cypher", lambda c: [])
    warnings = []
    assert pb.resolve_illus(SEC, "不存在的场景", "陆择", warnings) == ("", "")
    assert any("未命中" in w or "无 anchored_at" in w for w in warnings)


def test_resolve_illus_all_empty(monkeypatch):
    monkeypatch.setattr(pb, "_run_cypher", lambda c: [{"illus_id": None}])
    assert pb.resolve_illus(SEC, "", "y", []) == ("", "")


# ── build_candidates ──

def test_build_candidates_pool_structure(monkeypatch):
    monkeypatch.setattr(pb, "fetch_section_head", lambda sid: HEAD)
    monkeypatch.setattr(pb, "judgeable_lines", lambda sid: [dict(l) for l in LINES])
    monkeypatch.setattr(pb, "_scene_names_of", lambda ids: {"s00_酒店": "酒店-客房"})
    monkeypatch.setattr(pb, "_effective_ds", lambda sid, who, w: None)   # 版本信息为展示项,隔离查询
    monkeypatch.setattr(pb, "resolve_illus",
                        lambda sid, scene, who, w: ("I1", "appears_as"))
    monkeypatch.setattr(pb, "stands_of_illus", lambda iid: [
        {"id": "S1", "variant_label": "慵懒", "status": 11, "description": "宿醉"}])
    data = pb.build_candidates(SEC)
    assert data["scenes"]["s00_酒店"]["scene_name"] == "酒店-客房"
    char = data["scenes"]["s00_酒店"]["chars"]["陆择"]
    assert char["illus_id"] == "I1" and char["illus_source"] == "appears_as"
    assert char["stands"][0]["variant_label"] == "慵懒"
    assert data["lines"][1]["current_stand"] == "S9"     # 重配句参考上轮选绘
    assert not data["warnings"]


def test_build_candidates_no_illus_warns(monkeypatch):
    monkeypatch.setattr(pb, "fetch_section_head", lambda sid: HEAD)
    monkeypatch.setattr(pb, "judgeable_lines", lambda sid: [dict(l) for l in LINES])
    monkeypatch.setattr(pb, "_scene_names_of", lambda ids: {"s00_酒店": "酒店-客房"})
    monkeypatch.setattr(pb, "_effective_ds", lambda sid, who, w: None)
    monkeypatch.setattr(pb, "resolve_illus", lambda sid, scene, who, w: ("", ""))
    monkeypatch.setattr(pb, "stands_of_illus", lambda iid: [])
    data = pb.build_candidates(SEC)
    char = data["scenes"]["s00_酒店"]["chars"]["陆择"]
    assert char["stands"] == [] and char["illus_id"] == ""
    assert any("无着装" in w for w in data["warnings"])


# ── apply：校验前置（不写图） ──

def test_apply_missing_stand_fails_before_write(base):
    captured, mp = base
    tasks = {"陆择": [{"node_id": "L1", "key": "k", "text": "第一句", "scene_id": "s00_酒店"}]}
    with pytest.raises(ValueError, match="缺 stand"):
        pb.build_actions(SEC, tasks, [])
    assert not captured["called"]                        # 未写图


def test_apply_unknown_stand_id_fails(base):
    captured, mp = base
    mp.setattr(pb, "_lookup_stand", lambda sid: {})
    tasks = {"陆择": [{"node_id": "L1", "stand": "GHOST", "text": "x", "scene_id": "s00_酒店"}]}
    with pytest.raises(ValueError, match="不存在"):
        pb.build_actions(SEC, tasks, [])
    assert not captured["called"]


def test_apply_line_not_in_section_fails(base):
    captured, _ = base
    tasks = {"陆择": [{"node_id": "OTHER", "stand": "S1", "text": "x", "scene_id": "s00_酒店"}]}
    with pytest.raises(ValueError, match="不属于本节"):
        pb.build_actions(SEC, tasks, [])
    assert not captured["called"]


# ── apply：建边语句（不建 depicts/ref_style） ──

def test_apply_existing_stand_builds_uses_edge(base):
    captured, mp = base
    mp.setattr(pb, "_lookup_stand",
               lambda sid: {"id": sid, "variant_label": "慵懒", "illus_id": "I1"})
    mp.setattr(pb, "resolve_illus", lambda sid, scene, who, w: ("I1", "appears_as"))
    tasks = {"陆择": [{"node_id": "L1", "stand": "S1", "text": "第一句", "scene_id": "s00_酒店"}]}
    stmts, report = pb.build_actions(SEC, tasks, [])
    joined = "\n".join(stmts)
    assert "DELETE o" in joined and "MERGE (l)-[u:uses]->" in joined and "u.sync=false" in joined
    assert "MERGE (st:StandingIllustration" not in joined      # 复用不建节点
    assert "depicts" not in joined and "ref_style" not in joined  # 边已废止，不再补建
    assert report["counts"]["lines_bound"] == 1 and report["counts"]["new_variants"] == 0


def test_apply_new_variant_creates_node_and_edges(base):
    captured, mp = base
    mp.setattr(pb, "resolve_illus", lambda sid, scene, who, w: ("I1", "appears_as"))
    mp.setattr(pb, "_find_existing_stand", lambda iid, label: None)
    tasks = {"陆择": [{"node_id": "L1", "text": "第一句", "scene_id": "s00_酒店",
                       "stand": {"variant_label": "赧然", "description": "被戳穿后强撑镇定"}}]}
    stmts, report = pb.build_actions(SEC, tasks, [])
    joined = "\n".join(stmts)
    assert "MERGE (st:StandingIllustration" in joined and "st.status=0" in joined
    assert "st.variant_label='赧然'" in joined and "st.description='被戳穿后强撑镇定'" in joined
    assert "MERGE (i)-[e:expands_to]->" in joined and "e.variant_label='赧然'" in joined
    assert "MERGE (l)-[u:uses]->" in joined and "u.sync=false" in joined
    assert "ref_style" not in joined                       # 语言风格边已删
    assert "depicts" not in joined
    assert report["counts"]["new_variants"] == 1
    assert report["new_variants"][0]["variant_label"] == "赧然"


def test_apply_new_variant_reuses_same_label(base):
    captured, mp = base
    mp.setattr(pb, "resolve_illus", lambda sid, scene, who, w: ("I1", "appears_as"))
    mp.setattr(pb, "_find_existing_stand", lambda iid, label: "SEXIST")
    tasks = {"陆择": [{"node_id": "L1", "text": "第一句", "scene_id": "s00_酒店",
                       "stand": {"variant_label": "赧然", "description": "氛围"}}]}
    stmts, report = pb.build_actions(SEC, tasks, [])
    joined = "\n".join(stmts)
    assert "MERGE (st:StandingIllustration" not in joined      # 已有同 label → 复用
    assert "SEXIST" in joined                                   # uses 边指向已有节点
    assert report["counts"]["reused_variants"] == 1 and report["counts"]["new_variants"] == 0


def test_apply_same_label_two_lines_one_node(base):
    """两句都提同 label 新变体 → 只建一次节点，两行 uses 指向同一 stand。"""
    captured, mp = base
    mp.setattr(pb, "resolve_illus", lambda sid, scene, who, w: ("I1", "appears_as"))
    mp.setattr(pb, "_find_existing_stand", lambda iid, label: None)
    tasks = {"陆择": [
        {"node_id": "L1", "text": "第一句", "scene_id": "s00_酒店",
         "stand": {"variant_label": "赧然", "description": "氛围"}},
        {"node_id": "L2", "text": "第二句", "scene_id": "s00_酒店",
         "stand": {"variant_label": "赧然", "description": "氛围"}}]}
    stmts, report = pb.build_actions(SEC, tasks, [])
    joined = "\n".join(stmts)
    assert joined.count("MERGE (st:StandingIllustration") == 1          # 建节点仅一次
    assert joined.count("MERGE (l)-[u:uses]->") == 2                     # 两行各一条 uses
    assert report["counts"]["new_variants"] == 1 and report["counts"]["lines_bound"] == 2
