# 缺口检查查询库 + 推荐规则

> nrt-gap-filler 的执行参考。四组检查（E/S/C/X）的 cypher 模板 + focus 变体 + 推荐信号规则。
> 推荐规则曾带 2026-10-12 存量图回测（n=47）命中率背书——**2026-10-13 叙事基础重构（occurs_at 直挂 Location / Spot 后移 / leads_to）为结构性变更，旧命中率全部作废**；迁移完成后须用新图重跑 leave-one-out 重建基线（真值 Location 由旧两跳等价换算）。

## 一、缺口检查（scan 用）

### E1 · Event 缺 occurs_at（high，直接生产隐形）

```cypher
// 全图版
MATCH (e:Event) WHERE NOT (e)-[:occurs_at]->(:Location)
OPTIONAL MATCH (c:Character)-[:involved]->(e)
WITH e, collect(DISTINCT c.name) AS chars
RETURN e.id AS id, e.title AS title, e.time AS time, e.type AS type,
       e.description AS description, e.ending_kind AS ending_kind, chars
ORDER BY e.time LIMIT 100
```

focus 版（锚点 1 跳）：`MATCH (c0:Character) WHERE c0.name='<focus>' OR c0.id='<focus>' MATCH (c0)-[:involved]->(e:Event) WHERE NOT (e)-[:occurs_at]->(:Location) …`

### E2 · Location 完全未场景化（high，有事件但无任何 realizes Scene）

```cypher
MATCH (e:Event)-[:occurs_at]->(l:Location)
WHERE NOT EXISTS { MATCH (l)<-[:part_of]-(:Spot)-[:realizes]->(:Scene) }
WITH l, collect({id: e.id, title: e.title, time: e.time}) AS events, count(e) AS n
RETURN l.id AS loc_id, l.name AS loc, events, n
ORDER BY n DESC LIMIT 50
```

> Memgraph/Neo4j 双后端零分支：若 EXISTS 语法不适配，改 `OPTIONAL MATCH (l)<-[:part_of]-(:Spot)-[:realizes]->(:Scene) WITH l, events, n, count(scn) AS scns WHERE scns = 0`（拆聚合链）。修复 = **场景化派单**（scene-design agent，Location 模式；不手工建骨架，见修复模板节）。

### E3 · Event 缺 involved 且非结局事件（medium）

```cypher
MATCH (e:Event)
WHERE NOT (e)<-[:involved]-() AND coalesce(e.ending_kind, '') = ''
RETURN e.id AS id, e.title AS title, e.time AS time LIMIT 50
```

> ending_kind 非空的结局事件豁免——身份由 `Choice -option{leads_to_ending}-> Event` 承载（实测先例：「跳江BE」）。

### S1 · 已归组但 Spot 无 realizes（medium，半途场景化/手工编辑残留）

```cypher
MATCH (e:Event)-[:anchored_at]->(sp:Spot)
WHERE NOT (sp)-[:realizes]->()
WITH sp, collect(e.title) AS events, count(e) AS n
RETURN sp.id AS spot_id, sp.name AS spot, sp.kind AS kind, events, n
ORDER BY n DESC LIMIT 50
```

修复 = 场景化派单（scene-designer spot 直推模式补 Scene）。

### S2 · Location 已场景化但有事件漏归组（high，混挂状态）

```cypher
MATCH (e:Event)-[:occurs_at]->(l:Location)
WHERE NOT (e)-[:anchored_at]->()
  AND EXISTS { MATCH (l)<-[:part_of]-(:Spot)-[:realizes]->(:Scene) }
WITH l, collect({id: e.id, title: e.title}) AS ungrouped, count(e) AS n
RETURN l.id AS loc_id, l.name AS loc, ungrouped, n
ORDER BY n DESC LIMIT 50
```

修复 = 重跑 scene-designer（Location 模式）归组，或确认留待后续场景化时归组。

### S3 · 死 Spot（low，无 realizes ∧ 无 dsl_path ∧ 无 anchored_at 入边）

```cypher
MATCH (sp:Spot)
WHERE NOT (sp)-[:realizes]->()
  AND coalesce(sp.dsl_path, '') = ''
  AND NOT ()-[:anchored_at]->(sp)
RETURN sp.id AS id, sp.name AS name, sp.kind AS kind LIMIT 50
```

修复 = 删除建议（DETACH DELETE）/ 确认保留。

### C1 · 角色零事件（低优先，定性题）

```cypher
MATCH (c:Character) WHERE NOT (c)-[:involved]->()
RETURN c.id AS id, c.name AS name, c.priority AS priority LIMIT 50
```

### X1 · 孤立事件（无 evt_relation / leads_to，medium）

