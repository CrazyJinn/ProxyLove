---
name: chapter-publisher
description: |
  把全章各节产物就绪（各节 Section.status=11 ∧ 该节全部台词行 LineAudio=11）的章节从图发布到运行时 `99_game/`：
  用 generate_portrait_map.py（产出 chapter-map：bgm 段）+ merge_sections_to_chapter.py --chapter --chapter-map 把全章图行（Section-produces{order}->LineAudio 逐句行，按节序/order 投影；舞台调度 say.pos/hide 自各节 台词.ink 现算注入，不落图）合并为单一章 JSON（say.portrait 沿 `LineAudio-[:uses]->StandingIllustration` 边投影为立绘键 hexid(stand_id)——stand_id 全局唯一；缺 uses 边的 say 行打警告、portrait 空串；BGM 从图 Scene-has_bgm->BgmTrack 注入 scene-block，track=hexid(bgm_id)）拷到 99_game/data/chapters/ + status=11 的立绘/背景资源 + status=2 的 BgmTrack 音频到 99_game/assets/ + 更新 manifest（--rebuild）+ 产出章资源清单 chapter_packs.json（Web 按章分包依据）。
  章 stem = hexid(Chapter.id)（16 位小写 hex，to_hexid——章 JSON/pck 文件名主体；chapter_packs 条目内嵌 title/chapter_no 供运行时章下拉显示排序）。
  在全章各节定稿+逐句音频审批通过且所需立绘就绪、需发布到 Godot 运行时时使用；由用户直接触发（不在 plot-design 职责内，plot-design 推进到全章就绪即止）。
argument-hint: <chapter_id>
arguments:
  - chapter_id
allowed-tools: Read, Bash, Write, Edit
---

# 章节发布（Chapter + 各 Section → 99_game）

把审阅通过的章节从**图**（LineAudio 逐句行，台词.ink 为人机界面）发布到**运行时区**（`99_game/`）：
**从图投影全章各节台词行合并为一个章 JSON** 落到 `99_game/data/chapters/`（Godot 只读 JSON，运行时不感知节层；行节点 id 等图字段被投影丢弃，say.voice 取自行节点 voice_key），拷贝章节涉及的立绘/背景图片/BGM 音频到 `99_game/assets/`，更新 `manifest.json`，并产出**章资源清单** `chapter_packs.json`（Web 按章分包导出依据）。
发布是**确定性转换+拷贝**（非 LLM 创作），幂等——重复发布覆盖旧文件，无副作用。

**id 锚定（2026-10-31 起）**：章 stem 与全部运行时键（立绘/场景/voices/sfx/bgm）均为节点 id 的 **hexid**（`to_hexid(id)` 16 位小写 hex，[snowflake_base62.py](../../../.claude/scripts/snowflake_base62.py) 与 Base62 互逆）——name/title 改名零漂移；显示名（章 title/场景名/角色名）由运行时经 chapter_packs meta / 图查询回显。

## 参数

| 参数 | 说明 |
|------|------|
| chapter_id | Chapter 节点 ID（snowflake Base62） |

## 流程

### 1. 查询章节与各节 + 前驱状态

通过 `${CLAUDE_SKILL_DIR}/../../scripts/cypher_exec.py` 查 Chapter + 各 Section + 编排子图：

