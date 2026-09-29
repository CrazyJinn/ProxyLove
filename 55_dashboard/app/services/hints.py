"""hints.py — 推进指令生成 + 门控判断（纯函数，可单测）。

设计文档 §3.3：管理页不执行生产，只生成可复制指令文本（用户粘贴给 agent 会话）。
门控规则照抄 README：单节「推进此节」= ch.status==11 且该节产物链未全就绪且无待审项。
"""

from __future__ import annotations


def char_chain_hint(char_name: str, ap, ls, vd, costumes: list, sheets: list) -> str:
    """角色链推进指令。ap/ls/vd = 三数据节点 status 或 None（缺节点）；costumes/sheets = [{name,status}]。"""
    todo = []
    for label, st in (("AppearanceStyle", ap), ("LanguageStyle", ls)):
        if st in (None, -1, 0):
            todo.append(label)
    if any(c.get("status") in (-1, 0, None) for c in costumes):
        todo.append("CostumeStyle")
    if vd in (None, -1, 0):
        todo.append("VoiceDesign")
    if vd == 10:
        return "⏸ 声音设计待审：先到审批中心试听采用/批准，再推下游"
    if any(s.get("status") in (-1, 0) for s in sheets):
        todo.append("DesignSheet")
    if todo:
        return f'请运行 char-design 编排：角色「{char_name}」'
    return f'角色「{char_name}」基础链就绪（下游立绘按剧情需要由 plot-design 推进）'


def scene_chain_hint(loc_name: str, scenes: list) -> str:
    """场景链：任一 Scene/SceneLayer/BgmTrack 未就绪即建议跑 scene-design。"""
    for s in scenes:
        if s.get("status") in (-1, 0, None):
            return f'请运行 scene-design 编排：地点「{loc_name}」'
        for ly in s.get("layers", []):
            if ly.get("status") in (-1, 0):
                return f'请运行 scene-design 编排：地点「{loc_name}」'
        bgm = s.get("bgm")
        if bgm and bgm.get("status") in (-1, 0, 1):
            if bgm["status"] == 1:
                return f'🎵 等你手动生成 BGM wav 归档：{bgm.get("audio_path") or f"13_BGM/{bgm.get(name)}.wav"}'.replace(
                    "{name}", bgm.get("name", "")
                ) if False else f'🎵 等你手动生成 BGM wav 归档 13_BGM/{bgm.get("name")}.wav（bgm-designer 已出描述）'
            return f'请运行 scene-design 编排：地点「{loc_name}」（补 BGM 缺口）'
    return f'地点「{loc_name}」场景链就绪'


def chapter_ready(ch_status, secs: list) -> bool:
    """全章就绪 = ch=11 ∧ 各节 (ol=1 ∧ sc=11 ∧ 行全11)。立绘另查。"""
    if ch_status != 11:
        return False
    return all(s["ol_ok"] and s["sc_ok"] and s["lines_ok"] >= s["lines_total"] > 0 or
               (s["ol_ok"] and s["sc_ok"] and s["lines_total"] == 0 is not None and s["lines_total"] == 0)
               for s in secs) if False else all(
        s["ol_ok"] and s["sc_ok"] and (s["lines_total"] == 0 or s["lines_ok"] >= s["lines_total"])
        for s in secs
    )


def section_gate(ch_status: int, ol_ok: bool, sc_status, lines_ok: int, lines_total: int) -> dict:
    """单节「推进此节」门控 + 卡点描述。

    返回 {can_advance, button, blocker}：can_advance=按钮是否出现；
    blocker=未全就绪时的卡点描述（None=已就绪）。
    """
    done = ol_ok and sc_status == 11 and (lines_total == 0 or lines_ok >= lines_total)
    if done:
        return {"can_advance": False, "button": "✅ 就绪", "blocker": None}
    if ch_status != 11:
        return {"can_advance": False, "button": "—", "blocker": "章结构未批"}
    blocker = None
    if sc_status == 10:
        blocker = "定稿待审 → 审批中心"
    elif sc_status in (-1, 0, 1) and ol_ok:
        blocker = f"定稿未就绪（sc={sc_status}）"
    elif not ol_ok:
        blocker = "提纲未就绪"
    elif lines_ok < lines_total:
        blocker = f"行音频 {lines_ok}/{lines_total}"
    can = blocker is None or not (sc_status == 10)  # 有待审项不出按钮
    return {
        "can_advance": bool(can and ch_status == 11 and sc_status != 10),
        "button": "推进此节" if can and sc_status != 10 else "⏸ 待审",
        "blocker": blocker,
    }


def section_hint(sec_id: str, sec_title: str) -> str:
    return f"请运行 plot-design 编排（单节聚焦）：section_id={sec_id}（{sec_title}）"


def chapter_hint(ch_title: str) -> str:
    return f'请运行 plot-design 编排：章节「{ch_title}」（全量推进到全章就绪，不发布）'


def stand_hint(stand_id: str) -> str:
    return f"请直调 char-stand-designer {stand_id}（基于已批 IllusDesign 出立绘变体）"


def scene_hint_text(loc_name: str) -> str:
    return f'请运行 scene-design 编排：地点「{loc_name}」'
