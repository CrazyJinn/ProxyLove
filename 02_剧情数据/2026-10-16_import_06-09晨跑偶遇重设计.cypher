// ═══ 2024-06-09 晨跑偶遇重设计（老人辞世版） 2026-10-16 ═══
// 依据：02_剧情数据/2026-10-16_2024-06-09晨跑偶遇_关系提取.md（人工审阅版，两轮交互裁决）
// 结构：新 E1(替代 RGcLQijx3T)/E2/E3 + L2 康复中心 + C3 辞世老人 + I1~I8
// 处置：旧 E28 及专属 Info BN/BO/BM 标 status=-1（B8 跑姿口诀因被 06-05 教跑姿事件共用而保留）；
//       evt_relation 先后 与入向 leads_to 迁移至新 E1；RGcLQj1YBq 改名
// 执行：python .claude/scripts/cypher_exec.py -f <本文件> --multi

// ── 1. 作废：旧 E28 + 3 条专属 Info（B8 共用保留）──
UNWIND ['RGcLQijx3T','RGcLQj1YBN','RGcLQj1YBO','RGcLQj1YBM'] AS did
MATCH (n {id:did}) SET n.status = -1;

// ── 2. RGcLQj1YBq 改名（决策⑤）──
MATCH (i:Info {id:'RGcLQj1YBq'}) SET i.title = '陈默与苏晓禾的默契积累';

// ── 3. evt_relation 先后迁移：送行(06-08)→E1；E1→致歉(06-10) ──
MATCH (old:Event {id:'RGcLQijx3T'})-[r:evt_relation]->(u:Event {id:'RGcLQijx3U'}) DELETE r;
MATCH (s:Event {id:'RGcLQijx3S'}) MATCH (e1:Event {id:'RHmefLkiu0'}) MERGE (s)-[:evt_relation {type:'先后'}]->(e1);
MATCH (e1:Event {id:'RHmefLkiu0'}) MATCH (u:Event {id:'RGcLQijx3U'}) MERGE (e1)-[:evt_relation {type:'先后'}]->(u);

// ── 4. 入向 leads_to 迁移：教跑姿/第三闹钟 → E1（detail 措辞去「获认可」）──
MATCH (i:Event {id:'RGcLQijx3I'})-[r:leads_to]->(:Event {id:'RGcLQijx3T'}) DELETE r;
MATCH (i:Event {id:'RGcLQijx3I'}) MATCH (e1:Event {id:'RHmefLkiu0'}) MERGE (i)-[:leads_to {detail:'教的跑姿被照练执行，坚持晨跑才有了再次偶遇'}]->(e1);
MATCH (l:Event {id:'RGcLQijx3L'})-[r:leads_to]->(:Event {id:'RGcLQijx3T'}) DELETE r;
MATCH (l:Event {id:'RGcLQijx3L'}) MATCH (e1:Event {id:'RHmefLkiu0'}) MERGE (l)-[:leads_to {detail:'坚持同路线晨跑才有了老地方再遇'}]->(e1);

// ── 5. 新节点：C3 老人（L2 康复中心复用已有节点 QP23NrFZqm，不新建）──
MERGE (c3:Character {id:'RHmefLkiu4'}) SET c3.name = '辞世的老人', c3.description = '苏晓禾此前的照护对象，2024-06-09 凌晨前后在康复中心(QP23NrFZqm)辞世；未出场，仅被提及';

// ── 6. 新 Event ×3 ──
UNWIND [
  {id:'RHmefLkiu0', title:'陈默晨跑偶遇苏晓禾主动打招呼', time:'2024-06-09 06:00:00', type:'交流', description:'Day 8 清晨南滨路滨江步道老位置；替代 RGcLQijx3T——陈默主动打破无言默契打招呼'},
  {id:'RHmefLkiu1', title:'陈默看出苏晓禾情绪低落并询问', time:'2024-06-09 06:10:00', type:'交流', description:'紧接偶遇；「问及原因」引出照护老人辞世的披露'},
  {id:'RHmefLkiu2', title:'苏晓禾照护的老人在康复中心辞世', time:'2024-06-09 05:00:00', type:'状态变化', description:'夜间发生于康复中心；苏晓禾不在场，次日清晨获知；确切辞世时间待剧本定'}
] AS row MERGE (e:Event {id:row.id}) SET e = row;

// ── 7. 新 Info ×8（事实层 I1~I5 kl=1 / 推断层 I6~I8 kl=3）──
UNWIND [
  {id:'RHmefLkiu5', title:'苏晓禾是护工且有一名照护老人近日辞世', kl:1, content:'苏晓禾职业为护工（康复中心），其照护的一名老人于 2024-06-09 凌晨前后辞世——晨跑对话中首次披露'},
  {id:'RHmefLkiu6', title:'苏晓禾晨跑时情绪低落', kl:1, content:'2024-06-09 清晨南滨路，苏晓禾神态明显低落，被陈默察觉'},
  {id:'RHmefLkiu7', title:'陈默主动打破无言默契打招呼', kl:1, content:'2024-06-09 偶遇时陈默主动和苏晓禾打招呼，与此前仅并肩无言跑的关系模式不同'},
  {id:'RHmefLkiu8', title:'陈默能从神态察觉苏晓禾的情绪变化', kl:1, content:'陈默「看出」苏晓禾情绪低落——对她的关注度足以支撑情绪识别'},
  {id:'RHmefLkiu9', title:'苏晓禾次日清晨才获知老人辞世', kl:1, content:'老人夜间在康复中心辞世，机构次日清晨告知苏晓禾；她非当值亲历'},
  {id:'RHmefLkiuA', title:'苏晓禾对照护老人投入了真实感情', kl:3, content:'推断层：照护对象辞世致其次日晨跑明显低落→非纯工作关系，情感投入深'},
  {id:'RHmefLkiuB', title:'陈默对苏晓禾的在意超出普通跑友', kl:3, content:'推断层：主动打破沉默＋察觉情绪变化→关注度上升；与「苏晓禾对陈默渐生好感与在意」(RGcLQj1YBp)形成双向呼应'},
  {id:'RHmefLkiuC', title:'苏晓禾愿意向陈默袒露私事', kl:3, content:'推断层：被问即答出照护老人辞世→关系已越过点头之交层'}
] AS row MERGE (i:Info {id:row.id}) SET i.title = row.title, i.knowledge_level = row.kl, i.content = row.content;

