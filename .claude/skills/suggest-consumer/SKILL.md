---
name: suggest-consumer
description: |
  建议消费层——叙事事件链的 Schema 守门人：消费三类人读优先的自然语言文档（按语义解析）——**事件共识**（`*_共识.md`，纯 I 域条目）/ **事件定稿**（`*_定稿.md`，I+S 混合或纯 S 域）/ **小说对账补全**（`*_补全_草稿.md`，N 域）。逐条目对照 00_init/Schema/ 字段表契约严检（撰写契约、枚举、必填、时间格式、condition 序号换算、占位最小启动集、id 存在性、占位查重、文档内指称解析、各来源创作域红线），违例就地改写并留痕（before/after），生成 snowflake id、按模板组装建议 JSON（含 cypher，先节点后边、语句自包含、同文档指称绑定同轮生成 id），落盘同名 `_建议.json`，跑 suggest_lint 至全 PASS。**执行确认门**：lint PASS 后必停一问，用户明确同意才直接执行写回（单事务 + 读回验证，不经 dashboard）；不同意则留 dashboard 建议弹窗人工备选通道。
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

- Schema（严检的唯一依据，**逐条目按涉及节点 Read 对应文件**，不凭记忆）：[00_init/Schema/剧情/](../../../00_init/Schema/剧情/)（Event/SubEvent/Info/Lore/StoryArc/Choice 与各边）、[Schema/角色美术/](../../../00_init/Schema/角色美术/)（Character）、[Schema/场景美术/](../../../00_init/Schema/场景美术/)（Location/Spot/Scene）。
- 写 cypher 规则：[cypher_exec.py](../../scripts/cypher_exec.py) 顶部 docstring（内联值、MERGE 幂等、必须指定标签、加 LIMIT）。

## 流程（六步）

### 0. 读文档 + 定来源

- 文档路径入参（或扫 `02_剧情数据/` 最新 `*_{共识,定稿,补全_草稿}.md`）；文件名尾段定**允许的条目域**，**source 按条目域逐条定**（I 域条目 source='event-ideator'，S 域条目 source='event-stager'，N 域条目 source='chapter-novelist'）：
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
- Info.title/content：干净事实陈述，禁备忘/推导/编号引用/归属标注；knowledge_level 必填（1/2/3）；
- StoryArc.description：主旨+氛围两段式（「主旨：」「氛围：」引导），值内换行写 `\n` 转义（禁物理换行），段内不写时间戳、不复述情节；
- SubEvent.title：`<父title> · <叙事短名>`（非机位名）；description 节拍级粒度，对照 SubEvent.md 撰写契约正反例。

**机器项（cypher 现查，不靠记忆）**：

- 枚举/格式：type（行动/交流/转折/状态变化）、ending_kind（BE/TE/HE/NE）、time `yyyy-MM-dd HH:mm:ss`、knowledge_level 1-3、scene_type/kind；
- **condition 序号换算**：文档只写语义（如「三选一选了苏晓禾」）→ 现查该 Choice 全部 option 按 label 字典序的 1 基序号，写 `choice:<id>[<n>]`；文档直接写序号的也**现查复核**；
- 既有实体 id 存在性：文档内联的全部 id 逐个 MATCH 验在图；故事线成员逐个验（MATCH 落空=静默丢边，缺失即报错回上游层，不静默丢弃）；
- **文档内指称解析（混合定稿）**：S 条目中 `定稿I1/I2/I3「名称」` 指称（S2 父Event、S1 归属等）→ 在同文档 I 域条目中找到对应条目，组装时绑定其**同轮生成的 id**；指称找不到对应 I 条目 = 报错退回（不脑补、不许猜成既有实体——同文档指称只指向同文档条目）；
- 占位查重：新占位与图上同名/同缺口实体对照（占位与真身重名=图上两节点打架）；同缺口勿重复建占位；
- 表外字段一律不写：占位 Character 只 name/vibe、Location 只 name/description、Spot 只 name/kind/description、Scene 只 name/scene_type/status=0、CostumeStyle 只 name/vibe/status=0、IllusDesign 只 status=0。

**各来源创作域红线**（越域条目报错退回，不改写；混合定稿按条目域各查各的）：

- ideator：不建 SubEvent/Spot/Scene/CostumeStyle/IllusDesign/Choice，不改既有节点属性（I5 的 description 除外）；
- stager：不建 Event/Info/Lore/Choice/Location/Character；Event 直挂 anchored_at/appears_as 为违规（EA5）；
- novelist（N1）：只提新 Event/Info + 定位边（occurs_at/involved/leads_to/knows），**禁改既有实体属性、禁夹带校验节点、不建 Lore**。

**违例处置**：可无损改写的（措辞越界、格式、序号、转义）就地改写，**before/after 逐条记入汇报**；改写会改变叙事语义的 → 停下问用户。

### 2. id 生成

