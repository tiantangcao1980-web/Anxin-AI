# 20260315 - AI法务智能体系统 - 维护升级开发计划

> 编制日期：2026-03-16
> 基准文档：2026-03-09 PRD + 20260315 检查报告
> 核心原则：**在现有框架内修复和优化，不重构底层框架和交互逻辑**

---

## 一、升级总纲

### 1.1 指导原则

1. **守住底线**：只修复/优化，不重构。现有 React+Vite+Tailwind+Zustand 技术栈完全保留
2. **安全优先**：先堵安全漏洞，再做功能调整
3. **PRD 对齐**：导航结构调整为四大业务域，移除 PRD 明确排除的模块
4. **企业级规范**：统一设计规范、图标体系、交互规范，杜绝 "AI 味" 视觉
5. **渐进式交付**：每个 Phase 独立可验证，不影响其他模块运行

### 1.2 新导航结构（PRD 四大业务域）

```
┌─────────────────────────────────────────────────────┐
│  Logo + 安心AI法务                                     │
├─────────┬───────────┬───────────┬───────────┬───────┤
│ AI法务   │ 智能协作   │ 信息中心   │ 法律智库   │ ···  │
├─────────┴───────────┴───────────┴───────────┴───────┤
│                                                       │
│  AI法务:                                              │
│    ├─ 智能对话      /chat          (现有 Chat.tsx)     │
│    ├─ 合同审查      /contract-review (现有)            │
│    └─ 智能中台      /dashboard     (现有 Dashboard)    │
│                                                       │
│  智能协作:                                            │
│    ├─ 案件管理      /cases         (现有)              │
│    ├─ 文件管理      /documents     (现有)              │
│    ├─ 智能生成      /contracts     (现有 Contracts)    │
│    ├─ 在线协作      /collaboration (现有)              │
│    ├─ 律师精英      /experts       (基于 ExperienceCenter) │
│    └─ 案源管理      /leads         (新建)              │
│                                                       │
│  信息中心:                                            │
│    ├─ 司法资讯      /news          (新建)              │
│    └─ 尽职调查      /due-diligence (现有)              │
│                                                       │
│  法律智库:                                            │
│    ├─ 智慧搜索      /search        (基于 SmartSearch)  │
│    ├─ 知识图谱      /knowledge-graph (基于现有)        │
│    ├─ 司法智库      /knowledge-base  (基于现有)        │
│    └─ 司法学院      /academy       (新建)              │
│                                                       │
│  系统功能（右侧/底栏）:                                │
│    ├─ 通知中心      (已有组件，增强)                    │
│    ├─ 任务中心      (新建)                             │
│    └─ 系统设置      /settings      (现有)              │
└─────────────────────────────────────────────────────┘
```

### 1.3 需要移除的模块

| 模块 | 文件 | 移除原因 |
|------|------|---------|
| 财税资产 | `pages/TaxAssets.tsx` | PRD 明确延期到二期 |
| 舆情监控 | `pages/Sentiment.tsx` | PRD 未包含此独立模块 |
| 法律工具聚合页 | `pages/LegalTools.tsx` | 子功能已分配到各业务域，聚合页不再需要 |
| Chat.new.tsx | `pages/Chat.new.tsx` | 替代实现，与 Chat.tsx 重复 |

### 1.4 执行阶段总览

| Phase | 内容 | 预计工时 | 风险等级 |
|-------|------|---------|---------|
| Phase 0 | 后端安全加固 | 2h | 🔴 高（上线阻塞） |
| Phase 1 | 清理废弃模块与代码 | 1h | 🟢 低 |
| Phase 2 | 导航重构为四大业务域 | 3h | 🟡 中 |
| Phase 3 | 前端性能与质量优化 | 3h | 🟡 中 |
| Phase 4 | UI 规范统一与图标 SVG 化 | 4h | 🟡 中 |
| Phase 5 | 响应式与移动端适配 | 3h | 🟡 中 |
| Phase 6 | 后端稳定性与基础设施加固 | 2h | 🟡 中 |

---

## 二、Phase 0：后端安全加固（上线阻塞项）

> 目标：修复所有 🔴 严重安全问题，确保系统可安全上线

### 0.1 修复 CORS 配置（S-01 + B-03）

**文件**: `backend/src/api/main.py:62-68`

**修复方式**: 将硬编码的 `allow_origins=["*"]` 替换为从 config.py 读取

```python
# 修复前（当前代码）:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 修复后:
# 【说明】使用 settings.CORS_ORIGINS 而非硬编码 "*"
# config.py 已定义 CORS_ORIGINS = ["http://localhost:3000"]
# 生产环境通过 .env 配置实际域名（如 https://app.example.com）
# 这样既修复了 CORS 漏洞，又保持了可配置性
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)
```

### 0.2 修复 DEV_MODE 安全隐患（S-02）

**文件**: `backend/src/core/deps.py:203-212`

**修复方式**: 在 DEV_MODE 检查中增加环境校验

