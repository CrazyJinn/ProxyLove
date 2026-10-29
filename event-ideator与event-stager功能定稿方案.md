# event-ideator × event-stager 功能定稿方案

> 状态：书面定稿，待拍板后实施。本文档只定「应该实现的功能」，不涉具体实现细节。
> 背景：2026-10-28 对话逐题敲定。旧实现（grill skill + event-refiner agent）为旧分工
> （grill=记录已想好的事件 / refiner=细化+缺口留单），本方案将其升级为
> 「ideator=需求提出 / stager=需求细化+占位物化 / 实现 agent=占位消化」三层模型。
> 形态定稿：**两者一律为 skill**（同为多轮交互+产建议 JSON 形态，无需 agent 壳）。
> 新名：旧 grill → **event-ideator**（提出）；旧 event-refiner → **event-stager**（细化落地、舞台化）。
> 旧文件删除：`.claude/skills/grill/`（整个旧 skill 目录）、`.claude/agents/event-refiner.md`（旧 agent 壳）。
> 依据：SubEvent细化层改造方案.md（已实施）、用户 2026-10-27 方法论定稿。

## 0. 一句话总纲

**event-ideator 提需求 → event-stager 细化并物化为占位节点 → 实现 agent 消化占位。**
信息全部走图（占位节点自描述），不走文本留单；创作判断在哪层发生，创建权就在哪层。

## 1. 三层职责模型

| 层 | 执行者 | 创建占位的域 | 消化者 |
|---|---|---|---|
| 需求提出 | event-ideator（多轮交互） | 叙事基础域：Event、Character/Location 占位 | event-stager（细化）、char-design / scene-design（占位） |
| 需求细化 | event-stager（多轮交互） | 演出域：SubEvent、Scene/Spot/CostumeStyle/IllusDesign 占位 | char-design / scene-design |
| 实现 | char-design / scene-design | 不创建，只消化 status=0 占位 → 产真资产推 status | — |

统一交互通道（两线相同，铁律）：

- 多轮对话，**一次一问、每问附可归因的推荐答案**；
- 用户确认后**存建议 JSON**（`02_剧情数据/<日期>_round<N>_<主题>_<ideator|stager>_建议.json`）；
- **零直接图写入**——人工经 dashboard 建议弹窗审阅写回；
- 创建权只决定「JSON 里能出现什么节点类型」，不改变写入通道。

## 2. event-ideator —— 需求提出层

**定位**：发散层 / 创作发生器。从人物设定出发主动生成候选事件，而非仅记录已想好的事件。

**输入**：char（一或多个人物）+ base event（可选，既定目标事件）。

**名词**：base event = 确定要发生的目标事件；new event = 本轮新创作的 event。

**流程（四步）**：

1. **探索图** —— 人物设定、时间邻域、既有事件与因果（leads_to），为启发提供依据。
2. **启发**（三种模式，可组合，输出候选 new event）：

   | 模式 | 回答的创作问题 | 产出类型 |
   |---|---|---|
   | `char → new → base` | 角色经历了什么才抵达既定事件？ | 动机链事件（因果补桥） |
   | `char → new` | 这个人平时会干什么？ | 人物质感事件（血肉填充） |
   | `base → new → base` | 两个既定事件之间发生了什么（可有关可无关）？ | 间隙填充事件 |

3. **三要素细化** —— 补全 new event 的 char / location / time；所需实体图上不存在时
   （新配角、新地点），在本步提出 **Character / Location 占位**创建。
4. **询问** —— 逐题确认（一次一问附推荐答案），用户拍板。

**产出**：粗粒度 Event（+ involved / occurs_at 挂边 + Character/Location 占位），
全部进建议 JSON。事件密度刻意低是设计目标。

**不做**：拆解、机位、着装、任何演出域决策；不建 Spot/Scene/CostumeStyle/IllusDesign。

## 3. event-stager —— 需求细化层

**定位**：收敛层 / 演出物化器。把粗事件展开成机位级演出素材，并把演出所需实体
全部物化为占位节点。

