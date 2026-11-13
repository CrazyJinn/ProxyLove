# Skill 软单源复查 — 待拍板

> 按今日「Schema 软单源」主体思想，用 skill-creator 方法论整理全部 20 个 skill。本文档沉淀判定标准、已立先例、全量扫描发现与逐家待办，供一次审全貌、统一裁定。拍板执行完毕后本文档按惯例删除。

## 执行终态（2026-11-13，20/20 完成）

**规模**：35 文件，+179/−291（净减 112 行）；其中 Schema 侧个案小清洗 6 处（AppearanceStyle 护栏句 / CostumeStyle notes 迁移注记 / 边.md「已实施」/ DesignSheet 重复句 / IllusDesign display_scale 公式下沉 / VoiceDesign 日期注记——均按 §7 先例逐项经方案批准）。

**逐家清单**（全部按 §2 先例 + §7 裁定执行）：

| 链 | 家 | 要点 |
|---|---|---|
| 角色美术 6/6 | concept / costume / design-sheet / illus / stand / prompt-assembler | description 瘦身 ×6；template 字段副本/阵营表/流程状态节出清；幽灵护栏（color_direction ×3、slug ×3、「0→1→2」×4）；**cs.notes 回写砍除+透传语义**（§7-2）；负面体态词跨文件副本出清；display_scale 公式下沉 Schema；「版本三字段」计数漂移；查询冗余行 |
| 场景美术 3/3 | scene-designer / layer / prompt-assembler | description 瘦身；废弃广播（default/自动兜底/weather 四字段 ×3）；**参考文档坏链 ×3**；room-yml 样例坏链+幽灵保留字符规则；模式E 死文档整节删+「模式 E」称呼改「DSL 链」；layer 整节点直返补漏+「1 已有提示词」幽灵 |
| 声音 3/3 | bgm / voice-design / ambient-sfx | description 瘦身；**name=manifest 键知识错误修正**（id 锚定后键=hexid）；固化路径三处矛盾修正；历史值段指回 Schema；存量迁移/日期广播清 |
| 剧情 5/5 | structurer / novelist / dialoguer / voice-publisher / publisher | description 瘦身 ×5（novelist 8→4、voice-publisher 8→4）；time_day/summary/绿幕/name 派生广播；整节点直返 ×6；ink方言规范版本变更史整节删+废止行型/护栏删（§7-4）；「头部注记」坏链 ×2 |
| 叙事基础 2/2 | event-ideator / event-stager | description 瘦身（ideator 19→5、stager 11→4）；方法论溯源坏链删；故事线查询直返 ×4；日期/过程注记/清理记录 ×10 |
| infra 1/1 | infra-image-generator | 日期+变更叙述 ×1；api-reference 漏网日期 ×2（验证扫出） |

**验证结论**：废弃广播全仓清零；幽灵「0→1→2」仅剩 bgm-designer（BgmTrack 枚举 0→1→2 合法特例）；日期注记清零（仅剩事故样本文件名 `2024-06-12_round1_…json`——真实文件名非注记）；char 系 description 全部生效（skill 列表已刷新）。

**遗留（未在本轮范围）**：①Schema 节点文件头部流程语义段——23 文件形态议题（§7-3 另开专项）；②agents/ 三编排层 md 与 CLAUDE.md 未动（skill 改动未牵出必改引用——produce.py 映射按 skill 名，不受影响）。

## 1. 主体思想与判定清单

四层思想：**①软单源**（字段知识唯一来源=Schema，skill 只留指回锚）**②粒度对齐消费方**（Schema 拆到节点级，锚点精确到文件）**③规则抽象化**（纪律不硬编码字段名，字段清单唯一来源=Schema 表）**④废弃即清净**（不留废弃表/变更注记/冗余标记）。

6 项检查清单（逐家过）：

