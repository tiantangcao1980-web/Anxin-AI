# 任务 0 产出物 2 — 密钥治理 SOP（命令草稿，待用户执行）

> 类型：标准操作流程（SOP），不替用户执行
> 严重度：🔴 P0 阻塞 — 在完成本 SOP 前，所有其他任务的代码改动都不应推送到远端
> 假设：用户拥有所有相关账号 / 凭据 / 仓库的写权限
> 工具要求：`git`、`git filter-repo`（推荐，比 BFG 更安全）或 `bfg`（备选）、各第三方平台控制台访问权限

---

## 0. 立即停止的事

在用户开始执行本 SOP 之前：

- [ ] **不要**继续向 `origin/gongnengkaifa` 或其他分支 push 任何带 `.env` 或类似配置的提交
- [ ] **不要**在公开渠道（issue / PR / 截图 / 文档）提及具体的 secret 内容
- [ ] **不要**尝试 `git push --force` 修复（在影响面评估之前）
- [ ] **不要**以任何方式在对话中分享 `.env` 实际内容给 Claude（Claude 不需要看，且对话日志可能被持久化）

---

## 1. 已核实的边界（不读 .env 内容，只列文件名 + commit）

### 1.1 远端情况

| 远端 | URL | 状态 |
|---|---|---|
| `origin` | https://github.com/tiantangcao1980-web/Anxin-Smart-Legal-Services.git | 主仓库，包含泄露 commit |
| `v3` | https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant.git | 副仓库，需独立核查 |

**用户必须先确认（Day 0 上午）**：
- [ ] 这两个 GitHub 仓库当前是 **public 还是 private**？
- [ ] 若是 public，自 commit `ed8ea03`（2026-03-28 21:54）以来已经过了多少天 / 有没有任何 fork / star
- [ ] 是否有 GitHub Actions / 其他 CI / 第三方扫描器（如 GitGuardian、TruffleHog）已经触发并发邮件告警

> 上述信息决定了本 SOP 的紧急程度：public 仓 + 长时间 = 必须**当天**轮换全部凭据；private 仓 + 短时间 = 当周内即可。

### 1.2 历史中曾被提交的 .env 类文件名（不读内容）

```
.env
.env.example
.env.nas.example
.env.template
backend/.env
backend/.env.example
backend/.env.local
deploy/headlessx/.env.example
frontend/.env
frontend/.env.tauri
```

> `.env.example` / `.env.template` / `.env.nas.example` 是模板文件，按惯例不含真实密钥，但**用户必须打开核验**。
> 真正高危的是 `.env`、`backend/.env`、`backend/.env.local`、`frontend/.env`、`frontend/.env.tauri` 这 5 份。

### 1.3 当前工作树状态

| 项 | 状态 |
|---|---|
| 当前 `.env` 是否被 git 跟踪 | ❌（已从索引移除）|
| `.gitignore` 是否包含 `.env` | ✅ 已包含 `.env` / `.env.local` / `.env.*.local` |
| 主分支是否还有泄露 commit | ✅ 仍在历史（`git log --all --follow -- .env` 命中 1 个 commit `ed8ea03`）|

**结论**：当前工作树看起来干净，但 Git 历史里"按下不放"了一份完整 `.env`。任何能 `git clone` 或访问历史的人都能拿到。

---

## 2. 五步原子化处置流程（用户执行，Claude 仅产出命令草稿）

### Step 1 — 现状盘点（Day 0 上午，30 分钟）

**目的**：在动任何东西前，列全可能泄露的凭据 + 涉及的第三方 + 影响系统。

**用户操作**：
1. 在**安全离线环境**（不要在协作工具里）打开任意一个本地 `.env`
2. 把所有 KEY=VALUE 中的 KEY 复制出来（不要复制 VALUE）
3. 按下表分类填写到 `docs/audit/00-platform/_secret-inventory.private.md`（**该文件加入 .gitignore**）

