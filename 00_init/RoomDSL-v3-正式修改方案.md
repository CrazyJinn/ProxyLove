# Room DSL v3 正式修改方案：3D 房间建模 → 2D 投影 → 文生图

> **状态：正式方案（待实施）**。本方案取代 `SpotDSL-场景生产线设计.md`（v2，作废待删）。
> 演进：v1 叙事字段结构化（否决）→ v2 Spot 级 3D DSL（否决：一 Spot 一文件割裂房间）→ **v3 房间级 3D 建模 + scene 机位 + 视锥剔除 + 2D 投影出图（已实测验证，效果确认）**。
> 范围：ProxyLove 主线 + dailian-dashboard。
> 验证记录（2026-10-10）：八楼出租屋全房间建模 → 5 scene 剔除/投影 → scene2d.yml 文生图 → 效果用户确认「不错」；/room3d 白模+点击拾取+相机预览（2D bbox 叠加）全部浏览器实测通过。

## 0. 模型一句话

**一个 Location 一个 3D 房间 YAML（真源）；一个 Scene = 该房间的一次取景（camera）+ 物件状态（lights/deco）；出图时按 scene 相机做视锥剔除并投影成 2D 百分比布局（scene2d.yml），YAML 直接作为文生图输入。**

三个已验证的关键判断：
1. **房间级建模优于 Spot 级**：桌和床同房间，机位决定谁入镜——一 Spot 一文件会割裂空间。
2. **视锥剔除必要**：整房 YAML 喂模型会导致相机外物件也被渲染（实测问题）。
3. **2D 投影优于 3D 坐标**：t2i 模型理解画幅百分比布局远好于 3D 坐标（实测确认）；投影是确定性数学，由代码完成，模型不脑算透视。

## 1. 数据模型（已定稿格式）

### 1.1 文件布局
```
07_场景美术/<Location>/<Location>.room.yml        ← 真源（手写/scene-designer 产）
07_场景美术/slice_scenes.py                        ← 派生器（已存在，转正）
07_场景美术/<Location>/<Scene 名>.scene.yml        ← 派生：视锥剔除后的 3D 切片（调试/白模用）
07_场景美术/<Location>/<Scene 名>.scene2d.yml      ← 派生：2D 投影布局（文生图直接输入）
07_场景美术/<Location>/<Scene>/background/prompt.md ← 现状产物位（模式 E 产出，路径不变）
```

### 1.2 room.yml 结构（权威规范）
```yaml
location: {id, name, description}          # 只读，与图一致
room:                                      # 房间壳（外景见 §8.1：shell:open + ground/sky）
  floor: [X, Z]                            # 米；原点=地面中心；X右 Y上 Z朝房门(+Z)
  height / wall_color / floor_color
  door: {side, pos, size}
  windows: [{id, pos, size, rot, desc}]
  deco: <房间级固定背景散文>               # 海报/吊柜/顶灯等不建模的细节
objects:                                   # 几何关键件：影响构图/光源的大件（≤10 件/房间）
  - {id, spot, name, type, pos, size, rot, color, desc}
  # type: box[w,h,d] / plane 贴墙[w,h] / cylinder[直径,高] / sphere[直径]
  # spot: 所属 Spot 名后半段（=图上 zone Spot 对齐）——物件分组标签
scenes:                                    # 每 Scene 一个取景
  - id / scene_id / scene_name / spot      # scene_id 映射图节点
    scene_type / time_of_day / weather
    camera: {pos, look_at, fov}            # fov=竖直度数；水平按出图宽高比换算
    lights: [{type: point|ambient, pos, color, intensity}]
    deco: <该取景的物件细节散文>            # 显示器/麦克风等——版本差异落这里
    atmosphere: <一行氛围散文>
    objects_delta / text_passthrough       # 预留（v3 未启用）
```

**粒度铁律**：影响构图/遮挡/光源的物件用几何（房间地板上可挪动的大件）；氛围细节（海报、线缆、外卖盒）一律 deco 文字。每房间几何件数个位数。

