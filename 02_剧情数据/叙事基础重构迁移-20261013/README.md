# 叙事基础重构迁移（2026-10-13）

Schema 重构（occurs_at 直挂 Location / anchored_at 归组 / leads_to 统一因果 / 时间锚点 datetime）的图数据迁移。
参照 `Info合并迁移-20261012/` 先例：幂等脚本 + 本 README 执行记录。

**回滚锚点**：工作区根 `D:\project\ProxyLove\ProxyLove_backup_20261013_叙事基础重构前.csv`（952 节点 / 1554 边，Dashboard /data 导出格式，可经快照导入恢复）。

## 基线（迁移前实测，2026-10-13）

| 指标 | 值 |
|---|---|
| occurs_at 总数（全挂 Spot） | 47（default 目标 18 / zone 目标 29） |
| Spot | 19 default + 15 zone（全部有 part_of，34 条） |
| realizes | 19 |
| evt_relation | 62（先后 54 / 因果 5 / **type 空 3** ← 数据缺口，本次不修仅记录） |
| link | 28（涉及 27 / 因果 1：Info→Info） |
| Event | 64，time 全为 `Day N`/`Day N 时段`/`开场`×5/`后日谈`×3，无绝对日期 |
| 死 default Spot（无 realizes ∧ 无 dsl_path） | 17 |

## 执行顺序（全部在 Asset/ 目录内跑 cypher_exec）

```bash
cd Asset
# step1：occurs_at 上卷/拆分（default→Location；zone→Location+anchored_at），删旧边、清 anchor 属性
python .claude/scripts/cypher_exec.py -f "02_剧情数据/叙事基础重构迁移-20261013/step1_occurs_at_to_location.cypher" --multi
# step2：删死 default Spot（须在 step1 后：anchored_at 条件才可靠）
python .claude/scripts/cypher_exec.py -f "02_剧情数据/叙事基础重构迁移-20261013/step2_delete_dead_default_spots.cypher" --multi
# step3：因果边迁移（evt_relation{因果} 5 条 + link{因果} 1 条 → leads_to）
python .claude/scripts/cypher_exec.py -f "02_剧情数据/叙事基础重构迁移-20261013/step3_leads_to.cypher" --multi
# step4：时间换算（先生成、人工过目、再执行）
python "02_剧情数据/叙事基础重构迁移-20261013/step4_time_gen.py" --anchor '<锚点 yyyy-MM-dd HH:mm:ss>'
python .claude/scripts/cypher_exec.py -f "02_剧情数据/叙事基础重构迁移-20261013/step4_time_sets.cypher" --multi
# step5：校验（见下方清单，逐条跑，全部期望 0 / 对账值）
```

幂等性：step1/2/3 重跑无匹配即 no-op；step4 重放同值。

## step5 校验清单（全部期望 0，除对账区）

```cypher
-- V1 无缺 occurs_at 的 Event
MATCH (e:Event) WHERE NOT (e)-[:occurs_at]->(:Location) RETURN count(e) AS c;
-- V2 Event→Spot 旧边清零
MATCH (e:Event)-[:occurs_at]->(:Spot) RETURN count(*) AS c;
-- V3 因果残留清零（两条均应为 0）
MATCH ()-[r:evt_relation]->() WHERE r.type='因果' RETURN count(*) AS c;
MATCH ()-[r:link]->() WHERE r.type='因果' RETURN count(*) AS c;
-- V4 时间格式全过（Event+Choice；边时间另查）
MATCH (n) WHERE (n:Event OR n:Choice) AND n.time IS NOT NULL AND NOT n.time =~ '\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}' RETURN count(n) AS c;
MATCH ()-[r:link]->() WHERE r.time IS NOT NULL AND NOT r.time =~ '\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}' RETURN count(*) AS c;
MATCH ()-[r:relation|at]->() WHERE (r.start_time IS NOT NULL OR r.end_time IS NOT NULL) AND (coalesce(r.start_time,'') <> '' AND NOT r.start_time =~ '\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}' OR coalesce(r.end_time,'') <> '' AND NOT r.end_time =~ '\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}') RETURN count(*) AS c;
-- V5 无缺 part_of 的 Spot
MATCH (sp:Spot) WHERE NOT (sp)-[:part_of]->(:Location) RETURN count(sp) AS c;
-- V6 死 Spot 清零（default 与 zone 各查）
MATCH (sp:Spot) WHERE NOT (sp)-[:realizes]->() AND coalesce(sp.dsl_path,'')='' AND NOT ()-[:anchored_at]->(sp) RETURN count(sp) AS c;
-- V7 anchored_at 目标均有 part_of
MATCH (e)-[:anchored_at]->(sp:Spot) WHERE NOT (sp)-[:part_of]->(:Location) RETURN count(*) AS c;
-- V8 每 Event occurs_at 恰 1 条
MATCH (e:Event) WITH e, count { (e)-[:occurs_at]->() } AS n WHERE n <> 1 RETURN count(e) AS c;
-- V9 无 Info 作 link 源的反向边
MATCH (i:Info)-[:link]->(:Event) RETURN count(*) AS c;
```

