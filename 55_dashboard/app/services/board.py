"""board.py — 生产看板三链查询 + 叙事图浏览。

⚠ Memgraph 表达式兼容（2026-09-29 实测）：
  - `CASE WHEN cond THEN 1 ELSE 0` 可用，但 cond 内含 `IN (-1,0)` 列表字面量会 parse 崩
    （等值 = 可用）——避免 IN + 负数列表。
  - 聚合后 ORDER BY 引用原变量会 Unbound variable——用返回别名排序。
  本文件计数统一用 collect + 列表推导（`size([x IN l WHERE ...])`），全部实测可跑。
"""

from __future__ import annotations

# ── 生产看板 ──

def char_board(repo) -> list[dict]:
    rows = repo.run(
        """
        MATCH (c:Character)
        OPTIONAL MATCH (c)-[:has_appearance]->(ap:AppearanceStyle)
        OPTIONAL MATCH (c)-[:has_voice_style]->(ls:LanguageStyle)
        OPTIONAL MATCH (c)-[:has_voice_design]->(vd:VoiceDesign)
        RETURN c.id AS id, c.name AS name, c.priority AS prio,
               ap.status AS ap_st, ls.status AS ls_st, vd.status AS vd_st,
               vd.candidates_path AS vd_cand
        ORDER BY c.name
        """
    )
    costumes = {
        r["cid"]: r
        for r in repo.run(
            """
            MATCH (c:Character)-[:has_costume]->(co:CostumeStyle)
            WITH c.id AS cid, collect(co.status) AS sts
            RETURN cid, sts, size(sts) AS n, size([x IN sts WHERE x = -1 OR x = 0]) AS n_todo
            """
        )
    }
    # 三条独立查询（每层各自 collect，避免 ds×il×st 笛卡尔积；
    # 计数放 Cypher 侧：n = size(非null)，todo/review = 列表推导）
    ds_map = {
        r["cid"]: r
        for r in repo.run(
            """
            MATCH (c:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds:DesignSheet)
            WITH c.id AS cid, collect(ds.status) AS sts
            RETURN cid, sts, size(sts) AS n,
                   size([x IN sts WHERE x = -1 OR x = 0]) AS todo,
                   size([x IN sts WHERE x = 10]) AS review
            """
        )
    }
    il_map = {
        r["cid"]: r
        for r in repo.run(
            """
            MATCH (c:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(:DesignSheet)-[:produces]->(il:IllusDesign)
            WITH c.id AS cid, collect(il.status) AS sts
            RETURN cid, sts, size(sts) AS n,
                   size([x IN sts WHERE x = -1 OR x = 0]) AS todo,
                   size([x IN sts WHERE x = 10]) AS review
            """
        )
    }
    st_map = {
        r["cid"]: r
        for r in repo.run(
            """
            MATCH (c:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(:DesignSheet)-[:produces]->(:IllusDesign)-[:expands_to]->(st:StandingIllustration)
            WITH c.id AS cid, collect(st.status) AS sts
            RETURN cid, sts, size(sts) AS n,
                   size([x IN sts WHERE x = -1 OR x = 0]) AS todo,
                   size([x IN sts WHERE x = 10]) AS review
            """
        )
    }

    def merge_counts(*maps):
        return {
            "n": sum(m.get("n", 0) for m in maps),
            "todo": sum(m.get("todo", 0) for m in maps),
            "review": sum(m.get("review", 0) for m in maps),
        }

    # 产物明细（每角色：设计图 → [立绘设计(带着装)]；立绘挂在立绘设计下）
    detail = repo.run(
        """
        MATCH (c:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds:DesignSheet)
        OPTIONAL MATCH (ds)-[:produces]->(il:IllusDesign)
        OPTIONAL MATCH (c2:Character)-[:has_costume]->(co)-[:outfit_for]->(il)
        WITH c.id AS cid, ds {.id, .status, .image_path} AS ds,
             collect(DISTINCT il {.id, .status, .image_path, outfit: co.name}) AS ils
        RETURN cid, ds, ils
        """
    )
    stand_rows = repo.run(
        """
        MATCH (c:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(:DesignSheet)
              -[:produces]->(il:IllusDesign)-[:expands_to]->(st:StandingIllustration)
        WITH c.id AS cid, il.id AS iid, collect(st {.id, .status, .image_path, variant: st.variant_label}) AS sts
        RETURN cid, iid, sts
        """
    )
    stands_by_il = {}
    for r in stand_rows:
        stands_by_il.setdefault(r["cid"], {}).setdefault(r["iid"], []).extend(r["sts"])
    detail_map: dict[str, list] = {}
    for r in detail:
        cid = r["cid"]
        ils = []
        for il in r["ils"]:
            if not il.get("id"):
                continue
            il["stands"] = stands_by_il.get(cid, {}).get(il["id"], [])
            ils.append(il)
        detail_map.setdefault(cid, []).append({**r["ds"], "ils": ils})

    out = []
    for r in rows:
        cid = r["id"]
        co = costumes.get(cid)
        ds_c = merge_counts(ds_map.get(cid, {}))
        il_c = merge_counts(il_map.get(cid, {}))
        st_c = merge_counts(st_map.get(cid, {}))
        out.append({
            **r,
            "co_n": co["n"] if co else 0,
            "co_todo": co["n_todo"] if co else 0,
            "n_ds": ds_c["n"], "ds_todo": ds_c["todo"], "ds_review": ds_c["review"],
            "n_il": il_c["n"], "il_todo": il_c["todo"], "il_review": il_c["review"],
            "n_st": st_c["n"], "st_todo": st_c["todo"], "st_review": st_c["review"],
            "artifacts": detail_map.get(cid, []),
        })
    # 排序：优先级（P0 前）+ 名称；priority 可能是 None
    pri = {"P0": 0, "P1": 1, "P2": 2}
    out.sort(key=lambda r: (pri.get(r["prio"] or "", 9), r["name"]))
    return out


