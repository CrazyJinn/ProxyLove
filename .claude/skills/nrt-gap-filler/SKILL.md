---
name: nrt-gap-filler
description: |
  叙事关系缺口的交互式补全 + 渐进丰满：用图算法发现 Character/Event/Location/Info/Choice 五实体的关系断点
  （缺定位/缺参与人/因果断链/分支断头/孤立 Info），并支持两种启发式填充入参——
  ① 自由探索人物：查该角色时间线/关系/内心戏哪里薄，提案日常事件与 Info；
  ② 时间段：显式时间窗或两个事件定界，为窗口内空白日/叙事跳变启发式补桥接或点缀内容。
  逐个向用户提问确认修法（每题附推荐答案），全部敲定后组装修改建议 JSON 落盘 → dashboard 待审。
  稀疏纪律：创作类新增单次至多 3 Event + 2 Info——本 skill 靠多次运行逐步丰满，留白即叙事。
  范畴 = 叙事基础层五实体及其边；Spot/Scene 属场景域（scene-designer 独占），本 skill 不检查不创建。
  与 nrt-narrative-grower 的分工：grower 是无人值守体检+LLM 创意推断（不交互、建议直接落盘，已废弃合并入本 skill）；
  本 skill 是有人值守的逐缺口修复对话——每条修法经用户确认才进建议，且推荐答案可解释（带理由标签与数据依据）。
  在用户说「补缺口」「补链路」「修断点」「填充时间段」「两事件之间补」「探索/丰满人物」「gap-filler」或要求交互式治理叙事图时使用。
argument-hint: [角色名 | 事件A → 事件B | 起始~结束时间]
arguments:
  - focus
allowed-tools: Read, Bash, Write
---

# 叙事关系缺口交互补全（nrt-gap-filler）

目标：让叙事基础层五个实体——**Character / Event / Location / Info / Choice**——的关系闭环走通：每个 Event 有时间 + 地点 + 参与人，因果链（leads_to）与分支（Choice+option）不断头，Info 不孤立；显式聚焦（人物/时间窗）时另做**启发式提案**让图渐进丰满。**图算法发现缺口 → 逐个问用户 → 明确后提交 dashboard 待审**。

