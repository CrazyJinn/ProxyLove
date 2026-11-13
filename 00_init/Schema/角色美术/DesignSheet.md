## 设计图（DesignSheet）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

每角色每版本一个。首版/常规重做为**参考图图生图**——以用户提供的单张真人参考照片为底，`AppearanceStyle` 外貌属性全量作补充特征（冲突以属性为准）；参考图位置由 Character.`ref_image_path` 属性锚定（`06_角色美术/<char_id>/参考图.jpg`，兼容 .png/.jpeg——dashboard 上传自动压缩与规范命名并 SET 属性，或手动放置），缺失时为用户动作阻塞（不回退文生图）。剧情永久外貌变更（剪发/毁容等）时**以参考版设计图为底图生图新增版本**（仅变更 `delta_notes` 口述内容，保持同人物脸部一致），不改写旧版——旧链下游零作废。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| delta_notes | 改动说明 | string | 否 | **增量版本专用**：本版本相对参考版的口述变更（首版留空；不写未变更维度；不改写旧版）：口述变更描述（如「理发店剪发后：清爽利落的黑色短发，发丝干净有型」），图生图 prompt 变更段的唯一来源；首版留空 |
| active_from | 生效锚点 | int | 否 | `chapter_no*1000+section_no`（ch01/sec02=1002）；空 = 首版（最早恒生效）。取用时取「≤当前叙事位置的最新版本」 |
| prompt_path | 提示词文件 | string | 否 | 派生 prompt 文件相对路径 `06_角色美术/<char_id>/<ds_id>/prompt.md`（hexid 段），由 assembler 从上游 tags + 美术风格.md 生成 |
| image_path | 图片路径 | string | 否 | `06_角色美术/<char_id>/<ds_id>/设计图.png`（hexid 段；slug 版本层已废，多版本各得独立 ds_id 目录） |
| status | 流程状态 | int | 否 | `0` |

**status 枚举**：`0` 待生成 → `10` 待审（图片完成即待审，单轮直推）→ `11` 批准

> ⚠️ 编辑 DesignSheet 属性会沿 sync 边级联作废该版本全部 IllusDesign 与立绘——修正 active_from/delta_notes 前须评估级联影响。

---
