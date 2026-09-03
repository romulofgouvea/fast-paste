mod commands;
#[cfg(test)]
mod contract;
mod crypto;
mod db;
mod error;
mod hotkey;
mod media;
mod settings;
mod watcher;

use std::num::NonZeroUsize;
use std::path::PathBuf;
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex, MutexGuard};

use lru::LruCache;
use rusqlite::Connection;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::Manager;
use tauri_plugin_global_shortcut::ShortcutState;

use crate::error::AppError;

/// Capacidade do cache LRU de miniaturas decifradas.
const THUMB_CACHE_CAP: usize = 64;

/// Arredonda os cantos da janela no macOS sem depender da `macOSPrivateApi`
/// do Tauri (que usa API privada e barra o app na Mac App Store).
///
/// Sem essa flag o `WKWebView` não fica transparente no macOS — mas não é o
/// que precisamos: deixamos o webview opaco e mascaramos a **camada nativa**
/// do `contentView` num retângulo arredondado (`cornerRadius` + `masksToBounds`,
/// tudo API pública). O fundo da janela vira transparente para os cantos
/// mostrarem o desktop e a sombra nativa acompanhar o retângulo arredondado.
///
/// O raio (16px) casa com o `rounded-2xl` do shell no front-end.
#[cfg(target_os = "macos")]
fn style_macos_window(window: &tauri::WebviewWindow) {
    use objc2::runtime::AnyObject;
    use objc2::{class, msg_send};

    let Ok(ptr) = window.ns_window() else {
        return;
    };
    let ns_window = ptr as *mut AnyObject;
    if ns_window.is_null() {
        return;
    }

    // SAFETY: `ns_window` é um `NSWindow` válido — as janelas são estáticas e
    // nunca destruídas. `contentView`/`layer` podem ser nil e são checados
    // antes de qualquer mensagem de retorno `()`. Roda na thread principal
    // (dentro do `setup`).
    unsafe {
        let _: () = msg_send![ns_window, setOpaque: false];
        let clear_color: *mut AnyObject = msg_send![class!(NSColor), clearColor];
        let _: () = msg_send![ns_window, setBackgroundColor: clear_color];
        let _: () = msg_send![ns_window, setHasShadow: true];

        let content_view: *mut AnyObject = msg_send![ns_window, contentView];
        if content_view.is_null() {
            return;
        }
        let _: () = msg_send![content_view, setWantsLayer: true];
        let layer: *mut AnyObject = msg_send![content_view, layer];
        if layer.is_null() {
            return;
        }
        let _: () = msg_send![layer, setCornerRadius: 16.0f64];
        let _: () = msg_send![layer, setMasksToBounds: true];
    }
}

pub struct AppState {
    pub db: Arc<Mutex<Connection>>,
    pub suppress_capture: Arc<AtomicBool>,
    pub master_key: [u8; 32],
    pub data_dir: PathBuf,
    pub current_hotkey: Mutex<String>,
    /// Cache LRU de miniaturas já decifradas (id → data URI): descarta a menos
    /// usada ao encher, em vez de zerar tudo.
    pub thumb_cache: Mutex<LruCache<i64, String>>,
    /// Janela em primeiro plano antes do FPaste abrir (para o auto-paste).
    pub last_focus: Mutex<Option<isize>>,
    pub auto_paste: Mutex<bool>,
}

/// Acesso aos mutexes do estado com erro tipado, no lugar do antigo
/// `state.db.lock().map_err(|_| "db lock poisoned")?` repetido em cada comando.
impl AppState {
    pub fn db(&self) -> Result<MutexGuard<'_, Connection>, AppError> {
        self.db.lock().map_err(|_| AppError::LockPoisoned("db"))
    }

    pub fn hotkey(&self) -> Result<MutexGuard<'_, String>, AppError> {
        self.current_hotkey
            .lock()
            .map_err(|_| AppError::LockPoisoned("hotkey"))
    }

    pub fn auto_paste(&self) -> Result<MutexGuard<'_, bool>, AppError> {
        self.auto_paste
            .lock()
            .map_err(|_| AppError::LockPoisoned("auto_paste"))
    }

    pub fn thumb_cache(&self) -> Result<MutexGuard<'_, LruCache<i64, String>>, AppError> {
        self.thumb_cache
            .lock()
            .map_err(|_| AppError::LockPoisoned("thumb_cache"))
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_autostart::init(tauri_plugin_autostart::MacosLauncher::LaunchAgent, Some(vec![])))
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            hotkey::toggle_main_window_centered(app);
        }))
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
            // macOS: cantos arredondados + sombra nativa nas janelas estáticas.
            #[cfg(target_os = "macos")]
            {
                for label in ["main", "settings"] {
                    if let Some(window) = app.get_webview_window(label) {
                        style_macos_window(&window);
                    }
                }
            }

            let master_key =
                crypto::get_or_create_master_key().map_err(|e| format!("master key: {e}"))?;

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

            let mut stored_hotkey = settings::get_string(app.handle(), settings::KEY_HOTKEY)
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
                thumb_cache: Mutex::new(LruCache::new(
                    NonZeroUsize::new(THUMB_CACHE_CAP).expect("cache cap > 0"),
                )),
                last_focus: Mutex::new(None),
                auto_paste: Mutex::new(
                    settings::get_bool(app.handle(), settings::KEY_AUTO_PASTE).unwrap_or(false),
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
        // FPaste é um app residente na bandeja: fechar a janela principal ou
        // a de configurações (Alt+F4, X) só deve escondê-la, nunca destruí-la
        // — ambas são declaradas estaticamente e reabertas mostrando de novo;
        // destruí-las quebraria a próxima hotkey / o próximo "abrir settings".
        .on_window_event(|window, event| {
            if window.label() == "main" || window.label() == "settings" {
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
            commands::hide_settings,
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
            commands::open_linux_keyboard_settings,
            commands::macos_accessibility_trusted,
            commands::open_macos_accessibility_settings,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|_app_handle, _event| {
        });
}
