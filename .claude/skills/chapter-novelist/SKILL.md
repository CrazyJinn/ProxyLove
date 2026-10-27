---
name: chapter-novelist
description: |
  推进 Section 图节点的小说段（提纲已内化：**节的提纲即图数据本身**——Event/Info/Choice + 分支骨架；块 id=scene_id 由 1a 机位素材集现场取用；原 chapter-outliner 已废弃并入本 skill，设计简报与 Chapter.summary 已废止不入依据）：按 includes 物化成员圈定取材素材（本节 Event 直连 + involved 角色/Event 一跳 link 的 Info；时间由成员事件推导）→ 丰满度自检（不足拒绝产出报缺口，用户跑 nrt-gap-filler 补全）→ **结构推理在思维链中完成、不落中间提纲文件**（场景段切分 / 分支节点图核验 / 节拍规划）→ 五步产节级散文 小说.md（**纯文件产物，零图写入**；正文 `### <scene_block_id> <场景名> <时段>` 场景段标题承载拓扑契约，id = 所写机位的 scene_id（图即档案）；头部**取材指纹**＝实际取用素材 id + 内容指纹，scripts/fingerprint.py）。重写场景（素材 stale / 用户明示）：覆盖旧文（禁读旧文）且显式作废定稿链（SET Section.status=-1 + 该节全部行 -1）——本 skill 唯一图写入。对账发现的新 Event/Info 走 gap-filler 建议 JSON 通道（source='chapter-novelist'，人工经 dashboard 审阅入库；稀疏 ≤3 Event+2 Info）。
  前驱：无（章无 status、节创建即 11 取消结构审/定稿审；自由节与已组章节均可创作，配音前须组章）。场景段结构以小说 `###` 标题为契约（下游 dialoguer 照搬），分支事实以图 Choice/option 为准。存量直连：无小说.md 且 script_path 已有值的旧流程节不补小说。在需要为某节创作节级小说、plot-design 编排推进小说段、或定稿段报素材 stale 需重写时使用。
argument-hint: <section_id>
arguments:
  - section_id
allowed-tools: Read, Bash, Write, Edit
---

> **stale = 重写覆盖**：小说.md 头部取材指纹与当前图素材不一致（fingerprint.py check 退出码 1）时，**必须重写并覆盖旧文**——禁止因文件已存在而跳过，也**禁止读旧小说正文**（头部块只由脚本解析），直接以当前图数据为唯一来源重新创作；并按段 3 作废定稿链。

# 节小说（小说段 · 纯文件产物，零图写入）

剧情创作流程的**第二段**（节级，在章级结构段之后、定稿段之前）。**节的提纲即图数据本身**：Event（情节，经 includes 物化为节成员）、Info（信息）、Choice/option（分支）、机位素材集（includes→anchored_at，块 id 来源）——结构推理（场景段切分/分支核验/节拍规划）在本 skill 的思维链中完成，**不落任何中间提纲文件**。产出节级散文 **小说.md**（dialoguer 定稿段的创作土壤），**全程零图写入**（唯一例外：stale 重写时显式作废定稿链）。正文 `### <scene_block_id> <场景名> <时段>` 场景段标题即拓扑契约（dialoguer 照搬为 ink 场景块）。

## 参数

| 参数 | 说明 |
|------|------|
| section_id | Section 节点 ID（snowflake）。由 plot-design 编排传入，或用户直接触发。 |

## 流程（三段式：查状态 → 完成任务 → 保存结果）

> 小说.md 的「状态」= 文件存在性 + 取材指纹新鲜度（无图状态）；新鲜度由下游 fingerprint check 兜底——「存在 ≠ 新鲜」。

### 1. 查询目标节点状态 + 圈定素材 + 自检

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 查询。

#### 1a. 解析 Section + 前驱校验

```cypher
MATCH (sec:Section {id:'<input>'})
OPTIONAL MATCH (ch:Chapter)-[:has_section]->(sec)
OPTIONAL MATCH (sec)-[:includes]->(:Event)-[:anchored_at]->(s:Scene)
RETURN sec.id AS id, sec.section_no AS section_no, sec.title AS title, sec.summary AS summary,
       sec.status AS sec_status, sec.script_path AS script_path,
       ch.chapter_no AS chapter_no, ch.title AS ch_title, ch.status AS ch_status,
       collect(DISTINCT s.id) AS scene_ids, collect(DISTINCT s.name) AS scene_names
LIMIT 1
```

**前驱校验**：自由节（无所属章，`ch IS NULL`）**放行**——节由 dashboard ＋新节直建，小说可先于组章创作；有章亦直接放行（结构产出即可用，无审批）。仅须节自身 `sec.status ≠ -1`（作废态表示等重做流程，由编排层处置）。
**模式判定**：
- 小说.md 不存在 → **首建模式**（进 1b）。`script_path` 已有值时为存量直连节：plot-design 编排不会调到（判定在上游）；被用户直接触发 = 显式转新流程，报告「本节为旧流程直连形态，本次建小说层（stale 前不动定稿态）」后继续。
- 小说.md 存在 → 进 1d 指纹自检（stale → 重写模式；新鲜且用户未明示重写 → 汇报退出）。
- **小说路径推导**：有章 `25_剧本/chapter<NN>_<章概述>/sec<MM>_<节概述>/小说.md`；自由节 `25_剧本/自由节/sec<MM>_<节概述>/小说.md`（MM 零填充、概述取 title 清洗 Windows 非法字符——组章重排后重写时按新章路径落盘，旧自由节目录留存为历史）。

