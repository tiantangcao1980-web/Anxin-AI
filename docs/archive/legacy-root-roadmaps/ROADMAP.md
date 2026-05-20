# ⚠️ 已弃用 — v1.0 法务版历史路线图

> ```
> ╔══════════════════════════════════════════════════════════════╗
> ║  此文档为 v1.0「安心法务」历史路线图（2026-04-02）            ║
> ║  仅供回顾，不再维护。请勿据此规划新工作。                     ║
> ║                                                                ║
> ║  当前权威执行计划：                                            ║
> ║    • 总导航  → docs/00-project-execution-map.md               ║
> ║    • V3 路线图 → docs/v3/roadmap.md（P0-P21 完整阶段）         ║
> ║    • 商业交付  → docs/audit/PLAN.md                           ║
> ╚══════════════════════════════════════════════════════════════╝
> ```
>
> 制定日期：2026-04-02 | 预计周期：3个月（6个Sprint，Sprint 1-5 大部分已实施）

---

## 核心战略定位

**"低幻觉、高质量、合规先行"** — 当前法律AI行业最大痛点：
- 35%的AI合同审查幻觉率
- 仅20%的AI文书建议有参考价值
- 仅17%的系统实时同步最新法规
- 80%用户试用3-5款工具仍不满意

**差异化方向：**
1. 引用溯源 + RAG降低幻觉率至<10%
2. AI内容标识合规（GB 45438-2025，行业首批）
3. 法律文书质量做到"修改最少"
4. 实时协作编辑（蓝海，无竞品实现）
5. 智能条件模板引擎（所有竞品仍为静态模板）

---

## Sprint 1（第1-2周）— 合规基础 + 引用溯源

### 1.1 AI内容标识合规（GB 45438-2025）[P0]
**目标**：所有AI生成内容必须标识，满足《人工智能生成合成内容标识办法》

**后端改动：**
- `backend/src/core/ai_labeling.py` — 新建AI内容标识服务
  - 文本内容添加隐式标识（元数据水印）
  - 生成内容添加显式标识前缀
  - 文档导出自动添加AI辅助生成声明
- `backend/src/api/routes/chat.py` — 流式输出附加AI标识元数据
- `backend/src/api/routes/documents.py` — 生成文档标记AI辅助
- `backend/src/services/document_export.py` — PDF/DOCX导出页脚添加标识

**前端改动：**
- `frontend/src/components/chat/` — AI消息气泡添加标识图标
- `frontend/src/components/` — 通用AI标识组件

**涉及法规：**
- 《生成式人工智能服务管理暂行办法》
- 《人工智能生成合成内容标识办法》(2025.9.1施行)
- GB 45438-2025 国家标准

### 1.2 合同审查引用溯源机制 [P0]
**目标**：每个审查意见附带法条引用，可点击验证

**后端改动：**
- `backend/src/services/legal_citation.py` — 新建法律引用服务
  - 法条引用解析（"民法典第XXX条"→结构化引用）
  - 引用验证（检查法条编号有效性）
  - 引用链接生成（国家法律数据库URL）
- `backend/src/agents/contract_reviewer.py` — 审查结果增加引用解析
- `backend/src/prompts/agents/contract_reviewer.txt` — 要求输出带编号引用

**前端改动：**
- `frontend/src/pages/ContractReview.tsx` — 法条引用可点击展开
- 新建引用卡片组件，显示法条原文摘要

### 1.3 智能条件合同模板引擎 [P1]
**目标**：根据用户输入动态生成合同条款（区别于静态模板）

**后端改动：**
- `backend/src/services/template_engine.py` — 新建条件模板引擎
  - 模板定义格式（JSON Schema + 条件分支）
  - 变量插值 + 条件渲染
  - 地区司法差异适配（如不同省份的违约金上限）
- `backend/src/api/routes/templates.py` — 模板CRUD API
- `backend/src/models/template.py` — 模板数据模型
- 预置10套常用合同模板（买卖/租赁/劳动/服务/借款/股权/保密/合作/技术开发/代理）

