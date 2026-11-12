---
name: chapter-novelist
description: |
  推进 Section 图节点的小说段（提纲已内化：**节的提纲即图数据本身**——Event/Fact/Lore/Choice + 分支骨架；块 id=scene_id 由 1a 机位素材集现场取用；原 chapter-outliner 已废弃并入本 skill，设计简报与 Chapter.summary 已废止不入依据）：按 includes 物化成员圈定取材素材（本节 Event 直连 + 本节 Event 细化出的 SubEvent reveals 的 Hook + involved 角色 has_info 的 Lore；时间由成员事件推导）→ Lore 新鲜度裁量（遗忘曲线 R=base×2^(−Δ/h)，kl 分档半衰期，F≥70 正面可/≥30 仅侧面/<30 禁释放，scripts/fingerprint.py freshness）→ 丰满度自检（不足拒绝产出报缺口，用户跑 event-ideator 补全）→ **结构推理在思维链中完成、不落中间提纲文件**（场景段切分 / 分支节点图核验 / 节拍规划）→ 五步产节级散文 小说.md（**纯文件产物，零图写入**；正文 `### <scene_block_id> <场景名> <时段>` 场景段标题承载拓扑契约，id = 所写机位的 scene_id（图即档案）；头部**取材指纹**＝实际取用素材 id + 内容指纹 + fact/lore 消费强度 E/S，scripts/fingerprint.py）。重写场景（素材 stale / 用户明示）：覆盖旧文（禁读旧文）且显式作废定稿链（SET Section.status=-1 + 该节全部行 -1）——本 skill 唯一图写入。对账发现的新 Event/Fact 走建议 JSON 通道（source='chapter-novelist'，人工经 dashboard 审阅入库；稀疏 ≤3 Event+2 Hook）。
  前驱：无（章无 status 取消结构审；节创建即 0 待定稿，定稿审在下游 dialoguer 产出置 10 后由人工批准；自由节与已组章节均可创作，配音前须组章）。场景段结构以小说 `###` 标题为契约（下游 dialoguer 照搬），分支事实以图 Choice/option 为准。存量直连：无小说.md 且 script_path 已有值的旧流程节不补小说。在需要为某节创作节级小说、plot-design 编排推进小说段、或定稿段报素材 stale 需重写时使用。
argument-hint: <section_id>
arguments:
  - section_id
allowed-tools: Read, Bash, Write, Edit
---

> **stale = 重写覆盖**：小说.md 头部取材指纹与当前图素材不一致（fingerprint.py check 退出码 1）时，**必须重写并覆盖旧文**——禁止因文件已存在而跳过，也**禁止读旧小说正文**（头部块只由脚本解析），直接以当前图数据为唯一来源重新创作；并按段 3 作废定稿链。

# 节小说（小说段 · 纯文件产物，零图写入）

剧情创作流程的**第二段**（节级，在章级结构段之后、定稿段之前）。**节的提纲即图数据本身**：Event（情节，经 includes 物化为节成员）、Hook/Lore（事实/设定）、Choice/option（分支）、机位素材集（includes→anchored_at，块 id 来源）——结构推理（场景段切分/分支核验/节拍规划）在本 skill 的思维链中完成，**不落任何中间提纲文件**。产出节级散文 **小说.md**（dialoguer 定稿段的创作土壤），**全程零图写入**（唯一例外：stale 重写时显式作废定稿链）。正文 `### <scene_block_id> <场景名> <时段>` 场景段标题即拓扑契约（dialoguer 照搬为 ink 场景块）。

## 参数

| 参数 | 说明 |
|------|------|
| section_id | Section 节点 ID（snowflake）。由 plot-design 编排传入，或用户直接触发。 |

> **素材消化优先**：图素材（Event/Hook/Lore/sub.description）是**事实清单非台本**，正文不是它的散文化投影。一条素材合格入文的形态不是「出现」——陈述句裸装（安置句）与整条蒸发同级处理——而是**留下痕迹**：改变正文里某个具体的东西（一个动作的选择、一句台词的措辞、一个感知细节、一件物件的用法）。判别法：删掉承载句，段落若只损失信息、不损失动力，就是没消化。落稿前先构段 2a 叙事引擎（含段驱动），有权压缩/放大/改写呈现方式（拓扑与事实硬契约不变）。「把 description 逐项安置进段落」= 说明书，是本 skill 的头号反模式。

