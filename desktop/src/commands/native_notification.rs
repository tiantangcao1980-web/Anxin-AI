use crate::models::{AppMode, SharedAppState};
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, State};
use tauri_plugin_notification::NotificationExt;

const MAX_NOTIFICATION_TITLE_CHARS: usize = 80;
const MAX_NOTIFICATION_BODY_CHARS: usize = 180;
const MAX_RELATED_ID_CHARS: usize = 120;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DesktopNotificationKind {
    CaseProgress,
    RiskAlert,
    System,
    Sync,
}

impl DesktopNotificationKind {
    fn group(self) -> &'static str {
        match self {
            Self::CaseProgress => "case-progress",
            Self::RiskAlert => "risk-alert",
            Self::System => "system",
            Self::Sync => "sync",
        }
    }

    fn sent_message(self) -> &'static str {
        match self {
            Self::CaseProgress => "案件进展本机通知已发送",
            Self::RiskAlert => "风险预警本机通知已发送",
            Self::System => "系统本机通知已发送",
            Self::Sync => "同步状态本机通知已发送",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopNotificationPayload {
    pub kind: DesktopNotificationKind,
    pub title: String,
    pub body: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub related_id: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopNotificationPreview {
    pub kind: DesktopNotificationKind,
    pub title: String,
    pub body: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub related_id: Option<String>,
    pub local_only: bool,
    pub safe_in_top_secret: bool,
    pub requires_external_push: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopNotificationResponse {
    pub success: bool,
    pub kind: DesktopNotificationKind,
    pub title: String,
    pub body: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub related_id: Option<String>,
    pub local_only: bool,
    pub safe_in_top_secret: bool,
    pub privacy_mode: AppMode,
    pub message: String,
}

fn truncate_chars(value: &str, max_chars: usize) -> String {
    if value.chars().count() <= max_chars {
        return value.to_string();
    }

    let keep = max_chars.saturating_sub(3);
    let mut truncated = value.chars().take(keep).collect::<String>();
    truncated.push_str("...");
    truncated
}

fn normalize_notification_text(
    value: &str,
    field_label: &str,
    max_chars: usize,
) -> Result<String, String> {
    let normalized = value.split_whitespace().collect::<Vec<_>>().join(" ");
    if normalized.is_empty() {
        return Err(format!("{field_label}不能为空"));
    }
    Ok(truncate_chars(&normalized, max_chars))
}

fn normalize_related_id(value: Option<String>) -> Result<Option<String>, String> {
    let Some(value) = value else {
        return Ok(None);
    };
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return Ok(None);
    }
    if trimmed.chars().count() > MAX_RELATED_ID_CHARS {
        return Err(format!("关联 ID 不能超过 {MAX_RELATED_ID_CHARS} 个字符"));
    }
    if trimmed.chars().any(char::is_control) {
        return Err("关联 ID 不能包含控制字符".to_string());
    }
    Ok(Some(trimmed.to_string()))
}

pub fn build_desktop_notification_preview(
    payload: DesktopNotificationPayload,
) -> Result<DesktopNotificationPreview, String> {
    Ok(DesktopNotificationPreview {
        kind: payload.kind,
        title: normalize_notification_text(
            &payload.title,
            "通知标题",
            MAX_NOTIFICATION_TITLE_CHARS,
        )?,
        body: normalize_notification_text(&payload.body, "通知内容", MAX_NOTIFICATION_BODY_CHARS)?,
        related_id: normalize_related_id(payload.related_id)?,
        local_only: true,
        safe_in_top_secret: true,
        requires_external_push: false,
    })
}

fn response_from_preview(
    preview: DesktopNotificationPreview,
    privacy_mode: AppMode,
    message: String,
) -> DesktopNotificationResponse {
    DesktopNotificationResponse {
        success: true,
        kind: preview.kind,
        title: preview.title,
        body: preview.body,
        related_id: preview.related_id,
        local_only: preview.local_only,
        safe_in_top_secret: preview.safe_in_top_secret,
        privacy_mode,
        message,
    }
}

#[tauri::command]
pub async fn preview_desktop_notification(
    payload: DesktopNotificationPayload,
    state: State<'_, SharedAppState>,
) -> Result<DesktopNotificationResponse, String> {
    let privacy_mode = {
        let snapshot = state.read().await;
        snapshot.mode
    };
    let preview = build_desktop_notification_preview(payload)?;
    Ok(response_from_preview(
        preview,
        privacy_mode,
        "本机通知预览已生成".to_string(),
    ))
}

#[tauri::command]
pub async fn send_desktop_notification(
    payload: DesktopNotificationPayload,
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<DesktopNotificationResponse, String> {
    let privacy_mode = {
        let snapshot = state.read().await;
        snapshot.mode
    };
    let preview = build_desktop_notification_preview(payload)?;

    app.notification()
        .builder()
        .title(preview.title.clone())
        .body(preview.body.clone())
        .group(preview.kind.group())
        .show()
        .map_err(|err| format!("本机通知发送失败: {err}"))?;

    let message = preview.kind.sent_message().to_string();
    Ok(response_from_preview(preview, privacy_mode, message))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn payload(title: &str, body: &str) -> DesktopNotificationPayload {
        DesktopNotificationPayload {
            kind: DesktopNotificationKind::RiskAlert,
            title: title.to_string(),
            body: body.to_string(),
            related_id: Some(" case-2026-0001 ".to_string()),
        }
    }

    #[test]
    fn builds_local_only_preview_without_external_push() {
        let preview = build_desktop_notification_preview(payload(
            " 风险预警\n ",
            " 案件材料存在新风险。\n请及时处理。 ",
        ))
        .unwrap();

        assert_eq!(preview.kind, DesktopNotificationKind::RiskAlert);
        assert_eq!(preview.title, "风险预警");
        assert_eq!(preview.body, "案件材料存在新风险。 请及时处理。");
        assert_eq!(preview.related_id.as_deref(), Some("case-2026-0001"));
        assert!(preview.local_only);
        assert!(preview.safe_in_top_secret);
        assert!(!preview.requires_external_push);
    }

    #[test]
    fn rejects_empty_notification_copy() {
        assert!(build_desktop_notification_preview(payload("", "body")).is_err());
        assert!(build_desktop_notification_preview(payload("title", "   ")).is_err());
    }

    #[test]
    fn caps_long_title_and_body_for_os_surfaces() {
        let preview = build_desktop_notification_preview(payload(
            &"a".repeat(MAX_NOTIFICATION_TITLE_CHARS + 20),
            &"b".repeat(MAX_NOTIFICATION_BODY_CHARS + 20),
        ))
        .unwrap();

        assert_eq!(preview.title.chars().count(), MAX_NOTIFICATION_TITLE_CHARS);
        assert_eq!(preview.body.chars().count(), MAX_NOTIFICATION_BODY_CHARS);
        assert!(preview.title.ends_with("..."));
        assert!(preview.body.ends_with("..."));
    }

    #[test]
    fn rejects_control_characters_in_related_id() {
        let mut input = payload("title", "body");
        input.related_id = Some("case\n1".to_string());

        assert!(build_desktop_notification_preview(input).is_err());
    }

    #[test]
    fn response_keeps_privacy_mode_and_local_boundary() {
        let preview = build_desktop_notification_preview(payload("title", "body")).unwrap();
        let response = response_from_preview(preview, AppMode::TopSecret, "ok".to_string());

        assert!(response.success);
        assert_eq!(response.privacy_mode, AppMode::TopSecret);
        assert!(response.local_only);
        assert!(response.safe_in_top_secret);
    }
}
