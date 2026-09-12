"""script_splitter 纯函数单测（parse_ink / align / assign_orders / build_actions）——不连 Neo4j。

split 主流程（查图/写图）不在单测范围（需真实库，端到端验证）。
在 99_game/tools 下跑：python -m pytest test_script_splitter.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "skills"
                        / "section-voice-publisher" / "scripts"))
import script_splitter as sp  # noqa: E402


def _g(op, text, *, who=None, order=0, status=11, nid="g",
       voice_key=None, sha=None, scene_block_id=None, kind=None, pos=None):
    """图行 dict（split 图查询返回形状）。"""
    return {"id": nid, "op": op, "who": who, "pos": pos,
            "text": text, "kind": kind, "scene_block_id": scene_block_id,
            "status": status, "attempts": 0, "voice_key": voice_key,
            "text_sha1": sha if sha is not None else sp.text_sha1(text or ""),
            "ord": order}


# ── parse_ink（台词.ink 方言 v2，标准合法 ink；md→ink 转换保真锚见 test_md_to_ink.py）──

INK = """// 酒店醒来

=== s00_hotel // 酒店-客房（清晨）

旁白:清晨，一缕阳光从窗帘缝隙钻进来。
陆择:嗯……等下还要赶飞机。

* 起床 -> get_up
+ 再睡一会 -> sleep_in
* 直接赶路 -> END // ending: BE

= get_up

顾盈:哟，醒这么早？

没赶上飞机。 # ending: BE
-> END
"""


def _write_ink(tmp_path, text=INK):
    p = tmp_path / "台词.ink"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_parse_ink_basic(tmp_path):
    parsed = sp.parse_ink(_write_ink(tmp_path))
    rows, blocks = parsed["rows"], parsed["blocks"]
    ops = [r["op"] for r in rows]
    assert ops == ["narrate", "say", "label", "say", "ending"]   # 选择行不产行，场景块去图化
    assert blocks == [{"block": "s00_hotel", "scene_name": "酒店-客房"}]
    assert rows[0]["scene_block_id"] == "s00_hotel"
    assert rows[1] == {"op": "say", "who": "陆择", "text": "嗯……等下还要赶飞机。",
                       "scene_block_id": "s00_hotel"}
    assert rows[2] == {"op": "label", "text": "get_up", "scene_block_id": "s00_hotel"}  # = stitch
    assert rows[4] == {"op": "ending", "kind": "BE", "text": "没赶上飞机。",
                       "scene_block_id": "s00_hotel"}


def test_parse_ink_choice_lines_skipped(tmp_path):
    """* / + 选择行整行跳过（choice 不进图）——v2 行尾注释 `// ending:` 与 v1 行尾 tag `# ending:` 形均随行跳过。"""
    ink = ("=== s00_hotel // 场（早）\n"
           "* 起床 -> get_up\n"
           "+ 再睡一会 -> sleep_in\n"
           "* 直接出门 -> END // ending: BE\n"
           "* 旧式直达 -> END # ending: BE——落荒而逃\n"
           "旁白:醒了。\n")
    rows = sp.parse_ink(_write_ink(tmp_path, ink))["rows"]
    assert rows == [{"op": "narrate", "text": "醒了。", "scene_block_id": "s00_hotel"}]


def test_parse_ink_comment_ignored(tmp_path):
    ink = "// 节标题（人读注释）\n\n=== s0 场（早）\n旁白:正文。\n// 中间注释\n"
    rows = sp.parse_ink(_write_ink(tmp_path, ink))["rows"]
    assert [r["text"] for r in rows] == ["正文。"]


def test_parse_ink_v1_scene_marker_still_supported(tmp_path):
    """存量 chapter00 的 v1 === 行式（中文 id + 空格后缀）永久兼容、文件封存不改写。"""
    ink = ("=== s00_酒店 酒店-客房（清晨）\n"
           "旁白:正文。\n")
    parsed = sp.parse_ink(_write_ink(tmp_path, ink))
    assert parsed["blocks"] == [{"block": "s00_酒店", "scene_name": "酒店-客房"}]
    assert parsed["rows"][0]["scene_block_id"] == "s00_酒店"


def test_parse_ink_v2_scene_marker_variants(tmp_path):
    """v2 === 行变体：无时段合法；`//` 后缺 Scene 名报错。"""
    ink = "=== s01_road // 马路-路口\n旁白:正文。\n"
    assert sp.parse_ink(_write_ink(tmp_path, ink))["blocks"] == \
        [{"block": "s01_road", "scene_name": "马路-路口"}]
    p = _write_ink(tmp_path, "=== s01_road //\n旁白:正文。\n")
    with pytest.raises(ValueError, match="场景块标记格式错误"):
        sp.parse_ink(p)


def test_parse_ink_bare_end_skipped(tmp_path):
    """线性节尾裸 -> END：纯收束行不产行（消 inklecate loose ends 警告）。"""
    ink = "=== s0 场（早）\n旁白:正文。\n-> END\n"
    rows = sp.parse_ink(_write_ink(tmp_path, ink))["rows"]
    assert [r["op"] for r in rows] == ["narrate"]


def test_parse_ink_ending_two_line_single_row(tmp_path):
    """两行式结局（落点内容行 + 行尾 ending tag + 裸 -> END）解析为单条 op=ending，末尾标点保留。"""
    ink = "=== s0 场（早）\n没赶上飞机。 # ending: BE\n-> END\n"
    rows = sp.parse_ink(_write_ink(tmp_path, ink))["rows"]
    assert rows == [{"op": "ending", "kind": "BE", "text": "没赶上飞机。",
                     "scene_block_id": "s0"}]


def test_parse_ink_v1_single_line_ending_rejected(tmp_path):
    """v1 单行式 -> END # ending: 已废止：显式报错（存量无此行型，零迁移风险）。"""
    p = _write_ink(tmp_path, "=== s0 场（早）\n-> END # ending: BE——落荒而逃\n")
    with pytest.raises(ValueError, match="divert 仅支持裸 -> END"):
        sp.parse_ink(p)