## 流程（三段式：查状态 → 完成任务 → 保存结果）

> 小说.md 的「状态」= 文件存在性 + 取材指纹新鲜度（无图状态）；新鲜度由下游 fingerprint check 兜底——「存在 ≠ 新鲜」。

### 1. 查询目标节点状态 + 圈定素材 + 自检

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 查询。

#### 1a. 解析 Section + 前驱校验

```cypher
MATCH (sec:Section {id:'<input>'})
OPTIONAL MATCH (ch:Chapter)-[:has_section]->(sec)
WITH sec, ch
OPTIONAL MATCH (sec)-[:includes]->(:Event)-[:refines]->(:SubEvent)-[:anchored_at]->(s:Scene)
WITH sec.id AS id, sec.section_no AS section_no, sec.title AS title, sec.summary AS summary,
     sec.status AS sec_status, sec.script_path AS script_path,
     ch.chapter_no AS chapter_no, ch.title AS ch_title,
     collect(DISTINCT s.id) AS scene_ids, collect(DISTINCT s.name) AS scene_names
RETURN id, section_no, title, summary, sec_status, script_path,
       chapter_no, ch_title, scene_ids, scene_names
LIMIT 1
```

**前驱校验**：自由节（无所属章，`ch IS NULL`）**放行**——节由 dashboard ＋新节直建，小说可先于组章创作；有章亦直接放行（结构产出即可用，无审批）。仅须节自身 `sec.status ≠ -1`（作废态表示等重做流程，由编排层处置）。
**模式判定**：
- 小说.md 不存在 → **首建模式**（进 1b）。`script_path` 已有值时为存量直连节：plot-design 编排不会调到（判定在上游）；被用户直接触发 = 显式转新流程，报告「本节为旧流程直连形态，本次建小说层（stale 前不动定稿态）」后继续。
- 小说.md 存在 → 进 1d 指纹自检（stale → 重写模式；新鲜且用户未明示重写 → 汇报退出）。
- **小说路径推导**：有章 `25_剧本/ch<NN>/sec<MM>/小说.md`（NN=chapter_no、MM=section_no 零填充——人读区编号目录，title 改名零漂移，重排随编号迁移）；自由节 `25_剧本/自由节/sec<MM>/小说.md`。组章重排后重写时按新章路径落盘，旧自由节目录留存为历史。

#### 1b. 章级依据（图）+ 圈定取材素材

- 1a 查询已带回本节机位素材集 `scene_ids`（includes→anchored_at→Scene 的 DISTINCT id）——**段 id 唯一合法来源 = 所写机位的 scene_id**（同机位多段重复用同一 id，段边界由行序承载）。**创作自由不包括凭空发明地点**：切分只能在素材机位集合内（includes→refines→SubEvent→anchored_at）；想写集合外机位（无 sub 锚定的导语/转场段）时**即停即报**（段名+动机+三可能：隐含演出段未细化[走 event-stager 补 sub+anchored_at，含 Scene 占位物化] / 越界脑补[重切] / sub 锚错机位[修 anchored_at]），由用户拍板，禁止自行查图补 id 静默自愈。

圈定查询（一条 UNION，产出指纹素材 JSON；Event 沿 `Section→includes→Event` 直连 Event 驱动化，**includes 即成员、不做任何时间过滤**（节的时间坐标由成员事件推导，跨天节天然支持；旧模型的 `time_day` 时间窗过滤已随 contains 废止、字段本身亦已废止删除），Hook/Lore 按 label 分流两源防过宽：**Hook** 走本节成员事件细化出的 SubEvent `reveals` 的读者侧揭示（圈定即揭示主场，一次性显性交付）；**Lore** 走本节 involved 角色 `has_info` 的固有设定（含 `relation{type:控制}` 的控制者人格——受控角色的戏折射控制者特质，换魂/操控类题材通用；无揭示时刻，暴露节奏归遗忘曲线，见 1b'）——**Event-establishes 出边的 Hook 不圈定**（产生事件所在节直接演出事件本身，Hook 是事实投影无增量）；**`Event/Lore 端 reveals 均违规`**（Schema 已废止 Event 级、禁 Lore 目标；圈定查询天然不会带出））。场景段标题的场景名/时段来源：`MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)-[:refines]->(sub:SubEvent)-[:anchored_at]->(s:Scene) RETURN DISTINCT s.name AS name, s.time_of_day AS tod`：