```python
# 修复前:
if settings.DEV_MODE:
    # 直接返回 admin 用户，无任何限制

# 修复后:
# 【说明】增加双重校验：DEV_MODE 只在非 production 环境生效
# 即使有人误将 DEV_MODE=true 部署到生产，也不会绕过认证
if settings.DEV_MODE and settings.ENVIRONMENT != "production":
    logger.warning("⚠️ DEV_MODE 已启用，跳过认证（仅限开发环境）")
    ...
```

**文件**: `backend/src/api/main.py` lifespan 函数中增加启动校验

```python
# 【说明】在应用启动时检查危险配置组合，直接拒绝启动
if settings.ENVIRONMENT == "production" and settings.DEV_MODE:
    raise RuntimeError("❌ 生产环境禁止启用 DEV_MODE！请检查 .env 配置")
```

### 0.3 修复 JWT 默认密钥（S-03）

**文件**: `backend/src/api/main.py` lifespan 函数

```python
# 【说明】启动时检测 JWT 密钥是否为默认值
# 如果是生产环境且使用默认密钥，直接拒绝启动，防止 Token 被伪造
DEFAULT_JWT_KEYS = [
    "your-super-secret-jwt-key-change-in-production",
    "your-super-secret-jwt-key-please-change-in-production",
]
if settings.ENVIRONMENT == "production" and settings.JWT_SECRET_KEY in DEFAULT_JWT_KEYS:
    raise RuntimeError("❌ 生产环境必须设置自定义 JWT_SECRET_KEY！")
```

### 0.4 处理 .env 安全问题（S-04）

**操作**:
1. 创建 `.env.example`（移除所有真实密钥，只保留占位符）
2. 确认 `.gitignore` 包含 `.env`（防止真实密钥进入 git）
3. 在文档中说明生产环境应使用密钥管理服务

### 0.5 修复默认管理员密码（S-05）

**文件**: `backend/src/core/database.py:87`

```python
# 修复前:
hashed_pwd = get_password_hash("admin123")

# 修复后:
# 【说明】从环境变量读取初始管理员密码
# 如果未设置，使用 secrets 模块生成随机密码并在日志中输出（仅首次）
import secrets
initial_password = os.environ.get("ADMIN_INITIAL_PASSWORD")
if not initial_password:
    initial_password = secrets.token_urlsafe(16)
    logger.warning(f"⚠️ 未设置 ADMIN_INITIAL_PASSWORD，已生成随机密码: {initial_password}")
    logger.warning("请立即登录并修改密码！")
hashed_pwd = get_password_hash(initial_password)
```

### 0.6 修复 WebSocket Token 传递方式（S-06 + S-07）

**前端修复** - `frontend/src/lib/api.ts`

```typescript
// 修复前:
// Token 通过 URL 参数传递，会被记录到服务器日志
const wsUrl = `ws://...?token=${localStorage.getItem('access_token')}`

// 修复后:
// 【说明】WebSocket 连接时不在 URL 中传递 Token
// 而是在连接建立后，通过首条消息发送认证信息
// 这样 Token 不会出现在服务器访问日志、浏览器历史中
const ws = new WebSocket(wsUrl)  // URL 中不再包含 token
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: localStorage.getItem('access_token')
  }))
}
```

**后端修复** - `backend/src/api/routes/collaboration_ws.py:59-67`

```python
# 修复前:
if token:
    try:
        # TODO: 验证 token 获取用户信息
        pass
    except Exception as e:
        logger.warning(f"Token 验证失败: {e}")

# 修复后:
# 【说明】实现 WebSocket 首条消息认证
# 连接建立后，等待客户端发送 auth 消息，验证 Token 后才允许后续操作
# 超时 10 秒未认证则断开连接
auth_msg = await asyncio.wait_for(websocket.receive_json(), timeout=10)
if auth_msg.get("type") == "auth" and auth_msg.get("token"):
    try:
        user_id = verify_token(auth_msg["token"])
        # 查询用户信息
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user_id = str(user.id)
            user_name = user.name
    except Exception as e:
        logger.warning(f"WebSocket Token 验证失败: {e}")
        await websocket.close(code=4001, reason="认证失败")
        return
