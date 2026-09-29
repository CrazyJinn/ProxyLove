---
name: char-prompt-assembler
description: |
  从调用方传入的节点数据（设计元素 tags + 自由文本）组装图片生成提示词，派生为 prompt 文件并返回其路径。
  四种模式：DesignSheet（文生图）、DesignSheetDelta（图生图增量版——同人物仅变更 delta.notes 口述维度）、IllusDesign（图生图）、StandingIllustration（图生图）。
  纯产出层：不读写图数据库、不写 status，所有数据由调用方通过 data 参数提供。
  在需要为美术节点组装提示词或被其他 skill 调用时使用。
argument-hint: <mode> <data_json>
arguments:
  - mode
  - data
allowed-tools: Read, Bash, Write, Edit
---

> **纯产出层**：本 skill 只负责组装 prompt 文件并**返回文件路径**，**不读写图数据库、不写 status**。节点 `prompt_path` 字段与 `status` 由调用方（生产 skill）在「保存结果」步统一写入。`status=-1`（作废重做）时调用方会再次调用本 skill 覆盖旧 prompt 文件——本 skill 每次被调用都重新组装并覆盖。

# 提示词组装

从调用方传入的**设计元素 tags + 自由文本**组装图片生成提示词，派生为 **prompt 文件**并返回文件路径。不读写图数据库——所有数据由调用方通过 `data` 参数传入。

## 核心转换：tags → 自然语言

数据节点的可枚举维度以**标签**形式存储。组装时将每个标签展开为**自然语言描述句**，与自由文本字段一起，按 reference 模板的 markdown 结构组织成完整 prompt。

**复合字段**（eye/hair/garment）的值已是**合成组合描述**（如 `琥珀色上挑眼`、`深棕色大波浪长发`、`棉衬衫`），直接作为该维度的自然语言使用，无需再展开子维度。

- 标签 `hair_color=黑;挑染银` → "黑色长发，发丝间挑染银色"
- 标签 `garment="棉白衬衫"` → "白色棉质衬衫"
- 标签 `hand=叉腰` + `foot=前后开立` → "一手叉腰，双脚前后开立"

## 编写原则

- **标签展开为完整描述句**：转为自然语言（写"黑色长发"而非"hair_color:黑"）
- **主体 → 细节 → 风格**：先写主体，再补细节，画风放末尾
- **中文提示词**，按 reference 模板的 markdown 结构（标题/编号）组织
- **只提取不创作**：内容来自 data 参数（tags + 自由文本）和 `00_init/美术风格.md`，不臆造
- **去重不矛盾**：同维度的信息只在 tags 中表达一次（服装款式/颜色/材质统一在 `garment` 标签），避免提示词出现重复或矛盾描述
- **体态气质只用正向措辞，禁止负面体态词（含否定式）**：prompt 中不得出现「驼背 / 佝偻 / 含胸 / 塌腰」等负面体态字样——**否定句式也不行**（「不驼背佝偻」会把该体态词喂给模型、反而画出该姿态，2026-09-26 用户定规）。上游 adaptation_notes / delta_notes 若含此类否定句，组装时**丢弃该句**，用正向词替代表达（如「站姿挺拔舒展，肩背舒展打开，眼神坚定从容」）

## 输出流程（四种模式通用）

1. 解析 data，提取 tags（分号分隔串，需 split）、自由文本字段、`node.id`，以及调用方声明的 `output_path`
2. 从 `00_init/美术风格.md` 读取全局风格参数（线条、上色、色调等）；**背景按该文件「角色图片背景」节分模式处理——模式 A/B 画风段背景行固定声明不透明纯色背景（白色），模式 C 在画风段固化英文透明措辞（见模式 C 与立绘模板）**；**分辨率按当前模式从该文件的对应条目动态提取后写入 prompt 画风段（ASCII `x` 分隔，勿引入中文乘号 `×`）**——模式 A/B 取「设计图 / 立绘设计图」分辨率，模式 C 取「立绘」分辨率
3. 按模式规则组装 markdown prompt（见下方各模式 + reference 模板的维度结构）
4. 用 **Write 工具**写 prompt 文件到调用方在 data 中声明的 `output_path`（不经 shell，markdown 无损；目录不存在时 Write 自动创建）。**路径由调用方决定，assembler 透传，不自行拼接；三种模式均要求调用方在 `data` 中提供 `output_path`**
5. **返回 prompt 文件路径**给调用方（由调用方写入节点 `prompt_path` 字段）

