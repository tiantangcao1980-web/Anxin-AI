# 广东省政务电子签章接入计划

> **状态**: 调研完成 + 代码层 placeholder 已就位, 实际对接需业务方/法务推动
> **日期**: 2026-05-14
> **背景**: 产品方向调整 — 当前阶段以核心功能验证为主, 签约场景优先接入政务平台, 暂缓商业化电子签 (e签宝/法大大)。

---

## 一、为什么选政务签章 (而非商业化电子签)

| 维度 | 政务签章 (GDCA / 粤企签) | 商业化电子签 (e签宝 / 法大大) |
|---|---|---|
| **法律效力** | 《电子签名法》+ 广东省地方条例; 政务场景出文具同等效力 | 《电子签名法》, 民商合同主流 |
| **数据驻留** | 政务云内, **不出粤**; 满足等保 + 政务专网 | 商业云, 跨省存储 |
| **客户感知** | 与政府办事一致体验, 信任度高 (尤其涉企政务流程) | 商业品牌, 与政府办事流程脱节 |
| **接入成本** | 0 至中等 (粤企签 OAuth-like; GDCA 需 CA 证书) | 中等 (商业 SaaS, 月费 + 调用计费) |
| **当前阶段 ROI** | ✅ 政府/法务/律所客户验证 PMF 直接可用 | 🟡 商业化 PMF 后再启用更经济 |

---

## 二、调研结论 — 两个核心入口

### 1. GDCA (广东省数字证书认证中心 / 数安时代科技股份有限公司)

| 属性 | 数据 |
|---|---|
| 网址 | https://www.gdca.com.cn |
| 商务热线 | 95105813 |
| 法定资质 | 工信部颁发电子认证服务许可证 + 国家密码管理局颁发电子政务电子认证服务资质 |
| 接入方式 | 客户端 SDK + 服务端 API (NDA 后由商务方提供) |
| 已接入政务平台 | 政府采购智慧云 / 公共资源交易 / 施工图审查 / 等十余个 |
| 签名算法 | 国密 SM2 / SM3 / SM4 + RSA 2048 |
| 用户证书载体 | 实体 USB Key / 手机移动证书 / 软证书 (云证书) |

**适用场景**:
- 正式合同签发 (政府/律所/事业单位主体)
- 跨部门审批文件电子签章
- 法律意见书 / 评估报告等需要法定签章的产物

### 2. 粤企签 (粤商通体系 / 数字广东)

| 属性 | 数据 |
|---|---|
| 网址 | https://www.digitalgd.com.cn/construction/business/yst/ |
| 商务对接 | 数字广东 (Tencent 与广东省政府合资), 12345 政务服务热线 |
| 已上线服务 | 1094+ 涉企政务事项 + 158 类电子证照 |
| 用户认证 | 微信小程序刷脸 + 法人手机号验证 (UX 比 CA 轻量) |
| 适用 | 高新企业认定 / 知识产权申报 / 涉企政务办理 |

**适用场景**:
- 中小企业用户的轻量级签约 (合同 / 服务确认 / 申报材料)
- 与政务办事链路打通 (例如尽调报告直接用于高企申报)
- 移动场景 (粤商通 APP 内调起)

---

## 三、代码层现状 (2026-05-14)

### Provider Placeholder 已就位

`backend/src/services/esign_service.py`:

```python
class GdcaProvider(ESignProvider):
    """广东省 GDCA 政务电子签章 Provider — Placeholder (待接入)"""
    PROVIDER_NAME = "gdca"
    # 调用任何方法 → ESignProviderConfigError("尚未接入")

class YueQiQianProvider(ESignProvider):
    """粤企签 (粤商通体系) 移动政务电子签 Provider — Placeholder (待接入)"""
    PROVIDER_NAME = "yueqishang"
    # 调用任何方法 → ESignProviderConfigError("尚未接入")
```

### 环境变量预留

```bash
# GDCA
GDCA_APP_ID=<待申请>
GDCA_APP_SECRET=<待申请>
GDCA_API_ENDPOINT=<NDA 后提供>
GDCA_CA_CERT_PATH=<.pfx / .p12 路径>

# 粤企签
YUEQIQIAN_APP_ID=<待申请>
YUEQIQIAN_APP_SECRET=<待申请>
YUEQIQIAN_API_ENDPOINT=<待申请>
```

