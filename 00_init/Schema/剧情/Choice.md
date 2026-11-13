## 选择分叉（Choice）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

最小粒度：一个玩家选择分叉点。把 galgame「玩家选择」一等公民化——显式建模「在哪选择、不同选项导向不同后续」。

世界观设定（见 [00_init/游戏概览.md](../../00_init/游戏概览.md)）：灵魂穿越者只能在关键选择节点干预，而关键选择节点 = 玩家的选择项。

| 字段 | 中文 | 类型 | 必填 | 示例 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| name | 名称 | string | 是 | `跳江选择` / `三选一` |
| description | 情境 | string | 否 | 选择发生那一刻的情境一两句；不写各选项后果（由 option 边承载） |
| time | 时间 | string(datetime) | 否 | `yyyy-MM-dd HH:mm:ss`，自时间锚点推算（选填） |

> Choice 无 status 字段、不参与生产流水线，与 Character/Event/Location/Hook/Lore 同属纯数据实体。

**结局**：结局不单独建节点，仍用 `Event` + 可选属性 `ending_kind`（`BE`/`TE`/`HE`/`NE`，字段定义见上文事件节）表达；`option{leads_to_ending:true}`（见下文）指向的 Event 即结局事件。

---
