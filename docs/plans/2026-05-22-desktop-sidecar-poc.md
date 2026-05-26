# 桌面端嵌入式后端（Sidecar）PoC 方案

> 日期：2026-05-22
> 状态：**调研/规划，未实施**（M5 后启动）
> 配套：[桌面 bootstrap 方案 §3.2](2026-05-22-desktop-bootstrap.md)
> 决策来源：[产品蓝图 §3.1](2026-05-22-product-blueprint.md)（桌面 = 主工作站，需独立可跑）

---

## 1. 目标

让 macOS / Windows / Linux 桌面客户端安装后**无需 Docker / Python / Node** 即可运行，包含：

- 本地 FastAPI 后端（即 `backend/src/api/main.py` 的 sidecar 二进制）
- 必要 worker（Celery / 任务队列）—— 若桌面用得到
- 默认绑定 `127.0.0.1:<random port>`，仅本机访问
- 启动 / 退出由 Tauri 主进程管控（应用退出时 backend 也终止）

---

## 2. 三种打包方案对比

### 方案 A — PyInstaller

| 维度 | 评分 | 备注 |
|---|---|---|
| 实现难度 | ⭐⭐⭐ | 成熟，文档多，社区案例丰富 |
| 包大小 | 150-250 MB | 含 Python 解释器 + 全部依赖（含 SQLAlchemy / Pydantic / FastAPI / Uvicorn / Anthropic / OpenAI 等 SDK） |
| 启动速度 | 3-5 秒 | 解包到临时目录后启动 |
| 兼容性 | ✅ macOS / Windows / Linux | 需各平台分别打包 |
| 维护成本 | 中 | 依赖发版需重新打包，每次 release 跑 3 个平台 |
| 推荐场景 | **推荐** | 我们当前 backend 体量适合此方案 |

```bash
# backend/scripts/build-sidecar.sh
pip install pyinstaller
pyinstaller --onefile \
  --name anxin-backend \
  --add-data "src/prompts:prompts" \
  --add-data "src/migrations:migrations" \
  --hidden-import uvicorn.protocols.http.h11_impl \
  --hidden-import uvicorn.protocols.websockets.websockets_impl \
  src/api/main.py
```

### 方案 B — Nuitka

| 维度 | 评分 | 备注 |
|---|---|---|
| 实现难度 | ⭐⭐ | 编译型，错误诊断难 |
| 包大小 | 100-180 MB | 比 PyInstaller 小 |
| 启动速度 | 1-2 秒 | 真编译，性能最好 |
| 兼容性 | ⚠️ | 部分 C 扩展（如 lxml）需手动 hint |
| 维护成本 | 高 | 编译耗时 10-30 分钟 / 平台 / 架构 |
| 推荐场景 | 性能敏感后期优化 | 不作为首选 |

### 方案 C — 不嵌入 Python，全部走 Rust

| 维度 | 评分 | 备注 |
|---|---|---|
| 实现难度 | ⭐ | 需把 FastAPI 业务全部移植到 Axum / Actix |
| 包大小 | 20-40 MB | 最小 |
| 启动速度 | <100ms | 最快 |
| 兼容性 | ✅ 全平台 | |
| 维护成本 | 极高 | 后端逻辑全部要二次实现 |
| 推荐场景 | 长期理想，但 12 个月内不现实 | **不推荐** |

---

## 3. 推荐路径

**选择方案 A（PyInstaller）+ Tauri externalBin**

### 3.1 步骤

1. **新增 `backend/scripts/build-sidecar.sh`**（按平台/架构生成 `dist/anxin-backend-{target_triple}`）
2. **新增 `backend/sidecar/main_entry.py`**：sidecar 入口，绑定 `127.0.0.1:0`（随机端口）+ 把端口写入 stdout 第一行让 Tauri 读
3. **新增 `desktop/binaries/`** 目录占位（CI 注入对应平台的二进制）
4. **修 `desktop/tauri.conf.json`**：
   ```json
   {
     "bundle": {
       "externalBin": ["binaries/anxin-backend"]
     }
   }
   ```
5. **新增 `desktop/src/services/sidecar.rs`**：启动 sidecar、读端口、写到 `runtime_config.backend_url`、退出时杀进程
6. **修 `desktop/src/lib.rs`**：app `setup` 阶段调 `sidecar::spawn_and_register()`，应用退出时调 `sidecar::shutdown()`

### 3.2 渐进策略

