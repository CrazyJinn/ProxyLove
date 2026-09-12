---
name: chapter-dialoguer
description: |
  推进 Section 图节点的定稿段：读 structurer 的章级设计简报 + outliner 的本节提纲 outline.md → 创作逐句对话 → 产出节级 台词.ink（人读/人改的唯一定稿格式，标准合法 ink 方言 v3：场景块「=== <id> // <名>（<时段>）」ASCII knot、说话行「角色名:台词」不写[表情]、旁白行、音频三型 sfx:（点状）/ bed+ bed-（音床起止循环）、ink 原生选择/分支/结局两行式、llm: 占位行）→ 兜底建 SecScript（SecOutline-[:produces]->SecScript）写 script_path + status=10（定稿待审，直写不经 submit）。
  双模式：① 常规创作（本节无定稿或 ink 不含 llm: 占位）——整篇创作；② **填充模式**（SecScript 存在且 ink 含 llm: 行且 sc∈{0,1}）——只把 llm: 占位按上下文扩写成正式行，其余行一字不动，写回并送审（sc→10）。含占位的定稿 split 拒绝拆分。台词.ink 规范见 references/ink方言规范.md（方言 v3）；dashboard 定稿审渲染/编辑器修改；审批通过（sc=11）后由 section-voice-publisher 拆分进图再配音。BGM 不归本 skill（BgmTrack 由 scene-design 编排 bgm-designer 管理）。
  前驱 SecOutline.status=1（提纲就绪）。创作中若发现 outline 戏剧性破碎（分支无本质差异/scene 无情绪推进），产出「结构性问题报告」回退 outliner，不写 status。
argument-hint: <section_id>
arguments:
  - section_id
allowed-tools: Read, Bash, Write, Edit
---

> **status=-1 = 作废重做**：当本节 SecScript 节点被重置为 `status=-1` 时（如 SecOutline/Section/Chapter 属性变更沿 produces/has_outline/has_section 级联），即使 `台词.ink` 已落盘，也**必须重新创作并覆盖**（重走 0→10）。`-1` 明确表示有旧产物要覆盖，**禁止因文件已存在而跳过，也禁止读旧台词内容**，直接以当前图节点数据 + 本节 outline.md + 章级设计简报为唯一来源重新创作。

# 节细节对话（SecScript 定稿段 · status 0→10）

剧情创作流程的**第三段**（节级）。读 `chapter-structurer` 的**章级设计简报**（情感弧/戏剧意图）+ `chapter-outliner` 的**本节提纲 outline.md**，创作逐句对话，产出节级 **`台词.ink`**——人读/人改的定稿 ink 方言（**机器可解析**：审批通过后由 section-voice-publisher 拆分进图）。落盘 `25_剧本/`（**创作/审阅区，非运行时**）。

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| section_id | Section 节点 ID（snowflake） | 必传 |

## 流程（三段式：查状态 → 完成任务 → 保存结果）

> 本 skill 是 SecScript 产物节点的创建点 + 定稿段 status 的唯一写入点；台词.ink 由本 skill 直接创作产出。编剧是高自由度创作任务，**无纯产出子 skill**——创作与写图都在本 skill 内完成。

### 1. 查询目标节点状态

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 查询。

#### 1a. 解析 Section + SecOutline + SecScript + 前驱校验

```cypher
MATCH (ch:Chapter)-[:has_section]->(sec:Section {id:'<input>'})
OPTIONAL MATCH (sec)-[:has_outline]->(ol:SecOutline)
OPTIONAL MATCH (ol)-[:produces]->(sc:SecScript)
RETURN sec.id AS id, sec.section_no AS section_no, sec.title AS title,
       ol.outline_path AS outline_path, ol.status AS ol_status,
       sc.id AS sc_id, sc.script_path AS script_path, sc.status AS sc_status,
       ch.chapter_no AS chapter_no
LIMIT 1
```

**前驱校验**：`ol_status = 1`（提纲就绪，`outline_path` 非空），否则停止并提示先完成本节提纲段（`chapter-outliner`）。

#### 1a-2. 模式判定（常规创作 / 占位填充）

