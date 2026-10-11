---
name: scene-designer
description: |
  推进 Scene 图节点（spot 粒度）：定位 spot → 确保 Location 关联（关联既有或新建）→ 检查 spot 关联 event 决定复用或新建 Scene（新建时显式决定机位）→ 维护 Room DSL（room.yml 3D 布局真源，Scene=机位）→ 保存结果（Scene MERGE + realizes 边 + Spot.dsl_path 登记，status=1 已完成）。
  在需要为某 spot 创建/追加场景视觉设定、推进已有 spot 流程、或细化 anchor='default' 事件时使用。
argument-hint: <spot_id 或 spot 名>
arguments:
  - spot
allowed-tools: Read, Bash, Write, Edit
---

> **级联说明**：realizes 边 sync 恒 false——Location/Spot 属性变更**不再**级联作废 Scene（原 has_scene sync=true 的级联通道已随 Spot 方案移除）。Scene 自身仍是 SceneLayer 的 has_layer(sync=true) 上游：Scene 属性被编辑时 SceneLayer 照常重置。`status=-1` 的 Scene 仍须重新生成并覆盖，禁止因属性已有值而跳过。

# 场景设计（Scene · spot 粒度）

为单个 spot 决定视觉实现：spot 提供空间语义（name/kind/description），Scene 只补视觉维度（scene_type/time_of_day/weather/机位）。推进 Scene 节点并绑定 `realizes` 边（**Spot → Scene**）。新建场景写入内容后即 `status=1`（已完成，无审批），直接参与下游 SceneLayer 生产。

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| spot | spot 节点 ID（snowflake Base62）或 spot 名（全名 `八楼出租屋-卧室` / 短名 `卧室`） | 必传 |

## 流程（三段式：查状态 → 完成任务 → 保存结果）

> 本 skill 是 Scene 内容与 status 的唯一写入点，也是 default 事件细化归位（anchor→spot）的执行者。出图 prompt 由 scene-layer-designer 消费时**现场投影生成**（`slice_scenes.py --emit-prompt`：room.yml + 机位 → prompt.md 直写），本 skill 与出图链均无派生中间文件。

### 1. 查询目标节点状态

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 完成定位与决策依据查询：

**1a. 定位 spot**（按优先级依次尝试，命中即止）：

```cypher
// ① 按 ID
MATCH (sp:Spot {id: '<输入>'}) RETURN sp.id AS spot_id, sp.name AS spot_name;
// ② 按全名
MATCH (sp:Spot {name: '<输入>'}) RETURN sp.id AS spot_id, sp.name AS spot_name;
// ③ 按短名后缀（多条命中=歧义，报错让调用方给全名或 ID）
MATCH (sp:Spot) WHERE sp.name ENDS WITH '-<输入>' RETURN sp.id AS spot_id, sp.name AS spot_name;
```

**1b. spot + Location + 事件 + 已有 Scene**（决策依据；`loc_id` 为 null 说明 spot 无 part_of，走 2a 关联）：

```cypher
// spot 关联情况 + 事件量（pending = 待细化的 default 锚事件）+ 已有 Scene
MATCH (sp:Spot {id: '<spot_id>'})
OPTIONAL MATCH (sp)-[:part_of]->(l:Location)
OPTIONAL MATCH (e:Event)-[oa:occurs_at]->(sp)
OPTIONAL MATCH (sp)-[:realizes]->(s:Scene)
RETURN l.id AS loc_id, l.name AS loc_name, l.description AS loc_desc,
       sp.name AS spot_name, sp.kind AS kind, sp.description AS spot_desc,
       sp.dsl_path AS dsl_path,
       count(DISTINCT e) AS evt_cnt,
       count(DISTINCT CASE WHEN oa.anchor='default' THEN e END) AS pending_cnt,
       collect(DISTINCT {id: s.id, name: s.name, status: s.status}) AS scenes;

// 事件明细（复用/新建判定 + default 细化证据 + objects 建模证据）
MATCH (sp:Spot {id: '<spot_id>'})<-[oa:occurs_at]-(e:Event)
RETURN e.id AS event_id, e.title AS title, e.description AS descr, e.time AS time, oa.anchor AS anchor
ORDER BY e.time;
```

**1c. 探测本 spot 的 room.yml**：1b 返回的 `dsl_path` 非空 → 直接用该路径（spot 已建模）；为空则按规则探测磁盘 `07_场景美术/<loc_name>/<Spot目录名>/<Spot短名>.room.yml`（Spot 目录名规则见 2d）。存在则必须复用（空间只建模一次）。

