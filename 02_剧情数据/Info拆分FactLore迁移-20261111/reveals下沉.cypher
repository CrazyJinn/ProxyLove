// reveals 下沉迁移：Event ─reveals→ Fact ⇒ SubEvent ─reveals→ Fact（2026-11-11 拍板）
// ① 多 sub 的 6 条按用户逐条拍板挂指定 sub
MATCH (s:SubEvent {id:'RdzkJhNplw'}), (f:Fact {id:'RxhLwLmgno'}) MERGE (s)-[:reveals]->(f);
MATCH (s:SubEvent {id:'RdzkJhNplw'}), (f:Fact {id:'RxhLwLmgnn'}) MERGE (s)-[:reveals]->(f);
MATCH (s:SubEvent {id:'RdzkJhNplx'}), (f:Fact {id:'RxhLwLmgnt'}) MERGE (s)-[:reveals]->(f);
MATCH (s:SubEvent {id:'Ra7IfJLJtG'}), (f:Fact {id:'RxhLwLmgo7'}) MERGE (s)-[:reveals]->(f);
MATCH (s:SubEvent {id:'RlkWwdjD8c'}), (f:Fact {id:'RxhLwLmgnr'}) MERGE (s)-[:reveals]->(f);
MATCH (s:SubEvent {id:'RxoSkCPyio'}), (f:Fact {id:'RxhLwLmgoA'}) MERGE (s)-[:reveals]->(f);
// ② 单 sub 的边机械下沉（源事件恰 1 sub：边搬到 sub）
MATCH (e:Event)-[r:reveals]->(f:Fact)
MATCH (e)-[:refines]->(sub:SubEvent)
WITH e, f, count(sub) AS n
WHERE n = 1
MATCH (e)-[:refines]->(s2:SubEvent), (f2:Fact {id: f.id})
MERGE (s2)-[:reveals]->(f2)
WITH DISTINCT e, f
MATCH (e)-[old:reveals]->(f) DELETE old;
// ③ 悬空 2 条（咖啡店深夜谈心未拆 sub）：删边，stager 细化时经 S3 重新拍
MATCH (e:Event)-[r:reveals]->(f:Fact) WHERE NOT (e)-[:refines]->() DELETE r;
// ④ 兜底：清残留 Event 级 reveals（多 sub 事件已挂 sub，旧边删）
MATCH (e:Event)-[r:reveals]->(f:Fact) DELETE r;
