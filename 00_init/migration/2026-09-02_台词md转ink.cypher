// 2026-09-02 台词定稿 md→ink 一次性迁移（图侧）
// 文件侧配套：2026-09-02_台词md转ink.py（行内容已逐字转换并 --verify 深相等验证：
// parse_md(md) == parse_ink(ink)，rows 28/22/23 与迁移前图行完全一致）。
// 执行：python .claude/scripts/cypher_exec.py -f 00_init/migration/2026-09-02_台词md转ink.cypher --multi
//
// 只改 script_path 后缀，**不动 status**：三节 sc=11、行全 11、章 JSON 已发布——
// 对齐签名（op+who+text）逐字未变，下次重拆（仅手改后触发）按签名全 keep，
// 零行变更、零重配（对比 2026-08-27 jsonl→md 先例曾置 sc=0 重做——那次行模型
// 变了需重拆，本次行模型零漂移，明确不置）。
MATCH (sc:SecScript)
WHERE sc.script_path ENDS WITH '台词.md'
SET sc.script_path = replace(sc.script_path, '台词.md', '台词.ink');