**1d. 探测同 Location 其他 spot 的既有 yaml**（拷贝起步候选）：
`ls 07_场景美术/<loc_name>/*/*.room.yml`。

**1e. spot 不存在时**：从入参名解析 Location 前缀（Spot 命名约定 `<Location名>-<区域>`）→ 查 `MATCH (l:Location) WHERE l.name='<前缀>' RETURN l.id, l.name`：
- Location 存在 → 兜底建 zone Spot（生成 snowflake id）+ part_of，回到 1b；
- Location 不存在 → 与调用方确认后按 2a 新建 Location + default Spot + 本 zone Spot；
- 名称无 `-` 前缀或解析不出 → 报错退出，要求给全名或 ID。

### 2. 完成任务（决策）

**2a. Location 关联**（1b 查到 `loc_id` 非空则跳过本步）：

```cypher
// Location 不存在时：新建 Location + default Spot（幂等）
MERGE (l:Location {name: '<Location名>'})
  ON CREATE SET l.id = '<snowflake>', l.description = '...';
MERGE (dsp:Spot {name: '<Location名>-未细分'})
  ON CREATE SET dsp.id = '<snowflake>', dsp.kind = 'default', dsp.description = '默认 Spot（未细分）';
MATCH (dsp:Spot {id: '<default_spot_id>'}), (l:Location {id: '<loc_id>'})
MERGE (dsp)-[r:part_of]->(l) ON CREATE SET r.sync = false;
// 本 spot 关联 Location（孤立 spot 补挂 / 1e 兜底新建）
MATCH (sp:Spot {id: '<spot_id>'}), (l:Location {id: '<loc_id>'})
MERGE (sp)-[r2:part_of]->(l) ON CREATE SET r2.sync = false;
```

**2b. Scene 复用 / 新建**（检查 spot 关联的 event 决定）：

- **已有 Scene 已覆盖事件集与时间窗** → 复用（跳过，幂等）——复用判定看 Scene 的版本语义（时段/氛围字段）是否覆盖事件需求，禁止为已有覆盖重复建 Scene。
- **zone Spot 有事件** → 建 Scene realize 之（Spot 提供空间语义，Scene 只补视觉维度）。
- **zone Spot 无事件** → 记录「暂不出图」，不建 Scene（美术按需）。
- **default Spot 有事件** → 先评估叙事密度：
  - 值得细分 → 从事件 description 抽子空间证据，建 zone Spot（命名 `<Location名>-<区域>`）并迁挂事件（anchor→'spot'）；再对新 zone Spot 决定视觉实现。**证据不足的事件留在 default，禁止硬猜**。
  - 不值得细分或证据不足 → 建整点 Scene（name=Location 名），realize 默认 Spot；事件保持 anchor='default'。
- **时间窗版本**（更新设备前/后、有赛/空场等）→ 同一 Spot 下多个 Scene，版本语义写在 Scene 名与字段（时段/氛围），不另建 Spot。

**2c. 机位决策**（新建 Scene 时显式决定）：为每个新建 Scene 定 `camera {pos, look_at, fov}`（室内对话机位自门口平视略高；机位即构图——「机位后退、家具沿墙、中下部留空」由 camera 数值保证）。调机位先在 dashboard /room3d 相机预览看效果。

对需**新建**的 Scene，生成 snowflake id 并按下方字段表填写内容：

| 维度 | 属性 | 示例 | 说明 |
|------|------|------|------|
| 名称 | name | `咖啡店-点餐台` | `[Location名]-[区域]`（可与 zone Spot 同名）；时段/版本后缀（-更新设备后/-夜晚）只出现在 Scene 名 |
| 场景类型 | scene_type | dialogue / functional / combat / ui | 按事件性质：纯对话→dialogue，功能交互→functional，战斗→combat，界面→ui |
| 时段 | time_of_day | 清晨/白天/黄昏/夜晚 | 从 Event.time 和描述推导 |
| 天气 | weather | 晴/阴/雨/雪/雾 | 从事件描述推导 |
| 氛围 | atmosphere | `空气里弥漫咖啡香，慵懒午后` | 自由文本：整体氛围一句话 |
| 陈设细节 | deco | `桌上一台旧显示器亮着，麦克风支在杂乱桌面，外卖盒沿桌沿堆叠` | 自由文本：该机位画面里的陈设/小物描述（可移动小物与杂物堆**不建几何**，全写此处） |
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

**2d. 维护 Room DSL（room.yml —— 3D 布局真源）**

> **room.yml 是空间事实的唯一真源，图是投影**。

