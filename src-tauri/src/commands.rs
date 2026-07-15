use std::io::{Read as _, Write as _};
use std::sync::atomic::Ordering;

use base64::engine::general_purpose::STANDARD as B64;
use base64::Engine;
use clipboard_rs::common::{RustImage, RustImageData};
use clipboard_rs::{Clipboard, ClipboardContext};
use serde::Serialize;
use tauri::{AppHandle, Manager, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_store::StoreExt;

use crate::db::{self, ClipItem};
use crate::error::AppError;
use crate::AppState;
use crate::{hotkey, media};

const THUMB_MAX_PX: u32 = 320;
const THUMB_CACHE_CAP: usize = 64;

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

/// Copia o item escolhido de volta para o clipboard do SO e esconde a janela.
#[tauri::command]
pub fn select_item(app: AppHandle, state: State<'_, AppState>, id: i64) -> Result<(), AppError> {
    let (content, media_path) = {
        let conn = state.db()?;
        (db::get_content(&conn, id)?, db::get_media_path(&conn, id)?)
    };

    // O watcher deve ignorar esta escrita — é o próprio FPaste copiando.
    state.suppress_capture.store(true, Ordering::SeqCst);
    let ctx = ClipboardContext::new().map_err(AppError::msg)?;
    if let Some(text) = content {
        ctx.set_text(text).map_err(AppError::msg)?;
    } else if let Some(path) = media_path {
        let plain = media::load_decrypted(std::path::Path::new(&path), &state.master_key)?;
        let image = RustImageData::from_bytes(&plain).map_err(AppError::msg)?;
        ctx.set_image(image).map_err(AppError::msg)?;
    } else {
        return Err(AppError::msg("item sem conteúdo"));
    }

    if let Some(window) = app.get_webview_window("main") {
        let _ = window.hide();
    }
    maybe_auto_paste(&state);
    Ok(())
}

/// Copia texto arbitrário direto para o clipboard (usado pelo menu de
/// transformações: "colar como texto puro", "inverter maiúsc/minúsc" etc.)
/// sem passar pelo histórico.
#[tauri::command]
pub fn paste_text(app: AppHandle, state: State<'_, AppState>, text: String) -> Result<(), AppError> {
    state.suppress_capture.store(true, Ordering::SeqCst);
    let ctx = ClipboardContext::new().map_err(AppError::msg)?;
    ctx.set_text(text).map_err(AppError::msg)?;
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.hide();
    }
    maybe_auto_paste(&state);
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

#[tauri::command]
pub fn set_auto_paste(app: AppHandle, state: State<'_, AppState>, enabled: bool) -> Result<(), AppError> {
    *state.auto_paste()? = enabled;
    let store = app.store("settings.json").map_err(AppError::msg)?;
    store.set("autoPaste", serde_json::json!(enabled));
    store.save().map_err(AppError::msg)?;
    Ok(())
}

#[tauri::command]
pub fn get_auto_paste(state: State<'_, AppState>) -> Result<bool, AppError> {
    Ok(*state.auto_paste()?)
}

#[tauri::command]
pub fn toggle_pin(state: State<'_, AppState>, id: i64) -> Result<bool, AppError> {
    let conn = state.db()?;
    db::toggle_pin(&conn, id)
}

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
pub fn set_item_group(state: State<'_, AppState>, id: i64, group_id: Option<i64>) -> Result<(), AppError> {
    let conn = state.db()?;
    db::set_item_group(&conn, id, group_id)
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
pub fn hide_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.hide();
    }
}

