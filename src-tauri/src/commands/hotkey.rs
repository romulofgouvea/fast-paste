use serde_json::json;
use tauri::{AppHandle, State};

use crate::error::AppError;
use crate::{hotkey, settings};
use crate::AppState;

/// Valida, registra e persiste uma nova hotkey global vinda do key recorder.
#[tauri::command]
pub fn set_hotkey(app: AppHandle, state: State<'_, AppState>, shortcut: String) -> Result<(), AppError> {
    let mut current = state.hotkey()?;
    hotkey::swap_hotkey(&app, &shortcut, Some(current.as_str()))?;
    *current = shortcut.clone();
    settings::set(&app, settings::KEY_HOTKEY, json!(shortcut))
}

#[tauri::command]
pub fn get_hotkey(state: State<'_, AppState>) -> Result<String, AppError> {
    Ok(state.hotkey()?.clone())
}

/// Silencia temporariamente a hotkey ativa enquanto o key recorder grava
/// uma nova combinação (evita que apertar o atalho atual abra a janela
/// principal em vez de ser capturado pela UI de configurações).
#[tauri::command]
pub fn suspend_hotkey(app: AppHandle, state: State<'_, AppState>) -> Result<(), AppError> {
    let current = state.hotkey()?;
    hotkey::unregister(&app, &current);
    Ok(())
}

/// Restaura a hotkey ativa após o cancelamento da gravação (Esc ou combinação inválida).
#[tauri::command]
pub fn resume_hotkey(app: AppHandle, state: State<'_, AppState>) -> Result<(), AppError> {
    let current = state.hotkey()?;
    hotkey::swap_hotkey(&app, &current, None)
}
