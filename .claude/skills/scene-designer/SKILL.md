---
name: scene-designer
description: |
  推进 Scene 图节点（Location 粒度入口）：定位 Location → 聚合其 occurs_at 事件 → 推理既有 zone Spot 够用性（anchored_at 归组分布）→ 归组（证据明确命中唯一 zone 自动执行；歧义点——多 zone 命中/粒度歧义/证据不足——AskUserQuestion 多选由用户敲定后继续；Spot 只有 zone 一种 kind，default 已废止仅存量）→ 按 Spot 复用/新建 Scene（新建时显式决定机位）→ 维护 Room DSL（room.yml 3D 布局真源，Scene=机位）→ 保存结果（anchored_at 归组 + Scene MERGE + realizes 边 + Spot.dsl_path 登记，status=1 已完成）。
  在需要为某地点创建/追加场景视觉设定、推进已有 spot 流程、或为 Location 上未归组的事件做子空间细分时使用。spot 名/ID 直推兼容（经 part_of 定位所属 Location 后走全流程）。
argument-hint: <location_id 或 Location 名（兼容 spot_id/spot 名）>
arguments:
  - location
allowed-tools: Read, Bash, Write, Edit, AskUserQuestion
---

> **级联说明**：realizes/anchored_at 边 sync 恒 false——Location/Spot 属性变更**不再**级联作废 Scene（原 has_scene sync=true 的级联通道已随 Spot 方案移除）。Scene 自身仍是 SceneLayer 的 has_layer(sync=true) 上游：Scene 属性被编辑时 SceneLayer 照常重置。`status=-1` 的 Scene 仍须重新生成并覆盖，禁止因属性已有值而跳过。

# 场景设计（Scene · Location 粒度入口）

为单个 Location 决定空间细分与视觉实现：叙事推导期 Event 只 `occurs_at → Location`（一跳），本 skill 是 **Spot 归组（anchored_at）与 Scene 的唯一写入点**——按 Location 上挂载的事件推理既有 spot 是否够用、不够再新增，归组到 Spot 后仍按 Spot 粒度产 Scene（Spot 提供空间语义 name/kind/description，Scene 只补视觉维度 scene_type/time_of_day/机位）并绑定 `realizes` 边（**Spot → Scene**）。新建场景写入内容后即 `status=1`（已完成，无审批），直接参与下游 SceneLayer 生产。

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| location | Location 节点 ID（snowflake Base62）或 Location 名；兼容传 spot ID/spot 名（全名 `八楼出租屋-卧室` / 短名 `卧室`，经 part_of 定位所属 Location） | 必传 |

## 流程（三段式：查状态 → 完成任务 → 保存结果）

> 本 skill 是 Scene 内容与 status、Spot/anchored_at 归组的唯一写入点。出图 prompt 由 scene-layer-designer 消费时**现场投影生成**（`slice_scenes.py --emit-prompt`：room.yml + 机位 → prompt.md 直写），本 skill 与出图链均无派生中间文件。

### 1. 查询目标节点状态

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 完成定位与决策依据查询：

**1a. 定位 Location**（按优先级依次尝试，命中即止；spot 入参先解析为所属 Location）：

```cypher
// ① 按 Location ID
MATCH (l:Location {id: '<输入>'}) RETURN l.id AS loc_id, l.name AS loc_name, l.description AS loc_desc;
// ② 按 Location 名
MATCH (l:Location {name: '<输入>'}) RETURN l.id AS loc_id, l.name AS loc_name, l.description AS loc_desc;
// ③ spot 入参兜底：按 spot ID / 全名 / 短名后缀定位 spot，经 part_of 取所属 Location
MATCH (sp:Spot {id: '<输入>'})-[:part_of]->(l:Location) RETURN l.id AS loc_id, l.name AS loc_name, l.description AS loc_desc;
MATCH (sp:Spot {name: '<输入>'})-[:part_of]->(l:Location) RETURN l.id AS loc_id, l.name AS loc_name, l.description AS loc_desc;
MATCH (sp:Spot)-[:part_of]->(l:Location) WHERE sp.name ENDS WITH '-<输入>' RETURN l.id AS loc_id, l.name AS loc_name, l.description AS loc_desc;
```