```cypher
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)
RETURN 'event' AS kind, e.id AS id, e.title AS title, e.time AS time, e.type AS type,
       e.description AS description, e.ending_kind AS ending_kind, e.condition AS condition,
       null AS content, null AS knowledge_level
UNION
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e2:Event)-[:refines]->(sub:SubEvent)-[:reveals]->(f:Hook)
RETURN DISTINCT 'fact' AS kind, f.id AS id, f.title AS title, null AS time, null AS type,
       null AS description, null AS ending_kind, null AS condition,
       f.content AS content, f.knowledge_level AS knowledge_level
UNION
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e2:Event)
MATCH (src:Character)-[:has_info]->(l:Lore)
WHERE (src)-[:involved]->(e2)
   OR (src)-[:relation {type:'控制'}]->(:Character)-[:involved]->(e2)
RETURN DISTINCT 'lore' AS kind, l.id AS id, l.title AS title, null AS time, null AS type,
       null AS description, null AS ending_kind, null AS condition,
       l.content AS content, l.knowledge_level AS knowledge_level
```

演出段素材（父事件细化出的 SubEvent 是机位级演出事实，写场景段时按 sub 对号）：`MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)-[:refines]->(sub:SubEvent) OPTIONAL MATCH (sub)-[:anchored_at]->(sc:Scene) RETURN sub.id AS sub_id, sub.title AS title, sub.time AS time, sub.description AS description, sc.name AS scene`——sub.description 承载演出内容（升格自 Hook/Lore 的台词/动作），空缺 = 待 event-stager 拆解，可作素材不足信号。

**素材消化契约**（叙事引擎的解读权基础）：
- sub.description / Event.description = **事实清单**（发生了什么/谁在场/关键物件/机位/基调），是**素材不是台本**。Hook/Lore 的 **title 即事实**；content 可空（无增量时的缺省态），有值仅为补充证据——痕迹级呈现由写作现场设计，不从 content 誊写。
- **硬契约·事实不可蒸发，落点 = 痕迹而非陈述**：核心事实必须改变正文里某个可指认的具体物（一个动作选择/一句台词措辞/一个感知细节/一件物件），才算落点。判别法（自检用）：删掉承载句，段落只损失信息不损失动力 → 裸装安置句，回炉改折射。数字与专名可全隐（欠款 8600 可以只活在「把凉可乐往边上挪了挪」的手紧里），**事实的后果在场即可**。全篇找不到任何痕迹 = 蒸发，违硬契约——防的是两个极端：裸装（复述）与全暗线化（丢失）。
- **软素材**（novelist 可重写/可丢弃/可换呈现方式）：description 里的**台词原文、金句、比喻、情绪注解、道具与环境细节**——照抄即誊写；台词层由下游 dialoguer 从小说正文重新提炼，丢弃 description 台词无下游连锁。**注意 sub 契约（2026-11-09 定稿：节拍级）**：sub description = 2~4 个分句的节拍链（谁+做了什么+互动方向），不含台词/道具/环境/氛围；sub 提供的是「该演哪几个节拍、谁主导」，**具体怎么演完全由 novelist 即兴设计、自担物理合理性**；存量 sub 仍可能带微剧本级细节（含物理瑕疵），消化时按软素材条款有权丢弃，不必为其物理合理性兜底。
- **视角转换**：图素材一律完成时的上帝视角（「发生了 X」），正文一律进行时的限知体验（X 正在如何被看见/听见/做到/被误会）。复述感 = 完成时态总结句密度超标（「他知道/他认得/XX接了两个月/不久前……现在……」），识别与改法见去AI味工序「素材复述腔」。
- 均匀展开全部节拍 = 打钩式说明书；详略取舍见 2a 叙事引擎。

