"""环境音行任务生成（系统 python 跑）：查单节 op=transition / op=bed_start 的 status=0 图行 → jobs JSON。

方言 v3 音频三型：sfx:（点状→op=transition，kind=sfx，Freesound 实录）、bed+（音床起→
op=bed_start，kind=bed，AudioFly 声景）；旧环境音两型（独立行/内嵌）已废止（2026-09-03 迁移）。
track 由本脚本预计算（前缀 amb-/bed- + <stem>-<block>-<node_id>，复用 voice_bundler 单源
构造），杜绝 LLM 手拼 key；行上已有 track 沿用原键（键一经落图终身不换前缀）。
"""
import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS.parent.parent / "section-voice-publisher" / "scripts"))
from voice_bundler import _run_cypher, chapter_stem_from_meta, make_ambient_track  # noqa: E402


def collect(section_id: str) -> list:
    rows = _run_cypher(
        "MATCH (ch:Chapter)-[:has_section]->(sec:Section {id:'" + section_id + "'}) "
        "OPTIONAL MATCH (sec)-[:has_outline]->(ol:SecOutline)-[:produces]->(sc:SecScript) "
        "OPTIONAL MATCH (sc)-[p:produces]->(l:LineAudio) "
        "RETURN ch.chapter_no AS no, ch.title AS title, sc.id AS sc_id, "
        "l.id AS lid, l.op AS op, l.text AS text, l.bed AS bed, l.prompt AS prompt, "
        "l.ambient_track AS ambient_track, "
        "l.status AS status, l.scene_block_id AS block, p.order AS ord "
        "ORDER BY p.order"
    )
    if not rows or not rows[0].get("sc_id"):
        raise SystemExit(f"Section {section_id} 无 SecScript（先定稿+拆分）")
    stem = chapter_stem_from_meta(rows[0]["no"], rows[0]["title"])

    jobs, seen_any_line = [], False
    for r in rows:
        if not r.get("lid"):
            continue
        seen_any_line = True
        block = r.get("block") or ""  # 行上直读块归属（scene 行已去图化）
        if r["op"] == "transition":
            kind, text, prefix = "sfx", r.get("text") or "", "amb"
        elif r["op"] == "bed_start":
            kind, text, prefix = "bed", r.get("text") or "", "bed"  # 语义在 bed+ 行 text
        else:
            continue
        if r.get("status") != 0:
            continue  # 只挑待产行（被驳回/未产/stale 均归一于 0）
        track = r.get("ambient_track") or make_ambient_track(stem, block, r["lid"], prefix=prefix)
        jobs.append({"node_id": r["lid"], "track": track, "stem": stem,
                     "block": block, "text": text, "kind": kind, "bed": r.get("bed"),
                     "prompt": r.get("prompt") or ""})  # 行上存量 prompt（重产复用；空=需现场翻写）
    if not seen_any_line:
        raise SystemExit(f"Section {section_id} 图无行（先 section-voice-publisher 拆分）")
    return jobs


def main():
    ap = argparse.ArgumentParser(description="环境音行任务生成（op=transition status=0 + 氛围 narrate → jobs JSON）")
    ap.add_argument("--section", required=True)
    ap.add_argument("-o", "--out", default="-", help="输出路径（默认打印 stdout）")
    args = ap.parse_args()

    jobs = collect(args.section)
    data = json.dumps(jobs, ensure_ascii=False, indent=2)
    if args.out == "-":
        print(data)
    else:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(data, encoding="utf-8")
    print(f"[tasks] {len(jobs)} 条环境音待产", file=sys.stderr)


if __name__ == "__main__":
    main()
