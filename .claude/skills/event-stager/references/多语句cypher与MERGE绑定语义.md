# 发现：建议 JSON 多语句 cypher 的 MERGE 绑定语义（2026-11-02 事故）

> 2024-06-12 两事件重细化建议经 dashboard 弹窗执行后，图上出现 6 组重复 id 节点 +
> 2 个无属性幽灵节点，三个新 sub 的 anchored_at 全挂在重复节点上、第二条着装边全部丢失。
> 本文档固化根因分析与正确写法。**此结论已联网查证（Neo4j 官方 manual + GraphAware
> 《Cypher MERGE explained》），不是 Memgraph 特有行为，Neo4j 与 Memgraph 行为一致。**

## 执行链路（为什么会拆条）

dashboard `POST /events/suggest/apply`（app/main.py）与 Cypher 控制台同级语义，走
`cascade.execute_with_cascade` → `cascade.split_statements()` 把整段建议 cypher 按 `;`
拆成多条语句逐条执行。cypher_exec 的 `--multi` 同理。

## 根因一：变量不跨语句延续（Cypher 标准语义，两引擎一致）

`;` 分隔的每条语句是独立查询，变量作用域不越界。写：

```cypher
CREATE (sp:Spot {id:'X'}) SET sp.name='...';
MATCH (l:Location {id:'L'}) MERGE (l)-[r:part_of]->(sp) ON CREATE SET r.sync=false;
```

第二条里 `sp` 是**悬空变量**——`MERGE (l)-[part_of]->(sp)` 匹配到 l 的**既有** part_of
边（pattern 命中）→ 新 Spot 的挂边**静默失败，不报错**；若 pattern 未命中则建出
无属性幽灵节点再挂边。Neo4j 上同样如此。

## 根因二：MERGE 整 pattern 语义——未绑定端点建重复节点（Cypher 标准语义，两引擎一致）

即使变量已绑定，MERGE 的语义是**匹配整条 pattern，未命中则创建整条 pattern**：

```cypher
MATCH (e:Event {id:'E'}) MERGE (sub:SubEvent {id:'S'}) ... MERGE (e)-[r:refines]->(sub);
MERGE (sub)-[a:anchored_at]->(scn:Scene {id:'已有id'})   // ← 事故写法
```

第二条语句里 `sub` 悬空（跨语句）、`scn` 未绑定且带属性。MERGE 拿整条
`(sub)-[anchored_at]->(scn:Scene {id})` 去匹配，匹配不到（边不存在）→ **整条创建**：
新建一个只带 `{id}` 的重复 Scene 节点 + 幽灵 sub，anchored_at 挂在重复节点上。

- GraphAware《Cypher MERGE explained》Example 4 与此形态完全同构：核心概念
  **bound elements**——*"It will not use partially existing patterns — it will attempt
  to match the entire pattern and create the entire pattern if missing"*；
- 官方修法即 *"remember to bind elements"*：不想被重建的端点必须先绑定；
- StackOverflow（Neo4j）：*"MERGE on a pattern with an unbound variable will just
  create the entire pattern (including creating an empty node for unbound node
  variables)"*。

## 正确写法（铁律）

1. **每条 `;` 语句自包含**：不引用前一条语句的变量；
2. **MERGE 边的两端点都在本语句内先 MATCH（或 CREATE）绑定**：

```cypher
// 节点本体
CREATE (sp:Spot {id:'X'}) SET sp.name='...', sp.kind='zone', sp.status=0;
// 边：两端点各自 MATCH 绑定，MERGE 只负责边本身
MATCH (l:Location {id:'L'}) MATCH (sp:Spot {id:'X'}) MERGE (l)-[r:part_of]->(sp) ON CREATE SET r.sync=false;
// SubEvent 本体 + 父边一体；anchored_at / appears_as 各自独立成语句
MATCH (e:Event {id:'E'}) MERGE (sub:SubEvent {id:'S'})
ON CREATE SET sub.title='...', sub.time='...', sub.description='...'
MERGE (e)-[r:refines]->(sub) ON CREATE SET r.sync=true;
MATCH (sub:SubEvent {id:'S'}) MATCH (scn:Scene {id:'Y'})
MERGE (sub)-[a:anchored_at]->(scn) ON CREATE SET a.sync=false;
MATCH (sub:SubEvent {id:'S'}) MATCH (il:IllusDesign {id:'Z'})
MERGE (sub)-[ap:appears_as]->(il) ON CREATE SET ap.sync=false, ap.detail='继承：...';
```

3. **落盘前断言**：逐语句扫描悬空变量（节点模式声明的变量集 ⊇ 边端点变量集）；
4. **执行后回查必含**：
   - 重复 id：`MATCH (n) WHERE n.id IS NOT NULL WITH n.id AS id, count(*) AS c WHERE c>1 RETURN id, c`（期望 0 行）；
   - 幽灵节点：`MATCH (n) WHERE size(labels(n))=0 RETURN id(n)`（期望 0 行）；
   - 目标节点逐 id 三边回读（本体 + refines/anchored_at/appears_as）。

## 事故实录（对账数据）

- 事故建议：`02_剧情数据/2024-06-12_round1_stager重细化_stager_建议.json`（v1，已废弃；
  同日 v2 修复版重写为自包含语句后同路径覆盖）；
- 受害形态：重复 id 6 组（QmQCxuTrGK×3、RVaUJp92GH / R22lVGrBuC / Rk4VzrBkTh /
  NyJ99Sgpft / QmFVxZtCtc 各×2，重复者全部只有 `{id}` 一个属性）+ 无 label 幽灵 2 个；
  图库由快照整体还原恢复；
- 附带疑点：第 4 项执行 `cascade=8`（8 节点被级联置 -1），因无执行前基线未能归因，
  还原后未复现。
