# 叙事提取摘要 — 00_init/大纲.md（2026-09-13）

源：新版第一章大纲（Day 0-30 三段 + 三支线 + Day 30 揭晓 + 后日谈）。生成脚本 .tmp/narrative_extract_gen.py。

## 产出（01_叙事数据/csv/）

| 文件 | 行数 | 说明 |
|---|---|---|
| nodes_char.csv | 10 | 9 个已有角色复用更新描述/priority + 新角色陈念（1 新建） |
| nodes_location.csv | 13 | 全部新建（序章 4 地点在图中复用，不在 CSV） |
| nodes_event.csv | 54 | 全部新建；序章 7 事件（酒店醒来/买咖啡/遇雨/车祸/试炼规则/跳江挤入/跳江BE）图中复用 |
| nodes_info.csv | 19 | 18 新建 + **NvCkQmFPGb 更新**（见下） |
| nodes_choice.csv | 1 | 三选一（跳江选择 OdraDmqprU 图中复用） |
| 边 8 个文件 | 227 | relation 1 / involved 110 / occurred_at 35 / at 5 / link 18 / evt_relation 53 / presents 1 / option 4 |

## 与图现状的关键差异（导入前须知）

1. **NvCkQmFPGb 更新**：旧内容「灵魂穿越者无法直接控制宿主」与新大纲矛盾；新内容「可直接控制宿主言行，两难节点演出为玩家选择项（=陆择内心天平）」。
2. **小夏（PHuTf3ogEq）不再被引用**：新大纲开场店员即伊芙；小夏为序章存量角色，节点保留未动（序章已发布内容可能引用）。
3. **结构设定 Info**：零选择电影段 / 伊芙零反馈 / 三选一机制 / 温蔓青 66666 不回收 等「已共识」块已提取，供 chapter-structurer 分节与节奏控制使用。
4. 跳江衔接三件套（跳江挤入 / 跳江BE / 跳江选择）为图中存量，本次只补边：跳江选择 -option{再想想}-> 姐姐来电（旧边 option→跳江BE、presents 均在图中）。

## 导入

```bash
python .claude/scripts/cypher_exec.py -f 01_叙事数据/csv/import.cypher --multi
```
