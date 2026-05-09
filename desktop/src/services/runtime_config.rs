use crate::models::{AppMode, AppStateData, SyncStatus};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use tauri::{AppHandle, Manager};

const CONFIG_FILE_NAME: &str = "runtime-config.json";
const CONFIG_SCHEMA_VERSION: u8 = 1;
const MAX_PROFILE_COUNT: usize = 20;
const MAX_PROFILE_NAME_LEN: usize = 60;
const MAX_PROFILE_ID_LEN: usize = 80;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopRuntimeProfile {
    pub id: String,
    pub name: String,
    pub mode: AppMode,
    pub backend_url: String,
}

impl DesktopRuntimeProfile {
    pub fn new(id: &str, name: &str, mode: AppMode, backend_url: &str) -> Result<Self, String> {
        Ok(Self {
            id: normalize_profile_id(id)?,
            name: normalize_profile_name(name)?,
            mode,
            backend_url: normalize_backend_url(backend_url)?,
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopRuntimeConfig {
    pub schema_version: u8,
    pub mode: AppMode,
    pub backend_url: String,
    #[serde(default)]
    pub profiles: Vec<DesktopRuntimeProfile>,
}

impl DesktopRuntimeConfig {
    pub fn new(mode: AppMode, backend_url: &str) -> Result<Self, String> {
        Ok(Self {
            schema_version: CONFIG_SCHEMA_VERSION,
            mode,
            backend_url: normalize_backend_url(backend_url)?,
            profiles: Vec::new(),
        })
    }

    pub fn apply_to_state(&self, state: &mut AppStateData) {
        state.mode = self.mode;
        state.backend_url = self.backend_url.clone();
        state.sync_status = sync_status_for_mode(self.mode);
    }

    pub fn with_profiles(mut self, profiles: Vec<DesktopRuntimeProfile>) -> Result<Self, String> {
        self.profiles = normalize_profiles(profiles)?;
        Ok(self)
    }
}

pub fn normalize_backend_url(input: &str) -> Result<String, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Err("后端地址不能为空".to_string());
    }

    let parsed = reqwest::Url::parse(trimmed)
        .map_err(|_| "请输入完整的 http:// 或 https:// 地址".to_string())?;
    if !matches!(parsed.scheme(), "http" | "https") {
        return Err("后端地址只允许 http 或 https 协议".to_string());
    }
    if parsed.host_str().is_none() {
        return Err("后端地址缺少主机名".to_string());
    }

    Ok(parsed.to_string().trim_end_matches('/').to_string())
}

pub fn normalize_profile_name(input: &str) -> Result<String, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Err("配置档名称不能为空".to_string());
    }
    if trimmed.chars().count() > MAX_PROFILE_NAME_LEN {
        return Err(format!("配置档名称不能超过 {MAX_PROFILE_NAME_LEN} 个字符"));
    }
    Ok(trimmed.to_string())
}

pub fn normalize_profile_id(input: &str) -> Result<String, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Err("配置档 ID 不能为空".to_string());
    }
    if trimmed.len() > MAX_PROFILE_ID_LEN {
        return Err(format!("配置档 ID 不能超过 {MAX_PROFILE_ID_LEN} 个字符"));
    }
    if !trimmed
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_'))
    {
        return Err("配置档 ID 只能包含字母、数字、短横线或下划线".to_string());
    }
    Ok(trimmed.to_string())
}

pub fn generate_profile_id(name: &str) -> String {
    let slug = name
        .trim()
        .to_lowercase()
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() {
                ch
            } else if ch.is_whitespace() || matches!(ch, '-' | '_') {
                '-'
            } else {
                'p'
            }
        })
        .collect::<String>()
        .split('-')
        .filter(|part| !part.is_empty())
        .take(6)
        .collect::<Vec<_>>()
        .join("-");
    let prefix = if slug.is_empty() {
        "profile"
    } else {
        slug.as_str()
    };
    let millis = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis())
        .unwrap_or_default();
    format!("{prefix}-{millis}")
}

pub fn generate_unique_profile_id(name: &str, profiles: &[DesktopRuntimeProfile]) -> String {
    let base_id = generate_profile_id(name);
    if profiles.iter().all(|profile| profile.id != base_id) {
        return base_id;
    }

    for suffix in 2..=MAX_PROFILE_COUNT + 1 {
        let candidate = format!("{base_id}-{suffix}");
        if profiles.iter().all(|profile| profile.id != candidate) {
            return candidate;
        }
    }
    base_id
}

