---
name: tabletop-dialoguer
description: |
  跑团式节台词生成的入口（脚本驱动，2026-11-24 起原邮箱协议下线）：拉起工作区 Harness/tabletop-dialoguer/ 下的独立守护进程——裁判逻辑在代码里，角色出演与 DM 判定都是脚本发出的无状态 LLM 调用，状态全在 journal，任何一步崩溃都能断点续跑。本仓库里只有这一份入口说明，实现、配置、设计规则都在 Harness。
  节级创作链第一环（chapter-novelist 已软删 2026-11-20）：产出台词草稿 跑团草稿.md（拍头【场景：地点·时间｜block <scene_block_id>】行 + 头部取材指纹），落盘工作区 Harness/25_剧本/ch<NN>/sec<MM>/，交 chapter-dialoguer 打磨定稿；图写入仅一处 = 消费完毕置 Section.status 1→2。
  在需要为某 Section（status=1）产台词草稿、查看跑团进度、请求中止、或上线前自检时使用。
argument-hint: <section_id>
arguments:
  - section_id
allowed-tools: Read, Bash
---

# 跑团守护进程（tabletop-dialoguer）

> **不要自己演。** 跑团由脚本执行。本 skill 的职责只有三件：拉起命令、读它返回的 JSON、如实汇报。
> **实现不在本仓库。** 工具在工作区的 `Harness/tabletop-dialoguer/`，自成一体、不依赖本仓库。设计规则与判例见那边的
> `references/规则与判例.md`，配置与运维见 `references/运维.md`，给 agent 的完整说明见那边的 `SKILL.md`。

## 0. 入场与完成置位

- **入场**：`Section.status` 必须为 `1`（跑团待消费）。脚本自己校验，非 `1`（含 0 / 2 / 10 / 11 / -1）拒绝入场并如实报告，不改图。
- **完成**：草稿落盘后置 `status = 2` 并读回验证——这是工具唯一的图写入，由脚本执行，语句带 `WHERE s.status = 1`。
- **中途失败**：status 保持 `1`，下次运行从 journal 断点续跑。
- **重跑已消费节**：禁 `2→1`（用户裁决 2026-11-23）。先由用户置 `-1` 再置 `1` 重入管线。
- **定时消费入口**：Hermes 每日 00:30 的任务跑 `consume`，逐节串行消费全部 `status=1` 的节。

## 1. 怎么跑

```bash
# 入口脚本相对本仓库根：../Harness/tabletop-dialoguer/scripts/tabletop_runner.py（环境变量 TABLETOP_RUNNER 可覆盖）
R=python "${TABLETOP_RUNNER:-<本仓库根>/../Harness/tabletop-dialoguer/scripts/tabletop_runner.py}"

python $R consume                                   # 定时任务入口：全部 status=1 的节，派生守护进程后立即返回
python $R run --section <section_id>                # 单节：等最多 9 分钟，超时后守护进程继续在后台跑
python $R status [--section <section_id>]           # 进度；--wait-min N 等到出结果
python $R abort --section <section_id> | --all      # 请求在当前这一步之后停下
python $R doctor [--section <section_id>] [--ping]   # 上线前自检；--ping 另发一次最小请求验证端点、协议与 key
python $R materials --section <section_id> > <文件>.json   # 只输出该节的素材圈定（Q5）JSON 数组，给 chapter-dialoguer 的指纹自检当 --in；零 LLM 调用、不写图
```

- **配置**：工具读 Harness 根的 `settings.json`（与 Asset、Dashboard 各自在仓库根放一份的惯例一致；`--settings <路径>` / 环境变量 `TABLETOP_SETTINGS` 可以另指一份）。草稿默认写 Harness 根下的 `25_剧本/`，不用配（`tabletop.draft_root` 可改）。
- stdout 只有一个 JSON 对象，原样转述即可；人读日志在工具状态仓的 `daemon.log`。
- 退出码：0 完成 / 2 用法或配置 / 3 图库不可达 / 4 已有守护进程在跑 / 5 拒绝入场·阻断缺口·门禁失败 / 6 中止 / 7 预算用尽。
- 同一时刻只有一个守护进程。拿到退出码 4 时不要重试拉起，改用 `status` 汇报进度。
- 彩排可以加 `--max-events N` 只排前 N 个事件（正式模式没有这个开关）。结果的 `detail` 与草稿标题会写明不是整节，转述时别当成整节草稿。

## 2. 读结果

| 出口 | 含义 | 该做什么 |
|---|---|---|
| `published` | 草稿已落盘，status 已置 2 | 汇报路径，交 chapter-dialoguer |
| `gap_blocked` | 结构缺口：事件无 sub、拍无机位、在场为空、角色名非法 | 汇报 `gaps.blocking`，指向设计端（event-stager）。全程不花 LLM 调用 |
| `gate_blocked` | 指纹邻检门禁违规且策略为 `fail` | 汇报 `gate` 明细 |
| `budget_exhausted` | 调用数或墙钟到上限 | 不用管，下次 `consume` 自动续跑 |
| `aborted` | 见 `reason` | 模型侧原因（鉴权、配置、限流、格式）修好配置即可，下次自动续跑 |
| `refused_status` | 入场时 status ≠ 1 | 汇报，不改图 |
| `rehearsed` / `dry_run` | 彩排 / 干跑 | 读工具状态仓里的产物 |

`gaps.non_blocking` 是上报但照常演的缺口（拍点披露的目标听者无认知链、当事人自我事实无链等），已写进草稿附录，一并转述。

## 3. 行为准则

- **不等待过久**：agent 工具单次调用有超时上限。`run` 默认只等 9 分钟；返回时 `running` 仍为真就汇报「跑团后台进行中」并退出，下次再推进。需要跟进度用 `status --wait-min 9`。
- **不手工介入演出**：不手改工具状态仓里的 journal、场景帧或调用留档，不替脚本拼 prompt。要调措辞改工具的 `prompts/*.md`，要调上限改它的配置 `tabletop` 节。
- **缺口不现场补**：图料不足一律报缺口（设计端补 Cognition / 机位 / 拆 sub），不在跑团侧打补丁。错误前移到设计期是设计意图。
- **自由发挥**：角色跳过某条事实项或即兴换了演法是正常的，不算故障（用户裁决 2026-11-25）。不希望某件事被演出来，由图数据显式声明。
- **素材变动**：续跑前与置位前各比对一次图快照，变了就重开。`stale_at_publish` 属正常出口，重跑即可。
- **`status=2` 之后**：草稿交 chapter-dialoguer 打磨。本 skill 不连推。

## 4. 与本仓库的三处约定

- **草稿路径**：工作区 `Harness/25_剧本/ch<NN>/sec<MM>/跑团草稿.md`（产出物归 Harness）。存量小说.md 的副本也在那棵树下，指纹的新鲜度只扫它；`台词.ink` 不在那里，仍由 chapter-dialoguer 写在本仓库的 `25_剧本/`。拍头 `【场景：…｜block <scene_block_id>】` 行是拓扑契约，文末内部附录由 chapter-dialoguer 剥离。
- **取材指纹同源**：本仓库的 `.claude/scripts/fingerprint.py` 与工具里的 `scripts/fingerprint.py` 是同一份代码的两份拷贝，**必须保持字节一致**——改了任何一边都要同步另一边。
- **状态仓不在本仓库**：在 `Harness/tabletop-dialoguer/.tmp/tabletop/`。本仓库的 `.tmp/` 里没有跑团的东西。