#### 1b. 章级依据（图）+ 圈定取材素材

- 1a 查询已带回本节机位素材集 `scene_ids`（includes→anchored_at→Scene 的 DISTINCT id）——**段 id 唯一合法来源 = 所写机位的 scene_id**（同机位多段重复用同一 id，段边界由行序承载）。**创作自由不包括凭空发明地点**：切分只能在素材机位集合内；想写集合外机位（无事件锚定的导语/转场段）时**即停即报**（段名+动机+三可能：隐含事件未建[走 gap-filler 补事件+anchored_at] / 越界脑补[重切] / 事件锚错机位[修 anchored_at]），由用户拍板，禁止自行查图补 id 静默自愈。

圈定查询（一条 UNION，产出指纹素材 JSON；Event 沿 `Section→includes→Event` 直连 Event 驱动化，**includes 即成员、不做任何时间过滤**（节的时间坐标由成员事件推导，跨天节天然支持；旧模型的 `time_day` 时间窗过滤已随 contains 废止、字段本身亦已废止删除），Info 限本节 involved 角色 / Event 一跳 link 防过宽）。场景段标题的场景名/时段来源：`MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)-[:anchored_at]->(s:Scene) RETURN DISTINCT s.name AS name, s.time_of_day AS tod`：

```cypher
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e:Event)
RETURN 'event' AS kind, e.id AS id, e.title AS title, e.time AS time, e.type AS type,
       e.description AS description, e.ending_kind AS ending_kind, e.condition AS condition,
       null AS content, null AS knowledge_level
UNION
MATCH (sec:Section {id:'<sec_id>'})-[:includes]->(e2:Event)
MATCH (src)-[:link]->(i:Info)
WHERE (src:Character AND (src)-[:involved]->(e2)) OR src = e2
RETURN 'info' AS kind, i.id AS id, i.title AS title, null AS time, null AS type,
       null AS description, null AS ending_kind, null AS condition,
       i.content AS content, i.knowledge_level AS knowledge_level
```

Bash 落盘复用（段 3 的 gen 还要用同一份）：`python "${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py" -c "<上句>" --json > .tmp/novelist/<sec_id>_materials.json`（UNION 是单语句，`--json` 输出数组即素材 JSON）。

再查创作上下文（不进指纹）：出场角色 + LanguageStyle（与 chapter-dialoguer 1b 同款查询，对白语感权威源——**人 × 事交集：Event 是情节，LanguageStyle 是语感，小说写的对白必须按图上人设**）。

#### 1c. 丰满度自检（素材门控，不足拒绝产出）

圈定后体检本节素材丰满度（体检查询沿用原 outliner 范式，聚焦本节 Scene 源 Spot 的 Event）：(1) Event 数量（每 Scene 平均不足 ~1 个 = 过少）；(2) Event 间 leads_to 连贯性（链断裂）；(3) Choice option 指向的 target Event 是否存在（分支无落点）；(4) 出场角色 involved 事件数（角色弧空转）。**命中任一 → 停止——不写 status、不落盘**，产出「素材不足报告」（缺口明细）返回，提示用户跑 `nrt-gap-filler` 补全后重调。**禁止硬凑**。够 → 进段 2。

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
3. **节拍规划**：每场景段 3~5 拍（自然语言，思维链内），确定本节 turning point / climax 位置（按事件时序推演）。

#### 2b. 五步创作

1. **进场三问**：粒度 = 节级散文，每场景段约 500~1500 字（指引非硬性）；落点 = galgame 定稿土壤**非连载**——不写章末钩子/上章回顾/平台向调味；**视角人物定死**（依事件与出场角色），写入小说 `## 视角`。
2. **三件事钉人物 + 强场景锚**：每个主要出场角色钉「想要什么 / 怕什么 / 有什么不肯告诉别人的伤」→ 写入 `## 人物速写`（dialoguer 提炼台词的依据）；场景段序 = 强场景锚，**不可动**。
3. **节拍对齐**：按 2a 思维链节拍逐段展开——一场景段一节正文，覆盖全部节拍；**不增删场景、不改分支拓扑**（选择项归属图未定时按「纯角色内心」缺省并标注待定）。
4. **落稿**：只写图素材与节拍已背书的区间；**称谓规则**（穿越/换宿主题材）：内心独白与叙述用本名，说出口的台词用宿主名，叙述句身体动作与心理活动拆开归属；**禁裸 Day 计数**（叙述层用场景指称，如「那天在桥上」）；对白按 LanguageStyle（词汇/节奏/口头禅/情绪模式）。
5. **自检（就地修，不过关不进段 3）**：惯性签名轻检——同一比喻模板连用 ≥3 砍到最妙的 2 处、签名短语全篇 ≤1、场景结尾落点错开（画面/他人的话/动作各占其分）；拓扑复查——场景段数/顺序/分支与 2a 推理及图 Choice 一致；称谓与 Day 计数复查。**去 AI 味重工序不做**——留给 ink 定稿层（chapter-dialoguer）。
6. **标记实际取用素材**（段 3 gen 的输入）：指纹只记**正文实际取用**的素材，不是圈定全部——未使用的 Info 日后修订不得误 stale 本节。创作完成后从圈定清单列出实际用到的素材 id（Event 通常全用；Info 按正文真实引用挑），供段 3 `gen --ids` 使用。

