"""台词.ink 定稿文件编辑支撑：load / validate / save（dashboard 全文编辑器的 core 层）。

范式同 voice_candidates：纯函数、吃 project_root 参数、不 import settings/streamlit
——core 层可脱离 Streamlit 单测。save 走 narrative_review.mark_reviewed 同款
tmp + replace **原子写**（防半截文件被拆分器/审批读到）。

validate 调 `script_splitter.parse_ink_text`（机器侧唯一权威，与拆分进图同一解析器）
——懒导入：`.claude/skills/section-voice-publisher/scripts` 判存在后幂等插入 sys.path。
副作用已评估：script_splitter 顶层仅做 repo 根查找 + sys.path 插入（.claude/scripts
只含 cypher_exec/snowflake_base62，与 dashboard 依赖零命名冲突）。
"""
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _splitter(project_root: Path):
    """懒导入 script_splitter（parse_ink_text 权威解析器），按 project_root 定位。"""
    scripts = Path(project_root) / ".claude" / "skills" / "section-voice-publisher" / "scripts"
    if not (scripts / "script_splitter.py").exists():
        raise FileNotFoundError(f"未找到 script_splitter.py：{scripts}")
    p = str(scripts)
    if p not in sys.path:
        sys.path.insert(0, p)
    import script_splitter
    return script_splitter


def _abs(script_path: str, project_root: Path) -> Path:
    p = Path(script_path)
    return p if p.is_absolute() else Path(project_root) / p


def load(script_path: str, project_root: Path):
    """读 台词.ink 全文；文件缺失返回 None（UI 提示，不抛）。"""
    p = _abs(script_path, project_root)
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


def validate(text: str, project_root: Path):
    """parse_ink_text 校验 → (ok, msg)。错误带 parse_ink 行号+原文；成功给行型摘要。"""
    try:
        parsed = _splitter(project_root).parse_ink_text(text)
    except ValueError as e:
        return False, str(e)
    ops = Counter(r["op"] for r in parsed["rows"])
    detail = " / ".join(f"{op} {ops[op]}" for op in
                        ("say", "narrate", "transition", "bed_start", "bed_end", "label", "ending")
                        if ops[op])
    msg = f"✓ {len(parsed['blocks'])} 场景块 · {len(parsed['rows'])} 行（{detail}）"
    hints = parsed.get("llm_hints") or []
    if hints:
        msg += f" · ⚠️ llm 占位 {len(hints)}（填充后才能拆分）"
    return True, msg


def save(script_path: str, text: str, project_root: Path) -> None:
    """原子写：tmp 写入 → replace 落盘（utf-8，末尾保证换行）。"""
    p = _abs(script_path, project_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(p)
