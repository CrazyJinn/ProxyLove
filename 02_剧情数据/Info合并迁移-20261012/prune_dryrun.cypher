// prune_dryrun.cypher — 剪枝只读闸门（2026-10-12）
// 保留谓词：e.time = '开场' OR (Day N 且 N <= 10)。开窗条件：D1=41 行 / D2=1 行 / D3=4 行。

// D1 待删 Event（期望 41 行：Day 11~30 的 38 + 后日谈 3；标题清单与 README 核对）
MATCH (e:Event)
WHERE NOT (e.time = '开场' OR (e.time STARTS WITH 'Day' AND toInteger(split(e.time, ' ')[1]) IS NOT NULL AND toInteger(split(e.time, ' ')[1]) <= 10))
RETURN e.id AS id, e.time AS time, e.title AS title ORDER BY time;

// D2 待删 Choice（期望 1 行：三选一；先于事件删除评估，实际删除也须先于 Event）
MATCH (e:Event)-[:presents]->(c:Choice)
WHERE NOT (e.time = '开场' OR (e.time STARTS WITH 'Day' AND toInteger(split(e.time, ' ')[1]) IS NOT NULL AND toInteger(split(e.time, ' ')[1]) <= 10))
RETURN c.id AS id, c.name AS name;

// D3 待删 Info（期望 4 行：拯救的定义/试炼好处/林梦漫展做局/三选一机制——仅挂在被删事件上）
MATCH (i:Info)
WHERE NOT EXISTS {
  MATCH (a)-[:link]->(i)
  WHERE a:Character OR a:Location
     OR (a:Event AND (a.time = '开场' OR (a.time STARTS WITH 'Day' AND toInteger(split(a.time, ' ')[1]) IS NOT NULL AND toInteger(split(a.time, ' ')[1]) <= 10)))
}
RETURN i.id AS id, i.title AS title;

// D4 保留事件的出边余量（写入 README 执行记录，作为 verify_post 期望值）
MATCH (e:Event)-[r]->()
WHERE e.time = '开场' OR (e.time STARTS WITH 'Day' AND toInteger(split(e.time, ' ')[1]) IS NOT NULL AND toInteger(split(e.time, ' ')[1]) <= 10)
RETURN type(r) AS rel, count(*) AS remain ORDER BY rel;
