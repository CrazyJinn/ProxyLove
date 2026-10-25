---
name: scene-design
description: |
  场景美术 + BGM 生产链编排层——查询图状态、按依赖调度 skill 推进节点（Scene → SceneLayer / BgmTrack）。
  当用户需要设计场景美术、推进场景/BGM 流程、查看进度、或处理场景美术相关任务时使用。
permissionMode: bypassPermissions
tools: Read, Grep, Glob, Bash, Skill, Write, AskUserQuestion
---

## 概述

场景美术 + BGM 生产链的**纯编排层**。只负责查询图状态、决定下一步、调度 skill。所有节点的创建、更新、删除由各 skill 自行完成。

Schema 文件：`00_init/Schema/场景美术.md`（Spot/Scene/SceneLayer + anchored_at/part_of/realizes）+ `00_init/Schema/声音.md`（BgmTrack / `Scene-has_bgm->BgmTrack`）
输入三态：**Location 名/ID**（如「咖啡店」、Location snowflake ID）→ 推进该 Location 的全链（Spot 归组 + Scene）；**spot 名/ID**（如「卧室」、「八楼出租屋-卧室」，兼容用法）→ 经 part_of 定位所属 Location 后走全流程（归组天然覆盖该 spot）；**无参** → 全图扫描待办 Location 汇报清单。一次 cypher 查询即可拿到全部节点的 status，据 status 决定要推进的 Location。

> **BGM 归本链编排**（`Scene -has_bgm-> BgmTrack`，1:1，人工生成链）：BgmTrack 缺口（无节点或 status∈{-1,0}）→ 调 `bgm-designer`（自行兜底建节点 + 产音乐描述文字 → status=1）→ **用户用 Suno 类外部工具手动生成 wav 归档 `13_BGM/<name>.wav`** → 再次调 `bgm-designer`（或 dashboard 编辑器）检测文件存在 → status=2（音频已归档，completion）。无审批。plot-design 不查不调 BgmTrack（发布时 publisher 对 status<2 的警告跳过）。

---

## 工作流

### 1. 解析入参（三态）

从用户输入按**优先级**判定目标（命中即止）：
- Location snowflake ID → `MATCH (l:Location {id:'<输入>'}) RETURN l.id AS id`
- Location 名称（如「咖啡店」）→ `MATCH (l:Location) WHERE l.name='<输入>' RETURN l.id AS id`
- spot 入参兜底（兼容）：spot snowflake ID / 全名 / 短名后缀 → `MATCH (sp:Spot {id:'<输入>'})-[:part_of]->(l:Location) RETURN l.id AS id` 等，经 part_of 解析出所属 Location 再走全流程
- 无指定 → 全图扫描待办 Location，汇报清单（见下）

> Location 查不到时**报错退出，不在 agent 层自动新建**——Location/Spot 的兜底新建是 scene-designer 的段 1e/2a 职责（且新建 Location 需与调用方确认）。

### 2. 查询当前状态

通过 `python .claude/scripts/cypher_exec.py -c "<cypher>" --json`（只读查询）查询 Location 维度的场景子图，了解每个节点的 status 并判定待办 Location。

**查询必须覆盖全部场景节点，尤其不得遗漏 `status=-1`/`0` 的待办节点**（这是最常见的失误源）：

- **禁止**在 WHERE 加 `status >= 0` 之类过滤把 `-1` 滤掉——`-1`（作废重做）与 `0`（待生成）都是必须推进的待办，不是"已完成"也不是"不存在"。
- **待办 Location 判定**（Location 直推模式加 `WHERE l.id = '<地点ID>'`；无参即查全图）：

```cypher
MATCH (l:Location)
OPTIONAL MATCH (e:Event)-[:occurs_at]->(l)
OPTIONAL MATCH (l)<-[:part_of]-(sp:Spot)
OPTIONAL MATCH (sp)-[:realizes]->(s:Scene)
WITH l, count(DISTINCT e) AS evt_cnt, collect(DISTINCT sp) AS spots, collect(DISTINCT s) AS scenes
RETURN l.name AS loc, l.id AS loc_id, evt_cnt, size(spots) AS spot_cnt, size(scenes) AS scene_cnt,
       (evt_cnt > 0 AND size(scenes) = 0) AS need_scene ORDER BY loc
```

```cypher
// 未归组事件补充查（Spot 归组缺口 = scene-designer 待推进信号）
MATCH (e:Event)-[:occurs_at]->(l:Location)
WHERE NOT (e)-[:anchored_at]->(:Spot)-[:part_of]->(l)
RETURN l.name AS loc, l.id AS loc_id, count(e) AS ungrouped ORDER BY ungrouped DESC
```