// ── 8. involved ×6 ──
UNWIND [
  {e:'RHmefLkiu0', c:'陈默', r:'当事人'}, {e:'RHmefLkiu0', c:'苏晓禾', r:'当事人'},
  {e:'RHmefLkiu1', c:'陈默', r:'当事人'}, {e:'RHmefLkiu1', c:'苏晓禾', r:'当事人'},
  {e:'RHmefLkiu2', c:'苏晓禾', r:'相关人'}, {e:'RHmefLkiu2', c:'辞世的老人', r:'当事人'}
] AS row
MATCH (ev:Event {id:row.e}) MATCH (c:Character {name:row.c})
MERGE (c)-[:involved {role:row.r}]->(ev);

// ── 9. occurs_at ×3（不变式：每 Event 恰 1 条）──
UNWIND [
  {e:'RHmefLkiu0', l:'南滨路'}, {e:'RHmefLkiu1', l:'南滨路'}, {e:'RHmefLkiu2', l:'康复中心'}
] AS row
MATCH (ev:Event {id:row.e}) MATCH (loc:Location {name:row.l})
MERGE (ev)-[:occurs_at]->(loc);

// ── 10. link ×19（表 B；Schema 方向 Character/Event/Location → Info）──
// 10a. Character → Info ×9
UNWIND [
  {c:'苏晓禾', i:'RHmefLkiu5'}, {c:'陈默', i:'RHmefLkiu5'},
  {c:'苏晓禾', i:'RHmefLkiu6'}, {c:'陈默', i:'RHmefLkiu6'},
  {c:'陈默', i:'RHmefLkiu7'}, {c:'陈默', i:'RHmefLkiu8'},
  {c:'苏晓禾', i:'RHmefLkiu9'}, {c:'苏晓禾', i:'RHmefLkiuA'},
  {c:'陈默', i:'RHmefLkiuB'}, {c:'苏晓禾', i:'RHmefLkiuC'}
] AS row
MATCH (src:Character {name:row.c}) MATCH (i:Info {id:row.i})
MERGE (src)-[:link {type:'涉及'}]->(i);
// 10b. Location → Info ×3
UNWIND [
  {l:'南滨路', i:'RHmefLkiu6'}, {l:'南滨路', i:'RHmefLkiu7'}, {l:'康复中心', i:'RHmefLkiu9'}
] AS row
MATCH (src:Location {name:row.l}) MATCH (i:Info {id:row.i})
MERGE (src)-[:link {type:'涉及'}]->(i);
// 10c. Event → Info ×8（关联事件顺带）
UNWIND [
  {e:'RHmefLkiu1', i:'RHmefLkiu5'},
  {e:'RHmefLkiu0', i:'RHmefLkiu6'}, {e:'RHmefLkiu1', i:'RHmefLkiu6'},
  {e:'RHmefLkiu0', i:'RHmefLkiu7'},
  {e:'RHmefLkiu1', i:'RHmefLkiu8'},
  {e:'RHmefLkiu2', i:'RHmefLkiu9'},
  {e:'RHmefLkiu1', i:'RHmefLkiuA'},
  {e:'RHmefLkiu0', i:'RHmefLkiuB'}, {e:'RHmefLkiu1', i:'RHmefLkiuB'},
  {e:'RHmefLkiu1', i:'RHmefLkiuC'}
] AS row
MATCH (src:Event {id:row.e}) MATCH (i:Info {id:row.i})
MERGE (src)-[:link {type:'涉及'}]->(i);

// ── 11. leads_to ×5（表 C 真因果；上游均为本次新建 Event/Info，id 全局唯一）──
UNWIND [
  {up:'RHmefLkiu2', dn:'RHmefLkiu9', d:'辞世发生后机构次日清晨通知到人'},
  {up:'RHmefLkiu2', dn:'RHmefLkiu6', d:'照护对象离世是情绪低落的直接原因'},
  {up:'RHmefLkiu0', dn:'RHmefLkiu1', d:'打招呼后面对面交流才给了「看出」的机会'},
  {up:'RHmefLkiu1', dn:'RHmefLkiu5', d:'陈默的询问直接引出职业与变故的披露'},
  {up:'RHmefLkiu5', dn:'RHmefLkiuC', d:'被问即答，袒露行为由披露完成'}
] AS row
MATCH (u {id:row.up}) MATCH (v {id:row.dn})
MERGE (u)-[:leads_to {detail:row.d}]->(v);
