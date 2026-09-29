"""ink.py — 台词.ink 服务端轻量着色（定稿审批渲染用）。

按 ink 方言规范 v3 的行型表做行分类；只读展示用途，**不是** script_splitter
（拆分进图的机器侧权威在原项目 .claude/skills/section-voice-publisher/scripts/script_splitter.py）。
"""

from __future__ import annotations

import re

BED_START_RE = re.compile(r"^bed\+\s+([A-Za-z0-9_]+)\s*(?://\s*(.*))?$")
BED_END_RE = re.compile(r"^bed-\s+([A-Za-z0-9_]+)\s*$")
STITCH_RE = re.compile(r"^=\s*(\S+)\s*$")
CHOICE_RE = re.compile(r"^[*+]\s+(.*?)(?:\s*->\s*(\S+)(?:\s*//\s*(.*))?)?$")
BLOCK_RE = re.compile(r"^===\s+(\S+)(?:\s*//\s*(.*))?$")
ENDING_RE = re.compile(r"^(.*?)\s*#\s*ending:\s*(\w+)\s*$")
SAY_RE = re.compile(r"^([^:]{1,20}?)::?(.+)$")  # 角色名:台词（半角冒号）

PREFIXES = ("旁白:", "sfx:", "llm:")


def classify_line(raw: str) -> dict:
    """一行 → {cls, label, text}。cls ∈ comment/block/say/narrate/sfx/llm/
    bed_start/bed_end/label/choice/ending/end/blank/text。"""
    line = raw.rstrip("\n")
    s = line.strip()
    if not s:
        return {"cls": "blank", "label": "", "text": ""}
    if s.startswith("//"):
        return {"cls": "comment", "label": "注释", "text": s}
    if s.startswith("==="):
        m = BLOCK_RE.match(s)
        return {"cls": "block", "label": m.group(1) if m else s, "text": m.group(2) or "" if m else ""}
    if s.startswith("bed+"):
        m = BED_START_RE.match(s)
        return {"cls": "bed_start", "label": m.group(1) if m else "?", "text": m.group(2) or "" if m else ""}
    if s.startswith("bed-"):
        m = BED_END_RE.match(s)
        return {"cls": "bed_end", "label": m.group(1) if m else "?", "text": ""}
    if s.startswith("sfx:"):
        return {"cls": "sfx", "label": "音效", "text": s[4:].strip()}
    if s.startswith("llm:"):
        return {"cls": "llm", "label": "占位", "text": s[4:].strip()}
    if s.startswith("旁白:"):
        return {"cls": "narrate", "label": "旁白", "text": s[3:].strip()}
    if s.startswith("-> END"):
        return {"cls": "end", "label": "收束", "text": ""}
    if s.startswith("->"):
        return {"cls": " divert", "label": "跳转", "text": s[2:].strip()}
    if s.startswith("="):
        m = STITCH_RE.match(s)
        return {"cls": "label", "label": m.group(1) if m else s, "text": ""}
    if s[0] in "*+":
        m = CHOICE_RE.match(s)
        return {"cls": "choice", "label": "选项", "text": s}
    m = ENDING_RE.match(s)
    if m:
        return {"cls": "ending", "label": f"结局 {m.group(2)}", "text": m.group(1)}
    m = SAY_RE.match(s)
    if m and not s.startswith(("=", "*", "+", "->")):
        who, text = m.group(1).strip(), m.group(2).strip()
        if who not in ("sfx", "llm", "旁白") and ":" in line:
            return {"cls": "say", "label": who, "text": text}
    return {"cls": "text", "label": "", "text": s}


def render_ink(source: str) -> list[dict]:
    """全文 → 分类行列表（模板逐行渲染）。"""
    out = []
    cur_block = ""
    for raw in source.splitlines():
        item = classify_line(raw)
        if item["cls"] == "block":
            cur_block = item["label"]
        item["block"] = cur_block
        out.append(item)
    return out


def llm_placeholder_count(source: str) -> int:
    """llm: 占位行计数（split 门禁：含占位不能拆分）。"""
    return sum(1 for ln in source.splitlines() if ln.strip().startswith("llm:"))
