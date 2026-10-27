---
name: grill
description: |
  新事件的策划编辑式追问生产线（叙事生产四步流程①）：与用户一次一问敲定新 Event
  （每问附推荐答案，继承 grilling 质询方法论），产出建议 JSON 落盘 02_剧情数据/
  → 人工经 dashboard 建议弹窗审阅写回。零图写入、纯文件产物；只产 Event 节点 +
  对话中用户明确给出的 involved/occurs_at 挂边（cypher 只引用图中既有 Character/Location，
  id 起草时解析内联）；新建实体留给 event-refiner ①白名单修复，提及未建档实体只在
  追问中提示不入建议。稀疏纪律：单次至多 3 个 Event，不产 Info——多次运行逐步丰满，
  留白即叙事。在用户说「grill」「敲定事件」「新增事件」「追问」「策划事件」或要从零
  产出一个新叙事事件时使用；存量图缺口治理走 nrt-gap-filler，机位级细化走 event-refiner。
argument-hint: [事件主题 | 时间窗 | 留空自由追问]
arguments:
  - topic
allowed-tools: Read, Bash, Write
---

# 新事件策划编辑式追问（grill）

目标：**从零敲定一个值得发生的新 Event**。不靠图上已有缺口驱动（那是 nrt-gap-filler 的活），
而是从大纲与用户口述出发，用策划编辑式追问（一次一问 + 每问附推荐答案，承 grilling
质询方法论）把事件的贡献/时间/地点/人物/因果逐项敲实，最后组装建议 JSON 落盘，
人工经 dashboard 写回。**用户口述粗料 → 追问敲实 → 建议 JSON**。

