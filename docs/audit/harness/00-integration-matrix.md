# Harness 8 模块接入体检矩阵（H0）

> 时间：2026-05-05
> 范围：`backend/src/harness/` 全部 8 个模块
> 方法：grep 真实 import + 阅读主路径调用上下文，判断激活强度
> 结论：8 个模块中只有 **3 个真接入主路径**、**2 个软接入**、**3 个未接入业务**

---

## 一、总览（三色矩阵）

| 模块 | 状态 | 主接入点 | 真激活路径 | 缺口 | 修复优先级 |
|------|:---:|---------|-----------|------|:---:|
| `trace_context` | 🟢 真接入 | `chat_service.py:865/970` | 每次 chat 调用都 start/end trace | trace 只在内存，无落盘、无聚类、无跨设备 | P1（T1） |
| `task_engine` | 🟢 真接入 | `chat_service.py:876/884/937/962` | chat 主路径有完整状态机 | 仅 chat 用，agent / contract / DD 等长任务未接入 | P1（H1） |
| `cost_tracker` | 🟢 真接入 | `agents/base.py:517` | 每次 LLM 调用后异步记 | 无配额阻断；本地 LLM/流式无 usage 时静默丢失；无单用户成本告警 | P2（H1） |
| `output_validator` | 🟡 软接入 | `chat_service.py:943` | 调用了但**失败不阻断** | `try/except` 吞异常；未通过校验时仅 `log.warning`；回答照样发出 | **P0**（H1） |
| `context_engine` | 🟢 真接入 | `chat_service.py:696` / `due_diligence.py:987,1007` | 三处压缩调用统一改走 `harness.context_engine` | T3 (2026-05-14) 完成单一入口收口, 内部仍委托 `services.context_compressor`; 一个 release 后可删旧版 | ✅ 已完成 (T3) |
| `policy_engine` | 🟢 真接入 | `agents/base.py:_check_mcp_tool_policy / _filter_mcp_tools_for_policy / _execute_tool` 走 `harness.policy_enforcement.check_tool_call(enforce=True)` | 每次 MCP tool_call 前后均判权 | T2 (2026-05-14) 完成第二阶段切 enforce, 默认硬阻断; env `HARNESS_POLICY_ENFORCE=false` 留紧急降级 | ✅ 已完成 (T2) |
| `tool_registry` | 🔴 未接入业务 | 仅 `api/routes/harness.py` | admin 端只读 | 工具定义仍散落在各 agent prompt；无调用统计、无风险分级强制 | P1（H1） |
| `capability_negotiator` | 🔴 未接入业务 | 仅 `api/routes/harness.py` | admin 端只读 | 桌面端模式切换未走能力协商；ModeGate 与 negotiator 是两套逻辑 | P2（H1） |

---

## 二、关键证据（按状态分组）

### 🟢 真接入（3 个）

**trace_context** — `backend/src/services/chat_service.py:865, 932, 936, 970`
```python
trace = start_trace(user_id=user_id, conversation_id=conversation_id)
# ...
trace.end_span(span_id, status="success" | "error")
trace_summary = end_trace()
result_dict["_harness"] = {"trace_id": ..., "total_tokens": ..., ...}
```
✅ 真激活，但产物仅返回给前端 + 内存，**无持久化** → T1 处理。

**task_engine** — `chat_service.py:876, 884, 937, 962`
```python
task_record = task_engine.create_task(...)
task_engine.transition(task_record.task_id, TaskState.RUNNING)
# ... 失败：transition(..., FAILED)
# ... 成功：transition(..., COMPLETED)
```
✅ 状态机用得标准，但**只覆盖 chat**。合同审查/尽调/批量文档生成等长任务未接入。

**cost_tracker** — `backend/src/agents/base.py:513-527`
```python
try:
    usage = data.get("usage")
    if usage:
        from src.harness.cost_tracker import cost_tracker
        cost_tracker.record(model=..., provider=..., prompt_tokens=..., completion_tokens=..., agent_name=self.name, ...)
except Exception as _cost_err:
    logger.debug(f"成本追踪跳过: {_cost_err}")
```
✅ 异步、不阻塞主路径（好），但：
- 本地 LLM API 不返回 `usage` → **静默丢失**（H1 需补估算）
- 没有"超额阻断"门控
- 没有按用户/会话维度配额

### 🟡 软接入（1 个）

