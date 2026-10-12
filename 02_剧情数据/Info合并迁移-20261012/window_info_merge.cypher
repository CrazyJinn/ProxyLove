// window_info_merge.cypher — label 合并 + title 统一（单事务；2026-10-12；幂等可重跑）
// 前置：window_prune.cypher 已执行（或图上本就无 Day 11+ 节点——重跑场景，如快照恢复后补附加 label）。

// 1/4 Choice：name → title（仅 title 缺失且 name 存在时；剪枝后仅剩「跳江选择」）
MATCH (c:Choice) WHERE c.title IS NULL AND c.name IS NOT NULL
SET c.title = c.name;

// 2/4 Choice：REMOVE name（属性不存在时 REMOVE 为 no-op，天然幂等）
MATCH (c:Choice) WHERE c.name IS NOT NULL
REMOVE c.name;

// 3/4 Event 补基础 label :Info（纯元数据操作）
MATCH (e:Event) WHERE NOT e:Info
SET e:Info;

// 4/4 Choice 补基础 label :Info
MATCH (c:Choice) WHERE NOT c:Info
SET c:Info;
