use crate::models::{AppMode, SharedAppState};
use tauri::State;

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
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let mode = {
        let s = state.read().await;
        s.mode
    };

    if mode == AppMode::Cloud {
        return Err("云端模式下请使用云端 API".to_string());
    }

    let model_name = model.unwrap_or_else(|| "qwen2.5:7b".to_string());
    let ollama_url = std::env::var("OLLAMA_URL")
        .unwrap_or_else(|_| "http://localhost:11434".to_string());

    let client = reqwest::Client::new();

    let mut messages = Vec::new();

    // 添加法务系统提示词
    let sys_prompt = system_prompt.unwrap_or_else(|| {
        "你是安心法务AI助手，专注于中国法律咨询服务。请用中文回答。".to_string()
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
        return Err(format!(
            "本地 LLM 返回错误: {}",
            response.status()
        ));
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

/// 列出本地可用的 LLM 模型
#[tauri::command]
pub async fn list_local_models() -> Result<serde_json::Value, String> {
    let ollama_url = std::env::var("OLLAMA_URL")
        .unwrap_or_else(|_| "http://localhost:11434".to_string());

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

    let body: serde_json::Value = response
        .json()
        .await
        .map_err(|e| e.to_string())?;

    Ok(serde_json::json!({
        "available": true,
        "models": body.get("models").unwrap_or(&serde_json::json!([]))
    }))
}

/// 检查本地 LLM 服务是否可用
#[tauri::command]
pub async fn check_local_llm_status() -> Result<serde_json::Value, String> {
    let ollama_url = std::env::var("OLLAMA_URL")
        .unwrap_or_else(|_| "http://localhost:11434".to_string());

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
