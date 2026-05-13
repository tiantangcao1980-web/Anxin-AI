# 中文注释规范

> **强制规范。** 本项目面向中国制造业中小企业，开发团队以中文为主要工作语言。代码注释默认使用**简体中文**，让任何中国工程师都能 5 秒理解代码意图。

## 1. 基本原则

| 原则 | 说明 |
|---|---|
| **代码可读优先于注释** | 命名清晰、结构合理时，多数代码不需要注释 |
| **注释解释 WHY，不解释 WHAT** | "为什么这样写"比"做了什么"更有价值（后者读代码就能知道） |
| **中文是首选语言** | 业务、流程、决策、警告全用中文 |
| **保留英文的场景** | 技术术语、第三方协议、错误代码、标识符 |

## 2. 中文注释强制场景

下列场景**必须**写中文注释：

| 场景 | 示例 |
|---|---|
| **业务规则解释** | `# 合同审查必须先经法律顾问 persona 处理，再走合同管家` |
| **算法 / 流程决策** | `# 采用 5 步迭代检索，幻觉率从 18% 降至 6%` |
| **隐藏约束 / 边界** | `# 此处必须保持顺序：先写日志，再更新状态（事务一致性要求）` |
| **特殊处理 workaround** | `# 阿里云 LiteLLM 镜像有版本限制，故锁定 1.x 见 #142` |
| **TODO / FIXME** | `# TODO(#235): 待财税 persona 上线后接入` |
| **安全 / 合规警示** | `# ⚠️ 此处对接微信支付 v3，签名错误会导致幂等表污染` |
| **性能注意点** | `# 此查询数据量大，必须走 selectinload，否则 N+1` |
| **隐私 / 脱敏要求** | `# 写日志前必须脱敏手机号和身份证（PII 红线）` |

## 3. 英文注释保留场景

| 场景 | 原因 |
|---|---|
| **公共 API docstring 的参数名 / 返回类型** | 通用接口契约，第三方可能消费 |
| **第三方协议必须的英文字段名** | 如 OAuth `state` / `client_id` / Webhook payload 字段 |
| **错误代码 + 简短英文标识** | 便于跨系统对接（错误编码体系本身用英文） |
| **`__all__` / `export` 列表** | 标识符本身就是英文 |
| **包含纯英文标识符的引用** | 引用代码符号时按原标识符 |

中英混排可以，比如：

```python
# 调用 LLM provider router（按 X-Privacy-Mode header 自动选择 endpoint）
response = await call_llm(messages=messages, mode=privacy_mode)
```

## 4. Python 注释

### 4.1 行内注释

```python
# ✅ 推荐
async def review_contract(contract_id: UUID, user: User) -> ReviewResult:
    # 审查前先经合同调查 agent 提取关键要素（要求：必须先 investigate 再 review）
    investigation = await contract_investigator.investigate(contract_id)

    # 走双循环审查：investigator 提取 → reviewer 逐条 → checker 验证置信度
    review = await contract_reviewer.review(investigation, user)
    return review

# ❌ 反例（无意义注释 / 解释 WHAT）
async def review_contract(contract_id: UUID, user: User) -> ReviewResult:
    # 调用 investigate 方法
    investigation = await contract_investigator.investigate(contract_id)
    # 调用 review 方法
    review = await contract_reviewer.review(investigation, user)
    # 返回结果
    return review
```

### 4.2 Docstring

公共 API 必须有 docstring，**简洁中文**为主：

```python
async def create_contract(
    req: ContractCreateRequest,
    user: User,
    session: AsyncSession,
) -> Contract:
    """创建合同并写入审计日志。

    业务规则：
    - 合同标题在同一组织内必须唯一
    - 创建后自动写 audit_log

    Args:
        req: 创建请求（已 Pydantic 校验）
        user: 当前用户（来自 require_auth）
        session: 数据库会话

    Returns:
        新建的 Contract 实体

    Raises:
        BizException(2002): 标题已存在
    """
    ...
```

### 4.3 模块级注释

```python
"""合同业务服务。

负责合同的 CRUD、版本管理、签署流程编排。

依赖：
- contract_investigator agent（要素提取）
- contract_reviewer agent（双循环审查）
- audit_service（审计日志）

参考：docs/audit/_tasks/task-05-contract.md
"""
```

## 5. TypeScript / React 注释

### 5.1 函数 / 组件

```tsx
// ✅ 推荐
/**
 * 智能体工作台主聊天画布。
 *
 * 业务流：
 * 1. 通过 WebSocket 接收流式 token
 * 2. 按 ThinkingChain 阶段（requirement / planning / execution）拆分展示
 * 3. 工具调用结果通过 A2UI 协议渲染为动态卡片
 *
 * 关键约束：
 * - WebSocket 首包必须发 token 鉴权
 * - 断线后自动指数退避重连（最长 30s）
 */
export function ChatCanvas({ conversationId }: ChatCanvasProps) {
  ...
}
```

### 5.2 隐藏约束

```tsx
// ⚠️ 此处必须用 ref 而非 state：每次 state 变更会触发 WebSocket 重连
const wsRef = useRef<WebSocket | null>(null);

// 设计令牌：bg-primary 而非硬编码颜色（见 docs/standards/frontend-standard.md §6）
<div className="bg-primary text-primary-foreground">
```

## 6. Rust 注释（桌面端）

