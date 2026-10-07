---
name: char-design-sheet
description: |
  推进 DesignSheet 图节点：查询状态 → 组装提示词/生成图片 → 保存结果（MERGE 兜底建节点+边，写产物与 status）。
  双模式：常规（首版/重做——以用户提供的单张真人参考照片图生图，AppearanceStyle 全量补充特征、冲突以属性为准）与**增量模式**（`<char_id> <base_ds_id> <口述改动>`——以参考版设计图为底图生图新增版本，剧情永久外貌变更如剪发用）。
  单轮直推到最大门控（图片完成即待审 10）。在需要生成角色设计图或 DesignSheet 节点需推进时使用。
argument-hint: <char_id> [base_ds_id] [口述改动]
arguments:
  - char_id
  - base_ds_id
  - notes
allowed-tools: Read, Bash, Write, Edit
---

> **status=-1 = 作废重做**：当 DesignSheet 被 sync 级联重置为 `status=-1` 时，即使 `prompt_path`/`image_path` 已存在，也**必须重新生成并覆盖**（重走 0→1→2）。`-1` 与 `0` 都视为"需生成"起点；`-1` 明确表示有旧产物要覆盖，**禁止因文件已存在而跳过**。

# 设计图（DesignSheet）

每角色每版本一个 DesignSheet 节点。**首版/常规重做**以用户参考照片**图生图**（Mode A——AppearanceStyle 全量补充特征，冲突以属性为准）；**增量版本**（剧情永久外貌变更，如 sec02 剪发）以参考版设计图为底**图生图**（DesignSheetDelta 模式）——仅变更口述内容，保持同人物脸部一致，不改写旧版（旧链下游零作废）。

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| char_id | 角色 ID（snowflake） | 必传 |
| base_ds_id | 参考版 DesignSheet 节点 ID（增量模式必传；缺省 = 常规模式） | — |
| notes | 口述改动（增量模式必传，引号包裹）。须含：变更描述（如「清爽利落的黑色短发，发丝干净有型」）+ 生效点（`ch<NN>/sec<MM>`）+ 版本短名（`slug=<短名>`） | — |

## 模式判定

- **无 base_ds_id → 常规模式**：推进该角色已有 DesignSheet（status ∈ {-1,0} 逐个重做/生成），或首版不存在时新建（参考图图生图 Mode A）。
- **有 base_ds_id + notes → 增量模式**：从参考版图生图新增版本节点。口述缺生效点或 slug → **停止并询问，禁止猜**。

## 流程（三段式：查状态 → 完成任务 → 保存结果）

> 本 skill 是 status 的唯一写入点；提示词与图片由子 skill（char-prompt-assembler / infra-image-generator）纯产出，本 skill 在「保存结果」步统一写入图。

### 1. 查询目标节点状态

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 查询前驱 + 全部已有 DesignSheet：

```cypher
MATCH (ch:Character {id: '<char_id>'})-[:has_appearance]->(app:AppearanceStyle)
OPTIONAL MATCH (app)-[:produces]->(ds:DesignSheet)
RETURN ch.name AS char_name,
       app.id AS app_id, app.status AS app_status, app {.*} AS app_data,
       ds.id AS ds_id, ds.status AS ds_status, ds.slug AS slug,
       ds.active_from AS active_from, ds.delta_notes AS delta_notes
```

- **前驱校验**：`app_status >= 1`（外貌已由 char-concept-designer 设计），否则停止并提示先推进概念设计。
- **常规模式目标判定**：多版本时对每个 `ds_status ∈ {-1, 0}` 的版本逐个推进（`1` 已有提示词、`10` 待审不可推进、`11` 已完成跳过）；全部版本皆无且无任何 DS → 新建首版（生成新 snowflake id 作 `DESIGN_ID`）。
- **增量模式前置校验**：`base_ds_id` 属于该角色（出现在上述结果中）∧ 参考版 `ds_status = 11` ∧ `image_path` 非空且文件存在——否则停止并报告。生成新 snowflake id 作 `DESIGN_ID`。
- 记录 `char_name`（产物路径用）、`app_id`（保存步建 `produces` 边用）、`app_data`（外貌 tags + 自由文本 + `height_cm`/`ethnicity`，常规模式第 2 步组装 data 用）。**不取 `color_direction`**——配色逻辑属造型/着装范畴，不进设计图提示词（2026-10-06 用户定规）。

### 2. 完成任务

#### 常规模式（首版/重做——参考图图生图）

按当前 status 单轮直推到图片完成（待审 10）。生成以**单张真人参考照片**为底图生图，AppearanceStyle 外貌属性全量作为补充特征写入提示词（冲突以属性为准）。

**① 参考图探测（用户动作阻塞，同 BGM wav 归档模式）**：`ls "06_角色美术/<char_name>/"`，按 `参考图.png` > `参考图.jpg` > `参考图.jpeg` 优先级**精确匹配文件名**。目录缺失或三者皆无 → **停止并提示**：期望路径 `06_角色美术/<char_name>/参考图.jpg`（三种合法扩展名 png/jpg/jpeg 均可）、「经 dashboard 角色详情页上传（推荐，自动压缩与规范命名）或手动放入后重新触发本 skill」、**不回退文生图**；不写图、不写任何文件。status=-1 级联重做同受此约束（参考图被删同样阻塞，重传后重跑）。

