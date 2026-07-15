use aes_gcm::aead::{Aead, KeyInit};
use aes_gcm::{Aes256Gcm, Key, Nonce};
use base64::engine::general_purpose::STANDARD as B64;
use base64::Engine;
use rand::RngCore;
use sha2::{Digest, Sha256};

use crate::error::AppError;

const SERVICE: &str = "fpaste";
const KEY_NAME: &str = "db-master-key";
const NONCE_LEN: usize = 12;

/// Recupera a chave-mestra do gerenciador de credenciais do SO,
/// gerando e persistindo uma nova de 32 bytes no primeiro boot.
pub fn get_or_create_master_key() -> Result<[u8; 32], AppError> {
    let entry = keyring::Entry::new(SERVICE, KEY_NAME).map_err(AppError::msg)?;
    match entry.get_password() {
        Ok(b64) => {
            let bytes = B64.decode(b64).map_err(AppError::msg)?;
            bytes
                .try_into()
                .map_err(|_| AppError::msg("stored master key has invalid length"))
        }
        Err(keyring::Error::NoEntry) => {
            let mut key = [0u8; 32];
            rand::thread_rng().fill_bytes(&mut key);
            entry.set_password(&B64.encode(key)).map_err(AppError::msg)?;
            Ok(key)
        }
        Err(e) => Err(AppError::msg(e)),
    }
}

pub fn sha256_hex(data: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hex_encode(&hasher.finalize())
}

/// Cifra um blob com AES-256-GCM. Layout do resultado: nonce (12 bytes) || ciphertext.
pub fn encrypt_blob(key: &[u8; 32], plain: &[u8]) -> Result<Vec<u8>, AppError> {
    let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key));
    let mut nonce_bytes = [0u8; NONCE_LEN];
    rand::thread_rng().fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);
    let ciphertext = cipher.encrypt(nonce, plain).map_err(AppError::msg)?;
    let mut out = Vec::with_capacity(NONCE_LEN + ciphertext.len());
    out.extend_from_slice(&nonce_bytes);
    out.extend_from_slice(&ciphertext);
    Ok(out)
}

pub fn decrypt_blob(key: &[u8; 32], data: &[u8]) -> Result<Vec<u8>, AppError> {
    if data.len() < NONCE_LEN {
        return Err(AppError::msg("encrypted blob too short"));
    }
    let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key));
    let (nonce_bytes, ciphertext) = data.split_at(NONCE_LEN);
    cipher
        .decrypt(Nonce::from_slice(nonce_bytes), ciphertext)
        .map_err(AppError::msg)
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encrypt_decrypt_roundtrip() {
        let key = [7u8; 32];
        let plain = b"fpaste secret payload";
        let enc = encrypt_blob(&key, plain).unwrap();
        assert_ne!(&enc[NONCE_LEN..], plain.as_slice());
        assert_eq!(decrypt_blob(&key, &enc).unwrap(), plain);
    }

    #[test]
    fn decrypt_rejects_wrong_key() {
        let enc = encrypt_blob(&[1u8; 32], b"data").unwrap();
        assert!(decrypt_blob(&[2u8; 32], &enc).is_err());
    }

    #[test]
    fn sha256_is_stable() {
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }
}
