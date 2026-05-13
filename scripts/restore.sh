#!/bin/bash
# -*- coding: utf-8 -*-
# ============================================================
# 安心智能助手 - 数据恢复脚本
# 用法: bash scripts/restore.sh <备份目录路径>
# ============================================================

set -euo pipefail

BACKUP_DIR="${1:?用法: bash scripts/restore.sh <备份目录路径>}"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "错误: 目录不存在: $BACKUP_DIR"
    exit 1
fi

echo "=========================================="
echo "  安心智能助手 - 数据恢复"
echo "  备份目录: $BACKUP_DIR"
echo "=========================================="
echo ""
echo "  警告: 即将从备份恢复数据，当前数据将被覆盖！"
echo ""
read -p "  确认继续？(y/N): " confirm
if [ "$confirm" != "y" ]; then
    echo "  已取消"
    exit 0
fi

# 恢复 PostgreSQL
if [ -f "$BACKUP_DIR/postgres.sql.gz" ]; then
    echo ""
    echo ">>> 恢复 PostgreSQL..."
    gunzip -c "$BACKUP_DIR/postgres.sql.gz" | docker compose exec -T postgres psql -U postgres legal_agent_db
    echo "    PostgreSQL 恢复完成"
else
    echo ""
    echo ">>> 跳过 PostgreSQL 恢复（备份文件不存在）"
fi

# 恢复 Redis
if [ -f "$BACKUP_DIR/redis.rdb" ]; then
    echo ""
    echo ">>> 恢复 Redis..."
    docker compose cp "$BACKUP_DIR/redis.rdb" redis:/data/dump.rdb
    docker compose restart redis
    echo "    Redis 恢复完成"
else
    echo ""
    echo ">>> 跳过 Redis 恢复（备份文件不存在）"
fi

echo ""
echo "=========================================="
echo "  数据恢复完成"
echo "=========================================="
