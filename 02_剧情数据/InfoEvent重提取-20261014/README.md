# Info/Event 全量清理 + 以 25_剧本 ink 为唯一事实重提取（2026-10-14）

旧 Info(26)/Event(64)/Choice(2) 源自 2026-09-13 的 `00_init/大纲.md` 提取（Day 0-30 全书规划层），与实际写成的 ink 剧本（chapter00+chapter01，覆盖 Day −1~10）已发散。本次清理后以 13 个 `台词.ink` 为**唯一事实**重提取：Event 30 / Info 31 / Choice 1。方法论沿用 `叙事基础重构迁移-20261013/` 先例。

**回滚锚点**：工作区根 `D:\project\ProxyLove\ProxyLove_backup_20261014_InfoEvent清理前.csv`（Dashboard /data 全量导出，可经快照导入恢复）。

**已确认决策**：① Choice 一并重提取（跳江选择重建、三选一弃）；② anchored_at 按场景块映射恢复（27 条）；③ wears 按场景块映射迁移（20 条）；④ 大纲元知识 Info 不入图（总表附录备查）。

**零级联（执行前实证）**：Info/Event/Choice 均无 status；相连边无任何 sync=true——删除不触发生产链 status 扰动。

## 执行顺序（全部在 Asset/ 目录内跑 cypher_exec）

```bash
cd Asset
# step0：回滚锚点（需 Dashboard 运行：cd Dashboard && run.bat；然后浏览器/curl 触发导出，见下）
#        curl -X POST http://127.0.0.1:8502/data/snapshot/save  （或 /data 页面手动导出）
#        导出文件改名/复制到工作区根：ProxyLove_backup_20261014_InfoEvent清理前.csv
# step1：清理（唯一不可逆操作，仅能靠 step0 快照重建）
python .claude/scripts/cypher_exec.py -f "02_剧情数据/InfoEvent重提取-20261014/step1_detach_delete.cypher" --multi
# step2：导入新事实（30 Event + 31 Info + 1 Choice + 204 条边）
python .claude/scripts/cypher_exec.py -f "02_剧情数据/InfoEvent重提取-20261014/import.cypher" --multi
# step3：恢复 anchored_at(27) 与 wears(20)
python .claude/scripts/cypher_exec.py -f "02_剧情数据/InfoEvent重提取-20261014/step3_restore_anchored_at_wears.cypher" --multi
# step4：校验（见下方清单，逐条跑，全部期望 0 / 对账值）
```

幂等性：step1 重跑 no-op（已删空）；step2/step3 全 MERGE，重跑不重复。

## step4 校验清单（全部期望 0）

```cypher
-- V1 无缺 occurs_at 的 Event
MATCH (e:Event) WHERE NOT (e)-[:occurs_at]->(:Location) RETURN count(e) AS c;
-- V2 每 Event occurs_at 恰 1 条
MATCH (e:Event) WITH e, count { (e)-[:occurs_at]->() } AS n WHERE n <> 1 RETURN count(e) AS c;
-- V3 time 格式全过
MATCH (e:Event) WHERE e.time IS NULL OR NOT e.time =~ '\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}' RETURN count(e) AS c;
-- V4 Info 必填字段非空
MATCH (i:Info) WHERE i.title IS NULL OR i.content IS NULL OR i.knowledge_level IS NULL RETURN count(i) AS c;
-- V5 无孤立 Info（有 link 或 leads_to）
MATCH (i:Info) WHERE NOT ()-[:link]->(i) AND NOT (i)-[:leads_to]->() AND NOT ()-[:leads_to]->(i) RETURN count(i) AS c;
-- V6 Choice option 全有落点且 BE 项标记正确
MATCH (c:Choice) WHERE NOT (c)-[:option]->(:Event) RETURN count(c) AS c;
MATCH (c:Choice)-[o:option]->(e:Event) WHERE e.ending_kind='BE' AND NOT coalesce(o.leads_to_ending,false) RETURN count(*) AS c;
-- V7 anchored_at 目标 Spot 均有 part_of
MATCH (e)-[:anchored_at]->(sp:Spot) WHERE NOT (sp)-[:part_of]->(:Location) RETURN count(*) AS c;
-- V8 新边无 sync=true
MATCH (n)-[r]-() WHERE (n:Info OR n:Event OR n:Choice) AND r.sync = true RETURN count(*) AS c;
-- V9 旧 id 残留清零（抽查旧 id 池）
MATCH (n) WHERE n.id IN ['NvCkQmFPGa','QP23NrFZrh','R1UsenvIau','NvCkQmFPFx','QP23NrFZqx','QP23NrFZrf','OdraDmqprU','QP23NrFZqn'] RETURN count(n) AS c;
```

