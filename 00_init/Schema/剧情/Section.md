## 节（Section）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

编排容器 + 定稿态载体，**可先于章存在**：自由节 = 无 has_section 入边的 Section（创建时圈定 event 建 includes）；组章后为该章组成部分。节级产物为纯文件：小说.md 与 台词.ink（本节点 `script_path` 指向）；小说已产判据 = 节目录文件存在（有章 `25_剧本/ch<NN>/<secMM>/`，自由节 `25_剧本/自由节/sec<MM>/`），新鲜度 = 文件头部取材指纹（非图状态）。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| section_no | 节序号 | int | 是 | `0`（组章后 = 章内从 0 起，排序权威 + 文件名 `<MM>` 来源；自由节期 = 全局递增占位，组章时重写） |
| title | 标题 | string | 是 | `酒店清晨` |
| summary | 概要 | string | 否 | 本节戏剧职责一句话；不写剧情梗概、不写主旨（那是 StoryArc） |
| script_path | 定稿路径 | string | 否 | `25_剧本/ch<NN>/sec<MM>/台词.ink`（编号目录：ch=chapter_no、sec=section_no 零填充；人读/人改定稿，ink 方言；确认与拆分均以它为准） |
| status | 定稿状态 | int | 否 | `0` |

> 节不存时间字段：取材=includes 物化成员、时间由成员事件推导。

**status 枚举**（定稿审，2026-11-01 恢复）：`0` 创建待定稿（structurer/dashboard 建节直写）→ `10` 定稿待审（dialoguer 产出台词.ink 直写；填充模式写回同置 10）→ `11` 已批（dashboard 批准动作；定稿编辑**保存即 11**——人工编辑免审）。`-1` 作废（novelist stale 重写 / sync 级联 / **人工驳回定稿**）→ dialoguer 重新定稿恢复 `10`。合法值 `0/10/11/-1`；`=11` 是拆分/配音/环境音/立绘的唯一放行条件。

---
