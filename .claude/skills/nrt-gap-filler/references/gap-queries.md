# 缺口检查查询库 + 推荐规则

> nrt-gap-filler 的执行参考。五组检查（E/C/X/V/H）的 cypher 模板 + focus 变体 + 入参定界 + 推荐信号规则。
> **范畴 = 叙事基础层五实体**（Character/Event/Location/Info/Choice）及其八边；Spot/Scene/anchored_at/realizes 属场景域（scene-designer 独占），不在本查询库。
> 推荐规则曾带 2026-10-12 存量图回测（n=47）命中率背书——**2026-10-13 叙事基础重构（occurs_at 直挂 Location / Spot 移出叙事基础层 / leads_to 统一因果）为结构性变更，旧命中率全部作废**；迁移完成后须用新图重跑 leave-one-out 重建基线。

## 一、缺口检查（scan 用）

### E1 · Event 缺 occurs_at（high，叙事定位缺失）

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

### E3 · Event 缺 involved 且非结局事件（medium）

```cypher
MATCH (e:Event)
WHERE NOT (e)<-[:involved]-() AND coalesce(e.ending_kind, '') = ''
RETURN e.id AS id, e.title AS title, e.time AS time LIMIT 50
```

> ending_kind 非空的结局事件豁免——身份由 `Choice -option{leads_to_ending}-> Event` 承载（实测先例：「跳江BE」）。

### C1 · 角色零事件（low，定性题）

```cypher
MATCH (c:Character) WHERE NOT (c)-[:involved]->()
RETURN c.id AS id, c.name AS name, c.priority AS priority LIMIT 50
```

### X1 · 孤立事件（无 leads_to，medium）

```cypher
MATCH (e:Event)
WHERE NOT (e)-[:leads_to]-()
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

> grower 的 10 检查分流归并：temporal_gaps + narrative_density → **V1**；character_arcs + subgraph_connectivity → **V2**；implicit_relations → **V3**；info_depth → **V4**；event_chains → 即 X1（同检查，勿重复）；scene_utilization / bridge_scenes / relationship_evolution 为场景域统计且纯统计无动作——随 Spot 出圈（2026-10-13 重构 + 2026-10-14 范畴收窄）一并弃，场景域体检归 scene-designer 链。

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
// (2) P0/P1 活动地点 < 2（空间维度，occurs_at 一跳直挂 Location）
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

> Memgraph/Neo4j 双后端零分支：若 `elementId` 不适配（Memgraph 旧版），改 `WHERE id(a) < id(b)`（拆两写各自跑）。

### V4 · 孤立 Info（low，确定性补边）——无任何边的信息节点

```cypher
MATCH (i:Info) WHERE NOT (i)--() RETURN i.id AS id, i.title AS title, i.content AS content LIMIT 100
```

> `NOT (i)--()` 全向无差别，天然覆盖 link 入向与 leads_to 出入向。Info 可挂的两类边：`link`（任意关联，Character↔Info / Location→Info / Info→Info）与 `leads_to`（因果，Info↔Event 双向 + Info→Info）——修法在两者间选，因果语义一律 leads_to。

---

## 一c、H 组 · 启发式填充（2026-10-15 新增；显式聚焦时跑，查「值得填充的时刻」）

> 与 V 组的差异：V 查指标缺口（密度/计数阈值判定）；H 在**给定范围**（时间窗/人物）内侦察叙事上下文后由 LLM 启发选点，产出全是创作类草案。**稀疏纪律：单次 ≤3 Event + ≤2 Info**，候选超限只取优先级最高者，其余汇报为「下次可补」——多次运行逐步丰满，不是一次填满。

### 入参定界（resolve 用）

| 入参形态 | 判定 | 结果 |
|---|---|---|
| 单参数命中 Character | `MATCH (c:Character) WHERE c.name='<p>' OR c.id='<p>'` | 人物聚焦模式（E/C/X/V 收窄 + H2） |
| `起始~结束` 时间串 | 两段均可 `datetime.strptime` 解析（`%Y-%m-%d %H:%M:%S` 或 `%Y-%m-%d`，日期补 `00:00:00` / `23:59:59`） | 显式时间窗 → H1 |
| 两个事件（`A → B` / `A B` / `A 到 B` / `A 至 B`） | 按 title/id 各查一个 Event | 事件定界窗 → H1（并取两事件 involved/occurs_at/description 作叙事上下文） |

```cypher
// 事件定界 + 叙事上下文（两事件各命中恰一个才有效）
MATCH (e:Event) WHERE e.title IN ['<A>','<B>'] OR e.id IN ['<idA>','<idB>']
OPTIONAL MATCH (c:Character)-[:involved]->(e)
OPTIONAL MATCH (e)-[:occurs_at]->(l:Location)
RETURN e.id AS id, e.title AS title, e.time AS time, e.description AS description,
       collect(DISTINCT c.name) AS chars, l.name AS loc ORDER BY e.time