```

---

## 三、Phase 1：清理废弃模块与代码

> 目标：移除 PRD 不需要的模块，减少维护负担和打包体积

### 1.1 删除文件清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 删除 | `frontend/src/pages/TaxAssets.tsx` | PRD 延期的财税模块 |
| 删除 | `frontend/src/pages/Sentiment.tsx` | PRD 未包含的舆情模块 |
| 删除 | `frontend/src/pages/LegalTools.tsx` | 聚合页（子功能已分配到各域） |
| 删除 | `frontend/src/pages/Chat.new.tsx` | 与 Chat.tsx 重复的替代实现 |

### 1.2 更新路由配置

**文件**: `frontend/src/App.tsx`

```typescript
// 【说明】移除已删除页面的 import 和路由定义
// 删除以下 import:
// - import Sentiment from '@/pages/Sentiment'
// - import TaxAssets from '@/pages/TaxAssets'
// - import LegalTools from '@/pages/LegalTools'
//
// 删除以下路由:
// - <Route path="tools" element={<LegalTools />} />
// - <Route path="tax-assets" element={<TaxAssets />} />
// - <Route path="sentiment" element={<Sentiment />} />
```

### 1.3 清理废弃依赖

```bash
# 【说明】移除 package.json 中未使用或重复的依赖
# axios: 项目中从未 import 过，完全废弃
# motion: 与 framer-motion 功能重复（motion 是 framer-motion v11+ 的新包名）
#         当前代码中 import 的是 framer-motion，所以移除 motion
npm uninstall axios motion
```

### 1.4 清理后端对应路由（可选）

如果后端有 sentiment 和 assets 专用路由，标记为 deprecated 但不删除（避免影响已有数据）:

```python
# backend/src/api/routes/sentiment.py - 添加弃用标记
# 【说明】PRD 已移除舆情模块，后端路由标记为弃用
# 保留代码但不再注册到 router，避免删除影响数据库中已有数据
```

---

## 四、Phase 2：导航重构为四大业务域

> 目标：将 Layout.tsx 导航从平铺 5 项改为 PRD 定义的四大业务域分组结构

### 2.1 新建页面文件

以下页面目前不存在，需要新建（初始版本为骨架页，后续迭代填充内容）：

| 页面 | 路径 | 基于现有组件 |
|------|------|------------|
| 案源管理 | `pages/Leads.tsx` | 新建骨架页 |
| 司法资讯 | `pages/News.tsx` | 新建骨架页 |
| 律师精英 | `pages/Experts.tsx` | 包装 `components/knowledge-center/ExperienceCenter.tsx` |
| 智慧搜索 | `pages/Search.tsx` | 包装 `components/knowledge-center/SmartSearch.tsx` |
| 知识图谱 | `pages/KnowledgeGraph.tsx` | 包装 `components/knowledge-center/KnowledgeGraphExplorer.tsx` |
| 司法智库 | `pages/KnowledgeBase.tsx` | 包装 `components/knowledge-center/KnowledgeBaseManager.tsx` |
| 司法学院 | `pages/Academy.tsx` | 新建骨架页 |
| 任务中心 | `pages/Tasks.tsx` | 新建骨架页 |
| 404 页面 | `pages/NotFound.tsx` | 新建 |

**骨架页模板**（以案源管理为例）:

```tsx
// 【说明】骨架页：提供基本布局和占位内容
// 后续迭代中逐步实现具体业务功能
// 使用统一的页面容器结构，确保与其他页面风格一致
import { ScrollArea } from '@/components/ui/scroll-area'

export default function Leads() {
  return (
    <ScrollArea className="h-full">
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-foreground">案源管理</h1>
          <p className="text-sm text-muted-foreground mt-1">
            线索录入、客户需求管理、跟进记录与转化跟踪
          </p>
        </div>
        {/* TODO: 实现案源列表、录入表单、跟进记录等 */}
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
          案源管理模块开发中...
        </div>
      </div>
    </ScrollArea>
  )
}
```

### 2.2 重构 Layout.tsx 导航

**文件**: `frontend/src/components/Layout.tsx`

**修复方式**: 将平铺导航改为分组导航

```typescript
// 【说明】将导航从 5 个平铺项改为 PRD 定义的四大业务域
// 每个域包含子模块，桌面端用下拉菜单展示，移动端用手风琴展示
// 默认展示域名称 + 图标，hover/点击展开子模块列表

// 修复前（当前代码）:
const navItems = [
  { id: 'chat', path: '/chat', label: '智能对话', icon: MessageSquare },
  { id: 'due-diligence', path: '/due-diligence', label: '尽职调查', icon: Search },
  { id: 'cases', path: '/cases', label: '案件管理', icon: Briefcase },
  { id: 'documents', path: '/documents', label: '智能文档', icon: FileStack },
  { id: 'knowledge', path: '/knowledge', label: '知识中心', icon: GraduationCap },
];

// 修复后:
// 使用 Heroicons 图标（Phase 4 统一替换）
// 此处先用占位，Phase 4 时统一切换
const navGroups = [
  {
    id: 'ai-legal',
    label: 'AI法务',
    icon: ChatBubbleLeftRightIcon,  // heroicons
    children: [
      { id: 'chat', path: '/chat', label: '智能对话' },
      { id: 'contract-review', path: '/contract-review', label: '合同审查' },
      { id: 'dashboard', path: '/dashboard', label: '智能中台' },
    ],
  },
  {
    id: 'collaboration',
    label: '智能协作',
    icon: UsersIcon,
    children: [
      { id: 'cases', path: '/cases', label: '案件管理' },
      { id: 'documents', path: '/documents', label: '文件管理' },
      { id: 'contracts', path: '/contracts', label: '智能生成' },
      { id: 'collaboration', path: '/collaboration', label: '在线协作' },
      { id: 'experts', path: '/experts', label: '律师精英' },
      { id: 'leads', path: '/leads', label: '案源管理' },
    ],
  },
  {
    id: 'info-center',
    label: '信息中心',
    icon: NewspaperIcon,
    children: [
      { id: 'news', path: '/news', label: '司法资讯' },
      { id: 'due-diligence', path: '/due-diligence', label: '尽职调查' },
    ],
  },
  {
    id: 'knowledge',
    label: '法律智库',
    icon: BookOpenIcon,
    children: [
      { id: 'search', path: '/search', label: '智慧搜索' },
      { id: 'knowledge-graph', path: '/knowledge-graph', label: '知识图谱' },
      { id: 'knowledge-base', path: '/knowledge-base', label: '司法智库' },
      { id: 'academy', path: '/academy', label: '司法学院' },
    ],
  },
];
```

**桌面端导航交互**:
- 四大域名称横向排列在顶栏
- 当前激活域高亮（判断逻辑：当前路由匹配域内任一子路由）
- 点击域名称展开下拉面板，显示子模块列表
- 子模块使用图标 + 文字，点击跳转

**移动端导航交互**:
- 汉堡菜单展开后，显示四大域的手风琴列表
- 点击域名称展开/折叠子模块
- 子模块点击跳转并关闭菜单

### 2.3 更新 App.tsx 路由

```typescript
// 【说明】使用 React.lazy 实现路由懒加载（同时完成 Phase 3 的 P-01）
// 好处：首屏只加载 Chat 页面代码，其他页面按需加载
// Suspense fallback 使用 Skeleton 占位，避免白屏闪烁

