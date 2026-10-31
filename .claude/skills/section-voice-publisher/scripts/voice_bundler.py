"""voice 资源键生成与图行级 audio 绑定（搬运层共享逻辑）。

被 section-voice-publisher / chapter-publisher 与手动流程共用，保证
「wav/ogg 文件名 / manifest.voices 键 / 章 JSON 的 say.voice 字段」三处对齐。

键格式（2026-10-31 id 锚定重构后）：**键 = hexid(行节点id)**（16 位小写 hex）。
  - NTFS 大小写不敏感与 Base62 不兼容（同批 id 共享前缀仅末位大小写不同），
    凡进文件名/manifest 键的 id 一律 to_hexid（snowflake_base62.py，可逆）。
  - 母带唯一权威 = 图行属性 master_path（15_声音/<ch_hexid>/<block_hexid>/<行_hexid>.wav），
    键仅作运行时文件名主体；voice_key 与 ambient_track 值均为 hexid(行 id)，
    「voice 还是 sfx」由字段来源（谁非空）区分，不再依赖 amb-/bed- 前缀。
  - 稳定寻址不变：md 插入/删除/移动行不改变其他行的 key（wav 不成孤儿）。

legacy（仅存量兼容，过渡期后删）：旧四段键 <char>-<stem>-<block>-<行id> 的
split_voice_key / voice_master_path / chapter_stem_from_meta——服务 2026-10-31
迁移前的存量键反解，不再用于新键生成。

节级挑行/绑定走图（tasks-from-graph / bind-graph，经 cypher_exec.py）：
拆分对齐进图见 script_splitter.py（section-voice-publisher 第一步）。
与 portrait_key.make_key 同源设计：纯函数无 I/O、三处对齐契约。
"""
import argparse
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


_REPO_ROOT = _find_repo_root(Path(__file__).resolve())
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
CYPHER_EXEC = _SCRIPTS_DIR / "cypher_exec.py"

from snowflake_base62 import to_hexid  # noqa: E402

# 键进入 wav/ogg 文件名（assets/voices/<key>.wav），需清洗 Windows 非法字符
_ILLEGAL = re.compile(r'[\\/:*?"<>|]')


def _sanitize(s) -> str:
    if s is None:
        return ""
    return _ILLEGAL.sub("_", str(s).strip())


def _text_sha1(text: str) -> str:
    """与 script_splitter.text_sha1 同实现（stale 判定依据，不做 normalize）。"""
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
    proc = subprocess.run(
        [sys.executable, str(CYPHER_EXEC), "--stdin", "--multi"],
        input="\n".join(statements), capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"写图失败（退出码 {proc.returncode}）:\n{proc.stderr}")


def make_voice_key(node_id) -> str:
    """voice 资源键 = hexid(行节点id)（键即运行时文件名主体，与 ambient 同构）。"""
    return to_hexid(str(node_id))


def make_ambient_track(node_id) -> str:
    """环境音资源键 = hexid(行节点id)（amb-/bed- 前缀已废——运行时播放行为由 op
    分发，voice/sfx 归属由图字段来源区分）。与 make_voice_key 同值：同一行只有
    一个键，voice_key / ambient_track 谁非空谁是本键。"""
    return to_hexid(str(node_id))


def make_master_path(chapter_id, scene_block_id, node_id) -> str:
    """母带 rel_path：15_声音/<ch_hexid>/<block_hexid>/<行_hexid>.wav（纯规则派生，
    目录段全 hexid）。图行属性 master_path 与盘上母带均按此规则。"""
    return (f"15_声音/{to_hexid(str(chapter_id))}/{to_hexid(str(scene_block_id))}"
            f"/{to_hexid(str(node_id))}.wav")


def split_voice_key(key: str):
    """【legacy】旧四段键 <char>-<stem>-<block>-<行id> → 四元组（迁移前存量键反解）。

    新键（hexid，不含 '-'）返回 None。仅服务 2026-10-31 迁移期的旧 wav 定位，
    过渡期后删除。"""
    if not key or "-" not in key:
        return None
    parts = (key or "").rsplit("-", 3)
    if len(parts) != 4 or not all(p.strip() for p in parts):
        return None
    return tuple(parts)


def normalize_clone_mode(v) -> str:
    """clone_mode 归一（bind 写图 / runner 合成分支两侧共用）：

    'xvec' = 仅说话人向量（丢 ref 韵律，文本语义主导演绎——迟疑/强情绪句用，
    变体 C 实验验证：平静 ref 的韵律迁移会压制文本语气信号）；
    None / 'icl' / 脏值一律 'icl'（ICL：ref codec + ref_text 韵律迁移，生产链缺省）。"""
    return "xvec" if str(v or "").strip().lower() == "xvec" else "icl"