```

定界失败（查无事件/时间不可解析/命中多于一个）→ 澄清，勿猜。t_start ≥ t_end → 交换或澄清。

### H1 · 时间窗启发填充（时间窗模式专属，medium）

```cypher
// 窗口侦察：一次查全（事件+参与人+地点+因果邻接）
// time 为 yyyy-MM-dd HH:mm:ss 字符串序即时间序（Schema 约定），直接字符串比较；格式异常事件不落窗（V1 另行报）
MATCH (e:Event) WHERE e.time >= '<t_start>' AND e.time <= '<t_end>'
OPTIONAL MATCH (c:Character)-[:involved]->(e)
OPTIONAL MATCH (e)-[:occurs_at]->(l:Location)
OPTIONAL MATCH (e)-[:leads_to]->(nxt:Event)
RETURN e.id AS id, e.title AS title, e.time AS time, e.type AS type, e.description AS description,
       collect(DISTINCT c.name) AS chars, l.name AS loc, collect(DISTINCT nxt.title) AS leads
ORDER BY e.time LIMIT 100
```

Python 后处理：窗口逐日标记有无事件 → 空白日/多日间隔清单。侦察暴露的窗口内 E1/E3（缺 occurs_at/involved 的既有事件）按原修法走（挂边，非创作）。

> **⚠ Memgraph 兼容（2026-10-19 实测）**：上面这条侦察查询在 Memgraph 报 `Unbound variable: e`——MATCH+WHERE 后连挂多个 OPTIONAL MATCH 再聚合时，后续 OPTIONAL MATCH 引用 `e` 会失绑。**不要原样跑**：最稳是拆成每关系一条简单查询（时间窗本体 / `involved` / `occurs_at` / `leads_to` 各一条，后者用 `WHERE e.id IN[…]`），Python 侧按 id 组装；WITH 物化中转也可能触发同错。

**插入点启发（优先级序，候选超限时只取前几个）**：
1. **因果跳变桥接**：A 与 B 时序紧邻或有 leads_to，但 description 内容跳脱（质问→庆祝、冲突→和解）→ 中点时刻提议过渡事件。
2. **钩子收尾**：边界/窗口事件的 description 留了未接细节（未接来电/未回消息/发现线索）→ 紧邻其后提议跟进事件或 Info。
3. **长空白点缀**：连续 ≥2 日无事件 → 空白日中段提议 1 个日常事件（维持时间感，不推进主线）。

草案 time 必须在窗口内、避开与既有事件同一时刻（同日不同时分）。

### H2 · 人物自由探索丰满（人物模式专属，low）

```cypher
// 人物全景（计数）
MATCH (c:Character) WHERE c.name = '<focus>' OR c.id = '<focus>'
OPTIONAL MATCH (c)-[:involved]->(e:Event)
OPTIONAL MATCH (c)-[:relation]->(o:Character)
OPTIONAL MATCH (c)-[:link]-(i:Info)
RETURN c.id AS id, c.name AS name, c.priority AS p, c.description AS d,
       count(DISTINCT e) AS events, count(DISTINCT o) AS rels, count(DISTINCT i) AS infos;
