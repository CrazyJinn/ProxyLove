---
name: plot-design
description: |
  剧情创作生产链编排层——查询图状态、按依赖调度 skill/agent 推进小节剧本（节级产物链小说/定稿/拆分配音/环境音）与按需立绘。
  只支持单节聚焦粒度（section id，只推该节的小说/定稿/配音/环境音/该节台词 uses 边引用的立绘，由 dashboard「推进此节」入口或用户直呼触发）——无章级全量模式，输入不认章节标识。
  当用户需要推进某一小节的创作流程、查看小节进度、或处理剧本/配音/立绘相关任务时使用。
permissionMode: bypassPermissions
tools: Read, Grep, Glob, Bash, Skill, Write
---

## 概述

剧情创作生产链的**纯编排层**。只负责查询图状态、决定下一步、调度 skill。所有节点的创建、更新、status 推进由各 skill 自行完成。

Schema 文件：`00_init/Schema/剧情.md`（Chapter/Section（定稿态载体）+ LineAudio 逐句行 + has_section/produces{order}/includes/appears_as/uses 边——节级产物节点已删，小说.md/台词.ink 为纯文件产物）。
输入：**小节 section id**（snowflake ID；dashboard「推进此节」按钮传入或用户直呼）。一次 cypher 查询即可拿到该 Section（定稿态）+ 逐句行聚合 + includes 的事件 + 该节台词 uses 引用与 includes 链 appears_as 的立绘 status，据 status 决定下一步。

**小节产生于 event 之后**：Section 是对既有 Event 的组织（先事件、后分节）——节不是从零创作的入口，而是把图上已有事件圈选归组的人工地标。因此**建章分节不经 plot-design**：章级结构规划由用户直接触发 `chapter-structurer`（或用 dashboard 剧情 tab 的人工编排直写通道「＋新节/组章」）。plot-design 只接收**已存在**的 section id，推进其产物链；章未建、节未分、结构重排均不是本 agent 的调度对象。