**前端改动：**
- `frontend/src/components/templates/TemplateWizard.tsx` — 模板向导组件
  - 分步填写表单（根据合同类型动态生成）
  - 实时预览合同内容
  - 条件分支可视化

---

## Sprint 2（第3-4周）— RAG知识检索 + 知识图谱

### 2.1 LightRAG法律知识图谱集成 [P0]
**目标**：构建法律法规+案例+合同模板的知识图谱，Hybrid检索替换静态Prompt

**后端改动：**
- `backend/src/services/legal_rag.py` — 新建RAG检索服务
  - 接入LightRAG（pip install lightrag-hku）
  - 法律法规文档入库管道
  - Hybrid检索模式（Low-Level精确法条 + High-Level主题分析）
  - 检索结果格式化为Prompt上下文
- `backend/src/services/legal_data_loader.py` — 法律数据加载器
  - 民法典、劳动法、公司法等核心法律全文导入
  - 最高法司法解释导入
  - 支持增量更新（新法规自动融入）
- `backend/src/agents/base.py` — Agent基类增加RAG上下文注入
- `backend/data/legal_corpus/` — 法律语料目录

### 2.2 Agent RAG增强 [P0]
**目标**：所有法律Agent的回答都基于检索到的法律知识

**后端改动：**
- `backend/src/agents/contract_reviewer.py` — 审查前先检索相关法条
- `backend/src/agents/legal_advisor.py` — 咨询回答引用法律依据
- `backend/src/agents/document_drafter.py` — 起草时参考类似合同案例
- `backend/src/agents/litigation_strategist.py` — 诉讼分析引用判例

### 2.3 法律数据库基础建设 [P1]
**后端改动：**
- 导入民法典合同编全文（463-988条）
- 导入劳动合同法及实施条例
- 导入公司法(2024修订)
- 导入消费者权益保护法
- 导入数据安全法/个人信息保护法
- 结构化存储：法条编号→标题→正文→关联条文→司法解释

---

## Sprint 3（第5-6周）— 双循环审查 + 文书质量

### 3.1 双循环合同审查架构 [P1]
**目标**：从单Agent审查升级为分析循环+审查循环的多Agent协作

**后端改动：**
- `backend/src/agents/contract_investigator.py` — 新建合同调查Agent
  - 提取合同关键要素
  - 查询RAG知识库获取相关法条
  - 输出结构化分析笔记
- `backend/src/agents/contract_reviewer.py` — 重构为审查循环
  - 接收调查Agent的分析笔记
  - 基于法条知识逐条审查
  - 交叉验证风险点
- `backend/src/agents/review_checker.py` — 新建审查验证Agent
  - 验证审查结论的法律依据准确性
  - 检查是否遗漏关键条款
  - 生成置信度评分
- `backend/src/agents/workforce.py` — 新增review_pipeline DAG

### 3.2 文书生成质量验证 [P1]
**目标**：生成的文书通过自动化质量检查

**后端改动：**
- `backend/src/services/document_validator.py` — 文书质量验证器
  - 结构完整性检查（标题/编号/签署区是否齐全）
  - 字数达标检查（合同>=3000字）
  - 法条引用准确性验证
  - 必备条款覆盖率检查
  - 格式规范性验证
- `backend/src/agents/document_drafter.py` — 生成后自动验证+迭代

### 3.3 会话记忆与审查经验沉淀 [P1]
**后端改动：**
- `backend/src/services/review_memory.py` — 审查记忆服务
  - 保存审查会话（发现+用户修正）
  - 相似审查检索（复用历史经验）
  - 统计分析薄弱环节
- `backend/src/models/review_memory.py` — 审查记忆数据模型

---

## Sprint 4（第7-8周）— 电子签署 + 支付

### 4.1 电子签署集成 [P0]
**目标**：合同审查→修改→签署全流程闭环

**后端改动：**
- `backend/src/services/esign_service.py` — 重构电子签署服务
  - 集成法大大/e签宝 SDK（选择其一）
  - 合同发起签署流程
  - 签署状态回调
  - 签署完成后自动归档
- `backend/src/api/routes/esign.py` — 完善电签API
- 配置：`ESIGN_PROVIDER`、`ESIGN_APP_ID`、`ESIGN_SECRET`

