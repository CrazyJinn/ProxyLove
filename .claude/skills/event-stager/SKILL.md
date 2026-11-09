---
name: event-stager
description: |
  事件细化落地层——输入一个/多个 Event（id / title / 时间窗），四步推进：
  ①前置核验（发现确定性缺口：实体在图只缺边 → 转 S4 缺口修复建议，实体不在图
  → 报错列出，不代建）；②探索演出资源（char 立绘链 /
  location scene 链）并拆解 SubEvent（戏剧节拍分析→动作与状态变化分析→
  演出价值判断→模式库校验——模式只做查遗漏，不做生成依据）；
  ③占位物化——为每个 sub 构建 IllusDesign←appears_as←SubEvent→anchored_at→Scene
  链条，缺口建占位节点（status=0）：Spot/Scene/CostumeStyle/IllusDesign 均可建
  （叙事侧拍定哪个房间哪套衣服）；④逐 event 询问确认 + 产出建议 JSON（人工经
  dashboard 写回）。多轮交互一次一问、每问附推荐；单轮至多 3 个 event。在用户说
  「细化」「stager」「这批事件细化一下」或给出事件范围要求推进机位层时使用。
  不建 Event/Info/Choice/Location/Character（缺叙事基础实体一律报错，见 §1 入口核验）。
argument-hint: <event id列表 | 事件title列表 | 时间窗>
arguments:
  - events
allowed-tools: Read, Bash, Write
---

# 事件细化落地（event-stager）

目标：把粗粒度 Event 物化成机位级演出段（SubEvent），并把演出所需实体**全部占位物化**
（需求细化层——演出侧叙事决策在本层发生，创建权就在本层）。缺口处置一律
「占位节点（status=0）」——占位在图上的位置自带需求上下文，可被独立消化。

> **交互通道（铁律）**：多轮交互一次一问、每问附可归因推荐；用户逐 event 拍板后组装
> **建议 JSON** 落盘 `02_剧情数据/<日期>_round<N>_<主题>_stager_建议.json`——必须
> `_建议.json` 结尾，dashboard「📥 补全建议」弹窗按此 glob 拾取最新 3 个文件，落盘
> 即提交（不接收推送），人工经弹窗写回。**全程零直接图写入**。顶层数组，逐项
> `{check, priority, reason, content, cypher}` + `source:'event-stager'`（check 取值见
> §4）；一条建议的 cypher 可多语句（`;`+换行分隔，先节点后边），**每条语句自包含
> ——边 pattern 两端点变量必须在本语句内 MATCH/CREATE 绑定**（变量不跨 `;` 语句
> 延续；MERGE 边端点未先绑定会在未命中时整 pattern 重建出重复节点，见
> [references/多语句cypher与MERGE绑定语义.md](references/多语句cypher与MERGE绑定语义.md)），
> 落盘后必须 `$SUGGEST_LINT` 全 PASS；**禁止夹带自造的
> 校验节点**（必然孤儿）；执行校验由用户回报后只读回查完成。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
SF_GEN="python ${CLAUDE_SKILL_DIR}/../../scripts/snowflake_base62.py"
ROUND="python ${CLAUDE_SKILL_DIR}/../../scripts/suggest_round.py"    # 轮次推导（共享计数器）
PREFLIGHT="python ${CLAUDE_SKILL_DIR}/scripts/preflight.py"          # 前置核验（范围+契约+资源）
SUGGEST_LINT="python ${CLAUDE_SKILL_DIR}/../../scripts/suggest_lint.py"  # 建议语句级护栏（MERGE 绑定语义）
OUTPUT_DIR="02_剧情数据"
```

## 职责边界（铁律级）

- **创建域 = 演出域四类占位 + SubEvent**：
  1. `SubEvent` 节点 + `refines` 边（Event→SubEvent，sync=true）；
  2. `anchored_at` 边（SubEvent→Scene——**Scene 不存在时建 Scene 占位** status=0，
     挂 realizes 到既有 Spot；Spot 也不存在时建 Spot 占位）；
  3. `appears_as` 边（SubEvent→IllusDesign——优先继承父/兄弟 sub 着装；着装套不
     存在时建 CostumeStyle 占位、形象版本不存在时建 IllusDesign 占位）；着装占位
     **必须同时挂 `Character→has_costume` 归属边**（2026-11-05 约定）——归属角色
     在拍板上下文恒明确（该着装缺口所属的 involved 角色），孤儿占位会让 dashboard
     角色链图/叙事图全链路不可见、体检 E1 误报「缺出场形象」；
  4. 确定性缺口修复类（S4_gap_fix，§1 发现 → §4 拍板 → dashboard 写回）：
     缺 involved/occurs_at 补边（仅当实体在图、只缺边；实体不在图走 §1 入口
     核验报错，不代建）；
- **不建**：Event / Info / Choice / Location / Character。不产任何真资产（图片/
  room.yml 不在本层）。
- **sub description 不引用占位字段**：只写演出内容（动作/情绪基调/
  同事件内前后 sub 衔接，按 §2 内容规范），机位信息一律由 anchored_at 边承载
  ——占位 Scene 后续改名/改字段不造成 description 漂移（§方案 Q4 拍板）。
- **一题一答且一 Event 一题**：缺口修复逐条问；sub+占位方案按 Event 聚合成一题
  整体拍板。facts 自己查，decisions 才问用户。

## 模型（写 Cypher 前必读）

```
人工层：  Character ─involved→ Event ←occurs_at─ Location   （入口核验的前提）
          Section ─includes{order}→ Event                    ← 分节/时间轴只碰 Event
