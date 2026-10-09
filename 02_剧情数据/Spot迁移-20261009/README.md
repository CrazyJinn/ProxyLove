# Spot 迁移脚本（2026-10-09，Spot方案 v2.2 §6）

一次性存量迁移，全部幂等 MERGE，可安全重跑。执行入口：

```bash
python .claude/scripts/cypher_exec.py -f 02_剧情数据/Spot迁移-20261009/<脚本>.cypher --multi --json
```

| 脚本 | 内容 | 执行时机 |
|---|---|---|
| step1_default_spots.cypher | 19 个默认 Spot + part_of | 窗口前（步骤 3，新旧边并存） |
| window_zone_spots.cypher | 15 个 zone Spot + part_of | 原子窗口内 |
| window_occurs_at.cypher | 47 条 occurs_at（保留非空 detail）+ occurred_at 退役 DELETE | 原子窗口内（单事务，无中间态） |
| window_realizes.cypher | 19 个 Scene 归位 realizes | 原子窗口内 |

has_scene 退役 DELETE 不在此目录——消费方全部切净、验收全绿后单独执行（§9 步骤 6）。

## Spot id 分配表（snowflake_base62.py 预生成，2026-10-09）

### default（19）

| Spot 名 | id |
|---|---|
| 八楼出租屋-未细分 | R6YcFfBMWG |
| 登山步道-未细分 | R6YcFfBMWH |
| 地铁-未细分 | R6YcFfBMWI |
| 服装店-未细分 | R6YcFfBMWJ |
| 街角咖啡店-未细分 | R6YcFfBMWK |
| 康复中心-未细分 | R6YcFfBMWL |
| 连锁咖啡店-未细分 | R6YcFfBMWM |
| 林梦家-未细分 | R6YcFfBMWN |
| 理发店-未细分 | R6YcFfBMWO |
| 路边摊-未细分 | R6YcFfBMWP |
| 马路-未细分 | R6YcFfBMWQ |
| 漫展会场-未细分 | R6YcFfBMWR |
| 南滨路-未细分 | R6YcFfBMWS |
| 灵魂夹缝-未细分 | R6YcFfBMWT |
| 酒店-未细分 | R6YcFfBMWU |
| 超市-未细分 | R6YcFfBMWV |
| 西餐厅-未细分 | R6YcFfBMWW |
| 星耀电竞基地-未细分 | R6YcFfBMWX |
| 长江大桥-未细分 | R6YcFfBMWY |

### zone（15）

| Spot 名 | id | realize 的 Scene |
|---|---|---|
| 长江大桥-护栏段 | R6YcFfBMWZ | 长江大桥-护栏段 |
| 南滨路-滨江步道 | R6YcFfBMWa | 南滨路-滨江步道 |
| 马路-路口 | R6YcFfBMWb | 马路-路口 |
| 街角咖啡店-点餐台 | R6YcFfBMWc | 街角咖啡店-点餐台 |
| 酒店-客房 | R6YcFfBMWd | 酒店-客房 |
| 理发店-剪发区 | R6YcFfBMWe | 理发店-剪发区 |
| 连锁咖啡店-座位区 | R6YcFfBMWf | 连锁咖啡店-座位区 |
| 八楼出租屋-电脑桌区 | R6YcFfBMWg | 八楼出租屋-电脑桌直播位-更新设备前 / -更新设备后 |
| 八楼出租屋-厨房餐区 | R6YcFfBMWh | 八楼出租屋-厨房餐区 |
| 八楼出租屋-床铺区 | R6YcFfBMWi | 八楼出租屋-床铺区 |
| 八楼出租屋-进门处 | R6YcFfBMWj | 八楼出租屋-进门处 |
| 星耀电竞基地-比赛馆区 | R6YcFfBMWk | 星耀电竞基地-比赛场馆 / 星耀电竞基地-空场馆 |
| 星耀电竞基地-训练馆 | R6YcFfBMWl | 星耀电竞基地-训练馆 |
| 星耀电竞基地-经理办公区 | R6YcFfBMWm | 星耀电竞基地-经理办公区 |
| 星耀电竞基地-走廊 | R6YcFfBMWn | 星耀电竞基地-走廊 |

## 事件归位指派（47 条，含 6 条留 default 的多场景事件）

- 多场景 22 条：按 2026-10-09 用户过目定稿的指派表（八楼：电脑桌区 6 / 厨房餐区 1 / 床铺区 1 / 进门处 1 / default 6；星耀：训练馆 4 / 比赛馆区 2 / 经理办公区 1）——证据逐条见 window_occurs_at.cypher 注释。
- 单场景 15 条：v2.1 处置表（7 zone 全迁 anchor='spot'；服装店/灵魂夹缝留 default）。
- 0 场景 10 条：全部挂该地点 default Spot（anchor='default'，细化留 scene-designer 重跑）。

窗口纪律：自 step1 执行起至窗口结束，冻结 NRT 写操作；窗口前快照 `ProxyLove_backup_20261009_205726.csv`（857n/1418e，md5 42eb871b）。
