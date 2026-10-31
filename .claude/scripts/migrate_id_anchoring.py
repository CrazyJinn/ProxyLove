"""一次性迁移：产物目录从节点 name 锚定 → 雪花 id 锚定（六域 + 行键 + 脏数据）。

设计要点（实施计划见 plans/giggly-waddling-blossom.md §五）：
- 盘先图后：盘 rename 三态可重入（旧在→MOVE / 新在旧无→SKIP(exists) / 皆无→MISSING），
  图 SET 幂等可重放；中途崩溃后重跑两个方向都收敛。
- 15_声音 旧 wav 定位不解析键语义：用图上尚未覆写的旧键值 rsplit('-',3) 直算旧位置
  （存量键 block 段为旧短名快照，与行属性 scene_block_id 不一致属预期）。
- 全程审计 plan.json（00_init/.migration_plan_<日期>.json）：图 SET/REMOVE 与盘 FS_MOVE
  均记 old/new，--rollback 依此反向执行。
- Section.scene_blocks 的 REMOVE 不在本脚本（generate_portrait_map 改造前删会断发布链，
  阶段②改完代码后单独执行）。

用法（项目根）：
  python .claude/scripts/migrate_id_anchoring.py --dry-run              # 全域计划
  python .claude/scripts/migrate_id_anchoring.py --domain 06            # 单域执行
  python .claude/scripts/migrate_id_anchoring.py --domain all           # 全域执行
  python .claude/scripts/migrate_id_anchoring.py --verify               # 迁移后断言
  python .claude/scripts/migrate_id_anchoring.py --rollback <plan.json>
"""

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snowflake_base62 import to_hexid  # noqa: E402  文件名/键安全形态

_ROOT = Path(__file__).resolve().parents[2]
_CYPHER_EXEC = _ROOT / ".claude" / "scripts" / "cypher_exec.py"
PLAN_PATH = _ROOT / "00_init" / f".migration_plan_{date.today():%Y-%m-%d}.json"

DOMAINS = ("06", "07", "13", "14", "15", "25", "dirty")
DIR_06 = _ROOT / "06_角色美术"
DIR_07 = _ROOT / "07_场景美术"
DIR_13 = _ROOT / "13_BGM"
DIR_14 = _ROOT / "14_声音设计"
DIR_15 = _ROOT / "15_声音"
DIR_25 = _ROOT / "25_剧本"


# ---------------------------------------------------------------- 图访问

