"""台词.ink 拆分对齐进图（SecScript → 逐句 LineAudio，produces{order} 大间距排序）。

section-voice-publisher 第一步「拆分进图」的唯一实现。把已批定稿（SecScript=11 的
台词.ink，人读 ink 方言——规范见 chapter-dialoguer references/ink方言规范.md）幂等
拆分为图节点：

  parse_ink 解析 台词.ink（方言 v3，标准合法 ink：ASCII knot/stitch 标识符、knot 行尾
            注释载 Scene 名/时段、结局两行式=落点内容行+行尾 ending tag+裸 -> END；
            存量 v1 === 行双格式兼容；音频三型 sfx:（点状→transition）/ bed+ bed-（音床
            起止→bed_start/bed_end，文件级配对校验）/ 旧环境音两型废止报错；llm: 占位
            不产行（split 门禁拒绝含占位定稿））→ 行序列（say/narrate/transition/
            bed_start/bed_end/label/ending；* / + 选择行整行跳过——choice 及配套 jump
            暂不进图，建模后续设计；解析失败抛 ValueError 带行号）
  align     定稿行 vs 图已有行 difflib 对齐（签名 = op+who+text）→ 保留/更新/新建/删除
  split     经 cypher_exec.py（--stdin --multi 单事务）写图 + 产出报告 JSON

数据模型（00_init/Schema/剧情.md）：
  行身份 = 节点雪花 id（voice key 末段，插入/删除行不影响其他行）
  顺序   = produces 边 order：初始 (i+1)*1000；两句之间插入取 (上+下)//2 中点；
           同缝隙多行均分；中点耗尽（分配后非严格递增）→ 全节重排（order 不进
           voice key，重排安全）
  恢复   = sync 级联置 -1 的行：text_sha1 匹配且 wav 在 → 10（音频复用，保守进审）；
           非 say 行 → 11（无音频语义，拆分即完成）；否则 0
  微调   = 人工改 ink 重批后重拆：未变行原样保留（含已批 11），只有改动句置 0
           ——单句修改不丢

CLI:
  python script_splitter.py split --section <sec_id> [--report out.json] [--dry-run]
退码：0 成功（或 dry-run）/ 1 前置校验或解析失败 / 2 参数错。
"""
import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

def _find_repo_root(start: Path) -> Path:
    """向上搜索项目根（含 .claude/scripts/cypher_exec.py 的目录），不依赖固定层级。"""
    for p in (start, *start.parents):
        if (p / ".claude" / "scripts" / "cypher_exec.py").exists():
            return p
    raise RuntimeError("未找到项目根（向上搜索 .claude/scripts/cypher_exec.py 失败）")


ROOT = _find_repo_root(Path(__file__).resolve())     # 项目根
CYPHER_EXEC = ROOT / ".claude" / "scripts" / "cypher_exec.py"
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # 同目录：voice_bundler
from snowflake_base62 import SnowflakeGenerator  # noqa: E402
from voice_bundler import voice_master_path  # noqa: E402

ORDER_STEP = 1000          # 初始间距
SAY_DEFAULT_POS = "left"   # say 行立绘位兜底（单人块规则值；update 沿用存量时的兜底）


def _block_pos_map(script_rows_in_block: list) -> dict:
    """块内 say 行 who（按首次说话序）→ 立绘位（md 不写 pos，块级规则值即缺省值）：
    1 人 left（独白靠左，与对话框正文起始位一致）/ 2 人先说话者 left 后说话者 right（对话分侧）/
    ≥3 人按首话序 left/right/center（第 4+ 人兜底 center）。"""
    whos = []
    for m in script_rows_in_block:
        if m.get("op") == "say" and m.get("who") and m["who"] not in whos:
            whos.append(m["who"])
    if not whos:
        return {}
    if len(whos) == 1:
        seats = ["left"]
    elif len(whos) == 2:
        seats = ["left", "right"]
    else:
        seats = ["left", "right", "center"]
    return {w: (seats[i] if i < len(seats) else "center") for i, w in enumerate(whos)}

_GEN = SnowflakeGenerator()


def text_sha1(text: str) -> str:
    """台词文本指纹（stale 判定唯一依据，不做 normalize）。与 voice_bundler._text_sha1 同实现。"""
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()


