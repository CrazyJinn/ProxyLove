# 缺口检查查询库 + 推荐规则

> nrt-gap-filler 的执行参考。四组检查（E/S/C/X）的 cypher 模板 + focus 变体 + 推荐信号规则。
> 推荐规则全部带 2026-10-12 存量图回测（n=47 已定位事件 leave-one-out）命中率背书——改动规则前先重跑回测。

## 一、缺口检查（scan 用）

### E1 · Event 缺 occurs_at（high，直接生产隐形）

```cypher
// 全图版
MATCH (e:Event) WHERE NOT (e)-[:occurs_at]->()
OPTIONAL MATCH (c:Character)-[:involved]->(e)
WITH e, collect(DISTINCT c.name) AS chars
RETURN e.id AS id, e.title AS title, e.time AS time, e.type AS type,
       e.description AS description, e.ending_kind AS ending_kind, chars
ORDER BY e.time LIMIT 100
```

focus 版（锚点 1 跳）：`MATCH (c0:Character) WHERE c0.name='<focus>' OR c0.id='<focus>' MATCH (c0)-[:involved]->(e:Event) WHERE NOT (e)-[:occurs_at]->() …`

### E2 · Event 挂的 Spot 无 realizes（high，挂了也白挂）

```cypher
MATCH (e:Event)-[:occurs_at]->(sp:Spot)
WHERE NOT (sp)-[:realizes]->()
RETURN sp.id AS spot_id, sp.name AS spot, sp.kind AS kind,
       collect({id: e.id, title: e.title, time: e.time}) AS events,
       count(e) AS n
ORDER BY n DESC LIMIT 50
```

### E3 · Event 缺 involved 且非结局事件（medium）

```cypher
MATCH (e:Event)
WHERE NOT (e)<-[:involved]-() AND coalesce(e.ending_kind, '') = ''
RETURN e.id AS id, e.title AS title, e.time AS time LIMIT 50
```

> ending_kind 非空的结局事件豁免——身份由 `Choice -option{leads_to_ending}-> Event` 承载（实测先例：「跳江BE」）。

### S1 · Spot 有事件待场景化（E2 的 Spot 聚合视角）

同 E2 查询即得（events 聚合列）。修复动作 = 建 Scene + realizes 或整组改挂。

### S2 · Location 缺 default Spot（high，违反 Schema 不变式）

```cypher
MATCH (l:Location)
WHERE NOT EXISTS { MATCH (l)<-[:part_of]-(sp:Spot {kind:'default'}) }
RETURN l.id AS id, l.name AS name LIMIT 50
```

> Memgraph/Neo4j 双后端零分支：若 EXISTS 语法不适配，改 `OPTIONAL MATCH (l)<-[:part_of]-(sp:Spot {kind:'default'}) WITH l, count(sp) AS n WHERE n = 0`。

### C1 · 角色零事件（低优先，定性题）

```cypher
MATCH (c:Character) WHERE NOT (c)-[:involved]->()
RETURN c.id AS id, c.name AS name, c.priority AS priority LIMIT 50
```

### X1 · 孤立事件（无 evt_relation，medium）

```cypher
MATCH (e:Event)
WHERE NOT (e)-[:evt_relation]->() AND NOT (e)<-[:evt_relation]-()
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
Python 后处理：解析 `Day (\d+)` → ① 相邻日差 ≥3 = 大间隔（from/to/gap）；② 某日仅 1 事件 = 过稀日。开场/后日谈等非 Day 格式跳过。
实测样例（2026-10-12）：大间隔无，但过稀日 16 天（Day 3~22 段几乎天天薄）。

### V2 · 角色弧薄弱（medium，创作类）——事件少 + 场景窄

```cypher
// (1) P0/P1 involved < 5（备用角色/美术存档类先看 description 排除）
MATCH (c:Character) OPTIONAL MATCH (c)-[:involved]->(e:Event)
WITH c, count(e) AS ev WHERE coalesce(c.priority,'') IN ['P0','P1'] AND ev < 5
RETURN c.id AS id, c.name AS name, c.priority AS p, ev, c.description AS d ORDER BY ev
// (2) P0/P1 活动地点 < 2（空间维度）
MATCH (c:Character) OPTIONAL MATCH (c)-[:involved]->(e:Event)-[:occurs_at]->(:Spot)-[:part_of]->(l:Location)
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

