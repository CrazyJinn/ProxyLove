---
name: chapter-dialoguer
description: |
  推进 Section 图节点的定稿段：读 novelist 的本节小说.md（小说模式：场景段结构照搬小说 `### <scene_block_id> <场景名> <时段>` 标题——它就是拓扑契约；同源 scripts/fingerprint.py check 自检取材指纹，stale 则停止回退 chapter-novelist；分支事实以图 Choice/option 为准，与小说冲突报 FAIL）→ 从小说提炼逐句对话（钉子句沿用、立场守恒，只做体裁转换）→ 产出节级 台词.ink（人读/人改的唯一定稿格式，标准合法 ink 方言 v3：场景块「=== <id> // <名>（<时段>）」ASCII knot、说话行「角色名:台词」不写[表情]、旁白行、音频三型 sfx:（点状）/ bed+ bed-（音床起止循环）、ink 原生选择/分支/结局两行式、llm: 占位行）→ 唯一图写入 `SET sec.script_path + sec.status=11`（定稿在位；产出即定稿，人工微调走 dashboard 定稿编辑器「保存并同步」，保存即 11）。
  双模式：① 常规创作（本节无定稿/被作废 -1/或 ink 不含 llm: 占位）——整篇创作；② **填充模式**（script_path 已有值且 ink 含 llm: 行）——只把 llm: 占位按上下文扩写成正式行，其余行一字不动，写回（sec.status 保持 11；不消费小说、不走指纹自检）。含占位的定稿 split 拒绝拆分。台词.ink 规范见 references/ink方言规范.md（方言 v3）；sec.status=11 即可由 section-voice-publisher 拆分进图再配音。BGM 不归本 skill（BgmTrack 由 scene-design 编排 bgm-designer 管理）。
  **存量直连模式**：节目录无小说.md 且 sec.script_path 已有历史值的旧流程节（如 chapter00/01 现存节），读该历史文件（outline.md/骨架 ink/dayNN 蓝本）照旧创作，不要求小说。创作中发现分支无本质差异/scene 无情绪推进 → 「结构性问题报告」回退 chapter-novelist（重做小说层）；根因在图素材（事件空洞/链断裂）→ 提示跑 event-ideator，均不写 status。
argument-hint: <section_id>
arguments:
  - section_id
allowed-tools: Read, Bash, Write, Edit
---

> **status=-1 = 作废重做**：当本节 `Section.status` 被重置为 `-1` 时（如 Section/Chapter 属性变更沿 has_section/produces 级联，或小说素材变动由 chapter-novelist 显式作废），即使 `台词.ink` 已落盘，也**必须重新创作并覆盖**（定稿后写回 11）。`-1` 明确表示有旧产物要覆盖，**禁止因文件已存在而跳过，也禁止读旧台词内容**，直接以当前图节点数据 + 创作土壤（小说.md——须先过指纹自检；存量直连节读 script_path 历史文件）为唯一来源重新创作。

# 节细节对话（Section 定稿态 · status=11/-1）

剧情创作流程的**第三段**（节级）。读创作土壤（小说模式：`chapter-novelist` 的**本节小说.md**——场景段照搬其 `###` 拓扑契约；存量直连模式：sec.script_path 历史提纲/骨架文件），**从小说提炼**逐句对话，产出节级 **`台词.ink`**（落盘 25_剧本/ch<NN>/sec<MM>/，编号目录）——人读/人改的定稿 ink 方言（**机器可解析**：确认后由 section-voice-publisher 拆分进图）。落盘 `25_剧本/ch<NN>/sec<MM>/`（编号目录；**创作/审阅区，非运行时**）。

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
RETURN sec.id AS id, sec.section_no AS section_no, sec.title AS title,
       sec.script_path AS script_path, sec.status AS sc_status,
       ch.chapter_no AS chapter_no
