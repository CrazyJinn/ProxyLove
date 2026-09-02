"""台词.md → 台词.ink 一次性迁移（2026-09-02，自包含逐行变换——不 import 旧解析器，永久可跑）。

用法：
  python 00_init/migration/2026-09-02_台词md转ink.py            # 转换 25_剧本/**/台词.md（.ink 已在则跳过）
  python 00_init/migration/2026-09-02_台词md转ink.py --verify   # 逐对断言 parse_md(md) == parse_ink(ink)

行文本逐字保真：内容行（旁白/环境音/说话）原样拷贝——对齐签名（op+who+text）不变，
存量图行全 keep、order/status/已归档音频零触动。图侧配套：2026-09-02_台词md转ink.cypher
（只改 SecScript.script_path，不动 status）。

映射表（详见 chapter-dialoguer references/ink方言规范.md）：
  # <节标题>            → // <节标题>
  ## <块id> <名>（<时段>）→ === <块id> <名>（<时段>）
  **选择**              → 丢弃（ink 选择行自识别，无需块头）
  - <文本> → <去向>     → * <文本> -> <去向映射>（分支:X/场景:X→X；结局:K→END # ending: K）
  **分支:<label>**      → = <label>
  **结局**:<K>——<落点>  → -> END # ending: <K>——<落点>
  旁白:/环境音:/说话行  → 原样拷贝
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 00_init/migration/<本文件> → 项目根

# md 侧行型（与 script_splitter.parse_md 的正则同形——迁移器自包含，不依赖其存活）
_MD_H1_RE = re.compile(r"^#\s+(.*)$")
_MD_SCENE_RE = re.compile(r"^##\s+(\S+)\s+(.+?)\s*(?:（([^）]*)）)?\s*$")
_MD_CHOICE_RE = re.compile(r"^\*\*选择\*\*\s*$")
_MD_OPTION_RE = re.compile(r"^-\s+(.+?)\s*(?:→|->)\s*(.+?)\s*$")
_MD_LABEL_RE = re.compile(r"^\*\*分支\s*[:：]\s*(.+?)\s*\*\*$")
_MD_ENDING_RE = re.compile(r"^\*\*结局\*\*\s*[:：]\s*(BE|TE|HE|NE)\s*(?:——|—)\s*(.+)$")


def _map_target(dest: str) -> str:
    """md 选择行去向 → ink divert 目标：分支:X/场景:X → X；结局:K → END # ending: K；裸 label 名原样。"""
    for prefix in ("分支", "场景"):
        if dest.startswith(prefix + ":"):
            return dest[len(prefix) + 1:].strip()
    if dest.startswith("结局:"):
        return f"END # ending: {dest[len('结局:'):].strip()}"
    return dest


def convert_line(line: str, n: int, where: str, in_choice: list):
    """md 单行 → ink 单行。返回 ink 行；选择块头返回 None（丢弃）。in_choice 为单元素状态。"""
    if not line:
        return line
    m = _MD_H1_RE.match(line)
    if m:
        return f"// {m.group(1).strip()}"
    if _MD_CHOICE_RE.match(line):
        in_choice[0] = True
        return None
    if in_choice[0]:
        m = _MD_OPTION_RE.match(line)
        if m:
            return f"* {m.group(1).strip()} -> {_map_target(m.group(2))}"
        in_choice[0] = False  # 非选项行 = 选择块结束，继续正常转换
    if line.startswith("##"):
        m = _MD_SCENE_RE.match(line)
        if not m:
            raise ValueError(f"{where} 第 {n} 行场景标题格式错误：{line!r}")
        return "===" + line[2:]  # ## payload → === payload（payload 原样，含时段括号）
    m = _MD_LABEL_RE.match(line)
    if m:
        return f"= {m.group(1).strip()}"
    m = _MD_ENDING_RE.match(line)
    if m:
        return f"-> END # ending: {m.group(1)}——{m.group(2).strip()}"
    return line  # 旁白/环境音/说话行原样拷贝（行文本逐字保真）


def convert_file(md_path: Path) -> str:
    out_lines, in_choice = [], [False]
    for n, raw in enumerate(md_path.read_text(encoding="utf-8").splitlines(), 1):
        converted = convert_line(raw.strip(), n, str(md_path), in_choice)
        if converted is not None:
            out_lines.append(converted)
    return "\n".join(out_lines) + "\n"


def verify_pair(md_path: Path, ink_path: Path) -> None:
    """parse_md(md) == parse_ink(ink) 深相等断言——行文本逐字一致的机器证明。
    parse_md 已删除（Phase 5 后）时降级为警告跳过。"""
    sys.path.insert(0, str(ROOT / ".claude" / "skills" / "section-voice-publisher" / "scripts"))
    try:
        import script_splitter as sp
        assert hasattr(sp, "parse_md"), "script_splitter.parse_md 已删除（md 时代结束）"
    except (ImportError, AssertionError) as e:
        print(f"[warn] {e}——跳过深度校验（转换本身仍由 test_md_to_ink.py 锁定）")
        return
    md_parsed, ink_parsed = sp.parse_md(md_path), sp.parse_ink(ink_path)
    if md_parsed != ink_parsed:
        raise AssertionError(f"{md_path} 与 {ink_path} 解析结果不一致：\n"
                             f"md : {md_parsed}\nink: {ink_parsed}")
    print(f"[verify] OK {md_path.name} -> {ink_path.name}: "
          f"rows={len(ink_parsed['rows'])} blocks={len(ink_parsed['blocks'])}")


def main(argv=None) -> int:
    verify = "--verify" in (argv or sys.argv[1:])
    md_files = sorted(ROOT.glob("25_剧本/**/台词.md"))
    if not md_files:
        print("无待迁移的 台词.md（25_剧本/**）")
        return 0
    for md_path in md_files:
        ink_path = md_path.with_suffix(".ink")
        if ink_path.exists():
            print(f"[skip] {ink_path} 已存在（幂等）")
        else:
            try:
                ink_path.write_text(convert_file(md_path), encoding="utf-8")
            except ValueError as e:
                print(f"[fail] {e}")
                return 1
            print(f"[convert] {md_path} -> {ink_path}")
    if verify:
        for md_path in md_files:
            ink_path = md_path.with_suffix(".ink")
            if ink_path.exists():
                verify_pair(md_path, ink_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
