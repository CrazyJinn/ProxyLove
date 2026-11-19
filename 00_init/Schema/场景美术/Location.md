## 地点（Location）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

最小粒度：具体地点/游戏场景。Location 仅保留叙事属性；空间细分由 Spot 承载，视觉信息下沉到 Scene。

| 字段 | 中文 | 类型 | 必填 | 示例 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| name | 名称 | string | 是 | `重庆长江大桥` |
| description | 描述 | string | 否 | `横跨长江的公路铁路两用桥`（一句话空间定位：地理/功能说明；视觉不写归 Scene.vibe/deco、剧情不写） |
| priority | 优先级 | enum | 否 | `P0` ~ `P3` 四级（生产链准入）：P0 核心主场景（高频出场）/ P1 重要场景 / P2 一般低频场景——均进空间化生产链；**P3=占位锚点**（仅作 at/occurs_at 挂靠，无空间化预期）**不进**。占位 Location 物化时恒 P3；需要真实空间化时提案改级（P3→P0~P2）。无值 = 未评级 |

> Event 定位一律 `occurs_at → Location`（一跳，边定义见 [../剧情/边.md](../剧情/边.md)）；机位归组 `anchored_at → Scene` 只存在于 SubEvent 层（见下文）。Spot 经 `part_of` 从属 Location（方向 Location→Spot）。Location/Spot 改名**零漂移**——产物目录锚 id（realizes sync=false：改名不作废机位图）。

---