SecScript 已存在且有 `script_path` 时，Read 该 台词.ink 并检查是否含 `llm:` 行：

- **含 `llm:` 占位 且 `sc_status ∈ {0,1}`** → 进入**填充模式**（跳过下文「sc=10/11 停止」拦截与常规创作流程，直接走 §2b）：只扩写占位、其余行一字不动。用户流程是「占位 → LLM 填充 → 人工审阅」，**禁止整篇重写覆盖手改**。
- 无占位（或 SecScript 不存在）→ 常规创作流程。`sc_status` 为 `10/11` 且无占位 → 定稿已待审/已批，停止并提示。

#### 1b. 读设计简报 + 本节提纲 + 查创作上下文

**先读两份创作依据**：
- Read `25_剧本/chapter<NN>_<章概述>/设计简报.md`（NN = chapter_no 零填充，<章概述> 取章 title）——取出情感弧线 / 戏剧意图 / 设计支柱（本节在弧线中的位置靠分节规划定位），本节对话的情感基调全靠它。
- Read **本节** `outline.md`（`SecOutline.outline_path`）——场景分段（Scene 名/时段/scene-block id 契约值）、分支拓扑（choice/label/ending）必须如实体现到台词.ink（见格式规范）；`authoring` 散文（方向/情感弧/约束/职责/节拍/母题锚点/衔接）是创作指引，不进台词；「BGM 倾向」是散文参考（BGM 由 scene-design 编排管理，与本 skill 无关）。

任一缺失则停止并提示先跑上游（structurer / outliner）。

再查图：

```cypher
// 出场角色 + 语言习惯（创作对话的核心依据）——图关系遍历，不按名字列表猜：
// 本节包含的场景 ← 地点 ← 在此地发生的_event ← 参与的角色
MATCH (sec:Section {id:'<input>'})-[:contains]->(s:Scene)<-[:has_scene]-(loc:Location)
MATCH (loc)<-[:occurred_at]-(e:Event)<-[:involved]-(char:Character)
OPTIONAL MATCH (char)-[:has_voice_style]->(voice:LanguageStyle)
RETURN DISTINCT char.name AS name, char.description AS description, char.character_tags AS tags,
       voice.vocabulary AS vocabulary, voice.rhythm AS rhythm,
       voice.habits AS habits, voice.emotion_patterns AS emotion_patterns,
       voice.description AS voice_desc
LIMIT 20
```

### 2. 完成任务（创作细节对话）

读本节 outline.md 逐场景段，据章级设计简报（情感弧/戏剧意图）+ 角色 LanguageStyle，创作逐句对话写入 `台词.ink`。

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

1. **场景块标记**：`=== <scene_block_id> // <Scene 名>（<时段>）`（knot，v2 行式）——scene_block_id 照搬 structurer 预分配值（**ASCII 字母数字下划线、禁连字符**，如 `s00_hotel`，章内唯一），Scene 名/时段照搬提纲契约值挂行尾注释。时段仅供人读（运行时时段以 Scene.time_of_day 为准，拆分进图不存）。
2. **说话行**：`角色名:台词`——一行一句，冒号用**半角**，角色名用 Character.name 原名（「旁白」「sfx」「llm」是保留字）。**禁止写 `[表情]` 标注**（如 `[微笑]`）：本 skill 专注台词创作，演出层（立绘变体选择）与台词**彻底分离**——由 section-voice-publisher 配音判断期为每句 say 行按台词氛围选定（`LineAudio-[:uses]->StandingIllustration` 边），定稿不承载任何演出标注。**残留 `[表情]` 会在拆分时报错**（parse_ink 拒绝带方括号的说话行，报行号+原文）。pos 不进定稿（拆分时定）。
3. **旁白行**：`旁白:叙述`——一行一句，承载环境/动作/心理等非台词叙述。
4. **音频三型（v3，只写声音语义、不写资产名；旧「环境音」两型已废止——写了报错）**：
   - **点状音效**（独立行）：`sfx:语义描述`——极短声音（1~2 秒）运行时**播完再接下一句**台词/旁白（如推门风铃/开门吱呀/远处闷雷）。进图 op=transition，下游 Freesound CC0 实录。
   - **音床起止对**：`bed+ <id> // 语义描述` … `bed- <id>`——区间持续声景**循环播放**（如雨声/街道底噪/电流嗡鸣）。id 限 ASCII 字母数字下划线，同场景块内配对，多床并行/嵌套合法；起止行之间的叙述即床的覆盖区间。进图 op=bed_start（语义=text，AudioFly 声景 ~10s 首尾淡入淡出）/ op=bed_end。
   **克制使用**——只标记叙事上有意义的声音（不是每段旁白都配床），与「短节克制手法」取向一致。