def test_parse_ink_malformed_ending_tag_rejected(tmp_path):
    """含 # ending 提示但格式不完整（kind 后带尾巴）：显式报错，防 _SAY_RE 产垃圾 say 行。"""
    p = _write_ink(tmp_path, "=== s0 场（早）\n落点 # ending: BE——多余\n")
    with pytest.raises(ValueError, match="结局落点行格式错误"):
        sp.parse_ink(p)


def test_parse_ink_text_in_memory(tmp_path):
    """parse_ink_text（dashboard 编辑器 in-memory 校验入口）与文件版输出一致。"""
    assert sp.parse_ink_text(INK) == sp.parse_ink(_write_ink(tmp_path))


def test_parse_ink_rejects_bare_divert(tmp_path):
    """裸 divert（-> label）无图行建模：显式报错而非静默吞掉。"""
    p = _write_ink(tmp_path, "=== s0 场（早）\n-> 起床\n")
    with pytest.raises(ValueError, match="divert 仅支持裸 -> END"):
        sp.parse_ink(p)


def test_parse_ink_rejects_leading_hash(tmp_path):
    """ink 中 # 是 tag 非注释：行首 # 会被 _SAY_RE 吃成 who——显式拦截。"""
    p = _write_ink(tmp_path, "=== s0 场（早）\n# ending: BE\n")
    with pytest.raises(ValueError, match="# 开头"):
        sp.parse_ink(p)


def test_parse_ink_rejects_bad_scene_marker(tmp_path):
    p = _write_ink(tmp_path, "=== s0\n旁白:正文。\n")   # 缺 Scene 名
    with pytest.raises(ValueError, match="场景块标记格式错误"):
        sp.parse_ink(p)


def test_parse_ink_rejects_unknown_line(tmp_path):
    p = _write_ink(tmp_path, "=== s0 场（早）\n%%怪行%%\n")
    with pytest.raises(ValueError, match="第 2 行"):
        sp.parse_ink(p)


def test_parse_ink_rejects_legacy_portrait_bracket(tmp_path):
    p = _write_ink(tmp_path, "=== s0 场（早）\n陆择[微笑]:再睡五分钟嘛。\n")
    with pytest.raises(ValueError, match="第 2 行"):
        sp.parse_ink(p)


def test_parse_ink_requires_scene_marker(tmp_path):
    p = _write_ink(tmp_path, "// 只有节注释\n\n")
    with pytest.raises(ValueError, match="缺场景块标记行"):
        sp.parse_ink(p)


