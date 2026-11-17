---
name: section-material-list
description: |
  输入一个 Section，从图数据库提取本节取材素材——出场人物（仅 involved）+ 人物 Lore（含控制折射）+ 成员 Event + SubEvent + 未消费 Hook，程序化清洗（freshness blocked 剔除、条件事件标红、机位悬空标红），逐条判定入选/剔除/边界，产出本节取材清单（人读 Markdown + 机器可读 JSON，纯只读零图写入）。
  为某节准备取材清单（chapter-novelist 1b 的前置独立步骤 / 人工盘点节素材）时使用。
argument-hint: <section_id>
arguments:
  - section_id
allowed-tools: Read, Bash, Write
---

# 节取材清单（纯只读，零图写入）

剧情创作流程的**素材圈定前置步骤**（节级）。输入 Section，把散在图上的四类素材（人物 / 人物 Lore / Event / SubEvent）拉齐、清洗、筛选，产出**本节取材清单**：`25_剧本/<章或自由节>/sec<MM>/取材清单.md`（人读表 + 头部机器可读块）——chapter-novelist 跑 `--ids` 子集、dialoguer / 人工盘点就近消费。**全程零图写入、不写任何 status**——清单是快照不是流程态，节是否已产小说/定稿与它无关。

## 参数

| 参数 | 说明 |
|------|------|
| section_id | Section 节点 ID（snowflake）。由 plot-design 编排传入，或用户直接触发。 |

## 口径（已拍板）

- **人物 = 仅 involved**（本节成员事件的 `Character ─involved→ Event` 反查）；sub 演出者经 appears_as 可能超出此名单属预期（演出层自足，见叙事层口径），清单不收。
- **Hook = 只进未消费的**（走本节成员事件 sub 的 reveals；消费历史以 `25_剧本` 指纹头为基线，从未消费的 Hook 才入清单）。
- **Lore 两源**：involved 角色 `has_info` 直挂 + `relation{type:'控制'}` 控制者折射（受控角色的戏折射控制者人格，换魂/操控类题材通用）；控制折射 Lore 标注宿主与折射路径，入清单但单独分组。
- **信号标红不门禁**：边界素材（freshness side 档、无 sub 事件、无 reveals 的 Hook）标红交用户/下游裁量，不拦截产出。

## 流程（三段式：查状态 → 完成任务 → 保存结果）

### 1. 查询目标节点状态 + 提取素材（七条只读查询）

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 查询（服务器 Memgraph 聚合作用域紧，**逐关系简单查询 + 本 skill 脚本 Python 侧组装**，不写长聚合链）。目标节不存在时报错退出。

```bash
# Q0 节信息 + 章归属（前驱校验：节不存在 → 报错退出）
MATCH (sec:Section {id:'<input>'})
OPTIONAL MATCH (ch:Chapter)-[:has_section]->(sec)
RETURN sec.id AS id, sec.title AS title, sec.section_no AS no, sec.status AS status,
       ch.chapter_no AS ch_no, ch.title AS ch_title LIMIT 1

# Q1 成员事件（includes 即成员，不做时间过滤；condition 供清洗用）
MATCH (sec:Section {id:'<sec_id>'})-[inc:includes]->(e:Event)
RETURN e.id AS id, e.title AS title, e.time AS time, e.type AS type,
       e.condition AS condition, inc.order AS ord
ORDER BY e.time

# Q2 SubEvent + 机位（缺 anchored_at 标红）
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)-[:refines]->(sub:SubEvent)
OPTIONAL MATCH (sub)-[:anchored_at]->(sc:Scene)
RETURN sub.id AS sub_id, sub.title AS title, sub.time AS time,
       e.id AS evt_id, e.title AS evt_title, sc.name AS scene
ORDER BY sub.time

# Q3 出场人物（仅 involved）
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)<-[:involved]-(c:Character)
RETURN DISTINCT c.id AS id, c.name AS name, count(e) AS n_evt, collect(e.title) AS evts
ORDER BY n_evt DESC

# Q4 人物 Lore（involved 角色 has_info 直挂）
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)<-[:involved]-(c:Character)-[:has_info]->(l:Lore)
RETURN DISTINCT l.id AS id, l.title AS title, l.content AS content,
       l.knowledge_level AS kl, c.id AS host_id, c.name AS host
ORDER BY host, kl

# Q5 控制折射 Lore（relation{type:'控制'} 控制者人格经受控角色入场）
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)<-[:involved]-(c:Character)
MATCH (src:Character)-[:relation {type:'控制'}]->(c)
MATCH (src)-[:has_info]->(l:Lore)
RETURN DISTINCT l.id AS id, l.title AS title, l.content AS content,
       l.knowledge_level AS kl, src.id AS host_id, src.name AS host, c.name AS via
ORDER BY l.id

# Q6 Hook（本节成员事件 sub 的 reveals；未消费判定见段 2）
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)-[:refines]->(sub:SubEvent)-[:re
veals]->(h:Hook)
RETURN DISTINCT h.id AS id, h.title AS title, h.knowledge_level AS kl,
       sub.title AS via_sub, e.title AS via_evt
ORDER BY h.id
```