```markdown
# 凭据现状盘点（私密文件，不入库）

## 第三方 API 凭据
| KEY 名 | 第三方平台 | 是否已 push 到 GitHub | 是否能动账户/扣款 | 轮换难度 |
|---|---|---|---|---|
| OPENAI_API_KEY | OpenAI | 是 | 能扣费 | 中 |
| ANTHROPIC_API_KEY | Anthropic | 是 | 能扣费 | 中 |
| WECHAT_PAY_API_KEY | 微信支付 | 是 | 能动账户 | 高（商户号变更）|
| ALIPAY_PRIVATE_KEY | 支付宝 | 是 | 能动账户 | 高 |
| ESIGN_BAO_APP_SECRET | e签宝 | 是 | 能签发法律效力文件 | 高 |
| FADADA_APP_SECRET | 法大大 | 是 | 同上 | 高 |
| TURNSTILE_SECRET_KEY | Cloudflare | 是 | 防护降级 | 低 |
| ... | ... | ... | ... | ... |

## 数据库 / 中间件 凭据
| KEY 名 | 用途 | 是否能进生产 DB |
|---|---|---|
| DATABASE_URL | PostgreSQL 主库 | 是 |
| REDIS_URL | Redis | 是 |
| QDRANT_API_KEY | Qdrant | 是 |
| NEO4J_PASSWORD | Neo4j | 是 |
| MINIO_SECRET_KEY | MinIO 对象存储 | 是 |
| ... | ... | ... |

## 内部服务凭据
| KEY 名 | 用途 |
|---|---|
| JWT_SECRET_KEY | 签发 access/refresh token |
| WEBHOOK_SECRET_PAYMENT | 支付 webhook HMAC |
| WEBHOOK_SECRET_ESIGN | 电签 webhook HMAC |
| ENCRYPTION_KEY | DB 字段加密 |
| ... | ... |
```

**完成判定**：清单覆盖项目所有 `.env*` 文件中的所有 KEY。

---

### Step 2 — 影响面与紧急度定级（Day 0 上午，30 分钟）

按 Step 1 清单，给每条凭据打**紧急级**：

| 等级 | 判定 | 处置时限 |
|---|---|---|
| 🔴 立即（< 1h） | 能扣款 / 能签法律文件 / 能动生产数据库 / 仓库是 public | 当下立即 |
| 🟠 当天（< 8h） | 能用于敏感读取（生产数据查询）/ 能伪造身份 | 当天 |
| 🟡 当周（< 7d） | 仅影响开发环境 / 已经 expired / 公开模板文件 | 当周 |

**用户决策点**：
- [ ] 在 Step 1 清单上为每条凭据标记等级
- [ ] 把 🔴 项的轮换排到 Step 4 的最前面

---

### Step 3 — 准备替代凭据（Day 0 中午，2 小时）

**关键原则**：**先生成新凭据，验证新凭据可用，再失效旧凭据**。绝不允许"先废再生"——废后业务会立即崩。

每条 🔴 凭据按以下顺序：

```
1. 在第三方控制台生成新凭据（保留旧凭据并存）
2. 在本地新 .env 中替换为新值（仅本地，不入库）
3. 用 docker-compose.dev.yml 启起来，跑核心冒烟（登录/付费/电签 mock）
4. 确认新凭据可用 → 进入 Step 4 失效旧凭据
5. 若新凭据有问题，回退到旧凭据继续用，重新生成
```

**用户必须自行操作的第三方平台**：
- [ ] OpenAI Console → API Keys
- [ ] Anthropic Console → API Keys
- [ ] 微信支付商户平台（涉及商户号变更，需走流程）
- [ ] 支付宝开放平台
- [ ] e签宝 / 法大大 沙箱与生产
- [ ] Cloudflare Turnstile
- [ ] AWS / 阿里云 / 腾讯云（如有）
- [ ] PostgreSQL / Redis / Neo4j / Qdrant / MinIO 数据库密码

> Claude 不能（也不应该）代用户访问这些控制台。

---

### Step 4 — 同步执行：旧凭据失效 + 历史清理（Day 0 下午到 Day 1 上午，4 小时）

**这一步必须把"旧凭据失效"和"Git 历史清理"绑成一个原子操作**。如果只清历史不失效旧凭据，那段时间任何 fork 仍然有效；如果只失效旧凭据但历史还在，下次有人 clone 还是能尝试新一轮（虽然旧 key 已失效，但暴露行为本身可能违反平台 ToS）。

#### 4.1 旧凭据失效（每条 🔴 项）

按 Step 1 清单，在每个第三方控制台**逐项点击 "Revoke" / "Delete" / "Disable"**。

#### 4.2 Git 历史清理 — 命令草稿

> ⚠️ **以下命令是草稿，未经用户确认不要执行**。每条命令都会改写历史，是不可逆的破坏性操作。

