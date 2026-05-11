# skill_registry —— SKILL.md 运行时加载（P1 骨架）

## 用途
让 agent 像调用工具一样调用「技能包」。技能用 markdown 写 (`SKILL.md`)，无需改代码即可上下线。直接兼容 cowork 仓库中的 `anthropic-skills/` 目录格式。

## SKILL.md 格式规范

```markdown
---
name: contract-review
description: 合同审查与风险点识别
version: 1.0.0
type: legal
triggers:
  - 合同审查
  - 帮我看看这份合同
  - 风险审核
dependencies:
  - knowledge-base
requires_apps:
  - desktop
  - web
---

# 合同审查 SKILL

## 触发条件
当用户上传合同文件或在对话中提及"合同审查/审核"时启用。

## 工作流
1. 提取合同关键条款（违约金、保密、知识产权…）
2. 对照《民法典》合同编 / 行业范本检索差异点
3. 输出《风险点清单》（高/中/低）
...
```

### 字段约定

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 唯一标识，snake/kebab，与目录同名 |
| `description` | 是 | 一句话功能描述 |
| `version` | 否 | 语义化版本，默认 `0.0.0` |
| `type` | 否 | 领域：`legal` / `office` / `research` / `dev` / ... |
| `triggers` | 否 | 触发词数组，``find_by_trigger`` 召回用 |
| `dependencies` | 否 | 依赖的其它 skill name |
| `requires_apps` | 否 | 适配的客户端：`desktop` / `web` / `mobile` / `mp` / `im` |

正文（`body`）任意 markdown，会被注入到 agent 的 system prompt 中。

## 文件结构

| 文件 | 角色 |
|------|------|
| `models.py` | `Skill` dataclass（运行时对象） |
| `loader.py` | `SkillLoader`（单文件 / 目录加载，自带极简 YAML parser） |
| `registry.py` | `SkillRegistry` 单例（name / trigger / domain 路由） |

## 与 cowork anthropic-skills 兼容性

- **目录布局**一致：每个 skill 一个目录，目录内含 `SKILL.md`
- **frontmatter 字段**：本模块为必需字段保留 `name` / `description`，可选字段比 anthropic-skills 多 `triggers` / `requires_apps`（向下兼容）
- 直接 `loader.load_from_directory("/path/to/cowork/anthropic-skills")` 即可全量导入

## P5 实现路线

1. **YAML 升级**：替换骨架的 `_parse_simple_yaml` 为 `yaml.safe_load`（已在依赖中）
2. **热更新**：`watchdog` 监听 SKILL.md 目录变更，自动 reload + 通知 agent runtime
3. **召回升级**：`find_by_trigger` 接 BGE-M3 embedding，候选 → LLM 重排
4. **冲突检测**：注册完成后扫描 trigger 重叠并 WARN
5. **agent runtime 集成**：在 `services/chat_service.py` / `services/ai_assistant_service.py` 的 system prompt 组装阶段注入命中 skill 的 body
6. **权限 / 计费**：与 `models/billing.py` 联动，`requires_apps` + 用户订阅级别决定是否可用

## P6+ 扩展
- skill 远程仓库 + 一键安装（类似 npm registry）
- skill 执行沙箱（Codex Cloud + python skill）
- 用户自定义 skill 编辑器（IM / 法务知识沉淀场景）
