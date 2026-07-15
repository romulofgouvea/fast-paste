use std::sync::atomic::Ordering;

use clipboard_rs::common::{RustImage, RustImageData};
use clipboard_rs::{Clipboard, ClipboardContext};
use tauri::{AppHandle, Manager, State};

use crate::db;
use crate::error::AppError;
use crate::AppState;
use crate::{hotkey, media};

/// Conteúdo a ser devolvido ao clipboard do SO.
enum ClipPayload {
    Text(String),
    Image(Vec<u8>),
}

/// Escreve o payload no clipboard, esconde a janela principal e dispara o
/// auto-paste. Centraliza a sequência antes duplicada entre `select_item` e
/// `paste_text` (suprimir captura → escrever → esconder → colar).
fn put_on_clipboard_and_hide(
    app: &AppHandle,
    state: &State<'_, AppState>,
    payload: ClipPayload,
) -> Result<(), AppError> {
    // O watcher deve ignorar esta escrita — é o próprio FPaste copiando.
    state.suppress_capture.store(true, Ordering::SeqCst);
    let ctx = ClipboardContext::new().map_err(AppError::msg)?;
    match payload {
        ClipPayload::Text(text) => ctx.set_text(text).map_err(AppError::msg)?,
        ClipPayload::Image(bytes) => {
            let image = RustImageData::from_bytes(&bytes).map_err(AppError::msg)?;
            ctx.set_image(image).map_err(AppError::msg)?;
        }
    }
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.hide();
    }
    maybe_auto_paste(state);
    Ok(())
}

fn maybe_auto_paste(state: &State<'_, AppState>) {
    let enabled = state.auto_paste().map(|v| *v).unwrap_or(false);
    if !enabled {
        return;
    }
    let hwnd = state.last_focus.lock().ok().and_then(|g| *g);
    if let Some(hwnd) = hwnd {
        std::thread::spawn(move || hotkey::paste_into(hwnd));
    }
}

/// Copia o item escolhido de volta para o clipboard do SO e esconde a janela.
#[tauri::command]
pub fn select_item(app: AppHandle, state: State<'_, AppState>, id: i64) -> Result<(), AppError> {
    let (content, media_path) = {
        let conn = state.db()?;
        (db::get_content(&conn, id)?, db::get_media_path(&conn, id)?)
    };

    let payload = if let Some(text) = content {
        ClipPayload::Text(text)
    } else if let Some(path) = media_path {
        let plain = media::load_decrypted(std::path::Path::new(&path), &state.master_key)?;
        ClipPayload::Image(plain)
    } else {
        return Err(AppError::msg("item sem conteúdo"));
    };

    put_on_clipboard_and_hide(&app, &state, payload)
}

/// Copia texto arbitrário direto para o clipboard (usado pelo menu de
/// transformações: "colar como texto puro", "inverter maiúsc/minúsc" etc.)
/// sem passar pelo histórico.
#[tauri::command]
pub fn paste_text(
    app: AppHandle,
    state: State<'_, AppState>,
    text: String,
) -> Result<(), AppError> {
    put_on_clipboard_and_hide(&app, &state, ClipPayload::Text(text))
}
