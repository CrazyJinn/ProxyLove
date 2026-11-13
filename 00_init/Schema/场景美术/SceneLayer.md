## 场景图层（SceneLayer）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

场景的单一图层（传统 2D 游戏 4 层结构）。用 `layer_type` 区分背景/地面/陈设/遮罩；每个场景按 `scene_type` 按需拥有图层节点。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| name | 名称 | string | 是 | `[Scene名]-[图层中文]`，如 `咖啡店-点餐台-背景` |
| layer_type | 图层类型 | enum | 是 | `background`（背景）/ `floor`（地面）/ `decor`（陈设）/ `mask`（遮罩） |
| prompt_path | 提示词文件 | string | 否 | 派生 prompt 文件相对路径 `07_场景美术/<location_id>/<spot_id>/<scene_id>/<layer_type>/prompt.md`（hexid 段；机位目录名=scene_id），由 assembler 从 Scene 字段 + 美术风格.md 生成 |
| image_path | 图片路径 | string | 否 | `07_场景美术/<location_id>/<spot_id>/<scene_id>/<layer_type>/<layer_type>.png`（与 prompt.md 同层——图层子目录内 prompt.md + <layer_type>.png 配对） |
| status | 流程状态 | int | 否 | `0` |

**status 枚举**：`0` 待生成 → `10` 待审（图片完成即待审，单轮直推）→ `11` 批准

> **图层渲染顺序**（底→顶）：background 背景 → floor 地面 → decor 陈设 →（角色）→ mask 遮罩。遮罩层渲染在角色之上，形成前景遮挡。

---
