"""hints.py 单测：门控逻辑 + 推进指令文本。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.hints import (
    chapter_ready,
    char_chain_hint,
    section_gate,
    scene_chain_hint,
)


def test_section_gate_ready():
    g = section_gate(11, True, 11, 48, 48)
    assert g["can_advance"] is False and g["blocker"] is None


def test_section_gate_pending_review():
    g = section_gate(11, True, 10, 0, 0)
    assert g["can_advance"] is False and "待审" in g["button"] and g["blocker"]


def test_section_gate_can_advance():
    g = section_gate(11, True, 11, 40, 48)
    assert g["can_advance"] is True and g["button"] == "推进此节"
    assert g["blocker"] == "行音频 40/48"


def test_section_gate_ch_not_approved():
    g = section_gate(10, False, None, 0, 0)
    assert g["can_advance"] is False and g["blocker"] == "章结构未批"


def test_section_gate_no_outline():
    g = section_gate(11, False, None, 0, 0)
    assert g["blocker"] == "提纲未就绪" and g["can_advance"] is True  # 可推提纲


def test_chapter_ready():
    ok = [{"ol_ok": True, "sc_ok": True, "lines_ok": 5, "lines_total": 5}]
    assert chapter_ready(11, ok) is True
    assert chapter_ready(10, ok) is False
    bad = [{"ol_ok": True, "sc_ok": True, "lines_ok": 3, "lines_total": 5}]
    assert chapter_ready(11, bad) is False
    zero_lines = [{"ol_ok": True, "sc_ok": True, "lines_ok": 0, "lines_total": 0}]
    assert chapter_ready(11, zero_lines) is True


def test_char_chain_hint():
    # 全就绪
    h = char_chain_hint("陆择", 1, 1, 11, [{"name": "x", "status": 1}], [{"name": "d", "status": 11}])
    assert "就绪" in h
    # 有缺口
    h = char_chain_hint("江烈", 1, 1, 0, [{"name": "x", "status": 1}], [{"name": "d", "status": 0}])
    assert "char-design" in h and "江烈" in h
    # 声音待审
    h = char_chain_hint("江烈", 1, 1, 10, [{"name": "x", "status": 1}], [{"name": "d", "status": 11}])
    assert "审批中心" in h


def test_scene_chain_hint():
    # BGM 等归档
    s = {"status": 1, "layers": [], "bgm": {"status": 1, "name": "床帘"}}
    h = scene_chain_hint("出租屋", [s])
    assert "13_BGM" in h
    # 全就绪
    s2 = {"status": 1, "layers": [{"status": 11}], "bgm": {"status": 2, "name": "x"}}
    assert "就绪" in scene_chain_hint("酒店", [s2])