import { lazy, Suspense } from 'react'

const Chat = lazy(() => import('@/pages/Chat'))
const Cases = lazy(() => import('@/pages/Cases'))
const CaseDetail = lazy(() => import('@/pages/CaseDetail'))
const Documents = lazy(() => import('@/pages/Documents'))
const Contracts = lazy(() => import('@/pages/Contracts'))
const ContractReview = lazy(() => import('@/pages/ContractReview'))
const DueDiligence = lazy(() => import('@/pages/DueDiligence'))
const Collaboration = lazy(() => import('@/pages/Collaboration'))
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const Settings = lazy(() => import('@/pages/Settings'))
// 新增页面
const Leads = lazy(() => import('@/pages/Leads'))
const News = lazy(() => import('@/pages/News'))
const Experts = lazy(() => import('@/pages/Experts'))
const Search = lazy(() => import('@/pages/Search'))
const KnowledgeGraph = lazy(() => import('@/pages/KnowledgeGraph'))
const KnowledgeBase = lazy(() => import('@/pages/KnowledgeBase'))
const Academy = lazy(() => import('@/pages/Academy'))
const Tasks = lazy(() => import('@/pages/Tasks'))
const NotFound = lazy(() => import('@/pages/NotFound'))

// 路由配置:
<Suspense fallback={<PageSkeleton />}>
  <Routes>
    <Route path="/" element={<Layout />}>
      <Route index element={<Navigate to="/chat" replace />} />
      {/* AI法务 */}
      <Route path="chat" element={<Chat />} />
      <Route path="contract-review" element={<ContractReview />} />
      <Route path="dashboard" element={<Dashboard />} />
      {/* 智能协作 */}
      <Route path="cases" element={<Cases />} />
      <Route path="cases/:id" element={<CaseDetail />} />
      <Route path="documents" element={<Documents />} />
      <Route path="contracts" element={<Contracts />} />
      <Route path="collaboration" element={<Collaboration />} />
      <Route path="collaboration/:sessionId" element={<Collaboration />} />
      <Route path="experts" element={<Experts />} />
      <Route path="leads" element={<Leads />} />
      {/* 信息中心 */}
      <Route path="news" element={<News />} />
      <Route path="due-diligence" element={<DueDiligence />} />
      {/* 法律智库 */}
      <Route path="search" element={<Search />} />
      <Route path="knowledge-graph" element={<KnowledgeGraph />} />
      <Route path="knowledge-base" element={<KnowledgeBase />} />
      <Route path="academy" element={<Academy />} />
      {/* 系统 */}
      <Route path="settings" element={<Settings />} />
      <Route path="tasks" element={<Tasks />} />
      {/* 404 兜底 */}
      <Route path="*" element={<NotFound />} />
    </Route>
  </Routes>
</Suspense>
```

---

## 五、Phase 3：前端性能与质量优化

> 目标：提升首屏加载速度、运行时性能、代码可维护性

### 3.1 添加 Error Boundary（A-03）

**新建文件**: `frontend/src/components/ErrorBoundary.tsx`

```tsx
// 【说明】全局错误边界，捕获子组件的 JS 运行时异常
// 避免单个组件报错导致整个应用白屏
// 展示友好的错误提示，并提供"重试"按钮
import { Component, ErrorInfo, ReactNode } from 'react'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; error?: Error }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="h-screen flex items-center justify-center">
          <div className="text-center space-y-4">
            <h2 className="text-lg font-semibold">页面出现异常</h2>
            <p className="text-muted-foreground text-sm">
              {this.state.error?.message}
            </p>
            <button
              onClick={() => this.setState({ hasError: false })}
              className="px-4 py-2 bg-primary text-white rounded-lg text-sm"
            >
              重新加载
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
```

在 App.tsx 中包裹:

```tsx
<ErrorBoundary>
  <BrowserRouter>
    ...
  </BrowserRouter>
