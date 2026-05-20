# 💰 财税顾问

> **税务合规 / 财务分析 / 法律计算** · 业务域：合规经营

## 这是什么

`finance-tax-advisor` 是 [安心智能助手](../../README.md) 的 Persona 插件之一，提供 *税务合规 / 财务分析 / 法律计算* 能力。本插件已在 V3 主干注册到 `backend/src/agents/personas/registry.py`，可在桌面端 / Web / 飞书 / 钉钉同步调用。

## 60 秒快速开始

```bash
# 1. 在 Claude Code 中安装本市场
/plugin marketplace add /Volumes/安心科技02/Pproject/Anxin-AI

# 2. 安装本插件
/plugin install finance-tax-advisor@anxin-ai

# 3. 第一次使用前，跑冷启动访谈（生成 CLAUDE.md 执业画像）
/finance-tax-advisor:cold-start-interview
```

冷启动访谈是**所有 skill 输出质量的前提**。它会请你提供：

- 行业 / 公司 / 团队规模
- 现有 SOP、模板、风险红线
- 常用对接系统（飞书 / 钉钉 / ERP / CRM）
- 法域 / 司法管辖偏好（默认中国大陆）

输出的 `CLAUDE.md` 会被每个 skill 自动读取。

## 可用 Slash 命令

| 命令 | 说明 |
|---|---|
| `/finance-tax-advisor:tax-compliance` | tax-compliance skill |
| `/finance-tax-advisor:invoice-verify` | invoice-verify skill |
| `/finance-tax-advisor:vat-cross-border` | vat-cross-border skill |
| `/finance-tax-advisor:ar-aging` | ar-aging skill |
| `/finance-tax-advisor:cold-start-interview` | 首次冷启动访谈，生成执业画像 |

## 后台 Skill 文件

```
finance-tax-advisor/
├── .claude-plugin/plugin.json
├── CLAUDE.md                ← 执业画像（由冷启动生成，不要直接编辑）
├── README.md                ← 本文档
├── skills/
│   └── cold-start-interview/SKILL.md
└── agents/                  ← 可选：scheduled / event-driven managed agent
```

业务能力主体复用 `skills/legal|finance|office/` 下的现成 skill；本插件只负责调度与冷启动。

## 风险守门（与 Anthropic Claude for Legal / Financial Services 同源）

1. **所有输出均为草稿**：法律意见、税务结论、投资建议须由有执业资质的专业人士复核签字。
2. **来源标注**：所有引用条款必须附《法规名称 第 X 条》或《文件名 第 X 页》。
3. **法域透明**：默认中国大陆，跨境时显式提示适用法域并要求人工确认。
4. **特权处理**：律师 / 客户特权通讯不写入共享知识库。
5. **不发不送**：任何外发动作（邮件、合同盖章、Amazon listing 上架）都需要人工 confirm。

## 进一步阅读

- [AI-ASSISTANT-PLAYBOOK.md](../../AI-ASSISTANT-PLAYBOOK.md) — 整体方法论
- [CONNECTORS.md](../../CONNECTORS.md) — 接入的 MCP 与第三方数据源
- [docs/v3/agent-personas.md](../../docs/v3/agent-personas.md) — 10 personas 完整说明
