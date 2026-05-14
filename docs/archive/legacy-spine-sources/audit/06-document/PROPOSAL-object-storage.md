# 提案：对象存储抽象层（缺口 A）

> 范围：建立后端统一的 `object_storage_service`，对接 MinIO（本地）/ S3（生产），把所有"应该存文件但没存"的入口收口
> 状态：2026-05-06 已落地第一阶段底座：`local`/`minio` 适配、DocumentService 三入口、ContractService.save_contract_file、029 迁移、7 个对象存储/迁移回归测试
> 前置依赖：任务 0（密钥治理 SOP，MinIO 新凭据可用）
> 下游依赖：任务 5 / 8b / 9 / 10 / 11b 全部走该抽象层

---

## 1. 现状盘点

### 1.1 docker-compose.yml MinIO 服务（已存在）

- 镜像：`minio/minio:RELEASE.2024-12-18T13-15-44Z`，hostname=`minio`
- 命令：`server /data --console-address ":9001"`
- 端口：`expose: 9000 / 9001`（不暴露宿主机，仅内网通信，符合安全护栏）
- 凭据 env：`MINIO_ROOT_USER`（默认 `admin`）/ `MINIO_ROOT_PASSWORD`（默认 `password`）
- 数据卷：`minio_data:/data`
- 健康检查：`mc ready local`
- 后端容器只注入了 `MINIO_ENDPOINT=minio:9000`，未注入 access key / secret key

**结论**：容器跑得起来；后端现在已有 `object_storage_service.py` 可按 `STORAGE_BACKEND=minio` 连接它，生产仍需完成凭据轮换。

### 1.2 backend/src/core/config.py 现状（行 205-210）

```
MINIO_ENDPOINT: str = "localhost:9000"
MINIO_ACCESS_KEY: str = "admin"
MINIO_SECRET_KEY: str = "password"
MINIO_BUCKET: str = "legal-documents"
MINIO_USE_SSL: bool = False
```

- 已有 5 个 MinIO env 字段；2026-05-06 已补 `STORAGE_BACKEND` 与 `STORAGE_LOCAL_PATH`。
- S3 生产适配当前先复用 MinIO/S3-compatible client 思路，尚未引入 boto3/aioboto3 独立后端。
- 缺少 `MINIO_PRESIGNED_URL_TTL` 默认值
- 默认凭据是弱口令 `admin/password`，必须通过任务 0 SOP 替换

### 1.3 项目中"应该存文件但没存"的位置

- ✅ `backend/src/services/document_service.py` —— upload/delete/update_content 已接 `object_storage_service`。
- ✅ `backend/src/services/contract_service.py` —— `save_contract_file` 已写对象存储 key，不再直写 `data/contracts/...`。
- `backend/src/services/document_parser.py / document_export.py / document_generation_service.py` —— 全靠 `file_content: bytes` 流转，没读盘也没写盘
- IM / 尽调 / 案件 / 模板上传 / 桌面同步 / A2UI 工作台导出：底层接口已可用，但这些入口仍需逐项改造与业务测试覆盖

### 1.4 alembic 迁移历史

- `001_initial_schema.py` 起即建立 `documents.file_path String(500) NOT NULL`
- 历经 28 次迁移（`001..027` + `1f5e1455247f`）从未触碰 `file_path` 字段；2026-05-06 新增 `029_document_object_storage`。
- `documents` 与 `document_versions` 已新增 `storage_backend` / `object_key`，`file_path` 保留为过渡字段。
- 老数据全部是 `documents/{org_id}/{timestamp}_{hash8}.{ext}` 格式的"假路径"（实际文件不存在）

---

## 2. 设计：`backend/src/services/object_storage_service.py`

### 2.1 接口（async，最小可用集合）

