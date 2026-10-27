---
name: chapter-structurer
description: |
  推进 Chapter 图节点的结构段：解析/创建 Chapter → 校验 Scene 前驱 → 把时间窗事件清单按叙事段落规划成若干节（Section；节时间由成员事件推导；块 id=scene_id 由 novelist 现场取用，structurer 不碰块）→ 为每节建 Section 节点（编排字段 + status=11 创建即定稿在位）+ has_section/includes 边。Chapter 无 status。Section 是编排容器 + 定稿态载体（script_path 由 chapter-dialoguer 写）；逐句行 LineAudio 由 section-voice-publisher 拆分时建。
  在需要建立章节结构或重做章节结构时使用。原「章节设计简报」与 Chapter.summary/branch_summary 均已废止——章的叙事范围由调用方建章时给定（时间窗/事件范围），预分配块 id 上图。
argument-hint: <chapter_id_or_title>
arguments:
  - chapter_id_or_title
allowed-tools: Read, Bash, Write
---

> **作废重做**：Chapter 无 status，重做由**用户显式重调本 skill** 触发（或 dashboard 重组章）。重做时即使 has_section/includes 边已存在，也**必须重新分节、重新统合 Scene、重写全部 Section 编排字段并覆盖**。重做时先删除旧 has_section 边 + DETACH DELETE 旧 Section 节点**及其逐句行产物链**（LineAudio，分节可能变，旧行全部作废）再重建。禁止因产物已存在而跳过。

# 章节结构（Chapter 结构段 · 章无 status）

剧情创作流程的**第一段**（章级）。创建/补全 Chapter 节点的编排属性 + 把本章事件清单按叙事段落**规划成 K 个节**（每节建 `Section` 节点（编排字段 + `status=11` 创建即定稿在位）+ `has_section` 边，节内事件用 `includes` 边统合（order=事件 time 序）；Section 是编排容器 + 定稿态载体——script_path 由 dialoguer 写，逐句行由拆分建）+ **不再预分配块 id**。**Chapter 无 status**。**不创作对话**。

> 结构段只定 Scene 序 + 分节，不定分支拓扑（分支/结局拓扑由图 Choice/option 承载，chapter-novelist 结构推理时核验）。

## 参数

| 参数 | 说明 |
|------|------|
| chapter_id_or_title | Chapter 节点 ID（snowflake）或 title 或 chapter_no。首次创建时调用方需在 prompt 中提供 `title`/`chapter_no` 与本章叙事范围（时间窗或事件范围，用于定位候选 Scene），缺失则停止。 |

## 流程（三段式：查状态 → 完成任务 → 保存结果）

> 本 skill 是 Chapter 结构段 status 的写入点 + Section 节点的创建点。不调子 skill、不产任何文件。

### 1. 查询目标节点状态

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 查询。

#### 1a. 解析或创建 Chapter

```cypher
MATCH (ch:Chapter) WHERE ch.id='<input>' OR ch.title='<input>' OR ch.chapter_no=<input>
RETURN ch.id AS id, ch.title AS title, ch.chapter_no AS chapter_no
LIMIT 1
```

- **已存在**：用其 `id`；本章叙事范围（时间窗/事件范围）由本次调用的入参给定。用户明示重做时进入重做流程（段 3 先清旧 has_section 边 + 删旧 Section 及其下游产物链）。
- **不存在**（首次创建）：需从调用方（plot-design agent / 用户）获取 `title`/`chapter_no` 与本章叙事范围（时间窗 `yyyy-MM-dd~yyyy-MM-dd` 或事件清单，用于定位候选 Scene）；缺失则停止并提示。生成新 id：
  ```bash
  python "${CLAUDE_SKILL_DIR}/../../scripts/snowflake_base62.py" -n 1 -q
  ```

#### 1b. 查候选 Scene + 前驱校验

从调用方给定的叙事范围定位候选事件与其 Scene（时间窗内事件 → occurs_at → Location ─part_of→ Spot ─realizes→ Scene；已场景化事件可 `Event→anchored_at→Scene` 一跳直取机位；或事件清单直接沿边定位）：

```cypher
// 时间窗入参 <起>~<止>（yyyy-MM-dd）：窗内事件 → occurs_at → Location → Spot → realizes → Scene
MATCH (e:Event)-[:occurs_at]->(loc:Location)-[:part_of]->(sp:Spot)-[:realizes]->(s:Scene)
WHERE e.time >= '<起>' AND e.time < '<止次日>'
RETURN DISTINCT s.name AS name, s.scene_type AS scene_type, s.atmosphere AS atmosphere,
       s.time_of_day AS time_of_day, s.status AS status,
       loc.name AS loc, count(e) AS evt_count, min(e.time) AS first_evt
ORDER BY first_evt LIMIT 50
```

> **前驱校验**：所选 Scene 的 `status` 必须为 `1`（已完成）。`status=0/-1` 表示场景未就绪，停止并提示先推进 `scene-designer`。

