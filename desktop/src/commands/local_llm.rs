use crate::models::{AppMode, SharedAppState};
use crate::services::runtime_config;
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};
use tauri::{AppHandle, State};

const DEFAULT_LOCAL_LLM_ENDPOINT: &str = "http://localhost:11434";

fn configured_default_model(app: &AppHandle, state: &crate::models::AppStateData) -> String {
    runtime_config::load_or_default_for_app(app, state)
        .ok()
        .and_then(|config| config.local_model)
        .unwrap_or_else(runtime_config::default_local_model_name)
}

fn is_private_ipv4(address: Ipv4Addr) -> bool {
    address.is_loopback()
        || address.is_private()
        || address.is_link_local()
        || address.octets()[0] == 100 && (64..=127).contains(&address.octets()[1])
}

fn is_private_ipv6(address: Ipv6Addr) -> bool {
    address.is_loopback()
        || address.is_unicast_link_local()
        || (address.segments()[0] & 0xfe00) == 0xfc00
}

fn is_allowed_local_llm_host(host: &str) -> bool {
    let normalized = host.trim_end_matches('.').to_ascii_lowercase();
    if normalized == "localhost" || normalized.ends_with(".localhost") {
        return true;
    }
    if normalized.ends_with(".local") {
        return true;
    }
    match normalized.parse::<IpAddr>() {
        Ok(IpAddr::V4(address)) => is_private_ipv4(address),
        Ok(IpAddr::V6(address)) => is_private_ipv6(address),
        Err(_) => false,
    }
}

fn normalize_local_llm_endpoint(input: &str) -> Result<String, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Err("本地模型端点不能为空".to_string());
    }

    let parsed = reqwest::Url::parse(trimmed)
        .map_err(|_| "本地模型端点必须是完整的 http:// 或 https:// 地址".to_string())?;
    if !matches!(parsed.scheme(), "http" | "https") {
        return Err("本地模型端点只允许 http 或 https 协议".to_string());
    }
    if !parsed.username().is_empty() || parsed.password().is_some() {
        return Err("本地模型端点不能包含用户名或密码".to_string());
    }
    if parsed.path() != "/" || parsed.query().is_some() || parsed.fragment().is_some() {
        return Err("本地模型端点不能包含路径、查询参数或片段".to_string());
    }
    let host = parsed
        .host_str()
        .ok_or_else(|| "本地模型端点缺少主机名".to_string())?;
    if !is_allowed_local_llm_host(host) {
        return Err("本地模型端点必须指向 localhost、私网地址或 .local 主机".to_string());
    }

    Ok(parsed.to_string().trim_end_matches('/').to_string())
}

fn local_llm_endpoint_from_env() -> Result<String, String> {
    let raw =
        std::env::var("OLLAMA_URL").unwrap_or_else(|_| DEFAULT_LOCAL_LLM_ENDPOINT.to_string());
    normalize_local_llm_endpoint(&raw)
}

/// 本地 LLM 聊天（绝密模式和混合模式下使用）
///
/// 在绝密模式下，所有 AI 推理都通过本地 LLM 完成。
/// 在混合模式下，用户可选择使用本地或云端 LLM。
///
/// 支持的本地后端：
/// - Ollama (http://localhost:11434)
/// - llama.cpp server
/// - LM Studio
#[tauri::command]
pub async fn local_llm_chat(
    message: String,
    model: Option<String>,
    system_prompt: Option<String>,
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let snapshot = {
        let s = state.read().await;
        s.clone()
    };

    if snapshot.mode == AppMode::Cloud {
        return Err("云端模式下请使用云端 API".to_string());
    }

    let model_name = match model {
        Some(value) => runtime_config::normalize_local_model_name(&value)?,
        None => configured_default_model(&app, &snapshot),
    };
    let ollama_url = local_llm_endpoint_from_env()?;

    let client = reqwest::Client::new();

    let mut messages = Vec::new();

    // 添加法务系统提示词
    let sys_prompt = system_prompt.unwrap_or_else(|| {
        "你是安心智能助手AI助手，专注于中国法律咨询服务。请用中文回答。".to_string()
    });
    messages.push(serde_json::json!({
        "role": "system",
        "content": sys_prompt
    }));

    messages.push(serde_json::json!({
        "role": "user",
        "content": message
    }));

    let response = client
        .post(format!("{}/api/chat", ollama_url))
        .json(&serde_json::json!({
            "model": model_name,
            "messages": messages,
            "stream": false
        }))
        .send()
        .await
        .map_err(|e| format!("本地 LLM 连接失败: {}。请确保 Ollama 已启动。", e))?;

    if !response.status().is_success() {
        return Err(format!("本地 LLM 返回错误: {}", response.status()));
    }

    let body: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("解析 LLM 响应失败: {}", e))?;

    Ok(serde_json::json!({
        "success": true,
        "source": "local",
        "model": model_name,
        "message": body.get("message").and_then(|m| m.get("content")),
        "total_duration": body.get("total_duration"),
    }))
}

