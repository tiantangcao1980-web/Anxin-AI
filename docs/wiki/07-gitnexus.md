# GitNexus 使用说明

## 当前状态

仓库已存在可用 GitNexus 索引：

```text
.gitnexus/
```

索引信息：

| 项 | 值 |
|---|---|
| repo | `Anxin-Smart-Legal-Services` |
| indexed commit | `b01122d` |
| files | 1181 |
| nodes | 30003 |
| edges | 54587 |
| clusters | 1028 |
| processes | 300 |
| embeddings | 28219 |

当前索引已有结构图和 embeddings，`npx -y gitnexus@latest status` 可确认 up-to-date；direct rc binary 的 `context/query/cypher` 已通过 smoke，repo-scoped `query --repo Anxin-Smart-Legal-Services` 在支付 webhook、桌面 SQLCipher/keyring、移动/小程序 refresh-token 场景下均显示 vector/BM25 路径可读。2026-05-06 已确认 `.env` 中的 OpenAI-compatible embedding endpoint 可返回 1024 维向量，并通过 `GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus` 完成主仓 embedding 生成。

2026-05-07 MCP 侧补充验证：`gitnexus/list_repos` 可返回本仓 `28219` embeddings 和正确 indexed commit；`gitnexus/query` 与 `gitnexus/detect_changes` 在本次 Codex MCP 会话中返回 `Transport closed`，因此发布证据仍以 direct CLI 结果为准，MCP query/detect 只作为工具层待复核项。

## 启动 Web UI

```bash
cd /Users/pengchengkeji/Documents/GitHub/Anxin-Smart-Legal-Services
npx -y gitnexus@latest serve -p 4747
```

浏览器访问：

```text
http://localhost:4747
```

## 查看索引状态

```bash
npx -y gitnexus@latest status
```

期望看到：

```text
Status: up-to-date
```

## 常用查询

查看符号上下文：

```bash
/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus context -r Anxin-Smart-Legal-Services ContractService
/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus context -r Anxin-Smart-Legal-Services ProtectedRoute
/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus context -r Anxin-Smart-Legal-Services getTokenStorage
```

查看影响面：

```bash
/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus impact -r Anxin-Smart-Legal-Services ContractService
```

查看当前改动影响：

```bash
/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus detect-changes -r Anxin-Smart-Legal-Services --scope all
```

2026-05-07 当前 dirty worktree 影响面：

```text
Changes: 380 files, 6037 symbols
Affected processes: 240
Risk level: critical
```

该结果说明 GitNexus 只能作为索引和影响面导航；发布前必须整理提交交付文件，然后重跑索引和商业门禁。

## 生成 GitNexus 官方 Wiki

GitNexus CLI 的 wiki 生成支持：

- `--provider openai`
- `--provider cursor`

不支持直接使用 Codex App 作为 provider。

OpenAI：

```bash
npx -y gitnexus@latest wiki --provider openai --api-key "你的真实 OpenAI API Key"
```

Cursor：

```bash
npx -y gitnexus@latest wiki --provider cursor --model Auto
```

如果 Cursor 报 workspace trust：

```bash
agent
```

在交互中选择 trust 当前 workspace。

如果 Cursor 免费计划报 named model unavailable，尝试：

```bash
npx -y gitnexus@latest wiki --provider cursor --model auto
```

若仍失败，使用 OpenAI key，或继续维护本 `docs/wiki/`。

## WAL corrupted 修复

常见报错：

```text
Error: Runtime exception: Corrupted wal file. Read out invalid WAL record type.
```

处理步骤：

```bash
cd /Users/pengchengkeji/Documents/GitHub/Anxin-Smart-Legal-Services
pkill -f "gitnexus.*analyze" || true
pkill -f "gitnexus.*wiki" || true
pkill -f "gitnexus.*serve" || true
STAMP=$(date +%Y%m%d-%H%M%S)
mv .gitnexus ".gitnexus.corrupt-${STAMP}"
cp -R .gitnexus.backup-20260506-091041 .gitnexus
npx -y gitnexus@latest status
```

然后重新启动：

```bash
npx -y gitnexus@latest serve -p 4747
```

## 重建索引

默认只重建结构图：

```bash
bash scripts/gitnexus-index.sh
```

显式启用 embeddings（当前使用 release candidate）：

```bash
GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus \
bash scripts/gitnexus-index.sh --embeddings
```

`--embeddings` 会先运行一个极小临时仓库 preflight，验证当前 GitNexus + LadybugDB + embedding endpoint 能否完成 `CodeEmbedding` 写入和 `CREATE_VECTOR_INDEX`。稳定版 `gitnexus@latest` 在本机仍会触发 LadybugDB HNSW 原生崩溃；direct rc binary 已通过 preflight、生成主仓 `28219` 条 embedding rows，并通过 `cypher` 真实计数。

## 已知限制

- 当前索引停在 commit `b01122d`，很多未提交新符号未必进入图谱。
- 当前 dirty worktree 的 `detect-changes --scope all` 风险为 critical，发布前必须提交后重建/复验索引。
- Codex MCP `list_repos` 可用，但本次会话中 `query/detect_changes` transport closed；需要 query/detect 时优先用 direct CLI。
- `shape_check` 当前没有可用 route shape 结果。
- 自然语言 `query` 对部分中文/业务概念可能返回空。
- JSX 使用关系不完整，前端组件影响分析必须配合 `rg`。
- 新增文件和未提交文件要用 `rg`、源码阅读和测试补盲。
- embeddings 当前已生成；direct rc binary 的读取型 CLI（`context/query/cypher`）已可用。`npx gitnexus@rc` wrapper 仍可能触发 npm/arborist rebuild bug，优先使用上面的绝对路径。
