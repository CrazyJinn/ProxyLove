#!/usr/bin/env python
"""从 Neo4j 图生成/更新 99_game/data/manifest.json。

剧本只写逻辑名，manifest 把逻辑名映射到 Godot res:// 资源路径（章 JSON 权威 schema：99_game/data/剧本.schema.json）。
本脚本从图查：
  - status=11 的 StandingIllustration → portraits（键 = <char_name>.<variant_label>）
  - 所有 Scene                        → scenes   （键 = <Scene.name>）
并图驱动收集：
  - status=11 的音频行（ambient_track）→ sfx
  - status=11 的配音行（voice_key）   → voices
保留现有 manifest 的 bgm/cg（无对应图节点，手写）。

资源路径约定（与当前 manifest.json 一致，运行时缺资源由 PlaceholderGen 兜底）：
  portraits: assets/portraits/<逻辑名>.png
  scenes:    assets/scenes/<逻辑名>.png

用法：
    python 99_game/tools/manifest_builder.py [--manifest <path>] [--dry-run]

注意：本脚本只生成逻辑名→路径映射，不负责把美术产物（06_角色美术/、07_场景美术/）
复制到 99_game/assets/——那是部署步骤。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from portrait_key import make_key

ROOT = Path(__file__).resolve().parents[2]  # 99_game/tools/ → 项目根
CYPHER_EXEC = ROOT / ".claude" / "scripts" / "cypher_exec.py"
DEFAULT_MANIFEST = ROOT / "99_game" / "data" / "manifest.json"

PORTRAIT_PREFIX = "assets/portraits/"
SCENE_PREFIX = "assets/scenes/"

def _run_cypher(cypher: str) -> list:
    """调 cypher_exec.py --json，提取返回的 JSON 数组（cypher_exec 输出含连接提示行）。"""
    proc = subprocess.run(
        [sys.executable, str(CYPHER_EXEC), "-c", cypher, "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    out = proc.stdout
    start = out.find("[")
    end = out.rfind("]")
    if start == -1 or end == -1:
        raise RuntimeError(
            f"cypher_exec 未返回 JSON（退出码 {proc.returncode}）:\n"
            f"stderr: {proc.stderr}\nstdout: {out}"
        )
    return json.loads(out[start:end + 1])


def collect_portraits() -> tuple[dict, dict]:
    """status=11 的立绘 → hexid(stand_id): assets/portraits/<hexid>.png

    键 = make_key(stand_id) = hexid(StandingIllustration.id)（全局唯一，改名零漂移；
    角色名/着装/变体名不进键）。旧 name 整键/二维键由 --rebuild 清除。
    返回 (portraits, portrait_scales)：顺带带回 IllusDesign.display_scale（同一次查图），
    portrait_scales = {键: scale}，仅收录 display_scale 非 null 的立绘。
    """
    cypher = (
        "MATCH (stand:StandingIllustration {status:11}) "
        "OPTIONAL MATCH (stand)<-[:expands_to]-(illus:IllusDesign) "
        "RETURN DISTINCT stand.id AS stand_id, illus.display_scale AS scale"
    )
    portraits = {}
    scales = {}
    for r in _run_cypher(cypher):
        stand_id = (r.get("stand_id") or "").strip()
        if not stand_id:
            continue
        key = make_key(stand_id)
        portraits[key] = f"{PORTRAIT_PREFIX}{key}.png"
        scale = r.get("scale")
        if scale is not None:
            scales[key] = scale
    return portraits, scales


def collect_scenes() -> dict:
    """所有 Scene → hexid(Scene.id): assets/scenes/<hexid>.png"""
    from snowflake_base62 import to_hexid
    rows = _run_cypher("MATCH (s:Scene) RETURN s.id AS sid")
    scenes = {}
    for r in rows:
        sid = (r.get("sid") or "").strip()
        if sid:
            key = to_hexid(sid)
            scenes[key] = f"{SCENE_PREFIX}{key}.png"
    return scenes


def collect_sfx() -> dict:
    """已批环境音行 → hexid(行id): assets/sfx/<hexid>.wav（图驱动收集，status=11）。

    以 ambient_track 字段存在为准、不看 op——点状音效行（op=transition）与音床行
    （op=bed_start）同样收集。"""
    rows = _run_cypher(
        "MATCH (l:LineAudio) WHERE l.status = 11 "
        "AND l.ambient_track IS NOT NULL RETURN l.ambient_track AS track"
    )
    return {(r.get("track") or "").strip(): "assets/sfx/" + r["track"] + ".wav"
            for r in rows if (r.get("track") or "").strip()}


def collect_voices() -> dict:
    """已批配音行 → hexid(行id): assets/voices/<hexid>.wav（图驱动收集，status=11）。

    以 voice_key 字段存在为准（say 行）。此前 voices 段由 chapter-publisher 流程维护、
    manifest_builder 输出清单未含——单独重跑会静默抹掉 voices 段致运行时全部配音
    miss（2026-09-03 踩过），现改为图驱动收集与 sfx 对称。"""
    rows = _run_cypher(
        "MATCH (l:LineAudio) WHERE l.status = 11 "
        "AND l.voice_key IS NOT NULL RETURN l.voice_key AS key"
    )
    return {(r.get("key") or "").strip(): "assets/voices/" + r["key"] + ".wav"
            for r in rows if (r.get("key") or "").strip()}


def collect_bgm() -> dict:
    """status=2 的 BgmTrack → hexid(bgm_id): assets/bgm/<hexid>.wav（图驱动，取代旧手写 name 键）。"""
    from snowflake_base62 import to_hexid
    rows = _run_cypher(
        "MATCH (b:BgmTrack {status:2}) WHERE b.audio_path IS NOT NULL RETURN b.id AS bid"
    )
    bgm = {}
    for r in rows:
        bid = (r.get("bid") or "").strip()
        if bid:
            key = to_hexid(bid)
            bgm[key] = "assets/bgm/" + key + ".wav"
    return bgm


def build_manifest(manifest_path: Path, rebuild: bool = False) -> dict:
    # 读现有 manifest，保留 bgm/cg（非图来源）
    existing = {}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[warn] {manifest_path} JSON 解析失败，bgm/sfx/cg 从空重建", file=sys.stderr)

    # 缺省：图查覆盖/补充 existing（向后兼容）；--rebuild：图驱动段全量重建清旧 name 键。
    # bgm 恒图驱动（status=2 才收）——旧手写 name 键在 rebuild 时一并淘汰。
    portraits, scales = collect_portraits()
    scenes, voices, sfx, bgm = collect_scenes(), collect_voices(), collect_sfx(), collect_bgm()
    if rebuild:
        return {
            "portraits": portraits, "portrait_scales": scales,
            "scenes": scenes, "voices": voices, "bgm": bgm, "sfx": sfx,
            "cg": existing.get("cg", {}),
        }
    return {
        "portraits": {**existing.get("portraits", {}), **portraits},
        "portrait_scales": {**existing.get("portrait_scales", {}), **scales},
        "scenes": {**existing.get("scenes", {}), **scenes},
        "voices": {**existing.get("voices", {}), **voices},
        "bgm": {**existing.get("bgm", {}), **bgm},
        "sfx": {**existing.get("sfx", {}), **sfx},
        "cg": existing.get("cg", {}),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="从 Neo4j 图生成/更新 manifest.json")
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="manifest.json 路径")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写盘")
    ap.add_argument("--rebuild", action="store_true",
                    help="全量重建图驱动段（清旧 name 键；随 id 锚定全章重发布使用）")
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    data = build_manifest(manifest_path, rebuild=args.rebuild)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    if args.dry_run:
        sys.stdout.write(text)
        print(
            f"[dry-run] portraits={len(data['portraits'])} "
            f"portrait_scales={len(data['portrait_scales'])} scenes={len(data['scenes'])} "
            f"voices={len(data['voices'])} "
            f"bgm={len(data['bgm'])}(保留) sfx={len(data['sfx'])}(保留) cg={len(data['cg'])}(保留)",
            file=sys.stderr,
        )
        return

    manifest_path.write_text(text, encoding="utf-8")
    print(
        f"已写入 {manifest_path}：portraits={len(data['portraits'])} "
        f"portrait_scales={len(data['portrait_scales'])} "
        f"scenes={len(data['scenes'])} voices={len(data['voices'])} "
        f"bgm={len(data['bgm'])} sfx={len(data['sfx'])} cg={len(data['cg'])}"
    )


if __name__ == "__main__":
    main()
