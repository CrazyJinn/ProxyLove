---
name: event-stager
description: |
  事件细化落地层——输入 Event（id/title/时间窗），四步推进：前置核验（缺叙事基础实体报错不代建）→ 探索演出资源并拆解 SubEvent（戏剧节拍分析，模式库只查遗漏不做生成依据）→ 占位物化（为 sub 建 IllusDesign←appears_as←SubEvent→anchored_at→Scene 链，Spot/Scene/CostumeStyle/IllusDesign 缺口建占位）→ 逐 event 询问确认 + 产建议 JSON（人工经 dashboard 写回）。
  多轮交互一次一问、每问附推荐；单轮至多 3 个 event。不建 Event/Hook/Lore/Choice/Location/Character。
  在用户说「细化」「stager」「这批事件细化一下」或给出事件范围要求推进机位层时使用。
argument-hint: <event id列表 | 事件title列表 | 时间窗>
arguments:
  - events
allowed-tools: Read, Bash, Write
---

# 事件细化落地（event-stager）

把粗粒度 Event 物化成机位级演出段（SubEvent），并把演出所需实体**全部占位物化**（演出侧叙事决策在本层发生，创建权就在本层）。缺口处置一律「占位节点」——占位在图上的位置自带需求上下文，可被独立消化。

**三条铁律**（全程生效）：

1. **零直接图写入**：交互期间仅查询；全部产出经建议 JSON 落盘、人工在 dashboard 写回。
2. **建议 JSON 契约**：顶层数组，逐项 `{check, priority, reason, content, cypher}` + `source:'event-stager'`（check 见 §4）；落盘 `02_剧情数据/<日期>_round<N>_<主题>_stager_建议.json`（必须 `_建议.json` 结尾，dashboard 弹窗按此 glob 拾取）；轮次 N 由 `$ROUND` 推导（共享计数器，勿手写扫描）。落盘后 `$SUGGEST_LINT` 全 PASS 才算提交。
3. **一题一答且一 Event 一题**：一次只问一个问题、每问附可归因推荐答案；facts 自己查，decisions 才问用户；缺口修复逐条问，sub+占位方案按 Event 聚合成一题整体拍板。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
SF_GEN="python ${CLAUDE_SKILL_DIR}/../../scripts/snowflake_base62.py"
ROUND="python ${CLAUDE_SKILL_DIR}/../../scripts/suggest_round.py"    # 轮次推导（共享计数器）
PREFLIGHT="python ${CLAUDE_SKILL_DIR}/scripts/preflight.py"          # 前置核验（范围+契约+资源）
SUGGEST_LINT="python ${CLAUDE_SKILL_DIR}/../../scripts/suggest_lint.py"  # 建议语句级护栏
OUTPUT_DIR="02_剧情数据"
```

## 职责边界

- **创建域 = 演出域四类占位 + SubEvent**：SubEvent + refines 边；anchored_at 边（Scene 缺则建占位，挂 realizes 到既有 Spot，Spot 也缺则建 Spot 占位）；appears_as 边（着装优先继承父/兄弟 sub，套缺则建 CostumeStyle 占位、版本缺则建 IllusDesign 占位）；S3 揭示边（见 §4）。
- **着装占位必须同时挂 `Character→has_costume` 归属边**——归属角色 = 该着装缺口所属的 involved 角色（拍板上下文恒明确）；孤儿占位在 dashboard 全链路不可见、体检 E1 误报。
- **禁建**：Event/Hook/Lore/Choice/Location/Character（缺叙事基础实体一律报错回 event-ideator 层）；Event 直挂 anchored_at/appears_as（EA5 体检兜查）；改既有节点属性。
- **sub 与 Scene 的边界**：sub 描述剧情动作（谁做了什么、什么变化），Scene 只管机位/背景画面——人物姿势、表情、位置属立绘与演出指令层；镜头设计（近景/特写切换）是剧本分镜层的事，sub 只到「机位级演出段」粒度。
- 删父 Event 连带删其全部 sub（dashboard event_crud 已实现级联）。

## 图模型（写 Cypher 前必读）

```
人工层：  Character ─involved→ Event ─occurs_at→ Location   （入口核验的前提）
          Section ─includes{order}→ Event                    ← 分节/时间轴只碰 Event
细化层：  Event ─refines{sync:true}→ SubEvent                ← 1:N，本 skill 产
          SubEvent ─anchored_at→ Scene                       ← 严格 1:1（一 sub 一机位），缺则建 Scene 占位
          SubEvent ─appears_as→ IllusDesign                  ← 继承或占位