def scene_board(repo) -> list[dict]:
    locs = repo.run(
        """
        MATCH (l:Location)
        OPTIONAL MATCH (l)-[:has_scene]->(s:Scene)
        WITH l, s ORDER BY s.name
        RETURN l.id AS id, l.name AS name, collect(s { .id, .name, .status }) AS scenes
        """
    )
    scene_meta = {
        r["sid"]: r
        for r in repo.run(
            """
            MATCH (s:Scene)
            OPTIONAL MATCH (s)-[:has_layer]->(ly:SceneLayer)
            OPTIONAL MATCH (s)-[:has_bgm]->(b:BgmTrack)
            WITH s.id AS sid, collect(ly.status) AS ly_sts, b.name AS bgm_name, b.status AS bgm_st,
                 collect(ly {.id, .status, .image_path, .layer_type}) AS lys
            RETURN sid, ly_sts, bgm_name, bgm_st, lys,
                   size([x IN ly_sts WHERE x = -1 OR x = 0]) AS ly_todo,
                   size([x IN ly_sts WHERE x = 10]) AS ly_review
            """
        )
    }
    out = []
    for l in locs:
        scenes = []
        for s in l["scenes"]:
            m = scene_meta.get(s["id"], {})
            sts = m.get("ly_sts", [])
            lys = [ly for ly in (m.get("lys") or []) if ly.get("id")]
            scenes.append({
                **s,
                "n_ly": len(sts), "ly_todo": m.get("ly_todo", 0),
                "ly_review": m.get("ly_review", 0),
                "bgm_name": m.get("bgm_name"), "bgm_st": m.get("bgm_st"),
                "layers": lys,
            })
        out.append({**l, "scenes": scenes})
    return out


