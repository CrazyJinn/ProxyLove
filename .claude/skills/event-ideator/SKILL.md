---
name: event-ideator
description: |
  新事件与故事线的需求提出层（叙事生产链第一环）：从人物设定/既定事件/故事线锚点出发启发新 Event 候选，与用户多轮交互（一次一问、每问附可归因推荐答案）敲定后产建议 JSON 落盘 02_剧情数据/，人工经 dashboard 审阅写回。零图写入、纯文件产物。
  六种启发模式按 char/base/arc 入参组合触发（动机链补桥/人物质感/间隙填充/后果链/因果回溯/故事线填充，模式表见正文）；arc 单独给 = 建线/对账支线。产物含 Event + involved/occurs_at 边 + Character/Location 占位 + 限产 Hook + StoryArc 与 comprises 边。
  不做拆解、机位、着装等任何演出域决策。稀疏纪律：单次 ≤3 Event + 2 Hook + 2 故事线。
  在用户说「想事件」「启发事件」「敲定事件」「新增事件」「建故事线」「故事线对账」或要从零产出新叙事事件时使用。
argument-hint: <char 名或 id | base event id或title | arc 故事线 id或title>（事件启发 char/base 至少一个；arc 单独给走故事线支线）
arguments:
  - char_base_arc
allowed-tools: Read, Bash, Write
---

# 新事件启发与敲定（event-ideator）

**从人物设定出发，生成并敲定值得发生的粗粒度新 Event**（需求提出层——创作判断在本层发生，创建权就在本层）。**创建域**：Event + involved/occurs_at（/leads_to 仅用户明说因果时）挂边 + Character/Location 占位 + 限产 Hook（establishes 挂成立源）+ StoryArc 与 comprises 边（I5 对账更新 description 是唯一改既有节点属性的例外）。不建 Choice/Spot/Scene/SubEvent/CostumeStyle/IllusDesign（演出域全归 event-stager）；Lore 不经本通道（固有设定是构图期人工拍板）。

> **通道契约（全程唯一表述，各步不再重复）**：
> - **零图写入**——交互期间仅查询；写库由人工在 dashboard（建议弹窗「采纳」或 Cypher 控制台）执行。
> - **建议 JSON**：顶层数组，逐项 `{check, priority, reason, content, cypher}` + `source:'event-ideator'`（check 见 §4）；落盘 `02_剧情数据/<日期>_round<N>_<主题>_ideator_建议.json`（必须 `_建议.json` 结尾——dashboard 弹窗按此 glob 拾取最新 3 个文件，落盘即提交）；轮次 N 由 `$ROUND` 推导（共享计数器全量取 max+1，勿手写文件名扫描——排序取最新会在日期翻篇时跳号）。
> - **cypher 语句纪律**：可多语句（`;`+换行分隔，先节点后边），每条语句自包含——边 pattern 两端点在本语句内 MATCH/CREATE 绑定（变量不跨语句延续，MERGE 端点未先绑定会整 pattern 重建出重复节点）；禁止夹带自造的校验节点（必然孤儿）；落盘后 `$SUGGEST_LINT` 全 PASS 才算提交。
> - **产出纪律**：每个写回的 Event，其 involved Character 与 occurs_at Location **必已在图上**（既有的或本轮占位的）——缺实体一律占位兜底，不留悬空挂边；每个写回的 StoryArc，其 comprises 成员 Event 必已在图上且 id 为 0 步现查快照——MATCH 落空 = 静默丢边，成员清单必须在 reason 中逐个列 id+title 供人工核验。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
SF_GEN="python ${CLAUDE_SKILL_DIR}/../../scripts/snowflake_base62.py"
ROUND="python ${CLAUDE_SKILL_DIR}/../../scripts/suggest_round.py"     # 轮次推导（共享计数器）
NBHD="python ${CLAUDE_SKILL_DIR}/scripts/neighborhood.py"             # 锚点关系查询（双锚连通性）
SUGGEST_LINT="python ${CLAUDE_SKILL_DIR}/../../scripts/suggest_lint.py"  # 建议语句级护栏
OUTPUT_DIR="02_剧情数据"
```

- Schema：[Schema/剧情/](../../../00_init/Schema/剧情/)（Event/involved/occurs_at/establishes/leads_to/Hook/Lore/StoryArc/comprises 的唯一事实来源）；Character/Location 占位节点定义见 [Schema/角色美术/](../../../00_init/Schema/角色美术/) / [Schema/场景美术/](../../../00_init/Schema/场景美术/)。
- 写 cypher 规则：[cypher_exec.py](../../scripts/cypher_exec.py) 顶部 docstring（内联值、MERGE 幂等、必须指定标签、加 LIMIT）。

## 流程总览（五步 + 故事线支线）

```
0. explore  解析入参（char + base + arc；事件启发需 char/base ≥1，arc 单独给 → 走 §5 故事线支线）
            → 锚点关系查询 + 只读查图上下文
