use std::path::{Path, PathBuf};

use crate::crypto;
use crate::error::AppError;

/// Cifra o blob (AES-256-GCM) e grava em <data_dir>/media/<uuid>.bin.
/// Retorna o caminho absoluto do arquivo gravado.
pub fn save_encrypted(data_dir: &Path, key: &[u8; 32], plain: &[u8]) -> Result<PathBuf, AppError> {
    let media_dir = data_dir.join("media");
    std::fs::create_dir_all(&media_dir)?;
    let path = media_dir.join(format!("{}.bin", uuid::Uuid::new_v4()));
    let encrypted = crypto::encrypt_blob(key, plain)?;
    std::fs::write(&path, encrypted)?;
    Ok(path)
}

/// Lê e decifra um blob de mídia. A decifragem só acontece sob demanda,
/// quando a miniatura entra na área visível (spec §5.4).
pub fn load_decrypted(path: &Path, key: &[u8; 32]) -> Result<Vec<u8>, AppError> {
    let data = std::fs::read(path)?;
    crypto::decrypt_blob(key, &data)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn save_and_load_roundtrip() {
        let dir = std::env::temp_dir().join(format!("fpaste-test-{}", uuid::Uuid::new_v4()));
        let key = [9u8; 32];
        let plain = b"fake png bytes".to_vec();
        let path = save_encrypted(&dir, &key, &plain).unwrap();
        // O arquivo em disco não pode conter o conteúdo em claro.
        let on_disk = std::fs::read(&path).unwrap();
        assert!(!on_disk.windows(plain.len()).any(|w| w == plain.as_slice()));
        assert_eq!(load_decrypted(&path, &key).unwrap(), plain);
        let _ = std::fs::remove_dir_all(dir);
    }
}