```python
class ObjectStorageService:
    async def put(
        self, key: str, body: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> str:
        """写入对象，返回 backend 内部 URL（不直接给前端）"""

    async def get(self, key: str) -> bytes:
        """读取对象内容（小文件用；大文件走 stream / presigned）"""

    async def stream(self, key: str) -> AsyncIterator[bytes]:
        """分块流读，给导出/下载大文件用"""

    async def delete(self, key: str) -> None:
        """删除对象（幂等：不存在不报错）"""

    async def exists(self, key: str) -> bool:
        """存在性检查，校验 DB 与存储的一致性时用"""

    async def presigned_url(
        self, key: str, ttl_seconds: int = 3600,
        method: Literal["GET", "PUT"] = "GET",
    ) -> str:
        """生成临时直读/直传 URL，前端文件下载/上传走这里"""

    async def move(self, src_key: str, dst_key: str) -> None:
        """重命名/迁移；version 升级、归档、跨 bucket 迁移用"""
```

### 2.2 双后端 + env 切换

```
STORAGE_BACKEND=local   # Python 默认与 CI 单测兜底（基于 tmp 目录）
STORAGE_BACKEND=minio   # docker-compose / 本地 MinIO / S3-compatible endpoint
```

- `minio` 适配：`minio` python client（`minio>=7.2`），endpoint=`MINIO_ENDPOINT`，bucket=`MINIO_BUCKET`
- `s3` 适配：`boto3` + `aioboto3`，凭据 `S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY / S3_REGION / S3_BUCKET / S3_ENDPOINT_URL`（兼容腾讯云 COS / 阿里云 OSS S3 兼容协议）
- `local` 适配：`STORAGE_LOCAL_ROOT=/tmp/anxin-storage` 的简单文件落盘，仅用于 pytest

工厂函数：
```python
def get_object_storage() -> ObjectStorageService:
    backend = settings.STORAGE_BACKEND
    if backend == "minio": return MinIOAdapter(...)
    if backend == "s3":    return S3Adapter(...)
    if backend == "local": return LocalAdapter(...)
    raise ValueError(...)
```

### 2.3 key 命名规范

```
{entity_type}/{org_id}/{yyyy}/{mm}/{dd}/{hash16}-{slug(name)}{ext}
```

- `entity_type` 枚举：`document` / `contract` / `case` / `due_diligence` / `template` / `im` / `desktop_sync`
- `org_id` 必填（个人租户用 `personal-{user_id}`），保证多租户隔离
- 日期分桶避免单目录百万对象
- `hash16` = sha256 前 16 位，自带去重 hint
- `slug(name)` 限定 ASCII + 连字符，长度 ≤ 64

bucket 策略：先单 bucket（`MINIO_BUCKET=legal-documents`），按 prefix 隔离；后续按租户分 bucket 时只换 prefix → bucket 映射表，接口不变

---

## 3. 数据模型迁移

### 3.1 alembic 迁移（已落地第 29 号迁移）

文件：`backend/alembic/versions/029_add_document_object_storage_fields.py`

```python
def upgrade():
    op.add_column("documents",
        sa.Column("storage_backend", sa.String(16), nullable=True))
    op.add_column("documents",
        sa.Column("object_key", sa.String(1024), nullable=True))
    op.create_index("ix_documents_object_key", "documents", ["object_key"])

    op.add_column("document_versions",
        sa.Column("storage_backend", sa.String(16), nullable=True))
    op.add_column("document_versions",
        sa.Column("object_key", sa.String(1024), nullable=True))

def downgrade():
    op.drop_index("ix_documents_object_key", table_name="documents")
    op.drop_column("documents", "object_key")
    op.drop_column("documents", "storage_backend")
    op.drop_column("document_versions", "object_key")
    op.drop_column("document_versions", "storage_backend")
```

- 新字段都是 nullable=True，老数据不阻塞
- `storage_backend` 用 String(16) 不用 Enum，避免后续加 backend 又要改 enum
- 不删 `file_path`（双写过渡期保留，过渡完成后再发起独立的 dropping migration）
- 本地 SQLite + Postgres 各跑一遍 upgrade / downgrade

