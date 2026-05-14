/*!
 * 多端能力协商 — A5 (2026-05-14)
 *
 * Tauri 命令 `negotiate_capabilities`: 委托给云端
 * `/harness/capability/negotiate?platform=desktop&mode={mode}` 获取当前桌面
 * 端能力协商结果. 桌面端不再独立硬编码能力表, 与前端 `useCapabilities` hook
 * 共享同一份后端权威数据.
 *
 * 离线 / TopSecret 模式下云端不可达, 返回本地兜底表 (与前端 fallback 一致):
 *   - 所有 cloud/network 类 feature: false
 *   - 仅 document_export / legal_knowledge_base: true (本地包可用)
 */

use crate::models::SharedAppState;
use serde::{Deserialize, Serialize};
use tauri::State;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct NegotiationResult {
    pub platform: String,
    pub mode: String,
    pub available_features: serde_json::Map<String, serde_json::Value>,
    pub unavailable_features: Vec<String>,
    pub available_tasks: Vec<String>,
    pub warnings: Vec<String>,
    pub recommendations: Vec<String>,
    /// 来源: "cloud" (云端权威) 或 "fallback" (本地兜底)
    pub source: String,
}

fn local_fallback(mode: &str) -> NegotiationResult {
    // 本地兜底: 所有 cloud / network 类 feature 全关, 与 backend
    // capability_negotiator.MODE_CAPABILITIES[TOP_SECRET] 表保持一致
    let mut available = serde_json::Map::new();
    available.insert("document_export".to_string(), serde_json::json!(true));
    available.insert("legal_knowledge_base".to_string(), serde_json::json!(true));
    available.insert("offline_mode".to_string(), serde_json::json!(true));
    available.insert("local_llm".to_string(), serde_json::json!(true));
    for key in [
        "full_agent_orchestration",
        "knowledge_graph",
        "vector_search",
        "web_crawling",
        "real_time_collaboration",
        "audio_video_call",
        "multi_agent_consensus",
        "deep_research",
        "push_notification",
        "lawyer_matching",
        "sentiment_monitor",
        "due_diligence",
        "im_messaging",
        "case_market",
    ] {
        available.insert(key.to_string(), serde_json::json!(false));
    }

    NegotiationResult {
        platform: "desktop".to_string(),
        mode: mode.to_string(),
        available_features: available,
        unavailable_features: vec![
            "网络相关能力 (云端不可达, 已降级)".to_string(),
        ],
        available_tasks: vec!["general_consultation".to_string(), "document_summary".to_string()],
        warnings: vec!["云端 capability_negotiator 不可达, 已使用本地兜底表".to_string()],
        recommendations: vec!["切换到 hybrid/cloud 模式恢复全部能力".to_string()],
        source: "fallback".to_string(),
    }
}

/// 委托云端 capability_negotiator 获取当前模式的能力协商结果。
///
/// 调用方式 (前端 / Web)::
///   import { invoke } from "@tauri-apps/api/core"
///   const result = await invoke<NegotiationResult>("negotiate_capabilities", { mode: "hybrid" })
#[tauri::command]
pub async fn negotiate_capabilities(
    mode: String,
    state: State<'_, SharedAppState>,
) -> Result<NegotiationResult, String> {
    let app_state = state.read().await;
    let backend_url = app_state.backend_url.clone();
    let token = app_state.user_token.clone();
    drop(app_state);

    // TopSecret 模式下直接返回本地兜底, 不发请求 (节省时间 + 避免数据离境)
    if mode == "top_secret" {
        log::info!("[Capability] mode=top_secret, 使用本地兜底表");
        return Ok(local_fallback(&mode));
    }

    let url = format!(
        "{}/api/v1/harness/capability/negotiate?platform=desktop&mode={}",
        backend_url.trim_end_matches('/'),
        mode
    );

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| format!("HTTP client build failed: {}", e))?;

    let mut req = client.get(&url);
    if let Some(t) = token {
        req = req.bearer_auth(t);
    }

    match req.send().await {
        Ok(resp) if resp.status().is_success() => match resp.json::<serde_json::Value>().await {
            Ok(json) => {
                let data = json
                    .get("data")
                    .cloned()
                    .unwrap_or(serde_json::Value::Null);
                let mut result: NegotiationResult = match serde_json::from_value(data) {
                    Ok(r) => r,
                    Err(e) => {
                        log::warn!("[Capability] 后端响应解析失败 ({}), 降级本地表", e);
                        return Ok(local_fallback(&mode));
                    }
                };
                result.source = "cloud".to_string();
                Ok(result)
            }
            Err(e) => {
                log::warn!("[Capability] 响应 JSON 解码失败 ({}), 降级本地表", e);
                Ok(local_fallback(&mode))
            }
        },
        Ok(resp) => {
            log::warn!(
                "[Capability] 后端返回 {} (mode={}), 降级本地表",
                resp.status(),
                mode
            );
            Ok(local_fallback(&mode))
        }
        Err(e) => {
            log::warn!("[Capability] 后端不可达 ({}), 降级本地表", e);
            Ok(local_fallback(&mode))
        }
    }
}