**output_validator** — `backend/src/services/chat_service.py:941-958`
```python
try:
    validation = await output_validator.validate(...)
    if not validation.passed:
        logger.warning(f"[Harness] 输出校验未通过 | score={validation.score:.2f} | issues=[...]")
        if validation.has_critical:
            response_text += "\n\n⚠️ 本回答内容仅供参考..."   # ← 仅追加免责声明
except Exception as val_err:
    logger.debug(f"[Harness] 输出校验跳过: {val_err}")          # ← 异常完全吞掉
```
🚨 **本轮最大问题**：
1. `try/except` 把所有 validator 异常吞成 debug 日志 → 校验链路如果挂了，主流程感知不到
2. `not validation.passed` 时**只在 has_critical 才动作**，且动作只是"加免责声明"
3. 普通失败（结构错误、引用编号不存在、相关性偏题）**回答原样发出**
4. 与 roadmap 中"验证不通过 → 自动触发 Agent 修正（最多1次重试）"承诺不符

### 🔴 未接入业务（4 个）

**context_engine** — `backend/src/harness/__init__.py:19` 导出，无业务 import
- `chat_service.py:672-678` 直接走 `services/context_compressor`，**绕过 context_engine**
- 形成两套并行实现：
  - 旧：`services/context_compressor.py` — 真在用
  - 新：`harness/context_engine.py` — 包了一层 + 加了 memory_layer/experience_engine 整合，但没人用
- 决策：**保留一个**——要么把 chat_service 切到 context_engine，要么删 context_engine

**policy_engine** — 只在 `api/routes/harness.py` 出现 5 次（全是 admin 读取）
- 主路径 0 调用 → **任何 agent 调用任何工具都不过权限检查**
- 与"高风险操作（如生成正式法律意见 → 需律师审批）"完全脱节
- 与现有 `approvals` 模块也没接通

**tool_registry** — 只在 admin 出现
- 22 个 agent 的工具定义仍写在各自 prompt 里
- 没有 input/output schema 强校验
- 没有调用成功率/延迟统计入库

**capability_negotiator** — 只在 admin 出现
- 桌面端 `desktop/src/services/` 走自己的逻辑
- 前端 `ModeGate` 走自己的策略表
- 三套并行的"能力可用性判断"，互不知晓

---

## 三、与 roadmap 承诺的差异

[`memory/harness_engineering_roadmap.md`](../../../../../../.claude/projects/-Users-pengchengkeji-Documents-GitHub-Anxin-Smart-Legal-Services/memory/harness_engineering_roadmap.md) 阶段 1-3 标记为"已完成"，本次体检发现：

| roadmap 承诺 | 实际状态 |
|-------------|---------|
| 1.3 输出验证 Gate（验证不通过 → 自动触发 Agent 修正，最多 1 次重试） | ❌ 未做重试，且失败不阻断 |
| 1.4 trace_context + audit 记录 AI 事件 | ⚠️ trace 在内存，未对接 audit_service 持久化 |
| 2.2 工具注册中心替代散落在各 Agent prompt 中的工具定义 | ❌ Agent prompt 里仍是手写工具说明 |
| 2.3 policy_engine 高风险操作门控（与 approval 模块对接） | ❌ 主路径未调用，未与 approvals 对接 |
| 3.2 桌面端模式切换走 capability_negotiator | ❌ 桌面端走自己的逻辑 |

**结论**：roadmap 阶段 1-3 是"模块已建"而非"主路径已激活"，本轮 H1 必须补齐。

---

## 四、H1 修复优先级（输入给下一任务）

| 顺序 | 模块 | 动作 | 阻塞 |
|:---:|------|------|:---:|
| 1 | `output_validator` | 移除吞异常的 `try/except`；失败 → 阻断或单次重试；CRITICAL 必拒发 | 否 |
| 2 | `policy_engine` | 在 `agents/base.py` LLM tool 调用前后加门控；接 `approvals` | 否 |
| 3 | `context_engine` vs `context_compressor` | 二选一，保留 + 删另一个，修迁移测试 | 否 |
| 4 | `task_engine` | 扩展到 contract/DD/批量文档主路径 | 否 |
| 5 | `cost_tracker` | 本地 LLM 估算 + 用户/会话配额阻断 | 否 |
| 6 | `tool_registry` | 改造 agent 工具定义为注册式；从 prompt 抽离 | 与 C2 协同 |
| 7 | `capability_negotiator` | 统一桌面/前端/服务的能力可用性判断 | 与 C1 协同 |

---

## 五、本任务护栏遵守情况

- ✅ **零代码修改** — 全程只读
- ✅ 输出文件位置正确：`docs/audit/harness/00-integration-matrix.md`
- ✅ 修复优先级表已产出，可作为 H1 输入
- ✅ 没有"顺手修一下"

下一步：进入 **C1 / T1 / O1** 并行（W1 剩余三个），最后执行 **H1**。
