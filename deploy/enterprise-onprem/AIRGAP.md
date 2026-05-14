# 离线 / 完全断网部署（AirGap）

> 适用：物理隔离网络（政府机要 / 军工 / 银行核心）
> 关联：[`README.md`](./README.md) · [docs/v3/enterprise-cluster-design.md §5.2](../../docs/v3/enterprise-cluster-design.md)

## 关键约束

```
ENVIRONMENT=production
AIRGAP=true
```

`AIRGAP=true` 时后端代码层做以下兜底：

- 关闭 Sentry / 远端遥测
- 关闭 OTA 更新检查
- 不主动访问任何公网 URL（PyPI、HuggingFace、OpenAI、GitHub）
- Skill manifest 下载 → 仅允许本地路径 / 内网镜像

## 1. 镜像离线打包

在有网环境：

```bash
# 拉所有依赖镜像
docker pull ghcr.io/anxin/legal-backend:latest
docker pull postgres:16-alpine
docker pull redis:7-alpine
docker pull minio/minio:latest
docker pull nginx:1.27-alpine

# 打包
docker save \
  ghcr.io/anxin/legal-backend:latest \
  postgres:16-alpine redis:7-alpine \
  minio/minio:latest nginx:1.27-alpine \
  | gzip > anxin-onprem-images.tar.gz
```

在断网环境：

```bash
gunzip -c anxin-onprem-images.tar.gz | docker load
```

## 2. 模型离线包

```
models/
├── qwen2.5-72b-instruct/        # 主 LLM
│   ├── config.json
│   ├── tokenizer.json
│   └── pytorch_model-*.safetensors
├── bge-large-zh-v1.5/           # Embedding
└── reranker-large/              # Rerank（可选）
```

部署方式：

- 用 [vllm](https://github.com/vllm-project/vllm) 或客户已有的推理框架起本地 endpoint
- `.env` 中 `LLM_BASE_URL=http://your-local-llm:8000/v1`

## 3. Python 依赖离线

```bash
# 有网环境
pip download -r backend/requirements.txt -d ./wheels
tar -czf anxin-wheels.tar.gz ./wheels

# 断网环境
tar -xzf anxin-wheels.tar.gz
pip install --no-index --find-links=./wheels -r requirements.txt
```

或更推荐：**用预构建好的容器镜像**（上一节），跳过此步。

## 4. Skill 包离线分发

第三方 / 用户自定义 skill：

```
skills-bundle/
├── manifest.json     # 校验和、签名信息
├── office/
│   ├── docx/SKILL.md + code/
│   └── ...
└── PUBLIC_KEYS.txt   # publisher 公钥列表
```

部署：

```bash
# 解压到挂载目录（compose.onprem.yml 的 ./data/skills）
tar -xzf skills-bundle.tar.gz -C deploy/enterprise-onprem/data/skills/

# 注册公钥到 env
echo "SKILL_SANDBOX_PUBLISHER_KEYS=anxin-platform=<base64>,partner-x=<base64>" >> .env

# 重启 backend，registry 会热加载 SKILL.md
docker compose restart backend
```

T1 skill 在签名校验失败时**直接拒绝执行**（fail-closed）。

## 5. 时间同步

断网环境必须：

- 内网部署 chrony / ntpd
- 强制 TLS 证书校验时间窗 ≥ 1 年缓冲
- JWT 时钟偏移容忍设为 ±5min（已在 `core/security.py`）

## 6. 验收清单

- [ ] 拔网线后所有 docker compose 服务可独立启动
- [ ] `curl https://your-internal-domain/api/v1/health` 返回 200
- [ ] 用户登录走 LDAP，AI 对话走本地 LLM
- [ ] 完整跑通一次 skill 沙箱执行（T2 subprocess）
- [ ] 没有任何 `outbound connection: blocked` 日志
- [ ] `/api/v1/metrics` Prometheus 抓取正常