def test_parse_ink_line_before_first_scene_marker(tmp_path):
    p = _write_ink(tmp_path, "旁白:出现在首个场景块之前\n=== s0 场（早）\n")
    with pytest.raises(ValueError, match="首个场景块标记之前"):
        sp.parse_ink(p)


# ── 音频行型 v3：sfx 点状 / bed± 音床起止 / 旧环境音两型废止 ──

def test_parse_ink_sfx_line(tmp_path):
    """sfx: 点状音效行 → op=transition（图/投影/运行时语义不变，纯语法层）。"""
    ink = "=== s0 场（早）\nsfx: 推门时门口的风铃清脆作响\n"
    rows = sp.parse_ink(_write_ink(tmp_path, ink))["rows"]
    assert rows == [{"op": "transition", "text": "推门时门口的风铃清脆作响",
                     "scene_block_id": "s0"}]


def test_parse_ink_legacy_ambient_line_rejected(tmp_path):
    """「环境音:」独立行 v3 废止：显式报错并给替代语法（防静默丢声）。"""
    p = _write_ink(tmp_path, "=== s0 场（早）\n环境音:推门时门口的风铃清脆作响\n")
    with pytest.raises(ValueError, match="独立环境音行已废止"):
        sp.parse_ink(p)


def test_parse_ink_inline_ambient_rejected(tmp_path):
    """旁白内嵌【环境音:】v3 废止：报错引导 bed±/sfx。"""
    p = _write_ink(tmp_path, "=== s0 场（早）\n旁白:雨点骤然砸落【环境音:骤雨由疏转密】\n")
    with pytest.raises(ValueError, match="内嵌环境音标注已废止"):
        sp.parse_ink(p)


def test_parse_ink_inline_ambient_in_say_rejected(tmp_path):
    """内嵌哨兵通杀：说话行内嵌同样报错（先于 say 判定，防被 _SAY_RE 吃掉）。"""
    p = _write_ink(tmp_path, "=== s0 场（早）\n陆择:好吵【环境音:雨声】\n")
    with pytest.raises(ValueError, match="内嵌环境音标注已废止"):
        sp.parse_ink(p)


def test_parse_ink_bed_pair_rows(tmp_path):
    """bed+ / bed- 起止对 → bed_start（bed+text 语义）/ bed_end（bed）两行。"""
    ink = ("=== s0 场（早）\n"
           "bed+ rain // 雨点骤然砸落，越来越密\n"
           "旁白:雨下起来。\n"
           "bed- rain\n")
    parsed = sp.parse_ink(_write_ink(tmp_path, ink))
    assert parsed["rows"] == [
        {"op": "bed_start", "bed": "rain", "text": "雨点骤然砸落，越来越密", "scene_block_id": "s0"},
        {"op": "narrate", "text": "雨下起来。", "scene_block_id": "s0"},
        {"op": "bed_end", "bed": "rain", "scene_block_id": "s0"},
    ]
    assert parsed["llm_hints"] == []


def test_parse_ink_bed_unclosed_error(tmp_path):
    p = _write_ink(tmp_path, "=== s0 场（早）\nbed+ rain // 雨声\n旁白:正文。\n")
    with pytest.raises(ValueError, match="未闭合音床.*rain"):
        sp.parse_ink(p)


def test_parse_ink_bed_end_without_start_error(tmp_path):
    p = _write_ink(tmp_path, "=== s0 场（早）\nbed- rain\n")
    with pytest.raises(ValueError, match="无对应未闭合的 bed\\+"):
        sp.parse_ink(p)


def test_parse_ink_bed_cross_block_error(tmp_path):
    """跨场景块配对报错——运行时换段即停床，起止必须同块。"""
    p = _write_ink(tmp_path, "=== s0 场（早）\nbed+ rain // 雨声\n=== s1 场（晚）\nbed- rain\n")
    with pytest.raises(ValueError, match="跨场景块"):
        sp.parse_ink(p)


def test_parse_ink_bed_duplicate_start_error(tmp_path):
    p = _write_ink(tmp_path, "=== s0 场（早）\nbed+ rain // 雨声\nbed+ rain // 又一层\nbed- rain\n")
    with pytest.raises(ValueError, match="重复起始"):
        sp.parse_ink(p)


def test_parse_ink_bed_id_charset_rejected(tmp_path):
    """bed id 限 ASCII 字母数字下划线（禁中文/连字符）。"""
    for bad in ("雨声", "rain-storm"):
        p = _write_ink(tmp_path, f"=== s0 场（早）\nbed+ {bad} // x\nbed- {bad}\n")
        with pytest.raises(ValueError, match="音床行格式错误|无法解析"):
            sp.parse_ink(p)


