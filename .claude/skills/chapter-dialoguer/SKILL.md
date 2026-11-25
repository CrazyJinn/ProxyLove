---
name: chapter-dialoguer
description: |
  推进 Section 图节点的定稿段：读跑团草稿.md（现行链，tabletop-dialoguer 产——拍头【场景…｜block <scene_block_id>】拓扑契约 + 取材指纹自检，stale 回退 tabletop 重跑；存量小说.md 照旧消费；分支事实以图 Choice/option 为准）→ 从草稿**节奏重写**逐句对话（非转写：剥离 DM 判定/量化附录等非叙事杂质、钉子句仅限事实锚、旁白/内心轨量化纪律、感官句迁移、sfx 每场景块 ≤1）→ 产节级 台词.ink（人读/人改的唯一定稿格式，ink 方言 v3）→ ink_line_lint 量化门禁 → 唯一图写入 `SET sec.script_path + sec.status=10` 待审（dashboard 批准 11 后方可拆分配音）。
  双模式：常规创作 / 填充模式（只扩写 llm: 占位，其余行一字不动）；另含存量兼容（旧流程节：小说.md / script_path 历史文件照旧创作）。BGM 不归本 skill。
  在需要为某节产定稿台词、或定稿含 llm: 占位需填充时使用（由 plot-design 编排触发）。
argument-hint: <section_id>
arguments:
  - section_id
allowed-tools: Read, Bash, Write, Edit
---

> **status=-1 = 作废重做**：当本节 `Section.status` 被重置为 `-1` 时（如 Section/Chapter 属性变更沿 has_section/produces 级联、素材 stale 经编排回退重产（tabletop 重跑草稿 / 存量小说链重写）、或人工在 dashboard 驳回定稿），即使 `台词.ink` 已落盘，也**必须重新创作并覆盖**（定稿后写回 10 待审）。`-1` 明确表示有旧产物要覆盖，**禁止因文件已存在而跳过，也禁止读旧台词内容**，直接以当前图节点数据 + 创作土壤（跑团草稿.md / 存量小说.md——均须先过指纹自检；存量直连节读 script_path 历史文件）为唯一来源重新创作。

# 节细节对话（Section 定稿态 · status=10/11/-1）

剧情创作流程的**定稿段**（节级第二环；第一环 tabletop-dialoguer 产跑团草稿——chapter-novelist 已软删 2026-11-20）。读创作土壤（跑团模式：本节**跑团草稿.md**——拍头【场景…｜block】行即拓扑契约；存量小说模式：小说.md 的 `###` 场景段标题照旧；存量直连模式：sec.script_path 历史提纲/骨架文件），**从草稿打磨重写**逐句对话，产出节级 **`台词.ink`**——人读/人改的定稿 ink 方言（**机器可解析**：人工批准后由 section-voice-publisher 拆分进图）。**创作土壤（跑团草稿.md、存量小说.md）在工作区 `Harness/25_剧本/ch<NN>/sec<MM>/`**（Asset 仓库上一层目录里的 `Harness/`，下称**土壤目录**）；`台词.ink` 落盘本仓库的 `25_剧本/ch<NN>/sec<MM>/`（下称**定稿目录**；编号目录；**创作/审阅区，非运行时**）。两者不在一处。

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| section_id | Section 节点 ID（snowflake） | 必传 |

## 流程（三段式：查状态 → 完成任务 → 保存结果）

> 本 skill 是 `Section.status`（定稿态）+ `script_path` 的写入点（不建任何节点）；台词.ink 由本 skill 直接创作产出。编剧是高自由度创作任务，**无纯产出子 skill**——创作与写图都在本 skill 内完成。

### 1. 查询目标节点状态

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 查询。

#### 1a. 解析 Section + 前驱校验

```cypher
MATCH (sec:Section {id:'<input>'})
OPTIONAL MATCH (ch:Chapter)-[:has_section]->(sec)
RETURN sec, ch
LIMIT 1
```

#### 1a-2. 模式判定（作废重做 / 常规创作 / 占位填充）

`script_path` 已有值时，Read 该 台词.ink 并检查是否含 `llm:` 行。**按 `Section.status` 判定**——`script_path` 有值不再等同于「已批」（存量节与跑团重跑的节都可能带着旧的 `script_path`）：

