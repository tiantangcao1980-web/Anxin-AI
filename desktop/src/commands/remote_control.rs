use crate::commands::privacy_guard::ensure_data_network_allowed;
use crate::models::SharedAppState;
use crate::services::remote_control_host;
use serde_json::Value;
use tauri::{command, State};

#[command]
pub async fn remote_control_confirm_pairing(
    state: State<'_, SharedAppState>,
    pairing_id: String,
    desktop_device_id: String,
) -> Result<Value, String> {
    ensure_data_network_allowed(state.inner(), "确认移动远控配对").await?;
    let (backend_url, user_token) = remote_control_context(state.inner()).await?;
    let payload = remote_control_host::build_confirm_pairing_payload(&desktop_device_id)?;
    let client = remote_control_host::build_http_client()?;

    remote_control_host::post_remote_control_json(
        &client,
        &backend_url,
        &user_token,
        &format!(
            "pairings/{}/confirm",
            required_arg(&pairing_id, "pairing_id")?
        ),
        &payload,
    )
    .await
}

#[command]
pub async fn remote_control_claim_commands(
    state: State<'_, SharedAppState>,
    desktop_device_id: String,
    pairing_id: String,
    route_token: String,
    host_instance_id: String,
    limit: Option<u8>,
) -> Result<Value, String> {
    ensure_data_network_allowed(state.inner(), "领取移动远控命令").await?;
    let (backend_url, user_token) = remote_control_context(state.inner()).await?;
    let payload = remote_control_host::build_claim_commands_payload(
        &desktop_device_id,
        &pairing_id,
        &route_token,
        &host_instance_id,
        limit,
    )?;
    let client = remote_control_host::build_http_client()?;

    remote_control_host::post_remote_control_json(
        &client,
        &backend_url,
        &user_token,
        "commands/claim",
        &payload,
    )
    .await
}

#[command]
#[allow(clippy::too_many_arguments)]
pub async fn remote_control_report_command_status(
    state: State<'_, SharedAppState>,
    command_id: String,
    desktop_device_id: String,
    pairing_id: String,
    route_token: String,
    host_instance_id: String,
    status: String,
    result_summary: Option<Value>,
    failure_reason: Option<String>,
) -> Result<Value, String> {
    ensure_data_network_allowed(state.inner(), "回传移动远控命令状态").await?;
    let (backend_url, user_token) = remote_control_context(state.inner()).await?;
    let payload = remote_control_host::build_command_status_payload(
        &desktop_device_id,
        &pairing_id,
        &route_token,
        &host_instance_id,
        &status,
        result_summary,
        failure_reason,
    )?;
    let client = remote_control_host::build_http_client()?;

    remote_control_host::post_remote_control_json(
        &client,
        &backend_url,
        &user_token,
        &format!(
            "commands/{}/status",
            required_arg(&command_id, "command_id")?
        ),
        &payload,
    )
    .await
}

#[command]
pub async fn remote_control_run_host_cycle(
    state: State<'_, SharedAppState>,
    desktop_device_id: String,
    pairing_id: String,
    route_token: String,
    host_instance_id: String,
    limit: Option<u8>,
) -> Result<remote_control_host::RemoteControlHostCycleSummary, String> {
    ensure_data_network_allowed(state.inner(), "运行移动远控 host 单次循环").await?;
    let (backend_url, user_token) = remote_control_context(state.inner()).await?;
    let client = remote_control_host::build_http_client()?;

    remote_control_host::run_remote_control_host_cycle(
        &client,
        &backend_url,
        &user_token,
        &desktop_device_id,
        &pairing_id,
        &route_token,
        &host_instance_id,
        limit,
    )
    .await
}

#[command]
#[allow(clippy::too_many_arguments)]
pub async fn remote_control_run_host_poll(
    state: State<'_, SharedAppState>,
    desktop_device_id: String,
    pairing_id: String,
    route_token: String,
    host_instance_id: String,
    interval_seconds: Option<u64>,
    max_cycles: Option<u16>,
    limit: Option<u8>,
) -> Result<remote_control_host::RemoteControlHostPollSummary, String> {
    ensure_data_network_allowed(state.inner(), "运行移动远控 host 受限轮询").await?;
    let config = remote_control_host::build_host_poll_config(interval_seconds, max_cycles, limit)?;
    let (backend_url, user_token) = remote_control_context(state.inner()).await?;
    let client = remote_control_host::build_http_client()?;

    remote_control_host::run_remote_control_host_poll(
        &client,
        &backend_url,
        &user_token,
        &desktop_device_id,
        &pairing_id,
        &route_token,
        &host_instance_id,
        config,
    )
    .await
}

async fn remote_control_context(state: &SharedAppState) -> Result<(String, String), String> {
    let s = state.read().await;
    let user_token = s
        .user_token
        .as_deref()
        .map(str::trim)
        .filter(|token| !token.is_empty())
        .ok_or_else(|| "请先登录后再使用移动远控桌面 host 能力".to_string())?;

    Ok((
        s.backend_url.trim_end_matches('/').to_string(),
        user_token.to_string(),
    ))
}

fn required_arg(value: &str, field_name: &str) -> Result<String, String> {
    let normalized = value.trim();
    if normalized.is_empty() {
        return Err(format!("{field_name} 不能为空"));
    }
    Ok(normalized.to_string())
}