### 2. 完成任务（编排章节结构 + 分节规划）

#### 2a. 选 Scene + 排序 + 分节规划

据调用方给定的叙事范围，圈定本章事件清单（按 Event.time 时间序），**按叙事段落感把有序事件列表切成 K 个连续段，每段一节**——节 = 事件的有序组合。节的 Scene 序由节内事件的 `anchored_at→Scene` 首现序推导（未场景化事件报缺口、提示先推进 `scene-designer`）。
- 每节定 `section_no`（章内从 0 起）、`title`（节标题）、`summary`（本节戏剧职责一句话）；节的时间坐标由成员事件时间承载（time_day 已废止，不写）。
- 分节依据是叙事段落感（一个情绪单元 / 一个叙事小目标），不是机械等分。**线性章节可只分 1 节**（K=1 合法）。
- 节是事件时间序的**连续切片**，不交错（节 A 含事件 t0–t5，节 B 含 t6–t10）。
- **块 id**：块 id = 所写机位的 scene_id（Scene 节点 id），无分配动作、无章内唯一性要求（跨节拍平冲突由 chapter-publisher 发布期加节序前缀解决）。存量 `s<MM>_<short>` 形态（含 chapter00 中文 id）已随 603 行 scene_block_id 重写迁移完毕，仅存于 voice_key 出生快照与 15_声音 归档目录名，不再出现在任何活数据中。

> 这一步确定「本章分几节、每节含哪些事件（includes+order）」。段级切分（块）是 novelist 的创作自由，structurer 不预设。分支拓扑由图 Choice/option 承载（novelist 结构推理时核验）。

### 3. 保存结果（MERGE 兜底 + 建 Section + 写 status）

`--multi` 单事务，节点先于边；`status=-1` 重做时先删旧 Section 及其逐句行产物链（LineAudio）再重建：

```cypher
// 0.（仅 status=-1 重做时）清旧 has_section 边 + 删旧 Section 的产物链 + DETACH DELETE 旧 Section
//    （分节可能变，旧产物全部作废；DETACH DELETE 只删 Section 本身，产物链须显式先删）
MATCH (ch:Chapter {id:'<chapter_id>'})-[r:has_section]->() DELETE r;
MATCH (ch:Chapter {id:'<chapter_id>'})-[:has_section]->(sec:Section)
OPTIONAL MATCH (sec)-[:produces*1]->(p)
DETACH DELETE p;
MATCH (ch:Chapter {id:'<chapter_id>'})-[:has_section]->(sec:Section) DETACH DELETE sec;

// 1. Chapter 编排属性（无 summary/branch_summary——已废止，章范围不落图；无 status 取消结构审）
MATCH (ch:Chapter {id:'<chapter_id>'})
SET ch.title = '<title>',
    ch.chapter_no = <chapter_no>;

// 2. 每节：MERGE Section（编排字段 + status=11 创建即定稿在位）+ has_section(sync=true)；节内每事件：includes(order,sync=false)
//    （对 K 个节循环；每个 sec_id 用 snowflake_base62.py 新生成）
MERGE (sec:Section {id:'<sec_id>'});
MATCH (sec:Section {id:'<sec_id>'})
SET sec.section_no = <MM>, sec.title = '<sec_title>', sec.summary = '<sec_summary>',
    sec.status = 11;    // 创建即定稿在位
MATCH (ch:Chapter {id:'<chapter_id>'}), (sec:Section {id:'<sec_id>'})
MERGE (ch)-[r:has_section]->(sec) SET r.sync = true;
//    节内每个事件（按 Event.time 字符串序，order 从 0 起）：
MATCH (sec:Section {id:'<sec_id>'}), (e:Event {id:'<event_id>'})
MERGE (sec)-[r:includes]->(e) SET r.order = <order>, r.sync = false;
```

> `has_section` 边 `sync=true`（组成关系：人改 Chapter 属性时级联重置 Section 及其逐句行→-1）；`includes` 边 `sync=false`（编排引用，不级联；防级联 BFS 穿 Event 中继）。Section 的 `status=11` 创建即写。

**status 写入**：Chapter 无 status（属性已从图删除）。Section 创建即 `status=11`（定稿在位标记）。结构段完成即可进入各节的 `chapter-novelist`，无审批门控。

最后汇总：分节列表（section_no/title/所含事件+order 及各事件 anchored Scene）、K 个 Section（编排容器 + status=11）。**零文件产出**。

## 参考文档

- 剧情 Schema：[00_init/Schema/剧情.md](../../../00_init/Schema/剧情.md) — Chapter/Section（定稿态）/LineAudio/has_section/produces/includes 定义、status 流转
- 场景美术 Schema：[00_init/Schema/场景美术.md](../../../00_init/Schema/场景美术.md) — Scene 字段
- 下游：[chapter-novelist](../chapter-novelist/SKILL.md)（结构产出即可用，按节圈定取材/结构推理/产小说）