/// 获取本地 LLM 的非敏感运行配置。
#[tauri::command]
pub async fn get_local_llm_config(
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let snapshot = {
        let s = state.read().await;
        s.clone()
    };
    let config = runtime_config::load_or_default_for_app(&app, &snapshot)?;
    let default_model = config
        .local_model
        .unwrap_or_else(runtime_config::default_local_model_name);
    let endpoint_url = local_llm_endpoint_from_env()?;

    Ok(serde_json::json!({
        "default_model": default_model,
        "endpoint_url": endpoint_url,
        "stores_secrets": false,
        "message": "仅保存模型名称和本地端点引用，不保存 API 密钥"
    }))
}

/// 设置 Quick Query 与本地模式默认使用的本地模型名称。
#[tauri::command]
pub async fn set_default_local_model(
    model: String,
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let normalized = runtime_config::normalize_local_model_name(&model)?;
    let current = {
        let s = state.read().await;
        s.clone()
    };
    let mut config = runtime_config::load_or_default_for_app(&app, &current)?;
    config.local_model = Some(normalized.clone());
    runtime_config::save_for_app(&app, &config)?;

    Ok(serde_json::json!({
        "success": true,
        "default_model": normalized,
        "message": "本地默认模型已更新"
    }))
}

/// 列出本地可用的 LLM 模型
#[tauri::command]
pub async fn list_local_models() -> Result<serde_json::Value, String> {
    let ollama_url = local_llm_endpoint_from_env()?;

    let client = reqwest::Client::new();

    let response = client
        .get(format!("{}/api/tags", ollama_url))
        .send()
        .await
        .map_err(|e| format!("无法连接本地 LLM 服务: {}", e))?;

    if !response.status().is_success() {
        return Ok(serde_json::json!({
            "available": false,
            "models": [],
            "message": "本地 LLM 服务未运行"
        }));
    }

    let body: serde_json::Value = response.json().await.map_err(|e| e.to_string())?;

    Ok(serde_json::json!({
        "available": true,
        "models": body.get("models").unwrap_or(&serde_json::json!([]))
    }))
}

#[cfg(test)]
mod tests {
    use super::normalize_local_llm_endpoint;
    use crate::services::runtime_config::normalize_local_model_name;

    #[test]
    fn validates_local_model_names_for_ipc_boundaries() {
        assert_eq!(
            normalize_local_model_name(" qwen2.5:7b ").unwrap(),
            "qwen2.5:7b"
        );
        assert_eq!(
            normalize_local_model_name("library/llama3.1:8b").unwrap(),
            "library/llama3.1:8b"
        );
        assert!(normalize_local_model_name("").is_err());
        assert!(normalize_local_model_name("qwen 7b").is_err());
        assert!(normalize_local_model_name("qwen;export TOKEN=secret").is_err());
    }

    #[test]
    fn validates_local_llm_endpoint_is_local_or_private() {
        assert_eq!(
            normalize_local_llm_endpoint(" http://localhost:11434/ ").unwrap(),
            "http://localhost:11434"
        );
        assert_eq!(
            normalize_local_llm_endpoint("http://127.0.0.1:11434").unwrap(),
            "http://127.0.0.1:11434"
        );
        assert_eq!(
            normalize_local_llm_endpoint("http://192.168.1.20:11434").unwrap(),
            "http://192.168.1.20:11434"
        );
        assert_eq!(
            normalize_local_llm_endpoint("http://ollama.local:11434").unwrap(),
            "http://ollama.local:11434"
        );
    }

    #[test]
    fn rejects_remote_or_credentialed_local_llm_endpoints() {
        assert!(normalize_local_llm_endpoint("https://api.example.com").is_err());
        assert!(normalize_local_llm_endpoint("http://8.8.8.8:11434").is_err());
        assert!(normalize_local_llm_endpoint("http://token@localhost:11434").is_err());
        assert!(normalize_local_llm_endpoint("http://localhost:11434/api/tags").is_err());
        assert!(normalize_local_llm_endpoint("file:///tmp/model.sock").is_err());
    }
}

/// 检查本地 LLM 服务是否可用
#[tauri::command]
pub async fn check_local_llm_status() -> Result<serde_json::Value, String> {
    let ollama_url = local_llm_endpoint_from_env()?;

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(3))
        .build()
        .map_err(|e| e.to_string())?;

    match client.get(&ollama_url).send().await {
        Ok(resp) => Ok(serde_json::json!({
            "available": resp.status().is_success(),
            "url": ollama_url,
            "status": resp.status().as_u16()
        })),
        Err(_) => Ok(serde_json::json!({
            "available": false,
            "url": ollama_url,
            "message": "Ollama 服务未运行，请启动 Ollama"
        })),
    }
}
