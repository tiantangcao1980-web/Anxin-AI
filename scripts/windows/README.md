# Windows 启动器

> 角色：为 Windows 开发者提供 `.bat` 一键脚本，与 Makefile 等价

## 脚本清单

| 脚本 | 等价 Makefile 命令 | 说明 |
|---|---|---|
| `setup.bat` | `make init` | 初始化开发环境 |
| `start-dev.bat` | `make dev` | 启动开发环境 |
| `start-all.bat` | `make up` | 启动全栈 |
| `start-mcp.bat` | — | 启动 MCP 服务 |
| `healthcheck.bat` | `make health` | 健康检查 |
| `deploy-infrastructure.bat` | — | 部署基础设施 |
| `build-release.bat` | `make tauri-build` | 桌面 Release 构建 |

## 使用建议

- **macOS / Linux 开发者**：优先用 `make` 命令
- **Windows 开发者**：用本目录 `.bat` 等价
- **CI**：用 Makefile 或直接调底层命令

## 维护

- 新增脚本必须：kebab-case 命名 + 加入本表
- 修改脚本必须保持与 Makefile 同步
- 涉及环境变量改动同步 `.env.example`
