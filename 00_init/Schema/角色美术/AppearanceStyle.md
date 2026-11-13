## 外貌特征（AppearanceStyle）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

每个角色一个。定义角色的固定外貌（脸、体型、发色、瞳色等），全部结构化字段。纯数据节点，不参与风格继承。

**写法纪律**（对表内一切外貌字段生效）：
- 只写**客观静态形态**（颜色、形状、长短、发质、固定标记）；禁止情绪/神态/动态/状态类描述——此类内容归 Character.vibe 单一事实源（归属判定见 [Schema总览.md](../Schema总览.md) 属性撰写总则）。
- 同一特征不进两个字段：已在某字段承载的佩戴物/标记不在其他外貌字段重复（单一事实源；固定佩戴物归 marks）。
- 数值字段（如身高）写整数，无明确值写 `null`，不另设自由文本载体兜底。

> 无 `appearance` 自由文本字段——2026-11-13 废止（20 条存量仅 3 条非空且职责均有归属载体：综合气质归 Character.vibe、身高归 height_cm、体型主干归 body_type/shape_language；细粒度体型句按 vibe 提纯规范并入 Character.vibe）。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| name | 名称 | string | 是 | `[角色名]外貌特征` |
| shape_language | 形状语言 | string | 否 | 标签：三角型/方型/倒三角/细长型/圆形/不对称 |
| age_impression | 年龄感 | string | 否 | 标签 |
| body_type | 体态 | string | 否 | 标签 |
| skin_tone | 肤色 | string | 否 | 标签 |
| ethnicity | 面孔/人种 | string | 否 | 标签：中国面孔/日系面孔/韩系面孔/东南亚面孔/欧美面孔/中东面孔/非裔面孔/混血面孔 |
| hair | 头发 | string | 否 | 合成组合（发色+发型+发长，顺序固定——顺序即解析约定，下游按序读）：`深棕色大波浪长发`；短语非句子（标签族纪律见 [Schema总览.md](../Schema总览.md)） |
| eye | 眼睛 | string | 否 | 合成组合（瞳色+眼型，顺序固定）：`琥珀色上挑眼`；只写客观静态形态，禁神态/情绪/动态词——此类归 Character.vibe |
| lip_shape | 唇形 | string | 否 | 标签 |
| marks | 特殊标记 | string | 否 | 标签（可多选） |
| height_cm | 身高cm | int | 否 | 数值身高，供立绘显示缩放推算（迁移自 appearance 文本） |
| status | 流程状态 | int | 否 | `0` |

**status 枚举**：`0` 待设计 → `1` 已完成

---