```cypher
MATCH (e:Event)
WHERE NOT (e)-[:evt_relation]->() AND NOT (e)<-[:evt_relation]-()
  AND NOT (e)-[:leads_to]->() AND NOT (e)<-[:leads_to]-()
RETURN e.id AS id, e.title AS title, e.time AS time LIMIT 100
```

### X2 · Choice 选项无落点（high，分支断头）

```cypher
MATCH (c:Choice)
OPTIONAL MATCH (c)-[op:option]->(t:Event)
WITH c, collect(op.label) AS labels, count(t) AS targets
WHERE targets = 0 OR targets < size(labels)
MATCH (e:Event)-[:presents]->(c)
RETURN c.id AS choice_id, c.name AS name, labels, targets, e.title AS trigger_event LIMIT 20
```

---

## 一b、V 组 · 内容缺口（承自 grower，2026-10-12 合并；查「该有而没有的」）

> grower 的 10 检查分流归并：temporal_gaps + narrative_density → **V1**；character_arcs + subgraph_connectivity → **V2**；implicit_relations → **V3**；info_depth → **V4**；event_chains → 即 X1（同检查，勿重复）；scene_utilization / bridge_scenes / relationship_evolution 为纯统计无动作（dashboard `/events/checkup` 已有同款），弃。

### V1 · 时间线密度（medium，创作类）——大间隔 + 过稀日合并查

```cypher
MATCH (e:Event) WHERE e.time IS NOT NULL RETURN DISTINCT e.time AS t
```
Python 后处理：`datetime.strptime(t, '%Y-%m-%d %H:%M:%S')` 解析 → ① 相邻日差 ≥3 = 大间隔（from/to/gap）；② 某日仅 1 事件 = 过稀日。格式异常事件单独报（时间格式本身即缺口）。

### V2 · 角色弧薄弱（medium，创作类）——事件少 + 场景窄

```cypher
// (1) P0/P1 involved < 5（备用角色/美术存档类先看 description 排除）
MATCH (c:Character) OPTIONAL MATCH (c)-[:involved]->(e:Event)
WITH c, count(e) AS ev WHERE coalesce(c.priority,'') IN ['P0','P1'] AND ev < 5
RETURN c.id AS id, c.name AS name, c.priority AS p, ev, c.description AS d ORDER BY ev
// (2) P0/P1 活动地点 < 2（空间维度，occurs_at 一跳）
MATCH (c:Character) OPTIONAL MATCH (c)-[:involved]->(e:Event)-[:occurs_at]->(l:Location)
WITH c, count(DISTINCT l) AS locs WHERE coalesce(c.priority,'') IN ['P0','P1'] AND locs < 2
RETURN c.name AS name, locs
```

### V3 · 隐含关系（low，确定性补边）——共同参与 ≥2 事件但无 relation

```cypher
MATCH (a:Character)-[:involved]->(e:Event)<-[:involved]-(b:Character)
WHERE elementId(a) < elementId(b) AND NOT (a)-[:relation]-(b)
WITH a, b, count(DISTINCT e) AS shared, collect(DISTINCT e.title)[..3] AS sample
WHERE shared >= 2
RETURN a.id AS a_id, a.name AS a_name, b.id AS b_id, b.name AS b_name, shared, sample
ORDER BY shared DESC LIMIT 50
```

### V4 · 孤立 Info（low，确定性补边）——无任何边的信息节点

```cypher
MATCH (i:Info) WHERE NOT (i)--() RETURN i.id AS id, i.title AS title, i.content AS content LIMIT 100
```

> `NOT (i)--()` 全向无差别，天然覆盖 link 入向与 leads_to 出入向。

---

## 二、推荐信号规则（rounds 用）

### Location 推荐（四路信号按置信度融合）

| 层 | 信号 | 查询要点 | 旧回测命中率（Spot 粒度，已作废，待重跑） |
|---|---|---|---|
| 1 | 文本地名匹配 | `title+description` 含 Location 全名；miss 后再试核心词（如「八楼出租屋」→「出租屋」） | 全名 23% / 核心词 30% —— 最准，命中即排首 |
| 2 | involved 角色历史足迹 | 已选角色 occurs_at 过的 Location 按次数降序 | 64% —— 必须截 top-5 |
| 3 | 角色 at 边 | `at.type` 居住/工作 Location（直达，不再经 Spot） | 55% |
| 4 | 同日 Location（加分项） | 同 `time` 的 date 部分其他事件的 Location | 旧同日 9% —— 仅并列加分，禁单独成题 |

融合打分：`score = 3·文本 + 2·at边 + 1·历史次数 + 1·同日`，top-5 出 chips。

