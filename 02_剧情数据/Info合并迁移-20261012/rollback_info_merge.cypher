// rollback_info_merge.cypher — 仅撤销 label 合并（幂等；2026-10-12）
// 注意：剪枝（window_prune）不可逆，误删只能靠窗口前 CSV 快照整库恢复；
//       快照恢复后需重跑 window_info_merge.cypher 补附加 label。
// 约束回滚：按需逐条 DROP CONSTRAINT <name> IF EXISTS（名称见 step2_constraints.sh），须在事务外单条执行。

MATCH (e:Event) WHERE e:Info REMOVE e:Info;
MATCH (c:Choice) WHERE c:Info REMOVE c:Info;
MATCH (c:Choice) WHERE c.name IS NULL AND c.title IS NOT NULL SET c.name = c.title REMOVE c.title;