> **范畴边界**：本 skill 只检查与修复**叙事基础层**（五实体 + occurs_at/involved/relation/at/link/leads_to/presents/option 八边）。Spot/Scene/anchored_at/realizes 属**场景域**（见 00_init/Schema/场景美术.md），由 scene-designer 独占——本 skill 不检查、不建议、不创建。
>
> **只读不写（交互期间）**：发现与确认阶段仅查询图。用户敲定全部修法后，一次性组装建议 JSON 落盘；写库永远由人工在 dashboard Cypher 控制台执行（两段确认 + 级联预览），本 skill 不执行任何写语句。
>
> **产出兼容 grower 管道**：建议 JSON 逐项 `{check, priority, reason, content, cypher}` + `source:'nrt-gap-filler'`，落盘 `02_剧情数据/<日期>_round<N>_<主题>_补全_建议.json`——dashboard `/events` 页「📥 grower 建议」弹窗直接可读（该弹窗取最新 3 个 `*_建议.json`，文件必须以 `_建议.json` 结尾才会被拾取——曾用 `_补全建议.json` 因不匹配 glob 落空，勿回退；`source` 字段在弹窗内容里与 grower 产出区分）。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
SF_GEN="python ${CLAUDE_SKILL_DIR}/../../scripts/snowflake_base62.py"
OUTPUT_DIR="02_剧情数据"
```

- Schema：[叙事基础.md](../../../00_init/Schema/叙事基础.md)（五实体/边定义/不变式的唯一事实来源）。
- 缺口检查查询库与推荐规则：[references/gap-queries.md](references/gap-queries.md)（含回测命中率背书，先读它）。
- 写 cypher 规则：[cypher_exec.py](../../scripts/cypher_exec.py) 顶部 docstring（内联值、MERGE 幂等、必须指定标签、加 LIMIT）。

## 流程总览

```
0. resolve  解析入参 → 模式：人物聚焦 / 时间窗 / 全图（决定 scan 跑哪些组）
1. scan     跑缺口检查（图算法）→ 缺口清单
2. tree     每个缺口 → 一个待决问题；缺口间的依赖 → 问题树
3. rounds   一题一答逐个问（每题带推荐答案）→ 答复更新工作表
4. commit   问题问尽 → 组装建议 JSON 落盘 → 报审批入口，退出
```

---

## 1. scan — 图算法发现缺口

先 resolve 入参定模式（判定规则与定界查询见 [gap-queries.md](references/gap-queries.md) H 组「入参定界」）：

- **人物聚焦**（参数命中 Character name/id）：E/C/X/V 收窄到锚点 1-2 跳子图（focus 变体），**加跑 H2**（人物丰满启发）。
- **时间窗**（参数为 `起始~结束` 时间串，或两个事件 title/id 定界）：**只跑 H1**（窗口启发填充）——窗口界定本身就是一次显式密度治理，V1 大间隔不再单独跑；侦察查询带 occurs_at/involved，窗口内暴露的 E1/E3 缺口按原修法走（挂边，非创作）。
- **全图**（无参数）：E/C/X/V 全量；**不跑 H**——启发创作提案只在显式聚焦时做，避免全图轰炸。

模式定了以后，用 `$CYPHER_EXEC -c "<cypher>" --json` 依次跑 [gap-queries.md](references/gap-queries.md) 的五组检查（E 事件链 / C 角色链 / X 断链 / V 内容缺口 / **H 启发填充**）。

产出**缺口清单**（内存中的工作表，不落盘）：

| 组 | 缺口类型 | 判定 | 修复动作空间 |
|---|---|---|---|
| E1 | Event 缺 occurs_at | `NOT (e)-[:occurs_at]->(:Location)` | 挂既有 Location / 新建 Location |
| E3 | Event 缺 involved（非结局事件） | 无 involved 且 ending_kind 空 | 挂既有角色 / 新建角色 |
| C1 | 角色零事件 | Character 无 involved 出边 | 补事件（创作）/ 确认为背景角色 |
| X1 | 因果断链 | 孤立事件（无 leads_to 出入边） | 补 leads_to 链 / 确认独立 |
| X2 | Choice 选项无落点 | option 指向的 Event 缺失 | 补目标事件（创作） |
| V1 | 时间线密度不足 | 日差 ≥3 大间隔 / 单日仅 1 事件 | 补桥接事件（创作）/ 接受留白 |
| V2 | 角色弧薄弱 | P0/P1 involved<5 或活动地点<2 | 补事件（创作）/ 确认背景 |
| V3 | 隐含关系 | 共同参与 ≥2 事件但无 relation | 补 relation 边（type/detail 建议值可调） |
| V4 | 孤立 Info | 无任何边的 Info | 补 link / leads_to 边 / 确认孤立 |
| H1 | 时间窗空白/叙事跳变 | 窗口逐日侦察 + LLM 启发选点（时间窗模式专属） | 补桥接/点缀事件、跟进 Info（创作）/ 接受留白 |
| H2 | 人物薄期/内心戏缺失 | 人物全景 + 时间线启发（人物模式专属） | 补日常事件/内心 Info（创作）/ 确认现状 |

> **V 组与 E/C/X 的性质差异**：E/C/X 查的是「已有实体的链路断点」（缺口修法是确定性的：挂边/建骨架）；V 查的是「该有而没有的」（修法含**创作**：新事件 title/description 是 LLM 编的）。V 组建议项的 content 必须显式标「创意推断，可调整」。
>
> **V 组级联纪律（防越补越缺）**：V 组确认「补一个新事件」后，该事件天然缺 occurs_at/involved——**同题追问挂哪/谁参与**（复用 E 组的推荐信号），不留新的 E1/E3 缺口下库；V 组与 grower 职责边界见「与 grower 的分工」。
>
> **H 组 = 显式聚焦时的创作提案，严守稀疏纪律**：单次运行至多提案 **3 Event + 2 Info**，候选超限只取优先级最高者，其余汇报为「下次可补」；「接受留白」永远在选项里，低信号时是推荐项。**多次运行逐步丰满是设计意图——每次少补一点，不是一次填满**。提案前扫最近一轮 `*_建议.json` 的 H 组条目：已提案未审批的插入点标「上轮已提案待审」，不重复草案只提醒审批状态。H 组级联纪律同 V 组（新事件同题追问 occurs_at/involved）。

检查跑完先报**总览**（每组几条、涉及哪些实体），不展开细节——展开与否由 round 提问自然带出。

## 2. tree — 缺口 → 问题树

把缺口清单映射成 decision tree（本 skill 的核心抽象，承自 grilling）：

- **每个缺口 = 一个 decision**（怎么修这个缺口）。
- **依赖边**：一个缺口的修法依赖另一个缺口的答案时挂子问题。典型依赖：
  - E1（缺定位）的推荐 Location 是「不存在的地点」→ 子问题「新建 Location 吗？」
  - E3 与 C1 连锁（唯一候选角色是零事件角色）→ 先问 C1 的定性（主角/背景）再定 E3 修法
  - X2（Choice 无落点）的修法是新建目标 Event → 新 Event 的 occurs_at/involved 联动追问（同 V 组级联纪律）
  - V4（孤立 Info）选「补 leads_to」→ 追问因果上/下游是哪个 Event/Info（候选现查时间邻近与文本相关）
- **frontier** = prerequisites 已敲定的问题——现在就能问、无需猜测未听到答案的那些。
- **facts 自己查，decisions 问用户**：推荐候选、历史足迹、同日活动都是 facts（cypher 现查，承 grilling 的 sub-agent 原则为「不拿能查到的东西问用户」）；只有修法取舍是 decision。

**聚合降噪（必做）**：同类缺口按推荐动作分组合并成一个问题。逐事件问 64 次是失败设计——「以下 5 个事件建议都挂『八楼出租屋』（各自理由见推荐）」是一题。聚合粒度：同缺口类型 + 同推荐动作 + 同理由模式 = 一题；单题内列出全部涉及实体。

## 3. rounds — 逐个提问（一题一答）

**一次只问一个问题**，等用户回答后再问下一个（用户明确要求的节奏，不用 grilling 的整条 frontier 批量问）。聚合组（同类型+同动作+同理由模式的缺口合并）仍算一题。每个答复落到工作表——确认修法 / 改选 / 跳过（记录跳过理由，跳过也是一种敲定）。答复可能：解锁追问（如 E1 选「新建 Location」→ 追问名称与描述）、作废下游问题、或把已问过的推荐推翻（用户改主意就更新工作表）。

**提问纪律**：每题必附推荐答案且可归因（理由标签 + 数据依据）；facts 不问用户（候选现查）；答案依赖前一题答复的问题必须排在其后；用户答非所问时先澄清再继续；每题开头一句回显「这是第 N 题 / 共约 M 题」让用户知道进度。

```
❓ **Q1** - **八楼出租屋的 6 个事件定位**：
以下 6 个 Event 缺 occurs_at（叙事明示发生在八楼出租屋）：
发现转账删除温蔓青 / 温蔓青质问电话 / 三个未接来电 / 出租屋庆祝 / 伊芙现身三揭晓 / …
选项：
a) 整组挂既有 Location「八楼出租屋」
b) 挂其他既有 Location
c) 新建 Location

