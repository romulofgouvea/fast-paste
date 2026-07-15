use tauri::State;

use crate::db;
use crate::error::AppError;
use crate::AppState;

#[tauri::command]
pub fn list_groups(state: State<'_, AppState>) -> Result<Vec<db::Group>, AppError> {
    let conn = state.db()?;
    db::list_groups(&conn)
}

#[tauri::command]
pub fn create_group(state: State<'_, AppState>, name: String) -> Result<i64, AppError> {
    let name = name.trim();
    if name.is_empty() {
        return Err(AppError::msg("nome do grupo não pode ser vazio"));
    }
    let conn = state.db()?;
    db::create_group(&conn, name)
}

#[tauri::command]
pub fn delete_group(state: State<'_, AppState>, id: i64) -> Result<(), AppError> {
    let conn = state.db()?;
    db::delete_group(&conn, id)
}

#[tauri::command]
pub fn set_item_group(
    state: State<'_, AppState>,
    id: i64,
    group_id: Option<i64>,
) -> Result<(), AppError> {
    let conn = state.db()?;
    db::set_item_group(&conn, id, group_id)
}
