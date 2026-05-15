# 信任层级 Doctrine

> 每个 skill / cookbook / connector 都必须带一个 Trust Level。决定它在装载、调用、外发时的守门强度。
> 实现 `policy/trust-levels.yaml` + `plugins/builder-hub/skills/skill-installer`。

## 三级矩阵

| Level | 来源 | 安装行为 | 调用行为 | 撤回门槛 |
|---|---|---|---|---|
| `verified` | Anxin 官方 / Anthropic 官方 / 双签 PR 合并 | 自动安装 | 按 `access-matrix` | 安全应急委员会 |
| `community` | 通过 builder-hub 提交 + 1 reviewer | 提示后安装 | 默认要求 `REQUIRE_CONFIRM` | 任一 maintainer |
| `untrusted` | 任意第三方 | 拒绝；显式 `--trust-untrusted` 才能安装 | 永远 `REQUIRE_CONFIRM` + 不允许 connector 写动作 | 任一 user 自助 |

## 四步信任评估（builder-hub `skill-scan` 实现）

每次安装 / 升级前**串行**走：

1. **来源核验**
   - URL / 仓库 / npm 包名是否在 `policy/trust-levels.yaml § registries` 的 allowlist
   - 不在 → `untrusted`
2. **静态扫描**（`skill-scan` hard-fail 任一即拒）
   - hidden-content（零宽 / 字号 0 / 白底白字）
   - prompt-injection（ignore-previous / role-override / data-exfil）
   - tool-scope（声明只读但调用 write/edit/delete）
   - license（GPL / AGPL / SSPL 与 Apache-2.0 不兼容）
3. **签名核验**
   - verified 必须有 Anxin 官方 GPG 签名
   - community 必须有任一 builder GPG 签名
4. **历史口碑**
   - 检查 `revoked.json`：被撤回过的作者下次发布默认降一级
   - 检查 `.claude/builder-hub-audit.jsonl`：上一版调用失败率 > 5% → 降一级

## 升级 / 降级路径

```
untrusted ─(通过 4 步评估 + 1 reviewer 签字)──▶ community
community ─(连续 90 天 0 incident + 2 reviewer + 安全 lead 签字)──▶ verified
verified ─(任一 incident)──▶ community （热降级，24h 内决策）
任何级别 ─(安全事件)──▶ revoked （永久）
```

## 与 `access-matrix.yaml` 的关系

`access-matrix` 决定**谁能调用这个 skill**；`trust-levels` 决定**这个 skill 调用时是否要 confirm / 是否限制 tool**。

举例：
- `skill.contract.review` (verified) + `legal_member` → `ALLOW`
- `skill.competitor-screenshot` (community) + `legal_member` → `REQUIRE_CONFIRM`（即使在 access-matrix 中允许）
- `skill.malicious-test` (untrusted) + `legal_member` → `REQUIRE_CONFIRM` 且 connector 全禁

## 撤回（Revoke）

`revoked.json` 由 builder-hub 维护，含字段：

```json
{
  "skill_id": "/legal-advisor:bad-skill",
  "version": "1.2.3",
  "revoked_at": "2026-05-14T...Z",
  "reason": "存在 prompt-injection 漏洞 CVE-2026-XXXX",
  "revoked_by": "usr_security_lead",
  "successor_version": "1.2.4"
}
```

所有 Anxin 客户端在调用前查 revoked.json；命中 → 拒绝调用 + 推送升级提示。