def plot_board(repo) -> dict:
    chapters = repo.run(
        """
        MATCH (ch:Chapter)
        OPTIONAL MATCH (ch)-[:has_section]->(sec:Section)
        WITH ch, sec ORDER BY sec.section_no
        RETURN ch.id AS id, ch.title AS title, ch.chapter_no AS no, ch.status AS status,
               collect(sec { .id, .title, .section_no, .summary }) AS secs
        ORDER BY no
        """
    )
    sec_stats = {
        r["sid"]: r
        for r in repo.run(
            """
            MATCH (sec:Section)
            OPTIONAL MATCH (sec)-[:has_outline]->(so:SecOutline)
            OPTIONAL MATCH (so)-[:produces]->(sc:SecScript)
            OPTIONAL MATCH (sc)-[:produces]->(l:LineAudio)
            WITH sec.id AS sid, so.status AS ol_st, sc.status AS sc_st, sc.id AS sc_id,
                 collect(l.status) AS lsts
            RETURN sid, ol_st, sc_st, sc_id, lsts,
                   size(lsts) AS n_line, size([x IN lsts WHERE x = 11]) AS n_ok
            """
        )
    }
    ch_out = []
    for ch in chapters:
        secs = []
        for s in ch["secs"]:
            m = sec_stats.get(s["id"], {})
            secs.append({
                **s,
                "ol_st": m.get("ol_st"), "sc_st": m.get("sc_st"), "sc_id": m.get("sc_id"),
                "n_line": m.get("n_line", 0), "n_ok": m.get("n_ok", 0),
            })
        ch_out.append({**ch, "secs": secs})
    stand_gaps = repo.run(
        """
        MATCH (sc:Scene)-[:depicts]->(il:IllusDesign)-[:expands_to]->(stand:StandingIllustration)
        WHERE stand.status <> 11
        RETURN stand.id AS id, stand.variant_label AS label, stand.status AS st,
               stand.description AS descr, il.id AS il_id, sc.name AS scene_name
        ORDER BY stand.status, scene_name
        """
    )
    return {"chapters": ch_out, "stand_gaps": stand_gaps}


# ── 叙事图浏览 ──

LABEL_NAME_FIELD = {
    "Character": "name", "Event": "title", "Location": "name",
    "Info": "title", "Choice": "name",
}


def search_entities(repo, label: str, q_text: str, limit: int = 50) -> list[dict]:
    field = LABEL_NAME_FIELD.get(label, "name")
    return repo.run(
        f"""
        MATCH (n:{label})
        WHERE n.{field} CONTAINS $q OR (n.description IS NOT NULL AND n.description CONTAINS $q)
           OR (n.content IS NOT NULL AND n.content CONTAINS $q)
        RETURN n.id AS id, n.{field} AS name, coalesce(n.description, n.content, '') AS desc,
               labels(n)[0] AS label
        ORDER BY name LIMIT $limit
        """,
        {"q": q_text, "limit": limit},
    )


def entity_detail(repo, label: str, node_id: str) -> dict | None:
    field = LABEL_NAME_FIELD.get(label, "name")
    rows = repo.run(
        f"""
        MATCH (n:{label} {{id: $id}})
        RETURN n.id AS id, labels(n)[0] AS label, n.{field} AS name, properties(n) AS props
        """,
        {"id": node_id},
    )
    if not rows:
        return None
    d = rows[0]
    out_edges = repo.run(
        """
        MATCH (a {id:$id})-[r]->(b)
        RETURN type(r) AS type, b.id AS bid, labels(b)[0] AS blabel,
               coalesce(b.name, b.title, b.id) AS bname, properties(r) AS rprops
        """,
        {"id": node_id},
    )
    in_edges = repo.run(
        """
        MATCH (a)-[r]->(b {id:$id})
        RETURN type(r) AS type, a.id AS aid, labels(a)[0] AS alabel,
               coalesce(a.name, a.title, a.id) AS aname, properties(r) AS rprops
        """,
        {"id": node_id},
    )
    return {**d, "out_edges": out_edges, "in_edges": in_edges}