### 1.3 派生规则（slice_scenes.py，已实现已验证）
- **视锥剔除**：物件 8 角全在视锥同侧外 → 剔除。竖直 fov + 宽高比（默认 1.5=1536×1024）换算水平视场；窗/门同样参与。**不做遮挡剔除**（视锥内被挡住的保留，交模型理解——比错剔安全）。
- **2D 投影**：物件角点 → 画幅百分比 bbox `[x,y,w,h]`（y 向下）+ depth（距相机米数）+ clipped 标记（越缘）；房间结构（地板/后墙/左右墙/天花）投影为 room_regions；点光源投到画幅坐标。objects 列表按 depth **远→近排序 = 遮挡序**。
- 幂等可重跑：改 room.yml 后一键重切全部 scene。

### 1.4 投影单实现：后端算，前端展示（已拍板 2026-10-10）
- **权威实现唯一**：投影数学只存在于 slice_scenes.py。派生 scene2d.yml 时同时内嵌 `preview` 块（每 scene：物件 bbox/depth/标签 + 光源画幅位 + room_regions），room3d.html **删除 projectPoint/objCorners 两段 JS**，改为读 preview 块画框——页面退化为纯渲染器。
- **重算时机 = skill 驱动**：room.yml 被修改的链路（scene-designer 保存、dashboard /room3d 保存、用户手工改）之后，由**对应 skill 在其「保存结果」步调用 slice_scenes.py 重切**；级联作废（sync -1）后的重新生产也走同一入口。dashboard 侧保存接口（#8）内部同样调 slice_scenes 函数化入口，不在前端复算。
- **一致性断言**（验收 3 收紧）：页面叠加框坐标 == scene2d.yml 数值，变为**结构性保证**（同一份数据），不再依赖两实现同步纪律。
- 交互取舍（已接受）：无「拖动相机实时投影」——改机位 = 改 room.yml → 重切 → 页面重载，符合 v3 流程。
## 2. ProxyLove 主线修改清单

### 2.1 Schema 登记（`00_init/Schema/场景美术.md`）
- Scene 节点新增属性 **`dsl_path`**（string，可空）：指向 `07_场景美术/<Loc>/<Loc>.room.yml` 相对路径。scene 在文件内的定位靠 `scenes[].scene_id`（不加 variant 字段——单一来源）。
- 登记文件契约：room.yml 为真源，`scene.yml/scene2d.yml` 为派生产物（再生成物，不进 git？——待拍板③）。
- 不新增节点/边类型。Spot/Location/Scene 边（part_of/realizes/has_layer）不动。

### 2.2 slice_scenes.py 转正
- 位置不变（`07_场景美术/`），补：`--out-dir`、函数化入口（`slice_room(path, aspect, mode)` 供 assembler import）、校验器（穿墙/穿顶/支撑检查——本次已写的 Python 校验逻辑收编进来）。
- 产出确定性：同输入同输出（不写时间戳）。

### 2.3 scene-prompt-assembler 新增模式 E（2D YAML 出图）— P0
- **触发**：调用方（scene-layer-designer）传 `dsl_path`（Scene 节点字段）→ 模式 E；无 `dsl_path` → 旧自由文本模式（回退面，存量不动）。
- **流程**：读 room.yml → 定位 scene_id → 调 slice_scenes 派生 scene2d → prompt = **导语（固定）+ scene2d.yml 全文 verbatim + 收尾串（动态读 `00_init/美术风格.md` L83-89）**。
- 导语文案（随实现文件维护，不写死在 skill 散文里）：
  > 以下 YAML 描述一张游戏场景背景图的画幅布局：objects 的 bbox [x,y,w,h] 为物件在画面中的位置与大小（百分比，y 向下），列表由远及近（遮挡序），★ 无标记物件为背景元素；lights 为光源位置与颜色。请严格按此布局生成图片，物件位置/大小/颜色以 YAML 为准。
- **LLM 零改写**：assembler 只做文件读取+拼接+落盘（Write 工具），不重组语义。产物落 `prompt_path` 照旧。
- 纯产出层边界不变：不读写图、不写 status。

