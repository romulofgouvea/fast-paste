use serde::Serialize;
use tauri::State;

use crate::error::AppError;
use crate::AppState;

#[derive(Serialize)]
pub struct StorageInfo {
    pub path: String,
    #[serde(rename = "dbSizeBytes")]
    pub db_size_bytes: u64,
    #[serde(rename = "itemCount")]
    pub item_count: i64,
}

#[tauri::command]
pub fn get_storage_info(state: State<'_, AppState>) -> Result<StorageInfo, AppError> {
    let db_path = state.data_dir.join("fpaste.db");
    let db_size_bytes = std::fs::metadata(&db_path).map(|m| m.len()).unwrap_or(0);
    let conn = state.db()?;
    let item_count: i64 =
        conn.query_row("SELECT COUNT(*) FROM clipboard_history", [], |r| r.get(0))?;
    Ok(StorageInfo {
        path: db_path.display().to_string(),
        db_size_bytes,
        item_count,
    })
}

#[tauri::command]
pub fn clear_history(state: State<'_, AppState>) -> Result<(), AppError> {
    {
        let conn = state.db()?;
        conn.execute("DELETE FROM clipboard_history", [])?;
    }
    let _ = std::fs::remove_dir_all(state.data_dir.join("media"));
    Ok(())
}