### 3.2 双写过渡期（4 阶段，至少 14 天）

| 阶段 | 时长 | 写路径 | 读路径 |
|---|---|---|---|
| 阶段 1 | Day 1-3 | `file_path`（保留旧逻辑）+ `object_key`（写真实存储） | 优先 `file_path`，回退 `object_key` |
| 阶段 2 | Day 4-7 | 同上 | 优先 `object_key`，回退 `file_path`，差异打日志 |
| 阶段 3 | Day 8-10 | 同上 | 同阶段 2 + 跑 backfill 脚本对老数据补 `object_key`（按 `file_path` 内容补落盘） |
| 阶段 4 | Day 11+ | 仅 `object_key` | 仅 `object_key` |

- 任意阶段都给出回滚开关（env：`STORAGE_TRANSITION_PHASE=1|2|3|4`）
- Day 7 / Day 10 各做一次"DB 行数 vs MinIO 对象数"抽样比对

---

## 4. 影响模块清单（必须切换的）

| 模块 | 文件 | 当前状态 | 切换动作 |
|---|---|---|---|
| 文档主入口 | `backend/src/services/document_service.py` | ✅ 已接入 | 继续补真实 MinIO 集成测试 |
| 合同 | `backend/src/services/contract_service.py:351-373` | `open(...)` 写本地 `data/contracts` | 改为 `object_storage.put`，key=`contract/{org}/...` |
| IM 文件消息 | `backend/src/services/im_service.py` | 当前无文件落盘逻辑 | 新增 attachment 上传走 `presigned_url(method=PUT)` 直传 |
| 尽调 | `backend/src/services/due_diligence_service.py` | 报告生成完留 bytes | 接 `object_storage.put`，key=`due_diligence/...` |
| 案件证据 | `backend/src/services/case_service.py` | 现无证据上传链路 | 通过 document_service 间接接（不直连） |
| 模板上传 | `backend/src/services/template_engine.py` | 无落盘 | 间接走 document_service |
| 桌面同步 | `desktop/src/services/sync_engine.rs` | 任务 11b 处理 | 提供 `/api/v1/sync/file/presign` 接口给桌面端，让桌面直传 MinIO |
| A2UI 导出 | `backend/src/services/a2ui_*` | 导出 PDF/Markdown | 走 document_service |

**注意**：第一阶段已交付 `object_storage_service` + DocumentService 三入口 + ContractService.save_contract_file。其他模块的"切换"由各自任务（5/8b/9/10/11b）负责，但**接口契约（put/get/delete/presigned_url）冻结在本任务**

---

## 5. 测试方案

### 5.1 单元测试（pytest，至少 5 个 case）

1. ✅ `test_local_object_storage_put_get_delete_roundtrip` —— Local 适配器 put/get/delete 二进制一致。
2. ✅ `test_local_object_storage_rejects_path_traversal` —— 防止对象 key 逃逸本地根目录。
3. ✅ `test_document_upload_writes_object_storage` —— 上传文档后 DB 与对象内容一致。
4. ✅ `test_document_content_update_preserves_versions_in_storage` —— 新版本写新对象，旧版本仍可读。
5. ✅ `test_document_delete_removes_current_and_version_objects` —— 删除文档同步删除当前与历史版本对象。
6. ✅ `test_contract_save_file_writes_object_storage` —— 合同保存写入统一对象存储。
7. 待补：MinIO mock/容器 roundtrip 与 presigned URL TTL。

### 5.2 集成测试（pytest + 真 MinIO 容器）

6. `test_document_upload_e2e` —— 上传 1MB PDF → DB 行落地 → MinIO 控制台肉眼可见
7. `test_document_delete_e2e` —— 删除文档 → MinIO 对象消失
8. `test_double_write_consistency` —— 阶段 2 双写一致性校验

### 5.3 E2E（Playwright，至少 1 个）