| # | 检查项 | 判据 |
|---|--------|------|
| 1 | 字段知识零副本 | 正文 **与 description** 均无字段表/字段清单/写法纪律复述，只有 Read Schema 锚 |
| 2 | 流程/定义分界 | skill 只讲怎么做（三段式/门控/落盘/子 skill 调用）；Schema 独占是什么 |
| 3 | 规则抽象化 | 写侧纪律不含字段名硬编码 |
| 4 | 废弃即清净 | 已废边/机制/文件/字段零广播残留；幽灵字段、幽灵流程以 Schema 现状判 |
| 5 | 引用健康 | 每个 Read 锚/边名/枚举值指向真实存在且一致的 Schema |
| 6 | skill-creator 规范 | description 触发导向；正文 <500 行；重内容下沉 references |

## 2. 已确立先例（前 3 家裁定沉淀，后续直接适用）

1. **description 瘦身尺度**：干什么一句 + 何时触发 + 职责边界（谁管谁不管）；机制细节（脚本名/算法/路径/MERGE 兜底细节）全出清。`status=0 需推进` 统一改 `status∈{0,-1}`（-1 同为合法起点）。
2. **data_json 槽位罗列 = 载荷契约**，非查询别名，保留（今日 37f1985 先例）；已注明「图里没有的可选字段跳过」即可。
3. **SET 语句字段直列**（带条件写入语义，如「增量模式写/常规模式保持原值」）保留——占位符化会丢失条件语义；配「按 Schema 核对：缺一不可、表外不加」护栏。
4. **同一文件内就地重申**（cypher 注释 vs 正文头）= 排版非副本，不动；**跨文件**才算副本。
5. **废弃护栏权威归 Schema 后，正文广播全删**（wears/slug 先例：正文两处「已废」注记删除，护栏在边.md/字段说明列）。
6. **幽灵判定逐家查 Schema，不一刀切**：字段不存在（`color_direction`）或枚举无此值（`0→1→2`）即幽灵；但 BgmTrack 枚举确为 `0→1→2`（bgm-designer 写法合法）——每处先对照 Schema 再判。
7. **Schema 侧过程注记净化**：删日期/迁移细节/「已实施」状态词，留净护栏句（AppearanceStyle.md `appearance` 先例）。
8. **世界观硬编码不属 template**：阵营词汇表（骑士团/教会等异世界观残留）整节删；生成时从角色所属群体现推。

## 3. 已完成明细（git diff 可对照）

**char-concept-designer**：description 瘦身；template-角色美术设定.md 重写（出清逐字段映射段与写法纪律复述、删 appearance 废弃注记；保留自描述规则/核心关键词/形状语言选型/自留段定位）；template-角色语言风格.md 重写（删阵营表、speech_style 复述、「不写入图」段、流程状态节；保留身份规则方法论）；Schema AppearanceStyle.md 护栏句净化。

**char-costume-designer**：description 瘦身并补「消化占位」触发语境；段 3 标题删「wears 已废」；参考文档注释「各字段规则」→「体态与道具约定」（修漂移）；Schema CostumeStyle.md 删 notes 迁移注记、边.md 删「（已实施）」。

**char-design-sheet**：description 瘦身；「不取 color_direction（2026-10-06 用户定规）」→「不取配色方向」（幽灵字段+日期双清）；删 slug 广播 ×2；「版本三字段」→「delta_notes/active_from」（计数漂移）；SET 块注释归位；Schema DesignSheet.md 删重复「首版留空」。

## 4. char-illus-designer（已执行，2026-11-13）

description 瘦身；删「（重走 0→1→2）」幽灵；「slug 分目录」→「ds_id 版本目录」；data_json notes 槽位改**透传语义**（§7-2 裁定）；**删段 3 回写块**（`SET cs.notes` 整块）；display_scale 公式下沉 Schema、正文改引用；「Mode B」→「模式B（IllusDesign）」。同轮补漏：char-design-sheet 删「（重走 0→1→2）」；Schema IllusDesign.md display_scale 说明列补公式。