**输入**：target event list（event-ideator 产出 + 既有事件，id / title / 时间窗）。

**流程（四步）**：

1. **探索** —— char 下的立绘链（DesignSheet→IllusDesign 现状）、location 下的
   scene 链（Location→part_of→Spot→realizes→Scene 现状）。
2. **拆解** —— 按创作需要把 event 拆成 SubEvent（到场/离开/屋内换区等微内容
   系统性落在机位层；时间插值；沿用 refines 模型）。
3. **占位物化** —— 为每个 sub 构建链条
   `IllusDesign ←appears_as← SubEvent →anchored_at→ Scene`；
   发现缺口时**建占位节点（status=0）**，空间/着装的叙事侧决策（哪个房间、哪套衣服）
   在此拍定：

   | 缺口 | 占位节点 | 后续消化 |
   |---|---|---|
   | 空间不存在（新房间/新位置） | Spot（Location 缺口 = 上游未完成，报错退回 ideator，见 §6 Q1） | scene-design：Scene 细化 + room.yml |
   | 机位不存在 | Scene（status=0，挂 realizes 到 Spot） | scene-design |
   | 服装套不存在 | CostumeStyle（status=0） | char-design |
   | 某套衣服的形象版本不存在 | IllusDesign（status=0，挂 outfit_for 到 CostumeStyle） | char-design |

4. **逐 event 询问** —— 每个事件的拆解方案 + 占位清单逐题确认。

**产出**：SubEvent + refines/anchored_at/appears_as 绑边 + 全链占位节点，
全部进建议 JSON。

**不做**：建 Event / Info / Choice（新事件生产走 event-ideator）；不产任何真资产
（图片/room.yml 归实现 agent）。

## 4. 实现 agent —— 占位消化层

char-design / scene-design 职责从「补缺口（文本留单）」升级为「消化占位（图上自描述）」：

- 入口查询圈 `status=0` 的占位节点（含新 label：CostumeStyle/IllusDesign/Scene/Spot/Character/Location 皆可占位）；
- 占位节点在图上的位置（挂在哪个 CostumeStyle / 哪个 Spot 下、被哪个 SubEvent 引用）自带完整需求上下文；
- 产出真资产后推 status，走既有生产链与审批。

## 5. 与现实现的差异清单

| # | 项 | 现状 | 目标 | 动处 |
|---|---|---|---|---|
| D1 | event-ideator 启发能力 | 仅记录用户已想好的事件（零生成） | 三模式主动生成候选事件 | event-ideator SKILL.md 重写流程 |
| D2 | event-ideator 三要素 | involved/occurs_at 只挂既有实体 | 可建 Character/Location 占位 | event-ideator SKILL.md + 建议 JSON schema |
| D3 | stager 缺口处置 | anchored_at 只挂既有 Scene；IllusDesign 只继承；缺口文本留单派发 | Scene/Spot/CostumeStyle/IllusDesign 占位创建（status=0），留单机制废弃 | event-stager.md 重写 §3 |
| D4 | stager 绑定权 | appears_as 仅继承兄弟 sub | 可绑占位 IllusDesign（叙事侧拍定哪套衣服） | event-stager.md |
| D5 | 建议 JSON schema | Event/边/升级类 | 增：Character/Location/Spot/Scene/CostumeStyle/IllusDesign 占位创建 + 占位绑边 | event-ideator/stager 产出 schema + dashboard 建议弹窗 |
| D6 | dashboard 建议弹窗 | 不支持占位节点类型写回 | 支持六类占位节点及其上游边（part_of/realizes/outfit_for/has_appearance 等）创建 | dashboard 建议审阅页 |
| D7 | char-design / scene-design | 补缺口语义 | 消化 status=0 占位语义 | 两 agent 文档入口查询 |
| D8 | EA 体检 | EA5 查 Event 直挂违规 + sub 孤儿 | 增：占位节点存量/消化进度项（status=0 挂账） | event_checkup.py |

## 6. 开放问题（2026-10-28 已全部拍板）