pub fn normalize_profiles(
    profiles: Vec<DesktopRuntimeProfile>,
) -> Result<Vec<DesktopRuntimeProfile>, String> {
    if profiles.len() > MAX_PROFILE_COUNT {
        return Err(format!("工作站配置档最多保留 {MAX_PROFILE_COUNT} 个"));
    }

    let mut normalized = Vec::with_capacity(profiles.len());
    let mut seen_ids = std::collections::HashSet::new();
    for profile in profiles {
        let sanitized = DesktopRuntimeProfile::new(
            &profile.id,
            &profile.name,
            profile.mode,
            &profile.backend_url,
        )?;
        if !seen_ids.insert(sanitized.id.clone()) {
            return Err(format!("配置档 ID 重复: {}", sanitized.id));
        }
        normalized.push(sanitized);
    }
    Ok(normalized)
}

pub fn load_or_default_for_app(
    app: &AppHandle,
    state: &AppStateData,
) -> Result<DesktopRuntimeConfig, String> {
    match load_for_app(app)? {
        Some(config) => Ok(config),
        None => DesktopRuntimeConfig::new(state.mode, &state.backend_url),
    }
}

pub fn runtime_config_path(app: &AppHandle) -> Result<PathBuf, String> {
    if let Ok(path) = std::env::var("ANXIN_DESKTOP_RUNTIME_CONFIG_PATH") {
        return Ok(PathBuf::from(path));
    }

    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("无法定位桌面运行配置目录: {err}"))?;
    Ok(data_dir.join(CONFIG_FILE_NAME))
}

pub fn load_for_app(app: &AppHandle) -> Result<Option<DesktopRuntimeConfig>, String> {
    let path = runtime_config_path(app)?;
    load_runtime_config_from_path(&path)
}

pub fn save_for_app(app: &AppHandle, config: &DesktopRuntimeConfig) -> Result<(), String> {
    let path = runtime_config_path(app)?;
    save_runtime_config_to_path(&path, config)
}

pub fn load_runtime_config_from_path(path: &Path) -> Result<Option<DesktopRuntimeConfig>, String> {
    if !path.exists() {
        return Ok(None);
    }

    let raw = fs::read_to_string(path)
        .map_err(|err| format!("无法读取桌面运行配置 {}: {err}", path.display()))?;
    let mut config: DesktopRuntimeConfig = serde_json::from_str(&raw)
        .map_err(|err| format!("桌面运行配置格式无效 {}: {err}", path.display()))?;

    if config.schema_version != CONFIG_SCHEMA_VERSION {
        return Err(format!(
            "桌面运行配置版本不受支持: {}",
            config.schema_version
        ));
    }

    config.backend_url = normalize_backend_url(&config.backend_url)?;
    config.profiles = normalize_profiles(config.profiles)?;
    Ok(Some(config))
}

pub fn save_runtime_config_to_path(
    path: &Path,
    config: &DesktopRuntimeConfig,
) -> Result<(), String> {
    let persisted = DesktopRuntimeConfig::new(config.mode, &config.backend_url)?
        .with_profiles(config.profiles.clone())?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|err| format!("无法创建桌面运行配置目录 {}: {err}", parent.display()))?;
    }

    let raw = serde_json::to_string_pretty(&persisted)
        .map_err(|err| format!("无法序列化桌面运行配置: {err}"))?;
    let tmp_path = path.with_extension("json.tmp");
    fs::write(&tmp_path, raw)
        .map_err(|err| format!("无法写入桌面运行配置临时文件 {}: {err}", tmp_path.display()))?;

    if path.exists() {
        fs::remove_file(path)
            .map_err(|err| format!("无法替换旧桌面运行配置 {}: {err}", path.display()))?;
    }
    fs::rename(&tmp_path, path)
        .map_err(|err| format!("无法保存桌面运行配置 {}: {err}", path.display()))?;
    Ok(())
}

fn sync_status_for_mode(mode: AppMode) -> SyncStatus {
    match mode {
        AppMode::TopSecret => SyncStatus::Offline,
        AppMode::Hybrid | AppMode::Cloud => SyncStatus::Idle,
    }
}

#[cfg(test)]
mod tests {
    use super::{
        generate_unique_profile_id, load_runtime_config_from_path, normalize_backend_url,
        normalize_profiles, save_runtime_config_to_path, DesktopRuntimeConfig,
        DesktopRuntimeProfile,
    };
    use crate::models::{AppMode, AppStateData, SyncStatus};
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn test_path(name: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after UNIX_EPOCH")
            .as_nanos();
        std::env::temp_dir().join(format!("anxin-runtime-config-{name}-{nonce}.json"))
    }

