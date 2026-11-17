#!/usr/bin/env python3
"""ink_line_lint — 台词.ink 台词层量化门禁（chapter-dialoguer 段 2 自检，v1）

用法：
    python ink_line_lint.py <台词.ink> [--novel <同节小说.md>]

检查项（任一违规 exit 1，输出违规明细后就地修后重跑）：
  1. 旁白行长 > 25 字
  2. 旁白连续 ≥ 3 行
  3. 每场景块旁白行数 > say 行数
  4. 内心轨每场景块 > 3 行 / 全文 > 10 行（说话人以外的保留轨不判）
     —— 内心轨说话人通过 --inner <名字> 指定（换宿题材控制者轨），缺省「陆择」
  5. sfx 每场景块 > 1 / 全文 > 3 / 描述 > 10 字
  6. 搬运率：--novel 给定时，旁白+内心轨行与小说原句连续重叠 ≥10 字的行占比 > 15%
     （重叠 = 该行文本与小说任一句的最长公共子串，句按 。！？；\n 切）

纯 stdlib；只读，不改任何文件。说话人轨名由行首「名:」识别（半角冒号）。
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

NARRATOR = "旁白"
SFX = "sfx"
KNOT_RE = re.compile(r"^===\s+(\S+)")
SPEAK_RE = re.compile(r"^([^/=\-*+>\s][^:]{0,20}):(.*)$")


def split_blocks(lines):
    blocks, cur = [], None
    for ln in lines:
        m = KNOT_RE.match(ln)
        if m:
            cur = {"id": m.group(1), "rows": []}
            blocks.append(cur)
        elif cur is not None:
            cur["rows"].append(ln)
    return blocks


def parse_rows(lines):
    rows = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("//"):
            continue
        m = SPEAK_RE.match(s)
        if m:
            rows.append({"no": i + 1, "who": m.group(1).strip(), "text": m.group(2)})
        elif s.startswith("bed+") or s.startswith("bed-"):
            rows.append({"no": i + 1, "who": "bed", "text": s})
    return rows


def sentences(novel_text):
    parts = re.split(r"[。！？；\n]", novel_text)
    return [p for p in (p.strip() for p in parts) if len(p) >= 10]


def max_overlap(text, sents):
    best = 0
    for s in sents:
        m = difflib.SequenceMatcher(None, text, s, autojunk=False).find_longest_match(
            0, len(text), 0, len(s))
        best = max(best, m.size)
        if best >= len(text):
            break
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ink")
    ap.add_argument("--novel")
    ap.add_argument("--inner", default="陆择")
    ap.add_argument("--max-narr-len", type=int, default=25)
    ap.add_argument("--max-sfx-per-block", type=int, default=1)
    ap.add_argument("--max-sfx-total", type=int, default=3)
    ap.add_argument("--max-sfx-desc", type=int, default=10)
    ap.add_argument("--max-inner-per-block", type=int, default=3)
    ap.add_argument("--max-inner-total", type=int, default=10)
    ap.add_argument("--max-overlap-ratio", type=float, default=0.15)
    a = ap.parse_args()

    lines = Path(a.ink).read_text(encoding="utf-8").splitlines()
    blocks = split_blocks(lines)
    if not blocks:
        print("FAIL: 未发现任何 === 场景块")
        return 1
    sents = sentences(Path(a.novel).read_text(encoding="utf-8")) if a.novel else []

    errs = []
    n_narr_total = n_inner_total = n_sfx_total = 0
    moved, moved_hit = [], 0
    for b in blocks:
        rows = parse_rows(b["rows"])
        narr = [r for r in rows if r["who"] == NARRATOR]
        inner = [r for r in rows if r["who"] == a.inner]
        sfx = [r for r in rows if r["who"] == SFX]
        says = [r for r in rows if r["who"] not in (NARRATOR, SFX, a.inner, "bed")]
        n_narr_total += len(narr); n_inner_total += len(inner); n_sfx_total += len(sfx)
        for r in narr:
            if len(r["text"]) > a.max_narr_len:
                errs.append(f"L{r['no']} 旁白超长({len(r['text'])}字): {r['text'][:30]}…")
        run = 0
        for r in rows:
            run = run + 1 if r["who"] == NARRATOR else 0
            if run >= 3:
                errs.append(f"L{r['no']} 旁白连续≥3行"); run = 0
        if narr and len(narr) > len(says):
            errs.append(f"块{b['id']} 旁白行数({len(narr)}) > say行数({len(says)})")
        if len(inner) > a.max_inner_per_block:
            errs.append(f"块{b['id']} 内心轨{len(inner)}行 > {a.max_inner_per_block}")
        if len(sfx) > a.max_sfx_per_block:
            errs.append(f"块{b['id']} sfx{len(sfx)}个 > {a.max_sfx_per_block}")
        for r in sfx:
            if len(r["text"]) > a.max_sfx_desc:
                errs.append(f"L{r['no']} sfx描述超长({len(r['text'])}字): {r['text']}")
        for r in narr + inner:
            moved.append(r)
            if sents and max_overlap(r["text"], sents) >= 10:
                moved_hit += 1
                errs.append(f"L{r['no']} 搬运(≥10字重叠): {r['text'][:24]}…")
    if n_inner_total > a.max_inner_total:
        errs.append(f"全文内心轨{n_inner_total}行 > {a.max_inner_total}")
    if n_sfx_total > a.max_sfx_total:
        errs.append(f"全文sfx{n_sfx_total}个 > {a.max_sfx_total}")

    ratio = (moved_hit / len(moved)) if moved else 0.0
    print(f"块 {len(blocks)} · 旁白 {n_narr_total} · 内心轨({a.inner}) {n_inner_total} · "
          f"sfx {n_sfx_total} · 搬运率 {ratio:.0%}（限 {a.max_overlap_ratio:.0%}）")
    if ratio > a.max_overlap_ratio and not any("搬运(" in e for e in errs):
        errs.append(f"搬运率 {ratio:.0%} 超限")
    if errs:
        print(f"FAIL: {len(errs)} 项违规")
        for e in errs:
            print(" ", e)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
