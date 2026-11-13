## 事件（Event）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

最小粒度：某时某刻发生的某件事。一个事件 = 一个有明确时间点的具体动作或状态变化。

> **Event 记「发生」，Hook 记「埋设」，Lore 记「固有」**——需要在故事时间轴上被演出、直接推进剧情的事建 Event；因某事件成立的认知建 Hook；角色/地点固有属性建 Lore（判定测试见下文「钩子（Hook）与设定（Lore）」节）。

| 字段 | 中文 | 类型 | 必填 | 示例 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| title | 标题 | string | 是 | `陆择加入星耀电竞`。一句话可独立成立的事实句（主谓宾）；检验：能否直接当「已发生的事」陈述出来 |
| time | 时间 | string(datetime) | 是 | `yyyy-MM-dd HH:mm:ss`（如 `2024-06-14 19:00:00`），**自时间锚点推算**（锚点见 [游戏概览.md](../游戏概览.md) 基本信息）；字符串序即时间序，计算用 `datetime(e.time)` 现场转换 |
| description | 描述 | string | 否 | title 装不下的钉子细节 1~3 句（数字/物件/氛围摘句）；不复述 title、不写后果（后果是另一 Event + leads_to）、不写认知解读（归 Hook） |
| type | 类型 | enum | 否 | `行动` |
| ending_kind | 结局类型 | enum | 否 | `BE` / `TE` / `HE` / `NE`（非结局留空） |
| condition | 条件判断 | string | 否 | 条件表达式（语法见下方「condition 条件表达式」）；空/缺省 = 无条件，主线默认可激活 |

**type 枚举**：
- `行动`：具体的物理行为，如跳江、转账、报警
- `交流`：对话、发帖、聊天记录等沟通行为
- `转折`：改变事态走向的关键节点
- `状态变化`：人物状态或关系状态的改变，如分手、确诊

**ending_kind 枚举**（结局事件标记，可选）：`BE` Bad Ending / `TE` True Ending / `HE` Happy Ending / `NE` Normal Ending。非结局事件不填。结局事件由下文 `Choice -[option {leads_to_ending:true}]-> Event` 指向。

**condition 条件表达式**（选填；空 = 无条件，主线默认可激活）：

值为一个字符串，表达「玩家选择史」上的布尔条件——本 Event 仅当条件求值为真才可激活。典型用途：分支汇合点的软门控（玩家做过某选择后，另一条线上的后续事件才解锁）。

- **原子**（唯一原子类型）：`choice:<choice_id>[<n>]` —— 语义：「玩家在 Choice `<choice_id>` 选择了第 `n` 个选项」为真。
- **组合**：优先级 `!` > `&` > `|`，圆括号分组。例：`choice:RGj3o4sKsD[2] & !choice:RGcLQj1YBt[1]` = 「在 RGj3o4sKsD 选了第 2 项，且在 RGcLQj1YBt 没选第 1 项」。
- **选项序号 n 的定义**：该 Choice 全部出边 `option` 按 `label` 字典序（Unicode 升序）排列的 **1 基序号**。书写/校验时的可复现查询：
  ```cypher
  MATCH (c:Choice {id:'<choice_id>'})-[o:option]->(:Event)
  RETURN o.label ORDER BY o.label
  ```
- 注意：
  - **字典序 ≠ 叙事呈现顺序**。例：「三选一」三个选项 label 为 选林梦/选苏晓禾/选沈暮雪，字典序 林 < 沈 < 苏，故 `[1]`=选林梦、`[2]`=选沈暮雪、`[3]`=选苏晓禾。**写 condition 必须现查上表，不靠记忆**。
  - 同一 Choice 的 option.label **不得重复**（否则序号歧义）；改 label 等于改全部序号——凡被 condition 引用的 Choice，调整选项 label 前必须排查引用。
  - 求值输入 = 玩家选择史（运行时状态）；图上 option 边全集只提供序号基准，不承载「玩家实际选了什么」。
- **校验**（人工/工具自检，非法不落库）：choice_id 在图中存在；`n` ≤ 该 Choice 的 option 总数；括号配对；无空原子。
- Choice 节点与 presents/option 边定义见下文；condition 与 option 的分工（硬跳转 vs 软门控）见 option 边节。

**语法（BNF）**：

```
condition := ε | expr
expr      := term ( "|" term )*
term      := factor ( "&" factor )*
factor    := "!" factor | atom
atom      := "choice:" choice_id "[" n "]"
choice_id := [0-9A-Za-z]+        （雪花 Base62）
n         := [1-9][0-9]*         （1 基正整数）
```

---