def subgraph_around(repo, node_id: str, max_hops: int = 2, node_cap: int = 80) -> dict:
    """实体 ±hops 局部子图（ECharts 数据）。手写 BFS，不依赖 MAGE。"""
    visited: dict[str, dict] = {node_id: {}}
    edges: list[dict] = []
    frontier = {node_id}
    for _hop in range(max_hops):
        if not frontier or len(visited) >= node_cap:
            break
        flist = list(frontier)[:40]
        found = repo.run(
            """
            UNWIND $ids AS x
            MATCH (a {id:x})-[r]-(b)
            RETURN a.id AS aid, b.id AS bid, type(r) AS type,
                   labels(a)[0] AS alabel, labels(b)[0] AS blabel,
                   coalesce(a.name, a.title, a.id) AS aname,
                   coalesce(b.name, b.title, b.id) AS bname
            """,
            {"ids": flist},
        )
        next_frontier: set[str] = set()
        for e in found:
            for nid, lb, nm in ((e["aid"], e["alabel"], e["aname"]), (e["bid"], e["blabel"], e["bname"])):
                if nid not in visited and len(visited) < node_cap:
                    visited[nid] = {"id": nid, "label": lb, "name": nm}
            edges.append({"source": e["aid"], "target": e["bid"], "type": e["type"]})
            next_frontier.add(e["aid"])
            next_frontier.add(e["bid"])
        frontier = next_frontier - set(visited)
    # 起点/终点补名（起点的 name 由调用方覆盖）
    seen = set()
    uniq = []
    for e in edges:
        k = (e["source"], e["target"], e["type"])
        if k in seen:
            continue
        seen.add(k)
        if e["source"] in visited and e["target"] in visited:
            uniq.append(e)
    nodes = [{"id": k, "label": v.get("label", ""), "name": v.get("name", "")} for k, v in visited.items()]
    return {"nodes": nodes, "links": uniq, "truncated": len(visited) >= node_cap}


# ── 角色美术子图（分层取数，边由层级重构）──

def char_art_graph(repo, char_id: str) -> dict:
    """角色 → 数据节点 → DesignSheet(版本) → IllusDesign → StandingIllustration 全链。"""
    head = repo.run(
        "MATCH (c:Character {id:$id}) RETURN c.id AS id, c.name AS name, c.priority AS prio",
        {"id": char_id},
    )
    if not head:
        return {}
    h = head[0]
    nodes: dict[str, dict] = {
        h["id"]: {"id": h["id"], "label": "Character", "name": h["name"], "status": None, "depth": 0}
    }
    edges: list[dict] = []
    seen_edges: set[tuple] = set()

    def add_edge(src, dst, t):
        k = (src, dst, t)
        if k not in seen_edges:
            seen_edges.add(k)
            edges.append({"source": src, "target": dst, "type": t})

    def add_node(nid, label, name, status, depth):
        if nid:
            nodes.setdefault(
                nid, {"id": nid, "label": label, "name": name or nid, "status": status, "depth": depth}
            )

    for r in repo.run(
        """
        MATCH (c:Character {id:$id})-[r:has_appearance|has_costume|has_voice_style|has_voice_design]->(m)
        RETURN type(r) AS t, c.id AS src, m.id AS dst, labels(m)[0] AS lb,
               coalesce(m.name, m.variant_label, '') AS nm, m.status AS st
        """,
        {"id": char_id},
    ):
        add_node(r["dst"], r["lb"], r["nm"], r["st"], 1)
        add_edge(r["src"], r["dst"], r["t"])
    for r in repo.run(
        """
        MATCH (:Character {id:$id})-[:has_appearance]->(a:AppearanceStyle)-[r:produces]->(ds)
        RETURN a.id AS src, ds.id AS dst, labels(ds)[0] AS lb,
               coalesce(ds.slug, ds.delta_notes, '') AS nm, ds.status AS st
        """,
        {"id": char_id},
    ):
        add_node(r["dst"], r["lb"], "设计图" + (f"·{r['nm']}" if r["nm"] else ""), r["st"], 2)
        add_edge(r["src"], r["dst"], "produces")
    for r in repo.run(
        """
        MATCH (:Character {id:$id})-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds)-[r:produces]->(il)
        RETURN ds.id AS src, il.id AS dst, il.status AS st
        """,
        {"id": char_id},
    ):
        add_node(r["dst"], "IllusDesign", r["dst"], r["st"], 3)
        add_edge(r["src"], r["dst"], "produces")
    for r in repo.run(
        """
        MATCH (:Character {id:$id})-[:has_costume]->(co)-[r:outfit_for]->(il)
        RETURN co.id AS src, il.id AS dst, co.name AS via, il.status AS st
        """,
        {"id": char_id},
    ):
        add_node(r["dst"], "IllusDesign", r["dst"], r["st"], 3)
        if nodes.get(r["dst"]):
            nodes[r["dst"]]["via"] = r["via"]
        add_edge(r["src"], r["dst"], "outfit_for")
    for r in repo.run(
        """
        MATCH (:Character {id:$id})-[:has_appearance]->(:AppearanceStyle)-[:produces]->(:DesignSheet)
              -[:produces]->(il)-[r:expands_to]->(st)
        RETURN il.id AS src, st.id AS dst, st.variant_label AS nm, st.status AS st2
        """,
        {"id": char_id},
    ):
        add_node(r["dst"], "StandingIllustration", r["nm"], r["st2"], 4)
        add_edge(r["src"], r["dst"], "expands_to")
    # IllusDesign 显示名：着装名
    for nid, n in nodes.items():
        if n["label"] == "IllusDesign" and n.get("via"):
            n["name"] = n["via"]
    return {"nodes": list(nodes.values()), "links": edges}


