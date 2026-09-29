# 55_dashboard/CLAUDE.md

本文件为 Claude Code 提供本子项目（人工治理后台）的工作指南。

## 这是什么

**FastAPI + Jinja2 + uvicorn 治理后台**（http://localhost:8502），与 skills 共享同一个 Neo4j：浏览生产链状态、审批（10→11）、Cypher 控制台、CSV 快照导入/导出、ECharts 生产看板与叙事图浏览。原 Streamlit 版已移除（git 历史可溯）。

## 架构（三层，扁平）

```
app/main.py          ← 唯一入口：全部 FastAPI 路由（无 router 拆分）
app/services/*       ← 业务逻辑（status/cascade/board/queries/hints/ink/exporter/audit/artifacts/node_fields/snapshot_importer）
app/repo/graph_repo.py ← 图访问层（连接 + 参数化查询封装）
app/templates/*.html ← Jinja2 页面；app/static/ ← echarts.min.js（本地）/char_edit.js/mindmap.js/style.css
```

- **`app/services/status.py` 的 `NODE_STATUS` 是 status 白名单权威**：`-1` 作废重做 / `0` 待处理 / `1` 已完成 / `2` 图片完成 / `10` 待审 / `11` 批准（根 CLAUDE.md、cypher_exec.py 均指向此处）。
- **`app/services/cascade.py` 是 sync 级联权威**：写语句执行后沿 `sync=true` 出边 BFS 把可达下游置 `-1`。**审批动作（approve/reject/resubmit）不触发级联**；级联只由 Cypher 控制台与节点编辑确认卡触发。
- **`app/services/node_fields.py` 硬编码各标签字段中文名**（抄自 `00_init/Schema/*.md`，无自动加载）——**改 Schema 字段中文名时须手工同步此文件**。Schema .md 仍是 skills 侧的权威。
- **产物文件**（图片/音频/ink/md）经 `app/services/artifacts.py` 解析：按 settings.json 的 `artifact_roots`（当前 `[".."]` = 项目根）逐根找 `rel_path`，media 路由 `/media/{kind}/{rel}` 供页面展示；目录穿越由 `Path.is_relative_to` 守卫（跨平台）。

## 配置：settings.json（本目录内，已 gitignore）

唯一配置文件 `55_dashboard/settings.json`（**不向上搜索项目根**）。凭证优先级：环境变量 `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` > 本文件。

```json
{
  "neo4j_uri": "bolt://127.0.0.1:7687",
  "neo4j_user": "neo4j",
  "neo4j_password": "…",
  "artifact_roots": [".."],
  "csv_snapshot": "",
  "port": 8502,
  "webhook_url": "",
  "webhook_secret": ""
}
```

⚠ **`neo4j_password` 与项目根 `settings.json` 的 `neo4j_password` 是双份**——Neo4j 改密时两处都要改。`webhook_url`/`webhook_secret` 留空即禁用 /agent 触发（hermes gateway，本项目默认不部署）。

## 常用命令

```bash
bash 55_dashboard/run.sh        # 或 Windows 双击 run.bat；uv 优先，pip 兜底自装依赖
cd 55_dashboard && uv run pytest   # 3 个测试文件（纯逻辑，不连真实库；真实快照用例自动 skip）
```

启动需 cwd = 55_dashboard（`python -m uvicorn app.main:app --port 8502`）。

## 路由地图

| 页面 | 路由 | 说明 |
|---|---|---|
| 总览 | `/` | 全链 status 计数 |
| 审批中心 | `/approvals` + `/approvals/{script,voice,chapter,image,section}/{id}` | 各类待审；decision：approve(10→11) / reject(→0+attempts+1) / resubmit(0/1/11→10) / adopt(VoiceDesign 候选采用) |
| 逐句音频审 | `/approvals/section/{sec_id}`、`/approvals/line/{id}/decision` | 读 `15_声音/` 母带试听 |
| 生产看板 | `/board`（char/scene/plot 三 tab）、`/board/char/{id}` | ECharts 链图；节点属性卡 `/board/node/{id}/props`；内联审批 `/board/node/{id}/review` |
| 叙事图浏览 | `/graph`、`/graph/{label}/{id}` | 全图/节点详情 |
| 数据与设置 | `/data` | CSV 导出/导入（白名单限仓库内）、**Cypher 控制台**（写语句两段确认 + 级联预览）、BgmTrack 归档检测 `/bgm/{id}/check` |
| agent 触发 | `/agent` | 需 webhook 配置，默认禁用 |

审计流水追加写 `data/audit.jsonl`（已 gitignore）。

## 与 skills 的协作契约

- 审批/驳回/resubmit 的 status 语义必须与 `app/services/status.py` 一致；skills 侧文档（`.claude/agents/*`、`SKILL.md`）多处引用。
- 角色美术链展示子图 = `app/services/board.py` 的 `char_art_graph`（`has_appearance|has_costume|has_voice_style|has_voice_design|produces|outfit_for|expands_to`，**不含 `ref_style`**）；skill 侧 8 边正则以 `.claude/agents/char-design.md` 为准。
- 推进指令在 `/`、`/board` 的 hints 区（`app/services/hints.py`）生成**复制粘贴文本**（如「请运行 plot-design 编排（单节聚焦）：section_id=…」）——手动粘贴进 Claude Code 会话（原 Streamlit 版的 vscode deeplink 已移除）。

## 与旧版（Streamlit）的能力差异

缺失（人工流程替代）：叙事审批页（`02_剧情数据/*_建议.json` 写回 → 改用 /data Cypher 控制台逐条执行，无 `_reviewed.json` 去重，靠建议 cypher 本身 MERGE 幂等）；台词在线编辑器（直接外部编辑 `25_剧本/.../台词.ink` 后用 script_review 的「重新提交审批」）；Schema 驱动表单/标签库；VoiceDesign adopt 不再 move/清理 `14_声音设计/` 候选文件（人工清理）；环境音批准不再自动删 `15_声音/sfx_raw/` 素材（人工按 SOURCES.md 清理）。

新增：Cypher 控制台、CSV 快照导入/导出、ECharts 看板/叙事图浏览、BgmTrack 归档检测、/agent 触发页。

## ⚠ 严禁运行 `scripts/gen_mock_artifacts.py`

它是上游 dailian-dashboard 仓库的开发工具，会在**项目根生成 mock 产物树**（假图/假 wav）污染真实产物目录。仅随仓库保留，不要在本项目执行。