LIMIT 1
```

#### 1a-2. 模式判定（作废重做 / 常规创作 / 占位填充）

`script_path` 已有值时，Read 该 台词.ink 并检查是否含 `llm:` 行：

- **`sc_status = -1`** → 作废重做：整篇重新创作覆盖（见顶部注记）。
- **含 `llm:` 占位** → 进入**填充模式**（直接走 §2b）：只扩写占位、其余行一字不动。用户流程是「占位 → LLM 填充 → 人工微调」，**禁止整篇重写覆盖手改**。
- **无占位 且 script_path 已有值** → 定稿在位（sc=11），停止并提示（防覆盖手改/已定稿；要重做先经 novelist 作废或用户明示）。
- **script_path 为空** → 常规创作流程。

#### 1b. 章级依据（图）+ 创作土壤（小说 / 存量提纲）+ 查创作上下文

**先读两份创作依据**：
- **创作土壤二选一（按 1b-2 判定）**：
  - **小说模式**：Read 节目录 `小说.md`（chapter-novelist 产出）——`### <scene_block_id> <场景名> <时段>` 场景段标题是拓扑契约（场景块 id/顺序唯一来源，照搬不改写）；`## 视角`/`## 人物速写`/正文是创作土壤。
  - **存量直连模式**：Read `sec.script_path` 指向的历史文件（旧 outline.md / 骨架 ink / dayNN 蓝本），场景分段与分支拓扑照旧以它为准。

再查图（角色 LanguageStyle 同前 + **分支骨架**——分支事实权威在图 Choice/option，小说模式必查：`MATCH (sec:Section {id})-[:includes]->(e:Event) OPTIONAL MATCH (e)-[:presents]->(choice:Choice) OPTIONAL MATCH (choice)-[op:option]->(target:Event) RETURN …`，Choice 的 options/label/去向以此为准核对小说结构）。

再查图：

```cypher
// 出场角色 + 语言习惯（创作对话的核心依据）——图关系遍历，不按名字列表猜：
// 本节 includes 的事件 ← 参与的角色
MATCH (sec:Section {id:'<input>'})-[:includes]->(e:Event)
MATCH (e)<-[:involved]-(char:Character)
OPTIONAL MATCH (char)-[:has_voice_style]->(voice:LanguageStyle)
RETURN DISTINCT char.name AS name, char.description AS description, char.character_tags AS tags,
       voice.vocabulary AS vocabulary, voice.rhythm AS rhythm,
       voice.habits AS habits, voice.emotion_patterns AS emotion_patterns,
       voice.description AS voice_desc
LIMIT 20
```

#### 1b-2. 创作土壤判定 + 取材指纹自检（填充模式跳过本节）

**按小说.md 存在性判定**：
- 节目录 `小说.md` 存在 → **小说模式**（下文必过指纹自检）。
- 无 `小说.md` 且 `script_path` 已有历史值 → **存量直连模式**（旧流程节，读该历史文件照旧创作，跳过指纹自检）。
- 无 `小说.md` 且 `script_path` 为空 → 停止并提示先跑 `chapter-novelist <sec_id>`（小说段未做，台词须从小说提炼）。

**小说模式必过指纹自检**（小说是纯文件产物，新鲜度由内容指纹保证——status 只标记「产出过」不实时反映素材变动）：

```bash
# 1) 圈定素材（与 chapter-novelist 1b 同一条 UNION 查询,includes 物化成员直取,见该 SKILL.md）
python "${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py" -c "<圈定 UNION 查询>" --json > .tmp/novelist/<sec_id>_materials.json
# 2) 自检（同源脚本,归一化规则与生成侧一致）
python "${CLAUDE_SKILL_DIR}/../chapter-novelist/scripts/fingerprint.py" check --novel "<小说.md>" --in .tmp/novelist/<sec_id>_materials.json
```

- **exit 0（新鲜）** → 小说可用，进入段 2 提炼。
- **exit 1（stale：已记素材变动/被删）** → **停止**，产出报告（stale 明细 + 「需先重跑 chapter-novelist 重写小说并作废定稿」）退出——本 skill 不作废 sc（职责在 novelist），plot-design 接住后调 novelist，重写后本 skill 重新提炼。圈定内未标注（未使用）的素材不算 stale，属常态。

### 2. 完成任务（从小说提炼细节对话）

按 1b-2 判定的创作土壤逐场景段（小说模式的小说 `###` 结构 / 存量直连模式的历史文件），据角色 LanguageStyle 与事件脉络，**从小说提炼**逐句对话写入 `台词.ink`。

#### 从小说提炼台词的纪律（小说模式）