### 2.4 scene-designer 流程改写 — P1
三段式改造：
1. 查状态（不变）。
2. **读/产 room.yml**：Location 已有 room.yml → 只新增/调整 `scenes[]` 条目（新 Scene=新机位）；没有 → 从 Scene 自由文本字段产初稿（物件几何 + 机位由 LLM 定，人审）。一个房间建模一次，后续 Scene 只加机位——**生产成本从「每 Scene 一篇散文」降为「每 Scene 三个数字（pos/look_at/fov）」**。
3. 保存结果：MERGE Scene 节点 + `dsl_path` 登记 + 叙事投影字段（time_of_day/weather/atmosphere 照抄）。

### 2.5 scene-layer-designer 调用链 — P1
- 传 `dsl_path` 给 assembler（模式 E）。
- `image_path` 产物位不变（`background/background.png`），手工出图覆盖同路径照旧兼容。

### 2.6 存量 19 Scene 迁移 — P2（渐进，不停产）
- 不强制一次性改写。新 Scene 全走 room.yml。
- 存量 Scene：status=-1（作废重做）时顺带 DSL 化；或用户在 /room3d 手工建。
- 已出图且满意的 Scene（如八楼出租屋 5 个）**可以不迁**——旧 prompt.md 与产物已是终态，迁移无增益；八楼出租屋 room.yml 已人工完成（本次验证用）。

## 3. dailian-dashboard 修改清单

### 3.1 /room3d 转正（临时页 → 正式页）— P0
现状已可用（本次交付）：Three.js 白模、scene 切换、相机锥可视化、点击拾取（高亮+信息卡）、相机预览（1.5 画幅+2D bbox 叠加+光源标记+九宫格）、存预览图 PNG。
转正动作：
- 导航入口：顶栏不入（保持工作台简洁）；从场景 tab 深链进入（见 3.2）。
- 加「📋 复制 scene2d YAML」按钮（读派生文件原文进剪贴板——手工出图通道）。
- 加「🎨 跳到出图」：拼好导语+scene2d+收尾串 → 复制完整 prompt。
- 收尾串获取：后端小 API `GET /room3d/style-tail`（从主线仓库 `00_init/美术风格.md` 动态提取，不写死——漂移检查源头唯一）。

### 3.2 board 场景 tab 入口 — P0
- Location 节点卡 + Spot 节点卡加「🧊 3D 布局」按钮 → `/room3d?loc=<Location名>`（Spot 卡跳转后自动选中对应 scene 第一个）。
- Scene 节点卡同款按钮 → `/room3d?loc=<Loc>&scene=<scene_id>` 直接锁定该机位相机预览。

### 3.3 YAML 编辑与保存 — P1（弹窗/页内编辑器）
- /room3d 左侧加 YAML 编辑抽屉（textarea + 保存按钮）。
- 保存链路：`POST /room3d/{loc}/save` → PyYAML 校验 + 几何校验（穿墙/悬空/相机出房）→ 写 room.yml → **投影写图**（time_of_day/weather/atmosphere MERGE 回 Scene 节点）→ 前端刷新白模。
- **治理**：保存不触发 sync 级联、不动 status（级联仍由节点编辑确认卡/Cypher 控制台触发）。room.yml 变更导致的美术重做由用户经既有流程（改 Scene 字段触发级联或手动置 -1）显式发起。
- **先产物再写图**：YAML 校验失败禁止任何写操作。

### 3.4 「通过」与 status 的关系 — 维持既有设计
- DSL 弹窗/页面不设「通过」按钮推进 status——status 走看板既有审批（10→11）。
- dsl_path 登记由 scene-designer（生产链）或保存链路（3.3）写入，不越权。

## 4. 治理红线（不变项汇总）
- scene-designer 场景链唯一写入者；NRT 禁写生产层。
- status 白名单/审批动作/sync 级联语义零改动。
- 风格收尾串唯一来源 `00_init/美术风格.md`，任何代码/模板不写死。
- 手工试出图不接 OfoxAi（复制/下载即可）；正式出图仍走 infra-image-generator。
- 派生文件（scene.yml/scene2d.yml）不手改（文件头已有警告注释）。

