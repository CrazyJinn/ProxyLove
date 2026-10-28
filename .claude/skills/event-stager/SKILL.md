---
name: event-stager
description: |
  事件细化落地层（原 event-refiner 更名升级，吸收 event-precheck）——输入一个/多个
  Event（id 或 title），四步推进：①确定性缺口修复（缺 involved / 缺 occurs_at /
  提及实体未建档——白名单写入，逐题确认）；②探索演出资源（char 立绘链 / location
  scene 链）并拆解 SubEvent（到场/离开/换区按演出价值判据）；③占位物化——为每个
  sub 构建 IllusDesign←appears_as←SubEvent→anchored_at→Scene 链条，缺口建占位节点
  （status=0）：Spot/Scene/CostumeStyle/IllusDesign 均可建（叙事侧拍定哪个房间哪套
  衣服），替代旧「文本留单」；④逐 event 询问确认 + 产出建议 JSON（人工经 dashboard
  写回）。多轮交互一次一问、每问附推荐；单轮至多 3 个 event。在用户说「细化」「stager」
  「这批事件细化一下」或给出事件范围要求推进机位层时使用。不建 Event/Info/Choice
  （新事件走 event-ideator）；叙事基础缺口（Location/Character 缺）= 上游未完成，
  报错退回。
argument-hint: <event id列表 | 事件title列表 | 时间窗>
arguments:
  - events
allowed-tools: Read, Bash, Write
---

# 事件细化落地（event-stager）

目标：把粗粒度 Event 物化成机位级演出段（SubEvent），并把演出所需实体**全部占位物化**
（需求细化层——演出侧叙事决策在本层发生，创建权就在本层）。

> **前身**：event-refiner agent（已删除）——本 skill 吸收其全部职责并升级：缺口处置
> 从「文本留单派发」改为「占位节点（status=0）」，实现 agent（char-design/scene-design）
> 入口查询圈占位消化，占位在图上的位置自带需求上下文。
>
> **交互通道（铁律）**：多轮交互一次一问、每问附可归因推荐；用户逐 event 拍板后组装
> **建议 JSON** 落盘 `02_剧情数据/<日期>_round<N>_<主题>_stager_建议.json`，人工经
> dashboard「📥 补全建议」弹窗写回。**全程零直接图写入**。
>
> **输入契约（上游 event-ideator 的保证）**：进入本 skill 的事件，其 involved Character
> 与 occurs_at Location **必已在图上**（既有或 ideator 占位）。再遇叙事基础缺口 =
> 上游未完成 → **报错退回**（可操作错误：缺什么、退给谁补），不代建不跨层。

## 职责边界（铁律级）

- **创建域 = 演出域四类占位 + SubEvent**：
  1. `SubEvent` 节点 + `refines` 边（Event→SubEvent，sync=true）；
  2. `anchored_at` 边（SubEvent→Scene——**Scene 不存在时建 Scene 占位** status=0，
     挂 realizes 到既有 Spot；Spot 也不存在时建 Spot 占位）；
  3. `appears_as` 边（SubEvent→IllusDesign——优先继承父/兄弟 sub 着装；着装套不
     存在时建 CostumeStyle 占位、形象版本不存在时建 IllusDesign 占位）；
  4. 原白名单修复类：缺 involved/occurs_at 补边、提及未建档 Character/Location
     **报错退回 ideator**（不代建——叙事基础创建权在 ideator）；
  5. 演出型 Info 升格（Info→sub.description，Info 删除——保留/删除由用户拍板）。
- **不建**：Event / Info / Choice / Location / Character（前三归 ideator 创作域，
  后两叙事基础占位归 ideator）。不产任何真资产（图片/room.yml 归实现 agent）。
- **sub description 不引用占位字段**：只写演出内容（机位动作/参与人/情绪基调/
  邻接衔接），机位信息一律由 anchored_at 边承载——占位 Scene 后续被 scene-design
  改名/改字段不造成 description 漂移（§方案 Q4 拍板）。
- **一题一答且一 Event 一题**：缺口修复逐条问；sub+占位方案按 Event 聚合成一题
  整体拍板。facts 自己查，decisions 才问用户。

## 模型（写 Cypher 前必读）

```
人工层：  Character ─involved→ Event ←occurs_at─ Location   （上游保证在图）
          Section ─includes{order}→ Event                    ← 分节/时间轴只碰 Event
细化层：  Event ─refines{sync:true}→ SubEvent                ← 1:N，本 skill 产
          SubEvent ─anchored_at→ Scene                       ← 缺则建 Scene 占位
          SubEvent ─appears_as→ IllusDesign                  ← 继承或占位
空间链：  Location ─part_of→ Spot ─realizes→ Scene           ← Spot 缺则建占位
着装链：  CostumeStyle ─outfit_for→ IllusDesign              ← 缺则建占位
```

- SubEvent 属性仅 id/title/time/description；**无** status/type/involved/occurs_at。
- 占位节点属性：id + status=0 + 最小必要字段（Spot: name/kind；Scene: name/
  scene_type；CostumeStyle: name/outfit_style；IllusDesign: status + adaptation_notes
  可空）——完整字段下限**等实现 agent 消化体验反馈后固化**（§方案 Q3 拍板：等
  scene-design 拍），当前给名称即可被消化。
