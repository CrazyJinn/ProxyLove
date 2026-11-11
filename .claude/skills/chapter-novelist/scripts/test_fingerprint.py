"""test_fingerprint.py — fingerprint.py 单测(纯逻辑,不连图库不碰真实小说)。

覆盖:gen 强度标记 / check 双形态 kind 容错 / freshness 指数衰减·S 重置·跨章·自由节·kl 非法·从未消费。
fixture 在 tmp 目录构造小说树,不读 25_剧本 真实数据。用 dashboard venv 跑:uv run pytest / python -m pytest。
"""

from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import fingerprint as fp  # noqa: E402

import pytest  # noqa: E402

FP16 = "0123456789abcdef"


def lore(iid, kl=3, title="测试设定", content="内容", intensity=None):
    row: dict = {"kind": "lore", "id": iid, "title": title, "content": content, "knowledge_level": kl}
    if intensity:
        row["intensity"] = intensity
    return row


def evt(iid, title="t"):
    return {"kind": "event", "id": iid, "title": title, "time": "", "type": "",
            "description": "", "ending_kind": "", "condition": ""}


def write_novel(root, rel, header_lines):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = ("<!-- 取材指纹(chapter-novelist 生成,chapter-dialoguer 自检;变动=重写小说+作废定稿)\n"
            + "\n".join(header_lines) + "\n-->\n\n# 测试小说\n正文\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def capture(fn, *a, **kw):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = fn(*a, **kw)
    return rc, buf.getvalue()


@pytest.fixture()
def tree(tmp_path):
    """ch00 两节 + ch01 一节 + 自由节一节的小说树。"""
    write_novel(tmp_path, "ch00/sec00/小说.md", [f"lore  L1 {FP16} E 设定一", "event  E1 abcdefabcdef0001 事件一"])
    write_novel(tmp_path, "ch00/sec01/小说.md", [f"lore  L1 {FP16} E 设定一", f"lore  L2 {FP16} S 设定二"])
    write_novel(tmp_path, "ch01/sec00/小说.md", [f"lore  L3 {FP16} E 设定三"])
    write_novel(tmp_path, "自由节/sec00/小说.md", [f"lore  L1 {FP16} E 设定一"])
    return tmp_path


# ── gen ──────────────────────────────────────────────────────────────

def test_gen_intensity_suffix():
    rows = [lore("L1"), evt("E1")]
    rc, out = capture(fp.cmd_gen, [dict(r) for r in rows], {"L1": "S", "E1": "E"})
    assert rc == 0
    lore_line = [l for l in out.splitlines() if "L1" in l][0]
    assert " S " in lore_line          # lore 行记强度 S
    evt_line = [l for l in out.splitlines() if "E1" in l][0]
    assert " E " not in evt_line       # event 行不记强度


def test_gen_bare_id_defaults_E():
    rc, out = capture(fp.cmd_gen, [lore("L1")], {"L1": "E"})
    assert rc == 0
    assert any(" E " in l for l in out.splitlines())


def test_gen_missing_id_rejected():
    with pytest.raises(SystemExit):
        fp.cmd_gen([lore("L1")], {"LX": "E"})


# ── check 双形态 kind 容错 ───────────────────────────────────────────

def test_check_kind_equivalence(tmp_path):
    # 头部写 info(旧形态),素材给 lore(新形态),同 id 同内容 → 不 stale
    novel = write_novel(tmp_path, "ch00/sec00/小说.md",
                        [f"info   L1 {fp.fingerprint(lore('L1'))} 设定一"])
    rc, _ = capture(fp.cmd_check, [lore("L1")], novel)
    assert rc == 0


def test_check_content_change_stale(tmp_path):
    novel = write_novel(tmp_path, "ch00/sec00/小说.md",
                        [f"lore  L1 {fp.fingerprint(lore('L1'))} 设定一"])
    changed = lore("L1", content="改了")
    rc, _ = capture(fp.cmd_check, [changed], novel)
    assert rc == 1


# ── freshness ────────────────────────────────────────────────────────

def _fresh(tree, rows, at):
    rc, out = capture(fp.cmd_freshness, rows, str(tree), at)
    assert rc == 0
    return json.loads(out)


def test_freshness_never_consumed(tree):
    out = _fresh(tree, [lore("L9")], "ch01/sec01")
    assert out["L9"]["F"] == 100 and out["L9"]["allow"] == "explicit"


def test_freshness_recent_E_blocked(tree):
    # L3 在 ch01/sec00 消费(E),写 ch01/sec01:Δ=1,kl=3,h=3 → F=round(100*(1-2^(-1/3)))=21 → blocked
    out = _fresh(tree, [lore("L3")], "ch01/sec01")
    assert out["L3"]["delta"] == 1
    assert out["L3"]["F"] == 21 and out["L3"]["allow"] == "blocked"


def test_freshness_same_section_as_consumed_no_prior(tree):
    # 消费点取严格小于 --at:同节自身不算历史 → 从未消费
    out = _fresh(tree, [lore("L3")], "ch01/sec00")
    assert out["L3"]["last"] is None


def test_freshness_far_explicit(tree):
    # L3 ch01/sec00 消费 → ch01/sec09:Δ=9,h=3 → R=2^-3=0.125,F=88 → explicit
    out = _fresh(tree, [lore("L3")], "ch01/sec09")
    assert out["L3"]["delta"] == 9
    assert out["L3"]["F"] == 88 and out["L3"]["allow"] == "explicit"


def test_freshness_S_reset_higher_F(tree):
    # Δ=3,h=3:E→R=0.5,F=50(side);S→R=0.3,F=70(explicit 边界,70≥70)
    write_novel(tree, "ch02/sec00/小说.md", [f"lore  LA {FP16} S 设定A", f"lore  LB {FP16} E 设定B"])
    out = _fresh(tree, [lore("LA"), lore("LB")], "ch02/sec03")
    assert out["LA"]["F"] == 70 and out["LA"]["allow"] == "explicit"
    assert out["LB"]["F"] == 50 and out["LB"]["allow"] == "side"


def test_freshness_cross_chapter_delta_approx(tree):
    # ch00/sec01 → ch01/sec00:跨章按章差 Δ=1
    out = _fresh(tree, [lore("L2")], "ch01/sec00")
    assert out["L2"]["delta"] == 1


def test_freshness_most_recent_wins(tree):
    # L1 可见消费点:ch00/sec00 与 ch00/sec01(自由节排全部章节后,不可见)——最近=ch00/sec01,
    # 写 ch01/sec05 跨章 Δ=1(章差近似)
    out = _fresh(tree, [lore("L1")], "ch01/sec05")
    assert out["L1"]["last"]["path"].endswith("ch00/sec01/小说.md")
    assert out["L1"]["delta"] == 1


def test_freshness_free_section_no_recovery(tree):
    # 写自由节:消费点在自由节(按 mtime 排序)→ Δ=0 不给恢复,且已组章节消费点同样参与
    # L3 只在 ch01/sec00 消费,写自由节/sec00:消费点可见(章节 < 自由节),Δ 取 0(自由节不给恢复)
    out = _fresh(tree, [lore("L3")], "自由节/sec00")
    assert out["L3"]["delta"] == 0
    assert out["L3"]["F"] == 0 and out["L3"]["allow"] == "blocked"


def test_freshness_bad_kl_unlimited(tree):
    row = lore("L1")
    row["knowledge_level"] = None
    out = _fresh(tree, [row], "ch01/sec05")
    assert out["L1"]["allow"] == "explicit" and out["L1"]["note"]


def test_freshness_old_header_no_marker_as_E(tree):
    # 旧头无强度标记 → 按 E:Δ=2,h=3 → R=2^(-2/3)=0.63,F=37 → side
    write_novel(tree, "ch03/sec00/小说.md", [f"lore  L5 {FP16} 设定五"])
    out = _fresh(tree, [lore("L5")], "ch03/sec02")
    assert out["L5"]["last"]["intensity"] == "E"
    assert out["L5"]["F"] == 37 and out["L5"]["allow"] == "side"


def test_freshness_kl1_slow_decay(tree):
    # kl=1(h=12):Δ=5 → R=2^(-5/12)=0.749,F=25 → blocked(主线事实读者记得久)
    write_novel(tree, "ch04/sec00/小说.md", [f"lore  L6 {FP16} E 设定六"])
    out = _fresh(tree, [lore("L6", kl=1)], "ch04/sec05")
    assert out["L6"]["F"] == 25 and out["L6"]["allow"] == "blocked"


def test_freshness_at_accepts_sec_form(tree):
    a = _fresh(tree, [lore("L3")], "ch01/sec09")
    b = _fresh(tree, [lore("L3")], str(tree) + "/ch01/sec09/小说.md")
    assert a["L3"]["F"] == b["L3"]["F"]
