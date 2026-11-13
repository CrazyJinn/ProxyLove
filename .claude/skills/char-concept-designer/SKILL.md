---
name: char-concept-designer
description: |
  推进 AppearanceStyle / LanguageStyle 图节点：查询状态 → 生成外貌/语言设计内容 → 保存结果（MERGE 兜底建节点+边，写内容与 status）。
  CostumeStyle 由 char-costume-designer 负责。在需要设计角色外貌方向、生成语言风格、或概念节点 status=0 需推进时使用。
argument-hint: <char_id>
arguments:
  - char_id
allowed-tools: Read, Bash, Write, Edit
---

> **status=-1 = 作废重做**：当 AppearanceStyle/LanguageStyle 被 sync 级联重置为 `status=-1` 时，即使各属性已有值（本 skill 无外部文件，"产物"即图节点属性），也**必须重新生成并覆盖**。`-1` 与 `0` 都视为"需生成"起点；`-1` 明确表示旧内容作废，**禁止因属性已有值而跳过**。

# 角色概念设计

推进并写入 AppearanceStyle（外貌）和 LanguageStyle（语言风格）图节点。

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| char_id | 角色节点 ID（snowflake Base62） | 必传 |

## 流程（三段式：查状态 → 完成任务 → 保存结果）

### 1. 查询目标节点状态

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 查询角色 + 已有的 AppearanceStyle / LanguageStyle：

```cypher
MATCH (ch:Character {id: '<char_id>'})
OPTIONAL MATCH (ch)-[:has_appearance]->(app:AppearanceStyle)
OPTIONAL MATCH (ch)-[:has_voice_style]->(voice:LanguageStyle)
RETURN ch, app, voice
```

- **目标节点判定**：
  - 若 `app` 为空 → 生成新 snowflake id 作为 `APP_ID`，本次将新建；若存在 → `APP_ID = app.id`，按 status 决定起点（`-1`/`0` 需重做）。
  - `voice` 同理（怪物跳过，见下）。
- **角色类型判断**（决定是否生成 LanguageStyle）：

  | 角色类型 | AppearanceStyle | LanguageStyle |
  |---------|----------------|---------------|
  | 主角(char) / NPC | 完整版 | 生成 |
  | 怪物(enemy) | 简化版 | 不生成 |

### 2. 完成任务

LLM 按 [references/template-角色美术设定.md](references/template-角色美术设定.md) 与 [references/template-角色语言风格.md](references/template-角色语言风格.md) 生成设计内容。

**AppearanceStyle**（怪物用简化版）：

| 维度 | 属性 | 示例 | 说明 |
|------|------|------|------|
| 形状语言 | shape_language | 三角型 / 方型 / 倒三角 / 细长型 / 圆形 / 不对称 | 单选 |
| 年龄感 | age_impression | 少女 / 青年 / 成熟 / 御姐 / 正太 / 少年 | 单选 |
| 体态 | body_type | 曼妙 / 修长 / 健壮 / 娇小 / 丰腴 / 少年感 / 匀称 | 单选 |
| 肤色 | skin_tone | 象牙白 / 瓷白 / 苍白 / 蜜色 / 健康粉 / 小麦 / 古铜 | 单选 |
| 面孔/人种 | ethnicity | 中国面孔 / 日系面孔 / 韩系面孔 / 东南亚面孔 / 欧美面孔 / 中东面孔 / 非裔面孔 / 混血面孔 | 单选 |
| 头发 | hair | `深棕色大波浪长发` | 自由文本，需明确颜色、款式、长短 |
| 眼睛 | eye | `琥珀色上挑眼` | 自由文本，需明确颜色、眼型 |
| 唇形 | lip_shape | 薄唇 / 饱满 / 厚唇 / 微笑唇 | 单选 |
| 特殊标记 | marks | 无 / 疤痕 / 纹身 / 胎记 / 泪痣 | 可多选 |

**结构化字段纪律**：hair / eye / lip_shape / body_type / skin_tone / marks 等外貌字段只写**客观静态形态**（颜色、形状、长短、发质、固定标记）；禁止情绪/神态/动态/状态类描述（如「目光躲闪」「眼底含笑意」「眼神锐利」「说话时眉梢带动」）——此类只进 Character.vibe（气质归 Character.vibe 单一事实源）。固定佩戴物（眼镜等）归 marks 单一来源，不在 hair / eye 里重复。
例：✅「琥珀色上挑眼」 ❌「琥珀色上挑眼，眼神凌厉逼人」

**身高（height_cm）**：按角色设定身高直接写整数（供下游 IllusDesign 推算立绘显示缩放，见 char-illus-designer）。无明确身高写 `null`——不另设自由文本载体（appearance 已废，气质归 Character.vibe、体型主干归 body_type/shape_language）。

**LanguageStyle**（怪物跳过）：

| 内容 | 属性 |
|------|------|
| 说话风格 | speech_style（底色一句+五境分述，生成规范见 Schema/角色美术.md） |

### 3. 保存结果（MERGE 兜底 + 写内容 + status）

一次性写入（节点不存在则兜底创建）：

```cypher
// AppearanceStyle
MERGE (app:AppearanceStyle {id: '<APP_ID>'})
  ON CREATE SET app.status = 0;
MATCH (ch:Character {id: '<char_id>'}), (app:AppearanceStyle {id: '<APP_ID>'})
MERGE (ch)-[r:has_appearance]->(app) SET r.sync = true;
MATCH (app:AppearanceStyle {id: '<APP_ID>'})
SET app.name = '<角色名外貌特征>',
    app.shape_language = '...', app.age_impression = '...', app.body_type = '...',
    app.skin_tone = '...', app.ethnicity = '...', app.hair = '...', app.eye = '...',
    app.lip_shape = '...', app.marks = '...',
    app.height_cm = <身高整数或 null>,   // 按设定身高直接写（如 170）；无明确身高写 null
    app.status = 1;
// Character 占位消化归空（占位 status=0 是 event-ideator 的待建档标记；外貌建档即消化，REMOVE 对非占位无 status 者无害）
MATCH (ch:Character {id: '<char_id>'}) REMOVE ch.status;
```

LanguageStyle（怪物跳过）同理：MERGE 节点 + `has_voice_style` 边（sync=true）+ SET `speech_style` + `status = 1`。

**status 写入**：概念节点无审批，完成即 `status = 1`。

## 参考文档

- [角色美术设定模板](references/template-角色美术设定.md)
- [角色语言风格模板](references/template-角色语言风格.md)
