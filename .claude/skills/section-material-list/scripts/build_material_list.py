#!/usr/bin/env python3
"""build_material_list — 节取材清单生成器（section-material-list skill 的执行脚本）。

用法：
    python build_material_list.py <sec_id>

做三件事：
  1. 提取：七条只读 Cypher（节信息/成员事件/sub/人物/Lore/控制折射/Hook），
     结果缓存到 仓库根/.tmp/novelist/<sec_id>_listcache/*.json 供复查。
  2. 清洗：Lore freshness（blocked 剔除、side 标红）、Hook 已消费剔除、
     条件事件标红、机位悬空 sub 标红。
  3. 落盘：25_剧本/<章或自由节>/sec<MM>/取材清单.md（头部机器可读块 + 五张人读表）。

零图写入（全部只读查询）；退出码 2 = 节不存在；其余异常退出码 1。
连接：密码优先级 NEO4J_PASSWORD 环境变量 > 向上搜索 settings.json（与 cypher_exec 同源），
服务器 Memgraph 空密码时 auth=None。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]  # .claude/skills/<skill>/scripts → 仓库根
CYPHER_EXEC = REPO_ROOT / ".claude" / "scripts" / "cypher_exec.py"
FINGERPRINT = REPO_ROOT / ".claude" / "skills" / "chapter-novelist" / "scripts" / "fingerprint.py"
SCRIPT_ROOT = REPO_ROOT / "25_剧本"
CACHE_DIR = REPO_ROOT / ".tmp" / "novelist"

QUERIES = {
    "sec": "MATCH (sec:Section {id:'{sid}'}) OPTIONAL MATCH (ch:Chapter)-[:has_section]->(sec) "
           "RETURN sec.id AS id, sec.title AS title, sec.section_no AS no, sec.status AS status, "
           "ch.chapter_no AS ch_no, ch.title AS ch_title LIMIT 1",
    "events": "MATCH (sec:Section {id:'{sid}'})-[inc:includes]->(e:Event) "
              "RETURN e.id AS id, e.title AS title, e.time AS time, e.type AS type, "
              "e.condition AS condition, inc.order AS ord ORDER BY e.time",
    "subs": "MATCH (sec:Section {id:'{sid}'})-[:includes]->(e:Event)-[:refines]->(sub:SubEvent) "
            "OPTIONAL MATCH (sub)-[:anchored_at]->(sc:Scene) "
            "RETURN sub.id AS sub_id, sub.title AS title, sub.time AS time, "
            "e.id AS evt_id, e.title AS evt_title, sc.name AS scene ORDER BY sub.time",
    "chars": "MATCH (sec:Section {id:'{sid}'})-[:includes]->(e:Event)<-[:involved]-(c:Character) "
             "RETURN DISTINCT c.id AS id, c.name AS name, count(e) AS n_evt, collect(e.title) AS evts "
             "ORDER BY n_evt DESC",
    "lores": "MATCH (sec:Section {id:'{sid}'})-[:includes]->(e:Event)<-[:involved]-(c:Character)-[:has_info]->(l:Lore) "
             "RETURN DISTINCT l.id AS id, l.title AS title, l.content AS content, "
             "l.knowledge_level AS kl, c.id AS host_id, c.name AS host ORDER BY host, kl",
    "ctrl_lores": "MATCH (sec:Section {id:'{sid}'})-[:includes]->(e:Event)<-[:involved]-(c:Character) "
                  "MATCH (src:Character)-[:relation {type:'控制'}]->(c) "
                  "MATCH (src)-[:has_info]->(l:Lore) "
                  "RETURN DISTINCT l.id AS id, l.title AS title, l.content AS content, "
                  "l.knowledge_level AS kl, src.id AS host_id, src.name AS host, c.name AS via "
                  "ORDER BY l.id",
    "hooks": "MATCH (sec:Section {id:'{sid}'})-[:includes]->(e:Event)-[:refines]->(sub:SubEvent)-[:reveals]->(h:Hook) "
             "RETURN DISTINCT h.id AS id, h.title AS title, h.knowledge_level AS kl, "
             "sub.title AS via_sub, e.title AS via_evt ORDER BY h.id",
}


def run_cypher(query: str) -> list[dict]:
    # 子进程统一 uv 带依赖跑（系统 python 无 neo4j 模块）；与仓库 skill 调用惯例一致
    cmd = ["uv", "run", "--with", "neo4j", str(CYPHER_EXEC), "-c", query, "--json"]
    env = os.environ.copy()
    pwd = env.get("NEO4J_PASSWORD")
    if not pwd:  # settings.json 搜索兜底（与 cypher_exec 同源约定）
        for d in [REPO_ROOT, *REPO_ROOT.parents]:
            f = d / "settings.json"
            if f.exists():
                try:
                    pwd = json.loads(f.read_text(encoding="utf-8")).get("neo4j_password")
                except Exception:
                    pwd = None
                if pwd:
                    env["NEO4J_PASSWORD"] = pwd
                break
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=REPO_ROOT)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or r.stdout)
        raise RuntimeError(f"cypher_exec 失败: {query[:80]}…")
    out = r.stdout.strip()
    # cypher_exec --json 输出可带「已连接/连接已关闭」行，取最后一个 JSON 数组
    start = out.find("[")
    if start < 0:
        return []
    return json.loads(out[start:])


def fingerprint_consumed(ids: list[str]) -> dict[str, str | None]:
    """Hook 已消费判定：fingerprint.py consumed --ids，返回 {id: 上次消费节 or None}。"""
    if not ids:
        return {}
    cmd = ["uv", "run", "--with", "neo4j", str(FINGERPRINT), "consumed", "--root", str(SCRIPT_ROOT),
           "--ids", ",".join(ids)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    consumed: dict[str, str | None] = {}
    try:
        # consumed 真实形态：{id: [消费路径列表]}——从未消费的 id 不在映射里
        data = json.loads(r.stdout)
        for i in ids:
            paths = data.get(i)
            consumed[i] = paths[-1] if paths else None
    except Exception:
        # 解析失败降级：全部标「无法判定（consumed 输出形态未识别）」不清除入清单资格
        for i in ids:
            consumed[i] = "?"
    return consumed


def fingerprint_freshness(materials: list[dict], at: str) -> dict[str, str]:
    """Lore freshness 档位：返回 {lore_id: explicit|side|blocked|never|?}。"""
    if not materials:
        return {}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    min_path = CACHE_DIR / f"_{os.getpid()}_fresh_in.json"
    min_path.write_text(json.dumps(materials, ensure_ascii=False), encoding="utf-8")
    cmd = ["uv", "run", "--with", "neo4j", str(FINGERPRINT), "freshness", "--in", str(min_path),
           "--at", at, "--root", str(SCRIPT_ROOT)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    tiers: dict[str, str] = {}
    try:
        # freshness 真实形态：{id: {allow: explicit|side|blocked, …}}——dict 按 id 键
        data = json.loads(r.stdout)
        for rid, info in data.items():
            tiers[rid] = str(info.get("allow") or "?")
    except Exception:
        for m in materials:
            tiers[m["id"]] = "?"
    finally:
        min_path.unlink(missing_ok=True)
    return tiers


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: build_material_list.py <sec_id>", file=sys.stderr)
        return 1
    sid = sys.argv[1].strip()

    # ── 提取 ──
    data: dict[str, list[dict]] = {}
    for key, q in QUERIES.items():
        data[key] = run_cypher(q.replace("{sid}", sid))
    if not data["sec"]:
        print(f"Section {sid} 不存在", file=sys.stderr)
        return 2

    sec = data["sec"][0]
    cache = CACHE_DIR / f"{sid}_listcache"
    cache.mkdir(parents=True, exist_ok=True)
    for key, rows in data.items():
        (cache / f"{key}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 清洗 ──
    ch_no, sec_no = sec.get("ch_no"), sec.get("no")
    at = f"ch{ch_no:02d}/sec{sec_no:02d}" if ch_no is not None else f"自由节/sec{sec_no:02d}"
    fresh_tiers = fingerprint_freshness(
        [{"kind": "lore", **l} for l in data["lores"] + data["ctrl_lores"]], at)
    consumed = fingerprint_consumed([h["id"] for h in data["hooks"]])

    events, subs, flagged = data["events"], data["subs"], []
    for ev in events:
        if ev.get("condition"):
            flagged.append(("event", ev["id"], ev["title"],
                            f"条件事件：{ev['condition']}（本节按全支线并存呈现，是否成立交下游裁量）"))
    for s in subs:
        if not s.get("scene"):
            flagged.append(("sub", s["sub_id"], s["title"], "机位悬空：缺 anchored_at，待 event-stager 补"))
    lore_rows = []
    for l in data["lores"] + data["ctrl_lores"]:
        if l["id"] in {r["id"] for r in lore_rows}:
            continue
        tier = fresh_tiers.get(l["id"], "?")
        if tier == "blocked":
            continue  # 剔除：本节禁释放
        lore_rows.append({**l, "source": "直挂" if l in data["lores"] else "控制折射",
                          "tier": tier})
        if tier == "side":
            flagged.append(("lore", l["id"], l["title"], "freshness side 档：只可侧面折射"))
    hook_rows = []
    for h in data["hooks"]:
        c = consumed.get(h["id"])
        if c and c != "?":
            continue  # 已消费剔除
        hook_rows.append(h)
        if c == "?":
            flagged.append(("hook", h["id"], h["title"], "消费状态无法判定，保留待人工核"))

    # ── 落盘 ──
    mm = f"{sec_no:02d}"
    out_dir = (SCRIPT_ROOT / f"ch{ch_no:02d}" / f"sec{mm}") if ch_no is not None \
        else (SCRIPT_ROOT / "自由节" / f"sec{mm}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "取材清单.md"

    def tbl(header: list[str], rows: list[list[str]]) -> str:
        h = "| " + " | ".join(header) + " |"
        sep = "|" + "|".join(["---"] * len(header)) + "|"
        body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows) or "｜（空）"
        return "\n".join([h, sep, body])

    L = []
    ids = {
        "chars": ",".join(c["id"] for c in data["chars"]),
        "events": ",".join(e["id"] for e in events),
        "subs": ",".join(s["sub_id"] for s in subs),
        "lores": ",".join(l["id"] for l in lore_rows),
        "hooks": ",".join(h["id"] for h in hook_rows),
    }
    L.append(f"<!-- material-list v1\n{sid}\n"
             f"chars: {ids['chars']}\nevents: {ids['events']}\n"
             f"subs: {ids['subs']}\nlores: {ids['lores']}\nhooks: {ids['hooks']}\n-->")
    where = f"ch{ch_no:02d} {sec['ch_title']}" if ch_no is not None else "自由节"
    L.append(f"# 取材清单 · sec{mm} {sec['title']}（{where}）\n")
    L.append(f"生成：{datetime.now():%Y-%m-%d %H:%M} · 人物 {len(data['chars'])} · "
             f"事件 {len(events)} · sub {len(subs)} · Lore 入选 {len(lore_rows)}/"
             f"{len(data['lores']) + len(data['ctrl_lores'])} · Hook 未消费 {len(hook_rows)}/{len(data['hooks'])}\n")

    L.append("## 人物（仅 involved）")
    L.append(tbl(["id", "名字", "参与事件数", "参与事件"],
                 [[c["id"], c["name"], c["n_evt"], "、".join(c["evts"])] for c in data["chars"]]))
    L.append("\n## 事件（时间正序）")
    L.append(tbl(["id", "标题", "时间", "type", "condition", "判定"],
                 [[e["id"], e["title"], e["time"], e.get("type") or "",
                   e.get("condition") or "", "标红" if e.get("condition") else "入清单"]
                  for e in events]))
    L.append("\n## SubEvent（时间正序，按父事件分组）")
    sub_rows = [[s["sub_id"], s["title"], s["time"], s["evt_title"],
                 s.get("scene") or "⚠ 悬空", "标红" if not s.get("scene") else "入清单"]
                for s in subs]
    L.append(tbl(["id", "标题", "时间", "父事件", "机位", "判定"], sub_rows))
    L.append("\n## Lore（按宿主分组）")
    lore_tbl = [[l["id"], l["title"], l.get("kl", ""),
                 f"{l['host']}" + (f"（经 {l['via']} 折射）" if l.get("via") else ""),
                 l["source"], l["tier"],
                 "标红" if l["tier"] == "side" else "入清单"] for l in lore_rows]
    L.append(tbl(["id", "标题", "kl", "宿主", "来源", "freshness", "判定"], lore_tbl))
    L.append("\n## Hook（未消费）")
    if hook_rows:
        L.append(tbl(["id", "标题", "kl", "揭示 sub", "判定"],
                     [[h["id"], h["title"], h.get("kl", ""), h["via_sub"], "入清单"]
                      for h in hook_rows]))
    else:
        L.append(tbl(["id", "标题", "kl", "揭示 sub", "判定"], []) + "\n\n（本节无未消费 Hook）")

    if flagged:
        L.append("\n## ⚠ 标红项")
        for kind, fid, title, why in flagged:
            L.append(f"- **[{kind}]** {fid} 「{title}」——{why}")
    L.append("")

    out_path.write_text("\n".join(L), encoding="utf-8")

    # ── 读回核对 ──
    head = out_path.read_text(encoding="utf-8").split("-->")[0]
    assert sid in head, "头部块缺 section_id"
    for key, field in [("chars", "chars"), ("events", "events"), ("subs", "subs"),
                       ("lores", "lores"), ("hooks", "hooks")]:
        m = [ln for ln in head.splitlines() if ln.startswith(field + ":")]
        got = [x for x in (m[0].split(":", 1)[1].strip().split(",") if m else []) if x]
        want = ids[key].split(",") if ids[key] else []
        assert got == want, f"头部块 {field} 与统计不符"
    print(f"OK 取材清单: {out_path.relative_to(REPO_ROOT)}")
    print(f"  人物 {len(data['chars'])} · 事件 {len(events)} · sub {len(subs)} · "
          f"Lore {len(lore_rows)}/{len(data['lores']) + len(data['ctrl_lores'])} · "
          f"Hook {len(hook_rows)}/{len(data['hooks'])} · 标红 {len(flagged)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
