---
name: event-ideator
description: |
  新事件与故事线的需求提出层（叙事生产链第一环）：从人物设定/既定事件/故事线锚点出发启发新 Event 候选，与用户多轮交互（一次一问、每问附可归因推荐答案）迭代到共识，敲定后产**事件共识文档** `<日期>_<主题>_共识.md` 落盘 02_剧情数据/——默认交 event-stager 消化拆解演出（共识 → 定稿 → suggest-consumer → 用户确认后执行写回）；纯 I 域轮次（仅故事线构建/对账，或用户明示不拆演出）直接交 suggest-consumer。零图写入、不产 cypher、不跑 lint——Schema 纪律不在本层。
  六种启发模式按 char/base/arc 入参组合触发（动机链补桥/人物质感/间隙填充/后果链/因果回溯/故事线填充，模式表见正文）；arc 单独给 = 建线/对账支线；**盘点范围**单独给 = 存量 Info/认知盘点支线（§6，逐事件扫雷补条目，产 `_Info盘点<范围>_共识.md` 纯 I 通路直消 suggest-consumer）。共识承载 Event + involved/occurs_at 关联 + Character/Location 占位意图 + Info 与 establishes 意图 + 认知条目（Cognition）意图 + StoryArc 与 comprises 意图。
  不做拆解、机位、着装等任何演出域决策。无数量硬门控——批量由创作判断决定，留白即叙事。
  在用户说「想事件」「启发事件」「敲定事件」「新增事件」「建故事线」「故事线对账」「盘点」「重盘」或要从零产出新叙事事件时使用。
argument-hint: <char 名或 id | base event id或title | arc 故事线 id或title | 盘点范围（章/时间窗/全量/游离段）>（事件启发 char/base 至少一个；arc 单独给走故事线支线；盘点范围单独给走 §6 盘点支线）
arguments:
  - char_base_arc
allowed-tools: Read, Bash, Write
---

# 新事件启发与敲定（event-ideator）

**从人物设定出发，生成并敲定值得发生的粗粒度新 Event**（需求提出层——创作判断在本层发生，创建权就在本层）。**创建域**：Event + involved/occurs_at（/leads_to 仅用户明说因果时）挂边 + Character/Location 占位 + Info 与 establishes 边（事件的信息要素，成立轴）+ 认知条目（Cognition：知情者/偏差者+forms 锚）+ StoryArc 与 comprises 边（I5 对账更新 description 是唯一改既有节点属性的例外）。不建 Choice/Spot/Scene/SubEvent/CostumeStyle/IllusDesign（演出域全归 event-stager）；Lore 不经本通道（固有设定是构图期人工拍板）。

> **通道契约（全程唯一表述，各步不再重复）**：
> - **零图写入**——交互期间仅查询；写库由 suggest-consumer 在用户明确同意后执行，本层不碰图写。
> - **事件共识文档（人读优先）**：落盘 `02_剧情数据/<日期>_<主题>_共识.md`（`_共识.md` 结尾——**不触发** dashboard 建议弹窗的 `*_建议.json` glob；文件名不带轮次，同日同主题重跑**覆盖**，commit 汇报注明）。共识文档是 **event-stager 的输入与 I 域条目的权威快照**——stager 定稿逐条照抄、不重写，所以指称必须精确。文档是**给人读的 md**——条目组织与标签行只是惯例结构，人阅读性优先于机器可解析性；**不产 cypher、不跑 lint、不生成 id**——Schema 严检、id 生成、cypher 组装与执行全归下游。
> - **去向双通路**：含 I2 事件的共识默认交 **event-stager** 消化拆解演出（共识 → 定稿 → suggest-consumer → 确认执行写回）；**纯 I 通路**——本轮条目仅 I4/I5（故事线构建/对账）或用户明示「不拆演出」时，共识直接交 **suggest-consumer** 消费。
> - **引用纪律**：既有实体（Character/Location/Event/StoryArc/Choice）必须以**现查 id** 内联条目标签行（名称仅作注释，重名/改名会静默错挂——stager 的 preflight 会验图，错拼 id 直接打回本层）；新实体（占位/Info/新线）只写名称 + 一句话设定，由 suggest-consumer 物化为节点。condition 只写语义（如「三选一选了苏晓禾」），序号表达式由 consumer 现查 Choices 换算。
> - **产出纪律**：每个事件条目，其 involved Character 与 occurs_at Location 的**语义指称**必须明确——既有的写 id，缺的写占位意图 `[占位：名称]`（stager 据此判定该实体演出资源为零、链路全新占位）——不留悬空；故事线条目必须逐成员列「event id + title（0 步现查快照）」供 consumer 与人工核验。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
NBHD="python ${CLAUDE_SKILL_DIR}/scripts/neighborhood.py"             # 锚点关系查询（双锚连通性）
OUTPUT_DIR="02_剧情数据"
```

- Schema：[Schema/剧情/](../../../00_init/Schema/剧情/)（Event/involved/occurs_at/leads_to/Info/establishes/Cognition/Lore/StoryArc/comprises 的唯一事实来源）；Character/Location 占位节点定义见 [Schema/角色美术/](../../../00_init/Schema/角色美术/) / [Schema/场景美术/](../../../00_init/Schema/场景美术/)。本层**只需语义正确**（字段是什么、写什么内容），字段级撰写契约（零时间措辞等）由 suggest-consumer 消费时强制。
- 写 cypher 规则：[cypher_exec.py](../../scripts/cypher_exec.py) 顶部 docstring（内联值、MERGE 幂等、必须指定标签、加 LIMIT）。

## 流程总览（五步 + 故事线支线 + 盘点支线）

```
0. explore  解析入参（char + base + arc + 盘点范围；事件启发需 char/base ≥1，arc 单独给 → 走 §5 故事线支线，盘点范围单独给 → 走 §6 盘点支线）
            → 锚点关系查询 + 只读查图上下文
