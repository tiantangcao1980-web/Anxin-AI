# 20260315 - AI法务智能体系统 - 项目检查报告

> 检查日期：2026-03-16
> 检查范围：前端（React+TypeScript）、后端（Python FastAPI）、基础设施（Docker Compose）
> 检查依据：产品需求文档 v2026-03-09 + 代码实际状态

---

## 一、项目概况

| 项 | 值 |
|---|---|
| 前端框架 | React 18.2 + TypeScript + Vite 7.3 |
| UI 体系 | Tailwind CSS 3.4 + Radix UI + Shadcn 组件 |
| 状态管理 | Zustand 4.4 + TanStack React Query 5 |
| 后端框架 | Python FastAPI |
| 数据层 | PostgreSQL 15 + Redis 7 + Qdrant + Neo4j 5 + MinIO |
| 部署 | Docker Compose（7 服务） |
| 前端文件数 | 196 个 TypeScript/React 文件 |
| 前端总代码量 | 约 36,000 行 |

---

## 二、当前功能模块 vs PRD 要求对照

### 2.1 现有路由 → PRD 映射

| 现有路由 | 现有页面 | PRD 归属域 | 处置 |
|----------|---------|-----------|------|
| `/chat` | Chat.tsx (2349行) | AI法务 → 智能对话 | ✅ 保留并优化 |
| `/cases` | Cases.tsx | 智能协作 → 案件管理 | ✅ 保留 |
| `/cases/:id` | CaseDetail.tsx | 智能协作 → 案件管理 | ✅ 保留 |
| `/documents` | Documents.tsx | 智能协作 → 智能文档/文件管理 | ✅ 保留并扩展 |
| `/contracts` | Contracts.tsx | 智能协作 → 智能生成 | ✅ 保留 |
| `/contract-review` | ContractReview.tsx | AI法务（对话内调用） | ✅ 保留，可内嵌到对话 |
| `/due-diligence` | DueDiligence.tsx | 信息中心 → 尽职调查 | ✅ 保留并迁移 |
| `/knowledge` | Knowledge.tsx | 法律智库 | ✅ 保留并扩展 |
| `/collaboration` | Collaboration.tsx | 智能协作 → 在线协作 | ✅ 保留 |
| `/dashboard` | Dashboard.tsx | 控制中台（管理视角） | ✅ 保留 |
| `/settings` | Settings.tsx | 系统设置 | ✅ 保留 |
| `/tools` | LegalTools.tsx | ⚠️ 工具聚合页，子功能散落 | 🔄 拆解重分配 |
| `/tax-assets` | TaxAssets.tsx | ❌ 财税管理（PRD明确延期） | 🗑️ 移除 |
| `/sentiment` | Sentiment.tsx | ❌ PRD 未提及独立模块 | 🗑️ 移除 |

### 2.2 PRD 要求但现有缺失的模块

| PRD 模块 | 归属域 | 现状 |
|---------|-------|------|
| 司法资讯 | 信息中心 | ❌ 无对应页面，需新建 |
| 案源管理 | 智能协作 | ❌ 无对应页面，需新建 |
| 律师精英 | 智能协作 | 部分存在（ExperienceCenter.tsx），需独立路由 |
| 司法智库 | 法律智库 | 部分存在（KnowledgeBaseManager.tsx），需独立路由 |
| 司法学院 | 法律智库 | ❌ 无对应页面，需新建 |
| 智慧搜索 | 法律智库 | 部分存在（SmartSearch.tsx），需独立路由 |
| 通知中心 | 通用能力 | 存在组件（NotificationCenter.tsx），需独立路由 |
| 任务中心 | 通用能力 | ❌ 无对应页面，需新建 |

---

## 三、安全问题检查

### 🔴 严重（必须立即修复）

#### S-01: CORS 全开放 + 允许凭证
- **文件**: `backend/src/api/main.py:62-68`
- **现状**: `allow_origins=["*"]` 同时 `allow_credentials=True`
- **风险**: 违反 CORS 规范（浏览器会拒绝），但任何网站仍可发起无凭证跨域请求
- **修复方案**: 改用 `settings.CORS_ORIGINS`（config.py 已定义为 `["http://localhost:3000"]`），生产环境配置实际域名