- **拓扑契约权威 = 小说 `### <scene_block_id> <场景名> <时段>` 场景段标题**（场景块 id/顺序唯一来源，照搬为 ink `=== <id> // <名>（<时段>）`，不改写不自创）；**分支事实权威 = 图 Choice/option**——小说结构与图分支冲突时报 **FAIL**（回退 chapter-novelist），不静默对齐。
- **钉子句沿用**：小说中的关键锚点句（人物速写/正文中的定调句）原样进台词，读者跨层要认得同一根钉子。
- **立场守恒**：事实、事件顺序、情感极性、节拍位置零变化——只做**体裁转换**（散文 → say + 旁白），不改剧情、不加私货反转。
- **对白重塑**：小说对白按角色 LanguageStyle 重塑后进 say 行（小说口语 ≠ 台词定稿）；叙述散文浓缩进旁白行（旁白克制，galgame 旁白行远少于散文段落）。
- **去 AI 味重工序在本层做**（novelist 只做了惯性签名轻检）：台词层的库存句换角色性格推出的话、留白要有锚点——详见格式规范与方言规范。

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
4. **音频三型（v3，只写声音语义、不写资产名；旧「环境音」两型已废止——写了报错）**：
   - **点状音效**（独立行）：`sfx:语义描述`——极短声音（1~2 秒）运行时**播完再接下一句**台词/旁白（如推门风铃/开门吱呀/远处闷雷）。进图 op=transition，下游 Freesound CC0 实录。
   - **音床起止对**：`bed+ <id> // 语义描述` … `bed- <id>`——区间持续声景**循环播放**（如雨声/街道底噪/电流嗡鸣）。id 限 ASCII 字母数字下划线，同场景块内配对，多床并行/嵌套合法；起止行之间的叙述即床的覆盖区间。进图 op=bed_start（语义=text，AudioFly 声景 ~10s 首尾淡入淡出）/ op=bed_end。
   **克制使用**——只标记叙事上有意义的声音（不是每段旁白都配床），与「短节克制手法」取向一致。
5. **LLM 占位行**：`llm:提示语`——创作期拿不准的句子先占位（简短提示语说明意图/情绪/方向），**不进图、定稿含占位无法拆分**（split 门禁拒绝）；由本 skill 填充模式（见下）扩写为正式行。常规创作完成后**不应残留占位**——占位只用于「草稿暂存、下轮补写」场景（status 保持 11，split 门禁天然防漏拆分）。
6. **选择行**（ink 原生 `*`/`+`）：`* 选项文本 -> 去向`——单行，**禁止缩进的选项正文块**（分支正文一律写在 `= <label>` 之后）。去向 = label 名 / scene_block_id（均 ASCII 契约值）/ `END`（直达结局的 kind 写行尾注释 `// ending: <kind>`）。**连续选择行聚合进图一条 op=choice**（options 含 label+去向，运行时弹选项跳转；选项文本改 → 行 update，无音频损失）。
7. **分支行**（stitch）：`= <label 名>`（ASCII，照搬提纲契约值）标示分支正文起点（进图 op=label）。
8. **结局两行式**：`<落点一句话> # ending: <kind>`（落点内容行 + 行尾 ending tag，标准 ink）+ 单独一行 `-> END`——解析为单条 op=ending（kind + 落点）。线性节末尾也可加裸 `-> END` 收束。注意 ink 中 `#` 是 tag 非注释，行首 `#` 非法。
9. **覆盖完整**：提纲全部场景段、分支、结局都要写，不得增删场景/分支。
10. **情感递进**：每个场景内部情绪有起伏（不是平铺），对齐事件时序与章概要的节奏。
11. **机器可解析（硬约束）**：台词.ink 是 section-voice-publisher 拆分进图（`script_splitter.py parse_ink`）的输入——行型严格依赖行首标记（`===`/`=`/`* `/`+ `/`-> `/`//`/`sfx:`/`llm:`/`bed+`/`bed-`/`旁白:`/`角色名:`），**台词正文中不得出现这些行首前缀**（换行重写）；无法解析的行会在拆分时报错（行号+原文），拆分前必须修 ink。行首 `->` 仅支持裸 `-> END`（其余 divert 报错——jump 暂无图行建模）。
12. **Write 落盘**：`25_剧本/ch<NN>/sec<MM>/台词.ink`（编号目录：NN=chapter_no、MM=section_no 零填充，与该节小说.md 同目录）。`Section.script_path` 指向此 `.ink` 路径。Write 自动创建章/节目录。

#### 创作质量自检（发现 outline 破碎 → FAIL 报告）

创作完成后自检，若发现**根本问题在创作土壤而非台词**——再怎么写也写不出合格对话，按根因分两路（都不落盘、不写 status，产出「结构性问题报告」）：

