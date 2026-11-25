---
name: event-stager
description: |
  事件细化落地层——双入口：①**事件共识文档**（`*_共识.md`，event-ideator 产，新事件未写图——消化共识拆解演出，产**合并定稿**：I 域条目照抄 + S 域追加）；②**图中 Event**（id/title/时间窗，存量细化/重拆/补拆——产纯 S 域定稿）。四步推进：前置核验（缺叙事基础实体报错不代建；共识模式下占位实体演出资源为零是预期态非缺口）→ 探索演出资源并拆解 SubEvent（戏剧节拍分析，模式库只查遗漏不做生成依据）→ 占位物化（为 sub 建 IllusDesign←appears_as←SubEvent→anchored_at→Scene 链，Spot/Scene/CostumeStyle/IllusDesign 缺口建占位意图）→ 逐 event 询问确认 + 产**事件定稿文档** `<日期>_<主题>_定稿.md`（交 suggest-consumer 严检 Schema 并组装建议 JSON，用户确认后执行写回；本层不产 cypher、不跑 lint）。
  多轮交互一次一问、每问附推荐；每批交互默认 3 个 event（preflight 切批的交互节奏，非数量门控——定稿可多批累积）。不建 Event/Info/Choice/Location/Character。
  在用户说「细化」「stager」「消化这个共识」「这批事件细化一下」或给出事件范围/共识文档要求推进机位层时使用。
argument-hint: <共识文档路径 | event id列表 | 事件title列表 | 时间窗>
arguments:
  - events
allowed-tools: Read, Bash, Write
---

# 事件细化落地（event-stager）

把粗粒度 Event 物化成机位级演出段（SubEvent），并把演出所需实体**全部占位物化**（演出侧叙事决策在本层发生，创建权就在本层）。缺口处置一律「占位节点」——占位在图上的位置自带需求上下文，可被独立消化。

**三条铁律**（全程生效）：

1. **零直接图写入**：交互期间仅查询；全部产出一定稿落盘 → suggest-consumer 严检组装建议 JSON → **用户明确同意后执行写回**（不经本层）。
2. **事件定稿契约（人读优先）**：落盘 `02_剧情数据/<日期>_<主题>_定稿.md`（`_定稿.md` 结尾——**不触发** dashboard 建议弹窗的 `*_建议.json` glob；文件名不带轮次，同日同主题重跑覆盖——汇报注明）。**共识模式定稿 = I 域条目从共识文档逐条照抄（含 reason，不改写不删减）+ S 域条目追加**，同日期同主题；**图模式定稿 = 仅 S 域条目**。定稿是**给人读的 md**——条目组织与标签行只是惯例结构，人阅读性优先于机器可解析性，既有实体 id 内联、对同文档 I 域的指称统一 `定稿I1/I2/I3「名称」` 形态；**不产 cypher、不跑 lint、不生成 id**——Schema 严检、id 生成、建议 JSON 组装全归 suggest-consumer（S 域条目 source 标 'event-stager'）。
3. **一题一答且一 Event 一题**：一次只问一个问题、每问附可归因推荐答案；facts 自己查，decisions 才问用户；缺口修复逐条问，sub+占位方案按 Event 聚合成一题整体拍板。

## 前置

```bash
CYPHER_EXEC="python ${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py"
PREFLIGHT="python ${CLAUDE_SKILL_DIR}/scripts/preflight.py"          # 前置核验（双入口：--consensus / 图内 selector）
OUTPUT_DIR="02_剧情数据"
```

## 职责边界

- **创建域 = 演出域三类占位 + SubEvent**：SubEvent + refines 边；anchored_at 边（Scene 缺则建占位，挂 realizes 到既有 Spot，Spot 也缺则建 Spot 占位）；appears_as 边（着装优先继承父/兄弟 sub，套缺则建 CostumeStyle 占位、版本缺则建 IllusDesign 占位）。
- **着装占位必须同时挂 `Character→has_costume` 归属边**——归属角色 = 该着装缺口所属的 involved 角色（拍板上下文恒明确）；孤儿占位在 dashboard 全链路不可见、体检 E1 误报。
- **禁建**：Event/Info/Choice/Location/Character（缺叙事基础实体一律报错回 event-ideator 层）；Event 直挂 anchored_at/appears_as（EA5 体检兜查）；改既有节点属性。
- **sub 与 Scene 的边界**：sub 描述剧情动作（谁做了什么、什么变化），Scene 只管机位/背景画面——人物姿势、表情、位置属立绘与演出指令层；镜头设计（近景/特写切换）是剧本分镜层的事，sub 只到「机位级演出段」粒度。
- 删父 Event 连带删其全部 sub（dashboard event_crud 已实现级联）。

