use crate::models::{AppMode, SharedAppState};
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};

const EXECUTION_UPDATE_STATUSES: [&str; 3] = ["running", "completed", "failed"];
const SAFE_PROBE_COMMAND_TYPES: [&str; 4] = [
    "ping",
    "status_probe",
    "desktop.ping",
    "desktop.status_probe",
];
const DEFAULT_POLL_INTERVAL_SECONDS: u64 = 10;
const MIN_POLL_INTERVAL_SECONDS: u64 = 5;
const MAX_POLL_INTERVAL_SECONDS: u64 = 300;
const DEFAULT_POLL_CYCLES: u16 = 12;
const MAX_POLL_CYCLES: u16 = 120;
const HOST_DAEMON_ENABLED_ENV: &str = "ANXIN_DESKTOP_REMOTE_CONTROL_HOST_DAEMON";
const HOST_DAEMON_DESKTOP_DEVICE_ID_ENV: &str = "ANXIN_REMOTE_CONTROL_DESKTOP_DEVICE_ID";
const HOST_DAEMON_PAIRING_ID_ENV: &str = "ANXIN_REMOTE_CONTROL_PAIRING_ID";
const HOST_DAEMON_ROUTE_TOKEN_ENV: &str = "ANXIN_REMOTE_CONTROL_ROUTE_TOKEN";
const HOST_DAEMON_INSTANCE_ID_ENV: &str = "ANXIN_REMOTE_CONTROL_HOST_INSTANCE_ID";
const HOST_DAEMON_BEARER_TOKEN_ENV: &str = "ANXIN_REMOTE_CONTROL_BEARER_TOKEN";
const HOST_DAEMON_INTERVAL_SECONDS_ENV: &str = "ANXIN_REMOTE_CONTROL_HOST_POLL_INTERVAL_SECONDS";
const HOST_DAEMON_MAX_CYCLES_ENV: &str = "ANXIN_REMOTE_CONTROL_HOST_POLL_MAX_CYCLES";
const HOST_DAEMON_LIMIT_ENV: &str = "ANXIN_REMOTE_CONTROL_HOST_POLL_LIMIT";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RemoteControlHostCommand {
    pub command_id: String,
    pub command_type: String,
    pub payload_keys: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RemoteControlHostCommandDecision {
    pub status: &'static str,
    pub result_summary: Value,
    pub failure_reason: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct RemoteControlHostCycleSummary {
    pub claimed: usize,
    pub completed: usize,
    pub failed: usize,
    pub unsupported: usize,
    pub command_ids: Vec<String>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub struct RemoteControlHostPollConfig {
    pub interval_seconds: u64,
    pub max_cycles: u16,
    pub limit: u8,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct RemoteControlHostPollSummary {
    pub cycles: u16,
    pub claimed: usize,
    pub completed: usize,
    pub failed: usize,
    pub unsupported: usize,
    pub command_ids: Vec<String>,
    pub stopped_reason: String,
}

#[derive(Clone, PartialEq, Eq)]
pub struct RemoteControlHostDaemonConfig {
    pub desktop_device_id: String,
    pub pairing_id: String,
    pub route_token: String,
    pub host_instance_id: String,
    pub bearer_token_override: Option<String>,
    pub poll_config: RemoteControlHostPollConfig,
}

pub fn build_http_client() -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|err| format!("无法初始化远控 host HTTP 客户端: {err}"))
}

pub fn remote_control_url(backend_url: &str, path: &str) -> String {
    format!(
        "{}/api/v1/sync/remote-control/{}",
        backend_url.trim_end_matches('/'),
        path.trim_start_matches('/')
    )
}

pub fn build_confirm_pairing_payload(desktop_device_id: &str) -> Result<Value, String> {
    Ok(json!({
        "desktop_device_id": required_string(desktop_device_id, "desktop_device_id")?,
    }))
}

pub fn build_claim_commands_payload(
    desktop_device_id: &str,
    pairing_id: &str,
    route_token: &str,
    host_instance_id: &str,
    limit: Option<u8>,
) -> Result<Value, String> {
    Ok(json!({
        "desktop_device_id": required_string(desktop_device_id, "desktop_device_id")?,
        "pairing_id": required_string(pairing_id, "pairing_id")?,
        "route_token": required_string(route_token, "route_token")?,
        "host_instance_id": required_string(host_instance_id, "host_instance_id")?,
        "limit": normalize_claim_limit(limit)?,
    }))
}

pub fn build_command_status_payload(
    desktop_device_id: &str,
    pairing_id: &str,
    route_token: &str,
    host_instance_id: &str,
    status: &str,
    result_summary: Option<Value>,
    failure_reason: Option<String>,
) -> Result<Value, String> {
    let status = normalize_execution_status(status)?;
    let result_summary = normalize_result_summary(result_summary)?;
    Ok(json!({
        "desktop_device_id": required_string(desktop_device_id, "desktop_device_id")?,
        "pairing_id": required_string(pairing_id, "pairing_id")?,
        "route_token": required_string(route_token, "route_token")?,
        "host_instance_id": required_string(host_instance_id, "host_instance_id")?,
        "status": status,
        "result_summary": result_summary,
        "failure_reason": failure_reason
            .map(|reason| reason.trim().to_string())
            .filter(|reason| !reason.is_empty()),
    }))
}

pub async fn post_remote_control_json(
    client: &reqwest::Client,
    backend_url: &str,
    bearer_token: &str,
    path: &str,
    payload: &Value,
) -> Result<Value, String> {
    let bearer_token = required_string(bearer_token, "user_token")?;
    let response = client
        .post(remote_control_url(backend_url, path))
        .bearer_auth(bearer_token)
        .header("Content-Type", "application/json")
        .json(payload)
        .send()
        .await
        .map_err(|err| format!("远控 host API 请求失败: {err}"))?;

    let status = response.status();
    if !status.is_success() {
        let text = response.text().await.unwrap_or_default();
        return Err(format!("远控 host API HTTP {}: {}", status.as_u16(), text));
    }

    response
        .json::<Value>()
        .await
        .map_err(|err| format!("解析远控 host API 响应失败: {err}"))
}

#[allow(clippy::too_many_arguments)]
pub async fn run_remote_control_host_cycle(
    client: &reqwest::Client,
    backend_url: &str,
    bearer_token: &str,
    desktop_device_id: &str,
    pairing_id: &str,
    route_token: &str,
    host_instance_id: &str,
    limit: Option<u8>,
) -> Result<RemoteControlHostCycleSummary, String> {
    let claim_payload = build_claim_commands_payload(
        desktop_device_id,
        pairing_id,
        route_token,
        host_instance_id,
        limit,
    )?;
    let claim_response = post_remote_control_json(
        client,
        backend_url,
        bearer_token,
        "commands/claim",
        &claim_payload,
    )
    .await?;
    let commands = claimed_commands_from_response(&claim_response)?;
    let mut summary = RemoteControlHostCycleSummary {
        claimed: commands.len(),
        ..RemoteControlHostCycleSummary::default()
    };

    for command in commands {
        summary.command_ids.push(command.command_id.clone());
        let running_payload = build_command_status_payload(
            desktop_device_id,
            pairing_id,
            route_token,
            host_instance_id,
            "running",
            Some(json!({
                "handled_by": "desktop_remote_control_host",
                "phase": "started",
                "command_type": command.command_type,
            })),
            None,
        )?;
        post_remote_control_json(
            client,
            backend_url,
            bearer_token,
            &format!("commands/{}/status", command.command_id),
            &running_payload,
        )
        .await?;

        let decision = decide_host_command(&command);
        let final_payload = build_command_status_payload(
            desktop_device_id,
            pairing_id,
            route_token,
            host_instance_id,
            decision.status,
            Some(decision.result_summary),
            decision.failure_reason.clone(),
        )?;
        post_remote_control_json(
            client,
            backend_url,
            bearer_token,
            &format!("commands/{}/status", command.command_id),
            &final_payload,
        )
        .await?;

        match decision.status {
            "completed" => summary.completed += 1,
            "failed" => {
                summary.failed += 1;
                if decision.failure_reason.as_deref() == Some("unsupported_command_type") {
                    summary.unsupported += 1;
                }
            }
            _ => {}
        }
    }

    Ok(summary)
}

pub fn build_host_poll_config(
    interval_seconds: Option<u64>,
    max_cycles: Option<u16>,
    limit: Option<u8>,
) -> Result<RemoteControlHostPollConfig, String> {
    let interval_seconds = interval_seconds.unwrap_or(DEFAULT_POLL_INTERVAL_SECONDS);
    if !(MIN_POLL_INTERVAL_SECONDS..=MAX_POLL_INTERVAL_SECONDS).contains(&interval_seconds) {
        return Err(format!(
            "远控 host 轮询间隔必须在 {MIN_POLL_INTERVAL_SECONDS} 到 {MAX_POLL_INTERVAL_SECONDS} 秒之间"
        ));
    }

    let max_cycles = max_cycles.unwrap_or(DEFAULT_POLL_CYCLES);
    if max_cycles == 0 || max_cycles > MAX_POLL_CYCLES {
        return Err(format!(
            "远控 host 轮询次数必须在 1 到 {MAX_POLL_CYCLES} 之间"
        ));
    }

    Ok(RemoteControlHostPollConfig {
        interval_seconds,
        max_cycles,
        limit: normalize_claim_limit(limit)?,
    })
}

#[allow(clippy::too_many_arguments)]
pub fn build_host_daemon_config(
    enabled: bool,
    desktop_device_id: Option<&str>,
    pairing_id: Option<&str>,
    route_token: Option<&str>,
    host_instance_id: Option<&str>,
    bearer_token_override: Option<&str>,
    interval_seconds: Option<u64>,
    max_cycles: Option<u16>,
    limit: Option<u8>,
) -> Result<Option<RemoteControlHostDaemonConfig>, String> {
    if !enabled {
        return Ok(None);
    }

    let mut missing = Vec::new();
    let desktop_device_id =
        required_optional_string(desktop_device_id, "desktop_device_id", &mut missing);
    let pairing_id = required_optional_string(pairing_id, "pairing_id", &mut missing);
    let route_token = required_optional_string(route_token, "route_token", &mut missing);
    let host_instance_id =
        required_optional_string(host_instance_id, "host_instance_id", &mut missing);

    if !missing.is_empty() {
        return Err(format!(
            "远控 host 后台 safe-probe daemon 缺少配置: {}",
            missing.join(", ")
        ));
    }

    Ok(Some(RemoteControlHostDaemonConfig {
        desktop_device_id: desktop_device_id.expect("missing checked"),
        pairing_id: pairing_id.expect("missing checked"),
        route_token: route_token.expect("missing checked"),
        host_instance_id: host_instance_id.expect("missing checked"),
        bearer_token_override: normalize_optional_string(bearer_token_override),
        poll_config: build_host_poll_config(interval_seconds, max_cycles, limit)?,
    }))
}

pub fn build_host_daemon_config_from_env() -> Result<Option<RemoteControlHostDaemonConfig>, String>
{
    let enabled_raw = optional_env(HOST_DAEMON_ENABLED_ENV);
    let enabled = parse_daemon_enabled(enabled_raw.as_deref())?;
    let desktop_device_id = optional_env(HOST_DAEMON_DESKTOP_DEVICE_ID_ENV);
    let pairing_id = optional_env(HOST_DAEMON_PAIRING_ID_ENV);
    let route_token = optional_env(HOST_DAEMON_ROUTE_TOKEN_ENV);
    let host_instance_id = optional_env(HOST_DAEMON_INSTANCE_ID_ENV);
    let bearer_token = optional_env(HOST_DAEMON_BEARER_TOKEN_ENV);

    build_host_daemon_config(
        enabled,
        desktop_device_id.as_deref(),
        pairing_id.as_deref(),
        route_token.as_deref(),
        host_instance_id.as_deref(),
        bearer_token.as_deref(),
        parse_optional_u64_env(HOST_DAEMON_INTERVAL_SECONDS_ENV)?,
        parse_optional_u16_env(HOST_DAEMON_MAX_CYCLES_ENV)?,
        parse_optional_u8_env(HOST_DAEMON_LIMIT_ENV)?,
    )
}

#[allow(clippy::too_many_arguments)]
pub async fn run_remote_control_host_poll(
    client: &reqwest::Client,
    backend_url: &str,
    bearer_token: &str,
    desktop_device_id: &str,
    pairing_id: &str,
    route_token: &str,
    host_instance_id: &str,
    config: RemoteControlHostPollConfig,
) -> Result<RemoteControlHostPollSummary, String> {
    let mut summary = RemoteControlHostPollSummary {
        stopped_reason: "max_cycles_reached".to_string(),
        ..RemoteControlHostPollSummary::default()
    };

    for cycle_index in 0..config.max_cycles {
        let cycle = run_remote_control_host_cycle(
            client,
            backend_url,
            bearer_token,
            desktop_device_id,
            pairing_id,
            route_token,
            host_instance_id,
            Some(config.limit),
        )
        .await?;
        record_poll_cycle(&mut summary, cycle);

        if cycle_index + 1 < config.max_cycles {
            tokio::time::sleep(std::time::Duration::from_secs(config.interval_seconds)).await;
        }
    }

    Ok(summary)
}

pub async fn run_remote_control_host_daemon(
    client: &reqwest::Client,
    state: &SharedAppState,
    config: &RemoteControlHostDaemonConfig,
) -> Result<RemoteControlHostPollSummary, String> {
    let (mode, backend_url, state_user_token) = {
        let state = state.read().await;
        (
            state.mode,
            state.backend_url.clone(),
            state.user_token.clone(),
        )
    };

    if mode == AppMode::TopSecret {
        return Err("绝密模式下禁止启动移动远控 host 后台 safe-probe daemon".to_string());
    }

    let bearer_token = config
        .bearer_token_override
        .as_deref()
        .or(state_user_token.as_deref())
        .map(str::trim)
        .filter(|token| !token.is_empty())
        .ok_or_else(|| {
            "移动远控 host 后台 safe-probe daemon 需要登录态 token 或本地测试 bearer token"
                .to_string()
        })?;

    run_remote_control_host_poll(
        client,
        &backend_url,
        bearer_token,
        &config.desktop_device_id,
        &config.pairing_id,
        &config.route_token,
        &config.host_instance_id,
        config.poll_config,
    )
    .await
}

pub fn record_poll_cycle(
    summary: &mut RemoteControlHostPollSummary,
    cycle: RemoteControlHostCycleSummary,
) {
    summary.cycles += 1;
    summary.claimed += cycle.claimed;
    summary.completed += cycle.completed;
    summary.failed += cycle.failed;
    summary.unsupported += cycle.unsupported;
    summary.command_ids.extend(cycle.command_ids);
}

pub fn claimed_commands_from_response(
    response: &Value,
) -> Result<Vec<RemoteControlHostCommand>, String> {
    let items = response
        .get("items")
        .and_then(Value::as_array)
        .ok_or_else(|| "远控 host claim 响应缺少 items 数组".to_string())?;

    items
        .iter()
        .map(|item| {
            let command_id = item
                .get("command_id")
                .and_then(Value::as_str)
                .map(str::trim)
                .filter(|value| !value.is_empty())
                .ok_or_else(|| "远控 host claim 响应缺少 command_id".to_string())?;
            let command_type = item
                .get("command_type")
                .and_then(Value::as_str)
                .map(str::trim)
                .filter(|value| !value.is_empty())
                .ok_or_else(|| "远控 host claim 响应缺少 command_type".to_string())?;
            let payload_keys = item
                .get("payload")
                .and_then(Value::as_object)
                .map(|payload| {
                    let mut keys = payload.keys().cloned().collect::<Vec<_>>();
                    keys.sort();
                    keys
                })
                .unwrap_or_default();

            Ok(RemoteControlHostCommand {
                command_id: command_id.to_string(),
                command_type: command_type.to_string(),
                payload_keys,
            })
        })
        .collect()
}

pub fn decide_host_command(command: &RemoteControlHostCommand) -> RemoteControlHostCommandDecision {
    let command_type = command.command_type.trim().to_ascii_lowercase();
    if SAFE_PROBE_COMMAND_TYPES.contains(&command_type.as_str()) {
        return RemoteControlHostCommandDecision {
            status: "completed",
            result_summary: json!({
                "handled_by": "desktop_remote_control_host",
                "command_type": command.command_type,
                "safe_probe": true,
                "payload_keys": &command.payload_keys,
            }),
            failure_reason: None,
        };
    }

    RemoteControlHostCommandDecision {
        status: "failed",
        result_summary: json!({
            "handled_by": "desktop_remote_control_host",
            "received_command_type": command.command_type,
            "payload_keys": &command.payload_keys,
            "supported_command_types": SAFE_PROBE_COMMAND_TYPES,
        }),
        failure_reason: Some("unsupported_command_type".to_string()),
    }
}

fn required_string(value: &str, field_name: &str) -> Result<String, String> {
    let normalized = value.trim();
    if normalized.is_empty() {
        return Err(format!("{field_name} 不能为空"));
    }
    Ok(normalized.to_string())
}

fn required_optional_string(
    value: Option<&str>,
    field_name: &'static str,
    missing: &mut Vec<&'static str>,
) -> Option<String> {
    match value.and_then(|value| normalize_optional_string(Some(value))) {
        Some(value) => Some(value),
        None => {
            missing.push(field_name);
            None
        }
    }
}

fn normalize_optional_string(value: Option<&str>) -> Option<String> {
    value
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string)
}

fn optional_env(name: &str) -> Option<String> {
    std::env::var(name)
        .ok()
        .and_then(|value| normalize_optional_string(Some(&value)))
}

fn parse_daemon_enabled(value: Option<&str>) -> Result<bool, String> {
    let Some(value) = value else {
        return Ok(false);
    };
    match value.trim().to_ascii_lowercase().as_str() {
        "" | "0" | "false" | "no" | "off" => Ok(false),
        "1" | "true" | "yes" | "on" => Ok(true),
        _ => Err(format!(
            "{HOST_DAEMON_ENABLED_ENV} 只能是 true/false、1/0、yes/no 或 on/off"
        )),
    }
}

fn parse_optional_u64_env(name: &str) -> Result<Option<u64>, String> {
    optional_env(name)
        .map(|value| {
            value
                .parse::<u64>()
                .map_err(|_| format!("{name} 必须是正整数秒数"))
        })
        .transpose()
}

fn parse_optional_u16_env(name: &str) -> Result<Option<u16>, String> {
    optional_env(name)
        .map(|value| {
            value
                .parse::<u16>()
                .map_err(|_| format!("{name} 必须是 1 到 {MAX_POLL_CYCLES} 之间的整数"))
        })
        .transpose()
}

fn parse_optional_u8_env(name: &str) -> Result<Option<u8>, String> {
    optional_env(name)
        .map(|value| {
            value
                .parse::<u8>()
                .map_err(|_| format!("{name} 必须是 1 到 50 之间的整数"))
        })
        .transpose()
}

fn normalize_claim_limit(limit: Option<u8>) -> Result<u8, String> {
    let limit = limit.unwrap_or(10);
    if (1..=50).contains(&limit) {
        return Ok(limit);
    }
    Err("远控 host 每次领取命令数量必须在 1 到 50 之间".to_string())
}

fn normalize_execution_status(status: &str) -> Result<String, String> {
    let normalized = status.trim().to_ascii_lowercase();
    if EXECUTION_UPDATE_STATUSES.contains(&normalized.as_str()) {
        return Ok(normalized);
    }
    Err("远控命令状态只能是 running、completed 或 failed".to_string())
}

fn normalize_result_summary(value: Option<Value>) -> Result<Map<String, Value>, String> {
    match value {
        None => Ok(Map::new()),
        Some(Value::Object(map)) => Ok(map),
        Some(_) => Err("远控命令结果摘要必须是 JSON object".to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::{
        build_claim_commands_payload, build_command_status_payload, build_confirm_pairing_payload,
        build_host_daemon_config, build_host_poll_config, claimed_commands_from_response,
        decide_host_command, parse_daemon_enabled, record_poll_cycle, remote_control_url,
        run_remote_control_host_daemon, RemoteControlHostCommand, RemoteControlHostCycleSummary,
        RemoteControlHostPollSummary,
    };
    use crate::models::{AppMode, AppStateData};
    use serde_json::json;
    use std::sync::Arc;
    use tokio::sync::RwLock;

    #[test]
    fn remote_control_url_trims_backend_and_path_slashes() {
        assert_eq!(
            remote_control_url("http://localhost:8001/", "/commands/claim"),
            "http://localhost:8001/api/v1/sync/remote-control/commands/claim"
        );
    }

    #[test]
    fn confirm_pairing_payload_requires_desktop_device_id() {
        let payload = build_confirm_pairing_payload(" desktop-a ").expect("confirm payload");

        assert_eq!(payload["desktop_device_id"], "desktop-a");
        assert!(build_confirm_pairing_payload(" ").is_err());
    }

    #[test]
    fn claim_commands_payload_uses_default_limit_and_required_route_token() {
        let payload =
            build_claim_commands_payload("desktop-a", "pairing-1", "route-token", "host-a", None)
                .expect("claim payload");

        assert_eq!(payload["desktop_device_id"], "desktop-a");
        assert_eq!(payload["pairing_id"], "pairing-1");
        assert_eq!(payload["route_token"], "route-token");
        assert_eq!(payload["host_instance_id"], "host-a");
        assert_eq!(payload["limit"], 10);
        assert!(
            build_claim_commands_payload("desktop-a", "pairing-1", "", "host-a", Some(1)).is_err()
        );
        assert!(build_claim_commands_payload(
            "desktop-a",
            "pairing-1",
            "route-token",
            "host-a",
            Some(0)
        )
        .is_err());
    }

    #[test]
    fn command_status_payload_normalizes_status_and_rejects_non_object_summary() {
        let payload = build_command_status_payload(
            "desktop-a",
            "pairing-1",
            "route-token",
            "host-a",
            " COMPLETED ",
            Some(json!({"ok": true, "token": "backend-redacts-recursively"})),
            Some(" done ".to_string()),
        )
        .expect("status payload");

        assert_eq!(payload["status"], "completed");
        assert_eq!(payload["failure_reason"], "done");
        assert_eq!(payload["result_summary"]["ok"], true);
        assert!(build_command_status_payload(
            "desktop-a",
            "pairing-1",
            "route-token",
            "host-a",
            "queued",
            None,
            None,
        )
        .is_err());
        assert!(build_command_status_payload(
            "desktop-a",
            "pairing-1",
            "route-token",
            "host-a",
            "failed",
            Some(json!("not-object")),
            None,
        )
        .is_err());
    }

    #[test]
    fn claimed_commands_from_response_requires_items_and_command_fields() {
        let response = json!({
            "items": [
                {
                    "command_id": "cmd-1",
                    "command_type": "desktop.status_probe",
                    "payload": {"b": true, "a": 1}
                }
            ]
        });

        let commands = claimed_commands_from_response(&response).expect("claimed commands");

        assert_eq!(commands.len(), 1);
        assert_eq!(commands[0].command_id, "cmd-1");
        assert_eq!(commands[0].command_type, "desktop.status_probe");
        assert_eq!(commands[0].payload_keys, vec!["a", "b"]);
        assert!(
            claimed_commands_from_response(&json!({"items": [{"command_id": "cmd-1"}]})).is_err()
        );
        assert!(claimed_commands_from_response(&json!({})).is_err());
    }

    #[test]
    fn decide_host_command_only_completes_safe_probe_commands() {
        let safe = RemoteControlHostCommand {
            command_id: "cmd-1".to_string(),
            command_type: "desktop.status_probe".to_string(),
            payload_keys: vec!["mode".to_string()],
        };
        let risky = RemoteControlHostCommand {
            command_id: "cmd-2".to_string(),
            command_type: "open_file".to_string(),
            payload_keys: vec!["path".to_string()],
        };

        let safe_decision = decide_host_command(&safe);
        let risky_decision = decide_host_command(&risky);

        assert_eq!(safe_decision.status, "completed");
        assert!(safe_decision.failure_reason.is_none());
        assert_eq!(safe_decision.result_summary["safe_probe"], true);
        assert_eq!(risky_decision.status, "failed");
        assert_eq!(
            risky_decision.failure_reason.as_deref(),
            Some("unsupported_command_type")
        );
        assert_eq!(
            risky_decision.result_summary["received_command_type"],
            "open_file"
        );
    }

    #[test]
    fn host_poll_config_is_bounded_and_reuses_claim_limit_rules() {
        let default_config = build_host_poll_config(None, None, None).expect("default poll config");

        assert_eq!(default_config.interval_seconds, 10);
        assert_eq!(default_config.max_cycles, 12);
        assert_eq!(default_config.limit, 10);

        let custom_config =
            build_host_poll_config(Some(30), Some(3), Some(2)).expect("custom poll config");
        assert_eq!(custom_config.interval_seconds, 30);
        assert_eq!(custom_config.max_cycles, 3);
        assert_eq!(custom_config.limit, 2);

        assert!(build_host_poll_config(Some(1), Some(3), Some(2)).is_err());
        assert!(build_host_poll_config(Some(30), Some(0), Some(2)).is_err());
        assert!(build_host_poll_config(Some(30), Some(3), Some(0)).is_err());
    }

    #[test]
    fn host_daemon_enabled_flag_is_explicit() {
        assert!(!parse_daemon_enabled(None).expect("unset flag"));
        assert!(parse_daemon_enabled(Some("on")).expect("on flag"));
        assert!(parse_daemon_enabled(Some(" 1 ")).expect("numeric flag"));
        assert!(!parse_daemon_enabled(Some("false")).expect("false flag"));
        assert!(parse_daemon_enabled(Some("maybe")).is_err());
    }

    #[test]
    fn host_daemon_config_is_disabled_by_default_and_requires_pairing_scope() {
        let disabled = build_host_daemon_config(
            false,
            None,
            None,
            None,
            None,
            Some("bearer-token"),
            Some(5),
            Some(1),
            Some(1),
        )
        .expect("disabled config");
        assert!(disabled.is_none());

        let err = match build_host_daemon_config(
            true,
            Some("desktop-a"),
            None,
            Some("route-secret"),
            Some("host-a"),
            None,
            Some(5),
            Some(1),
            Some(1),
        ) {
            Ok(_) => panic!("missing pairing id must fail"),
            Err(err) => err,
        };

        assert!(err.contains("pairing_id"));
        assert!(!err.contains("route-secret"));
    }

    #[test]
    fn host_daemon_config_trims_secrets_and_keeps_poll_bounds() {
        let config = build_host_daemon_config(
            true,
            Some(" desktop-a "),
            Some(" pairing-1 "),
            Some(" route-secret "),
            Some(" host-a "),
            Some(" bearer-secret "),
            Some(30),
            Some(2),
            Some(3),
        )
        .expect("daemon config")
        .expect("enabled daemon config");

        assert_eq!(config.desktop_device_id, "desktop-a");
        assert_eq!(config.pairing_id, "pairing-1");
        assert_eq!(config.route_token, "route-secret");
        assert_eq!(config.host_instance_id, "host-a");
        assert_eq!(
            config.bearer_token_override.as_deref(),
            Some("bearer-secret")
        );
        assert_eq!(config.poll_config.interval_seconds, 30);
        assert_eq!(config.poll_config.max_cycles, 2);
        assert_eq!(config.poll_config.limit, 3);
        assert!(build_host_daemon_config(
            true,
            Some("desktop-a"),
            Some("pairing-1"),
            Some("route-secret"),
            Some("host-a"),
            None,
            Some(1),
            Some(1),
            Some(1),
        )
        .is_err());
    }

    #[tokio::test]
    async fn host_daemon_rejects_top_secret_mode_before_network() {
        let state = Arc::new(RwLock::new(AppStateData {
            mode: AppMode::TopSecret,
            user_token: Some("state-token".to_string()),
            ..AppStateData::default()
        }));
        let config = build_host_daemon_config(
            true,
            Some("desktop-a"),
            Some("pairing-1"),
            Some("route-secret"),
            Some("host-a"),
            None,
            Some(5),
            Some(1),
            Some(1),
        )
        .expect("daemon config")
        .expect("enabled daemon config");
        let client = super::build_http_client().expect("http client");

        let err = run_remote_control_host_daemon(&client, &state, &config)
            .await
            .expect_err("top secret mode must block daemon before HTTP");

        assert!(err.contains("绝密模式"));
        assert!(!err.contains("route-secret"));
    }

    #[tokio::test]
    async fn host_daemon_requires_login_or_test_bearer_before_network() {
        let state = Arc::new(RwLock::new(AppStateData {
            mode: AppMode::Cloud,
            user_token: None,
            ..AppStateData::default()
        }));
        let config = build_host_daemon_config(
            true,
            Some("desktop-a"),
            Some("pairing-1"),
            Some("route-secret"),
            Some("host-a"),
            None,
            Some(5),
            Some(1),
            Some(1),
        )
        .expect("daemon config")
        .expect("enabled daemon config");
        let client = super::build_http_client().expect("http client");

        let err = run_remote_control_host_daemon(&client, &state, &config)
            .await
            .expect_err("missing bearer must block daemon before HTTP");

        assert!(err.contains("登录态 token"));
        assert!(!err.contains("route-secret"));
    }

    #[test]
    fn record_poll_cycle_accumulates_counts_without_payloads() {
        let mut summary = RemoteControlHostPollSummary {
            stopped_reason: "max_cycles_reached".to_string(),
            ..RemoteControlHostPollSummary::default()
        };

        record_poll_cycle(
            &mut summary,
            RemoteControlHostCycleSummary {
                claimed: 2,
                completed: 1,
                failed: 1,
                unsupported: 1,
                command_ids: vec!["cmd-a".to_string(), "cmd-b".to_string()],
            },
        );
        record_poll_cycle(
            &mut summary,
            RemoteControlHostCycleSummary {
                claimed: 1,
                completed: 1,
                failed: 0,
                unsupported: 0,
                command_ids: vec!["cmd-c".to_string()],
            },
        );

        assert_eq!(summary.cycles, 2);
        assert_eq!(summary.claimed, 3);
        assert_eq!(summary.completed, 2);
        assert_eq!(summary.failed, 1);
        assert_eq!(summary.unsupported, 1);
        assert_eq!(summary.command_ids, vec!["cmd-a", "cmd-b", "cmd-c"]);
        assert_eq!(summary.stopped_reason, "max_cycles_reached");
    }
}
