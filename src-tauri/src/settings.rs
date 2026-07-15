//! Acesso centralizado ao arquivo de configurações do Tauri (`settings.json`).
//!
//! Antes as chaves (`"hotkey"`, `"autoPaste"`, …) e o padrão de leitura/escrita
//! ficavam espalhados por `commands.rs` e `lib.rs`. Aqui elas viram constantes e
//! helpers tipados — uma única fonte da verdade para o store.

use serde_json::Value;
use tauri::AppHandle;
use tauri_plugin_store::StoreExt;

use crate::error::AppError;

pub const STORE_FILE: &str = "settings.json";

pub const KEY_HOTKEY: &str = "hotkey";
pub const KEY_AUTO_PASTE: &str = "autoPaste";

/// Lê uma string do store, ou `None` se ausente/ilegível.
pub fn get_string(app: &AppHandle, key: &str) -> Option<String> {
    app.store(STORE_FILE)
        .ok()?
        .get(key)?
        .as_str()
        .map(String::from)
}

/// Lê um booleano do store, ou `None` se ausente/ilegível.
pub fn get_bool(app: &AppHandle, key: &str) -> Option<bool> {
    app.store(STORE_FILE).ok()?.get(key)?.as_bool()
}

/// Grava um valor e persiste o store em disco.
pub fn set(app: &AppHandle, key: &str, value: Value) -> Result<(), AppError> {
    let store = app.store(STORE_FILE).map_err(AppError::msg)?;
    store.set(key, value);
    store.save().map_err(AppError::msg)?;
    Ok(())
}
