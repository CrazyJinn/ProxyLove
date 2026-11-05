#!/usr/bin/env python3
"""stager 前置核验：范围解析 + 入口核验 + 演出资源现状（只读）。

用法：
    python preflight.py --ids <id1,id2> [--titles t1,t2] [--window 起,止] [--json]
    （三 selector 可组合；--window 止为开区间次日，如 2024-06-01,2024-06-16）

输出：
  verdict   PASS / FAIL
  scope     命中事件 {id, title, time, locations[], chars[]}（按 time 排序）
  failures  契约违规清单（每事件缺 occurs_at / 缺 involved，含修复指引）
  batch     单轮上限 3：命中 >3 时取时间最早 3 个，余者列入 next_round
  assets    演出资源现状（§2 探索步的 facts）：
    chars    每 involved Character 的立绘链：Character→AppearanceStyle→DesignSheet→IllusDesign←outfit_for← CostumeStyle
    costumes 每 involved Character 的着装（has_costume 直查，含 stager 占位 status=0——防同缺口重复建占位）
    scenes   每 occurs_at Location 的空间链：Spot →realizes→ Scene

聚合查询一律段段 WITH 物化（双后端 Memgraph/Neo4j 兼容，见 cypher_exec.py 硬约束 11）。

FAIL 语义：范围内任一事件缺 occurs_at Location 或缺 involved Character →
stager 报错停止（不代建叙事基础实体），本脚本直接输出可操作错误
（缺什么、哪个事件）。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]          # .../skills/event-stager
ROOT = SKILL_DIR.parents[2]                               # 项目根（skills/<name> 上跳 3 级）
CYPHER_EXEC = ROOT / ".claude" / "scripts" / "cypher_exec.py"
BATCH_LIMIT = 3


def run_cypher(cypher: str) -> list:
    proc = subprocess.run(
        [sys.executable, str(CYPHER_EXEC), "-c", cypher, "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    out = proc.stdout
    start, end = out.find("["), out.rfind("]")
    if start == -1 or end == -1:
        raise RuntimeError(f"cypher_exec 未返回 JSON（退出码 {proc.returncode}）:\n"
                           f"stderr: {proc.stderr}\nstdout: {out}")
    return json.loads(out[start:end + 1])


def q(v: str) -> str:
    return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"


SELFTEST_PROBE = (
    "MATCH (e:Event) WITH e LIMIT 1 "
    "OPTIONAL MATCH (e)-[:occurs_at]->(l:Location) "
    "WITH e, collect(DISTINCT l.id) AS loc_ids "
    "RETURN e.id AS id, loc_ids")


def selftest() -> int:
    """最小探针：图库连接 + 聚合物化形态（双后端 Memgraph/Neo4j 兼容）可用性。"""
    try:
        run_cypher(SELFTEST_PROBE)
    except RuntimeError as exc:
        text = str(exc)
        if "Unbound variable" in text:
            hint = "后端不接受「WITH 物化聚合」形态（聚合缺陷传导）——核对 cypher_exec.py 硬约束 11"
        elif "Auth" in text or "Unauthorized" in text or "credential" in text:
            hint = "认证失败——检查 settings.json 的 neo4j_password 或 NEO4J_PASSWORD 环境变量"
        elif ("ServiceUnavailable" in text or "Failed to establish" in text
              or "Connection" in text):
            hint = "连不上图库——确认服务运行（NEO4J_URI / bolt://localhost:7687）"
        else:
            hint = "未知错误，完整信息如下"
        print(f"selftest FAIL：{hint}\n{text}")
        return 2
    print("selftest OK：连接 + WITH 物化聚合形态可用（双后端）")
    return 0


def build_scope_clause(ids, titles, window) -> str:
    """组合 WHERE 子句（内联值；id 精确、title 精确、时间窗 [起, 止次日)）。"""
    conds = []
    if ids:
        conds.append("e.id IN [" + ",".join(q(i) for i in ids) + "]")
    if titles:
        conds.append("e.title IN [" + ",".join(q(t) for t in titles) + "]")
    if window:
        conds.append(f"e.time >= {q(window[0] + ' 00:00:00')} AND e.time < {q(window[1] + ' 00:00:00')}")
    if not conds:
        raise SystemExit("至少给一个 selector：--ids / --titles / --window")
    return " OR ".join(conds)


def preflight(ids, titles, window) -> dict:
    scope = run_cypher(
        "MATCH (e:Event) WHERE " + build_scope_clause(ids, titles, window) + " "
        "OPTIONAL MATCH (e)-[:occurs_at]->(l:Location) "
        "WITH e, collect(DISTINCT {id: l.id, name: l.name}) AS locations "
        "OPTIONAL MATCH (c:Character)-[:involved]->(e) "
        "WITH e, locations, collect(DISTINCT {id: c.id, name: c.name}) AS chars "
        "RETURN e.id AS id, e.title AS title, e.time AS time, locations, chars "
        "ORDER BY time")
    if not scope:
        return {"verdict": "EMPTY", "scope": [], "failures": [{
            "error": "范围内无事件——检查 id/title 拼写或时间窗（含 selector 是否全空）"}],
            "batch": {}, "assets": {}}

    # 过滤 OPTIONAL MATCH 未命中时的占位空值（id 为 null 的收集项）
    for ev in scope:
        ev["locations"] = [x for x in ev["locations"] if x["id"]]
        ev["chars"] = [x for x in ev["chars"] if x["id"]]

    failures = []
    for ev in scope:
        if not ev["locations"]:
            failures.append({"event": f"{ev['title']} ({ev['id']})", "missing": "occurs_at Location",
                             "fix": "先补齐 occurs_at 定位（叙事基础实体不在本层创建域）"})
        if not ev["chars"]:
            failures.append({"event": f"{ev['title']} ({ev['id']})", "missing": "involved Character",
                             "fix": "先补齐 involved 参与人（叙事基础实体不在本层创建域）"})

    # 批次切分（单轮 ≤3，取时间最早）
    if len(scope) > BATCH_LIMIT:
        batch = {"this_round": [e["id"] for e in scope[:BATCH_LIMIT]],
                 "next_round": [e["id"] for e in scope[BATCH_LIMIT:]]}
        detail = [e for e in scope[:BATCH_LIMIT]]
    else:
        batch = {"this_round": [e["id"] for e in scope], "next_round": []}
        detail = scope

    # 演出资源现状（只对本周批次的 involved/occurs_at 实体查——探索步的全部 facts）
    char_ids, loc_ids = set(), set()
    for ev in detail:
        char_ids.update(c["id"] for c in ev["chars"])
        loc_ids.update(l["id"] for l in ev["locations"])
    chars = run_cypher(
        "MATCH (c:Character) WHERE c.id IN " + json.dumps(sorted(char_ids)) + " "
        "OPTIONAL MATCH (c)-[:has_appearance]->(a:AppearanceStyle) "
        "OPTIONAL MATCH (a)-[:produces]->(ds:DesignSheet) "
        "OPTIONAL MATCH (ds)-[:produces]->(i:IllusDesign) "
        "OPTIONAL MATCH (cs:CostumeStyle)-[:outfit_for]->(i) "
        "RETURN c.id AS char_id, c.name AS char, c.status AS char_status, "
        "ds.id AS ds_id, i.id AS illus_id, "
        "coalesce(cs.name, '<无着装>') AS costume "
        "ORDER BY char, costume") if char_ids else []
    scenes = run_cypher(
        "MATCH (l:Location) WHERE l.id IN " + json.dumps(sorted(loc_ids)) + " "
        "OPTIONAL MATCH (l)-[:part_of]->(sp:Spot) "
        "OPTIONAL MATCH (sp)-[:realizes]->(sc:Scene) "
        "RETURN l.id AS loc_id, l.name AS loc, sp.id AS spot_id, sp.name AS spot, "
        "sp.status AS spot_status, sc.id AS scene_id, sc.name AS scene, "
        "sc.status AS scene_status ORDER BY loc, spot") if loc_ids else []
    # 着装现状（has_costume 直查）：含 stager 占位（status=0，无 DesignSheet 链，
    # 上方 chars 四段链查不到）——防同缺口重复建占位（占位与真身重名打架）
    costumes = run_cypher(
        "MATCH (c:Character) WHERE c.id IN " + json.dumps(sorted(char_ids)) + " "
        "OPTIONAL MATCH (c)-[:has_costume]->(cs:CostumeStyle) "
        "OPTIONAL MATCH (cs)-[:outfit_for]->(i:IllusDesign) "
        "RETURN c.id AS char_id, c.name AS char, cs.id AS costume_id, "
        "cs.name AS costume, cs.status AS costume_status, "
        "i.id AS illus_id, i.status AS illus_status "
        "ORDER BY char, costume") if char_ids else []

    return {"verdict": "FAIL" if failures else "PASS",
            "scope": scope, "failures": failures, "batch": batch,
            "assets": {"chars": chars, "costumes": costumes, "scenes": scenes}}


def main() -> int:
    ap = argparse.ArgumentParser(description="stager 前置核验（只读）")
    ap.add_argument("--ids", default="", help="event id 列表（逗号分隔）")
    ap.add_argument("--titles", default="", help="event title 列表（逗号分隔）")
    ap.add_argument("--window", default="", help="时间窗 起,止（止为开区间次日）")
    ap.add_argument("--json", action="store_true", help="纯 JSON 输出（默认人读格式）")
    ap.add_argument("--selftest", action="store_true",
                    help="最小探针自检（连接 + 双后端聚合形态），与 selector 互斥")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    ids = [x for x in args.ids.split(",") if x]
    titles = [x for x in args.titles.split(",") if x]
    window = [x for x in args.window.split(",") if x]
    if window and len(window) != 2:
        raise SystemExit("--window 需要 起,止 两个日期")

    try:
        r = preflight(ids, titles, window)
    except RuntimeError as exc:
        print(f"preflight 执行失败（人话分诊见下；可先跑 --selftest 定位）：\n{exc}")
        return 2
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 1 if r["verdict"] == "FAIL" else 0

    print(f"verdict: {r['verdict']}")
    print(f"\n== 范围（{len(r['scope'])} 事件） ==")
    for ev in r["scope"]:
        print(f"  {ev['time']}  {ev['title']} ({ev['id']})")
        print(f"      at: {', '.join(l['name'] for l in ev['locations']) or '<缺 occurs_at>'}"
              f" | who: {', '.join(c['name'] for c in ev['chars']) or '<缺 involved>'}")
    if r["failures"]:
        print(f"\n== 契约违规（报错停止） ==")
        for f in r["failures"]:
            if "error" in f:
                print(f"  {f['error']}")
            else:
                print(f"  {f['event']}: 缺 {f['missing']} → {f['fix']}")
    b = r["batch"]
    if b.get("next_round"):
        print(f"\n== 批次（>{BATCH_LIMIT} 切轮）: 本轮 {len(b['this_round'])} 个，"
              f"下轮 {len(b['next_round'])} 个 ==")
    a = r["assets"]
    if a.get("chars"):
        print(f"\n== 立绘链现状 ==")
        for c in a["chars"]:
            if c["ds_id"]:
                tail = f" → {c['costume']}" + (f" (IllusDesign {c['illus_id']})" if c["illus_id"] else "")
                print(f"  {c['char']}: DesignSheet {c['ds_id']}{tail}")
            else:
                note = "（占位 Character，外貌链不在本层）" if c["char_status"] == 0 \
                    else "（无外貌链——着装继承不可用，缺口走 CostumeStyle/IllusDesign 占位）"
                print(f"  {c['char']}: {note}")
    if a.get("costumes"):
        print(f"\n== 着装现状（has_costume 直查，含占位——同缺口勿重复建占位） ==")
        for cs in a["costumes"]:
            ph = " <占位待消化>" if cs["costume_status"] == 0 else ""
            il = f" → IllusDesign {cs['illus_id']} (status={cs['illus_status']})" if cs["illus_id"] else ""
            print(f"  {cs['char']}: {cs['costume']}{ph}{il}")
    if a.get("scenes"):
        print(f"\n== 空间链现状 ==")
        for s in a["scenes"]:
            scene_part = f" → Scene {s['scene']}" + (f" (status={s['scene_status']})" if s["scene_id"] else "（无机位）") if s["spot_id"] else ""
            print(f"  {s['loc']}: " + (f"Spot {s['spot']}" + (f" (status={s['spot_status']})" if s["spot_status"] is not None else "") + scene_part if s["spot_id"] else "（无 Spot——空间缺口，占位候选）"))
    return 1 if r["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