```cypher
// (1) Chapter 本体（无 status 起章无审批态）
MATCH (ch:Chapter {id:'<chapter_id>'})
RETURN ch.title AS title, ch.chapter_no AS no;
// (2) 各 Section（按 section_no）+ 定稿态 + 逐句行聚合 + 前驱校验
MATCH (ch:Chapter {id:'<chapter_id>'})-[:has_section]->(sec:Section)
OPTIONAL MATCH (sec)-[:produces]->(l:LineAudio)
RETURN sec.section_no AS no, sec.title AS title,
       sec.status AS sc_status, sec.script_path AS script_path,
       count(l) AS line_count,
       sum(CASE WHEN coalesce(l.status, 0) = 11 THEN 1 ELSE 0 END) AS line_done
ORDER BY sec.section_no;
// (3) 全章 background 图层（场景集 = 各节行 scene_block_id 集合→Scene id 直查——发布投影权威；
//     历史节（无 includes）与新节通吃；scene 键 = hexid(Scene.id)，与章 JSON scenes[].scene 同源）
MATCH (s:Scene)
WHERE s.id IN ['<各行 scene_block_id 去重集合（即 scene_id）>']
OPTIONAL MATCH (s)-[:has_layer]->(sl:SceneLayer {layer_type:'background'})
RETURN DISTINCT s.id AS scene_id, sl.image_path AS bg_image, sl.status AS bg_status;
// (3b) 全章 BGM（同上场景集 JOIN has_bgm；status=2 才拷贝/注入，<2 警告跳过；generate_bgm 已内置此逻辑）
MATCH (s:Scene)-[:has_bgm]->(b:BgmTrack)
WHERE s.id IN ['<同上场景 id 集>']
RETURN DISTINCT s.id AS scene_id, b.id AS bgm_id, b.name AS track_name, b.status AS bgm_status, b.audio_path AS audio_path;
// (4) 本章被引用立绘（LineAudio-uses->stand：选绘行级直连——拷贝清单=被引用清单，与 requires 同源；
//     立绘键 = hexid(stand.id)，无需回溯角色/着装/变体名）
MATCH (ch:Chapter {id:'<chapter_id>'})-[:has_section]->(:Section)
      -[:produces]->(l:LineAudio)-[:uses]->(stand:StandingIllustration)
RETURN DISTINCT stand.id AS stand_id, stand.image_path AS image_path, stand.status AS status;
// (4b) 选绘缺口计数（say 行无 uses 边——发布将打警告、portrait 空串、运行时占位图兜底）
MATCH (ch:Chapter {id:'<chapter_id>'})-[:has_section]->(:Section)
      -[:produces]->(l:LineAudio)
WHERE l.op = 'say' AND NOT (l)-[:uses]->(:StandingIllustration)
RETURN count(l) AS say_no_stand;
```

**前驱校验**：
- **每节必须就绪：`sc_status=11` ∧ `line_count>0 ∧ line_done=line_count`**（定稿在位 + 该节全部台词行声音已批）——章真正可发布 = 全部节产物就绪（章无 status）。任一不满足则停止并提示先在 dashboard 推进对应节（含拆分配音、逐句音频审）。
- 被引用立绘（uses 边目标）：`status=11` 且 `image_path` 非空的才拷贝；`status≠11` 的逐个**警告**（运行时该变体走占位图），不阻断发布（让已就绪资源先上线）。`say_no_stand>0` 时**警告** N 句缺选绘（该批句运行时保持上一张/占位图）。
- background SceneLayer：同理，`status=11` 且 `image_path` 非空才拷贝。
- BgmTrack：`status=2` 且 `audio_path` 文件存在的才拷贝/注入；`<2` 或文件缺失逐个**警告**（该场景运行时无 BGM，静默），不阻断发布。
- 环境音行（可选附加查询）：`MATCH (ch:Chapter {id:'<chapter_id>'})-[:has_section]->(:Section)-[:produces]->(l:LineAudio) WHERE l.status=11 AND l.ambient_track IS NOT NULL RETURN DISTINCT l.ambient_track AS track`——本章已批环境音的 track 清单（chapter_packs 用；拷贝由下步 (e) publish 统一做）。以 ambient_track 字段存在为准、不看 op（转场音效 op=transition 与 narrate 内嵌声景 ambience 都算）。注意环境音行未全批会卡各节产物链就绪判定（行 gate），与 say 同规。

### 2. 合并拍平 + 拷贝资源到 99_game/

**章 stem**：`stem = to_hexid('<chapter_id>')`（16 位小写 hex；`python .claude/scripts/snowflake_base62.py -x <id1> <id2>`）——章 JSON/`<stem>.pck` 文件名主体。旧 `chapter<NN>_<章概述>` name 派生已废（章 title 改名零漂移；显示名进 chapter_packs 条目 meta）。合并输入 = 全章图行（工具内部按 section_no 节序 + produces.order 行序投影）。