- **Q1 占位的上游边界（已拍）**：ideator 的三要素细化保证叙事基础层在图上（含 Character/
  Location 占位）——**进 stager 的事件，其 Location/Character 必已存在**。stager 再遇
  Location 缺口 = 上游未完成，**报错退回**（可操作错误：缺什么、退给 ideator 补），
  不代建不跨层。stager 的创建域严格限于演出域四类：Spot/Scene/CostumeStyle/IllusDesign。
- **Q2 Character 占位的外貌链（已拍）**：**char-design 创建**——入口圈到无外貌链的占位
  Character 时现场建链（AppearanceStyle→…）再推进；ideator 只建 Character 裸节点。
- **Q3 占位节点字段下限（已拍）**：**等 scene-design 拍**——不预先定死，实施中由消费方
  （char-design/scene-design）按消化体验反馈回填各 label 下限，再固化进 skill 文档。
- **Q4 占位阶段级联（已拍）**：**sub description 不引用 Scene 机位名等占位字段**——
  description 只写演出内容（动作/参与人/情绪/衔接），机位信息一律由 anchored_at 边承载。
  结构上解除「占位改名 → description 漂移」风险；占位阶段无级联，细化产物（10/11 后）
  变更照旧级联。此约束写入 stager 的 description 模板规范（与 §8.2 模板字段一致——
  模板中本来就没有机位名字段，机位在 anchored_at 一列）。

## 7. 实施顺序（拍板后）

1. 建议 JSON schema 定稿（六类占位 + 绑边）→ dashboard 建议弹窗支持（先行，否则 JSON 写不回）。
2. event-ideator SKILL.md 按四步流程重写（D1/D2）。
3. event-stager.md 按四步流程重写（D3/D4），删除文本留单机制。
4. char-design / scene-design 文档改占位消化语义（D7）。
5. EA 体检增补（D8）。
6. 回归测试：event-ideator/stager 产出 schema 断言、dashboard 建议弹窗写回用例。

两仓改动不自行 commit，等用户触发。

## 8. 方法论蒸馏（源自 xindoo/sumeru，网文创作 skill 集 MIT）

> 来源：github.com/xindoo/sumeru（7 skill：worldbuilder 编排 / topic 选题 / outline 大纲细纲 /
> write 细纲驱动写作 / review 审查 / polish 润色 / finalize 完稿）。
> 蒸馏原则：取其「创作方法论与数据流转结构」，去其「全自动流水线」取向——
> 我们是人工拍板通道（建议 JSON → dashboard 写回），sumeru 是直接落盘流水线；
> sumeru 的爽点经济学面向网文读者市场，我们的「价值判断」面向 galgame 演出。

### 8.1 event-ideator 蒸馏自 sumeru-topic（选题策划）

| sumeru 做法 | 蒸馏为 ideator 方法论 |
|---|---|
| 一次生成 **3-5 套差异化选题方案**，不一次一个 | 启发阶段每轮输出**多条候选 new event**（差异化：动机链/质感/间隙三种模式各出候选），配对比表供挑选，而非线性逐个问 |
| **多维度评分对比表**（热度/竞争/受众/难度/变现/风险 → 综合分+推荐） | 候选事件评分维度替换为：与人物设定的契合度 / 与既有事件重复度（查图去重）/ 戏剧价值（情绪曲线贡献）/ 生产成本（需新建多少占位）→ 综合推荐 |
| **金手指/核心卖点/爽点模式**结构化字段 | 每个 new event 候选必带结构化字段：一句话核心 / 情绪价值（给玩家什么感受）/ 与 base event 的因果或反差关系 |
| 选题输出 `options.json` **机器可读**供 outline 自动复用 | 建议 JSON 即接口：stager 直接吃 ideator 的建议 JSON（含评分与推荐），无需人肉转述 |
| 市场分析标注「AI 推理非实时数据」caveat | 启发依据标注来源：图上实查 vs 模型常识推断，分开呈现防幻觉混入图数据 |

### 8.2 event-stager 蒸馏自 sumeru-outline（大纲+细纲）

