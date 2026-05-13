# PR 审查清单

> Reviewer 在 approve 前对照此清单逐项核查。PR 作者自查后也按此对照。

## 1. 命名 & 结构

- [ ] 文件名符合 [naming-convention.md](./naming-convention.md)
- [ ] 没有中文文件名/目录名
- [ ] 没有 SCREAMING_CASE 出现在 docs/ 内部
- [ ] 没有日期前缀文件（除非 archive / ADR）
- [ ] 文件在正确的目录层级（按 [documentation-standard.md §1](./documentation-standard.md#1-文档分层)）

## 2. 代码质量

- [ ] 通过 `ruff check` / `eslint` / `cargo clippy`
- [ ] 通过 `mypy` / `tsc --noEmit` / `cargo check`
- [ ] 通过对应单元测试
- [ ] 关键路径有集成测试 / E2E
- [ ] 无 `console.log` / `print` 残留
- [ ] 无未处理的 `TODO` / `FIXME`（或必须带 issue 链接）

## 3. 安全

- [ ] 无密钥 / token / API key 入库
- [ ] 用户输入有后端校验
- [ ] SQL 走 ORM，无字符串拼接
- [ ] 新增第三方依赖已评估（CVE 扫描）
- [ ] 涉及 LLM 提示词的改动，提示词注入防护到位

## 4. 性能

- [ ] 无 N+1 查询
- [ ] 长任务（> 10s）走异步
- [ ] 大列表分页
- [ ] 前端新增 chunk 不超 500 KB

## 5. 文档

- [ ] 新功能有 README 或 docs/ 说明
- [ ] API 变更同步更新 OpenAPI / 类型定义
- [ ] 涉及架构调整有 ADR
- [ ] 涉及破坏性变更，CHANGELOG.md 已加条目
- [ ] 涉及流程变更，对应 standards 文档已更新

## 6. Git

- [ ] PR 标题符合 [commit-convention.md](./commit-convention.md)
- [ ] commit 历史干净（必要时 squash）
- [ ] 不包含无关文件改动
- [ ] 不包含 `.env`、`node_modules`、构建产物

## 7. 用户体验

- [ ] UI 改动有截图 / 录屏
- [ ] 错误状态、加载状态、空状态都有处理
- [ ] 移动端 + 暗色模式（如适用）已验证
- [ ] 国际化 / a11y（如适用）

## 8. 部署 / 运维

- [ ] 新增 env 变量在 `.env.example` 已列出
- [ ] Docker 镜像构建通过
- [ ] 数据库迁移可逆
- [ ] 涉及外部服务的改动，第三方账号 / 凭据需求已在 [docs/release/external-resource-handoff.md](../release/external-resource-handoff.md) 标记

## 9. V3 智能助手对齐（如涉及）

- [ ] 是否在 [docs/v3/](../v3/) 的范围内？如否，说明扩展理由
- [ ] 是否影响 10 personas 的能力矩阵？
- [ ] 是否涉及 [openspec/00-intelligent-assistant-platform-spec.md](../openspec/00-intelligent-assistant-platform-spec.md) 中的边界（隐私 / 治理 / 桌面远控等）？

## 10. 跨端一致性（如涉及多端）

- [ ] 桌面 + 移动 + 小程序 + Web 端 API 调用一致
- [ ] 设计 token 复用，无硬编码颜色
- [ ] 同样的业务逻辑在不同端表现一致

---

## Reviewer 速记

每条不通过都要：
1. **明确指出**哪条规范被违反
2. **指向**对应 standards 文档章节
3. **给改进建议**或要求

PR 反馈语气专业、对事不对人。