**1b. Location + 事件 + 既有 Spot/Scene 覆盖**（三个决策查询）：

```cypher
// ① Location 总览：事件量 + 既有 Spot 及 Scene 覆盖
MATCH (l:Location {id: '<loc_id>'})
OPTIONAL MATCH (e:Event)-[:occurs_at]->(l)
OPTIONAL MATCH (l)<-[:part_of]-(sp:Spot)
OPTIONAL MATCH (sp)-[:realizes]->(s:Scene)
RETURN l.name AS loc_name, l.description AS loc_desc,
       count(DISTINCT e) AS evt_cnt,
       collect(DISTINCT {id: sp.id, name: sp.name, kind: sp.kind, dsl_path: sp.dsl_path,
                scenes: [(sp)-[:realizes]->(x:Scene) | x.name]}) AS spots;

// ② 未归组事件明细（归组判定证据 + objects 建模证据；scene-design 未推进过的 Location 此处=全部事件）
MATCH (e:Event)-[:occurs_at]->(l:Location {id: '<loc_id>'})
WHERE NOT (e)-[:anchored_at]->(:Spot)-[:part_of]->(l)
RETURN e.id AS event_id, e.title AS title, e.description AS descr, e.time AS time
ORDER BY e.time;

// ③ 既有 zone Spot 归组分布（「既有 spot 够用性」的量化依据）
MATCH (l:Location {id: '<loc_id>'})<-[:part_of]-(sp:Spot)
OPTIONAL MATCH (e:Event)-[:anchored_at]->(sp)
RETURN sp.id AS spot_id, sp.name AS spot, sp.kind AS kind, sp.dsl_path AS dsl_path,
       count(e) AS grouped_cnt, collect(e.title)[..5] AS sample
ORDER BY grouped_cnt DESC;
```

**1c. 探测本 Location 各 spot 的 room.yml**：1b 返回的各 `dsl_path` 非空 → 直接用该路径（spot 已建模）；为空则按规则探测磁盘 `07_场景美术/<loc_name>/<Spot目录名>/<Spot短名>.yml`（路径与命名速查见 [references/room-yml-v3.md](references/room-yml-v3.md) §3）。存在则必须复用（空间只建模一次）。

**1d. 探测同 Location 其他 spot 的既有 yaml**（拷贝起步候选）：
`ls 07_场景美术/<loc_name>/*/*.yml`。

**1e. Location 不存在时**：与调用方确认后**只新建 Location**（不连带建 Spot——Spot 由本流程 2b 按事件证据决定）：

```cypher
MERGE (l:Location {name: '<Location名>'})
  ON CREATE SET l.id = '<snowflake>', l.description = '...';
```

### 2. 完成任务（决策）

**2a. Spot 够用性推理与事件归组**（对 1b② 的每个未归组事件 u；U 为空则直接跳到 2b 的 Scene 决策）：

