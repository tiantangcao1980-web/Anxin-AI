use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;

/// 三种运行模式
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum AppMode {
    /// 绝密模式：完全本地处理，仅 OTA 更新通道
    TopSecret,
    /// 混合模式：本地 + 选择性云同步
    Hybrid,
    /// 云端模式：完全依托云端
    #[default]
    Cloud,
}

impl std::fmt::Display for AppMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AppMode::TopSecret => write!(f, "绝密模式"),
            AppMode::Hybrid => write!(f, "混合模式"),
            AppMode::Cloud => write!(f, "云端模式"),
        }
    }
}

/// 同步状态
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum SyncStatus {
    #[default]
    Idle,
    Syncing,
    Error,
    Offline,
}

/// 全局应用状态（线程安全共享）
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppStateData {
    pub mode: AppMode,
    pub sync_status: SyncStatus,
    pub last_sync_time: Option<String>,
    pub backend_url: String,
    pub is_online: bool,
    pub user_token: Option<String>,
    pub unread_count: u32,
}

impl Default for AppStateData {
    fn default() -> Self {
        Self {
            mode: AppMode::default(),
            sync_status: SyncStatus::default(),
            last_sync_time: None,
            backend_url: std::env::var("ANXIN_BACKEND_URL")
                .unwrap_or_else(|_| "http://localhost:8001".to_string()),
            is_online: true,
            user_token: None,
            unread_count: 0,
        }
    }
}

/// 线程安全的全局状态容器
pub type SharedAppState = Arc<RwLock<AppStateData>>;

pub fn create_shared_state() -> SharedAppState {
    Arc::new(RwLock::new(AppStateData::default()))
}