#### S-02: DEV_MODE 绕过全部认证
- **文件**: `backend/src/core/deps.py:203-212`
- **现状**: `DEV_MODE=true` 时，所有请求无需 Token 直接获得 admin 权限
- **风险**: 如果生产部署时忘记关闭，等于无认证
- **修复方案**: 添加 `ENVIRONMENT != "production"` 双重校验；启动时 ENVIRONMENT=production + DEV_MODE=true 直接报错退出

#### S-03: JWT 密钥为默认值
- **文件**: `backend/src/core/config.py:29`, `.env:272`
- **现状**: `"your-super-secret-jwt-key-change-in-production"`
- **风险**: Token 可被伪造
- **修复方案**: 启动时检测是否为默认值，生产环境拒绝启动

#### S-04: API Key 明文暴露在 .env 中
- **文件**: `.env:19,26,43,54,63,71,96`
- **现状**: 多个 LLM 提供商的 `sk-xxx` 密钥明文写入（包括 Qwen、DeepSeek、GLM、Minimax 等）
- **风险**: .env 文件一旦泄露，所有密钥全部暴露
- **修复方案**: .env 加入 .gitignore；提供 .env.example 替代；生产环境使用 Docker Secrets 或密钥管理服务

#### S-05: 硬编码默认管理员密码
- **文件**: `backend/src/core/database.py:87`
- **现状**: `get_password_hash("admin123")`
- **风险**: 默认凭证可直接登录
- **修复方案**: 初始化后强制首次登录修改密码；或从环境变量读取初始密码

#### S-06: WebSocket Token 传递在 URL 参数中
- **文件**: `frontend/src/lib/api.ts:~1495`
- **现状**: `ws://...?token=${localStorage.getItem('access_token')}`
- **风险**: Token 出现在服务器访问日志、浏览器历史、代理日志
- **修复方案**: 改用 WebSocket 首条消息传递 Token，或使用 `Sec-WebSocket-Protocol` 头

#### S-07: WebSocket 端 Token 验证未实现
- **文件**: `backend/src/api/routes/collaboration_ws.py:61`
- **现状**: `# TODO: 验证 token 获取用户信息` + `pass`
- **风险**: 任何人可匿名接入协作 WebSocket
- **修复方案**: 实现 Token 验证逻辑

### 🟠 高危

#### S-08: Token 存储在 localStorage
- **文件**: `frontend/src/lib/api.ts:21,40-41`
- **现状**: `localStorage.setItem('access_token', token)`
- **风险**: XSS 攻击可直接窃取 Token
- **说明**: 当前阶段可接受，但应作为长期改进项（迁移到 httpOnly Cookie）

#### S-09: 加密失败时 API Key 回退为明文
- **文件**: `backend/src/services/llm_service.py:62-64`
- **现状**: `except Exception: return api_key`（加密失败直接返回明文）
- **修复方案**: 加密失败应抛出异常，不允许明文回退

#### S-10: 数据库密码硬编码在 docker-compose.yml
- **文件**: `docker-compose.yml:57,110,129`
- **现状**: `POSTGRES_PASSWORD: password`、`NEO4J_AUTH: neo4j/password`、`MINIO_ROOT_PASSWORD: password`
- **修复方案**: 使用环境变量 + .env 文件

#### S-11: Docker 镜像未锁定版本
- **文件**: `docker-compose.yml:89,119`
- **现状**: `qdrant/qdrant:latest`、`minio/minio:latest`
- **修复方案**: 锁定到具体版本号

#### S-12: index.html 缺少安全头
- **文件**: `frontend/index.html`
- **现状**: 无 CSP、无 X-Frame-Options、无 Referrer-Policy
- **修复方案**: 添加 meta 标签或通过 nginx 配置

---

## 四、前端问题检查

### 4.1 性能问题

