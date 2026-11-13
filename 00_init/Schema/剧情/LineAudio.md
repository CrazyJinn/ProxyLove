## 台词行（LineAudio）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

一句台词/旁白/结构行，每行一个节点。节点 id 即行身份（插入/删除行不漂移）；wav 母带按 `master_path` 属性落盘（`15_声音/<ch_hexid>/<block_hexid>/<行_hexid>.wav`，规则派生自 LineAudio.id + 所属 Chapter.id + scene_block_id）。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62（= 行身份） |
| op | 行类型 | enum | 是 | `say`/`narrate`/`transition`/`bed_start`/`bed_end`/`label`/`choice`/`hide`/`ending`。**transition**=点状音效（1~2s 播完再接下一句）；**bed_start/bed_end**=音床起止对（区间声景循环，同块配对）；**choice**=选择行（连续 `*`/`+` 聚合一条）；**hide**=立绘下台指令（清 slots 角色槽）；场景标题不进行（块 id=scene_id 直连 Scene） |
| who | 说话人 | string | 否 | say 行必填（Character.name 原名） |
| pos | 立绘位 | enum | 否 | `left`/`center`/`right`；拆分按块内规则自动分配（1 人 center / 2 人先左后右 / ≥3 人按首话序），定稿 `pos:` 行可覆盖 |
| text | 行正文 | string | 否 | **行正文唯一载体**（2026-11-12 M3 合并：原 name 双写字段已删）；投影字幕用；choice 行选项明细在 options |
| tts_text | 配音变体 | string | 否 | 仅 say 行；text 的标点/停顿级变体，TTS 实际输入——**禁增删改任何汉字**、不得写回 text、一句一变体 |
| kind | 结局类型 | enum | 否 | 仅 op=ending：`BE`/`TE`/`HE`/`NE` |
| options | 选项清单 | json string | 否 | 仅 op=choice：`[{label, to \| scene \| leads_to_ending+kind}]`；签名=options 序列化 |
| bed | 音床标识 | string | 否 | 仅 bed_start/bed_end：`[A-Za-z0-9_]+`，同 scene_block 配对 |
| prompt | 生成提示 | string | 否 | 仅 bed_start：AudioFly 英文提示；重产复用原文，不即兴改写 |
| scene_block_id | 场景块 | string | 否 | 所有行：块归属——**=所写机位的 scene_id（Scene 节点雪花 id）**，id 直连；同机位多段共用同一 id，段序由行序承载 |
| voice_key | 配音键 | string | 否 | **= hexid(本节点 id)**（运行时 voices 文件名主体），配音后写 |
| ambient_track | 环境音键 | string | 否 | 仅 transition/bed_start 行：**= hexid(本节点 id)**（运行时 sfx 文件名主体；voice/sfx 归属由本字段与 voice_key 谁非空区分，播放行为由 op 分发） |
| master_path | 母带路径 | string | 否 | `15_声音/<ch_hexid>/<block_hexid>/<行_hexid>.wav`——**母带唯一权威**（dashboard 试听/发布/清理全读它；bind 时随 voice_key 一并落图） |
| emotion | 情绪 | string | 否 | 配音期判别（12 词表）；标注用，不进合成参数 |
| clone_mode | 克隆模式 | enum | 否 | 仅 say 行：`icl`（ref 韵律迁移，缺省）/ `xvec`（文本主导演绎） |
| text_sha1 | 文本指纹 | string | 否 | sha1(text)，重拆对齐/stale 判定依据 |
| status | 流程状态 | int | 否 | `0` 待配音 / `-1` 被驳回或级联作废（**驳回即重配**：驳回动作 REMOVE voice_key，重拆复用条件即不满足）|

**status 枚举**：`0` 待配音 → `10` 配完待审 → `11` 已批。`-1` 作废（sync 级联）**或人工驳回**（驳回动作 = `SET status=-1 REMOVE voice_key`——voice_key 缺失使重拆恢复条件不满足，必置 0 强制重配；master_path 保留可回听旧版）。音频行（say/transition/bed_start）走 `0→10→11`；非音频行（narrate/label/ending/choice/hide/bed_end）拆分即 `11`。行 status 只代表音频——文字定稿经 Section 定稿审（10→11，见上）把关，人工微调走 dashboard 定稿编辑器（保存即 11）。

---
