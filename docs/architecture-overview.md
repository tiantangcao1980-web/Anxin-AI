# Anxin Smart Assistant — 系统架构与功能全景

> 企业级 AI 智能助手智能平台 | Multi-Agent + RAG + A2UI

---

## 一、系统架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        用户层 (User Layer)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Web 浏览器│  │ 移动端   │  │ OA 集成  │  │ 微信/支付宝 OAuth│   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
└───────┼──────────────┼──────────────┼────────────────┼─────────────┘
        │              │              │                │
┌───────▼──────────────▼──────────────▼────────────────▼─────────────┐
│                     前端层 (Frontend Layer)                         │
│  React 18 + TypeScript + Vite + Tailwind CSS + Radix UI            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Zustand Store  │  React Query  │  WebSocket  │  Router     │   │
│  ├─────────────────┴───────────────┴─────────────┴─────────────┤   │
│  │  A2UI 动态渲染引擎  │  Tiptap 协作编辑  │  Three.js 知识图谱 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ REST API / WebSocket / SSE
┌───────────────────────────────▼─────────────────────────────────────┐
│                     后端层 (Backend Layer)                           │
│  FastAPI + SQLAlchemy 2.0 Async + Pydantic 2.5                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  API 网关 (Routes)                            │   │
│  │  Auth │ Chat │ Cases │ Contracts │ Documents │ Knowledge │...│   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │                  业务服务层 (Services)                        │   │
│  │  47 个专业服务: RAG / 缓存 / 事件总线 / 导出 / 爬虫 / ...   │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │              多智能体引擎 (Multi-Agent Engine)                │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ Coordinator → DAG 编排 → 16 专业 Agent 并行执行        │  │   │
│  │  │         ↕ 消息池 (MessagePool)  ↕ 生命周期管理          │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │                三层记忆系统 (Memory System)                   │   │
│  │  语义记忆 (知识) ← 情景记忆 (经验) ← 工作记忆 (会话)        │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │                进化学习系统 (Evolution System)                │   │
│  │  用户反馈 → 经验提取 → 策略优化 → Agent 动态调整             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└───────────────┬────────────┬───────────┬──────────┬─────────────────┘
                │            │           │          │
