#!/bin/bash
# -*- coding: utf-8 -*-
# ============================================================
# 安心智能助手 - 数据备份脚本
# 用法: bash scripts/backup.sh
# ============================================================

set -euo pipefail

# flock 互斥锁，防止并发备份
LOCK_FILE="/tmp/anxin-backup.lock"
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "错误: 另一个备份进程正在运行，退出。"
    exit 1
fi

BACKUP_DIR="./backups/$(date +%Y-%m-%d_%H-%M)"
mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "  安心智能助手 - 数据备份"
echo "  备份目录: $BACKUP_DIR"
echo "=========================================="

# PostgreSQL 备份
echo ""
echo ">>> 备份 PostgreSQL..."
if docker compose exec -T postgres pg_dump -U postgres legal_agent_db | gzip > "$BACKUP_DIR/postgres.sql.gz"; then
    echo "    PostgreSQL 备份完成"
else
    echo "    PostgreSQL 备份失败"
fi

# Redis 备份
echo ""
echo ">>> 备份 Redis..."
docker compose exec -T redis redis-cli BGSAVE >/dev/null 2>&1 || true
sleep 2
if docker compose cp redis:/data/dump.rdb "$BACKUP_DIR/redis.rdb" 2>/dev/null; then
    echo "    Redis 备份完成"
else
    echo "    Redis 备份跳过（无持久化数据）"
fi

# MinIO 文件列表备份
echo ""
echo ">>> 备份 MinIO 文件列表..."
if docker compose exec -T minio mc ls local --recursive > "$BACKUP_DIR/minio_files.txt" 2>/dev/null; then
    echo "    MinIO 文件列表备份完成"
else
    echo "    MinIO 文件列表跳过"
fi

echo ""
echo "=========================================="
echo "  备份完成: $BACKUP_DIR"
echo "=========================================="
ls -lh "$BACKUP_DIR/"

# 清理 7 天前的备份
echo ""
echo ">>> 清理 7 天前的备份..."
find ./backups -maxdepth 1 -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
echo "    清理完成"