## 图模型（拆解与占位前必读）

```
人工层：  Character ─involved→ Event ─occurs_at→ Location   （入口核验的前提）
          Section ─includes{order}→ Event                    ← 分节/时间轴只碰 Event
细化层：  Event ─refines{sync:true}→ SubEvent                ← 1:N，本 skill 产
          SubEvent ─anchored_at→ Scene                       ← 严格 1:1（一 sub 一机位），缺则建 Scene 占位
          SubEvent ─appears_as→ IllusDesign                  ← 继承或占位
空间链：  Location ─part_of→ Spot ─realizes→ Scene           ← Spot 缺则建占位
着装链：  Character ─has_costume→ CostumeStyle ─outfit_for→ IllusDesign ← 缺则建占位（占位即挂归属边）
```

- SubEvent 属性仅 id/title/start_time/end_time/description；**无** status/type/involved/occurs_at。
- 占位节点属性 = 最小启动集（Spot: name/kind/description 无 status 骨架；Scene: name/scene_type；CostumeStyle: name/vibe；IllusDesign: 裸节点——后三者流水线 status=0 起点，含义是"待生产"非"占位标记"）；其余字段由消化方（scene-designer / char-design 链）按各自 Schema 补全。
- 占位 Scene 后续改名/改字段不造成 sub 漂移（title/description 不引用机位信息，见 §2 规范）。

## 工作流（四步）

### 1. 前置核验（发现确定性缺口）——双入口

```bash
$PREFLIGHT --consensus <共识文档路径> [--json]                           # 共识模式（新事件未写图）
$PREFLIGHT --ids <id1,id2> [--titles t1,t2] [--window 起,止] [--json]    # 图模式（存量细化/重拆/补拆）
```

两模式输出同构（mode/scope/failures/batch/placeholders/assets，全部只读），判读规则：

**图模式**（沿用）：

- **范围解析**：命中事件清单（id/title/start_time/occurs_at/involved），复述 N 个事件 + 时间跨度再进下一步；
- **入口核验（权威表述）**：`verdict=FAIL`（缺 occurs_at Location / 缺 involved Character）→ **先分诊**：缺的实体**在图、只缺边** → 转 §4 的 `S3_gap_fix` 补边建议，流程继续；实体**不在图** → **报错停止**（脚本 `failures` 已逐事件列出），不代建，回 event-ideator 层补。title/description 提及实体未建档同理（LLM 读文判断，实体是否在图对照 `assets` 段核查）；
- **演出资源现状**：`assets` 段（每 involved char 立绘链 / 着装直查表 `costumes`——含 status=0 占位，**同缺口勿重复建占位** / 每 location 空间链）——§2 拆解的全部 facts，不必重查。

**共识模式**（新事件尚未写图——scope 条目 id=null，title 即指称）：

- **解析失败**（退出码 2：无 I2 条目 / 缺 start_time / 裸名指称无 id 无占位）→ 回读共识文档人肉分诊：共识本身有缺 → **报错回 event-ideator 修共识**，本层不脑补；
- `failures`「缺 occurs_at/involved」= 共识条目缺字段 → **报错回 event-ideator**（`S3_gap_fix` 仅适用图模式「实体在图只缺边」，共识模式不产 S3）；
- `failures`「id 图上查无」= 共识内联 id 错拼 → **报错回 event-ideator 修共识**（id 须现查内联，防静默错挂）；
- **`placeholders` 段（占位 Character/Location）→ 演出资源为零是预期态，不是缺口报错**：着装不可继承（无立绘链）、空间无既有 Spot/Scene——链路必然全新占位（CostumeStyle+IllusDesign / Spot+Scene 占位），照常推进不得因 `assets` 空停摆；既有 id 的 Character/Location 正常查 `assets` 做继承判断。

**批次切分**（两模式同）：每批默认 3 个 event（`batch` 段已切好：本轮时间最早 3 个——图模式按 id、共识模式按 title 标识；余者列入汇报「下批可细化」）——**交互节奏默认，非数量门控**：需要时连续多批运行，定稿逐批累积后一并交 suggest-consumer。

### 2. 探索演出资源 + 拆解 SubEvent