</ErrorBoundary>
```

### 3.2 添加页面加载骨架屏

**新建文件**: `frontend/src/components/PageSkeleton.tsx`

```tsx
// 【说明】配合 React.lazy 的 Suspense fallback 使用
// 避免页面切换时的白屏闪烁，提供加载中的视觉反馈
export function PageSkeleton() {
  return (
    <div className="h-full p-6 animate-pulse space-y-4">
      <div className="h-8 w-48 bg-muted rounded" />
      <div className="h-4 w-96 bg-muted rounded" />
      <div className="grid grid-cols-3 gap-4 mt-6">
        <div className="h-32 bg-muted rounded-lg" />
        <div className="h-32 bg-muted rounded-lg" />
        <div className="h-32 bg-muted rounded-lg" />
      </div>
    </div>
  )
}
```

### 3.3 index.html 安全头（S-12）

**文件**: `frontend/index.html`

```html
<!-- 【说明】添加安全相关的 meta 标签 -->
<!-- CSP: 限制脚本和样式的加载来源，防止 XSS 注入 -->
<!-- X-Frame-Options: 防止页面被嵌入 iframe（点击劫持防护） -->
<!-- Referrer-Policy: 控制 HTTP Referrer 头，防止敏感 URL 泄露 -->
<meta http-equiv="Content-Security-Policy"
  content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' ws: wss:; font-src 'self';" />
<meta http-equiv="X-Frame-Options" content="DENY" />
<meta name="referrer" content="strict-origin-when-cross-origin" />
```

### 3.4 TypeScript 严格化（T-01）

**文件**: `frontend/tsconfig.json`

```json
// 【说明】启用未使用变量/参数检测
// 好处：在编译时发现死代码，保持代码库整洁
// 可能需要清理一些现有的未使用 import
"noUnusedLocals": true,
"noUnusedParameters": true,
```

---

## 六、Phase 4：UI 规范统一与图标 SVG 化

> 目标：建立企业级设计规范，统一图标体系，消除 "AI 味" 视觉元素

### 4.1 安装 Heroicons

```bash
# 【说明】Heroicons 是 Tailwind CSS 官方推荐的 SVG 图标库
# 提供 outline（线框）和 solid（填充）两种风格，共 300+ 图标
# 风格统一、大小一致、无渐变色，符合企业级视觉规范
npm install @heroicons/react
```

### 4.2 创建设计规范文件

**新建文件**: `frontend/src/lib/design-tokens.ts`

```typescript
/**
 * AI法务智能体系统 - 统一设计规范（Design Tokens）
 *
 * 【说明】此文件定义全局设计规范，所有组件必须遵循：
 * 1. 图标统一使用 Heroicons，不使用 lucide-react / Lottie / emoji
 * 2. 颜色使用 Tailwind CSS 变量（--primary 等），不使用硬编码色值
 * 3. 禁止蓝紫色渐变（gradient）、霓虹发光效果（glow/neon）
 * 4. 间距、圆角、阴影使用统一 Token
 */

// ========== 图标规范 ==========
// 来源：仅限 @heroicons/react/24/outline 和 @heroicons/react/24/solid
// 大小标准：
export const ICON_SIZE = {
  xs: 'w-3.5 h-3.5',  // 14px - 行内辅助图标
  sm: 'w-4 h-4',      // 16px - 按钮内图标、导航项图标
  md: 'w-5 h-5',      // 20px - 标准交互图标、工具栏
  lg: 'w-6 h-6',      // 24px - 页面标题图标、空状态
  xl: 'w-8 h-8',      // 32px - 大型展示图标
} as const

// ========== 间距规范 ==========
export const SPACING = {
  page: 'p-6',                    // 页面内边距
  pageMobile: 'p-4',             // 移动端页面内边距
  section: 'space-y-6',          // 区块间距
  card: 'p-4',                   // 卡片内边距
  cardCompact: 'p-3',            // 紧凑卡片内边距
  itemGap: 'gap-3',              // 列表项间距
} as const

// ========== 圆角规范 ==========
export const RADIUS = {
  sm: 'rounded-md',     // 4px - 小型元素（Badge、Tag）
  md: 'rounded-lg',     // 8px - 标准元素（Card、Button）
  lg: 'rounded-xl',     // 12px - 大型容器（Modal、Panel）
  full: 'rounded-full', // 圆形（Avatar、Status dot）
} as const

// ========== 阴影规范 ==========
// 【说明】使用中性阴影，不使用品牌色阴影（shadow-legal-* 系列将逐步替换）
export const SHADOW = {
  sm: 'shadow-sm',                                  // 微阴影
  md: 'shadow-md',                                  // 标准阴影
  lg: 'shadow-lg',                                  // 强调阴影
  card: 'shadow-sm hover:shadow-md transition-shadow', // 卡片悬浮效果
} as const

// ========== 颜色语义 ==========
// 【说明】禁止直接使用 hex/rgb 色值，统一使用 Tailwind 语义色
export const COLOR_SEMANTIC = {
  // 状态色
  success: 'text-emerald-600 bg-emerald-50',
  warning: 'text-amber-600 bg-amber-50',
  error: 'text-red-600 bg-red-50',
  info: 'text-blue-600 bg-blue-50',
  // 交互色
  primaryButton: 'bg-primary text-primary-foreground hover:bg-primary/90',
  secondaryButton: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
  ghostButton: 'hover:bg-muted text-muted-foreground hover:text-foreground',
} as const

