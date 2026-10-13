---
name: nrt-narrative-extractor
description: |
  叙事提取器。从创作输入（角色设定/事件/场景/信息 + 叙事基础 Schema）中提取实体、事件、关系、信息节点，
  输出实体 .md 文件 + CSV 文件 + import.cypher 导入脚本。
  触发条件：(1) 用户要求从叙事内容提取图数据
  (2) 用户提到"提取实体"、"提取事件"、"导出CSV"、"生成表格"、"实体提取"
  (3) 用户提供了叙事内容和 Schema 路径，要求结构化输出
allowed-tools: Read, Bash
---

# 叙事提取器

从创作输入中提取实体、事件、关系、信息，输出实体 .md 文件和 CSV 文件。

## 输入类型识别

| 输入类型 | 可能包含的节点 | 示例 |
|----------|---------------|------|
| 完整章节 | 全部类型（角色、事件、地点、信息） | "第一章-7号农场.md" |
| 角色背景 | 角色、信息 | "角色名：幼时失去双亲被教会收养" |
| 世界观设定 | 地点、信息 | "骑士团信奉人类至上" |
| 对话提纲 | 信息、角色、场景 | 场景级对话笔记 |
| 只言片语 | 信息、角色 | "老莫说南方营地被扫荡了" |

**原则：有什么就提取什么，不强求凑齐所有节点类型。**

## Workflow

### 1. 读取

读取叙事基础文档（默认 `00_init/Schema/叙事基础.md`）和叙事内容。如无法解析，要求用户提供正确路径。

### 2. 实体提取

按叙事基础中的节点类型逐类扫描内容，提取匹配的实例。已有编号的直接复用，不新建重复节点。

节点类型（4 种）：
- **角色（Character）** — 每个有名字的真实人物
- **事件（Event）** — 某时某刻发生的某件事
- **地点（Location）** — 具体地点/游戏场景
- **信息（Info）** — 每条对读者有意义的新认知

### 3. 信息提取（核心步骤）

对内容中的每段有意义的描述，逐一回答：

> **这段内容让读者/玩家知道了什么之前不知道的事？**

每个新认知 = 一条信息。区分两层：

- **事件层**：发生了什么（过程）
- **结论层**：因此知道了什么（结论）

**知识层判定**：

| 层级 | 受众 | 典型内容 |
|------|------|----------|
| `1` 表层 | 所有玩家 | 主线过场、关键 NPC 对话、视觉地标 |
| `2` 参与层 | 探索者 | 支线对话、可收集笔记、可选 NPC |
| `3` 深层 | 世界观猎人 | 隐藏文档、需推理的细节、跨线索关联 |

**判定原则**：默认 `1`。无法判断时降级而非升级。

**因果链**：如果 A 事件直接导致 B 事件/状态，记录因果关系。

### 4. 关系提取

按叙事基础的边类型连边（7 种）：

| 边类型 | 方向 | 说明 |
|--------|------|------|
| relation | Character → Character | 人物关系，可随时间变化 |
| involved | Character → Event | 人物参与事件 |
| occurs_at | Event → Location | 事件发生地点（一跳直挂） |
| at | Character → Location | 人物—场景关联 |
| link | Character/Event/Location → Info | 信息关联（type=涉及等；因果不在 link 上） |
| leads_to | (Event\|Info) → (Event\|Info) | 导致——叙事层唯一因果边，四向全通（事件→事件、事件→信息、信息→信息、信息→事件） |
| evt_relation | Event → Event | 事件关联（先后/包含；因果已归 leads_to） |

**不建 Spot**：叙事提取只建 Character/Event/Location/Info/Choice 节点，Event 定位一律 `occurs_at → Location`。子空间细分（Spot）与事件归组（anchored_at）是 scene-designer 场景化推进时的职责（见 `00_init/Schema/场景美术.md`），文本里的子空间线索（「电脑桌前」「点餐台」）写进 Event.description 供下游参考，不建图。

**时间推算**：Event.time 等 `yyyy-MM-dd HH:mm:ss`，从 `00_init/游戏概览.md`「时间锚点」推算（Day N = 锚点 + N×24h；开场 = 锚点 −1 天；后日谈 = 锚点 +31 天；时段词：清晨 06 / 上午 09 / 下午 15 / 傍晚 18 / 晚上 20 / 深夜 23 点，无时段词默认 12:00:00）。

- 完整内容：构建完整故事主线链
- 碎片输入：信息直接用适当的边关联角色/场景

### 5. CSV 生成

参照 [references/csv-patterns.md](references/csv-patterns.md) 生成 CSV 文件。

输出到 `01_叙事数据/` 目录：
- `01_叙事数据/csv/nodes_{type}.csv` — 每种节点类型一个文件
- `01_叙事数据/csv/edges_{edgeType}.csv` — 每种边类型一个文件
- `01_叙事数据/csv/import.cypher` — 一键导入脚本（LOAD CSV + MERGE）
- `01_叙事数据/_summary.md` — 提取摘要

只生成有数据的文件，空类型不生成。

## Resources

- [references/csv-patterns.md](references/csv-patterns.md) — CSV 格式规范、列定义、LOAD CSV 导入模板
- [references/extraction-examples.md](references/extraction-examples.md) — 提取示例（输入→输出对）