## 5. 实施顺序（每步独立可停、独立提交）
| # | 内容 | 项目 | 级别 |
|---|---|---|---|
| 1 | Schema 登记 dsl_path + 文件契约 | ProxyLove | P0 |
| 2 | slice_scenes.py 转正（校验器收编+函数化；**派生结果内嵌 preview 块**，见 §1.4） | ProxyLove | P0 |
| 3 | assembler 模式 E（导语+scene2d verbatim+收尾串） | ProxyLove | P0 |
| 4 | /room3d 转正（复制 YAML/跳到出图/style-tail API） | dashboard | P0 |
| 5 | board 场景 tab 入口按钮（Location/Spot/Scene 卡） | dashboard | P0 |
| 6 | scene-designer 流程改写（读/产 room.yml） | ProxyLove | P1 |
| 7 | scene-layer-designer 传 dsl_path | ProxyLove | P1 |
| 8 | /room3d YAML 编辑+保存+投影写图 | dashboard | P1 |
| 9 | 存量 Scene 渐进迁移（-1 顺带） | ProxyLove | P2 |

提交点：P0 一批（#1-5）、P1 一批（#6-8）、P2 随生产节奏。当前已存在未提交的 dashboard 临时页代码即 #4 的底子。

## 6. 验收标准
1. **链路**：board 场景 tab → 🧊 3D → 白模/相机预览 → 复制 prompt → 手工出图 → 覆盖 background.png——全链路无手工拼装。
2. **模式 E**：有 dsl_path 的 Scene 出图 prompt = 导语+scene2d+收尾串，程序化断言（无 LLM 重组）；无 dsl_path 的 Scene 走旧模式（回归）。
3. **投影一致性**：/room3d 相机预览的 bbox 叠加与 scene2d.yml 数值一致（同一投影公式两处实现——页面 JS 与 slice_scenes.py，修改任一侧须同步）。
4. **治理**：保存/预览不触发级联不动 status；收尾串从美术风格.md 动态读取。
5. **出图质量**：相机外物件不再出现（本次已验证）；构图服从 bbox 布局。

## 7. 回退
- Scene 清空 `dsl_path` → 立即回旧自由文本链（单节点粒度）。
- /room3d 页面独立路由，删除无副作用。
- room.yml 留在文件系统不碍事；slice_scenes.py 无副作用。

## 8. 已拍板记录（2026-10-10，全部定案）
1. **派生文件进 git**（scene.yml/scene2d.yml 均提交）：出图可复现（任何一次出图的 prompt 都能在历史找到当时 bbox）、diff 可审（改机位后 bbox 变化一目了然）。纪律：**改 room.yml 必须同提交重切产物**——slice_scenes.py 幂等，重跑覆盖即可；提交前校验「派生是否新鲜」列入 #2 转正项的校验器。
2. **scene.yml（3D 剔除版）保留**：白模相机预览的剔除判定、机位调试用；成本只是文件数。
3. **外景规范已定案**（长江大桥 demo 验证，2026-10-10），细则如下。

### 8.1 外景规范（Room DSL v3 外景细则）
- **shell: open**：room 块声明 `shell: open` 即外景——无墙无天花无门；`floor` 语义变为「承载面」（桥面/地面），配 `floor_color`；新增：
  - `ground: {y, color, desc}`：远景承载面（江面/大地），y 通常为大负值（桥高），desc 写环境散文（对岸灯火等）
  - `sky: {color, desc}`：天穹（色 + 天气/光污染描述）
- **slice_scenes**：open 壳输出 `room_regions.ground_desc / sky_desc`（不输出墙区）；页面画江面大板 + 天穹球壳。
- **沿轴延伸物必须拆段**：桥面/护栏/长路等沿视线方向延伸的大件，整件投影会退化成消失点处一根线（bbox w≈0，长江大桥 demo 实测踩坑）。规则：按近/中/远拆 2~4 段，各段独立 bbox，透视递变由分段 bbox 表达；段边界按场景机位定（不必均匀）。
- **光源 out_of_frame**：近处高杆灯灯头常在画外（fov 装不下），lights 条目带 `out_of_frame: true`——光照效果仍有效，仅位置标记出画。
- 已验证实例：`07_场景美术/长江大桥/长江大桥.room.yml`（护栏三段拆分 + 消失点构图机位）。
