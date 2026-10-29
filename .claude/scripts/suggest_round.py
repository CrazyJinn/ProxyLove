#!/usr/bin/env python3
"""建议 JSON 轮次推导（共享基础设施，只读）。

用法：
    python suggest_round.py                 # 输出下一轮次号（纯数字，供内联）
    python suggest_round.py --dir <path>    # 指定产物目录（默认 <项目根>/02_剧情数据）
    python suggest_round.py --list          # 附带列出全部 round 文件与推导依据

规则：扫目录下 `*round*_建议.json`，从文件名提取 `_round<N>_`，**全量取 max+1**。
走建议 JSON 通道的 skill（event-ideator / event-stager /
chapter-novelist）共用同一轮次计数器——新建议文件必须取全局 max+1，否则与
既有文件撞号，dashboard 按文件名倒序拾取时撞号文件会互相顶掉。

为什么不能按文件名排序取最新文件的轮次：日期翻篇或新开主题时，最新文件的
轮次可以小于历史最大轮次（如 10-21 已到 round8，10-22 新开主题文件名是
round1）——排序取最新会把轮次倒回去，产生 2026-10-22_round9 与既有
2026-10-21_round9 并存。必须全量提取取全局 max。
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # .claude/scripts/ → 项目根
PAT = re.compile(r"round(\d+)")


def next_round(out_dir: Path) -> tuple[int, dict[str, int]]:
    """返回 (下一轮次号, {文件名: 轮次})。无任何 round 文件时下一轮为 1。"""
    seen: dict[str, int] = {}
    for fp in sorted(out_dir.glob("*round*_建议.json")):
        m = PAT.search(fp.name)
        if m:
            seen[fp.name] = int(m.group(1))
    return (max(seen.values()) + 1 if seen else 1), seen


def main() -> int:
    ap = argparse.ArgumentParser(description="建议 JSON 轮次推导（取全局 max+1）")
    ap.add_argument("--dir", default=str(ROOT / "02_剧情数据"), help="建议 JSON 目录")
    ap.add_argument("--list", action="store_true", help="列出全部 round 文件与推导依据")
    args = ap.parse_args()

    out_dir = Path(args.dir)
    if not out_dir.is_dir():
        print(f"目录不存在: {out_dir}", file=sys.stderr)
        return 2

    nxt, seen = next_round(out_dir)
    if args.list:
        for name, n in sorted(seen.items(), key=lambda kv: kv[1]):
            print(f"round{n}\t{name}")
        print(f"--- 全局 max={max(seen.values()) if seen else 0} → 下一轮 = {nxt}")
    else:
        print(nxt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