def voice_master_path(root, key: str) -> Path:
    """【legacy】旧四段键 → 迁移前旧母带位置 15_声音/<stem>/<block>/<key>.wav。
    新键的母带定位读图行属性 master_path（或 make_master_path 规则派生）。"""
    t = split_voice_key(key)
    if t is None:
        raise ValueError(f"无法解析旧资源键：{key!r}")
    _, stem, block, _ = t
    return Path(root) / "15_声音" / stem / block / f"{key}.wav"


def chapter_stem_from_path(chapter_json_path) -> str:
    """chapter JSON 文件路径 → stem（去目录与 .json）。与 chapter_stem_from_meta 同为
    【legacy】——新章文件名 = hexid(Chapter.id)（阶段⑤起）。"""
    return Path(chapter_json_path).stem


def chapter_stem_from_meta(no, title) -> str:
    """【legacy】chapter_no + title → 旧 stem。新键体系不再派生 stem；保留仅供
    迁移期旧数据核对。"""
    return f"chapter{int(no):02d}_{_sanitize(title)}"


# ── 章级（读合并后章 JSON {meta, scenes}；say.voice 是发布投影 voice_key 的结果，
#    此处三模式服务全章重算/清单推导等搬运场景）──

def iter_say_lines(chapter: dict):
    """遍历 chapter JSON 的所有 say 行，yield (scene_id, line, line_voice_key_or_None)。"""
    for block in chapter.get("scenes", []):
        scene_id = block.get("id", "")
        for line in block.get("lines", []):
            if line.get("op") == "say":
                yield scene_id, line, line.get("voice")


def collect_voice_keys(chapter: dict) -> list:
    """列本章所有 say 的 voice 键（供 chapter_packs_updater --voices）。"""
    return [v for _, _, v in iter_say_lines(chapter) if v]


def build_manifest_voices(chapter: dict, ext: str = "wav") -> dict:
    """推导 manifest.voices 段：{key: f"assets/voices/{key}.{ext}"}。"""
    ext = ext.lstrip(".")
    return {k: f"assets/voices/{k}.{ext}" for k in collect_voice_keys(chapter)}


# ── 节级（图行：LineAudio 按 produces.order；拆分对齐见 script_splitter.py）──

def fetch_section(section_id: str) -> dict:
    """查节定稿态 + Chapter（id 与 no/title）+ 全部行（ORDER BY order）。

    返回 {section_id, sc_status, script_path, ch_id, chapter_no, chapter_title, lines:[...]}。
    行含 op/who/text/status 等节点属性 + ord + scene 行的 scene_block_id。
    """
    head = _run_cypher(
        "MATCH (ch:Chapter)-[:has_section]->(sec:Section {id:'" + section_id + "'}) "
        "RETURN sec.id AS section_id, sec.status AS sc_status, sec.script_path AS p, "
        "ch.id AS ch_id, ch.chapter_no AS no, ch.title AS title LIMIT 1"
    )
    if not head:
        raise ValueError(f"Section {section_id} 不存在")
    lines = _run_cypher(
        "MATCH (sec:Section {id:'" + section_id + "'})-[p:produces]->(l:LineAudio) "
        "RETURN l.id AS id, l.op AS op, l.who AS who, l.text AS text, "
        "l.status AS status, l.attempts AS attempts, l.voice_key AS voice_key, "
        "l.text_sha1 AS text_sha1, l.scene_block_id AS scene_block_id, "
        "l.master_path AS master_path, "
        "l.clone_mode AS clone_mode, p.order AS ord "
        "ORDER BY p.order"
    )
    out = dict(head[0])
    out["lines"] = lines
    return out


