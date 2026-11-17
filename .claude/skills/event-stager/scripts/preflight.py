#!/usr/bin/env python3
"""stager 前置核验：范围解析 + 入口核验 + 演出资源现状（只读）。

用法：
    python preflight.py --consensus <共识文档路径> [--json]           # 共识模式（新事件未写图）
    python preflight.py --ids <id1,id2> [--titles t1,t2] [--window 起,止] [--json]
    （图模式三 selector 可组合，与 --consensus 互斥；--window 止为开区间次日，如 2024-06-01,2024-06-16）

输出（两模式同构）：
  verdict   PASS / FAIL
  mode      graph / consensus
  scope     命中事件 {id, title, time, locations[], chars[]}（按 time 排序；
            共识模式 id=None——事件尚未写图，title 即指称）
  failures  契约违规清单（缺 occurs_at / 缺 involved / 既有 id 图上查无，含修复指引）
  batch     单轮上限 3：命中 >3 时取时间最早 3 个，余者列入 next_round
            （图模式按 id、共识模式按 title 标识）
  placeholders（共识模式）占位 Character/Location 名录——尚不在图，无演出资源，
            着装/空间链必然全新占位（预期态，非缺口报错）
  assets    演出资源现状（§2 探索步的 facts；共识模式只查既有 id 实体）：
    chars    每 involved Character 的立绘链：Character→AppearanceStyle→DesignSheet→IllusDesign←outfit_for← CostumeStyle
    costumes 每 involved Character 的着装（has_costume 直查，含 stager 占位 status=0——防同缺口重复建占位）
    scenes   每 occurs_at Location 的空间链：Spot →realizes→ Scene

共识解析：扫 `## [I2 事件] <title>` 头与其下 time/occurs_at/involved 行；
occurs_at/involved 逐项识别「名称(id)」既有引用与「[占位:名称]」占位指称。
解析失败（无 I2 条目 / 缺 time / 裸名无 id 无占位）→ 可操作报错退出码 2，
SKILL.md 约定由 LLM 回读共识人肉分诊。

聚合查询一律段段 WITH 物化（双后端 Memgraph/Neo4j 兼容，见 cypher_exec.py 硬约束 11）。

FAIL 语义：范围内任一事件缺 occurs_at Location 或缺 involved Character →
stager 报错停止（不代建叙事基础实体），本脚本直接输出可操作错误
（缺什么、哪个事件；共识模式的缺字段回 event-ideator 修共识，S4 补边仅适用图模式）。
"""

import argparse
import json
import re
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


# ── 共识文档解析（--consensus 模式）────────────────────────────────────

I2_HEADER = re.compile(r"^##\s*\[I2\s*事件\]\s*(.+?)\s*$")
FIELD_LINE = re.compile(r"^-\s*([^:：]+?)\s*[:：]\s*(.*)$")
ID_REF = re.compile(r"^(.*?)\s*\(\s*([A-Za-z0-9]{8,12})\s*\)\s*$")
PLACEHOLDER_REF = re.compile(r"\[占位[:：]\s*(.+?)\s*\]")
TIME_FMT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def split_refs(value: str) -> list:
    """把 occurs_at/involved 的值拆成逐项指称，每项分类：
    {"kind":"id","name","id"} 既有引用 / {"kind":"placeholder","name"} 占位 /
    {"kind":"bad","raw"} 裸名（无 id 无占位标记——ideator 纪律违例）。"""
    items = [x.strip() for x in re.split(r"[、,，]", value) if x.strip()]
    out = []
    for it in items:
        m = PLACEHOLDER_REF.search(it)
        if m:
            out.append({"kind": "placeholder", "name": m.group(1)})
            continue
        m = ID_REF.match(it)
        if m and m.group(1):
            out.append({"kind": "id", "name": m.group(1), "id": m.group(2)})
            continue
        out.append({"kind": "bad", "raw": it})
    return out