`$SF_GEN -n 1 -q` 逐节点生成（占位实体、事件、Info、新 StoryArc、SubEvent；引用既有实体的不生成）。同一实体在节点语句与挂边语句中必须是同一字面值；**混合定稿中同文档指称实体只生成一次 id**（`定稿I1/I2/I3「名称」`→id 映射贯穿组装，S 域挂边语句用同一字面值）。

### 3. 组装建议 JSON

顶层数组，逐项 `{check, priority, reason, content, cypher, source}`（source 按条目域）。**组装顺序 = 依赖序（节点先于边）**：

- **混合定稿固定 I1 占位 → S1 占位 → I2 事件 → S2 SubEvent → S3 补边**——S1 Spot 的 part_of 挂同轮 I1 生成的 Location id、S2 的 refines 挂同轮 I2 生成的事件 id，按序执行/采纳时依赖成立；
- 纯 S 定稿沿用 S1 → S2 → S3；纯 I 共识沿用 I1 → I2 → I3/I4/I5（先占位实体后事件，挂边随各自条目）。

汇报附**跨条目依赖清单**（如「#5 S1 依赖 #1 I1 的生成 id」），提示执行/人工采纳按序全采、勿只采一半。check/priority 沿用：

- ideator 域：I1_placeholder_entity / I2_new_event（结局/转折 high 否则 medium）/ I3_new_info（low）/ I4_new_story_arc（medium；扩线注明、省略 CREATE 句）/ I5_story_arc_update（low，唯一改既有节点属性的例外，仅 description）；
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
// 占位 Character（裸节点：name/vibe，无 status；外貌链不在创建域）
CREATE (c:Character {id:'<snowflake>'}) SET c.name='<姓名>', c.vibe='<一句话氛围人设>';
// 占位 Location（裸节点：name/description，无 status；空间链不在创建域）
CREATE (l:Location {id:'<snowflake>'}) SET l.name='<名称>', l.description='<一句话定位>';
// 新事件
CREATE (e:Event {id:'<snowflake>'}) SET e.title='<title>', e.start_time='<yyyy-MM-dd HH:mm:ss>', e.end_time='<yyyy-MM-dd HH:mm:ss 点事件同值>', e.type='<type>', e.description='<desc>';
MATCH (e:Event {id:'<event_id>'}) MATCH (l:Location {id:'<loc_id>'}) MERGE (e)-[r:occurs_at]->(l) ON CREATE SET r.sync=false;
MATCH (c:Character {id:'<char_id>'}) MATCH (e:Event {id:'<event_id>'}) MERGE (c)-[r:involved]->(e) ON CREATE SET r.sync=false;
// 仅文档明说因果时（方向 = 因 → 果）
MATCH (a:Event {id:'<既有事件id>'}) MATCH (e:Event {id:'<event_id>'}) MERGE (a)-[r:leads_to]->(e) ON CREATE SET r.sync=false;
// Info（Event ─knows→ Info，每个知晓承载事件一条 knows 边）
CREATE (f:Info {id:'<snowflake>'}) SET f.title='<标题>', f.content='<内容>', f.knowledge_level=<1|2|3>;
MATCH (ev:Event {id:'<carrier_event_id>'}) MATCH (f:Info {id:'<info_id>'}) MERGE (ev)-[r:knows]->(f) ON CREATE SET r.sync=false;
// 故事线（I4 建线形；扩线形 = 仅 MERGE，每成员一条）
CREATE (a:StoryArc {id:'<snowflake>'}) SET a.title='<标题>', a.description='主旨：…\n氛围：…';
MATCH (a:StoryArc {id:'<arc_id>'}) MATCH (e:Event {id:'<event_id>'}) MERGE (a)-[r:comprises]->(e) ON CREATE SET r.sync=false;
// I5 对账更新（唯一改既有节点属性的例外，仅 description）
MATCH (a:StoryArc {id:'<arc_id>'}) SET a.description='<重写后的主旨/氛围全文>';
// arc→new 新事件挂线（追加在该事件 I2 项 cypher 末尾）
MATCH (a:StoryArc {id:'<arc_id>'}) MATCH (e:Event {id:'<event_id>'}) MERGE (a)-[r:comprises]->(e) ON CREATE SET r.sync=false;
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

- 边 sync 语义：refines/outfit_for/has_costume=true（细化时级联下游）；叙事挂边与演出绑定（involved/occurs_at/knows/leads_to/comprises/part_of/realizes/anchored_at/appears_as）恒 false（以 [Schema/剧情/边.md](../../../00_init/Schema/剧情/边.md) / 场景美术边文件为准）。
- 多语句 `;`+换行分隔、逐句 `;` 结尾、先节点后边；MERGE 幂等；内联值单引号转义；不用 `$param`；不加时序边。

## 参考文档

- [00_init/Schema/](../../../00_init/Schema/)（严检唯一依据：逐节点字段表 + 撰写契约正反例）
- [suggest_lint.py](../../scripts/suggest_lint.py)（语句级护栏）· [snowflake_base62.py](../../scripts/snowflake_base62.py)（id）
- 文档来源 skill：[event-ideator](../event-ideator/SKILL.md)（共识）/ [event-stager](../event-stager/SKILL.md)（定稿）