def _q(v) -> str:
    """Cypher 字符串字面量（单引号，转义 \\ 与 '）。None → null。"""
    if v is None:
        return "null"
    s = str(v).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def _run_cypher(cypher: str) -> list:
    """调 cypher_exec.py --json，提取返回的 JSON 数组（cypher_exec 输出含连接提示行）。"""
    proc = subprocess.run(
        [sys.executable, str(CYPHER_EXEC), "-c", cypher, "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    out = proc.stdout
    start, end = out.find("["), out.rfind("]")
    if start == -1 or end == -1:
        raise RuntimeError(
            f"cypher_exec 未返回 JSON（退出码 {proc.returncode}）:\nstderr: {proc.stderr}\nstdout: {out}"
        )
    return json.loads(out[start:end + 1])


def _run_cypher_multi(statements: list) -> None:
    """多语句单事务写图（--stdin --multi）；任一失败整体回滚。"""
    tx = "\n".join(statements)
    proc = subprocess.run(
        [sys.executable, str(CYPHER_EXEC), "--stdin", "--multi"],
        input=tx, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"写图失败（退出码 {proc.returncode}）:\n{proc.stderr}")


# ── 解析 台词.ink（方言 v2 规范：chapter-dialoguer references/ink方言规范.md）──

# 场景块标记（knot）双格式：v2「=== <ascii_id> // <Scene 名>（<时段>）」（优先，行尾注释——标准 ink）
# + v1「=== <id> <Scene 名>（<时段>）」（空格分隔，存量 chapter00 中文 id 封存兼容；
#   哨兵 (?!//) 防 v1 把 // 后缀当 Scene 名）
_SCENE_RE = re.compile(r"^===\s+(\S+)(?:\s+//\s*|\s+(?!//))(.+?)\s*(?:（([^）]*)）)?\s*$")
_NARRATE_RE = re.compile(r"^旁白\s*:\s*(.+)$")
# 说话行不支持 [表情] 标注（演出层已与台词分离）：角色名排除 [ 与 ]，残留标注（陆择[微笑]:x）
# 因 group(1) 无法跨 [ 而整行不匹配 → 落入末尾 ValueError 显式拦截
_SAY_RE = re.compile(r"^([^:\[\]]+?)\s*:\s*(.+)$")
# 分支标记（= stitch）→ op=label；解析器不校验字符集（ASCII 是文档契约，存量中文零风险）
_STITCH_RE = re.compile(r"^=\s+(.+?)\s*$")
# v2 两行式结局·落点行：裸内容行 + 行尾 ending tag（官方 tag 挂内容行）；
# text=落点、kind=tag 段；判定必须先于 narrate/say（tag 冒号会被 _SAY_RE 吃）
_ENDING_LINE_RE = re.compile(r"^(.+?)\s*#\s*ending[:：]\s*(BE|TE|HE|NE)\s*$")
# ending 哨兵：行内含「# ending」但不匹配完整格式 → 显式报错（防 _SAY_RE 产垃圾 say 行）
_ENDING_HINT_RE = re.compile(r"#\s*ending")
# 裸收束行 -> END：不产行（线性节尾可加，消 inklecate loose ends 警告）
_BARE_END_RE = re.compile(r"^->\s*END\s*$")
# 选择行（* once-only / + sticky 均可，解析不区分）：整行跳过，含行尾 tag/注释
_CHOICE_RE = re.compile(r"^[*+](\s|$)")
# 注释行（ink 中 # 是 tag 非注释，注释是 //）
_COMMENT_RE = re.compile(r"^//")
# ── 音频行型 v3（sfx 点状 / bed± 音床起止 / llm 占位）──
# sfx 点状音效：→ op=transition（图/投影/运行时语义不变，纯语法层）。含冒号，先于 _SAY_RE
_SFX_RE = re.compile(r"^sfx\s*[:：]\s*(.+)$")
# 音床起止对：id 限 [A-Za-z0-9_]+（配对/多床并行/嵌套）；起始行语义必填（AudioFly 生成提示语）
_BED_START_RE = re.compile(r"^bed\+\s+([A-Za-z0-9_]+)(?:\s*//\s*(.+))?$")
_BED_END_RE = re.compile(r"^bed-\s+([A-Za-z0-9_]+)$")
_BED_HINT_RE = re.compile(r"^bed[+-]")  # 哨兵：bed 行格式坏 → 定向报错（防落兜底笼统错误）
# LLM 占位：不产行不进图（split 门禁拒绝含占位定稿）；含冒号，必须先于 _SAY_RE
_LLM_RE = re.compile(r"^llm\s*[:：]\s*(.+)$")
# v3 废止探测（报错引导新语法，防静默丢行/丢声）：
# 环境音独立行（→ sfx:）与内嵌【环境音:…】（→ bed±）
_AMBIENT_RE = re.compile(r"^环境音\s*[:：]\s*(.+)$")
_INLINE_AMBIENT_RE = re.compile(r"【环境音[:：]([^】]+)】")


def parse_ink(path) -> dict:
    """解析 台词.ink 文件 → {"rows", "blocks", "llm_hints"}（薄壳，主体在 parse_ink_text）。"""
    return parse_ink_text(Path(path).read_text(encoding="utf-8"))


def parse_ink_text(text: str) -> dict:
    """解析 台词.ink 文本（方言 v3，标准合法 ink）→
    {"rows": [...], "blocks": [{block, scene_name}, ...], "llm_hints": [(行号, 提示语), ...]}。

    行 dict：op/who/text/kind/bed/scene_block_id。演出层（立绘选择）不在拆分期——由配音
    判断期选绘建 LineAudio-[:uses]->StandingIllustration 边。
    判定次序（防线，顺序敏感）：空行 → // 注释 → */+ 选择行（整行跳过——choice 不进图）
    → === 场景块（双格式，先于 =）→ 首块前内容行报错 → 行首 # 报错 → 行首 ->
    （裸 END 跳过 / 其余报错）→ ending 落点行（先于 narrate/say）→ 内嵌【环境音:】哨兵
    （v3 废止，通杀旁白/说话行）→ 旁白 → 环境音独立行（v3 废止报错）→ sfx:（点状→
    transition）→ bed+ / bed-（音床起止 + 配对状态机）→ llm:（占位不产行）→ bed 哨兵
    （格式坏定向报错）→ = 分支（label）→ 说话行 → 兜底。sfx:/llm: 含冒号，**必须先于
    _SAY_RE**（否则被吃成 who）。解析失败抛 ValueError（带行号与原文）。
    """
    rows, blocks, llm_hints = [], [], []
    open_beds = {}  # bed id -> (起始行号, scene_block_id)；配对状态机（多床并行/嵌套天然支持）
    cur_block = None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or _COMMENT_RE.match(line):
            continue  # 空行 / // 注释
        if _CHOICE_RE.match(line):
            continue  # 选择行：整行跳过（choice 及去向 tag/注释不进图，建模后续设计）
        if line.startswith("==="):
            m = _SCENE_RE.match(line)
            if not m:
                raise ValueError(f"台词.ink 第 {n} 行场景块标记格式错误：{raw!r}"
                                 "（应为 === <scene_block_id> // <Scene 名>（<时段>）；"
                                 "存量 v1 行式 === <id> <Scene 名>（<时段>）兼容）")
            cur_block = m.group(1)
            blocks.append({"block": cur_block, "scene_name": m.group(2).strip()})
            continue
        if cur_block is None:
            raise ValueError(f"台词.ink 第 {n} 行出现在首个场景块标记之前：{raw!r}")
        if line.startswith("#"):
            raise ValueError(f"台词.ink 第 {n} 行以 # 开头（tag 非行首语法，仅结局落点行行尾支持）：{raw!r}")
        if line.startswith("->"):
            if _BARE_END_RE.match(line):
                continue  # 裸 -> END：纯收束行，不产行（线性节尾消 loose ends）
            raise ValueError(f"台词.ink 第 {n} 行 divert 仅支持裸 -> END：{raw!r}"
                             "（v1 单行式 -> END # ending: 已废止——结局改两行式："
                             "<落点一句话> # ending: <BE|TE|HE|NE> 内容行 + 单独一行 -> END）")
        if _ENDING_HINT_RE.search(line):
            m = _ENDING_LINE_RE.match(line)
            if not m:
                raise ValueError(f"台词.ink 第 {n} 行结局落点行格式错误：{raw!r}"
                                 "（应为 <落点一句话> # ending: <BE|TE|HE|NE>）")
            rows.append({"op": "ending", "kind": m.group(2), "text": m.group(1).strip(),
                         "scene_block_id": cur_block})
            continue
        if _INLINE_AMBIENT_RE.search(line):
            raise ValueError(f"台词.ink 第 {n} 行内嵌环境音标注已废止（方言 v3）：{raw!r}"
                             "——区间声景改用 bed+ <id> // <语义> … bed- <id>，"
                             "点状音效改用 sfx: <语义>")
        m = _NARRATE_RE.match(line)
        if m:
            rows.append({"op": "narrate", "text": m.group(1).strip(),
                         "scene_block_id": cur_block})
            continue
        if _AMBIENT_RE.match(line):
            raise ValueError(f"台词.ink 第 {n} 行独立环境音行已废止（方言 v3）：{raw!r}"
                             "——点状音效改 sfx: <语义>，区间音床改 bed+ <id> // <语义> … bed- <id>")
        m = _SFX_RE.match(line)
        if m:
            rows.append({"op": "transition", "text": m.group(1).strip(),
                         "scene_block_id": cur_block})
            continue
        m = _BED_START_RE.match(line)
        if m:
            if not m.group(2):
                raise ValueError(f"台词.ink 第 {n} 行 bed+ 缺语义（AudioFly 生成提示语必填）：{raw!r}"
                                 "（应为 bed+ <id> // <语义>）")
            bid = m.group(1)
            if bid in open_beds:
                raise ValueError(f"台词.ink 第 {n} 行音床 {bid} 重复起始"
                                 f"（第 {open_beds[bid][0]} 行已起始且未闭合）")
            open_beds[bid] = (n, cur_block)
            rows.append({"op": "bed_start", "bed": bid, "text": m.group(2).strip(),
                         "scene_block_id": cur_block})
            continue
        m = _BED_END_RE.match(line)
        if m:
            bid = m.group(1)
            if bid not in open_beds:
                raise ValueError(f"台词.ink 第 {n} 行 bed- {bid} 无对应未闭合的 bed+")
            s_ln, s_blk = open_beds.pop(bid)
            if s_blk != cur_block:
                raise ValueError(f"台词.ink 第 {n} 行 bed- {bid} 跨场景块"
                                 f"（bed+ 在第 {s_ln} 行·块 {s_blk}，bed- 在块 {cur_block}）"
                                 "——运行时换段即停床，起止必须在同一场景块内")
            rows.append({"op": "bed_end", "bed": bid, "scene_block_id": cur_block})
            continue
        m = _LLM_RE.match(line)
        if m:
            llm_hints.append((n, m.group(1).strip()))
            continue  # 占位不产行不进图（split 门禁拒绝含占位定稿）
        if _BED_HINT_RE.match(line):
            raise ValueError(f"台词.ink 第 {n} 行音床行格式错误：{raw!r}"
                             "（应为 bed+ <id> // <语义> 或 bed- <id>，id 限 ASCII 字母数字下划线）")
        m = _STITCH_RE.match(line)
        if m:
            rows.append({"op": "label", "text": m.group(1).strip(),
                         "scene_block_id": cur_block})
            continue
        m = _SAY_RE.match(line)
        if m:
            rows.append({"op": "say", "who": m.group(1).strip(),
                         "text": m.group(2).strip(), "scene_block_id": cur_block})
            continue
        raise ValueError(f"台词.ink 第 {n} 行无法解析：{raw!r}"
                         "（方言规范见 chapter-dialoguer references/ink方言规范.md）")
    if not blocks:
        raise ValueError("台词.ink 缺场景块标记行（=== <scene_block_id> // <Scene 名>（<时段>））")
    if open_beds:
        raise ValueError("台词.ink 有未闭合音床：" +
                         "、".join(f"{bid}（第 {ln} 行）" for bid, (ln, _) in open_beds.items()))
    return {"rows": rows, "blocks": blocks, "llm_hints": llm_hints}


def ensure_no_placeholders(parsed: dict) -> None:
    """split 门禁：含 llm: 占位的定稿拒绝拆分进图（占位不产行，静默拆分会丢内容）。
    先由 chapter-dialoguer 填充模式扩写占位，再拆分。"""
    hints = parsed.get("llm_hints") or []
    if hints:
        where = "、".join(f"第 {ln} 行" for ln, _ in hints)
        raise ValueError(f"台词.ink 含 {len(hints)} 处 llm: 占位（{where}）——"
                         "先由 chapter-dialoguer 填充模式扩写占位，再拆分进图")


def _sig(r: dict) -> tuple:
    """对齐签名：ending 用 kind+落点；bed 起止用 bed id（防两个 bed_end 同签名产生配对
    歧义）；narrate 含内嵌氛围语义（v3 已废止内嵌，⟨⟩ 恒空——保留拼接防旧图残留行
    对齐断裂，残留行自然走 update 洗掉）。存量 op=scene（已去图化）必落 delete；
    存量 op=ambient 归一 transition（改名兼容，防历史图行对齐断裂误置 0 重配）。"""
    op = r.get("op")
    if op == "ambient":
        op = "transition"
    if op == "ending":
        return ("ending", "", (r.get("kind") or "") + "——" + (r.get("text") or ""))
    if op in ("bed_start", "bed_end"):
        return (op, r.get("bed") or "", r.get("text") or "")
    if op == "narrate":
        return ("narrate", "", (r.get("text") or "") + "⟨" + (r.get("ambient_text") or "") + "⟩")
    return (op, r.get("who") or "", r.get("text") or "")


def _row_name(m: dict) -> str:
    """行正文即 name。"""
    return m.get("text") or ""


def _wav_exists(voice_key: str) -> bool:
    """母带是否已生成（-1 恢复判定）。路径从 key 自身解析（15_声音/<stem>/<block>/），
    不查图不按角色目录——章改名后图上现算的 stem 会指错旧 wav 位置。"""
    if not voice_key:
        return False
    try:
        return voice_master_path(ROOT, voice_key).exists()
    except ValueError:
        return False


def _purge_line_audio_files(g: dict, report: dict) -> None:
    """删除行时清理其音频产物：母带 + 运行时副本 + Godot .import 伴生。
    say 行按 voice_key（voices 目录），ambient 行按 ambient_track（sfx 目录）。"""
    keys = [k for k in (g.get("voice_key"), g.get("ambient_track")) if k]
    purged = []
    for key in keys:
        try:
            master = voice_master_path(ROOT, key)
        except ValueError:
            continue
        runtime_root = ROOT / "99_game" / "assets" / ("sfx" if key.startswith(("amb-", "bed-")) else "voices")
        for p in (master, runtime_root / f"{key}.wav", Path(str(master) + ".import"),
                  Path(str(runtime_root / f"{key}.wav") + ".import")):
            if p.exists():
                p.unlink()
                purged.append(str(p))
    if purged:
        report.setdefault("purged", []).extend(purged)


# ── 对齐 ─────────────────────────────────────────────────────

def align(script_rows: list, graph_rows: list) -> dict:
    """定稿行 vs 图行（须按 order 升序）→ {keep, update, create, delete} 计划。

    keep   equal：签名全同（text 必相同）。-1 恢复 / 演出字段 diff 在 build_actions 处理
    update replace 块按位置配对：沿用图行 id/order，字段全量更新，status=0（stale 重配）
    create md 独有：新节点（雪花 id）+ order 中点
    delete 图独有：DETACH DELETE（wav 留盘）
    """
    sm = difflib.SequenceMatcher(None, [_sig(r) for r in graph_rows], [_sig(r) for r in script_rows])
    plan = {"keep": [], "update": [], "create": [], "delete": []}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                plan["keep"].append({"graph": graph_rows[i1 + k], "md": script_rows[j1 + k]})
        elif tag == "delete":
            plan["delete"].extend({"graph": g} for g in graph_rows[i1:i2])
        elif tag == "insert":
            plan["create"].extend({"md": m} for m in script_rows[j1:j2])
        else:  # replace：按位置配对，多出部分按删/建
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                plan["update"].append({"graph": graph_rows[i1 + k], "md": script_rows[j1 + k]})
            plan["delete"].extend({"graph": g} for g in graph_rows[i1 + n:i2])
            plan["create"].extend({"md": m} for m in script_rows[j1 + n:j2])
    return plan


def assign_orders(script_rows: list, plan: dict) -> tuple:
    """给最终序列（定稿顺序）分配 order。返回 (seq, reordered)。

    seq = [{md, action, graph?, id, order}]。create 行取上下邻居中点（同缝隙多行均分
    gap/(n+1)）；头/尾插入外推 ±1000；分配后非严格递增（或旧行缺 order）→ 全节重排
    (i+1)*1000（reordered=True，order 不进 voice key，重排安全）。
    """
    by_md = {}
    for action in ("keep", "update"):
        for it in plan[action]:
            by_md[id(it["md"])] = (action, it)
    seq = []
    for m in script_rows:
        hit = by_md.get(id(m))
        if hit:
            action, it = hit
            seq.append({"md": m, "action": action,
                        "graph": it["graph"], "id": it["graph"]["id"],
                        "order": it["graph"].get("ord")})
        else:
            seq.append({"md": m, "action": "create", "graph": None,
                        "id": _GEN.next_id_base62(), "order": None})
    if any(item["action"] != "create" and item["order"] is None for item in seq):
        for i, item in enumerate(seq, 1):  # 旧图行缺 order：直接全节重排
            item["order"] = i * ORDER_STEP
        return seq, True
    _fill_creates(seq)
    if not _strictly_increasing(seq):
        for i, item in enumerate(seq, 1):
            item["order"] = i * ORDER_STEP
        return seq, True
    return seq, False


def _fill_creates(seq: list) -> None:
    """为连续 create 段分配中点 order（同缝隙多行均分；头尾外推）。原地修改。"""
    i = 0
    while i < len(seq):
        if seq[i]["action"] != "create":
            i += 1
            continue
        j = i
        while j < len(seq) and seq[j]["action"] == "create":
            j += 1
        n = j - i
        prev_o = seq[i - 1]["order"] if i > 0 else None
        next_o = seq[j]["order"] if j < len(seq) else None
        if prev_o is None and next_o is None:      # 全新节：顺序铺开
            for k in range(n):
                seq[i + k]["order"] = (k + 1) * ORDER_STEP
        elif prev_o is None:                        # 头部插入：向左外推
            for k in range(n):
                seq[i + k]["order"] = next_o - ORDER_STEP * (n - k)
        elif next_o is None:                        # 尾部插入：向右外推
            for k in range(n):
                seq[i + k]["order"] = prev_o + ORDER_STEP * (k + 1)
        else:                                       # 缝隙均分 (prev, next)
            gap = next_o - prev_o
            step = gap // (n + 1)
            for k in range(n):
                seq[i + k]["order"] = prev_o + step * (k + 1) if step > 0 else prev_o
        i = j


def _strictly_increasing(seq: list) -> bool:
    return all(a["order"] < b["order"] for a, b in zip(seq, seq[1:]))


# ── 动作生成（恢复 / 演出 diff / 字段更新 / 建删） ──────────────

def _set_props(m: dict, pos) -> str:
    """行字段全量 SET 子句（update/create 用）。status：音频行（say 配音 / transition
    点状音效 / bed_start 音床起）=0 待产；其余非音频行（纯 narrate/label/ending/
    bed_end）=11。ambient_text 恒写 null（v3 内嵌已废止，自愈旧图残留）。"""
    return ", ".join([
        f"l.name={_q(_row_name(m))}",
        f"l.op={_q(m['op'])}",
        f"l.who={_q(m.get('who'))}",
        f"l.pos={_q(pos)}",
        f"l.text={_q(m.get('text'))}",
        f"l.kind={_q(m.get('kind'))}",
        f"l.bed={_q(m.get('bed'))}",
        f"l.scene_block_id={_q(m.get('scene_block_id'))}",
        f"l.ambient_text={_q(m.get('ambient_text'))}",
        f"l.text_sha1={_q(text_sha1(m.get('text') or ''))}",
        f"l.status={0 if m['op'] in ('say', 'transition', 'bed_start') else 11}",
    ])


def build_actions(seq: list, plan: dict, sc_id: str) -> tuple:
    """最终序列 → (cypher 语句列表, 报告 dict)。含 keep 的 -1 恢复、块归属补写与演出字段 diff。"""
    stmts = []
    report = {"counts": {"kept": 0, "created": 0, "updated": 0, "deleted": 0, "restored": 0},
              "created": [], "updated": [], "deleted": [], "restored": [], "warnings": []}

    for it in plan["delete"]:  # 图有 md 无：删行 + 清理音频产物（母带/运行时副本/.import）
        g = it["graph"]
        _purge_line_audio_files(g, report)
        stmts.append(f"MATCH (l:LineAudio {{id:{_q(g['id'])}}}) DETACH DELETE l;")
        report["deleted"].append({"id": g["id"], "op": g.get("op"),
                                  "text": (g.get("text") or "")[:30]})

    pos_map = {}  # 块内 who → 规则立绘位（块级分配：对话分侧/单人靠左，块切换重算）
    prev_block = None
    for idx, item in enumerate(seq):
        m, action, oid, order = item["md"], item["action"], item["id"], item["order"]
        if m.get("scene_block_id") != prev_block:
            prev_block = m.get("scene_block_id")
            blk_rows = []
            for it2 in seq[idx:]:
                if it2["md"].get("scene_block_id") != prev_block:
                    break
                blk_rows.append(it2["md"])
            pos_map = _block_pos_map(blk_rows)
        if action == "create":
            pos = pos_map.get(m.get("who") or "") if m["op"] == "say" else None
            stmts.append(
                f"MERGE (l:LineAudio {{id:{_q(oid)}}}) "
                f"ON CREATE SET {_set_props(m, pos)} "
                f"WITH l MATCH (sc:SecScript {{id:{_q(sc_id)}}}) "
                f"MERGE (sc)-[r:produces]->(l) SET r.order={order}, r.sync=true;"
            )
            report["created"].append({"id": oid, "op": m["op"], "order": order,
                                      "text": (m.get("text") or m.get("scene_block_id") or "")[:30]})
        elif action == "update":  # 台词变了（stale）：沿用 id/order，全量更新，置 0 重配
            g = item["graph"]
            pos = g.get("pos")
            if m["op"] == "say":
                pos = pos_map.get(m.get("who") or "") or pos
            stmts.append(f"MATCH (l:LineAudio {{id:{_q(oid)}}}) SET {_set_props(m, pos)};")
            if m["op"] == "say":
                pos_map[m.get("who") or ""] = pos or SAY_DEFAULT_POS
            report["updated"].append({"id": oid, "op": m["op"],
                                      "text": (m.get("text") or "")[:30]})
        else:  # keep：未变行。仅 -1 恢复、演出字段 diff（op 归一/pos）与块归属补写，status 0/10/11 原样保留
            g = item["graph"]
            if g.get("op") == "ambient" and m["op"] == "transition":
                # 存量 op=ambient 改名归一（幂等自愈；_sig 已归一防对齐断裂，此处落图）
                stmts.append(f"MATCH (l:LineAudio {{id:{_q(oid)}}}) SET l.op='transition';")
                g = {**g, "op": "transition"}
            if g.get("scene_block_id") != m.get("scene_block_id"):
                # scene 行去图化的存量迁移：行上补写块归属（不动 status，幂等）
                stmts.append(f"MATCH (l:LineAudio {{id:{_q(oid)}}}) "
                             f"SET l.scene_block_id={_q(m.get('scene_block_id'))};")
            if g.get("status") == -1:
                # 非音频行恢复 11；音频行按「键在 +（say 另需 text_sha1 匹配）+ 母带 wav 在」恢复 10
                # （transition/bed_start 音频行：ambient_track 在且母带在 → 10 否则 0——
                # 修复历史死条件：md 侧 op 永不为 'ambient'，旧写法实际落 else 置 11 违反
                # ambient-sfx-designer「track 在+wav 在→10 否则 0」的宣称）
                track = g.get("ambient_track")
                if m["op"] == "say":
                    ok = g.get("voice_key") and g.get("text_sha1") == text_sha1(m.get("text") or "") \
                        and _wav_exists(g.get("voice_key"))
                    new_status = 10 if ok else 0
                elif m["op"] in ("transition", "bed_start"):
                    new_status = 10 if (track and _wav_exists(track)) else 0
                else:
                    new_status = 11
                stmts.append(f"MATCH (l:LineAudio {{id:{_q(oid)}}}) SET l.status={new_status};")
                report["restored"].append({"id": oid, "to": new_status})
            if m["op"] == "say":
                want = pos_map.get(m.get("who") or "")
                if want and g.get("pos") != want:  # 演出 diff：存量 pos 与块规则不一致 → 自愈补写
                    stmts.append(f"MATCH (l:LineAudio {{id:{_q(oid)}}}) SET l.pos={_q(want)};")
                    report.setdefault("pos_fixed", []).append({"id": oid, "to": want})
            report["counts"]["kept"] += 1

    report["counts"].update(created=len(report["created"]), updated=len(report["updated"]),
                            deleted=len(report["deleted"]), restored=len(report["restored"]))
    return stmts, report


def _order_statements(seq: list, sc_id: str, reordered: bool) -> list:
    """order 写入：create 行已在建边语句带 order；重排时对已有行补 SET order。"""
    if not reordered:
        return []
    return [
        f"MATCH (sc:SecScript {{id:{_q(sc_id)}}})-[r:produces]->(l:LineAudio {{id:{_q(item['id'])}}}) "
        f"SET r.order={item['order']};"
        for item in seq if item["action"] != "create"
    ]


# ── split 主流程 ─────────────────────────────────────────────

def split(section_id: str, dry_run: bool = False) -> dict:
    """拆分对齐进图。前置：SecScript=11。返回报告 dict（查询/解析/写图失败 raise）。"""
    rows = _run_cypher(
        "MATCH (:Section {id:'" + section_id + "'})-[:has_outline]->(:SecOutline)"
        "-[:produces]->(sc:SecScript) "
        "RETURN sc.id AS sc_id, sc.script_path AS p, sc.status AS st LIMIT 1"
    )
    if not rows:
        raise ValueError(f"Section {section_id} 无 SecScript（先跑 chapter-dialoguer 产定稿）")
    sc_id, script_path, st = rows[0]["sc_id"], rows[0]["p"], rows[0]["st"]
    if st != 11:
        raise ValueError(f"SecScript.status={st}（须 11 定稿已批才能拆分进图）")
    if not script_path:
        raise ValueError("SecScript.script_path 为空")
    parsed = parse_ink(script_path)
    ensure_no_placeholders(parsed)  # llm: 占位定稿拒绝拆分（防占位内容静默丢失）
    script_rows, blocks = parsed["rows"], parsed["blocks"]

    graph_rows = _run_cypher(
        "MATCH (sc:SecScript {id:'" + sc_id + "'})-[p:produces]->(l:LineAudio) "
        "RETURN l.id AS id, l.op AS op, l.who AS who, l.pos AS pos, "
        "l.text AS text, l.kind AS kind, l.bed AS bed, l.scene_block_id AS scene_block_id, "
        "l.ambient_text AS ambient_text, "
        "l.status AS status, l.attempts AS attempts, l.voice_key AS voice_key, "
        "l.ambient_track AS ambient_track, l.text_sha1 AS text_sha1, p.order AS ord "
        "ORDER BY p.order"
    )

    plan = align(script_rows, graph_rows)
    seq, reordered = assign_orders(script_rows, plan)
    stmts, report = build_actions(seq, plan, sc_id)
    # 块定义写入 SecScript.scene_blocks（scene 行已去图化，块元数据的图上落点）
    stmts.append(f"MATCH (sc:SecScript {{id:{_q(sc_id)}}}) "
                 f"SET sc.scene_blocks={_q(json.dumps(blocks, ensure_ascii=False))};")
    stmts = _order_statements(seq, sc_id, reordered) + stmts
    report.update({"section_id": section_id, "sc_id": sc_id, "script_path": script_path,
                   "reordered": reordered, "statements": len(stmts), "dry_run": dry_run,
                   "blocks": blocks})
    if stmts and not dry_run:
        _run_cypher_multi(stmts)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="台词.ink 拆分对齐进图（SecScript→逐句 LineAudio）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_split = sub.add_parser("split", help="拆分进图")
    p_split.add_argument("--section", required=True, help="Section 节点 ID（snowflake）")
    p_split.add_argument("--report", help="报告 JSON 落盘路径（缺省仅 stdout）")
    p_split.add_argument("--dry-run", action="store_true", help="只产计划不写图")
    args = ap.parse_args(argv)

    try:
        report = split(args.section, dry_run=args.dry_run)
    except (ValueError, RuntimeError) as e:
        sys.stderr.write(f"拆分失败: {e}\n")
        return 1
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    print(text)
    c = report["counts"]
    print(f"OK: kept={c['kept']} created={c['created']} updated={c['updated']} "
          f"deleted={c['deleted']} restored={c['restored']} reordered={report['reordered']}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
