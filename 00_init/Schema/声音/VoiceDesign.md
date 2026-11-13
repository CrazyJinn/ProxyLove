## 声音设计（VoiceDesign）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

每个角色一个，基线音色——Qwen VoiceDesign 自然语言 instruct + 固化音色的参考音频；基线确定后整章台词复用同一 ref_audio。情绪不建多维档案（由逐句 `tts_text` 变体承载）。区别于 LanguageStyle（文字层说话方式，`has_voice_style` 边）：本节点是声音层，供节级配音。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| name | 名称 | string | 是 | `<角色名>声音设计` |
| instruct | 声音设计指令 | string | 否 | Qwen VoiceDesign instruct 文本：六要素各一个明确值（年龄/性别/音色/气质/语速/尾音）；不写台词样例与模糊愿望；改音色=改原文而非追加 |
| ref_text | 参考文本 | string | 否 | 固化音色的**全角色统一**参考长句（54 字中性陈述，约 10~12 秒，覆盖翘舌/平舌/前后鼻音/复韵母）：`上午我把书桌上的三份文件整理好，然后把水杯和钥匙放进背包，中午在城南餐厅吃了一顿面，下午再准时把报告直接交给负责人。` |
| ref_audio_path | 参考音频 | string | 否 | `14_声音设计/<char_id>/ref.wav`（hexid 目录；候选「采用」后固化的 24kHz 正式产物，下游 24k 原生消费） |
| candidates_path | 候选清单 | string | 否 | `14_声音设计/<char_id>/candidates/candidates.json`（hexid 目录；瞬态目录，采用后整夹删除）；**非空 = status=10 的「候选待选」子态**（3 候选 ref + 每候选 3 情绪试听），候选采用后删除该属性 |
| adopted_candidate | 采用候选 | string | 否 | 候选 key（c1/c2/c3）——dashboard「采用」动作写入，标记固化自哪一候选 |
| status | 流程状态 | int | 否 | `0` |

**status 枚举**：`0` 待设计 → `10` ref 固化（生产完成**即待审**）→ `11` 批准。驳回归 `0`，作废 `-1`。`1`/`2` 为历史兼容值（旧流程中间态/生产完成态，不再写）。

> 无 `description` 字段——音色气质单一载体 = instruct（展示侧截取 instruct 即可）。

> `status=10` 两态（status 值不变，由 `candidates_path` 区分）：非空 = **候选待选**（人工逐候选试听「采用」固化 ref，status 仍 10 走二审）；空 = 单 ref 待审。**下游配音要求 `11`**——审批门为治理逐句克隆的 GPU 消耗而设。
> 无 `clone_prompt_path` 字段：clone prompt 由 voice_clone_runner 内存构建不落盘。

---