#### 小说.md 结构（固定骨架；`###` 场景段标题 = 拓扑契约，dialoguer 照搬）

```
<!-- 取材指纹(chapter-novelist 生成,chapter-dialoguer 自检;变动=重写小说+作废定稿)
event <id> <hash16> <title>
info  <id> <hash16> <title>
-->                       ← 段 3 由 fingerprint.py gen 产出，Write 时置于文件首
# <节标题> · chapter <NN> 小说
## 视角
<视角人物名 + 一句理由>
## 人物速写
### <角色名>
- 想要：<…>
- 怕：<…>
- 伤：<…>
## 正文
### <scene_block_id> <场景名> <时段>   ← 契约 id/场景名/时段（预分配 id + Scene.name + 时段），每场景段一节
<散文正文…>
```

### 3. 保存结果（指纹头部 + 落盘 + 唯一作废写入 + 对账建议）

1. **指纹头部**：`python "${CLAUDE_SKILL_DIR}/scripts/fingerprint.py" gen --in .tmp/novelist/<sec_id>_materials.json --ids <实际取用素材 id 逗号列表>` → 产出完整头部块（**只含取用子集**——省略 `--ids` 会记圈定全量，禁止）。
2. **Write** 小说.md（头部块置文件首 + 全文）到约定路径。首建模式到此完成（零图写入）。
3. **重写模式才作废定稿链**（首建模式跳过；`sec_status IS NULL` 跳过）——`--multi` 单事务：

```cypher
MATCH (sec:Section {id:'<sec_id>'}) WHERE sec.status <> -1 SET sec.status = -1;
MATCH (sec:Section {id:'<sec_id>'})-[p:produces]->(l:LineAudio) WHERE l.status <> -1 SET l.status = -1;
```

> 作废后行级恢复走重拆机制（text_sha1 匹配且 wav 在的行恢复 10），plot-design 按产物链现状续推 dialoguer 重新提炼。

4. **对账建议（可选）**：段 2 中长出的新 Event/Info（图上查无、值得回写大纲的）→ 组装建议 JSON（契约与纪律见 [nrt-gap-filler](../nrt-gap-filler/SKILL.md) §4，差异仅三处）：
   - `check = 'N1_novel_new_entity'`，`source = 'chapter-novelist'`
   - 落盘 `02_剧情数据/<日期>_round<N>_ch<NN>sec<MM>_<节概述>_补全_建议.json`（必须 `_建议.json` 结尾；轮次 N 扫描 `02_剧情数据/*round*_建议.json` 取 max+1，与 gap-filler 共用计数器）
   - cypher 开箱可执行：只 MERGE 新实体节点 + 定位边（occurs_at/involved/link/leads_to），**禁止 SET 既有实体属性、禁止夹带校验节点**；新 Event 的 title/description 不携带时间信息（时间唯一承载 = `Event.time`）。稀疏纪律：单次至多 3 Event + 2 Info，无新增不落盘只汇报。
5. **汇总**：小说路径 + 取材条数（event/info 分计）+ 模式（首建/重写）+ 是否作废定稿链（sec.status 与行数前后变化）+ 建议 JSON 路径（如有）+ 分支待补标注（如有）+ 自检修正说明。

## 参考文档

- 方法论（节级裁剪）：[references/小说方法论精简版.md](references/小说方法论精简版.md)——五步展开、对账四分类、惯性签名轻检清单
- 指纹契约：[scripts/fingerprint.py](scripts/fingerprint.py) 顶部 docstring（归一化规则 / gen --ids / check）
- 剧情 Schema：[00_init/Schema/剧情.md](../../../00_init/Schema/剧情.md) — Section 定稿态 / 创作流程注记「小说段」
- 上游：[chapter-structurer](../chapter-structurer/SKILL.md)（章级建结构；块 id 预分配已废止，见 1a）
- 下游：[chapter-dialoguer](../chapter-dialoguer/SKILL.md)（读小说.md 提炼 台词.ink，场景段照 `###` 标题；入场 fingerprint check 自检，stale 回退本 skill）
- 建议通道：[nrt-gap-filler](../nrt-gap-filler/SKILL.md) §4（建议 JSON 字段 / 多语句 / 控制台执行）
