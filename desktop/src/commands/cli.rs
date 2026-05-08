#![allow(dead_code)]

/// CLI 命令接口
///
/// 将安心法务的核心功能暴露为桌面端命令，
/// 可通过 Tauri IPC 调用，也可未来扩展为真正的 shell 命令。
///
/// 安全约束（Harness policy_engine）：
/// - 使用 API Key 认证（X-API-Key header）
/// - 商业环境下使用短期 route token（X-Capability-Route-Token header）
/// - 每条命令审计记录
/// - 高危操作禁止（delete/payment/sign）
/// - 频率限制 30 req/min
use crate::commands::privacy_guard::ensure_data_network_allowed;
use crate::models::SharedAppState;
use serde::{Deserialize, Serialize};
use tauri::{command, State};

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

#[derive(Debug, Serialize)]
struct CLIRouteTokenRequest {
    scope: String,
    route_key: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CLIRouteTokenResponse {
    success: bool,
    required: bool,
    route_token: Option<String>,
    error: Option<String>,
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
    route_token: Option<String>,
    route_key: Option<String>,
    state: State<'_, SharedAppState>,
) -> Result<CLIResponse, String> {
    ensure_data_network_allowed(state.inner(), "执行 CLI 命令").await?;

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
    let required_scope = cli_scope_for_command(&command);

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;

    let body = serde_json::json!({
        "command": command,
        "args": args,
    });

    // 从环境或配置获取后端 URL
    let backend_url =
        std::env::var("ANXIN_BACKEND_URL").unwrap_or_else(|_| "http://localhost:8001".to_string());

    let route_token = match normalize_optional_string(route_token) {
        Some(token) => Some(token),
        None => match request_cli_route_token(
            &client,
            &backend_url,
            &api_key,
            required_scope,
            normalize_optional_string(route_key),
        )
        .await
        {
            Ok(token) => token,
            Err(error) => {
                let elapsed = start.elapsed().as_secs_f64() * 1000.0;
                return Ok(CLIResponse {
                    success: false,
                    command: command.clone(),
                    result: None,
                    error: Some(error),
                    execution_time_ms: elapsed,
                });
            }
        },
    };

    let mut request_builder = client
        .post(format!("{}/api/v1/cli/execute", backend_url))
        .header("X-API-Key", &api_key)
        .header("Content-Type", "application/json");
    if let Some(route_token) = route_token.as_ref() {
        request_builder = request_builder.header("X-Capability-Route-Token", route_token);
    }

    let response = request_builder
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

fn cli_scope_for_command(command: &str) -> &'static str {
    match command.trim().to_ascii_lowercase().as_str() {
        "consult" | "review" | "draft" => "chat",
        "export" => "export",
        _ => "read",
    }
}

fn normalize_optional_string(value: Option<String>) -> Option<String> {
    value
        .map(|item| item.trim().to_string())
        .filter(|item| !item.is_empty())
}

async fn request_cli_route_token(
    client: &reqwest::Client,
    backend_url: &str,
    api_key: &str,
    scope: &str,
    route_key: Option<String>,
) -> Result<Option<String>, String> {
    let body = CLIRouteTokenRequest {
        scope: scope.to_string(),
        route_key: route_key
            .or_else(|| normalize_optional_string(std::env::var("ANXIN_CLI_ROUTE_KEY").ok())),
    };
    let response = client
        .post(format!("{}/api/v1/cli/route-token", backend_url))
        .header("X-API-Key", api_key)
        .header("Content-Type", "application/json")
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("CLI route token 请求失败: {}", e))?;

    let status = response.status();
    if status == reqwest::StatusCode::NOT_FOUND || status == reqwest::StatusCode::METHOD_NOT_ALLOWED
    {
        return Ok(None);
    }
    if !status.is_success() {
        let text = response.text().await.unwrap_or_default();
        return Err(format!(
            "CLI route token HTTP {}: {}",
            status.as_u16(),
            text
        ));
    }

    let data: CLIRouteTokenResponse = response
        .json()
        .await
        .map_err(|e| format!("解析 CLI route token 响应失败: {}", e))?;
    if data.success {
        return normalize_optional_string(data.route_token)
            .map(Some)
            .ok_or_else(|| "CLI route token 响应缺少 token".to_string());
    }
    if data.required {
        return Err(data
            .error
            .unwrap_or_else(|| "CLI route token 被治理策略拒绝".to_string()));
    }
    Ok(None)
}

/// 创建 API Key
#[command]
pub async fn cli_create_key(
    name: String,
    scopes: Vec<String>,
    expires_days: Option<u32>,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    ensure_data_network_allowed(state.inner(), "创建 CLI API Key").await?;

    let backend_url =
        std::env::var("ANXIN_BACKEND_URL").unwrap_or_else(|_| "http://localhost:8001".to_string());

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
pub async fn cli_list_keys(state: State<'_, SharedAppState>) -> Result<serde_json::Value, String> {
    ensure_data_network_allowed(state.inner(), "列出 CLI API Key").await?;

    let backend_url =
        std::env::var("ANXIN_BACKEND_URL").unwrap_or_else(|_| "http://localhost:8001".to_string());

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

#[cfg(test)]
mod tests {
    use super::{cli_scope_for_command, normalize_optional_string};

    #[test]
    fn maps_cli_commands_to_route_scopes() {
        assert_eq!(cli_scope_for_command("consult"), "chat");
        assert_eq!(cli_scope_for_command(" REVIEW "), "chat");
        assert_eq!(cli_scope_for_command("draft"), "chat");
        assert_eq!(cli_scope_for_command("export"), "export");
        assert_eq!(cli_scope_for_command("status"), "read");
        assert_eq!(cli_scope_for_command("unknown"), "read");
    }

    #[test]
    fn normalizes_blank_optional_strings() {
        assert_eq!(
            normalize_optional_string(Some(" token ".to_string())),
            Some("token".to_string())
        );
        assert_eq!(normalize_optional_string(Some("   ".to_string())), None);
        assert_eq!(normalize_optional_string(None), None);
    }
}
