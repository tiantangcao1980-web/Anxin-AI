# 任务 0 产出物 4 — CI 安全扫描接入方案

> 目的：在密钥治理（02-secret-rotation-sop.md）完成后，建立"防再发"的 CI 闸门
> 工具：gitleaks（密钥扫描）+ trivy（容器/依赖扫描）+ pip-audit（Python 依赖）+ npm audit（Node 依赖）+ ruff（Python lint，已有）+ pre-commit（本地闸门）
> 预期成本：CI 增加 ~3 分钟；GitHub Actions 免费额度 2000 分钟/月，足够

---

## 1. 现状盘点

### 1.1 当前 CI

```bash
ls .github/workflows/
```

预计存在但未在本审计核查范围。**用户必须在执行本方案前检查**：
- [ ] 当前有几个 workflow 文件
- [ ] 是否已经跑了 lint/test/build
- [ ] 是否已经接 codecov 或类似覆盖率
- [ ] CI 触发条件（push / pull_request / schedule）

### 1.2 当前已有的安全相关代码

- `backend/.gitleaksignore`（如有）—— 待核
- `pre-commit-config.yaml`（如有）—— 待核
- `requirements.txt` / `pyproject.toml` 是否有依赖锁定

---

## 2. 四件套接入

### 2.1 gitleaks（密钥扫描）

**目的**：拦截 commit 中的 secret 模式（API key、token、证书等 100+ 种）

**本地接入**（每次 commit 都跑）：

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

```bash
brew install pre-commit gitleaks
pre-commit install
# 一次性扫历史
gitleaks detect --source . --report-path gitleaks-history.json
```

**CI 接入**：

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  push:
    branches: [main, gongnengkaifa]
  pull_request:
    branches: [main]

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # gitleaks 需要全历史
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}  # 企业版可选
```

**配置文件**（白名单 + 自定义规则）：

```toml
# .gitleaks.toml
[allowlist]
description = "全局白名单"
paths = [
    '''docs/audit/.*\.md''',  # 审计文档可能列举密钥名（非密钥值）
    '''.*\.example$''',        # 示例文件
    '''.*\.template$''',
]

# 自定义规则（默认 100+ 规则之外）
[[rules]]
id = "anxin-internal-token"
description = "项目内部 token 模式"
regex = '''ANX_TOKEN_[A-Za-z0-9]{32,}'''
tags = ["token"]
```

**预期阻断点**：
- 任何 push/pr 中含 sk-... / ghp_... / API_KEY=... 等模式 → CI 失败
- 拦截后开发者必须重写 commit 历史，不能简单"再 push 一次"

---

### 2.2 trivy（容器 + 依赖扫描）

**目的**：扫 Dockerfile / docker-compose 中的镜像漏洞，扫源码中的依赖漏洞

**CI 接入**：

```yaml
# 续 .github/workflows/security-scan.yml
  trivy-fs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Trivy 文件系统扫描
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          format: 'sarif'
          output: 'trivy-fs.sarif'
      - name: 上传 SARIF 到 GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-fs.sarif'

  trivy-image:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: 构建 backend 镜像
        run: docker build -t anxin-backend:scan -f backend/Dockerfile backend/
      - name: Trivy 镜像扫描
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'anxin-backend:scan'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'  # CRITICAL/HIGH 直接 fail CI
          ignore-unfixed: true
```

**白名单**：

```yaml
# .trivyignore
# 已知不修复的低风险（必须每条注释原因）
CVE-2024-XXXX  # lottie-web eval 已知，无生产影响（前端 build 警告）
```

---

### 2.3 pip-audit（Python 依赖）

**目的**：扫 `pyproject.toml` / `requirements.txt` 中的已知漏洞

**CI 接入**：

```yaml
  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: 安装 pip-audit
        run: pip install pip-audit
      - name: 扫描 backend 依赖
        run: pip-audit -r backend/requirements.txt --strict
        # --strict：任何已知 CVE 都失败
```

**本地命令**：

```bash
cd backend
pip install pip-audit
pip-audit
```

---

### 2.4 npm audit（Node 依赖）

**目的**：扫 `package-lock.json` 中的已知漏洞

**CI 接入**：

```yaml
  npm-audit-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: 'frontend/package-lock.json'
      - run: cd frontend && npm ci
      - run: cd frontend && npm audit --audit-level=high
        # 仅 high+critical 失败 CI；moderate 仅警告

  npm-audit-mini:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '18' }
      - run: cd mini-program && npm ci && npm audit --audit-level=high

  npm-audit-mobile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '18' }
      - run: cd mobile && npm ci && npm audit --audit-level=high
