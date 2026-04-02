use crate::models::SharedAppState;

/// OTA 更新检查器
///
/// 属于控制面，在所有运行模式下都保持工作。
/// 使用 tauri-plugin-updater 的前端 API 执行实际更新。
/// 此模块提供 Rust 侧的辅助功能。
pub struct UpdateChecker {
    state: SharedAppState,
}

impl UpdateChecker {
    pub fn new(state: SharedAppState) -> Self {
        Self { state }
    }

    /// 检查更新（控制面 - 所有模式可用）
    pub async fn check_update(&self) -> Result<Option<UpdateAvailable>, String> {
        let backend_url = {
            self.state.read().await.backend_url.clone()
        };

        let current_version = env!("CARGO_PKG_VERSION");
        let target = std::env::consts::OS;
        let arch = std::env::consts::ARCH;

        let url = format!(
            "{}/api/v1/updates/{}/{}/{}",
            backend_url, target, arch, current_version
        );

        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(15))
            .build()
            .map_err(|e| e.to_string())?;

        let response = match client.get(&url).send().await {
            Ok(resp) => resp,
            Err(e) => {
                log::warn!("更新检查失败: {}", e);
                return Ok(None);
            }
        };

        if response.status() == reqwest::StatusCode::NO_CONTENT {
            // 204 = 已是最新版本
            return Ok(None);
        }

        if !response.status().is_success() {
            return Ok(None);
        }

        let update: UpdateAvailable = response
            .json()
            .await
            .map_err(|e| format!("解析更新信息失败: {}", e))?;

        Ok(Some(update))
    }
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct UpdateAvailable {
    pub version: String,
    pub notes: String,
    pub pub_date: String,
    pub url: String,
    pub signature: String,
    pub mandatory: bool,
}
