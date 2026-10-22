"""fingerprint.py — 小说.md 取材指纹的生成与自检(生成与自检同源,杜绝双入口不一致)。

归一化规则(改这里 = 改所有已产小说的新鲜度判据,慎动;已落盘小说需重产指纹):
  Event: '|'.join(title, time, type, description, ending_kind, condition)
  Info : '|'.join(title, content, knowledge_level)
  每字段 strip,None/缺失 → 空串;整体 utf-8 后 sha256 取前 16 位 hex。

素材 JSON 输入(cypher_exec --json 的查询产物,数组;行内 kind 或 label 二选一):
  [{"kind":"event","id":"…","title":"…","time":"…","type":"…","description":"…","ending_kind":"","condition":""},
   {"kind":"info","id":"…","title":"…","content":"…","knowledge_level":2}]

用法:
  gen   产完整头部块(含 <!-- --> 包裹,直接嵌入小说.md 头部);--ids 只圈**实际取用**的素材子集
        (指纹=「使用的」而非「圈定的全部」,无关素材修订不误 stale 本节):
        python fingerprint.py gen --in materials.json [--ids id1,id2,…]   # 或 stdin 传 JSON
  check 自检小说.md 头部清单 vs 当前素材:退出码 0=新鲜 / 1=stale(stdout 报告明细):
        python fingerprint.py check --novel 小说.md --in materials.json
        stale 判定 = 已记素材 hash 不等 / 已记素材被删;圈定内未标注的不算 stale(未使用是常态)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys

KIND_FIELDS: dict[str, tuple[str, ...]] = {
    "event": ("title", "time", "type", "description", "ending_kind", "condition"),
    "info": ("title", "content", "knowledge_level"),
}

HEADER_OPEN = "<!-- 取材指纹(chapter-novelist 生成,chapter-dialoguer 自检;变动=重写小说+作废定稿)"
HEADER_RE = re.compile(r"^(event|info)\s+(\S+)\s+([0-9a-f]{16})\s*(.*)$")


def _kind(row: dict) -> str | None:
    k = str(row.get("kind") or row.get("label") or "").strip().lower()
    return k if k in KIND_FIELDS else None


def fingerprint(row: dict) -> str:
    kind = _kind(row)
    if kind is None:
        raise ValueError(f"未知素材 kind/label: {row!r}")
    norm = "|".join("" if row.get(f) is None else str(row.get(f)).strip() for f in KIND_FIELDS[kind])
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _materials(text: str) -> list[dict]:
    rows = json.loads(text)
    if not isinstance(rows, list):
        raise SystemExit("素材 JSON 顶层必须是数组(cypher_exec --json 单语句输出)")
    out = []
    for row in rows:
        if _kind(row) is None or not row.get("id"):
            continue  # 容错跳过非 Event/Info 行(圈定查询可能带出别的列)
        out.append(row)
    return out


def _line(kind: str, row: dict, fp: str) -> str:
    pad = " " if kind == "event" else "  "  # event/info 等宽对齐
    return f"{kind}{pad} {row['id']} {fp} {str(row.get('title') or '')}"


def cmd_gen(rows: list[dict], ids: set[str] | None) -> int:
    if ids is not None:
        rows = [r for r in rows if str(r["id"]) in ids]
        missing = ids - {str(r["id"]) for r in rows}
        if missing:
            raise SystemExit(f"--ids 指定的素材不在输入 JSON 中: {sorted(missing)}")
    if not rows:
        raise SystemExit("素材为空:圈定查询未命中任何 Event/Info(或 --ids 过滤后为空)")
    lines = [HEADER_OPEN]
    for row in rows:
        lines.append(_line(_kind(row), row, fingerprint(row)))
    lines.append("-->")
    print("\n".join(lines))
    return 0


def _header_rows(novel_text: str) -> list[tuple[str, str, str]]:
    """解析小说.md 头部取材指纹块(第一个 <!-- 取材指纹 … --> 之间)。"""
    m = re.search(r"<!--\s*取材指纹.*?-->", novel_text, re.S)
    if not m:
        raise SystemExit("小说.md 头部未找到「取材指纹」块——旧版或手删,需重跑 chapter-novelist 重产")
    out = []
    for line in m.group(0).splitlines():
        hit = HEADER_RE.match(line.strip())
        if hit:
            out.append((hit.group(1), hit.group(2), hit.group(3)))
    return out


def cmd_check(rows: list[dict], novel_path: str) -> int:
    current = {(_kind(r), str(r["id"])): fingerprint(r) for r in rows}
    old = {}
    for kind, sid, fp in _header_rows(open(novel_path, encoding="utf-8").read()):
        old[(kind, sid)] = fp

    changed = [k for k, fp in old.items() if k in current and current[k] != fp]
    deleted = sorted(k for k in old if k not in current)

    if not (changed or deleted):
        print(f"新鲜:已记取材 {len(old)} 条素材指纹全部一致(圈定共 {len(current)} 条,未标注 {len(current) - len(old)} 条未使用属常态)")
        return 0
    print("STALE——需重跑 chapter-novelist(重写小说 + 作废定稿):")
    for kind, sid in changed:
        print(f"  变动  {kind} {sid}:头部 {old[(kind, sid)]} → 当前 {current[(kind, sid)]}")
    for kind, sid in deleted:
        print(f"  已删  {kind} {sid}:头部有、图上无")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("gen", "check"):
        p = sub.add_parser(name)
        p.add_argument("--in", dest="infile", help="素材 JSON 文件;缺省读 stdin")
        if name == "check":
            p.add_argument("--novel", required=True, help="小说.md 路径")
        else:
            p.add_argument("--ids", help="逗号分隔的素材 id 列表——只圈实际取用的子集(指纹=使用的,非圈定全部)")
    args = ap.parse_args()
    text = open(args.infile, encoding="utf-8").read() if args.infile else sys.stdin.read()
    rows = _materials(text)
    if args.cmd == "gen":
        ids = set(s.strip() for s in args.ids.split(",")) if args.ids else None
        return cmd_gen(rows, ids)
    return cmd_check(rows, args.novel)


if __name__ == "__main__":
    sys.exit(main())
