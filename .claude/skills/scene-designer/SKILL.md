---
name: scene-designer
description: |
  推进 Scene 图节点：查询状态 → 按 Location 的 Spot 树与各 Spot 事件量决定视觉实现（含 default 事件的子空间细化归位）→ 维护 Room DSL（room.yml 3D 布局真源，Scene=机位）→ 保存结果（Scene MERGE + dsl_path 登记 + realizes 边，status=1 已完成）。
  在需要为地点创建/追加场景视觉设定、或细化 anchor='default' 事件时使用。
argument-hint: <loc_id>
arguments:
  - loc_id
allowed-tools: Read, Bash, Write, Edit
---

> **级联说明**：realizes 边 sync 恒 false——Location/Spot 属性变更**不再**级联作废 Scene（原 has_scene sync=true 的级联通道已随 Spot 方案移除）。Scene 自身仍是 SceneLayer 的 has_layer(sync=true) 上游：Scene 属性被编辑时 SceneLayer 照常重置。`status=-1` 的 Scene 仍须重新生成并覆盖，禁止因属性已有值而跳过。

# 场景设计（Scene）

为 Location 的每个 Spot 决定视觉实现：Spot 提供空间语义（name/kind/description），Scene 只补视觉维度（scene_type/time_of_day/weather/lighting/composition）。推进 Scene 节点并绑定 `realizes` 边（**Spot → Scene**）。新建场景写入内容后即 `status=1`（已完成，无审批），直接参与下游 SceneLayer 生产。

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| loc_id | 地点节点 ID（snowflake Base62） | 必传 |

## 流程（三段式：查状态 → 完成任务 → 保存结果）

> 本 skill 是 Scene 内容与 status 的唯一写入点，也是 default 事件细化归位（anchor→spot）的执行者。

### 1. 查询目标节点状态

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 查询地点 + 其 Spot 树 + 各 Spot 事件量（决策依据）：

```cypher
// 地点 + Spot 树 + 各 Spot 事件量（pending = 待细化的 default 锚事件）
MATCH (l:Location {id: '<loc_id>'})<-[:part_of]-(sp:Spot)
OPTIONAL MATCH (e:Event)-[oa:occurs_at]->(sp)
RETURN sp.id AS spot_id, sp.name AS spot_name, sp.kind AS kind,
       count(e) AS evt_cnt,
       count(CASE WHEN oa.anchor='default' THEN 1 END) AS pending_cnt
ORDER BY sp.kind, sp.name;

// 各 Spot 已有的 Scene（视觉实现现状）
MATCH (l:Location {id: '<loc_id>'})<-[:part_of]-(sp:Spot)-[:realizes]->(s:Scene)
RETURN sp.name AS spot_name, collect(s.name) AS scenes;

// 待细化事件明细（default 锚事件的子空间证据来源）
MATCH (l:Location {id: '<loc_id>'})<-[:part_of]-(sp:Spot {kind:'default'})<-[:occurs_at {anchor:'default'}]-(e:Event)
RETURN e.id AS event_id, e.title AS title, e.description AS descr, e.time AS time
ORDER BY e.time;
```

### 2. 完成任务（为每个 Spot 决定视觉实现）

- **zone Spot 有事件** → 建 Scene realize 之（Spot 提供空间语义，Scene 只补视觉维度）。
- **zone Spot 无事件** → 记录「暂不出图」，不建 Scene（美术按需）。
- **default Spot 有事件** → 先评估叙事密度：
  - 值得细分 → 从事件 description 抽子空间证据，建 zone Spot（命名 `<Location名>-<区域>`）并迁挂事件（anchor→'spot'）；再对新 zone Spot 决定视觉实现。**证据不足的事件留在 default，禁止硬猜**。
  - 不值得细分或证据不足 → 建整点 Scene（name=Location 名），realize 默认 Spot；事件保持 anchor='default'。
