// 原子窗口：47 条 occurs_at 迁移（保留原 occurred_at 非空 detail）+ occurred_at 退役 DELETE
// 单事务（--multi）：建新边在前、删旧边在后，无「事件无定位」中间态
// 指派依据：单场景 15 条=v2.1 处置表；0 场景 10 条=全 default；多场景 22 条=2026-10-09 用户过目定稿指派表

// ── 单场景·zone（anchor='spot'）──
MATCH (e:Event {id:'NvCkQmFPG2'}), (sp:Spot {id:'R6YcFfBMWZ'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqo'}), (sp:Spot {id:'R6YcFfBMWZ'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='接电话处', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrZ'}), (sp:Spot {id:'R6YcFfBMWZ'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='并肩跑过护栏段', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrd'}), (sp:Spot {id:'R6YcFfBMWZ'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='并肩跑过大桥', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqt'}), (sp:Spot {id:'R6YcFfBMWa'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='晨跑路线', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqy'}), (sp:Spot {id:'R6YcFfBMWa'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrU'}), (sp:Spot {id:'R6YcFfBMWa'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='跑步路线', r.sync=false;
MATCH (e:Event {id:'NvCkQmFPFy'}), (sp:Spot {id:'R6YcFfBMWb'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='车祸发生的路口', r.sync=false;
MATCH (e:Event {id:'PHuTf3ogEt'}), (sp:Spot {id:'R6YcFfBMWb'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='咖啡店门口街角，转入马路', r.sync=false;
MATCH (e:Event {id:'PHuTf3ogEs'}), (sp:Spot {id:'R6YcFfBMWc'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='买咖啡地点', r.sync=false;
MATCH (e:Event {id:'NvCkQmFPFx'}), (sp:Spot {id:'R6YcFfBMWd'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='陆择和顾盈过夜的酒店', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqq'}), (sp:Spot {id:'R6YcFfBMWe'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='Day 1 上午', r.sync=false;
MATCH (e:Event {id:'QP23NrFZr0'}), (sp:Spot {id:'R6YcFfBMWf'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='约见', r.sync=false;

// ── 八楼出租屋·多场景（指派表定稿 2026-10-09）──
MATCH (e:Event {id:'QP23NrFZqr'}), (sp:Spot {id:'R6YcFfBMWg'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqu'}), (sp:Spot {id:'R6YcFfBMWg'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqv'}), (sp:Spot {id:'R6YcFfBMWg'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqw'}), (sp:Spot {id:'R6YcFfBMWg'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrE'}), (sp:Spot {id:'R6YcFfBMWg'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QmJFWWyN1C'}), (sp:Spot {id:'R6YcFfBMWg'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqs'}), (sp:Spot {id:'R6YcFfBMWh'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrA'}), (sp:Spot {id:'R6YcFfBMWi'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZr3'}), (sp:Spot {id:'R6YcFfBMWj'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='避雨处', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqp'}), (sp:Spot {id:'R6YcFfBMWG'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqz'}), (sp:Spot {id:'R6YcFfBMWG'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrF'}), (sp:Spot {id:'R6YcFfBMWG'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrT'}), (sp:Spot {id:'R6YcFfBMWG'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.detail='庆祝', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrb'}), (sp:Spot {id:'R6YcFfBMWG'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.detail='深夜现身', r.sync=false;
MATCH (e:Event {id:'QmJFWWyN1B'}), (sp:Spot {id:'R6YcFfBMWG'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;

// ── 星耀电竞基地·多场景（指派表定稿 2026-10-09）──
MATCH (e:Event {id:'QP23NrFZrD'}), (sp:Spot {id:'R6YcFfBMWk'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='空场馆', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrL'}), (sp:Spot {id:'R6YcFfBMWk'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='首秀', r.sync=false;
MATCH (e:Event {id:'QP23NrFZqx'}), (sp:Spot {id:'R6YcFfBMWl'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.detail='试训场', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrG'}), (sp:Spot {id:'R6YcFfBMWl'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrH'}), (sp:Spot {id:'R6YcFfBMWl'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrI'}), (sp:Spot {id:'R6YcFfBMWl'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrJ'}), (sp:Spot {id:'R6YcFfBMWm'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='spot', r.sync=false;

// ── 单场景·留 default（v2.1 处置表：弱后缀≈整点）──
MATCH (e:Event {id:'QmJFWWyN1A'}), (sp:Spot {id:'R6YcFfBMWJ'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;
MATCH (e:Event {id:'NvCkQmFPFz'}), (sp:Spot {id:'R6YcFfBMWT'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;

// ── 0 场景 8 地点·全 default（细化留 scene-designer 重跑）──
MATCH (e:Event {id:'QP23NrFZr6'}), (sp:Spot {id:'R6YcFfBMWH'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;
MATCH (e:Event {id:'QP23NrFZr7'}), (sp:Spot {id:'R6YcFfBMWI'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.detail='返程', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrC'}), (sp:Spot {id:'R6YcFfBMWL'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.detail='苏晓禾工作地', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrY'}), (sp:Spot {id:'R6YcFfBMWL'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;
MATCH (e:Event {id:'QP23NrFZr9'}), (sp:Spot {id:'R6YcFfBMWN'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrB'}), (sp:Spot {id:'R6YcFfBMWP'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;
MATCH (e:Event {id:'QP23NrFZrK'}), (sp:Spot {id:'R6YcFfBMWP'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.detail='夜宵摊', r.sync=false;
MATCH (e:Event {id:'QP23NrFZr8'}), (sp:Spot {id:'R6YcFfBMWR'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;
MATCH (e:Event {id:'QP23NrFZr4'}), (sp:Spot {id:'R6YcFfBMWV'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;
MATCH (e:Event {id:'QP23NrFZr1'}), (sp:Spot {id:'R6YcFfBMWW'}) MERGE (e)-[r:occurs_at]->(sp) ON CREATE SET r.anchor='default', r.sync=false;

// ── 退役旧边（同事务最后一步）──
MATCH (e:Event)-[r:occurred_at]->() DELETE r;
