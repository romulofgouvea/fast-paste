use tauri::{AppHandle, Manager};

use crate::error::AppError;

#[tauri::command]
pub fn hide_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.hide();
    }
}

/// Abre (ou traz ao foco) a janela de configurações.
/// Usa `run_on_main_thread` porque a criação de WebviewWindow deve ocorrer
/// na thread principal no Windows/macOS. O comando retorna imediatamente
/// (fire-and-forget) para não bloquear o invoke do frontend, evitando o
/// deadlock que causava tela em branco no WebView2.
#[tauri::command]
pub fn open_settings(app: AppHandle) -> Result<(), AppError> {
    if let Some(window) = app.get_webview_window("settings") {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
        return Ok(());
    }

    let app_clone = app.clone();
    app.run_on_main_thread(move || {
        // URL vazia = raiz do dev server (http://localhost:1420/) ou
        // do frontendDist em produção. "index.html" falhava no Vite.
        let result = tauri::WebviewWindowBuilder::new(
            &app_clone,
            "settings",
            tauri::WebviewUrl::default(),
        )
        .title("Configurações — FPaste")
        .inner_size(760.0, 560.0)
        .min_inner_size(640.0, 480.0)
        .resizable(false)
        .center()
        // Injeta antes do React rodar — garante detecção do tipo de janela
        // independente de timing do getCurrentWindow() no WebView2.
        .initialization_script("window.__FPASTE_WINDOW__ = 'settings';")
        .build();

        if let Ok(window) = &result {
            let _ = window.show();
            let _ = window.set_focus();
        }
        if let Err(e) = result {
            eprintln!("fpaste: falha ao abrir configurações: {e}");
        }
    })
    .map_err(AppError::msg)
}
