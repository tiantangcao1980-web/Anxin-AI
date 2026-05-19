#!/bin/bash
# -*- coding: utf-8 -*-
# ============================================================
# Anxin AI 安心智能助手 - 数据恢复脚本
# 用法: bash scripts/restore.sh <备份目录路径>
#
# 流程：
#   1. 校验 manifest.txt 存在
#   2. 校验各备份文件 sha256 与 manifest 一致
#   3. 用户确认 → 恢复 PostgreSQL / Redis / MinIO
# ============================================================

set -euo pipefail

BACKUP_DIR="${1:?用法: bash scripts/restore.sh <备份目录路径>}"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "错误: 目录不存在: $BACKUP_DIR"
    exit 1
fi

echo "=========================================="
echo "  Anxin AI 安心智能助手 - 数据恢复"
echo "  备份目录: $BACKUP_DIR"
echo "=========================================="

# ---- [S3.4] manifest 完整性校验 ----
MANIFEST="$BACKUP_DIR/manifest.txt"
if [ ! -f "$MANIFEST" ]; then
    echo "⚠️  未找到 manifest.txt — 这可能是旧格式备份或被篡改，请人工核对。"
    echo "    继续恢复将跳过 sha256 校验。"
else
    echo ""
    echo ">>> 校验 manifest sha256..."
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        local_name=$(echo "$line" | awk '{print $1}')
        expected_sha=$(echo "$line" | awk -F'sha256:' '{print $2}')
        target="$BACKUP_DIR/$local_name"
        if [ -e "$target" ]; then
            actual_sha=$(find "$target" -type f -print0 2>/dev/null | sort -z | xargs -0 shasum -a 256 2>/dev/null | shasum -a 256 | awk '{print $1}')
            if [ "$actual_sha" = "$expected_sha" ]; then
                echo "  ✓ $local_name"
            else
                echo "  ✗ $local_name  sha256 不匹配！"
                echo "    expected: $expected_sha"
                echo "    actual:   $actual_sha"
                exit 2
            fi
        else
            echo "  ⚠️  $local_name 在 manifest 中但文件缺失"
        fi
    done < "$MANIFEST"
    echo "    所有备份文件 sha256 校验通过"
fi

echo ""
echo "  ⚠️  即将从备份恢复数据，当前数据将被覆盖！"
echo ""
read -r -p "  确认继续？(y/N): " confirm
if [ "$confirm" != "y" ]; then
    echo "  已取消"
    exit 0
fi

# 恢复 PostgreSQL — 支持新格式 (custom dump) 与旧格式 (plain SQL)
if [ -f "$BACKUP_DIR/postgres.dump.gz" ]; then
    echo ""
    echo ">>> 恢复 PostgreSQL (custom format)..."
    gunzip -c "$BACKUP_DIR/postgres.dump.gz" \
        | docker compose exec -T postgres pg_restore -U postgres -d legal_agent_db --clean --if-exists
    echo "    PostgreSQL 恢复完成"
elif [ -f "$BACKUP_DIR/postgres.sql.gz" ]; then
    echo ""
    echo ">>> 恢复 PostgreSQL (plain SQL, legacy format)..."
    gunzip -c "$BACKUP_DIR/postgres.sql.gz" \
        | docker compose exec -T postgres psql -U postgres legal_agent_db
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

# 恢复 MinIO 对象数据 — [S3.4]
if [ -d "$BACKUP_DIR/minio" ]; then
    echo ""
    echo ">>> 恢复 MinIO 对象数据 (mc mirror reverse)..."
    docker compose run --rm -T \
        -v "$PWD/$BACKUP_DIR/minio:/backup-in:ro" \
        --entrypoint /bin/sh \
        minio -c 'mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null && mc mirror --overwrite /backup-in local'
    echo "    MinIO 恢复完成"
else
    echo ""
    echo ">>> 跳过 MinIO 恢复（备份目录不存在）"
fi

echo ""
echo "=========================================="
echo "  数据恢复完成"
echo "=========================================="