```

---

## 3. GitHub 平台原生功能（必开）

### 3.1 Secret Scanning + Push Protection

```
GitHub 仓库 → Settings → Code security and analysis
☑ Secret scanning
☑ Push protection（拦截 push 时含 secret 的 commit）
☑ Dependabot alerts
☑ Dependabot security updates
☑ Code scanning（CodeQL）
```

**作用**：
- Secret Scanning：自动扫所有 commit，发现已知 secret 模式立即告警
- Push Protection：从源头阻止再发，开发者 push 时被拦截，无法绕过
- Dependabot：自动 PR 升级有漏洞的依赖
- CodeQL：扫代码逻辑漏洞（SQL 注入、XSS、command injection 等）

**用户操作**：上述 5 个开关在仓库 Settings 里点开即可。免费且零代码改动。

---

### 3.2 分支保护规则

```
GitHub 仓库 → Settings → Branches → Add rule
- Branch name pattern: main
- ☑ Require a pull request before merging
- ☑ Require status checks to pass before merging
    - 必选：security-scan / gitleaks
    - 必选：security-scan / trivy-fs
    - 必选：security-scan / pip-audit
    - 必选：security-scan / npm-audit-frontend
    - 必选：CI / backend-tests
    - 必选：CI / frontend-build
- ☑ Require branches to be up to date before merging
- ☑ Do not allow bypassing the above settings
```

---

## 4. ruff / mypy 零基线管理

**历史问题**：早期快照曾有 ruff 7873 errors / mypy 2002 errors；当前全仓 Ruff 与 backend mypy 已清零，发布路线不再接受“只是不恶化”的非零基线。

**方案：零回退策略**

```yaml
# .github/workflows/lint-baseline.yml
name: Static Quality Zero Baseline

on: [pull_request]

jobs:
  ruff-no-regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ruff
      - name: 比较错误数（PR vs main）
        run: |
          # 1. 当前 PR 错误数
          PR_ERRORS=$(ruff check backend/src backend/tests --statistics 2>&1 | tail -1 | awk '{print $1}')
          # 2. main 错误数
          git fetch origin main
          git checkout origin/main -- .
          MAIN_ERRORS=$(ruff check backend/src backend/tests --statistics 2>&1 | tail -1 | awk '{print $1}')
          git checkout HEAD -- .
          # 3. PR 不允许新增错误
          if [ "$PR_ERRORS" -gt "$MAIN_ERRORS" ]; then
            echo "::error::Ruff errors increased: $MAIN_ERRORS → $PR_ERRORS"
            exit 1
          fi
          echo "Ruff errors: $PR_ERRORS (baseline: $MAIN_ERRORS)"
```

**配套工作**：每周例会跑一次 `ruff check --fix --unsafe-fixes`，按目录修，把基线降低。一年时间内分批降到 0。

---

## 5. 完整 workflow 模板

把以上所有 job 整合到一个文件：

```yaml
# .github/workflows/security-scan.yml （完整版）
name: Security Scan

on:
  push:
    branches: [main, gongnengkaifa]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # 每周一凌晨 2 点全量扫一遍

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  trivy-fs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install pip-audit && pip-audit -r backend/requirements.txt

  npm-audit:
    strategy:
      matrix:
        dir: [frontend, mini-program, mobile]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '18' }
      - run: cd ${{ matrix.dir }} && npm ci && npm audit --audit-level=high
```

---

## 6. 渐进式接入路线（避免一次性瘫痪）

| 阶段 | 时间 | 接入项 | CI 失败策略 |
|---|---|---|---|
| Day 0 | 任务 0 | gitleaks（CI + pre-commit） | 失败即阻塞合并 |
| Day 0 | 任务 0 | GitHub Secret Scanning + Push Protection | 自动拦截，开发者侧失败 |
| Day 2 | 波次 1 | pip-audit / npm audit（warning-only） | 仅警告，不阻塞 |
| Day 5 | 波次 2 | trivy-fs（仅 CRITICAL 阻塞） | CRITICAL 阻塞，HIGH 警告 |
| Day 10 | 波次 3 | trivy-image（仅 CRITICAL 阻塞） | 同上 |
| Day 15 | 波次 4 | ruff-no-regression（基线策略） | 错误数增加即阻塞 |
| Day 20 | 收尾 | mypy-no-regression（基线策略） | 同上 |
| Day 30+ | 持续 | 把 npm/pip-audit 升级为 high+critical 都阻塞 | — |

---

## 7. 用户必须答复 Claude 的事项

- [ ] GitHub 仓库当前是否已开启 Secret Scanning？
- [ ] 是否已有现成的 .github/workflows/ 文件，是否需要 Claude 列清单？
- [ ] 是否同意 Day 0 接入 gitleaks（最严格，会立即阻塞含 secret 的 PR）？
- [ ] 是否有依赖第三方扫描器（GitGuardian / Snyk / Sonarqube）的现成账号可以联动？
- [ ] 是否同意"渐进式接入路线"的时间表？

---

> 文档作者：Claude Code
> 状态：待用户答复 §7 后激活