┌───────────────▼────┐ ┌─────▼─────┐ ┌──▼───┐ ┌───▼────┐ ┌──────────┐
│   PostgreSQL 15    │ │  Redis 7  │ │Qdrant│ │ Neo4j  │ │  MinIO   │
│   关系型数据库      │ │ 缓存/消息  │ │向量库 │ │知识图谱│ │ 对象存储  │
│   40+ 表           │ │ Pub/Sub   │ │语义搜索│ │关系推理│ │ 文件存储  │
└────────────────────┘ └───────────┘ └──────┘ └────────┘ └──────────┘
```

---

## 二、技术栈清单

| 层级 | 技术 | 版本 | 用途 |
|:-----|:-----|:-----|:-----|
| **前端框架** | React + TypeScript | 18.2 / 5.3 | SPA 单页应用 |
| **构建工具** | Vite | 7.3 | 极速构建与 HMR |
| **状态管理** | Zustand | 4.4 | 轻量全局状态 |
| **数据获取** | TanStack React Query | 5.17 | 服务端状态管理 |
| **UI 组件库** | Radix UI | 最新 | 无障碍无头组件 |
| **样式** | Tailwind CSS | 3.4 | 原子化 CSS |
| **动画** | Framer Motion + Lottie | 10.18 / 2.4 | 交互动画 |
| **图表** | Recharts | 2.10 | 数据可视化 |
| **3D 可视化** | Three.js + react-force-graph | 0.182 | 知识图谱 3D |
| **协作编辑** | Tiptap + Yjs | 2.27 / 13.6 | 实时多人编辑 |
| **后端框架** | FastAPI | 0.109+ | 异步 Web API |
| **ORM** | SQLAlchemy 2.0 Async | 2.0+ | 数据库 ORM |
| **多智能体** | CAMEL-AI | 0.2.0 | Agent 框架 |
| **LLM 集成** | OpenAI / Anthropic / 通义千问 | 多版本 | 大语言模型 |
| **Embedding** | sentence-transformers | 2.3 | 本地向量编码 |
| **文档处理** | PyPDF / python-docx / reportlab | 多版本 | 文件解析与导出 |
| **数据库** | PostgreSQL | 15 | 主数据库 |
| **缓存** | Redis | 7 | 缓存 + Pub/Sub |
| **向量库** | Qdrant | 1.12 | 语义检索 |
| **图数据库** | Neo4j | 5 | 知识图谱 |
| **对象存储** | MinIO | 最新 | 文件存储 |
| **容器化** | Docker + Docker Compose | 最新 | 部署编排 |

---

## 三、功能模块对照表

### 3.1 四大核心功能模块

```
┌──────────────────────────────────────────────────────────────────┐
│                    四大核心功能模块                                │
├────────────────┬────────────────┬────────────────┬───────────────┤
│   合同智能审查   │   尽职调查      │  案件管理       │  AI 智能对话   │
│                │                │                │               │
│ • 文档上传解析   │ • 企业信息检索   │ • 案件 CRUD     │ • 多轮对话     │
│ • AI 风险识别   │ • 法律案件查询   │ • 时间线管理     │ • 流式响应     │
│ • 原文高亮对比   │ • 合规审查      │ • 状态流转      │ • 文件上传     │
│ • 一键修改      │ • 舆情分析      │ • 风险评分      │ • Agent 协作   │
│ • PDF/DOCX 导出 │ • 关系图谱      │ • 预警通知      │ • A2UI 卡片   │
│ • 服务器保存    │ • 风险时间线     │ • 统计概览      │ • 思维链展示   │
└────────────────┴────────────────┴────────────────┴───────────────┘
```

### 3.2 全功能模块详细对照表

| 模块 | 子功能 | 前端页面 | 后端路由 | 核心服务 | Agent |
|:-----|:-------|:---------|:---------|:---------|:------|
| **AI 智能对话** | 多轮法律咨询 | `Chat.tsx` | `chat.py` | `chat_service.py` | CoordinatorAgent → 16 Agent |
| | 流式响应 (SSE) | `StreamingMessage.tsx` | `chat.py` (stream) | `a2ui_stream.py` | — |
| | 思维链展示 | `ThinkingChain.tsx` | — | — | — |
| | A2UI 动态卡片 | `a2ui/components/*` | — | `a2ui_protocol.py` | — |
| | Agent 执行可视化 | `AgentFlow.tsx` | WebSocket | `event_bus.py` | — |
| | 文件上传分析 | `MultiModalInput.tsx` | `documents.py` | `document_parser.py` | — |
| | 知识图谱 3D | `KnowledgeGraphView.tsx` | `knowledge.py` | `graph_service.py` | — |
| **合同智能审查** | 文档上传解析 | `ContractReview.tsx` | `contracts.py` | `document_parser.py` | — |
| | AI 风险识别 | `ContractReview.tsx` | `contracts.py` | `contract_service.py` | ContractReviewAgent |
| | 风险条款高亮 | `ContractReview.tsx` | — | — | — |
| | 原文 vs 建议对比 | `ContractReview.tsx` | — | — | — |
| | 一键接受修改 | `ContractReview.tsx` | `apply-suggestions` | `contract_service.py` | — |
| | 保存到服务器 | `ContractReview.tsx` | `save-file` | `contract_service.py` | — |
| | PDF/DOCX 下载 | `ContractReview.tsx` | `download` | `document_export.py` | — |
| | 合同库管理 | `Contracts.tsx` | `contracts.py` | `contract_service.py` | — |
| **尽职调查** | 企业信息检索 | `CompanyProfile.tsx` | `due_diligence.py` | `due_diligence_service.py` | DueDiligenceAgent |
| | 法律案件查询 | `LegalCases.tsx` | `due_diligence.py` | `due_diligence_service.py` | — |
| | 合规审查报告 | `ComplianceReport.tsx` | `due_diligence.py` | `due_diligence_service.py` | ComplianceAgent |
| | 舆情分析 | `SentimentAnalysis.tsx` | `sentiment.py` | `sentiment_service.py` | SentimentAgent |
| | 关系图谱 | `RelationshipGraph.tsx` | `due_diligence.py` | `graph_service.py` | — |
| | 风险时间线 | `RiskTimeline.tsx` | `due_diligence.py` | `due_diligence_service.py` | RiskAssessmentAgent |
| **案件管理** | 案件 CRUD | `CaseManagement.tsx` | `cases.py` | `case_service.py` | — |
| | 时间线管理 | `CaseTimeline.tsx` | `cases.py` | `case_service.py` | — |
| | 状态流转 | `CaseList.tsx` | `cases.py` | `case_service.py` | — |
| | 风险评分 | `CaseDetail.tsx` | `cases.py` | `case_service.py` | RiskAssessmentAgent |
| | 实时预警 | `RealtimeAlerts.tsx` | `cases.py` (alerts) | `case_service.py` | — |
| | 统计概览 | `CaseDistribution.tsx` | `cases.py` (statistics) | `case_service.py` | — |
| **文档管理** | 文档上传 | `Documents.tsx` | `documents.py` | `document_service.py` | — |
| | 版本控制 | `DocumentLibrary.tsx` | `documents.py` | `document_service.py` | — |
| | 模板库 | `TemplateGallery.tsx` | `documents.py` | — | — |
| | AI 文书生成 | `AIGenerator.tsx` | `chat.py` | `chat_service.py` | DocumentDraftAgent |
| | 文档导出 | — | `documents.py` | `document_export.py` | — |
| **协作编辑** | 实时多人编辑 | `CollaborativeEditor.tsx` | `collaboration_ws.py` | `collaboration_service.py` | — |
| | Yjs + Tiptap 同步 | `CollaborativeEditor.tsx` | WebSocket | — | — |
| | 版本历史 | `Collaboration.tsx` | `collaboration.py` | `collaboration_service.py` | — |
| **知识库** | 知识库管理 | `KnowledgeBase.tsx` | `knowledge.py` | `knowledge_service.py` | — |
| | RAG 语义检索 | `SmartSearch.tsx` | `knowledge.py` | `rag_service.py` | LegalResearchAgent |
| | 向量存储 | — | — | `vector_store.py` | — |
| | 重排序 | — | `knowledge.py` | `reranker_service.py` | — |
| | 知识图谱浏览 | `KnowledgeGraph.tsx` | `knowledge.py` | `graph_service.py` | — |
| **舆情监控** | 监控任务管理 | `Sentiment.tsx` | `sentiment.py` | `sentiment_service.py` | SentimentAgent |
| | 舆情记录 | — | `sentiment.py` | `sentiment_service.py` | — |
| | 告警推送 | — | `sentiment.py` | `notification_service.py` | — |
| **仪表板** | 案件分布图 | `CaseDistribution.tsx` | `cases.py` | `case_service.py` | — |
| | 合规评分 | `ComplianceScore.tsx` | `cases.py` | `case_service.py` | — |
| | 律师工作量 | `LawyerWorkload.tsx` | — | — | — |
| | Token 使用统计 | `TokenUsage.tsx` | — | — | — |
| | 实时告警 | `RealtimeAlerts.tsx` | `cases.py` | `case_service.py` | — |
| **认证安全** | 邮箱密码登录 | `Login.tsx` | `auth.py` | `user_service.py` | — |
| | 微信 OAuth | `Login.tsx` | `auth.py` | `oauth_service.py` | — |
| | 支付宝 OAuth | `Login.tsx` | `auth.py` | `oauth_service.py` | — |
| | JWT Token | — | `auth.py` | `security.py` | — |
| | RBAC 权限 | `ProtectedRoute.tsx` | `security.py` | `security.py` | — |
| | 路由守卫 | `ProtectedRoute.tsx` | — | — | — |
| **其他模块** | 任务管理 | `Tasks.tsx` | `tasks.py` | `task_service.py` | — |
| | 案源管理 | `Leads.tsx` | `leads.py` | `lead_service.py` | — |
| | 律师精英库 | `Experts.tsx` | `experts.py` | `expert_service.py` | — |
| | 司法学院 | `Academy.tsx` | `courses.py` | `course_service.py` | — |
| | 通知中心 | `NotificationCenter.tsx` | `notifications.py` | `notification_service.py` | — |
| | 企业数据中心 | — | `datacenter.py` | `data_center_service.py` | — |
| | LLM 配置管理 | `Settings.tsx` | `llm.py` | `llm_service.py` | — |
| | MCP 工具调用 | — | `mcp_routes.py` | `mcp_client_service.py` | — |

---

## 四、多智能体架构

### 4.1 Agent 团队组成

```
                        ┌──────────────────────┐
                        │   CoordinatorAgent   │
                        │   (大脑 / PM)         │
                        │   意图识别 → DAG编排   │
                        └──────────┬───────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼─────────┐ ┌───────▼───────┐ ┌─────────▼─────────┐
    │ 需求分析团队        │ │ 审查执行团队   │ │ 研究支持团队       │
    │                    │ │               │ │                   │
    │ RequirementAnalyst │ │ ContractReview│ │ LegalResearch     │
    │ LegalAdvisor       │ │ DueDiligence  │ │ RegulatoryMonitor │
    │                    │ │ Compliance    │ │ EvidenceAnalyst   │
    └────────────────────┘ │ RiskAssessment│ └───────────────────┘
                           └───────────────┘
    ┌────────────────────┐ ┌───────────────┐ ┌───────────────────┐
    │ 专业领域团队        │ │ 文书生产团队   │ │ 决策仲裁团队       │
    │                    │ │               │ │                   │
    │ IPSpecialist       │ │ DocumentDraft │ │ Consensus         │
    │ TaxCompliance      │ │ ContractSteward││ LitigationStrat.  │
    │ LaborCompliance    │ │               │ │                   │
    └────────────────────┘ └───────────────┘ └───────────────────┘
```

### 4.2 DAG 执行流程

```
用户输入
  │
  ▼
CoordinatorAgent (意图识别)
  │
  ▼
DAG 编排 (确定 Agent 调用顺序)
  │
  ├─── 阶段 1: [RequirementAnalyst] ─── 需求澄清
  │         │
  │         ▼
  ├─── 阶段 2: [LegalResearch, ContractReview, DueDiligence] ─── 并行执行
  │         │              │                    │
  │         ▼              ▼                    ▼
  ├─── 阶段 3: [RiskAssessment, Compliance] ─── 汇总评估
  │         │              │
  │         ▼              ▼
  └─── 阶段 4: [DocumentDraft] → [Consensus] ─── 最终输出
                                      │
                                      ▼
                              CoordinatorAgent (结果汇总)
                                      │
                                      ▼
                                  用户响应
```

### 4.3 Agent 详细职责

| Agent | 角色 | 核心能力 |
|:------|:-----|:---------|
| **CoordinatorAgent** | 大脑/PM | 意图识别、DAG 任务编排、多 Agent 协调、结果汇总 |
| **RequirementAnalystAgent** | 需求分析师 | 需求理解、完整性检查、引导式提问 |
| **LegalAdvisorAgent** | 首席法律顾问 | 通用法律咨询、快速响应、前置过滤 |
| **ContractReviewAgent** | 合同审查专家 | 条款审查、风险识别、修改建议生成 |
| **DueDiligenceAgent** | 尽职调查专家 | 企业背景调查、信息收集、报告生成 |
| **LegalResearchAgent** | 法律研究员 | 法规检索、判例分析、法律观点支持 |
| **DocumentDraftAgent** | 文书起草专家 | 法律文书生成、格式规范、内容优化 |
| **ComplianceAgent** | 合规审核官 | 业务流程合规检查、风险规避建议 |
| **RiskAssessmentAgent** | 风险评估专家 | 法律风险综合评分、量化分析、建议 |
| **ConsensusAgent** | 共识决策者 | 多 Agent 意见分歧处理、仲裁结论 |
| **LitigationStrategistAgent** | 诉讼战略家 | 案件策略制定、胜诉概率评估 |
| **IPSpecialistAgent** | 知识产权专家 | IP 风险评估、专利检索、商标保护 |
| **RegulatoryMonitorAgent** | 监管监测员 | 政策变化监控、合规通知推送 |
| **TaxComplianceAgent** | 税务合规官 | 税务规划、税务风险识别 |
| **LaborComplianceAgent** | 劳动合规官 | 劳动法合规、HR 流程审查 |
| **EvidenceAnalystAgent** | 证据分析师 | 证据效力评估、证据链完整性分析 |
| **ContractStewardAgent** | 合同管家 | 合同全生命周期管理、到期提醒 |
| **SentimentAgent** | 舆情分析师 | 舆情监控、情感分析、预警推送 |

---

## 五、三层记忆系统

```
┌─────────────────────────────────────────────────────┐
│              多层融合检索 (MultiTierRetrieval)         │
│                                                     │
│   用户查询 ──→ [并行检索三层] ──→ [加权融合] ──→ 上下文  │
│                                                     │
├─────────────────┬─────────────────┬─────────────────┤
│   语义记忆       │   情景记忆        │   工作记忆      │
│   Semantic       │   Episodic       │   Working       │
│                 │                  │                 │
│ • 法律知识       │ • 历史案例        │ • 会话上下文    │
│ • 法规条文       │ • 执行轨迹        │ • 中间结果      │
│ • 专业术语       │ • 用户交互记录    │ • 临时数据      │
│                 │                  │                 │
│ 持久存储         │ 自动归档          │ 单次会话        │
│ Qdrant 向量库    │ Qdrant + PG      │ Redis           │
└─────────────────┴─────────────────┴─────────────────┘
```

---

## 六、进化学习系统

```
用户使用 → 评分反馈 (1-5星)
               │
               ▼
        ┌──────────────┐
        │ FeedbackPipeline │
        │  反馈管道       │
        └──────┬───────┘
               │
     ┌─────────┼─────────┐
     ▼                   ▼
≥ 4 星               < 3 星
成功模式              失败模式
     │                   │
     ▼                   ▼
┌────────────────────────────┐
│  ExperienceExtractor        │
│  经验模式提取                │
│  • DAG 优化模式             │
│  • 推理模板                 │
│  • 协作模式                 │
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│  PolicyOptimizer            │
│  策略优化器                  │
│  • Agent 组合优化           │
│  • DAG 结构调整             │
│  • 实时策略切换             │
└────────────────────────────┘
```

---

## 七、A2UI 动态渲染框架

```
Agent 输出结构化 JSON
        │
        ▼
┌──────────────────┐
│ A2UIRenderer     │ ← 核心渲染器
│ (组件映射表)      │
├──────────────────┤
│ 30+ 专业组件:     │
│                  │
│ • RiskCard       │  风险评估卡片
│ • ContractCompare│  合同对比卡片
│ • FeeEstimate    │  费用估算卡片
│ • CaseProgress   │  案件进度卡片
│ • Recommendation │  推荐建议卡片
│ • FormSheet      │  表单交互
│ • ProgressSteps  │  流程步骤
│ • RiskIndicator  │  风险指示器
│ • Button/Input   │  基础交互
│ • Alert/Card     │  信息展示
│ • TypingIndicator│  输入指示
│ • Lottie 动画    │  状态动画
└──────────────────┘
```

---

## 八、安全架构

```
┌──────────────────────────────────────────────┐
│                 安全防护层                     │
├──────────────┬───────────────┬───────────────┤
│  认证与授权    │   输入防护      │   数据保护     │
│              │               │               │
│ JWT (HS256)  │ SQL 注入防护   │ bcrypt 密码    │
│ Token 黑名单  │ XSS 检测      │ API Key 加密   │
│ 刷新 Token   │ 命令注入防护   │ PII 脱敏       │
│ RBAC 6 角色  │ 文件上传校验   │ HTTPS 传输     │
│ 30+ 权限点   │               │               │
│ OAuth 2.0    │               │               │
├──────────────┴───────────────┴───────────────┤
│                 限流与审计                     │
│                                              │
│ Redis 滑动窗口限流 (60/min, 1000/hr)          │
│ 操作审计日志 (AuditLog)                       │
│ 多租户隔离 (Organization)                     │
└──────────────────────────────────────────────┘
```

---

## 九、部署架构

```
┌─────────────────────────────────────────────────┐
│              Docker Compose 编排                 │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ frontend │  │ backend  │  │  PostgreSQL  │  │
│  │ React    │  │ FastAPI  │  │    15        │  │
│  │ :80      │  │ :8001    │  │    :5432     │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Redis   │  │  Qdrant  │  │   Neo4j      │  │
│  │  7       │  │  v1.12   │  │   5          │  │
│  │  :6379   │  │  :6333   │  │   :7687      │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
│                                                 │
│  ┌──────────────┐                               │
│  │    MinIO      │                               │
│  │  对象存储      │                               │
│  │  :9000        │                               │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘
```

---

## 十、数据流向图

### 10.1 AI 对话完整链路

```
用户输入
  │
  ├─ 文本 / 文件 / 语音
  │
  ▼
ChatInput (前端)
  │
  ▼ POST /api/v1/chat/messages (SSE)
  │
ChatRoute (路由)
  │
  ▼
ChatService → LegalWorkforce
  │
  ├─ 1. MultiTierRetrieval (记忆检索)
  │     ├─ 语义记忆 → 相关法律知识
  │     ├─ 情景记忆 → 类似历史案例
  │     └─ 工作记忆 → 当前对话上下文
  │
  ├─ 2. CoordinatorAgent (意图识别)
  │     └─ 生成 DAG 执行计划
  │
  ├─ 3. Agent 并行执行 (DAG)
  │     ├─ LegalResearch → 法规检索
  │     ├─ ContractReview → 条款审查
  │     ├─ RiskAssessment → 风险评估
  │     └─ ...
  │
  ├─ 4. ConsensusAgent (意见汇总)
  │
  ├─ 5. A2UI 组件生成
  │     └─ 结构化 JSON → 风险卡片/对比表/推荐
  │
  └─ 6. 流式推送到前端
        └─ SSE / WebSocket → StreamingMessage
```

### 10.2 合同审查完整链路

```
用户上传合同
  │
  ▼ POST /api/v1/contracts/upload-and-review
  │
DocumentParser (文档解析)
  │ PDF / DOCX / TXT → 纯文本
  ▼
ContractReviewAgent (AI 审查)
  │
  ├─ 条款拆分分析
  ├─ 风险识别 (critical/high/medium/low)
  ├─ 原文定位 (original_text)
  └─ 修改建议生成 (suggested_text)
  │
  ▼
前端审阅界面 (review step)
  │
  ├─ 左侧: 合同原文 + 风险高亮
  ├─ 右侧: 风险卡片 + 接受/撤回
  └─ 底部: 一键接受 / 应用修改
  │
  ▼ POST /api/v1/contracts/{id}/apply-suggestions
  │
ContractService.apply_suggestions()
  │ 从后往前替换文本 (避免位移)
  ▼
保存 / 下载
  ├─ POST /save-file → 服务器持久化
  ├─ GET /download?format=pdf → PDF 导出
  └─ GET /download?format=docx → DOCX 导出
```

---

## 十一、项目统计

| 指标 | 数量 |
|:-----|:-----|
| 后端 Python 文件 | 131 |
| 前端 TypeScript/TSX 文件 | 200+ |
| 数据库表 | 40+ |
| API 路由端点 | 100+ |
| 专业 AI Agent | 18 |
| 业务服务 | 47 |
| UI 组件 | 100+ |
| A2UI 专业卡片 | 30+ |
| 自定义 React Hooks | 5 |
| 安全权限点 | 30+ |

---

## 十二、环境变量配置

| 变量 | 用途 | 示例值 |
|:-----|:-----|:-------|
| `DATABASE_URL` | PostgreSQL 连接 | `postgresql+asyncpg://user:pass@localhost/db` |
| `REDIS_URL` | Redis 连接 | `redis://localhost:6379/0` |
| `QDRANT_URL` | Qdrant 向量库 | `http://localhost:6333` |
| `NEO4J_URI` | Neo4j 图数据库 | `bolt://localhost:7687` |
| `OPENAI_API_KEY` | OpenAI API | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API | `sk-ant-...` |
| `QWEN_API_KEY` | 通义千问 API | `sk-...` |
| `WECHAT_APP_ID` | 微信开放平台 | — |
| `WECHAT_APP_SECRET` | 微信密钥 | — |
| `ALIPAY_APP_ID` | 支付宝开放平台 | — |
| `ALIPAY_PRIVATE_KEY` | 支付宝私钥 | — |
| `JWT_SECRET_KEY` | JWT 签名密钥 | 随机字符串 |
| `DEV_MODE` | 开发模式 | `true` / `false` |

---

*文档生成日期: 2026-03-23*
*系统版本: Anxin Smart Assistant v1.0*
