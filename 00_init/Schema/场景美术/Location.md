## 地点（Location）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

最小粒度：具体地点/游戏场景。Location 仅保留叙事属性；空间细分由 Spot 承载，视觉信息下沉到 Scene。

| 字段 | 中文 | 类型 | 必填 | 示例 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| name | 名称 | string | 是 | `重庆长江大桥` |
| description | 描述 | string | 否 | `横跨长江的公路铁路两用桥`（一句话空间定位：地理/功能说明；视觉不写归 Scene.vibe/deco、剧情不写） |

> Event 定位一律 `occurs_at → Location`（一跳，边定义见 [../剧情/边.md](../剧情/边.md)）；机位归组 `anchored_at → Scene` 只存在于 SubEvent 层（见下文）。Spot 经 `part_of` 从属 Location（方向 Location→Spot）。Location/Spot 改名**零漂移**——产物目录锚 id（realizes sync=false：改名不作废机位图）。

---