> prompt 文件路径由调用方在 `output_path` 入参中声明，assembler 透传使用；每个节点的路径唯一性由调用方保证。

## 模式A：DesignSheet（文生图）

为三视图设计稿组装提示词。聚焦角色外貌，不涉及衣着——角色统一穿着深色基础衣物（黑色长袖压缩上衣与深色全长压缩裤，措辞为安全审核实测过的固定值，勿改回贴身/背心/短裤类），与肤色形成高对比。详细维度映射见 [references/template-设计图提示词.md](references/template-设计图提示词.md)。

**data 参数结构**：
```json
{
  "appearance": {
    "tags": {"shape_language":"...","age_impression":"...","body_type":"...","skin_tone":"...","hair":"...","eye":"...","lip_shape":"...","marks":"..."},
    "appearance":"...(自由文本:综合气质/身高)","visual_tone":"...","first_impression":"..."
  },
  "character": {"id":"<char_id>","name":"...","color_direction":"...(自由文本:配色逻辑)"},
  "node": {"id":"<designsheet_node_id>"},
  "output_path": "06_角色美术/<char_name>/prompt.md"
}
```

组装：从 `appearance.tags` 展开各维度（体态/肤色/发长发型发色/眼型瞳色/唇形/特殊标记）为自然语言，结合 `appearance` 自由文本（综合气质、身高）与 `character.color_direction`（配色逻辑），加贴身基础衣物说明，画风放末尾。画风段背景行固定声明**不透明纯色背景**（白色，无渐变、无纹理、无场景元素——设计图产物非透明）；图面要求**无描述性文字**（无标签/注记/说明文字），三视图可附 3 宫格特写（面部、手部等，见模板三视图规则）；**画风段分辨率取美术风格.md 的「设计图 / 立绘设计图」条目（动态提取，不硬编码数值，ASCII `x` 分隔）。**

## 模式A-delta：DesignSheetDelta（图生图增量版）

为**设计图增量版本**组装提示词——以参考版设计图为底图，仅变更口述维度（剧情永久外貌变更如剪发）。详细维度结构与增量纪律见 [references/template-设计图增量提示词.md](references/template-设计图增量提示词.md)。

**data 参数结构**：
```json
{
  "base": { "image": "06_角色美术/<char_name>/设计图.png", "summary": "参考版设计图（同人物）" },
  "delta": { "notes": "<口述改动原文>", "negation": "<对参考图旧特征的显式否定（只否定被变更维度）>" },
  "character": {"id":"<char_id>","name":"...","color_direction":"..."},
  "node": {"id":"<新designsheet_node_id>"},
  "output_path": "06_角色美术/<char_name>/<slug>/prompt.md"
}
```

组装（按模板四段顺序）：**同一人物开篇**（「与参考图为同一人物的角色设计图，全身三视图」）→ **保持段**（面部五官/体型肤色/特殊标记/黑色长袖压缩上衣+深色全长压缩裤底衣/静态姿态构图均与参考图完全一致不变）→ **变更段**（仅 `delta.notes` 展开为具体视觉描述句，唯一变更来源，禁止顺手改未口述项）→ **否定锚定段**（`delta.negation` 原样写入，压制参考图惯性）→ 画风段（同模式 A：三视图、无描述性文字、不透明纯色白背景、分辨率动态提取）。底衣措辞沿用模式 A 固定安全值。

## 模式B：IllusDesign（图生图）

为着装适配立绘设计图组装提示词。聚焦着装描述，不重复角色外貌（图生图以 DesignSheet 为参考底图，外貌已在底图）。详细维度映射见 [references/template-着装提示词.md](references/template-着装提示词.md)。

