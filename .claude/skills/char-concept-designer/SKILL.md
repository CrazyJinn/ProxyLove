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

**先读字段表**：Read [00_init/Schema/角色美术/AppearanceStyle.md](../../../00_init/Schema/角色美术/AppearanceStyle.md) 与 [LanguageStyle.md](../../../00_init/Schema/角色美术/LanguageStyle.md)——**字段全集、类型、必填与写法纪律均以该文件为准（含节点级「写法纪律」节），不凭记忆写字段**；表中没有的字段一律不写。

随后按 [references/template-角色美术设定.md](references/template-角色美术设定.md) 与 [references/template-角色语言风格.md](references/template-角色语言风格.md) 生成设计内容（本节以下只列生成纪律，字段清单见 Schema）。

**LanguageStyle**（怪物跳过）：speech_style——生成规范见 [LanguageStyle.md](../../../00_init/Schema/角色美术/LanguageStyle.md)。

### 3. 保存结果（MERGE 兜底 + 写内容 + status）

执行方式与段 1 一致：`${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py`；多语句块走 `--stdin --multi --json`（按 `;` 分割单事务顺序执行，写 cypher 规则见 [cypher_exec.py](../../scripts/cypher_exec.py) 顶部 docstring）。

按段 2 读到的 Schema 字段表写 SET 语句。**形态**（锚定与约定，字段清单以 Schema 为准——表中有什么字段、本节点就 SET 什么）：

```cypher
// AppearanceStyle（形态示例——实际 SET 字段清单按段2读到的 Schema 字段表生成）
MERGE (app:AppearanceStyle {id: '<APP_ID>'})
  ON CREATE SET app.status = 0;
MATCH (ch:Character {id: '<char_id>'}), (app:AppearanceStyle {id: '<APP_ID>'})
MERGE (ch)-[r:has_appearance]->(app) SET r.sync = true;
MATCH (app:AppearanceStyle {id: '<APP_ID>'})
SET app.name = '<角色名外貌特征>',
    app.<字段1> = '...', app.<字段2> = '...',  // ← Schema 字段表逐字段（含数值/空值字段按其类型写法），缺一不可、表外不加
    app.status = 1;
```

LanguageStyle（怪物跳过）同理：MERGE 节点 + `has_voice_style` 边（sync=true）+ 按其 Schema 字段表 SET + `status = 1`。

**写后读回验证**：SET 完成后按 Schema 字段表逐字段读回（`MATCH (app:AppearanceStyle {id:'<APP_ID>'}) RETURN app`），核对无缺漏、无表外字段。

**status 写入**：概念节点无审批，完成即 `status = 1`。

## 参考文档

- [角色美术设定模板](references/template-角色美术设定.md)
- [角色语言风格模板](references/template-角色语言风格.md)