- **根因在小说层**（小说模式）：人物速写自相矛盾 / 视角漂移 / scene 间无情绪推进（无 turning point/climax）/ 小说场景段结构与图 Choice 分支冲突到无法提炼 → 报告标注「根因 = 小说层」，由 plot-design 接住后调 `chapter-novelist` 强制重写（重写即按其段 3 作废定稿链）。**与 novelist 素材不足报告对称**——不硬凑烂对话交付。
- **根因在图素材**（两模式皆可）：分支 options 无戏剧本质差异（flavor 级 Choice）/ 拓扑死胡同或 ending 缺落点（图 option 指向的 Event 缺失）→ 报告标注「根因 = 叙事图」，提示用户跑 `event-ideator` 补全 Choice 分化或落点事件后重调。

> 通过自检才进段 3 写图。

#### §2b 占位填充模式（1a-2 判定进入；只扩写占位，其余行一字不动）

1. Read 台词.ink 全文 + 出场角色 LanguageStyle（同 1b 查询——扩写的语言风格依据）。
2. 逐个 `llm:` 占位：按**上下文**（前后文 + 占位提示语 + 提纲 authoring + 角色 LanguageStyle + 情感弧）扩写为正式 `旁白:` / `角色名:` 行——可一拆多行（如一句占位扩成旁白+对话），扩写内容须完全兑现提示语意图并丰满。
3. **替换写回**：占位行删除、扩写行就位；**其余已有行（含场景块/bed±/sfx/选择/分支/结局）一字不动**——这是手改保护，违者破坏用户内容。
4. 自检：对写回文件跑 `parse_ink`（0 报错、llm_hints 空、bed 配对闭合——Bash `python -c "import sys; sys.path.insert(0, '<skill>/../section-voice-publisher/scripts'); import script_splitter as sp; p=sp.parse_ink('<ink_path>'); assert not p['llm_hints']; print(p['rows'].__len__(), 'rows')" ` 或等价方式）。
5. **写回定稿态**（sec.status=11，只写此字段——-1 作废节经此恢复）：

```cypher
MATCH (sec:Section {id:'<sec_id>'}) SET sec.status = 11;
```

6. **汇报**：填充 N 处 + 每条「占位提示语 → 扩写成文」前后对照表，提示用户可到 dashboard 定稿编辑器查看/微调（保存即 11）。**填充模式不走创作质量 FAIL**（定稿主体是用户的，不重评结构）。

> 常规创作模式下若确有拿不准的句子：写 `llm:` 占位（status 保持 11——split 门禁拒绝含占位拆分，天然防漏），下轮本 skill 自动进填充模式补齐。

### 3. 保存结果（写图：SET Section.script_path + status=11，不建节点）

```cypher
MATCH (sec:Section {id:'<sec_id>'})
SET sec.script_path = '<script_path>',   // 25_剧本/.../台词.ink
    sec.status = 11;            // 定稿在位（产出即定稿，无审批；-1 作废节经此恢复）
```

> BGM 不在本 skill 职责内：BgmTrack（Scene-has_bgm->BgmTrack）由 **scene-design agent 编排 `bgm-designer`** 统一管理（缺口兜底、描述生成、wav 归档检测），plot-design 与本 skill 均不查不调。

**status 写入**：固定 `Section.status=11`（定稿在位 取消定稿审，产出即定稿；人工微调走 dashboard 定稿编辑器，保存即 11）；创作质量 FAIL → 不写 status（见段 2 末尾）。

最后汇总：定稿 `Section.script_path`（台词.ink）、`Section.status=11`、说话行/旁白行/场景段计数。若触发创作质量 FAIL，汇总「结构性问题报告」而非定稿路径。

## 参考文档

- 剧情 Schema：[00_init/Schema/剧情.md](../../../00_init/Schema/剧情.md) — Section（定稿态载体）/LineAudio 逐句行/produces{order}
- 上游：[chapter-novelist](../chapter-novelist/SKILL.md)（本节小说.md 创作土壤 + 场景段拓扑契约 + 取材指纹；自检脚本 [fingerprint.py](../chapter-novelist/scripts/fingerprint.py)）
- 下游：[section-voice-publisher](../section-voice-publisher/SKILL.md)（sc=11 后拆分进图 + 配音）；拆分解析器 [script_splitter.py](../section-voice-publisher/scripts/script_splitter.py)（parse_ink——机器侧权威）；[ink方言规范.md](references/ink方言规范.md)（定稿方言规范权威，与本 SKILL 互链）