Bash 落盘复用（段 3 的 gen 还要用同一份）：`python "${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py" -c "<上句>" --json > .tmp/novelist/<sec_id>_materials.json`（UNION 是单语句，`--json` 输出数组即素材 JSON）。

再查创作上下文（不进指纹）：出场角色 + LanguageStyle（与 chapter-dialoguer 1b 同款查询——已含控制跳：灵魂的 LS 随宿主入场，**内心独白语感用控制者 LS**；对白语感权威源——**人 × 事交集：Event 是情节，LanguageStyle 是语感，小说写的对白必须按图上人设**）。

#### 1b'. Lore 新鲜度裁量（圈定 lore 行非空时）

Lore 消费有限次——读者记忆按指数衰减建模（`R = base × 2^(−Δ/h)`，Δ=距上次消费的节数、h=按 kl 分档半衰期 1→12/2→6/3→3；上次消费 E 正面=记忆重置到满、S 侧面=重置到 60%）。圈定素材含 lore 行时跑：

```bash
python "${CLAUDE_SKILL_DIR}/scripts/fingerprint.py" freshness --in .tmp/novelist/<sec_id>_materials.json --at <chNN/secMM> --root 25_剧本
```

按输出的 `allow` 档位裁量（不设人工停点）：

- `explicit`（F≥70）：正面/侧面均可——读者记忆已淡，重新显性陈述不显重复
- `side`（30≤F<70）：**只可侧面**折射（改动作/措辞/细节），正面即车轱辘话
- `blocked`（F<30）：本节禁释放，静默剔除出取材清单
- 从未消费：无限制

Hook 行不跑 freshness（圈定即揭示主场，按 2a 信息释放节奏正常显性交付）。落盘时（段 3 gen）按**实际写法**带强度标记：正面=E、侧面=S——这是下一次 freshness 的衰减基线，标记由段 2a 的释放方式规划机械转录，非额外裁量。

#### 1c. 丰满度自检（素材门控，不足拒绝产出）

圈定后体检本节素材丰满度（体检查询沿用原 outliner 范式，聚焦本节 Scene 源 Spot 的 Event）：(1) Event 数量（每 Scene 平均不足 ~1 个 = 过少）；(2) Event 间 leads_to 连贯性（链断裂）；(3) Choice option 指向的 target Event 是否存在（分支无落点）；(4) 出场角色 involved 事件数（角色弧空转）。**命中任一 → 停止——不写 status、不落盘**，产出「素材不足报告」（缺口明细）返回，提示用户跑 `event-ideator` 补全后重调。**禁止硬凑**。够 → 进段 2。

#### 1d. 指纹自检（小说.md 已存在时）

```bash
python "${CLAUDE_SKILL_DIR}/scripts/fingerprint.py" check --novel "<小说.md 路径>" --in .tmp/novelist/<sec_id>_materials.json
```

- **exit 0（新鲜）且用户未明示重写** → 汇报「小说已是最新（取材 N 条一致）」，停止退出。
- **exit 1（stale）或用户明示重写** → **重写模式**（进段 2；禁读旧小说正文；段 3 需作废 sc）。

### 2. 完成任务（结构推理 + 五步创作，唯一落盘 = 小说.md）

方法论依据 [references/小说方法论精简版.md](references/小说方法论精简版.md)（节级 + galgame 落点裁剪版）。

#### 2a. 结构推理（**在思维链中完成，不落中间提纲文件**）

