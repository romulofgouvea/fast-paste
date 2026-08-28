use tauri::{AppHandle, Emitter, Manager, PhysicalPosition};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut};

use crate::error::AppError;
use crate::AppState;

/// Handle da janela que estava em primeiro plano antes do FPaste abrir —
/// usada pelo auto-paste para devolver o foco e simular Ctrl+V nela.
#[cfg(target_os = "windows")]
pub fn foreground_window() -> isize {
    #[link(name = "user32")]
    extern "system" {
        fn GetForegroundWindow() -> isize;
    }
    unsafe { GetForegroundWindow() }
}

#[cfg(not(target_os = "windows"))]
pub fn foreground_window() -> isize {
    0
}

/// Devolve o foco à janela que estava ativa antes do FPaste abrir e simula
/// Ctrl+V nela. Só implementado no Windows por enquanto — no macOS isso
/// exigiria permissão de Acessibilidade e no Linux depende do compositor
/// (X11 vs. Wayland), então lá o auto-paste fica desativado por ora.
#[cfg(target_os = "windows")]
pub fn paste_into(hwnd: isize) {
    use enigo::{Direction, Enigo, Key, Keyboard, Settings};

    #[link(name = "user32")]
    extern "system" {
        fn SetForegroundWindow(hwnd: isize) -> i32;
    }
    if hwnd == 0 {
        return;
    }
    unsafe {
        SetForegroundWindow(hwnd);
    }
    std::thread::sleep(std::time::Duration::from_millis(80));
    if let Ok(mut enigo) = Enigo::new(&Settings::default()) {
        let _ = enigo.key(Key::Control, Direction::Press);
        let _ = enigo.key(Key::Unicode('v'), Direction::Click);
        let _ = enigo.key(Key::Control, Direction::Release);
    }
}

#[cfg(not(target_os = "windows"))]
pub fn paste_into(_hwnd: isize) {}

/// Em layouts não-US (ex.: ABNT2 brasileiro), a tecla física do apóstrofo
/// gera um virtual-key diferente de VK_OEM_7. Resolvemos via VkKeyScanW qual
/// Code corresponde ao caractere `'` no layout ativo, para que o padrão
/// "Ctrl + '" funcione no teclado real do usuário.
#[cfg(target_os = "windows")]
fn apostrophe_code() -> &'static str {
    #[link(name = "user32")]
    extern "system" {
        fn VkKeyScanW(ch: u16) -> i16;
    }
    let scan = unsafe { VkKeyScanW(u16::from(b'\'')) };
    match (scan & 0xFF) as u8 {
        0xC0 => "Backquote",    // VK_OEM_3 — ABNT2: apóstrofo à esquerda do 1
        0xDE => "Quote",        // VK_OEM_7 — layout US
        0xBA => "Semicolon",    // VK_OEM_1
        0xBF => "Slash",        // VK_OEM_2
        0xDB => "BracketLeft",  // VK_OEM_4
        0xDD => "BracketRight", // VK_OEM_6
        0xDC => "Backslash",    // VK_OEM_5
        _ => "Quote",
    }
}

#[cfg(not(target_os = "windows"))]
fn apostrophe_code() -> &'static str {
    // No Linux/macOS com teclado ABNT2, a tecla (') fica no Backquote.
    // Como não temos VkKeyScanW aqui, assumimos Backquote como padrão mais provável para usuários BR.
    "Backquote"
}

pub fn default_hotkey() -> String {
    format!("CommandOrControl+{}", apostrophe_code())
}

/// Valida e registra uma nova hotkey global, removendo a anterior.
/// Retorna erro legível se a combinação for inválida ou rejeitada pelo SO.
pub fn swap_hotkey(app: &AppHandle, new: &str, previous: Option<&str>) -> Result<(), AppError> {
    let shortcut: Shortcut = new
        .parse()
        .map_err(|_| AppError::msg(format!("Atalho inválido: {new}")))?;
    if let Some(prev) = previous {
        unregister(app, prev);
    }
    app.global_shortcut()
        .register(shortcut)
        .map_err(|e| AppError::msg(format!("O sistema recusou o atalho: {e}")))
}

/// Remove o registro de uma hotkey, se válida. Usado para "silenciar"
/// temporariamente o atalho ativo enquanto o key recorder captura uma nova
/// combinação — sem isso, apertar o atalho atual durante a gravação abriria
/// a janela principal em vez de ser capturado pelo recorder.
pub fn unregister(app: &AppHandle, shortcut: &str) {
    if let Ok(s) = shortcut.parse::<Shortcut>() {
        let _ = app.global_shortcut().unregister(s);
    }
}

/// Se a janela já estiver visível, esconde; senão guarda a janela que tinha
/// foco (para o auto-paste) e devolve `true` para o chamador posicionar e
/// exibir. Compartilhado pelos dois pontos de entrada (hotkey e bandeja).
fn prepare_show(app: &AppHandle, window: &tauri::WebviewWindow) -> bool {
    if window.is_visible().unwrap_or(false) {
        let _ = window.hide();
        return false;
    }
    if let Some(state) = app.try_state::<AppState>() {
        if let Ok(mut last) = state.last_focus.lock() {
            *last = Some(foreground_window());
        }
    }
    true
}

/// Mostra a janela principal sob o cursor (com clamp para não sair do monitor)
/// ou a esconde se já estiver visível. Usado pela hotkey global.
pub fn toggle_main_window(app: &AppHandle) {
    let Some(window) = app.get_webview_window("main") else {
        return;
    };
    if !prepare_show(app, &window) {
        return;
    }

    let open_centered = crate::settings::get_bool(app, "openCentered").unwrap_or(false);
    if open_centered {
        let _ = window.center();
    } else if let Ok(cursor) = app.cursor_position() {
        let (mut x, mut y) = (cursor.x, cursor.y);
        let win_size = window.outer_size().ok();
        if let (Ok(Some(monitor)), Some(size)) =
            (app.monitor_from_point(cursor.x, cursor.y), win_size)
        {
            // Centraliza a janela em relação ao cursor (horizontal e vertical),
            // com um leve deslocamento para baixo para o cursor ficar um
            // pouco acima do centro
            x -= size.width as f64 / 2.0;
            y -= size.height as f64 / 2.0 - 70.0;

            let mpos = monitor.position();
            let msize = monitor.size();
            let max_x = mpos.x as f64 + msize.width as f64 - size.width as f64;
            let max_y = mpos.y as f64 + msize.height as f64 - size.height as f64;

            x = x.clamp(mpos.x as f64, max_x.max(mpos.x as f64));
            y = y.clamp(mpos.y as f64, max_y.max(mpos.y as f64));
        }
        let _ = window.set_position(PhysicalPosition::new(x as i32, y as i32));
    }
    let _ = window.show();
    let _ = window.set_focus();
    let _ = app.emit("fpaste://opened", ());
}

/// Mostra a janela principal centralizada na tela, ou esconde se já estiver
/// visível. Usado pelo menu do ícone da bandeja — diferente da hotkey, que
/// abre sob o cursor.
pub fn toggle_main_window_centered(app: &AppHandle) {
    let Some(window) = app.get_webview_window("main") else {
        return;
    };
    if !prepare_show(app, &window) {
        return;
    }
    let _ = window.center();
    let _ = window.show();
    let _ = window.set_focus();
    let _ = app.emit("fpaste://opened", ());
}
