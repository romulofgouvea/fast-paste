use std::io::{Read as _, Write as _};

use base64::engine::general_purpose::STANDARD as B64;
use base64::Engine;
use serde::Serialize;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

use crate::db::{self, ClipKind};
use crate::error::AppError;
use crate::AppState;

#[derive(Serialize)]
pub struct ImportSummary {
    pub imported: i64,
    pub skipped: i64,
}

/// Linha crua lida do banco de um backup: (type, content, preview_text,
/// secure_file_path, hash, size_bytes).
type BackupRow = (
    ClipKind,
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
