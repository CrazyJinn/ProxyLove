## 立绘（StandingIllustration）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

从立绘设计图拓展出的具体变体——不同表情、动作的单张立绘。每张独立节点。表情和动作参考角色的 LanguageStyle 生成。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| prompt_path | 提示词文件 | string | 否 | 派生 prompt 文件相对路径 `06_角色美术/<char_id>/<ds_id>/<costume_id>/立绘/<stand_id>.md`（hexid 段；文件名=本节点 id） |
| image_path | 图片路径 | string | 否 | `06_角色美术/<char_id>/<ds_id>/<costume_id>/立绘/<stand_id>.png`（hexid 段；文件名=本节点 id——运行时立绘键 = hexid(stand_id)，与此同源） |
| variant_label | 变体 | string | 是 | 简短自由词（2~4 字，如 慵懒/玩味/挑眉/茫然）；情绪词/动作词；同 IllusDesign 下不重复然/沉吟/庄严/浅笑），不设词表限制 |
| eye | 眼部 | string | 否 | 标签 |
| brow | 眉毛 | string | 否 | 标签 |
| mouth | 嘴部 | string | 否 | 标签 |
| head_angle | 头部角度 | string | 否 | 标签 |
| hand | 手部动作 | string | 否 | 标签 |
| foot | 脚部动作 | string | 否 | 标签 |
| vibe | 变体调性 | string | 否 | 该变体的情绪调性（1~2 句），供出图把握表情强度/朝向/张力；不写台词情境与剧情语境、着装（归 CostumeStyle）、参考图已有的持物（2026-11-13 自 description 更名；四问见 [Schema总览.md](../Schema总览.md)「属性撰写总则」） |
| status | 流程状态 | int | 否 | `0` |

**status 枚举**：`0` 待生成 → `10` 待审（图片完成即待审，单轮直推）→ `11` 批准

---