> **分工边界**：grill 是**新事件的创作前端**（从零敲定一个事件该发生、长什么样）；
> nrt-gap-filler 是**存量图的治理端**（图算法发现断点 → 修复/渐进丰满）。两者产物同走
> 建议 JSON 通道；写回后的细化（补缺挂边/建档未档实体/拆 SubEvent/派美术单）统一交
> event-refiner。
>
> **只读不写（全程）**：交互期间仅查询图。用户敲定全部事件后，一次性组装建议 JSON 落盘；
> 写库永远由人工在 dashboard（建议弹窗逐条「采纳」或 Cypher 控制台两段确认）执行，
> 本 skill 不执行任何写语句。
>
> **建议 JSON 契约**：逐项 `{check, priority, reason, content, cypher}` + `source:'grill'`，
> 落盘 `02_剧情数据/<日期>_round<N>_<主题>_grill_建议.json`——dashboard `/events` 页
> 「📥 补全建议」弹窗直接可读（该弹窗取最新 3 个 `*_建议.json`，文件必须以 `_建议.json`
> 结尾才会被拾取）；轮次 N 与 nrt-gap-filler / chapter-novelist 共享同一计数器。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
SF_GEN="python ${CLAUDE_SKILL_DIR}/../../scripts/snowflake_base62.py"
OUTPUT_DIR="02_剧情数据"
```

- Schema：[叙事基础.md](../../../00_init/Schema/叙事基础.md)（Event/involved/occurs_at/leads_to 的唯一事实来源）。
- 契约母本：[nrt-gap-filler/SKILL.md](../nrt-gap-filler/SKILL.md)（建议 JSON 契约、提问纪律、cypher 规则的同源实现）。
- 写 cypher 规则：[cypher_exec.py](../../scripts/cypher_exec.py) 顶部 docstring（内联值、MERGE 幂等、必须指定标签、加 LIMIT）。

## 流程总览

```
0. resolve  解析主题入参 → 读大纲 + 只读查图上下文（既有事件/实体名录/待审建议）
1. grill    一次一问敲定每个事件（决策树见下）→ 答复更新工作表（内存）
2. commit   问尽 → 组装建议 JSON 落盘 → 报审批入口与下一步
```

---

## 0. resolve — 解析入参 + 拉上下文

- 入参三态：事件主题短语（如「漫展合练请假」）/ 时间窗（`起始~结束`）/ 留空（自由追问）。
- 读 `00_init/大纲.md`——**推荐答案必须有大纲依据**（事件要服务弧线，不凭空造戏）。
- 只读查图（`$CYPHER_EXEC -c "<cypher>" --json`，全部带 LIMIT）：
  1. 相关时间窗既有 Event（title/time/occurs_at/involved）——去重冲突终检与因果候选的依据；
  2. Character / Location 名录——名称→id 解析表（**id 内联进 cypher，不在 cypher 里做名称
     匹配**：重名/改名会静默错挂）；
  3. 涉分支时 Choice option label 序号表（condition 的序号 = option 按 label 字典序 1 基
     编号，现查不靠记忆）；
  4. 扫最近几份 `*_建议.json`——已提案未审批的事件标「待审」，不重复起草，只在追问中
     提醒审批状态。

## 1. grill — 事件决策树（每事件按序过，一题一答）

每个事件按以下维度推进。**聚合降噪**：高置信维度（type/description 要点/ending_kind）
并入相邻题一起确认（像 event-refiner 的「完整方案整体拍板」），核心分歧题（弧线贡献/
time/occurs_at/involved）单独问——单事件约 4~6 题，不逐维度机械拆问。

| # | 维度（问题示例） | 推荐答案来源 |
|---|---|---|
| 1 | 这个事件为弧线贡献什么（**删除测试**：删了弧线塌吗） | 大纲 + 时间窗邻接事件 |
| 2 | title + 一句话概述 + type（行动/交流/转折/状态变化） | 用户口述提炼 |
| 3 | **time 锚点**（'yyyy-MM-dd HH:mm:ss' 必填；给同日邻接事件时刻供插位） | 时间窗邻接查询 |
| 4 | **occurs_at**（只推既有 Location：① 文本地名匹配 ② 参与人历史足迹 ③ at 边） | 只读查图 |
| 5 | **involved + role**（逐人敲定枚举值：当事人/目击者/受害者/施害者/参与者；只推既有 Character：该 Location 历史参与者 → at 边居民 → 同日参与者） | 只读查图 |
| 6 | description 要点（钉子细节 1-3 句） | 口述 |
| 7 | ending_kind（**仅定位为结局事件才问**，BE/TE/HE/NE） | — |
| 8 | condition（**仅分支相关才问**；现查 option 序号表后给候选表达式） | Choice 查询 |
| 9 | 因果（**仅用户明说才建** leads_to：「明确由哪个既有事件导致/导致哪个？」） | 时间窗因果候选 |
| 10 | **去重冲突终检**（与时间/地点/参与人重叠的既有事件对照：合并/改时间/放弃） | 只读查图 |

**交互纪律**（承 grilling）：

- **一次只问一个问题**，等用户回答后再问下一个；每问开头一句回显「这是第 N 题 / 共约 M 题」。
- **每问必附推荐答案且可归因**（理由标签 + 数据依据，不许「我觉得」）；「放弃这个事件」
  永远在选项里——追问本身可能证伪事件的价值。
- 回答模糊 → 标「未解决依赖」继续，后续成为矛盾根源时回溯重问。
- **共识判据**：该事件可一段话概述（贡献/时间/地点/人物/因果）且连续三问无新矛盾。
- **收尾复述**：每约 5 个决定复述一次已定清单（一句话一条），防长对话漂移；commit 前做
  最终复述。
- 语言禁忌：不一次性抛问卷、不替用户写大段正文、始终用「你」。

## 2. commit — 组装建议 JSON 落盘

全部事件问尽（每个候选都有处置：敲定/放弃，放弃要留痕进汇报）后：

1. **推导轮次 N**：扫描 `${OUTPUT_DIR}/*round*_建议.json` 取 max+1（全生产者共享计数器）。
2. **主题** = 入参主题短语 / 时间窗起止（如 `0623-0625`）/「自由」。
3. **组装数组**：每个敲定的事件一项，`{check, priority, reason, content, cypher, source}`：
   - `check` = `G1_new_event`
   - `priority` = medium 缺省；结局事件（ending_kind 非空）/ 转折类 high
   - `reason` = 大纲依据 + 用户口述来源 + 敲定过程要点
   - `content` = 人读事件卡片（title/time/type/地点（或「缺，refiner ① 补」）/参与人/因果）
   - `cypher` = 开箱可执行（模板见下）
   - `source` = `'grill'`
   - id 用 `$SF_GEN -n 1 -q` 逐事件生成。
4. **Write 落盘** `${OUTPUT_DIR}/${DATE}_round<N>_<主题>_grill_建议.json`（顶层数组，UTF-8）。
   落盘即提交——dashboard 不接收推送，`GET /events/suggestions` 按 glob 拾取最新 3 个文件。
5. **汇报收尾**：文件路径 + 建议条数与 priority 分布 + 放弃清单（含理由）+ 未建档实体
   清单（提示 event-refiner ① 会建档修复）+ 待审重叠提醒 + 下一步话术：
   - dashboard `/events` 页「📥 补全建议」弹窗逐条审阅「采纳」写回；
   - 写回后跑 `event-refiner`（传新事件 id/title）：补缺挂边/建档未档实体/拆 SubEvent/派美术单。

## cypher 模板（照抄改值，形状对齐 gap-filler 产出的建议语句）

```
CREATE (e:Event {id:'<snowflake>'}) SET e.title='<title>', e.time='<yyyy-MM-dd HH:mm:ss>', e.type='<type>', e.description='<desc>';
MATCH (e:Event {id:'<snowflake>'}), (l:Location {id:'<loc_id>'}) MERGE (e)-[r:occurs_at]->(l) ON CREATE SET r.sync=false;
MATCH (c:Character {id:'<char_id>'}), (e:Event {id:'<snowflake>'}) MERGE (c)-[r:involved]->(e) ON CREATE SET r.role='<role>', r.sync=false;
// 仅用户明说因果时追加（方向 = 因 → 果）：
MATCH (a:Event {id:'<既有事件id>'}), (e:Event {id:'<snowflake>'}) MERGE (a)-[r:leads_to]->(e);
```

- 多语句 `;`+换行分隔，逐句以 `;` 结尾；先建节点再挂边。
- involved 每人一条 MERGE；occurs_at 可多条（跨地点事件）；ending_kind/condition 仅在
  敲定值时并入首句 SET（如 `SET e.title=…, e.ending_kind='TE', e.condition='choice:abc123[2]'`）。
- 内联值单引号转义；不用 `$param`；**不加 Event 间时序边**（先后时序由 `Event.time`
  字符串序承载，Schema 已废止 evt_relation）。

## 铁律

1. **全程零写库**。落盘的是建议 JSON（文件），不是图。
2. **只产 Event**：新建 Event 节点 + 用户明确给出的 involved/occurs_at 挂边（既有实体）+
   （仅用户明说因果时）leads_to。不建 Character/Location/Info/Choice/Spot/Scene/SubEvent，
   不改既有节点属性。
3. **未建档实体只提示**：追问中发现提及的 Character/Location 不在图中 → 在问题里明示
   「图中未建档，本次不入建议，event-refiner ① 会建档修复」，对应挂边语句整段省略并在
   content 注明「occurs_at/involved 缺——refiner ① 补」。
4. **稀疏纪律**：单次至多 3 个 Event，不产 Info；超限候选只取优先级最高者，其余汇报为
   「下次可敲定」——多次运行逐步丰满是设计意图，留白即叙事。
5. **一题一答 + 每问必附推荐答案**，推荐必须可归因（理由标签 + 数据依据）。
6. **facts 不问用户**：候选、历史、同日活动、option 序号全部现查；只有取舍问用户。
7. **title/description 不带时间**：新事件的 title 与 description 禁止携带任何时间信息
   （绝对日期、「第 N 天」、周次、时段词「次日/当晚/周末/两周后」等）——时间真相唯一
   承载是 `Event.time`；用户口头带时间的草案落 JSON 前转写为无时间表述。
8. **防重**：已提案未审批的事件不重复起草，只提醒审批状态；commit 前必过去重冲突终检。
9. **cypher 只含交付目标本身**，禁止夹带自造的「校验/checksum 节点」；执行校验由 agent
   在用户回报执行后用只读查询回查完成。

## 参考文档

- [nrt-gap-filler/SKILL.md](../nrt-gap-filler/SKILL.md) — 同源契约与提问纪律
- [叙事基础.md Schema](../../../00_init/Schema/叙事基础.md)