```bash
# 确保目标目录存在
mkdir -p 99_game/data/chapters 99_game/assets/portraits 99_game/assets/scenes 99_game/assets/bgm

# (a.0) 章映射 chapter-map：bgm 段（Scene-has_bgm->BgmTrack，仅 status=2 进 map；
#       键=hexid(scene.id)、track=hexid(bgm.id)，与章 JSON scenes[].scene 同源 join）。
#       立绘键由 merge 沿 LineAudio-[:uses]->stand 边在投影期直接解析
python 99_game/tools/generate_portrait_map.py '<chapter_id>' -o '99_game/data/.cache/chapter-map-<stem>.json'

# (a) 剧本：从图投影全章台词行 → 99_game/data/chapters/<stem>.json（Chapter→Section(section_no)→
#     Section-produces{order}->LineAudio；前置校验各节产物就绪；
#     say.portrait 沿 uses 边投影为 hexid(stand_id)（缺边 say 行警告 + 空串）；--chapter-map 注入
#     scene-block.bgm；requires.portraits = 投影键并集；
#     行节点 id 等图字段投影丢弃，say.voice = 行节点 voice_key（hexid(行id)））
python 99_game/tools/merge_sections_to_chapter.py \
  --chapter '<chapter_id>' \
  --chapter-map '99_game/data/.cache/chapter-map-<stem>.json' \
  -o '99_game/data/chapters/<stem>.json'
python 99_game/tools/validate_chapter.py '99_game/data/chapters/<stem>.json' 99_game/data/剧本.schema.json
#   validate FAIL → 中断发布，报警（剧本 schema 不合，回 台词.ink 修对应节并重新走拆分/审批）
#   注：合并工具内置 scene-block id 章内唯一性校验（重复则报错）——若报 id 重复，说明图数据/上游产物引用了重复块 id，需回上游修正。

# (b) 立绘：透明原图直通 + 头位归一化 → 99_game/assets/portraits/<hexid(stand_id)>.png
#     立绘由生成端直出透明 PNG（提示词英文透明措辞驱动，绿幕抠图已退役）；本步不抠图，
#     仅以人物高/7.5 头身为尺度、YuNet 双眼中心为锚点缩放平移，使同角色各变体头部（眼线）
#     落在画布同一水平线（人物等高 1200，输出按前景紧凑裁剪、宽随双眼锚定）。
#     输入无 alpha 通道会直接报错（旧绿底立绘须先重生成再发布）。原图 06_/ 不动。
#     <键> = hexid(stand_id)（与 manifest 键、合并 JSON requires.portraits 一致——
#     三处同经 portrait_key.make_key，键源 = uses 边的 stand.id）
python 99_game/tools/process_portrait.py '<image_path>' -o '99_game/assets/portraits/<hexid(stand_id)>.png'

# (c) 背景：SceneLayer.image_path → 99_game/assets/scenes/<hexid(scene_id)>.png
cp '<bg_image>' '99_game/assets/scenes/<hexid(scene_id)>.png'

# (d) BGM：status=2 的 BgmTrack.audio_path → 99_game/assets/bgm/<hexid(bgm_id)>.wav
cp '13_BGM/<hexid(bgm_id)>/<hexid(bgm_id)>.wav' '99_game/assets/bgm/<hexid(bgm_id)>.wav'

# (e) 音频（voices + sfx 一步）：按章查已批（status=11）音频行 → 母带拷运行时
#     voice_key → 99_game/assets/voices/<hexid(行id)>.wav；ambient_track（含 narrate 内嵌
#     声景）→ 99_game/assets/sfx/<hexid(行id)>.wav。源=母带图行 master_path 属性
#     （15_声音/<ch_hexid>/<block_hexid>/，缺失时规则派生兜底），幂等，
#     母带缺失警告不阻断。**99_game/assets 只经发布收已批音频**——生成期无 sync，
#     dashboard 逐句审批试听直接读母带
python .claude/skills/section-voice-publisher/scripts/voice_bundler.py publish --chapter '<chapter_id>'
```

> 源路径（`image_path`/各节 `script_path`）是项目根相对，`cp`/合并时 cwd 应在项目根。立绘目标路径用 `hexid(stand_id)`（来自第 1 步 uses 边查询），与 manifest 的 portraits 键、合并后 JSON 的 `meta.requires.portraits` 三处对齐。键由 merge_sections_to_chapter.py / manifest_builder.py 经 [portrait_key.make_key](../../../99_game/tools/portrait_key.py) 同源生成。
> 缺源文件（`image_path` 指向的图不存在）则**警告跳过**该资源，不中断。

