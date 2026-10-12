---
name: nrt-gap-filler
description: |
  叙事链路缺口的交互式补全：用图算法发现 event→spot→scene→char 链路断点（缺定位/待场景化/缺参与人/断链），
  逐个向用户提问确认修法（每题附推荐答案），全部敲定后组装修改建议 JSON 落盘 → dashboard 待审。
  与 nrt-narrative-grower 的分工：grower 是无人值守体检+LLM 创意推断（不交互、建议直接落盘）；
  本 skill 是有人值守的逐缺口修复对话——每条修法经用户确认才进建议，且推荐答案可解释（带理由标签与数据依据）。
  在用户说「补缺口」「补链路」「修断点」「gap-filler」或要求交互式治理叙事图时使用。
argument-hint: [focus]
arguments:
  - focus
allowed-tools: Read, Bash, Write
---

# 叙事链路缺口交互补全（nrt-gap-filler）

目标：让每个 Event 走通「时间 + 地点 + 人物 + 视觉落点」的完整链路。**图算法发现缺口 → 逐个问用户 → 明确后提交 dashboard 待审**。

> **只读不写（交互期间）**：发现与确认阶段仅查询图。用户敲定全部修法后，一次性组装建议 JSON 落盘；写库永远由人工在 dashboard Cypher 控制台执行（两段确认 + 级联预览），本 skill 不执行任何写语句。
>
> **产出兼容 grower 管道**：建议 JSON 逐项 `{check, priority, reason, content, cypher}` + `source:'nrt-gap-filler'`，落盘 `02_剧情数据/<日期>_round<N>_<主题>_补全_建议.json`——dashboard `/events` 页「📥 grower 建议」弹窗直接可读（该弹窗取最新 3 个 `*_建议.json`，文件必须以 `_建议.json` 结尾才会被拾取——曾用 `_补全建议.json` 因不匹配 glob 落空，勿回退；`source` 字段在弹窗内容里与 grower 产出区分）。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
SF_GEN="python ${CLAUDE_SKILL_DIR}/../../scripts/snowflake_base62.py"
OUTPUT_DIR="02_剧情数据"
```

- Schema：[叙事基础.md](../../../00_init/Schema/叙事基础.md)（字段/边方向/不变式的唯一事实来源）。
- 缺口检查查询库与推荐规则：[references/gap-queries.md](references/gap-queries.md)（含回测命中率背书，先读它）。
- 写 cypher 规则：[cypher_exec.py](../../scripts/cypher_exec.py) 顶部 docstring（内联值、MERGE 幂等、必须指定标签、加 LIMIT）。

## 流程总览

```
1. scan     跑缺口检查（图算法）→ 缺口清单
2. tree     每个缺口 → 一个待决问题；缺口间的依赖 → 问题树
3. rounds   一题一答逐个问（每题带推荐答案）→ 答复更新工作表
4. commit   问题问尽 → 组装建议 JSON 落盘 → 报审批入口，退出
```

---

## 1. scan — 图算法发现缺口

用 `$CYPHER_EXEC -c "<cypher>" --json` 依次跑 [gap-queries.md](references/gap-queries.md) 的五组检查（E 事件链 / S 空间链 / C 角色链 / X 断链 / **V 内容缺口**）。`focus` 传入时先查锚点，全部查询收窄到锚点 1-2 跳子图（模板见 gap-queries.md 的 focus 变体）。

产出**缺口清单**（内存中的工作表，不落盘）：

| 组 | 缺口类型 | 判定 | 修复动作空间 |
|---|---|---|---|
| E1 | Event 缺 occurs_at | `NOT (e)-[:occurs_at]->()` | 挂既有 Spot / 新建 Location+default Spot / 新建 zone |
| E2 | Event 挂的 Spot 无 realizes | `(e)-[:occurs_at]->(sp)` 且 `NOT (sp)-[:realizes]->()` | 挂别的既有 Spot / 场景化派单（建 Scene，交 scene-design） |
| E3 | Event 缺 involved（非结局事件） | 无 involved 且 ending_kind 空 | 挂既有角色 / 新建角色 |
| S1 | Spot 有事件待场景化 | E2 的 Spot 视角聚合 | 建 Scene+realizes（场景化派单） |
| S2 | Location 缺 default Spot | 无 `kind='default'` 子节点 | 建 default Spot |
| C1 | 角色零事件 | Character 无 involved 出边 | 补事件（转 grower 职责）或确认为背景角色 |
| X1 | evt_relation 断链 | 孤立事件 | 补链 / 确认独立 |
| X2 | Choice 无落点 | option 指向的 Event 缺失 | 补目标事件 |
| V1 | 时间线密度不足 | 日差 ≥3 大间隔 / 单日仅 1 事件 | 补桥接事件（创作）/ 接受留白 |
| V2 | 角色弧薄弱 | P0/P1 involved<5 或活动地点<2 | 补事件（创作）/ 确认背景 |
| V3 | 隐含关系 | 共同参与 ≥2 事件但无 relation | 补 relation 边（type/detail 建议值可调） |
| V4 | 孤立 Info | 无任何边的 Info | 补 link 边 / 确认孤立 |

> **V 组与 E/S/C/X 的性质差异**：E/S/C/X 查的是「已有实体的链路断点」（缺口修法是确定性的：挂边/建骨架）；V 查的是「该有而没有的」（修法含**创作**：新事件 title/description 是 LLM 编的）。V 组建议项的 content 必须显式标「创意推断，可调整」。
>
> **V 组级联纪律（防越补越缺）**：V 组确认「补一个新事件」后，该事件天然缺 occurs_at/involved——**同题追问挂哪/谁参与**（复用 E 组的推荐信号），不留新的 E1/E3 缺口下库；V 组与 grower 职责边界见「与 grower 的分工」。

检查跑完先报**总览**（每组几条、涉及哪些实体），不展开细节——展开与否由 round 提问自然带出。

## 2. tree — 缺口 → 问题树

把缺口清单映射成 decision tree（本 skill 的核心抽象，承自 grilling）：

- **每个缺口 = 一个 decision**（怎么修这个缺口）。
- **依赖边**：一个缺口的修法依赖另一个缺口的答案时挂子问题。典型依赖：
  - E1（缺定位）的推荐 Spot 是「不存在的地点」→ 子问题「新建 Location + default Spot 吗？」（S2 随之解锁）
  - E2 聚合出的 S1（多个事件同 Spot）→ 子问题「整组场景化派单还是逐事件改挂？」
  - E3 与 C1 连锁（唯一候选角色是零事件角色）→ 先问 C1 的定性（主角/背景）再定 E3 修法
- **frontier** = prerequisites 已敲定的问题——现在就能问、无需猜测未听到答案的那些。
- **facts 自己查，decisions 问用户**：推荐候选、历史足迹、同日活动都是 facts（cypher 现查，承 grilling 的 sub-agent 原则为「不拿能查到的东西问用户」）；只有修法取舍是 decision。

**聚合降噪（必做）**：同类缺口按推荐动作分组合并成一个问题。逐事件问 64 次是失败设计——「以下 5 个事件建议都挂『八楼出租屋-未细分』（各自理由见推荐）」是一题。聚合粒度：同缺口类型 + 同推荐动作 + 同理由模式 = 一题；单题内列出全部涉及实体。

## 3. rounds — 逐个提问（一题一答）

**一次只问一个问题**，等用户回答后再问下一个（用户明确要求的节奏，不用 grilling 的整条 frontier 批量问）。聚合组（同类型+同动作+同理由模式的缺口合并）仍算一题。每个答复落到工作表——确认修法 / 改选 / 跳过（记录跳过理由，跳过也是一种敲定）。答复可能：解锁追问（如选「细分新 zone」→ 追问 zone 名与空间描述）、作废下游问题、或把已问过的推荐推翻（用户改主意就更新工作表）。

**提问纪律**：每题必附推荐答案且可归因（理由标签 + 数据依据）；facts 不问用户（候选现查）；答案依赖前一题答复的问题必须排在其后；用户答非所问时先澄清再继续；每题开头一句回显「这是第 N 题 / 共约 M 题」让用户知道进度。

```
❓ **Q1** - **八楼出租屋的 6 个事件挂法**：
以下 6 个 Event 挂在「八楼出租屋-未细分」（default，无 Scene）：
发现转账删除温蔓青 / 温蔓青质问电话 / 三个未接来电 / 出租屋庆祝 / 伊芙现身三揭晓 / …
选项：
a) 整组场景化派单（为该 Spot 建 Scene + realizes，转 scene-design 出图）
b) 改挂既有 zone「八楼出租屋-电脑桌区/床铺区/进门处」（各自已有 Scene）
c) 细分新 zone（如「厨房区」）后场景化

