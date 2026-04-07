#![allow(dead_code)]

use crate::models::{AppMode, AppStateData, SharedAppState, SyncStatus};

/// 模式管理器：管理三种运行模式的切换和状态
pub struct ModeManager {
    state: SharedAppState,
}

impl ModeManager {
    pub fn new(state: SharedAppState) -> Self {
        Self { state }
    }

    /// 切换运行模式
    pub async fn switch_mode(&self, new_mode: AppMode) -> Result<AppMode, String> {
        let mut s = self.state.write().await;
        let old = s.mode;

        // 如果模式相同，直接返回
        if old == new_mode {
            return Ok(old);
        }

        // 模式切换前的清理
        match (old, new_mode) {
            // 从云端/混合切换到绝密：断开数据面
            (_, AppMode::TopSecret) => {
                s.sync_status = SyncStatus::Offline;
                log::info!("已进入绝密模式：数据面断开，控制面保持");
            }
            // 从绝密切换到混合/云端：重新连接数据面
            (AppMode::TopSecret, _) => {
                s.sync_status = SyncStatus::Idle;
                log::info!("已退出绝密模式：数据面恢复连接");
            }
            _ => {
                s.sync_status = SyncStatus::Idle;
            }
        }

        s.mode = new_mode;
        Ok(old)
    }

    /// 获取当前模式
    pub async fn current_mode(&self) -> AppMode {
        self.state.read().await.mode
    }

    /// 获取完整状态快照
    pub async fn snapshot(&self) -> AppStateData {
        self.state.read().await.clone()
    }

    /// 检查是否允许网络数据操作
    pub async fn is_data_network_allowed(&self) -> bool {
        let s = self.state.read().await;
        matches!(s.mode, AppMode::Hybrid | AppMode::Cloud)
    }

    /// 检查是否允许控制面操作（始终允许）
    pub fn is_control_plane_allowed(&self) -> bool {
        // 控制面（OTA、许可证验证）在所有模式下都可用
        true
    }
}