### 3. 重建 manifest（--rebuild 全量图驱动）

manifest_builder 已五段全图驱动（portraits/portrait_scales/scenes/voices/sfx/bgm 均查图，键全 hexid；bgm 段收 status=2 的 BgmTrack——无需再手补；cg 仍手写保留）。id 锚定切换后**必须 `--rebuild`** 清除旧 name 键，防死键累积：

```bash
python 99_game/tools/manifest_builder.py --rebuild
```

**补 manifest.voices 段**：节级配音（section-voice-publisher）已把 `audio.key` 写进各节台词行，投影合并时成为章 JSON 的 `say.voice`；manifest 的 voices 段在此补（读合并后章 JSON 的 `say.voice` 推导，节级阶段章未合并无法写）：

```bash
# 写 manifest.voices 段（{key: assets/voices/<key>.wav}）
python .claude/skills/section-voice-publisher/scripts/voice_bundler.py manifest '99_game/data/chapters/<stem>.json' --ext wav
# 导出本章 voice 键 CSV，供下一步 chapter_packs.voices
python .claude/skills/section-voice-publisher/scripts/voice_bundler.py list '99_game/data/chapters/<stem>.json' > '99_game/data/.cache/voices-<stem>.csv'
```

### 4. 产出章资源清单 chapter_packs.json（Web 分包依据）

把本章用到的资源键记入 `99_game/data/chapter_packs.json`，供导出工具按章把资源分组打成 `<stem>.pck`（pck 内路径与全局 manifest 一致，挂载后 `res://` 全局路径命中）。**分包粒度仍是章 stem**（= hexid(Chapter.id)；运行时不感知节层；条目内嵌 `title`/`chapter_no` 供 Title 章下拉显示与排序——**必须传**，否则下拉显示 hexid 码）。

数据源 = 合并后章 JSON 的 `meta.requires.portraits`（投影期已沿 uses 边解析，与 lines 引用同源）+ 第 1 步全章背景 + 第 3 步导出的 voice 键 + 章内各 scene-block 的 bgm：
- `portraits`：`hexid(stand_id)`（直接取合并 JSON 的 requires.portraits）
- `scenes`：`hexid(scene_id)`（has_layer background）
- `voices`：`hexid(行id)`（第 3 步 `voice_bundler list` 导出的 CSV）
- `bgm`：`hexid(bgm_id)`（合并时从图 Scene-has_bgm 注入各 scene-block 的 `bgm.track`，去重；漏传则 Web 章包缺音乐）

```bash
python 99_game/tools/chapter_packs_updater.py '<stem>' \
  --title '<Chapter.title>' --chapter-no <chapter_no> \
  --portraits '<hexid1>,<hexid2>' --scenes '<hexid1>,<hexid2>' \
  --voices "$(cat '99_game/data/.cache/voices-<stem>.csv')" \
  --bgm '<hexid1>,<hexid2>' --sfx '<已批 ambient 行 track CSV>'
```

工具幂等：覆盖该 stem 条目，保留其他章。空列表（该章无立绘/背景）也要写入，保持清单完整。

### 5. 汇报

列出：发布的章 JSON 路径（`99_game/data/chapters/<stem>.json`，stem=hexid）、合并的节数、拷贝的立绘清单（`hexid(stand_id)`，括注查图得的角色/着装/变体名）、背景清单（`hexid(scene_id)` + 场景名）、BGM 清单（`hexid(bgm_id)` + track 名）、跳过/缺失的资源警告、manifest 重建结果、章清单更新结果（该章 portraits/scenes/bgm 条数）。
附运行时入口提示：`GameManager.start_new_game('<stem>', '<首节首 scene-block id>')`（stem = hexid(Chapter.id)；首 scene-block id 取 section_no=0 节的第一个段 id）。

## Web 发布前的额外步骤（导出阶段，非本 skill）

剧本加密 + 按章分包在**导出时**做（本 skill 只产明文 + 清单，保持桌面/开发期可读）：