1. **场景段切分**：按圈定 Event 的时空与叙事节奏切分本节为若干场景段（同场同时段的连续事件一段；干跑范式：上午康复中心 / 下午床铺 / 夜直播位 = 3 段），每段绑定所写机位的 scene_id + Scene 名 + 时段（id 从 1a 素材集取，同机位多段共用同一 id）。
2. **分支节点图核验**（本节含 Choice 时）：在推理中画分支拓扑——每个 option 的落点 Event 必须存在（图上查）、无死胡同（每条分支汇合回主线或导向 ending）；分支本质差异存疑（flavor 级）时标注待补并在汇报中提示，不擅自替 Choice 加戏。
3. **叙事引擎**（说明书感的根治层——以下四步在思维链中依次完成，结果浓缩为 `## 叙事引擎` 两行落进小说.md）：
   1. **悬置问题**（dramatic question）：一句话——读者带着什么未决问题读这节？在哪个场景段兑现或反转？必须从 Event 冲突/Hook/Lore 反差中**提炼**（例：签约节不是「他能不能签下来」——那是流程；是「这具身体的署名权归谁」），禁止发明图上没有的情节。**素材确实提炼不出悬置问题**（全是流程性事件、无对抗无线索反差）→ **显式报告「本节缺乏可悬置冲突」并停止**，不硬凑不落盘，转用户跑 event-ideator 补冲突素材——信号标红，不是门禁拦截。
   2. **张力曲线**：每场景段标功能位（铺垫/升温/转折/回落）+ 相对张力值。硬规则：相邻段张力不得全平——全平即说明书，回炉重排（通过调整详略与释放节奏救，不动拓扑）。
   3. **段驱动（micro-intent，段内引擎）**：每场景段落笔前定一句话——视角人物在本段**正试图完成的一件小事**（意图可以极小：挂掉这通电话 / 把字签完 / 撑到下播）+ 什么在妨碍（摩擦：另一个人 / 这具身体 / 环境 / 自己）。段的推进力来自意图-摩擦，**素材只有两种入场资格：服务该意图 / 干扰该意图**——两边都不沾的素材没有入场券（改走暗线或换段）。这是悬置问题的段级降粒：节级问「读者带着什么未决问题读」，段级问「这个人此刻想干什么、谁在挡」。没有段驱动的段落，写出来必然是素材安置区。
   4. **详略配比**：段内 sub 节拍过权重表——**每场景段选一个重拍临场详演**，其余压成半句/一笔带过/做环境背景；同段多 sub 禁止均匀展开（配比理由留在思维链）。重拍选择依据：意图-摩擦最尖锐处、悬置问题的兑现/反转点、人物关系变化点优先于流程性节拍。
   5. **信息释放节奏**：圈定的 Hook/Lore 逐条标释放方式（Lore 按 1b' freshness 档位约束：side 档只可折射、blocked 剔除）（陈述式显性交付每场景段 ≤1 / 折射在场 / 本节不释放），与落稿笔法规范第 2 条（素材燃烧）衔接；释放时机服务张力曲线（升温段埋、转折段收）。

#### 2b. 五步创作

1. **进场三问**：粒度 = 节级散文，每场景段约 500~1500 字（指引非硬性）；落点 = galgame 定稿土壤**非连载**——不写章末钩子/上章回顾/平台向调味；**视角人物定死**（依事件与出场角色），写入小说 `## 视角`。
2. **三件事钉人物 + 强场景锚**：每个主要出场角色钉「想要什么 / 怕什么 / 有什么不肯告诉别人的伤」→ 写入 `## 人物速写`（dialoguer 提炼台词的依据）；场景段序 = 强场景锚，**不可动**。
3. **节拍对齐**：按 2a 叙事引擎逐段展开——**事实全消化（痕迹式落点，见素材消化契约）、详略按配比**：重拍临场演出，轻拍压缩带过（半句/环境背景/一笔带过），description 的台词/金句等软素材可重写可丢弃；**不增删场景、不改分支拓扑**（选择项归属图未定时按「纯角色内心」缺省并标注待定）。**逐项等权展开 = 说明书，自检必拦。**
4. **落稿**：只写图素材与节拍已背书的区间；**称谓规则**（穿越/换宿主题材）：内心独白与叙述用本名，说出口的台词用宿主名，叙述句身体动作与心理活动拆开归属；**禁裸 Day 计数**（叙述层用场景指称，如「那天在桥上」）；对白按 LanguageStyle（词汇/节奏/口头禅/情绪模式）。
   - **落稿笔法规范（演出优先——小说不是汇报，写时遵守非写后补）**：
     1. **演出 > 概述**：体验不命名——禁「翻旧账环节」「电话有自己的流程」式流程标签/批注句，节奏与氛围由对话和动作自己演；本段最重的事件至少一处临场演出，禁全程战报式压缩（可「一局详演+余局压缩」式配比）。
     2. **素材燃烧**：Hook/Lore/背景素材的合格形态 = 痕迹（见素材消化契约），不是被引用。每场景段陈述式显性释放 ≤1 条，其余一律折射（改动作选择/改台词措辞/改感知细节）或留白；认知素材入场必须走视角人物的感知通道（看见/听见/算到/身体反应），且入场动机由当下场景供给——narrator 主动交代背景（「他知道……」「XX接了两个月」）违例；禁「他想起……」式同手法连用回收多条素材（打钩感 = 引用文献感）。
     3. **感官密度**：每场景段至少 1~2 处非视觉感官（温度/触感/气味/声音质感）；人物身体状态写进动作，不写成判断句。
     4. **节奏节制**：一句成段只留给节拍重音（转折/落笔/收束），每场景段 ≤3~5 处，其余并入段落——碎切过密是排版技巧不是叙事。
     5. **对话人味**：术语型角色（职业身份台词密度高者）全篇至少 1~2 处「裂缝」——冷面下的细（多余的半句/顺手的动作/便签式小心思）；生活碎屑优于功能完整。