**探索**（facts 由 §1 `assets` 段带出）：立绘链（Character→AppearanceStyle→DesignSheet→IllusDesign←outfit_for←CostumeStyle）是着装继承与占位判断的依据；着装全集另见 `costumes` 段（has_costume 直查，覆盖无 DesignSheet 的占位着装）——建占位前先对表防重。空间链（Spot→realizes→Scene）是机位选用与占位判断的依据；信息不足时按需补查（查询形态见 preflight.py 源码）。**共识模式下父 Event 取自共识 I2 条目**（title/time/description 照共识，不在图中）——SubEvent title 的 `<父事件title>` 即共识 I2 的 title，时间插值以 I2 time 为锚；S2 条目「父Event」写 `定稿I2「<父title>」` 指称（suggest-consumer 组装时绑定同轮生成的 id）。

**拆解六步固定**（模式库在末位做校验与补遗——先找演出价值，再对模式查遗漏）：

1. **戏剧节拍分析**：从事件 title/description 识别值得表现的节拍（铺垫/触发/反应/释放/余韵）。只识别潜在演出内容，不要求每个节拍都生成 sub。
2. **动作与状态变化分析**：把值得表现的节拍转化为具体剧情动作——逐项过：谁行动、对象、时间与空间、结果、是否带来可感知的信息/情绪/关系/状态变化（**未带来变化的动作不拆**）。description 按 [SubEvent.md](../../../00_init/Schema/剧情/SubEvent.md) 撰写契约落节拍级。
3. **独立演出价值判断**（拆/不拆的裁决，防过拆与欠拆）：**结构性硬信号先行（几乎必拆——即 [SubEvent.md](../../../00_init/Schema/剧情/SubEvent.md) 最小粒度定义的演出段类型）：① 换场景——anchored_at 指向不同 Scene/机位（换区、位移到另一空间）；② 换装——appears_as 着装集合变化；③ 到场/离开——人物进出带来的演出段切换。命中任一硬信号即产生天然拍界**；硬信号之外的拆分走演出价值裁决：演出价值 = 铺垫→触发→释放→余韵**至少占一环，且 sub 必须带来可感知的变化**——仅存在一个动作不构成拆分理由；无价值不拆，挤水分与拆段都是伤害，宁少勿滥；纯过渡/独处/状态变化单段即足。拆分数量遵循实际剧情密度：**过拆**（普通动作、每句对话都拆）与**欠拆**（多个独立戏剧阶段塞一个 sub）都是错误；对峙类高密度演出优先 1 个 sub，独立触发/反转/爆发阶段显著时可拆多段。
4. **模式库校验**：对照 [references/微演出模式库.md](references/微演出模式库.md) 检查拆分方案有没有漏拆（漏掉的到场/物件交互）或踩不拆反例——不强制每个 sub 匹配一个模式，命中多模式可组合参考。
5. **SubEvent 生成**：生成 sub 及 anchored_at/appears_as 关系。时间由上下文推导（到场在主活动前、离开在收尾后、换区按位移节奏），**不虚构精确时间**——只要求与父事件及邻接 sub 因果先后相容，允许合理重叠（并行发生的事）。
6. **演出验收**：时间符合因果先后、人物连续性、动作完整性（每个 sub 能说清「谁对谁做了什么」）、不重复表达父 Event 已承载的内容。

#### sub description 规范（权威在 Schema）

Read [SubEvent.md](../../../00_init/Schema/剧情/SubEvent.md)「description 撰写契约」——节拍级粒度、title 叙事短名规范、「写/不写」清单与正反例均以该节为准；生成时对照其正反例自检。

### 3. 占位物化（缺口 → 占位节点）

对每个 sub 的链条 `IllusDesign←appears_as←sub→anchored_at→Scene` 逐环检查，缺则占位：

| 缺口 | 占位节点（最小启动集，定稿以标签行表达） |
|---|---|
| 空间不存在（新房间/新位置） | Spot：name/kind='zone'/description + 归属 Location（必已存在，否则走入口核验报错） |
| 机位不存在 | Scene：name/scene_type + 归属 Spot |
| 服装套不存在 | CostumeStyle：name/vibe + 归属 Character（占位即指明归属角色） |
| 形象版本不存在 | IllusDesign：裸节点 + 归属 CostumeStyle |
| 着装可继承 | 不占位：appears_as 直接指明继承兄弟 sub 的既有 IllusDesign（id） |

**着装优先级**：兄弟 sub 继承 > CostumeStyle 占位 > IllusDesign 占位。**空间/着装叙事决策（哪个房间、哪套衣服）在本层拍定**——占位节点的 name 即决策载体，命名对照 [references/占位命名规范.md](references/占位命名规范.md)（四类命名模式 + 查重自检——占位与真身重名 = 图上两节点打架）。

### 4. 逐 event 拍板 + 组装事件定稿

**一 Event 一题**（保持必问）：每题摆出该事件完整方案（0/1/N 个 sub + 各自 anchored_at 目标〔既有/占位标明〕+ appears_as 目标〔继承/占位标明〕+ 时间插值 + description 要点），用户整体拍板（可改细节后接受）。范围内事件按时间序逐个过。

