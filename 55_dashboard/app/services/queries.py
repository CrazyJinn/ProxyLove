"""queries.py — 页面数据查询（每页一查，避免 N+1）。全部只读。"""

from __future__ import annotations

from neo4j.graph import Node
from pathlib import Path
import json

from app.services.artifacts import resolve

# ── 总览 ──

OVERVIEW_LABELS = [
    "DesignSheet", "IllusDesign", "StandingIllustration", "SceneLayer", "VoiceDesign",
    "Chapter", "SecScript", "LineAudio", "BgmTrack",
    "AppearanceStyle", "LanguageStyle", "CostumeStyle", "Scene", "SecOutline",
]

CHAIN_OF_LABEL = {
    "AppearanceStyle": "char", "LanguageStyle": "char", "CostumeStyle": "char",
    "VoiceDesign": "char", "DesignSheet": "char", "IllusDesign": "char",
    "StandingIllustration": "char",
    "Scene": "scene", "SceneLayer": "scene", "BgmTrack": "scene",
    "Chapter": "plot", "SecOutline": "plot", "SecScript": "plot", "LineAudio": "plot",
}


def label_counts(repo) -> list[dict]:
    """按 label × status 计数。"""
    rows = repo.run(
        """
        MATCH (n)
        WHERE any(l IN labels(n) WHERE l IN $labels)
        RETURN labels(n)[0] AS label, n.status AS st, count(*) AS c
        ORDER BY label, st
        """,
        {"labels": OVERVIEW_LABELS},
    )
    out = []
    for r in rows:
        out.append({**r, "chain": CHAIN_OF_LABEL.get(r["label"], "")})
    return out


def pending_approvals(repo) -> list[dict]:
    """全部 status=10 待审项 + 面包屑上下文。"""
    return repo.run(
        """
        MATCH (n) WHERE n.status = 10
        OPTIONAL MATCH (sec:Section)-[:has_outline]->(:SecOutline)-[:produces]->(sc:SecScript {id:n.id})
        OPTIONAL MATCH (ch:Chapter)-[:has_section]->(sec)
        OPTIONAL MATCH (c2:Character)-[:has_voice_design]->(vd:VoiceDesign {id:n.id})
        OPTIONAL MATCH (i2:IllusDesign)-[:expands_to]->(st:StandingIllustration {id:n.id})
        OPTIONAL MATCH (c3:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds:DesignSheet {id:n.id})
        OPTIONAL MATCH (ds2:DesignSheet)-[:produces]->(il:IllusDesign {id:n.id})
        OPTIONAL MATCH (c4:Character)-[:has_costume]->(:CostumeStyle)-[:outfit_for]->(il2:IllusDesign {id:n.id})
        OPTIONAL MATCH (s2:Scene)-[:has_layer]->(ly:SceneLayer {id:n.id})
        RETURN n.id AS id, labels(n)[0] AS label,
               coalesce(ch.title, c2.name, c3.name, c4.name, ds2.id, '') AS ctx1,
               coalesce(sec.title, '', '') AS ctx2,
               coalesce(i2.variant_label, '') AS ctx3,
               coalesce(s2.name, '') AS ctx3b
        ORDER BY label, ctx1, ctx2
        """
    )