### 切换 Provider

```bash
# 启用 GDCA
ESIGN_PROVIDER=gdca

# 启用粤企签
ESIGN_PROVIDER=yueqishang  # or yueqiqian / yuesangtong (别名)
```

---

## 四、接入清单 (业务方推进顺序)

### Phase 1: 商务对接 (2-4 周, 业务方驱动)

| 步骤 | 责任方 | 输入 / 输出 |
|---|---|---|
| 1.1 GDCA 商务洽谈 | 业务负责人 | 营业执照 / 法人证 / 业务场景说明 |
| 1.2 签订 NDA + 商务合同 | 法务 + 业务 | NDA / 商务合同 + 报价单 |
| 1.3 GDCA 提供测试环境 | GDCA 商务 | 测试 endpoint / appId / appSecret / 测试 CA 证书 |
| 1.4 粤商通企业入驻 | 业务负责人 | 企业实名认证 + 法人代表认证 |
| 1.5 粤企签开发者权限 | 数字广东 | 开发者凭据 + 沙箱环境访问 |

### Phase 2: 技术对接 (1-2 周, 工程驱动)

| 步骤 | 责任方 | 输出 |
|---|---|---|
| 2.1 阅读 GDCA / 粤企签 API 文档 | 后端工程师 | 接入设计稿 |
| 2.2 完善 `GdcaProvider._call_api` 国密签名 | 后端 | 单元测试覆盖签名生成 |
| 2.3 完善 `YueQiQianProvider` OAuth 风格授权 | 后端 | 单元测试覆盖 token 刷新 |
| 2.4 沙箱跑通 5 个流程 | 后端 + QA | sandbox transcript |
| 2.5 生产证书申请 + 公网回调 URL 配置 | 运维 + 业务 | 生产凭据 + ICP/公网证 |

### Phase 3: 验收上线 (1 周)

| 步骤 | 责任方 | Gate |
|---|---|---|
| 3.1 安全审计 (国密合规) | 安全 | 等保备案号 |
| 3.2 真实合同签发 5 笔 (各类型) | QA + 业务 | live transcripts |
| 3.3 切换 ESIGN_PROVIDER=gdca / yueqishang | 运维 | 流量切换 |
| 3.4 监控 + 告警 | 运维 | Sentry / Prometheus 看板 |

---

## 五、降级与回退策略

| 场景 | 策略 |
|---|---|
| GDCA 政务云不可达 | log ERROR + 不静默 fallback (政务场景禁止 fail-open) |
| 用户证书过期 | UI 提示去政务大厅续期, 不自动绕过 |
| 粤企签 token 过期 | 后台自动刷新; 失败 3 次 → 触发人工干预 |
| 商业化场景 (非政务客户) | 切换 ESIGN_PROVIDER=esignbao/fadada (现有 placeholder 已可用) |

---

## 六、相关文档

- [docs/REQUIREMENTS.md](../REQUIREMENTS.md) — 业务需求总表 (P3 商业化签约段落)
- [docs/DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) §4.5 候补 — 政务签约引入
- [docs/standards/security-standard.md](../standards/security-standard.md) — 国密合规要求
- [docs/release/external-resource-handoff.md](../release/external-resource-handoff.md) — 外部资源申请清单

---

## 七、产品决策记录

**2026-05-14 用户决策**:
> "签约和支付等设置付费的功能其实可以先不作为项目核心任务，因为目前我们的核心任务是先把项目的核心功能先验证了，再能谈后续的商业化。签约可以引入政府的平台，去看看广东省政府有没有数字签约的功能，添加上去即可。"

**实施影响**:
- ✅ 代码层 GDCA + 粤企签 Provider placeholder 已就位 (本次)
- ✅ ESIGN_PROVIDER 环境变量支持 5 种渠道 (mock / gdca / yueqishang / esignbao / fadada)
- ✅ 文档化接入路径 (本文档)
- 🟡 真实对接需业务方启动 Phase 1 商务对接
- 📉 e签宝 / 法大大 在 DEVELOPMENT_PLAN 中从 P0/P1 降级为 P3 (商业化阶段)