// ========== 禁止使用的样式 ==========
// 以下样式在代码审查中会被标记：
// ❌ bg-gradient-to-r from-blue-500 to-purple-500  (蓝紫渐变)
// ❌ bg-gradient-to-r from-indigo-500 to-cyan-500  (AI 味渐变)
// ❌ shadow-[0_0_20px_rgba(99,102,241,0.5)]        (霓虹发光)
// ❌ animate-pulse（用于装饰，非加载状态）
// ❌ 直接使用 emoji 作为功能图标
```

### 4.3 创建图标映射文件

**新建文件**: `frontend/src/lib/icons.ts`

```typescript
/**
 * 统一图标导出
 *
 * 【说明】所有组件从此文件导入图标，不直接从 @heroicons/react 导入
 * 好处：
 * 1. 全局统一图标风格（默认使用 outline 风格）
 * 2. 需要更换图标时只改一处
 * 3. 命名语义化，按业务场景分组
 */

// ===== 导航图标 =====
export {
  ChatBubbleLeftRightIcon as IconChat,
  UserGroupIcon as IconCollaboration,
  NewspaperIcon as IconInfoCenter,
  BookOpenIcon as IconKnowledge,
} from '@heroicons/react/24/outline'

// ===== AI法务 =====
export {
  ChatBubbleLeftRightIcon as IconSmartChat,
  DocumentCheckIcon as IconContractReview,
  ChartBarIcon as IconDashboard,
} from '@heroicons/react/24/outline'

// ===== 智能协作 =====
export {
  BriefcaseIcon as IconCases,
  FolderIcon as IconDocuments,
  DocumentDuplicateIcon as IconContracts,
  UsersIcon as IconOnlineCollab,
  AcademicCapIcon as IconExperts,
  FunnelIcon as IconLeads,
} from '@heroicons/react/24/outline'

// ===== 信息中心 =====
export {
  NewspaperIcon as IconNews,
  MagnifyingGlassCircleIcon as IconDueDiligence,
} from '@heroicons/react/24/outline'

// ===== 法律智库 =====
export {
  MagnifyingGlassIcon as IconSearch,
  ShareIcon as IconKnowledgeGraph,
  BuildingLibraryIcon as IconKnowledgeBase,
  AcademicCapIcon as IconAcademy,
} from '@heroicons/react/24/outline'

// ===== 通用操作 =====
export {
  Cog6ToothIcon as IconSettings,
  BellIcon as IconNotification,
  ClipboardDocumentListIcon as IconTasks,
  UserCircleIcon as IconUser,
  ArrowRightOnRectangleIcon as IconLogout,
  Bars3Icon as IconMenu,
  XMarkIcon as IconClose,
  PlusIcon as IconAdd,
  PencilIcon as IconEdit,
  TrashIcon as IconDelete,
  ArrowDownTrayIcon as IconDownload,
  ArrowUpTrayIcon as IconUpload,
  CheckCircleIcon as IconSuccess,
  ExclamationTriangleIcon as IconWarning,
  InformationCircleIcon as IconInfo,
  XCircleIcon as IconError,
  ChevronDownIcon as IconChevronDown,
  ChevronRightIcon as IconChevronRight,
  EllipsisVerticalIcon as IconMore,
} from '@heroicons/react/24/outline'

