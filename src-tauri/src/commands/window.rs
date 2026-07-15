use tauri::{AppHandle, Manager};

use crate::error::AppError;

#[tauri::command]
pub fn hide_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.hide();
    }
}

/// Abre (ou traz ao foco) a janela de configurações.
///
/// A janela `settings` é declarada estaticamente em `tauri.conf.json`
/// (invisível na inicialização) e o fechamento apenas a esconde — como a
/// `main`. Assim ela já está carregada e basta mostrá-la, evitando a criação
/// dinâmica de WebviewWindow em runtime, que era a causa da tela em branco
/// (o segundo webview não carregava a página de forma confiável, sobretudo no
/// WebKitGTK do Linux).
#[tauri::command]
pub fn open_settings(app: AppHandle) -> Result<(), AppError> {
    let window = app
        .get_webview_window("settings")
        .ok_or(AppError::Message("janela 'settings' não encontrada".into()))?;
    let _ = window.unminimize();
    let _ = window.show();
    let _ = window.set_focus();
    Ok(())
}