1. **加密剧本**（挡自动扒包，可选但 Web 推荐）：覆盖式加密，运行时 ChapterLoader 检测 magic 头自动解密。
   ```bash
   pip install -r 99_game/tools/requirements.txt   # 需 cryptography
   python 99_game/tools/encrypt_chapter.py '99_game/data/chapters/<stem>.json' '99_game/data/chapters/<stem>.json'
   ```
   ⚠️ 加密后无法再 `validate_chapter.py`（明文），故加密必须在本 skill 流程之后。
2. **按章分包 + Web 导出**（2026-08-30 起有完整流水线）：`python 99_game/tools/publish_web.py` 一键完成「字体子集化 → 导出 Web 主包（exclude assets/chapters/full.ttf）→ build_chapter_packs.gd 按清单产各章 `<stem>.pck` → 恢复字体」；产物上传 R2 用 `deploy_r2.py`（详见两个脚本头部注释）。分包机制：主 pck 不含任何章资源，开局/读档/跨章由 ChapterPackLoader 下载章包挂载（带进度 UI）。

## 与 section-voice-publisher 的边界

`voice` 字段（`say.voice`）由 [section-voice-publisher](../section-voice-publisher/SKILL.md) 在**节级定稿后**经 `bind-graph` 写进行节点 `voice_key`，本 skill 图投影合并时自动带进章 JSON：

- **生产时序**：chapter-dialoguer（台词.ink → Section.status=11 定稿在位）→ **section-voice-publisher**（拆分进图 → 节级 TTS + bind-graph 写行节点 → 行 status=10→逐句审→11）→ **chapter-publisher**（图投影台词行[voice=voice_key] + 立绘/BGM + 补 manifest.voices / chapter_packs.voices）。
- 本 skill 合并时 say 行节点已含 voice_key（投影把 `voice_key` 投为 `say.voice`）→ 合并后章 JSON 每 say 自带 voice，**无需再注入**。
- **本 skill 末尾补 manifest.voices + chapter_packs.voices**（节级阶段章未合并，这两处无法写；合并后用 voice_bundler 读章 JSON 推导补齐，见第 3、4 步）。
- **行身份稳定寻址**：voice_key = hexid(LineAudio 行节点 id)——台词.ink 插入/删除/移动行不影响其他行 key；某句台词被改（stale 重配）后重跑该节 section-voice-publisher 覆盖对应 wav 即可，无全节重配。
- chapter JSON 的 `meta.requires` 不含 voices（voice 键按行节点 id 算，不进 requires）。

## 参考文档

- 台词.ink 方言（人读定稿）与图行投影：[script_splitter.py](../section-voice-publisher/scripts/script_splitter.py)（parse_ink——机器侧权威；方言规范见 [ink方言规范.md](../chapter-dialoguer/references/ink方言规范.md)）+ [merge_sections_to_chapter.py](../../../99_game/tools/merge_sections_to_chapter.py)（graph_lines_to_doc 图行投影）
- 节合并工具：[99_game/tools/merge_sections_to_chapter.py](../../../99_game/tools/merge_sections_to_chapter.py)（图行 → 1 章 JSON）
- manifest 生成器：[99_game/tools/manifest_builder.py](../../../99_game/tools/manifest_builder.py)（--rebuild 全量图驱动）
- 章资源清单更新器：[99_game/tools/chapter_packs_updater.py](../../../99_game/tools/chapter_packs_updater.py)
- 剧本加密（Web）：[99_game/tools/encrypt_chapter.py](../../../99_game/tools/encrypt_chapter.py) ↔ 运行时 [99_game/scripts/util/ScriptCipher.gd](../../../99_game/scripts/util/ScriptCipher.gd)
- 章包加载（运行时）：[99_game/scripts/autoload/ChapterPackLoader.gd](../../../99_game/scripts/autoload/ChapterPackLoader.gd)
- id 锚定与 hexid：[00_init/Schema/剧情.md](../../../00_init/Schema/剧情.md) 头部注记 + [snowflake_base62.py](../../../.claude/scripts/snowflake_base62.py)
- 剧情 Schema（Chapter/Section/has_section/LineAudio）：[00_init/Schema/剧情.md](../../../00_init/Schema/剧情.md)