**前置准备**：
```bash
# 1. 全部协作者先 push 自己的本地 commit 到远端（避免清理后丢工作）
# （这一步由用户协调团队完成，Claude 无法替执行）

# 2. 备份当前主仓库
cd ~/Documents/GitHub
git clone --mirror https://github.com/tiantangcao1980-web/Anxin-Smart-Legal-Services.git \
    Anxin-Smart-Legal-Services.bak.$(date +%Y%m%d).git

# 3. 备份副仓库
git clone --mirror https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant.git \
    Anxin-Smart-Assistant.bak.$(date +%Y%m%d).git
```

**清理（推荐 git-filter-repo）**：
```bash
# 0. 安装 git-filter-repo（macOS）
brew install git-filter-repo

# 1. 进入仓库
cd ~/Documents/GitHub/Anxin-Smart-Legal-Services

# 2. 列出要清除的路径（与 1.2 节一致）
cat > /tmp/anxin-paths-to-remove.txt <<'EOF'
.env
backend/.env
backend/.env.local
frontend/.env
frontend/.env.tauri
EOF

# 3. 执行清理（dry-run 先看效果，加 --analyze 可以看分析报告）
git filter-repo --analyze
git filter-repo --invert-paths --paths-from-file /tmp/anxin-paths-to-remove.txt --dry-run

# 4. 实际执行（不可逆）
git filter-repo --invert-paths --paths-from-file /tmp/anxin-paths-to-remove.txt

# 5. filter-repo 会自动移除 origin remote。重新加回去：
git remote add origin https://github.com/tiantangcao1980-web/Anxin-Smart-Legal-Services.git
git remote add v3 https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant.git

# 6. 强制推送（破坏性，必须明确确认）
git push origin --force --all
git push origin --force --tags
git push v3 --force --all
git push v3 --force --tags
```

**对副仓库 Anxin-Smart-Assistant 同样操作**：
```bash
cd ~/Documents/GitHub/Anxin-Smart-Assistant
git filter-repo --invert-paths --paths-from-file /tmp/anxin-paths-to-remove.txt
git remote add origin https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant.git
git push origin --force --all
git push origin --force --tags
```

#### 4.3 GitHub fork 与 cache 处理

**GitHub 即使删除原始 commit，fork 中仍可能保留**。处理：

```
A. 在 GitHub 仓库 Settings → Branches 启用"分支保护"，强制 force-push 时通知所有协作者
B. 在 GitHub 仓库 Insights → Forks 列出所有 fork，逐个联系作者请求删除
C. 联系 GitHub Support 删除特定 commit 的 cache（https://docs.github.com/en/site-policy/content-removal-policies/github-private-information-removal-policy）
   邮件主题：Request removal of leaked secrets in commit history
   提供：仓库 URL、commit hash（ed8ea03 等）、私密信息类型、已轮换证明
```

#### 4.4 团队同步

```bash
# 所有协作者必须重新 clone（旧 clone 的本地仓不能再 push）
# 协作者操作：
mv ~/Documents/GitHub/Anxin-Smart-Legal-Services ~/Documents/GitHub/Anxin-Smart-Legal-Services.OLD
git clone https://github.com/tiantangcao1980-web/Anxin-Smart-Legal-Services.git
# 把本地 worktree 的未提交工作 cherry-pick 过来
```

---

### Step 5 — 验证 + 加固防再发（Day 1 下午，2 小时）

#### 5.1 验证旧凭据已失效

对每条 🔴 凭据，用旧值打一次 API 调用，**预期返回 401 / 403 / 凭据无效**：

```bash
# 示例：OpenAI
curl https://api.openai.com/v1/models \
    -H "Authorization: Bearer <旧 key>" \
    | grep -i "invalid\|expired\|unauthorized"
# 预期：返回 invalid_api_key

# 示例：微信支付（用商户号 + 旧 key 调用查询订单接口）
# 预期：签名校验失败
```

#### 5.2 加固防再发

```bash
# 1. 安装 pre-commit + gitleaks（项目根）
cd ~/Documents/GitHub/Anxin-Smart-Legal-Services
brew install pre-commit gitleaks

# 2. 写 .pre-commit-config.yaml（详见 04-ci-security-scan.md）

# 3. 安装 hooks
pre-commit install

# 4. 一次性扫描历史，确认无残留
gitleaks detect --source . --report-path gitleaks-report.json
```

#### 5.3 GitHub Secret Scanning + Push Protection

