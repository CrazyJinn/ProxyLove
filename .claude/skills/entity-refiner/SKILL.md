---
name: entity-refiner
description: |
  占位实体细化层——共识/定稿文档中占位 Character 的随建细化，或点名既有 Character 治存量：priority（P0~P5 六级）、常驻地双占位（保留名「居住地点占位」「工作地点占位」+ at 边意图）、基础身份 Lore（按 priority 软区间条数）。产出**就地改写**同一文档对应条目的「细化：」块（before/after 留痕），零图写入、不产 cypher、不跑 lint、不生成 snowflake——Schema 字段级契约由 suggest-consumer 消费时强制。
  由 event-design agent 调度（共识/定稿含占位 Character 条目且无细化块时，先于 stager/consumer 派发）；或用户点名既有 Character（如「细化陆择」「给陆择补常驻地」）走存量治理——指称既有 id，不产占位。Location 一律保留占位不细化（保留名占位为合法终态，不进空间化生产链）。
  在共识/定稿落盘后需要细化占位人物、或治存量缺常驻地/priority/Lore 的人物时使用。
argument-hint: <文档路径（02_剧情数据/*_共识.md | *_定稿.md） | char 名或 id（存量点名）>
arguments:
  - doc_or_char
allowed-tools: Read, Bash, Write
---

# 占位实体细化（entity-refiner）

**只细化 Character，Location 一律保留占位。** 输入是文档（含 I1 占位 Character 条目）或点名既有 Character；输出是就地改写的「细化：」块——本层是自然语言草稿层，创作判断在本层发生，图物化归 suggest-consumer（严检 + 建议 JSON + 执行确认门）。

## 细化范围（三条，均只挂 Character）

1. **priority**（P0~P5 六级，生产链准入：P0~P4 进、P5 纯提及不进）：

| 级 | 定位 | 生产链 | 基础 Lore 条数（软区间） |
|----|------|--------|------------------------|
| P0 | 主角 | 进 | 5~8 |
| P1 | 核心配角 | 进 | 4~5 |
| P2 | 重要配角 | 进 | 3~4 |
| P3 | 常驻配角（多事件出场） | 进 | 2~3 |
| P4 | 一次性配角（单事件/单节） | 进 | 1~2 |
| P5 | 纯提及人物（不出场只被谈到） | 不进 | 0~1 |

2. **常驻地双占位**（at 边意图）：**一律新增两个带宿主 id 后缀的保留名占位 Location**——`居住地点占位·<宿主Character id>` / `工作地点占位·<宿主Character id>`（如「居住地点占位·QP23NrFZrz」），不另起具体地名、不写定位描述、不查不推既有 Location 复用。**后缀用宿主 id 不用人名**：人名可重复、可变更，id 稳定唯一（雪花、改名零漂移）——占位名全局唯一，同名查重照常适用（同宿主同名占位再次出现=真冲突，退回）；消费/审阅侧不会把不同人物的占位误读为同一地点，宿主一跳可查（at 边）。
   - **豁免口（唯一）**：人物存在「退休 / 无业 / 无固定居所 / 纯线上人物」类事实时，对应占位省略——**事实本身写进基础 Lore**（如「已退休，鱼摊去年盘给徒弟」），不在条目里写「工作地：无」注记；省略时汇报注明依据的 Lore 条目。
   - **工作地=居住地同地点时，只写居住**：不另建工作占位、不挂工作边、不为「居家工作」单独提 Lore（如居家代练、居家接单——职业事实若图中已有则不重复提）。
   - 时间只写语义（「一直住这」「2024-03 起租」「搬过一次」），起止格式与哨兵（`开篇前`/`至今`）换算归 consumer，本层不背。
3. **基础 Lore**：只收**身份事实**——职业、家世、婚育、履历、能力这类「放在第一章和最后一章都成立」的固有设定；每条标 knowledge_level 语义（1 公开 / 2 参与 / 3 深层）。条数按上表软区间（非硬门控，用户可增删；>区间上限提示拆批）。

**不收**（各归各层）：剧情因果→Event、认知分布→Info、性格调性→vibe（ideator 已给，不改）、双边关系→relation 边、世界观规则/Location 设定→构图期人工拍板。

## 流程（五步）

### 0. 读输入 + 圈条目

- 文档路径入参：Read 后找全部 I1 占位 Character 条目（`[I1 占位 Character]` 或语义同款）；**已有「细化：」块的跳过**（幂等，不重复细化）。文档找不到占位条目 → 汇报「无待细化条目」即止。
- char 名/ id 入参（存量点名）：Bash 查图（`MATCH (c:Character {name:'…'}) RETURN c.id, c.name, c.priority, c.vibe`）拿实存 id 与现状（at 边数、既有 has_info→Lore 清单、involved 事件数）——细化产物指称既有 id，不产占位、不改 name/vibe。
- 每个待细化人物顺带查图做依据：involved 事件数、挂线（StoryArc 途经）、at 边现状、既有 Lore 清单（Lore 起草要避开语义重复）。

### 1. 起草细化

每人一组建议：priority 判级（依据：involved 事件数 / 挂线 / 是否出场还是仅被提及——图上实查与常识推断分离标注）+ 双占位（默认两条；豁免口命中则省略并给 Lore 事实）+ 基础 Lore 草案（按区间条数，title 为干净事实陈述）。

### 2. 逐条敲定（一次一问，沿用 event-ideator ask 纪律）

每问附推荐答案与依据；用户可改判级、增删 Lore、否决豁免。全部条目有处置（敲定/放弃留痕）后才进下一步。

### 3. 就地改写

Write 回**同一文档**：在对应 I1 条目下追加「细化（entity-refiner）：」块，格式照抄：

```markdown
- 细化（entity-refiner）：
  - priority: P3
  - 常驻地：
    - 居住: [占位：居住地点占位·<宿主id>]
    - 工作: [占位：工作地点占位·<宿主id>]
  - 基础 lore：卖了十年鱼，独子在外地（kl=1）；已退休，鱼摊去年盘给徒弟（kl=1）
  - reason: <判级依据，图上实查/常识推断分离标注>
```

（豁免时常驻地只列未省略的一行；存量点名时 `居住: NvXxx（既有 Location id）` 也可——点名轮允许挂既有，新占位轮一律保留名。）

### 4. 汇报

细化条目数 + 每人 before/after + 豁免清单（含依据 Lore）+ 放弃清单 + Lore 超区间提示（如有）。**汇报完成即止，交回 event-design agent 调度**——本 skill 不指定下游（stager/consumer 由 agent 依文档形态派发）；用户直触时提示「可继续拆解演出或直接组装建议 JSON」。

## 红线

- **零图写入**：不产 cypher、不跑 snowflake、不跑 lint、不 SET 任何属性——一切物化经 suggest-consumer 执行确认门。
- **只动「细化：」块**：不改条目正文（vibe/事件/Info/故事线内容归原层），不改其他条目，不动 Location 占位的名称与定位。
- **双占位一律新增带宿主 id 后缀的保留名**（`居住地点占位·<宿主id>`/`工作地点占位·<宿主id>`，后缀=id 不用人名——人名可重可改），不推复用、不起地名；保留名占位是合法终态（恒 priority=P3，不进空间化生产链），后续有事件要 occurs_at 指向时才由 ideator/stager 提案升级为实名——本层不主动触发。**工作地与居住地同地点时只写居住**（不建工作占位、不挂工作边、不为居家工作单独提 Lore）。
- **基础 Lore 判据**：身份事实且禁备忘/推导/编号引用/归属标注；与该人物既有 Lore 语义重复的不重复提（consumer 宿主查重会退回）。
- 存量点名轮：只补 priority/at/Lore，不改 name/vibe/ref_image_path 等既有属性（改判 priority 是例外——点名轮的判级更新即本层职责）。

## 参考文档

- [Schema/角色美术/Character.md](../../../00_init/Schema/角色美术/Character.md)（priority 六级）/ [Schema/角色美术/边.md](../../../00_init/Schema/角色美术/边.md)（at 边：type 词表 + 起止哨兵）
- [Schema/剧情/Lore.md](../../../00_init/Schema/剧情/Lore.md)（Lore 字段表 + knowledge_level 枚举）/ [Schema/剧情/边.md](../../../00_init/Schema/剧情/边.md)（has_info 宿主边）
- [suggest-consumer](../suggest-consumer/SKILL.md)（细化块的物化层：严检 + 建议 JSON + 执行确认门）