5. **自检（就地修，不过关不进段 3）**：**去 AI 味工序**（重工序已从 ink 定稿层前移到本层）——按 [references/小说去AI味工序.md](references/小说去AI味工序.md) 执行：叙述层四病灶（价值拔高/narrator 腔/破折号过密/翻译腔）+ 对白层八反模式逐段过，再走 Pass 1 保真回读（拓扑复查——场景段数/顺序/分支与 2a 推理及图 Choice 一致；称谓与 Day 计数复查；声音一致）+ Pass 2 残留味回读（含原惯性签名轻检三样 + **落稿笔法规范五条回检**，已并入该文档）。修不掉的病灶记录进汇报不阻塞落盘。
6. **标记实际取用素材**（段 3 gen 的输入）：指纹只记**正文实际取用**的素材，不是圈定全部——未使用的 Lore/Fact 日后修订不得误 stale 本节。创作完成后从圈定清单列出实际用到的素材 id（Event 通常全用；Hook/Lore 按正文真实引用挑），**fact/lore 逐条标注实际写法强度：正面陈述=E、侧面折射=S**（与 2a 第 5 步释放方式规划一致），供段 3 `gen --ids id:E,id:S` 使用。

#### 小说.md 结构（固定骨架；`###` 场景段标题 = 拓扑契约，dialoguer 照搬）

```
<!-- 取材指纹(chapter-novelist 生成,chapter-dialoguer 自检;变动=重写小说+作废定稿)
event <id> <hash16> <title>
info  <id> <hash16> <title>
-->                       ← 段 3 由 fingerprint.py gen 产出，Write 时置于文件首
# <节标题> · chapter <NN> 小说
## 叙事引擎
- 悬置问题：<一句话，含兑现/反转位置>
- 张力：<段1 功能位> → <段2 功能位> → …（每段一词 + 重拍标记★，人工审「这节有没有戏」先看这两行）
## 视角
<视角人物名 + 一句理由>
## 人物速写
### <角色名>
- 想要：<…>
- 怕：<…>
- 伤：<…>
## 正文
### <scene_block_id> <场景名> <时段>   ← 契约 id/场景名/时段（id = 所写机位的 Scene.id + Scene.name + 时段），每场景段一节
<散文正文…>
```

### 3. 保存结果（指纹头部 + 落盘 + 唯一作废写入 + 对账建议）

1. **指纹头部**：`python "${CLAUDE_SKILL_DIR}/scripts/fingerprint.py" gen --in .tmp/novelist/<sec_id>_materials.json --ids <实际取用素材列表：event 裸 id，fact/lore 带 :E/:S 强度后缀（如 id1,id2:S,id3:E）>` → 产出完整头部块（**只含取用子集**，fact/lore 行记强度——它是后续 freshness 的衰减基线；省略 `--ids` 会记圈定全量，禁止）。
2. **Write** 小说.md（头部块置文件首 + 全文）到约定路径。首建模式到此完成（零图写入）。
3. **重写模式才作废定稿链**（首建模式跳过；`sec_status IS NULL` 跳过）——`--multi` 单事务：