- **`sec.status = -1`** → 作废重做：整篇重新创作覆盖（见顶部注记）。
- **`sec.status = 1`** → 跑团尚未消费完：停止并提示「跑团进行中，草稿未就绪」（守护进程在跑或待跑，完成时 status 置 2）。
- **`sec.status = 10`** → 定稿待人工审：停止并提示（批准 11 后由 voice-publisher 拆分；驳回 -1 后才轮到本 skill 重做——编排层不会在 10 态调本 skill，此处为防御）。
- **含 `llm:` 占位** → 进入**填充模式**（直接走 §2b）：只扩写占位、其余行一字不动。用户流程是「占位 → LLM 填充 → 人工微调」，**禁止整篇重写覆盖手改**。
- **无占位 且 script_path 已有值 且 `sec.status = 11`** → 定稿已批，停止并提示（防覆盖手改/已定稿；要重做先经 dashboard 驳回或用户明示）。
- **其余**（**script_path 为空**，或 `sec.status = 0` / `2`）→ 常规创作流程。`status = 2` 表示跑团草稿已就绪、旧 `script_path` 指向的是存量产物：以跑团草稿为土壤常规创作并覆盖。

#### 1b. 章级依据（图）+ 创作土壤（小说 / 存量提纲）+ 查创作上下文

**先读两份创作依据**：
- **创作土壤（按 1b-2 判定）**：
  - **跑团模式（现行链）**：Read 土壤目录的 `跑团草稿.md`（tabletop-dialoguer 产出）——拍头 `【场景：地点·时间｜block <scene_block_id>】` 行是拓扑契约（场景块 id 唯一来源，同机位多拍同 id、按拍序合并为场景块，照搬不改写）；DM 旁白 + 台词行 + 内心轨是创作土壤；**文末内部附录（DM 判定/量化对照/机制发现）不是土壤，打磨时整体剥离**。
  - **存量小说模式（兼容）**：Read 土壤目录的 `小说.md`（chapter-novelist 存量产出的副本，归 Harness）——`### <scene_block_id> <场景名> <时段>` 场景段标题是拓扑契约（场景块 id/顺序唯一来源，照搬不改写）；`## 视角`/`## 人物速写`/正文是创作土壤。
  - **存量直连模式**：Read `sec.script_path` 指向的历史文件（旧 outline.md / 骨架 ink / dayNN 蓝本），场景分段与分支拓扑照旧以它为准。

再查图（角色 LanguageStyle 同前 + **分支骨架**——分支事实权威在图 Choice/option，小说模式必查：`MATCH (sec:Section {id})-[:includes]->(e:Event) OPTIONAL MATCH (e)-[:presents]->(choice:Choice) OPTIONAL MATCH (choice)-[op:option]->(target:Event) RETURN …`，Choice 的 options/label/去向以此为准核对小说结构）。

再查图：

```cypher
// 出场角色 + 语言习惯（创作对话的核心依据）——图关系遍历，不按名字列表猜：
// 本节 includes 的事件 ← 参与的角色；控制对端（灵魂）随宿主入场——
// 台词轨用宿主 LS、内心轨用控制者 LS（称谓规则的语言侧对应）
MATCH (sec:Section {id:'<input>'})-[:includes]->(e:Event)
MATCH (e)<-[:involved]-(host:Character)
MATCH (char:Character) WHERE char = host OR (char)-[:relation {type:'控制'}]->(host)
OPTIONAL MATCH (char)-[:has_voice_style]->(voice:LanguageStyle)
RETURN DISTINCT char, voice
LIMIT 20
```

#### 1b-2. 创作土壤判定 + 取材指纹自检（填充模式跳过本节）

**按创作土壤文件存在性判定（优先级从上到下）**：
- 土壤目录 `跑团草稿.md` 存在 → **跑团模式**（现行链，下文必过指纹自检）。
- 土壤目录无 `跑团草稿.md` 但 `小说.md` 存在 → **存量小说模式**（兼容，下文必过指纹自检）。
- 两者皆无且 `script_path` 已有历史值 → **存量直连模式**（旧流程节，读该历史文件照旧创作，跳过指纹自检）。
- 两者皆无且 `script_path` 为空 → 停止并提示先把 `Section.status` 置 `1` 进跑团管线（`tabletop-dialoguer` 的守护进程消费后产草稿、置 2；台词须从跑团草稿打磨）。

**跑团/小说模式必过指纹自检**（草稿是纯文件产物，新鲜度由内容指纹保证——status 只标记「产出过」不实时反映素材变动）：