1. ideate   六模式启发 → 候选批（多条差异化候选 + 评分对比表）
2. enrich   三要素细化：char / location / start_time 补全；缺失实体 → 占位提案
3. ask      一次一问逐事件敲定（候选评分表 → 用户挑选/修改/放弃）→ 共识成立确认
4. commit   组装事件共识文档落盘 → 报下一步（默认 event-stager 消化；纯 I 轮次 suggest-consumer 直消）
```

支线 A 故事线构建（§5a）：读图取材 → 起草主旨/氛围 → 勾骨架成员（非全量入线）→ 敲 title → commit（I4）
支线 B 故事线对账（§5b）：读线+成员 → 比对 description vs 实际 → 失配产 I5；自动（触碰 comprises 的流程结尾）+ 手动（用户说「对账」）
支线 C 存量盘点（§6）：圈范围 → 查基线 → 事实登记表 → 逐事件过堂 → 同义对照 → 汇总拍板落盘（纯 I 通路）→ 终验

---

## 0. explore — 解析入参 + 拉上下文

- 入参（事件启发：char 与 base 至少给一个，可同给）：`char`（人名或 id——人物锚点，多个角色顿号分隔）；`base event`（id 或 title——既定目标事件；给 char 时启用动机链/间隙模式，只给 base 时启用后果链/回溯模式）；`arc`（故事线 id 或 title——单独给 = 建线/对账支线〔§5〕，与 char/base 同给 = `arc→new` 填充模式）。
- **推荐答案必须有图数据依据**（人物设定/邻域表/因果链，事件要服务弧线，不凭空造戏）。
- 只读查图（全部带 LIMIT）：
  1. **锚点关系查询**（见下，启发的主依据）；
  2. **char 深读**（锚含 char 时）：人物设定（vibe/relation）+ LanguageStyle——人物弧线的第一依据（其历史事件已在邻域表中）；
  3. Character / Location 名录——名称→id 解析表（**id 内联进 cypher，不在 cypher 里做名称匹配**：重名/改名会静默错挂）；同时用于识别「提及但未建档」→ 占位候选；
  4. 涉分支时 Choice option label 序号表（condition 序号 = option 按 label 字典序 1 基编号，现查不靠记忆）；
  5. 扫最近几份 `*_建议.json`——已提案未审批的事件标「待审」，不重复起草；
  6. **故事线上下文**（arc 入参、arc→new 或对账触发时；直查 cypher，不经 `$NBHD`——其边白名单不含 comprises，故事线中继不会污染双锚连通性判断，这是期望行为）：

     ```cypher
     // a. 读线（id 精确或 title 关键词，二选一改写）
     MATCH (a:StoryArc) WHERE a.id='<arc_id>' OR a.title CONTAINS '<关键词>'
     RETURN a LIMIT 10;
     // b. 全名录（建线前防重复建线）
     MATCH (a:StoryArc) RETURN a LIMIT 100;
     // c. 成员按时间序（读缺口的主依据）
     MATCH (a:StoryArc {id:'<arc_id>'})-[:comprises]->(e:Event)
     RETURN e ORDER BY e.start_time LIMIT 200;
     // d. 反查所属线（对账传 event id 时）
     MATCH (a:StoryArc)-[:comprises]->(e:Event {id:'<event_id>'})
     RETURN a LIMIT 10;
     ```

     **读缺口**（arc→new 主依据）：成员时间轴上相邻间隔 > 1 天的空洞 × description 主旨对照——主旨的哪个面向写了却缺事件支撑（含收束未至），缺环即候选落点。

**锚点关系查询（char 与 base 之间的关系——图上实捞，不是模型想象）**：
`$NBHD --char <char_id> --base <event_id>` 双锚查**两锚在叙事基础域（Character/Event/Location）的连通性**——直接关系 + 间接路径（≤4 跳，边限 involved/occurs_at/at/relation/leads_to，按真实方向画箭头）+ 不连通判定；不滚邻域雪球（不把锚点周围的所有 char/location 全捞出来）。单锚退化为一跳清单：`--char` → 近期 10 事件 + at 常驻地 + relation 关系人；`--base` → 参与人 + 地点 + leads_to 因果邻居。锚点查无时脚本直接报错退出（先做名称→id 解析），不静默降级不猜。

**读图口径**（看查询结果直判，启发从数据长出来，不凭空造）：

- **连通性即空隙**：双锚不连通或仅弱连通（≥3 跳）——新事件就是桥，`char→new→base` 的落点；已直接 involved 则无需补桥，启发转向质感/间隙模式；
- **中介即桥形态**：间接路径揭示的中介（共同地点、共同参与人、已有因果链的上游事件）提示新事件怎么挂——同地点共场、引入中介角色、或接因果上游；
- **时间间隙**（单锚 char 事件列表）：相邻间隔 > 1 天的空洞——喂 `base→new→base`；
- **锚点稀薄**：单锚清单只有 1~2 行 = 该锚点故事稀薄，本身就是最大的信号。

**查询纪律**：只查锚点之间的关系（双锚连通/单锚一跳），不做全量邻域扫描——周围实体全捞会稀释信号。深读优于广扫：查询结果中出现的事件/角色，其 description/relation 细节按候选需要逐个深读。

## 1. ideate — 六模式启发（候选批，不是逐个问）

按入参组合选定模式（可组合），每模式产 2~3 条候选，合成本轮候选批（合计 ≤6 条）。**候选从 0 步锚点关系中长出来**（不连通/弱连通→补桥，中介→桥形态，时间间隙→间隙填充），每条候选标注来源依据：

| 模式 | 触发条件 | 回答的创作问题 | 产出类型 |
|---|---|---|---|
| `char → new → base` | char + base 给定 | 角色经历了什么才抵达既定事件？ | 动机链事件（因果补桥） |
| `char → new` | char 给定 | 这个人平时会干什么？ | 人物质感事件（血肉填充） |
| `base → new → base` | base 给定且有时间邻接事件 | 两个既定事件之间发生了什么（可有关可无关）？ | 间隙填充事件 |
| `base → new` | base 给定 | 这个既定事件之后引发了什么连锁反应？ | 后果链事件（leads_to 正向延伸） |
| `new → base` | base 给定 | 什么导致了这个既定事件（不限单一角色）？ | 无锚因果回溯（补 leads_to 上游） |
| `arc → new` | arc 给定（可与 char/base 组合） | 这条故事线的主旨还缺哪些事件支撑？ | 故事线填充事件（按主旨表达缺口补环，写回时附 comprises 挂边） |

**每条候选必带结构化字段**（对比表列）：一句话核心（这个事件是什么）/ 情绪价值（给玩家什么感受）/ 与锚的关系（因果铺垫、后果延伸、反差、无关；arc 模式时填补故事线哪一段）/ 评分（四维 1-5 + 综合，评分依据必须可归因）：

- **人设契合**：与相关角色（char 锚 / base 事件 involved）的设定/创伤/目标一致性（对照 0 步深读）；
- **查图去重**：与既有事件的重复度（时间/地点/参与人重叠 → 低分）；
- **戏剧价值**：对情绪曲线的贡献（铺垫→触发→释放→余韵，缺环处加分）；
- **生产成本**：需新建多少占位（新 Location/新 Character 越多分越低）。

**依据分离标注**：候选理由中图上实查的（邻接事件、既有实体）与模型常识推断的（人物心理推演）分开表述，防幻觉混入图数据。

## 2. enrich — 三要素细化 + 占位提案

对用户初选的候选（见 §3 首题）逐个补全三要素：

| 要素 | 来源 | 缺失时 |
|---|---|---|
| **time** | 邻接事件时刻插位（'yyyy-MM-dd HH:mm:ss' 必填） | 邻接事件供插位候选 |
| **location** | 只推既有 Location：①文本地名匹配 ②char 历史足迹 ③at 边 | 图上无 → **Location 占位提案** |
| **char**（involved） | 只推既有 Character：同 Location 历史参与者→at 边居民→同日活动者 | 图上无（新配角）→ **Character 占位提案** |

**占位只写占位意图**（待建档缺口由内容缺失表达：Character 缺 has_appearance、Location 缺空间化即骨架）：Character 占位写 name/vibe（姓名+一句话氛围人设）、Location 占位写 name/description（名称+一句话定位），**均无 status**，外貌链/空间链不在创建域；着装补充说明不涉及（stager 域）。占位意图随共识文档一并落盘（格式见共识模板），节点物化由 suggest-consumer 完成。

## 3. ask — 逐事件敲定（一次一问）

**第一题永远是候选批整体拍板**：摆出评分对比表（模式/一句话核心/四维评分/推荐），用户挑选进入细化的候选（可改可弃——放弃留痕，防重复起草）。此后对每条入选候选按序过：

| # | 维度 | 推荐答案来源 |
|---|---|---|
| 1 | 弧线贡献（**删除测试**：删了弧线塌吗） | 图上角色事件序列 / 因果链 + 时间窗邻接事件 |
| 2 | title + 一句话概述 + type（行动/交流/转折/状态变化） | 候选字段 |
| 3 | **time 锚点** | 时间窗邻接查询 |
| 4 | **occurs_at**（含占位提案确认） | 只读查图 / 占位 |
| 5 | **involved**（逐人确认参与；含占位确认） | 只读查图 / 占位 |
| 6 | description 要点（钉子细节 1-3 句） | 口述 |
| 7 | ending_kind（**仅结局事件才问**，BE/TE/HE/NE） | — |
| 8 | condition（**仅分支相关才问**） | Choice 查询 |
| 9 | 因果（**仅用户明说才建** leads_to） | 时间窗因果候选 |
| 10 | **去重冲突终检**（时间/地点/参与人重叠对照：合并/改时间/放弃） | 只读查图 |

**Info 提案（新事件默认伴随）**：提案每个新 Event 时自问「**这个事件使什么事实成立（产生了什么信息要素）**」——有则附 Info 提案并入候选批（无认知增量则不提，不硬凑）；**从严口径**：只立有持续叙事意义的事实（身份/关系/资源/知情面的持久变化），过程性/过渡性事实（战绩起伏/单次冲突/方案文档/邀约悬置类）默认不立，宁漏勿滥；锚点关系查询/深读中发现的隐认知、伏笔注记、背景事实同通道，不单独立题。**分支纪律**：挂 condition 的分支事件不提 Info/不产认知条目——分支备线非既成事实，建了会经 forms 键跨支泄漏进小说取材。挂靠：**成立承载事件**挂 `Event ─establishes→ Info`（默认本事件；固有前史事实建前史事件承载，无 sub 不演出）。**知晓分布由认知条目显式承载**（`Character ─has_cognition→ Cognition ─about→ Info` + `Event ─forms→ Cognition`，契约见 [Schema/剧情/Cognition.md](../../../00_init/Schema/剧情/Cognition.md)）：提案 Info 时同产**全量**知情者/偏差者认知条目草案（type 四态；所信≠事实必写偏差 title；forms 默认锚成立事件）——封闭世界下漏建=角色被误判不知情；「参与即知情」已废止，involved 不推导知情。title/content 为干净事实陈述（禁备忘/推导/编号引用，占位文字允许），knowledge_level 必填（1/2/3，下游 freshness 半衰期档位，不影响认知集投放）。存量盘点（非新事件提案）走 §6 盘点支线；换述判例见 [references/Info盘点判例.md](references/Info盘点判例.md)。

**同义对照步（Info 查重主闸，提 I3 前必做；2026-11-20 裁定：语义判断在本层，consumer 只浅验证）**：先圈**对照池**（四源，全部图上结构/字符串查询，零语义成本）——① **同承载产出**：承载事件为图上既有时查其既有 `establishes→` Info，承载为新事件/同文档 I2 时对照同文档内挂同一承载事件的其他 I3 草案；② involved 角色认知集内 Info（`has_cognition→about`）；③ 候选事件时间窗 ±7 天内事件承载的 Info；④ 候选 title/content 中实体名（角色名/专名）`CONTAINS` 扫全量 Info title。**池上限 20 条**，①→④ 优先级装池，超限截断并在 reason 注明截断了哪些源。池内逐条三分类：**同一事实**（换述/近义）→不新建，改回补（补承载边+认知挂既有 Info）；**不同侧面**→可新建，reason 必注与相近条目的区分点；**拿不准**→列裁决点附推荐。升级口：池内疑似不确定或用户对裁决点追问时，允许对全量做一次 LLM 对照（reason 注明「全量复核」），常态不跑。

**交互纪律**：

- 一次只问一个问题；每问开头回显「第 N 题 / 共约 M 题」。
- 每问必附推荐答案且可归因（理由标签 + 数据依据，不许「我觉得」）；「放弃」永远在选项里。
- **facts 不问用户**（邻接事件、名录、option 序号现查），只问取舍。
- 回答模糊 → 标「未解决依赖」继续，矛盾时回溯重问。
- 共识判据（事件级）：一段话可概述该事件（贡献/时间/地点/人物/因果）且连续三问无新矛盾。
- **共识成立确认（commit 前最后一问，必问）**：全部候选处置完毕后逐项复述共识清单（事件/占位/Info/线），问「以上 N 项共识是否成立？」——推荐答案「成立」；用户明确答复成立 → 进 §4 落盘（含 I2 → 默认交 stager；纯 I4/I5 → 落盘后交 consumer）；答复回改 → 定位到具体条目重问。沉默或「差不多」不算成立，追问确认。
- 收尾复述：每约 5 个决定复述一次；commit 前最终复述。
- 不一次性抛问卷、不替用户写大段正文、始终用「你」。

**无数量硬门控**：共识不再卡「≤3 Event + 2 Info + 2 故事线」——批量由创作判断与留白原则决定（多次运行逐步丰满，留白即叙事）；超大共识的审阅负担由 suggest-consumer 在汇报中提示分批，不在本层拦截。

## 4. commit — 组装事件共识文档落盘

全部候选有处置（敲定/放弃，放弃留痕）后：

1. **主题** = char 名（+ base event 短题）；故事线支线时主题 = arc title。
2. **组装共识条目**（顺序：先占位实体后事件——节点先于边）：
   - 占位实体条目（类型 I1）：`[占位 Character]`/`[占位 Location]`——名称 + 一句话氛围人设/定位；
   - 事件条目（类型 I2）：title + type + start_time（跨时段事件补 end_time，点事件省略）+ occurs_at（既有 id 或占位指称）+ involved（逐人：id 或占位指称）+ condition 语义 + description 要点（钉子细节 1-3 句，自然语言）+ 因果（仅用户明说）+ ending_kind（仅结局事件）；
   - Info 条目（类型 I3）：title + content + knowledge_level + 成立承载事件（establishes，默认本事件；既有 id 或 `定稿I2「<title>」`，可多条）+ 全量认知条目（知情者/偏差者逐人：type/title(仅偏差)/forms 锚）——知晓分布由认知条目逐人显式承载，与承载事件的选择无关；分支事件（挂 condition）不出本类条目；
   - 故事线条目（类型 I4）：title + description 草案（主旨/氛围）+ 逐成员「event id + title」（建线/扩线注明）；
   - 对账条目（类型 I5）：线 id + 重写后的 description 全文草案；
   - arc→new 敲定的事件：条目内注明「挂线：<arc id>」——不为挂边单独立条。
   - 每条目附 reason（依据：图上实查 vs 常识推断，分离标注）。
3. **Write 落盘** `${OUTPUT_DIR}/${DATE}_<主题>_共识.md`（UTF-8，条目格式见下方共识模板；同日同主题重跑覆盖——汇报注明）。
4. **汇报**：共识路径 + 条目数与类型分布 + 放弃清单 + 占位清单 + 下一步话术**双分支**——默认「跑 event-stager 消化本共识（拆 SubEvent → 定稿 → suggest-consumer → 用户确认后执行写回）」；纯 I 轮次「跑 suggest-consumer 消费本共识（严检 Schema、组装建议 JSON → 用户确认后执行写回）」。

## 5. 故事线支线 —— 构建（I4）与对账（I5）

### 5a. 构建（用户说「建故事线」「拉一条线」；入参：主题口述，arc 可空）

1. **读图取材**（0 步第 6 项查询）：候选成员池 = 主题关键词扫 Event（title/description CONTAINS）+ 相关 Character 的 involved 事件 + 时间窗聚类；同时查 StoryArc 全名录——同主题线已存在 → 建议「扩线/对账」而非新建。
2. **起草 description（写作思路层，不是事件复述）**：两段式——**主旨**（一两句：这条线想表达什么）+ **氛围**（一段：质感与调性），「主旨：」「氛围：」引导、段间换行。不复述情节结构（时序由成员 Event.start_time 承载）；计划中但未建图的走向可写，须与用户确认；段内不写时间戳。
3. **勾骨架成员**（一次一问，交互纪律沿用 §3；**非全量入线**——事件不进线≠不重要，只圈承载主旨的骨架事件）：摆「成员事件时间轴 + 主旨草案」对照表，逐事件问「它承载主旨的哪个面向？」（推荐答案来自 1 的取材；可勾可弃可补查）。
4. **敲定 title**（≤10 字弧线名，如「陆择的救赎线」）。
5. **主旨覆盖自检 + commit**：勾定后若主旨某面向零成员——提醒用户（改 description 或留注「收束待补」），随后走 §4 同款共识落盘/汇报（故事线支线 = 纯 I 通路，落盘后交 suggest-consumer 直消）；I4 一条目，主题 = arc title。

### 5b. 对账（description vs 实际成员）

**触发**：自动（本次产出涉及 comprises 挂边——I4 建线/扩线、或 arc→new 的 I2 事件挂线——commit 前对每条被触碰的 StoryArc 跑一次）/ 手动（用户说「对账」「检查故事线」，入参 arc id/title（单线）或 event id（反查所属线，逐线对账）；无入参时列名录让用户选）。

**步骤**：① 重读该线 description + 当前成员全集（含本次即将新增的）；② 判断两类失配：新成员改变主旨表达（新面向进线 / 原有面向该收束了）、description 写了但成员里没有的事（描述预言了未发生/已删除的事）；③ 失配 → 产 I5（content = 重写后的 description **全文**，一线一条目，随本次共识落盘，纯 I 通路直消）；不失配 → 不产 I5，汇报注明「故事线『<title>』核对无变化」。

**边界**：对账只产 I5 描述更新项与 I4 扩线挂边；**摘成员边（DELETE 关系）不进建议 JSON**——删除类操作由用户在 dashboard Cypher 控制台人工执行，对账汇报里只提示「建议摘除：<event title>」。

## 6. 盘点支线 —— 存量 Info/认知补全（纯 I 通路）

**入口**：入参 `盘点范围`（章号 / 时间窗 / 全量 / 游离段）单独给出即走本支线（与 char/base 同给时仍走事件启发 §0~§4，本支线不混跑）。适用：全量盘点、按章批次盘点、主支确定后的分支段重盘、任意存量知情补全。模型契约见 [Schema/剧情/](../../../00_init/Schema/剧情/)；陷阱与判例见 [references/Info盘点判例.md](references/Info盘点判例.md)。

**七步**：

1. **圈定范围**：查事件全量明细 id/title/start_time/description/involved/occurs_at/**condition**——condition 决定分支处置，先查分布（`MATCH (e:Event) WHERE e.start_time >= '…' RETURN e.condition, count(*)`）；
2. **查基线**：既有 Info 与认知分布（establishes 汇总 + has_cognition/about/forms 明细）——**只记补条目**（新承载边/新知情者/态度转变改写），不重建；
3. **建事实登记表**（文档内表格：事实 → 承载事件集 → 已登记认知）——贯穿维护，防「同一事实跨 5+ 事件再现靠记忆必漏」；
4. **逐事件过堂**（start_time 升序）：每事件答「使什么事实成立（0~N 条）」→ 每条当场判认知分布（谁以什么态度知道、forms 锚哪个事件——**先问「他在此事件之前是否已知」**，更早形成的认知锚更早事件）；三分记录：**产出 / 零增量 / 从严不立**（留痕供重盘）；
5. **同义对照**：每条候选新 Info 走 §3 同义对照步（对照池四源、上限 20、三分类）——同一事实改回补，不新建；
6. **汇总**：新 Info（title 中性事实句/kl/establishes 源/认知分布）+ 补条目 + 裁决点清单（附推荐）→ 用户拍板 → 共识落盘 `${OUTPUT_DIR}/${DATE}_Info盘点<范围>_共识.md`（纯 I 通路直消 suggest-consumer）；
7. **终验**（落图后）：无孤 Info（全部 ≥1 establishes）、无残认知（forms≥1 且 about 齐）、**认知链零并存**（每对 (Character, Info) 经 Cognition 至多一条链）、近重复对扫描（范围内两两 title 对照，报告人工拍板；合并走 dashboard 人工执行——删除类不进建议 JSON）。

**执行口径（项目口径）**：

1. **穿越后主语**：2024-05-31 18:00（穿越）起身体行为获得的认知，主语一律记陆择；陈默原主灵魂状态图上不表达；
2. **远程知晓 forms 锚**＝内容可得的源头事件（发布/直播/告知事件），不锚下游行为事件；
3. **疑似知情者按叙事意图推断补建**，条目 reason 标注「推断」；
4. **分支事件不建**：挂 condition 的事件一律零增量；Choice 兑现事件（选项本体）同理；分支段重盘以**主支确定**为前提；
5. **从严口径（最高优先）**：只立有持续叙事意义的事实（身份/关系/资源/知情面的持久变化），过程性/过渡性事实默认不立，宁漏勿滥；拿不准列裁决点附「从严建议不立」。

**条目映射**（复用现有类型，不新增 I6）：新 Info/补承载边 = I3（承载事件写既有 id，多事件并列在条目内列全）；认知补建 = I3 认知块（知情者/偏差者逐人）；认知改写 = 认知块「改写型」标注（原主语→新主语/新 type/新 forms 锚——consumer R4 三形态照吃）。

## 共识模板（照抄改值）

// ⚠ 共识文档是给人读的自然语言 md：标签行只是惯例结构，可自由组织；语义完整即可，字段级撰写契约（零时间措辞、title 事实句等）由 suggest-consumer 对照 Schema 强制。既有实体一律 id 内联（stager preflight 据此验图），新实体只写名称+一句话；占位指称统一 `[占位：名称]` 形态（stager 据此判定演出资源为零）。

```markdown
# <主题> 共识