def test_parse_ink_bed_missing_semantic_error(tmp_path):
    """bed+ 语义必填（AudioFly 生成提示语）。"""
    p = _write_ink(tmp_path, "=== s0 场（早）\nbed+ rain\nbed- rain\n")
    with pytest.raises(ValueError, match="缺语义"):
        sp.parse_ink(p)


def test_parse_ink_bed_parallel_and_nested_ok(tmp_path):
    """多床并行与嵌套（A 起、B 起、B 止、A 止）均合法。"""
    ink = ("=== s0 场（早）\n"
           "bed+ rain // 雨声\n"
           "bed+ motor // 引擎轰鸣\n"
           "旁白:正文。\n"
           "bed- motor\n"
           "bed- rain\n")
    rows = sp.parse_ink(_write_ink(tmp_path, ink))["rows"]
    assert [r["op"] for r in rows] == ["bed_start", "bed_start", "narrate", "bed_end", "bed_end"]


def test_parse_ink_llm_hint_collected(tmp_path):
    """llm: 占位不产行不进图，llm_hints 收集 (行号, 提示语)；不会被 _SAY_RE 吃成 say。"""
    ink = ("=== s0 场（早）\n"
           "旁白:正文。\n"
           "llm: 陆择被撞后短暂失忆，自嘲一句\n"
           "旁白:结尾。\n")
    parsed = sp.parse_ink(_write_ink(tmp_path, ink))
    assert [r["op"] for r in parsed["rows"]] == ["narrate", "narrate"]
    assert parsed["llm_hints"] == [(3, "陆择被撞后短暂失忆，自嘲一句")]


def test_ensure_no_placeholders_gate():
    """split 门禁：llm 占位定稿拒绝拆分（防占位内容静默丢失）。"""
    sp.ensure_no_placeholders({"rows": [], "blocks": [], "llm_hints": []})  # 无占位放行
    with pytest.raises(ValueError, match="2 处 llm: 占位.*第 2 行、第 5 行"):
        sp.ensure_no_placeholders({"llm_hints": [(2, "a"), (5, "b")]})


def test_sig_bed_includes_id():
    """bed 起止签名含 bed id——防两个 bed_end 同签名产生配对歧义。"""
    assert sp._sig({"op": "bed_start", "bed": "rain", "text": "雨"}) == ("bed_start", "rain", "雨")
    assert sp._sig({"op": "bed_end", "bed": "rain"}) == ("bed_end", "rain", "")
    assert sp._sig({"op": "bed_end", "bed": "motor"}) != sp._sig({"op": "bed_end", "bed": "rain"})


def test_bed_create_status_zero_and_end_eleven():
    """bed_start 是音频行（待产 0）、bed_end 非音频行（拆分即 11）。"""
    md = [{"op": "bed_start", "bed": "rain", "text": "雨声", "scene_block_id": "s0"},
          {"op": "bed_end", "bed": "rain", "scene_block_id": "s0"}]
    plan = sp.align(md, [])
    seq, _ = sp.assign_orders(md, plan)
    stmts, _ = sp.build_actions(seq, plan, "SC")
    start_stmt = [s for s in stmts if "l.op='bed_start'" in s][0]
    end_stmt = [s for s in stmts if "l.op='bed_end'" in s][0]
    assert "l.status=0" in start_stmt and "l.bed='rain'" in start_stmt
    assert "l.status=11" in end_stmt


# ── align / assign_orders ──

def _md_rows():
    return [
        {"op": "say", "who": "陆择", "text": "第一句", "scene_block_id": "s0"},
        {"op": "say", "who": "陆择", "text": "第二句", "scene_block_id": "s0"},
        {"op": "narrate", "text": "收尾", "scene_block_id": "s0"},
    ]


def test_align_full_new():
    plan = sp.align(_md_rows(), [])
    assert len(plan["create"]) == 3 and not plan["keep"] and not plan["update"] and not plan["delete"]
    seq, reordered = sp.assign_orders(_md_rows(), plan)
    assert [x["order"] for x in seq] == [1000, 2000, 3000]
    assert not reordered
    assert all(x["action"] == "create" for x in seq)


