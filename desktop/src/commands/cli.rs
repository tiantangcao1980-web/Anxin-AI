#![allow(dead_code)]

/// CLI 命令接口
///
/// 将安心法务的核心功能暴露为桌面端命令，
/// 可通过 Tauri IPC 调用，也可未来扩展为真正的 shell 命令。
///
/// 安全约束（Harness policy_engine）：
/// - 使用 API Key 认证（X-API-Key header）
/// - 每条命令审计记录
/// - 高危操作禁止（delete/payment/sign）
/// - 频率限制 30 req/min

use serde::{Deserialize, Serialize};
use tauri::command;

/// CLI 命令请求
#[allow(dead_code)]
#[derive(Debug, Serialize, Deserialize)]
pub struct CLIRequest {
    pub command: String,
    pub args: std::collections::HashMap<String, serde_json::Value>,
}

/// CLI 命令响应
#[derive(Debug, Serialize, Deserialize)]
pub struct CLIResponse {
    pub success: bool,
    pub command: String,
    pub result: Option<serde_json::Value>,
    pub error: Option<String>,
    pub execution_time_ms: f64,
}

/// 执行 CLI 命令
///
/// 前端调用：`invoke('cli_execute', { command, args })`
/// 实际通过 HTTP 转发到后端 /api/v1/cli/execute
#[command]
pub async fn cli_execute(
    command: String,
    args: std::collections::HashMap<String, serde_json::Value>,
    api_key: Option<String>,
) -> Result<CLIResponse, String> {
    let api_key = api_key.unwrap_or_default();
    if api_key.is_empty() {
        return Ok(CLIResponse {
            success: false,
            command: command.clone(),
            result: None,
            error: Some("请先配置 API Key（设置 → CLI 密钥管理）".to_string()),
            execution_time_ms: 0.0,
        });
    }

    let start = std::time::Instant::now();

    // 构建请求
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;

    let body = serde_json::json!({
        "command": command,
        "args": args,
    });

    // 从环境或配置获取后端 URL
    let backend_url = std::env::var("ANXIN_BACKEND_URL")
        .unwrap_or_else(|_| "http://localhost:8001".to_string());

    let response = client
        .post(format!("{}/api/v1/cli/execute", backend_url))
        .header("X-API-Key", &api_key)
        .header("Content-Type", "application/json")
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("请求失败: {}", e))?;

    let elapsed = start.elapsed().as_secs_f64() * 1000.0;

    if response.status().is_success() {
        let data: CLIResponse = response
            .json()
            .await
            .map_err(|e| format!("解析响应失败: {}", e))?;
        Ok(data)
    } else {
        let status = response.status().as_u16();
        let text = response.text().await.unwrap_or_default();
        Ok(CLIResponse {
            success: false,
            command,
            result: None,
            error: Some(format!("HTTP {}: {}", status, text)),
            execution_time_ms: elapsed,
        })
    }
}

/// 创建 API Key
#[command]
pub async fn cli_create_key(
    name: String,
    scopes: Vec<String>,
    expires_days: Option<u32>,
) -> Result<serde_json::Value, String> {
    let backend_url = std::env::var("ANXIN_BACKEND_URL")
        .unwrap_or_else(|_| "http://localhost:8001".to_string());

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    let body = serde_json::json!({
        "name": name,
        "scopes": scopes,
        "expires_days": expires_days.unwrap_or(90),
    });

    let response = client
        .post(format!("{}/api/v1/cli/keys", backend_url))
        .header("Content-Type", "application/json")
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("请求失败: {}", e))?;

    let data: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("解析响应失败: {}", e))?;

    Ok(data)
}

/// 列出 API Keys
#[command]
pub async fn cli_list_keys() -> Result<serde_json::Value, String> {
    let backend_url = std::env::var("ANXIN_BACKEND_URL")
        .unwrap_or_else(|_| "http://localhost:8001".to_string());

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    let response = client
        .get(format!("{}/api/v1/cli/keys", backend_url))
        .send()
        .await
        .map_err(|e| format!("请求失败: {}", e))?;

    let data: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("解析响应失败: {}", e))?;

    Ok(data)
}