# ── 角色 tab 左栏：P0~P2 分组列表（状态简述+待办）──

def char_groups(repo) -> list[dict]:
    """按 priority 分组的角色摘要（供左栏折叠列表）。"""
    rows = repo.run(
        """
        MATCH (c:Character)
        OPTIONAL MATCH (c)-[:has_appearance]->(ap:AppearanceStyle)
        OPTIONAL MATCH (c)-[:has_voice_style]->(ls:LanguageStyle)
        OPTIONAL MATCH (c)-[:has_voice_design]->(vd:VoiceDesign)
        RETURN c.id AS id, c.name AS name, c.priority AS prio,
               ap.status AS ap_st, ls.status AS ls_st, vd.status AS vd_st,
               vd.candidates_path AS vd_cand
        ORDER BY c.name
        """
    )
    co = {
        r["cid"]: r
        for r in repo.run(
            """
            MATCH (c:Character)-[:has_costume]->(x)
            WITH c.id AS cid, collect(x.status) AS sts
            RETURN cid, sts, size([s IN sts WHERE s = -1 OR s = 0]) AS todo
            """
        )
    }
    prod = {
        r["cid"]: r
        for r in repo.run(
            """
            MATCH (c:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(:DesignSheet)
                  -[:produces]->(:IllusDesign)-[:expands_to]->(st)
            WITH c.id AS cid, collect(st.status) AS sts
            RETURN cid, size([s IN sts WHERE s = 11]) AS ok, size(sts) AS total
            """
        )
    }
    out = []
    for r in rows:
        cid = r["id"]
        c_ = co.get(cid)
        p_ = prod.get(cid)
        todos = []
        if r["ap_st"] in (None, -1, 0):
            todos.append("外貌")
        if r["ls_st"] in (None, -1, 0):
            todos.append("语言")
        if c_ and c_["todo"]:
            todos.append(f"着装×{c_['todo']}")
        if r["vd_st"] in (None, -1, 0):
            todos.append("声音")
        elif r["vd_st"] == 10:
            todos.append("声音待审" + ("（候选）" if r["vd_cand"] else ""))
        if p_ and p_["ok"] < p_["total"]:
            todos.append(f"立绘 {p_['ok']}/{p_['total']}")
        brief = "链就绪" if not todos else "待办: " + "、".join(todos[:4])
        out.append({
            **r, "brief": brief, "n_todo": len(todos),
            "st_ok": 0 if todos else 1,
        })
    groups: dict[str, list] = {}
    for r in out:
        groups.setdefault(r["prio"] or "未分级", []).append(r)
    return [
        {"prio": k, "chars": v, "n_todo": sum(x["n_todo"] for x in v)}
        for k, v in sorted(groups.items())
    ]


# ── 场景 tab 三栏支撑 ──

