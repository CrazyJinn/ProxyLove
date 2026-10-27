# 代恋 - 三大编排 Agent 流程图

> **本文定位**：可视化 [.claude/agents/](.claude/agents/) 下三个编排层 Agent（`char-design` / `scene-design` / `plot-design`）的执行流程，统一用**时序图**表达。
>
> - **审批流程独立成节**（[§2](#2-审批流程)），不在各 Agent 时序图里展开——时序图只画"生产调度"主线，遇到待审就用 `⏸ 待审 → 批准` 一行带过并引用 §2。

---

## 目录

1. [三个 Agent 的共同铁律](#三个-agent-的共同铁律)
2. [审批流程](#2-审批流程)
3. [char-design —— 角色美术 + 声音生产链](#char-design--角色美术--声音生产链)
4. [scene-design —— 场景美术生产链](#scene-design--场景美术生产链)
5. [plot-design —— 剧情创作生产链](#plot-design--剧情创作生产链)
6. [全部 Skill 功能概述](#全部-skill-功能概述)

---

## 三个 Agent 的共同铁律

> `char-design` / `scene-design` / `plot-design` 是三条生产链各自的**纯编排层**，骨架完全一致，差异只在"调度哪几个 skill / agent"。

| 铁律 | 含义 |
|------|------|
| **纯分发，不亲自动手** | 入口决策只做：解析输入 → 只读查 status → 据 status 决策 → 用 `Skill` 工具加载生产 skill → 复查 → 汇报；**严禁**在入口决策阶段亲自写 Cypher 写入、亲自调生成脚本、绕过生产 skill 直调纯产出子 skill（`*-prompt-assembler` / `infra-image-generator`）。**Skill 工具是扁平的**：加载某生产 skill 后，agent 即在该 skill 流程内继续执行其三段式（含按其指示调用其声明的子 skill），这是预期行为，不是越界；真正越界 = ①未先加载生产 skill 就凭空直调子 skill，或 ②产出文件后不走该 skill「保存结果」步写 status。 |
| **只读查全量，禁止过滤 -1** | 开局一次查询拿到本地状态表。`-1`（作废重做）与 `0`（待生成）都是待办，**禁止**在 WHERE 加 `status >= 0` 把 `-1` 滤掉。 |
| **调度只看 status，不看产物文件** | 唯一判据是节点 `status` 是否到达该链最大门控。**禁止**因 `prompt_path`/`image_path`/`script_path` 已有值或磁盘文件已存在而跳过；`-1` 必须重生成并**覆盖**旧产物，重做时禁止读旧文件。 |
| **全量循环推进，禁止只推一个就停** | 枚举所有 `status < 10` 的待办逐个委派，直到全部到达终态、撞上审批阻塞（`10` 待 dashboard 批）、或撞上需用户决策的分歧点，才返回（plot-design 单节聚焦模式只推目标节，不受此约束）。 |
| **审批阻塞** | 生产节点产物完成即入待审 `10`（Chapter / VoiceDesign / Section（定稿态）/ LineAudio 由生产 skill 直写，无 submit 步）；批准 `11` 才允许下游推进；驳回归 `0`。审批由人工治理后台（独立项目 dailian-dashboard，gitee `crazyjinn/dailian-dashboard`）触发，**详见 [§2 审批流程](#2-审批流程)**。 |
| **复查就地在内存表更新** | 仅在 skill/agent 返回（发生一次写入）后，对**该被推进节点**复查一次；禁止每推一个就重查整张子图。 |
| **汇报逐节点交代** | 列出全部节点，逐个给 `status` + 本轮是否处理；未推进的说明原因；**禁止**把 `status=-1` 误报成"节点未创建"。 |

### status 语义（三链通用）

```
-1  作废重做（sync 级联重置后；看到 -1 必须重生成覆盖，禁止跳过）
 0  待处理 / 待生成
 1  已完成（数据节点）｜提示词完成（生产节点）
 2  图片完成（生产节点可选中间态）
10  待审（审批专属，等 dashboard）
11  批准（生产节点唯一"真正完成"值）
```

> 审批态与生产态数值隔开：生产用 `0/1/2`，审批专属 `10`/`11`。数据节点完成值 `1`（无审批）；生产节点完成值 `11`。**全图统一，无 label 专属值**（原 Section 专属值 20-33 已随 Section 拆分为产物链而废除）。

---

## 2. 审批流程

> 所有**生产节点**（产出图片/剧本/章节结构的节点）完成后都要人工审批。审批态用 `10`（待审）/ `11`（批准），与生产态 `0/1/2` 隔开。本节是通用流程，各 Agent 时序图遇到待审均引用此处。

```mermaid
sequenceDiagram
    participant Skill as 生产 Skill
    participant Agent as 编排 Agent
    participant DB as Neo4j 图
    participant Dash as Dashboard 人工
    participant Down as 下游 Skill

    Skill->>DB: 产物完成，MERGE 写 status=10（待审）
    Skill-->>Agent: 返回 status=10
    Note over Agent,Down: ⏸ 审批阻塞：下游不可推进
    Dash->>Dash: 在 dashboard 审阅产物（图 / 剧本 / 章节结构）
    alt 批准
        Dash->>DB: status 10 → 11
        DB-->>Agent: status=11
        Note over Down: ✅ 解锁：下游可推进
        Down->>DB: 读上游=11，继续推进
    else 驳回
        Dash->>DB: status 10 → 0
        DB-->>Agent: status=0
        Note over Skill: 🔁 重做：skill 看到 0 / -1 重新生成并覆盖
        Skill->>DB: 重生成 → 再次写 10
    end
```

### 待审节点清单

| 节点 | 进入待审 | 批准解锁的下游 |
|------|---------|-----------------|
| DesignSheet | 图片完成 → 10 | IllusDesign |
| IllusDesign | 图片完成 → 10 | StandingIllustration（plot-design 按 appears_as 推进） |
| StandingIllustration | 图片完成 → 10 | 无下游；作为发布前置（质量确认） |
| SceneLayer | 图片完成 → 10 | 无下游；作为发布前置 |
| VoiceDesign | 候选+试听落盘即写 `10`（无 submit 步；`candidates_path` 非空=候选待选，dashboard 试听「采用」固化 ref 后仍 10 走二审） | `11` → 节级配音（section-voice-publisher 要求 VoiceDesign=11） |
| Chapter | 结构完成 → `10`（structurer 直写，不经 submit） | `11` → 进入节级生产（提纲 / 定稿 / 拆分配音） |
| Section（定稿态） | ~~定稿审已取消~~：创建即 `11`（定稿在位标记）；-1 作废（novelist stale）↔ dialoguer 恢复 11；**编辑保存即 11** | `11` → 节级拆分+配音 + 该节立绘推进 |
| LineAudio（逐句音频审） | 配音完成 → 行节点 `10`（section-voice-publisher 的 bind-graph 直写，不经 submit；**行级** status 只代表音频审批） | 全部行 `11` = 该节配音完成（派生判断，无节级批准按钮；全章各节产物就绪 + 立绘全 11 才发布） |

> AppearanceStyle / LanguageStyle / CostumeStyle / Scene 等数据节点完成值 `1`，**无审批**。
> 产物各态独立——驳回定稿（Section.status→0）只重写定稿（行不动）、驳回单句 LineAudio 行只重配该句；上游变更的作废走 sync 级联（见 §5）。定稿支持**人工微调回路**：直接编辑 台词.ink 改单句 → dashboard「重新提交审批」0/1/11→10（**仅改 Section.status、不动行节点**；不经 dialoguer，手改不丢——重批后重拆按 text_sha1 保留未变句审批结果，只重配被改句）；「保存并同步 LineAudio」**保存即 11**（编辑即审批）。

---

## char-design —— 角色美术 + 声音生产链

> **职责**：对角色进行基础设计，包括外貌特征、语言风格、声音、着装。

### 节点 → Skill 映射

| 图节点 | Skill | Status 流程 | 审批 |
|--------|-------|------------|------|
| AppearanceStyle / LanguageStyle | char-concept-designer | -1/0 → 1 | 无 |
| CostumeStyle | char-costume-designer | -1/0 → 1 | 无 |
| VoiceDesign | char-voice-design | -1/0→1→10→11 | ✅ |
| DesignSheet（首版/已有版本推进） | char-design-sheet `<char_id>` | -1/0→1→2→10→11 | ✅ |
| DesignSheet（增量版本，剪发等永久形象变更） | char-design-sheet `<char_id> <base_ds_id> <口述改动>`（图生图：参考版设计图为底，仅变更口述维度，保持同人物脸部一致） | 新建 →10→11 | ✅ |
| IllusDesign | char-illus-designer `<char_id> [design_sheet]` | -1/0→1→2→10→11 | ✅ |

> **设计图版本链（多版本形象）**：剧情永久外貌变更（如 ch1 sec02 陈默剪发）不改动 AppearanceStyle、不改写旧版设计图——以参考版 DesignSheet 为底**图生图新增版本**（新版本带 `delta_notes` 口述变更 / `active_from` 生效锚点 `chapter_no*1000+section_no` / `slug` 路径目录段），下游为每 (DesignSheet, CostumeStyle) 组合各建一个 IllusDesign，产物路径按 slug 分目录隔离（`06_角色美术/<char>/<slug>/…`，旧版零迁移）。选绘（section-voice-publisher）按 active_from 时间线自动取「≤本节叙事位置的最新版本」。⚠️ 修正 `active_from`/`slug`/`delta_notes` 用 cypher 直改——**勿走 dashboard 编辑器**（改 DesignSheet 属性会 sync 级联作废该版本全部 IllusDesign 与立绘）。

### 时序图

```mermaid
sequenceDiagram
    actor U as 用户
    participant A as char-design 编排Agent
    participant DB as Neo4j 图
    participant S1 as char-concept-designer
    participant S2 as char-costume-designer
    participant SV as char-voice-design
    participant S3 as char-design-sheet
    participant S4 as char-illus-designer

    U->>A: 角色名 / ID（如"陆择"）

    rect rgb(235, 245, 255)
    Note over A,DB: ① 解析 + 只读查全量状态
    A->>DB: MATCH (c:Character{name}) RETURN c.id
    A->>DB: 变长路径查全部美术+声音节点 status<br/>含 -1/0，禁止过滤（只读）
    DB-->>A: 本地状态表（5 类节点）
    end

    rect rgb(240, 255, 240)
    Note over A,S4: ② 按依赖顺序逐节点整体委派 Skill
    A->>S1: Skill char-concept-designer char_id
    Note right of S1: 内部三段式：查→组装→MERGE 写 status
    S1-->>A: Appearance/Language → 1

    A->>S2: Skill char-costume-designer char_id
    S2-->>A: Costume → 1

    A->>SV: Skill char-voice-design char_id（与 costume 无依赖，可并列）
    Note right of SV: 读 LanguageStyle 生成 instruct + 统一长句 ref_text<br/>先落盘 3 候选 ref + 9 情绪试听（Qwen3 Base）再写图
    SV-->>A: VoiceDesign → 10 候选待选
    Note over A: ⏸ dashboard 逐候选试听「采用」（固化 ref，仍 10）<br/>→ 二审批准 11（见 §2 审批流程）

    A->>S3: Skill char-design-sheet char_id 2
    S3-->>A: DesignSheet → 10 待审
    Note over A: ⏸ 待审 → 批准 11（见 §2 审批流程）

    A->>S4: Skill char-illus-designer char_id 2
    S4-->>A: IllusDesign → 10 待审
    Note over A: ⏸ 待审 → 批准 11（见 §2 审批流程）
    end

    A-->>U: 逐节点汇报 status<br/>终点 IllusDesign = 11
```

> **Skill 工具是扁平的**：char-design 用 `Skill` 加载 `char-design-sheet` / `char-illus-designer` 后，即在该 skill 流程内继续执行其三段式，**包括按其指示调用子 skill**（`char-prompt-assembler` 组装提示词 → `infra-image-generator` 出图）——这是预期行为，不是越界；status 由该 skill 的「保存结果」步统一写入（判定标准见 §1 铁律）。

---

## scene-design —— 场景美术 + BGM 生产链

> **职责**：对场景进行基础设计，包括整体氛围设计、背景图、BGM（BgmTrack 人工生成链：skill 产描述 → 用户外部工具生成 wav 归档）。**编排粒度 = spot**：agent 决定要推进的 spot（新建流程或推进已有流程），逐 spot 委派。

### 节点 → Skill 映射

| 图节点 | Skill | Status 流程 | 审批 |
|--------|-------|------------|------|
| Scene | scene-designer `<location_id 或 Location 名>`（Location 粒度入口，兼容 spot 直推） | -1/0 → 1 | 无 |
| SceneLayer | scene-layer-designer `<scene_id>` | -1/0→1→2→10→11 | ✅ |
| BgmTrack | bgm-designer（缺口兜底自建） | -1/0→1（描述产出）→2（用户放 wav 后检测） | 无 |

### 时序图

```mermaid
sequenceDiagram
    actor U as 用户
    participant A as scene-design 编排Agent
    participant DB as Neo4j 图
    participant Scene as scene-designer
    participant Layer as scene-layer-designer
    participant BGM as bgm-designer

    U->>A: spot 名/ID（如「卧室」）<br/>或地点名/ID（枚举其待办 spot）或无参（全图扫描）

    rect rgb(235, 245, 255)
    Note over A,DB: ① 解析入参（Location 三态）+ 只读查待办 Location
    A->>DB: Location.id → Location.name<br/>→ spot 入参经 part_of 解析（兼容）→ 无参全图扫描
    A->>DB: Location 待办判定查（occurs_at 事件量 + 未归组事件 + Scene/SceneLayer/BgmTrack status）<br/>含 -1/0，禁止过滤 + has_bgm 缺口排查（只读）
    DB-->>A: 待办 Location 清单（need_scene / ungrouped / 待重做 Scene / 缺层 / BGM 缺口）
    end

    rect rgb(240, 255, 240)
    Note over A,BGM: ② 逐 Location 按依赖顺序委派 Skill
    loop 每个待办 Location
        A->>Scene: Skill scene-designer location_id
        Note right of Scene: 定位 Location → 聚合 occurs_at 事件<br/>→ Spot 够用性推理 + anchored_at 直挂 Scene(归组即拍机位)<br/>（新增 zone / 歧义点提问敲定）<br/>→ 按事件复用/新建 Scene（新建立机位）<br/>→ 维护 room.yml（--check 校验，不重切）<br/>→ MERGE 写 status + Spot 登记 dsl_path
        Scene-->>A: Scene → 1

        A->>Layer: Skill scene-layer-designer scene_id
        Note right of Layer: DSL 链：slice_scenes.py --emit-prompt<br/>现场投影直写 prompt.md → infra-image-generator 出图<br/>（dsl_path 空的存量走 assembler 模式 A 自由文本）
        Layer-->>A: SceneLayer → 10 待审
        Note over A: ⏸ 待审 → 批准 11（见 §2 审批流程）

        A->>BGM: Skill bgm-designer scene 名（缺口或 -1/0）
        Note right of BGM: 无节点自行兜底建 BgmTrack(0)+has_bgm<br/>产音乐描述文字 → status=1
        BGM-->>A: 描述已产出（等用户外部生成 wav 归档 13_BGM/）
        Note over A,U: 🎵 用户动作阻塞：用户生成 wav 放入后<br/>再触发 bgm-designer 检测置 2（无审批）
    end
    end

    A-->>U: 按 spot 分组逐节点汇报 status
```

---

## plot-design —— 剧情创作生产链

> **唯一职责**：推进某章节从「建结构 → 创作（提纲 + 细节对话）→ 拆分+配音 → 立绘」到全章就绪为止。输入**章节标题、序号或 ID**（如「新皮肤」、`1`、snowflake ID），或**小节 section id**（单节聚焦，由 dashboard「推进此节」入口触发，只推该节的提纲/定稿/配音/该节台词 uses 边引用的立绘，不做后续节的事情）。
>
> 创作链（混合粒度）= **章级结构段 → 各节小说段（`chapter-novelist`：提纲已内化——结构推理在思维链完成，产 小说.md 纯文件产物，零图写入）→ 各节定稿段（台词.ink，dialoguer 从小说提炼，写 Section.status=11 定稿在位）→ 各节拆分+选绘+配音段 → 各节逐句音频审 → 立绘（按需）**，到全章就绪为止；BGM 走 scene-design 编排（`bgm-designer`），plot-design 不查不调 BgmTrack。结构段是**章级**，节级链是**节级**（各节独立推进、独立重做）；**发布不在 plot-design 职责内**——全章就绪后汇报退出，`chapter-publisher` 由用户直接触发：
> 1. 创作侧拆为 `chapter-structurer`（建结构+scene_block_ids 预分配，零文件产出）→ `chapter-novelist`（节级小说·**提纲内化**，纯文件产物）→ `chapter-dialoguer`（台词.ink，从小说提炼，写 Section 定稿态）→ `section-voice-publisher`（拆分进图 + 选绘建边 + 配音），原 `screenwriter`/`chapter-outliner` 已删除/废弃、`SecOutline`/`SecScript` 节点已删、设计简报已废止；BGM 走 `bgm-designer`（scene-design 编排：产描述文字 → 用户手动生成 wav 归档 `13_BGM/`）。
> 2. **节级链（最薄图）**：`Section（编排+定稿态 status/script_path/scene_blocks） -[:produces {order}]-> LineAudio(×N 逐句行)`——**文件是节级产物的唯一载体**（小说.md/台词.ink 不入图），图只存结构真相（行）与最小状态（Section 定稿态）；sync 级联：节属性变更自动作废全部行。「节完成」= Section.status=11 ∧ 该节全部行 LineAudio=11。
> 3. **台词双轨分离**：`台词.ink`（人读/人改的唯一定稿格式，ink 方言机器可解析）↔ 图行（结构化真相：行身份=节点雪花 id，顺序=produces 边 order 大间距 ×1000 中点插入）。确认（Section.status=11）后由 section-voice-publisher 第一步拆分进图（script_splitter.py 幂等对齐：新增建行+中点 order、修改沿用节点置 0、删除 DETACH DELETE、级联未变句恢复）再配音。`台词.jsonl` 已停产（历史文件留创作区，链路不再读取）。
> 4. 立绘侧：**StandingIllustration 由 plot-design 直接调 `char-stand-designer <stand_id>`**（按需；Section.status=11 定稿已确认后通用动作，独立于声音门控——立绘不依赖配音）；上游 `IllusDesign` 未就绪时**报警跳过**（不跨链调 `char-design`，角色美术链由人工单独跑）。
> 5. 素材门控：**novelist 丰满度自检 event 不够时拒绝产出并报告缺口**，plot-design 汇报后退出（剧情链不内置自增长）——用户手动跑 `nrt-gap-filler`（交互式补缺口）补全叙事基础后重调 plot-design。

### 创作侧四阶段（对应 4 个 skill）

| 阶段 | Skill | 状态 | 职责 |
|------|-------|------|------|
| ① 建章节结构 | `chapter-structurer` | ✅ 已实现 | 建 Chapter + 分节建 Section（has_section，编排容器；节成员=includes 物化，节时间由成员事件推导；定稿态由下游写）+ 各节 `Section-includes->Event`；零文件产出 |
| ② 出节级小说 | `chapter-novelist` | ✅ 已实现 | **提纲内化（原 chapter-outliner 已废弃并入）——节的提纲即图数据本身**：按 `Section→includes` 物化成员圈定取材素材（本节 Scene 源 Spot 归组的 Event + involved 角色/Event 一跳 link 的 Info）+ 丰满度自检（不足报缺口）→ **结构推理在思维链完成、不落提纲文件**（场景段切分/分支核验/节拍规划）→ 方法论五步产节级散文 **小说.md**（**纯文件产物，零图写入**；正文 `### <scene_block_id> <场景名> <时段>` 场景段标题承载拓扑契约；头部**取材指纹**＝实际取用素材 id+内容指纹，`scripts/fingerprint.py`）；素材 stale 时重写覆盖并显式作废定稿链（sec.status=-1 + 全部行 -1）；对账新实体走 gap-filler 建议 JSON（source='chapter-novelist'） |
| ③ 节级细节对话 | `chapter-dialoguer` | ✅ 已实现 | **从小说提炼台词**：读章概要（Chapter.summary）+ 小说.md（小说模式：场景段照搬 `###` 标题拓扑契约 + 入场同源指纹自检，stale 回退 novelist；**存量直连模式**：无小说.md 且 script_path 已有历史值的旧流程节读历史文件照旧创作）→ 产出 `25_剧本/.../sec<MM>_/台词.ink`（人读 ink 方言、机器可解析：场景块标记带 scene_block_id、说话行 `角色名:台词`、选择/分支/结局标记——**不写演出标注**，立绘由配音期选绘判定；入参 section_id；唯一图写入 `SET sec.script_path + sec.status=11` 定稿在位——产出即定稿，人工微调走 dashboard 定稿编辑器**编辑保存即 11**） |
| ④ 节级拆分+选绘+配音 | `section-voice-publisher` | ✅ 已实现 | 定稿已确认（Section.status=11）后**拆分进图**（script_splitter.py 对齐 md↔已有行 → 逐句 LineAudio + produces{order}）→ 挑行（say 且 status∈{0,-1}）+ 产选绘候选池（portrait_binder candidates）+ **LLM 判 emotion + 产 tts_text 变体 + 选立绘 stand**（按台词氛围每句选，池中无贴切变体则提新变体）→ **apply 建边**（`LineAudio-[:uses {sync:false}]->stand` 每句一条 + 新变体兜底建 status=0 + expands_to）+ Qwen3 Base Voice Clone 逐句克隆 → 母带 `15_声音/<chapter_stem>/<scene_block_id>/` + bind-graph 写行节点（待审行 status=10，dashboard 按节聚合逐句通过=11/驳回=0，试听读母带）。不拷运行时副本——`99_game/assets/` 只由发布期按 status=11 收录（立绘整键沿 uses 边投影） |

> **门控**：① 建章节结构（组章即结构就绪，无审批）→ 进入 ②③④ 节级创作；无小说.md 且 script_path 为空由 novelist 推进；**无小说.md 且 script_path 有历史值 = 存量直连**（旧流程节）；小说模式节 dialoguer 必经指纹自检；Section.status=11（定稿在位）才拆分配音、才推该节立绘（立绘独立于音频门控）；**全章就绪 = 各节产物就绪（sec.status=11 ∧ 行全 11）∧ 立绘全 `11`**——plot-design 到此汇报退出，发布由用户直接触发 `chapter-publisher`。
> **status**：Chapter **无 status**；节级 **Section.status 定稿态**（**创建即 `11`** 定稿在位；`-1` 作废（novelist stale）↔ dialoguer 恢复 11；**编辑保存即 11**；script_path/scene_blocks 同挂 Section）· 小说.md 无 status（纯文件产物：已产=文件存在、新鲜=取材指纹自检，dialoguer 兜底——「调度只看 status」铁律的唯一显式例外）· LineAudio 逐句行（say 行 `0→10→11` 行级音频审，10 由 bind-graph 直写；非 say 行拆分即 11）**；BgmTrack `0→1→2`（无审批，2=音频已归档）——全图统一通用值（SecOutline/SecScript 节点类型已删）。
> **推进粒度**：dashboard 章行「推进剧情创作」= 章节全量（structurer / 全量循环，到全章就绪即止，不发布）；各节「推进此节」（该节未全就绪时出现）= 单节聚焦（plot-design 按节级链当前段推进该节；sec.status=11 时拆分配音后推该节台词 uses 边引用的立绘——appears_as 枚举中未被本节台词引用的仅提示不推进；不碰其他节、不做后续节的事情、不发布）。

### 节点 → Skill 映射

| 图节点 | Skill | Status 流程 | 审批 |
|--------|-------|------------|------|
| Chapter | `chapter-structurer` | -1/0→1→10→11 | ✅ |
| Section（编排容器） | `chapter-structurer`（创建；定稿态由 dialoguer 写） | status 见下行 | — |
| Section.status（定稿态） | `chapter-dialoguer`（写 script_path+status；台词.ink 为纯文件产物） | 创建即 11；-1 作废↔恢复 11（编辑保存即 11） | —（已取消定稿审） |
| 小说.md（节级小说·**纯文件产物，不入图**） | `chapter-novelist` | 无 status——文件存在 + 指纹新鲜（stale 重写并作废定稿链） | 无 |
| LineAudio（逐句台词行 ×N） | `section-voice-publisher`（拆分进图 + 配音） | say 行：-1/0→10→11；非音频行拆分即 11 | ✅（逐句审） |
| StandingIllustration | `char-stand-designer`（直调 stand_id） | -1/0→1→2→10→11 | ✅ |
| BgmTrack | `bgm-designer`（**scene-design 编排**，plot-design 不查不调） | -1/0→1→2 | 无（手工放入文件夹即合格） |

> `chapter-publisher`（章级发布，不写节点 status）**不在此表**——由用户直接触发，不在 plot-design 职责内。

### 时序图

```mermaid
sequenceDiagram
    actor U as 用户
    participant A as plot-design 编排Agent
    participant DB as Neo4j 图
    participant ST as chapter-structurer
    participant NV as chapter-novelist
    participant DG as chapter-dialoguer
    participant SV as section-voice-publisher
    participant Stand as char-stand-designer

    U->>A: 章节标题/序号/ID（如「新皮肤」）<br/>或 section id（单节聚焦：只推该节）

    rect rgb(235, 245, 255)
    Note over A,DB: ① 解析 + 只读查全量状态
    A->>DB: MATCH (ch:Chapter{title/chapter_no}) RETURN ch.id
    A->>DB: 一次查 Chapter + 各 Section（定稿态）+ 行聚合(LineAudio)<br/>+ includes的Event + appears_as的立绘（只读）
    DB-->>A: 本地状态表
    end

    rect rgb(255, 248, 240)
    Note over A,SV: ② 创作+拆分配音（structurer 建结构（无审批）→ 各节 novelist 小说.md（纯文件产物，零图写入）→ dialoguer 台词.ink（写 Section.status=11 定稿在位）<br/>→ 拆分进图+配音 → 逐句音频审；节级链 Section→LineAudio×N）
    opt 章节结构未就绪（未建 / 用户明示重做）
        A->>ST: Skill chapter-structurer ch_id
        Note right of ST: 建 Chapter + 按情感弧分节建 Section（has_section，创建即 status=11）<br/>+ 各节 Section-includes->Event，预分配 scene-block id
        ST-->>A: 结构完成（Chapter 无 status，组章即结构就绪，无审批）
    end
    loop 章已建后，遍历各 Section（按 section_no 逐节推进产物链）
        opt 节目录无 小说.md 且非存量直连（待小说·提纲内化，纯文件产物）
            A->>NV: Skill chapter-novelist sec_id（首建 / stale 重写）
            alt 素材够（丰满度自检通过）
                Note right of NV: 结构推理（场景段切分/分支核验/节拍）在思维链完成，不落提纲文件<br/>圈定取材素材（includes 物化成员：本节 Event + 一跳 Info）<br/>→ 五步产 小说.md（### 场景段标题 = 拓扑契约），零图写入<br/>头部取材指纹（fingerprint.py）<br/>stale 重写时显式作废定稿链（sec.status=-1 + 行 -1）<br/>对账新实体 → 建议 JSON（人工经 dashboard 审入库）
                NV-->>A: 小说.md 落盘（无小说.md 且 script_path 有历史值的存量节 → 直连跳过本段）
            else 素材不足
                NV-->>A: 报缺口（不写 status）
                A-->>U: 📋 素材不足 + 缺口清单<br/>请手动跑 nrt-gap-filler 补全叙事基础后重调
                Note over A,U: 退出（剧情链不内置自增长，用户手动跑 gap-filler）
            end
        end
        opt 有小说.md 或存量直连，且（无定稿 ∨ sec.status ∈ {-1,0,1}）（待定稿·从小说提炼）
            A->>DG: Skill chapter-dialoguer sec_id
            Note right of DG: 入场同源指纹自检（stale → 回退 novelist）<br/>场景段照小说 ### 标题、分支照图 Choice<br/>从本节小说提炼逐句对话（纯台词，不写演出标注）<br/>产出 台词.ink，SET sec.script_path + sec.status=11
            DG-->>A: 定稿在位（sec.status=11，产出即定稿，无审批；人工微调走定稿编辑器保存即 11）
        end
        opt sec.status=11（定稿已确认）且（无行 ∨ 行未全 11）
            A->>SV: Skill section-voice-publisher sec_id
            Note right of SV: ① script_splitter 拆分进图（幂等对齐 md↔行）<br/>② 挑行 + portrait_binder candidates 产选绘候选池<br/>③ LLM 判 emotion + tts_text + 选立绘 stand（按台词氛围每句选）<br/>④ portrait_binder apply 建 uses 边（新变体兜底建 status=0）<br/>⑤ Qwen3 Base Voice Clone 逐句克隆（voice_clone_runner publish）<br/>⑥ 母带 15_声音/ + bind-graph 写行节点 status=10
            SV-->>A: 待审行 status=10 逐句音频审
            Note over A: ⏸ 逐句音频审（行 10→11，节完成=全部行 11）→ 见 §2 审批流程
        end
    end
    end

    rect rgb(255, 240, 245)
    Note over A,Stand: ③ 立绘（sec.status=11 定稿已确认后通用动作，独立于声音门控；<br/>plot-design 按 appears_as 直调 char-stand-designer）
    loop 每个 appears_as 立绘
        A->>DB: 查该 stand 上游 IllusDesign.status（只读）
        DB-->>A: illus_status
        alt IllusDesign = 11
            A->>Stand: Skill char-stand-designer stand_id 2
            Note right of Stand: 基于 IllusDesign 产出立绘变体
            Stand-->>A: StandingIllustration → 10 待审
            Note over A: ⏸ 待审 → 11（见 §2 审批流程）
        else IllusDesign ≠ 11
            Note over A: 🚨 报警：角色美术链未就绪，跳过该立绘<br/>请人工跑 char-design（plot-design 不跨链）
        end
    end
    end

    opt 全章各节产物就绪（sec.status=11 ∧ 行全 11）且 立绘全 11 且 ch=11（全章就绪）
        Note over A,U: ✅ 全章就绪，可发布——plot-design 到此为止<br/>chapter-publisher 由用户直接触发（不经 plot-design）
    end

    A-->>U: 逐节点汇报<br/>结构/提纲/定稿/配音/立绘 status + 全章就绪状态
```

---

## 全部 Skill 功能概述

> 下表覆盖三条生产链的全部 skill + 叙事层 + 基础设施。**纯产出层**（只产文件、不读写图、不写 status）单独标注。三个**编排 Agent**（`char-design` / `scene-design` / `plot-design`）不在此表——它们是调度者，调度的对象就是表里的 skill。

### 叙事层（创作输入 → 叙事图）

| Skill | 功能 | 主要产出 | 读写图 / 写 status |
|-------|------|---------|-------------------|
| nrt-gap-filler | 叙事图缺口交互式补全（体检发现 + 逐题确认修法；叙事基础层增补唯一入口） | `02_剧情数据/<日期>_round<N>_<主题>_补全_建议.json` | ✅（建议经 dashboard 审阅 + 控制台写回） |

### 角色美术 + 声音层（Character → IllusDesign / VoiceDesign）

| Skill | 阶段 | 功能 | 主要产出 | 读写图 / 写 status |
|-------|------|------|---------|-------------------|
| char-concept-designer | ① 概念 | 外貌 + 语言风格设计 | AppearanceStyle / LanguageStyle 字段 | ✅ |
| char-costume-designer | ② 着装 | 着装设计 | CostumeStyle 字段 | ✅ |
| char-voice-design | ② 声音设计（与着装并列） | 角色基线音色多候选设计（instruct ≤60 字 + 统一长句 ref_text → 3 候选 ref + 每候选 3 情绪试听，dashboard 试听「采用」固化） | `14_声音设计/<char>/candidates/` + `<char>_ref.wav` | ✅ |
| bgm-designer | 场景 BGM（scene-design 编排，亦可用户直触） | 缺口自行兜底建 BgmTrack + 生成音乐描述文字给用户 → 用户外部工具手动产 wav 归档 `13_BGM/<name>.wav` → 检测置 2（Scene-has_bgm->BgmTrack 1:1） | BgmTrack prompt/description + `13_BGM/<name>.md` 文档 + wav | ✅ |
| char-design-sheet | ③ 三视图 | 外貌底图设计（参考图图生图：dashboard 上传的真人参考照片 + AppearanceStyle 补充特征，冲突以属性为准） | DesignSheet prompt + 图 | ✅ |
| char-illus-designer | ④ 立绘设计图 | 着装适配立绘（图生图） | IllusDesign prompt + 图 | ✅ |
| char-stand-designer | ⑤ 立绘变体 | 表情/动作变体（图生图），stand_id 按需模式（变体需求由 section-voice-publisher 配音判断期选绘兜底建缺口，description 含变体氛围） | StandingIllustration prompt + 图 | ✅（plot-design 直调） |
| char-prompt-assembler | 纯产出 | 组装角色提示词（Mode A/B/C） | prompt 文件 | ❌ |

### 场景美术层（Location → SceneLayer）

| Skill | 阶段 | 功能 | 主要产出 | 读写图 / 写 status |
|-------|------|------|---------|-------------------|
| scene-designer | ① 场景（Location 粒度入口） | 定位 Location → 聚合 occurs_at 事件 → Spot 够用性推理 + anchored_at 直挂 Scene（新增 zone / 歧义点提问敲定；归组即拍机位）→ 按事件复用/新建 Scene（新建立机位）→ 维护 room.yml（--check 校验，不重切派生） | Scene 字段 + room.yml + anchored_at 归组 | ✅ |
| scene-layer-designer | ② 图层 | 场景图层（文生图/图生图） | SceneLayer prompt + 图 | ✅ |
| scene-prompt-assembler | 纯产出 | 组装场景提示词（模式 A 自由文本——服务 dsl_path 为空的存量；DSL 链已代码化为 slice_scenes.py --emit-prompt 现场投影直写） | prompt 文件 | ❌ |

### 剧情层（Chapter + Section 产物链 → 运行时）

| Skill | 阶段 | 功能 | 主要产出 | 读写图 / 写 status |
|-------|------|------|---------|-------------------|
| chapter-structurer | ① 章级结构 | 建 Chapter + 按情感弧分节建 Section（纯编排容器）+ 各节 `Section-includes->Event` + 预分配 scene-block id | Chapter + has_section + Section + includes 边 | ✅ |
| chapter-outliner | ~~节级提纲~~ | ⚠️ **已废弃**——提纲内化，结构推理并入 `chapter-novelist` 思维链 | （历史 outline.md） | ❌ 停维护 |
| chapter-novelist | ② 节级小说（提纲内化） | 按 `Section→includes` 物化成员圈定取材素材（本节 Scene 源 Spot 归组的 Event + involved 角色/Event 一跳 link 的 Info）+ 丰满度自检 → **结构推理在思维链完成、不落提纲文件** → 方法论五步产节级散文 **小说.md**（**纯文件产物，零图写入**；正文 `### <scene_block_id> …` 场景段标题承载拓扑契约；头部**取材指纹** `scripts/fingerprint.py`——dialoguer 入场同源自检，stale 时本 skill 重写覆盖并作废定稿链；对账新实体走 gap-filler 建议 JSON，source='chapter-novelist'） | `25_剧本/.../sec<MM>_/小说.md` + `02_剧情数据/..._补全_建议.json` | ✅（零图写入；唯一例外 = stale 作废定稿链） |
| chapter-dialoguer | ③ 节级定稿 | **从小说提炼台词**：读章概要（Chapter.summary）+ 小说.md（小说模式：场景段照搬 `###` 拓扑契约 + 入场同源指纹自检，stale 回退 novelist；存量直连：读 script_path 历史文件）创作逐句对话，产出人读 ink 方言定稿（场景块标记带 scene_block_id、说话行 `角色名:台词`、选择/分支/结局标记——不写演出标注，立绘由配音期选绘判定；入参 section_id；唯一图写入 `SET sec.script_path + sec.status=11` 定稿在位） | `25_剧本/.../sec<MM>_/台词.ink` + Section 定稿态 | — |
| section-voice-publisher | ④ 节级拆分+选绘+配音 | 定稿已确认（Section.status=11）：script_splitter 拆分对齐进图（逐句 LineAudio + produces{order} 中点排序）→ 挑行 + portrait_binder candidates 候选池 → LLM 判 emotion + 产 tts_text 变体 + 选立绘 stand → apply 建 `LineAudio-[:uses]->stand` 边（新变体兜底建 status=0 + expands_to）→ Qwen3 Base Voice Clone 逐句克隆 → bind-graph 写行节点 status=10（母带即产物，运行时副本不在此步） | 图逐句行 + uses 选绘边 + 立绘缺口 + `15_声音/<chapter_stem>/<scene_block_id>/<key>.wav` 母带 | ✅ |
| chapter-publisher | 章级发布（用户直接触发，不经 plot-design） | 全章各节产物就绪（各节 Section.status=11 ∧ 行全 11）时**从图投影**合并 + 立绘/背景/BGM/已批音频（voices+sfx，voice_bundler publish 按 status=11）到运行时 + 补 manifest.voices / chapter_packs | `99_game/` 资源 + manifest | ✅ |

### 基础设施 & 元工具

| 组件 | 功能 | 说明 |
|------|------|------|
| infra-image-generator | 读 prompt 调 OfoxAI API 出图（纯产出） | 文生图 / 图生图；不写图、不写 status |
| cypher_exec.py | 执行 Cypher（统一图读写入口） | 所有 skill 读写 Neo4j 的唯一脚本，支持 `-c`/`-f`/`--stdin`/`--multi`/`--json` |
| `.claude/skills/section-voice-publisher/scripts/` | 声音链脚本组（收编进 skill） | script_splitter.py（台词.ink 拆分对齐进图：parse_ink + difflib 对齐 + 单事务写图）· voice_clone_runner.py（Qwen3 全家：候选/试听/ref + 逐句配音 publish，env/.venv-qwen）· voice_bundler.py（voice key 单一源 make_voice_key + tasks-from-graph/bind-graph + publish 发布期拷运行时）· paths.py（模型路径配置，读 settings.json）；char-voice-design / chapter-publisher 跨 skill 引用 |

> 纯产出层（`char-prompt-assembler` / `scene-prompt-assembler` / `infra-image-generator`）只产文件，节点字段与 status 一律由调用方生产 skill 在「保存结果」步用 MERGE 兜底写入。

---

## 项目文件夹结构

> 目录前缀的数字是**流水线阶段编号**（创作输入 `00_` → 叙事数据 `01_` → 剧情数据 `02_` → 美术 `06_/07_` → 声音 `14_/15_` → 剧本 `25_` → 成品 `99_`），按编号即可判断某产物在链路中的位置。`.claude/` 是 Claude Code 自动化层（skill / agent / 脚本），`env/` 是声音链隔离环境（gitignore）。人工治理后台不在本仓库（独立项目 dailian-dashboard，共享同一图数据库）。

```
代恋/
├── .claude/                          # Claude Code 自动化层
│   ├── agents/                       # 编排 agent：char-design / scene-design / plot-design
│   ├── scripts/                      # cypher_exec.py · snowflake_base62.py · voice/（Qwen3 声音链脚本）
│   └── skills/                       # 全部生产 skill（见 §6 全部 Skill 功能概述）
│
├── 00_init/                          # 创作输入 + Schema（唯一事实来源）
│   ├── Schema/                       # Neo4j Schema（叙事基础 / 角色美术 / 场景美术 / 剧情 / 声音）
│   └── migration/
│
├── 01_叙事数据/                      # 历史：初始建图离线产出
│   └── csv/                          # 实体/关系 CSV + import.cypher
│
├── 02_剧情数据/                      # gap-filler 建议 JSON（<日期>_round<N>_<主题>_补全_建议.json + _reviewed.json 审批留痕）
│
├── 06_角色美术/                      # 角色美术产出（DesignSheet / IllusDesign / StandingIllustration）
│   ├── 沈暮雪/
│   │   ├── 沈暮雪-电竞经理职业装/    # 每套着装 = 一个 IllusDesign，含 prompt.md + 立绘设计图.png；其下 立绘/ 子目录 = StandingIllustration 立绘变体（<变体>.png + <变体>.md 同名配对）
│   │   └── …                         # 同角色其余着装（咖啡店休闲装 / 西餐厅约会装 / 路边摊日常 …）
│   ├── 陆择/
│   └── …                             # 其余角色（林梦 / 苏晓禾 / 陈默 / 顾盈 …）
│
├── 07_场景美术/                      # 场景美术产出（Scene / SceneLayer；每 Spot 一目录收拢）
│   └── 酒店/
│       └── 客房/                     # Spot 目录（Spot 短名；整点建模=Location 名）
│           ├── 客房.yml         # 3D 布局真源 + 派生 酒店-客房.scene2d.yml（同层，唯一派生物）
│           └── 酒店-客房/
│               └── background/       # 图层目录：prompt.md + background.png 同层配对
│
├── 14_声音设计/                      # char-voice-design 产出（<char>/candidates/ 多候选 ref + 情绪试听；采用后固化 <char>_ref.wav）
│
├── 15_声音/                          # TTS 逐句母带（<char>/<char>-<stem>-<scene_block_id>-<行节点id>.wav；requirements/ venv 锁文件，见其 README）
│
├── 25_剧本/                          # 剧本产出（节级：novelist 出小说.md，dialoguer 出台词.ink；structurer 零文件产出）
│   └── chapter<NN>_<章概述>/         # 每章一目录：各 sec<MM>_<节概述>/（小说.md + 台词.ink；历史节另有 outline.md/骨架/dayNN 蓝本与章级设计简报.md 存档）
│
├── env/                              # 声音链环境（gitignore）：.venv-qwen（Qwen3-TTS）
│
└── 99_game/                          # Godot 4.3+ 游戏运行时（chapter-publisher 发布目标）
    ├── assets/                       # portraits / scenes / bgm / voices / sfx（发布期按 status=11 收录的运行时副本）
    ├── data/chapters/                # 发布后的章节剧本 JSON（ScriptInterpreter 消费）
    ├── scenes/                       # Godot 场景
    ├── scripts/                      # autoload / data / scenes / ui / util
    ├── tools/                        # validate_chapter.py（数据校验，无需 Godot）
    └── tests/
```