def parse_consensus(path: str) -> list:
    """解析共识文档的 I2 事件条目（title/time/occurs_at/involved）。
    解析失败 → 抛 SystemExit（可操作报错：哪条目缺什么）。"""
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"共识文档不存在：{path}")
    events, cur, errors = [], None, []
    for ln, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        m = I2_HEADER.match(line)
        if m:
            cur = {"title": m.group(1), "line": ln, "time": None,
                   "occurs_at": "", "involved": ""}
            events.append(cur)
            continue
        if line.startswith("## "):
            cur = None  # 离开当前 I2 条目（I1/I3/… 的字段不收）
            continue
        if cur is None or not line.startswith("-"):
            continue
        m = FIELD_LINE.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "time":
            cur["time"] = val
        elif key in ("occurs_at", "involved"):
            cur[key] = (cur[key] + "、" + val) if cur[key] else val
    if not events:
        raise SystemExit(
            f"共识文档未找到任何 '## [I2 事件]' 条目——核对 {p.name} 是否为 "
            "event-ideator 产出的共识文档（*_共识.md）")
    for ev in events:
        if not ev["time"]:
            errors.append(f"事件「{ev['title']}」（L{ev['line']}）缺 time 字段")
        elif not TIME_FMT.match(ev["time"]):
            errors.append(f"事件「{ev['title']}」time 非法（须 yyyy-MM-dd HH:mm:ss）：{ev['time']}")
        for field in ("occurs_at", "involved"):
            for ref in split_refs(ev[field] or ""):
                if ref["kind"] == "bad":
                    errors.append(
                        f"事件「{ev['title']}」{field} 指称「{ref['raw']}」既无 id 也无占位标记"
                        "（ideator 纪律：既有实体 id 内联，缺的写 [占位:名称]）")
    if errors:
        raise SystemExit("共识文档解析失败（逐条修复后重跑）：\n  - " + "\n  - ".join(errors))
    return events


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
        return {"mode": "graph", "verdict": "EMPTY", "scope": [], "failures": [{
            "error": "范围内无事件——检查 id/title 拼写或时间窗（含 selector 是否全空）"}],
            "batch": {}, "placeholders": {}, "assets": {}}

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

    return {"mode": "graph",
            "verdict": "FAIL" if failures else "PASS",
            "scope": scope, "failures": failures, "batch": batch,
            "placeholders": {},
            "assets": query_assets(char_ids, loc_ids)}


def query_assets(char_ids: set, loc_ids: set) -> dict:
    """演出资源三查询（只读）：立绘链 / has_costume 直查（含占位防重）/ 空间链。"""
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
    return {"chars": chars, "costumes": costumes, "scenes": scenes}