def scene_groups(repo) -> list[dict]:
    """地点分组列表：完成度分组（未就绪在前），每地点状态简述。"""
    locs = repo.run(
        """
        MATCH (l:Location)
        OPTIONAL MATCH (l)-[:has_scene]->(s:Scene)
        WITH l, s ORDER BY s.name
        RETURN l.id AS id, l.name AS name, collect(s { .id, .name, .status }) AS scenes
        """
    )
    meta = {
        r["sid"]: r
        for r in repo.run(
            """
            MATCH (s:Scene)
            OPTIONAL MATCH (s)-[:has_layer]->(ly)
            OPTIONAL MATCH (s)-[:has_bgm]->(bg)
            WITH s.id AS sid, collect(ly.status) AS sts, bg.name AS bn, bg.status AS bs,
                 collect(ly {.id, .status, .image_path, .layer_type}) AS lys
            RETURN sid, sts, bn, bs, lys,
                   size([x IN sts WHERE x = -1 OR x = 0]) AS todo,
                   size([x IN sts WHERE x = 10]) AS review
            """
        )
    }
    out = []
    for l in locs:
        todos = []
        n_ly = n_ok = 0
        n_scenes = len(l["scenes"])
        for s in l["scenes"]:
            m = meta.get(s["id"], {})
            sts = m.get("sts", [])
            n_ly += len(sts)
            n_ok += sum(1 for x in sts if x == 11)
            if s.get("status") in (-1, 0, None):
                todos.append(f"{s['name']}(场景未建)")
            if m.get("todo"):
                todos.append(f"{s['name']} 图层×{m['todo']}")
            if m.get("review"):
                todos.append(f"{s['name']} 图层待审×{m['review']}")
            if m.get("bs") == 1:
                todos.append(f"{m['bn']} BGM等wav")
            elif m.get("bs") in (-1, 0, None) and m.get("bs") is not None:
                todos.append(f"{m['bn']} BGM未做")
        # ⚠ 空地点 ≠ 就绪：无 Scene = 未开工（需 scene-designer 切场景）
        if n_scenes == 0:
            brief = "未建场景（0 个 Scene）"
            todos.append("未建场景")
        else:
            brief = "链就绪" if not todos else "待办: " + "、".join(todos[:3]) + ("…" if len(todos) > 3 else "")
        out.append({
            "id": l["id"], "name": l["name"], "n_todo": len(todos),
            "brief": brief, "n_ly": n_ly, "n_ok": n_ok, "n_scenes": n_scenes,
        })
    done = [x for x in out if x["n_todo"] == 0]
    todo = [x for x in out if x["n_todo"] > 0]
    return [
        {"prio": "待处理", "chars": todo},
        {"prio": "就绪", "chars": done},
    ]


def scene_art_graph(repo, loc_id: str) -> dict:
    """地点 → Scene → SceneLayer / BgmTrack 树。"""
    head = repo.run(
        "MATCH (l:Location {id:$id}) RETURN l.id AS id, l.name AS name", {"id": loc_id}
    )
    if not head:
        return {}
    h = head[0]
    nodes = {h["id"]: {"id": h["id"], "label": "Location", "name": h["name"], "status": None, "depth": 0}}
    edges: list[dict] = []
    seen: set[tuple] = set()

    def add_edge(src, dst, t):
        k = (src, dst, t)
        if k not in seen:
            seen.add(k)
            edges.append({"source": src, "target": dst, "type": t})

    for r in repo.run(
        """
        MATCH (l:Location {id:$id})-[:has_scene]->(s)
        RETURN s.id AS sid, s.name AS nm, s.status AS st, s.scene_type AS typ, s.time_of_day AS tod
        """,
        {"id": loc_id},
    ):
        nm = r["nm"] + (f"（{r['tod']}）" if r.get("tod") else "")
        nodes[r["sid"]] = {"id": r["sid"], "label": "Scene", "name": nm, "status": r["st"], "depth": 1}
        add_edge(h["id"], r["sid"], "has_scene")
        for ly in repo.run(
            """
            MATCH (s:Scene {id:$sid})-[:has_layer]->(ly)
            RETURN ly.id AS id, ly.layer_type AS typ, ly.status AS st
            """,
            {"sid": r["sid"]},
        ):
            nodes[ly["id"]] = {
                "id": ly["id"], "label": "SceneLayer",
                "name": f"{ly['typ']}", "status": ly["st"], "depth": 2,
            }
            add_edge(r["sid"], ly["id"], "has_layer")
        for bg in repo.run(
            """
            MATCH (s:Scene {id:$sid})-[:has_bgm]->(bg)
            RETURN bg.id AS id, bg.name AS nm, bg.status AS st
            """,
            {"sid": r["sid"]},
        ):
            nodes[bg["id"]] = {
                "id": bg["id"], "label": "BgmTrack", "name": f"BGM·{bg['nm']}",
                "status": bg["st"], "depth": 2,
            }
            add_edge(r["sid"], bg["id"], "has_bgm")
    return {"nodes": list(nodes.values()), "links": edges}
