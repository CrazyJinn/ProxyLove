"""step4_time_gen.py — 存量时间字段 → 'yyyy-MM-dd HH:mm:ss'（自时间锚点推算）的换算生成器。

只读查询 → 规则换算 → 产 step4_time_sets.cypher（显式逐条 SET，文件本身即 old→new 逆向映射日志，
可重放还原）+ step4_复核清单.md（无法自动换算的条目）。

换算规则（与 游戏概览.md「时间锚点」注一致）：
  Day N            → 锚点 + N 天 12:00:00
  Day N <时段>     → 锚点 + N 天 <时段小时>:00:00（清晨06/上午09/下午15/傍晚18/晚上20/深夜23/凌晨2）
  开场             → 锚点 − 1 天 12:00:00
  后日谈           → 锚点 + 31 天 12:00:00
  已是 yyyy-MM-dd… → 保留日期，补 12:00:00（已是完整 datetime 则不动）
  其他/模糊        → 不改，进复核清单

用法（在 Asset/ 目录内）：
  python "02_剧情数据/叙事基础重构迁移-20261013/step4_time_gen.py" --anchor '2024-06-01 22:00:00'
"""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta

_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".claude", "scripts"))
if os.path.isdir(_SCRIPTS_DIR):
    sys.path.insert(0, _SCRIPTS_DIR)

from cypher_exec import create_client  # noqa: E402

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

PERIOD_HOURS = {"清晨": 6, "上午": 9, "下午": 15, "傍晚": 18, "晚上": 20, "深夜": 23, "凌晨": 2}
FMT = "%Y-%m-%d %H:%M:%S"
_DAY_RE = re.compile(r"^Day\s*(\d+)\s*(.*)$")


def convert(val: str, anchor: datetime):
    """返回 (new_value | None, reason)。None = 进复核清单。"""
    s = (val or "").strip()
    if not s:
        return None, "空值"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", s):
        return s, "已是 datetime 格式"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s + " 12:00:00", "日期补默认时刻"
    if s == "开场":
        return (anchor - timedelta(days=1)).strftime("%Y-%m-%d") + " 12:00:00", "开场=锚点−1天"
    if s == "后日谈":
        return (anchor + timedelta(days=31)).strftime("%Y-%m-%d") + " 12:00:00", "后日谈=锚点+31天"
    m = _DAY_RE.match(s)
    if m:
        n = int(m.group(1))
        rest = m.group(2).strip()
        day = (anchor + timedelta(days=n)).strftime("%Y-%m-%d")
        for word, hour in PERIOD_HOURS.items():
            if word in rest:
                return f"{day} {hour:02d}:00:00", f"Day {n} {word}={hour}点"
        return f"{day} 12:00:00", f"Day {n} 无时段词默认 12:00"
    return None, "无法识别的格式"


def esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace("'", "\\'")


def _note(old: str) -> str:
    return str(old).replace("'", "").replace("\n", " ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", required=True, help="时间锚点 Day 0 绝对时刻 'yyyy-MM-dd HH:mm:ss'")
    args = ap.parse_args()
    anchor = datetime.strptime(args.anchor, FMT)

    client = create_client()

    node_rows = client.run(
        "MATCH (n) WHERE (n:Event OR n:Choice) AND n.time IS NOT NULL "
        "RETURN n.id AS id, labels(n)[0] AS label, n.time AS t"
    )
    edge_rows = client.run(
        "MATCH (a)-[r]->(b) WHERE "
        "(type(r)='link' AND r.time IS NOT NULL) OR "
        "((type(r)='relation' OR type(r)='at') AND (r.start_time IS NOT NULL OR r.end_time IS NOT NULL)) "
        "RETURN a.id AS fid, b.id AS tid, type(r) AS et, r.time AS t, "
        "r.start_time AS st, r.end_time AS en"
    )

    sets, review = [], []
    for r in node_rows:
        new, reason = convert(r["t"], anchor)
        if new is None:
            review.append(f"{r['label']} {r['id']} time='{r['t']}' —— {reason}")
        elif new != r["t"]:
            sets.append(
                f"MATCH (n:{r['label']} {{id: '{esc(r['id'])}'}}) "
                f"SET n.time = '{new}';  // was '{_note(r['t'])}' ({reason})"
            )
    for r in edge_rows:
        for prop, old in (("time", r["t"]), ("start_time", r["st"]), ("end_time", r["en"])):
            if old is None:
                continue
            new, reason = convert(old, anchor)
            if new is None:
                review.append(f"{r['et']} {r['fid']}->{r['tid']} {prop}='{old}' —— {reason}")
            elif new != old:
                sets.append(
                    f"MATCH (a {{id: '{esc(r['fid'])}'}})-[r:{r['et']}]->(b {{id: '{esc(r['tid'])}'}}) "
                    f"SET r.{prop} = '{new}';  // was '{_note(old)}' ({reason})"
                )

    with open(os.path.join(OUT_DIR, "step4_time_sets.cypher"), "w", encoding="utf-8") as f:
        f.write("\n".join(sets) + "\n")
    with open(os.path.join(OUT_DIR, "step4_复核清单.md"), "w", encoding="utf-8") as f:
        f.write("# step4 复核清单（无法自动换算，需人工定值）\n\n")
        f.write("\n".join(review) if review else "（无——全部自动换算）\n")
    print(f"生成 {len(sets)} 条 SET 语句；复核清单 {len(review)} 条")
    print("产物：step4_time_sets.cypher / step4_复核清单.md")


if __name__ == "__main__":
    main()
