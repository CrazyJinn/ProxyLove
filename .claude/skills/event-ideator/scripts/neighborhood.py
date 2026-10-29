#!/usr/bin/env python3
"""ideator 锚点关系查询（只读）——只查 Location/Character/Event 三类实体之间的关系。

用法：
    python neighborhood.py --char <char_id> --base <event_id>   # 双锚：连通性检查（主模式）
    python neighborhood.py --char <char_id>                     # 单锚 char：一跳清单
    python neighborhood.py --base <event_id>                    # 单锚 event：一跳清单

双锚（主模式）查两锚在叙事基础域的连通性，不做全量邻域扫描：
  直接关系   两锚间的直接边（含 properties，如 involved.role）
  间接路径   ≤4 跳路径（边限 involved/occurs_at/at/relation/leads_to，
             节点限 Character/Event/Location——Info/Choice/演出域实体不参与），
             按跳数排序取前 10
  不连通     两锚无路径——启发空隙（新事件即桥），如实输出

单锚退化为一跳清单（不滚雪球）：
  char 锚    近期 involved 事件 10 条（时间倒序）+ at 常驻地 + relation 关系人
  event 锚   involved 参与人（含 role）+ occurs_at 地点 + leads_to 因果邻居

锚点查无 → 报错退出（先做名称→id 解析），不静默降级不猜。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]          # .../skills/event-ideator
ROOT = SKILL_DIR.parents[2]                               # 项目根
CYPHER_EXEC = ROOT / ".claude" / "scripts" / "cypher_exec.py"

# 三实体之间流转的叙事基础边（Schema/叙事基础.md 出边表归纳；Info/Choice 中转由节点过滤排除）
EDGE_TYPES = "involved|occurs_at|at|relation|leads_to"
MAX_HOPS = 4


def run_cypher(cypher: str) -> list:
    proc = subprocess.run(
        [sys.executable, str(CYPHER_EXEC), "-c", cypher, "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    out = proc.stdout
    start, end = out.find("["), out.rfind("]")
    if start == -1:
        raise SystemExit(f"cypher_exec 未返回 JSON（退出码 {proc.returncode}）:\n"
                         f"{proc.stderr or out}")
    return json.loads(out[start:end + 1])


def q(v: str) -> str:
    return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"


def anchor_info(anchor_id: str) -> dict:
    rows = run_cypher(
        f"MATCH (n {{id:{q(anchor_id)}}}) "
        f"RETURN labels(n)[0] AS kind, n.id AS id, coalesce(n.name, n.title) AS name LIMIT 1")
    if not rows:
        raise SystemExit(f"锚点查无: {anchor_id}（零返回——先做名称→id 解析，或确认实体存在）")
    return rows[0]


def pair(char_id: str, base_id: str) -> dict:
    """双锚连通性：直接关系 + 间接路径（≤4 跳，三实体域）。"""
    direct = run_cypher(
        f"MATCH (a {{id:{q(char_id)}}})-[r]-(b {{id:{q(base_id)}}}) "
        f"RETURN type(r) AS rel, properties(r) AS props")
    paths = run_cypher(
        f"MATCH (a {{id:{q(char_id)}}}), (b {{id:{q(base_id)}}}) "
        f"MATCH p = (a)-[:{EDGE_TYPES}*1..{MAX_HOPS}]-(b) "
        f"WHERE all(n IN nodes(p) WHERE n:Character OR n:Event OR n:Location) "
        f"RETURN [n IN nodes(p) | coalesce(n.name, n.title, n.id)] AS nodes, "
        f"[n IN nodes(p) | n.id] AS node_ids, "
        f"[r IN relationships(p) | type(r) + '·' + startNode(r).id] AS rels, "
        f"length(p) AS hops "
        f"ORDER BY hops LIMIT 10")
    return {"direct": direct, "paths": paths}


def single_char(char_id: str) -> dict:
    events = run_cypher(
        f"MATCH (c:Character {{id:{q(char_id)}}})-[:involved]->(e:Event) "
        f"RETURN e.title AS title, e.time AS time, e.type AS type "
        f"ORDER BY e.time DESC LIMIT 10")
    at = run_cypher(
        f"MATCH (c:Character {{id:{q(char_id)}}})-[r:at]->(l:Location) "
        f"RETURN l.name AS loc, properties(r) AS props")
    rels = run_cypher(
        f"MATCH (c:Character {{id:{q(char_id)}}})-[r:relation]->(o:Character) "
        f"RETURN o.name AS other, r.type AS rel_type")
    return {"events": events, "at": at, "relations": rels}


def single_event(event_id: str) -> dict:
    chars = run_cypher(
        f"MATCH (c:Character)-[iv:involved]->(e:Event {{id:{q(event_id)}}}) "
        f"RETURN c.name AS name, iv.role AS role")
    locs = run_cypher(
        f"MATCH (e:Event {{id:{q(event_id)}}})-[:occurs_at]->(l:Location) "
        f"RETURN l.name AS name")
    causes = run_cypher(
        f"MATCH (e:Event {{id:{q(event_id)}}})-[r:leads_to]-(o:Event) "
        f"RETURN o.title AS other, "
        f"CASE WHEN startNode(r) = e THEN '→出(果)' ELSE '←入(因)' END AS dir")
    return {"chars": chars, "locations": locs, "leads_to": causes}


def fmt_path(nodes: list, node_ids: list, rels: list) -> str:
    """按每条边的真实起点画方向（无向匹配不带方向，靠 startNode 判定）。"""
    parts = [nodes[0]]
    for i, r in enumerate(rels):
        rtype, _, start = r.partition("·")
        if start == node_ids[i]:
            parts.append(f" -{rtype}-> ")
        else:
            parts.append(f" <-{rtype}- ")
        parts.append(nodes[i + 1])
    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="ideator 锚点关系查询（只读）")
    ap.add_argument("--char", default="", help="Character id")
    ap.add_argument("--base", default="", help="base Event id")
    ap.add_argument("--json", action="store_true", help="纯 JSON 输出（默认人读）")
    args = ap.parse_args()
    if not args.char and not args.base:
        ap.error("至少给一个锚：--char 和/或 --base")

    if args.char and args.base:
        a, b = anchor_info(args.char), anchor_info(args.base)
        result = {"mode": "pair", "char": a, "base": b, **pair(args.char, args.base)}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=1)); return 0
        print(f"锚对: {a['name']}({a['kind']}) ↔ {b['name']}({b['kind']})")
        if result["direct"]:
            for d in result["direct"]:
                props = " ".join(f"{k}={v}" for k, v in d["props"].items()) if d["props"] else ""
                print(f"直接关系: {d['rel']} {props}".rstrip())
        else:
            print("直接关系: 无")
        if result["paths"]:
            print(f"间接路径（≤{MAX_HOPS} 跳，仅 Character/Event/Location，按跳数）：")
            seen = set()
            for p in result["paths"]:
                key = (tuple(p["nodes"]), tuple(p["rels"]))
                if key in seen:
                    continue
                seen.add(key)
                print(f"  [{p['hops']}跳] {fmt_path(p['nodes'], p['node_ids'], p['rels'])}")
        else:
            print(f"间接路径: 无——两锚在叙事基础域（≤{MAX_HOPS} 跳）不连通，启发空隙（新事件即桥）")
        return 0

    if args.char:
        a = anchor_info(args.char)
        result = {"mode": "single-char", "anchor": a, **single_char(args.char)}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=1)); return 0
        print(f"锚点: {a['name']}(Character) 一跳清单")
        print(f"近期事件（{len(result['events'])} 条，时间倒序）：")
        for e in result["events"]:
            print(f"  {e['time']}  [{e['type']}] {e['title']}")
        if result["at"]:
            print(f"常驻地: " + "、".join(x["loc"] for x in result["at"]))
        if result["relations"]:
            print(f"关系人: " + "、".join(f"{x['other']}({x['rel_type']})" for x in result["relations"]))
        return 0

    a = anchor_info(args.base)
    result = {"mode": "single-event", "anchor": a, **single_event(args.base)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1)); return 0
    print(f"锚点: {a['name']}(Event) 一跳清单")
    who = "、".join(f"{x['name']}·{x['role'] or '?'}" for x in result["chars"]) or "<缺 involved>"
    print(f"参与人: {who}")
    print(f"地点: " + ("、".join(x["name"] for x in result["locations"]) or "<缺 occurs_at>"))
    if result["leads_to"]:
        print(f"因果邻居: " + "、".join(f"{x['dir']} {x['other']}" for x in result["leads_to"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