9. 用户上传 PDF → 在文档列表可见 → 点击下载（走 presigned url）→ 文件内容 hash 与原文件一致

### 5.4 性能基线

- 100MB 文件上传 P95 < 10s（局域网 MinIO）
- 500 页 PDF 流式导出，进程内存峰值 < 500MB

---

## 6. 工时估算

| 任务 | 工时 |
|---|---|
| `object_storage_service.py` + 双适配器 + 工厂 | 0.5 天 |
| 9 个测试用例（5 单元 + 3 集成 + 1 E2E） | 1 天 |
| alembic 028 迁移 + 升降级双向跑通 | 0.5 天 |
| document_service 三入口切换 + 合同保存切换 | ✅ 已完成 |
| contract_service.save_contract_file 切换 | 0.25 天 |
| backfill 脚本（老 file_path 补 object_key） | 0.5 天 |
| 配置 + docker-compose 接入 + 文档 | 0.25 天 |
| 联调 + 性能基线 + bug 修 | 0.5 天 |
| **合计** | **4 天** |

（与 TASK-06 估的 4-5 天对齐，对象存储抽象层占其中 4 天）

---

## 7. 风险护栏

- **凭据**：MinIO `admin/password` 是公开默认值，**必须**走任务 0 SOP 后的"新凭据"，写入 `.env`，禁止入 git；S3 凭据用 IAM Role 或 STS 临时密钥，禁止长期 access key 入 git
- **双写过渡期**：至少 14 天（高于横切缺口文档建议的 7 天，因为本系统已无文件，全是新写），**禁止 big-bang**
- **alembic 迁移**：`upgrade` + `downgrade` 双向脚本必须给齐；本地 SQLite + Postgres 各跑一遍；生产前先在 staging 灰度
- **前置依赖**：本提案是任务 5（合同附件）/ 8b（案件证据）/ 9（尽调报告）/ 10（IM 文件消息）/ 11b（桌面同步文件）的前置依赖。**该抽象层未交付前，下游任务不得用 mock 实现绕过**
- **接口契约冻结**：`put/get/delete/presigned_url/move/stream/exists` 七个方法签名一旦合并进 main 即冻结；下游任务只许调，不许改
- **bucket 策略**：单 bucket + prefix 隔离起步；当某租户对象数 > 100 万时再考虑分 bucket，不在 v1 范围内
- **大文件上限**：MAX_UPLOAD_SIZE 当前 10MB（config.py:84），**保留**；超出走 presigned_url(PUT) 客户端直传，不经过后端进程
- **observability**：put / get / delete 三个核心方法接 prometheus 指标 `storage_op_total{op,backend,result}` + 耗时 histogram，便于切 S3 时观察回归
- **回滚预案**：阶段 2 / 3 出问题 → 把 `STORAGE_TRANSITION_PHASE` 调回阶段 1 即可，DB 与存储双写已经在跑，不会丢数据

---

## 8. 非范围（明确说不做的）

- 不做 CDN 接入（生产再加）
- 不做对象生命周期策略（冷热分层、过期删除）
- 不做病毒扫描 / DLP 内容过滤（任务 9 / 安全任务负责）
- 不做客户端加密（数据落地默认信任 MinIO/S3 自身加密）
- 不改 `MAX_UPLOAD_SIZE`（沿用现有 10MB）
- 不接 task 11b 的桌面端 SQLite 同步逻辑（仅暴露 presign 接口契约）

---

> 待评审项：
> 1. 是否同意采用 `STORAGE_BACKEND` env 切换 + 三适配器（minio/s3/local）方案？
> 2. 是否同意 alembic 028 加 `storage_backend` + `object_key` 字段，保留 `file_path` 进入双写过渡？
> 3. 是否同意双写过渡期定为 14 天（而非缺口文档默认的 7 天）？
> 4. 接口契约冻结清单（§2.1 七个方法）是否需要再加 `copy` / `list_keys` 等方法？