def test_align_insert_middle_gets_midpoint_order():
    graph = [_g("say", "第一句", who="陆择", order=1000, nid="b"),
             _g("narrate", "收尾", order=3000, nid="d")]
    md = [  # 在 第一句 与 收尾 之间插入 第二句
        {"op": "say", "who": "陆择", "text": "第一句", "scene_block_id": "s0"},
        {"op": "say", "who": "陆择", "text": "第二句", "scene_block_id": "s0"},
        {"op": "narrate", "text": "收尾", "scene_block_id": "s0"},
    ]
    plan = sp.align(md, graph)
    assert len(plan["keep"]) == 2 and len(plan["create"]) == 1
    seq, reordered = sp.assign_orders(md, plan)
    new = [x for x in seq if x["action"] == "create"][0]
    assert new["order"] == 2000                 # (1000+3000)//2 中点
    assert not reordered
    assert [x["order"] for x in seq] == [1000, 2000, 3000]


def test_align_modify_keeps_id_and_marks_stale():
    graph = [_g("say", "旧台词", who="陆择", order=1000, nid="keepme")]
    md = [{"op": "say", "who": "陆择", "text": "新台词", "scene_block_id": "s0"}]
    plan = sp.align(md, graph)
    assert len(plan["update"]) == 1
    seq, _ = sp.assign_orders(md, plan)
    assert seq[0]["id"] == "keepme" and seq[0]["order"] == 1000
    stmts, report = sp.build_actions(seq, plan, "SC")
    assert report["updated"] == [{"id": "keepme", "op": "say", "text": "新台词"}]
    assert any("l.status=0" in s for s in stmts)         # stale 重配
    assert any("keepme" in s and "l.text='新台词'" in s for s in stmts)


def test_align_delete_detaches():
    graph = [_g("say", "第一句", who="A", order=1000, nid="a"),
             _g("say", "将删", who="A", order=2000, nid="del")]
    md = [{"op": "say", "who": "A", "text": "第一句", "scene_block_id": "s0"}]
    plan = sp.align(md, graph)
    assert len(plan["delete"]) == 1 and plan["delete"][0]["graph"]["id"] == "del"
    seq, _ = sp.assign_orders(md, plan)
    stmts, report = sp.build_actions(seq, plan, "SC")
    assert any("DETACH DELETE l" in s and "del" in s for s in stmts)
    assert report["counts"]["deleted"] == 1


def test_align_repeated_text_pairs_stably():
    graph = [_g("say", "一样的话", who="A", order=1000, nid="x", voice_key="k1"),
             _g("say", "一样的话", who="A", order=2000, nid="y", voice_key="k2"),
             _g("say", "不一样", who="A", order=3000, nid="z")]
    md = [{"op": "say", "who": "A", "text": "一样的话", "scene_block_id": "s0"},
          {"op": "say", "who": "A", "text": "一样的话", "scene_block_id": "s0"},
          {"op": "say", "who": "A", "text": "不一样", "scene_block_id": "s0"}]
    plan = sp.align(md, graph)
    assert len(plan["keep"]) == 3 and not plan["create"] and not plan["delete"]


def test_order_exhaustion_triggers_full_reorder():
    graph = [_g("say", "一", who="A", order=1000, nid="a"),
             _g("say", "三", who="A", order=1001, nid="c")]   # 缝隙差 1，插不进
    md = [{"op": "say", "who": "A", "text": "一", "scene_block_id": "s0"},
          {"op": "say", "who": "A", "text": "二", "scene_block_id": "s0"},  # 新句
          {"op": "say", "who": "A", "text": "三", "scene_block_id": "s0"}]
    plan = sp.align(md, graph)
    seq, reordered = sp.assign_orders(md, plan)
    assert reordered
    assert [x["order"] for x in seq] == [1000, 2000, 3000]
    body, _ = sp.build_actions(seq, plan, "SC")
    stmts = sp._order_statements(seq, "SC", reordered) + body
    assert any("SET r.order=3000" in s for s in stmts)   # 被挤开的旧行重排到新位
    assert any("MERGE (sc)-[r:produces]->(l) SET r.order=2000" in s for s in stmts)  # 新行建边带序


# ── build_actions：keep 的恢复与保留 ──

