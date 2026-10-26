// ══ 2026-10-26_import_event驱动化原子迁移.cypher ══
// 依据:Event驱动化改造提案.md(2026-10-26 定稿)+ .tmp/event_migration/precheck_report.json
// 结构:S1 includes → S2 新 anchored_at → S3 appears_as(显式清单) → S4 part_of 翻转 → S5-S9 删旧边(先建后删)
// 处置:单事务;全语句幂等(MERGE);预期计数见各段注释,验收走 .tmp/event_migration/verify.py(E1-E9)
// 执行:python .claude/scripts/cypher_exec.py -f 02_剧情数据/2026-10-26_import_event驱动化原子迁移.cypher --multi
// 回滚:窗口前快照 ProxyLove_backup_20261026_202722.csv wipe 重灌;重灌后需重跑 active_from 回填(NOTES.md)

// ── S1. includes 建边(M2:8 节 × 12 事件,order=事件 time 序;须在删 contains 前执行)──
MATCH (sec:Section)-[:contains]->(:Scene)<-[:realizes]-(sp:Spot) MATCH (e:Event)-[:anchored_at]->(sp) WHERE sec.time_day IS NOT NULL AND e.time STARTS WITH sec.time_day WITH sec, e ORDER BY e.time, e.id WITH sec, collect(DISTINCT e) AS evts UNWIND [i IN range(0, size(evts)-1) | [evts[i], i]] AS pair WITH sec, pair[0] AS e2, pair[1] AS ord MERGE (sec)-[r:includes]->(e2) ON CREATE SET r.order = ord, r.sync = false;