// 时间线明细
MATCH (c:Character)-[:involved]->(e:Event) WHERE c.name = '<focus>'
RETURN e.time AS time, e.title AS title, e.description AS description ORDER BY time LIMIT 100
```

**启发维度（优先级序）**：
1. **事件薄期**：时间线上该人物连续 ≥3 日无事件 → 日常事件提案（做什么/遇谁，与既有 Location/角色勾连优先）。
2. **内心戏缺失**：人物只「行动」没「想法」（events 多而 infos 少）→ Info 提案（秘密/动机/情绪）。
3. **关系空白**：复用 V3 结果（共同出场无 relation）作人物模式的一个子题，不另跑。
4. **日常切片**（最低优先，前三类无可提案时才启用，单次至多 1 个）：非主线生活切片（爱好/习惯/小波折）。

### 稀疏纪律（H 组通用）

- 单次提案上限 **3 Event + 2 Info**；超限只取优先级最高者，其余在汇报中列为「下次可补」。
- 留白即叙事：「接受留白/下次再说」永远在选项里，且低信号时是推荐项。
- **去重**：提案前扫最近一轮 `${OUTPUT_DIR}/*_建议.json` 的 H 组条目——已提案未审批的插入点标「上轮已提案待审」，不再重复草案，只提醒审批状态。
- 新事件/新 Info 的 occurs_at / involved / link 边按联动推荐**同题追问**（级联纪律同 V 组，不留新缺口下库）。

---

## 二、推荐信号规则（rounds 用）

### Location 推荐（四路信号按置信度融合）

| 层 | 信号 | 查询要点 |
|---|---|---|
| 1 | 文本地名匹配 | `title+description` 含 Location 全名；miss 后再试核心词（如「八楼出租屋」→「出租屋」）——最准，命中即排首 |
| 2 | involved 角色历史足迹 | 已选角色 occurs_at 过的 Location 按次数降序——必须截 top-5 |
| 3 | 角色 at 边 | `at.type` 居住/工作 Location（一跳直达） |
| 4 | 同日 Location（加分项） | 同 `time` 的 date 部分其他事件的 Location——仅并列加分，禁单独成题 |

融合打分：`score = 3·文本 + 2·at边 + 1·历史次数 + 1·同日`，top-5 出 chips。
（旧回测命中率：文本全名 23% / 核心词 30% / at边 55% / 历史足迹 64% / 同日 9%——Spot 粒度数字，已作废待重跑，仅作信号间相对强弱参考。）

```cypher
// 信号2+3 一次查全（<char_names> 为已定 involved）
MATCH (c:Character)-[:involved]->(:Event)-[:occurs_at]->(l:Location)
WHERE c.name IN ['<char1>','<char2>']
RETURN l.id AS id, l.name AS name, count(*) AS freq ORDER BY freq DESC LIMIT 5;
MATCH (c:Character)-[a:at]->(l:Location)
WHERE c.name IN ['<char1>'] RETURN DISTINCT l.id AS id, l.name AS name, a.type AS at_type LIMIT 10;
```

### Char 推荐（已定 Location 后联动）

| 信号 | 查询要点 |
|---|---|
| 1. 该 Location 历史参与者 | 次数降序 top-3 |
| 2. at 边挂此 Location 的居民 | 最准 |
| 3. 同日参与者 | 并列加分 |

```cypher
MATCH (c:Character)-[:involved]->(:Event)-[:occurs_at]->(l:Location {id:'<loc_id>'})
RETURN c.name AS name, count(*) AS freq ORDER BY freq DESC LIMIT 3;
```

### Info/Choice 联动推荐（X2/V4 用）

- **X2 补落点事件**：新 Event 的 involved/occurs_at 承 **presents 上游事件**（分支与主干同场同人是叙事惯例，facts 现查上游事件的 involved 角色与 occurs_at 地点，直接作推荐）；ending_kind 按选项语义定（`op.leads_to_ending` 为真 → 按选项 label 定 BE/TE/HE/NE）。
- **V4 孤立 Info 补边**：候选 = ① 时间邻近（Info 关联事件 time ±1 日内的 Event/Info）→ ② title/content 文本包含关系（Info.title 中的角色名/地名即候选锚点，名称查 id 现查）→ ③ 同源事件（若 Info 经历史快照可追溯来源事件）。因果语义用 leads_to，泛关联用 link。

### 禁用与兜底

- **leads_to 邻居信号禁用**：邻接事件同地点比例回测仅 16%（事件链跨空间推进；回测基于旧 evt_relation 邻接，因果链语义同），不得用于 Location/Char 推荐。
- **冷启动盲区**：一次性/首访地点（理发店、漫展会场、登山步道…）无任何历史信号。推荐「新建 Location」并明示无历史依据；完整 Location 候选列表永远在选项里兜底。
- 理由标签格式：「文案提及」/「<角色>常来×N」/「<角色>居住地」/「当日出现」/「此处常客×N」/「此处居民」/「承上游事件（分支惯例）」。

---

## 三、修复 cypher 模板（commit 用）

### E1 挂既有 Location

```cypher
MATCH (e:Event {id:'<eid>'}), (l:Location {id:'<lid>'})
MERGE (e)-[r:occurs_at]->(l)
ON CREATE SET r.sync = false;
```

### E1 + 新建地点

```cypher
// <new_loc_id> 由 $SF_GEN 生成
CREATE (l:Location {id:'<new_loc_id>'}) SET l.name = '<地点名>', l.description = '<一句描述>';
MATCH (e:Event {id:'<eid>'}), (l:Location {id:'<new_loc_id>'})
MERGE (e)-[r:occurs_at]->(l) ON CREATE SET r.sync = false;
```

### E3 挂既有角色

```cypher
MATCH (c:Character {id:'<cid>'}), (e:Event {id:'<eid>'})
MERGE (c)-[r:involved]->(e) SET r.role = '<建议值：当事人/目击者/参与者>', r.sync = false;
```

### X1 补 leads_to

因果链：`MATCH (a {id:'<from>'}), (b {id:'<to>'}) WHERE (a:Event OR a:Info) AND (b:Event OR b:Info) MERGE (a)-[r:leads_to]->(b) ON CREATE SET r.detail = '<因果语境>', r.sync = false;`
时序不建边，由 Event.time 承载。

### X2 补落点事件（创作类，先节点后边）

```cypher
// <new_eid> 由 $SF_GEN 生成；ending_kind 按选项语义（BE/TE/HE/NE 或留空）
CREATE (t:Event {id:'<new_eid>'}) SET t.title = '<事件标题>', t.time = '<yyyy-MM-dd HH:mm:ss 承上游事件时间推算>', t.ending_kind = '<按需>';
MATCH (c:Choice {id:'<cid>'}) MERGE (c)-[op:option]->(t) SET op.label = '<选项label>', op.leads_to_ending = <true/false>;
// 新 Event 的 occurs_at / involved 按联动推荐另出语句（同 V 组级联纪律，不留新缺口）
```

### V3 补 relation 边

```cypher
MATCH (a:Character {id:'<aid>'}), (b:Character {id:'<bid>'})
MERGE (a)-[r:relation]->(b) SET r.type = '<如：恋爱/同事/对手>', r.detail = '<按需>', r.sync = false;
```

### V4 补 Info 边（link / leads_to 二选一）

```cypher
// 因果/导致 → leads_to（方向：因→果）
MATCH (i:Info {id:'<iid>'}), (n {id:'<nid>'}) WHERE n:Event OR n:Info
MERGE (i)-[r:leads_to]->(n) ON CREATE SET r.detail = '<因果语境>', r.sync = false;
// 泛关联 → link（type 必填）
MATCH (i:Info {id:'<iid>'}), (c:Character {id:'<cid>'})
MERGE (i)-[r:link]->(c) SET r.type = '<如：涉及>', r.sync = false;
```

### H 组创作类新事件（X2 亦通用；先节点后边）

```cypher
// <new_eid> 由 $SF_GEN 生成；time 在窗口内、避开与既有事件同一时刻（同日不同时分）
// type 用合法枚举：行动/交流/转折/状态变化（日常事件多为 行动 或 交流，勿发明新值）
CREATE (e:Event {id:'<new_eid>'}) SET e.title='<草案标题>', e.time='<yyyy-MM-dd HH:mm:ss>',
       e.type='<行动|交流|转折|状态变化>', e.description='<一句话草案>';
// 桥接类（因果跳变补过渡）另出 leads_to：
MATCH (a:Event {id:'<aid>'}), (e:Event {id:'<new_eid>'})
MERGE (a)-[r:leads_to]->(e) ON CREATE SET r.detail='<因果语境>', r.sync = false;
// occurs_at / involved 按联动推荐另出语句（级联纪律，不留新缺口）
```

### H 组创作类新 Info

```cypher
// <new_iid> 由 $SF_GEN 生成；knowledge_level 必填：1 表层/2 参与层/3 深层（秘密/动机/内心推断类默认 3）
CREATE (i:Info {id:'<new_iid>'}) SET i.title='<草案标题>', i.content='<草案内容>', i.knowledge_level='<1|2|3>';
// link/leads_to 按 V4 联动推荐另出语句
```

---

## 四、回测脚本备档

回测方法：47 个已定位事件 leave-one-out（候选统计排除事件自身），逐信号统计真值落入候选的比例与候选规模。回测脚本曾出现两个污染 bug（统计字典在循环外复用、把真答案从候选排除），修正后数据如下（2026-10-12，**Spot 粒度旧模型，已作废**）：

- Spot：文本全名 23%、核心词 30%、同日 9%、at边 55%、历史足迹 64%、组合 89%
- Char：Spot 常客 65%、at 居民 57%、同日 43%、组合 87%
- evt_relation 邻居同 Spot 16%（76 邻接对中 12）→ 禁用

**2026-10-13 叙事基础重构后**：推荐粒度 Spot→Location、信号2/3 查询链路变短、Spot 维度信号消失；**2026-10-14 起本 skill 范畴收窄至五实体关系闭环，Spot/Scene 类检查与信号整体出圈**——结构性变更，上述数字不可引用。迁移完成后重跑 leave-one-out（真值 Location = occurs_at 一跳直值，较旧两跳更简单）重建基线。
