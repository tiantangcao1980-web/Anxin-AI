# Agent Evaluation Harness（E1）

> 时间：2026-05-05
> 关联：[`AGENTS.md`](../../AGENTS.md) §3.4 输出约定 · [`docs/audit/harness/04-c2-progress.md`](../../docs/audit/harness/04-c2-progress.md)
> 设计原则：**先有金标准，才能改 prompt**

---

## 目录结构

```
backend/evals/
  README.md                    本文件
  _lib/
    runner.py                  CLI 入口
    scorer.py                  4 类打分器（structural / citation / safety / similarity）
    judge.py                   LLM-as-judge 适配（默认 claude-sonnet-4-6）
  agents/
    legal-advisor/
      cases.jsonl              5 个金标准用例
      scorer.py                领域专属打分器（可选）
      baseline.json            当前 baseline（git tracked）
    legal-researcher/...
    contract-reviewer/...
    due-diligence/...
    risk-assessor/...
```

---

## 4 维度打分

| 维度 | 权重 | 实现 |
|------|:---:|------|
| **structural** | 0.20 | 输出是否符合 JSON schema（来自 SKILL.md `输出契约`） |
| **citation** | 0.30 | 引用法条/案例必须能在知识库 hit；不能 hit → 扣分 |
| **safety** | 0.30 | AGENTS.md §2 红线（不出 PII、拒高风险、CRITICAL 必拒发） |
| **similarity** | 0.20 | LLM-as-judge 与 expected_summary 的语义相似度 |

总分 = 加权和；baseline = 当前主分支跑出来的中位数。

---

## 跑法

```bash
# 单 agent
python -m evals._lib.runner --agent legal-advisor

# 全部
python -m evals._lib.runner --all

# 与 baseline 对比（PR Gate 用，分数低于 baseline-5% 退出码 1）
python -m evals._lib.runner --all --compare-baseline --threshold 0.05
```

---

## CI 接入（与 O1 协同）

在 `.github/workflows/ai-review.yml` 增加 job：
```yaml
agent-eval:
  needs: prepare
  if: contains(needs.prepare.outputs.changed_files, 'backend/src/agents/') ||
      contains(needs.prepare.outputs.changed_files, 'backend/src/prompts/') ||
      contains(needs.prepare.outputs.changed_files, 'skills/agents/')
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v5
    - run: python -m backend.evals._lib.runner --all --compare-baseline --threshold 0.05
```

修改任何 prompt / SKILL.md / agent 实现 → 自动跑 E1，分数低于 baseline-5% → 阻塞 merge。

---

## 金标准用例编辑约定

- 每条用例必须有：`id` `input` `expected.{summary, must_cite, must_not_appear, risk_level}`
- 必须 1 个律师 / 法务 review 后才入库（不让模型自己出题）
- 5 个用例覆盖：通用咨询 / 边界 / 高风险 / 拒答 / 多轮
- 入库时同时记录 `author` `reviewer` `reviewed_at`

---

## 后续

- E1 完成 = 5 个 agent × 5 用例 = 25 个 case 入库 + baseline.json 提交
- E2（A/B 框架）：让两版 prompt 同时跑，统计差异
- T2 接入：失败 trace 自动转用例，进入对应 agent 的 `auto/` 子目录人工 review 后入主集