```cypher
MATCH (sec:Section {id:'<sec_id>'}) WHERE sec.status <> -1 SET sec.status = -1;
MATCH (sec:Section {id:'<sec_id>'})-[p:produces]->(l:LineAudio) WHERE l.status <> -1 SET l.status = -1;
```

> 作废后行级恢复走重拆机制（text_sha1 匹配且 wav 在的行恢复 10），plot-design 按产物链现状续推 dialoguer 重新提炼。

4. **对账建议（可选）**：段 2 中长出的新 Event/Hook（图上查无、值得对账入图的）→ 组装建议 JSON（顶层数组，逐项 `{check, priority, reason, content, cypher}` + `source:'chapter-novelist'`；cypher 开箱可执行、可多语句 `;` 分隔先节点后边、**禁止夹带校验节点**；落盘 `*_建议.json` 由 dashboard「📥 补全建议」弹窗拾取写回）：
   - `check = 'N1_novel_new_entity'`，`source = 'chapter-novelist'`
   - 落盘 `02_剧情数据/<日期>_round<N>_ch<NN>sec<MM>_<节概述>_补全_建议.json`（必须 `_建议.json` 结尾；轮次 N = `python .claude/scripts/suggest_round.py` 输出，共享计数器，勿手写扫描）
   - **语句自包含铁律**：每条 `;` 语句的边 pattern 两端点在本语句内 MATCH/CREATE 绑定
     （变量不跨语句延续，MERGE 边端点未先绑定会整 pattern 重建出重复节点——见
     event-stager/references/多语句cypher与MERGE绑定语义.md）；每个分号独占行尾；
     cypher 字段不带 `//` 注释行
   - **落盘后跑** `python .claude/scripts/suggest_lint.py <文件路径>`，FAIL（exit 1）
     就地改写、覆盖重写并重跑至全 PASS（exit 0）再汇报（dashboard 执行侧有同规格
     兜底，FAIL 形态会在采纳时被 400 拒绝）
   - cypher 开箱可执行：只 MERGE 新实体节点 + 定位边（occurs_at/involved/establishes/leads_to），**禁止 SET 既有实体属性、禁止夹带校验节点**；新 Event 的 title/description 不携带时间信息（时间唯一承载 = `Event.time`）；新 Hook 的 title/content 为干净事实陈述（禁备忘/推导/编号引用，占位文字允许），knowledge_level 必填（1/2/3，novelist freshness 半衰期档位），必须挂 establishes 成立源、不建 reveals（揭示场合归 event-stager 拍板）——**novelist 不建 Lore**（固有设定是构图期拍板，非写作期对账产物）。稀疏纪律：单次至多 3 Event + 2 Hook，无新增不落盘只汇报。
5. **汇总**：小说路径 + 取材条数（event/fact/lore 分计）+ 模式（首建/重写）+ 是否作废定稿链（sec.status 与行数前后变化）+ **Lore freshness 裁量行**（每个被消费 lore id → F 值 → 本节释放方式 E/S；fact 无需）+ 建议 JSON 路径（如有）+ 分支待补标注（如有）+ 自检修正说明。

## 参考文档

- 方法论（节级裁剪）：[references/小说方法论精简版.md](references/小说方法论精简版.md)——五步展开、对账四分类
- 去AI味工序（段 2b.5 执行）：[references/小说去AI味工序.md](references/小说去AI味工序.md)——叙述层四病灶、对白层八反模式、两遍回读
- 指纹契约：[scripts/fingerprint.py](scripts/fingerprint.py) 顶部 docstring（归一化规则 / gen --ids / check）
- 剧情 Schema：[00_init/Schema/剧情.md](../../../00_init/Schema/剧情.md) — Section 定稿态 / 创作流程注记「小说段」
- 上游：[chapter-structurer](../chapter-structurer/SKILL.md)（章级建结构，**用户直触**，不经 plot-design；dashboard 人工编排直写为并列通道）
- 下游：[chapter-dialoguer](../chapter-dialoguer/SKILL.md)（读小说.md 提炼 台词.ink，场景段照 `###` 标题；入场 fingerprint check 自检，stale 回退本 skill）
- 建议通道：本文件段 4 内联契约（建议 JSON 字段 / 多语句 / dashboard 弹窗写回）
