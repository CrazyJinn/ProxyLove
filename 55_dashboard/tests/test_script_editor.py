"""core/script_editor 单测（load / validate / save）——不连 Neo4j、不启动 Streamlit。

validate 经懒导入走真实 script_splitter（项目根在 parents[2]），顺带从 dashboard 侧
再锁一次存量 v1 === 行式兼容。在 55_dashboard 下跑：python -m pytest tests/test_script_editor.py -v
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "55_dashboard"))

from core import script_editor  # noqa: E402

V2_INK = """// 测试节

=== s00_hotel // 酒店-客房（清晨）

旁白:清晨，一缕阳光从窗帘缝隙钻进来。
陆择:嗯……等下还要赶飞机。

没赶上飞机。 # ending: BE
-> END
"""

# 存量 chapter00 行式（中文 id + 空格后缀）——方言 v2 解析器双格式兼容
V1_LEGACY_INK = "=== s00_酒店 酒店-客房（清晨）\n旁白:正文。\n"


def test_load_ok_and_missing(tmp_path):
    p = tmp_path / "台词.ink"
    p.write_text(V2_INK, encoding="utf-8")
    assert script_editor.load(str(p), tmp_path) == V2_INK
    assert script_editor.load(str(tmp_path / "无.ink"), tmp_path) is None


def test_validate_ok_returns_summary(tmp_path):
    ok, msg = script_editor.validate(V2_INK, PROJECT_ROOT)
    assert ok and "1 场景块" in msg and "ending 1" in msg


def test_validate_v1_legacy_scene_marker_ok():
    """存量 v1 === 行（中文 id）从 dashboard 编辑器侧再锁一次兼容。"""
    ok, msg = script_editor.validate(V1_LEGACY_INK, PROJECT_ROOT)
    assert ok and "1 场景块" in msg


def test_validate_syntax_error_reports_line():
    ok, msg = script_editor.validate("=== s00_hotel // 场（早）\n%%怪行%%\n", PROJECT_ROOT)
    assert not ok and "第 2 行" in msg


def test_validate_rejects_v1_single_line_ending():
    """v1 单行式结局已废止——编辑器校验同步拒绝（防手滑写回旧行式）。"""
    ok, msg = script_editor.validate("=== s00_hotel // 场（早）\n-> END # ending: BE——x\n",
                                     PROJECT_ROOT)
    assert not ok and "divert" in msg


def test_save_atomic_roundtrip(tmp_path):
    p = tmp_path / "sub" / "台词.ink"
    script_editor.save(str(p), V2_INK.rstrip("\n"), tmp_path)   # 无末尾换行 → save 补齐
    assert script_editor.load(str(p), tmp_path) == V2_INK
    assert not list(tmp_path.rglob("*.tmp"))                     # 无 .tmp 残留


def test_validate_summary_counts_llm_placeholders():
    """llm: 占位行不报错（合法编辑中状态）但摘要警告占位数（填充后才能拆分）。"""
    ink = "=== s00_hotel // 场（早）\n旁白:正文。\nllm: 陆择自嘲一句\n"
    ok, msg = script_editor.validate(ink, PROJECT_ROOT)
    assert ok and "llm 占位 1（填充后才能拆分）" in msg


def test_validate_rejects_deprecated_ambient_syntax():
    """v3 废止语法：环境音独立行 / 内嵌 → 报错并给替代语法。"""
    for bad in ("=== s00_hotel // 场（早）\n环境音:风铃作响\n",
                "=== s00_hotel // 场（早）\n旁白:雨下【环境音:雨声】\n"):
        ok, msg = script_editor.validate(bad, PROJECT_ROOT)
        assert not ok and "已废止" in msg