```bash
# 1) 圈定素材（与 tabletop-dialoguer 守护进程同一条查询——直接调它的子命令取，不手抄 Cypher；零 LLM 调用、不写图。路径相对 Asset 根，工作区布局见根 CLAUDE.md）
python ../Harness/tabletop-dialoguer/scripts/tabletop_runner.py materials --section <sec_id> > .tmp/novelist/<sec_id>_materials.json
# 2) 自检（同源脚本,归一化规则与生成侧一致;--novel 参数对 跑团草稿.md / 小说.md 通用）
python "${CLAUDE_SKILL_DIR}/../../scripts/fingerprint.py" check --novel "<跑团草稿.md|小说.md>" --in .tmp/novelist/<sec_id>_materials.json
```

- **exit 0（新鲜）** → 草稿可用，进入段 2 打磨。
- **exit 1（stale：已记素材变动/被删）** → **停止**，产出报告（stale 明细 + 「需先重跑 tabletop-dialoguer 重产草稿并作废定稿；存量小说链经编排重写」）退出——本 skill 不作废 sc（职责在编排层），plot-design 接住后作废定稿链（置 `-1`）再置 `1` 重入跑团管线，tabletop 守护进程重产后本 skill 重新打磨。圈定内未标注（未使用）的素材不算 stale，属常态。

### 2. 完成任务（从草稿打磨细节对话）

按 1b-2 判定的创作土壤逐场景段（跑团模式按拍头 block 合并场景块 / 存量小说模式的 `###` 结构 / 存量直连模式的历史文件），据角色 LanguageStyle 与事件脉络，**从草稿打磨重写**逐句对话写入 `台词.ink`。

#### 从草稿打磨台词的纪律（跑团/小说模式 · 节奏重写，非转写）

> 打磨 = **为逐行点击/逐行语音播报重写节奏**。跑团草稿的台词已是对话体但为「会话流」优化（自然长、口语拖尾、轮转松散），台词行为「点击」优化——把草稿台词原样誊录进 ink 是本 skill 头号病灶（量化门禁拦截，见下方 ink_line_lint）；小说散文（存量模式）则须经体裁转换（散文 → say + 旁白）。

- **跑团模式专属**：文末内部附录（DM 判定/量化对照/机制发现）整体剥离不进 ink；DM 旁白散文按旁白纪律压缩改写（非搬运）；草稿「（沉默）」可转 silence 处理或删；`inner`（内心）按内心轨纪律限量重写。
- **拓扑契约权威 = 草稿块标注**（跑团模式：拍头 `【场景：…｜block <scene_block_id>】`——同机位多拍合并为同一 ink 场景块，段边界由拍序承载；存量小说模式：`### <scene_block_id> <场景名> <时段>` 场景段标题），照搬为 ink `=== <id> // <名>（<时段>）`，不改写不自创；**分支事实权威 = 图 Choice/option**——草稿结构与图分支冲突时报 **FAIL**（回退 tabletop 重跑），不静默对齐。

- **立场守恒（收窄）**：事实、事件顺序、情感极性、节拍位置零变化——**措辞不在守恒范围**（措辞守恒=搬运，违门禁）。只做节奏与体裁转换（跑团会话流 → 点击节奏 / 存量散文 → say + 旁白），不改剧情、不加私货反转。
- **旁白纪律**：一行 ≤25 字（目标 ≤15）；每场景块旁白行数 ≤ say 行数；旁白只写三类——时空切换（到了哪/几点）、可见动作（谁做了什么）、视线引导（看向哪）。**环境氛围、感官质感、比喻意象禁入旁白**（走下方感官句迁移）；禁止 ≥3 行旁白连排。
- **内心轨纪律**（控制者轨，换宿题材）：每场景块 ≤3 行、全文 ≤10 行；**必须口语化**——按控制者 LS 自问自答/糙话/即时吐槽，一句一口气，禁书面叙述句（反例：*关系户。手离键盘三分钟、回来顺手就点下一局的，靠什么进的队，比靠什么赢比赛清楚*——这是小说叙述段；重写如*这手离键盘三分钟还点下一局——哦，懂了，塞进来的*）。**入场券**：只写「说不出但玩家必须知道的信息」（反讽/误读/身份张力）；场面可自行读出的心理描写不拆轨。
- **钉子句沿用（收窄）**：钉子 = **事实锚**（*「陈默」两个字又快又顺*、*手是好的*）——原样进台词，读者跨层要认得同一根钉子；**意象句/氛围句不是钉子**（*温水攥出咯吱咯吱的响*、*空椅子在原地打转*）——转 sfx/动作行或删，禁原句入旁白。
- **感官句迁移规则**：小说感官/环境句的落点优先级 = **动作行（写进谁做了什么）> bed（持续声景）> sfx（点状，受限）> 删**；旁白不是感官句的落点。
- **对白重塑**：草稿/小说对白按角色 LanguageStyle.speech_style（情绪为轴）重塑后进 say 行（草稿口语 ≠ 台词定稿）。
- **sfx 限量**：**每场景块 ≤1 个、全文 ≤3 个**；语义 = 可检索物理短事件——名词+动词、≤10 字、无修饰（*门轴吱呀*、*键盘连点* ✓；*笔尖落在合同纸上*、*语音频道挂断的提示音* ✗ 改 *挂断提示音*）；没有必须标的点状声就不写——sfx 是重音不是配乐。
- **去 AI 味重工序在本层做**：台词层的库存句换角色性格推出的话、留白要有锚点——详见格式规范与方言规范。

