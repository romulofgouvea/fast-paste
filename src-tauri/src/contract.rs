//! Guarda de contrato Rust↔TS (alternativa sem dependências ao codegen do
//! tauri-specta, que só suporta Tauri 2 em crates pré-lançamento).
//!
//! Garante que os DTOs serializam exatamente com as chaves que o frontend
//! espera em `src/lib/api.ts`. Qualquer rename, campo novo ou remoção no Rust
//! quebra estes testes — sinalizando que o TypeScript precisa acompanhar, em
//! vez de virar um bug silencioso em runtime.

use std::collections::BTreeSet;

use serde::Serialize;

use crate::commands::{HistoryPage, ImportSummary, StorageInfo};
use crate::db::{ClipItem, ClipKind, Group};

fn keys<T: Serialize>(value: &T) -> BTreeSet<String> {
    serde_json::to_value(value)
        .unwrap()
        .as_object()
        .expect("DTO deve serializar como objeto")
        .keys()
        .cloned()
        .collect()
}

fn expected(fields: &[&str]) -> BTreeSet<String> {
    fields.iter().map(|s| s.to_string()).collect()
}

#[test]
fn clip_item_contract() {
    let item = ClipItem {
        id: 1,
        kind: ClipKind::Text,
        preview: None,
        content: None,
        pinned: false,
        timestamp: 0,
        has_media: false,
        group_id: None,
    };
    assert_eq!(
        keys(&item),
        expected(&[
            "id", "type", "preview", "content", "pinned", "timestamp", "hasMedia", "groupId",
        ])
    );
}

#[test]
fn clip_kind_serializes_lowercase() {
    // Deve casar 1:1 com o union ClipType do TS.
    for (kind, expected) in [
        (ClipKind::Text, "text"),
        (ClipKind::Link, "link"),
        (ClipKind::Code, "code"),
        (ClipKind::Image, "image"),
        (ClipKind::Files, "files"),
    ] {
        assert_eq!(serde_json::to_value(kind).unwrap(), serde_json::json!(expected));
    }
}

#[test]
fn group_contract() {
    let g = Group { id: 1, name: "x".into() };
    assert_eq!(keys(&g), expected(&["id", "name"]));
}

#[test]
fn history_page_contract() {
    let p = HistoryPage { items: vec![], has_more: false };
    assert_eq!(keys(&p), expected(&["items", "hasMore"]));
}

#[test]
fn storage_info_contract() {
    let s = StorageInfo { path: String::new(), db_size_bytes: 0, item_count: 0 };
    assert_eq!(keys(&s), expected(&["path", "dbSizeBytes", "itemCount"]));
}

#[test]
fn import_summary_contract() {
    let s = ImportSummary { imported: 0, skipped: 0 };
    assert_eq!(keys(&s), expected(&["imported", "skipped"]));
}
