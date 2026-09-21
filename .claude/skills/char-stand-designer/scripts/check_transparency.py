#!/usr/bin/env python3
"""立绘透明校验（char-stand-designer 生成后、写图前门禁）。

判据（2026-09-09 实验矩阵）：OfoxAI gpt-image 系透明由英文措辞 +
--background transparent 参数双在场触发；主体像素 alpha≈253（非 255），故不能用
「alpha<255 占比」——必须用 **alpha==0 像素占比 > 1%** 判定背景被真正扣除。

用法：
    python check_transparency.py <image_path> [--min-zero-ratio 0.01]
退出码：0 透明合格 / 1 不合格（无 alpha 通道或 alpha=0 占比不足）/ 2 文件不存在
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image


def main(argv) -> int:
    p = argparse.ArgumentParser(description="立绘透明 PNG 校验（alpha=0 占比 > 阈值）")
    p.add_argument("image", help="待校验图片路径")
    p.add_argument("--min-zero-ratio", type=float, default=0.01,
                   help="alpha=0 像素占比阈值（默认 0.01，即 1%%）")
    args = p.parse_args(argv)

    if not Path(args.image).is_file():
        print(json.dumps({"ok": False, "reason": "file_not_found", "path": args.image},
                         ensure_ascii=False))
        return 2

    img = Image.open(args.image)
    has_alpha = "A" in img.getbands() or (img.mode == "P" and "transparency" in img.info)
    if not has_alpha:
        print(json.dumps({"ok": False, "reason": "no_alpha_channel", "mode": img.mode,
                          "hint": "模型返回 RGB——prompt 缺英文透明措辞或被忽略"},
                         ensure_ascii=False))
        return 1

    alpha = img.convert("RGBA").getchannel("A")
    hist = alpha.histogram()
    total = alpha.width * alpha.height
    zero_ratio = hist[0] / total
    ok = zero_ratio > args.min_zero_ratio
    print(json.dumps({"ok": ok, "path": args.image, "mode": img.mode,
                      "alpha_zero_ratio": round(zero_ratio, 4),
                      "reason": None if ok else "alpha_zero_ratio_below_threshold"},
                     ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