| sumeru 做法 | 蒸馏为 stager 方法论 |
|---|---|
| **章节细纲 12 要素必填清单**（核心事件/出场人物/剧情推进/爽点悬念/伏笔/前后关联/场景/POV/情绪基调…） | SubEvent description 结构化模板必填：机位动作 / 到场离场方式 / 参与人 / 情绪基调 / **与邻接 sub 的衔接**（承接什么引出什么）/ 着装时点 |
| 细纲标准 =「**包含足够细节，支持独立生成完整章节**」 | SubEvent 自足性标准：novelist/dialoguer **不回读父事件**也能演出该 sub——description 模板按此验收 |
| 细纲双轨输出：人读 `.md` + 机器读 `chapter-outlines.json` | 建议 JSON（机器）之外，每个 event 附**人读拆解卡**（markdown 表格：sub 序 / 机位 / 着装 / 一句话演出），dashboard 审阅体验对齐 |
| 16 个**风格参考库**（references/ 按题材） | stager 内置 **微演出模式库** references/：到场 / 离开 / 屋内换区 / 对峙 / 独白 / 并行小事 / 目击 / 误认……每种模式给拆解范式与示例，拆解决策「查库」而非每次现想 |
| **命名库**（虚构人名地名姓氏库） | 占位节点命名规范库：Scene 机位名 / Spot 段名 / CostumeStyle 套装名的命名模式（与 room-dsl 对齐），保证占位名可直接被实现 agent 消化 |
| 并行细纲生成后**一致性校验**（相邻衔接/人物连续性/时间线/跨卷伏笔） | stager 写后复查清单：同父 subs 时间连续无重叠 / 同机位同角色着装一致（EA3）/ sub 顺序与父事件 time 相容 / 跨 event 相邻 sub 衔接（承上启下字段非空） |
| 爽点排布公式（密度 + 铺垫→转折→爆发→余韵节奏） | 拆解时的**演出价值判据**：不是每个到离场都值得 sub——按「铺垫→触发→释放→余韵」判断该微内容是否有演出价值，无价值的不拆（回答「到场/离开/换区有没有演出价值」的系统化判据） |

### 8.3 编排层蒸馏自 worldbuilder / AGENTS.md（两 skill 共用）

| sumeru 做法 | 蒸馏为共用规则 |
|---|---|
| **Skill 间解耦**：下游禁止调上游，数据一律经持久化文件传递 | ideator / stager 互不调用、互不依赖运行；唯一接口 = 建议 JSON + 图数据。stager 对「事件从哪来」无感知 |
| **阶段检查点 + 进度文件**（断点续传） | 多轮交互的中间态落盘（当前轮次 / 已拍板项 / 待问队列），会话中断可续——建议 JSON 落盘前先写进行中的会话状态文件 |
| **批量上限约束**（每子 Agent 最多 3 章，硬性） | stager 单轮处理 event 批次设上限（建议 ≤3 个 event/轮）：保证逐 event 询问质量、上下文不溢出；超出则分轮 |
| 中间数据/用户可见输出**路径分离** | 会话状态（内部）与建议 JSON（交付物）分离存放；建议 JSON 命名规范沿用 `02_剧情数据/` 既有六件套范式 |
| description 含**触发关键词 + 排除规则** | 两 skill 的 SKILL.md description 显式写触发词与「何时 NOT 用」（ideator：不拆解不拍机位；stager：不创作新事件）——sumeru 的可发现性工程直接继承 |
| 输出确定性 + 错误友好 | 同输入同结构输出；探索图失败/实体缺失时报可操作错误（缺什么、找谁补），不静默降级 |

### 8.4 明确不蒸馏的（留档防复采）

- **全自动流水线 + 阶段自动推进**（worldbuilder「跳过确认」）：与人工拍板通道冲突，不取。
- **自动修复直接改产物**（review 改 chapters/ 自动备份）：我们的等价物是级联作废+建议 JSON，写权在 dashboard，不取直改。
- **爽点密度公式**（每 3-5 章一爽点）：galgame 节奏由剧情驱动非更新压力驱动，只取节奏形态（8.2 末行）不取密度指标。
- **市场/变现维度评估**：不适用，已替换为戏剧价值维度。