细化层：  Event ─refines{sync:true}→ SubEvent                ← 1:N，本 skill 产
          SubEvent ─anchored_at→ Scene                       ← 缺则建 Scene 占位
          SubEvent ─appears_as→ IllusDesign                  ← 继承或占位
空间链：  Location ─part_of→ Spot ─realizes→ Scene           ← Spot 缺则建占位
着装链：  Character ─has_costume→ CostumeStyle ─outfit_for→ IllusDesign ← 缺则建占位（占位即挂归属边）
```

- SubEvent 属性仅 id/title/time/description；**无** status/type/involved/occurs_at。
- 占位节点属性：id + status=0 + 最小必要字段（Spot: name/kind；Scene: name/
  scene_type；CostumeStyle: name/outfit_style；IllusDesign: status + adaptation_notes
  可空）——完整字段下限待消化实践反馈后固化，当前给名称即可被消化。
- **Event 直挂 anchored_at/appears_as 为违规**（EA5 体检兜查）。
- 删父 Event 连带删其全部 sub（dashboard event_crud 已实现级联）。

## 工作流（四步）

> S4 缺口修复走「§1 **发现** → §4 拍板 → dashboard 写回」闭环，第 1 步只发现
> 不修复（全程零直接图写入）。

### 1. 前置核验（发现确定性缺口）

跑：

```bash
$PREFLIGHT --ids <id1,id2> [--titles t1,t2] [--window 起,止] [--json]
```

一次跑出四样 facts（全部只读，不用现场写范围解析 cypher）：

- **范围解析**：命中事件清单（id/title/time/occurs_at/involved），复述 N 个
  事件 + 时间跨度再进下一步；
- **入口核验（权威表述，全 skill 唯一）**：`verdict=FAIL`（缺 occurs_at Location /
  缺 involved Character）→ **先分诊**（preflight 的 FAIL 不区分下述两种，需自查）：
  缺的实体**在图、只缺边** → 按创建域第 4 条转 §4 的 `S4_gap_fix` 补边建议，
  流程继续；实体**不在图** → **报错停止**，脚本 `failures` 已逐事件列出缺失项，
  **不代建叙事基础实体**——Event/Info/Choice/Location/Character 均不在本 skill
  创建域，缺口回 event-ideator 层补。title/description 提及实体未建档同理
  （LLM 读文判断，实体是否在图对照 `assets` 段核查）；
- **批次切分**：单轮上限 3 个 event（批量约束），超出时脚本 `batch` 段已切好
  （本轮时间最早 3 个，余者列入汇报「下轮可细化」）；
- **演出资源现状**：`assets` 段（每 involved char 立绘链 / 每 involved char 着装
  直查表（`costumes`——含 status=0 占位，**同缺口勿重复建占位**）/ 每 location
  空间链）——第 2 步拆解的全部 facts，不必重查。

### 2. 探索演出资源 + 拆解 SubEvent

**探索**（facts 由 §1 preflight `assets` 段带出）：

- 立绘链现状（每 involved Character）：Character →AppearanceStyle→ DesignSheet → IllusDesign
  ←outfit_for← CostumeStyle（Schema 正源四段链）——着装继承与占位判断的依据；
  着装全集另见 `costumes` 段（has_costume 直查）——四段链查不到无 DesignSheet 的
  占位着装，建占位前先对表防重；
- 空间链现状（每 occurs_at Location）：Spot →realizes→ Scene——机位选用与
  占位判断的依据。信息不足时按需补查（查询形态见 preflight.py 源码）。

**拆解流程（六步固定，模式库在末位做校验与补遗——先找演出价值，再对模式查遗漏）**：

1. **戏剧节拍分析**：从事件 title/description 理解事件内部的戏剧发展，识别
   值得表现的节拍（铺垫/触发/反应/释放/余韵，如告白=犹豫→拿出礼物→说出
   心意→沉默→接受/拒绝→新相处状态）。只识别潜在演出内容，**不要求每个
   节拍都生成 sub**；
2. **动作与状态变化分析**：把值得表现的节拍转化为具体剧情动作——逐项过：
   谁采取行动、行动对象、发生时间与空间、产生什么结果、是否带来可感知的
   信息/情绪/关系/状态变化（未带来变化的动作不拆）。description 落**节拍级**——2~4 个分句、
   每分句一个节拍并点明互动方向（粒度规范见下方内容规范）——道具、环境、台词、动作细节全部属
   novelist 即兴域；
3. **独立演出价值判断**：对每个候选动作按下方拆解判据裁决拆/不拆（防过拆
   与欠拆两个极端）；
4. **模式库校验**：对照 [references/微演出模式库.md](references/微演出模式库.md)
   检查拆分方案——模式提供经验与查遗漏（有没有漏拆的到场/物件交互，或
   拆出来的其实是不拆反例），**不强制每个 sub 匹配一个模式**；命中多模式
   不等于要生成多个 sub，可组合参考；
5. **SubEvent 生成**：生成 sub 及 anchored_at/appears_as 关系；
6. **演出验收**：时间符合因果先后、人物连续性、动作完整性（每个 sub 能说清
   「谁对谁做了什么」）、不重复表达父 Event 已承载的内容。

**拆解判据**（演出价值，非既有 ink——细化在前、ink 在后，禁止把后续产物当依据）：

- **演出价值判据**：铺垫→触发→释放→余韵 至少占一环，**且 sub 必须带来可感知的
  信息/情绪/关系/状态变化**——仅存在一个动作不构成拆分理由；无价值不拆——
  挤水分与拆段都是伤害，宁少勿滥；纯过渡/独处/状态变化单段即足；
- **时间推导**：sub 时间由上下文推导（到场在主活动前、离开在收尾后、换区按
  位移节奏），**不虚构精确时间**——不设固定窗幅，只要求与父事件及邻接 sub
  因果先后相容，允许合理重叠（如并行发生的事）；
- **拆分数量**：遵循实际剧情密度，防两个极端——**过拆**（普通动作、每句
  对话都拆成 sub）与**欠拆**（多个独立戏剧阶段塞进一个 sub）；对峙类高密度
  演出优先 1 个 sub，但独立触发/反转/爆发阶段显著时可拆多段；
- **模式参考**：十一种微演出模式（到场/离开/换区/对峙/独白/并行小事/目击/误认/
  物件交互/情绪转变/决策）各含适用判据、典型拆解形态、项目实感示例与
  **不拆反例**；拆解决策对照模式库而非现想，文末拆解自检清单在落建议 JSON
  前过一遍。

**sub description 内容规范**（字段级，按实际情况填写、非必要不强制）：

| 内容 | 要求 |
|---|---|
| 角色动作 | **必填**（动作完整性：能说清「谁对谁做了什么」） |
| 动作对象 | 有对象时填写 |
| 时间 | 由上下文推导，不虚构精确值 |
| 情绪基调 / 人物站位 / 到离场方式 / 行动结果 | 有表现价值时填写 |
| 前后衔接 | 存在必要衔接时填写，**仅限同事件内前后 sub** |

**参与人不入 description**：sub 的参与角色由父 Event 的 `involved` 边唯一承载
（图是唯一事实来源，description 写「参与：…」即第二套事实、必与图漂移）；
description 只写动作/基调/衔接等演出内容，不列参与人名单。

**description 颗粒度（结构决策层契约，2026-11-09 拍板；当日三次迭代后定稿：节拍级）**：sub 只承载演出结构
决策——拆分粒度、机位归属、时序插值、**节拍链与互动方向**。description 为**2~4 个分句**（分号分隔），
每分句一个节拍（谁+做了什么），并**点明互动方向**（谁主动、谁反应、对视/先后/呼应等）；
**不写字段头**（「动作：」「变化：」「基调：」等一律不写）、**不写台词**、**不写道具与环境细节**、
**不写情绪氛围**。粒度标准：novelist 拿它知道**该演哪几个节拍、谁主导**，但不知道**具体怎么演**；
写得更细 = 越权替 novelist 排练，压得更简 = 节拍链断裂、novelist 无锚可依（单句版实测效果不佳，
2026-11-09 v3 复盘）。

sub 写成微剧本 = 三重绑架下游：novelist 被迫消化图上的细节（含物理瑕疵）；
道具台词进了图却不进 novelist 取材指纹（sub 不受 stale 保护，两层无感漂移）；
改一句台词要动图→小说→ink 三层。sub 是结构决策层，不是初稿层。

**四不**：不重复父 Event 已表达的内容；不写机位名（机位信息只走 anchored_at
边）；不塞具体镜头设计（近景/特写切换是剧本分镜层的事，sub 只到「机位级
演出段」粒度）；人物状态变化不写成冗长自然语言。
衔接**仅限同事件内前后 sub**——禁止指涉其他事件（跨事件因果/时序由 leads_to 边
与 Event.time 承载，description 写「同日下午」「当晚」等跨事件相对时间词即违规，
时间唯一承载是 Event.time）。

**职责边界提醒**：SubEvent ─anchored_at→ Scene 是**严格 1:1**（一个 sub 一个机位）。
sub 描述剧情动作（谁做了什么、什么变化），Scene 只管机位/背景画面——人物姿势、
表情、位置属于立绘与演出指令层，不塞进 Scene，也不在 sub 里做镜头设计。

### 3. 占位物化（缺口 → status=0 占位）

对每个 sub 的链条 `IllusDesign←appears_as←sub→anchored_at→Scene` 逐环检查，缺则占位：

| 缺口 | 占位节点（cypher 要点） |
|---|---|
| 空间不存在（新房间/新位置） | `CREATE (sp:Spot {id,status:0,name,kind:'zone'})` + `(l)-[:part_of]->(sp)`（Location 必已存在，否则走入口核验报错） |
| 机位不存在 | `CREATE (sc:Scene {id,status:0,name,scene_type})` + `(sp)-[:realizes]->(sc)` |
| 服装套不存在 | `CREATE (cs:CostumeStyle {id,status:0,name,outfit_style})` + `(ch)-[:has_costume]->(cs)`（归属角色 = 该着装缺口所属 involved 角色，占位即挂边） |
| 形象版本不存在 | `CREATE (idn:IllusDesign {id,status:0,adaptation_notes})` + `(cs)-[:outfit_for]->(idn)` |
| 着装可继承 | 不占位：`appears_as` 直接挂兄弟 sub 的既有 IllusDesign |

**着装优先级**：兄弟 sub 继承 > CostumeStyle 占位 > IllusDesign 占位（继承优先，
占位只补缺口）。**空间/着装叙事决策（哪个房间、哪套衣服）在本层拍定**——占位节点
的 name 即决策载体，命名对照 [references/占位命名规范.md](references/占位命名规范.md)
（从图上实存节点归纳的四类命名模式 + 查重自检——占位与真身重名 = 图上两节点打架）。

### 4. 逐 event 询问 + 组装建议 JSON

**一 Event 一题**：每题摆出该事件完整方案（0/1/N 个 sub + 各自 anchored_at 目标
（既有/占位标明）+ appears_as 目标（继承/占位标明）+ 时间插值 + description 要点），用户整体拍板（可改细节后
接受）。范围内事件按时间序逐个过。

全部拍板后组装建议 JSON（**顺序：占位节点 → 边**，节点先于边）：

- 项结构 `{check, priority, reason, content, cypher, source:'event-stager'}`；
- check 取值：`S1_placeholder_node`（占位 Spot/Scene/CostumeStyle/IllusDesign）、
  `S2_subevent`（SubEvent+refines+anchored_at+appears_as 一体）、
  `S4_gap_fix`（确定性缺口修复：involved/occurs_at 补边——仅当图上实体确实存在
  只是边缺失时才走此类，实体缺失一律报错不走此类）；
- priority：占位 high（生产链待消化）；其余 medium；
- 落盘 `02_剧情数据/<日期>_round<N>_<主题>_stager_建议.json`，轮次 N 由 `$ROUND`
  推导（共享计数器全量取 max+1，勿手写文件名扫描——排序取最新会跳号）；
- **写后复查（建议 JSON 内容层面）**：每个 event 的 sub 时间符合因果与先后约束
  （与父 time 相容，允许合理重叠）/ 同机位同
  角色着装一致（EA3 口径）/ sub 顺序与父 time 相容 / description 无机位名等占位字段
  引用 / EA5 违规形态零出现（Event 直挂两边）。复查发现的问题就地修正后再落盘。
- **写后复查（建议 JSON 语句层，提交门槛）**：落盘后立即跑
  `$SUGGEST_LINT <文件路径>`——exit 0 = 全 PASS；任何 FAIL 按输出提示就地改写
  cypher、覆盖重写文件、重跑，直到全 PASS 才算提交（dashboard 执行侧有同规格
  兜底，FAIL 形态会在采纳时被 400 拒绝）。

### cypher 模板（照抄改值）

> **语句自包含铁律**（2026-11-02 重复 id 节点事故后的硬约束，详解见
> [references/多语句cypher与MERGE绑定语义.md](references/多语句cypher与MERGE绑定语义.md)）：
> ① `;` 分隔的每条语句是独立查询，**变量不跨语句延续**——挂边语句的两端点都在
> **本语句内**先 `MATCH (x:Label {id:'…'})` 绑定，MERGE 边里只用裸变量 `(x)`；
> ② MERGE 边端点不得写成 `(y:Label {id:'…'})` 锚定模式直接出现——未绑定的端点在
> MERGE 未命中时**整 pattern 重建**（新建只带 {id} 的重复节点 + 幽灵节点，即事故形态）；
> ③ 每个分号独占行尾（`;`+换行）；④ 写入建议 JSON 的 cypher 字段**不携带 `//` 注释
> 行**——注释写在建议 reason 或本文件（cypher 字段是机器载荷，注释只增漂移面；下方
> 注释仅是文档说明）；⑤ 同一实体的 id 在节点语句与挂边语句中是**同一字面值**（挂边
> 靠 MATCH 该 id 重新绑定）。