1. **子空间证据抽取**：从 u 的 title/description 找空间线索词（「电脑桌前」「点餐台」「床铺」「厨房」）。
2. **证据明确命中唯一既有 zone**（线索词与该 zone 短名/`description` 语义同空间）→ **自动归组不打扰**，建 `anchored_at(u → zone)`，detail 写证据词。判「命中」须引用三条旁证（汇报中列明）：① 语义重合；② 该 zone 已有 Scene（归组即达绿档，零出图成本）；③ 该 zone grouped_cnt 未过载（单 zone 事件叙事密度合理）。
3. **歧义点 → 停下问（AskUserQuestion 多选，有歧义就问）**：
   - **触发面**：① 证据可命中**多个**既有 zone；② 粒度歧义——拆新 zone vs 同 Spot 多 Scene（机位/时间窗版本）均可行；③ 证据不足/笼统，需拆 zone。
   - **候选构成**：按事件语义拟 1-3 个 zone 方案（含短名=Location 名的**整点 zone** 候选——整点建模、目录名即 Location 名；Other 由工具自动提供）。
   - **多选语义**（multiSelect=true）：可同时勾选多个拆 zone 方案——事件归入最贴切的 zone，其余选中 zone 建为**预留**（无归组事件 → 2b 判「暂不出图」不建 Scene，零出图成本）。
   - **提问纪律**（承 nrt-gap-filler）：每题附推荐选项（首位 + Recommended）且**可归因**——理由标签 + 数据依据（如「零拆分成本」「为后续事件预留细分」），不许「我觉得」；facts 不问用户（候选 zone 方案、既有归组分布现查），只问取舍；同 Location 多事件同模式**聚合为一题**、单题列全实体；**一题一答**、依赖排序（用户选拆 zone → 追问 zone 名/短名合法性，短名不得含文件系统保留字符）。
4. **按敲定结果执行**：新增 zone Spot（命名 `<Location名>-<区域>`，kind='zone'——**不再有 default kind**，整点即区域段=Location 名）建 part_of + anchored_at，或归入用户选定的既有 zone。「评估过但无子空间证据」的自动兜底已废止，一律经 3 敲定。
5. **粒度铁律**：同一物理空间的叙事细分优先吸收为同 Spot 多 Scene（机位/时间窗版本），确需拆 zone Spot（≈新物理空间、新 room.yml 文件）时才新建；「新建 zone 一张图起」vs「归组到既有 zone 零成本」作为取舍依据写进提问的推荐理由与汇报。

**2b. Scene 复用 / 新建**（按归组后的每个 Spot 决定）：

- **已有 Scene 已覆盖事件集与时间窗** → 复用（跳过，幂等）——复用判定看 Scene 的版本语义（时段/氛围字段）是否覆盖事件需求，禁止为已有覆盖重复建 Scene。
- **zone Spot 有归组事件** → 建 Scene realize 之（Spot 提供空间语义，Scene 只补视觉维度）。
- **zone Spot 无归组事件** → 记录「暂不出图」，不建 Scene（美术按需）。
- **整点 zone（短名=Location 名）有归组事件** → 建整点 Scene（name=Location 名），realize 该 zone。
- **时间窗版本**（更新设备前/后、有赛/空场等）→ 同一 Spot 下多个 Scene，版本语义写在 Scene 名与字段（时段/氛围），不另建 Spot。

**2c. 机位决策**（新建 Scene 时显式决定）：为每个新建 Scene 定 `camera {pos, look_at, fov}`（室内对话机位自门口平视略高；机位即构图——「机位后退、家具沿墙、中下部留空」由 camera 数值保证；起步数值取 [references/room-yml-v3.md](references/room-yml-v3.md) §6 基线）。调机位先在 dashboard /room3d 相机预览看效果。

对需**新建**的 Scene，生成 snowflake id 并按下方字段表填写内容：

| 维度 | 属性 | 示例 | 说明 |
|------|------|------|------|
| 名称 | name | `咖啡店-点餐台` | `[Location名]-[区域]`（可与 zone Spot 同名）；时段/版本后缀（-更新设备后/-夜晚）只出现在 Scene 名 |
| 场景类型 | scene_type | dialogue / functional / combat / ui | 按事件性质：纯对话→dialogue，功能交互→functional，战斗→combat，界面→ui |
| 时段 | time_of_day | 清晨/白天/黄昏/夜晚 | 从 Event.time（`yyyy-MM-dd HH:mm:ss`，小时即时段依据）和描述推导（出图经 --tod 进模式 E prompt；运行时契约） |
| 氛围 | atmosphere | `空气里弥漫咖啡香，慵懒午后` | 自由文本：整体氛围一句话（含天气，如「雨幕笼罩的路口」） |
| 陈设细节 | deco | `桌上一台旧显示器亮着，麦克风支在杂乱桌面，外卖盒沿桌沿堆叠` | 自由文本：该机位画面里的陈设/小物描述（可移动小物与杂物堆**不建几何**，全写此处） |
| 概要 | description | `咖啡店的点餐区域` | 1-2 句 |