➡️ 推荐 b 的逐事件拆挂：6 个事件里 4 个叙述场景明确在电脑桌/床铺（理由标签见下），
   其余 2 个叙述笼统的建议留在 default 走 a) 场景化。依据：该 Location 已有 3 个 zone 全部
   realizes，改挂即达绿档；新建 zone 成本一张图起。
```

**推荐答案的生成规则**（全部可解释，回测依据见 gap-queries.md）：

- **Spot 推荐**（按置信度）：① 文本地名匹配（title/description 含 Location 名或去前缀核心词，命中即排首）→ ② involved 角色历史足迹（occurs_at 次数排序 top-5）→ ③ 角色 at 边（居住/工作地）→ ④ 同 Day 已出现 Spot（仅作并列加分，不单独成题）。每条推荐附理由标签（「文案提及」「陆择常来×7」「陆择居住地」）。
- **Char 推荐**（已定 Spot 后联动）：① 该 Spot 历史参与者（次数降序 top-3）→ ② at 边挂此 Location 的居民 → ③ 同 Day 参与者。
- **冷启动兜底**：四路信号全空（一次性/首访地点，回测占 11%）时，推荐「新建 Location+default Spot」并明确说这是 LLM 判断无历史依据，请用户裁定；完整下拉候选永远在选项里。
- **evt_relation 邻居信号禁用**（回测 16%，事件链跨空间推进，无效）。

**收尾复述**：每敲定 5 个决定左右复述一次已定清单（一句话一条），防长对话漂移；全部问完后 commit 前做最终复述。

## 4. commit — 组装建议 JSON 落盘

全部问题问完（每个缺口都有处置：修复/跳过）后：

1. **推导轮次 N**：扫描 `${OUTPUT_DIR}/*round*_建议.json`（与 grower 共用轮次计数器）取 max+1；主题 = focus 名或「全图」。
2. **组装数组**：每个「修复」决定一项，`{check, priority, reason, content, cypher, source}`：
   - `check` = 缺口类型标识（`E1_missing_occurs_at` / `E2_spot_no_scene` / `E3_no_involved` / `S2_missing_default_spot` / `X1_isolated_event` / `X2_choice_no_target` / `V1_thin_timeline` / `V2_weak_arc` / `V3_implicit_relation` / `V4_orphan_info`）
   - `priority` = E1/E2/S2 high（直接阻断生产）、E3/X1/V1/V2 medium、V3/V4 low、X2/C1 按影响定
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
   - **场景化派单类决定**（E2/S1 选 a 的）：cypher 只建 Scene+realizes 骨架并置 status=0，出图归 scene-design agent——提示用户写回后可从生产看板一键派单，本 skill 不越界出图。

---

## 铁律

1. **交互期间零写库**。落盘的是建议 JSON（文件），不是图。
2. **每题必附推荐答案**，且推荐必须可归因（理由标签 + 数据依据），不许「我觉得」。
3. **facts 不问用户**：候选、历史、同日活动全部现查；只有修法取舍问用户。
4. **聚合提问**：同类型+同动作+同理由模式的缺口合并成一题；单题列全实体。
5. **跳过要留痕**：结束判据是「每个缺口都有处置」，跳过项进汇报清单。
6. **cypher 契约**：MERGE 幂等、内联值单引号转义、必须指定标签、先节点后边、查询加 LIMIT；Event 定位一律 occurs_at→Spot 禁直挂 Location；范围限定叙事基础层（生产链节点只碰 Scene 骨架 status=0，不碰 realizes 以外的美术边）。
7. **一题一答**：一次只问一个，答完再问下一个；依赖前一题答复的问题排在其后。

## 与 grower 的分工（grower 已废弃，2026-10-12 合并）

`nrt-narrative-grower` 的缺口发现能力已全量并入本 skill（V1←temporal_gaps+narrative_density、V2←character_arcs+subgraph_connectivity、V3←implicit_relations、V4←info_depth、X1←event_chains；scene_utilization/bridge_scenes/relationship_evolution 纯统计无动作，弃——dashboard `/events/checkup` 已有同款）。grower skill 目录保留但**已停止维护**，新缺口治理一律走本 skill（有人值守逐题确认）。存量 `02_剧情数据/*_建议.json` 不受影响，dashboard 建议弹窗同通道展示。

> 历史：grower 是无人值守批量体检（LLM 直接产建议落盘不经确认），本 skill 是有人值守版（每条修法经用户确认）。合并后「发现缺口」的唯一入口是本 skill；`/events` 页的「深化(grower)」按钮投递的指令已无对应维护方，dashboard 侧待改为投递本 skill。

## 参考文档

- [缺口检查查询库 + 推荐规则（含回测命中率）](references/gap-queries.md)
- [叙事基础.md Schema](../../../00_init/Schema/叙事基础.md)
- 手动建节点补边：[nrt-graph-builder](../nrt-graph-builder/SKILL.md)（本 skill 落建议 JSON 之外的零星手工通道）