#### 台词.ink 格式规范（正式定稿格式，标准合法 ink 方言 v3，机器可解析）

> 完整方言规范（行型表/音频三型/占位工作流/命名契约/硬约束）见 [references/ink方言规范.md](references/ink方言规范.md)——本节为创作侧速览。

```ink
// <节标题>（人读注释，不进图）

=== <scene_block_id> // <Scene 名>（<时段>）

sfx:<点状短事件语义（1~2 秒，播完再接下一句）>
旁白:<叙述文本，一行一句>
<角色名>:<台词>
llm:<拿不准的句子先占位：简短提示语，本 skill 填充模式扩写>

bed+ rain // <区间声景语义（循环播放到 bed-）>
旁白:<床起后的叙述>
bed- rain

* <选项文本> -> <去向：label 名 / scene_block_id / END>
* <直达结局选项> -> END // ending: <kind>

= <label 名>

<角色名>:<台词>
旁白:<叙述>

<落点一句话> # ending: <BE|TE|HE|NE>
-> END
```

1. **场景块标记**：`=== <scene_block_id> // <Scene 名>（<时段>）`（knot，v3 行式）——scene_block_id 照搬小说 `###` 段标题值（块 id = scene_id（Scene 节点雪花 id，ASCII 天然合法），同机位多段共用同一 id，段序由行序承载），Scene 名/时段照搬小说段标题挂行尾注释——**注释是场景名唯一人类可读来源**（图上不再存块→名映射）。时段仅供人读（运行时时段以 Scene.time_of_day 为准，拆分进图不存）。
2. **说话行**：`角色名:台词`——一行一句，冒号用**半角**，角色名用 Character.name 原名（「旁白」「sfx」「llm」是保留字）。**禁止写 `[表情]` 标注**（如 `[微笑]`）：本 skill 专注台词创作，演出层（立绘变体选择）与台词**彻底分离**——由 section-voice-publisher 配音判断期为每句 say 行按台词氛围选定（`LineAudio-[:uses]->StandingIllustration` 边），定稿不承载任何演出标注。**残留 `[表情]` 会在拆分时报错**（parse_ink 拒绝带方括号的说话行，报行号+原文）。pos 不进定稿（拆分时定）。
3. **旁白行**：`旁白:叙述`——一行一句，承载环境/动作/心理等非台词叙述。
4. **音频三型（v3，只写声音语义、不写资产名；三型之外的音频行型 parse_ink 一律报错）**：
   - **点状音效**（独立行）：`sfx:语义描述`——极短声音（1~2 秒）运行时**播完再接下一句**台词/旁白（如推门风铃/开门吱呀/远处闷雷）。**硬约束：每场景块 ≤1 个、全文 ≤3 个；语义 = 可检索物理短事件（名词+动词、≤10 字、无修饰）；没有必须标的点状声就不写**。进图 op=transition，下游 Freesound CC0 实录。
   - **音床起止对**：`bed+ <id> // 语义描述` … `bed- <id>`——区间持续声景**循环播放**（如雨声/街道底噪/电流嗡鸣）。id 限 ASCII 字母数字下划线，同场景块内配对，多床并行/嵌套合法；起止行之间的叙述即床的覆盖区间。进图 op=bed_start（语义=text，AudioFly 声景 ~10s 首尾淡入淡出）/ op=bed_end。
   **克制使用**——只标记叙事上有意义的声音（不是每段旁白都配床），与「短节克制手法」取向一致。
