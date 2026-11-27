---
name: suggest-consumer
description: |
  建议消费层——叙事事件链的 Schema 守门人：消费三类人读优先的自然语言文档（按语义解析）——**事件共识**（`*_共识.md`，纯 I 域条目）/ **事件定稿**（`*_定稿.md`，I+S 混合或纯 S 域）/ **小说对账补全**（`*_补全_草稿.md`，N 域）。逐条目对照 00_init/Schema/ 字段表契约严检（撰写契约、枚举、必填、时间格式、condition 序号换算、占位最小启动集、id 存在性、占位查重、文档内指称解析、各来源创作域红线），违例就地改写并留痕（before/after），生成 snowflake id、按模板组装建议 JSON（含 cypher，先节点后边、语句自包含、同文档指称绑定同轮生成 id），落盘同名 `_建议.json`，跑 suggest_lint 至全 PASS。I1 条目含 entity-refiner「细化：」块时一并物化（priority / 常驻地保留名占位 + at 边 / 基础固有 Info + has_info，source='entity-refiner'）。**执行确认门**：lint PASS 后必停一问，用户明确同意才直接执行写回（单事务 + 读回验证，不经 dashboard）；不同意则留 dashboard 建议弹窗人工备选通道。
  默认零图写入（未经明确同意绝不执行）、原则上零交互（执行确认是唯一必问；严检违例自动改写并汇报；语义两可才回头问用户）；无数量硬门控（不设上限校验，超大文档仅提示分批审阅）。
  在用户说「消费草稿」「组装建议」「严检定稿」「执行写回」或 ideator/stager/novelist 汇报指向本文档时使用。
