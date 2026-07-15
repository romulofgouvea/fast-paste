use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

use base64::engine::general_purpose::STANDARD as B64;
use base64::Engine;
use rusqlite::{params_from_iter, Connection, OptionalExtension};
use serde::Serialize;

use crate::error::AppError;

const SCHEMA: &str = "
CREATE TABLE IF NOT EXISTS clipboard_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  content TEXT,
  preview_text TEXT,
  secure_file_path TEXT,
  hash TEXT NOT NULL,
  size_bytes INTEGER NOT NULL DEFAULT 0,
  pinned INTEGER NOT NULL DEFAULT 0,
  group_id INTEGER,
  timestamp INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_ts ON clipboard_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_history_hash ON clipboard_history(hash);

CREATE TABLE IF NOT EXISTS groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL
);
";

#[derive(Serialize, Clone)]
pub struct ClipItem {
    pub id: i64,
    #[serde(rename = "type")]
    pub kind: String,
    pub preview: Option<String>,
    pub content: Option<String>,
    pub pinned: bool,
    pub timestamp: i64,
    #[serde(rename = "hasMedia")]
    pub has_media: bool,
    #[serde(rename = "groupId")]
    pub group_id: Option<i64>,
}

#[derive(Serialize, Clone)]
pub struct Group {
    pub id: i64,
    pub name: String,
}

pub struct NewItem {
    pub kind: String,
    pub content: Option<String>,
    pub preview: Option<String>,
    pub secure_file_path: Option<String>,
    pub hash: String,
    pub size_bytes: i64,
}

pub fn now_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

/// Abre (ou cria) o banco cifrado com SQLCipher. A chave-mestra é aplicada
/// como passphrase via PRAGMA key antes de qualquer acesso.
pub fn open(dir: &Path, master_key: &[u8; 32]) -> Result<Connection, AppError> {
    std::fs::create_dir_all(dir)?;
    let conn = Connection::open(dir.join("fpaste.db"))?;
    conn.pragma_update(None, "key", B64.encode(master_key))?;
    conn.execute_batch(SCHEMA)?;
    Ok(conn)
}

/// Se um item com este hash já existe, promove-o ao topo (timestamp) e
/// devolve seu id — deduplicação estilo Ditto.
pub fn touch_by_hash(conn: &Connection, hash: &str) -> Result<Option<i64>, AppError> {
    let existing: Option<i64> = conn
        .query_row(
            "SELECT id FROM clipboard_history WHERE hash = ?1 LIMIT 1",
            [hash],
            |row| row.get(0),
        )
        .optional()?;
    if let Some(id) = existing {
        conn.execute(
            "UPDATE clipboard_history SET timestamp = ?1 WHERE id = ?2",
            rusqlite::params![now_ms(), id],
        )?;
    }
    Ok(existing)
}

/// Insere um item novo; se o hash já existe, apenas promove o item existente.
/// Retorna (id, criado_agora).
pub fn insert_or_touch(conn: &Connection, item: &NewItem) -> Result<(i64, bool), AppError> {
    if let Some(id) = touch_by_hash(conn, &item.hash)? {
        return Ok((id, false));
    }

    conn.execute(
        "INSERT INTO clipboard_history (type, content, preview_text, secure_file_path, hash, size_bytes, timestamp)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        rusqlite::params![
            item.kind,
            item.content,
            item.preview,
            item.secure_file_path,
            item.hash,
            item.size_bytes,
            now_ms()
        ],
    )?;
    Ok((conn.last_insert_rowid(), true))
}

/// Paginação por deslocamento conforme a spec. Busca LIMIT size+1 para
/// detectar se há mais páginas sem um COUNT extra.
pub fn query_page(
    conn: &Connection,
    page: u32,
    size: u32,
    search: Option<&str>,
    kind: Option<&str>,
    group_id: Option<i64>,
) -> Result<(Vec<ClipItem>, bool), AppError> {
    let mut sql = String::from(
        "SELECT id, type, preview_text, content, secure_file_path, pinned, timestamp, group_id \
         FROM clipboard_history",
    );
    let mut wheres: Vec<&str> = Vec::new();
    let mut params: Vec<String> = Vec::new();

    if let Some(q) = search.filter(|q| !q.trim().is_empty()) {
        wheres.push("(content LIKE ? OR preview_text LIKE ?)");
        let pattern = format!("%{}%", q.trim());
        params.push(pattern.clone());
        params.push(pattern);
    }
    if let Some(k) = kind.filter(|k| !k.is_empty()) {
        wheres.push("type = ?");
        params.push(k.to_string());
    }
    if let Some(g) = group_id {
        wheres.push("group_id = ?");
        params.push(g.to_string());
    }
    if !wheres.is_empty() {
        sql.push_str(" WHERE ");
        sql.push_str(&wheres.join(" AND "));
    }
    sql.push_str(&format!(
        " ORDER BY pinned DESC, timestamp DESC LIMIT {} OFFSET {}",
        size as i64 + 1,
        page as i64 * size as i64
    ));

    let mut stmt = conn.prepare(&sql)?;
    let rows = stmt
        .query_map(params_from_iter(params.iter()), |row| {
            let file_path: Option<String> = row.get(4)?;
            Ok(ClipItem {
                id: row.get(0)?,
                kind: row.get(1)?,
                preview: row.get(2)?,
                content: row.get(3)?,
                pinned: row.get::<_, i64>(5)? != 0,
                timestamp: row.get(6)?,
                has_media: file_path.is_some(),
                group_id: row.get(7)?,
            })
        })?
        .collect::<Result<Vec<_>, _>>()?;

    let has_more = rows.len() > size as usize;
    let items = rows.into_iter().take(size as usize).collect();
    Ok((items, has_more))
}

