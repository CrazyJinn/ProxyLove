## 背景音乐（BgmTrack）

> 字段全集以本表为准；skill 写入前 Read 本节，不凭记忆写字段。

一个场景一轨。**人工生成链**：依 Scene 情绪产描述文字（Scene 无关联时兜底自建节点）→ 用户在外部工具生成 wav 归档 `13_BGM/<bgm_id>/<bgm_id>.wav`（hexid 目录；检测到文件存在即置 2）。发布时注入章 JSON scene-block 的 bgm 字段。

| 字段 | 中文 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | 编号 | string | 是 | snowflake Base62 |
| name | 名称 | string | 是 | track 显示名（如 `晨离`）——纯人读，不锚定文件/键 |
| vibe | 氛围 | string | 否 | 音乐定位（情绪/氛围，1-2 句）——BGM 的恒定调性，与 Character.vibe/Scene.vibe 同族：只写音乐本身的味道（情绪/织体感），不写场景画面（归源 Scene.vibe）、剧情、织体/BPM/结构细节（归 prompt）（2026-11-13 自 description 更名；四问见 [Schema总览.md](../Schema总览.md)「属性撰写总则」） |
| prompt | 生成提示词 | string | 否 | 完整配方：场景曲定位+情绪基调+织体+BPM+结构（循环友好/总长）+收尾禁令，供外部工具生成——vibe 是味道、prompt 是配方，配方展开味道不复述画面 |
| audio_path | 音频路径 | string | 否 | 预制归档路径 `13_BGM/<bgm_id>/<bgm_id>.wav`（hexid 目录，手工放入即合格；运行时 manifest.bgm 键 = 章 JSON bgm.track = hexid(bgm_id) 同源）；`<bgm_id>/<bgm_id>.md` 随写图同步落盘存档 |
| mode | 播放模式 | string | 否 | `play` / `fade`（缺省 `play`，章 JSON bgm.mode） |
| loop | 循环 | boolean | 否 | 缺省 `true`（章 JSON bgm.loop） |
| status | 流程状态 | int | 否 | `0` |

**status 枚举**（无审批——音频由用户手工生成，放入即合格）：`0` 待设计 → `1` 文字描述已产出（等用户放 wav）→ `2` 音频已归档。作废 `-1`。

---
