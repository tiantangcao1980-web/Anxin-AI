# 存算一体硬件接入协议（草案 v0.1）

本文档定义「安心法务 × 独立存算一体硬件」的接入协议。
目标：硬件出厂预装安心法务服务（backend + Ollama + 本地知识库），
用户只需上电 → 连接同局域网 → 在客户端一键绑定即可使用全部本地功能。

---

## 1. 硬件形态参考

- **规格**：ARM64 / x86_64 小主机（RK3588 / N100 / M1 Mini 等）
- **存储**：≥ 512 GB NVMe SSD（需预留 50 GB 给离线法规+判例包）
- **内存**：≥ 16 GB（7B 量化模型最低 8 GB，13B 要 14 GB）
- **推理加速**：可选 GPU / NPU（RK3588 内置 NPU 6 TOPS 即可）
- **TEE**：TrustZone 或 Intel SGX（用于硬件绑定的设备证书）

## 2. 固件软件栈

```
┌────────────────────────────────────┐
│ 系统托盘 UI / OTA 控制面           │  ← 硬件自带 Web UI（80/8080）
├────────────────────────────────────┤
│ 安心法务 backend (FastAPI)          │  ← 容器化（containerd）
│ Ollama + Embedding server           │
│ Chroma + SQLite（法规/判例）         │
│ MinIO 单机模式（私有桶）             │
├────────────────────────────────────┤
│ Linux / Yocto + TEE + 设备私钥       │
└────────────────────────────────────┘
```

## 3. 设备身份与绑定

### 3.1 设备证书

- 出厂时由工厂私钥在 TEE 中注入 **设备私钥 + X.509 证书**
- 证书 CN = `appliance-<SN>`, 带 SAN 包含 MAC / SN
- 根 CA 由安心法务官方发布（内嵌客户端 trust bundle）

### 3.2 客户端发现

客户端通过两种方式发现设备：

**mDNS**（首选）：
```
_anxin-appliance._tcp.local
   hostname = anxin-appliance-<SN>.local
   port     = 8443
   txt      = { sn=..., fw=..., caps=['llm','kb','ocr'] }
```

**扫码绑定**（兜底）：
- 硬件 Web UI 生成二维码，内容为 `anxin-appliance://<ip>:8443?token=<one-time>`
- 客户端扫码后发起 TLS 握手

### 3.3 TLS 握手与绑定

```
Client → Appliance:  TLS 1.3 ClientHello (SNI=anxin-appliance-<SN>)
Appliance ← Client:  出示设备证书
Client → Appliance:  POST /bind { client_id, client_nonce, user_token }
Appliance ← Client:  { device_id, device_nonce, signed_challenge }
Client 校验 signed_challenge 由设备证书私钥签名
双方交换 session_key，写入本地 keychain
```

## 4. API 兼容性

设备上的 backend 暴露与云端**相同的 `/api/v1/*`**，客户端配置 `backend_url` 指向设备即可。

约束：
- 设备默认禁用 `/privacy/export` 跨设备导出（受 TEE 绑定限制）
- 离线包下载统一指向设备本地路径
- 同步引擎 push/pull 在设备与用户其它客户端之间走 LAN 直连

## 5. OTA 固件升级

- 设备定期 `GET https://api.anxinlegal.com/api/v1/firmware/{sn}/latest`
- 返回 `{ version, url, signature }`，签名用安心根私钥
- 升级包在 TEE 内校验签名后写入 dual-partition，重启 fallback 友好

## 6. 工厂预置工作流

| 步骤 | 执行者 | 产出 |
|---|---|---|
| 1. 烧录系统镜像 | 工厂 | 基础 OS + 容器运行时 |
| 2. TEE 注入设备私钥 + 证书 | 工厂 HSM | `/secure/device.key` `/secure/device.crt` |
| 3. 拉取 backend / frontend / ollama 容器 | 工厂流水线 | 预热镜像，首启即用 |
| 4. 预置法规 core pack（50 MB） | 工厂 | SQLite + FTS5 索引 |
| 5. 首次开机向导 | 终端用户 | 选 WiFi → 绑定账号 → 拉取 full pack（可选） |

## 7. 最低接入协议变更（本轮代码层）

为让"硬件一体机"能被现有软件栈识别，本轮已埋以下占位：

- `backend/src/core/config.py` 新增 `RUNTIME_MODE` 字段（cloud / hybrid / nas-lite / local / appliance）
- `backend/src/core/llm_helper.py` 增加 Ollama fallback 链路
- `backend/src/api/routes/offline_packs.py` 提供离线包目录接口
- `desktop/src/commands/app_mode.rs`（已存在）负责本地模式 + 硬件模式 UI

下一步（非本轮范围）：
- 实现 mDNS 发现组件
- 实现 TEE 设备证书校验中间件
- 实现 `/firmware/*` OTA 端点
- 制作工厂预置脚本 `scripts/factory-setup.sh`

## 8. 安全基线

- **默认关闭公网直连**：设备出厂默认 `WAN_INBOUND=false`，用户必须主动开启
- **账号绑定限制**：每个设备最多绑定 5 个账号，新增需通过"注销旧设备"流程
- **审计日志本地留存**：90 天，用户可通过 Web UI 导出
- **紧急擦除**：长按物理按键 10 秒触发设备本地数据全擦除（TEE 侧销毁密钥即可）

## 9. 未来路线

- 家庭律师多账号共用设备（带家长模式）
- 小型事务所场景的多设备联盟 / HA
- 与国产信创软硬件（飞腾 / 龙芯 / 麒麟 OS）的适配认证