**data 参数结构**：
```json
{
  "costume": {
    "tags": {"outfit_style":"...","garment":"...","footwear":"...","accessory_type":"..."}
  },
  "illus": {"adaptation_notes":"...(可选)"},
  "character": {"id":"<char_id>","name":"..."},
  "node": {"id":"<illusdesign_node_id>"},
  "output_path": "06_角色美术/<char_name>/<CostumeStyle.name>/prompt.md"
}
```

组装：从 `costume.tags` 展开着装（风格/材质+颜色+类型/鞋/配饰）为自然语言，加 `adaptation_notes` 适配补充（无则跳过），画风放末尾。开头声明与画风段**不写背景内容**，画风段背景行固定声明**不透明纯色背景**（白色，产物非透明，禁止任何透明措辞）；图面要求**无描述性文字**，三视图可附 3 宫格特写；**画风段分辨率取美术风格.md 的「设计图 / 立绘设计图」条目（动态提取，不硬编码数值，ASCII `x` 分隔）。**

## 模式C：StandingIllustration（图生图）

为立绘表情变体组装提示词。描述全身立绘的表情与动作。详细规则见 [references/template-立绘提示词.md](references/template-立绘提示词.md)。

**data 参数结构**：
```json
{
  "stand": {
    "description":"...(自由文本:该变体在剧情该时刻的氛围/情绪情境，出图的首要依据)",
    "tags": {"variant_label":"...","eye":"...","brow":"...","mouth":"...","head_angle":"...","hand":"...","foot":"..."}
  },
  "voice": {"emotion_patterns":"...","description":"..."},
  "character": {"id":"<char_id>","name":"..."},
  "node": {"id":"<standing_node_id>"},
  "output_path": "06_角色美术/<char_name>/<CostumeStyle.name>/立绘/<variant_label>.md"
}
```

组装：**首要依据 `stand.description`（变体氛围/情绪情境）定调表情强度、身体朝向、动作张力**；固定前缀 `[角色名]立绘，全身像，`（不写背景——透明措辞固化在画风段背景行，不放前缀），随后**据 description 氛围自主决定身体面对镜头的朝向**（正视镜头/3/4侧身/全侧身/背影——默认/微笑倾向正视镜头，战斗/愤怒等动态倾向 3/4侧身，回眸/悲伤等倾向全侧身或背影）写在「全身像」之后；再从 `stand.tags` 展开表情（eye/brow/mouth/head_angle）与动作（hand/foot）为自然语言，结合 `voice.emotion_patterns` 补充情绪；**动态/强情绪变体的动作幅度应更大、更有张力**（见 [references/template-立绘提示词.md](references/template-立绘提示词.md) 编写要点）。**默认站姿**：人物保持站立体态——跨步/走路/重心偏移/前倾/挥臂等站姿范围内的大幅动作均可，坐/卧/跪/躺/跳起腾空等非站立体态仅当 stand.description（或调用方数据）明确要求时使用。**手持物品保持不变**：参考图（IllusDesign 立绘设计图）上已有的手持物品不丢失、不改变、不替换、不新增；提示词不描述手持物本身（参考图已携带）。画风放末尾，**画风段背景行固化英文透明措辞（原样写入、一字不改）**：`**背景**：主体完整居中，fully transparent background with alpha channel, no background elements, no cast shadow on background`——立绘产物**必须透明**；透明触发需措辞与 API 参数双在场（2026-09-13 实测：仅措辞连续返 RGB），调用方生成时须同时传 `--background transparent`（png 已由 infra-image-generator 全局强制）。**身体朝向与动作幅度由 LLM 据 `stand.description` 氛围自主生成**（data 里无硬编码朝向字段，description 是氛围依据）。**画风段分辨率取美术风格.md 的「立绘」条目（动态提取，不硬编码数值）。**

## 参考文档

- [设计图提示词模板](references/template-设计图提示词.md) — 维度结构与编写要点（模式A）
- [设计图增量提示词模板](references/template-设计图增量提示词.md) — 保持/变更/否定锚定结构与增量纪律（模式A-delta）
- [着装提示词模板](references/template-着装提示词.md) — 维度结构与编写要点（模式B）
- [立绘提示词模板](references/template-立绘提示词.md) — 表情+动作要素与变体规则（模式C）

> 模板文件的**维度结构**有效，但数据源以本文件各模式的 data 结构（tags + 自由文本）为准。
