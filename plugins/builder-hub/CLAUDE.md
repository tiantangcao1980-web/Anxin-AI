# Builder Hub · 信任层策略

> Builder Hub 不需要冷启动访谈 — 它是工具治理插件，行为由策略决定，不受执业风格影响。

## 1. Trust Level 矩阵

| Level | 允许动作 | 安装前检查 |
|---|---|---|
| `verified` | 自动安装 | scan + 签名校验 |
| `community` | 提示后安装 | scan + 必须用户 confirm |
| `untrusted` | 默认禁止 | 必须 `--trust-untrusted` 显式覆盖 |

## 2. 必扫规则（不可关闭）

- hidden-content/* — 三种隐藏文本注入
- prompt-injection/* — 三种 prompt override
- tool-scope/excessive-write — 声明只读但出现 write/edit/delete
- license/incompatible — 与 Apache-2.0 冲突的 GPL/AGPL/SSPL

## 3. 可调规则（默认开）

- freshness/stale-30d — 法规 / 政策类引用过期
- tool-scope/network-egress — 是否允许访问公网
- size/oversized — SKILL.md > 50 KB 提示拆分

## 4. 审计

所有动作写入 `.claude/builder-hub-audit.jsonl`。保留 365 天。

## 5. 升级矩阵

| 风险 | 自动处理 | 提示人工 | 强制升级 |
|---|---|---|---|
| 隐藏内容 | 拒绝安装 | / | / |
| 越权 write | 拒绝安装 | / | / |
| 公网外发 | / | 提示 | 大于 10 个域名时升级 |
| License 不兼容 | 拒绝安装 | / | / |
| 来源 untrusted | / | 提示 | 涉及客户数据时升级 |