def collect_graph_tasks(lines: list, chapter_id: str, node_ids=()) -> dict:
    """图行 → 按角色分组的待配任务：{char: [{key, text, scene_id, node_id, master_path, clone_mode}]}。

    chapter_id：Chapter 节点 id（裸 Base62）——master_path 规则派生用。
    挑行条件 = say 行 status∈{0, -1}（0=待配/被驳回，stale 句在拆分对齐时已被置 0；
    -1=级联作废/存量迁移重做——与 0 同为需生成，禁止把 -1 滤掉）。
    node_ids：行节点 id 白名单（重生成 deeplink 定位被驳回句；缺省不过滤）。
    emotion / tts_text **不预填**——由 section-voice-publisher 的 LLM 逐句判别/变体后
    写入 tasks JSON，publish 缺省回落原文。clone_mode **透传图上现值**（上轮 bind
    终值或人工在 dashboard 改的值）作判别初值；null=从未判过（缺省 icl）。
    """
    wanted = {s.strip() for s in node_ids if s.strip()}
    tasks = {}
    for l in lines:
        if l.get("op") != "say" or l.get("status") not in (0, -1):
            continue
        if wanted and l.get("id") not in wanted:
            continue
        who = l.get("who") or ""
        scene_id = l.get("scene_block_id") or ""  # 行上直读块归属（scene 行已去图化）
        tasks.setdefault(who, []).append({
            "key": make_voice_key(l.get("id", "")),
            "text": l.get("text") or "",
            "scene_id": scene_id,
            "node_id": l.get("id", ""),
            "master_path": make_master_path(chapter_id, scene_id, l.get("id", "")),
            "clone_mode": l.get("clone_mode"),
        })
    return tasks


def bind_graph(tasks: dict, keys=None) -> dict:
    """把（重）生成结果写回图行节点（经 cypher_exec --stdin --multi 单事务）。

    tasks：{char: [{key, text, node_id, master_path?, emotion?, tts_text?, clone_mode?}]}。
    keys：可选键过滤（只 bind 生成成功的句）。写：voice_key/emotion/tts_text/
    clone_mode=归一化终值（=本句实际合成模式，下轮重配的判别初值）/
    attempts=旧+1/text_sha1=当前台词 sha1/status=10（配完待审）；
    master_path 非 null 时一并落图（母带唯一权威）。
    返回 {bound, skipped} 统计。
    """
    key_set = {k.strip() for k in keys if k.strip()} if keys else None
    stmts = []
    bound = skipped = 0
    for char, items in tasks.items():
        for it in items:
            if key_set is not None and it.get("key") not in key_set:
                skipped += 1
                continue
            node_id = it.get("node_id") or ""
            if not node_id:
                skipped += 1
                continue
            stmts.append(
                f"MATCH (l:LineAudio {{id:{_q(node_id)}}}) "
                f"SET l.voice_key={_q(it.get('key'))}, "
                f"l.master_path={_q(it.get('master_path'))}, "
                f"l.emotion={_q(it.get('emotion'))}, "
                f"l.tts_text={_q(it.get('tts_text'))}, "
                f"l.clone_mode={_q(normalize_clone_mode(it.get('clone_mode')))}, "
                f"l.attempts=coalesce(l.attempts,0)+1, "
                f"l.text_sha1={_q(_text_sha1(it.get('text') or ''))}, "
                f"l.status=10;"
            )
            bound += 1
    if stmts:
        _run_cypher_multi(stmts)
    return {"bound": bound, "skipped": skipped}


def collect_approved_audio_keys(rows: list) -> list:
    """publish 图查询行（{vk, at, mp}）→ 已批音频条目清单（去重保序）。

    返回 [{"key", "kind": "voice"|"sfx", "master"}]：voice_key 非空 → voice（运行时
    voices），ambient_track 非空 → sfx（运行时 sfx；bed 音床也走 sfx 段）——**按字段
    来源分发**（旧 amb-/bed- 前缀判定已废，键均为 hexid）。master 取图行 master_path；
    缺失时为 None（调用方按规则派生兜底）。
    以字段存在为准、**不看 op**——转场行（op=transition，存量 ambient 兼容）与 narrate 内嵌声景行
    （op=narrate + ambient_track）同样发布（历史版本只查 op='ambient' 会漏后者）。
    Cypher 的缺省列是 null，此处过滤。
    """
    items, seen = [], set()
    for r in rows:
        for k, kind in ((r.get("vk"), "voice"), (r.get("at"), "sfx")):
            if k and k not in seen:
                seen.add(k)
                items.append({"key": k, "kind": kind, "master": r.get("mp")})
    return items