> Q6 的 reveals 边在 Cypher 里跨行书写时必须写在同一行（`-[:reveals]->` 不可断行）。

### 2. 完成任务（脚本清洗筛选 + 逐条判定）

用本 skill 脚本一键完成（内置上述七查 + 清洗规则 + 落盘）：

```bash
python "${CLAUDE_SKILL_DIR}/scripts/build_material_list.py" <sec_id>
```

脚本自动完成：

**提取**（七查全跑，结果缓存放仓库 `.tmp/novelist/<sec_id>_listcache/`）：
- Q0~Q6 结果各自落 JSON 供复查。

**清洗规则**（程序化，零裁量）：
1. **Lore freshness**：对 Q4/Q5 全部 Lore 跑 `fingerprint.py freshness --in <合并素材JSON> --at <chNN/secMM 或 自由节路径> --root 25_剧本`——**注意素材行必须带 `knowledge_level` 键（查询别名 `AS kl` 须回映射，脚本已内置；缺键时 fingerprint 按"无限制"降级，freshness 形同虚设）**——`blocked` 档**剔除**（附档位），`side` 档**保留但标红**（只可侧面折射），`explicit`/从未消费正常入清单。
2. **条件事件**：Q1 事件带 `condition` 时标红（本节走不到该支线的可能——`choice:<id>[n]` 是否成立取决于玩家路径，清单按「全支线并存」呈现，标注表达式交下游裁量）。
3. **机位悬空 sub**：Q2 中 `scene IS NULL` 的 sub 标红（待 event-stager 补 anchored_at）。
4. **Hook 消费过滤**：对 Q6 的每条 Hook 跑 `fingerprint.py consumed --root 25_剧本 --ids <id>`——从未消费的入清单，已消费的剔除并附「上次消费节」注记（本节是该 Hook 的揭示主场与否交下游裁量，清单只报事实）。
5. **Lore 去重**：Q4 与 Q5 结果按 id 求并（控制折射偶尔与直挂重复）。

**筛选产出**（清单主体 = 五张表）：
- 人物表（id/名字/参与事件数/参与事件）
- Event 表（时间正序：id/标题/时间/type/condition/判定）
- SubEvent 表（时间正序，按父事件分组：id/标题/时间/父事件/机位/判定）
- Lore 表（按宿主分组：id/标题/kl/宿主/来源(直挂|控制折射)/freshness 档位/判定）
- Hook 表（id/标题/kl/揭示 sub/判定）——空表保留表头并注「本节无未消费 Hook」

**判定值**：`入清单` / `剔除`（附理由：freshness blocked / 已消费）／标红类目（side 档、条件事件、机位悬空、以及不可程序化判定的语义边界——逐条附「理由 + 可选处置」交用户拍板，不门禁）。

### 3. 保存结果（唯一落盘 = 取材清单.md）

**路径推导**（与小说.md 同目录规则）：有章 `25_剧本/ch<NN>/sec<MM>/取材清单.md`（NN=chapter_no、MM=section_no 零填充）；自由节 `25_剧本/自由节/sec<MM>/取材清单.md`。

**清单结构**（头部机器可读 + 正文人读表）：

```markdown
<!-- material-list v1
<section_id>
chars: <char_id>,<char_id>,…
events: <evt_id>,…
subs: <sub_id>,…
lores: <lore_id>,<lore_id>,…
hooks: <hook_id>,…
-->
# 取材清单 · sec?? 标题（ch?? 章名 / 自由节）

生成时间、素材计数摘要。

## 人物（仅 involved）
| id | 名字 | 参与事件数 | 参与事件 |
…（五张表，见段 2）
```

落盘后读回核对头部块 id 集与脚本统计一致，汇报摘要（计数 + 标红项逐条）。