### V4 · 孤立 Info（low，确定性补边）——无任何边的信息节点（仅纯 Info；多 label 后排除 Event/Choice 形态）

```cypher
MATCH (i:Info) WHERE NOT (i)--() AND NOT i:Event AND NOT i:Choice
RETURN i.id AS id, i.title AS title, i.content AS content LIMIT 100
```

---

## 二、推荐信号规则（rounds 用）

### Spot 推荐（四路信号按置信度融合）

| 层 | 信号 | 查询要点 | 回测命中率 | 噪声（命中时候选数） |
|---|---|---|---|---|
| 1 | 文本地名匹配 | `title+description` 含 Location 全名；miss 后再试去前缀核心词（八楼出租屋→出租屋，剥 `0-9八一二三四五六七八九十楼层` 前缀，核心词 ≥2 字） | 全名 23% / 核心词 30% | 1.5 / 2.2 —— 最准，命中即排首 |
| 2 | involved 角色历史足迹 | 已选角色 occurs_at 过的 Spot 按次数降序 | 64% | 20.1 —— 必须截 top-5 |
| 3 | 角色 at 边 | `at.type` 居住/工作 Location 的全部 Spot | 55% | 6.9 |
| 4 | 同 Day Spot（加分项） | 同 `time` 字段其他事件的 Spot | **9%** —— 仅并列加分，禁单独成题 | 4.0 |

组合覆盖率 89%（42/47）。融合打分：`score = 3·文本 + 2·at边 + 1·历史次数 + 1·同日`，top-5 出 chips。

```cypher
// 信号2+3 一次查全（<char_names> 为已定 involved）
MATCH (c:Character)-[:involved]->(:Event)-[:occurs_at]->(sp:Spot)
WHERE c.name IN ['<char1>','<char2>']
RETURN sp.id AS id, sp.name AS name, count(*) AS freq ORDER BY freq DESC LIMIT 5;
MATCH (c:Character)-[a:at]->(l:Location)-[:part_of]-(sp:Spot)
WHERE c.name IN ['<char1>'] RETURN DISTINCT sp.id AS id, sp.name AS name, a.type AS at_type LIMIT 10;
```

### Char 推荐（已定 Spot 后联动）

| 信号 | 回测命中率 | 候选数 |
|---|---|---|
| 1. 该 Spot 历史参与者（次数降序 top-3）| 65% | 3.0 |
| 2. at 边挂此 Location 的居民 | 57% | 1.3 —— 最准 |
| 3. 同 Day 参与者 | 43% | 2.7 |

组合 87%。

```cypher
MATCH (c:Character)-[:involved]->(:Event)-[:occurs_at]->(sp:Spot {id:'<spot_id>'})
RETURN c.name AS name, count(*) AS freq ORDER BY freq DESC LIMIT 3;
```

### 禁用与兜底

- **evt_relation 邻居信号禁用**：邻接事件同 Spot 比例回测仅 16%（事件链跨空间推进），不得使用。
- **冷启动盲区（11% 全 miss）**：一次性/首访地点（理发店、漫展会场、登山步道…）无任何历史信号。推荐「新建 Location+default Spot」并明示无历史依据；完整 Spot 候选列表永远在选项里兜底。
- 理由标签格式：「文案提及」/「<角色>常来×N」/「<角色>居住地」/「当日出现」/「此处常客×N」/「此处居民」。

---

## 三、修复 cypher 模板（commit 用）

### E1 挂既有 Spot