### 8.5 chapter-novelist 去 AI 味工序（第三处蒸馏，触发点：小说层叙述+对白均 AI 味重）

> 用户反馈（2026-10-28）：小说创作的 AI 味太浓，不像真人会说的话——**主病灶在 novelist 层**
> （叙述+对白都假），不只是 dialoguer 台词层。方案已对齐、待「实施」指令后落盘。

**诊断**：小说.md 是 dialoguer 的「创作土壤」——土壤带 AI 味，台词提炼得再自然也救不回来。
现行《小说方法论精简版》第四步明确把「去 AI 味重工序」推给 ink 定稿层（dialoguer），但
dialoguer 只治理台词层，叙述层的 AI 味（narrator 腔 / 价值拔高 / 破折号过密 / 翻译腔）
两层都没人管。

**改法**（把重工序从 dialoguer 层**前移到 novelist 层**，蒸馏三源）：

1. **新参考文档** `chapter-novelist/references/小说去AI味工序.md`，三源蒸馏：
   - 项目内《日常对白自然度技巧》（dialoguer references，12 反模式+两遍回读）——
     其中叙述层四病灶（4.5 价值拔高 / 4.6 narrator 腔 / 4.7 破折号过密 / 4.12 翻译腔）
     + 对白八反模式在小说层同样适用，全文蒸馏改写为小说层工序；
   - **sumeru-polish** 文笔优化五条（精准用词 / 句式长短结合 / 感官描写 / 比喻具象 /
     删「非常/十分/很」类程度副词）+ 对话优化五条（人设贴合 / 潜台词 / 节奏控制——
     长对话拆轮穿插动作 / 口语化但不硬凹网感 / 对话标签用具体动作代替「说道」）；
   - **sumeru-write** 叙事纪律：无对话段（物件静帧+动作代替台词）、跨场景物件镜像
     （同一物件前后对照，余味比当场回收长）——这两条已在《小说方法论精简版》第二步
     节奏工具里，纳入新工序统一引用。
2. **SKILL.md 最小改**：2b.5 自检步「惯性签名轻检」升级为「去 AI 味工序」（按新参考文档
   12 反模式 + Pass 1 保真 / Pass 2 残留味两遍回读），删除原「去 AI 味重工序不做——
   留给 ink 定稿层」表述；原轻检三样（比喻≥3 砍、签名短语≤1、结尾落点错开）并入新工序
   回读清单，不两处维护。
3. **《小说方法论精简版》头部标注**：第四步轻检已并入新工序文档（防两处维护）。
4. **不蒸馏**：sumeru 3 级润色等级（我们单档两遍回读）、爽点强化/前置铺垫（无爽点经济学）、
   6 风格适配（我们按角色 LanguageStyle 管语感，统一语域原则保留）。

**不动**：dialoguer 的《日常对白自然度技巧》原样保留（台词层继续用，句子层工序两层数据
不同但清单同源）；拓扑契约 / 指纹 / 对账机制零改动。

## 附：2026-10-28 拍板记录

- 分层：event-ideator 发散（创作发生器）/ stager 收敛（演出物化器）——用户提出，确认。
- §6 四问全拍：Q1 stager 遇 Location 缺报错退回（上游契约由 ideator 保证）；Q2 外貌链
  char-design 创建；Q3 占位字段下限等 scene-design 拍；Q4 sub description 不引用占位
  字段（机位信息只走 anchored_at 边）——用户逐条拍板。
- novelist 去 AI 味：主病灶在小说层（叙述+对白），重工序从 dialoguer 前移到 novelist，
  三源蒸馏（对白自然度技巧 + sumeru-polish + sumeru-write）——用户确认（§8.5）。
- stager 占位创建权：Spot/CostumeStyle/IllusDesign 由「只绑既有+留单」改为占位创建——用户拍板。
- Scene 占位同样归 stager 创建——用户拍板。
- event-ideator 亦可建 Character/Location 占位——用户补充确认。
- 写入通道不变：两线均多轮交互→确认→存 JSON→人工 dashboard 写回——用户拍板。
