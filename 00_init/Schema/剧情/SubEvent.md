## 细化事件（SubEvent）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

最小粒度：父事件（Event）在机位层的演出物化——到场/离开/换区/换装等演出段。一个 Event 可细化出多个 sub，一个 sub 只属一个父（存量分布 0~4 sub/事件；无 sub 事件=显式工作缺口，交 event-stager 补细化）。

| 字段 | 中文 | 类型 | 必填 | 示例 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| title | 标题 | string | 是 | `<父事件title> · <机位名>` |
| time | 时间 | string(datetime) | 是 | 继承父事件或时间插值 |
| description | 描述 | string | 否 | 演出内容——节拍级 2~4 分句，每分句一个节拍+互动方向；不写字段头/台词原文/道具环境细节/氛围；时间地点人须与父 Event 相容（撰写契约见 event-stager skill） |

- SubEvent **无** status / type / ending_kind / condition / involved / occurs_at——叙事身份（时间、人物、地点、因果、分支）全部在父 Event 层；sub 只承载 `anchored_at→Scene`、`appears_as→IllusDesign` 与 `reveals→Hook` 三边。
- **时间轴查询只碰 Event**（label 隔离——SubEvent 不干扰 Event 时间轴/时间窗查询）。
- 删父 Event 必须连带删其全部 sub。

---
