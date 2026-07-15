use serde::Serialize;
use tauri::State;

use crate::db::{self, ClipItem};
use crate::error::AppError;
use crate::AppState;

#[derive(Serialize)]
pub struct HistoryPage {
    pub items: Vec<ClipItem>,
    #[serde(rename = "hasMore")]
    pub has_more: bool,
}

#[tauri::command]
pub fn get_history(
    state: State<'_, AppState>,
    page: u32,
    page_size: u32,
    query: Option<String>,
    type_filter: Option<String>,
    group_id: Option<i64>,
) -> Result<HistoryPage, AppError> {
    let conn = state.db()?;
    let (items, has_more) = db::query_page(
        &conn,
        page,
        page_size.clamp(1, 100),
        query.as_deref(),
        type_filter.as_deref(),
        group_id,
    )?;
    Ok(HistoryPage { items, has_more })
}

#[tauri::command]
pub fn delete_item(state: State<'_, AppState>, id: i64) -> Result<(), AppError> {
    let file_path = {
        let conn = state.db()?;
        db::delete(&conn, id)?
    };
    if let Some(path) = file_path {
        let _ = std::fs::remove_file(path);
    }
    Ok(())
}

#[tauri::command]
pub fn toggle_pin(state: State<'_, AppState>, id: i64) -> Result<bool, AppError> {
    let conn = state.db()?;
    db::toggle_pin(&conn, id)
}