    #[test]
    fn normalizes_http_backend_url() {
        assert_eq!(
            normalize_backend_url(" http://localhost:8001/ ").unwrap(),
            "http://localhost:8001"
        );
        assert_eq!(
            normalize_backend_url("https://api.anxin.example/v1/").unwrap(),
            "https://api.anxin.example/v1"
        );
    }

    #[test]
    fn rejects_non_backend_url_schemes() {
        assert!(normalize_backend_url("").is_err());
        assert!(normalize_backend_url("local://api").is_err());
        assert!(normalize_backend_url("file:///tmp/anxin").is_err());
    }

    #[test]
    fn saves_and_loads_runtime_config_without_secrets() {
        let path = test_path("round-trip");
        let profile = DesktopRuntimeProfile::new(
            "staging",
            "Staging",
            AppMode::Hybrid,
            "https://staging.anxin.example/",
        )
        .unwrap();
        let config = DesktopRuntimeConfig::new(AppMode::Hybrid, "https://api.anxin.example/v1/")
            .unwrap()
            .with_profiles(vec![profile])
            .unwrap();

        save_runtime_config_to_path(&path, &config).unwrap();
        let loaded = load_runtime_config_from_path(&path).unwrap().unwrap();
        let raw = std::fs::read_to_string(&path).unwrap();

        assert_eq!(loaded.mode, AppMode::Hybrid);
        assert_eq!(loaded.backend_url, "https://api.anxin.example/v1");
        assert_eq!(loaded.profiles.len(), 1);
        assert_eq!(
            loaded.profiles[0].backend_url,
            "https://staging.anxin.example"
        );
        assert!(!raw.contains("token"));
        assert!(!raw.contains("secret"));

        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn accepts_legacy_runtime_config_without_profiles() {
        let path = test_path("legacy");
        std::fs::write(
            &path,
            r#"{"schemaVersion":1,"mode":"hybrid","backendUrl":"http://localhost:8001/"}"#,
        )
        .unwrap();

        let loaded = load_runtime_config_from_path(&path).unwrap().unwrap();

        assert_eq!(loaded.mode, AppMode::Hybrid);
        assert_eq!(loaded.backend_url, "http://localhost:8001");
        assert!(loaded.profiles.is_empty());

        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn rejects_duplicate_profile_ids_and_unsafe_profile_backend() {
        let duplicate = DesktopRuntimeProfile::new(
            "staging",
            "Staging",
            AppMode::Hybrid,
            "https://staging.anxin.example",
        )
        .unwrap();
        let duplicate_again = DesktopRuntimeProfile::new(
            "staging",
            "Staging Copy",
            AppMode::Cloud,
            "https://api.anxin.example",
        )
        .unwrap();
        assert!(normalize_profiles(vec![duplicate, duplicate_again]).is_err());
        assert!(DesktopRuntimeProfile::new("prod", "Prod", AppMode::Cloud, "file:///tmp").is_err());
        assert!(DesktopRuntimeProfile::new(
            "bad id",
            "Prod",
            AppMode::Cloud,
            "https://api.example"
        )
        .is_err());
    }

    #[test]
    fn generated_profile_id_avoids_existing_profiles() {
        let existing = DesktopRuntimeProfile::new(
            "staging-123",
            "Staging",
            AppMode::Hybrid,
            "https://staging.anxin.example",
        )
        .unwrap();
        let generated = generate_unique_profile_id("Staging", &[existing]);

        assert_ne!(generated, "staging-123");
        assert!(generated.starts_with("staging-"));
    }

    #[test]
    fn rejects_persisted_local_backend_placeholder() {
        let path = test_path("invalid-scheme");
        std::fs::write(
            &path,
            r#"{"schemaVersion":1,"mode":"hybrid","backendUrl":"local://api"}"#,
        )
        .unwrap();

        assert!(load_runtime_config_from_path(&path).is_err());

        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn applies_runtime_config_to_state_without_auth_material() {
        let mut state = AppStateData {
            user_token: Some("do-not-persist".to_string()),
            ..AppStateData::default()
        };
        let config =
            DesktopRuntimeConfig::new(AppMode::TopSecret, "http://localhost:9000").unwrap();

        config.apply_to_state(&mut state);

        assert_eq!(state.mode, AppMode::TopSecret);
        assert_eq!(state.sync_status, SyncStatus::Offline);
        assert_eq!(state.backend_url, "http://localhost:9000");
        assert_eq!(state.user_token.as_deref(), Some("do-not-persist"));
    }
}
