// 4 条 Fact → Lore 重分类（2026-11-11 用户拍板：固有设定非事件产物）
// 苏晓禾条目按拍板改写描述（人设归 Lore，事件反应留在 Event.description）
MATCH (n {id:'RxhLwLmgo3'}) SET n.title='苏晓禾对照顾的人投入真感情', n.content='「照顾别人」不是工作而是情感寄托；亲近之人离世会击中软肋';
MATCH (n {id:'RxhLwLmgnw'}) SET n:Lore REMOVE n:Fact;
MATCH (n {id:'RxhLwLmgnz'}) SET n:Lore REMOVE n:Fact;
MATCH (n {id:'RxhLwLmgnp'}) SET n:Lore REMOVE n:Fact;
MATCH (n {id:'RxhLwLmgo3'}) SET n:Lore REMOVE n:Fact;
MATCH (c:Character {id:'NvCkQmFPFt'}) MATCH (l:Lore {id:'RxhLwLmgnw'}) MERGE (c)-[:has_info]->(l);
MATCH (c:Character {id:'NvCkQmFPFu'}) MATCH (l:Lore {id:'RxhLwLmgnz'}) MERGE (c)-[:has_info]->(l);
MATCH (c:Character {id:'NvCkQmFPFq'}) MATCH (l:Lore {id:'RxhLwLmgnp'}) MERGE (c)-[:has_info]->(l);
MATCH (c:Character {id:'NvCkQmFPFs'}) MATCH (l:Lore {id:'RxhLwLmgo3'}) MERGE (c)-[:has_info]->(l);
MATCH ()-[r:establishes]->(l:Lore) DELETE r;
MATCH ()-[r:reveals]->(l:Lore) DELETE r;