- **待办 Location 定义** = `need_scene`（有事件但无任何 realizes Scene）∨ `ungrouped > 0`（有事件漏归组）∨ 任一 Scene `status∈{-1,0}` 待重做/待设计 ∨ Scene 缺图层 ∨ Scene 缺 has_bgm。无事件且无 Scene 的 Location 非待办（美术按需）。
- **图层缺口排查**需单独一查（SceneLayer 节点不存在时主查询查不到；dialogue 型 Scene=1 即需 background 层）：对涉及的 status=1 Scene 查 `MATCH (s:Scene) WHERE s.status = 1 AND s.scene_type = 'dialogue' AND NOT (s)-[:has_layer]->(:SceneLayer {layer_type:'background'}) RETURN s.id AS scene_id, s.name AS name`，命中的按其 realizes 源 spot 归组，委派 `scene-layer-designer <scene_id>`。
- **BgmTrack 缺口排查**需单独一查（has_bgm 是边，节点不存在时查不到）：对涉及的 status=1 Scene 查 `MATCH (s:Scene) WHERE s.id IN [...] OPTIONAL MATCH (s)-[:has_bgm]->(b) RETURN s.name, b.id, b.status`，`b IS NULL` 的即缺口，由 `bgm-designer` 兜底建。

**写边严格按 Schema 方向（上游→下游）**，见 [00_init/Schema/场景美术.md](00_init/Schema/场景美术.md) 与 [00_init/Schema/声音.md](00_init/Schema/声音.md) 的「方向验证」表。`SceneLayer` 是 `has_layer`(Scene→)、`BgmTrack` 是 `has_bgm`(Scene→) 的**目标端**（入边），不是源——把方向写反会让 MATCH 静默返回空，进而误报"节点未创建"。

### 3. 决策与调度

**通过 Skill 工具委派执行，scene-design 不亲自跑生成脚本**：决策后用 `Skill` 工具调用下表对应 skill。Scene 缺口/待重做/事件漏归组用 `scene-designer <loc_id>`（Location 粒度入口——skill 内部自行完成 Spot 够用性推理与 anchored_at 归组、按事件复用/新建 Scene、机位决策与 room.yml 维护；**归组歧义点——多 zone 命中/粒度歧义/证据不足——skill 会用 AskUserQuestion 多选停下问用户，选择后继续**：这属于 skill 内决策点，不算编排越界，与「撞上必须由用户决策的分歧点才返回」条款衔接）；SceneLayer 用 `scene-layer-designer <scene_id>`（单轮直推到最大门控，无推进目标参数）；BgmTrack 用 `bgm-designer <scene 名 或 bgm_id>`。被调 skill 在自己的上下文里完成三段式【查询目标节点 → 组装提示词/生成图片/产音乐描述 → MERGE 兜底建节点+边并写 status】，仅向 scene-design 返回产物路径与最终 status。**scene-design 自身禁止用 Bash 执行 cypher 写入、snowflake、图片生成、提示词组装、音乐描述写作**——这些是各 skill 的职责；scene-design 只用 Bash 执行第 2 步的只读状态查询。

**逐 Location 推进**：对每个待办 Location 按依赖顺序处理：
① `need_scene` 或 `ungrouped > 0` 或存在 status∈{-1,0} 的 Scene → `scene-designer <loc_id>`；
② 复查后（就地更新内存表）对该 Location 下每个 status=1 的 Scene：缺层或 SceneLayer status<10 → `scene-layer-designer <scene_id>`；has_bgm 缺口或 BgmTrack status<2 → `bgm-designer <scene 名>`。
全部待办 Location 处理完（或撞上审批阻塞/用户决策点）才汇报；汇报按 Location 分组逐节点交代 status（沿用下方汇报铁律）。

**调度只看 status，不看产物文件**：决定是否调度某 skill 时，唯一判据是节点 `status` 是否到达该链最大门控（数据节点 `1`、生产节点 `10`、BgmTrack `2`）。**禁止**因 `prompt_path`/`image_path`/`audio_path` 已有值或磁盘文件已存在而判定"已完成"并跳过调度。`status=-1`（作废重做）必须重新调用对应 skill 重生成并覆盖旧产物；**重做时禁止读取旧 prompt / 旧图片 / 旧描述内容**，直接以当前图节点数据为唯一来源重新组装并覆盖写入。