全部拍板后组装定稿（**S 域条目顺序：占位节点 → 边**，节点先于边）：

- **定稿结构（共识模式两段式；图模式只有第二段）**：
  - **一、事件共识**——共识文档 I 域条目（I1~I5）**逐条照抄**（含 reason，不改写不删减——这是 I 域的权威快照，任何改写都会偏离用户与 ideator 达成的共识）；
  - **二、演出拆解**——本轮 S 域条目（自然语言标签行 + reason；check 分类沿用）：
    - `S1_placeholder_node` — 占位 Spot/Scene/CostumeStyle/IllusDesign（最小启动集 + 归属；归属可指既有 id、本节上文占位，或 `定稿I1「名称」`——共识占位 Location 物化后的 Spot 挂靠）；
    - `S2_subevent` — SubEvent（title/start_time/description 要点）+ 父 Event（图模式写 id；共识模式写 `定稿I2「<父title>」`）+ anchored_at 目标 + appears_as 目标（继承注明来源 sub id）；
    - `S3_gap_fix` — 确定性缺口修复（involved/occurs_at 补边，**仅图模式**且实体在图只缺边；实体缺失一律报错不走此类；共识模式不产 S3——事件还没进图，无「补边」语义）。
- **写后复查（内容层，LLM 判定两项）**：① 每个 event 的 sub 时间与父事件 start_time 及相互先后因果相容（允许合理重叠）；② 同机位同角色着装一致（EA3 口径）。发现问题就地修正后再落盘。
- **落盘与移交**：Write `${OUTPUT_DIR}/${DATE}_<主题>_定稿.md`（UTF-8，共识模式主题与来源共识相同；条目格式见下方定稿模板；同日同主题重跑覆盖——汇报注明）；语句级护栏（语句自包含、`$SUGGEST_LINT`）与 Schema 字段契约严检归 suggest-consumer——定稿只需语义完整、既有实体 id 内联。汇报含下一步话术（「跑 suggest-consumer 消费本定稿 → 严检 Schema、组装建议 JSON → 用户确认后执行写回」）。

### 定稿模板（照抄改值）

// ⚠ 定稿是自然语言层：语义完整即可；字段级契约（SubEvent description 撰写契约、status/最小启动集、边方向与 sync）由 suggest-consumer 对照 Schema 强制。共识模式含「一、事件共识」照抄段；图模式只写「二、演出拆解」段。

```markdown
# <主题> 定稿
> 来源：<共识文件名>（I 域照抄）｜ stager 拆解于 <日期>
> （图模式此行改写：图模式——图中 Event 直细化，无 I 域段）

## 一、事件共识（照抄自共识，逐条原样）

## [I1 占位 Location] 书店
- 定位：临街两层小书店
- reason: <照抄>

## [I2 事件] <title>
- …（共识文档 I1~I5 条目原样照抄，含 reason）

## 二、演出拆解（本轮 S 域追加）

## [S1 占位 Scene] 康复中心-护理站走廊
- name: 护理站走廊 / scene_type: 走廊
- 归属 Spot: [占位：康复中心-一楼]（上条）或 既有id 或 定稿I1「书店」
- reason: <依据>

## [S2 SubEvent] 王昊嘲讽护理陈默苏晓禾回嘴 · 隔壁桌凑近
- 父Event: S8zaNYXiEs（图模式） / 定稿I2「王昊嘲讽护理陈默苏晓禾回嘴」（共识模式）
- title: 路边摊嘲讽 · 隔壁桌凑近
- time: 2024-06-23 18:42:00（父事件起 2 分钟，插值）
- description 要点: 王昊端着啤酒杯晃过来，扫见书袋，嗤笑出声
- anchored_at: [占位：路边摊-烧烤摊位]（S1）
- appears_as: 继承 <兄弟sub id> 的 IllusDesign / [占位：新套装]
- reason: <依据>

## [S3 缺口修复]（仅图模式）…同款结构
```

## 参考文档

- [references/微演出模式库.md](references/微演出模式库.md) — §2 第 4 步校验时读（十一种模式范式 + 不拆反例 + 自检清单）
- [references/占位命名规范.md](references/占位命名规范.md) — §3 占位物化时读（四类命名模式 + 查重自检）
- [Schema/剧情/](../../../00_init/Schema/剧情/)（Event/SubEvent/Info）/ [Schema/场景美术/](../../../00_init/Schema/场景美术/) / [Schema/角色美术/](../../../00_init/Schema/角色美术/)
