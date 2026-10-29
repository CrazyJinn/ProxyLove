---
name: event-ideator
description: |
  新事件的需求提出层（叙事生产链第一环）：从人物设定出发启发新 Event 候选，与用户
  多轮交互（一次一问、每问附可归因推荐答案）敲定后产出建议 JSON
  落盘 02_剧情数据/ → 人工经 dashboard 建议弹窗审阅写回。零图写入、纯文件产物。
  产物范围：Event 节点 + involved/occurs_at 挂边 + Character/Location 占位节点（三要素
  细化时所需实体图上不存在 → 占位 status=0，待后续消化）+
  （仅用户明说因果时）leads_to + Info 节点（限产：仅锚点关系中明显缺内心戏/静态
  注记时，≤2 个/次，link 挂锚点）。五种启发模式：char→new→base（动机链补桥，抵达既定
  事件）/ char→new（人物质感填充）/ base→new→base（两既定事件间间隙填充，可无关）/
  base→new（既定事件的后果链推演）/ new→base（无角色锚的因果回溯）。入参 char 与
  base 至少给一个。
  不做：拆解、机位、着装、任何演出域决策。稀疏纪律：单次至多
  3 个 Event + 2 个 Info——多次运行逐步丰满，留白即叙事。在用户说「想事件」「启发
  事件」「敲定事件」「新增事件」或要从零产出新叙事事件时使用。
argument-hint: <char 名或 id | base event id或title | 两者都给>（char 与 base 至少一个）
arguments:
  - char_and_base
allowed-tools: Read, Bash, Write
---

# 新事件启发与敲定（event-ideator）

目标：**从人物设定出发，生成并敲定值得发生的粗粒度新 Event**（需求提出层——
创作判断在本层发生，创建权就在本层：Event + 叙事基础占位）。