空间链：  Location ─part_of→ Spot ─realizes→ Scene           ← Spot 缺则建占位
着装链：  Character ─has_costume→ CostumeStyle ─outfit_for→ IllusDesign ← 缺则建占位（占位即挂归属边）
```

- SubEvent 属性仅 id/title/time/description；**无** status/type/involved/occurs_at。
- 占位节点属性 = 最小启动集（Spot: name/kind/description 无 status 骨架；Scene: name/scene_type；CostumeStyle: name/vibe；IllusDesign: 裸节点——后三者流水线 status=0 起点，含义是"待生产"非"占位标记"）；其余字段由消化方（scene-designer / char-design 链）按各自 Schema 补全。
- 占位 Scene 后续改名/改字段不造成 sub 漂移（title/description 不引用机位信息，见 §2 规范）。

## 工作流（四步）

### 1. 前置核验（发现确定性缺口）

```bash
$PREFLIGHT --ids <id1,id2> [--titles t1,t2] [--window 起,止] [--json]
```

一次跑出四样 facts（全部只读）：

- **范围解析**：命中事件清单（id/title/time/occurs_at/involved），复述 N 个事件 + 时间跨度再进下一步；
- **入口核验（权威表述）**：`verdict=FAIL`（缺 occurs_at Location / 缺 involved Character）→ **先分诊**：缺的实体**在图、只缺边** → 转 §4 的 `S4_gap_fix` 补边建议，流程继续；实体**不在图** → **报错停止**（脚本 `failures` 已逐事件列出），不代建，回 event-ideator 层补。title/description 提及实体未建档同理（LLM 读文判断，实体是否在图对照 `assets` 段核查）；
- **批次切分**：单轮上限 3 个 event，超出时脚本 `batch` 段已切好（本轮时间最早 3 个，余者列入汇报「下轮可细化」）；
- **演出资源现状**：`assets` 段（每 involved char 立绘链 / 着装直查表 `costumes`——含 status=0 占位，**同缺口勿重复建占位** / 每 location 空间链）——§2 拆解的全部 facts，不必重查。

### 2. 探索演出资源 + 拆解 SubEvent

**探索**（facts 由 §1 `assets` 段带出）：立绘链（Character→AppearanceStyle→DesignSheet→IllusDesign←outfit_for←CostumeStyle）是着装继承与占位判断的依据；着装全集另见 `costumes` 段（has_costume 直查，覆盖无 DesignSheet 的占位着装）——建占位前先对表防重。空间链（Spot→realizes→Scene）是机位选用与占位判断的依据；信息不足时按需补查（查询形态见 preflight.py 源码）。

**拆解六步固定**（模式库在末位做校验与补遗——先找演出价值，再对模式查遗漏）：

1. **戏剧节拍分析**：从事件 title/description 识别值得表现的节拍（铺垫/触发/反应/释放/余韵）。只识别潜在演出内容，不要求每个节拍都生成 sub。
2. **动作与状态变化分析**：把值得表现的节拍转化为具体剧情动作——逐项过：谁行动、对象、时间与空间、结果、是否带来可感知的信息/情绪/关系/状态变化（**未带来变化的动作不拆**）。description 按 [SubEvent.md](../../../00_init/Schema/剧情/SubEvent.md) 撰写契约落节拍级。
3. **独立演出价值判断**（拆/不拆的裁决，防过拆与欠拆）：演出价值 = 铺垫→触发→释放→余韵**至少占一环，且 sub 必须带来可感知的变化**——仅存在一个动作不构成拆分理由；无价值不拆，挤水分与拆段都是伤害，宁少勿滥；纯过渡/独处/状态变化单段即足。拆分数量遵循实际剧情密度：**过拆**（普通动作、每句对话都拆）与**欠拆**（多个独立戏剧阶段塞一个 sub）都是错误；对峙类高密度演出优先 1 个 sub，独立触发/反转/爆发阶段显著时可拆多段。
4. **模式库校验**：对照 [references/微演出模式库.md](references/微演出模式库.md) 检查拆分方案有没有漏拆（漏掉的到场/物件交互）或踩不拆反例——不强制每个 sub 匹配一个模式，命中多模式可组合参考。
5. **SubEvent 生成**：生成 sub 及 anchored_at/appears_as 关系。时间由上下文推导（到场在主活动前、离开在收尾后、换区按位移节奏），**不虚构精确时间**——只要求与父事件及邻接 sub 因果先后相容，允许合理重叠（并行发生的事）。
6. **演出验收**：时间符合因果先后、人物连续性、动作完整性（每个 sub 能说清「谁对谁做了什么」）、不重复表达父 Event 已承载的内容。

#### sub description 规范（权威在 Schema）

Read [SubEvent.md](../../../00_init/Schema/剧情/SubEvent.md)「description 撰写契约」——节拍级粒度、title 叙事短名规范、「写/不写」清单与正反例均以该节为准；生成时对照其正反例自检。

### 3. 占位物化（缺口 → 占位节点）

对每个 sub 的链条 `IllusDesign←appears_as←sub→anchored_at→Scene` 逐环检查，缺则占位：

| 缺口 | 占位节点（cypher 要点） |
|---|---|
| 空间不存在（新房间/新位置） | `CREATE (sp:Spot {id,name,kind:'zone',description})` + `(l)-[:part_of]->(sp)`（Location 必已存在，否则走入口核验报错） |
| 机位不存在 | `CREATE (sc:Scene {id,status:0,name,scene_type})` + `(sp)-[:realizes]->(sc)` |
| 服装套不存在 | `CREATE (cs:CostumeStyle {id,status:0,name,vibe})` + `(ch)-[:has_costume]->(cs)`（占位即挂归属边） |
| 形象版本不存在 | `CREATE (idn:IllusDesign {id,status:0})` + `(cs)-[:outfit_for]->(idn)` |
| 着装可继承 | 不占位：`appears_as` 直接挂兄弟 sub 的既有 IllusDesign |

**着装优先级**：兄弟 sub 继承 > CostumeStyle 占位 > IllusDesign 占位。**空间/着装叙事决策（哪个房间、哪套衣服）在本层拍定**——占位节点的 name 即决策载体，命名对照 [references/占位命名规范.md](references/占位命名规范.md)（四类命名模式 + 查重自检——占位与真身重名 = 图上两节点打架）。

### 4. 逐 event 拍板 + 组装建议 JSON

**一 Event 一题**（保持必问）：每题摆出该事件完整方案（0/1/N 个 sub + 各自 anchored_at 目标〔既有/占位标明〕+ appears_as 目标〔继承/占位标明〕+ 时间插值 + description 要点），用户整体拍板（可改细节后接受）。范围内事件按时间序逐个过。

全部拍板后组装建议 JSON（**顺序：占位节点 → 边**，节点先于边）：

- 项结构 `{check, priority, reason, content, cypher, source:'event-stager'}`；priority：占位 high（生产链待消化）、其余 medium。
- check 取值：
  - `S1_placeholder_node` — 占位 Spot/Scene/CostumeStyle/IllusDesign；
  - `S2_subevent` — SubEvent + refines + anchored_at + appears_as 一体；
  - `S3_fact_reveal` — 读者侧揭示场合拍板（`SubEvent ─reveals→ Hook`）：拆 sub 时逐 sub 判断该场戏是否使读者知晓某既有 Hook（该 Hook 尚无 reveals 或本次有叙事增量）——揭示边挂 sub（演出发生在机位层，揭示时刻同层）；**源为 Event 或目标为 Lore 均违规**；sub 被 sync 级联重细化时边随删、重拆重拍；并入该 event 的拍板题确认，不单独立题；
  - `S4_gap_fix` — 确定性缺口修复（involved/occurs_at 补边，仅当实体在图只缺边；实体缺失一律报错不走此类）。
- **写后复查（内容层，LLM 判定两项）**：① 每个 event 的 sub 时间与父 time 及相互先后因果相容（允许合理重叠）；② 同机位同角色着装一致（EA3 口径）。发现问题就地修正后再落盘。（EA5 违规形态、机位名引用等机械项由体检与 lint 机器兜底，不在文档层重复检查。）
- **写后复查（语句层，提交门槛）**：落盘后立即跑 `$SUGGEST_LINT <文件路径>`——exit 0 = 全 PASS；任何 FAIL 按输出提示就地改写 cypher、覆盖重写、重跑至全 PASS（dashboard 执行侧有同规格兜底，FAIL 会在采纳时被 400 拒绝）。

### cypher 模板（照抄改值）

> **语句自包含铁律**：`;` 分隔的每条语句是独立查询，**变量不跨语句延续**——挂边语句的两端点都在**本语句内**先 `MATCH (x:Label {id:'…'})` 绑定，MERGE 边里只用裸变量；MERGE 端点写成 `(y:Label {id:'…'})` 锚定形态直接出现时，未命中会**整 pattern 重建**出重复 id 节点（历史事故形态）。每个分号独占行尾；cypher 字段不携带 `//` 注释（写在 reason）；同一实体 id 在节点语句与挂边语句中是同一字面值。机器护栏 = `$SUGGEST_LINT`。