def preflight_consensus(path: str) -> dict:
    """共识模式：解析 *_共识.md 的 I2 事件条目 → 既有 id 验图 → 占位收集 → 资产查询。
    事件尚未写图：scope 条目 id=None；缺字段回 event-ideator（不走 S4）；
    占位实体无演出资源（预期态）——assets 只查既有 id 实体。"""
    events = parse_consensus(path)
    scope, failures = [], []
    ph_chars, ph_locs = [], []
    all_char_ids, all_loc_ids = set(), set()

    for ev in events:
        locs, chs = [], []
        for ref in split_refs(ev["occurs_at"]):
            if ref["kind"] == "placeholder":
                ph_locs.append(ref["name"])
                locs.append({"id": None, "name": f"[占位]{ref['name']}"})
            else:
                all_loc_ids.add(ref["id"])
                locs.append({"id": ref["id"], "name": ref["name"]})
        for ref in split_refs(ev["involved"]):
            if ref["kind"] == "placeholder":
                ph_chars.append(ref["name"])
                chs.append({"id": None, "name": f"[占位]{ref['name']}"})
            else:
                all_char_ids.add(ref["id"])
                chs.append({"id": ref["id"], "name": ref["name"]})
        if not locs:
            failures.append({"event": ev["title"], "missing": "occurs_at Location",
                             "fix": "共识条目缺 occurs_at——回 event-ideator 补共识（S4 补边仅适用图模式）"})
        if not chs:
            failures.append({"event": ev["title"], "missing": "involved Character",
                             "fix": "共识条目缺 involved——回 event-ideator 补共识（S4 补边仅适用图模式）"})
        scope.append({"id": None, "title": ev["title"], "time": ev["time"],
                      "locations": locs, "chars": chs})

    # 既有 id 验图（错拼即报错回 ideator，防静默错挂）
    def verify(ids, label):
        if not ids:
            return set()
        rows = run_cypher(
            f"MATCH (n:{label}) WHERE n.id IN " + json.dumps(sorted(ids)) + " "
            "RETURN n.id AS id LIMIT 100")
        return {r["id"] for r in rows}
    ok_chars = verify(all_char_ids, "Character")
    ok_locs = verify(all_loc_ids, "Location")
    for ev in scope:
        for ref in ev["chars"]:
            if ref["id"] and ref["id"] not in ok_chars:
                failures.append({"event": ev["title"],
                                 "missing": f"Character id {ref['id']}（{ref['name']}）图上查无",
                                 "fix": "回 event-ideator 修正共识——既有实体 id 须现查内联，防静默错挂"})
        for ref in ev["locations"]:
            if ref["id"] and ref["id"] not in ok_locs:
                failures.append({"event": ev["title"],
                                 "missing": f"Location id {ref['id']}（{ref['name']}）图上查无",
                                 "fix": "回 event-ideator 修正共识——既有实体 id 须现查内联，防静默错挂"})

    # 批次切分（同图模式：time 最早 3 个；无图 id，按 title 标识）
    scope.sort(key=lambda e: e["time"])
    keys = [e["title"] for e in scope]
    if len(scope) > BATCH_LIMIT:
        batch = {"this_round": keys[:BATCH_LIMIT], "next_round": keys[BATCH_LIMIT:]}
        detail = scope[:BATCH_LIMIT]
    else:
        batch = {"this_round": keys, "next_round": []}
        detail = scope

    # 资产只查本周批次的既有 id 实体（占位实体无演出资源——链路必然全新占位）
    char_ids, loc_ids = set(), set()
    for ev in detail:
        char_ids.update(c["id"] for c in ev["chars"] if c["id"])
        loc_ids.update(l["id"] for l in ev["locations"] if l["id"])

    return {"mode": "consensus",
            "verdict": "FAIL" if failures else "PASS",
            "scope": scope, "failures": failures, "batch": batch,
            "placeholders": {"characters": sorted(set(ph_chars)),
                             "locations": sorted(set(ph_locs))},
            "assets": query_assets(char_ids, loc_ids)}


def main() -> int:
    ap = argparse.ArgumentParser(description="stager 前置核验（只读）")
    ap.add_argument("--consensus", default="",
                    help="共识文档路径（02_剧情数据/*_共识.md）——与三 selector 互斥")
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
    if args.consensus and (ids or titles or window):
        raise SystemExit("--consensus 与 --ids/--titles/--window 互斥（共识模式不需要图内 selector）")

    try:
        if args.consensus:
            r = preflight_consensus(args.consensus)
        else:
            r = preflight(ids, titles, window)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"preflight 执行失败（人话分诊见下；可先跑 --selftest 定位）：\n{exc}")
        return 2
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 1 if r["verdict"] == "FAIL" else 0

    print(f"verdict: {r['verdict']}（mode: {r.get('mode', 'graph')}）")
    print(f"\n== 范围（{len(r['scope'])} 事件） ==")
    for ev in r["scope"]:
        tag = f"({ev['id']})" if ev["id"] else "（共识条目，未写图）"
        print(f"  {ev['time']}  {ev['title']} {tag}")
        print(f"      at: {', '.join(l['name'] for l in ev['locations']) or '<缺 occurs_at>'}"
              f" | who: {', '.join(c['name'] for c in ev['chars']) or '<缺 involved>'}")
    if r["failures"]:
        print(f"\n== 契约违规（报错停止） ==")
        for f in r["failures"]:
            if "error" in f:
                print(f"  {f['error']}")
            else:
                print(f"  {f['event']}: 缺 {f['missing']} → {f['fix']}")
    ph = r.get("placeholders") or {}
    if ph.get("characters") or ph.get("locations"):
        print(f"\n== 占位实体（尚不在图，无演出资源——着装/空间链必然全新占位，预期态非缺口） ==")
        if ph.get("locations"):
            print(f"  Location: {'、'.join(ph['locations'])}")
        if ph.get("characters"):
            print(f"  Character: {'、'.join(ph['characters'])}")
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