5. **LLM 占位行**：`llm:提示语`——创作期拿不准的句子先占位（简短提示语说明意图/情绪/方向），**不进图、定稿含占位无法拆分**（split 门禁拒绝）；由本 skill 填充模式（见下）扩写为正式行。常规创作完成后**不应残留占位**——占位只用于「草稿暂存、下轮补写」场景（产出照常写 10 待审，split 门禁拒绝含占位拆分、天然防漏）。
6. **选择行**（ink 原生 `*`/`+`）：`* 选项文本 -> 去向`——单行，**禁止缩进的选项正文块**（分支正文一律写在 `= <label>` 之后）。去向 = label 名 / scene_block_id（均 ASCII 契约值）/ `END`（直达结局的 kind 写行尾注释 `// ending: <kind>`）。**连续选择行聚合进图一条 op=choice**（options 含 label+去向，运行时弹选项跳转；选项文本改 → 行 update，无音频损失）。
7. **分支行**（stitch）：`= <label 名>`（ASCII，照搬提纲契约值）标示分支正文起点（进图 op=label）。
8. **结局两行式**：`<落点一句话> # ending: <kind>`（落点内容行 + 行尾 ending tag，标准 ink）+ 单独一行 `-> END`——解析为单条 op=ending（kind + 落点）。线性节末尾也可加裸 `-> END` 收束。注意 ink 中 `#` 是 tag 非注释，行首 `#` 非法。
9. **覆盖完整**：提纲全部场景段、分支、结局都要写，不得增删场景/分支。
10. **情感递进**：每个场景内部情绪有起伏（不是平铺），对齐小说场景段结构与情绪推进的节奏。
11. **机器可解析（硬约束）**：台词.ink 是 section-voice-publisher 拆分进图（`script_splitter.py parse_ink`）的输入——行型严格依赖行首标记（`===`/`=`/`* `/`+ `/`-> `/`//`/`sfx:`/`llm:`/`bed+`/`bed-`/`旁白:`/`角色名:`），**台词正文中不得出现这些行首前缀**（换行重写）；无法解析的行会在拆分时报错（行号+原文），拆分前必须修 ink。行首 `->` 仅支持裸 `-> END`（其余 divert 报错——jump 暂无图行建模）。
12. **Write 落盘**：定稿目录 `25_剧本/ch<NN>/sec<MM>/台词.ink`（本仓库；编号目录：NN=chapter_no、MM=section_no 零填充）。`Section.script_path` 指向此 `.ink` 路径（项目根相对）。Write 自动创建章/节目录。创作土壤在土壤目录（工作区 Harness/25_剧本/ 的同名路径），不往那里写东西。

#### 创作质量自检（发现 outline 破碎 → FAIL 报告）

创作完成后自检，若发现**根本问题在创作土壤而非台词**——再怎么写也写不出合格对话，按根因分两路（都不落盘、不写 status，产出「结构性问题报告」）：

- **根因在草稿层**（跑团模式）：场景帧要素矛盾 / 角色行止与钉子冲突 / scene 间无情绪推进（无 turning point/climax）/ 草稿块结构与图 Choice 分支冲突到无法提炼 → 报告标注「根因 = 草稿层」，由 plot-design 接住后作废定稿链、置 `1` 重入跑团管线（tabletop 守护进程重跑覆盖草稿）；存量小说模式根因（人物速写矛盾/视角漂移等）同走编排回退。**与上游素材不足报告对称**——不硬凑烂对话交付。
- **根因在图素材**（两模式皆可）：分支 options 无戏剧本质差异（flavor 级 Choice）/ 拓扑死胡同或 ending 缺落点（图 option 指向的 Event 缺失）→ 报告标注「根因 = 叙事图」，提示用户跑 `event-ideator` 补全 Choice 分化或落点事件后重调。

> 通过自检才进段 3 写图。

#### 台词层量化自检（ink_line_lint，常规创作与填充模式均必过）

```bash
python "${CLAUDE_SKILL_DIR}/scripts/ink_line_lint.py <台词.ink> --novel <跑团草稿.md|小说.md> [--inner <控制者轨名>]
```

