#!/usr/bin/env bash
# step2_constraints.sh — 全部 21 个 label 建 id 唯一约束（2026-10-12）
# Neo4j DDL 不能在显式事务内执行（cypher_exec --multi 是单显式事务），
# 故逐条经 -c 单语句 auto-commit；IF NOT EXISTS 幂等可重跑。
# 在 Asset 根目录执行：bash 02_剧情数据/Info合并迁移-20261012/step2_constraints.sh
set -e
LABELS="Character Location Spot Info Event Choice Scene SceneLayer CostumeStyle LanguageStyle AppearanceStyle DesignSheet IllusDesign StandingIllustration VoiceDesign Chapter Section SecOutline SecScript BgmTrack LineAudio"
for L in $LABELS; do
  NAME=$(echo "$L" | tr 'A-Z' 'a-z')_id_unique
  echo "== CREATE CONSTRAINT $NAME =="
  python .claude/scripts/cypher_exec.py -c "CREATE CONSTRAINT $NAME IF NOT EXISTS FOR (n:$L) REQUIRE n.id IS UNIQUE" --json
done
echo "== SHOW CONSTRAINTS =="
python .claude/scripts/cypher_exec.py -c "SHOW CONSTRAINTS" --json