def test_keep_restores_minus1_with_wav(monkeypatch):
    monkeypatch.setattr(sp, "_wav_exists", lambda key: True)
    g = _g("say", "第一句", who="A", order=1000, nid="a", status=-1, voice_key="k1")
    md = [{"op": "say", "who": "A", "text": "第一句", "scene_block_id": "s0"}]
    plan = sp.align(md, [g])
    seq, _ = sp.assign_orders(md, plan)
    stmts, report = sp.build_actions(seq, plan, "SC")
    assert report["restored"] == [{"id": "a", "to": 10}]
    assert any("SET l.status=10" in s for s in stmts)


def test_keep_restores_minus1_without_wav_to_zero(monkeypatch):
    monkeypatch.setattr(sp, "_wav_exists", lambda key: False)
    g = _g("say", "第一句", who="A", order=1000, nid="a", status=-1, voice_key="k1")
    md = [{"op": "say", "who": "A", "text": "第一句", "scene_block_id": "s0"}]
    plan = sp.align(md, [g])
    seq, _ = sp.assign_orders(md, plan)
    _, report = sp.build_actions(seq, plan, "SC")
    assert report["restored"] == [{"id": "a", "to": 0}]


def test_keep_restores_minus1_transition_and_bed_with_wav(monkeypatch):
    """修复锁定：transition/bed_start 行 -1 恢复按「track 在+wav 在→10 否则 0」——
    旧写法 `op=='ambient' or ambient_text` 是死条件（md 侧永无 ambient op），
    实际落 else 置 11，违反 ambient-sfx-designer 宣称。"""
    monkeypatch.setattr(sp, "_wav_exists", lambda key: True)
    for op, extra in (("transition", {}), ("bed_start", {"bed": "rain"})):
        g = dict(_g(op, "雨声", order=1000, nid="t1", status=-1), ambient_track="amb-x-t1", **extra)
        md = [dict({"op": op, "text": "雨声", "scene_block_id": "s0"}, **extra)]
        plan = sp.align(md, [g])
        seq, _ = sp.assign_orders(md, plan)
        _, report = sp.build_actions(seq, plan, "SC")
        assert report["restored"] == [{"id": "t1", "to": 10}], op
    monkeypatch.setattr(sp, "_wav_exists", lambda key: False)
    g = dict(_g("transition", "雨声", order=1000, nid="t2", status=-1), ambient_track="amb-x-t2")
    md = [{"op": "transition", "text": "雨声", "scene_block_id": "s0"}]
    plan = sp.align(md, [g])
    seq, _ = sp.assign_orders(md, plan)
    _, report = sp.build_actions(seq, plan, "SC")
    assert report["restored"] == [{"id": "t2", "to": 0}]


def test_keep_restores_nonsay_to_eleven():
    g = _g("narrate", "收尾", order=1000, nid="a", status=-1)
    md = [{"op": "narrate", "text": "收尾", "scene_block_id": "s0"}]
    plan = sp.align(md, [g])
    seq, _ = sp.assign_orders(md, plan)
    _, report = sp.build_actions(seq, plan, "SC")
    assert report["restored"] == [{"id": "a", "to": 11}]


def test_keep_preserves_non_minus1_status():
    g = _g("say", "第一句", who="A", order=1000, nid="a", status=11)
    md = [{"op": "say", "who": "A", "text": "第一句", "scene_block_id": "s0"}]
    plan = sp.align(md, [g])
    seq, _ = sp.assign_orders(md, plan)
    stmts, report = sp.build_actions(seq, plan, "SC")
    assert report["counts"]["restored"] == 0
    assert not any("l.status=" in s for s in stmts)       # 不触碰 status（微调回路：11 保持）


def test_keep_backfills_scene_block_id():
    g = _g("say", "第一句", who="A", order=1000, nid="a", status=11, scene_block_id=None)
    md = [{"op": "say", "who": "A", "text": "第一句", "scene_block_id": "s00_酒店"}]
    plan = sp.align(md, [g])
    seq, _ = sp.assign_orders(md, plan)
    stmts, _ = sp.build_actions(seq, plan, "SC")
    assert any("SET l.scene_block_id='s00_酒店'" in s for s in stmts)


# ── 演出层已剥离：语句不含 portrait 属性 ──