- **Event 直挂 anchored_at/appears_as 为违规**（EA5 体检兜查）。
- 删父 Event 连带删其全部 sub（dashboard event_crud 已实现级联）。

## 工作流（四步）

### 1. 解析范围 + 确定性缺口修复

```cypher
// 范围解析（id/title/时间窗 → id 列表，复述 N 个事件+时间跨度再进下一步）
MATCH (e:Event) WHERE e.id IN ['<id1>'] OR e.title IN ['<t1>']
  OR (e.time >= '<起>' AND e.time < '<止次日>')
RETURN e.id AS id, e.title AS title, e.time AS time ORDER BY e.time
```

- **上游契约核验**：范围内事件缺 occurs_at Location / 缺 involved Character →
  **报错退回**（明确列出：事件 id、缺什么、建议跑 event-ideator 补占位），
  本 skill 不代建叙事基础实体。title/description 提及实体未建档同理。
- **单轮上限 3 个 event**（§方案 8.3 批量约束）：超出分轮，本轮取时间最早的 3 个，
  其余列入汇报「下轮可细化」。

### 2. 探索演出资源 + 拆解 SubEvent

**探索**（facts 自己查）：

- 每个 involved Character 的立绘链现状：`MATCH (c:Character {id:'<id>'})-[:has_appearance]->(ds:DesignSheet)-[:produces]->(id:IllusDesign) OPTIONAL MATCH (cs:CostumeStyle)-[:outfit_for]->(id) RETURN …`——着装继承与占位判断的依据；
- 每个 occurs_at Location 的 scene 链现状：`MATCH (l:Location {id:'<id>'})-[:part_of]->(sp:Spot)-[:realizes]->(sc:Scene) RETURN sp.name, sp.id, sc.name, sc.id`——机位选用与占位判断的依据。

**拆解判据**（演出价值，非既有 ink——细化在前、ink 在后，禁止把下游产物当依据）：

- **到场规则**：「赴约/到访/首进场」性质 → 开场报到演出（接人/寒暄），时间=事件前 5~15 分钟插值；
- **换区规则**：叙事横跨 Location 内多子空间 → 按子空间分段各挂机位；单机位不拆；
- **离开规则**：冲突/尴尬/离别收尾 → 送别/收尾演出，时间=事件后 15~30 分钟插值；
- **演出价值判据**（铺垫→触发→释放→余韵）：无价值不拆——挤水分与拆段都是伤害，
  宁少勿滥；纯过渡/独处/状态变化单段即足。
- **模式参考**：常见微演出模式（到场/离开/换区/对峙/独白/并行小事/目击/误认）的
  拆解范式，决策时对照模式库而非现想（持续沉淀进本 skill 目录，暂无独立文件时
  以本节规则为准）。

**sub description 模板**（必填，不含机位名）：机位动作 / 到场离场方式 / 参与人 /
情绪基调 / 与邻接 sub 的衔接（承接什么引出什么）。

### 3. 占位物化（缺口 → status=0 占位）

对每个 sub 的链条 `IllusDesign←appears_as←sub→anchored_at→Scene` 逐环检查，缺则占位：

| 缺口 | 占位节点（cypher 要点） | 消化者 |
|---|---|---|
| 空间不存在（新房间/新位置） | `CREATE (sp:Spot {id,status:0,name,kind:'zone'})` + `(l)-[:part_of]->(sp)`（Location 必已存在，否则退回 ①） | scene-design |
| 机位不存在 | `CREATE (sc:Scene {id,status:0,name,scene_type})` + `(sp)-[:realizes]->(sc)` | scene-design |
| 服装套不存在 | `CREATE (cs:CostumeStyle {id,status:0,name,outfit_style})` | char-design |
| 形象版本不存在 | `CREATE (idn:IllusDesign {id,status:0,adaptation_notes})` + `(cs)-[:outfit_for]->(idn)` | char-design |
| 着装可继承 | 不占位：`appears_as` 直接挂兄弟 sub 的既有 IllusDesign | — |

**着装优先级**：兄弟 sub 继承 > CostumeStyle 占位 > IllusDesign 占位（继承优先，
占位只补缺口）。**空间/着装叙事决策（哪个房间、哪套衣服）在本层拍定**——占位节点
的 name 即决策载体。

### 4. 逐 event 询问 + 组装建议 JSON

**一 Event 一题**：每题摆出该事件完整方案（0/1/N 个 sub + 各自 anchored_at 目标
（既有/占位标明）+ appears_as 目标（继承/占位标明）+ 时间插值 + description 要点）
+ Info 升格项（如有），用户整体拍板（可改细节后接受）。范围内事件按时间序逐个过。

全部拍板后组装建议 JSON（**顺序：占位节点 → 边**，节点先于边）：