def publish_runtime(root, items: list, runtime_voices, runtime_sfx=None, ext: str = "wav") -> dict:
    """已批音频条目 → 母带拷运行时（**发布期动作**，chapter-publisher 调用）：

    - kind=sfx → <runtime_sfx>/<key>.<ext>（默认 99_game/assets/sfx；与
      manifest_builder.collect_sfx 的 ambient_track 口径一致——bed 音床也走 sfx 段）
    - kind=voice → <runtime_voices>/<key>.<ext>（默认 99_game/assets/voices）
    源 = 图行 master_path（缺失时按规则派生兜底）；母带缺失计 missing 不中断
    （status=11 却无母带=文件被误删，发布汇报需警告）。返回
    {copied, skipped, missing, copied_sfx, skipped_sfx, missing_sfx}。
    （生成期 sync 已废除——99_game/assets 只收已批音频，dashboard 审批试听读母带。）
    """
    import shutil
    voices = Path(runtime_voices)
    voices.mkdir(parents=True, exist_ok=True)
    sfx = Path(runtime_sfx) if runtime_sfx else None
    if sfx is not None:
        sfx.mkdir(parents=True, exist_ok=True)
    counts = {"copied": 0, "skipped": 0, "missing": 0,
              "copied_sfx": 0, "skipped_sfx": 0, "missing_sfx": 0}
    for it in items:
        is_sfx = it.get("kind") == "sfx"
        if is_sfx and sfx is None:
            continue
        key = it["key"]
        master_rel = it.get("master")
        master = Path(root) / master_rel if master_rel else None
        if master is None or not master.exists():
            # 图上无 master_path 或文件不在：查图派生兜底再试一次（章+块 → make_master_path）
            from snowflake_base62 import from_hexid
            try:
                lid = from_hexid(key)
            except ValueError:
                continue
            row = _run_cypher(
                "MATCH (l:LineAudio {id:'" + lid + "'})"
                "<-[:produces]-(:Section)<-[:has_section]-(ch:Chapter) "
                "RETURN l.master_path AS mp, l.scene_block_id AS block, ch.id AS ch LIMIT 1")
            if row:
                r0 = row[0]
                mp = r0["mp"] or (make_master_path(r0["ch"], r0["block"], lid)
                                  if r0.get("block") and r0.get("ch") else None)
                if mp:
                    master = Path(root) / mp
        dst = (sfx if is_sfx else voices) / f"{key}.{ext}"
        ck, sk, mk = (("copied_sfx", "skipped_sfx", "missing_sfx")
                      if is_sfx else ("copied", "skipped", "missing"))
        if master is None or not master.exists():
            counts[mk] += 1
            continue
        if dst.exists() and dst.stat().st_mtime == master.stat().st_mtime \
                and dst.stat().st_size == master.stat().st_size:
            counts[sk] += 1
            continue
        shutil.copy2(master, dst)
        counts[ck] += 1
    return counts


