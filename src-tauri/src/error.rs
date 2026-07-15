use serde::{Serialize, Serializer};

/// Erro unificado do backend do FPaste.
///
/// Substitui o antigo padrão `Result<_, String>` espalhado por todos os
/// módulos: as variantes com `#[from]` deixam o operador `?` converter os
/// erros de origem automaticamente, eliminando os `.map_err(|e| e.to_string())`
/// repetidos. Ao cruzar o IPC do Tauri é serializado como a string `Display`,
/// mantendo compatibilidade com o frontend, que já trata erro como texto.
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("banco de dados: {0}")]
    Db(#[from] rusqlite::Error),

    #[error("E/S: {0}")]
    Io(#[from] std::io::Error),

    #[error("backup: {0}")]
    Zip(#[from] zip::result::ZipError),

    #[error("lock '{0}' envenenado")]
    LockPoisoned(&'static str),

    #[error("{0}")]
    Message(String),
}

impl AppError {
    /// Envolve qualquer erro/valor `Display` numa mensagem — usado no lugar dos
    /// antigos `.map_err(|e| e.to_string())` para fontes sem `From` dedicado
    /// (clipboard, criptografia, plugins do Tauri, etc.).
    pub fn msg(e: impl std::fmt::Display) -> Self {
        AppError::Message(e.to_string())
    }
}

impl From<String> for AppError {
    fn from(s: String) -> Self {
        AppError::Message(s)
    }
}

impl From<&str> for AppError {
    fn from(s: &str) -> Self {
        AppError::Message(s.to_string())
    }
}

impl Serialize for AppError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}
