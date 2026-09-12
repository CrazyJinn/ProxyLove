---
name: ambient-sfx-designer
description: |
  推进单节音频环境行（LineAudio op=transition 点状音效 sfx + op=bed_start 音床起，status=0）的音频产出——「实录 foley + AudioFly 声景」双通道：
  ① ambient_tasks.py 查待产行并预计算 track（前缀 amb-/bed-，杜绝手拼 key；bed 行并带出行上存量 prompt 供复用）→
  ② 类型由图行 op 决定（ambient_tasks.py 直带 kind）：sfx 点状行（短事件，1~2s 播完接下一句）走 Freesound CC0 实录检索，bed 音床行（声景 ~10s 全长原样）走 AudioFly 生成 →
  ③ Freesound 链：匿名 curl 搜索（CC0+时长过滤）→ 取最佳 1 条候选落 .tmp/ambient/ 请用户试听 → 转码落母带 + 15_声音/sfx_raw/SOURCES.md 登记；
  AudioFly 链：prompt 复用行上存量或现场翻写（AudioCaps 风格英文）→ ambient_fly.py jobs 单候选（env/.venv-audiofly）→ 用户试听 → finalize（bed 全长原样无淡入淡出，一次性播放；未播完时用户推进由程序 1s 淡出）→
  ④ 先产物后写图：SET ambient_track + status=10 待审即止（bed 行并持久化 l.prompt，重产可复用）——不拷运行时副本（dashboard 逐句审批试听读母带 15_声音/；99_game/assets/sfx 只由 chapter-publisher 发布时按 status=11 收录）。
  在单节定稿已拆分、需要产出/重做环境音时使用（由 plot-design 单节聚焦在配音步之后编排）。
argument-hint: <section_id>
arguments:
  - section_id
allowed-tools: Read, Bash, Write, Edit, Skill
---

# 音频环境层产出（sfx 点状实录 + bed 音床声景）

台词.ink 方言 v3 的音频行型（`sfx: <语义>` 点状 → op=transition；`bed+ <id> // <语义>` 音床起 → op=bed_start）
拆分进图后均为待产行（status=0）——本 skill 把它们产出为音频资产，走行级审批（10→11）
与其他音频行同构。旧「环境音」两型（独立行/内嵌）已废止（2026-09-03 存量迁移为 sfx/bed）。

**双通道分工**（2026-08-28 demo 验证结论 + v3 音床规格）：

| kind | 语义类型 | 通道 | 成品规格 | 依据 |
|---|---|---|---|---|
| sfx | 点状短事件（有明确起振/动作语义） | **Freesound CC0 实录** | 1~2s（峰值截取）+ 短淡出，**播完再接下一句** | 扩散模型对秒级高频单发事件糊，实录真实感碾压 |
| bed | 持续声景（底噪/氛围语义，区间播放） | **AudioFly 生成** | ~10s **全长原样**（无淡入淡出，**一次性播放不循环**——自然播完后推进直接切句；未播完时用户推进 → **1s 程序淡出**后再切句） | AudioCaps 评测超 Stable Audio Open（FD 40.1 vs 78.24），Apache 2.0 |

**track（= 母带/manifest 统一键）**：`<prefix>-<chapter_stem>-<scene_block_id>-<行节点id>`（sfx 行 prefix=amb（历史沿用）；bed 行 prefix=bed），由 ambient_tasks.py 预计算——**LLM 不手拼 key**；**行上已有 track 沿用原键**（键一经落图终身不换前缀，重跑覆盖母带）。母带 `15_声音/<stem>/<block>/<track>.wav`（审批试听源）；运行时副本 `99_game/assets/sfx/<track>.wav` 由 chapter-publisher 发布时按 status=11 拷贝，本 skill 不碰 99_game。

## 参数

| 参数 | 说明 |
|------|------|
| section_id | Section 节点 ID（snowflake） |

## 流程（三段式）

### 1. 查状态 + 产 jobs