```
// ── 占位节点：节点本体与挂边各自独立语句，挂边两端点各自 MATCH 绑定 ──
// ⚠ 字段名对照 00_init/Schema/ 对应节点文件核对（表外字段一律不写）
// Spot 占位——节点本体
CREATE (sp:Spot {id:'<snowflake>'}) SET sp.name='<地点名>-<区域>', sp.kind='zone', sp.description='<一句话>';
// part_of 边（<snowflake> = 上方节点语句同一 id）
MATCH (l:Location {id:'<loc_id>'}) MATCH (sp:Spot {id:'<snowflake>'}) MERGE (l)-[r:part_of]->(sp) ON CREATE SET r.sync=false;
// Scene 占位——节点本体
CREATE (sc:Scene {id:'<snowflake>'}) SET sc.name='<机位名>', sc.scene_type='<类型>', sc.status=0;
// realizes 边（Spot 可为既有或上方占位）
MATCH (sp:Spot {id:'<spot_id_既有或上方占位>'}) MATCH (sc:Scene {id:'<snowflake>'}) MERGE (sp)-[r:realizes]->(sc) ON CREATE SET r.sync=false;
// CostumeStyle 占位——节点本体
CREATE (cs:CostumeStyle {id:'<snowflake>'}) SET cs.name='<着装名>', cs.vibe='<调性一句话>', cs.status=0;
// has_costume 归属边（占位即挂——禁止孤儿占位）
MATCH (ch:Character {id:'<char_id>'}) MATCH (cs:CostumeStyle {id:'<snowflake>'}) MERGE (ch)-[r:has_costume]->(cs) ON CREATE SET r.sync=true;
// IllusDesign 占位——节点本体
CREATE (idn:IllusDesign {id:'<snowflake>'}) SET idn.status=0;
// outfit_for 边（CostumeStyle 可为既有或上方占位）
MATCH (cs:CostumeStyle {id:'<cs_id_既有或上方占位>'}) MATCH (idn:IllusDesign {id:'<snowflake>'}) MERGE (cs)-[r:outfit_for]->(idn) ON CREATE SET r.sync=true;
// ── S2 SubEvent：本体+refines 一体语句；anchored_at / appears_as 各自独立语句 ──
MATCH (e:Event {id:'<parent_id>'})
MERGE (sub:SubEvent {id:'<snowflake>'})
ON CREATE SET sub.title='<父title> · <叙事短名（非机位名）>', sub.time='<插值时间>',
              sub.description='<2~4 分句节拍链，规范见 SubEvent.md 撰写契约>'
MERGE (e)-[r:refines]->(sub) ON CREATE SET r.sync=true;
MATCH (sub:SubEvent {id:'<snowflake_同上>'}) MATCH (scn:Scene {id:'<scene_id_既有或本建议占位>'})
MERGE (sub)-[a:anchored_at]->(scn) ON CREATE SET a.sync=false;
MATCH (sub:SubEvent {id:'<snowflake_同上>'}) MATCH (il:IllusDesign {id:'<illus_id_继承既有或本建议占位>'})
MERGE (sub)-[ap:appears_as]->(il) ON CREATE SET ap.sync=false, ap.detail='<继承：同父兄弟着装 / 占位：新套装待消化>';
// ── S4 缺口修复：补边（实体在图只缺边时）──
MATCH (ch:Character {id:'<char_id>'}) MATCH (e:Event {id:'<event_id>'}) MERGE (ch)-[r:involved]->(e) ON CREATE SET r.sync=false;
MATCH (e:Event {id:'<event_id>'}) MATCH (l:Location {id:'<loc_id>'}) MERGE (e)-[r:occurs_at]->(l) ON CREATE SET r.sync=false;
```

- 边 sync 语义：outfit_for/refines/has_costume=true（细化时级联下游）；part_of/realizes/anchored_at/appears_as=false（Schema 规定恒 false，演出绑定不级联）。
- 多语句 `;`+换行分隔、先节点后边；MERGE 幂等；id 用 `$SF_GEN -n 1 -q` 逐个生成。

## 参考文档

- [references/微演出模式库.md](references/微演出模式库.md) — §2 第 4 步校验时读（十一种模式范式 + 不拆反例 + 自检清单）
- [references/占位命名规范.md](references/占位命名规范.md) — §3 占位物化时读（四类命名模式 + 查重自检）
- [Schema/剧情/](../../../00_init/Schema/剧情/)（Event/SubEvent/Hook/Lore）/ [Schema/场景美术/](../../../00_init/Schema/场景美术/) / [Schema/角色美术/](../../../00_init/Schema/角色美术/)