对账区（期望值）：

```cypher
MATCH (e:Event) RETURN count(e) AS c;    -- 30
MATCH (i:Info) RETURN count(i) AS c;     -- 31
MATCH (c:Choice) RETURN count(c) AS c;   -- 1
MATCH ()-[r:involved]->() RETURN count(r) AS c;      -- 76
MATCH ()-[r:occurs_at]->() RETURN count(r) AS c;     -- 30
MATCH ()-[r:evt_relation]->() RETURN count(r) AS c;  -- 29
MATCH ()-[r:leads_to]->() RETURN count(r) AS c;      -- 9
MATCH ()-[r:link]->() RETURN count(r) AS c;          -- 57
MATCH ()-[r:presents]->() RETURN count(r) AS c;      -- 1
MATCH ()-[r:option]->() RETURN count(r) AS c;        -- 2
MATCH ()-[r:anchored_at]->() RETURN count(r) AS c;   -- 27
MATCH ()-[r:wears]->() RETURN count(r) AS c;         -- 20
-- scene 链恢复抽查（事件属于某场景）：
MATCH (e:Event)-[:anchored_at]->(sp:Spot)-[:realizes]->(s:Scene) RETURN count(DISTINCT e) AS c;  -- 27（新 Event 全部可溯至 Scene）
-- 出场角色推导链抽查（chapter-dialoguer 路径）：
MATCH (sec:Section)-[:contains]->(sc:Scene)<-[:realizes]-(sp:Spot)<-[:anchored_at]-(e:Event)<-[:involved]-(ch:Character) RETURN count(DISTINCT ch) AS c;  -- ≥ 8（陆择/陈默/陈念/林梦/苏晓禾/沈暮雪/江烈/Tony 等）
```

## 风险与回滚

- step1 删点是唯一不可逆操作——仅能靠 step0 CSV 快照重建（Dashboard `/data/snapshot/{file}/restore`，幂等 MERGE）。
- step2/step3 可逆向：`MATCH (n) WHERE n:Info OR n:Event OR n:Choice DETACH DELETE n` 后重放，或直接恢复快照。
- 清理→导入之间 Dashboard /events 页短暂空转（连续执行窗口极短）。
- 旧 wears 33 条中 13 条随大纲层 Event 丢弃（林梦后日谈/漫展等 ink 未写到的事件），CostumeStyle 节点本体不受影响。

## 执行记录（2026-10-14）

| 步骤 | 结果 |
|---|---|
| step0 | 快照 `Dashboard/data/snapshots/ProxyLove_backup_20261014_004428.csv`（935n/1566e）→ 工作区根 `ProxyLove_backup_20261014_InfoEvent清理前.csv`，验证含 64 Event + 26 Info |
| step1 | DETACH DELETE 完成：Info 26 / Event 64 / Choice 2 及 331 条相连边清零，复查 remaining=0 |
| step2 | import.cypher 266 条语句全部执行：Event 30 / Info 31 / Choice 1 + 边 involved 76 / occurs_at 30 / evt_relation 29 / leads_to 9 / link 57 / presents 1 / option 2 |
| step3 | anchored_at 恢复 27 + wears 迁移 20（共 47 条 MERGE） |
| step4 | V1~V9 全部 0；对账 12 项全部精确吻合（见上方对账区）；scene 链 27 Event 全部可溯至 Scene；出场角色推导链 11 角色/26 事件接通；抽查「陆择发现陈默的66666转账」（八楼出租屋，陆择/陈默/温蔓青）与 ink 原文一致 |
| 冒烟 | Dashboard /events 三轴查询正常；checkup 10 项对新数据体检合理（无孤立 Info、无断链；八楼出租屋 14 事件/6 角色为主枢纽，符合剧情） |
| 存档 | `csv/` 12 个文件（BOM，列格式沿用 01_叙事数据/csv），由图导出、计数与图一致 |
