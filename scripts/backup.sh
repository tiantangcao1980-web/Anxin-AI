#!/bin/bash
# -*- coding: utf-8 -*-
# ============================================================
# Anxin AI 安心智能助手 - 数据备份脚本
# 用法: bash scripts/backup.sh
#
# 备份内容：
#   - PostgreSQL: pg_dump 全库导出 (gz)
#   - Redis:       BGSAVE 后拷贝 dump.rdb
#   - MinIO:       mc mirror 实际对象数据（而非仅文件列表 — S3.4）
# ============================================================

set -euo pipefail

# flock 互斥锁，防止并发备份
LOCK_FILE="/tmp/anxin-backup.lock"
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "错误: 另一个备份进程正在运行，退出。"
    exit 1
fi
trap 'flock -u 200 2>/dev/null || true; rm -f "$LOCK_FILE" 2>/dev/null || true' EXIT

BACKUP_DIR="./backups/$(date +%Y-%m-%d_%H-%M)"
mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "  Anxin AI 安心智能助手 - 数据备份"
echo "  备份目录: $BACKUP_DIR"
echo "=========================================="

# manifest：记录备份产物 + 校验信息，restore.sh 据此校验完整性
MANIFEST="$BACKUP_DIR/manifest.txt"
: > "$MANIFEST"
add_manifest() {
    local file="$1"
    if [ -f "$file" ] || [ -d "$file" ]; then
        local sha
        sha=$(find "$file" -type f -print0 2>/dev/null | sort -z | xargs -0 shasum -a 256 2>/dev/null | shasum -a 256 | awk '{print $1}')
        echo "$(basename "$file")  $(date -u +%FT%TZ)  sha256:$sha" >> "$MANIFEST"
    fi
}

# PostgreSQL 备份
echo ""
echo ">>> 备份 PostgreSQL..."
if docker compose exec -T postgres pg_dump -U postgres --format=custom legal_agent_db \
       | gzip > "$BACKUP_DIR/postgres.dump.gz"; then
    echo "    PostgreSQL 备份完成 ($(du -h "$BACKUP_DIR/postgres.dump.gz" | cut -f1))"
    add_manifest "$BACKUP_DIR/postgres.dump.gz"
else
    echo "    PostgreSQL 备份失败" >&2
    exit 1
fi

# Redis 备份
echo ""
echo ">>> 备份 Redis..."
docker compose exec -T redis redis-cli BGSAVE >/dev/null 2>&1 || true
sleep 2
if docker compose cp redis:/data/dump.rdb "$BACKUP_DIR/redis.rdb" 2>/dev/null; then
    echo "    Redis 备份完成 ($(du -h "$BACKUP_DIR/redis.rdb" | cut -f1))"
    add_manifest "$BACKUP_DIR/redis.rdb"
else
    echo "    Redis 备份跳过（无持久化数据）"
fi

# MinIO 真实对象数据备份 — [S3.4]
echo ""
echo ">>> 备份 MinIO 对象数据 (mc mirror)..."
MINIO_BACKUP_DIR="$BACKUP_DIR/minio"
mkdir -p "$MINIO_BACKUP_DIR"

# 在 minio 容器内 mirror 到挂载点；容器内 /backup 由 docker run -v 挂载
# 这里用 docker compose run 单次执行，避免依赖容器内长期挂载
if docker compose run --rm -T \
        -v "$PWD/$MINIO_BACKUP_DIR:/backup-out" \
        --entrypoint /bin/sh \
        minio -c 'mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null && mc mirror --overwrite --remove local /backup-out' 2>&1 \
        | tail -5; then
    echo "    MinIO 对象数据备份完成 ($(du -sh "$MINIO_BACKUP_DIR" | cut -f1))"
    add_manifest "$MINIO_BACKUP_DIR"
else
    echo "    MinIO 备份失败（容器可能未启动）" >&2
    # 不 exit — pg/redis 已成功也算部分备份
fi

echo ""
echo "=========================================="
echo "  备份完成: $BACKUP_DIR"
echo "=========================================="
ls -lh "$BACKUP_DIR/"
echo ""
echo "manifest:"
cat "$MANIFEST"

# 清理 7 天前的备份
echo ""
echo ">>> 清理 7 天前的备份..."
find ./backups -maxdepth 1 -type d -mtime +7 -name '20*' -exec rm -rf {} + 2>/dev/null || true
echo "    清理完成"
