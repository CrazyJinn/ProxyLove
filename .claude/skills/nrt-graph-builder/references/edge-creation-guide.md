# 边创建指南

9 种边类型的方向规则、属性 schema 和 Cypher 模板。

---

## 叙事关系边（7种）

### 1. relation — 人物关系

- **方向**：`char → char`
- **属性**：`type`（关系类型，如"恋爱""亲属""同事"）、`detail`（如"恋爱中""已分手""姐弟"）
- **方向语义**：有向，A→B 表示 A 对 B 的关系描述

```cypher
MATCH (a:Character {id: $from}), (b:Character {id: $to})
MERGE (a)-[:relation {type: $type, detail: $detail}]->(b)
```

### 2. at — 人物—地点

- **方向**：`Character → Location`
- **属性**：`type`（如"居住""前往""工作"）、`detail`

```cypher
MATCH (a:Character {id: $from}), (b:Location {id: $to})
MERGE (a)-[:at {type: $type, detail: $detail}]->(b)
```

### 3. link — 信息关联

- **方向**：`Character / Event / Location → Info`
- **属性**：`type`（如"涉及"）、`detail`、`time`（`yyyy-MM-dd HH:mm:ss`，自时间锚点推算）
- **注意**：因果不在 link 上——用 leads_to

```cypher
MATCH (a {id: $from}), (b:Info {id: $to})
MERGE (a)-[:link {type: $type, detail: $detail, time: $time}]->(b)
```

### 4. involved — 人物—事件

- **方向**：`Character → Event`
- **属性**：`role`（如"当事人""目击者""受害者""施害者""参与者"）、`detail`

```cypher
MATCH (a:Character {id: $from}), (b:Event {id: $to})
MERGE (a)-[:involved {role: $role, detail: $detail}]->(b)
```

### 5. occurs_at — 事件—地点

- **方向**：`Event → Location`（**一跳直挂**；不建 Spot——子空间归组 anchored_at 由 scene-designer 场景化时建，本工具禁建）
- **属性**：`detail`（如"跳江地点""约会地点"）；子空间线索（"电脑桌前""点餐台"）写进 detail 或 Event.description

```cypher
MATCH (a:Event {id: $from}), (b:Location {id: $to})
MERGE (a)-[:occurs_at {detail: $detail, sync: false}]->(b)
```

### 6. leads_to — 导致（叙事层唯一因果边）

- **方向**：`(Event | Info) → (Event | Info)`——四向全通（事件→事件、事件→信息、信息→信息、信息→事件）
- **属性**：`detail`（因果语境）
- **语义**：上游是下游的直接原因

```cypher
MATCH (a {id: $from}), (b {id: $to})
WHERE (a:Event OR a:Info) AND (b:Event OR b:Info)
MERGE (a)-[:leads_to {detail: $detail, sync: false}]->(b)
```

### 7. evt_relation — 事件—事件

- **方向**：`Event → Event`
- **属性**：`type`（`先后`/`包含`；因果已归 leads_to）、`detail`
- **方向语义**：`先后` = 时间顺序；`包含` = 大事件→子事件

```cypher
MATCH (a:Event {id: $from}), (b:Event {id: $to})
MERGE (a)-[:evt_relation {type: $type, detail: $detail}]->(b)
```

---

## 分组边（2种）

### 7. BELONGS_TO — 角色—阵营

- **方向**：`Character → Faction`
- **属性**：`role`（如"战队经理""战队队长""成员"）
- **注意**：无阵营角色无此边

```cypher
MATCH (a:Character {id: $from}), (b:Faction {id: $to})
MERGE (a)-[:BELONGS_TO {role: $role}]->(b)
```

### 8. CATEGORIZED_AS — 地点—类型

- **方向**：`Location → LocationType`
- **属性**：无

```cypher
MATCH (a:Location {id: $from}), (b:LocationType {id: $to})
MERGE (a)-[:CATEGORIZED_AS]->(b)
```

---

## 方向验证规则

创建边前必须验证方向正确：

| from 标签 | 允许的边类型 | to 标签 |
|-----------|------------|---------|
| Character | relation, at, link, involved, BELONGS_TO | → Character / Location / Info / Event / Faction |
| Event | occurs_at, evt_relation, leads_to, link | → Location / Event / Info |
| Location | CATEGORIZED_AS, link | → LocationType / Info |
| Info | leads_to | → Event / Info |
| Faction | — | — |
| LocationType | — | — |

> anchored_at（Event → Spot）为 scene 域边，本工具禁建（scene-designer 独占写入）。