**内容生成规则**：
1. 构图/光影/配色**不写字段**——构图由机位数值保证（2c：机位后退、家具沿墙、中下部留空），光影由 room.yml `lights` 数值承载，配色归美术风格.md 全局风格。
2. atmosphere 一句话承担整体氛围与天气表达；deco 承担机位画面内可移动小物与杂物堆。

**2d. 维护 Room DSL（room.yml —— 3D 布局真源）**

> **room.yml 是空间事实的唯一真源，图是投影**。结构模板与硬约束、坐标系、路径命名、校验规则、立绘安全区阈值、数值基线、外景分支、atmosphere/deco 例句——统一见 [references/room-yml-v3.md](references/room-yml-v3.md)（**写 yaml 前必读**，规则出处标注到 slice_scenes.py / check_framing.py 行号）。

- **读/产路径**：`07_场景美术/<Location名>/<Spot目录名>/<Spot短名>.yml`（目录名=Spot 短名；整点 zone 短名=Location 名，详见 references §3）。**挂靠单元 = Spot（建模单元，通常即物理房间）**：同一物理空间的叙事细分优先吸收为同 Spot 多 Scene（机位/时间窗版本），确需拆 zone Spot（≈新物理空间）时才产新文件。
- **复用（文件已存在）**：只追加 scenes[] 条目（新 Scene=新机位），objects 除非有新事件证据不动。
- **产（不存在时）三分支**：
  - ① 同 Location 其他 Spot 已有 yaml → 拷贝其房间壳与共享物件起步（显式复制，禁止跨文件引用），删与本 spot 无关物件、聚焦子空间；
  - ② 全 Location 无 yaml → 按 v3 结构新建（location/room/objects/scenes 四块，模板见 references §1），objects 建模依据 = 本 spot 归组事件的 description（陈设证据）+ Spot.description + Location.description，**证据不足的物件不建几何、写进图 Scene.deco（禁止硬猜）**；机位/灯/尺寸起步数值取 references §6 基线；
  - ③ 外景：`shell: open` + `ground/sky`，沿轴延伸物（护栏/长路）必须拆近/中/远段（整件投影退化成线；模板见 references §7）。
- 粒度铁律：**只建不移动的固定大件**（床/桌/柜/门窗结构等，每房间 ≤8 件）；可移动小物与杂物堆（床头杂物/外卖盒/线缆）**不建几何**——其视觉表现写进图 Scene.deco；光源（lights）保留数值。**大件贴墙布置，房间正中不放挡视线大件**（中岛/中央桌类至多一件且须偏侧贴边；安全区阈值见 references §5）。**长 YAML 禁止手打全文**：Python dict 构造 + `yaml.safe_dump` 落盘。
- **新 Scene（机位）**：`scenes[]` 追加条目（id/scene_id/scene_name/spot/camera{pos,look_at,fov}/lights/objects_delta）——**纯几何/数值，不存文字**；机位来自 2c 的决策。
- **文字归图**：deco/atmosphere/time_of_day 等一切叙事文字只写图 Scene 节点（段 3 SET），yaml 的 scene 条目不留这些键；构图/光影/配色**无字段**（真源=room.yml 几何 + 美术风格.md；旧字段 weather/composition/lighting/color_direction 已全图清理废止）。

**2e. 校验（写后质量门，两门都必跑）**：写/改 room.yml 后必跑 ① `python 07_场景美术/slice_scenes.py <room.yml> --check`（几何/结构校验）② `python 07_场景美术/check_framing.py <room.yml>`（立绘安全区），报错必须修复后才进段 3。**本 skill 不重切派生**——slice_scenes.py 由 scene-prompt-assembler 模式 E 出图前调用（消费侧重切）。