/// Alterna o estado de fixado do item e devolve o novo valor.
pub fn toggle_pin(conn: &Connection, id: i64) -> Result<bool, AppError> {
    conn.execute(
        "UPDATE clipboard_history SET pinned = 1 - pinned WHERE id = ?1",
        [id],
    )?;
    let pinned = conn.query_row(
        "SELECT pinned FROM clipboard_history WHERE id = ?1",
        [id],
        |row| row.get::<_, i64>(0),
    )?;
    Ok(pinned != 0)
}

pub fn set_item_group(conn: &Connection, id: i64, group_id: Option<i64>) -> Result<(), AppError> {
    conn.execute(
        "UPDATE clipboard_history SET group_id = ?1 WHERE id = ?2",
        rusqlite::params![group_id, id],
    )?;
    Ok(())
}

pub fn list_groups(conn: &Connection) -> Result<Vec<Group>, AppError> {
    let mut stmt = conn.prepare("SELECT id, name FROM groups ORDER BY name COLLATE NOCASE")?;
    let groups = stmt
        .query_map([], |row| {
            Ok(Group {
                id: row.get(0)?,
                name: row.get(1)?,
            })
        })?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(groups)
}

pub fn create_group(conn: &Connection, name: &str) -> Result<i64, AppError> {
    conn.execute(
        "INSERT INTO groups (name, created_at) VALUES (?1, ?2)",
        rusqlite::params![name, now_ms()],
    )?;
    Ok(conn.last_insert_rowid())
}

pub fn delete_group(conn: &Connection, id: i64) -> Result<(), AppError> {
    conn.execute(
        "UPDATE clipboard_history SET group_id = NULL WHERE group_id = ?1",
        [id],
    )?;
    conn.execute("DELETE FROM groups WHERE id = ?1", [id])?;
    Ok(())
}

pub fn get_content(conn: &Connection, id: i64) -> Result<Option<String>, AppError> {
    let content = conn.query_row(
        "SELECT content FROM clipboard_history WHERE id = ?1",
        [id],
        |row| row.get(0),
    )?;
    Ok(content)
}

pub fn get_media_path(conn: &Connection, id: i64) -> Result<Option<String>, AppError> {
    let path = conn.query_row(
        "SELECT secure_file_path FROM clipboard_history WHERE id = ?1",
        [id],
        |row| row.get(0),
    )?;
    Ok(path)
}

pub fn delete(conn: &Connection, id: i64) -> Result<Option<String>, AppError> {
    let file_path: Option<String> = conn
        .query_row(
            "SELECT secure_file_path FROM clipboard_history WHERE id = ?1",
            [id],
            |row| row.get(0),
        )
        .optional()?
        .flatten();
    conn.execute("DELETE FROM clipboard_history WHERE id = ?1", [id])?;
    Ok(file_path)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mem_db() -> Connection {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute_batch(SCHEMA).unwrap();
        conn
    }

    fn text_item(text: &str) -> NewItem {
        NewItem {
            kind: "text".into(),
            content: Some(text.into()),
            preview: Some(text.into()),
            secure_file_path: None,
            hash: crate::crypto::sha256_hex(text.as_bytes()),
            size_bytes: text.len() as i64,
        }
    }

    #[test]
    fn dedup_touches_existing_row() {
        let conn = mem_db();
        let (id1, created1) = insert_or_touch(&conn, &text_item("hello")).unwrap();
        let (id2, created2) = insert_or_touch(&conn, &text_item("hello")).unwrap();
        assert!(created1);
        assert!(!created2);
        assert_eq!(id1, id2);
        let count: i64 = conn
            .query_row("SELECT COUNT(*) FROM clipboard_history", [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 1);
    }

    #[test]
    fn pagination_reports_has_more() {
        let conn = mem_db();
        for i in 0..25 {
            insert_or_touch(&conn, &text_item(&format!("item {}", i))).unwrap();
        }
        let (items, has_more) = query_page(&conn, 0, 20, None, None, None).unwrap();
        assert_eq!(items.len(), 20);
        assert!(has_more);
        let (items, has_more) = query_page(&conn, 1, 20, None, None, None).unwrap();
        assert_eq!(items.len(), 5);
        assert!(!has_more);
    }

    #[test]
    fn search_and_type_filter() {
        let conn = mem_db();
        insert_or_touch(&conn, &text_item("banana split")).unwrap();
        insert_or_touch(&conn, &text_item("apple pie")).unwrap();
        let mut link = text_item("https://example.com");
        link.kind = "link".into();
        insert_or_touch(&conn, &link).unwrap();

        let (items, _) = query_page(&conn, 0, 20, Some("banana"), None, None).unwrap();
        assert_eq!(items.len(), 1);
        let (items, _) = query_page(&conn, 0, 20, None, Some("link"), None).unwrap();
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].kind, "link");
    }

    #[test]
    fn pin_toggle_and_group_assignment() {
        let conn = mem_db();
        let (id, _) = insert_or_touch(&conn, &text_item("pin me")).unwrap();
        assert!(toggle_pin(&conn, id).unwrap());
        assert!(!toggle_pin(&conn, id).unwrap());

        let gid = create_group(&conn, "Trabalho").unwrap();
        set_item_group(&conn, id, Some(gid)).unwrap();
        let (items, _) = query_page(&conn, 0, 20, None, None, Some(gid)).unwrap();
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].group_id, Some(gid));

        delete_group(&conn, gid).unwrap();
        let (items, _) = query_page(&conn, 0, 20, None, None, None).unwrap();
        assert_eq!(items[0].group_id, None);
    }
}
