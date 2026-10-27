"""选绘（say 行 → StandingIllustration）候选池生成与建边应用。

section-voice-publisher 配音判断期的选绘两步（3b 之前的候选、3b 之后的应用）：
  candidates  查图产候选池 JSON（每 (scene_block, who) 的可选立绘 + 兜底 IllusDesign 决策）
  apply       读 tasks JSON 的 stand 字段 → 新变体兜底建 + uses 边幂等替换

设计约束（00_init/Schema/剧情.md uses 边）：
  - 选绘范围 ⊇ 配音挑行：say 且 status∈{0,-1}，另含 status=10 且无 uses 边的
    补选绘行（先配音、角色着装链后建的时序坑，链就绪后回头补选绘；配音挑行
    voice_bundler.collect_graph_tasks 仍只认 {0,-1}，两范围自此不再相同。
    status=11 已批行不自动纳入——重选须经显式驳回）
  - 每句 say 行都显式建 uses 边（sync=false）；apply 先全量校验后单事务写，任一项不合法即
    整体拒绝（不写图）——LLM 漏判可补 tasks 后重跑，无图副作用
  - **Event 驱动化**：候选池与 apply 共用同一 IllusDesign 解析——
    `Section→includes→Event→refines→SubEvent→anchored_at→Scene(块名)` 的事件 `→appears_as→IllusDesign`
    直读，零推理；多个终点按 id 字典序取首并记 warning，重跑稳定。原 depicts/wears/
    has_costume 三路推演已随边删除废止
  - **形象版本判定已物化到写边时**（appears_as 建边/回填时按事件时间 vs
    DesignSheet.active_from 选版）——读路径零过滤，_effective_ds 仅作 LLM 对齐展示

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

# IllusDesign 解析来源标签（Event 驱动化后单路直读）
_SOURCE = "appears_as"

_POS_CACHE = {}   # section_id → 叙事位置 int 或 None
_EFF_CACHE = {}   # (section_id, who) → 生效 DesignSheet dict 或 None


# ── 公共查询 ─────────────────────────────────────────────────

def fetch_section_head(section_id: str) -> dict:
    """Section 头信息（sec.status≠11 raise）。Section.scene_blocks 已废止——块 id=scene_id，块→场景名经 id 直查图（_scene_names_of）。"""
    rows = _run_cypher(
        "MATCH (sec:Section {id:'" + section_id + "'}) "
        "RETURN sec.status AS st LIMIT 1"
    )
    if not rows:
        raise ValueError(f"Section {section_id} 不存在")
    st = rows[0]["st"]
    if st != 11:
        raise ValueError(f"Section.status={st}（须 11 定稿已确认才能选绘）")
    return {"section_id": section_id}


def _scene_names_of(scene_ids: list) -> dict:
    """块 id（scene_id）→ 图 Scene 真名。id 直连（无 name join，无漂移空间）。"""
    if not scene_ids:
        return {}
    quoted = ",".join(_q(i) for i in scene_ids if i)
    rows = _run_cypher(
        "MATCH (s:Scene) WHERE s.id IN [" + quoted + "] RETURN s.id AS i, s.name AS n")
    return {r["i"]: r["n"] for r in rows if r.get("i")}


def judgeable_lines(section_id: str) -> list:
    """待判 say 行（选绘范围 = 配音挑行 ∪ 补选绘行）：say ∧ (status∈{0,-1}
    ∨ (status=10 ∧ 无 uses 边))，按 produces.order。补选绘行 = 已配音待审但
    选绘期候选池空没建成 uses 边（先配音、着装链后建），链就绪后由此补。"""
    return _run_cypher(
        "MATCH (sec:Section {id:'" + section_id + "'})-[p:produces]->(l:LineAudio) "
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

    SubEvent 细化层：`Section→includes→Event→refines→SubEvent→anchored_at→Scene(块名)`
    的演出段 `→appears_as→IllusDesign` 直读（经 outfit_for←has_costume 限定到该 Character），
    零推理——形象版本判定在写 appears_as 边时已物化，读路径不做 active_from 过滤。
    多个终点按 id 字典序取首（决定性），记 warning；全空 → ("", "")。
    scene_name 为空（块 id 不命中图 Scene）时退化为「节内该角色全部 sub 的 appears_as」。
    """
    where = ("WHERE scn.name = " + _q(scene_name) + " ") if scene_name else ""
    rows = _run_cypher(
        "MATCH (sec:Section {id:" + _q(section_id) + "})-[:includes]->(e:Event) "
        "MATCH (e)-[:refines]->(sub:SubEvent) "
        "OPTIONAL MATCH (sub)-[:anchored_at]->(scn:Scene) " + where +
        "OPTIONAL MATCH (c0:Character {name:" + _q(who) + "})-[:involved]->(e) "
        "OPTIONAL MATCH (sub)-[:appears_as]->(il:IllusDesign)"
        "<-[:outfit_for]-(:CostumeStyle)<-[:has_costume]-(c0) "
        "RETURN DISTINCT il.id AS illus_id"
    )
    if scene_name and not rows:
        warnings.append(f"{scene_name}：本节 sub 无 anchored_at 命中此 Scene"
                        f"（块 id 与图 Scene 不符，或未归组/未细化）——请核对 ink 块标记 id 是否为 scene_id"
                        f" 及 event-refiner/scene-designer 归组")
    vals = sorted({r["illus_id"] for r in rows if r.get("illus_id")})
    if len(vals) > 1:
        warnings.append(f"{scene_name}/{who}：appears_as 命中多个 IllusDesign（{vals}），"
                        f"按 id 字典序取首 {vals[0]}")
    if vals:
        return vals[0], _SOURCE
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
    fetch_section_head(section_id)
    warnings = []
    lines = judgeable_lines(section_id)
    scene_name_of = _scene_names_of([l.get("block") for l in lines])

    scenes = {}
    for block in dict.fromkeys(l.get("block") for l in lines):  # 保序去重
        scene_name = scene_name_of.get(block) or ""
        if not scene_name:
            warnings.append(f"{block}：块 id 不命中图 Scene（非 scene_id？）——选绘 IllusDesign 解析降级")
        chars = {}
        for who in dict.fromkeys(l.get("who") for l in lines if l.get("block") == block):
            illus_id, source = resolve_illus(section_id, scene_name, who, warnings)
            stands = stands_of_illus(illus_id) if illus_id else []
            if not illus_id:
                warnings.append(f"{block}/{who}：无着装 IllusDesign（该场景事件无 appears_as "
                                f"或角色未 involved）——apply 无法建边，需补 appears_as（E1）或先补角色着装链")
            entry = {"illus_id": illus_id, "illus_source": source, "stands": stands}
            eff = _effective_ds(section_id, who, warnings)   # 已缓存，取生效形象供 LLM 对齐
            if eff:
                entry["design_sheet"] = eff                  # {"id","slug","notes"}——剪发后形象以 notes 为准
            chars[who] = entry
        scenes[block] = {"scene_name": scene_name, "chars": chars}

    return {"section_id": section_id, "scene_name_of": scene_name_of,
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
    fetch_section_head(section_id)
    judgeable = {l["node_id"]: l for l in judgeable_lines(section_id)}
    scene_name_of = _scene_names_of([l.get("block") for l in judgeable.values()])
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
                         "uses_replaced": 0},
              "new_variants": [], "warnings": warnings}
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
                # Character→has_voice_style 反查（char-stand-designer 前驱）
                report["counts"]["new_variants"] += 1
                report["new_variants"].append({"id": sid, "variant_label": label,
                                               "illus_id": p["illus_id"], "char": p["who"],
                                               "scene_name": p["scene_name"]})
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
                  f"reused_variants={c['reused_variants']}",
                  file=sys.stderr)
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"选绘失败: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