```cypher
MATCH (e:Event {id:'<eid>'}), (sp:Spot {id:'<sid>'})
MERGE (e)-[r:occurs_at]->(sp)
ON CREATE SET r.anchor = CASE WHEN sp.kind = 'zone' THEN 'spot' ELSE 'default' END, r.sync = false;
```

### E1 + 新建地点（S2 联动，节点先于边）

```cypher
// <new_loc_id>/<new_spot_id> 由 $SF_GEN 生成
CREATE (l:Location {id:'<new_loc_id>'}) SET l.name = '<地点名>', l.description = '<一句描述>';
CREATE (sp:Spot {id:'<new_spot_id>'}) SET sp.name = '<地点名>-未细分', sp.kind = 'default', sp.description = '<一句空间描述>';
MATCH (sp:Spot {id:'<new_spot_id>'}), (l:Location {id:'<new_loc_id>'})
MERGE (sp)-[r:part_of]->(l) SET r.sync = false;
MATCH (e:Event {id:'<eid>'}), (sp:Spot {id:'<new_spot_id>'})
MERGE (e)-[r2:occurs_at]->(sp)
ON CREATE SET r2.anchor = 'default', r2.sync = false;
```

### E2 整组场景化派单（建 Scene 骨架 + realizes，出图归 scene-design）

```cypher
// Scene 字段按 00_init/Schema/场景美术.md；scene_type/atmosphere/time_of_day 从事件叙述推断（建议值，content 标可调整）
CREATE (scn:Scene {id:'<new_scene_id>'}) SET scn.name = '<Spot名>', scn.scene_type = '<建议值>',
    scn.atmosphere = '<建议值>', scn.time_of_day = '<建议值>', scn.status = 0;
MATCH (sp:Spot {id:'<sid>'}), (scn:Scene {id:'<new_scene_id>'})
MERGE (sp)-[r:realizes]->(scn) SET r.sync = false;
```

### E3 挂既有角色

```cypher
MATCH (c:Character {id:'<cid>'}), (e:Event {id:'<eid>'})
MERGE (c)-[r:involved]->(e) SET r.role = '<建议值：当事人/目击者/参与者>', r.sync = false;
```

### X1 补 evt_relation / X2 补落点事件

X1 沿用 grower 模板（MATCH 两端真实 id + MERGE 边 + 创意字段建议值）。X2 新建目标 Event 须写多 label 双 label 形态 `MERGE (n:Info:Event {id:'<new_id>'})`（2026-10-12 合并，漏基础 `:Info` 会让新节点游离）+ `MATCH (c:Choice {id:'<cid>'})` 端点按附加 label 匹配 + `[op:option]` 置 `op.label`/`op.leads_to_ending`（ending_kind 按选项语义）。

```cypher
MERGE (n:Info:Event {id:'<new_id>'}) SET n.title='<建议值>', n.time='<建议值>', n.description='<建议值>', n.ending_kind='<按选项语义/留空>';
MATCH (c:Choice {id:'<cid>'}), (n:Event {id:'<new_id>'})
MERGE (c)-[op:option]->(n) SET op.label='<选项文本>', op.leads_to_ending=<true/false>;
```

---

## 四、回测脚本备档

回测方法：47 个已定位事件 leave-one-out（候选统计排除事件自身），逐信号统计真 Spot/真 involved 落入候选的比例与候选规模。回测脚本曾出现两个污染 bug（统计字典在循环外复用、把真答案从候选排除），修正后数据如下（2026-10-12）：

- Spot：文本全名 23%、核心词 30%、同日 9%、at边 55%、历史足迹 64%、组合 89%
- Char：Spot 常客 65%、at 居民 57%、同日 43%、组合 87%
- evt_relation 邻居同 Spot 16%（76 邻接对中 12）→ 禁用

改动推荐规则前重跑回测验证（新缺口修复后图分布会变，命中率会漂移）。