前置：该节 SecScript=11 且已拆分（图有行）。跑：

```bash
python "${CLAUDE_SKILL_DIR}/scripts/ambient_tasks.py" --section '<section_id>' -o '.tmp/ambient-jobs-<stem>-sec<MM>.json'
```

0 条待产行（全 10/11）→ 直接汇报跳过。

### 2. 逐行确认类型 + 产出（先产物后写图）

**类型由图行 op 决定**（ambient_tasks.py 已在 jobs 里带 `kind`，无需再判）：
- `kind=sfx`：`sfx:` 行（点状音效，op=transition）——极短音（1~2s）运行时播完再接下一句；
- `kind=bed`：`bed+` 行（音床起，op=bed_start）——~10s 声景一次性播放；未播完时用户推进由程序 1s 淡出后切句，播完直接切。

**按 kind 直取**（sfx→Freesound、bed→AudioFly），个别语义明显不匹配时（如 bed 语义其实是单次事件）以语义为准并在汇报中说明。

#### 2a. Freesound 链（sfx 行，kind=sfx）

匿名 curl 检索（无需登录；网页搜索/CDN 预览均公开，仅下载原始无损需用户账号）：

```bash
# 搜索（英文关键词，CC0 + ≤5s 过滤；关键词由 LLM 从中文语义翻写，AudioCaps 风格：声源+空间+修饰）
curl -s 'https://freesound.org/search/?q=<english+keywords>&f=license%3A%22Creative+Commons+0%22+duration%3A%5B0+TO+5%5D' -H "User-Agent: Mozilla/5.0" \
  | grep -oE 'href="/people/[^"]+/sounds/[0-9]+/"' | sort -u | head -6
# 逐候选详情页确认许可并取 CDN 预览直链
curl -s "https://freesound.org/people/<user>/sounds/<id>/" -H "User-Agent: Mozilla/5.0" \
  | grep -oE '(https://cdn\.freesound\.org/previews/[^"]+-hq\.mp3)|(Creative Commons 0)'
# 下载 2~3 个候选到 .tmp/ambient/（128k mp3 试听质量；先 curl -o 再转 wav）
```

- 候选下载后**停下请用户试听**（`.tmp/ambient/`）。
**单候选制**（用户 2026-08-29 定）：每行只出 1 个候选试听，不做多选一——不满意就换检索词/换 seed 重出下一版，迭代到满意为止。
- 选定后：mp3 转 wav（`env/.venv-audiofly` 的 soundfile 可读 mp3）+ 裁剪（峰值截取 1~2s，可复用 `ambient_fly.py finalize --kind sfx --cut <秒>`，传 mp3 转出的临时 wav）+ 落母带路径。
- **SOURCES.md 登记**（Steam 商售合规留存）：在 `15_声音/sfx_raw/SOURCES.md` 追加一行 `| <文件 stem> | <声音名> | <作者> | <详情页 URL> | CC0 | <成品 track> | 备注 |`（成品 track 列填本行 amb-… 键——dashboard 批准后按此列自动删除原始素材，登记文本保留）。
- **无损升级可选不阻塞**：先以预览版落盘写图（流水线不断）；SKILL 汇报里注明「用户可事后登录 freesound.org 下载无损原件覆盖同名母带，track 不变图不动」。
- curl 失败/限流 → 降级：报告搜索结果页链接请用户手选，不硬造。

#### 2b. AudioFly 链（bed 行，kind=bed，env/.venv-audiofly）

```bash
# ① 生成单候选（10s 原生段 .tmp/ambient/<track>_c1.wav；模型 ~8GB 一次加载批量跑，count 默认 1）
env/.venv-audiofly/Scripts/python.exe "${CLAUDE_SKILL_DIR}/scripts/ambient_fly.py" jobs '.tmp/ambient-jobs-<stem>-sec<MM>.json'
# ② 用户选定后 finalize（音床：全长 ~10s 原样无淡入淡出；点状语义误判可 --kind sfx --cut 1.5）
env/.venv-audiofly/Scripts/python.exe "${CLAUDE_SKILL_DIR}/scripts/ambient_fly.py" finalize \
  '.tmp/ambient/<track>_c<N>.wav' '15_声音/<stem>/<block>/<track>.wav' --kind bed
```

