## 立绘设计图（IllusDesign）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

每个 (DesignSheet, CostumeStyle) 组合一个——同角色同着装可因多版本设计图（如剪发前后）并存多版本。角色穿着特定着装的三视图设计稿——由设计图（外貌基础）和着装特征共同决定。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| prompt_path | 提示词文件 | string | 否 | 派生 prompt 文件相对路径 `06_角色美术/<char_id>/<ds_id>/<costume_id>/prompt.md`（hexid 段） |
| image_path | 图片路径 | string | 否 | `06_角色美术/<char_id>/<ds_id>/<costume_id>/立绘设计图.png`（hexid 段） |
| display_scale | 显示缩放 | float | 否 | 运行时立绘显示缩放（1.0=占满立绘层满高）：`round(height_cm/200, 4)`（REF_HEIGHT=200，与 99_game/tools/init_portrait_scales.py 一致）；height_cm 缺失写 null（按满高显示） |
| status | 流程状态 | int | 否 | `0` |

**status 枚举**：`0` 待生成 → `10` 待审（图片完成即待审，单轮直推）→ `11` 批准

---