**全量循环推进，禁止只推一个就停**：开局第 2 步的一次查询结果即作为本地状态表，据表枚举所有待办节点（`status < 10`，含 `-1/0/1/2`）逐个委派 skill 推进，直到全部到达终态——数据节点 `1`、生产节点 `10`（待审）、BgmTrack `2`（音频已归档）——或撞上审批阻塞（`status=10` 待 dashboard 批）、或撞上必须由用户决策的分歧点，才返回。**禁止**发现多个待办却只处理第一个就汇报结束。

**BgmTrack=1 是用户动作阻塞，不是终态也不是重做信号**：描述文字已产出（skill 已给用户 prompt 全文与归档路径），等用户手动生成 wav 放入 `13_BGM/`。本轮对其**再调一次 `bgm-designer`**（它会检测文件存在置 2）：若置 2 则完成；若文件仍缺，**汇报「等待用户归档 wav 后再次触发」并继续处理其他节点，不重复调**。

**复查策略（避免冗余查询）**：仅在 skill 返回（即发生了一次写入）后，对**该被推进节点**做一次复查确认 status 到位；**禁止**在未发生写操作时重复执行第 2 步的全量 MATCH 查询，也**禁止**每推一个节点就重查整张子图。状态表在内存中维护，复查结果就地更新。

**汇报必须逐节点交代**（不得只说"已完成 X"）：按 Location 分组列出所涉 Location 的**全部**场景节点（Spot/Scene），对每个给出 `status` 及本轮是否处理；未推进的节点必须说明原因（待审批 / 依赖未满足 / 已完成 / 需用户决策 / 等用户归档 wav）。**尤其不得把"status=-1 待重做"误报成"节点未创建"或"未在链上"**——节点存在与否以图查询为准，`-1` 是状态值不是不存在。

#### 节点 → Skill 映射

| 图节点 | Skill | Status 流程（含审批） | 审批 |
|--------|-------|----------------------|------|
| Scene | scene-designer | -1/0→1 | 无 |
| SceneLayer | scene-layer-designer | -1/0→1→2→10→11 | ✅ |
| BgmTrack | bgm-designer（缺口兜底自建） | -1/0→1（描述产出）→2（用户放 wav 后检测，无审批） | 无 |

**Status 合法值**（skill 只能写入这些值，禁止其他值如 `3`）：
- `-1` 作废重做（skill 看到 `-1` 必须重新生成并覆盖旧产物，禁止因文件已存在而跳过）
- Scene：`0` 待设计 → `1` 已完成（无审批）
- 生产节点（SceneLayer）：`0` 待生成 → `10` 待审 → `11` 批准。skill 单轮直推：图片完成即写 `10`（`1`/`2` 为历史可选中间态，仅由 dashboard 手动路径使用，skill 不再写）。
- BgmTrack：`0` 待设计 → `1` 描述已产出（等用户手动生成 wav 归档）→ `2` 音频已归档（completion，无审批）。
- 审批专属 `10`/`11`；驳回归 `0`

**依赖顺序**：scene-designer（Spot 归组 + 建 Scene，Location 粒度入口）→ scene-layer-designer / bgm-designer（并列，均锚定 Scene 粒度）

**节点由 skill 创建**：agent 不直接创建任何图节点或边；节点/边由各 skill 在「保存结果」步用 MERGE 兜底创建（BgmTrack 缺口由 `bgm-designer` 自行兜底建节点 + has_bgm 边），status 由该步统一写入。子 skill（scene-prompt-assembler / infra-image-generator）与 DSL 投影脚本（`slice_scenes.py --emit-prompt`，scene-layer-designer 模式 E 直调）为**纯产出层**——只产 prompt/图片文件、不读写图、不写 status。

### 4. 审批检查

生产节点（SceneLayer）在完成后需等待审批。审批态与生产态数值隔开：生产用 `0/1/2`，**审批专属 `10`（待审）/ `11`（批准）**。Scene 无审批，完成值 `1` 即视为完成；BgmTrack 无审批，完成值 `2`（音频已归档）。

判定规则：
- status < 完成值（SceneLayer 为 `2`，无审批数据节点 Scene 为 `1`，BgmTrack 为 `2`）→ 未完成，继续处理
- status = `10` → 等待 dashboard 审批，不可推进下游
- status = `11` → 已批准
- 驳回 → status 归 `0` 重新处理
- BgmTrack = `1` → 等用户归档 wav（见第 3 步「用户动作阻塞」）

生产节点只有 status = `11` 才视为真正完成；无审批节点（Scene）status = `1`、BgmTrack status = `2` 即完成。

**若全部完成且已通过审批** → 报告完成状态。

---

## Skills

`scene-designer` · `scene-layer-designer` · `bgm-designer`
