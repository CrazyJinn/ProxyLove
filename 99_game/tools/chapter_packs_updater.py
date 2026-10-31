#!/usr/bin/env python
"""更新 data/chapter_packs.json 中某章节的资源清单（幂等）。

Web 按章分包的依据：导出工具读本文件，把每章列出的资源打进 <stem>.pck。
pck 内部资源路径与全局 manifest 一致（如 assets/portraits/陈默.沉重.png），
故各章包挂载后 res:// 全局路径都能命中，跨章复用的资源在各章包内各自存在副本。

结构（2026-10-31 id 锚定：stem=hexid(Chapter.id)，条目内嵌 title/chapter_no 供
Title 章下拉显示与排序；各清单为 hexid 键）：
    {
      "04fb5959f0800000": {
        "title": "新皮肤",
        "chapter_no": 1,
        "portraits": ["04fe016b88800000", ...],
        "scenes": ["0507e713eac00001", ...],
        "voices": ["04fe002dea400026", ...],
        "sfx": [...], "bgm": [...]
      },
      ...
    }

数据源由 chapter-publisher 提供（合并章 JSON 的 requires.portraits——uses 边投影的 guid 整键；+ has_layer 背景）；
voices 由 chapter-publisher 提供（从合并后章 JSON 的 say.voice 推导，voice_bundler list 出 voice 键 CSV）。
幂等：覆盖该 stem 条目，保留其他章。无依赖（仅标准库）。

CLI: chapter_packs_updater.py <hexid_stem> [--title T] [--chapter-no N] [--portraits ...] ...
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 99_game/tools/ → 项目根
DEFAULT_PACKS = ROOT / "99_game" / "data" / "chapter_packs.json"


def _split_csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="更新 chapter_packs.json 的某章资源清单")
    ap.add_argument("stem", help="章节 stem = hexid(Chapter.id)（章 JSON/pck 同名主体）")
    ap.add_argument("--title", default="", help="章显示名（Chapter.title，Title 章下拉用）")
    ap.add_argument("--chapter-no", type=int, default=None, help="章序号（Title 下拉排序用）")
    ap.add_argument("--portraits", default="", help="立绘键 CSV（hexid(stand_id)，取合并章 JSON requires.portraits）")
    ap.add_argument("--scenes", default="", help="场景键 CSV（hexid(Scene.id)）")
    ap.add_argument("--voices", default="", help="语音键 CSV（hexid(行id)）")
    ap.add_argument("--sfx", default="", help="环境音键 CSV（hexid(行id)，本章已批 ambient 行）")
    ap.add_argument("--bgm", default="", help="BGM 键 CSV（hexid(bgm_id)，章 JSON 各 scene-block bgm.track）")
    ap.add_argument("--packs", default=str(DEFAULT_PACKS), help="chapter_packs.json 路径")
    args = ap.parse_args(argv)

    path = Path(args.packs)
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except json.JSONDecodeError:
            print(f"[warn] {path} JSON 解析失败，从空重建", file=sys.stderr)
            data = {}

    entry = data.get(args.stem, {})
    if args.title:
        entry["title"] = args.title
    if args.chapter_no is not None:
        entry["chapter_no"] = args.chapter_no
    # 仅更新显式传入（非空）的字段，保留未传字段（部分更新，避免调用方只传 --voices 时清空 portraits/scenes）
    if args.portraits:
        entry["portraits"] = _split_csv(args.portraits)
    if args.scenes:
        entry["scenes"] = _split_csv(args.scenes)
    if args.voices:
        entry["voices"] = _split_csv(args.voices)
    if args.sfx:
        entry["sfx"] = _split_csv(args.sfx)
    if args.bgm:
        entry["bgm"] = _split_csv(args.bgm)
    data[args.stem] = entry

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"OK: {args.stem} title={entry.get('title', '')} no={entry.get('chapter_no')} "
        f"portraits={len(entry.get('portraits', []))} "
        f"scenes={len(entry.get('scenes', []))} voices={len(entry.get('voices', []))} "
        f"sfx={len(entry.get('sfx', []))} bgm={len(entry.get('bgm', []))} -> {path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