5. **LLM 占位行**：`llm:提示语`——创作期拿不准的句子先占位（简短提示语说明意图/情绪/方向），**不进图、定稿含占位无法拆分**（split 门禁拒绝）；由本 skill 填充模式（见下）扩写为正式行。常规创作完成后**不应残留占位**——占位只用于「草稿暂存、下轮补写」场景（配 SecScript status=1 草稿态，不进审批）。
6. **选择行**（ink 原生 `*`/`+`）：`* 选项文本 -> 去向`——单行，**禁止缩进的选项正文块**（分支正文一律写在 `= <label>` 之后）。去向 = label 名 / scene_block_id（均 ASCII 契约值）/ `END`（直达结局的 kind 写行尾注释 `// ending: <kind>`——仅拓扑记录）。**选择行暂不进图**（choice 建模后续设计）——解析器整行跳过（含行尾 tag/注释）。
7. **分支行**（stitch）：`= <label 名>`（ASCII，照搬提纲契约值）标示分支正文起点（进图 op=label）。
8. **结局两行式**：`<落点一句话> # ending: <kind>`（落点内容行 + 行尾 ending tag，标准 ink）+ 单独一行 `-> END`——解析为单条 op=ending（kind + 落点）。线性节末尾也可加裸 `-> END` 收束。注意 ink 中 `#` 是 tag 非注释，行首 `#` 非法。
9. **覆盖完整**：提纲全部场景段、分支、结局都要写，不得增删场景/分支。
10. **情感递进**：每个场景内部情绪有起伏（不是平铺），对齐设计简报情感弧线的该段位置。
11. **机器可解析（硬约束）**：台词.ink 是 section-voice-publisher 拆分进图（`script_splitter.py parse_ink`）的输入——行型严格依赖行首标记（`===`/`=`/`* `/`+ `/`-> `/`//`/`sfx:`/`llm:`/`bed+`/`bed-`/`旁白:`/`角色名:`），**台词正文中不得出现这些行首前缀**（换行重写）；无法解析的行会在拆分时报错（行号+原文），拆分前必须修 ink。行首 `->` 仅支持裸 `-> END`（其余 divert 报错——jump 暂无图行建模）。
12. **Write 落盘**：`25_剧本/chapter<NN>_<章概述>/sec<MM>_<节概述>/台词.ink`（与该节 outline.md 同目录）。`SecScript.script_path` 指向此 `.ink` 路径。Write 自动创建章/节目录。

#### 创作质量自检（发现 outline 破碎 → FAIL 报告）

创作完成后自检，若发现**根本问题在 outline 而非台词**——即 outline 戏剧性破碎，再怎么写也写不出合格对话：
- 分支 options 无戏剧本质差异（outliner 的本质差异门控漏过的 flavor 级分支）
- scene 间无情绪推进（提纲本身平铺，无 turning point/climax）
- 拓扑死胡同或 ending 缺落点

→ **触发创作质量 FAIL**：**不落盘定稿、不写 SecScript status**，产出「结构性问题报告」返回，列出破碎点（哪个 choice/scene/拓扑 + 为什么写不出合格对话）。由 plot-design 接住后把 `SecOutline.status` 归 `0`（待提纲），重调 `chapter-outliner` 重做本节提纲。**与 outliner 素材不足报告对称**——不硬凑烂对话交付。

> 通过自检才进段 3 写图。

#### §2b 占位填充模式（1a-2 判定进入；只扩写占位，其余行一字不动）