```
// ── 占位节点：节点本体与挂边各自独立语句，挂边两端点各自 MATCH 绑定 ──
// Spot 占位（空间缺口）——节点本体
CREATE (sp:Spot {id:'<snowflake>'}) SET sp.name='<地点名>-<区域>', sp.kind='zone', sp.description='<一句话>', sp.status=0;
// part_of 边（Spot 的 <snowflake> = 上方节点语句同一 id）
MATCH (l:Location {id:'<loc_id>'}) MATCH (sp:Spot {id:'<snowflake>'}) MERGE (l)-[r:part_of]->(sp) ON CREATE SET r.sync=true;
// Scene 占位（机位缺口）——节点本体
CREATE (sc:Scene {id:'<snowflake>'}) SET sc.name='<机位名>', sc.scene_type='<类型>', sc.status=0;
// realizes 边（Spot 可为既有或上方占位）
MATCH (sp:Spot {id:'<spot_id_既有或上方占位>'}) MATCH (sc:Scene {id:'<snowflake>'}) MERGE (sp)-[r:realizes]->(sc) ON CREATE SET r.sync=true;
// CostumeStyle 占位——节点本体
CREATE (cs:CostumeStyle {id:'<snowflake>'}) SET cs.name='<着装名>', cs.outfit_style='<风格>', cs.status=0;
// has_costume 归属边（占位即挂——归属角色 = 该着装缺口所属 involved 角色，禁止孤儿占位）
MATCH (ch:Character {id:'<char_id>'}) MATCH (cs:CostumeStyle {id:'<snowflake>'}) MERGE (ch)-[r:has_costume]->(cs) ON CREATE SET r.sync=true;
// IllusDesign 占位——节点本体
CREATE (idn:IllusDesign {id:'<snowflake>'}) SET idn.adaptation_notes='<着装补充>', idn.status=0;
// outfit_for 边（CostumeStyle 可为既有或上方占位）
MATCH (cs:CostumeStyle {id:'<cs_id_既有或上方占位>'}) MATCH (idn:IllusDesign {id:'<snowflake>'}) MERGE (cs)-[r:outfit_for]->(idn) ON CREATE SET r.sync=true;
// ── S2 SubEvent：本体+refines 一体语句；anchored_at / appears_as 各自独立语句 ──
MATCH (e:Event {id:'<parent_id>'})
MERGE (sub:SubEvent {id:'<snowflake>'})
ON CREATE SET sub.title='<父title> · <序号或短名>', sub.time='<插值时间>',
              sub.description='<节拍级：2~4 分句、每分句一个节拍并点明互动方向；不写字段头/台词/道具环境细节/氛围>'
MERGE (e)-[r:refines]->(sub) ON CREATE SET r.sync=true;
MATCH (sub:SubEvent {id:'<snowflake_同上>'}) MATCH (scn:Scene {id:'<scene_id_既有或本建议占位>'})
MERGE (sub)-[a:anchored_at]->(scn) ON CREATE SET a.sync=false;
MATCH (sub:SubEvent {id:'<snowflake_同上>'}) MATCH (il:IllusDesign {id:'<illus_id_继承既有或本建议占位>'})
MERGE (sub)-[ap:appears_as]->(il) ON CREATE SET ap.sync=false, ap.detail='<继承：同父兄弟着装 / 占位：新套装待消化>';
```

- 占位节点间边（part_of/realizes/outfit_for）sync=true（细化时级联下游）；sub 三边
  中 refines sync=true、anchored_at/appears_as sync=false（演出绑定不级联）。
- 多语句 `;`+换行分隔、先节点后边、每个分号独占行尾；MERGE 幂等；id 用 snowflake
  逐个生成（`$SF_GEN -n 1 -q`）。

## 参考文档

- [references/微演出模式库.md](references/微演出模式库.md) — §2 第 4 步校验时读（十一种模式范式+不拆反例+自检清单）
- [references/占位命名规范.md](references/占位命名规范.md) — §3 占位物化时读（四类命名模式+查重自检）
- [叙事基础.md](../../../00_init/Schema/叙事基础.md) / [场景美术.md](../../../00_init/Schema/场景美术.md) / [角色美术.md](../../../00_init/Schema/角色美术.md)
- 方法论溯源：工作区根《event-ideator与event-stager功能定稿方案.md》§3/§6/§8.2
