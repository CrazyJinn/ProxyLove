---
name: nrt-narrative-extractor2
description: |
  叙事关系提取器（审阅版）。从创作输入（角色设定/事件/场景/信息文本）中提取三类核心叙事关系：
  ①谁在哪里干了什么、哪里发生了什么（char-event-location）②谁/哪里有什么信息（char-info-location）
  ③Event/Info 之间的因果链（leads_to）。
  连 Neo4j 只读对照已有实体（标「已有 id」/「新发现」），输出单个 md 文件（实体清单 + 三类关系表 + 疑点交互记录）
  到 02_剧情数据/，供人工审阅。不产 CSV、不产 import.cypher、不写图、不为新实体生成 id。
  Info 双层提取：事实层照提 + 推断层（隐含背景/性格/动机等，宁多勿漏，推断错了由人工审阅拒绝）。
  触发条件：(1) 用户要求提取/梳理叙事关系、人物-事件-地点关系、信息归属、event/info 因果
  (2) 用户提到"关系提取"、"叙事关系表"、"谁在哪干了什么"、"因果链梳理"、"提取到02"
  (3) 用户提供叙事内容，要求 md 表格形式的审阅产物（而非直接入图）
allowed-tools: Read, Grep, Glob, Bash, Write
---

# 叙事关系提取器（审阅版）

从创作输入中提取三类核心叙事关系，输出 md 表格到 `02_剧情数据/` 供人工审阅。

**边界：只读图、只产 md。** 不产 CSV/cypher、不写图、不为新实体生成 id。要全量提取入图（CSV + import.cypher）用 `nrt-narrative-extractor`（v1）；本 skill 是它的轻量审阅前站。

## 三类核心关系

| # | 关系 | 覆盖的边（Schema 见 `00_init/Schema/叙事基础.md`） |
|---|------|------|
| A | 谁在哪里干了什么 / 哪里发生了什么 | involved（Character→Event）+ occurs_at（Event→Location） |
| B | 谁、哪里有什么信息 | link（Character/Location→Info；Event→Info 顺带一并列出） |
| C | Event/Info 因果链 | leads_to（(Event\|Info)→(Event\|Info) 四向全通） |

## Workflow

### 1. 读取

- Schema：`00_init/Schema/叙事基础.md`（节点/边定义、方向、枚举）
- 时间锚点：`00_init/游戏概览.md`。Event.time 推算：Day N = 锚点 + N×24h；开场 = 锚点 −1 天；时段词 清晨06 / 上午09 / 下午15 / 傍晚18 / 晚上20 / 深夜23，无时段词默认 12:00:00
- 叙事内容：用户给的文本或文件路径。无法解析时要求用户提供正确路径

### 2. 连图对照（只读）

用 `cypher_exec.py` 批量按名/标题查已有实体（`IN` + `LIMIT`）：

```bash
python .claude/scripts/cypher_exec.py -c "MATCH (c:Character) WHERE c.name IN ['陆择','陈默'] RETURN c.name AS name, c.id AS id" --json
```

四类同理：`Character.name` / `Location.name` / `Event.title` / `Info.title`。

- 连不上（Neo4j 未启动）→ 降级为纯文本提取，产物头部标注「未连图：实体未对照」并提醒用户
- **严禁任何写操作**——MERGE/SET/CREATE/DELETE 一律禁止，本 skill 全程只读

### 3. 实体提取 + 清单表

按输入有什么提取什么，不强求凑齐节点类型；已有编号的标图 id，新发现的标「新」（不生成 id）。产出 5 张实体清单表（角色/地点/事件/信息-事实/信息-推断，列定义见 [references/output-format.md](references/output-format.md)）。

- Event 含 time（按时间锚点推算）、type（行动/交流/转折/状态变化）
- Info 含 knowledge_level：默认 `1`，无法判断时降级而非升级
- **Info 双层提取（事实层 + 推断层）**：
  - 事实层：文本直接陈述的事实，按上述粒度照提
  - 推断层：从事实与行为细节推断的隐含信息——人物背景（如「林梦出资8600投资」→【林梦家庭条件优渥】）、性格、动机、关系、处境。每条须有一条清晰推理链（证据→结论，写进依据列），不做二跳推断（证据→A→B 时只提 A 不提 B）
  - 推断层 knowledge_level 默认 `3`；事实层与推断层**分表列出**（1.4 事实 / 1.5 推断），编号统一 I 系列接续，避免两层混排难辨
  - 推断层宁多勿漏：推断可能错也没关系，人工审阅时会拒绝——「拿不准」不是省略理由，也不必问用户（疑点交互只处理影响事实层的问题）
- **Location 粒度**：子空间线索（「护栏外侧」「点餐台」）并入地点行内备注，不单列

### 4. 三类关系表

产出表 A/B/C（列定义见 [references/output-format.md](references/output-format.md)），行内引用实体清单编号（C1/L2/E3/I4…）：

- **表 A** 每行一个 Event：时间、地点、人物（含 role）。无人物参与的事件照列（「哪里发生了什么」）
- **表 B** 每行一条 Info：角色/地点/事件三类关联端点分列
- **表 C** 只收**真因果**（上游是下游的直接原因）；纯时间先后/包含不进本表，写进表 A 备注即可。因果语境写清「为什么导致」

### 5. 疑点交互（边提取边记）

不清晰处累计成问题清单，分批向用户提问，**每题附推荐答案 + 理由**；确认结论记入产物「已确认决策」。典型疑点：

- 同名/别名是否同一实体（「小雪」=「沈暮雪」？）
- Location 归属粒度（「桥上」挂已有 长江大桥 还是新地点？）
- 因果 vs 先后拿不准
- knowledge_level 犹豫（2 还是 3）
- 时间推算歧义（缺 Day 定位/时段词）

不影响表格内容的细节不问，避免刷屏。推断层 Info 的取舍不在此列——拿不准照提，交人工审阅裁决。

### 6. 产出单文件

`02_剧情数据/<YYYY-MM-DD>_<主题>_关系提取.md`，骨架：头部说明（事实源/时间锚点/连图状态/已确认决策）→ 实体清单 5 表 → 表 A/B/C → 待确认问题（未决的）→ 统计摘要。

模板与列定义见 [references/output-format.md](references/output-format.md)，完整输入→输出示例见 [references/extraction-example.md](references/extraction-example.md)。产出后把文件路径和统计摘要回报给用户。

## Resources

- [references/output-format.md](references/output-format.md) — 产物骨架 + 各表列定义与填写规则
- [references/extraction-example.md](references/extraction-example.md) — 提取示例（输入→输出对）