创作链（节级）= **各节小说段（chapter-novelist：提纲已内化——结构推理在思维链完成，产 小说.md 纯文件产物，零图写入）→ 各节定稿段（台词.ink，dialoguer 从小说提炼，写 Section.status=10 定稿待审）——小说→定稿同轮连续推进、中间零停等（小说无人工审环节，人工把关点唯一 = 定稿审）→ 人工定稿审（dashboard 批准 10→11 / 驳回 10→-1，plot-design 在 10 态停等）→ 各节拆分+选绘+配音段 → 各节音频环境段（sfx 点状实录 / bed 音床声景）→ 各节逐句音频审（配音+环境音行）→ 立绘（按需）**，到该节就绪为止。
- **节级链（最薄图）**（各节独立推进、独立重做；`Section（编排+定稿态） -[:produces {order}]-> LineAudio(×N 逐句行)`，节级产物节点已删）：每节独立走 `chapter-novelist`（**节级小说段，提纲已内化**——节的提纲即图数据本身（Event/Fact/Lore/Choice + 机位素材集），原 chapter-outliner 已废弃、设计简报已废止；结构推理（场景段切分/分支核验/节拍规划）在 novelist 思维链完成不落提纲文件；按 `Section→includes` 物化成员圈定素材 + 丰满度自检；产 小说.md 纯文件产物（节目录约定路径；正文 `### <scene_block_id> …` 场景段标题承载拓扑契约，id = 所写机位 scene_id；头部取材指纹 fingerprint.py）；**零图写入**（唯一例外 = stale 重写时显式作废定稿链）；对账新实体走建议 JSON 通道 source='chapter-novelist'）→ `chapter-dialoguer`（**从小说提炼台词**：产 `台词.ink` 人读定稿，唯一图写入 `SET sec.script_path + sec.status=10`（定稿产出**待审**——人工批准 10→11 后才可拆分，驳回 10→-1 重做；填充模式写回同置 10）；场景段照搬小说 `###` 标题、分支以图 Choice 为准；入场用同源 fingerprint.py check 自检，stale 则停止回退 novelist）→ **人工定稿审（dashboard 批准 10→11；plot-design 遇 10 态停等汇报，不推进该节）** → `section-voice-publisher`（**第一步拆分进图**：script_splitter.py 对齐 台词.ink ↔ 已有行 → 逐句 LineAudio 节点；第二步挑行 + 产选绘候选池 portrait_binder candidates；第三步 LLM 逐句判 emotion/clone_mode/tts_text/**选立绘 stand**；第四步 apply 建边——`LineAudio-[:uses]->stand`（sync=false）每句一条 + 新变体缺口兜底建（expands_to；不建 depicts/ref_style——边已废止）；第五步 TTS 克隆 + bind-graph 写行节点 status=10）→ `ambient-sfx-designer`（音频环境行（op=transition 点状 sfx 与 op=bed_start 音床）：点状走 Freesound CC0 实录、声景走 AudioFly 生成，产 wav 写 ambient_track + status=10）→ 逐句音频审（行 status 10→11）。
- **小说段文件契约**（对「调度只看 status」铁律的**唯一显式例外**）：小说.md 的「已产」判据 = 文件存在（节目录约定路径推导），「新鲜」判据 = 取材指纹自检（dialoguer 1b-2 兜底，plot-design 不自跑 fingerprint）；**存在 ≠ 完成**，禁止把文件存在当跳过依据——最终由 dialoguer 的 stale 自检把关。**素材变动链路**：Event/Hook/Lore 属性变更（叙事出边全 sync=false，图级联不触达小说）→ 下次推进该节时 dialoguer 自检报 stale → plot-design 调 `chapter-novelist <sec_id>` 重写覆盖（novelist 显式 `SET sec.status=-1` + 全部行 -1，行级恢复走重拆机制）→ 续推 dialoguer 重新提炼。**存量直连**：无小说.md 且 sec.script_path 已有历史值的旧流程节（chapter00/01 现存节），dialoguer 读该历史文件照旧创作，不补小说；被作废打回（sec.status=-1）的节按新流程重走 novelist。
- **台词模型**：台词.ink（ink 方言）是人读/人改的唯一定稿格式（机器可解析）；图行是结构化真相——行身份 = 节点雪花 id（voice key = hexid(行id)，插入/删除行不漂移；母带唯一权威 = 行属性 master_path）；顺序 = produces 边 order（大间距 ×1000，句间插入取中点）；`台词.jsonl` 已停产。
- **LineAudio 行级审批**（行节点 status，只代表音频——文字审批已在 Section 定稿审（10→11）完成）：say 行 `0` 待配/被驳回 → `10` 配完待审 → `11` 已通过；非 say 行拆分即 11。「节完成」gate = 该节全部行 status=11（派生判断）；单句驳回后审批卡出现「重生成」deeplink 唤起本 agent 单节聚焦（voice-publisher `--nodes <行id>` 只重做该句）。
- **定稿审（Section 10→11）与驳回**：dialoguer 产出置 10 后，人工在 dashboard 审批中心/看板批准（→11，随后 plot-design 继续拆分配音）或驳回（→-1，plot-design 下轮重调 dialoguer 整篇重写）。**人工微调回路（不经审批）**：用户在 dashboard 定稿编辑器直改 `台词.ink` → 「保存并同步 LineAudio」（写文件 + 对齐进图：被改句置 0、删行清 wav、新行入图，未变句审批结果不动）→ **sec.status=11（编辑保存即定稿，人工编辑免审）** → 重跑 voice-publisher 重拆：text_sha1 匹配的行原样保留审批结果（含 11），只有被改句置 0 重配——手改不丢。**plot-design 看到行 status≠11 即需推配音**。
- **节完成**（派生判断）= Section.status=11 ∧ 该节全部 LineAudio 行=11（Section.status=11 即定稿已批）。
- 立绘由 plot-design 按引用直调 `char-stand-designer` 推进（已从 char-design 剥离；推进范围 = 本节 say 行 uses 边可达，严禁做后续节的事情）。**立绘上游 IllusDesign 未就绪时报警，不跨链调 char-design**。**event 素材不足时 novelist 丰满度自检拒绝产出并报告缺口**，plot-design 汇报后退出——用户需用独立流程 `event-ideator` 补全叙事基础后重调 plot-design。
- **BGM 不归 plot-design 编排**：BgmTrack（`Scene -has_bgm-> BgmTrack`，0→1→2 无审批）由 **scene-design agent 编排 `bgm-designer`** 推进（缺口兜底建 + 产描述 → 用户手动生成 wav 归档 `13_BGM/`）。plot-design 不调 bgm-designer、不检查 BgmTrack status（发布时 publisher 对 status<2 的警告跳过）。
- **发布不在 plot-design 职责内**：该节产物就绪（Section.status=11 ∧ 行全 11）后汇报并退出；`chapter-publisher` 由**用户直接触发**，plot-design **任何情况下不调它**（如同不跨链调 char-design）。

---

## 工作流

### 1. 解析小节

从用户输入提取 **section id**（snowflake ID；dashboard「推进此节」按钮传入，或用户直呼小节标识）：

- `MATCH (sec:Section {id:'<输入>'}) RETURN sec.id`——命中即进入推进流程，顺带 `MATCH (ch:Chapter)-[:has_section]->(sec) RETURN ch.id AS ch_id` 取所属章（章无 status，存在即结构就绪）。
- 用户以标题/名称等非 id 形式指节时，先按名称查：`MATCH (sec:Section) WHERE sec.title='<名称>' RETURN sec.id, sec.title LIMIT 5`，命中（唯一/用户确认）即同上。
- **输入不认章节标识**：用户给章节标题/序号/章 ID 时，不进入章级推进（无此模式），列出该章各 Section 概况请用户指定要推进的节。
- 自由节（无所属章）可推小说/定稿（`section-voice-publisher` 需 chapter_stem，配音前须组章）。

### 2. 查询当前状态

通过 `python .claude/scripts/cypher_exec.py -c "<cypher>" --json`（只读查询）以目标 Section 为锚点**三条查询**（① 节级行聚合 ② 事件-机位-立绘明细 ③ say 行缺选绘），LLM 侧合并判读（含行聚合、该节 say 行 uses 引用的立绘（**推进范围**）、includes→Event→refines→SubEvent→appears_as 立绘（**仅提示**）；聚合形态双后端兼容——WITH 物化 + 列表推导计数，见 cypher_exec.py 硬约束 11）：

```cypher
// ① 节级行聚合（自由节无所属章 → ch_* 为 null 照常返回）
MATCH (sec:Section {id:'<sec_id>'})
OPTIONAL MATCH (ch:Chapter)-[:has_section]->(sec)
OPTIONAL MATCH (sec)-[:produces]->(l:LineAudio)
OPTIONAL MATCH (l)-[:uses]->(ustand:StandingIllustration)
WITH sec, ch,
     collect(DISTINCT l {.id, .op, .status}) AS lines,
     collect(DISTINCT ustand {.id, .variant_label, .status}) AS ustands
RETURN sec.id AS sec_id, sec.section_no AS sec_no, sec.title AS sec_title,
       sec.script_path AS script_path, sec.status AS sc_status,
       ch.id AS ch_id, ch.title AS ch_title,
       size([x IN lines WHERE x IS NOT NULL]) AS line_count,
       size([x IN lines WHERE x IS NOT NULL AND x.status = 11]) AS line_done,
       size([x IN lines WHERE x IS NOT NULL AND x.op = 'say']) AS say_count,
       size([x IN lines WHERE x IS NOT NULL AND x.op = 'say' AND x.status = 11]) AS say_done,
       size([x IN lines WHERE x IS NOT NULL AND (x.op = 'transition' OR x.op = 'bed_start')]) AS amb_count,
       size([x IN lines WHERE x IS NOT NULL AND (x.op = 'transition' OR x.op = 'bed_start') AND x.status = 11]) AS amb_done,
       size([x IN ustands WHERE x IS NOT NULL AND x.status = 11]) AS used_done,
       [x IN ustands WHERE x IS NOT NULL AND x.status <> 11 | x.id + '/' + coalesce(x.variant_label, '') + ':' + toString(x.status)] AS used_pending;

// ② 事件-机位-立绘明细（includes→refines→SubEvent 链；appears_as 枚举仅提示）
MATCH (sec:Section {id:'<sec_id>'})
OPTIONAL MATCH (sec)-[:includes]->(e2:Event)
OPTIONAL MATCH (e2)-[:refines]->(:SubEvent)-[:anchored_at]->(s:Scene)
OPTIONAL MATCH (e2)-[:refines]->(:SubEvent)-[:appears_as]->(illus:IllusDesign)
OPTIONAL MATCH (illus)-[:expands_to]->(stand:StandingIllustration)
RETURN e2.id AS event_id, e2.time AS event_time, s.id AS scene_id, s.name AS scene_name,
       illus.id AS illus_id, illus.status AS illus_status,
       stand.id AS stand_id, stand.variant_label AS variant, stand.status AS stand_status
ORDER BY event_time, variant;

// ③ say 行缺选绘专项（无 uses 边的 say 行）
MATCH (sec:Section {id:'<sec_id>'})
OPTIONAL MATCH (sec)-[:produces]->(l:LineAudio)
WITH sec, collect(DISTINCT CASE WHEN l.op = 'say' AND NOT (l)-[:uses]->(:StandingIllustration) THEN l.id END) AS ids
RETURN size([x IN ids WHERE x IS NOT NULL]) AS say_no_stand, [x IN ids WHERE x IS NOT NULL] AS say_no_stand_ids
```

派生规则：`line_count=0` = 无行（未拆分）。聚合按 op 拆分（防路由死循环）：配音看 `say_*`（`say_done<say_count` = 存在未配音行）、环境音看 `amb_*`（`amb_count>0 ∧ amb_done<amb_count` = 环境音待产/待审）；`say_no_stand` = 该节 say 行**缺选绘数**（无 uses 边）——行未全 11 时无需关心（配音轮选绘会顺带建边），`sec.status=11 ∧ 行全 11 ∧ say_no_stand>0` 时**仅汇报缺口**（如需补选 = 整句置 0 重配音，成本决策交用户，**不自动触发**）；「节全部行就绪」= `line_count>0 ∧ line_done=line_count`（含 narrate 等非音频行——拆分即 11，天然满足）。**小说探测**（纯文件产物，不在图上）：小说路径 = 节目录约定 `小说.md`（Bash `test -f` 只读探测）；存在性 + `sc_status` 决定小说段动作（见决策），**新鲜度不在编排层判**（指纹自检是 dialoguer 1b-2 的职责）。

**查询必须覆盖全部依赖节点，尤其不得遗漏 `status=-1`/`0` 的待办节点**（这是最常见的失误源）：

- **禁止**在 WHERE 加 `status >= 0` 之类过滤把 `-1` 滤掉——`-1`（作废重做）与 `0`（待生成）都是必须推进的待办，不是「已完成」也不是「不存在」。
- **判断节点有无 status 必须用 `is not None`**——`status=0`（待处理）是合法 falsy，真值判断会误隐藏。
- 用 `OPTIONAL MATCH` 保证首次推进（produces/includes/uses 边尚未建立）也能返回 Section 本身；行同理——**sec.status=0（无行）= 该节小说/定稿未做**，**sec.status=10 = 定稿已产待人工审（本 agent 停等，不推进）**，**sec.status=11 且 say_count=0 = 该节定稿已批、待拆分配音**，不是异常。
- 限定边类型的变长路径回溯立绘所属角色（复用美术边类型集 `has_appearance|has_voice_style|has_costume|produces|outfit_for|expands_to`（ref_style 已删）），既能明确范围，又能阻止遍历越界到叙事 Event / 其他角色。

**写边严格按 Schema 方向（上游→下游）**，见 [00_init/Schema/剧情.md](00_init/Schema/剧情.md) 与 [00_init/Schema/角色美术.md](00_init/Schema/角色美术.md)。`has_section` 是 `Chapter→Section`；`produces` 是 `Section→LineAudio`（1:N 带 order）；`includes` 是 `Section→Event`（order=事件 time 序;节内 Scene 经 `Event→refines→SubEvent→anchored_at` 推导）；`appears_as` 是 `SubEvent→IllusDesign`（Event 经 `refines→SubEvent` 到达，直挂为违规；形象版本写边时物化;变体经 `IllusDesign-[:expands_to]->StandingIllustration` 枚举）；`uses` 是 `LineAudio→StandingIllustration`（选绘行级引用，sync=false 固定）；`StandingIllustration` 是 `expands_to`/`uses` 的**目标端**（入边），不是源——把方向写反会让 MATCH 静默返回空，进而误报「节点未创建」。

### 3. 决策与调度

**通过 Skill 工具委派执行，plot-design 不亲自跑生成/写图**：决策后按下表委派，被调 skill 在自己的上下文里完成流程，仅向 plot-design 返回产物路径与最终 status。**plot-design 自身禁止用 Bash 执行 cypher 写入、snowflake、剧本生成、拆分、配音、立绘生成**——这些是各 skill 的职责；plot-design 只用 Bash 执行第 2 步的只读状态查询。

**只处理目标节**（查询见第 2 步），不枚举其他节、不建章分节、不发布：

- **前置**：无章级门控（章无 status）——目标节有所属章即可推（组章即结构就绪）；自由节（无所属章）可推小说/定稿（`section-voice-publisher` 需 chapter_stem，配音前须组章）。
- **小说**（节目录无 小说.md 且非存量直连）→ `Skill chapter-novelist <sec_id>`（提纲内化：结构推理思维链 + 丰满度自检 + 产 小说.md，零图写入；返回「素材不足」按现状汇报缺口退出）；无 小说.md 且 `script_path` 已有历史值 → **存量直连**（旧流程节，跳过小说段）；有 小说.md → 直接进定稿判定（stale 自检是 dialoguer 的活；dialoguer 返回 stale 报告 → `Skill chapter-novelist <sec_id>` 重写（作废定稿链 sec.status=-1 + 全部行 -1）→ 回到定稿判定续推）。**novelist 正常返回后同轮立即调 dialoguer 续推定稿，不停等人工过目小说、不询问「是否继续」**——小说无人工审环节，首次推进一口气到 台词.ink 置 10（定稿待审）才停。
- **定稿**（有 小说.md 或存量直连，且（`script_path` 为空 ∨ `sc_status = -1`））→ `Skill chapter-dialoguer <sec_id>`（小说模式从小说提炼、存量直连模式读历史文件；产台词.ink → `SET sec.script_path + sec.status=10` 定稿待审；返回 stale 报告按上条回退 novelist）。`sc_status = 10` → **定稿待人工审，本节停**（汇报「定稿待审，请到 dashboard 审批中心/看板批准（10→11）或驳回（10→-1）」，不推进拆分/配音/环境音/立绘）。`script_path` 已有值且 `sc_status = 11` → 定稿已批，dialoguer 会拒绝覆盖，直接看拆分配音判定。
- **拆分+选绘+配音**（`sc_status = 11` 且（`say_count=0` ∨ `say_done < say_count`））→ `Skill section-voice-publisher <sec_id>`（拆分进图 + 挑行选绘 + TTS → 待审行 status=10），随后继续本节后续判定（环境音/立绘）。
- **环境音**（`sc_status = 11` 且 `amb_count > 0` 且 `amb_done < amb_count`）→ `Skill ambient-sfx-designer <sec_id>`（产出待产 ambient 行 → status=10 待审），随后继续本节后续判定（立绘）。
- 存在待审行（`line_done < line_count` 且其余行均 ≥10）→ 先推进该节 uses 立绘（见下），再汇报「该节逐句音频/环境音待审，请到 dashboard 审批中心逐句审（行级 10→11）」，退出。
- `line_done = line_count > 0`（全部行已批）→ 推进该节 uses 立绘（见下）；本节 uses 立绘全 `11` → 汇报「该节小说/定稿/配音/环境音/立绘均已就绪」，退出。
- **推进本节立绘**（`sc_status=11` 定稿已批后通用动作，**独立于音频门控**——立绘不依赖配音，不应被逐句音频审阻塞）：推进范围 = **本节 say 行 `LineAudio-[:uses]->` 可达的 StandingIllustration**（第 2 步查询的 `used_pending` 已带回 id/变体/status 清单；选绘 apply 建边保证缺口新变体自带 uses 边、天然在范围内），对每个 `stand.status≠11` 先查上游 IllusDesign（一次查询全部）：
  - **上游 `IllusDesign=11`** 的收集为逗号分隔 id 列表，**一次** `Skill char-stand-designer <id1,id2,...>` 委派（传 ≥2 个 id 时 skill 走批量模式并发出图——OfoxAI 单张 30s~10min，串行会堵死编排链；传 1 个即单变体）→ 各自 10 待审；
  - **`IllusDesign≠11`（或不存在）** → 报警「立绘上游 IllusDesign 未就绪，请先单独跑 `char-design`」，**剔除出列表**（不跨链调 char-design），不阻塞其余就绪变体。
  - **appears_as 枚举仅作提示，不推进**：`Section-includes->Event-refines->SubEvent-appears_as->IllusDesign-expands_to->stand` 枚举出的立绘若未被本节任何 say 行 uses 引用（Scene 是多节共享节点，这类立绘的消费方是其他节的台词行），**仅在汇报中列缺口，严禁出图**——单节聚焦不做后续节的事情（那是后续节自身聚焦的活）。
- **不调 `chapter-publisher`**（发布由用户直接触发，不在 plot-design 职责内）。

**严禁**：枚举其他节、做后续节的事情（含推进仅被后续节台词引用的立绘）、建章分节（章级结构由用户直触 `chapter-structurer` 或 dashboard 人工编排直写）、调 `chapter-publisher`。立绘只推**本节 say 行 uses 边可达**的（appears_as 枚举中未被本节引用的仅提示不推进），不跨链调 `char-design` / 角色美术链 skill。铁律（只看 status 不看产物、`-1` 必须重生成覆盖、不读旧小说/旧剧本/旧图）同样适用。汇报只交代目标节（节标题 / 产物链 `sc status`（`10` = 定稿待人工审，停等）+ 行聚合 `say_count/say_done/amb_count/amb_done` / 本节 uses 立绘各 `stand.status` + appears_as 提示缺口 + 本轮是否处理 + 原因），不报其他节。

#### 节点 → Skill 映射

| 图节点 | 委派对象 | 工具 | Status 流程（含审批） | 审批 |
|--------|---------|------|----------------------|------|
| Section（编排容器 + **定稿态载体**） | structurer/dashboard 建编排字段 + `status=0`；`script_path` 由 `chapter-dialoguer` 写 | Skill | `0` 创建待定稿 → `10` 定稿待审（dialoguer 产出直写，填充模式写回同置）→ `11` 已批（dashboard 批准/编辑保存即 11）；`-1` 作废（novelist stale/级联/人工驳回）↔ dialoguer 重写回 `10` | ✅ 定稿审（10→11） |
| 小说.md（节级小说·**纯文件产物，不入图**） | `chapter-novelist` | Skill | 无 status——文件存在 + 指纹新鲜（dialoguer 自检兜底；「调度只看 status」铁律的唯一显式例外） | 无 |
| LineAudio（逐句台词行 ×N） | `section-voice-publisher`（拆分进图 + 配音） | Skill | say 行：-1/0→10→11（10 直写）；非音频行拆分即 11 | — |
| LineAudio（音频环境行 op=transition/bed_start） | `ambient-sfx-designer`（sfx→Freesound 实录 / bed→AudioFly 声景） | Skill | -1/0→10→11（10 直写）；拆分即 0 待产 | ✅ 逐句审（sfx 试听） |
| LineAudio 行级逐句音频审 | dashboard 审批中心（按节聚合卡） | — | 行 10→11（gate=该节全部行 11，派生无节级按钮） | ✅ 逐句审 |
| StandingIllustration（章节所需立绘） | `char-stand-designer` | Skill | -1/0→1→2→10→11 | ✅ |

> `chapter-structurer`（章级建 Chapter + 分节 + Section 编排容器）与 `chapter-publisher`（章级发布 图→`99_game/`）**均不在此表**——都由用户直接触发，不是 plot-design 的调度对象。

**调度只看 status，不看产物文件**：决定是否调度时，唯一判据是节点 `status` 是否到达该链最大门控。**禁止**因 `script_path`/`image_path` 已有值或磁盘文件已存在而判定「已完成」并跳过。`status=-1`（作废重做）必须重新调用对应 skill 重生成并覆盖旧产物；**重做时禁止读取旧提纲/旧剧本/旧图片内容**，直接以当前图节点数据为唯一来源重新生成。（sec.status=-1 重做后行节点由下次拆分对齐处置——未变句恢复，被改句重配，plot-design 无需关心行级细节。）**唯一显式例外 = 小说.md**（纯文件产物无图状态）：其「已产」按路径约定探测文件存在、「新鲜」由 dialoguer 指纹自检兜底（见概述「小说段文件契约」）——但**存在 ≠ 完成**，编排层仍不得以「文件在」为由跳过对它的调度判定。

**复查策略（避免冗余查询）**：仅在 skill/agent 返回（即发生了一次写入）后，对**该被推进节点**做一次复查确认 status 到位；**禁止**在未发生写操作时重复执行第 2 步的 MATCH 查询，也**禁止**每推一个节点就重查整张子图。状态表在内存中维护，复查结果就地更新。

**汇报必须逐节点交代**（不得只说「已完成 X」）：列出该节产物链（`sc status` + **小说状态**（未产 / 已产 / 存量直连）+ 行聚合 `say_count/say_done`（配音）与 `amb_count/amb_done`（环境音），标注所处段：小说/定稿/配音/环境音）+ Scene + 立绘 `stand.status`，及本轮是否处理；未推进的说明原因（待审批 / 依赖未满足 / 已完成 / 需用户决策）。**尤其不得把「status=-1 待重做」误报成「节点未创建」**。

**Status 合法值**（skill/agent 只能写入这些值，禁止其他值如 `3`）：
- `-1` 作废重做（看到 `-1` 必须重新生成并覆盖旧产物，禁止因文件已存在而跳过）
- **Chapter**：无 status。
- **Section（节编排容器 + 定稿态载体）**：`0` 创建待定稿（structurer/dashboard 建节直写）→ `10` 定稿待审（dialoguer 产出直写；填充模式写回同置）→ `11` 已批（dashboard 批准动作 / 定稿编辑器**保存即 11**——人工编辑免审）。`-1` 作废（novelist stale 重写 / 属性级联 / **人工驳回定稿**）→ dialoguer 重新定稿回 `10`。合法值 `0/10/11/-1`；**`=11` 是拆分/配音/环境音/立绘的唯一放行条件**。`script_path` 同挂 Section；小说.md 为纯文件（无图状态，新鲜度靠指纹）。
- **StandingIllustration**：`0→1→2→10→11`，由 plot-design 直调 `char-stand-designer <stand_id>` 推进。
- **LineAudio（逐句台词行）**：say 行 `0` 待配音/被驳回 → `10` 配完待审 → `11` 已通过（行级审批，completion=11）。`10` 由 section-voice-publisher 的 bind-graph 直写；行级驳回归 `0`（重配，不改台词）。非 say 行（narrate/scene/label/ending）拆分即 `11`。「节完成」= 全部行 11（派生）。
- **IllusDesign**（立绘上游，plot-design **只读不写**）：由 `char-design` 推进到 `11`（人工触发）。plot-design 推进某立绘前须先确认其上游 IllusDesign=11，否则报警跳过。

**依赖顺序**（节级链）：`chapter-novelist`（提纲内化：结构推理思维链 + 丰满度自检 + 产 小说.md，零图写入）→ `chapter-dialoguer`（从小说提炼台词.ink，`SET sec.script_path + sec.status=10` 定稿待审；前两步**同轮连推零停等**）→ **人工定稿审（dashboard 批准 10→11；plot-design 停等）** → `section-voice-publisher`（拆分进图 → 逐句 LineAudio → 选绘建 uses 边/变体缺口 → 配音 → 待审行 10）→ 逐句音频审（行 10→11）→ 推进本节 uses 立绘（`char-stand-designer`；上游 IllusDesign≠11 则报警跳过，不跨链）→ 该节就绪，汇报退出（章级发布 `chapter-publisher` 由用户直接触发：从图投影全章行 →`99_game/` 单一章 JSON，行节点 voice_key 投影为 say.voice、uses 边投影为 say.portrait 整键）

**门控**：未组章的自由节不拆分配音（母带目录依赖所属章）；**小说段完成后零停等——同轮连推 dialoguer 直至 台词.ink 置 10**（小说无人工审环节，编排不得在小说→定稿之间插入停等或询问）；小说模式节（有小说.md）dialoguer 必经指纹自检；sec.status ≠ `11`（`0` 未定稿 / `10` 定稿待人工审 / `-1` 作废态）不拆分不配音、不推该节立绘（`-1` 先重走 novelist→dialoguer，`10` 停等 dashboard 批准）；**发布不在 plot-design 职责内**——推进到该节产物就绪（sec.status=11 ∧ 行全 11 ∧ 本节 uses 立绘全 11）即汇报退出，`chapter-publisher` 由用户直接触发。

**节点由 skill 创建**：agent 不直接创建任何图节点或边。Section 节点（含 `status=0`）+ `Section-includes->Event` 边由 `chapter-structurer` 或 dashboard 人工编排直写建立（均在 plot-design 之外，用户触发）；`Section.script_path` + 定稿态（`10` 产出直写、`-1` 恢复到 `10`）由 `chapter-dialoguer` SET 写入（不建节点）；`LineAudio` 逐句行节点 + `Section-[:produces{order}]->行` 边由 `section-voice-publisher` 第一步拆分（script_splitter.py）幂等建，`uses` 边 + 立绘缺口节点（`StandingIllustration status=0` + `expands_to`，vibe 含变体调性）由其选绘 apply 步骤（portrait_binder.py）兜底建；缺口立绘的推进由 plot-design 直调 `char-stand-designer`；IllusDesign 上游由 `char-design` 推进（人工触发，plot-design 不跨链）。`chapter-novelist` 零图写入（小说.md 为纯文件；唯一图操作 = stale 重写时显式作废定稿链）。

### 4. 审批检查

Chapter 无审批。**Section 有定稿审一道（`10→11`，dashboard 审批中心/看板；驳回 `10→-1` 由 dialoguer 重做）**；LineAudio 有**行级逐句音频审**（行 status 10→11，dashboard 按节聚合卡；「节完成」= 全部行 11 派生判断）；StandingIllustration 一道（`10→11`）。（IllusDesign 的审批由 char-design 链管，不在 plot-design 职责内。）

产物链判定规则（对目标节按序判定）：
- 节目录无 小说.md 且 `script_path` 为空 → 待小说，调 chapter-novelist（产小说.md，零图写入）
- 无 小说.md 且 `script_path` 已有历史值 → 存量直连（旧流程节，跳过小说段，dialoguer 读历史文件）
- 有小说.md 或存量直连，且（`script_path` 为空 ∨ `sc_status = -1`）→ 待定稿，调 dialoguer（小说模式自检 stale 报回时调 novelist 重写后重推；产出置 10）
- `sc_status = 10` → 定稿待人工审（dashboard 批准 10→11 / 驳回 10→-1），plot-design 停等该节
- `sc_status = 11` 且（`say_count=0` ∨ `say_done < say_count`）→ 待拆分/配音，调 section-voice-publisher
- `sc_status = 11` 且 `amb_count>0 ∧ amb_done < amb_count` → 环境音待产/待审，调 ambient-sfx-designer
- 存在行 status=10 → 逐句音频待审（含环境音行），等 dashboard（行级审 10→11）
- `line_count>0 ∧ line_done=line_count` → 全部行已批，推进本节 uses 立绘；uses 立绘全 11 → 该节产物链就绪

立绘判定：`stand.status = 10` 待审；` = 11` 已批；`< 11` 未就绪需推进——**推进前须确认上游 IllusDesign=11，否则报警跳过**（不跨链调 char-design）。

**该节就绪 = Section.status=11 ∧ 全部行 11 ∧ 本节 uses 立绘全 11**（各节小说/定稿/配音与所需立绘均就绪）。

**若该节就绪** → 汇报「该节产物链与所需立绘均就绪。章级发布 `chapter-publisher` 由用户直接触发」并**退出**（plot-design 任何情况下不调 chapter-publisher）。

---

## Skills

`chapter-novelist`（skill，节级小说段，**提纲内化**：结构推理思维链 + 丰满度自检（不足报缺口）+ 按 includes 物化成员圈定素材产 小说.md 纯文件产物（场景段标题承载拓扑契约 + 头部取材指纹），零图写入；stale 重写并作废定稿链；对账新实体走建议 JSON。原 chapter-outliner 已废弃并入）· `chapter-dialoguer`（skill，从小说提炼台词：节级产 台词.ink，写 Section.script_path + status=10 定稿待审；场景段照小说 `###` 标题、分支照图 Choice；入场指纹自检，stale 回退 novelist）· `section-voice-publisher`（skill，定稿已批（sec.status=11）后拆分进图 + 选绘建边 + 逐句配音——script_splitter 建逐句 LineAudio + portrait_binder 建 uses 边/变体缺口 + bind-graph 写行 10）· `char-stand-designer`（skill，按需出立绘——单变体或逗号分隔列表批量并发，出图层为 scripts/stand_batch.py）

> `chapter-structurer`（章级建结构，用户直触）与 `chapter-publisher`（章级发布 图→`99_game/`，用户直触）**都不是 plot-design 的调度对象**。