```cypher
// 信号2+3 一次查全（<char_names> 为已定 involved）
MATCH (c:Character)-[:involved]->(:Event)-[:occurs_at]->(l:Location)
WHERE c.name IN ['<char1>','<char2>']
RETURN l.id AS id, l.name AS name, count(*) AS freq ORDER BY freq DESC LIMIT 5;
MATCH (c:Character)-[a:at]->(l:Location)
WHERE c.name IN ['<char1>'] RETURN DISTINCT l.id AS id, l.name AS name, a.type AS at_type LIMIT 10;
```

### Char 推荐（已定 Location 后联动）

| 信号 | 旧回测命中率（已作废，待重跑） |
|---|---|
| 1. 该 Location 历史参与者（次数降序 top-3）| 65% |
| 2. at 边挂此 Location 的居民 | 57% —— 最准 |
| 3. 同日参与者 | 43% |

```cypher
MATCH (c:Character)-[:involved]->(:Event)-[:occurs_at]->(l:Location {id:'<loc_id>'})
RETURN c.name AS name, count(*) AS freq ORDER BY freq DESC LIMIT 3;
```

### 禁用与兜底

- **evt_relation / leads_to 邻居信号禁用**：邻接事件同地点比例回测仅 16%（事件链跨空间推进），不得使用。
- **冷启动盲区**：一次性/首访地点（理发店、漫展会场、登山步道…）无任何历史信号。推荐「新建 Location」并明示无历史依据；完整 Location 候选列表永远在选项里兜底。**不建 Spot**——场景化时 scene-designer 兜底。
- 理由标签格式：「文案提及」/「<角色>常来×N」/「<角色>居住地」/「当日出现」/「此处常客×N」/「此处居民」。

---

## 三、修复 cypher 模板（commit 用）

### E1 挂既有 Location

```cypher
MATCH (e:Event {id:'<eid>'}), (l:Location {id:'<lid>'})
MERGE (e)-[r:occurs_at]->(l)
ON CREATE SET r.sync = false;
```

### E1 + 新建地点（只建 Location，不建 Spot）

```cypher
// <new_loc_id> 由 $SF_GEN 生成
CREATE (l:Location {id:'<new_loc_id>'}) SET l.name = '<地点名>', l.description = '<一句描述>';
MATCH (e:Event {id:'<eid>'}), (l:Location {id:'<new_loc_id>'})
MERGE (e)-[r:occurs_at]->(l) ON CREATE SET r.sync = false;
```

### E2/S1/S2 场景化派单（不建骨架，只出指引）

新流程中 Spot 归组、Scene、机位、room.yml 是 scene-designer 一体化的三段式，**手工建 Scene/anchored_at 骨架=半成品**。建议项 `cypher` 留空串，`content` 写派单指引：「写回后从生产看板一键派单 scene-design agent，入参 `<loc_id>` / `<spot_id>`」。

### E3 挂既有角色

```cypher
MATCH (c:Character {id:'<cid>'}), (e:Event {id:'<eid>'})
MERGE (c)-[r:involved]->(e) SET r.role = '<建议值：当事人/目击者/参与者>', r.sync = false;
```

### X1 补 leads_to / evt_relation、X2 补落点事件

X1 因果链：`MATCH (a {id:'<from>'}), (b {id:'<to>'}) WHERE (a:Event OR a:Info) AND (b:Event OR b:Info) MERGE (a)-[r:leads_to]->(b) ON CREATE SET r.detail = '<因果语境>', r.sync = false;`；时序/包含沿用 evt_relation（type 仅 先后/包含）。X2 新建目标 Event（`$SF_GEN` id + ending_kind 按选项语义）+ `MERGE (c:Choice {id:'<cid>'})-[op:option]->(t)` 置 `op.label`/`op.leads_to_ending`。

---

## 四、回测脚本备档

回测方法：47 个已定位事件 leave-one-out（候选统计排除事件自身），逐信号统计真值落入候选的比例与候选规模。回测脚本曾出现两个污染 bug（统计字典在循环外复用、把真答案从候选排除），修正后数据如下（2026-10-12，**Spot 粒度旧模型，已作废**）：

- Spot：文本全名 23%、核心词 30%、同日 9%、at边 55%、历史足迹 64%、组合 89%
- Char：Spot 常客 65%、at 居民 57%、同日 43%、组合 87%
- evt_relation 邻居同 Spot 16%（76 邻接对中 12）→ 禁用

**2026-10-13 叙事基础重构后**：推荐粒度 Spot→Location、信号2/3 查询链路变短、Spot 维度信号消失——结构性变更，上述数字不可引用。迁移完成后重跑 leave-one-out（真值 Location = 旧 occurs_at 两跳的等价换算）重建基线。
