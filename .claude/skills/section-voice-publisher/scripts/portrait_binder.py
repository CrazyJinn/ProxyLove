"""选绘（say 行 → StandingIllustration）候选池生成与建边应用。

section-voice-publisher 配音判断期的选绘两步（3b 之前的候选、3b 之后的应用）：
  candidates  查图产候选池 JSON（每 (scene_block, who) 的可选立绘 + 兜底 IllusDesign 决策）
  apply       读 tasks JSON 的 stand 字段 → 新变体兜底建 + depicts 补建 + uses 边幂等替换

设计约束（00_init/Schema/剧情.md uses 边）：
  - 选绘范围 ⊇ 配音挑行：say 且 status∈{0,-1}，另含 status=10 且无 uses 边的
    补选绘行（先配音、角色着装链后建的时序坑，链就绪后回头补选绘；配音挑行
    voice_bundler.collect_graph_tasks 仍只认 {0,-1}，两范围自此不再相同。
    status=11 已批行不自动纳入——重选须经显式驳回）
  - 每句 say 行都显式建 uses 边（sync=false）；apply 先全量校验后单事务写，任一项不合法即
    整体拒绝（不写图）——LLM 漏判可补 tasks 后重跑，无图副作用
  - 候选池与 apply 共用同一 IllusDesign 解析（确定性：depicts 已有 > 场景事件 wears >
    has_costume 兜底；同级歧义按 id 字典序取首并记 warning，重跑稳定）
  - **形象版本时间线**（DesignSheet 版本链，如剪发前后）：三路候选 IllusDesign 一律回溯
    `<-[:produces]-(ds:DesignSheet)` 按 ds.active_from 过滤，取「≤本节叙事位置
    (chapter_no*1000+section_no) 的最新版本」——多版本角色（sec02 剪发后）自动取新形象，
    场景已 depicts 的旧版本被滤除并记 warning；单版本角色恒等于唯一版（零行为变化）

CLI:
  python portrait_binder.py candidates --section <sec_id> [-o out.json]
  python portrait_binder.py apply --section <sec_id> --tasks <tasks.json> [--report out.json]
退码：0 成功 / 1 前置校验或 tasks 不合法 / 2 参数错。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 同目录：script_splitter
from script_splitter import _q, _run_cypher, _run_cypher_multi  # noqa: E402
from snowflake_base62 import SnowflakeGenerator  # noqa: E402

_GEN = SnowflakeGenerator()

# IllusDesign 解析优先级（候选列 → 其所属 DesignSheet 列 → source 标签）
_PRIORITY = (("depicts_id", "depicts_ds", "depicts"),
             ("wears_id", "wears_ds", "event_wears"),
             ("default_id", "default_ds", "default_costume"))

_POS_CACHE = {}   # section_id → 叙事位置 int 或 None
_EFF_CACHE = {}   # (section_id, who) → 生效 DesignSheet dict 或 None


# ── 公共查询 ─────────────────────────────────────────────────

def fetch_section_head(section_id: str) -> dict:
    """Section → SecScript 头信息 + scene_blocks（sc≠11 raise）。"""
    rows = _run_cypher(
        "MATCH (:Section {id:'" + section_id + "'})-[:has_outline]->(:SecOutline)"
        "-[:produces]->(sc:SecScript) "
        "RETURN sc.id AS sc_id, sc.status AS st, sc.scene_blocks AS scene_blocks LIMIT 1"
    )
    if not rows:
        raise ValueError(f"Section {section_id} 无 SecScript（先跑 chapter-dialoguer 产定稿）")
    st = rows[0]["st"]
    if st != 11:
        raise ValueError(f"SecScript.status={st}（须 11 定稿已批才能选绘）")
    blocks = []
    raw = rows[0].get("scene_blocks")
    if raw:
        try:
            blocks = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, json.JSONDecodeError):
            blocks = []
    return {"sc_id": rows[0]["sc_id"], "scene_blocks": blocks or []}


def judgeable_lines(section_id: str) -> list:
    """待判 say 行（选绘范围 = 配音挑行 ∪ 补选绘行）：say ∧ (status∈{0,-1}
    ∨ (status=10 ∧ 无 uses 边))，按 produces.order。补选绘行 = 已配音待审但
    选绘期候选池空没建成 uses 边（先配音、着装链后建），链就绪后由此补。"""
    return _run_cypher(
        "MATCH (:Section {id:'" + section_id + "'})-[:has_outline]->(:SecOutline)"
        "-[:produces]->(sc:SecScript)-[p:produces]->(l:LineAudio) "
        "WHERE l.op = 'say' AND (l.status IN [0, -1] "
        "OR (l.status = 10 AND NOT (l)-[:uses]->())) "
        "OPTIONAL MATCH (l)-[:uses]->(st:StandingIllustration) "
        "RETURN l.id AS node_id, l.who AS who, l.scene_block_id AS block, l.text AS text, "
        "l.status AS status, st.id AS current_stand ORDER BY p.order"
    )


def _section_pos(section_id: str):
    """Section 叙事位置 = chapter_no*1000+section_no；缺 Chapter/编号 → None（降级不过滤）。"""
    if section_id not in _POS_CACHE:
        rows = _run_cypher(
            "MATCH (sec:Section {id:" + _q(section_id) + "})<-[:has_section]-(ch:Chapter) "
            "RETURN ch.chapter_no AS cn, sec.section_no AS sn LIMIT 1"
        )
        _POS_CACHE[section_id] = (int(rows[0]["cn"]) * 1000 + int(rows[0].get("sn") or 0)
                                  if rows and rows[0].get("cn") is not None else None)
    return _POS_CACHE[section_id]


def _effective_ds(section_id: str, who: str, warnings: list):
    """该 (节, 角色) 生效的 DesignSheet 版本 → {"id","slug","notes"} 或 None。

    形象版本时间线（DesignSheet 版本链，如剪发前后）：取 active_from 为空（首版）或
    ≤本节叙事位置的最新版本；并列（同 active_from）按 id 字典序取首 + warning；全部
    active_from 在未来（病态）→ 最早版兜底 + warning。None = 不过滤（无定位/无 DS，
    单版本角色常态——行为与旧版一致）。
    """
    key = (section_id, who)
    if key in _EFF_CACHE:
        return _EFF_CACHE[key]
    eff = None
    pos = _section_pos(section_id)
    if pos is None:
        warnings.append(f"{section_id}：缺 Chapter/section_no，形象版本时间线过滤跳过（旧行为）")
    else:
        _base = ("MATCH (c:Character {name:" + _q(who) + "})-[:has_appearance]->()"
                 "-[:produces]->(ds:DesignSheet) ")
        rows = _run_cypher(
            _base + "WHERE ds.active_from IS NULL OR ds.active_from <= " + str(pos) + " "
            "WITH coalesce(ds.active_from, -1) AS af, ds ORDER BY af DESC, ds.id ASC "
            "WITH af, collect({id: ds.id, slug: ds.slug, notes: ds.delta_notes}) AS cands "
            "ORDER BY af DESC LIMIT 1 RETURN cands"
        )
        if not rows:  # 病态兜底：全部版本 active_from 在未来 → 取最早版
            rows = _run_cypher(
                _base + "WITH coalesce(ds.active_from, -1) AS af, ds ORDER BY af ASC, ds.id ASC "
                "WITH af, collect({id: ds.id, slug: ds.slug, notes: ds.delta_notes}) AS cands "
                "ORDER BY af ASC LIMIT 1 RETURN cands"
            )
            if rows:
                warnings.append(f"{who}：本节叙事位置早于全部设计图版本的 active_from，取最早版兜底")
        if rows:
            cands = rows[0]["cands"]
            ids = sorted(c["id"] for c in cands)
            if len(ids) > 1:
                warnings.append(f"{who}：生效点并列多个设计图版本（{ids}），按 id 字典序取首 {ids[0]}")
            eff = next(c for c in cands if c["id"] == ids[0])
    _EFF_CACHE[key] = eff
    return eff


def resolve_illus(section_id: str, scene_name: str, who: str, warnings: list) -> tuple:
    """该 (scene, who) 的着装 IllusDesign 决策 → (illus_id, source)。

    三路候选一次查询带回，Python 按 depicts > 事件 wears > has_costume 优先级取一；
    同级多个按 id 字典序取首（决定性），歧义记 warning。三路全空 → ("", "")。
    depicts 路径须经 outfit_for←has_costume 连到该 Character——同 Scene 常 depicts 多个
    角色的 IllusDesign，不过滤角色会把别人的着装池当候选。
    **形象版本过滤**：三路候选一律回溯所属 DesignSheet（illus←produces←DS，1:1 无行
    乘积），不属于生效版本（_effective_ds）的 IllusDesign 先滤除（记 warning）再取首——
    多版本角色（sec02 剪发后）自动取新形象，共用场景 depicts 的旧版本被时间线拦下。
    """
    rows = _run_cypher(
        "MATCH (sec:Section {id:" + _q(section_id) + "}) "
        "OPTIONAL MATCH (c0:Character {name:" + _q(who) + "}) "
        "OPTIONAL MATCH (sec)-[:contains]->(scn:Scene {name:" + _q(scene_name) + "}) "
        "OPTIONAL MATCH (scn)-[:depicts]->(d:IllusDesign)<-[:outfit_for]-(:CostumeStyle)<-[:has_costume]-(c0) "
        "OPTIONAL MATCH (d)<-[:produces]-(dsd:DesignSheet) "
        "OPTIONAL MATCH (scn)<-[:has_scene]-(loc:Location) "
        "OPTIONAL MATCH (c0)-[:involved]->(e:Event)-[:wears]->(wc:CostumeStyle), "
        "(c0)-[:has_costume]->(wc), (wc)-[:outfit_for]->(wi:IllusDesign), "
        "(e)-[:occurred_at]->(loc) "
        "OPTIONAL MATCH (wi)<-[:produces]-(dsw:DesignSheet) "
        "OPTIONAL MATCH (c0)-[:has_costume]->(:CostumeStyle)-[:outfit_for]->(di:IllusDesign) "
        "OPTIONAL MATCH (di)<-[:produces]-(dsx:DesignSheet) "
        "RETURN DISTINCT d.id AS depicts_id, dsd.id AS depicts_ds, "
        "wi.id AS wears_id, dsw.id AS wears_ds, "
        "di.id AS default_id, dsx.id AS default_ds, "
        "scn.name AS scene_hit"
    )
    if scene_name and rows and all(r.get("scene_hit") is None for r in rows):
        warnings.append(f"{scene_name}：未命中本节 contains 的任何 Scene（名字与图 Scene 名不符）——"
                        f"depicts/wears 两路将降级，请核对 SecScript.scene_blocks 的 scene_name")
    eff = _effective_ds(section_id, who, warnings)
    for col, ds_col, source in _PRIORITY:
        kept, dropped = set(), set()
        for r in rows:
            v = r.get(col)
            if not v:
                continue
            if eff and r.get(ds_col) != eff["id"]:
                dropped.add(v)
            else:
                kept.add(v)
        if dropped:
            warnings.append(f"{scene_name}/{who}：{source} 路径 {len(dropped)} 个 IllusDesign "
                            f"属未生效设计图版本（{sorted(dropped)}），按 active_from 时间线过滤")
        vals = sorted(kept)
        if len(vals) > 1:
            warnings.append(f"{scene_name}/{who}：{source} 路径命中多个 IllusDesign（{vals}），"
                            f"按 id 字典序取首 {vals[0]}")
        if vals:
            return vals[0], source
    return "", ""


def stands_of_illus(illus_id: str) -> list:
    """该 IllusDesign 的全部变体（含未出图——LLM 可选，出图由 plot-design 推进）。"""
    return _run_cypher(
        "MATCH (:IllusDesign {id:" + _q(illus_id) + "})-[:expands_to]->(st:StandingIllustration) "
        "RETURN st.id AS id, st.variant_label AS variant_label, st.status AS status, "
        "st.description AS description ORDER BY variant_label"
    )


# ── candidates：候选池 ────────────────────────────────────────

def build_candidates(section_id: str) -> dict:
    """待判行 + 每 (block, who) 候选立绘池 → JSON dict（供 3b LLM 读）。"""
    head = fetch_section_head(section_id)
    warnings = []
    scene_name_of = {b.get("block"): b.get("scene_name") for b in head["scene_blocks"]}
    lines = judgeable_lines(section_id)

    scenes = {}
    for block in dict.fromkeys(l.get("block") for l in lines):  # 保序去重
        scene_name = scene_name_of.get(block) or ""
        if not scene_name:
            warnings.append(f"{block}：scene_blocks 无此块（scene_name 未知），选绘 IllusDesign 解析降级")
        chars = {}
        for who in dict.fromkeys(l.get("who") for l in lines if l.get("block") == block):
            illus_id, source = resolve_illus(section_id, scene_name, who, warnings)
            stands = stands_of_illus(illus_id) if illus_id else []
            if not illus_id:
                warnings.append(f"{block}/{who}：无着装 IllusDesign（depicts/事件 wears/has_costume "
                                f"均空或全被形象版本过滤）——apply 无法建边，需先补角色着装链")
            entry = {"illus_id": illus_id, "illus_source": source, "stands": stands}
            eff = _effective_ds(section_id, who, warnings)   # 已缓存，取生效形象供 LLM 对齐
            if eff:
                entry["design_sheet"] = eff                  # {"id","slug","notes"}——剪发后形象以 notes 为准
            chars[who] = entry
        scenes[block] = {"scene_name": scene_name, "chars": chars}

    return {"section_id": section_id, "sc_id": head["sc_id"],
            "scenes": scenes, "lines": lines, "warnings": warnings}


# ── apply：建边 ───────────────────────────────────────────────

def _flat_tasks(tasks: dict) -> list:
    """tasks JSON（{char: [item…]}）→ 展平 item 列表。"""
    return [item for items in tasks.values() for item in items]


def _find_existing_stand(illus_id: str, label: str):
    """同 IllusDesign 下同 variant_label 的已有变体 → stand_id or None。"""
    rows = _run_cypher(
        "MATCH (:IllusDesign {id:" + _q(illus_id) + "})-[:expands_to]->"
        "(st:StandingIllustration) WHERE st.variant_label = " + _q(label) + " "
        "RETURN st.id AS id LIMIT 1"
    )
    return rows[0]["id"] if rows else None


def _lookup_stand(stand_id: str) -> dict:
    """stand 节点存在性与归属（expands_to 的 IllusDesign）→ {id, variant_label, illus_id} or {}。"""
    rows = _run_cypher(
        "MATCH (st:StandingIllustration {id:" + _q(stand_id) + "}) "
        "OPTIONAL MATCH (i:IllusDesign)-[:expands_to]->(st) "
        "RETURN st.id AS id, st.variant_label AS variant_label, i.id AS illus_id LIMIT 1"
    )
    return rows[0] if rows else {}


def build_actions(section_id: str, tasks: dict, warnings: list) -> tuple:
    """tasks + 候选解析 → (cypher 语句列表, 报告 dict)。校验失败 raise ValueError（一次列出全部坏项）。"""
    head = fetch_section_head(section_id)
    scene_name_of = {b.get("block"): b.get("scene_name") for b in head["scene_blocks"]}
    judgeable = {l["node_id"]: l for l in judgeable_lines(section_id)}
    items = _flat_tasks(tasks)

    errors = []
    planned = []       # [{node_id, line, stand_id, new_variant?, who, scene_name, illus_id}]
    label_cache = {}   # (illus_id, label) → stand_id（同组合多句复用同一新变体）
    resolve_cache = {}  # (scene_name, who) → (illus_id, source)
    for item in items:
        node_id = item.get("node_id")
        line = judgeable.get(node_id)
        if line is None:
            errors.append(f"行 {node_id}：不属于本节待判 say 行（不存在 / 非 say / "
                          f"status∉{{0,-1}} 且非 10 无 uses 补选绘行）")
            continue
        stand = item.get("stand")
        if stand is None or stand == "":
            errors.append(f"行 {node_id}（{line.get('who')}：{(line.get('text') or '')[:20]}…）：缺 stand 字段")
            continue
        who = line.get("who") or ""
        block = line.get("block") or ""
        scene_name = scene_name_of.get(block) or ""

        def _resolve():
            if (scene_name, who) not in resolve_cache:
                resolve_cache[(scene_name, who)] = resolve_illus(section_id, scene_name, who, warnings)
            return resolve_cache[(scene_name, who)]

        if isinstance(stand, str):
            hit = _lookup_stand(stand)
            if not hit:
                errors.append(f"行 {node_id}：stand_id {stand} 不存在（StandingIllustration 无此节点）")
                continue
            if hit.get("illus_id") and scene_name:
                # 归属检查：LLM 传的 stand_id 是否出自本 (scene, who) 的候选 IllusDesign
                cand_id, _src = _resolve()
                if cand_id and hit["illus_id"] != cand_id:
                    warnings.append(f"行 {node_id}：stand {hit.get('variant_label')} 属 IllusDesign "
                                    f"{hit['illus_id']}，与 {block}/{who} 候选 {cand_id} 不同"
                                    f"（跨着装/形象版本引用，已放行）")
            planned.append({"node_id": node_id, "stand_id": stand, "who": who,
                            "scene_name": scene_name, "illus_id": hit.get("illus_id") or ""})
        elif isinstance(stand, dict):
            label = (stand.get("variant_label") or "").strip()
            if not (2 <= len(label) <= 24):
                errors.append(f"行 {node_id}：新变体 variant_label 须 2~24 字（得 {label!r}）")
                continue
            illus_id, _src = _resolve() if scene_name else ("", "")
            if not illus_id:
                errors.append(f"行 {node_id}：{block}/{who} 无着装 IllusDesign，无法兜底建新变体")
                continue
            if not (stand.get("description") or "").strip():
                warnings.append(f"行 {node_id}：新变体 {label} 缺 description（变体氛围），出图把握降级")
            cache_key = (illus_id, label)
            if cache_key not in label_cache:
                existing = _find_existing_stand(illus_id, label)
                label_cache[cache_key] = existing or _GEN.next_id_base62()
            planned.append({"node_id": node_id, "stand_id": label_cache[cache_key],
                            "new_variant": {"id": label_cache[cache_key], "variant_label": label,
                                            "description": (stand.get("description") or "").strip()},
                            "who": who, "scene_name": scene_name, "illus_id": illus_id})
        else:
            errors.append(f"行 {node_id}：stand 须为 stand_id 字符串或 {{variant_label, description}} 对象")

    if errors:
        raise ValueError("tasks 校验失败（未写图，补齐后重跑）：\n  - " + "\n  - ".join(errors))

    stmts = []
    report = {"counts": {"lines_bound": 0, "new_variants": 0, "reused_variants": 0,
                         "depicts_created": 0, "uses_replaced": 0},
              "new_variants": [], "warnings": warnings}
    depicts_seen = set()
    built_ids = set()   # 已产建节点语句的新变体 id（同 (illus,label) 多句只建一次）
    for p in planned:
        nv = p.get("new_variant")
        if nv:
            sid, label, desc = nv["id"], nv["variant_label"], nv["description"]
            existing = _find_existing_stand(p["illus_id"], label)
            if existing:
                p["stand_id"] = existing          # 查重兜底：同 label 已有则复用
                report["counts"]["reused_variants"] += 1
            elif sid not in built_ids:
                built_ids.add(sid)
                stmts.append(
                    f"MERGE (st:StandingIllustration {{" + f"id:{_q(sid)}" + "}) "
                    f"SET st.variant_label={_q(label)}, st.description={_q(desc or None)}, st.status=0;"
                )
                stmts.append(
                    f"MATCH (i:IllusDesign {{" + f"id:{_q(p['illus_id'])}" + "}), "
                    f"(st:StandingIllustration {{" + f"id:{_q(sid)}" + "}) "
                    f"MERGE (i)-[e:expands_to]->(st) SET e.sync=true, e.variant_label={_q(label)};"
                )
                stmts.append(
                    f"MATCH (:Character {{" + f"name:{_q(p['who'])}" + "})-[:has_voice_style]->(ls:LanguageStyle), "
                    f"(st:StandingIllustration {{" + f"id:{_q(sid)}" + "}) "
                    f"MERGE (ls)-[r:ref_style]->(st) SET r.sync=true;"
                )
                report["counts"]["new_variants"] += 1
                report["new_variants"].append({"id": sid, "variant_label": label,
                                               "illus_id": p["illus_id"], "char": p["who"],
                                               "scene_name": p["scene_name"]})
        if p["scene_name"] and p["illus_id"]:
            key = (p["scene_name"], p["illus_id"])
            if key not in depicts_seen:
                depicts_seen.add(key)
                stmts.append(
                    f"MATCH (s:Scene {{" + f"name:{_q(p['scene_name'])}" + "}), "
                    f"(i:IllusDesign {{" + f"id:{_q(p['illus_id'])}" + "}) "
                    f"MERGE (s)-[d:depicts]->(i) SET d.sync=false;"
                )
                report["counts"]["depicts_created"] += 1
        stmts.append(
            f"MATCH (l:LineAudio {{" + f"id:{_q(p['node_id'])}" + "}) "
            f"OPTIONAL MATCH (l)-[o:uses]->() DELETE o "
            f"WITH DISTINCT l "
            f"MATCH (st:StandingIllustration {{" + f"id:{_q(p['stand_id'])}" + "}) "
            f"MERGE (l)-[u:uses]->(st) SET u.sync=false;"
        )
        report["counts"]["lines_bound"] += 1
        report["counts"]["uses_replaced"] += 1
    return stmts, report


def apply(section_id: str, tasks_path: str, report_path=None) -> dict:
    """校验 → 单事务写图 → 报告。"""
    tasks = json.loads(Path(tasks_path).read_text(encoding="utf-8"))
    warnings = []
    stmts, report = build_actions(section_id, tasks, warnings)
    if stmts:
        _run_cypher_multi(stmts)
    report.update({"section_id": section_id, "tasks": tasks_path, "statements": len(stmts)})
    if report_path:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


# ── CLI ──────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="选绘候选池与建边应用（say 行 → StandingIllustration）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_c = sub.add_parser("candidates", help="查图产候选池 JSON")
    p_c.add_argument("--section", required=True, help="Section 节点 ID（snowflake）")
    p_c.add_argument("-o", "--out", help="落盘路径（缺省仅 stdout）")
    p_a = sub.add_parser("apply", help="读 tasks 的 stand 字段建 uses 边")
    p_a.add_argument("--section", required=True, help="Section 节点 ID（snowflake）")
    p_a.add_argument("--tasks", required=True, help="voice tasks JSON 路径（含 stand 字段）")
    p_a.add_argument("--report", help="报告 JSON 落盘路径（缺省仅 stdout）")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "candidates":
            data = build_candidates(args.section)
            text = json.dumps(data, ensure_ascii=False, indent=2)
            if args.out:
                Path(args.out).parent.mkdir(parents=True, exist_ok=True)
                Path(args.out).write_text(text + "\n", encoding="utf-8")
            print(text)
            if not data["lines"]:
                print("[candidates] 0 行待判——无需选绘", file=sys.stderr)
            else:
                print(f"OK: lines={len(data['lines'])} blocks={len(data['scenes'])} "
                      f"warnings={len(data['warnings'])}", file=sys.stderr)
        else:
            report = apply(args.section, args.tasks, report_path=args.report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            c = report["counts"]
            print(f"OK: lines_bound={c['lines_bound']} new_variants={c['new_variants']} "
                  f"reused_variants={c['reused_variants']} depicts={c['depicts_created']}",
                  file=sys.stderr)
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"选绘失败: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