- **时间窗版本**（更新设备前/后、有赛/空场等）→ 同一 Spot 下多个 Scene，版本语义写在 Scene 名与字段（时段/氛围），不另建 Spot。
- 已有 Scene 已覆盖的子空间跳过（去重）。

对需**新建**的 Scene，生成 snowflake id 并按下方字段表填写内容：

| 维度 | 属性 | 示例 | 说明 |
|------|------|------|------|
| 名称 | name | `咖啡店-点餐台` | `[Location名]-[区域]`（可与 zone Spot 同名）；时段/版本后缀（-更新设备后/-夜晚）只出现在 Scene 名 |
| 场景类型 | scene_type | dialogue / functional / combat / ui | 按事件性质：纯对话→dialogue，功能交互→functional，战斗→combat，界面→ui |
| 时段 | time_of_day | 清晨/白天/黄昏/夜晚 | 从 Event.time 和描述推导 |
| 天气 | weather | 晴/阴/雨/雪/雾 | 从事件描述推导 |
| 氛围 | atmosphere | `空气里弥漫咖啡香，慵懒午后` | 自由文本：整体氛围一句话 |
| 构图 | composition | `远景：店内墙面与菜单牌；中景：点餐台沿右侧墙面排开，台前地面空旷` | 自由文本：远/中/近景分层（分号分隔）；室内对话场景仅远/中两段（见生成规则 1） |
| 光影 | lighting | `主光源从右上方照射，暖黄色调，环境光柔和偏橙` | 自由文本：主光源方向+色温+环境光 |
| 配色逻辑 | color_direction | `主色咖啡棕，辅色奶白，点缀暖橙` | 自由文本：主辅点缀色与明暗逻辑 |
| 概要 | description | `咖啡店的点餐区域` | 1-2 句 |

**内容生成规则**：
1. 构图（composition）是下游 SceneLayer 背景提示词的主体来源，按室内外分叉：
   - **室内 dialogue 场景只写远景/中景两段，去掉近景段**——画面中下部是角色立绘站位带（运行时立绘贴底、左右分列，高占满屏），必须保持空旷，让地面/墙面自然延伸。机位从房间入口/门洞处平视略高取全景，透视灭点位于画面中上部；家具全部进中景并沿墙/靠画面两侧布置（措辞标明方位，如「沿左侧墙面」「靠右墙」），画面中央留空；狭窄/拥挤/压抑等氛围由远景与画面上部元素承载（低矮吊柜、墙面污渍、边缘堆叠物），不由中下部拥堵承载。
   - 室外 dialogue 场景沿用远/中/近三段分层，中下部同样避免放置大型物体。
2. 光影（lighting）须含主光源方向+色温+环境光，是提示词光影段来源。
3. 配色与光效由 color_direction/lighting 自由定调。

### 2b. 维护 Room DSL（room.yml —— 3D 布局真源）

> 规范见 `00_init/RoomDSL-v3-正式修改方案.md`；**room.yml 是空间事实的唯一真源，图是投影**。

- **读**：`07_场景美术/<Location名>/<Location名>.room.yml`（存在则必须复用——房间只建模一次）。
- **产（不存在时）**：按 v3 结构写 room.yml（location/room/objects/scenes 四块）。粒度铁律：**影响构图/光源的大件用几何（每房间 ≤8 件）**，氛围细节（海报/线缆/杂物）全进 `deco` 文字；光源（lights）保留数值。外景用 `shell: open` + `ground/sky`（方案 §8.1），**沿轴延伸物（护栏/长路）必须拆近/中/远段**（整件投影退化成线）。**长 YAML 禁止手打全文**：Python dict 构造 + `yaml.safe_dump` 落盘。
- **校验**：写后必跑 `python3 07_场景美术/slice_scenes.py <room.yml> --check`（几何/结构/新鲜度三检），报错必须修复后才进段 3。
- **新 Scene（机位）**：`scenes[]` 追加条目（scene_id/camera{pos,look_at,fov}/lights/deco/atmosphere）。**机位即构图**：室内对话机位自门口平视略高（旧「机位后退、家具沿墙、中下部留空」规则改由 camera 数值保证）；调机位先在 dashboard /room3d 相机预览看效果。
- **重切派生**：room.yml 任何改动后重跑 `python3 07_场景美术/slice_scenes.py <room.yml> --mode 2d`（幂等覆盖全部派生）——**改 room.yml 必同提交重切**（派生进 git）。
- **投影回填**：time_of_day/weather/atmosphere 等叙事字段 MERGE 回 Scene；composition/lighting/color_direction **不再手写**（由 room.yml 的 deco/lights 承载，SceneLayer 走模式 E 出图）。存量旧字段保留不删。