/// Valida, registra e persiste uma nova hotkey global vinda do key recorder.
#[tauri::command]
pub fn set_hotkey(app: AppHandle, state: State<'_, AppState>, shortcut: String) -> Result<(), AppError> {
    let mut current = state.hotkey()?;
    hotkey::swap_hotkey(&app, &shortcut, Some(current.as_str()))?;
    *current = shortcut.clone();
    let store = app.store("settings.json").map_err(AppError::msg)?;
    store.set("hotkey", serde_json::json!(shortcut));
    store.save().map_err(AppError::msg)?;
    Ok(())
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

#[derive(Serialize)]
pub struct StorageInfo {
    pub path: String,
    #[serde(rename = "dbSizeBytes")]
    pub db_size_bytes: u64,
    #[serde(rename = "itemCount")]
    pub item_count: i64,
}

#[tauri::command]
pub fn get_storage_info(state: State<'_, AppState>) -> Result<StorageInfo, AppError> {
    let db_path = state.data_dir.join("fpaste.db");
    let db_size_bytes = std::fs::metadata(&db_path).map(|m| m.len()).unwrap_or(0);
    let conn = state.db()?;
    let item_count: i64 =
        conn.query_row("SELECT COUNT(*) FROM clipboard_history", [], |r| r.get(0))?;
    Ok(StorageInfo {
        path: db_path.display().to_string(),
        db_size_bytes,
        item_count,
    })
}

#[tauri::command]
pub fn clear_history(state: State<'_, AppState>) -> Result<(), AppError> {
    {
        let conn = state.db()?;
        conn.execute("DELETE FROM clipboard_history", [])?;
    }
    let _ = std::fs::remove_dir_all(state.data_dir.join("media"));
    Ok(())
}

/// Decifra a imagem sob demanda e devolve uma miniatura como data URI.
/// Chamado pelo frontend apenas quando o cartão entra na área visível.
#[tauri::command]
pub fn get_thumbnail(state: State<'_, AppState>, id: i64) -> Result<String, AppError> {
    if let Ok(cache) = state.thumb_cache() {
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
        if cache.len() >= THUMB_CACHE_CAP {
            cache.clear();
        }
        cache.insert(id, uri.clone());
    }
    Ok(uri)
}

#[derive(Serialize)]
pub struct ImportSummary {
    pub imported: i64,
    pub skipped: i64,
}

/// Linha crua lida do banco de um backup: (type, content, preview_text,
/// secure_file_path, hash, size_bytes).
type BackupRow = (
    String,
    Option<String>,
    Option<String>,
    Option<String>,
    String,
    i64,
);

/// Gera um snapshot consistente do banco cifrado (VACUUM INTO) e compacta
/// junto com a pasta de mídia em um .zip, opcionalmente protegido por senha
/// (AES-256 por entrada). O conteúdo já sai cifrado — a senha do zip é uma
/// segunda camada para o trânsito/compartilhamento do arquivo de backup.
#[tauri::command]
pub fn export_backup(app: AppHandle, state: State<'_, AppState>, password: Option<String>) -> Result<String, AppError> {
    let dest = app
        .dialog()
        .file()
        .add_filter("Backup FPaste", &["zip"])
        .set_file_name("fpaste-backup.zip")
        .blocking_save_file()
        .ok_or("Exportação cancelada")?;
    let dest_path = dest.into_path().map_err(AppError::msg)?;

    let snapshot_path = state.data_dir.join("fpaste.backup.tmp.db");
    let _ = std::fs::remove_file(&snapshot_path);
    {
        let conn = state.db()?;
        conn.execute(
            "VACUUM INTO ?1",
            [snapshot_path.to_string_lossy().as_ref()],
        )?;
    }

    let file = std::fs::File::create(&dest_path)?;
    let mut zip = zip::ZipWriter::new(file);

    let write_entry = |zip: &mut zip::ZipWriter<std::fs::File>, name: &str, bytes: &[u8], pw: &Option<String>| -> Result<(), AppError> {
        let opts: zip::write::FileOptions<()> = zip::write::FileOptions::default()
            .compression_method(zip::CompressionMethod::Deflated);
        let opts = match pw {
            Some(p) => opts.with_aes_encryption(zip::AesMode::Aes256, p),
            None => opts,
        };
        zip.start_file(name, opts)?;
        zip.write_all(bytes)?;
        Ok(())
    };

    let db_bytes = std::fs::read(&snapshot_path)?;
    write_entry(&mut zip, "fpaste.db", &db_bytes, &password)?;

    let media_dir = state.data_dir.join("media");
    if media_dir.is_dir() {
        for entry in std::fs::read_dir(&media_dir)? {
            let entry = entry?;
            if !entry.path().is_file() {
                continue;
            }
            let bytes = std::fs::read(entry.path())?;
            let name = format!("media/{}", entry.file_name().to_string_lossy());
            write_entry(&mut zip, &name, &bytes, &password)?;
        }
    }
    zip.finish()?;
    let _ = std::fs::remove_file(&snapshot_path);
    Ok(dest_path.display().to_string())
}

/// Importa um backup gerado pelo FPaste, mesclando por hash com o histórico
/// atual para não duplicar itens já existentes (spec §5.3).
#[tauri::command]
pub fn import_backup(app: AppHandle, state: State<'_, AppState>, password: Option<String>) -> Result<ImportSummary, AppError> {
    let src = app
        .dialog()
        .file()
        .add_filter("Backup FPaste", &["zip"])
        .blocking_pick_file()
        .ok_or("Importação cancelada")?;
    let src_path = src.into_path().map_err(AppError::msg)?;

    let file = std::fs::File::open(&src_path)?;
    let mut archive = zip::ZipArchive::new(file)?;

    let read_entry = |archive: &mut zip::ZipArchive<std::fs::File>, name: &str, pw: &Option<String>| -> Result<Vec<u8>, AppError> {
        let mut zf = match pw {
            Some(p) => archive
                .by_name_decrypt(name, p.as_bytes())
                .map_err(|_| AppError::msg("backup inválido ou senha incorreta"))?,
            None => archive.by_name(name)?,
        };
        let mut buf = Vec::new();
        zf.read_to_end(&mut buf)?;
        Ok(buf)
    };

    let db_bytes = read_entry(&mut archive, "fpaste.db", &password)?;
    let tmp_db = state.data_dir.join("fpaste.import.tmp.db");
    std::fs::write(&tmp_db, &db_bytes)?;

    let backup_conn = rusqlite::Connection::open(&tmp_db)?;
    backup_conn.pragma_update(None, "key", B64.encode(state.master_key))?;
    backup_conn
        .query_row("SELECT count(*) FROM clipboard_history", [], |r| r.get::<_, i64>(0))
        .map_err(|e| AppError::msg(format!("backup inválido ou de outra instalação do FPaste: {e}")))?;

    let rows: Vec<BackupRow> = {
        let mut stmt = backup_conn
            .prepare("SELECT type, content, preview_text, secure_file_path, hash, size_bytes FROM clipboard_history")?;
        let collected = stmt
            .query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?, r.get(5)?)))?
            .collect::<Result<_, _>>()?;
        collected
    };
    drop(backup_conn);
    let _ = std::fs::remove_file(&tmp_db);

    let mut imported = 0i64;
    let mut skipped = 0i64;
    let media_dir = state.data_dir.join("media");
    let conn = state.db()?;
    for (kind, content, preview, old_file_path, hash, size) in rows {
        if db::touch_by_hash(&conn, &hash)?.is_some() {
            skipped += 1;
            continue;
        }
        let new_file_path = match &old_file_path {
            Some(fp) => {
                let fname = std::path::Path::new(fp)
                    .file_name()
                    .map(|f| f.to_string_lossy().to_string())
                    .ok_or("nome de arquivo de mídia inválido no backup")?;
                let zip_entry = format!("media/{fname}");
                let bytes = read_entry(&mut archive, &zip_entry, &password)?;
                std::fs::create_dir_all(&media_dir)?;
                let dest = media_dir.join(&fname);
                std::fs::write(&dest, &bytes)?;
                Some(dest.display().to_string())
            }
            None => None,
        };
        db::insert_or_touch(
            &conn,
            &db::NewItem {
                kind,
                content,
                preview,
                secure_file_path: new_file_path,
                hash,
                size_bytes: size,
            },
        )?;
        imported += 1;
    }

    Ok(ImportSummary { imported, skipped })
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
