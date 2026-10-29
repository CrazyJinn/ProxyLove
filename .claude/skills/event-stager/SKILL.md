---
name: event-stager
description: |
  事件细化落地层——输入一个/多个 Event（id / title / 时间窗），四步推进：
  ①前置核验+确定性缺口修复（缺 involved / 缺 occurs_at：实体在图只缺边 → 补边，
  实体不在图 → 报错列出，不代建）；②探索演出资源（char 立绘链 /
  location scene 链）并拆解 SubEvent（对照微演出模式库，按演出价值判据）；
  ③占位物化——为每个 sub 构建 IllusDesign←appears_as←SubEvent→anchored_at→Scene
  链条，缺口建占位节点（status=0）：Spot/Scene/CostumeStyle/IllusDesign 均可建
  （叙事侧拍定哪个房间哪套衣服）；④逐 event 询问确认 + 产出建议 JSON（人工经
  dashboard 写回）。多轮交互一次一问、每问附推荐；单轮至多 3 个 event。在用户说
  「细化」「stager」「这批事件细化一下」或给出事件范围要求推进机位层时使用。
  不建 Event/Info/Choice/Location/Character；范围内事件缺叙事基础实体（缺
  occurs_at / 缺 involved）时报错列出，不代建。
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
> §4）；一条建议的 cypher 可多语句（`;`+换行分隔，先节点后边）；**禁止夹带自造的
> 校验节点**（必然孤儿）；执行校验由用户回报后只读回查完成。
>
> **入口核验**：范围内事件缺 occurs_at Location / 缺 involved Character → **报错停止**
> （逐事件列出缺失项），不代建叙事基础实体——Event/Info/Choice/Location/Character
> 均不在本 skill 创建域。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
SF_GEN="python ${CLAUDE_SKILL_DIR}/../../scripts/snowflake_base62.py"
ROUND="python ${CLAUDE_SKILL_DIR}/../../scripts/suggest_round.py"    # 轮次推导（共享计数器）
PREFLIGHT="python ${CLAUDE_SKILL_DIR}/scripts/preflight.py"          # 前置核验（范围+契约+资源）
OUTPUT_DIR="02_剧情数据"
```

## 职责边界（铁律级）

- **创建域 = 演出域四类占位 + SubEvent**：
  1. `SubEvent` 节点 + `refines` 边（Event→SubEvent，sync=true）；
  2. `anchored_at` 边（SubEvent→Scene——**Scene 不存在时建 Scene 占位** status=0，
     挂 realizes 到既有 Spot；Spot 也不存在时建 Spot 占位）；
  3. `appears_as` 边（SubEvent→IllusDesign——优先继承父/兄弟 sub 着装；着装套不
     存在时建 CostumeStyle 占位、形象版本不存在时建 IllusDesign 占位）；
  4. 确定性缺口修复类：缺 involved/occurs_at 补边（仅当实体在图、只缺边）；实体
     不在图 → 报错列出，不代建；
  5. 演出型 Info 升格（Info→sub.description，Info 删除——保留/删除由用户拍板）。
- **不建**：Event / Info / Choice / Location / Character。不产任何真资产（图片/
  room.yml 不在本层）。
- **sub description 不引用占位字段**：只写演出内容（机位动作/参与人/情绪基调/
  邻接衔接），机位信息一律由 anchored_at 边承载——占位 Scene 后续改名/改字段
  不造成 description 漂移（§方案 Q4 拍板）。
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
着装链：  CostumeStyle ─outfit_for→ IllusDesign              ← 缺则建占位
```

- SubEvent 属性仅 id/title/time/description；**无** status/type/involved/occurs_at。
- 占位节点属性：id + status=0 + 最小必要字段（Spot: name/kind；Scene: name/
  scene_type；CostumeStyle: name/outfit_style；IllusDesign: status + adaptation_notes
  可空）——完整字段下限待消化实践反馈后固化，当前给名称即可被消化。
- **Event 直挂 anchored_at/appears_as 为违规**（EA5 体检兜查）。
- 删父 Event 连带删其全部 sub（dashboard event_crud 已实现级联）。

## 工作流（四步）

### 1. 前置核验 + 确定性缺口修复

跑：

```bash
$PREFLIGHT --ids <id1,id2> [--titles t1,t2] [--window 起,止] [--json]
```

一次跑出四样 facts（全部只读，不用现场写范围解析 cypher）：

- **范围解析**：命中事件清单（id/title/time/occurs_at/involved），复述 N 个
  事件 + 时间跨度再进下一步；
- **入口核验**：`verdict=FAIL`（缺 occurs_at / 缺 involved）→ **报错停止**，
  脚本 `failures` 已逐事件列出缺失项；本 skill
  不代建叙事基础实体。title/description 提及实体未建档同理（LLM 读文判断，
  实体是否在图对照 `assets` 段核查）；
- **批次切分**：单轮上限 3 个 event（批量约束），超出时脚本 `batch` 段已切好
  （本轮时间最早 3 个，余者列入汇报「下轮可细化」）；
- **演出资源现状**：`assets` 段（每 involved char 立绘链 / 每 location 空间链）
  ——第 2 步拆解的全部 facts，不必重查。