- **读/产路径**：`07_场景美术/<Location名>/<Spot目录名>/<Spot短名>.room.yml`。**Spot 目录名**：zone Spot 取 name 去 `<Location名>-` 前缀的短名；default Spot（`<Location名>-未细分`）取 Location 名；zone 短名恰等于 Location 名时复用 default 的目录与 yaml，不另建文件。**挂靠单元 = Spot（建模单元，通常即物理房间）**：同一物理空间的叙事细分优先吸收为同 Spot 多 Scene（机位/时间窗版本），确需拆 zone Spot（≈新物理空间）时才产新文件。
- **复用（文件已存在）**：只追加 scenes[] 条目（新 Scene=新机位），objects 除非有新事件证据不动。
- **产（不存在时）三分支**：
  - ① 同 Location 其他 Spot 已有 yaml → 拷贝其房间壳与共享物件起步（显式复制，禁止跨文件引用），删与本 spot 无关物件、聚焦子空间；
  - ② 全 Location 无 yaml → 按 v3 结构新建（location/room/objects/scenes 四块），objects 建模依据 = 本 spot 事件 description（陈设证据）+ Spot.description + Location.description，**证据不足的物件不建几何、写进图 Scene.deco（禁止硬猜）**；
  - ③ 外景：`shell: open` + `ground/sky`，沿轴延伸物（护栏/长路）必须拆近/中/远段（整件投影退化成线）。
- 粒度铁律：**只建不移动的固定大件**（床/桌/柜/门窗结构等，每房间 ≤8 件）；可移动小物与杂物堆（床头杂物/外卖盒/线缆）**不建几何**——其视觉表现写进图 Scene.deco；光源（lights）保留数值。**长 YAML 禁止手打全文**：Python dict 构造 + `yaml.safe_dump` 落盘。
- **新 Scene（机位）**：`scenes[]` 追加条目（id/scene_id/scene_name/spot/camera{pos,look_at,fov}/lights/objects_delta）——**纯几何/数值，不存文字**；机位来自 2c 的决策。
- **文字归图**：deco/atmosphere/time_of_day/weather 等一切叙事文字只写图 Scene 节点（段 3 SET），yaml 的 scene 条目不留这些键；composition/lighting/color_direction **不再手写**（由 room.yml 几何 + 图 deco/atmosphere 承载，SceneLayer 走模式 E 出图）。存量旧字段保留不删。

**2e. 校验（写后质量门）**：写/改 room.yml 后必跑 `python3 07_场景美术/slice_scenes.py <room.yml> --check`（几何/结构校验），报错必须修复后才进段 3。**本 skill 不重切派生**——slice_scenes.py 由 scene-prompt-assembler 模式 E 出图前调用（消费侧重切）。

### 3. 保存结果

#### 细化迁挂（若段 2b 建了 zone Spot 并迁挂 default 事件）

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
    s.atmosphere = '...', s.deco = '...',
    s.status = 1;
// DSL 路线下 composition/lighting/color_direction 不再手写（由 room.yml 承载）；存量旧字段保留（模式 A 消费方仍读）。
// Spot 登记 dsl_path（单一真源：非空 = spot 已 3D 建模，其 realizes 的 Scene 出图走 assembler 模式 E）
MATCH (sp:Spot {id: '<spot_id>'})
SET sp.dsl_path = '07_场景美术/<Location名>/<Spot目录名>/<Spot短名>.room.yml';
```

> realizes 重建时先清后建（幂等模板见 00_init/Schema/场景美术.md 引用；Scene 节点不删，层链由 scene-layer-designer 管理）。

**status 写入**：新建场景创建即 `status = 1`（已完成，无审批）。

**验收**：每个新建 Scene 恰好 1 条 realizes 入边；realize default Spot 的 Scene 必须是「整点 Scene」决策（name=Location 名）；迁挂后无 anchor='default' 事件残留在已细分的 zone 上（anchor 与目标 Spot.kind 一致）。**DSL 验收**：room.yml `--check` 通过；room.yml 内每个 scenes[].scene_id 与图节点一一对应；源 Spot.dsl_path 已登记（Scene 节点不持有 dsl_path）。

最后汇总：Location 关联了哪个（或新建）、复用了哪些已有 Scene、细化了哪些 zone Spot（迁挂几个事件）、新建了哪些（status=1 已完成）、哪些 zone 暂不出图。

## 参考文档

- [场景美术 Schema](00_init/Schema/场景美术.md) — Scene 节点字段、realizes 边、scene_type 与所需图层
- [叙事基础 Schema](00_init/Schema/叙事基础.md) — Spot 节点、occurs_at/part_of 边
- [场景美术风格](00_init/美术风格.md) — 渲染与色彩基调、提示词硬约束（风格收尾串）