#### P-01: 所有页面同步导入，无路由懒加载
- **文件**: `frontend/src/App.tsx:1-17`
- **现状**: 15 个页面全部静态 import，首屏加载全部代码
- **影响**: 首屏 bundle 体积过大，尤其是引入了 three.js（3D图形）、reactflow、tiptap 等重型库
- **修复方案**: 使用 `React.lazy()` + `Suspense` 按需加载

#### P-02: Chat.tsx 单文件 2349 行
- **文件**: `frontend/src/pages/Chat.tsx`
- **现状**: 消息渲染、文件上传、WebSocket、侧边栏、Canvas 编辑全在一个文件
- **影响**: 维护困难，任何修改触发整个组件重新渲染
- **修复方案**: 拆分为 ChatPage（容器）+ ChatMessageList + ChatInputArea + ChatSidebar 等子组件

#### P-03: SigningWorkflow.tsx 50KB 单文件
- **文件**: `frontend/src/components/chat/SigningWorkflow.tsx`
- **影响**: 同 P-02
- **修复方案**: 按签署流程步骤拆分子组件

#### P-04: 3D 可视化库未做代码分割
- **现状**: `react-force-graph-3d`、`three`、`three-spritetext` 全量打包
- **影响**: 仅知识图谱页面使用，但所有页面都要加载
- **修复方案**: 对 KnowledgeGraphExplorer 使用 `React.lazy()` 动态导入

#### P-05: 缺少列表虚拟化
- **现状**: 对话列表、案件列表无虚拟滚动
- **影响**: 数据量大时页面卡顿
- **修复方案**: 引入 `@tanstack/react-virtual` 或 `react-window`

### 4.2 架构问题

#### A-01: Zustand Store 单片过大
- **文件**: `frontend/src/lib/store.ts`（20KB+）
- **现状**: 一个 Store 管理 40+ 状态（聊天、工作区、签署、律师面板混在一起）
- **修复方案**: 拆分为 `useChatStore`、`useWorkspaceStore`、`useSigningStore` 等

#### A-02: API 层单文件 49KB
- **文件**: `frontend/src/lib/api.ts`（1500+ 行）
- **现状**: 所有 API 命名空间混在一个文件
- **修复方案**: 按业务域拆分为 `api/auth.ts`、`api/chat.ts`、`api/cases.ts` 等

#### A-03: 缺少全局 Error Boundary
- **文件**: `frontend/src/App.tsx`
- **现状**: 任何子组件 JS 报错会导致整个应用白屏
- **修复方案**: 在 App.tsx 中添加 ErrorBoundary 组件

#### A-04: 缺少 404 页面
- **文件**: `frontend/src/App.tsx:25-43`
- **现状**: 未匹配的路由无兜底处理
- **修复方案**: 添加 `<Route path="*" element={<NotFound />} />`

### 4.3 UI/UX 问题

#### U-01: 图标体系不统一
- **现状**: 使用 lucide-react（SVG 组件），但部分页面内嵌了 Lottie 动画图标，以及硬编码的 emoji
- **问题**: 图标风格不一致，部分 Lottie 图标有蓝紫色渐变的 "AI 味"
- **修复方案**: 统一使用 Heroicons（@heroicons/react）SVG 图标库，移除 lucide-react 和 Lottie 装饰性图标

#### U-02: 导航结构与 PRD 四大业务域不匹配
- **现状**: 5 个平铺导航项（智能对话、尽职调查、案件管理、智能文档、知识中心）
- **PRD 要求**: AI法务、智能协作、信息中心、法律智库 四大业务域
- **修复方案**: 重构为四大域分组导航，每域下含子模块

#### U-03: 移动端适配不完善
- **现状**: Layout.tsx 有基础移动端菜单，但内页无响应式适配
- **修复方案**: 对 Chat、Cases、Documents 等核心页面添加移动端布局

#### U-04: 缺少统一设计规范文件
- **现状**: 没有设计 Token 文档，各组件样式各自定义
- **修复方案**: 创建 `design-tokens.ts` 统一间距、圆角、阴影、颜色规范

### 4.4 废弃依赖

#### D-01: axios 声明但从未使用
- **文件**: `frontend/package.json:53`
- **修复**: `npm uninstall axios`