```rust
//! 桌面端 SQLCipher 加密数据库管理。
//!
//! 主密钥通过 OS Keyring 存储（macOS Keychain / Windows Credential / Linux Secret Service）。
//! 首次启动会触发 Keyring 授权弹窗，后续复用进程内 SQLCIPHER_KEY_CACHE。

/// 打开加密数据库连接。
///
/// # 失败场景
/// - Keyring 不可用（系统未配置）
/// - SQLCipher 密钥不匹配（数据库已被其他密钥加密过）
pub async fn open_secure_db() -> Result<Connection> {
    // 加 cache 避免每次连接都触发 Keyring 弹窗（macOS 用户体验问题，见 ADR-003）
    if let Some(cached) = SQLCIPHER_KEY_CACHE.get() {
        return Connection::open_with_key(&db_path, cached);
    }
    ...
}
```

## 7. Shell / Bat 注释

```bash
#!/usr/bin/env bash
set -euo pipefail

# 商业发布前 48 小时倒排计划的代码级门禁
# 详见 docs/release/48-hour-commercial-delivery-plan.md
#
# 注意：
# - 此脚本仅做代码级 + 本地证据采集
# - 真实商户沙箱必须人工触发，不能在 CI 自动跑
```

## 8. SQL / Alembic 注释

```python
"""028_add_agent_tasks_table

V3 异步任务编排所需的 agent_tasks 主表。

字段说明：
- status: 状态机 (pending → running → succeeded/failed/cancelled)
- payload: 入参 JSON（不包含密钥）
- result: 输出 JSON（含引用、token 用量）
- error: 失败时的错误堆栈（已脱敏）

索引设计：
- (user_id, status, created_at desc) 支持任务中心列表查询
- (organization_id, persona) 支持组织级统计

参考：docs/v3/architecture.md §异步任务编排
"""
```

## 9. 注释禁忌

| ❌ 禁止 | ✅ 改为 |
|---|---|
| `# 这里是合同创建` | 删除（命名已说明） |
| `# i = 1` 简单赋值的注释 | 删除 |
| `# 修改：2026-04-15 by 张三` | 删除（git blame 已记录） |
| `# 临时代码先这样` 不带 issue | 加 `# TODO(#issue-num): ...` |
| `// 待重构` 没人懂的注释 | 写清楚问题与方向 |
| `# DO NOT MODIFY` 不解释原因 | 写明为什么不能改 + 如改要怎么做 |
| `# 这里应该是 X` 模棱两可 | 直接改成 X，或写明为什么没改 |
| AI 生成的废话注释（"这是一个 React 组件"） | 全部删除 |

## 10. 多人协作的注释风格

- **不写日记式注释**：`# 2026-05-13 改了一下`
- **不写情绪注释**：`# 这段代码很恶心`
- **不写自我对话**：`# 我觉得这里应该这样`
- **写事实与决策**：`# 走 IM gateway 是因为 P3 决策（见 ADR-004）`

## 11. 注释更新原则

- 修改代码必须同步修改注释，否则误导比无注释更糟
- 删除过时注释，不要"留着以防万一"
- 注释里的链接（issue / docs）失效后立即修复或删除
- 大段过时注释先评估是否还有价值，无价值直接删

## 12. PR 评审注释要点

Reviewer 在评审时关注：

- [ ] 业务规则有中文注释
- [ ] 隐藏约束 / workaround 有 WHY 注释
- [ ] TODO / FIXME 带 issue 链接
- [ ] 公共 API 有 docstring
- [ ] 没有 AI 生成的废话注释
- [ ] 没有过时注释
- [ ] 中文标点正确（"" 不用 ""，— 不用 ----）

## 13. 中文标点规范

| 推荐 | 替代 |
|---|---|
| `"中文引号"` | `"英文引号"` |
| `（中文括号）` | `(英文括号)`（**例外**：代码内仍用英文括号） |
| `：` | `:`（**例外**：代码内冒号仍英文） |
| `，` | `,`（**例外**：代码内逗号仍英文） |
| `——` 破折号 | `--` `——`（注释正文用） |
| `…` 省略号 | `...`（注释正文用） |

代码本身的标点（`def foo(x: int):`）保持英文。

## 14. 速查表

```python
# ✅ 好注释（解释 WHY + 业务规则 + 关键约束）
# ----------------------------------------
# 此处必须先 commit session 再发送事件，否则订阅方收到事件时数据库还没写入
await session.commit()
await event_bus.publish("contract.created", contract.id)

# ⚠️ TODO(#235): 待 P9 法律顾问 persona 上线后，把此处的硬编码 routing 改为 PersonaRegistry
intent = "contract_review"

# 民法典第 595 条规定，买卖合同的标的物必须明确（合规校验依据）
if not contract.subject:
    raise BizException(2001, "买卖合同必须有明确标的物")

# ❌ 坏注释（解释 WHAT / 废话 / 过时）
# ----------------------------------------
# 设置 contract.title 为 req.title
contract.title = req.title

# 这是一个保存函数
session.add(contract)

# 2026-04-15 张三：先这样吧
return contract
```

---

## 与其他规范的关系

- 注释整体风格遵循 [code-style.md](./code-style.md)
- 标识符命名遵循 [naming-convention.md](./naming-convention.md)
- 文档（README / 设计稿）规范见 [documentation-standard.md](./documentation-standard.md)

---

**记住**：好的代码 + 好的命名 + 关键中文注释 = 任何中国工程师 30 秒读懂。
