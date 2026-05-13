# 代码风格规范

> 强制规范。各语言遵守对应工具链 + 项目补充约定。

## 1. Python（backend/）

### 工具链

| 工具 | 用途 | 配置 |
|---|---|---|
| `ruff` | Lint + 格式化 | `pyproject.toml` |
| `mypy` | 类型检查 | `pyproject.toml` |
| `pytest` | 测试 | `pytest.ini` |
| `black` | 格式化（被 ruff 替代） | — |

### 强制规则

- **Python 3.11+** 语法
- **类型注解**：函数签名 + 公共 API 必须有类型
- **异步**：FastAPI 路由必须 `async def`，IO 一律 await
- **ORM**：`AsyncSession`，禁止同步 Session 进 async 上下文
- **错误**：业务异常继承 `services/exceptions.py`，由全局 handler 转 UnifiedResponse
- **日志**：`from loguru import logger`，禁止 `print`
- **配置**：`pydantic-settings`，集中在 `core/config.py`，禁止业务代码 `os.getenv`
- **导入顺序**：stdlib → 第三方 → 本项目（ruff 自动）

### 命名

按 [naming-convention.md §4](./naming-convention.md#4-代码符号)：snake_case 函数、PascalCase 类、UPPER_SNAKE 常量。

### 测试

- 单元：`backend/tests/unit/`
- 集成：`backend/tests/integration/`
- E2E：`backend/tests/e2e/`
- 命名：`test_<被测>_<场景>_<期望>`
- 必须有 fixture / mock，禁止直连真实外部服务（除非显式 `@pytest.mark.live`）

## 2. TypeScript / React（frontend/ + mobile/ + apps/）

### 工具链

| 工具 | 用途 |
|---|---|
| `eslint` | Lint（`--max-warnings 0`） |
| `tsc` | 类型检查（`tsc --noEmit`） |
| `vitest` | 单元测试 |
| `playwright` | E2E |
| `vite` / `expo` | 构建 |

### 强制规则

- **TypeScript 5.x**，禁止 `any`（业务代码）
- **React 18+ 函数组件**，禁止 Class
- **Hooks**：自定义 hook 命名 `useXxx`
- **状态**：优先 Zustand store，跨树共享用 React Context（仅 Privacy / Theme 两个用 Context）
- **服务端数据**：`@tanstack/react-query` 或自封装 `lib/api.ts`
- **样式**：Tailwind 语义类（`bg-primary`），**禁止**硬编码 `bg-[#xxx]` 或 `text-white`
- **API 调用**：必须走 `frontend/src/lib/api.ts`，不直接 fetch
- **错误**：`toast` / `Sonner` 显示业务错误；技术错误进 console + Sentry

### 命名

- 组件：`PascalCase.tsx`
- Hook：`useXxx.ts`
- 工具：`camelCase.ts`
- Store：`useXxxStore.ts`

## 3. Rust（desktop/）

### 工具链

| 工具 | 用途 |
|---|---|
| `cargo fmt` | 格式化 |
| `cargo clippy --all-targets --all-features` | Lint |
| `cargo test` | 测试 |

### 强制规则

- **Edition 2021**
- **错误处理**：`anyhow::Result` 业务；`thiserror` 定义具名错误
- **异步**：`tokio`
- **IPC 命令**：`#[tauri::command]` 必须显式参数类型
- **不安全代码**：`unsafe` 块必须有注释解释为什么需要

## 4. Shell（scripts/）

### 强制规则

```bash
#!/usr/bin/env bash
set -euo pipefail              # 强制错误传播

# 函数名 snake_case
function do_something() {
  local var_name="$1"
  echo "$var_name"
}

# 主流程
main() {
  do_something "hello"
}

main "$@"
```

- `set -euo pipefail` 强制
- 用 `"$var"` 包裹防止空格 / 通配
- `local` 限定函数变量
- 大型脚本必须有 `--help`

## 5. SQL / Alembic 迁移

- 迁移文件按 `NNN_<topic>.py` 命名（项目现有约定）
- 必须可逆（实现 `downgrade`）
- 大表 schema 变更必须分 N 步：加新列 → 双写 → 数据回填 → 切读 → 删旧列
- 禁止直接 `DROP TABLE` / `ALTER COLUMN TYPE`（先评估）

## 6. 注释与文档

- **默认不写注释**，代码自解释（清晰命名 > 注释）
- 注释解释 **WHY**（为什么这样写），不是 **WHAT**（写了什么）
- 公共 API 必须有 docstring / TSDoc
- TODO / FIXME 必须带 issue 链接：`# TODO(#142): ...`

## 7. 测试覆盖目标

| 模块 | 目标 |
|---|---|
| 核心业务（auth / payment / persona） | ≥ 80% |
| Service 层 | ≥ 70% |
| Route 层 | ≥ 60%（含集成测试） |
| UI 组件 | 关键路径必有 |
| E2E | 主用户旅程必有 |

## 8. 性能基线

- 单接口 P95 < 500 ms（不含 LLM 流式）
- 前端 chunk < 500 KB（vite 警告阈值）
- 数据库 N+1 禁止（用 `selectinload` / `joinedload`）
- Qdrant top_k > 50 必须 rerank

## 9. 安全红线

- **密钥**永不入库；`.env.example` 用占位符
- 用户输入必须**后端校验**（Pydantic）
- SQL 100% 走 ORM
- 文件上传：扩展名 + MIME + 内容三重校验
- LLM 提示词注入：用围栏包裹用户输入

## 10. CI 必跑

每个 PR 必须通过：

| 检查 | 工具 |
|---|---|
| Backend lint | `ruff check` |
| Backend type | `mypy` |
| Backend test | `pytest -q` |
| Frontend lint | `eslint --max-warnings 0` |
| Frontend type | `tsc --noEmit` |
| Frontend test | `vitest run` |
| Frontend build | `vite build` |
| Desktop check | `cargo clippy` + `cargo test` |
| Mobile typecheck | `tsc --noEmit` |
| 安全扫描 | `release-evidence-secret-scan.sh` |
