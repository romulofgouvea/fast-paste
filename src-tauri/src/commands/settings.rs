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

#[tauri::command]
pub fn open_linux_keyboard_settings() -> Result<(), AppError> {
    #[cfg(target_os = "linux")]
    {
        let _ = std::process::Command::new("gnome-control-center")
            .arg("keyboard")
            .spawn();
    }
    Ok(())
}

/// `true` se o FPaste tem permissão de Acessibilidade no macOS — necessária
/// para o auto-paste injetar o Cmd+V. Nas outras plataformas retorna `true`
/// (não se aplica), para o front-end não mostrar o aviso à toa.
#[tauri::command]
pub fn macos_accessibility_trusted() -> bool {
    #[cfg(target_os = "macos")]
    {
        // `Boolean` do CoreFoundation é um `u8` (0/1), não o `bool` do Rust.
        #[link(name = "ApplicationServices", kind = "framework")]
        extern "C" {
            fn AXIsProcessTrusted() -> u8;
        }
        unsafe { AXIsProcessTrusted() != 0 }
    }
    #[cfg(not(target_os = "macos"))]
    {
        true
    }
}

/// Abre o painel Ajustes → Privacidade e Segurança → Acessibilidade no macOS,
/// já rolado até a lista onde o usuário marca o FPaste.
#[tauri::command]
pub fn open_macos_accessibility_settings() -> Result<(), AppError> {
    #[cfg(target_os = "macos")]
    {
        let _ = std::process::Command::new("open")
            .arg("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")
            .spawn();
    }
    Ok(())
}