```
GitHub 仓库 → Settings → Code security and analysis →
  ☑ Secret scanning
  ☑ Push protection（拦截 push 时含 secret 的 commit）
```

**这是免费且关键的防再发机制，必须开启**。

#### 5.4 应急联系人 + 时间戳记录

在 `docs/audit/00-platform/_secret-rotation-log.private.md`（**入 .gitignore**）记录：

```markdown
# 密钥轮换执行日志（私密）

| 时间 | 操作人 | 凭据 | 旧值前 4 位 | 新值前 4 位 | 失效验证 |
|---|---|---|---|---|---|
| 2026-05-04 14:32 | <用户> | OPENAI_API_KEY | sk-A... | sk-B... | ✅ 旧值返回 401 |
| ... | ... | ... | ... | ... | ... |
```

---

## 3. 风险与回滚

### 3.1 强制推送的回滚

如果 `git push --force` 后发现误删：

```bash
# 在备份镜像中找回
cd ~/Documents/GitHub/Anxin-Smart-Legal-Services.bak.YYYYMMDD.git
git push --force https://github.com/tiantangcao1980-web/Anxin-Smart-Legal-Services.git --all

# 然后重新做 filter-repo
```

### 3.2 凭据切换业务回滚

如果新凭据上生产后业务报错：
- 不要立即恢复旧凭据（旧凭据已失效，恢复无意义）
- 在第三方控制台**生成第二个新凭据**，替换不工作的新凭据
- 留 24 小时观察期再彻底关掉旧凭据所在槽位

### 3.3 协作者本地仓的处理

强制推送后，协作者本地的旧分支不能再 push（Git 会拒绝 non-fast-forward）。
- 推荐：协作者 `git clone` 一份新的，把本地工作 cherry-pick 过去
- 不推荐：让协作者自己 force-push，会引入更多冲突

---

## 4. 时间线（用户执行节奏建议）

```
Day 0 上午
  09:00 - 09:30  Step 1 现状盘点
  09:30 - 10:00  Step 2 影响面定级
  10:00 - 12:00  Step 3 生成新凭据（仅 🔴 + 🟠 项）

Day 0 下午
  14:00 - 16:00  Step 4.1 旧凭据失效（每个第三方控制台逐个操作）
  16:00 - 17:00  Step 4.2 Git 历史清理（在所有协作者 push 完后）
  17:00 - 18:00  Step 4.3 GitHub fork 处理 + Step 4.4 团队同步

Day 1 上午
  09:00 - 11:00  Step 5.1 验证失效
  11:00 - 12:00  Step 5.2/5.3/5.4 加固防再发

Day 1 下午
  14:00         M-A 里程碑达成 → 进入波次 1（任务 1 + 任务 2）
```

---

## 5. 用户必须答复 Claude 的事项（开工前）

- [ ] 仓库 `Anxin-Smart-Legal-Services` 当前是 public 还是 private？
- [ ] 仓库 `Anxin-Smart-Assistant` 同问？
- [ ] 自 2026-03-28 commit `ed8ea03` 以来，是否已有外部 fork、star、或 GitGuardian 类工具告警？
- [ ] 当前是否有真实付费用户、订阅账号、生产数据？
- [ ] 是否有现成的 secret 管理方案（HashiCorp Vault / AWS Secrets Manager / 阿里云 KMS / 腾讯云 SSM）可以承接新凭据？
- [ ] 团队规模 + 是否所有协作者都能在同一天配合 force-push 后的 re-clone？

收到答复后，Claude 会：
1. 把"紧急程度"重新定级
2. 把时间线收紧或拉长
3. 调整 Step 4 的 fork/cache 处理章节

---

## 6. 本 SOP 的"已知不足"

- 本 SOP 假设用户拥有所有必要的第三方账号写权限。若用户是子账号，需先申请管理员权限
- 本 SOP 不涵盖"密钥轮换后的合规通报"（如有 GDPR / 等保 2.0 / 律师对客户告知义务）
- 本 SOP 不涵盖"如果旧凭据已被滥用（异常扣费 / 异常调用）的事后追溯"——若发现，立即联系第三方平台风控
- BFG 备选方案未详写。如果用户不方便装 git-filter-repo，可用 BFG，但 BFG 对子目录处理不如 filter-repo 精确

---

> 文档作者：Claude Code
> 状态：等待用户答复 §5 后激活
> 执行者：用户（Claude 不替执行任何破坏性 Git / 控制台操作）
