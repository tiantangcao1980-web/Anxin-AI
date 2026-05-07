# 2026-03-10 AI法务智能体系统 最终升级方案定稿

## 1. 文档定位

本文档用于在现有项目重构讨论、正式产品文档、技术架构文档、技术选型决策书以及《AI智能体开源项目深度分析报告》基础上，对 AI法务智能体系统 的升级重构方案作最终定稿与收口。

本定稿文档自 2026-03-10 起，作为项目升级重构的最高优先级执行口径。

## 2. 外部分析报告结论吸收

已吸收《AI智能体开源项目深度分析报告》的核心判断：

1. OpenClaw 最值得借鉴的是 `Channel -> Session -> Agent -> Tool -> Memory` 的统一执行闭环，以及多渠道、多设备、工作区隔离能力。
2. HiClaw 最值得借鉴的是 `Manager -> Worker` 协作模型、`Worker 不持有真实凭证` 的安全设计、Matrix 可观测协作和集中式 Gateway。
3. ZeroClaw 最值得借鉴的是轻量内核、trait/接口可插拔、单二进制部署和混合检索思路。
4. CoPaw / AgentScope 最值得借鉴的是工程化记忆系统、长期记忆文件化、定时任务和模块解耦。
5. IronClaw 与 NanoClaw 强化了一个明确结论：安全、隔离、权限控制和注入防御不能后补，必须前置到架构层。

## 3. 最终产品边界

当前升级重构后的正式项目，严格聚焦四个法律主模块：

1. AI法务
2. 智能协作
3. 信息中心
4. 法律智库

当前版本明确不纳入：

1. 财税管理主模块
2. 财务分析专项工作台
3. 税务管理专项工作台
4. 非法律主线的跨域业务扩张

说明：

财税管理能力不删除历史实现，但不进入新项目主线目录，不进入当前版本导航，不作为当前阶段产品承诺。待试运行稳定和版本稳定后，再独立立项作为二期扩展。

## 4. 最终技术路线

### 4.1 后端定稿

正式采用：`Python + Rust`

职责划分：

1. Python 负责 AI法务、智能协作、信息中心、法律智库等业务域服务，以及文档解析、RAG、知识处理、行业智能逻辑。
2. Rust 负责 Unified Gateway、实时消息核心、会话控制、Skills Registry、MCP Broker、Policy / Approval / Audit / Notification、Scheduler 和 Secret Proxy。
3. 不再新增 Go 主线，不走 Go + Python + Rust 三线并行。
4. 如果未来因团队组织原因必须改用 Go，则只能采用 Go 替换 Rust 控制面，不保留三语言并行。

### 4.2 前端定稿

正式采用：`React Web + React Native / Expo`

职责划分：

1. Web 作为主工作台入口。
2. Mobile 围绕聊天、通知、审批、案件动态、知识查询优先建设。
3. Desktop 不作为第一阶段前提，后续按需通过 Tauri 封装。
4. 当前不重写为 Flutter。

## 5. 最终架构原则

1. 单一正式升级目录，不继续在旧目录堆叠新增主线代码。
2. 新项目只迁入经过筛选的有效代码和文档，不复制缓存、构建产物、依赖目录、历史试验目录。
3. 先统一控制面、聊天、Skills、MCP 和记忆，再推进业务域迁移。
4. 安全优先于功能扩张，凭证不下发到 Worker。
5. 历史项目保留作为参考和迁移源，不再作为正式升级开发入口。

## 6. 最终目标架构

```text
User / Web / Mobile / Matrix
  -> Unified Gateway (Rust)
    -> Identity / Tenant / Session
    -> Chat & Room Core
    -> Manager / Worker Orchestration
    -> Skills Registry & Runtime Control
    -> MCP Broker / Tool Gateway
    -> Memory Fabric
    -> Policy / Approval / Audit / Notify
    -> Domain Services (Python)
    -> Data & Storage
```

## 7. 新项目目录原则

升级重构后的正式项目必须在现有仓库根目录下新建独立目录实施。

正式定义如下：

1. 新项目目录名固定为 `ai-legal-agent-v2/`。
2. `ai-legal-agent-v2/` 是升级重构唯一正式开发入口。
3. 旧的 `frontend/`、`backend/`、`enterprise-super-assistant/`、`refactor-core/` 只作为迁移参考源，不再承接最终升级版主线新增功能。
4. 所有新模块、新服务、新脚手架、新协议文档，都必须优先进入 `ai-legal-agent-v2/`。

## 8. 迁移策略定稿

### 8.1 允许迁入新项目的内容

1. 已验证有效的业务模型和接口契约。
2. 聊天、协作、记忆、审批、审计、MCP、Skills 的可复用设计。
3. 成熟的前端交互模式、页面信息架构和设计规范。
4. 已有文档中的最终定稿内容。

### 8.2 禁止直接带入新项目的内容

1. `node_modules/`
2. `frontend/node_modules/`
3. `frontend/dist/`
4. `.pydeps/`
5. `.uv-cache/`
6. `.uv-data/`
7. `backend/.venv/`
8. `backend/.pytest_cache/`
9. `docs/reports/`
10. 各类历史周报、临时交付记录、冻结骨架、过期试验目录

### 8.3 历史目录定位

1. `frontend/`：旧主前端参考源
2. `backend/`：旧主后端参考源
3. `enterprise-super-assistant/`：Rust 控制面与控制台参考源
4. `refactor-core/`：冻结历史骨架，仅作历史参考
5. `docs/`：历史文档与定稿文档并存目录

## 9. 第一阶段正式实施范围

第一阶段只做以下内容：

1. 新项目目录初始化
2. 架构契约固化
3. Web 主入口骨架
4. Rust Gateway 骨架
5. Python Domain Service 骨架
6. 聊天房间模型
7. Skills Registry 模型
8. MCP Broker 模型
9. Memory Fabric 接口层
10. 开发规则和迁移规则落地

第一阶段明确不做：

1. 财税管理模块迁移
2. 旧目录全量复制
3. 旧功能无筛选平移
4. 为了追求完整而引入过多历史负担

## 10. 执行优先级

后续执行顺序固定为：

1. 新目录和规则先定
2. 契约先定
3. 控制面先立
4. 聊天 / Skills / MCP / 记忆先统一
5. 再逐步迁移法律业务域
6. 最后才考虑二期财税模块

## 11. 本定稿的执行要求

1. 后续新增方案不得与本定稿冲突。
2. 若出现旧文档与本定稿冲突，以本定稿为准。
3. 若需要调整模块边界或目录策略，必须先更新本定稿文档。
