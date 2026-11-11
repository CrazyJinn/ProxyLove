"""fingerprint.py — 小说.md 取材指纹的生成与自检(生成与自检同源,杜绝双入口不一致)。

归一化规则(改这里 = 改所有已产小说的新鲜度判据,慎动;已落盘小说需重产指纹):
  Event: '|'.join(title, time, type, description, ending_kind, condition)
  Hook/Lore(旧 info/fact): '|'.join(title, content, knowledge_level)
  每字段 strip,None/缺失 → 空串;整体 utf-8 后 sha256 取前 16 位 hex。

素材 JSON 输入(cypher_exec --json 的查询产物,数组;行内 kind 或 label 二选一):
  [{"kind":"event","id":"…","title":"…",…},
   {"kind":"lore","id":"…","title":"…","content":"…","knowledge_level":3,"intensity":"E"}]
  kind 兼容旧值 info/fact(拆分前存量形态);intensity 可选 E/S(缺省 E)。

用法:
  gen   产完整头部块(含 <!-- --> 包裹,直接嵌入小说.md 头部);--ids 只圈**实际取用**的素材子集
        (指纹=「使用的」而非「圈定的全部」,无关素材修订不误 stale 本节)。
        --ids 条目可带强度后缀 `id:E` / `id:S`(hook/lore 行;裸 id 缺省 E,event 行忽略强度):
        python fingerprint.py gen --in materials.json [--ids id1:E,id2:S,…]   # 或 stdin 传 JSON
  check 自检小说.md 头部清单 vs 当前素材:退出码 0=新鲜 / 1=stale(stdout 报告明细):
        python fingerprint.py check --novel 小说.md --in materials.json
        stale 判定 = 已记素材 hash 不等 / 已记素材被删;圈定内未标注的不算 stale(未使用是常态)
        kind 容错:头部 info 行 vs 素材 fact/lore 行(或反之)按同字段指纹比对不算 stale——
        Hook/Lore label 拆分迁移期的多形态兼容。
  consumed 扫描 root 下全部小说.md 指纹头部的 info/fact/lore 行,输出「id → 消费它的小说路径列表」
        JSON 映射(裸映射,调度/对账用)。--ids 只查给定子集:
        python fingerprint.py consumed [--root 25_剧本] [--ids id1,…]
  freshness 新鲜度计算(Lore 新鲜度算法,2026-11-11 方案):
        对 --in 素材中的每条 hook/lore,按「最近一次消费点 → --at 节」的间隔 Δ 算
        R = base × 2^(−Δ/h)(上次消费 E:base=1.0 / S:base=S_RESET),F = round(100×(1−R)),
        并给允许档位 explicit/side/blocked。--at 接受 chNN/secMM 相对形态或小说.md 路径:
        python fingerprint.py freshness --in materials.json --at ch02/sec06 [--root 25_剧本]

新鲜度参数表(方案定稿;改这里 = 全部小说的裁量档位变):
  BASE=100  S_RESET=0.6  H_BY_KL={1:12, 2:6, 3:3}  档位 F≥70 正面可 / ≥30 仅侧面 / <30 禁释放
  全局阅读序 = 目录序 chNN/secMM;自由节(自由节/secMM,无章位次)排在全部已组章节之后(按 mtime),
  其作为消费点 Δ 按 0 计(不给恢复);旧指纹头无强度标记 → 视为 E(保守)。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys

KIND_FIELDS: dict[str, tuple[str, ...]] = {
    "event": ("title", "time", "type", "description", "ending_kind", "condition"),
    # info/fact 为旧形态别名(拆分前);指纹字段集相同
    "hook": ("title", "content", "knowledge_level"),
    "fact": ("title", "content", "knowledge_level"),  # 旧值等价
    "lore": ("title", "content", "knowledge_level"),
    "info": ("title", "content", "knowledge_level"),
}
# freshness 管制对象(fact 仅兜底,lore 为主);event 不参与
FRESHNESS_KINDS = {"hook", "fact", "lore", "info"}

# ── 新鲜度参数表(集中一处,改这里全生效) ──────────────────────────────
F_BASE = 100          # 百分制基准
S_RESET = 0.6         # 侧面消费后的记忆基线(正面重置到 1.0)
H_BY_KL = {1: 12, 2: 6, 3: 3}   # kl → 半衰期(节)
F_ALLOW_EXPLICIT = 70  # F ≥ 此值:正面/侧面均可
F_ALLOW_SIDE = 30      # F ≥ 此值:仅侧面;再低禁释放

HEADER_OPEN = "<!-- 取材指纹(chapter-novelist 生成,chapter-dialoguer 自检;变动=重写小说+作废定稿)"
HEADER_RE = re.compile(r"^(event|info|fact|hook|lore)\s+(\S+)\s+([0-9a-f]{16})(?:\s+([ES]))?\s*(.*)$")
PATH_ORDER_RE = re.compile(r"(?:^|/)(ch(\d+))(?:/|\\)(sec(\d+))")
FREE_RE = re.compile(r"(?:^|/)自由节(?:/|\\)(sec(\d+))")


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
            continue  # 容错跳过非 Event/Hook/Lore 行(圈定查询可能带出别的列)
        out.append(row)
    return out


def _line(kind: str, row: dict, fp: str, intensity: str | None = None) -> str:
    pad = " " if kind in ("event", "fact", "hook") else "  "  # event/fact/hook 与 info/lore 等宽对齐
    tok = f" {intensity}" if (intensity and kind in ("hook", "fact", "lore")) else ""
    return f"{kind}{pad} {row['id']} {fp}{tok} {str(row.get('title') or '')}"


def cmd_gen(rows: list[dict], ids: dict[str, str] | None) -> int:
    if ids is not None:
        want = set(ids)
        have = {str(r["id"]) for r in rows}
        missing = want - have
        if missing:
            raise SystemExit(f"--ids 指定的素材不在输入 JSON 中: {sorted(missing)}")
        rows = [r for r in rows if str(r["id"]) in want]
    if not rows:
        raise SystemExit("素材为空:圈定查询未命中任何 Event/Hook/Lore(或 --ids 过滤后为空)")
    lines = [HEADER_OPEN]
    for row in rows:
        kind = _kind(row)
        assert kind is not None  # _materials 已滤
        intensity = None
        if kind in ("fact", "hook", "lore"):
            if ids is not None:
                intensity = ids.get(str(row["id"]), "E")
            else:
                intensity = str(row.get("intensity") or "E").upper()
            if intensity not in ("E", "S"):
                intensity = "E"
        lines.append(_line(kind, row, fingerprint(row), intensity))
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


def _equiv_kind(kind: str) -> str:
    """info/fact/lore 在指纹内容比对上等价(同字段集)——label 迁移期双形态兼容。"""
    return "info-like" if kind in ("info", "fact", "hook", "lore") else kind


def cmd_check(rows: list[dict], novel_path: str) -> int:
    current = {(_equiv_kind(_kind(r) or ""), str(r["id"])): fingerprint(r) for r in rows}
    old = {}
    for kind, sid, fp in _header_rows(open(novel_path, encoding="utf-8").read()):
        old[(_equiv_kind(kind), sid)] = fp

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


def cmd_consumed(root: str, ids: set[str] | None) -> int:
    """扫描 root 下全部 小说.md 指纹头部,汇总 id → 消费路径列表。"""
    import glob
    import os

    novels = sorted(glob.glob(os.path.join(root, "**", "小说.md"), recursive=True))
    mapping: dict[str, list[str]] = {}
    for path in novels:
        try:
            rows = _header_rows(open(path, encoding="utf-8").read())
        except SystemExit:
            continue  # 无指纹块的旧流程小说(如 ch00 存档)跳过
        for kind, sid, _fp in rows:
            if kind not in FRESHNESS_KINDS:
                continue
            mapping.setdefault(sid, []).append(path.replace("\\", "/"))
    if ids is not None:
        mapping = {k: v for k, v in mapping.items() if k in ids}
    print(json.dumps(mapping, ensure_ascii=False, indent=2))
    return 0


# ── freshness:全局节序 + 指数衰减 ────────────────────────────────────

def _sec_order_key(path: str, free_mtime: dict[str, float]):
    """小说路径 → 全局排序键。chNN/secMM → (0, NN, MM);自由节 → (1, mtime, sec) 排全部章节后。"""
    p = path.replace("\\", "/")
    m = PATH_ORDER_RE.search(p)
    if m:
        return (0, int(m.group(2)), int(m.group(4)))
    f = FREE_RE.search(p)
    if f:
        return (1, free_mtime.get(p, 0.0), int(f.group(2)))
    return None


def _header_rows_full(novel_text: str) -> list[tuple[str, str, str, str | None]]:
    """同 _header_rows,但带强度标记(无标记的旧头返回 None → 按 E 处理)。"""
    m = re.search(r"<!--\s*取材指纹.*?-->", novel_text, re.S)
    if not m:
        raise SystemExit("无指纹块")
    out = []
    for line in m.group(0).splitlines():
        hit = HEADER_RE.match(line.strip())
        if hit:
            out.append((hit.group(1), hit.group(2), hit.group(3), hit.group(4)))
    return out


def cmd_freshness(rows: list[dict], root: str, at: str) -> int:
    import glob
    import os

    # --at 解析:chNN/secMM 或 小说.md 路径
    at_norm = at.replace("\\", "/")
    if not at_norm.endswith("小说.md"):
        at_norm = at_norm.rstrip("/") + "/小说.md"
    at_key = _sec_order_key(at_norm, {})
    if at_key is None:
        raise SystemExit(f"--at 无法解析节位次(须 chNN/secMM 或其小说.md 路径): {at}")

    novels = sorted(glob.glob(os.path.join(root, "**", "小说.md"), recursive=True))
    free_mtime = {}
    for p in novels:
        pn = p.replace("\\", "/")
        if _sec_order_key(pn, {}) is None:
            free_mtime[pn] = os.path.getmtime(pn)

    # 消费事件:id → [(order_key, path, intensity)](仅 FRESHNESS_KINDS;旧头无标记按 E)
    events: dict[str, list[tuple[tuple, str, str]]] = {}
    for p in novels:
        pn = p.replace("\\", "/")
        key = _sec_order_key(pn, free_mtime)
        if key is None:
            continue  # 目录形态外的小说不参与排序
        try:
            hrows = _header_rows_full(open(p, encoding="utf-8").read())
        except (SystemExit, OSError):
            continue
        for kind, sid, _fp, inten in hrows:
            if kind not in FRESHNESS_KINDS:
                continue
            events.setdefault(sid, []).append((key, pn, inten or "E"))

    want = {str(r["id"]): r for r in rows if _kind(r) in FRESHNESS_KINDS}
    out = {}
    for sid, row in want.items():
        kl = row.get("knowledge_level")
        h = None
        if kl is not None and str(kl).strip().lstrip("-").isdigit():
            h = H_BY_KL.get(int(kl))
        priors = sorted((k, p, i) for k, p, i in events.get(sid, []) if k < at_key)
        if not priors or h is None:
            note = "从未消费,无限制" if not priors else "kl 缺失/非法,按无限制处理"
            out[sid] = {"kind": _kind(row), "kl": kl, "h": h, "title": row.get("title"),
                        "last": None, "delta": None, "F": F_BASE, "allow": "explicit", "note": note}
            continue
        lkey, lpath, inten = priors[-1]
        # Δ:同章节数差;跨章按章差近似;消费点在自由节(章位 ∞)或目标为自由节 → Δ=0(不给恢复)
        if at_key[0] == 1:
            delta = 0
        elif lkey[0] == 1:
            delta = 0
        elif at_key[1] == lkey[1]:
            delta = at_key[2] - lkey[2]
        else:
            delta = at_key[1] - lkey[1]
        base = 1.0 if inten == "E" else S_RESET
        r = base * (2 ** (-delta / h))
        f = max(0, min(F_BASE, round(F_BASE * (1 - r))))
        allow = "explicit" if f >= F_ALLOW_EXPLICIT else ("side" if f >= F_ALLOW_SIDE else "blocked")
        out[sid] = {"kind": _kind(row), "kl": kl, "h": h, "title": row.get("title"),
                    "last": {"path": lpath, "intensity": inten}, "delta": delta,
                    "R": round(r, 4), "F": f, "allow": allow}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("gen", "check", "consumed", "freshness"):
        p = sub.add_parser(name)
        if name in ("gen", "check", "freshness"):
            p.add_argument("--in", dest="infile", help="素材 JSON 文件;缺省读 stdin")
        if name == "check":
            p.add_argument("--novel", required=True, help="小说.md 路径")
        elif name == "gen":
            p.add_argument("--ids", help="逗号分隔素材 id,可带强度后缀 id:E/id:S(缺省 E);只圈实际取用子集")
        elif name == "consumed":
            p.add_argument("--root", default="25_剧本", help="扫描根目录(递归找 小说.md)")
            p.add_argument("--ids", help="逗号分隔的 id 列表——只查给定子集")
        else:  # freshness
            p.add_argument("--at", required=True, help="目标节位次:chNN/secMM 或其 小说.md 路径")
            p.add_argument("--root", default="25_剧本", help="扫描根目录(递归找 小说.md)")
    args = ap.parse_args()
    if args.cmd == "consumed":
        ids = set(s.strip() for s in args.ids.split(",")) if args.ids else None
        return cmd_consumed(args.root, ids)
    text = open(args.infile, encoding="utf-8").read() if args.infile else sys.stdin.read()
    rows = _materials(text)
    if args.cmd == "gen":
        ids: dict[str, str] = {}
        if args.ids:
            for part in args.ids.split(","):
                part = part.strip()
                if not part:
                    continue
                if ":" in part:
                    sid, inten = part.rsplit(":", 1)
                    ids[sid.strip()] = inten.strip().upper()
                else:
                    ids[part] = "E"
        return cmd_gen(rows, ids)
    if args.cmd == "freshness":
        return cmd_freshness(rows, args.root, args.at)
    return cmd_check(rows, args.novel)


if __name__ == "__main__":
    sys.exit(main())