> **只读不写（全程）**：交互期间仅查询图。用户敲定后一次性组装建议 JSON 落盘；
> 写库永远由人工在 dashboard（建议弹窗逐条「采纳」或 Cypher 控制台两段确认）执行。
>
> **建议 JSON 契约**：顶层数组，逐项 `{check, priority, reason, content, cypher}` +
> `source:'event-ideator'`（check 取值见 §4），落盘
> `02_剧情数据/<日期>_round<N>_<主题>_ideator_建议.json`——必须 `_建议.json` 结尾，
> dashboard「📥 补全建议」弹窗按此 glob 拾取最新 3 个文件，落盘即提交（不接收推送）。
> 一条建议的 cypher 可多语句（`;`+换行分隔，先节点后边）；**禁止夹带自造的校验节点**
> （必然孤儿）；执行校验由用户回报后只读回查完成。轮次 N 由 `$ROUND` 推导（全
> skill 共享计数器）。
>
> **产出纪律**：每个写回的 Event，其 involved Character 与 occurs_at Location
> **必已在图上**（既有的或本轮占位的）——缺实体一律占位兜底，不留无实体挂边的悬空事件。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
SF_GEN="python ${CLAUDE_SKILL_DIR}/../../scripts/snowflake_base62.py"
ROUND="python ${CLAUDE_SKILL_DIR}/../../scripts/suggest_round.py"     # 轮次推导（共享计数器）
NBHD="python ${CLAUDE_SKILL_DIR}/scripts/neighborhood.py"             # 锚点关系查询（双锚连通性）
OUTPUT_DIR="02_剧情数据"
```

- Schema：[叙事基础.md](../../../00_init/Schema/叙事基础.md)（Event/involved/occurs_at/
  leads_to 的唯一事实来源）。
- 写 cypher 规则：[cypher_exec.py](../../scripts/cypher_exec.py) 顶部 docstring
  （内联值、MERGE 幂等、必须指定标签、加 LIMIT）。

## 流程总览（五步：探索图 → 启发 → 三要素细化 → 询问 → 落盘）

```
0. explore  解析入参（char 必填 + base event 可选）→ 锚点关系查询 + 只读查图上下文
1. ideate   五模式启发 → 候选 new event 批（多条差异化候选 + 评分对比表）
2. enrich   三要素细化：char / location / time 补全；缺失实体 → Character/Location 占位提案
3. ask      一次一问逐事件敲定（候选评分表 → 用户挑选/修改/放弃）
4. commit   问尽 → 组装建议 JSON 落盘 → 报审批入口与下一步
```

---

## 0. explore — 解析入参 + 拉上下文

- 入参（char 与 base 至少给一个，可同给）：`char`（人名或 id——启发的人物锚点，多个角色顿号分隔）；
  `base event`（id 或 title——既定目标事件；给 char 时启用动机链/间隙模式，只给 base 时
  启用后果链/回溯模式）。
- **推荐答案必须有图数据依据**（人物设定 / 邻域表 / 因果链，事件要服务弧线，不凭空造戏）
- 只读查图（全部带 LIMIT）：
  1. **锚点关系查询**（见下，启发的主依据）；
  2. **char 深读**（锚含 char 时）：人物设定（description/tags/relation）+
     LanguageStyle——人物弧线的第一依据（其历史事件已在邻域表中）；
  3. Character / Location 名录——名称→id 解析表（**id 内联进 cypher，不在 cypher 里
     做名称匹配**：重名/改名会静默错挂）；同时用于识别「提及但未建档」→ 占位候选；
  4. 涉分支时 Choice option label 序号表（condition 序号 = option 按 label 字典序
     1 基编号，现查不靠记忆）；
  5. 扫最近几份 `*_建议.json`——已提案未审批的事件标「待审」，不重复起草。

**锚点关系查询（char 与 base 之间的关系——图上实捞，不是模型想象）**：
`$NBHD --char <char_id> --base <event_id>` 双锚查**两锚在叙事基础域
（Character/Event/Location）的连通性**——直接关系（含 involved.role）+ 间接
路径（≤4 跳，边限 involved/occurs_at/at/relation/leads_to，按真实方向画箭头）
+ 不连通判定；不滚邻域雪球（不把锚点周围的所有 char/location 全捞出来）。
单锚退化为一跳清单：`--char` → 近期 10 事件 + at 常驻地 + relation 关系人；
`--base` → 参与人（·role）+ 地点 + leads_to 因果邻居。锚点查无时脚本直接报错
退出（先做名称→id 解析），不静默降级不猜。

**读图口径（看查询结果直判，启发从数据长出来，不凭空造）**：

- **连通性即空隙**：双锚不连通或仅弱连通（≥3 跳）——新事件就是桥，
  `char→new→base` 的落点；已直接 involved 则无需补桥，启发转向质感/间隙模式；
- **中介即桥形态**：间接路径揭示的中介（共同地点、共同参与人、已有因果链的
  上游事件）提示新事件怎么挂——同地点共场、引入中介角色、或接因果上游；
- **时间间隙**（单锚 char 事件列表）：相邻间隔 > 1 天的空洞——喂 `base→new→base`；
- **锚点稀薄**：单锚清单只有 1~2 行 = 该锚点故事稀薄，本身就是最大的信号。

**查询纪律**：只查锚点之间的关系（双锚连通 / 单锚一跳），不做全量邻域扫描——
锚点周围的所有 char/location 全捞出来会稀释信号。深读优于广扫：查询结果中出现
的事件/角色，其 description/relation 细节按候选需要逐个深读。每条候选的理由必须
标注依据（图上实查 vs 由数据做的创作推断，分开表述——依据分离标注）。

## 1. ideate — 五模式启发（候选批，不是逐个问）

按入参组合选定模式（可组合），每模式产 2~3 条候选，合成本轮候选批（合计 ≤6 条）。**候选从 0 步锚点关系中长出来**（不连通/弱连通→补桥，中介→桥形态，时间间隙→间隙填充），每条候选标注来源依据：

| 模式 | 触发条件 | 回答的创作问题 | 产出类型 |
|---|---|---|---|
| `char → new → base` | char + base 给定 | 角色经历了什么才抵达既定事件？ | 动机链事件（因果补桥） |
| `char → new` | char 给定 | 这个人平时会干什么？ | 人物质感事件（血肉填充） |
| `base → new → base` | base 给定且有时间邻接事件 | 两个既定事件之间发生了什么（可有关可无关）？ | 间隙填充事件 |
| `base → new` | base 给定 | 这个既定事件之后引发了什么连锁反应？ | 后果链事件（向前推演，leads_to 正向延伸） |
| `new → base` | base 给定 | 什么导致了这个既定事件（不限单一角色）？ | 无锚因果回溯（多角色/环境前因，补 leads_to 上游） |

**每条候选必带结构化字段**（对比表列）：

- 一句话核心（这个事件是什么）
- 情绪价值（给玩家什么感受）
- 与 base 的关系（因果铺垫 / 后果延伸 / 反差 / 无关；无 base 时填与聚焦锚的关系）
- 评分（四维 1-5 + 综合，评分依据必须可归因）：
  - **人设契合**：与相关角色（char 锚 / base 事件 involved）的设定/创伤/目标一致性（对照 0 步深读）
  - **查图去重**：与既有事件的重复度（时间/地点/参与人重叠 → 低分）
  - **戏剧价值**：对情绪曲线的贡献（铺垫→触发→释放→余韵，缺环处加分）
  - **生产成本**：需新建多少占位（新 Location/新 Character 越多分越低）

**依据分离标注**：候选理由中图上实查的（邻接事件、既有实体）与模型常识推断的
（人物心理推演）分开表述，防幻觉混入图数据。

## 2. enrich — 三要素细化 + 占位提案

对用户初选的候选（见 3 的批量挑选）逐个补全三要素：

| 要素 | 来源 | 缺失时 |
|---|---|---|
| **time** | 邻接事件时刻插位（'yyyy-MM-dd HH:mm:ss' 必填） | 邻接事件供插位候选 |
| **location** | 只推既有 Location：①文本地名匹配 ②char 历史足迹 ③at 边 | 图上无 → **Location 占位提案**（名称+一句话定位，status=0） |
| **char**（involved+role） | 只推既有 Character：同 Location 历史参与者→at 边居民→同日活动者 | 图上无（新配角）→ **Character 占位提案**（姓名+一句话人设，status=0） |

占位提案一并进建议 JSON（cypher 见模板）——**占位只建裸节点**（name/description/
status=0）；外貌链（AppearanceStyle→…）不在创建域，不建。

## 3. ask — 逐事件敲定（一次一问）

**第一题永远是候选批整体拍板**：摆出评分对比表（模式/一句话核心/四维评分/推荐），
用户挑选进入细化的候选（可改可弃）。此后对每条入选候选按序过：

| # | 维度 | 推荐答案来源 |
|---|---|---|
| 1 | 弧线贡献（**删除测试**：删了弧线塌吗） | 图上角色事件序列 / 因果链 + 时间窗邻接事件 |
| 2 | title + 一句话概述 + type（行动/交流/转折/状态变化） | 候选字段 |
| 3 | **time 锚点** | 时间窗邻接查询 |
| 4 | **occurs_at**（含占位提案确认） | 只读查图 / 占位 |
| 5 | **involved + role**（逐人敲定枚举值：当事人/目击者/受害者/施害者/参与者；含占位确认） | 只读查图 / 占位 |
| 6 | description 要点（钉子细节 1-3 句） | 口述 |
| 7 | ending_kind（**仅结局事件才问**，BE/TE/HE/NE） | — |
| 8 | condition（**仅分支相关才问**） | Choice 查询 |
| 9 | 因果（**仅用户明说才建** leads_to） | 时间窗因果候选 |
| 10 | **去重冲突终检**（时间/地点/参与人重叠对照：合并/改时间/放弃） | 只读查图 |

**Info 提案（可选，≤2/次）**：锚点关系查询或深读中明显缺内心戏/静态注记（角色对
某事的隐认知、伏笔注记、背景事实）时，提议 1~2 个 Info（`link` 挂锚点
Event/Character）——并入候选批一起询问，不单独立题。

**交互纪律**：

- 一次只问一个问题；每问开头回显「第 N 题 / 共约 M 题」。
- 每问必附推荐答案且可归因（理由标签 + 数据依据，不许「我觉得」）；「放弃」永远
  在选项里（放弃候选留痕，防重复起草）。
- **第一题是候选批整体拍板**（多方案评分对比表，不是逐个问）——先发散后收敛。
- 回答模糊 → 标「未解决依赖」继续，矛盾时回溯重问。
- 共识判据（事件级）：一段话可概述该事件（贡献/时间/地点/人物/因果）且连续三问
  无新矛盾。
- 收尾复述：每约 5 个决定复述一次；commit 前最终复述。
- 语言禁忌：不一次性抛问卷、不替用户写大段正文、始终用「你」。

## 4. commit — 组装建议 JSON 落盘

全部候选有处置（敲定/放弃，放弃留痕）后：

1. **推导轮次 N**：`$ROUND`（共享计数器，全量取 max+1；勿手写文件名扫描——
   字符串排序取最新会在日期翻篇时跳号）。
2. **主题** = char 名（+ base event 短题）。
3. **组装数组**（顺序：先占位实体后事件——节点先于边）：
   - 占位实体项：`{check:'I1_placeholder_entity', priority:'medium', reason, content, cypher, source:'event-ideator'}`——每个新 Character/Location 一项；
   - 事件项：`{check:'I2_new_event', priority: 结局/转折 high 否则 medium, reason, content, cypher, source:'event-ideator'}`——每事件一项，cypher 内 id 先解析既有实体、占位实体引用占位 id。
   - Info 项：`{check:'I3_new_info', priority:'low', reason, content, cypher, source:'event-ideator'}`——每个 Info 一项。
   - id 用 `$SF_GEN -n 1 -q` 逐节点生成。
4. **Write 落盘** `${OUTPUT_DIR}/${DATE}_round<N>_<主题>_ideator_建议.json`（顶层数组，UTF-8）。
5. **汇报**：文件路径 + 条数与 priority 分布 + 放弃清单 + 占位清单 + 审批入口
   话术（dashboard `/events`「📥 补全建议」逐条审阅写回）。

## cypher 模板（照抄改值）

```
// 占位 Location（裸节点）
CREATE (l:Location {id:'<snowflake>'}) SET l.name='<名称>', l.description='<一句话定位>', l.status=0;
// 占位 Character（裸节点，外貌链不在创建域）
CREATE (c:Character {id:'<snowflake>'}) SET c.name='<姓名>', c.description='<一句话人设>', c.status=0;
// 新事件（occurs_at/involved 引用既有或占位 id）
CREATE (e:Event {id:'<snowflake>'}) SET e.title='<title>', e.time='<yyyy-MM-dd HH:mm:ss>', e.type='<type>', e.description='<desc>';
MATCH (e:Event {id:'<event_id>'}), (l:Location {id:'<loc_id>'}) MERGE (e)-[r:occurs_at]->(l) ON CREATE SET r.sync=false;
MATCH (c:Character {id:'<char_id>'}), (e:Event {id:'<event_id>'}) MERGE (c)-[r:involved]->(e) ON CREATE SET r.role='<role>', r.sync=false;
// 仅用户明说因果时（方向 = 因 → 果）：
MATCH (a:Event {id:'<既有事件id>'}), (e:Event {id:'<event_id>'}) MERGE (a)-[r:leads_to]->(e);
// Info（限产 ≤2，link 挂锚点——锚点可为 Event 或 Character）
CREATE (i:Info {id:'<snowflake>'}) SET i.title='<标题>', i.content='<内容>';
MATCH (a {id:'<anchor_id>'}), (i:Info {id:'<info_id>'}) MERGE (a)-[r:link]->(i);
```

- 多语句 `;`+换行分隔，逐句以 `;` 结尾；**先建节点（含占位）再挂边**。
- involved 每人一条 MERGE；occurs_at 可多条；ending_kind/condition 仅敲定时并入首句 SET。
- 内联值单引号转义；不用 `$param`；不加时序边（时序由 `Event.time` 字符串序承载）。

## 铁律

1. **全程零写库**。落盘的是建议 JSON（文件），不是图。
2. **创建域 = 叙事基础**：Event + involved/occurs_at/leads_to 边 + Character/Location
   **占位** + Info（限产，见 §3）。不建 Choice/Spot/Scene/SubEvent/CostumeStyle/
   IllusDesign（演出域全归 event-stager），不改既有节点属性。
3. **占位只建裸节点**：name/description/status=0，不建外貌链、不建空间链。
4. **稀疏纪律**：单次至多 3 个 Event + 2 个 Info（Info 仅明显缺内心戏/静态注记时）；
   超限候选留「下次可敲定」。
5. **一题一答 + 每问必附可归因推荐**；候选批整体拍板是第一题（多方案对比，不逐个问）。
6. **facts 不问用户**：邻接事件、名录、option 序号现查；只有取舍问用户。
7. **title/description 不带时间**：时间唯一承载是 `Event.time`。
8. **防重**：已提案未审批不重复起草；commit 前必过去重终检。
9. **cypher 只含交付目标本身**，禁止夹带校验节点；执行后校验由用户回报触发只读回查。
10. **产出纪律**：写回后的 Event 其 Character/Location 必在图上（既有或本轮占位）——
    靠占位机制兜底，不留悬空事件。

## 参考文档

- [叙事基础.md Schema](../../../00_init/Schema/叙事基础.md)
- 方法论溯源：工作区根《event-ideator与event-stager功能定稿方案.md》§2/§8.1
