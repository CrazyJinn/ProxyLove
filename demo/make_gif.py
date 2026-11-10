#!/usr/bin/env python3
"""demo：参考图 → OfoxAI 精灵图 → 本地 Pillow 合成 GIF

为什么走精灵图路径（见 demo/gif.md）：
  - OfoxAI 的原生 GIF 只在文生图 generations 端点支持（frame_count/frame_duration_ms），
    图片编辑端点（edits，带参考图的图生图）不输出 GIF；
  - 因此带参考图的链路 = edits 产「精灵图」静态 PNG → 本地切格合成 GIF。
  - 好处：帧率/尺寸/循环全部在合成侧精确可控，改配置重新合成不重新调 API。

用法（在 demo/ 或仓库任意目录均可）：
  python demo/make_gif.py all                    # 全链路：参考图 → sheet.png → out.gif
  python demo/make_gif.py gen-sheet              # 只调 API 产精灵图
  python demo/make_gif.py compose                # 只本地合成（默认读 demo/sheet.png）
  python demo/make_gif.py compose --frame-ms 200 --out-width 384   # 改配置重新合成（免费）
  python demo/make_gif.py inspect demo/out.gif   # 检查帧数/帧间隔/循环/首尾帧差异

依赖：requests（系统 Python 已有，ofoxai_api 需要）+ Pillow（pip install Pillow）。
凭证：复用 Asset/settings.json 的 ofox_api_key（ofoxai_api.find_settings 向上搜索）。
"""

import argparse
import sys
from pathlib import Path

# ── 复用项目 API 层（skill 同款：key 读取 / 重试 / b64 解码）──
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude/skills/infra-image-generator/scripts"))
from ofoxai_api import submit_task, save_result  # noqa: E402

try:
    from PIL import Image, ImageChops, ImageStat
except ImportError:
    raise SystemExit("缺少 Pillow，请先安装：python -m pip install Pillow")

DEMO_DIR = Path(__file__).resolve().parent
REF_IMAGE = DEMO_DIR / "参考图.png"

# ── 可调配置（待讨论敲定）────────────────────────────────────────────
SHEET_PROMPT = """Create one still sprite sheet of the chibi girl from the attached reference image (use the leftmost side view facing left as the model). Exactly nine equal cells in three columns and three rows, read left-to-right then top-to-bottom, no borders or gutters. Cells 1 through 8 show one complete run cycle spread evenly: she runs toward the left with quick light strides, both legs going through a full stride (contact, push-off, passing, reach), arms swinging naturally. Her black hooded cape flows and trails behind her, its hem and purple lining fluttering in a continuous wave across frames. The ninth and last cell must repeat exactly the same pose as the first cell — identical starting pose, framing, scale and proportions — so the sequence loops seamlessly. Keep her identity fixed in every cell: black bob haircut, purple-lined cape, black dress, thigh-high socks, black boots. One centered full-body side view per cell, same scale and framing, identical plain background in every cell. Match the reference style: clean chibi anime lines, flat colors, soft simple shading. No text, captions, cell labels, extra characters or props. This output is a sprite sheet for later GIF assembly, not an animation."""

CONFIG = {
    # API 侧（gen-sheet）
    "model": "openai/gpt-image-2.6-sunburst",  # 2.6 双模型之一；flare/sunburst 均可换
    "size": "1536x1536",                    # 3×3 → 每格 512×512 正方形（2.6 接受 16 倍数尺寸）
    "quality": "medium",
    # 合成侧（compose）
    "cols": 3,
    "rows": 3,                              # 格子数 = cols×rows = 9（首末格同姿态锚定循环）
    "drop_last": 1,                         # 合成时丢末尾 N 帧（第 9 格=第 1 格重复，进 GIF 前丢弃避免停顿）
    "frame_ms": 100,                        # 每帧时长 ms（跑步循环 ≈ 10 fps；GIF 粒度 10ms）
    "out_width": 512,                       # 输出 GIF 每帧宽度 px（高度按格子比例）
    "loop": 0,                              # 0 = 无限循环；N = 播 N 遍后停
    "transparent": False,                   # False = 白底不透明；True = 保留透明（1bit 抖动）
}
# ─────────────────────────────────────────────────────────────────────


def gen_sheet(out_path: Path, cfg: dict) -> Path:
    """参考图 → OfoxAI edits 端点 → 精灵图 PNG（图生图，multipart 确实传图）"""
    if not REF_IMAGE.exists():
        raise SystemExit(f"参考图不存在: {REF_IMAGE}")
    print(f"[gen-sheet] model={cfg['model']} size={cfg['size']} ref={REF_IMAGE.name}")
    result = submit_task(
        prompt=cfg["prompt"],
        model=cfg["model"],
        size=cfg["size"],
        quality=cfg["quality"],
        image=[str(REF_IMAGE)],
    )
    saved = save_result(result, str(out_path))
    if saved.get("status") != "done":
        raise SystemExit(f"[gen-sheet] 失败: {saved}")
    path = Path(saved["image_path"])
    print(f"[gen-sheet] 精灵图已保存: {path}")
    return path