def _load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _save_json(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_tasks(tasks, out):
    data = json.dumps(tasks, ensure_ascii=False, indent=2)
    if not out or out == "-":
        print(data)
    else:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(data, encoding="utf-8")
    return sum(len(v) for v in tasks.values())


# ── CLI（3 章级 + 2 节级图版 + 1 发布）──

def _cmd_manifest(args):
    path = Path(args.chapter_json)
    chapter = _load_json(path)
    voices = build_manifest_voices(chapter, ext=args.ext)
    manifest_path = Path(args.manifest) if args.manifest else path.parent.parent / "manifest.json"
    manifest = _load_json(manifest_path) if manifest_path.exists() else {}
    manifest.setdefault("voices", {}).update(voices)
    _save_json(manifest_path, manifest)
    print(f"[manifest] wrote {len(voices)} voices -> {manifest_path} (ext={args.ext})")


def _cmd_list(args):
    chapter = _load_json(args.chapter_json)
    keys = collect_voice_keys(chapter)
    print(",".join(keys))  # CSV，供 chapter_packs_updater --voices


def _cmd_tasks_from_graph(args):
    """图行（say 且 status∈{0,-1}）→ 按角色分组任务 JSON（节级配音；emotion/tts_text 留给 skill，clone_mode 透传现值）。"""
    info = fetch_section(args.section)
    if info["sc_status"] != 11:
        raise ValueError(f"Section.status={info['sc_status']}（须 11 定稿已确认；先拆分对齐见 script_splitter）")
    chapter_hex = to_hexid(info["ch_id"])
    node_ids = tuple(s.strip() for s in args.nodes.split(",")) if args.nodes else ()
    tasks = collect_graph_tasks(info["lines"], info["ch_id"], node_ids=node_ids)
    n_lines = _write_tasks(tasks, args.out)
    print(f"[tasks-from-graph] chapter={info['ch_id']} ({chapter_hex}) {n_lines} lines / {len(tasks)} chars"
          + (f" nodes={args.nodes}" if args.nodes else "") + f" -> {args.out or 'stdout'}")


def _cmd_bind_graph(args):
    """把生成结果（含判别 emotion + tts_text 变体）写回图行节点（status=10 待审）。"""
    tasks = _load_json(args.tasks)
    keys = [s.strip() for s in args.keys.split(",")] if args.keys else None
    stats = bind_graph(tasks, keys)
    print(f"[bind-graph] bound={stats['bound']} skipped={stats['skipped']} -> LineAudio")


def _cmd_publish(args):
    """按章查已批（status=11）音频行 → 母带拷运行时（发布期；dashboard 试听读母带不经此步）。"""
    rows = _run_cypher(
        "MATCH (ch:Chapter {id:" + _q(args.chapter) + "})-[:has_section]->(:Section)"
        "-[:produces]->(l:LineAudio) "
        "WHERE l.status=11 AND (l.voice_key IS NOT NULL OR l.ambient_track IS NOT NULL) "
        "RETURN l.voice_key AS vk, l.ambient_track AS at, l.master_path AS mp"
    )
    items = collect_approved_audio_keys(rows)
    stats = publish_runtime(_REPO_ROOT, items, args.runtime,
                            runtime_sfx=args.runtime_sfx, ext=args.ext)
    line = (f"[publish] chapter={args.chapter} keys={len(items)}"
            f" voices copied={stats['copied']} skipped={stats['skipped']}"
            f" | sfx copied={stats['copied_sfx']} skipped={stats['skipped_sfx']}")
    miss = stats["missing"] + stats["missing_sfx"]
    if miss:
        line += f" | ⚠️ 母带缺失 {miss}（status=11 但 15_声音 无文件，需检查）"
    print(line)


def main():
    ap = argparse.ArgumentParser(description="voice 资源键生成与图行级 audio 绑定（三处对齐）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_man = sub.add_parser("manifest", help="推导 manifest.voices 段并合并写入 manifest.json（读章 JSON）")
    p_man.add_argument("chapter_json")
    p_man.add_argument("--ext", default="wav", choices=["wav", "ogg"])
    p_man.add_argument("--manifest", help="manifest.json 路径（默认 chapter 同级 ../manifest.json）")
    p_man.set_defaults(func=_cmd_manifest)

    p_list = sub.add_parser("list", help="列本章 voice 键（CSV，供 chapter_packs_updater --voices）")
    p_list.add_argument("chapter_json")
    p_list.set_defaults(func=_cmd_list)

    p_tfg = sub.add_parser("tasks-from-graph", help="图行（say 且 status∈{0,-1}）→ 按角色分组任务 JSON（节级配音，供 voice_clone_runner publish；clone_mode 透传现值作判别初值）")
    p_tfg.add_argument("--section", required=True, help="Section 节点 ID（snowflake）")
    p_tfg.add_argument("--nodes", default=None, help="行节点 id 白名单（逗号分隔，重生成被驳回句用；缺省不过滤）")
    p_tfg.add_argument("-o", "--out", help="输出 JSON 路径（缺省打印到 stdout）")
    p_tfg.set_defaults(func=_cmd_tasks_from_graph)

    p_bg = sub.add_parser("bind-graph", help="把生成结果（含 emotion + tts_text 变体 + clone_mode 终值）写回图行节点（status=10 待审）")
    p_bg.add_argument("--tasks", required=True, help="tasks JSON 路径（tasks-from-graph 产出 + skill 已填 emotion/tts_text/clone_mode）")
    p_bg.add_argument("--keys", default=None, help="只 bind 指定 key（逗号分隔，publish 失败句排除用；缺省=全部）")
    p_bg.set_defaults(func=_cmd_bind_graph)

    p_pub = sub.add_parser("publish", help="按章查已批（status=11）音频行 → 母带拷运行时 voices/sfx（发布期，chapter-publisher 调用；以 voice_key/ambient_track 字段存在为准，含 narrate 内嵌声景）")
    p_pub.add_argument("--chapter", required=True, help="Chapter 节点 ID（snowflake）")
    p_pub.add_argument("--runtime", default="99_game/assets/voices", help="配音运行时目录（扁平 <key>.wav）")
    p_pub.add_argument("--runtime-sfx", default="99_game/assets/sfx", dest="runtime_sfx",
                       help="环境音运行时目录（扁平 <track>.wav）")
    p_pub.add_argument("--ext", default="wav", choices=["wav", "ogg"])
    p_pub.set_defaults(func=_cmd_publish)

    args = ap.parse_args()
    try:
        args.func(args)
    except (ValueError, RuntimeError) as e:
        sys.stderr.write(f"失败: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