### 3. 保存结果

#### 细化迁挂（若段 2 建了 zone Spot 并迁挂 default 事件）

```cypher
// 建 zone Spot（幂等）
MERGE (sp:Spot {name: '<Location名>-<区域>'})
  ON CREATE SET sp.id = '<snowflake_id>', sp.kind = 'zone', sp.description = '...';
MATCH (sp:Spot {id: '<snowflake_id>'}), (l:Location {id: '<loc_id>'})
MERGE (sp)-[r:part_of]->(l) ON CREATE SET r.sync = false;
// 事件迁挂（删旧建新，anchor→spot）
MATCH (e:Event {id: '<event_id>'})-[r:occurs_at]->(:Spot) DELETE r;
MATCH (e:Event {id: '<event_id>'}), (sp:Spot {id: '<snowflake_id>'})
MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor = 'spot', r.sync = false;
```

#### Scene 写入（MERGE 节点 + realizes 边，status=1 已完成）

```cypher
MERGE (s:Scene {id: '<snowflake_id>'})
  ON CREATE SET s.status = 0;
MATCH (sp:Spot {id: '<spot_id>'}), (s:Scene {id: '<snowflake_id>'})
MERGE (sp)-[r:realizes]->(s) ON CREATE SET r.sync = false;
MATCH (s:Scene {id: '<snowflake_id>'})
SET s.name = '<Location名-区域>',
    s.scene_type = '...', s.time_of_day = '...', s.weather = '...',
    s.atmosphere = '...',
    s.dsl_path = '07_场景美术/<Location名>/<Location名>.room.yml',
    s.status = 1;
// DSL 路线下 composition/lighting/color_direction 不再手写（由 room.yml 承载；dsl_path 登记后 SceneLayer 走 assembler 模式 E）；存量旧字段保留（无 dsl_path 消费方仍读）。
```

> realizes 重建以 Location 为单位时先清后建（幂等模板见 00_init/Schema/场景美术.md 引用；Scene 节点不删，层链由 scene-layer-designer 管理）。

**status 写入**：新建场景创建即 `status = 1`（已完成，无审批）。

**验收**：每个新建 Scene 恰好 1 条 realizes 入边；realize default Spot 的 Scene 必须是「整点 Scene」决策（name=Location 名）；迁挂后无 anchor='default' 事件残留在已细分的 zone 上（anchor 与目标 Spot.kind 一致）。**DSL 验收**：room.yml `--check` 通过且派生新鲜；room.yml 内每个 scenes[].scene_id 与图节点一一对应；改 room.yml 的提交必含重切后的派生文件。

最后汇总：细化了哪些 zone Spot（迁挂几个事件）、跳过了哪些已有 Scene、新建了哪些（status=1 已完成）、哪些 zone 暂不出图。

## 参考文档

- [场景美术 Schema](00_init/Schema/场景美术.md) — Scene 节点字段、realizes 边、scene_type 与所需图层
- [叙事基础 Schema](00_init/Schema/叙事基础.md) — Spot 节点、occurs_at/part_of 边
- [场景美术风格](00_init/美术风格.md) — 渲染与色彩基调、提示词硬约束（风格收尾串）
- [Room DSL v3 方案](00_init/RoomDSL-v3-正式修改方案.md) — room.yml 结构/粒度/外景规范/派生纪律（scene-designer 的空间真源职责）
