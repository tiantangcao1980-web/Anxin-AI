use serde_json::Value;
use tauri::AppHandle;

use crate::services::secure_db::{self, SecureDbResetReport, SecureExecuteResult};

#[tauri::command]
pub fn secure_sql_execute(
    app: AppHandle,
    sql: String,
    bind_values: Option<Vec<Value>>,
) -> Result<SecureExecuteResult, String> {
    secure_db::execute(&app, &sql, bind_values.unwrap_or_default())
}

#[tauri::command]
pub fn secure_sql_select(
    app: AppHandle,
    sql: String,
    bind_values: Option<Vec<Value>>,
) -> Result<Vec<Value>, String> {
    secure_db::select(&app, &sql, bind_values.unwrap_or_default())
}

#[tauri::command]
pub fn secure_db_reset_local_data(
    app: AppHandle,
    confirmation: String,
) -> Result<SecureDbResetReport, String> {
    secure_db::reset_local_data(&app, &confirmation)
}
