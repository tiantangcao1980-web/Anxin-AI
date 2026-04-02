use serde::{Deserialize, Serialize};

/// 同步操作类型
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SyncAction {
    Create,
    Update,
    Delete,
}

/// 同步实体类型
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EntityType {
    Message,
    Document,
    Case,
    Contract,
    Setting,
}

/// 单条同步记录
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncRecord {
    pub id: String,
    pub entity_type: EntityType,
    pub entity_id: String,
    pub action: SyncAction,
    pub data: serde_json::Value,
    pub timestamp: String,
    pub version: i64,
}

/// 同步推送请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncPushRequest {
    pub records: Vec<SyncRecord>,
    pub device_id: String,
    pub last_sync_version: i64,
}

/// 同步拉取响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncPullResponse {
    pub records: Vec<SyncRecord>,
    pub server_version: i64,
    pub has_more: bool,
}

/// 同步冲突
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncConflict {
    pub entity_type: EntityType,
    pub entity_id: String,
    pub local_data: serde_json::Value,
    pub remote_data: serde_json::Value,
    pub local_timestamp: String,
    pub remote_timestamp: String,
}

/// 冲突解决策略
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ConflictResolution {
    KeepLocal,
    KeepRemote,
    Merge(serde_json::Value),
}

/// OTA 更新信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateInfo {
    pub version: String,
    pub notes: String,
    pub pub_date: String,
    pub url: String,
    pub signature: String,
    pub mandatory: bool,
}
