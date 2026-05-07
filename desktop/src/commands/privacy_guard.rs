use crate::models::{AppMode, SharedAppState};

pub fn ensure_data_network_allowed_for_mode(mode: AppMode, action: &str) -> Result<(), String> {
    if mode == AppMode::TopSecret {
        return Err(format!(
            "绝密模式下禁止{action}；请切换到混合或云端模式后再执行外部数据操作"
        ));
    }
    Ok(())
}

pub async fn ensure_data_network_allowed(
    state: &SharedAppState,
    action: &str,
) -> Result<(), String> {
    let mode = state.read().await.mode;
    ensure_data_network_allowed_for_mode(mode, action)
}

#[cfg(test)]
mod tests {
    use super::ensure_data_network_allowed_for_mode;
    use crate::models::AppMode;

    #[test]
    fn rejects_data_network_actions_in_top_secret_mode() {
        let err = ensure_data_network_allowed_for_mode(AppMode::TopSecret, "执行 CLI 命令")
            .expect_err("top secret mode must block data-network operations");

        assert!(err.contains("绝密模式下禁止执行 CLI 命令"));
    }

    #[test]
    fn allows_data_network_actions_in_hybrid_and_cloud_modes() {
        assert!(ensure_data_network_allowed_for_mode(AppMode::Hybrid, "同步").is_ok());
        assert!(ensure_data_network_allowed_for_mode(AppMode::Cloud, "同步").is_ok());
    }
}