// ===== Solid 变体（用于激活/选中状态） =====
export {
  ChatBubbleLeftRightIcon as IconChatSolid,
  BellIcon as IconNotificationSolid,
  CheckCircleIcon as IconSuccessSolid,
} from '@heroicons/react/24/solid'
```

### 4.4 图标迁移步骤

**执行策略**：逐文件替换，不做全量批量替换（避免遗漏）

1. **Layout.tsx**：替换 lucide-react 图标为 Heroicons
2. **NotificationCenter.tsx**：替换
3. **UserProfile.tsx**：替换
4. **各页面文件**：逐个替换
5. **最后**：确认无文件 import lucide-react 后，`npm uninstall lucide-react`

**替换对照表**（lucide → heroicons）：

| lucide-react | @heroicons/react/24/outline | 用途 |
|-------------|---------------------------|------|
| `MessageSquare` | `ChatBubbleLeftRightIcon` | 智能对话 |
| `Search` | `MagnifyingGlassIcon` | 搜索 |
| `Briefcase` | `BriefcaseIcon` | 案件 |
| `FileStack` | `FolderIcon` | 文档 |
| `GraduationCap` | `AcademicCapIcon` | 知识/学院 |
| `Bell` | `BellIcon` | 通知 |
| `User` | `UserCircleIcon` | 用户 |
| `Settings` | `Cog6ToothIcon` | 设置 |
| `Menu` | `Bars3Icon` | 菜单 |
| `X` | `XMarkIcon` | 关闭 |
| `Bot` | `SparklesIcon` | AI/Logo |
| `Plus` | `PlusIcon` | 新增 |
| `Trash2` | `TrashIcon` | 删除 |
| `BarChart3` | `ChartBarIcon` | 图表 |
| `Calculator` | `CalculatorIcon` | 计算 |
| `FileCheck` | `DocumentCheckIcon` | 审查 |

### 4.5 移除 Lottie 装饰性动画

**文件**:
- `frontend/src/components/ui/LottieIcon.tsx` → 删除
- `frontend/src/components/a2ui/animations/LottieAnimations.tsx` → 重构为纯 CSS 动画或移除

```typescript
// 【说明】Lottie 动画图标存在以下问题：
// 1. 加载外部 CDN 资源（lottie.host），离线/内网部署不可用
// 2. 蓝紫色渐变风格与企业级规范不符
// 3. 增加 lottie-react 依赖体积
//
// 替代方案：
// - 加载状态使用 Tailwind 的 animate-spin + Heroicons ArrowPathIcon
// - 成功状态使用 CheckCircleIcon + 简单 CSS 动画
// - 空状态使用 Heroicons 图标 + 文字说明
```

最后移除依赖：
```bash
npm uninstall lottie-react
```

---

## 七、Phase 5：响应式与移动端适配

> 目标：核心页面支持移动端使用，参考千问的移动端卡片式交互

### 5.1 Layout.tsx 移动端导航优化

**修复方式**: 移动端底部 Tab 栏（借鉴千问移动端设计）

```tsx
// 【说明】移动端使用底部 Tab 栏替代顶部导航
// 原因：
// 1. 底部 Tab 更适合单手操作（拇指可达区域）
// 2. 参考千问/微信等主流移动端应用的导航方式
// 3. 四大域 + "更多" 刚好适合 5 个 Tab 位置
//
// 实现方式：仅在 lg: 以下显示底栏，lg: 以上显示顶栏（已有逻辑）

{/* Mobile Bottom Tab Bar */}
<div className="lg:hidden fixed bottom-0 left-0 right-0 bg-background border-t border-border safe-area-inset-bottom z-50">
  <div className="flex items-center justify-around py-2">
    {/* AI法务 */}
    <TabItem icon={IconChat} label="AI法务" path="/chat" />
    {/* 协作 */}
    <TabItem icon={IconCollaboration} label="协作" path="/cases" />
    {/* 信息 */}
    <TabItem icon={IconInfoCenter} label="信息" path="/news" />
    {/* 智库 */}
    <TabItem icon={IconKnowledge} label="智库" path="/search" />
    {/* 更多 */}
    <TabItem icon={IconMore} label="更多" onClick={toggleMobileMenu} />
  </div>
</div>
```

### 5.2 Chat 页面移动端适配

```tsx
// 【说明】Chat 页面移动端适配要点：
// 1. 对话侧边栏默认隐藏，通过手势或按钮展开（当前已支持）
// 2. 输入框固定在底部，键盘弹起时自动上推
// 3. 消息气泡宽度自适应，最大宽度不超过屏幕 85%
// 4. 工具面板（右侧）改为底部抽屉（Sheet）
//
// 具体修改（在现有 Chat.tsx 中微调，不重构）：
// - 添加 className="max-w-[85vw] lg:max-w-[70%]" 到消息容器
// - 右侧面板在移动端使用 Drawer 组件替代固定面板
// - 输入框添加 safe-area-inset-bottom padding
```

### 5.3 卡片组件移动端适配

```tsx
// 【说明】参考千问的卡片设计：
// - 卡片内容紧凑，移动端去除多余内边距
// - 操作按钮使用底部操作条（Action Bar），不使用右上角小图标
// - 长文本使用 line-clamp 截断，点击展开
//
// 在 Tailwind 中实现响应式：
// className="p-4 lg:p-6"           -- 移动端紧凑，桌面端宽松
// className="grid grid-cols-1 lg:grid-cols-3" -- 移动端单列，桌面端三列
// className="text-sm lg:text-base" -- 移动端字号略小
```

---

## 八、Phase 6：后端稳定性与基础设施加固

### 6.1 异常信息脱敏（B-01）

**修复方式**: 创建统一异常处理中间件

```python
# 【说明】生产环境不向客户端暴露详细异常信息
# 开发环境保留 detail 方便调试
# 所有异常都记录到日志（含完整堆栈），但只向客户端返回错误码 + 友好提示

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if settings.ENVIRONMENT == "production":
        # 生产环境：返回通用错误信息
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": "服务异常，请稍后重试" if exc.status_code >= 500 else exc.detail,
            }
        )
    # 开发环境：返回详细信息
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail}
    )
```

### 6.2 修复裸 except（B-02）

**文件**: `backend/src/api/routes/collaboration_ws.py:199`

```python
# 修复前:
except:
    pass

# 修复后:
# 【说明】裸 except 会吞掉所有异常（包括 KeyboardInterrupt、SystemExit）
# 至少应该捕获 Exception 并记录日志
except Exception as e:
    logger.warning(f"协作 WebSocket 处理异常: {e}")
