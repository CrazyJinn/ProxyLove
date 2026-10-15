// ═══ Day 21 三选一核心选择增补 2026-10-16 ═══
// 用户口述规划节点（非 ink 提取）：锚点+21天=2024-06-22 22:00:00，三女主同时来信，陈默/陆择三选一
// 结构：E31 触发事件 -presents-> Choice 三选一 -option-> E32/E33/E34 支线入口
// 三女主=林梦/苏晓禾/沈暮雪；involved 遵守穿越后规则（不挂陆择）；occurs_at 按 Schema 不变式挂常驻地八楼出租屋（规划期推定）
// 执行：python .claude/scripts/cypher_exec.py -f <本文件> --multi

// ── 1. Event 节点 ×4 ──
UNWIND [
  {id:'RGj3o4sKsC', title:'三女主同时发来信息', time:'2024-06-22 22:00:00', type:'交流', description:'规划节点（用户口述增补，非 ink 提取）：Day 21 深夜，林梦/苏晓禾/沈暮雪三人同时给陈默发来信息；地点按常驻地推定八楼出租屋'},
  {id:'RGj3o4sKsE', title:'陈默选择林梦确立恋爱关系进入林梦支线', time:'2024-06-22 22:00:00', type:'状态变化', description:'规划节点：三选一之林梦线——确立恋爱关系，进入林梦支线（互斥分支，仅选林梦时成立）'},
  {id:'RGj3o4sKsF', title:'陈默选择苏晓禾确立恋爱关系进入苏晓禾支线', time:'2024-06-22 22:00:00', type:'状态变化', description:'规划节点：三选一之苏晓禾线——确立恋爱关系，进入苏晓禾支线（互斥分支，仅选苏晓禾时成立）'},
  {id:'RGj3o4sKsG', title:'陈默选择沈暮雪确立恋爱关系进入沈暮雪支线', time:'2024-06-22 22:00:00', type:'状态变化', description:'规划节点：三选一之沈暮雪线——确立恋爱关系，进入沈暮雪支线（互斥分支，仅选沈暮雪时成立）'}
] AS row MERGE (e:Event {id:row.id}) SET e = row;

// ── 2. Choice 节点 ×1 ──
MERGE (ch:Choice {id:'RGj3o4sKsD'})
SET ch.name = '三选一', ch.description = 'Day 21 深夜三女主同时来信，陈默（陆择）择一回应——选择谁谁成为女朋友，进入对应女主支线（第一试炼核心抉择，选项互斥）', ch.time = '2024-06-22 22:00:00';

// ── 3. involved ×10（E31 四人 + 三个支线入口各 2 人；陆择不挂）──
UNWIND [
  {e:'RGj3o4sKsC', c:'陈默', r:'当事人'}, {e:'RGj3o4sKsC', c:'林梦', r:'发信人'}, {e:'RGj3o4sKsC', c:'苏晓禾', r:'发信人'}, {e:'RGj3o4sKsC', c:'沈暮雪', r:'发信人'},
  {e:'RGj3o4sKsE', c:'陈默', r:'当事人'}, {e:'RGj3o4sKsE', c:'林梦', r:'当事人'},
  {e:'RGj3o4sKsF', c:'陈默', r:'当事人'}, {e:'RGj3o4sKsF', c:'苏晓禾', r:'当事人'},
  {e:'RGj3o4sKsG', c:'陈默', r:'当事人'}, {e:'RGj3o4sKsG', c:'沈暮雪', r:'当事人'}
] AS row
MATCH (ev:Event {id:row.e}) MATCH (c:Character {name:row.c})
MERGE (c)-[:involved {role:row.r}]->(ev);

// ── 4. occurs_at ×4（规划期按常驻地推定）──
UNWIND [
  {e:'RGj3o4sKsC'}, {e:'RGj3o4sKsE'}, {e:'RGj3o4sKsF'}, {e:'RGj3o4sKsG'}
] AS row
MATCH (ev:Event {id:row.e}) MATCH (l:Location {name:'八楼出租屋'})
MERGE (ev)-[:occurs_at]->(l);

// ── 5. evt_relation{先后}：E30 主线延续 → E31 ──
MATCH (x:Event {id:'RGcLQijx3V'}) MATCH (y:Event {id:'RGj3o4sKsC'})
MERGE (x)-[:evt_relation {type:'先后'}]->(y);

// ── 6. presents + option ×3（互斥分支入口，非结局不设 leads_to_ending）──
MATCH (e31:Event {id:'RGj3o4sKsC'}) MATCH (ch:Choice {id:'RGj3o4sKsD'})
MERGE (e31)-[:presents]->(ch);
MATCH (ch:Choice {id:'RGj3o4sKsD'}) MATCH (e:Event {id:'RGj3o4sKsE'})
MERGE (ch)-[:option {label:'选林梦'}]->(e);
MATCH (ch:Choice {id:'RGj3o4sKsD'}) MATCH (e:Event {id:'RGj3o4sKsF'})
MERGE (ch)-[:option {label:'选苏晓禾'}]->(e);
MATCH (ch:Choice {id:'RGj3o4sKsD'}) MATCH (e:Event {id:'RGj3o4sKsG'})
MERGE (ch)-[:option {label:'选沈暮雪'}]->(e);
