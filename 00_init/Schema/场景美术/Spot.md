## 空间细分（Spot）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

最小粒度：地点内的子空间。按空间证据创建（或复用既有）：Location 上挂载的事件呈现子空间证据时细分出 zone，并把事件细化出的 sub 以 `anchored_at` 直挂到该 Spot realize 的 Scene（机位）——归组与拍机位一步完成（既有 spot 够用则只归组不新建）；叙事期 Event 只挂 `occurs_at → Location`。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| name | 名称 | string | 是 | **一律 `<Location名>-<区域>`**：如「八楼出租屋-电脑桌区」；整点建模区域段=Location 名（如「服装店-服装店」）。人读展示用——**不锚定目录**（目录锚 spot_id，改名零漂移） |
| kind | 类型 | enum | 是 | `zone`（细分区域）——Spot 只有 zone 一种 kind；存量 default Spot（服装店/灵魂夹缝/林梦家-未细分）保留为历史形态，不迁移不再建 |
| description | 描述 | string | 否 | 一句空间描述（这是什么区域，如「地铁车厢内部」）；视觉与剧情不写 |
| dsl_path | DSL 路径 | string | 否 | `07_场景美术/<location_id>/<spot_id>/<spot_id>.yml`（hexid 段；该 spot 的 3D 布局真源相对路径，文件名=本节点 id）。**挂靠单元 = Spot（建模单元，通常即物理房间）**：同一物理空间的叙事细分优先吸收为同 Spot 多 Scene（机位/时间窗版本），确需拆 zone Spot（≈新物理空间）时才产新文件。**非空 = 该 spot 已 3D 建模**——其 realizes 的全部 Scene 出图 prompt 由 room.yml 机位条目现场投影直写（文件内以 `scenes[].scene_id` = Scene.id 定位机位条目；无派生中间文件）；为空走自由文本组装（回退面） |

> Spot 不参与生产流水线（无 status 字段——待细化缺口由结构表达：有 name/kind 无 realizes 出边即占位骨架，scene-designer 圈定消化）。创建纪律：证据明确命中唯一既有 zone 时自动归组；歧义点（多 zone 命中/粒度歧义/证据不足）须人工敲定（禁止硬猜）。整点需求由短名=Location 名的整点 zone 承载。
> zone Spot 与同名 Scene 不冲突（label 不同且 realizes 边显式连接）。

---
