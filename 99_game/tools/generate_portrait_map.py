#!/usr/bin/env python
"""生成章节映射 chapter-map（发布时章 JSON 的 BGM 演出注入源）。

查图一路：
  bgm：本章 Section-contains->Scene-has_bgm->BgmTrack（仅 status=2 音频已归档的进 map，
       <2 的打印警告由发布方处理）。填入 {scene: {track, mode, loop}}。

章映射只含 bgm 段；立绘整键由 merge_sections_to_chapter.py 沿
LineAudio-[:uses]->StandingIllustration 边在投影期直接解析，不再需要 scene 级映射改写。
工具名与 CLI 保持不变（chapter-publisher 调用零改）。

CLI: generate_portrait_map.py <chapter_id> -o <out.json>
退码：0 成功 / 1 查图失败 / 2 参数错（与 99_game/tools 既有工具对齐）。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 99_game/tools/ → 项目根
CYPHER_EXEC = ROOT / ".claude" / "scripts" / "cypher_exec.py"
_SYS = ROOT / ".claude" / "scripts"
if str(_SYS) not in sys.path:
    sys.path.insert(0, str(_SYS))  # snowflake_base62.to_hexid（键 hexid 化）


def _run_cypher(cypher: str) -> list:
    """调 cypher_exec.py --json，提取返回的 JSON 数组（cypher_exec 输出含连接提示行）。

    与 manifest_builder.py 同款（项目风格：每脚本自携一份）。
    """
    proc = subprocess.run(
        [sys.executable, str(CYPHER_EXEC), "-c", cypher, "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    out = proc.stdout
    start, end = out.find("["), out.rfind("]")
    if start == -1 or end == -1:
        raise RuntimeError(
            f"cypher_exec 未返回 JSON（退出码 {proc.returncode}）:\n"
            f"stderr: {proc.stderr}\nstdout: {out}"
        )
    return json.loads(out[start:end + 1])


def _scene_ids_of_chapter(chapter_id: str) -> list[str]:
    """章内全部行块 id（LineAudio.scene_block_id=scene_id）去重。
    id 直连（scene_blocks 属性已废），历史节与新节通吃。"""
    rows = _run_cypher(
        "MATCH (:Chapter {id:'" + chapter_id + "'})-[:has_section]->(:Section)"
        "-[:produces]->(l:LineAudio) "
        "WHERE l.scene_block_id IS NOT NULL "
        "RETURN DISTINCT l.scene_block_id AS bid"
    )
    return [r["bid"] for r in rows if r.get("bid")]


def generate_bgm(chapter_id: str) -> tuple:
    """查图生成 ({scene_hexid: {track=bgm_hexid, mode, loop}}, [未就绪警告])。
    仅 status=2 的 BgmTrack 进 map。场景集取各节行块 id 直查 Scene
    （id 直连，键 = hexid(scene.id)，与章 JSON scenes[].scene 同源）。"""
    from snowflake_base62 import to_hexid
    bids = _scene_ids_of_chapter(chapter_id)
    if not bids:
        return {}, []
    in_list = ", ".join("'" + b.replace("'", "\\'") + "'" for b in bids)
    rows = _run_cypher(
        "MATCH (scene:Scene)-[:has_bgm]->(b:BgmTrack) "
        "WHERE scene.id IN [" + in_list + "] "
        "RETURN DISTINCT scene.id AS sid, b.id AS bid, b.name AS bname, b.status AS status, "
        "b.mode AS mode, b.loop AS loop ORDER BY sid"
    )
    m: dict = {}
    warnings = []
    for r in rows:
        sid, bid = (r.get("sid") or "").strip(), (r.get("bid") or "").strip()
        if not sid or not bid:
            continue
        if r.get("status") != 2:
            warnings.append(f"scene={sid} 的 BgmTrack {r.get('bname')!r} status={r.get('status')}（≠2 音频未归档），跳过注入")
            continue
        m[to_hexid(sid)] = {
            "track": to_hexid(bid),
            "mode": (r.get("mode") or "play"),
            "loop": r.get("loop") if r.get("loop") is not None else True,
        }
    return m, warnings


def generate_map(chapter_id: str) -> dict:
    """产出章映射 {"bgm": {...}}（见模块 docstring）。"""
    bgm, warnings = generate_bgm(chapter_id)
    for w in warnings:
        print(f"[warn] {w}", file=sys.stderr)
    return {"bgm": bgm}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成章节映射（BGM 注入源；立绘整键已改由 uses 边投影）")
    ap.add_argument("chapter_id", help="Chapter 节点 ID（snowflake）")
    ap.add_argument("-o", "--out", required=True, help="输出 JSON 路径")
    args = ap.parse_args(argv)

    try:
        m = generate_map(args.chapter_id)
    except (RuntimeError, ValueError) as e:
        sys.stderr.write(f"生成失败: {e}\n")
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OK: {args.out}（{len(m['bgm'])} bgm 映射）")
    for scene, info in m["bgm"].items():
        print(f"  {scene} | bgm -> {info['track']} ({info['mode']}, loop={info['loop']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
