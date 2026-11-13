## 场景（Scene）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

每个 Spot 一个或多个（时段/版本变体各一 Scene）。定义子空间在某时段/版本下的视觉设定。**Scene = 源 Spot 的 room.yml 内一个机位条目**（`scenes[].scene_id` = Scene.id，含 camera/lights；room.yml 路径登记在源 Spot 的 `dsl_path`，见上文 Spot 节点）。纯数据节点（按 Location 粒度推导、Spot 粒度产出），创建后即 `status=1`（已完成，无审批）。Scene 字段自足承载视觉设定：vibe 氛围 + deco 陈设 + time_of_day 时段（2026-11-12 description 废止——空间定位归 Spot.description，剧情语境归 anchored_at 归组边，视觉细节归 deco/vibe）。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| name | 名称 | string | 是 | `[Location名]-[区域]`，如 `咖啡店-点餐台`（可与 zone Spot 同名，label 与 realizes 边已区分）；时段/版本后缀（-更新设备后/-夜晚）只出现在 Scene 名。人读展示用——运行时场景键 = hexid(Scene.id)（manifest.scenes 与章 JSON scenes[].scene 同源），改名零漂移 |
| scene_type | 场景类型 | enum | 是 | `dialogue`（对话背景）/ `functional`（功能场景）/ `combat`（战斗场景）/ `ui`（UI背景）。决定所需图层（见下表） |
| time_of_day | 时段 | string | 否 | 标签：清晨/白天/黄昏/夜晚。出图经 `--tod` 进模式 E prompt；Godot 运行时时段以此为准 |
| vibe | 氛围 | string | 否 | 该机位画面的恒定味道，一句（可含天气，如「雨幕笼罩的路口」）——服务场景出图/读图取材；不写陈设小物（归 deco）、空间定位（归 Spot.description）、剧情语境（归 anchored_at）、人物持物、构图光影数值（归 room.yml）（2026-11-12 自 atmosphere 更名并提纯；四问见 [Schema总览.md](../Schema总览.md)「属性撰写总则」） |
| deco | 陈设细节 | string | 否 | 该机位画面里的陈设/小物清单：短语并列不散文化（标签就是标签，见 [Schema总览.md](../Schema总览.md)）——可移动小物与杂物堆**不建 room.yml 几何**，视觉表现全写此处（出图时经 `--deco` 传入 slice_scenes.py 拼 prompt） |
| status | 流程状态 | int | 否 | `0` |

**status 枚举**：`0` 待设计 → `1` 已完成

> Scene 无 weather/composition/lighting/color_direction 字段：氛围=Scene.vibe，构图=room.yml 机位投影，光影=yaml `lights`，配色=美术风格.md 全局风格。

---
