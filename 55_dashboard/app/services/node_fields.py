"""node_fields.py — 节点字段中文名（抄自 00_init/Schema/*.md 的「字段|中文」表）。"""

FIELD_ZH: dict[str, dict[str, str]] = {
    "Character": {
        "name": "姓名", "gender": "性别", "description": "简介", "birth_year": "出生年份",
        "character_tags": "人设标签", "color_direction": "配色逻辑", "priority": "优先级",
        "status": "流程状态",
    },
    "AppearanceStyle": {
        "name": "名称", "appearance": "外貌描述（综合气质/身高/观感）", "visual_tone": "视觉气质",
        "first_impression": "第一印象", "shape_language": "形状语言", "age_impression": "年龄感",
        "body_type": "体态", "skin_tone": "肤色", "ethnicity": "面孔/人种", "hair": "头发（发色+发型+发长）",
        "eye": "眼睛（瞳色+眼型）", "lip_shape": "唇形", "marks": "特殊标记", "height_cm": "身高cm",
        "status": "流程状态",
    },
    "LanguageStyle": {
        "name": "名称", "vocabulary": "词汇风格", "rhythm": "句子节奏", "habits": "语言习惯（口头禅等）",
        "emotion_patterns": "情绪模式（5 情境）", "description": "概要", "status": "流程状态",
    },
    "CostumeStyle": {
        "name": "着装名称", "outfit_style": "着装风格", "garment": "服装（材质+类型，多件分号）",
        "footwear": "鞋类", "accessory_type": "配饰类型", "status": "流程状态",
    },
    "VoiceDesign": {
        "name": "名称", "instruct": "声音设计指令（Qwen instruct）", "ref_text": "参考文本（统一长句）",
        "ref_audio_path": "参考音频路径", "candidates_path": "候选清单路径", "description": "概要",
        "status": "流程状态",
    },
    "DesignSheet": {
        "delta_notes": "改动说明（增量版本专用）", "active_from": "生效锚点 ch*1000+sec",
        "slug": "版本短名（路径段）", "prompt_path": "提示词文件", "image_path": "图片路径",
        "status": "流程状态",
    },
    "IllusDesign": {
        "adaptation_notes": "着装补充说明", "display_scale": "显示缩放", "prompt_path": "提示词文件",
        "image_path": "图片路径", "status": "流程状态",
    },
    "StandingIllustration": {
        "variant_label": "变体名（2~4字）", "description": "变体氛围（服务台词情境）",
        "eye": "眼部", "brow": "眉毛", "mouth": "嘴部", "head_angle": "头部角度",
        "hand": "手部动作", "foot": "脚部动作", "prompt_path": "提示词文件", "image_path": "图片路径",
        "status": "流程状态",
    },
    "Scene": {
        "name": "名称", "scene_type": "场景类型", "time_of_day": "时段", "weather": "天气",
        "atmosphere": "氛围", "composition": "构图", "lighting": "光影", "color_direction": "配色逻辑",
        "description": "概要", "status": "流程状态",
    },
    "SceneLayer": {
        "name": "名称", "layer_type": "图层类型", "prompt_path": "提示词文件", "image_path": "图片路径",
        "status": "流程状态",
    },
    "Location": {
        "name": "名称", "description": "描述",
    },
    "BgmTrack": {
        "name": "track 逻辑名（wav 文件名主体）", "description": "音乐定位描述（情绪/氛围）",
        "prompt": "生成提示词（供外部工具产 wav）", "audio_path": "音频归档路径",
        "mode": "播放模式 play/fade", "loop": "循环", "status": "流程状态",
    },
}

COMMON_ZH = {"id": "编号（雪花ID，勿改）", "name": "名称"}


def zh_of(label: str, key: str) -> str:
    return FIELD_ZH.get(label, {}).get(key) or COMMON_ZH.get(key) or key
