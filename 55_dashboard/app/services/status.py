"""status.py — NODE_STATUS 表 + 派生判断（对应原 55_dashboard/core/status.py）。

status 语义（README §1，全图统一）：
  -1 作废重做 │ 0 待处理/待生成 │ 1 数据完成/提示词完成 │ 2 图片完成 │ 10 待审 │ 11 批准
"""

from __future__ import annotations

# label → (completion, has_approval)；None = 无 status 语义（Section 纯编排容器）
NODE_STATUS: dict[str, tuple[int, bool]] = {
    # 数据节点（无审批，完成=1）
    "AppearanceStyle": (1, False),
    "LanguageStyle": (1, False),
    "CostumeStyle": (1, False),
    "Scene": (1, False),
    "SecOutline": (1, False),
    # 生产节点（有审批，完成=11）
    "DesignSheet": (11, True),
    "IllusDesign": (11, True),
    "StandingIllustration": (11, True),
    "SceneLayer": (11, True),
    "VoiceDesign": (11, True),
    "Chapter": (11, True),
    "SecScript": (11, True),
    "LineAudio": (11, True),
    # 特殊：BgmTrack 无审批但 completion=2（音频已归档）
    "BgmTrack": (2, False),
}

PRODUCTION_LABELS = {
    "DesignSheet", "IllusDesign", "StandingIllustration", "SceneLayer",
    "VoiceDesign", "Chapter", "SecScript", "LineAudio",
}
DATA_LABELS = {
    "Character", "Event", "Location", "Info", "Choice",
    "AppearanceStyle", "LanguageStyle", "CostumeStyle", "Scene", "SecOutline", "Section",
}
NARRATIVE_LABELS = {"Character", "Event", "Location", "Info", "Choice"}

STATUS_TEXT = {
    -1: "作废重做", 0: "待处理", 1: "已完成", 2: "图片完成",
    10: "待审", 11: "批准",
}
STATUS_CLASS = {
    -1: "st--1", 0: "st-0", 1: "st-1", 2: "st-2", 10: "st-10", 11: "st-11",
}


def status_text(st) -> str:
    if st is None:
        return "—"
    return STATUS_TEXT.get(st, f"?{st}")


def status_class(st) -> str:
    return STATUS_CLASS.get(st, "st-0")


def voice_design_substate(node: dict) -> str:
    """VoiceDesign status=10 的两态：candidates_path 非空 = 候选待选。"""
    if node.get("status") != 10:
        return ""
    return "candidates" if node.get("candidates_path") else "single"


def line_audio_ready(node: dict) -> bool:
    """行完成（音频审）：status=11。"""
    return node.get("status") == 11