**② 组装提示词**：Skill 工具调用 `char-prompt-assembler`，参数 `DesignSheet '<data_json>'`：

```json
{
  "appearance": { "tags": {"shape_language":"...","age_impression":"...","body_type":"...","skin_tone":"...","ethnicity":"...(可选)","hair":"...","eye":"...","lip_shape":"...","marks":"..."}, "appearance":"...","visual_tone":"...","first_impression":"...", "height_cm": "可选 int" },
  "character": { "id":"<char_id>", "name":"<char_name>" },
  "base": { "image": "06_角色美术/<char_name>/参考图.<ext>", "summary": "真人参考照片（单张）" },
  "node": { "id":"<DESIGN_ID>" },
  "output_path": "06_角色美术/<char_name>/prompt.md"
}
```

（`appearance` 数据取自第 1 步查询的 `app_data`；图里没有的可选字段（`ethnicity`/`height_cm` 等）跳过。重做多版本中某版时：`output_path` 用该版 slug 段——见下方路径规则；`appearance.tags` 的 `hair` 等**未随版本变更的字段仍以 AppearanceStyle 为准**，变更过的维度以该版 `delta_notes` 覆盖描述。）

**③ 生成图片**：Skill 工具调用 `infra-image-generator`，参数 `<PROMPT_PATH> <OUTPUT_PATH> <base.image>`（**图生图**，第三参 = 探测到的参考图路径）：`OUTPUT_PATH = 06_角色美术/<char_name>/设计图.png`。dashboard 上传的参考图已完成压缩（EXIF 转正 + 长边 ≤1536 + JPEG），直接使用；手动放置的原图亦直传。

#### 增量模式（图生图新增版本）

**解析口述**（缺项停止询问，禁止猜）：
- 变更描述：notes 正文（图生图 prompt 变更段唯一来源）
- 生效点：形如 `ch01/sec02` → `active_from = chapter_no*1000 + section_no`（如 1002）
- slug：形如 `slug=短发` → 版本短名（产物路径目录段，禁 Windows 非法字符）
- 否定锚定 `negation`：由 LLM 据「变更描述 × AppearanceStyle 对应旧字段值」生成对旧特征的显式否定（如旧 hair「黑色凌乱短发，油腻缺乏打理」→「头发不油腻、不凌乱，无颓废未打理感」）——压制参考图惯性，**只否定被变更的维度**，不得引入新否定

**组装提示词**：Skill 工具调用 `char-prompt-assembler`，参数 `DesignSheetDelta '<data_json>'`：

```json
{
  "base": { "image": "<参考版 image_path>", "summary": "参考版设计图（同人物）" },
  "delta": { "notes": "<口述变更描述>", "negation": "<否定锚定>" },
  "character": { "id":"<char_id>", "name":"<char_name>" },
  "node": { "id":"<DESIGN_ID>" },
  "output_path": "06_角色美术/<char_name>/<slug>/prompt.md"
}
```

**生成图片**：Skill 工具调用 `infra-image-generator`，参数 `<PROMPT_PATH> <OUTPUT_PATH> <base_image>`（**图生图**，第三参 = 参考版设计图路径）：

`OUTPUT_PATH = 06_角色美术/<char_name>/<slug>/设计图.png`。

#### 路径规则（两模式通用）

- slug 为空的版本（首版/单版角色）：`06_角色美术/<char_name>/prompt.md` 与 `设计图.png`（旧路径零迁移）。
- slug 非空的版本：`06_角色美术/<char_name>/<slug>/prompt.md` 与 `设计图.png`。
- 反向校验：角色已有多个版本而本版 slug 为空（且非 active_from 为空的首版）→ 停止并提示补 slug（防两版同路径物理覆盖）。

### 3. 保存结果（MERGE 兜底 + 写产物 + 推进 status）

一次性写入（节点不存在则兜底创建）：

```cypher
// 兜底建节点+边（ON CREATE 仅初始化，不覆盖已推进的 status）
MERGE (ds:DesignSheet {id: '<DESIGN_ID>'})
  ON CREATE SET ds.status = 0;
MATCH (app:AppearanceStyle {id: '<app_id>'}), (ds:DesignSheet {id: '<DESIGN_ID>'})
MERGE (app)-[r:produces]->(ds) SET r.sync = true;
// 写产物 + 推进 status（增量版本并写版本三字段）
MATCH (ds:DesignSheet {id: '<DESIGN_ID>'})
SET ds.prompt_path = '<PROMPT_PATH>',
    ds.image_path  = '<IMAGE_PATH>',
    ds.delta_notes = '<增量模式：口述变更描述；常规模式：保持原值不动>',
    ds.active_from = <增量模式：生效锚点 int；常规模式：保持原值不动>,
    ds.slug        = '<增量模式：版本短名；常规模式：保持原值不动>',
    ds.status = 10;                      // 图片完成即待审（直写，不经 submit）
```

**status 写入**：固定 `10`（待审，等待 dashboard 审批）。增量版本审批重点：与参考版并排比对——脸部/五官/体型/眼镜一致、**仅口述维度变化**。

## 参考文档

- 提示词组装：[char-prompt-assembler](../char-prompt-assembler/SKILL.md) Mode A（首版/重做——参考图图生图）/ DesignSheetDelta（增量版）
- 图片生成：[infra-image-generator](../infra-image-generator/SKILL.md)