对账区（期望值）：

```cypher
MATCH ()-[r:occurs_at]->() RETURN count(r) AS c;    -- 47
MATCH ()-[r:anchored_at]->() RETURN count(r) AS c;  -- 29（= 迁移前 zone 目标数）
MATCH ()-[r:leads_to]->() RETURN count(r) AS c;     -- 6（= 5 evt_relation因果 + 1 link因果）
MATCH ()-[r:evt_relation]->() RETURN count(r) AS c; -- 57（= 62 − 5）
MATCH (sp:Spot) RETURN count(sp) AS c;              -- 17（= 19 default − 17 死删 + 15 zone）
MATCH (i:Info) RETURN count(i) AS c;                -- 迁移前值不变（删点只删 Spot）
```

## 风险与回滚

- step2 删点是唯一不可逆操作（17 个死 default Spot，删除条件三重：无 realizes ∧ 无 dsl_path ∧ 无 anchored_at 入边）——仅能靠 CSV 快照重建。
- step1/3 边迁移可由 anchored_at+part_of / detail+端点反推重建。
- step4 的 `step4_time_sets.cypher` 内联注释即 old→new 逆向映射，可重放还原。

## 执行记录（2026-10-13）

| 步骤 | 结果 |
|---|---|
| step1 | occurs_at 47 全部上卷/拆分：default 18 → Location；zone 29 → Location + anchored_at；旧边清零；anchor 属性清零 |
| step2 | 删死 default Spot 17（34→17：留 2 default + 15 zone）；同条件死 zone = 0（无需复核） |
| step3 | leads_to = 6（evt_relation{因果} 5 + link{因果} 1）；evt_relation 62→57；因果残留 0 |
| step4 | 锚点 `2024-06-01 22:00:00`；73 条 SET（64 Event + Choice/边时间）；复核清单 0 条；换算后范围 2024-05-31（开场）~ 2024-07-02（后日谈）；格式校验 bad=0 |
| step5 | V2/V3/V4/V5/V6/V7/V9 全 0；对账 occurs_at=47、anchored_at=29、leads_to=6、evt_relation=57、Spot=17、总边数 1566（=1554+29 拆分净增−17 死 Spot part_of）——全部精确 |

**V1/V8 = 17 的说明**：64 Event − 47 occurs_at = 17 个**存量 E1 缺口**（迁移前即无定位，Dashboard 孤儿区原有待办，非本次引入）。含锚点事件「陈默跳江陆择灵魂挤入」（Day 0 深夜）与两个后日谈。处置：留给 nrt-gap-filler E1 流程补挂（时间已同步换算为 datetime）。

## step6 — SceneLayer 历史路径错位修复（追加，2026-10-13）

**与本次迁移无关**（迁移前后快照中 image_path/prompt_path 逐字一致）——用户报告「图片未挂载」后发现的存量错位：全部 15 个 SceneLayer 的路径缺物理目录层（图 `07_场景美术/<Location>/<Scene名>/…` vs 磁盘 `07_场景美术/<Location>/<物理目录>/<Scene名>/…`；八楼出租屋的物理目录为收拢名 卧室/门厅）。修复：`step6_fix_layer_paths.cypher` 按 Scene 名逐条赋完整正确路径（image_path + prompt_path 共 30 条），执行后逐条校验文件实存全过。注：首版 step6 用 replace 前缀替换误吞 Scene 段，已即时重写为全值赋值版修复。

**回滚方式**：工作区根 `ProxyLove_backup_20261013_叙事基础重构前.csv` 经 Dashboard /data 快照导入恢复；step4 可由 `step4_time_sets.cypher` 注释逆向重放。