➡️ 推荐 a：6 个事件的 title/description 均明示在出租屋（理由标签「文案提及」），
   该 Location 已有 7 个历史事件（陆择常来×7），挂上即完成定位闭环。
```

**推荐答案的生成规则**（全部可解释，回测依据见 gap-queries.md）：

- **Location 推荐**（按置信度）：① 文本地名匹配（title/description 含 Location 名，命中即排首）→ ② involved 角色历史足迹（occurs_at→Location 次数排序 top-5）→ ③ 角色 at 边（居住/工作地）→ ④ 同日已出现 Location（datetime 取 date 部分组，仅作并列加分，不单独成题）。每条推荐附理由标签（「文案提及」「陆择常来×7」「陆择居住地」）。
- **Char 推荐**（已定 Location 后联动）：① 该 Location 历史参与者（次数降序 top-3）→ ② at 边挂此 Location 的居民 → ③ 同日参与者。
- **Info/Choice 联动推荐**（X2/V4 用）：X2 补落点事件时，参与人与地点承 presents 上游事件（分支与主干同场同人，facts 现查上游 involved/occurs_at）；V4 补边时，候选 = 时间邻近 ±1 事件的 link/leads_to 惯例 + title 文本相关节点。
- **H 组创作推荐**（H1/H2 用）：推荐答案 = 创作草案本身——拟插入时间点 + title + 一句话 description，依据列启发维度与触发信号（「因果跳变：质问→庆祝 无过渡」「空白 3 日」「三个未接来电无跟进」）。content 必标「创意推断，可调整」；用户可现场改 title/description/时间，改后版本入建议。
- **冷启动兜底**：四路信号全空（一次性/首访地点）时，推荐「新建 Location」并明确说这是 LLM 判断无历史依据，请用户裁定；完整下拉候选永远在选项里。
- **leads_to 邻居信号禁用**（因果链跨空间推进，无效——原 evt_relation 邻接回测同地点比例仅 16%）。

**收尾复述**：每敲定 5 个决定左右复述一次已定清单（一句话一条），防长对话漂移；全部问完后 commit 前做最终复述。

## 4. commit — 组装建议 JSON 落盘

全部问题问完（每个缺口都有处置：修复/跳过）后：

1. **推导轮次 N**：扫描 `${OUTPUT_DIR}/*round*_建议.json`（与 grower 共用轮次计数器）取 max+1；主题 = focus 名 / 时间窗起止（如 `03-01~03-10`）或「全图」。
2. **组装数组**：每个「修复」决定一项，`{check, priority, reason, content, cypher, source}`：
   - `check` = 缺口类型标识（`E1_missing_occurs_at` / `E3_no_involved` / `C1_zero_event_char` / `X1_isolated_event` / `X2_choice_no_target` / `V1_thin_timeline` / `V2_weak_arc` / `V3_implicit_relation` / `V4_orphan_info` / `H1_window_fill` / `H2_char_richness`）
   - `priority` = E1/X2 high（直接断叙事流）、E3/X1/V1/V2/H1 medium（H1 桥接因果跳变 medium、纯点缀降 low）、C1/V3/V4/H2 low、按影响可调
   - `reason` = 缺口事实（图算法查出什么）+ 用户在对话中敲定的依据
   - `content` = 人读修法描述（含理由标签）
   - `cypher` = 开箱可执行（MERGE 幂等、内联值、节点语句在前边语句在后；新建节点用 `$SF_GEN` 生成 id）
   - `source` = `'nrt-gap-filler'`（区分 grower 产出）
   - 聚合决定拆成逐条 cypher（每实体一条建议项），但 content 注明「同组批量：<组名>」——dashboard 逐条审时能看出组内关联。
   - **跳过的缺口不产生建议项**，但在对话汇报中列出（缺口 + 跳过理由），保证没有默默消失的缺口。
3. **Write 落盘** `${OUTPUT_DIR}/${DATE}_round<N>_<主题>_补全_建议.json`（顶层数组）。**落盘即提交**——dashboard 不接收推送，`GET /events/suggestions` 每次按 glob 拾取最新 3 个文件；落盘后可用该接口回查验证拾取成功。
4. **汇报收尾**：文件路径 + 建议条数与 priority 分布 + 跳过清单 + 审批入口提示：
   - dashboard `/events` 页「📥 grower 建议」弹窗查看（本文件与 grower 建议同通道）；
   - 逐条审过后经 `/data` Cypher 控制台执行写库（两段确认 + 级联预览）；MERGE 幂等，执行前自查该条是否已写回。

---

## 铁律

1. **交互期间零写库**。落盘的是建议 JSON（文件），不是图。
2. **每题必附推荐答案**，且推荐必须可归因（理由标签 + 数据依据），不许「我觉得」。
3. **facts 不问用户**：候选、历史、同日活动全部现查；只有修法取舍问用户。
4. **聚合提问**：同类型+同动作+同理由模式的缺口合并成一题；单题列全实体。
5. **跳过要留痕**：结束判据是「每个缺口都有处置」，跳过项进汇报清单。
6. **范畴与 cypher 契约**：范畴 = 叙事基础层五实体（Character/Event/Location/Info/Choice）及其八边（occurs_at/involved/relation/at/link/leads_to/presents/option）；**Spot/Scene 属场景域，本 skill 不检查不创建**（场景化归 scene-designer）。cypher 一律 MERGE 幂等、内联值单引号转义、必须指定标签、先节点后边、查询加 LIMIT；Event 定位一律 occurs_at→Location（一跳直挂）；叙事因果一律 leads_to，**Event 间禁建 evt_relation（已废止，先后时序由 Event.time 承载）**。
7. **一题一答**：一次只问一个，答完再问下一个；依赖前一题答复的问题排在其后。
8. **稀疏填充**：创作类新增（H 组）单次至多提案 3 Event + 2 Info，宁少勿多——多次运行逐步丰满是设计意图，不是一次填满；「接受留白」永远在选项里，低信号时是推荐项；上轮已提案待审的插入点不重复提案。

## 与 grower 的分工（grower 已废弃，2026-10-12 合并）

`nrt-narrative-grower` 的缺口发现能力已全量并入本 skill（V1←temporal_gaps+narrative_density、V2←character_arcs+subgraph_connectivity、V3←implicit_relations、V4←info_depth、X1←event_chains；scene_utilization / bridge_scenes / relationship_evolution 为场景域统计且纯统计无动作，弃——场景域体检随 Spot 出圈一并移出本 skill 范畴）。grower skill 目录保留但**已停止维护**，新缺口治理一律走本 skill（有人值守逐题确认）。存量 `02_剧情数据/*_建议.json` 不受影响，dashboard 建议弹窗同通道展示。

> 历史：grower 是无人值守批量体检（LLM 直接产建议落盘不经确认），本 skill 是有人值守版（每条修法经用户确认）。合并后「发现缺口」的唯一入口是本 skill；`/events` 页的「深化(grower)」按钮投递的指令已无对应维护方，dashboard 侧待改为投递本 skill。

## 参考文档

- [缺口检查查询库 + 入参定界 + 推荐规则（含回测命中率）](references/gap-queries.md)
- [叙事基础.md Schema](../../../00_init/Schema/叙事基础.md)
- 手动建节点补边：[nrt-graph-builder](../nrt-graph-builder/SKILL.md)（本 skill 落建议 JSON 之外的零星手工通道）
