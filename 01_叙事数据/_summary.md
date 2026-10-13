# 叙事提取摘要 — 25_剧本 ink 唯一事实（2026-10-14）

> 本文件取代 2026-09-13 版（大纲提取摘要，见文末历史注记）。`csv/` 目录为旧大纲提取产物，**已退役（2026-10-09 起标注，禁止再整体执行）**，仅作历史存档。

## 现行事实（2026-10-14 重提取）

- **源**：`25_剧本/` 13 个 `台词.ink`（chapter00_序章 3 节 + chapter01_新皮肤 10 节，27 个场景块，剧情 Day −1 ~ Day 10）——**唯一事实**；大纲/蓝本仅作 Day 定位参考。
- **产物**：`02_剧情数据/InfoEvent重提取-20261014/`（提取总表 md + import.cypher + step1/step3 脚本 + csv/ 存档 + README 执行记录）。
- **图内数据**：Event 30 / Info 31 / Choice 1；边 involved 76 / occurs_at 30 / evt_relation 29 / leads_to 9 / link 57 / presents 1 / option 2 / anchored_at 27 / wears 20。
- **回滚锚点**：工作区根 `ProxyLove_backup_20261014_InfoEvent清理前.csv`。

## 提取纪律（沿用）

- 后续新章节 ink 定稿（SecScript status=11）后，增量提取新 Event/Info/Choice 并挂边；时序接 `evt_relation{先后}`，因果接 `leads_to`。
- 大纲层元知识（真规则/六试炼结构等）**不入图**，源头读 `00_init/大纲.md`，备查见提取总表附录。
- 旧大纲 Day 11+ 事件（西餐厅牛排起 40 个）已随本次清理移除，待对应章节 ink 产出后重提取。

## 历史注记（2026-09-13 版摘要，源 00_init/大纲.md）

源：新版第一章大纲（Day 0-30 三段 + 三支线 + Day 30 揭晓 + 后日谈）。生成脚本 .tmp/narrative_extract_gen.py。产出 nodes_char 10 / nodes_location 13 / nodes_event 54 / nodes_info 19 / nodes_choice 1 + 边 8 文件 227 条——该批数据已于 2026-10-14 全量清理并被 ink 重提取取代（Character/Location 未清理，仍沿用）。
