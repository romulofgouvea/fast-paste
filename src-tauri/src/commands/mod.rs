//! Comandos expostos ao frontend via IPC do Tauri, agrupados por
//! responsabilidade (SRP em nível de módulo). Cada submódulo cuida de uma área;
//! o `pub use` reexporta tudo para que os caminhos `commands::<fn>` usados no
//! `generate_handler!` continuem válidos.

mod backup;
mod clipboard;
mod groups;
mod history;
mod hotkey;
mod settings;
mod storage;
mod thumbnail;
mod window;

pub use backup::*;
pub use clipboard::*;
pub use groups::*;
pub use history::*;
pub use hotkey::*;
pub use settings::*;
pub use storage::*;
pub use thumbnail::*;
pub use window::*;