### 3. 保存结果

#### Spot 新建与事件归组（若段 2a 建了新 Spot / 归组了事件）

```cypher
// 新建 zone Spot（幂等；整点 zone 同型，区域段=Location 名）
MERGE (sp:Spot {name: '<Location名>-<区域>'})
  ON CREATE SET sp.id = '<snowflake_id>', sp.kind = 'zone', sp.description = '...';
MATCH (sp:Spot {id: '<snowflake_id>'}), (l:Location {id: '<loc_id>'})
MERGE (sp)-[r:part_of]->(l) ON CREATE SET r.sync = false;
// 事件归组（occurs_at→Location 恒保留不动；重指只删本 Location 范围旧 anchored_at——跨地点事件其他地点的归组不动）
MATCH (e:Event {id: '<event_id>'})-[old:anchored_at]->(:Spot)-[:part_of]->(:Location {id: '<loc_id>'}) DELETE old;
MATCH (e:Event {id: '<event_id>'}), (sp:Spot {id: '<spot_id>'})
MERGE (e)-[r:anchored_at]->(sp) ON CREATE SET r.detail = '<证据词>', r.sync = false;
```

#### Scene 写入（MERGE 节点 + realizes 边，status=1 已完成）

```cypher
MERGE (s:Scene {id: '<snowflake_id>'})
  ON CREATE SET s.status = 0;
MATCH (sp:Spot {id: '<spot_id>'}), (s:Scene {id: '<snowflake_id>'})
MERGE (sp)-[r:realizes]->(s) ON CREATE SET r.sync = false;
MATCH (s:Scene {id: '<snowflake_id>'})
SET s.name = '<Location名-区域>',
    s.scene_type = '...', s.time_of_day = '...',
    s.atmosphere = '...', s.deco = '...',
    s.status = 1;
// 构图/光影/配色无字段（真源=room.yml 几何 + 美术风格.md；weather/composition/lighting/color_direction 已废止清理）。
// Spot 登记 dsl_path（单一真源：非空 = spot 已 3D 建模，其 realizes 的 Scene 出图走 assembler 模式 E）
MATCH (sp:Spot {id: '<spot_id>'})
SET sp.dsl_path = '07_场景美术/<Location名>/<Spot目录名>/<Spot短名>.yml';
```

> realizes 重建时先清后建（幂等模板见 00_init/Schema/场景美术.md 引用；Scene 节点不删，层链由 scene-layer-designer 管理）。

**status 写入**：新建场景创建即 `status = 1`（已完成，无审批）。

**验收**：本 Location 所有 occurs_at 事件要么已有 anchored_at 归组、要么在汇报中显式列「暂不归组（原因）」；每个新建 Scene 恰好 1 条 realizes 入边；realize 整点 zone 的 Scene 必须是「整点 Scene」决策（name=Location 名）。**DSL 验收**：room.yml `--check` 通过；room.yml 内每个 scenes[].scene_id 与图节点一一对应；源 Spot.dsl_path 已登记（Scene 节点不持有 dsl_path）。

最后汇总：Location 归组了哪些事件（新建 zone / 归入既有 zone）、复用了哪些已有 Scene、新建了哪些（status=1 已完成）、哪些 zone 暂不出图。

## 参考文档

- [场景美术 Schema](00_init/Schema/场景美术.md) — Spot/Scene 节点字段、anchored_at/part_of/realizes 边、scene_type 与所需图层
- [room.yml v3 速查](references/room-yml-v3.md) — 结构模板/校验规则/立绘安全区阈值/数值基线/外景模板/例句（写 yaml 前必读）
- [叙事基础 Schema](00_init/Schema/叙事基础.md) — Event/Location 节点、occurs_at 边
- [场景美术风格](00_init/美术风格.md) — 渲染与色彩基调、提示词硬约束（风格收尾串）
