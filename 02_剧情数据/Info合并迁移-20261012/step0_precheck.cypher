// step0_precheck.cypher — 开窗前只读预检（2026-10-12 Info 合并迁移）
// P1 每 label 重复 id：必须返回 0 行（21 个唯一约束的前置条件）
MATCH (n) UNWIND labels(n) AS lb
WITH lb, n.id AS id, count(*) AS cnt WHERE cnt > 1 RETURN lb, id, cnt;

// P2 Choice 属性现状（确认：跳江选择有 name 无 title；三选一同）
MATCH (c:Choice) RETURN c.id AS id, c.name AS name, c.title AS title;

// P3 Event title 完备性（title 是合并后唯一显示名字段）
MATCH (e:Event) WHERE e.title IS NULL RETURN e.id AS id, e.title AS title;

// P4 基线计数（期望 Event 64 / Info 26 / Choice 2 / 全库 950）
MATCH (e:Event) RETURN 'Event' AS kind, count(*) AS n;
MATCH (i:Info) RETURN 'Info' AS kind, count(*) AS n;
MATCH (c:Choice) RETURN 'Choice' AS kind, count(*) AS n;
MATCH (n) RETURN 'ALL' AS kind, count(*) AS n;
