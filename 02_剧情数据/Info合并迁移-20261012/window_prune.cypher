// window_prune.cypher — 剪枝窗口（单事务；2026-10-12）
// 前置：prune_dryrun.cypher 实测 41/1/4 并人工核对标题清单。
// 顺序有讲究：Choice 必须先于 Event 删除，否则 presents 边随事件消失会导致 Choice 漏删。
// 幂等性：谓词重跑时不再命中已删节点，安全。

// 1/3 删除由删除候选事件抛出的 Choice（三选一）
MATCH (e:Event)-[:presents]->(c:Choice)
WHERE NOT (e.time = '开场' OR (e.time STARTS WITH 'Day' AND toInteger(split(e.time, ' ')[1]) IS NOT NULL AND toInteger(split(e.time, ' ')[1]) <= 10))
DETACH DELETE c;

// 2/3 删除仅挂在删除候选事件上的 Info（B 组 4 个；Character/Location/保留事件挂载的不受影响）
MATCH (i:Info)
WHERE NOT EXISTS {
  MATCH (a)-[:link]->(i)
  WHERE a:Character OR a:Location
     OR (a:Event AND (a.time = '开场' OR (a.time STARTS WITH 'Day' AND toInteger(split(a.time, ' ')[1]) IS NOT NULL AND toInteger(split(a.time, ' ')[1]) <= 10)))
}
DETACH DELETE i;

// 3/3 删除 Event（Day 11~30 + 后日谈；DETACH DELETE 带走 involved/occurs_at/evt_relation/link/wears 中属于它们的边）
MATCH (e:Event)
WHERE NOT (e.time = '开场' OR (e.time STARTS WITH 'Day' AND toInteger(split(e.time, ' ')[1]) IS NOT NULL AND toInteger(split(e.time, ' ')[1]) <= 10))
DETACH DELETE e;
