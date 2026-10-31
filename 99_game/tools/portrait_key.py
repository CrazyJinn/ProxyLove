"""立绘运行时键生成（搬运层共享逻辑）。

被 generate_portrait_map.py 与 manifest_builder.py 共用，保证
「章 JSON say.portrait / manifest 键 / PNG 文件名」三处对齐。

键格式（2026-10-31 id 锚定重构后）：**hexid(StandingIllustration.id)**
  - NTFS 大小写不敏感与 Base62 不兼容（同批 id 共享前缀仅末位大小写不同），
    凡进文件名/manifest 键的 id 一律 to_hexid（可逆，见 .claude/scripts/snowflake_base62.py）。
  - stand_id 全局唯一 → 键天然唯一，与 Character/CostumeStyle/variant 改名彻底解耦。

Godot 侧 PortraitLayer._resolve 直接用 portrait 字段整键查 manifest；
旧章（二维键 <char>.<variant>）走「拼 who」fallback 兼容。

纯函数、无 I/O、无 neo4j 依赖，可独立单测。
"""
import re
import sys
from pathlib import Path

_SYS = Path(__file__).resolve().parents[2] / ".claude" / "scripts"
if str(_SYS) not in sys.path:
    sys.path.insert(0, str(_SYS))
from snowflake_base62 import to_hexid  # noqa: E402

# 兜底清洗（hexid 天然只含 [0-9a-f]，此处防御未来输入变化）
_ILLEGAL = re.compile(r'[\\/:*?"<>|]')


def _sanitize(s: str) -> str:
    """替换 Windows 文件名非法字符为 _，折叠首尾空白。"""
    if not s:
        return ""
    return _ILLEGAL.sub("_", s.strip())


def make_key(stand_id: str) -> str:
    """生成运行时键 = hexid(StandingIllustration.id)。

    旧四段整键 <char>-<costume>-<variant>-<stand_id> 已废（随全章重发布切换，
    manifest_builder --rebuild 清旧键）。
    """
    return to_hexid(_sanitize(stand_id))