### 2. 探索演出资源 + 拆解 SubEvent

**探索**（facts 由 §1 preflight `assets` 段带出）：

- 立绘链现状（每 involved Character）：DesignSheet → IllusDesign ←outfit_for←
  CostumeStyle——着装继承与占位判断的依据；
- 空间链现状（每 occurs_at Location）：Spot →realizes→ Scene——机位选用与
  占位判断的依据。信息不足时按需补查（查询形态见 preflight.py 源码）。

**拆解判据**（演出价值，非既有 ink——细化在前、ink 在后，禁止把后续产物当依据）：

- **到场规则**：「赴约/到访/首进场」性质 → 开场报到演出（接人/寒暄），时间=事件前 5~15 分钟插值；
- **换区规则**：叙事横跨 Location 内多子空间 → 按子空间分段各挂机位；单机位不拆；
- **离开规则**：冲突/尴尬/离别收尾 → 送别/收尾演出，时间=事件后 15~30 分钟插值；
- **演出价值判据**（铺垫→触发→释放→余韵）：无价值不拆——挤水分与拆段都是伤害，
  宁少勿滥；纯过渡/独处/状态变化单段即足。
- **模式参考**：读 [references/微演出模式库.md](references/微演出模式库.md)——
  八种微演出模式（到场/离开/换区/对峙/独白/并行小事/目击/误认）各含适用判据、
  典型拆解形态、项目实感示例与**不拆反例**；拆解决策对照模式库而非现想，
  文末拆解自检清单在落建议 JSON 前过一遍。

**sub description 模板**（必填，不含机位名）：机位动作 / 到场离场方式 / 参与人 /
情绪基调 / 与邻接 sub 的衔接（承接什么引出什么）。

### 3. 占位物化（缺口 → status=0 占位）

对每个 sub 的链条 `IllusDesign←appears_as←sub→anchored_at→Scene` 逐环检查，缺则占位：

| 缺口 | 占位节点（cypher 要点） |
|---|---|
| 空间不存在（新房间/新位置） | `CREATE (sp:Spot {id,status:0,name,kind:'zone'})` + `(l)-[:part_of]->(sp)`（Location 必已存在，否则走入口核验报错） |
| 机位不存在 | `CREATE (sc:Scene {id,status:0,name,scene_type})` + `(sp)-[:realizes]->(sc)` |
| 服装套不存在 | `CREATE (cs:CostumeStyle {id,status:0,name,outfit_style})` |
| 形象版本不存在 | `CREATE (idn:IllusDesign {id,status:0,adaptation_notes})` + `(cs)-[:outfit_for]->(idn)` |
| 着装可继承 | 不占位：`appears_as` 直接挂兄弟 sub 的既有 IllusDesign |

**着装优先级**：兄弟 sub 继承 > CostumeStyle 占位 > IllusDesign 占位（继承优先，
占位只补缺口）。**空间/着装叙事决策（哪个房间、哪套衣服）在本层拍定**——占位节点
的 name 即决策载体，命名对照 [references/占位命名规范.md](references/占位命名规范.md)
（从图上实存节点归纳的四类命名模式 + 查重自检——占位与真身重名 = 图上两节点打架）。

### 4. 逐 event 询问 + 组装建议 JSON

**一 Event 一题**：每题摆出该事件完整方案（0/1/N 个 sub + 各自 anchored_at 目标
（既有/占位标明）+ appears_as 目标（继承/占位标明）+ 时间插值 + description 要点）
+ Info 升格项（如有），用户整体拍板（可改细节后接受）。范围内事件按时间序逐个过。

全部拍板后组装建议 JSON（**顺序：占位节点 → 边**，节点先于边）：

- 项结构 `{check, priority, reason, content, cypher, source:'event-stager'}`；
- check 取值：`S1_placeholder_node`（占位 Spot/Scene/CostumeStyle/IllusDesign）、
  `S2_subevent`（SubEvent+refines+anchored_at+appears_as 一体）、
  `S3_info_upgrade`（Info 升格：建 sub + DETACH DELETE Info）、
  `S4_gap_fix`（确定性缺口修复：involved/occurs_at 补边——仅当图上实体确实存在
  只是边缺失时才走此类，实体缺失一律报错不走此类）；
- priority：占位 high（生产链待消化）；其余 medium；
- 落盘 `02_剧情数据/<日期>_round<N>_<主题>_stager_建议.json`，轮次 N 由 `$ROUND`
  推导（共享计数器全量取 max+1，勿手写文件名扫描——排序取最新会跳号）；
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
  ap.detail='<继承：同父兄弟着装 / 占位：新套装待消化>';
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

## 参考文档

- [references/微演出模式库.md](references/微演出模式库.md) — §2 拆解时读（八模式范式+不拆反例+自检清单）
- [references/占位命名规范.md](references/占位命名规范.md) — §3 占位物化时读（四类命名模式+查重自检）
- [叙事基础.md](../../../00_init/Schema/叙事基础.md) / [场景美术.md](../../../00_init/Schema/场景美术.md) / [角色美术.md](../../../00_init/Schema/角色美术.md)
- 方法论溯源：工作区根《event-ideator与event-stager功能定稿方案.md》§3/§6/§8.2
