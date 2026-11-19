# 认知（Cognition）

一条认知持有：**某角色对某条 Info 当前以什么态度持有什么认知**。中间节点层——
知晓分布的唯一判源（封闭世界：无 Cognition 链 = 不知情）。

整句读法：`<角色> 在 <forms 边的事件> 中，对 <about 边的 Info> 形成了 <type [+title]> 的认知`。

- 三边：`Character ─has_cognition→ Cognition ─about→ Info`，`Event ─forms→ Cognition`
  （边定义见 [边.md](边.md)）。
- **封闭世界**：角色对某 Info 无 has_cognition 链 = 该角色不知道这条 Info。只给
  知情者/偏差者建节点，不做「不知道」显式节点；因此知情盘点必须完整——漏建节点
  会被判「不知道」。
- **当前态（无历史字段）**：不设 status/时间字段，Cognition 只反映当前态度。每对
  `(Character, Info)` **至多一个** Cognition 节点；态度转变 = 就地改写（type/title
  改写、forms 换锚转变事件），不得并存新旧两态。转变本身的留痕走 Info 层：有叙事
  意义的转变由转变事件 `establishes` 新 Info 承载；「他何时变的」= forms 锚事件的
  start_time。
- **forms 必填 ≥1**：认知必有来处（开篇前固有认知走前史事件承载，不开免挂口）。
- 与 `Event ─establishes→ Info`（成立轴）分工：establishes 答「事实因何成立」，
  Cognition 答「谁以什么态度知道」；事件 involved 参与不推导出任何知情
  （「参与即知情」已废止）。

## 字段

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| type | 认知态度 | enum | 是 | `KNOWS` / `BELIEVES` / `SUSPECTS` / `DOUBTS`（语义参考表见下，**非门禁**） |
| title | 认知内容 | string | **条件** | **仅当所信命题 ≠ Info 的 title 时必填**——认知偏差内容（如 Info「A假死」而此角色信「A真死亡」），与 Info 同名对齐。所信=事实（完全认知）**不填**，填了即复述，违规。干净的事实陈述，禁备忘/推导文字 |
| note | 备注 | string | 否 | 仅存「图上无载体」的增量（如认知依据的极简锚点），禁备忘 |

## type 语义参考表（写作参考，非门禁）

type 答「以什么态度持有」，title 答「实际信的是什么」：

| type | 语义参考 | title |
|------|----------|-------|
| `KNOWS` | 确知：正确且有所本 | 恒空 |
| `BELIEVES` | 持明确命题但未达确知 | 所信=事实→空（无实据但猜对）；所信≠事实→必填 |
| `SUSPECTS` | 对 Info 命题起疑/趋向其为真，无明确替代命题 | 恒空（形成替代命题时升 BELIEVES+title） |
| `DOUBTS` | 拒绝接受 Info 命题为真（嘴硬/否认） | 恒空（持明确反向命题时升 BELIEVES+title） |

参考推论：「信错」典型落法 = BELIEVES + title（偏差命题）；KNOWS/SUSPECTS/DOUBTS
是对 Info 命题本身的正/疑/否认姿态。判定测试：拿掉 title 这条认知还能定位吗——
能（态度指向 Info 本身）→ 不该有 title；不能（信另一命题）→ 必须有 title。

## 建边模板（幂等）

```cypher
// 新建：先查后建（保证 (Character, Info) 唯一）
MATCH (ch:Character {id:'…'}) MATCH (i:Info {id:'…'})
OPTIONAL MATCH (ch)-[:has_cognition]->(ex:Cognition)-[:about]->(i)
WITH ch, i, ex WHERE ex IS NULL
CREATE (c:Cognition {id:'<snowflake>'}) SET c.type='KNOWS'
CREATE (ch)-[:has_cognition]->(c)
CREATE (c)-[:about]->(i)
MATCH (ev:Event {id:'…'}) MATCH (c:Cognition {id:'<snowflake>'})
MERGE (ev)-[f:forms]->(c) ON CREATE SET f.sync=false;

// 改写（态度转变）：就地改 type/title + forms 换锚
MATCH (ch:Character {id:'…'})-[:has_cognition]->(c:Cognition)-[:about]->(i:Info {id:'…'})
SET c.type='KNOWS', c.title=null
OPTIONAL MATCH (old:Event)-[f:forms]->(c) DELETE f
MATCH (ev:Event {id:'…'}) MERGE (ev)-[f2:forms]->(c) ON CREATE SET f2.sync=false;
```