1. Read 台词.ink 全文 + 本节 outline.md + 章级设计简报 + 出场角色 LanguageStyle（同 1b 查询——扩写的语言风格依据）。
2. 逐个 `llm:` 占位：按**上下文**（前后文 + 占位提示语 + 提纲 authoring + 角色 LanguageStyle + 情感弧）扩写为正式 `旁白:` / `角色名:` 行——可一拆多行（如一句占位扩成旁白+对话），扩写内容须完全兑现提示语意图并丰满。
3. **替换写回**：占位行删除、扩写行就位；**其余已有行（含场景块/bed±/sfx/选择/分支/结局）一字不动**——这是手改保护，违者破坏用户内容。
4. 自检：对写回文件跑 `parse_ink`（0 报错、llm_hints 空、bed 配对闭合——Bash `python -c "import sys; sys.path.insert(0, '<skill>/../section-voice-publisher/scripts'); import script_splitter as sp; p=sp.parse_ink('<ink_path>'); assert not p['llm_hints']; print(p['rows'].__len__(), 'rows')" ` 或等价方式）。
5. **送审**（sc→10，复用已有 sc_id；不写其他任何字段）：

```cypher
MATCH (sc:SecScript {id:'<sc_id>'}) SET sc.status = 10;
```

6. **汇报**：填充 N 处 + 每条「占位提示语 → 扩写成文」前后对照表，提示用户到 dashboard 审批中心审阅。**填充模式不走创作质量 FAIL**（定稿主体是用户的，不重评结构）。

> 常规创作模式下若确有拿不准的句子：写 `llm:` 占位 + 把 SecScript 置 `status=1`（草稿态，不进审批——10/11 会被定稿审看到占位且 split 拒绝），下轮本 skill 自动进填充模式补齐。

### 3. 保存结果（写图：MERGE 兜底建 SecScript + produces 边 + 写 script_path/status）

`--multi` 单事务；`sc_id` 用 `snowflake_base62.py` 新生成（已存在 SecScript 时复用其 id）：

```cypher
// 1. MERGE 兜底建 SecScript 产物节点
MERGE (sc:SecScript {id:'<sc_id>'})
SET sc.name = '<节标题>定稿',
    sc.script_path = '<script_path>',   // 25_剧本/.../台词.ink
    sc.status = 10;            // 定稿待审（直写不经 submit）

// 2. 兜底建 produces 边（SecOutline→SecScript，sync=true：改提纲级联作废定稿+全部台词行）
MATCH (ol:SecOutline {id:'<ol_id>'}), (sc:SecScript {id:'<sc_id>'})
MERGE (ol)-[r:produces]->(sc) SET r.sync = true;
```

> BGM 不在本 skill 职责内：BgmTrack（Scene-has_bgm->BgmTrack）由 **scene-design agent 编排 `bgm-designer`** 统一管理（缺口兜底、描述生成、wav 归档检测），plot-design 与本 skill 均不查不调。

**status 写入**：固定 `SecScript.status=10`（定稿待审，等 dashboard `approve`→`11`）；创作质量 FAIL → 不写 status（见段 2 末尾）。

最后汇总：定稿 `SecScript.script_path`（台词.ink）、`SecScript.status=10`、说话行/旁白行/场景段计数。若触发创作质量 FAIL，汇总「结构性问题报告」而非定稿路径。

## 参考文档

- 剧情 Schema：[00_init/Schema/剧情.md](../../../00_init/Schema/剧情.md) — Section/产物链（SecOutline/SecScript/LineAudio 逐句行）/produces{order}/stages 边
- 上游：[chapter-structurer](../chapter-structurer/SKILL.md)（章级设计简报）/ [chapter-outliner](../chapter-outliner/SKILL.md)（本节提纲 → SecOutline status=1）
- 下游：[section-voice-publisher](../section-voice-publisher/SKILL.md)（sc=11 后拆分进图 + 配音）；拆分解析器 [script_splitter.py](../section-voice-publisher/scripts/script_splitter.py)（parse_ink——机器侧权威）；[ink方言规范.md](references/ink方言规范.md)（定稿方言规范权威，与本 SKILL 互链）
