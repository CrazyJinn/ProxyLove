"""从图投影全章各节台词行（LineAudio），合并拍平为单一章运行时 JSON。

chapter-publisher 在全章各节产物就绪时调用：图（Section-produces{order}->LineAudio 逐句行）
+ 台词.ink（舞台调度）→ 1 个章级 JSON。台词.jsonl 已停产，图是内容行的结构化真相。

- 图查询：Chapter→has_section→Section(按 section_no)→produces→LineAudio
  -[p:produces]->LineAudio（ORDER BY p.order）；块时段另查 Scene.time_of_day；立绘整键另查
  uses 边（fetch_uses_portrait_keys，与 scene_times 同款二次查询——防主查询行乘积）。
- 舞台调度（say.pos / hide 下台行）自 ink 注入：复用
  script_splitter 的 parse_ink/座位算法/对齐签名（单一实现防两份解析器漂移）；ink
  内容行与图行逐行 _sig 校验，漂移即报错引导重拆（发布 gate 保证拆分后两边同构）。
- 投影：graph_lines_to_doc（ink 行序驱动）→ {meta, scenes}（requires 从行推导；
  voice_key→voice；say.portrait = uses 边解析的 guid 整键，无边的 say 行空串并计缺口；
  say.pos = 块规则座位 + stage/pos 声明现算；hide 行由 ink 直出）。
- meta：chapter/title 取 Chapter 节点；requires = 各节并集（保序去重）。
- scenes：按节序拼接各 scene-block（块 id=scene_id——同机位多段为同 id 多区间，段序由行序承载；跨节同名 id 由章级拼接天然加节前缀去重）。
- BGM 注入：--chapter-map 的 bgm 段（Scene-has_bgm->BgmTrack，status=2 才进 map）写入 scene-block.bgm。
- 合并后校验 scene-block id 章内唯一（防御性）。
- 部分发布：--sections 0,1 仅合并指定节（section_no 逗号分隔）——章内其余节未就绪时
  先发已就绪节；前置校验仅针对所选节。全量重发覆盖同 stem 文件（幂等）。

前置校验：各节 Section.status=11 ∧ 该节全部行 LineAudio=11（不满足报缺口并退出）。
choice/jump 行暂不进图（建模后续设计），投影自然不含分支跳转行。
不做 schema 校验（校验由 validate_chapter.py 负责，保持工具正交）。
退码：0 成功 / 1 查图/校验/IO 失败 / 2 参数错。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from portrait_key import make_key

_REPO_ROOT = Path(__file__).resolve().parents[2]  # Asset 项目根（图上 rel_path 的锚）
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
CYPHER_EXEC = _SCRIPTS_DIR / "cypher_exec.py"

# 复用主线拆分器的 ink 解析/座位算法/对齐签名（单一实现，防两份解析器漂移）
_SPLITTER_DIR = _REPO_ROOT / ".claude" / "skills" / "section-voice-publisher" / "scripts"
sys.path.insert(0, str(_SPLITTER_DIR))
from script_splitter import parse_ink_text, _block_pos_map, _sig, SAY_DEFAULT_POS  # noqa: E402


def _run_cypher(cypher: str) -> list:
    """调 cypher_exec.py --json，提取返回的 JSON 数组（与 generate_portrait_map 同款）。"""
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


# Day/节标题解析：ink 是唯一来源（人读人改的唯一定稿格式），发布搬运时投影进章 JSON。
# 节级 = 首行头注释「// 第N章 Day X[-Y] 节标题（备注…）」；块级 = knot 头括号「（Day Y · …）」覆盖。
_DAY_SEC_RE = re.compile(r"^//\s*第.+?章\s+Day\s*(\d+)(?:-(\d+))?\s*(.+?)\s*(?:[（(].*)?$", re.M)
_DAY_BLK_RE = re.compile(r"^===\s+(\S+)\s*(.*)$", re.M)


def _parse_ink_days(raw_ink: str):
    """→ (sec_day|None, sec_title|None, {block_id: day})。头注释无 Day（如序章）→ 全 None/空。

    实测形态：「// 第一章 Day 9-10 咖啡店邀约（入场券 · 小说版 2026-10-06）」→ (9, 咖啡店邀约,
    {s09_pm: 9, s09_cafe: 10})——块级 Day 9/10 覆盖节级区间起值，段内跨日天然正确。
    """
    m = _DAY_SEC_RE.search(raw_ink)
    sec_day = int(m.group(1)) if m else None
    sec_title = m.group(3).strip() if m else None
    blk_days = {}
    for bid, rest in _DAY_BLK_RE.findall(raw_ink):
        dm = re.search(r"Day\s*(\d+)", rest)
        if dm:
            blk_days[bid] = int(dm.group(1))
    return sec_day, sec_title, blk_days


def graph_lines_to_doc(lines: list, blocks, scene_times: dict, chapter_no, sec_title: str,
                       portrait_keys: dict = None, ink: dict = None,
                       sec_day: int = None, ink_title: str = None, block_days: dict = None) -> dict:
    """一节投影：ink 行序驱动（舞台调度）+ 图行内容对齐（音频/选绘）→ doc {meta, scenes}。

    ink = parse_ink_text(台词.ink) 结果 {rows(含 hide), pos_overrides}——舞台调度
    （say.pos / hide 行）的唯一事实源。开投影前先校验 ink
    内容行（除 hide）与图行逐行 _sig 同构——漂移即 raise 引导重拆（发布 gate 保证
    拆分后两边一致）。

    blocks = 行 scene_block_id 派生块表 [{block, scene_name, time}]；
    portrait_keys = {行id: 立绘 guid 整键}（fetch_uses_portrait_keys 沿 uses 边解析——
    say.portrait 的唯一来源，无边的 say 行投影空串）。
    内容文本取 ink 行（内容权威）；音频/选绘事实取图行（voice_key/ambient_track/lid）。
    say.pos = 块规则座位（_block_pos_map 块内首话序）+ stage/pos 声明覆盖，现算；
    hide 行由 ink 直出。label 行 text → name；ending 行 text → title；say 行 voice_key → voice；
    transition 行（方言 v3 的 sfx: 点状音效）→ {"op":"transition","track"}（运行时等播完再推进）；
    bed_start/bed_end 行（音床起止）→ {"op","bed","track"} / {"op","bed"}（运行时区间循环/停止）。
    """
    portrait_keys = portrait_keys or {}
    ink_rows = (ink or {}).get("rows") or []
    pos_overrides = (ink or {}).get("pos_overrides") or {}
    content = [r for r in ink_rows if r.get("op") != "hide"]
    if len(content) != len(lines) or any(_sig(a) != _sig(b) for a, b in zip(content, lines)):
        raise ValueError(
            f"sec「{sec_title}」图行与 台词.ink 内容行不同构"
            f"（图 {len(lines)} 行 vs ink {len(content)} 内容行）——重跑 section-voice-publisher"
            " 拆分进图（幂等对齐）后再发布")

    chars, scenes_seq, portraits = [], [], []
    def _keep(seq, v):
        if v and v not in seq:
            seq.append(v)

    scenes = [{"id": b["block"], "scene": b.get("scene_name") or "",
               **({"time": b["time"]} if b.get("time") else {})} for b in blocks]
    for s in scenes:
        _keep(scenes_seq, s["scene"])
    # Day 过场数据（ink 是唯一来源，此处只搬运）：节标题 + 块 day（块级覆盖，缺省节级；
    # 无日（如序章）两键都不写，运行时节间不播 Day 过场）
    if ink_title:
        for s in scenes:
            s["section_title"] = ink_title
            d = (block_days or {}).get(s["id"], sec_day)
            if d is not None:
                s["day"] = d

    rows_by_block = {}
    for r in ink_rows:
        rows_by_block.setdefault(r.get("scene_block_id"), []).append(r)
    block2scene = {b["block"]: s for b, s in zip(blocks, scenes)}
    cur = None
    prev_block = None
    pos_map = {}
    gi = 0  # 图行指针（content 与 lines 同序同构，已校验）
    for m in ink_rows:
        if m.get("scene_block_id") != prev_block:  # 换块：切块 + 重算座位表（块规则 + 声明覆盖）
            prev_block = m.get("scene_block_id")
            cur = block2scene.get(prev_block)
            pos_map = _block_pos_map(rows_by_block.get(prev_block) or [])
            pos_map.update(pos_overrides.get(prev_block) or {})
        if cur is None:
            continue  # 行的块归属不在 blocks 定义里（数据异常），防御跳过
        op = m.get("op")
        if op == "hide":  # 舞台调度：ink 直出（不落图）。清 slots 中该角色槽。
            if m.get("who"):
                cur.setdefault("lines", []).append({"op": "hide", "who": m["who"]})
            continue
        l = lines[gi]
        gi += 1
        if op == "say":
            say = {"op": "say", "who": m.get("who") or "",
                   "portrait": portrait_keys.get(l.get("lid")) or "",
                   "pos": pos_map.get(m.get("who") or "") or SAY_DEFAULT_POS,
                   "text": m.get("text") or ""}
            if l.get("voice_key"):
                say["voice"] = l["voice_key"]
            cur.setdefault("lines", []).append(say)
            _keep(chars, m.get("who"))
            _keep(portraits, say["portrait"])
        elif op == "narrate":
            # narrate 纯文本行（方言 v3 起内嵌氛围已废止迁移为 bed±）
            cur.setdefault("lines", []).append({"op": "narrate", "text": m.get("text") or ""})
        elif op == "transition":
            # 点状音效独立行（方言 v3 的 sfx: 语法）→ {"op":"transition"}（运行时等播完再推进）。
            # track 缺失静默跳过——发布 gate 全行 11 保证产音后 track 必在。
            if l.get("ambient_track"):
                cur.setdefault("lines", []).append({"op": "transition", "track": l["ambient_track"]})
        elif op == "bed_start":
            # 音床起：{"op":"bed_start"}（运行时循环播放直到 bed_end/换段）；track 缺失静默跳过同上
            if l.get("ambient_track"):
                cur.setdefault("lines", []).append(
                    {"op": "bed_start", "bed": m.get("bed") or "", "track": l["ambient_track"]})
        elif op == "bed_end":
            # 音床止：{"op":"bed_end"}（运行时停对应床；幂等）
            cur.setdefault("lines", []).append({"op": "bed_end", "bed": m.get("bed") or ""})
        elif op == "label":
            cur.setdefault("lines", []).append({"op": "label", "name": m.get("text") or ""})
        elif op == "choice":
            # 选择行（ink 侧 options 本就是 list）→ {"op":"choice","options":[...]}（运行时
            # 阻塞弹选项，choose 沿 to/scene/leads_to_ending 跳转）。
            opts = m.get("options")
            if isinstance(opts, list) and opts:
                cur.setdefault("lines", []).append({"op": "choice", "options": opts})
        elif op == "ending":
            end = {"op": "ending", "kind": m.get("kind") or "NE"}
            if m.get("text"):
                end["title"] = m["text"]
            cur.setdefault("lines", []).append(end)

    meta = {"chapter": chapter_no, "title": sec_title,
            "requires": {"characters": chars, "scenes": scenes_seq, "portraits": portraits}}
    return {"meta": meta, "scenes": scenes}


def _parse_section_nos(spec: str) -> set:
    """'0,1' → {0,1}（容错空白/小数/str 数字）；非法或空集报 ValueError。"""
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(float(part)))
        except ValueError:
            raise ValueError(f"--sections 含非法节号: {part!r}（应为逗号分隔 section_no，如 0,1）")
    if not out:
        raise ValueError("--sections 不能为空（如需全章发布请省略该参数）")
    return out


def _in_sections(no, wanted) -> bool:
    """行/节的 section_no 是否在所选集（None 时全选；no 缺失/非数不选）。"""
    if wanted is None:
        return True
    if no is None:
        return False
    try:
        return int(no) in wanted
    except (TypeError, ValueError):
        return False


def fetch_uses_portrait_keys(chapter_id: str, section_nos=None) -> tuple:
    """沿 uses 边解析全章 say 行立绘整键 → ({行id: 整键}, [缺边行id])。

    与 scene_times 同款的二次查询模式（主查询不内联 OPTIONAL uses 边——防行乘积破坏
    逐行投影）。costume 经 stand 自身 IllusDesign 回溯（stand 唯一 → 键唯一，同场换装
    歧义结构上不存在）；孤儿立绘（无 outfit_for）→ make_key 的 None costume 三段键。
    section_nos={0,1} 时仅解析所选节（部分发布——未选节的缺边行不进 missing 警告）。
    """
    rows = _run_cypher(
        "MATCH (ch:Chapter {id:'" + chapter_id + "'})-[:has_section]->(sec:Section)"
        "-[:produces]->(l:LineAudio) "
        "WHERE l.op = 'say' "
        "OPTIONAL MATCH (l)-[:uses]->(st:StandingIllustration) "
        "OPTIONAL MATCH (illus:IllusDesign)-[:expands_to]->(st) "
        "OPTIONAL MATCH (costume:CostumeStyle)-[:outfit_for]->(illus) "
        "RETURN l.id AS lid, l.who AS who, st.id AS stand_id, st.variant_label AS variant, "
        "costume.name AS costume, sec.section_no AS sno"
    )
    keys, missing, seen = {}, [], set()
    for r in rows:
        if not _in_sections(r.get("sno"), section_nos):
            continue
        lid = r.get("lid")
        if not r.get("stand_id"):
            missing.append(lid)
            continue
        if lid in seen:      # 防御：多 costume/多 illus 回溯行乘积，取首行
            continue
        seen.add(lid)
        keys[lid] = make_key(r.get("who") or "", r.get("variant") or "",
                             r.get("stand_id"), r.get("costume"))
    return keys, missing


def fetch_chapter(chapter_id: str, section_nos=None) -> dict:
    """查全章图 → {chapter_no, title, sections: [投影doc 按节序]}；前置不满足 raise ValueError。

    前置：每节 Section.status=11 ∧ 该节全部行 LineAudio=11。
    section_nos={0,1} 时部分发布：仅投影所选节，前置校验也仅针对所选节（章内其余节
    可未就绪）——供先发已就绪节；全量重发覆盖同 stem 文件。
    """
    rows = _run_cypher(
        "MATCH (ch:Chapter {id:'" + chapter_id + "'})-[:has_section]->(sec:Section) "
        "OPTIONAL MATCH (sec)-[p:produces]->(l:LineAudio) "
        "RETURN ch.chapter_no AS no, ch.title AS title, sec.section_no AS section_no, "
        "sec.title AS sec_title, sec.status AS sc_status, "
        "sec.script_path AS script_path, "
        "l.id AS lid, l.op AS op, l.who AS who, l.pos AS pos, "
        "l.text AS text, l.kind AS kind, l.bed AS bed, l.scene_block_id AS scene_block_id, "
        "l.voice_key AS voice_key, l.ambient_track AS ambient_track, l.options AS options, "
        "l.status AS line_status, p.order AS ord "
        "ORDER BY sec.section_no, p.order"
    )
    if not rows:
        raise ValueError(f"Chapter {chapter_id} 不存在或无 Section")
    if section_nos is not None:
        avail = sorted({int(r["section_no"]) for r in rows if r.get("section_no") is not None})
        rows = [r for r in rows if _in_sections(r.get("section_no"), section_nos)]
        if not rows:
            raise ValueError(
                f"Chapter {chapter_id} 下不存在 section_no ∈ {sorted(section_nos)} 的节（现有节号: {avail}）"
            )
        sys.stderr.write(
            f"[info] 部分发布：仅合并 section_no ∈ {sorted(section_nos)}（全章节号: {avail}）\n"
        )
    chapter_no, chapter_title = rows[0]["no"], rows[0]["title"]

    # 块时段/块结构：行 scene_block_id（=scene_id）直查 Scene——
    # id 直连取 time_of_day 与场景名（ink 注释名仅供人读，投影以图为准）
    scene_of = {}
    bid_set = sorted({r["scene_block_id"] for r in rows if r.get("scene_block_id")})
    if bid_set:
        for t in _run_cypher(
                "MATCH (s:Scene) WHERE s.id IN ["
                + ",".join("'" + b.replace("'", "\\'") + "'" for b in bid_set)
                + "] RETURN s.id AS bid, s.name AS name, s.time_of_day AS t"):
            scene_of[t["bid"]] = {"scene_name": t.get("name") or "", "time": t.get("t") or ""}

    # 立绘整键：沿 uses 边二次查询（say 行无 uses = 选绘缺口，发布警告、投影空串）
    portrait_keys, no_uses = fetch_uses_portrait_keys(chapter_id, section_nos=section_nos)
    if no_uses:
        preview = ", ".join(no_uses[:5])
        sys.stderr.write(f"[warn] {len(no_uses)} 句 say 行缺 uses 选绘边（章 JSON 该句 portrait 为空串，"
                         f"运行时占位图兜底）: {preview}{'…' if len(no_uses) > 5 else ''}\n")

    by_sec = {}
    for r in rows:
        key = (r["section_no"], r["sec_title"], r["sc_status"])
        by_sec.setdefault(key, []).append(r)

    problems, sections = [], []
    for (section_no, sec_title, sc_status), sec_rows in sorted(by_sec.items()):
        sec_tag = f"sec{int(section_no):02d}（{sec_title}）"
        if sc_status != 11:
            problems.append(f"{sec_tag}：Section.status={sc_status}（须 11 定稿已确认）")
            continue
        line_rows = [r for r in sec_rows if r.get("lid")]
        if not line_rows:
            problems.append(f"{sec_tag}：无 LineAudio 行（先跑 section-voice-publisher 拆分进图）")
            continue
        # 块结构从行派生（保序去重）：块 id=scene_id 直连图
        blocks = []
        _seen_b = set()
        for r in line_rows:
            b = r.get("scene_block_id")
            if b and b not in _seen_b:
                _seen_b.add(b)
                info = scene_of.get(b)
                if not info:
                    problems.append(f"{sec_tag}：行块 id {b} 不命中图 Scene（非 scene_id？）")
                    continue
                blocks.append({"block": b, "scene_name": info["scene_name"],
                               "time": info["time"]})
        if problems:
            continue
        not_done = [r for r in line_rows if r.get("line_status") != 11]
        if not_done:
            problems.append(f"{sec_tag}：{len(not_done)} 行 LineAudio.status≠11"
                            f"（逐句音频审未完成，如 {(not_done[0].get('text') or '')[:20]!r}）")
            continue
        # 舞台调度自 ink 注入：读该节定稿 → 解析（复用拆分器，同构由投影前校验保证）
        sp_rel = sec_rows[0].get("script_path")
        if not sp_rel:
            problems.append(f"{sec_tag}：Section.script_path 缺失（舞台调度自 ink 注入，无法投影）")
            continue
        try:
            raw_ink = (_REPO_ROOT / sp_rel).read_text(encoding="utf-8")
            ink = parse_ink_text(raw_ink)
        except OSError as e:
            problems.append(f"{sec_tag}：台词.ink 读取失败（{sp_rel}）：{e}")
            continue
        # Day/节标题自 ink 解析（同一份原文双用）；非序章却解析不到 Day → 头注释可能被改坏
        sec_day, ink_title, blk_days = _parse_ink_days(raw_ink)
        if sec_day is None and int(chapter_no) > 0:
            sys.stderr.write(f"[warn] {sec_tag}：ink 头注释未解析到 Day，本节 day/节标题不注入\n")
        try:
            sections.append(graph_lines_to_doc(line_rows, blocks, {}, chapter_no, sec_title,
                                               portrait_keys=portrait_keys, ink=ink,
                                               sec_day=sec_day, ink_title=ink_title, block_days=blk_days))
        except ValueError as e:
            problems.append(str(e))
    if problems:
        scope = "所选节" if section_nos is not None else "全章"
        raise ValueError(f"{scope}产物未就绪：\n  " + "\n  ".join(problems))
    return {"chapter_no": chapter_no, "title": chapter_title, "sections": sections}


def _stage_lint_doc(doc: dict) -> list:
    """章级舞台兜底校验（轻量副本，权威实现在 section-voice-publisher 的
    script_splitter._stage_lint——拆分期是唯一闸门，此处只打警告防手工改图绕过拆分器）。
    回放 say 写槽 / hide 清槽 / 换块清场，返回 issues（不阻断发布）。
    """
    issues = []
    for s in doc.get("scenes", []):
        # choice 分支不可线性回放（双分支各自 hide 同一角色会串行误报）——有 choice 的块
        # 跳过「无效 hide」，其余规则照报（与 splitter._stage_lint 同口径）
        has_choice = any(l.get("op") == "choice" for l in s.get("lines", []))
        slots = {}
        for i, l in enumerate(s.get("lines", [])):
            if l.get("op") == "say":
                pos, who = l.get("pos") or "left", l.get("who") or ""
                if pos == "center":
                    issues.append((s.get("id", "?"), i, "stage-warn", f"{who}@center（center 已停用，双槽模型）"))
                prev = slots.get(pos)
                if prev and prev != who:
                    issues.append((s.get("id", "?"), i, "stage-error",
                                   f"{who}@{pos} 覆盖 {prev}（撞槽换绘）"))
                slots[pos] = who
                if len(slots) == 2 and "center" in slots and not ({"left", "right"} <= set(slots)):
                    issues.append((s.get("id", "?"), i, "stage-warn", f"{who} 双人偏构图 {sorted(slots)}"))
                if len(slots) >= 3:
                    issues.append((s.get("id", "?"), i, "stage-warn", f"{who} 三人满场"))
            elif l.get("op") == "hide":
                w = l.get("who") or ""
                if w not in slots.values() and not has_choice:
                    issues.append((s.get("id", "?"), i, "stage-warn", f"无效 hide {w}"))
                slots = {k: v for k, v in slots.items() if v != w}
    return issues


def _union(*lists):
    """保序去重并集（None 安全：缺省子字段视作空）。"""
    out = []
    seen = set()
    for lst in lists:
        for x in (lst or []):
            if x not in seen:
                seen.add(x)
                out.append(x)
    return out


def _inject_bgm(scenes, bgm_map):
    """把 bgm_map（{scene_name: {track, mode, loop}}）写入对应 scene-block 的 bgm 字段。

    map 由 generate_portrait_map.py 查图产出（仅 status=2 的 BgmTrack 进 map，
    未就绪的上游已打警告）。mode/loop 在 map 侧已填默认（play/true），此处原样写入。
    """
    for blk in scenes:
        info = bgm_map.get(blk.get("scene"))
        if not info or not info.get("track"):
            continue
        blk["bgm"] = {"track": info["track"], "mode": info.get("mode", "play"), "loop": info.get("loop", True)}


def merge(sections, chapter, title, chapter_map=None):
    """合并各节投影 doc（按节序，fetch_chapter.sections 或手工构造）→ {meta, scenes}。

    say.portrait 已在各节投影期沿 uses 边解析为 guid 整键（graph_lines_to_doc），
    requires.portraits 即投影结果的并集。chapter_map 非 None 时（generate_portrait_map.py
    产出，现仅 bgm 段）注入 scene-block.bgm；为 None 时不处理。
    """
    # requires 并集（characters/scenes/portraits）
    reqs = [(s.get("meta", {}) or {}).get("requires", {}) or {} for s in sections]
    requires = {
        "characters": _union(*[r.get("characters") for r in reqs]),
        "scenes": _union(*[r.get("scenes") for r in reqs]),
        "portraits": _union(*[r.get("portraits") for r in reqs]),
    }

    # scenes 按节序拼接 + id 章内唯一性校验
    scenes = []
    seen_ids = set()
    for s in sections:
        for blk in s.get("scenes", []) or []:
            bid = blk.get("id")
            if bid in seen_ids:
                raise ValueError(
                    f"scene-block id 重复（非章内唯一）：{bid!r}——structurer 应在分节规划时预分配唯一 id"
                )
            seen_ids.add(bid)
            scenes.append(blk)

    # BGM 注入（chapter-map 现仅 bgm 段）
    if chapter_map:
        bgm_map = chapter_map.get("bgm") or {}
        if bgm_map:
            _inject_bgm(scenes, bgm_map)

    return {"meta": {"chapter": chapter, "title": title, "requires": requires}, "scenes": scenes}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="从图投影全章台词行合并为章运行时 JSON（图内容行 + ink 舞台调度 → 1 拍平）")
    p.add_argument("--chapter", required=True, help="Chapter 节点 ID（snowflake）")
    p.add_argument("-o", "--out", required=True, help="输出章 JSON 路径")
    p.add_argument("--chapter-map", default=None,
                   help="章映射 JSON 路径（generate_portrait_map.py 产出，现仅 bgm 段）；"
                        "传入则注入 scene-block.bgm（say.portrait 已在投影期沿 uses 边解析为整键）")
    p.add_argument("--sections", default=None,
                   help="部分发布：仅合并指定节（逗号分隔 section_no，如 0,1）；"
                        "前置校验仅针对所选节，章内其余节可未就绪。缺省=全章")
    args = p.parse_args(argv)

    chapter_map = None
    if args.chapter_map:
        try:
            chapter_map = json.loads(Path(args.chapter_map).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            sys.stderr.write(f"读取 chapter-map 失败: {e}\n")
            return 1

    try:
        section_nos = _parse_section_nos(args.sections) if args.sections else None
        info = fetch_chapter(args.chapter, section_nos=section_nos)
        doc = merge(info["sections"], info["chapter_no"], info["title"], chapter_map)
    except (RuntimeError, ValueError) as e:
        sys.stderr.write(f"合并失败: {e}\n")
        return 1
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for bid, i, tag, detail in _stage_lint_doc(doc):
        print(f"[{tag}] scene={bid} line#{i}: {detail}")
    print(f"OK: {len(info['sections'])} 节合并 -> {args.out}（{len(doc['scenes'])} 场景段）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