// ── S2. anchored_at 端点改挂 Spot→Scene(M1 显式清单,42 条;orphan 0 条不入,见人工清单)──
MATCH (e:Event {id:'RMoHgKlbdq'}), (sc:Scene {id:'RVaUJp92GH'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='用户多选敲定:参观主场景归训练大厅(领域语义);花园同时建为预留'; // section_order 康复中心-训练大厅 -> 康复中心-训练大厅
MATCH (e:Event {id:'RQEfM71ctk'}), (sc:Scene {id:'RVkysIzpeD'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='卡座临别邀爬山,时间顺承同一顿饭'; // section_order 火锅店-火锅店 -> 火锅店
MATCH (e:Event {id:'RU7x61XmiG'}), (sc:Scene {id:'RVkysIzpeD'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='卡座对坐相亲局'; // section_order 火锅店-火锅店 -> 火锅店
MATCH (e:Event {id:'RINsONAOMr'}), (sc:Scene {id:'QmJFWWyN17'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='店内试衣置装刷卡六百八(整点,无子空间证据)'; // fallback 服装店-未细分 -> 服装店
MATCH (e:Event {id:'RINsONAOMl'}), (sc:Scene {id:'OwNTDArnfs'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='湖畔茅草屋前伊芙宣告下地狱与穿越试炼规则(整点)'; // fallback 灵魂夹缝-未细分 -> 灵魂夹缝
MATCH (e:Event {id:'RINsONAOMm'}), (sc:Scene {id:'QW6yYoIiSu'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='桥面护栏边翻回栏杆接陈念来电'; // fallback 长江大桥-护栏段 -> 长江大桥-护栏段
MATCH (e:Event {id:'RINsONAOMn'}), (sc:Scene {id:'QW6yYoIiSu'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='深夜翻越护栏外侧坠江(BE)'; // fallback 长江大桥-护栏段 -> 长江大桥-护栏段
MATCH (e:Event {id:'RINsONAONB'}), (sc:Scene {id:'QW6yYoIiSu'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='陆择入体初醒,深夜立于护栏外侧'; // fallback 长江大桥-护栏段 -> 长江大桥-护栏段
MATCH (e:Event {id:'RINsONAOMw'}), (sc:Scene {id:'QW7CSvlX5k'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='滨江步道晨跑搭讪被苏晓禾婉拒'; // fallback 南滨路-滨江步道 -> 南滨路-滨江步道
MATCH (e:Event {id:'RINsONAOMz'}), (sc:Scene {id:'QW7CSvlX5k'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='按闹钟晨跑三公里买菜'; // fallback 南滨路-滨江步道 -> 南滨路-滨江步道
MATCH (e:Event {id:'RINsONAON4'}), (sc:Scene {id:'QW7CSvlX5k'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='晨跑偶遇苏晓禾得知老人离世'; // fallback 南滨路-滨江步道 -> 南滨路-滨江步道
MATCH (e:Event {id:'RINsONAOMk'}), (sc:Scene {id:'Oib4U5kSnI'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='路口遭摩托车撞击身亡'; // fallback 马路-路口 -> 马路-路口
MATCH (e:Event {id:'RINsONAOMj'}), (sc:Scene {id:'PHuTf3ogEu'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='点餐台买拿铁打包问路'; // fallback 街角咖啡店-点餐台 -> 街角咖啡店-点餐台
MATCH (e:Event {id:'RINsONAOMi'}), (sc:Scene {id:'OiZR8tKjLc'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='客房醒来与顾盈晨别'; // fallback 酒店-客房 -> 酒店-客房
MATCH (e:Event {id:'RINsONAOMq'}), (sc:Scene {id:'QW7Q5BdYAq'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='剪发椅上改造形象'; // fallback 理发店-剪发区 -> 理发店-剪发区
MATCH (e:Event {id:'RINsONAON6'}), (sc:Scene {id:'QW7MyzUtiS'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='座位区面谈,沈暮雪邀约加入星耀二队'; // fallback 连锁咖啡店-座位区 -> 连锁咖啡店-座位区
MATCH (e:Event {id:'RINsONAON2'}), (sc:Scene {id:'QW7J1XaAFc'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='五连工位 solo 试训五局全胜'; // fallback 星耀电竞基地-训练馆 -> 星耀电竞基地-训练馆
MATCH (e:Event {id:'RINsONAON3'}), (sc:Scene {id:'QW7J1XaAFc'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='训练赛崩盘顶撞江烈不欢而散'; // fallback 星耀电竞基地-训练馆 -> 星耀电竞基地-训练馆
MATCH (e:Event {id:'RINsONAOMo'}), (sc:Scene {id:'QW77oRdOwS'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='深夜电脑桌前翻转账记录删联系方式'; // fallback_multi 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备前
MATCH (e:Event {id:'RINsONAOMs'}), (sc:Scene {id:'QW77oRdOwS'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='电脑前盘点余额与待交付订单'; // fallback_multi 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备前
MATCH (e:Event {id:'RINsONAOMt'}), (sc:Scene {id:'QW77oRdOwS'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='电脑桌前上线接单翻盘'; // fallback_multi 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备前
MATCH (e:Event {id:'RINsONAOMu'}), (sc:Scene {id:'QW77oRdOwS'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='电脑桌前打林梦陪玩单'; // fallback_multi 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备前
MATCH (e:Event {id:'RINsONAOMx'}), (sc:Scene {id:'QW77oRdOwS'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='接林梦来电谈设备升级与投资(直播事务,屋内)'; // fallback_multi 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备前
MATCH (e:Event {id:'RINsONAOMy'}), (sc:Scene {id:'QW77oRdOwS'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='收拾屋子定三闹钟(全屋动作,归卧室)'; // fallback_multi 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备前
MATCH (e:Event {id:'RINsONAON0'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='电脑桌直播位首播峰值一万二'; // override 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RINsONAON1'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='深夜下播后电脑桌前收沈暮雪私信'; // override 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RINsONAON5'}), (sc:Scene {id:'QW77oRdOwU'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='晨起手机收沈暮雪微信致歉'; // override 八楼出租屋-卧室 -> 八楼出租屋-床铺区
MATCH (e:Event {id:'RINsONAON7'}), (sc:Scene {id:'QW77oRdOwU'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='起床后床铺上看三女主三连消息'; // fallback_kw 八楼出租屋-卧室 -> 八楼出租屋-床铺区
MATCH (e:Event {id:'RINsONAON8'}), (sc:Scene {id:'QW77oRdOwU'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='起床后回消息与苏晓禾确定关系(床铺)'; // fallback_kw 八楼出租屋-卧室 -> 八楼出租屋-床铺区
MATCH (e:Event {id:'RINsONAON9'}), (sc:Scene {id:'QW77oRdOwU'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='起床后回消息与林梦确定关系(床铺)'; // fallback_kw 八楼出租屋-卧室 -> 八楼出租屋-床铺区
MATCH (e:Event {id:'RINsONAONA'}), (sc:Scene {id:'QW77oRdOwU'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='起床后回消息与沈暮雪确定关系(床铺)'; // fallback_kw 八楼出租屋-卧室 -> 八楼出租屋-床铺区
MATCH (e:Event {id:'RMoHgKlbdp'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='直播中人气回落,电脑桌直播位'; // section_order 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RMxYXuS6IC'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='卧室内手机收微信'; // section_order 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RO5gftNez3'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='电脑桌前线上练习赛'; // section_order 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RQAZwH7RHW'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='电脑桌前刷录像复盘写方案'; // section_order 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RQBqw5y3oe'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='下播后电脑桌前连麦'; // section_order 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RRl7l6AeGG'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='电脑桌前线上训练赛'; // section_order 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RRpw8kqSLw'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='电脑桌直播位下播连麦'; // section_order 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RU608HspJw'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='电脑桌前线上训练赛'; // section_order 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RU608K9cMS'}), (sc:Scene {id:'R22lVGrBuC'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='电脑桌前线上训练赛'; // section_order 八楼出租屋-卧室 -> 八楼出租屋-电脑桌直播位-更新设备后
MATCH (e:Event {id:'RINsONAOMp'}), (sc:Scene {id:'QW77oRdOwT'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='陈念上门塞满冰箱留现金(冰箱在门厅厨房角)'; // fallback_kw 八楼出租屋-门厅 -> 八楼出租屋-厨房餐区
MATCH (e:Event {id:'RINsONAOMv'}), (sc:Scene {id:'RLFwn8iZlJ'}) MERGE (e)-[na:anchored_at]->(sc) ON CREATE SET na.sync = false, na.detail='家中剪辑录像并发布头条(整点,无子空间证据)'; // fallback 林梦家-未细分 -> 林梦家

// ── S3. appears_as 建边(M3 显式清单,78 条:depicts/wears/default 三路口径+事件时间选版)──
MATCH (e:Event {id:'RINsONAOMi'}), (il:IllusDesign {id:'P16PBEZd32'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陆择 @ 2024-05-31 06:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMi'}), (il:IllusDesign {id:'NyJEE0VkCO'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 顾盈 @ 2024-05-31 06:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMj'}), (il:IllusDesign {id:'Pu7LOpNs3s'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 小夏 @ 2024-05-31 06:30:00 [depicts]
MATCH (e:Event {id:'RINsONAOMj'}), (il:IllusDesign {id:'OLBbajiuMS'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陆择 @ 2024-05-31 06:30:00 [depicts]
MATCH (e:Event {id:'RINsONAOMk'}), (il:IllusDesign {id:'OLBbajiuMS'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陆择 @ 2024-05-31 07:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMl'}), (il:IllusDesign {id:'OxzWPYTYG0'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 伊芙 @ 2024-05-31 18:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMl'}), (il:IllusDesign {id:'P1CMB2XHMn'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陆择 @ 2024-05-31 18:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMm'}), (il:IllusDesign {id:'Qe4TZcpKbI'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈念 @ 2024-06-01 23:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMm'}), (il:IllusDesign {id:'QUVhvJKplY'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-01 23:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMn'}), (il:IllusDesign {id:'QUVhvJKplY'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-01 23:00:00 [depicts]
MATCH (e:Event {id:'RINsONAONB'}), (il:IllusDesign {id:'QUVhvJKplY'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-01 23:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMo'}), (il:IllusDesign {id:'QUVhvJKplY'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-01 23:30:00 [depicts]
MATCH (e:Event {id:'RINsONAOMp'}), (il:IllusDesign {id:'Qe4TZcpKbI'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈念 @ 2024-06-02 09:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMp'}), (il:IllusDesign {id:'QUVhvJKplY'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-02 09:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMq'}), (il:IllusDesign {id:'Qy1MVYC2TI'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // Tony @ 2024-06-03 09:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMq'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-03 09:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMr'}), (il:IllusDesign {id:'QxzPjfsg5Y'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 季棠 @ 2024-06-03 10:30:00 [depicts]
MATCH (e:Event {id:'RINsONAOMr'}), (il:IllusDesign {id:'QmFVxZtCtd'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-03 10:30:00 [depicts]
MATCH (e:Event {id:'RINsONAOMs'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-03 15:00:00 [depicts+override]
MATCH (e:Event {id:'RINsONAOMt'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-03 20:00:00 [depicts+override]
MATCH (e:Event {id:'RINsONAOMu'}), (il:IllusDesign {id:'QSkk1LfIx8'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 林梦 @ 2024-06-04 15:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMu'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-04 15:00:00 [depicts+override]
MATCH (e:Event {id:'RINsONAOMv'}), (il:IllusDesign {id:'QSkk1LfIx6'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 林梦 @ 2024-06-04 20:00:00 [default]
MATCH (e:Event {id:'RINsONAOMw'}), (il:IllusDesign {id:'NyJ99Sgpfs'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 苏晓禾 @ 2024-06-05 06:30:00 [depicts]
MATCH (e:Event {id:'RINsONAOMw'}), (il:IllusDesign {id:'QmFVxZtCte'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-05 06:30:00 [depicts]
MATCH (e:Event {id:'RINsONAOMx'}), (il:IllusDesign {id:'QSkk1LfIx8'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 林梦 @ 2024-06-06 12:00:00 [depicts]
MATCH (e:Event {id:'RINsONAOMx'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-06 12:00:00 [depicts+override]
MATCH (e:Event {id:'RINsONAOMy'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-06 18:00:00 [depicts+override]
MATCH (e:Event {id:'RINsONAOMz'}), (il:IllusDesign {id:'QmFVxZtCte'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-07 06:50:00 [depicts]
MATCH (e:Event {id:'RINsONAON0'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-07 20:00:00 [depicts+override]
MATCH (e:Event {id:'RINsONAON1'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-07 23:30:00 [depicts]
MATCH (e:Event {id:'RINsONAON1'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-07 23:30:00 [depicts+override]
MATCH (e:Event {id:'RINsONAON2'}), (il:IllusDesign {id:'R4u7BQso3k'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 江烈 @ 2024-06-08 15:00:00 [depicts]
MATCH (e:Event {id:'RINsONAON2'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-08 15:00:00 [depicts]
MATCH (e:Event {id:'RINsONAON2'}), (il:IllusDesign {id:'QmQCxuTrGK'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-08 15:00:00 [depicts]
MATCH (e:Event {id:'RINsONAON3'}), (il:IllusDesign {id:'R4u7BQso3k'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 江烈 @ 2024-06-08 16:30:00 [depicts]
MATCH (e:Event {id:'RINsONAON3'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-08 16:30:00 [depicts]
MATCH (e:Event {id:'RINsONAON3'}), (il:IllusDesign {id:'QmQCxuTrGK'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-08 16:30:00 [depicts]
MATCH (e:Event {id:'RINsONAON4'}), (il:IllusDesign {id:'NyJ99Sgpfs'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 苏晓禾 @ 2024-06-09 06:00:00 [depicts]
MATCH (e:Event {id:'RINsONAON4'}), (il:IllusDesign {id:'QmFVxZtCte'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-09 06:00:00 [depicts]
MATCH (e:Event {id:'RINsONAON5'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-10 09:00:00 [depicts]
MATCH (e:Event {id:'RINsONAON5'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-10 09:00:00 [depicts+override]
MATCH (e:Event {id:'RINsONAON6'}), (il:IllusDesign {id:'OpaeGwlw3s'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-10 15:00:00 [depicts]
MATCH (e:Event {id:'RINsONAON6'}), (il:IllusDesign {id:'QmFVxZtCtd'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-10 15:00:00 [depicts]
MATCH (e:Event {id:'RMoHgKlbdp'}), (il:IllusDesign {id:'QSkk1LfIx8'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 林梦 @ 2024-06-11 20:00:00 [depicts]
MATCH (e:Event {id:'RMoHgKlbdp'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-11 20:00:00 [depicts+override]
MATCH (e:Event {id:'RQBqw5y3oe'}), (il:IllusDesign {id:'QSkk1LfIx8'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 林梦 @ 2024-06-11 21:00:00 [depicts]
MATCH (e:Event {id:'RQBqw5y3oe'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-11 21:00:00 [depicts+override]
MATCH (e:Event {id:'RMoHgKlbdq'}), (il:IllusDesign {id:'NyJ99Sgpfs'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 苏晓禾 @ 2024-06-12 10:00:00 [default]
MATCH (e:Event {id:'RMoHgKlbdq'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-12 10:00:00 [default+override]
MATCH (e:Event {id:'RMxYXuS6IC'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-12 16:00:00 [depicts]
MATCH (e:Event {id:'RMxYXuS6IC'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-12 16:00:00 [depicts+override]
MATCH (e:Event {id:'RRl7l6AeGG'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-13 19:30:00 [depicts]
MATCH (e:Event {id:'RRl7l6AeGG'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-13 19:30:00 [depicts+override]
MATCH (e:Event {id:'RRpw8kqSLw'}), (il:IllusDesign {id:'QSkk1LfIx8'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 林梦 @ 2024-06-14 21:00:00 [depicts]
MATCH (e:Event {id:'RRpw8kqSLw'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-14 21:00:00 [depicts+override]
MATCH (e:Event {id:'RQAZwH7RHW'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-15 20:30:00 [depicts]
MATCH (e:Event {id:'RQAZwH7RHW'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-15 20:30:00 [depicts+override]
MATCH (e:Event {id:'RU608HspJw'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-17 19:30:00 [depicts]
MATCH (e:Event {id:'RU608HspJw'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-17 19:30:00 [depicts+override]
MATCH (e:Event {id:'RU7x61XmiG'}), (il:IllusDesign {id:'NyJ99Sgpfs'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 苏晓禾 @ 2024-06-18 12:00:00 [default]
MATCH (e:Event {id:'RU7x61XmiG'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-18 12:00:00 [default+override]
MATCH (e:Event {id:'RQEfM71ctk'}), (il:IllusDesign {id:'NyJ99Sgpfs'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 苏晓禾 @ 2024-06-18 12:30:00 [default]
MATCH (e:Event {id:'RQEfM71ctk'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-18 12:30:00 [default+override]
MATCH (e:Event {id:'RU608K9cMS'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-18 19:30:00 [depicts]
MATCH (e:Event {id:'RU608K9cMS'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-18 19:30:00 [depicts+override]
MATCH (e:Event {id:'RO5gftNez3'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-19 19:30:00 [depicts]
MATCH (e:Event {id:'RO5gftNez3'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-19 19:30:00 [depicts+override]
MATCH (e:Event {id:'RINsONAON7'}), (il:IllusDesign {id:'QSkk1LfIx8'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 林梦 @ 2024-06-22 09:00:00 [depicts]
MATCH (e:Event {id:'RINsONAON7'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-22 09:00:00 [depicts]
MATCH (e:Event {id:'RINsONAON7'}), (il:IllusDesign {id:'NyJ99Sgpfs'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 苏晓禾 @ 2024-06-22 09:00:00 [default]
MATCH (e:Event {id:'RINsONAON7'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-22 09:00:00 [depicts+override]
MATCH (e:Event {id:'RINsONAON8'}), (il:IllusDesign {id:'NyJ99Sgpfs'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 苏晓禾 @ 2024-06-22 09:00:00 [default]
MATCH (e:Event {id:'RINsONAON8'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-22 09:00:00 [depicts+override]
MATCH (e:Event {id:'RINsONAON9'}), (il:IllusDesign {id:'QSkk1LfIx8'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 林梦 @ 2024-06-22 09:00:00 [depicts]
MATCH (e:Event {id:'RINsONAON9'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-22 09:00:00 [depicts+override]
MATCH (e:Event {id:'RINsONAONA'}), (il:IllusDesign {id:'O0BFwtiWA4'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 沈暮雪 @ 2024-06-22 09:00:00 [depicts]
MATCH (e:Event {id:'RINsONAONA'}), (il:IllusDesign {id:'QmFVxZtCtc'}) MERGE (e)-[r:appears_as]->(il) ON CREATE SET r.sync = false; // 陈默 @ 2024-06-22 09:00:00 [depicts+override]

// ── S4. part_of 翻转 Spot→Location ⇒ Location→Spot(20 条,保 sync=false)──
MATCH (sp:Spot)-[old:part_of]->(l:Location) MERGE (l)-[np:part_of]->(sp) ON CREATE SET np.sync = false DELETE old;

// ── S5. 删 contains(52;includes 已建)──
MATCH ()-[r:contains]->() DELETE r;
// ── S6. 删 depicts(38;appears_as 已建)──
MATCH ()-[r:depicts]->() DELETE r;
// ── S7. 删旧 anchored_at(42:Event→Spot;新 Event→Scene 已建)──
MATCH (:Event)-[r:anchored_at]->(:Spot) DELETE r;
// ── S8. 删旧 wears(3:Event→CostumeStyle;appears_as 已建)──
MATCH (:Event)-[r:wears]->(:CostumeStyle) DELETE r;
// ── S9. 删 ref_style(103)──
MATCH (:LanguageStyle)-[r:ref_style]->(:StandingIllustration) DELETE r;