def test_create_update_stmts_have_no_portrait_property():
    graph = [_g("say", "旧台词", who="A", order=1000, nid="keepme")]
    md = [{"op": "say", "who": "A", "text": "新句", "scene_block_id": "s0"},
          {"op": "say", "who": "A", "text": "全新", "scene_block_id": "s0"}]
    plan = sp.align(md, graph)
    seq, _ = sp.assign_orders(md, plan)
    stmts, _ = sp.build_actions(seq, plan, "SC")
    assert stmts
    assert not any("l.portrait" in s for s in stmts)      # portrait 属性已废弃（选绘走 uses 边）


def test_say_create_gets_default_pos_and_status_zero():
    md = [{"op": "say", "who": "陆择", "text": "嗨", "scene_block_id": "s0"}]
    plan = sp.align(md, [])
    seq, _ = sp.assign_orders(md, plan)
    stmts, report = sp.build_actions(seq, plan, "SC")
    create_stmt = [s for s in stmts if "MERGE (l:LineAudio" in s and "l.op='say'" in s][0]
    assert "l.status=0" in create_stmt and "l.pos='left'" in create_stmt  # 单人块靠左
    assert any("r.order=1000" in s for s in stmts)


# ── 环境音行（transition / ambience）与块级 pos 分配 ──
# 「环境音:」独立行 / 旁白内嵌【环境音:x】两型解析用例：test_parse_ink_transition_and_inline_ambient

def test_block_pos_two_speakers_split_sides():
    """双人块：先说话者 left、后说话者 right（对话分侧）；create/update 都按块规则值。"""
    md = [
        {"op": "say", "who": "小夏", "text": "欢迎光临。", "scene_block_id": "s0"},
        {"op": "say", "who": "陆择", "text": "来杯拿铁。", "scene_block_id": "s0"},
    ]
    graph = [_g("say", "欢迎光临呀。", who="小夏", order=1000, nid="a", pos="left")]  # 旧文本 → update
    plan = sp.align(md, graph)
    seq, _ = sp.assign_orders(md, plan)
    stmts, report = sp.build_actions(seq, plan, "SC")
    create_stmt = [s for s in stmts if "MERGE (l:LineAudio" in s and "l.op='say'" in s
                   and "来杯拿铁" in s][0]
    assert "l.pos='right'" in create_stmt                       # 后说话者 right（create 规则值）
    update_stmt = [s for s in stmts if "MATCH (l:LineAudio" in s and "欢迎光临。" in s][0]
    assert "l.pos='left'" in update_stmt                        # 先说话者规则值 left（update 全量 SET）


def test_keep_pos_diff_self_heals():
    """keep 行存量 pos 与块规则不一致（如全 left 旧数据）→ 自愈补写 SET l.pos；一致则不写。"""
    g = _g("say", "第一句", who="A", order=1000, nid="a", status=11, pos="left")
    md = [
        {"op": "say", "who": "A", "text": "第一句", "scene_block_id": "s0"},
        {"op": "say", "who": "B", "text": "第二句", "scene_block_id": "s0"},
    ]
    plan = sp.align(md, [g])
    seq, _ = sp.assign_orders(md, plan)
    stmts, report = sp.build_actions(seq, plan, "SC")
    assert not any("SET l.pos=" in s and "'a'" in s for s in stmts)     # 规则 left 与存量 left 一致 → 不写
    # 反例：单人块规则 left，存量 center → 补写 left
    g2 = dict(_g("say", "独白", who="A", order=1000, nid="b", status=11), pos="center")
    md2 = [{"op": "say", "who": "A", "text": "独白", "scene_block_id": "s0"}]
    plan2 = sp.align(md2, [g2])
    seq2, _ = sp.assign_orders(md2, plan2)
    stmts2, _ = sp.build_actions(seq2, plan2, "SC")
    assert any("SET l.pos='left'" in s and "'b'" in s for s in stmts2)


def test_legacy_ambient_graph_row_aligns_as_keep():
    """存量 op=ambient 图行 vs md op=transition：签名归一对齐为 keep，且落图自愈 SET op。"""
    g = _g("ambient", "风铃作响", order=1000, nid="amb1", status=11)
    md = [{"op": "transition", "text": "风铃作响", "scene_block_id": "s0"}]
    plan = sp.align(md, [g])
    assert len(plan["keep"]) == 1 and not plan["update"]      # 不误置 0 重配
    seq, _ = sp.assign_orders(md, plan)
    stmts, _ = sp.build_actions(seq, plan, "SC")
    assert any("SET l.op='transition'" in s for s in stmts)   # 幂等自愈改名
