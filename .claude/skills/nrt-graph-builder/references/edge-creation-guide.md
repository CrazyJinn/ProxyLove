# 边创建指南

8 种边类型的方向规则、属性 schema 和 Cypher 模板。

---

## 叙事关系边（6种）

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

- **方向**：`任意实体 → Info`
- **属性**：`type`（如"涉及""因果"）、`detail`、`time`
- **特殊规则**：`type=因果` 时仅用于 `Info → Info`

```cypher
// 实体关联信息
MATCH (a {id: $from}), (b:Info {id: $to})
MERGE (a)-[:link {type: $type, detail: $detail, time: $time}]->(b)

// 信息因果链（仅 Info→Info）
MATCH (a:Info {id: $from}), (b:Info {id: $to})
MERGE (a)-[:link {type: '因果', detail: $detail}]->(b)
```

### 4. involved — 人物—事件

- **方向**：`Character → Event`
- **属性**：`role`（如"当事人""目击者""受害者""施害者""参与者"）、`detail`

```cypher
MATCH (a:Character {id: $from}), (b:Event {id: $to})
MERGE (a)-[:involved {role: $role, detail: $detail}]->(b)
```

### 5. occurs_at — 事件—空间

- **方向**：`Event → Spot`（**禁止 Event 直挂 Location**）
- **属性**：`anchor`（必填：`spot`=细分 Spot / `default`=默认 Spot，与目标 Spot.kind 一致）、`detail`（如"跳江地点""约会地点"）
- 目标 Spot：文本有子空间线索 → 建/复用 zone Spot（命名 `<Location名>-<区域>`）；无线索 → 该 Location 默认 Spot（`<Location名>-未细分`）

```cypher
MATCH (a:Event {id: $from}), (b:Spot {id: $to})
MERGE (a)-[:occurs_at {anchor: $anchor, detail: $detail, sync: false}]->(b)
```

### 5b. part_of — 空间—地点

- **方向**：`Spot → Location`
- **属性**：`sync` 恒 false
- 建 Location 必须连带建默认 Spot（kind='default'，name=`<Location名>-未细分`）+ 本边

```cypher
MATCH (a:Spot {id: $from}), (b:Location {id: $to})
MERGE (a)-[:part_of {sync: false}]->(b)
```

### 6. evt_relation — 事件—事件

- **方向**：`Event → Event`
- **属性**：`type`（`因果`/`先后`/`包含`）、`detail`
- **方向语义**：`因果` = 前因→后果；`先后` = 时间顺序；`包含` = 大事件→子事件

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
| Event | occurs_at, evt_relation, link | → Spot / Event / Info |
| Spot | part_of | → Location |
| Location | CATEGORIZED_AS, link | → LocationType / Info |
| Info | link | → Info |
| Faction | — | — |
| LocationType | — | — |
| 任意 | link | → Info |
