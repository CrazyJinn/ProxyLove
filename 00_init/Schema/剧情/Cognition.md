# 认知（Cognition）

一条认知持有：**某角色自 forms 锚事件起、对某条 Info 以什么态度持有什么认知**。中间节点层——
知晓分布的唯一判源（封闭世界：时间点 T 无有效认知链 = T 时刻不知情）。

整句读法：`<角色> 在 <forms 边的事件> 中，对 <about 边的 Info> 形成了 <type [+title]> 的认知`。

- 三边：`Character ─has_cognition→ Cognition ─about→ Info`，`Event ─forms→ Cognition`
  （边定义见 [边.md](边.md)）。
- **封闭世界**：角色对某 Info 无 has_cognition 链 = 该角色不知道这条 Info（时间点
  语义：无 forms 锚 start_time ≤ T 的链 = T 时刻不知道）。只给知情者/偏差者建节点，
  不做「不知道」显式节点；因此知情盘点必须完整——漏建节点会被判「不知道」。
- **认知编年史（append-only）**：同一 `(Character, Info)` 允许多条 Cognition 沿
  forms 时间轴并存——各记一态，误信态与揭底态共存是常态（例：陈默 06-12 对相亲局
  持 BELIEVES「一起吃饭」、06-14 揭底后追加 KNOWS，两条并存）。态度转变 = **追加
  新条目**（新 snowflake + 三边，forms 锚转变事件），旧条保留永不覆盖——认知历史
  与 Event/Info 同为不可变的世界事实。**取材规则**：时间点 T 的认知态 = 该
  (Character, Info) 下 forms 锚 start_time ≤ T 的**最新一条**；查询可全量返回时间线
  （认知演变线对创作层有戏眼价值），投放白名单时按拍时刻取最新有效态。
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
| `SUSPECTS` | 对 Info 命题起疑/趋向其为真，无明确替代命题 | 恒空（形成替代命题时新增一条 BELIEVES+title，本条保留） |
| `DOUBTS` | 拒绝接受 Info 命题为真（嘴硬/否认） | 恒空（持明确反向命题时新增一条 BELIEVES+title，本条保留） |

参考推论：「信错」典型落法 = BELIEVES + title（偏差命题）；KNOWS/SUSPECTS/DOUBTS
是对 Info 命题本身的正/疑/否认姿态。判定测试：拿掉 title 这条认知还能定位吗——
能（态度指向 Info 本身）→ 不该有 title；不能（信另一命题）→ 必须有 title。

## 建边模板（幂等）

```cypher
// 新建：MERGE 幂等（重跑/双通道重入无重复），节点先于边，各语句自包含；同 (Character, Info, forms 锚事件) 三元不重复由建议生成端严检保证（生成前现查三元组）
MERGE (c:Cognition {id:'<snowflake>'}) ON CREATE SET c.type='<KNOWS|BELIEVES|SUSPECTS|DOUBTS>', c.title='<仅所信≠Info title 时写，否则删本段>';
MATCH (ch:Character {id:'<char_id>'}) MATCH (c:Cognition {id:'<snowflake_同上>'}) MERGE (ch)-[r:has_cognition]->(c) ON CREATE SET r.sync=false;
MATCH (c:Cognition {id:'<snowflake_同上>'}) MATCH (i:Info {id:'<info_id>'}) MERGE (c)-[r:about]->(i) ON CREATE SET r.sync=false;
MATCH (ev:Event {id:'<forms_event_id>'}) MATCH (c:Cognition {id:'<snowflake_同上>'}) MERGE (ev)-[f:forms]->(c) ON CREATE SET f.sync=false;

// 追加（态度转变）：与新建同款——新 snowflake 再建一条（has_cognition 同角色、about 同 Info、forms 锚转变事件），旧条零改动（编年史并存，无 SET/DELETE 改写语句）
```
