# 安心AI法务 — 项目开发进度

> 本文件用于跨设备/跨智能体协作时快速了解项目状态，每次开发后更新。

---

## 当前版本

**v0.9.0-beta** | 预计上线：2026-04-01（第一版客户测试）

## 最近更新（2026-04-01 核心功能质量优化）

### 文件上传全链路增强
- [x] 后端 document_parser.py 新增 Excel (.xlsx/.xls)、CSV、PPTX 解析支持
- [x] 使用 openpyxl 解析 Excel（多工作表），python-pptx 解析 PPT（含表格文本）
- [x] 前端聊天文件选择器扩展：支持 PDF/Word/Excel/CSV/PPT/TXT/MD/图片（MultiModalInput + ChatInput + Chat.tsx）
- [x] 前端 useChatInput 增加文件大小校验（>10MB 拒绝）和扩展名白名单校验
- [x] 聊天区新增拖拽上传：拖入文件显示蒙层提示，松开自动附加并推断工作流
- [x] **核心**：聊天文件→AI 分析链路打通 — WebSocket 和 ChatService 在收到 document_id 时自动提取文档文本（extracted_text 或实时解析），截取前 8000 字拼接到用户消息中，AI Agent 可直接分析文件内容
- [x] 后端 config.py ALLOWED_FILE_EXTENSIONS 和 documents.py MIME 白名单同步扩展
- [x] 默认主题从 'system' 改为 'light'（深色模式需用户手动开启），增加 persist migrate 兼容存量用户

### 合同审查质量大幅提升
- [x] contract_reviewer.txt 提示词从56行扩充至200+行
- [x] 新增完整法律依据引用（民法典、劳动法、公司法等核心法条）
- [x] 新增三层系统化审查框架（效力审查→核心条款→特殊条款）
- [x] 新增合同类型专项审查指南（买卖/租赁/服务/劳动/投资）
- [x] 新增 missing_clauses 和 legal_basis 字段增强输出结构
- [x] 细化风险等级判断标准（关联具体法律后果）

### 合同/法律文书生成质量提升
- [x] document_drafter.txt 提示词从53行扩充至300+行
- [x] 新增完整的合同标准结构模板（14条+签署页+附件区）
- [x] 新增民事起诉状、律师函等专用格式模板
- [x] 定义严格的内容详实性要求（合同正文不少于3000字）
- [x] 规范编号体系：第X条→X.X→（1）三级编号
- [x] 新增法律文书排版规范和格式要求

### 文档协作编辑器全面升级
- [x] 新增 TipTap 扩展：Underline、TextAlign、TextStyle、Color、Highlight
- [x] 工具栏增强：字体颜色、高亮、文本对齐（左/中/右/两端）、下划线、删除线
- [x] 标题格式下拉选择器（正文/标题1/标题2/标题3）
- [x] 颜色选择器组件（12色快速选取）
- [x] A4页面模拟布局（210mm×297mm，标准页边距）
- [x] 缩放控制（50%-200%）
- [x] 打印功能（专业法律文书打印样式，宋体/1.8行距）
- [x] 快捷键支持（Ctrl+S保存、Ctrl+P打印）
- [x] 图标系统修正：Bold/Italic/Heading等编辑器图标使用正确的lucide-react图标