**prompt（bed 行专用，持久化）**：jobs JSON 的 `prompt` 字段——**行上已有存量 prompt（ambient_tasks 已带出）则直接复用**（汇报注明「沿用行上 prompt」，用户明确要求换措辞才重写）；为空才由 LLM 从中文语义翻写为**英文**（AudioCaps 风格：声源+空间+氛围修饰，如「雨点骤然砸落」→ `Rain suddenly starts falling on a city street, rapidly growing heavier, raindrops hitting wet asphalt`），回填 jobs 后再跑 ①。**最终 prompt 随 §3 写图持久化到行节点**（`l.prompt`）——重产可复用、dashboard 可查看。

候选生成后**停下请用户试听**，满意 → finalize → 母带就位；不满意 → 调 prompt 措辞或换 `--seed` 重出（单候选迭代制，不并排出多个）。

### 3. 写图 + 汇报（产物落盘校验后才写）

```bash
# 校验：ls 母带文件存在且 >10KB，任一缺失停止不写图
python .claude/scripts/cypher_exec.py --stdin --multi <<'EOF'
MATCH (l:LineAudio {id:'<node_id>'}) SET l.ambient_track='<track>', l.attempts=coalesce(l.attempts,0)+1, l.status=10;
EOF
```

**bed 行另带 prompt 持久化**（AudioFly 链专用；sfx 行不写 prompt——Freesound 下载链的素材登记在 SOURCES.md）：

```bash
python .claude/scripts/cypher_exec.py --stdin --multi <<'EOF'
MATCH (l:LineAudio {id:'<node_id>'}) SET l.ambient_track='<track>', l.prompt='<英文prompt>', l.attempts=coalesce(l.attempts,0)+1, l.status=10;
EOF
```

不拷运行时副本——dashboard 逐句审批试听直接读母带 `15_声音/`，`99_game/assets/sfx/` 只由 chapter-publisher 发布时按 `status=11` 收录。

收尾：`rm -f '.tmp/ambient-jobs-<stem>-sec<MM>.json'`（候选 wav 保留至用户选定后由下一轮清理；prompt 已持久化到行节点，临时文件删除无损失）。

汇报：每行 track / 判型 / 通道来源 / status=10 + **bed 行附所用 prompt（标明沿用/新翻写）**，提示到 dashboard 审批中心逐句审（环境音行卡：🔊 徽章 + 母带试听 + prompt + 通过/驳回）；驳回 → status=0，重跑本 skill 只重做该行（prompt 沿用行上存量）。

## 重做

- **status=-1 级联**后重拆：ambient 行「track 在且母带 wav 在 → 恢复 10，否则 0」（script_splitter 恢复逻辑，音频复用不重产）。
- **text 变化**（stale）：置 0 重产，track 沿用覆盖母带——描述改了但行身份不变。
- 重做判定**只看 status，不看文件**；`-1` 必须重新生成覆盖，禁止读旧 prompt/旧 wav。

## 参考文档

- 行模型：[00_init/Schema/剧情.md](../../../00_init/Schema/剧情.md)（LineAudio op=transition/bed_start/bed_end / bed / ambient_track / status）
- track 解析与母带路径：[voice_bundler.py](../section-voice-publisher/scripts/voice_bundler.py)（split_voice_key / voice_master_path / make_ambient_track）
- AudioFly 环境（env/.venv-audiofly 重建）与能力边界：[demo/README.md](../../../demo/README.md)
- Freesound 素材登记：[15_声音/sfx_raw/SOURCES.md](../../../15_声音/sfx_raw/SOURCES.md)
