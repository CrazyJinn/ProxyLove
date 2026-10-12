// verify_post.cypher — 窗口后只读验收（2026-10-12）
// 基线：开窗前 950 节点；剪枝删 46（Event 41 + Info 4 + Choice 1）→ 904。

MATCH (n) RETURN '全库节点(期望904=950-46)' AS chk, count(n) AS v;
MATCH (n:Info) RETURN 'Info总数(期望46)' AS chk, count(n) AS v;
MATCH (n:Info:Event) RETURN 'Event形态(期望23)' AS chk, count(n) AS v;
MATCH (n:Info:Choice) RETURN 'Choice形态(期望1)' AS chk, count(n) AS v;
MATCH (n:Info) WHERE NOT n:Event AND NOT n:Choice RETURN '纯Info(期望22)' AS chk, count(n) AS v;
MATCH (n:Event) WHERE NOT n:Info RETURN '漏打Info的Event(期望0)' AS chk, count(n) AS v;
MATCH (n:Choice) WHERE NOT n:Info RETURN '漏打Info的Choice(期望0)' AS chk, count(n) AS v;
MATCH (n:Choice) WHERE n.name IS NOT NULL RETURN '残留name(期望0)' AS chk, count(n) AS v;

// 边计数（期望值 = 2026-10-12 dry-run 实测：各边总数 - willLose）
MATCH ()-[r:link]->() RETURN 'link(期望24=28-4)' AS chk, count(r) AS v;
MATCH ()-[r:presents]->() RETURN 'presents(期望1=2-1)' AS chk, count(r) AS v;
MATCH ()-[r:option]->() RETURN 'option(期望2=5-3)' AS chk, count(r) AS v;
MATCH ()-[r:evt_relation]->() RETURN 'evt_relation(期望22=62-40)' AS chk, count(r) AS v;
MATCH ()-[r:involved]->() RETURN 'involved(期望39=125-86)' AS chk, count(r) AS v;
MATCH ()-[r:occurs_at]->() RETURN 'occurs_at(期望22=47-25)' AS chk, count(r) AS v;
MATCH ()-[r:wears]->() RETURN 'wears(期望19=33-14)' AS chk, count(r) AS v;

// 形态抽样
MATCH (c:Choice) RETURN c.id AS id, c.title AS title, labels(c) AS labels;
MATCH (e:Event {title:'沈暮雪邀约二队'}) RETURN e.id AS id, e.time AS time, labels(e) AS labels;
MATCH (e:Event {title:'陆择酒店醒来'}) RETURN e.id AS id, e.time AS time, labels(e) AS labels;
