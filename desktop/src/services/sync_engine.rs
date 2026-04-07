#![allow(dead_code)]

use crate::models::{AppMode, SharedAppState, SyncStatus};

/// 同步引擎：处理本地与云端之间的数据同步
///
/// 架构设计：
/// - 控制面（始终在线）：OTA 更新、许可证验证、能力清单
/// - 数据面（按模式）：消息、文档、案件等业务数据
pub struct SyncEngine {
    state: SharedAppState,
    backend_url: String,
}

impl SyncEngine {
    pub fn new(state: SharedAppState, backend_url: String) -> Self {
        Self {
            state,
            backend_url,
        }
    }

    /// 执行增量同步
    pub async fn sync(&self) -> Result<SyncResult, String> {
        let mode = {
            let s = self.state.read().await;
            s.mode
        };

        match mode {
            AppMode::TopSecret => {
                return Ok(SyncResult {
                    success: false,
                    pushed: 0,
                    pulled: 0,
                    conflicts: 0,
                    message: "绝密模式下不执行数据同步".to_string(),
                });
            }
            AppMode::Hybrid => self.sync_selective().await,
            AppMode::Cloud => self.sync_full().await,
        }
    }

    /// 选择性同步（混合模式）
    async fn sync_selective(&self) -> Result<SyncResult, String> {
        self.set_sync_status(SyncStatus::Syncing).await;

        // 1. 推送本地待同步数据
        let pushed = self.push_pending_records().await?;

        // 2. 拉取云端增量更新（仅用户标记为同步的内容）
        let pulled = self.pull_incremental_updates().await?;

        self.set_sync_status(SyncStatus::Idle).await;
        self.update_last_sync_time().await;

        Ok(SyncResult {
            success: true,
            pushed,
            pulled,
            conflicts: 0,
            message: "混合模式同步完成".to_string(),
        })
    }

    /// 全量同步（云端模式）
    async fn sync_full(&self) -> Result<SyncResult, String> {
        self.set_sync_status(SyncStatus::Syncing).await;

        let pushed = self.push_pending_records().await?;
        let pulled = self.pull_incremental_updates().await?;

        self.set_sync_status(SyncStatus::Idle).await;
        self.update_last_sync_time().await;

        Ok(SyncResult {
            success: true,
            pushed,
            pulled,
            conflicts: 0,
            message: "全量同步完成".to_string(),
        })
    }

    /// 推送本地待同步记录
    async fn push_pending_records(&self) -> Result<u32, String> {
        // TODO: 从 SQLite sync_log 查询 status='pending' 的记录
        // 然后 POST /api/v1/sync/push
        log::info!("推送待同步记录到: {}/api/v1/sync/push", self.backend_url);
        Ok(0)
    }

    /// 拉取云端增量更新
    async fn pull_incremental_updates(&self) -> Result<u32, String> {
        // TODO: GET /api/v1/sync/pull?since={last_sync_version}
        // 然后写入本地 SQLite
        log::info!(
            "拉取增量更新从: {}/api/v1/sync/pull",
            self.backend_url
        );
        Ok(0)
    }

    /// 控制面心跳（所有模式都执行）
    pub async fn control_plane_heartbeat(&self) -> Result<(), String> {
        let backend_url = {
            self.state.read().await.backend_url.clone()
        };

        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .map_err(|e| e.to_string())?;

        match client
            .get(format!("{}/api/v1/health", backend_url))
            .send()
            .await
        {
            Ok(resp) => {
                let mut s = self.state.write().await;
                s.is_online = resp.status().is_success();
                Ok(())
            }
            Err(_) => {
                let mut s = self.state.write().await;
                s.is_online = false;
                Ok(())
            }
        }
    }

    async fn set_sync_status(&self, status: SyncStatus) {
        let mut s = self.state.write().await;
        s.sync_status = status;
    }

    async fn update_last_sync_time(&self) {
        let mut s = self.state.write().await;
        s.last_sync_time = Some(chrono::Utc::now().to_rfc3339());
    }
}

#[derive(Debug, serde::Serialize)]
pub struct SyncResult {
    pub success: bool,
    pub pushed: u32,
    pub pulled: u32,
    pub conflicts: u32,
    pub message: String,
}