def run_cypher(cypher: str) -> list:
    proc = subprocess.run(
        [sys.executable, str(_CYPHER_EXEC), "-c", cypher, "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    out = proc.stdout
    start, end = out.find("["), out.rfind("]")
    if start == -1 or end == -1:
        raise RuntimeError(f"cypher_exec 无 JSON 输出:\n{out}\n{proc.stderr}")
    return json.loads(out[start:end + 1])


def run_write(statements: list) -> None:
    """多语句写图。语句以 ; 分隔——cypher_exec --multi 按 ; 切分为独立语句单事务
    顺序执行；若仅换行分隔，多条 MATCH...SET 会被拼接为单条查询（变量复用导致
    后续 MATCH 退化为过滤条件，仅首条生效且退出码为 0，静默丢失）。"""
    if not statements:
        return
    proc = subprocess.run(
        [sys.executable, str(_CYPHER_EXEC), "--stdin", "--multi"],
        input=";\n".join(statements), capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"写图失败（退出码 {proc.returncode}）:\n{proc.stderr}\n{proc.stdout}")
    if "发生错误" in proc.stdout or "Error" in proc.stdout:
        raise RuntimeError(f"写图可能失败:\n{proc.stdout[-2000:]}")


def q(s: str) -> str:
    """Cypher 单引号字符串转义。"""
    return "'" + str(s).replace("\\", "\\\\").replace("'", "\\'") + "'"


# ---------------------------------------------------------------- 迁移器

class Migrator:
    def __init__(self, dry_run: bool):
        self.dry = dry_run
        self.plan = []      # 审计：图 SET/REMOVE + 盘 FS_MOVE
        self.skip = []      # SKIP(exists)
        self.missing = []   # 盘旧位置缺失（图仍写新值，verify 兜底）
        self.statements = []  # 本域 Cypher 写语句累积

    # ---- 盘 ----
    def fs_move(self, old: Path, new: Path, domain: str, note: str = "") -> str:
        rel_old, rel_new = old.relative_to(_ROOT), new.relative_to(_ROOT)
        if new.exists() and not old.exists():
            self.skip.append(f"SKIP(exists): {rel_old} -> {rel_new}")
            return "skip"
        if not old.exists():
            self.missing.append(f"MISSING: {rel_old} ({note or '期望旧位置不存在'})")
            return "missing"
        if new.exists():  # 旧新都在：冗余副本，不动旧文件（NTFS case-fold 撞名也会走到这）
            self.missing.append(f"CONFLICT(双侧都在): {rel_old} vs {rel_new}")
            return "conflict"
        if not self.dry:
            new.parent.mkdir(parents=True, exist_ok=True)
            old.rename(new)
        self.plan.append({"domain": domain, "op": "FS_MOVE", "old": str(rel_old), "new": str(rel_new)})
        print(f"MOVE: {rel_old} -> {rel_new}")
        return "moved"

    def fs_move_dir(self, old: Path, new: Path, domain: str) -> str:
        """父目录整挪（内容随迁），新目录已存在则拒绝（避免合并语义不明）。"""
        rel_old, rel_new = old.relative_to(_ROOT), new.relative_to(_ROOT)
        if new.exists() and not old.exists():
            self.skip.append(f"SKIP(exists): {rel_old} -> {rel_new}")
            return "skip"
        if not old.exists():
            self.missing.append(f"MISSING: {rel_old}")
            return "missing"
        if new.exists():
            self.missing.append(f"CONFLICT(双侧都在): {rel_old} vs {rel_new}")
            return "missing"
        if not self.dry:
            new.parent.mkdir(parents=True, exist_ok=True)
            old.rename(new)
        self.plan.append({"domain": domain, "op": "FS_MOVE", "old": str(rel_old), "new": str(rel_new)})
        print(f"MOVEDIR: {rel_old} -> {rel_new}")
        return "moved"

    def sweep_empty(self, base: Path, keep_top: bool = True) -> None:
        """迁移后自底向上删空目录（不删任何文件；keep_top=True 保留域根目录本身）。"""
        if not base.exists():
            return
        dirs = [d for d in base.rglob("*") if d.is_dir()]
        for d in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
            try:
                next(d.iterdir())
            except StopIteration:
                if not self.dry:
                    d.rmdir()
                print(f"RMDIR(空): {d.relative_to(_ROOT)}")
        if not keep_top:
            try:
                next(base.iterdir())
            except StopIteration:
                if not self.dry:
                    base.rmdir()
                print(f"RMDIR(空): {base.relative_to(_ROOT)}")

    # ---- 图 ----
    def set_prop(self, node_id: str, label: str, prop: str, old, new, domain: str,
                 literal: str | None = None, detail: list | None = None) -> None:
        """记审计 + 生成 SET 语句。literal 为完整自定义 SET 子句（批量 UNWIND 用），
        detail 为批量语句的逐行 [{node,prop,old,new}]（回滚凭据）。"""
        entry = {"domain": domain, "op": "SET", "node": node_id, "label": label,
                 "prop": prop, "old": old, "new": new}
        if detail:
            entry["detail"] = detail
        self.plan.append(entry)
        if literal:
            self.statements.append(literal)

    def flush_graph(self, batch_size: int = 1) -> None:
        """执行累积的写语句（statements 由调用方控制粒度：单条 SET 或批量 UNWIND）。"""
        if self.dry:
            print(f"[dry-run] 图写语句 {len(self.statements)} 条未执行")
            self.statements = []
            return
        # UNWIND 批量语句可能很长，按条直接提交（--multi 单事务顺序执行，条数即语句数）
        for i in range(0, len(self.statements), 100):
            run_write(self.statements[i:i + 100])
        print(f"[graph] 已提交 {len(self.statements)} 条语句")
        self.statements = []

    def save_plan(self) -> None:
        if self.dry:
            return
        existing = []
        if PLAN_PATH.exists():
            existing = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        existing.extend(self.plan)
        PLAN_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[plan] 审计已追加 {PLAN_PATH.name}（累计 {len(existing)} 条）")


# ---------------------------------------------------------------- 域 06 角色美术

def domain_06(m: Migrator) -> None:
    print("\n===== 域 06_角色美术 =====")

    # DesignSheet：06/<char_id>/<ds_id>/{prompt.md,设计图.png}
    rows = run_cypher(
        "MATCH (c:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds:DesignSheet) "
        "RETURN c.id AS cid, c.name AS cname, ds.id AS dsid, ds.prompt_path AS prompt_path, ds.image_path AS image_path LIMIT 100"
    )
    for r in rows:
        ds_dir = f"06_角色美术/{to_hexid(r['cid'])}/{to_hexid(r['dsid'])}"
        for prop, fname in (("prompt_path", "prompt.md"), ("image_path", "设计图.png")):
            old_val = r[prop]
            if old_val is None:
                continue
            new_val = f"{ds_dir}/{fname}"
            m.fs_move(_ROOT / old_val, _ROOT / new_val, "06", f"DS {r['dsid']}.{prop}")
            m.set_prop(r["dsid"], "DesignSheet", prop, old_val, new_val, "06",
                       f"MATCH (n:DesignSheet {{id:{q(r['dsid'])}}}) SET n.{prop} = {q(new_val)}")

    # IllusDesign：06/<char_id>/<ds_id>/<cos_id>/{prompt.md,立绘设计图.png}
    rows = run_cypher(
        "MATCH (c:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds:DesignSheet)"
        "-[:produces]->(i:IllusDesign)<-[:outfit_for]-(cs:CostumeStyle) "
        "RETURN c.id AS cid, ds.id AS dsid, cs.id AS cosid, i.id AS iid, i.prompt_path AS prompt_path, i.image_path AS image_path LIMIT 200"
    )
    for r in rows:
        ill_dir = f"06_角色美术/{to_hexid(r['cid'])}/{to_hexid(r['dsid'])}/{to_hexid(r['cosid'])}"
        for prop, fname in (("prompt_path", "prompt.md"), ("image_path", "立绘设计图.png")):
            old_val = r[prop]
            if old_val is None:
                continue
            new_val = f"{ill_dir}/{fname}"
            m.fs_move(_ROOT / old_val, _ROOT / new_val, "06", f"Illus {r['iid']}.{prop}")
            m.set_prop(r["iid"], "IllusDesign", prop, old_val, new_val, "06",
                       f"MATCH (n:IllusDesign {{id:{q(r['iid'])}}}) SET n.{prop} = {q(new_val)}")

    # StandingIllustration：…/立绘/<stand_id>.{md,png}
    rows = run_cypher(
        "MATCH (c:Character)-[:has_appearance]->(:AppearanceStyle)-[:produces]->(ds:DesignSheet)"
        "-[:produces]->(i:IllusDesign)<-[:outfit_for]-(cs:CostumeStyle), "
        "(i:IllusDesign)-[:expands_to]->(st:StandingIllustration) "
        "RETURN c.id AS cid, ds.id AS dsid, cs.id AS cosid, st.id AS stid, st.prompt_path AS prompt_path, st.image_path AS image_path LIMIT 300"
    )
    for r in rows:
        stand_dir = f"06_角色美术/{to_hexid(r['cid'])}/{to_hexid(r['dsid'])}/{to_hexid(r['cosid'])}/立绘"
        for prop, ext in (("prompt_path", "md"), ("image_path", "png")):
            old_val = r[prop]
            if old_val is None:
                continue
            new_val = f"{stand_dir}/{r['stid']}.{ext}"
            m.fs_move(_ROOT / old_val, _ROOT / new_val, "06", f"Stand {r['stid']}.{prop}")
            m.set_prop(r["stid"], "StandingIllustration", prop, old_val, new_val, "06",
                       f"MATCH (n:StandingIllustration {{id:{q(r['stid'])}}}) SET n.{prop} = {q(new_val)}")

    # 参考图（无图属性，盘探测旧 name 目录）→ 06/<char_id>/参考图.<ext> + 回填 ref_image_path
    chars = run_cypher("MATCH (c:Character) RETURN c.id AS cid, c.name AS name LIMIT 100")
    for c in chars:
        for ext in ("png", "jpg", "jpeg"):
            old = DIR_06 / c["name"] / f"参考图.{ext}"
            if old.exists():
                new_val = f"06_角色美术/{to_hexid(c['cid'])}/参考图.{ext}"
                m.fs_move(old, _ROOT / new_val, "06", f"{c['name']} 参考图")
                m.set_prop(c["cid"], "Character", "ref_image_path", None, new_val, "06",
                           f"MATCH (n:Character {{id:{q(c['cid'])}}}) SET n.ref_image_path = {q(new_val)}")
                break

    m.sweep_empty(DIR_06)
    m.flush_graph()
    m.save_plan()


# ---------------------------------------------------------------- 域 07 场景美术

def domain_07(m: Migrator) -> None:
    print("\n===== 域 07_场景美术 =====")

    rows = run_cypher(
        "MATCH (loc:Location)-[:part_of]->(sp:Spot) WHERE sp.dsl_path IS NOT NULL "
        "RETURN loc.id AS lid, sp.id AS sid, sp.dsl_path AS dsl_path LIMIT 100"
    )
    for r in rows:
        new_val = f"07_场景美术/{to_hexid(r['lid'])}/{to_hexid(r['sid'])}/{to_hexid(r['sid'])}.yml"
        m.fs_move(_ROOT / r["dsl_path"], _ROOT / new_val, "07", f"Spot {r['sid']}.dsl_path")
        m.set_prop(r["sid"], "Spot", "dsl_path", r["dsl_path"], new_val, "07",
                   f"MATCH (n:Spot {{id:{q(r['sid'])}}}) SET n.dsl_path = {q(new_val)}")

    rows = run_cypher(
        "MATCH (loc:Location)-[:part_of]->(sp:Spot)-[:realizes]->(scn:Scene)"
        "-[:has_layer]->(l:SceneLayer) "
        "RETURN loc.id AS lid, sp.id AS sid, scn.id AS scnid, l.layer_type AS lt, "
        "l.id AS llid, l.prompt_path AS prompt_path, l.image_path AS image_path LIMIT 100"
    )
    for r in rows:
        layer_dir = f"07_场景美术/{to_hexid(r['lid'])}/{to_hexid(r['sid'])}/{to_hexid(r['scnid'])}/{r['lt']}"
        for prop, fname in (("prompt_path", "prompt.md"), ("image_path", f"{r['lt']}.png")):
            old_val = r[prop]
            if old_val is None:
                continue
            new_val = f"{layer_dir}/{fname}"
            m.fs_move(_ROOT / old_val, _ROOT / new_val, "07", f"Layer {r['llid']}.{prop}")
            m.set_prop(r["llid"], "SceneLayer", prop, old_val, new_val, "07",
                       f"MATCH (n:SceneLayer {{id:{q(r['llid'])}}}) SET n.{prop} = {q(new_val)}")

    # 只清各 Location 旧目录下的空壳（07 根下脚本/存档不动）
    if DIR_07.exists():
        for d in sorted(DIR_07.iterdir()):
            if d.is_dir():
                m.sweep_empty(d, keep_top=False)

    m.flush_graph()
    m.save_plan()


# ---------------------------------------------------------------- 域 13 BGM

def domain_13(m: Migrator) -> None:
    print("\n===== 域 13_BGM =====")

    rows = run_cypher(
        "MATCH (b:BgmTrack) RETURN b.id AS bid, b.name AS name, b.audio_path AS audio_path LIMIT 100"
    )
    for r in rows:
        new_dir = DIR_13 / to_hexid(r["bid"])
        new_audio = f"13_BGM/{to_hexid(r['bid'])}/{to_hexid(r['bid'])}.wav"
        if r["audio_path"]:
            m.fs_move(_ROOT / r["audio_path"], _ROOT / new_audio, "13", f"BgmTrack {r['bid']}.audio_path")
        else:
            new_dir.mkdir(parents=True, exist_ok=True) if not m.dry else None
        m.set_prop(r["bid"], "BgmTrack", "audio_path", r["audio_path"], new_audio, "13",
                   f"MATCH (n:BgmTrack {{id:{q(r['bid'])}}}) SET n.audio_path = {q(new_audio)}")
        # 同名 md（无图属性）：挪到 13_BGM/<id>/<id>.md
        if r["name"]:
            old_md = DIR_13 / f"{r['name']}.md"
            m.fs_move(old_md, new_dir / f"{to_hexid(r['bid'])}.md", "13", f"BgmTrack {r['bid']} 同名 md")

    m.sweep_empty(DIR_13)
    m.flush_graph()
    m.save_plan()


# ---------------------------------------------------------------- 域 14 声音设计

def domain_14(m: Migrator) -> None:
    print("\n===== 域 14_声音设计 =====")

    rows = run_cypher(
        "MATCH (c:Character)-[:has_voice_design]->(v:VoiceDesign) "
        "RETURN c.id AS cid, v.id AS vid, v.ref_audio_path AS ref_audio_path, v.candidates_path AS candidates_path LIMIT 100"
    )
    for r in rows:
        char_dir = DIR_14 / to_hexid(r["cid"])
        new_ref = f"14_声音设计/{to_hexid(r['cid'])}/ref.wav"
        if r["ref_audio_path"]:
            m.fs_move(_ROOT / r["ref_audio_path"], _ROOT / new_ref, "14", f"VoiceDesign {r['vid']}.ref_audio_path")
            m.set_prop(r["vid"], "VoiceDesign", "ref_audio_path", r["ref_audio_path"], new_ref, "14",
                       f"MATCH (n:VoiceDesign {{id:{q(r['vid'])}}}) SET n.ref_audio_path = {q(new_ref)}")
        # candidates 目录瞬态（采用后删）：目录存在则整挪，candidates_path 图值一并更新
        if r["candidates_path"]:
            new_cp = f"14_声音设计/{to_hexid(r['cid'])}/candidates/candidates.json"
            old_dir = (_ROOT / r["candidates_path"]).parent
            m.fs_move_dir(old_dir, char_dir / "candidates", "14")
            m.set_prop(r["vid"], "VoiceDesign", "candidates_path", r["candidates_path"], new_cp, "14",
                       f"MATCH (n:VoiceDesign {{id:{q(r['vid'])}}}) SET n.candidates_path = {q(new_cp)}")

    m.sweep_empty(DIR_14)
    m.flush_graph()
    m.save_plan()


# ---------------------------------------------------------------- 域 15 声音母带（含行键重写）

def domain_15(m: Migrator) -> None:
    print("\n===== 域 15_声音 + 行键 =====")

    rows = run_cypher(
        "MATCH (ch:Chapter)-[:has_section]->(:Section)-[:produces]->(l:LineAudio) "
        "WHERE l.voice_key IS NOT NULL OR l.ambient_track IS NOT NULL "
        "RETURN l.id AS lid, l.voice_key AS vk, l.ambient_track AS at, "
        "l.scene_block_id AS block, ch.id AS chid LIMIT 1000"
    )
    key_sets, master_sets, key_detail, master_detail = [], [], [], []
    for r in rows:
        lid = r["lid"]
        new_master = f"15_声音/{to_hexid(r['chid'])}/{to_hexid(r['block'])}/{to_hexid(lid)}.wav"
        for key_prop in ("vk", "at"):
            key = r[key_prop]
            if not key:
                continue
            parts = key.rsplit("-", 3)
            if len(parts) != 4:
                m.missing.append(f"BADKEY(无法四段反解): {key} (行 {lid})")
                continue
            old_wav = DIR_15 / parts[1] / parts[2] / f"{key}.wav"
            m.fs_move(old_wav, _ROOT / new_master, "15", f"行 {lid} {key_prop}")
        key_sets.append({"id": lid, "hx": to_hexid(lid)})
        if r["vk"]:
            key_detail.append({"node": lid, "prop": "voice_key", "old": r["vk"], "new": lid})
            master_sets.append({"id": lid, "mp": new_master})
            master_detail.append({"node": lid, "prop": "master_path", "old": None, "new": new_master})
        if r["at"]:
            key_detail.append({"node": lid, "prop": "ambient_track", "old": r["at"], "new": lid})
        print(f"KEY: 行 {lid} voice_key={r['vk'] or '-'} ambient_track={r['at'] or '-'} -> {lid}")

    # 批量 SET：voice_key/ambient_track = 行 id；say 行并写 master_path
    if key_sets:
        maps = ", ".join("{id:" + q(x["id"]) + ", hx:" + q(x["hx"]) + "}" for x in key_sets)
        m.set_prop("*", "LineAudio", "voice_key/ambient_track", "(批量)", "(=行id)", "15",
                   detail=key_detail,
                   literal="UNWIND [" + maps + "] AS r MATCH (l:LineAudio {id:r.id}) "
                   "SET l.voice_key = CASE WHEN l.voice_key IS NOT NULL THEN r.hx ELSE l.voice_key END, "
                   "l.ambient_track = CASE WHEN l.ambient_track IS NOT NULL THEN r.hx ELSE l.ambient_track END")
    if master_sets:
        maps = ", ".join("{id:" + q(x["id"]) + ", mp:" + q(x["mp"]) + "}" for x in master_sets)
        m.set_prop("*", "LineAudio", "master_path", "(批量)", "(新母带路径)", "15",
                   detail=master_detail,
                   literal="UNWIND [" + maps + "] AS r MATCH (l:LineAudio {id:r.id}) SET l.master_path = r.mp")

    # 清旧章 stem 目录（requirements/ sfx_raw/ 保留）
    if DIR_15.exists():
        for d in sorted(DIR_15.iterdir()):
            if d.is_dir() and d.name not in ("requirements", "sfx_raw"):
                m.sweep_empty(d, keep_top=False)

    m.flush_graph()
    m.save_plan()


# ---------------------------------------------------------------- 域 25 剧本

def domain_25(m: Migrator) -> None:
    print("\n===== 域 25_剧本 =====")

    rows = run_cypher(
        "MATCH (ch:Chapter)-[:has_section]->(sec:Section) WHERE sec.script_path IS NOT NULL "
        "RETURN ch.id AS chid, sec.id AS sid, sec.script_path AS script_path LIMIT 200"
    )
    for r in rows:
        sp = r["script_path"].replace("\\", "/")
        sec_dir_old = (_ROOT / sp).parent           # …/secMM_概述
        new_dir = DIR_25 / to_hexid(r["chid"]) / to_hexid(r["sid"])     # 25_剧本/<ch_hexid>/<sec_hexid>
        m.fs_move_dir(sec_dir_old, new_dir, "25")
        new_val = f"25_剧本/{to_hexid(r['chid'])}/{to_hexid(r['sid'])}/{(_ROOT / sp).name}"
        m.set_prop(r["sid"], "Section", "script_path", sp, new_val, "25",
                   f"MATCH (n:Section {{id:{q(r['sid'])}}}) SET n.script_path = {q(new_val)}")

    # 自由节（未组章）：25_剧本/自由节/<sec_id>/（当前图上无，规则保留）
    rows = run_cypher(
        "MATCH (sec:Section) WHERE NOT ()-[:has_section]->(sec) AND sec.script_path IS NOT NULL "
        "RETURN sec.id AS sid, sec.script_path AS script_path LIMIT 100"
    )
    for r in rows:
        sp = r["script_path"].replace("\\", "/")
        new_dir = DIR_25 / "自由节" / to_hexid(r["sid"])
        m.fs_move_dir((_ROOT / sp).parent, new_dir, "25")
        new_val = f"25_剧本/自由节/{to_hexid(r['sid'])}/{(_ROOT / sp).name}"
        m.set_prop(r["sid"], "Section", "script_path", sp, new_val, "25",
                   f"MATCH (n:Section {{id:{q(r['sid'])}}}) SET n.script_path = {q(new_val)}")

    if DIR_25.exists():
        for d in sorted(DIR_25.iterdir()):
            if d.is_dir() and d.name != "自由节":
                m.sweep_empty(d, keep_top=False)

    m.flush_graph()
    m.save_plan()


# ---------------------------------------------------------------- 域 dirty 脏数据

def domain_dirty(m: Migrator) -> None:
    print("\n===== 域 dirty（脏数据清理）=====")
    # 注意：Section.scene_blocks 不在此清（generate_portrait_map 尚在消费，阶段②改码后再删）

    jobs = [
        ("VoiceDesign", "clone_prompt_path",
         "MATCH (v:VoiceDesign) WHERE v.clone_prompt_path IS NOT NULL "
         "RETURN v.id AS id, v.clone_prompt_path AS val LIMIT 50"),
        ("DesignSheet", "name",
         "MATCH (d:DesignSheet) WHERE d.name IS NOT NULL "
         "RETURN d.id AS id, d.name AS val LIMIT 50"),
        ("Spot", "status",
         "MATCH (s:Spot) WHERE s.status IS NOT NULL "
         "RETURN s.id AS id, s.status AS val LIMIT 50"),
        ("DesignSheet", "slug",
         "MATCH (d:DesignSheet) WHERE d.slug IS NOT NULL "
         "RETURN d.id AS id, d.slug AS val LIMIT 50"),
    ]
    for label, prop, cy in jobs:
        for r in run_cypher(cy):
            m.set_prop(r["id"], label, prop, r["val"], None, "dirty",
                       f"MATCH (n:{label} {{id:{q(r['id'])}}}) REMOVE n.{prop}")
            print(f"REMOVE: {label} {r['id']}.{prop} (旧值 {r['val']!r})")

    # CostumeStyle.name 去 <char>- 前缀（先查冲突：strip 后同角色重名则跳过报人工）
    rows = run_cypher(
        "MATCH (c:Character)-[:has_costume]->(cs:CostumeStyle) "
        "WHERE cs.name STARTS WITH c.name + '-' "
        "RETURN c.id AS cid, c.name AS cname, cs.id AS csid, cs.name AS csname LIMIT 100"
    )
    seen: dict[str, str] = {}
    for r in rows:
        new_name = r["csname"][len(r["cname"]) + 1:]
        prev = seen.get(r["cid"] + "/" + new_name)
        if prev:
            m.missing.append(f"CONFLICT(strip 重名): {prev} 与 {r['csid']} -> {new_name!r}（跳过，人工裁决）")
            continue
        seen[r["cid"] + "/" + new_name] = r["csid"]
        m.set_prop(r["csid"], "CostumeStyle", "name", r["csname"], new_name, "dirty",
                   f"MATCH (n:CostumeStyle {{id:{q(r['csid'])}}}) SET n.name = {q(new_name)}")
        print(f"STRIP: CostumeStyle {r['csid']} {r['csname']!r} -> {new_name!r}")

    m.flush_graph()
    m.save_plan()


# ---------------------------------------------------------------- verify

def cmd_verify() -> int:
    print("\n===== verify（五断言）=====")
    fails, warns = [], []

    # ① 路径属性 → 文件存在
    checks = [
        ("DesignSheet", "prompt_path"), ("DesignSheet", "image_path"),
        ("IllusDesign", "prompt_path"), ("IllusDesign", "image_path"),
        ("StandingIllustration", "prompt_path"), ("StandingIllustration", "image_path"),
        ("SceneLayer", "prompt_path"), ("SceneLayer", "image_path"),
        ("Spot", "dsl_path"), ("BgmTrack", "audio_path"),
        ("VoiceDesign", "ref_audio_path"), ("VoiceDesign", "candidates_path"),
        ("Character", "ref_image_path"), ("Section", "script_path"),
        ("LineAudio", "master_path"),
    ]
    referenced = set()
    for label, prop in checks:
        where = "n.status = 2" if (label, prop) == ("BgmTrack", "audio_path") else "true"
        rows = run_cypher(
            f"MATCH (n:{label}) WHERE n.{prop} IS NOT NULL AND {where} "
            f"RETURN n.id AS id, n.{prop} AS val LIMIT 2000"
        )
        for r in rows:
            p = _ROOT / str(r["val"]).replace("\\", "/")
            referenced.add(str(p.relative_to(_ROOT)).replace("\\", "/"))
            if not p.exists():
                fails.append(f"① {label} {r['id']}.{prop} -> {r['val']} 不存在")

    # ② status 门
    for cy, desc in (
        ("MATCH (l:LineAudio) WHERE l.status >= 10 AND l.voice_key IS NOT NULL AND l.master_path IS NOT NULL "
         "RETURN l.id AS id, l.master_path AS val LIMIT 2000", "行 status≥10 母带"),
        ("MATCH (b:BgmTrack) WHERE b.status = 2 RETURN b.id AS id, b.audio_path AS val LIMIT 100", "BGM status=2"),
        ("MATCH (s:Section) WHERE s.script_path IS NOT NULL RETURN s.id AS id, s.script_path AS val LIMIT 200", "节定稿"),
    ):
        for r in run_cypher(cy):
            if not (_ROOT / str(r["val"]).replace("\\", "/")).exists():
                fails.append(f"② {desc} {r['id']} -> {r['val']} 不存在")

    # ③ 孤儿扫描（六域树上不被图属性引用的文件 → WARN）
    exempt_prefix = ("15_声音/requirements/", "15_声音/sfx_raw/", "25_剧本/第一个故事/")
    exempt_names = {"README.md", "SOURCES.md"}
    for base in (DIR_06, DIR_07, DIR_13, DIR_14, DIR_15, DIR_25):
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if not f.is_file():
                continue
            rel = str(f.relative_to(_ROOT)).replace("\\", "/")
            if rel.startswith(exempt_prefix) or f.name in exempt_names or f.suffix in (".py", ".pyc"):
                continue
            if rel.endswith(".md") and rel.startswith("13_BGM/"):
                continue  # BGM 同名 md（无图属性）
            if rel.startswith("25_剧本/") and not rel.endswith("台词.ink"):
                continue  # 节私有产物（小说.md/outline/dayNN 等，零图写入哲学）
            if rel not in referenced:
                warns.append(f"③ 孤儿: {rel}")

    # ④ NTFS case-fold：文件名域 = hexid（全小写），检查 hexid 解码无重复即可
    ids = run_cypher("MATCH (n) WHERE n.id IS NOT NULL RETURN n.id AS id LIMIT 100000")
    hex_map: dict[str, str] = {}
    for r in ids:
        h = to_hexid(r["id"])
        if h in hex_map and hex_map[h] != r["id"]:
            fails.append(f"④ hexid 碰撞: {hex_map[h]} vs {r['id']}")
        hex_map[h] = r["id"]

    # ⑤ 行键 ≡ hexid(行 id)
    for prop in ("voice_key", "ambient_track"):
        rows = run_cypher(
            f"MATCH (l:LineAudio) WHERE l.{prop} IS NOT NULL "
            f"RETURN l.id AS id, l.{prop} AS val LIMIT 2000"
        )
        for r in rows:
            if r["val"] != to_hexid(r["id"]):
                fails.append(f"⑤ 行 {r['id']} {prop}={r['val']} ≠ hexid")

    for f in fails[:80]:
        print(f"FAIL {f}")
    for w in warns[:80]:
        print(f"WARN {w}")
    print(f"\n[verify] FAIL {len(fails)} · WARN {len(warns)}"
          f"{' —— 未全部通过' if fails else ' —— 通过（WARN 供人工裁决）'}")
    return 1 if fails else 0


# ---------------------------------------------------------------- rollback

def cmd_rollback(plan_file: str) -> None:
    entries = json.loads(Path(plan_file).read_text(encoding="utf-8"))
    graph_sets = []
    print(f"回滚 {len(entries)} 条（盘先逆挪，图后逆写）")
    for e in reversed(entries):
        if e["op"] == "FS_MOVE":
            old, new = _ROOT / e["old"], _ROOT / e["new"]
            if new.exists() and not old.exists():
                old.parent.mkdir(parents=True, exist_ok=True)
                new.rename(old)
                print(f"REV-MOVE: {e['new']} -> {e['old']}")
            else:
                print(f"REV-SKIP: {e['old']} / {e['new']}")
        elif e["op"] == "SET":
            label = e["label"]
            rows_to_rev = e.get("detail") or [e]
            for row in rows_to_rev:
                node, prop, old = row["node"], row["prop"], row.get("old", row)
                if node == "*":
                    continue
                if old is None:
                    graph_sets.append(f"MATCH (n:{label} {{id:{q(node)}}}) REMOVE n.{prop}")
                else:
                    graph_sets.append(f"MATCH (n:{label} {{id:{q(node)}}}) SET n.{prop} = {q(old)}")
    for i in range(0, len(graph_sets), 100):
        run_write(graph_sets[i:i + 100])
    print(f"[rollback] 图逆写 {len(graph_sets)} 条已提交")


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="产物目录 name→id 锚定一次性迁移")
    ap.add_argument("--dry-run", action="store_true", help="只列计划不执行")
    ap.add_argument("--domain", choices=[*DOMAINS, "all"], help="迁移域")
    ap.add_argument("--verify", action="store_true", help="迁移后断言")
    ap.add_argument("--rollback", metavar="PLAN_JSON", help="按审计计划反向回滚")
    args = ap.parse_args()

    if args.rollback:
        cmd_rollback(args.rollback)
        return 0
    if args.verify:
        return cmd_verify()

    runners = {"06": domain_06, "07": domain_07, "13": domain_13, "14": domain_14,
               "15": domain_15, "25": domain_25, "dirty": domain_dirty}
    todo = list(DOMAINS) if args.domain in (None, "all") else [args.domain]
    if args.domain is None and not args.dry_run:
        print("提示：未指定 --domain；执行需显式给 --domain <域|all>（dry-run 可省略）")
        return 2

    for d in todo:
        m = Migrator(dry_run=args.dry_run)
        runners[d](m)
        n_move = sum(1 for e in m.plan if e["op"] == "FS_MOVE")
        print(f"[{d}] MOVE {n_move} · SKIP {len(m.skip)} · MISSING/CONFLICT {len(m.missing)}"
              f"{'（dry-run）' if args.dry_run else ''}")
        for s in m.skip[:20]:
            print(f"  {s}")
        for s in m.missing[:20]:
            print(f"  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