```

### 6.3 API Key 加密回退修复（S-09）

**文件**: `backend/src/services/llm_service.py:62-64`

```python
# 修复前:
except Exception as e:
    logger.warning(f"加密API密钥失败: {e}")
    return api_key  # 回退为明文！

# 修复后:
# 【说明】加密失败不应回退为明文存储
# 抛出异常让调用方感知，避免敏感数据以明文形式存入数据库
except Exception as e:
    logger.error(f"加密API密钥失败: {e}")
    raise ValueError(f"API密钥加密失败，请检查加密配置: {e}")
```

### 6.4 Docker Compose 加固

**文件**: `docker-compose.yml`

```yaml
# 【修复 I-01】密码从环境变量读取，不再硬编码
# 在 .env 中配置：
# POSTGRES_PASSWORD=your-strong-password
# NEO4J_PASSWORD=your-strong-password
# MINIO_PASSWORD=your-strong-password
postgres:
  environment:
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}  # 默认值仅用于开发

# 【修复 I-02】锁定镜像版本，避免意外升级
qdrant:
  image: qdrant/qdrant:v1.7.4    # 原为 latest
minio:
  image: minio/minio:RELEASE.2024-01-05T22-17-24Z  # 原为 latest

# 【修复 I-04】为所有服务添加健康检查
qdrant:
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:6333/"]
    interval: 15s
    timeout: 5s
    retries: 3

neo4j:
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:7474/"]
    interval: 15s
    timeout: 5s
    retries: 3

minio:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
    interval: 15s
    timeout: 5s
    retries: 3
```

### 6.5 创建 .env.example

```bash
# 【说明】.env.example 作为配置模板，不包含真实密钥
# 团队成员复制为 .env 后填入自己的密钥
# .env 已在 .gitignore 中，不会被提交到 git

# 确认 .gitignore 包含:
# .env
# .env.local
# .env.*.local
```

---

## 九、执行检查清单

每个 Phase 完成后的验证项：

### Phase 0 验证
- [ ] 启动后端，确认 CORS 只允许配置的域名
- [ ] 设置 ENVIRONMENT=production + DEV_MODE=true，确认拒绝启动
- [ ] 设置 ENVIRONMENT=production + 默认 JWT 密钥，确认拒绝启动
- [ ] 测试 WebSocket 连接，确认首条消息认证生效
- [ ] 确认 .env.example 不含真实密钥

### Phase 1 验证
- [ ] 删除的页面文件不存在
- [ ] 访问 /tools、/tax-assets、/sentiment 返回 404
- [ ] `npm run build` 无报错
- [ ] Bundle 体积对比（应有减少）

### Phase 2 验证
- [ ] 顶部导航显示四大域：AI法务、智能协作、信息中心、法律智库
- [ ] 点击每个域可展开子模块列表
- [ ] 所有路由可正常访问
- [ ] 新建骨架页正常渲染
- [ ] 404 页面正常工作

### Phase 3 验证
- [ ] 路由切换时显示 Skeleton 加载动画（非白屏）
- [ ] 故意制造组件报错，确认 ErrorBoundary 捕获并显示友好提示
- [ ] 查看 index.html source，确认安全 meta 标签存在
- [ ] `tsc --noEmit` 无未使用变量警告

### Phase 4 验证
- [ ] 所有图标为 Heroicons SVG，无 lucide-react 残留
- [ ] 无蓝紫色渐变图标
- [ ] 图标大小统一（导航 20px、按钮 16px）
- [ ] `npm ls lucide-react` 返回空（已卸载）
- [ ] `npm ls lottie-react` 返回空（已卸载）

### Phase 5 验证
- [ ] Chrome DevTools 切换到 iPhone 视口，底部 Tab 栏正常显示
- [ ] 移动端 Chat 页面：输入框在底部，消息宽度自适应
- [ ] 移动端导航：底部 Tab 可切换四大域
- [ ] iPad 视口：布局合理，不出现断裂

### Phase 6 验证
- [ ] 生产模式下，500 错误不暴露堆栈信息
- [ ] API Key 加密失败时抛出异常（不回退明文）
- [ ] Docker Compose 启动所有服务，健康检查通过
- [ ] docker-compose.yml 中无 `:latest` 标签

---

## 十、风险预案

| 风险 | 影响 | 预案 |
|------|------|------|
| 图标替换遗漏 | 个别页面图标丢失 | 逐文件 grep `lucide-react`，确保零残留 |
| 导航重构影响现有书签 | 用户书签失效 | 旧路由添加 `<Navigate>` 重定向 |
| React.lazy 导致首次加载慢 | 页面切换有延迟 | 使用 prefetch（鼠标 hover 导航时预加载） |
| 后端安全加固导致现有功能异常 | 部分 API 调用失败 | Phase 0 后充分测试所有 API 端点 |
| 移除 Lottie 后部分组件样式异常 | 空状态/加载动画丢失 | 用 CSS 动画 + Heroicons 逐一替代 |

---

> **下一步**：请审核此计划，确认无误后我将按 Phase 0 → Phase 6 顺序逐步执行。
> 每完成一个 Phase，会暂停并报告执行结果，你确认后再继续下一个 Phase。