def graph_totals(repo) -> dict:
    n = repo.run("MATCH (n) RETURN count(n) AS c")[0]["c"]
    e = repo.run("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
    return {"nodes": n, "edges": e}


# ── 审批中心 ──

def get_node(repo, node_id: str) -> Node | None:
    rows = repo.run("MATCH (n {id: $id}) RETURN n", {"id": node_id})
    return rows[0]["n"] if rows else None


def script_context(repo, sc_id: str) -> dict:
    """SecScript 审批页：节/章面包屑 + 本节全部行。"""
    return repo.run(
        """
        MATCH (sc:SecScript {id:$id})
        OPTIONAL MATCH (so:SecOutline)-[:produces]->(sc)
        OPTIONAL MATCH (sec:Section)-[:has_outline]->(so)
        OPTIONAL MATCH (ch:Chapter)-[:has_section]->(sec)
        OPTIONAL MATCH (lines:LineAudio)<-[:produces]-(sc)
        WITH sc, sec, ch, lines ORDER BY lines.who
        RETURN sc.id AS sc_id, sc.status AS sc_status, sc.script_path AS script_path,
               sc.name AS sc_name, sec.title AS sec_title, sec.section_no AS sec_no,
               ch.title AS ch_title, ch.chapter_no AS ch_no,
               count(lines) AS n_lines,
               sum(CASE WHEN lines.status = 11 THEN 1 ELSE 0 END) AS n_approved
        """,
        {"id": sc_id},
    )[0]


def line_rows(repo, sec_id: str) -> list[dict]:
    """某节全部台词行（音频审列表）。"""
    return repo.run(
        """
        MATCH (:Section {id:$sec})-[:has_outline]->(:SecOutline)-[:produces]->(:SecScript)-[p:produces]->(l:LineAudio)
        RETURN l.id AS id, l.op AS op, l.who AS who, l.text AS text, l.emotion AS emotion,
               l.clone_mode AS clone_mode, l.attempts AS attempts, l.status AS status,
               l.voice_key AS voice_key, l.ambient_track AS ambient_track,
               l.scene_block_id AS block, p.order AS ord,
               l.kind AS kind, l.bed AS bed
        ORDER BY p.order
        """,
        {"sec": sec_id},
    )


def section_of_script(repo, sc_id: str) -> dict | None:
    rows = repo.run(
        """
        MATCH (sec:Section)-[:has_outline]->(:SecOutline)-[:produces]->(sc:SecScript {id:$id})
        RETURN sec.id AS sec_id, sec.title AS title, sec.section_no AS no
        """,
        {"id": sc_id},
    )
    return rows[0] if rows else None


def voice_design_context(repo, vd_id: str) -> dict:
    return repo.run(
        """
        MATCH (c:Character)-[:has_voice_design]->(v:VoiceDesign {id:$id})
        RETURN v.id AS id, v.name AS name, v.status AS status, v.instruct AS instruct,
               v.ref_text AS ref_text, v.ref_audio_path AS ref_audio_path,
               v.candidates_path AS candidates_path, c.name AS char_name
        """,
        {"id": vd_id},
    )[0]


def chapter_context(repo, ch_id: str) -> dict:
    return repo.run(
        """
        MATCH (ch:Chapter {id:$id})
        OPTIONAL MATCH (ch)-[:has_section]->(sec:Section)
        WITH ch, sec ORDER BY sec.section_no
        RETURN ch.id AS id, ch.title AS title, ch.chapter_no AS no, ch.status AS status,
               ch.brief_path AS brief_path, ch.summary AS summary, ch.branch_summary AS branch_summary,
               collect(DISTINCT sec { .id, .title, .section_no, .summary }) AS sections
        """,
        {"id": ch_id},
    )[0]


def image_node_context(repo, node_id: str) -> dict:
    """图片类节点（DesignSheet/IllusDesign/Stand/SceneLayer）审批页上下文。"""
    return repo.run(
        """
        MATCH (n {id:$id})
        OPTIONAL MATCH (c:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds:DesignSheet {id:n.id})
        OPTIONAL MATCH (ds2:DesignSheet)-[:produces]->(il:IllusDesign {id:n.id})
        OPTIONAL MATCH (c5:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds2)
        OPTIONAL MATCH (c6:Character)-[:has_costume]->(:CostumeStyle)-[:outfit_for]->(il:IllusDesign {id:n.id})
        OPTIONAL MATCH (c7:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds3:DesignSheet)-[:produces]->(il)
        OPTIONAL MATCH (il2:IllusDesign)-[:expands_to]->(st:StandingIllustration {id:n.id})
        OPTIONAL MATCH (c8:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds4:DesignSheet)-[:produces]->(il2)
        OPTIONAL MATCH (s:Scene)-[:has_layer]->(ly:SceneLayer {id:n.id})
        OPTIONAL MATCH (loc:Location)-[:has_scene]->(s)
        RETURN n.id AS id, labels(n)[0] AS label, n.name AS name, n.status AS status,
               n.image_path AS image_path, n.prompt_path AS prompt_path,
               n.variant_label AS variant_label, n.description AS description,
               n.adaptation_notes AS adaptation_notes,
               n.layer_type AS layer_type, n.prompt AS prompt,
               n.delta_notes AS delta_notes, n.active_from AS active_from, n.slug AS slug,
               coalesce(c.name, c5.name, c6.name, c7.name, c8.name, '') AS char_name,
               coalesce(s.name, '') AS scene_name,
               coalesce(loc.name, '') AS loc_name
        """,
        {"id": node_id},
    )[0]


# ── 节点产物预览（生产页融合审批用）──

def node_artifacts(repo, node_id: str) -> dict:
    """节点 → {label, name, status, kind, url, text, audio, candidates, breadcrumb}。"""
    rows = repo.run(
        "MATCH (n {id:$id}) RETURN properties(n) AS p, labels(n)[0] AS l", {"id": node_id}
    )
    if not rows:
        return {}
    p, label = rows[0]["p"], rows[0]["l"]
    out = {
        "label": label,
        "name": p.get("name") or p.get("title") or p.get("variant_label") or node_id,
        "status": p.get("status"),
        "id": node_id,
    }
    # 图类
    if label in ("DesignSheet", "IllusDesign", "StandingIllustration", "SceneLayer"):
        out["kind"] = "image"
        out["url"] = (resolve(p.get("image_path"), "image") or {}).get("url", "")
        out["path"] = p.get("image_path") or ""
        pp = resolve(p.get("prompt_path"), "text")
        out["text"] = Path(pp["abs"]).read_text(encoding="utf-8", errors="replace") if pp and pp.get("exists") else ""
    elif label == "VoiceDesign":
        out["kind"] = "voice"
        ref = resolve(p.get("ref_audio_path"), "audio")
        out["url"] = (ref or {}).get("url", "")
        out["instruct"] = p.get("instruct") or ""
        out["candidates"] = p.get("candidates_path") or ""
        cands = []
        if p.get("candidates_path"):
            ci = resolve(p["candidates_path"], "text")
            if ci and ci.get("exists"):
                try:
                    manifest = json.loads(Path(ci["abs"]).read_text(encoding="utf-8"))
                    raw = manifest.get("candidates", manifest) if isinstance(manifest, dict) else manifest
                    for item in raw:
                        rp = resolve(item.get("ref_path") or item.get("ref") or "", "audio") or {}
                        cands.append({
                            "name": item.get("name") or item.get("id", "?"),
                            "url": rp.get("url", ""),
                            "instruct": item.get("instruct", ""),
                            "audios": [
                                (resolve(a.get("path", ""), "audio") or {}).get("url", "")
                                for a in item.get("audios", item.get("emotions", []))
                            ],
                        })
                except (json.JSONDecodeError, OSError):
                    pass
        out["cands"] = cands
    elif label == "Chapter":
        out["kind"] = "brief"
        bi = resolve(p.get("brief_path"), "text")
        out["text"] = Path(bi["abs"]).read_text(encoding="utf-8", errors="replace") if bi and bi.get("exists") else ""
        out["path"] = p.get("brief_path") or ""
    else:
        out["kind"] = "text"
    return out
