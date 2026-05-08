use serde_json::{json, Map, Value};

const EXECUTION_UPDATE_STATUSES: [&str; 3] = ["running", "completed", "failed"];

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

fn required_string(value: &str, field_name: &str) -> Result<String, String> {
    let normalized = value.trim();
    if normalized.is_empty() {
        return Err(format!("{field_name} 不能为空"));
    }
    Ok(normalized.to_string())
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
        remote_control_url,
    };
    use serde_json::json;

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
}
