use base64::engine::general_purpose::STANDARD as B64;
use base64::Engine;
use clipboard_rs::common::{RustImage, RustImageData};
use tauri::State;

use crate::db;
use crate::error::AppError;
use crate::media;
use crate::AppState;

const THUMB_MAX_PX: u32 = 320;

/// Decifra a imagem sob demanda e devolve uma miniatura como data URI.
/// Chamado pelo frontend apenas quando o cartão entra na área visível.
#[tauri::command]
pub fn get_thumbnail(state: State<'_, AppState>, id: i64) -> Result<String, AppError> {
    if let Ok(mut cache) = state.thumb_cache() {
        if let Some(uri) = cache.get(&id) {
            return Ok(uri.clone());
        }
    }

    let path = {
        let conn = state.db()?;
        db::get_media_path(&conn, id)?
    }
    .ok_or("item não possui mídia")?;

    let plain = media::load_decrypted(std::path::Path::new(&path), &state.master_key)?;
    let image = RustImageData::from_bytes(&plain).map_err(AppError::msg)?;
    let png = image
        .thumbnail(THUMB_MAX_PX, THUMB_MAX_PX)
        .and_then(|t| t.to_png())
        .or_else(|_| image.to_png())
        .map_err(AppError::msg)?;
    let uri = format!("data:image/png;base64,{}", B64.encode(png.get_bytes()));

    if let Ok(mut cache) = state.thumb_cache() {
        // O LRU descarta sozinho a entrada menos usada ao exceder a capacidade.
        cache.put(id, uri.clone());
    }
    Ok(uri)
}