### 4.2 支付网关集成 [P0]
**后端改动：**
- `backend/src/services/payment_service.py` — 支付服务
  - 微信支付（JSAPI/Native）
  - 支付宝（电脑网站/手机网站）
  - 订单管理、退款处理
  - Webhook回调验签
- `backend/src/api/routes/payments.py` — 重构支付API
- 配置：`WECHAT_PAY_*`、`ALIPAY_*`

### 4.3 订阅计费体系 [P1]
**后端改动：**
- `backend/src/services/subscription_service.py` — 订阅管理
  - 三档套餐：个人版(免费/受限) / 专业版 / 企业版
  - 用量计量（AI调用次数、文档生成数、存储空间）
  - 自动续费、到期提醒
- 前端：订阅页面、套餐选择、支付流程

---

## Sprint 5（第9-10周）— 协作增强 + 知识管理

### 5.1 编辑器高级扩展 [P1]
**前端改动：**
- Callout扩展（法律警示块：风险提示/重要条款/修改说明）
- Toggle/Details折叠块（合同定义/附件/补充条款）
- 版本Diff对比视图（合同修订对比高亮）
- @提及功能（标注团队成员审阅）

### 5.2 律所知识管理平台 [P2]
**目标**：律所内部案例经验结构化沉淀和复用

**后端改动：**
- `backend/src/services/knowledge_management.py`
  - 案例经验库（按领域/类型分类）
  - 文档模板管理（律所自定义模板）
  - 智能推荐（根据当前任务推荐相关经验）
- 前端：知识库浏览、搜索、标签管理

### 5.3 客户门户 [P2]
**目标**：客户可自助查看案件进度、文档、账单

- 独立的客户视图路由
- 文档共享（访问码机制）
- 进度追踪面板
- 在线沟通（IM集成）

---

## Sprint 6（第11-12周）— 性能优化 + 上线准备

### 6.1 性能优化 [P1]
- 多Agent流式聚合优化（sequential→streaming追加）
- 知识图谱大规模性能优化
- 前端首屏加载优化（代码分割、懒加载）
- 数据库查询优化（索引、缓存策略）

### 6.2 安全加固与合规审计 [P0]
- 生成式AI服务备案申请
- 数据分类分级实施
- 个人信息脱敏处理加固
- 安全渗透测试
- 合规审计报告

### 6.3 部署与上线 [P0]
- 生产环境部署（Docker Compose + Nginx）
- SSL证书配置
- 监控告警配置（Grafana + Prometheus）
- 数据备份策略
- 灰度发布计划

---

## 已完成的基础工作（v0.9.0-beta）

| 模块 | 完成度 | 关键改动 |
|------|--------|---------|
| 文件上传(Excel/CSV) | 100% | document_parser.py + 前端accept |
| 合同审查提示词 | 100% | 56行→200+行，三层审查框架 |
| 文书起草提示词 | 100% | 53行→300+行，完整结构模板 |
| 编辑器升级 | 100% | TipTap扩展+A4布局+Slash命令 |
| DOCX/PDF导出 | 100% | 专业法律文书排版 |
| Agent代码增强 | 100% | 类型专项审查+结构指南+JSON解析 |
| 参考项目研究 | 100% | MrDoc/docmost/DeepTutor |

---

## 风险与依赖

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LightRAG集成复杂度 | 可能延期1周 | 先用简单向量检索兜底 |
| 电签SDK接入周期 | 需要企业认证 | 提前申请开发者账号 |
| 支付备案周期 | 2-4周审核 | Sprint 2即开始申请 |
| AI备案审核 | 周期不确定 | 优先准备材料 |
| 法律语料版权 | 需确认来源合法性 | 使用公开的法律法规数据 |

---

## 团队分工建议

- **后端**：RAG服务、Agent重构、支付/电签集成
- **前端**：模板向导、引用卡片、编辑器扩展、客户门户
- **AI/数据**：法律语料整理、知识图谱构建、Prompt优化
- **合规**：AI备案、数据安全评估、合规文档

---

*本路线图每2周评审一次，根据实际进度和反馈调整优先级。*