#### D-02: lottie-react 建议移除
- **用途**: 仅用于装饰性动画图标
- **修复**: 移除依赖，用 SVG 图标替代

#### D-03: framer-motion 与 motion 重复
- **文件**: `package.json:59,63`
- **现状**: 同时安装了 `framer-motion@^10.18.0` 和 `motion@^12.27.1`
- **修复**: 统一使用一个，移除另一个

### 4.5 TypeScript 配置

#### T-01: 未启用死代码检测
- **文件**: `frontend/tsconfig.json:19-20`
- **现状**: `noUnusedLocals: false`、`noUnusedParameters: false`
- **修复**: 设为 `true`，清理无用代码

---

## 五、后端问题检查

### 5.1 安全问题（已在第三节列出）

### 5.2 代码质量

#### B-01: 异常信息直接返回客户端
- **文件**: 多处路由（auth.py、mcp_routes.py、contracts.py 等）
- **现状**: `detail=str(e)` 将堆栈信息暴露给前端
- **修复方案**: 生产环境返回统一错误码，日志记录详细异常

#### B-02: 裸 except 吞掉异常
- **文件**: `backend/src/api/routes/collaboration_ws.py:199`
- **现状**: `except: pass`
- **修复方案**: 至少 `except Exception as e: logger.warning(...)`

#### B-03: CORS 配置与 config.py 定义不一致
- **文件**: `main.py:64` vs `config.py:46`
- **现状**: config.py 定义了 `CORS_ORIGINS = ["http://localhost:3000"]`，但 main.py 硬编码为 `"*"`
- **修复方案**: 使用 `settings.CORS_ORIGINS`

#### B-04: 无请求限流中间件
- **现状**: config.py 定义了限流配置（`RATE_LIMIT_PER_MINUTE=60`），但 main.py 未注册限流中间件
- **修复方案**: 添加 SlowAPI 或自定义限流中间件

---

## 六、基础设施问题

#### I-01: 所有服务密码为 "password"
- **文件**: `docker-compose.yml`
- **涉及**: PostgreSQL、Neo4j、MinIO
- **修复**: 使用环境变量 + .env 文件

#### I-02: Qdrant 和 MinIO 使用 latest 标签
- **风险**: 自动升级可能导致不兼容
- **修复**: 锁定版本（如 `qdrant/qdrant:v1.7.4`、`minio/minio:RELEASE.2024-01-05T22-17-24Z`）

#### I-03: 前端 Docker 镜像可能以 root 运行
- **文件**: `frontend/Dockerfile`（如果使用 nginx 基础镜像）
- **修复**: 添加 `USER nginx` 或创建非 root 用户

#### I-04: 缺少健康检查
- **现状**: postgres 和 redis 有 healthcheck，但 qdrant、neo4j、minio 没有
- **修复**: 为所有服务添加 healthcheck

---

## 七、问题汇总统计

| 严重级别 | 数量 | 类型 |
|---------|------|------|
| 🔴 严重 | 7 | 安全漏洞 |
| 🟠 高危 | 5 | 安全隐患 |
| 🟡 性能 | 5 | 前端性能 |
| 🟡 架构 | 4 | 代码架构 |
| 🟡 UI/UX | 4 | 界面交互 |
| 🔵 依赖 | 3 | 废弃/重复依赖 |
| 🔵 配置 | 1 | TypeScript 配置 |
| 🔵 后端 | 4 | 代码质量 |
| 🔵 基设 | 4 | Docker/部署 |
| **合计** | **37** | |

---

## 八、修复优先级建议

1. **立即修复（上线阻塞）**: S-01 ~ S-07（7项安全严重问题）
2. **高优先（本周内）**: S-08 ~ S-12 + B-01 ~ B-04（9项高危+后端质量）
3. **中优先（两周内）**: P-01 ~ P-05 + A-01 ~ A-04（9项性能+架构）
4. **按计划推进**: U-01 ~ U-04 + D-01 ~ D-03 + T-01 + I-01 ~ I-04（12项UI+依赖+基设）

> 详细修复方案和执行计划见：《20260315-AILegalAgent-维护升级开发计划.md》
