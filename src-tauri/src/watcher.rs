use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use std::path::PathBuf;

use clipboard_rs::common::RustImage;
use clipboard_rs::{
    Clipboard, ClipboardContext, ClipboardHandler, ClipboardWatcher, ClipboardWatcherContext,
    ContentFormat,
};
use rusqlite::Connection;
use tauri::{AppHandle, Emitter};

use crate::db::ClipKind;
use crate::error::AppError;
use crate::{crypto, db, media};

const PREVIEW_LEN: usize = 300;

/// Classifica o conteúdo textual copiado em `Link`, `Code` ou `Text`.
pub fn classify_text(text: &str) -> ClipKind {
    let trimmed = text.trim();
    if is_url(trimmed) {
        return ClipKind::Link;
    }
    if looks_like_code(trimmed) {
        return ClipKind::Code;
    }
    ClipKind::Text
}

fn is_url(text: &str) -> bool {
    if text.lines().count() != 1 {
        return false;
    }
    (text.starts_with("http://") || text.starts_with("https://") || text.starts_with("www."))
        && !text.contains(char::is_whitespace)
}

/// Heurística leve: multilinha + sinais estruturais típicos de código.
fn looks_like_code(text: &str) -> bool {
    let lines: Vec<&str> = text.lines().collect();
    if lines.len() < 2 {
        return false;
    }
    let mut score = 0;
    if text.contains('{') && text.contains('}') {
        score += 1;
    }
    let semicolon_endings = lines
        .iter()
        .filter(|l| {
            let t = l.trim_end();
            t.ends_with(';') || t.ends_with('{') || t.ends_with('}')
        })
        .count();
    if semicolon_endings * 2 >= lines.len() {
        score += 1;
    }
    let indented = lines
        .iter()
        .filter(|l| l.starts_with("    ") || l.starts_with('\t'))
        .count();
    if indented * 3 >= lines.len() {
        score += 1;
    }
    const KEYWORDS: [&str; 12] = [
        "fn ",
        "def ",
        "function ",
        "import ",
        "const ",
        "let ",
        "class ",
        "#include",
        "pub ",
        "return ",
        "if (",
        "=> ",
    ];
    if lines.iter().any(|l| {
        KEYWORDS
            .iter()
            .any(|k| l.trim_start().starts_with(k) || l.contains(k))
    }) {
        score += 1;
    }
    score >= 2
}

fn make_preview(text: &str) -> String {
    text.chars().take(PREVIEW_LEN).collect()
}

struct Monitor {
    app: AppHandle,
    db: Arc<Mutex<Connection>>,
    suppress: Arc<AtomicBool>,
    ctx: ClipboardContext,
    master_key: [u8; 32],
    data_dir: PathBuf,
}

impl Monitor {
    fn capture_text(&self) -> Result<bool, AppError> {
        let mut text_opt = None;
        for _ in 0..5 {
            if let Ok(t) = self.ctx.get_text() {
                text_opt = Some(t);
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
        let text = match text_opt {
            Some(t) => t,
            None => return Ok(false),
        };
        if text.trim().is_empty() {
            return Ok(false);
        }
        let item = db::NewItem {
            kind: classify_text(&text),
            preview: Some(make_preview(&text)),
            hash: crypto::sha256_hex(text.as_bytes()),
            size_bytes: text.len() as i64,
            content: Some(text),
            secure_file_path: None,
        };
        let conn = self.db.lock().map_err(|_| AppError::LockPoisoned("db"))?;
        db::insert_or_touch(&conn, &item)?;
        Ok(true)
    }

    /// Imagens nunca vão para dentro do banco: são cifradas em disco e o
    /// registro guarda apenas o caminho + hash SHA-256 (spec §5.4).
    fn capture_image(&self) -> Result<bool, AppError> {
        let mut image_opt = None;
        for _ in 0..5 {
            if let Ok(img) = self.ctx.get_image() {
                image_opt = Some(img);
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
        let image = match image_opt {
            Some(img) => img,
            None => return Ok(false),
        };
        let png = image.to_png().map_err(AppError::msg)?;
        let bytes = png.get_bytes();
        let hash = crypto::sha256_hex(bytes);

        let conn = self.db.lock().map_err(|_| AppError::LockPoisoned("db"))?;
        if db::touch_by_hash(&conn, &hash)?.is_some() {
            return Ok(true);
        }
        let path = media::save_encrypted(&self.data_dir, &self.master_key, bytes)?;
        let item = db::NewItem {
            kind: ClipKind::Image,
            content: None,
            preview: None,
            secure_file_path: Some(path.display().to_string()),
            hash,
            size_bytes: bytes.len() as i64,
        };
        db::insert_or_touch(&conn, &item)?;
        Ok(true)
    }
}

impl ClipboardHandler for Monitor {
    fn on_clipboard_change(&mut self) {
        // Cópias feitas pelo próprio FPaste (select_item) não devem recapturar.
        if self.suppress.swap(false, Ordering::SeqCst) {
            return;
        }
        let captured = if self.ctx.has(ContentFormat::Image) {
            self.capture_image()
        } else {
            self.capture_text()
        };
        match captured {
            Ok(true) => {
                let _ = self.app.emit("clipboard://new-item", ());
            }
            Ok(false) => {}
            Err(e) => eprintln!("fpaste: failed to persist clipboard item: {e}"),
        }
    }
}

/// Inicia a escuta do clipboard em uma thread dedicada (start_watch é bloqueante).
pub fn spawn(
    app: AppHandle,
    db: Arc<Mutex<Connection>>,
    suppress: Arc<AtomicBool>,
    master_key: [u8; 32],
    data_dir: PathBuf,
) {
    std::thread::spawn(move || {
        let Ok(ctx) = ClipboardContext::new() else {
            eprintln!("fpaste: could not create clipboard context");
            return;
        };
        let monitor = Monitor {
            app,
            db,
            suppress,
            ctx,
            master_key,
            data_dir,
        };
        match ClipboardWatcherContext::new() {
            Ok(mut watcher) => {
                watcher.add_handler(monitor);
                watcher.start_watch();
            }
            Err(e) => eprintln!("fpaste: could not start clipboard watcher: {e}"),
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classifies_urls() {
        assert_eq!(classify_text("https://tauri.app/start"), ClipKind::Link);
        assert_eq!(classify_text("www.example.com"), ClipKind::Link);
        assert_eq!(classify_text("visit https://a.com now"), ClipKind::Text);
    }

    #[test]
    fn classifies_code() {
        let rust = "fn main() {\n    println!(\"hi\");\n}";
        assert_eq!(classify_text(rust), ClipKind::Code);
        let js = "const x = 1;\nlet y = 2;\nreturn x + y;";
        assert_eq!(classify_text(js), ClipKind::Code);
    }

    #[test]
    fn classifies_plain_text() {
        assert_eq!(classify_text("uma nota simples"), ClipKind::Text);
        assert_eq!(
            classify_text("primeira linha\nsegunda linha de prosa"),
            ClipKind::Text
        );
    }
}