argument-hint: <文档路径（02_剧情数据/*_共识.md | *_定稿.md | *_补全_草稿.md）>
arguments:
  - draft_path
allowed-tools: Read, Bash, Write
---

# 建议消费与 Schema 严检（suggest-consumer）

**输入文档是自然语言层（语义完整即可），本层是唯一的格式与契约强制点**——ideator/stager 不背 Schema 纪律，一切字段级契约（零时间措辞、title 事实句、枚举、最小启动集、语句形态）在消费时对照 Schema 文件强制执行。**默认零图写入**：产建议 JSON 落盘；lint PASS 后停在**执行确认门**（§5）——用户明确同意才执行写回，不同意则留 dashboard 人工通道。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
SF_GEN="python ${CLAUDE_SKILL_DIR}/../../scripts/snowflake_base62.py"      # id 生成
SUGGEST_LINT="python ${CLAUDE_SKILL_DIR}/../../scripts/suggest_lint.py"   # 建议语句级护栏
OUTPUT_DIR="02_剧情数据"
```

- Schema（严检的唯一依据，**逐条目按涉及节点 Read 对应文件**，不凭记忆）：[00_init/Schema/剧情/](../../../00_init/Schema/剧情/)（Event/SubEvent/Info〔固有 / 事件两类〕/Cognition/StoryArc/Choice 与各边）、[Schema/角色美术/](../../../00_init/Schema/角色美术/)（Character）、[Schema/场景美术/](../../../00_init/Schema/场景美术/)（Location/Spot/Scene）。
- 写 cypher 规则：[cypher_exec.py](../../scripts/cypher_exec.py) 顶部 docstring（内联值、MERGE 幂等、必须指定标签、加 LIMIT）。

## 流程（六步）

### 0. 读文档 + 定来源

- 文档路径入参（或扫 `02_剧情数据/` 最新 `*_{共识,定稿,补全_草稿}.md`）；文件名尾段定**允许的条目域**，**source 按条目域逐条定**（I 域条目 source='event-ideator'，I1 细化块物化语句 source='entity-refiner'，S 域条目 source='event-stager'，N 域条目 source='chapter-novelist'）：
  - `_共识.md` → 允许 I1~I5（出现 S 条目 = 报错退回——共识里不该有演出域，先回 event-stager 层）；
  - `_定稿.md` → 允许 I1~I5 + S1~S3 混合（或纯 S——图模式定稿）；
  - `_补全_草稿.md` → N1（chapter-novelist 通道，不变）。
- **同日期同主题的 `_共识.md` 与 `_定稿.md` 并存 → 只消费定稿**（定稿含共识全部 I 域条目，再消费共识会产出第二套 snowflake 重复节点），汇报注明「共识已并入定稿」；纯 I 通路（无定稿）才直消共识。
- **文档是人读优先的 md**：标签行/条目结构只是惯例，**按语义解析**——字段能从行文读出即认可（不要求固定字段名/格式），读不出才回头问用户；不因格式自由而放过契约违例。
- **输出文件名 = 输入文件名把 `_共识.md` / `_定稿.md` / `_补全_草稿.md` 尾段换成 `_建议.json`**（同日期同主题；文件名不带轮次，禁止另行推导——consumer 落盘后该文件即被 dashboard glob 拾取）。
- 文档缺字段/条目语义不清 → 停下问用户，不脑补创作内容（本层只做格式与契约，不做叙事决策）。
- **无数量硬门控**：不校验条目数量上限；超大文档（如 >10 事件）在汇报中提示分批审阅，不拦截。

### 1. 逐条目严检（对照 Schema，机器项现查图）

对每条目按涉及节点 Read 对应 Schema 文件字段表，逐项过：

**撰写契约（LLM 判定，违例改写留痕）**：

- Event.title：一句话可独立成立的事实句（主谓宾）；
- Event.description：钉子细节 1-3 句，**零时间措辞**——时序定位词（周X/当晚/当天/次日/深夜等）与相对时长词（N 天后）一律不写，**跨事件时序锚定（「瑜伽馆散场后/推荐完/买完教材」类回指上游事件的措辞）同禁**——时间唯一承载是 `start_time`/`end_time` 字段；不复述 title、不写后果（另一 Event+leads_to 的职责）、不写认知解读（Info 职责）、不写拓扑注记（Choice 边职责）、不着装（appears_as 边职责）；
- Info.title/content：干净事实陈述，禁备忘/推导/编号引用/归属标注；knowledge_level 必填（1/2/3）。**两种标题契约**——固有 Info（挂 has_info）写描述性文字、不带宿主名、一条一事（如「热爱美食」）；事件 Info（挂 establishes）是带主语的完整事实句；content 默认不填；
- **Info 挂靠互斥（机器项）**：每条 Info 恰一种挂靠——事件 Info 恰 1 条 establishes、0 条 has_info；固有 Info ≥1 条 has_info、0 条 establishes。两种都无或都有 → 报错退回；
- StoryArc.description：主旨+氛围两段式（「主旨：」「氛围：」引导），值内换行写 `\n` 转义（禁物理换行），段内不写时间戳、不复述情节；
- SubEvent.title：`<父title> · <叙事短名>`（非机位名）；description 节拍级粒度，对照 SubEvent.md 撰写契约正反例。

**机器项（cypher 现查，不靠记忆）**：

- 枚举/格式：type（行动/交流/转折/状态变化）、ending_kind（BE/TE/HE/NE）、time `yyyy-MM-dd HH:mm:ss`、knowledge_level 1-3、scene_type/kind、**priority（Character P0~P5 / Location P0~P3）**、**at.type（居住/工作/暂驻）**；
- **at 起止合法性（细化块机器项）**：start_time/end_time 必填——`yyyy-MM-dd HH:mm:ss` 或哨兵 `开篇前`（久远/无法推导）/ `至今`（持续中）；细化块写语义（「一直住这」）→ 换算为 `开篇前`→`至今`，具体日期语义按文档推算，推不出问用户；
- **condition 序号换算**：文档只写语义（如「三选一选了苏晓禾」）→ 现查该 Choice 全部 option 按 label 字典序的 1 基序号，写 `choice:<id>[<n>]`；文档直接写序号的也**现查复核**；
- 既有实体 id 存在性：文档内联的全部 id 逐个 MATCH 验在图；故事线成员逐个验（MATCH 落空=静默丢边，缺失即报错回上游层，不静默丢弃）；
- **文档内指称解析（混合定稿）**：S 条目中 `定稿I1/I2/I3「名称」` 指称（S2 父Event、S1 归属等）→ 在同文档 I 域条目中找到对应条目，组装时绑定其**同轮生成的 id**；指称找不到对应 I 条目 = 报错退回（不脑补、不许猜成既有实体——同文档指称只指向同文档条目）；
- 占位查重：新占位与图上同名/同缺口实体对照（占位与真身重名=图上两节点打架）；同缺口勿重复建占位；**保留名占位带宿主 id 后缀**——`居住地点占位·<宿主id>`/`工作地点占位·<宿主id>`（后缀=Character 雪花 id，稳定唯一不受人名重复/改名影响；同名查重照常适用，同宿主同名占位再次出现=真冲突退回）；
- **固有 Info 宿主查重（细化块机器项）**：新固有 Info 与该 Character 既有的固有 Info（`MATCH (c {id:'…'})-[:has_info]->(i:Info) RETURN i.title LIMIT 50`）语义重复 → 报错退回（防第二套重复设定），不改写；新固有 Info 的 title 含宿主名 → 就地改写去掉宿主名（如「Tony 是理发师」→「是理发师」）；
- **Info 查重浅验证（2026-11-20 裁定：语义判断归生成端 event-ideator，本层不做语义对照）**：新 Info 的承载事件为图上既有时，其已有 `establishes→` 其他 Info → 该 I3 条目必须带显式「不同侧面」区分标注（reason/区分点），缺 → 报错退回；新 Info title 归一化（去空白/标点）与既有 Info 完全同名 → 拦。除此之外不设任何语义判断；
- **Cognition 机器项（认知条目，契约见 [Cognition.md](../../../00_init/Schema/剧情/Cognition.md)）**：type 枚举（KNOWS/BELIEVES/SUSPECTS/DOUBTS）；title 条件必填——所信命题 ≠ Info title 时必填、= 事实时不填（填即复述，违规改写为 null）；**认知三元不重复**（认知编年史：同一 (Character, Info) 多条并存合法，仅同 (Character, Info, forms 锚事件或「前史」) 三元重复才报错退回——现查图已有同锚条目即拦）；态度转变 = **追加新条目**（新 Cognition + 三边，forms 锚转变事件，旧条零改动——无任何 SET/DELETE 改写语句）；**主语换挂**（认知归属人 A→B）在新条目照建后于汇报提示「建议摘除旧主语链（dashboard 人工执行）」——删边类不进建议 JSON；**forms 可选、有口径**——指向事件 Info（有 establishes）的认知必须 ≥1 条 forms；**无 forms = 前史认知**（开篇前就知道），只能指向固有 Info（挂 has_info、无 establishes），指向事件 Info 却无 forms → 报错退回；**宿主不给自己建认知**（持有者同时是所指固有 Info 的宿主 → 报错退回）；**锚事件 condition**——establishes 与 forms 的锚事件挂 condition（choice 表达式分支事件）**照常放行**：图是 run 无关的，有效性由跑团端按周目已选支线过滤（跨支不泄漏——非本支锚的认知对其他支线的 run 不可见，见 [Event.md](../../../00_init/Schema/剧情/Event.md) condition 求值口径）；**不查 type×title 映射**（语义表是写作参考非门禁）；
- 表外字段一律不写：占位 Character 只 name/vibe（细化块有 priority 则加写）、Location 只 name/description/**priority（占位恒 P3）**、Spot 只 name/kind/description、Scene 只 name/scene_type/status=0、CostumeStyle 只 name/vibe/status=0、IllusDesign 只 status=0。

**各来源创作域红线**（越域条目报错退回，不改写；混合定稿按条目域各查各的）：

- ideator：不建 SubEvent/Spot/Scene/CostumeStyle/IllusDesign/Choice，不改既有节点属性（I5 的 StoryArc.description 与 I6 的 Event.description 除外——后者仅盘点支线分界契约修正场景：剥 Info 复述/补行为名义/删时间措辞，reason 必含 before/after 摘要）；
- refiner（I1 细化块）：只产 Character.priority、at 边（type=居住/工作，挂保留名占位或点名轮既有 Location id）、基础固有 Info + has_info 边（节点标签 `Info`）；不建 Event/事件 Info/Choice/Spot/Scene/SubEvent/CostumeStyle/IllusDesign，不改 vibe/name/事件条目；
- stager：不建 Event/Info/Choice/Location/Character；Event 直挂 anchored_at/appears_as 为违规（EA5）；
- novelist（N1）：只提新 Event/Info + 定位边（occurs_at/involved/leads_to/establishes）与认知条目（has_cognition/about/forms），**禁改既有实体属性、禁夹带校验节点、不建固有 Info**。

**违例处置**：可无损改写的（措辞越界、格式、序号、转义）就地改写，**before/after 逐条记入汇报**；改写会改变叙事语义的 → 停下问用户。

### 2. id 生成

`$SF_GEN -n 1 -q` 逐节点生成（占位实体、事件、Info、新 StoryArc、SubEvent；引用既有实体的不生成）。同一实体在节点语句与挂边语句中必须是同一字面值；**混合定稿中同文档指称实体只生成一次 id**（`定稿I1/I2/I3「名称」`→id 映射贯穿组装，S 域挂边语句用同一字面值）；**保留名占位 Location 名带宿主 Character id 后缀**（`居住/工作地点占位·<宿主id>`，id 逐一独立生成；后缀是宿主 id 不是该 Location 自己的 id——查宿主 Character 拿字面值）。

### 3. 组装建议 JSON

顶层数组，逐项 `{check, priority, reason, content, cypher, source}`（source 按条目域）。**组装顺序 = 依赖序（节点先于边）**：

- **混合定稿固定 I1 占位（含细化物化：占位 Location → Character → at 边 → 固有 Info → has_info）→ S1 占位 → I2 事件 → S2 SubEvent → S3 补边**——S1 Spot 的 part_of 挂同轮 I1 生成的 Location id、S2 的 refines 挂同轮 I2 生成的事件 id、at 边挂同轮 I1 生成的 Character/保留名占位 id，按序执行/采纳时依赖成立；
- 纯 S 定稿沿用 S1 → S2 → S3；纯 I 共识沿用 I1 → I2 → I3/I4/I5（先占位实体后事件，挂边随各自条目）。

汇报附**跨条目依赖清单**（如「#5 S1 依赖 #1 I1 的生成 id」），提示执行/人工采纳按序全采、勿只采一半。check/priority 沿用：

- ideator 域：I1_placeholder_entity（占位 Character 节点，细化块有 priority 则并入本项 SET；占位 Location 节点恒 priority=P3）/ I2_new_event（结局/转折 high 否则 medium）/ I3_new_info（low）/ I4_new_story_arc（medium；扩线注明、省略 CREATE 句）/ I5_story_arc_update（low，改既有节点属性例外一，仅 StoryArc.description）/ I6_desc_update（low，改既有节点属性例外二，仅 Event.description，盘点分界契约修正——新文案过零时间措辞/不复述 title/不写认知解读三检，reason 必含 before/after 摘要）；
- refiner 域（I1 细化块物化，source='entity-refiner'）：R1_anchor_at（保留名占位 Location 节点 + at 边，随人物一项，medium）/ R2_char_info（基础固有 Info 节点 + has_info 边，每条一项，low；项名沿用）/ R3_char_priority（点名轮既有 Character 补写或改判 priority，low）；
- cognition 域（共识/定稿/点名稿含认知条目，source 按文档来源）：R4_cognition（Cognition 节点 + has_cognition/about/forms 三边，新建与追加同款——态度转变即追加新条目（forms 锚转变事件），主语换挂建新条目后汇报提示旧链人工摘除；叙事关键 medium 否则 low）；
- stager 域：S1_placeholder_node（high）/ S2_subevent / S3_gap_fix；
- novelist 域：N1_novel_new_entity（新 Event/Info + 定位边，priority 按事件类型同 I2）；
- arc→new 事件：I2 项 cypher 末尾追加 comprises 挂线语句（不为挂边单独立项）；
- reason 保留文档的依据标注（图上实查 vs 常识推断分离），含严检改写说明。

### 4. 落盘 + lint（提交门槛）

- Write `${OUTPUT_DIR}/<输入文档同日期同主题>_建议.json`（UTF-8；JSON 是执行确认前的审阅载体 + 审计 + dashboard 兼容，无论走哪条通道都必须先落盘）；
- `$SUGGEST_LINT <文件路径>`——exit 0 = 全 PASS；任何 FAIL 按输出提示就地改写 cypher、覆盖重写、重跑至全 PASS；
- lint 只护 cypher 语句——**第 1 步的撰写契约严检是文本层的唯一防线**，不许因 lint PASS 跳过。

### 5. 执行确认门（必停一问）+ 执行写回

- **lint PASS 后必须停下问用户**（本 skill 零交互原则的唯一例外，也是写图的唯一入口）：摆出条目清单（逐条 #序号 check/title/依赖序）+「是否直接执行写回图？」——**用户明确同意才执行**；不同意/暂缓 → 汇报 dashboard 备选通道话术（`/events`「📥 补全建议」逐条审阅采纳）后结束。被 agent 编排时同样停等用户本人，agent 不代答。
- **执行机制**：
  1. JSON 内全部 cypher 按序写入 `.tmp/consumer/<主题>_执行.cypher`（每语句 `;` 结尾、依赖有序）；
  2. `cypher_exec.py -f <file> --multi` **单事务**执行——全成或全败无半写状态，MERGE 幂等可安全重跑；
  3. **读回验证**（写后必读回）：逐类节点/边 MATCH 计数对照 JSON 条目数；抽查 refines sync=true、anchored_at/appears_as 挂 SubEvent 不挂 Event、占位节点最小启动集与 status=0；
  4. 验证通过 → 删临时文件（`.tmp/` 用后即删）；验证不符 → 保留临时文件并报路径。
- **失败处置**：事务失败或读回不符 → 原样报错停下，**不擅自重试、不擅自修补**——修复决策交用户（可改共识/定稿重走，或人工 dashboard 处置）。
- **与 dashboard 通道幂等共存**：雪花 id 固定 + MERGE + `ON CREATE SET`——即使执行后 dashboard 再采纳同一 JSON 也不会重复建节点；两通道互不冲突。

### 6. 汇报

建议 JSON 路径 + 条数与 check/priority 分布 + lint 全 PASS 确认 + **严检改写清单（before/after）** + 占位清单 + 跨条目依赖清单 + **执行结果分支**（已执行：语句数 + 读回验证结论 + 「已写回，可分节推进」；未执行：原因 + dashboard 备选通道话术）+ 语义两可未决项（如有）。

## cypher 模板（照抄改值）

> **语句自包含铁律**：`;` 分隔的每条语句是独立查询，**变量不跨语句延续**——挂边语句的两端点都在**本语句内**先 `MATCH (x:Label {id:'…'})` 绑定，MERGE 边里只用裸变量；MERGE 端点写成 `(y:Label {id:'…'})` 锚定形态直接出现时，未命中会**整 pattern 重建**出重复 id 节点（历史事故形态）。每个分号独占行尾；cypher 字段不携带 `//` 注释（写在 reason）；同一实体 id 在节点语句与挂边语句中是同一字面值。

### ideator 域

```
// 占位 Character（裸节点：name/vibe；I1 细化块有 priority 则并入本句 SET；MERGE 幂等——重跑/双通道重入无重复节点）
MERGE (c:Character {id:'<snowflake>'}) ON CREATE SET c.name='<姓名>', c.vibe='<一句话氛围人设>', c.priority='<P0~P5，仅细化块有则写>';
// 占位 Location（裸节点：name/description + priority 恒 P3；空间链不在创建域）
MERGE (l:Location {id:'<snowflake>'}) ON CREATE SET l.name='<名称>', l.description='<一句话定位>', l.priority='P3';
// 新事件
MERGE (e:Event {id:'<snowflake>'}) ON CREATE SET e.title='<title>', e.start_time='<yyyy-MM-dd HH:mm:ss>', e.end_time='<yyyy-MM-dd HH:mm:ss 点事件同值>', e.type='<type>', e.description='<desc>';
MATCH (e:Event {id:'<event_id>'}) MATCH (l:Location {id:'<loc_id>'}) MERGE (e)-[r:occurs_at]->(l) ON CREATE SET r.sync=false;
MATCH (c:Character {id:'<char_id>'}) MATCH (e:Event {id:'<event_id>'}) MERGE (c)-[r:involved]->(e) ON CREATE SET r.sync=false;
// 仅文档明说因果时（方向 = 因 → 果）
MATCH (a:Event {id:'<既有事件id>'}) MATCH (e:Event {id:'<event_id>'}) MERGE (a)-[r:leads_to]->(e) ON CREATE SET r.sync=false;
// 事件 Info（Event ─establishes→ Info，恰一个成立承载事件；title 是带主语的完整事实句）
MERGE (f:Info {id:'<snowflake>'}) ON CREATE SET f.title='<标题：带主语的完整事实句>', f.content='<内容，可空则省略本段>', f.knowledge_level=<1|2|3>;
MATCH (ev:Event {id:'<carrier_event_id>'}) MATCH (f:Info {id:'<info_id>'}) MERGE (ev)-[r:establishes]->(f) ON CREATE SET r.sync=false;
// 固有 Info（(Character|Location) ─has_info→ Info；开篇前就已为真；title 写描述性文字、不带宿主名、一条一事）
MERGE (f:Info {id:'<snowflake>'}) ON CREATE SET f.title='<描述性文字>', f.content='<内容，可空则省略本段>', f.knowledge_level=<1|2|3>;
MATCH (h {id:'<host_id：Character 或 Location>'}) MATCH (f:Info {id:'<info_id>'}) MERGE (h)-[r:has_info]->(f) ON CREATE SET r.sync=false;
// 故事线（I4 建线形；扩线形 = 仅 MERGE，每成员一条）
MERGE (a:StoryArc {id:'<snowflake>'}) ON CREATE SET a.title='<标题>', a.description='主旨：…\n氛围：…';
MATCH (a:StoryArc {id:'<arc_id>'}) MATCH (e:Event {id:'<event_id>'}) MERGE (a)-[r:comprises]->(e) ON CREATE SET r.sync=false;
// I5 对账更新（唯一改既有节点属性的例外，仅 description）
MATCH (a:StoryArc {id:'<arc_id>'}) SET a.description='<重写后的主旨/氛围全文>';
// I6 Event.description 修正（盘点分界契约场景：剥 Info 复述/补行为名义/删时间措辞；新文案过零时间措辞/不复述 title/不写认知解读三检）
MATCH (e:Event {id:'<event_id>'}) SET e.description='<重写后的 description 全文>';
// arc→new 新事件挂线（追加在该事件 I2 项 cypher 末尾）
MATCH (a:StoryArc {id:'<arc_id>'}) MATCH (e:Event {id:'<event_id>'}) MERGE (a)-[r:comprises]->(e) ON CREATE SET r.sync=false;
```

### refiner 域（I1 细化块物化）

```
// R1_anchor_at——保留名占位 Location（名带宿主 Character id 后缀，稳定唯一；每锚点独立 id）+ at 边（节点先于边，各语句自包含；工作地与居住地同地点时不建工作锚）
// ⚠ at 边 MERGE 必须带 {type:…} 入 pattern：不带 type 时同人物同地点的第二条边（如工作）会 MERGE 命中第一条（居住）而静默不建（2026-11-19 全角色细化轮实测事故）
MERGE (l:Location {id:'<snowflake>'}) ON CREATE SET l.name='居住地点占位·QP23NrFZrz', l.priority='P3';
MATCH (c:Character {id:'<char_id_本建议占位或既有>'}) MATCH (l:Location {id:'<snowflake_同上>'})
MERGE (c)-[r:at {type:'居住'}]->(l) ON CREATE SET r.start_time='<yyyy-MM-dd HH:mm:ss 或 开篇前>', r.end_time='<同左 或 至今>', r.sync=false;
// R2_char_info——基础固有 Info 节点 + has_info 宿主边（每条一项；项名沿用，节点标签 Info）
MERGE (f:Info {id:'<snowflake>'}) ON CREATE SET f.title='<描述性文字，不带宿主名>', f.content='<内容，可空则省略本段>', f.knowledge_level=<1|2|3>;
MATCH (c:Character {id:'<char_id>'}) MATCH (f:Info {id:'<snowflake_同上>'}) MERGE (c)-[r:has_info]->(f) ON CREATE SET r.sync=false;
// R3_char_priority——点名轮既有 Character 补写/改判（唯一改既有 Character 属性的通道，仅 priority）
MATCH (c:Character {id:'<char_id>'}) SET c.priority='<P0~P5>';
```

### cognition 域（R4_cognition）

```
// 新建/追加同款（认知编年史：态度转变=追加新条目，旧条零改动）——MERGE 幂等（重跑/双通道重入无重复），节点先于边，各语句自包含；同 (Character, Info, forms 锚事件或「前史」) 三元不重复由 §1 严检在生成端保证（生成前现查三元组）
MERGE (c:Cognition {id:'<snowflake>'}) ON CREATE SET c.type='<KNOWS|BELIEVES|SUSPECTS|DOUBTS>', c.title='<仅所信≠Info title 时写，否则删本段>';
MATCH (ch:Character {id:'<char_id>'}) MATCH (c:Cognition {id:'<snowflake_同上>'}) MERGE (ch)-[r:has_cognition]->(c) ON CREATE SET r.sync=false;
MATCH (c:Cognition {id:'<snowflake_同上>'}) MATCH (i:Info {id:'<info_id>'}) MERGE (c)-[r:about]->(i) ON CREATE SET r.sync=false;
MATCH (ev:Event {id:'<forms_event_id>'}) MATCH (c:Cognition {id:'<snowflake_同上>'}) MERGE (ev)-[f:forms]->(c) ON CREATE SET f.sync=false;
// 前史认知（开篇前就知道；只能指向固有 Info）：省略上面 forms 那一句
// 主语换挂：新主语按上款建新条目；旧主语链的删边不进建议 JSON——汇报提示「建议摘除旧主语链 <cognition_id>（dashboard 人工执行）」
```

### stager 域

```
// Spot 占位——节点本体
CREATE (sp:Spot {id:'<snowflake>'}) SET sp.name='<地点名>-<区域>', sp.kind='zone', sp.description='<一句话>';
MATCH (l:Location {id:'<loc_id>'}) MATCH (sp:Spot {id:'<snowflake>'}) MERGE (l)-[r:part_of]->(sp) ON CREATE SET r.sync=false;
// Scene 占位——节点本体
CREATE (sc:Scene {id:'<snowflake>'}) SET sc.name='<机位名>', sc.scene_type='<类型>', sc.status=0;
MATCH (sp:Spot {id:'<spot_id_既有或上方占位>'}) MATCH (sc:Scene {id:'<snowflake>'}) MERGE (sp)-[r:realizes]->(sc) ON CREATE SET r.sync=false;
// CostumeStyle 占位——节点本体 + 归属（占位即挂，禁止孤儿占位）
CREATE (cs:CostumeStyle {id:'<snowflake>'}) SET cs.name='<着装名>', cs.vibe='<调性一句话>', cs.status=0;
MATCH (ch:Character {id:'<char_id>'}) MATCH (cs:CostumeStyle {id:'<snowflake>'}) MERGE (ch)-[r:has_costume]->(cs) ON CREATE SET r.sync=true;
// IllusDesign 占位——节点本体
CREATE (idn:IllusDesign {id:'<snowflake>'}) SET idn.status=0;
MATCH (cs:CostumeStyle {id:'<cs_id_既有或上方占位>'}) MATCH (idn:IllusDesign {id:'<snowflake>'}) MERGE (cs)-[r:outfit_for]->(idn) ON CREATE SET r.sync=true;
// SubEvent：本体+refines 一体语句；anchored_at / appears_as 各自独立语句
MATCH (e:Event {id:'<parent_id>'})
MERGE (sub:SubEvent {id:'<snowflake>'})
ON CREATE SET sub.title='<父title> · <叙事短名>', sub.start_time='<插值时间>', sub.end_time='<同值>',
              sub.description='<节拍链，规范见 SubEvent.md 撰写契约>'
MERGE (e)-[r:refines]->(sub) ON CREATE SET r.sync=true;
MATCH (sub:SubEvent {id:'<snowflake_同上>'}) MATCH (scn:Scene {id:'<scene_id_既有或本建议占位>'})
MERGE (sub)-[a:anchored_at]->(scn) ON CREATE SET a.sync=false;
MATCH (sub:SubEvent {id:'<snowflake_同上>'}) MATCH (il:IllusDesign {id:'<illus_id_继承既有或本建议占位>'})
MERGE (sub)-[ap:appears_as]->(il) ON CREATE SET ap.sync=false, ap.detail='<继承：同父兄弟着装 / 占位：新套装待消化>';
// S3 补边（仅图模式：实体在图只缺边）
MATCH (ch:Character {id:'<char_id>'}) MATCH (e:Event {id:'<event_id>'}) MERGE (ch)-[r:involved]->(e) ON CREATE SET r.sync=false;
```

- 边 sync 语义：refines/outfit_for/has_costume=true（细化时级联下游）；叙事挂边与演出绑定（involved/occurs_at/establishes/leads_to/comprises/part_of/realizes/anchored_at/appears_as/at/has_info/has_cognition/about/forms）恒 false（以 [Schema/剧情/边.md](../../../00_init/Schema/剧情/边.md) / 场景美术边文件为准）。
- 多语句 `;`+换行分隔、逐句 `;` 结尾、先节点后边；MERGE 幂等；内联值单引号转义；不用 `$param`；不加时序边。

## 参考文档

- [00_init/Schema/](../../../00_init/Schema/)（严检唯一依据：逐节点字段表 + 撰写契约正反例）
- [suggest_lint.py](../../scripts/suggest_lint.py)（语句级护栏）· [snowflake_base62.py](../../scripts/snowflake_base62.py)（id）
- 文档来源 skill：[event-ideator](../event-ideator/SKILL.md)（共识）/ [entity-refiner](../entity-refiner/SKILL.md)（I1 细化块）/ [event-stager](../event-stager/SKILL.md)（定稿）