「0→1→2」幽灵另余 2 家待清：char-stand-designer / scene-layer-designer（bgm-designer 合法，BgmTrack 枚举特例）。

## 5. 全量扫描发现（grep 实据）

### 5.1 废弃注记 ~30 处 / 14 文件

- **广播型（建议删）**：ambient-sfx-designer:21「（2026-09-03 存量迁移为 sfx/bed）」、:30「amb-/bed- 前缀已废」；chapter-publisher:79「旧 name 派生已废」；section-voice-publisher:8「depicts/ref_style（边已废止）」、:62「旧 chapter_stem_from_meta 已废」；scene-designer:4「default 已废止仅存量」、:130/:167 weather/composition/lighting/color_direction 广播 ×2；scene-layer-designer:81 同款；event-stager 多语句cypher文档:76「v1，已废弃」。
- **护栏型（建议留但净化）**：ink方言规范.md:96 废止行型表（解析器报错引导——有行为后果）、:183/:188/:194（行型/结局/pos 废止护栏）；VoiceDesign.md clone_prompt_path 废弃说明（char-voice-design:125 正当引用）；占位命名规范.md:16 default、:45 adaptation_notes。

### 5.2 日期注记 20+ 处（见 §7 裁定点 1）

「用户 2026-08-29 定」（ambient-sfx:73）、「2026-08-28 demo 验证结论」（:23）、「2026-09-13 实测 OfoxAI 安全审核收紧」「2026-10-04 用户定规」（char-prompt-assembler 正文+template ×3）、「2026-10-06 用户定规」（template-设计图提示词:6）、「2026-09-26 用户定规」（assembler:38+template:61 双写）、「2026-10-19 起」双槽模型（ink方言规范:138-140）、「2026-10-31 起」id 锚定（chapter-publisher:20）、「2026-08-30 起」分包流水线（:182）、「2026-11-09 定稿」sub 契约（chapter-novelist:82）、「2026-10-28 前移」（小说方法论:4）。

### 5.3 description 重灾区（行数）

event-ideator **19**、event-stager **11**、section-voice-publisher **8**、ambient-sfx-designer **7**、scene-prompt-assembler 5、char-illus-designer 4（已在方案）、chapter-publisher 4。

### 5.4 skill 内跨文件副本

- char-prompt-assembler SKILL.md:38 ↔ template-设计图提示词.md:61：「禁负面体态词（含否定式）」整段两处复述（skill 正文 vs 自己的 reference）。
- template-设计图提示词.md:6「不引用 `Character.color_direction`（2026-10-06 用户定规）」——color_direction 幽灵第 3 处。

### 5.5 其他

- 小说方法论精简版.md:4 删除线编辑残留（`~~去 AI 味重工序留在 ink 定稿层~~`）。
- chapter-novelist description 与正文 :55 超长段落（单段 400+ 字）。
- template-图层JSON.md:28「废弃车辆、岩石堆」为 grep 误报（场景内容名词，非废弃注记）。

## 6. 剩余 16 家审查要点（已全部执行，见头部「执行终态」）

## 7. 跨切面裁定点（已全部裁定，2026-11-13）

1. **日期注记批量净化** → **已裁：直接清理掉**（删日期留结论，出处注记一并删，历史归 git）。
2. **`cs.notes` 唯一写入点冲突** → **已裁：①删回写，且砍发散创作职责**——char-illus-designer 对着装纯执行透传（notes 槽位 = 图上 cos.notes 原样透传，不创作、不回写）；cs.notes 写入归 costume/stager 层，唯一写入点成立。存量证据：16 条非空 notes 均为 costume/stager 层底稿形态，回填路径零实例，且覆盖式回写反冲底稿。
3. **Schema 节点文件头部流程语义段** → **已裁：本轮不动**（另开专项）。
4. **references 大文档的废弃行型护栏** → **已裁：连护栏一并删**（边界：references 文档删；Schema 文件按 3 本轮不动）。
