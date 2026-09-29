"""main.py — 代恋·图数据库工作流管理页（纯 Python：FastAPI + Jinja2 + 零前端 JS）。

路由（设计文档 §6）：总览 / 审批中心 / media 产物。交互全部 form POST + 303 整页刷新。
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.repo.graph_repo import get_client, load_settings, PROJECT_ROOT
from app.services import audit, ink as ink_svc
from app.services import board as b
from app.services import cascade, exporter
from app.services import hints
from app.services import node_fields
from app.services import queries as q
from app.services.artifacts import decode_rel, local_path, resolve
from app.services.snapshot_importer import import_snapshot
from app.services.status import (
    NODE_STATUS, status_class, status_text, voice_design_substate,
)

ROOT = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(ROOT / "app" / "templates"))
templates.env.filters["sttext"] = status_text
templates.env.filters["stclass"] = status_class

app = FastAPI(title="代恋·图数据库管理页")
app.mount("/static", StaticFiles(directory=str(ROOT / "app" / "static")), name="static")


def repo():
    return get_client()


# ── 总览 ──

@app.get("/")
def index(request: Request):
    db = repo()
    counts = q.label_counts(db)
    pending = q.pending_approvals(db)
    totals = q.graph_totals(db)
    bgm_wait = db.run(
        "MATCH (:Scene)-[:has_bgm]->(b:BgmTrack) WHERE b.status = 1 "
        "RETURN b.id AS id, b.name AS name, b.audio_path AS audio_path"
    )
    for b in bgm_wait:
        if not b["audio_path"]:
            # Schema 约定：归档路径 = 13_BGM/<name>.wav（节点未显式存时推导）
            b["audio_path"] = f"13_BGM/{b['name']}.wav"
    # Memgraph 对四段 OPTIONAL MATCH 聚合链有变量绑定 bug（Unbound variable: ch）——
    # 拆两条简单查询 + Python 侧聚合。
    chapters = db.run(
        """
        MATCH (ch:Chapter)
        OPTIONAL MATCH (ch)-[:has_section]->(sec:Section)
        WITH ch, sec ORDER BY ch.chapter_no, sec.section_no
        RETURN ch.id AS id, ch.title AS title, ch.chapter_no AS no, ch.status AS status,
               collect(sec { .id, .section_no }) AS secs
        ORDER BY no
        """
    )
    sec_stats = {
        r["sec_id"]: r
        for r in db.run(
            """
            MATCH (sec:Section)
            OPTIONAL MATCH (sec)-[:has_outline]->(so:SecOutline)
            OPTIONAL MATCH (so)-[:produces]->(sc:SecScript)
            OPTIONAL MATCH (sc)-[:produces]->(l:LineAudio)
            RETURN sec.id AS sec_id,
                   (so.status = 1) AS ol_ok, (sc.status = 11) AS sc_ok,
                   count(l) AS n_line,
                   sum(CASE WHEN l.status = 11 THEN 1 ELSE 0 END) AS n_line_ok
            """
        )
    }
    ch_out = []
    for ch in chapters:
        n_sec = len(ch["secs"])
        n_ol = n_sc = n_line = n_line_ok = 0
        for s in ch["secs"]:
            st_ = sec_stats.get(s["id"])
            if st_:
                if st_["ol_ok"]:
                    n_ol += 1
                if st_["sc_ok"]:
                    n_sc += 1
                n_line += st_["n_line"] or 0
                n_line_ok += st_["n_line_ok"] or 0
        ch_out.append({**ch, "n_sec": n_sec, "n_ol": n_ol, "n_sc": n_sc,
                       "n_line": n_line, "n_line_ok": n_line_ok})
    # 三链聚合
    chains = {
        "char": {"name": "角色美术+声音", "total": 0, "redo": 0, "todo": 0, "review": 0},
        "scene": {"name": "场景美术", "total": 0, "redo": 0, "todo": 0, "review": 0},
        "plot": {"name": "剧情", "total": 0, "redo": 0, "todo": 0, "review": 0},
    }
    for c in counts:
        ch_ = chains.get(c["chain"])
        if not ch_ or c["st"] is None:
            continue
        ch_["total"] += c["c"]
        if c["st"] == -1:
            ch_["redo"] += c["c"]
        elif c["st"] == 0:
            ch_["todo"] += c["c"]
        elif c["st"] == 10:
            ch_["review"] += c["c"]
    return templates.TemplateResponse(request, "index.html", {
        "counts": counts, "pending": pending, "totals": totals,
        "chains": chains, "bgm_wait": bgm_wait, "chapters": ch_out,
    })


# ── 审批中心 ──

@app.get("/approvals")
def approvals(request: Request):
    db = repo()
    pending = q.pending_approvals(db)
    return templates.TemplateResponse(request, "approvals.html", {"pending": pending})


def _decision_redirect(node_id: str) -> RedirectResponse:
    return RedirectResponse(f"/approvals?just={node_id}", status_code=303)


@app.post("/approvals/{node_id}/decision")
def decision(node_id: str, action: str = Form(...), candidate: str = Form("")):
    db = repo()
    node = q.get_node(db, node_id)
    if not node:
        raise HTTPException(404, "节点不存在")
    label = list(node.keys()) and next(iter(node.labels)) if hasattr(node, "labels") else ""
    # 统一取 label
    label = db.run("MATCH (n {id:$id}) RETURN labels(n)[0] AS l", {"id": node_id})[0]["l"]

    if action == "approve":
        db.run_write(
            "MATCH (n {id:$id}) SET n.status = 11, n.reviewed_at = toString(date())",
            {"id": node_id},
        )
        audit.log(node_id, label, "approve", "")
    elif action == "reject":
        db.run_write(
            "MATCH (n {id:$id}) SET n.status = 0, "
            "n.attempts = CASE WHEN n.attempts IS NULL THEN 1 ELSE n.attempts + 1 END",
            {"id": node_id},
        )
        audit.log(node_id, label, "reject", "")
    elif action == "resubmit":
        # SecScript 人工微调回路：0/1/11 → 10，只改 sc，不动行
        db.run_write("MATCH (n {id:$id}) SET n.status = 10", {"id": node_id})
        audit.log(node_id, label, "resubmit", "")
    elif action == "adopt":
        # VoiceDesign 候选采用：固化 ref、删 candidates_path、status 保持 10
        if label != "VoiceDesign":
            raise HTTPException(400, "adopt 仅用于 VoiceDesign")
        db.run_write(
            "MATCH (v:VoiceDesign {id:$id}) "
            "SET v.ref_audio_path = $ref, v.candidates_path = null, v.adopted_candidate = $cand",
            {"id": node_id, "ref": candidate, "cand": candidate},
        )
        audit.log(node_id, label, "adopt", candidate)
    else:
        raise HTTPException(400, f"未知 action: {action}")
    return _decision_redirect(node_id)


# ── 各类型审阅器 ──

@app.get("/approvals/script/{sc_id}")
def script_review(request: Request, sc_id: str):
    db = repo()
    if not q.get_node(db, sc_id):
        raise HTTPException(404, "节点不存在")
    ctx = q.script_context(db, sc_id)
    node = q.get_node(db, sc_id)
    source = ""
    art = resolve(node.get("script_path"), "text") if node else None
    if art and art["exists"]:
        source = Path(art["abs"]).read_text(encoding="utf-8", errors="replace")
    lines = ink_svc.render_ink(source)
    sec = q.section_of_script(db, sc_id)
    rows = q.line_rows(db, sec["sec_id"]) if sec else []
    return templates.TemplateResponse(request, "script_review.html", {
        "ctx": ctx, "lines": lines, "source": source, "art": art,
        "llm_count": ink_svc.llm_placeholder_count(source), "rows": rows, "sec": sec,
    })


@app.get("/approvals/voice/{vd_id}")
def voice_review(request: Request, vd_id: str):
    db = repo()
    try:
        ctx = q.voice_design_context(db, vd_id)
    except IndexError:
        raise HTTPException(404, "VoiceDesign 不存在")
    sub = voice_design_substate({"status": ctx["status"], "candidates_path": ctx["candidates_path"]})
    ref_art = resolve(ctx["ref_audio_path"], "audio")
    cands = []
    if ctx["candidates_path"]:
        cinfo = resolve(ctx["candidates_path"], "text")
        if cinfo and cinfo["exists"]:
            try:
                manifest = json.loads(Path(cinfo["abs"]).read_text(encoding="utf-8"))
                # manifest 结构兼容：{candidates:[{...ref/audios...}]} 或 list
                raw = manifest.get("candidates", manifest) if isinstance(manifest, dict) else manifest
                for item in raw:
                    ref_rel = item.get("ref_path") or item.get("ref") or ""
                    cands.append({
                        "name": item.get("name") or item.get("id", "?"),
                        "ref_url": resolve(ref_rel, "audio") or {},
                        "audios": [
                            resolve(a.get("path", ""), "audio") or {}
                            for a in item.get("audios", item.get("emotions", []))
                        ],
                        "instruct": item.get("instruct", ""),
                    })
            except (json.JSONDecodeError, OSError):
                cands = []
    return templates.TemplateResponse(request, "voice_review.html", {
        "ctx": ctx, "sub": sub, "ref_art": ref_art, "cands": cands,
        "cinfo": resolve(ctx["candidates_path"], "text") if ctx["candidates_path"] else None,
    })


@app.get("/approvals/chapter/{ch_id}")
def chapter_review(request: Request, ch_id: str):
    db = repo()
    try:
        ctx = q.chapter_context(db, ch_id)
    except IndexError:
        raise HTTPException(404, "Chapter 不存在")
    brief = ""
    art = resolve(ctx.get("brief_path"), "text") if ctx.get("brief_path") else None
    if art and art["exists"]:
        brief = Path(art["abs"]).read_text(encoding="utf-8", errors="replace")
    return templates.TemplateResponse(request, "chapter_review.html", {
        "ctx": ctx, "brief": brief, "art": art,
    })


@app.get("/approvals/image/{node_id}")
def image_review(request: Request, node_id: str):
    db = repo()
    try:
        ctx = q.image_node_context(db, node_id)
    except IndexError:
        raise HTTPException(404, "节点不存在")
    art = resolve(ctx.get("image_path"), "image")
    prompt_text = ""
    part = resolve(ctx.get("prompt_path"), "text")
    if part and part["exists"]:
        prompt_text = Path(part["abs"]).read_text(encoding="utf-8", errors="replace")
    return templates.TemplateResponse(request, "image_review.html", {
        "ctx": ctx, "art": art, "prompt_text": prompt_text, "part": part,
    })


# ── 行级音频审（按节聚合）──

@app.get("/approvals/section/{sec_id}")
def section_audio_review(request: Request, sec_id: str):
    db = repo()
    try:
        head = db.run(
        """
        MATCH (ch:Chapter)-[:has_section]->(sec:Section {id:$id})
        OPTIONAL MATCH (sec)-[:has_outline]->(:SecOutline)-[:produces]->(sc:SecScript)
        RETURN sec.id AS sec_id, sec.title AS title, sec.section_no AS no,
               ch.title AS ch_title, ch.chapter_no AS ch_no, sc.id AS sc_id, sc.status AS sc_status
        """,
        {"id": sec_id},
    )[0]
    except IndexError:
        raise HTTPException(404, "Section 不存在")
    rows = q.line_rows(db, sec_id)
    audio = []
    for r in rows:
        a = None
        if r.get("voice_key"):
            # voice_key = <char>-<chapter_stem>-<scene_block_id>-<行id>（后两段 [A-Za-z0-9_]+ 无连字符）
            key = r["voice_key"]
            parts = key.split("-")
            if len(parts) >= 4:
                stem = parts[1]
                block = parts[2]
                rel = f"15_声音/{stem}/{block}/{key}.wav"
                a = resolve(rel, "audio")
        if a is None and r.get("ambient_track"):
            # transition/bed_start 行：ambient_track = <prefix>-<stem>-<block>-<行id>，同目录
            track = r["ambient_track"]
            parts = track.split("-")
            if len(parts) >= 4:
                rel = f"15_声音/{parts[1]}/{parts[2]}/{track}.wav"
                a = resolve(rel, "audio")
        audio.append(a)
    return templates.TemplateResponse(request, "section_audio.html", {
        "head": head, "rows": rows, "audio": audio,
    })


@app.post("/approvals/line/{line_id}/decision")
def line_decision(line_id: str, action: str = Form(...), back: str = Form("")):
    db = repo()
    row = db.run(
        """
        MATCH (l:LineAudio {id:$id})<-[:produces]-(sc:SecScript)<-[:produces]-(:SecOutline)<-[:has_outline]-(sec:Section)
        RETURN sec.id AS sec_id
        """,
        {"id": line_id},
    )
    if not row:
        raise HTTPException(404, "行不存在或未挂节")
    sec_id = row[0]["sec_id"]
    if action == "approve":
        db.run_write("MATCH (l {id:$id}) SET l.status = 11", {"id": line_id})
        audit.log(line_id, "LineAudio", "approve", "")
    elif action == "reject":
        db.run_write(
            "MATCH (l {id:$id}) SET l.status = 0, "
            "l.attempts = CASE WHEN l.attempts IS NULL THEN 1 ELSE l.attempts + 1 END",
            {"id": line_id},
        )
        audit.log(line_id, "LineAudio", "reject", "")
    else:
        raise HTTPException(400, f"未知 action: {action}")
    return RedirectResponse(f"/approvals/section/{sec_id}", status_code=303)


# ── 生产看板 ──

@app.get("/board")
def board_page(request: Request, tab: str = "char"):
    if tab not in ("char", "scene", "plot"):
        tab = "char"
    db = repo()
    chars = scenes = plot = None
    groups = None
    sel = sel_head = None
    sel_graph = None
    if tab == "char":
        groups = b.char_groups(db)
        sel = request.query_params.get("sel", "")
        if sel:
            head = db.run(
                "MATCH (c:Character {id:$id}) RETURN c.id AS id, c.name AS name", {"id": sel}
            )
            if head:
                sel_head = head[0]
                sel_graph = b.char_art_graph(db, sel)
    elif tab == "scene":
        groups = b.scene_groups(db)
        sel = request.query_params.get("sel", "")
        if sel:
            head = db.run(
                "MATCH (l:Location {id:$id}) RETURN l.id AS id, l.name AS name", {"id": sel}
            )
            if head:
                sel_head = head[0]
                sel_graph = b.scene_art_graph(db, sel)
    else:
        plot = b.plot_board(db)
        for ch in plot["chapters"]:
            ch["ready"] = hints.chapter_ready(
                ch["status"],
                [{"ol_ok": s["ol_st"] == 1, "sc_ok": s["sc_st"] == 11,
                  "lines_ok": s["n_ok"], "lines_total": s["n_line"]} for s in ch["secs"]],
            )
            ch["hint"] = hints.chapter_hint(ch["title"])
            for s in ch["secs"]:
                g = hints.section_gate(ch["status"], s["ol_st"] == 1, s["sc_st"], s["n_ok"], s["n_line"])
                s.update(g)
                s["hint"] = hints.section_hint(s["id"], s["title"])
        for g_ in plot["stand_gaps"]:
            g_["hint"] = hints.stand_hint(g_["id"])
    return templates.TemplateResponse(request, "board.html", {
        "chars": chars, "scenes": scenes, "plot": plot, "tab": tab,
        "tab_names": {"char": "角色", "scene": "场景", "plot": "剧情"},
        "groups": groups, "sel": sel, "sel_head": sel_head, "sel_graph": sel_graph,
        "sel_graph_json": json.dumps(sel_graph, ensure_ascii=False) if sel_graph else None,
    })


# ── 角色美术子图 + 节点编辑 ──

EDITABLE_SAFE_FIELDS = {  # 高危字段（级联语义）不进表单，提示用 Cypher 直改
    "DesignSheet": {"active_from", "slug", "delta_notes"},
}


@app.get("/board/char/{char_id}")
def char_art_page(request: Request, char_id: str):
    db = repo()
    head = db.run(
        "MATCH (c:Character {id:$id}) RETURN c.id AS id, c.name AS name", {"id": char_id}
    )
    if not head:
        raise HTTPException(404, "角色不存在")
    g = b.char_art_graph(db, char_id)
    return templates.TemplateResponse(request, "char_art.html", {
        "head": head[0], "g": g, "g_json": json.dumps(g, ensure_ascii=False),
    })


@app.get("/board/node/{node_id}/props")
def node_props(node_id: str):
    db = repo()
    rows = db.run("MATCH (n {id:$id}) RETURN properties(n) AS p, labels(n)[0] AS l", {"id": node_id})
    if not rows:
        raise HTTPException(404, "节点不存在")
    p = rows[0]["p"]
    label = rows[0]["l"]
    safe_skip = EDITABLE_SAFE_FIELDS.get(label, set())
    fields = []
    for k in sorted(p.keys()):
        fields.append({
            "key": k,
            "value": "" if p[k] is None else str(p[k]),
            "locked": k in safe_skip or k == "id",
            "zh": node_fields.zh_of(label, k),
        })
    # 图上没有的可选字段（常用编辑目标）
    optional = {
        "Character": ["description", "character_tags", "color_direction", "priority"],
        "AppearanceStyle": ["appearance", "hair", "eye", "height_cm", "shape_language", "visual_tone"],
        "LanguageStyle": ["vocabulary", "rhythm", "habits", "emotion_patterns", "description"],
        "CostumeStyle": ["name", "outfit_style", "garment", "footwear", "accessory_type"],
        "VoiceDesign": ["instruct", "ref_text", "description"],
        "DesignSheet": ["prompt_path", "image_path"],
        "IllusDesign": ["adaptation_notes", "display_scale"],
        "StandingIllustration": ["variant_label", "description", "eye", "brow", "mouth", "hand"],
        "SceneLayer": ["prompt_path", "image_path"],
        "Scene": ["atmosphere", "composition", "lighting", "color_direction"],
        "Location": ["description"],
        "BgmTrack": ["description", "prompt", "audio_path", "mode", "loop", "status"],
    }.get(label, [])
    for k in optional:
        if k not in p:
            fields.append({"key": k, "value": "", "locked": False, "zh": node_fields.zh_of(label, k)})
    return {"label": label, "id": node_id, "fields": fields}


@app.get("/board/node/{node_id}/art")
def node_art(node_id: str):
    db = repo()
    r = q.node_artifacts(db, node_id)
    if not r:
        raise HTTPException(404, "节点不存在")
    return r


@app.post("/board/node/{node_id}/review")
def node_review(node_id: str, action: str = Form(...)):
    """生产页内审批：approve 10→11 / reject 10→0（JSON 返回）。"""
    if action not in ("approve", "reject"):
        raise HTTPException(400, "action 必须是 approve|reject")
    db = repo()
    row = db.run("MATCH (n {id:$id}) RETURN labels(n)[0] AS l, n.status AS st", {"id": node_id})
    if not row:
        raise HTTPException(404, "节点不存在")
    if row[0]["st"] != 10:
        return {"ok": False, "error": f"当前 status={row[0]['st']}，仅待审(10)可审"}
    if action == "approve":
        db.run_write("MATCH (n {id:$id}) SET n.status = 11", {"id": node_id})
    else:
        db.run_write(
            "MATCH (n {id:$id}) SET n.status = 0, "
            "n.attempts = CASE WHEN n.attempts IS NULL THEN 1 ELSE n.attempts + 1 END",
            {"id": node_id},
        )
    audit.log(node_id, row[0]["l"], action, "board-inline")
    return {"ok": True, "status": 11 if action == "approve" else 0}


@app.get("/board/node/{node_id}/preview")
def node_preview(node_id: str, cypher: str = ""):
    """编辑确认卡：级联影响预览（只读 JSON）。"""
    db = repo()
    preview = []
    for tid in cascade.extract_target_ids(cypher):
        for d in cascade.sync_downstream(db, tid):
            d["target"] = tid
            preview.append(d)
    return {"n": len(preview), "preview": preview[:100]}


@app.post("/board/node/{node_id}/save")
def node_save(node_id: str, cypher: str = Form(...)):
    """编辑确认卡：执行 SET + 级联（JSON 返回）。"""
    audit.log(node_id, "node-edit", "executed", cypher[:300])
    db = repo()
    char_id = _char_id_of(db, node_id)
    try:
        r = cascade.execute_with_cascade(db, cypher, True)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:300]}
    return {"ok": True, "cascaded": len(r["cascaded"]), "char_id": char_id}


def _esc_cypher(v: str) -> str:
    return v.replace("\\", "\\\\").replace("'", "\\'")


def _guess_typed(v: str):
    s = v.strip()
    if s == "":
        return None, "null"
    if re.fullmatch(r"-?\d+", s):
        return None, s
    if re.fullmatch(r"-?\d+\.\d+", s):
        return None, s
    if s.lower() in ("true", "false"):
        return None, s.lower()
    return None, f"'{_esc_cypher(s)}'"


def _char_id_of(db, node_id: str) -> str:
    rows = db.run(
        """
        MATCH (n {id:$id})
        OPTIONAL MATCH (c:Character)-[:has_appearance|has_costume|has_voice_style|has_voice_design]->(n)
        OPTIONAL MATCH (c2:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(:DesignSheet)-[:produces]->(n)
        OPTIONAL MATCH (c2)-[:has_costume]->(:CostumeStyle)-[:outfit_for]->(n)
        OPTIONAL MATCH (c3:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(:DesignSheet)-[:produces]->(:IllusDesign)-[:expands_to]->(n)
        RETURN coalesce(c.id, c2.id, c3.id, '') AS cid
        """,
        {"id": node_id},
    )
    return rows[0]["cid"] if rows else ""


# ── 叙事图浏览 ──

@app.get("/graph", name="graph_home")
def graph_home(request: Request, label: str = "Character", q: str = ""):
    db = repo()
    q_text = q.strip()
    rows = b.search_entities(db, label, q_text) if q_text else b.search_entities(db, label, "")
    return templates.TemplateResponse(request, "graph_search.html", {
        "rows": rows, "label": label, "q": q_text,
        "labels": list(b.LABEL_NAME_FIELD.keys()),
    })


@app.get("/graph/{label}/{node_id}")
def graph_detail(request: Request, label: str, node_id: str):
    db = repo()
    if label not in b.LABEL_NAME_FIELD:
        raise HTTPException(404, "未知实体类型")
    d = b.entity_detail(db, label, node_id)
    if not d:
        raise HTTPException(404, "实体不存在")
    sg = b.subgraph_around(db, node_id, max_hops=2)
    # 起点名补齐（subgraph 里 visited 起点无 name）
    for n in sg["nodes"]:
        if n["id"] == node_id:
            n["name"] = d["name"]
            n["label"] = d["label"]
    # 出边分组（按边类型）
    groups: dict[str, list] = {}
    for e in d["out_edges"]:
        groups.setdefault(e["type"], []).append(e)
    return templates.TemplateResponse(request, "graph_detail.html", {
        "d": d, "sg": sg, "sg_json": json.dumps(sg, ensure_ascii=False), "groups": groups,
    })


# ── 数据与设置 ──

@app.get("/data")
def data_page(request: Request, msg: str = ""):
    db = repo()
    totals = q.graph_totals(db)
    audit_rows = audit.tail(50)
    bgm = db.run(
        "MATCH (b:BgmTrack) RETURN b.id AS id, b.name AS n, b.status AS st, b.audio_path AS p ORDER BY b.name"
    )
    s = load_settings()
    return templates.TemplateResponse(request, "data.html", {
        "totals": totals, "audit_rows": audit_rows, "msg": msg, "bgm": bgm,
        "settings": {
            "neo4j_uri": s.get("neo4j_uri"), "neo4j_user": s.get("neo4j_user"),
            "artifact_root": s.get("artifact_root"), "port": s.get("port"),
            "csv_snapshot": s.get("csv_snapshot"),
        },
    })


@app.get("/data/export")
def data_export():
    db = repo()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out = ROOT / "data" / f"ProxyLove_backup_{stamp}.csv"
    r = exporter.export_snapshot(db, out)
    audit.log("-", "export", f"{r['nodes']}n/{r['edges']}e", str(out))
    return FileResponse(out, filename=out.name, media_type="text/csv")


@app.post("/data/import")
def data_import(csv_path: str = Form(...), wipe: bool = Form(False)):
    path = Path(csv_path.strip())
    if not path.is_file():
        return RedirectResponse(f"/data?msg={path}%20不存在", status_code=303)
    if not str(path.resolve()).startswith(str(PROJECT_ROOT)) and path.resolve() != Path(
        load_settings().get("csv_snapshot", "")
    ).resolve() and not str(path).startswith("/tmp/"):
        return RedirectResponse("/data?msg=仅允许仓库内或/tmp的CSV", status_code=303)
    db = repo()
    try:
        r = import_snapshot(db, str(path), wipe=wipe)
    except ValueError as exc:
        return RedirectResponse(f"/data?msg=导入失败：{exc}", status_code=303)
    audit.log("-", "import", f"{r['nodes']}n/{r['edges']}e created={r['created']}", str(path))
    return RedirectResponse(
        f"/data?msg=导入完成：{r['nodes']}节点/{r['edges']}边，新建{r['created']}", status_code=303
    )


@app.post("/data/cypher")
def data_cypher(request: Request, cypher: str = Form(...), confirmed: bool = Form(False)):
    db = repo()
    text = cypher.strip().rstrip(";")
    if not text:
        return RedirectResponse("/data?msg=空语句", status_code=303)
    write = cascade.is_write(text)
    if write and not confirmed:
        # 一段确认：给出级联影响预览，不执行
        preview = []
        for tid in cascade.extract_target_ids(text):
            for d in cascade.sync_downstream(db, tid):
                d["target"] = tid
                preview.append(d)
        return templates.TemplateResponse(request, "cypher_confirm.html", {
            "cypher": text, "preview": preview[:100],
            "no_ids": not cascade.extract_target_ids(text),
        })
    try:
        if write:
            result_wrap = cascade.execute_with_cascade(db, text, confirmed)
            counters = result_wrap["counters"]
            result = [{**counters, "cascade_reset": len(result_wrap["cascaded"])}]
            audit.log("-", "cypher-write", str(result[0]), text[:200])
        else:
            read_q = f"{text} LIMIT 500" if not re.search(r"\bLIMIT\b", text, re.IGNORECASE) else text
            rows = db.run(read_q)
            result = rows
            audit.log("-", "cypher-read", f"{len(rows)}行", text[:200])
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/data?msg=执行失败：{str(exc)[:200]}", status_code=303)
    return templates.TemplateResponse(request, "cypher_result.html", {
        "cypher": text, "rows": result, "write": write,
    })


@app.post("/bgm/{bgm_id}/check")
def bgm_check(bgm_id: str):
    db = repo()
    row = db.run("MATCH (b:BgmTrack {id:$id}) RETURN b.name AS n, b.audio_path AS p", {"id": bgm_id})
    if not row:
        raise HTTPException(404, "BgmTrack 不存在")
    name = row[0]["n"]
    rel = row[0]["p"] or f"13_BGM/{name}.wav"
    art = resolve(rel, "audio")
    if art and art["exists"]:
        db.run_write("MATCH (b {id:$id}) SET b.status = 2", {"id": bgm_id})
        audit.log(bgm_id, "BgmTrack", "archive-detected", rel)
        return RedirectResponse(f"/data?msg=已归档：{rel}（status→2）", status_code=303)
    return RedirectResponse(f"/data?msg=未找到 {rel}（artifact_root 内）", status_code=303)


# ── media（产物文件，白名单根内）──
@app.get("/media/{kind}/{rel:path}")
def media(kind: str, rel: str):
    if kind not in ("image", "audio", "text"):
        raise HTTPException(400, "kind 非法")
    p = local_path(decode_rel(rel))
    if not p:
        raise HTTPException(404, "产物不存在或未挂载")
    mime = {
        "image": "image/png", "audio": "audio/wav", "text": "text/plain; charset=utf-8",
    }[kind]
    return FileResponse(p, media_type=mime)


# ── 健康检查 ──

@app.get("/healthz")
def healthz():
    try:
        db = repo()
        t = q.graph_totals(db)
        return {"ok": True, "nodes": t["nodes"], "edges": t["edges"]}
    except Exception as exc:  # noqa: BLE001
        return PlainTextResponse(f"unhealthy: {exc}", status_code=503)


# ── Agent 触发（dashboard → hermes 会话）──

import subprocess

AGENT_TRIGGER_HELP = """触发格式：
- 提交任意文本 → 转发给 Hermes agent（进入当前活跃的对话会话），由它按需加载 skill 执行。
- 例如：「请运行 char-design 编排：角色「江烈」」「/skill libai-skill 润色这段：……」「推进 ch1 sec05」
"""


@app.get("/agent")
def agent_page(request: Request, msg: str = ""):
    trig = [a for a in audit.tail(200) if a.get("action") == "agent-trigger"][:20]
    s = load_settings()
    webhook_on = bool((s.get("webhook_url") or "").strip()) and bool((s.get("webhook_secret") or "").strip())
    return templates.TemplateResponse(request, "agent.html", {
        "msg": msg, "help": AGENT_TRIGGER_HELP, "triggers": trig, "webhook_on": webhook_on,
    })


@app.post("/agent/trigger")
def agent_trigger(text: str = Form(...)):
    body = text.strip()
    if not body:
        return RedirectResponse("/agent?msg=空指令", status_code=303)
    # webhook 触发（HMAC-SHA256 签名 POST → gateway → agent 会话，deliver=origin）
    # URL/secret 来自 settings.json: webhook_url / webhook_secret（未配置即禁用本功能）
    s = load_settings()
    webhook_url = (s.get("webhook_url") or "").strip()
    webhook_secret = (s.get("webhook_secret") or "").strip()
    if not webhook_url or not webhook_secret:
        return RedirectResponse(
            "/agent?msg=未配置 webhook（55_dashboard/settings.json 的 webhook_url / webhook_secret）",
            status_code=303,
        )
    import hmac as hmac_mod
    import hashlib
    payload = json.dumps({
        "type": "dashboard",  # webhook 事件字段名是 type（event 会被当 unknown 忽略）
        "text": body,
        "who": "dashboard",
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False).encode("utf-8")
    sig = hmac_mod.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    try:
        import urllib.request
        req = urllib.request.Request(
            webhook_url, data=payload, method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=" + sig,
                "X-Hermes-Event": "dashboard",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/agent?msg=触发失败：{str(exc)[:200]}", status_code=303)
    audit.log("-", "agent-trigger", f"webhook-{status}", body[:200])
    return RedirectResponse(f"/agent?msg=已触发（{status}）：{body[:60]} — 结果将回到聊天会话", status_code=303)
