# 功能完成度

## 总体评估

| 模块 | 完成度 | 可信度 | 说明 |
|---|---:|---|---|
| Web 主界面 | 80%-85% | 高 | 路由和页面覆盖完整，构建通过 |
| 后端主线 API | 70%-80% | 中高 | 测试覆盖较多，但外部渠道仍有占位 |
| 合同审查 | 75%-85% | 高 | 服务流和测试覆盖明确 |
| 文档工作台 | 70%-80% | 中高 | 对象存储、版本、适配器已具备，仍需验收大文件/协作 |
| 知识库 / RAG | 65%-75% | 中高 | 权限边界统一，检索质量仍需业务验收 |
| 支付 / 订阅 | 55%-70% | 中 | 微信/支付宝 provider 有实现，生产默认 mock 风险必须收口 |
| 电子签 | 35%-50% | 中低 | e签宝/法大大类在索引中仍显示占位，当前需源码和测试复核 |
| IM / 通知 | 60%-75% | 中 | WebSocket、离线 ACK 等已有测试，仍需实机长连验收 |
| 桌面同步 | 40%-60% | 中低 | 后端同步底座有推进，桌面本地同步路径仍需统一验证 |
| 移动端深功能 | 45%-60% | 中 | MVP 有真实 API，调查/智库搜索仍断点 |
| 小程序 | 40%-50% | 中 | 轻量入口已去除主路径“开发中”死胡同，核心事项由 AI 助手承接；仍缺真机验收和完整业务页 |

## 已较真实的链路

### 合同审查


1. `contracts.upload_and_review_contract`
2. `ContractService.create_contract`
3. `ContractService.review_contract`
4. `_normalize_review_result`
5. `_calculate_risk_score`
6. `_get_risk_level`
7. `_save_risks`

并且存在 `backend/tests/test_contract_review_workflow.py` 等测试覆盖。

### 知识库权限

`KnowledgeService._check_kb_access` 被多个流程复用：

- 上传文档到知识库
- 批量上传文档
- 添加文档
- 搜索知识
- RAG 查询
- 索引文档

这说明知识库权限不是页面级临时判断，而是进入了服务层。

### Web 权限与模式门控

Web 路由已使用：

- `ProtectedRoute`
- `AdminRoute`
- `ModeGate`
- `SubscriptionGate`

这对多角色、多客户端、本地/混合/云端模式是必要基础。

## 仍需谨慎的链路

### 支付

`get_payment_provider` 默认使用 `mock`，未知渠道还会回退到 `MockPaymentProvider`。这在开发环境方便，但生产环境应改为 fail-closed。

微信支付和支付宝 provider 有真实签名/验签实现，但还需要真实商户配置和沙箱/生产回调验收。

### 电子签


- `ESignBaoProvider` 是占位实现
- `FaDaDaProvider` 是占位实现
- 核心方法抛 `NotImplementedError`


### 多模态

OCR、ASR、PDF 解析在部分服务中仍有 TODO 或 mock 元数据。不要把“上传文件入口存在”理解为“多模态能力生产可用”。

### 移动端调查与智库

移动端：

- `investigation.tsx` 的开始调查仍是 TODO + `console.log`
- `knowledge.tsx` 的搜索仍是 TODO + `console.log`

这两块是明显断点。