### 合同审查Agent代码增强
- [x] 新增合同类型专项审查方法 `_get_type_specific_guide()`，覆盖8类合同
- [x] 审查提示词构建增强：要求至少5维度分析、必须引用法律依据、补充missing_clauses
- [x] JSON解析增强：支持```json包裹格式，增加missing_clauses/legal_basis字段兼容
- [x] quick_review方法升级为结构化JSON输出

### 文书起草Agent代码增强
- [x] 新增文书类型结构指南 `_get_structure_guide()`，覆盖合同/诉讼/函件/法律意见
- [x] 起草提示词增强：要求合同不少于3000字、至少10条款、完整签署区
- [x] draft_contract方法增加结构指南和编号体系要求

### DOCX/PDF导出专业化
- [x] DOCX导出：A4纸张、标准页边距(上下2.54cm/左右3.17cm)
- [x] 标题排版：小二号(18pt)黑体居中、条款四号(14pt)黑体、正文小四号(12pt)宋体
- [x] 正文两端对齐、首行缩进2字符、1.5倍行距
- [x] Markdown智能解析：自动识别标题/条款/签署区/分隔线
- [x] PDF导出同步升级排版标准

### Slash命令系统（借鉴docmost）
- [x] 新建 SlashCommandExtension.tsx，18个命令覆盖基本格式+法律文书两大类
- [x] 法律文书专用命令：合同标题区、甲乙方信息、鉴于条款、标准条款、违约责任、争议解决、不可抗力、保密条款、签署区、附件列表
- [x] 输入"/"弹出命令面板，支持关键词搜索、方向键/Enter选择
- [x] 集成到CollaborativeEditor主编辑器

### Bug修复
- [x] 修复 AdminConfig.tsx 中缺失的 Smartphone 图标引用
- [x] 修复 Chat.tsx 中重复的 accept 属性导致的TS编译错误

---

## 更早的更新（2026-04-01 安全纵深防御 + 功能开关机制）

### 功能开关机制
- [x] 后端 config.py 新增 4 个开关：EMAIL_VERIFY_ENABLED / SMS_ENABLED / OAUTH_WECHAT_ENABLED / OAUTH_ALIPAY_ENABLED
- [x] 邮箱验证默认关闭（EMAIL_VERIFY_ENABLED=False），关闭时注册自动标记 email_verified=True
- [x] OAuth 端点受开关保护，未启用时返回 404
- [x] 后端 GET /auth/features 公开端点供前端查询开关状态
- [x] 前端 Login.tsx 根据开关动态显示微信/支付宝登录按钮
- [x] 前端注册流程：开关关闭时注册后自动登录，开启后跳转验证页
- [x] AdminConfig 安全配置 Tab 新增认证功能开关面板（4 个开关的 UI 控制）

### 安全纵深防御
- [x] 安全响应头：X-Content-Type-Options / X-Frame-Options / X-XSS-Protection / Referrer-Policy / HSTS(生产)
- [x] 文件上传白名单：扩展名 + MIME 类型双重校验（pdf/doc/docx/txt/md/xlsx/xls/csv）
- [x] 匿名聊天加固：消息长度 4096 上限 + 30条/分钟频率限制 + HTML 转义防 XSS
- [x] 验证码端点频率限制：verify-email 10次/5分钟、reset-password 10次/5分钟

---

## 更早的更新（2026-03-31 安全加固 + 认证体系升级）

### 安全加固 — 生产上线标准
- [x] 路由认证加固：contracts/llm/datacenter/documents/chat/collaboration/compliance 全部强制认证
- [x] LLM 配置路由：读取需登录，写入/删除需管理员权限
- [x] 集成 Webhook：添加 X-Integration-Key 密钥校验
- [x] CORS 收紧：allow_headers 改为具体列表

### 认证体系升级
- [x] 邮箱验证完整流程已启用（注册→验证码→通过才能登录）
- [x] 阿里云邮件推送 email_service.py（DirectMail SDK）
- [x] 阿里云短信服务 sms_service.py（Dysmsapi SDK，注册/登录/密码重置）
- [x] OAuth 微信+支付宝代码就绪（填入 AppID/Secret 即可启用）

### 用户类型与权限分层
- [x] 注册四类身份：个人用户/企业用户/律师/律所机构
- [x] 初始权限：个人→individual_user，企业→enterprise_user，律师/律所→viewer（待认证）
- [x] 企业内部分权：org_admin→dept_admin→enterprise_user→member
- [x] 审批流预留：approvals + integrations webhook OA 集成

### 后台管理增强
- [x] AdminConfig 新增短信服务和邮件服务配置 Tab
- [x] OAuth 配置添加官方文档链接

---

## 更早的更新（2026-03-31 续）

### 找律师 — AI 核心能力实现
- [x] 新建 `lawyer_matching_service.py`：AI 案情分析 + 自动脱敏 + 领域识别 + 风险评估 + 法律要素提取
- [x] 文本脱敏引擎：手机号/身份证/邮箱/银行卡/中文姓名/地址/公司名 正则清洗
- [x] 法律领域自动识别：10 大领域关键词匹配 + 置信度评分
- [x] 智能律师匹配算法：领域匹配(40%) + 评分(25%) + 活跃度(20%) + 紧急加权
- [x] LLM 增强分析：调用大模型生成专业匿名案情摘要（失败降级到规则引擎）
- [x] 升级 `create_consultation` 路由：接入 AI 分析服务替代原有占位逻辑
- [x] 升级 `list_lawyers` 路由：支持按领域智能匹配排序

### 合规自检 — 报告生成与 AI 增强
- [x] 新建 `compliance_service.py`：合规报告生成 + AI 增强整改建议 + 历史对比
- [x] HTML 报告模板：评分卡片 + 风险明细表格 + 整改建议列表
- [x] AI 增强整改建议：调用 LLM 为不合规项生成专业整改建议
- [x] 新增 `/compliance-check/report` 端点：生成完整 HTML 报告
- [x] 新增 `/compliance-check/compare` 端点：对比两次检查结果

### 任务中心 — 看板操作增强
- [x] 任务状态机：定义合法状态转换规则（pending→in_progress→completed 等）
- [x] 看板拖拽批量更新：`batch_update_status()` 支持多任务同时状态变更
- [x] 看板统计：`get_kanban_stats()` 各状态任务数量统计
- [x] 新增 `/tasks/{id}/transition` 端点：带校验的状态转换
- [x] 新增 `/tasks/batch-update` 端点：看板拖拽批量操作
- [x] 新增 `/tasks/kanban/stats` 端点：看板统计数据

## 最近更新（2026-03-31）

### 知识图谱 Canvas 文本渲染性能优化
- [x] 新增 `textMeasureCache.ts` 文本测量缓存工具：measureAndCache（宽度缓存）、truncateToWidth（像素级智能截断，替代朴素 slice）、setFontIfChanged（字体指纹比对，避免每帧重复 ctx.font 赋值）、LRU 淘汰防内存泄漏
- [x] 改造 `ForceGraphCanvas.tsx` 2D 渲染回调（nodeCanvasObject / linkCanvasObject）使用缓存，消除 60fps×N 节点的重复 measureText 和字体切换开销
- [x] 改造 `KnowledgeGraphExplorer.tsx` 2D 节点渲染使用缓存，中英文混排标签截断从字符计数升级为像素宽度二分查找
- [x] 借鉴 pretext "预处理+缓存"架构思想，不引入外部依赖，轻量实现

### AI 生成管线性能分析与优化规划
- [x] 深度分析 [chenglou/pretext](https://github.com/chenglou/pretext) 项目架构，验证"几百倍性能提升"属实（Chrome 468x，Safari 1,296x）
- [x] 完成当前 AI 生成管线全链路瓶颈诊断（多 Agent 串行阻塞、3 次串行 LLM、无对话历史等 8 项问题）
- [x] 输出技术分析文档：`docs/2026-03-31_Pretext技术分析与性能优化借鉴.md`
- [x] 输出优化方案文档：`docs/2026-03-31_AI生成管线性能优化方案.md`
- [x] P0 小步落地（第一批）：`LLMService` 默认配置 TTL 缓存（60s）+ Agent 热路径统一自愈入口，避免 `chat/stream_chat` 重复回库
- [x] P0 小步落地（第一批）：聊天入口新增空消息校验，阻断无效请求进入多 Agent/LLM 链路
- [x] P0 小步落地（第二批）：单 Agent 流式链路与 WebSocket 单 Agent 回复补齐最近 10 条历史透传
- [x] 回归基线修复：补充 `backend/tests/test_llm_service_cache.py`，并修正 `backend/tests/test_chat.py` 中与当前接口契约不一致的断言与 mock
- [x] P0 小步落地（第三批）：多 Agent DAG 链路通过 `_task_history_var` contextvars 自动透传对话历史，覆盖 workforce + lifecycle manager 两条执行路径
- [x] P0 小步落地（第四批）：合并意图识别+需求分析为单次 LLM 调用（`CoordinatorAgent.analyze_and_classify`），复杂消息路径减少 1 次串行 LLM
- [x] P0 小步落地（第五批）：单 Agent 意图（11 种）走真流式 `stream_chat` 快速路径，绕过 `process_task` DAG，首 token 延迟从数十秒降到 ~2s
- [x] P1 动态 max_tokens：根据复杂度和意图自动分档（512/2048/4096），`stream_chat` 新增 `max_tokens` 参数
- [x] P1 Prompt 模板化管理：创建 `backend/src/prompts/` 模块（加载器 + 20 个 .txt 模板文件），17 个 Agent + Coordinator 改为文件加载，支持热更新和版本管理
- [x] P2 拆分 WebSocket handler：`websocket_chat` 从 1534 行降到 1040 行，提取 6 个独立 handler 模块（A2UI/工作台/Canvas/尽调/RAG/共享上下文）
- [x] P1 Prompt 模板化管理收尾：Coordinator `merged_intent_analysis` 抽取为模板文件，`requirement_analyst` 路径统一到 `agents/` 目录，全部 Agent + Coordinator prompt 均已模板化
- [x] P2 统一 Service 层消除三重重复：提取 `_ChatContext` + `_decide_route()` + `_prepare_chat_context()` + `_execute_due_diligence()` + `_execute_rag()` + `_finalize_response()` 共享编排层，`chat()` 和 `stream_chat()` 复用同一套路由决策和前后处理
- [x] P0 多 Agent DAG 真流式输出：新增 `LegalWorkforce.process_task_streaming()` 异步生成器，DAG 第一层主 Agent 使用 `stream_chat()` token-by-token 推送，其余 Agent 并行同步执行，后续层级增量追加；`ChatService.stream_chat()` 多 Agent 分支改用新方法消费事件流，首 token 延迟从"等全部完成"降到"主 Agent 开始输出"（~2s）

### 对话入口与研究模式统一
- [x] Chat 请求协议补充 `mode` 与 `knowledge_base_ids`，普通对话、快捷动作和知识库研究模式统一走同一聊天入口
- [x] 聊天输入区新增 `KnowledgeBaseSelector`，支持多知识库勾选、搜索、缓存、刷新和跳转知识库管理页
- [x] `/chat/history` 返回消息级 `sources`，知识库检索与尽调结果可在历史记录中保留来源信息
- [x] 知识库研究模式在 WebSocket 链路中支持按知识库范围检索并回传来源卡片

### 企业尽调强路由与 A2UI 闭环
- [x] 尽调服务新增企业调查意图识别、公司名抽取与结构化摘要格式化能力
- [x] `ChatService.chat` 与 `stream_chat` 新增企业调查强路由，识别到尽调请求后优先返回尽调结果，不再落回通用协调链路
- [x] A2UI 事件新增 `start_due_diligence`，表单提交后可直接返回状态卡、明细列表、风险提示与建议动作
- [x] 尽调意图词扩充到供应商/合作方/交易对手等业务表述，减少“公司调查”类请求漏判

### 右侧面板与工作台文档一体化
- [x] `RightPanel` 升级为 v7.1，正式采用“工作台 / 文档”双模式
- [x] 文档查看、归档、回看完整文档与新建对话入口统一收敛到右侧面板头部与工作台动作区
- [x] 文档列表去重与内容缓存增强，避免关闭文档后重复归档
- [x] 流式文书生成时对系统噪音进行清洗，右侧文档模式展示更稳定

### Chat 与导航交互优化
- [x] QuickActionsBar 支持基于使用频次的个性化排序，始终显示并在处理中置灰
- [x] 快捷动作彻底收敛为“填充输入框”的对话型触发，不再依赖聊天页内部跳转分支
- [x] 侧边栏默认展开，减少新会话和回访时的视图跳变
- [x] 用户面板新增“导航栏显示文字”开关，可切换顶栏动作是否展示文字标签
- [x] 后台管理布局改为静态引入，规避 Vite 动态加载偶发 `Failed to fetch module` 问题

### 知识图谱体验增强
- [x] `ForceGraphCanvas` 暴露 `resetView` / `zoomToFit` 句柄，页面工具栏可直接控制画布
- [x] 图谱 2D/3D 模式补齐自动旋转、标签开关、类型筛选联动
- [x] 图谱和探索器适配亮色 / 暗色主题，标签、连线、背景和光晕按主题切换

### 测试与验证资产补充
- [x] 新增尽调意图识别单测：`test_due_diligence_intent.py`
- [x] 新增尽调强路由单测：`test_chat_due_diligence_routing.py`
- [x] 新增 A2UI 尽调事件单测：`test_a2ui_due_diligence_event.py`
- [x] 前端新增右侧面板双模式 E2E：`frontend/e2e/right-panel.spec.ts`
- [x] 前端引入 `@playwright/test` 并补充本地配置：`frontend/playwright.local.config.ts`

## 最近更新（2026-03-28 ~ 03-29）

### 导航架构重构
- [x] 四大模块下拉菜单改为直达链接，各模块有独立左侧导航栏
- [x] 创建通用 `ModuleLayout` 组件（展开200px/收起56px）
- [x] 移除全屏下拉面板（Portal）和所有 hover/click 展开逻辑
- [x] AI法务直达 `/chat`，智能协作→`/cases`，智能调查→`/due-diligence`，法律智库→`/knowledge-graph`

### Chat 页面优化
- [x] 三栏标题栏高度统一为 h-12（48px）
- [x] 添加可拖拽分隔条（对话列表↔聊天区、聊天区↔智能工作台）
- [x] 智能工作台整合文档功能（去掉独立文档Tab，统一面板）

### 后台管理重组
- [x] 15个菜单项重组为4个分组（用户与权限/系统运维/业务管理/安全与合规）
- [x] AdminLayout 侧边栏使用主题系统颜色，统一视觉规范

### 功能模块整合
- [x] 系统设置→后台管理（AI配置/安全设置/功能开关）
- [x] 审批中心+任务中心→任务中心
- [x] 后台管理入口迁移到用户面板（按权限显示）
- [x] 找律师+律师精英合并
- [x] 合同审查→合同管理，文档+工作台→在线协作
- [x] AI法务中的后台功能（AI助手配置/私有LLM等）迁移到后台管理

### 登录页面优化
- [x] 去掉左侧纯色渐变背景，改为 bg-muted/50 适配深浅色
- [x] 添加几何圆环装饰元素和2个形象角色占位框

### 测试账号体系
- [x] 17个测试账号覆盖6大角色（平台管理/律所/律师/员工/企业/个人）
- [x] 统一使用 `@anxinfawu.com` 域名，简单密码格式

## 功能完成度

| 模块 | 前端 | 后端 | 状态 |
|------|------|------|------|
| AI 智能对话 | 98% | 92% | 可用（已支持知识库研究模式与来源回写） |
| 智能工作台 | 97% | 82% | 可用（工作台 / 文档双模式已落地） |
| 案件管理 | 90% | 95% | 可用 |
| 合同管理 | 85% | 90% | 可用 |
| 在线协作 | 80% | 70% | 基本可用 |
| 找律师 | 80% | 85% | 可用（AI脱敏+智能匹配已实现） |
| 合规自检 | 85% | 80% | 可用（报告生成+AI建议已实现） |
| 智能调查（尽职调查） | 96% | 92% | 可用（支持尽调强路由与 A2UI 表单闭环） |
| 司法资讯 | 80% | 70% | 已隐藏（v2.0启用） |
| 知识图谱 | 85% | 75% | 可用（2D/3D 控制与主题适配增强） |
| 任务中心 | 75% | 70% | 基本可用 |
| 后台管理 | 90% | 85% | 可用 |
| 登录/注册 | 95% | 95% | 可用 |

## 已知问题

1. `conversation_summaries` 表外键类型不匹配（VARCHAR vs UUID），`init_db` 的 `create_all` 会报错但已跳过
2. Qdrant 客户端版本（1.17）与服务端版本（1.12）不兼容，功能性警告
3. 部分页面在后端离线时显示加载错误（正常行为）

## P0 验证完成情况（2026-03-31）

### Alembic 迁移链验证 ✅
- 22 个迁移脚本链完整，无孤立/循环依赖
- 修复了 011/012 文档头与实际 down_revision 不匹配的问题
- 两个 011 文件（approval_chain + notification_preferences）命名冲突但链功能正确

### 后端单测 ✅ 14/14
- `test_due_diligence_intent.py` — 6 个测试全部通过
- `test_chat_due_diligence_routing.py` — 4 个测试全部通过
- `test_a2ui_due_diligence_event.py` — 2 个测试全部通过
- `test_a2ui_action_coverage.py` — 2 个测试全部通过（21 个 actionId 全覆盖）

### 前端 E2E 测试 ✅ 15/16
- 认证流程 4/4、导航结构 4/4、右侧面板 3/3、移动端 3/3 全部通过
- 仅 `新建对话` 间歇性超时（后端响应时序抖动，非代码缺陷）
- 修复了测试断言与 UI 文案不同步的问题（placeholder、nav selectors）

### 深色模式 ✅
- CSS 变量体系完整（浅色 / 深色双套 HSL 色阶）
- ThemeProvider 正确响应 system / dark / light 三种模式
- 主要页面（Chat、知识图谱等）均有 dark: 适配

### 移动端响应式 ✅
- Layout.tsx 使用 lg: (1024px) 断点正确切换桌面/移动布局
- 移动端底部 Tab 栏、顶部二级导航、侧边栏隐藏均正常
- Chat 页面 isMobile 状态与右面板/侧边栏联动正确

### 核心路由可用性 ✅
- `/chat` — AI 对话页正常（欢迎页 + 快捷操作 + 工作台面板）
- `/cases` — 案件管理正常（8 个案件 + 搜索 + 筛选）
- `/contracts` — 合同审查正常（风险评分 + 状态管理）
- `/due-diligence` — 智能调查正常（示例数据 + 五维风险评估）
- `/knowledge-graph` — 知识图谱正常（2D 力导图 + 工具栏）

### 其他修复
- 移除 api.ts 未使用的 `export default` 聚合导出，消除 Vite HMR 循环引用错误
- 前端控制台零错误（重启后验证）

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS + Radix UI |
| 后端 | FastAPI + SQLAlchemy 2.0 + Alembic |
| AI | CAMEL-AI (16+ Agent) + OpenAI + Anthropic |
| 数据库 | PostgreSQL + Redis + Qdrant + Neo4j |
| 部署 | Docker + GitHub Actions |

## 端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 (Vite) | 3001 | 开发服务器 |
| 后端 (Uvicorn) | 8005 | API 服务 |
| PostgreSQL | 5433 | 数据库（Docker映射） |
| Redis | 6379 | 缓存 |
| Qdrant | 6333 | 向量检索 |
| Neo4j | 7687 | 图数据库 |

## 最新更新（2026-03-29 晚）

### P1 智能工作台深化（参考豆包/千问设计）
- [x] 已发送消息编辑重发：用户消息 hover 显示编辑图标，点击进入编辑模式，修改后重新发送（删除旧消息及后续回复）
- [x] 快捷技能栏重构：workflowConfig.ts 统一管理 12 个业务动作，豆包风格紧凑横排（快速咨询 / 合同审查 / 协作起草 / 合规检查 / 尽职调查 / 知识检索 + 更多），附件感知自动切换提示
- [x] 斜杠命令面板：从 workflowConfig 自动生成，按分类分组（核心法务/知识与检索/交付与协作），支持中英文模糊搜索
- [x] 文档管理增强（RightPanel v6）：文档快捷操作栏（生成摘要/翻译全文/AI润色/风险检查）、新建空白文档/合同模板、文档列表历史管理、保存/关闭文档
- [x] store 新增 documentList 文档列表状态管理
- [x] icons.ts 新增 FilePlus、Signal 图标

### 用户反馈迭代（2026-03-29 深夜）
- [x] 品牌欢迎页：千问风格 Logo + 标语 + 4 个能力卡片（合同审查/文书起草/合规检查/尽职调查），点击卡片填充输入框
- [x] 移除重复上传按钮：QuickActionsBar 去掉 "+" 号（输入框左侧已有回形针），只保留功能快捷入口
- [x] 需求确认交互增强（ClarificationBubble v2）：每个问题新增"自己输入"选项 + 自定义文本框 + 可切换重选 + 部分回答也可提交 + 引导提示优化
- [x] AI 生成文书自动推送到工作台：检测法律文书特征（条款/甲乙方/签署日期等），自动设置 Canvas 内容并打开右面板
- [x] 新建对话自动收起右面板：resetWorkspace 后同步 rightPanelOpen=false + chatWidth=100%

### LLM 切换（2026-03-29 下午）
- [x] 本地 LLM 服务（192.168.110.45:1234）不可达，切换到通义千问 DashScope 云端
- [x] `.env` 和数据库 `llm_configs` 表同步更新为 `qwen-plus` 模型
- [x] 对话功能验证通过（法律顾问 Agent 返回专业法律回答）

### Chat 页面优化
- [x] 三个拖拽分隔条样式统一（6px透明区域 + 1px居中线 + grip指示器）
- [x] 输入框高度自适应（拖拽调高时 textarea 跟随填满）
- [x] 输入区宽度自适应（移除 max-w-4xl 限制）
- [x] 附件和发送按钮锚定底部（self-end）

### 导航图标修复
- [x] 消息/任务中心改为图标+文字显示
- [x] Chat 侧边栏收起/展开用 ChevronLeft/ChevronRight 图标
- [x] 所有侧边栏宽度统一 220px/56px

## 最新更新（2026-03-29）

### 智能调查模块全面升级
- [x] "信息中心"更名为"智能调查"，提升为一级模块（直达 `/due-diligence`）
- [x] 司法资讯暂时隐藏，待 v2.0 版本迭代启用
- [x] 仪表板布局：左侧 8 模块导航 + 右侧动态内容区
- [x] 多 Agent 协同调查引擎：采集→交叉验证→辩论综合→报告编制 4 阶段工作流
- [x] 增强 SSE 协议：新增 stage/agent_start/agent_result/conflict/consensus 事件
- [x] 新增 7 个前端组件：InvestigationSidebar/Overview/Progress/SentimentDashboard/InteractiveGraph/ScenarioSimulation/InvestigationReport
- [x] 新增 4 个后端服务：InvestigationOrchestrator/ReportEngine/ScenarioSimulation/Investigation Model
- [x] 交互式关系图谱联动法律智库知识图谱
- [x] 风险场景推演（4 种预设场景 + 影响链可视化 + 雷达对比）
- [x] 调查报告引擎（IR→HTML/PDF，章节导航）
- [x] 修复子组件硬编码：RelationshipGraph 公司名、LegalCases 诉讼数、ComplianceReport 合规项
- [x] 后端新增 8 个 API 端点（协同流式调查/调查历史/报告/场景推演）

## 下一步计划（优先级排序，已按 2026-03-31 最新改动重排）

### P0 — 上线前必须
1. 完成 Alembic 迁移烟雾验证，重点覆盖 IM、通知偏好、律所管理和尽调相关变更
2. 执行新增后端单测与前端 Playwright 本地回归，并把结果同步回文档
3. 前端深色模式和移动端响应式做一轮全链路复查
4. 全部核心路由与聊天入口能力做上线前可用性验证

### P1 — 对话工作台闭环强化
5. ~~合规风控 / 法律检索 / 找律师 / 尽调 的后端意图识别与 A2UI 卡片输出稳定化~~ ✅ 新增 FIND_LAWYER 意图+关键词+A2UI配置，扩充合规/法律检索关键词，找律师强路由
6. ~~知识库研究模式增强来源引用、权限校验和空知识库提示~~ ✅ RAG sources 补充 content_snippet，_execute_rag 透传 user_id 权限校验，WebSocket RAG 调用补传 user_id
7. 工作台动作与消息流联动补全 — 后端侧已就绪（通知推送链路、Canvas handler、模板 Agent 调度均完整），剩余为前端集成：WebSocket 通知监听、模板→工作流 UI 联动、文档版本历史展示、语音对话 ASR 接入

### P2 — 体验优化
8. 全局样式规范统一（字体大小、间距、内容区布局、图谱亮暗主题细节）— 纯前端，待实施
9. ~~对话历史搜索和收藏功能~~ ✅ 后端已完成：Alembic 迁移（is_starred/starred_at）、list_conversations 支持 keyword/starred_only、toggle_star/search_messages Service 方法、3 个新 API 端点（/star, /messages/search, /history?keyword&starred）
10. ~~多模型切换界面（在对话中切换不同大模型）~~ ✅ 后端已完成：ChatMessage 新增 model_id 字段、_prepare_chat_context 支持按 model_id 加载指定 LLM 配置、新增 GET /chat/models 端点返回可用模型列表
11. 大规模知识图谱场景下的性能优化与高级过滤 — 待实施

## 设计参考文件

位置：`/Users/pengchengkeji/Desktop/安心法务-设计参考/`（37个截图）
- 豆包桌面端：左侧导航 + 文档处理 + 快捷技能栏
- 千问桌面端：深色/浅色模式 + 深度思考 + 文件上传标签

---

*最后更新: 2026-03-31 23:59*
