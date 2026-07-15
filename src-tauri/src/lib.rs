mod commands;
mod crypto;
mod db;
mod hotkey;
mod media;
mod watcher;

use std::path::PathBuf;
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex};

use rusqlite::Connection;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::Manager;
use tauri_plugin_global_shortcut::ShortcutState;
use tauri_plugin_store::StoreExt;

pub struct AppState {
    pub db: Arc<Mutex<Connection>>,
    pub suppress_capture: Arc<AtomicBool>,
    pub master_key: [u8; 32],
    pub data_dir: PathBuf,
    pub current_hotkey: Mutex<String>,
    /// Cache simples de miniaturas já decifradas (id → data URI).
    pub thumb_cache: Mutex<std::collections::HashMap<i64, String>>,
    /// Janela em primeiro plano antes do FPaste abrir (para o auto-paste).
    pub last_focus: Mutex<Option<isize>>,
    pub auto_paste: Mutex<bool>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, _shortcut, event| {
                    if event.state() == ShortcutState::Pressed {
                        hotkey::toggle_main_window(app);
                    }
                })
                .build(),
        )
        .setup(|app| {
            let master_key = crypto::get_or_create_master_key()
                .map_err(|e| format!("master key: {e}"))?;

            // %APPDATA%\fpaste\data (e equivalentes no macOS/Linux), conforme a spec.
            let data_dir = app.path().data_dir()?.join("fpaste").join("data");
            let conn = db::open(&data_dir, &master_key).map_err(|e| format!("db: {e}"))?;
            let db = Arc::new(Mutex::new(conn));
            let suppress = Arc::new(AtomicBool::new(false));

            watcher::spawn(
                app.handle().clone(),
                db.clone(),
                suppress.clone(),
                master_key,
                data_dir.clone(),
            );

            let mut stored_hotkey = app
                .store("settings.json")
                .ok()
                .and_then(|s| s.get("hotkey"))
                .and_then(|v| v.as_str().map(String::from))
                .unwrap_or_else(hotkey::default_hotkey);
            if let Err(e) = hotkey::swap_hotkey(app.handle(), &stored_hotkey, None) {
                eprintln!("fpaste: hotkey '{stored_hotkey}' failed ({e}), falling back to default");
                stored_hotkey = hotkey::default_hotkey();
                hotkey::swap_hotkey(app.handle(), &stored_hotkey, None)?;
            }
            println!("fpaste: hotkey global registrada: {stored_hotkey}");

            app.manage(AppState {
                db,
                suppress_capture: suppress,
                master_key,
                data_dir,
                current_hotkey: Mutex::new(stored_hotkey),
                thumb_cache: Mutex::new(std::collections::HashMap::new()),
                last_focus: Mutex::new(None),
                auto_paste: Mutex::new(
                    app.store("settings.json")
                        .ok()
                        .and_then(|s| s.get("autoPaste"))
                        .and_then(|v| v.as_bool())
                        .unwrap_or(false),
                ),
            });

            let open = MenuItem::with_id(app, "open", "Abrir FPaste", true, None::<&str>)?;
            let settings = MenuItem::with_id(app, "settings", "Configurações", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Sair", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &settings, &quit])?;
            TrayIconBuilder::with_id("fpaste-tray")
                .icon(app.default_window_icon().cloned().expect("bundled icon"))
                .tooltip("FPaste")
                .menu(&menu)
                .show_menu_on_left_click(false)
                // Clique com o botão esquerdo no ícone abre centralizado na tela
                // (diferente da hotkey global, que abre sob o cursor).
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click {
                        button: tauri::tray::MouseButton::Left,
                        button_state: tauri::tray::MouseButtonState::Up,
                        ..
                    } = event
                    {
                        hotkey::toggle_main_window_centered(tray.app_handle());
                    }
                })
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "open" => hotkey::toggle_main_window_centered(app),
                    "settings" => {
                        let _ = commands::open_settings(app.clone());
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        // FPaste é um app residente na bandeja: fechar a janela principal
        // (Alt+F4, X) só deve escondê-la, nunca destruí-la — do contrário a
        // próxima hotkey não encontraria mais a janela para reabrir.
        .on_window_event(|window, event| {
            if window.label() == "main" {
                if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    let _ = window.hide();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_history,
            commands::select_item,
            commands::delete_item,
            commands::hide_window,
            commands::set_hotkey,
            commands::get_hotkey,
            commands::suspend_hotkey,
            commands::resume_hotkey,
            commands::get_storage_info,
            commands::clear_history,
            commands::open_settings,
            commands::get_thumbnail,
            commands::toggle_pin,
            commands::list_groups,
            commands::create_group,
            commands::delete_group,
            commands::set_item_group,
            commands::paste_text,
            commands::set_auto_paste,
            commands::get_auto_paste,
            commands::export_backup,
            commands::import_backup,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        // Defesa extra: mesmo que todas as janelas fechem, o FPaste continua
        // vivo na bandeja — só "Sair" no menu do tray encerra o processo.
        .run(|_app_handle, event| {
            if let tauri::RunEvent::ExitRequested { api, .. } = event {
                api.prevent_exit();
            }
        });
}