程序判：旁白行长（≤25）/ 旁白连排（<3 行）/ 每块旁白≤say 行数 / 内心轨每块 ≤3、全文 ≤10 / sfx 每块 ≤1、全文 ≤3、描述 ≤10 字 / **搬运率**（旁白+内心轨行与草稿原句连续重叠 ≥10 字的行占比 ≤15%——--novel 对 跑团草稿.md / 小说.md 通用，比对源即 1b-2 判定的创作土壤文件）。**exit 1 = 门禁拦截**——逐条看违规明细就地修后重跑至 PASS；填充模式扩写行同样受检。书面腔内心轨无法程序判，人工按控制者 LS 抽检。

#### §2b 占位填充模式（1a-2 判定进入；只扩写占位，其余行一字不动）

1. Read 台词.ink 全文 + 出场角色 LanguageStyle（同 1b 查询——扩写的语言风格依据）。
2. 逐个 `llm:` 占位：按**上下文**（前后文 + 占位提示语 + 提纲 authoring + 角色 LanguageStyle + 情感弧）扩写为正式 `旁白:` / `角色名:` 行——可一拆多行（如一句占位扩成旁白+对话），扩写内容须完全兑现提示语意图并丰满。
3. **替换写回**：占位行删除、扩写行就位；**其余已有行（含场景块/bed±/sfx/选择/分支/结局）一字不动**——这是手改保护，违者破坏用户内容。
4. 自检：对写回文件跑 `parse_ink`（0 报错、llm_hints 空、bed 配对闭合——Bash `python -c "import sys; sys.path.insert(0, '<skill>/../section-voice-publisher/scripts'); import script_splitter as sp; p=sp.parse_ink('<ink_path>'); assert not p['llm_hints']; print(p['rows'].__len__(), 'rows')" ` 或等价方式）。
5. **写回定稿态**（sec.status=10 重审——扩写为实质内容变更，统一回待审关口，只写此字段）：

```cypher
MATCH (sec:Section {id:'<sec_id>'}) SET sec.status = 10;
```

6. **汇报**：填充 N 处 + 每条「占位提示语 → 扩写成文」前后对照表，提示用户到 dashboard 审批（批准 10→11 后才可拆分配音；也可进定稿编辑器微调，保存即 11）。**填充模式不走创作质量 FAIL**（定稿主体是用户的，不重评结构）。

> 常规创作模式下若确有拿不准的句子：写 `llm:` 占位（产出照常写 10 待审——split 门禁拒绝含占位拆分，天然防漏），下轮本 skill 自动进填充模式补齐（写回重新置 10）。

### 3. 保存结果（写图：SET Section.script_path + status=10，不建节点）

```cypher
MATCH (sec:Section {id:'<sec_id>'})
SET sec.script_path = '<script_path>',   // 25_剧本/.../台词.ink  ← 字段名以 Schema/剧情/Section.md 表为准
    sec.status = 10;            // 定稿产出待审（-1 作废节经此恢复到待审）
```

> BGM 不在本 skill 职责内：BgmTrack（Scene-has_bgm->BgmTrack）由 **scene-design agent 编排 `bgm-designer`** 统一管理（缺口兜底、描述生成、wav 归档检测），plot-design 与本 skill 均不查不调。

**status 写入**：固定 `Section.status=10`（定稿产出**待审**——人工在 dashboard 批准 10→11 后才允许拆分配音/选立绘；驳回 10→-1 由本 skill 重做；人工微调走 dashboard 定稿编辑器，保存即 11 免审）；创作质量 FAIL → 不写 status（见段 2 末尾）。

最后汇总：定稿 `Section.script_path`（台词.ink）、`Section.status=10`（待人工审）、说话行/旁白行/场景段计数。若触发创作质量 FAIL，汇总「结构性问题报告」而非定稿路径。

## 参考文档

- 剧情 Schema：[00_init/Schema/剧情/](../../../00_init/Schema/剧情/) — Section（定稿态载体）/LineAudio 逐句行/produces{order}
- 上游：[tabletop-dialoguer](../tabletop-dialoguer/SKILL.md)（跑团草稿.md 创作土壤，现行链）/[chapter-novelist-mark-delete](../chapter-novelist-mark-delete/SKILL.md)（存量小说.md 链，已软删 2026-11-20）；自检脚本 [fingerprint.py](../../scripts/fingerprint.py)（共享）
- 下游：[section-voice-publisher](../section-voice-publisher/SKILL.md)（sc=11 已批后拆分进图 + 配音）；拆分解析器 [script_splitter.py](../section-voice-publisher/scripts/script_splitter.py)（parse_ink——机器侧权威）；[ink方言规范.md](references/ink方言规范.md)（定稿方言规范权威，与本 SKILL 互链）