def compose(sheet_path: Path, out_path: Path, cfg: dict) -> Path:
    """精灵图 PNG → GIF（本地，零 API 调用；改 frame_ms/out_width 后可免费重跑）"""
    sheet = Image.open(sheet_path).convert("RGBA")
    w, h = sheet.size
    cols, rows = cfg["cols"], cfg["rows"]
    if w % cols or h % rows:
        raise SystemExit(f"网格无法等分: 图 {w}x{h} ÷ {cols}x{rows}（换 --cols/--rows 或重新生成）")
    cw, ch = w // cols, h // rows
    scale = cfg["out_width"] / cw
    frames = []
    for r in range(rows):
        for c in range(cols):
            cell = sheet.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
            cell = cell.resize((cfg["out_width"], round(ch * scale)), Image.LANCZOS)
            frames.append(to_gif_frame(cell, cfg["transparent"]))
    drop = cfg.get("drop_last", 0)
    total = len(frames)
    if drop > 0:
        frames = frames[: max(1, total - drop)]
    first, rest = frames[0], frames[1:]
    first.save(
        out_path,
        save_all=True,
        append_images=rest,
        duration=cfg["frame_ms"],
        loop=cfg["loop"],
        optimize=True,
        **frame_save_kwargs(cfg["transparent"]),
    )
    dropped = f"（切 {total} 格，丢末 {drop} 帧）" if drop else ""
    print(f"[compose] {len(frames)} 帧 × {cfg['frame_ms']}ms (周期 {len(frames) * cfg['frame_ms'] / 1000:.2f}s)"
          f" 宽 {cfg['out_width']}px loop={cfg['loop']}{dropped} → {out_path}")
    return out_path


def to_gif_frame(cell: Image.Image, transparent: bool) -> Image.Image:
    """RGBA 帧 → GIF P 模式帧。白底模式铺白底；透明模式把 alpha 阈值化为索引 255 透明色。"""
    if not transparent:
        bg = Image.new("RGB", cell.size, (255, 255, 255))
        bg.paste(cell, mask=cell.split()[3])
        return bg.convert("P", palette=Image.ADAPTIVE)
    p = cell.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
    mask = cell.split()[3].point(lambda a: 255 if a <= 128 else 0)  # alpha≤128 → 透明
    p.paste(255, mask)
    return p


def frame_save_kwargs(transparent: bool) -> dict:
    if not transparent:
        return {}
    return {"transparency": 255, "disposal": 2}


def inspect(gif_path: Path) -> None:
    """验收（gif.md：预览会动 ≠ 导出正确，必须核对结构数字）"""
    im = Image.open(gif_path)
    n = getattr(im, "n_frames", 1)
    durations = []
    for i in range(n):
        im.seek(i)
        durations.append(im.info.get("duration", 0))
    im.seek(0)
    first = im.convert("RGB")
    im.seek(n - 1)
    last = im.convert("RGB")
    diff = sum(ImageStat.Stat(ImageChops.difference(first, last)).mean) / 3
    size = gif_path.stat().st_size
    print(f"文件        : {gif_path}")
    print(f"尺寸        : {im.size[0]} × {im.size[1]} px")
    print(f"帧数        : {n}")
    print(f"每帧时长    : {durations} ms")
    print(f"总周期      : {sum(durations) / 1000:.2f} s")
    print(f"循环        : {im.info.get('loop', '(缺省=播放一次)')} (0=无限)")
    print(f"文件大小    : {size:,} 字节 ({size / 1024:.0f} KB)")
    print(f"首尾帧 RGB 差异: {diff:.1f}/255 (越小循环越顺滑；只作诊断不是评分)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["all", "gen-sheet", "compose", "inspect"],
                    help="all=全链路 | gen-sheet=只调 API | compose=只本地合成 | inspect=检查 GIF")
    ap.add_argument("target", nargs="?", help="inspect 的 GIF 路径")
    ap.add_argument("--sheet", default=str(DEMO_DIR / "sheet.png"), help="精灵图路径（compose 输入）")
    ap.add_argument("--out", default=str(DEMO_DIR / "out.gif"), help="GIF 输出路径")
    ap.add_argument("--model")
    ap.add_argument("--size")
    ap.add_argument("--cols", type=int)
    ap.add_argument("--rows", type=int)
    ap.add_argument("--drop-last", type=int, help="合成时丢末尾 N 帧（首末格同姿态时丢 1）")
    ap.add_argument("--frame-ms", type=int, help="每帧时长 ms（帧率=1000/frame_ms）")
    ap.add_argument("--out-width", type=int, help="输出 GIF 宽度 px")
    ap.add_argument("--loop", type=int, help="0=无限循环")
    ap.add_argument("--transparent", action="store_true", help="保留透明背景（默认白底不透明）")
    args = ap.parse_args()

    cfg = dict(CONFIG)
    cfg["prompt"] = SHEET_PROMPT
    for k in ("model", "size", "cols", "rows", "drop_last", "frame_ms", "out_width", "loop"):
        if getattr(args, k) is not None:
            cfg[k] = getattr(args, k)
    if args.transparent:
        cfg["transparent"] = True

    if args.cmd == "inspect":
        if not args.target:
            raise SystemExit("用法: python make_gif.py inspect <gif路径>")
        inspect(Path(args.target))
    elif args.cmd == "gen-sheet":
        gen_sheet(Path(args.sheet), cfg)
    elif args.cmd == "compose":
        compose(Path(args.sheet), Path(args.out), cfg)
    else:  # all
        sheet = gen_sheet(Path(args.sheet), cfg)
        compose(sheet, Path(args.out), cfg)
        inspect(Path(args.out))


if __name__ == "__main__":
    main()