1. ideate   六模式启发 → 候选批（多条差异化候选 + 评分对比表）
2. enrich   三要素细化：char / location / time 补全；缺失实体 → 占位提案
3. ask      一次一问逐事件敲定（候选评分表 → 用户挑选/修改/放弃）
4. commit   问尽 → 组装建议 JSON 落盘 → 报审批入口与下一步
```

支线 A 故事线构建（§5a）：读图取材 → 起草主旨/氛围 → 勾骨架成员（非全量入线）→ 敲 title → commit（I4）
支线 B 故事线对账（§5b）：读线+成员 → 比对 description vs 实际 → 失配产 I5；自动（触碰 comprises 的流程结尾）+ 手动（用户说「对账」）

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
     RETURN e ORDER BY e.time LIMIT 200;
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

**占位只建裸节点**（待建档缺口由内容缺失表达：Character 缺 has_appearance、Location 缺空间化即骨架）：Character 占位写 name/vibe（姓名+一句话氛围人设）、Location 占位写 name/description（名称+一句话定位），**均无 status**，外貌链/空间链不在创建域；着装补充说明不涉及（stager 域）。占位提案随建议 JSON 一并落盘（cypher 见模板）。

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

**Hook 提案（可选，≤2/次）**：锚点关系查询或深读中明显缺内心戏/静态注记（角色对某事的隐认知、伏笔注记、背景事实）时，提议 1~2 个 Hook——并入候选批一起询问，不单独立题。挂靠：**事实成立**挂 `Event ─establishes→ Hook`（必答「事实由哪个事件成立」，锚只能是 Event）；**读者侧揭示场合** `reveals` 由 event-stager 演出域拍板（ideator 不建 reveals）。title/content 为干净事实陈述（禁备忘/推导/编号引用，占位文字允许），knowledge_level 必填（1/2/3，下游 novelist freshness 半衰期档位）。

**交互纪律**：

- 一次只问一个问题；每问开头回显「第 N 题 / 共约 M 题」。
- 每问必附推荐答案且可归因（理由标签 + 数据依据，不许「我觉得」）；「放弃」永远在选项里。
- **facts 不问用户**（邻接事件、名录、option 序号现查），只问取舍。
- 回答模糊 → 标「未解决依赖」继续，矛盾时回溯重问。
- 共识判据（事件级）：一段话可概述该事件（贡献/时间/地点/人物/因果）且连续三问无新矛盾。
- 收尾复述：每约 5 个决定复述一次；commit 前最终复述。
- 不一次性抛问卷、不替用户写大段正文、始终用「你」。

**稀疏纪律**：单次至多 3 个 Event + 2 个 Hook + 2 条新建 StoryArc（I5 对账项不占额度——修正不是产出）；超限候选留「下次可敲定」——多次运行逐步丰满，留白即叙事。

## 4. commit — 组装建议 JSON 落盘

全部候选有处置（敲定/放弃，放弃留痕）后：

1. **主题** = char 名（+ base event 短题）；故事线支线时主题 = arc title。
2. **组装数组**（顺序：先占位实体后事件——节点先于边）：
   - 占位实体项：`{check:'I1_placeholder_entity', priority:'medium', reason, content, cypher}`——每个新 Character/Location 一项；
   - 事件项：`{check:'I2_new_event', priority: 结局/转折 high 否则 medium, reason, content, cypher}`——每事件一项，cypher 内 id 先解析既有实体、占位实体引用占位 id；
   - Hook 项：`{check:'I3_new_info', priority:'low', reason, content, cypher}`——每个 Hook 一项；
   - 故事线项：`{check:'I4_new_story_arc', priority:'medium', reason, content, cypher}`——建线一项（CREATE StoryArc + 逐成员 MERGE comprises；reason 必须逐成员列「event id + title（0 步现查快照）」）；既有线扩线挂成员复用同 check、reason 注明「扩线」、cypher 省略 CREATE 句；
   - 对账项：`{check:'I5_story_arc_update', priority:'low', reason, content, cypher}`——对账失配的线一线一项（content = 重写后 description 全文；cypher = MATCH SET）；
   - arc→new 敲定的事件：其 I2 项 cypher **末尾追加挂线语句**（见模板）——不为挂边单独立项；
   - id 用 `$SF_GEN -n 1 -q` 逐节点生成。
3. **Write 落盘** `${OUTPUT_DIR}/${DATE}_round<N>_<主题>_ideator_建议.json`（顶层数组，UTF-8）。
4. **lint（提交门槛）**：`$SUGGEST_LINT <文件路径>`——exit 0 = 全 PASS；任何 FAIL 按输出提示就地改写 cypher、覆盖重写文件、重跑至全 PASS（dashboard 执行侧有同规格兜底，FAIL 会在采纳时被 400 拒绝）。
5. **汇报**：文件路径 + 条数与 priority 分布 + lint 全 PASS 确认 + 放弃清单 + 占位清单 + 审批入口话术（dashboard `/events`「📥 补全建议」逐条审阅写回）。

## 5. 故事线支线 —— 构建（I4）与对账（I5）

### 5a. 构建（用户说「建故事线」「拉一条线」；入参：主题口述，arc 可空）

1. **读图取材**（0 步第 6 项查询）：候选成员池 = 主题关键词扫 Event（title/description CONTAINS）+ 相关 Character 的 involved 事件 + 时间窗聚类；同时查 StoryArc 全名录——同主题线已存在 → 建议「扩线/对账」而非新建。
2. **起草 description（写作思路层，不是事件复述）**：两段式——**主旨**（一两句：这条线想表达什么）+ **氛围**（一段：质感与调性），「主旨：」「氛围：」引导、段间换行。不复述情节结构（时序由成员 Event.time 承载）；计划中但未建图的走向可写，须与用户确认；段内不写时间戳。
3. **勾骨架成员**（一次一问，交互纪律沿用 §3；**非全量入线**——事件不进线≠不重要，只圈承载主旨的骨架事件）：摆「成员事件时间轴 + 主旨草案」对照表，逐事件问「它承载主旨的哪个面向？」（推荐答案来自 1 的取材；可勾可弃可补查）。
4. **敲定 title**（≤10 字弧线名，如「陆择的救赎线」）。
5. **主旨覆盖自检 + commit**：勾定后若主旨某面向零成员——提醒用户（改 description 或留注「收束待补」），随后走 §4 同款落盘/lint/汇报；I4 一项，主题 = arc title。

### 5b. 对账（description vs 实际成员）

**触发**：自动（本次产出涉及 comprises 挂边——I4 建线/扩线、或 arc→new 的 I2 事件挂线——commit 前对每条被触碰的 StoryArc 跑一次）/ 手动（用户说「对账」「检查故事线」，入参 arc id/title（单线）或 event id（反查所属线，逐线对账）；无入参时列名录让用户选）。

**步骤**：① 重读该线 description + 当前成员全集（含本次即将新增的）；② 判断两类失配：新成员改变主旨表达（新面向进线 / 原有面向该收束了）、description 写了但成员里没有的事（描述预言了未发生/已删除的事）；③ 失配 → 产 I5（content = 重写后的 description **全文**，一线一项，随本次建议 JSON 落盘）；不失配 → 不产 I5，汇报注明「故事线『<title>』核对无变化」。

**边界**：对账只产 I5 描述更新项与 I4 扩线挂边；**摘成员边（DELETE 关系）不进建议 JSON**——删除类操作由用户在 dashboard Cypher 控制台人工执行，对账汇报里只提示「建议摘除：<event title>」。

## cypher 模板（照抄改值）

// ⚠ 字段名以 Schema 为准（00_init/Schema/剧情/ 对应节点文件）：逐字段对照，表外字段一律不写；title/description 不带时间（时间唯一承载是 Event.time，含 StoryArc.description 只写叙事次序）。

```
// 占位 Character（裸节点：name/vibe，无 status；外貌链不在创建域）
CREATE (c:Character {id:'<snowflake>'}) SET c.name='<姓名>', c.vibe='<一句话氛围人设>';
// 占位 Location（裸节点：name/description，无 status；空间链不在创建域）
CREATE (l:Location {id:'<snowflake>'}) SET l.name='<名称>', l.description='<一句话定位>';
// 新事件（occurs_at/involved 引用既有或占位 id）
CREATE (e:Event {id:'<snowflake>'}) SET e.title='<title>', e.time='<yyyy-MM-dd HH:mm:ss>', e.type='<type>', e.description='<desc>';
MATCH (e:Event {id:'<event_id>'}), (l:Location {id:'<loc_id>'}) MERGE (e)-[r:occurs_at]->(l) ON CREATE SET r.sync=false;
MATCH (c:Character {id:'<char_id>'}), (e:Event {id:'<event_id>'}) MERGE (c)-[r:involved]->(e) ON CREATE SET r.sync=false;
// 仅用户明说因果时（方向 = 因 → 果）：
MATCH (a:Event {id:'<既有事件id>'}), (e:Event {id:'<event_id>'}) MERGE (a)-[r:leads_to]->(e) ON CREATE SET r.sync=false;
// Hook（限产 ≤2，Event ─establishes→ Hook 成立源——锚点只能是 Event；揭示场合归 event-stager 拍板）
CREATE (f:Hook {id:'<snowflake>'}) SET f.title='<标题>', f.content='<内容>', f.knowledge_level=<1|2|3>;
MATCH (a:Event {id:'<anchor_id>'}), (f:Hook {id:'<fact_id>'}) MERGE (a)-[r:establishes]->(f) ON CREATE SET r.sync=false;
// 故事线（I4 标准形：建线 + 逐成员挂边；成员 id 全部 0 步现查——MATCH 落空=静默丢边）
CREATE (a:StoryArc {id:'<snowflake>'}) SET a.title='<标题>', a.description='主旨：…\n氛围：…';
MATCH (a:StoryArc {id:'<arc_id>'}), (e:Event {id:'<event_id>'}) MERGE (a)-[r:comprises]->(e) ON CREATE SET r.sync=false;
// I4 扩线形 = 仅上句 MERGE（无 CREATE）；每成员一条 MERGE。
// 故事线对账更新（I5：全 skill 唯一改既有节点属性的例外，仅 description 一字段）
MATCH (a:StoryArc {id:'<arc_id>'}) SET a.description='<重写后的主旨/氛围全文>';
// arc→new 新事件挂线（追加在该事件 I2 项 cypher 末尾）
MATCH (a:StoryArc {id:'<arc_id>'}), (e:Event {id:'<event_id>'}) MERGE (a)-[r:comprises]->(e) ON CREATE SET r.sync=false;
```

- 多语句 `;`+换行分隔，逐句以 `;` 结尾，先建节点（含占位）再挂边；MERGE 幂等；involved 每人一条、occurs_at 可多条；ending_kind/condition 仅敲定时并入事件首句 SET。
- **StoryArc.description 值内换行一律写 `\n` 转义序列**（禁物理换行——多语句以 `;`+换行分隔，值内裸换行会破坏该约定与 lint 判定）。
- 内联值单引号转义；不用 `$param`；不加时序边（时序由 Event.time 字符串序承载）。

## 参考文档

- [Schema/剧情/](../../../00_init/Schema/剧情/)（Event/Hook/Lore/StoryArc/comprises）
- Character/Location 节点定义见 [Schema/角色美术/Character.md](../../../00_init/Schema/角色美术/Character.md) / [Schema/场景美术/Location.md](../../../00_init/Schema/场景美术/Location.md)