## [I1 占位 Location] 书店
- 定位：临街两层小书店，二楼有医学护理专区
- reason：<依据，图上实查/常识推断分离标注>

## [I2 事件] 苏晓禾陪陈默书店买护理教材
- time: 2024-06-23 18:00:00
- type: 交流
- occurs_at: [占位：书店]（上条）
- involved: 陈默(NvCkQmFPFq)、苏晓禾(NvCkQmFPFs)
- condition: 三选一选了苏晓禾
- description 要点: 苏晓禾拉着陈默直奔书店，护理专区翻遍入门教材，挑最厚的基础护理学加图解人体
- 挂线: RpPzkWr7Mw（苏晓禾线）
- reason: <依据>

## [I3 Info] / [I4 故事线] / [I5 对账] …同款结构
```

- 条目顺序：先占位实体后事件（节点先于边）；involved 每人一列、occurs_at 可多条；ending_kind/condition/因果仅敲定时注明。

## 参考文档

- [Schema/剧情/](../../../00_init/Schema/剧情/)（Event/Info/Lore/StoryArc/comprises）
- Character/Location 节点定义见 [Schema/角色美术/Character.md](../../../00_init/Schema/角色美术/Character.md) / [Schema/场景美术/Location.md](../../../00_init/Schema/场景美术/Location.md)
