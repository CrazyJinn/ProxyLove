// Info→Fact/Lore 拆分迁移（2026-11-11 方案 §7）
// 前置已核：establishes 31 = Event 23 + Character 8 + Location 0，每 Info 恰一源；reveals 30 = 指 Fact 候选 22 + Lore 候选 8
// 预期结果：Fact 23 / Lore 8 / Info 0；establishes 23（全 Event→Fact）；has_info 8；reveals 22
MATCH (e:Event)-[:establishes]->(i:Info) SET i:Fact REMOVE i:Info;
MATCH (c:Character)-[r:establishes]->(i:Info) SET i:Lore REMOVE i:Info CREATE (c)-[:has_info]->(i) DELETE r;
MATCH (l:Location)-[r:establishes]->(i:Info) SET i:Lore REMOVE i:Info CREATE (l)-[:has_info]->(i) DELETE r;
MATCH (e:Event)-[r:reveals]->(l:Lore) DELETE r;