> **不强制所有用户用 sidecar**。`runtime_config.backend_url` 有三种：
> - `sidecar`（默认）→ 启动嵌入式后端
> - `local`（手动配置）→ 用户本机另起 `make backend`
> - `remote`（企业部署）→ 指向公司内网/云端

UI（设置 → 本机运行）让用户选。

### 3.3 CI 流水线

- macOS Intel + Apple Silicon → 1 个 universal 二进制（lipo）
- Windows x64
- Linux x64（glibc 2.31+，AppImage 友好）
- 上传到 GitHub Release，Tauri build 时从 release artifact 下载注入

---

## 4. 已知风险

| 风险 | 缓解 |
|---|---|
| 包体积 +200 MB | 用 `--exclude-module` 砍掉桌面不需要的模块（如 LiveKit / Sentry / Celery worker）；按"桌面必需"裁剪 backend |
| 跨平台兼容 | CI 在 macOS / Windows / Linux 各跑一遍 PyInstaller，并对各平台做 smoke |
| 启动延迟 3-5 秒 | Tauri splash 期间 sidecar 并行启动，用户感知 ≤ 2 秒 |
| Python SDK 版本漂移 | sidecar 与 backend/ 共享 `pyproject.toml`，CI lock 一致 |
| 杀毒软件误报 | Windows 提交 SmartScreen 白名单；macOS 走 Apple notarization |
| 端口冲突 | 用 `:0` 随机端口，Rust 端读 stdout 第一行 |
| sidecar 崩溃 | Rust 端做 healthcheck heartbeat（5s/次），异常时重启 ≤ 3 次，全失败后通知用户切换到 `remote` 模式 |

---

## 5. 验收（DoD）

- [ ] `make backend-sidecar` 生成 `backend/dist/anxin-backend-{triple}`，文件大小 < 300 MB
- [ ] `cd desktop && cargo tauri build` 含 sidecar 注入，dmg 大小增长 ≤ 250 MB
- [ ] 干净 macOS 安装 dmg → 启动 5 秒内可访问 `127.0.0.1:<port>/health`
- [ ] 任务管理器中 `anxin-assistant` 退出时 `anxin-backend` 也退出（无僵尸进程）
- [ ] 设置 → 本机运行 → 显示 sidecar 状态 + 一键切换到 remote
- [ ] Windows / Linux 同样验证

---

## 6. 时间表

| 阶段 | 时长 | 内容 |
|---|---|---|
| **W1** | 1 周 | backend 裁剪 + PyInstaller spec，单平台 PoC（macOS） |
| **W2** | 1 周 | Tauri externalBin + sidecar.rs + healthcheck + 退出钩子 |
| **W3** | 1 周 | Windows / Linux 跨平台 CI |
| **W4** | 1 周 | 真机验收 + dmg/exe/deb 体积治理 + 文档 |

总 4 周。可与 M3-M5 并行（非阻塞 main 进度）。

---

## 7. 启动前置条件

- M3 桌面三栏布局已落地（sidecar 才有用武之地）
- M6 后端 sync 契约已 implement（避免后端持续大改导致 sidecar 频繁重打包）
- 商业证据链不依赖 sidecar（先做 remote 模式打通签名 / 公证 / 跨设备同步证据）

---

## 8. 不做的事

- ❌ 不打包 Celery worker / Redis / Postgres / Qdrant —— 太重；桌面只 sidecar 一个 FastAPI 进程，数据库走本地 SQLCipher
- ❌ 不打包前端到 sidecar（前端走 Tauri webview，与 backend 独立）
- ❌ 不在 sidecar 启动外部模型 —— LLM 调用走 OpenAI / 通义 / Ollama 等 provider；Ollama 本身是单独安装
- ❌ 不强制升级 sidecar Python 版本（保持与 backend/ pyproject.toml 完全一致）

---

## 9. 关联

- 实施方案：[`docs/plans/2026-05-22-implementation-plan.md`](2026-05-22-implementation-plan.md)
- 桌面 bootstrap 方案：[`docs/plans/2026-05-22-desktop-bootstrap.md`](2026-05-22-desktop-bootstrap.md)
- 桌面同步引擎：[`docs/desktop/sync-engine-design.md`](../desktop/sync-engine-design.md)
- 三态模式：[`docs/openspec/00-intelligent-assistant-platform-spec.md`](../openspec/00-intelligent-assistant-platform-spec.md)