- 项结构 `{check, priority, reason, content, cypher, source:'event-stager'}`；
- check 取值：`S1_placeholder_node`（占位 Spot/Scene/CostumeStyle/IllusDesign）、
  `S2_subevent`（SubEvent+refines+anchored_at+appears_as 一体）、
  `S3_info_upgrade`（Info 升格：建 sub + DETACH DELETE Info）、
  `S4_gap_fix`（原白名单修复：involved/occurs_at 补边——注意上游契约，仅当图上
  实体确实存在只是边缺失时才走此类，实体缺失一律退回不走此类）；
- priority：占位 high（生产链待消化）；其余 medium；
- 落盘 `02_剧情数据/<日期>_round<N>_<主题>_stager_建议.json`，轮次 N 共享计数器；
- **写后复查（建议 JSON 内容层面）**：每个 event 的 sub 时间连续无重叠 / 同机位同
  角色着装一致（EA3 口径）/ sub 顺序与父 time 相容 / description 无机位名等占位字段
  引用 / EA5 违规形态零出现（Event 直挂两边）。复查发现的问题就地修正后再落盘。

### cypher 模板（照抄改值）

```
// Spot 占位（空间缺口）
CREATE (sp:Spot {id:'<snowflake>'}) SET sp.name='<地点名>-<区域>', sp.kind='zone', sp.description='<一句话>', sp.status=0;
MATCH (l:Location {id:'<loc_id>'}) MERGE (l)-[r:part_of]->(sp) ON CREATE SET r.sync=true;
// Scene 占位（机位缺口）
CREATE (sc:Scene {id:'<snowflake>'}) SET sc.name='<机位名>', sc.scene_type='<类型>', sc.status=0;
MATCH (sp:Spot {id:'<spot_id>'}) MERGE (sp)-[r:realizes]->(sc) ON CREATE SET r.sync=true;
// CostumeStyle 占位
CREATE (cs:CostumeStyle {id:'<snowflake>'}) SET cs.name='<着装名>', cs.outfit_style='<风格>', cs.status=0;
// IllusDesign 占位（挂 outfit_for）
CREATE (idn:IllusDesign {id:'<snowflake>'}) SET idn.adaptation_notes='<着装补充>', idn.status=0;
MATCH (cs:CostumeStyle {id:'<cs_id>'}) MERGE (cs)-[r:outfit_for]->(idn) ON CREATE SET r.sync=true;
// SubEvent + 三边（S2 一体）
MATCH (e:Event {id:'<parent_id>'})
MERGE (sub:SubEvent {id:'<snowflake>'})
ON CREATE SET sub.title='<父title> · <序号或短名>', sub.time='<插值时间>',
              sub.description='<演出内容（模板五要素，不含机位名）>'
MERGE (e)-[r:refines]->(sub) ON CREATE SET r.sync=true
MERGE (sub)-[a:anchored_at]->(scn:Scene {id:'<scene_id_既有或占位>'}) ON CREATE SET a.sync=false
MERGE (sub)-[ap:appears_as]->(il:IllusDesign {id:'<illus_id_继承或占位>'}) ON CREATE SET ap.sync=false,
  ap.detail='<继承：同父兄弟着装 / 占位：新套装待 char-design 消化>';
// Info 升格（S3）
MATCH (e:Event {id:'<parent_id>'})
MERGE (sub:SubEvent {id:'<snowflake>'})
ON CREATE SET sub.title='<Info.title>', sub.time='<e.time>', sub.description='<Info.content>'
MERGE (e)-[r:refines]->(sub) ON CREATE SET r.sync=true
MERGE (sub)-[a:anchored_at]->(scn:Scene {id:'<scene_id>'}) ON CREATE SET a.sync=false
MERGE (i:Info {id:'<info_id>'}) DETACH DELETE i;
```

- 占位节点间边（part_of/realizes/outfit_for）sync=true（细化时级联下游）；sub 三边
  中 refines sync=true、anchored_at/appears_as sync=false（演出绑定不级联）。
- 多语句 `;` 分隔先节点后边；MERGE 幂等；id 用 snowflake 逐个生成。

## 交接契约

| 上游 | 接什么 |
|---|---|
| event-ideator / 人工 / nrt-gap-filler | 粗 Event（**involved/occurs_at 保证在图**，含占位） |
| event-ideator | 叙事基础缺口退回通道（本 skill 报错 → ideator 补占位） |

| 下游 | 交什么 |
|---|---|
| char-design | CostumeStyle/IllusDesign 占位（status=0）+ 占位 Character 的外貌链兜底创建 |
| scene-design | Spot/Scene 占位（status=0）+ room.yml 细化 |
| plot-design / novelist | 无直接交接——经图消费（includes→refines→sub→anchored_at/appears_as） |

novelist 的即停即报（集合外机位）仍是最后防线：发现漏细化时上报，由本 skill 补细化。

## 参考文档

- [叙事基础.md](../../../00_init/Schema/叙事基础.md) / [场景美术.md](../../../00_init/Schema/场景美术.md) / [角色美术.md](../../../00_init/Schema/角色美术.md)
- [nrt-gap-filler/SKILL.md](../nrt-gap-filler/SKILL.md) — 建议 JSON 契约母本
- 方法论溯源：工作区根《event-ideator与event-stager功能定稿方案.md》§3/§6/§8.2
