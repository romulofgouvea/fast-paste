use serde_json::json;
use tauri::{AppHandle, State};

use crate::error::AppError;
use crate::settings;
use crate::AppState;

#[tauri::command]
pub fn set_auto_paste(
    app: AppHandle,
    state: State<'_, AppState>,
    enabled: bool,
) -> Result<(), AppError> {
    *state.auto_paste()? = enabled;
    settings::set(&app, settings::KEY_AUTO_PASTE, json!(enabled))
}

#[tauri::command]
pub fn get_auto_paste(state: State<'_, AppState>) -> Result<bool, AppError> {
    Ok(*state.auto_paste()?)
}
