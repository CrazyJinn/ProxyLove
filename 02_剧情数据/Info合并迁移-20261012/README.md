# Info 合并迁移（2026-10-12）：叙事层剪枝 + Event/Info/Choice 多 label 合并

两件事一次窗口完成：

1. **剪枝**：图内叙事数据只保留 ch00（序章，开场 5 事件）+ ch01（新皮肤，Day 0~**10**，含 Day 10「沈暮雪邀约二队」——Chapter1 summary 权威覆盖到 Day 10 咖啡店邀约/sec09）。删除 Day 11~30 + 后日谈。
2. **合并**：Event/Info/Choice → 基础 label `:Info` + 附加 label（`:Info:Event` / `:Info:Choice`）；Choice 的 `name`→`title`；全库 21 个 label 建 id 唯一约束。

## 脚本清单

| 文件 | 内容 | 执行时机 |
|---|---|---|
| `step0_precheck.cypher` | 只读预检：P1 每 label 重复 id（**必须 0 行**）/ P2 Choice 属性 / P3 Event title 完备 / P4 基线计数 | 开窗前 |
| `prune_dryrun.cypher` | 只读闸门：D1 待删 Event（**必须 41 行**）/ D2 待删 Choice（**1**）/ D3 待删 Info（**4**）/ D4 剪枝后各类边余量 | 开窗前，数字不符禁止开窗 |
| `window_prune.cypher` | 剪枝（单事务）：Choice → Info(B组) → Event 顺序 DETACH DELETE | 窗口 ② |
| `window_info_merge.cypher` | label 合并 + name→title（单事务，幂等） | 窗口 ③ |
| `step2_constraints.sh` | 21 个 label 唯一约束（DDL 须事务外，逐条 auto-commit） | 窗口 ④ |
| `verify_post.cypher` | 只读验收（计数 + 形态抽样） | 窗口 ⑤ |
| `rollback_info_merge.cypher` | 仅 label 合并可逆（去附加 label / name 恢复 / 删约束） | 异常时 |

## 执行入口（在 Asset 根目录）

```bash
python .claude/scripts/cypher_exec.py -f 02_剧情数据/Info合并迁移-20261012/step0_precheck.cypher --multi --json
python .claude/scripts/cypher_exec.py -f 02_剧情数据/Info合并迁移-20261012/prune_dryrun.cypher --multi --json
# ↑ P1=0 行、D1/D2/D3=41/1/4 全过才允许 ↓
python .claude/scripts/cypher_exec.py -f 02_剧情数据/Info合并迁移-20261012/window_prune.cypher --multi --json
python .claude/scripts/cypher_exec.py -f 02_剧情数据/Info合并迁移-20261012/window_info_merge.cypher --multi --json
bash 02_剧情数据/Info合并迁移-20261012/step2_constraints.sh
python .claude/scripts/cypher_exec.py -f 02_剧情数据/Info合并迁移-20261012/verify_post.cypher --multi --json
```

## 保留谓词（Event 归属 ch00/ch01，各脚本共用）

```cypher
e.time = '开场'
OR (e.time STARTS WITH 'Day' AND toInteger(split(e.time, ' ')[1]) IS NOT NULL
    AND toInteger(split(e.time, ' ')[1]) <= 10)
```

## 删留口径（用户 2026-10-12 拍板）

- **Event**：保留 23（开场 5 + Day 0~10 18）；删除 41（Day 11~30 的 38 + 后日谈 3）。
- **Choice**：「跳江选择」(Day 0 深夜) 保留；「三选一」(Day 22) 及其 3 个 option 事件整组删除（option 事件已含在 41 内）。
- **Info**：删 4 个 B 组（仅挂在被删事件上：拯救的定义/试炼好处/林梦漫展做局/三选一机制）；挂在 Character/Location/保留事件上的 22 个保留。
- **孤儿 Spot/Location/CostumeStyle 本次不动**（DETACH DELETE 只带走边，不删其他节点）。

## 窗口纪律

- 窗口前全量 CSV 快照：`D:\project\ProxyLove\ProxyLove_backup_20261012_212138.csv`（950 节点 / 1552 边，md5 `57fda47a6d0ecb5efd26e89c9b6be97c`）。
- 窗口内冻结 NRT 写操作（graph-builder 写入、grower 建议回写、Dashboard /events 新增）。
- 闸门：P1 每 label 重复 id = 0 行；D1/D2/D3 = 41/1/4 且标题清单核对。任一不符即停。

## 回滚说明

- **label 合并**可逆：`rollback_info_merge.cypher`（幂等）。
- **剪枝不可逆**（DETACH DELETE 无反向脚本）：唯一回滚 = 窗口前 CSV 快照经 Dashboard `/data` 导入整库恢复。
- **旧快照恢复后附加 label 会丢**：恢复完成后再重跑 `window_info_merge.cypher`（幂等）补 `:Info` 基础 label；约束由 `step2_constraints.sh` 幂等重建。

## 执行记录

- 2026-10-12 21:21 备份快照落盘（950n/1552e，md5 见上）。
- 2026-10-12 预检/dry-run 实测（开窗闸门全过）：
  - P1 每 label 重复 id = **0 行**；P3 Event title 缺失 = 0；P4 基线 Event 64 / Info 26 / Choice 2 / 全库 950。
  - D1 待删 Event = **41 行**（Day 11~30 的 38 + 后日谈 3，标题清单核对一致）；D2 = **1**（三选一）；D3 = **4**（拯救的定义/林梦漫展做局/三选一机制/试炼好处）。
  - 边余量实测（总数-将删）：evt_relation 22(62-40)、involved 39(125-86)、link 24(28-4)、occurs_at 22(47-25)、option 2(5-3)、presents 1(2-1)、wears 19(33-14)；生产层各边（produces/uses/contains/has_* 等）将删数全为 0。
- 2026-10-12 开窗执行（用户确认无并发写）：
  - window_prune / window_info_merge 单事务执行成功；
  - 21 条约束全部建成（每个 label 一条 `<label小写>_id_unique`：character/location/spot/info/event/choice/scene/scenelayer/costumestyle/languagestyle/appearancestyle/designsheet/illusdesign/standingillustration/voicedesign/chapter/section/secoutline/secscript/bgmtrack/lineaudio）；
  - verify_post 全绿：全库 904（950-46）/ Info 超集 46 / :Info:Event 23 / :Info:Choice 1 / 纯 Info 22 / 漏打 0 / 残留 name 0；边计数 link 24 / presents 1 / option 2 / evt_relation 22 / involved 39 / occurs_at 22 / wears 19，与 dry-run 预测逐项一致；
  - 抽样：跳江选择 labels=[Info, Choice] title 正常；沈暮雪邀约二队（Day 10）与陆择酒店醒来（开场）labels=[Info, Event]。
- 遗留数据质量问题（本次只报告不修，留 gap-filler）：「陈默跳江陆择灵魂挤入」缺 occurs_at 边；Day 2 内部 3 条 evt_relation 的 rtype 为 null。
